"""Loop engineering item E-S1: the consumption module's ``supply`` column kind.

A ``columns`` entry of kind ``supply`` is one non-delivering arm of the Solver's
``supply_variants`` block (the E42 mechanism). Under the review-off profile the
compiler builds the whole block (one arm per column in column order, the twin,
the delivering arm LAST with no override and no release swap), parses it with
the rails' own ``parse_supply_variants`` before writing, adds K - 1 to the
ceiling, writes the frame's declared ``alternates`` to
``knowledge_stores.<store>.alternates`` and picks the program-family id. The
config loader's ``verify_declared_module`` then holds a declared config to
exactly that block. Model-free throughout.
"""

from __future__ import annotations

import copy
import dataclasses

import pytest

from test_consumption_module_review_off import review_off_block

from speech_aware_evidence_acquisition.rails import consumption_module as cm
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import (
    carrier_module_hooks,
)
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    load_native_episode_config,
)

FIT = {
    "slot_tokens": 24576, "completion_ceiling": 640,
    "base_prompt_tokens": 9600, "tokens_per_supplied_item": 120,
}
EX_K = "knowledge_stores.train-exemplars.phase_supply.solver.k"
EX_C = "knowledge_stores.train-exemplars.phase_supply.solver.fuse_coverage.c"
ALT_RELEASE = "knowledge/slurp/alt/release.json"
ALT = {
    "train-exemplars": [{
        "release": {"relpath": ALT_RELEASE, "sha256": "a" * 64},
        "snapshot": {"relpath": "knowledge/slurp/alt/snapshot.json", "sha256": "b" * 64},
    }],
}


def _supply_block(*, twin=True, alternates=True, columns=None):
    block = review_off_block()
    block["columns"] = columns if columns is not None else [
        {"column_id": "typ", "kind": "supply", "node": "solver", "max_supplied_items": 40,
         "overrides": {EX_K: 10}},
        {"column_id": "ace", "kind": "supply", "node": "solver", "max_supplied_items": 55,
         "release_swap": {"store_id": "train-exemplars", "release": ALT_RELEASE}},
    ]
    frame = {"twin": twin, "fit_estimate": dict(FIT), "delivering_max_supplied_items": 55}
    if alternates:
        frame["alternates"] = copy.deepcopy(ALT)
    block["supply_frame"] = frame
    return block


def _compose(block):
    composed = cm.compile_module(block, carrier_module_hooks())
    values = composed.values()
    values["carrier_lock_key"] = "slurp"
    values["native_episode"]["consumption_module"] = block
    return composed, values


def test_supply_columns_compile_to_one_block_with_the_twin_and_the_lock_last():
    composed = cm.compile_module(_supply_block(), carrier_module_hooks())
    values = composed.values()
    block = values["native_episode"]["roles"]["solver"]["supply_variants"]
    assert block["arm_visits"] == "first" and block["fit_estimate"] == FIT
    assert [(a["arm_id"], a.get("deliver"), a.get("replicate_of")) for a in block["arms"]] == [
        ("typ", None, None), ("ace", None, None), ("aa", None, "lock"), ("lock", True, None),
    ]
    typ, ace, aa, lock = block["arms"]
    assert typ == {"arm_id": "typ", "max_supplied_items": 40, "overrides": {EX_K: 10}}
    assert ace["release_swap"] == {"store_id": "train-exemplars", "release": ALT_RELEASE}
    # the twin and the delivering arm carry no override and no release swap
    for arm in (aa, lock):
        assert "overrides" not in arm and "release_swap" not in arm
        assert arm["max_supplied_items"] == 55
    # review-off graph (perception 1 + solver 1) + (K - 1): K = 4 -> 5.
    assert (composed.program_id, composed.program_ceiling) == ("phase-native-module-v1-c5", 5)
    assert values["policy"] == "phase-native-module-v1-c5"
    assert "template_variants" not in values["native_episode"]["roles"]["solver"]
    # the frame's alternates reach the store entry; no other store is touched
    stores = values["knowledge_stores"]
    assert stores["train-exemplars"]["alternates"] == ALT["train-exemplars"]
    assert all("alternates" not in v for k, v in stores.items() if k != "train-exemplars")


def test_without_a_twin_the_ceiling_follows_the_arm_count():
    columns = [{"column_id": "typ", "kind": "supply", "node": "solver", "max_supplied_items": 40,
                "overrides": {EX_K: 10}}]
    composed = cm.compile_module(
        _supply_block(twin=False, alternates=False, columns=columns), carrier_module_hooks())
    assert (composed.program_id, composed.program_ceiling) == ("phase-native-module-v1-c3", 3)
    arms = composed.values()["native_episode"]["roles"]["solver"]["supply_variants"]["arms"]
    assert [a["arm_id"] for a in arms] == ["typ", "lock"]


def test_the_compile_changes_only_the_supply_block_the_alternates_and_the_program():
    """Byte-identity of everything a request is composed from: the module graph with
    and without the column differs ONLY in the program id, the Solver's
    ``supply_variants`` block and the declared alternates."""

    plain = cm.compile_module(review_off_block(), carrier_module_hooks()).values()
    armed = cm.compile_module(_supply_block(), carrier_module_hooks()).values()
    diff = cm.differing_paths(plain, armed)
    assert diff, "the column must change something"
    allowed = (
        "policy",
        "native_episode.roles.solver.supply_variants",
        "knowledge_stores.train-exemplars.alternates",
    )
    assert all(path == allowed[0] or path.startswith(allowed[1]) or path.startswith(allowed[2])
               for path in diff), diff
    # every request-bearing block is equal as a whole: templates, role graph minus
    # the supply block, knobs, tools, deliver normaliser
    for key in ("phase_material", "phase_tools"):
        assert plain.get(key) == armed.get(key), key
    for role in ("perception", "solver", "reviewer", "planner"):
        left = copy.deepcopy(plain["native_episode"]["roles"][role])
        right = copy.deepcopy(armed["native_episode"]["roles"][role])
        right.pop("supply_variants", None)
        assert left == right, role
    assert plain["native_episode"]["deliver_normaliser"] == armed["native_episode"]["deliver_normaliser"]
    for sid, spec in plain["knowledge_stores"].items():
        rest = {k: v for k, v in armed["knowledge_stores"][sid].items() if k != "alternates"}
        assert spec == rest, sid


def test_the_compiled_block_loads_through_the_runtime_loader_and_verifies():
    block = _supply_block()
    composed, values = _compose(block)
    program = default_phase_program(values["policy"])
    parsed = load_native_episode_config(values, program)
    # the contact ceiling is the module's own K - 1 term; the FIT cap (rows x
    # max_contacts x 4) reads this one number
    assert parsed.max_contacts == composed.program_ceiling == 5
    group = parsed.supply_variant_group
    assert not group.is_template and group.arm_ids == ("typ", "ace", "aa", "lock")
    assert group.delivered_arm.arm_id == "lock" and group.arm_visits == "first"
    assert not parsed.review_loop_enabled
    cm.verify_declared_module(block, values)
    edited = copy.deepcopy(values)
    edited["native_episode"]["roles"]["solver"]["supply_variants"]["arms"][0]["overrides"][EX_K] = 9
    with pytest.raises(cm.ConsumptionModuleConfigError, match="differ"):
        cm.verify_declared_module(block, edited)
    # an alternate dropped from the store entry is a drift as well
    dropped = copy.deepcopy(values)
    dropped["knowledge_stores"]["train-exemplars"].pop("alternates")
    with pytest.raises(cm.ConsumptionModuleConfigError, match="differ"):
        cm.verify_declared_module(block, dropped)


def test_the_block_identity_binds_the_arms_and_the_frame():
    a = cm.parse_consumption_module_block(_supply_block())
    other = _supply_block()
    other["columns"][0]["overrides"][EX_K] = 11
    assert a.block_sha256 != cm.parse_consumption_module_block(other).block_sha256
    other = _supply_block()
    other["supply_frame"]["delivering_max_supplied_items"] = 54
    assert a.block_sha256 != cm.parse_consumption_module_block(other).block_sha256
    assert [c.kind for c in a.columns] == ["supply", "supply"]
    assert a.supply_columns == a.columns and a.branch_columns == () and a.template_columns == ()
    assert a.supply_frame["twin"] is True


def test_a_supply_block_is_not_the_module_off_arm():
    assert not cm.is_module_off_block(_supply_block())


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda b: b["columns"][0].update(template={"relpath": "x", "sha256": "0" * 64}), "keys must be"),
        (lambda b: b["columns"][0].pop("max_supplied_items"), "keys must be"),
        (lambda b: b["columns"][0].update(toggle="top2-contrast"), "keys must be"),
        (lambda b: b["columns"][0].update(max_supplied_items=0), "positive integer"),
        (lambda b: b["columns"][0].update(overrides={EX_K: "ten"}), "knob path -> integer"),
        (lambda b: b["columns"][0].update(overrides={}), "neither overrides nor a release_swap"),
        (lambda b: b["columns"][1].update(release_swap={"store_id": "x"}), "exactly {store_id, release}"),
        (lambda b: b["columns"][1].update(column_id="typ"), "ids must be distinct"),
        (lambda b: b["columns"][1].update(node="reviewer"), "one node"),
        (lambda b: b.pop("supply_frame"), "supply_frame is required"),
        (lambda b: b["supply_frame"].update(extra=1), "keys must be"),
        (lambda b: b["supply_frame"].update(twin="yes"), "must be a bool"),
        (lambda b: b["supply_frame"].update(delivering_max_supplied_items=0), "positive integer"),
        (lambda b: b["supply_frame"].update(alternates={}), "non-empty object"),
        (lambda b: b["supply_frame"]["alternates"]["train-exemplars"][0].pop("snapshot"),
         "exactly {release, snapshot}"),
        (lambda b: b["supply_frame"]["alternates"]["train-exemplars"][0]["release"].update(sha256="XYZ"),
         "64-hex"),
        (lambda b: b.update(columns=[]), "no supply column is"),
        (lambda b: b.pop("review_loop"), "only under the explicit review-off profile"),
        (lambda b: b.update(template_frame={"max_supplied_items": 4, "delivering_template_tokens": 4,
                                            "twin": True, "fit_estimate": dict(FIT)}),
         "no template column is"),
        (lambda b: b["columns"].append(
            {"column_id": "t1", "kind": "template", "node": "solver",
             "template": {"relpath": "configs/probes/nx/t1.txt", "sha256": "c" * 64},
             "template_tokens": 400}),
         "beside template or Perception-branch columns"),
        (lambda b: b["columns"].append(
            {"column_id": "p1", "toggle": "top2-contrast", "to": "on", "level": 2}),
         "does not support branch columns"),
    ],
)
def test_the_parse_refuses_a_malformed_supply_column_or_frame(mutate, message):
    block = _supply_block()
    mutate(block)
    with pytest.raises(cm.ConsumptionModuleConfigError, match=message):
        cm.parse_consumption_module_block(block)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        # the rails' own refusals, applied at compile time and named
        (lambda b: b["columns"][0].update(overrides={"knowledge_stores.train-exemplars.phase_supply.solver.tau": 3}),
         "does not admit"),
        (lambda b: b["columns"][0].update(overrides={
            "knowledge_stores.train-exemplars.phase_supply.perception.k": 3}),
         "FIRST phase"),
        (lambda b: b["columns"][0].update(overrides={
            "knowledge_stores.no-such-store.phase_supply.solver.k": 3}),
         "does not declare"),
        (lambda b: b["columns"][0].update(overrides={EX_K: 10, EX_C: 4}) or b["columns"][1].update(
            release_swap=None, overrides={EX_K: 10, EX_C: 4}), "same overrides"),
        (lambda b: b["columns"][1]["release_swap"].update(release="knowledge/slurp/alt/other.json"),
         "absent from its declared alternates"),
        (lambda b: b["columns"][1]["release_swap"].update(store_id="slot-contracts"),
         "absent from its declared alternates"),
        (lambda b: b["supply_frame"].update(fit_estimate=dict(FIT, base_prompt_tokens=30000)), "exceeds"),
        (lambda b: b["supply_frame"]["alternates"].update(nope=ALT["train-exemplars"]),
         "lock layer does not declare"),
        (lambda b: b["columns"].extend(
            {"column_id": f"x{i}", "kind": "supply", "node": "solver", "max_supplied_items": 40,
             "overrides": {EX_K: 20 + i}} for i in range(6)),
         "between 2 and 8"),
    ],
)
def test_the_compiler_applies_the_rails_own_refusals_before_writing(mutate, message):
    block = _supply_block()
    mutate(block)
    with pytest.raises(cm.ConsumptionModuleConfigError, match=message):
        cm.compile_module(block, carrier_module_hooks())


def test_a_carrier_without_the_hook_refuses_a_supply_column():
    hooks = dataclasses.replace(carrier_module_hooks(), supply_variant_frame=None)
    with pytest.raises(cm.ConsumptionModuleConfigError, match="supply_variant_frame"):
        cm.compile_module(_supply_block(), hooks)


def test_a_carrier_that_admits_another_node_refuses():
    frame = dict(carrier_module_hooks().supply_variant_frame, node="perception")
    hooks = dataclasses.replace(carrier_module_hooks(), supply_variant_frame=frame)
    with pytest.raises(cm.ConsumptionModuleConfigError, match="admits supply variants only at"):
        cm.compile_module(_supply_block(), hooks)


def test_a_twin_needs_the_carriers_twin_arm_id():
    frame = dict(carrier_module_hooks().supply_variant_frame, twin_arm_id=None)
    hooks = dataclasses.replace(carrier_module_hooks(), supply_variant_frame=frame)
    with pytest.raises(cm.ConsumptionModuleConfigError, match="no twin arm id"):
        cm.compile_module(_supply_block(twin=True), hooks)
    cm.compile_module(_supply_block(twin=False), hooks)


def test_the_supply_node_receipt_schema_is_a_registered_node_receipt():
    receipt = cm.module_header_receipt(
        cm.compile_module(_supply_block(), carrier_module_hooks()),
        node_receipts=[{"schema": "saea-supply-variant-arms-v3", "pointer": "supply_variants"}],
    )
    cm.validate_module_header_receipt(receipt)
    assert receipt["program_ceiling"] == 5


def test_a_supply_column_does_not_disturb_a_template_block_or_the_plain_review_off_block():
    plain = cm.compile_module(review_off_block(), carrier_module_hooks())
    assert plain.program_ceiling == 2
    assert "supply_variants" not in plain.values()["native_episode"]["roles"]["solver"]


# ---------------------------------------------------------------------------
# The delivering arm's realised request, with and without the column
# ---------------------------------------------------------------------------

pytest.importorskip("openjiuwen", reason="OpenJiuwen unavailable")

from test_llama_server_transport import _spawn_live_matching_process  # noqa: E402,F401
from test_native_episode_runner import _ActualEpisodeHarness  # noqa: E402
from test_stage3_supply_variant_interleaving import (  # noqa: E402
    ARM_VALUE,
    _arm_output,
    _arm_resolver,
    _live_config,
)

_REQUEST_FIELDS = (
    "decoding_params", "task_instruction", "tool_schemas", "speech_feature_parts",
    "speech_packet_sha256", "query_source", "key_representation_id", "matcher_policy_id",
    "carrier_lock_key", "media_relpath", "audio_seconds", "sample_rate_hz", "sample_id",
    "supplied_evidence", "evidence_provenance",
)


def _requests(tmp_path, *, group, max_contacts, selections):
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0, max_contacts=max_contacts, planner_actions=(),
    )
    harness.config = _live_config(group=group, max_contacts=max_contacts)
    if group is not None:
        harness.supply_variant_for_phase = _arm_resolver(selections)
    harness._output = _arm_output
    try:
        summary = harness.run()
    finally:
        harness.close()
    requests = [
        payload["payload"] for channel, _rid, payload in harness.trace.records
        if channel == "MODEL_REQUEST"
    ]
    return summary.results[0], requests


def test_the_delivering_arms_realised_request_equals_the_plain_modules_request(tmp_path):
    """I7 / I7v unchanged: the module graph composed with the supply column delivers a
    Solver request whose every field equals the plain module's (no column), and the
    delivered text is the last contact's own response. Driven through the production
    walk (graph, request renderer, state sealer, trace sink), the group parsed by the
    LOADER from the module's compiled block."""

    # two knob arms: a release-swap arm needs the flight-owned alternate snapshot
    # resolver, which this walk does not bind (the E42 release-swap rendering is
    # proven by test_stage3_supply_variant_interleaving)
    knob_block = _supply_block(alternates=False, columns=[
        {"column_id": "typ", "kind": "supply", "node": "solver", "max_supplied_items": 40,
         "overrides": {EX_K: 10}},
        {"column_id": "ace", "kind": "supply", "node": "solver", "max_supplied_items": 40,
         "overrides": {EX_K: 5}},
    ])
    composed, values = _compose(knob_block)
    group = load_native_episode_config(
        values, default_phase_program(values["policy"])).supply_variant_group
    armed_result, armed = _requests(
        tmp_path / "armed", group=group, max_contacts=composed.program_ceiling,
        selections={"typ": (ARM_VALUE,), "ace": (ARM_VALUE,), "aa": (), "lock": ()},
    )
    plain_result, plain = _requests(
        tmp_path / "plain", group=None, max_contacts=2, selections=None)
    # perception + K = 4 solver arms; the plain run has perception + one solver contact
    assert len(armed) == 5 and len(plain) == 2
    delivering, plain_solver = armed[-1], plain[-1]
    for field in _REQUEST_FIELDS:
        assert delivering[field] == plain_solver[field], field
    assert len(delivering["history"]) == len(plain_solver["history"])
    assert delivering["history"][0] == plain_solver["history"][0]
    # the perception contact is untouched by the column
    for field in _REQUEST_FIELDS:
        assert armed[0][field] == plain[0][field], field
    # a non-delivering arm differs in its supplied evidence only
    assert [b["evidence_id"] for b in armed[1]["supplied_evidence"]] == [ARM_VALUE]
    for field in _REQUEST_FIELDS:
        if field not in ("supplied_evidence", "evidence_provenance"):
            assert armed[1][field] == delivering[field], field
    # the twin is byte-equal to the delivering arm
    for field in _REQUEST_FIELDS:
        assert armed[3][field] == delivering[field], field
    # I7: the delivered text is the last arm's own completion
    assert armed_result.final_response_text == _arm_output((armed_result.sample_id, "solver", 1, 4))
    # every arm is sealed under its own id, in declared order
    receipt = armed_result.supply_variants
    assert [row["arm_id"] for row in receipt["arms"]] == ["typ", "ace", "aa", "lock"]
    assert [row["deliver"] for row in receipt["arms"]] == [False, False, False, True]
