"""Real, reproducible evaluation of the Customer360 Intelligence Assistant.

Run with: DATABASE_URL=... JWT_SECRET_KEY=... .venv/bin/python scripts/run_ai_eval.py

Measures only what is genuinely measurable in this environment:

- **Tool-call correctness**: the agent's deterministic keyword router is
  compared against a hand-specified expected tool set per question. This is
  fully deterministic and 100% reproducible (no LLM involved).
- **Retrieval relevance**: for each question with a documentation-based
  expected answer, checks whether the top-scoring retrieved chunk's source
  file matches a hand-labelled expected source. Uses the actual
  `DeterministicLocalEmbedding` + pgvector cosine search running in
  production today.
- **Latency**: real wall-clock time for `run_agent()` end to end, including
  the DB round-trips for tool calls and retrieval.

Explicitly NOT measured, and not reported as a score: answer correctness,
groundedness of the final natural-language answer, or citation narrative
quality. All three require a configured LLM to produce a natural-language
answer to score in the first place -- this environment has none configured
(see docs/AI_EVALUATION.md for why, and what would be needed to add these).
"""
from __future__ import annotations

import json
import statistics
import time
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text

from c360.ai.agent import run_agent
from c360.config import get_settings
from c360.db import get_sessionmaker


@dataclass
class EvalCase:
    id: str
    category: str
    question: str
    needs_customer: bool
    expected_tools: list[str]
    expected_source_substring: str | None  # a substring expected in the top retrieved chunk's source path


EVAL_SET: list[EvalCase] = [
    EvalCase("profile-1", "customer_profile", "Tell me about this customer's profile.", True,
             ["get_customer_profile"], None),
    EvalCase("metric-1", "metric_explanation", "Explain this customer's RFM profile.", True,
             ["get_customer_profile", "get_customer_metrics"], None),
    EvalCase("metric-2", "metric_explanation", "What is the customer's total spend and CLV?", True,
             ["get_customer_profile", "get_customer_metrics"], None),
    EvalCase("segment-1", "segment_explanation", "Why is this customer considered high value?", True,
             # The question contains the literal trigger phrase "high value" (a segment name),
             # so the router correctly also fetches segment membership, not just metrics.
             ["get_customer_profile", "get_customer_metrics", "get_customer_segments"], None),
    EvalCase("segment-2", "segment_explanation", "What segments does this customer belong to?", True,
             ["get_customer_profile", "get_customer_segments"], None),
    EvalCase("identity-1", "identity_explanation", "Why does the system consider these identities the same customer?", True,
             ["get_customer_profile", "get_customer_identities"], None),
    EvalCase("dq-1", "dq_explanation", "What data quality issues affect this customer?", True,
             ["get_customer_profile", "get_customer_quality"], None),
    EvalCase("timeline-1", "timeline_summary", "Summarise this customer's recent activity and timeline.", True,
             ["get_customer_profile", "get_customer_timeline"], None),
    EvalCase("doc-segment", "platform_doc", "What is the threshold for the high value segment?", False,
             [], "config/segments.yaml"),
    EvalCase("doc-dq-email", "platform_doc", "What rule validates email address syntax?", False,
             [], "config/dq_rules.yaml"),
    EvalCase("doc-identity", "platform_doc", "How does identity resolution use connected components?", False,
             [], "docs/DATA_PIPELINE.md"),
    EvalCase("doc-offtopic", "platform_doc", "What is the capital of France?", False,
             [], None),  # expect NO relevant source (tests the insufficient-info fallback)
]


def run_eval() -> dict:
    db = get_sessionmaker()()
    settings = get_settings()
    customer_id = db.execute(text("SELECT canonical_customer_id FROM customers LIMIT 1")).scalar_one()

    results = []
    latencies_ms = []
    tool_correct = 0
    retrieval_correct = 0
    retrieval_applicable = 0

    for case in EVAL_SET:
        cid = customer_id if case.needs_customer else None
        start = time.perf_counter()
        agent_result = run_agent(db, "admin", settings, case.question, cid)
        elapsed_ms = (time.perf_counter() - start) * 1000
        latencies_ms.append(elapsed_ms)

        actual_tools = set(agent_result.tools_called)
        expected_tools = set(case.expected_tools)
        tool_match = actual_tools == expected_tools
        if tool_match:
            tool_correct += 1

        retrieval_match = None
        if case.expected_source_substring is not None:
            retrieval_applicable += 1
            top_source = agent_result.sources[0].source if agent_result.sources else None
            retrieval_match = bool(top_source and case.expected_source_substring in top_source)
            if retrieval_match:
                retrieval_correct += 1
        elif case.id == "doc-offtopic":
            retrieval_applicable += 1
            retrieval_match = len(agent_result.sources) == 0
            if retrieval_match:
                retrieval_correct += 1

        results.append({
            "id": case.id,
            "category": case.category,
            "question": case.question,
            "expected_tools": sorted(expected_tools),
            "actual_tools": sorted(actual_tools),
            "tool_call_correct": tool_match,
            "expected_source_substring": case.expected_source_substring,
            "top_retrieved_source": agent_result.sources[0].source if agent_result.sources else None,
            "top_retrieved_score": agent_result.sources[0].score if agent_result.sources else None,
            "retrieval_correct": retrieval_match,
            "latency_ms": round(elapsed_ms, 2),
            "provider_configured": agent_result.configured,
        })

    summary = {
        "total_cases": len(EVAL_SET),
        "tool_call_correctness": round(tool_correct / len(EVAL_SET), 3),
        "retrieval_relevance": round(retrieval_correct / retrieval_applicable, 3) if retrieval_applicable else None,
        "retrieval_applicable_cases": retrieval_applicable,
        "latency_ms_mean": round(statistics.mean(latencies_ms), 2),
        "latency_ms_median": round(statistics.median(latencies_ms), 2),
        "latency_ms_max": round(max(latencies_ms), 2),
        "answer_correctness": "NOT EVALUATED -- no LLM provider configured in this environment",
        "groundedness": "NOT EVALUATED -- no LLM provider configured in this environment",
        "citation_narrative_correctness": "NOT EVALUATED -- no LLM provider configured in this environment",
    }
    return {"summary": summary, "cases": results}


if __name__ == "__main__":
    output = run_eval()
    print(json.dumps(output["summary"], indent=2))
    out_path = Path(__file__).resolve().parents[2] / "benchmarks" / "AI_EVAL_RESULTS.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(f"\nFull results written to {out_path}")
