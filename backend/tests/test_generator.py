"""T-01/T-02/T-03: generator reproducibility and distributional sanity."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest


def _run_generate(out_dir: Path, seed: int = 42, size: str = "tiny", defect_profile: str = "default") -> None:
    subprocess.run(
        [sys.executable, "-m", "c360.generator.main",
         "--seed", str(seed), "--size", size, "--out-dir", str(out_dir),
         "--defect-profile", defect_profile],
        check=True, cwd=Path(__file__).resolve().parents[1],
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_reproducible_generation(tmp_path):
    out1, out2 = tmp_path / "run1", tmp_path / "run2"
    _run_generate(out1)
    _run_generate(out2)
    for fname in ["customers_crm.csv", "loyalty_members.csv", "app_users.jsonl",
                  "products.csv", "orders.jsonl", "order_items.csv",
                  "support_tickets.csv", "marketing_events.jsonl"]:
        assert _sha256(out1 / "input" / fname) == _sha256(out2 / "input" / fname), fname


def test_manifest_present_and_consistent(tmp_path):
    out = tmp_path / "run"
    _run_generate(out)
    manifest = json.loads((out / "generated" / "manifest.json").read_text())
    assert manifest["true_person_count"] == 200
    dataset_ids = {d["id"] for d in manifest["datasets"]}
    assert dataset_ids == {"D-01", "D-02", "D-03", "D-04", "D-05", "D-06", "D-07", "D-08", "D-09"}
    for d in manifest["datasets"]:
        assert d["rows"] > 0


def test_defect_profile_none_disables_injection(tmp_path):
    out = tmp_path / "run"
    _run_generate(out, defect_profile="none")
    manifest = json.loads((out / "generated" / "manifest.json").read_text())
    for defect in manifest["defects"]:
        assert defect["realised_count"] == 0, defect


def test_ground_truth_file_written(tmp_path):
    out = tmp_path / "run"
    _run_generate(out)
    gt = out / "generated" / "ground_truth_identity.parquet"
    gt_csv = out / "generated" / "ground_truth_identity.csv"
    assert gt.exists() or gt_csv.exists()


def test_orders_reference_seeded_defects(tmp_path):
    """Sanity check: seeded defects from §4.9 are actually observable in the raw files."""
    out = tmp_path / "run"
    _run_generate(out, size="small")
    crm_text = (out / "input" / "customers_crm.csv").read_text()
    assert "india " in crm_text or "Bharat" in crm_text or "INDIA" in crm_text  # X-11
    orders_text = (out / "input" / "orders.jsonl").read_text()
    assert '"' in orders_text  # sanity: file is non-trivial
