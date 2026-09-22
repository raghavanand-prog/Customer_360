"""Identity namespace helpers (§10.2, §10.3).

Normalisation of raw values happens upstream in ``c360.pipeline.typing_clean``
(F-03); this module only adds the hash/mask pair that is what gets persisted
in the identity graph tables, so the graph carries less raw PII than the
source layer (§10.3).
"""
from __future__ import annotations

from pyspark.sql import Column
from pyspark.sql import functions as F

NAMESPACES = ("email", "phone", "crm_id", "loyalty_id", "app_user_id", "device_cookie")

# device_cookie is deliberately excluded from matching by default (§10.2) --
# enforced by simply never blocking on it in matching.py, not by omitting it
# from the graph (it is still used for sessionisation/attribution).
MATCHABLE_NAMESPACES = ("email", "phone", "crm_id", "loyalty_id", "app_user_id")


def value_hash(namespace_col: Column, value_col: Column) -> Column:
    return F.sha2(F.concat_ws(":", namespace_col, value_col), 256)


def masked_value(namespace_col: Column, value_col: Column) -> Column:
    """Shows a short, non-reversible-looking prefix/suffix for display."""
    length = F.length(value_col)
    return F.when(
        value_col.isNull(), F.lit(None)
    ).otherwise(
        F.concat(F.substring(value_col, 1, 2), F.lit("***"),
                  F.when(length > 4, F.substring(value_col, -2, 2)).otherwise(F.lit("")))
    )


def normalise_authoritative_id(col: Column) -> Column:
    return F.upper(F.trim(col))
