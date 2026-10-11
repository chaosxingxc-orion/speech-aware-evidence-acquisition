"""Loop engineering items E-S1/E-S2: a derived module cell carrying a supply column passes the model-free gates.

A 4-row dry run is shown by TEST, not by flight: a cell derived the way the NX derive scripts derive one (the
registered R5 review-off module baseline on lock v2.2, its module block extended with supply columns, every policy
block rewritten by the compiler) composes, loads, and clears the effect-floor, finite-completion, harness-admission and
flight-registration gates on synthetic trees, up to the refusals an unsigned, unminted cell owes (not-ready,
row-not-countersigned, receipt-missing). Nothing is registered in docs/readiness/ and no ledger row is written.
Model-free.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
for _extra in (REPO / "scripts" / "checks",):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

import finite_completion_policy_check as finite_gate  # noqa: E402
import flight_registration_check as flight_gate  # noqa: E402
import stage3_effect_floor_check as floor_gate  # noqa: E402
import test_finite_completion_policy_check as finite_t  # noqa: E402
import test_flight_registration_check as flight_t  # noqa: E402
import test_harness_admission_check as harness_t  # noqa: E402
from test_stage3_effect_floor_check import _build as floor_build  # noqa: E402
from test_stage3_effect_floor_check import _declaration, _kinds as floor_kinds  # noqa: E402

from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import (  # noqa: E402
    carrier_module_hooks,
)
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program  # noqa: E402
from speech_aware_evidence_acquisition.rails.native_episode_config import (  # noqa: E402
    load_native_episode_config,
)

R5 = "configs/baseline/slurp-native-stage3-nx-r5-composed-dev2000-added-baseline-v1.json"
EX_K = "knowledge_stores.train-exemplars.phase_supply.solver.k"
FIT = {
    "slot_tokens": 24576, "completion_ceiling": 640,
    "base_prompt_tokens": 9600, "tokens_per_supplied_item": 120,
}


def derive(*, candidates=1, twin=True) -> dict:
    """The derived cell's baseline: the R5 baseline with a supply column block, compiler-rewritten."""

    document = json.loads((REPO / R5).read_text(encoding="utf-8"))
    block = copy.deepcopy(document["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY])
    assert not block.get("columns") and block["review_loop"] == "off"
    block["columns"] = [
        {"column_id": f"typ{i}", "kind": "supply", "node": "solver", "max_supplied_items": 40,
         "overrides": {EX_K: 10 + i}}
        for i in range(candidates)
    ]
    block["supply_frame"] = {"twin": twin, "fit_estimate": dict(FIT), "delivering_max_supplied_items": 55}
    composed = cm.compile_module(block, carrier_module_hooks(), repo_root=REPO)
    derived = composed.apply_to(document)
    derived["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY] = block
    derived["_composed_ceiling"] = composed.program_ceiling
    return derived


def test_the_derived_two_arm_cell_composes_loads_and_verifies():
    derived = derive(twin=False)  # one candidate + the delivering arm: a two-arm column
    ceiling = derived.pop("_composed_ceiling")
    block = derived["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY]
    cm.verify_declared_module(block, derived, repo_root=REPO)
    assert derived["policy"] == "phase-native-module-v1-c3" and ceiling == 3
    parsed = load_native_episode_config(
        dict(derived, carrier_lock_key="slurp"), default_phase_program(derived["policy"]))
    group = parsed.supply_variant_group
    assert group.arm_ids == ("typ0", "lock") and group.arm_visits == "first"
    assert parsed.max_contacts == 3
    # the policies the finite-completion gate demands survive the compile
    ne = derived["native_episode"]
    assert ne["finite_completion_policy"] == "deliver-latest-or-abstain"
    assert ne["react_exhaustion_policy"] == "continue-without-answer"
    # FIT cap formula: rows x max_contacts x 4
    assert 4 * parsed.max_contacts * 4 == 48


def test_the_twin_form_adds_the_a_a_replicate():
    derived = derive(candidates=1, twin=True)
    assert derived.pop("_composed_ceiling") == 4
    assert derived["policy"] == "phase-native-module-v1-c4"


def test_the_finite_completion_gate_passes_the_derived_cell(tmp_path):
    derived = derive(twin=False)
    derived.pop("_composed_ceiling")
    finite_t._build(tmp_path, policy="deliver-latest-or-abstain")
    baseline = tmp_path / "configs" / "baseline" / f"{finite_t.BASELINE}.json"
    baseline.write_text(json.dumps(derived, indent=2, sort_keys=True), encoding="utf-8")
    result = finite_gate.evaluate(tmp_path)
    assert result["passed"] is True and result["violations"] == []
    assert result["checked_baselines"] == [finite_t.BASELINE]
    # a derived cell that dropped the policy would be refused
    broken = copy.deepcopy(derived)
    broken["native_episode"].pop("finite_completion_policy")
    baseline.write_text(json.dumps(broken, indent=2, sort_keys=True), encoding="utf-8")
    assert not finite_gate.evaluate(tmp_path)["passed"]


def test_the_effect_floor_gate_reads_the_cell_as_a_same_flight_supply_column(tmp_path):
    # the arm: 1,080 rows, expected effect above the same-flight contrast floor, benefit claimed
    floor_build(
        tmp_path,
        declaration=_declaration(
            measurement_design="same-flight-supply-variant", expected_effect_pp=2.0, rows=1080,
            primary_metric_key="slu"),
        rows=1080, registered_date="2026-10-11")
    data = floor_gate.evaluate(tmp_path)
    assert floor_kinds(data) == [] and data["passed"] is True
    # below the floor: refused
    low = tmp_path / "low"
    low.mkdir()
    floor_build(
        low,
        declaration=_declaration(
            measurement_design="same-flight-supply-variant", expected_effect_pp=1.0, rows=1080,
            primary_metric_key="slu"),
        rows=1080, registered_date="2026-10-11")
    assert floor_kinds(floor_gate.evaluate(low)) == ["effect-below-floor"]
    # the 4-row smoke is a form proof: no benefit claim
    smoke = tmp_path / "smoke"
    smoke.mkdir()
    floor_build(
        smoke,
        declaration=_declaration(
            measurement_design="same-flight-supply-variant", expected_effect_pp=0.0, rows=4,
            claims_benefit=False, primary_metric_key="slu"),
        rows=4, registered_date="2026-10-11")
    assert floor_kinds(floor_gate.evaluate(smoke)) == []


def _flight_world(tmp_path, derived):
    world = flight_t.World(tmp_path)
    block = derived["native_episode"]["roles"]["solver"]["supply_variants"]
    extra = len(block["arms"]) - 1
    world.supply_variants = block
    world.measurement = {
        "measurement_design": "same-flight-supply-variant", "expected_effect_pp": 1.5,
        "claim": "nominated", "aa_arm_id": "aa",
        "tuning_roster": "SLURP-TUNE-POOL-V1",
        "read_roster": "SLURP-READ-FOLD-A-V1",
        "variant_cost": {"extra_contacts_per_row": extra, "extra_audio_seconds": 3.2 * extra},
    }
    world.write_roster_receipt(
        "SLURP-TUNE-POOL-V1",
        disjointness_proof={"slurp-read-fold-a-v1": {"shared_recordings": 0, "shared_utterances": 0}},
    )
    world.write_roster_receipt("SLURP-READ-FOLD-A-V1")
    return world


def test_flight_registration_accepts_the_cell_then_owes_the_unsigned_refusals(tmp_path):
    derived = derive(candidates=1, twin=True)
    derived.pop("_composed_ceiling")
    world = _flight_world(tmp_path, derived)
    data = world.build().run(cells=[flight_t.EXPERIMENT])
    kinds = flight_t._kinds(data)
    assert kinds == [], kinds
    assert data["cells"][0]["supply_variant"]["arm_visits"] == "first"
    # the refusals an unsigned, unminted, unready cell owes
    world.rows[flight_t.RUN] = flight_t._row(flight_t.RUN, flight_t.DRAFT)
    world.states[flight_t.EXPERIMENT] = "held"
    data = world.build().run(cells=[flight_t.EXPERIMENT])
    kinds = flight_t._kinds(data)
    assert "row-not-countersigned" in kinds and "not-ready" in kinds
    (world.data / flight_t.RECEIPT).unlink()
    assert "receipt-missing" in flight_t._kinds(world.run(cells=[flight_t.EXPERIMENT]))


def test_flight_registration_refuses_a_cost_that_ignores_the_column_arms(tmp_path):
    derived = derive(candidates=2, twin=True)
    derived.pop("_composed_ceiling")
    world = _flight_world(tmp_path, derived)
    world.measurement["variant_cost"]["extra_contacts_per_row"] = 1  # K = 4 arms -> 3 extra
    assert "variant-cost-mismatch" in flight_t._kinds(world.build().run(cells=[flight_t.EXPERIMENT]))


def test_harness_admission_compiles_a_supply_column_on_arm():
    receipt = harness_t._committed()
    entry = next(e for e in receipt["entries"] if e["switch"]["table"] == "module")
    switch = copy.deepcopy(entry["switch"])
    # an ON arm that arms a supply column (no component armed beyond the OFF arm's)
    on = copy.deepcopy(switch["off"])
    on["review_loop"] = "off"
    on["columns"] = [{"column_id": "typ", "kind": "supply", "node": "solver", "max_supplied_items": 40,
                      "overrides": {EX_K: 10}}]
    on["supply_frame"] = {"twin": True, "fit_estimate": dict(FIT), "delivering_max_supplied_items": 55}
    switch["on"] = on
    failures = harness_t.hac._check_module_switch(switch, REPO, "entry", entry.get("status"))
    assert not [f for f in failures if "does not compile" in f], failures
    # a malformed supply column in the ON arm is named by the gate
    on["columns"][0]["overrides"] = {"knowledge_stores.train-exemplars.phase_supply.solver.tau": 3}
    failures = harness_t.hac._check_module_switch(switch, REPO, "entry", entry.get("status"))
    assert any("does not compile" in f for f in failures)


def test_the_committed_harness_receipt_still_passes():
    assert harness_t.hac.evaluate(REPO)["passed"] is True
