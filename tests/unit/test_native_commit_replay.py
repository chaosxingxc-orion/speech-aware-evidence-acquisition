"""E2 (SLURP v2 base program M2), item 5: the offline COMMIT-policy replay CLI.

Model-free: builds a synthetic sealed ``outputs.jsonl`` (the shape
``reproduction.ojw.native_group_solver.run_grouped_solver_samples`` produces
under its ``solver_group`` custody field) and re-applies the registered
commit policy with DIFFERENT parameters, never touching the sealed file.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.native_commit_replay import (
    NativeCommitReplayError,
    main,
    replay,
)
from speech_aware_evidence_acquisition.e0.artifacts import sha256_file

POLICY = "saea-commit-plurality-support-v1"


def _sample_record(sample_index, *, scenario, action, entities=()):
    return {
        "sample_index": sample_index,
        "seed": 1000 + sample_index,
        "temperature": 0.7,
        "parse_status": "ok",
        "parsed_answer": {"scenario": scenario, "action": action, "entities": list(entities)},
        "contacts": [
            {
                "agent_contact_id": f"contact-{sample_index}",
                "request_id": f"req-{sample_index}",
                "request_sha256": "a" * 64,
                "response_sha256": "b" * 64,
                "response_text_sha256": "c" * 64,
            }
        ],
    }


def _malformed_record(sample_index):
    return {
        "sample_index": sample_index,
        "seed": 1000 + sample_index,
        "temperature": 0.7,
        "parse_status": "malformed",
        "parsed_answer": None,
        "contacts": [
            {
                "agent_contact_id": f"contact-{sample_index}",
                "request_id": f"req-{sample_index}",
                "request_sha256": "a" * 64,
                "response_sha256": "b" * 64,
                "response_text_sha256": "d" * 64,
            }
        ],
    }


def _row(sample_id, records):
    return {
        "sample_id": sample_id,
        "solver_group": {
            "commit_policy_id": POLICY,
            "samples": records,
            "delivered": {
                "intent_support": 0,
                "intent_member_sample_indices": [],
                "intent_tie_break_sample_index": None,
                "entities": [],
            },
        },
    }


def _write_sealed_outputs(path: Path) -> None:
    rows = [
        _row("row-1", [
            _sample_record(0, scenario="alarm", action="set", entities=[{"type": "time", "filler": "six am"}]),
            _sample_record(1, scenario="alarm", action="set", entities=[{"type": "time", "filler": "six a m"}]),
            _malformed_record(2),
        ]),
        _row("row-2", [
            _sample_record(0, scenario="calendar", action="query"),
            _sample_record(1, scenario="calendar", action="query"),
            _sample_record(2, scenario="calendar", action="set"),
        ]),
    ]
    text = "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def test_replay_writes_new_outputs_and_provenance_without_touching_the_seal(tmp_path):
    outputs_path = tmp_path / "outputs.jsonl"
    _write_sealed_outputs(outputs_path)
    before_bytes = outputs_path.read_bytes()
    before_sha = sha256_file(outputs_path)

    output_dir = tmp_path / "replay-min-support-2"
    provenance = replay(
        outputs_path=outputs_path,
        policy_id=POLICY,
        commit_params={"min_support": 2, "similarity_threshold": 0.6},
        output_dir=output_dir,
    )

    assert outputs_path.read_bytes() == before_bytes
    assert sha256_file(outputs_path) == before_sha

    assert provenance["model_calls"] == 0
    assert provenance["policy_id"] == POLICY
    assert provenance["parameters"] == {"min_support": 2, "similarity_threshold": 0.6}
    assert provenance["source"]["sha256"] == before_sha
    assert provenance["rows"] == 2

    replayed_text = (output_dir / "outputs.jsonl").read_text(encoding="utf-8")
    replayed_rows = [json.loads(line) for line in replayed_text.splitlines() if line.strip()]
    assert [row["sample_id"] for row in replayed_rows] == ["row-1", "row-2"]

    row1 = next(row for row in replayed_rows if row["sample_id"] == "row-1")
    payload = json.loads(row1["final_response_text"])
    # min_support 2, threshold 0.6: the "six am"/"six a m" cluster survives.
    assert payload["scenario"] == "alarm"
    assert payload["action"] == "set"
    assert payload["entities"] == [{"type": "time", "filler": "six am"}]

    row2 = next(row for row in replayed_rows if row["sample_id"] == "row-2")
    payload2 = json.loads(row2["final_response_text"])
    assert (payload2["scenario"], payload2["action"]) == ("calendar", "query")


def test_replay_refuses_to_overwrite_an_existing_output_dir(tmp_path):
    outputs_path = tmp_path / "outputs.jsonl"
    _write_sealed_outputs(outputs_path)
    output_dir = tmp_path / "replay"
    replay(
        outputs_path=outputs_path, policy_id=POLICY,
        commit_params={"min_support": 1, "similarity_threshold": 0.8},
        output_dir=output_dir,
    )
    with pytest.raises(NativeCommitReplayError, match="overwrite"):
        replay(
            outputs_path=outputs_path, policy_id=POLICY,
            commit_params={"min_support": 2, "similarity_threshold": 0.8},
            output_dir=output_dir,
        )


def test_a_different_min_support_changes_which_entities_survive(tmp_path):
    outputs_path = tmp_path / "outputs.jsonl"
    _write_sealed_outputs(outputs_path)
    output_dir = tmp_path / "replay-strict"
    replay(
        outputs_path=outputs_path, policy_id=POLICY,
        commit_params={"min_support": 3, "similarity_threshold": 0.6},
        output_dir=output_dir,
    )
    replayed_rows = [
        json.loads(line)
        for line in (output_dir / "outputs.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    row1 = next(row for row in replayed_rows if row["sample_id"] == "row-1")
    payload = json.loads(row1["final_response_text"])
    # min_support 3 with only 2 similar mentions: the entity cluster is dropped.
    assert payload["entities"] == []


def test_cli_main_runs_end_to_end(tmp_path):
    outputs_path = tmp_path / "outputs.jsonl"
    _write_sealed_outputs(outputs_path)
    output_dir = tmp_path / "cli-replay"
    exit_code = main([
        "--outputs", str(outputs_path),
        "--policy", POLICY,
        "--min-support", "2",
        "--similarity-threshold", "0.6",
        "--output-dir", str(output_dir),
    ])
    assert exit_code == 0
    assert (output_dir / "outputs.jsonl").exists()
    assert (output_dir / "provenance.json").exists()
