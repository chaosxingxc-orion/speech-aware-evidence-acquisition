"""Evidence-consumption module, migration step 6 (owner decisions 195, 196 and
204; design docs/superpowers/specs/2026-09-29-slurp-consumption-module-design.md
section 4 step 6, coordinator ruling R2).

* The harness ``module`` switch class: ONE key, ``native_episode.consumption_module``,
  whose OFF arm is the all-off block on the carrier's CURRENT lock (v2.1 here; v2.2 since
  decision 249, see the superseded-lock case below) and
  compiles byte for byte to it; ``harness_admission_check.py`` recomputes that
  licence rather than believing it.
* Lock versions: ``lock: v2.1`` is the v2.0 layer with ONE pin moved (the G5
  Reviewer template); a block with no ``lock`` key still compiles to v2.0.
* Roster pins: the sealed per-roster query vectors inside the policy blocks
  are cell identity, never policy.
* The module's first end-to-end cell (COMP-1b on DEV-2000-ADDED as a module
  block on lock v2.1): its policy blocks are cell A2's flown bytes except the
  lock-v2.1 Reviewer pin, and its in-chain A/A is the lock-v2.1 bytes (AT-M6).

Model-free throughout: no model, server, GPU, network, flight or lease.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO / "scripts" / "analysis") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts" / "analysis"))

import module_equivalence_proof as proof  # noqa: E402

from speech_aware_evidence_acquisition.core.config import compose  # noqa: E402
from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters import slurp_module_hooks as smh  # noqa: E402
from speech_aware_evidence_acquisition.rails.config_tables import (  # noqa: E402
    MODULE_SWITCH_CLASS, SWITCH_CLASS_NAMES, ConfigTableError, module_block_of,
    resolve_module_switch_key,
)
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program  # noqa: E402
from speech_aware_evidence_acquisition.rails.native_episode_config import (  # noqa: E402
    load_native_episode_config,
)


def _load_check():
    spec = importlib.util.spec_from_file_location(
        "harness_admission_check", _REPO / "scripts" / "checks" / "harness_admission_check.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


hac = _load_check()

ARM = "slurp-native-stage3-module-comp1b-dev2000-added-v1"
SMOKE = "slurp-native-stage3-module-comp1b-dev2000-added-smoke-4-v1"
AA = "slurp-native-stage3-module-comp1b-aa-dev2000-added-v1"
A2_ARM = "slurp-native-stage3-comp1b-dev2000-added-v1"
BOUNDARY = "knowledge_stores.intent-boundaries.phase_supply.perception"


def _baseline_of(experiment: str) -> dict:
    cell = json.loads((_REPO / f"configs/experiment/{experiment}.json").read_text(encoding="utf-8"))["cells"][0]
    return json.loads((_REPO / f"configs/baseline/{cell['baseline_fragment']}.json").read_text(encoding="utf-8"))


def _composed(experiment: str):
    cell = json.loads((_REPO / f"configs/experiment/{experiment}.json").read_text(encoding="utf-8"))["cells"][0]
    return compose(_REPO, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], experiment)


def _hooks():
    return smh.carrier_module_hooks(repo_root=_REPO)


def _committed_module_entry() -> dict:
    receipt = json.loads((_REPO / "docs/receipts/harness-admission.json").read_text(encoding="utf-8"))
    return next(e for e in receipt["entries"] if e["switch"]["table"] == MODULE_SWITCH_CLASS)


# ---------------------------------------------------------------------------
# The harness ``module`` switch class (ruling R2).
# ---------------------------------------------------------------------------


def test_the_module_switch_is_one_key_whose_off_arm_compiles_to_the_lock():
    """The receipt entry's proof: ONE key; its OFF arm (the A/A's declared
    block) is the all-off block on lock v2.1 (the registered cell's lock, which
    CURRENT_LOCK v2.3 superseded under decisions 249 and 263 A) and compiles to exactly the
    lock v2.1 blocks; its ON arm (the arm's declared block) moves, against the OFF
    arm, exactly the leaves of the two components it arms."""

    assert MODULE_SWITCH_CLASS == "module" and SWITCH_CLASS_NAMES[-1] == MODULE_SWITCH_CLASS
    key = resolve_module_switch_key("native_episode.consumption_module")
    for bad in ("native_episode.consumption", "consumption_module", "native_episode.review_loop", "", None):
        with pytest.raises(ConfigTableError):
            resolve_module_switch_key(bad)
    arm, aa = _baseline_of(ARM), _baseline_of(AA)
    off, on = module_block_of(aa), module_block_of(arm)
    assert key == "native_episode.consumption_module"
    assert cm.is_module_off_block(off) and not cm.is_module_off_block(on)
    assert off["lock"] == on["lock"] == "v2.1" and smh.CURRENT_LOCK == "v2.3"
    hooks = _hooks()
    off_policy = cm.compile_module(off, hooks)
    assert off_policy.values() == json.loads(json.dumps(dict(hooks.lock_versions["v2.1"]())))
    on_policy = cm.compile_module(on, hooks)
    moved = cm.differing_paths(on_policy.values_on_roster_of(arm), off_policy.values_on_roster_of(aa))
    assert moved and all(
        path == f"{BOUNDARY}.rank_weights.w_agree" or path == f"{BOUNDARY}.k"
        or path.startswith((f"{BOUNDARY}.agreement_source.", f"{BOUNDARY}.facet_source."))
        for path in moved
    ), moved
    # The committed receipt entry carries exactly these two arms.
    entry = _committed_module_entry()
    assert entry["switch"]["off"] == off and entry["switch"]["on"] == on
    assert entry["status"] == "PENDING"
    # Decision 249: the registered entry keeps its cell's lock and names the lock that superseded it.
    assert entry["switch"]["lock_superseded_by"] == smh.CURRENT_LOCK


def test_the_committed_receipt_passes_with_the_module_entry():
    result = hac.evaluate(_REPO)
    assert result["passed"], result["failures"]
    row = next(r for r in result["entries"] if r["table"] == MODULE_SWITCH_CLASS)
    assert row["switch_key"] == "native_episode.consumption_module" and row["in_default_plans"] == []


def _evaluate_with(tmp_path, mutate) -> dict:
    receipt = json.loads((_REPO / "docs/receipts/harness-admission.json").read_text(encoding="utf-8"))
    entry = next(e for e in receipt["entries"] if e["switch"]["table"] == MODULE_SWITCH_CLASS)
    mutate(entry["switch"])
    path = tmp_path / "harness-admission.json"
    path.write_text(json.dumps(receipt), encoding="utf-8")
    return hac.evaluate(_REPO, path)


def _failures(result) -> str:
    return "\n".join(result["failures"])


def test_an_off_arm_with_a_component_on_is_refused(tmp_path):
    result = _evaluate_with(tmp_path, lambda s: s.__setitem__("off", copy.deepcopy(s["on"])))
    assert "is not the module's OFF arm" in _failures(result)


def test_an_off_arm_on_a_stale_lock_is_refused(tmp_path):
    def mutate(switch):
        switch["off"]["lock"] = "v2.0"
        switch.pop("lock_superseded_by")
    result = _evaluate_with(tmp_path, mutate)
    assert "CURRENT lock ('v2.3')" in _failures(result)


def test_a_superseded_lock_needs_a_pending_entry_naming_the_current_lock(tmp_path):
    """Decision 249: only a PENDING entry may stay on a lock CURRENT_LOCK has moved past, and it must
    name the CURRENT lock as its successor."""
    assert "lock_superseded_by" not in _failures(_evaluate_with(tmp_path, lambda s: None))

    def wrong_successor(switch):
        switch["lock_superseded_by"] = "v2.1"
    assert "lock_superseded_by is 'v2.1'" in _failures(_evaluate_with(tmp_path, wrong_successor))

    def no_marker(switch):
        switch.pop("lock_superseded_by")
    assert "CURRENT lock ('v2.3')" in _failures(_evaluate_with(tmp_path, no_marker))

    receipt = json.loads((_REPO / "docs/receipts/harness-admission.json").read_text(encoding="utf-8"))
    entry = next(e for e in receipt["entries"] if e["switch"]["table"] == MODULE_SWITCH_CLASS)
    entry["status"] = "ADMITTED"
    path = tmp_path / "admitted.json"
    path.write_text(json.dumps(receipt), encoding="utf-8")
    assert "only a PENDING entry may stay" in _failures(hac.evaluate(_REPO, path))


def test_an_off_arm_without_a_lock_key_is_refused(tmp_path):
    result = _evaluate_with(tmp_path, lambda s: (s["off"].pop("lock"), s.pop("lock_superseded_by")))
    assert "CURRENT lock" in _failures(result)


def test_a_falsifier_cell_that_does_not_carry_the_lock_is_refused(tmp_path):
    def mutate(switch):
        switch["falsifier"]["cells"] = ["slurp-native-default-plan-lock-v1"]  # the v2.0 bytes
    result = _evaluate_with(tmp_path, mutate)
    assert "does not carry lock v2.1's policy blocks" in _failures(result)
    assert "instruction_template" in _failures(result)


def test_a_missing_or_foreign_falsifier_is_refused(tmp_path):
    result = _evaluate_with(tmp_path, lambda s: s.pop("falsifier"))
    assert "compiles-to-lock" in _failures(result)
    result = _evaluate_with(tmp_path, lambda s: s["falsifier"].__setitem__("kind", "request-bytes-identical"))
    assert "compiles-to-lock" in _failures(result)


def test_an_on_arm_that_arms_nothing_or_does_not_compile_is_refused(tmp_path):
    result = _evaluate_with(tmp_path, lambda s: s.__setitem__("on", copy.deepcopy(s["off"])))
    assert "arms at least one component" in _failures(result)

    def g5_over_v2_1(switch):
        entry = proof.component_entries()[cm.REVIEWER_G5_REPAIR]
        switch["on"]["components"] = [entry if c["component_id"] == cm.REVIEWER_G5_REPAIR else c
                                      for c in switch["on"]["components"]]
    result = _evaluate_with(tmp_path, g5_over_v2_1)
    assert "does not compile" in _failures(result) and "already carries this Reviewer template" in _failures(result)


def test_a_plan_arms_the_module_key_only_with_a_non_off_block():
    arm, aa = _baseline_of(ARM), _baseline_of(AA)
    key = "native_episode.consumption_module"
    assert hac._switch_present(arm, MODULE_SWITCH_CLASS, key) is True
    assert hac._switch_present(aa, MODULE_SWITCH_CLASS, key) is False
    assert hac._switch_present(_baseline_of(A2_ARM), MODULE_SWITCH_CLASS, key) is False


# ---------------------------------------------------------------------------
# Lock versions (owner decision 204).
# ---------------------------------------------------------------------------


def test_lock_v2_1_is_the_v2_0_layer_with_exactly_the_reviewer_template_moved():
    hooks = _hooks()
    v20, v21 = dict(hooks.lock_versions["v2.0"]()), dict(hooks.lock_versions["v2.1"]())
    assert cm.differing_paths(v20, v21) == ["phase_material.reviewer.instruction_template"]
    assert v21["phase_material"]["reviewer"]["instruction_template"] == smh.LOCK_V2_1_REVIEWER_TEMPLATE[0]
    assert dict(hooks.lock_layer()) == v20  # a block with no lock key keeps the v2.0 bytes


def test_a_block_without_a_lock_key_still_compiles_to_the_v2_0_lock():
    hooks = _hooks()
    bare = proof.module_block(())
    assert "lock" not in bare
    composed = cm.compile_module(bare, hooks)
    assert composed.lock_version is None
    assert composed.values() == json.loads(json.dumps(dict(hooks.lock_layer())))
    with_v20 = cm.compile_module(proof.module_block((), lock="v2.0"), hooks)
    assert with_v20.values() == composed.values()
    assert with_v20.config_block_sha256 != composed.config_block_sha256  # the key is identity


@pytest.mark.parametrize("lock, message", [
    ("v9.9", "is not a lock version"), ("2.1", "must match"), ("", "must match"), (21, "must match"),
])
def test_an_unknown_or_malformed_lock_is_refused(lock, message):
    block = proof.module_block(())
    block["lock"] = lock
    with pytest.raises(cm.ConsumptionModuleConfigError, match=message):
        cm.compile_module(block, _hooks())


def test_the_g5_repair_cannot_be_armed_over_a_lock_that_already_carries_it():
    with pytest.raises(cm.ConsumptionModuleConfigError, match="already carries this Reviewer template"):
        cm.compile_module(proof.module_block((cm.REVIEWER_G5_REPAIR,), lock="v2.1"), _hooks())
    # ... and on v2.0 it still compiles to cell G5, as before.
    assert proof.run_case("extra")["ok"]


def test_a_carrier_without_lock_versions_refuses_a_named_lock():
    hooks = _hooks()
    bare = cm.CarrierHooks(profile="slurp", lock_layer=hooks.lock_layer, flown_programs=hooks.flown_programs)
    with pytest.raises(cm.ConsumptionModuleConfigError, match="lock_versions"):
        cm.compile_module(proof.module_block((), lock="v2.1"), bare)


# ---------------------------------------------------------------------------
# Roster pins are cell identity.
# ---------------------------------------------------------------------------


def test_roster_pins_are_the_targets_own_and_nothing_else_is():
    hooks = _hooks()
    composed = cm.compile_module(proof.module_block((), lock="v2.1"), hooks)
    aa = _baseline_of(AA)
    rebuilt = composed.apply_to(aa)
    for path in smh.ROSTER_PIN_PATHS:
        node_rebuilt, node_aa, node_lock = rebuilt, aa, composed.values()
        for key in path:
            node_rebuilt, node_aa, node_lock = node_rebuilt[key], node_aa[key], node_lock[key]
        assert node_rebuilt == node_aa and node_rebuilt != node_lock  # DEV vectors, not Fold A's
    diff = cm.differing_paths(composed.values(), cm.policy_owned_values(aa))
    assert diff and all(".query_source." in p for p in diff)


# ---------------------------------------------------------------------------
# The module's first end-to-end cell (AT-M6).
# ---------------------------------------------------------------------------


def test_at_m6_the_module_cell_is_a2_except_the_lock_v2_1_reviewer_pin():
    report = proof.run_case("m6")
    assert report["ok"], report
    by = {row["cell"]: row for row in report["results"]}
    for key in ("arm", "smoke"):
        assert by[key]["module_policy_on_a2_roster_differing_paths"] == [proof.REVIEWER_TEMPLATE_LEAF]
        assert by[key]["composed_config_diff_vs_a2"]["policy"] == [proof.REVIEWER_TEMPLATE_LEAF]
        assert by[key]["armed"] == [cm.AGREE_VOTE_SEED, cm.CENTROID_BOUNDARY_KEY]
        assert by[key]["program_id"] == "phase-native-candidates-review-revise-v1"
        assert by[key]["program_ceiling"] == 11
    assert by["aa"]["off_arm"] is True and by["aa"]["lock_v2_1_differing_paths"] == []
    assert by["aa"]["module_policy_on_a2_roster_differing_paths"] == [proof.BOUNDARY_K_LEAF, proof.REVIEWER_TEMPLATE_LEAF]


@pytest.mark.parametrize("experiment", [ARM, SMOKE, AA])
def test_the_loader_accepts_each_module_cell_and_binds_its_block(experiment):
    composed = _composed(experiment)
    config = load_native_episode_config(composed.values, default_phase_program(composed.values["policy"]))
    assert json.loads(config.consumption_module_json) == composed.values["native_episode"]["consumption_module"]


def test_the_loader_refuses_a_module_cell_whose_policy_was_hand_edited():
    composed = _composed(ARM)
    values = copy.deepcopy(composed.values)
    values["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]["k"] = 8
    with pytest.raises(ValueError, match="differ from what its consumption_module block compiles to"):
        load_native_episode_config(values, default_phase_program(values["policy"]))


def test_the_module_cells_are_held_and_fly_in_one_campaign():
    plan = json.loads((_REPO / "configs/campaign/slurp-native-stage3-module-comp1b-dev2000-added-v1.json").read_text(
        encoding="utf-8"))
    assert [c["cell"] for c in plan["cells"]] == [AA, ARM]
    for experiment in (ARM, SMOKE, AA):
        cell = json.loads((_REPO / f"configs/experiment/{experiment}.json").read_text(encoding="utf-8"))["cells"][0]
        # held at registration (2026-09-30); flipped to ready for the NX R5 chain (2026-10-10, 5ec1db691)
        assert cell["readiness"]["state"] in ("held", "ready")
        assert _baseline_of(experiment)["native_episode"]["finite_completion_policy"] == "deliver-latest-or-abstain"
