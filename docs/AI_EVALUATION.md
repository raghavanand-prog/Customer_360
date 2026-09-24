# AI Evaluation — Customer360 Intelligence Assistant

This documents an evaluation that was **actually executed** against the
running code, not a projected or estimated one. Reproduce it yourself with:

```bash
cd backend
DATABASE_URL="<your local or Neon connection string>" \
JWT_SECRET_KEY="<any non-placeholder value>" \
PYTHONPATH=. .venv/bin/python scripts/run_ai_eval.py
```

It requires the AI knowledge base to already be ingested
(`python -m c360.cli ingest-ai-docs`) and at least one customer row loaded
(the normal pipeline output).

## What is, and isn't, measurable in this environment

No LLM API key (`ANTHROPIC_API_KEY`) is configured anywhere in this
project. The assistant's `NotConfiguredProvider` path is the only one
actually exercised, which means there is no model-generated natural
language answer to grade. Consequently:

| Metric | Status | Why |
|---|---|---|
| Tool-call correctness | ✅ Measured | Deterministic keyword router — no LLM involved, fully reproducible |
| Retrieval relevance | ✅ Measured | Real pgvector cosine search against real ingested docs |
| Latency | ✅ Measured | Real wall-clock time of `run_agent()`, including DB round-trips |
| Answer correctness | 🔴 Not evaluated | No LLM-generated answer exists to grade |
| Groundedness | 🔴 Not evaluated | Same reason |
| Citation narrative correctness | 🔴 Not evaluated | Same reason (source *retrieval* is measured above; whether a model would *narrate* those sources faithfully is untested) |
| Hallucination rate | 🔴 Not evaluated | No generated text to check for hallucination |

If `ANTHROPIC_API_KEY` is configured later, the three 🔴 rows become
measurable with an LLM-as-judge harness (grading the generated answer
against the retrieved context for faithfulness) — that is future work, not
claimed here.

## Evaluation set

12 hand-written questions across the categories requested: customer
profile, metric explanation, segment explanation, identity explanation, DQ
explanation, timeline summary, and platform-documentation-only questions
(no customer context) — including one deliberately off-topic question
("What is the capital of France?") to test the "insufficient information"
fallback. The full set is in `backend/scripts/run_ai_eval.py::EVAL_SET`.

## Results (actually run, this session)

```json
{
  "total_cases": 12,
  "tool_call_correctness": 1.0,
  "retrieval_relevance": 0.75,
  "retrieval_applicable_cases": 4,
  "latency_ms_mean": 2.37,
  "latency_ms_median": 2.44,
  "latency_ms_max": 5.15
}
```

Full per-case results: [`benchmarks/AI_EVAL_RESULTS.json`](../benchmarks/AI_EVAL_RESULTS.json).

**Tool-call correctness: 12/12 (100%).** The deterministic router selected
exactly the expected tool set for every question, including one case where
the expected set itself needed correcting during development (see below).

**Retrieval relevance: 3/4 (75%) on cases with a documentation-based
expected answer.** The one miss is real and instructive, not swept under
the rug: the deliberately off-topic question "What is the capital of
France?" scored 0.372 against `docs/DATA_DICTIONARY.md` — above this
system's 0.25 relevance floor — so it returned documentation context
instead of the "insufficient information" fallback. This is a genuine,
disclosed limitation of the feature-hashed lexical embedding (see
`c360/ai/embeddings.py`): short questions built from very common English
words can spike similarity against any chunk that happens to share those
words, regardless of topical relevance. A trained semantic embedding model
would not have this failure mode. Rather than raise the relevance floor to
paper over this single adversarial example (risking overfitting a
threshold to a 12-question set), it is reported honestly here.

**Latency: ~2.4ms median end to end**, which is unsurprising and not a
meaningful "AI latency" number — it reflects local Postgres round-trips
with no network call to an LLM (there is none configured). Once a real LLM
provider is added, expect latency to be dominated by that network call
(typically hundreds of milliseconds to a few seconds), not by anything
measured here.

## A real bug this evaluation surfaced

Building the "timeline summary" eval case exercised `get_customer_timeline`
against real data for the first time end-to-end and hit a pre-existing bug:
`backend/c360/repositories/customers.py` referenced a `support_tickets.subject`
column that does not exist in the actual schema (the real column is
`category`). This was a latent bug in the existing `/customers/{id}/timeline`
endpoint, unrelated to the AI feature itself, found and fixed during this
work — see the corresponding commit. It's recorded here because "the AI
feature helped find a bug in the underlying platform" is a more honest and
more interesting story than pretending everything was already correct.

## Retrieval calibration note

The 0.25 relevance floor in `c360/ai/agent.py::MIN_RETRIEVAL_SCORE` was set
empirically: on-topic questions in this corpus scored 0.35-0.43 against
their best-matching chunk, while intentionally off-topic questions
(excluding the one documented miss above) topped out around 0.15-0.19.
Re-calibrate this constant if the corpus or embedding model changes.

## What would change with a real embedding/LLM provider

- **Embeddings**: swapping `DeterministicLocalEmbedding` for a real model
  (e.g. a hosted embedding API) would very likely fix the off-topic false
  positive above, since semantic embeddings distinguish topic, not just
  shared vocabulary. This requires re-running the migration's vector
  dimension to match the new model's output size (see the migration's
  docstring) and re-ingesting.
- **LLM**: `AnthropicProvider` in `c360/ai/llm.py` is implemented against
  the documented Messages API shape but has not been exercised against a
  live account in this session — no credential was available. Configuring
  `ANTHROPIC_API_KEY` would activate it with no other code change, and at
  that point answer correctness/groundedness could be evaluated for real,
  ideally with a small LLM-as-judge harness scoring generated answers
  against the retrieved context — not implemented in this phase.
