"""Identifier screening: the over-merge guard (§10.4).

An identifier that fails a screen is retained on the record (for display and
support search) but is stripped of matching power -- it never causes an
edge to be generated, and it never causes a record to be dropped.
"""
from __future__ import annotations

import re

from pyspark.sql import Column, DataFrame
from pyspark.sql import functions as F
from pyspark.sql import Window

from .namespaces import masked_value, value_hash

GENERIC_LOCAL_RE = re.compile(r"^(info|admin|support|noreply|no-reply|sales|contact|help|billing|hello|office)$")


def _is_syntactically_implausible(value_col: Column) -> Column:
    """Catches only unambiguous junk: a single digit repeated throughout
    (e.g. ``1111111111``). Anything with more digit variety is left to R-03
    to link and to the attribute-conflict guard to arbitrate (§10.8 Ex. 3),
    since a genuinely low-diversity *real* number must not be screened away
    before it has a chance to be evaluated on its merits."""
    digits_only = F.regexp_replace(value_col, r"[^0-9]", "")
    distinct_digit_count = F.size(F.array_distinct(F.split(digits_only, "")))
    return (F.length(digits_only) >= 7) & (distinct_digit_count <= 1)


def screen_identifiers(
    edges_input: DataFrame,
    denylist: dict,
    screening_cfg: dict,
    person_attrs: DataFrame | None = None,
) -> tuple[DataFrame, DataFrame]:
    """edges_input: (source_system, source_record_id, identity_namespace, identity_value_norm[, full_name_norm]).

    Returns (edges_input_with_screen_flag, screened_log_df).
    """
    df = edges_input.withColumn("value_hash", value_hash(F.col("identity_namespace"), F.col("identity_value_norm")))
    df = df.withColumn("value_masked", masked_value(F.col("identity_namespace"), F.col("identity_value_norm")))

    static_values = [v.lower() for v in denylist.get("values", [])]
    local_denylist = denylist.get("email_local_denylist", [])

    is_static = F.lower(F.col("identity_value_norm")).isin(static_values)
    local_part = F.regexp_extract(F.col("identity_value_norm"), r"^([^@]+)@", 1)
    is_generic_email = (F.col("identity_namespace") == "email") & F.lower(local_part).isin(local_denylist)
    is_implausible = _is_syntactically_implausible(F.col("identity_value_norm"))

    # S3: frequency threshold -- more than N distinct records across >= 2 sources.
    # Exact counts via collect_set, not approx_count_distinct: this guard is
    # precision-critical (it is what neutralises switchboard numbers, §10.4),
    # and approx_count_distinct is unreliable at the small cardinalities this
    # operates over -- it is a HyperLogLog estimator built for scale, not for
    # correctly distinguishing "3 records" from "9 records".
    freq_window = Window.partitionBy("identity_namespace", "value_hash")
    df = df.withColumn("_distinct_records", F.size(F.collect_set(
        F.concat_ws(":", "source_system", "source_record_id")).over(freq_window)))
    df = df.withColumn("_distinct_sources", F.size(F.collect_set("source_system").over(freq_window)))
    max_persons = screening_cfg.get("max_persons_per_identifier", 8)
    is_high_frequency = (F.col("_distinct_records") > max_persons) & (F.col("_distinct_sources") >= 2)

    screen_reason = (
        F.when(is_static, F.lit("S1_static_denylist"))
        .when(is_generic_email, F.lit("S2_format_denylist"))
        .when(is_high_frequency, F.lit("S3_frequency_threshold"))
        .when(is_implausible, F.lit("S5_syntactic_implausibility"))
        .otherwise(F.lit(None))
    )

    # S4: phone_max_distinct_names -- needs person attributes joined in
    if person_attrs is not None and "full_name_norm" in person_attrs.columns:
        joined = df.join(person_attrs, on=["source_system", "source_record_id"], how="left")
        name_window = Window.partitionBy("identity_namespace", "value_hash")
        joined = joined.withColumn("_distinct_names", F.size(F.collect_set("full_name_norm").over(name_window)))
        phone_names_threshold = screening_cfg.get("phone_max_distinct_names", 3)
        is_s4 = (F.col("identity_namespace") == "phone") & (F.col("_distinct_names") > phone_names_threshold)
        screen_reason = F.when(screen_reason.isNotNull(), screen_reason).when(is_s4, F.lit("S4_phone_name_cardinality")).otherwise(F.lit(None))
        df = joined.withColumn("screen_reason", screen_reason)
    else:
        df = df.withColumn("screen_reason", screen_reason)

    df = df.withColumn("is_screened", F.col("screen_reason").isNotNull())

    screened_log = (
        df.filter(F.col("is_screened"))
        .groupBy("identity_namespace", "value_hash", "value_masked", "screen_reason")
        .agg(
            F.countDistinct(F.concat_ws(":", "source_system", "source_record_id")).alias("distinct_record_count"),
            F.countDistinct("source_system").alias("distinct_source_count"),
        )
    )
    return df, screened_log
