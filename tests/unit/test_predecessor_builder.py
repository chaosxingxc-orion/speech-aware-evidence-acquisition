from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.bundle.artifacts import VerifiedBundle
from speech_aware_evidence_acquisition.core.predecessor_builder import (
    CONTRACT_SCHEMA,
    build_predecessor_snapshot,
    recover_parent_rows,
    verify_parent_contract,
)
from speech_aware_evidence_acquisition.core.predecessor_snapshot import (
    PredecessorSnapshotError,
    load_predecessor_binding,
)

RUN_ID = "SAEA-E21-FRESH-DIRECT-TEST"
ATTEMPT_ID = "attempt-fresh-direct-test"
CONFIG_HASH = "a" * 64
PROTOCOL_HASH = "b" * 64
SPLIT_HASH = "c" * 64
EXPOSURE_ROW = "SAEA-E21-MF-FRESH-PREDECESSOR-TEST"


def _record(channel: str, record_id: str, payload: dict) -> dict:
    return {"channel": channel, "record_id": record_id, "payload": payload}


def _world(tmp_path: Path, *, saturated: bool = True):
    repo = tmp_path / "repo"
    data = tmp_path / "data"
    run_dir = data / "runs" / RUN_ID / ATTEMPT_ID
    receipts = repo / "docs" / "receipts"
    run_dir.mkdir(parents=True)
    receipts.mkdir(parents=True)
    (repo / "docs" / "exposure-ledger.md").write_text(
        f"| {EXPOSURE_ROW} | model-free-check |\n", encoding="utf-8"
    )

    specifications = (
        ("call-a", (("alpha", 0.0, 90.0, False, 101, 11),)),
        (
            "call-b",
            (
                ("raw runaway", 0.0, 90.0, saturated, 202, 22),
                ("omega", 90.0, 135.5, False, 303, 33),
            ),
        ),
    )
    trace_records: dict[str, dict] = {}
    trace_lines: list[dict] = []
    geometry: list[dict] = []
    outputs_rows: list[dict] = []
    total_prompt = total_completion = 0
    total_saturated = 0
    for sample_id, windows in specifications:
        request_ids = []
        delivered = []
        for index, (text, start, end, is_saturated, prompt, completion) in enumerate(
            windows, start=1
        ):
            request_id = f"{sample_id}-i{index:04d}"
            request_ids.append(request_id)
            request = _record(
                "MODEL_REQUEST",
                f"{request_id}/request",
                {
                    "arm": "speech-feature-query",
                    "payload": {
                        "sample_id": sample_id,
                        "audio_seconds": end - start,
                    },
                },
            )
            obs = _record(
                "OBS",
                f"{request_id}/obs",
                {
                    "obs_iteration": index,
                    "obs_window_start_seconds": start,
                    "obs_window_end_seconds": end,
                    "obs_saturated": is_saturated,
                },
            )
            response = _record(
                "MODEL_RESPONSE", f"{request_id}/response", {"text": text}
            )
            cost = _record(
                "COST",
                f"{request_id}/cost",
                {"prompt_tokens": prompt, "completion_tokens": completion},
            )
            for item in (request, obs, response, cost):
                trace_lines.append(item)
                trace_records[item["record_id"]] = item["payload"]
            geometry.append(
                {
                    "sample_id": sample_id,
                    "window_index": index,
                    "start_seconds": start,
                    "end_seconds": end,
                }
            )
            delivered.append("" if is_saturated else text)
            total_prompt += prompt
            total_completion += completion
            total_saturated += int(is_saturated)
        stitch_request = _record(
            "MODEL_REQUEST",
            f"{sample_id}/request",
            {"stitch": True, "stitched_request_ids": request_ids},
        )
        stitch_response = _record(
            "MODEL_RESPONSE",
            f"{sample_id}/response",
            {"stitch": True, "text": "ignored"},
        )
        for item in (stitch_request, stitch_response):
            trace_lines.append(item)
            trace_records[item["record_id"]] = item["payload"]
        outputs_rows.append({"sample_id": sample_id, "text": " ".join(filter(None, delivered))})

    trace_path = run_dir / f"{RUN_ID}.trace.jsonl"
    trace_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in trace_lines) + "\n",
        encoding="utf-8",
    )
    outputs_path = run_dir / f"{RUN_ID}.outputs.jsonl"
    outputs_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in outputs_rows) + "\n",
        encoding="utf-8",
    )
    manifest_path = run_dir / f"{RUN_ID}.run-manifest.json"
    manifest = {
        "status": "COMPLETED",
        "run_id": RUN_ID,
        "attempt": {"attempt_id": ATTEMPT_ID},
        "plan": {"carrier_lock_key": "earnings21-original"},
        "config": {"config_hash": CONFIG_HASH},
        "protocol_hash": PROTOCOL_HASH,
        "split": {"identity_hash": SPLIT_HASH},
        "raw_trace": {
            "path": str(trace_path),
            "sha256": hashlib.sha256(trace_path.read_bytes()).hexdigest(),
        },
        "outputs": {
            "path": str(outputs_path),
            "sha256": hashlib.sha256(outputs_path.read_bytes()).hexdigest(),
        },
        "cost": {
            "calls_used": len(geometry),
            "prompt_tokens_total": total_prompt,
            "completion_tokens_total": total_completion,
            "skipped_slice_count": 0,
            "saturated_slice_count": total_saturated,
        },
    }
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    bundle = VerifiedBundle(
        manifest_path=manifest_path,
        manifest=manifest,
        outputs_path=outputs_path,
        outputs_rows=tuple(outputs_rows),
        trace_records=trace_records,
        split_ids=frozenset(row["sample_id"] for row in outputs_rows),
        attempt_state="COMPLETED",
    )
    contract = {
        "schema": CONTRACT_SCHEMA,
        "run_id": RUN_ID,
        "attempt_id": ATTEMPT_ID,
        "config_hash": CONFIG_HASH,
        "protocol_hash": PROTOCOL_HASH,
        "split_identity_hash": SPLIT_HASH,
        "sample_ids": ["call-a", "call-b"],
        "window_geometry": geometry,
    }
    return {
        "repo": repo,
        "data": data,
        "run_dir": run_dir,
        "manifest_path": manifest_path,
        "trace_path": trace_path,
        "outputs_path": outputs_path,
        "bundle": bundle,
        "contract": contract,
        "receipt_path": receipts / "fresh.json",
        "total_prompt": total_prompt,
        "total_completion": total_completion,
    }


def _build(monkeypatch, world):
    import speech_aware_evidence_acquisition.core.predecessor_builder as module

    monkeypatch.setattr(module, "verify_bundle", lambda path: world["bundle"])
    monkeypatch.setattr(module, "require_clean_study_repo", lambda repo: "d" * 40)
    return build_predecessor_snapshot(
        manifest_path=world["manifest_path"],
        repo_root=world["repo"],
        data_root=world["data"],
        contract=world["contract"],
        receipt_path=world["receipt_path"],
        exposure_row=EXPOSURE_ROW,
    )


def test_fresh_parent_builds_loadable_binding_and_preserves_every_parent_byte(
    tmp_path, monkeypatch
):
    world = _world(tmp_path)
    before = {
        path: path.read_bytes()
        for path in (world["manifest_path"], world["trace_path"], world["outputs_path"])
    }

    result = _build(monkeypatch, world)

    assert result["windows"] == 3
    assert result["calls"] == 2
    receipt = json.loads(world["receipt_path"].read_text(encoding="utf-8"))
    assert receipt["run_id"] == RUN_ID
    assert receipt["attempt_id"] == ATTEMPT_ID
    assert receipt["prompt_tokens_total"] == world["total_prompt"] == 606
    assert receipt["completion_tokens_total"] == world["total_completion"] == 66
    assert receipt["saturated_windows"] == 1
    assert receipt["additional_model_contacts"] == 0
    snapshot = load_predecessor_binding(
        world["receipt_path"],
        world["data"],
        expected_receipt_sha256=result["receipt_sha256"],
    )
    assert snapshot.run_id == RUN_ID
    assert [row.text for row in snapshot.for_sample("call-b")] == ["", "omega"]
    assert [row.saturated for row in snapshot.for_sample("call-b")] == [True, False]
    assert {path: path.read_bytes() for path in before} == before


@pytest.mark.parametrize(
    ("label", "mutate", "message"),
    [
        ("status", lambda w: w["bundle"].manifest.__setitem__("status", "ABORTED"), "parent status"),
        ("run", lambda w: w["contract"].__setitem__("run_id", "foreign-run"), "run differs"),
        (
            "attempt",
            lambda w: w["contract"].__setitem__("attempt_id", "foreign-attempt"),
            "attempt differs",
        ),
        (
            "carrier",
            lambda w: w["bundle"].manifest["plan"].__setitem__(
                "carrier_lock_key", "slurp"
            ),
            "carrier differs",
        ),
        (
            "config",
            lambda w: w["contract"].__setitem__("config_hash", "f" * 64),
            "configuration differs",
        ),
        (
            "protocol",
            lambda w: w["contract"].__setitem__("protocol_hash", "e" * 64),
            "protocol differs",
        ),
        (
            "split",
            lambda w: w["contract"].__setitem__("split_identity_hash", "9" * 64),
            "split differs",
        ),
        (
            "roster",
            lambda w: w["contract"].__setitem__(
                "sample_ids", ["call-a", "foreign-call"]
            ),
            "call roster differs",
        ),
    ],
)
def test_foreign_parent_identity_is_refused(tmp_path, label, mutate, message):
    world = _world(tmp_path)
    mutate(world)
    with pytest.raises(PredecessorSnapshotError, match=message):
        verify_parent_contract(world["bundle"], world["contract"])


def test_changed_or_incomplete_window_geometry_is_refused(tmp_path):
    world = _world(tmp_path)
    world["contract"]["window_geometry"][1]["end_seconds"] = 89.5
    with pytest.raises(PredecessorSnapshotError, match="window source geometry"):
        recover_parent_rows(world["bundle"], world["contract"])

    world = _world(tmp_path / "missing")
    world["contract"]["window_geometry"].pop()
    with pytest.raises(PredecessorSnapshotError, match="window source geometry"):
        recover_parent_rows(world["bundle"], world["contract"])


def test_exact_stitch_mismatch_refuses_before_any_derivative_is_written(
    tmp_path, monkeypatch
):
    world = _world(tmp_path)
    world["bundle"] = VerifiedBundle(
        **{
            **world["bundle"].__dict__,
            "outputs_rows": (
                {"sample_id": "call-a", "text": "changed"},
                world["bundle"].outputs_rows[1],
            ),
        }
    )
    import speech_aware_evidence_acquisition.core.predecessor_builder as module

    monkeypatch.setattr(module, "verify_bundle", lambda path: world["bundle"])
    monkeypatch.setattr(module, "require_clean_study_repo", lambda repo: "d" * 40)
    with pytest.raises(Exception, match="do not rebuild the sealed hypothesis"):
        build_predecessor_snapshot(
            manifest_path=world["manifest_path"],
            repo_root=world["repo"],
            data_root=world["data"],
            contract=world["contract"],
            receipt_path=world["receipt_path"],
            exposure_row=EXPOSURE_ROW,
        )
    assert not world["receipt_path"].exists()
    assert not (
        world["data"]
        / "derived/e21-predecessor"
        / RUN_ID
        / ATTEMPT_ID
        / "window-hypotheses.json"
    ).exists()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("calls_used", 4, "generation contact count"),
        ("prompt_tokens_total", 605, "prompt_tokens total"),
        ("completion_tokens_total", 65, "completion_tokens total"),
        ("skipped_slice_count", 1, "skipped windows"),
        ("saturated_slice_count", 0, "saturation count"),
    ],
)
def test_manifest_cost_and_terminal_window_totals_must_agree(
    tmp_path, field, value, message
):
    world = _world(tmp_path)
    world["bundle"].manifest["cost"][field] = value
    with pytest.raises(PredecessorSnapshotError, match=message):
        recover_parent_rows(world["bundle"], world["contract"])


def test_missing_duplicate_or_invalid_per_window_cost_refuses(tmp_path):
    world = _world(tmp_path)
    costs = [
        key
        for key, record in world["bundle"].trace_records.items()
        if key.endswith("/cost")
    ]
    del world["bundle"].trace_records[costs[0]]
    with pytest.raises(PredecessorSnapshotError, match="lacks its original cost"):
        recover_parent_rows(world["bundle"], world["contract"])

    world = _world(tmp_path / "duplicate")
    original = next(
        record
        for key, record in world["bundle"].trace_records.items()
        if key.endswith("/cost")
    )
    world["bundle"].trace_records["duplicate/cost"] = copy.deepcopy(original)
    with pytest.raises(PredecessorSnapshotError, match="generation contact count"):
        recover_parent_rows(world["bundle"], world["contract"])

    world = _world(tmp_path / "invalid")
    original = next(
        record
        for key, record in world["bundle"].trace_records.items()
        if key.endswith("/cost")
    )
    original["prompt_tokens"] = True
    with pytest.raises(PredecessorSnapshotError, match="cost is unavailable or invalid"):
        recover_parent_rows(world["bundle"], world["contract"])


def test_existing_derivative_is_never_overwritten(tmp_path, monkeypatch):
    world = _world(tmp_path)
    world["receipt_path"].write_text("keep-me", encoding="utf-8")
    with pytest.raises(PredecessorSnapshotError, match="already exists"):
        _build(monkeypatch, world)
    assert world["receipt_path"].read_text(encoding="utf-8") == "keep-me"