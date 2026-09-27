#!/usr/bin/env python3
"""Write the REV-TFRL-1 registration package (owner decision 165) from the committed configs.

The first training-free RL optimisation of the Reviewer node. Reads the three derived fragments, the
Reviewer credit read's machine report (numbers only), and the two instruction files; recomposes every
cell's own hashes; PROVES the composed-config diff against the AGREE parent is the ONE pin
(``phase_material.reviewer.instruction_template``) plus bookkeeping; proves the instruction edit list
against the sealed contrastive source word by word; and writes the package documents, a numbers-only
credit summary, a draft decision receipt for root and (with ``--append-ledger``) the eight DRAFT exposure
rows (six flight rows, the model-free credit read row and the paired READ row). Config alone: no adapter,
no split load, no contact; it flips nothing and mints nothing.

    python scripts/flights/revtfrl/write_slurp_revtfrl_registration.py --study-commit <sha> \\
        --registered-at 2026-09-27T20:00:00.000000+00:00 \\
        [--credit-report $SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-REVIEWER-CREDIT-TABLE-V1/report.json] \\
        [--append-ledger]
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import io
import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash  # noqa: E402

PACKAGE = "docs/readiness/2026-09-27-slurp-stage3-reviewer-tfrl-v1"
PREREG = PACKAGE + "-preregistration.md"
SUMMARY = PACKAGE + "/credit-table-summary-v1.json"
EDIT_PROOF = PACKAGE + "/instruction-edit-proof-v1.json"
LEDGER = "docs/exposure-ledger.md"

PARENT_ARM = "slurp-native-stage3-agree-w1-fold-a-v1"
PARENT_SMOKE = "slurp-native-stage3-agree-w1-fold-a-smoke-4-v1"
AGREE_RUN = "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1"
AGREE_AA_RUN = "SAEA-SLURP-STAGE3-AGREE-AA-FOLD-A-V1"
AGREE_OFFICIAL = {"intent_accuracy": 85.83, "slu_f1": 65.16}
AGREE_READ = "docs/results/2026-09-27-slurp-agree-w1-fold-a-read.md"
AGREE_SUPPLY_OUTPUT_SHA = "eab5c61e92a47c1723c478f2b7914abade6152b195f676d7d32251f3d18884ae"
AGREE_GPU_H_PER_1080 = 1.8816
AGREE_CONTACTS_PER_ROW = 4.060
SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"

CELLS = {
    "arm": "slurp-native-stage3-revtfrl-fold-a-v1",
    "smoke": "slurp-native-stage3-revtfrl-fold-a-smoke-4-v1",
    "aa": "slurp-native-stage3-revtfrl-aa-fold-a-v1",
}
PARENTS = {"arm": PARENT_ARM, "smoke": PARENT_SMOKE, "aa": PARENT_ARM}
PREFIX = {"arm": "", "smoke": "smoke-", "aa": "aa-"}
FLIGHT_PROSE = {
    "arm": "Cell REV-TFRL-1",
    "smoke": "Four-row form smoke of cell REV-TFRL-1",
    "aa": "The in-chain A/A replicate of cell REV-TFRL-1 (the base: AGREE with G5's Reviewer instruction)",
}
DECISION_ID = "slurp-stage3-revtfrl-fold-a-admission-v1"
DECISION_RELPATH = "coordination/slurp-stage3-revtfrl-fold-a-v1/root-admission-v1.json"
CREDIT_ROW = "SAEA-SLURP-STAGE3-REVIEWER-CREDIT-TABLE-V1"
READ_ROW = "SAEA-SLURP-STAGE3-REVTFRL-FOLD-A-READ-V1"
READ_ROOT = "analysis/SAEA-SLURP-STAGE3-REVTFRL-FOLD-A-READ-V1"
CREDIT_SCRIPT = "scripts/analysis/slurp_reviewer_credit_table.py"
CREDIT_ROOT = "analysis/SAEA-SLURP-STAGE3-REVIEWER-CREDIT-TABLE-V1"

LOCKED_TEMPLATE = "probes/slurp_native_role_reviewer_v1.txt"
G5_TEMPLATE = "probes/slurp_native_role_reviewer_v1_g5_v1.txt"
NEW_TEMPLATE = "probes/slurp_native_role_reviewer_contrastive_v1.txt"
SOURCE_TEMPLATE = "probes/slurp_native_role_reviewer_candidate_recovery_v1.txt"
THE_ONE_PIN = "phase_material.reviewer.instruction_template"
BOOKKEEPING_PREFIXES = ("native_contact_fit.", "prepared_phase_supply", "what_this_is")
ALGORITHM_ID = "sealed-credit-system-policy-v1"

H_SLU, H_INTENT = 1.2485, 0.9943
INSTRUMENT = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"
OWNER_DECISIONS = "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md"
G5_PACKAGE = "docs/readiness/2026-09-27-slurp-stage3-g5-fold-a-v1"
CANDREC_PREREG = "docs/readiness/2026-09-25-slurp-stage3-candidate-recovery-v1-preregistration.md"
SYNTHESIS_NOTE = "docs/results/2026-09-27-slurp-mechanism-synthesis.md (branch fable/synthesis)"
ERRSRC = "docs/results/2026-09-27-slurp-agree-arm-error-sources.md"
TRJ = "docs/results/2026-09-25-slurp-system-trajectory-attribution.md"
RPG = "docs/results/2026-09-26-slurp-reviewer-planner-global-state-audit.md"
GATE = "scripts/checks/stage3_effect_floor_check.py"
DERIVE_SCRIPT = "scripts/flights/revtfrl/derive_slurp_revtfrl_cells.py"
CONFIG_TEST = "tests/unit/test_revtfrl_config.py"
READ_DRIVER = "scripts/analysis/plan_cell_read.py"


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
    experiment_block = [k for k in changed if k.split(".", 1)[0] in experiment_keys
                        and k not in one_pin and k not in bookkeeping]
    other = [k for k in changed if k not in one_pin and k not in bookkeeping and k not in experiment_block]
    return {"the_one_pin": one_pin, "baseline_bookkeeping_only": bookkeeping,
            "experiment_fragment_own_block": experiment_block, "anything_else": other}


def identities() -> dict:
    out = {}
    for key, experiment in CELLS.items():
        document = json.loads(rd(f"configs/experiment/{experiment}.json"))
        cell = document["cells"][0]
        composed = compose(REPO_ROOT, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"],
                           experiment)
        parent_doc = json.loads(rd(f"configs/experiment/{PARENTS[key]}.json"))
        parent_cell = parent_doc["cells"][0]
        parent = compose(REPO_ROOT, parent_cell["model_fragment"], parent_cell["dataset_fragment"],
                         parent_cell["baseline_fragment"], PARENTS[key])
        baseline_keys = set(json.loads(rd(f"configs/baseline/{parent_cell['baseline_fragment']}.json")))
        diff = composed_diff(parent.values, composed.values, set(document) | set(parent_doc), baseline_keys)
        if diff["anything_else"]:
            raise SystemExit(f"{key}: composed config differs from its AGREE parent beyond the pin and bookkeeping: "
                             f"{diff['anything_else']}")
        template = composed.values["phase_material"]["reviewer"]["instruction_template"]
        expected = G5_TEMPLATE if key == "aa" else NEW_TEMPLATE
        if diff["the_one_pin"] != [THE_ONE_PIN] or template != expected:
            raise SystemExit(f"{key}: the Reviewer pin is {template!r}, expected {expected!r}")
        if "prepared_phase_supply" in composed.values or "phase_tools" in composed.values:
            raise SystemExit(f"{key}: a committed prepared_phase_supply or phase_tools is present")
        mine_pm = {k: v for k, v in composed.values["phase_material"].items() if k != "reviewer"}
        theirs_pm = {k: v for k, v in parent.values["phase_material"].items() if k != "reviewer"}
        if mine_pm != theirs_pm:
            raise SystemExit(f"{key}: phase_material differs beyond the reviewer entry")
        split = document["population"]["split_identity_hash"]
        out[key] = {
            "experiment": experiment, "cell": cell["cell_id"], "run_id": cell["run_id"],
            "attempt_id": cell["attempt_id"], "baseline_fragment": cell["baseline_fragment"],
            "parent_experiment": PARENTS[key], "dataset_fragment": cell["dataset_fragment"],
            "model_fragment": cell["model_fragment"], "arm": composed.values["arm"],
            "rows": document["population"]["count"], "split_identity_hash": split,
            "composed_config_hash": composed.config_hash, "parent_composed_config_hash": parent.config_hash,
            "protocol_hash": protocol_hash(composed.config_hash, composed.values["arm"], split),
            "fit": dict(composed.values["native_contact_fit"]), "family_budget": document["family_budget"],
            "execution_profile": document["execution_profile"],
            "carrier_lock_key": composed.values["carrier_lock_key"],
            "reviewer_instruction_template": template,
            "composed_config_diff_against_the_agree_parent": diff,
            "readiness": cell["readiness"],
        }
    return out


def edit_proof() -> dict:
    """Word-level edit list of the new Reviewer text against the sealed contrastive source it adapts, and
    its relation to the G5 text it replaces."""

    source = rd("configs/" + SOURCE_TEMPLATE)
    new = rd("configs/" + NEW_TEMPLATE)
    g5 = rd("configs/" + G5_TEMPLATE)
    a, b = source.split(), new.split()
    ops = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if tag != "equal":
            ops.append({"op": tag, "source_words": " ".join(a[i1:i2]), "new_words": " ".join(b[j1:j2])})
    equal_words = sum(i2 - i1 for tag, i1, i2, _j1, _j2 in
                      difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes() if tag == "equal")
    return {
        "schema": "saea-revtfrl-instruction-edit-proof-v1",
        "new": {"relpath": "configs/" + NEW_TEMPLATE, "sha256": sha_file("configs/" + NEW_TEMPLATE),
                "words": len(b), "characters": len(new)},
        "source": {"relpath": "configs/" + SOURCE_TEMPLATE, "sha256": sha_file("configs/" + SOURCE_TEMPLATE),
                   "words": len(a), "flown_by": "SAEA-SLURP-NATIVE-STAGE3-CANDIDATE-RECOVERY-CONTROL-R01C-SEAL-RECOVERY1-V1"},
        "replaces": {"relpath": "configs/" + G5_TEMPLATE, "sha256": sha_file("configs/" + G5_TEMPLATE),
                     "words": len(g5.split())},
        "words_kept_in_order_from_the_source": equal_words,
        "edits_against_the_source": ops,
        "why_each_edit": [
            "'candidate proposal' -> 'Perception candidates' and 'The original candidates and exemplar-supported "
            "additions' -> 'Perception's candidates and the retrieved examples': this plan carries no derived candidate "
            "proposal and no exemplar-supported additions; it carries Perception's own 1-3 candidates and the "
            "retrieved TRAIN exemplars, which the renamed words now name",
            "'and call only tools actually exposed in this turn' deleted: no tool is exposed to any role of this "
            "plan (item E25; G5 deleted the locked text's retired-tool order for the same reason)",
            "'Do not request a transcript' kept from the locked and G5 Reviewer text: a standing boundary of this "
            "study (no transcript state anywhere)",
        ],
        "token_note": (
            "Not tokenised here (this registration contacts no tokenizer): the new text has "
            f"{len(b)} words against the G5 text's {len(g5.split())}, so each Reviewer contact carries a few "
            "hundred more prompt tokens against a slot of 24,576 and a sealed Reviewer prompt near 10,000; the "
            "flip's FIT stage measures every request envelope before any generation contact."
        ),
    }


def summarise(report: dict, report_sha: str) -> dict:
    loop = report["loop_value"]
    return {
        "schema": "saea-reviewer-credit-summary-v1",
        "read_id": report["read_id"], "recipe": report["recipe"],
        "report_json_content_sha256_without_generated_at": report_sha,
        "analysis_root": CREDIT_ROOT, "script": CREDIT_SCRIPT,
        "contacts": report["contacts"], "roster_checks": report["roster_checks"],
        "pools": [{k: p[k] for k in ("label", "run_id", "use", "form", "scorer", "visits", "revise_routes",
                                     "phases_sha256", "outputs_sha256", "scores_sha256", "checks")}
                  for p in report["pools"]],
        "credit": report["credit"], "stance_route": report["stance_route"], "triggers": report["triggers"],
        "loop_value": loop, "form_selection": report["form_selection"],
        "gate_scope_crossfit": {g: {"folds": v["folds"],
                                    "top_by_mean_intent_vs_as_built": sorted(
                                        v["in_sample_mean_vs_as_built"].items(),
                                        key=lambda kv: -kv[1]["mean_intent_pp"])[:6]}
                                for g, v in report["grid"]["crossfit"].items()},
        "note": ("Numbers only: ids, classes, counts, rates and hashes; no utterance, transcript, gold string, "
                 "Reviewer text or delivered answer. Selection used the 'selection' pools (TRAIN R01C, outside Fold "
                 "A) only; the Fold A and DEV pools are descriptive."),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--study-commit", required=True)
    parser.add_argument("--registered-at", required=True)
    parser.add_argument("--branch", default="fable/revtfrl")
    parser.add_argument("--worktree", default="/home/chao/saea-worktrees/fable-revtfrl")
    parser.add_argument("--credit-report", default=None)
    parser.add_argument("--append-ledger", action="store_true")
    args = parser.parse_args(argv)
    os.chdir(REPO_ROOT)

    if args.credit_report:
        report = json.loads(Path(args.credit_report).read_text(encoding="utf-8"))
        stripped = {k: v for k, v in report.items() if k != "generated_at"}
        report_sha = hashlib.sha256(json.dumps(stripped, indent=1, sort_keys=True).encode("utf-8")).hexdigest()
        wjson(SUMMARY, summarise(report, report_sha))
    summary = json.loads(rd(SUMMARY))
    summary_sha = sha_file(SUMMARY)
    proof = edit_proof()
    proof_sha = wjson(EDIT_PROOF, proof)

    fs = summary["form_selection"]
    locked_first = summary["triggers"]["selection / locked-v1"]
    r01c_wrong_rate = locked_first["intent_wrong"] / locked_first["first_visits"]
    base_wrong_rate = 1.0 - AGREE_OFFICIAL["intent_accuracy"] / 100.0
    expected = round(fs["paired_difference_intent_pp"] * base_wrong_rate / r01c_wrong_rate, 2)
    expected_lo = round(fs["paired_difference_ci95"][0] * base_wrong_rate / r01c_wrong_rate, 2)
    expected_hi = round(fs["paired_difference_ci95"][1] * base_wrong_rate / r01c_wrong_rate, 2)
    arm_contacts_per_row = 3657 / 625
    arm_gpu_h = round(AGREE_GPU_H_PER_1080 * arm_contacts_per_row / AGREE_CONTACTS_PER_ROW, 2)
    expected_arm_contacts = round(1080 * arm_contacts_per_row)

    ids = identities()
    arm, aa, smoke = ids["arm"], ids["aa"], ids["smoke"]
    caps, smoke_caps = arm["family_budget"], smoke["family_budget"]
    if aa["family_budget"] != caps:
        raise SystemExit("the A/A caps are not the arm's")

    expectation_arithmetic = (
        f"Measured, never a prior (decision 139): on the SAME 625 TRAIN R01C rows (outside Fold A), the contrastive "
        f"form's review loop moved intent by {fs['contrastive_loop_intent_pp']:+.2f} pp over its own first drafts and "
        f"the locked form's by {fs['locked_loop_intent_pp_mean']:+.3f} pp (mean of {len(fs['locked_pools'])} sealed "
        f"pools); paired per row the difference is {fs['paired_difference_intent_pp']:+.3f} pp CI95 "
        f"[{fs['paired_difference_ci95'][0]:+.3f}, {fs['paired_difference_ci95'][1]:+.3f}] "
        f"({fs['unit']}, {fs['draws']} draws, seed {fs['seed']}). A review loop can only act on a wrong draft, so the "
        f"transfer to the base scales by the first-draft intent-wrong rate: R01C "
        f"{locked_first['intent_wrong']}/{locked_first['first_visits']} = {100 * r01c_wrong_rate:.2f} % under the "
        f"locked form, the base {100 * base_wrong_rate:.2f} % (the sealed AGREE arm's official intent "
        f"{AGREE_OFFICIAL['intent_accuracy']}, {AGREE_READ}). Expected intent effect "
        f"{fs['paired_difference_intent_pp']:.3f} x {base_wrong_rate:.4f} / {r01c_wrong_rate:.4f} = {expected:+.2f} pp "
        f"(interval {expected_lo:+.2f} to {expected_hi:+.2f}), BELOW the cross-flight benefit bar of about 2.5 pp at "
        f"n = 1,080 and below the intent own-null half-width {H_INTENT}: the design cannot see it as a gain, so the "
        "cell claims none and is admitted on NO HARM; the node's own within-trajectory loop value is read beside it."
    )
    confound = (
        "The selection's measured object is the review loop of the sealed candidate-recovery control arm, which "
        "also changed the Planner's routing text, the Solver's instruction and the candidate proposal. This cell "
        "moves the Reviewer instruction ALONE (the brief scopes the optimisation to the node); the Planner keeps "
        "the locked routing text and the Solver the locked revision clause. The transfer is therefore an "
        "assumption stated here and tested by the read: the arm's own per-visit credit (REVISE rate per class, "
        "helped / hurt per revision, the entity-error delta on CORRECT drafts) is compared with the source arm's "
        "sealed credit, and a loop value far below the source's is read as 'the lift lived in the Planner / Solver "
        "texts', which names the next round's node."
    )

    no_harm_rule = (
        "NO-HARM ADMITTED (owner decision 127): against the IN-CHAIN A/A arm flown in the same chain, the paired "
        f"CI95 lower bound of the intent-accuracy delta (primary, decision 133) is not below -{H_INTENT} pp AND the "
        f"paired CI95 lower bound of the official pooled SLU-F1 delta (the guard) is not below -{H_SLU} pp -- each "
        f"metric at its own Fold A own-null half-width ({INSTRUMENT} section 2d). HARMFUL: a measured loss on either "
        "metric (CI95 upper bound below zero, decision 25). NEUTRAL-BY-WIDTH IS THE ADMISSION. The cell is NEVER "
        "reported as a gain, whatever the point estimate. Beside the verdict, never instead of it, the read reports "
        "the NODE CREDIT: on each arm, the loop value (delivered answer minus the same trajectory's first Solver "
        "draft, intent and official pooled SLU-F1, paired within the flight, cluster CI95) and the per-visit credit "
        f"table by pre-review error class computed by {CREDIT_SCRIPT}'s own functions; the arm-minus-A/A difference "
        f"of loop values set beside the declared expectation {expected:+.2f} pp; the Reviewer contact rate and "
        "REVISE rate; the per-scenario table in both weightings and the frontier row (decision 75); and a model-free "
        "count of Reviewer responses narrating a tool call on each arm."
    )

    measurement = {
        arm["run_id"]: {
            "admission": "no-harm", "claims_benefit": False, "expected_effect_pp": expected,
            "harm_margin_pp": H_SLU, "harm_margin_pp_by_metric": {"intent_accuracy": H_INTENT, "slu_f1": H_SLU},
            "measurement_design": "cross-flight-with-in-chain-replicate",
            "primary_metric": "intent accuracy (scenario_action exact), official pooled SLU-F1 the non-inferiority guard (owner decision 133)",
            "replicate_run_id": aa["run_id"], "rows": 1080,
            "note": (
                "Admitted on NO HARM and never reported as a gain. expected_effect_pp is the MEASURED transfer of the "
                "offline selection statistic (registered-facts-v1.json expectation_arithmetic), below the design's "
                "benefit bar, which is why claims_benefit is false; the harm margin is the design's measured sampling "
                "floor at n = 1,080 (Fold A own null, PLAN vs PLANr). The node credit (within-flight loop value per arm) "
                "is read beside the verdict and is the next optimisation round's reward signal."
            ),
        },
        aa["run_id"]: {
            "claims_benefit": False, "expected_effect_pp": 0.0,
            "measurement_design": "cross-flight-with-in-chain-replicate",
            "primary_metric": "intent accuracy and official pooled SLU-F1, as the instrument",
            "replicate_run_id": arm["run_id"], "rows": 1080,
            "note": "The in-chain null: the base (AGREE with G5's Reviewer instruction) re-flown in the same chain. Its expected effect is zero by construction.",
        },
        smoke["run_id"]: {
            "claims_benefit": False, "expected_effect_pp": 0.0, "measurement_design": "form-proof",
            "primary_metric": "none (structural form only)", "rows": 4,
            "note": "Four rows prove FORM only: the new instruction loads by its relpath, every request fits, the Reviewer answers with findings and no tool call, the episode completes. Never scored or read.",
        },
    }

    offline_split = {
        "scored_offline_exactly": [
            "WHEN a Reviewer verdict may change the answer (a gate over the sealed revision events: every gate of "
            "the grid, on each sealed pool, by re-scoring the answer the gated policy would deliver -- the pre-review "
            "draft when the gate refuses, the revised draft when it honours)",
            "WHAT a revision may change (scope: full, intent-only, entities-only), by merging the sealed pre-review "
            "and revised drafts and re-scoring",
            "the node's CREDIT per visit (helped / hurt / neutral on intent and on the row's entity errors, by the "
            "pre-review draft's error class) and its loop value over its own first drafts",
            "the choice between Reviewer FORMS that some sealed arm already flew, by their loop values on the same rows",
        ],
        "needs_a_flight": [
            "any Reviewer text or evidence view no sealed arm flew: its findings, the Planner's routing on them and "
            "the Solver's revision are new model contacts",
            "a trigger that makes the Reviewer act on rows where no sealed revision exists (a gate can only REMOVE "
            "sealed revisions offline, never add one)",
        ],
        "why_the_flight_read_is_still_precise_for_the_node": (
            "every trajectory seals the pre-review draft beside the delivered answer, so the node's loop value is a "
            "paired WITHIN-trajectory contrast with no flight offset -- the between-flight band that swamps a "
            "cross-flight system read does not enter it"
        ),
    }

    gpu = {
        "rate_source": f"{AGREE_READ}: the AGREE arm's measured {AGREE_GPU_H_PER_1080} GPU-h per 1,080 rows at {AGREE_CONTACTS_PER_ROW} contacts per row (serving monitor active seconds)",
        "offline_rounds": "0 GPU-h: the credit table, the gate x scope grid, the cross-fit and the form selection are model-free over sealed bytes",
        "this_cell": {
            "smoke": "4 rows, at most 44 contacts, about 0.01 GPU-h",
            "in_chain_aa": f"about {round(1080 * AGREE_CONTACTS_PER_ROW)} contacts, about {AGREE_GPU_H_PER_1080} GPU-h (the AGREE rate)",
            "arm": f"about {expected_arm_contacts:,} contacts ({arm_contacts_per_row:.2f} per row, the sealed contrastive-review rate of the candidate-recovery control arm: 3,657 contacts on 625 rows), about {arm_gpu_h} GPU-h",
            "total": f"about {round(AGREE_GPU_H_PER_1080 + arm_gpu_h + 0.01, 1)} GPU-h, one official complete score per 1,080-row cell; caps 11,880 generation contacts and 12.0 GPU-h per cell as ceilings",
        },
        "next_round_selection_flights": (
            "Reviewer variants the offline loop cannot score are flown on TRAIN rows outside Fold A (R01C, or the "
            "decision-162 filler chunks on Fold B, decision 168), K variants plus the as-built control in ONE campaign, each read by its own "
            "within-trajectory loop value: about 625 x 5.85 x 0.000429 = 1.6 GPU-h per 625-row variant, so K = 3 plus "
            "control is about 6.3 GPU-h; only the winner re-enters Fold A beside an in-chain A/A (about 4.6 GPU-h)."
        ),
    }

    facts = {
        "schema": "saea-registered-facts-v1",
        "_note": ("Every model-free measured fact this registration rests on, and the CANONICAL stage3_measurement "
                  f"block {GATE} resolves (keyed by run id). The preregistration fence repeats it; this copy has precedence."),
        "registered_at_utc": args.registered_at, "study_commit_at_registration": args.study_commit,
        "owner_decisions": {
            "165": "nodes like the Reviewer can all be optimised; do not mechanically throw them away -- optimise its behaviour on its own with training-free RL",
            "127": "no-harm admission of an item whose effect the design cannot see as a gain; never reported as a gain",
            "133": "intent primary, official SLU-F1 the guard",
            "139": "expectations from measured numbers only; no conditional pre-commitment",
            "153": "G5 (the base's Reviewer text) prepared and flown as a no-harm item",
            "161": "the agreement term retained (the base's AGREE form)",
        },
        "rows": 1080, "stage3_measurement": measurement,
        "the_policy": {
            "node": "Reviewer", "composed_key": THE_ONE_PIN,
            "from": {"value": G5_TEMPLATE, "sha256": proof["replaces"]["sha256"]},
            "to": {"value": NEW_TEMPLATE, "sha256": proof["new"]["sha256"]},
            "adapted_from_the_sealed_form": {"value": SOURCE_TEMPLATE, "sha256": proof["source"]["sha256"],
                                             "flown_by": proof["source"]["flown_by"]},
            "edit_proof": {"relpath": EDIT_PROOF, "sha256": proof_sha},
            "untouched": "Planner and Solver templates, the agreement term, the three stores, the program and its ceiling, roster, geometry, normaliser, scorers",
        },
        "offline_selection": {
            "credit_summary": {"relpath": SUMMARY, "sha256": summary_sha},
            "selection_pools": [p["label"] for p in summary["pools"] if p["use"] == "selection"],
            "form_selection": fs,
            "gate_scope_grid": summary["gate_scope_crossfit"],
            "reading": (
                "No gate and no revision scope over the sealed revisions beat honouring every revision: the "
                "cross-fitted choices returned 0.000 / 0.000 (contrastive) and -0.024 / -0.18 intent (locked) on their "
                "held-out folds. The node's existing revisions are net useful on intent; its deficit is REACH. The "
                "offline loop therefore selects on the one policy dimension where a sealed alternative exists -- the "
                "Reviewer's form -- and leaves gating and scope as they are."
            ),
        },
        "expectation_arithmetic": expectation_arithmetic,
        "confound_stated": confound,
        "offline_and_flight_split": offline_split,
        "gpu_budget": gpu,
        "identity": {key: {k: v for k, v in ids[key].items() if k not in ("composed_config_diff_against_the_agree_parent", "readiness")} for key in CELLS},
        "composed_config_diff_against_the_agree_parent": {key: ids[key]["composed_config_diff_against_the_agree_parent"] for key in CELLS},
        "byte_identity_expectation": {
            "sealed_agree_supply_output_sha256": AGREE_SUPPLY_OUTPUT_SHA,
            "claim": "the Reviewer instruction is not an input to the first-phase supply, so every 1,080-row supply the flip mints for the arm and the A/A must carry this output digest; a different digest means the knowledge channel moved -- stop and report",
        },
        "comparator": {
            "in_chain_replicate": aa["run_id"], "context_only": [AGREE_RUN, AGREE_AA_RUN],
            "margins": {"h_intent": H_INTENT, "h_slu": H_SLU, "source": f"{INSTRUMENT} section 2d"},
        },
        "no_harm_rule": no_harm_rule,
        "prohibitions": [
            "Never reported as a gain.",
            "No Fold A gold was used for selection; Fold A pools entered the credit table descriptively only.",
            "No test-split, Fold B or DEV contact; no re-flying of any sealed cell.",
            "No second factor: no Planner, Solver, store, roster, geometry or session change.",
            "No paper-scale profile; no flight before root mints the decision receipt and the cells are flipped.",
        ],
    }
    facts_sha = wjson(PACKAGE + "/registered-facts-v1.json", facts)

    protocol = {
        "schema": "saea-registered-protocol-v1", "protocol_id": "slurp-stage3-revtfrl-fold-a-protocol-v1",
        "registered_at_utc": args.registered_at, "study_commit_at_registration": args.study_commit,
        "source_tree": f"studies/speech-aware-evidence-acquisition, worktree {args.worktree}, branch {args.branch}",
        "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP",
        "the_question": (
            "With the Reviewer node's instruction moved to the contrastive form selected offline over sealed TRAIN "
            "R01C trajectories and nothing else changed, does the system stay within its own null on TRAIN Fold A "
            "1,080 against an in-chain A/A (the AGREE arm with G5's Reviewer instruction), and how large is the node's "
            "own within-trajectory credit beside the A/A's?"
        ),
        "one_factor": f"Composed key {THE_ONE_PIN}: {G5_TEMPLATE} -> {NEW_TEMPLATE} (sha256 {proof['new']['sha256']}).",
        "cells": {key: {k: ids[key][k] for k in ("cell", "experiment", "run_id", "attempt_id", "rows", "composed_config_hash",
                                                  "protocol_hash", "split_identity_hash", "reviewer_instruction_template")}
                  | {"fit_run_id": ids[key]["fit"]["run_id"], "fit_attempt_id": ids[key]["fit"]["attempt_id"]} for key in CELLS},
        "decision_rule_fixed_here": no_harm_rule,
        "expectation_arithmetic": expectation_arithmetic,
        "confound_stated": confound,
        "development_numbers_only": "TRAIN Fold A construction-fold development numbers (owner decisions 28 and 86); never a test claim.",
        "failure_policy": "Stop and preserve on the first failure. AT MOST ONE root-diagnosed recovery re-registration; a second failure closes the cell and the fix is proven on a four-row dry run. The budget is run-cumulative across attempts.",
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
                "schema": f"saea-registered-{kind}-plan-v1", "plan_kind": kind, "cell": identity["cell"],
                "experiment": identity["experiment"], "composed_config_hash": identity["composed_config_hash"],
                "registered_at_utc": args.registered_at, "status": protocol["status"],
                "source_tree": protocol["source_tree"], "preparation_base_commit": args.study_commit,
                "expected_session_id": SESSION, "unused_budget_is_not_attempt_authority": True,
                "execution_plan": {
                    "schema": "saea-execution-plan-v1", "study": "speech-aware-evidence-acquisition",
                    "carrier_lock_key": identity["carrier_lock_key"], "run_id": run_id,
                    "attempt_id": identity["fit"]["attempt_id"] if is_fit else identity["attempt_id"],
                    "execution_profile": identity["execution_profile"], "split_role": "discovery",
                    "split_identity_hash": identity["split_identity_hash"], "protocol_hash": identity["protocol_hash"],
                    "planned_model_calls": budget["fit_endpoint_calls_cap"] if is_fit else budget["generation_calls_cap"],
                    "planned_speech_audio_seconds": budget["repeated_speech_audio_seconds_cap"],
                    "planned_gpu_hours": budget["gpu_hours_fit_inclusive"],
                },
                "family_budget": budget,
                "execution_route": (
                    "The shared core.flight.cli FIT path under this cell's own native_contact_fit ids; it measures request envelopes and produces no generation."
                    if is_fit else
                    "Shared core.flight.cli campaign over configs/campaign/slurp-native-stage3-revtfrl-fold-a-v1.json, which carries the in-chain A/A AND the REV-TFRL-1 arm so the two fly in ONE chain; one official score per generation cell at finalize."
                    if key != "smoke" else
                    "Shared core.flight.cli worker on this cell alone; the smoke is outside the campaign plan and is never scored."
                ),
                "prepared_phase_supply": {
                    "relpath": f"prepared/{identity['run_id']}/phase-supply-v1.json", "sha256": "MINTED_AT_THE_FLIP",
                    "expected_output_sha256": AGREE_SUPPLY_OUTPUT_SHA if key != "smoke" else "the AGREE smoke's own four-row digest",
                    "note": facts["byte_identity_expectation"]["claim"],
                },
                "protocol_document": {"relpath": PACKAGE + "/protocol-registered-v1.json", "sha256": protocol_sha},
                "one_factor": protocol["one_factor"] if key != "aa" else "none: the base (AGREE with G5's Reviewer instruction)",
                "purpose": f"{run_id}: {FLIGHT_PROSE[key]}. " + (
                    "It measures request envelopes only and reads nothing." if is_fit else
                    no_harm_rule if key == "arm" else
                    "It supplies the within-chain null and the base Reviewer's own credit; no claim of its own." if key == "aa" else
                    "Structural form proof only: no score and no read."),
                "quality_read_gate": "No task-quality read before the complete sealed manifest, the ordered outputs, the native phase summary and the single successful complete official TRAIN score exist for BOTH the arm and its in-chain A/A, and before the READ row " + READ_ROW + " is countersigned.",
            }
            plan_shas[run_id] = wjson(f"{PACKAGE}/{PREFIX[key]}{kind}-plan-registered-v1.json", plan_doc)

    recipe = {
        "schema": "saea-slurp-paired-analysis-recipe-v1",
        "recipe_id": "slurp-stage3-revtfrl-fold-a-paired-analysis-v1",
        "title": "Cell REV-TFRL-1 -- the paired roster read against the in-chain A/A under the no-harm rule, with the Reviewer node's within-trajectory credit on both arms",
        "registered_at_utc": args.registered_at,
        "read_run_id": READ_ROW,
        "run_ids": {"arm": arm["run_id"], "aa": aa["run_id"], "smoke": smoke["run_id"], "fit_arm": arm["fit"]["run_id"],
                    "fit_aa": aa["fit"]["run_id"], "fit_smoke": smoke["fit"]["run_id"], "read": READ_ROW},
        "arms": {
            "arm": {"run_id": arm["run_id"], "attempt_id": arm["attempt_id"], "fit_run_id": arm["fit"]["run_id"],
                    "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL", "outputs_sha256": "PENDING_SEAL"},
            "in_chain_replicate": {"run_id": aa["run_id"], "attempt_id": aa["attempt_id"], "fit_run_id": aa["fit"]["run_id"],
                                   "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL",
                                   "outputs_sha256": "PENDING_SEAL", "role": "the within-chain null the delta is read at"},
            "context": {"run_ids": [AGREE_RUN, AGREE_AA_RUN], "role": "sealed AGREE family, context beside the A/A, never the bar"},
        },
        "resampling": {"bootstrap_draws": 10000, "metrics": ["scenario_action_exact", "slu_f1_f1"], "seed": 20260927,
                       "unit": "row (paired); the node loop value uses the whole-utterance cluster bootstrap of the credit driver"},
        "decision_rule": no_harm_rule, "margins": {"h_intent": H_INTENT, "h_slu": H_SLU},
        "declared_expectation": {"expected_effect_pp": expected, "arithmetic": expectation_arithmetic},
        "steps": [
            "1. Refuse unless BOTH the arm and the in-chain A/A carry a COMPLETE sealed manifest at 1,080 rows with the committed roster's ids, each with one successful complete official TRAIN score, their config hashes are this package's (the arm the contrastive Reviewer file, the A/A the G5 file), and the READ row is countersigned.",
            "2. Structural: 0 tool schemas and 0 tool calls on every contact of both arms; Reviewer contacts per row; REVISE routes per row; a model-free count of Reviewer responses narrating a tool call (counts only).",
            f"3. The paired system read: arm minus in-chain A/A, intent and official pooled SLU-F1, 10,000 paired draws, seed 20260927 ({READ_DRIVER} family); apply the no-harm rule; never write 'gain' or 'no gain'.",
            f"4. The NODE CREDIT on each arm with {CREDIT_SCRIPT}'s own functions (visit_records, credit_table, loop value against the trajectory's own first draft): the per-class credit table, the loop value with its cluster CI95, and the arm-minus-A/A difference of loop values beside the declared expectation.",
            "5. Beside every number: the per-scenario table in both weightings, the frontier row (decision 75), the arm's credit table next to the sealed source arm's (the confound check stated in the protocol).",
            "6. Hand the arm's per-visit credit table to the next proposer round as its reward signal; an unadmitted policy is withdrawn with the credit table as the first root-cause lead.",
        ],
        "output": {"analysis_root": READ_ROOT},
        "boundary": "A development read on a TRAIN construction fold (owner decisions 28 and 86); never a test claim. No utterance text, transcript, gold string, Reviewer text or model output is printed or persisted.",
    }
    recipe_sha = wjson(PACKAGE + "/analysis-recipe-v1.json", recipe)

    eligible = [arm["run_id"], arm["fit"]["run_id"], aa["run_id"], aa["fit"]["run_id"], smoke["run_id"], smoke["fit"]["run_id"]]
    draft = {
        "_draft_note": ("A DRAFT written by the registration agent for root to mint on the data root with "
                        "scripts/flights/revtfrl/revtfrl_mint_receipt.py, which sets status 'decided', stamps "
                        "recorded_at_utc, re-hashes every antecedent path and refuses to overwrite. It authorises nothing "
                        "while its status is not 'decided'."),
        "schema": "saea-campaign-decision-v1", "decision_id": DECISION_ID, "status": "DRAFT-NOT-MINTED",
        "recorded_at_utc": None, "owner": "root", "coordinator": "Fable5.1", "eligible_run_ids": eligible,
        "cell_kind": f"Stage-3 training-free RL cell ({ALGORITHM_ID}): one arm on TRAIN Fold A 1,080, its in-chain A/A in the same chain, and a four-row form smoke outside the chain.",
        "decision": ("Fly REV-TFRL-1: the AGREE arm with the Reviewer node's instruction moved from the G5 text to the "
                     "contrastive form selected offline over sealed TRAIN R01C trajectories, read at the in-chain A/A (the "
                     f"base) on NO HARM at the Fold A half-widths (intent {H_INTENT}, SLU {H_SLU}); never reported as a gain; "
                     "the node's within-trajectory credit read beside it."),
        "authorization_basis": f"Owner decision 165 (optimise the Reviewer node on its own with training-free RL); 127, 133, 139, 153, 161; the binding instrument note {INSTRUMENT}.",
        "antecedents": {
            "owner_decisions": {"path": OWNER_DECISIONS, "sha256": sha_file(OWNER_DECISIONS)},
            "instrument_note": {"path": INSTRUMENT, "sha256": sha_file(INSTRUMENT)},
            "preregistration": {"path": PREREG, "sha256": None},
            "readiness_readme": {"path": PACKAGE + "/README.md", "sha256": None},
            "protocol": {"path": PACKAGE + "/protocol-registered-v1.json", "sha256": protocol_sha},
            "registered_facts": {"path": PACKAGE + "/registered-facts-v1.json", "sha256": facts_sha},
            "analysis_recipe": {"path": PACKAGE + "/analysis-recipe-v1.json", "sha256": recipe_sha},
            "credit_summary": {"path": SUMMARY, "sha256": summary_sha},
            "edit_proof": {"path": EDIT_PROOF, "sha256": proof_sha},
            "new_instruction": {"path": "configs/" + NEW_TEMPLATE, "sha256": proof["new"]["sha256"]},
            "config_proof": {"path": CONFIG_TEST, "sha256": sha_file(CONFIG_TEST) if Path(CONFIG_TEST).is_file() else None},
            "registration_base_commit": args.study_commit,
        },
        "budget": {**{k: caps[k] for k in sorted(caps)}, "smoke": smoke_caps, "paid_api_calls": 0,
                   "expected_contacts": {"arm": expected_arm_contacts, "aa": round(1080 * AGREE_CONTACTS_PER_ROW)},
                   "expected_gpu_hours": {"arm": arm_gpu_h, "aa": AGREE_GPU_H_PER_1080},
                   "plan_budget_is_run_cumulative": True},
        "claim_boundary": "No superiority, generalisation, component-causal, held-out, confirmatory or paper-scale claim; a no-harm admission of one Reviewer policy, never reported as a gain.",
        "failure_policy": protocol["failure_policy"],
        "not_authorized": ["any flight before the cells are flipped and the receipt is minted", "--allow-output-change on the re-pin tool",
                           "any Planner, Solver, store or roster change", "reporting the cell as a gain", "re-flying or re-scoring any sealed cell"],
        "population": {"count": 1080, "split_identity_hash": arm["split_identity_hash"], "split_role": "discovery",
                       "partition": "TRAIN Fold A 1,080", "fold_b_contact_authorized": False, "test_contact_authorized": False},
        "registered_hashes": {key: {"composed_config": ids[key]["composed_config_hash"], "protocol": ids[key]["protocol_hash"]} for key in CELLS},
        "service": {"expected_session_id": SESSION, "model_fragment": arm["model_fragment"], "slots": 4, "slot_tokens": 24576,
                    "note": "the resident SLURP np4 session; the flight attaches only, never spawns or stops"},
    }
    draft_sha = wjson(PACKAGE + "/root-admission-draft-v1.json", draft)

    readme = render_readme(args, summary, proof, fs, locked_first, expected, expected_lo, expected_hi, r01c_wrong_rate,
                           base_wrong_rate, gpu, offline_split, confound, ids, caps, smoke_caps, arm_gpu_h, expected_arm_contacts)
    readme_sha = wr(PACKAGE + "/README.md", readme)
    fence = json.dumps({"stage3_measurement": measurement}, indent=2, ensure_ascii=False, sort_keys=True)
    prereg = f"""# Cell REV-TFRL-1: preregistration

Registered {args.registered_at[:10]} at study commit `{args.study_commit}`, before any contact, from the committed AGREE
arm fragments by script (decision 58) with one pin moved, under owner decision 165. Development numbers only (owner
decisions 28 and 86); never a test claim. The design, the credit table and the offline selection are in
[`{Path(PACKAGE).name}/README.md`]({Path(PACKAGE).name}/README.md).

## The cell

| item | value |
| --- | --- |
| base (= the in-chain A/A) | the AGREE arm (w_agree 1.0, k 60, fuse 8-1-8; sealed `{AGREE_RUN}`, intent {AGREE_OFFICIAL['intent_accuracy']} / SLU-F1 {AGREE_OFFICIAL['slu_f1']}) with G5's Reviewer instruction `{G5_TEMPLATE}` |
| factor | `{THE_ONE_PIN}`: `{G5_TEMPLATE}` -> `{NEW_TEMPLATE}` (sha256 `{proof['new']['sha256']}`), the contrastive review form selected offline |
| unchanged | roster (TRAIN Fold A 1,080), geometry (np4 x 24,576), session, program and its 11-contact ceiling, the agreement term, the three stores, the Perception / Solver / Planner templates, normaliser, scorers, budgets; `phase_tools` absent |
| in-chain replicate | `{aa['run_id']}` |
| admission | NO HARM (owner decision 127): intent CI95 lower bound against the in-chain A/A not below -{H_INTENT}, SLU lower bound not below -{H_SLU}; never reported as a gain |
| declared expectation | {expected:+.2f} pp intent, the measured transfer of the offline selection statistic (below the benefit bar; claims_benefit false) |
| node credit (beside the verdict) | loop value over the trajectory's own first draft on each arm, per-class credit table |
| runs | `{arm['run_id']}` / `{arm['fit']['run_id']}`; `{aa['run_id']}` / `{aa['fit']['run_id']}`; `{smoke['run_id']}` / `{smoke['fit']['run_id']}`; read `{READ_ROW}` |
| composed config hashes | arm `{arm['composed_config_hash']}`; A/A `{aa['composed_config_hash']}`; smoke `{smoke['composed_config_hash']}` |
| protocol hashes | arm `{arm['protocol_hash']}`; A/A `{aa['protocol_hash']}`; smoke `{smoke['protocol_hash']}` |
| split identity | arm and A/A `{arm['split_identity_hash']}`; smoke `{smoke['split_identity_hash']}` |
| stage3_algorithm | `{ALGORITHM_ID}` (arm and smoke, operators_used `context_application`); `none` on the A/A |

## Decision rule (fixed here)

{no_harm_rule}

## Expectation (measured, decision 139)

{expectation_arithmetic}

## The confound, stated before contact

{confound}

## The measurement declaration

```json
{fence}
```

## Prohibitions

Never reported as a gain. No Fold A gold was used for selection. No paper-scale profile, no test-split, Fold B or DEV
contact, no re-flying of any sealed cell, no second factor. No flight before root mints the decision receipt and the
cells are flipped; `--allow-output-change` is never passed.
"""
    prereg_sha = wr(PREREG, prereg)

    ledger_state = "not-requested"
    if args.append_ledger:
        ledger_state = append_ledger(args, ids=ids, plan_shas=plan_shas, expected=expected, summary_sha=summary_sha, proof=proof)
    print(json.dumps({"package": PACKAGE, "expected_effect_pp": expected,
                      "written": {"README.md": readme_sha, "registered-facts-v1.json": facts_sha,
                                  "protocol-registered-v1.json": protocol_sha, "analysis-recipe-v1.json": recipe_sha,
                                  "root-admission-draft-v1.json": draft_sha, "credit-table-summary-v1.json": summary_sha,
                                  "instruction-edit-proof-v1.json": proof_sha, Path(PREREG).name: prereg_sha,
                                  **{f"plan[{r}]": s for r, s in plan_shas.items()}},
                      "exposure_ledger": ledger_state,
                      "identity": {k: {"run_id": ids[k]["run_id"], "composed_config_hash": ids[k]["composed_config_hash"],
                                       "protocol_hash": ids[k]["protocol_hash"],
                                       "diff": ids[k]["composed_config_diff_against_the_agree_parent"]} for k in CELLS}},
                     indent=2, sort_keys=True))
    return 0


def _credit_rows(table: dict) -> str:
    head = ("| pre-review class | visits | REVISE % | revised | intent changed | intent helped / hurt | "
            "entity helped / hurt | entity-error delta |\n| --- | ---: | ---: | ---: | ---: | --- | --- | ---: |\n")
    lines = []
    for cls, c in table.items():
        visits = c.get("visits", 0)
        rev = c.get("route_REVISE", 0)
        lines.append(f"| {cls} | {visits:,} | {100 * rev / visits if visits else 0:.2f} | {c.get('revised', 0)} | "
                     f"{c.get('revised_intent_changed', 0)} | {c.get('intent_helped', 0)} / {c.get('intent_hurt', 0)} | "
                     f"{c.get('entity_helped', 0)} / {c.get('entity_hurt', 0)} | {c.get('entity_errors_delta', 0.0):+.2f} |")
    return head + "\n".join(lines)


def render_readme(args, summary, proof, fs, locked_first, expected, lo, hi, r01c_rate, base_rate, gpu, split, confound,
                  ids, caps, smoke_caps, arm_gpu_h, arm_contacts) -> str:
    credit = summary["credit"]
    loop = summary["loop_value"]
    sel_locked = [lb for lb, v in loop.items() if v["use"] == "selection" and lb != "candrec"]
    loop_rows = "\n".join(
        f"| {lb} | {v['use']} | {v['rows']} | {v['revision_events']} | {v['as_built_vs_first_draft']['intent_pp']:+.3f} "
        f"{v['as_built_vs_first_draft']['intent_ci95']} | {v['as_built_vs_first_draft']['slu_pp']:+.3f} "
        f"{v['as_built_vs_first_draft']['slu_ci95']} |" for lb, v in loop.items())
    grid = summary["gate_scope_crossfit"]
    crossfit_lines = "\n".join(
        f"- {g}: fold 0 chose `{v['folds']['0']['policy']}` -> held-out (intent, SLU) {v['folds']['0']['held_out_fold_value']}; "
        f"fold 1 chose `{v['folds']['1']['policy']}` -> held-out {v['folds']['1']['held_out_fold_value']}"
        for g, v in grid.items())
    stance = summary["stance_route"]["selection / locked-v1"]
    narr = credit["selection / locked-v1"]["ALL"].get("narration", 0)
    allv = credit["selection / locked-v1"]["ALL"]["visits"]
    edits = "\n".join(f"- `{e['op']}`: \"{e['source_words']}\" -> \"{e['new_words']}\"" for e in proof["edits_against_the_source"])
    return f"""# REV-TFRL-1: training-free RL optimisation of the Reviewer node (owner decision 165)

Owner decision 165 (2026-09-27, translated): *"nodes like the Reviewer can all be optimised and improved; do not
mechanically throw them away -- use training-free RL to optimise its behaviour on its own."* This package is the
design, the reward signal (the Reviewer's credit table over sealed pools), the offline inner loop, and the first
cell it selects. Registered before contact {args.registered_at[:10]} at study commit `{args.study_commit}` by
Claude Opus 5.5 (worktree `{args.worktree}`, branch `{args.branch}`); all three cells **held**. Nothing here
authorises a flight, a flip or an admission entry. Development numbers only (owner decisions 28 and 86).

**Model-free.** Zero model, server, tokenizer, encoder, embedder, scorer-subprocess, network and GPU contacts; ports
8080 / 8081 untouched. Gold was read OFFLINE on the scoring side only (`data.slurp.load_slurp_split`), and no
utterance, transcript, gold string, Reviewer text or delivered answer is printed or persisted anywhere.

## 1. The reward signal: the Reviewer's credit table

`{CREDIT_SCRIPT}` (read id `{CREDIT_ROW}`, machine outputs `$SPEECHRL_DATA_DIR/{CREDIT_ROOT}/`, numbers-only
twin [`credit-table-summary-v1.json`](credit-table-summary-v1.json)) reads every Reviewer visit of 22 sealed SLURP
arms: for each visit, the pre-review Solver draft's error class (scored offline), the Planner route that followed,
gold-free flags of the Reviewer's text (issue / endorse / none, tool narration, naming another shortlisted intent),
whether the revision changed intent or entities, and the visit's outcome (helped / hurt / neutral on intent and on the
row's entity errors). Every draft is scored with the runtime's own deliver projection and the in-process port of the
official metric; on every single-sample arm the port reproduces the sealed per-sample intent AND SLU counts of the
delivered answer on every row (625/625, 1,080/1,080, 1,000/1,000). On the grouped-Solver pools (ROLL-1, ROLL-AA,
ROLL-2, ROLL-3) the sealed score is of the unprojected committed text, so the port agrees on 94-98 % of rows; the loop
values there compare two drafts under one convention and are internally consistent. R01C and Fold A share no
recording and no utterance (checked from the committed dataset fragments).

**Pools.** SELECTION (TRAIN R01C, outside Fold A): VAR-1 PLAN / PLANR / EX-DIV / EX-K10 / EX-K30 / PER-K16C5, F10
control and empty, evidence-path control, ROLL-1, ROLL-AA (the locked Reviewer form, 6,753 visits), and the sealed
candidate-recovery control arm (the CONTRASTIVE Reviewer form, 1,010 visits). DESCRIPTIVE only: Fold A (PLAN,
PLANr, AGREE A/A, AGREE, ROLL-2, P1; R-PRIM's primitive form separately) and DEV-2000-ADDED (ROLL-3, the two PLAN DEV
arms). No candidate policy is evaluated on a descriptive pool.

### 1a. The locked Reviewer (selection pools, {allv:,} visits)

{_credit_rows(credit['selection / locked-v1'])}

### 1b. The contrastive Reviewer (the sealed candidate-recovery control arm, R01C)

{_credit_rows(credit['selection / contrastive-candrec'])}

### 1c. The locked Reviewer on Fold A (descriptive)

{_credit_rows(credit['fold-a / locked-v1 (descriptive)'])}

**Where the Reviewer is useful, useless, harmful.**

- **Useful, rarely: intent repair.** When the locked loop revises a wrong-intent draft it repairs it often and almost
  never breaks a right one: 64 intent repairs against 9 intent breaks over the selection pools, 22 against 8 on Fold
  A. Its revisions of FALSE-POSITIVE-entity drafts also help (ENT-FP: 17 entity repairs, 1 harm; ENT-MIXED 22 / 2).
- **Useless, mostly: reach.** It routes REVISE on 5.45 % of visits; on drafts whose gold intent sat on Perception's
  own shortlist (the "Solver choice" class) on 8.89 %; on first visits the Planner routes REVISE on only 52 of
  the 554 such drafts (9.39 %). The text
  narrates a tool on {narr:,} of {allv:,} visits ({100 * narr / allv:.1f} %) -- the retired-tool order G5 removes --
  and a Reviewer whose text endorses the draft is followed to ACCEPT on {stance['ENDORSE']['route_ACCEPT']:,} of
  {stance['ENDORSE']['visits']:,} visits.
- **Harmful, on correct drafts' entities.** Its 34 revisions of fully CORRECT drafts broke entities on 19 and intent on
  5 (entity-error delta +65.14 over the selection pools); on Fold A 26 revisions, 13 entity breaks, 3 intent breaks.
- **Net.** The loop's value over its own first drafts is small and mostly positive on intent: from
  {min(loop[lb]['as_built_vs_first_draft']['intent_pp'] for lb in sel_locked):+.2f} to
  {max(loop[lb]['as_built_vs_first_draft']['intent_pp'] for lb in sel_locked):+.2f} pp over the eleven locked selection pools, mean
  {fs['locked_loop_intent_pp_mean']:+.3f}; on Fold A {loop['agree-aa']['as_built_vs_first_draft']['intent_pp']:+.3f} (AGREE A/A) and
  {loop['agree-w1']['as_built_vs_first_draft']['intent_pp']:+.3f} (AGREE); SLU-F1 from
  {min(v['as_built_vs_first_draft']['slu_pp'] for v in loop.values()):+.3f} to {max(v['as_built_vs_first_draft']['slu_pp'] for v in loop.values()):+.3f} over all 22 arms, most intervals spanning zero.
- **The contrastive form acts on almost every row and harms little.** It routes REVISE on 46.24 % of visits (57-58 %
  on wrong-intent drafts, 33 % on correct ones), yet its 65 revisions of correct drafts broke intent once and entities
  4 times, and over all 386 revisions it repaired intent 19 times against 3 breaks and cut the entity-error count by
  51.3. Its loop moved intent **{fs['contrastive_loop_intent_pp']:+.2f} pp** over its own first drafts.

### 1d. The loop value per pool (delivered answer minus the same trajectory's first Solver draft)

| pool | use | rows | revision events | intent pp [CI95] | SLU-F1 pp [CI95] |
| --- | --- | ---: | ---: | --- | --- |
{loop_rows}

## 2. The optimisation design (node-scoped, training-free)

**Policy parameters of the Reviewer node.** (i) its instruction text; (ii) the evidence it is shown (today the whole
episode history: the eight boundary entries, twenty exemplars and slot cards, Perception's shortlist, the Solver
draft -- the "top-2 contrast" is already inside that history and the instruction decides whether the node uses it);
(iii) the intervention trigger (when its verdict may change the answer); (iv) the revision scope (what a revision may
change).

**Algorithm `{ALGORITHM_ID}`**, applied NODE-SCOPED as owner decision 165 rules it (per-node credit: the Reviewer's
revise / keep decisions and their outcomes in the sealed pools are the reward signal); its update step is a reflective
proposal in GEPA's manner (arXiv:2507.19457) restricted to one node, and every step is scored where this rig can see: (1) *rollout* -- the sealed pools already on disk and the flights
this design queues; (2) *scoring* -- offline, per draft, against gold on the scoring side; (3) *credit
assignment* -- per Reviewer VISIT, by the pre-review draft's error class; (4) *update* -- a reflective proposal of the
node's policy from the credit table (the proposer reads the table, names the failing class, and edits the policy for
it); (5) *selection* -- over sealed pools of TRAIN rows outside Fold A; (6) *context application* -- one flight of the
selected policy beside its in-chain A/A. The key property: **every trajectory seals the pre-review draft beside the
delivered answer, so the node's own effect (its loop value) is a paired within-trajectory contrast with no flight
offset** -- the between-flight band that hides small system effects does not enter the node's credit.

**What is scored offline and what needs a flight.**

Offline, exactly (zero GPU):
{chr(10).join('- ' + s for s in split['scored_offline_exactly'])}

Needs a flight:
{chr(10).join('- ' + s for s in split['needs_a_flight'])}

**Round 1, run here.** The gate x scope grid (13 gates x 3 scopes over the sealed revision events, both Reviewer forms)
with a two-fold cross-fit by utterance:

{crossfit_lines}

No gate and no scope beats honouring every revision: the existing revisions are net useful on intent and the node's
deficit is REACH, which a gate can only reduce. So the loop selects on the one dimension a sealed alternative exists
for -- the Reviewer's FORM -- by the node's own loop value on the SAME 625 R01C rows:

| form | loop value, intent pp |
| --- | ---: |
| locked (mean of {len(fs['locked_pools'])} sealed pools) | {fs['locked_loop_intent_pp_mean']:+.3f} |
| contrastive (the candidate-recovery control arm) | {fs['contrastive_loop_intent_pp']:+.2f} |
| **paired difference** | **{fs['paired_difference_intent_pp']:+.3f} [{fs['paired_difference_ci95'][0]:+.3f}, {fs['paired_difference_ci95'][1]:+.3f}]** |

**The reflective update** (the proposer's edit, [`instruction-edit-proof-v1.json`](instruction-edit-proof-v1.json)):
the selected form's text, adapted to this plan and changed in nothing else --

{edits}

`configs/{NEW_TEMPLATE}` (sha256 `{proof['new']['sha256']}`, {proof['new']['words']} words, {proof['words_kept_in_order_from_the_source']} kept in order from the source).

**Selection data.** R01C (625 TRAIN construction rows, disjoint from Fold A); the decision-162 filler chunks, which
decision 168 places on Fold B's 1,080 TRAIN rows (outside Fold A), are the substrate of later rounds. Fold A gold entered the credit table
descriptively and never a selection.

**The read.** TRAIN Fold A 1,080, the in-chain A/A = the base (AGREE + G5's Reviewer text), intent primary, SLU-F1
guard, admitted on NO HARM, never reported as a gain; the node credit (loop value, per-class table) on both arms
beside it.

**Expectation (measured only, decision 139).** The paired difference {fs['paired_difference_intent_pp']:+.3f} pp was
measured where {100 * r01c_rate:.2f} % of first drafts had the wrong intent; the base has {100 * base_rate:.2f} %
(AGREE, intent {AGREE_OFFICIAL['intent_accuracy']}). A review loop acts only on wrong drafts, so the transfer is
{fs['paired_difference_intent_pp']:.3f} x {base_rate:.4f} / {r01c_rate:.4f} = **{expected:+.2f} pp** (interval {lo:+.2f} to
{hi:+.2f}). That is below the 2.5 pp cross-flight benefit bar and below the intent own-null half-width {H_INTENT}, so
the cell claims no benefit: `admission` `no-harm`, `claims_benefit` false, `expected_effect_pp` {expected}.

**The confound.** {confound}

**GPU budget.** Rate: {gpu['rate_source']}. Offline rounds: 0 GPU-h. This cell: smoke about 0.01 GPU-h; A/A about
{AGREE_GPU_H_PER_1080} GPU-h; arm about {arm_contacts:,} contacts, about {arm_gpu_h} GPU-h; total about
{round(AGREE_GPU_H_PER_1080 + arm_gpu_h + 0.01, 1)} GPU-h (caps {caps['generation_calls_cap']:,} generation contacts and
{caps['gpu_hours_fit_inclusive']} GPU-h per cell are ceilings; smoke {smoke_caps['generation_calls_cap']} / {smoke_caps['gpu_hours_fit_inclusive']}).
Next rounds: {gpu['next_round_selection_flights']}

**Round 2 (queued by this design, not registered here).** Decision 165 names G5 as the node's first, no-harm step and
the Planner as the next node on the same route. The proposer reads REV-TFRL-1's own sealed credit table. If
the arm's REVISE reach lands near the source arm's but its correct-draft harm is higher, the next candidate is the
revision-scope text on the Solver side or the Planner's routing criterion (the source arm's other two texts), each a
one-node variant flown on R01C / filler rows in ONE campaign with the as-built control and read by loop value; if the
reach itself does not transfer, the next candidate is the Reviewer shown the top-2 contrast explicitly (a typed
evidence line: the draft's intent and Perception's strongest competitor, each with its boundary entry and exemplar
count), which needs one engineering item (a Reviewer evidence view) before it can be registered.

## 3. The registered cell

| cell | run id | Reviewer template | role |
| --- | --- | --- | --- |
| arm | `{ids['arm']['run_id']}` | `{NEW_TEMPLATE}` | the selected policy |
| in-chain A/A | `{ids['aa']['run_id']}` | `{G5_TEMPLATE}` | the base, same chain |
| smoke | `{ids['smoke']['run_id']}` | `{NEW_TEMPLATE}` | four rows, form only |

Derived by `{DERIVE_SCRIPT}` from the committed AGREE fragments; the composed-config diff against the AGREE parent is
the one pin plus bookkeeping (`registered-facts-v1.json`), re-proven by `{CONFIG_TEST}`. Every supply the flip mints
for the arm and the A/A must carry the sealed AGREE output digest `{AGREE_SUPPLY_OUTPUT_SHA}` (the Reviewer text is not
an input to the first-phase supply). The READ row `{READ_ROW}` is registered with the flight (`analysis-recipe-v1.json`
`run_ids.read`).

**Mint, flip, queue.** Root countersigns the eight DRAFT exposure rows, mints `{DECISION_RELPATH}` (id `{DECISION_ID}`,
six eligible run ids) with `scripts/flights/revtfrl/revtfrl_mint_receipt.py`, flips with
`scripts/flights/revtfrl/revtfrl_flip.sh` (the generic re-pin loop over the three `revtfrl_repin_*.sh`, converged at one
HEAD), then queues `scripts/flights/revtfrl/batch_chain_revtfrl.sh` behind whatever occupies the np4 session (decision 77).

| file | what it holds |
| --- | --- |
| `../{Path(PREREG).name}` | the preregistration and the `stage3_measurement` fence |
| `credit-table-summary-v1.json` | the credit read's numbers (per pool, per class, triggers, loop values, grid, form selection) |
| `instruction-edit-proof-v1.json` | the proposer's edit list against the sealed source text |
| `registered-facts-v1.json` | every measured fact, the diffs, the CANONICAL `stage3_measurement` |
| `protocol-registered-v1.json` | identities, hashes, the rule, the expectation, the confound |
| `*-plan-registered-v1.json` | the six flight plans |
| `analysis-recipe-v1.json` | the paired read plus the node credit; `run_ids.read` = `{READ_ROW}` |
| `root-admission-draft-v1.json` | the decision receipt root mints |
"""


MODEL_TOOL_ARM = ("Frozen Q4_K_M decoder-only c98304 np4 max512; promoted EVO-FOLDS-V2 speech packets; NO native tool authority "
                  "on any role; prompt bytes the AGREE arm's except the Reviewer instruction (the contrastive review form)")
MODEL_TOOL_AA = ("Frozen Q4_K_M decoder-only c98304 np4 max512; promoted EVO-FOLDS-V2 speech packets; NO native tool authority "
                 "on any role; prompt bytes the AGREE arm's except the Reviewer instruction (G5's repaired text)")
INHERITED = ("TRAIN Fold A discovery rows already exposed by the sealed anchors, B-cells, PLAN, PLANr, ROLL-2, CONV, the AGREE "
             "family, KPROBE, G5 and COMP-1 (flown or queued at registration); this cell adds no new row to the fold and opens no "
             "split. Prior exposure is inherited in full.")


def append_ledger(args, *, ids, plan_shas, expected, summary_sha, proof) -> str:
    """Six DRAFT flight rows, the model-free credit read row and the READ row. Idempotent by run id; no '|'."""

    text = rd(LEDGER)
    eligible = [ids["arm"]["run_id"], ids["arm"]["fit"]["run_id"], ids["aa"]["run_id"], ids["aa"]["fit"]["run_id"],
                ids["smoke"]["run_id"], ids["smoke"]["fit"]["run_id"]]

    def notes(key: str, kind: str) -> str:
        identity = ids[key]
        run_id = identity["fit"]["run_id"] if kind == "fit" else identity["run_id"]
        attempt = identity["fit"]["attempt_id"] if kind == "fit" else identity["attempt_id"]
        declaration = (
            f"admission no-harm, harm_margin_pp {H_SLU} (intent {H_INTENT}, SLU {H_SLU}), claims_benefit false, expected_effect_pp {expected} (measured transfer), measurement_design cross-flight-with-in-chain-replicate, replicate_run_id {ids['aa']['run_id']}, rows 1080"
            if key == "arm" else
            f"measurement_design cross-flight-with-in-chain-replicate, claims_benefit false, expected_effect_pp 0.0, replicate_run_id {ids['arm']['run_id']}, rows 1080 (the instrument)"
            if key == "aa" else "measurement_design form-proof, claims_benefit false, expected_effect_pp 0.0, rows 4")
        return (
            f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) {args.registered_at[:10]} at study commit "
            f"{args.study_commit} by the REV-TFRL-1 registration agent (worktree {args.worktree}, branch {args.branch}); owner "
            f"decision 165. This registration performs no contact and authorises none. Plan SHA256 {plan_shas[run_id]}; attempt "
            f"{attempt}. Protocol hash {identity['protocol_hash']}; composed config {identity['composed_config_hash']}; expected "
            f"session {SESSION} (attach only). READINESS HELD: root mints {DECISION_RELPATH} (decision id {DECISION_ID}) with the "
            f"six eligible run ids {', '.join(eligible)}, then re-pins with scripts/flights/repin_cell.py --set-ready, which mints "
            f"each cell's own first-phase supply (item E16; expected output digest {AGREE_SUPPLY_OUTPUT_SHA}); --allow-output-change "
            f"must never be passed. ONE PIN: {THE_ONE_PIN} {G5_TEMPLATE} -> {NEW_TEMPLATE} (sha256 {proof['new']['sha256']}) on the "
            f"arm and the smoke, the A/A keeping the G5 file. Measurement declaration ({GATE}): {declaration}. The read row is "
            f"{READ_ROW}. Stop and preserve on the first failure; AT MOST ONE root-diagnosed recovery re-registration. No "
            f"paper-scale profile, no test-split contact, no admission entry from this row."
        )

    def row(key: str, kind: str) -> str:
        identity = ids[key]
        budget = identity["family_budget"]
        is_fit = kind == "fit"
        run_id = identity["fit"]["run_id"] if is_fit else identity["run_id"]
        scope = FLIGHT_PROSE[key] + (" -- FIT spend identity, request envelopes only, no generation" if is_fit else "") + ": " + (
            "the AGREE arm with the Reviewer instruction moved to the contrastive review form selected offline, read on no harm against the in-chain A/A with the node credit beside it"
            if key == "arm" else
            "the AGREE arm with G5's Reviewer instruction re-flown in the same chain as the within-chain null"
            if key == "aa" else
            "the contrastive Reviewer instruction on the first four rows of the unchanged roster; structural form only, never scored")
        cells = ["", args.registered_at, run_id, "bounded-discovery-probe", scope,
                 MODEL_TOOL_AA if key == "aa" else MODEL_TOOL_ARM, f"slurp TRAIN Fold A {identity['rows']}", "discovery",
                 identity["split_identity_hash"], "no",
                 str(budget["fit_endpoint_calls_cap"] if is_fit else budget["generation_calls_cap"]),
                 str(budget["repeated_speech_audio_seconds_cap"]), str(budget["gpu_hours_fit_inclusive"]), INHERITED,
                 f"{PACKAGE}/{PREFIX[key]}{kind}-plan-registered-v1.json", notes(key, kind), ""]
        return " | ".join(cells).strip()

    credit_row = " | ".join([
        "", args.registered_at, CREDIT_ROW, "model-free-check",
        ("The Reviewer node's per-visit credit table over 22 sealed SLURP arms (selection pools TRAIN R01C outside Fold A; Fold A "
         "and DEV descriptive), the loop value of each arm over its own first drafts, gold-free trigger reach, the gate x scope "
         "policy grid with a two-fold cross-fit on the selection pools, and the Reviewer-form selection statistic (owner decision 165)."),
        f"No model, tokenizer, encoder, embedder, server or scorer-subprocess contact: {CREDIT_SCRIPT} over sealed phases, outputs and scores; gold read offline through data.slurp.load_slurp_split on the scoring side only; the in-process port of the official metric; 4 workers",
        "slurp TRAIN R01C 625, TRAIN Fold A 1080, DEV-2000-ADDED 1000 (sealed phase summaries; ids, classes and counts only)",
        "discovery",
        ("f56bc386776421aec2d8001d8697611b01c9b0562885a462759b15531e2f4515 (TRAIN R01C, selection); "
         "61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6 (TRAIN Fold A, descriptive); "
         "ee6c43cd4dd8fc2a583d2dd053e799c2d002efa3755fcd092ba7c7565431bf67 (DEV-2000-ADDED, descriptive)"),
        "yes", "0", "0", "0.0",
        "No new speech exposure; every row read was already exposed by the arm that sealed it. Gold read offline for scoring only; Fold A and DEV gold never used for selection. Prior exposure inherited in full.",
        f"{SUMMARY}",
        (f"REGISTERED AT THE READ (DRAFT, root countersignature pending) {args.registered_at[:10]}: a descriptive model-free read run "
         f"once by the registration agent on its own worktree before the cell it informs was registered; the pre-computation is "
         f"recorded here because a read is registered before any cell rests on it. Summary {SUMMARY} SHA256 {summary_sha}; "
         f"machine outputs $SPEECHRL_DATA_DIR/{CREDIT_ROOT}/ (report.json, visits.jsonl, tables.md, content-sha256.json). "
         "Status DESCRIPTIVE: admits nothing, registers nothing by itself."),
        "",
    ]).strip()
    read_row = " | ".join([
        "", args.registered_at, READ_ROW, "model-free-check",
        (f"The cell REV-TFRL-1 read (recipe slurp-stage3-revtfrl-fold-a-paired-analysis-v1): the arm {ids['arm']['run_id']} against its "
         f"in-chain A/A {ids['aa']['run_id']} under the no-harm rule, intent primary, official SLU-F1 the guard, and the Reviewer node "
         f"credit (loop value and per-class credit table) on both arms beside it."),
        f"No model, tokenizer, encoder or server contact: {READ_DRIVER} family over the sealed per-sample official scores plus {CREDIT_SCRIPT}'s credit functions over the two sealed phase summaries; paired bootstrap 10,000 draws, seed 20260927",
        "slurp TRAIN Fold A 1080", "discovery", ids["arm"]["split_identity_hash"], "no", "0", "0", "0.0",
        "Reads only sealed manifests of this package and the sealed AGREE family as context; no new audio, gold or reference exposure beyond the offline scoring of drafts.",
        f"{PACKAGE}/analysis-recipe-v1.json",
        (f"REGISTERED WITH THE FLIGHT (DRAFT, root countersignature pending) {args.registered_at[:10]} at study commit {args.study_commit}; "
         f"countersigned after the seal and before any score is read. Analysis root {READ_ROOT}."),
        "",
    ]).strip()

    fresh = {}
    for key in ("arm", "aa", "smoke"):
        for kind in ("generation", "fit"):
            run_id = ids[key]["fit"]["run_id"] if kind == "fit" else ids[key]["run_id"]
            fresh[run_id] = row(key, kind)
    fresh[CREDIT_ROW] = credit_row
    fresh[READ_ROW] = read_row
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
        raise SystemExit("the ledger carries some but not all REV-TFRL-1 rows; refusing to guess")
    if replaced:
        wr(LEDGER, "\n".join(lines))
        return f"replaced-{replaced}"
    header = (
        "\n## Cell REV-TFRL-1: training-free RL optimisation of the Reviewer node -- the arm, its in-chain A/A, its four-row "
        "smoke, the model-free credit read and the paired READ row (DRAFT, root countersignature pending)\n\n"
        "Six unconsumed flight rows, the model-free Reviewer credit read and the READ row the recipe declares. Owner decision "
        "165. None of these rows is countersigned and none authorises a contact.\n\n"
        "| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | split role | "
        "split identity hash | consumed | calls | speech audio seconds | gpu hours | inherited exposure | artifacts | notes |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
    )
    suffix = "" if text.endswith("\n") else "\n"
    wr(LEDGER, text + suffix + header + "\n".join(fresh[r] for r in order) + "\n")
    return "appended"


if __name__ == "__main__":
    raise SystemExit(main())
