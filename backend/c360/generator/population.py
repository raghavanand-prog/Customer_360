"""Population model: §5.2 step 1-2, §5.4.

Builds the in-memory "true person" population that every source file is a
lossy, defect-laden projection of. This is what makes the generated dataset
*relationally coherent* rather than independently sampled per file.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

import numpy as np

from .config import ARCHETYPES
from .vocab import CATEGORY_NAMES, CITY_WEIGHTS, FIRST_NAMES, LAST_NAMES


@dataclass
class Person:
    true_person_id: str
    first_name: str
    last_name: str
    email_primary: str
    email_secondary: str | None
    phone: str
    city: str
    state: str
    country: str  # canonical "IN", formatting variants applied at projection
    date_of_birth: date
    gender: str
    tenure_start: date
    archetype: str
    category_affinity: dict[str, float]
    device_cookies: list[str]
    opt_in: bool
    postal_code: str
    churn_cutoff: date | None  # set when archetype == "churned"

    # source presence, assigned later
    in_crm: bool = False
    in_loyalty: bool = False
    in_app: bool = False
    crm_duplicate: bool = False   # within-source dup (X-07)
    shares_phone_with: str | None = None  # true_person_id of household pair (X-09)


def _weighted_choice(rng: np.random.Generator, items: list, weights: list[float]):
    w = np.asarray(weights, dtype=float)
    w = w / w.sum()
    idx = rng.choice(len(items), p=w)
    return items[idx]


def _make_email(rng: np.random.Generator, first: str, last: str, domain_pool, n: int = 0) -> str:
    domain = _weighted_choice(rng, [d for d, _ in domain_pool], [w for _, w in domain_pool])
    suffix = "" if n == 0 else str(n)
    local = f"{first.lower()}.{last.lower()}{suffix}"
    return f"{local}@{domain}"


def _make_phone(rng: np.random.Generator, used: set[str]) -> str:
    while True:
        national = "".join(str(d) for d in rng.integers(0, 10, size=10))
        if national[0] in "6789" and national not in used:  # realistic Indian mobile prefix
            used.add(national)
            return national


def generate_population(
    rng: np.random.Generator,
    n_persons: int,
    date_range_start: date,
    date_range_end: date,
) -> list[Person]:
    from .vocab import EMAIL_DOMAINS

    archetype_names = list(ARCHETYPES.keys())
    archetype_weights = [ARCHETYPES[a]["share"] for a in archetype_names]
    archetypes = rng.choice(archetype_names, size=n_persons, p=np.asarray(archetype_weights) / sum(archetype_weights))

    used_phones: set[str] = set()
    total_days = (date_range_end - date_range_start).days

    people: list[Person] = []
    for i in range(n_persons):
        pid = f"PER{i + 1:07d}"
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        city, state, _ = _weighted_choice(rng, CITY_WEIGHTS, [w for *_, w in CITY_WEIGHTS])

        email1 = _make_email(rng, first, last, EMAIL_DOMAINS, n=int(rng.integers(0, 100)) if rng.random() < 0.15 else 0)
        email2 = _make_email(rng, first, last, EMAIL_DOMAINS, n=int(rng.integers(100, 999))) if rng.random() < 0.2 else None

        phone = _make_phone(rng, used_phones)

        age_years = int(np.clip(rng.normal(32, 8), 18, 70))
        dob = date_range_end.replace(year=date_range_end.year - age_years)
        dob = dob - timedelta(days=int(rng.integers(0, 365)))

        # tenure weighted toward recent (growing business): Beta skew
        tenure_frac = rng.beta(2.0, 1.2)
        tenure_start = date_range_start + timedelta(days=int(tenure_frac * total_days))

        archetype = archetypes[i]
        churn_cutoff = None
        if ARCHETYPES[archetype]["churns"]:
            cutoff_frac = rng.uniform(0.2, 0.7)
            churn_cutoff = tenure_start + timedelta(days=int((date_range_end - tenure_start).days * cutoff_frac))

        affinity_draw = rng.dirichlet(np.full(len(CATEGORY_NAMES), 0.6))
        affinity = dict(zip(CATEGORY_NAMES, affinity_draw.tolist()))

        n_cookies = int(rng.integers(1, 4))
        cookies = [f"ck_{pid.lower()}_{k}" for k in range(n_cookies)]

        gender = rng.choice(["M", "F", "O"], p=[0.48, 0.48, 0.04])
        postal = f"{int(rng.integers(560001, 600100))}"

        people.append(Person(
            true_person_id=pid,
            first_name=first,
            last_name=last,
            email_primary=email1,
            email_secondary=email2,
            phone=phone,
            city=city,
            state=state,
            country="IN",
            date_of_birth=dob,
            gender=str(gender),
            tenure_start=tenure_start,
            archetype=str(archetype),
            category_affinity=affinity,
            device_cookies=cookies,
            opt_in=bool(rng.random() < (0.75 if archetype != "browser_no_buy" else 0.5)),
            postal_code=postal,
            churn_cutoff=churn_cutoff,
        ))

    return people


def assign_source_presence(rng: np.random.Generator, people: list[Person]) -> None:
    """§5.4/§4.2-4.4 source coverage: CRM 55%, loyalty 40%, app 60%."""
    n = len(people)
    crm_mask = rng.random(n) < 0.55
    loyalty_mask = rng.random(n) < 0.40
    app_mask = rng.random(n) < 0.60
    for p, in_crm, in_loy, in_app in zip(people, crm_mask, loyalty_mask, app_mask):
        p.in_crm = bool(in_crm)
        p.in_loyalty = bool(in_loy)
        p.in_app = bool(in_app)
