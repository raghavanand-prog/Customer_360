import { useState } from "react";
import { Icon } from "./Icons";

// Human-readable view of a segment rule AST, mirroring the semantics of the
// backend compiler (backend/c360/segments/compiler.py):
//   group: {op: "AND"|"OR", children: [...]},  {op: "NOT", children: [node]}
//   leaf:  {op, field, value}  where value may be {param: name} -> thresholds[name]
//          ops: > >= < <= = != IN "NOT IN" "IS NULL" "IS NOT NULL"
// Anything that doesn't match that grammar falls back to the raw JSON, so the
// view never guesses at a rule it doesn't understand.

interface RuleNode {
  op: string;
  field?: string;
  value?: unknown;
  children?: RuleNode[];
}

const COMPARE: Record<string, string> = { ">": ">", ">=": "≥", "<": "<", "<=": "≤", "=": "=", "!=": "≠", IN: "in", "NOT IN": "not in" };
const NULL_OPS: Record<string, string> = { "IS NULL": "is empty", "IS NOT NULL": "is present" };

function isRule(node: unknown): node is RuleNode {
  if (!node || typeof node !== "object") return false;
  const n = node as Record<string, unknown>;
  if (typeof n.op !== "string") return false;
  if (n.op === "AND" || n.op === "OR") return Array.isArray(n.children) && n.children.length > 0 && n.children.every(isRule);
  if (n.op === "NOT") return Array.isArray(n.children) && n.children.length === 1 && isRule(n.children[0]);
  if (typeof n.field !== "string") return false;
  if (n.op in NULL_OPS) return true;
  if (n.op === "IN" || n.op === "NOT IN") return Array.isArray(n.value);
  return n.op in COMPARE && "value" in n;
}

function literal(v: unknown): string {
  if (typeof v === "number") return v.toLocaleString("en-IN");
  if (typeof v === "string") return `"${v}"`;
  return JSON.stringify(v);
}

function Value({ v, thresholds }: { v: unknown; thresholds: Record<string, unknown> }) {
  if (v && typeof v === "object" && !Array.isArray(v) && "param" in v) {
    const name = String((v as { param: unknown }).param);
    const resolved = thresholds[name];
    return (
      <span className="inline-flex flex-wrap items-baseline gap-x-1.5">
        <span className="font-mono text-accent">{resolved === undefined ? "?" : literal(resolved)}</span>
        <span className="text-2xs text-ink-faint font-mono" title="Threshold parameter, resolved from this version's thresholds">
          {name}
        </span>
      </span>
    );
  }
  if (Array.isArray(v)) {
    return (
      <span className="font-mono text-accent">
        ({v.map((x, i) => (
          <span key={i}>
            {i > 0 && ", "}
            <Value v={x} thresholds={thresholds} />
          </span>
        ))})
      </span>
    );
  }
  return <span className="font-mono text-accent">{literal(v)}</span>;
}

function Node({ node, thresholds }: { node: RuleNode; thresholds: Record<string, unknown> }) {
  if (node.op === "AND" || node.op === "OR") {
    return (
      <div className="rounded-md border border-surface-border bg-white/[0.015]">
        <div className="px-3 py-1.5 text-2xs uppercase tracking-[0.08em] text-ink-faint border-b border-surface-border">
          {node.op === "AND" ? "All of" : "Any of"}
        </div>
        <ul className="p-2 space-y-1.5">
          {node.children!.map((c, i) => (
            <li key={i} className="flex items-start gap-2">
              <span className="mt-2 font-mono text-2xs text-ink-faint w-7 shrink-0 text-right">{i === 0 ? "" : node.op.toLowerCase()}</span>
              <div className="flex-1 min-w-0">
                <Node node={c} thresholds={thresholds} />
              </div>
            </li>
          ))}
        </ul>
      </div>
    );
  }
  if (node.op === "NOT") {
    return (
      <div className="flex items-start gap-2">
        <span className="mt-2 text-2xs uppercase tracking-[0.08em] text-danger/80">Not</span>
        <div className="flex-1 min-w-0">
          <Node node={node.children![0]} thresholds={thresholds} />
        </div>
      </div>
    );
  }
  return (
    <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1 rounded-md border border-surface-border bg-surface-sunken px-3 py-2 text-sm">
      <span className="font-mono text-ink">{node.field}</span>
      <span className="text-ink-muted">{COMPARE[node.op] ?? NULL_OPS[node.op]}</span>
      {!(node.op in NULL_OPS) && <Value v={node.value} thresholds={thresholds} />}
    </div>
  );
}

export function RuleView({ ast, thresholds }: { ast: unknown; thresholds: Record<string, unknown> | undefined }) {
  const readable = isRule(ast);
  const [showJson, setShowJson] = useState(!readable);
  const json = JSON.stringify(ast, null, 2);

  return (
    <div className="space-y-3">
      {readable && <Node node={ast} thresholds={thresholds ?? {}} />}
      {readable && (
        <button
          type="button"
          onClick={() => setShowJson((v) => !v)}
          aria-expanded={showJson}
          className="btn-ghost -ml-2"
        >
          <Icon.ChevronRight size={12} className={`transition-transform duration-200 ${showJson ? "rotate-90" : ""}`} />
          {showJson ? "Hide rule JSON" : "View rule JSON"}
        </button>
      )}
      {showJson && (
        <pre className="state-panel text-xs leading-relaxed bg-surface-sunken border border-surface-border rounded-md p-4 overflow-x-auto text-ink-muted font-mono">
          {json}
        </pre>
      )}
    </div>
  );
}
