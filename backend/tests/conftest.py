import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def spark():
    from c360.spark.session import build_spark
    s = build_spark("pytest", master="local[2]")
    yield s
    s.stop()


def _generate(out_dir: Path, defect_profile: str) -> Path:
    subprocess.run(
        [sys.executable, "-m", "c360.generator.main", "--seed", "7", "--size", "tiny",
         "--out-dir", str(out_dir), "--defect-profile", defect_profile],
        check=True, cwd=BACKEND_ROOT,
    )
    return out_dir / "input"


@pytest.fixture(scope="session")
def generated_tiny_dataset(tmp_path_factory):
    return _generate(tmp_path_factory.mktemp("dq_default"), "default")


@pytest.fixture(scope="session")
def generated_tiny_clean_dataset(tmp_path_factory):
    return _generate(tmp_path_factory.mktemp("dq_none"), "none")
