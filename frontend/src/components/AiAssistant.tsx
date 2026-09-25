import { useImperativeHandle, useLayoutEffect, useRef, useState } from "react";
import type { ReactNode, Ref } from "react";
import axios from "axios";
import { useQuery } from "@tanstack/react-query";
import { createTimeline } from "animejs/timeline";
import { stagger } from "animejs/utils";
import { api, errorMessage } from "../lib/api";
import type { AiAskResponse, AiSourceRef, AiStatus } from "../lib/types";
import { EASE_OUT, prefersReducedMotion, useReducedMotion } from "../lib/motion";
import { Icon } from "./Icons";
import { StatusDot } from "./Common";

interface ConversationTurn {
  id: number;
  question: string;
  response?: AiAskResponse;
  error?: string;
}

export interface AssistantHandle {
  focus: () => void;
}

const CUSTOMER_QUESTIONS = [
  "Why is this customer considered high value?",
  "Explain this customer's RFM profile.",
  "What segments does this customer belong to?",
  "Summarise this customer's recent activity.",
  "What data-quality issues affect this customer?",
  "Why does the system consider these identities the same customer?",
];

const PLATFORM_QUESTIONS = [
  "What data quality rules exist in this project?",
  "How does identity resolution decide two records are the same person?",
  "How is the High Value segment defined?",
];

const TOOL_LABELS: Record<string, string> = {
  get_customer_profile: "Profile",
  get_customer_metrics: "Metrics",
  get_customer_segments: "Segments",
  get_customer_timeline: "Timeline",
  get_customer_identities: "Identities",
  get_customer_quality: "Data quality",
  get_segment_definition: "Segment definition",
  get_data_quality_summary: "DQ summary",
};

const MAX_QUESTION = 2000; // matches AskRequest.question max_length on the API

function toolLabel(name: string) {
  return TOOL_LABELS[name] ?? name;
}

type StepState = "ok" | "denied" | "empty" | "skipped";

interface TraceStep {
  key: string;
  label: string;
  detail?: string;
  state: StepState;
}

/**
 * Builds the execution trace *after* the response arrives, strictly from
 * fields the API returned. Order mirrors the server (c360/ai/agent.py):
 * allowlisted tools -> knowledge retrieval -> provider. Nothing here is
 * inferred or simulated.
 */
function buildTrace(r: AiAskResponse, status: AiStatus | undefined): TraceStep[] {
  const steps: TraceStep[] = [];
  for (const t of r.tools_called) steps.push({ key: `t-${t}`, label: toolLabel(t), detail: "tool", state: "ok" });
  for (const t of r.tool_denied) steps.push({ key: `d-${t}`, label: toolLabel(t), detail: "not authorized", state: "denied" });
  steps.push({
    key: "retrieval",
    label: "Knowledge retrieval",
    detail: `${r.sources.length} source${r.sources.length === 1 ? "" : "s"}`,
    state: r.sources.length ? "ok" : "empty",
  });
  let genDetail: string;
  if (r.configured) genDetail = [r.provider, r.model].filter(Boolean).join(" · ");
  else if (status?.configured) genDetail = "skipped — insufficient context";
  else if (status && !status.configured) genDetail = "not configured";
  else genDetail = "no generated answer";
  steps.push({ key: "generation", label: "Generation", detail: genDetail, state: r.configured ? "ok" : "skipped" });
  return steps;
}

const STEP_STYLE: Record<StepState, { box: string; icon: ReactNode }> = {
  ok: { box: "border-accent/25 bg-accent/[0.06] text-ink", icon: <Icon.Check size={12} className="text-accent" /> },
  denied: { box: "border-warn/25 bg-warn/[0.06] text-ink", icon: <Icon.Denied size={12} className="text-warn" /> },
  empty: { box: "border-surface-border bg-white/[0.02] text-ink-muted", icon: <Icon.Info size={12} className="text-ink-faint" /> },
  skipped: { box: "border-surface-border border-dashed bg-transparent text-ink-muted", icon: <Icon.Info size={12} className="text-ink-faint" /> },
};

function ExecutionTrace({ steps }: { steps: TraceStep[] }) {
  return (
    <div>
      <div className="stat-label mb-2 flex items-center gap-1.5">
        <Icon.Route size={12} />
        Execution trace
      </div>
      <ol className="flex flex-wrap items-center gap-y-2" aria-label="Execution trace">
        {steps.map((s, i) => (
          <li key={s.key} data-trace-step className="flex items-center">
            {i > 0 && <Icon.ChevronRight size={12} className="mx-1 text-ink-faint/60 shrink-0" />}
            <span className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs ${STEP_STYLE[s.state].box}`}>
              {STEP_STYLE[s.state].icon}
              <span className="font-medium">{s.label}</span>
              {s.detail && <span className="text-ink-faint">· {s.detail}</span>}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}

function SourceItem({ s }: { s: AiSourceRef }) {
  const pct = Math.max(0, Math.min(1, s.score)) * 100;
  return (
    <li data-evidence className="flex items-start gap-2.5 rounded-md border border-surface-border bg-surface-sunken/60 px-3 py-2">
      <Icon.File size={14} className="text-ink-faint mt-0.5 shrink-0" />
      <div className="min-w-0 flex-1">
        <div className="font-mono text-2xs text-ink-faint truncate" title={s.source}>
          {s.source}
        </div>
        <div className="text-xs text-ink-muted mt-0.5 break-words">{s.section}</div>
      </div>
      <div className="shrink-0 w-16 text-right" title="Cosine similarity between the question and this chunk (pgvector)">
        <div className="font-mono text-2xs text-ink-muted tabular-nums">{s.score.toFixed(2)}</div>
        <div className="meter mt-1">
          <span className="bg-accent/60" style={{ width: `${pct}%` }} />
        </div>
      </div>
    </li>
  );
}

function Evidence({ r }: { r: AiAskResponse }) {
  const hasCustomerData = r.tools_called.length > 0 || r.tool_denied.length > 0;
  return (
    <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
      <div className="md:col-span-2">
        <div className="stat-label mb-2 flex items-center gap-1.5">
          <Icon.Database size={12} />
          Customer data
        </div>
        {!hasCustomerData && <p className="text-xs text-ink-faint">No customer tools ran — no customer was in context.</p>}
        <ul className="space-y-1.5">
          {r.tools_called.map((t) => (
            <li key={t} data-evidence className="flex items-center justify-between gap-2 rounded-md border border-surface-border bg-surface-sunken/60 px-3 py-2">
              <span className="text-xs text-ink-muted">{toolLabel(t)}</span>
              <span className="font-mono text-2xs text-ink-faint truncate">{t}</span>
            </li>
          ))}
          {r.tool_denied.map((t) => (
            <li key={t} data-evidence className="flex items-center justify-between gap-2 rounded-md border border-warn/20 bg-warn/[0.04] px-3 py-2">
              <span className="text-xs text-warn">{toolLabel(t)}</span>
              <span className="text-2xs text-ink-faint">not authorized for your role</span>
            </li>
          ))}
        </ul>
      </div>
      <div className="md:col-span-3">
        <div className="stat-label mb-2 flex items-center gap-1.5">
          <Icon.File size={12} />
          Platform knowledge
          <span className="normal-case tracking-normal font-normal text-ink-faint/80">· pgvector cosine similarity</span>
        </div>
        {r.sources.length === 0 ? (
          <p className="text-xs text-ink-faint">No documentation chunk scored above the relevance threshold.</p>
        ) : (
          <ul className="space-y-1.5">
            {r.sources.map((s, j) => (
              <SourceItem key={j} s={s} />
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function AnswerBlock({ r }: { r: AiAskResponse }) {
  if (r.configured) {
    return (
      <div data-answer>
        <div className="stat-label mb-1.5 flex items-center gap-2">
          Generated answer
          <span className="normal-case tracking-normal font-normal font-mono text-ink-faint">
            {[r.provider, r.model].filter(Boolean).join(" · ")}
          </span>
        </div>
        <div className="text-sm text-ink leading-relaxed whitespace-pre-wrap">{r.answer}</div>
      </div>
    );
  }
  // Not model-generated: show the server's message verbatim, visually
  // distinct from a generated answer so it can't be mistaken for one.
  return (
    <div data-answer className="rounded-md border border-warn/20 bg-warn/[0.05] px-3 py-2.5">
      <div className="flex items-center gap-2 text-xs font-medium text-warn">
        <Icon.Info size={13} />
        System response · no model-generated text
      </div>
      <p className="text-sm text-ink-muted mt-1.5 leading-relaxed whitespace-pre-wrap">{r.answer}</p>
    </div>
  );
}

function TurnView({ turn, status, onRetry }: { turn: ConversationTurn; status: AiStatus | undefined; onRetry: (q: string) => void }) {
  const ref = useRef<HTMLDivElement>(null);

  // Choreography for a freshly arrived response: answer, then the trace
  // steps in the order the server ran them, then the evidence items.
  useLayoutEffect(() => {
    const root = ref.current;
    if (!root || !turn.response || prefersReducedMotion()) return;
    const q = (sel: string) => Array.from(root.querySelectorAll<HTMLElement>(sel));
    const answer = q("[data-answer]");
    const steps = q("[data-trace-step]");
    const evidence = q("[data-evidence]");
    const all = [...answer, ...steps, ...evidence];
    for (const el of all) el.style.opacity = "0";
    const clear = () => {
      for (const el of all) {
        el.style.opacity = "";
        el.style.transform = "";
      }
    };
    const tl = createTimeline({ defaults: { ease: EASE_OUT }, onComplete: clear });
    tl.add(answer, { opacity: [0, 1], translateY: [6, 0], duration: 360 }, 0);
    if (steps.length) tl.add(steps, { opacity: [0, 1], translateX: [-6, 0], duration: 300, delay: stagger(70) }, 120);
    if (evidence.length) tl.add(evidence, { opacity: [0, 1], translateY: [6, 0], duration: 320, delay: stagger(50) }, 200 + steps.length * 70);
    return () => {
      tl.cancel();
      clear();
    };
    // Runs once per turn: a turn's response never changes after it arrives.
  }, [turn.response]);

  return (
    <article ref={ref} className="space-y-3" aria-label={`Question: ${turn.question}`}>
      <div className="flex items-start gap-2.5">
        <span className="mt-0.5 font-mono text-2xs text-accent/80 shrink-0">Q</span>
        <p className="text-sm text-ink font-medium break-words">{turn.question}</p>
      </div>
      {turn.error && (
        <div role="alert" className="ml-5 flex flex-wrap items-center gap-3 rounded-md border border-danger/25 bg-danger/[0.06] px-3 py-2 text-sm text-danger">
          <Icon.Alert size={14} />
          <span className="flex-1 min-w-0">{turn.error}</span>
          <button onClick={() => onRetry(turn.question)} className="btn-ghost text-xs">
            <Icon.Refresh size={12} />
            Retry
          </button>
        </div>
      )}
      {turn.response && (
        <div className="ml-5 rounded-lg border border-surface-border bg-surface/60 p-4 space-y-4">
          <AnswerBlock r={turn.response} />
          <ExecutionTrace steps={buildTrace(turn.response, status)} />
          <div className="border-t border-surface-border pt-4">
            <Evidence r={turn.response} />
          </div>
        </div>
      )}
    </article>
  );
}

function ProviderStatus({ status, isError }: { status: AiStatus | undefined; isError: boolean }) {
  if (isError) {
    return (
      <span className="badge bg-white/[0.05] text-ink-faint">
        <StatusDot tone="neutral" />
        Provider status unavailable
      </span>
    );
  }
  if (!status) return <span className="skeleton h-5 w-40 inline-block" aria-hidden="true" />;
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className={`badge ${status.configured ? "bg-accent/10 text-accent" : "bg-warn/10 text-warn"}`}>
        <StatusDot tone={status.configured ? "good" : "warn"} />
        {status.configured ? `LLM · ${status.provider}` : "LLM provider not configured"}
      </span>
      <span className="badge bg-white/[0.05] text-ink-muted">
        <Icon.File size={11} />
        {status.knowledge_chunks.toLocaleString()} knowledge chunks
      </span>
    </div>
  );
}

export function AiAssistantPanel({ customerId, ref }: { customerId?: string; ref?: Ref<AssistantHandle> }) {
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<ConversationTurn[]>([]);
  const [loading, setLoading] = useState(false);
  const [pending, setPending] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const sectionRef = useRef<HTMLElement>(null);
  const logRef = useRef<HTMLDivElement>(null);
  const nextId = useRef(1);
  const reduced = useReducedMotion();

  const statusQuery = useQuery({
    queryKey: ["ai-status"],
    queryFn: async () => (await api.get<AiStatus>("/ai/status")).data,
    staleTime: 5 * 60_000,
  });
  const status = statusQuery.data;

  useImperativeHandle(ref, () => ({
    focus() {
      sectionRef.current?.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" });
      inputRef.current?.focus({ preventScroll: true });
    },
  }));

  useLayoutEffect(() => {
    const log = logRef.current;
    if (!log || turns.length === 0) return;
    log.scrollTo({ top: log.scrollHeight, behavior: reduced ? "auto" : "smooth" });
  }, [turns.length, loading, reduced]);

  async function ask(q: string) {
    const trimmed = q.trim();
    if (!trimmed || loading) return;
    setLoading(true);
    setPending(trimmed);
    setQuestion("");
    const controller = new AbortController();
    abortRef.current = controller;
    const id = nextId.current++;
    try {
      const resp = await api.post<AiAskResponse>(
        "/ai/ask",
        { question: trimmed, customer_id: customerId },
        { signal: controller.signal },
      );
      setTurns((prev) => [...prev, { id, question: trimmed, response: resp.data }]);
    } catch (err) {
      const message = axios.isCancel(err) ? "Request cancelled." : errorMessage(err);
      setTurns((prev) => [...prev, { id, question: trimmed, error: message }]);
    } finally {
      setLoading(false);
      setPending(null);
      abortRef.current = null;
    }
  }

  const suggestions = customerId ? CUSTOMER_QUESTIONS : PLATFORM_QUESTIONS;

  return (
    <section ref={sectionRef} className="card overflow-hidden scroll-mt-20" aria-labelledby="assistant-title">
      <div className="px-4 sm:px-5 py-4 border-b border-surface-border bg-white/[0.012]">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-3 min-w-0">
            <span className="h-8 w-8 rounded-md bg-accent/10 border border-accent/20 text-accent flex items-center justify-center shrink-0">
              <Icon.Prompt size={15} />
            </span>
            <div className="min-w-0">
              <h3 id="assistant-title" className="section-title">
                Customer360 Intelligence
              </h3>
              <p className="text-xs text-ink-faint mt-0.5">
                Controlled agent · allowlisted, role-checked tools · retrieval over platform documentation
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 sm:justify-end">
            <ProviderStatus status={status} isError={statusQuery.isError} />
            {turns.length > 0 && (
              <button onClick={() => setTurns([])} className="btn-ghost" disabled={loading}>
                Clear
              </button>
            )}
          </div>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
          <span className="text-ink-faint">Context</span>
          {customerId ? (
            <span className="badge bg-white/[0.05] text-ink-muted font-mono">
              <Icon.Customers size={11} />
              {customerId}
            </span>
          ) : (
            <span className="badge bg-white/[0.05] text-ink-muted">Platform documentation only</span>
          )}
        </div>
        {status && !status.configured && (
          <p className="mt-3 text-xs text-ink-faint leading-relaxed max-w-3xl">
            No LLM provider is configured on this deployment, so no natural-language answer is generated. Each response
            still shows exactly which customer tools ran and which documentation was retrieved.
          </p>
        )}
      </div>

      <div ref={logRef} role="log" aria-live="polite" aria-label="Assistant conversation" className="max-h-[36rem] overflow-y-auto px-4 sm:px-5 py-4 space-y-6">
        {turns.length === 0 && !loading && (
          <div>
            <div className="text-xs text-ink-faint mb-2">Suggested questions</div>
            <div className="flex flex-wrap gap-2">
              {suggestions.map((q) => (
                <button
                  key={q}
                  onClick={() => ask(q)}
                  className="text-left text-xs px-2.5 py-1.5 rounded-md border border-surface-border bg-surface-sunken/60 text-ink-muted hover:text-ink hover:border-accent/40 hover:bg-accent/[0.04] transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
        {turns.map((turn) => (
          <TurnView key={turn.id} turn={turn} status={status} onRetry={(q) => void ask(q)} />
        ))}
        {loading && (
          <div className="space-y-3" role="status">
            {pending && (
              <div className="flex items-start gap-2.5">
                <span className="mt-0.5 font-mono text-2xs text-accent/80 shrink-0">Q</span>
                <p className="text-sm text-ink font-medium break-words">{pending}</p>
              </div>
            )}
            <div className="ml-5">
              <div className="flex items-center justify-between gap-3 text-xs text-ink-muted">
                <span>Running agent request…</span>
                <button onClick={() => abortRef.current?.abort()} className="btn-ghost">
                  Stop
                </button>
              </div>
              <div className="mt-2 h-0.5 w-full overflow-hidden rounded-full bg-white/[0.05]" aria-hidden="true">
                <div className="h-full w-full bg-accent/70 origin-left motion-safe:animate-indeterminate motion-reduce:opacity-40" />
              </div>
            </div>
          </div>
        )}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          void ask(question);
        }}
        className="px-4 sm:px-5 py-3 border-t border-surface-border bg-white/[0.012] flex gap-2"
      >
        <label htmlFor="assistant-input" className="sr-only">
          {customerId ? "Ask about this customer" : "Ask about the platform"}
        </label>
        <input
          id="assistant-input"
          ref={inputRef}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          maxLength={MAX_QUESTION}
          placeholder={customerId ? "Ask about this customer…" : "Ask about the platform…"}
          className="input flex-1"
          disabled={loading}
          autoComplete="off"
        />
        <button type="submit" disabled={loading || !question.trim()} className="btn-primary px-4">
          Ask
        </button>
      </form>
    </section>
  );
}
