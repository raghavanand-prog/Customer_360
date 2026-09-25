import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import type { AnalyticsSummary, PipelineRun } from "../lib/types";
import { useMeter, useReveal } from "../lib/motion";
import {
  AnimatedNumber,
  EmptyState,
  ErrorState,
  Loading,
  Meter,
  PageBody,
  PageHeader,
  SkeletonTiles,
  Skeleton,
  StatTile,
  StatusDot,
  TONE_TEXT,
  formatCompactCurrency,
  formatCurrency,
  formatDateTime,
  formatDuration,
  formatScore,
  scoreLabel,
  scoreTone,
  type Tone,
} from "../components/Common";
import { Icon } from "../components/Icons";

function pct(part: number, total: number): string {
  if (!total) return "0%";
  return `${((part / total) * 100).toFixed(1)}%`;
}

function CustomerBaseCard({ data }: { data: AnalyticsSummary }) {
  const sweepRef = useMeter<HTMLDivElement>(data.total_customers, 220);
  const other = Math.max(0, data.total_customers - data.active_customers - data.at_risk_customers);
  const parts = [
    { label: "Active", value: data.active_customers, bar: "bg-accent", dot: "bg-accent" },
    { label: "At risk", value: data.at_risk_customers, bar: "bg-warn", dot: "bg-warn" },
    { label: "Other bands", value: other, bar: "bg-white/15", dot: "bg-ink-faint" },
  ];
  return (
    <section data-reveal className="card p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="section-title">Customer base by churn band</h2>
          <p className="text-xs text-ink-faint mt-0.5">From customer_metrics.churn_risk_band on the latest load.</p>
        </div>
        <Link to="/customers" className="btn-ghost shrink-0">
          Browse
          <Icon.ChevronRight size={12} />
        </Link>
      </div>
      <div
        className="mt-5 h-2 w-full overflow-hidden rounded-full bg-white/[0.05]"
        role="img"
        aria-label={parts.map((p) => `${p.label} ${pct(p.value, data.total_customers)}`).join(", ")}
      >
        {/* One sweep for the whole distribution, so the bands read as parts of a single total. */}
        <div ref={sweepRef} className="flex h-full w-full origin-left">
          {parts.map((p) => (
            <span key={p.label} className={`${p.bar} h-full`} style={{ width: pct(p.value, data.total_customers) }} />
          ))}
        </div>
      </div>
      <dl className="mt-4 grid grid-cols-3 gap-3">
        {parts.map((p) => (
          <div key={p.label} className="min-w-0">
            <dt className="flex items-center gap-1.5 text-xs text-ink-faint">
              <span className={`h-1.5 w-1.5 rounded-full ${p.dot}`} aria-hidden="true" />
              {p.label}
            </dt>
            <dd className="mt-1 text-base font-semibold text-ink">
              <AnimatedNumber value={p.value} />
            </dd>
            <dd className="text-xs text-ink-faint tabular-nums">{pct(p.value, data.total_customers)}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function DataHealthCard({ data }: { data: AnalyticsSummary }) {
  const tone = scoreTone(data.dq_score);
  return (
    <section data-reveal className="card p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="section-title">Data health</h2>
          <p className="text-xs text-ink-faint mt-0.5">Platform DQ score from the latest successful pipeline run.</p>
        </div>
        <Link to="/quality" className="btn-ghost shrink-0">
          Details
          <Icon.ChevronRight size={12} />
        </Link>
      </div>
      <div className="mt-5 flex items-end justify-between gap-3">
        <div className={`text-3xl font-semibold tracking-tight ${TONE_TEXT[tone]}`}>
          {data.dq_score !== null && data.dq_score !== undefined ? <AnimatedNumber value={data.dq_score} format={formatScore} /> : "—"}
          <span className="text-sm font-normal text-ink-faint ml-1">/ 100</span>
        </div>
        <span className={`text-xs ${TONE_TEXT[tone]}`}>{scoreLabel(data.dq_score)}</span>
      </div>
      <div className="mt-3">
        <Meter value={data.dq_score} tone={tone} label="Platform data quality score" />
      </div>
      <div className="mt-4 pt-4 border-t border-surface-border flex items-center justify-between text-xs">
        <span className="text-ink-faint">Last pipeline run</span>
        {data.last_run_id ? (
          <Link to="/pipeline" className="font-mono text-ink-muted hover:text-accent transition-colors">
            #{data.last_run_id}
          </Link>
        ) : (
          <span className="text-ink-faint">—</span>
        )}
      </div>
    </section>
  );
}

const STATUS_DOT: Record<string, Tone> = { succeeded: "good", completed: "good", running: "info", failed: "bad", error: "bad" };

/** Latest runs from the same endpoint (and query cache) the Pipeline Runs screen uses. */
function RecentRunsCard() {
  const runs = useQuery({
    queryKey: ["pipeline-runs"],
    queryFn: async () => (await api.get<{ items: PipelineRun[] }>("/pipeline/runs")).data.items,
  });
  const recent = runs.data?.slice(0, 4) ?? [];
  const latest = recent[0];

  return (
    <section data-reveal className="card p-5 lg:col-span-2 xl:col-span-1 flex flex-col">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="section-title">Recent pipeline runs</h2>
          <p className="text-xs text-ink-faint mt-0.5">
            {latest ? (
              <>
                Latest run <span className={TONE_TEXT[STATUS_DOT[latest.status] ?? "neutral"]}>{latest.status}</span>
                {latest.duration_ms !== null && <> in {formatDuration(latest.duration_ms)}</>}.
              </>
            ) : (
              "Ingestion through segmentation, newest first."
            )}
          </p>
        </div>
        <Link to="/pipeline" className="btn-ghost shrink-0">
          All runs
          <Icon.ChevronRight size={12} />
        </Link>
      </div>
      {runs.isLoading && (
        <Loading label="Loading recent runs">
          <div className="mt-4 space-y-3">
            {Array.from({ length: 4 }, (_, i) => (
              <Skeleton key={i} className="h-4 w-full" />
            ))}
          </div>
        </Loading>
      )}
      {runs.isError && (
        <p role="alert" className="mt-4 text-xs text-ink-faint">
          Could not load pipeline runs.{" "}
          <button onClick={() => runs.refetch()} className="text-ink-muted hover:text-ink underline underline-offset-2">
            Retry
          </button>
        </p>
      )}
      {runs.data && recent.length === 0 && <p className="mt-4 text-xs text-ink-faint">No pipeline runs yet.</p>}
      {recent.length > 0 && (
        <ol className="mt-3 -mx-2 flex-1">
          {recent.map((r) => (
            <li key={r.run_id}>
              <Link
                to="/pipeline"
                className="flex items-center gap-3 rounded-md px-2 py-2 text-xs hover:bg-white/[0.03] transition-colors"
              >
                <StatusDot tone={STATUS_DOT[r.status] ?? "neutral"} pulse={r.status === "running"} />
                <span className="font-mono text-ink w-10 shrink-0">#{r.run_id}</span>
                <span className="text-ink-faint truncate flex-1 min-w-0">
                  {formatDateTime(r.started_at)} · {r.dataset_size}
                </span>
                <span className="tabular-nums text-ink-muted shrink-0">{formatDuration(r.duration_ms)}</span>
              </Link>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

export default function Overview() {
  const { data, isLoading, isError, error, isFetching, refetch } = useQuery({
    queryKey: ["analytics-summary"],
    queryFn: async () => (await api.get<AnalyticsSummary>("/analytics/summary")).data,
  });
  const revealRef = useReveal(!!data);

  return (
    <div>
      <PageHeader title="Overview" subtitle="Platform health, customer, commerce, and pipeline signals at a glance." />
      <PageBody>
        {isLoading && (
          <Loading label="Loading platform summary">
            <SkeletonTiles />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
              <Skeleton className="h-44 rounded-lg" />
              <Skeleton className="h-44 rounded-lg" />
            </div>
          </Loading>
        )}
        {isError && <ErrorState message="Could not load the platform summary." error={error} onRetry={() => refetch()} retrying={isFetching} />}
        {data && (
          <div ref={revealRef} className="space-y-4">
            <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
              <StatTile
                label="Total customers"
                count={data.total_customers}
                emphasis
                sub={data.total_customers ? `${pct(data.active_customers, data.total_customers)} active` : undefined}
              />
              {/* Compact headline, exact figure underneath: scannable without losing precision. */}
              <StatTile label="Revenue" count={data.total_revenue} format={formatCompactCurrency} sub={formatCurrency(data.total_revenue)} emphasis />
              <StatTile label="Orders" count={data.total_orders} emphasis />
              <StatTile label="Average order value" count={data.avg_aov} format={formatCurrency} emphasis />
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
              <CustomerBaseCard data={data} />
              <DataHealthCard data={data} />
              <RecentRunsCard />
            </div>
          </div>
        )}
        {!isLoading && !isError && !data && <EmptyState message="No data yet." hint="Run the pipeline to populate the platform." />}
      </PageBody>
    </div>
  );
}
