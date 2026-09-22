import { useQuery } from "@tanstack/react-query";
import { useParams, Link } from "react-router-dom";
import { api } from "../lib/api";
import type { CustomerProfile } from "../lib/types";
import { ChurnBadge, ErrorState, LoadingState, StatTile, formatCurrency, formatDate, formatDateTime } from "../components/Common";

export default function CustomerProfilePage() {
  const { id } = useParams<{ id: string }>();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["customer-profile", id],
    queryFn: async () => (await api.get<CustomerProfile>(`/customers/${id}/profile`)).data,
    enabled: !!id,
  });

  if (isLoading) return <LoadingState label="Loading customer profile…" />;
  if (isError) return <ErrorState message="Could not load this customer." onRetry={() => refetch()} />;
  if (!data) return null;

  const profile = data.profile as Record<string, any>;
  const metrics = data.metrics;

  return (
    <div className="p-6 space-y-6 max-w-6xl">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-ink">
            {profile.full_name_display || <span className="text-ink-faint">Unnamed customer</span>}
          </h1>
          <div className="text-xs text-ink-faint font-mono mt-1">{data.identity.canonical_customer_id}</div>
        </div>
        <ChurnBadge band={metrics?.churn_risk_band ?? null} />
      </div>

      {/* IDENTITY */}
      <section className="card p-4">
        <h2 className="stat-label mb-3">Identity &amp; provenance</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <StatTile label="Source systems" value={data.identity.identities.length} />
          <StatTile label="Email" value={<span className="text-sm break-all">{profile.primary_email ?? "—"}</span>} />
          <StatTile label="Phone" value={profile.primary_phone ?? "—"} />
          <StatTile label="Location" value={[profile.city, profile.state].filter(Boolean).join(", ") || "—"} />
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Source system</th>
              <th>Source record ID</th>
              <th>Namespace</th>
              <th>First seen</th>
            </tr>
          </thead>
          <tbody>
            {data.identity.identities.map((idn) => (
              <tr key={idn.identity_id}>
                <td className="capitalize">{idn.source_system}</td>
                <td className="font-mono text-xs">{idn.source_record_id}</td>
                <td>{idn.identity_namespace}</td>
                <td>{formatDateTime(idn.first_seen_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* TRANSACTIONS */}
      <section className="card p-4">
        <h2 className="stat-label mb-3">Transactions</h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
          <StatTile label="Total spend" value={formatCurrency(metrics?.total_spend)} />
          <StatTile label="Orders" value={metrics?.order_count ?? 0} />
          <StatTile label="AOV" value={formatCurrency(metrics?.aov ?? null)} />
          <StatTile label="First order" value={formatDate(metrics?.first_order_at)} />
          <StatTile label="Last order" value={formatDate(metrics?.last_order_at)} />
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Order</th>
              <th>Date</th>
              <th>Status</th>
              <th>Channel</th>
              <th className="text-right">Amount</th>
            </tr>
          </thead>
          <tbody>
            {data.orders.map((o) => (
              <tr key={o.order_id}>
                <td className="font-mono text-xs">{o.order_id}</td>
                <td>{formatDate(o.order_ts)}</td>
                <td className="capitalize">{o.order_status}</td>
                <td className="capitalize">{o.channel ?? "—"}</td>
                <td className="text-right">{formatCurrency(o.revenue_amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* BEHAVIOUR */}
      <section className="card p-4">
        <h2 className="stat-label mb-3">Behaviour &amp; engagement</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatTile label="Engagement score" value={metrics?.engagement_score ?? "—"} />
          <StatTile label="RFM segment" value={metrics?.rfm_segment ?? "—"} />
          <StatTile label="Days since last order" value={metrics?.days_since_last_order ?? "—"} />
          <StatTile label="Refunded amount" value={formatCurrency(metrics?.refunded_amount ?? null)} />
        </div>
      </section>

      {/* SEGMENTS */}
      <section className="card p-4">
        <h2 className="stat-label mb-3">Segments</h2>
        {data.segments.length === 0 && <div className="text-sm text-ink-faint">Not currently a member of any segment.</div>}
        <div className="flex flex-wrap gap-2">
          {data.segments.map((s) => (
            <Link
              key={s.segment_id}
              to={`/segments/${s.segment_id}`}
              className="badge bg-accent/10 text-accent hover:bg-accent/20 transition-colors"
            >
              {s.name}
            </Link>
          ))}
        </div>
      </section>

      {/* DATA QUALITY */}
      {data.quality.length > 0 && (
        <section className="card p-4">
          <h2 className="stat-label mb-3">Data quality flags for this customer</h2>
          <div className="text-sm text-ink-muted">
            {data.quality.length} quarantined source record{data.quality.length === 1 ? "" : "s"} associated with this customer.
          </div>
        </section>
      )}
    </div>
  );
}
