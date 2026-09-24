"""Chunking for the RAG knowledge corpus (§8 of the Adobe-JD AI phase).

The corpus is real project documentation, not invented text:
docs/DATA_DICTIONARY.md, docs/ARCHITECTURE.md, docs/DATA_PIPELINE.md,
config/dq_rules.yaml, config/segments.yaml. Structured sources (the two
YAML files) get one chunk per logical unit (one DQ rule, one segment
definition) rather than being split by character count, since that keeps
each chunk semantically whole -- exactly the unit an answer would cite.
"""
from __future__ import annotations

from dataclasses import dataclass

import yaml


@dataclass
class Chunk:
    source: str
    section: str
    content: str
    metadata: dict


def chunk_markdown(text: str, source: str, max_chars: int = 900) -> list[Chunk]:
    """Split a Markdown file on its `##`/`###` headings, then further split
    any section still over `max_chars` on paragraph boundaries."""
    lines = text.splitlines()
    sections: list[tuple[str, list[str]]] = []
    current_heading = "Introduction"
    current_lines: list[str] = []
    for line in lines:
        if line.startswith("## ") or line.startswith("### "):
            if current_lines:
                sections.append((current_heading, current_lines))
            current_heading = line.lstrip("#").strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines:
        sections.append((current_heading, current_lines))

    chunks: list[Chunk] = []
    for heading, body_lines in sections:
        body = "\n".join(body_lines).strip()
        if not body:
            continue
        if len(body) <= max_chars:
            chunks.append(Chunk(source=source, section=heading, content=body, metadata={"kind": "markdown_section"}))
            continue
        paragraphs = [p for p in body.split("\n\n") if p.strip()]
        buf = ""
        part = 1
        for para in paragraphs:
            if buf and len(buf) + len(para) + 2 > max_chars:
                chunks.append(Chunk(
                    source=source, section=f"{heading} (part {part})", content=buf.strip(),
                    metadata={"kind": "markdown_section"},
                ))
                part += 1
                buf = para
            else:
                buf = f"{buf}\n\n{para}" if buf else para
        if buf.strip():
            chunks.append(Chunk(
                source=source, section=f"{heading} (part {part})" if part > 1 else heading,
                content=buf.strip(), metadata={"kind": "markdown_section"},
            ))
    return chunks


def chunk_dq_rules(yaml_text: str, source: str) -> list[Chunk]:
    """One chunk per data-quality rule (config/dq_rules.yaml)."""
    data = yaml.safe_load(yaml_text)
    chunks: list[Chunk] = []
    datasets = data.get("datasets", data) if isinstance(data, dict) else {}
    for dataset_name, dataset_obj in (datasets.items() if isinstance(datasets, dict) else []):
        rules = dataset_obj.get("rules", []) if isinstance(dataset_obj, dict) else dataset_obj
        if not isinstance(rules, list):
            continue
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            rule_id = rule.get("id", "unknown")
            lines = [f"Dataset: {dataset_name}", f"Rule {rule_id}: {rule.get('name', '')}"]
            for key in ("dimension", "type", "column", "columns", "applies_when", "severity", "threshold_dataset_fail_rate"):
                if key in rule:
                    lines.append(f"{key}: {rule[key]}")
            chunks.append(Chunk(
                source=source, section=f"DQ rule {rule_id} ({dataset_name})",
                content="\n".join(lines),
                metadata={"kind": "dq_rule", "rule_id": rule_id, "dataset": dataset_name},
            ))
    return chunks


def chunk_segments(yaml_text: str, source: str) -> list[Chunk]:
    """One chunk per segment definition (config/segments.yaml)."""
    data = yaml.safe_load(yaml_text)
    segments = data.get("segments", data) if isinstance(data, dict) else data
    chunks: list[Chunk] = []
    if not isinstance(segments, list):
        return chunks
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        seg_id = segment.get("id", "unknown")
        lines = [
            f"Segment {seg_id}: {segment.get('name', '')}",
            f"Description: {segment.get('description', '')}",
            f"Null handling: {segment.get('null_handling', '')}",
        ]
        if "rule_ast" in segment:
            lines.append(f"Rule definition (JSON AST): {segment['rule_ast']}")
        if "thresholds" in segment:
            lines.append(f"Thresholds: {segment['thresholds']}")
        chunks.append(Chunk(
            source=source, section=f"Segment {seg_id} ({segment.get('name', '')})",
            content="\n".join(lines),
            metadata={"kind": "segment_definition", "segment_id": seg_id},
        ))
    return chunks
