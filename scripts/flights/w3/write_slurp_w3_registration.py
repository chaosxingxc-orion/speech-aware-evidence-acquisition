#!/usr/bin/env python3
"""Write the W3 registration package from the committed configs (owner decision 164, knowledge-wave
item W3 as W3a ALONE: the intent contrast cards; re-registered 2026-09-27 by the coordinator ruling
under decision 164's one-change rule, the per-intent exemplar cap W3b of the first registration
dropped).

Reads the two derived fragments, the contrast-card release receipt and the offline read, recomposes
every cell's own hashes, PROVES the composed-config diff against the retained AGREE cells is the ONE
knowledge-content pin (W3a; the Solver exemplar supply is the AGREE arm's, byte for byte), the
contrast release's two frozen source receipts and per-flight bookkeeping,
and writes the package documents, the analysis recipe (with its READ run id), a draft decision
receipt for root and (with ``--append-ledger``) seven DRAFT exposure rows. Config alone: no adapter,
no split load, no lock, no contact; it flips nothing and mints nothing. The Fit gate numbers and the
first-phase supply proof are read from the package's ``preflight-proofs-v1.json``
(``scripts/flights/w3/w3_preflight_proofs.py``).

    python scripts/flights/w3/write_slurp_w3_registration.py --study-commit <sha> \\
        --registered-at 2026-09-27T17:00:00.000000+00:00 \\
        [--append-ledger]
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

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.config import (  # noqa: E402
    compose,
    protocol_hash,
)

PACKAGE = "docs/readiness/2026-09-27-slurp-stage3-w3-contrast-fold-a-v1"
PREREG = PACKAGE + "-preregistration.md"
OFFLINE = PACKAGE + "/offline-estimates-v1.json"
PROOFS = PACKAGE + "/preflight-proofs-v1.json"
CARDS = "docs/receipts/knowledge/slurp-intent-contrast-cards-v1.json"
LEDGER = "docs/exposure-ledger.md"

CELLS = {"arm": "slurp-native-stage3-w3-fold-a-v1", "smoke": "slurp-native-stage3-w3-fold-a-smoke-4-v1"}
PARENTS = {"arm": "slurp-native-stage3-agree-w1-fold-a-v1", "smoke": "slurp-native-stage3-agree-w1-fold-a-smoke-4-v1"}
PREFIX = {"arm": "", "smoke": "smoke-"}
FLIGHT_PROSE = {"arm": "Cell W3", "smoke": "Four-row form smoke of cell W3"}
COMPARATOR_RUN = "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1"
COMPARATOR_ATTEMPT = "attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1"
COMPARATOR_OFFICIAL = {"intent_accuracy": 85.8333, "slu_f1": 65.1575}
SHARED_AA = "SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1"
SHARED_AA_ATTEMPT = "attempt-slurp-native-stage3-wave1-aa-fold-a-generation-v1"
READ_RUN = "SAEA-SLURP-STAGE3-W3-FOLD-A-PAIRED-ANALYSIS-V1"
BUILD_ROW = "SAEA-SLURP-W3-INTENT-CONTRAST-CARDS-BUILD-V1"
OFFLINE_ROW = "SAEA-SLURP-W3-CONTRAST-CAP-OFFLINE-V1"
DECISION_ID = "slurp-stage3-w3-contrast-fold-a-admission-v1"
DECISION_RELPATH = "coordination/slurp-stage3-w3-contrast-fold-a-v1/root-admission-v1.json"
SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"
AGREE_SUPPLY_OUTPUT_SHA = {"arm": "eab5c61e92a47c1723c478f2b7914abade6152b195f676d7d32251f3d18884ae", "smoke": None}
AGREE_SMOKE_SUPPLY = "prepared/SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-SMOKE-4-V1"
FUSE_POLICY = "saea-fuse-supplyfilter-target-cap-v1"

IB = "knowledge_stores.intent-boundaries."
SOLVER = "knowledge_stores.train-exemplars.phase_supply.solver."
PINNED_W3A = [IB + "release.relpath", IB + "release.sha256", IB + "snapshot.relpath", IB + "snapshot.sha256"]
PINNED_W3B = [SOLVER + "fuse_coverage.c", SOLVER + "fuse_coverage.m", SOLVER + "fuse_policy", SOLVER + "k"]
RECEIPTS = "preparation_source_receipts"
BOOKKEEPING_PREFIXES = ("native_contact_fit.", "prepared_phase_supply", "what_this_is")
H_SLU, H_INTENT = 1.2485, 0.9943
CONV = {"rate": 0.457143, "m": 32, "n": 70, "what": "P(intent right | gold boundary card NEWLY DELIVERED to Perception), cell CONV"}
KPROBE = {"rate": 0.436364, "m": 24, "n": 55, "what": "the same conditional rate for the centroid key, cell KPROBE"}
AGREE_RATE = {"calls_used": 4385, "gpu_hours_per_1080": 1.8816, "prefilled_tokens_per_row": 8733.5}

AUDIT = "docs/results/2026-09-27-slurp-knowledge-content-audit.md"
ERRSRC = "docs/results/2026-09-27-slurp-agree-arm-error-sources.md"
SYNTHESIS = "docs/results/2026-09-27-slurp-mechanism-synthesis.md"
INSTRUMENT = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"
OWNER_DECISIONS = "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md"
AGREE_PACKAGE = "docs/readiness/2026-09-26-slurp-stage3-agree-w1-fold-a-v1"
BUILD_SCRIPT = "scripts/build_slurp_intent_contrast_cards.py"
OFFLINE_SCRIPT = "scripts/analysis/slurp_w3_contrast_cap_offline.py"
DERIVE_SCRIPT = "scripts/flights/w3/derive_slurp_w3_cells.py"
CONFIG_TEST = "tests/unit/test_w3_config.py"
FUSER_TEST = "tests/unit/test_kb_policy_target_cap.py"
GATE = "scripts/checks/stage3_effect_floor_check.py"
READ_DRIVER = "scripts/analysis/stage3_paired_read.py (branch fable/launchgate; --stage3 --package)"


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


def identities() -> dict:
    out = {}
    for key, experiment in CELLS.items():
        document = json.loads(rd(f"configs/experiment/{experiment}.json"))
        cell = document["cells"][0]
        composed = compose(REPO_ROOT, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], experiment)
        parent_doc = json.loads(rd(f"configs/experiment/{PARENTS[key]}.json"))
        parent_cell = parent_doc["cells"][0]
        parent = compose(REPO_ROOT, parent_cell["model_fragment"], parent_cell["dataset_fragment"],
                         parent_cell["baseline_fragment"], PARENTS[key])
        baseline_keys = set(json.loads(rd(f"configs/baseline/{parent_cell['baseline_fragment']}.json")))
        experiment_keys = set(document) | set(parent_doc)
        if experiment_keys & baseline_keys:
            raise SystemExit("an experiment fragment overrides a baseline key")
        a, b = flatten(parent.values), flatten(composed.values)
        changed = sorted(k for k in set(a) | set(b) if a.get(k, "<absent>") != b.get(k, "<absent>"))
        diff = {
            "w3a_contrast_store_pins": [k for k in changed if k in PINNED_W3A],
            "w3b_exemplar_cap_pins": [k for k in changed if k in PINNED_W3B],
            "frozen_source_receipts": [k for k in changed if k == RECEIPTS],
            "baseline_bookkeeping_only": [k for k in changed if k.startswith(BOOKKEEPING_PREFIXES)],
            "experiment_fragment_own_block": [k for k in changed if k.split(".", 1)[0] in experiment_keys],
        }
        accounted = {k for group in diff.values() for k in group}
        other = [k for k in changed if k not in accounted]
        if other or diff["w3a_contrast_store_pins"] != sorted(PINNED_W3A) or diff["w3b_exemplar_cap_pins"] != []:
            raise SystemExit(f"{key}: the composed diff is not the W3a pin alone: other={other} diff={diff}")
        if composed.values["knowledge_stores"]["train-exemplars"] != parent.values["knowledge_stores"]["train-exemplars"]:
            raise SystemExit(f"{key}: the train-exemplars store is not the AGREE arm's (W3b must be absent)")
        diff["anything_else"] = other
        added = [entry for entry in composed.values[RECEIPTS] if entry not in parent.values[RECEIPTS]]
        split = document["population"]["split_identity_hash"]
        solver = composed.values["knowledge_stores"]["train-exemplars"]["phase_supply"]["solver"]
        out[key] = {
            "experiment": experiment, "cell": cell["cell_id"], "run_id": cell["run_id"], "attempt_id": cell["attempt_id"],
            "baseline_fragment": cell["baseline_fragment"], "parent_experiment": PARENTS[key],
            "dataset_fragment": cell["dataset_fragment"], "model_fragment": cell["model_fragment"],
            "arm": composed.values["arm"], "rows": document["population"]["count"], "split_identity_hash": split,
            "composed_config_hash": composed.config_hash, "parent_composed_config_hash": parent.config_hash,
            "protocol_hash": protocol_hash(composed.config_hash, composed.values["arm"], split),
            "fit": dict(composed.values["native_contact_fit"]), "family_budget": document["family_budget"],
            "execution_profile": document["execution_profile"], "carrier_lock_key": composed.values["carrier_lock_key"],
            "intent_boundaries_pins": {k: composed.values["knowledge_stores"]["intent-boundaries"][k] for k in ("release", "snapshot")},
            "solver_exemplar_supply": {k: solver[k] for k in ("fuse_policy", "k", "fuse_coverage", "rank_policy", "rank_weights", "tau")},
            "frozen_source_receipts_added": added,
            "composed_config_diff_against_the_agree_cell": diff,
            "readiness": cell["readiness"], "allowed_execution_stages": cell["allowed_execution_stages"],
            "generation_budget_target": document.get("generation_budget", {}).get("target"),
        }
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--study-commit", required=True)
    parser.add_argument("--registered-at", required=True)
    parser.add_argument("--branch", default="fable/w3")
    parser.add_argument("--worktree", default="/home/chao/saea-worktrees/fable-w3")
    parser.add_argument("--append-ledger", action="store_true")
    args = parser.parse_args(argv)
    os.chdir(REPO_ROOT)

    offline = json.loads(rd(OFFLINE))
    cards = json.loads(rd(CARDS))
    tuning = offline["fold_b_tuning"]
    cap, depth = int(tuning["chosen_cap"]), int(tuning["chosen_depth"])
    fold_a = offline["fold_a_estimates"]
    contrast_a = fold_a["contrast_cards"]
    cap_a = fold_a["exemplar_cap"]
    tokens = cards["tokens"]
    release = cards["release"]

    ids = identities()
    arm, smoke = ids["arm"], ids["smoke"]
    caps, smoke_caps = arm["family_budget"], smoke["family_budget"]
    agree_caps = json.loads(rd(f"configs/experiment/{PARENTS['arm']}.json"))["family_budget"]
    if agree_caps != caps:
        raise SystemExit("the arm caps are not the AGREE arithmetic")
    smoke_supply = None
    data_root = os.environ.get("SPEECHRL_DATA_DIR")
    if data_root and (Path(data_root) / AGREE_SMOKE_SUPPLY).is_dir():
        candidates = sorted((Path(data_root) / AGREE_SMOKE_SUPPLY).glob("phase-supply-v*.json"))
        if candidates:
            smoke_supply = json.loads(candidates[-1].read_text(encoding="utf-8"))["output_sha256"]
    AGREE_SUPPLY_OUTPUT_SHA["smoke"] = smoke_supply
    fit_summary = json.loads(Path(PROOFS).read_text(encoding="utf-8")) if Path(PROOFS).is_file() else None

    wrong_rows = contrast_a["wrong_rows"]
    named_before = contrast_a["pair_named_on_a_delivered_card_before"]
    named_after = contrast_a["pair_named_on_a_delivered_card_after"]
    presence = cap_a["wrong_rows"]["gold_zero_to_present"]
    risk_unique = cap_a["right_rows"]["unique_gold_plurality_broken"]
    risk_absolute = cap_a["right_rows"]["absolute_gold_majority_broken"]
    at_cap = tuning["table"][str(cap)]
    below = tuning["table"].get(str(cap - 1))
    newly_named = named_after - named_before
    rereg_date = "2026-09-27"  # the coordinator ruling's date; the re-registration time is args.registered_at
    why_dropped = (
        f"Coordinator ruling (Fable 5.1, {rereg_date}) under owner decision 164's one-change rule: the wave's W3 cell is "
        "re-derived as W3a ALONE -- the intent contrast cards with the Solver exemplar supply restored to exactly the AGREE "
        "arm's (no per-intent exemplar cap). W3b is dropped as a second change with no measured upside: (1) on Fold A the "
        f"cap removes {cap_a['wrong_rows']['wrong_plurality_removed']} wrong-intent pluralities on the "
        f"{cap_a['wrong_rows']['rows']} intent-wrong rows ({OFFLINE} fold_a_estimates.exemplar_cap.wrong_rows."
        "wrong_plurality_removed); (2) on Fold B the chosen cap N = "
        f"{cap} scores GAIN {at_cap['gain_wrong_plurality_removed']} / HARM {at_cap['harm_gold_plurality_removed']} "
        f"({OFFLINE} fold_b_tuning.table[\"{cap}\"]); (3) it changes "
        f"{cap_a['right_rows']['block_changed']} Solver blocks on the {cap_a['right_rows']['rows']} rows the AGREE arm got "
        f"right, lowering the gold exemplar count on {cap_a['right_rows']['gold_count_down']} ({OFFLINE} "
        "fold_a_estimates.exemplar_cap.right_rows.block_changed / gold_count_down)."
    )

    no_harm_rule = (
        "NO-HARM READ (owner decision 164 brief, row 139): against the SHARED wave-1 in-chain A/A "
        f"{SHARED_AA} flown in the same chain, the paired CI95 lower bound of the intent-accuracy delta "
        f"(primary, decision 133) is not below -{H_INTENT} pp AND the paired CI95 lower bound of the official "
        f"pooled SLU-F1 delta (the guard) is not below -{H_SLU} pp -- each metric read at its own Fold A own-null "
        f"half-width ({INSTRUMENT} section 2d). HARMFUL: a measured loss on either metric (CI95 upper bound below "
        "zero, decision 25). A CI that includes zero and clears the margin is the admission. The cell is NEVER "
        "reported as a gain whatever the point estimate: no measured conversion applies to contrast text, so no "
        "expected effect is declared (decision 139). Every verdict carries the "
        "per-scenario table in both weightings, the frontier row (decision 75), the row-level attribution of the "
        "delta to the rows the contrast lines newly name "
        "(membership fixed in offline-estimates-v1.json before contact), and the A/A's own delta against the sealed "
        "AGREE arm as the instrument's reading."
    )
    expectation = {
        "declared_expected_effect_pp": 0.0,
        "claims_benefit": False,
        "why_no_benefit_is_declared": (
            "Row 139: an expectation may be declared only from a measured conversion analogue. The two measured "
            "conversions on this programme are DELIVERY conversions of the gold boundary card to Perception (CONV "
            f"{CONV['m']} of {CONV['n']} = {CONV['rate']}, KPROBE {KPROBE['m']} of {KPROBE['n']} = {KPROBE['rate']}). "
            "W3a delivers nothing new -- the delivered set is the AGREE arm's own, byte for byte -- it changes what "
            "an already-delivered card SAYS, and no contrast text has ever been flown and read. The analogue does not "
            "apply, so the cell is registered as a no-harm read and says so. The 2026-09-27 re-registration as W3a "
            "alone keeps this declaration: the package declares no separate W3a number from a measured basis."
        ),
        "scale_only_not_declared": {
            "note": (
                "For scale only, NOT a declaration and NOT used by any gate: the rows W3a newly reaches times the CONV "
                "delivery rate, as the knowledge audit quoted its own ceilings. 1 row = 0.0926 pp on 1,080 rows. W3a "
                "alone: the rows the dropped cap newly gave a gold exemplar are no longer counted."
            ),
            "contrast_rows_newly_named_on_a_delivered_card": newly_named,
            "rows_times_conv_rate_pp": round(newly_named * CONV["rate"] * 100.0 / 1080.0, 3),
            "rows_ceiling_pp": round(newly_named * 100.0 / 1080.0, 3),
            "first_registration_w3a_plus_w3b_rows_times_conv_rate_pp": round((newly_named + presence) * CONV["rate"] * 100.0 / 1080.0, 3),
        },
    }
    measurement = {
        arm["run_id"]: {
            "admission": "no-harm",
            "claims_benefit": False,
            "expected_effect_pp": 0.0,
            "harm_margin_pp": H_SLU,
            "harm_margin_pp_by_metric": {"intent_accuracy": H_INTENT, "slu_f1": H_SLU},
            "measurement_design": "cross-flight-with-in-chain-replicate",
            "primary_metric": "intent accuracy (scenario_action exact), official pooled SLU-F1 the non-inferiority guard (owner decision 133)",
            "replicate_run_id": SHARED_AA,
            "rows": 1080,
            "note": (
                "A knowledge-content cell registered as a NO-HARM read because no measured conversion applies (row 139; "
                "registered-facts-v1.json expectation). The harm margin is the measured floor of this design at n = 1,080 "
                "-- the Fold A own-null half-width, SLU 1.2485 (the gate's single field) and intent 0.9943 (the primary "
                "metric's own, applied by the read). The delta is read against the SHARED wave-1 in-chain A/A "
                f"{SHARED_AA}, registered by the coordinator and flown in the same chain (rule 3), never against the "
                "sealed AGREE arm alone. Never reported as a gain."
            ),
        },
        smoke["run_id"]: {
            "claims_benefit": False,
            "expected_effect_pp": 0.0,
            "measurement_design": "form-proof",
            "primary_metric": "none (structural form only)",
            "rows": 4,
            "note": (
                "Four rows prove FORM and nothing else: that the contrast release loads, "
                "that every request fits and that the episode completes. Scored by no "
                "one, read by no one (instrument rule 5)."
            ),
        },
    }
    split_note = {
        "affordable": True,
        "registered": False,
        "registered_now": "W3a ALONE, in place of the composed W3 (re-registered in place, same run ids): the how_to_derive recipe below was followed on the coordinator's ruling; W3b alone is not registered",
        "ruling": why_dropped,
        "why_not_registered": "first registration: the brief registered the split only if the coordinator asked; superseded by the re-registration as W3a alone",
        "cost_each": (
            f"about {AGREE_RATE['gpu_hours_per_1080']} GPU hours and about {AGREE_RATE['calls_used']:,} contacts per "
            "1,080-row cell at the sealed AGREE arm's own rate (frontier read), read at the same shared A/A -- so the "
            "attribution split costs about 3.8 GPU hours for the pair"
        ),
        "how_to_derive": (
            "W3a alone = this baseline with the train-exemplars Solver supply restored to AGREE's (fuse_policy "
            "saea-fuse-supplyfilter-v1, k 20, m/c/top_l 20); W3b alone = this baseline with the intent-boundaries pins "
            "and the two added receipts restored to AGREE's. Each is one derive_slurp_w3_cells.py flag away and "
            "re-uses this package's recipe shape."
        ),
        "what_attribution_is_available_without_it": (
            "W3a alone is ONE change against the AGREE arm, so the arm-minus-A/A delta is the contrast cards' by "
            "construction; the row attribution to the fixed membership set of offline-estimates-v1.json (rows whose "
            "pair the contrast lines newly name) remains attribution by exposure"
        ),
    }
    facts = {
        "schema": "saea-registered-facts-v1",
        "_note": (
            "Every model-free measured fact this registration rests on, and the CANONICAL stage3_measurement block "
            f"{GATE} resolves (keyed by run id). The same block is repeated in the preregistration's fenced json for "
            "readability; this copy has precedence."
        ),
        "registered_at_utc": args.registered_at,
        "study_commit_at_registration": args.study_commit,
        "owner_decisions": {
            "164": "the knowledge wave: W3 = intent contrast cards (+ a per-intent exemplar cap in the first registration), prepared now, flip-ready by about 01:00Z 2026-09-28, read at the shared wave-1 A/A",
            "coordinator ruling (under 164's one-change rule)": why_dropped,
            "139": "an expectation is declared only from a measured conversion analogue; otherwise the read is no-harm or form-proof and says so",
            "133": "intent accuracy primary, official SLU-F1 the guard",
            "28 and 86": "TRAIN Fold A numbers are development numbers, never a test claim",
        },
        "rows": 1080,
        "stage3_measurement": measurement,
        "the_item": {
            "evidence": {
                "K1": f"{AUDIT} section 1: every card has exactly one activation sentence and one confusable exclusion, 57.7 % of each card is boilerplate; on 75 of the AGREE arm's 153 intent-wrong rows both the right and the chosen card are delivered and neither names the other; 119 distinct confusion pairs",
                "K6": f"{AUDIT} section 2.3: 38 wrong rows have 0 gold-intent exemplars among the 20; the exemplar majority is the chosen (wrong) intent on 93",
                "error_sources": f"{ERRSRC}: the wrong answer is Perception's first guess on 132 of 153; the 20 exemplars outvote gold on 107 of 152",
                "synthesis": f"{SYNTHESIS}: every gain so far was row-matched CONTENT to the deciding node; every harm a FORM change without content -- so W3 adds content and changes no form it does not pay for in content",
            },
            "w3a": {
                "what": "the intent-boundaries store moves to intent-boundaries-contrast-v1: header, activation boundary, authored exclusion and card-specific limitations verbatim; the shared uncertainty sentence and the shared limitation bullet removed; a contrast section against the card's nearest TRAIN-centroid rivals added",
                "card_format": [
                    "Intent <id>.",
                    "Activation boundary:", "- <authored, verbatim>",
                    "Confusable exclusions:", "- <authored, verbatim>",
                    "Nearest rivals, typical TRAIN words (this intent | rival):",
                    "- <rival intent>: <word>, <word> [<slot type>] | <word>, <word> [<slot type>]   (2-4 lines, nearest first)",
                    "Limitations:", "- <card-specific bullets only, verbatim; the section is absent when the card had none>",
                ],
                "derivation": cards["rule"],
                "release": release,
                "tokens": tokens,
                "rivals_carried_distribution": cards["rivals_carried_distribution"],
                "invariants": cards["invariants"],
                "receipt": {"relpath": CARDS, "sha256": sha_file(CARDS)},
                "build_script": {"relpath": BUILD_SCRIPT, "sha256": sha_file(BUILD_SCRIPT)},
            },
            "w3b_dropped": {
                "status": f"DROPPED {rereg_date}, never flown: the Solver's train-exemplars supply is the AGREE arm's own (saea-fuse-supplyfilter-v1, k 20, c/m/top_l 20)",
                "why_dropped": why_dropped,
                "what": f"(first registration only) the Solver's train-exemplars supply moves from saea-fuse-supplyfilter-v1 at k 20 to {FUSE_POLICY}: walk the pure-cosine ranking, take at most {cap} exemplars per intent, stop at 20; admission depth and recall k {depth}",
                "fuser": {"id": FUSE_POLICY, "module": "src/speech_aware_evidence_acquisition/rails/kb_policy.py", "pure_rule": "select_target_capped", "unit_tests": FUSER_TEST},
                "cap": cap, "depth": depth,
                "fold_b_tuning": tuning,
                "why_this_cap": (
                    f"the declared rule (smallest N whose GAIN >= HARM on TRAIN Fold B) selects N = {cap}: at N = {cap} GAIN "
                    f"{at_cap['gain_wrong_plurality_removed']} / HARM {at_cap['harm_gold_plurality_removed']} / presence "
                    f"{at_cap['gold_presence_gained']}"
                    + (f"; at N = {cap - 1} GAIN {below['gain_wrong_plurality_removed']} / HARM {below['harm_gold_plurality_removed']}" if below else "")
                    + ". Every smaller cap breaks more right-intent pluralities than wrong-intent ones on Fold B, so the "
                    "registered cap is the one that removes no gold majority while still letting other intents into blocks "
                    "one intent used to fill."
                ),
            },
        },
        "fold_a_offline_estimates": {
            "note": "counts only over the AGREE arm's sealed Fold A rows (gold offline); never a tuning input",
            "contrast_cards": contrast_a,
            "exemplar_cap": cap_a,
            "risk": {"right_rows_unique_gold_plurality_broken": risk_unique, "right_rows_absolute_gold_majority_broken": risk_absolute},
            "source": {"relpath": OFFLINE, "sha256": sha_file(OFFLINE), "script": {"relpath": OFFLINE_SCRIPT, "sha256": sha_file(OFFLINE_SCRIPT)}},
        },
        "expectation": expectation,
        "attribution_split": split_note,
        "fit_gate": {
            "proofs": ({"relpath": PROOFS, "sha256": sha_file(PROOFS), "line": fit_summary["line"],
                        "per_cell": {key: {"per_phase": cell["check"]["per_phase"], "blockers": cell["check"]["blockers"],
                                           "first_phase_supply_output_sha256": cell["first_phase_supply_proof"]["output_sha256"],
                                           "identical_to_agree": cell["first_phase_supply_proof"]["identical"]}
                                     for key, cell in fit_summary["cells"].items()},
                        "realised_agree_requests": fit_summary["realised_agree_requests"]}
                       if fit_summary else None),
            "headroom_before": "the AGREE arm registered Solver 21,278 of 21,504 usable tokens (np4 slot 24,576 minus the 3,072 reserve): 226 tokens of headroom on the pre-flight placeholder count",
            "w3_spends": "none by construction on the cards (every card at or below its flown token count, all 60 together -{} tokens); the Solver exemplar block is the AGREE arm's own".format(-tokens["delta_all_60"]),
            "what_must_be_freed": "nothing for W3 alone; W1's saving is not needed and is not spent",
        },
        "identity": {key: {k: v for k, v in ids[key].items() if k not in ("composed_config_diff_against_the_agree_cell", "readiness")} for key in CELLS},
        "composed_config_diff_against_the_agree_cell": {key: ids[key]["composed_config_diff_against_the_agree_cell"] for key in CELLS} | {
            "note": f"flattened composed configs (core.config.compose); re-proven by {CONFIG_TEST}",
        },
        "comparator": {
            "run_id": COMPARATOR_RUN, "attempt_id": COMPARATOR_ATTEMPT, "official": COMPARATOR_OFFICIAL, "never_reflown": True,
            "in_chain_replicate": {"run_id": SHARED_AA, "registered_by": "the coordinator (the shared wave-1 A/A)", "why": "rule 4 refuses a cross-flight contrast with no in-chain replicate"},
            "margins": {"h_slu": H_SLU, "h_intent": H_INTENT, "source": f"the plan's own null on this roster ({INSTRUMENT} section 2d)"},
        },
        "no_harm_rule": no_harm_rule,
        "byte_identity_expectation": {
            "agree_arm_supply_output_sha256": AGREE_SUPPLY_OUTPUT_SHA["arm"],
            "agree_smoke_supply_output_sha256": AGREE_SUPPLY_OUTPUT_SHA["smoke"],
            "claim": (
                "the first-phase (Perception) supply reads facet keys, the agreement table and value ids; W3 moves none of "
                "them (the contrast release keeps every facet and value id), so every supply the flip mints must carry the "
                "AGREE family's own output digest -- a different digest means the boundary retrieval moved: stop and report"
            ),
        },
        "implementation_identity": (
            "rails/kb_policy.py gains the registered fuser (the canonical registration site). Its sha256 is part of every "
            "prepared supply's identity (core.flight.runtime._phase_seed_inputs sources.implementation), so on the merge "
            "every READY-but-unflown cell of another family must be re-pinned at the flight commit before it flies; the "
            "flown default selection is unchanged (tests/unit/test_kb_policy_target_cap.py and the existing kb_policy tests)."
        ),
        "budget_arithmetic": {
            "caps_are_the_agree_arithmetic": True,
            "arm_family_budget": caps, "smoke_family_budget": smoke_caps,
            "derivation": [
                "generation_calls_cap = 1,080 rows x 11 contacts per row (perception 1, solver 1, reviewer 3, planner 1, max_revisions 1) = 11,880; the smoke 4 x 11 = 44",
                "fit_endpoint_calls_cap = 4 x generation = 47,520 (smoke 176); native_task_contract_calls_cap 6,480 (smoke 24); repeated_speech_audio_seconds_cap 33,930 (smoke 117); gpu_hours_fit_inclusive 12.0 (smoke 1.0) -- the AGREE family's own ceilings",
                f"expected spend at the sealed AGREE arm's own realized rate: about {AGREE_RATE['calls_used']:,} contacts and about {AGREE_RATE['gpu_hours_per_1080']} GPU hours per 1,080 rows",
                "official_complete_scoring_jobs = 1 for the arm, one job over the complete manifest through core.scoring_batch, never sharded; the smoke is never scored",
            ],
            "run_cumulative": "every cap binds across ALL attempts of a run id",
        },
        "prohibitions": [
            "Never reported as a gain (no benefit declared).",
            "No test-split contact, no DEV read; Fold B was read OFFLINE for tuning only (gold labels and pinned vectors, no contact).",
            "No re-flying of the sealed AGREE arm; no registration of the shared A/A by this package.",
            "No third factor: roster, geometry, session, program, agreement term, slot store, role graph, templates and scorers are AGREE's.",
            "No paper-scale profile.",
            "No flight before root mints the decision receipt and the cells are flipped.",
        ],
        "authority_relpaths": [AUDIT, ERRSRC, SYNTHESIS, INSTRUMENT, OWNER_DECISIONS, AGREE_PACKAGE + "/README.md", GATE],
    }
    facts_sha = wjson(PACKAGE + "/registered-facts-v1.json", facts)

    protocol = {
        "schema": "saea-registered-protocol-v1",
        "protocol_id": "slurp-stage3-w3-contrast-fold-a-protocol-v1",
        "registered_at_utc": args.registered_at,
        "study_commit_at_registration": args.study_commit,
        "source_tree": f"studies/speech-aware-evidence-acquisition, worktree {args.worktree}, branch {args.branch}",
        "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP",
        "the_question": (
            "With the intent cards carrying TRAIN-derived contrast lines in place of boilerplate (no more tokens per card) "
            "and nothing else changed (W3a alone; the Solver exemplar block is the AGREE arm's own), do the official intent "
            "accuracy and pooled SLU-F1 on TRAIN Fold A 1,080 stay within the design's own null, read against the shared "
            "wave-1 in-chain A/A? A no-harm question, because no measured conversion applies (row 139)."
        ),
        "one_pin": {"w3a": facts["the_item"]["w3a"]["what"]},
        "dropped": {"w3b": facts["the_item"]["w3b_dropped"]["what"], "why": why_dropped},
        "unchanged": (
            "everything but the one pin, the contrast release's two frozen source receipts and per-flight bookkeeping: "
            f"the roster (TRAIN Fold A 1,080, split identity {arm['split_identity_hash']}), the model fragment and serving "
            f"geometry (np4 x 24,576), the session {SESSION}, the phase program and its 11-contact ceiling, the agreement "
            "term (w_agree 1.0, k 60, fuse 8-1-8), the Solver exemplar supply (saea-fuse-supplyfilter-v1 at k 20), "
            "the facet keys, the slot-contracts store, the role graph, the response "
            "formats, every template, the deliver normaliser, the scorers and every budget"
        ),
        "cells": {key: {k: ids[key][k] for k in ("cell", "experiment", "run_id", "attempt_id", "rows", "composed_config_hash", "protocol_hash", "split_identity_hash")}
                  | {"fit_run_id": ids[key]["fit"]["run_id"], "fit_attempt_id": ids[key]["fit"]["attempt_id"]} for key in CELLS},
        "comparator": facts["comparator"],
        "decision_rule_fixed_here": no_harm_rule,
        "expectation": expectation,
        "what_a_harmful_read_would_mean": (
            "That replacing boilerplate with contrast text costs the deciding nodes more than the content gives -- read row "
            "by row against the fixed membership set before anything is withdrawn; W3a is the only change, so no further "
            "split is needed."
        ),
        "model_free_proofs_landed_before_contact": {
            "contrast_release": {"receipt": CARDS, "reloaded": release["reloaded_through_load_knowledge_store_binding"], "tokens": tokens},
            "offline_read_validation": offline["validation"],
            "composed_config_diff": facts["composed_config_diff_against_the_agree_cell"],
        },
        "development_numbers_only": "Every number this family will produce is a TRAIN Fold A construction-fold development number (owner decisions 28 and 86) and is never a test claim.",
        "failure_policy": "Stop and preserve on the first failure. AT MOST ONE root-diagnosed recovery re-registration; a second failure closes the cell and the fix is proven on a four-row dry run. The budget is run-cumulative across attempts.",
        "authority": f"owner decision 164 and rows 28, 86, 101, 133, 139 ({OWNER_DECISIONS}); {AUDIT}; {ERRSRC}; {SYNTHESIS}; the measurement instrument {INSTRUMENT}; the AGREE chain shape {AGREE_PACKAGE}",
        "prohibitions": facts["prohibitions"],
    }
    protocol_sha = wjson(PACKAGE + "/protocol-registered-v1.json", protocol)

    plan_shas: dict[str, str] = {}
    for key in ("arm", "smoke"):
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
                    "Shared core.flight.cli campaign in the coordinator's wave-1 chain beside the shared in-chain A/A "
                    f"{SHARED_AA}; this family's own plan configs/campaign/slurp-native-stage3-w3-fold-a-v1.json carries the "
                    "arm alone; one official score per generation cell at finalize."
                    if key == "arm" else
                    "Shared core.flight.cli worker on this cell alone; the smoke is deliberately outside the campaign plan and is never scored."
                ),
                "prepared_phase_supply": {
                    "relpath": f"prepared/{identity['run_id']}/phase-supply-v1.json",
                    "sha256": "MINTED_AT_THE_FLIP",
                    "expected_output_sha256": AGREE_SUPPLY_OUTPUT_SHA[key],
                    "note": facts["byte_identity_expectation"]["claim"],
                },
                "protocol_document": {"relpath": PACKAGE + "/protocol-registered-v1.json", "sha256": protocol_sha},
                "one_pin": protocol["one_pin"],
                "purpose": (
                    f"{run_id}: {FLIGHT_PROSE[key]}. "
                    + ("It measures request envelopes only and reads nothing." if is_fit
                       else no_harm_rule if key == "arm"
                       else "Structural form proof only: no score and no read.")
                ),
                "quality_read_gate": (
                    "No task-quality read before the complete sealed manifest, the exact ordered outputs, the native phase "
                    f"summary and the single successful complete official TRAIN score all exist for BOTH the W3 arm and the "
                    f"shared in-chain A/A {SHARED_AA}. A verdict computed against the sealed AGREE arm alone is refused."
                ),
            }
            name = f"{PREFIX[key]}{kind}-plan-registered-v1.json"
            plan_shas[run_id] = wjson(f"{PACKAGE}/{name}", plan_doc)

    recipe = {
        "schema": "saea-slurp-paired-analysis-recipe-v1",
        "recipe_id": "slurp-stage3-w3-contrast-fold-a-paired-analysis-v1",
        "title": "Cell W3 -- the standard paired roster read on intent + SLU at the shared wave-1 in-chain A/A, under the no-harm rule, with row attribution to the fixed contrast membership set (W3a alone)",
        "registered_at_utc": args.registered_at,
        "read_run_id": READ_RUN,
        "run_ids": {"read": READ_RUN, "arm": arm["run_id"], "in_chain_replicate": SHARED_AA, "comparator": COMPARATOR_RUN},
        "arms": {
            "arm": {"run_id": arm["run_id"], "attempt_id": arm["attempt_id"], "fit_run_id": arm["fit"]["run_id"],
                    "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL", "outputs_sha256": "PENDING_SEAL"},
            "in_chain_replicate": {"run_id": SHARED_AA, "attempt_id": SHARED_AA_ATTEMPT, "registered_by": "the coordinator",
                                   "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL", "outputs_sha256": "PENDING_SEAL",
                                   "role": "the within-chain null the delta is read at (the attempt id is the coordinator's registration; read it from that package if it differs)"},
            "comparator": {"run_id": COMPARATOR_RUN, "attempt_id": COMPARATOR_ATTEMPT, "role": "the sealed AGREE arm, context beside the A/A, never the bar"},
        },
        "resampling": {"bootstrap_draws": 10000, "metrics": ["scenario_action_exact", "slu_f1_f1"], "seed": 20260927, "unit": "row (paired)"},
        "decision_rule": no_harm_rule,
        "margins": {"h_intent": H_INTENT, "h_slu": H_SLU},
        "membership_sets": {
            "relpath": OFFLINE, "sha256": sha_file(OFFLINE),
            "fixed_before_contact": True,
            "note": "the offline read's Fold A counts define the attribution groups; the per-row membership is recomputed by the same script at read time from the same pinned inputs and must reproduce these counts exactly",
        },
        "steps": [
            f"1. Refuse unless BOTH the W3 arm and the shared A/A {SHARED_AA} carry a COMPLETE sealed manifest at 1,080 rows with the committed roster's ids, each with one successful complete official TRAIN score, and their config hashes are the registered ones.",
            "2. Structural stage: on the arm, the Perception consumption's delivered boundary ids must equal the AGREE arm's on every row (W3 moves no key); the Solver consumption must equal the AGREE arm's 20 exemplars on every row (W3a moves no exemplar; the offline read's validation re-derived them 1080 of 1080); the delivered card bodies must hash to the contrast release. A mismatch is an engineering defect, not an effect, and closes the read.",
            "3. Score once per arm over the complete manifest with the standard scorer (slurp-slu-official-train through core.scoring_batch, never sharded).",
            "4. Paired row bootstrap (10,000 draws, seed 20260927) of the arm minus shared A/A delta on intent accuracy and on official pooled SLU-F1; the same against the sealed AGREE arm BESIDE it, never instead of it.",
            f"5. Apply the no-harm rule: ADMITTED iff the intent lower bound >= -{H_INTENT} and the SLU lower bound >= -{H_SLU}; HARMFUL iff either upper bound < 0 (decision 25); otherwise NOT ADMITTED (width). Never write 'gain' or 'no gain'.",
            "6. Row attribution: the intent transition table (A/A -> arm) on the rows whose chosen-vs-gold pair the contrast lines newly name and on the rest -- counts only.",
            "7. Report beside every number: the per-scenario table in the natural-mixture and equal-scenario weightings; the frontier row (decision 75); the Solver prompt tokens per contact from the sealed COST records against the A/A; the A/A's own delta against the sealed AGREE arm as the instrument's reading.",
        ],
        "read_driver": READ_DRIVER,
        "output": {"analysis_root": f"analysis/{READ_RUN}"},
        "boundary": "A development read on a TRAIN construction fold (owner decisions 28 and 86); never a test claim, never a generalisation claim, and it admits nothing beyond the no-harm entry it is registered for. No utterance text, transcript, gold label string, knowledge body or model output is printed or persisted.",
    }
    recipe_sha = wjson(PACKAGE + "/analysis-recipe-v1.json", recipe)

    eligible = [arm["run_id"], arm["fit"]["run_id"], smoke["run_id"], smoke["fit"]["run_id"]]
    draft = {
        "_draft_note": (
            "A DRAFT written by the registration agent, in the repository, for root to mint on the data root with "
            "scripts/flights/w3/w3_mint_receipt.py, which sets status 'decided', stamps recorded_at_utc, re-hashes every "
            "antecedent path at mint time and refuses to overwrite. It authorises nothing while its status is not 'decided'."
        ),
        "schema": "saea-campaign-decision-v1",
        "decision_id": DECISION_ID,
        "status": "DRAFT-NOT-MINTED",
        "recorded_at_utc": None,
        "owner": "root",
        "coordinator": "Claude Opus 5.5",
        "eligible_run_ids": eligible,
        "cell_kind": "Stage-3 knowledge-content cell (label none), registered as a no-harm read. One arm on TRAIN Fold A 1,080 read at the shared wave-1 in-chain A/A (the coordinator's, under its own receipt), and a four-row form smoke outside the chain.",
        "decision": (
            "Fly cell W3 as W3a alone: the retained AGREE arm with the intent-boundaries store moved to the contrast-card "
            "release (the Solver exemplar supply the AGREE arm's own), against the sealed AGREE arm read at the shared "
            f"wave-1 in-chain A/A {SHARED_AA}. Admission is NO HARM at the Fold A own-null half-widths (intent {H_INTENT}, "
            f"SLU {H_SLU}); the cell is never reported as a gain."
        ),
        "authorization_basis": f"Owner decision 164 (the knowledge wave); rows 139, 133, 28, 86, 101, 77; the binding instrument note {INSTRUMENT}.",
        "antecedents": {
            "owner_decisions": {"path": OWNER_DECISIONS, "sha256": sha_file(OWNER_DECISIONS)},
            "instrument_note": {"path": INSTRUMENT, "sha256": sha_file(INSTRUMENT)},
            "preregistration": {"path": PREREG, "sha256": None},
            "readiness_readme": {"path": PACKAGE + "/README.md", "sha256": None},
            "protocol": {"path": PACKAGE + "/protocol-registered-v1.json", "sha256": protocol_sha},
            "registered_facts": {"path": PACKAGE + "/registered-facts-v1.json", "sha256": facts_sha},
            "analysis_recipe": {"path": PACKAGE + "/analysis-recipe-v1.json", "sha256": recipe_sha},
            "offline_estimates": {"path": OFFLINE, "sha256": sha_file(OFFLINE)},
            "preflight_proofs": {"path": PROOFS, "sha256": sha_file(PROOFS) if Path(PROOFS).is_file() else None},
            "contrast_card_receipt": {"path": CARDS, "sha256": sha_file(CARDS)},
            "config_proof": {"path": CONFIG_TEST, "sha256": sha_file(CONFIG_TEST) if Path(CONFIG_TEST).is_file() else None},
            "base_cell": f"the retained AGREE arm ({COMPARATOR_RUN}): W3 is that fragment with one knowledge-content pin (W3a alone; re-registered {rereg_date})",
            "registration_base_commit": args.study_commit,
        },
        "budget": {**{k: caps[k] for k in sorted(caps)}, "smoke": smoke_caps, "paid_api_calls": 0,
                   "expected_contacts_per_1080_row_cell": AGREE_RATE["calls_used"], "plan_budget_is_run_cumulative": True},
        "claim_boundary": "No superiority, generalisation, component-causal, held-out, confirmatory or paper-scale claim; a no-harm read of one knowledge-content cell, never reported as a gain.",
        "failure_policy": protocol["failure_policy"],
        "not_authorized": [
            "any flight before the cells are flipped and the receipt is minted",
            "the shared wave-1 A/A (the coordinator's own receipt)",
            "touching the resident np4 session by anyone but the coordinator",
            "any ASR, transcript, encoder or paid-API contact",
            "re-flying or re-scoring any sealed cell",
            "--allow-output-change on the re-pin tool",
            "reporting the cell as a gain",
        ],
        "population": {"count": 1080, "split_identity_hash": arm["split_identity_hash"], "split_role": "discovery", "partition": "TRAIN Fold A 1,080", "fold_b_contact_authorized": False, "test_contact_authorized": False},
        "prepared_phase_supply": {"note": "minted by scripts/flights/repin_cell.py at the flip (each cell's own, item E16); expected output digest " + AGREE_SUPPLY_OUTPUT_SHA["arm"]},
        "registered_hashes": {"note": f"the values of the fragments exactly as committed at {args.study_commit}; repin_cell.py recomputes them at the flip.",
                              **{key: {"composed_config": ids[key]["composed_config_hash"], "protocol": ids[key]["protocol_hash"]} for key in CELLS}},
        "service": {"expected_session_id": SESSION, "model_fragment": arm["model_fragment"], "slots": 4, "slot_tokens": 24576, "decoder_only": True, "no_child_start_stop": True},
    }
    draft_sha = wjson(PACKAGE + "/root-admission-draft-v1.json", draft)

    fence = json.dumps({"stage3_measurement": measurement}, indent=2, ensure_ascii=False, sort_keys=True)
    fit_line = "not measured in this write (run scripts/flights/w3/w3_preflight_proofs.py first)"
    if fit_summary:
        fit_line = fit_summary["line"] + " Receipt: [`preflight-proofs-v1.json`](preflight-proofs-v1.json)."
    table_b = "\n".join(
        f"| {n} | {row['gain_wrong_plurality_removed']} | {row['harm_gold_plurality_removed']} | {row['net']} | {row['gold_presence_gained']} | {row['absolute_gold_majority_broken']} | {row['blocks_changed']} | {row['blocks_filled_to_20']} |"
        for n, row in sorted(tuning["table"].items(), key=lambda item: -int(item[0])) if int(n) >= max(cap - 4, 1)
    )
    wa, ra = cap_a["wrong_rows"], cap_a["right_rows"]
    arm_phases = fit_summary["cells"]["arm"]["check"]["per_phase"] if fit_summary else None
    after_line = (
        "perception {:,} / reviewer {:,} / planner {:,} / Solver {:,} rendered tokens, Solver operational margin {} and "
        "physical margin {:,}; first-phase supply digests arm {} and smoke {}".format(
            arm_phases["perception"]["rendered_text_tokens"], arm_phases["reviewer"]["rendered_text_tokens"],
            arm_phases["planner"]["rendered_text_tokens"], arm_phases["solver"]["rendered_text_tokens"],
            arm_phases["solver"]["operational_margin_tokens"], arm_phases["solver"]["physical_margin_tokens"],
            fit_summary["cells"]["arm"]["first_phase_supply_proof"]["output_sha256"][:8],
            fit_summary["cells"]["smoke"]["first_phase_supply_proof"]["output_sha256"][:8],
        ) if fit_summary else "not measured in this write"
    )
    readme = f"""# Cell W3a: intent contrast cards (W3 re-registered as W3a alone)

Registered before contact {args.registered_at} at study commit `{args.study_commit}` (owner decision 164,
knowledge-wave item W3). First registered 2026-09-27 at study commit `701bd63a` as W3a + W3b; **re-registered in place as W3a
alone** (see [Re-registration](#re-registration) below). Both cells are **held**. Nothing here authorises a flight, a
flip or an admission entry.

**Why.** [`{AUDIT}`](../../results/{Path(AUDIT).name}) K1: every intent card carries one
activation sentence and one confusable exclusion, and 57.7 % of it is boilerplate; on 75 of the AGREE arm's 153
intent-wrong rows both the right and the chosen card are delivered and neither names the other. The mechanism
synthesis: every gain so far was row-matched CONTENT to the deciding node -- so W3a adds content and pays for it
inside the tokens it removes.

**W3a -- contrast cards, the one change** (`{BUILD_SCRIPT}`, release `{release['namespace']}`, content hash
`{release['snapshot']['content_sha256']}`, receipt [`{CARDS}`](../../receipts/knowledge/{Path(CARDS).name})). Each card keeps its
header, activation boundary, authored exclusion and card-specific limitation bullets verbatim; the uncertainty sentence
(identical on all 60) and the shared limitation bullet are removed; a section
`Nearest rivals, typical TRAIN words (this intent | rival):` adds one line per nearest TRAIN-centroid rival (KPROBE's
centroid keys), `- <rival>: <word>, <word> [<slot type>] | <word>, <word> [<slot type>]` -- the two words most typical of
each side's TRAIN requests against the other (document-frequency gap, outside annotated slot spans, at least 3
utterances, function words and the wake word excluded) and the slot type one side carries and the other does not, from
the R01-excluded pool (8,554 utterances, disjoint from Fold A, Fold B and R01, checked). Rivals are added nearest-first
only while the card tokenises to no more tokens than the flown card (the G5 measurement's vocab-only tokenizer):
**{tokens['all_60_cards_flown']:,} -> {tokens['all_60_cards_rebuilt']:,} tokens over the 60 cards ({tokens['delta_all_60']:+,}), max per-card delta
{tokens['max_card_delta']:+}**, rivals carried per card {json.dumps(cards['rivals_carried_distribution'])}. Facets, keys and value ids are
unchanged, so Perception's delivered set is the AGREE arm's own.

**Against the AGREE bytes** (composed configs, `registered-facts-v1.json` `composed_config_diff_against_the_agree_cell`,
re-proven by `tests/unit/test_w3_config.py`): only `knowledge_stores.intent-boundaries.{{release,snapshot}}.{{relpath,sha256}}`
move (intent-boundaries-v1 -> intent-boundaries-contrast-v1), plus the contrast release's two frozen source receipts and
per-flight bookkeeping. The Solver's `knowledge_stores.train-exemplars.phase_supply.solver` is the AGREE arm's, byte for
byte (`saea-fuse-supplyfilter-v1`, `k` 20, `c`/`m`/`top_l` 20) -- the condition
`scripts/flights/wave/wave_preconditions.py` checks before the wave flips or flies.

**Fold A offline table** (the AGREE arm's own chosen intents and delivered sets; counts only):

| quantity | value |
| --- | ---: |
| intent-wrong rows | {wrong_rows} |
| pair named on a delivered card, before (authored exclusion alone) | {named_before} |
| pair named on a delivered card, after (plus the contrast lines) | {named_after} |
| of the {contrast_a['both_cards_delivered_neither_names_the_other_before']} rows with both cards delivered and neither naming the other, named after | {contrast_a['of_which_named_after']} |

**The expectation, and its basis.** None is declared (`expected_effect_pp` 0.0, `claims_benefit` false): row 139
allows an expectation only from a measured conversion analogue, and the two this programme has (CONV 32 of 70 = 0.457,
KPROBE 24 of 55 = 0.436) are conversions of a NEWLY DELIVERED gold card at Perception. W3a delivers nothing new -- it
changes what an already-delivered card says. So W3a is registered as a **no-harm read** and says so; the package
declares no separate W3a number from a measured basis, so the re-registration keeps 0.0. For scale only (not declared,
not gated): the {newly_named} newly named rows at the CONV rate would be
{expectation['scale_only_not_declared']['rows_times_conv_rate_pp']} pp.

**Fit.** {fit_line}

**`stage3_measurement`.** The arm declares `admission` `no-harm`, `harm_margin_pp` {H_SLU} (by metric intent {H_INTENT} /
SLU {H_SLU}), `claims_benefit` false, `expected_effect_pp` 0.0, `measurement_design`
`cross-flight-with-in-chain-replicate`, `replicate_run_id` **`{SHARED_AA}`** -- the shared wave-1 A/A the coordinator
registers (not this package). The READ is registered with the flight: `analysis-recipe-v1.json` declares
`run_ids.read` **`{READ_RUN}`** and its DRAFT ledger row exists.

**Attribution.** W3a is one change against the AGREE arm, so the arm-minus-A/A delta is the contrast cards' by
construction; the recipe's row attribution (step 6) splits it over the rows whose pair the contrast lines newly name.

**Implementation identity.** `rails/kb_policy.py` carries the registered target-capped fuser (merged with the first
registration); W3a does not use it, and the flown default selection is unchanged. Every prepared supply's identity
hashes that module, so any READY-but-unflown cell of another family is re-pinned at its flight commit.

**Mint, flip, queue.** Root countersigns the seven DRAFT rows, mints `{DECISION_RELPATH}` (id `{DECISION_ID}`) with
`scripts/flights/w3/w3_mint_receipt.py` (four eligible ids), flips inside the wave with
`scripts/flights/wave/wave_flip.sh` (smoke, then arm, converging at one HEAD; `--allow-output-change` never passed; the
minted supplies must carry the AGREE family's own output digests), and the wave chain flies the arm as step 2 of
`scripts/flights/wave/batch_chain_wave.sh`, A/A -> W1 -> W3a -> W4 (decision 77).

| file | what it holds |
| --- | --- |
| `../{Path(PREREG).name}` | the preregistration, including the `stage3_measurement` fence |
| `registered-facts-v1.json` | every model-free fact, the composed diff, the CANONICAL `stage3_measurement`, the ruling |
| `protocol-registered-v1.json` | identities, hashes, the no-harm rule, the claim boundary |
| `generation-plan-registered-v1.json` / `fit-plan-registered-v1.json` | the arm's plans |
| `smoke-generation-plan-registered-v1.json` / `smoke-fit-plan-registered-v1.json` | the smoke's plans |
| `analysis-recipe-v1.json` | the paired read at the shared A/A, with `run_ids.read` |
| `offline-estimates-v1.json` | the contrast membership counts, the request-size projection, and the dropped cap's Fold B tuning and Fold A counts |
| `preflight-proofs-v1.json` | the held check per phase (Fit), the scratch-minted first-phase supply digests, the realised AGREE request sizes |
| `root-admission-draft-v1.json` | the decision receipt root mints with `w3_mint_receipt.py` |

**Not authorised by this package.** No flight before the receipt is minted and the cells are flipped; no contact by this
registration; no re-flying of the comparator; no test-split or DEV read (Fold B was read offline, for tuning only); no
second or third factor; no report of a gain; no admission entry.

## Re-registration

**{rereg_date} -- coordinator ruling (Fable 5.1) under owner decision 164's one-change rule; re-registered
{args.registered_at}.** The wave's W3 cell is
re-derived as **W3a alone**: the intent contrast cards with the Solver exemplar supply restored to exactly the AGREE
arm's (no per-intent exemplar cap). W3b is dropped because it is a second change with no measured upside. Each fact,
with the file and section it comes from ("the first README" is this file as committed at `94c88036`):

1. **On Fold A the cap removes no wrong-intent plurality**: {wa['wrong_plurality_removed']} of the {wa['rows']} intent-wrong
   rows (`offline-estimates-v1.json` `fold_a_estimates.exemplar_cap.wrong_rows.wrong_plurality_removed`; the first
   README's "Fold A offline table", row "wrong rows whose wrong-intent plurality the cap removes").
2. **On Fold B a cap of {cap} scores GAIN {at_cap['gain_wrong_plurality_removed']} / HARM {at_cap['harm_gold_plurality_removed']}**
   (`offline-estimates-v1.json` `fold_b_tuning.table["{cap}"]`; the first README's "W3b -- per-intent exemplar cap"
   section, Fold B tuning table, row N = {cap}). Every smaller cap scores HARM above GAIN on Fold B (same table, N <= {cap - 1}).
3. **It changes {ra['block_changed']} Solver blocks on the {ra['rows']} rows the AGREE arm got right**, lowering the gold
   exemplar count on {ra['gold_count_down']} of them (`offline-estimates-v1.json`
   `fold_a_estimates.exemplar_cap.right_rows.block_changed` and `gold_count_down`; the first README's "Fold A offline
   table", row "right rows whose block the cap changes / whose gold count falls").

**How it was derived.** Exactly `registered-facts-v1.json` `attribution_split.how_to_derive` for W3a alone ("this
baseline with the train-exemplars Solver supply restored to AGREE's (fuse_policy saea-fuse-supplyfilter-v1, k 20,
m/c/top_l 20)"), by `scripts/flights/w3/derive_slurp_w3_cells.py`, which now derives W3a alone. Same run ids, same
attempt ids, same package directory: a re-registration of unflown cells. The seven DRAFT exposure rows are rewritten in
place by run id (never duplicated), each carrying a RE-REGISTERED note.

**What moved.** The four config fragments (composed and protocol hashes: arm `{arm['composed_config_hash'][:12]}` /
`{arm['protocol_hash'][:12]}`, smoke `{smoke['composed_config_hash'][:12]}` / `{smoke['protocol_hash'][:12]}`), the plans, the
protocol, the facts, the recipe (steps 2 and 6), the draft receipt, the preregistration, the pre-flight proofs and the
ledger rows. The pre-flight proofs were re-run at `{args.study_commit}`: before (the first registration, `701bd63a`)
perception 19,087 / reviewer 18,951 / planner 18,890 / Solver 20,916 rendered tokens, Solver operational margin 45 and
physical margin 3,117; supply digests arm eab5c61e and smoke 308601c5. After: {after_line}. The numbers are identical
because the pre-flight bound counts the twenty longest exemplars whether the cap is present or not.

**What did not move.** The contrast-card release, the offline read (kept as the record of the dropped cap and as the
source of the contrast membership set), `expected_effect_pp` 0.0 (the package declares no separate W3a number from a
measured basis), the harm margins, the READ run id, the four eligible run ids, the caps and the shared A/A.
"""
    readme_sha = wr(PACKAGE + "/README.md", readme)

    prereg = f"""# Preregistration: cell W3 as W3a alone -- intent contrast cards (TRAIN Fold A 1,080)

Registered before contact {args.registered_at} at study commit `{args.study_commit}` by the W3 registration agent
(worktree `{args.worktree}`, branch `{args.branch}`). Owner decision 164. The package README
(`{PACKAGE}/README.md`) carries the evidence, the card format, the tuning table and the Fold A table; this note fixes
the question, the arms, the rule and the fence. RE-REGISTERED {args.registered_at} in place of the first registration
(W3a + W3b, study commit `701bd63a`): {why_dropped}

## The question

{protocol['the_question']}

## The arms

- **W3 arm** `{arm['run_id']}` (cell `{arm['cell']}`, composed `{arm['composed_config_hash']}`, protocol `{arm['protocol_hash']}`):
  the retained AGREE arm with ONE change (W3a alone): {facts['the_item']['w3a']['what']}. The Solver exemplar supply is
  the AGREE arm's own; the first registration's per-intent cap (W3b) is dropped.
- **Shared in-chain A/A** `{SHARED_AA}`: registered by the coordinator, flown in the same chain.
- **Comparator** `{COMPARATOR_RUN}` (sealed AGREE arm, official intent {COMPARATOR_OFFICIAL['intent_accuracy']} / SLU-F1
  {COMPARATOR_OFFICIAL['slu_f1']}): context beside the A/A, never re-flown, never the bar.
- **Four-row smoke** `{smoke['run_id']}`: form only, never scored.

## The rule

{no_harm_rule}

## The expectation

{expectation['why_no_benefit_is_declared']}

## The measurement fence

```json
{fence}
```

## Boundary

Development numbers only (owner decisions 28 and 86). No test-split or DEV read; TRAIN Fold B was read OFFLINE, gold
labels and pinned vectors only, to tune the cap that is no longer flown. No utterance text, gold string, knowledge body or model output is
committed. The shared A/A, the flip and the flight are the coordinator's.
"""
    prereg_sha = wr(PREREG, prereg)

    ledger_state = "not-requested"
    if args.append_ledger:
        ledger_state = append_ledger(args, ids=ids, plan_shas=plan_shas, cap=cap, depth=depth, cards=cards, offline=offline)

    print(json.dumps({
        "package": PACKAGE,
        "written": {"README.md": readme_sha, "registered-facts-v1.json": facts_sha, "protocol-registered-v1.json": protocol_sha,
                    "analysis-recipe-v1.json": recipe_sha, "root-admission-draft-v1.json": draft_sha,
                    Path(PREREG).name: prereg_sha, **{f"plan[{run}]": sha for run, sha in plan_shas.items()}},
        "exposure_ledger": ledger_state,
        "identity": {key: {"run_id": ids[key]["run_id"], "composed_config_hash": ids[key]["composed_config_hash"],
                           "protocol_hash": ids[key]["protocol_hash"]} for key in CELLS},
        "cap": cap, "depth": depth,
    }, indent=2, sort_keys=True))
    return 0


MODEL_TOOL = (
    "Frozen Q4_K_M decoder-only c98304 np4 max512; promoted EVO-FOLDS-V2 speech packets; NO native tool authority on any "
    "role; prompt bytes the retained AGREE arm's except the intent-boundary card bodies (contrast release, no card longer "
    "than flown); the Solver exemplar block is the AGREE arm's own (W3a alone)"
)
INHERITED = (
    "TRAIN Fold A discovery rows already exposed by the sealed dual-store anchor, the released direct anchor, cells "
    "B0/B0r, B1 and its twin, B4b, B4b-rep, B5e, B7a, B7a-v2, B8b-anchor, B1-notool, PLAN, PLANr, ROLL-2, CONV, the AGREE "
    "family, KPROBE, COMP-1 and G5 (flown or in flight at registration); this cell adds no new row to the fold and opens no "
    "split. Prior exposure is inherited in full."
)


def append_ledger(args, *, ids, plan_shas, cap, depth, cards, offline) -> str:
    """Four DRAFT flight rows, one DRAFT READ row and two model-free rows. Idempotent: replace-or-append by
    run id. No cell may contain a literal '|'."""

    text = rd(LEDGER)
    eligible = [ids["arm"]["run_id"], ids["arm"]["fit"]["run_id"], ids["smoke"]["run_id"], ids["smoke"]["fit"]["run_id"]]
    release = cards["release"]
    tokens = cards["tokens"]

    def notes(key: str, kind: str) -> str:
        identity = ids[key]
        is_fit = kind == "fit"
        run_id = identity["fit"]["run_id"] if is_fit else identity["run_id"]
        attempt = identity["fit"]["attempt_id"] if is_fit else identity["attempt_id"]
        declaration = (
            f"admission no-harm, harm_margin_pp {H_SLU} (by metric: intent {H_INTENT}, SLU {H_SLU}), claims_benefit false, expected_effect_pp 0.0, measurement_design cross-flight-with-in-chain-replicate, replicate_run_id {SHARED_AA}, rows 1080"
            if key == "arm" else
            "measurement_design form-proof, claims_benefit false, expected_effect_pp 0.0, rows 4"
        )
        return (
            f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) {args.registered_at[:10]} at study commit "
            f"{args.study_commit} by the W3 registration agent (worktree {args.worktree}, branch {args.branch}). This "
            f"registration performs no contact and authorises none. Plan SHA256 {plan_shas[run_id]}; attempt {attempt}. "
            f"Protocol hash {identity['protocol_hash']}; composed config {identity['composed_config_hash']}; expected session "
            f"{SESSION} (attach only, never spawn or stop). READINESS HELD: root mints {DECISION_RELPATH} (decision id "
            f"{DECISION_ID}) from the package's root-admission-draft-v1.json with the four eligible run ids {', '.join(eligible)} "
            f"and this family's caps, then flips with scripts/flights/w3/w3_flip.sh, which mints each cell's OWN first-phase "
            f"supply under its own run id (item E16; expected output digest the AGREE family's own, arm "
            f"{AGREE_SUPPLY_OUTPUT_SHA['arm']}); the requirements lists are EMPTY and --allow-output-change must never be passed. "
            f"Every hash in this row moves at the flip and the re-pin tool rewrites it. ONE PIN (owner decision 164; W3a alone): the "
            f"intent-boundaries store moves to {release['namespace']} (content {release['snapshot']['content_sha256']}, release "
            f"{release['release']['sha256']}), 60 cards {tokens['all_60_cards_flown']} -> {tokens['all_60_cards_rebuilt']} tokens, "
            f"no card above its flown count; the Solver exemplar supply is the AGREE arm's own. Measurement declaration ({GATE}): {declaration} -- declared at the top level of "
            f"{PACKAGE}/registered-facts-v1.json and repeated in the preregistration fence. THE RULE: admitted on NO HARM against "
            f"the shared wave-1 in-chain A/A at the Fold A half-widths, HARMFUL on a measured loss (decision 25), NEVER reported "
            f"as a gain (no measured conversion applies, row 139). The READ is {READ_RUN}. Caps are the AGREE arithmetic. Stop "
            f"and preserve on the first failure; AT MOST ONE root-diagnosed recovery re-registration. No paper-scale profile, no "
            f"confirmatory split, no test-split contact, no comparator re-flight and no admission entry from this row. "
            f"RE-REGISTERED {args.registered_at[:10]} (coordinator ruling of 2026-09-27 under owner decision 164's one-change rule): W3 is "
            f"W3a alone -- the per-intent exemplar cap W3b of the first registration (study commit 701bd63a) is dropped "
            f"(Fold A: 0 wrong-intent pluralities removed; Fold B N = {cap}: GAIN 0 / HARM 0; 700 Solver blocks changed on rows "
            f"the AGREE arm got right; {PACKAGE}/README.md, Re-registration); same run id, this row rewritten in place, not "
            f"duplicated."
        )

    def row(key: str, kind: str) -> str:
        identity = ids[key]
        is_fit = kind == "fit"
        budget = identity["family_budget"]
        run_id = identity["fit"]["run_id"] if is_fit else identity["run_id"]
        scope = FLIGHT_PROSE[key] + (" -- FIT spend identity, request envelopes only, no generation" if is_fit else "") + ": " + (
            "the retained AGREE arm with the intent cards carrying TRAIN-derived contrast lines in place of boilerplate (W3a alone; the Solver exemplar supply the AGREE arm's own), read on no harm against the shared wave-1 in-chain A/A"
            if key == "arm" else
            "the same one pin (W3a alone) on the first four rows of the unchanged roster; structural form only, never scored"
        )
        cells = [
            "", args.registered_at, run_id, "bounded-discovery-probe", scope, MODEL_TOOL,
            f"slurp TRAIN Fold A {identity['rows']}", "discovery", identity["split_identity_hash"], "no",
            str(budget["fit_endpoint_calls_cap"] if is_fit else budget["generation_calls_cap"]),
            str(budget["repeated_speech_audio_seconds_cap"]), str(budget["gpu_hours_fit_inclusive"]), INHERITED,
            f"{PACKAGE}/{PREFIX[key]}{kind}-plan-registered-v1.json", notes(key, kind), "",
        ]
        return " | ".join(cells).strip()

    read_row = " | ".join([
        "", args.registered_at, READ_RUN, "model-free-check",
        (
            f"The cell W3 read (W3a alone): the contrast-card arm against the shared wave-1 in-chain A/A {SHARED_AA} "
            f"under the no-harm rule (harm margins intent {H_INTENT} / SLU {H_SLU}), per-scenario tables in both weightings, "
            "the frontier row and the row attribution to the fixed contrast membership set."
        ),
        "No model, tokenizer, encoder or server contact: the registered read driver over the sealed per-sample official scores and sealed receipts.",
        "slurp TRAIN Fold A 1080", "discovery", ids["arm"]["split_identity_hash"], "no", "0", "0", "0.0",
        "Reads only sealed manifests of this package, the shared A/A and the registered comparator; no new audio, gold or reference exposure.",
        f"{PACKAGE}/analysis-recipe-v1.json",
        (
            f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) {args.registered_at[:10]} at study commit "
            f"{args.study_commit} with the flight rows, as the pre-launch gate requires; runs only after both seals. No "
            "utterance text, gold, transcript, knowledge body or model output is printed or persisted. RE-REGISTERED "
            f"{args.registered_at[:10]} (coordinator ruling of 2026-09-27): W3 is W3a alone (the exemplar cap dropped; {PACKAGE}/README.md, Re-registration); "
            "same run id, rewritten in place."
        ),
        "",
    ]).strip()

    build_row = " | ".join([
        "", args.registered_at[:10], BUILD_ROW, "model-free-check",
        (
            "Build and release the W3 intent contrast cards: intent-boundaries-v1 bodies with the shared uncertainty sentence "
            "and shared limitation bullet replaced by contrast lines against each card's nearest centroid rivals (typical TRAIN "
            "words and slot types per side from the R01-excluded pool), no card above its flown token count; facets, keys and "
            "value ids unchanged; released under the data root and re-loaded through load_knowledge_store_binding. Zero model, "
            "server, encoder, embedder, scorer, network, GPU and paid-API contacts; ports 8080/8081 untouched."
        ),
        f"no model or tool contact; local vocab-only llama-tokenize process ({tokens['tokenizer']['invocations']} invocations) over the rebuilt card texts",
        "slurp TRAIN construction pool (R01-excluded, 8,554 utterances; disjoint from Fold A, Fold B and R01, checked); pinned centroid keys",
        "construction", release["source_split_identity_hash"], "no", "0", "0", "0",
        "No new speech exposure: TRAIN construction text already released as the exemplar pool; no evaluated row's gold is read.",
        CARDS,
        (
            f"REGISTERED BEFORE RESULT READING (DRAFT, root countersignature pending) {args.registered_at[:10]} at study commit "
            f"{args.study_commit}. Release {release['namespace']}: snapshot content {release['snapshot']['content_sha256']}, "
            f"release.json {release['release']['sha256']}, completion.json {release['completion']['sha256']}, source "
            f"{release['source']['sha256']}; builder {BUILD_SCRIPT}. Tokens over 60 cards {tokens['all_60_cards_flown']} -> "
            f"{tokens['all_60_cards_rebuilt']}, max per-card delta {tokens['max_card_delta']}. The receipt carries no card text "
            "or cue word. It authorises nothing."
        ),
        "",
    ]).strip()

    offline_row = " | ".join([
        "", args.registered_at[:10], OFFLINE_ROW, "model-free-check",
        (
            "Tune the W3 per-intent exemplar cap on TRAIN Fold B offline (gold labels and pinned vectors, the registered "
            "fuser's own selection function) and count the Fold A estimates of both W3 changes against the AGREE arm's sealed "
            "rows; validation: the re-derived Fold A top 20 equals the AGREE Solver consumption and the Fold B top 20 "
            "reproduces the pinned Fold B agreement table. Zero model, server, encoder, embedder, scorer, tokenizer, network, "
            "GPU and paid-API contacts."
        ),
        "no model or tool contact; float64 arithmetic over sealed vector files",
        "slurp TRAIN Fold B 1080 (gold offline, tuning) and TRAIN Fold A 1080 (sealed AGREE outputs, counts only)",
        "discovery", ids["arm"]["split_identity_hash"], "no", "0", "0", "0",
        "No new speech exposure: pinned vectors and sealed outputs already exposed by the flights that sealed them; Fold B gold labels read offline for tuning only, as the brief allows.",
        OFFLINE,
        (
            f"REGISTERED BEFORE RESULT READING (DRAFT, root countersignature pending) {args.registered_at[:10]} at study commit "
            f"{args.study_commit}. Script {OFFLINE_SCRIPT}; output analysis/{OFFLINE_ROW}/read-v1.json and the package copy "
            f"{OFFLINE}. Chosen cap {cap}, depth {depth}; validation {offline['validation']['fold_a_top20_equals_agree_solver_consumption']} "
            f"(Fold A) and {offline['validation']['fold_b_top20_intent_shares_equal_pinned_agreement_table']} (Fold B). Counts only. It authorises nothing. "
            f"RE-REGISTRATION {args.registered_at[:10]} (coordinator ruling of 2026-09-27): the cap this row tuned is NOT flown -- W3 is W3a alone; the row stands as "
            f"the record of why (Fold B N = {cap}: GAIN 0 / HARM 0; Fold A: 0 wrong-intent pluralities removed, 700 right-row "
            "blocks changed) and as the source of the contrast membership set."
        ),
        "",
    ]).strip()

    fresh = {}
    for key in ("arm", "smoke"):
        for kind in ("generation", "fit"):
            run_id = ids[key]["fit"]["run_id"] if kind == "fit" else ids[key]["run_id"]
            fresh[run_id] = row(key, kind)
    fresh[READ_RUN] = read_row
    fresh[BUILD_ROW] = build_row
    fresh[OFFLINE_ROW] = offline_row
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
        raise SystemExit("the ledger carries some but not all W3 rows; refusing to guess")
    if replaced:
        wr(LEDGER, "\n".join(lines))
        return f"replaced-{replaced}"
    header = (
        "\n## Cell W3 (W3a alone since the 2026-09-27 re-registration): intent contrast cards -- the arm, its four-row smoke, the READ row and "
        "the two model-free rows (DRAFT, root countersignature pending)\n\n"
        "Four unconsumed flight rows -- the W3 arm, its four-row form smoke and their two FIT spend identities -- the READ "
        "row registered with the flight, and two model-free rows: the contrast-card build and release, and the offline cap "
        f"tuning and Fold A estimates. Owner decision 164; authority {AUDIT} (K1, K6), {ERRSRC} and {SYNTHESIS}. The arm is "
        f"read at the SHARED wave-1 in-chain A/A {SHARED_AA}, registered by the coordinator, not here. None of these rows is "
        "countersigned and none authorises a contact.\n\n"
        "| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | split role | "
        "split identity hash | consumed | calls | speech audio seconds | gpu hours | inherited exposure | artifacts | notes |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
    )
    suffix = "" if text.endswith("\n") else "\n"
    wr(LEDGER, text + suffix + header + "\n".join(fresh[run_id] for run_id in order) + "\n")
    return "appended"


if __name__ == "__main__":
    raise SystemExit(main())
