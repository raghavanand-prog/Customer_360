import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import type { SegmentSummary } from "../lib/types";
import { EmptyState, ErrorState, LoadingState, PageHeader, formatDateTime } from "../components/Common";

export default function Segments() {
  const navigate = useNavigate();
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["segments"],
    queryFn: async () => (await api.get<{ items: SegmentSummary[] }>("/segments")).data.items,
  });

  return (
    <div>
      <PageHeader title="Segments" subtitle="Rule-defined audiences evaluated against customer_metrics on every pipeline run." />
      <div className="p-6">
        {isLoading && <LoadingState />}
        {isError && <ErrorState message="Could not load segments." onRetry={() => refetch()} />}
        {data && data.length === 0 && <EmptyState message="No segments defined yet." />}
        {data && data.length > 0 && (
          <div className="card overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Segment</th>
                  <th>Description</th>
                  <th>Members</th>
                  <th>Version</th>
                  <th>Last computed</th>
                </tr>
              </thead>
              <tbody>
                {data.map((s) => (
                  <tr key={s.segment_id} onClick={() => navigate(`/segments/${s.segment_id}`)} className="cursor-pointer">
                    <td className="text-ink font-medium">{s.name}</td>
                    <td className="text-ink-muted max-w-md">{s.description}</td>
                    <td>{s.member_count.toLocaleString()}</td>
                    <td>v{s.current_version}</td>
                    <td className="text-ink-muted">{formatDateTime(s.last_computed_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
