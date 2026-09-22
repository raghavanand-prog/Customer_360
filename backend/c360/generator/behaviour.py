"""Session + web event synthesis (§5.2 step 6, §5.5 items 6-8)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

import numpy as np

from .catalogue import Product, category_popularity_index
from .commerce import Order
from .config import ARCHETYPES, EVENT_TYPE_WEIGHTS
from .population import Person


@dataclass
class WebEvent:
    event_id: str | None
    event_type: str
    event_ts: datetime
    app_user_id: str | None
    device_cookie: str
    session_hint: str
    page_url: str
    product_id: str | None
    search_term: str | None
    cart_value: float | None
    utm_source: str | None
    utm_medium: str | None
    utm_campaign: str | None
    device_type: str
    country: str
    user_agent: str


UTM_SOURCES = [("google", "cpc"), ("facebook", "cpc"), ("newsletter", "email"),
               (None, None), (None, None)]
DEVICE_TYPES = ["mobile", "desktop", "tablet"]


def generate_events(
    rng: np.random.Generator,
    people: list[Person],
    products: list[Product],
    orders_by_person: dict[str, list[Order]],
    date_range_end: date,
) -> list[WebEvent]:
    pop_index = category_popularity_index(rng, products)
    events: list[WebEvent] = []
    event_seq = 0

    for person in people:
        archetype = ARCHETYPES[person.archetype]
        session_rate = archetype["session_rate"]
        active_end = date_range_end
        if person.churn_cutoff:
            active_end = min(active_end, person.churn_cutoff)
        active_days = max((active_end - person.tenure_start).days, 1)
        n_active_days_with_sessions = int(np.clip(rng.poisson(active_days * min(session_rate / 30.0, 1.0)), 0, active_days))
        if n_active_days_with_sessions == 0:
            continue

        session_days = rng.choice(active_days, size=n_active_days_with_sessions, replace=False)
        person_orders = orders_by_person.get(person.true_person_id, [])

        for day_offset in session_days:
            session_day = person.tenure_start + timedelta(days=int(day_offset))
            n_sessions_today = int(np.clip(rng.poisson(1.1), 1, 5))
            for _ in range(n_sessions_today):
                start_hour = int(rng.integers(6, 23))
                session_start = datetime.combine(session_day, datetime.min.time()) + timedelta(
                    hours=start_hour, minutes=int(rng.integers(0, 60)))
                n_events = int(np.clip(rng.geometric(0.35), 1, 25))
                cookie = rng.choice(person.device_cookies)
                device_type = rng.choice(DEVICE_TYPES, p=[0.6, 0.3, 0.1])
                utm_source, utm_medium = UTM_SOURCES[int(rng.integers(0, len(UTM_SOURCES)))]
                session_hint = f"s_{person.true_person_id}_{int(day_offset)}"
                cur_ts = session_start
                will_purchase = any(abs((o.order_ts - session_start).total_seconds()) < 3 * 3600
                                     for o in person_orders if o.order_ts.date() == session_day)

                for e in range(n_events):
                    cur_ts += timedelta(seconds=float(rng.lognormal(3.2, 0.8)))
                    if e == n_events - 1 and will_purchase:
                        etype = "purchase"
                    else:
                        types = list(EVENT_TYPE_WEIGHTS.keys())
                        weights = np.array(list(EVENT_TYPE_WEIGHTS.values()))
                        etype = rng.choice(types, p=weights / weights.sum())

                    product_id = None
                    if etype in ("product_view", "add_to_cart", "remove_from_cart", "purchase"):
                        cats = list(person.category_affinity.keys())
                        weights_c = np.array(list(person.category_affinity.values()))
                        cat_name = rng.choice(cats, p=weights_c / weights_c.sum())
                        cat_id = next((p.category_id for p in products if p.category_name == cat_name), None)
                        if cat_id in pop_index:
                            candidates = pop_index[cat_id]
                            prods = [c[0] for c in candidates]
                            probs = np.array([c[1] for c in candidates])
                            product_id = rng.choice(prods, p=probs / probs.sum()).product_id

                    event_seq += 1
                    is_app_user = person.in_app and rng.random() < 0.6
                    events.append(WebEvent(
                        event_id=f"evt_{event_seq:012d}",
                        event_type=etype,
                        event_ts=cur_ts,
                        app_user_id=f"U{person.true_person_id[3:]}" if is_app_user else None,
                        device_cookie=cookie,
                        session_hint=session_hint,
                        page_url=f"/p/{product_id}" if product_id else "/",
                        product_id=product_id,
                        search_term="wireless earbuds" if etype == "search" else None,
                        cart_value=round(float(rng.uniform(200, 5000)), 2) if etype in ("add_to_cart", "checkout_start") else None,
                        utm_source=utm_source,
                        utm_medium=utm_medium,
                        utm_campaign="audio_sep" if utm_source else None,
                        device_type=str(device_type),
                        country="IN",
                        user_agent="Mozilla/5.0 (compatible; c360-sim)",
                    ))

    # bot-like archetype and anonymous browsing volume, so the event stream
    # isn't purely attributable traffic (§5.5 item 8: ~40% anonymous).
    n_anon = int(len(events) * 0.4)
    anon_cookies = [f"ck_anon_{i}" for i in range(max(1, n_anon // 20))]
    for i in range(n_anon):
        ts = datetime.combine(date_range_end, datetime.min.time()) - timedelta(days=int(rng.integers(0, 365)),
                                                                                  hours=int(rng.integers(0, 24)))
        event_seq += 1
        events.append(WebEvent(
            event_id=f"evt_{event_seq:012d}",
            event_type=rng.choice(["page_view", "product_view", "search"], p=[0.6, 0.3, 0.1]),
            event_ts=ts, app_user_id=None, device_cookie=rng.choice(anon_cookies),
            session_hint=f"s_anon_{i}", page_url="/", product_id=None, search_term=None,
            cart_value=None, utm_source=None, utm_medium=None, utm_campaign=None,
            device_type=str(rng.choice(DEVICE_TYPES)), country="IN",
            user_agent="Mozilla/5.0 (compatible; c360-sim-anon)",
        ))

    events.sort(key=lambda e: e.event_ts)
    return events
