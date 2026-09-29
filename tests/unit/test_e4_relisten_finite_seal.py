"""E4-1 seal abort regression: a finite-completion delivery followed by the
post-accept relisten stage's SHADOW contacts.

Cell E4-1 (``slurp-native-stage3-relisten-fold-a-v1``) flew all 1,080 rows and
aborted at seal with ``FlightRuntimeError: finite source is not the last actual
sample contact``: on 8 rows the finite-completion policy
(``deliver-latest-or-abstain``, item E13) delivered the latest Solver answer
after an interrupted Reviewer/Planner contact, and the relisten stage (owner
decision 185, ``rails.runner.run_relisten_stage``) then spent its own
blind/forced-choice contacts over that delivered answer. The seal compared the
finite source against the sample's LAST recorded contact, which was now a
shadow relisten contact.

The relisten stage is post-delivery SHADOW (design section 8, ruling 2: "The
delivered column stays the flight's normal answer"), so its contacts can never
move delivery. The seal therefore keeps the finite source as the last contact
that could move delivery, and admits after it exactly -- and only -- the row's
own sealed relisten receipt contacts.

The receipt lives only in memory until the seal writes it, so a seal-only
resume-recovery of E4-1 must re-derive it from the recorded relisten contacts
(``core.flight.resume`` + ``rails.relisten.replay_relisten_receipt``); the
replay test proves the replayed row is byte-identical to the live seal.

Zero model, real server, GPU or network contact: the fake transport of
``_ActualEpisodeHarness`` composes every response. No utterance text,
transcript, gold label or model output is printed or persisted.
"""

from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_e4_relisten_live import (
    _DELIVERED_ANSWER,
    _arm_relisten_request_gate,
    _relisten_config,
    _two_entity_output,
)
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_episode_runner import _ActualEpisodeHarness
from test_native_finite_outcome_integration import _finite_wire

from speech_aware_evidence_acquisition.core.bundle import BundleError
from speech_aware_evidence_acquisition.core.bundle.outputs import (
    _verify_outputs_trace_binding,
)
from speech_aware_evidence_acquisition.core.flight.resume import read_predecessor_attempt
from speech_aware_evidence_acquisition.core.flight.runtime import (
    FlightRuntime,
    FlightRuntimeError,
)
from speech_aware_evidence_acquisition.rails import relisten as rl
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

REPO_ROOT = Path(__file__).resolve().parents[2]
_MAX_SLOTS = 2


def _canonical_runtime(harness, summary, *, carry_relisten=True):
    runtime = object.__new__(FlightRuntime)
    runtime._composed = SimpleNamespace(values={"native_episode": {
        "finite_completion_policy": harness.config.finite_completion_policy,
        "exhaustion_policy": "raise", "max_revisions": 0,
        "actions": dict(zip(("accept", "revise", "acquire"), harness.config.actions)),
    }})
    runtime._plan = harness.plan
    runtime._phase_summaries = [summary]
    runtime._output_rows = [
        {
            "sample_id": row.sample_id,
            "final_response_text": row.final_response_text,
            "native_episode_receipt": row.native_episode_receipt,
            **(
                {"relisten": dict(row.relisten)}
                if carry_relisten and row.relisten is not None else {}
            ),
        }
        for row in summary.results
    ]
    runtime._result_kind = lambda: "answer"
    runtime._arm = lambda: harness.client.arm
    return runtime


def _run_finite_then_relisten(tmp_path, monkeypatch):
    """One row: Perception, Solver (a two-entity SLU answer), a Reviewer
    tool turn, then a Reviewer turn that stops on ``finish_reason=length``
    -- the finite completion that delivers the latest Solver answer -- and
    then the relisten stage's 2 blind + 2 confirm shadow contacts."""

    _finite_wire(monkeypatch, "reviewer")
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0,
        max_contacts=5 + rl.relisten_extra_ceiling(_MAX_SLOTS),
        planner_actions=("ACCEPT",), reviewer_task_tool=True,
    )
    harness.config = replace(
        harness.config,
        finite_completion_policy="deliver-latest-or-abstain",
        relisten_json=_relisten_config(_MAX_SLOTS).as_json(),
    )
    harness.repo_root = REPO_ROOT
    sample_id = harness.samples[0].sample_id
    relisten_output = _two_entity_output(sample_id)
    base_output = harness._output

    def output(key):
        if key[1] in {"solver", "relisten-blind", "relisten-confirm"}:
            return relisten_output(key)
        return base_output(key)

    harness._output = output
    _arm_relisten_request_gate(harness)
    try:
        summary = harness.run()
    except BaseException:
        harness.close()
        raise
    return harness, summary


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_finite_delivery_followed_by_relisten_shadow_contacts_seals(tmp_path, monkeypatch):
    harness, summary = _run_finite_then_relisten(tmp_path, monkeypatch)
    try:
        runtime = _canonical_runtime(harness, summary)
        # Before the fix this raised "finite source is not the last actual
        # sample contact" -- the exact E4-1 seal abort.
        outputs = runtime._canonical_output_rows(harness.client)
        timings = list(harness.client.timings)
    finally:
        harness.close()

    (result,) = summary.results
    receipt = result.native_episode_receipt
    # The row really is the E4-1 shape: a finite delivery of the latest
    # Solver answer, and relisten contacts recorded AFTER the finite source.
    assert receipt["terminal_disposition"]["reason"] == "finite_completion"
    assert "accepted_solver_receipt" not in receipt
    source_id = receipt["interrupted_role"]["execution_receipt"]["final_contact"]["request_id"]
    shadow_ids = rl.relisten_contact_request_ids(result.relisten)
    assert len(shadow_ids) == result.relisten["contacts_used"] == 4
    order = [timing.request_id for timing in timings]
    assert order[-1] != source_id
    assert order[order.index(source_id) + 1:] == list(shadow_ids)

    # Shadow delivery: the sealed row is the delivered Solver answer, bound
    # to the terminal Solver's own contact -- never a relisten contact.
    (row,) = outputs
    assert result.final_response_text == row["text"] == _DELIVERED_ANSWER
    assert row["request_id"] == receipt["terminal_solver_receipt"]["final_contact"]["request_id"]
    assert row["request_id"] not in shadow_ids
    assert row["relisten"] == result.relisten

    # I7 and I7l still hold over the sealed row and its own trace.
    records = {rid: payload for _, rid, payload in harness.trace.records}
    _verify_outputs_trace_binding(tuple(outputs), records)
    forged = copy.deepcopy(outputs)
    forged[0]["relisten"]["contacts_used"] = 3
    with pytest.raises(BundleError):
        _verify_outputs_trace_binding(tuple(forged), records)


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_finite_source_still_refuses_contacts_no_relisten_receipt_explains(tmp_path, monkeypatch):
    harness, summary = _run_finite_then_relisten(tmp_path, monkeypatch)
    try:
        # Without the row's relisten receipt the four trailing contacts are
        # unexplained: they are "actual sample contacts" after the source.
        runtime = _canonical_runtime(harness, summary, carry_relisten=False)
        with pytest.raises(
            FlightRuntimeError, match="finite source is not the last actual sample contact",
        ):
            runtime._canonical_output_rows(harness.client)

        # A receipt that names only part of the trailing contacts still
        # leaves an unexplained contact after the source.
        runtime = _canonical_runtime(harness, summary)
        partial = copy.deepcopy(runtime._output_rows[0]["relisten"])
        partial["entities"] = partial["entities"][:1]
        runtime._output_rows[0] = {**runtime._output_rows[0], "relisten": partial}
        with pytest.raises(
            FlightRuntimeError, match="finite source is not the last actual sample contact",
        ):
            runtime._canonical_output_rows(harness.client)

        # A receipt that names a contact which does not follow the source
        # (here: the source itself) is refused as well.
        runtime = _canonical_runtime(harness, summary)
        receipt = summary.results[0].native_episode_receipt
        source_id = receipt["interrupted_role"]["execution_receipt"]["final_contact"]["request_id"]
        misplaced = copy.deepcopy(runtime._output_rows[0]["relisten"])
        misplaced["entities"][0]["blind"]["contact_id"] = source_id
        runtime._output_rows[0] = {**runtime._output_rows[0], "relisten": misplaced}
        with pytest.raises(FlightRuntimeError):
            runtime._canonical_output_rows(harness.client)
    finally:
        harness.close()


def _write_trace(harness, directory: Path, *, drop_request_ids=()) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{harness.plan.run_id}.trace.jsonl"
    lines = [
        json.dumps({"channel": channel, "record_id": record_id, "payload": payload},
                   ensure_ascii=False, sort_keys=True)
        for channel, record_id, payload in harness.trace.records
        if record_id.split("/")[0] not in drop_request_ids
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return path


def _scan(harness, path: Path, *, relisten):
    return read_predecessor_attempt(
        run_id=harness.plan.run_id, attempt_id="attempt-aborted",
        attempt_dir=path.parent, program_id=harness.program.program_id,
        relisten=relisten,
    )


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_resume_replay_re_derives_the_relisten_receipt_and_seals_byte_identically(
    tmp_path, monkeypatch,
):
    """A seal-only recovery of E4-1 replays every row from the aborted trace.
    The receipt lived only in memory, so the replay must re-derive it from the
    recorded relisten contacts -- and the replayed row must be byte-identical
    to the row the live seal renders (finite source + trailing shadow
    contacts included)."""

    harness, summary = _run_finite_then_relisten(tmp_path, monkeypatch)
    try:
        runtime = _canonical_runtime(harness, summary)
        live_rows = runtime._canonical_output_rows(harness.client)
        path = _write_trace(harness, tmp_path / "aborted")
        (result,) = summary.results
        relisten_ids = rl.relisten_contact_request_ids(result.relisten)

        scan = _scan(harness, path, relisten=json.loads(_relisten_config(_MAX_SLOTS).as_json()))
        assert scan.incomplete == {}
        (sample_id,) = scan.complete_sample_ids
        replayed = scan.complete[sample_id]
        assert replayed.relisten == result.relisten
        # Live ``contacts`` never names a relisten contact; the replay agrees.
        assert [c.request_id for c in replayed.contacts] == [
            c.request_id for c in scan.contacts[sample_id] if c.request_id not in relisten_ids
        ]
        assert FlightRuntime._result_contact_count(replayed) == len(scan.contacts[sample_id])
        summaries, timings = scan.replay([sample_id], controller_policy_id="p")
        rows = FlightRuntime._rows_from_phase_summaries(
            summaries, policy=harness.program.program_id,
        )
        assert rows[0]["relisten"] == result.relisten
        rendered = runtime._canonical_output_rows(
            harness.client, output_rows=rows, timings=timings, phase_summaries=summaries,
        )
        assert [json.dumps(row, sort_keys=True) for row in rendered] == [
            json.dumps(row, sort_keys=True) for row in live_rows
        ]

        # Unarmed replay of a trace that records relisten contacts: re-fly.
        unarmed = _scan(harness, path, relisten=None)
        assert unarmed.complete == {}
        assert "declares no native_episode.relisten" in unarmed.incomplete[sample_id]

        # A recorded relisten contact missing from the trace: re-fly.
        short = _write_trace(harness, tmp_path / "short", drop_request_ids={relisten_ids[-1]})
        partial = _scan(harness, short, relisten=_relisten_config(_MAX_SLOTS))
        assert partial.complete == {}
        assert "relisten receipt cannot be re-derived" in partial.incomplete[sample_id]
    finally:
        harness.close()


def test_relisten_contact_request_ids_reads_blind_and_fired_confirm_contacts():
    receipt = {
        "schema": rl.RELISTEN_RECEIPT_SCHEMA,
        "entities": [
            {"blind": {"contact_id": "flight-0010"}, "confirm": {"contact_id": "flight-0011"}},
            {"blind": {"contact_id": "flight-0012"}, "confirm": None},
        ],
    }
    assert rl.relisten_contact_request_ids(receipt) == (
        "flight-0010", "flight-0011", "flight-0012",
    )
    assert rl.relisten_contact_request_ids(None) == ()
    for bad in (
        {"entities": "x"},
        {"entities": [{"blind": None}]},
        {"entities": [{"blind": {"contact_id": ""}}]},
        {"entities": [{"blind": {"contact_id": "a"}, "confirm": {"contact_id": 3}}]},
        {"entities": [{"blind": {"contact_id": "a"}}, {"blind": {"contact_id": "a"}}]},
    ):
        with pytest.raises(rl.RelistenError):
            rl.relisten_contact_request_ids(bad)
