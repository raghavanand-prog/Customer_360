import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import type { AnalyticsSummary } from "../lib/types";
import { useReveal } from "../lib/motion";
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
  TONE_TEXT,
  formatCurrency,
  formatScore,
  scoreLabel,
  scoreTone,
} from "../components/Common";
import { Icon } from "../components/Icons";
import { RecentRunsPanel, RevenueTrendPanel, SegmentsPanel, TopCustomersPanel } from "../components/OverviewPanels";

function pct(part: number, total: number): string {
  if (!total) return "0%";
  return `${((part / total) * 100).toFixed(1)}%`;
}

function CustomerBaseCard({ data }: { data: AnalyticsSummary }) {
  const other = Math.max(0, data.total_customers - data.active_customers - data.at_risk_customers);
  const parts = [
    { label: "Active", value: data.active_customers, bar: "bg-positive", dot: "bg-positive" },
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
        className="mt-5 flex h-2 w-full overflow-hidden rounded-full bg-white/[0.05]"
        role="img"
        aria-label={parts.map((p) => `${p.label} ${pct(p.value, data.total_customers)}`).join(", ")}
      >
        {parts.map((p) => (
          <span key={p.label} className={`${p.bar} h-full first:rounded-l-full last:rounded-r-full`} style={{ width: pct(p.value, data.total_customers) }} />
        ))}
      </div>
      <dl className="mt-4 grid grid-cols-3 gap-3">
        {parts.map((p) => (
          <div key={p.label} className="min-w-0">
            <dt className="flex items-center gap-1.5 text-xs text-ink-faint">
              <span className={`h-1.5 w-1.5 rounded-full ${p.dot}`} aria-hidden="true" />
              {p.label}
            </dt>
            <dd className="mt-1 serif-num font-light text-3xl text-ink">
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
        <div className={`serif-num font-light text-5xl ${TONE_TEXT[tone]}`}>
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

export default function Overview() {
  const { data, isLoading, isError, refetch } = useQuery({
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
        {isError && <ErrorState message="Could not load the platform summary." onRetry={() => refetch()} />}
        {data && (
          <div ref={revealRef} className="space-y-4">
            <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
              <StatTile label="Total customers" count={data.total_customers} emphasis />
              <StatTile label="Revenue" count={data.total_revenue} format={formatCurrency} emphasis />
              <StatTile label="Orders" count={data.total_orders} emphasis />
              <StatTile label="Average order value" count={data.avg_aov} format={formatCurrency} emphasis />
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <CustomerBaseCard data={data} />
              <DataHealthCard data={data} />
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <RevenueTrendPanel />
              <SegmentsPanel />
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <RecentRunsPanel />
              <TopCustomersPanel />
            </div>
          </div>
        )}
        {!isLoading && !isError && !data && <EmptyState message="No data yet." hint="Run the pipeline to populate the platform." />}
      </PageBody>
    </div>
  );
}
