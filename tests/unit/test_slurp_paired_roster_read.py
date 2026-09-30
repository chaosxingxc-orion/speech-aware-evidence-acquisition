"""Tests for the cell B6 reusable READ DRIVER (owner decision 58).

Everything here runs against SYNTHETIC fixtures under ``tmp_path`` -- a small twelve-row roster
with two utterance clusters carrying two recordings each and three scenarios, and matching
two-arm sealed-run directory trees built by hand in the shape ``load_arm`` expects. No real
``SPEECHRL_DATA_DIR`` byte is ever read by this file, and the driver itself is never pointed at
the real data root.
"""

from __future__ import annotations

import dataclasses
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DRIVER_PATH = REPO_ROOT / "scripts" / "analysis" / "slurp_paired_roster_read.py"

# Import the driver as a top-level module (not via a dotted package path) so its own dataclasses
# resolve normally -- register it in sys.modules before exec, exactly as a bare `python
# path/to/driver.py` run would leave it registered as `__main__`.
_SPEC = importlib.util.spec_from_file_location("slurp_paired_roster_read", DRIVER_PATH)
drv = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = drv
_SPEC.loader.exec_module(drv)


SENTINEL_TEXT = "THE-QUICK-BROWN-FOX-SENTINEL-8f2c1e"

CARRIER = "slurp"


# --------------------------------------------------------------------------
# Fixture construction
# --------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


#: Twelve rows over ten utterances: u1 and u2 are DOUBLED (headset + far-field recording of the
#: same utterance, 2 rows each), u3..u10 carry one recording each -- 2*2 + 8*1 = 12 rows total.
#: Scenario is deliberately NOT put in the roster items -- the roster genuinely withholds it,
#: exactly like the real DEV-2000-ADDED roster; the aggregate-only scenario_allocation below
#: carries three scenario names, matching what a real roster's design-level block looks like.
def _build_roster_items() -> list[dict]:
    specs = [
        # (utterance_id, sample suffixes, headset flags)
        ("u1", ["a", "b"], [True, False]),
        ("u2", ["a", "b"], [True, False]),
        ("u3", ["a"], [True]),
        ("u4", ["a"], [False]),
        ("u5", ["a"], [True]),
        ("u6", ["a"], [False]),
        ("u7", ["a"], [True]),
        ("u8", ["a"], [False]),
        ("u9", ["a"], [True]),
        ("u10", ["a"], [False]),
    ]
    items = []
    for utterance, suffixes, headsets in specs:
        for suffix, headset in zip(suffixes, headsets):
            sample_id = f"{CARRIER}:devel:{utterance}:audio-{suffix}"
            items.append(
                {
                    "audio_seconds": 1.5,
                    "headset": headset,
                    "id": sample_id,
                    "key": f"{CARRIER}:{CARRIER}:devel:{utterance}:audio-{suffix}",
                    "sample_id": sample_id,
                    "utterance_id": f"{CARRIER}:devel:{utterance}",
                }
            )
    return items


def _make_roster(tmp_path: Path) -> tuple[Path, list[str]]:
    items = _build_roster_items()
    ids = [item["id"] for item in items]
    identity_hash = drv.split_identity_hash(drv.prefixed(CARRIER, ids))
    roster = {
        "carrier_lock_key": CARRIER,
        "items": items,
        "roster_id": "unit-test-roster-v1",
        "scenario_allocation": {"calendar": 3, "email": 3, "iot": 2},
        "split_identity_hash": identity_hash,
        "split_role": "dev",
        "stratum_withheld_per_item": True,
    }
    path = tmp_path / "repo" / "docs" / "receipts" / "rosters" / "unit-test-roster-v1.json"
    _write_json(path, roster)
    return path, ids


def _per_sample_row(sample_id: str, *, correct: bool) -> dict:
    """One official-scorer per_sample row. ``correct`` toggles every exact-match flag and the
    pooled tp/fp/fn counts consistently (tp=1/fp=0/fn=0 when correct, tp=0/fp=1/fn=1 otherwise)."""

    exact = 1.0 if correct else 0.0
    tp = 1.0 if correct else 0.0
    fp = 0.0 if correct else 1.0
    fn = 0.0 if correct else 1.0
    return {
        "sample_id": sample_id,
        "parsed": True,
        "scenario_action_exact": exact,
        "scenario_exact": exact,
        "action_exact": exact,
        "slot_f1_exact_f1": exact,
        "slot_f1_exact_precision": exact,
        "slot_f1_exact_recall": exact,
        "slot_f1_exact_tp": tp,
        "slot_f1_exact_fp": fp,
        "slot_f1_exact_fn": fn,
        "slu_f1_f1": exact,
        "slu_f1_precision": exact,
        "slu_f1_recall": exact,
        "slu_f1_word_f1": exact,
        "slu_f1_word_tp": tp,
        "slu_f1_word_fp": fp,
        "slu_f1_word_fn": fn,
        "slu_f1_char_f1": exact,
        "slu_f1_char_tp": tp,
        "slu_f1_char_fp": fp,
        "slu_f1_char_fn": fn,
    }


def _official_aggregate(rows: list[dict]) -> dict:
    """Recompute the aggregate from the rows the same way the real official scorer would, so the
    stop-stage 1e-6 reproduction check passes for a HONEST fixture."""

    table = {row["sample_id"]: row for row in rows}
    ids = list(table)
    slu = drv.pooled_f1(table, ids, drv.MICRO_METRICS["slu_f1_micro"])
    span = drv.pooled_f1(table, ids, drv.MICRO_METRICS["span_f1_micro"])
    return {
        "evaluator_commit": "0" * 40,
        "identity_check": {"passed": True, "slu_f1_abs_diff": 0.0, "span_f1_abs_diff": 0.0, "tolerance": 1e-6},
        "official": {
            "action_accuracy": slu,
            "intent_accuracy": slu,
            "scenario_accuracy": slu,
            "slu_f1": slu,
            "span_f1": span,
            "raw": {},
            "command": [],
            "stdout": "",
        },
        "samples": len(ids),
        "split_id": "unit-test",
    }


def _make_arm(
    data_root: Path,
    run_id: str,
    attempt_id: str,
    *,
    ids: list[str],
    scorer_id: str,
    split_identity_hash: str,
    correct_ids: set[str],
    with_native_episode: bool,
    tool_calls: int = 0,
    calls_used: int | None = None,
    with_flight_receipts: bool = True,
) -> None:
    run_dir = data_root / "runs" / run_id / attempt_id
    run_dir.mkdir(parents=True, exist_ok=True)

    rows = [_per_sample_row(sid, correct=sid in correct_ids) for sid in ids]

    outputs_lines = []
    for sid in ids:
        row = {
            "admitted": True,
            "arm": run_id,
            "carrier_lock_key": CARRIER,
            "request_id": f"req-{sid}",
            "request_sha256": "0" * 64,
            "response_sha256": "0" * 64,
            "response_text_sha256": "0" * 64,
            "sample_id": sid,
            "text": SENTINEL_TEXT,
        }
        if with_native_episode:
            row["native_episode_receipt"] = {
                "accepted_solver_receipt": {"contacts": [], "final_contact": {}},
                "context_fit": {
                    "compacted_contacts": 0,
                    "contacts": [],
                    "policy": "compact-or-abstain",
                    "prompt_limit_tokens": 20990,
                    "schema": "saea-native-context-fit-v1",
                    "slot_tokens": 24576,
                },
                "deliver_normaliser": {
                    "applied": True,
                    "carrier_lock_key": CARRIER,
                    "changed": False,
                    "label_branch": "already-legal",
                    "normaliser_id": "saea-deliver-normalise-v3",
                },
                "planner_routes": [{"action": "ACCEPT", "revision_count": 0, "role_visit_index": 3}],
                "role_visits": [
                    {"role_id": "perception", "stage": 0, "execution_receipt": {}},
                    {"role_id": "solver", "stage": 0, "execution_receipt": {}},
                    {"role_id": "reviewer", "stage": 0, "execution_receipt": {}},
                    {"role_id": "planner", "stage": 0, "execution_receipt": {}},
                ],
            }
        outputs_lines.append(json.dumps(row))
    outputs_path = run_dir / f"{run_id}.outputs.jsonl"
    outputs_path.write_text("\n".join(outputs_lines) + "\n", encoding="utf-8", newline="\n")

    scores_doc = {
        "cost": {"aggregate": {}, "per_sample": []},
        scorer_id: {"aggregate": _official_aggregate(rows), "per_sample": rows},
    }
    scores_path = run_dir / f"{run_id}.scores.json"
    _write_json(scores_path, scores_doc)

    generation_manifest = {
        "cost": {
            "audio_seconds_used": 10.0 * len(ids),
            "calls_used": calls_used if calls_used is not None else len(ids),
            "completion_tokens_total": 100 * len(ids),
            "latency_seconds_total": 1.0 * len(ids),
            "prompt_tokens_total": 1000 * len(ids),
            "tool_calls": tool_calls,
        },
    }
    _write_json(run_dir / f"{run_id}.generation-manifest.json", generation_manifest)

    manifest = {
        "status": "COMPLETED",
        "scores": {"path": str(scores_path), "sha256": _sha256_file(scores_path)},
        "split": {
            "carrier_lock_key": CARRIER,
            "count": len(ids),
            "identity_hash": split_identity_hash,
            "name": "UNIT-TEST-ROSTER",
            "role": "dev",
        },
        "study_repo_dirt": [],
    }
    _write_json(run_dir / f"{run_id}.run-manifest.json", manifest)

    score_jobs_path = run_dir / "score-jobs.jsonl"
    score_jobs_path.write_text(
        json.dumps({"job_id": attempt_id, "manifest": str(run_dir / f"{run_id}.run-manifest.json")})
        + "\n",
        encoding="utf-8",
        newline="\n",
    )

    if with_flight_receipts:
        flight_receipts = {
            "attempt_id": attempt_id,
            "receipts_hash": "0" * 64,
            "run_id": run_id,
            "schema": "saea-flight-receipts-v1",
            "stages": {
                "seal": {
                    "serving_monitor_summary": {
                        "active_seconds": 36.0,
                        "mean_utilization_percent": 55.0,
                        "wall_seconds": 40.0,
                    },
                },
                "run_phases": {"wall_seconds": 40.0, "contacts_per_second": 1.0},
            },
        }
        _write_json(run_dir / "flight-receipts.json", flight_receipts)

    attempts_dir = data_root / "attempts" / run_id
    attempts_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        attempts_dir / f"{attempt_id}.json",
        {
            "actual": {
                "audio_seconds": generation_manifest["cost"]["audio_seconds_used"],
                "calls": generation_manifest["cost"]["calls_used"],
            },
            "attempt_id": attempt_id,
            "carrier_lock_key": CARRIER,
            "run_id": run_id,
            "schema": "saea-attempt-v1",
            "state": "FINALIZED",
        },
    )


@pytest.fixture
def world(tmp_path: Path):
    roster_path, ids = _make_roster(tmp_path)
    repo_root = roster_path.parents[3]  # tmp_path / repo
    data_root = tmp_path / "data"

    roster_doc = json.loads(roster_path.read_text(encoding="utf-8"))
    split_hash = roster_doc["split_identity_hash"]

    # The left (direct) arm gets everything correct on 8/12 rows; the right (plan) arm gets 10/12,
    # a real but modest gain, so saves > harms and the bootstrap/McNemar machinery has signal.
    left_correct = set(ids[:8])
    right_correct = set(ids[:10])

    _make_arm(
        data_root,
        "UNIT-DIRECT-V1",
        "attempt-direct-v1",
        ids=ids,
        scorer_id="slurp-slu-official",
        split_identity_hash=split_hash,
        correct_ids=left_correct,
        with_native_episode=False,
    )
    _make_arm(
        data_root,
        "UNIT-PLAN-V1",
        "attempt-plan-v1",
        ids=ids,
        scorer_id="slurp-slu-official",
        split_identity_hash=split_hash,
        correct_ids=right_correct,
        with_native_episode=True,
    )

    args = drv.Args(
        stage="all",
        left=drv.ArmSpec("direct", "UNIT-DIRECT-V1", "attempt-direct-v1"),
        right=drv.ArmSpec("plan", "UNIT-PLAN-V1", "attempt-plan-v1"),
        scorer_id="slurp-slu-official",
        roster_relpath="docs/receipts/rosters/unit-test-roster-v1.json",
        cluster_key="utterance_id",
        analysis_root=tmp_path / "analysis" / "UNIT-B6-V1",
        repo_root=repo_root,
        data_root=data_root,
        seed=20260915,
        draws=200,
        recipe_id="unit-test-recipe-v1",
        title="unit test B6 read",
        split_identity_hash=None,
    )
    return {
        "tmp_path": tmp_path,
        "roster_path": roster_path,
        "ids": ids,
        "split_hash": split_hash,
        "data_root": data_root,
        "repo_root": repo_root,
        "args": args,
    }


def _scan_for_sentinel(root: Path) -> list[Path]:
    hits = []
    for path in root.rglob("*"):
        if path.is_file():
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if SENTINEL_TEXT in text:
                hits.append(path)
    return hits


# --------------------------------------------------------------------------
# stop stage
# --------------------------------------------------------------------------


def test_stop_stage_passes_and_writes_stop_json(world):
    args = world["args"]
    left = drv.load_arm(args.data_root, args.left)
    right = drv.load_arm(args.data_root, args.right)
    roster = drv.load_roster(args.repo_root, args.roster_relpath, args.cluster_key)
    payload = drv.stage_stop(args, left, right, roster)
    assert payload["status"] == "PASSED"
    assert (args.analysis_root / "stop.json").exists()
    for zero_contacts in payload["contacts"].values():
        assert zero_contacts == 0


def test_stop_stage_refuses_a_roster_mismatch(world, tmp_path):
    args = world["args"]
    # Build a roster that differs by one id from what the sealed arms actually cover.
    items = _build_roster_items()
    items[0]["id"] = items[0]["sample_id"] = "slurp:devel:bogus:audio-z"
    bad_ids = [item["id"] for item in items]
    bad_hash = drv.split_identity_hash(drv.prefixed(CARRIER, bad_ids))
    bad_roster = {
        "carrier_lock_key": CARRIER,
        "items": items,
        "split_identity_hash": bad_hash,
        "split_role": "dev",
        "stratum_withheld_per_item": True,
    }
    bad_path = world["repo_root"] / "docs" / "receipts" / "rosters" / "bad-roster-v1.json"
    _write_json(bad_path, bad_roster)

    left = drv.load_arm(args.data_root, args.left)
    right = drv.load_arm(args.data_root, args.right)
    roster = drv.load_roster(args.repo_root, "docs/receipts/rosters/bad-roster-v1.json", args.cluster_key)

    with pytest.raises(drv.StopStageError):
        drv.stage_stop(args, left, right, roster)
    assert not (args.analysis_root / "stop.json").exists()


def test_stop_stage_refuses_an_aggregate_that_does_not_reproduce(world):
    args = world["args"]
    # Corrupt the sealed scores.json of the left arm: flip the published slu_f1 without touching
    # per_sample, so the recomputation and the published number disagree.
    scores_path = args.data_root / "runs" / "UNIT-DIRECT-V1" / "attempt-direct-v1" / "UNIT-DIRECT-V1.scores.json"
    doc = json.loads(scores_path.read_text(encoding="utf-8"))
    doc["slurp-slu-official"]["aggregate"]["official"]["slu_f1"] = 0.999999
    scores_path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    # The manifest's pinned sha256 must now be stale for the corrupted bytes -- refresh the pin so
    # the aggregate-reproduction check (not the byte-pin check) is what actually fires.
    manifest_path = args.data_root / "runs" / "UNIT-DIRECT-V1" / "attempt-direct-v1" / "UNIT-DIRECT-V1.run-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["scores"]["sha256"] = _sha256_file(scores_path)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")

    left = drv.load_arm(args.data_root, args.left)
    right = drv.load_arm(args.data_root, args.right)
    roster = drv.load_roster(args.repo_root, args.roster_relpath, args.cluster_key)

    with pytest.raises(drv.StopStageError, match="does not reproduce"):
        drv.stage_stop(args, left, right, roster)
    assert not (args.analysis_root / "stop.json").exists()


# --------------------------------------------------------------------------
# structural stage
# --------------------------------------------------------------------------


def test_structural_stage_counts(world):
    args = world["args"]
    left = drv.load_arm(args.data_root, args.left)
    right = drv.load_arm(args.data_root, args.right)
    payload = drv.stage_structural(args, left, right)
    assert payload["left"]["rows"] == len(world["ids"])
    assert payload["right"]["rows"] == len(world["ids"])
    assert payload["left"]["has_native_episode_receipt"] is False
    assert payload["right"]["has_native_episode_receipt"] is True
    assert payload["right"]["planner_action_histogram"] == {"ACCEPT": len(world["ids"])}
    assert payload["left"]["tool_calls_zero"] is True
    assert payload["right"]["tool_calls_zero"] is True


# --------------------------------------------------------------------------
# contrast stage
# --------------------------------------------------------------------------


def test_pooled_micro_f1_equals_the_aggregate(world):
    args = world["args"]
    left = drv.load_arm(args.data_root, args.left)
    right = drv.load_arm(args.data_root, args.right)
    roster = drv.load_roster(args.repo_root, args.roster_relpath, args.cluster_key)
    contrast, _ = drv.stage_contrast(args, left, right, roster)

    left_rows = drv._rows_table(left, args.scorer_id)
    right_rows = drv._rows_table(right, args.scorer_id)
    left_official = left.scores[args.scorer_id]["aggregate"]["official"]["slu_f1"]
    right_official = right.scores[args.scorer_id]["aggregate"]["official"]["slu_f1"]

    recomputed_left = drv.pooled_f1(left_rows, roster.ids, drv.MICRO_METRICS["slu_f1_micro"])
    recomputed_right = drv.pooled_f1(right_rows, roster.ids, drv.MICRO_METRICS["slu_f1_micro"])

    assert recomputed_left == pytest.approx(left_official, abs=1e-9)
    assert recomputed_right == pytest.approx(right_official, abs=1e-9)

    entry = contrast["pooled_micro"]["slu_f1_micro"]
    assert entry["left_pct"] == pytest.approx(100 * left_official, abs=1e-6)
    assert entry["right_pct"] == pytest.approx(100 * right_official, abs=1e-6)


def test_bootstrap_is_deterministic_under_the_seed(world):
    args = world["args"]
    left = drv.load_arm(args.data_root, args.left)
    right = drv.load_arm(args.data_root, args.right)
    roster = drv.load_roster(args.repo_root, args.roster_relpath, args.cluster_key)

    contrast_a, _ = drv.stage_contrast(args, left, right, roster)
    contrast_b, _ = drv.stage_contrast(args, left, right, roster)

    ci_a = contrast_a["pooled_micro"]["slu_f1_micro"]["cluster_bootstrap"]["ci95_pp"]
    ci_b = contrast_b["pooled_micro"]["slu_f1_micro"]["cluster_bootstrap"]["ci95_pp"]
    assert ci_a == ci_b

    per_row_a = contrast_a["per_row"]["scenario_action_exact"]["cluster_bootstrap"]["ci95_pp"]
    per_row_b = contrast_b["per_row"]["scenario_action_exact"]["cluster_bootstrap"]["ci95_pp"]
    assert per_row_a == per_row_b


def test_per_scenario_is_reported_not_available(world):
    args = world["args"]
    left = drv.load_arm(args.data_root, args.left)
    right = drv.load_arm(args.data_root, args.right)
    roster = drv.load_roster(args.repo_root, args.roster_relpath, args.cluster_key)
    _, per_scenario = drv.stage_contrast(args, left, right, roster)
    assert per_scenario["natural_mixture"]["status"] == "NOT_AVAILABLE"
    assert per_scenario["equal_scenario_weighting"]["status"] == "NOT_AVAILABLE"
    assert "scenario" in per_scenario["natural_mixture"]["reason"].lower()


def test_per_channel_table_splits_headset_and_far_field(world):
    args = world["args"]
    left = drv.load_arm(args.data_root, args.left)
    right = drv.load_arm(args.data_root, args.right)
    roster = drv.load_roster(args.repo_root, args.roster_relpath, args.cluster_key)
    contrast, _ = drv.stage_contrast(args, left, right, roster)
    channels = contrast["per_channel"]["scenario_action_exact"]
    assert set(channels) == {"headset", "far_field"}
    total_n = sum(row["n"] for row in channels.values())
    assert total_n == len(world["ids"])


def test_saves_harms_ties_and_mcnemar_are_present(world):
    args = world["args"]
    left = drv.load_arm(args.data_root, args.left)
    right = drv.load_arm(args.data_root, args.right)
    roster = drv.load_roster(args.repo_root, args.roster_relpath, args.cluster_key)
    contrast, _ = drv.stage_contrast(args, left, right, roster)
    entry = contrast["per_row"]["scenario_action_exact"]
    assert entry["saves"] + entry["harms"] + entry["ties"] == len(world["ids"])
    # right is correct on ids[8:10] where left was not -> exactly 2 saves, 0 harms.
    assert entry["saves"] == 2
    assert entry["harms"] == 0
    assert 0.0 <= entry["mcnemar_p"] <= 1.0


# --------------------------------------------------------------------------
# efficiency stage
# --------------------------------------------------------------------------


def test_efficiency_stage_reports_gpu_hours_and_tokens_per_row(world):
    args = world["args"]
    left = drv.load_arm(args.data_root, args.left)
    right = drv.load_arm(args.data_root, args.right)
    payload = drv.stage_efficiency(args, left, right)
    rows = len(world["ids"])
    assert payload["left"]["contacts_per_row"] == pytest.approx(1.0)
    assert payload["left"]["gpu_hours"] == pytest.approx(36.0 / 3600.0)
    assert payload["left"]["gpu_hours_per_1000_rows"] == pytest.approx(
        (36.0 / 3600.0) * 1000.0 / rows
    )
    assert payload["right"]["prompt_tokens_per_row"] == pytest.approx(1000.0)
    assert "gpu_hours" in payload["delta_right_minus_left"]


# --------------------------------------------------------------------------
# verdict stage / full pipeline
# --------------------------------------------------------------------------


def test_all_stages_end_to_end_write_every_artifact(world):
    args = world["args"]
    drv.run_stages(args)
    for name in (
        "stop.json",
        "structural.json",
        "score-contrasts.json",
        "per-scenario-tables.json",
        "efficiency.json",
        "verdict.json",
        "README.md",
    ):
        assert (args.analysis_root / name).exists(), name

    verdict = json.loads((args.analysis_root / "verdict.json").read_text(encoding="utf-8"))
    assert verdict["status"] == "DESCRIPTIVE"
    assert verdict["contacts"] == {"model": 0, "tokenizer": 0, "encoder": 0, "scorer": 0}
    assert set(verdict["artifact_sha256"]) >= {
        "stop.json", "structural.json", "score-contrasts.json",
        "per-scenario-tables.json", "efficiency.json", "README.md", "driver.py",
    }
    for name, sha in verdict["artifact_sha256"].items():
        if name == "driver.py":
            continue
        assert sha == _sha256_file(args.analysis_root / name)


def test_verdict_stage_alone_requires_earlier_artifacts(world):
    args = world["args"]
    args.analysis_root.mkdir(parents=True, exist_ok=True)
    with pytest.raises(drv.ReadDriverError):
        drv.stage_verdict(args)


def test_cli_main_runs_all_stages(world):
    args = world["args"]
    rc = drv.main(
        [
            "--stage", "all",
            "--left-run", args.left.run_id,
            "--left-attempt", args.left.attempt_id,
            "--left-label", args.left.label,
            "--right-run", args.right.run_id,
            "--right-attempt", args.right.attempt_id,
            "--right-label", args.right.label,
            "--scorer-id", args.scorer_id,
            "--roster", args.roster_relpath,
            "--cluster-key", args.cluster_key,
            "--analysis-root", str(args.analysis_root),
            "--repo-root", str(args.repo_root),
            "--data-root", str(args.data_root),
            "--seed", str(args.seed),
            "--draws", str(args.draws),
        ]
    )
    assert rc == 0
    assert (args.analysis_root / "verdict.json").exists()


def test_cli_main_refuses_nonzero_on_stop_failure(world, tmp_path):
    args = world["args"]
    # A roster with a wrong id count refuses at the stop stage via the CLI path too.
    bad_roster = {
        "carrier_lock_key": CARRIER,
        "items": [_build_roster_items()[0]],
        "split_identity_hash": "0" * 64,
        "split_role": "dev",
        "stratum_withheld_per_item": True,
    }
    bad_path = world["repo_root"] / "docs" / "receipts" / "rosters" / "tiny-roster-v1.json"
    _write_json(bad_path, bad_roster)
    rc = drv.main(
        [
            "--stage", "stop",
            "--left-run", args.left.run_id,
            "--left-attempt", args.left.attempt_id,
            "--right-run", args.right.run_id,
            "--right-attempt", args.right.attempt_id,
            "--scorer-id", args.scorer_id,
            "--roster", "docs/receipts/rosters/tiny-roster-v1.json",
            "--analysis-root", str(args.analysis_root),
            "--repo-root", str(args.repo_root),
            "--data-root", str(args.data_root),
        ]
    )
    assert rc == 1


# --------------------------------------------------------------------------
# No text ever written
# --------------------------------------------------------------------------


def test_no_artifact_ever_carries_the_sentinel_text(world):
    args = world["args"]
    drv.run_stages(args)
    hits = _scan_for_sentinel(args.analysis_root)
    assert hits == [], f"sentinel text leaked into: {hits}"


def test_structural_stage_never_carries_the_sentinel_either(world):
    args = world["args"]
    left = drv.load_arm(args.data_root, args.left)
    right = drv.load_arm(args.data_root, args.right)
    drv.stage_structural(args, left, right)
    hits = _scan_for_sentinel(args.analysis_root)
    assert hits == []

# --------------------------------------------------------------------------
# TRAIN construction roster support (synthetic; never opens real VAR-1 data)
# --------------------------------------------------------------------------

def _as_train_world(world):
    from dataclasses import replace
    args = world["args"]
    doc = json.loads(world["roster_path"].read_text(encoding="utf-8"))
    doc["split_role"] = "discovery"
    for item in doc["items"]:
        for field in ("id", "sample_id", "key", "utterance_id"):
            item[field] = item[field].replace(":devel:", ":train:")
    world["ids"] = [item["sample_id"] for item in doc["items"]]
    world["split_hash"] = drv.split_identity_hash(drv.prefixed(CARRIER, world["ids"]))
    doc["split_identity_hash"] = world["split_hash"]
    _write_json(world["roster_path"], doc)
    for spec, correct in ((args.left, set(world["ids"][:8])),
                          (args.right, set(world["ids"][:10]))):
        _make_arm(
            args.data_root, spec.run_id, spec.attempt_id,
            ids=world["ids"], scorer_id="slurp-slu-official-train",
            split_identity_hash=world["split_hash"], correct_ids=correct,
            with_native_episode=(spec == args.right),
        )
        manifest_path = args.data_root / "runs" / spec.run_id / spec.attempt_id / f"{spec.run_id}.run-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["split"]["role"] = "discovery"
        _write_json(manifest_path, manifest)
    return replace(args, scorer_id="slurp-slu-official-train", expected_split_role="discovery")


def test_train_construction_roster_passes_with_explicit_role_and_train_scorer(world):
    args = _as_train_world(world)
    roster = drv.load_roster(args.repo_root, args.roster_relpath, args.cluster_key)
    left, right = (drv.load_arm(args.data_root, spec) for spec in (args.left, args.right))
    stop = drv.stage_stop(args, left, right, roster)
    assert stop["status"] == "PASSED"
    assert stop["roster"]["split_role"] == "discovery"


def test_train_roster_refuses_default_dev_and_wrong_scorer(world):
    args = _as_train_world(world)
    roster = drv.load_roster(args.repo_root, args.roster_relpath, args.cluster_key)
    left, right = (drv.load_arm(args.data_root, spec) for spec in (args.left, args.right))
    from dataclasses import replace
    with pytest.raises(drv.StopStageError, match="split role"):
        drv.stage_stop(replace(args, expected_split_role="dev"), left, right, roster)
    with pytest.raises(drv.StopStageError, match="scorer"):
        drv.stage_stop(replace(args, scorer_id="slurp-slu-official"), left, right, roster)


@pytest.mark.parametrize("forbidden", ["test", "confirmatory"])
def test_cli_rejects_forbidden_split_roles(forbidden, world):
    args = world["args"]
    with pytest.raises(SystemExit):
        drv.parse_args([
            "--left-run", args.left.run_id, "--left-attempt", args.left.attempt_id,
            "--right-run", args.right.run_id, "--right-attempt", args.right.attempt_id,
            "--analysis-root", str(args.analysis_root), "--data-root", str(args.data_root),
            "--expected-split-role", forbidden,
        ])


def test_final_report_role_parses_but_requires_the_test_scorer(world):
    # 2026-09-29 milestone fix: "final-report" is an accepted CLI role (run_package gates it
    # further), but this driver's own stage_stop refuses it under any scorer but the TEST one.
    from dataclasses import replace
    args = world["args"]
    parsed = drv.parse_args([
        "--left-run", args.left.run_id, "--left-attempt", args.left.attempt_id,
        "--right-run", args.right.run_id, "--right-attempt", args.right.attempt_id,
        "--analysis-root", str(args.analysis_root), "--data-root", str(args.data_root),
        "--expected-split-role", "final-report",
    ])
    assert parsed.expected_split_role == "final-report"
    roster = drv.load_roster(args.repo_root, args.roster_relpath, args.cluster_key)
    roster = replace(roster, document={**roster.document, "split_role": "final-report"})
    left, right = (drv.load_arm(args.data_root, spec) for spec in (args.left, args.right))
    for scorer in ("slurp-slu-official", "slurp-slu-official-train"):
        with pytest.raises(drv.StopStageError, match="TEST official scorer"):
            drv.stage_stop(
                replace(args, expected_split_role="final-report", scorer_id=scorer),
                left, right, roster,
            )
    assert not (args.analysis_root / "stop.json").exists()

def test_train_full_read_uses_construction_language(world):
    args = _as_train_world(world)
    drv.run_stages(args)
    stop = json.loads((args.analysis_root / "stop.json").read_text(encoding="utf-8"))
    verdict = json.loads((args.analysis_root / "verdict.json").read_text(encoding="utf-8"))
    readme = (args.analysis_root / "README.md").read_text(encoding="utf-8")
    scenario = json.loads((args.analysis_root / "per-scenario-tables.json").read_text(encoding="utf-8"))
    assert stop["roster"]["split_role"] == "discovery"
    assert verdict["status"] == "DESCRIPTIVE"
    assert "TRAIN construction" in readme
    assert "DEV-2000-ADDED" not in readme
    assert "TRAIN construction" in scenario["natural_mixture"]["reason"]
    contrast = json.loads((args.analysis_root / "score-contrasts.json").read_text(encoding="utf-8"))
    assert contrast["sign_convention"].startswith("delta = right(")
    assert "right variant" in contrast["sign_convention"]


# --------------------------------------------------------------------------
# owner decision 172, docs/superpowers/specs/2026-09-27-same-flight-supply-variant-instrument-
# design.md section 3: the column source, AT4 same-parent refusal, Q4 row resampling with the
# utterance-level number reported beside (never gating), and AT5's nominated claim ceiling.
# --------------------------------------------------------------------------


def _make_column_score(
    data_root: Path,
    run_id: str,
    attempt_id: str,
    *,
    column: str,
    scorer_id: str,
    rows: list[dict],
) -> Path:
    """A derived per-arm column score plus its receipt, in the shape
    ``core.scoring_batch.score_complete_derived_copy`` writes (result file + ``.receipt.json``),
    under the arm's OWN sealed run directory (``load_arm.SUPPLY_VARIANT_COLUMN_DIR``).
    ``parent_manifest_sha256`` is the ACTUAL hash of that run's own sealed manifest (exactly what
    the real derived-score receipt binds), never an arbitrary placeholder, because ``load_arm``
    verifies the receipt's claim against the manifest bytes actually sitting in this directory."""

    run_dir = data_root / "runs" / run_id / attempt_id
    manifest_path = run_dir / f"{run_id}.run-manifest.json"
    scores_path = run_dir / drv.SUPPLY_VARIANT_COLUMN_DIR / f"arm-{column}-{scorer_id}-scores.json"
    _write_json(scores_path, {scorer_id: {"aggregate": _official_aggregate(rows), "per_sample": rows}})
    receipt_path = scores_path.with_name(scores_path.name + ".receipt.json")
    _write_json(receipt_path, {
        "schema": "saea-derived-complete-score-receipt-v1",
        "parent_manifest_sha256": _sha256_file(manifest_path),
        "parent_run_id": run_id,
        "parent_attempt_id": attempt_id,
        "scorer_id": scorer_id,
        "column_binding": {"arm": column},
    })
    return scores_path


def test_load_arm_reads_a_derived_column_score_and_binds_its_parent(world):
    rows = [_per_sample_row(sid, correct=True) for sid in world["ids"]]
    _make_column_score(
        world["data_root"], "UNIT-PLAN-V1", "attempt-plan-v1",
        column="twin", scorer_id="slurp-slu-official", rows=rows,
    )
    spec = drv.ArmSpec("twin-column", "UNIT-PLAN-V1", "attempt-plan-v1", "twin")
    arm = drv.load_arm(world["data_root"], spec, scorer_id="slurp-slu-official")
    expected_manifest_sha256 = _sha256_file(
        world["data_root"] / "runs" / "UNIT-PLAN-V1" / "attempt-plan-v1" / "UNIT-PLAN-V1.run-manifest.json"
    )
    assert arm.parent_manifest_sha256 == expected_manifest_sha256
    assert {row["sample_id"] for row in arm.scores["slurp-slu-official"]["per_sample"]} == set(world["ids"])
    # the ordinary sealed artefacts are still read from the arm's OWN sealed run directory: a
    # column is a different SCORE of the same flight, never a new run.
    assert arm.manifest["status"] == "COMPLETED"
    assert arm.rows == len(world["ids"])


def test_load_arm_column_without_a_scorer_id_is_refused(world):
    spec = drv.ArmSpec("twin-column", "UNIT-PLAN-V1", "attempt-plan-v1", "twin")
    with pytest.raises(drv.StopStageError, match="scorer id"):
        drv.load_arm(world["data_root"], spec)


def test_load_arm_column_with_no_derived_score_is_refused(world):
    spec = drv.ArmSpec("twin-column", "UNIT-PLAN-V1", "attempt-plan-v1", "never-rendered")
    with pytest.raises(drv.StopStageError, match="missing required sealed file"):
        drv.load_arm(world["data_root"], spec, scorer_id="slurp-slu-official")


def test_load_arm_column_refuses_a_receipt_naming_the_wrong_parent(world, tmp_path):
    rows = [_per_sample_row(sid, correct=True) for sid in world["ids"]]
    scores_path = _make_column_score(
        world["data_root"], "UNIT-PLAN-V1", "attempt-plan-v1",
        column="twin", scorer_id="slurp-slu-official", rows=rows,
    )
    receipt_path = scores_path.with_name(scores_path.name + ".receipt.json")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["parent_manifest_sha256"] = "0" * 64
    _write_json(receipt_path, receipt)
    spec = drv.ArmSpec("twin-column", "UNIT-PLAN-V1", "attempt-plan-v1", "twin")
    with pytest.raises(drv.StopStageError, match="parent_manifest_sha256"):
        drv.load_arm(world["data_root"], spec, scorer_id="slurp-slu-official")


def _load_two_columns_of_one_flight(world, *, left_run="UNIT-PLAN-V1", left_attempt="attempt-plan-v1",
                                     right_run="UNIT-PLAN-V1", right_attempt="attempt-plan-v1"):
    """Two column reads: a genuine same-flight pair when the run/attempt args agree (the twin and
    the delivering arm are both derived from the SAME sealed run), a cross-flight mistake
    otherwise (used to exercise AT4's refusal)."""

    rows = [_per_sample_row(sid, correct=True) for sid in world["ids"]]
    _make_column_score(world["data_root"], left_run, left_attempt,
                        column="twin", scorer_id="slurp-slu-official", rows=rows)
    _make_column_score(world["data_root"], right_run, right_attempt,
                        column="plan", scorer_id="slurp-slu-official", rows=rows)
    left = drv.load_arm(world["data_root"], drv.ArmSpec("twin", left_run, left_attempt, "twin"),
                         scorer_id="slurp-slu-official")
    right = drv.load_arm(world["data_root"], drv.ArmSpec("plan", right_run, right_attempt, "plan"),
                          scorer_id="slurp-slu-official")
    return left, right


def test_at4_column_pair_with_different_parents_is_refused(world):
    # "twin" derived from UNIT-DIRECT-V1, "plan" derived from UNIT-PLAN-V1: two DIFFERENT sealed
    # flights, exactly the cross-flight mistake AT4 exists to catch.
    left, right = _load_two_columns_of_one_flight(
        world, left_run="UNIT-DIRECT-V1", left_attempt="attempt-direct-v1",
    )
    args = dataclasses.replace(world["args"], cluster_key="sample_id")
    with pytest.raises(drv.StopStageError, match="AT4"):
        drv._assert_column_pair_invariants(left, right, args)


def test_at4_column_pair_of_the_same_flight_passes(world):
    left, right = _load_two_columns_of_one_flight(world)
    args = dataclasses.replace(world["args"], cluster_key="sample_id")
    drv._assert_column_pair_invariants(left, right, args)  # does not raise


def test_q4_column_pair_requires_the_row_cluster_key(world):
    left, right = _load_two_columns_of_one_flight(world)
    args = dataclasses.replace(world["args"], cluster_key="utterance_id")
    with pytest.raises(drv.StopStageError, match="Q4"):
        drv._assert_column_pair_invariants(left, right, args)


def test_an_ordinary_non_column_pair_is_unaffected_by_the_invariant_check(world):
    left = drv.load_arm(world["data_root"], world["args"].left)
    right = drv.load_arm(world["data_root"], world["args"].right)
    # neither arm is a column; cluster_key stays utterance_id (the world default) and no
    # parent_manifest_sha256 exists on either side -- the check is a pure no-op.
    drv._assert_column_pair_invariants(left, right, world["args"])


def test_end_to_end_column_pair_writes_nominated_claim_and_the_utterance_level_number(world):
    # a genuine same-flight read: "twin" and "plan" are both columns derived from the ONE sealed
    # UNIT-PLAN-V1 run, exactly as owner decision 172 defines the instrument.
    rows = [_per_sample_row(sid, correct=sid in set(world["ids"][:10])) for sid in world["ids"]]
    _make_column_score(world["data_root"], "UNIT-PLAN-V1", "attempt-plan-v1",
                        column="twin", scorer_id="slurp-slu-official", rows=rows)
    right_rows = [_per_sample_row(sid, correct=True) for sid in world["ids"]]
    _make_column_score(world["data_root"], "UNIT-PLAN-V1", "attempt-plan-v1",
                        column="plan", scorer_id="slurp-slu-official", rows=right_rows)
    args = dataclasses.replace(
        world["args"],
        left=drv.ArmSpec("twin", "UNIT-PLAN-V1", "attempt-plan-v1", "twin"),
        right=drv.ArmSpec("plan", "UNIT-PLAN-V1", "attempt-plan-v1", "plan"),
        cluster_key="sample_id",
        analysis_root=world["tmp_path"] / "analysis" / "COLUMN-PAIR-V1",
    )
    drv.run_stages(args)

    contrast = json.loads((args.analysis_root / "score-contrasts.json").read_text(encoding="utf-8"))
    assert contrast["cluster_key"] == "sample_id"
    reported = contrast["utterance_level_reported"]
    assert reported["cluster_key"] == "utterance_id"
    assert "never gates" in reported["note"]
    assert set(reported["per_row"]) == set(drv.PER_ROW_METRICS)
    assert reported["per_row"]["slu_f1_f1"]["n"] == len(world["ids"])
    # the row-clustered read is the one used for gating; it stays a sibling key, not replaced.
    assert "per_row" in contrast and contrast["per_row"] is not reported["per_row"]

    verdict = json.loads((args.analysis_root / "verdict.json").read_text(encoding="utf-8"))
    assert verdict["claim"] == "nominated"


def test_an_ordinary_pair_never_gets_a_claim_field_or_the_utterance_level_block(world):
    drv.run_stages(world["args"])
    contrast = json.loads((world["args"].analysis_root / "score-contrasts.json").read_text(encoding="utf-8"))
    verdict = json.loads((world["args"].analysis_root / "verdict.json").read_text(encoding="utf-8"))
    assert "utterance_level_reported" not in contrast
    assert "claim" not in verdict
