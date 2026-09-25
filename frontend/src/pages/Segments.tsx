import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import type { SegmentSummary } from "../lib/types";
import { useReveal } from "../lib/motion";
import { AnimatedNumber, EmptyState, ErrorState, Loading, PageBody, PageHeader, ShareBar, Skeleton, formatDateTime } from "../components/Common";
import { Icon } from "../components/Icons";

function SegmentCard({ s, maxMembers, index }: { s: SegmentSummary; maxMembers: number; index: number }) {
  const share = maxMembers ? (s.member_count / maxMembers) * 100 : 0;
  return (
    <Link data-reveal to={`/segments/${s.segment_id}`} className="card-interactive group flex flex-col p-4 min-w-0">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <Icon.Segments size={14} className="text-accent/80 shrink-0" />
          <h2 className="text-sm font-semibold text-ink truncate group-hover:text-accent transition-colors">{s.name}</h2>
        </div>
        <span className="badge bg-white/[0.05] text-ink-faint font-mono shrink-0">v{s.current_version}</span>
      </div>
      <p className="text-xs text-ink-muted mt-2 leading-relaxed line-clamp-2 min-h-[2.5rem]">{s.description}</p>
      <div className="mt-4 flex items-end justify-between gap-3">
        <div>
          <div className="stat-label">Members</div>
          <div className="text-xl font-semibold text-ink mt-0.5">
            <AnimatedNumber value={s.member_count} />
          </div>
        </div>
        <Icon.ChevronRight size={14} className="text-ink-faint group-hover:text-accent group-hover:translate-x-0.5 transition-[color,transform] duration-200" />
      </div>
      {/* Relative size vs the largest segment, for quick comparison only. Grows
          just after its card lands (cards stagger 45ms apart). */}
      <div className="mt-3">
        <ShareBar pct={share} delay={220 + index * 45} />
      </div>
      <div className="text-2xs text-ink-faint mt-2.5">Computed {formatDateTime(s.last_computed_at)}</div>
    </Link>
  );
}

export default function Segments() {
  const { data, error, isLoading, isError, isFetching, refetch } = useQuery({
    queryKey: ["segments"],
    queryFn: async () => (await api.get<{ items: SegmentSummary[] }>("/segments")).data.items,
  });
  const revealRef = useReveal(!!data?.length);
  const maxMembers = data?.reduce((m, s) => Math.max(m, s.member_count), 0) ?? 0;

  return (
    <div>
      <PageHeader title="Segments" subtitle="Rule-defined audiences evaluated against customer_metrics on every pipeline run." />
      <PageBody>
        {isLoading && (
          <Loading label="Loading segments">
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
              {Array.from({ length: 6 }, (_, i) => (
                <Skeleton key={i} className="h-44 rounded-lg" />
              ))}
            </div>
          </Loading>
        )}
        {isError && <ErrorState message="Could not load segments." error={error} onRetry={() => refetch()} retrying={isFetching} />}
        {data && data.length === 0 && <EmptyState message="No segments defined yet." hint="Segments are defined in config/segments.yaml and evaluated on every pipeline run." />}
        {data && data.length > 0 && (
          <div ref={revealRef} className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
            {data.map((s, i) => (
              <SegmentCard key={s.segment_id} s={s} maxMembers={maxMembers} index={i} />
            ))}
          </div>
        )}
      </PageBody>
    </div>
  );
}
