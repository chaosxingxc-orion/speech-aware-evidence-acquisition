"""NX programme E1 for the PERCEPTION node (2026-10-10, owner decision 239): K Perception
instruction-template arms at the one Perception visit, each followed by its own level-2 Solver
contact that sees that arm's note.

Layers, all model-free:

1. **The parser and the loader** -- ``roles.perception.template_variants`` parsed into the level-2
   Perception branch group; the refusals; the ceiling ``base + 2 (K - 1)``.
2. **The production graph** -- the SAME ``_ActualEpisodeHarness`` fake transport the template and
   level-2 render proofs use, four rows, arms p1, p2, aa (twin), lock: every arm's Perception
   contact renders its own template, every arm's first-visit Solver contact renders that arm's own
   note, and the delivering arm's Perception and Solver requests are the UNARMED plan's, byte for
   byte.
3. **The seal** -- the v4 receipt through the bundle's I7v verifier and the runtime's
   ``_canonical_output_rows``; the level-2 "note differs but Solver rendering equals A's" refusal
   fires for a template branch.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections import defaultdict
from dataclasses import replace
from types import MappingProxyType, SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails.native_episode_config import (
    load_native_episode_config,
)
from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
    PERCEPTION_BRANCH_RECEIPT_SCHEMA_V4,
    validate_perception_branch_receipt,
)
from speech_aware_evidence_acquisition.rails.supply_variants import (
    PERCEPTION_BRANCH_LEVEL_SOLVER,
    PerceptionBranchError,
    parse_perception_template_variants,
    perception_branch_ceiling,
)
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

FIT = {
    "slot_tokens": 24576, "completion_ceiling": 640,
    "base_prompt_tokens": 9600, "tokens_per_supplied_item": 120,
}
LOCKED = "probes/slurp_native_role_perception_v2.txt"
SHA = {name: ("abcdef1"["abcdefg".index(name)]) * 64 for name in "abcdefg"}


def _pin(name, sha):
    return {"relpath": f"configs/probes/nx/{name}.txt", "sha256": sha}


def _block(*, twin=True, candidates=2, node="perception"):
    arms = [
        {"arm_id": f"p{i}", "instruction_template": _pin(f"p{i}", SHA["abcdefg"[i - 1]]),
         "template_tokens": 400}
        for i in range(1, candidates + 1)
    ]
    if twin:
        arms.append({"arm_id": "aa", "replicate_of": "lock"})
    arms.append({"arm_id": "lock", "deliver": True, "template_tokens": 380})
    return {"node": node, "arms": arms, "max_supplied_items": 4, "fit_estimate": dict(FIT)}


def _group(**kwargs):
    return parse_perception_template_variants(
        _block(**kwargs), phase_id="perception", locked_template=LOCKED,
    )


# ---------------------------------------------------------------------------
# 1. The parser and the loader
# ---------------------------------------------------------------------------


def test_the_parser_builds_a_level_two_branch_group_with_the_template_axis():
    group = _group()
    assert group.level == PERCEPTION_BRANCH_LEVEL_SOLVER and group.is_template
    assert group.branch_ids == ("p1", "p2", "aa", "lock")
    assert group.delivering_branch.branch_id == "lock"
    assert group.twin_branch.branch_id == "aa"
    p1 = group.branch("p1")
    assert p1.is_b and p1.instruction_template.relpath == "probes/nx/p1.txt"
    assert p1.template_tokens == 400 and p1.knobs == () and p1.key_source is None
    assert group.branch("lock").instruction_template is None
    assert group.branch("aa").instruction_template is None
    # K = 4 -> the contact term is 2 (K - 1) = 6 over the base.
    assert perception_branch_ceiling(base_ceiling=2, branch_count=4, level=2) == 8


@pytest.mark.parametrize("mutate, message", [
    (lambda b: b["arms"][0].update(overrides={"k": 3}), "overrides exactly its instruction_template"),
    (lambda b: b["arms"][0].update(release_swap={"store_id": "x"}), "overrides exactly its instruction_template"),
    (lambda b: b["arms"][0].update(unknown=1), "unknown keys"),
    (lambda b: b["arms"][0].__setitem__("instruction_template", _pin("p1", "short")), "64-hex"),
    (lambda b: b["arms"][0].__setitem__(
        "instruction_template", {"relpath": "configs/other/p1.txt", "sha256": SHA["a"]}), "allowed template roots"),
    (lambda b: b["arms"][0].__setitem__(
        "instruction_template", {"relpath": "configs/probes/../x.txt", "sha256": SHA["a"]}), "plain repository-relative"),
    (lambda b: b["arms"][0].__setitem__("instruction_template", {"relpath": "configs/probes/nx/p1.txt"}), "relpath, sha256"),
    (lambda b: b["arms"][1].__setitem__("instruction_template", b["arms"][0]["instruction_template"]), "same template"),
    (lambda b: b["arms"][0].pop("instruction_template"), "must declare an instruction_template"),
    (lambda b: b["arms"][-1].__setitem__("instruction_template", _pin("x", SHA["g"])), "delivering arm or the twin"),
    (lambda b: b["arms"][0].pop("template_tokens"), "template_tokens"),
    (lambda b: b.__setitem__("arms", [b["arms"][-1], *b["arms"][:-1]]), "LAST arm"),
    (lambda b: b.__setitem__("node", "solver"), "declared on exactly the node it names"),
    (lambda b: b["arms"][1].__setitem__("arm_id", "p1"), "distinct"),
])
def test_the_parser_refuses_by_name(mutate, message):
    block = _block()
    mutate(block)
    with pytest.raises(PerceptionBranchError.__mro__[1], match=message):
        parse_perception_template_variants(block, phase_id="perception", locked_template=LOCKED)


def test_more_than_six_candidates_and_a_missing_twin_are_refused():
    with pytest.raises(Exception, match="between 1 and 6"):
        parse_perception_template_variants(
            _block(candidates=7), phase_id="perception", locked_template=LOCKED,
        )
    with pytest.raises(PerceptionBranchError, match="exactly one twin"):
        parse_perception_template_variants(
            _block(twin=False), phase_id="perception", locked_template=LOCKED,
        )


def test_a_candidate_equal_to_the_locked_template_is_refused():
    block = _block()
    block["arms"][0]["instruction_template"] = {"relpath": LOCKED, "sha256": SHA["g"]}
    with pytest.raises(Exception, match="locked template"):
        parse_perception_template_variants(block, phase_id="perception", locked_template=LOCKED)


def _values(*, candidates=2, twin=True):
    from test_review_off_capacity import values

    v = copy.deepcopy(values(False))
    v["phase_material"] = {"perception": {"instruction_template": LOCKED}}
    v["native_episode"]["roles"]["perception"]["template_variants"] = _block(
        candidates=candidates, twin=twin,
    )
    return v


def _program(ceiling):
    from test_native_episode_config import program

    return program(ceiling=ceiling)


def test_the_loader_parses_the_group_and_adds_two_per_non_delivering_arm_to_the_ceiling():
    # Review-off graph 1 + 1 = 2; K = 4 -> 2 + 2 (4 - 1) = 8.
    config = load_native_episode_config(_values(), _program(8))
    assert config.max_contacts == 8
    group = config.perception_branch_group
    assert group is not None and group.is_template and group.level == 2
    assert config.perception_branch_phase_id == "perception"
    assert config.role("perception").perception_branches is group
    assert config.supply_variant_group is None


def test_the_program_ceiling_must_equal_the_bounded_graph_ceiling():
    with pytest.raises(ValueError, match="program contact ceiling must equal"):
        load_native_episode_config(_values(), _program(5))


def test_a_node_without_its_locked_template_is_refused():
    v = _values()
    v["phase_material"] = {}
    with pytest.raises(ValueError, match="requires the node's own"):
        load_native_episode_config(v, _program(8))


def test_a_block_naming_another_node_than_the_one_it_sits_on_is_refused_by_the_loader():
    v = _values()
    v["native_episode"]["roles"]["perception"]["template_variants"]["node"] = "solver"
    with pytest.raises(ValueError, match="declared on exactly the node it names"):
        load_native_episode_config(v, _program(8))


def test_a_variant_on_the_reviewer_or_planner_is_still_refused():
    for role in ("reviewer", "planner"):
        v = _values()
        block = v["native_episode"]["roles"]["perception"].pop("template_variants")
        v["native_episode"]["roles"][role]["template_variants"] = block
        with pytest.raises(ValueError, match=f"roles.{role}.template_variants is refused"):
            load_native_episode_config(v, _program(2))


def test_double_declaration_is_refused():
    v = _values()
    v["native_episode"]["roles"]["perception"]["branches"] = {"branches": [], "level": 2}
    with pytest.raises(ValueError, match="cannot combine"):
        load_native_episode_config(v, _program(8))
    v = _values()
    v["phase_material"]["solver"] = {"instruction_template": "probes/slurp_native_role_solver_v2.txt"}
    v["native_episode"]["roles"]["solver"]["template_variants"] = _block(node="solver")
    with pytest.raises(ValueError, match="cannot combine"):
        load_native_episode_config(v, _program(8))


def test_a_config_without_the_key_is_unchanged():
    v = _values()
    del v["native_episode"]["roles"]["perception"]["template_variants"]
    config = load_native_episode_config(v, _program(2))
    assert config.perception_branch_group is None and config.max_contacts == 2


def test_a_v4_receipt_row_carries_only_the_template_axis():
    from speech_aware_evidence_acquisition.rails.supply_variants import perception_branch_record

    group = _group()
    kwargs = dict(
        contact_id="c", request_sha256="1" * 64, response_text_sha256="2" * 64,
        note_sha256="2" * 64, note_parse_status="malformed", candidate_intent_ids=(),
        supplied_value_ids=(),
    )
    row = perception_branch_record(
        branch=group.branch("p1"), branch_index=0, template_group=True, **kwargs,
    )
    assert row["instruction_template"] == {"relpath": "probes/nx/p1.txt", "sha256": SHA["a"]}
    assert perception_branch_record(
        branch=group.branch("lock"), branch_index=3, template_group=True, **kwargs,
    )["instruction_template"] is None
    with pytest.raises(PerceptionBranchError, match="not the template"):
        perception_branch_record(branch=group.branch("p1"), branch_index=0, **kwargs)


# ---------------------------------------------------------------------------
# 2. The production graph
# ---------------------------------------------------------------------------

pytest.importorskip("openjiuwen", reason="OpenJiuwen unavailable")

import test_native_episode_runner as harness_module  # noqa: E402
from test_llama_server_transport import _spawn_live_matching_process  # noqa: E402,F401
from test_native_episode_runner import _ActualEpisodeHarness  # noqa: E402
from test_perception_branch_live import _perception_live_config  # noqa: E402
from test_perception_branch_presentation_live import VALUE_X, VALUE_Y, _intent_snapshot  # noqa: E402
from test_rails_controllers import _phase_supply  # noqa: E402

pytestmark = pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")

ROWS = 4
TEXT = {
    "p1": "PERCEPTION-TEMPLATE-ONE: report an empty entity list when none was heard.",
    "p2": "PERCEPTION-TEMPLATE-TWO: list heard values once each.",
}
# Branch order p1, p2, aa, lock -> perception turns 1, 2, 3, 4; the same order at the Solver.
NOTE = {1: "beta-note", 2: "gamma-note", 3: "alpha-note", 4: "alpha-note"}


def _note_values(note: str) -> tuple[str, ...]:
    return (VALUE_X,) if "alpha" in note else (VALUE_Y,)


def _assert_view_binds_its_own_note(context):
    """The branch artifact the runner hands the binding must satisfy its own binding: run the
    REAL hypothesis parser over it. The fake notes are not hypothesis documents, so only the
    source-response SHA-256 refusal is a failure here (it is the first check, before content)."""

    from speech_aware_evidence_acquisition.rails.slurp_intent_hypotheses import (
        SlurpIntentHypothesisError, parse_slurp_intent_hypothesis_state,
    )

    artifact = [
        s for s in context.agent_states if s.state_kind == "phase:perception"
    ][-1]
    assert artifact.source_response_sha256 == hashlib.sha256(
        artifact.content.encode("utf-8")
    ).hexdigest()
    try:
        parse_slurp_intent_hypothesis_state(
            artifact, expected_sample_id=context.sample_id,
            legal_intent_ids={"x"}, max_candidates=1,
        )
    except SlurpIntentHypothesisError as error:
        assert "source response SHA-256" not in str(error), error



def _rebound(state, content):
    """The defect's history re-read: A's note, bound to its own bytes as A's sealed state is."""

    return replace(
        state, content=content,
        source_response_sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
    )



def _perception_note(context) -> str:
    return [
        state for state in context.agent_states if state.state_kind == "phase:perception"
    ][-1].content


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
        return f"solver-answer:{sample_id}:4"
    return f"{phase}-analysis:{sample_id}:visit:{visit}"


def _builder(harness, arm_id):
    from speech_aware_evidence_acquisition.rails.material import PhaseMaterial

    def build(phase, context, sealed):
        assert phase == "perception"
        visit = harness.material_visits[(context.sample_id, phase)]
        marker = f"native-role:{phase}:sample:{context.sample_id}:visit:{visit}"
        return PhaseMaterial(
            instruction=f"{marker}\n{TEXT[arm_id]}", response_format=None,
            contact_id=marker, purpose=phase,
        ).validate()

    return build


def _build(tmp_path, monkeypatch, *, armed=True, resolver="own-note"):
    class FourRowWorld(harness_module._World):
        SAMPLE_SPECS = (("s1", 2.0), ("s2", 3.5), ("s3", 2.5), ("s4", 3.0))

    monkeypatch.setattr(harness_module, "_World", FourRowWorld)
    group = _group() if armed else None
    contacts = 8 if armed else 2
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=ROWS, max_revisions=0, max_contacts=contacts, planner_actions=(),
    )
    harness.config = _perception_live_config(group=group, max_contacts=contacts)
    harness.program = replace(
        harness.program,
        phases=tuple(
            replace(phase, knowledge="supplied") if phase.name == "solver" else phase
            for phase in harness.program.phases
        ),
    )

    def supply(phase, context):
        if phase != "solver":
            return None
        return _phase_supply(
            context, value_ids=_note_values(_perception_note(context)),
            facet_ids=("operation:dim",),
        )

    def branch_supply(*, branch_id, phase_id, context):
        assert phase_id == "solver"
        _assert_view_binds_its_own_note(context)
        note = "alpha-note" if resolver == "a-supply" else _perception_note(context)
        return _phase_supply(
            context, value_ids=_note_values(note), facet_ids=("operation:dim",),
        )

    real_binding = harness_module.NativeEpisodeRunBinding

    def bind(**kwargs):
        extra = {"supply_for_phase": supply}
        if armed:
            extra["perception_branch_solver_supply"] = branch_supply
        return real_binding(**kwargs, **extra)

    monkeypatch.setattr(harness_module, "NativeEpisodeRunBinding", bind)
    if armed:
        harness.template_variant_materials = MappingProxyType({
            arm_id: _builder(harness, arm_id) for arm_id in TEXT
        })
    harness._output = _output if armed else _control_output
    return group, harness


def _requests_by_row(harness):
    by_row = defaultdict(list)
    for channel, _record_id, payload in harness.trace.records:
        if channel == "MODEL_REQUEST":
            request = payload["payload"]
            by_row[request["sample_id"]].append(request)
    return by_row


def _control(request):
    turn = request["history"][-1]
    assert turn["role"] == "control"
    return json.loads(turn["content"])


def _instruction(request):
    return _control(request)["messages"][1]["content"]


def _control_without_contact(request):
    control = _control(request)
    control.pop("contact_id")
    return control


def _history_text(request) -> str:
    return json.dumps(
        {
            "states": [
                {key: h[key] for key in ("state_kind", "content", "content_sha256")}
                for h in request["history"] if "state_kind" in h
            ],
            "supplied_evidence": request["supplied_evidence"],
        },
        default=str, sort_keys=True,
    )


def _run(harness):
    try:
        return harness.run(snapshot=_intent_snapshot())
    finally:
        harness.close()


def test_four_rows_walk_the_production_graph_with_each_arm_rendering_its_own_template_and_note(
    tmp_path, monkeypatch,
):
    from speech_aware_evidence_acquisition.rails import runner as runner_module

    real_view = runner_module.perception_note_view_state
    view_calls = []

    def recording_view(state, *, note_text):
        view = real_view(state, note_text=note_text)
        view_calls.append(view)
        return view

    monkeypatch.setattr(runner_module, "perception_note_view_state", recording_view)
    group, harness = _build(tmp_path / "armed", monkeypatch)
    summary = _run(harness)
    assert len(summary.results) == ROWS
    # Both runner sites (settle's supply fan-out and the Solver render view) build the branch
    # artifact through the one helper (at least two non-A, non-twin branches x two sites x ROWS rows).
    assert len(view_calls) >= 2 * 2 * ROWS
    assert all(
        v.source_response_sha256 == hashlib.sha256(v.content.encode("utf-8")).hexdigest()
        for v in view_calls
    )
    by_row = _requests_by_row(harness)
    identical = 0
    for result in summary.results:
        sid = result.sample_id
        requests = by_row[sid]
        # Perception p1, p2, aa, lock then the Solver's p1, p2, aa, lock.
        assert len(requests) == 8
        perception, solver = requests[:4], requests[4:]
        # Perception: p1 and p2 render their own template; aa and lock the locked one.
        assert TEXT["p1"] in _instruction(perception[0]) and TEXT["p2"] not in _instruction(perception[0])
        assert TEXT["p2"] in _instruction(perception[1]) and TEXT["p1"] not in _instruction(perception[1])
        assert not any(t in _instruction(perception[2]) for t in TEXT.values())
        assert not any(t in _instruction(perception[3]) for t in TEXT.values())
        assert _instruction(perception[2]) == _instruction(perception[3])
        # Solver: every arm sees ITS OWN note; aa repeats lock.
        assert f"beta-note:{sid}" in _history_text(solver[0])
        assert f"alpha-note:{sid}" not in _history_text(solver[0])
        assert f"gamma-note:{sid}" in _history_text(solver[1])
        assert f"alpha-note:{sid}" not in _history_text(solver[1])
        assert f"alpha-note:{sid}" in _history_text(solver[3])
        assert f"beta-note:{sid}" not in _history_text(solver[3])
        assert _history_text(solver[2]) == _history_text(solver[3])
        ids = [[i["evidence_id"] for i in r["supplied_evidence"]] for r in solver]
        assert ids == [[VALUE_Y], [VALUE_Y], [VALUE_X], [VALUE_X]]
        # The Solver instruction is the node's locked one in every arm.
        assert len({_control_without_contact(r)["messages"][1]["content"].split("Native")[0]
                    for r in solver}) == 1
        assert not any(t in _instruction(r) for r in solver for t in TEXT.values())
        # Custody is lock's: the sealed Perception state and final supply.
        perception_states = [s for s in result.agent_states if s.state_kind == "phase:perception"]
        assert [s.content for s in perception_states] == [f"alpha-note:{sid}"]
        assert tuple(result.final_query_state.retrieved_value_ids) == (VALUE_X,)
        receipt = result.native_episode_receipt["perception_branches"]
        assert receipt["schema"] == PERCEPTION_BRANCH_RECEIPT_SCHEMA_V4
        assert receipt["level"] == 2 and receipt["delivered_branch_id"] == "lock"
        rows = {row["branch_id"]: row for row in receipt["branches"]}
        assert list(rows) == list(group.branch_ids)
        assert rows["p1"]["instruction_template"] == {"relpath": "probes/nx/p1.txt", "sha256": SHA["a"]}
        assert rows["p2"]["instruction_template"]["sha256"] == SHA["b"]
        assert rows["aa"]["instruction_template"] is None and rows["lock"]["instruction_template"] is None
        assert rows["aa"]["replicate_of"] == "lock"
        assert rows["p1"]["candidate_supply_value_ids"] == [VALUE_Y]
        assert rows["lock"]["candidate_supply_value_ids"] == [VALUE_X]
        validate_perception_branch_receipt(
            receipt, branch_ids=list(group.branch_ids), delivered_branch_id="lock",
            twin_branch_id="aa", phase_id="perception", level=2,
        )
        assert len({row["contact_id"] for row in receipt["branches"]}) == 4
        assert len({row["solver_contact_id"] for row in receipt["branches"]}) == 4
        identical += 1
    assert identical == ROWS

    # The byte statement: lock's Perception and Solver requests are the UNARMED plan's, per row.
    monkeypatch.undo()
    _none, control = _build(tmp_path / "control", monkeypatch, armed=False)
    _run(control)
    control_rows = _requests_by_row(control)
    matched = 0
    for result in summary.results:
        armed_requests, plan_requests = by_row[result.sample_id], control_rows[result.sample_id]
        assert len(plan_requests) == 2
        for armed_request, plan_request, label in (
            (armed_requests[3], plan_requests[0], "perception"),
            (armed_requests[7], plan_requests[1], "solver"),
        ):
            for field in (
                "decoding_params", "tool_schemas", "speech_feature_parts", "query_source",
                "supplied_evidence", "sample_id", "task_instruction",
            ):
                assert armed_request[field] == plan_request[field], (label, field)
            assert _history_text(armed_request) == _history_text(plan_request), label
            assert _instruction(armed_request).split("Native")[0] == _instruction(plan_request).split("Native")[0]
        matched += 1
    print("NX-PERCEPTION-REHEARSAL-SUMMARY " + json.dumps({
        "rows": ROWS, "arms_per_row": list(group.branch_ids),
        "requests_per_row": 8, "receipt_schema": PERCEPTION_BRANCH_RECEIPT_SCHEMA_V4,
        "delivering_requests_identical_to_unarmed_plan": f"{matched}/{ROWS} rows",
    }, sort_keys=True))


def test_template_branches_seal_through_the_bundle_verifier_and_the_runtime(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core.bundle.outputs import _verify_outputs_trace_binding
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime

    group, harness = _build(tmp_path, monkeypatch)
    summary = harness.run(snapshot=_intent_snapshot())
    try:
        raw_native = {
            "finite_completion_policy": harness.config.finite_completion_policy,
            "exhaustion_policy": "raise", "max_revisions": 0,
            "actions": dict(zip(("accept", "revise", "acquire"), harness.config.actions)),
            "roles": {
                "perception": {"phase_id": "perception", "template_variants": _block()},
                "solver": {"phase_id": "solver"},
            },
        }
        runtime = object.__new__(FlightRuntime)
        runtime._composed = SimpleNamespace(values={"native_episode": raw_native})
        runtime._plan = harness.plan
        runtime._phase_summaries = [summary]
        runtime._output_rows = [
            {"sample_id": row.sample_id, "final_response_text": row.final_response_text,
             "native_episode_receipt": row.native_episode_receipt}
            for row in summary.results
        ]
        runtime._result_kind = lambda: "answer"
        runtime._arm = lambda: harness.client.arm
        outputs = runtime._canonical_output_rows(harness.client)
        assert [row["sample_id"] for row in outputs] == ["s1", "s2", "s3", "s4"]
        for row in outputs:
            block = row["native_episode_receipt"]["perception_branches"]
            assert block["schema"] == PERCEPTION_BRANCH_RECEIPT_SCHEMA_V4
        records = {rid: payload for _, rid, payload in harness.trace.records}
        _verify_outputs_trace_binding(tuple(outputs), records)
    finally:
        harness.close()


def test_a_template_branch_that_replicates_a_is_refused_at_seal_by_name(tmp_path, monkeypatch):
    """The 2026-10-09 recurrence guard, for a template branch: p1's note differs from lock's, so a
    Solver column that rendered lock's request is the defect and the seal refuses it by name."""

    from speech_aware_evidence_acquisition.rails import native_episode_config as config_module

    real_select = config_module.select_native_role_history

    def defective_select(*, role, solver_phase_id, states, local_tool_result_ids):
        states = tuple(
            _rebound(state, state.content.replace("beta-note", "alpha-note").replace(
                "gamma-note", "alpha-note"))
            if state.state_kind == "phase:perception" else state
            for state in states
        )
        return real_select(
            role=role, solver_phase_id=solver_phase_id, states=states,
            local_tool_result_ids=local_tool_result_ids,
        )

    monkeypatch.setattr(config_module, "select_native_role_history", defective_select)
    _group_, harness = _build(tmp_path, monkeypatch, resolver="a-supply")
    try:
        with pytest.raises(Exception, match="replicated branch A's rendered request"):
            harness.run(snapshot=_intent_snapshot())
    finally:
        harness.close()


def test_builders_must_match_the_declared_template_branches(tmp_path, monkeypatch):
    _group_, harness = _build(tmp_path, monkeypatch)
    harness.template_variant_materials = None
    try:
        with pytest.raises(Exception, match="template_variant_materials"):
            harness.run(snapshot=_intent_snapshot())
    finally:
        harness.close()
    monkeypatch.undo()
    _group_, harness = _build(tmp_path / "two", monkeypatch)
    harness.template_variant_materials = MappingProxyType({
        **harness.template_variant_materials, "p9": _builder(harness, "p1"),
    })
    try:
        with pytest.raises(Exception, match="template_variant_materials"):
            harness.run(snapshot=_intent_snapshot())
    finally:
        harness.close()


# ---------------------------------------------------------------------------
# 4. The dry-run walk and the review-off rehearsal profile
# ---------------------------------------------------------------------------


def test_the_dry_run_walks_every_perception_template_arm_model_free(tmp_path):
    import hashlib

    from speech_aware_evidence_acquisition.analysis.native_episode_dry_run import (
        dry_run_native_episode,
    )
    from speech_aware_evidence_acquisition.rails.controllers import PhaseProgram, PhaseSpec
    from speech_aware_evidence_acquisition.rails.material import PhaseMaterial

    from test_rails_frozen_core_client import _World, _plan
    from test_rails_runner import _FakeAdapter, _knowledge_snapshot

    group = _group()
    world = _World(tmp_path)
    world.samples = world.samples[:1]
    sample = world.samples[0]
    program = PhaseProgram(
        program_id="dry-run-perception-template-proof-v1",
        phases=tuple(
            PhaseSpec(
                name=phase, purpose="answer" if phase == "solver" else phase,
                knowledge="supplied", response_format_id=None, barrier=False,
            )
            for phase in harness_module.PHASES
        ),
        max_contacts=8, stop_rule="native-role-episode",
    ).validate()
    episode = _perception_live_config(group=group, max_contacts=8)

    def material_for_phase(phase, context, prior):
        return PhaseMaterial(
            instruction=f"dry-run instruction for {phase}", response_format=None,
            contact_id=f"dry-run:{phase}", purpose="answer" if phase == "solver" else phase,
        ).validate()

    def arm_builder(arm_id):
        def build(phase, context, prior):
            return PhaseMaterial(
                instruction=f"dry-run instruction for {phase}\n{TEXT[arm_id]}",
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
                branch.branch_id: arm_builder(branch.branch_id)
                for branch in group.branches if branch.instruction_template is not None
            },
        },
    )
    document = dry_run_native_episode(
        runtime, answers={"perception": "perception draft", "solver": "solver draft"},
        node_order=("perception", "solver"),
    ).as_json()
    perception = next(n for n in document["nodes"] if n["phase"] == "perception")
    arms = {a["arm_id"]: a for a in perception["supply_variant_arms"]}
    assert list(arms) == ["p1", "p2", "aa", "lock"]
    locked = hashlib.sha256(b"dry-run instruction for perception").hexdigest()
    assert arms["lock"]["instruction_sha256"] == arms["aa"]["instruction_sha256"] == locked
    assert arms["p1"]["instruction_template"]["sha256"] == SHA["a"]
    assert len({a["instruction_sha256"] for a in arms.values()}) == 3
    solver = next(n for n in document["nodes"] if n["phase"] == "solver")
    assert solver["supply_variant_arms"] == []


def test_the_review_off_rehearsal_profile_admits_a_perception_template_group():
    from speech_aware_evidence_acquisition.analysis import native_graph_rehearsal as graph

    v = _values()
    v["policy"] = "phase-native-module-v1-c8"
    v["native_graph_capacity_profile"] = "review-off-v1"
    parsed = graph.rehearsal_profile(v, "review-off-v1")
    assert parsed.max_contacts == 8 and parsed.perception_branch_group.is_template


def test_a_v4_block_replays_as_v4_for_seal_only_resume():
    import hashlib

    from speech_aware_evidence_acquisition.rails.supply_variants import (
        PerceptionBranchReplayContact,
        perception_branch_receipt,
        perception_branch_record,
        replay_perception_branch_block,
    )

    group = _group()
    records, contacts = [], {}
    for index, branch in enumerate(group.branches):
        text = f"note-{branch.branch_id}" if index < 2 else "note-lock"
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        request = f"{index + 1:x}" * 64
        solver_request = f"{index + 5:x}" * 64
        contacts[f"c{index}"] = PerceptionBranchReplayContact(
            request_sha256=request, response_text_sha256=digest, text=text,
        )
        contacts[f"s{index}"] = PerceptionBranchReplayContact(
            request_sha256=solver_request, response_text_sha256=digest, text="answer",
        )
        records.append(perception_branch_record(
            branch=branch, branch_index=index, contact_id=f"c{index}",
            request_sha256=request, response_text_sha256=digest, note_sha256=digest,
            note_parse_status="malformed", candidate_intent_ids=(), supplied_value_ids=(),
            solver_contact_id=f"s{index}", solver_request_sha256=solver_request,
            solver_response_text_sha256=digest, candidate_supply_value_ids=(),
            template_group=True,
        ))
    block = perception_branch_receipt(group=group, phase_id="perception", records=records)
    assert block["schema"] == PERCEPTION_BRANCH_RECEIPT_SCHEMA_V4
    replayed = replay_perception_branch_block(block, contacts=contacts)
    assert replayed["schema"] == PERCEPTION_BRANCH_RECEIPT_SCHEMA_V4
    assert [r["instruction_template"] for r in replayed["branches"]] == [
        {"relpath": "probes/nx/p1.txt", "sha256": SHA["a"]},
        {"relpath": "probes/nx/p2.txt", "sha256": SHA["b"]}, None, None,
    ]
