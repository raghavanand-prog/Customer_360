import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../lib/api";
import type { DatasetQualityScore } from "../lib/types";
import { EmptyState, ErrorState, LoadingState, PageHeader, StatTile } from "../components/Common";

interface RuleResult {
  rule_id: string;
  rule_name: string;
  dimension: string;
  severity: string;
  records_applicable: number;
  records_failed: number;
  failure_rate: number;
}

function scoreColor(score: number | null): string {
  if (score === null) return "text-ink-faint";
  if (score >= 98) return "text-accent";
  if (score >= 90) return "text-warn";
  return "text-danger";
}

export default function DataQuality() {
  const [expanded, setExpanded] = useState<string | null>(null);

  const summary = useQuery({
    queryKey: ["quality-summary"],
    queryFn: async () => (await api.get<{ run_id: number | null; datasets: DatasetQualityScore[] }>("/quality/summary")).data,
  });

  const detail = useQuery({
    queryKey: ["quality-detail", expanded],
    queryFn: async () => (await api.get<{ rules: RuleResult[] }>(`/quality/datasets/${expanded}`)).data,
    enabled: !!expanded,
  });

  const overall = summary.data?.datasets.length
    ? summary.data.datasets.reduce((acc, d) => acc + d.score_overall, 0) / summary.data.datasets.length
    : null;

  return (
    <div>
      <PageHeader title="Data Quality" subtitle="Six-dimension quality scoring per dataset, drill down to the exact rule that failed." />
      <div className="p-6 space-y-6">
        {summary.isLoading && <LoadingState />}
        {summary.isError && <ErrorState message="Could not load data quality summary." />}
        {summary.data && summary.data.datasets.length === 0 && <EmptyState message="No pipeline run has completed yet." />}

        {summary.data && summary.data.datasets.length > 0 && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <StatTile label="Platform score" value={<span className={scoreColor(overall)}>{overall?.toFixed(1)}</span>} />
              <StatTile label="Datasets scored" value={summary.data.datasets.length} />
              <StatTile
                label="Total quarantined"
                value={summary.data.datasets.reduce((a, d) => a + d.records_quarantined, 0)}
              />
              <StatTile label="Latest run" value={`#${summary.data.run_id}`} />
            </div>

            <div className="card overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Dataset</th>
                    <th>Ingested</th>
                    <th>Accepted</th>
                    <th>Warned</th>
                    <th>Quarantined</th>
                    <th>Rejected</th>
                    <th>Score</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.data.datasets.map((d) => (
                    <>
                      <tr key={d.dataset} onClick={() => setExpanded(expanded === d.dataset ? null : d.dataset)} className="cursor-pointer">
                        <td className="text-ink font-medium">{d.dataset}</td>
                        <td>{d.records_ingested}</td>
                        <td>{d.records_accepted}</td>
                        <td>{d.records_warned}</td>
                        <td className={d.records_quarantined > 0 ? "text-warn" : ""}>{d.records_quarantined}</td>
                        <td className={d.records_rejected > 0 ? "text-danger" : ""}>{d.records_rejected}</td>
                        <td className={scoreColor(d.score_overall)}>{d.score_overall?.toFixed(1)}</td>
                      </tr>
                      {expanded === d.dataset && (
                        <tr key={`${d.dataset}-detail`}>
                          <td colSpan={7} className="bg-black/20 p-0">
                            <div className="p-4">
                              {detail.isLoading && <LoadingState label="Loading rule results…" />}
                              {detail.data && (
                                <table className="data-table">
                                  <thead>
                                    <tr>
                                      <th>Rule</th>
                                      <th>Dimension</th>
                                      <th>Severity</th>
                                      <th>Applicable</th>
                                      <th>Failed</th>
                                      <th>Failure rate</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {detail.data.rules.map((r) => (
                                      <tr key={r.rule_id}>
                                        <td className="font-mono text-xs">
                                          {r.rule_id} — {r.rule_name}
                                        </td>
                                        <td className="capitalize">{r.dimension}</td>
                                        <td className="capitalize">{r.severity}</td>
                                        <td>{r.records_applicable}</td>
                                        <td className={r.records_failed > 0 ? "text-warn" : ""}>{r.records_failed}</td>
                                        <td>{(r.failure_rate * 100).toFixed(1)}%</td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
