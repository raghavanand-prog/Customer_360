"""Defect injection bookkeeping (§4.9, §5.6).

Each named defect is injected inline, at its configured rate, by the writer
functions in ``writers.py``. This module only tracks *realised* counts so
that ``manifest.json`` reports what actually happened, which is what tests
compare against (never a hard-coded expectation).
"""
from __future__ import annotations

from collections import defaultdict

from .config import DEFECT_RATES


class DefectTracker:
    def __init__(self, defect_profile: str = "default") -> None:
        self.defect_profile = defect_profile
        self.realised: dict[str, int] = defaultdict(int)
        self.applicable: dict[str, int] = defaultdict(int)

    def rate(self, defect_id: str) -> float:
        if self.defect_profile == "none":
            return 0.0
        base = DEFECT_RATES.get(defect_id, 0.0)
        if self.defect_profile == "aggressive":
            return min(base * 2, 0.9) if base < 1 else base
        return base

    def record(self, defect_id: str, applicable: int = 1) -> None:
        self.realised[defect_id] += 1
        self.applicable[defect_id] += applicable

    def note_applicable(self, defect_id: str, count: int = 1) -> None:
        self.applicable[defect_id] += count

    def to_manifest_section(self) -> list[dict]:
        out = []
        for defect_id, configured in DEFECT_RATES.items():
            realised_count = self.realised.get(defect_id, 0)
            applicable = self.applicable.get(defect_id, 0)
            realised_rate = (realised_count / applicable) if applicable else 0.0
            out.append({
                "id": defect_id,
                "configured_rate": self.rate(defect_id),
                "realised_count": realised_count,
                "realised_rate": round(realised_rate, 5),
            })
        return out
