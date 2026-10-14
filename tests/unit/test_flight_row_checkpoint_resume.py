"""Owner decision 309 (2026-10-14): durable rows and resume mode B.

The proofs here drive the ACTUAL native role episode (the real OpenJiuwen graph,
the real request composer, a scripted transport) through the ACTUAL
``FlightRuntime._dispatch_phase_program`` and the ACTUAL
``rails.phase_runner.run_continuous_program`` over a FULL-roster adapter -- the
E10 lesson (docs/superpowers/specs/2026-09-18-resume-modes-comparison.md): a
resume test that drives a roster-sized fake proves nothing about the dispatch.
No model, server, tokenizer or network contact anywhere in this file.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.contracts.errors import GateClosed
from speech_aware_evidence_acquisition.contracts.gate_exposure import _ExposureAndCarrierMixin
from speech_aware_evidence_acquisition.core import row_checkpoint as rc
from speech_aware_evidence_acquisition.core.attempts import (
    STATE_ABORTED, STATE_OPENED, AttemptStore,
)
from speech_aware_evidence_acquisition.core.bundle.outputs import (
    _verify_outputs_trace_binding,
    _verify_raw_trace,
    verify_predecessor_attempts,
)
from speech_aware_evidence_acquisition.core.flight.resume import (
    CheckpointPredecessor,
    MergedPredecessors,
    ResumeDeclaration,
    ResumeRecoveryError,
    read_checkpoint_predecessor,
    resume_declarations_from_document,
)
from speech_aware_evidence_acquisition.core.flight.runtime import (
    FlightRuntime,
    FlightRuntimeError,
)

from test_flight_resume_recovery import _harness, _skeleton, _values
from test_flight_runtime import _make_runtime
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_episode_runner import _ActualEpisodeHarness
from test_rails_frozen_core_client import _plan

RUN_ID = "SAEA-E-native-role-runner-proof"


@pytest.fixture(autouse=True)
def _four_sample_world(monkeypatch):
    """The synthetic world carries two samples by default (its own note: 'a
    subclass may widen the roster'); the crash/resume proofs need four."""

    from test_rails_frozen_core_client import _World

    monkeypatch.setattr(
        _World, "SAMPLE_SPECS", tuple((f"s{index}", 1.5 + index * 0.5) for index in range(1, 5))
    )


def _sequential(harness) -> None:
    """One slot: rows settle in roster order, so 'the first N rows' is exact."""

    harness.adapter.serving_geometry = lambda: {
        "slots": 1, "slot_tokens": 4096, "max_tokens": 256,
    }


def _ckpt_skeleton(harness, monkeypatch, attempt_dir: Path, sample_ids) -> FlightRuntime:
    """The E10 dispatch skeleton, with row checkpointing switched on."""

    runtime = _skeleton(harness, monkeypatch)
    # One row at a time, end to end: queue_depth 1 admits the next row only
    # after the previous one settled, so "the first N rows" is exact and the
    # attempt-scoped request counter is deterministic.
    import functools

    from speech_aware_evidence_acquisition.rails.phase_runner import run_continuous_program

    runtime._continuous_phase_runner = functools.partial(
        run_continuous_program, slot_count=1, queue_depth=1
    )
    runtime._composed = SimpleNamespace(values=_values(harness), config_hash="h" * 64)
    runtime._row_checkpointing = True
    runtime._row_checkpoint_writer = None
    runtime._row_checkpoint_report = None
    runtime._explicit_run_dir = attempt_dir
    runtime._samples = tuple(SimpleNamespace(sample_id=sample_id) for sample_id in sample_ids)
    return runtime


def _fly_all(runtime, harness):
    try:
        rows, *_ = runtime._dispatch_phase_program(
            harness.client, harness.plan, harness.program.program_id
        )
    finally:
        harness.close()
    runtime._output_rows = rows
    runtime._client = harness.client
    return rows


def _canonical_json(rows) -> list[str]:
    return [json.dumps(row, sort_keys=True, ensure_ascii=False) for row in rows]


IDS = ("s1", "s2", "s3", "s4")


# ---------------------------------------------------------------------------
# (a) The checkpoint is written, fsynced, after each row -- before the program
#     ends and before ANY trace byte reaches the client's sink.
# ---------------------------------------------------------------------------


def test_each_settled_row_is_durable_the_moment_it_settles(tmp_path, monkeypatch):
    harness = _harness(tmp_path, "full", IDS)
    _sequential(harness)
    attempt_dir = tmp_path / "attempt-full"
    runtime = _ckpt_skeleton(harness, monkeypatch, attempt_dir, IDS)
    snapshots = []
    fsyncs = []
    real_fsync = rc.os.fsync
    monkeypatch.setattr(rc.os, "fsync", lambda fd: (fsyncs.append(fd), real_fsync(fd))[1])
    real_checkpoint_row = FlightRuntime._checkpoint_row
    trace_file = harness.world.run_dir / f"{harness.plan.run_id}.trace.jsonl"

    def watching(self, **kwargs):
        before = len(fsyncs)
        real_checkpoint_row(self, **kwargs)
        document = rc.read_checkpoint(rc.checkpoint_path(attempt_dir, harness.plan.run_id))
        snapshots.append((
            [row.sample_id for row in document.rows], len(fsyncs) - before,
            trace_file.exists(),
        ))

    monkeypatch.setattr(FlightRuntime, "_checkpoint_row", watching)
    _fly_all(runtime, harness)

    # After the k-th row settled the file held exactly k rows, one fsync paid
    # for the append, and the client's trace file did not exist yet: the defect
    # of 2026-10-14 (nothing durable until the seal) is gone.
    assert [rows for rows, _, _ in snapshots] == [list(IDS[: k + 1]) for k in range(4)]
    assert all(count == 1 for _, count, _ in snapshots)
    assert not any(trace_present for _, _, trace_present in snapshots)

    # The checkpointed canonical record IS the record the seal renders.
    canonical = runtime._canonical_output_rows(harness.client)
    document = rc.read_checkpoint(rc.checkpoint_path(attempt_dir, harness.plan.run_id))
    assert document.complete_rows == 4 and document.unrendered_rows == 0
    assert _canonical_json([row.output_rows[0] for row in document.rows]) == _canonical_json(canonical)
    # ... and carries the row's whole trace: the contacts, the episode receipt.
    first = document.rows[0]
    ids = [json.loads(line)["record_id"] for line in first.trace_lines]
    assert any(record_id.endswith("/native-episode") for record_id in ids)
    assert any(record_id.endswith("/request") for record_id in ids)
    assert first.contacts >= 1
    # The seal-time verification agrees and returns the manifest block.
    block = runtime._seal_row_checkpoint(canonical)
    assert block["sha256"] == rc.sha256_file(document.path)
    assert block["row_count"] == 4 and block["complete_rows"] == 4
    assert runtime._row_checkpoint_report["status"] == "VERIFIED"


def test_the_trace_the_client_writes_is_unchanged_by_checkpointing(tmp_path, monkeypatch):
    """The final trace is the same bytes with and without a checkpoint: the
    runtime-use records are emitted into each row's own buffer at the same
    place, and the buffers reach the sink in the same order."""

    def stable(node):
        # wall-clock measurements differ between any two runs; nothing else may
        if isinstance(node, dict):
            return {k: stable(v) for k, v in node.items() if k != "latency_seconds"}
        if isinstance(node, list):
            return [stable(v) for v in node]
        return node

    traces = {}
    for name, checkpointing in (("on", True), ("off", False)):
        harness = _harness(tmp_path, name, IDS)
        _sequential(harness)
        runtime = _ckpt_skeleton(harness, monkeypatch, tmp_path / f"attempt-{name}", IDS)
        runtime._row_checkpointing = checkpointing
        _fly_all(runtime, harness)
        text = (harness.world.run_dir / f"{harness.plan.run_id}.trace.jsonl").read_text("utf-8")
        records = [json.loads(line) for line in text.splitlines()]
        for record in records:
            if record["record_id"].endswith("/sample-execution-timing"):
                record["payload"] = {}
        traces[name] = [stable(record) for record in records]
    assert traces["on"] == traces["off"]
    assert len(traces["on"]) > 40


# ---------------------------------------------------------------------------
# (b) Kill mid-flight -> the checkpoint holds the settled rows -> the resume
#     keeps them, flies the rest, and seals the merged rows.
# ---------------------------------------------------------------------------


def _crashing_flight(tmp_path, monkeypatch, *, die_on="s3"):
    attempt_id = "attempt-crashed"
    plan = _plan(
        run_id=RUN_ID, attempt_id=attempt_id,
        planned_model_calls=len(IDS) * 4 + 8,
    )
    harness = _ActualEpisodeHarness(
        tmp_path / "crashed", sample_count=len(IDS), sample_ids=IDS, max_revisions=0,
        max_contacts=4, planner_actions=("ACCEPT",), arm="speech-feature-query",
        execution_plan=plan,
    )
    _sequential(harness)
    original = harness._output

    def dying(key):
        if key[0] == die_on:
            raise RuntimeError("host restarted: Windows Update")
        return original(key)

    harness._output = dying
    attempt_dir = tmp_path / "runs" / RUN_ID / attempt_id
    runtime = _ckpt_skeleton(harness, monkeypatch, attempt_dir, IDS)
    with pytest.raises(Exception):  # noqa: B017 -- the simulated process death
        runtime._dispatch_phase_program(
            harness.client, harness.plan, harness.program.program_id
        )
    harness.close()
    return harness, runtime, attempt_dir


def _reference_rows(tmp_path, monkeypatch):
    harness = _harness(tmp_path, "reference", IDS)
    _sequential(harness)
    runtime = _ckpt_skeleton(harness, monkeypatch, tmp_path / "attempt-reference", IDS)
    _fly_all(runtime, harness)
    return runtime._canonical_output_rows(harness.client)


def _resume(tmp_path, monkeypatch, attempt_dir, crashed):
    pin = rc.sha256_file(rc.checkpoint_path(attempt_dir, RUN_ID))
    recovery = _harness(tmp_path, "recovery", ("s3", "s4"))
    _sequential(recovery)
    recovery_dir = tmp_path / "runs" / RUN_ID / "attempt-recovery"
    runtime = _ckpt_skeleton(recovery, monkeypatch, recovery_dir, IDS)
    predecessor = read_checkpoint_predecessor(
        run_id=RUN_ID, attempt_id="attempt-crashed", attempt_dir=attempt_dir,
        expected_checkpoint_sha256=pin,
        materialize_dir=recovery_dir / "resume-predecessors" / "attempt-crashed",
        protocol_hash=recovery.plan.protocol_hash,
        split_identity_hash=recovery.plan.split_identity_hash,
    )
    runtime._resume = MergedPredecessors((predecessor,))
    runtime._resume_flown_sample_ids = tuple(
        sample_id for sample_id in IDS if sample_id not in predecessor.complete_sample_ids
    )
    return recovery, runtime, predecessor


def test_a_kill_after_two_rows_leaves_two_durable_rows(tmp_path, monkeypatch):
    _harness_, _runtime, attempt_dir = _crashing_flight(tmp_path, monkeypatch)
    # Nothing but the checkpoint is on disk of that attempt's rows -- exactly
    # the 2026-10-14 shape -- yet the two settled rows survived it.
    assert not list(attempt_dir.glob("*.trace.jsonl"))
    document = rc.read_checkpoint(rc.checkpoint_path(attempt_dir, RUN_ID))
    assert [row.sample_id for row in document.rows] == ["s1", "s2"]
    assert all(row.keepable for row in document.rows)
    # The in-flight row left no partial record behind.
    assert document.torn_tail_bytes == 0


def test_a_checkpointed_row_equals_the_mode_a_replay_of_its_own_stored_trace(
    tmp_path, monkeypatch
):
    """An independent oracle for 'exactly as the seal would produce it': write
    the stored trace lines out as a trace file, replay it with the mode-A
    reader (no knowledge of the live result objects), render the rows through
    the same canonical stage, and compare byte for byte with what the
    checkpoint stored from the LIVE result."""

    from speech_aware_evidence_acquisition.core.flight.resume import read_predecessor_attempt

    crashed, runtime, attempt_dir = _crashing_flight(tmp_path, monkeypatch)
    document = rc.read_checkpoint(rc.checkpoint_path(attempt_dir, RUN_ID))
    replay_dir = tmp_path / "replayed"
    replay_dir.mkdir()
    (replay_dir / f"{RUN_ID}.trace.jsonl").write_text(
        rc.kept_trace_text(document.rows), encoding="utf-8", newline="\n"
    )
    scan = read_predecessor_attempt(
        run_id=RUN_ID, attempt_id="attempt-crashed", attempt_dir=replay_dir,
        program_id=crashed.program.program_id,
    )
    assert scan.complete_sample_ids == ("s1", "s2")
    summaries, timings = scan.replay(scan.complete_sample_ids, controller_policy_id="p")
    replayed = runtime._canonical_output_rows(
        crashed.client,
        output_rows=FlightRuntime._rows_from_phase_summaries(
            summaries, policy=crashed.program.program_id
        ),
        timings=timings, phase_summaries=summaries,
    )
    assert _canonical_json(replayed) == _canonical_json(
        [row.output_rows[0] for row in document.rows]
    )


def test_the_resume_keeps_the_settled_rows_flies_the_rest_and_the_bundle_holds_every_row(
    tmp_path, monkeypatch
):
    reference = _reference_rows(tmp_path, monkeypatch)
    crashed, _crash_runtime, attempt_dir = _crashing_flight(tmp_path, monkeypatch)
    recovery, runtime, predecessor = _resume(tmp_path, monkeypatch, attempt_dir, crashed)

    assert predecessor.complete_sample_ids == ("s1", "s2")
    assert runtime._resume_flown_sample_ids == ("s3", "s4")
    _fly_all(runtime, recovery)
    # The recovery spent contacts on the rows it flew and on no other.
    assert {timing.sample_id for timing in recovery.client.timings} == {"s3", "s4"}

    merged, block, _ = runtime._merged_canonical_rows()
    assert [row["sample_id"] for row in merged] == list(IDS)
    # Kept rows: byte for byte the rows an uninterrupted flight seals.
    assert _canonical_json(merged[:2]) == _canonical_json(reference[:2])
    # Flown rows: the same delivered answer; only the attempt-scoped transport
    # identity (request ids and the hashes bound to them) is the recovery's own.
    attempt_scoped = {"request_id", "request_sha256", "response_sha256", "native_episode_receipt"}
    for flown, expected in zip(merged[2:], reference[2:], strict=True):
        assert {k: v for k, v in flown.items() if k not in attempt_scoped} == {
            k: v for k, v in expected.items() if k not in attempt_scoped
        }
    assert block["mode"] == "checkpoint"
    assert block["counts"] == {"kept": 2, "flown": 2, "partial": 0}
    assert block["checkpoint_sha256"] == predecessor.checkpoint_sha256
    assert block["kept_sample_ids"] == ["s1", "s2"]

    # (e) the recovery's OWN checkpoint covers exactly the rows it flew, and the
    #     seal-time hold against the merged rows passes.
    own = runtime._seal_row_checkpoint(merged)
    own_document = rc.read_checkpoint(rc.checkpoint_path(tmp_path / "runs" / RUN_ID / "attempt-recovery", RUN_ID))
    assert [row.sample_id for row in own_document.rows] == ["s3", "s4"]
    assert own["sha256"] == own_document.sha256

    # I7r with the REAL verifier: kept rows against the materialized predecessor
    # trace (re-derived from the pinned checkpoint), flown rows against the
    # recovery's own trace; no row against both.
    manifest = {"run_id": RUN_ID, "predecessor_attempt": block}
    per_sample, kept = verify_predecessor_attempts(
        manifest, split_ids=frozenset(IDS), attempt_id="attempt-recovery"
    )
    assert kept == frozenset({"s1", "s2"})
    recovery_trace = (recovery.world.run_dir / f"{recovery.plan.run_id}.trace.jsonl").read_bytes()
    _verify_outputs_trace_binding(
        tuple(merged), _verify_raw_trace(recovery_trace, None),
        predecessor_records=per_sample, kept_sample_ids=kept,
    )


def test_a_row_the_checkpoint_does_not_hold_complete_is_re_flown_whole(tmp_path, monkeypatch):
    _crashed, _runtime, attempt_dir = _crashing_flight(tmp_path, monkeypatch)
    path = rc.checkpoint_path(attempt_dir, RUN_ID)
    document = rc.read_checkpoint(path)
    # Re-write the checkpoint with s2 recorded as NOT rendered (the canonical
    # stage refused it): it is incomplete, with its reason, and is re-flown.
    clone_dir = tmp_path / "runs" / RUN_ID / "attempt-clone"
    writer = rc.RowCheckpointWriter(
        clone_dir, RUN_ID, "attempt-crashed",
        identity={k: document.header[k] for k in ("protocol_hash", "split_identity_hash")},
    )
    first, second = document.rows
    writer.append_row(sample_id=first.sample_id, complete=True, output_rows=list(first.output_rows),
                      trace_lines=list(first.trace_lines))
    writer.append_row(sample_id=second.sample_id, complete=False, output_rows=[],
                      trace_lines=list(second.trace_lines), reason="FlightRuntimeError: refused")
    writer.close()
    predecessor = read_checkpoint_predecessor(
        run_id=RUN_ID, attempt_id="attempt-crashed", attempt_dir=clone_dir,
        expected_checkpoint_sha256=rc.sha256_file(writer.path),
        materialize_dir=tmp_path / "materialized",
        protocol_hash=document.header["protocol_hash"],
        split_identity_hash=document.header["split_identity_hash"],
    )
    assert predecessor.complete_sample_ids == ("s1",)
    assert predecessor.incomplete == {"s2": "FlightRuntimeError: refused"}
    assert predecessor.started_sample_ids == ("s1", "s2")
    # Its spend is still accounted for (the contacts really happened).
    assert predecessor.cost_totals()["calls_used"] == first.contacts + second.contacts


# ---------------------------------------------------------------------------
# (c) A multi-arm column row is kept only when every arm is present.
# ---------------------------------------------------------------------------


def _checkpoint_with(tmp_path: Path, rows: dict[str, dict]) -> tuple[Path, str]:
    writer = rc.RowCheckpointWriter(
        tmp_path / "attempt-arms", "RUN-ARMS", "attempt-arms",
        identity={"protocol_hash": "p" * 64, "split_identity_hash": "s" * 64},
    )
    for index, (sample_id, record) in enumerate(rows.items(), start=1):
        request_id = f"flight-{index:04d}"
        lines = rc.serialize_trace_records([
            ("MODEL_REQUEST", f"{request_id}/request", {"payload": {"sample_id": sample_id}, "payload_sha256": "a" * 64}),
            ("MODEL_RESPONSE", f"{request_id}/response", {"text": "t", "response_sha256": "b" * 64, "response_text_sha256": "c" * 64}),
        ])
        writer.append_row(
            sample_id=sample_id, complete=True,
            output_rows=[{"sample_id": sample_id, "request_id": request_id, "text": "t", **record}],
            trace_lines=lines,
        )
    writer.close()
    return writer.path.parent, rc.sha256_file(writer.path)


def _arms(arm_count: int, present: int) -> dict:
    arms = [{"arm_index": i, "arm_id": f"arm-{i}"} for i in range(present)]
    return {"supply_variants": {
        "arm_count": arm_count, "arms": arms,
        "delivered_arm_id": arms[-1]["arm_id"] if arms else None,
    }}


def test_a_column_row_is_kept_only_with_every_arm(tmp_path):
    attempt_dir, pin = _checkpoint_with(tmp_path, {
        "whole": _arms(3, 3), "two-of-three": _arms(3, 2), "none-of-three": _arms(3, 0),
        "plain": {},
    })
    predecessor = read_checkpoint_predecessor(
        run_id="RUN-ARMS", attempt_id="attempt-arms", attempt_dir=attempt_dir,
        expected_checkpoint_sha256=pin, materialize_dir=tmp_path / "m",
    )
    assert predecessor.complete_sample_ids == ("plain", "whole")
    assert set(predecessor.incomplete) == {"two-of-three", "none-of-three"}
    assert all("arm" in reason for reason in predecessor.incomplete.values())
    # the materialized trace holds ONLY the kept rows' lines
    text = predecessor.trace_path.read_text(encoding="utf-8")
    assert "flight-0001/request" in text and "flight-0004/request" in text
    assert "flight-0002/request" not in text and "flight-0003/request" not in text


# ---------------------------------------------------------------------------
# (d) A tampered checkpoint is refused, by name.
# ---------------------------------------------------------------------------


def test_a_tampered_checkpoint_is_refused_at_the_resume(tmp_path):
    attempt_dir, pin = _checkpoint_with(tmp_path, {"a": {}, "b": {}})
    path = rc.checkpoint_path(attempt_dir, "RUN-ARMS")
    path.write_bytes(path.read_bytes().replace(b'"text":"t"', b'"text":"X"', 1))
    with pytest.raises(ResumeRecoveryError, match="hashes to"):
        read_checkpoint_predecessor(
            run_id="RUN-ARMS", attempt_id="attempt-arms", attempt_dir=attempt_dir,
            expected_checkpoint_sha256=pin, materialize_dir=tmp_path / "m",
        )
    # Even re-pinned to the tampered bytes, the CHAIN refuses.
    with pytest.raises(ResumeRecoveryError, match="edited after it was written"):
        read_checkpoint_predecessor(
            run_id="RUN-ARMS", attempt_id="attempt-arms", attempt_dir=attempt_dir,
            expected_checkpoint_sha256=rc.sha256_file(path), materialize_dir=tmp_path / "m",
        )


def test_a_checkpoint_of_another_protocol_or_attempt_is_refused(tmp_path):
    attempt_dir, pin = _checkpoint_with(tmp_path, {"a": {}})
    common = dict(run_id="RUN-ARMS", attempt_dir=attempt_dir, expected_checkpoint_sha256=pin,
                  materialize_dir=tmp_path / "m")
    with pytest.raises(ResumeRecoveryError, match="protocol_hash"):
        read_checkpoint_predecessor(attempt_id="attempt-arms", protocol_hash="q" * 64, **common)
    with pytest.raises(ResumeRecoveryError, match="attempt_id"):
        read_checkpoint_predecessor(attempt_id="another-attempt", **common)
    with pytest.raises(ResumeRecoveryError, match="no row checkpoint"):
        read_checkpoint_predecessor(
            run_id="RUN-ARMS", attempt_id="attempt-arms", attempt_dir=tmp_path / "empty",
            expected_checkpoint_sha256=pin, materialize_dir=tmp_path / "m")


def test_the_resume_declaration_takes_exactly_one_pin():
    trace = ResumeDeclaration.from_document({"attempt_id": "a", "trace_sha256": "1" * 64})
    ckpt = ResumeDeclaration.from_document({"attempt_id": "a", "checkpoint_sha256": "2" * 64})
    assert (trace.mode, ckpt.mode) == ("trace", "checkpoint")
    for bad in (
        {"attempt_id": "a", "trace_sha256": "1" * 64, "checkpoint_sha256": "2" * 64},
        {"attempt_id": "a", "checkpoint_sha256": "nope"},
        {"attempt_id": "a"},
    ):
        with pytest.raises(ResumeRecoveryError):
            ResumeDeclaration.from_document(bad)
    mixed = resume_declarations_from_document([
        {"attempt_id": "a", "trace_sha256": "1" * 64},
        {"attempt_id": "b", "checkpoint_sha256": "2" * 64},
    ])
    assert [d.mode for d in mixed] == ["trace", "checkpoint"]


# ---------------------------------------------------------------------------
# (e) The sealed manifest records the checkpoint sha256; a divergent checkpoint
#     refuses the seal before a bundle byte is written.
# ---------------------------------------------------------------------------


def _captured_runtime(tmp_path, captured):
    def builder(**kwargs):
        captured.update(kwargs)
        from test_flight_runtime import _fake_manifest_builder
        return _fake_manifest_builder(**kwargs)

    return _make_runtime(tmp_path, happy_path=True, manifest_builder=builder)


def _stage_to_seal(runtime):
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    runtime.run_phases()


def _write_flown_checkpoint(runtime, *, corrupt: str | None = None, skip: str | None = None):
    canonical = runtime._canonical_output_rows(runtime._client)
    writer = rc.RowCheckpointWriter(
        runtime._run_dir(), runtime.run_id, runtime.attempt_id,
        identity={"protocol_hash": runtime.plan.protocol_hash},
    )
    for row in canonical:
        if row["sample_id"] == skip:
            continue
        stored = dict(row)
        if row["sample_id"] == corrupt:
            stored["text"] = "not what the seal renders"
        writer.append_row(
            sample_id=row["sample_id"], complete=True, output_rows=[stored],
            trace_lines=rc.serialize_trace_records([
                ("MODEL_REQUEST", f"{row['request_id']}/request",
                 {"payload": {"sample_id": row["sample_id"]}, "payload_sha256": row["request_sha256"]}),
            ]),
        )
    writer.close()
    runtime._row_checkpoint_writer = writer
    return writer


def test_the_sealed_manifest_records_the_checkpoint_sha256(tmp_path):
    captured = {}
    runtime = _captured_runtime(tmp_path, captured)
    _stage_to_seal(runtime)
    writer = _write_flown_checkpoint(runtime)
    receipt = runtime.seal()
    block = captured["row_checkpoint"]
    assert block["sha256"] == rc.sha256_file(writer.path)
    assert block["path"] == str(writer.path)
    assert (block["row_count"], block["complete_rows"], block["unrendered_rows"]) == (2, 2, 0)
    assert receipt["row_checkpoint"]["status"] == "VERIFIED"
    assert receipt["row_checkpoint"]["sha256"] == block["sha256"]


def test_a_flight_whose_runner_never_checkpointed_is_reported_not_hidden(tmp_path):
    captured = {}
    runtime = _captured_runtime(tmp_path, captured)
    _stage_to_seal(runtime)
    runtime._row_checkpoint_writer = rc.RowCheckpointWriter(
        runtime._run_dir(), runtime.run_id, runtime.attempt_id, identity={})
    receipt = runtime.seal()
    assert "row_checkpoint" not in captured  # no empty claim in the manifest
    assert receipt["row_checkpoint"] == {"status": "NOT-EXERCISED", "rows": 0}


@pytest.mark.parametrize("fault", ("corrupt", "skip"))
def test_a_checkpoint_that_disagrees_with_the_seal_refuses_it(tmp_path, fault):
    captured = {}
    runtime = _captured_runtime(tmp_path, captured)
    _stage_to_seal(runtime)
    _write_flown_checkpoint(runtime, **({"corrupt": "s2"} if fault == "corrupt" else {"skip": "s2"}))
    with pytest.raises(FlightRuntimeError, match="row checkpoint disagrees|disagrees with the rows"):
        runtime.seal()
    assert not captured  # refused before the manifest was built
    assert not list(runtime._run_dir().glob("*.outputs.jsonl"))


# ---------------------------------------------------------------------------
# The stage sequence through preflight / run_phases / seal for mode B.
# ---------------------------------------------------------------------------

_CONFIG = {"policy": "phase-direct-only-v1"}


def _plan_identity(tmp_path):
    probe = _make_runtime(tmp_path / "probe", happy_path=True, config_kwargs=_CONFIG)
    probe.preflight()
    return {
        "protocol_hash": probe.plan.protocol_hash,
        "split_identity_hash": probe.plan.split_identity_hash,
        "implementation": dict(FlightRuntime.row_checkpoint_implementation()),
    }


def _predecessor_checkpoint(tmp_path, identity, attempt_id, sample_ids, *, run_id="SAEA-TEST-RUN-001"):
    attempt_dir = tmp_path / "data" / "runs" / run_id / attempt_id
    writer = rc.RowCheckpointWriter(attempt_dir, run_id, attempt_id, identity=identity)
    for index, sample_id in enumerate(sample_ids, start=1):
        request_id = f"{attempt_id}-{index:04d}"
        record = {
            "request_id": request_id, "sample_id": sample_id, "carrier_lock_key": "fake-carrier",
            "arm": "test-arm", "text": f"kept {sample_id}", "admitted": True,
            "request_sha256": "a" * 64, "response_sha256": "b" * 64,
            "response_text_sha256": hashlib.sha256(f"kept {sample_id}".encode()).hexdigest(),
        }
        writer.append_row(
            sample_id=sample_id, complete=True, output_rows=[record],
            trace_lines=rc.serialize_trace_records([
                ("MODEL_REQUEST", f"{request_id}/request", {"payload": {"sample_id": sample_id}, "payload_sha256": "a" * 64}),
                ("MODEL_RESPONSE", f"{request_id}/response", {"text": f"kept {sample_id}", "response_sha256": "b" * 64, "response_text_sha256": record["response_text_sha256"]}),
            ]),
        )
    writer.close()
    return rc.sha256_file(writer.path)


def _open_attempt(tmp_path, run_id, attempt_id):
    AttemptStore(tmp_path / "data" / "attempts").open_attempt(
        run_id, attempt_id, carrier_lock_key="fake-carrier", reserved_calls=10,
        reserved_audio_seconds=100.0,
    )


def test_a_seal_only_completion_from_two_checkpoints_seals_the_stored_rows(tmp_path):
    identity = _plan_identity(tmp_path)
    pin_a = _predecessor_checkpoint(tmp_path, identity, "attempt-dead-a", ["s1"])
    pin_b = _predecessor_checkpoint(tmp_path, identity, "attempt-dead-b", ["s2"])
    for attempt in ("attempt-dead-a", "attempt-dead-b"):
        _open_attempt(tmp_path, "SAEA-TEST-RUN-001", attempt)
    captured = {}

    def builder(**kwargs):
        captured.update(kwargs)
        from test_flight_runtime import _fake_manifest_builder
        return _fake_manifest_builder(**kwargs)

    runtime = _make_runtime(
        tmp_path, happy_path=True, config_kwargs=_CONFIG, manifest_builder=builder,
        resume_from=[
            {"attempt_id": "attempt-dead-a", "checkpoint_sha256": pin_a},
            {"attempt_id": "attempt-dead-b", "checkpoint_sha256": pin_b},
        ],
    )
    receipt = runtime.preflight()
    assert runtime.is_seal_only
    assert receipt["resume"]["counts"]["kept"] == 2
    assert {p["mode"] for p in receipt["resume"]["predecessors"]} == {"checkpoint"}
    # The gate-visible declaration is on disk before the first gate touch.
    declaration = json.loads((runtime._run_dir() / "resume-declaration.json").read_text("utf-8"))
    assert [p["attempt_id"] for p in declaration["predecessors"]] == ["attempt-dead-a", "attempt-dead-b"]

    runtime.preprocess()
    runtime.serve()
    runtime.run_phases()
    # Admission: the crashed attempts (state OPENED forever) are settled.
    store = AttemptStore(tmp_path / "data" / "attempts")
    for attempt in ("attempt-dead-a", "attempt-dead-b"):
        document = json.loads(store.handle("SAEA-TEST-RUN-001", attempt).path.read_text("utf-8"))
        assert document["state"] == STATE_ABORTED

    seal = runtime.seal()
    rows = [json.loads(line) for line in Path(seal["outputs_path"]).read_text("utf-8").splitlines()]
    assert [row["text"] for row in rows] == ["kept s1", "kept s2"]
    blocks = captured["predecessor_attempts"]
    assert [b["mode"] for b in blocks] == ["checkpoint", "checkpoint"]
    assert [b["checkpoint_sha256"] for b in blocks] == [pin_a, pin_b]
    assert "row_checkpoint" not in captured  # a seal-only attempt flew nothing


def test_preflight_refuses_a_checkpoint_pin_that_does_not_match(tmp_path):
    identity = _plan_identity(tmp_path)
    _predecessor_checkpoint(tmp_path, identity, "attempt-dead-a", ["s1"])
    runtime = _make_runtime(
        tmp_path, happy_path=True, config_kwargs=_CONFIG,
        resume_from={"attempt_id": "attempt-dead-a", "checkpoint_sha256": "0" * 64},
    )
    with pytest.raises(FlightRuntimeError, match="hashes to"):
        runtime.preflight()


def test_preflight_refuses_a_checkpoint_written_for_another_protocol(tmp_path):
    identity = _plan_identity(tmp_path)
    pin = _predecessor_checkpoint(
        tmp_path, {**identity, "protocol_hash": "9" * 64}, "attempt-dead-a", ["s1"])
    runtime = _make_runtime(
        tmp_path, happy_path=True, config_kwargs=_CONFIG,
        resume_from={"attempt_id": "attempt-dead-a", "checkpoint_sha256": pin},
    )
    with pytest.raises(FlightRuntimeError, match="protocol_hash"):
        runtime.preflight()


def test_preflight_refuses_a_checkpoint_written_by_different_code(tmp_path):
    identity = _plan_identity(tmp_path)
    pin = _predecessor_checkpoint(
        tmp_path,
        {**identity, "implementation": {**identity["implementation"], "runner": "0" * 64}},
        "attempt-dead-a", ["s1"],
    )
    runtime = _make_runtime(
        tmp_path, happy_path=True, config_kwargs=_CONFIG,
        resume_from={"attempt_id": "attempt-dead-a", "checkpoint_sha256": pin},
    )
    with pytest.raises(FlightRuntimeError, match=r"different code \(runner\)"):
        runtime.preflight()


def test_a_partial_checkpoint_resume_flies_the_remainder(tmp_path):
    identity = _plan_identity(tmp_path)
    pin = _predecessor_checkpoint(tmp_path, identity, "attempt-dead-a", ["s1"])
    runtime = _make_runtime(
        tmp_path, happy_path=True, config_kwargs=_CONFIG,
        resume_from={"attempt_id": "attempt-dead-a", "checkpoint_sha256": pin},
    )
    receipt = runtime.preflight()
    assert not runtime.is_seal_only
    assert runtime._flight_roster_sample_ids() == ("s2",)
    assert receipt["resume"]["counts"] == {
        "roster": 2, "kept": 1, "flown": 1, "partial": 0, "unstarted": 1,
    }
    assert receipt["resume"]["predecessors"][0]["checkpoint_sha256"] == pin


# ---------------------------------------------------------------------------
# The attempt registry / exposure gate: a resume is admitted, a fresh second
# attempt is still refused.
# ---------------------------------------------------------------------------


class _Gate(_ExposureAndCarrierMixin):
    def __init__(self, data_root: Path) -> None:
        self.data_root = data_root


def _allowance(run_id: str) -> dict:
    return {"read_run_ids": [run_id]}


def _write_attempt_state(data_root: Path, run_id: str, attempt_id: str, state: str) -> None:
    path = data_root / "attempts" / run_id / f"{attempt_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"state": state}), encoding="utf-8")


def _declare(data_root: Path, run_id: str, attempt_id: str, predecessors) -> None:
    path = data_root / "runs" / run_id / attempt_id / "resume-declaration.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "schema": "saea-resume-declaration-v1", "run_id": run_id, "attempt_id": attempt_id,
        "predecessors": [{"attempt_id": name} for name in predecessors],
    }), encoding="utf-8")


def test_the_one_read_rule_admits_a_resume_of_an_interrupted_attempt_only(tmp_path):
    run_id = "SAEA-READ-1"
    plan = SimpleNamespace(run_id=run_id, attempt_id="attempt-2")
    gate = _Gate(tmp_path)
    _write_attempt_state(tmp_path, run_id, "attempt-1", STATE_OPENED)

    # A fresh second attempt that resumes nothing is still refused (unchanged).
    with pytest.raises(GateClosed, match="allows at most 1 attempt"):
        gate._require_final_report_attempt_budget(plan, _allowance(run_id))

    # The same attempt declaring that it resumes the interrupted one is admitted.
    _declare(tmp_path, run_id, "attempt-2", ["attempt-1"])
    gate._require_final_report_attempt_budget(plan, _allowance(run_id))

    # Once the predecessor is superseded (ABORTED) the resume is still admitted.
    _write_attempt_state(tmp_path, run_id, "attempt-1", STATE_ABORTED)
    gate._require_final_report_attempt_budget(plan, _allowance(run_id))

    # A resume does not open a door to a THIRD attempt.
    _write_attempt_state(tmp_path, run_id, "attempt-2", STATE_OPENED)
    third = SimpleNamespace(run_id=run_id, attempt_id="attempt-3")
    with pytest.raises(GateClosed, match="allows at most 1 attempt"):
        gate._require_final_report_attempt_budget(third, _allowance(run_id))


def test_a_settled_attempt_can_never_be_resumed(tmp_path):
    run_id = "SAEA-READ-2"
    gate = _Gate(tmp_path)
    _write_attempt_state(tmp_path, run_id, "attempt-1", "FINALIZED")
    _declare(tmp_path, run_id, "attempt-2", ["attempt-1"])
    with pytest.raises(GateClosed, match="FINALIZED"):
        gate._require_final_report_attempt_budget(
            SimpleNamespace(run_id=run_id, attempt_id="attempt-2"), _allowance(run_id))
    _declare(tmp_path, run_id, "attempt-3", ["attempt-missing"])
    with pytest.raises(GateClosed, match="no attempt record"):
        gate._require_final_report_attempt_budget(
            SimpleNamespace(run_id=run_id, attempt_id="attempt-3"), _allowance(run_id))
