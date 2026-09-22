"""Order / order-item generation: purchase process per person (§5.2 step 5, §5.5)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

import numpy as np

from .catalogue import Product, category_popularity_index
from .config import ARCHETYPES
from .population import Person

SEASONALITY = {1: 0.9, 2: 0.85, 3: 0.9, 4: 0.95, 5: 1.0, 6: 0.95, 7: 0.9,
               8: 0.95, 9: 1.05, 10: 1.3, 11: 1.35, 12: 1.1}


@dataclass
class OrderItem:
    order_id: str
    line_number: int
    product_id: str
    quantity: int
    unit_price: float
    line_discount: float


@dataclass
class Order:
    order_id: str
    true_person_id: str | None  # None => true guest, no identifiable key (X-35)
    customer_ref_kind: str  # "crm_id" | "app_user_id" | "email" | None
    order_ts: datetime
    order_status: str
    order_type: str
    currency: str
    gross_amount: float
    discount_amount: float
    shipping_amount: float
    tax_amount: float
    payment_method: str
    channel: str
    ship_country: str
    updated_at: datetime
    items: list[OrderItem] = field(default_factory=list)
    is_legitimate_repeat: bool = False


def _season_weight(d: date) -> float:
    return SEASONALITY[d.month] * (1.15 if d.weekday() >= 5 else 1.0)


def generate_orders(
    rng: np.random.Generator,
    people: list[Person],
    products: list[Product],
    date_range_end: date,
    guest_order_rate: float = 0.02,
) -> list[Order]:
    pop_index = category_popularity_index(rng, products)
    products_by_id = {p.product_id: p for p in products}
    orders: list[Order] = []
    order_seq = 1

    for person in people:
        archetype = ARCHETYPES[person.archetype]
        lo, hi = archetype["orders_per_year"]
        if hi <= 0:
            continue
        years_active = max((date_range_end - person.tenure_start).days / 365.0, 0.05)
        mean_orders = rng.uniform(lo, hi) * years_active
        if mean_orders <= 0:
            continue
        # negative-binomial via gamma-poisson mixture for over-dispersion
        shape = 2.0
        lam = rng.gamma(shape, mean_orders / shape)
        n_orders = int(rng.poisson(max(lam, 0.01)))
        if n_orders == 0:
            continue

        active_end = date_range_end
        if person.churn_cutoff:
            active_end = min(active_end, person.churn_cutoff)
        active_days = max((active_end - person.tenure_start).days, 1)

        order_days = sorted(rng.integers(0, active_days, size=n_orders).tolist())
        prev_order_day = None
        for k, day_offset in enumerate(order_days):
            order_date = person.tenure_start + timedelta(days=int(day_offset))
            if order_date > date_range_end:
                continue
            order_ts = datetime.combine(order_date, datetime.min.time()) + timedelta(
                hours=int(rng.integers(7, 23)), minutes=int(rng.integers(0, 60)))

            cats = list(person.category_affinity.keys())
            weights = np.array(list(person.category_affinity.values()))
            chosen_cat_name = rng.choice(cats, p=weights / weights.sum())
            cat_id = next((p.category_id for p in products if p.category_name == chosen_cat_name), None)
            if cat_id is None or cat_id not in pop_index:
                continue
            candidates = pop_index[cat_id]
            prods = [c[0] for c in candidates]
            probs = np.array([c[1] for c in candidates])

            n_items = int(np.clip(rng.poisson(1.3) + 1, 1, 6))
            chosen_products = rng.choice(prods, size=min(n_items, len(prods)), replace=False, p=probs / probs.sum())

            order_id = f"O{order_seq:010d}"
            order_seq += 1
            items = []
            gross = 0.0
            for line_no, prod in enumerate(np.atleast_1d(chosen_products), start=1):
                qty = int(np.clip(rng.poisson(1.2) + 1, 1, 5))
                unit_price = float(prod.unit_price)
                line_discount = round(unit_price * qty * rng.choice([0, 0, 0, 0.05, 0.1]), 2)
                items.append(OrderItem(order_id, line_no, prod.product_id, qty, unit_price, line_discount))
                gross += unit_price * qty

            discount = round(sum(i.line_discount for i in items), 2)
            shipping = 0.0 if gross > 999 else round(rng.uniform(29, 99), 2)
            tax = round((gross - discount) * 0.18, 2)

            status = rng.choice(
                ["delivered", "delivered", "delivered", "shipped", "cancelled", "refunded"],
                p=[0.55, 0.15, 0.1, 0.1, 0.05, 0.05])
            order_type = "refund" if status == "refunded" and rng.random() < 0.5 else "sale"

            is_repeat = False
            if prev_order_day is not None and day_offset - prev_order_day == 0 and rng.random() < 0.15:
                is_repeat = True  # legitimate same-day repeat purchase, must survive dedup (X-21)
            prev_order_day = day_offset

            channel = rng.choice(["web", "app", "store", "phone"], p=[0.4, 0.35, 0.2, 0.05])
            payment = rng.choice(["upi", "card", "cod", "netbanking", "wallet"])

            ref_kind = None
            if person.in_crm and rng.random() < 0.5:
                ref_kind = "crm_id"
            elif person.in_app and rng.random() < 0.7:
                ref_kind = "app_user_id"
            elif rng.random() < 0.85:
                ref_kind = "email"

            orders.append(Order(
                order_id=order_id,
                true_person_id=person.true_person_id,
                customer_ref_kind=ref_kind,
                order_ts=order_ts,
                order_status=status,
                order_type=order_type,
                currency="INR",
                gross_amount=round(gross, 2),
                discount_amount=discount,
                shipping_amount=shipping,
                tax_amount=tax,
                payment_method=payment,
                channel=channel,
                ship_country="IN",
                updated_at=order_ts + timedelta(hours=int(rng.integers(1, 48))),
                items=items,
                is_legitimate_repeat=is_repeat,
            ))

    # true guest orders with no identifiable person at all (X-35), a fixed
    # small share of order volume, generated independently of the population.
    n_guest = int(len(orders) * guest_order_rate)
    for _ in range(n_guest):
        order_id = f"O{order_seq:010d}"
        order_seq += 1
        prod = products[int(rng.integers(0, len(products)))]
        order_date = date_range_end - timedelta(days=int(rng.integers(0, 365)))
        order_ts = datetime.combine(order_date, datetime.min.time())
        orders.append(Order(
            order_id=order_id, true_person_id=None, customer_ref_kind=None,
            order_ts=order_ts, order_status="delivered", order_type="sale",
            currency="INR", gross_amount=prod.unit_price, discount_amount=0.0,
            shipping_amount=49.0, tax_amount=round(prod.unit_price * 0.18, 2),
            payment_method="cod", channel="store", ship_country="IN",
            updated_at=order_ts, items=[OrderItem(order_id, 1, prod.product_id, 1, prod.unit_price, 0.0)],
        ))

    return orders
