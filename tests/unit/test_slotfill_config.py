"""Cell SLOTFILL -- the dispatcher keeps every serving slot loaded (owner decision 159) -- is the
locked PLAN plan with ONE key added, read on no harm at an in-chain A/A.

Config only: no data root, no lock, no adapter, no contact. Every assertion here is a property a
reader of the registration should be able to take for granted, and each one is a defect this
registration could plausibly have shipped.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
from speech_aware_evidence_acquisition.rails.dispatch_slot_fill import (
    DispatchSlotFill,
    parse_dispatch_slot_fill,
)

REPO = Path(__file__).resolve().parents[2]

ARM = "slurp-native-stage3-slotfill-fold-a-v1"
AA = "slurp-native-stage3-slotfill-aa-fold-a-v1"
SMOKE = "slurp-native-stage3-slotfill-fold-a-smoke-4-v1"
ARM_RUN = "SAEA-SLURP-STAGE3-SLOTFILL-FOLD-A-V1"
AA_RUN = "SAEA-SLURP-STAGE3-SLOTFILL-AA-FOLD-A-V1"
SMOKE_RUN = "SAEA-SLURP-STAGE3-SLOTFILL-FOLD-A-SMOKE-4-V1"
FIT = {
    ARM_RUN: "SAEA-SLURP-STAGE3-SLOTFILL-FOLD-A-FIT-V1",
    AA_RUN: "SAEA-SLURP-STAGE3-SLOTFILL-AA-FOLD-A-FIT-V1",
    SMOKE_RUN: "SAEA-SLURP-STAGE3-SLOTFILL-FOLD-A-SMOKE-4-FIT-V1",
}
MEASUREMENT_ROW = "SAEA-SLURP-SLOTFILL-MODEL-FREE-PROOF-V1"
PARENT = {ARM: "slurp-native-default-plan-lock-v1", AA: "slurp-native-default-plan-lock-v1", SMOKE: "slurp-native-default-plan-lock-smoke-4-v1"}
G5 = "slurp-native-stage3-g5-fold-a-v1"
G5_SMOKE = "slurp-native-stage3-g5-fold-a-smoke-4-v1"

PACKAGE = REPO / "docs/readiness/2026-09-27-slurp-stage3-slotfill-fold-a-v1"
PREREG = REPO / "docs/readiness/2026-09-27-slurp-stage3-slotfill-fold-a-v1-preregistration.md"
THE_KEY = "dispatch"
ALL_ON = DispatchSlotFill(recall_prefetch=True, role_input_offload=True, gc_freeze=True)
BOOKKEEPING = ("native_contact_fit.", "prepared_phase_supply", "what_this_is")
H_SLU, H_INTENT = 1.2485, 0.9943
PLAN_SUPPLY_OUTPUT_SHA = "ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f"


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _text(path: Path) -> str:
    return io.open(path, encoding="utf-8", newline="").read()


def _flatten(node, prefix: str = "") -> dict:
    out = {}
    if isinstance(node, dict):
        for key, value in node.items():
            out.update(_flatten(value, f"{prefix}{key}."))
    else:
        out[prefix[:-1]] = node
    return out


def _compose(experiment: str):
    document = _read(REPO / "configs/experiment" / f"{experiment}.json")
    cell = document["cells"][0]
    return document, compose(REPO, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], experiment)


def _diff(experiment: str) -> dict:
    document, mine = _compose(experiment)
    parent_doc, parent = _compose(PARENT[experiment])
    baseline_keys = set(_read(REPO / "configs/baseline" / (parent_doc["cells"][0]["baseline_fragment"] + ".json")))
    experiment_keys = set(document) | set(parent_doc)
    assert not (experiment_keys & baseline_keys), "the experiment fragment overrides a baseline key"
    a, b = _flatten(parent.values), _flatten(mine.values)
    changed = sorted(k for k in set(a) | set(b) if a.get(k, "<absent>") != b.get(k, "<absent>"))
    one_key = [k for k in changed if k == THE_KEY or k.startswith(THE_KEY + ".")]
    bookkeeping = [k for k in changed if k.startswith(BOOKKEEPING)]
    experiment_block = [k for k in changed if k.split(".", 1)[0] in experiment_keys and k not in one_key and k not in bookkeeping]
    other = [k for k in changed if k not in one_key and k not in bookkeeping and k not in experiment_block]
    return {"one_key": one_key, "bookkeeping": bookkeeping, "experiment_block": experiment_block, "other": other,
            "mine": mine, "parent": parent, "document": document}


def _package_ready() -> bool:
    return (PACKAGE / "registered-facts-v1.json").is_file()


@pytest.fixture(scope="module")
def facts() -> dict:
    if not _package_ready():
        pytest.skip("the registration package is not written yet")
    return _read(PACKAGE / "registered-facts-v1.json")


# --------------------------------------------------------------------------
# one key, proven on the composed configs
# --------------------------------------------------------------------------


@pytest.mark.parametrize("experiment", [ARM, SMOKE])
def test_arm_and_smoke_differ_from_their_locked_plan_parent_by_the_one_key_and_bookkeeping(experiment: str) -> None:
    d = _diff(experiment)
    assert d["other"] == [], d["other"]
    assert d["one_key"] and all(k.startswith(THE_KEY + ".") for k in d["one_key"])
    mine, parent = d["mine"].values, d["parent"].values
    assert parse_dispatch_slot_fill(parent) is None
    assert parse_dispatch_slot_fill(mine) == ALL_ON
    for key in ("phase_material", "knowledge_stores", "native_episode", "scorers", "policy", "arm", "evidence_source",
                "task_instruction_template", "task_instruction_fill", "serving_slot_tokens", "serving_slots",
                "preparation_source_receipts"):
        assert mine[key] == parent[key], key
    assert "phase_tools" not in mine and "prepared_phase_supply" not in mine


def test_the_in_chain_aa_is_the_locked_plan_with_bookkeeping_alone() -> None:
    d = _diff(AA)
    assert d["other"] == [] and d["one_key"] == []
    mine, parent = d["mine"].values, d["parent"].values
    assert parse_dispatch_slot_fill(mine) is None
    for key in ("phase_material", "knowledge_stores", "native_episode", "scorers", "policy", "arm", "preparation_source_receipts"):
        assert mine[key] == parent[key], key
    assert "phase_tools" not in mine and "prepared_phase_supply" not in mine


def test_the_arm_and_the_aa_differ_from_each_other_in_the_one_key_and_their_own_identities_only() -> None:
    arm_doc, arm = _compose(ARM)
    aa_doc, aa = _compose(AA)
    own_block = set(arm_doc) | set(aa_doc)
    a, b = _flatten(aa.values), _flatten(arm.values)
    changed = sorted(k for k in set(a) | set(b) if a.get(k, "<absent>") != b.get(k, "<absent>"))
    other = [k for k in changed if not k.startswith(BOOKKEEPING) and k.split(".", 1)[0] not in own_block]
    assert other and all(k.startswith(THE_KEY + ".") for k in other), other
    assert arm_doc["family_budget"] == aa_doc["family_budget"]
    assert arm_doc["population"] == aa_doc["population"]


@pytest.mark.parametrize("experiment", [ARM, AA, SMOKE])
def test_readiness_is_held_with_an_empty_requirements_list_and_the_policies_the_gates_require(experiment: str) -> None:
    document, composed = _compose(experiment)
    readiness = document["cells"][0]["readiness"]
    assert readiness["state"] == "held" and readiness["requirements"] == []
    assert "--allow-output-change must never be passed" in readiness["reason"]
    assert PLAN_SUPPLY_OUTPUT_SHA in readiness["reason"]
    episode = composed.values["native_episode"]
    assert episode["finite_completion_policy"] == "deliver-latest-or-abstain"
    assert episode["react_exhaustion_policy"] == "continue-without-answer"
    label = document["stage3_algorithm"]
    assert label["id"] == "none" and label["operators_used"] == [] and "NO training-free RL operator" in label["note"]
    assert document["execution_profile"] == "bounded-discovery-probe"
    assert document["execution_plan"]["split_role"] == "discovery"


def test_caps_are_the_locked_family_arithmetic() -> None:
    g5 = _read(REPO / "configs/experiment" / f"{G5}.json")
    g5_smoke = _read(REPO / "configs/experiment" / f"{G5_SMOKE}.json")
    for experiment in (ARM, AA):
        document = _read(REPO / "configs/experiment" / f"{experiment}.json")
        assert document["family_budget"] == g5["family_budget"]
        assert document["execution_plan"] == g5["execution_plan"]
        assert document["family_budget"]["generation_calls_cap"] == 1080 * 11
        assert document["family_budget"]["fit_endpoint_calls_cap"] == 4 * 1080 * 11
        assert document["generation_budget"]["cap"] == 1080 * 11
    smoke = _read(REPO / "configs/experiment" / f"{SMOKE}.json")
    assert smoke["family_budget"] == g5_smoke["family_budget"]
    assert smoke["family_budget"]["generation_calls_cap"] == 44
    assert smoke["population"]["count"] == 4 and len(smoke["populations"][0]["ids"]) == 4


@pytest.mark.parametrize("experiment,fit_run", [(ARM, FIT[ARM_RUN]), (AA, FIT[AA_RUN]), (SMOKE, FIT[SMOKE_RUN])])
def test_the_fit_identity_is_each_cell_s_own(experiment: str, fit_run: str) -> None:
    document, composed = _compose(experiment)
    fit = composed.values["native_contact_fit"]
    assert fit["run_id"] == fit_run
    assert fit["attempt_id"].startswith("attempt-slurp-native-stage3-slotfill-") and fit["attempt_id"].endswith("-fit-v1")
    assert fit["contact_cap"] == document["family_budget"]["fit_endpoint_calls_cap"]


def test_the_campaign_plan_is_the_aa_then_the_arm_and_the_smoke_is_outside_it() -> None:
    plan = _read(REPO / "configs/campaign" / f"{ARM}.json")
    assert plan["schema"] == "saea-campaign-plan-v1"
    assert plan["cells"] == [{"cell": AA, "experiment": AA}, {"cell": ARM, "experiment": ARM}]
    for experiment in (ARM, AA):
        assert "campaign" in _read(REPO / "configs/experiment" / f"{experiment}.json")["cells"][0]["allowed_execution_stages"]
    assert "campaign" not in _read(REPO / "configs/experiment" / f"{SMOKE}.json")["cells"][0]["allowed_execution_stages"]


# --------------------------------------------------------------------------
# the declaration, the package, the ledger
# --------------------------------------------------------------------------


def test_the_measurement_declaration_is_a_no_harm_admission_at_the_fold_a_half_widths(facts: dict) -> None:
    block = facts["stage3_measurement"][ARM_RUN]
    assert block["admission"] == "no-harm"
    assert block["harm_margin_pp"] == H_SLU
    assert block["harm_margin_pp_by_metric"] == {"intent_accuracy": H_INTENT, "slu_f1": H_SLU}
    assert block["claims_benefit"] is False and block["expected_effect_pp"] == 0.0
    assert block["measurement_design"] == "cross-flight-with-in-chain-replicate"
    assert block["replicate_run_id"] == AA_RUN and block["rows"] == 1080
    assert block["primary_metric"].startswith("intent accuracy")
    assert block["throughput_ceiling"]["read_against"] == AA_RUN and block["throughput_ceiling"]["claims_gain"] is False
    aa = facts["stage3_measurement"][AA_RUN]
    assert aa["claims_benefit"] is False and aa["replicate_run_id"] == ARM_RUN and "admission" not in aa
    smoke = facts["stage3_measurement"][SMOKE_RUN]
    assert smoke["measurement_design"] == "form-proof" and smoke["claims_benefit"] is False and smoke["rows"] == 4


def test_the_effect_floor_gate_accepts_the_family() -> None:
    if not _package_ready():
        pytest.skip("the registration package is not written yet")
    import importlib.util

    spec = importlib.util.spec_from_file_location("stage3_effect_floor_check", REPO / "scripts/checks/stage3_effect_floor_check.py")
    gate = importlib.util.module_from_spec(spec)
    import sys

    # a dataclass module must be importable by name while it is executed
    sys.modules[spec.name] = gate
    spec.loader.exec_module(gate)
    data = gate.evaluate(REPO)
    ours = [f for f in data["findings"] if any(cell in f["message"] for cell in (ARM, AA, SMOKE))]
    assert ours == [], ours
    assert gate.floor_for("cross-flight-with-in-chain-replicate", 1080, purpose="harm")[0] == pytest.approx(H_SLU)


def test_the_preregistration_fence_repeats_the_canonical_block(facts: dict) -> None:
    text = PREREG.read_text(encoding="utf-8")
    start = text.index("```json")
    fenced = json.loads(text[text.index("\n", start) + 1 : text.index("```", start + 7)])
    assert fenced["stage3_measurement"] == facts["stage3_measurement"]


def test_the_facts_carry_the_one_key_diffs_and_the_proofs(facts: dict) -> None:
    diff = facts["composed_config_diff_against_the_locked_plan_cell"]
    for key in ("arm", "smoke"):
        assert diff[key]["the_one_key"] and diff[key]["anything_else"] == []
    assert diff["aa"]["the_one_key"] == [] and diff["aa"]["anything_else"] == []
    assert facts["byte_identity"]["all_identical"] is True
    assert facts["reproduced_accounting"]["matches_note"] is True
    assert facts["comparator"]["margins"]["h_slu"] == H_SLU and facts["comparator"]["margins"]["h_intent"] == H_INTENT


def test_the_plan_documents_carry_the_recomposed_hashes() -> None:
    if not _package_ready():
        pytest.skip("the registration package is not written yet")
    for experiment, run, prefix in ((ARM, ARM_RUN, ""), (AA, AA_RUN, "aa-"), (SMOKE, SMOKE_RUN, "smoke-")):
        document, composed = _compose(experiment)
        split = document["population"]["split_identity_hash"]
        expected = protocol_hash(composed.config_hash, composed.values["arm"], split)
        for kind, run_id in (("generation", run), ("fit", FIT[run])):
            plan = _read(PACKAGE / f"{prefix}{kind}-plan-registered-v1.json")
            assert plan["composed_config_hash"] == composed.config_hash
            assert plan["execution_plan"]["protocol_hash"] == expected
            assert plan["execution_plan"]["run_id"] == run_id
            assert plan["execution_plan"]["split_identity_hash"] == split
            assert plan["prepared_phase_supply"]["sha256"] == "MINTED_AT_THE_FLIP"
            assert plan["prepared_phase_supply"]["expected_output_sha256"] == PLAN_SUPPLY_OUTPUT_SHA


def test_the_draft_decision_receipt_names_the_six_run_ids_and_is_not_decided() -> None:
    if not _package_ready():
        pytest.skip("the registration package is not written yet")
    draft = _read(PACKAGE / "root-admission-draft-v1.json")
    assert draft["eligible_run_ids"] == [ARM_RUN, FIT[ARM_RUN], AA_RUN, FIT[AA_RUN], SMOKE_RUN, FIT[SMOKE_RUN]]
    assert draft["status"] != "decided"
    assert draft["decision_id"] == "slurp-stage3-slotfill-fold-a-admission-v1"


def test_all_seven_exposure_rows_exist_and_no_cell_contains_a_pipe() -> None:
    """A literal '|' inside a cell silently splits the row, and
    contracts.ledger._parse_ledger_tables then refuses the whole ledger."""

    if not _package_ready():
        pytest.skip("the registration package is not written yet")
    lines = _text(REPO / "docs/exposure-ledger.md").split("\n")
    runs = [ARM_RUN, FIT[ARM_RUN], AA_RUN, FIT[AA_RUN], SMOKE_RUN, FIT[SMOKE_RUN], MEASUREMENT_ROW]
    for run in runs:
        found = [line for line in lines if line.startswith("|") and ("| " + run + " |") in line]
        assert len(found) == 1, run
        parts = found[0].split("|")
        assert len(parts) == 17, (run, parts[:3])
        cells = [part.strip() for part in parts[1:-1]]
        assert cells[6] == "discovery" and cells[8] == "no"
        assert cells[2] == ("model-free-check" if run == MEASUREMENT_ROW else "bounded-discovery-probe")
        assert "DRAFT" in cells[14]
    arm_row = next(line for line in lines if ("| " + ARM_RUN + " |") in line)
    assert "admission no-harm" in arm_row and "NEVER reported as a quality gain" in arm_row
