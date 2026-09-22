"""Data quality rule type registry (§9.2, §9.3).

Every rule type is a class implementing ``build(rule_cfg, df) -> Column``
that returns ``true`` when a record *passes*. ``RecordRule`` and
``DatasetRule`` are kept as distinct base classes because a dataset-level
rule (row-count bounds, drift) has no per-record truth value -- conflating
the two is exactly the modelling mistake §9.3 warns against.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from pyspark.sql import Column, DataFrame
from pyspark.sql import functions as F


@dataclass
class RuleConfig:
    id: str
    name: str
    dimension: str
    type: str
    severity: str
    column: str | None = None
    columns: list[str] | None = None
    pattern: str | None = None
    values: list[Any] | None = None
    min: Any = None
    max: Any = None
    max_expr: str | None = None
    max_age_years: int | None = None
    inclusive: bool = True
    min_len: int | None = None
    max_len: int | None = None
    ref_dataset: str | None = None
    ref_column: str | None = None
    skew_tolerance_s: int = 300
    column_earlier: str | None = None
    column_later: str | None = None
    allow_equal: bool = True
    expression: str | None = None
    key_columns: list[str] | None = None
    value_column: str | None = None
    target_type: str | None = None
    applies_when: str | None = None
    threshold_dataset_fail_rate: float | None = None


class RecordRule(ABC):
    """A rule whose truth value is defined per record."""

    @abstractmethod
    def build(self, cfg: RuleConfig, df: DataFrame, context: dict) -> Column:
        ...


class DatasetRule(ABC):
    """A rule whose truth value is defined over the whole dataset."""

    @abstractmethod
    def evaluate(self, cfg: RuleConfig, df: DataFrame, context: dict) -> tuple[bool, dict]:
        ...


def _scope(cfg: RuleConfig, passed: Column) -> Column:
    if cfg.applies_when:
        return F.when(F.expr(cfg.applies_when), passed).otherwise(F.lit(True))
    return passed


class NotNullRule(RecordRule):
    def build(self, cfg, df, context):
        return _scope(cfg, F.col(cfg.column).isNotNull())


class NotBlankRule(RecordRule):
    def build(self, cfg, df, context):
        return _scope(cfg, (F.col(cfg.column).isNotNull()) & (F.trim(F.col(cfg.column)) != ""))


class TypeCastRule(RecordRule):
    def build(self, cfg, df, context):
        casted_col = f"{cfg.column}_typed"
        if casted_col in df.columns:
            return _scope(cfg, ~((F.col(cfg.column).isNotNull()) & (F.col(casted_col).isNull())))
        return F.lit(True)


class RegexRule(RecordRule):
    def build(self, cfg, df, context):
        return _scope(cfg, F.col(cfg.column).rlike(cfg.pattern))


class InSetRule(RecordRule):
    def build(self, cfg, df, context):
        return _scope(cfg, F.col(cfg.column).isin(cfg.values) | F.col(cfg.column).isNull())


class NumericRangeRule(RecordRule):
    def build(self, cfg, df, context):
        c = F.col(cfg.column)
        if cfg.inclusive:
            cond = (c >= cfg.min) & (c <= cfg.max)
        else:
            cond = (c > cfg.min) & (c < cfg.max)
        return _scope(cfg, cond | c.isNull())


class LengthRangeRule(RecordRule):
    def build(self, cfg, df, context):
        length = F.length(F.col(cfg.column))
        return _scope(cfg, ((length >= cfg.min_len) & (length <= cfg.max_len)) | F.col(cfg.column).isNull())


class UniqueRule(RecordRule):
    def build(self, cfg, df, context):
        from pyspark.sql import Window
        w = Window.partitionBy(*cfg.columns)
        return F.count("*").over(w) == 1


class ReferentialRule(RecordRule):
    def build(self, cfg, df, context):
        ref_keys = context.get("ref_keys", {}).get(cfg.ref_dataset)
        if ref_keys is None:
            return F.lit(True)
        return _scope(cfg, F.col(cfg.column).isin(ref_keys) | F.col(cfg.column).isNull())


class TimestampNotFutureRule(RecordRule):
    def build(self, cfg, df, context):
        c = F.col(cfg.column)
        limit = F.expr(f"current_timestamp() + INTERVAL {cfg.skew_tolerance_s} SECONDS")
        return _scope(cfg, (c <= limit) | c.isNull())


class TimestampRangeRule(RecordRule):
    def build(self, cfg, df, context):
        c = F.col(cfg.column)
        return _scope(cfg, ((c >= F.lit(cfg.min).cast("timestamp")) & (c <= F.lit(cfg.max).cast("timestamp"))) | c.isNull())


class DateRangeRule(RecordRule):
    def build(self, cfg, df, context):
        c = F.col(cfg.column)
        max_expr = F.expr(cfg.max_expr) if cfg.max_expr else F.current_date()
        cond = (c >= F.lit(cfg.min).cast("date")) & (c <= max_expr)
        if cfg.max_age_years:
            cond = cond & (F.datediff(F.current_date(), c) <= cfg.max_age_years * 366)
        return _scope(cfg, cond | c.isNull())


class TemporalOrderRule(RecordRule):
    def build(self, cfg, df, context):
        earlier, later = F.col(cfg.column_earlier), F.col(cfg.column_later)
        cond = (later >= earlier) if cfg.allow_equal else (later > earlier)
        return _scope(cfg, cond | earlier.isNull() | later.isNull())


class EmailSyntaxRule(RecordRule):
    PATTERN = r"^[^@\s]+@[^@\s.]+\.[^@\s]{2,}$"

    def build(self, cfg, df, context):
        c = F.col(cfg.column)
        return _scope(cfg, c.rlike(self.PATTERN) | c.isNull())


class PhoneNormalisableRule(RecordRule):
    def build(self, cfg, df, context):
        norm_col = f"{cfg.column}_norm"
        if norm_col in df.columns:
            return _scope(cfg, F.col(norm_col).isNotNull() | F.col(cfg.column).isNull())
        return F.lit(True)


class CrossFieldConsistencyRule(RecordRule):
    def build(self, cfg, df, context):
        return _scope(cfg, F.expr(cfg.expression))


class DuplicateCompositeRule(RecordRule):
    def build(self, cfg, df, context):
        from pyspark.sql import Window
        w = Window.partitionBy(*cfg.columns)
        return F.count("*").over(w) == 1


class SetConsistencyRule(RecordRule):
    def build(self, cfg, df, context):
        from pyspark.sql import Window
        w = Window.partitionBy(*cfg.key_columns)
        return F.approx_count_distinct(F.col(cfg.value_column)).over(w) <= 1


RULE_REGISTRY: dict[str, RecordRule | DatasetRule] = {
    "not_null": NotNullRule(),
    "not_blank": NotBlankRule(),
    "type_cast": TypeCastRule(),
    "regex": RegexRule(),
    "in_set": InSetRule(),
    "numeric_range": NumericRangeRule(),
    "length_range": LengthRangeRule(),
    "unique": UniqueRule(),
    "referential": ReferentialRule(),
    "timestamp_not_future": TimestampNotFutureRule(),
    "timestamp_range": TimestampRangeRule(),
    "date_range": DateRangeRule(),
    "temporal_order": TemporalOrderRule(),
    "email_syntax": EmailSyntaxRule(),
    "phone_normalisable": PhoneNormalisableRule(),
    "cross_field_consistency": CrossFieldConsistencyRule(),
    "duplicate_composite": DuplicateCompositeRule(),
    "set_consistency": SetConsistencyRule(),
}

SEVERITY_WEIGHT = {"info": 0.1, "warn": 0.4, "quarantine": 1.0, "reject": 1.0}
DIMENSION_WEIGHT = {
    "completeness": 0.25, "validity": 0.25, "uniqueness": 0.15,
    "consistency": 0.15, "integrity": 0.10, "timeliness": 0.10,
}
