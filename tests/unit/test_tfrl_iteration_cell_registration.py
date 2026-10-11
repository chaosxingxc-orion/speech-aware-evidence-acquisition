"""Loop iteration cells (decision 263-A): derived cells compose, labels resolve, and the model-free gates see exactly the owed refusals.

A cell derived by ``scripts/flights/tfrl/derive_tfrl_iteration_cells.py`` (the NX R6-P1 Fold B base with the Perception template columns
replaced by Solver ``kind: supply`` columns, compiled by ``rails.consumption_module``) and registered by
``write_tfrl_iteration_registration.py`` is built in a WRITABLE OVERLAY of the repository (``tfrl_overlay``; the real tree is never
written) and shown, in the manner of ``test_supply_column_cell_checks.py``, to:

* compose and carry the arm set of its iteration with the delivering arm LAST and the twin ``replicate_of`` it;
* clear the finite-completion, effect-floor (same-flight supply variant), harness-admission (typed columns) and flight-registration
  gates up to the refusals an unsigned, unminted, unready cell owes;
* resolve its ``stage3_algorithm`` label (two algorithms in one fragment);
* compose on lock v2.3 (v2.2 plus the empty ``ace-playbook-i0`` declaration, decisions 263 A / 266-A), so the loader's
  ``verify_declared_module`` accepts the ace column under the REAL carrier hooks, with no wrapper; only the ace release pins of
  the iteration (zeros until it is prepared) remain a named blocker.

No contact, no ledger row in the real ledger, no flip. Synthetic and aggregate only.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[2]
TFRL = REPO / "scripts" / "flights" / "tfrl"
for _extra in (REPO / "scripts" / "checks", TFRL, REPO / "src"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

import derive_tfrl_iteration_cells as dv  # noqa: E402
import finite_completion_policy_check as finite_gate  # noqa: E402
import flight_registration_check as flight_gate  # noqa: E402
import stage3_effect_floor_check as floor_gate  # noqa: E402
import test_finite_completion_policy_check as finite_t  # noqa: E402
import test_flight_registration_check as flight_t  # noqa: E402
import test_harness_admission_check as harness_t  # noqa: E402
import tfrl_family as tf  # noqa: E402
import tfrl_overlay  # noqa: E402
import write_tfrl_iteration_registration as reg  # noqa: E402
from test_stage3_effect_floor_check import _build as floor_build  # noqa: E402
from test_stage3_effect_floor_check import _declaration, _kinds as floor_kinds  # noqa: E402

from speech_aware_evidence_acquisition.core import roster as roster_module  # noqa: E402
from speech_aware_evidence_acquisition.core.config import compose  # noqa: E402
from speech_aware_evidence_acquisition.core.stage3_algorithms import validate_stage3_algorithm_label  # noqa: E402
from speech_aware_evidence_acquisition.rails import consumption_module as cm
from speech_aware_evidence_acquisition.rails.adapters import slurp_module_lock_v2_3 as lock_v2_3  # noqa: E402
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program  # noqa: E402
from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config  # noqa: E402

EX_K = "knowledge_stores.train-exemplars.phase_supply.solver.k"
COMMIT, AT = "b" * 40, "2026-10-11T12:00:00.000000+00:00"


def spec(*, typed: bool = False, parent: bool = False, iteration: int = 1) -> dict:
    return {"typed": {"overrides": {EX_K: 12}} if typed else None,
            "parent": {"overrides": {EX_K: 10}} if parent else None, "ace": {"iteration": iteration}}


@pytest.fixture(scope="module")
def derived(tmp_path_factory):
    """The iteration-1 stall form (ace / aa / lock), derived and registered once in a writable overlay."""

    root = tfrl_overlay.make_overlay(tmp_path_factory.mktemp("overlay"), REPO)
    result = reg.write_iteration(root, 1, spec(), COMMIT, AT, predicted_effect_pp=0.0, with_proposers=False)
    return SimpleNamespace(root=root, result=result)


def fresh_ledger_overlay(dest: Path) -> Path:
    """An overlay whose ledger copy has NO row of the iteration-1 column package (the pre-countersign state a fresh registration appends to)."""

    root = tfrl_overlay.make_overlay(dest, REPO)
    ledger = root / "docs" / "exposure-ledger.md"
    package = reg.package_names(1)["column"]
    kept = [line for line in ledger.read_text(encoding="utf-8").split("\n")
            if not (line.startswith("| ") and (f"{package}/" in line or "SAEA-SLURP-STAGE3-TFRL-LOOP-I1-FOLD-B-" in line))]
    ledger.write_text("\n".join(kept), encoding="utf-8", newline="\n")
    return root


def baseline(root: Path, iteration: int = 1, kind: str = "arm") -> dict:
    name = tf.names(iteration, kind)["baseline"]
    return json.loads((root / "configs" / "baseline" / f"{name}.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------------------------------------------------------
# composition
# ---------------------------------------------------------------------------------------------------------------------------


def test_the_stall_form_carries_ace_aa_lock_with_the_delivering_arm_last(derived):
    document = baseline(derived.root)
    group = document["native_episode"]["roles"]["solver"]["supply_variants"]
    assert [a["arm_id"] for a in group["arms"]] == ["ace", "aa", "lock"]
    assert group["arms"][1]["replicate_of"] == "lock"
    last = group["arms"][-1]
    assert last["deliver"] is True and "overrides" not in last and "release_swap" not in last
    assert group["arms"][0]["release_swap"]["store_id"] == tf.ACE_STORE_ID
    assert group["arm_visits"] == "first"
    assert document["policy"] == "phase-native-module-v1-c4"
    ne = document["native_episode"]
    assert ne["finite_completion_policy"] == "deliver-latest-or-abstain" and ne["react_exhaustion_policy"] == "continue-without-answer"
    assert (ne["review_loop"], ne["max_revisions"]) == ("off", 0)
    assert "prepared_phase_supply" not in document
    store = document["knowledge_stores"][tf.ACE_STORE_ID]
    assert store["store_role"] == "stage3-deltas" and store["context_supply"]["solver"]["cap"] == 8
    assert document["knowledge_stores"][tf.ACE_STORE_ID]["alternates"][0]["release"]["relpath"].endswith("ace-playbook-i1/release.json")
    # FIT cap = rows x ceiling x 4 endpoints
    assert document["native_contact_fit"]["contact_cap"] == 1080 * 4 * 4
    smoke = baseline(derived.root, kind="smoke")
    assert smoke["native_contact_fit"]["contact_cap"] == 4 * 4 * 4


@pytest.mark.parametrize("typed,parent,iteration,arms,program", [
    (True, False, 1, ["typ", "ace", "aa", "lock"], "phase-native-module-v1-c5"),
    (False, True, 2, ["par", "ace", "aa", "lock"], "phase-native-module-v1-c5"),
    (True, True, 2, ["par", "typ", "ace", "aa", "lock"], "phase-native-module-v1-c6"),
    (True, True, 3, ["par", "typ", "ace", "aa", "lock"], "phase-native-module-v1-c6"),
])
def test_the_arm_set_follows_the_iteration_and_the_typed_arm_may_be_absent(tmp_path, typed, parent, iteration, arms, program):
    root = tfrl_overlay.make_overlay(tmp_path / "o", REPO)
    out = dv.derive_iteration(iteration, spec(typed=typed, parent=parent, iteration=iteration), repo_root=root)
    assert out["arms"] == arms and out["program"] == program and out["ceiling"] == len(arms) + 1
    group = baseline(root, iteration)["native_episode"]["roles"]["solver"]["supply_variants"]
    assert [a["arm_id"] for a in group["arms"]] == arms
    assert tf.arm_ids(iteration, typed_present=typed, parent_present=parent) == tuple(arms)


def test_derivation_is_idempotent(derived):
    root = derived.root
    names = tf.names(1, "arm")
    files = [root / "configs" / "baseline" / f"{names['baseline']}.json", root / "configs" / "experiment" / f"{names['experiment']}.json",
             root / names["campaign"]]
    before = [f.read_bytes() for f in files]
    dv.derive_iteration(1, spec(), repo_root=root)
    assert [f.read_bytes() for f in files] == before


def test_the_experiment_fragment_is_held_and_carries_no_inherited_identity(derived):
    names = tf.names(1, "arm")
    experiment = json.loads((derived.root / "configs" / "experiment" / f"{names['experiment']}.json").read_text(encoding="utf-8"))
    cell = experiment["cells"][0]
    assert cell["readiness"]["state"] == "held" and cell["cell_id"] == names["experiment"] and cell["run_id"] == names["run_id"]
    text = json.dumps(experiment)
    assert "nx-r6" not in text.lower().replace("nx r6", "") and "R6-P1" not in text
    assert experiment["population"]["count"] == 1080 and experiment["execution_profile"] == "bounded-discovery-probe"
    assert experiment["family_budget"]["generation_calls_cap"] == 1080 * 4
    composed = compose(derived.root, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], names["experiment"])
    assert composed.values["policy"] == "phase-native-module-v1-c4" and composed.values["carrier_lock_key"] == "slurp"


def test_every_policy_and_scorer_value_resolves_in_the_core_registries(derived):
    from speech_aware_evidence_acquisition.core import base

    values = baseline(derived.root)
    default_phase_program(values["policy"])
    assert values["evidence_source"] in base.EVIDENCE_SOURCES.names()
    for scorer in values["scorers"]:
        assert scorer in base.SCORERS.names()


# ---------------------------------------------------------------------------------------------------------------------------
# labels
# ---------------------------------------------------------------------------------------------------------------------------


def test_the_iteration_cell_label_holds_two_algorithms_and_resolves(derived):
    names = tf.names(1, "arm")
    experiment = json.loads((derived.root / "configs" / "experiment" / f"{names['experiment']}.json").read_text(encoding="utf-8"))
    record, used = validate_stage3_algorithm_label(experiment["stage3_algorithm"], cell=names["experiment"])
    assert record.id == tf.ALGORITHM_TYPED and "credit_assignment" in used
    assert experiment["stage3_algorithm"]["columns"] == {"ace": tf.ALGORITHM_ACE}
    bad = copy.deepcopy(experiment["stage3_algorithm"])
    bad["columns"]["ace"] = "no-such-algorithm"
    with pytest.raises(Exception, match="no-such-algorithm|unregistered|not registered|unknown"):
        validate_stage3_algorithm_label(bad, cell="x")
    typed = dv.algorithm_label(spec(typed=True, parent=True, iteration=2))
    assert typed["columns"] == {"par": tf.ALGORITHM_TYPED, "typ": tf.ALGORITHM_TYPED, "ace": tf.ALGORITHM_ACE}
    validate_stage3_algorithm_label(typed, cell="i2")
    for kind in ("typed", "ace"):
        validate_stage3_algorithm_label(dv.text_only_label(kind), cell=kind)


def test_the_stage3_label_gate_accepts_the_derived_fragment(derived):
    import stage3_algorithm_label_check as label_gate

    result = label_gate.evaluate(derived.root)
    assert result["passed"] is True and result["violations"] == []
    mine = [c for c in result["stage3_cells"] if c["cell"] in (tf.names(1, "arm")["experiment"], tf.names(1, "smoke")["experiment"])]
    assert len(mine) == 2 and {c["algorithm_id"] for c in mine} == {tf.ALGORITHM_TYPED}


# ---------------------------------------------------------------------------------------------------------------------------
# the cell loads under the REAL hooks (lock v2.3), and only the ace release pins of the iteration are pending
# ---------------------------------------------------------------------------------------------------------------------------


def test_the_loader_accepts_the_derived_cell_under_the_real_hooks_and_only_the_release_pins_are_pending(derived):
    document = baseline(derived.root)
    block = document["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY]
    assert block["lock"] == tf.LOCK == "v2.3" and tf.PARENT_LOCK == "v2.2"
    assert not hasattr(dv, "hooks_with_ace_store")                   # the wrapper workaround is gone
    assert derived.result["loader_verification"] == {"ok": True, "refusal": None}
    assert {b["id"] for b in derived.result["column"]["blockers"]} == {"ace-release-pins-pending"}
    cm.verify_declared_module(block, document, repo_root=derived.root)      # the real hooks resolve the profile
    parsed = load_native_episode_config(dict(document, carrier_lock_key="slurp"), default_phase_program(document["policy"]))
    group = parsed.supply_variant_group
    assert group.arm_ids == ("ace", "aa", "lock") and group.arm_visits == "first" and parsed.max_contacts == 4
    # the primary ace-playbook store is the lock's own declaration of the empty release i0
    assert document["knowledge_stores"][tf.ACE_STORE_ID]["release"] == lock_v2_3.ACE_I0_RELEASE
    assert document["knowledge_stores"][tf.ACE_STORE_ID]["snapshot"] == lock_v2_3.ACE_I0_SNAPSHOT


# ---------------------------------------------------------------------------------------------------------------------------
# gates
# ---------------------------------------------------------------------------------------------------------------------------


def test_the_finite_completion_gate_passes_the_derived_cell(derived, tmp_path):
    finite_t._build(tmp_path, policy="deliver-latest-or-abstain")
    path = tmp_path / "configs" / "baseline" / f"{finite_t.BASELINE}.json"
    path.write_text(json.dumps(baseline(derived.root), indent=2, sort_keys=True), encoding="utf-8")
    result = finite_gate.evaluate(tmp_path)
    assert result["passed"] is True and result["violations"] == []
    broken = baseline(derived.root)
    broken["native_episode"].pop("react_exhaustion_policy")
    path.write_text(json.dumps(broken, indent=2, sort_keys=True), encoding="utf-8")
    assert not finite_gate.evaluate(tmp_path)["passed"]


def measurement(root: Path, kind: str = "arm") -> tuple[str, dict]:
    facts = json.loads((root / reg.package_names(1)["column"] / "registered-facts-v1.json").read_text(encoding="utf-8"))
    run_id = tf.names(1, kind)["run_id"]
    return run_id, facts["stage3_measurement"][run_id]


def test_the_effect_floor_gate_reads_the_registered_same_flight_measurement(derived, tmp_path):
    run_id, block = measurement(derived.root)
    assert block["measurement_design"] == "same-flight-supply-variant" and block["primary_metric_key"] == "slu"
    assert block["claims_benefit"] is False and block["expected_effect_pp"] == 0.0     # the stall form claims nothing
    declaration = _declaration(measurement_design=block["measurement_design"], expected_effect_pp=block["expected_effect_pp"],
                               rows=block["rows"], claims_benefit=block["claims_benefit"], primary_metric_key=block["primary_metric_key"])
    floor_build(tmp_path, declaration=declaration, rows=1080, registered_date="2026-10-11", run_id=run_id)
    assert floor_kinds(floor_gate.evaluate(tmp_path)) == []
    # a typed arm that flies must predict at least the floor; the writer sets claims_benefit only at >= 1.5 pp
    claimed = reg.measurement_blocks({"arm": {"run_id": "R", "program": "p"}, "smoke": {"run_id": "S", "program": "p"}}, 1, 2.0, ["typ", "ace", "aa", "lock"], 3.2)
    assert claimed["R"]["claims_benefit"] is True and claimed["R"]["expected_effect_pp"] == 2.0
    assert claimed["R"]["variant_cost"]["extra_contacts_per_row"] == 3
    weak = reg.measurement_blocks({"arm": {"run_id": "R", "program": "p"}, "smoke": {"run_id": "S", "program": "p"}}, 1, 1.0, ["typ", "ace", "aa", "lock"], 3.2)
    assert weak["R"]["claims_benefit"] is False and weak["R"]["expected_effect_pp"] == 0.0
    low = tmp_path / "low"
    low.mkdir()
    floor_build(low, declaration=_declaration(measurement_design="same-flight-supply-variant", expected_effect_pp=1.0, rows=1080,
                                              primary_metric_key="slu"), rows=1080, registered_date="2026-10-11")
    assert floor_kinds(floor_gate.evaluate(low)) == ["effect-below-floor"]
    smoke_id, smoke_block = measurement(derived.root, "smoke")
    assert smoke_block["measurement_design"] == "form-proof" and smoke_block["claims_benefit"] is False and smoke_block["rows"] == 4


def _flight_world(tmp_path, derived_root):
    document = baseline(derived_root)
    block = document["native_episode"]["roles"]["solver"]["supply_variants"]
    _, declared = measurement(derived_root)
    world = flight_t.World(tmp_path)
    world.supply_variants = block
    world.measurement = {
        "measurement_design": "same-flight-supply-variant", "expected_effect_pp": 1.5, "claim": "nominated", "aa_arm_id": "aa",
        "tuning_roster": "SLURP-TUNE-POOL-V1", "read_roster": "SLURP-READ-FOLD-A-V1", "variant_cost": declared["variant_cost"]}
    world.write_roster_receipt("SLURP-TUNE-POOL-V1",
                               disjointness_proof={"slurp-read-fold-a-v1": {"shared_recordings": 0, "shared_utterances": 0}})
    world.write_roster_receipt("SLURP-READ-FOLD-A-V1")
    return world


def test_flight_registration_accepts_the_cell_then_owes_only_the_unsigned_refusals(derived, tmp_path):
    world = _flight_world(tmp_path, derived.root)
    data = world.build().run(cells=[flight_t.EXPERIMENT])
    kinds = flight_t._kinds(data)
    assert kinds == [], kinds
    assert data["cells"][0]["supply_variant"]["arm_visits"] == "first"
    world.rows[flight_t.RUN] = flight_t._row(flight_t.RUN, flight_t.DRAFT)
    world.states[flight_t.EXPERIMENT] = "held"
    kinds = flight_t._kinds(world.build().run(cells=[flight_t.EXPERIMENT]))
    assert "row-not-countersigned" in kinds and "not-ready" in kinds
    (world.data / flight_t.RECEIPT).unlink()
    assert "receipt-missing" in flight_t._kinds(world.run(cells=[flight_t.EXPERIMENT]))
    allowed = {"row-not-countersigned", "not-ready", "receipt-missing"}
    assert set(flight_t._kinds(world.run(cells=[flight_t.EXPERIMENT]))) <= allowed | {"receipt-missing"}


def test_the_variant_cost_declaration_matches_the_arm_list(derived, tmp_path):
    world = _flight_world(tmp_path, derived.root)
    world.measurement["variant_cost"] = dict(world.measurement["variant_cost"], extra_contacts_per_row=1)   # K = 3 -> 2 extra
    assert "variant-cost-mismatch" in flight_t._kinds(world.build().run(cells=[flight_t.EXPERIMENT]))


def test_harness_admission_compiles_typed_supply_columns_and_names_the_ace_store_gap():
    receipt = harness_t._committed()
    entry = next(e for e in receipt["entries"] if e["switch"]["table"] == "module")
    switch = copy.deepcopy(entry["switch"])
    fit = dict(tf.FIT_ESTIMATE)
    on = copy.deepcopy(switch["off"])
    on["review_loop"] = "off"
    on["columns"] = [{"column_id": "typ", "kind": "supply", "node": "solver", "max_supplied_items": tf.COLUMN_MAX_SUPPLIED_ITEMS,
                      "overrides": {EX_K: 12}}]
    on["supply_frame"] = {"twin": True, "fit_estimate": fit, "delivering_max_supplied_items": tf.DELIVERING_MAX_SUPPLIED_ITEMS}
    switch["on"] = on
    failures = harness_t.hac._check_module_switch(switch, REPO, "entry", entry.get("status"))
    assert not [f for f in failures if "does not compile" in f], failures
    # the ace column on the entry's OLD lock (v2.1 declares no ace-playbook store) does not compile: named, not hidden
    on = copy.deepcopy(on)
    on["columns"].append({"column_id": "ace", "kind": "supply", "node": "solver", "max_supplied_items": tf.COLUMN_MAX_SUPPLIED_ITEMS,
                          "release_swap": {"store_id": tf.ACE_STORE_ID, "release": "knowledge/slurp/semantic/ace-playbook-i1/release.json"}})
    on["supply_frame"]["alternates"] = {tf.ACE_STORE_ID: [dv.ace_alternate({"iteration": 1})]}
    switch["on"] = on
    failures = harness_t.hac._check_module_switch(switch, REPO, "entry", entry.get("status"))
    assert any("does not compile" in f and "ace-playbook" in f for f in failures), failures


# ---------------------------------------------------------------------------------------------------------------------------
# the package and the DRAFT discipline
# ---------------------------------------------------------------------------------------------------------------------------


def test_the_package_is_draft_held_and_writes_no_ledger_row(derived):
    pkg = derived.root / derived.result["column"]["package"]
    for name in ("README.md", "registered-facts-v1.json", "root-admission-draft-v1.json", "draft-ledger-rows.md"):
        text = (pkg / name).read_text(encoding="utf-8")
        assert "DRAFT" in text, name
    draft = json.loads((pkg / "root-admission-draft-v1.json").read_text(encoding="utf-8"))
    assert draft["status"] == "DRAFT-NOT-MINTED" and draft["recorded_at_utc"] is None
    names = tf.names(1, "arm"), tf.names(1, "smoke")
    assert draft["eligible_run_ids"] == [names[0]["run_id"], names[0]["fit_run_id"], names[1]["run_id"], names[1]["fit_run_id"]]
    plans = sorted(pkg.glob("*plan-registered*.json"))
    assert len(plans) == 4
    for plan in plans:
        document = json.loads(plan.read_text(encoding="utf-8"))
        assert document["status"].startswith("DRAFT-HELD") and document["loop_protocol"]["status"] == "DRAFT-HELD"
    # the registration writes no ledger row: the overlay's ledger copy is byte-identical to the real one (which now carries the countersigned
    # first-attempt column rows, so "the run id is absent" is no longer the invariant)
    assert (derived.root / "docs" / "exposure-ledger.md").read_bytes() == (REPO / "docs" / "exposure-ledger.md").read_bytes()
    rows = (pkg / "draft-ledger-rows.md").read_text(encoding="utf-8")
    assert rows.count("| no |") >= 4 and "consumed" in rows
    # the protocol file itself says DRAFT-HELD and the registration points at it
    protocol = json.loads((REPO / tf.PROTOCOL_RELPATH).read_text(encoding="utf-8"))
    assert protocol["status"] == "DRAFT-HELD"


def test_append_ledger_is_the_coordinators_act_and_defaults_off(tmp_path):
    root = tfrl_overlay.make_overlay(tmp_path / "o", REPO)
    before = (root / "docs" / "exposure-ledger.md").read_text(encoding="utf-8")
    reg.write_iteration(root, 1, spec(), COMMIT, AT)
    assert (root / "docs" / "exposure-ledger.md").read_text(encoding="utf-8") == before
    real_before = (REPO / "docs" / "exposure-ledger.md").read_bytes()
    reg.write_iteration(root, 1, spec(), COMMIT, AT, append_ledger=True)
    after = (root / "docs" / "exposure-ledger.md").read_text(encoding="utf-8")
    assert len(after) > len(before) and "DRAFT -- REGISTERED" in after
    assert (REPO / "docs" / "exposure-ledger.md").read_bytes() == real_before          # the real ledger is never written by a test


# ---------------------------------------------------------------------------------------------------------------------------
# the two text-only cells
# ---------------------------------------------------------------------------------------------------------------------------


def text_only(tmp_path):
    root = tfrl_overlay.make_overlay(tmp_path / "o", REPO)
    dummy = {"relpath": "analysis/x.json", "sha256": "1" * 64}
    from speech_aware_evidence_acquisition.rails import tfrl_typed_proposer as tp

    pins = {"typed": {"tables": dummy, "context": dummy},
            "ace": {"playbook": dummy, "token_cap": 16521, "materials": {s: dummy for s in tp.SCENARIOS}}}
    out = {kind: dv.derive_text_only(1, kind, pins[kind], repo_root=root) for kind in ("typed", "ace")}
    return root, out


def test_the_text_only_cells_compose_on_their_programs_and_carriers(tmp_path):
    root, out = text_only(tmp_path)
    from speech_aware_evidence_acquisition.rails import tfrl_typed_proposer as tp

    for kind, program in (("typed", tp.TFRL_TYPED_PROGRAM_ID), ("ace", tp.TFRL_ACE_PROGRAM_ID)):
        names = tf.names(1, kind)
        experiment = json.loads((root / "configs" / "experiment" / f"{names['experiment']}.json").read_text(encoding="utf-8"))
        cell = experiment["cells"][0]
        composed = compose(root, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], names["experiment"])
        assert composed.values["policy"] == program and composed.values["arm"] == "construction-proposer-text"
        assert default_phase_program(program).max_contacts == 1
        assert experiment["stage3_algorithm"]["id"] == (tf.ALGORITHM_TYPED if kind == "typed" else tf.ALGORITHM_ACE)
        validate_stage3_algorithm_label(experiment["stage3_algorithm"], cell=kind)
        ids = experiment["populations"][0]["ids"]
        carriers = (composed.values["tfrl_proposer"] if kind == "typed" else composed.values["tfrl_ace_reflector"])["carriers"]
        assert sorted(c["sample_id"] for c in carriers) == sorted(ids) and experiment["population"]["count"] == len(ids)
        assert len(ids) == (tf.TYPED_CARRIERS if kind == "typed" else 18)
        receipt = json.loads((root / names["carrier_roster"]).read_text(encoding="utf-8"))
        assert receipt["roster_role"] == "construction" and roster_module.verify_roster(receipt) == experiment["population"]["split_identity_hash"]
        assert experiment["execution_plan"]["planned_model_calls"] == len(ids) * 3
        assert cell["readiness"]["state"] == "held" and len(experiment["cells"]) == 1
        assert "gepa" not in json.dumps(experiment).lower() and "gepa_groups" not in composed.values


def test_the_text_only_cell_blocks_are_read_by_the_runtime_resolver(derived, tmp_path):
    """The fragment blocks the derive writes are exactly what the flight-time resolver reads (pins verified, flown rows = carriers)."""

    from speech_aware_evidence_acquisition.core.flight import runtime as flight_runtime

    sys.path.insert(0, str(REPO / "tests" / "unit"))
    import test_tfrl_loop_driver as drv_t

    world = drv_t.World(tmp_path)
    assert world.run(*drv_t.propose_args(world), fakes=drv_t.Fakes())[0] == 0
    for kind, expected_kind, count in (("typed", "typed", tf.TYPED_CARRIERS), ("ace", "ace", 18)):
        names = tf.names(1, kind)
        experiment = json.loads((world.root / "configs" / "experiment" / f"{names['experiment']}.json").read_text(encoding="utf-8"))
        cell = experiment["cells"][0]
        composed = compose(world.root, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], names["experiment"])
        samples = [SimpleNamespace(sample_id=sid) for sid in experiment["populations"][0]["ids"]]
        material = flight_runtime._default_construction_material(
            composed.values, lock={}, data_root=world.data, repo_root=world.root, samples=samples)
        assert material.kind == expected_kind and len(material.contacts) == count
        for contact in material.contacts:
            assert contact.instruction and "slurp:train" not in contact.instruction


# ---------------------------------------------------------------------------------------------------------------------------
# wrappers and the mint tool
# ---------------------------------------------------------------------------------------------------------------------------


def test_the_family_wrappers_are_lf_valid_shell_and_name_scripts_that_exist():
    import re
    import subprocess

    names = ["tfrl_i1_flip.sh", "tfrl_i1_repin_arm.sh", "tfrl_i1_repin_smoke.sh", "tfrl_i1_repin_typed.sh", "tfrl_i1_repin_ace.sh",
             "batch_chain_tfrl_i1.sh", "tfrl_i1_read.sh"]
    for name in names:
        raw = (TFRL / name).read_bytes()
        assert b"\r" not in raw, f"{name} has CR bytes (shell scripts must be LF)"
        text = raw.decode("utf-8")
        assert text.startswith("#!/bin/bash")
        assert "--allow-output-change" not in text.replace("--allow-output-change must never be passed", "").replace(
            "ALLOW_OUTPUT_CHANGE", ""), name
        if shutil_which("bash"):
            assert subprocess.run(["bash", "-n", str(TFRL / name)], capture_output=True).returncode == 0, name
        for ref in re.findall(r"(?:\$TF|\$SP|\$MAIN/scripts/flights/(?:tfrl|batch))/([A-Za-z0-9_]+\.(?:sh|py))", text):
            assert (TFRL / ref).exists() or (REPO / "scripts" / "flights" / "batch" / ref).exists(), (name, ref)
    flip = (TFRL / "tfrl_i1_flip.sh").read_text(encoding="utf-8")
    assert "convergence pass" in flip and "for pass in 1 2 3 4" in flip and "repin_loop_generic.sh" in flip
    chain = (TFRL / "batch_chain_tfrl_i1.sh").read_text(encoding="utf-8")
    assert "core.flight.cli|batch_driver.sh" in chain and "serving-slurp-native-candidate-five-train-a-np4-v1" in chain


def shutil_which(name: str):
    import shutil

    return shutil.which(name)


def test_the_mint_tool_copies_the_draft_once_and_never_overwrites(derived, tmp_path, monkeypatch, capsys):
    import tfrl_mint_receipt as mint

    monkeypatch.setattr(mint, "ROOT", str(derived.root))
    monkeypatch.setattr(mint, "DATA", str(tmp_path / "data"))
    assert mint.main(["--iteration", "1", "--kind", "column", "--dry"]) == 0
    assert "(dry) would write" in capsys.readouterr().out
    assert mint.main(["--iteration", "1", "--kind", "column"]) == 0
    out = tmp_path / "data" / "coordination" / "slurp-tfrl-loop-i1-v1" / "root-admission-v1.json"
    receipt = json.loads(out.read_text(encoding="utf-8"))
    assert receipt["status"] == "decided" and receipt["decision_id"] == "slurp-tfrl-loop-i1-admission-v1"
    assert len(receipt["eligible_run_ids"]) == 4
    with pytest.raises(SystemExit, match="refusing to overwrite"):
        mint.main(["--iteration", "1", "--kind", "column"])


def test_the_real_cell_gate_on_the_overlay_owes_only_the_pre_flip_refusals(tmp_path):
    """``flight_registration_check --cell`` over the DERIVED cells and the DRAFT ledger rows (appended in the overlay's own ledger copy):
    exactly the refusals an unsigned, unminted, unflipped cell owes -- nothing about its shape, its measurement block, its arm group,
    its variant cost, its rosters or its READ row."""

    root = fresh_ledger_overlay(tmp_path / "o")
    reg.write_iteration(root, 1, spec(), COMMIT, AT, append_ledger=True)
    data = tmp_path / "data"
    data.mkdir()
    owed = {"not-ready", "row-not-countersigned", "receipt-missing", "registered-supply-binding"}
    for kind in ("arm", "smoke"):
        cell = tf.names(1, kind)["experiment"]
        result = flight_gate.evaluate(root, data, root / "docs" / "exposure-ledger.md", cells=[f"{cell}:{cell}"])
        kinds = {f["kind"] for c in result["cells"] for f in c["findings"]}
        assert kinds <= owed, kinds
        assert {"not-ready", "row-not-countersigned", "receipt-missing"} <= kinds
        assert not result["passed"]


# ---------------------------------------------------------------------------------------------------------------------------
# the proposers package: ledger artifacts cell, prompt pins, analysis recipe, scope text (first real flip, 2026-10-11)
# ---------------------------------------------------------------------------------------------------------------------------


def _proposer_pins() -> dict:
    from speech_aware_evidence_acquisition.rails import tfrl_typed_proposer as tp

    dummy = {"relpath": "analysis/x.json", "sha256": "1" * 64}
    return {"typed": {"tables": dummy, "context": dummy},
            "ace": {"playbook": dummy, "token_cap": 16521, "materials": {s: dummy for s in tp.SCENARIOS}}}


def _ledger_rows(text: str) -> dict:
    from speech_aware_evidence_acquisition.contracts.ledger import _parse_ledger_tables

    return {row["run/experiment id"]: row for row in _parse_ledger_tables(text)}


def test_the_proposers_rows_carry_the_plan_path_the_prompt_hash_and_the_construction_scope(tmp_path):
    import hashlib

    root, _ = text_only(tmp_path)
    proposers = reg.proposers_package(root, 1, COMMIT, AT)
    text = reg.draft_text_only_rows(root, 1, proposers["ids"], proposers["shas"], AT,
                                    {"typed": {"tables_sha256": "a" * 64, "archive_sha256": "b" * 64},
                                     "ace": {"tables_sha256": "c" * 64, "archive_sha256": "b" * 64}}, COMMIT)
    rows = _ledger_rows(text)
    pkg = reg.package_names(1)["proposers"]
    for kind, template in (("typed", "typed-proposer-v1.txt"), ("ace", "ace-reflector-v1.txt")):
        row = rows[tf.names(1, kind)["run_id"]]
        plan = f"{pkg}/{kind}-generation-plan-registered-v1.json"
        assert row["artifacts"] == plan and (root / plan).is_file()                      # the gate reads this cell as a repository path
        prompt = hashlib.sha256((REPO / "configs" / "probes" / "tfrl" / template).read_bytes()).hexdigest()
        assert f"prompt sha256 {prompt}" in row["notes"] and "prompt sha256 pending" not in text
        assert f"Plan SHA256 {hashlib.sha256((root / plan).read_bytes()).hexdigest()}" in row["notes"]
        assert "Fold B credit" not in row["scope"] and "construction-source lock column" in row["scope"]
    read = rows[reg.proposers_read_run_id(1)]
    assert read["execution profile"] == "model-free-check" and read["calls"] == "0"
    assert read["artifacts"] == f"{pkg}/analysis-recipe-v1.json" and (root / read["artifacts"]).is_file()


def test_the_proposers_package_carries_an_analysis_recipe_naming_the_driver_step(tmp_path):
    root, _ = text_only(tmp_path)
    proposers = reg.proposers_package(root, 1, COMMIT, AT)
    recipe = json.loads((root / proposers["package"] / "analysis-recipe-v1.json").read_text(encoding="utf-8"))
    assert recipe["read_run_id"] == reg.proposers_read_run_id(1) == recipe["run_ids"]["read"]
    assert "tfrl_loop_driver.py --execute open --iter 1 --stage cell" in recipe["stages"]["1_validate_and_curate"]
    assert recipe["measurement_design"] == "form-proof" and "No benefit" in recipe["claim_boundary"]
    assert set(recipe["contacts"].values()) == {0}
    assert proposers["shas"]["analysis-recipe-v1.json"]


def test_the_real_cell_gate_on_the_proposer_overlay_owes_only_the_pre_flip_refusals(tmp_path):
    """The typed and ACE cells with their DRAFT rows (appended in the overlay's own ledger copy): no ``no-analysis-recipe``, no
    ``read-row-missing``, no unresolvable artifact -- only what an unsigned, unminted, unflipped cell owes."""

    root = tfrl_overlay.make_overlay(tmp_path / "o", REPO)
    # iteration 2: the repository ledger already holds the (countersigned) iteration-1 proposer rows
    result = reg.write_iteration(root, 2, spec(iteration=2), COMMIT, AT, pins=_proposer_pins(), append_ledger=True)
    assert (root / result["proposers"]["package"] / "analysis-recipe-v1.json").is_file()
    data = tmp_path / "data"
    data.mkdir()
    owed = {"not-ready", "row-not-countersigned", "receipt-missing", "registered-supply-binding", "no-decision-receipt"}
    for kind in ("typed", "ace"):
        cell = tf.names(2, kind)["experiment"]
        out = flight_gate.evaluate(root, data, root / "docs" / "exposure-ledger.md", cells=[f"{cell}:{cell}"])
        kinds = {f["kind"] for c in out["cells"] for f in c["findings"]}
        assert "no-analysis-recipe" not in kinds and "read-row-missing" not in kinds, kinds
        assert kinds <= owed, kinds
        assert {"not-ready", "row-not-countersigned"} <= kinds


# ---------------------------------------------------------------------------------------------------------------------------
# the smoke's single recovery (rec1, 2026-10-11): refused at preflight on the ACE snapshot pin, re-flown whole under rec1 attempt ids
# ---------------------------------------------------------------------------------------------------------------------------

REC = "-rec1"
PKG1 = reg.package_names(1)["column"]


def _load(root: Path, relpath: str) -> dict:
    return json.loads((root / relpath).read_text(encoding="utf-8"))


def _header() -> str:
    return "| " + " | ".join(reg.LEDGER_COLUMNS) + " |\n| " + " | ".join("---" for _ in reg.LEDGER_COLUMNS) + " |\n"


def test_rec1_attempt_ids_are_on_the_iteration_one_smoke_only():
    smoke, arm = tf.names(1, "smoke"), tf.names(1, "arm")
    assert smoke["attempt_id"] == "attempt-slurp-native-stage3-tfrl-loop-i1-fold-b-smoke-4-generation-rec1-v1"
    assert smoke["fit_attempt_id"] == "attempt-slurp-native-stage3-tfrl-loop-i1-fold-b-smoke-4-fit-rec1-v1"
    # a (run id, attempt id) pair is a one-time key: the run ids do NOT change, the arm keeps its first-attempt ids
    assert smoke["run_id"] == "SAEA-SLURP-STAGE3-TFRL-LOOP-I1-FOLD-B-SMOKE-4-V1" and smoke["fit_run_id"].endswith("SMOKE-4-FIT-V1")
    assert arm["attempt_id"].endswith("fold-b-generation-v1") and arm["fit_attempt_id"].endswith("fold-b-fit-v1")
    assert REC not in json.dumps(arm)
    for iteration in (2, 3):                                  # no other iteration has a recovery
        assert REC not in json.dumps(tf.names(iteration, "smoke")) and tf.smoke_recovery(iteration) is None
    for kind in ("typed", "ace"):
        assert REC not in json.dumps(tf.names(1, kind))
    assert tf.smoke_rec_suffix(1) == REC and tf.smoke_rec_suffix(2) == ""
    rec = tf.smoke_recovery(1)
    assert rec["recovery_index"] == 1 and rec["predecessor_attempt_id"].endswith("smoke-4-generation-v1")
    assert tf.smoke_predecessor_spend(1) == (0, 0.0)
    assert tf.smoke_cumulative_budget(1, 16, 41) == (16, 41) and tf.smoke_cumulative_budget(2, 16, 41) == (16, 41)
    assert tf.plan_file_name(1, "smoke", "generation") == "smoke-generation-plan-registered-rec1-v1.json"
    assert tf.plan_file_name(1, "smoke", "fit") == "smoke-fit-plan-registered-rec1-v1.json"
    assert tf.plan_file_name(1, "arm", "generation") == "generation-plan-registered-v1.json"
    assert tf.plan_file_name(2, "smoke", "generation") == "smoke-generation-plan-registered-v1.json"


def test_the_cumulative_budget_adds_the_failed_spend_and_rounds_the_audio_up(monkeypatch):
    patched = copy.deepcopy(tf.SMOKE_RECOVERIES[1])
    patched["predecessors"] = [{"attempt_id": "x", "contacts_spent": 7, "speech_seconds_spent": 12.25}]
    monkeypatch.setitem(tf.SMOKE_RECOVERIES, 1, patched)
    assert tf.smoke_predecessor_spend(1) == (7, 12.25)
    assert tf.smoke_cumulative_budget(1, 16, 41) == (23, 54)                 # 41 + 12.25 = 53.25 -> 54


def test_the_fragments_carry_rec1_on_the_smoke_and_leave_the_arm_untouched(derived):
    smoke_exp = _load(derived.root, f"configs/experiment/{tf.names(1, 'smoke')['experiment']}.json")
    smoke_base = baseline(derived.root, kind="smoke")
    assert smoke_exp["cells"][0]["attempt_id"] == tf.names(1, "smoke")["attempt_id"]
    assert smoke_base["native_contact_fit"]["attempt_id"] == tf.names(1, "smoke")["fit_attempt_id"]
    assert "single root-diagnosed recovery" in smoke_exp["failure_policy"] and "rec1" in smoke_exp["failure_policy"]
    arm_exp = _load(derived.root, f"configs/experiment/{tf.names(1, 'arm')['experiment']}.json")
    arm_base = baseline(derived.root)
    assert arm_exp["cells"][0]["attempt_id"] == tf.names(1, "arm")["attempt_id"]
    assert REC not in json.dumps(arm_exp) and REC not in json.dumps(arm_base)
    # the structural FIT cap is NOT scaled by the recovery
    assert smoke_base["native_contact_fit"]["contact_cap"] == 4 * 4 * 4
    assert smoke_exp["family_budget"]["fit_endpoint_calls_cap"] == 64


def test_the_recovery_plans_carry_the_original_plan_the_failed_spend_and_the_root_cause(derived):
    pkg = derived.root / PKG1
    names = sorted(p.name for p in pkg.glob("*plan-registered*.json"))
    assert names == ["fit-plan-registered-v1.json", "generation-plan-registered-v1.json",
                     "smoke-fit-plan-registered-rec1-v1.json", "smoke-generation-plan-registered-rec1-v1.json"]
    assert not (pkg / "smoke-generation-plan-registered-v1.json").exists() and not (pkg / "smoke-fit-plan-registered-v1.json").exists()
    smoke = tf.names(1, "smoke")
    gen = _load(derived.root, f"{PKG1}/smoke-generation-plan-registered-rec1-v1.json")
    fit = _load(derived.root, f"{PKG1}/smoke-fit-plan-registered-rec1-v1.json")
    assert gen["execution_plan"]["attempt_id"] == smoke["attempt_id"] and fit["execution_plan"]["attempt_id"] == smoke["fit_attempt_id"]
    assert gen["execution_plan"]["run_id"] == smoke["run_id"] and fit["execution_plan"]["run_id"] == smoke["fit_run_id"]
    for plan in (gen, fit):
        recovery = plan["execution_plan"]["recovery"]
        assert recovery == tf.smoke_recovery(1)
        assert recovery["predecessors"] == [{"attempt_id": recovery["predecessor_attempt_id"], "contacts_spent": 0,
                                             "speech_seconds_spent": 0.0, "state": "OPENED, refused at preflight before any contact"}]
        assert "ACE snapshot pin was the file hash; corrected to the preparer's content hash" in recovery["root_cause"]
        assert "snapshot SHA-256 mismatch" in recovery["reason"]
    budget = gen["recovery_budget"]
    assert budget["failed_attempt_spend"]["model_calls"] == 0 and budget["failed_attempt_spend"]["speech_audio_seconds"] == 0.0
    assert budget["original_plan"] == budget["cumulative_plan"] and budget["original_plan"]["planned_model_calls"] == 16
    assert gen["execution_plan"]["planned_model_calls"] == 16
    assert fit["execution_plan"]["planned_model_calls"] == 64                                # structural, never scaled
    arm_gen = _load(derived.root, f"{PKG1}/generation-plan-registered-v1.json")
    assert "recovery" not in arm_gen["execution_plan"] and "recovery_budget" not in arm_gen
    assert arm_gen["execution_plan"]["attempt_id"] == tf.names(1, "arm")["attempt_id"]


def test_the_package_documents_name_the_recovery_and_the_decision_draft_extends_the_eligible_attempt_ids(derived):
    smoke, arm = tf.names(1, "smoke"), tf.names(1, "arm")
    draft = _load(derived.root, f"{PKG1}/root-admission-draft-v1.json")
    assert draft["eligible_run_ids"] == [arm["run_id"], arm["fit_run_id"], smoke["run_id"], smoke["fit_run_id"]]    # the run ids did not change
    assert draft["eligible_attempt_ids"] == [arm["attempt_id"], arm["fit_attempt_id"], smoke["attempt_id"], smoke["fit_attempt_id"]]
    assert draft["superseded_attempt_ids"] == [tf.smoke_recovery(1)["predecessor_attempt_id"], tf.smoke_recovery(1)["predecessor_fit_attempt_id"]]
    protocol = _load(derived.root, f"{PKG1}/protocol-registered-v1.json")
    assert protocol["recovery"] == {"smoke": tf.smoke_recovery(1)}
    assert protocol["cells"]["smoke"]["attempt_id"] == smoke["attempt_id"] and protocol["cells"]["arm"]["attempt_id"] == arm["attempt_id"]
    facts = _load(derived.root, f"{PKG1}/registered-facts-v1.json")
    assert facts["recovery"]["smoke"] == tf.smoke_recovery(1) and facts["identity"]["smoke"]["attempt_id"] == smoke["attempt_id"]
    assert facts["recovery"]["smoke_plans"] == ["smoke-generation-plan-registered-rec1-v1.json", "smoke-fit-plan-registered-rec1-v1.json"]
    for text in ((derived.root / PKG1 / "README.md").read_text(encoding="utf-8"),
                 (derived.root / reg.package_names(1)["prereg"]).read_text(encoding="utf-8")):
        assert "Smoke recovery" in text and smoke["attempt_id"] in text and "ACE snapshot pin was the file hash" in text


def test_a_second_run_reproduces_the_package_byte_for_byte_and_never_resurrects_the_first_attempt_plans(tmp_path):
    """``open --stage cell`` re-runs the writer: an existing recovery must not be clobbered (every recovery artefact derives from the family)."""

    root = tfrl_overlay.make_overlay(tmp_path / "o", REPO)
    reg.write_iteration(root, 1, spec(), COMMIT, AT)
    first = {p.name: p.read_bytes() for p in (root / PKG1).iterdir()}
    stale = root / PKG1 / "smoke-generation-plan-registered-v1.json"
    stale.write_text("{}", encoding="utf-8")                                  # a first-attempt plan that reappears is removed again
    reg.write_iteration(root, 1, spec(), COMMIT, AT)
    second = {p.name: p.read_bytes() for p in (root / PKG1).iterdir()}
    assert second == first and not stale.exists()
    assert "smoke-generation-plan-registered-rec1-v1.json" in second


def test_the_queue_step_flies_the_smoke_under_rec1_and_the_arm_under_its_first_attempt():
    import tfrl_i1_queue as queue

    def facts_loader(relpath):
        return json.loads((REPO / relpath).read_text(encoding="utf-8"))

    (step,) = queue.build_steps(1, "column", "tfrl-i1", facts_loader)
    assert step["smoke_attempt_id"] == tf.names(1, "smoke")["attempt_id"] and step["smoke_attempt_id"].endswith("generation-rec1-v1")
    assert step["gen_attempt_id"] == tf.names(1, "arm")["attempt_id"] and REC not in step["gen_attempt_id"]
    assert step["smoke_run_id"] == tf.names(1, "smoke")["run_id"] and step["run_id"] == tf.names(1, "arm")["run_id"]
    assert step["fit_run_id"] == tf.names(1, "arm")["fit_run_id"]
    for proposer in queue.build_steps(1, "proposers", "tfrl-i1", facts_loader):          # the text-only cells carry no smoke
        assert proposer["smoke_attempt_id"] is None


def test_the_flip_and_repin_wrappers_carry_the_rec1_plan_marker():
    flip = (TFRL / "tfrl_i1_flip.sh").read_text(encoding="utf-8")
    assert "tf.smoke_rec_suffix($ITER)" in flip
    assert 'PLAN_REC="$SMOKE_REC" bash "$SP/repin_loop_generic.sh" "$TF/tfrl_i1_repin_smoke.sh"' in flip
    assert 'PLAN_REC="$SMOKE_REC" bash "$SP/repin_loop_generic.sh" "$TF/tfrl_i1_repin_arm.sh"' not in flip     # the arm has no recovery
    generic = (REPO / "scripts" / "flights" / "batch" / "repin_loop_generic.sh").read_bytes()
    assert b"\r" not in generic
    # the generic default (no PLAN_REC) is the historical file name, so every other family is unchanged
    assert b'os.environ.get("PLAN_REC", "")' in generic and b"{plan}-plan-registered{rec}-v1.json" in generic


def test_the_recovery_ledger_rows_are_appended_beside_the_column_rows_idempotently_and_unedited(tmp_path):
    root = tfrl_overlay.make_overlay(tmp_path / "o", REPO)
    ledger = root / "docs" / "exposure-ledger.md"
    smoke = tf.names(1, "smoke")
    base = "\n".join(line for line in ledger.read_text(encoding="utf-8").split("\n")
                     if not (line.startswith("| ") and smoke["attempt_id"] in line))          # the ledger as it stood before the rec1 rows
    ledger.write_text(base, encoding="utf-8", newline="\n")
    assert reg.write_iteration(root, 1, spec(), COMMIT, AT, append_recovery_ledger=True)["recovery_ledger_appended"] is True
    after = ledger.read_text(encoding="utf-8")
    added = [line for line in after.split("\n") if line.startswith("| ") and smoke["attempt_id"] in line]
    assert len(added) == 2
    # removing exactly the two added lines gives the old ledger back: nothing else was edited, and the rows sit inside the column block
    assert "\n".join(line for line in after.split("\n") if line not in added) == base
    assert after.split("\n").index(added[0]) > max(k for k, line in enumerate(after.split("\n")) if f"{PKG1}/analysis-recipe-v1.json" in line) - 1
    assert reg.write_iteration(root, 1, spec(), COMMIT, AT, append_recovery_ledger=True)["recovery_ledger_appended"] is False
    assert ledger.read_text(encoding="utf-8") == after


def test_the_recovery_rows_name_the_failed_attempt_the_cause_and_the_rec1_ids(derived):
    import hashlib

    ids = reg.identities(derived.root, 1, ("arm", "smoke"))
    shas = derived.result["column"]["shas"]
    text = reg.recovery_ledger_rows(ids, COMMIT, AT, ["ace", "aa", "lock"], PKG1, shas)
    rows = _ledger_rows(_header() + text)
    smoke = ids["smoke"]
    assert set(rows) == {smoke["run_id"], smoke["fit_run_id"]}
    gen, fit = rows[smoke["run_id"]], rows[smoke["fit_run_id"]]
    for row in (gen, fit):
        assert row["consumed"] == "no" and row["scope"].startswith("DRAFT") and "SMOKE RECOVERY rec1" in row["scope"]
        assert "RECOVERY RE-REGISTRATION" in row["notes"] and "ACE snapshot pin was the file hash" in row["notes"]
        assert smoke["attempt_id"] in row["notes"] and smoke["fit_attempt_id"] in row["notes"]
        assert "SUPERSEDES the first-attempt row of the same run id" in row["notes"]
    assert gen["calls"] == "16" and fit["calls"] == "64"
    assert gen["artifacts"] == f"{PKG1}/smoke-generation-plan-registered-rec1-v1.json" and (derived.root / gen["artifacts"]).is_file()
    assert fit["artifacts"] == f"{PKG1}/smoke-fit-plan-registered-rec1-v1.json"
    assert f"Plan SHA256 {hashlib.sha256((derived.root / gen['artifacts']).read_bytes()).hexdigest()}" in gen["notes"]
    # draft-ledger-rows.md carries the same two rows beside the arm rows and the READ row; the arm rows carry no recovery text
    package_rows = _ledger_rows((derived.root / PKG1 / "draft-ledger-rows.md").read_text(encoding="utf-8"))
    assert len(package_rows) == 5
    assert "RECOVERY RE-REGISTRATION" in package_rows[smoke["run_id"]]["notes"]
    assert "RECOVERY RE-REGISTRATION" not in package_rows[ids["arm"]["run_id"]]["notes"]
    assert "smoke-generation-plan-registered-rec1-v1.json" in package_rows[smoke["run_id"]]["artifacts"]


def test_the_gate_on_an_overlay_with_the_rec1_rows_reports_only_the_owed_refusals(tmp_path):
    """Overlay = this tree: the countersigned first-attempt column rows PLUS the two DRAFT rec1 rows. Only the refusals an unflipped,
    receipt-less sandbox owes may appear; the smoke additionally owes ``duplicate-row`` for as long as the ledger carries two rows for
    one of its run ids (a run id carries exactly one row at launch: the coordinator folds the first-attempt rows into the rec1 ones when
    countersigning)."""

    root = tfrl_overlay.make_overlay(tmp_path / "o", REPO)
    data = tmp_path / "data"
    data.mkdir()
    ledger = root / "docs" / "exposure-ledger.md"
    text = ledger.read_text(encoding="utf-8")
    owed = {"not-ready", "receipt-missing", "no-decision-receipt", "registered-supply-binding", "row-not-countersigned"}
    for kind in ("arm", "smoke"):
        names = tf.names(1, kind)
        duplicated = any(text.count(f"| {run_id} | ") > 1 for run_id in (names["run_id"], names["fit_run_id"]))
        cell = names["experiment"]
        result = flight_gate.evaluate(root, data, ledger, cells=[f"{cell}:{cell}"])
        kinds = {f["kind"] for c in result["cells"] for f in c["findings"]}
        assert kinds <= owed | ({"duplicate-row"} if duplicated else set()), kinds
        assert ("duplicate-row" in kinds) == duplicated
        assert not result["passed"]
    assert not any(text.count(f"| {run_id} | ") > 1 for run_id in (tf.names(1, "arm")["run_id"], tf.names(1, "arm")["fit_run_id"]))


def test_the_gate_on_a_fresh_overlay_with_only_the_rec1_rows_owes_the_unsigned_refusals(tmp_path):
    """The pre-countersign state: no first-attempt rows, only the DRAFT rows (the writer's own append)."""

    root = fresh_ledger_overlay(tmp_path / "o")
    reg.write_iteration(root, 1, spec(), COMMIT, AT, append_ledger=True)
    data = tmp_path / "data"
    data.mkdir()
    cell = tf.names(1, "smoke")["experiment"]
    result = flight_gate.evaluate(root, data, root / "docs" / "exposure-ledger.md", cells=[f"{cell}:{cell}"])
    kinds = {f["kind"] for c in result["cells"] for f in c["findings"]}
    assert kinds <= {"not-ready", "row-not-countersigned", "receipt-missing", "registered-supply-binding"}, kinds
    assert "duplicate-row" not in kinds and "missing-row" not in kinds


def test_the_close_step_reads_only_the_arm_flight_so_a_rec1_smoke_cannot_confuse_it():
    """``close --iter t`` scores the ARM run's sealed attempt; it never opens the smoke run, so a smoke that flew under rec1 attempt ids is
    invisible to it. ``open --stage cell`` only re-runs the writer, which is reproducible byte for byte (see the idempotence test above)."""

    import re

    source = (TFRL / "tfrl_loop_driver.py").read_text(encoding="utf-8")
    assert not re.search(r"names\([^)]*['\"]smoke['\"]", source) and "smoke-4" not in source and "smoke_attempt" not in source
    assert 'names = tf.names(t, "arm")' in source and 'run, attempt = names["run_id"], names["attempt_id"]' in source
    assert tf.names(1, "arm")["attempt_id"] == "attempt-slurp-native-stage3-tfrl-loop-i1-fold-b-generation-v1"
