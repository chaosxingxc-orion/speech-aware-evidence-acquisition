"""``analysis.a2t_read``: the P-A2T Stage-1 A0 baseline pinned offline read
suite.

Engineering-only, zero live model contact -- every fixture here is a
hand-authored synthetic attempt directory built on top of the shared
``audio2tool_world`` fixture (``tests/unit/conftest.py``'s
``Audio2ToolWorld``, already used by ``test_rails_audio2tool_adapter.py``).
This module is NEVER pointed at the real flight attempt directory
(``$SPEECHRL_DATA_DIR/runs/SAEA-BASE-a2t-a0-400/``); that is a separate,
one-shot registered read.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_read import (
    A2tReadError,
    build_a2t_report,
    expected_sample_ids,
    headroom_to_json,
    is_empty_tool_call,
    main as a2t_read_main,
    report_to_json,
)
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import Audio2ToolAdapter

# ---------------------------------------------------------------------------
# Fixture-world responses.
#
# tier1_direct:000001   gold setLighting()                     -> exact match
# tier3_multi_intent:000004
#   gold [setSecurityMode(mode='Armed_Away', level=2),
#         setTargetTemperature(temperature=68.0), setColor(color='blue'),
#         calibrateThermostat()]
#   response names the SAME 4 tools (tool_accuracy == 1.0) but with a wrong
#   argument value (mode='Home') -> exact_match == 0.0: the required
#   "tool-correct-EM-wrong" row (and the Stage-2 headroom sample).
# tier7_multiturn:000009  gold setAlarm(time='06:30', repeat=['Weekdays'])
#   response "[]" -> the required empty-tool-call row.
# ---------------------------------------------------------------------------

_TIER1_ID = "tier1_direct:000001"
_TIER3_ID = "tier3_multi_intent:000004"
_TIER7_ID = "tier7_multiturn:000009"

_TIER1_RESPONSE = json.dumps([{"name": "setLighting", "arguments": {}}])
_TIER3_RESPONSE = json.dumps(
    [
        {"name": "setSecurityMode", "arguments": {"mode": "Home", "level": 2}},
        {"name": "setTargetTemperature", "arguments": {"temperature": 68.0}},
        {"name": "setColor", "arguments": {"color": "blue"}},
        {"name": "calibrateThermostat", "arguments": {}},
    ]
)
_TIER7_EMPTY_RESPONSE = "[]"


def _adapter(world) -> Audio2ToolAdapter:
    lock = load_lock(world.lock_path)
    return Audio2ToolAdapter(lock, world.data_root, repo_root=world.repo_root)


def _clean_rows(world) -> list[dict]:
    """3 rows, each scored with the REAL adapter so the embedded ``metrics``
    exactly matches what a fresh recompute will produce (zero recheck
    mismatches) -- mirroring exactly what the flight launcher itself does
    (``adapter.score`` at flight time, embedded verbatim into the row)."""

    adapter = _adapter(world)
    samples_by_id = {s.sample_id: s for s in adapter.load_split("discovery")}
    rows = []
    for sample_id, response_text in (
        (_TIER1_ID, _TIER1_RESPONSE),
        (_TIER3_ID, _TIER3_RESPONSE),
        (_TIER7_ID, _TIER7_EMPTY_RESPONSE),
    ):
        sample = samples_by_id[sample_id]
        metrics = adapter.score(sample, response_text)
        rows.append(_row("zero-supply", sample_id, response_text, dict(metrics)))
    return rows


def _row(arm: str, sample_id: str, response_text: str, metrics: dict) -> dict:
    return {
        "arm": arm,
        "sample_id": sample_id,
        "messages": [
            {"role": "system", "content": "you control tools"},
            {"role": "user", "content": [{"type": "input_audio", "media_relpath": "unused"}]},
        ],
        "response_text": response_text,
        "metrics": metrics,
        "consumption": {"records": [], "copy_rate": 0.0, "dose_realized": 0, "trace_version": "consumption-trace-v1"},
    }


def _receipt_split_identity_hash(world) -> str:
    return json.loads(world.receipt_path.read_text(encoding="utf-8"))["split_identity_hash"]


def _write_outputs_jsonl(path: Path, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write((json.dumps(row) if isinstance(row, dict) else row) + "\n")


def _write_flight_receipt(
    path: Path,
    *,
    split_identity_hash: str,
    status: str = "COMPLETED",
    arms: list | None = None,
    request_failures: list | None = None,
) -> None:
    document = {
        "status": status,
        "error": None,
        "arms": arms if arms is not None else ["zero-supply"],
        "split_identity_hash": split_identity_hash,
        "request_failures": request_failures if request_failures is not None else [],
    }
    path.write_text(json.dumps(document), encoding="utf-8")


def _build_attempt_dir(
    tmp_path: Path,
    world,
    rows: list,
    *,
    write_receipt: bool = True,
    receipt_kwargs: dict | None = None,
    name: str = "attempt",
) -> Path:
    attempt_dir = tmp_path / name
    _write_outputs_jsonl(attempt_dir / "outputs.jsonl", rows)
    if write_receipt:
        kwargs = dict(split_identity_hash=_receipt_split_identity_hash(world))
        kwargs.update(receipt_kwargs or {})
        _write_flight_receipt(attempt_dir / "flight-receipt.json", **kwargs)
    return attempt_dir


# ---------------------------------------------------------------------------
# Clean read: aggregates, gap, empty-tool-call rate, headroom, zero recheck
# mismatches, and scores that reproduce Audio2ToolAdapter.score directly.
# ---------------------------------------------------------------------------


def test_clean_read_scores_every_row_and_matches_the_frozen_gold(audio2tool_world, tmp_path):
    rows = _clean_rows(audio2tool_world)
    attempt_dir = _build_attempt_dir(tmp_path, audio2tool_world, rows)
    lock = load_lock(audio2tool_world.lock_path)

    report = build_a2t_report(
        attempt_dir, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root
    )

    assert report.flight_status == "COMPLETED"
    assert report.overall.n_samples == 3
    # tier1 exact match, tier3 tool-correct/EM-wrong, tier7 empty -> 1/3, 0/3
    assert report.overall.tool_accuracy == pytest.approx(2 / 3)
    assert report.overall.exact_match == pytest.approx(1 / 3)
    assert report.overall.gap == pytest.approx(1 / 3)
    assert report.recheck_mismatches == ()


def test_clean_read_flags_the_tool_correct_em_wrong_row_as_headroom(audio2tool_world, tmp_path):
    rows = _clean_rows(audio2tool_world)
    attempt_dir = _build_attempt_dir(tmp_path, audio2tool_world, rows)
    lock = load_lock(audio2tool_world.lock_path)

    report = build_a2t_report(
        attempt_dir, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root
    )

    assert report.headroom_ids == (_TIER3_ID,)
    tier3 = report.by_tier["tier3_multi_intent"]
    assert tier3.tool_accuracy == 1.0
    assert tier3.exact_match == 0.0
    assert tier3.gap == 1.0


def test_clean_read_flags_the_empty_tool_call_row_per_tier_and_overall(audio2tool_world, tmp_path):
    rows = _clean_rows(audio2tool_world)
    attempt_dir = _build_attempt_dir(tmp_path, audio2tool_world, rows)
    lock = load_lock(audio2tool_world.lock_path)

    report = build_a2t_report(
        attempt_dir, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root
    )

    tier7 = report.by_tier["tier7_multiturn"]
    assert tier7.empty_tool_call_count == 1
    assert tier7.empty_tool_call_rate == 1.0
    assert report.overall.empty_tool_call_count == 1
    assert report.overall.empty_tool_call_rate == pytest.approx(1 / 3)
    # every other tier has zero empty-tool-call rows
    assert report.by_tier["tier1_direct"].empty_tool_call_count == 0
    assert report.by_tier["tier3_multi_intent"].empty_tool_call_count == 0


def test_scores_reproduce_audio2tool_adapter_score_on_fixtures(audio2tool_world, tmp_path):
    """The report's own per-row numbers are not a second, drifting
    computation -- they equal exactly what calling ``Audio2ToolAdapter.score``
    on the same (sample, response) pair returns."""

    rows = _clean_rows(audio2tool_world)
    attempt_dir = _build_attempt_dir(tmp_path, audio2tool_world, rows)
    lock = load_lock(audio2tool_world.lock_path)

    report = build_a2t_report(
        attempt_dir, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root
    )

    adapter = _adapter(audio2tool_world)
    samples_by_id = {s.sample_id: s for s in adapter.load_split("discovery")}
    directly = adapter.score(samples_by_id[_TIER3_ID], _TIER3_RESPONSE)
    tier3 = report.by_tier["tier3_multi_intent"]
    assert tier3.tool_accuracy == directly["tool_accuracy"]
    assert tier3.exact_match == directly["exact_match"]


# ---------------------------------------------------------------------------
# Harness-defect refusals.
# ---------------------------------------------------------------------------


def test_malformed_row_is_a_harness_defect_refusal(audio2tool_world, tmp_path):
    rows = _clean_rows(audio2tool_world)
    broken = dict(rows[1])
    del broken["metrics"]  # required key missing -> malformed
    rows[1] = broken
    attempt_dir = _build_attempt_dir(tmp_path, audio2tool_world, rows)
    lock = load_lock(audio2tool_world.lock_path)

    with pytest.raises(A2tReadError, match="harness defect"):
        build_a2t_report(attempt_dir, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root)


def test_duplicate_sample_id_is_a_harness_defect_refusal(audio2tool_world, tmp_path):
    rows = _clean_rows(audio2tool_world)
    rows.append(dict(rows[0]))  # duplicate tier1_direct:000001 row
    attempt_dir = _build_attempt_dir(tmp_path, audio2tool_world, rows)
    lock = load_lock(audio2tool_world.lock_path)

    with pytest.raises(A2tReadError, match="duplicate sample_id"):
        build_a2t_report(attempt_dir, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root)


def test_wrong_arm_is_a_harness_defect_refusal(audio2tool_world, tmp_path):
    rows = _clean_rows(audio2tool_world)
    rows[2] = dict(rows[2], arm="supplied")
    attempt_dir = _build_attempt_dir(tmp_path, audio2tool_world, rows)
    lock = load_lock(audio2tool_world.lock_path)

    with pytest.raises(A2tReadError, match="arm other than"):
        build_a2t_report(attempt_dir, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root)


def test_missing_flight_receipt_is_a_harness_defect_refusal(audio2tool_world, tmp_path):
    rows = _clean_rows(audio2tool_world)
    attempt_dir = _build_attempt_dir(tmp_path, audio2tool_world, rows, write_receipt=False)
    lock = load_lock(audio2tool_world.lock_path)

    with pytest.raises(A2tReadError, match="flight-receipt.json missing"):
        build_a2t_report(attempt_dir, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root)


def test_non_completed_flight_receipt_is_a_harness_defect_refusal(audio2tool_world, tmp_path):
    rows = _clean_rows(audio2tool_world)
    attempt_dir = _build_attempt_dir(
        tmp_path, audio2tool_world, rows, receipt_kwargs={"status": "ABORTED"}
    )
    lock = load_lock(audio2tool_world.lock_path)

    with pytest.raises(A2tReadError, match="status='ABORTED'"):
        build_a2t_report(attempt_dir, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root)


def test_nonempty_request_failures_is_a_harness_defect_refusal(audio2tool_world, tmp_path):
    rows = _clean_rows(audio2tool_world)
    attempt_dir = _build_attempt_dir(
        tmp_path,
        audio2tool_world,
        rows,
        receipt_kwargs={"request_failures": [{"index": 3, "error": "TimeoutError"}]},
    )
    lock = load_lock(audio2tool_world.lock_path)

    with pytest.raises(A2tReadError, match="request_failures non-empty"):
        build_a2t_report(attempt_dir, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root)


def test_missing_sample_is_a_harness_defect_refusal(audio2tool_world, tmp_path):
    rows = _clean_rows(audio2tool_world)[:2]  # drop the tier7 row
    attempt_dir = _build_attempt_dir(tmp_path, audio2tool_world, rows)
    lock = load_lock(audio2tool_world.lock_path)

    with pytest.raises(A2tReadError, match="missing 1 sample"):
        build_a2t_report(attempt_dir, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root)


def test_split_identity_hash_mismatch_is_a_harness_defect_refusal(audio2tool_world, tmp_path):
    rows = _clean_rows(audio2tool_world)
    attempt_dir = _build_attempt_dir(
        tmp_path, audio2tool_world, rows, receipt_kwargs={"split_identity_hash": "f" * 64}
    )
    lock = load_lock(audio2tool_world.lock_path)

    with pytest.raises(A2tReadError, match="split_identity_hash mismatch"):
        build_a2t_report(attempt_dir, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root)


# ---------------------------------------------------------------------------
# Small unit-level checks.
# ---------------------------------------------------------------------------


def test_is_empty_tool_call_true_for_an_empty_list_response():
    assert is_empty_tool_call("[]") is True


def test_is_empty_tool_call_false_for_a_real_call():
    assert is_empty_tool_call(_TIER1_RESPONSE) is False


def test_is_empty_tool_call_true_for_unparseable_text():
    assert is_empty_tool_call("not json at all") is True


def test_expected_sample_ids_matches_the_adapters_own_load_split_derivation(audio2tool_world):
    from speech_aware_evidence_acquisition.data.audio2tool import audio2tool_receipts

    receipt = next(iter(audio2tool_receipts(audio2tool_world.repo_root).values()))
    ids = expected_sample_ids(receipt)

    adapter = _adapter(audio2tool_world)
    assert set(ids) == {s.sample_id for s in adapter.load_split("discovery")}


def test_report_to_json_and_headroom_to_json_shapes(audio2tool_world, tmp_path):
    rows = _clean_rows(audio2tool_world)
    attempt_dir = _build_attempt_dir(tmp_path, audio2tool_world, rows)
    lock = load_lock(audio2tool_world.lock_path)

    report = build_a2t_report(
        attempt_dir, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root
    )

    document = report_to_json(report)
    assert document["schema"] == "saea-a2t-a0-read-v1"
    assert document["overall"]["n_samples"] == 3
    assert document["headroom"]["sample_ids"] == [_TIER3_ID]
    assert document["recheck_mismatch_count"] == 0

    headroom_document = headroom_to_json(report)
    assert headroom_document["schema"] == "saea-a2t-a0-headroom-v1"
    assert headroom_document["sample_ids"] == [_TIER3_ID]
    assert headroom_document["count"] == 1


# ---------------------------------------------------------------------------
# CLI: end-to-end + one-shot idempotence guard.
# ---------------------------------------------------------------------------


def _cli_repo_layout(tmp_path: Path, world) -> Path:
    """<umbrella>/studies/<name>/ so ``umbrella_lock_path``'s own
    ``repo_root.parent.parent / "docs" / "datasets.lock.json"`` convention
    resolves to this world's own lock file, with the frozen probe receipt
    copied under the new repo_root's own ``docs/receipts/probe-samples/``."""

    repo_root = tmp_path / "umbrella" / "studies" / "study"
    receipts_dir = repo_root / "docs" / "receipts" / "probe-samples"
    receipts_dir.mkdir(parents=True)
    (receipts_dir / world.receipt_path.name).write_text(
        world.receipt_path.read_text(encoding="utf-8"), encoding="utf-8"
    )
    lock_dest = tmp_path / "umbrella" / "docs" / "datasets.lock.json"
    lock_dest.parent.mkdir(parents=True, exist_ok=True)
    lock_dest.write_text(world.lock_path.read_text(encoding="utf-8"), encoding="utf-8")
    return repo_root


def test_cli_refuses_to_run_twice_against_the_same_output_dir(audio2tool_world, tmp_path, monkeypatch):
    rows = _clean_rows(audio2tool_world)
    attempt_dir = _build_attempt_dir(tmp_path, audio2tool_world, rows)
    repo_root = _cli_repo_layout(tmp_path, audio2tool_world)
    monkeypatch.setenv("SPEECHRL_DATA_DIR", str(audio2tool_world.data_root))
    output_dir = tmp_path / "read-report"
    output_dir.mkdir()

    argv = [str(attempt_dir), "--output-dir", str(output_dir), "--repo-root", str(repo_root)]

    first_exit = a2t_read_main(argv)
    assert first_exit == 0
    verdict_path = output_dir / "verdict.json"
    assert verdict_path.is_file()
    assert (output_dir / "headroom.json").is_file()
    assert (output_dir / "report.txt").is_file()

    second_exit = a2t_read_main(argv)
    assert second_exit == 1
