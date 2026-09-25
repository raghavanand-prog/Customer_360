import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import type { SegmentSummary } from "../lib/types";
import { useReveal } from "../lib/motion";
import { AnimatedNumber, EmptyState, ErrorState, Loading, PageBody, PageHeader, Skeleton, formatDateTime } from "../components/Common";
import { Icon } from "../components/Icons";

function SegmentCard({ s, maxMembers }: { s: SegmentSummary; maxMembers: number }) {
  const share = maxMembers ? (s.member_count / maxMembers) * 100 : 0;
  return (
    <Link data-reveal to={`/segments/${s.segment_id}`} className="card-interactive group flex flex-col p-4 min-w-0">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <Icon.Segments size={14} className="text-accent/80 shrink-0" />
          <h2 className="relative font-serif text-xl font-normal text-ink truncate group-hover:text-accent transition-colors duration-500">
            {s.name}
            <span className="absolute left-0 -bottom-0.5 h-px w-full bg-accent/70 origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-700 ease-out-quart" aria-hidden="true" />
          </h2>
        </div>
        <span className="badge bg-white/[0.05] text-ink-faint font-mono shrink-0">v{s.current_version}</span>
      </div>
      <p className="text-xs text-ink-muted mt-2 leading-relaxed line-clamp-2 min-h-[2.5rem]">{s.description}</p>
      <div className="mt-4 flex items-end justify-between gap-3">
        <div>
          <div className="stat-label">Members</div>
          <div className="serif-num font-light text-3xl text-ink mt-1">
            <AnimatedNumber value={s.member_count} />
          </div>
        </div>
        <Icon.ChevronRight size={14} className="text-ink-faint group-hover:text-accent group-hover:translate-x-0.5 transition-[color,transform] duration-200" />
      </div>
      {/* Relative size vs the largest segment, for quick comparison only. */}
      <div className="meter mt-3" aria-hidden="true">
        <span className="bg-accent/50" style={{ width: `${share}%` }} />
      </div>
      <div className="text-2xs text-ink-faint mt-2.5">Computed {formatDateTime(s.last_computed_at)}</div>
    </Link>
  );
}

export default function Segments() {
  const { data, isLoading, isError, refetch } = useQuery({
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
        {isError && <ErrorState message="Could not load segments." onRetry={() => refetch()} />}
        {data && data.length === 0 && <EmptyState message="No segments defined yet." />}
        {data && data.length > 0 && (
          <div ref={revealRef} className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
            {data.map((s) => (
              <SegmentCard key={s.segment_id} s={s} maxMembers={maxMembers} />
            ))}
          </div>
        )}
      </PageBody>
    </div>
  );
}
