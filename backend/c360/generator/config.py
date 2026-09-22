"""Generator configuration: size profiles, archetypes, defect rates.

All numbers here are the *configured* rates from PROJECT_PLAN.md §4.9 and
§5.3/§5.4. Realised rates are measured at generation time and written to
``manifest.json`` -- this module never claims a realised outcome, only a
target.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SizeProfile:
    name: str
    persons: int
    products: int


SIZE_PROFILES: dict[str, SizeProfile] = {
    "tiny": SizeProfile("tiny", 200, 50),
    "small": SizeProfile("small", 1_000, 500),
    "medium": SizeProfile("medium", 50_000, 5_000),
    "large": SizeProfile("large", 500_000, 20_000),
}

# Behaviour archetypes: §5.4. orders/yr is a (min, max) used to parameterise
# a negative-binomial draw's mean; session_rate is sessions/month mean.
ARCHETYPES: dict[str, dict] = {
    "loyal_high_value": {
        "share": 0.06, "orders_per_year": (8, 20), "session_rate": 12.0,
        "spend_multiplier": 3.5, "churns": False,
    },
    "regular": {
        "share": 0.24, "orders_per_year": (2, 5), "session_rate": 4.0,
        "spend_multiplier": 1.5, "churns": False,
    },
    "occasional": {
        "share": 0.34, "orders_per_year": (0.5, 2), "session_rate": 1.5,
        "spend_multiplier": 1.0, "churns": False,
    },
    "browser_no_buy": {
        "share": 0.18, "orders_per_year": (0, 0), "session_rate": 5.0,
        "spend_multiplier": 0.0, "churns": False,
    },
    "churned": {
        "share": 0.12, "orders_per_year": (1, 3), "session_rate": 2.0,
        "spend_multiplier": 1.0, "churns": True,
    },
    "new_recent": {
        "share": 0.05, "orders_per_year": (0, 2), "session_rate": 3.0,
        "spend_multiplier": 1.0, "churns": False,
    },
    "bot_like": {
        "share": 0.01, "orders_per_year": (0, 0), "session_rate": 200.0,
        "spend_multiplier": 0.0, "churns": False,
    },
}

# Defect injection rates, keyed by defect ID -- §4.9.
DEFECT_RATES: dict[str, float] = {
    "X-01": 0.06,   # missing email (D-01)
    "X-02": 0.03,   # invalid email syntax
    "X-03": 0.35,   # non-canonical phone format
    "X-04": 0.02,   # unnormalisable phone
    "X-05": 0.005,  # sentinel phone
    "X-06": 0.008,  # generic/role email
    "X-07": 0.04,   # within-source duplicate person
    "X-08": 0.08,   # cross-source duplicate person
    "X-09": 0.006,  # shared phone, 2 distinct persons
    "X-10": 5,      # fixed count of high-frequency shared identifiers
    "X-11": 0.25,   # country spelling variants
    "X-12": 0.20,   # casing/whitespace noise
    "X-13": 0.03,   # numeric-as-formatted-string
    "X-14": 0.01,   # negative/zero where positive required
    "X-15": 0.01,   # impossible date
    "X-16": 0.005,  # timestamp in the future
    "X-17": 0.003,  # epoch-0 / implausibly old timestamp
    "X-18": 0.10,   # mixed timestamp formats
    "X-19": 0.015,  # duplicate order (exact)
    "X-20": 0.003,  # suspected duplicate order
    "X-21": 0.002,  # legitimate repeat purchase (must survive dedup)
    "X-22": 0.02,   # duplicate web event (event_id twice)
    "X-23": 0.02,   # null event_id
    "X-24": 0.005,  # orphan order_id in items
    "X-25": 0.01,   # unknown product_id
    "X-26": 0.004,  # order with no items
    "X-27": 0.004,  # duplicate SKU
    "X-28": 2,      # fixed count category_name inconsistency
    "X-29": 0.01,   # unmapped event type/enum
    "X-30": 0.005,  # temporal anomaly
    "X-31": 0.002,  # unknown currency code
    "X-32": 0.001,  # malformed json / wrong csv column count
    "X-33": 0.01,   # bot traffic share of events
    "X-34": 0.01,   # out-of-range satisfaction score
    "X-35": 0.04,   # guest order, no usable identifier
}

EVENT_TYPE_WEIGHTS = {
    "page_view": 0.45, "product_view": 0.25, "search": 0.10,
    "add_to_cart": 0.08, "remove_from_cart": 0.03, "checkout_start": 0.05,
    "purchase": 0.04,
}

GENERATOR_VERSION = "1.0.0"
DEFAULT_COUNTRY_CODE = "+91"
CURRENCY = "INR"
REPORTING_CURRENCY = "INR"
