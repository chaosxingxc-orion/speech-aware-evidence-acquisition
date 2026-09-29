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
    MergedPredecessors,
    ResumeDeclaration,
    ResumeRecoveryError,
    kept_sample_ids_sha256,
    read_predecessor_attempt,
)
from speech_aware_evidence_acquisition.core.flight.runtime import (
    FlightRuntime,
    FlightRuntimeError,
)
from speech_aware_evidence_acquisition.rails.runner import RailsRunnerError

from test_native_episode_runner import _ActualEpisodeHarness
from test_rails_frozen_core_client import _plan
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
    # E10b: the same starting state FlightRuntime.__init__ gives a flight that
    # is not a recovery -- no prepared-artifact identity is widened.
    runtime._identity_packet_bindings = None
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


def _harness(tmp_path, name, sample_ids, *, max_revisions=0, planned_model_calls=None):
    """One roster's worth of the actual episode, in its own directory.

    ``planned_model_calls`` overrides the harness default (whole roster x
    ``max_contacts``) so a recovery can carry a plan sized to the rows IT
    flies -- the budget shape E10c is about.
    """

    max_contacts = 4 + 3 * max_revisions
    return _ActualEpisodeHarness(
        tmp_path / name,
        sample_count=len(sample_ids),
        sample_ids=tuple(sample_ids),
        max_revisions=max_revisions,
        max_contacts=max_contacts,
        planner_actions=("ACCEPT",) if max_revisions == 0 else ("REVISE", "ACCEPT"),
        arm="speech-feature-query",
        **(
            {}
            if planned_model_calls is None
            else {
                "execution_plan": _plan(
                    run_id="SAEA-E-native-role-runner-proof",
                    attempt_id="attempt-native-role-runner-proof",
                    planned_model_calls=planned_model_calls,
                )
            }
        ),
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
    recovery_runtime._resume = MergedPredecessors((scan,))
    recovery_runtime._resume_flown_sample_ids = ("s2",)
    try:
        rows, *_ = recovery_runtime._dispatch_phase_program(
            recovery.client, recovery.plan, recovery.program.program_id
        )
    finally:
        recovery.close()
    recovery_runtime._output_rows = rows
    recovery_runtime._client = recovery.client

    merged, block, _seal_only_results = recovery_runtime._merged_canonical_rows()
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


def _annotate_receipts(records, mutate) -> list[dict]:
    for record in records:
        if record["channel"] == "USE" and record["record_id"].endswith("/native-episode"):
            mutate(record["payload"]["use_native_episode"])
    return records


def test_receipt_annotation_blocks_are_not_claimed_as_wire_contacts(tmp_path, monkeypatch):
    """2026-09-28 (the COMP-1 arm abort): a receipt carrying the context-fit
    and the cited-answer annotation blocks -- whose ``contacts`` rows are keyed
    by the agent contact id and carry no request id -- must still classify a
    settled row COMPLETE. Before the fix every such row read "names contact
    None" and a resume kept nothing."""

    def annotate(receipt):
        receipt["context_fit"] = {
            "contacts": [{"contact_id": "c-1", "role_id": "solver", "context_compaction": None}],
        }
        receipt["solver_citations"] = {
            "schema": "saea-solver-citations-v1",
            "contacts": [{"contact_id": "c-1", "role_id": "solver", "parse": "ok"}],
        }

    harness = _harness(tmp_path, "full", ("s1", "s2"))
    _runtime, _canonical, trace_path = _fly(harness, monkeypatch)
    records = _annotate_receipts(_trace_lines(trace_path), annotate)
    predecessor = _write_predecessor(
        records, tmp_path / "aborted", harness.plan.run_id, keep={"s1", "s2"},
    )
    scan = _scan(predecessor, harness)
    assert scan.complete_sample_ids == ("s1", "s2")
    assert scan.incomplete == {}


def test_a_claimed_wire_contact_without_a_request_record_still_refuses_the_row(
    tmp_path, monkeypatch
):
    """The skip is by block name, never by shape: a wire-contact array that
    names a request the trace does not carry still makes the row INCOMPLETE."""

    def annotate(receipt):
        receipt["solver_citations"] = {"contacts": [{"contact_id": "c-1"}]}
        receipt["unregistered_block"] = {"contacts": [{"request_id": "no-such-request"}]}

    harness = _harness(tmp_path, "full", ("s1",))
    _runtime, _canonical, trace_path = _fly(harness, monkeypatch)
    records = _annotate_receipts(_trace_lines(trace_path), annotate)
    predecessor = _write_predecessor(
        records, tmp_path / "aborted", harness.plan.run_id, keep={"s1"},
    )
    scan = _scan(predecessor, harness)
    assert scan.complete_sample_ids == ()
    assert "no-such-request" in scan.incomplete["s1"]


_TEST_NORMALISER_ID = "test-resume-deliver-upper-v1"


def _upper_normaliser(text):
    return SimpleNamespace(text=text.upper(), changed=text.upper() != text)


def _normalised_predecessor(tmp_path, monkeypatch, *, corrupt_output=False):
    """Fly the actual episode, then give every settled receipt the E11
    ``deliver_normaliser`` block a live normalised row carries: the rule's
    input is the delivered contact's recorded response and its output is
    what the row delivered. Exactly the COMP-1 shape (every kept row
    normalised by saea-deliver-cited-answer-normalise-v3-v1)."""

    import hashlib  # noqa: PLC0415

    from speech_aware_evidence_acquisition.core.base import (  # noqa: PLC0415
        DELIVERY_NORMALISERS,
    )

    monkeypatch.setitem(
        DELIVERY_NORMALISERS._entries, _TEST_NORMALISER_ID, _upper_normaliser
    )
    digest = lambda text: hashlib.sha256(text.encode("utf-8")).hexdigest()  # noqa: E731
    harness = _harness(tmp_path, "full", ("s1", "s2"))
    runtime, _canonical, trace_path = _fly(harness, monkeypatch)
    records = _trace_lines(trace_path)
    texts = {
        record["record_id"][: -len("/response")]: record["payload"]["text"]
        for record in records
        if record["channel"] == "MODEL_RESPONSE" and record["record_id"].endswith("/response")
    }

    def annotate(receipt):
        request_id = receipt["accepted_solver_receipt"]["final_contact"]["request_id"]
        raw = texts[request_id]
        receipt["deliver_normaliser"] = {
            "normaliser_id": _TEST_NORMALISER_ID,
            "input_sha256": digest(raw),
            "output_sha256": digest("corrupt" if corrupt_output else raw.upper()),
        }

    predecessor = _write_predecessor(
        _annotate_receipts(records, annotate), tmp_path / "aborted",
        harness.plan.run_id, keep={"s1", "s2"},
    )
    return harness, runtime, predecessor


def test_a_normalised_row_replays_the_normaliser_output_not_the_raw_response(
    tmp_path, monkeypatch
):
    """2026-09-29 (COMP-1 resume attempt 3 seal abort): every kept row carried
    a ``deliver_normaliser`` block, and the replay handed the seal the RAW
    accepted response as the delivered text, so ``_canonical_output_rows``
    refused the first kept row with "native delivery normalisation output
    differs from the delivered text" after all 609 flown rows had settled.
    The replay must deliver the rule's reproduced output, and the canonical
    seal stage must accept the replayed rows."""

    harness, runtime, predecessor = _normalised_predecessor(tmp_path, monkeypatch)
    scan = _scan(predecessor, harness)
    assert scan.complete_sample_ids == ("s1", "s2")
    for sample_id in ("s1", "s2"):
        delivered = scan.complete[sample_id].final_response_text
        assert delivered == delivered.upper()
        assert delivered.startswith("SOLVER-ANSWER:")

    summaries, timings = scan.replay(scan.complete_sample_ids, controller_policy_id="p")
    replayed_rows = FlightRuntime._rows_from_phase_summaries(
        summaries, policy=harness.program.program_id
    )
    sealed = runtime._canonical_output_rows(
        harness.client, output_rows=replayed_rows, timings=timings,
        phase_summaries=summaries,
    )
    assert [row["text"] for row in sealed] == [
        f"solver-answer:{sample}:visit:1".upper() for sample in ("s1", "s2")
    ]


def test_a_normalised_row_whose_rule_does_not_reproduce_is_re_flown(
    tmp_path, monkeypatch
):
    """The replay never approximates: when the named rule, re-run over the
    recorded response, does not reproduce the recorded output digest, the row
    is INCOMPLETE (re-flown), never kept with the raw text."""

    harness, _runtime, predecessor = _normalised_predecessor(
        tmp_path, monkeypatch, corrupt_output=True,
    )
    scan = _scan(predecessor, harness)
    assert scan.complete_sample_ids == ()
    assert "does not reproduce its recorded output" in scan.incomplete["s1"]


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
    recovery_runtime._resume = MergedPredecessors((scan,))
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
# ---------------------------------------------------------------------------
# E10b (2026-09-18): a prepared artifact is verified over the WHOLE roster.
# ---------------------------------------------------------------------------


def _supplied_skeleton(harness, monkeypatch):
    """The same skeleton, for a cell whose FIRST phase carries phase supply.

    The cell shape the first resume-recovery flight actually aborted on: a
    ``prepared_phase_supply`` pin plus the frozen source receipts every
    prepared artifact's identity embeds.
    """

    import hashlib

    runtime = _skeleton(harness, monkeypatch)
    runtime._repo_root = harness.world.data_root
    receipt = harness.world.data_root / "e10b-frozen-source.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_bytes(b"E10b frozen source receipt")
    runtime._composed.values["preparation_source_receipts"] = [
        {
            "root": "data",
            "relpath": receipt.name,
            "sha256": hashlib.sha256(receipt.read_bytes()).hexdigest(),
        }
    ]
    spec = SimpleNamespace(
        phase=harness.program.phase_names()[0],
        query_source={},
        as_json=lambda: {"provider": "kb-facet-v1", "k": 1},
    )
    runtime._phase_program_material = {
        **runtime._phase_program_material,
        "supply_specs": {spec.phase: spec},
    }
    return runtime, spec


_PREPARED_RELPATH = "prepared/phase-supply-v1.json"


def _prepare_supply_artifact(runtime, spec):
    """Prepare the first-phase selection over the WHOLE roster and pin it.

    This is what ``core.flight.repin`` does for a real cell: the artifact is
    produced, and later re-verified, over every row of the cell's roster --
    never over the subset one attempt happens to fly.
    """

    from speech_aware_evidence_acquisition.core.preparation import prepare_artifact

    binding = runtime._phase_program_material
    roster = sorted(binding["speech_packet_bindings"])
    path = runtime._data_root / _PREPARED_RELPATH
    path.parent.mkdir(parents=True, exist_ok=True)
    inputs = runtime._phase_seed_inputs(
        binding, spec, runtime._plan.split_identity_hash
    )
    selection = {
        "facets": {spec.phase: {sample_id: ["operation:dim"] for sample_id in roster}},
        "values": {
            spec.phase: {sample_id: ["value:dim-light"] for sample_id in roster}
        },
    }
    receipt = prepare_artifact(
        path, kind="phase-supply", inputs=inputs, producer=lambda: selection
    )
    runtime._composed.values["prepared_phase_supply"] = {
        "relpath": _PREPARED_RELPATH,
        "sha256": receipt["sha256"],
    }
    return receipt


def test_a_resume_loads_a_prepared_supply_prepared_over_the_whole_roster(
    tmp_path, monkeypatch
):
    """E10b, the defect this fix exists for.

    The first resume-recovery flight (2026-09-18) passed preflight, preprocess
    and serve and then died in ``run_phases`` with ZERO contacts:
    ``core.preparation.load_artifact`` refused with "prepared artifact
    identity mismatch", because the resume narrowing had already replaced the
    binding's 1,080-row packet map with the 500 rows the recovery was to fly,
    and the prepared artifact's identity embeds the packet map of the roster
    it was prepared over.

    Here the artifact is prepared over BOTH rows, the aborted attempt covers
    one of them, and the recovery must load the artifact unchanged, seed only
    the row it flies, and seal a kept row byte identical to the uninterrupted
    one.

    E10c (2026-09-18) makes this the whole real path: no roster is narrowed
    inside the test any more. The recovery's adapter carries the cell's whole
    split, ``FlightRuntime._dispatch_phase_program`` hands the runner the
    flown roster explicitly, and the run therefore exercises every roster
    assertion between the dispatch and the seal -- the packet-binding
    assertion, the contact ceiling against a plan sized to the flown rows,
    and the merged seal over the whole roster.
    """

    roster = ("s1", "s2")
    source = _harness(tmp_path, "full", roster)
    source_runtime, source_spec = _supplied_skeleton(source, monkeypatch)
    source_receipt = _prepare_supply_artifact(source_runtime, source_spec)
    try:
        rows, *_ = source_runtime._dispatch_phase_program(
            source.client, source.plan, source.program.program_id
        )
    finally:
        source.close()
    source_runtime._output_rows = rows
    canonical = source_runtime._canonical_output_rows(source.client)
    full_rows = {row["sample_id"]: row for row in canonical}
    assert set(full_rows) == set(roster)
    trace_path = source.world.run_dir / f"{source.plan.run_id}.trace.jsonl"

    predecessor = _write_predecessor(
        _trace_lines(trace_path), tmp_path / "aborted", source.plan.run_id,
        keep={"s1"}, truncate={"s2"},
    )
    scan = _scan(predecessor, source)
    assert scan.complete_sample_ids == ("s1",)

    # The recovery attempt carries the SAME cell -- same roster, same prepared
    # artifact bytes -- and flies only the row the predecessor did not finish.
    # Its plan is sized to the rows IT flies (E10c): one row at the program's
    # contact ceiling, which is exactly half of what the whole roster would
    # need. That is what makes this test a ceiling proof -- a dispatch that
    # took its roster from ``adapter.load_split`` would compute
    # ``planned_ceiling = 2 x max_contacts`` and refuse against this budget.
    recovery = _harness(
        tmp_path, "recovery", roster,
        planned_model_calls=source.program.max_contacts,
    )
    recovery_runtime, recovery_spec = _supplied_skeleton(recovery, monkeypatch)
    recovery_receipt = _prepare_supply_artifact(recovery_runtime, recovery_spec)
    assert recovery_receipt["sha256"] == source_receipt["sha256"]
    recovery_runtime._samples = tuple(
        SimpleNamespace(sample_id=sample_id) for sample_id in roster
    )
    recovery_runtime._resume = MergedPredecessors((scan,))
    recovery_runtime._resume_flown_sample_ids = ("s2",)
    # E10c: the adapter stays WHOLE. The flown roster reaches the runner as an
    # explicit restriction instead, so the split it loads, the packet map it
    # asserts over and the ceiling it charges are one roster -- and the
    # prepared artifact is still verified over the cell's whole roster.
    assert recovery_runtime._adapter is recovery.adapter
    assert len(recovery.adapter.load_split("all")) == len(roster)
    assert recovery_runtime._resume_dispatch_roster() == ("s2",)
    try:
        rows, *_ = recovery_runtime._dispatch_phase_program(
            recovery.client, recovery.plan, recovery.program.program_id
        )
    finally:
        recovery.close()
    recovery_runtime._output_rows = rows
    recovery_runtime._client = recovery.client

    # The dispatch flew ONLY the unfinished row, while the artifact was
    # verified against the whole roster it was prepared over.
    assert [row["sample_id"] for row in rows] == ["s2"]
    assert set(recovery_runtime._identity_packet_bindings) == set(roster)
    # E10c, the ceiling: the flight ran under a plan that covers exactly one
    # row at the program's contact ceiling, and every contact it spent was
    # charged against it.
    assert recovery.plan.planned_model_calls == 1 * recovery.program.max_contacts
    assert 0 < len(recovery.client.timings) <= recovery.plan.planned_model_calls

    # And the seed the recovery actually handed the runner is narrowed to the
    # flown row: rails.runner._per_sample_bootstrap refuses a seed that names
    # a sample outside the flown split, so a wide seed would have aborted the
    # flight above.
    narrowed = recovery_runtime._resume_filtered_binding(
        recovery_runtime._phase_program_material
    )
    facet_seed, value_seed = recovery_runtime._phase_supply_seeds(
        recovery.program, narrowed, {recovery_spec.phase: recovery_spec},
        recovery.plan,
    )
    assert set(value_seed[recovery_spec.phase]) == {"s2"}
    assert set(facet_seed[recovery_spec.phase]) == {"s2"}
    assert value_seed[recovery_spec.phase]["s2"] == ("value:dim-light",)

    merged, block, _seal_only_results = recovery_runtime._merged_canonical_rows()
    assert [row["sample_id"] for row in merged] == list(roster)
    assert json.dumps(merged[0], sort_keys=True) == json.dumps(
        full_rows["s1"], sort_keys=True
    )
    assert merged[1]["text"] == full_rows["s2"]["text"]
    assert block["counts"] == {"kept": 1, "flown": 1, "partial": 1}


def test_phase_seed_inputs_are_invariant_under_a_resume(tmp_path, monkeypatch):
    """E10b rule 1, stated as an assertion: identity never moves.

    The resume narrowing applies to what is DISPATCHED, never to what is
    VERIFIED. So one binding yields one set of prepared-artifact inputs
    whether or not this attempt is a recovery, and the narrowed binding is
    verified against the whole roster rather than against itself.
    """

    harness = _harness(tmp_path, "full", ("s1", "s2"))
    runtime, spec = _supplied_skeleton(harness, monkeypatch)
    harness.close()
    binding = runtime._phase_program_material
    identity = harness.plan.split_identity_hash
    ordinary = runtime._phase_seed_inputs(binding, spec, identity)
    assert ordinary["sources"]["packets"] == dict(harness.speech_bindings)
    assert runtime._identity_packet_bindings is None

    runtime._resume = object()
    runtime._resume_flown_sample_ids = ("s2",)
    narrowed = runtime._resume_filtered_binding(binding)
    assert set(narrowed["speech_packet_bindings"]) == {"s2"}

    # (a) An ordinary cell's identity does not move because a resume exists.
    assert runtime._phase_seed_inputs(binding, spec, identity) == ordinary
    # (b) The narrowed dispatch binding is verified over the whole roster.
    assert runtime._phase_seed_inputs(narrowed, spec, identity) == ordinary
    # Not vacuous: the packet map is what the two bindings disagree about.
    assert set(narrowed["speech_packet_bindings"]) != set(
        binding["speech_packet_bindings"]
    )


# ---------------------------------------------------------------------------
# E10c (2026-09-18): the runner's own roster is the flown one.
# ---------------------------------------------------------------------------


def test_the_runner_refuses_a_flown_row_that_the_split_does_not_carry(
    tmp_path, monkeypatch
):
    """A flown id outside the split refuses BY NAME, with zero contacts.

    The restriction can only ever narrow: a row the adapter's split does not
    carry is not something a recovery may fly, and saying so here -- rather
    than letting the packet assertion report a count mismatch -- is what
    keeps a mis-declared resume readable.
    """

    recovery = _harness(tmp_path, "recovery", ("s1", "s2"))
    runtime = _skeleton(recovery, monkeypatch)
    runtime._samples = tuple(
        SimpleNamespace(sample_id=sample_id) for sample_id in ("s1", "s2")
    )
    runtime._resume = object()
    runtime._resume_flown_sample_ids = ("s2",)
    # The cell's split lost the row this recovery says it must fly.
    runtime._adapter = type(recovery.adapter)(
        samples=tuple(
            sample for sample in recovery.samples if sample.sample_id == "s1"
        )
    )
    try:
        with pytest.raises(RailsRunnerError, match="outside split"):
            runtime._dispatch_phase_program(
                recovery.client, recovery.plan, recovery.program.program_id
            )
    finally:
        recovery.close()
    assert recovery.client.timings == ()


def test_the_runner_restriction_is_absent_without_a_resume(tmp_path, monkeypatch):
    """Rule 1's other half: an ordinary flight hands the runner nothing.

    ``flown_sample_ids`` is optional and the ordinary path never sets it, so
    an uninterrupted flight loads the whole split exactly as it did before
    this seam existed.
    """

    harness = _harness(tmp_path, "full", ("s1", "s2"))
    runtime = _skeleton(harness, monkeypatch)
    assert runtime._resume_dispatch_roster() is None
    seen = {}

    def spy(**kwargs):
        seen.update(kwargs)
        raise RuntimeError("stop before any contact")

    runtime._continuous_phase_runner = spy
    try:
        with pytest.raises(RuntimeError, match="stop before any contact"):
            runtime._dispatch_phase_program(
                harness.client, harness.plan, harness.program.program_id
            )
    finally:
        harness.close()
    assert "flown_sample_ids" not in seen
    assert set(seen["speech_packet_bindings"]) == {"s1", "s2"}
    assert seen["adapter"] is harness.adapter
    assert harness.client.timings == ()


def test_the_phase_runner_refuses_a_roster_that_differs_from_its_packet_map(tmp_path):
    """One dispatch flies one roster.

    ``rails.phase_runner`` validates its results against
    ``speech_packet_bindings`` while ``rails.runner`` validates the split
    against ``flown_sample_ids``; letting the two disagree would reintroduce
    exactly the defect E10c fixes, so the disagreement refuses before the
    loop is entered.
    """

    from speech_aware_evidence_acquisition.rails.phase_runner import (
        PhaseRunnerError,
        run_continuous_program,
    )

    harness = _harness(tmp_path, "full", ("s1", "s2"))
    # ``solo`` is the plain one-phase form: this proof is about the roster
    # arguments, not about the native episode's own custody.
    program = harness.program.solo(harness.program.phase_names()[0])
    try:
        with pytest.raises(PhaseRunnerError, match="same rows"):
            run_continuous_program(
                program=program,
                adapter=harness.adapter,
                plan=harness.plan,
                data_root=harness.world.data_root,
                core_client=harness.client,
                split_id="all",
                knowledge_snapshot=_knowledge_snapshot(),
                speech_packet_bindings=dict(harness.speech_bindings),
                trace_sink=harness.trace,
                decoding_params={"temperature": 0, "max_tokens": 64},
                material_for_phase=harness.material_for_phase,
                flown_sample_ids=("s2",),
                agent_runner=lambda **_kwargs: pytest.fail(
                    "the loop must not be entered"
                ),
            )
    finally:
        harness.close()
    assert harness.client.timings == ()
