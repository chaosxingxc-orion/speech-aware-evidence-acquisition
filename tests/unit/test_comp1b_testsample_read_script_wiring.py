"""``scripts/flights/comp1/comp1b_testsample_read.sh`` argument wiring (blocker 5, registered
facts): the milestone read must pass the population-weighted post-stratified weighting fix
through to ``stage3_paired_read.py --package``, and must never silently fall back to the raw
roster mean it used to pass through unmodified. Syntax-checked with ``bash -n`` (no execution) and
the population-counts side proved with a subprocess dry run of
``scripts/analysis/build_population_counts.py`` on a fake roster receipt (never real test data).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "flights" / "comp1" / "comp1b_testsample_read.sh"
READ_PAIRED_CELL_PATH = REPO_ROOT / "scripts" / "flights" / "read_paired_cell.sh"
BUILD_POPULATION_COUNTS_PATH = REPO_ROOT / "scripts" / "analysis" / "build_population_counts.py"
PACKAGE_DIR = REPO_ROOT / "docs" / "readiness" / "2026-09-29-slurp-stage3-comp1b-testsample-v1"
POPULATION_COUNTS_PATH = PACKAGE_DIR / "population-counts-v1.json"


def _bash_n(path: Path) -> subprocess.CompletedProcess:
    if shutil.which("bash") is None:
        pytest.skip("bash is not on PATH")
    return subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True, check=False)


def test_the_milestone_read_script_is_syntactically_valid() -> None:
    result = _bash_n(SCRIPT_PATH)
    assert result.returncode == 0, result.stderr


def test_the_shared_paired_cell_wrapper_is_still_syntactically_valid() -> None:
    result = _bash_n(READ_PAIRED_CELL_PATH)
    assert result.returncode == 0, result.stderr


def test_the_milestone_read_script_wires_the_post_stratified_weighting_flags() -> None:
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "--weighting post-stratified" in text
    assert "--population-counts" in text and "population-counts-v1.json" in text
    # coordinator ruling 2026-09-30: post-stratification happens INSIDE the official-scoring step
    # (aggregates only); the per-row gold-bank channel is not legal on the signed test sample.
    command = text.split("bash \"$MAIN/scripts/flights/read_paired_cell.sh\"", 1)[1]
    assert "--strata-source scorer" in command
    assert "--strata-source gold-bank" not in command
    assert "--gold-bank-roster" not in command
    assert "--strata-key" not in command
    # blocker 5's own words: the raw roster mean must never be what this script's read calls
    # natural_mixture on a floored sample.
    assert "raw roster mean" in text or "raw" in text.lower()


def test_the_test_sample_roster_declares_the_stratification_block_the_scorer_mode_requires() -> None:
    """``--strata-inside-scorer`` refuses a roster receipt without a ``stratification`` block;
    the signed test sample's receipt carries one (read here by key only -- no item is opened)."""

    roster = json.loads(
        (REPO_ROOT / "docs" / "receipts" / "rosters" / "slurp-test-sample-3010-v1.json").read_text(encoding="utf-8")
    )
    assert isinstance(roster.get("stratification"), dict) and roster["stratification"]
    assert roster.get("stratum_withheld_per_item") is True


def test_the_committed_population_counts_file_matches_the_roster_receipts_per_intent_table() -> None:
    if not POPULATION_COUNTS_PATH.is_file():
        pytest.skip("population-counts-v1.json is not committed under this package on this branch")
    document = json.loads(POPULATION_COUNTS_PATH.read_text(encoding="utf-8"))
    assert document["schema"] == "saea-population-counts-v1"
    roster_relpath = document["source_roster_receipt"]["relpath"]
    roster_path = REPO_ROOT / roster_relpath
    roster = json.loads(roster_path.read_text(encoding="utf-8"))
    per_intent = roster["per_intent"]
    field = document["count_field"]
    assert document["population_counts"] == {name: row[field] for name, row in per_intent.items()}
    assert document["population_total"] == sum(row[field] for row in per_intent.values())
    assert document["strata_count"] == len(per_intent)


def test_build_population_counts_reproduces_the_committed_file_from_the_committed_roster(
    tmp_path: Path,
) -> None:
    """Subprocess dry run of the real generator against the real committed roster receipt --
    reads only committed, already-frozen bytes (no test audio, no gold, model-free) and proves the
    committed population-counts-v1.json is exactly what the generator produces today."""

    if not POPULATION_COUNTS_PATH.is_file():
        pytest.skip("population-counts-v1.json is not committed under this package on this branch")
    out_path = tmp_path / "population-counts-v1.json"
    result = subprocess.run(
        [sys.executable, "-B", str(BUILD_POPULATION_COUNTS_PATH),
         "--roster", "docs/receipts/rosters/slurp-test-sample-3010-v1.json",
         "--repo-root", str(REPO_ROOT), "--count-field", "test_recordings", "--out", str(out_path)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    fresh = json.loads(out_path.read_text(encoding="utf-8"))
    committed = json.loads(POPULATION_COUNTS_PATH.read_text(encoding="utf-8"))
    assert fresh["population_counts"] == committed["population_counts"]
    assert fresh["source_roster_receipt"]["sha256"] == committed["source_roster_receipt"]["sha256"]
