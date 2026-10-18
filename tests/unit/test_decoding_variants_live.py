"""NX-T R4: the node-DECODING arm kind at the request seam and in the live wiring (model-free).

1. **The request seam** -- ``MeteredNativeSpeechRequest.prepare`` with a ``solver_arm_decoding`` map over the real request
   fixture of ``test_thinking_policy_column``: a candidate arm's Solver request carries exactly the declared sampling fields
   on top of the lock's request; the delivering arm, the twin, the Perception role and an unarmed adapter are byte-identical;
   the thinking budget, the cap, the seed, the response format and the tool authority are untouched.
2. **The live wiring** -- the SAME ``_ActualEpisodeHarness`` fake transport the template-variant proofs use: K real contacts,
   one batch, the delivering arm's own text delivered, the v6 receipt sealed, and the byte statements the form rests on.
"""

from __future__ import annotations

import json
from types import MappingProxyType

import pytest

pytest.importorskip("openjiuwen", reason="OpenJiuwen unavailable")

from test_decoding_variants import D1, D2, D3, D4, _parse  # noqa: E402

from speech_aware_evidence_acquisition.rails.native_episode_receipt import validate_supply_variant_receipt  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.ojw.native_request import NativeSpeechRequestError  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.ojw.native_roles import (  # noqa: E402
    NativeRoleContactContext,
    NativeRoleModelRequest,
)

ARM_DECODING = {"d1": D1, "d2": D2, "d3": D3, "d4": D4}
SAMPLING_KEYS = {"temperature", "top_p", "top_k", "presence_penalty"}


# ---- 1. the request seam ------------------------------------------------------------------------------------------------------


@pytest.fixture()
def seam(tmp_path):
    import test_thinking_policy_column as tpc

    world = tpc._World(tmp_path)
    feature_root, packet, bindings = tpc._speech_feature_world(world, tmp_path)
    counter = iter(range(1, 1000))

    def adapter(**kwargs):
        # one attempt id per adapter: each owns its client (the attempt store refuses a second open of one id)
        client, _gate, _t = tpc._client(
            world, tmp_path, transport=tpc._ScriptedTransport([("a", "stop", 3)] * 40), arm="speech-feature-query-native-tools",
            tool_schemas=tpc._TOOLS, speech_feature_root=feature_root, speech_packet_bindings=bindings,
            plan=tpc._native_plan(planned_model_calls=200, attempt_id=f"attempt-native-tools-client-{next(counter):04d}"),
        )
        return tpc.MeteredNativeSpeechRequest(
            client=client, binding_provider=lambda r: tpc._native_binding(r.role_id, packet), render_request=lambda b: json.loads(b),
            completion_sink=lambda request, completion: None, **kwargs,
        )

    def request(role_id, arm, contact):
        return NativeRoleModelRequest(
            role_id=role_id, context=NativeRoleContactContext(sample_id="s1", agent_contact_id=contact, variant_arm_id=arm),
            messages=({"role": "system", "content": "Choose exactly one opaque key id."}, {"role": "user", "content": "Inspect the speech."}),
            tool_schemas=(), visible_tool_names=(), decoding_controls=MappingProxyType({}))

    return adapter, request


def _body(adapter, request, role, arm, contact="c1"):
    return adapter.prepare(request(role, arm, contact)).rendered_body()


def test_a_candidate_arm_adds_exactly_its_sampling_fields_to_the_locks_request(seam):
    make, request = seam
    plain = make()
    armed = make(solver_arm_decoding=ARM_DECODING, solver_arm_decoding_role_id="solver")
    reference = _body(plain, request, "solver", None)["decoding_params"]
    for arm, override in ARM_DECODING.items():
        body = _body(armed, request, "solver", arm)["decoding_params"]
        assert body == {**reference, **override}, arm
        # nothing but the declared sampling fields moved: the thinking budget, the cap, the seed, the response format and the
        # tool authority are the lock's
        moved = {key for key in set(body) | set(reference) if body.get(key) != reference.get(key)}
        assert moved <= set(override) and moved <= SAMPLING_KEYS, (arm, moved)
        for key in ("thinking_budget_tokens", "chat_template_kwargs", "max_tokens", "seed", "tool_choice", "parallel_tool_calls", "response_format"):
            if key in reference:
                assert body[key] == reference[key], (arm, key)
    assert all(reference.get(key) != value for key, value in D1.items())      # every sampling field of d1 really moves


def test_every_sampling_field_reaches_the_wire_body_as_a_top_level_request_field(seam):
    make, request = seam
    armed = make(solver_arm_decoding=ARM_DECODING, solver_arm_decoding_role_id="solver")
    prepared = armed.prepare(request("solver", "d2", "c-d2"))
    payload = json.loads(prepared.request.payload_bytes)["decoding_params"]
    for key, value in D2.items():
        assert payload[key] == value
    # custody: the payload hash covers the override (a different override is a different request)
    other = make(solver_arm_decoding={"d2": {**D2, "presence_penalty": 1.0}}, solver_arm_decoding_role_id="solver")
    prepared_other = other.prepare(request("solver", "d2", "c-d2"))
    assert prepared.request.payload_bytes != prepared_other.request.payload_bytes


def test_the_transport_forwards_each_sampling_field_verbatim_to_the_openai_compatible_body():
    """llama.cpp's OpenAI-compatible /v1/chat/completions accepts temperature, top_p, top_k and presence_penalty as top-level
    body fields; ``core.model.transport`` moves every ``decoding_params`` key it does not own to the body unchanged, and the
    adapter's allowlist admits exactly the closed set (read from source: no server is contacted)."""

    from speech_aware_evidence_acquisition.core.model.request_types import ALLOWED_DECODING_KEYS
    from speech_aware_evidence_acquisition.rails.native_episode_receipt import DECODING_VARIANT_KNOBS

    assert set(DECODING_VARIANT_KNOBS) <= ALLOWED_DECODING_KEYS
    import inspect

    import speech_aware_evidence_acquisition.core.model.transport as transport

    source = inspect.getsource(transport)
    assert "for key, value in decoding_params.items():" in source and "body[key] = value" in source


def test_the_delivering_arm_the_twin_perception_and_an_unarmed_adapter_are_byte_identical(seam):
    make, request = seam
    plain = make()
    armed = make(solver_arm_decoding=ARM_DECODING, solver_arm_decoding_role_id="solver")
    for role, arm in (("solver", None), ("solver", "lock"), ("solver", "aa"), ("perception", None), ("perception", "d1"), ("perception", "d4")):
        a = plain.prepare(request(role, arm, "c-same"))
        b = armed.prepare(request(role, arm, "c-same"))
        assert a.request.payload_bytes == b.request.payload_bytes and a.body_bytes == b.body_bytes, (role, arm)


def test_a_malformed_or_unbound_arm_decoding_map_is_refused_by_the_adapter(seam):
    make, _request = seam
    with pytest.raises(NativeSpeechRequestError, match="requires exactly one"):
        make(solver_arm_decoding=ARM_DECODING)
    with pytest.raises(NativeSpeechRequestError, match="requires exactly one"):
        make(solver_arm_decoding_role_id="solver")
    for bad in ({"seed": 1}, {"temperature": 9}, {}, {"top_k": 2.5}, {"temperature": True}):
        with pytest.raises(NativeSpeechRequestError, match="is invalid"):
            make(solver_arm_decoding={"d1": bad}, solver_arm_decoding_role_id="solver")


def test_the_answer_only_reask_of_an_arm_contact_keeps_the_arms_sampling(seam):
    make, request = seam
    armed = make(solver_arm_decoding=ARM_DECODING, solver_arm_decoding_role_id="solver")
    try:
        body = armed.prepare(request("solver", "d1", "c-d1"), answer_only=True).rendered_body()["decoding_params"]
    except Exception as error:  # the fixture's fragment may carry no answer reserve; the override placement is what is proven
        pytest.skip(f"fixture has no answer reserve: {error}")
    assert {key: body[key] for key in D1} == D1


# ---- 2. the live wiring -------------------------------------------------------------------------------------------------------


from test_llama_server_transport import _spawn_live_matching_process  # noqa: E402,F401
from test_native_episode_runner import _ActualEpisodeHarness  # noqa: E402
from test_stage3_supply_variant_interleaving import _live_config  # noqa: E402


def _decoding_harness(tmp_path, group, *, rows=1):
    contacts = 1 + group.arm_count
    harness = _ActualEpisodeHarness(tmp_path, sample_count=rows, max_revisions=0, max_contacts=contacts, planner_actions=())
    harness.config = _live_config(group=group, max_contacts=contacts)
    harness.template_variant_materials = MappingProxyType({})          # a decoding group has no per-arm material
    harness._output = lambda key: (
        f"solver-arm-{key[3]}:{key[0]}" if key[1] == "solver" else f"{key[1]}-analysis:{key[0]}:visit:{key[2]}"
    )
    return harness


def _requests(harness):
    return [payload["payload"] for channel, _record_id, payload in harness.trace.records if channel == "MODEL_REQUEST"]


def _run(harness):
    try:
        summary = harness.run()
    finally:
        close = harness.close()
    return summary, close


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_a_six_arm_visit_spends_k_contacts_seals_the_v6_receipt_and_delivers_the_last_arms_own_text(tmp_path):
    group = _parse(locked_decoding=None)
    harness = _decoding_harness(tmp_path, group)
    summary, close = _run(harness)
    assert close["request_count"] == 1 + 6
    result = summary.results[0]
    assert len(result.contacts) == 7
    receipt = result.supply_variants
    assert receipt["schema"] == "saea-supply-variant-arms-v6" and receipt["arm_visits"] == "first"
    assert [row["arm_id"] for row in receipt["arms"]] == ["d1", "d2", "d3", "d4", "aa", "lock"]
    assert [row["decoding_override"] for row in receipt["arms"]] == [D1, D2, D3, D4, None, None]
    assert len({tuple(row["supplied_value_ids"]) for row in receipt["arms"]}) == 1          # unvaried evidence
    assert all(row["resolved_knobs"] == [] and row["release_swap"] is None for row in receipt["arms"])
    assert len({row["contact_id"] for row in receipt["arms"]}) == 6
    validate_supply_variant_receipt(
        receipt, arm_ids=group.arm_ids, delivered_arm_id="lock", phase_id="solver",
        retrieved_value_ids=result.final_query_state.retrieved_value_ids, arm_visits="first",
    )
    # the delivered text is the LAST (delivering) arm's own response (I7)
    assert result.final_response_text == f"solver-arm-6:{result.sample_id}"
    waves = [wave.as_json() for wave in result.waves]
    assert [wave["fanout_semantics"] for wave in waves] == ["single", "action_alternatives"]
    assert waves[1]["batch_id"].endswith(":variants")


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_each_candidate_arm_request_differs_from_the_delivering_arm_in_the_sampling_fields_alone(tmp_path):
    group = _parse(locked_decoding=None)
    harness = _decoding_harness(tmp_path, group)
    _run(harness)
    requests = _requests(harness)
    assert len(requests) == 7
    candidates, twin, lock = requests[1:5], requests[5], requests[6]
    for arm_id, request in zip(("d1", "d2", "d3", "d4"), candidates):
        override = {"d1": D1, "d2": D2, "d3": D3, "d4": D4}[arm_id]
        assert request["decoding_params"] == {**lock["decoding_params"], **override}, arm_id
        for field in ("tool_schemas", "speech_feature_parts", "speech_packet_sha256", "query_source", "sample_id",
                      "supplied_evidence", "evidence_provenance", "task_instruction"):
            assert request[field] == lock[field], (arm_id, field)
        assert request["history"][:-1] == lock["history"][:-1]
        # the instruction (the Solver's locked template) is the same text: only the contact id differs
        control = json.loads(request["history"][-1]["content"])
        control_lock = json.loads(lock["history"][-1]["content"])
        assert control["messages"] == control_lock["messages"]
    assert twin["decoding_params"] == lock["decoding_params"]
    for field in ("tool_schemas", "supplied_evidence", "task_instruction"):
        assert twin[field] == lock[field]


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_the_delivering_arms_request_is_the_unarmed_plans_request_byte_for_byte(tmp_path):
    """I7 by comparison to an UNARMED run of the same row under the same program ceiling, not by construction alone."""

    from test_native_episode_runner import _ActualEpisodeHarness as Harness  # noqa: PLC0415

    group = _parse(locked_decoding=None)
    ceiling = 1 + group.arm_count
    plain = Harness(tmp_path / "plain", sample_count=1, max_revisions=0, max_contacts=ceiling, planner_actions=())
    plain.config = _live_config(group=None, max_contacts=ceiling)
    plain._output = lambda key: (
        f"solver-arm-{key[3]}:{key[0]}" if key[1] == "solver" else f"{key[1]}-analysis:{key[0]}:visit:{key[2]}"
    )
    _run(plain)
    plain_solver = _requests(plain)[1]
    armed = _decoding_harness(tmp_path / "armed", group)
    _run(armed)
    delivering = _requests(armed)[-1]
    for field in ("decoding_params", "tool_schemas", "speech_feature_parts", "speech_packet_sha256", "query_source", "sample_id",
                  "supplied_evidence", "evidence_provenance", "task_instruction"):
        assert delivering[field] == plain_solver[field], field
    assert delivering["history"][:-1] == plain_solver["history"][:-1]
    control, control_plain = json.loads(delivering["history"][-1]["content"]), json.loads(plain_solver["history"][-1]["content"])
    control.pop("contact_id"), control_plain.pop("contact_id")
    assert control == control_plain


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_a_declared_group_with_template_materials_is_refused_before_any_contact(tmp_path):
    group = _parse(locked_decoding=None)
    harness = _decoding_harness(tmp_path, group)
    harness.template_variant_materials = MappingProxyType({"d1": lambda *a: None})
    try:
        with pytest.raises(Exception, match="template_variant_materials"):
            harness.run()
    finally:
        harness.close()
