"""NX programme E1 (2026-10-09): the node-template arm kind, wired end to end.

Four layers, all model-free:

1. **The configuration** -- ``roles.solver.template_variants`` through
   ``load_native_episode_config``: the ceiling (the review-off graph plus
   K - 1), the program-id agreement, and the refusals the loader adds.
2. **The live wiring** -- the SAME ``_ActualEpisodeHarness`` fake transport the
   supply-variant proofs use: K real contacts, one contact batch, ONE registered
   Solver state, the delivering arm's own text delivered, and -- the byte
   statements the form rests on -- the delivering arm's request equal to the
   plan's (an UNARMED run) and a template arm differing from it in the
   instruction text and nothing else.
3. **The dry-run walk** -- ``dry_run_native_episode`` over a synthetic row.
4. **The custody** -- a sealed row with a v4 receipt passes invariant I7v.
"""

from __future__ import annotations

import copy
import hashlib
import json
from types import MappingProxyType

import pytest

from speech_aware_evidence_acquisition.rails.native_episode_config import (
    load_native_episode_config,
)
from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
    validate_supply_variant_receipt,
)
from speech_aware_evidence_acquisition.rails.supply_variants import parse_template_variants
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

FIT = {
    "slot_tokens": 24576,
    "completion_ceiling": 640,
    "base_prompt_tokens": 9600,
    "tokens_per_supplied_item": 120,
}
LOCKED = "probes/slurp_native_role_solver_v2.txt"
SHA = {name: name * 64 for name in "abcd"}


def _pin(name, sha):
    return {"relpath": f"configs/probes/nx/{name}.txt", "sha256": sha}


def _block(*, twin=True, candidates=2):
    arms = [
        {"arm_id": f"t{i}", "instruction_template": _pin(f"t{i}", SHA["abcd"[i - 1]]),
         "template_tokens": 400}
        for i in range(1, candidates + 1)
    ]
    if twin:
        arms.append({"arm_id": "aa", "replicate_of": "lock"})
    arms.append({"arm_id": "lock", "deliver": True, "template_tokens": 380})
    return {
        "node": "solver", "arms": arms, "max_supplied_items": 4,
        "fit_estimate": dict(FIT),
    }


def _group(**kwargs):
    return parse_template_variants(
        _block(**kwargs), role_kind="solver", phase_id="solver", locked_template=LOCKED,
    )


# ---------------------------------------------------------------------------
# 1. The configuration
# ---------------------------------------------------------------------------


def _values(*, candidates=2, twin=True):
    from test_review_off_capacity import values

    v = copy.deepcopy(values(False))
    v["phase_material"] = {"solver": {"instruction_template": LOCKED}}
    v["native_episode"]["roles"]["solver"]["template_variants"] = _block(
        candidates=candidates, twin=twin,
    )
    return v


def _program(ceiling):
    from test_native_episode_config import program

    return program(ceiling=ceiling)


def test_the_loader_parses_the_group_and_adds_k_minus_one_to_the_ceiling():
    # Review-off graph: perception 1 + solver 1 = 2; K = 2 candidates + twin +
    # the delivering arm = 4 contacts at the Solver's first visit -> 2 + 3.
    config = load_native_episode_config(_values(), _program(5))
    assert config.max_contacts == 5
    group = config.supply_variant_group
    assert group is not None and group.is_template
    assert group.arm_ids == ("t1", "t2", "aa", "lock")
    assert config.supply_variant_arm_count == 4
    assert config.supply_variant_phase_id == "solver"
    assert config.role("solver").supply_variants is group
    assert not config.review_loop_enabled


def test_the_program_ceiling_must_equal_the_bounded_graph_ceiling():
    with pytest.raises(ValueError, match="program contact ceiling must equal"):
        load_native_episode_config(_values(), _program(4))


def test_a_node_without_its_locked_template_is_refused():
    v = _values()
    v["phase_material"] = {}
    with pytest.raises(ValueError, match="requires the node's own"):
        load_native_episode_config(v, _program(5))


def test_a_candidate_naming_the_locked_template_is_refused_by_the_loader():
    v = _values()
    v["native_episode"]["roles"]["solver"]["template_variants"]["arms"][0][
        "instruction_template"
    ] = {"relpath": LOCKED, "sha256": SHA["d"]}
    with pytest.raises(ValueError, match="locked template"):
        load_native_episode_config(v, _program(5))


def test_template_and_supply_variants_cannot_share_a_node():
    v = _values()
    v["native_episode"]["roles"]["solver"]["supply_variants"] = {"arms": [], "fit_estimate": {}}
    with pytest.raises(ValueError, match="cannot combine"):
        load_native_episode_config(v, _program(5))


@pytest.mark.parametrize("role", ["reviewer", "planner"])
def test_a_variant_declared_on_another_node_is_refused_by_name(role):
    v = _values()
    block = v["native_episode"]["roles"]["solver"].pop("template_variants")
    v["native_episode"]["roles"][role]["template_variants"] = block
    with pytest.raises(ValueError, match=f"roles.{role}.template_variants is refused"):
        load_native_episode_config(v, _program(2))


def test_a_block_naming_another_node_than_the_one_it_sits_on_is_refused():
    v = _values()
    v["native_episode"]["roles"]["solver"]["template_variants"]["node"] = "perception"
    with pytest.raises(ValueError, match="declared on exactly the node it names"):
        load_native_episode_config(v, _program(5))


def test_a_supply_knob_on_an_arm_is_refused_by_the_loader():
    v = _values()
    v["native_episode"]["roles"]["solver"]["template_variants"]["arms"][0][
        "overrides"
    ] = {"knowledge_stores.train-exemplars.phase_supply.solver.k": 10}
    with pytest.raises(ValueError, match="overrides exactly its instruction_template"):
        load_native_episode_config(v, _program(5))


def test_the_review_off_rehearsal_profile_admits_a_template_group_and_the_family_carries_its_ceiling():
    from speech_aware_evidence_acquisition.analysis import native_graph_rehearsal as graph

    v = _values()  # review-off, two candidates + twin + lock -> ceiling 5
    v["policy"] = "phase-native-module-v1-c5"
    v["native_graph_capacity_profile"] = "review-off-v1"
    parsed = graph.rehearsal_profile(v, "review-off-v1")
    assert parsed.max_contacts == 5 and parsed.supply_variant_group.is_template
    for ceiling in range(4, 11):
        from speech_aware_evidence_acquisition.rails.controllers import module_program_family_id

        assert module_program_family_id(ceiling) == f"phase-native-module-v1-c{ceiling}"


def test_a_config_without_the_key_is_unchanged():
    v = _values()
    del v["native_episode"]["roles"]["solver"]["template_variants"]
    config = load_native_episode_config(v, _program(2))
    assert config.supply_variant_group is None and config.max_contacts == 2


# ---------------------------------------------------------------------------
# 2. The live wiring
# ---------------------------------------------------------------------------

pytest.importorskip("openjiuwen", reason="OpenJiuwen unavailable")

from test_llama_server_transport import _spawn_live_matching_process  # noqa: E402,F401
from test_native_episode_runner import PHASES, _ActualEpisodeHarness  # noqa: E402
from test_stage3_supply_variant_interleaving import (  # noqa: E402
    _live_config,
    _live_config_with_review,
)

TEMPLATE_TEXT = {
    "t1": "TEMPLATE-ARM-ONE: list every entity once.",
    "t2": "TEMPLATE-ARM-TWO: answer with an empty entity list when unsure.",
}


def _builder(harness, arm_id, *, response_format=None):
    from speech_aware_evidence_acquisition.rails.material import PhaseMaterial

    def build(phase, context, sealed):
        visit = harness.material_visits[(context.sample_id, phase)]
        marker = f"native-role:{phase}:sample:{context.sample_id}:visit:{visit}"
        return PhaseMaterial(
            instruction=f"{marker}\n{TEMPLATE_TEXT[arm_id]}",
            response_format=response_format,
            contact_id=marker, purpose=phase,
        ).validate()

    return build


def _arm_output(key):
    sample_id, phase, visit, turn = key
    if phase == "solver":
        return f"solver-arm-{turn}:{sample_id}"
    return f"{phase}-analysis:{sample_id}:visit:{visit}"


def _template_harness(tmp_path, group, *, rows=1, max_contacts=None, **kwargs):
    contacts = max_contacts or 1 + group.arm_count
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=rows, max_revisions=0, max_contacts=contacts,
        planner_actions=(),
    )
    harness.config = _live_config(group=group, max_contacts=contacts)
    harness.template_variant_materials = MappingProxyType({
        arm.arm_id: _builder(harness, arm.arm_id)
        for arm in group.arms if arm.instruction_template is not None
    })
    harness._output = _arm_output
    return harness


def _requests(harness):
    return [
        payload["payload"]
        for channel, _record_id, payload in harness.trace.records
        if channel == "MODEL_REQUEST"
    ]


def _control(request):
    """The contact's own control turn, parsed: it carries the system message,
    the original query (the role instruction) and the contact id."""

    turn = request["history"][-1]
    assert turn["role"] == "control"
    return json.loads(turn["content"])


def _instruction(request):
    return _control(request)["messages"][1]["content"]


def _control_without_instruction(request):
    control = _control(request)
    control.pop("contact_id")
    messages = [dict(m) for m in control["messages"]]
    messages[1].pop("content")
    control["messages"] = messages
    return control


def _run(harness):
    try:
        summary = harness.run()
    finally:
        close = harness.close()
    return summary, close


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_a_three_arm_visit_spends_k_contacts_and_delivers_the_last_arms_own_text(tmp_path):
    group = _group(twin=False)  # t1, t2, lock
    harness = _template_harness(tmp_path, group)
    summary, close = _run(harness)

    assert close["request_count"] == 4  # perception + 3 arms
    result = summary.results[0]
    assert len(result.contacts) == 4
    receipt = result.supply_variants
    assert receipt["schema"] == "saea-supply-variant-arms-v4"
    assert [row["arm_id"] for row in receipt["arms"]] == ["t1", "t2", "lock"]
    assert [row["deliver"] for row in receipt["arms"]] == [False, False, True]
    assert receipt["arms"][0]["instruction_template"] == {
        "relpath": "probes/nx/t1.txt", "sha256": SHA["a"],
    }
    assert receipt["arms"][1]["instruction_template"]["sha256"] == SHA["b"]
    assert receipt["arms"][2]["instruction_template"] is None
    # Unvaried supply: every arm carries the delivering arm's ids.
    assert len({tuple(row["supplied_value_ids"]) for row in receipt["arms"]}) == 1
    assert all(row["resolved_knobs"] == [] for row in receipt["arms"])
    assert len({row["contact_id"] for row in receipt["arms"]}) == 3
    validate_supply_variant_receipt(
        receipt, arm_ids=group.arm_ids, delivered_arm_id="lock", phase_id="solver",
        retrieved_value_ids=result.final_query_state.retrieved_value_ids,
        arm_visits="first",
    )
    # The delivered text is the LAST (delivering) arm's own response (I7).
    assert result.final_response_text == _arm_output((result.sample_id, "solver", 1, 3))
    solver_states = [s for s in result.agent_states if s.state_kind == "phase:solver"]
    assert len(solver_states) == 1 and solver_states[0].content == result.final_response_text
    waves = [wave.as_json() for wave in result.waves]
    assert [wave["fanout_semantics"] for wave in waves] == ["single", "action_alternatives"]
    assert waves[1]["batch_id"].endswith(":variants")
    assert len({p["query_state_sha256"] for p in waves[1]["contact_plans"]}) == 1


FIELDS_EQUAL = (
    "decoding_params", "tool_schemas", "speech_feature_parts", "speech_packet_sha256",
    "query_source", "key_representation_id", "matcher_policy_id", "carrier_lock_key",
    "media_relpath", "audio_seconds", "sample_rate_hz", "sample_id",
    "supplied_evidence", "evidence_provenance",
)


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_a_template_arm_differs_from_the_delivering_arm_in_the_instruction_alone(tmp_path):
    group = _group(twin=False)
    harness = _template_harness(tmp_path, group)
    _run(harness)
    requests = _requests(harness)
    assert len(requests) == 4
    t1, t2, lock = requests[1], requests[2], requests[3]
    for arm, text in ((t1, TEMPLATE_TEXT["t1"]), (t2, TEMPLATE_TEXT["t2"])):
        assert text in _instruction(arm)
        assert text not in _instruction(lock)
        for field in FIELDS_EQUAL + ("task_instruction",):
            assert arm[field] == lock[field], field
        # the same history of earlier nodes ...
        assert arm["history"][:-1] == lock["history"][:-1]
        # ... and a control turn that differs ONLY in the contact id and the
        # role instruction.
        assert _control_without_instruction(arm) == _control_without_instruction(lock)
        assert arm["history"][-1]["role"] == lock["history"][-1]["role"] == "control"
    assert _instruction(t1) != _instruction(t2)


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_the_delivering_arms_request_is_the_locked_plans_request_byte_for_byte(tmp_path):
    """I7: the delivered request is the unvaried plan's, by comparison to an
    UNARMED run of the same row under the same program ceiling, not by
    construction alone. (The ceiling is part of the plan: the visit's bounded
    "Native episode limits" text states the contacts the program still
    allows.)"""

    group = _group()  # t1, t2, aa, lock
    ceiling = 1 + group.arm_count
    plain = _ActualEpisodeHarness(
        tmp_path / "plain", sample_count=1, max_revisions=0, max_contacts=ceiling,
        planner_actions=(),
    )
    plain.config = _live_config(group=None, max_contacts=ceiling)
    plain._output = _arm_output
    _run(plain)
    plain_solver = _requests(plain)[1]

    armed = _template_harness(tmp_path / "armed", group)
    _run(armed)
    armed_requests = _requests(armed)
    delivering = armed_requests[-1]
    assert len(armed_requests) == 1 + group.arm_count

    for field in FIELDS_EQUAL + ("task_instruction",):
        assert delivering[field] == plain_solver[field], field
    assert delivering["history"][:-1] == plain_solver["history"][:-1]
    # The control turn -- system message, role instruction, limits -- is the
    # unarmed plan's own, byte for byte, up to the contact id every contact
    # carries (the delivering arm is the 3rd contact of its visit, not the 1st).
    assert _control(delivering).pop("contact_id") != _control(plain_solver).pop("contact_id")
    assert _control_without_instruction(delivering) == _control_without_instruction(plain_solver)
    assert _instruction(delivering) == _instruction(plain_solver)
    # And no arm's template text leaked into the delivered request.
    assert not any(text in _instruction(delivering) for text in TEMPLATE_TEXT.values())


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_the_twin_renders_the_delivering_arms_request_byte_for_byte(tmp_path):
    group = _group()  # t1, t2, aa (twin), lock
    harness = _template_harness(tmp_path, group)
    summary, _ = _run(harness)
    requests = _requests(harness)
    twin, lock = requests[3], requests[4]
    for field in FIELDS_EQUAL + ("task_instruction",):
        assert twin[field] == lock[field], field
    assert _instruction(twin) == _instruction(lock)
    assert _control_without_instruction(twin) == _control_without_instruction(lock)
    receipt = summary.results[0].supply_variants
    rows = {row["arm_id"]: row for row in receipt["arms"]}
    assert rows["aa"]["replicate_of"] == "lock"
    assert rows["aa"]["instruction_template"] is None


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_four_rows_are_walked_model_free_through_the_production_graph(
    tmp_path, monkeypatch,
):
    """The model-free 4-row proof: the production native graph, the
    production request renderer and the production state sealer over four
    rows, answered by canned text, with a four-arm template group."""

    import test_native_episode_runner as runner_tests

    class FourRowWorld(runner_tests._World):
        SAMPLE_SPECS = (("s1", 2.0), ("s2", 3.5), ("s3", 2.5), ("s4", 3.0))

    monkeypatch.setattr(runner_tests, "_World", FourRowWorld)
    group = _group(twin=True)  # 2 candidates + twin + lock = 4 arms
    harness = _template_harness(tmp_path, group, rows=4)
    summary, close = _run(harness)
    assert len(summary.results) == 4
    assert close["request_count"] == 4 * (1 + group.arm_count)
    for result in summary.results:
        receipt = result.supply_variants
        assert receipt["schema"] == "saea-supply-variant-arms-v4"
        assert [row["arm_id"] for row in receipt["arms"]] == list(group.arm_ids)
        validate_supply_variant_receipt(
            receipt, arm_ids=group.arm_ids, delivered_arm_id="lock", phase_id="solver",
            arm_visits="first",
        )
        assert result.final_response_text == _arm_output(
            (result.sample_id, "solver", 1, group.arm_count)
        )
    # Every row's template arms carried their own text; its delivering arm did not.
    instructions = [_instruction(r) for r in _requests(harness) if r["history"][-1]["role"] == "control"]
    assert sum(TEMPLATE_TEXT["t1"] in text for text in instructions) == 4
    assert sum(TEMPLATE_TEXT["t2"] in text for text in instructions) == 4

    # The byte statement, per row: the delivering arm's request equals the same row's request in an
    # UNARMED 4-row run under the same program ceiling.
    plain = _ActualEpisodeHarness(
        tmp_path / "plain", sample_count=4, max_revisions=0, max_contacts=1 + group.arm_count,
        planner_actions=(),
    )
    plain.config = _live_config(group=None, max_contacts=1 + group.arm_count)
    plain._output = _arm_output
    _run(plain)

    def by_sample(requests):
        grouped = {}
        for request in requests:
            grouped.setdefault(request["sample_id"], []).append(request)
        return grouped

    armed_rows, plain_rows = by_sample(_requests(harness)), by_sample(_requests(plain))
    assert set(armed_rows) == set(plain_rows) == {"s1", "s2", "s3", "s4"}
    identical = 0
    for sample_id, armed_requests in armed_rows.items():
        assert len(armed_requests) == 1 + group.arm_count and len(plain_rows[sample_id]) == 2
        delivering, unarmed = armed_requests[-1], plain_rows[sample_id][1]
        for field in FIELDS_EQUAL + ("task_instruction",):
            assert delivering[field] == unarmed[field], (sample_id, field)
        assert delivering["history"][:-1] == unarmed["history"][:-1]
        assert _instruction(delivering) == _instruction(unarmed)
        assert _control_without_instruction(delivering) == _control_without_instruction(unarmed)
        identical += 1
    print("NX-REHEARSAL-SUMMARY " + json.dumps({
        "rows": len(summary.results),
        "arms_per_row": list(group.arm_ids),
        "model_free_requests": close["request_count"],
        "contacts_per_row": [len(r.contacts) for r in summary.results],
        "receipt_schema": summary.results[0].supply_variants["schema"],
        "templates": {
            row["arm_id"]: row["instruction_template"]
            for row in summary.results[0].supply_variants["arms"]
        },
        "delivering_request_identical_to_unarmed_plan": f"{identical}/4 rows",
    }, sort_keys=True))


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_a_revision_visit_contacts_the_delivering_arm_alone(tmp_path):
    group = _group(twin=False)
    # perception 1 + round0 [solver 3 + reviewer + planner] + round1 [solver 1 +
    # reviewer + planner] = 1 + 5 + 3 = 9 = base 7 + (K - 1) 2.
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=1, max_contacts=9,
        planner_actions=("REVISE", "ACCEPT"),
    )
    harness.config = _live_config_with_review(group=group, max_contacts=9, max_revisions=1)
    harness.template_variant_materials = MappingProxyType({
        arm.arm_id: _builder(harness, arm.arm_id)
        for arm in group.arms if arm.instruction_template is not None
    })

    def output(key):
        sample_id, phase, visit, turn = key
        if phase == "planner":
            return ("REVISE", "ACCEPT")[visit - 1]
        if phase == "solver":
            return f"solver-arm-{visit}-{turn}:{sample_id}"
        return f"{phase}-analysis:{sample_id}:visit:{visit}"

    harness._output = output
    summary, close = _run(harness)
    assert close["request_count"] == 9
    result = summary.results[0]
    solver_visits = [
        v for v in result.native_episode_receipt["role_visits"] if v["stage"] == "solver"
    ]
    assert [len(v["execution_receipt"]["contacts"]) for v in solver_visits] == [3, 1]
    assert result.supply_variants["visit_index"] == 0
    assert result.final_response_text == output((result.sample_id, "solver", 2, 1))
    # the revisit's request carries NO template arm text
    revisit = _requests(harness)[-3]
    assert not any(text in _instruction(revisit) for text in TEMPLATE_TEXT.values())


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_a_declared_group_without_its_material_builders_is_refused_before_any_contact(tmp_path):
    group = _group(twin=False)
    harness = _template_harness(tmp_path, group)
    harness.template_variant_materials = None
    try:
        with pytest.raises(Exception, match="template_variant_materials"):
            harness.run()
    finally:
        harness.close()


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_builders_for_an_undeclared_arm_are_refused(tmp_path):
    group = _group(twin=False)
    harness = _template_harness(tmp_path, group)
    harness.template_variant_materials = MappingProxyType({
        **harness.template_variant_materials, "t9": _builder(harness, "t1"),
    })
    try:
        with pytest.raises(Exception, match="template_variant_materials"):
            harness.run()
    finally:
        harness.close()


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_builders_without_a_declared_group_are_refused(tmp_path):
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0, max_contacts=2, planner_actions=(),
    )
    harness.template_variant_materials = MappingProxyType({"t1": _builder(harness, "t1")})
    try:
        with pytest.raises(Exception, match="template_variant_materials"):
            harness.run()
    finally:
        harness.close()


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_an_arm_that_changes_the_response_format_is_refused(tmp_path):
    group = _group(twin=False)
    harness = _template_harness(tmp_path, group)
    harness.template_variant_materials = MappingProxyType({
        arm.arm_id: _builder(harness, arm.arm_id, response_format={"type": "json_object"})
        for arm in group.arms if arm.instruction_template is not None
    })
    try:
        with pytest.raises(Exception, match="changed the node's response format"):
            harness.run()
    finally:
        harness.close()


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_a_supply_resolver_beside_a_template_group_is_refused(tmp_path):
    group = _group(twin=False)
    harness = _template_harness(tmp_path, group)
    harness.supply_variant_for_phase = lambda **kwargs: None
    try:
        with pytest.raises(Exception, match="supply_variant_for_phase"):
            harness.run()
    finally:
        harness.close()


# ---------------------------------------------------------------------------
# 3. The dry-run walk
# ---------------------------------------------------------------------------


def _dry_walk(tmp_path, group):
    from types import SimpleNamespace

    from speech_aware_evidence_acquisition.analysis.native_episode_dry_run import (
        dry_run_native_episode,
    )
    from speech_aware_evidence_acquisition.rails.controllers import PhaseProgram, PhaseSpec
    from speech_aware_evidence_acquisition.rails.material import PhaseMaterial

    from test_rails_frozen_core_client import _World, _plan
    from test_rails_runner import _FakeAdapter, _knowledge_snapshot

    world = _World(tmp_path)
    world.samples = world.samples[:1]
    sample = world.samples[0]
    max_contacts = 1 + group.arm_count
    program = PhaseProgram(
        program_id="dry-run-template-proof-v1",
        phases=tuple(
            PhaseSpec(
                name=phase, purpose="answer" if phase == "solver" else phase,
                knowledge="supplied", response_format_id=None, barrier=False,
            )
            for phase in PHASES
        ),
        max_contacts=max_contacts, stop_rule="native-role-episode",
    ).validate()
    episode = _live_config(group=group, max_contacts=max_contacts)

    def material_for_phase(phase, context, prior):
        return PhaseMaterial(
            instruction=f"dry-run instruction for {phase}", response_format=None,
            contact_id=f"dry-run:{phase}", purpose="answer" if phase == "solver" else phase,
        ).validate()

    def arm_builder(arm_id):
        def build(phase, context, prior):
            return PhaseMaterial(
                instruction=f"dry-run instruction for {phase}\n{TEMPLATE_TEXT[arm_id]}",
                response_format=None, contact_id=f"dry-run:{phase}:{arm_id}", purpose=phase,
            ).validate()
        return build

    phase_binding = {
        "material_for_phase": material_for_phase, "supply_for_phase": None,
        "knowledge_snapshot": _knowledge_snapshot(),
        "speech_packet_bindings": {sample.sample_id: {
            "packet_id": sample.audio_ref.path, "sha256": sample.audio_ref.sha256,
        }},
        "query_source": "speech_audio", "supply_specs": {},
    }
    runtime = SimpleNamespace(
        _composed=SimpleNamespace(values={}), _plan=_plan(), _samples=tuple(world.samples),
        _adapter=_FakeAdapter(samples=tuple(world.samples)),
        _phase_supply_seeds=lambda *args, **kwargs: ({}, {}),
        _dry_run_binding={
            "policy": program.program_id, "program": program, "episode": episode,
            "phase_binding": phase_binding, "store_ids": (),
            "supply_variant_for_phase": None,
            "template_variant_materials": {
                arm.arm_id: arm_builder(arm.arm_id)
                for arm in group.arms if arm.instruction_template is not None
            },
        },
    )
    return dry_run_native_episode(
        runtime, answers={"perception": "perception draft", "solver": "solver draft"},
        node_order=("perception", "solver"),
    )


def test_the_dry_run_walks_every_template_arm_model_free(tmp_path):
    group = _group(twin=True)
    document = _dry_walk(tmp_path, group).as_json()
    solver = next(n for n in document["nodes"] if n["phase"] == "solver")
    arms = solver["supply_variant_arms"]
    assert [a["arm_id"] for a in arms] == ["t1", "t2", "aa", "lock"]
    assert document["delivered_arm_id"] == "lock"
    # unvaried supply: one count for every arm
    assert len({tuple(a["supplied_value_ids"]) for a in arms}) == 1
    assert all(a["resolved_knobs"] == [] for a in arms)
    by_id = {a["arm_id"]: a for a in arms}
    locked_digest = hashlib.sha256(b"dry-run instruction for solver").hexdigest()
    # The delivering arm and the twin render the node's own locked instruction.
    assert by_id["lock"]["instruction_sha256"] == by_id["aa"]["instruction_sha256"] == locked_digest
    assert by_id["lock"]["instruction_template"] is None
    # Each template arm renders its own, and they differ from the lock and each other.
    assert by_id["t1"]["instruction_template"]["sha256"] == SHA["a"]
    digests = {a["instruction_sha256"] for a in arms}
    assert len(digests) == 3
    perception = next(n for n in document["nodes"] if n["phase"] == "perception")
    assert perception["supply_variant_arms"] == []
    print("NX-DRYRUN-SUMMARY " + json.dumps({
        "delivered_arm_id": document["delivered_arm_id"],
        "arms": [
            {k: arm[k] for k in ("arm_id", "deliver", "instruction_template", "instruction_sha256",
                                 "supplied_item_count")}
            for arm in arms
        ],
    }, sort_keys=True))


# ---------------------------------------------------------------------------
# 4. The custody: a sealed row with a v4 receipt passes I7v
# ---------------------------------------------------------------------------


def _sealed_row(revisions=1):
    sample = "slurp:train:synthetic-nx"
    arm_name = "speech-feature-query-native-tools"

    def sha(value):
        return hashlib.sha256(value.encode()).hexdigest()

    trace, visits = {}, []
    arm_ids = ["t1", "t2", "lock"]
    contacts0 = []
    for index, arm_id in enumerate(arm_ids):
        rid = f"v0-{arm_id}"
        answer = f"answer-v0-{arm_id}"
        contact = {
            "agent_contact_id": f"solver:0:{index}", "request_id": rid,
            "request_sha256": sha(rid), "response_sha256": sha("envelope-" + rid),
            "response_text_sha256": sha(answer),
        }
        contacts0.append(contact)
        trace[rid + "/request"] = {
            "arm": arm_name, "payload": {"sample_id": sample},
            "payload_sha256": contact["request_sha256"],
        }
        trace[rid + "/response"] = {
            "text": answer, "response_sha256": contact["response_sha256"],
            "response_text_sha256": contact["response_text_sha256"],
        }
    visits.append({
        "role_id": "solver", "stage": "solver",
        "execution_receipt": {"contacts": contacts0, "final_contact": contacts0[-1]},
    })
    last = contacts0[-1]
    for revision in range(1, revisions + 1):
        rid = f"v{revision}"
        answer = f"answer-{rid}"
        contact = {
            "agent_contact_id": f"solver:{revision}:0", "request_id": rid,
            "request_sha256": sha(rid), "response_sha256": sha("envelope-" + rid),
            "response_text_sha256": sha(answer),
        }
        trace[rid + "/request"] = {
            "arm": arm_name, "payload": {"sample_id": sample},
            "payload_sha256": contact["request_sha256"],
        }
        trace[rid + "/response"] = {
            "text": answer, "response_sha256": contact["response_sha256"],
            "response_text_sha256": contact["response_text_sha256"],
        }
        visits.append({
            "role_id": "solver", "stage": "solver",
            "execution_receipt": {"contacts": [contact], "final_contact": contact},
        })
        last = contact
    trace["synthetic/org"] = {"org_final_query_state": {
        "query_sample_id": sample, "retrieved_value_ids": ["v:plan"],
    }}

    def arm_row(index, arm_id, template, deliver=False):
        return {
            "arm_index": index, "arm_id": arm_id, "deliver": deliver, "replicate_of": None,
            "release_swap": None, "instruction_template": template,
            "contact_id": contacts0[index]["agent_contact_id"], "resolved_knobs": [],
            "supplied_value_ids": ["v:plan"], "supplied_item_count": 1,
            "max_supplied_items": 5,
        }

    variant = {
        "schema": "saea-supply-variant-arms-v4", "phase_id": "solver",
        "arm_count": 3, "delivered_arm_id": "lock", "arm_visits": "first",
        "visit_index": 0,
        "fit_estimate": {
            "slot_tokens": 24576, "completion_ceiling": 512,
            "base_prompt_tokens": 100, "tokens_per_supplied_item": 10,
            "reserve_tokens": 3072, "prompt_limit_tokens": 20990,
        },
        "arms": [
            arm_row(0, "t1", {"relpath": "probes/nx/t1.txt", "sha256": SHA["a"]}),
            arm_row(1, "t2", {"relpath": "probes/nx/t2.txt", "sha256": SHA["b"]}),
            arm_row(2, "lock", None, deliver=True),
        ],
    }
    row = {
        "request_id": last["request_id"], "sample_id": sample,
        "carrier_lock_key": "slurp", "arm": arm_name,
        "text": trace[last["request_id"] + "/response"]["text"],
        "admitted": True, "request_sha256": last["request_sha256"],
        "response_sha256": last["response_sha256"],
        "response_text_sha256": last["response_text_sha256"],
        "native_episode_receipt": {"role_visits": visits},
        "supply_variants": variant,
    }
    return row, trace, sample, arm_name


def _verify(row, trace, sample, arm_name):
    from speech_aware_evidence_acquisition.core.bundle.outputs import (
        _verify_outputs, _verify_outputs_trace_binding,
    )

    rows = _verify_outputs(
        (json.dumps(row) + "\n").encode(), frozenset({sample}), "slurp", arm_name,
    )
    _verify_outputs_trace_binding(rows, trace)


def test_a_sealed_v4_row_passes_i7v():
    _verify(*_sealed_row(revisions=1))


def test_a_sealed_v4_row_whose_arm_names_a_second_template_twice_is_refused():
    row, trace, sample, arm_name = _sealed_row()
    row["supply_variants"]["arms"][1]["instruction_template"] = dict(
        row["supply_variants"]["arms"][0]["instruction_template"]
    )
    with pytest.raises(Exception, match="I7v"):
        _verify(row, trace, sample, arm_name)


def test_a_sealed_v4_row_whose_arm_varies_the_evidence_is_refused():
    row, trace, sample, arm_name = _sealed_row()
    row["supply_variants"]["arms"][0]["supplied_value_ids"] = ["v:other"]
    with pytest.raises(Exception, match="I7v"):
        _verify(row, trace, sample, arm_name)


def test_a_later_visit_with_more_than_one_contact_is_refused():
    row, trace, sample, arm_name = _sealed_row(revisions=1)
    later = row["native_episode_receipt"]["role_visits"][1]["execution_receipt"]["contacts"]
    later.append(dict(later[0]))
    with pytest.raises(Exception, match="I7v"):
        _verify(row, trace, sample, arm_name)
