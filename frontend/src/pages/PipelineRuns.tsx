import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../lib/api";
import type { PipelineRun } from "../lib/types";
import { EmptyState, ErrorState, LoadingState, PageHeader, StatusBadge, formatDateTime } from "../components/Common";

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

export default function PipelineRuns() {
  const [selected, setSelected] = useState<number | null>(null);

  const runs = useQuery({
    queryKey: ["pipeline-runs"],
    queryFn: async () => (await api.get<{ items: PipelineRun[] }>("/pipeline/runs")).data.items,
  });
  const stages = useQuery({
    queryKey: ["pipeline-stages", selected],
    queryFn: async () => (await api.get<{ items: StageRun[] }>(`/pipeline/runs/${selected}/stages`)).data.items,
    enabled: selected !== null,
  });

  return (
    <div>
      <PageHeader title="Pipeline Runs" subtitle="Ingestion through segmentation, one row per stage, with record counts and durations." />
      <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="card overflow-x-auto">
          {runs.isLoading && <LoadingState />}
          {runs.isError && <ErrorState message="Could not load pipeline runs." />}
          {runs.data && runs.data.length === 0 && <EmptyState message="No pipeline runs yet." />}
          {runs.data && runs.data.length > 0 && (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Run</th>
                  <th>Size</th>
                  <th>Status</th>
                  <th>Started</th>
                  <th>Duration</th>
                </tr>
              </thead>
              <tbody>
                {runs.data.map((r) => (
                  <tr key={r.run_id} onClick={() => setSelected(r.run_id)} className="cursor-pointer">
                    <td className="font-mono text-xs">#{r.run_id}</td>
                    <td>{r.dataset_size}</td>
                    <td>
                      <StatusBadge status={r.status} />
                    </td>
                    <td className="text-ink-muted">{formatDateTime(r.started_at)}</td>
                    <td className="text-ink-muted">{r.duration_ms ? `${(r.duration_ms / 1000).toFixed(1)}s` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <section className="card p-4">
          <h2 className="stat-label mb-3">{selected ? `Run #${selected} stages` : "Select a run to inspect its stages"}</h2>
          {selected && stages.isLoading && <LoadingState />}
          {selected && stages.data && (
            <ol className="space-y-2">
              {stages.data.map((s) => (
                <li key={s.stage_run_id} className="flex items-center justify-between text-sm border-b border-surface-border/60 pb-2">
                  <div>
                    <div className="text-ink">{s.stage_name}</div>
                    <div className="text-xs text-ink-faint">
                      {s.rows_in ?? "—"} in → {s.rows_out ?? "—"} out
                      {s.rows_quarantined ? `, ${s.rows_quarantined} quarantined` : ""}
                    </div>
                  </div>
                  <div className="text-right">
                    <StatusBadge status={s.status} />
                    <div className="text-xs text-ink-faint mt-1">{s.duration_ms ? `${s.duration_ms}ms` : "—"}</div>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </section>
      </div>
    </div>
  );
}
