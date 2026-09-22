"""Dataset contract primitives (§7.3).

A contract is the single declared truth for a source dataset's column set:
name, target type, nullability, semantic role, sensitivity label, and (for
timestamps) the ordered list of accepted patterns. It is read by:

- the Spark typing stage (J-02), to build ``try_cast`` expressions and
  detect missing/extra columns;
- the DQ engine, to auto-generate ``Q-TYPE-*`` rules;
- ``scripts/check_contracts.py`` (CI), to catch drift against the DDL, the
  Pydantic API models, and ``docs/DATA_DICTIONARY.md``.

This module is intentionally free of any PySpark or SQLAlchemy import, so it
can be imported from the API process too (which must run without Spark
installed, §7.4).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SemanticType(str, Enum):
    IDENTIFIER = "identifier"
    NAME = "name"
    ADDRESS = "address"
    DEMOGRAPHIC = "demographic"
    STATUS = "status"
    ATTRIBUTE = "attribute"
    AUDIT = "audit"
    CONSENT = "consent"
    MONEY = "money"


class Sensitivity(str, Enum):
    INTERNAL = "internal"
    PII = "pii"
    SENSITIVE_PII = "sensitive_pii"


@dataclass(frozen=True)
class ColumnContract:
    name: str
    target_type: str  # "string" | "integer" | "decimal" | "boolean" | "timestamp" | "date" | "array<string>"
    required: bool
    semantic: SemanticType
    sensitivity: Sensitivity
    identity_namespace: str | None = None
    timestamp_patterns: tuple[str, ...] = ()
    enum_values: tuple[str, ...] = ()
    bool_true_values: tuple[str, ...] = ("true", "1", "y", "yes")
    bool_false_values: tuple[str, ...] = ("false", "0", "n", "no", "")


@dataclass(frozen=True)
class DatasetContract:
    dataset_id: str          # D-01 .. D-09
    name: str                # conformed name, e.g. "customers_crm"
    version: int
    primary_key: tuple[str, ...]
    columns: tuple[ColumnContract, ...]
    source_system: str

    def column_names(self) -> set[str]:
        return {c.name for c in self.columns}

    def required_columns(self) -> set[str]:
        return {c.name for c in self.columns if c.required}
