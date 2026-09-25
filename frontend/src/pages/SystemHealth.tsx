import { useQuery } from "@tanstack/react-query";
import { useReveal } from "../lib/motion";
import { api } from "../lib/api";
import {
  AnimatedNumber,
  ErrorState,
  Loading,
  PageBody,
  PageHeader,
  SectionHeader,
  SkeletonTiles,
  StatTile,
  StatusDot,
  TONE_BG,
  TONE_TEXT,
  formatDateTime,
  type Tone,
} from "../components/Common";
import { Icon } from "../components/Icons";

interface HealthDetail {
  status: string;
  database: string;
  last_successful_run: { run_id: number; finished_at: string } | null;
  row_counts: Record<string, number>;
}

const REFRESH_MS = 30_000;

function healthTone(value: string): Tone {
  const v = value.toLowerCase();
  if (v === "ok" || v === "up" || v === "healthy") return "good";
  if (v === "degraded") return "warn";
  return "bad";
}

function StatusValue({ value }: { value: string }) {
  const tone = healthTone(value);
  return (
    <span className={`inline-flex items-center gap-2 ${TONE_TEXT[tone]}`}>
      <StatusDot tone={tone} />
      <span className={value.length <= 2 ? "uppercase" : "capitalize"}>{value}</span>
    </span>
  );
}

function overallTone(d: HealthDetail): Tone {
  const tones = [healthTone(d.status), healthTone(d.database)];
  return tones.includes("bad") ? "bad" : tones.includes("warn") ? "warn" : "good";
}

const OVERALL_TITLE: Record<string, string> = {
  good: "All systems operational",
  warn: "Degraded performance",
  bad: "Service disruption",
};

/**
 * The page's one-line answer, derived only from the two checks the API
 * reports. The hairline at the bottom fills over the refresh interval and
 * restarts on every check, so "live" is visible rather than claimed.
 */
function StatusBanner({ data, checkedAt }: { data: HealthDetail; checkedAt: number }) {
  const tone = overallTone(data);
  const box = { good: "border-accent/20 bg-accent/[0.04]", warn: "border-warn/25 bg-warn/[0.05]", bad: "border-danger/25 bg-danger/[0.05]" }[
    tone as "good" | "warn" | "bad"
  ];
  return (
    <section data-reveal className={`relative overflow-hidden rounded-lg border px-4 py-3.5 sm:px-5 ${box}`} aria-live="polite">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
        <div className="flex items-center gap-2.5 min-w-0">
          <StatusDot tone={tone} />
          <h2 className={`text-sm font-semibold ${TONE_TEXT[tone]}`}>{OVERALL_TITLE[tone]}</h2>
        </div>
        <p className="text-xs text-ink-faint sm:text-right">
          API <span className="text-ink-muted">{data.status}</span> · database <span className="text-ink-muted">{data.database}</span>
          {data.last_successful_run && (
            <>
              {" "}
              · last run <span className="font-mono text-ink-muted">#{data.last_successful_run.run_id}</span> finished{" "}
              {formatDateTime(data.last_successful_run.finished_at)}
            </>
          )}
        </p>
      </div>
      <span
        key={checkedAt}
        className={`absolute left-0 bottom-0 h-px w-full origin-left animate-countdown motion-reduce:hidden ${TONE_BG[tone]} opacity-40`}
        style={{ animationDuration: `${REFRESH_MS}ms` }}
        aria-hidden="true"
      />
    </section>
  );
}

export default function SystemHealth() {
  const { data, error, isLoading, isError, isFetching, dataUpdatedAt, refetch } = useQuery({
    queryKey: ["health-detail"],
    queryFn: async () => (await api.get<HealthDetail>("/health/detail")).data,
    refetchInterval: REFRESH_MS,
  });
  // Keyed on "has data", so the 30s background refresh never replays the entrance.
  const revealRef = useReveal(!!data);
  const rowCounts = data ? Object.entries(data.row_counts).sort(([a], [b]) => a.localeCompare(b)) : [];

  return (
    <div>
      <PageHeader
        title="System Health"
        subtitle="Live dependency status for the serving layer and the most recent pipeline run."
        actions={
          <div className="flex items-center gap-3">
            {dataUpdatedAt > 0 && (
              <span className="text-xs text-ink-faint hidden sm:inline">
                Checked {new Date(dataUpdatedAt).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" })} · every 30s
              </span>
            )}
            <button onClick={() => refetch()} disabled={isFetching} className="btn-secondary text-xs px-2.5 py-1.5" aria-label="Refresh health status">
              <Icon.Refresh size={13} className={isFetching ? "motion-safe:animate-spin" : ""} />
              Refresh
            </button>
          </div>
        }
      />
      <PageBody>
        {isLoading && (
          <Loading label="Checking system health">
            <SkeletonTiles />
          </Loading>
        )}
        {isError && <ErrorState message="Could not reach the health endpoint." error={error} onRetry={() => refetch()} retrying={isFetching} />}
        {data && (
          <div ref={revealRef} className="space-y-6">
            <StatusBanner data={data} checkedAt={dataUpdatedAt} />
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <StatTile label="API status" value={<StatusValue value={data.status} />} />
              <StatTile label="Database" value={<StatusValue value={data.database} />} />
              <StatTile
                label="Last successful run"
                value={data.last_successful_run ? <span className="font-mono">#{data.last_successful_run.run_id}</span> : "—"}
                sub={data.last_successful_run ? formatDateTime(data.last_successful_run.finished_at) : "No successful run yet"}
              />
              <StatTile label="Customers loaded" count={data.row_counts.customers ?? 0} />
            </div>

            {rowCounts.length > 0 && (
              <section data-reveal className="card p-4 sm:p-5">
                <SectionHeader title="Serving-layer row counts" description="Rows currently in each table the API reads from." />
                <dl className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-6">
                  {rowCounts.map(([table, count]) => (
                    <div key={table} className="flex items-center justify-between gap-3 py-2.5 border-b border-surface-border/60">
                      <dt className="font-mono text-xs text-ink-muted truncate">{table}</dt>
                      <dd className="text-sm text-ink font-medium">
                        <AnimatedNumber value={count} />
                      </dd>
                    </div>
                  ))}
                </dl>
              </section>
            )}
          </div>
        )}
      </PageBody>
    </div>
  );
}
