import type { ReactNode } from "react";
import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../lib/api";
import { useReducedMotion, useReveal } from "../lib/motion";
import { EmptyState, ErrorState, Loading, PageBody, PageHeader, SectionHeader, formatCompactCurrency, formatCurrency, formatInt } from "../components/Common";

const C = {
  accent: "#cdb284",
  warn: "#d48354",
  danger: "#cf5959",
  neutral: "#797167",
  grid: "#2a2724",
  axis: "#797167",
  surface: "#1e1c1a",
  border: "#39342d",
};

const BAND_FILL: Record<string, string> = {
  active: "#89b39b",
  at_risk: C.warn,
  churned: C.danger,
  no_purchase_history: C.neutral,
};

const tooltipProps = {
  contentStyle: {
    background: C.surface,
    border: `1px solid ${C.border}`,
    borderRadius: 6,
    fontSize: 12,
    boxShadow: "0 8px 24px -12px rgba(0,0,0,0.6)",
  },
  labelStyle: { color: "#9f958a", marginBottom: 4 },
  itemStyle: { color: "#ede8de" },
  cursor: { fill: "rgba(255,255,255,0.03)", stroke: "rgba(255,255,255,0.08)" },
};

const axisProps = { stroke: C.axis, fontSize: 11, tickLine: false, axisLine: false, tickMargin: 8 } as const;

function ChartCard<T>({
  title,
  description,
  query,
  height,
  emptyMessage,
  className = "",
  children,
}: {
  title: string;
  description: string;
  query: UseQueryResult<T[]>;
  height: number;
  emptyMessage: string;
  className?: string;
  children: (data: T[]) => ReactNode;
}) {
  return (
    <section data-reveal className={`card p-4 sm:p-5 min-w-0 ${className}`}>
      <SectionHeader title={title} description={description} />
      {query.isLoading && (
        <Loading label={`Loading ${title.toLowerCase()}`}>
          <div className="skeleton w-full rounded-md" style={{ height }} aria-hidden="true" />
        </Loading>
      )}
      {query.isError && <ErrorState message={`Could not load ${title.toLowerCase()}.`} onRetry={() => query.refetch()} />}
      {query.data && query.data.length === 0 && <EmptyState message={emptyMessage} />}
      {query.data && query.data.length > 0 && <div style={{ height }}>{children(query.data)}</div>}
    </section>
  );
}

export default function Analytics() {
  const reduced = useReducedMotion();
  const anim = { isAnimationActive: !reduced, animationDuration: 700, animationEasing: "ease-out" as const };

  const revenue = useQuery({
    queryKey: ["revenue"],
    queryFn: async () => (await api.get<{ items: { period: string; revenue: number; orders: number }[] }>("/analytics/revenue")).data.items,
  });
  const topCustomers = useQuery({
    queryKey: ["top-customers"],
    queryFn: async () =>
      (await api.get<{ items: { full_name_display: string | null; total_spend: number }[] }>("/analytics/top-customers", { params: { limit: 8 } }))
        .data.items,
  });
  const churn = useQuery({
    queryKey: ["churn-distribution"],
    queryFn: async () => (await api.get<{ items: { churn_risk_band: string; customers: number }[] }>("/analytics/churn-distribution")).data.items,
  });
  const revealRef = useReveal(true);

  return (
    <div>
      <PageHeader title="Analytics" subtitle="Revenue, customer, and engagement trends over the curated model." />
      <PageBody>
        <div ref={revealRef} className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <ChartCard
            title="Revenue over time"
            description="Recognised revenue per period."
            query={revenue}
            height={280}
            emptyMessage="No revenue data yet."
            className="lg:col-span-2"
          >
            {(rows) => (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="revenueFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={C.accent} stopOpacity={0.22} />
                      <stop offset="100%" stopColor={C.accent} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke={C.grid} vertical={false} />
                  <XAxis dataKey="period" {...axisProps} minTickGap={24} />
                  <YAxis {...axisProps} width={64} tickFormatter={(v: number) => formatCompactCurrency(v)} />
                  <Tooltip {...tooltipProps} formatter={(v) => [formatCurrency(Number(v)), "Revenue"]} />
                  <Area type="monotone" dataKey="revenue" stroke={C.accent} strokeWidth={2} fill="url(#revenueFill)" activeDot={{ r: 4, strokeWidth: 0 }} {...anim} />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </ChartCard>

          <ChartCard title="Top customers by spend" description="Highest lifetime spend, top 8." query={topCustomers} height={280} emptyMessage="No customer spend data yet.">
            {(rows) => (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={rows.map((r) => ({ ...r, label: r.full_name_display || "Unnamed" }))}
                  layout="vertical"
                  margin={{ top: 0, right: 12, left: 0, bottom: 0 }}
                >
                  <CartesianGrid stroke={C.grid} horizontal={false} />
                  <XAxis type="number" {...axisProps} tickFormatter={(v: number) => formatCompactCurrency(v)} />
                  <YAxis type="category" dataKey="label" {...axisProps} width={110} />
                  <Tooltip {...tooltipProps} formatter={(v) => [formatCurrency(Number(v)), "Total spend"]} />
                  <Bar dataKey="total_spend" fill={C.accent} fillOpacity={0.85} radius={[0, 3, 3, 0]} barSize={14} {...anim} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </ChartCard>

          <ChartCard title="Churn risk distribution" description="Customers per churn-risk band." query={churn} height={280} emptyMessage="No churn data yet.">
            {(rows) => (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid stroke={C.grid} vertical={false} />
                  <XAxis dataKey="churn_risk_band" {...axisProps} tickFormatter={(v: string) => v.replace(/_/g, " ")} />
                  <YAxis {...axisProps} width={48} tickFormatter={(v: number) => formatInt(v)} />
                  <Tooltip {...tooltipProps} formatter={(v) => [formatInt(Number(v)), "Customers"]} labelFormatter={(l) => String(l).replace(/_/g, " ")} />
                  <Bar dataKey="customers" radius={[3, 3, 0, 0]} maxBarSize={56} {...anim}>
                    {rows.map((r) => (
                      <Cell key={r.churn_risk_band} fill={BAND_FILL[r.churn_risk_band] ?? C.neutral} fillOpacity={0.85} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </ChartCard>
        </div>
      </PageBody>
    </div>
  );
}
