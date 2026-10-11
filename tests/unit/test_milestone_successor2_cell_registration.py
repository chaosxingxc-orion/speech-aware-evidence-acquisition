"""SLURP test-sample SUCCESSOR-2 (the NX R5 composed arm on the signed sample): the HELD registration is what its package says (model-free).

Reads committed fragments, the SIGNED allowance (owner decision 251 A, 2026-10-10), the package, the go-live wrappers and the ledger tail.
Proves: the identities are exactly the registered ones; the cell is a final-report plan on the sample's split identity; the allowance pin is the
signed bytes in every copy (status authorised) and the gate ACCEPTS exactly the two permitted ids and refuses a drifted pin; the policy is the
review-off c2 program with ceiling 2; the budgets are the ceiling arithmetic; one attempt per id; the cell is still held; the sealed successor-1
comparators are named and not re-flown; no smoke fragment exists and the launch chain's queue declares no smoke; the decision-250 exception is
recorded; the measurement block and the three DRAFT ledger rows (the END of the ledger, one contiguous block) agree.
"""

from __future__ import annotations

import ast
import hashlib
import importlib
import json
import math
import re
import shutil
import sys
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.contracts import ExecutionScopeError
from speech_aware_evidence_acquisition.contracts.plan import require_owner_split_allowance
from speech_aware_evidence_acquisition.core.stage3_algorithms import registered_ids, validate_stage3_algorithm_label
from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
from speech_aware_evidence_acquisition.rails import consumption_module as cm
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config

REPO = Path(__file__).resolve().parents[2]
ZERO = "0" * 64
SIGNED = "4e04b23f89b9eb06c1b228649a6f991fb9399dea6efbaf4d168a4b731d9e388d"  # committed bytes at master 951de831b
CELL = "slurp-milestone-successor2-composed-v1"
BASELINE = "slurp-milestone-successor2-composed-baseline-v1"
RUN = "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-COMPOSED-V1"
ATTEMPT = "attempt-slurp-milestone-successor2-composed-generation-v1"
FIT_RUN = "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-COMPOSED-FIT-V1"
FIT_ATTEMPT = "attempt-slurp-milestone-successor2-composed-fit-v1"
READ_RUN = "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-PAIRED-ANALYSIS-V1"
RECIPE_ID = "slurp-milestone-successor2-composed-paired-analysis-v1"
PACKAGE = "docs/readiness/2026-10-10-slurp-milestone-successor2-composed-v1"
ALLOWANCE = "docs/receipts/owner/2026-10-10-slurp-test-sample-successor2-allowance-v1.json"
S1_ALLOWANCE = "docs/receipts/owner/2026-10-01-slurp-test-sample-successor1-allowance-v1.json"
SPLIT = "0164dabf7b30f8e06f830ba28af849cef7459e8c8821cfbea7a56cabb32470f9"
S1_COMP1B = "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR1-COMP1B-V1"
S1_PLAN = "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR1-PLAN-V1"
ROWS = 3010
AUDIO_SECONDS = 8206.436875


def _load(relpath: str) -> dict:
    return json.loads((REPO / relpath).read_text(encoding="utf-8"))


def _experiment() -> dict:
    return _load(f"configs/experiment/{CELL}.json")


def _baseline() -> dict:
    return _load(f"configs/baseline/{BASELINE}.json")


def _facts() -> dict:
    return _load(f"{PACKAGE}/registered-facts-v1.json")


def _composed():
    document = _experiment()
    cell = document["cells"][0]
    return compose(REPO, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], CELL)


def _sha(relpath: str) -> str:
    return hashlib.sha256((REPO / relpath).read_bytes()).hexdigest()


# ---- identities, role, roster ---------------------------------------------------------------------------------
def test_identities_are_exactly_the_registered_ones():
    document = _experiment()
    cell = document["cells"][0]
    assert (cell["cell_id"], cell["baseline_fragment"], cell["run_id"], cell["attempt_id"]) == (CELL, BASELINE, RUN, ATTEMPT)
    assert document["experiment_id"] == RUN
    fit = _baseline()["native_contact_fit"]
    assert (fit["run_id"], fit["attempt_id"]) == (FIT_RUN, FIT_ATTEMPT)
    recipe = _load(f"{PACKAGE}/analysis-recipe-v1.json")
    assert (recipe["read_run_id"], recipe["recipe_id"]) == (READ_RUN, RECIPE_ID)
    assert _load(f"configs/campaign/{CELL}.json")["cells"] == [{"cell": CELL, "experiment": CELL}]


def test_final_report_role_roster_and_split_identity():
    document = _experiment()
    assert document["execution_plan"]["split_role"] == "final-report"
    assert document["split_id"] == "TEST-SAMPLE"
    assert document["population"]["count"] == ROWS
    assert document["population"]["split_identity_hash"] == SPLIT
    roster = _load(document["population"]["roster_receipt"])
    assert roster["roster_id"] == "SLURP-TEST-SAMPLE-3010-V1" and roster["split_identity_hash"] == SPLIT
    assert _load(S1_ALLOWANCE)["split"]["split_identity_hash"] == SPLIT
    composed = _composed()
    assert composed.values["scorers"] == ["slurp-slu-official-test", "cost"]
    assert composed.values["split_role"] == "final-report"
    assert composed.values["split_identity_hash"] == SPLIT
    assert composed.values["count"] == ROWS


def test_the_sample_preparations_are_successor_ones_pins_reused():
    s1 = _load("docs/readiness/2026-10-01-slurp-milestone-successor1-v1/registered-facts-v1.json")["sample_preparation_pins"]["pins"]
    mine = _facts()["sample_preparation_pins"]["pins"]
    assert mine == s1 and len(mine) == 6
    required = {r["relpath"]: r["sha256"] for r in _experiment()["cells"][0]["readiness"]["requirements"]}
    for pin in mine:
        if pin["relpath"].endswith(("agreement.jsonl", "query-vectors-speech-segments.jsonl", "query-vectors-speech-content-v1.jsonl")):
            assert required[pin["relpath"]] == pin["sha256"]


# ---- the allowance DRAFT and its pin --------------------------------------------------------------------------
def test_the_cell_pins_the_signed_allowance_bytes_and_the_gate_accepts_exactly_the_two_ids():
    document = _experiment()
    assert document["owner_allowance"] == {"path": ALLOWANCE, "sha256": SIGNED}
    assert _composed().values["owner_allowance"] == {"path": ALLOWANCE, "sha256": SIGNED}
    assert _sha(ALLOWANCE) == SIGNED
    signed = _load(ALLOWANCE)
    assert signed["status"] == "authorised"
    assert signed["signature"]["decision"] == 251 and signed["signature"]["form"] == "explicit confirmation in conversation"
    assert signed["signature"]["signed_by"] and signed["signature"]["signed_at"] == "2026-10-10T12:30:00Z"
    assert signed["signature"]["owner_words_english"].startswith("Decision 249: agreed; 250: A; 251: A, allowance v3 signed")
    for run_id in (RUN, FIT_RUN):
        accepted = require_owner_split_allowance(
            run_id=run_id, execution_profile="bounded-discovery-probe", carrier_lock_key="slurp",
            split_identity_hash=SPLIT, owner_allowance=document["owner_allowance"], source_root=REPO)
        assert run_id in accepted["permitted_run_ids"]
        with pytest.raises(ExecutionScopeError, match="hashes to"):
            require_owner_split_allowance(
                run_id=run_id, execution_profile="bounded-discovery-probe", carrier_lock_key="slurp",
                split_identity_hash=SPLIT, owner_allowance={"path": ALLOWANCE, "sha256": ZERO}, source_root=REPO)
    for other in (READ_RUN, S1_COMP1B, S1_PLAN, RUN.replace("-V1", "-V2")):
        with pytest.raises(ExecutionScopeError, match="is not in the owner allowance"):
            require_owner_split_allowance(
                run_id=other, execution_profile="bounded-discovery-probe", carrier_lock_key="slurp",
                split_identity_hash=SPLIT, owner_allowance=document["owner_allowance"], source_root=REPO)
    with pytest.raises(ExecutionScopeError):
        require_owner_split_allowance(
            run_id=RUN, execution_profile="paper-scale-confirmatory", carrier_lock_key="slurp",
            split_identity_hash=SPLIT, owner_allowance=document["owner_allowance"], source_root=REPO)


def test_the_signed_sha_is_pinned_in_every_copy_and_no_zero_pin_remains():
    facts = _facts()
    assert facts["allowance"]["sha256_pinned_in_the_fragment"] == SIGNED and facts["allowance"]["sha256_of_signed_bytes"] == SIGNED
    assert facts["allowance"]["status_signed"] == "authorised"
    assert facts["cells"]["composed"]["owner_allowance"] == {"path": ALLOWANCE, "sha256": SIGNED}
    for kind in ("generation", "fit"):
        assert _load(f"{PACKAGE}/{kind}-plan-registered-v1.json")["execution_plan"]["owner_allowance"] == {"path": ALLOWANCE, "sha256": SIGNED}
    draft = _load(f"{PACKAGE}/root-admission-draft-v1.json")
    assert draft["antecedents"]["allowance"]["sha256"] == SIGNED
    zero_pin = re.compile(r'"owner_allowance": \{\s*"path": "[^"]+",\s*"sha256": "' + ZERO + '"')
    for relpath in [f"configs/experiment/{CELL}.json", *(str(p.relative_to(REPO)).replace("\\", "/") for p in (REPO / PACKAGE).iterdir() if p.is_file())]:
        text = (REPO / relpath).read_text(encoding="utf-8")
        assert not zero_pin.search(text), relpath
    for relpath in (f"{PACKAGE}/README.md", f"{PACKAGE}-preregistration.md"):
        text = (REPO / relpath).read_text(encoding="utf-8")
        assert SIGNED in text and "unsigned DRAFT" not in text, relpath
    for relpath in (f"{PACKAGE}/protocol-registered-v1.json", f"{PACKAGE}/registered-facts-v1.json"):
        text = (REPO / relpath).read_text(encoding="utf-8")
        assert SIGNED in text and "an unsigned DRAFT" not in text, relpath
    ledger = (REPO / "docs/exposure-ledger.md").read_text(encoding="utf-8")
    rows = [line for line in ledger.split("\n") if line.startswith("| 2026-") and (f"| {RUN} |" in line or f"| {FIT_RUN} |" in line)]
    assert len(rows) == 2 and all(SIGNED in row and "allowance SIGNED 2026-10-10" in row and "unsigned" not in row for row in rows)


def test_the_signed_allowance_permits_exactly_the_two_new_ids_and_supersedes_successor_one_by_scope():
    draft = _load(ALLOWANCE)
    assert draft["schema"] == "saea-owner-split-allowance-v1" and draft["study"] == "speech-aware-evidence-acquisition"
    assert draft["permitted_run_ids"] == [RUN, FIT_RUN]
    assert draft["read_run_ids"] == [RUN] and draft["preparation_run_ids"] == [FIT_RUN]
    assert READ_RUN not in draft["permitted_run_ids"]
    assert draft["run_ids"][RUN]["kind"] == "read" and draft["run_ids"][FIT_RUN]["kind"] == "preparation"
    assert draft["supersedes"]["path"] == S1_ALLOWANCE
    assert draft["supersedes"]["sha256"] == _sha(S1_ALLOWANCE)
    assert draft["supersedes"]["scope"].startswith("New successor run identities only")
    assert "\"As you suggest.\"" in draft["dated_owner_decision"] and "241" in draft["dated_owner_decision"]
    assert draft["first_contact_gate"]["basis"] == "R5 read NEUTRAL on DEV-2000-ADDED 2026-10-10: efficiency result, no harm, intent gain replicated a third time"
    s1 = _load(S1_ALLOWANCE)
    for key in ("split", "venue", "closure_status", "derived_from", "schema", "study"):
        assert draft[key] == s1[key], key
    assert draft["budgets"]["generation_cap_per_arm"] == 6020 and draft["budgets"]["fit_endpoint_cap_per_arm"] == 24080
    # successor 1's signed bytes are untouched (they are what the draft pins)
    assert s1["status"] == "authorised"


def test_a_re_signed_copy_is_accepted_for_exactly_the_two_ids(tmp_path: Path):
    draft = _load(ALLOWANCE)
    signed = dict(draft, status="authorised",
                  signature=dict(draft["signature"], signed_by="owner", signed_at="2026-10-10T00:00:00+00:00",
                                 owner_words_english="As you suggest.", coordinator="test"))
    raw = (json.dumps(signed, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    target = tmp_path / ALLOWANCE
    target.parent.mkdir(parents=True)
    target.write_bytes(raw)
    pin = {"path": ALLOWANCE, "sha256": hashlib.sha256(raw).hexdigest()}

    def call(run_id: str):
        return require_owner_split_allowance(
            run_id=run_id, execution_profile="bounded-discovery-probe", carrier_lock_key="slurp",
            split_identity_hash=SPLIT, owner_allowance=pin, source_root=tmp_path)

    for run_id in (RUN, FIT_RUN):
        assert run_id in call(run_id)["permitted_run_ids"]
    for other in (READ_RUN, S1_COMP1B, S1_PLAN, "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-COMPOSED-V2"):
        with pytest.raises(ExecutionScopeError, match="is not in the owner allowance"):
            call(other)


# ---- the program, ceiling and caps -----------------------------------------------------------------------------
def test_policy_is_the_review_off_c2_program_with_ceiling_two():
    document = _baseline()
    block = document["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY]
    cm.verify_declared_module(block, document, repo_root=REPO)
    assert block["lock"] == "v2.2" and block["review_loop"] == "off"
    assert sorted(c["component_id"] for c in block["components"] if c["state"] != "off") == [cm.AGREE_VOTE_SEED, cm.CENTROID_BOUNDARY_KEY]
    assert document["policy"] == "phase-native-module-v1-c2"
    ne = document["native_episode"]
    assert ne["review_loop"] == "off" and ne["max_revisions"] == 0
    assert ne["roles"]["reviewer"]["max_iterations"] == 0 and ne["roles"]["planner"]["max_iterations"] == 0
    assert ne["deliver_normaliser"]["normaliser"] == "saea-deliver-normalise-v4g"
    assert ne["finite_completion_policy"] == "deliver-latest-or-abstain"
    assert ne["react_exhaustion_policy"] == "continue-without-answer"
    assert document["phase_tools"] == {}
    values = dict(document)
    values["carrier_lock_key"] = document.get("carrier_lock_key", "slurp")
    parsed = load_native_episode_config(values, default_phase_program(document["policy"]))
    assert parsed.max_contacts == 2 and not parsed.review_loop_enabled


def test_the_arm_is_the_r5_dev_cell_with_only_roster_role_and_bookkeeping_leaves_moved():
    r5 = _load("configs/baseline/slurp-native-stage3-nx-r5-composed-dev2000-added-baseline-v1.json")
    mine = _baseline()
    for key in ("native_episode", "phase_material", "phase_tools", "policy", "evidence_source", "serving_slots", "serving_slot_tokens",
                "task_instruction_template", "task_instruction_fill", "speech_feature_key_representation_id"):
        assert mine[key] == r5[key] or key == "native_episode", key
    mine_ne, r5_ne = dict(mine["native_episode"]), dict(r5["native_episode"])
    for ne in (mine_ne, r5_ne):
        ne["consumption_module"] = {k: v for k, v in ne["consumption_module"].items() if k != "components"}
    assert mine_ne == r5_ne
    facts = _facts()["composed_config_diffs"]
    assert facts["s2_vs_r5_dev"]["anything_else"] == [] and facts["s2_vs_r5_dev"]["composition_factor"] == []
    assert facts["composition_delta_commutes"]["commutes"] is True
    assert facts["composition_delta_commutes"]["graph_leaves_moved_by_r5_on_dev"] == facts["composition_delta_commutes"]["successor1_comp1b_to_s2_moves_exactly_these"]


def test_budgets_are_the_ceiling_arithmetic():
    document = _experiment()
    budget = document["family_budget"]
    assert budget["generation_calls_cap"] == ROWS * 2 == 6020
    assert budget["fit_endpoint_calls_cap"] == ROWS * 2 * (_baseline()["native_contact_fit"]["max_speech_packets"] + 3) == 24080
    assert _baseline()["native_contact_fit"]["contact_cap"] == 24080
    assert budget["native_task_contract_calls_cap"] == 6020
    assert budget["repeated_speech_audio_seconds_cap"] == math.ceil(2 * AUDIO_SECONDS) == 16413
    assert budget["gpu_hours_fit_inclusive"] == 4.6 >= round(6020 / 24 / 60, 2)
    assert budget["official_complete_scoring_jobs"] == 1 and budget["asr_calls"] == 0 and budget["encoder_calls"] == 0
    assert document["generation_budget"]["cap"] == 6020
    plan = document["execution_plan"]
    assert (plan["planned_model_calls"], plan["planned_speech_audio_seconds"], plan["planned_gpu_hours"]) == (6020, 16413, 4.6)
    for kind, calls in (("generation", 6020), ("fit", 24080)):
        doc = _load(f"{PACKAGE}/{kind}-plan-registered-v1.json")
        assert doc["execution_plan"]["planned_model_calls"] == calls
        assert doc["execution_plan"]["split_role"] == "final-report" and doc["execution_plan"]["owner_allowance"]["sha256"] == SIGNED
        assert doc["execution_plan"]["split_identity_hash"] == SPLIT
    s1_facts = _load("docs/readiness/2026-10-01-slurp-milestone-successor1-v1/registered-facts-v1.json")
    assert s1_facts["rows"] == ROWS


def test_plan_documents_carry_the_composed_hashes():
    composed = _composed()
    facts = _facts()["cells"]["composed"]
    assert facts["composed_config_hash"] == composed.config_hash
    assert facts["protocol_hash"] == protocol_hash(composed.config_hash, composed.values["arm"], SPLIT)
    for kind in ("generation", "fit"):
        doc = _load(f"{PACKAGE}/{kind}-plan-registered-v1.json")
        assert doc["composed_config_hash"] == composed.config_hash
        assert doc["execution_plan"]["protocol_hash"] == facts["protocol_hash"]
        assert doc["protocol_document"]["sha256"] == _sha(f"{PACKAGE}/protocol-registered-v1.json")


# ---- one attempt, held, comparators, no smoke ------------------------------------------------------------------
def test_one_attempt_semantics_and_no_recovery():
    document = _experiment()
    policy = document["failure_policy"]
    assert policy.startswith("ONE ATTEMPT, EVER")
    assert "NO recovery re-registration" in policy and "NO resume-recovery" in policy and "no re-score" in policy
    assert "resume_from" not in document["cells"][0]
    draft = _load(ALLOWANCE)
    assert draft["attempt_budget"]["read_run_ids"] == 1 and draft["attempt_budget"]["preparation_run_ids"] == 1
    assert "No automatic retry" in draft["attempt_budget"]["statement"]
    assert "smoke" in " ".join(draft["not_authorized"]).lower()


def test_the_cell_carries_its_own_pinned_supply_and_the_minted_root_admission():
    # Registered HELD with a zero-hash supply and no decision requirement; flipped to ready by 26545f617
    # (2026-10-10), which pinned the cell's own prepared_phase_supply and added the root-admission decision
    # requirement. The cell was then flown and sealed, so the post-flip shape is the stable invariant.
    cell = _experiment()["cells"][0]
    assert cell["readiness"]["state"] == "ready"
    kinds = [r["kind"] for r in cell["readiness"]["requirements"]]
    assert "decision" in kinds
    supply = [r for r in cell["readiness"]["requirements"] if r["relpath"].endswith("phase-supply-v1.json")]
    assert len(supply) == 1 and supply[0]["sha256"] != ZERO and supply[0]["relpath"] == f"prepared/{RUN}/phase-supply-v1.json"
    assert _baseline()["prepared_phase_supply"] == {"relpath": supply[0]["relpath"], "sha256": supply[0]["sha256"]}
    assert all(r["sha256"] != ZERO for r in cell["readiness"]["requirements"])
    draft = _load(f"{PACKAGE}/root-admission-draft-v1.json")
    assert draft["status"] == "DRAFT-NOT-MINTED" and draft["eligible_run_ids"] == [RUN, FIT_RUN]


def test_the_sealed_successor_one_comparators_are_named_and_not_reflown():
    recipe = _load(f"{PACKAGE}/analysis-recipe-v1.json")
    assert recipe["arms"]["comparator"]["run_id"] == S1_COMP1B
    assert recipe["arms"]["plan_comparator"]["run_id"] == S1_PLAN
    assert recipe["arms"]["arm"]["run_id"] == RUN and "in_chain_replicate" not in recipe["arms"]
    assert recipe["read_driver"]["scorer"] == "slurp-slu-official-test"
    assert recipe["resampling"]["seed"] == 20260915 and recipe["resampling"]["bootstrap_draws"] == 10000
    facts = _facts()
    assert facts["comparators_sealed"]["re_flown"] is False
    assert facts["comparators_sealed"]["primary"]["run_id"] == S1_COMP1B and facts["comparators_sealed"]["plan"]["run_id"] == S1_PLAN
    campaign = _load(f"configs/campaign/{CELL}.json")
    assert S1_COMP1B not in json.dumps(campaign) and S1_PLAN not in json.dumps(campaign)
    experiments = [p.name for p in (REPO / "configs/experiment").glob("*successor2*")]
    assert experiments == [f"{CELL}.json"]


def test_no_smoke_fragment_or_smoke_run_exists_for_the_sample():
    assert not list((REPO / "configs").rglob("*successor2*smoke*"))
    assert not list((REPO / PACKAGE).glob("*smoke*"))
    ledger = (REPO / "docs/exposure-ledger.md").read_text(encoding="utf-8")
    assert "SUCCESSOR2-SMOKE" not in ledger and "SUCCESSOR2-COMPOSED-SMOKE" not in ledger
    assert "smoke" in _load(f"{PACKAGE}/registered-facts-v1.json")["allowance"]["smoke"].lower()


# ---- the measurement block and the ledger rows ------------------------------------------------------------------
def test_measurement_block_is_a_cross_flight_no_harm_declaration_with_the_dev_offset():
    block = _facts()["stage3_measurement"][RUN]
    assert block["measurement_design"] == "cross-flight-no-replicate"
    assert block["admission"] == "no-harm" and block["claims_benefit"] is False and block["harm_margin_pp"] == 2.5
    assert block["primary_metric_key"] == "slu" and block["expected_effect_pp"] == 1.2429 and block["rows"] == ROWS
    assert block["declared_flight_offset"]["slu_pp"] == 0.7274 and block["declared_flight_offset"]["intent_pp"] == 0.2
    assert block["comparator_run_id"] == S1_COMP1B and block["plan_comparator_run_id"] == S1_PLAN
    assert block["read_roster"] == "SLURP-TEST-SAMPLE-3010-V1" and block["tuning_roster"] != "none"
    assert "no in-chain replicate" in block["design_statement"].lower() or "NO IN-CHAIN REPLICATE" in block["design_statement"]
    assert _experiment()["stage3_algorithm"]["id"] in registered_ids()
    validate_stage3_algorithm_label(_experiment()["stage3_algorithm"], cell=CELL)
    assert _experiment()["stage3_algorithm"]["id"] == _load("configs/experiment/slurp-native-stage3-nx-r5-composed-dev2000-added-v1.json")["stage3_algorithm"]["id"]


def test_three_countersigned_ledger_rows_sit_in_one_contiguous_block_of_their_own_section():
    lines = (REPO / "docs/exposure-ledger.md").read_text(encoding="utf-8").rstrip("\n").split("\n")
    heading = max(i for i, line in enumerate(lines) if line.startswith("## Test-sample successor 2:"))
    # Bound the tail at the next section: later registrations (VER-1a/1b/1c, the earnings22 all-off block) are
    # appended after this section, so "the end of the ledger" was only true when the test was written.
    following = next((i for i in range(heading + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    tail = lines[heading:following]
    while tail and not tail[-1].strip():
        tail.pop()
    rows = [line for line in tail if line.startswith("| 2026-")]
    assert len(rows) == 3 and all(line.startswith("|") for line in tail[tail.index(next(l for l in tail if l.startswith("| date"))):])
    assert [row.split(" | ")[1] for row in rows] == [RUN, FIT_RUN, READ_RUN]
    for row in rows:
        # Registered as DRAFT rows; root countersigned them 2026-10-10 (12:55Z run/FIT rows, 18:40Z analysis row)
        # before the flight. The countersigned wording replaced the draft wording in the same row text.
        assert "REGISTERED BEFORE CONTACT (root countersigned 2026-10-10T" in row and "DRAFT, root countersignature pending" not in row
        assert row.split(" | ")[8] == "yes"  # consumed: flown and sealed; closed by scripts/flights/batch/ledger_mark_consumed.py
    assert rows[0].split(" | ")[2] == "bounded-discovery-probe" and rows[2].split(" | ")[2] == "model-free-check"
    assert rows[0].split(" | ")[9] == "6020" and rows[1].split(" | ")[9] == "24080"
    assert all(len(row.strip("|").split(" | ")) == 15 for row in rows)
    assert (REPO / PACKAGE / "README.md").exists() and (REPO / (PACKAGE + "-preregistration.md")).exists()


# ---- the go-live wrappers, the no-smoke chain, the decision-250 exception -----------------------------------------
NX = REPO / "scripts/flights/nx"


def _import_nx(name: str):
    if str(NX) not in sys.path:
        sys.path.insert(0, str(NX))
    return importlib.import_module(name)


def _chain_steps() -> list[dict]:
    text = (NX / "batch_chain_milestone_successor2.sh").read_text(encoding="utf-8")
    for body in re.findall(r"<<'PY'[^\n]*\n(.*?)\nPY\n", text, flags=re.S):
        tree = ast.parse(body)
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(getattr(target, "id", "") == "steps" for target in node.targets):
                return ast.literal_eval(node.value)
    raise AssertionError("the chain writes no queue")


def test_the_chain_queue_has_one_step_and_no_smoke_and_the_driver_skips_a_missing_smoke():
    steps = _chain_steps()
    assert len(steps) == 1
    step = steps[0]
    assert step["kind"] == "cell" and step["experiment"] == CELL and step["cell"] == CELL
    assert step["smoke_experiment"] is None and step["smoke_cell"] is None
    assert step["smoke_run_id"] is None and step["smoke_attempt_id"] is None
    assert step["run_id"] == RUN and step["fit_run_id"] == FIT_RUN and step["gen_attempt_id"] == ATTEMPT
    assert step["campaign_plan"] == f"configs/campaign/{CELL}.json"
    assert step["expected_rows"] == ROWS and step["contacts_per_row"] == 2 and step["ceiling_per_row"] == 2 and step["notool"] is True
    driver = (REPO / "scripts/flights/batch/batch_driver.sh").read_text(encoding="utf-8")
    assert 'if [ -n "$sexp" ] && [ "$sexp" != "None" ]; then' in driver and "fly_smoke $order" in driver
    for name in ("batch_chain_milestone_successor2.sh", "milestone_successor2_flip.sh", "milestone_successor2_repin_cell.sh",
                 "milestone_successor2_mint_receipt.py", "milestone_successor2_preflip_check.py"):
        source = (NX / name).read_text(encoding="utf-8")
        assert "smoke-4" not in source and "SMOKE-4" not in source, name
    chain = (NX / "batch_chain_milestone_successor2.sh").read_text(encoding="utf-8")
    assert "serving-slurp-native-candidate-five-train-a-np4-v1" in chain and "/home/chao/ms2-flight-commit.txt" in chain
    assert "ONE attempt, ever; refusing to launch" in chain and "milestone_successor2_preflip_check.py" in chain


def test_flip_wrapper_is_loop_form_single_cell_and_refuses_without_the_receipt():
    flip = (NX / "milestone_successor2_flip.sh").read_text(encoding="utf-8")
    assert "root-admission-v1.json" in flip and "is not minted" in flip and "exit 6" in flip
    assert "repin_loop_generic.sh" in flip and "for pass in 1 2 3 4" in flip and 'echo "$CONVERGED" > /home/chao/ms2-flight-commit.txt' in flip
    assert flip.count("repin_loop_generic.sh") == 1
    assert "milestone_successor2_preflip_check.py" in flip
    repin = (NX / "milestone_successor2_repin_cell.sh").read_text(encoding="utf-8")
    assert f"CELL={CELL}" in repin and "ARM=0" in repin and "unset ALLOW_OUTPUT_CHANGE" in repin
    assert "DEC_ID=slurp-milestone-successor2-admission-v1" in repin and f"DEC_PATH=coordination/{CELL}/root-admission-v1.json" in repin.replace("$PKG", CELL)
    assert "allow-output-change" not in flip.replace("--allow-output-change must never be passed", "")


def test_mint_wrapper_binds_the_two_eligible_ids_and_the_draft_identity():
    mint = _import_nx("milestone_successor2_mint_receipt")
    draft = _load(f"{PACKAGE}/root-admission-draft-v1.json")
    assert mint.ELIGIBLE == [RUN, FIT_RUN] == draft["eligible_run_ids"]
    assert mint.DECISION_ID == draft["decision_id"] == "slurp-milestone-successor2-admission-v1"
    assert mint.DECISION_RELPATH == f"coordination/{CELL}/root-admission-v1.json"
    assert mint.DRAFT == f"{PACKAGE}/root-admission-draft-v1.json"


def test_preflip_gate_is_clean_on_the_held_registration_and_refuses_drift(tmp_path: Path):
    pf = _import_nx("milestone_successor2_preflip_check")
    assert pf.refusals(REPO, None) == []
    work = tmp_path / "repo"
    for sub in ("configs/experiment", "configs/baseline", "configs/campaign"):
        (work / sub).mkdir(parents=True)
    shutil.copy(REPO / f"configs/experiment/{CELL}.json", work / f"configs/experiment/{CELL}.json")
    shutil.copy(REPO / f"configs/baseline/{BASELINE}.json", work / f"configs/baseline/{BASELINE}.json")
    shutil.copy(REPO / f"configs/campaign/{CELL}.json", work / f"configs/campaign/{CELL}.json")
    (work / ALLOWANCE).parent.mkdir(parents=True)
    shutil.copy(REPO / ALLOWANCE, work / ALLOWANCE)
    assert pf.refusals(work, None) == []
    # a smoke fragment for the sample is refused
    (work / "configs/experiment/slurp-milestone-successor2-composed-smoke-4-v1.json").write_text("{}", encoding="utf-8")
    assert any(line.startswith("smoke-registered") for line in pf.refusals(work, None))
    (work / "configs/experiment/slurp-milestone-successor2-composed-smoke-4-v1.json").unlink()
    # a drifted allowance (bytes or status) is refused
    allowance = json.loads((work / ALLOWANCE).read_text(encoding="utf-8"))
    allowance["status"] = "draft-awaiting-owner-signature"
    (work / ALLOWANCE).write_text(json.dumps(allowance, indent=2) + "\n", encoding="utf-8")
    found = pf.refusals(work, None)
    assert any(line.startswith("allowance-pin-mismatch") for line in found) and any(line.startswith("allowance-not-authorised") for line in found)
    shutil.copy(REPO / ALLOWANCE, work / ALLOWANCE)
    # ONE attempt, ever: an existing attempt directory is refused
    data = tmp_path / "data"
    (data / "attempts" / RUN).mkdir(parents=True)
    (data / "attempts" / RUN / ATTEMPT).write_text("x", encoding="utf-8")
    assert any(line.startswith("attempt-exists") for line in pf.refusals(work, data))


def test_decision_250_exception_is_recorded_in_every_measurement_copy():
    for relpath in (f"{PACKAGE}/registered-facts-v1.json", f"{PACKAGE}/protocol-registered-v1.json"):
        block = _load(relpath)["stage3_measurement"][RUN]
        assert block["measurement_design"] == "cross-flight-no-replicate"
        ruling = block["owner_ruling_decision_250"]
        assert ruling["decision"] == 250 and ruling["option"] == "A" and ruling["date"] == "2026-10-10"
        assert "cross-flight-no-replicate" in ruling["ruling"] and "0.7274 pp SLU-F1 / 0.20 pp intent" in ruling["ruling"]
        assert "no in-chain replicate" in ruling["ruling"].lower() and "margin 2.5" in ruling["ruling"]
        assert block["declared_flight_offset"]["slu_pp"] == 0.7274 and block["declared_flight_offset"]["intent_pp"] == 0.2
        assert "owner decision 250 (option A)" in block["design_statement"]
    assert _facts()["allowance"]["decision_250_ruling"]["option"] == "A"
    assert _load(f"{PACKAGE}/root-admission-draft-v1.json")["decision_250_ruling"]["decision"] == 250
    for relpath in (f"{PACKAGE}/README.md", f"{PACKAGE}-preregistration.md"):
        text = (REPO / relpath).read_text(encoding="utf-8")
        assert "owner_ruling_decision_250" in text and "decision 250" in text.lower(), relpath
    blockers = _facts()["blockers_before_the_flip"]
    assert blockers[0].startswith("OWNER SIGNATURE: RESOLVED") and blockers[1].startswith("MEASUREMENT RULE: RULED")
