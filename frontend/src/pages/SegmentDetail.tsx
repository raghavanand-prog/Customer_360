import { useQuery } from "@tanstack/react-query";
import { useParams, Link } from "react-router-dom";
import { api } from "../lib/api";
import { EmptyState, ErrorState, LoadingState, PageHeader, StatTile, formatDate } from "../components/Common";

interface SegmentDetailResponse {
  segment: { segment_id: string; name: string; description: string; current_version: number };
  version: { rule_ast: Record<string, unknown>; thresholds: Record<string, unknown>; null_handling: string } | null;
  history: { member_count: number; entered_count: number; exited_count: number; computed_at: string }[];
}

interface Member {
  canonical_customer_id: string;
  full_name_display: string | null;
  primary_email: string | null;
  entered_on: string;
}

export default function SegmentDetail() {
  const { id } = useParams<{ id: string }>();

  const detail = useQuery({
    queryKey: ["segment", id],
    queryFn: async () => (await api.get<SegmentDetailResponse>(`/segments/${id}`)).data,
    enabled: !!id,
  });
  const members = useQuery({
    queryKey: ["segment-members", id],
    queryFn: async () => (await api.get<{ items: Member[] }>(`/segments/${id}/members`, { params: { limit: 25 } })).data.items,
    enabled: !!id,
  });

  if (detail.isLoading) return <LoadingState label="Loading segment…" />;
  if (detail.isError || !detail.data) return <ErrorState message="Could not load this segment." onRetry={() => detail.refetch()} />;

  const latest = detail.data.history[0];

  return (
    <div>
      <PageHeader title={detail.data.segment.name} subtitle={detail.data.segment.description} />
      <div className="p-6 space-y-6 max-w-5xl">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatTile label="Members" value={latest?.member_count ?? "—"} />
          <StatTile label="Entered (last run)" value={latest?.entered_count ?? 0} />
          <StatTile label="Exited (last run)" value={latest?.exited_count ?? 0} />
          <StatTile label="Null handling" value={detail.data.version?.null_handling ?? "exclude"} />
        </div>

        <section className="card p-4">
          <h2 className="stat-label mb-2">Rule definition</h2>
          <pre className="text-xs bg-surface rounded p-3 overflow-x-auto text-ink-muted font-mono">
            {JSON.stringify(detail.data.version?.rule_ast, null, 2)}
          </pre>
        </section>

        <section className="card p-4">
          <h2 className="stat-label mb-3">Sample members</h2>
          {members.isLoading && <LoadingState />}
          {members.data && members.data.length === 0 && <EmptyState message="No customers currently qualify." />}
          {members.data && members.data.length > 0 && (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Customer</th>
                  <th>Email</th>
                  <th>Entered on</th>
                </tr>
              </thead>
              <tbody>
                {members.data.map((m) => (
                  <tr key={m.canonical_customer_id}>
                    <td>
                      <Link to={`/customers/${m.canonical_customer_id}`} className="text-accent hover:underline">
                        {m.full_name_display || m.canonical_customer_id}
                      </Link>
                    </td>
                    <td className="text-ink-muted">{m.primary_email ?? "—"}</td>
                    <td className="text-ink-muted">{formatDate(m.entered_on)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </div>
    </div>
  );
}
