"""J-02 type_and_validate + J-03 clean_and_conform (F-02, F-03).

For every contract column, produces a ``<col>_typed`` value using
``try_cast`` semantics (never a silent-NULL cast that isn't captured -- see
§7.2 F-02). For identity-bearing and DQ-referenced fields, also produces the
``*_norm`` cleaned copies described in §F-03, always keeping the ``*_raw``
value untouched.
"""
from __future__ import annotations

from pyspark.sql import Column, DataFrame
from pyspark.sql import functions as F

from c360.schema.contracts import DatasetContract

SPARK_TYPE_MAP = {
    "string": "string", "integer": "int", "decimal": "decimal(14,2)",
    "boolean": "boolean", "timestamp": "timestamp", "date": "date",
}

SENTINELS = ["", "NULL", "null", "N/A", "n/a", "-", "unknown", "9999-12-31"]

COUNTRY_MAP = {"india": "IN", "in": "IN", "bharat": "IN", "us": "US", "usa": "US"}


def _clean_sentinel(col: Column) -> Column:
    trimmed = F.trim(col)
    return F.when(trimmed.isin(SENTINELS), F.lit(None)).otherwise(trimmed)


def _numeric_string(col: Column) -> Column:
    return F.regexp_replace(F.regexp_replace(col, r"[,₹$]", ""), r"\s+", "")


def _try_timestamp(col: Column, patterns: tuple[str, ...]) -> Column:
    if not patterns:
        patterns = ("yyyy-MM-dd'T'HH:mm:ss'Z'",)
    exprs = [F.to_timestamp(col, p) for p in patterns]
    return F.coalesce(*exprs)


def apply_contract_typing(df: DataFrame, contract: DatasetContract) -> DataFrame:
    out = df
    for col in contract.columns:
        if col.name not in out.columns:
            out = out.withColumn(col.name, F.lit(None).cast("string"))
        target = col.target_type
        raw = F.col(col.name) if target == "array<string>" else _clean_sentinel(F.col(col.name))
        clean_helper = f"__clean_{col.name}"
        if target == "timestamp":
            typed = _try_timestamp(raw, col.timestamp_patterns)
        elif target == "date":
            typed = F.coalesce(F.to_date(raw, "yyyy-MM-dd"), F.to_date(raw, "dd/MM/yyyy"))
        elif target == "decimal":
            out = out.withColumn(clean_helper, _numeric_string(raw))
            typed = F.expr(f"try_cast(`{clean_helper}` as decimal(14,2))")
        elif target == "integer":
            out = out.withColumn(clean_helper, raw)
            typed = F.expr(f"try_cast(`{clean_helper}` as int)")
        elif target == "boolean":
            lowered = F.lower(F.trim(raw))
            typed = (F.when(lowered.isin(list(col.bool_true_values)), F.lit(True))
                     .when(lowered.isin(list(col.bool_false_values)), F.lit(False))
                     .otherwise(F.lit(None).cast("boolean")))
        elif target == "array<string>":
            typed = raw  # arrays already parsed by the JSON reader; kept as-is
        else:
            typed = raw
        out = out.withColumn(f"{col.name}_typed", typed)
    helper_cols = [c for c in out.columns if c.startswith("__clean_")]
    if helper_cols:
        out = out.drop(*helper_cols)
    return out


def apply_cleaning(df: DataFrame) -> DataFrame:
    """F-03: identifier-bearing normalisation, applied where the column exists."""
    out = df
    cols = set(out.columns)

    if "email" in cols:
        out = out.withColumn(
            "email_norm",
            F.when(F.col("email").isNull() | (F.trim(F.col("email")) == ""), F.lit(None))
            .otherwise(F.regexp_replace(F.lower(F.trim(F.col("email"))), r"\.$", "")))
    if "email_address" in cols:
        out = out.withColumn(
            "email_norm",
            F.when(F.col("email_address").isNull() | (F.trim(F.col("email_address")) == ""), F.lit(None))
            .otherwise(F.regexp_replace(F.lower(F.trim(F.col("email_address"))), r"\.$", "")))
    if "requester_email" in cols:
        out = out.withColumn(
            "requester_email_norm",
            F.when(F.col("requester_email").isNull(), F.lit(None))
            .otherwise(F.regexp_replace(F.lower(F.trim(F.col("requester_email"))), r"\.$", "")))
    if "recipient_email" in cols:
        out = out.withColumn("email_norm", F.lower(F.trim(F.col("recipient_email"))))

    phone_col = "phone" if "phone" in cols else ("mobile" if "mobile" in cols else None)
    if phone_col:
        digits = F.regexp_replace(F.col(phone_col), r"[^0-9]", "")
        # §4.8: strip non-digits, strip a leading "00", strip a leading "0"
        # when the remainder is 10 digits, accept a leading country code 91.
        national = (F.when(F.length(digits) == 10, digits)
                    .when((F.length(digits) == 11) & (F.substring(digits, 1, 1) == "0"), F.substring(digits, 2, 10))
                    .when((F.length(digits) == 12) & (F.substring(digits, 1, 2) == "91"), F.substring(digits, 3, 10))
                    .when((F.length(digits) == 13) & (F.substring(digits, 1, 3) == "091"), F.substring(digits, 4, 10))
                    .otherwise(F.lit(None)))
        # Structural normalisation only; sentinel/switchboard screening is an
        # identity-resolution concern (§10.4), not a cleaning concern.
        out = out.withColumn("phone_norm", F.when(national.isNotNull(), F.concat(F.lit("+91"), national)).otherwise(F.lit(None)))

    if "country" in cols:
        out = out.withColumn("country_norm", _map_country(F.col("country")))
    if "ship_country" in cols:
        out = out.withColumn("country_norm", _map_country(F.col("ship_country")))
    if "country_code" in cols:
        out = out.withColumn("country_norm", _map_country(F.col("country_code")))

    if "account_status" in cols:
        out = out.withColumn("account_status_norm", F.lower(F.trim(F.col("account_status"))))
    if "first_name" in cols:
        out = out.withColumn("first_name_norm", F.lower(F.trim(F.regexp_replace(F.col("first_name"), r"\s+", " "))))
    if "last_name" in cols:
        out = out.withColumn("last_name_norm", F.lower(F.trim(F.regexp_replace(F.col("last_name"), r"\s+", " "))))
    if "member_name" in cols:
        parts = F.split(F.trim(F.regexp_replace(F.col("member_name"), r"\s+", " ")), " ")
        out = out.withColumn("first_name_norm", F.lower(parts.getItem(0)))
        out = out.withColumn("last_name_norm", F.lower(F.element_at(parts, -1)))

    return out


def _map_country(col: Column) -> Column:
    lowered = F.lower(F.trim(col))
    mapping = F.create_map(*[x for kv in COUNTRY_MAP.items() for x in (F.lit(kv[0]), F.lit(kv[1]))])
    return F.coalesce(mapping[lowered], F.upper(F.trim(col)))
