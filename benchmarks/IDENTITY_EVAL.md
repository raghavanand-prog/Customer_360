# Identity Resolution Evaluation

Produced by `c360/eval/identity_eval.py` against the generator's ground
truth (never seen by the pipeline itself), per §10.9 of `PROJECT_PLAN.md`.
These are the only identity-resolution numbers used anywhere in this
repository's documentation or resume material — every other number would
be an invented one, which §35/§37 of the plan explicitly forbids.

## `small` profile (1,000 true persons), seed `20260922`, run #8

```json
{
  "true_pairs": 769,
  "resolved_pairs": 663,
  "true_positive_pairs": 659,
  "false_positive_pairs": 4,
  "false_negative_pairs": 110,
  "pairwise_precision": 0.994,
  "pairwise_recall": 0.857,
  "f1": 0.9204,
  "over_merge_incidents": 2,
  "under_merge_incidents": 96,
  "evaluated_source_records": 1545
}
```

**Reading this honestly.**

- **Precision 99.4%.** The design goal stated in §10.1 — bias toward
  precision, because over-merging is the worse failure — is what these
  numbers show. Of 663 pairs the resolver merged, 659 were genuinely the
  same person.
- **The 2 remaining over-merge incidents** are both 3-member clusters where
  two different true persons share a phone number (a seeded household case,
  §4.9 X-09) and the third member is genuinely linked to one of them by
  email. The attribute-conflict guard (§10.6) as implemented only
  arbitrates the *pairwise* case (a 2-member cluster held together by a
  single unreinforced phone edge, exactly the worked example in §10.8
  Example 3); it does not yet generalise to a 3-member cluster where a
  second, legitimate edge keeps the ambiguous pair connected transitively.
  This is a known, explainable gap — not a silent one — and is recorded in
  `docs/PROJECT_DECISIONS.md`.
- **Recall 85.7%.** The 110 missed pairs are dominated by persons who share
  no *matchable* identifier at all across two of their fragments (e.g. an
  app record with only a device cookie and no email/phone — cookies are
  deliberately excluded from matching, §10.2) — under-merging is the
  cheaper failure mode by design, and this is the expected shape of that
  trade-off, not a bug.
- **A generator/ground-truth bug was found and fixed while producing this
  number.** The first version of `ground_truth_identity` mapped CRM records
  to true persons using a separately recomputed sequential counter, which
  silently desynchronised from the CRM file's actual row IDs the moment a
  within-source duplicate (X-07) wrote two rows for one person. That bug
  made the resolver look far worse than it is (precision ~0.27 on
  apparently-identical input) purely because the *evaluation's* ground
  truth was wrong, not because the resolver was. The fix (writers now
  return the exact `(record_id, true_person_id)` pairs they wrote, instead
  of the caller reconstructing them) is in `c360/generator/writers.py`, and
  the before/after is recorded in `docs/PROJECT_DECISIONS.md` as ADR-15.
  This is left in the history deliberately: it is a real example of the
  kind of "is this the resolver or the harness" debugging this project
  exists to demonstrate.

## `tiny` profile (200 persons) — used by the automated test suite

The hand-built fixtures in `tests/test_identity_resolution.py` (§10.8's
worked examples: 3-hop chain, shared-phone household, generic-email trap,
switchboard frequency screen, no-identifier singleton, cross-run stability)
pass exactly as specified and are the primary correctness evidence for the
algorithm; the `small`-profile run above is the primary evidence for its
behaviour on realistic, messy, generated data at volume.

## Reproducing this

```
make generate SIZE=small
make migrate
make run-pipeline SIZE=small
cd backend && .venv/bin/python -m c360.eval.identity_eval \
    --generated-dir ../data/generated --database-url "$DATABASE_URL"
```
