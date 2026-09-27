#!/usr/bin/env python3
"""Write the W1 (slot-card selection) registration package from the committed configs.

Knowledge-wave item W1 (owner decision 164; a row-127 no-harm FORM item). Reads the two
derived fragments and the model-free measurement receipt, recomposes each cell's own hashes,
PROVES the composed-config diff against the retained AGREE cells is the ONE key
(``knowledge_stores.slot-contracts.candidate_supply.solver.candidate_legality_source``) plus
per-flight bookkeeping, and writes the package documents, a draft decision receipt for root,
and (with ``--append-ledger``) seven DRAFT exposure rows: the arm, the smoke, their two FIT
identities, the model-free legality build, the model-free measurement and the READ row.
With ``--check-dir`` it folds in the pre-flight prompt budget ``core.flight.cli check``
measured for each cell. Config alone: no contact, no flip, no mint.

    python scripts/flights/write_slurp_w1_registration.py --study-commit <sha> \\
        --registered-at 2026-09-27T16:30:00.000000+00:00 [--check-dir DIR] [--append-ledger]
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

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash  # noqa: E402

PACKAGE = "docs/readiness/2026-09-27-slurp-stage3-w1-card-selection-fold-a-v1"
PREREG = PACKAGE + "-preregistration.md"
MEASUREMENT = PACKAGE + "/card-selection-measurement-v1.json"
LEDGER = "docs/exposure-ledger.md"

CELLS = {"arm": "slurp-native-stage3-w1-cardsel-fold-a-v1", "smoke": "slurp-native-stage3-w1-cardsel-fold-a-smoke-4-v1"}
PARENTS = {"arm": "slurp-native-stage3-agree-w1-fold-a-v1", "smoke": "slurp-native-stage3-agree-w1-fold-a-smoke-4-v1"}
PREFIX = {"arm": "", "smoke": "smoke-"}
FLIGHT_PROSE = {"arm": "Cell W1", "smoke": "Four-row form smoke of cell W1"}
SUPPLY_OUTPUT_SHA = {
    "arm": "eab5c61e92a47c1723c478f2b7914abade6152b195f676d7d32251f3d18884ae",
    "smoke": "308601c52b54ec49013422349e045dd3a4d621c530bf3d2be730fdfe1fdd2fc9",
}
COMPARATOR_RUN = "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1"
COMPARATOR_ATTEMPT = "attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1"
COMPARATOR_OFFICIAL = {"intent_accuracy": 85.8333, "slu_f1": 65.1575, "span_f1": 54.4343, "calls_used": 4385}
SHARED_AA_RUN = "SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1"
SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"
DECISION_ID = "slurp-stage3-w1-cardsel-fold-a-admission-v1"
DECISION_RELPATH = "coordination/slurp-stage3-w1-cardsel-fold-a-v1/root-admission-v1.json"
LEGALITY_ROW = "SAEA-SLURP-INTENT-SLOT-LEGALITY-POOL-V1"
MEASUREMENT_ROW = "SAEA-SLURP-W1-CARD-SELECTION-MEASUREMENT-V1"
READ_ROW = "SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-PAIRED-ANALYSIS-V1"
LEGALITY_RELPATH = "prepared/SAEA-SLURP-INTENT-SLOT-LEGALITY-POOL-V1/legality.json"
LEGALITY_RECEIPT = "prepared/SAEA-SLURP-INTENT-SLOT-LEGALITY-POOL-V1/receipt.json"
THE_ONE_KEY = "knowledge_stores.slot-contracts.candidate_supply.solver.candidate_legality_source"
BOOKKEEPING_PREFIXES = ("native_contact_fit.", "prepared_phase_supply", "what_this_is", "preparation_source_receipts")
H_SLU, H_INTENT = 1.2485, 0.9943
BEFORE_SOLVER = {"rendered_text_tokens": 21278, "required_window_tokens": 21821, "physical_margin_tokens": 2755,
                 "operational_margin_tokens": -317, "decision": "COMPACT_REQUIRED",
                 "source": f"the sealed AGREE arm's own pre-flight receipt ({COMPARATOR_RUN}/{COMPARATOR_ATTEMPT}/flight-receipts.json stages.preflight.prompt_budget)"}

AUDIT = "docs/results/2026-09-27-slurp-knowledge-content-audit.md"
TPUT = "docs/results/2026-09-27-slurp-throughput-baseline-and-levers.md"
INSTRUMENT = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"
OWNER_DECISIONS = "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md"
AGREE_PACKAGE = "docs/readiness/2026-09-26-slurp-stage3-agree-w1-fold-a-v1"
G5_PACKAGE = "docs/readiness/2026-09-27-slurp-stage3-g5-fold-a-v1"
BUILD_SCRIPT = "scripts/build_slurp_intent_slot_legality.py"
MEASURE_SCRIPT = "scripts/analysis/slurp_w1_card_selection_measurement.py"
DERIVE_SCRIPT = "scripts/flights/derive_slurp_w1_cells.py"
CONFIG_TEST = "tests/unit/test_w1_cardsel_config.py"
CODE_TEST = "tests/unit/test_candidate_legality_narrowing.py"
GATE = "scripts/checks/stage3_effect_floor_check.py"
READ_DRIVER_FAMILY = "scripts/analysis/plan_cell_read.py"


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
    one_key = [k for k in changed if k == THE_ONE_KEY or k.startswith(THE_ONE_KEY + ".")]
    bookkeeping = [k for k in changed if k.startswith(BOOKKEEPING_PREFIXES)]
    experiment_block = [k for k in changed if k.split(".", 1)[0] in experiment_keys and k not in one_key and k not in bookkeeping]
    other = [k for k in changed if k not in one_key and k not in bookkeeping and k not in experiment_block]
    return {"the_one_key": one_key, "baseline_bookkeeping_only": bookkeeping,
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
            raise SystemExit(f"{key}: composed config differs from the AGREE parent beyond the one key and bookkeeping: {diff['anything_else']}")
        if not diff["the_one_key"]:
            raise SystemExit(f"{key}: the one key did not move")
        if "prepared_phase_supply" in composed.values:
            raise SystemExit(f"{key}: the derived cell must carry no committed prepared_phase_supply")
        route = composed.values["knowledge_stores"]["slot-contracts"]["candidate_supply"]["solver"]
        source = route["candidate_legality_source"]
        if source["relpath"] != LEGALITY_RELPATH:
            raise SystemExit(f"{key}: the legality source is not {LEGALITY_RELPATH}")
        split = document["population"]["split_identity_hash"]
        out[key] = {
            "experiment": experiment, "cell": cell["cell_id"], "run_id": cell["run_id"], "attempt_id": cell["attempt_id"],
            "baseline_fragment": cell["baseline_fragment"], "parent_experiment": PARENTS[key],
            "dataset_fragment": cell["dataset_fragment"], "model_fragment": cell["model_fragment"],
            "arm": composed.values["arm"], "rows": document["population"]["count"], "split_identity_hash": split,
            "composed_config_hash": composed.config_hash, "parent_composed_config_hash": parent.config_hash,
            "protocol_hash": protocol_hash(composed.config_hash, composed.values["arm"], split),
            "fit": dict(composed.values["native_contact_fit"]), "family_budget": document["family_budget"],
            "execution_profile": document["execution_profile"], "carrier_lock_key": composed.values["carrier_lock_key"],
            "candidate_legality_source": dict(source),
            "card_route_caps": {k: route[k] for k in ("max_candidates", "max_values_per_candidate", "max_total_values")},
            "composed_config_diff_against_the_agree_cell": diff,
            "readiness": cell["readiness"],
        }
    return out


def fold_check(check_dir: str | None) -> dict:
    if not check_dir:
        return {"status": "PENDING_CHECK"}
    out = {"status": "MEASURED_BY_CHECK", "cells": {}}
    for key, cell_id in CELLS.items():
        path = Path(check_dir) / f"check-{cell_id}.json"
        if not path.is_file():
            out["cells"][key] = {"status": "MISSING"}
            continue
        report = json.loads(path.read_text(encoding="utf-8"))
        preflight = report.get("preflight") or {}
        phases = []
        for receipt in preflight.get("prompt_budget") or ():
            breakdown = receipt.get("breakdown") or {}
            phases.append({
                "phase": receipt.get("phase"), "decision": receipt.get("decision"),
                "rendered_text_tokens": breakdown.get("rendered_text_tokens"),
                "required_window_tokens": breakdown.get("required_window_tokens"),
                "physical_margin_tokens": receipt.get("physical_margin_tokens"),
                "operational_margin_tokens": receipt.get("operational_margin_tokens"),
                "payload_sha256_prefix": (receipt.get("payload_sha256") or "")[:16],
            })
        out["cells"][key] = {"scientific_readiness": report.get("scientific_readiness"), "blockers": report.get("blockers"),
                             "config_hash": preflight.get("config_hash"), "protocol_hash": preflight.get("protocol_hash"),
                             "prompt_budget_per_phase": phases}
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--study-commit", required=True)
    parser.add_argument("--registered-at", required=True)
    parser.add_argument("--branch", default="fable/w1")
    parser.add_argument("--worktree", default="/home/chao/saea-worktrees/fable-w1")
    parser.add_argument("--check-dir", default=None)
    parser.add_argument("--append-ledger", action="store_true")
    args = parser.parse_args(argv)
    os.chdir(REPO_ROOT)

    m = json.loads(rd(MEASUREMENT))
    if m["schema"] != "saea-w1-card-selection-measurement-v1":
        raise SystemExit("the measurement receipt is not the expected schema")
    measurement_sha = sha_file(MEASUREMENT)
    ids = identities()
    arm, smoke = ids["arm"], ids["smoke"]
    if arm["candidate_legality_source"]["sha256"] != m["inputs"]["legality"]["sha256"]:
        raise SystemExit("the arm pins a different legality table from the one measured")
    caps, smoke_caps = arm["family_budget"], smoke["family_budget"]
    fit = fold_check(args.check_dir)
    after_solver = None
    if fit["status"] == "MEASURED_BY_CHECK" and "prompt_budget_per_phase" in fit["cells"].get("arm", {}):
        after_solver = next((p for p in fit["cells"]["arm"]["prompt_budget_per_phase"] if p["phase"] == "solver"), None)

    saving, harm, cards, bound = m["saving"], m["harm"], m["cards"], m["static_bound_utf8_bytes"]
    ceiling = {
        "kind": "form: prompt room freed, not a task-quality expectation",
        "tokens_per_solver_contact_mean": saving["tokens_per_solver_contact"]["mean"],
        "tokens_per_solver_contact_median": saving["tokens_per_solver_contact"]["median"],
        "tokens_per_solver_contact_p95": saving["tokens_per_solver_contact"]["p95"],
        "tokens_per_row_mean_over_every_contact_rendering_the_block": saving["tokens_per_row_over_every_contact_rendering_the_block"]["mean"],
        "tokens_per_1080_row_flight": saving["tokens_per_1080_row_flight"],
        "cards_per_row": {"flown": cards["per_row_flown"]["mean"], "w1": cards["per_row_w1"]["mean"]},
        "preflight_solver_card_envelope_utf8_bytes": {"flown": bound["flown_global_longest_28"], "w1": bound["w1_heaviest_28_any_3_intents_can_reach"]},
        "preflight_solver_rendered_tokens": {"before": BEFORE_SOLVER["rendered_text_tokens"], "after": after_solver["rendered_text_tokens"] if after_solver else "PENDING_CHECK"},
        "source": f"{MEASUREMENT} (sha256 {measurement_sha})",
    }
    no_harm_rule = (
        "NO-HARM ADMITTED (owner decision 127): against the SHARED in-chain A/A " + SHARED_AA_RUN + " (the retained AGREE "
        f"arm's own bytes, registered by the coordinator for wave items W1-W4) flown in the same chain, the paired CI95 lower "
        f"bound of the intent-accuracy delta (primary, decision 133) is not below -{H_INTENT} pp AND the paired CI95 lower bound "
        f"of the official pooled SLU-F1 delta (the guard) is not below -{H_SLU} pp -- each at its own Fold A own-null half-width "
        f"(PLAN vs PLANr, {INSTRUMENT} section 2d; the G5 precedent). HARMFUL: a measured loss on either metric (CI95 upper bound "
        "below zero, decision 25). NEUTRAL-BY-WIDTH IS THE ADMISSION (decision 127). Never reported as a gain; two base items are "
        "never assumed to add (decision 138). Every verdict carries the per-scenario table in both weightings, the frontier row "
        "(decision 75), the measured Solver prompt-token delta per contact and per row from the sealed COST records, and the "
        f"registered harm rows ({harm['rows_losing_a_gold_type_card']} rows that lose a gold-type card) read row by row."
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
            "replicate_run_id": SHARED_AA_RUN,
            "rows": 1080,
            "declared_ceiling": ceiling,
            "note": (
                "A row-127 FORM item (knowledge-wave W1, owner decision 164), admitted on NO HARM and never reported as a gain: "
                "expected_effect_pp is 0.0 because the cell registers no effect to look for, claims_benefit is false, and the harm "
                "margin is the measured floor of this design at n = 1,080 (the Fold A own-null half-width of PLAN vs PLANr, SLU 1.2485 "
                "in the gate's field, intent 0.9943 applied by the read), exactly as G5 declared it. The delta is read against the "
                "shared in-chain A/A of the AGREE arm's own bytes flown in the same chain, never against the sealed AGREE arm alone. "
                "The declared ceiling is the prompt room freed (declared_ceiling), measured model-free on the sealed AGREE arm; the "
                f"measured risk is {harm['rows_losing_a_gold_type_card']} rows / {harm['gold_items_of_lost_types']} gold items whose "
                f"slot card W1 drops ({harm['of_which_delivered_exactly_right_by_agree']} delivered exactly right by AGREE)."
            ),
        },
        smoke["run_id"]: {
            "claims_benefit": False,
            "expected_effect_pp": 0.0,
            "measurement_design": "form-proof",
            "primary_metric": "none (structural form only)",
            "rows": 4,
            "note": (
                "Four rows prove FORM and nothing else: that the legality table loads and verifies, that the card route narrows "
                "without error, that every request fits and that the episode completes. Scored by no one, read by no one."
            ),
        },
    }

    facts = {
        "schema": "saea-registered-facts-v1",
        "_note": f"Every model-free fact this registration rests on, and the CANONICAL stage3_measurement block {GATE} resolves (keyed by run id). The preregistration's fence repeats it; this copy has precedence.",
        "registered_at_utc": args.registered_at,
        "study_commit_at_registration": args.study_commit,
        "owner_decisions": {
            "127": "the ENGINEERING-BASE admission: sound logic, a stated ceiling, a no-harm reading at a margin equal to the design's measured floor; never reported as a gain",
            "161": "AGREE retained; later items derive from the retained AGREE arm",
            "164": "knowledge wave: W1 slot-card selection approved, analysis and preparation now, flight as soon as possible after 09:00 (owner's time, about 01:00Z 2026-09-28)",
        },
        "rows": 1080,
        "stage3_measurement": measurement,
        "the_item": {
            "finding": (
                f"{AUDIT} deficit K8: 12.9 slot-contract cards reach the Solver per row and 91.1 % of their text serves neither the "
                "delivered nor the gold slot types, while the Solver's pre-flight envelope has 226 tokens of headroom (21,278 of "
                f"21,504 usable); {TPUT} lever 2 prices dropping cards no candidate intent can carry at +7.0 % throughput."
            ),
            "measured_here": (
                "The flown card route already selects through the authored intent_bindings, and those 402 bindings are EXACTLY the "
                "(intent, slot type) pairs the released 9,354-utterance exemplar store carries at least once -- so 'legal under a "
                "candidate intent' by mere presence is what flies today. What the audit calls unused is carried by ANECDOTAL "
                "bindings: 116 of the 402 pairs are witnessed by a single pool utterance."
            ),
            "change": "narrow the card route's index to the 286 pairs the store carries in at least two distinct utterances",
            "legality_table": {
                "relpath": LEGALITY_RELPATH, "sha256": arm["candidate_legality_source"]["sha256"],
                "receipt": LEGALITY_RECEIPT, "builder": BUILD_SCRIPT, "rule": "pool-utterance-support-at-least-2-v1",
                "source": "the released TRAIN exemplar store size-pool-annotated-exemplars (content hash 4c498dc0...), 9,354 utterances, Fold A-free (checked); type names only",
                "why_not_the_8554_sibling": "the R01-excluded 8,554-utterance sibling lacks cooking_query entirely and 42 of the authored pairs; the brief's '9,354' is the flown store, which is the one the Solver already reads and whose pairs equal the authored bindings",
                "pairs": {"authored": 402, "kept": 286, "removed": 116},
            },
            "how_the_rule_was_chosen": (
                "min_support 2 is the smallest non-trivial support threshold (a binding seen once is not a convention of the intent). "
                "The sensitivity grid in the measurement receipt was computed on the same sealed Fold A arm before the rule was fixed "
                "and is disclosed in full; 2 is the grid's most conservative non-identity point (3: 10 harmed rows, 5: 22)."
            ),
        },
        "measurement": {
            "receipt": {"relpath": MEASUREMENT, "sha256": measurement_sha, "script": {"relpath": MEASURE_SCRIPT, "sha256": sha_file(MEASURE_SCRIPT)}},
            "validation": m["validation"],
            "cards": {k: v for k, v in cards.items() if k != "zero_card_rows_w1"},
            "zero_card_rows_w1": cards.get("zero_card_rows_w1"),
            "saving": saving,
            "harm": harm,
            "static_bound_utf8_bytes": bound,
            "sensitivity_grid": m["sensitivity_grid"],
        },
        "fit": {
            "rule": "the pre-flight prompt budget binds to the LIVE slot (24,576 tokens, np4) with a reserve of one eighth (3,072); the Solver phase of the AGREE arm reads COMPACT_REQUIRED with a positive physical margin and proceeds under context_fit_policy compact-or-abstain",
            "before_solver": BEFORE_SOLVER,
            "measured": fit,
            "why_the_bound_moves": "core.flight.runtime._legality_narrowed_candidate_blocks bounds a narrowed card route by the heaviest 28 cards ANY 3 indexed intents can reach (7,816 fewer UTF-8 bytes than the store's globally longest 28); candidate blocks are unioned into every native role's bound, so every phase's envelope moves by the same amount",
        },
        "identity": {key: {k: v for k, v in ids[key].items() if k not in ("composed_config_diff_against_the_agree_cell", "readiness")} for key in CELLS},
        "composed_config_diff_against_the_agree_cell": {key: {**ids[key]["composed_config_diff_against_the_agree_cell"], "parent_experiment": PARENTS[key]} for key in CELLS}
        | {"note": f"flattened composed configs (core.config.compose): the one key, the baseline's bookkeeping (FIT ids, the dropped prepared_phase_supply, the legality receipt in preparation_source_receipts, what_this_is) and the experiment fragment's own block. {CONFIG_TEST} re-proves it."},
        "comparator": {
            "run_id": COMPARATOR_RUN, "attempt_id": COMPARATOR_ATTEMPT, "official": COMPARATOR_OFFICIAL, "never_reflown": True,
            "in_chain_replicate": {"run_id": SHARED_AA_RUN, "registered_by": "the coordinator, separately, as the shared A/A of wave items W1-W4 (the AGREE arm's own bytes)"},
            "margins": {"h_slu": H_SLU, "h_intent": H_INTENT, "source": f"PLAN vs PLANr Fold A own null ({INSTRUMENT} section 2d), as {G5_PACKAGE} declared"},
        },
        "no_harm_rule": no_harm_rule,
        "byte_identity_expectation": {
            "arm_supply_output_sha256": SUPPLY_OUTPUT_SHA["arm"], "smoke_supply_output_sha256": SUPPLY_OUTPUT_SHA["smoke"],
            "claim": "the card route is not an input to the first-phase (Perception) supply, so the supply the flip mints for each cell must carry the AGREE preparation's output digest; a different digest means the Perception channel moved -- stop and report",
        },
        "budget_arithmetic": {
            "arm_family_budget": caps, "smoke_family_budget": smoke_caps,
            "derivation": [
                "generation_calls_cap = 1,080 x 11 (perception 1, solver 1, reviewer 3, planner 1, max_revisions 1 -> 1 + 2 x (3 + 1 + 1)) = 11,880; the smoke 4 x 11 = 44",
                "fit_endpoint_calls_cap = 4 x generation = 47,520 (smoke 176); native_task_contract_calls_cap 6,480 (smoke 24); repeated_speech_audio_seconds_cap 33,930 (smoke 117); gpu_hours_fit_inclusive 12.0 (smoke 1.0): the AGREE family's own ceilings",
                "expected spend at the sealed AGREE arm's own rate: about 4,385 contacts; W1 removes prompt tokens and adds none, and no cap is denominated in tokens",
                "official_complete_scoring_jobs = 1 per 1,080-row cell through core.scoring_batch, never sharded; the smoke is never scored",
            ],
            "run_cumulative": "every cap binds across ALL attempts of a run id",
        },
        "prohibitions": [
            "Never reported as a gain (decision 127).",
            "No test-split, Fold B or DEV contact or read.",
            "No re-flying of the sealed AGREE comparator.",
            "No second factor: no other store, snapshot, cap, template, roster, geometry or session change.",
            "No paper-scale profile.",
            "No flight before root mints the decision receipt and the cells are flipped; the shared A/A is the coordinator's registration, not this package's.",
        ],
        "authority_relpaths": [AUDIT, TPUT, INSTRUMENT, OWNER_DECISIONS, AGREE_PACKAGE + "/README.md", G5_PACKAGE + "/README.md", GATE],
    }
    facts_sha = wjson(PACKAGE + "/registered-facts-v1.json", facts)

    one_factor = (
        f"Composed key {THE_ONE_KEY}: absent -> the pinned legality table {LEGALITY_RELPATH} (sha256 "
        f"{arm['candidate_legality_source']['sha256']}); the card route's authored index (402 pairs) narrowed to the 286 pairs "
        "the released exemplar store carries in at least two distinct utterances; nothing added."
    )
    protocol = {
        "schema": "saea-registered-protocol-v1",
        "protocol_id": "slurp-stage3-w1-cardsel-fold-a-protocol-v1",
        "registered_at_utc": args.registered_at,
        "study_commit_at_registration": args.study_commit,
        "source_tree": f"studies/speech-aware-evidence-acquisition, worktree {args.worktree}, branch {args.branch}",
        "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP",
        "the_question": (
            "With the Solver's slot-contract cards narrowed to the slot types legal under the row's shortlisted intents, do the "
            "official intent accuracy and pooled SLU-F1 on TRAIN Fold A 1,080 stay within the plan's own null, read against the "
            "shared in-chain A/A? (A no-harm question; the item's value is the prompt room it frees, stated as a ceiling.)"
        ),
        "one_factor": one_factor,
        "unchanged": (
            f"everything but that key and per-flight bookkeeping: the roster (TRAIN Fold A 1,080, split identity {arm['split_identity_hash']}), "
            f"the model fragment and serving geometry (np4 x 24,576), the session {SESSION}, the program and its 11-contact ceiling, all "
            "three stores and their pins, the agreement term, the exemplar k of 20, the card route's caps (3 / 16 / 28), the role graph, "
            "every template, the deliver normaliser, the scorers and every budget"
        ),
        "cells": {key: {k: ids[key][k] for k in ("cell", "experiment", "run_id", "attempt_id", "rows", "composed_config_hash", "protocol_hash", "split_identity_hash")}
                  | {"fit_run_id": ids[key]["fit"]["run_id"], "fit_attempt_id": ids[key]["fit"]["attempt_id"]} for key in CELLS},
        "comparator": facts["comparator"],
        "decision_rule_fixed_here": no_harm_rule,
        "declared_ceiling": ceiling,
        "registered_risk": {k: harm[k] for k in ("rows_losing_a_gold_type_card", "gold_items_of_lost_types", "of_which_delivered_exactly_right_by_agree", "rows_whose_delivered_answer_used_a_dropped_type")},
        "what_a_harmful_read_would_mean": "that the dropped anecdotal cards carried guidance the Solver used beyond their type -- read first on the registered harm rows and on the rows whose delivered answer used a dropped type -- and W1 is withdrawn from the composed round pending a root cause; a NEUTRAL read is the admission and is never written as 'no gain'",
        "development_numbers_only": "TRAIN Fold A construction-fold development numbers (owner decisions 28 and 86); never a test claim.",
        "failure_policy": "Stop and preserve on the first failure. AT MOST ONE root-diagnosed recovery re-registration; a second failure closes the cell and the fix is proven on a four-row dry run. The budget is run-cumulative across attempts.",
        "prohibitions": facts["prohibitions"],
    }
    protocol_sha = wjson(PACKAGE + "/protocol-registered-v1.json", protocol)

    plan_shas: dict[str, str] = {}
    for key in CELLS:
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
                    "Shared core.flight.cli campaign: configs/campaign/slurp-native-stage3-w1-cardsel-fold-a-v1.json carries the W1 arm alone; the coordinator's chain flies it beside the shared in-chain A/A " + SHARED_AA_RUN + " in ONE chain; one official score per generation cell at finalize."
                    if key == "arm" else
                    "Shared core.flight.cli worker on this cell alone; the smoke is outside the campaign plan and is never scored."
                ),
                "prepared_phase_supply": {
                    "relpath": f"prepared/{identity['run_id']}/phase-supply-v1.json",
                    "sha256": "MINTED_AT_THE_FLIP",
                    "expected_output_sha256": SUPPLY_OUTPUT_SHA[key],
                    "note": facts["byte_identity_expectation"]["claim"],
                },
                "protocol_document": {"relpath": PACKAGE + "/protocol-registered-v1.json", "sha256": protocol_sha},
                "one_factor": one_factor,
                "purpose": f"{run_id}: {FLIGHT_PROSE[key]}. " + (
                    "It measures request envelopes only and reads nothing." if is_fit
                    else no_harm_rule if key == "arm" else "Structural form proof only: no score and no read."
                ),
                "quality_read_gate": "No task-quality read before the complete sealed manifest, the exact ordered outputs, the native phase summary and the single successful complete official TRAIN score all exist for BOTH the W1 arm and the shared in-chain A/A. A verdict computed against the sealed AGREE arm alone is refused.",
            }
            plan_shas[run_id] = wjson(f"{PACKAGE}/{PREFIX[key]}{kind}-plan-registered-v1.json", plan_doc)

    recipe = {
        "schema": "saea-slurp-paired-analysis-recipe-v1",
        "recipe_id": "slurp-stage3-w1-cardsel-fold-a-paired-analysis-v1",
        "title": "Cell W1 -- the standard paired roster read on intent + SLU at the shared in-chain A/A, under the no-harm rule",
        "registered_at_utc": args.registered_at,
        "read_run_id": READ_ROW,
        "run_ids": {"read": READ_ROW, "arm": arm["run_id"], "in_chain_replicate": SHARED_AA_RUN, "comparator": COMPARATOR_RUN},
        "arms": {
            "arm": {"run_id": arm["run_id"], "attempt_id": arm["attempt_id"], "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL", "outputs_sha256": "PENDING_SEAL"},
            "in_chain_replicate": {"run_id": SHARED_AA_RUN, "role": "the within-chain null the delta is read at (the AGREE arm's own bytes; registered by the coordinator)"},
            "comparator": {"run_id": COMPARATOR_RUN, "attempt_id": COMPARATOR_ATTEMPT, "role": "context, sealed, never re-flown"},
        },
        "resampling": {"bootstrap_draws": 10000, "metrics": ["scenario_action_exact", "slu_f1_f1"], "seed": 20260927, "unit": "row (paired)"},
        "decision_rule": no_harm_rule,
        "margins": {"h_intent": H_INTENT, "h_slu": H_SLU},
        "steps": [
            "1. Refuse unless BOTH the W1 arm and the shared in-chain A/A carry a COMPLETE sealed manifest at 1,080 rows with the committed roster's ids, each with one successful complete official TRAIN score.",
            "2. Structural stage: on the arm, every Solver card selection is a subset of the one the A/A made on the same Perception shortlist; the per-row card count and the Solver prompt tokens per contact from the sealed COST records against the A/A (expected about -1,186 per Solver contact where the shortlist agrees).",
            "3. Score once per arm over the complete manifest with slurp-slu-official-train through core.scoring_batch, never sharded.",
            "4. Paired row bootstrap (10,000 draws, seed 20260927) of the arm minus A/A delta on intent accuracy and official pooled SLU-F1, point and CI95; the delta against the sealed AGREE arm reported BESIDE it, never instead of it.",
            f"5. ADMITTED iff intent lower bound >= -{H_INTENT} and SLU lower bound >= -{H_SLU}; HARMFUL iff either upper bound < 0; otherwise NOT ADMITTED (width). Never write 'gain' or 'no gain'.",
            "6. Report: per-scenario tables in both weightings; the frontier row (decision 75); the registered harm rows of card-selection-measurement-v1.json read row by row (ids and type names only); the rows whose delivered answer used a dropped type.",
        ],
        "read_driver_family": READ_DRIVER_FAMILY,
        "output": {"analysis_root": f"analysis/{READ_ROW}"},
        "boundary": "A development read on a TRAIN construction fold (owner decisions 28 and 86); never a test claim. No utterance text, transcript, gold filler or model output is printed or persisted.",
    }
    recipe_sha = wjson(PACKAGE + "/analysis-recipe-v1.json", recipe)

    eligible = [arm["run_id"], arm["fit"]["run_id"], smoke["run_id"], smoke["fit"]["run_id"]]
    draft = {
        "_draft_note": "A DRAFT for root to mint on the data root with scripts/flights/w1/w1_mint_receipt.py (status decided, recorded_at_utc stamped, antecedents re-hashed, never overwrites). It authorises nothing while its status is not 'decided'.",
        "schema": "saea-campaign-decision-v1",
        "decision_id": DECISION_ID,
        "status": "DRAFT-NOT-MINTED",
        "recorded_at_utc": None,
        "owner": "root",
        "coordinator": "Fable5.1",
        "eligible_run_ids": eligible,
        "cell_kind": "Stage-3 engineering-base no-harm FORM item (label none). One arm on TRAIN Fold A 1,080 read at the shared in-chain A/A " + SHARED_AA_RUN + " (registered and made eligible by the coordinator's own receipt), and a four-row form smoke outside the chain.",
        "decision": (
            "Fly W1: the retained AGREE arm with its slot-contract card route narrowed by the pinned legality table (286 of the "
            "402 authored bindings, those the released exemplar store carries in at least two utterances), read on NO HARM at "
            f"the shared in-chain A/A at the plan's own Fold A half-widths (intent {H_INTENT}, SLU {H_SLU}); never reported as a gain."
        ),
        "authorization_basis": f"Owner decision 164 (knowledge wave W1), 127 (engineering-base admission), 161 (AGREE retained), 138 (cumulative check in the composed round); the audit {AUDIT} K8; standing: 25, 28, 86, 101, 133, 77, and {INSTRUMENT}.",
        "antecedents": {
            "owner_decisions": {"path": OWNER_DECISIONS, "sha256": sha_file(OWNER_DECISIONS)},
            "instrument_note": {"path": INSTRUMENT, "sha256": sha_file(INSTRUMENT)},
            "preregistration": {"path": PREREG, "sha256": None},
            "readiness_readme": {"path": PACKAGE + "/README.md", "sha256": None},
            "protocol": {"path": PACKAGE + "/protocol-registered-v1.json", "sha256": protocol_sha},
            "registered_facts": {"path": PACKAGE + "/registered-facts-v1.json", "sha256": facts_sha},
            "analysis_recipe": {"path": PACKAGE + "/analysis-recipe-v1.json", "sha256": recipe_sha},
            "measurement": {"path": MEASUREMENT, "sha256": measurement_sha},
            "config_proof": {"path": CONFIG_TEST, "sha256": sha_file(CONFIG_TEST) if Path(CONFIG_TEST).is_file() else None},
            "code_proof": {"path": CODE_TEST, "sha256": sha_file(CODE_TEST)},
            "base_cell": f"the retained AGREE arm ({COMPARATOR_RUN}, decision 161): W1 is that fragment with one key added",
            "registration_base_commit": args.study_commit,
        },
        "budget": {**{k: caps[k] for k in sorted(caps)}, "smoke": smoke_caps, "paid_api_calls": 0,
                   "expected_contacts_per_1080_row_cell": COMPARATOR_OFFICIAL["calls_used"], "plan_budget_is_run_cumulative": True},
        "claim_boundary": "No superiority, generalisation, component-causal, held-out, confirmatory or paper-scale claim; a no-harm admission of one engineering-base FORM item, never reported as a gain.",
        "failure_policy": protocol["failure_policy"],
        "not_authorized": [
            "any flight before the cells are flipped and the receipt is minted",
            "flying the arm without the shared in-chain A/A in the same chain",
            "touching the resident np4 session by anyone but the coordinator",
            "any ASR, transcript, encoder or paid-API contact",
            "re-flying or re-scoring any sealed cell",
            "--allow-output-change on the re-pin tool",
            "any change beyond the one registered key",
            "reporting the item as a gain",
        ],
        "population": {"count": 1080, "split_identity_hash": arm["split_identity_hash"], "split_role": "discovery", "partition": "TRAIN Fold A 1,080", "fold_b_contact_authorized": False, "test_contact_authorized": False},
        "prepared_phase_supply": {"note": f"minted by scripts/flights/repin_cell.py at the flip (each cell's own, item E16); expected output digests arm {SUPPLY_OUTPUT_SHA['arm']}, smoke {SUPPLY_OUTPUT_SHA['smoke']}"},
        "registered_hashes": {key: {"composed_config": ids[key]["composed_config_hash"], "protocol": ids[key]["protocol_hash"]} for key in CELLS},
        "service": {"expected_session_id": SESSION, "model_fragment": arm["model_fragment"], "slots": 4, "slot_tokens": 24576, "note": "the resident SLURP np4 session; the flight attaches only"},
    }
    draft_sha = wjson(PACKAGE + "/root-admission-draft-v1.json", draft)

    fit_line = "PENDING (run core.flight.cli check after the exposure rows exist, then re-run this writer with --check-dir)"
    if after_solver:
        fit_line = (
            f"Solver rendered {BEFORE_SOLVER['rendered_text_tokens']:,} -> {after_solver['rendered_text_tokens']:,} tokens, required window "
            f"{BEFORE_SOLVER['required_window_tokens']:,} -> {after_solver['required_window_tokens']:,}, physical margin "
            f"{BEFORE_SOLVER['physical_margin_tokens']:,} -> {after_solver['physical_margin_tokens']:,}, operational margin "
            f"{BEFORE_SOLVER['operational_margin_tokens']:,} -> {after_solver['operational_margin_tokens']:,}, decision "
            f"{BEFORE_SOLVER['decision']} -> {after_solver['decision']}"
        )
    fence = json.dumps({"stage3_measurement": measurement}, indent=2, ensure_ascii=False, sort_keys=True)
    harm_table = "\n".join(
        f"| `{h['sample_id']}` | {', '.join(h['lost_gold_slot_types'])} | {h['gold_intent_position_in_shortlist'] or 'not shortlisted'} "
        f"| {', '.join(f'{t}: {n}' for t, n in h['lost_type_support_under_gold_intent'].items())} "
        f"| {sum(1 for i in h['gold_items_of_lost_types'] if i['delivered_exactly_right_by_agree'])} of {len(h['gold_items_of_lost_types'])} "
        f"| {', '.join(e['kind'] for e in h['error_source_items_of_lost_types']) or '--'} |"
        for h in harm["rows"]
    )
    readme = f"""# Cell W1: slot-card selection (knowledge wave item W1)

Registered before contact {args.registered_at[:10]} at study commit `{args.study_commit}` (owner decision 164, a row-127
no-harm FORM item derived from the retained AGREE arm, decision 161); both cells **held**. Nothing here authorises a
flight, a flip or an admission entry.

**The deficit.** [`{AUDIT}`](../../results/{Path(AUDIT).name}) K8: 12.9 slot-contract cards reach the Solver per row and
91.1 % of their text serves neither the delivered nor the gold slot types, under a Solver envelope with 226 tokens of
headroom (21,278 of 21,504 usable).

**What was measured first** (`{BUILD_SCRIPT}`, model-free). The flown card route already selects through the authored
`intent_bindings`, and those 402 bindings are EXACTLY the (intent, slot type) pairs the released 9,354-utterance
exemplar store carries at least once. So "legal under a candidate intent" by mere presence is what flies today; the
unused text comes from ANECDOTAL bindings -- 116 of the 402 pairs are witnessed by one pool utterance.

**The one change.** `{THE_ONE_KEY}` = the pinned table `{LEGALITY_RELPATH}` (sha256
`{arm['candidate_legality_source']['sha256']}`, receipt beside it): the route keeps the 286 pairs the store carries in
at least two distinct utterances (rule `pool-utterance-support-at-least-2-v1`). A table can only remove an authored
binding (the loader refuses one that adds). Caps (3 / 16 / 28), stores, roster, geometry, templates: the AGREE arm's.

**What it saves** (`{MEASURE_SCRIPT}` -> [`card-selection-measurement-v1.json`](card-selection-measurement-v1.json); the
flown selection replayed identically on 1,080 / 1,080 rows first; exact tokens by the local vocab-only tokenizer,
{m['inputs']['tokenizer']['invocations']} invocations): cards per row {cards['per_row_flown']['mean']} -> {cards['per_row_w1']['mean']}; Solver prompt tokens per contact
**-{saving['tokens_per_solver_contact']['mean']}** on average (median {saving['tokens_per_solver_contact']['median']}, p95 {saving['tokens_per_solver_contact']['p95']}, max {saving['tokens_per_solver_contact']['max']});
**-{saving['tokens_per_row_over_every_contact_rendering_the_block']['mean']}** per row over the Solver, Reviewer and Planner contacts that render the block;
{saving['tokens_per_1080_row_flight']:,} per 1,080-row flight. Pre-flight card envelope {bound['flown_global_longest_28']:,} -> {bound['w1_heaviest_28_any_3_intents_can_reach']:,} UTF-8 bytes.

**What it risks** (gold read offline, ids and type names only): **{harm['rows_losing_a_gold_type_card']} rows** lose a card for a gold slot type
({harm['gold_items_of_lost_types']} gold items; **{harm['of_which_delivered_exactly_right_by_agree']}** of them the AGREE arm delivered exactly right); rows with every gold type carded
{harm['rows_all_gold_types_carded_flown']} -> {harm['rows_all_gold_types_carded_w1']} of {harm['rows_with_gold_entities']}; {harm['rows_whose_delivered_answer_used_a_dropped_type']} rows' delivered answer used a type whose card W1 drops;
{cards['rows_with_zero_cards_w1']} row receives no card at all (disposition `no-mapping`; its exemplars still arrive).

| row | lost gold type | gold intent's shortlist position | pool support under the gold intent | AGREE right | error-source item |
| --- | --- | --- | --- | --- | --- |
{harm_table}

Sensitivity (computed on the same arm before the rule was fixed, disclosed): min support 3 -> 10 harmed rows, 5 -> 22.

**Fit.** Before (the sealed AGREE preflight): Solver rendered {BEFORE_SOLVER['rendered_text_tokens']:,}, `{BEFORE_SOLVER['decision']}`, physical margin
{BEFORE_SOLVER['physical_margin_tokens']:,}. After: {fit_line}.

**`stage3_measurement`.** `admission` `no-harm`, `harm_margin_pp` {H_SLU} (by metric intent {H_INTENT} / SLU {H_SLU}, the G5
precedent), `claims_benefit` false, `expected_effect_pp` 0.0, `cross-flight-with-in-chain-replicate`, `replicate_run_id`
`{SHARED_AA_RUN}` (the coordinator's shared A/A of the AGREE arm's own bytes), `declared_ceiling` the measured saving.

| file | what it holds |
| --- | --- |
| `../{Path(PREREG).name}` | the preregistration, including the `stage3_measurement` fence |
| `card-selection-measurement-v1.json` | the replay, the saving, the harm rows, the static bound, the sensitivity grid |
| `registered-facts-v1.json` | every model-free fact, the one-key diff, the CANONICAL `stage3_measurement` |
| `protocol-registered-v1.json` | identities, hashes, the no-harm rule, the registered risk |
| `generation-plan-registered-v1.json` / `fit-plan-registered-v1.json` | the arm's plans |
| `smoke-generation-plan-registered-v1.json` / `smoke-fit-plan-registered-v1.json` | the smoke's plans |
| `analysis-recipe-v1.json` | the paired read, READ run id `{READ_ROW}` |
| `root-admission-draft-v1.json` | the receipt root mints with `scripts/flights/w1/w1_mint_receipt.py` |

**Mint, flip, queue.** Root countersigns the seven DRAFT rows ({arm['run_id']}, {arm['fit']['run_id']}, {smoke['run_id']},
{smoke['fit']['run_id']}, `{LEGALITY_ROW}`, `{MEASUREMENT_ROW}`, and the READ row `{READ_ROW}`, which may stay DRAFT until the
seal), mints `{DECISION_RELPATH}` (id `{DECISION_ID}`, four eligible run ids) with `scripts/flights/w1/w1_mint_receipt.py`,
flips with `scripts/flights/w1/w1_flip.sh` (the generic re-pin loop over `w1_repin_smoke.sh` and `w1_repin_arm.sh`,
converged at one HEAD), and queues the arm in ONE chain with `{SHARED_AA_RUN}`. The minted supplies must carry the AGREE
output digests (arm `{SUPPLY_OUTPUT_SHA['arm'][:8]}...`, smoke `{SUPPLY_OUTPUT_SHA['smoke'][:8]}...`).
"""
    readme_sha = wr(PACKAGE + "/README.md", readme)

    prereg = f"""# Cell W1 (slot-card selection): preregistration

Registered {args.registered_at[:10]} at study commit `{args.study_commit}`, before any contact, from the retained AGREE
fragments by script (`{DERIVE_SCRIPT}`, decision 58) with one key added, under owner decisions 127, 161 and 164.
Development numbers only (owner decisions 28 and 86); never a test claim.

| item | value |
| --- | --- |
| base | the retained AGREE arm `{COMPARATOR_RUN}` (intent {COMPARATOR_OFFICIAL['intent_accuracy']} / SLU {COMPARATOR_OFFICIAL['slu_f1']}), sealed, never re-flown |
| factor | {one_factor} |
| in-chain replicate | `{SHARED_AA_RUN}`, the AGREE arm's own bytes, registered by the coordinator, flown in the SAME chain |
| admission | NO HARM: intent CI95 lower bound against the A/A not below -{H_INTENT}, SLU not below -{H_SLU}; never reported as a gain |
| declared ceiling | -{saving['tokens_per_solver_contact']['mean']} tokens per Solver contact (mean), -{saving['tokens_per_row_over_every_contact_rendering_the_block']['mean']} per row; pre-flight card envelope {bound['flown_global_longest_28']:,} -> {bound['w1_heaviest_28_any_3_intents_can_reach']:,} bytes |
| registered risk | {harm['rows_losing_a_gold_type_card']} rows / {harm['gold_items_of_lost_types']} gold items lose their type's card ({harm['of_which_delivered_exactly_right_by_agree']} delivered right by AGREE) |
| runs | `{arm['run_id']}` / `{arm['fit']['run_id']}`; `{smoke['run_id']}` / `{smoke['fit']['run_id']}`; READ `{READ_ROW}` |
| composed config hashes | arm `{arm['composed_config_hash']}`; smoke `{smoke['composed_config_hash']}` |
| protocol hashes | arm `{arm['protocol_hash']}`; smoke `{smoke['protocol_hash']}` |
| split identity | arm `{arm['split_identity_hash']}`; smoke `{smoke['split_identity_hash']}` |

## Decision rule (fixed here)

{no_harm_rule}

## The measurement declaration

```json
{fence}
```

## Budgets and failure rule

Arm {caps['generation_calls_cap']:,} generation contacts (run-cumulative), {caps['fit_endpoint_calls_cap']:,} FIT endpoints, {caps['repeated_speech_audio_seconds_cap']:,}
repeated speech seconds, {caps['gpu_hours_fit_inclusive']} GPU hours, one official complete score; smoke {smoke_caps['generation_calls_cap']} / {smoke_caps['fit_endpoint_calls_cap']} /
{smoke_caps['repeated_speech_audio_seconds_cap']} / {smoke_caps['gpu_hours_fit_inclusive']}, never scored. Expected about 4,385 contacts at the AGREE arm's rate. Stop and preserve on
the first failure; AT MOST ONE root-diagnosed recovery re-registration.

## Prohibitions

Never reported as a gain. No paper-scale profile, no test-split, Fold B or DEV contact, no comparator re-flight, no
second factor, no flight before root mints the receipt and the cells are flipped, and `--allow-output-change` is never
passed.
"""
    prereg_sha = wr(PREREG, prereg)

    ledger_state = append_ledger(args, ids=ids, plan_shas=plan_shas, m=m, measurement_sha=measurement_sha) if args.append_ledger else "not-requested"
    print(json.dumps({
        "package": PACKAGE, "exposure_ledger": ledger_state, "fit": fit["status"],
        "written": {"README.md": readme_sha, "registered-facts-v1.json": facts_sha, "protocol-registered-v1.json": protocol_sha,
                    "analysis-recipe-v1.json": recipe_sha, "root-admission-draft-v1.json": draft_sha, Path(PREREG).name: prereg_sha,
                    **{f"plan[{run}]": sha for run, sha in plan_shas.items()}},
        "identity": {key: {"run_id": ids[key]["run_id"], "composed_config_hash": ids[key]["composed_config_hash"], "protocol_hash": ids[key]["protocol_hash"],
                           "diff": ids[key]["composed_config_diff_against_the_agree_cell"]} for key in CELLS},
    }, indent=2, sort_keys=True))
    return 0


MODEL_TOOL = (
    "Frozen Q4_K_M decoder-only c98304 np4 max512; promoted EVO-FOLDS-V2 speech packets; NO native tool authority on any "
    "role; prompt bytes the retained AGREE arm's except the Solver-phase slot-contract cards, narrowed by the pinned legality table"
)
INHERITED = (
    "TRAIN Fold A discovery rows already exposed by the sealed anchor, cells B0 through PLANr, ROLL-2, CONV, the AGREE family, "
    "KPROBE, COMP-1 and G5 (flown or in flight at registration); this cell adds no new row to the fold and opens no split. "
    "Prior exposure is inherited in full."
)


def append_ledger(args, *, ids, plan_shas, m, measurement_sha) -> str:
    """Seven DRAFT rows. Idempotent: replace-or-append by run id. No cell may contain a literal '|'."""

    text = rd(LEDGER)
    eligible = [ids["arm"]["run_id"], ids["arm"]["fit"]["run_id"], ids["smoke"]["run_id"], ids["smoke"]["fit"]["run_id"]]
    saving, harm = m["saving"], m["harm"]

    def flight_row(key: str, kind: str) -> str:
        identity = ids[key]
        is_fit = kind == "fit"
        budget = identity["family_budget"]
        run_id = identity["fit"]["run_id"] if is_fit else identity["run_id"]
        attempt = identity["fit"]["attempt_id"] if is_fit else identity["attempt_id"]
        declaration = (
            f"admission no-harm, harm_margin_pp {H_SLU} (by metric: intent {H_INTENT}, SLU {H_SLU}), claims_benefit false, expected_effect_pp 0.0, "
            f"measurement_design cross-flight-with-in-chain-replicate, replicate_run_id {SHARED_AA_RUN}, rows 1080, declared ceiling "
            f"-{saving['tokens_per_solver_contact']['mean']} tokens per Solver contact"
            if key == "arm" else "measurement_design form-proof, claims_benefit false, expected_effect_pp 0.0, rows 4"
        )
        notes = (
            f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) {args.registered_at[:10]} at study commit {args.study_commit} "
            f"by the W1 registration agent (worktree {args.worktree}, branch {args.branch}). This registration performs no contact and "
            f"authorises none. Plan SHA256 {plan_shas[run_id]}; attempt {attempt}. Protocol hash {identity['protocol_hash']}; composed "
            f"config {identity['composed_config_hash']}; expected session {SESSION} (attach only). READINESS HELD: root mints "
            f"{DECISION_RELPATH} (decision id {DECISION_ID}) from the package's root-admission-draft-v1.json with the four eligible run ids "
            f"{', '.join(eligible)}, then re-pins with scripts/flights/repin_cell.py --set-ready, which mints each cell's OWN first-phase "
            f"supply (item E16; expected output digest {SUPPLY_OUTPUT_SHA[key]}); --allow-output-change must never be passed. Every hash in "
            f"this row moves at the flip and the re-pin tool rewrites it. ONE KEY (owner decision 164): {THE_ONE_KEY} = {LEGALITY_RELPATH} "
            f"(sha256 {identity['candidate_legality_source']['sha256']}), the card route narrowed from the 402 authored bindings to the 286 "
            f"the released exemplar store carries in at least two utterances; measured on the sealed AGREE arm: -{saving['tokens_per_solver_contact']['mean']} "
            f"tokens per Solver contact, {harm['rows_losing_a_gold_type_card']} rows / {harm['gold_items_of_lost_types']} gold items lose their type's card. "
            f"Measurement declaration ({GATE}): {declaration} -- canonical in {PACKAGE}/registered-facts-v1.json. THE RULE (decision 127): "
            f"admitted on NO HARM against the shared in-chain A/A {SHARED_AA_RUN} flown in the same chain, HARMFUL on a measured loss, NEVER "
            f"reported as a gain. Caps are the AGREE arithmetic. Stop and preserve on the first failure; AT MOST ONE root-diagnosed recovery "
            f"re-registration. No paper-scale profile, no test-split contact, no comparator re-flight and no admission entry from this row."
        )
        scope = FLIGHT_PROSE[key] + (" -- FIT spend identity, request envelopes only, no generation" if is_fit else "") + ": " + (
            "the retained AGREE arm with the slot-contract card route narrowed to slot types legal under the shortlisted intents (knowledge wave W1), read on no harm against the shared in-chain A/A"
            if key == "arm" else "the narrowed card route on the first four rows of the unchanged roster; structural form only, never scored"
        )
        cells = ["", args.registered_at, run_id, "bounded-discovery-probe", scope, MODEL_TOOL,
                 f"slurp TRAIN Fold A {identity['rows']}", "discovery", identity["split_identity_hash"], "no",
                 str(budget["fit_endpoint_calls_cap"] if is_fit else budget["generation_calls_cap"]),
                 str(budget["repeated_speech_audio_seconds_cap"]), str(budget["gpu_hours_fit_inclusive"]), INHERITED,
                 f"{PACKAGE}/{PREFIX[key]}{kind}-plan-registered-v1.json", notes, ""]
        return " | ".join(cells).strip()

    split = ids["arm"]["split_identity_hash"]
    legality_row = " | ".join([
        "", args.registered_at[:10], LEGALITY_ROW, "model-free-check",
        "Build the intent -> slot-type legality table cell W1 pins: the (intent, slot type) pairs the released TRAIN exemplar store (size-pool-annotated-exemplars, 9,354 utterances) carries in at least two distinct utterances, read from the store's own annotation text (type names only); prove the store's observed carded pairs equal the 402 authored bindings and that the store holds no Fold A utterance. Zero model, server, tokenizer, encoder, embedder, scorer, network, GPU and paid-API contacts.",
        "no model or tool contact; arithmetic over the released exemplar store, the authored slot-contract source and the roster's sample ids",
        "slurp TRAIN exemplar store (9,354 utterances, Fold A-free); the Fold A roster's ids only", "discovery", split, "no", "0", "0", "0",
        "No new exposure: the released store is already exposed knowledge; no governed label, transcript, devel or test file is opened. Prior exposure inherited in full.",
        LEGALITY_RECEIPT,
        f"REGISTERED BEFORE USE (DRAFT, root countersignature pending) {args.registered_at[:10]} at study commit {args.study_commit}. Artifact {LEGALITY_RELPATH} sha256 {ids['arm']['candidate_legality_source']['sha256']}; builder {BUILD_SCRIPT}; rule pool-utterance-support-at-least-2-v1; 402 authored pairs, 286 kept, 116 removed; roster utterances in the store 0. It authorises nothing.",
        "",
    ]).strip()
    measurement_row = " | ".join([
        "", args.registered_at[:10], MEASUREMENT_ROW, "model-free-check",
        "Replay the sealed AGREE arm's slot-card selection from its own sealed Perception shortlists (1,080 / 1,080 identical in order), re-take it over the W1-narrowed index, price the difference in exact tokens of each rendered card block, and count offline the rows where a card for a GOLD slot type would be dropped. Zero model, server, encoder, embedder, scorer, network, GPU and paid-API contacts.",
        f"no model contact; local vocab-only llama-tokenize process ({m['inputs']['tokenizer']['invocations']} invocations) over the 54 committed card texts; read-only sealed phase summaries",
        "slurp TRAIN Fold A 1080, sealed AGREE phase summaries and outputs (ids, counts and type names only); governed train.jsonl gold for Fold A rows, offline, counts only",
        "discovery", split, "no", "0", "0", "0",
        "No new speech exposure; the sealed summaries were exposed by the arm that sealed them, and Fold A gold was already read offline by the audits of this fold. Prior exposure inherited in full.",
        MEASUREMENT,
        f"REGISTERED BEFORE USE (DRAFT, root countersignature pending) {args.registered_at[:10]} at study commit {args.study_commit}. Receipt {MEASUREMENT} sha256 {measurement_sha}; script {MEASURE_SCRIPT}. Measured: cards per row {m['cards']['per_row_flown']['mean']} -> {m['cards']['per_row_w1']['mean']}; -{saving['tokens_per_solver_contact']['mean']} tokens per Solver contact, -{saving['tokens_per_row_over_every_contact_rendering_the_block']['mean']} per row; {harm['rows_losing_a_gold_type_card']} rows / {harm['gold_items_of_lost_types']} gold items lose their type's card ({harm['of_which_delivered_exactly_right_by_agree']} delivered right). No utterance text, filler or answer persisted. It authorises nothing.",
        "",
    ]).strip()
    read_row = " | ".join([
        "", args.registered_at, READ_ROW, "model-free-check",
        f"The cell W1 read: the narrowed card route against the shared in-chain A/A {SHARED_AA_RUN} under the no-harm rule (harm margins intent {H_INTENT} / SLU {H_SLU}), per-scenario tables in both weightings, the measured Solver token saving, and the registered harm rows read row by row.",
        "No model, tokenizer, encoder or server contact: the registered read driver over the sealed per-sample official scores and sealed receipts.",
        "slurp TRAIN Fold A 1080", "discovery", split, "no", "0", "0", "0.0",
        "Reads only sealed manifests of this package and its registered comparators; no new audio, gold or reference exposure.",
        f"{PACKAGE}/analysis-recipe-v1.json",
        "REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending; countersigned after the seal and before any number is read). No utterance text, gold, transcript or model output is printed or persisted.",
        "",
    ]).strip()

    fresh = {}
    for key in CELLS:
        for kind in ("generation", "fit"):
            run_id = ids[key]["fit"]["run_id"] if kind == "fit" else ids[key]["run_id"]
            fresh[run_id] = flight_row(key, kind)
    fresh[LEGALITY_ROW] = legality_row
    fresh[MEASUREMENT_ROW] = measurement_row
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
        raise SystemExit("the ledger carries some but not all W1 rows; refusing to guess")
    if replaced:
        wr(LEDGER, "\n".join(lines))
        return f"replaced-{replaced}"
    header = (
        "\n## Cell W1: slot-card selection (knowledge wave item W1) -- the arm, its four-row smoke, the model-free legality build, "
        "the model-free measurement and the READ row (DRAFT, root countersignature pending)\n\n"
        "Four unconsumed flight rows -- the W1 arm, its four-row form smoke and their two FIT spend identities -- plus two model-free "
        "rows (the legality table build and the card-selection measurement) and the READ row. Owner decisions 127, 161 and 164; "
        f"authority {AUDIT} (K8). The arm is read at the coordinator's shared in-chain A/A {SHARED_AA_RUN}. None of these rows is "
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
