import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import type { CustomerListItem } from "../lib/types";
import { ChurnBadge, EmptyState, ErrorState, LoadingState, PageHeader, formatCurrency } from "../components/Common";

export default function CustomerSearch() {
  const [q, setQ] = useState("");
  const [submitted, setSubmitted] = useState("");
  const navigate = useNavigate();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["customers", submitted],
    queryFn: async () =>
      (await api.get<{ items: CustomerListItem[] }>("/customers", { params: { q: submitted || undefined, limit: 50 } })).data
        .items,
  });

  return (
    <div>
      <PageHeader title="Customer Search" subtitle="Search by name, email, phone, or canonical customer ID." />
      <div className="p-6">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setSubmitted(q);
          }}
          className="flex gap-2 mb-4"
        >
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search customers…"
            aria-label="Search customers"
            className="flex-1 max-w-md bg-surface-raised border border-surface-border rounded px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-accent"
          />
          <button type="submit" className="px-4 py-2 text-sm rounded bg-accent text-surface font-medium hover:bg-accent-dim">
            Search
          </button>
        </form>

        {isLoading && <LoadingState />}
        {isError && <ErrorState message="Could not load customers." onRetry={() => refetch()} />}
        {data && data.length === 0 && <EmptyState message="No customers match this search." />}
        {data && data.length > 0 && (
          <div className="card overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Customer</th>
                  <th>Email</th>
                  <th>Country</th>
                  <th>Orders</th>
                  <th>Total spend</th>
                  <th>Churn risk</th>
                </tr>
              </thead>
              <tbody>
                {data.map((c) => (
                  <tr
                    key={c.canonical_customer_id}
                    onClick={() => navigate(`/customers/${c.canonical_customer_id}`)}
                    className="cursor-pointer"
                  >
                    <td>
                      <div className="text-ink">{c.full_name_display || <span className="text-ink-faint">Unnamed</span>}</div>
                      <div className="text-xs text-ink-faint font-mono">{c.canonical_customer_id}</div>
                    </td>
                    <td className="text-ink-muted">{c.primary_email ?? "—"}</td>
                    <td className="text-ink-muted">{c.country_code ?? "—"}</td>
                    <td className="text-ink-muted">{c.order_count ?? 0}</td>
                    <td className="text-ink">{formatCurrency(c.total_spend)}</td>
                    <td>
                      <ChurnBadge band={c.churn_risk_band} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
