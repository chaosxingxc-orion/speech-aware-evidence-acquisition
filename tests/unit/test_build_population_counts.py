"""``scripts/analysis/build_population_counts.py``: the {stratum: population_count} extraction a
floored roster's post-stratified weighting needs, straight from a committed roster receipt's own
``per_intent`` table -- never by reading the test split. Loaded by file path: the shared venv
carries a top-level ``scripts`` package (verl 0.8.0) that shadows this repository's own.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "analysis" / "build_population_counts.py"


def _load():
    spec = importlib.util.spec_from_file_location("_test_build_population_counts", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mod = _load()


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _fake_roster(*, general_greet_zero: bool = True) -> dict:
    per_intent = {
        "alarm_query": {"test_recordings": 225, "test_utterances": 34, "sample_recordings": 63,
                        "sample_utterances": 10, "closure_recordings": 162, "closure_utterances": 24},
        "weather_query": {"test_recordings": 682, "test_utterances": 89, "sample_recordings": 89,
                          "sample_utterances": 26, "closure_recordings": 593, "closure_utterances": 63},
    }
    if general_greet_zero:
        per_intent["general_greet"] = {"test_recordings": 15, "test_utterances": 1,
                                       "sample_recordings": 0, "sample_utterances": 0,
                                       "closure_recordings": 15, "closure_utterances": 1}
    return {
        "schema": "saea-roster-receipt-v1", "roster_id": "SLURP-TEST-SAMPLE-3010-V1",
        "split_identity_hash": "deadbeef", "per_intent": per_intent,
        "strata_definition": "GOLD INTENT scenario_action of the prompt",
    }


def test_build_extracts_test_recordings_by_default(tmp_path: Path) -> None:
    roster_path = tmp_path / "roster.json"
    _write(roster_path, _fake_roster())
    document = mod.build(roster_path, count_field="test_recordings", roster_relpath="docs/roster.json")
    assert document["schema"] == mod.SCHEMA
    assert document["population_counts"] == {"alarm_query": 225, "weather_query": 682, "general_greet": 15}
    assert document["population_total"] == 225 + 682 + 15
    assert document["strata_count"] == 3
    assert document["count_field"] == "test_recordings"
    assert document["source_roster_receipt"]["relpath"] == "docs/roster.json"
    assert document["source_roster_receipt"]["roster_id"] == "SLURP-TEST-SAMPLE-3010-V1"
    assert document["source_roster_receipt"]["sha256"] == hashlib.sha256(roster_path.read_bytes()).hexdigest()


def test_build_extracts_test_utterances_when_asked(tmp_path: Path) -> None:
    roster_path = tmp_path / "roster.json"
    _write(roster_path, _fake_roster())
    document = mod.build(roster_path, count_field="test_utterances", roster_relpath="docs/roster.json")
    assert document["population_counts"] == {"alarm_query": 34, "weather_query": 89, "general_greet": 1}


def test_build_refuses_a_roster_with_no_per_intent_table(tmp_path: Path) -> None:
    roster_path = tmp_path / "roster.json"
    _write(roster_path, {"schema": "saea-roster-receipt-v1", "roster_id": "X"})
    with pytest.raises(mod.PopulationCountsError):
        mod.build(roster_path, count_field="test_recordings", roster_relpath="docs/roster.json")


def test_build_refuses_a_negative_or_missing_count(tmp_path: Path) -> None:
    roster_path = tmp_path / "roster.json"
    bad = _fake_roster()
    bad["per_intent"]["alarm_query"]["test_recordings"] = -1
    _write(roster_path, bad)
    with pytest.raises(mod.PopulationCountsError):
        mod.build(roster_path, count_field="test_recordings", roster_relpath="docs/roster.json")

    roster_path2 = tmp_path / "roster2.json"
    bad2 = _fake_roster()
    del bad2["per_intent"]["alarm_query"]["test_recordings"]
    _write(roster_path2, bad2)
    with pytest.raises(mod.PopulationCountsError):
        mod.build(roster_path2, count_field="test_recordings", roster_relpath="docs/roster2.json")


def test_build_refuses_an_unknown_count_field(tmp_path: Path) -> None:
    roster_path = tmp_path / "roster.json"
    _write(roster_path, _fake_roster())
    with pytest.raises(mod.PopulationCountsError):
        mod.build(roster_path, count_field="sample_recordings", roster_relpath="docs/roster.json")


def test_main_writes_the_counts_file_with_a_sha256(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    roster_relpath = "docs/receipts/rosters/fake.json"
    _write(repo / roster_relpath, _fake_roster())
    out_path = tmp_path / "out" / "population-counts-v1.json"
    code = mod.main([
        "--roster", roster_relpath, "--repo-root", str(repo), "--out", str(out_path),
    ])
    assert code == 0
    document = json.loads(out_path.read_text(encoding="utf-8"))
    assert document["population_counts"]["alarm_query"] == 225
    assert document["strata_count"] == 3


def test_main_cli_subprocess_dry_run_on_a_fake_roster(tmp_path: Path) -> None:
    """A subprocess-level dry run: the CLI as a caller (the milestone package's generation step)
    would actually invoke it, on a fake roster receipt -- never real test data."""

    repo = tmp_path / "repo"
    roster_relpath = "docs/receipts/rosters/fake.json"
    _write(repo / roster_relpath, _fake_roster())
    out_path = tmp_path / "out" / "population-counts-v1.json"
    result = subprocess.run(
        [sys.executable, "-B", str(SCRIPT_PATH), "--roster", roster_relpath,
         "--repo-root", str(repo), "--out", str(out_path)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["strata_count"] == 3
    assert out_path.is_file()


def test_main_refuses_and_exits_nonzero_on_a_bad_roster(tmp_path: Path, capsys) -> None:
    repo = tmp_path / "repo"
    roster_relpath = "docs/receipts/rosters/fake.json"
    _write(repo / roster_relpath, {"schema": "saea-roster-receipt-v1"})
    out_path = tmp_path / "out" / "population-counts-v1.json"
    code = mod.main(["--roster", roster_relpath, "--repo-root", str(repo), "--out", str(out_path)])
    assert code == 1
    assert not out_path.exists()
    assert "REFUSED" in capsys.readouterr().err
