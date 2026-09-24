import { useRef, useState } from "react";
import axios from "axios";
import { api, errorMessage } from "../lib/api";
import type { AiAskResponse } from "../lib/types";

interface ConversationTurn {
  question: string;
  response?: AiAskResponse;
  error?: string;
}

const SUGGESTED_QUESTIONS = [
  "Why is this customer considered high value?",
  "Explain this customer's RFM profile.",
  "What segments does this customer belong to?",
  "Summarise this customer's recent activity.",
  "What data-quality issues affect this customer?",
  "Why does the system consider these identities the same customer?",
];

export function AiAssistantPanel({ customerId }: { customerId?: string }) {
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<ConversationTurn[]>([]);
  const [loading, setLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  async function ask(q: string) {
    const trimmed = q.trim();
    if (!trimmed || loading) return;
    setLoading(true);
    setQuestion("");
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const resp = await api.post<AiAskResponse>(
        "/ai/ask",
        { question: trimmed, customer_id: customerId },
        { signal: controller.signal }
      );
      setTurns((prev) => [...prev, { question: trimmed, response: resp.data }]);
    } catch (err) {
      if (axios.isCancel(err)) {
        setTurns((prev) => [...prev, { question: trimmed, error: "Request cancelled." }]);
      } else {
        setTurns((prev) => [...prev, { question: trimmed, error: errorMessage(err) }]);
      }
    } finally {
      setLoading(false);
      abortRef.current = null;
    }
  }

  function cancel() {
    abortRef.current?.abort();
  }

  function clearConversation() {
    setTurns([]);
  }

  function retry(q: string) {
    void ask(q);
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="badge bg-accent/10 text-accent hover:bg-accent/20 transition-colors inline-flex items-center gap-1.5"
      >
        <span className="w-1.5 h-1.5 rounded-full bg-accent" />
        Ask about this customer
      </button>
    );
  }

  return (
    <section className="card p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="stat-label flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-accent" />
          Customer360 Intelligence Assistant
        </h2>
        <div className="flex items-center gap-3">
          {turns.length > 0 && (
            <button onClick={clearConversation} className="text-xs text-ink-faint hover:text-ink-muted">
              Clear
            </button>
          )}
          <button onClick={() => setOpen(false)} className="text-xs text-ink-faint hover:text-ink-muted">
            Close
          </button>
        </div>
      </div>

      {customerId ? (
        <div className="text-xs text-ink-faint mb-3 font-mono">
          Context: customer <span className="text-ink-muted">{customerId}</span>
        </div>
      ) : (
        <div className="text-xs text-ink-faint mb-3">Context: platform documentation only (no customer selected)</div>
      )}

      {turns.length === 0 && (
        <div className="mb-4">
          <div className="text-sm text-ink-muted mb-2">Try asking:</div>
          <div className="flex flex-wrap gap-2">
            {SUGGESTED_QUESTIONS.map((q) => (
              <button
                key={q}
                onClick={() => ask(q)}
                className="text-xs px-2.5 py-1.5 rounded border border-surface-border text-ink-muted hover:text-ink hover:border-accent/40 transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-4 max-h-96 overflow-y-auto mb-3">
        {turns.map((turn, i) => (
          <div key={i} className="space-y-1.5">
            <div className="text-sm text-ink font-medium">{turn.question}</div>
            {turn.error && (
              <div className="text-sm text-danger flex items-center gap-2">
                {turn.error}
                <button onClick={() => retry(turn.question)} className="text-xs underline text-ink-faint hover:text-ink-muted">
                  Retry
                </button>
              </div>
            )}
            {turn.response && (
              <div className="rounded border border-surface-border bg-white/5 p-3 space-y-2">
                {!turn.response.configured && (
                  <div className="text-xs px-2 py-1 rounded bg-warn/10 text-warn inline-block">AI provider not configured</div>
                )}
                <div className="text-sm text-ink-muted whitespace-pre-wrap">{turn.response.answer}</div>
                {(turn.response.tools_called.length > 0 || turn.response.tool_denied.length > 0) && (
                  <div className="text-xs text-ink-faint">
                    Tools called: {turn.response.tools_called.length > 0 ? turn.response.tools_called.join(", ") : "none"}
                    {turn.response.tool_denied.length > 0 && (
                      <span className="text-warn"> · Not authorized: {turn.response.tool_denied.join(", ")}</span>
                    )}
                  </div>
                )}
                {turn.response.sources.length > 0 && (
                  <div className="text-xs text-ink-faint">
                    <div className="mb-1">Sources:</div>
                    <ul className="space-y-0.5">
                      {turn.response.sources.map((s, j) => (
                        <li key={j} className="font-mono">
                          {s.source} — {s.section} <span className="text-ink-faint/70">({s.score.toFixed(2)})</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex items-center gap-2 text-sm text-ink-faint">
            <span className="animate-pulse">Thinking…</span>
            <button onClick={cancel} className="text-xs underline hover:text-ink-muted">
              Stop
            </button>
          </div>
        )}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask(question);
        }}
        className="flex gap-2"
      >
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={customerId ? "Ask about this customer…" : "Ask about the platform…"}
          className="flex-1 bg-white/5 border border-surface-border rounded px-3 py-2 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent/50"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="px-3 py-2 rounded bg-accent/15 text-accent text-sm hover:bg-accent/25 disabled:opacity-40 transition-colors"
        >
          Ask
        </button>
      </form>
    </section>
  );
}
