"""The cell DET pair read: byte identity between two sealed passes, on synthetic bytes.

The driver is exercised end to end on a temporary data root holding two sealed
attempts of three rows: two rows whose delivered text is byte-identical across
the passes and one whose text differs. The stop stage must refuse a manifest
whose split identity does not match the roster, and must refuse an outputs row
whose text does not re-hash to its recorded digest. Nothing here touches the
real data root, and no text is printed.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash

REPO_ROOT = Path(__file__).resolve().parents[2]
DRIVER = REPO_ROOT / "scripts" / "analysis" / "slurp_det_pair_read.py"

IDS = ("slurp:train:000001:audio-1", "slurp:train:000002:audio-2", "slurp:train:000003:audio-3")
TEXTS_A = ("intent: alarm_set\nentities: none", "intent: iot_hue_lightoff\nentities: none", "draft one")
TEXTS_B = ("intent: alarm_set\nentities: none", "intent: iot_hue_lightoff\nentities: none", "draft two")


def _load_driver():
    spec = importlib.util.spec_from_file_location("slurp_det_pair_read", DRIVER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # dataclasses resolve string annotations through sys.modules[cls.__module__];
    # a module executed from a spec must be registered there first.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_roster(repo_root: Path) -> str:
    receipt = {
        "schema": "saea-roster-receipt-v1",
        "roster_id": "TEST-DET-3",
        "carrier_lock_key": "slurp",
        "split_role": "discovery",
        "roster_role": "construction",
        "items": [{"sample_id": sid, "stratum": "alarm" if i < 2 else "iot"} for i, sid in enumerate(IDS)],
        "split_identity_hash": split_identity_hash(prefixed("slurp", IDS)),
    }
    path = repo_root / "docs" / "receipts" / "rosters" / "test-det-3.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return "docs/receipts/rosters/test-det-3.json"


def _seal_arm(data_root: Path, run_id: str, attempt_id: str, texts, *, split_hash: str,
              intents=(True, True, False), slus=(1.0, 1.0, 0.5), corrupt_row: int | None = None,
              parsed=None) -> None:
    run_dir = data_root / "runs" / run_id / attempt_id
    run_dir.mkdir(parents=True)
    lines = []
    for index, (sid, text) in enumerate(zip(IDS, texts)):
        digest = _sha(text)
        if corrupt_row == index:
            digest = "0" * 64
        lines.append(json.dumps({"sample_id": sid, "text": text, "response_text_sha256": digest}))
    (run_dir / f"{run_id}.outputs.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    per_sample = []
    for index, sid in enumerate(IDS):
        row = {"sample_id": sid, "slu_f1_f1": slus[index], "scenario_action_exact": intents[index]}
        if parsed is not None:
            row["parsed"] = parsed[index]
        per_sample.append(row)
    scores = {"slurp-slu-official-train": {"per_sample": per_sample, "aggregate": {}}}
    scores_path = run_dir / f"{run_id}.scores.json"
    scores_path.write_text(json.dumps(scores) + "\n", encoding="utf-8")
    manifest = {
        "status": "COMPLETED",
        "study_commit": "deadbeef",
        "study_repo_dirt": [],
        "split": {"identity_hash": split_hash, "role": "discovery", "count": len(IDS)},
        "scores": {"path": scores_path.name, "sha256": hashlib.sha256(scores_path.read_bytes()).hexdigest()},
        "serving_session_id": "serving-test-np1",
    }
    (run_dir / f"{run_id}.run-manifest.json").write_text(json.dumps(manifest) + "\n", encoding="utf-8")
    attempts = data_root / "attempts" / run_id
    attempts.mkdir(parents=True)
    (attempts / f"{attempt_id}.json").write_text(json.dumps({"state": "FINALIZED"}) + "\n", encoding="utf-8")
    # the sealed dispatch window and cost block the throughput numbers come from:
    # 15 contacts in 120 s -> 7.5 contacts per minute; 24,000 prompt tokens -> 200 tok/s
    receipts = {
        "run_id": run_id, "attempt_id": attempt_id,
        "stages": {
            "serve": {"stage": "serve", "session_id": "serving-test-np1"},
            "run_phases": {
                "stage": "run_phases", "wall_seconds": 120.0,
                "contact_window": {"from": 1000.0, "to": 1120.0}, "contact_count": 15,
                "contacts_per_second": 0.125, "serving_slots": 1, "occupancy_slots": 1,
            },
        },
    }
    (run_dir / "flight-receipts.json").write_text(json.dumps(receipts) + "\n", encoding="utf-8")
    generation = {"cost": {"calls_used": 15, "prompt_tokens_total": 24000,
                           "completion_tokens_total": 900, "audio_seconds_used": 30.0}}
    (run_dir / f"{run_id}.generation-manifest.json").write_text(
        json.dumps(generation) + "\n", encoding="utf-8"
    )


PARSED_A = (
    {"scenario": "alarm", "action": "set", "entities": []},
    {"scenario": "iot", "action": "hue_lightoff", "entities": [{"type": "house_place", "filler": "kitchen"}]},
    {"scenario": "iot", "action": "hue_lightoff", "entities": []},
)
PARSED_B = (
    {"scenario": "alarm", "action": "set", "entities": []},
    {"scenario": "iot", "action": "hue_lightoff", "entities": [{"type": "house_place", "filler": "kitchen"}]},
    {"scenario": "iot", "action": "hue_lighton", "entities": [{"type": "house_place", "filler": "bedroom"}]},
)


def _args(repo_root: Path, data_root: Path, roster: str, analysis_root: Path, **extra) -> list[str]:
    argv = [
        "--stage", "all",
        "--left-run", "RUN-A", "--left-attempt", "attempt-a",
        "--right-run", "RUN-B", "--right-attempt", "attempt-b",
        "--roster", roster, "--repo-root", str(repo_root), "--data-root", str(data_root),
        "--analysis-root", str(analysis_root), "--draws", "200",
    ]
    for key, value in extra.items():
        argv.extend([f"--{key.replace('_', '-')}", str(value)])
    return argv


def test_two_of_three_rows_repeat_and_the_third_flips(tmp_path: Path, capsys) -> None:
    driver = _load_driver()
    repo_root, data_root = tmp_path / "repo", tmp_path / "data"
    repo_root.mkdir()
    roster = _write_roster(repo_root)
    split_hash = split_identity_hash(prefixed("slurp", IDS))
    _seal_arm(data_root, "RUN-A", "attempt-a", TEXTS_A, split_hash=split_hash, parsed=PARSED_A,
              intents=(True, True, False), slus=(1.0, 1.0, 0.0))
    _seal_arm(data_root, "RUN-B", "attempt-b", TEXTS_B, split_hash=split_hash, parsed=PARSED_B,
              intents=(True, True, True), slus=(1.0, 1.0, 1.0))
    analysis_root = tmp_path / "analysis"
    assert driver.main(_args(repo_root, data_root, roster, analysis_root,
                             expected_session_id="serving-test-np1")) == 0

    summary = json.loads((analysis_root / "summary.json").read_text(encoding="utf-8"))
    byte = summary["byte_identical_delivered_answer"]
    assert (byte["count"], byte["rows"], byte["all_identical"]) == (2, 3, False)
    assert byte["non_identical_sample_ids"] == [IDS[2]]
    assert summary["scored"] is True
    assert summary["intent_flip"] == {"count": 1, "denominator": 3, "share": pytest.approx(1 / 3), "unknown": 0}
    assert summary["entity_set_flip"]["count"] == 1
    assert summary["scenario_action_exact_disagreement"] == {"count": 1, "rows": 3}
    assert summary["paired_delta_slu_f1_f1"]["mean_pp"] == pytest.approx(100.0 / 3)
    assert summary["paired_delta_scenario_action_exact"]["n"] == 3
    assert summary["per_stratum"]["alarm"]["byte_identical"] == 2
    assert summary["per_stratum"]["iot"]["byte_identical"] == 0
    assert "NOT all rows repeat" in summary["routing_rule"]
    assert summary["contacts"] == {"model": 0, "tokenizer": 0, "encoder": 0, "scorer": 0, "server": 0}
    # decision 140: throughput beside determinism, from the sealed window, in one table
    throughput = summary["throughput"]
    for side in ("pass_a_np1_nocache", "pass_b_np1_nocache"):
        assert throughput[side]["contacts_per_minute"] == pytest.approx(7.5)
        assert throughput[side]["prompt_tokens_per_second"] == pytest.approx(200.0)
        assert throughput[side]["contact_count"] == 15 and throughput[side]["serving_slots"] == 1
    reference = throughput["roll_2_np4_reference"]
    assert reference["wall_seconds"] == 8558
    assert reference["contacts_per_minute"] == pytest.approx(63.07, abs=0.01)
    assert reference["prompt_tokens_per_second"] == pytest.approx(9515.8, abs=0.1)
    assert [row["contacts_per_minute"] for row in throughput["table"]] == pytest.approx([7.5, 7.5, 63.07], abs=0.01)
    assert "determinism question and INFORMS a throughput one" in throughput["decision_140"]

    per_row = json.loads((analysis_root / "per_row.json").read_text(encoding="utf-8"))
    assert [r["byte_identical"] for r in per_row["rows"]] == [True, True, False]
    # No delivered text anywhere in the persisted files or on stdout.
    persisted = "".join(p.read_text(encoding="utf-8") for p in analysis_root.iterdir())
    printed = capsys.readouterr().out
    for text in (*TEXTS_A, *TEXTS_B):
        assert text not in persisted and text not in printed


def test_all_rows_identical_routes_to_the_two_hundred_row_re_estimate(tmp_path: Path, capsys) -> None:
    driver = _load_driver()
    repo_root, data_root = tmp_path / "repo", tmp_path / "data"
    repo_root.mkdir()
    roster = _write_roster(repo_root)
    split_hash = split_identity_hash(prefixed("slurp", IDS))
    _seal_arm(data_root, "RUN-A", "attempt-a", TEXTS_A, split_hash=split_hash)
    _seal_arm(data_root, "RUN-B", "attempt-b", TEXTS_A, split_hash=split_hash)
    analysis_root = tmp_path / "analysis"
    assert driver.main(_args(repo_root, data_root, roster, analysis_root)) == 0
    summary = json.loads((analysis_root / "summary.json").read_text(encoding="utf-8"))
    assert summary["byte_identical_delivered_answer"]["all_identical"] is True
    assert "ALL rows repeat" in summary["routing_rule"]
    # parsed absent -> the flip shares are unknown, never guessed
    assert summary["intent_flip"]["unknown"] == 3
    capsys.readouterr()


def test_stop_refuses_a_manifest_bound_to_another_split(tmp_path: Path) -> None:
    driver = _load_driver()
    repo_root, data_root = tmp_path / "repo", tmp_path / "data"
    repo_root.mkdir()
    roster = _write_roster(repo_root)
    split_hash = split_identity_hash(prefixed("slurp", IDS))
    _seal_arm(data_root, "RUN-A", "attempt-a", TEXTS_A, split_hash=split_hash)
    _seal_arm(data_root, "RUN-B", "attempt-b", TEXTS_A, split_hash="f" * 64)
    with pytest.raises(driver.StopStageError, match="split identity_hash"):
        driver.main(_args(repo_root, data_root, roster, tmp_path / "analysis"))


def test_stop_refuses_a_row_whose_text_does_not_rehash(tmp_path: Path) -> None:
    driver = _load_driver()
    repo_root, data_root = tmp_path / "repo", tmp_path / "data"
    repo_root.mkdir()
    roster = _write_roster(repo_root)
    split_hash = split_identity_hash(prefixed("slurp", IDS))
    _seal_arm(data_root, "RUN-A", "attempt-a", TEXTS_A, split_hash=split_hash, corrupt_row=1)
    _seal_arm(data_root, "RUN-B", "attempt-b", TEXTS_A, split_hash=split_hash)
    with pytest.raises(driver.StopStageError, match="re-hash"):
        driver.main(_args(repo_root, data_root, roster, tmp_path / "analysis"))
