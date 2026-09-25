import React from "react";
import { Link } from "react-router-dom";
import { describeError } from "../lib/api";
import { useCountUp, useMeter } from "../lib/motion";
import { Icon } from "./Icons";

// ---------------------------------------------------------------- formatting

export function formatCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(value);
}

export function formatCompactCurrency(value: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

export function formatInt(value: number): string {
  return Math.round(value).toLocaleString("en-IN");
}

export function formatScore(value: number): string {
  return value.toFixed(1);
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

export function formatCompactInt(value: number): string {
  return new Intl.NumberFormat("en-IN", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

/** 850ms · 48.0s · 14m 07s · 2h 05m */
export function formatDuration(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return "—";
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
  const totalSec = Math.round(ms / 1000);
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  return h > 0 ? `${h}h ${String(m).padStart(2, "0")}m` : `${m}m ${String(s).padStart(2, "0")}s`;
}

const SOURCE_LABELS: Record<string, string> = { crm: "CRM", app: "App", pos: "POS", erp: "ERP" };

/** Source-system codes as people say them (CRM, not "Crm"). */
export function sourceLabel(system: string): string {
  return SOURCE_LABELS[system.toLowerCase()] ?? system.charAt(0).toUpperCase() + system.slice(1);
}

// ---------------------------------------------------------------- tones

export type Tone = "good" | "warn" | "bad" | "neutral" | "info";

export const TONE_TEXT: Record<Tone, string> = {
  good: "text-accent",
  warn: "text-warn",
  bad: "text-danger",
  neutral: "text-ink-muted",
  info: "text-info",
};

export const TONE_BG: Record<Tone, string> = {
  good: "bg-accent",
  warn: "bg-warn",
  bad: "bg-danger",
  neutral: "bg-ink-faint",
  info: "bg-info",
};

const TONE_BADGE: Record<Tone, string> = {
  good: "bg-accent/10 text-accent",
  warn: "bg-warn/10 text-warn",
  bad: "bg-danger/10 text-danger",
  neutral: "bg-white/[0.06] text-ink-muted",
  info: "bg-info/10 text-info",
};

/** Same thresholds the Data Quality screen has always used. */
export function scoreTone(score: number | null | undefined): Tone {
  if (score === null || score === undefined) return "neutral";
  if (score >= 98) return "good";
  if (score >= 90) return "warn";
  return "bad";
}

export function scoreLabel(score: number | null | undefined): string {
  const tone = scoreTone(score);
  return tone === "good" ? "Healthy" : tone === "warn" ? "Watch" : tone === "bad" ? "Failing" : "No data";
}

// ---------------------------------------------------------------- layout

export function PageHeader({
  title,
  subtitle,
  actions,
  crumbs,
  meta,
}: {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  actions?: React.ReactNode;
  crumbs?: { label: string; to?: string }[];
  /** full-width row under the title (e.g. an entity's key facts) */
  meta?: React.ReactNode;
}) {
  return (
    <header className="px-4 sm:px-6 lg:px-8 pt-5 pb-5 border-b border-surface-border">
      {crumbs && crumbs.length > 0 && (
        <nav aria-label="Breadcrumb" className="mb-2">
          <ol className="flex items-center gap-1 text-xs text-ink-faint">
            {crumbs.map((c, i) => (
              <li key={i} className="flex items-center gap-1 min-w-0">
                {i > 0 && <Icon.ChevronRight size={12} className="shrink-0 opacity-60" />}
                {c.to ? (
                  <Link to={c.to} className="hover:text-ink transition-colors truncate">
                    {c.label}
                  </Link>
                ) : (
                  <span className="text-ink-muted truncate font-mono" aria-current="page">
                    {c.label}
                  </span>
                )}
              </li>
            ))}
          </ol>
        </nav>
      )}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h1 className="text-xl font-semibold text-ink tracking-tight">{title}</h1>
          {subtitle && <p className="text-sm text-ink-muted mt-1 max-w-2xl">{subtitle}</p>}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2 shrink-0">{actions}</div>}
      </div>
      {meta && <div className="mt-4">{meta}</div>}
    </header>
  );
}

/** Inline key-facts row: label over value, wraps on narrow screens. */
export function FactStrip({ facts }: { facts: { label: string; value: React.ReactNode; hint?: string }[] }) {
  return (
    <dl className="flex flex-wrap gap-x-8 gap-y-3">
      {facts.map((f) => (
        <div key={f.label} className="min-w-0">
          <dt className="stat-label">{f.label}</dt>
          <dd className="mt-1 text-sm font-medium text-ink tabular-nums">
            {f.value}
            {f.hint && <span className="ml-1.5 text-xs font-normal text-ink-faint">{f.hint}</span>}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function PageBody({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`px-4 sm:px-6 lg:px-8 py-6 ${className}`}>{children}</div>;
}

export function SectionHeader({
  title,
  description,
  index,
  actions,
}: {
  title: string;
  description?: string;
  index?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-3 mb-4">
      <div className="flex items-baseline gap-2.5 min-w-0">
        {index && <span className="font-mono text-2xs text-accent/70 tabular-nums">{index}</span>}
        <div className="min-w-0">
          <h2 className="section-title">{title}</h2>
          {description && <p className="text-xs text-ink-faint mt-0.5">{description}</p>}
        </div>
      </div>
      {actions}
    </div>
  );
}

// ---------------------------------------------------------------- numbers

export function AnimatedNumber({
  value,
  format = formatInt,
  className = "",
}: {
  value: number | null | undefined;
  format?: (n: number) => string;
  className?: string;
}) {
  const ref = useCountUp(value, format);
  return (
    <span ref={ref} className={`tabular-nums ${className}`}>
      {value === null || value === undefined ? "—" : format(value)}
    </span>
  );
}

export function Meter({ value, max = 100, tone = "good", label }: { value: number | null | undefined; max?: number; tone?: Tone; label?: string }) {
  const ref = useMeter(value);
  const pct = value === null || value === undefined ? 0 : Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div
      className="meter"
      role="meter"
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuenow={value ?? undefined}
      aria-label={label}
    >
      <span ref={ref} className={TONE_BG[tone]} style={{ width: `${pct}%` }} />
    </div>
  );
}

export function StatTile({
  label,
  value,
  count,
  format,
  sub,
  tone,
  meter,
  emphasis = false,
  className = "",
}: {
  label: string;
  value?: React.ReactNode;
  /** numeric value to count up on first render (takes precedence over `value`) */
  count?: number | null;
  format?: (n: number) => string;
  sub?: React.ReactNode;
  tone?: Tone;
  /** optional 0-100 meter under the value */
  meter?: { value: number | null | undefined; tone?: Tone; max?: number };
  emphasis?: boolean;
  className?: string;
}) {
  return (
    <div data-reveal-item data-reveal className={`card px-4 py-3.5 min-w-0 ${className}`}>
      <div className="stat-label leading-snug">{label}</div>
      <div
        className={`mt-1.5 font-semibold tracking-tight tabular-nums leading-tight break-words ${emphasis ? "text-lg sm:text-2xl lg:text-xl xl:text-2xl" : "text-base sm:text-lg"} ${
          tone ? TONE_TEXT[tone] : "text-ink"
        }`}
      >
        {count !== undefined ? <AnimatedNumber value={count} format={format} /> : value}
      </div>
      {meter && (
        <div className="mt-2.5">
          <Meter value={meter.value} max={meter.max} tone={meter.tone ?? scoreTone(meter.value)} label={label} />
        </div>
      )}
      {sub && <div className="text-xs text-ink-faint mt-1 truncate">{sub}</div>}
    </div>
  );
}

// ---------------------------------------------------------------- states

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton ${className}`} aria-hidden="true" />;
}

export function SkeletonTiles({ count = 4, className = "" }: { count?: number; className?: string }) {
  return (
    <div className={`grid grid-cols-2 md:grid-cols-4 gap-3 ${className}`} aria-hidden="true">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="card px-4 py-3.5">
          <Skeleton className="h-2.5 w-20" />
          <Skeleton className="h-5 w-24 mt-3" />
        </div>
      ))}
    </div>
  );
}

export function SkeletonTable({ rows = 6, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <div className="card overflow-hidden" aria-hidden="true">
      <div className="px-4 py-3 border-b border-surface-border bg-white/[0.015] flex gap-6">
        {Array.from({ length: cols }, (_, i) => (
          <Skeleton key={i} className="h-2.5 flex-1 max-w-[90px]" />
        ))}
      </div>
      {Array.from({ length: rows }, (_, r) => (
        <div key={r} className="px-4 py-3.5 border-b border-surface-border/60 last:border-b-0 flex gap-6">
          {Array.from({ length: cols }, (_, c) => (
            <Skeleton key={c} className={`h-3 flex-1 ${c === 0 ? "max-w-[160px]" : "max-w-[100px]"}`} />
          ))}
        </div>
      ))}
    </div>
  );
}

/** Screen-reader announcement + skeleton content for a loading region. */
export function Loading({ label = "Loading", children }: { label?: string; children: React.ReactNode }) {
  return (
    <div role="status" aria-live="polite">
      <span className="sr-only">{label}…</span>
      {children}
    </div>
  );
}

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="flex items-center justify-center gap-2.5 py-16 text-ink-muted text-sm">
      <span
        className="h-3.5 w-3.5 rounded-full border-2 border-ink-faint/30 border-t-accent motion-safe:animate-spin"
        aria-hidden="true"
      />
      {label}
    </div>
  );
}

/**
 * Failed request. When the query's `error` is passed, the panel says what the
 * API actually returned (HTTP status + its message) and shows the request id
 * an operator can quote -- instead of a generic "something went wrong".
 */
export function ErrorState({
  message,
  error,
  onRetry,
  retrying = false,
}: {
  message: string;
  error?: unknown;
  onRetry?: () => void;
  retrying?: boolean;
}) {
  const info = error === undefined ? null : describeError(error);
  return (
    <div role="alert" className="state-panel flex flex-col items-center justify-center text-center py-14 gap-3">
      <span className="h-9 w-9 rounded-full bg-danger/10 text-danger flex items-center justify-center">
        <Icon.Alert />
      </span>
      <div>
        <div className="text-sm text-ink">{message}</div>
        <div className="text-xs text-ink-faint mt-0.5">{info ? info.detail : "The API returned an error or could not be reached."}</div>
        {info?.requestId && (
          <div className="text-2xs text-ink-faint mt-1.5">
            Request ID <span className="font-mono text-ink-muted select-all">{info.requestId}</span>
          </div>
        )}
      </div>
      {onRetry && (
        <button onClick={onRetry} disabled={retrying} className="btn-secondary text-xs px-3 py-1.5">
          <Icon.Refresh size={13} className={retrying ? "motion-safe:animate-spin" : ""} />
          {retrying ? "Retrying…" : "Retry"}
        </button>
      )}
    </div>
  );
}

export function EmptyState({ message, hint, action }: { message: string; hint?: string; action?: React.ReactNode }) {
  return (
    <div className="state-panel flex flex-col items-center justify-center text-center py-14 gap-2">
      <span className="h-9 w-9 rounded-full bg-white/[0.04] text-ink-faint flex items-center justify-center">
        <Icon.Info />
      </span>
      <div className="text-sm text-ink-muted">{message}</div>
      {hint && <div className="text-xs text-ink-faint max-w-sm">{hint}</div>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

/**
 * Decorative share-of-max bar (the number beside it carries the meaning, so
 * it is aria-hidden). Grows from the left on first render; `delay` lets it
 * follow its container's entrance.
 */
export function ShareBar({
  pct,
  className = "bg-accent/50",
  delay,
  animateKey = true,
}: {
  pct: number;
  className?: string;
  delay?: number;
  animateKey?: unknown;
}) {
  const ref = useMeter(animateKey, delay);
  return (
    <div className="meter" aria-hidden="true">
      <span ref={ref} className={className} style={{ width: `${Math.max(0, Math.min(100, pct))}%` }} />
    </div>
  );
}

// ---------------------------------------------------------------- badges

export function StatusDot({ tone, pulse = false }: { tone: Tone; pulse?: boolean }) {
  return (
    <span className="relative inline-flex h-1.5 w-1.5 shrink-0" aria-hidden="true">
      {pulse && <span className={`absolute inset-0 rounded-full ${TONE_BG[tone]} motion-safe:animate-ping opacity-60`} />}
      <span className={`relative inline-flex h-1.5 w-1.5 rounded-full ${TONE_BG[tone]}`} />
    </span>
  );
}

export function ToneBadge({ tone, children, dot = true, pulse = false }: { tone: Tone; children: React.ReactNode; dot?: boolean; pulse?: boolean }) {
  return (
    <span className={`badge ${TONE_BADGE[tone]}`}>
      {dot && <StatusDot tone={tone} pulse={pulse} />}
      {children}
    </span>
  );
}

const BAND_TONES: Record<string, Tone> = {
  active: "good",
  at_risk: "warn",
  churned: "bad",
  no_purchase_history: "neutral",
};

export function ChurnBadge({ band }: { band: string | null }) {
  if (!band) return <span className="text-ink-faint">—</span>;
  return <ToneBadge tone={BAND_TONES[band] ?? "neutral"}>{band.replace(/_/g, " ")}</ToneBadge>;
}

const STATUS_TONES: Record<string, Tone> = {
  succeeded: "good",
  completed: "good",
  success: "good",
  running: "info",
  pending: "neutral",
  skipped: "neutral",
  cancelled: "neutral",
  refunded: "warn",
  failed: "bad",
  error: "bad",
};

/** `running` gets a soft ping (it is genuinely in progress); finished states are static. */
export function StatusBadge({ status }: { status: string }) {
  const tone = STATUS_TONES[status] ?? "neutral";
  return (
    <ToneBadge tone={tone} pulse={status === "running"}>
      {status}
    </ToneBadge>
  );
}
