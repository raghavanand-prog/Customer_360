"""Server-side PII masking (§18.5, §26). Never trust the browser to hide it."""
from __future__ import annotations


def mask_email(value: str | None) -> str | None:
    if not value or "@" not in value:
        return value
    local, domain = value.split("@", 1)
    visible = local[:2]
    return f"{visible}***@{domain}"


def mask_phone(value: str | None) -> str | None:
    if not value or len(value) < 4:
        return value
    return f"{value[:3]}***{value[-2:]}"


def apply_profile_masking(profile: dict, role: str, masked_roles: set[str]) -> dict:
    if role not in masked_roles:
        return profile
    masked = dict(profile)
    if masked.get("primary_email"):
        masked["primary_email"] = mask_email(masked["primary_email"])
    if masked.get("primary_phone"):
        masked["primary_phone"] = mask_phone(masked["primary_phone"])
    return masked
