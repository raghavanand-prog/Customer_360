import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { PipelineRun } from "../lib/types";
import { useReveal } from "../lib/motion";
import {
  EmptyState,
  ErrorState,
  Loading,
  PageBody,
  PageHeader,
  SectionHeader,
  Skeleton,
  SkeletonTable,
  StatusBadge,
  StatusDot,
  formatDateTime,
  formatDuration,
  formatInt,
  type Tone,
} from "../components/Common";

interface StageRun {
  stage_run_id: number;
  stage_name: string;
  stage_order: number;
  status: string;
  rows_in: number | null;
  rows_out: number | null;
  rows_quarantined: number | null;
  duration_ms: number | null;
}

const NODE_TONE: Record<string, Tone> = { succeeded: "good", completed: "good", running: "info", failed: "bad", error: "bad" };

function StageTimeline({ runId }: { runId: number }) {
  const stages = useQuery({
    queryKey: ["pipeline-stages", runId],
    queryFn: async () => (await api.get<{ items: StageRun[] }>(`/pipeline/runs/${runId}/stages`)).data.items,
  });
  const revealRef = useReveal<HTMLOListElement>(stages.data ? runId : null, { step: 35, distance: 6 });
  const maxDuration = stages.data?.reduce((m, s) => Math.max(m, s.duration_ms ?? 0), 0) ?? 0;

  if (stages.isLoading)
    return (
      <Loading label="Loading stages">
        <div className="space-y-4">
          {Array.from({ length: 6 }, (_, i) => (
            <div key={i} className="flex gap-3">
              <Skeleton className="h-3 w-3 rounded-full" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-3 w-40" />
                <Skeleton className="h-2.5 w-24" />
              </div>
            </div>
          ))}
        </div>
      </Loading>
    );
  if (stages.isError) return <ErrorState message="Could not load stages for this run." onRetry={() => stages.refetch()} />;
  if (!stages.data || stages.data.length === 0) return <EmptyState message="No stage records for this run." />;

  return (
    <ol ref={revealRef} className="relative">
      {stages.data.map((s, i) => {
        const tone = NODE_TONE[s.status] ?? "neutral";
        const last = i === stages.data!.length - 1;
        const share = maxDuration && s.duration_ms ? (s.duration_ms / maxDuration) * 100 : 0;
        return (
          <li key={s.stage_run_id} data-reveal className="relative flex gap-3 pb-4 last:pb-0">
            {!last && <span className="absolute left-[5px] top-4 bottom-0 w-px bg-surface-border" aria-hidden="true" />}
            <span className="relative mt-1.5 h-[11px] w-[11px] rounded-full border border-surface-strong bg-surface-raised flex items-center justify-center shrink-0">
              <StatusDot tone={tone} pulse={s.status === "running"} />
            </span>
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-sm text-ink truncate">
                    <span className="font-mono text-2xs text-ink-faint mr-2 tabular-nums">{String(s.stage_order).padStart(2, "0")}</span>
                    {s.stage_name}
                  </div>
                  <div className="text-xs text-ink-faint mt-0.5 tabular-nums">
                    {s.rows_in !== null ? formatInt(s.rows_in) : "—"} in → {s.rows_out !== null ? formatInt(s.rows_out) : "—"} out
                    {s.rows_quarantined ? <span className="text-warn">, {formatInt(s.rows_quarantined)} quarantined</span> : null}
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <StatusBadge status={s.status} />
                </div>
              </div>
              <div className="mt-2 flex items-center gap-2">
                <div className="meter flex-1" aria-hidden="true">
                  <span className="bg-info/50" style={{ width: `${share}%` }} />
                </div>
                <span className="text-2xs text-ink-faint tabular-nums w-14 text-right">{formatDuration(s.duration_ms)}</span>
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

export default function PipelineRuns() {
  const [selected, setSelected] = useState<number | null>(null);

  const runs = useQuery({
    queryKey: ["pipeline-runs"],
    queryFn: async () => (await api.get<{ items: PipelineRun[] }>("/pipeline/runs")).data.items,
  });
  const revealRef = useReveal(!!runs.data?.length);
  // Default to the most recent run so the stage view is never empty on arrival.
  const activeRun = selected ?? runs.data?.[0]?.run_id ?? null;

  return (
    <div>
      <PageHeader title="Pipeline Runs" subtitle="Ingestion through segmentation, one row per stage, with record counts and durations." />
      <PageBody>
        {runs.isLoading && (
          <Loading label="Loading pipeline runs">
            <SkeletonTable rows={5} cols={5} />
          </Loading>
        )}
        {runs.isError && <ErrorState message="Could not load pipeline runs." onRetry={() => runs.refetch()} />}
        {runs.data && runs.data.length === 0 && <EmptyState message="No pipeline runs yet." />}
        {runs.data && runs.data.length > 0 && (
          <div ref={revealRef} className="grid grid-cols-1 xl:grid-cols-5 gap-4 items-start">
            <section data-reveal className="card overflow-hidden xl:col-span-3">
              <div className="px-4 sm:px-5 pt-4 sm:pt-5">
                <SectionHeader title="Runs" description="Select a run to inspect its stages." />
              </div>
              <div className="overflow-x-auto border-t border-surface-border">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Run</th>
                      <th>Size</th>
                      <th>Status</th>
                      <th>Started</th>
                      <th className="text-right">Duration</th>
                    </tr>
                  </thead>
                  <tbody>
                    {runs.data.map((r) => {
                      const isActive = r.run_id === activeRun;
                      return (
                        <tr
                          key={r.run_id}
                          onClick={() => setSelected(r.run_id)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" || e.key === " ") {
                              e.preventDefault();
                              setSelected(r.run_id);
                            }
                          }}
                          tabIndex={0}
                          aria-selected={isActive}
                          className={`row-link ${isActive ? "row-selected" : ""}`}
                        >
                          <td className="font-mono text-xs">#{r.run_id}</td>
                          <td className="text-ink-muted">{r.dataset_size}</td>
                          <td>
                            <StatusBadge status={r.status} />
                          </td>
                          <td className="text-ink-muted whitespace-nowrap">{formatDateTime(r.started_at)}</td>
                          <td className="text-ink-muted text-right">{formatDuration(r.duration_ms)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>

            <section data-reveal className="card p-4 sm:p-5 xl:col-span-2 xl:sticky xl:top-6" aria-live="polite">
              <SectionHeader title={activeRun ? `Run #${activeRun} stages` : "Stages"} description="Bar length is stage duration relative to the slowest stage." />
              {activeRun !== null && <StageTimeline key={activeRun} runId={activeRun} />}
            </section>
          </div>
        )}
      </PageBody>
    </div>
  );
}
