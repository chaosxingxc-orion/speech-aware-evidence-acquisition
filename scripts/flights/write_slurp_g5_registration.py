#!/usr/bin/env python3
"""Write the G5 registration package from the committed configs.

Item G5 -- the Reviewer instruction's retired-tool order (owner decisions 135 and
153; a row-127 no-harm item flown in round 3, folded into the composed round
after it under row 138). Reads the three derived fragments and the token
measurement receipt, recomposes every cell's own hashes, PROVES the composed-
config diff against the locked PLAN cells is the ONE pin
(``phase_material.reviewer.instruction_template``) plus per-flight bookkeeping
for the arm and the smoke and bookkeeping alone for the in-chain A/A, and
writes the package documents, the COMP-2 pin fragment, a draft decision receipt
for root, and (with ``--append-ledger``) the seven exposure rows. Config alone:
no adapter, no split load, no lock, no contact; it flips nothing and mints
nothing.

    python scripts/flights/write_slurp_g5_registration.py \\
        --study-commit <sha> --registered-at 2026-09-27T13:00:00.000000+00:00 [--append-ledger]
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.config import (  # noqa: E402
    compose,
    protocol_hash,
)

PACKAGE = "docs/readiness/2026-09-27-slurp-stage3-g5-fold-a-v1"
PREREG = PACKAGE + "-preregistration.md"
RECEIPT = PACKAGE + "/instruction-token-measurement-v1.json"
LEDGER = "docs/exposure-ledger.md"

PARENT_ARM = "slurp-native-default-plan-lock-v1"
PARENT_SMOKE = "slurp-native-default-plan-lock-smoke-4-v1"
COMPARATOR_RUN = "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1"
COMPARATOR_ATTEMPT = "attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1"
COMPARATOR_OFFICIAL = {"slu_f1": 63.6304, "intent_accuracy": 82.2222}
PLANR_RUN = "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-REPLICATE-V1"
PLAN_SUPPLY_OUTPUT_SHA = "ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f"
SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"

CELLS = {
    "arm": "slurp-native-stage3-g5-fold-a-v1",
    "smoke": "slurp-native-stage3-g5-fold-a-smoke-4-v1",
    "aa": "slurp-native-stage3-g5-aa-fold-a-v1",
}
PARENTS = {"arm": PARENT_ARM, "smoke": PARENT_SMOKE, "aa": PARENT_ARM}
PREFIX = {"arm": "", "smoke": "smoke-", "aa": "aa-"}
FLIGHT_PROSE = {
    "arm": "Cell G5",
    "smoke": "Four-row form smoke of cell G5",
    "aa": "The in-chain A/A replicate of cell G5",
}
DECISION_ID = "slurp-stage3-g5-fold-a-admission-v1"
DECISION_RELPATH = "coordination/slurp-stage3-g5-fold-a-v1/root-admission-v1.json"
MEASUREMENT_ROW = "SAEA-SLURP-G5-REVIEWER-INSTRUCTION-TOKEN-MEASUREMENT-V1"

OLD_TEMPLATE = "probes/slurp_native_role_reviewer_v1.txt"
NEW_TEMPLATE = "probes/slurp_native_role_reviewer_v1_g5_v1.txt"
THE_ONE_PIN = "phase_material.reviewer.instruction_template"
BOOKKEEPING_PREFIXES = ("native_contact_fit.", "prepared_phase_supply", "what_this_is")

H_SLU, H_INTENT = 1.2485, 0.9943

AUDIT = "docs/results/2026-09-26-slurp-reviewer-planner-global-state-audit.md"
AUDIT_SCRIPT = "scripts/analysis/slurp_reviewer_planner_global_state_audit.py"
SUMMARY_DIAG = "docs/results/2026-09-26-system-summary001-fidelity-and-feedback-diagnostic.md"
INSTRUMENT = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"
OWNER_DECISIONS = "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md"
NOTOOL_VERDICT = "docs/results/2026-09-20-slurp-b1-notool-verdict.md"
HARNESS_RECEIPT = "docs/receipts/harness-admission.json"
AGREE_PACKAGE = "docs/readiness/2026-09-26-slurp-stage3-agree-w1-fold-a-v1"
MEASURE_SCRIPT = "scripts/analysis/slurp_g5_reviewer_instruction_token_measurement.py"
DERIVE_SCRIPT = "scripts/flights/derive_slurp_g5_cells.py"
CONFIG_TEST = "tests/unit/test_g5_config.py"
READ_DRIVER_FAMILY = "scripts/analysis/plan_cell_read.py"
GATE = "scripts/checks/stage3_effect_floor_check.py"

E25_CITATION = (
    f"{HARNESS_RECEIPT}: the entry whose row is SAEA-SLURP-NATIVE-EXEMPLARS-K20-NOTOOL-V1 (status "
    "RETIRED, switch class phase_tools, key phase_tools.reviewer, ON = the saea-tool-task-contract-v1 "
    "toolkit the anchor-to-B5e cells carried, OFF = absent); the class and status were added to the "
    "receipt's switch_rule and status_values by item E25 on 2026-09-20 (schema_history "
    f"saea-harness-admission-v3). Verdict {NOTOOL_VERDICT} (owner decisions 55, 56; status NEUTRAL made "
    f"final by decision 61 in {OWNER_DECISIONS}); the lock note docs/results/2026-09-22-slurp-v2-lock-v1.md "
    "row 'the Reviewer's native toolkit: phase_tools absent, RETIRED'."
)


def rd(path: str) -> str:
    return io.open(path, encoding="utf-8", newline="").read()


def wr(path: str, text: str) -> str:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="").write(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def wjson(path: str, obj: object) -> str:
    return wr(path, json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def sha_file(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def flatten(node, prefix: str = "") -> dict:
    out = {}
    if isinstance(node, dict):
        for key, value in node.items():
            out.update(flatten(value, f"{prefix}{key}."))
    else:
        out[prefix[:-1]] = node
    return out


def composed_diff(parent_values: dict, mine: dict, experiment_keys: set, baseline_keys: set) -> dict:
    overlap = sorted(experiment_keys & baseline_keys)
    if overlap:
        raise SystemExit(f"the experiment fragment overrides baseline keys: {overlap}")
    a, b = flatten(parent_values), flatten(mine)
    changed = sorted(k for k in set(a) | set(b) if a.get(k, "<absent>") != b.get(k, "<absent>"))
    one_pin = [k for k in changed if k == THE_ONE_PIN]
    bookkeeping = [k for k in changed if k.startswith(BOOKKEEPING_PREFIXES)]
    experiment_block = [k for k in changed if k.split(".", 1)[0] in experiment_keys and k not in one_pin and k not in bookkeeping]
    other = [k for k in changed if k not in one_pin and k not in bookkeeping and k not in experiment_block]
    return {"the_one_pin": one_pin, "baseline_bookkeeping_only": bookkeeping,
            "experiment_fragment_own_block": experiment_block, "anything_else": other}


def identities() -> dict:
    out = {}
    for key, experiment in CELLS.items():
        document = json.loads(rd(f"configs/experiment/{experiment}.json"))
        cell = document["cells"][0]
        composed = compose(REPO_ROOT, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], experiment)
        parent_doc = json.loads(rd(f"configs/experiment/{PARENTS[key]}.json"))
        parent_cell = parent_doc["cells"][0]
        parent = compose(REPO_ROOT, parent_cell["model_fragment"], parent_cell["dataset_fragment"], parent_cell["baseline_fragment"], PARENTS[key])
        baseline_keys = set(json.loads(rd(f"configs/baseline/{parent_cell['baseline_fragment']}.json")))
        diff = composed_diff(parent.values, composed.values, set(document) | set(parent_doc), baseline_keys)
        if diff["anything_else"]:
            raise SystemExit(f"{key}: composed config differs from its locked PLAN parent beyond the pin and bookkeeping: {diff['anything_else']}")
        template = composed.values["phase_material"]["reviewer"]["instruction_template"]
        if key == "aa":
            if diff["the_one_pin"] or template != OLD_TEMPLATE:
                raise SystemExit("the A/A must carry the OLD Reviewer instruction and move no pin")
        else:
            if diff["the_one_pin"] != [THE_ONE_PIN] or template != NEW_TEMPLATE:
                raise SystemExit(f"{key}: the one pin did not move to {NEW_TEMPLATE}")
        if "prepared_phase_supply" in composed.values:
            raise SystemExit(f"{key}: the derived cell must carry no committed prepared_phase_supply")
        if "phase_tools" in composed.values:
            raise SystemExit(f"{key}: phase_tools present; the Reviewer toolkit is RETIRED")
        mine_pm = {k: v for k, v in composed.values["phase_material"].items() if k != "reviewer"}
        theirs_pm = {k: v for k, v in parent.values["phase_material"].items() if k != "reviewer"}
        if mine_pm != theirs_pm:
            raise SystemExit(f"{key}: phase_material differs beyond the reviewer entry")
        split = document["population"]["split_identity_hash"]
        out[key] = {
            "experiment": experiment, "cell": cell["cell_id"], "run_id": cell["run_id"], "attempt_id": cell["attempt_id"],
            "baseline_fragment": cell["baseline_fragment"], "parent_experiment": PARENTS[key],
            "parent_baseline_fragment": parent_cell["baseline_fragment"],
            "dataset_fragment": cell["dataset_fragment"], "model_fragment": cell["model_fragment"],
            "arm": composed.values["arm"], "rows": document["population"]["count"], "split_identity_hash": split,
            "composed_config_hash": composed.config_hash, "parent_composed_config_hash": parent.config_hash,
            "protocol_hash": protocol_hash(composed.config_hash, composed.values["arm"], split),
            "fit": dict(composed.values["native_contact_fit"]), "family_budget": document["family_budget"],
            "execution_plan": document["execution_plan"], "execution_profile": document["execution_profile"],
            "carrier_lock_key": composed.values["carrier_lock_key"],
            "reviewer_instruction_template": template,
            "native_episode_policies": {k: composed.values["native_episode"].get(k) for k in ("finite_completion_policy", "react_exhaustion_policy")},
            "composed_config_diff_against_the_locked_plan_cell": diff,
            "readiness": cell["readiness"],
            "allowed_execution_stages": cell["allowed_execution_stages"],
            "generation_budget_target": document.get("generation_budget", {}).get("target"),
        }
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--study-commit", required=True)
    parser.add_argument("--registered-at", required=True)
    parser.add_argument("--branch", default="fable/g5")
    parser.add_argument("--worktree", default="/home/chao/saea-worktrees/fable-g5")
    parser.add_argument("--append-ledger", action="store_true")
    args = parser.parse_args(argv)
    os.chdir(REPO_ROOT)

    receipt = json.loads(rd(RECEIPT))
    if receipt["schema"] != "saea-g5-reviewer-instruction-token-measurement-v1":
        raise SystemExit("the token measurement receipt is not the expected schema")
    new_sha = receipt["instruction"]["new"]["sha256"]
    old_sha = receipt["instruction"]["old"]["sha256"]
    if sha_file("configs/" + NEW_TEMPLATE) != new_sha or sha_file("configs/" + OLD_TEMPLATE) != old_sha:
        raise SystemExit("the instruction files on disk do not hash to the measurement receipt")
    proof = receipt["deletion_only_proof"]
    if not (proof["word_level"]["only_equal_and_delete"] and proof["byte_level"]["old_equals_deleted_head_plus_new"]):
        raise SystemExit("the receipt does not prove a deletion-only edit")
    tokens = receipt["tokens"]
    plan = receipt["sealed_reviewer_contact_rate"]["plan"]
    saving = receipt["saving"]
    receipt_sha = sha_file(RECEIPT)

    ids = identities()
    arm, aa, smoke = ids["arm"], ids["aa"], ids["smoke"]
    caps, smoke_caps = arm["family_budget"], smoke["family_budget"]
    if aa["family_budget"] != caps:
        raise SystemExit("the A/A caps are not the arm's")
    agree_caps = json.loads(rd(f"configs/experiment/{AGREE_PACKAGE.rsplit('/', 1)[1].replace('2026-09-26-slurp-stage3-', 'slurp-native-stage3-')}.json"))["family_budget"]
    if agree_caps != caps:
        raise SystemExit("the arm caps are not the AGREE arithmetic")

    no_harm_rule = (
        "NO-HARM ADMITTED (owner decision 127): against the IN-CHAIN A/A arm flown in the same "
        f"chain, the paired CI95 lower bound of the intent-accuracy delta (primary, decision 133) is not "
        f"below -{H_INTENT} pp AND the paired CI95 lower bound of the official pooled SLU-F1 delta (the "
        f"guard) is not below -{H_SLU} pp -- each metric read at its own Fold A own-null half-width "
        f"(PLAN vs PLANr, {INSTRUMENT} section 2d). HARMFUL: a measured loss on either metric (CI95 "
        "upper bound below zero, decision 25). NEUTRAL-BY-WIDTH IS THE ADMISSION: a CI that includes "
        "zero and clears the margin is exactly the reading a base item requires (decision 127). The "
        "item is NEVER reported as a gain, whatever the point estimate; two base items are never assumed "
        "to add, and the cumulative check is the next composed round (decision 138). Every verdict "
        "carries the per-scenario table in both weightings, the frontier row (decision 75), the measured "
        "Reviewer prompt-token delta per contact and per row, the Reviewer contact rate, and a model-free "
        "count of Reviewer responses that narrate a tool call or a tool result on each arm (the downstream "
        f"failure {SUMMARY_DIAG} recorded)."
    )
    ceiling = (
        "What the repair unlocks (row 127 asks for the ceiling, not a gain): a Reviewer that is no longer "
        "instructed to perform an action it cannot perform and to review 'against' a tool result that does "
        "not exist -- the standing instruction to fabricate that the 2026-09-26 system-summary diagnostic "
        "traced downstream (summaries treating textual tool-result claims as execution while the tool event "
        "list is empty). It is the node-side precondition for the typed evidence link (G1/G2) and for any "
        "later Reviewer grounding, and it frees "
        f"{saving['tokens_per_reviewer_contact']} prompt tokens per Reviewer contact "
        f"({saving['tokens_per_row_at_the_sealed_plan_rate']:.2f} per row at the sealed PLAN rate, "
        f"{saving['tokens_per_1080_row_flight_at_the_sealed_plan_count']:,} per 1,080-row flight). No "
        "task-quality ceiling is claimed for it and none is needed under row 127."
    )

    measurement = {
        arm["run_id"]: {
            "admission": "no-harm",
            "claims_benefit": False,
            "expected_effect_pp": 0.0,
            "harm_margin_pp": H_SLU,
            "harm_margin_pp_by_metric": {"intent_accuracy": H_INTENT, "slu_f1": H_SLU},
            "measurement_design": "cross-flight-with-in-chain-replicate",
            "primary_metric": "intent accuracy (scenario_action exact), official pooled SLU-F1 the non-inferiority guard (owner decision 133)",
            "replicate_run_id": aa["run_id"],
            "rows": 1080,
            "note": (
                "A row-127 ENGINEERING-BASE item, admitted on NO HARM and never reported as a gain: expected_effect_pp is 0.0 "
                "because the cell registers no effect to look for, claims_benefit is false, and the harm margin is the "
                "measured floor of this design at n = 1,080 -- the Fold A own-null half-width of PLAN vs PLANr, SLU 1.2485 "
                "(the gate's single harm_margin_pp field, in the floor table's own unit) and intent 0.9943 (the primary "
                "metric's own half-width, applied by the read; harm_margin_pp_by_metric). The delta is read against the "
                "in-chain A/A replicate flown in the same chain (rule 3), never against the sealed comparator alone. The "
                "ceiling the item unlocks is stated in registered-facts-v1.json (ceiling_unlocked); it is a form ceiling, not "
                "a task-quality expectation. The read is neutral-by-width-is-admission (decision 127); a measured loss on "
                "either metric is HARMFUL (decision 25). Folded into the next composed round for the cumulative check "
                "(decision 138)."
            ),
        },
        aa["run_id"]: {
            "claims_benefit": False,
            "expected_effect_pp": 0.0,
            "measurement_design": "cross-flight-with-in-chain-replicate",
            "primary_metric": "intent accuracy (scenario_action exact) and official pooled SLU-F1, as the instrument",
            "replicate_run_id": arm["run_id"],
            "rows": 1080,
            "note": (
                "The A/A replicate is the INSTRUMENT, not a claim: it re-flies the locked plan's own form -- the OLD Reviewer "
                "instruction -- so the G5 delta is read against a within-chain null. Its expected effect is exactly zero by "
                "construction, and a non-zero read on it is a measurement of the instrument, which is what it is for."
            ),
        },
        smoke["run_id"]: {
            "claims_benefit": False,
            "expected_effect_pp": 0.0,
            "measurement_design": "form-proof",
            "primary_metric": "none (structural form only)",
            "rows": 4,
            "note": (
                "Four rows prove FORM and nothing else: that the repaired Reviewer instruction loads by its new relpath, "
                "that every request fits, that the Reviewer answers on its first contact with no tool call and that the "
                "episode completes. Scored by no one, read by no one; under the measurement instrument's rule 5 a batch of "
                "four rows can never be evidence of benefit or of harm."
            ),
        },
    }

    facts = {
        "schema": "saea-registered-facts-v1",
        "_note": (
            "Every model-free measured fact this registration rests on, and the CANONICAL stage3_measurement block "
            f"{GATE} resolves (keyed by run id; the arm's block is the no-harm declaration). The same block is repeated "
            "in the preregistration's fenced json for readability; this copy has precedence."
        ),
        "registered_at_utc": args.registered_at,
        "study_commit_at_registration": args.study_commit,
        "owner_decisions": {
            "127": "the ENGINEERING-BASE admission: sound logic, a stated ceiling, a no-harm reading at a preregistered margin equal to the design's measured floor; never reported as a gain",
            "135": "the defect is REAL and its deferral DELIBERATE until the AGREE read, so that one read never carries two prompt-byte changes",
            "138": "the cumulative harm check is folded into the optimisation rounds: every composed round's read against the lock IS the check",
            "153": "G5 is prepared now and flown in round 3 (the consumption-form round) as a row-127 no-harm item, folded into the following composed round; row 135's deferral is discharged by the AGREE read",
        },
        "rows": 1080,
        "stage3_measurement": measurement,
        "the_item": {
            "finding": (
                f"{AUDIT} section G5: the Reviewer's committed instruction opens by ordering it to call the task-contract "
                "tool 'exactly once through its native function schema' and to 'use only its returned source-bound result'; "
                "that toolkit is RETIRED and the audit confirms 0 tool schemas in all 2,590 contacts of the lock arm, so 52 of "
                "the instruction's 82 tokens (63 %) order an action the node cannot perform, and the same day's system-summary "
                "diagnostic records the downstream consequence: summaries treat textual tool-result claims as execution while "
                "the tool event list is empty."
            ),
            "retired_tool": {
                "what": "the Reviewer's task-contract toolkit saea-tool-task-contract-v1 (phase_tools.reviewer: mode native-tools, knowledge view text, source authority reviewer)",
                "retirement_record": E25_CITATION,
                "sealed_evidence": f"tool_calls {plan['run_manifest_cost']['tool_calls']} in the sealed PLAN run manifest cost block; 0 tool schemas in every lock-arm contact ({AUDIT} section 1)",
            },
            "repair": (
                "Delete the two sentences that order, describe and depend on the retired tool; add nothing; rephrase nothing. "
                "The surviving text is the audit's own 'review order' partition, byte for byte."
            ),
            "cost_sign": "negative: fewer prompt tokens per Reviewer contact, zero new bytes anywhere",
        },
        "instruction": {
            "old": receipt["instruction"]["old"],
            "new": receipt["instruction"]["new"],
            "deleted_clauses_verbatim": receipt["instruction"]["deleted_clauses_verbatim"],
            "kept_on_purpose": receipt["instruction"]["kept_on_purpose"],
            "deletion_only_proof": proof,
            "resolution": receipt["resolution"],
            "measurement_receipt": {"relpath": RECEIPT, "sha256": receipt_sha, "script": {"relpath": MEASURE_SCRIPT, "sha256": sha_file(MEASURE_SCRIPT)}},
        },
        "token_measurement": {
            "tokenizer": receipt["tokenizer"],
            "old_tokens_per_reviewer_contact": tokens["old_whole"],
            "retired_tool_order_tokens": tokens["old_retired_tool_order_head"],
            "retired_tool_share_pct": tokens["retired_tool_share_of_old_pct"],
            "reproduces_the_audit_82_and_52": tokens["reproduces_the_audit"],
            "new_tokens_per_reviewer_contact": tokens["new_whole"],
            "delta_per_reviewer_contact": tokens["delta_per_reviewer_contact"],
            "why_51_not_52": (
                "the audit priced the deleted HEAD on its own bytes (52); tokenised alone the surviving text costs 31, not "
                "82 - 52 = 30, because 'Then' at the start of a text is one token and ' Then' after a space is another. The "
                "saving on the wire is the standalone difference, 82 -> 31 = -51 per Reviewer contact; the 63 % is the "
                "audit's head-over-whole share, reproduced exactly."
            ),
            "variants_priced_not_applied": tokens["variants_priced_not_applied"],
            "sealed_plan_reviewer_contacts": plan["reviewer_contacts"],
            "sealed_plan_rows": plan["rows"],
            "sealed_plan_role_visits": plan["role_visits"],
            "sealed_plan_calls_used": plan["run_manifest_cost"]["calls_used"],
            "reviewer_contacts_per_row": plan["reviewer_contacts_per_row"],
            "saved_tokens_per_row": saving["tokens_per_row_at_the_sealed_plan_rate"],
            "saved_tokens_per_1080_row_flight": saving["tokens_per_1080_row_flight_at_the_sealed_plan_count"],
            "saved_share_of_sealed_plan_prompt_tokens": saving["share_of_the_sealed_plan_prompt_tokens_total"],
            "source_of_the_contact_rate": f"the sealed PLAN arm {COMPARATOR_RUN} / {COMPARATOR_ATTEMPT}: phases.json native_episode_receipt.role_visits (per-role identity of every contact) beside the run manifest cost block; ROLL-2 reported beside it in the receipt and not used",
        },
        "identity": {key: {k: v for k, v in ids[key].items() if k not in ("composed_config_diff_against_the_locked_plan_cell", "readiness")} for key in CELLS},
        "composed_config_diff_against_the_locked_plan_cell": {
            key: {
                **ids[key]["composed_config_diff_against_the_locked_plan_cell"],
                "parent_experiment": PARENTS[key],
                "phase_material_equal_except_reviewer_instruction_template": True,
            } for key in CELLS
        } | {
            "note": (
                "computed by flattening both composed configs (core.config.compose) and listing every path whose value "
                "differs: the one pin (arm and smoke; none on the A/A), the baseline's per-flight bookkeeping (this cell's "
                "FIT identities and cap, the dropped prepared_phase_supply, what_this_is) and the experiment fragment's own "
                f"block. The unit test {CONFIG_TEST} re-proves it."
            ),
        },
        "comparator": {
            "run_id": COMPARATOR_RUN, "attempt_id": COMPARATOR_ATTEMPT, "official": COMPARATOR_OFFICIAL,
            "never_reflown": True,
            "in_chain_replicate": {"run_id": aa["run_id"], "why": "rule 4 refuses a cross-flight contrast with no in-chain replicate; the A/A is the locked plan's own form re-flown in the SAME campaign chain"},
            "margins": {"h_slu": H_SLU, "h_intent": H_INTENT, "source": f"the plan's own null on this roster, PLAN vs PLANr ({PLANR_RUN}); {INSTRUMENT} section 2d"},
        },
        "no_harm_rule": no_harm_rule,
        "ceiling_unlocked": ceiling,
        "comp2_pin": {
            "note": (
                "Decision 153: G5 flies in round 3 and is folded into the composed round after it (COMP-2), so the repair is "
                "also prepared as a fragment COMP-2 can pin: one composed key, one relpath, one sha256 -- repository copy "
                "comp2-pin-v1.json in this package."
            ),
            "composed_key": THE_ONE_PIN,
            "value": NEW_TEMPLATE,
            "instruction_path": "configs/" + NEW_TEMPLATE,
            "instruction_sha256": new_sha,
            "replaces": {"value": OLD_TEMPLATE, "sha256": old_sha},
        },
        "byte_identity_expectation": {
            "sealed_plan_supply_output_sha256": PLAN_SUPPLY_OUTPUT_SHA,
            "claim": "the Reviewer instruction is not an input to the first-phase supply, so every supply the flip mints for this family must carry this output digest on all 1,080 rows (the smoke on its four); a different digest means the knowledge channel moved -- stop and report",
        },
        "budget_arithmetic": {
            "caps_are_the_agree_arithmetic": True,
            "arm_and_aa_family_budget": caps,
            "smoke_family_budget": smoke_caps,
            "derivation": [
                "generation_calls_cap = 1,080 rows x 11 contacts per row (perception 1, solver 1, reviewer 3, planner 1, max_revisions 1 -> 1 + 2 * (3 + 1 + 1)) = 11,880; the A/A the same; the smoke 4 x 11 = 44",
                "fit_endpoint_calls_cap = 4 x generation = 47,520 (smoke 176); native_task_contract_calls_cap = 1,080 x 6 = 6,480 (smoke 24); repeated_speech_audio_seconds_cap 33,930 (smoke 117); gpu_hours_fit_inclusive 12.0 (smoke 1.0), the locked family's own ceilings",
                f"expected spend per 1,080-row cell at the sealed PLAN arm's own realized rate: about {plan['run_manifest_cost']['calls_used']:,} contacts ({plan['run_manifest_cost']['calls_used'] / 1080:.3f} per row) and about 3.7 GPU hours; the arm's Reviewer prefill is {saving['tokens_per_reviewer_contact']} tokens per contact lighter, about {saving['tokens_per_1080_row_flight_at_the_sealed_plan_count']:,} tokens per flight ({100 * saving['share_of_the_sealed_plan_prompt_tokens_total']:.3f} % of the sealed PLAN prompt total) -- no cap is denominated in tokens, so 'minus the saved tokens' moves no cap and widens the FIT margin against the 24,576-token slot",
                "official_complete_scoring_jobs = 1 per 1,080-row cell, one job over the complete manifest through core.scoring_batch, never sharded; the smoke is never scored",
            ],
            "run_cumulative": "every cap binds across ALL attempts of a run id, so the one permitted recovery re-registration spends from the same ceiling",
        },
        "committed_artifacts": {
            "repaired_instruction": {"relpath": "configs/" + NEW_TEMPLATE, "sha256": new_sha},
            "prepared_phase_supply": (
                "NONE COMMITTED, by design: the flip mints each cell's own under its own run id (item E16), the readiness "
                "requirements list is empty, and --allow-output-change must never be passed."
            ),
        },
        "prohibitions": [
            "Never reported as a gain: a no-harm item is admitted on the reading and two base items are never assumed to add (decision 127).",
            "No test-split, Fold B or DEV contact or read.",
            "No re-flying of the sealed comparator.",
            "No second factor: no other template, knob, store, release, snapshot, roster, geometry or session change; the 211 committed configs are NOT re-pinned to the repaired instruction -- COMP-2 pins it (decision 153).",
            "No paper-scale profile.",
            "No flight before root mints the decision receipt and the cells are flipped.",
        ],
        "authority_relpaths": [AUDIT, AUDIT_SCRIPT, SUMMARY_DIAG, INSTRUMENT, OWNER_DECISIONS, NOTOOL_VERDICT, HARNESS_RECEIPT, AGREE_PACKAGE + "/README.md", GATE],
    }
    facts_sha = wjson(PACKAGE + "/registered-facts-v1.json", facts)

    protocol = {
        "schema": "saea-registered-protocol-v1",
        "protocol_id": "slurp-stage3-g5-fold-a-protocol-v1",
        "registered_at_utc": args.registered_at,
        "study_commit_at_registration": args.study_commit,
        "source_tree": f"studies/speech-aware-evidence-acquisition, worktree {args.worktree}, branch {args.branch}",
        "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP",
        "the_question": (
            "With the two sentences ordering the retired task-contract tool deleted from the Reviewer's instruction and "
            "nothing else changed, do the official intent accuracy and pooled SLU-F1 on TRAIN Fold A 1,080 stay within the "
            "plan's own null, read against an in-chain A/A? (A no-harm question; the item's value is the removal of a "
            "standing order to fabricate and its negative token cost, stated as a ceiling, never as a gain.)"
        ),
        "one_factor": facts["the_item"]["repair"] + " Composed key " + THE_ONE_PIN + ": " + OLD_TEMPLATE + " -> " + NEW_TEMPLATE + f" (sha256 {new_sha}).",
        "unchanged": (
            "everything but that pin and per-flight bookkeeping: the roster (TRAIN Fold A 1,080, split identity "
            f"{arm['split_identity_hash']}), the model fragment and serving geometry (np4 x 24,576), the session {SESSION}, "
            "the phase program and its 11-contact ceiling, all three knowledge stores and their release/snapshot pins, the "
            "exemplar k of 20, the role graph, the response formats, every other instruction template, the task contract, "
            "the deliver normaliser, the scorers and every budget"
        ),
        "cells": {key: {k: ids[key][k] for k in ("cell", "experiment", "run_id", "attempt_id", "rows", "composed_config_hash", "protocol_hash", "split_identity_hash", "reviewer_instruction_template")} | {"fit_run_id": ids[key]["fit"]["run_id"], "fit_attempt_id": ids[key]["fit"]["attempt_id"]} for key in CELLS},
        "comparator": facts["comparator"],
        "decision_rule_fixed_here": no_harm_rule,
        "ceiling_unlocked": ceiling,
        "what_a_harmful_read_would_mean": (
            "That the Reviewer's behaviour depended on the stale order in a way the audit did not predict -- which would "
            "itself be a finding about the node, reported with the tool-narration count beside it -- and the repair is "
            "withdrawn from COMP-2 pending a root cause. A NEUTRAL read is the admission, not a failure, and is never "
            "written as 'no gain'."
        ),
        "model_free_proofs_landed_before_contact": {
            "token_measurement": facts["token_measurement"],
            "deletion_only": proof,
            "composed_config_diff": facts["composed_config_diff_against_the_locked_plan_cell"],
        },
        "development_numbers_only": "Every number this family will produce is a TRAIN Fold A construction-fold development number (owner decisions 28 and 86) and is never a test claim.",
        "failure_policy": "Stop and preserve on the first failure. AT MOST ONE root-diagnosed recovery re-registration; a second failure closes the cell and the fix is proven on a four-row dry run. The budget is run-cumulative across attempts.",
        "authority": (
            f"owner decisions 127, 135, 138 and 153 ({OWNER_DECISIONS}); the audit {AUDIT} (G5) and its script {AUDIT_SCRIPT}; "
            f"the retirement record {E25_CITATION}; the measurement instrument {INSTRUMENT} (rules 3 and 4, section 2d); "
            f"the AGREE chain shape {AGREE_PACKAGE}; owner decisions 25 (measured loss), 28 and 86 (development numbers), "
            "101 (the Stage-3 algorithm label), 133 (intent primary)"
        ),
        "prohibitions": facts["prohibitions"],
    }
    protocol_sha = wjson(PACKAGE + "/protocol-registered-v1.json", protocol)

    plan_shas: dict[str, str] = {}
    for key in ("arm", "aa", "smoke"):
        identity = ids[key]
        budget = identity["family_budget"]
        for kind in ("generation", "fit"):
            is_fit = kind == "fit"
            run_id = identity["fit"]["run_id"] if is_fit else identity["run_id"]
            plan_doc = {
                "schema": f"saea-registered-{kind}-plan-v1",
                "plan_kind": kind,
                "cell": identity["cell"],
                "experiment": identity["experiment"],
                "composed_config_hash": identity["composed_config_hash"],
                "registered_at_utc": args.registered_at,
                "status": protocol["status"],
                "source_tree": protocol["source_tree"],
                "preparation_base_commit": args.study_commit,
                "expected_session_id": SESSION,
                "unused_budget_is_not_attempt_authority": True,
                "execution_plan": {
                    "schema": "saea-execution-plan-v1",
                    "study": "speech-aware-evidence-acquisition",
                    "carrier_lock_key": identity["carrier_lock_key"],
                    "run_id": run_id,
                    "attempt_id": identity["fit"]["attempt_id"] if is_fit else identity["attempt_id"],
                    "execution_profile": identity["execution_profile"],
                    "split_role": "discovery",
                    "split_identity_hash": identity["split_identity_hash"],
                    "protocol_hash": identity["protocol_hash"],
                    "planned_model_calls": budget["fit_endpoint_calls_cap"] if is_fit else budget["generation_calls_cap"],
                    "planned_speech_audio_seconds": budget["repeated_speech_audio_seconds_cap"],
                    "planned_gpu_hours": budget["gpu_hours_fit_inclusive"],
                },
                "family_budget": budget,
                "execution_route": (
                    "The shared core.flight.cli FIT path under this cell's own native_contact_fit ids; it measures request envelopes and produces no generation."
                    if is_fit else
                    "Shared core.flight.cli campaign over the committed campaign plan configs/campaign/slurp-native-stage3-g5-fold-a-v1.json, which carries the A/A replicate AND the G5 arm so the two fly in ONE chain; the campaign acquires its own GenerationLease against the resident session and schedules one official score per generation cell at finalize."
                    if key != "smoke" else
                    "Shared core.flight.cli worker on this cell alone; the smoke is deliberately outside the campaign plan and is never scored."
                ),
                "prepared_phase_supply": {
                    "relpath": f"prepared/{identity['run_id']}/phase-supply-v1.json",
                    "sha256": "MINTED_AT_THE_FLIP",
                    "expected_output_sha256": PLAN_SUPPLY_OUTPUT_SHA,
                    "note": facts["committed_artifacts"]["prepared_phase_supply"] + " " + facts["byte_identity_expectation"]["claim"],
                },
                "protocol_document": {"relpath": PACKAGE + "/protocol-registered-v1.json", "sha256": protocol_sha},
                "one_factor": protocol["one_factor"],
                "purpose": (
                    f"{run_id}: {FLIGHT_PROSE[key]}. "
                    + ("It measures request envelopes only and reads nothing." if is_fit
                       else no_harm_rule if key == "arm"
                       else "It supplies the within-chain null the G5 no-harm read is taken at and makes no claim of its own." if key == "aa"
                       else "Structural form proof only: no score and no read.")
                ),
                "quality_read_gate": (
                    "No task-quality read before the complete sealed manifest, the exact ordered outputs, the native phase summary and the single successful complete official TRAIN score all exist for BOTH the G5 arm and its in-chain A/A replicate. A verdict computed against the sealed comparator alone is refused."
                ),
            }
            name = f"{PREFIX[key]}{kind}-plan-registered-v1.json"
            plan_shas[run_id] = wjson(f"{PACKAGE}/{name}", plan_doc)

    recipe = {
        "schema": "saea-slurp-paired-analysis-recipe-v1",
        "recipe_id": "slurp-stage3-g5-fold-a-paired-analysis-v1",
        "title": "Cell G5 -- the standard paired roster read on intent + SLU against the sealed PLAN arm, at the in-chain A/A null flown beside it, under the no-harm rule",
        "registered_at_utc": args.registered_at,
        "arms": {
            "arm": {"run_id": arm["run_id"], "attempt_id": arm["attempt_id"], "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL", "outputs_sha256": "PENDING_SEAL"},
            "in_chain_replicate": {"run_id": aa["run_id"], "attempt_id": aa["attempt_id"], "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL", "outputs_sha256": "PENDING_SEAL", "role": "the within-chain null the delta is read at"},
            "comparator": {"run_id": COMPARATOR_RUN, "attempt_id": COMPARATOR_ATTEMPT, "role": "gating comparator, sealed, never re-flown"},
        },
        "resampling": {"bootstrap_draws": 10000, "metrics": ["scenario_action_exact", "slu_f1_f1"], "seed": 20260927, "unit": "row (paired)"},
        "decision_rule": no_harm_rule,
        "margins": {"h_intent": H_INTENT, "h_slu": H_SLU},
        "steps": [
            "1. Refuse unless BOTH the G5 arm and the in-chain A/A carry a COMPLETE sealed manifest at 1,080 rows with the committed roster's ids, each with one successful complete official TRAIN score, and their config hashes are this package's (the arm flew the repaired instruction, the A/A the old one).",
            "2. Structural stage: on both arms, 0 tool schemas and 0 tool calls on every contact; the Reviewer contact rate per row; the Reviewer prompt tokens per contact from the sealed COST records, whose arm-minus-A/A difference must sit at the measured -51 (a boundary token of tolerance); and a model-free count of Reviewer responses on each arm whose text narrates a tool call or a tool result (counts only, no text persisted).",
            "3. Score once per arm over the complete manifest with the dataset's standard scorer (slurp-slu-official-train through core.scoring_batch, never sharded); take per row scenario_action_exact and the per-row SLU-F1 contributions.",
            "4. Paired row bootstrap (10,000 draws, seed 20260927) of the arm minus in-chain A/A delta on intent accuracy and on official pooled SLU-F1; report the point estimate and CI95 of each; report the same paired delta against the sealed PLAN comparator BESIDE it, never instead of it.",
            f"5. Apply the no-harm rule: ADMITTED iff the intent lower bound >= -{H_INTENT} and the SLU lower bound >= -{H_SLU}; HARMFUL iff either upper bound < 0 (decision 25); otherwise NOT ADMITTED (width). Never write 'gain' or 'no gain'.",
            "6. Report beside every number: the per-scenario table in the natural-mixture and equal-stratum weightings; the frontier row (decision 75); the measured token delta per Reviewer contact and per row; the tool-narration counts of step 2; and the A/A's own delta against the sealed comparator as the instrument's reading.",
            "7. Hand the admitted pin (comp2-pin-v1.json) to COMP-2 for the cumulative check (decision 138); an unadmitted pin is withdrawn from COMP-2 with the tool-narration counts as the first root-cause lead.",
        ],
        "read_driver_family": READ_DRIVER_FAMILY,
        "output": {"analysis_root": "analysis/SAEA-SLURP-STAGE3-G5-FOLD-A-PAIRED-ANALYSIS-V1"},
        "boundary": "A development read on a TRAIN construction fold (owner decisions 28 and 86); never a test claim, never a generalisation claim, and it admits nothing beyond the no-harm entry it is registered for. No utterance text, transcript, gold label or model output is printed or persisted.",
    }
    recipe_sha = wjson(PACKAGE + "/analysis-recipe-v1.json", recipe)

    comp2 = {
        "schema": "saea-comp2-pin-fragment-v1",
        "item": "G5 -- the Reviewer instruction with the retired-tool order deleted",
        "composed_key": THE_ONE_PIN,
        "value": NEW_TEMPLATE,
        "instruction_path": "configs/" + NEW_TEMPLATE,
        "instruction_sha256": new_sha,
        "replaces": {"value": OLD_TEMPLATE, "sha256": old_sha},
        "tokens_per_reviewer_contact": {"old": tokens["old_whole"], "new": tokens["new_whole"], "delta": tokens["delta_per_reviewer_contact"]},
        "admission_state": "PREPARED, not admitted: pin into COMP-2 only after the round-3 no-harm read (decision 153; cumulative check under decision 138)",
        "how_to_pin": "set phase_material.reviewer.instruction_template to the value above in the COMP-2 baseline; nothing else moves",
    }
    comp2_sha = wjson(PACKAGE + "/comp2-pin-v1.json", comp2)

    eligible = [arm["run_id"], arm["fit"]["run_id"], aa["run_id"], aa["fit"]["run_id"], smoke["run_id"], smoke["fit"]["run_id"]]
    draft = {
        "_draft_note": (
            "A DRAFT written by the registration agent, in the repository, for root to mint on the data root with "
            "scripts/flights/g5/g5_mint_receipt.py, which sets status 'decided', stamps recorded_at_utc, re-hashes every "
            "antecedent path at mint time and refuses to overwrite. It authorises nothing while its status is not 'decided' "
            "(core.flight.campaign.declared_readiness refuses it)."
        ),
        "schema": "saea-campaign-decision-v1",
        "decision_id": DECISION_ID,
        "status": "DRAFT-NOT-MINTED",
        "recorded_at_utc": None,
        "owner": "root",
        "coordinator": "Fable5.1",
        "eligible_run_ids": eligible,
        "cell_kind": "Stage-3 engineering-base no-harm item (label none). One arm on TRAIN Fold A 1,080, its in-chain A/A replicate in the same chain, and a four-row form smoke outside the chain.",
        "decision": (
            "Fly the G5 family: the locked PLAN plan with the Reviewer node's instruction template moved to the file that "
            "deletes the two sentences ordering the task-contract tool retired as item E25 (nothing added), against the sealed "
            "PLAN arm read at the in-chain A/A flown in the same chain. Admission is NO HARM at the plan's own Fold A half-widths "
            f"(intent {H_INTENT}, SLU {H_SLU}); the item is never reported as a gain and is folded into the next composed round."
        ),
        "authorization_basis": (
            f"Owner decision 153 (G5 prepared now, flown in round 3 as a row-127 no-harm item), 127 (the engineering-base "
            f"admission), 135 (deferral discharged by the AGREE read) and 138 (cumulative check in the composed round); the "
            f"audit {AUDIT} G5; standing: 25, 28, 86, 101, 116, 133, 77, and the binding instrument note {INSTRUMENT}."
        ),
        "antecedents": {
            "owner_decisions": {"path": OWNER_DECISIONS, "sha256": sha_file(OWNER_DECISIONS)},
            "audit_note": {"path": AUDIT, "sha256": sha_file(AUDIT)},
            "retirement_record": {"path": HARNESS_RECEIPT, "sha256": sha_file(HARNESS_RECEIPT)},
            "instrument_note": {"path": INSTRUMENT, "sha256": sha_file(INSTRUMENT)},
            "preregistration": {"path": PREREG, "sha256": None},
            "readiness_readme": {"path": PACKAGE + "/README.md", "sha256": None},
            "protocol": {"path": PACKAGE + "/protocol-registered-v1.json", "sha256": protocol_sha},
            "registered_facts": {"path": PACKAGE + "/registered-facts-v1.json", "sha256": facts_sha},
            "analysis_recipe": {"path": PACKAGE + "/analysis-recipe-v1.json", "sha256": recipe_sha},
            "token_measurement": {"path": RECEIPT, "sha256": receipt_sha},
            "comp2_pin": {"path": PACKAGE + "/comp2-pin-v1.json", "sha256": comp2_sha},
            "repaired_instruction": {"path": "configs/" + NEW_TEMPLATE, "sha256": new_sha},
            "config_proof": {"path": CONFIG_TEST, "sha256": sha_file(CONFIG_TEST) if Path(CONFIG_TEST).is_file() else None},
            "base_cell": f"the LOCKED default plan, cell PLAN ({COMPARATOR_RUN}, v2.0 lock 2026-09-22): G5 is that fragment with one pin moved",
            "clause_comparator": f"the sealed PLAN arm {COMPARATOR_RUN}, never re-flown, read at the in-chain A/A {aa['run_id']}",
            "registration_base_commit": args.study_commit,
        },
        "budget": {
            **{k: caps[k] for k in sorted(caps)},
            "smoke": smoke_caps,
            "paid_api_calls": 0,
            "expected_contacts_per_1080_row_cell": plan["run_manifest_cost"]["calls_used"],
            "ceiling_note": "11 contacts per row = 1 + 2 x (1 + 3 + 1) at max_revisions 1; 12.0 GPU-h per 1,080-row cell is a ceiling (the sealed PLAN arm realized about 3.7 h); the Reviewer prefill is 51 tokens per contact lighter on the arm",
            "plan_budget_is_run_cumulative": True,
        },
        "claim_boundary": "No superiority, generalisation, component-causal, held-out, confirmatory or paper-scale claim of any kind; a no-harm admission of one engineering-base item, never reported as a gain.",
        "failure_policy": protocol["failure_policy"],
        "not_authorized": [
            "any flight before the cells are flipped and the receipt is minted",
            "touching the resident np4 session by anyone but the coordinator",
            "any ASR, transcript, encoder or paid-API contact",
            "re-flying or re-scoring any sealed cell",
            "--allow-output-change on the re-pin tool",
            "any change beyond the one registered pin; re-pinning the 211 committed configs (COMP-2 pins it after the read, decision 153)",
            "reporting the item as a gain",
        ],
        "population": {"count": 1080, "split_identity_hash": arm["split_identity_hash"], "split_role": "discovery", "partition": "TRAIN Fold A 1,080, the locked roster", "fold_b_contact_authorized": False, "test_contact_authorized": False},
        "prepared_phase_supply": {"note": "minted by scripts/flights/repin_cell.py at the flip (each cell's own, item E16); not pinned by this receipt; expected output digest " + PLAN_SUPPLY_OUTPUT_SHA},
        "registered_hashes": {"note": f"the values of the fragments exactly as committed at {args.study_commit} (readiness held, no decision requirement); repin_cell.py recomputes them at the flip.",
                              **{key: {"composed_config": ids[key]["composed_config_hash"], "protocol": ids[key]["protocol_hash"]} for key in CELLS}},
        "service": {"expected_session_id": SESSION, "model_fragment": arm["model_fragment"], "slots": 4, "slot_tokens": 24576, "decoder_only": True, "mmproj": "absent", "no_child_start_stop": True, "note": "the resident SLURP np4 session; the flight attaches only, never spawns or stops"},
    }
    draft_sha = wjson(PACKAGE + "/root-admission-draft-v1.json", draft)

    fence = json.dumps({"stage3_measurement": measurement}, indent=2, ensure_ascii=False, sort_keys=True)
    readme = f"""# Cell G5: the Reviewer instruction that orders a retired tool, repaired

Registered before contact {args.registered_at[:10]} at study commit `{args.study_commit}` (owner decisions 135 and 153,
a row-127 no-harm item for round 3); all three cells **held**. Nothing here authorises a flight, a flip or an
admission entry.

**The defect.** [`{AUDIT}`](../../results/{Path(AUDIT).name}) section G5: the locked PLAN plan's Reviewer
instruction (`configs/{OLD_TEMPLATE}`, resolved from the composed config at `{THE_ONE_PIN}`) opens by ordering
the Reviewer to call a task-contract tool "exactly once through its native function schema" and to "use only its
returned source-bound result". That toolkit was **RETIRED as item E25** -- `{HARNESS_RECEIPT}`, the entry with row
`SAEA-SLURP-NATIVE-EXEMPLARS-K20-NOTOOL-V1`, status `RETIRED`, switch class `phase_tools`, after
[`{NOTOOL_VERDICT}`](../../results/{Path(NOTOOL_VERDICT).name}) (decisions 55, 56, 61) -- and the locked plan renders
0 tool schemas in every contact (`tool_calls` {plan['run_manifest_cost']['tool_calls']} in the sealed PLAN cost block).
The same day's summary diagnostic recorded the consequence: summaries treating a Reviewer's textual tool-result
claims as execution while the tool event list is empty. Decision 135 deferred the repair so that the AGREE read
would carry one prompt-byte change, not two; decision 153 admits it now.

**The measurement, reproduced** (`{MEASURE_SCRIPT}` -> [`instruction-token-measurement-v1.json`](instruction-token-measurement-v1.json),
the audit's own vocab-only `llama-tokenize` and the audit's own split at "Then review"; zero model, server, encoder
or scorer contacts): the whole instruction is **{tokens['old_whole']}** tokens, the retired-tool order **{tokens['old_retired_tool_order_head']}**
-- {tokens['old_retired_tool_order_head']} / {tokens['old_whole']} = **{tokens['retired_tool_share_of_old_pct']} %**, the audit's 63 % exactly. The surviving text tokenised on its own
costs **{tokens['new_whole']}** (not 82 - 52 = 30: "Then" at the start of a text is a different token from " Then" after a
space), so the wire saving is **-{saving['tokens_per_reviewer_contact']} tokens per Reviewer contact**. The sealed PLAN arm
(`{COMPARATOR_RUN}`) made **{plan['reviewer_contacts']:,} Reviewer contacts on {plan['rows']:,} rows**
({plan['reviewer_contacts_per_row']:.4f} per row; role visits {json.dumps(plan['role_visits'])}, run-manifest `calls_used`
{plan['run_manifest_cost']['calls_used']:,}), so the saving is **{saving['tokens_per_row_at_the_sealed_plan_rate']:.2f} tokens per row** and
**{saving['tokens_per_1080_row_flight_at_the_sealed_plan_count']:,} per 1,080-row flight** ({100 * saving['share_of_the_sealed_plan_prompt_tokens_total']:.3f} % of the arm's
{plan['run_manifest_cost']['prompt_tokens_total']:,} prompt tokens). No cap is denominated in tokens, so no cap moves.

**The repaired instruction.** `configs/{NEW_TEMPLATE}` (sha256 `{new_sha}`) is the old file with the two sentences
that order, describe and depend on the retired tool deleted and NOTHING added: word-level diff = `equal` and
`delete` opcodes only ({proof['word_level']['deleted_words']} of {proof['word_level']['old_words']} words deleted, {proof['word_level']['new_words']} kept in order), and old == deleted head +
new byte for byte. Two words a reader might also cut are KEPT on purpose and priced in the receipt: "Then" (deleting
it forces a case change, which is a rephrase) and "or invent a tool result" (it forbids fabricating a tool result --
the very failure the diagnostic recorded -- and neither orders nor depends on the tool).

**One pin, proven.** Arm and smoke: `{THE_ONE_PIN}` `{OLD_TEMPLATE}` -> `{NEW_TEMPLATE}`; the composed-config diff
against the locked PLAN cells (`registered-facts-v1.json`, `composed_config_diff_against_the_locked_plan_cell`) is that
pin plus bookkeeping only (each cell's FIT identities and cap, no committed `prepared_phase_supply`, `what_this_is`).
The in-chain A/A is the locked form with the OLD instruction and bookkeeping alone. `phase_tools` is absent everywhere.
`{CONFIG_TEST}` re-proves all of it.

**Three cells, one chain (the AGREE shape).** `configs/campaign/slurp-native-stage3-g5-fold-a-v1.json` carries the A/A
and the arm, because a cross-flight contrast with no in-chain replicate is refused outright (instrument rule 4); the
four-row smoke is outside the plan and never scored. If round 3 flies several consumption-form items in one chain, ONE
A/A can serve them all: drop this family's A/A from the campaign plan before the flip, re-point `replicate_run_id`,
and mint with `g5_mint_receipt.py --drop-aa`.

**`stage3_measurement`.** The arm declares `admission` **`no-harm`** with `harm_margin_pp` **{H_SLU}** (the gate's single
field, SLU, the design's measured floor at n = 1,080) and `harm_margin_pp_by_metric` intent **{H_INTENT}** / SLU **{H_SLU}**
(the Fold A own-null half-widths of PLAN vs PLANr, instrument section 2d), `claims_benefit` false, `expected_effect_pp`
0.0, `measurement_design` `cross-flight-with-in-chain-replicate`, `replicate_run_id` `{aa['run_id']}`. `{GATE}` reads a
no-harm margin against the design's SAMPLING half-width (decision 127's own numbers), not against the rule-3 benefit
bar. **The rule:** admitted iff the intent CI95 lower bound against the in-chain A/A is not below -{H_INTENT} and the SLU
lower bound not below -{H_SLU}; HARMFUL on a measured loss; never reported as a gain.

**`stage3_algorithm`.** `none`: a deletion is not a policy search.

**COMP-2.** Decision 153 folds G5 into the composed round after round 3, so the pin is also prepared as a fragment:
[`comp2-pin-v1.json`](comp2-pin-v1.json) -- key `{THE_ONE_PIN}`, value `{NEW_TEMPLATE}`, sha256 `{new_sha}`.

| file | what it holds |
| --- | --- |
| `../{Path(PREREG).name}` | the preregistration proper, including the `stage3_measurement` fence |
| `instruction-token-measurement-v1.json` | the reproduced measurement, the deletion-only proof, the sealed Reviewer contact rate |
| `registered-facts-v1.json` | every model-free fact, the one-pin diffs, the CANONICAL `stage3_measurement` |
| `protocol-registered-v1.json` | identities, hashes, budgets, the no-harm rule, the claim boundary |
| `generation-plan-registered-v1.json` / `fit-plan-registered-v1.json` | the arm's two plans |
| `aa-generation-plan-registered-v1.json` / `aa-fit-plan-registered-v1.json` | the in-chain A/A's plans |
| `smoke-generation-plan-registered-v1.json` / `smoke-fit-plan-registered-v1.json` | the four-row smoke's plans |
| `analysis-recipe-v1.json` | the standard paired roster read on intent + SLU under the no-harm rule |
| `comp2-pin-v1.json` | the fragment COMP-2 pins |
| `root-admission-draft-v1.json` | the decision receipt root mints with `scripts/flights/g5/g5_mint_receipt.py` |

**Budgets, as arithmetic (AGREE's).** Arm and A/A each: {caps['generation_calls_cap']:,} generation contacts (1,080 x 11, run-cumulative),
{caps['fit_endpoint_calls_cap']:,} FIT endpoints, {caps['native_task_contract_calls_cap']:,} native task-contract calls, {caps['repeated_speech_audio_seconds_cap']:,} repeated speech
seconds, {caps['gpu_hours_fit_inclusive']} GPU hours, one official complete score. Smoke: {smoke_caps['generation_calls_cap']} / {smoke_caps['fit_endpoint_calls_cap']} / {smoke_caps['native_task_contract_calls_cap']} / {smoke_caps['repeated_speech_audio_seconds_cap']} / {smoke_caps['gpu_hours_fit_inclusive']}, never
scored. Expected spend per 1,080-row cell about {plan['run_manifest_cost']['calls_used']:,} contacts and about 3.7 GPU hours at the sealed PLAN
arm's own rate, the arm minus {saving['tokens_per_1080_row_flight_at_the_sealed_plan_count']:,} prefill tokens.

**No committed `prepared_phase_supply`, and empty requirements lists.** The flip mints each cell's own first-phase
supply under its own run id (item E16) and appends the requirement; `--allow-output-change` must never be passed. The
Reviewer instruction is not an input to the supply, so every minted supply must carry the sealed PLAN output digest
`{PLAN_SUPPLY_OUTPUT_SHA}` -- the flip's byte-identity check.

**Mint, flip, queue.** Root countersigns the seven DRAFT exposure rows (six flight rows and
`{MEASUREMENT_ROW}`), mints `{DECISION_RELPATH}` (id `{DECISION_ID}`, six eligible run ids) with
`scripts/flights/g5/g5_mint_receipt.py`, flips with `scripts/flights/g5/g5_flip.sh` (the generic re-pin loop over
`g5_repin_smoke.sh`, `g5_repin_aa.sh`, `g5_repin_arm.sh`, converged at one HEAD), then queues
`scripts/flights/g5/batch_chain_g5.sh` behind whatever occupies the np4 session (decision 77).

**Not authorised by this package.** No flight before the receipt is minted and the cells are flipped; no contact by
this registration; no re-flying of the comparator; no test-split, Fold B or DEV read; no second factor; no re-pin of
the 211 committed configs; no report of a gain; no admission entry.
"""
    readme_sha = wr(PACKAGE + "/README.md", readme)

    prereg_text = f"""# Cell G5: preregistration

Registered {args.registered_at[:10]} at study commit `{args.study_commit}`, before any contact, from the locked PLAN
fragments by script (decision 58) with one pin moved, under owner decisions 127, 135, 138 and 153. Development
numbers only (owner decisions 28 and 86); never a test claim.

## The cell

| item | value |
| --- | --- |
| base | the locked v2.0 plan, the sealed PLAN arm `{COMPARATOR_RUN}` ({COMPARATOR_OFFICIAL['slu_f1']} / {COMPARATOR_OFFICIAL['intent_accuracy']}) |
| factor | `{THE_ONE_PIN}`: `{OLD_TEMPLATE}` -> `{NEW_TEMPLATE}` (sha256 `{new_sha}`) -- the two sentences ordering the task-contract tool retired as item E25 deleted, nothing added, nothing rephrased (deletion-only, proven word by word); {tokens['old_whole']} -> {tokens['new_whole']} tokens per Reviewer contact ({tokens['old_retired_tool_order_head']} / {tokens['old_whole']} = {tokens['retired_tool_share_of_old_pct']} % of the old instruction was the retired order) |
| unchanged | roster (TRAIN Fold A 1,080), geometry (np4 x 24,576), session, program and its 11-contact ceiling, all three stores and their pins, exemplar k = 20, role graph, every other template, normaliser, scorers, budgets; `phase_tools` absent |
| comparator | `{COMPARATOR_RUN}`, sealed, never re-flown |
| in-chain replicate | `{aa['run_id']}`, the locked form with the OLD instruction re-flown in the SAME campaign chain |
| admission | NO HARM (owner decision 127): intent CI95 lower bound against the in-chain A/A not below -{H_INTENT}, SLU lower bound not below -{H_SLU} (the plan's own Fold A null, PLAN vs PLANr); never reported as a gain |
| ceiling unlocked | a Reviewer no longer ordered to perform an impossible action and to fabricate its result; -{saving['tokens_per_reviewer_contact']} prompt tokens per Reviewer contact, {saving['tokens_per_row_at_the_sealed_plan_rate']:.2f} per row at the sealed PLAN rate |
| smoke | four engineering rows, structural acceptance, never scored |
| runs | `{arm['run_id']}` / `{arm['fit']['run_id']}`; `{aa['run_id']}` / `{aa['fit']['run_id']}`; `{smoke['run_id']}` / `{smoke['fit']['run_id']}` |
| composed config hashes | arm `{arm['composed_config_hash']}`; A/A `{aa['composed_config_hash']}`; smoke `{smoke['composed_config_hash']}` |
| protocol hashes | arm `{arm['protocol_hash']}`; A/A `{aa['protocol_hash']}`; smoke `{smoke['protocol_hash']}` |
| split identity | arm and A/A `{arm['split_identity_hash']}`; smoke `{smoke['split_identity_hash']}` |
| authority | owner decisions 127, 135, 138, 153 ({OWNER_DECISIONS}); {AUDIT} (G5); {E25_CITATION} {INSTRUMENT} (rules 3 and 4, section 2d); the AGREE chain shape {AGREE_PACKAGE}; decisions 25, 28, 86, 101, 133 |

## Decision rule (fixed here)

{no_harm_rule}

## The measurement declaration

```json
{fence}
```

The arm's block is a NO-HARM declaration: `admission` `no-harm`, `harm_margin_pp` {H_SLU} (the gate's single field,
in the floor table's SLU unit, equal to this design's measured floor at n = 1,080) with `harm_margin_pp_by_metric`
intent {H_INTENT} / SLU {H_SLU} applied by the read, `claims_benefit` false, `expected_effect_pp` 0.0, and the in-chain
replicate named. `{GATE}` compares a no-harm margin with the design's SAMPLING half-width (decision 127's own
numbers), never with the rule-3 benefit bar a gain must exceed.

## What the item is, and what it is not

{facts['the_item']['finding']}

{ceiling}

It is not a mechanism, not a gain and not a component-causal claim. Two base items are never assumed to add; the
cumulative check is the next composed round (decision 138), which is why the pin is also prepared as
`comp2-pin-v1.json` for COMP-2 (decision 153).

## Budgets and failure rule

Arm and A/A each {caps['generation_calls_cap']:,} generation contacts (run-cumulative), {caps['fit_endpoint_calls_cap']:,} FIT endpoints,
{caps['repeated_speech_audio_seconds_cap']:,} repeated speech seconds, {caps['gpu_hours_fit_inclusive']} GPU hours, one official complete score; smoke
{smoke_caps['generation_calls_cap']} / {smoke_caps['fit_endpoint_calls_cap']} / {smoke_caps['repeated_speech_audio_seconds_cap']} / {smoke_caps['gpu_hours_fit_inclusive']}, never scored -- the AGREE arithmetic; the arm's Reviewer
prefill is {saving['tokens_per_reviewer_contact']} tokens per contact lighter and no cap is denominated in tokens. Expected spend per 1,080-row cell
about {plan['run_manifest_cost']['calls_used']:,} contacts and about 3.7 GPU hours at the sealed PLAN arm's own rate. Stop and preserve on the
first failure. AT MOST ONE root-diagnosed recovery re-registration; a second failure closes the cell and the fix is
proven on a four-row dry run.

## Prohibitions

Never reported as a gain. No paper-scale profile. No confirmatory or test-split contact. No Fold B or DEV read. No
re-flying of the sealed comparator. No second factor and no knob change; the 211 committed configs are not re-pinned.
No flight before root mints the decision receipt and the cells are flipped, and `--allow-output-change` is never
passed.
"""
    prereg_sha = wr(PREREG, prereg_text)

    ledger_state = "not-requested"
    if args.append_ledger:
        ledger_state = append_ledger(args, ids=ids, plan_shas=plan_shas, receipt=receipt, receipt_sha=receipt_sha, new_sha=new_sha, old_sha=old_sha)

    print(json.dumps({
        "package": PACKAGE,
        "written": {"README.md": readme_sha, "registered-facts-v1.json": facts_sha, "protocol-registered-v1.json": protocol_sha,
                    "analysis-recipe-v1.json": recipe_sha, "comp2-pin-v1.json": comp2_sha, "root-admission-draft-v1.json": draft_sha,
                    Path(PREREG).name: prereg_sha, **{f"plan[{run}]": sha for run, sha in plan_shas.items()}},
        "exposure_ledger": ledger_state,
        "identity": {key: {"run_id": ids[key]["run_id"], "fit_run_id": ids[key]["fit"]["run_id"], "composed_config_hash": ids[key]["composed_config_hash"],
                           "protocol_hash": ids[key]["protocol_hash"], "parent_composed_config_hash": ids[key]["parent_composed_config_hash"],
                           "diff": ids[key]["composed_config_diff_against_the_locked_plan_cell"]} for key in CELLS},
        "tokens": {"old": tokens["old_whole"], "new": tokens["new_whole"], "delta": tokens["delta_per_reviewer_contact"], "share_pct": tokens["retired_tool_share_of_old_pct"]},
    }, indent=2, sort_keys=True))
    return 0


MODEL_TOOL_ARM = (
    "Frozen Q4_K_M decoder-only c98304 np4 max512; promoted EVO-FOLDS-V2 speech packets; NO native tool "
    "authority on any role; prompt bytes the locked PLAN arm's except the Reviewer instruction, which loses its two "
    "retired-tool sentences (82 -> 31 tokens per Reviewer contact)"
)
MODEL_TOOL_AA = (
    "Frozen Q4_K_M decoder-only c98304 np4 max512; promoted EVO-FOLDS-V2 speech packets; NO native tool "
    "authority on any role; prompt bytes the locked PLAN arm's, byte for byte (the OLD Reviewer instruction)"
)
INHERITED = (
    "TRAIN Fold A discovery rows already exposed by the sealed dual-store anchor, the released direct anchor, cells "
    "B0/B0r, B1 and its twin, B4b, B4b-rep, B5e, B7a, B7a-v2, B8b-anchor, B1-notool, PLAN, PLANr, ROLL-2, CONV, the "
    "AGREE family and KPROBE (flown or in flight at registration); this cell adds no new row to the fold and opens no "
    "split. Prior exposure is inherited in full."
)


def append_ledger(args, *, ids, plan_shas, receipt, receipt_sha, new_sha, old_sha) -> str:
    """Six DRAFT flight rows and one model-free measurement row. Idempotent: replace-or-append by run id.
    No cell may contain a literal '|'."""

    text = rd(LEDGER)
    tokens = receipt["tokens"]
    plan = receipt["sealed_reviewer_contact_rate"]["plan"]
    saving = receipt["saving"]
    eligible = [ids["arm"]["run_id"], ids["arm"]["fit"]["run_id"], ids["aa"]["run_id"], ids["aa"]["fit"]["run_id"], ids["smoke"]["run_id"], ids["smoke"]["fit"]["run_id"]]

    def notes(key: str, kind: str) -> str:
        identity = ids[key]
        is_fit = kind == "fit"
        run_id = identity["fit"]["run_id"] if is_fit else identity["run_id"]
        attempt = identity["fit"]["attempt_id"] if is_fit else identity["attempt_id"]
        declaration = (
            f"admission no-harm, harm_margin_pp {H_SLU} (by metric: intent {H_INTENT}, SLU {H_SLU}), claims_benefit false, expected_effect_pp 0.0, measurement_design cross-flight-with-in-chain-replicate, replicate_run_id {ids['aa']['run_id']}, rows 1080"
            if key == "arm" else
            f"measurement_design cross-flight-with-in-chain-replicate, claims_benefit false, expected_effect_pp 0.0, replicate_run_id {ids['arm']['run_id']}, rows 1080 (the instrument)"
            if key == "aa" else
            "measurement_design form-proof, claims_benefit false, expected_effect_pp 0.0, rows 4"
        )
        return (
            f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) {args.registered_at[:10]} at study commit "
            f"{args.study_commit} by the G5 registration agent (worktree {args.worktree}, branch {args.branch}). This "
            f"registration performs no contact and authorises none. Plan SHA256 {plan_shas[run_id]}; attempt {attempt}. "
            f"Protocol hash {identity['protocol_hash']}; composed config {identity['composed_config_hash']}; expected session "
            f"{SESSION} (attach only, never spawn or stop). READINESS HELD: root mints {DECISION_RELPATH} (decision id "
            f"{DECISION_ID}) from the package's root-admission-draft-v1.json with the six eligible run ids {', '.join(eligible)} "
            f"and this family's caps, then re-pins with scripts/flights/repin_cell.py --set-ready, which mints each cell's OWN "
            f"first-phase supply under its own run id (item E16; expected output digest {PLAN_SUPPLY_OUTPUT_SHA}, the Reviewer "
            f"instruction not being an input to it); the requirements lists are EMPTY and --allow-output-change must never be "
            f"passed. Every hash in this row moves at the flip and the re-pin tool rewrites it. ONE PIN (owner decisions 135 and "
            f"153): {THE_ONE_PIN} {OLD_TEMPLATE} (sha256 {old_sha}) -> {NEW_TEMPLATE} (sha256 {new_sha}) on the arm and the smoke, "
            f"the A/A keeping the old file; the two sentences ordering the task-contract tool retired as item E25 deleted and "
            f"nothing added (deletion-only, proven word by word in {RECEIPT}); measured with the audit's own vocab-only tokenizer "
            f"{tokens['old_whole']} -> {tokens['new_whole']} tokens per Reviewer contact ({tokens['old_retired_tool_order_head']} of "
            f"{tokens['old_whole']} = {tokens['retired_tool_share_of_old_pct']} % was the retired order), {saving['tokens_per_row_at_the_sealed_plan_rate']:.2f} "
            f"tokens per row at the sealed PLAN arm's {plan['reviewer_contacts']:,} Reviewer contacts on {plan['rows']:,} rows. Measurement "
            f"declaration ({GATE}): {declaration} -- declared at the top level of {PACKAGE}/registered-facts-v1.json and repeated in the "
            f"preregistration fence. THE RULE (owner decision 127): admitted on NO HARM against the in-chain A/A at the plan's own Fold A "
            f"half-widths, HARMFUL on a measured loss (decision 25), NEVER reported as a gain; folded into the next composed round "
            f"(decision 138) through {PACKAGE}/comp2-pin-v1.json. Caps are the AGREE arithmetic; no cap is denominated in tokens. "
            f"Stop and preserve on the first failure; AT MOST ONE root-diagnosed recovery re-registration. No paper-scale profile, no "
            f"confirmatory split, no test-split contact, no comparator re-flight and no admission entry from this row."
        )

    def row(key: str, kind: str) -> str:
        identity = ids[key]
        is_fit = kind == "fit"
        budget = identity["family_budget"]
        run_id = identity["fit"]["run_id"] if is_fit else identity["run_id"]
        scope = FLIGHT_PROSE[key] + (" -- FIT spend identity, request envelopes only, no generation" if is_fit else "") + ": " + (
            "the locked PLAN plan with the Reviewer node's instruction moved to the file that deletes the retired-tool order (item E25), read on no harm against the in-chain A/A"
            if key == "arm" else
            "the locked PLAN plan's own form with the OLD Reviewer instruction, re-flown in the same chain as the within-chain null"
            if key == "aa" else
            "the repaired Reviewer instruction on the first four rows of the unchanged roster; structural form only, never scored"
        )
        cells = [
            "", args.registered_at, run_id, "bounded-discovery-probe", scope,
            MODEL_TOOL_AA if key == "aa" else MODEL_TOOL_ARM,
            f"slurp TRAIN Fold A {identity['rows']}", "discovery", identity["split_identity_hash"], "no",
            str(budget["fit_endpoint_calls_cap"] if is_fit else budget["generation_calls_cap"]),
            str(budget["repeated_speech_audio_seconds_cap"]), str(budget["gpu_hours_fit_inclusive"]), INHERITED,
            f"{PACKAGE}/{PREFIX[key]}{kind}-plan-registered-v1.json", notes(key, kind), "",
        ]
        return " | ".join(cells).strip()

    measurement_row = " | ".join([
        "", args.registered_at[:10], MEASUREMENT_ROW, "model-free-check",
        (
            "Reproduce the 2026-09-26 global-state audit's G5 measurement of the Reviewer instruction (82 tokens, 52 of them "
            "the retired-tool order, 63 %) with the audit's own vocab-only local tokenizer, write the repaired instruction as the "
            "review-order partition alone, prove the edit deletion-only at word and byte level, and read the sealed PLAN arm's "
            "Reviewer contact rate from its own phase summaries. Zero model, server, encoder, embedder, scorer, network, GPU and "
            "paid-API contacts; port 8080 untouched."
        ),
        f"no model or tool contact; local vocab-only llama-tokenize process ({receipt['tokenizer']['invocations']} invocations) over committed text; read-only sealed phase summaries",
        "slurp TRAIN Fold A 1080, sealed PLAN phase summaries (ids and counts only); the committed instruction text",
        "discovery", ids["arm"]["split_identity_hash"], "no", "0", "0", "0",
        "No new speech exposure: no speech byte is read; the sealed summaries read were already exposed by the arm that sealed them. Prior exposure inherited in full.",
        RECEIPT,
        (
            f"REGISTERED BEFORE RESULT READING (DRAFT, root countersignature pending) {args.registered_at[:10]} at study commit "
            f"{args.study_commit}. Receipt {RECEIPT} SHA256 {receipt_sha}; script {MEASURE_SCRIPT}. Measured: old instruction "
            f"{tokens['old_whole']} tokens, retired-tool order {tokens['old_retired_tool_order_head']} ({tokens['retired_tool_share_of_old_pct']} %, the audit's 63 % "
            f"reproduced), repaired instruction {tokens['new_whole']} tokens (sha256 {new_sha}), delta {tokens['delta_per_reviewer_contact']} per Reviewer contact; "
            f"sealed PLAN role visits {json.dumps(plan['role_visits'])} on {plan['rows']} rows, {plan['reviewer_contacts_per_row']:.4f} Reviewer contacts per row, "
            f"saving {saving['tokens_per_row_at_the_sealed_plan_rate']:.2f} tokens per row and {saving['tokens_per_1080_row_flight_at_the_sealed_plan_count']:,} per flight. "
            f"Deletion-only: word-level opcodes equal and delete only; old equals deleted head plus new byte for byte. It constructs no "
            f"ExecutionPlan, reserves no contact, re-pins no committed config and authorises nothing; it exists because a "
            f"pre-computation is registered before its result is read, even when it is model-free."
        ),
        "",
    ]).strip()

    fresh = {}
    for key in ("arm", "aa", "smoke"):
        for kind in ("generation", "fit"):
            run_id = ids[key]["fit"]["run_id"] if kind == "fit" else ids[key]["run_id"]
            fresh[run_id] = row(key, kind)
    fresh[MEASUREMENT_ROW] = measurement_row
    for run_id, line in fresh.items():
        if len(line.split("|")) != 17:
            raise SystemExit(f"ledger row {run_id} does not have exactly fifteen cells; a literal '|' slipped into a cell")

    order = list(fresh)
    lines = text.split("\n")
    replaced = 0
    for index, line in enumerate(lines):
        if line.startswith("|") and len(line.split("|")) > 3 and line.split("|")[2].strip() in fresh:
            lines[index] = fresh.pop(line.split("|")[2].strip())
            replaced += 1
    if replaced and fresh:
        raise SystemExit("the ledger carries some but not all G5 rows; refusing to guess")
    if replaced:
        wr(LEDGER, "\n".join(lines))
        return f"replaced-{replaced}"
    header = (
        "\n## Cell G5: the Reviewer instruction's retired-tool order deleted -- the arm, its in-chain A/A replicate, its "
        "four-row smoke and the model-free token measurement (DRAFT, root countersignature pending)\n\n"
        "Six unconsumed flight rows -- the G5 arm, the in-chain A/A replicate, the four-row form smoke and their three FIT "
        "spend identities -- plus one model-free row for the reproduced token measurement and the deletion-only proof. "
        f"Owner decisions 127, 135, 138 and 153; authority {AUDIT} (G5) and the retirement record in {HARNESS_RECEIPT} "
        "(item E25). None of these rows is countersigned and none authorises a contact.\n\n"
        "| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | split role | "
        "split identity hash | consumed | calls | speech audio seconds | gpu hours | inherited exposure | artifacts | notes |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
    )
    suffix = "" if text.endswith("\n") else "\n"
    wr(LEDGER, text + suffix + header + "\n".join(fresh[run_id] for run_id in order) + "\n")
    return "appended"


if __name__ == "__main__":
    raise SystemExit(main())
