import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../lib/api";
import { EmptyState, ErrorState, LoadingState, PageHeader } from "../components/Common";

const CHART_COLOR = "#2dd4a7";

export default function Analytics() {
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

  return (
    <div>
      <PageHeader title="Analytics" subtitle="Revenue, customer, and engagement trends over the curated model." />
      <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="card p-4">
          <h2 className="stat-label mb-3">Revenue over time</h2>
          {revenue.isLoading && <LoadingState />}
          {revenue.isError && <ErrorState message="Could not load revenue trend." />}
          {revenue.data && revenue.data.length === 0 && <EmptyState message="No revenue data yet." />}
          {revenue.data && revenue.data.length > 0 && (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={revenue.data}>
                <CartesianGrid stroke="#262b31" strokeDasharray="3 3" />
                <XAxis dataKey="period" stroke="#6b747c" fontSize={11} />
                <YAxis stroke="#6b747c" fontSize={11} />
                <Tooltip contentStyle={{ background: "#15181c", border: "1px solid #262b31", fontSize: 12 }} />
                <Line type="monotone" dataKey="revenue" stroke={CHART_COLOR} strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </section>

        <section className="card p-4">
          <h2 className="stat-label mb-3">Top customers by spend</h2>
          {topCustomers.data && topCustomers.data.length > 0 && (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={topCustomers.data} layout="vertical" margin={{ left: 40 }}>
                <CartesianGrid stroke="#262b31" strokeDasharray="3 3" />
                <XAxis type="number" stroke="#6b747c" fontSize={11} />
                <YAxis type="category" dataKey="full_name_display" stroke="#6b747c" fontSize={11} width={100} />
                <Tooltip contentStyle={{ background: "#15181c", border: "1px solid #262b31", fontSize: 12 }} />
                <Bar dataKey="total_spend" fill={CHART_COLOR} radius={[0, 3, 3, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </section>

        <section className="card p-4">
          <h2 className="stat-label mb-3">Churn risk distribution</h2>
          {churn.data && churn.data.length > 0 && (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={churn.data}>
                <CartesianGrid stroke="#262b31" strokeDasharray="3 3" />
                <XAxis dataKey="churn_risk_band" stroke="#6b747c" fontSize={11} />
                <YAxis stroke="#6b747c" fontSize={11} />
                <Tooltip contentStyle={{ background: "#15181c", border: "1px solid #262b31", fontSize: 12 }} />
                <Bar dataKey="customers" fill={CHART_COLOR} radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </section>
      </div>
    </div>
  );
}
