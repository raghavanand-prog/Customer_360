import { Fragment, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { DatasetQualityScore } from "../lib/types";
import { useReveal } from "../lib/motion";
import {
  EmptyState,
  ErrorState,
  Loading,
  Meter,
  PageBody,
  PageHeader,
  SkeletonTable,
  SkeletonTiles,
  StatTile,
  TONE_TEXT,
  ToneBadge,
  formatInt,
  formatScore,
  scoreLabel,
  scoreTone,
  type Tone,
} from "../components/Common";
import { Icon } from "../components/Icons";

interface RuleResult {
  rule_id: string;
  rule_name: string;
  dimension: string;
  severity: string;
  records_applicable: number;
  records_failed: number;
  failure_rate: number;
}

const DIMENSIONS: { key: keyof DatasetQualityScore; label: string }[] = [
  { key: "score_completeness", label: "Completeness" },
  { key: "score_validity", label: "Validity" },
  { key: "score_uniqueness", label: "Uniqueness" },
  { key: "score_consistency", label: "Consistency" },
  { key: "score_integrity", label: "Integrity" },
  { key: "score_timeliness", label: "Timeliness" },
];

function severityTone(severity: string): Tone {
  const s = severity.toLowerCase();
  if (s === "critical" || s === "error" || s === "reject") return "bad";
  if (s === "warning" || s === "warn" || s === "quarantine") return "warn";
  return "neutral";
}

function DatasetDetail({ dataset }: { dataset: DatasetQualityScore }) {
  const detail = useQuery({
    queryKey: ["quality-detail", dataset.dataset],
    queryFn: async () => (await api.get<{ rules: RuleResult[] }>(`/quality/datasets/${dataset.dataset}`)).data,
  });
  const revealRef = useReveal(detail.data ? dataset.dataset : null, { step: 30, distance: 6 });

  return (
    <div ref={revealRef} className="p-4 sm:p-5 space-y-5">
      <div>
        <div className="stat-label mb-2.5">Dimension scores</div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {DIMENSIONS.map(({ key, label }) => {
            const v = dataset[key] as number | null;
            const tone = scoreTone(v);
            return (
              <div key={key} className="min-w-0">
                <div className="flex items-baseline justify-between gap-2 text-xs">
                  <span className="text-ink-faint truncate">{label}</span>
                  <span className={`tabular-nums font-medium ${TONE_TEXT[tone]}`}>{v === null ? "—" : formatScore(v)}</span>
                </div>
                <div className="mt-1.5">
                  <Meter value={v} tone={tone} label={`${label} score`} />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div>
        <div className="stat-label mb-2.5">Rule results</div>
        {detail.isLoading && (
          <Loading label="Loading rule results">
            <SkeletonTable rows={4} cols={6} />
          </Loading>
        )}
        {detail.isError && <ErrorState message="Could not load rule results." onRetry={() => detail.refetch()} />}
        {detail.data && detail.data.rules.length === 0 && <div className="text-sm text-ink-faint">No rules apply to this dataset.</div>}
        {detail.data && detail.data.rules.length > 0 && (
          <div className="rounded-md border border-surface-border overflow-x-auto bg-surface-raised">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Rule</th>
                  <th>Dimension</th>
                  <th>Severity</th>
                  <th className="text-right">Applicable</th>
                  <th className="text-right">Failed</th>
                  <th className="w-40">Failure rate</th>
                </tr>
              </thead>
              <tbody>
                {detail.data.rules.map((r) => (
                  <tr key={r.rule_id} data-reveal>
                    <td>
                      <span className="font-mono text-xs text-ink-faint mr-2">{r.rule_id}</span>
                      <span className="text-ink">{r.rule_name}</span>
                    </td>
                    <td className="capitalize text-ink-muted">{r.dimension}</td>
                    <td>
                      <ToneBadge tone={severityTone(r.severity)} dot={false}>
                        {r.severity}
                      </ToneBadge>
                    </td>
                    <td className="text-right text-ink-muted">{formatInt(r.records_applicable)}</td>
                    <td className={`text-right ${r.records_failed > 0 ? "text-warn" : "text-ink-muted"}`}>{formatInt(r.records_failed)}</td>
                    <td>
                      <div className="flex items-center gap-2">
                        <span className="tabular-nums text-xs w-12 text-right text-ink-muted">{(r.failure_rate * 100).toFixed(1)}%</span>
                        <div className="meter flex-1" aria-hidden="true">
                          <span className={r.records_failed > 0 ? "bg-warn/70" : "bg-accent/40"} style={{ width: `${Math.max(r.failure_rate * 100, r.records_failed > 0 ? 2 : 0)}%` }} />
                        </div>
                      </div>
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

export default function DataQuality() {
  const [expanded, setExpanded] = useState<string | null>(null);

  const summary = useQuery({
    queryKey: ["quality-summary"],
    queryFn: async () => (await api.get<{ run_id: number | null; datasets: DatasetQualityScore[] }>("/quality/summary")).data,
  });
  const datasets = summary.data?.datasets ?? [];
  const revealRef = useReveal(datasets.length > 0);

  const overall = datasets.length ? datasets.reduce((acc, d) => acc + d.score_overall, 0) / datasets.length : null;
  const counts = datasets.reduce(
    (acc, d) => {
      acc[scoreTone(d.score_overall)] += 1;
      return acc;
    },
    { good: 0, warn: 0, bad: 0, neutral: 0, info: 0 } as Record<Tone, number>,
  );
  const quarantined = datasets.reduce((a, d) => a + d.records_quarantined, 0);
  const rejected = datasets.reduce((a, d) => a + d.records_rejected, 0);

  return (
    <div>
      <PageHeader title="Data Quality" subtitle="Six-dimension quality scoring per dataset, drill down to the exact rule that failed." />
      <PageBody>
        {summary.isLoading && (
          <Loading label="Loading data quality summary">
            <SkeletonTiles />
            <div className="mt-6">
              <SkeletonTable rows={6} cols={7} />
            </div>
          </Loading>
        )}
        {summary.isError && <ErrorState message="Could not load data quality summary." onRetry={() => summary.refetch()} />}
        {summary.data && datasets.length === 0 && <EmptyState message="No pipeline run has completed yet." />}

        {datasets.length > 0 && (
          <div ref={revealRef} className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <StatTile
                label="Platform score"
                count={overall}
                format={formatScore}
                tone={scoreTone(overall)}
                meter={{ value: overall }}
                emphasis
              />
              <StatTile
                label="Datasets scored"
                count={datasets.length}
                sub={[counts.good && `${counts.good} healthy`, counts.warn && `${counts.warn} watch`, counts.bad && `${counts.bad} failing`].filter(Boolean).join(" · ")}
              />
              <StatTile label="Quarantined records" count={quarantined} tone={quarantined > 0 ? "warn" : undefined} sub="Held for review, never dropped" />
              <StatTile label="Rejected records" count={rejected} tone={rejected > 0 ? "bad" : undefined} sub={`Latest run #${summary.data?.run_id ?? "—"}`} />
            </div>

            <div data-reveal className="card overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Dataset</th>
                    <th className="text-right">Ingested</th>
                    <th className="text-right">Accepted</th>
                    <th className="text-right">Warned</th>
                    <th className="text-right">Quarantined</th>
                    <th className="text-right">Rejected</th>
                    <th className="w-44">Score</th>
                  </tr>
                </thead>
                <tbody>
                  {datasets.map((d) => {
                    const isOpen = expanded === d.dataset;
                    const tone = scoreTone(d.score_overall);
                    const toggle = () => setExpanded(isOpen ? null : d.dataset);
                    return (
                      <Fragment key={d.dataset}>
                        <tr onClick={toggle} className={`row-link ${isOpen ? "row-selected" : ""}`}>
                          <td>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                toggle();
                              }}
                              aria-expanded={isOpen}
                              aria-controls={`dq-${d.dataset}`}
                              className="inline-flex items-center gap-2 text-ink font-medium"
                            >
                              <Icon.ChevronRight
                                size={12}
                                className={`text-ink-faint transition-transform duration-200 ${isOpen ? "rotate-90 text-accent" : ""}`}
                              />
                              {d.dataset}
                            </button>
                          </td>
                          <td className="text-right text-ink-muted">{formatInt(d.records_ingested)}</td>
                          <td className="text-right text-ink-muted">{formatInt(d.records_accepted)}</td>
                          <td className="text-right text-ink-muted">{formatInt(d.records_warned)}</td>
                          <td className={`text-right ${d.records_quarantined > 0 ? "text-warn" : "text-ink-muted"}`}>{formatInt(d.records_quarantined)}</td>
                          <td className={`text-right ${d.records_rejected > 0 ? "text-danger" : "text-ink-muted"}`}>{formatInt(d.records_rejected)}</td>
                          <td>
                            <div className="flex items-center gap-2.5">
                              <span className={`tabular-nums font-medium w-10 ${TONE_TEXT[tone]}`}>{formatScore(d.score_overall)}</span>
                              <div className="flex-1 min-w-[48px]">
                                <Meter value={d.score_overall} tone={tone} label={`${d.dataset} score`} />
                              </div>
                              <span className={`text-2xs w-12 ${TONE_TEXT[tone]}`}>{scoreLabel(d.score_overall)}</span>
                            </div>
                          </td>
                        </tr>
                        {isOpen && (
                          <tr id={`dq-${d.dataset}`} className="hover:bg-transparent">
                            <td colSpan={7} className="bg-surface-sunken/70 p-0">
                              <DatasetDetail dataset={d} />
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </PageBody>
    </div>
  );
}
