import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { ErrorState, LoadingState, PageHeader, StatTile, formatDateTime } from "../components/Common";

interface HealthDetail {
  status: string;
  database: string;
  last_successful_run: { run_id: number; finished_at: string } | null;
  row_counts: Record<string, number>;
}

export default function SystemHealth() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["health-detail"],
    queryFn: async () => (await api.get<HealthDetail>("/health/detail")).data,
    refetchInterval: 30_000,
  });

  return (
    <div>
      <PageHeader title="System Health" subtitle="Live dependency status for the serving layer and the most recent pipeline run." />
      <div className="p-6 space-y-6">
        {isLoading && <LoadingState />}
        {isError && <ErrorState message="Could not reach the health endpoint." onRetry={() => refetch()} />}
        {data && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatTile label="API status" value={data.status} />
            <StatTile label="Database" value={data.database} />
            <StatTile
              label="Last successful run"
              value={data.last_successful_run ? `#${data.last_successful_run.run_id}` : "—"}
              sub={data.last_successful_run ? formatDateTime(data.last_successful_run.finished_at) : undefined}
            />
            <StatTile label="Customers loaded" value={data.row_counts.customers ?? 0} />
          </div>
        )}
      </div>
    </div>
  );
}
