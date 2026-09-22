"""J-06/J-07/J-08: customer aggregation, sessionisation, profile assembly."""
from __future__ import annotations

from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F


def enrich_orders(orders: DataFrame) -> DataFrame:
    net = (F.col("gross_amount_typed")
           - F.coalesce(F.col("discount_amount_typed"), F.lit(0))
           + F.coalesce(F.col("shipping_amount_typed"), F.lit(0))
           + F.coalesce(F.col("tax_amount_typed"), F.lit(0)))
    is_sale = F.col("order_type") == "sale"
    revenue = F.when(is_sale, net).otherwise(F.lit(0))

    w = Window.partitionBy("canonical_customer_id").orderBy("order_ts_typed")
    out = (
        orders.withColumn("net_amount", net)
        .withColumn("revenue_amount", revenue)
        .withColumn("is_first_order", F.row_number().over(w) == 1)
        .withColumn("days_since_previous_order",
                    F.datediff(F.col("order_ts_typed"), F.lag("order_ts_typed").over(w)))
    )
    return out


def compute_customer_metrics(orders_enriched: DataFrame, sessions: DataFrame, as_of_date) -> DataFrame:
    sale_orders = orders_enriched.filter((F.col("order_type") == "sale") & F.col("canonical_customer_id").isNotNull())
    refund_orders = orders_enriched.filter((F.col("order_type") == "refund") & F.col("canonical_customer_id").isNotNull())

    order_agg = sale_orders.groupBy("canonical_customer_id").agg(
        F.count("*").alias("order_count"),
        F.sum("revenue_amount").alias("total_spend"),
        F.min("order_ts_typed").alias("first_order_at"),
        F.max("order_ts_typed").alias("last_order_at"),
        F.avg("revenue_amount").alias("aov"),
        F.expr("percentile_approx(days_since_previous_order, 0.5)").alias("median_ipi_days"),
    )
    refund_agg = refund_orders.groupBy("canonical_customer_id").agg(
        F.sum(F.abs(F.col("net_amount"))).alias("refunded_amount"))

    session_agg = sessions.groupBy("canonical_customer_id").agg(
        F.count("*").alias("sessions_90d"),
        F.sum(F.col("has_add_to_cart").cast("int")).alias("cart_abandon_sessions_90d_raw"),
        F.max("session_end_ts").alias("last_seen_at"),
        F.sum("event_count").alias("events_90d"),
    )

    metrics = order_agg.join(refund_agg, "canonical_customer_id", "left") \
        .join(session_agg, "canonical_customer_id", "left")

    metrics = metrics.withColumn("refunded_amount", F.coalesce(F.col("refunded_amount"), F.lit(0.0)))
    metrics = metrics.withColumn("days_since_last_order", F.datediff(F.lit(as_of_date), F.col("last_order_at")))
    metrics = metrics.withColumn("days_since_last_seen", F.datediff(F.lit(as_of_date), F.col("last_seen_at")))
    metrics = metrics.withColumn(
        "purchase_frequency_per_year",
        F.when(F.col("first_order_at").isNotNull(),
               F.col("order_count") / F.greatest(F.datediff(F.lit(as_of_date), F.col("first_order_at")) / 365.0, F.lit(0.01)))
        .otherwise(F.lit(None)))
    metrics = metrics.withColumn("historical_clv", F.col("total_spend") - F.col("refunded_amount"))

    # RFM quintiles (§F-09 item 5)
    w_r = Window.orderBy(F.col("days_since_last_order").asc_nulls_last())
    w_f = Window.orderBy(F.col("order_count").asc_nulls_last())
    w_m = Window.orderBy(F.col("total_spend").asc_nulls_last())
    metrics = (metrics
               .withColumn("r_score", F.ntile(5).over(w_r))
               .withColumn("f_score", F.ntile(5).over(w_f))
               .withColumn("m_score", F.ntile(5).over(w_m)))
    metrics = metrics.withColumn("rfm_segment", F.concat_ws("", F.col("r_score"), F.col("f_score"), F.col("m_score")))

    metrics = metrics.withColumn(
        "churn_risk_band",
        F.when(F.col("order_count").isNull() | (F.col("order_count") == 0), F.lit("no_purchase_history"))
        .when(F.col("days_since_last_order") <= 90, F.lit("active"))
        .when(F.col("days_since_last_order") <= 365, F.lit("at_risk"))
        .otherwise(F.lit("churned")))

    metrics = metrics.withColumn(
        "engagement_raw",
        F.coalesce(F.col("sessions_90d"), F.lit(0)) * 1.0 + F.coalesce(F.col("events_90d"), F.lit(0)) * 0.1)
    engagement_window = Window.orderBy(F.col("engagement_raw").asc_nulls_first())
    metrics = metrics.withColumn("engagement_score", (F.ntile(10).over(engagement_window) * 10).cast("int"))
    metrics = metrics.withColumn("as_of_date", F.lit(as_of_date))
    metrics = metrics.withColumnRenamed("cart_abandon_sessions_90d_raw", "cart_abandon_sessions_90d")
    return metrics


def sessionise(events: DataFrame, gap_minutes: int = 30) -> DataFrame:
    """F-08: 30-minute inactivity rule via window functions (J-04)."""
    key_cols = ["canonical_customer_id", "device_cookie"]
    w = Window.partitionBy(*key_cols).orderBy("event_ts_typed")
    with_gap = events.withColumn("_prev_ts", F.lag("event_ts_typed").over(w))
    with_gap = with_gap.withColumn(
        "_new_session",
        F.when(F.col("_prev_ts").isNull(), 1)
        .when(F.col("event_ts_typed").cast("long") - F.col("_prev_ts").cast("long") > gap_minutes * 60, 1)
        .otherwise(0))
    with_gap = with_gap.withColumn("_session_seq", F.sum("_new_session").over(w.rowsBetween(Window.unboundedPreceding, 0)))
    with_gap = with_gap.withColumn(
        "session_id",
        F.sha2(F.concat_ws(":", F.coalesce(F.col("canonical_customer_id"), F.lit("anon")),
                            F.col("device_cookie"), F.col("_session_seq").cast("string")), 256))

    session_window = Window.partitionBy("session_id")
    sessions = with_gap.groupBy("session_id", "canonical_customer_id", "device_cookie").agg(
        F.min("event_ts_typed").alias("session_start_ts"),
        F.max("event_ts_typed").alias("session_end_ts"),
        F.count("*").alias("event_count"),
        F.countDistinct("page_url").alias("distinct_pages"),
        F.max((F.col("event_type") == "add_to_cart").cast("boolean")).alias("has_add_to_cart"),
        F.max((F.col("event_type") == "checkout_start").cast("boolean")).alias("has_checkout_start"),
        F.max((F.col("event_type") == "purchase").cast("boolean")).alias("has_purchase"),
        F.first("page_url").alias("entry_page"),
        F.first("utm_source", ignorenulls=True).alias("utm_source"),
    )
    sessions = sessions.withColumn("duration_s", F.col("session_end_ts").cast("long") - F.col("session_start_ts").cast("long"))
    sessions = sessions.withColumn("is_bounce", (F.col("event_count") == 1) & (F.col("duration_s") < 10))
    with_session_id = with_gap.select(
        F.coalesce(F.col("event_id"), F.sha2(F.concat_ws(":", "device_cookie", "event_ts_typed", "event_type"), 256)).alias("event_id"),
        "canonical_customer_id", "session_id", "device_cookie", "event_type", "event_ts_typed",
        "page_url", "product_id", "search_term", "cart_value", "utm_source", "utm_campaign", "device_type",
    )
    return sessions, with_session_id
