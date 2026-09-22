import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { AnalyticsSummary } from "../lib/types";
import { EmptyState, ErrorState, LoadingState, PageHeader, StatTile, formatCurrency } from "../components/Common";

export default function Overview() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["analytics-summary"],
    queryFn: async () => (await api.get<AnalyticsSummary>("/analytics/summary")).data,
  });

  return (
    <div>
      <PageHeader title="Overview" subtitle="Platform health, customer, commerce, and pipeline signals at a glance." />
      <div className="p-6">
        {isLoading && <LoadingState />}
        {isError && <ErrorState message="Could not load the platform summary." onRetry={() => refetch()} />}
        {data && (
          <div className="space-y-6">
            <section>
              <h2 className="stat-label mb-2">Data health</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <StatTile label="DQ score" value={`${data.dq_score?.toFixed(1) ?? "—"} / 100`} />
                <StatTile label="Last pipeline run" value={data.last_run_id ? `#${data.last_run_id}` : "—"} />
                <StatTile label="Total customers" value={data.total_customers.toLocaleString()} />
                <StatTile label="Active customers" value={data.active_customers.toLocaleString()} />
              </div>
            </section>
            <section>
              <h2 className="stat-label mb-2">Customer</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <StatTile label="At-risk customers" value={data.at_risk_customers.toLocaleString()} />
                <StatTile label="Total customers" value={data.total_customers.toLocaleString()} />
              </div>
            </section>
            <section>
              <h2 className="stat-label mb-2">Commerce</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <StatTile label="Revenue" value={formatCurrency(data.total_revenue)} />
                <StatTile label="Orders" value={data.total_orders.toLocaleString()} />
                <StatTile label="Average order value" value={formatCurrency(data.avg_aov)} />
              </div>
            </section>
          </div>
        )}
        {!isLoading && !isError && !data && <EmptyState message="No data yet. Run the pipeline to populate the platform." />}
      </div>
    </div>
  );
}
