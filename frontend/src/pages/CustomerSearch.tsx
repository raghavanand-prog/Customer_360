import { useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import type { CustomerListItem } from "../lib/types";
import { useReveal } from "../lib/motion";
import {
  ChurnBadge,
  EmptyState,
  ErrorState,
  Loading,
  PageBody,
  PageHeader,
  SkeletonTable,
  formatCurrency,
} from "../components/Common";
import { Icon } from "../components/Icons";

// Only the first rows get a staggered entrance; the rest appear with them.
// Animating 50 rows individually would be slow to read and costly to run.
const REVEAL_ROWS = 12;

export default function CustomerSearch() {
  const [q, setQ] = useState("");
  const [submitted, setSubmitted] = useState("");
  const navigate = useNavigate();
  const clearSearch = () => {
    setQ("");
    setSubmitted("");
  };

  const { data, error, isLoading, isFetching, isError, isPlaceholderData, dataUpdatedAt, refetch } = useQuery({
    queryKey: ["customers", submitted],
    queryFn: async () =>
      (await api.get<{ items: CustomerListItem[] }>("/customers", { params: { q: submitted || undefined, limit: 50 } })).data
        .items,
    placeholderData: keepPreviousData,
  });
  // Previous results stay on screen (dimmed) while a new search runs; the
  // entrance plays only once the fresh result set has actually arrived.
  const revealRef = useReveal<HTMLTableSectionElement>(data && !isPlaceholderData ? dataUpdatedAt : null, { step: 25 });

  return (
    <div>
      <PageHeader title="Customer Search" subtitle="Search by name, email, phone, or canonical customer ID." />
      <PageBody>
        <form
          role="search"
          onSubmit={(e) => {
            e.preventDefault();
            setSubmitted(q.trim());
          }}
          className="flex flex-col sm:flex-row gap-2 mb-4"
        >
          <div className="relative flex-1 sm:max-w-lg">
            <Icon.Search className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint pointer-events-none" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Name, email, phone, or CX… id"
              aria-label="Search customers"
              className="input pl-9"
            />
          </div>
          <div className="flex gap-2">
            <button type="submit" className="btn-primary px-4">
              Search
            </button>
            {submitted && (
              <button type="button" className="btn-secondary" onClick={clearSearch}>
                Clear
              </button>
            )}
          </div>
        </form>

        <div className="flex items-center justify-between mb-2 min-h-[20px] text-xs text-ink-faint" aria-live="polite">
          {data && (
            <span>
              {data.length === 50 ? "Showing first 50 results" : `${data.length} result${data.length === 1 ? "" : "s"}`}
              {submitted && (
                <>
                  {" "}
                  for <span className="text-ink-muted font-mono">“{submitted}”</span>
                </>
              )}
            </span>
          )}
          {isFetching && data && (
            <span className="flex items-center gap-1.5">
              <span className="h-3 w-3 rounded-full border-2 border-ink-faint/30 border-t-accent motion-safe:animate-spin" aria-hidden="true" />
              Updating
            </span>
          )}
        </div>

        {isLoading && (
          <Loading label="Loading customers">
            <SkeletonTable rows={8} cols={6} />
          </Loading>
        )}
        {isError && <ErrorState message="Could not load customers." error={error} onRetry={() => refetch()} retrying={isFetching} />}
        {data && data.length === 0 && (
          <EmptyState
            message={submitted ? "No customers match this search." : "No customers loaded yet."}
            hint={submitted ? "Try a partial email, a phone number, or a canonical ID." : "Run the pipeline to populate the serving layer."}
            action={
              submitted ? (
                <button type="button" className="btn-secondary text-xs px-3 py-1.5" onClick={clearSearch}>
                  Clear search
                </button>
              ) : undefined
            }
          />
        )}
        {data && data.length > 0 && (
          <div className={`card scroll-x transition-opacity duration-200 ${isFetching ? "opacity-60" : ""}`}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Customer</th>
                  <th className="hidden md:table-cell">Email</th>
                  <th className="hidden xl:table-cell">Country</th>
                  <th className="hidden sm:table-cell text-right">Orders</th>
                  <th className="text-right">Total spend</th>
                  <th>Churn risk</th>
                </tr>
              </thead>
              <tbody ref={revealRef}>
                {data.map((c, i) => (
                  <tr
                    key={c.canonical_customer_id}
                    data-reveal={i < REVEAL_ROWS ? "" : undefined}
                    onClick={() => navigate(`/customers/${c.canonical_customer_id}`)}
                    className="row-link"
                  >
                    <td>
                      <Link
                        to={`/customers/${c.canonical_customer_id}`}
                        onClick={(e) => e.stopPropagation()}
                        className="block group"
                      >
                        <div className="text-ink group-hover:text-accent transition-colors">
                          {c.full_name_display || <span className="text-ink-faint">Unnamed</span>}
                        </div>
                        <div className="text-xs text-ink-faint font-mono">{c.canonical_customer_id}</div>
                      </Link>
                    </td>
                    <td className="hidden md:table-cell text-ink-muted">{c.primary_email ?? "—"}</td>
                    <td className="hidden xl:table-cell text-ink-muted">{c.country_code ?? "—"}</td>
                    <td className="hidden sm:table-cell text-ink-muted text-right">{c.order_count ?? 0}</td>
                    <td className="text-ink text-right">{formatCurrency(c.total_spend)}</td>
                    <td>
                      <ChurnBadge band={c.churn_risk_band} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </PageBody>
    </div>
  );
}
