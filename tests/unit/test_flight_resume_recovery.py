"""E10 (owner decision 22, 2026-09-18): resume-recovery of an aborted attempt.

Every test here drives the ACTUAL native role episode
(``test_native_episode_runner._ActualEpisodeHarness``: the real OpenJiuwen
graph, the real request composer, a scripted transport) and the ACTUAL
``FlightRuntime`` sealing stage. No model, server, tokenizer or network
contact anywhere in this file -- the "model" is the harness's own scripted
wire response, exactly as every other episode proof in this suite.

The proof that matters: a row REPLAYED from an aborted attempt's trace is
byte identical to the row the uninterrupted flight sealed for that sample.
Both are rendered by the one ``_canonical_output_rows`` stage; the replay
only supplies the phase results and the ``RequestTiming`` records the live
dispatch would have supplied.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core import preparation_fit
from speech_aware_evidence_acquisition.core.flight import runtime as flight_module
from speech_aware_evidence_acquisition.core.flight.resume import (
    RESUME_PREDECESSOR_SCHEMA,
    ResumeDeclaration,
    ResumeRecoveryError,
    kept_sample_ids_sha256,
    read_predecessor_attempt,
)
from speech_aware_evidence_acquisition.core.flight.runtime import (
    FlightRuntime,
    FlightRuntimeError,
)

from test_native_episode_runner import _ActualEpisodeHarness
from test_rails_runner import _knowledge_snapshot
# The module-scoped fixture the harness's transport identity needs: it copies
# the python interpreter to a llama-server-shaped path and has it hold an
# ephemeral socket. No model, no resident service, no request ever leaves this
# process -- the harness answers through its own scripted ``post``.
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401


def _values(harness) -> dict:
    """The composed values a native-episode flight seals under."""

    return {
        "policy": harness.program.program_id,
        "carrier_lock_key": harness.plan.carrier_lock_key,
        "native_episode": {
            "schema": "saea-native-episode-config-v1",
            "episode_id": harness.config.episode_id,
            "max_revisions": harness.config.max_revisions,
            "actions": dict(
                zip(("accept", "revise", "acquire"), harness.config.actions)
            ),
            "roles": {
                role.role_kind: {
                    "phase_id": role.phase_id,
                    "max_iterations": role.max_iterations,
                }
                for role in harness.config.roles
            },
        },
        "native_contact_fit": {
            "run_id": "SAEA-RESUME-FIT",
            "attempt_id": "attempt-resume-fit",
            "contact_cap": 8 * harness.config.max_contacts,
        },
    }


def _skeleton(harness, monkeypatch) -> FlightRuntime:
    """The same skeleton ``test_flight_native_episode_dispatch`` builds: a real
    FlightRuntime bound to the harness's adapter, transport, plan and
    material, with the fit gate and program lookup seamed."""

    runtime = object.__new__(FlightRuntime)
    runtime._composed = SimpleNamespace(values=_values(harness))
    runtime._model = runtime._dataset = runtime._baseline = {}
    runtime._adapter = harness.adapter
    runtime._data_root = harness.world.data_root
    runtime._split_id = "all"
    runtime._transport = harness.transport
    runtime._arm = lambda: harness.client.arm
    runtime._plan = harness.plan
    runtime._phase_program_material = {
        "knowledge_snapshot": _knowledge_snapshot(),
        "speech_packet_bindings": harness.speech_bindings,
        "material_for_phase": harness.material_for_phase,
        "trace_sink": harness.trace,
        "review_for_phase": None,
    }
    from speech_aware_evidence_acquisition.rails.phase_runner import (
        run_continuous_program,
    )

    runtime._continuous_phase_runner = run_continuous_program
    runtime._phase_planner_specs = lambda _policy: {}
    runtime._phase_decoding_params = lambda: {"temperature": 0, "max_tokens": 64}
    runtime._fit_base_plan = lambda plan: plan
    runtime._build_phase_tool_dispatcher = lambda *args, **kwargs: None
    runtime._resume = None
    runtime._resume_flown_sample_ids = ()
    runtime._artifact_result_binding = None
    runtime._artifact_content_validator = None
    monkeypatch.setattr(
        flight_module, "default_phase_program", lambda _policy: harness.program
    )

    def identity_only_gate(request):
        harness.request_gate(request)
        identity_only_gate.receipts.append({"capacity_verified": False})

    identity_only_gate.receipts = []
    monkeypatch.setattr(
        preparation_fit, "build_native_contact_fit_gate", lambda *_args: identity_only_gate
    )
    return runtime


def _fly(harness, monkeypatch):
    """Run the actual episode for this harness's whole roster and seal it."""

    runtime = _skeleton(harness, monkeypatch)
    try:
        rows, *_ = runtime._dispatch_phase_program(
            harness.client, harness.plan, harness.program.program_id
        )
    finally:
        harness.close()
    runtime._output_rows = rows
    canonical = runtime._canonical_output_rows(harness.client)
    trace_path = harness.world.run_dir / f"{harness.plan.run_id}.trace.jsonl"
    return runtime, canonical, trace_path


def _trace_lines(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").split("\n")
        if line.strip()
    ]


def _write_predecessor(
    records, directory: Path, run_id: str, *, keep: set[str], truncate: set[str] = frozenset()
) -> Path:
    """Slice a real trace down to the samples an aborted attempt had reached.

    ``keep`` samples keep every record they produced. ``truncate`` samples
    keep their requests but lose their LAST response and their episode
    receipt -- exactly the shape a killed server leaves behind.
    """

    request_sample = {}
    sample_requests: dict[str, list[str]] = {}
    for record in records:
        if record["channel"] == "MODEL_REQUEST" and record["record_id"].endswith("/request"):
            request_id = record["record_id"][: -len("/request")]
            sample_id = record["payload"]["payload"]["sample_id"]
            request_sample[request_id] = sample_id
            sample_requests.setdefault(sample_id, []).append(request_id)
    wanted = set(keep) | set(truncate)
    dropped_responses = {
        sample_requests[sample_id][-1] for sample_id in truncate if sample_requests.get(sample_id)
    }
    kept_lines = []
    for record in records:
        record_id = record["record_id"]
        head = record_id.split("/")[0]
        sample_id = request_sample.get(head)
        if sample_id is None and head in wanted:
            sample_id = head
        if sample_id not in wanted:
            continue
        if sample_id in truncate:
            if record_id.endswith("/native-episode"):
                continue
            if head in dropped_responses and not record_id.endswith("/request"):
                continue
        kept_lines.append(json.dumps(record, ensure_ascii=False, sort_keys=True))
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{run_id}.trace.jsonl"
    path.write_text("\n".join(kept_lines) + "\n", encoding="utf-8", newline="\n")
    return path


def _scan(path: Path, harness, *, attempt_id="attempt-aborted", expected=None):
    return read_predecessor_attempt(
        run_id=harness.plan.run_id,
        attempt_id=attempt_id,
        attempt_dir=path.parent,
        expected_trace_sha256=expected,
        program_id=harness.program.program_id,
    )


def _harness(tmp_path, name, sample_ids, *, max_revisions=0):
    """One roster's worth of the actual episode, in its own directory."""

    return _ActualEpisodeHarness(
        tmp_path / name,
        sample_count=len(sample_ids),
        sample_ids=tuple(sample_ids),
        max_revisions=max_revisions,
        max_contacts=4 + 3 * max_revisions,
        planner_actions=("ACCEPT",) if max_revisions == 0 else ("REVISE", "ACCEPT"),
        arm="speech-feature-query",
    )


# ---------------------------------------------------------------------------
# The replay itself.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("max_revisions", (0, 1))
def test_replayed_rows_are_byte_identical_to_the_uninterrupted_seal(
    tmp_path, monkeypatch, max_revisions
):
    """(a) The nominal episode and the episode with an executed revision.

    The predecessor trace IS the uninterrupted run's own records, so a
    replayed row that differs from the sealed one by a single byte fails
    here.
    """

    harness = _harness(tmp_path, "full", ("s1", "s2"), max_revisions=max_revisions)
    runtime, canonical, trace_path = _fly(harness, monkeypatch)

    predecessor = _write_predecessor(
        _trace_lines(trace_path), tmp_path / "aborted", harness.plan.run_id,
        keep={"s1", "s2"},
    )
    scan = _scan(predecessor, harness)
    assert scan.complete_sample_ids == ("s1", "s2")
    assert scan.incomplete == {}

    summaries, timings = scan.replay(scan.complete_sample_ids, controller_policy_id="p")
    replayed_rows = FlightRuntime._rows_from_phase_summaries(
        summaries, policy=harness.program.program_id
    )
    replayed = runtime._canonical_output_rows(
        harness.client,
        output_rows=replayed_rows,
        timings=timings,
        phase_summaries=summaries,
    )
    assert [json.dumps(row, sort_keys=True) for row in replayed] == [
        json.dumps(row, sort_keys=True) for row in canonical
    ]
    # Not vacuous: the rows carry the delivered answer and its episode custody.
    assert [row["text"] for row in replayed] == [
        f"solver-answer:{sample}:visit:{max_revisions + 1}" for sample in ("s1", "s2")
    ]


@pytest.mark.parametrize("started", (True, False), ids=("partial", "unstarted"))
def test_a_row_the_predecessor_did_not_finish_is_re_flown_in_full(
    tmp_path, monkeypatch, started
):
    """(a) The third case: a row whose last response never arrived, and its
    twin, a row the aborted attempt never reached at all.

    A partial row is reported INCOMPLETE with a reason, it is NOT kept, and
    the recovery flies the WHOLE row again -- a resume never stitches a half
    row together from the contacts that did land. The merged seal is the
    union, in roster order, with the kept row byte identical to the
    uninterrupted one.
    """

    harness = _harness(tmp_path, "full", ("s1", "s2"))
    _runtime, canonical, trace_path = _fly(harness, monkeypatch)
    full_rows = {row["sample_id"]: row for row in canonical}

    predecessor = _write_predecessor(
        _trace_lines(trace_path), tmp_path / "aborted", harness.plan.run_id,
        keep={"s1"}, truncate={"s2"} if started else frozenset(),
    )
    scan = _scan(predecessor, harness)
    assert scan.complete_sample_ids == ("s1",)
    if started:
        assert scan.incomplete_sample_ids == ("s2",)
        assert "terminal receipt" in scan.incomplete["s2"]
        assert scan.started_sample_ids == ("s1", "s2")
    else:
        # Never started: neither complete nor incomplete, simply absent. The
        # roster is what puts it back into the flown set.
        assert scan.incomplete == {}
        assert scan.started_sample_ids == ("s1",)

    # The recovery attempt: the same episode over exactly the rows that are
    # not COMPLETE, in its own world with its own request-id counter.
    recovery = _harness(tmp_path, "recovery", ("s2",))
    recovery_runtime = _skeleton(recovery, monkeypatch)
    recovery_runtime._samples = tuple(
        SimpleNamespace(sample_id=sample_id) for sample_id in ("s1", "s2")
    )
    recovery_runtime._resume = scan
    recovery_runtime._resume_flown_sample_ids = ("s2",)
    try:
        rows, *_ = recovery_runtime._dispatch_phase_program(
            recovery.client, recovery.plan, recovery.program.program_id
        )
    finally:
        recovery.close()
    recovery_runtime._output_rows = rows
    recovery_runtime._client = recovery.client

    merged, block = recovery_runtime._merged_canonical_rows()
    assert [row["sample_id"] for row in merged] == ["s1", "s2"]
    # The kept row is byte identical to the uninterrupted seal.
    assert json.dumps(merged[0], sort_keys=True) == json.dumps(
        full_rows["s1"], sort_keys=True
    )
    # The re-flown row carries the same delivered answer; its transport
    # identity is this attempt's own, because request ids are attempt scoped.
    assert merged[1]["text"] == full_rows["s2"]["text"]
    assert merged[1]["response_text_sha256"] == full_rows["s2"]["response_text_sha256"]
    assert block == {
        "schema": RESUME_PREDECESSOR_SCHEMA,
        "run_id": harness.plan.run_id,
        "attempt_id": "attempt-aborted",
        "trace_path": str(predecessor),
        "trace_sha256": scan.trace_sha256,
        "kept_sample_ids": ["s1"],
        "kept_sample_ids_sha256": kept_sample_ids_sha256(["s1"]),
        "counts": {"kept": 1, "flown": 1, "partial": 1 if started else 0},
    }


def test_replay_refuses_a_declared_trace_hash_that_does_not_match(tmp_path, monkeypatch):
    harness = _harness(tmp_path, "full", ("s1",))
    _runtime, _canonical, trace_path = _fly(harness, monkeypatch)
    predecessor = _write_predecessor(
        _trace_lines(trace_path), tmp_path / "aborted", harness.plan.run_id, keep={"s1"},
    )
    with pytest.raises(ResumeRecoveryError, match="hashes to"):
        _scan(predecessor, harness, expected="0" * 64)


def test_replay_refuses_to_select_a_subset_of_the_complete_rows(tmp_path, monkeypatch):
    """No selection is expressible: asking to replay a row that is not
    COMPLETE refuses, and the caller cannot ask for fewer than all of them
    without the seal noticing the missing sample."""

    harness = _harness(tmp_path, "full", ("s1", "s2"))
    _runtime, _canonical, trace_path = _fly(harness, monkeypatch)
    predecessor = _write_predecessor(
        _trace_lines(trace_path), tmp_path / "aborted", harness.plan.run_id,
        keep={"s1"}, truncate={"s2"},
    )
    scan = _scan(predecessor, harness)
    with pytest.raises(ResumeRecoveryError, match="not COMPLETE"):
        scan.replay(("s1", "s2"))


def test_merged_rows_refuse_a_sample_that_was_kept_and_also_flown(tmp_path, monkeypatch):
    harness = _harness(tmp_path, "full", ("s1", "s2"))
    _runtime, _canonical, trace_path = _fly(harness, monkeypatch)
    predecessor = _write_predecessor(
        _trace_lines(trace_path), tmp_path / "aborted", harness.plan.run_id,
        keep={"s1", "s2"},
    )
    scan = _scan(predecessor, harness)

    recovery = _harness(tmp_path, "recovery", ("s1",))
    recovery_runtime = _skeleton(recovery, monkeypatch)
    recovery_runtime._samples = tuple(
        SimpleNamespace(sample_id=sample_id) for sample_id in ("s1", "s2")
    )
    recovery_runtime._resume = scan
    # The defect this refuses: a recovery that re-flew a row its predecessor
    # had already completed.
    recovery_runtime._resume_flown_sample_ids = ("s1",)
    try:
        rows, *_ = recovery_runtime._dispatch_phase_program(
            recovery.client, recovery.plan, recovery.program.program_id
        )
    finally:
        recovery.close()
    recovery_runtime._output_rows = rows
    recovery_runtime._client = recovery.client
    with pytest.raises(FlightRuntimeError, match="sealed twice"):
        recovery_runtime._merged_canonical_rows()


# ---------------------------------------------------------------------------
# The declaration and the narrowed roster.
# ---------------------------------------------------------------------------


def test_resume_declaration_refuses_a_malformed_document():
    for document in (
        {},
        {"attempt_id": "a"},
        {"attempt_id": "", "trace_sha256": "0" * 64},
        {"attempt_id": "a", "trace_sha256": "nope"},
        {"attempt_id": "a", "trace_sha256": "0" * 64, "extra": 1},
    ):
        with pytest.raises(ResumeRecoveryError):
            ResumeDeclaration.from_document(document)


def test_preflight_reads_the_declaration_and_fixes_the_flown_roster(
    tmp_path, monkeypatch
):
    """The config form the coordinator registers, end to end through the
    actual preflight: a ``resume_from`` block on the cell, the predecessor
    attempt beside this one under the same run id, and a flown roster that
    is the roster minus the predecessor's COMPLETE rows -- fixed BEFORE any
    contact, and recorded in the preflight receipt."""

    from test_flight_runtime import _make_runtime

    source = _harness(tmp_path, "full", ("s1", "s2"))
    _runtime, _canonical, trace_path = _fly(source, monkeypatch)
    run_id = "SAEA-TEST-RUN-001"
    attempt_dir = tmp_path / "data" / "runs" / run_id / "attempt-aborted"
    predecessor = _write_predecessor(
        _trace_lines(trace_path), attempt_dir, run_id, keep={"s1"}, truncate={"s2"},
    )
    import hashlib

    digest = hashlib.sha256(predecessor.read_bytes()).hexdigest()
    runtime = _make_runtime(
        tmp_path,
        happy_path=True,
        config_kwargs={
            "policy": source.program.program_id,
            "baseline_extra": {"native_episode": _values(source)["native_episode"]},
        },
        resume_from={"attempt_id": "attempt-aborted", "trace_sha256": digest},
    )
    receipt = runtime.preflight()

    assert receipt["resume"]["attempt_id"] == "attempt-aborted"
    assert receipt["resume"]["trace_sha256"] == digest
    assert receipt["resume"]["counts"] == {
        "roster": 2, "kept": 1, "flown": 1, "partial": 1, "unstarted": 0,
    }
    assert receipt["resume"]["partial_sample_ids"] == ["s2"]
    # Run-cumulative exposure: the recovery's own plan must still cover the
    # rows it flies at the program's contact ceiling.
    assert receipt["resume"]["worst_case_contacts"] == source.program.max_contacts
    assert runtime._flight_roster_sample_ids() == ("s2",)
    assert runtime.resume_predecessor.complete_sample_ids == ("s1",)


def test_preflight_refuses_a_predecessor_whose_trace_hash_was_not_declared(
    tmp_path, monkeypatch
):
    from test_flight_runtime import _make_runtime

    source = _harness(tmp_path, "full", ("s1", "s2"))
    _runtime, _canonical, trace_path = _fly(source, monkeypatch)
    run_id = "SAEA-TEST-RUN-001"
    _write_predecessor(
        _trace_lines(trace_path),
        tmp_path / "data" / "runs" / run_id / "attempt-aborted",
        run_id,
        keep={"s1"},
        truncate={"s2"},
    )
    runtime = _make_runtime(
        tmp_path,
        happy_path=True,
        config_kwargs={
            "policy": source.program.program_id,
            "baseline_extra": {"native_episode": _values(source)["native_episode"]},
        },
        resume_from={"attempt_id": "attempt-aborted", "trace_sha256": "0" * 64},
    )
    with pytest.raises(FlightRuntimeError, match="hashes to"):
        runtime.preflight()


def test_preflight_refuses_a_resume_on_a_dispatch_the_replay_cannot_read(
    tmp_path, monkeypatch
):
    """A policy whose rows carry no native episode receipt has no terminal
    custody in the trace, so a resume for it is refused by name rather than
    silently re-flying the whole roster."""

    from test_flight_runtime import _make_runtime

    runtime = _make_runtime(
        tmp_path,
        happy_path=True,
        config_kwargs={"policy": "fixed"},
        resume_from={"attempt_id": "attempt-aborted", "trace_sha256": "0" * 64},
    )
    with pytest.raises(FlightRuntimeError, match="does not produce one"):
        runtime.preflight()


def test_a_recovery_attempt_may_not_reuse_the_aborted_attempt_id(tmp_path):
    from test_flight_runtime import _make_runtime

    with pytest.raises(FlightRuntimeError, match="own new attempt id"):
        _make_runtime(
            tmp_path,
            happy_path=True,
            attempt_id="attempt-001",
            resume_from={"attempt_id": "attempt-001", "trace_sha256": "0" * 64},
        )


def test_resume_filtered_binding_narrows_the_flown_roster(tmp_path, monkeypatch):
    harness = _harness(tmp_path, "full", ("s1", "s2"))
    runtime = _skeleton(harness, monkeypatch)
    harness.close()
    binding = {
        "speech_packet_bindings": {"s1": {"packet_id": "p1"}, "s2": {"packet_id": "p2"}},
        "material_for_phase": harness.material_for_phase,
    }
    assert runtime._resume_filtered_binding(binding) is binding

    runtime._resume = object()
    runtime._resume_flown_sample_ids = ("s2",)
    narrowed = runtime._resume_filtered_binding(binding)
    assert set(narrowed["speech_packet_bindings"]) == {"s2"}
    assert narrowed["material_for_phase"] is binding["material_for_phase"]

    runtime._resume_flown_sample_ids = ("s2", "s9")
    with pytest.raises(FlightRuntimeError, match="no packet"):
        runtime._resume_filtered_binding(binding)
