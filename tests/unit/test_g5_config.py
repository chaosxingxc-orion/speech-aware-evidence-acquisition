"""Cell G5 -- the Reviewer instruction's retired-tool order deleted -- is the locked PLAN plan with
ONE pin moved, read on no harm at an in-chain A/A.

Config only: no data root, no lock, no adapter, no contact. Every assertion here is a property a
reader of the registration should be able to take for granted, and each one is a defect this
registration could plausibly have shipped.
"""

from __future__ import annotations

import difflib
import hashlib
import io
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash

REPO = Path(__file__).resolve().parents[2]

ARM = "slurp-native-stage3-g5-fold-a-v1"
AA = "slurp-native-stage3-g5-aa-fold-a-v1"
SMOKE = "slurp-native-stage3-g5-fold-a-smoke-4-v1"
ARM_RUN = "SAEA-SLURP-STAGE3-G5-FOLD-A-V1"
AA_RUN = "SAEA-SLURP-STAGE3-G5-AA-FOLD-A-V1"
SMOKE_RUN = "SAEA-SLURP-STAGE3-G5-FOLD-A-SMOKE-4-V1"
FIT = {ARM_RUN: "SAEA-SLURP-STAGE3-G5-FOLD-A-FIT-V1", AA_RUN: "SAEA-SLURP-STAGE3-G5-AA-FOLD-A-FIT-V1", SMOKE_RUN: "SAEA-SLURP-STAGE3-G5-FOLD-A-SMOKE-4-FIT-V1"}
MEASUREMENT_ROW = "SAEA-SLURP-G5-REVIEWER-INSTRUCTION-TOKEN-MEASUREMENT-V1"
PARENT = {ARM: "slurp-native-default-plan-lock-v1", AA: "slurp-native-default-plan-lock-v1", SMOKE: "slurp-native-default-plan-lock-smoke-4-v1"}
AGREE = "slurp-native-stage3-agree-w1-fold-a-v1"
AGREE_SMOKE = "slurp-native-stage3-agree-w1-fold-a-smoke-4-v1"

PACKAGE = REPO / "docs/readiness/2026-09-27-slurp-stage3-g5-fold-a-v1"
PREREG = REPO / "docs/readiness/2026-09-27-slurp-stage3-g5-fold-a-v1-preregistration.md"
OLD = REPO / "configs/probes/slurp_native_role_reviewer_v1.txt"
NEW = REPO / "configs/probes/slurp_native_role_reviewer_v1_g5_v1.txt"
ONE_PIN = "phase_material.reviewer.instruction_template"
BOOKKEEPING = ("native_contact_fit.", "prepared_phase_supply", "what_this_is")
H_SLU, H_INTENT = 1.2485, 0.9943
PLAN_SUPPLY_OUTPUT_SHA = "ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f"
RUN = {ARM: ARM_RUN, AA: AA_RUN, SMOKE: SMOKE_RUN}
DECISION_ID = "slurp-stage3-g5-fold-a-admission-v1"


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


def _assert_no_supply_or_the_cells_own(values: dict, experiment: str) -> None:
    """Before the flip no prepared supply is committed; the flip (scripts/flights/repin_cell.py --set-ready, the
    pattern of KPROBE's flip baa5ff99) pins this cell's OWN first-phase supply under its own run id (item E16)
    into the derived baseline. Either state is registered truth; a foreign supply never is."""

    supply = values.get("prepared_phase_supply")
    if supply is None:
        return
    assert supply["relpath"].startswith(f"prepared/{RUN[experiment]}/"), supply


def _diff(experiment: str) -> dict:
    document, mine = _compose(experiment)
    parent_doc, parent = _compose(PARENT[experiment])
    baseline_keys = set(_read(REPO / "configs/baseline" / (parent_doc["cells"][0]["baseline_fragment"] + ".json")))
    experiment_keys = set(document) | set(parent_doc)
    assert not (experiment_keys & baseline_keys), "the experiment fragment overrides a baseline key"
    a, b = _flatten(parent.values), _flatten(mine.values)
    changed = sorted(k for k in set(a) | set(b) if a.get(k, "<absent>") != b.get(k, "<absent>"))
    one_pin = [k for k in changed if k == ONE_PIN]
    bookkeeping = [k for k in changed if k.startswith(BOOKKEEPING)]
    experiment_block = [k for k in changed if k.split(".", 1)[0] in experiment_keys and k not in one_pin and k not in bookkeeping]
    other = [k for k in changed if k not in one_pin and k not in bookkeeping and k not in experiment_block]
    return {"one_pin": one_pin, "bookkeeping": bookkeeping, "experiment_block": experiment_block, "other": other,
            "mine": mine, "parent": parent, "document": document}


@pytest.fixture(scope="module")
def receipt() -> dict:
    return _read(PACKAGE / "instruction-token-measurement-v1.json")


@pytest.fixture(scope="module")
def facts() -> dict:
    return _read(PACKAGE / "registered-facts-v1.json")


# --------------------------------------------------------------------------
# the repaired instruction: deletions only, and the retired order is gone
# --------------------------------------------------------------------------


def test_the_repaired_instruction_is_the_old_one_minus_the_retired_tool_order() -> None:
    old, new = _text(OLD), _text(NEW)
    head, marker, tail = old.partition("Then review")
    assert marker, "the audit's split marker is gone from the v1 instruction"
    assert new == marker + tail, "the repaired file is not the review order byte for byte"
    assert head + new == old
    assert "task-contract tool" in head and "native function schema" in head and "source-bound result" in head
    for phrase in ("task-contract tool", "native function schema", "source-bound result", "do not call it again", "framework does not inject"):
        assert phrase not in new, phrase


def test_the_edit_is_deletion_only_at_word_level() -> None:
    old_words, new_words = _text(OLD).split(), _text(NEW).split()
    opcodes = difflib.SequenceMatcher(a=old_words, b=new_words, autojunk=False).get_opcodes()
    kinds = {tag for tag, *_ in opcodes}
    assert kinds <= {"equal", "delete"}, kinds
    deleted = sum(i2 - i1 for tag, i1, i2, _j1, _j2 in opcodes if tag == "delete")
    assert deleted == len(old_words) - len(new_words) > 0
    # the survivors are the old words, in order, with nothing added or rewritten
    it = iter(old_words)
    assert all(word in it for word in new_words)


def test_the_surviving_clauses_are_kept_verbatim() -> None:
    new = _text(NEW)
    assert new.startswith("Then review the Solver proposal against the current speech and role history.")
    assert "Do not request a transcript or invent a tool result." in new
    assert new.rstrip("\n").endswith("State concise findings for the Planner.")


def test_the_measurement_receipt_reproduces_the_audit_and_hashes_the_files(receipt: dict) -> None:
    tokens = receipt["tokens"]
    assert tokens["old_whole"] == 82 and tokens["old_retired_tool_order_head"] == 52
    assert tokens["retired_tool_share_of_old_pct"] == 63.4
    assert tokens["reproduces_the_audit"] is True
    assert tokens["new_whole"] == tokens["old_whole"] + tokens["delta_per_reviewer_contact"]
    assert tokens["delta_per_reviewer_contact"] < 0
    assert receipt["instruction"]["old"]["sha256"] == hashlib.sha256(OLD.read_bytes()).hexdigest()
    assert receipt["instruction"]["new"]["sha256"] == hashlib.sha256(NEW.read_bytes()).hexdigest()
    proof = receipt["deletion_only_proof"]
    assert proof["word_level"]["only_equal_and_delete"] is True
    assert proof["byte_level"]["old_equals_deleted_head_plus_new"] is True
    assert receipt["contacts"]["model"] == 0 and receipt["contacts"]["server"] == 0 and receipt["contacts"]["encoder"] == 0
    plan = receipt["sealed_reviewer_contact_rate"]["plan"]
    assert plan["run_id"] == "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1" and plan["rows"] == 1080
    assert plan["reviewer_contacts"] == plan["role_visits"]["reviewer"] >= 1080
    saving = receipt["saving"]
    assert saving["tokens_per_reviewer_contact"] == -tokens["delta_per_reviewer_contact"]
    assert saving["tokens_per_1080_row_flight_at_the_sealed_plan_count"] == saving["tokens_per_reviewer_contact"] * plan["reviewer_contacts"]
    assert saving["tokens_per_row_at_the_sealed_plan_rate"] == pytest.approx(saving["tokens_per_reviewer_contact"] * plan["reviewer_contacts"] / 1080, abs=1e-3)


# --------------------------------------------------------------------------
# one pin, proven on the composed configs
# --------------------------------------------------------------------------


@pytest.mark.parametrize("experiment", [ARM, SMOKE])
def test_arm_and_smoke_differ_from_their_locked_plan_parent_by_the_one_pin_and_bookkeeping(experiment: str) -> None:
    d = _diff(experiment)
    assert d["other"] == [], d["other"]
    assert d["one_pin"] == [ONE_PIN]
    mine, parent = d["mine"].values, d["parent"].values
    assert parent["phase_material"]["reviewer"]["instruction_template"] == "probes/slurp_native_role_reviewer_v1.txt"
    assert mine["phase_material"]["reviewer"]["instruction_template"] == "probes/slurp_native_role_reviewer_v1_g5_v1.txt"
    assert {k: v for k, v in mine["phase_material"]["reviewer"].items() if k != "instruction_template"} == \
        {k: v for k, v in parent["phase_material"]["reviewer"].items() if k != "instruction_template"}
    for phase in ("perception", "solver", "planner"):
        assert mine["phase_material"][phase] == parent["phase_material"][phase]
    for key in ("knowledge_stores", "native_episode", "scorers", "policy", "arm", "evidence_source", "task_instruction_template",
                "task_instruction_fill", "serving_slot_tokens", "serving_slots", "preparation_source_receipts"):
        assert mine[key] == parent[key], key
    assert "phase_tools" not in mine
    _assert_no_supply_or_the_cells_own(mine, experiment)


def test_the_in_chain_aa_is_the_locked_plan_with_bookkeeping_alone() -> None:
    d = _diff(AA)
    assert d["other"] == [] and d["one_pin"] == []
    mine, parent = d["mine"].values, d["parent"].values
    assert mine["phase_material"] == parent["phase_material"]
    assert mine["phase_material"]["reviewer"]["instruction_template"] == "probes/slurp_native_role_reviewer_v1.txt"
    for key in ("knowledge_stores", "native_episode", "scorers", "policy", "arm", "preparation_source_receipts"):
        assert mine[key] == parent[key], key
    assert "phase_tools" not in mine
    _assert_no_supply_or_the_cells_own(mine, AA)


def test_the_arm_and_the_aa_differ_from_each_other_in_the_one_pin_and_their_own_identities_only() -> None:
    arm_doc, arm = _compose(ARM)
    aa_doc, aa = _compose(AA)
    own_block = set(arm_doc) | set(aa_doc)  # the experiment fragment's own keys: ids, purpose, label, budgets
    a, b = _flatten(aa.values), _flatten(arm.values)
    changed = sorted(k for k in set(a) | set(b) if a.get(k, "<absent>") != b.get(k, "<absent>"))
    knowledge_side = [k for k in changed if not k.startswith(BOOKKEEPING) and k.split(".", 1)[0] not in own_block]
    assert knowledge_side == [ONE_PIN], knowledge_side
    assert arm_doc["family_budget"] == aa_doc["family_budget"]
    assert arm_doc["population"] == aa_doc["population"]


@pytest.mark.parametrize("experiment", [ARM, AA, SMOKE])
def test_readiness_is_held_with_an_empty_requirements_list_and_the_policies_the_gates_require(experiment: str) -> None:
    document, composed = _compose(experiment)
    readiness = document["cells"][0]["readiness"]
    # `held` with the empty requirements list as registered (b23b0fd7); `ready` after the converging re-pin, whose
    # requirements are this family's own decision receipt and this cell's own prepared supply (the KPROBE flip
    # baa5ff99 and its test repair 324808a5 are the pattern).
    assert readiness["state"] in ("held", "ready")
    if readiness["state"] == "held":
        assert readiness["requirements"] == []
        assert "--allow-output-change must never be passed" in readiness["reason"]
        assert PLAN_SUPPLY_OUTPUT_SHA in readiness["reason"]
    else:
        kinds = sorted(req["kind"] for req in readiness["requirements"])
        assert kinds == ["decision", "preparation"], kinds
        for req in readiness["requirements"]:
            if req["kind"] == "decision":
                assert req["expected_decision_id"] == DECISION_ID, req
            else:
                assert req["relpath"].startswith(f"prepared/{RUN[experiment]}/"), req
    episode = composed.values["native_episode"]
    assert episode["finite_completion_policy"] == "deliver-latest-or-abstain"
    assert episode["react_exhaustion_policy"] == "continue-without-answer"
    label = document["stage3_algorithm"]
    assert label["id"] == "none" and label["operators_used"] == [] and "NO training-free RL operator" in label["note"]
    assert document["execution_profile"] == "bounded-discovery-probe"
    assert document["execution_plan"]["split_role"] == "discovery"


def test_caps_are_the_agree_arithmetic() -> None:
    agree = _read(REPO / "configs/experiment" / f"{AGREE}.json")
    agree_smoke = _read(REPO / "configs/experiment" / f"{AGREE_SMOKE}.json")
    for experiment in (ARM, AA):
        document = _read(REPO / "configs/experiment" / f"{experiment}.json")
        assert document["family_budget"] == agree["family_budget"]
        assert document["execution_plan"] == agree["execution_plan"]
        assert document["family_budget"]["generation_calls_cap"] == 1080 * 11
        assert document["family_budget"]["fit_endpoint_calls_cap"] == 4 * 1080 * 11
        assert document["generation_budget"]["cap"] == 1080 * 11
    smoke = _read(REPO / "configs/experiment" / f"{SMOKE}.json")
    assert smoke["family_budget"] == agree_smoke["family_budget"]
    assert smoke["family_budget"]["generation_calls_cap"] == 44
    assert smoke["population"]["count"] == 4 and len(smoke["populations"][0]["ids"]) == 4


@pytest.mark.parametrize("experiment,fit_run", [(ARM, FIT[ARM_RUN]), (AA, FIT[AA_RUN]), (SMOKE, FIT[SMOKE_RUN])])
def test_the_fit_identity_is_each_cell_s_own(experiment: str, fit_run: str) -> None:
    document, composed = _compose(experiment)
    fit = composed.values["native_contact_fit"]
    assert fit["run_id"] == fit_run
    assert fit["attempt_id"].startswith("attempt-slurp-native-stage3-g5-") and fit["attempt_id"].endswith("-fit-v1")
    assert fit["contact_cap"] == document["family_budget"]["fit_endpoint_calls_cap"]


def test_the_campaign_plan_is_the_arm_alone_and_the_smoke_is_outside_it() -> None:
    """Owner decision 160: the G5 A/A is dropped from the plan -- the shared A/A (COMP-1's) flies in COMP-1's
    plan in the SAME chain (scripts/flights/comp1/batch_chain_comp1_g5.sh). The superseded A/A cell itself is
    left exactly as registered."""

    plan = _read(REPO / "configs/campaign" / f"{ARM}.json")
    assert plan["schema"] == "saea-campaign-plan-v1"
    assert plan["cells"] == [{"cell": ARM, "experiment": ARM}]
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
    # owner decision 160: re-declared to the shared in-chain A/A, COMP-1's
    assert block["replicate_run_id"] == "SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1" and block["rows"] == 1080
    assert "decision 160" in block["replicate_note"] and "shared-aa-proof-v1.json" in block["replicate_note"]
    assert "intent accuracy" in block["primary_metric"]
    aa = facts["stage3_measurement"][AA_RUN]
    assert aa["claims_benefit"] is False and aa["replicate_run_id"] == ARM_RUN and "admission" not in aa
    assert aa["status"].startswith("superseded-unflown")
    smoke = facts["stage3_measurement"][SMOKE_RUN]
    assert smoke["measurement_design"] == "form-proof" and smoke["claims_benefit"] is False and smoke["rows"] == 4


def test_the_effect_floor_gate_accepts_the_family() -> None:
    import importlib.util
    import sys

    # The gate module declares dataclasses, which resolve their own module through sys.modules while the class
    # body executes; an unregistered spec-loaded module therefore fails to import unless an EARLIER test had
    # already imported it by name (order dependence: this test failed when run alone). Reuse the registered
    # module when present, else register it before executing.
    gate = sys.modules.get("stage3_effect_floor_check")
    if gate is None:
        spec = importlib.util.spec_from_file_location("stage3_effect_floor_check", REPO / "scripts/checks/stage3_effect_floor_check.py")
        gate = importlib.util.module_from_spec(spec)
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


def test_the_facts_carry_the_one_pin_diffs_and_the_comp2_fragment(facts: dict) -> None:
    diff = facts["composed_config_diff_against_the_locked_plan_cell"]
    for key in ("arm", "smoke"):
        assert diff[key]["the_one_pin"] == [ONE_PIN] and diff[key]["anything_else"] == []
    assert diff["aa"]["the_one_pin"] == [] and diff["aa"]["anything_else"] == []
    pin = _read(PACKAGE / "comp2-pin-v1.json")
    assert pin["composed_key"] == ONE_PIN
    assert pin["value"] == "probes/slurp_native_role_reviewer_v1_g5_v1.txt"
    assert pin["instruction_sha256"] == hashlib.sha256(NEW.read_bytes()).hexdigest() == facts["comp2_pin"]["instruction_sha256"]
    assert pin["replaces"]["sha256"] == hashlib.sha256(OLD.read_bytes()).hexdigest()
    assert facts["comparator"]["margins"] == {"h_slu": H_SLU, "h_intent": H_INTENT} | {"source": facts["comparator"]["margins"]["source"]}
    assert "never reported as a gain" in facts["no_harm_rule"].lower() or "never reported as a gain" in facts["prohibitions"][0].lower()


def test_the_plan_documents_carry_the_recomposed_hashes() -> None:
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
    draft = _read(PACKAGE / "root-admission-draft-v1.json")
    assert draft["eligible_run_ids"] == [ARM_RUN, FIT[ARM_RUN], AA_RUN, FIT[AA_RUN], SMOKE_RUN, FIT[SMOKE_RUN]]
    assert draft["status"] != "decided"
    assert draft["decision_id"] == "slurp-stage3-g5-fold-a-admission-v1"


def test_all_seven_exposure_rows_exist_and_no_cell_contains_a_pipe() -> None:
    """A literal '|' inside a cell silently splits the row, and
    contracts.ledger._parse_ledger_tables then refuses the whole ledger."""

    lines = _text(REPO / "docs/exposure-ledger.md").split("\n")
    runs = [ARM_RUN, FIT[ARM_RUN], AA_RUN, FIT[AA_RUN], SMOKE_RUN, FIT[SMOKE_RUN], MEASUREMENT_ROW]
    for run in runs:
        found = [line for line in lines if line.startswith("|") and ("| " + run + " |") in line]
        assert len(found) == 1, run
        parts = found[0].split("|")
        assert len(parts) == 17, (run, parts[:3])
        cells = [part.strip() for part in parts[1:-1]]
        assert cells[6] == "discovery" and cells[8] in ("no", "yes")  # flown and sealed; closed by scripts/flights/batch/ledger_mark_consumed.py
        assert cells[2] == ("model-free-check" if run == MEASUREMENT_ROW else "bounded-discovery-probe")
    arm_row = next(line for line in lines if ("| " + ARM_RUN + " |") in line)
    assert "admission no-harm" in arm_row and "NEVER reported as a gain" in arm_row
