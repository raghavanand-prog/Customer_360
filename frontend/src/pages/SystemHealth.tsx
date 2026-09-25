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

export default function SystemHealth() {
  const { data, isLoading, isError, isFetching, dataUpdatedAt, refetch } = useQuery({
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
        {isError && <ErrorState message="Could not reach the health endpoint." onRetry={() => refetch()} />}
        {data && (
          <div ref={revealRef} className="space-y-6">
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
