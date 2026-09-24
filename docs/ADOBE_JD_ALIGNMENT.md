# Adobe Associate Technical Consultant — JD Alignment

Honest, evidence-based mapping of this repository against a representative
Adobe Associate Technical Consultant job description. Every row cites the
actual file(s) that back the claim. Nothing here is inflated: a requirement
is marked ✅ only if a working, tested implementation exists in this repo
right now; 🟡 if a real but partial/adjacent capability exists; 🔴 if
nothing exists yet. This document is updated as of the AI-assistant phase
described in `docs/CHANGELOG.md` — re-check it before quoting a status in
an interview, since implementation continues after this snapshot.

## How to read this table

- **Repository Location** is always a real path in this repo, not a
  hypothetical.
- **Verification Method** says exactly how the claim was checked — a test
  suite, a live deployment check, a manual read of the code — not "trust
  me."
- A ✅ for "PySpark" does not imply a distributed cluster was used; see
  `docs/CLOUD_ARCHITECTURE.md` and the honesty note under "Distributed
  Systems" for the local-vs-cluster distinction.

## Core engineering

| Adobe Requirement | Status | Current Evidence | Repository Location | Verification Method | Interview Talking Point |
|---|---|---|---|---|---|
| Python | ✅ | Entire backend, pipeline, generator, DQ engine, identity resolution | `backend/c360/**` | 16/16 non-skipped tests passing (`make test`) | "The whole data platform — ingestion through serving API — is Python 3.11." |
| PySpark | ✅ | 13-stage pipeline: ingest → type/clean → DQ → identity resolution → aggregation → load | `backend/c360/pipeline/*.py`, `backend/c360/identity/*.py` | Live-run against Neon Postgres this session: run_id 4 succeeded, 991 customers / 2,679 orders written | "I can walk through why identity resolution took ~59s of an ~83s run — it's an iterative connected-components join, not a data-volume problem." |
| SQL / Database applications | ✅ | Parameterized SQL AST compiler for segments; hand-written migrations; least-privilege grants | `backend/c360/segments/compiler.py`, `backend/alembic/versions/0001_initial_schema.py`, `0002_grants.py` | Migrations applied live to Neon this session (`alembic upgrade head` → 2 revisions) | "Segment rules are a JSON AST compiled to parameterized SQL — never string-interpolated — specifically to avoid injection while keeping rules data-driven." |
| REST / Web development | ✅ | FastAPI app, versioned under `/api/v1`, consistent error envelope | `backend/c360/api/v1/*.py`, `backend/c360/api/errors.py` | Live: `GET /api/v1/health` → 200, unauthenticated `GET /api/v1/customers` → 401 with structured error body | "Every error is `{error: {code, message, request_id, details}}` — consistent shape whether it's a 401, 404, or 500." |
| Distributed applications | 🟡 | Spark's programming model (partitions, stages, shuffle, lazy evaluation) is used correctly; execution is `local[*]` on a single machine, not a cluster | `backend/c360/spark/session.py` | Honest limitation, not yet written up in a dedicated cloud-architecture doc | "The pipeline is written the way you'd write it for a cluster — no `.collect()` mid-pipeline, partition-aware joins — but it's never been run against a multi-node cluster. I can speak to what would change (shuffle partition tuning, executor sizing) without claiming I've done it." |
| JavaScript / TypeScript | ✅ | Entire frontend in strict TypeScript | `frontend/src/**`, `frontend/tsconfig.json` | `tsc` passes in CI | — |
| React | ✅ | 9-screen operations console, React Router, TanStack Query | `frontend/src/pages/*.tsx`, `frontend/src/App.tsx` | Live at https://customer360-console.vercel.app/ | — |
| CSS | ✅ | Tailwind-based design system, dark enterprise theme | `frontend/src/index.css`, component-level Tailwind classes | Visual — see `docs/screenshots/` | — |
| OOP / CS fundamentals | ✅ | Layered architecture (repositories → services → API), typed data contracts, graph algorithms (connected components) hand-rolled | `backend/c360/identity/components.py`, `backend/c360/repositories/*.py` | ADR-12 in `docs/PROJECT_DECISIONS.md` documents choosing hand-rolled components over GraphFrames | "I can explain why min-label-propagation converges and what its worst-case iteration count is." |
| Java / Java EE / Spring / Hibernate | 🔴 | Not implemented in this phase | — | ADR-23 in `docs/PROJECT_DECISIONS.md` | Deliberately deferred, not forgotten — adding a Spring service or JSP with no architectural need would be the "keyword-collection" outcome this phase explicitly avoided; can discuss Spring/Hibernate/JPA concepts from prior experience/coursework |
| XML / SOAP-style web services | 🔴 | Not implemented | — | — | REST/JSON only; can discuss XML vs JSON trade-offs conceptually |

## GenAI / applied AI

| Adobe Requirement | Status | Current Evidence | Repository Location | Verification Method | Interview Talking Point |
|---|---|---|---|---|---|
| GenAI fundamentals | ✅ | Full RAG + tool-calling + controlled-agent pipeline, built and verified end to end this phase | `backend/c360/ai/*` | Live via real HTTP requests (TestClient) and a real browser (Playwright) this session | "I can walk through the whole request lifecycle: auth → routing → tool calls → retrieval → grounding → response." |
| LLM integration | 🟡 | Provider-agnostic interface implemented (`generate`/`stream`/`structured_generate`); `NotConfiguredProvider` (the only path actually exercised) never fakes a response; `AnthropicProvider` is code-complete but unverified against a live account | `backend/c360/ai/llm.py` | Live-verified: the not-configured path returns the honest message via the real API | "The abstraction and the honest fallback are proven live; the paid-provider path is implemented but I haven't paid to prove it, and I say so." |
| RAG | ✅ | Real chunking of real project docs (69 chunks: 23 markdown sections, 38 DQ rules, 8 segment definitions) → embedding → pgvector storage → cosine retrieval → context construction → response | `backend/c360/ai/chunking.py`, `ingest.py`, `agent.py`, `repositories/ai.py`, migration `0003_ai_knowledge` | Live-verified: real retrieval returns the correct segment/DQ-rule chunk for on-topic questions (see `docs/AI_EVALUATION.md`) | Can explain the full pipeline and its one measured failure mode (an off-topic false positive, documented not hidden) |
| Embeddings | 🟡 | `EmbeddingProvider` abstraction; `DeterministicLocalEmbedding` (feature-hashed bag-of-words, the only path exercised) is deterministic, unit-tested, and honestly documented as lexical not semantic | `backend/c360/ai/embeddings.py` | Unit-tested (determinism, normalisation, similarity ordering) + live retrieval results | "It's a real, well-understood technique (the hashing trick), not a trained model — I can explain exactly what it can and can't distinguish, and the eval set shows a concrete case where that limit shows up." |
| Vector search | ✅ | pgvector extension + cosine distance (`<=>`) against the existing Postgres instance, no separate vector DB | Migration `0003_ai_knowledge`, `repositories/ai.py::search_similar_chunks` | Live-verified against a real ~70-row corpus; also found and fixed a real ivfflat-index bug at this scale (see ADR-18) | Can explain why an approximate index was actively wrong at this corpus size, and what corpus size would justify one |
| Agentic AI | ✅ | Single controlled agent: deterministic keyword-based tool routing (no LLM in the selection loop), fixed tool allowlist, hard-capped tool calls | `backend/c360/ai/agent.py` | Unit tests (routing policy) + live RBAC verification (viewer vs analyst getting different tool sets) | "Deliberately not autonomous — see ADR-19/20 for exactly why, including the security argument." |
| AI evaluation | ✅ | 12-question reproducible eval set; only genuinely measurable metrics reported (tool-call correctness, retrieval relevance, latency); answer-correctness/groundedness explicitly marked not evaluated | `docs/AI_EVALUATION.md`, `backend/scripts/run_ai_eval.py`, `benchmarks/AI_EVAL_RESULTS.json` | Actually executed this session: 100% tool-call correctness, 75% retrieval relevance (one documented, explained miss) | "I can walk through the one metric that came in below 100% and explain exactly why, rather than tuning a threshold to hide it." |
| Function/tool calling | ✅ | 8 tools wrapping existing, already-tested repository functions — no new SQL, no arbitrary query capability, per-tool RBAC matching the direct REST endpoints exactly | `backend/c360/ai/tools.py` | Live RBAC test: viewer denied `get_customer_identities`/`get_customer_quality`, analyst allowed | "The LLM never gets SQL access — every tool is the same code path the REST API already uses." |
| Conversational AI UX | ✅ | "Ask about this customer" panel on the Customer 360 page: suggested questions, conversation history, tool-activity display, source citations with scores, loading/cancel/retry/error/empty states, "AI provider not configured" banner — native to the existing dark enterprise design, not a generic chat widget | `frontend/src/components/AiAssistant.tsx` | Live-verified in a real headless browser (screenshot on file) | — |
| Streaming | 🔴 | Not implemented. The non-streaming request/response path was implemented and verified correctly first, per this phase's own instruction not to sacrifice correctness for a keyword | — | — | "SSE streaming is the clearly-scoped next increment — the response shape and provider interface already have a `stream()` seam for it." |
| Node.js | 🔴 | Deliberately not introduced — FastAPI handles the AI endpoint cleanly with no second backend needed | — | ADR-23 | "Added Node only where it earns its place; here it wouldn't have." |

## Consulting / delivery skills

| Adobe Requirement | Status | Current Evidence | Repository Location | Verification Method | Interview Talking Point |
|---|---|---|---|---|---|
| Business requirements → technical specs | 🟡 | This document itself, plus `PROJECT_PLAN.md`, is a real requirements-to-implementation trace | `PROJECT_PLAN.md`, this file | — | — |
| Data integration | ✅ | 9 source files across 3 formats reconciled into one canonical schema | `backend/c360/pipeline/conform.py`, `docs/DATA_PIPELINE.md` | Pipeline run logs | — |
| Cloud technologies | ✅ | Public deployment: Vercel (frontend + backend) + Neon Postgres | `docs/DEPLOYMENT.md`, `docs/CLOUD_ARCHITECTURE.md` | Live URLs, verified this session | — |
| Big data concepts | 🟡 | Spark concepts genuinely applied at small scale; not benchmarked at "big data" volume | `benchmarks/RESULTS.md` | Honest limitation stated in the same doc | — |
| Customer assistance / knowledge transfer | 🟡 | `docs/SETUP.md` exists; a dedicated knowledge-transfer doc is a possible next step, not yet written | `docs/SETUP.md` | — | — |
| Scrum / engineering process | 🔴 | Solo project, no formal Scrum artifacts | — | — | Can discuss the ADR-driven decision log as a lightweight substitute |

## Honest summary

**Strong today, independent of this AI phase:** Python, PySpark, SQL, REST
API design, React/TypeScript, cloud deployment, data engineering, identity
resolution, data quality.

**Built and verified this phase:** LLM/embedding provider abstractions, a
real RAG pipeline over the project's own documentation via pgvector, a
small controlled agent with 8 Customer360 tools and per-tool RBAC, a native
assistant UI on the Customer 360 page, and a real (not fabricated)
evaluation pass — 100% tool-call correctness, 75% retrieval relevance with
the one miss explained rather than hidden. Two pre-existing bugs were found
and fixed along the way: a broken column reference in
`/customers/{id}/timeline`, and segment evaluation (`evaluate_all`) being
fully implemented but never wired to the pipeline, CLI, or CI — meaning
`test_segments_list` had been passing for the wrong reason (leftover
database state, not reproducible pipeline output). Both are recorded as
ADRs in `docs/PROJECT_DECISIONS.md` rather than fixed silently.

**Explicitly out of scope for now:** SSE streaming (the non-streaming path
was correctness-verified first), Java/Spring/Hibernate, XML/SOAP
integration, a Node.js gateway, Kubernetes, Kafka, multi-agent systems.
These are documented gaps, not hidden ones — see the "Scope reductions"
section of `docs/PROJECT_DECISIONS.md` for the same honesty pattern applied
to the rest of the platform.
