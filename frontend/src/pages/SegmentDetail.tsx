import { useQuery } from "@tanstack/react-query";
import { useParams, Link } from "react-router-dom";
import { api } from "../lib/api";
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
  SkeletonTiles,
  StatTile,
  formatDate,
} from "../components/Common";

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
  const revealRef = useReveal(detail.data?.segment.segment_id);

  if (detail.isLoading)
    return (
      <Loading label="Loading segment">
        <div className="px-4 sm:px-6 lg:px-8 pt-5 pb-5 border-b border-surface-border">
          <Skeleton className="h-3 w-28" />
          <Skeleton className="h-6 w-56 mt-3" />
        </div>
        <PageBody className="space-y-6 max-w-5xl">
          <SkeletonTiles />
          <Skeleton className="h-40 rounded-lg" />
        </PageBody>
      </Loading>
    );
  if (detail.isError || !detail.data)
    return (
      <div>
        <PageHeader title="Segment" crumbs={[{ label: "Segments", to: "/segments" }, { label: id ?? "" }]} />
        <ErrorState message="Could not load this segment." onRetry={() => detail.refetch()} />
      </div>
    );

  const latest = detail.data.history[0];

  return (
    <div>
      <PageHeader
        crumbs={[{ label: "Segments", to: "/segments" }, { label: detail.data.segment.segment_id }]}
        title={detail.data.segment.name}
        subtitle={detail.data.segment.description}
        actions={<span className="badge bg-white/[0.05] text-ink-muted font-mono">v{detail.data.segment.current_version}</span>}
      />
      <PageBody className="max-w-5xl">
        <div ref={revealRef} className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatTile label="Members" count={latest?.member_count ?? null} emphasis />
            <StatTile
              label="Entered (last run)"
              count={latest?.entered_count ?? 0}
              tone={(latest?.entered_count ?? 0) > 0 ? "good" : undefined}
            />
            <StatTile label="Exited (last run)" count={latest?.exited_count ?? 0} tone={(latest?.exited_count ?? 0) > 0 ? "warn" : undefined} />
            <StatTile label="Null handling" value={<span className="text-base font-mono">{detail.data.version?.null_handling ?? "exclude"}</span>} />
          </div>

          <section data-reveal className="card p-4 sm:p-5">
            <SectionHeader title="Rule definition" description="JSON rule AST, compiled to parameterised SQL on every run." />
            <pre className="text-xs leading-relaxed bg-surface-sunken border border-surface-border rounded-md p-4 overflow-x-auto text-ink-muted font-mono">
              {JSON.stringify(detail.data.version?.rule_ast, null, 2)}
            </pre>
          </section>

          <section data-reveal className="card overflow-hidden">
            <div className="px-4 sm:px-5 pt-4 sm:pt-5">
              <SectionHeader title="Sample members" description="First 25 customers currently in this segment." />
            </div>
            {members.isLoading && (
              <Loading label="Loading members">
                <div className="px-4 pb-4">
                  <SkeletonTable rows={5} cols={3} />
                </div>
              </Loading>
            )}
            {members.isError && <ErrorState message="Could not load segment members." onRetry={() => members.refetch()} />}
            {members.data && members.data.length === 0 && <EmptyState message="No customers currently qualify." />}
            {members.data && members.data.length > 0 && (
              <div className="overflow-x-auto border-t border-surface-border">
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
                          <Link to={`/customers/${m.canonical_customer_id}`} className="text-ink hover:text-accent transition-colors">
                            {m.full_name_display || <span className="font-mono text-xs">{m.canonical_customer_id}</span>}
                          </Link>
                        </td>
                        <td className="text-ink-muted">{m.primary_email ?? "—"}</td>
                        <td className="text-ink-muted">{formatDate(m.entered_on)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      </PageBody>
    </div>
  );
}
