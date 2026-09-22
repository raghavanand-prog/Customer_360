"""Per-source formatting variants: phone (§4.8), country (§4.9 X-11), dates.

These are applied at *projection* time (population truth -> source schema),
which is why a normalisation stage in the pipeline has real, seeded work to
do (F-03).
"""
from __future__ import annotations

from datetime import date, datetime

import numpy as np

PHONE_FORMATTERS = [
    lambda n: f"+91 {n[:5]} {n[5:]}",
    lambda n: f"+91{n}",
    lambda n: f"0098{n}",
    lambda n: f"0{n}",
    lambda n: f"{n[:5]}-{n[5:]}",
    lambda n: n,
    lambda n: f"+91-{n[:5]}-{n[5:]}",
    lambda n: f"(9{n[1:3]}){n[3:6]} {n[6:]}",
    lambda n: f"+91 ({n[:2]}) {n[2:5]} {n[5:]}",
    lambda n: f"91 {n[:5]} {n[5:]}",
    lambda n: f"{n[:5]} {n[5:]} ext 12",  # deliberately unnormalisable (X-04)
]

COUNTRY_VARIANTS = ["India", "INDIA", "india ", "IN", "Bharat"]


def format_phone(rng: np.random.Generator, national_10digit: str, noncanonical_rate: float) -> str:
    if rng.random() < noncanonical_rate:
        fmt = PHONE_FORMATTERS[int(rng.integers(0, len(PHONE_FORMATTERS)))]
        return fmt(national_10digit)
    return f"+91{national_10digit}"


def format_country(rng: np.random.Generator, canonical: str, variant_rate: float) -> str:
    if canonical == "IN" and rng.random() < variant_rate:
        return str(rng.choice(COUNTRY_VARIANTS))
    return canonical


def noise_case_whitespace(rng: np.random.Generator, value: str, rate: float) -> str:
    if not value or rng.random() >= rate:
        return value
    choice = rng.integers(0, 3)
    if choice == 0:
        return f"  {value.upper()} "
    if choice == 1:
        return value.lower()
    return f" {value} "


def ts_iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def ts_variant(rng: np.random.Generator, dt: datetime, mixed_rate: float) -> str:
    if rng.random() >= mixed_rate:
        return ts_iso(dt)
    choice = int(rng.integers(0, 3))
    if choice == 0:
        return dt.strftime("%d-%m-%Y %H:%M")
    if choice == 1:
        return dt.strftime("%d/%m/%Y %H:%M")
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def date_ddmmyyyy(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def numeric_as_string(rng: np.random.Generator, value: float, rate: float) -> str:
    if rng.random() < rate:
        return f"{value:,.2f}"
    return f"{value:.2f}"
