"""Lock v2.3 declares the ``ace-playbook`` store at the empty release i0 (decisions 263 A / 266-A).

Proof P-ACE-0 (design 2026-10-11 section 6): the lock with ``ace-playbook@i0`` declared renders every request byte-identical to
lock v2.2's, because the i0 release is one inert anchor row addressed to the ``planner`` node and the Solver route therefore
declines every phase. The ACE supply column (``release_swap`` to ``ace-playbook@i<t>``) verifies under the REAL hooks, and a swap to
a release the frame does not declare is refused. Model-free throughout.
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path

import pytest

from test_consumption_module_review_off import review_off_block
from test_tfrl_ace_material import LEGAL, _roster, _write_pin

from speech_aware_evidence_acquisition.core.semantic_knowledge_preparation import prepare_semantic_knowledge_store
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash
from speech_aware_evidence_acquisition.rails import consumption_module as cm
from speech_aware_evidence_acquisition.rails import tfrl_ace_material as ace
from speech_aware_evidence_acquisition.rails.adapters import slurp_module_hooks as smh
from speech_aware_evidence_acquisition.rails.adapters import slurp_module_lock_v2_3 as lock_v2_3
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import carrier_module_hooks
from speech_aware_evidence_acquisition.rails.controllers import (
    PhaseProgram,
    PhaseSpec,
    default_phase_program,
)
from speech_aware_evidence_acquisition.rails.knowledge_stores import (
    build_knowledge_store_supply,
    load_knowledge_store_binding,
)
from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config

try:  # the production walk needs OpenJiuwen and the module-scoped local listener fixture the other walk tests use
    import openjiuwen  # noqa: F401
    from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
    WALK_AVAILABLE = True
except ImportError:  # pragma: no cover
    WALK_AVAILABLE = False

REPO_ROOT = Path(__file__).resolve().parents[2]
ACE_ALT = {
    "ace-playbook": [{
        "release": {"relpath": "knowledge/slurp/semantic/ace-playbook-i1/release.json", "sha256": "a" * 64},
        "snapshot": {"relpath": "knowledge/slurp/semantic/ace-playbook-i1/snapshot.json", "sha256": "b" * 64},
    }],
}
FIT = {"slot_tokens": 24576, "completion_ceiling": 640, "base_prompt_tokens": 9600, "tokens_per_supplied_item": 120}
EX_K = "knowledge_stores.train-exemplars.phase_supply.solver.k"


def _block(lock, *, ace_column=False, swap_release=None):
    block = review_off_block()
    block["lock"] = lock
    if ace_column:
        release = swap_release or ACE_ALT["ace-playbook"][0]["release"]["relpath"]
        block["columns"] = [
            {"column_id": "typ", "kind": "supply", "node": "solver", "max_supplied_items": 63, "overrides": {EX_K: 10}},
            {"column_id": "ace", "kind": "supply", "node": "solver", "max_supplied_items": 63,
             "release_swap": {"store_id": "ace-playbook", "release": release}},
        ]
        block["supply_frame"] = {"twin": True, "fit_estimate": dict(FIT), "delivering_max_supplied_items": 55,
                                 "alternates": copy.deepcopy(ACE_ALT)}
    return block


def _compose(block):
    composed = cm.compile_module(block, carrier_module_hooks())
    values = composed.values()
    values["carrier_lock_key"] = "slurp"
    values["native_episode"]["consumption_module"] = block
    return composed, values


# ---------------------------------------------------------------------------
# the declaration is the whole difference
# ---------------------------------------------------------------------------


def test_the_v2_3_layer_is_the_v2_2_layer_plus_exactly_the_ace_playbook_store():
    versions = carrier_module_hooks().lock_versions
    v22, v23 = json.loads(json.dumps(dict(versions["v2.2"]()))), json.loads(json.dumps(dict(versions["v2.3"]())))
    diff = cm.differing_paths(v22, v23)
    assert diff and all(path.startswith("knowledge_stores.ace-playbook") for path in diff), diff
    declared = v23["knowledge_stores"].pop("ace-playbook")
    assert v22 == v23
    assert declared == lock_v2_3.ace_store_i0()
    assert declared["store_role"] == "stage3-deltas" and set(declared["context_supply"]) == {"solver"}
    assert declared["context_supply"]["solver"]["node_target"] == "solver"
    assert "alternates" not in declared
    # v2.3 keeps v2.2's delivery normaliser; no other lock moves
    names = {lock: factory() for lock, factory in carrier_module_hooks().lock_deliver_normalisers.items()}
    assert names["v2.3"] == names["v2.2"] == "saea-deliver-normalise-v4g"
    assert names["v2.0"] == names["v2.1"] == "saea-deliver-normalise-v3"


def test_the_v2_3_layer_refuses_a_second_declaration_of_the_store():
    layer = dict(carrier_module_hooks().lock_versions["v2.3"]())
    with pytest.raises(cm.ConsumptionModuleConfigError, match="without a 'ace-playbook' entry"):
        lock_v2_3.layer_from_v2_2(layer)


def test_the_committed_i0_receipt_pins_what_the_lock_declares():
    receipt = json.loads(
        (REPO_ROOT / "docs/readiness/2026-10-11-slurp-tfrl-loop-v1/ace-playbook-i0-release-receipt-v1.json").read_text("utf-8")
    )
    assert receipt["empty"] is True and receipt["iteration"] == 0 and receipt["contacts"] == {"model": 0, "tool": 0, "scorer": 0}
    assert receipt["release"] == lock_v2_3.ACE_I0_RELEASE and receipt["snapshot"] == lock_v2_3.ACE_I0_SNAPSHOT
    assert receipt["playbook_content_hash"] == ace.empty_playbook()["content_hash"]
    registration = json.loads((REPO_ROOT / receipt["registration"]["relpath"]).read_text("utf-8"))
    assert registration["store_id"] == "ace-playbook" and registration["output_namespace"].endswith("ace-playbook-i0")


def test_the_module_baseline_composes_identically_under_v2_2_and_v2_3_apart_from_the_declaration():
    plain22, plain23 = _compose(_block("v2.2")), _compose(_block("v2.3"))
    left, right = plain22[1], plain23[1]
    assert (plain22[0].program_id, plain22[0].program_ceiling) == (plain23[0].program_id, plain23[0].program_ceiling)
    diff = cm.differing_paths(left, right)
    assert diff and all(p.startswith("knowledge_stores.ace-playbook") or p == "native_episode.consumption_module.lock"
                        for p in diff), diff
    for key in ("phase_material", "phase_tools", "policy"):
        assert left.get(key) == right.get(key), key
    for role in ("perception", "solver", "reviewer", "planner"):
        assert left["native_episode"]["roles"][role] == right["native_episode"]["roles"][role], role
    assert left["native_episode"]["deliver_normaliser"] == right["native_episode"]["deliver_normaliser"]
    for sid, spec in left["knowledge_stores"].items():
        assert spec == right["knowledge_stores"][sid], sid


# ---------------------------------------------------------------------------
# the Solver route over the i0 release: hermetic build, then the real one
# ---------------------------------------------------------------------------


def _program():
    return PhaseProgram(
        program_id="synthetic-perception-then-solver-v1",
        phases=(PhaseSpec("perception", "propose", "none", None, False), PhaseSpec("solver", "solve", "supplied", None, False)),
        max_contacts=2, stop_rule="always-run-full-program",
    ).validate()


def _hermetic_i0(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    ids = ("row-a", "row-b", "row-c")
    identity = split_identity_hash(prefixed("slurp", ids))
    binding = {
        "construction_scope": _write_pin(repo_root / "scope.json", _roster(ids, roster_id="scope")),
        "permitted_roster": _write_pin(repo_root / "permitted.json", _roster(ids, roster_id="permitted")),
        "forbidden_rosters": [_write_pin(repo_root / "forbidden.json",
                                         _roster(("forbidden-1",), roster_id="forbidden", roster_role="evaluation"))],
    }
    registration = repo_root / "registration-i0.json"
    data_root = tmp_path / "data"
    ace.build_playbook_release(
        ace.empty_playbook(), data_root=data_root, carrier_sample_ids=("row-a",), legal_intent_ids=LEGAL,
        source_split_identity_hash=identity, registration_binding=binding, registration_path=registration,
    )
    completion = prepare_semantic_knowledge_store(registration, repo_root=repo_root, data_root=data_root)["completion"]
    store = lock_v2_3.ace_store_i0()
    store["release"], store["snapshot"] = completion["release"], completion["snapshot"]
    return data_root, store


def _solver_supply(store, data_root, candidates):
    from test_candidate_semantic_supply import _artifact, _context  # noqa: PLC0415

    binding = load_knowledge_store_binding({"knowledge_stores": {"ace-playbook": copy.deepcopy(store)}}, data_root=data_root)
    # the production routing: the lock's own context_supply spec, phase names renamed to the synthetic program's
    router = build_knowledge_store_supply(binding, program=_program(), data_root=data_root, legal_candidate_ids=LEGAL)
    context = _context(binding, _artifact("s1", candidates, state_kind="phase:perception"))
    return router, router.automatic_for_phase("solver", context), router.automatic_for_phase("perception", context)


def test_the_hermetic_i0_release_supplies_the_solver_nothing_for_any_candidate_set(tmp_path):
    data_root, store = _hermetic_i0(tmp_path)
    for candidates in (LEGAL, LEGAL[:1], LEGAL[1:3]):
        router, solver, perception = _solver_supply(store, data_root, candidates)
        assert solver is None and perception is None
        entry = next(iter(router.receipt["delta_supply"].values()))
        assert entry["selected"] == 0 and entry["store_id"] == "ace-playbook" and entry["phase"] == "solver"
        assert entry["reason"] == "no delta of this node slice matches the row candidates"
    assert router.receipt["stores"]["ace-playbook"]["context_supply"] == ["solver"]


def _real_data_root():
    root = os.environ.get("SPEECHRL_DATA_DIR")
    if not root or not (Path(root) / lock_v2_3.ACE_I0_RELEASE["relpath"]).is_file():
        pytest.skip("the prepared ace-playbook-i0 release is not on this machine's data root")
    return Path(root)


def test_the_real_i0_release_loads_at_the_lock_pins_and_supplies_the_solver_nothing():
    data_root = _real_data_root()
    store = lock_v2_3.ace_store_i0()
    binding = load_knowledge_store_binding({"knowledge_stores": {"ace-playbook": store}}, data_root=data_root)
    snapshot = binding.snapshot_for("ace-playbook")
    assert len(snapshot.values) == 1 and snapshot.values[0].task_target.startswith("planner:")
    assert snapshot.content_hash() == lock_v2_3.ACE_I0_SNAPSHOT["sha256"]
    for candidates in (LEGAL, LEGAL[:1]):
        _router, solver, perception = _solver_supply(store, data_root, candidates)
        assert solver is None and perception is None


# ---------------------------------------------------------------------------
# P-ACE-0 through the production walk (graph, request renderer, state sealer, trace sink)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not WALK_AVAILABLE, reason="OpenJiuwen unavailable")
def test_p_ace_0_every_request_is_byte_identical_under_v2_2_and_v2_3(tmp_path):
    from test_consumption_module_supply_columns import _requests  # noqa: PLC0415
    from test_stage3_supply_variant_interleaving import ARM_VALUE  # noqa: PLC0415

    seen = {}
    for lock in ("v2.2", "v2.3"):
        composed, values = _compose(_block(lock))
        assert composed.program_ceiling == 2
        assert load_native_episode_config(values, default_phase_program(values["policy"])).max_contacts == 2
        result, requests = _requests(tmp_path / lock, group=None, max_contacts=2, selections=None)
        seen[lock] = (result.final_response_text, requests)
    assert len(seen["v2.2"][1]) == 2                       # the Perception request and the Solver request
    assert seen["v2.2"][1] == seen["v2.3"][1]              # whole payloads, every field, both contacts
    assert seen["v2.2"][0] == seen["v2.3"][0]
    assert json.dumps(seen["v2.2"][1], sort_keys=True) == json.dumps(seen["v2.3"][1], sort_keys=True)

    # and with two knob supply columns armed (the release-swap arm needs the flight-owned resolver): every request is equal
    armed = {}
    for lock in ("v2.2", "v2.3"):
        composed, values = _compose(_knob_block(lock))
        group = load_native_episode_config(values, default_phase_program(values["policy"])).supply_variant_group
        _result, requests = _requests(
            tmp_path / f"armed-{lock}", group=group, max_contacts=composed.program_ceiling,
            selections={"typ": (ARM_VALUE,), "ace": (ARM_VALUE,), "aa": (), "lock": ()},
        )
        armed[lock] = requests
    assert armed["v2.2"] == armed["v2.3"]


def _knob_block(lock):
    block = review_off_block()
    block["lock"] = lock
    block["columns"] = [
        {"column_id": "typ", "kind": "supply", "node": "solver", "max_supplied_items": 40, "overrides": {EX_K: 10}},
        {"column_id": "ace", "kind": "supply", "node": "solver", "max_supplied_items": 40, "overrides": {EX_K: 5}},
    ]
    block["supply_frame"] = {"twin": True, "fit_estimate": dict(FIT), "delivering_max_supplied_items": 55}
    return block


# ---------------------------------------------------------------------------
# the ACE supply column under the REAL hooks (no wrapper)
# ---------------------------------------------------------------------------


def test_the_ace_column_with_a_declared_release_swap_verifies_under_the_real_hooks_on_v2_3():
    block = _block("v2.3", ace_column=True)
    composed, values = _compose(block)
    arms = values["native_episode"]["roles"]["solver"]["supply_variants"]["arms"]
    assert [a["arm_id"] for a in arms] == ["typ", "ace", "aa", "lock"]
    assert arms[1]["release_swap"] == {"store_id": "ace-playbook", "release": ACE_ALT["ace-playbook"][0]["release"]["relpath"]}
    assert values["knowledge_stores"]["ace-playbook"]["alternates"] == ACE_ALT["ace-playbook"]
    assert values["knowledge_stores"]["ace-playbook"]["release"] == lock_v2_3.ACE_I0_RELEASE
    cm.verify_declared_module(block, values)                # the loader's check, the REAL carrier hooks
    parsed = load_native_episode_config(values, default_phase_program(values["policy"]))
    assert parsed.supply_variant_group.arm_ids == ("typ", "ace", "aa", "lock")


def test_a_swap_to_an_undeclared_release_is_refused_and_v2_2_cannot_host_the_column():
    undeclared = "knowledge/slurp/semantic/ace-playbook-i2/release.json"
    with pytest.raises(cm.ConsumptionModuleConfigError, match="absent from its declared alternates"):
        cm.compile_module(_block("v2.3", ace_column=True, swap_release=undeclared), carrier_module_hooks())
    with pytest.raises(cm.ConsumptionModuleConfigError, match="lock layer does not declare"):
        cm.compile_module(_block("v2.2", ace_column=True), carrier_module_hooks())
    # a drift of the declared store entry in a composed document is a refusal as well
    block = _block("v2.3", ace_column=True)
    _composed, values = _compose(block)
    drifted = copy.deepcopy(values)
    drifted["knowledge_stores"]["ace-playbook"].pop("alternates")
    with pytest.raises(cm.ConsumptionModuleConfigError, match="differ"):
        cm.verify_declared_module(block, drifted)
    assert smh.carrier_module_hooks().lock_versions["v2.3"] is not None
