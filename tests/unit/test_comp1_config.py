"""Cell COMP-1 -- the first composed Stage-3 arm -- is the locked PLAN plan with
exactly three registered factors composed (the agreement term as AGREE, the
centroid key as KPROBE, the citation contract), its in-chain A/A the locked plan's
own bytes, and nothing else.

Config only: no data root, no lock, no adapter, no contact. Every assertion here is
a property a reader of the registration should be able to take for granted, and
each one is a defect this registration could plausibly have shipped.
"""

from __future__ import annotations

import io
import json
import re
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
from speech_aware_evidence_acquisition.core.stage3_algorithms import validate_stage3_algorithm_label

REPO = Path(__file__).resolve().parents[2]

ARM = "slurp-native-stage3-comp1-fold-a-v1"
AA = "slurp-native-stage3-comp1-aa-fold-a-v1"
SMOKE = "slurp-native-stage3-comp1-fold-a-smoke-4-v1"
PARENT = "slurp-native-default-plan-lock-v1"
PARENT_SMOKE = "slurp-native-default-plan-lock-smoke-4-v1"
RUNS = {
    ARM: ("SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1", "SAEA-SLURP-STAGE3-COMP1-FOLD-A-FIT-V1"),
    AA: ("SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1", "SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-FIT-V1"),
    SMOKE: ("SAEA-SLURP-STAGE3-COMP1-FOLD-A-SMOKE-4-V1", "SAEA-SLURP-STAGE3-COMP1-FOLD-A-SMOKE-4-FIT-V1"),
}
PACKAGE = REPO / "docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1"
PREREG = REPO / "docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1-preregistration.md"
PLACEHOLDER = "TO-BE-DECLARED-BY-COORDINATOR-FROM-AGREE-AND-KPROBE-READS"
PLAN_SUPPLY_OUTPUT_SHA = "ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f"
CLASSES_ROW = "SAEA-SLURP-STAGE3-COMP1-ATTRIBUTION-CLASSES-V1"

BOUNDARY = "knowledge_stores.intent-boundaries.phase_supply.perception"
FACTOR_1 = (f"{BOUNDARY}.rank_weights.w_agree", f"{BOUNDARY}.agreement_source.")
FACTOR_2 = (f"{BOUNDARY}.facet_source.",)
FACTOR_3 = ("policy", "phase_material.solver.instruction_template", "phase_material.solver.response_format_id", "native_episode.deliver_normaliser.normaliser")
RECALL = f"{BOUNDARY}.k"
BOOKKEEPING = ("native_contact_fit.", "prepared_phase_supply", "preparation_source_receipts", "what_this_is")


DECISION_ID = "slurp-stage3-comp1-fold-a-admission-v1"


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _is_own_supply(relpath: str, run_id: str) -> bool:
    """This cell's own first-phase supply: phase-supply-v1.json as registered (3667e01d); the flips (b7cbfe69,
    dc63fe64, bf483458) re-pinned the same bytes as phase-supply-v2.json through scripts/flights/repin_cell.py."""

    return re.fullmatch(rf"prepared/{re.escape(run_id)}/phase-supply-v\d+\.json", relpath) is not None


def _own_supply(cell: dict) -> dict:
    own = [r for r in cell["readiness"]["requirements"] if _is_own_supply(r["relpath"], cell["run_id"])]
    assert len(own) == 1, cell["readiness"]["requirements"]
    return own[0]


def _declared(value) -> bool:
    """True once the coordinator replaced the placeholder with a number (43027f59: 3.23 pp)."""

    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _flatten(node, prefix: str = "") -> dict:
    out = {}
    if isinstance(node, dict):
        for key, value in node.items():
            out.update(_flatten(value, f"{prefix}{key}."))
    else:
        out[prefix[:-1]] = node
    return out


def _composed(experiment: str):
    document = _read(REPO / "configs/experiment" / f"{experiment}.json")
    cell = document["cells"][0]
    return document, cell, compose(REPO, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], experiment)


def _matches(key: str, path: str) -> bool:
    return key == path or (path.endswith(".") and key.startswith(path))


def _diff(parent_values, mine, experiment_keys, baseline_keys, allowed):
    assert not (experiment_keys & baseline_keys), "the experiment fragment overrides a baseline key"
    a, b = _flatten(parent_values), _flatten(mine)
    changed = sorted(k for k in set(a) | set(b) if a.get(k, "<absent>") != b.get(k, "<absent>"))
    factor = [k for k in changed if any(_matches(k, p) for p in allowed)]
    bookkeeping = [k for k in changed if k not in factor and k.startswith(BOOKKEEPING)]
    experiment_block = [k for k in changed if k not in factor and k not in bookkeeping and k.split(".", 1)[0] in experiment_keys]
    other = [k for k in changed if k not in factor and k not in bookkeeping and k not in experiment_block]
    return factor, bookkeeping, experiment_block, other


@pytest.fixture(scope="module")
def cells():
    return {name: _composed(name) for name in (ARM, AA, SMOKE)}


@pytest.fixture(scope="module")
def parents():
    return {PARENT: _composed(PARENT), PARENT_SMOKE: _composed(PARENT_SMOKE)}


@pytest.fixture(scope="module")
def baseline_keys(parents):
    _doc, cell, _c = parents[PARENT]
    return set(_read(REPO / "configs/baseline" / (cell["baseline_fragment"] + ".json")))


@pytest.fixture(scope="module")
def facts():
    return _read(PACKAGE / "registered-facts-v1.json")


def test_the_arm_differs_from_the_locked_plan_by_the_three_factors_the_recall_width_and_bookkeeping(cells, parents, baseline_keys):
    doc, _cell, composed = cells[ARM]
    pdoc, _pcell, parent = parents[PARENT]
    factor, _bk, _exp, other = _diff(parent.values, composed.values, set(doc) | set(pdoc), baseline_keys, FACTOR_1 + FACTOR_2 + FACTOR_3 + (RECALL,))
    assert other == [], other
    for path in FACTOR_1 + FACTOR_2 + FACTOR_3 + (RECALL,):
        assert any(_matches(k, path) for k in factor), path


def test_the_aa_differs_from_the_locked_plan_by_the_recall_width_and_bookkeeping_only(cells, parents, baseline_keys):
    doc, _cell, composed = cells[AA]
    pdoc, _pcell, parent = parents[PARENT]
    factor, _bk, _exp, other = _diff(parent.values, composed.values, set(doc) | set(pdoc), baseline_keys, (RECALL,))
    assert other == [], other
    assert factor == [RECALL]
    mine = composed.values["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
    assert mine["k"] == 60 and mine["rank_weights"] == {"w_agree": 0.0, "w_cos": 1.0, "w_prior": 0.0}
    assert "agreement_source" not in mine
    assert mine["facet_source"] == parent.values["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]["facet_source"]
    assert composed.values["policy"] == parent.values["policy"] == "phase-native-candidates-review-revise-v1"
    assert composed.values["phase_material"]["solver"] == parent.values["phase_material"]["solver"]
    assert composed.values["native_episode"]["deliver_normaliser"] == {"normaliser": "saea-deliver-normalise-v3"}


def test_the_arm_differs_from_the_aa_by_the_three_factors_alone(cells, baseline_keys):
    adoc, _acell, arm = cells[ARM]
    bdoc, _bcell, aa = cells[AA]
    factor, _bk, _exp, other = _diff(aa.values, arm.values, set(adoc) | set(bdoc), baseline_keys, FACTOR_1 + FACTOR_2 + FACTOR_3)
    assert other == [], other
    assert RECALL not in factor
    for path in FACTOR_1 + FACTOR_2 + FACTOR_3:
        assert any(_matches(k, path) for k in factor), path


def test_the_smoke_is_the_arm_form_on_the_plan_smoke(cells, parents, baseline_keys):
    doc, _cell, composed = cells[SMOKE]
    pdoc, _pcell, parent = parents[PARENT_SMOKE]
    factor, _bk, _exp, other = _diff(parent.values, composed.values, set(doc) | set(pdoc), baseline_keys, FACTOR_1 + FACTOR_2 + FACTOR_3 + (RECALL,))
    assert other == [], other
    adoc, _acell, arm = cells[ARM]
    for path in ("policy", "phase_material", "native_episode", "knowledge_stores"):
        assert composed.values[path] == arm.values[path]


def test_factor_one_is_the_agree_arm_s_term_byte_for_byte(cells):
    _doc, _cell, arm = cells[ARM]
    mine = arm.values["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
    agree = _read(REPO / "configs/baseline/slurp-native-stage3-agree-w1-fold-a-baseline-v1.json")["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
    assert mine["agreement_source"] == agree["agreement_source"]
    assert mine["rank_weights"] == agree["rank_weights"] == {"w_agree": 1.0, "w_cos": 1.0, "w_prior": 0.0}
    assert mine["k"] == agree["k"] == 60
    assert mine["fuse_coverage"] == agree["fuse_coverage"] == {"m": 8, "c": 1, "top_l": 8}
    assert mine["tau"] == 0.0


def test_factor_two_is_kprobe_s_centroid_pin_byte_for_byte(cells):
    _doc, _cell, arm = cells[ARM]
    mine = arm.values["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
    kprobe = _read(REPO / "configs/baseline/slurp-native-stage3-kprobe-fold-a-55-baseline-v1.json")
    assert mine["facet_source"] == kprobe["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]["facet_source"]
    assert mine["facet_source"]["relpath"] == "prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/facets.jsonl"
    assert mine["facet_source"]["sha256"] == "16c33640151cff6428bc50e4f00ced93b35f76fa186b8d08fcefdfdb33fd5532"


def test_factor_three_is_the_citation_contract_as_one_arming(cells):
    _doc, _cell, arm = cells[ARM]
    assert arm.values["policy"] == "phase-native-candidates-review-revise-cited-v1"
    solver = arm.values["phase_material"]["solver"]
    assert solver["response_format_id"] == "saea-solver-cited-answer-v1"
    assert solver["instruction_template"] == "probes/slurp_native_role_solver_cited_v1.txt"
    assert arm.values["native_episode"]["deliver_normaliser"] == {"normaliser": "saea-deliver-cited-answer-normalise-v3-v1"}
    program = _read(REPO / "configs/policy/phase-native-candidates-review-revise-cited-v1.json")
    assert next(p for p in program["phases"] if p["name"] == "solver")["response_format_id"] == "saea-solver-cited-answer-v1"
    assert (REPO / "configs" / solver["instruction_template"]).is_file()
    for phase in ("perception", "reviewer", "planner"):
        assert arm.values["phase_material"][phase] == cells[AA][2].values["phase_material"][phase]


def test_the_receipts_are_the_parent_s_plus_the_two_factor_receipts(cells, parents):
    _doc, _cell, arm = cells[ARM]
    _pdoc, _pcell, parent = parents[PARENT]
    mine = {r["relpath"]: r for r in arm.values["preparation_source_receipts"]}
    theirs = {r["relpath"]: r for r in parent.values["preparation_source_receipts"]}
    assert all(mine[k] == v for k, v in theirs.items())
    assert sorted(set(mine) - set(theirs)) == [
        "prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/receipt.json",
        "prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-A-V1/receipt.json",
    ]
    for store in ("intent-boundaries", "train-exemplars", "slot-contracts"):
        for pin in ("snapshot", "release"):
            assert arm.values["knowledge_stores"][store][pin] == parent.values["knowledge_stores"][store][pin]
    assert arm.values["scorers"] == parent.values["scorers"]
    assert arm.values["arm"] == parent.values["arm"]


def test_no_prepared_phase_supply_is_committed_and_each_cell_pins_its_own(cells):
    for name, (doc, cell, composed) in cells.items():
        run_id, fit_run = RUNS[name]
        # nothing committed as registered; after the flip the baseline pins this cell's OWN supply, never a foreign one
        supply = composed.values.get("prepared_phase_supply")
        assert supply is None or _is_own_supply(supply["relpath"], run_id), supply
        assert cell["run_id"] == run_id
        assert composed.values["native_contact_fit"]["run_id"] == fit_run
        readiness = cell["readiness"]
        assert readiness["state"] in ("held", "ready")
        own = _own_supply(cell)
        assert own["kind"] == "preparation"
        assert own["sha256"] != "0" * 64 and len(own["sha256"]) == 64
        if supply is not None:
            assert supply == {"relpath": own["relpath"], "sha256": own["sha256"]}
        table = [r for r in readiness["requirements"] if r["relpath"].endswith("agreement.jsonl")]
        assert len(table) == (0 if name == AA else 1)
        decisions = [r for r in readiness["requirements"] if r["kind"] == "decision"]
        if readiness["state"] == "held":
            assert not decisions
        else:
            assert [r["expected_decision_id"] for r in decisions] == [DECISION_ID]
        assert "--allow-output-change must never be passed" in readiness["reason"]


def test_the_caps_are_the_plan_family_s_own(cells):
    for name, (doc, _cell, composed) in cells.items():
        caps = doc["family_budget"]
        rows = doc["population"]["count"]
        assert rows == (4 if name == SMOKE else 1080)
        assert caps["generation_calls_cap"] == rows * 11
        assert caps["fit_endpoint_calls_cap"] == 4 * rows * 11
        assert caps["native_task_contract_calls_cap"] == rows * 6
        assert composed.values["native_contact_fit"]["contact_cap"] == caps["fit_endpoint_calls_cap"]
        assert doc["execution_plan"]["planned_model_calls"] == caps["generation_calls_cap"]
        assert doc["execution_profile"] == "bounded-discovery-probe"
        assert doc["execution_plan"]["split_role"] == "discovery"
        episode = composed.values["native_episode"]
        assert episode["finite_completion_policy"] == "deliver-latest-or-abstain"
        assert episode["react_exhaustion_policy"] == "continue-without-answer"


def test_the_measurement_declaration_leaves_the_arm_s_expectation_to_the_coordinator(facts):
    block = facts["stage3_measurement"]
    arm, aa, smoke = (block[RUNS[n][0]] for n in (ARM, AA, SMOKE))
    # The placeholder as registered (3667e01d); the coordinator's number since 43027f59 (3.23 pp, owner decisions
    # 139, 152, 161), with the token then retired from every prose field (234f7dde: the minter refuses on any
    # occurrence).
    declared = _declared(arm["expected_effect_pp"])
    if declared:
        assert arm["expected_effect_declaration"]
        assert PLACEHOLDER not in json.dumps(facts)
    else:
        assert arm["expected_effect_pp"] == PLACEHOLDER
    assert arm["claims_benefit"] is True
    assert arm["measurement_design"] == "cross-flight-with-in-chain-replicate"
    assert arm["replicate_run_id"] == RUNS[AA][0]
    assert arm["rows"] == 1080 and "intent" in arm["primary_metric"]
    assert aa["expected_effect_pp"] == 0.0 and aa["claims_benefit"] is False and aa["replicate_run_id"] == RUNS[ARM][0]
    assert smoke["measurement_design"] == "form-proof" and smoke["claims_benefit"] is False and smoke["rows"] == 4
    fill = facts["the_expectation_the_coordinator_declares"]["where_to_fill"]
    assert len(fill) == 2
    if not declared:
        assert all(entry["currently"] == PLACEHOLDER for entry in fill)


def test_the_preregistration_fence_repeats_the_canonical_block(facts):
    text = PREREG.read_text(encoding="utf-8")
    start = text.index("```json")
    fenced = json.loads(text[text.index("\n", start) + 1 : text.index("```", start + 7)])
    assert fenced["stage3_measurement"] == facts["stage3_measurement"]
    declared = _declared(facts["stage3_measurement"][RUNS[ARM][0]]["expected_effect_pp"])
    assert (PLACEHOLDER not in text) if declared else (PLACEHOLDER in text)


def test_the_stage3_labels_resolve_and_say_what_the_cells_are(cells):
    for name, (doc, _cell, _composed) in cells.items():
        record, used = validate_stage3_algorithm_label(doc["stage3_algorithm"], cell=name)
        if name == AA:
            assert record.id == "none" and used == ()
        else:
            assert record.id == "sealed-credit-system-policy-v1"
            assert used == ("context_application",)
            note = doc["stage3_algorithm"]["note"]
            assert ("step (iv)" in note and "re-execution" in note) if name == ARM else "form smoke" in note


def test_the_campaign_plan_flies_the_aa_then_the_arm_in_one_chain(cells):
    plan = _read(REPO / "configs/campaign/slurp-native-stage3-comp1-fold-a-v1.json")
    assert plan["schema"] == "saea-campaign-plan-v1"
    assert plan["cells"] == [{"cell": AA, "experiment": AA}, {"cell": ARM, "experiment": ARM}]
    for name in (ARM, AA):
        assert "campaign" in cells[name][1]["allowed_execution_stages"]
    assert "campaign" not in cells[SMOKE][1]["allowed_execution_stages"]


def test_the_plan_documents_carry_the_recomposed_hashes(cells):
    for name, prefix in ((ARM, ""), (AA, "aa-"), (SMOKE, "smoke-")):
        doc, cell, composed = cells[name]
        split = doc["population"]["split_identity_hash"]
        expected = protocol_hash(composed.config_hash, composed.values["arm"], split)
        for kind, run in (("generation", RUNS[name][0]), ("fit", RUNS[name][1])):
            plan = _read(PACKAGE / f"{prefix}{kind}-plan-registered-v1.json")
            assert plan["composed_config_hash"] == composed.config_hash
            assert plan["execution_plan"]["protocol_hash"] == expected
            assert plan["execution_plan"]["run_id"] == run
            assert plan["execution_plan"]["split_identity_hash"] == split
            own = _own_supply(cell)
            assert plan["prepared_phase_supply"]["sha256"] == own["sha256"]
        if name == AA:
            assert _read(PACKAGE / "aa-generation-plan-registered-v1.json")["byte_identity_obligation"]["this_cell_output_sha256"] == PLAN_SUPPLY_OUTPUT_SHA


def test_the_registered_facts_prove_the_byte_identity_and_the_diffs(facts, cells):
    identity = facts["default_byte_identity"]
    assert identity["verified"] is True and identity["aa_output_sha256"] == PLAN_SUPPLY_OUTPUT_SHA
    assert identity["arm_output_sha256"] != PLAN_SUPPLY_OUTPUT_SHA
    diffs = facts["composed_config_diffs"]
    for name in ("arm_vs_locked_plan", "aa_vs_locked_plan", "arm_vs_aa", "smoke_vs_locked_plan_smoke"):
        assert diffs[name]["anything_else"] == [], name
    assert diffs["aa_vs_locked_plan"]["factor_paths"] == [RECALL]
    assert RECALL not in diffs["arm_vs_aa"]["factor_paths"]
    for name in (ARM, AA, SMOKE):
        key = {ARM: "arm", AA: "aa", SMOKE: "smoke"}[name]
        assert facts["cells"][key]["composed_config_hash"] == cells[name][2].config_hash
        own = _own_supply(cells[name][1])
        assert facts["prepared_supplies"][key]["file_sha256"] == own["sha256"]


def test_the_attribution_classes_partition_the_191_intent_wrong_rows(facts, cells):
    classes = _read(PACKAGE / "attribution-classes-v1.json")
    assert classes["intent_wrong_rows"] == 191
    members = {k: set(v["ids"]) for k, v in classes["classes"].items()}
    assert set(members) == {"delivered-but-wrong", "newly-by-both", "newly-by-agree", "newly-by-centroid", "catch-all"}
    assert sum(len(v) for v in members.values()) == 191
    assert len(set().union(*members.values())) == 191
    assert len(members["delivered-but-wrong"]) == 86
    assert len(members["newly-by-both"]) + len(members["newly-by-agree"]) == 70
    assert len(members["newly-by-both"]) + len(members["newly-by-centroid"]) == 55
    assert len(classes["per_row"]) == 191
    summary = classes["summary"]
    assert summary["delivered_under_comp1"] == sum(r["delivered_comp1"] for r in classes["per_row"].values())
    for key in ("arm", "aa"):
        own = _own_supply(cells[{"arm": ARM, "aa": AA}[key]][1])
        assert classes["inputs"][f"{key}_supply"]["sha256"] == own["sha256"]
    assert classes["inputs"]["aa_supply"]["output_sha256"] == PLAN_SUPPLY_OUTPUT_SHA
    assert facts["composed_delivery_model_free"]["summary"] == summary


def test_the_draft_decision_receipt_names_the_six_run_ids_and_is_not_decided():
    draft = _read(PACKAGE / "root-admission-draft-v1.json")
    assert draft["eligible_run_ids"] == [RUNS[ARM][0], RUNS[ARM][1], RUNS[AA][0], RUNS[AA][1], RUNS[SMOKE][0], RUNS[SMOKE][1]]
    assert draft["status"] != "decided"
    assert draft["decision_id"] == "slurp-stage3-comp1-fold-a-admission-v1"


def test_all_seven_exposure_rows_exist_and_no_cell_contains_a_pipe():
    """A literal '|' inside a cell silently splits the row, and
    contracts.ledger._parse_ledger_tables then refuses the whole ledger."""

    lines = io.open(REPO / "docs/exposure-ledger.md", encoding="utf-8", newline="").read().split("\n")
    wanted = [run for pair in RUNS.values() for run in pair] + [CLASSES_ROW]
    for run in wanted:
        found = [line for line in lines if line.startswith("|") and ("| " + run + " |") in line]
        assert len(found) == 1, run
        parts = found[0].split("|")
        assert len(parts) == 17, (run, len(parts))
        cells = [part.strip() for part in parts[1:-1]]
        assert cells[6] == "discovery"
        # "consumed" is operational lifecycle state (yes once the row is actually contacted),
        # never design identity; the schema position/enum is what a registered row must hold.
        assert cells[8] in ("yes", "no")
        if run == CLASSES_ROW:
            assert cells[2] == "model-free-check" and cells[9] == "0"
        elif run == RUNS[ARM][0]:
            assert PLACEHOLDER in found[0]
