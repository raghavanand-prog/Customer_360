"""F-04 conforming + identity_edges_input construction.

Builds the namespaced identifier long table (§F-04 step 3) from the three
person-bearing sources, and resolves each order's polymorphic
``customer_ref`` to a namespace + value pair so it can be joined against the
identity graph (R-05, §10.5).
"""
from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def person_identity_edges(crm: DataFrame, loyalty: DataFrame, app: DataFrame) -> DataFrame:
    crm_edges = crm.select(
        F.lit("crm").alias("source_system"), F.col("crm_customer_id").alias("source_record_id"),
        F.array(
            F.struct(F.lit("crm_id").alias("identity_namespace"), F.upper(F.trim(F.col("crm_customer_id"))).alias("identity_value_norm")),
            F.struct(F.lit("email").alias("identity_namespace"), F.col("email_norm").alias("identity_value_norm")),
            F.struct(F.lit("phone").alias("identity_namespace"), F.col("phone_norm").alias("identity_value_norm")),
        ).alias("edges"),
        F.col("first_name_norm"), F.col("last_name_norm"),
    )
    loyalty_edges = loyalty.select(
        F.lit("loyalty").alias("source_system"), F.col("loyalty_id").alias("source_record_id"),
        F.array(
            F.struct(F.lit("loyalty_id").alias("identity_namespace"), F.upper(F.trim(F.col("loyalty_id"))).alias("identity_value_norm")),
            F.struct(F.lit("email").alias("identity_namespace"), F.col("email_norm").alias("identity_value_norm")),
            F.struct(F.lit("phone").alias("identity_namespace"), F.col("phone_norm").alias("identity_value_norm")),
        ).alias("edges"),
        F.col("first_name_norm"), F.col("last_name_norm"),
    )
    app_edges = app.select(
        F.lit("app").alias("source_system"), F.col("app_user_id").alias("source_record_id"),
        F.array(
            F.struct(F.lit("app_user_id").alias("identity_namespace"), F.upper(F.trim(F.col("app_user_id"))).alias("identity_value_norm")),
            F.struct(F.lit("email").alias("identity_namespace"), F.col("email_norm").alias("identity_value_norm")),
            F.struct(F.lit("phone").alias("identity_namespace"), F.col("phone_norm").alias("identity_value_norm")),
        ).alias("edges"),
        F.lit(None).cast("string").alias("first_name_norm"), F.lit(None).cast("string").alias("last_name_norm"),
    )

    unioned = crm_edges.unionByName(loyalty_edges).unionByName(app_edges)
    person_attrs = unioned.select(
        "source_system", "source_record_id", "first_name_norm", "last_name_norm",
        F.concat_ws(" ", "first_name_norm", "last_name_norm").alias("full_name_norm"),
    )
    edges_long = (
        unioned.select("source_system", "source_record_id", F.explode("edges").alias("e"))
        .select("source_system", "source_record_id", F.col("e.identity_namespace"), F.col("e.identity_value_norm"))
        .filter(F.col("identity_value_norm").isNotNull() & (F.trim(F.col("identity_value_norm")) != ""))
    )
    return edges_long, person_attrs


def resolve_order_customer_ref(orders: DataFrame) -> DataFrame:
    ref = F.col("customer_ref")
    inferred_type = F.coalesce(
        F.col("customer_ref_type"),
        F.when(ref.rlike("^[Cc][0-9]{6}$"), F.lit("crm_id"))
        .when(ref.rlike("^[Uu][0-9A-Za-z]{8,}$"), F.lit("app_user_id"))
        .when(ref.contains("@"), F.lit("email"))
        .otherwise(F.lit(None)),
    )
    namespace = (F.when(inferred_type == "crm_id", F.lit("crm_id"))
                 .when(inferred_type == "app_user_id", F.lit("app_user_id"))
                 .otherwise(F.lit("email")))
    value_norm = (F.when(namespace == "email", F.lower(F.trim(ref)))
                  .otherwise(F.upper(F.trim(ref))))
    return orders.withColumn("ref_namespace", namespace).withColumn("ref_value_norm", value_norm)
