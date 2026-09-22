"""RBAC matrix (§18.3-18.4). Roles are strictly ordered by privilege."""
from __future__ import annotations

ROLE_ORDER = ["viewer", "analyst", "data_engineer", "admin"]
ROLE_RANK = {r: i for i, r in enumerate(ROLE_ORDER)}


def highest_role(roles: list[str]) -> str:
    ranked = [r for r in roles if r in ROLE_RANK]
    if not ranked:
        return "viewer"
    return max(ranked, key=lambda r: ROLE_RANK[r])


def has_at_least(user_roles: list[str], minimum: str) -> bool:
    if minimum not in ROLE_RANK:
        return False
    return ROLE_RANK[highest_role(user_roles)] >= ROLE_RANK[minimum]
