"""AST -> parameterised SQL compiler (§14.4).

Values never enter the SQL string; every leaf becomes ``<expr> <op>
%(param_n)s`` with the literal bound separately. This is the structural
reason injection is impossible here -- there is no string interpolation of
a user-supplied value, ever.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .registry import FIELD_REGISTRY

_SQL_OPS = {">": ">", ">=": ">=", "<": "<", "<=": "<=", "=": "=", "!=": "!="}


class SegmentValidationError(ValueError):
    pass


@dataclass
class CompiledPredicate:
    sql: str
    params: dict = field(default_factory=dict)


def _resolve_value(value, thresholds: dict, params: dict, counter: list[int]):
    if isinstance(value, dict) and "param" in value:
        resolved = thresholds.get(value["param"])
        if resolved is None:
            raise SegmentValidationError(f"Unknown threshold parameter: {value['param']}")
        value = resolved
    key = f"p{counter[0]}"
    counter[0] += 1
    params[key] = value
    return f"%({key})s"


def compile_ast(node: dict, thresholds: dict, null_handling: str, params: dict | None = None,
                 counter: list[int] | None = None) -> CompiledPredicate:
    params = params if params is not None else {}
    counter = counter if counter is not None else [0]
    op = node.get("op")

    if op in ("AND", "OR"):
        parts = [compile_ast(c, thresholds, null_handling, params, counter).sql for c in node["children"]]
        joiner = f" {op} "
        return CompiledPredicate(f"({joiner.join(parts)})", params)
    if op == "NOT":
        inner = compile_ast(node["children"][0], thresholds, null_handling, params, counter)
        return CompiledPredicate(f"(NOT {inner.sql})", params)

    field_name = node.get("field")
    field_def = FIELD_REGISTRY.get(field_name)
    if field_def is None:
        raise SegmentValidationError(f"Unknown field: {field_name}")
    if op not in field_def.allowed_operators and op not in ("IS NULL", "IS NOT NULL"):
        raise SegmentValidationError(f"Operator {op} not allowed on field {field_name}")

    if op in _SQL_OPS:
        placeholder = _resolve_value(node["value"], thresholds, params, counter)
        base = f"{field_def.sql_expression} {_SQL_OPS[op]} {placeholder}"
    elif op in ("IN", "NOT IN"):
        values = node["value"]
        placeholders = []
        for v in values:
            placeholders.append(_resolve_value(v, thresholds, params, counter))
        base = f"{field_def.sql_expression} {op} ({', '.join(placeholders)})"
    elif op == "IS NULL":
        return CompiledPredicate(f"{field_def.sql_expression} IS NULL", params)
    elif op == "IS NOT NULL":
        return CompiledPredicate(f"{field_def.sql_expression} IS NOT NULL", params)
    else:
        raise SegmentValidationError(f"Unsupported operator: {op}")

    if field_def.nullable:
        if null_handling == "include":
            base = f"({base} OR {field_def.sql_expression} IS NULL)"
        else:
            base = f"({base})"  # SQL's native NULL semantics already yield UNKNOWN -> excluded from WHERE
    return CompiledPredicate(base, params)
