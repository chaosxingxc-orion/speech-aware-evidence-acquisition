"""scripts/flights/refresh_registered_plan_pins.py on a synthetic tree (no model, no GPU)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[2] / "scripts" / "flights" / "refresh_registered_plan_pins.py"
_spec = importlib.util.spec_from_file_location("refresh_registered_plan_pins", _PATH)
tool = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tool)

REAL = "ab" * 32
PLACEHOLDER = "0" * 64
RELPATH = "prepared/X/phase-supply-v1.json"


def _w(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _tree(tmp_path: Path, baseline_sha: str, cell_in_plan: str = "cell-1"):
    _w(tmp_path / "configs/experiment/exp-1.json",
       {"cells": [{"cell_id": "cell-1", "baseline_fragment": "base-1"}]})
    _w(tmp_path / "configs/baseline/base-1.json",
       {"prepared_phase_supply": {"relpath": RELPATH, "sha256": baseline_sha}})
    pkg = tmp_path / "docs/readiness/pkg"
    _w(pkg / "generation-plan-registered-v1.json", {
        "cell": cell_in_plan, "experiment": "exp-1",
        "prepared_phase_supply": {"relpath": RELPATH, "sha256": PLACEHOLDER,
                                  "note": "minted at the flip", "expected_output_sha256": "cd" * 32},
    })
    return pkg, pkg / "generation-plan-registered-v1.json"


def test_placeholder_baseline_leaves_plan_unchanged(tmp_path):
    pkg, plan = _tree(tmp_path, PLACEHOLDER)
    before = plan.read_bytes()
    out = tool.refresh_package(tmp_path, pkg)
    assert out[0]["status"] == "unchanged" and plan.read_bytes() == before


def test_minted_baseline_refreshes_and_moves_annotations(tmp_path):
    pkg, plan = _tree(tmp_path, REAL)
    out = tool.refresh_package(tmp_path, pkg)
    doc = json.loads(plan.read_text(encoding="utf-8"))
    assert out[0]["status"] == "refreshed" and out[0]["after"] == REAL
    assert doc["prepared_phase_supply"] == {"relpath": RELPATH, "sha256": REAL}
    assert doc["prepared_phase_supply_annotations"] == {"note": "minted at the flip",
                                                        "expected_output_sha256": "cd" * 32}


def test_second_run_is_idempotent(tmp_path):
    pkg, plan = _tree(tmp_path, REAL)
    tool.refresh_package(tmp_path, pkg)
    first = plan.read_bytes()
    out = tool.refresh_package(tmp_path, pkg)
    assert out[0]["status"] == "unchanged" and plan.read_bytes() == first


def test_dry_writes_nothing(tmp_path, capsys):
    pkg, plan = _tree(tmp_path, REAL)
    before = plan.read_bytes()
    assert tool.main(["--package", str(pkg), "--repo-root", str(tmp_path), "--dry"]) == 0
    assert plan.read_bytes() == before
    assert "refreshed" in capsys.readouterr().out


def test_unresolvable_cell_is_refused_by_name(tmp_path, capsys):
    pkg, plan = _tree(tmp_path, REAL, cell_in_plan="no-such-cell")
    before = plan.read_bytes()
    assert tool.main(["--package", str(pkg), "--repo-root", str(tmp_path)]) == 2
    err = capsys.readouterr().err
    assert "no-such-cell" in err and "generation-plan-registered-v1.json" in err
    assert plan.read_bytes() == before
    with pytest.raises(tool.RefreshError):
        tool.refresh_package(tmp_path, pkg)
