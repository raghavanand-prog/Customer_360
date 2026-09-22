"""Product catalogue generation (§4.5, §5.2 step 4)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np

from .vocab import BRANDS, CATEGORY_NAMES, PRODUCT_NOUNS


@dataclass
class Product:
    product_id: str
    sku: str
    product_name: str
    category_id: str
    category_name: str
    brand: str
    unit_price: float
    currency: str
    is_active: bool
    stock_qty: int
    launched_on: date


def generate_catalogue(rng: np.random.Generator, n_products: int, date_range_start: date, date_range_end: date) -> list[Product]:
    category_ids = {name: f"CAT{idx + 1:03d}" for idx, name in enumerate(CATEGORY_NAMES)}
    products: list[Product] = []
    total_days = (date_range_end - date_range_start).days

    for i in range(n_products):
        category_name = rng.choice(CATEGORY_NAMES)
        category_id = category_ids[category_name]
        noun = rng.choice(PRODUCT_NOUNS[category_name])
        brand = rng.choice(BRANDS)
        # log-normal price so the catalogue has a realistic long tail
        price = float(np.round(np.exp(rng.normal(7.0, 0.9)), 2))
        launched = date_range_start + timedelta(days=int(rng.integers(0, max(total_days, 1))))
        products.append(Product(
            product_id=f"P{i + 1:06d}",
            sku=f"SKU-{category_id[3:]}-{i % 999 + 1:03d}",
            product_name=f"{noun} {brand if rng.random() < 0.3 else ''}".strip(),
            category_id=category_id,
            category_name=category_name,
            brand=brand,
            unit_price=price,
            currency="INR",
            is_active=bool(rng.random() < 0.9),
            stock_qty=int(rng.integers(0, 500)),
            launched_on=launched,
        ))
    return products


def category_popularity_index(rng: np.random.Generator, products: list[Product]) -> dict[str, list[tuple[Product, float]]]:
    """Zipf-weighted in-category popularity, so product choice has signal."""
    by_cat: dict[str, list[Product]] = {}
    for p in products:
        by_cat.setdefault(p.category_id, []).append(p)
    result: dict[str, list[tuple[Product, float]]] = {}
    for cat, plist in by_cat.items():
        ranks = np.arange(1, len(plist) + 1)
        weights = 1.0 / ranks
        weights = weights / weights.sum()
        result[cat] = list(zip(plist, weights.tolist()))
    return result
