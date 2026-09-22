"""Support tickets and marketing events (§5.2 steps 7-8, §4.8, §5.5 items 9-10)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

import numpy as np

from .commerce import Order
from .population import Person
from .vocab import CAMPAIGN_NAMES, TICKET_SUBJECTS


@dataclass
class Ticket:
    ticket_id: str
    requester_email: str
    subject: str
    category: str
    priority: str
    status: str
    created_at: datetime
    first_response_at: datetime | None
    resolved_at: datetime | None
    satisfaction_score: int | None
    order_id: str | None


@dataclass
class MarketingEvent:
    campaign_id: str
    campaign_name: str
    channel: str
    recipient_email: str
    event_type: str
    event_ts: datetime
    link_url: str | None
    product_id: str | None


def generate_tickets(rng: np.random.Generator, people: list[Person], orders_by_person: dict[str, list[Order]]) -> list[Ticket]:
    tickets: list[Ticket] = []
    seq = 1
    for person in people:
        person_orders = orders_by_person.get(person.true_person_id, [])
        # tickets conditioned on orders: delivery/refund require a related order
        for order in person_orders:
            if rng.random() < 0.06:
                category = rng.choice(["delivery", "refund", "product_quality", "payment", "account", "other"],
                                       p=[0.3, 0.2, 0.2, 0.1, 0.1, 0.1])
                created = order.order_ts + timedelta(days=int(rng.integers(0, 10)))
                resolution_hours = float(rng.lognormal(3.0, 0.6))
                first_response = created + timedelta(hours=float(rng.uniform(0.5, 6)))
                resolved = created + timedelta(hours=resolution_hours) if rng.random() < 0.85 else None
                score = None
                status = "open"
                if resolved:
                    status = "resolved"
                    score = int(np.clip(round(rng.normal(4.2 - resolution_hours / 100, 1.0)), 1, 5))
                tickets.append(Ticket(
                    ticket_id=f"T{seq:08d}", requester_email=person.email_primary,
                    subject=str(rng.choice(TICKET_SUBJECTS[category])), category=category,
                    priority=str(rng.choice(["low", "medium", "high", "urgent"], p=[0.4, 0.35, 0.2, 0.05])),
                    status=status, created_at=created, first_response_at=first_response,
                    resolved_at=resolved, satisfaction_score=score,
                    order_id=order.order_id if category in ("delivery", "refund") else None,
                ))
                seq += 1
    return tickets


def generate_marketing(rng: np.random.Generator, people: list[Person], date_range_start: date, date_range_end: date) -> list[MarketingEvent]:
    events: list[MarketingEvent] = []
    opted_in = [p for p in people if p.opt_in]

    # a "list" population not present in other sources — some recipients are
    # unattributable to any known customer, a real and instructive case.
    list_only_emails = [f"subscriber{n}@example.net" for n in range(max(1, len(people) // 20))]

    total_days = (date_range_end - date_range_start).days
    n_campaigns = max(1, total_days // 30)
    for c in range(n_campaigns):
        campaign_id = f"CMP{c + 1:05d}"
        campaign_name = str(rng.choice(CAMPAIGN_NAMES))
        channel = str(rng.choice(["email", "push", "sms"], p=[0.7, 0.2, 0.1]))
        send_date = date_range_start + timedelta(days=int(c * (total_days / max(n_campaigns, 1))))
        send_ts = datetime.combine(send_date, datetime.min.time()) + timedelta(hours=10)

        recipients = list(rng.choice([p.email_primary for p in opted_in],
                                      size=min(len(opted_in), max(50, len(opted_in) // 3)), replace=False))
        recipients += list(rng.choice(list_only_emails, size=min(len(list_only_emails), 20), replace=False)) if list_only_emails else []

        for email in recipients:
            events.append(MarketingEvent(campaign_id, campaign_name, channel, email, "sent", send_ts, None, None))
            if rng.random() < 0.6:
                events.append(MarketingEvent(campaign_id, campaign_name, channel, email, "delivered",
                                              send_ts + timedelta(minutes=1), None, None))
            if rng.random() < 0.35:
                open_ts = send_ts + timedelta(hours=float(rng.uniform(0.1, 48)))
                events.append(MarketingEvent(campaign_id, campaign_name, channel, email, "open", open_ts, None, None))
                if rng.random() < 0.25:
                    events.append(MarketingEvent(campaign_id, campaign_name, channel, email, "click",
                                                  open_ts + timedelta(minutes=float(rng.uniform(0.5, 20))),
                                                  "https://example.com/promo", None))
            if rng.random() < 0.02:
                events.append(MarketingEvent(campaign_id, campaign_name, channel, email, "unsubscribe",
                                              send_ts + timedelta(days=1), None, None))
    return events
