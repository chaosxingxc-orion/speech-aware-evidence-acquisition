"""NX-T R1 seal fix (2026-10-15): a NON-delivering level-2 branch whose Solver contact ends on a finite completion is RECORDED, not fatal.

The incident (docs/readiness/2026-10-13-slurp-nxt-r1-thinking-policy-fold-b-v1-sealonly-v1/README.md): in the NX-T R1 column flight one
row's ``both-off`` Solver contact (no thinking, ``enable_thinking`` false) ran to the 4,096-token cap and ended with ``finish_reason``
``length``. ``FrozenCoreRoleFiniteCompletionError`` left the whole Solver fan-out, so the delivering arm (A, invoked LAST) never ran, the
row's episode ended on its finite-completion disposition, and the final assembly raised ``perception branch 'both-off' sealed no level-2
Solver column`` -- stopping a 1,030-row flight.

These proofs are model-free (fake transports only). Layers: 1. the receipt (optional ``solver_absent`` / ``absent_reason``, old receipts
unchanged); 2. the fan-out seam (non-delivering absorbed, delivering fail-closed); 3. the production graph and the bundle verifier; 4. the
column renderer (absent column = canonical empty answer, counted).
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
    PERCEPTION_BRANCH_ABSENT_FIELDS,
    PERCEPTION_BRANCH_ABSENT_REASONS,
    validate_perception_branch_receipt,
)
from speech_aware_evidence_acquisition.rails.supply_variants import (
    PerceptionBranchError,
    perception_branch_receipt,
    perception_branch_record,
)
from speech_aware_evidence_acquisition.reproduction.ojw.native_roles import FrozenCoreRoleFiniteCompletionError
from speech_aware_evidence_acquisition.reproduction.ojw.native_supply_variants import (
    SupplyVariantNodeError,
    run_perception_branch_solver_arms,
)

from test_thinking_policy_column import _group

LENGTH = "finite-completion:length"
ARM_IDS = ("perception-off", "solver-off", "both-off", "both-on-twin", "both-on")


def _digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


# ---------------------------------------------------------------------------
# 1. The receipt
# ---------------------------------------------------------------------------


def _rows(group, *, absent=()):
    rows = []
    for index, branch in enumerate(group.branches):
        digest = _digest(f"note-{index}")
        rows.append(perception_branch_record(
            branch=branch, branch_index=index, contact_id=f"c{index}", request_sha256=digest, response_text_sha256=digest,
            note_sha256=digest, note_parse_status="malformed", candidate_intent_ids=(), supplied_value_ids=(),
            solver_contact_id=f"s{index}", solver_request_sha256=digest, solver_response_text_sha256=digest,
            candidate_supply_value_ids=(), thinking_group=True,
            solver_absent=branch.branch_id in absent, absent_reason=LENGTH if branch.branch_id in absent else None,
        ))
    return rows


def _validate(block, group):
    validate_perception_branch_receipt(
        block, branch_ids=list(group.branch_ids), delivered_branch_id="both-on", twin_branch_id="both-on-twin",
        phase_id="perception", level=2,
    )


def test_an_absent_row_names_its_real_contact_and_gains_exactly_two_keys():
    group = _group()
    rows = _rows(group, absent=("both-off",))
    absent, present = rows[2], rows[0]
    assert absent["solver_absent"] is True and absent["absent_reason"] == LENGTH
    assert set(absent) - set(present) == set(PERCEPTION_BRANCH_ABSENT_FIELDS)
    assert absent["solver_contact_id"] == "s2" and len(absent["solver_request_sha256"]) == 64
    assert not (set(PERCEPTION_BRANCH_ABSENT_FIELDS) & set(present))                # a present row is byte-identical to before
    block = perception_branch_receipt(group=group, phase_id="perception", records=rows)
    _validate(block, group)
    assert block["schema"] == "saea-perception-branch-arms-v5"                   # no schema bump


def test_a_receipt_without_any_absent_key_still_validates_unchanged():
    group = _group()
    block = perception_branch_receipt(group=group, phase_id="perception", records=_rows(group))
    assert not any(set(PERCEPTION_BRANCH_ABSENT_FIELDS) & set(row) for row in block["branches"])
    _validate(block, group)


def test_the_twin_and_every_candidate_may_be_absent_but_never_the_delivering_arm():
    group = _group()
    for arm in ("perception-off", "solver-off", "both-off", "both-on-twin"):
        _validate(perception_branch_receipt(group=group, phase_id="perception", records=_rows(group, absent=(arm,))), group)
    with pytest.raises(PerceptionBranchError, match="delivering branch"):
        _rows(group, absent=("both-on",))
    forged = perception_branch_receipt(group=group, phase_id="perception", records=_rows(group))
    forged["branches"][-1].update(solver_absent=True, absent_reason=LENGTH)
    with pytest.raises(ValueError, match="cannot have an absent Solver column"):
        _validate(forged, group)


@pytest.mark.parametrize("mutate, message", [
    (lambda row: row.pop("absent_reason"), "invalid shape"),
    (lambda row: row.pop("solver_absent"), "invalid shape"),
    (lambda row: row.update(solver_absent=False), "must be true"),
    (lambda row: row.update(absent_reason="whatever"), "absent_reason must be one of"),
    (lambda row: row.update(absent_reason=None), "absent_reason must be one of"),
])
def test_a_malformed_absent_mark_is_refused_by_name(mutate, message):
    group = _group()
    block = perception_branch_receipt(group=group, phase_id="perception", records=_rows(group, absent=("both-off",)))
    mutate(block["branches"][2])
    with pytest.raises(ValueError, match=message):
        _validate(block, group)


def test_the_absent_reasons_are_the_finite_completions_and_nothing_else():
    assert PERCEPTION_BRANCH_ABSENT_REASONS == {"finite-completion:length", "finite-completion:content_filter"}
    group = _group()
    with pytest.raises(PerceptionBranchError, match="absent_reason must be one of"):
        perception_branch_record(
            branch=group.branch("both-off"), branch_index=2, contact_id="c", request_sha256="1" * 64, response_text_sha256="1" * 64,
            note_sha256="1" * 64, note_parse_status="malformed", candidate_intent_ids=(), supplied_value_ids=(),
            solver_contact_id="s", solver_request_sha256="1" * 64, solver_response_text_sha256="1" * 64,
            candidate_supply_value_ids=(), thinking_group=True, solver_absent=True, absent_reason="no-solver-visit",
        )
    with pytest.raises(PerceptionBranchError, match="still name its Solver contact"):
        perception_branch_record(
            branch=group.branch("both-off"), branch_index=2, contact_id="c", request_sha256="1" * 64, response_text_sha256="1" * 64,
            note_sha256="1" * 64, note_parse_status="malformed", candidate_intent_ids=(), supplied_value_ids=(),
            thinking_group=True, solver_absent=True, absent_reason=LENGTH,
        )
    with pytest.raises(PerceptionBranchError, match="no solver_absent mark"):
        perception_branch_record(
            branch=group.branch("both-off"), branch_index=2, contact_id="c", request_sha256="1" * 64, response_text_sha256="1" * 64,
            note_sha256="1" * 64, note_parse_status="malformed", candidate_intent_ids=(), supplied_value_ids=(),
            solver_contact_id="s", solver_request_sha256="1" * 64, solver_response_text_sha256="1" * 64,
            candidate_supply_value_ids=(), thinking_group=True, absent_reason=LENGTH,
        )


def test_an_absent_mark_is_refused_at_level_one():
    group = _group()
    block = perception_branch_receipt(group=group, phase_id="perception", records=_rows(group, absent=("both-off",)))
    for row in block["branches"]:                     # make it a level-1 shape: no Solver-column fields
        for key in ("solver_contact_id", "solver_request_sha256", "solver_response_text_sha256", "candidate_supply_value_ids"):
            row.pop(key)
    block["level"] = 1
    with pytest.raises(ValueError, match="only at level 2"):
        validate_perception_branch_receipt(
            block, branch_ids=list(group.branch_ids), delivered_branch_id="both-on", twin_branch_id="both-on-twin",
            phase_id="perception", level=1,
        )


# ---------------------------------------------------------------------------
# 2. The fan-out seam
# ---------------------------------------------------------------------------


def _contact(index):
    return {
        "agent_contact_id": f"agent-{index}", "request_id": f"req-{index}", "request_sha256": _digest(f"rq{index}"),
        "response_sha256": _digest(f"rs{index}"), "response_text_sha256": _digest(f"rt{index}"),
    }


def _finite_error(index, *, receipt=True, reason="length"):
    completion = SimpleNamespace(
        request_sha256=_digest(f"rq{index}"), response_sha256=_digest(f"rs{index}"), response_text_sha256=_digest(f"rt{index}"),
    )
    error = FrozenCoreRoleFiniteCompletionError(completion=completion, finish_reason=reason, original_message={})
    error.role_id = "solver"
    error.execution_receipt = {"contacts": [_contact(index)], "final_contact": _contact(index)} if receipt else None
    return error


def _fan_out(*, fail=None, error=None, absent=True, receipt=True):
    group = _group()
    seen = {"records": [], "absent": []}

    async def invoke_branch(index):
        if fail == index:
            raise error if error is not None else _finite_error(index, receipt=receipt)
        contact = _contact(index)
        return {
            "role_id": "solver", "result_type": "answer", "actor_output": f"answer-{index}",
            "execution_receipt": {"contacts": [contact], "final_contact": contact},
        }

    def record(index, _result):
        seen["records"].append(index)
        return {"branch_id": group.branch_at(index).branch_id}

    def record_absent(index, failure):
        seen["absent"].append((index, type(failure).__name__))
        return {"branch_id": group.branch_at(index).branch_id}

    result = asyncio.run(run_perception_branch_solver_arms(
        invoke_branch, group=group, branch_record=record, branch_absent=record_absent if absent else None,
    ))
    return result, seen


def test_a_non_delivering_finite_completion_is_recorded_and_the_fan_out_continues():
    result, seen = _fan_out(fail=2)
    assert seen["absent"] == [(2, "FrozenCoreRoleFiniteCompletionError")]
    assert seen["records"] == [0, 1, 3, 4]                                  # the failed branch is not a normal record
    # The delivering arm (A) ran AFTER the failure and is the answer; the failed contact stays in the visit's contact list, in order.
    assert result["actor_output"] == "answer-4" and result["result_type"] == "answer"
    assert [c["agent_contact_id"] for c in result["execution_receipt"]["contacts"]] == [f"agent-{i}" for i in range(5)]
    assert result["execution_receipt"]["final_contact"]["agent_contact_id"] == "agent-4"


def test_every_non_delivering_branch_may_fail_at_once():
    group = _group()
    failing = {0, 1, 2, 3}

    async def invoke_branch(index):
        if index in failing:
            raise _finite_error(index)
        contact = _contact(index)
        return {"role_id": "solver", "result_type": "answer", "actor_output": "a", "execution_receipt": {"contacts": [contact], "final_contact": contact}}

    absent = []
    result = asyncio.run(run_perception_branch_solver_arms(
        invoke_branch, group=group, branch_record=lambda i, r: {"branch_id": group.branch_at(i).branch_id},
        branch_absent=lambda i, e: absent.append(i) or {"branch_id": group.branch_at(i).branch_id},
    ))
    assert absent == [0, 1, 2, 3] and len(result["execution_receipt"]["contacts"]) == 5


def test_without_the_seam_a_finite_completion_still_leaves_the_fan_out():
    with pytest.raises(FrozenCoreRoleFiniteCompletionError):
        _fan_out(fail=2, absent=False)


def test_the_delivering_arm_keeps_its_fail_closed_finite_completion():
    with pytest.raises(FrozenCoreRoleFiniteCompletionError):
        _fan_out(fail=4)                                                   # A, with the seam armed


def test_any_other_failure_on_a_non_delivering_branch_still_propagates():
    with pytest.raises(RuntimeError, match="transport down"):
        _fan_out(fail=1, error=RuntimeError("transport down"))


def test_a_finite_completion_without_its_execution_receipt_is_refused():
    with pytest.raises(SupplyVariantNodeError, match="without its execution receipt"):
        _fan_out(fail=2, receipt=False)


def test_the_absent_callback_must_name_the_branch():
    group = _group()

    async def invoke_branch(index):
        if index == 2:
            raise _finite_error(2)
        contact = _contact(index)
        return {"role_id": "solver", "result_type": "answer", "actor_output": "a", "execution_receipt": {"contacts": [contact], "final_contact": contact}}

    with pytest.raises(SupplyVariantNodeError, match="names another branch"):
        asyncio.run(run_perception_branch_solver_arms(
            invoke_branch, group=group, branch_record=lambda i, r: {"branch_id": group.branch_at(i).branch_id},
            branch_absent=lambda i, e: {"branch_id": "someone-else"},
        ))


# ---------------------------------------------------------------------------
# 3. The production graph and the bundle verifier
# ---------------------------------------------------------------------------

pytest.importorskip("openjiuwen", reason="OpenJiuwen unavailable")

import test_native_episode_runner as harness_module  # noqa: E402
from test_llama_server_transport import _spawn_live_matching_process  # noqa: E402,F401
from test_perception_branch_presentation_live import _intent_snapshot  # noqa: E402
from test_thinking_policy_column import (  # noqa: E402
    NO, ON, THINK_DECODING, _build, _wire,
)
from test_perception_template_variants import _requests_by_row  # noqa: E402

CAP = "LENGTH-CAP-MARKER:"


def _length_wire(real):
    def wire(text):
        if text.startswith(CAP):
            return json.dumps(
                {"choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": "length"}],
                 "usage": {"prompt_tokens": 7, "completion_tokens": 4096}},
                separators=(",", ":"),
            ).encode()
        return real(text)
    return wire


def _arm(tmp_path, monkeypatch, *, cap_row="s2", cap_turn=3):
    """The thinking-policy column on the fake world, with ONE Solver contact (``cap_row`` / ``cap_turn``) ending on ``length``."""

    monkeypatch.setattr(harness_module, "_wire_response", _length_wire(harness_module._wire_response))
    group, harness = _build(tmp_path, monkeypatch)
    base = harness._output

    def output(key):
        sample_id, phase, _visit, turn = key
        if sample_id == cap_row and phase == "solver" and turn == cap_turn:
            return f"{CAP}partial-{sample_id}"
        return base(key)

    harness._output = output
    return group, harness


def test_a_both_off_solver_that_hits_the_cap_is_recorded_and_the_row_still_delivers_its_arm(tmp_path, monkeypatch):
    group, harness = _arm(tmp_path / "armed", monkeypatch)
    try:
        summary = harness.run(snapshot=_intent_snapshot(), decoding_params=dict(THINK_DECODING))
        by_row = _requests_by_row(harness)
        assert len(summary.results) == 4
        for result in summary.results:
            sid = result.sample_id
            receipt = result.native_episode_receipt["perception_branches"]
            rows = {row["branch_id"]: row for row in receipt["branches"]}
            validate_perception_branch_receipt(
                receipt, branch_ids=list(group.branch_ids), delivered_branch_id="both-on", twin_branch_id="both-on-twin",
                phase_id="perception", level=2,
            )
            assert len(by_row[sid]) == 10                                    # every contact was made, the failed one included
            # The delivering arm is the lock arm's answer on EVERY row, the capped one included.
            assert result.final_response_text == f"solver-answer:{sid}:5"
            assert [_wire(r) for r in by_row[sid][5:]] == [ON, NO, NO, ON, ON]
            if sid == "s2":
                assert rows["both-off"]["solver_absent"] is True and rows["both-off"]["absent_reason"] == LENGTH
                assert [b for b, r in rows.items() if "solver_absent" in r] == ["both-off"]
                # Its custody is the real contact: five distinct Solver contacts, the capped one named by the row.
                assert len({r["solver_contact_id"] for r in receipt["branches"]}) == 5
                solver_visit = next(v for v in result.native_episode_receipt["role_visits"] if v["stage"] == "solver")
                assert [c["agent_contact_id"] for c in solver_visit["execution_receipt"]["contacts"]] == [
                    r["solver_contact_id"] for r in receipt["branches"]
                ]
                assert result.native_episode_receipt.get("terminal_disposition") is None
            else:
                assert not any("solver_absent" in r for r in receipt["branches"])
    finally:
        harness.close()


def test_the_delivering_arm_hitting_the_cap_still_stops_the_row(tmp_path, monkeypatch):
    _group_, harness = _arm(tmp_path / "armed", monkeypatch, cap_turn=5)
    try:
        with pytest.raises(Exception, match="finish_reason|non-authoritative|sealed no level-2"):
            harness.run(snapshot=_intent_snapshot(), decoding_params=dict(THINK_DECODING))
    finally:
        harness.close()


def _outputs_and_records(harness, summary):
    from types import SimpleNamespace as NS

    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
    from test_thinking_policy_column import _block

    raw_native = {
        "finite_completion_policy": harness.config.finite_completion_policy, "exhaustion_policy": "raise", "max_revisions": 0,
        "actions": dict(zip(("accept", "revise", "acquire"), harness.config.actions)),
        "roles": {"perception": {"phase_id": "perception", "thinking_variants": _block()}, "solver": {"phase_id": "solver"}},
    }
    runtime = object.__new__(FlightRuntime)
    runtime._composed = NS(values={"native_episode": raw_native})
    runtime._plan = harness.plan
    runtime._phase_summaries = [summary]
    runtime._output_rows = [
        {"sample_id": r.sample_id, "final_response_text": r.final_response_text, "native_episode_receipt": r.native_episode_receipt}
        for r in summary.results
    ]
    runtime._result_kind = lambda: "answer"
    runtime._arm = lambda: harness.client.arm
    outputs = runtime._canonical_output_rows(harness.client)
    return outputs, {rid: payload for _, rid, payload in harness.trace.records}


def test_the_sealed_outputs_carry_the_absent_column_and_the_bundle_verifier_accepts_it(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core.bundle import outputs as bundle_outputs
    from speech_aware_evidence_acquisition.core.bundle.outputs import _verify_outputs_trace_binding

    _group_, harness = _arm(tmp_path / "armed", monkeypatch)
    try:
        summary = harness.run(snapshot=_intent_snapshot(), decoding_params=dict(THINK_DECODING))
        outputs, records = _outputs_and_records(harness, summary)
        assert [row["sample_id"] for row in outputs] == ["s1", "s2", "s3", "s4"]
        capped = next(row for row in outputs if row["sample_id"] == "s2")
        absent = [b for b in capped["native_episode_receipt"]["perception_branches"]["branches"] if b.get("solver_absent")]
        assert [b["branch_id"] for b in absent] == ["both-off"] and absent[0]["absent_reason"] == LENGTH
        assert capped["text"] == "solver-answer:s2:5"
        _verify_outputs_trace_binding(tuple(outputs), records)             # I7 / I7v / the thinking-policy wire check, all rows

        # The absent mark is held against the TRACE, not the receipt's say-so.
        episode = capped["native_episode_receipt"]
        solver_visit = next(v for v in episode["role_visits"] if v["stage"] == "solver")
        contact = next(c for c in solver_visit["execution_receipt"]["contacts"] if c["agent_contact_id"] == absent[0]["solver_contact_id"])
        wire_id = f"{contact['request_id']}/wire-response"
        assert records[wire_id]["finish_reason"] == "length"
        forged = copy.deepcopy(records)
        forged[wire_id]["finish_reason"] = "stop"
        with pytest.raises(Exception, match="another finish_reason"):
            _verify_outputs_trace_binding(tuple(outputs), forged)
        # A claim for a contact the Solver visit never made is refused.
        lying = copy.deepcopy(outputs)
        next(r for r in lying if r["sample_id"] == "s2")["native_episode_receipt"]["perception_branches"]["branches"][2]["solver_contact_id"] = "ghost"
        with pytest.raises(Exception):
            _verify_outputs_trace_binding(tuple(lying), records)
        # A row that was not absent cannot be turned absent by editing the receipt (its wire says "stop").
        edited = copy.deepcopy(outputs)
        row = next(r for r in edited if r["sample_id"] == "s1")["native_episode_receipt"]["perception_branches"]["branches"][0]
        row.update(solver_absent=True, absent_reason=LENGTH)
        with pytest.raises(Exception, match="another finish_reason"):
            _verify_outputs_trace_binding(tuple(edited), records)
        assert bundle_outputs is not None
    finally:
        harness.close()


def test_a_stopped_attempt_with_an_absent_column_replays_whole_and_the_replay_check_sees_the_wire(tmp_path, monkeypatch):
    """Seal-only/resume mode A over the recorded trace: the capped row is KEPT whole (its five Solver contacts, the failed one included, are the
    row's own), the scan carries each request's thinking decoding fields and each wire response's finish_reason, and the bundle's Perception check
    (I7v, the v5 wire check and the absent-column check) passes over replay-shaped records exactly as the offline replay tool builds them."""

    from speech_aware_evidence_acquisition.core.bundle.outputs import _verify_perception_branch_trace_binding
    from speech_aware_evidence_acquisition.core.flight.resume import read_predecessor_attempt
    from test_perception_branch_degenerate_lists import _write_trace

    _group_, harness = _arm(tmp_path / "armed", monkeypatch)
    try:
        summary = harness.run(snapshot=_intent_snapshot(), decoding_params=dict(THINK_DECODING))
        live = {r.sample_id: r for r in summary.results}
        path = _write_trace(harness, tmp_path / "aborted")
        scan = read_predecessor_attempt(
            run_id=harness.plan.run_id, attempt_id="attempt-aborted", attempt_dir=path.parent, program_id=harness.program.program_id,
        )
        assert scan.incomplete == {} and sorted(scan.complete) == ["s1", "s2", "s3", "s4"]
        replayed = scan.complete["s2"].native_episode_receipt["perception_branches"]
        assert json.dumps(replayed, sort_keys=True) == json.dumps(json.loads(json.dumps(live["s2"].native_episode_receipt["perception_branches"])), sort_keys=True)
        assert [b["branch_id"] for b in replayed["branches"] if b.get("solver_absent")] == ["both-off"]
        capped = [c for c in scan.contacts["s2"] if c.finish_reason == "length"]
        assert len(capped) == 1 and capped[0].decoding_view == {
            "thinking_budget_tokens": None, "chat_template_kwargs": {"enable_thinking": False}, "max_tokens": 1024,
        }
        assert all(c.finish_reason == "stop" for sid in ("s1", "s3", "s4") for c in scan.contacts[sid])
        for sid in ("s1", "s2"):
            records = {}
            for contact in scan.contacts[sid]:
                records[f"{contact.request_id}/request"] = {
                    "payload_sha256": contact.request_sha256,
                    "payload": {"sample_id": contact.sample_id, **({} if contact.decoding_view is None else {"decoding_params": dict(contact.decoding_view)})},
                }
                records[f"{contact.request_id}/response"] = {
                    "text": contact.text, "response_sha256": contact.response_sha256, "response_text_sha256": contact.response_text_sha256,
                }
                if contact.finish_reason is not None:
                    records[f"{contact.request_id}/wire-response"] = {"finish_reason": contact.finish_reason}
            _verify_perception_branch_trace_binding(
                {"sample_id": sid, "native_episode_receipt": scan.complete[sid].native_episode_receipt}, records,
            )
    finally:
        harness.close()


# ---------------------------------------------------------------------------
# 4. The column renderer
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("stage3_rollout_score_absent", ROOT / "scripts/analysis/stage3_rollout_score.py")
score = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(score)

SAMPLE = "slurp:train:ABSENT:0"


def _answer(scenario):
    return json.dumps({"scenario": scenario, "action": "set", "entities": []}, sort_keys=True)


def _render_fixture(tmp_path, *, absent, delivered=None):
    group = _group()
    trace, contacts, answers = {}, [], {}
    for index, name in enumerate(group.branch_ids):
        raw = _answer("alarm" if name in ("both-on", "both-on-twin") else "audio")
        answers[name] = raw
        request_id = f"{SAMPLE}-solver-{name}"
        digest = _digest(raw)
        trace[f"{request_id}/request"] = {"payload_sha256": "a" * 64}
        trace[f"{request_id}/response"] = {"text": raw, "response_text_sha256": digest}
        contacts.append({"agent_contact_id": request_id, "request_id": request_id, "request_sha256": "a" * 64, "response_text_sha256": digest})
    records = []
    for index, branch in enumerate(group.branches):
        records.append(perception_branch_record(
            branch=branch, branch_index=index, contact_id=f"perception-{index}", request_sha256="b" * 64,
            response_text_sha256="c" * 64, note_sha256="d" * 64, note_parse_status="ok", candidate_intent_ids=("x",),
            supplied_value_ids=(), solver_contact_id=contacts[index]["agent_contact_id"],
            solver_request_sha256=contacts[index]["request_sha256"], solver_response_text_sha256=contacts[index]["response_text_sha256"],
            candidate_supply_value_ids=(), thinking_group=True,
            solver_absent=branch.branch_id in absent, absent_reason=LENGTH if branch.branch_id in absent else None,
        ))
    visit = {"stage": "solver", "role_id": "solver", "execution_receipt": {"contacts": contacts, "final_contact": contacts[-1]}}
    row = {
        "sample_id": SAMPLE, "text": answers["both-on"] if delivered is None else delivered,
        "native_episode_receipt": {
            "role_visits": [visit], "kind": "accepted",
            "perception_branches": perception_branch_receipt(group=group, phase_id="perception", records=records),
        },
    }
    manifest_path = tmp_path / "runs" / "RUN" / "ATT" / "RUN.manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("{}")
    bundle = SimpleNamespace(
        manifest={"status": "COMPLETED", "run_id": "RUN", "config": {"config_hash": "c" * 64}, "outputs": {"sha256": "d" * 64},
                  "raw_trace": {"sha256": "e" * 64}, "scores": {"sha256": "f" * 64}},
        attempt_state="FINALIZED", manifest_path=manifest_path, split_ids=frozenset([SAMPLE]), outputs_rows=(row,), trace_records=trace,
    )
    return bundle, group


@pytest.fixture
def _delivery_stub(monkeypatch):
    from speech_aware_evidence_acquisition.rails import native_episode_receipt

    monkeypatch.setattr(
        native_episode_receipt, "validate_native_episode_delivery_receipt",
        lambda episode, **_kwargs: SimpleNamespace(kind=episode["kind"]),
    )


def _render(bundle, group, tmp_path):
    return score.render_perception_branch_columns(
        bundle, group, {SAMPLE: "alarm"}, tmp_path / "analysis", run_id="RUN", attempt_id="ATT",
        roster_sha256="1" * 64, config_hash="c" * 64,
    )


def test_an_absent_column_renders_as_the_canonical_empty_answer_and_is_counted(tmp_path, _delivery_stub):
    bundle, group = _render_fixture(tmp_path, absent=("both-off",))
    manifest = _render(bundle, group, tmp_path)
    assert manifest["solver_absent_by_branch"] == {name: int(name == "both-off") for name in ARM_IDS}
    assert manifest["malformed_first_visit_by_branch"]["both-off"] == 0               # absent is not malformed
    both_off = list(score.iter_jsonl(Path(manifest["copies"]["both-off"]["path"])))
    assert both_off == [{"sample_id": SAMPLE, "text": score.EMPTY_ANSWER}]
    present = list(score.iter_jsonl(Path(manifest["copies"]["perception-off"]["path"])))
    assert present[0]["text"] != score.EMPTY_ANSWER                                  # an ordinary column is untouched
    delivering = list(score.iter_jsonl(Path(manifest["copies"]["both-on"]["path"])))
    assert delivering[0]["text"] == _answer("alarm") and manifest["at1_column_reproduction_checked_rows"] == 1
    meta = json.loads((tmp_path / "analysis" / "first-visit-rows.json").read_text())["rows"][0]["branches"]
    assert [m["parse_status"] for m in meta] == ["ok", "ok", "absent", "ok", "ok"]
    assert next(m for m in meta if m["parse_status"] == "absent")["absent_reason"] == LENGTH


def test_a_run_without_an_absent_column_counts_zero_everywhere(tmp_path, _delivery_stub):
    bundle, group = _render_fixture(tmp_path, absent=())
    manifest = _render(bundle, group, tmp_path)
    assert manifest["solver_absent_by_branch"] == {name: 0 for name in ARM_IDS}


def test_the_renderer_refuses_an_absent_delivering_column(tmp_path, _delivery_stub):
    bundle, group = _render_fixture(tmp_path, absent=())
    branches = bundle.outputs_rows[0]["native_episode_receipt"]["perception_branches"]["branches"]
    branches[-1].update(solver_absent=True, absent_reason=LENGTH)
    with pytest.raises(Exception, match="absent"):
        _render(bundle, group, tmp_path)
