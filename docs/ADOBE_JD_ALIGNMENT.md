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
| Distributed applications | 🟡 | Spark's programming model (partitions, stages, shuffle, lazy evaluation) is used correctly; execution is `local[*]` on a single machine, not a cluster | `backend/c360/spark/session.py` | Honest by design — see `docs/CLOUD_ARCHITECTURE.md` | "The pipeline is written the way you'd write it for a cluster — no `.collect()` mid-pipeline, partition-aware joins — but it's never been run against a multi-node cluster. I can speak to what would change (shuffle partition tuning, executor sizing) without claiming I've done it." |
| JavaScript / TypeScript | ✅ | Entire frontend in strict TypeScript | `frontend/src/**`, `frontend/tsconfig.json` | `tsc` passes in CI | — |
| React | ✅ | 9-screen operations console, React Router, TanStack Query | `frontend/src/pages/*.tsx`, `frontend/src/App.tsx` | Live at https://customer360-console.vercel.app/ | — |
| CSS | ✅ | Tailwind-based design system, dark enterprise theme | `frontend/src/index.css`, component-level Tailwind classes | Visual — see `docs/screenshots/` | — |
| OOP / CS fundamentals | ✅ | Layered architecture (repositories → services → API), typed data contracts, graph algorithms (connected components) hand-rolled | `backend/c360/identity/components.py`, `backend/c360/repositories/*.py` | ADR-12 in `docs/PROJECT_DECISIONS.md` documents choosing hand-rolled components over GraphFrames | "I can explain why min-label-propagation converges and what its worst-case iteration count is." |
| Java / Java EE / Spring / Hibernate | 🔴 | Not implemented in this phase | — | — | Deliberately deferred — see `docs/PROJECT_DECISIONS.md` ADR on scope, and `docs/ENTERPRISE_JAVA_NOTES.md` (concepts-only, no forced JSP/Servlet code in the product) if/when written |
| XML / SOAP-style web services | 🔴 | Not implemented | — | — | REST/JSON only; can discuss XML vs JSON trade-offs conceptually |

## GenAI / applied AI

| Adobe Requirement | Status | Current Evidence | Repository Location | Verification Method | Interview Talking Point |
|---|---|---|---|---|---|
| GenAI fundamentals | 🟡→ in progress | LLM/embedding provider abstractions being implemented this phase | `backend/c360/ai/*` (new) | Unit tests, no live paid-provider call yet | See `docs/AI_EVALUATION.md` once written |
| LLM integration | 🟡 | Provider-agnostic interface implemented; falls back to "AI provider not configured" without credentials (never fakes a response) | `backend/c360/ai/llm.py` | Runs with zero configured provider in this environment — that path is the one actually exercised live | "The abstraction is real; I haven't paid for a hosted model to prove the OpenAI-compatible path end-to-end, and I say so rather than claim it." |
| RAG | 🟡/in progress | Chunking + pgvector retrieval over real project docs | `backend/c360/ai/rag.py`, migration adding `document_chunks` | Retrieval tested with deterministic local embeddings | — |
| Embeddings | 🟡 | `EmbeddingProvider` abstraction with a deterministic local fallback for tests/no-credential environments | `backend/c360/ai/embeddings.py` | Unit-tested | "Same story as the LLM: a real provider integration exists in code, exercised in this environment only via its deterministic fallback." |
| Vector search | 🟡 | pgvector extension + cosine-similarity query against Neon Postgres (no separate vector DB) | migration + `backend/c360/ai/rag.py` | Live query against Neon this session — see final report | ADR: why pgvector instead of a dedicated vector database |
| Agentic AI | 🟡 | Single controlled agent: fixed tool allowlist, bounded tool calls, no autonomous loop | `backend/c360/ai/agent.py` | Unit + policy tests | "Deliberately not an autonomous multi-agent system — see the ADR on why." |
| AI evaluation | 🟡 | Small reproducible eval set; only genuinely measurable metrics reported | `docs/AI_EVALUATION.md`, `backend/scripts/run_ai_eval.py` | Actually executed — see recorded results | "I evaluated what I could measure without a paid LLM judge, and said clearly what I couldn't." |
| Function/tool calling | ✅/🟡 | Fixed set of Customer360 tools wrapping existing repository functions, strict schemas, no arbitrary SQL | `backend/c360/ai/tools.py` | Authorization + schema tests | — |
| Conversational AI UX / streaming | 🟡 | Assistant panel added to Customer 360 page; streaming implemented only if it didn't require disproportionate change (see final report for actual status) | `frontend/src/components/*Assistant*` | Manual UI check | — |
| Node.js | 🔴 | Deliberately not introduced — FastAPI handles the AI endpoint cleanly with no second backend needed | — | — | "Added Node only where it earns its place; here it wouldn't have." |

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

**Being built this phase:** LLM/embedding abstractions, RAG over real
project docs via pgvector, a small controlled agent with Customer360 tools,
grounded assistant UI, and a real (not fabricated) evaluation pass.

**Explicitly out of scope for now:** Java/Spring/Hibernate, XML/SOAP
integration, a Node.js gateway, Kubernetes, Kafka, multi-agent systems.
These are documented gaps, not hidden ones — see the "Scope reductions"
section of `docs/PROJECT_DECISIONS.md` for the same honesty pattern applied
to the rest of the platform.
