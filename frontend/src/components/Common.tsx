import React from "react";

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between px-6 py-5 border-b border-surface-border">
      <div>
        <h1 className="text-lg font-semibold text-ink">{title}</h1>
        {subtitle && <p className="text-sm text-ink-muted mt-0.5">{subtitle}</p>}
      </div>
      {actions}
    </div>
  );
}

export function StatTile({ label, value, sub }: { label: string; value: React.ReactNode; sub?: string }) {
  return (
    <div className="card px-4 py-3">
      <div className="stat-label">{label}</div>
      <div className="text-xl font-semibold text-ink mt-1">{value}</div>
      {sub && <div className="text-xs text-ink-faint mt-0.5">{sub}</div>}
    </div>
  );
}

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center py-16 text-ink-muted text-sm">
      <span className="animate-pulse">{label}</span>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3">
      <div className="text-danger text-sm">{message}</div>
      {onRetry && (
        <button onClick={onRetry} className="text-xs px-3 py-1.5 rounded border border-surface-border text-ink-muted hover:text-ink">
          Retry
        </button>
      )}
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return <div className="flex items-center justify-center py-16 text-ink-faint text-sm">{message}</div>;
}

const BAND_COLORS: Record<string, string> = {
  active: "bg-accent/15 text-accent",
  at_risk: "bg-warn/15 text-warn",
  churned: "bg-danger/15 text-danger",
  no_purchase_history: "bg-white/10 text-ink-muted",
};

export function ChurnBadge({ band }: { band: string | null }) {
  if (!band) return <span className="text-ink-faint">—</span>;
  return <span className={`badge ${BAND_COLORS[band] ?? "bg-white/10 text-ink-muted"}`}>{band.replace(/_/g, " ")}</span>;
}

export function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    succeeded: "bg-accent/15 text-accent",
    running: "bg-warn/15 text-warn",
    failed: "bg-danger/15 text-danger",
  };
  return <span className={`badge ${colors[status] ?? "bg-white/10 text-ink-muted"}`}>{status}</span>;
}

export function formatCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(value);
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}
