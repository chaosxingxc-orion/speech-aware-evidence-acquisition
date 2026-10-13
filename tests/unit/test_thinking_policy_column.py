"""NX-T R1 (2026-10-13): the per-node THINKING-POLICY column -- a same-flight arm kind over the decoding knobs.

``roles.perception.thinking_variants`` fans the Perception visit out to K arms (a level-2 branch group, receipt schema v5).
Every arm renders the delivering arm's own evidence, template and QueryState; only the per-node ``enable_thinking`` /
``reasoning_budget_tokens`` / ``answer_reserve_tokens`` of the arm's OWN Perception and Solver contacts differ (the Solver
prompt of a non-delivering arm differs by that arm's own Perception note, exactly as it does for a template branch). The
delivering arm declares no policy, so its requests are the locked plan's, byte for byte.

Layers, all model-free (fake transports only): 1. the parser and the loader; 2. the v5 receipt; 3. the request seam
(per-arm request shape and the delivering-arm byte identity); 4. the production graph and the bundle verifier; 5. the
consumption module's ``thinking`` column kind.
"""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
from collections import defaultdict
from dataclasses import replace
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails import consumption_module as cm
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import carrier_module_hooks
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config
from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
    PERCEPTION_BRANCH_RECEIPT_SCHEMA_V5,
    validate_perception_branch_receipt,
)
from speech_aware_evidence_acquisition.rails.supply_variants import (
    PERCEPTION_BRANCH_LEVEL_SOLVER,
    PerceptionBranchError,
    parse_perception_thinking_variants,
    perception_branch_ceiling,
    perception_branch_receipt,
    perception_branch_record,
    replay_perception_branch_block,
)
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

FIT = {"slot_tokens": 24576, "completion_ceiling": 4096, "base_prompt_tokens": 9600, "tokens_per_supplied_item": 120}
GUARD = "refuse-think-marker-in-content"
OFF = {"enable_thinking": False}
ARMS = ("perception-off", "solver-off", "both-off")
POLICY = {
    "perception-off": {"perception": OFF},
    "solver-off": {"solver": OFF},
    "both-off": {"perception": OFF, "solver": OFF},
}


def _block(*, twin=True, drop=()):
    arms = [{"arm_id": a, "thinking_policy": copy.deepcopy(POLICY[a])} for a in ARMS if a not in drop]
    if twin:
        arms.append({"arm_id": "both-on-twin", "replicate_of": "both-on"})
    arms.append({"arm_id": "both-on", "deliver": True})
    return {"node": "perception", "arms": arms, "max_supplied_items": 4, "fit_estimate": dict(FIT)}


def _group(**kwargs):
    return parse_perception_thinking_variants(_block(**kwargs), phase_id="perception")


# ---------------------------------------------------------------------------
# 1. The parser and the loader
# ---------------------------------------------------------------------------


def test_the_parser_builds_a_level_two_branch_group_with_the_thinking_axis():
    group = _group()
    assert group.level == PERCEPTION_BRANCH_LEVEL_SOLVER and group.is_thinking and not group.is_template
    assert group.renders_unvaried_evidence
    assert group.branch_ids == ("perception-off", "solver-off", "both-off", "both-on-twin", "both-on")
    assert group.delivering_branch.branch_id == "both-on" and group.twin_branch.branch_id == "both-on-twin"
    assert group.branch("both-on").thinking_policy is None and group.branch("both-on-twin").thinking_policy is None
    assert group.branch("both-off").thinking_policy == {"perception": OFF, "solver": OFF}
    assert group.branch("both-off").knobs == () and group.branch("both-off").instruction_template is None
    # K = 5 -> the contact term is 2 (K - 1) = 8 over the review-off base 2.
    assert perception_branch_ceiling(base_ceiling=2, branch_count=5, level=2) == 10


def test_the_twin_is_optional_for_the_thinking_kind():
    group = _group(twin=False)
    assert not group.has_twin and group.branch_count == 4


@pytest.mark.parametrize("mutate, message", [
    (lambda b: b["arms"][0]["thinking_policy"]["perception"].update(temperature=0.6), "unknown|must be a non-empty mapping over"),
    (lambda b: b["arms"][0]["thinking_policy"].update(reviewer={"enable_thinking": False}), "role kind"),
    (lambda b: b["arms"][0].__setitem__("thinking_policy", {}), "non-empty mapping"),
    (lambda b: b["arms"][0].__setitem__("thinking_policy", {"perception": {"enable_thinking": "no"}}), "boolean"),
    (lambda b: b["arms"][0].__setitem__("thinking_policy", {"perception": {"reasoning_budget_tokens": -1}}), "non-negative integer"),
    (lambda b: b["arms"][0].pop("thinking_policy"), "must declare a thinking_policy"),
    (lambda b: b["arms"][0].update(overrides={"k": 3}), "unknown keys"),
    (lambda b: b["arms"][0].update(instruction_template={"relpath": "x", "sha256": "0" * 64}), "unknown keys"),
    (lambda b: b["arms"][-1].__setitem__("thinking_policy", POLICY["solver-off"]), "delivering arm or the twin"),
    (lambda b: b["arms"][-2].__setitem__("thinking_policy", POLICY["solver-off"]), "delivering arm or the twin"),
    (lambda b: b["arms"][1].__setitem__("thinking_policy", POLICY["perception-off"]), "same policy"),
    (lambda b: b.__setitem__("arms", [b["arms"][-1], *b["arms"][:-1]]), "LAST arm"),
    (lambda b: b.__setitem__("node", "solver"), "exactly the node it names"),
    (lambda b: b["arms"][1].__setitem__("arm_id", "perception-off"), "distinct"),
    (lambda b: b["arms"][-2].__setitem__("replicate_of", "perception-off"), "not the delivering arm"),
    (lambda b: b.update(extra=1), "exactly"),
])
def test_the_parser_refuses_by_name(mutate, message):
    block = _block()
    mutate(block)
    with pytest.raises(PerceptionBranchError, match=message):
        parse_perception_thinking_variants(block, phase_id="perception")


def test_candidate_count_and_twin_count_are_bounded():
    many = _block()
    many["arms"] = [
        {"arm_id": f"a{i}", "thinking_policy": {"perception": {"reasoning_budget_tokens": 100 + i}}} for i in range(7)
    ] + [many["arms"][-1]]
    with pytest.raises(PerceptionBranchError, match="between 1 and 6"):
        parse_perception_thinking_variants(many, phase_id="perception")
    two_twins = _block()
    two_twins["arms"].insert(-1, {"arm_id": "twin-2", "replicate_of": "both-on"})
    with pytest.raises(PerceptionBranchError, match="at most one"):
        parse_perception_thinking_variants(two_twins, phase_id="perception")


def test_a_fit_overrun_is_refused():
    block = _block()
    block["fit_estimate"]["base_prompt_tokens"] = 23000
    with pytest.raises(PerceptionBranchError, match="exceeds"):
        parse_perception_thinking_variants(block, phase_id="perception")


def _values(*, twin=True, block=None, thinking=True):
    from test_review_off_capacity import values

    v = copy.deepcopy(values(False))
    v["policy"] = "phase-native-module-v1-c10" if twin else "phase-native-module-v1-c8"
    v["phase_material"] = {"perception": {"instruction_template": "probes/slurp_native_role_perception_v2.txt"}}
    v["native_episode"]["roles"]["perception"]["thinking_variants"] = block if block is not None else _block(twin=twin)
    if thinking:
        v.update(
            reasoning_content_guard=GUARD, reasoning_budget_tokens=3072, answer_reserve_tokens=1024, enable_thinking=True,
            decoding_params={"temperature": 0, "seed": 20260913, "max_tokens": 4096},
        )
    return v


def _program(ceiling):
    from test_native_episode_config import program

    return program(ceiling=ceiling)


def test_the_loader_parses_the_group_and_adds_two_per_non_delivering_arm_to_the_ceiling():
    config = load_native_episode_config(_values(), _program(10))
    assert config.max_contacts == 10
    group = config.perception_branch_group
    assert group is not None and group.is_thinking and group.level == 2 and config.supply_variant_group is None
    assert config.perception_branch_phase_id == "perception"
    assert load_native_episode_config(_values(twin=False), _program(8)).max_contacts == 8


def test_the_loader_refuses_by_name():
    with pytest.raises(ValueError, match="program contact ceiling must equal"):
        load_native_episode_config(_values(), _program(8))
    with pytest.raises(ValueError, match="reasoning fragment"):
        load_native_episode_config(_values(thinking=False), _program(10))
    # An arm whose own budget leaves the geometry cap.
    big = _block()
    big["arms"][0]["thinking_policy"] = {"perception": {"reasoning_budget_tokens": 6000}}
    with pytest.raises(ValueError, match="exceeds the geometry cap"):
        load_native_episode_config(_values(block=big), _program(10))
    # A no-think arm that also declares a budget contradicts itself.
    clash = _block()
    clash["arms"][0]["thinking_policy"] = {"perception": {"enable_thinking": False, "reasoning_budget_tokens": 10}}
    with pytest.raises(ValueError, match="contradicts enable_thinking false"):
        load_native_episode_config(_values(block=clash), _program(10))
    # The fit ceiling must cover the delivering arm's cap.
    low = _block()
    low["fit_estimate"]["completion_ceiling"] = 512
    with pytest.raises(ValueError, match="below the delivering arm"):
        load_native_episode_config(_values(block=low), _program(10))
    for other in ("branches", "template_variants"):
        v = _values()
        v["native_episode"]["roles"]["perception"][other] = {"x": 1}
        with pytest.raises(ValueError, match="cannot combine"):
            load_native_episode_config(v, _program(10))


def test_a_config_without_the_key_is_unchanged():
    v = _values()
    del v["native_episode"]["roles"]["perception"]["thinking_variants"]
    config = load_native_episode_config(v, _program(2))
    assert config.perception_branch_group is None and config.max_contacts == 2


# ---------------------------------------------------------------------------
# 2. The v5 receipt
# ---------------------------------------------------------------------------


def _rows(group, *, thinking=True):
    rows = []
    for index, branch in enumerate(group.branches):
        digest = hashlib.sha256(f"note-{index}".encode()).hexdigest()
        rows.append(perception_branch_record(
            branch=branch, branch_index=index, contact_id=f"c{index}", request_sha256=digest, response_text_sha256=digest,
            note_sha256=digest, note_parse_status="malformed", candidate_intent_ids=(), supplied_value_ids=(),
            solver_contact_id=f"s{index}", solver_request_sha256=digest, solver_response_text_sha256=digest,
            candidate_supply_value_ids=(), thinking_group=thinking,
        ))
    return rows


def test_a_v5_row_carries_only_the_thinking_axis_and_the_receipt_validates():
    group = _group()
    rows = _rows(group)
    assert rows[2]["thinking_policy"] == {"perception": OFF, "solver": OFF}
    assert rows[3]["thinking_policy"] is None and rows[4]["thinking_policy"] is None
    assert "instruction_template" not in rows[0]
    block = perception_branch_receipt(group=group, phase_id="perception", records=rows)
    assert block["schema"] == PERCEPTION_BRANCH_RECEIPT_SCHEMA_V5
    validate_perception_branch_receipt(
        block, branch_ids=list(group.branch_ids), delivered_branch_id="both-on", twin_branch_id="both-on-twin",
        phase_id="perception", level=2,
    )
    with pytest.raises(PerceptionBranchError, match="not the thinking"):
        perception_branch_record(
            branch=group.branch("both-off"), branch_index=2, contact_id="c", request_sha256="1" * 64,
            response_text_sha256="1" * 64, note_sha256="1" * 64, note_parse_status="malformed",
            candidate_intent_ids=(), supplied_value_ids=(),
        )


def test_a_v5_receipt_without_a_twin_validates_and_a_malformed_axis_is_refused():
    group = _group(twin=False)
    block = perception_branch_receipt(group=group, phase_id="perception", records=_rows(group))
    validate_perception_branch_receipt(
        block, branch_ids=list(group.branch_ids), delivered_branch_id="both-on", twin_branch_id=None,
        phase_id="perception", level=2,
    )
    # Every other schema still requires its twin.
    v4 = dict(block, schema="saea-perception-branch-arms-v4")
    with pytest.raises(ValueError):
        validate_perception_branch_receipt(
            v4, branch_ids=list(group.branch_ids), delivered_branch_id="both-on", twin_branch_id=None,
            phase_id="perception", level=2,
        )
    bad = copy.deepcopy(block)
    bad["branches"][-1]["thinking_policy"] = {"solver": OFF}            # the delivering arm declares an axis
    with pytest.raises(ValueError, match="must declare no axis"):
        validate_perception_branch_receipt(
            bad, branch_ids=list(group.branch_ids), delivered_branch_id="both-on", twin_branch_id=None,
            phase_id="perception", level=2,
        )
    bad = copy.deepcopy(block)
    bad["branches"][0]["thinking_policy"] = None                         # a candidate declares none
    with pytest.raises(ValueError, match="exactly one axis|only axis"):
        validate_perception_branch_receipt(
            bad, branch_ids=list(group.branch_ids), delivered_branch_id="both-on", twin_branch_id=None,
            phase_id="perception", level=2,
        )
    bad = copy.deepcopy(block)
    bad["branches"][0]["thinking_policy"] = {"perception": {"temperature": 0}}
    with pytest.raises(ValueError, match="thinking_policy"):
        validate_perception_branch_receipt(
            bad, branch_ids=list(group.branch_ids), delivered_branch_id="both-on", twin_branch_id=None,
            phase_id="perception", level=2,
        )


def test_a_v5_block_replays_as_v5_for_seal_only_resume():
    from speech_aware_evidence_acquisition.rails.supply_variants import PerceptionBranchReplayContact

    group = _group()
    rows = _rows(group)
    contacts = {}
    for index, row in enumerate(rows):
        text = f"note-{index}"
        digest = hashlib.sha256(text.encode()).hexdigest()
        contacts[f"c{index}"] = PerceptionBranchReplayContact(request_sha256=digest, response_text_sha256=digest, text=text)
        contacts[f"s{index}"] = PerceptionBranchReplayContact(request_sha256=digest, response_text_sha256=digest, text=text)
    block = perception_branch_receipt(group=group, phase_id="perception", records=rows)
    replayed = replay_perception_branch_block(block, contacts=contacts)
    assert replayed["schema"] == PERCEPTION_BRANCH_RECEIPT_SCHEMA_V5
    assert [r["thinking_policy"] for r in replayed["branches"]] == [r["thinking_policy"] for r in rows]


# ---------------------------------------------------------------------------
# 3. The request seam
# ---------------------------------------------------------------------------

from speech_aware_evidence_acquisition.reproduction.ojw.native_request import (  # noqa: E402
    MeteredNativeSpeechRequest,
    NativeSpeechRequestError,
)
from speech_aware_evidence_acquisition.reproduction.ojw.native_roles import (  # noqa: E402
    NativeRoleContactContext,
    NativeRoleModelRequest,
)
from test_rails_core_client_native_tools import (  # noqa: E402
    _TOOLS, _World, _client, _plan as _native_plan, _speech_feature_messages, _speech_feature_world,
)
from test_thinking_transport_and_native_knobs import KNOBS, _ScriptedTransport, _native_binding  # noqa: E402

try:
    from types import MappingProxyType
except ImportError:  # pragma: no cover
    raise

BRANCH_POLICY = {
    arm: {role: dict(entry) for role, entry in policy.items()} for arm, policy in POLICY.items()
}


def _adapter(tmp_path, *, branch_policy):
    world = _World(tmp_path)
    feature_root, packet, bindings = _speech_feature_world(world, tmp_path)
    client, _gate, _t = _client(
        world, tmp_path, transport=_ScriptedTransport([("a", "stop", 3)] * 8), arm="speech-feature-query-native-tools",
        tool_schemas=_TOOLS, speech_feature_root=feature_root, speech_packet_bindings=bindings,
        plan=_native_plan(planned_model_calls=50),
    )
    return MeteredNativeSpeechRequest(
        client=client, binding_provider=lambda r: _native_binding(r.role_id, packet), render_request=lambda b: json.loads(b),
        completion_sink=lambda request, completion: None, branch_thinking_policy=branch_policy,
    )


def _request(role_id, *, branch=None, contact="c-1"):
    return NativeRoleModelRequest(
        role_id=role_id,
        context=NativeRoleContactContext(sample_id="s1", agent_contact_id=contact, perception_branch_id=branch),
        messages=({"role": "system", "content": "Choose exactly one opaque key id."}, {"role": "user", "content": "Inspect the speech."}),
        tool_schemas=(), visible_tool_names=(), decoding_controls=MappingProxyType({}),
    )


def _decoding(adapter, role_id, *, branch=None):
    return adapter.prepare(_request(role_id, branch=branch)).rendered_body()["decoding_params"]


def test_each_arm_composes_its_own_per_node_request_and_every_other_node_keeps_the_fragment_default(tmp_path):
    adapter = _adapter(tmp_path / "a", branch_policy={arm: dict(p) for arm, p in BRANCH_POLICY.items()})
    on = {"thinking_budget_tokens": 3072, "chat_template_kwargs": {"enable_thinking": True}, "max_tokens": 4096}
    for role in ("perception", "solver"):
        for arm in ("both-on", "both-on-twin", None):
            assert {k: _decoding(adapter, role, branch=arm)[k] for k in on} == on
    for arm, policy in BRANCH_POLICY.items():
        for role in ("perception", "solver"):
            decoding = _decoding(adapter, role, branch=arm)
            if role in policy:
                assert "thinking_budget_tokens" not in decoding, (arm, role)
                assert decoding["chat_template_kwargs"] == {"enable_thinking": False} and decoding["max_tokens"] == 1024
            else:
                assert {k: decoding[k] for k in on} == on, (arm, role)


def test_the_delivering_arm_request_is_the_locked_plan_request_byte_for_byte(tmp_path):
    """Decision 5: compose the 268-B lock request (no arm policy at all) and the delivering arm's / twin's request (an adapter that
    DOES carry the column's policies) and compare the request bodies, the payloads and the prepared bytes minus the arm id."""

    lock = _adapter(tmp_path / "lock", branch_policy=None)
    column = _adapter(tmp_path / "col", branch_policy={arm: dict(p) for arm, p in BRANCH_POLICY.items()})
    for role in ("perception", "solver"):
        reference = lock.prepare(_request(role, branch=None))
        for arm in ("both-on", "both-on-twin"):
            armed = column.prepare(_request(role, branch=arm))
            assert armed.rendered_body() == reference.rendered_body(), (role, arm)
            assert armed.request.payload_bytes == reference.request.payload_bytes, (role, arm)
            strip = lambda blob: json.loads(blob)["context"]  # noqa: E731
            expected = json.loads(reference.role_request_bytes)
            actual = json.loads(armed.role_request_bytes)
            assert actual["context"].pop("perception_branch_id") == arm
            assert actual == expected, (role, arm)


def test_a_policy_naming_a_malformed_override_is_refused_at_construction(tmp_path):
    with pytest.raises(NativeSpeechRequestError, match="branch_thinking_policy"):
        _adapter(tmp_path, branch_policy={"x": {"perception": "no"}})
    with pytest.raises(NativeSpeechRequestError, match="branch_thinking_policy"):
        _adapter(tmp_path / "b", branch_policy={"x": {}})


def test_a_budget_arm_resolves_through_the_same_seam_for_the_later_budget_round(tmp_path):
    adapter = _adapter(tmp_path, branch_policy={"b1024": {"solver": {"reasoning_budget_tokens": 1024}}})
    decoding = _decoding(adapter, "solver", branch="b1024")
    assert decoding["thinking_budget_tokens"] == 1024 and decoding["max_tokens"] == 2048
    assert _decoding(adapter, "perception", branch="b1024")["thinking_budget_tokens"] == 3072
    assert KNOBS["max_tokens"] == 4096


# ---------------------------------------------------------------------------
# 4. The production graph and the bundle verifier
# ---------------------------------------------------------------------------

pytest.importorskip("openjiuwen", reason="OpenJiuwen unavailable")

import test_native_episode_runner as harness_module  # noqa: E402
from test_llama_server_transport import _spawn_live_matching_process  # noqa: E402,F401
from test_native_episode_runner import _ActualEpisodeHarness  # noqa: E402
from test_perception_branch_live import _perception_live_config  # noqa: E402
from test_perception_branch_presentation_live import VALUE_X, VALUE_Y, _intent_snapshot  # noqa: E402
from test_perception_template_variants import _perception_note, _requests_by_row  # noqa: E402
from test_rails_controllers import _phase_supply  # noqa: E402

pytestmark = pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")

ROWS = 4
THINK_DECODING = {
    "temperature": 0, "max_tokens": 4096, "thinking_budget_tokens": 3072, "chat_template_kwargs": {"enable_thinking": True},
}
# Branch order perception-off, solver-off, both-off, both-on-twin, both-on -> turns 1..5.
NOTE = {1: "beta-note", 2: "gamma-note", 3: "delta-note", 4: "alpha-note", 5: "alpha-note"}


def _output(key):
    sample_id, phase, visit, turn = key
    if phase == "perception":
        return f"{NOTE[turn]}:{sample_id}"
    if phase == "solver":
        return f"solver-answer:{sample_id}:{turn}"
    return f"{phase}-analysis:{sample_id}:visit:{visit}"


def _control_output(key):
    sample_id, phase, visit, turn = key
    if phase == "perception":
        return f"alpha-note:{sample_id}"
    if phase == "solver":
        return f"solver-answer:{sample_id}:5"
    return f"{phase}-analysis:{sample_id}:visit:{visit}"


def _history_text(request) -> str:
    return json.dumps(
        {"states": [{k: h[k] for k in ("state_kind", "content", "content_sha256")} for h in request["history"] if "state_kind" in h],
         "supplied_evidence": request["supplied_evidence"]},
        default=str, sort_keys=True,
    )


def _build(tmp_path, monkeypatch, *, armed=True):
    class FourRowWorld(harness_module._World):
        SAMPLE_SPECS = (("s1", 2.0), ("s2", 3.5), ("s3", 2.5), ("s4", 3.0))

    monkeypatch.setattr(harness_module, "_World", FourRowWorld)
    # A budgeted thinking request may spend one answer-only re-ask per contact (the plan ceiling allows for it): double the plan.
    real_plan = harness_module._plan
    monkeypatch.setattr(
        harness_module, "_plan",
        lambda **kw: real_plan(**{**kw, "planned_model_calls": kw["planned_model_calls"] * 2}),
    )
    real_transport = harness_module._transport
    monkeypatch.setattr(
        harness_module, "_transport", lambda *a, **k: real_transport(*a, reasoning_content_guard=GUARD, **k),
    )
    group = _group() if armed else None
    contacts = 10 if armed else 2
    harness = _ActualEpisodeHarness(tmp_path, sample_count=ROWS, max_revisions=0, max_contacts=contacts, planner_actions=())
    harness.config = _perception_live_config(group=group, max_contacts=contacts)
    harness.program = replace(
        harness.program,
        phases=tuple(replace(p, knowledge="supplied") if p.name == "solver" else p for p in harness.program.phases),
    )

    def supply(phase, context):
        if phase != "solver":
            return None
        values = (VALUE_X,) if "alpha" in _perception_note(context) else (VALUE_Y,)
        return _phase_supply(context, value_ids=values, facet_ids=("operation:dim",))

    def branch_supply(*, branch_id, phase_id, context):
        values = (VALUE_X,) if "alpha" in _perception_note(context) else (VALUE_Y,)
        return _phase_supply(context, value_ids=values, facet_ids=("operation:dim",))

    real_binding = harness_module.NativeEpisodeRunBinding

    def bind(**kwargs):
        extra = {"supply_for_phase": supply}
        if armed:
            extra["perception_branch_solver_supply"] = branch_supply
        return real_binding(**kwargs, **extra)

    monkeypatch.setattr(harness_module, "NativeEpisodeRunBinding", bind)
    harness._output = _output if armed else _control_output
    return group, harness


def _run(harness):
    try:
        return harness.run(snapshot=_intent_snapshot(), decoding_params=dict(THINK_DECODING))
    finally:
        harness.close()


def _wire(request):
    d = request["decoding_params"]
    return d.get("thinking_budget_tokens"), d.get("chat_template_kwargs"), d["max_tokens"]


ON = (3072, {"enable_thinking": True}, 4096)
NO = (None, {"enable_thinking": False}, 1024)


def test_four_rows_walk_the_production_graph_with_each_arm_carrying_its_own_thinking_decoding(tmp_path, monkeypatch):
    group, harness = _build(tmp_path / "armed", monkeypatch)
    summary = _run(harness)
    assert len(summary.results) == ROWS
    by_row = _requests_by_row(harness)
    for result in summary.results:
        sid = result.sample_id
        requests = by_row[sid]
        assert len(requests) == 10
        perception, solver = requests[:5], requests[5:]
        # Perception: perception-off, solver-off, both-off, twin, lock.
        assert [_wire(r) for r in perception] == [NO, ON, NO, ON, ON]
        # Solver: each arm's own contact -- perception-off keeps it on, solver-off and both-off turn it off.
        assert [_wire(r) for r in solver] == [ON, NO, NO, ON, ON]
        # The Solver prompt differs by the arm's OWN Perception note; the evidence/template are the delivering arm's.
        for index, note in enumerate(("beta", "gamma", "delta", "alpha", "alpha")):
            assert f"{note}-note:{sid}" in _history_text(solver[index])
        assert _history_text(solver[3]) == _history_text(solver[4])
        # The sealed state and the delivered answer are the lock arm's.
        assert [s.content for s in result.agent_states if s.state_kind == "phase:perception"] == [f"alpha-note:{sid}"]
        assert result.final_response_text == f"solver-answer:{sid}:5"
        receipt = result.native_episode_receipt["perception_branches"]
        assert receipt["schema"] == PERCEPTION_BRANCH_RECEIPT_SCHEMA_V5
        rows = {row["branch_id"]: row for row in receipt["branches"]}
        assert list(rows) == list(group.branch_ids)
        assert rows["solver-off"]["thinking_policy"] == {"solver": OFF}
        assert rows["both-on"]["thinking_policy"] is None and rows["both-on-twin"]["thinking_policy"] is None
        validate_perception_branch_receipt(
            receipt, branch_ids=list(group.branch_ids), delivered_branch_id="both-on", twin_branch_id="both-on-twin",
            phase_id="perception", level=2,
        )
        assert len({r["contact_id"] for r in receipt["branches"]}) == 5
        assert len({r["solver_contact_id"] for r in receipt["branches"]}) == 5


def test_the_delivering_arm_requests_equal_the_unarmed_plan_requests_per_row(tmp_path, monkeypatch):
    group, harness = _build(tmp_path / "armed", monkeypatch)
    summary = _run(harness)
    by_row = _requests_by_row(harness)
    monkeypatch.undo()
    _none, control = _build(tmp_path / "control", monkeypatch, armed=False)
    _run(control)
    control_rows = _requests_by_row(control)
    for result in summary.results:
        armed_requests, plan_requests = by_row[result.sample_id], control_rows[result.sample_id]
        assert len(plan_requests) == 2
        for armed_request, plan_request, label in ((armed_requests[4], plan_requests[0], "perception"), (armed_requests[9], plan_requests[1], "solver")):
            for field in ("decoding_params", "tool_schemas", "speech_feature_parts", "query_source", "supplied_evidence", "sample_id", "task_instruction"):
                assert armed_request[field] == plan_request[field], (label, field)
            assert _history_text(armed_request) == _history_text(plan_request), label


def test_thinking_branches_seal_through_the_bundle_verifier_and_the_runtime(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core.bundle import outputs as bundle_outputs
    from speech_aware_evidence_acquisition.core.bundle.outputs import _verify_outputs_trace_binding
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime

    group, harness = _build(tmp_path, monkeypatch)
    summary = harness.run(snapshot=_intent_snapshot(), decoding_params=dict(THINK_DECODING))
    try:
        raw_native = {
            "finite_completion_policy": harness.config.finite_completion_policy, "exhaustion_policy": "raise", "max_revisions": 0,
            "actions": dict(zip(("accept", "revise", "acquire"), harness.config.actions)),
            "roles": {"perception": {"phase_id": "perception", "thinking_variants": _block()}, "solver": {"phase_id": "solver"}},
        }
        runtime = object.__new__(FlightRuntime)
        runtime._composed = SimpleNamespace(values={"native_episode": raw_native})
        runtime._plan = harness.plan
        runtime._phase_summaries = [summary]
        runtime._output_rows = [
            {"sample_id": r.sample_id, "final_response_text": r.final_response_text, "native_episode_receipt": r.native_episode_receipt}
            for r in summary.results
        ]
        runtime._result_kind = lambda: "answer"
        runtime._arm = lambda: harness.client.arm
        outputs = runtime._canonical_output_rows(harness.client)
        assert [row["sample_id"] for row in outputs] == ["s1", "s2", "s3", "s4"]
        records = {rid: payload for _, rid, payload in harness.trace.records}
        _verify_outputs_trace_binding(tuple(outputs), records)
        # The wire check is live: a forged request that moves a thinking field its arm does not name is refused.
        forged = copy.deepcopy(records)
        row = outputs[0]
        branch_rows = row["native_episode_receipt"]["perception_branches"]["branches"]
        episode = row["native_episode_receipt"]
        perception_visit = next(v for v in episode["role_visits"] if v["stage"] == "perception")
        request_id = perception_visit["execution_receipt"]["contacts"][1]["request_id"]    # solver-off's Perception contact
        forged[f"{request_id}/request"]["payload"]["decoding_params"]["max_tokens"] = 7
        with pytest.raises(Exception, match="thinking field"):
            bundle_outputs._verify_thinking_policy_wire(
                branch_rows, perception_visit["execution_receipt"]["contacts"],
                episode["role_visits"], forged,
                refuse=lambda reason: (_ for _ in ()).throw(RuntimeError(reason)),
            )
    finally:
        harness.close()


# ---------------------------------------------------------------------------
# 5. The consumption module's ``thinking`` column kind
# ---------------------------------------------------------------------------

from test_consumption_module_review_off import review_off_block  # noqa: E402

THINKING_FRAME = {"max_supplied_items": 48, "twin": True, "fit_estimate": dict(FIT)}


def _column(name):
    return {"column_id": name, "kind": "thinking", "node": "perception", "thinking_policy": copy.deepcopy(POLICY[name])}


def _module_block(*, names=ARMS, twin=True):
    block = review_off_block()
    block["columns"] = [_column(n) for n in names]
    block["thinking_frame"] = {**THINKING_FRAME, "twin": twin}
    return block


def test_thinking_columns_compile_to_one_block_at_the_perception_node():
    composed = cm.compile_module(_module_block(), carrier_module_hooks())
    block = composed.values()["native_episode"]["roles"]["perception"]["thinking_variants"]
    assert block["node"] == "perception"
    assert [(a["arm_id"], a.get("deliver"), a.get("replicate_of")) for a in block["arms"]] == [
        ("perception-off", None, None), ("solver-off", None, None), ("both-off", None, None),
        ("both-on-twin", None, "both-on"), ("both-on", True, None),
    ]
    assert block["arms"][-1] == {"arm_id": "both-on", "deliver": True}
    # review-off graph 2 + 2 (K - 1), K = 5 -> 10.
    assert (composed.program_id, composed.program_ceiling) == ("phase-native-module-v1-c10", 10)
    assert block["fit_estimate"] == FIT


def test_the_compiled_block_loads_through_the_runtime_loader_and_verifies():
    block = _module_block()
    composed = cm.compile_module(block, carrier_module_hooks())
    values = composed.values()
    values["carrier_lock_key"] = "slurp"
    values["native_episode"]["consumption_module"] = block
    values.update(
        reasoning_content_guard=GUARD, reasoning_budget_tokens=3072, answer_reserve_tokens=1024, enable_thinking=True,
        decoding_params={"temperature": 0, "seed": 20260913, "max_tokens": 4096},
    )
    parsed = load_native_episode_config(values, default_phase_program(values["policy"]))
    assert parsed.max_contacts == composed.program_ceiling == 10
    assert parsed.perception_branch_group.is_thinking
    cm.verify_declared_module(block, values)
    edited = copy.deepcopy(values)
    edited["native_episode"]["roles"]["perception"]["thinking_variants"]["arms"][0]["thinking_policy"] = {"solver": OFF}
    with pytest.raises(cm.ConsumptionModuleConfigError, match="differ"):
        cm.verify_declared_module(block, edited)


def test_the_compiler_applies_the_parsers_refusals_before_writing():
    block = _module_block()
    block["columns"][1]["thinking_policy"] = copy.deepcopy(POLICY["perception-off"])
    with pytest.raises(cm.ConsumptionModuleConfigError, match="same policy"):
        cm.compile_module(block, carrier_module_hooks())
    block = _module_block()
    block["columns"][0]["thinking_policy"] = {"perception": {"temperature": 0}}
    with pytest.raises(cm.ConsumptionModuleConfigError, match="thinking_policy"):
        cm.compile_module(block, carrier_module_hooks())
    block = _module_block()
    block["columns"][0]["extra"] = 1
    with pytest.raises(cm.ConsumptionModuleConfigError, match="keys must be exactly"):
        cm.compile_module(block, carrier_module_hooks())
    block = _module_block()
    del block["thinking_frame"]
    with pytest.raises(cm.ConsumptionModuleConfigError, match="thinking_frame is required"):
        cm.compile_module(block, carrier_module_hooks())


def test_a_carrier_without_the_frame_refuses_the_column_and_kinds_do_not_mix():
    hooks = dataclasses.replace(carrier_module_hooks(), thinking_variant_frame=None)
    with pytest.raises(cm.ConsumptionModuleConfigError, match="thinking_variant_frame"):
        cm.compile_module(_module_block(), hooks)
    block = _module_block()
    block["columns"].append({
        "column_id": "t9", "kind": "template", "node": "perception",
        "template": {"relpath": "configs/probes/nx/t9.txt", "sha256": "f" * 64}, "template_tokens": 400,
    })
    with pytest.raises(cm.ConsumptionModuleConfigError, match="one fan-out"):
        cm.parse_consumption_module_block(block)


def test_the_v5_perception_receipt_is_a_registered_node_receipt():
    receipt = cm.module_header_receipt(
        cm.compile_module(_module_block(), carrier_module_hooks()),
        node_receipts=[{"schema": PERCEPTION_BRANCH_RECEIPT_SCHEMA_V5, "pointer": "perception_branches"}],
    )
    cm.validate_module_header_receipt(receipt)
    assert receipt["program_ceiling"] == 10


# ---------------------------------------------------------------------------
# 6. The column scorer's arm-group parser and the review-off rehearsal profile
# ---------------------------------------------------------------------------


def test_the_official_column_scorer_parses_a_thinking_group_and_refuses_double_declaration():
    import sys
    from pathlib import Path

    scripts = Path(__file__).resolve().parents[2] / "scripts" / "analysis"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import stage3_rollout_score as mod

    group = mod.parse_perception_arm_group({}, {"phase_id": "perception", "thinking_variants": _block()}, {})
    assert group.is_thinking and group.branch_ids == _group().branch_ids
    with pytest.raises(mod.Stage3ScoreError, match="beside branches or template_variants"):
        mod.parse_perception_arm_group({}, {"phase_id": "perception", "thinking_variants": _block(), "branches": {}}, {})
    with pytest.raises(mod.Stage3ScoreError):
        mod.parse_perception_arm_group({}, {"phase_id": "perception", "thinking_variants": {"arms": []}}, {})


def test_the_review_off_rehearsal_profile_admits_a_thinking_group():
    from speech_aware_evidence_acquisition.analysis import native_graph_rehearsal as graph

    v = _values()
    v["native_graph_capacity_profile"] = "review-off-v1"
    parsed = graph.rehearsal_profile(v, "review-off-v1")
    assert parsed.max_contacts == 10 and parsed.perception_branch_group.is_thinking


def test_the_dry_run_walks_every_thinking_arm_model_free_and_reports_each_arms_node_decoding(tmp_path):
    from speech_aware_evidence_acquisition.analysis.native_episode_dry_run import dry_run_native_episode
    from speech_aware_evidence_acquisition.rails.controllers import PhaseProgram, PhaseSpec
    from speech_aware_evidence_acquisition.rails.material import PhaseMaterial

    from test_rails_frozen_core_client import _World as DryWorld, _plan
    from test_rails_runner import _FakeAdapter, _knowledge_snapshot

    group = _group()
    world = DryWorld(tmp_path)
    world.samples = world.samples[:1]
    sample = world.samples[0]
    program = PhaseProgram(
        program_id="dry-run-thinking-policy-proof-v1",
        phases=tuple(
            PhaseSpec(name=phase, purpose="answer" if phase == "solver" else phase, knowledge="supplied", response_format_id=None, barrier=False)
            for phase in harness_module.PHASES
        ),
        max_contacts=10, stop_rule="native-role-episode",
    ).validate()
    episode = _perception_live_config(group=group, max_contacts=10)

    def material_for_phase(phase, context, prior):
        return PhaseMaterial(instruction=f"dry-run instruction for {phase}", response_format=None, contact_id=f"dry-run:{phase}",
                             purpose="answer" if phase == "solver" else phase).validate()

    phase_binding = {
        "material_for_phase": material_for_phase, "supply_for_phase": None, "knowledge_snapshot": _knowledge_snapshot(),
        "speech_packet_bindings": {sample.sample_id: {"packet_id": sample.audio_ref.path, "sha256": sample.audio_ref.sha256}},
        "query_source": "speech_audio", "supply_specs": {},
    }
    runtime = SimpleNamespace(
        _composed=SimpleNamespace(values={}), _plan=_plan(), _samples=tuple(world.samples), _adapter=_FakeAdapter(samples=tuple(world.samples)),
        _phase_supply_seeds=lambda *args, **kwargs: ({}, {}),
        _dry_run_binding={
            "policy": program.program_id, "program": program, "episode": episode, "phase_binding": phase_binding, "store_ids": (),
            "supply_variant_for_phase": None, "template_variant_materials": {}, "values": _values(),
        },
    )
    document = dry_run_native_episode(
        runtime, answers={"perception": "perception draft", "solver": "solver draft"}, node_order=("perception", "solver"),
    ).as_json()
    perception = next(n for n in document["nodes"] if n["phase"] == "perception")
    arms = {a["arm_id"]: a for a in perception["supply_variant_arms"]}
    assert list(arms) == list(fam_arm_order())
    locked = hashlib.sha256(b"dry-run instruction for perception").hexdigest()
    assert len({a["instruction_sha256"] for a in arms.values()}) == 1 and arms["both-on"]["instruction_sha256"] == locked
    on = {"thinking_budget_tokens": 3072, "chat_template_kwargs": {"enable_thinking": True}, "max_tokens": 4096}
    off = {"thinking_budget_tokens": None, "chat_template_kwargs": {"enable_thinking": False}, "max_tokens": 1024}
    assert arms["both-on"]["node_decoding"] == arms["both-on-twin"]["node_decoding"] == {"perception": on, "solver": on}
    assert arms["perception-off"]["node_decoding"] == {"perception": off, "solver": on}
    assert arms["solver-off"]["node_decoding"] == {"perception": on, "solver": off}
    assert arms["both-off"]["node_decoding"] == {"perception": off, "solver": off}
    assert arms["solver-off"]["thinking_policy"] == {"solver": OFF} and arms["both-on"]["thinking_policy"] is None
    assert len({tuple(a["supplied_value_ids"]) for a in arms.values()}) == 1                # the evidence is unvaried
    assert next(n for n in document["nodes"] if n["phase"] == "solver")["supply_variant_arms"] == []


def fam_arm_order():
    return _group().branch_ids
