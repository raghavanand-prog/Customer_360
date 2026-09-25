import { useId, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { animate } from "animejs/animation";
import { createDrawable } from "animejs/svg";
import { stagger } from "animejs/utils";
import { api } from "../lib/api";
import type { PipelineRun, SegmentSummary } from "../lib/types";
import { EASE_OUT, prefersReducedMotion } from "../lib/motion";
import { AnimatedNumber, Meter, Skeleton, StatusBadge, formatCompactCurrency, formatCurrency, formatDateTime, formatDuration } from "./Common";
import { Icon } from "./Icons";

function PanelHeader({ title, description, to, linkLabel }: { title: string; description: string; to?: string; linkLabel?: string }) {
  return (
    <div className="flex items-start justify-between gap-3 mb-4">
      <div className="min-w-0">
        <h2 className="section-title">{title}</h2>
        <p className="text-xs text-ink-faint mt-0.5">{description}</p>
      </div>
      {to && (
        <Link to={to} className="btn-ghost shrink-0">
          {linkLabel ?? "View"}
          <Icon.ChevronRight size={12} />
        </Link>
      )}
    </div>
  );
}

function PanelState({ loading, error, empty, height = 160 }: { loading: boolean; error: boolean; empty: boolean; height?: number }) {
  if (loading) return <Skeleton className="w-full h-40 rounded-md" />;
  if (error) return <p className="text-xs text-ink-faint py-6 text-center">Could not load this panel.</p>;
  if (empty) return <p className="text-xs text-ink-faint py-6 text-center" style={{ minHeight: height / 2 }}>No data yet.</p>;
  return null;
}

// ------------------------------------------------------------ revenue trend

const W = 640;
const H = 180;
const PAD_Y = 14;

/** Lightweight SVG trend (no chart library on this page): the line draws itself in with Anime.js createDrawable. */
export function RevenueTrendPanel() {
  const q = useQuery({
    queryKey: ["revenue"],
    queryFn: async () => (await api.get<{ items: { period: string; revenue: number; orders: number }[] }>("/analytics/revenue")).data.items,
  });
  const rows = useMemo(() => q.data ?? [], [q.data]);
  const gradId = useId().replace(/:/g, "");
  const lineRef = useRef<SVGPathElement>(null);
  const areaRef = useRef<SVGPathElement>(null);
  const dotsRef = useRef<SVGGElement>(null);
  const [hover, setHover] = useState<number | null>(null);

  const geo = useMemo(() => {
    if (rows.length < 2) return null;
    const vals = rows.map((r) => r.revenue);
    const max = Math.max(...vals);
    const min = Math.min(...vals, 0);
    const x = (i: number) => (i / (rows.length - 1)) * W;
    const y = (v: number) => H - PAD_Y - ((v - min) / (max - min || 1)) * (H - PAD_Y * 2);
    const pts = rows.map((r, i) => [x(i), y(r.revenue)] as const);
    // smooth path via midpoint quadratic curves
    let d = `M ${pts[0][0]} ${pts[0][1]}`;
    for (let i = 1; i < pts.length; i++) {
      const [px, py] = pts[i - 1];
      const [cx, cy] = pts[i];
      const mx = (px + cx) / 2;
      d += ` C ${mx} ${py}, ${mx} ${cy}, ${cx} ${cy}`;
    }
    const area = `${d} L ${W} ${H} L 0 ${H} Z`;
    return { d, area, pts };
  }, [rows]);

  useLayoutEffect(() => {
    if (!geo || prefersReducedMotion()) return;
    const line = lineRef.current!;
    const area = areaRef.current!;
    const dots = Array.from(dotsRef.current?.querySelectorAll<SVGCircleElement>("circle") ?? []);
    const drawable = createDrawable(line);
    area.style.opacity = "0";
    for (const el of dots) el.style.opacity = "0";
    const a = animate(drawable, { draw: ["0 0", "0 1"], duration: 1800, ease: "inOutQuart", delay: 200 });
    const b = animate(area, {
      opacity: [0, 1],
      duration: 1200,
      delay: 900,
      ease: EASE_OUT,
      onComplete: () => {
        area.style.opacity = "";
      },
    });
    const c = animate(dots, {
      opacity: [0, 1],
      scale: [0, 1],
      duration: 500,
      delay: stagger(90, { start: 400 }),
      ease: "outBack(2)",
      onComplete: () => {
        for (const el of dots) {
          el.style.opacity = "";
          el.style.transform = "";
        }
      },
    });
    return () => {
      a.cancel();
      b.cancel();
      c.cancel();
      line.removeAttribute("pathLength");
      line.style.strokeDasharray = "";
      line.style.strokeDashoffset = "";
      area.style.opacity = "";
    };
  }, [geo]);

  const first = rows[0]?.revenue ?? 0;
  const last = rows[rows.length - 1]?.revenue ?? 0;
  const change = first ? ((last - first) / first) * 100 : 0;
  const active = hover !== null ? rows[hover] : rows[rows.length - 1];

  return (
    <section data-reveal className="card p-5 lg:col-span-2 min-w-0">
      <PanelHeader title="Revenue trend" description="Recognised revenue per period." to="/analytics" linkLabel="Analytics" />
      <PanelState loading={q.isLoading} error={q.isError} empty={!q.isLoading && !q.isError && rows.length < 2} />
      {geo && active && (
        <>
          <div className="flex flex-wrap items-end justify-between gap-3 mb-3">
            <div>
              <div className="text-xs text-ink-faint">{active.period}</div>
              <div className="text-2xl font-semibold tracking-tight text-ink tabular-nums">{formatCurrency(active.revenue)}</div>
            </div>
            <div className={`text-xs tabular-nums ${change >= 0 ? "text-accent" : "text-warn"}`}>
              {change >= 0 ? "▲" : "▼"} {Math.abs(change).toFixed(1)}% since {rows[0].period}
            </div>
          </div>
          <svg
            viewBox={`0 0 ${W} ${H}`}
            preserveAspectRatio="none"
            className="w-full h-44 overflow-visible"
            role="img"
            aria-label={`Revenue from ${rows[0].period} to ${rows[rows.length - 1].period}, ${change >= 0 ? "up" : "down"} ${Math.abs(change).toFixed(1)}%`}
            onMouseLeave={() => setHover(null)}
            onMouseMove={(e) => {
              const r = e.currentTarget.getBoundingClientRect();
              const i = Math.round(((e.clientX - r.left) / r.width) * (rows.length - 1));
              setHover(Math.max(0, Math.min(rows.length - 1, i)));
            }}
          >
            <defs>
              <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#2dd4a7" stopOpacity="0.25" />
                <stop offset="100%" stopColor="#2dd4a7" stopOpacity="0" />
              </linearGradient>
            </defs>
            {[0.25, 0.5, 0.75].map((f) => (
              <line key={f} x1="0" x2={W} y1={H * f} y2={H * f} stroke="#20252b" strokeWidth="1" vectorEffect="non-scaling-stroke" />
            ))}
            <path ref={areaRef} d={geo.area} fill={`url(#${gradId})`} />
            <path ref={lineRef} d={geo.d} fill="none" stroke="#2dd4a7" strokeWidth="2" vectorEffect="non-scaling-stroke" strokeLinecap="round" />
            {hover !== null && (
              <line x1={geo.pts[hover][0]} x2={geo.pts[hover][0]} y1="0" y2={H} stroke="rgba(255,255,255,0.12)" strokeWidth="1" vectorEffect="non-scaling-stroke" />
            )}
            <g ref={dotsRef}>
              {geo.pts.map(([x, y], i) => (
                <circle
                  key={i}
                  cx={x}
                  cy={y}
                  r={hover === i ? 5 : 3}
                  fill={hover === i ? "#2dd4a7" : "#15181c"}
                  stroke="#2dd4a7"
                  strokeWidth="1.5"
                  vectorEffect="non-scaling-stroke"
                  style={{ transformOrigin: `${x}px ${y}px`, transformBox: "view-box" }}
                />
              ))}
            </g>
          </svg>
          <div className="flex justify-between text-2xs text-ink-faint mt-2 tabular-nums">
            <span>{rows[0].period}</span>
            <span>{formatCompactCurrency(Math.max(...rows.map((r) => r.revenue)))} peak</span>
            <span>{rows[rows.length - 1].period}</span>
          </div>
        </>
      )}
    </section>
  );
}

// ------------------------------------------------------------ segments

export function SegmentsPanel() {
  const q = useQuery({
    queryKey: ["segments"],
    queryFn: async () => (await api.get<{ items: SegmentSummary[] }>("/segments")).data.items,
  });
  const top = [...(q.data ?? [])].sort((a, b) => b.member_count - a.member_count).slice(0, 6);
  const max = top[0]?.member_count ?? 0;
  return (
    <section data-reveal className="card p-5 min-w-0">
      <PanelHeader title="Largest segments" description="Members per rule-defined audience." to="/segments" linkLabel="All" />
      <PanelState loading={q.isLoading} error={q.isError} empty={!q.isLoading && !q.isError && top.length === 0} />
      <ul className="space-y-3">
        {top.map((s) => (
          <li key={s.segment_id}>
            <Link to={`/segments/${s.segment_id}`} className="group block">
              <div className="flex items-baseline justify-between gap-2 text-sm">
                <span className="text-ink-muted group-hover:text-accent transition-colors truncate">{s.name}</span>
                <span className="text-ink font-medium">
                  <AnimatedNumber value={s.member_count} />
                </span>
              </div>
              <div className="mt-1.5">
                <Meter value={s.member_count} max={max} tone="good" label={`${s.name} members`} />
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

// ------------------------------------------------------------ top customers

export function TopCustomersPanel() {
  const q = useQuery({
    queryKey: ["top-customers", 5],
    queryFn: async () =>
      (await api.get<{ items: { full_name_display: string | null; total_spend: number }[] }>("/analytics/top-customers", { params: { limit: 5 } })).data.items,
  });
  const rows = q.data ?? [];
  const max = rows[0]?.total_spend ?? 0;
  return (
    <section data-reveal className="card p-5 min-w-0">
      <PanelHeader title="Top customers" description="Highest lifetime spend." to="/customers" linkLabel="Customers" />
      <PanelState loading={q.isLoading} error={q.isError} empty={!q.isLoading && !q.isError && rows.length === 0} />
      <ol className="space-y-3">
        {rows.map((r, i) => (
          <li key={i} className="flex items-center gap-3">
            <span className="font-mono text-2xs text-ink-faint w-4 tabular-nums">{String(i + 1).padStart(2, "0")}</span>
            <div className="flex-1 min-w-0">
              <div className="flex items-baseline justify-between gap-2 text-sm">
                <span className={`truncate ${r.full_name_display ? "text-ink-muted" : "text-ink-faint"}`}>{r.full_name_display || "Unnamed customer"}</span>
                <span className="text-ink font-medium">
                  <AnimatedNumber value={r.total_spend} format={formatCurrency} />
                </span>
              </div>
              <div className="mt-1.5">
                <Meter value={r.total_spend} max={max} tone="info" label="Share of top spend" />
              </div>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

// ------------------------------------------------------------ pipeline

export function RecentRunsPanel() {
  const q = useQuery({
    queryKey: ["pipeline-runs"],
    queryFn: async () => (await api.get<{ items: PipelineRun[] }>("/pipeline/runs")).data.items,
  });
  const runs = (q.data ?? []).slice(0, 5);
  return (
    <section data-reveal className="card p-5 lg:col-span-2 min-w-0">
      <PanelHeader title="Recent pipeline runs" description="Ingestion through segmentation, newest first." to="/pipeline" linkLabel="Pipeline" />
      <PanelState loading={q.isLoading} error={q.isError} empty={!q.isLoading && !q.isError && runs.length === 0} />
      <ol className="relative">
        {runs.map((r, i) => (
          <li key={r.run_id} className="relative flex items-center gap-4 py-2.5">
            {i < runs.length - 1 && <span className="absolute left-[5px] top-7 -bottom-2.5 w-px bg-surface-border" aria-hidden="true" />}
            <span
              className={`relative h-[11px] w-[11px] rounded-full border-2 shrink-0 ${
                r.status === "succeeded" ? "border-accent bg-accent/30" : r.status === "failed" ? "border-danger bg-danger/30" : "border-info bg-info/30"
              }`}
              aria-hidden="true"
            />
            <span className="font-mono text-xs text-ink w-10">#{r.run_id}</span>
            <StatusBadge status={r.status} />
            <span className="text-xs text-ink-muted hidden sm:inline">{r.dataset_size}</span>
            <span className="text-xs text-ink-faint ml-auto whitespace-nowrap">{formatDateTime(r.started_at)}</span>
            <span className="text-xs text-ink-muted w-14 text-right tabular-nums">{formatDuration(r.duration_ms)}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}

// ------------------------------------------------------------ sidebar status

interface HealthDetail {
  status: string;
  database: string;
  last_successful_run: { run_id: number; finished_at: string } | null;
}

/** Live status widget for the sidebar: real /health/detail, refreshed every 60s. */
export function SidebarStatus() {
  const q = useQuery({
    queryKey: ["health-detail"],
    queryFn: async () => (await api.get<HealthDetail>("/health/detail")).data,
    refetchInterval: 60_000,
  });
  const ok = q.data?.status === "ok" && q.data?.database === "up";
  const tone = q.isError ? "bg-danger" : !q.data ? "bg-ink-faint" : ok ? "bg-accent" : "bg-warn";
  return (
    <Link to="/system" className="mx-3 mb-3 block rounded-lg border border-surface-border bg-surface/60 p-3 hover:border-surface-strong transition-colors">
      <div className="flex items-center gap-2">
        <span className="relative inline-flex h-2 w-2">
          {ok && <span className={`absolute inset-0 rounded-full ${tone} motion-safe:animate-ping opacity-50`} />}
          <span className={`relative inline-flex h-2 w-2 rounded-full ${tone}`} />
        </span>
        <span className="text-xs text-ink">{q.isError ? "API unreachable" : !q.data ? "Checking…" : ok ? "All systems live" : "Degraded"}</span>
      </div>
      {q.data && (
        <div className="mt-2 grid grid-cols-2 gap-2 text-2xs text-ink-faint">
          <div>
            API <span className="text-ink-muted uppercase">{q.data.status}</span>
          </div>
          <div>
            DB <span className="text-ink-muted uppercase">{q.data.database}</span>
          </div>
          {q.data.last_successful_run && (
            <div className="col-span-2">
              Last run <span className="text-ink-muted font-mono">#{q.data.last_successful_run.run_id}</span> ·{" "}
              {formatDateTime(q.data.last_successful_run.finished_at)}
            </div>
          )}
        </div>
      )}
    </Link>
  );
}
