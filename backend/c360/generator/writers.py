"""Projection of the population model to the nine source-system files (§4).

Defects from §4.9 are injected here, last, onto otherwise-coherent data
(§5.2), and every injection increments the shared :class:`DefectTracker`.
"""
from __future__ import annotations

import csv
import gzip
import json
import os
from datetime import date, datetime
from pathlib import Path

import numpy as np

from .catalogue import Product
from .commerce import Order
from .defects import DefectTracker
from .format_utils import (date_ddmmyyyy, format_country, format_phone,
                            noise_case_whitespace, numeric_as_string, ts_iso,
                            ts_variant)
from .population import Person
from .support_marketing import MarketingEvent, Ticket
from .behaviour import WebEvent


def _maybe_invalid_email(rng: np.random.Generator, email: str, tracker: DefectTracker) -> str:
    tracker.note_applicable("X-02")
    if rng.random() < tracker.rate("X-02"):
        tracker.record("X-02")
        choice = int(rng.integers(0, 3))
        if choice == 0:
            return email.replace("@", "@@", 1)
        if choice == 1:
            return email.replace("@", "", 1)
        return email.replace("@", " @", 1)
    return email


def write_customers_crm(path: Path, people: list[Person], rng: np.random.Generator, tracker: DefectTracker) -> int:
    rows_written = 0
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["crm_customer_id", "first_name", "last_name", "email", "phone",
                    "date_of_birth", "gender", "city", "state", "country", "postal_code",
                    "account_status", "signup_channel", "created_at", "updated_at"])
        seq = 1
        for person in people:
            if not person.in_crm:
                continue
            n_copies = 1
            tracker.note_applicable("X-07")
            if rng.random() < tracker.rate("X-07"):
                n_copies = 2
                tracker.record("X-07")
            for copy_idx in range(n_copies):
                crm_id = f"C{seq:06d}"
                seq += 1
                email = person.email_primary if copy_idx == 0 else (person.email_secondary or person.email_primary)
                tracker.note_applicable("X-01")
                if rng.random() < tracker.rate("X-01"):
                    email = ""
                    tracker.record("X-01")
                elif rng.random() < tracker.rate("X-06"):
                    tracker.note_applicable("X-06")
                    tracker.record("X-06")
                    email = "noreply@" + email.split("@", 1)[1]
                elif email:
                    email = _maybe_invalid_email(rng, email, tracker)

                tracker.note_applicable("X-03")
                phone = format_phone(rng, person.phone, tracker.rate("X-03"))
                tracker.note_applicable("X-04")
                if rng.random() < tracker.rate("X-04"):
                    phone = phone + " ext 12"
                    tracker.record("X-04")

                dob = person.date_of_birth
                dob_str = dob.isoformat()
                tracker.note_applicable("X-15")
                if rng.random() < tracker.rate("X-15"):
                    dob_str = f"{dob.year}-02-31"
                    tracker.record("X-15")

                gender = noise_case_whitespace(rng, person.gender, tracker.rate("X-12"))
                country = format_country(rng, person.country, tracker.rate("X-11"))
                first_name = noise_case_whitespace(rng, person.first_name, tracker.rate("X-12"))
                status = noise_case_whitespace(rng, "active", tracker.rate("X-12"))

                w.writerow([crm_id, first_name, person.last_name, email, phone, dob_str,
                            gender, person.city, person.state, country, person.postal_code,
                            status, rng.choice(["web", "store", "partner", "import"]),
                            ts_iso(datetime.combine(person.tenure_start, datetime.min.time())),
                            ts_iso(datetime.combine(person.tenure_start, datetime.min.time()))])
                rows_written += 1
    return rows_written


def write_loyalty(path: Path, people: list[Person], rng: np.random.Generator, tracker: DefectTracker) -> int:
    rows_written = 0
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["loyalty_id", "member_name", "mobile", "email_address", "tier",
                    "points_balance", "enrolled_on", "home_store", "city", "country_code",
                    "last_updated"])
        seq = 1
        for person in people:
            if not person.in_loyalty:
                continue
            loyalty_id = f"L{seq:08d}"
            seq += 1
            email = "" if rng.random() < 0.45 else person.email_primary
            tracker.note_applicable("X-03")
            mobile = format_phone(rng, person.phone, tracker.rate("X-03")).lstrip("+")

            tracker.note_applicable("X-05")
            if rng.random() < tracker.rate("X-05"):
                mobile = "0000000000"
                tracker.record("X-05")

            points = int(rng.integers(0, 5000))
            tracker.note_applicable("X-14")
            if rng.random() < tracker.rate("X-14"):
                points = -abs(points) or -15
                tracker.record("X-14")

            name = f"{person.first_name} {person.last_name}"
            name = noise_case_whitespace(rng, name, tracker.rate("X-12"))
            country = format_country(rng, person.country, tracker.rate("X-11"))

            w.writerow([loyalty_id, name, mobile, email,
                        rng.choice(["bronze", "silver", "gold", "platinum"]), points,
                        date_ddmmyyyy(person.tenure_start), f"{person.city[:3].upper()}-01",
                        person.city, country,
                        datetime.combine(person.tenure_start, datetime.min.time()).strftime("%d/%m/%Y %H:%M")])
            rows_written += 1
    return rows_written


def write_app_users(path: Path, people: list[Person], rng: np.random.Generator, tracker: DefectTracker) -> int:
    rows_written = 0
    with open(path, "w", encoding="utf-8") as fh:
        for person in people:
            if not person.in_app:
                continue
            app_user_id = f"U{person.true_person_id[3:]}"
            email = person.email_primary
            if rng.random() < 0.15 and person.email_secondary:
                local, domain = email.split("@")
                email = f"{local}+shop@{domain}"

            tracker.note_applicable("X-06")
            if rng.random() < tracker.rate("X-06"):
                email = "info@partner-example.com"
                tracker.record("X-06")

            phone = None
            if rng.random() < 0.35:
                tracker.note_applicable("X-03")
                phone = format_phone(rng, person.phone, tracker.rate("X-03"))

            signup_ts = datetime.combine(person.tenure_start, datetime.min.time())
            last_login = signup_ts
            tracker.note_applicable("X-16")
            if rng.random() < tracker.rate("X-16"):
                last_login = datetime(2027, 1, 1)
                tracker.record("X-16")

            record = {
                "app_user_id": app_user_id,
                "email": email,
                "display_name": person.first_name,
                "phone": phone,
                "phone_verified": rng.choice(["Y", "N", "true", "1", ""]),
                "locale": rng.choice(["en-IN", "en_IN", "en", "EN-in"]),
                "signup_ts": ts_iso(signup_ts),
                "marketing_opt_in": rng.choice(["true", "1", "", "false"]) if person.opt_in else "false",
                "last_login_ts": ts_iso(last_login),
                "device_cookies": person.device_cookies,
            }
            tracker.note_applicable("X-32")
            if rng.random() < tracker.rate("X-32"):
                fh.write("{not valid json,,,\n")
                tracker.record("X-32")
                continue
            fh.write(json.dumps(record) + "\n")
            rows_written += 1
    return rows_written


def write_products(path: Path, products: list[Product], rng: np.random.Generator, tracker: DefectTracker) -> int:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["product_id", "sku", "product_name", "category_id", "category_name",
                    "brand", "unit_price", "currency", "is_active", "stock_qty", "launched_on"])
        seen_categories: dict[str, str] = {}
        inconsistent_budget = 2
        for i, p in enumerate(products):
            sku = p.sku
            tracker.note_applicable("X-27")
            if i > 0 and rng.random() < tracker.rate("X-27"):
                sku = products[i - 1].sku
                tracker.record("X-27")

            price_str = str(p.unit_price)
            tracker.note_applicable("X-13")
            if rng.random() < tracker.rate("X-13"):
                price_str = numeric_as_string(rng, p.unit_price, 1.0)
                tracker.record("X-13")
            tracker.note_applicable("X-14")
            if rng.random() < tracker.rate("X-14"):
                price_str = str(-abs(p.unit_price))
                tracker.record("X-14")

            currency = p.currency
            tracker.note_applicable("X-31")
            if rng.random() < tracker.rate("X-31"):
                currency = "XYZ"
                tracker.record("X-31")

            category_name = p.category_name
            if (inconsistent_budget > 0 and tracker.rate("X-28") > 0
                    and p.category_id in seen_categories and rng.random() < 0.5):
                category_name = category_name.upper()
                tracker.record("X-28")
                inconsistent_budget -= 1
            seen_categories[p.category_id] = p.category_name

            brand = noise_case_whitespace(rng, p.brand, tracker.rate("X-12"))
            w.writerow([p.product_id, sku, p.product_name, p.category_id, category_name,
                        brand, price_str, currency, str(p.is_active).lower(),
                        p.stock_qty, p.launched_on.isoformat()])
    return len(products)


def _customer_ref(rng: np.random.Generator, order: Order, people_by_id: dict[str, Person], tracker: DefectTracker) -> tuple[str | None, str | None]:
    if order.true_person_id is None:
        return None, None
    person = people_by_id[order.true_person_id]
    kind = order.customer_ref_kind
    if kind == "crm_id" and person.in_crm:
        return f"C{int(order.true_person_id[3:]) % 999999:06d}", "crm_id"
    if kind == "app_user_id" and person.in_app:
        return f"U{person.true_person_id[3:]}", "app_user_id"
    return person.email_primary, "email"


def write_orders_and_items(orders_path: Path, items_path: Path, orders: list[Order],
                            people_by_id: dict[str, Person], products: list[Product],
                            rng: np.random.Generator, tracker: DefectTracker) -> tuple[int, int]:
    product_ids = [p.product_id for p in products]
    n_written = 0
    n_items_written = 0

    with open(orders_path, "w", encoding="utf-8") as ofh, \
         open(items_path, "w", newline="", encoding="utf-8") as ifh:
        item_writer = csv.writer(ifh)
        item_writer.writerow(["order_id", "line_number", "product_id", "quantity", "unit_price", "line_discount"])

        for order in orders:
            ref, ref_type = _customer_ref(rng, order, people_by_id, tracker)
            tracker.note_applicable("X-35")
            if ref is None:
                tracker.record("X-35")

            ts_str = ts_variant(rng, order.order_ts, tracker.rate("X-18"))
            tracker.note_applicable("X-18")

            tracker.note_applicable("X-17")
            if rng.random() < tracker.rate("X-17"):
                ts_str = ts_iso(datetime(1970, 1, 1))
                tracker.record("X-17")

            gross_str = str(order.gross_amount)
            tracker.note_applicable("X-13")
            if rng.random() < tracker.rate("X-13"):
                gross_str = numeric_as_string(rng, order.gross_amount, 1.0)
                tracker.record("X-13")

            status = order.order_status
            if rng.random() < 0.1:
                status = status.upper()

            record = {
                "order_id": order.order_id, "customer_ref": ref, "customer_ref_type": ref_type,
                "order_ts": ts_str, "order_status": status, "order_type": order.order_type,
                "currency": order.currency, "gross_amount": gross_str,
                "discount_amount": order.discount_amount, "shipping_amount": order.shipping_amount,
                "tax_amount": order.tax_amount, "payment_method": order.payment_method,
                "channel": order.channel, "ship_country": format_country(rng, order.ship_country, tracker.rate("X-11")),
                "updated_at": ts_iso(order.updated_at),
            }
            ofh.write(json.dumps(record) + "\n")
            n_written += 1
            tracker.note_applicable("X-19")
            if rng.random() < tracker.rate("X-19"):
                ofh.write(json.dumps(record) + "\n")  # exact duplicate delivery
                tracker.record("X-19")
                n_written += 1

            tracker.note_applicable("X-26")
            skip_items = rng.random() < tracker.rate("X-26")
            if skip_items:
                tracker.record("X-26")
                continue

            for item in order.items:
                product_id = item.product_id
                tracker.note_applicable("X-25")
                if rng.random() < tracker.rate("X-25"):
                    product_id = "P999999"
                    tracker.record("X-25")
                qty = item.quantity
                tracker.note_applicable("X-14")
                if rng.random() < tracker.rate("X-14"):
                    qty = 0
                    tracker.record("X-14")
                item_writer.writerow([order.order_id, item.line_number, product_id, qty,
                                       item.unit_price, item.line_discount])
                n_items_written += 1

            tracker.note_applicable("X-24")
            if rng.random() < tracker.rate("X-24"):
                item_writer.writerow([f"O_ORPHAN_{order.order_id}", 1, product_ids[0], 1, 10.0, 0.0])
                tracker.record("X-24")
                n_items_written += 1

    return n_written, n_items_written


def write_web_events(root: Path, events: list[WebEvent], rng: np.random.Generator, tracker: DefectTracker, shards: int = 1) -> int:
    root.mkdir(parents=True, exist_ok=True)
    by_date: dict[str, list[WebEvent]] = {}
    for e in events:
        by_date.setdefault(e.event_ts.date().isoformat(), []).append(e)

    n_written = 0
    seen_event_ids: set[str] = set()
    for dt_str, day_events in by_date.items():
        part_dir = root / f"dt={dt_str}"
        part_dir.mkdir(parents=True, exist_ok=True)
        shard_files = [gzip.open(part_dir / f"part-{s:03d}.jsonl.gz", "wt", encoding="utf-8") for s in range(max(shards, 1))]
        try:
            for i, e in enumerate(day_events):
                fh = shard_files[i % len(shard_files)]
                event_id = e.event_id
                tracker.note_applicable("X-23")
                if rng.random() < tracker.rate("X-23"):
                    event_id = None
                    tracker.record("X-23")

                event_type = e.event_type
                tracker.note_applicable("X-29")
                if rng.random() < tracker.rate("X-29"):
                    event_type = {"page_view": "pageView", "product_view": "PRODUCT_VIEW"}.get(event_type, "wishlist_add")
                    tracker.record("X-29")

                ua = e.user_agent
                tracker.note_applicable("X-33")
                if rng.random() < tracker.rate("X-33"):
                    ua = "python-requests/2.31"
                    tracker.record("X-33")

                record = {
                    "event_id": event_id, "event_type": event_type, "event_ts": ts_iso(e.event_ts),
                    "app_user_id": e.app_user_id, "device_cookie": e.device_cookie,
                    "session_hint": e.session_hint, "page_url": e.page_url, "referrer": None,
                    "product_id": e.product_id, "search_term": e.search_term, "cart_value": e.cart_value,
                    "utm_source": e.utm_source, "utm_medium": e.utm_medium, "utm_campaign": e.utm_campaign,
                    "device_type": e.device_type, "country": format_country(rng, e.country, tracker.rate("X-11")),
                    "user_agent": ua,
                }
                fh.write(json.dumps(record) + "\n")
                n_written += 1

                tracker.note_applicable("X-22")
                if event_id and event_id not in seen_event_ids and rng.random() < tracker.rate("X-22"):
                    fh.write(json.dumps(record) + "\n")  # duplicate delivery
                    tracker.record("X-22")
                    n_written += 1
                if event_id:
                    seen_event_ids.add(event_id)
        finally:
            for fh in shard_files:
                fh.close()
    return n_written


def write_tickets(path: Path, tickets: list[Ticket], rng: np.random.Generator, tracker: DefectTracker) -> int:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["ticket_id", "requester_email", "subject", "category", "priority", "status",
                    "created_at", "first_response_at", "resolved_at", "satisfaction_score", "order_id"])
        for t in tickets:
            email = t.requester_email
            tracker.note_applicable("X-02")
            if rng.random() < tracker.rate("X-02") / 2:
                email = email.replace("@", "@@", 1)
                tracker.record("X-02")

            first_response = t.first_response_at
            tracker.note_applicable("X-30")
            if first_response and rng.random() < tracker.rate("X-30"):
                first_response = t.created_at.replace(hour=max(t.created_at.hour - 2, 0))
                tracker.record("X-30")

            score = t.satisfaction_score
            tracker.note_applicable("X-34")
            if score is not None and rng.random() < tracker.rate("X-34"):
                score = rng.choice([0, 7])
                tracker.record("X-34")

            w.writerow([t.ticket_id, email, t.subject, t.category, t.priority, t.status,
                        ts_iso(t.created_at), ts_iso(first_response) if first_response else "",
                        ts_iso(t.resolved_at) if t.resolved_at else "", score if score is not None else "",
                        t.order_id or ""])
    return len(tickets)


def write_marketing(path: Path, events: list[MarketingEvent], rng: np.random.Generator, tracker: DefectTracker) -> int:
    with open(path, "w", encoding="utf-8") as fh:
        for e in events:
            record = {
                "campaign_id": e.campaign_id, "campaign_name": e.campaign_name, "channel": e.channel,
                "recipient_email": e.recipient_email, "event_type": e.event_type,
                "event_ts": ts_iso(e.event_ts), "link_url": e.link_url, "product_id": e.product_id,
            }
            fh.write(json.dumps(record) + "\n")
    return len(events)
