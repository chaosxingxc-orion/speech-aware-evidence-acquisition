#!/usr/bin/env python3
"""Write cell W4's readiness package (knowledge-wave item W4, slot conventions; owner
decision 164) from the derived fragments, the model-free build outputs and the offline
Fold A estimate -- config and receipt-pinned bytes only: no adapter contact, no server,
no lock, no model, tokenizer, encoder, embedder or scorer contact. It flips nothing and
mints nothing.

Package ``docs/readiness/2026-09-27-slurp-stage3-w4-slot-conventions-fold-a-v1/`` and the
preregistration beside it. ``--append-ledger`` writes the DRAFT exposure rows (four flight
rows, the READ row, and the two model-free rows for the build and the estimate), replacing
in place on re-run. ``--check-dir`` folds the per-phase prompt-budget receipts of an
already-run ``core.flight.cli check`` (it attaches to nothing) into the facts.

    python scripts/flights/w4/write_slurp_w4_registration.py --data-root "$SPEECHRL_DATA_DIR" \\
        --study-commit <sha> --registered-at 2026-09-27T17:00:00.000000+00:00 \\
        [--check-dir /home/chao/saea-worktrees/.w4-checks] [--append-ledger]
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

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash  # noqa: E402

PACKAGE = "docs/readiness/2026-09-27-slurp-stage3-w4-slot-conventions-fold-a-v1"
PREREG = PACKAGE + "-preregistration.md"
LEDGER = "docs/exposure-ledger.md"
CELLS = {"arm": "slurp-native-stage3-w4-fold-a-v1", "smoke": "slurp-native-stage3-w4-fold-a-smoke-4-v1"}
PARENTS = {"arm": "slurp-native-stage3-agree-w1-fold-a-v1", "smoke": "slurp-native-stage3-agree-w1-fold-a-smoke-4-v1"}
PREFIX = {"arm": "", "smoke": "smoke-"}
COMPARATOR_RUN = "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1"
COMPARATOR_ATTEMPT = "attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1"
COMPARATOR_OFFICIAL = {"slu_f1": 65.1575, "intent_accuracy": 85.8333}
SHARED_AA_RUN = "SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1"
READ_RUN = "SAEA-SLURP-STAGE3-W4-FOLD-A-PAIRED-READ-V1"
BUILD_ROW = "SAEA-SLURP-SLOT-CONVENTIONS-W4-PREPARE-V1"
ESTIMATE_ROW = "SAEA-SLURP-W4-FOLD-A-OFFLINE-ESTIMATE-V1"
SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"
DECISION_ID = "slurp-stage3-w4-fold-a-admission-v1"
DECISION_RELPATH = "coordination/slurp-stage3-w4-fold-a-v1/root-admission-v1.json"
AGREE_SUPPLY_OUTPUT = {"arm": "eab5c61e92a47c1723c478f2b7914abade6152b195f676d7d32251f3d18884ae",
                       "smoke": "308601c52b54ec49013422349e045dd3a4d621c530bf3d2be730fdfe1fdd2fc9"}
H_SLU, H_INTENT = 1.2485, 0.9943
BENEFIT_FLOOR = 2.5
THE_PIN = "knowledge_stores.slot-contracts"
ALLOWED_PREFIXES = ("knowledge_stores.slot-contracts.release.", "knowledge_stores.slot-contracts.snapshot.",
                    "preparation_source_receipts", "native_contact_fit.", "prepared_phase_supply", "what_this_is")

PREP = "prepared/SAEA-SLURP-SLOT-CONVENTIONS-W4-PREPARE-V1"
STORE_NS = "knowledge/slurp/semantic/slot-contracts-w4-v1"
PREP_REGISTRATION = "docs/readiness/2026-09-27-slurp-slot-contracts-w4-preparation-registration-v1.json"
ESTIMATE = "analysis/SAEA-SLURP-W4-FOLD-A-OFFLINE-ESTIMATE-V1/estimate-v1.json"
BUILD_SCRIPT = "scripts/build_slurp_slot_conventions_w4.py"
ESTIMATE_SCRIPT = "scripts/analysis/slurp_w4_fold_a_offline_estimate.py"
DERIVE_SCRIPT = "scripts/flights/w4/derive_slurp_w4_cells.py"
CONFIG_TEST = "tests/unit/test_w4_config.py"
AUDIT = "docs/results/2026-09-27-slurp-knowledge-content-audit.md (branch fable/kaudit, commit 0d5e2693)"
ERRSRC = "docs/results/2026-09-27-slurp-agree-arm-error-sources.md (branch fable/errsrc, commit 96666424)"
SYNTHESIS = "docs/results/2026-09-27-slurp-mechanism-synthesis.md (branch fable/synthesis, commit 8366307c)"
M4B_VERDICTS = "docs/results/2026-09-17-slurp-b4b-slot-store-v2-verdict.md; docs/results/2026-09-19-slurp-b4b-replicate-verdict.md"
INSTRUMENT = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"
OWNER_DECISIONS = "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md"
AGREE_PACKAGE = "docs/readiness/2026-09-26-slurp-stage3-agree-w1-fold-a-v1"
GATE = "scripts/checks/stage3_effect_floor_check.py"
READ_DRIVER = "scripts/analysis/stage3_paired_read.py (branch fable/launchgate) or scripts/analysis/plan_cell_read.py"


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


def sha_file(path: str | Path) -> str:
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
        pin = [k for k in changed if k.startswith(THE_PIN + ".")]
        bookkeeping = [k for k in changed if k.startswith(ALLOWED_PREFIXES) and k not in pin]
        block = [k for k in changed if k.split(".", 1)[0] in experiment_keys and k not in pin and k not in bookkeeping]
        other = [k for k in changed if k not in pin and k not in bookkeeping and k not in block]
        if other:
            raise SystemExit(f"{key}: composed config differs from its AGREE parent beyond the pin and bookkeeping: {other}")
        if sorted(pin) != sorted(f"{THE_PIN}.{p}.{f}" for p in ("release", "snapshot") for f in ("relpath", "sha256")):
            raise SystemExit(f"{key}: the one pin did not move: {pin}")
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
            "slot_store": composed.values["knowledge_stores"]["slot-contracts"],
            "composed_config_diff_against_the_agree_cell": {"the_one_pin": pin, "bookkeeping": bookkeeping,
                                                            "experiment_fragment_own_block": block, "anything_else": other},
        }
    return out


def fold_check(check_dir: str | None) -> dict:
    if not check_dir:
        return {"status": "PENDING_CHECK"}
    out = {"status": "MEASURED_BY_CHECK", "cells": {}}
    for key, cell_id in CELLS.items():
        path = Path(check_dir) / f"check-{cell_id}.json"
        if not path.is_file() or not path.read_text(encoding="utf-8").strip():
            out["cells"][key] = {"status": "MISSING", "path": str(path)}
            continue
        report = json.loads(path.read_text(encoding="utf-8"))
        preflight = report.get("preflight") or {}
        phases = []
        for receipt in preflight.get("prompt_budget") or ():
            entry = {"phase": receipt.get("phase"), "decision": receipt.get("decision")}
            breakdown = receipt.get("breakdown") if isinstance(receipt.get("breakdown"), dict) else {}
            for name in ("physical_margin_tokens", "operational_margin_tokens", "rendered_text_tokens",
                         "required_window_tokens", "completion_token_ceiling", "speech_feature_tokens"):
                if name in receipt:
                    entry[name] = receipt[name]
                elif name in breakdown:
                    entry[name] = breakdown[name]
            phases.append(entry)
        out["cells"][key] = {"check_path": str(path), "blockers": report.get("blockers"),
                             "scientific_readiness": report.get("scientific_readiness"),
                             "config_hash": preflight.get("config_hash"), "protocol_hash": preflight.get("protocol_hash"),
                             "prompt_budget_per_phase": phases}
    return out


def tables(conventions: dict, changes: dict) -> dict:
    """Commit-safe tables: slot TYPE names, counts, schematic rules, and the value lists of
    CLOSED types only (semi-closed and open values stay in the data-root store)."""
    revised = changes["changed_cards"]
    vocab_rows, scope_rows, span_rows = [], [], []
    for t in revised:
        v = conventions["vocabulary"].get(t, {})
        vocab_rows.append({
            "slot_type": t, "class": v.get("class"), "pool_mentions": v.get("mentions"),
            "distinct_values": v.get("distinct_values"), "loo_value_coverage": v.get("loo_value_coverage"),
            "n90": v.get("n90"), "listed_values": len(v.get("listed", [])),
            "listed_coverage": v.get("listed_coverage"),
            "closed_value_list": [value for value, _ in v.get("listed", [])] if v.get("class") == "closed" else None,
        })
        s = conventions["annotation_scope"].get(t, {})
        scope_rows.append({
            "slot_type": t, "values_with_evidence": s.get("values_with_evidence", 0),
            "spoken_occurrences": s.get("spoken_occurrences", 0),
            "tagged_occurrences": s.get("tagged_occurrences", 0), "untagged_occurrences": s.get("untagged_occurrences", 0),
            "tagged_when_spoken_values": len(s.get("tagged_when_spoken", [])),
            "usually_untagged_values": len(s.get("usually_untagged", [])),
            "tagged_when_spoken_counts": [[r["tagged"], r["tagged"] + r["untagged"]] for r in s.get("tagged_when_spoken", [])],
            "usually_untagged_counts": [[r["tagged"], r["tagged"] + r["untagged"]] for r in s.get("usually_untagged", [])],
        })
        e = conventions["span_extent"].get(t, {})
        span_rows.append({"slot_type": t, "located_mentions": e.get("located_mentions", 0), "rules": [
            {"edge": r["edge"], "word": r["word"], "side": r["side"], "count": r["count"], "cases": r["cases"]}
            for r in e.get("rules", [])]})
    return {"vocabulary": vocab_rows, "annotation_scope": scope_rows, "span_extent": span_rows,
            "card_byte_deltas": {c["slot_id"]: {"v2": c["bytes_v2"], "w4": c["bytes_w4"], "added": c["added_bytes"],
                                                "components": c["components"]} for c in changes["cards"]},
            "classes_all_types": {k: sum(1 for v in conventions["vocabulary"].values() if v["class"] == k)
                                  for k in ("closed", "semi-closed", "open")},
            "thresholds": conventions["thresholds"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--study-commit", required=True)
    parser.add_argument("--registered-at", required=True)
    parser.add_argument("--branch", default="fable/w4")
    parser.add_argument("--worktree", default="/home/chao/saea-worktrees/fable-w4")
    parser.add_argument("--check-dir", default=None)
    parser.add_argument("--append-ledger", action="store_true")
    args = parser.parse_args(argv)
    os.chdir(REPO_ROOT)
    data = Path(args.data_root)

    conventions = json.loads((data / PREP / "conventions-v1.json").read_text(encoding="utf-8"))
    changes = json.loads((data / PREP / "CHANGES.json").read_text(encoding="utf-8"))
    build_receipt = json.loads((data / PREP / "receipt.json").read_text(encoding="utf-8"))
    estimate = json.loads((data / ESTIMATE).read_text(encoding="utf-8"))
    completion = json.loads((data / STORE_NS / "completion.json").read_text(encoding="utf-8"))
    if build_receipt["script"]["sha256"] != sha_file(BUILD_SCRIPT):
        raise SystemExit("the build script changed after the build; rebuild into a new namespace")
    if estimate["inputs"]["conventions_sha256"] != sha_file(data / PREP / "conventions-v1.json"):
        raise SystemExit("the estimate was not computed on these conventions")

    ids = identities()
    arm, smoke = ids["arm"], ids["smoke"]
    caps, smoke_caps = arm["family_budget"], smoke["family_budget"]
    store = {
        "release": arm["slot_store"]["release"], "snapshot": arm["slot_store"]["snapshot"],
        "completion": {"relpath": STORE_NS + "/completion.json", "sha256": sha_file(data / STORE_NS / "completion.json")},
        "authored_source": completion["binding"]["authored_source"], "permitted_roster": completion["binding"]["permitted_roster"],
        "exact_support_roster": completion["exact_support_roster"], "forbidden_rosters": completion["forbidden_rosters"],
        "registration": {"relpath": PREP_REGISTRATION, "sha256": sha_file(PREP_REGISTRATION)},
        "build_outputs": build_receipt["outputs"], "build_receipt_sha256": sha_file(data / PREP / "receipt.json"),
        "contacts": completion["contacts"],
        "replaces": {"release": "knowledge/slurp/semantic/slot-contracts-v2/release.json (f8e42d4f...)",
                     "snapshot": "knowledge/slurp/semantic/slot-contracts-v2/snapshot.json (content d5992bd1...)"},
        "changed_cards": changes["changed_cards"], "total_added_bytes": changes["total_added_bytes"],
        "all_key_text_unchanged": changes["all_key_text_unchanged"],
        "source": "the R01-excluded TRAIN exemplar pool size-pool-annotated-exemplars-minus-r01 (8,554 utterances, content hash 6eaa03aea96a1928dd1ac29ecc71c3955c136498c9f8114266eaa830d1207c63); no Fold A, Fold B, DEV or test byte, no flight output and no score read to author a value",
    }
    table = tables(conventions, changes)
    cost = estimate["cost"]
    analogue = estimate["m4b_analogue"]
    exp = analogue["w4_expected_pp"]
    fit = fold_check(args.check_dir)

    rule = (
        "NO-HARM ADMITTED: against the knowledge wave's SHARED in-chain A/A " + SHARED_AA_RUN + " flown in the same "
        f"chain, the paired CI95 lower bound of the official pooled SLU-F1 delta (PRIMARY -- the mechanism acts on slots, "
        f"so owner decision 133's intent-primary rule, scoped to intent-acting mechanisms, does not apply and decision "
        f"115's shape holds) is not below -{H_SLU} pp AND the paired CI95 lower bound of the intent-accuracy delta (the "
        f"guard) is not below -{H_INTENT} pp -- each at its own Fold A own-null half-width ({INSTRUMENT} section 2d). "
        "HARMFUL: a measured loss on either metric (CI95 upper bound below zero, decision 25). A SLU-F1 CI95 lower bound "
        f"above zero is REPORTED as a development-fold effect beside the no-harm verdict, never as an admission of benefit "
        f"(the design's benefit floor is {BENEFIT_FLOOR} pp and the measured analogue sits below it). Every verdict carries "
        "the per-scenario table in both weightings, the frontier row (decision 75), the per-type FN/FP table on the 19 "
        "revised types, the realised prompt-token delta per Solver/Reviewer/Planner contact and per row, and the "
        "K2/K3/K4 item classes of registered-facts-v1.json read on the sealed arm."
    )
    note = (
        f"W4 acts on SLOTS, so SLU-F1 is primary and intent the guard (owner decision 133 scopes intent-primary to "
        f"intent-acting mechanisms). The expectation is declared from the measured analogue only (row 139): M4b (cell B4b, "
        f"the date/time slot-contract revision) moved official pooled SLU-F1 by +2.5519 (first) and +1.5403 (request-identical "
        f"replicate) over {analogue['m4b_fn_items_on_its_eight_types']} FN items on its eight revised types -- "
        f"{analogue['m4b_pp_per_fn_item']['replicate']:.6f} to {analogue['m4b_pp_per_fn_item']['first']:.6f} pp per item; W4 "
        f"targets {analogue['w4_fn_items_on_revised_types_with_card_delivered']} FN items on its 19 revised types where the "
        f"card was delivered on the AGREE arm, so the analogue expects {exp['replicate']} to {exp['first']} pp (mean "
        f"{exp['mean']}). That is BELOW the design's {BENEFIT_FLOOR} pp benefit floor at n = 1,080, so a benefit declaration "
        f"would be refused (effect-below-floor) and the cell is declared NO-HARM: expected_effect_pp 0.0, claims_benefit "
        f"false, harm_margin_pp {H_SLU} (SLU, primary) with intent {H_INTENT} as the guard; the analogue is recorded in "
        "registered-facts-v1.json (expectation_basis) and never used as an admission bar. Read against the shared in-chain "
        "A/A flown in the same chain (rule 3)."
    )
    measurement = {
        arm["run_id"]: {
            "admission": "no-harm", "claims_benefit": False, "expected_effect_pp": 0.0,
            "harm_margin_pp": H_SLU, "harm_margin_pp_by_metric": {"slu_f1": H_SLU, "intent_accuracy": H_INTENT},
            "measurement_design": "cross-flight-with-in-chain-replicate",
            "primary_metric": "official pooled SLU-F1 (primary: a slot-acting mechanism, owner decision 133's scope), intent accuracy the non-inferiority guard",
            "replicate_run_id": SHARED_AA_RUN, "rows": 1080, "note": note,
        },
        smoke["run_id"]: {
            "claims_benefit": False, "expected_effect_pp": 0.0, "measurement_design": "form-proof",
            "primary_metric": "none (structural form only)", "rows": 4,
            "note": "Four rows prove FORM and nothing else: the slot-contracts-w4-v1 release loads by its pins, every extended card renders, every request fits and the episode completes. Scored by no one, read by no one.",
        },
    }
    k = estimate["counts"]
    fold_a = {
        "arm_read": {"run_id": COMPARATOR_RUN, "official": estimate["arm"]["official"], "exact_tp_fp_fn": estimate["arm"]["exact_tp_fp_fn"],
                     "pooled_span_f1": estimate["arm"]["pooled_span_f1"]},
        "items": {
            "K2_omission_gold_value_in_w4_list_or_tagged_when_spoken": k.get("K2", {}).get("omission_gold_value_listed", 0),
            "K2_wrong_filler_gold_listed_prediction_not": k.get("K2", {}).get("wrong_gold_listed_pred_not", 0),
            "K3_over_emission_value_usually_untagged": k.get("K3", {}).get("over_emission_value_usually_untagged", 0),
            "K4_containment_wrong_fillers": k.get("K4", {}).get("containment_wrong_filler", 0),
            "K4_span_rule_would_fix": k.get("K4", {}).get("span_rule_would_fix", 0),
            "risk_exact_tp_value_usually_untagged": k.get("risk", {}).get("exact_tp_value_usually_untagged", 0),
            "risk_listed_value_spoken_but_untagged_in_gold": k.get("risk", {}).get("listed_value_spoken_untagged", 0),
        },
        "rows_touched": estimate["rows_touched"],
        "per_type": estimate["per_type"],
        "span_f1_oracle_ceilings_pp": estimate["span_f1_oracle_ceilings_pp"],
        "estimate": {"relpath": ESTIMATE, "sha256": sha_file(data / ESTIMATE), "script": {"relpath": ESTIMATE_SCRIPT, "sha256": sha_file(ESTIMATE_SCRIPT)}},
        "boundary": "only error items on a type whose W4 card the row was actually delivered (the AGREE consumption records) are counted; gold read offline; counts only; development numbers (owner decisions 28 and 86)",
    }
    token_cost = {
        "chars_per_token_measured_on_the_agree_solver": cost["chars_per_token_measured"],
        "per_phase": cost["per_phase"], "per_row": cost["per_row"],
        "flight_total_added_tokens": cost["total_added_tokens"], "flight_total_prompt_tokens_realised_agree": cost["total_prompt_tokens_realised"],
        "added_share_of_prompt_volume": round(cost["total_added_tokens"] / cost["total_prompt_tokens_realised"], 4),
        "compaction_projection": (
            "the projected widest realised request per phase (the sealed AGREE per-contact prompt tokens plus that contact's W4 "
            "byte delta at the measured ratio) stays below the live operational budget (24,576 slot - 3,072 reserve - 512 "
            "completion = 20,992): no realised request is projected to compact"
        ),
    }
    fit_statement = (
        "W1 has NOT landed (branch fable/w1 carries no commit beyond master at registration), so W4 is registered to fly "
        "ALONE on the AGREE form; it composes with W1 later without change (W4 only extends cards a row already receives). "
        "The audit's '226 tokens of headroom' is the PREFLIGHT operational margin measured by core.flight.cli check with its "
        "placeholder 4-bytes-per-token counter on the widest representative request; under the armed context_fit_policy "
        "compact-or-abstain a COMPACT_REQUIRED preflight with a non-negative PHYSICAL margin is recorded and proceeds (the "
        "AGREE and COMP-1 cells already read COMPACT_REQUIRED on the Solver), and only a negative physical margin refuses. "
        "The binding facts are therefore (a) the check's physical margin after W4 (folded in 'fit'), and (b) the realised "
        "requests, projected from the sealed AGREE trace, which stay far below the live budget (token_cost.compaction_projection)."
    )
    facts = {
        "schema": "saea-registered-facts-v1",
        "_note": f"Every model-free fact this registration rests on, and the CANONICAL stage3_measurement block {GATE} resolves (keyed by run id).",
        "registered_at_utc": args.registered_at, "study_commit_at_registration": args.study_commit,
        "owner_decisions": {
            "164": "knowledge-wave item W4 (slot conventions) prepared and registered now, to be flown in the knowledge wave after 09:00 (owner, 2026-09-27: agreed; start the analysis and preparation immediately)",
            "133": "intent is primary only for intent-acting mechanisms; a slot-acting mechanism keeps decision 115's shape (SLU primary, intent guard)",
            "139": "no prior: the expectation is declared from a measured analogue only (M4b)",
            "127": "the no-harm admission form and its margins at the design's measured floor",
            "28/86": "TRAIN Fold A numbers are development numbers, never a test claim",
        },
        "rows": 1080, "stage3_measurement": measurement,
        "the_item": {
            "evidence": [
                f"{AUDIT}: K2 (157 gold items whose value TRAIN lists missed or wrong, SLU ceiling +9.29), K3 (278 over-emissions, 193 of 202 on intent-right rows type-legal, +9.30), K4 (91 of 183 wrong same-type fillers a sub/super-span, +5.33)",
                f"{ERRSRC}: 27.13 of the 34.84 SLU-F1 points lost sit on intent-RIGHT rows; the slot card was delivered on 644 of 660 error items; relative-day dates the largest single item",
                f"{SYNTHESIS}: gains come from row-matched content reaching the deciding node; M4b is the successful slot-contract precedent",
            ],
            "the_change": "the released slot-contracts-v2 cards with 19 cards' extraction_cues and admissible_formats extended by K2/K3/K4 conventions mined from the R01-excluded TRAIN exemplar pool; intent bindings, facet keys and every other card byte-identical",
            "cards_chosen_by": "the audit's per-type loss table plus its closed types (as the A3 audit chose M4b's cards); every value and count derived from the pool only",
        },
        "store": store,
        "conventions_tables": table,
        "token_cost": token_cost,
        "fit_statement": fit_statement,
        "fit": fit,
        "fold_a_offline": fold_a,
        "expectation_basis": {"m4b_analogue": analogue, "m4b_verdicts": M4B_VERDICTS, "benefit_floor_pp": BENEFIT_FLOOR,
                              "declared": "no-harm (the analogue is below the floor)"},
        "identity": {key: {k2: v for k2, v in ids[key].items() if k2 != "composed_config_diff_against_the_agree_cell"} for key in CELLS},
        "composed_config_diff_against_the_agree_cell": {key: ids[key]["composed_config_diff_against_the_agree_cell"] for key in CELLS},
        "comparator": {"run_id": COMPARATOR_RUN, "attempt_id": COMPARATOR_ATTEMPT, "official": COMPARATOR_OFFICIAL, "never_reflown": True,
                       "in_chain_replicate": {"run_id": SHARED_AA_RUN, "registered_by": "the coordinator (knowledge wave shared A/A)",
                                              "why": "rule 4 refuses a cross-flight contrast with no in-chain replicate"},
                       "margins": {"h_slu": H_SLU, "h_intent": H_INTENT, "source": f"{INSTRUMENT} section 2d"}},
        "decision_rule": rule,
        "byte_identity_expectation": {
            "agree_first_phase_supply_output_sha256": AGREE_SUPPLY_OUTPUT,
            "claim": "the slot-contracts store is not an input to the first-phase (Perception boundary) supply, so the supply the flip mints for the arm must carry the AGREE arm's output digest and the smoke's the AGREE smoke's; a different digest means the boundary channel moved -- stop and report",
        },
        "budget_arithmetic": {"arm_family_budget": caps, "smoke_family_budget": smoke_caps,
                              "note": "the AGREE arithmetic (1,080 x 11 contacts, run-cumulative); W4 adds prompt tokens, never contacts"},
        "prohibitions": [
            "No test-split, Fold B or DEV contact or read.", "No re-flying of the sealed AGREE comparator.",
            "No second factor: no other template, knob, store, roster, geometry or session change.",
            "No paper-scale profile.", "No flight before root mints the decision receipt, the coordinator registers the shared A/A and the cells are flipped.",
            "A SLU gain is never reported as an admitted benefit under this no-harm declaration.",
        ],
    }
    facts_sha = wjson(PACKAGE + "/registered-facts-v1.json", facts)

    protocol = {
        "schema": "saea-registered-protocol-v1", "protocol_id": "slurp-stage3-w4-fold-a-protocol-v1",
        "registered_at_utc": args.registered_at, "study_commit_at_registration": args.study_commit,
        "source_tree": f"studies/speech-aware-evidence-acquisition, worktree {args.worktree}, branch {args.branch}",
        "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP",
        "the_question": "With the slot-contract cards extended by TRAIN-mined slot conventions (value vocabulary, annotation scope, span extent) and nothing else changed, does the official pooled SLU-F1 on TRAIN Fold A 1,080 stay within the design's null -- and where does it move -- read against the knowledge wave's shared in-chain A/A?",
        "one_factor": f"{THE_PIN}: slot-contracts-v2 -> slot-contracts-w4-v1 (release {store['release']['sha256']}, snapshot content {store['snapshot']['sha256']}) and its two receipts appended to preparation_source_receipts",
        "cells": {key: {k2: ids[key][k2] for k2 in ("cell", "experiment", "run_id", "attempt_id", "rows", "composed_config_hash", "protocol_hash", "split_identity_hash")}
                  | {"fit_run_id": ids[key]["fit"]["run_id"], "fit_attempt_id": ids[key]["fit"]["attempt_id"]} for key in CELLS},
        "comparator": facts["comparator"], "decision_rule_fixed_here": rule,
        "development_numbers_only": "Every number is a TRAIN Fold A development number (owner decisions 28 and 86), never a test claim.",
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
                "schema": f"saea-registered-{kind}-plan-v1", "plan_kind": kind, "cell": identity["cell"],
                "experiment": identity["experiment"], "composed_config_hash": identity["composed_config_hash"],
                "registered_at_utc": args.registered_at, "status": protocol["status"], "source_tree": protocol["source_tree"],
                "preparation_base_commit": args.study_commit, "expected_session_id": SESSION,
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
                    "The shared core.flight.cli FIT path under this cell's own native_contact_fit ids; request envelopes only, no generation." if is_fit else
                    f"Shared core.flight.cli campaign over the knowledge wave's committed campaign plan, which the coordinator composes to carry the shared in-chain A/A {SHARED_AA_RUN} and this arm in ONE chain." if key == "arm" else
                    "Shared core.flight.cli worker on this cell alone; the smoke is outside any campaign plan and never scored."
                ),
                "prepared_phase_supply": {"relpath": f"prepared/{identity['run_id']}/phase-supply-v1.json", "sha256": "MINTED_AT_THE_FLIP",
                                          "expected_output_sha256": AGREE_SUPPLY_OUTPUT[key],
                                          "note": facts["byte_identity_expectation"]["claim"]},
                "protocol_document": {"relpath": PACKAGE + "/protocol-registered-v1.json", "sha256": protocol_sha},
                "one_factor": protocol["one_factor"],
                "purpose": f"{run_id}: " + ("request envelopes only; reads nothing." if is_fit else rule if key == "arm" else "structural form proof only: no score and no read."),
                "quality_read_gate": "No task-quality read before the complete sealed manifest, the ordered outputs, the phase summary and the single complete official TRAIN score exist for BOTH this arm and the shared in-chain A/A; a verdict against the sealed comparator alone is refused.",
            }
            plan_shas[run_id] = wjson(f"{PACKAGE}/{PREFIX[key]}{kind}-plan-registered-v1.json", plan_doc)

    recipe = {
        "schema": "saea-slurp-paired-analysis-recipe-v1", "recipe_id": "slurp-stage3-w4-fold-a-paired-analysis-v1",
        "title": "Cell W4 -- the standard paired roster read on SLU (primary) + intent (guard) against the knowledge wave's shared in-chain A/A, sealed AGREE beside it, under the no-harm rule",
        "registered_at_utc": args.registered_at,
        "read_run_id": READ_RUN,
        "run_ids": {"read": READ_RUN, "arm": arm["run_id"], "in_chain_replicate": SHARED_AA_RUN, "comparator": COMPARATOR_RUN},
        "arms": {
            "arm": {"run_id": arm["run_id"], "attempt_id": arm["attempt_id"], "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL", "outputs_sha256": "PENDING_SEAL"},
            "in_chain_replicate": {"run_id": SHARED_AA_RUN, "role": "the within-chain null (registered by the coordinator)", "run_manifest_sha256": "PENDING_SEAL"},
            "comparator": {"run_id": COMPARATOR_RUN, "attempt_id": COMPARATOR_ATTEMPT, "role": "context, sealed, never re-flown"},
        },
        "resampling": {"bootstrap_draws": 10000, "metrics": ["slu_f1_f1", "scenario_action_exact"], "seed": 20260927, "unit": "row (paired)"},
        "decision_rule": rule, "margins": {"h_slu": H_SLU, "h_intent": H_INTENT},
        "steps": [
            "1. Refuse unless the W4 arm and the shared A/A each carry a COMPLETE sealed 1,080-row manifest with one successful complete official TRAIN score and this package's / the A/A package's config hashes.",
            "2. Structural stage: every W4 request carries the slot-contracts-w4-v1 snapshot identity; realised prompt tokens per Solver/Reviewer/Planner contact, arm minus A/A, against the registered token_cost; count of compacted contacts on each arm (expected 0).",
            "3. Score once per arm with slurp-slu-official-train through core.scoring_batch, never sharded.",
            "4. Paired row bootstrap (10,000 draws, seed 20260927) of arm minus shared A/A on official pooled SLU-F1 (primary) and intent accuracy (guard); the same delta against the sealed AGREE arm BESIDE it, never instead.",
            f"5. Apply the rule: ADMITTED (no harm) iff SLU lower bound >= -{H_SLU} and intent lower bound >= -{H_INTENT}; HARMFUL iff either upper bound < 0; otherwise NOT ADMITTED (width). A SLU lower bound above zero is reported as a development-fold effect, never as an admitted benefit.",
            "6. Mechanism read (model-free, counts only): per revised type FN/FP arm vs A/A; the registered K2 / K3 / K4 item classes (registered-facts-v1.json fold_a_offline) re-read on the sealed arm -- converted, unchanged, broken -- and the two risk classes (usually-untagged true positives lost; listed-value over-emissions gained).",
            "7. Report the per-scenario table in both weightings and the frontier row (decision 75).",
        ],
        "read_driver_family": READ_DRIVER,
        "output": {"analysis_root": f"analysis/{READ_RUN}"},
        "boundary": "A development read on a TRAIN construction fold (owner decisions 28 and 86); never a test claim. No utterance text, transcript, gold label or model output is printed or persisted.",
    }
    recipe_sha = wjson(PACKAGE + "/analysis-recipe-v1.json", recipe)

    eligible = [arm["run_id"], arm["fit"]["run_id"], smoke["run_id"], smoke["fit"]["run_id"]]
    draft = {
        "_draft_note": "A DRAFT for root to mint on the data root with scripts/flights/w4/w4_mint_receipt.py (status decided, recorded_at_utc stamped, antecedents re-hashed, never overwrites). It authorises nothing while its status is not 'decided'.",
        "schema": "saea-campaign-decision-v1", "decision_id": DECISION_ID, "status": "DRAFT-NOT-MINTED",
        "recorded_at_utc": None, "owner": "root", "coordinator": "Fable5.1", "eligible_run_ids": eligible,
        "cell_kind": "Stage-3 knowledge-wave item (label none), no-harm declaration. One arm on TRAIN Fold A 1,080 read at the knowledge wave's shared in-chain A/A, and a four-row form smoke.",
        "decision": "Fly cell W4: the retained AGREE arm with the slot-contracts store re-pinned to slot-contracts-w4-v1 (TRAIN-mined slot conventions appended to 19 existing cards), read at the shared in-chain A/A " + SHARED_AA_RUN + " flown in the same chain; SLU-F1 primary, intent guard; no-harm at the Fold A half-widths.",
        "authorization_basis": f"Owner decision 164 (knowledge wave W4); 133 (scope of intent-primary), 139 (expectation from a measured analogue), 127 (no-harm form), 28/86; the audit {AUDIT}; the instrument {INSTRUMENT}.",
        "antecedents": {
            "owner_decisions": {"path": OWNER_DECISIONS, "sha256": sha_file(OWNER_DECISIONS)},
            "instrument_note": {"path": INSTRUMENT, "sha256": sha_file(INSTRUMENT)},
            "preregistration": {"path": PREREG, "sha256": None},
            "readiness_readme": {"path": PACKAGE + "/README.md", "sha256": None},
            "protocol": {"path": PACKAGE + "/protocol-registered-v1.json", "sha256": protocol_sha},
            "registered_facts": {"path": PACKAGE + "/registered-facts-v1.json", "sha256": facts_sha},
            "analysis_recipe": {"path": PACKAGE + "/analysis-recipe-v1.json", "sha256": recipe_sha},
            "store_registration": {"path": PREP_REGISTRATION, "sha256": sha_file(PREP_REGISTRATION)},
            "build_script": {"path": BUILD_SCRIPT, "sha256": sha_file(BUILD_SCRIPT)},
            "config_proof": {"path": CONFIG_TEST, "sha256": sha_file(CONFIG_TEST) if Path(CONFIG_TEST).is_file() else None},
            "base_cell": f"the retained AGREE arm {COMPARATOR_RUN} (owner decision 161): W4 is that fragment with one pin moved",
            "registration_base_commit": args.study_commit,
        },
        "budget": {**{k2: caps[k2] for k2 in sorted(caps)}, "smoke": smoke_caps, "paid_api_calls": 0, "plan_budget_is_run_cumulative": True},
        "claim_boundary": "No superiority, generalisation, component-causal, held-out, confirmatory or paper-scale claim; a no-harm reading of one knowledge-content change on a development fold.",
        "failure_policy": protocol["failure_policy"],
        "not_authorized": ["any flight before the cells are flipped, the receipt is minted and the shared A/A is registered", "touching the resident np4 session by anyone but the coordinator", "any ASR, transcript, encoder or paid-API contact", "re-flying or re-scoring any sealed cell", "--allow-output-change on the re-pin tool", "any change beyond the registered pin"],
        "population": {"count": 1080, "split_identity_hash": arm["split_identity_hash"], "split_role": "discovery", "fold_b_contact_authorized": False, "test_contact_authorized": False},
        "registered_hashes": {key: {"composed_config": ids[key]["composed_config_hash"], "protocol": ids[key]["protocol_hash"]} for key in CELLS},
        "service": {"expected_session_id": SESSION, "model_fragment": arm["model_fragment"], "slots": 4, "slot_tokens": 24576, "no_child_start_stop": True},
    }
    draft_sha = wjson(PACKAGE + "/root-admission-draft-v1.json", draft)
    tables_sha = wjson(PACKAGE + "/conventions-tables-v1.json", {"schema": "saea-slurp-slot-conventions-w4-tables-v1",
                                                                  "source": store["source"], **table})

    fence = json.dumps({"stage3_measurement": measurement}, indent=2, ensure_ascii=False, sort_keys=True)
    readme, prereg = render_docs(args, ids, store, table, token_cost, fold_a, analogue, fit, rule, fence, caps, smoke_caps, fit_statement)
    readme_sha = wr(PACKAGE + "/README.md", readme)
    prereg_sha = wr(PREREG, prereg)

    ledger = "not-requested"
    if args.append_ledger:
        ledger = append_ledger(args, ids, plan_shas, store, estimate, data)
    print(json.dumps({"package": PACKAGE, "ledger": ledger,
                      "written": {"README.md": readme_sha, "registered-facts-v1.json": facts_sha, "protocol": protocol_sha,
                                  "analysis-recipe": recipe_sha, "root-admission-draft": draft_sha, "tables": tables_sha,
                                  "prereg": prereg_sha, **plan_shas},
                      "identity": {key: {"run_id": ids[key]["run_id"], "composed": ids[key]["composed_config_hash"],
                                         "protocol": ids[key]["protocol_hash"]} for key in CELLS},
                      "fit": fit.get("status")}, indent=2))
    return 0


def _fit_lines(fit: dict) -> str:
    if fit.get("status") != "MEASURED_BY_CHECK":
        return "PENDING: core.flight.cli check not yet folded in."
    lines = ["| cell | phase | decision | rendered (4 B/token) | operational margin | physical margin |", "| --- | --- | --- | ---: | ---: | ---: |"]
    for key, cell in fit["cells"].items():
        for p in cell.get("prompt_budget_per_phase", []):
            lines.append(f"| {key} | {p.get('phase')} | {p.get('decision')} | {p.get('rendered_text_tokens')} | {p.get('operational_margin_tokens')} | {p.get('physical_margin_tokens')} |")
    return "\n".join(lines)


def render_docs(args, ids, store, table, token_cost, fold_a, analogue, fit, rule, fence, caps, smoke_caps, fit_statement):
    arm, smoke = ids["arm"], ids["smoke"]
    vocab_lines = ["| type | class | pool mentions | distinct | LOO coverage | N90 | listed | covered |", "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for r in table["vocabulary"]:
        vocab_lines.append(f"| `{r['slot_type']}` | {r['class']} | {r['pool_mentions']} | {r['distinct_values']} | {r['loo_value_coverage']:.3f} | {r['n90']} | {r['listed_values']} | {r['listed_coverage']:.3f} |")
    closed = "; ".join(f"`{r['slot_type']}`: {', '.join(r['closed_value_list'])}" for r in table["vocabulary"] if r["closed_value_list"])
    scope_lines = ["| type | values with evidence | spoken occurrences | tagged / untagged | tagged-when-spoken values (tagged/spoken) | usually-untagged values (tagged/spoken) |", "| --- | ---: | ---: | --- | --- | --- |"]
    for r in table["annotation_scope"]:
        tw = ", ".join(f"{a}/{b}" for a, b in r["tagged_when_spoken_counts"]) or "--"
        uu = ", ".join(f"{a}/{b}" for a, b in r["usually_untagged_counts"]) or "--"
        scope_lines.append(f"| `{r['slot_type']}` | {r['values_with_evidence']} | {r['spoken_occurrences']} | {r['tagged_occurrences']} / {r['untagged_occurrences']} | {tw} | {uu} |")
    span_lines = ["| type | located mentions | rules (edge, word, side, count/cases) |", "| --- | ---: | --- |"]
    for r in table["span_extent"]:
        rules = "; ".join(f"{x['edge']} `{x['word']}` {x['side']} {x['count']}/{x['cases']}" for x in r["rules"]) or "--"
        span_lines.append(f"| `{r['slot_type']}` | {r['located_mentions']} | {rules} |")
    cost_lines = ["| phase | contacts | added tokens mean / max | realised prompt max (AGREE) | projected max |", "| --- | ---: | --- | ---: | ---: |"]
    for phase, p in token_cost["per_phase"].items():
        cost_lines.append(f"| {phase} | {p['contacts']} | {p['added_tokens_mean']} / {p['added_tokens_max']} | {p['realised_prompt_tokens_max']} | {p['projected_prompt_tokens_max']} |")
    items = fold_a["items"]
    exp = analogue["w4_expected_pp"]
    readme = f"""# Cell W4: slot conventions (knowledge wave, owner decision 164)

Registered before contact {args.registered_at[:10]} at study commit `{args.study_commit}`; both cells **held**.
Nothing here authorises a flight, a flip or an admission entry. Development numbers only (owner decisions 28 and 86).

**What W4 is.** The retained AGREE arm (`{COMPARATOR_RUN}`, official SLU-F1 65.16 / intent 85.83 on TRAIN Fold A)
with ONE pin moved: `knowledge_stores.slot-contracts` from the released `slot-contracts-v2` store to
`slot-contracts-w4-v1` (release `{store['release']['sha256']}`, snapshot content `{store['snapshot']['sha256']}`). The new
store is v2 with **{len(store['changed_cards'])} cards extended** ({store['total_added_bytes']:,} bytes in all) by three kinds of slot
convention the 2026-09-27 knowledge content audit found missing (K2 value vocabulary, K3 annotation scope, K4 span
extent), **mined only from the R01-excluded TRAIN exemplar pool** (8,554 utterances; no Fold A, Fold B, DEV or test
byte, no flight output). Every intent binding is byte-identical, so a card still reaches a row only when the row's
candidate intents bind it (W4 composes with W1's card selection), and the facet keys and candidate supply do not move.
Built model-free by `scripts/build_slurp_slot_conventions_w4.py` and `saea-driver prepare-semantic-knowledge`
(registration `{PREP_REGISTRATION}`; contacts model 0 / tool 0 / scorer 0).

**Primary metric.** Official pooled SLU-F1, intent accuracy the guard: owner decision 133 makes intent primary only
for intent-acting mechanisms; W4 acts on slots, so decision 115's shape holds.

**Declared expectation: NO-HARM.** From the measured analogue only (row 139): M4b moved SLU-F1 by +2.55 / +1.54
(first / replicate) over {analogue['m4b_fn_items_on_its_eight_types']} FN items; W4 targets {analogue['w4_fn_items_on_revised_types_with_card_delivered']} FN items with
the card delivered, so the analogue expects **{exp['replicate']} to {exp['first']} pp (mean {exp['mean']})** -- below the
{BENEFIT_FLOOR} pp benefit floor of this design at n = 1,080. The arm is therefore declared `admission` `no-harm`,
`harm_margin_pp` {H_SLU} (SLU) with intent {H_INTENT} the guard, `expected_effect_pp` 0.0, `claims_benefit` false,
`replicate_run_id` `{SHARED_AA_RUN}` (the knowledge wave's shared A/A, registered by the coordinator).

## K2 -- value vocabulary (pool statistics; closed = LOO value coverage >= 0.90; semi-closed = N90 <= 20)

{chr(10).join(vocab_lines)}

Closed value lists (TRAIN annotation values): {closed}. Semi-closed lists live in the store only.

## K3 -- annotation scope (spoken occurrences under the card's intents; tag rate >= 0.85 "tagged when spoken", <= 0.35 "usually left untagged"; >= 5 occurrences)

{chr(10).join(scope_lines)}

## K4 -- span extent (rules at >= 0.80 of >= 8 cases; words limited to function words and generic unit/head words)

{chr(10).join(span_lines)}

## Token cost and Fit

{chr(10).join(cost_lines)}

Per row: +{token_cost['per_row']['added_tokens_mean']} tokens mean (max {token_cost['per_row']['added_tokens_max']}), {token_cost['added_share_of_prompt_volume'] * 100:.2f} % of
the AGREE prompt volume; measured at {token_cost['chars_per_token_measured_on_the_agree_solver']} characters per token on the AGREE
Solver. {token_cost['compaction_projection']}.

{fit_statement}

{_fit_lines(fit)}

## Fold A offline estimate (the AGREE arm, types whose W4 card was delivered; counts)

| class | items |
| --- | ---: |
| K2 omission, gold value in the W4 list or tagged-when-spoken list | {items['K2_omission_gold_value_in_w4_list_or_tagged_when_spoken']} |
| K2 wrong filler, gold listed, prediction not | {items['K2_wrong_filler_gold_listed_prediction_not']} |
| K3 over-emission whose value is usually untagged | {items['K3_over_emission_value_usually_untagged']} |
| K4 containment wrong fillers (all) / fixed by a stated rule | {items['K4_containment_wrong_fillers']} / {items['K4_span_rule_would_fix']} |
| RISK: exact true positives whose value is usually untagged | {items['risk_exact_tp_value_usually_untagged']} |
| RISK: listed value spoken but untagged in gold | {items['risk_listed_value_spoken_but_untagged_in_gold']} |

Rows touched {json.dumps(fold_a['rows_touched'])}; exact span-F1 oracle ceilings (pp) {json.dumps(fold_a['span_f1_oracle_ceilings_pp'])}.

## Files

| file | what it holds |
| --- | --- |
| `../{Path(PREREG).name}` | the preregistration, with the `stage3_measurement` fence |
| `registered-facts-v1.json` | every model-free fact; the CANONICAL `stage3_measurement` |
| `conventions-tables-v1.json` | the K2/K3/K4 tables above (types, counts, closed-type values, schematic rules) |
| `protocol-registered-v1.json` | identities, hashes, the rule |
| `generation-plan-registered-v1.json` / `fit-plan-registered-v1.json` | the arm's plans |
| `smoke-generation-plan-registered-v1.json` / `smoke-fit-plan-registered-v1.json` | the smoke's plans |
| `analysis-recipe-v1.json` | the paired read; `run_ids.read` = `{READ_RUN}` |
| `root-admission-draft-v1.json` | the receipt root mints with `scripts/flights/w4/w4_mint_receipt.py` |

**Sequence.** (1) The coordinator registers the shared A/A `{SHARED_AA_RUN}` and the wave's campaign plan. (2) Root
countersigns the DRAFT rows (four flight rows; the READ row stays draft until the seal), mints `{DECISION_RELPATH}`
with `scripts/flights/w4/w4_mint_receipt.py`. (3) Flip with `scripts/flights/w4/w4_flip.sh` (smoke, then arm; minted
supplies must reproduce the AGREE digests). (4) Queue behind the np4 session (decision 77).

**Budgets.** Arm {caps['generation_calls_cap']:,} generation contacts, {caps['fit_endpoint_calls_cap']:,} FIT endpoints, {caps['repeated_speech_audio_seconds_cap']:,} speech seconds,
{caps['gpu_hours_fit_inclusive']} GPU hours; smoke {smoke_caps['generation_calls_cap']} / {smoke_caps['fit_endpoint_calls_cap']} / {smoke_caps['repeated_speech_audio_seconds_cap']} / {smoke_caps['gpu_hours_fit_inclusive']} -- the AGREE arithmetic.
"""
    prereg = f"""# Cell W4 (slot conventions): preregistration

Registered {args.registered_at[:10]} at study commit `{args.study_commit}`, before any contact, from the retained AGREE
arm fragments by script (decision 58) with one pin moved, under owner decision 164. Development numbers only.

## The cell

| item | value |
| --- | --- |
| base | the retained AGREE arm `{COMPARATOR_RUN}` (65.1575 / 85.8333), owner decision 161 |
| factor | `{THE_PIN}`: slot-contracts-v2 -> slot-contracts-w4-v1 (release `{store['release']['sha256']}`, snapshot content `{store['snapshot']['sha256']}`); {len(store['changed_cards'])} cards extended, intent bindings byte-identical |
| in-chain replicate | `{SHARED_AA_RUN}` (the knowledge wave's shared A/A, registered by the coordinator) |
| primary / guard | official pooled SLU-F1 / intent accuracy (decision 133 scopes intent-primary to intent-acting mechanisms) |
| admission | NO HARM: SLU lower bound >= -{H_SLU}, intent lower bound >= -{H_INTENT} |
| runs | `{arm['run_id']}` / `{arm['fit']['run_id']}`; `{smoke['run_id']}` / `{smoke['fit']['run_id']}`; read `{READ_RUN}` |
| composed config hashes | arm `{arm['composed_config_hash']}`; smoke `{smoke['composed_config_hash']}` |
| protocol hashes | arm `{arm['protocol_hash']}`; smoke `{smoke['protocol_hash']}` |
| split identity | arm `{arm['split_identity_hash']}`; smoke `{smoke['split_identity_hash']}` |

## Decision rule (fixed here)

{rule}

## The measurement declaration

```json
{fence}
```

## Prohibitions

No test-split, Fold B or DEV contact; no re-flying of the comparator; no second factor; no paper-scale profile; no
flight before the receipt is minted, the shared A/A registered and the cells flipped; `--allow-output-change` never passed.
"""
    return readme, prereg


MODEL_TOOL = ("Frozen Q4_K_M decoder-only c98304 np4 max512; promoted EVO-FOLDS-V2 speech packets; NO native tool authority on any role; "
              "prompt bytes the retained AGREE arm's except the slot-contract cards, 19 of which carry TRAIN-mined slot conventions (slot-contracts-w4-v1)")
INHERITED = ("TRAIN Fold A discovery rows already exposed by the sealed anchors and every Stage-2/3 Fold A cell (B-series, PLAN, PLANr, ROLL-2, CONV, "
             "the AGREE family, KPROBE, COMP-1, G5, flown or in flight at registration); this cell adds no new row to the fold and opens no split. Prior exposure is inherited in full.")


def append_ledger(args, ids, plan_shas, store, estimate, data) -> str:
    text = rd(LEDGER)
    eligible = [ids["arm"]["run_id"], ids["arm"]["fit"]["run_id"], ids["smoke"]["run_id"], ids["smoke"]["fit"]["run_id"]]

    def flight_notes(key: str, kind: str) -> str:
        identity = ids[key]
        run_id = identity["fit"]["run_id"] if kind == "fit" else identity["run_id"]
        attempt = identity["fit"]["attempt_id"] if kind == "fit" else identity["attempt_id"]
        declaration = (f"admission no-harm, harm_margin_pp {H_SLU} (SLU primary; intent guard {H_INTENT}), claims_benefit false, expected_effect_pp 0.0, "
                       f"measurement_design cross-flight-with-in-chain-replicate, replicate_run_id {SHARED_AA_RUN}, rows 1080"
                       if key == "arm" else "measurement_design form-proof, claims_benefit false, expected_effect_pp 0.0, rows 4")
        return (
            f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) {args.registered_at[:10]} at study commit {args.study_commit} by the W4 "
            f"registration agent (worktree {args.worktree}, branch {args.branch}). This registration performs no contact and authorises none. Plan SHA256 "
            f"{plan_shas[run_id]}; attempt {attempt}. Protocol hash {identity['protocol_hash']}; composed config {identity['composed_config_hash']}; expected "
            f"session {SESSION} (attach only). READINESS HELD: root mints {DECISION_RELPATH} (decision id {DECISION_ID}) with the four eligible run ids "
            f"{', '.join(eligible)}, the coordinator registers the shared A/A {SHARED_AA_RUN}, then scripts/flights/w4/w4_flip.sh re-pins with "
            f"scripts/flights/repin_cell.py --set-ready, minting each cell's own first-phase supply (item E16; expected output digest "
            f"{AGREE_SUPPLY_OUTPUT[key]}, the AGREE {key}'s); --allow-output-change must never be passed. Every hash in this row moves at the flip. ONE PIN "
            f"(owner decision 164): {THE_PIN} slot-contracts-v2 -> slot-contracts-w4-v1 (release {store['release']['sha256']}, snapshot content "
            f"{store['snapshot']['sha256']}), {len(store['changed_cards'])} cards extended with TRAIN-mined slot conventions from the R01-excluded exemplar pool. "
            f"Measurement declaration ({GATE}): {declaration} -- canonical in {PACKAGE}/registered-facts-v1.json. Caps are the AGREE arithmetic. Stop and "
            f"preserve on the first failure; AT MOST ONE root-diagnosed recovery re-registration. No test-split, Fold B or DEV contact, no comparator re-flight."
        )

    def flight_row(key: str, kind: str) -> str:
        identity = ids[key]
        budget = identity["family_budget"]
        run_id = identity["fit"]["run_id"] if kind == "fit" else identity["run_id"]
        scope = (("Cell W4 (slot conventions)" if key == "arm" else "Four-row form smoke of cell W4") + (" -- FIT spend identity, request envelopes only, no generation" if kind == "fit" else "")
                 + ": the retained AGREE arm with the slot-contract cards extended by TRAIN-mined slot conventions" + (", read on no harm against the knowledge wave's shared in-chain A/A" if key == "arm" else ", structural form only, never scored"))
        cells = ["", args.registered_at, run_id, "bounded-discovery-probe", scope, MODEL_TOOL, f"slurp TRAIN Fold A {identity['rows']}", "discovery",
                 identity["split_identity_hash"], "no", str(budget["fit_endpoint_calls_cap"] if kind == "fit" else budget["generation_calls_cap"]),
                 str(budget["repeated_speech_audio_seconds_cap"]), str(budget["gpu_hours_fit_inclusive"]), INHERITED,
                 f"{PACKAGE}/{PREFIX[key]}{kind}-plan-registered-v1.json", flight_notes(key, kind), ""]
        return " | ".join(cells).strip()

    read_row = " | ".join(["", args.registered_at[:10], READ_RUN, "model-free-check",
        f"The paired read of cell W4 against the knowledge wave's shared in-chain A/A {SHARED_AA_RUN} (SLU-F1 primary, intent guard), the sealed AGREE arm beside it, by the recipe {PACKAGE}/analysis-recipe-v1.json. Zero model, server, encoder, embedder, tokenizer and GPU contacts; one official score per arm is the flights' own.",
        "no model or tool contact; read of sealed bytes only", "slurp TRAIN Fold A 1080, sealed W4 arm and shared A/A (after the seal)", "discovery",
        ids["arm"]["split_identity_hash"], "no", "0", "0", "0", "No new speech exposure; reads sealed outputs and official scores only. Prior exposure inherited in full.",
        f"{PACKAGE}/analysis-recipe-v1.json",
        f"REGISTERED WITH THE FLIGHT (DRAFT, root countersignature pending; countersigned after the seal and before any number is read) {args.registered_at[:10]} at study commit {args.study_commit}. Recipe slurp-stage3-w4-fold-a-paired-analysis-v1; output analysis/{READ_RUN}. It admits nothing beyond the no-harm entry it is registered for.",
        ""]).strip()
    build_row = " | ".join(["", args.registered_at[:10], BUILD_ROW, "model-free-check",
        "Build the W4 slot conventions (K2 value vocabulary, K3 annotation scope, K4 span extent) from the R01-excluded TRAIN exemplar pool, append them to 19 existing slot-contract cards, freeze the permitted construction roster, and release slot-contracts-w4-v1 with saea-driver prepare-semantic-knowledge. Zero model, tokenizer, encoder, embedder, scorer, server, network and GPU contacts.",
        "no model or tool contact; local JSON reads of the pinned pool snapshot and the v2 authored source", "slurp TRAIN construction pool (R01-excluded, 8,554 utterances); no Fold A, Fold B, DEV or test byte", "discovery",
        store["exact_support_roster"]["split_identity_hash"], "no", "0", "0", "0", "No speech exposure: text annotations of the construction pool only (already the knowledge source of the flown exemplar store).",
        f"{PREP}/receipt.json",
        f"MODEL-FREE BUILD, RUN BEFORE THIS ROW WAS WRITTEN (disclosed; DRAFT, root countersignature pending) {args.registered_at[:10]} by the W4 registration agent; script {BUILD_SCRIPT}; build receipt sha256 {store['build_receipt_sha256']}; authored source {store['authored_source']['sha256']}; permitted roster {store['permitted_roster']['sha256']} ({store['exact_support_roster']['sample_count']} recordings); release {store['release']['sha256']}; snapshot content {store['snapshot']['sha256']}; completion contacts model 0 tool 0 scorer 0. It authorises nothing.",
        ""]).strip()
    estimate_row = " | ".join(["", args.registered_at[:10], ESTIMATE_ROW, "model-free-check",
        "Offline Fold A estimate for cell W4: on the sealed AGREE arm, count the error items the W4 conventions could touch (K2 listed-value omissions and wrong fillers, K3 usually-untagged over-emissions, K4 span-rule fixes) and the risk items, only for types whose card the row was delivered; measure the per-contact and per-row token cost from the sealed trace; derive the M4b analogue. Gold read offline, counts only. Zero model, server, tokenizer, encoder, embedder, scorer and GPU contacts.",
        "no model or tool contact; read-only sealed AGREE outputs, score, phase summary and trace; governed train gold offline", "slurp TRAIN Fold A 1080 (sealed AGREE arm, ids and counts only)", "discovery",
        ids["arm"]["split_identity_hash"], "no", "0", "0", "0", "No new speech exposure: sealed bytes already exposed by the AGREE arm. Prior exposure inherited in full.",
        ESTIMATE,
        f"MODEL-FREE READ OF SEALED BYTES, RUN BEFORE THIS ROW WAS WRITTEN (disclosed; DRAFT, root countersignature pending) {args.registered_at[:10]}; script {ESTIMATE_SCRIPT}; output sha256 {sha_file(data / ESTIMATE)}. Development numbers (owner decisions 28 and 86); it authorises nothing.",
        ""]).strip()

    fresh = {}
    for key in CELLS:
        for kind in ("generation", "fit"):
            run_id = ids[key]["fit"]["run_id"] if kind == "fit" else ids[key]["run_id"]
            fresh[run_id] = flight_row(key, kind)
    fresh[READ_RUN] = read_row
    fresh[BUILD_ROW] = build_row
    fresh[ESTIMATE_ROW] = estimate_row
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
        raise SystemExit("the ledger carries some but not all W4 rows; refusing to guess")
    if replaced:
        wr(LEDGER, "\n".join(lines))
        return f"replaced-{replaced}"
    header = ("\n## Cell W4: slot conventions (knowledge wave, owner decision 164) -- the arm, its four-row smoke, the READ row, the model-free "
              "build and the offline estimate (DRAFT, root countersignature pending)\n\nFour unconsumed flight rows, one READ row registered with the "
              "flight, and two model-free rows. The in-chain A/A is the knowledge wave's shared one, registered by the coordinator. None of these rows "
              "is countersigned and none authorises a contact.\n\n"
              "| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | split role | split identity hash | consumed | calls | speech audio seconds | gpu hours | inherited exposure | artifacts | notes |\n"
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")
    suffix = "" if text.endswith("\n") else "\n"
    wr(LEDGER, text + suffix + header + "\n".join(fresh[r] for r in order) + "\n")
    return "appended"


if __name__ == "__main__":
    raise SystemExit(main())
