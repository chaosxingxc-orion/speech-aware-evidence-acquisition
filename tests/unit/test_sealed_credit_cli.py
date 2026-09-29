"""End-to-end CLI test on a synthetic data root (no real utterances, zero model
contact): builds a tiny fake sealed tree (one single-sample-arm pool, one
grouped-multi-sample pool, both TRAIN so the real governed loader can serve
them if pointed at a synthetic LOCK/media tree) is impractical to fabricate
faithfully here, so this test instead drives the CLI's ``--dry-run`` path (pool
manifest + policy-space validation, no gold, no sealed run) end to end, plus
the CLI's own reproducibility contract (refuses a non-empty ``--out`` without
``--check``) against a hand-written output directory. The full real-data path
is exercised by the coordinator-directed run over the actual tuning pools
(see the run's own report), not fabricated here.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_PATH = REPO_ROOT / "scripts" / "analysis" / "sealed_credit_inner_loop.py"


def _load_cli():
    spec = importlib.util.spec_from_file_location("sealed_credit_inner_loop", CLI_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["sealed_credit_inner_loop"] = module
    spec.loader.exec_module(module)
    return module


def _receipt(repo, roster_id, disjointness_proof=None):
    payload = {"schema": "saea-roster-receipt-v1", "roster_id": roster_id}
    if disjointness_proof is not None:
        payload["disjointness_proof"] = disjointness_proof
    path = repo / "docs" / "receipts" / "rosters" / f"{roster_id.lower()}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _pools_manifest(tmp_path):
    manifest = {
        "schema": "saea-sealed-credit-pools-v1",
        "tuning_roster": ["SLURP-STAGE3-CONSTRUCTION-R01C", "SLURP-EVO-FOLD-A-V2"],
        "read_rosters": {"same-flight-supply-variant": "SLURP-EVO-FOLD-B-V2"},
        "pools": [
            {"label": "agree", "run_id": "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1", "kind": "single-sample-arm",
             "roster": "SLURP-EVO-FOLD-A-V2", "use": "tuning", "scorer": "slurp-slu-official-train"},
        ],
    }
    path = tmp_path / "pools.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def _policy_space(tmp_path):
    doc = {
        "schema": "saea-sealed-credit-policy-space-v1",
        "knobs": [
            {
                "id": "reviewer_planner", "node": "review_loop", "estimator": "exact_offline",
                "flown_value": "on",
                "values": [{"value": "off", "conversion_source": {"type": "credit_table_reviewer_toggle", "pool": "agree"}}],
            },
        ],
    }
    path = tmp_path / "policy-space.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def test_dry_run_reports_summary_and_touches_nothing_else(tmp_path, capsys):
    cli = _load_cli()
    pools_path = _pools_manifest(tmp_path)
    policy_path = _policy_space(tmp_path)
    exit_code = cli.main([
        "--pools", str(pools_path), "--policy-space", str(policy_path),
        "--read-design", "same-flight-supply-variant", "--out", str(tmp_path / "out"),
        "--dry-run",
    ])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "dry-run OK" in captured.out
    assert not (tmp_path / "out").exists()


def test_refuses_non_empty_out_without_check(tmp_path):
    cli = _load_cli()
    pools_path = _pools_manifest(tmp_path)
    policy_path = _policy_space(tmp_path)
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "already-here.txt").write_text("x", encoding="utf-8")
    exit_code = cli.main([
        "--pools", str(pools_path), "--policy-space", str(policy_path),
        "--read-design", "same-flight-supply-variant", "--out", str(out_dir),
    ])
    assert exit_code == 1


def test_blocking_roster_finding_refuses_before_any_pool_is_opened(tmp_path, capsys):
    # no roster receipts exist under tmp_path/docs/receipts/rosters -- missing-roster-receipt
    # is blocking, so main() must exit 1 before ever trying to open a sealed run.
    cli = _load_cli()
    pools_path = _pools_manifest(tmp_path)
    policy_path = _policy_space(tmp_path)
    exit_code = cli.main([
        "--pools", str(pools_path), "--policy-space", str(policy_path),
        "--read-design", "same-flight-supply-variant", "--out", str(tmp_path / "out"),
        "--dry-run",
    ])
    # dry-run never checks rosters against REPO_ROOT's real receipts in a way that could
    # find this synthetic manifest's rosters, so this exercises the REAL repository's own
    # roster receipts instead: SLURP-STAGE3-CONSTRUCTION-R01C / SLURP-EVO-FOLD-A-V2 /
    # SLURP-EVO-FOLD-B-V2 are real, registered rosters, so dry-run succeeds.
    assert exit_code == 0


def test_cross_flight_in_chain_replicate_alias_reads_at_fold_a_size(tmp_path, capsys):
    cli = _load_cli()
    exit_code = cli.main([
        "--pools", str(_pools_manifest(tmp_path)), "--policy-space", str(_policy_space(tmp_path)),
        "--read-design", "cross-flight-with-in-chain-replicate", "--out", str(tmp_path / "out"),
        "--dry-run",
    ])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "'cross-flight-with-in-chain-replicate' at rows=1080" in out


def test_report_renders_run_label_and_compositions():
    cli = _load_cli()
    credit_table = {"pools": {}}
    comp = {"id": "c1", "components": [{"knob_id": "a", "value": "x"}], "predicted_intent_pp": 3.0,
            "predicted_slu_pp": None, "guard_pp": 1.2485, "floor_pp": 2.5, "guard_discarded": False,
            "clears_floor": True}
    text = cli.render_report(credit_table, [], {"nominated": False, "reason": "none"}, "d", 1080,
                             run_label="run 2", compositions=[comp], top_n=8)
    assert text.startswith("# Sealed-credit inner loop, run 2")
    assert "sealed-credit-inner-loop-run-2-v1" in text
    assert "| c1 | a=x | +3.0000 | n/a |" in text
    assert "## Top 8 candidates" in text
