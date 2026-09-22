"""Generator orchestration and Typer CLI (§5.2, §5.6, §5.7)."""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import typer

from . import catalogue, commerce, support_marketing, writers
from .behaviour import generate_events
from .config import GENERATOR_VERSION, SIZE_PROFILES
from .defects import DefectTracker
from .population import Person, assign_source_presence, generate_population

app = typer.Typer(add_completion=False)


def _seed_household_and_switchboard(rng: np.random.Generator, people: list[Person], defect_profile: str) -> dict:
    """Injects X-09 (shared phone, 2 people) and X-10 (switchboard, 5 fixed values)."""
    stats = {"shared_phone_pairs": 0, "switchboard_values": 0}
    if defect_profile == "none":
        return stats
    n_pairs = max(1, int(len(people) * 0.006 / 2))
    eligible = [p for p in people if p.in_crm or p.in_loyalty]
    if len(eligible) >= 2 * n_pairs:
        idx = rng.choice(len(eligible), size=2 * n_pairs, replace=False)
        for k in range(n_pairs):
            a, b = eligible[idx[2 * k]], eligible[idx[2 * k + 1]]
            b.phone = a.phone
            a.shares_phone_with = b.true_person_id
            b.shares_phone_with = a.true_person_id
            stats["shared_phone_pairs"] += 1

    # 5 fixed switchboard numbers, each shared by 8+ records across sources
    switchboard_numbers = [f"9{d}00000{d}0" if len(f"9{d}00000{d}0") == 10 else "9000000001" for d in range(5)]
    switchboard_numbers = ["9000000001", "9000000002", "9000000003", "9000000004", "9000000005"]
    remaining = [p for p in people if p.shares_phone_with is None]
    per_group = min(10, max(8, len(remaining) // max(len(switchboard_numbers), 1) // 50 + 8))
    for i, number in enumerate(switchboard_numbers):
        if len(remaining) < per_group:
            break
        group = remaining[i * per_group:(i + 1) * per_group]
        for p in group:
            p.phone = number
        stats["switchboard_values"] += 1
    return stats


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_ground_truth(path: Path, records: list[tuple[str, str, str]]) -> None:
    """(source_system, source_record_id, true_person_id) rows.

    Written as Parquet when pyarrow is available (as specified), and as CSV
    otherwise so the generator remains usable without the optional
    dependency -- documented in docs/PROJECT_DECISIONS.md (ADR).
    """
    try:
        import pandas as pd
        df = pd.DataFrame(records, columns=["source_system", "source_record_id", "true_person_id"])
        df.to_parquet(path.with_suffix(".parquet"), index=False)
    except ImportError:
        import csv
        with open(path.with_suffix(".csv"), "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["source_system", "source_record_id", "true_person_id"])
            w.writerows(records)


@app.command()
def generate(
    seed: int = typer.Option(20260922, help="Root seed for PCG64."),
    size: str = typer.Option("small", help="tiny|small|medium|large"),
    out_dir: str = typer.Option("data", help="Root output directory."),
    shards: int = typer.Option(1, help="Parallel shard count for web events."),
    defect_profile: str = typer.Option("default", help="none|default|aggressive"),
    date_start: str = typer.Option(None, help="YYYY-MM-DD, default 3 years before today."),
    date_end: str = typer.Option(None, help="YYYY-MM-DD, default today."),
) -> None:
    if size not in SIZE_PROFILES:
        typer.echo(f"Unknown size profile: {size}", err=True)
        raise typer.Exit(1)
    profile = SIZE_PROFILES[size]

    end = date.fromisoformat(date_end) if date_end else date.today()
    start = date.fromisoformat(date_start) if date_start else end.replace(year=end.year - 3)

    root = Path(out_dir)
    input_dir = root / "input"
    generated_dir = root / "generated"
    if input_dir.exists():
        shutil.rmtree(input_dir)
    if generated_dir.exists():
        shutil.rmtree(generated_dir)
    input_dir.mkdir(parents=True)
    generated_dir.mkdir(parents=True)

    seed_seq = np.random.SeedSequence(seed)
    child_seeds = seed_seq.spawn(8)
    rngs = [np.random.Generator(np.random.PCG64(s)) for s in child_seeds]
    rng_pop, rng_cat, rng_ord, rng_evt, rng_tix, rng_mkt, rng_fmt, rng_house = rngs

    typer.echo(f"[generate] size={size} persons={profile.persons} seed={seed} defect_profile={defect_profile}")

    people = generate_population(rng_pop, profile.persons, start, end)
    assign_source_presence(rng_pop, people)
    household_stats = _seed_household_and_switchboard(rng_house, people, defect_profile)
    people_by_id = {p.true_person_id: p for p in people}

    products = catalogue.generate_catalogue(rng_cat, profile.products, start, end)

    guest_order_rate = 0.0 if defect_profile == "none" else 0.02
    orders = commerce.generate_orders(rng_ord, people, products, end, guest_order_rate=guest_order_rate)
    orders_by_person: dict[str, list] = {}
    for o in orders:
        if o.true_person_id:
            orders_by_person.setdefault(o.true_person_id, []).append(o)

    events = generate_events(rng_evt, people, products, orders_by_person, end)
    tickets = support_marketing.generate_tickets(rng_tix, people, orders_by_person)
    marketing = support_marketing.generate_marketing(rng_mkt, people, start, end)

    tracker = DefectTracker(defect_profile)

    n_crm, crm_id_map = writers.write_customers_crm(input_dir / "customers_crm.csv", people, rng_fmt, tracker)
    n_loy, loyalty_id_map = writers.write_loyalty(input_dir / "loyalty_members.csv", people, rng_fmt, tracker)
    n_app, app_id_map = writers.write_app_users(input_dir / "app_users.jsonl", people, rng_fmt, tracker)
    n_prod = writers.write_products(input_dir / "products.csv", products, rng_fmt, tracker)
    n_ord, n_items = writers.write_orders_and_items(
        input_dir / "orders.jsonl", input_dir / "order_items.csv", orders, people_by_id, products, rng_fmt, tracker)
    n_events = writers.write_web_events(input_dir / "web_events", events, rng_fmt, tracker, shards=shards)
    n_tix = writers.write_tickets(input_dir / "support_tickets.csv", tickets, rng_fmt, tracker)
    n_mkt = writers.write_marketing(input_dir / "marketing_events.jsonl", marketing, rng_fmt, tracker)

    # ground truth: only crm/loyalty/app source records carry a person identity;
    # orders/events/tickets/marketing are attributed via the person's identifiers
    # and are not independent identity-bearing source records.
    ground_truth: list[tuple[str, str, str]] = (
        [("crm", crm_id, true_id) for crm_id, true_id in crm_id_map]
        + [("loyalty", loy_id, true_id) for loy_id, true_id in loyalty_id_map]
        + [("app", app_id, true_id) for app_id, true_id in app_id_map]
    )
    _write_ground_truth(generated_dir / "ground_truth_identity", ground_truth)

    dataset_files = [
        ("D-01", "customers_crm.csv", n_crm),
        ("D-02", "loyalty_members.csv", n_loy),
        ("D-03", "app_users.jsonl", n_app),
        ("D-04", "products.csv", n_prod),
        ("D-05", "orders.jsonl", n_ord),
        ("D-06", "order_items.csv", n_items),
        ("D-07", "web_events/", n_events),
        ("D-08", "support_tickets.csv", n_tix),
        ("D-09", "marketing_events.jsonl", n_mkt),
    ]
    datasets_manifest = []
    for did, fname, rows in dataset_files:
        fpath = input_dir / fname
        digest = _sha256(fpath) if fpath.is_file() else "n/a-directory"
        size_bytes = fpath.stat().st_size if fpath.is_file() else sum(
            f.stat().st_size for f in fpath.rglob("*") if f.is_file())
        datasets_manifest.append({"id": did, "file": fname, "rows": rows, "bytes": size_bytes, "sha256": digest})

    cross_source_dup = tracker.realised.get("X-08", 0)
    manifest = {
        "generator_version": GENERATOR_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "size_profile": size,
        "date_range": {"start": start.isoformat(), "end": end.isoformat()},
        "python_version": sys.version.split()[0],
        "true_person_count": len(people),
        "datasets": datasets_manifest,
        "defects": tracker.to_manifest_section(),
        "expectations": {
            "within_source_duplicate_records": tracker.realised.get("X-07", 0),
            "shared_phone_person_pairs": household_stats["shared_phone_pairs"],
            "high_frequency_identifiers": household_stats["switchboard_values"],
            "purchase_event_order_reconciliation_rate": 1.0,
        },
        "archetype_counts": {a: sum(1 for p in people if p.archetype == a)
                              for a in {p.archetype for p in people}},
    }
    with open(generated_dir / "manifest.json", "w") as fh:
        json.dump(manifest, fh, indent=2, default=str)

    typer.echo(f"[generate] done. datasets written to {input_dir}, manifest at {generated_dir / 'manifest.json'}")


if __name__ == "__main__":
    app()
