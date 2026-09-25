import React, { useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams, Link } from "react-router-dom";
import { api } from "../lib/api";
import type { CustomerProfile } from "../lib/types";
import { useStagedReveal } from "../lib/motion";
import {
  ChurnBadge,
  ErrorState,
  Loading,
  PageHeader,
  Skeleton,
  SkeletonTable,
  SkeletonTiles,
  StatTile,
  formatCurrency,
  formatDate,
  formatDateTime,
  formatInt,
} from "../components/Common";
import { AiAssistantPanel, type AssistantHandle } from "../components/AiAssistant";
import { Icon } from "../components/Icons";

function Stage({
  index,
  title,
  description,
  children,
}: {
  index: string;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  const headingId = `stage-${index}`;
  return (
    <section data-stage aria-labelledby={headingId}>
      <div className="flex items-baseline gap-3 mb-3">
        <span className="font-mono text-2xs text-accent/70 tabular-nums w-5 shrink-0">{index}</span>
        <div className="min-w-0 flex-1 flex flex-col sm:flex-row sm:items-baseline sm:gap-3">
          <h2 id={headingId} className="section-title">
            {title}
          </h2>
          <p className="text-xs text-ink-faint">{description}</p>
        </div>
      </div>
      <div className="sm:pl-8">{children}</div>
    </section>
  );
}

function ProfileSkeleton() {
  return (
    <Loading label="Loading customer profile">
      <div className="px-4 sm:px-6 lg:px-8 pt-5 pb-5 border-b border-surface-border">
        <Skeleton className="h-3 w-40" />
        <Skeleton className="h-6 w-64 mt-3" />
        <Skeleton className="h-3 w-44 mt-2" />
      </div>
      <div className="px-4 sm:px-6 lg:px-8 py-6 space-y-8 max-w-6xl">
        <SkeletonTiles />
        <SkeletonTable rows={3} cols={4} />
        <SkeletonTiles />
      </div>
    </Loading>
  );
}

export default function CustomerProfilePage() {
  const { id } = useParams<{ id: string }>();
  const assistantRef = useRef<AssistantHandle>(null);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["customer-profile", id],
    queryFn: async () => (await api.get<CustomerProfile>(`/customers/${id}/profile`)).data,
    enabled: !!id,
  });
  const stagesRef = useStagedReveal(data?.identity.canonical_customer_id);

  if (isLoading) return <ProfileSkeleton />;
  if (isError)
    return (
      <div>
        <PageHeader title="Customer" crumbs={[{ label: "Customers", to: "/customers" }, { label: id ?? "" }]} />
        <ErrorState message="Could not load this customer." onRetry={() => refetch()} />
      </div>
    );
  if (!data) return null;

  const profile = data.profile as Record<string, any>;
  const metrics = data.metrics;
  const canonicalId = data.identity.canonical_customer_id;
  const location = [profile.city, profile.state].filter(Boolean).join(", ");
  const rfmParts = metrics ? [["R", metrics.r_score], ["F", metrics.f_score], ["M", metrics.m_score]].filter(([, v]) => v !== null) : [];

  return (
    <div>
      <PageHeader
        crumbs={[{ label: "Customers", to: "/customers" }, { label: canonicalId }]}
        title={profile.full_name_display || <span className="text-ink-muted">Unnamed customer</span>}
        subtitle={
          <span className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-ink-faint">
            <span className="font-mono">{canonicalId}</span>
            <span aria-hidden="true">·</span>
            <span>
              {data.identity.identities.length} source record{data.identity.identities.length === 1 ? "" : "s"} resolved
            </span>
            {profile.country_code && (
              <>
                <span aria-hidden="true">·</span>
                <span>{profile.country_code}</span>
              </>
            )}
          </span>
        }
        actions={
          <>
            <ChurnBadge band={metrics?.churn_risk_band ?? null} />
            <button onClick={() => assistantRef.current?.focus()} className="btn-accent-soft">
              <Icon.Prompt size={14} />
              Ask about this customer
            </button>
          </>
        }
      />

      <div ref={stagesRef} className="px-4 sm:px-6 lg:px-8 py-6 space-y-10 max-w-6xl">
        <Stage index="01" title="Identity & provenance" description="Every source record resolved into this canonical customer.">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
            <StatTile label="Source records" count={data.identity.identities.length} />
            <StatTile label="Email" value={<span className="text-sm font-medium break-all whitespace-normal">{profile.primary_email ?? "—"}</span>} />
            <StatTile label="Phone" value={<span className="text-sm font-medium">{profile.primary_phone ?? "—"}</span>} />
            <StatTile label="Location" value={<span className="text-sm font-medium">{location || "—"}</span>} />
          </div>
          <div data-reveal-item className="card overflow-x-auto">
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
                    <td className="font-mono text-xs text-ink-muted">{idn.source_record_id}</td>
                    <td className="text-ink-muted">{idn.identity_namespace}</td>
                    <td className="text-ink-muted">{formatDateTime(idn.first_seen_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {data.quality.length > 0 && (
            <div data-reveal-item className="mt-3 flex items-start gap-2.5 rounded-md border border-warn/20 bg-warn/[0.05] px-3 py-2.5 text-sm">
              <Icon.Alert size={14} className="text-warn mt-0.5 shrink-0" />
              <span className="text-ink-muted">
                {data.quality.length} quarantined source record{data.quality.length === 1 ? "" : "s"} associated with this
                customer.{" "}
                <Link to="/quality" className="text-warn hover:underline">
                  Review data quality
                </Link>
              </span>
            </div>
          )}
        </Stage>

        <Stage index="02" title="Behaviour & engagement" description="Recency, frequency, value and engagement signals.">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatTile label="Engagement score" value={metrics?.engagement_score ?? "—"} />
            <StatTile
              label="RFM segment"
              value={<span className="text-base">{metrics?.rfm_segment ?? "—"}</span>}
              sub={rfmParts.length ? rfmParts.map(([k, v]) => `${k}${v}`).join(" · ") : undefined}
            />
            <StatTile label="Days since last order" value={metrics?.days_since_last_order ?? "—"} />
            <StatTile label="Refunded amount" value={formatCurrency(metrics?.refunded_amount ?? null)} />
          </div>
        </Stage>

        <Stage index="03" title="Transactions" description="Order history and lifetime commerce totals.">
          <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-5 gap-3 mb-3">
            <StatTile label="Total spend" count={metrics?.total_spend ?? null} format={formatCurrency} emphasis />
            <StatTile label="Orders" count={metrics?.order_count ?? 0} format={formatInt} emphasis />
            <StatTile label="AOV" value={formatCurrency(metrics?.aov ?? null)} />
            <StatTile label="First order" value={<span className="text-base">{formatDate(metrics?.first_order_at)}</span>} />
            <StatTile label="Last order" value={<span className="text-base">{formatDate(metrics?.last_order_at)}</span>} />
          </div>
          <div data-reveal-item className="card overflow-x-auto">
            {data.orders.length === 0 ? (
              <div className="px-4 py-8 text-center text-sm text-ink-faint">No orders on record.</div>
            ) : (
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
                      <td className="font-mono text-xs text-ink-muted">{o.order_id}</td>
                      <td className="text-ink-muted">{formatDate(o.order_ts)}</td>
                      <td className="capitalize">{o.order_status}</td>
                      <td className="capitalize text-ink-muted">{o.channel ?? "—"}</td>
                      <td className="text-right">{formatCurrency(o.revenue_amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </Stage>

        <Stage index="04" title="Segments" description="Rule-defined audiences this customer currently qualifies for.">
          {data.segments.length === 0 ? (
            <div data-reveal-item className="text-sm text-ink-faint">
              Not currently a member of any segment.
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              {data.segments.map((s) => (
                <Link
                  key={s.segment_id}
                  data-reveal-item
                  to={`/segments/${s.segment_id}`}
                  className="group inline-flex items-center gap-2 rounded-md border border-accent/20 bg-accent/[0.06] px-3 py-1.5 text-sm text-accent hover:bg-accent/[0.12] hover:border-accent/40 transition-colors"
                >
                  <Icon.Segments size={13} />
                  {s.name}
                  <span className="text-2xs text-ink-faint group-hover:text-ink-muted transition-colors">since {formatDate(s.entered_on)}</span>
                </Link>
              ))}
            </div>
          )}
        </Stage>

        <Stage index="05" title="Intelligence" description="Ask questions grounded in this customer's data and the platform documentation.">
          <div data-reveal-item>
            <AiAssistantPanel ref={assistantRef} customerId={canonicalId} />
          </div>
        </Stage>
      </div>
    </div>
  );
}
