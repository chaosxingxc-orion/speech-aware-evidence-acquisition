#!/usr/bin/env python3
"""Write cell COMP-1's registration package -- the FIRST COMPOSED Stage-3 arm
(owner decisions 138 and 152) -- from the committed configs.

Reads the three derived fragments, recomposes every hash, PROVES from the composed
configs that the arm differs from the locked PLAN cell by exactly the three
composed factors plus per-flight bookkeeping (and the A/A by the recall width
plus bookkeeping, and the arm from the A/A by the three factors alone), reads the
three prepared first-phase supplies this registration minted (the A/A's output
digest must be the sealed comparator's ``ba5e1faa...``), reads the model-free
attribution-class derivation, and writes the package documents, six plan
documents, the analysis recipe with the per-class attribution table, a draft
decision receipt for root, the README, the preregistration and (with
``--append-ledger``) the seven exposure rows.

THE EXPECTATION IS NOT DECLARED HERE. ``stage3_measurement[<arm run id>]
.expected_effect_pp`` is written as the literal string
``TO-BE-DECLARED-BY-COORDINATOR-FROM-AGREE-AND-KPROBE-READS`` in both places the
gate reads (``registered-facts-v1.json`` and the preregistration fence), because
owner decision 139 forbids a prior and decision 152 says the number is composed
from the AGREE and KPROBE reads' measured m values. ``scripts/checks/
stage3_effect_floor_check.py`` refuses the arm as ``unparsable-declaration`` until
the coordinator replaces the string with a number in both places; that refusal is
the intended state of this package.

Config and receipt-pinned bytes alone: no adapter contact, no server, no lock, no
model, tokenizer, encoder, embedder or scorer contact; it flips nothing and mints
nothing. ``--check-dir`` folds the per-phase prompt-budget receipts of an
already-run ``core.flight.cli check`` (model-free; it attaches to nothing) into
the facts so the fit is recorded from the runtime's own measurement.

    python scripts/flights/comp1/write_slurp_comp1_registration.py \\
        --package-dir docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1 \\
        --data-root "$SPEECHRL_DATA_DIR" --study-commit <sha> \\
        --registered-at 2026-09-27T12:00:00.000000+00:00 [--check-dir <dir>] [--append-ledger]
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash  # noqa: E402

PARENT_EXPERIMENT = "slurp-native-default-plan-lock-v1"
PARENT_SMOKE_EXPERIMENT = "slurp-native-default-plan-lock-smoke-4-v1"
COMPARATOR_RUN = "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1"
COMPARATOR_ATTEMPT = "attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1"
COMPARATOR_OFFICIAL = {"slu_f1": 63.6304, "intent_accuracy": 82.2222}
SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"
PLAN_SUPPLY_OUTPUT_SHA = "ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f"
PLACEHOLDER = "TO-BE-DECLARED-BY-COORDINATOR-FROM-AGREE-AND-KPROBE-READS"

CELLS = {
    "arm": "slurp-native-stage3-comp1-fold-a-v1",
    "aa": "slurp-native-stage3-comp1-aa-fold-a-v1",
    "smoke": "slurp-native-stage3-comp1-fold-a-smoke-4-v1",
}
PACKAGE_NAME = "slurp-stage3-comp1-fold-a-v1"
DECISION_ID = "slurp-stage3-comp1-fold-a-admission-v1"
DECISION_RELPATH = f"coordination/{PACKAGE_NAME}/root-admission-v1.json"
CAMPAIGN_PLAN = "configs/campaign/slurp-native-stage3-comp1-fold-a-v1.json"

AGREE_PACKAGE = "docs/readiness/2026-09-26-slurp-stage3-agree-w1-fold-a-v1"
KPROBE_PACKAGE = "docs/readiness/2026-09-27-slurp-stage3-kprobe-fold-a-55-v1"
CONV_READ = "docs/results/2026-09-27-slurp-conv-probe-read.md"
INSTRUMENT = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"
BAD_CASE_BANK_DOC = "docs/results/2026-09-24-slurp-plan-bad-case-bank.md"
OWNER_DECISIONS = "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md"
RANK_DIAGNOSTIC = "docs/results/2026-09-26-slurp-intent-retrieval-rank-diagnostic.md"
KEY_DIAGNOSTIC = "docs/results/2026-09-27-slurp-boundary-key-construction-diagnostic.md"
CITATION_MODULE = "src/speech_aware_evidence_acquisition/rails/solver_citation.py"
CITATION_COST_SCRIPT = "scripts/analysis/solver_citation_cost.py"
CREDIT_MODULE = "src/speech_aware_evidence_acquisition/analysis/citation_credit.py"
CONFIG_TEST = "tests/unit/test_comp1_config.py"
DERIVE_SCRIPT = "scripts/flights/comp1/derive_slurp_comp1_cells.py"
CLASSES_SCRIPT = "scripts/flights/comp1/comp1_attribution_classes.py"
CLASSES_ROW = "SAEA-SLURP-STAGE3-COMP1-ATTRIBUTION-CLASSES-V1"
LEDGER = "docs/exposure-ledger.md"

HEADROOM_INTENT = 12.04 / 130.0
HEADROOM_SLU = 5.41 / 130.0
OWN_NULL = {"h_slu": 1.2485, "h_intent": 0.9943, "n": 1080}
BAR_PP = 2.5

BOUNDARY = "knowledge_stores.intent-boundaries.phase_supply.perception"
FACTOR_PATHS = {
    "factor_1_agreement_term": (
        f"{BOUNDARY}.rank_weights.w_agree",
        f"{BOUNDARY}.agreement_source.",
    ),
    "factor_2_centroid_key": (f"{BOUNDARY}.facet_source.",),
    "factor_3_citation_contract": (
        "policy",
        "phase_material.solver.instruction_template",
        "phase_material.solver.response_format_id",
        "native_episode.deliver_normaliser.normaliser",
    ),
}
RECALL_WIDTH_PATH = f"{BOUNDARY}.k"
BOOKKEEPING_PREFIXES = ("native_contact_fit.", "prepared_phase_supply", "preparation_source_receipts", "what_this_is")


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


def classify_diff(parent_values: dict, mine: dict, experiment_keys: set, baseline_keys: set, *, allowed: tuple[str, ...]) -> dict:
    overlap = sorted(experiment_keys & baseline_keys)
    if overlap:
        raise SystemExit(f"the experiment fragment overrides baseline keys: {overlap}")
    a, b = flatten(parent_values), flatten(mine)
    changed = sorted(k for k in set(a) | set(b) if a.get(k, "<absent>") != b.get(k, "<absent>"))

    def matches(key: str, path: str) -> bool:
        return key == path or (path.endswith(".") and key.startswith(path))

    factor = [k for k in changed if any(matches(k, p) for p in allowed)]
    bookkeeping = [k for k in changed if k not in factor and k.startswith(BOOKKEEPING_PREFIXES)]
    experiment_block = [k for k in changed if k not in factor and k not in bookkeeping and k.split(".", 1)[0] in experiment_keys]
    other = [k for k in changed if k not in factor and k not in bookkeeping and k not in experiment_block]
    return {"factor_paths": factor, "bookkeeping": bookkeeping, "experiment_fragment_own_block": experiment_block, "anything_else": other}


def composed_of(experiment: str):
    document = json.loads(rd(f"configs/experiment/{experiment}.json"))
    cell = document["cells"][0]
    composed = compose(REPO_ROOT, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], experiment)
    return document, cell, composed


def supply_facts(data_root: Path, relpath: str) -> dict:
    path = data_root / relpath
    document = json.loads(path.read_text(encoding="utf-8"))
    values = document["output"]["values"]
    rows = {sid: ids for phase in values.values() for sid, ids in phase.items()}
    return {
        "relpath": relpath,
        "file_sha256": sha_file(str(path)),
        "output_sha256": document["output_sha256"],
        "kind": document["kind"],
        "contact_class": document["contact_class"],
        "rows_seeded": len(rows),
        "selected_value_ids": sum(len(ids) for ids in rows.values()),
        "width_histogram": {str(k): v for k, v in sorted(Counter(len(ids) for ids in rows.values()).items())},
        "supply_spec_rank_weights": document["inputs"]["sources"]["supply_spec"].get("rank_weights"),
        "supply_spec_facet_source_sha256": document["inputs"]["sources"]["supply_spec"]["facet_source"]["sha256"],
        "supply_spec_declares_agreement_source": "agreement_source" in document["inputs"]["sources"]["supply_spec"],
        "implementation": document["inputs"]["sources"]["implementation"],
    }


def fold_check(check_dir: str | None, cells: dict) -> dict:
    """The per-phase prompt-budget receipts of ``core.flight.cli check`` for each
    cell, if the coordinator has run it; otherwise the pending marker."""

    if not check_dir:
        return {"status": "PENDING_CHECK", "note": "run core.flight.cli check on the three cells after the exposure rows exist and re-run this writer with --check-dir"}
    out = {"status": "MEASURED_BY_CHECK", "cells": {}}
    for key, cell_id in cells.items():
        path = Path(check_dir) / f"check-{cell_id}.json"
        if not path.is_file():
            out["cells"][key] = {"status": "MISSING", "path": str(path)}
            continue
        report = json.loads(path.read_text(encoding="utf-8"))
        preflight = report.get("preflight") or {}
        phases = []
        for receipt in preflight.get("prompt_budget") or ():
            entry = {"phase": receipt.get("phase"), "decision": receipt.get("decision")}
            for name in ("physical_margin_tokens", "operational_margin_tokens", "serving_slot_limit_tokens", "operational_limit_tokens"):
                if name in receipt:
                    entry[name] = receipt[name]
            breakdown = receipt.get("breakdown") if isinstance(receipt.get("breakdown"), dict) else {}
            for name in ("rendered_text_tokens", "required_window_tokens", "completion_token_ceiling", "speech_feature_tokens"):
                if name in breakdown:
                    entry[name] = breakdown[name]
                elif name in receipt:
                    entry[name] = receipt[name]
            payload = receipt.get("payload_sha256") or receipt.get("input_sha256")
            if isinstance(payload, str):
                entry["payload_sha256_prefix"] = payload[:16]
            phases.append(entry)
        out["cells"][key] = {
            "check_path": str(path),
            "scientific_readiness": report.get("scientific_readiness"),
            "blockers": report.get("blockers"),
            "config_hash": preflight.get("config_hash"),
            "protocol_hash": preflight.get("protocol_hash"),
            "prompt_budget_per_phase": phases,
        }
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--package-dir", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--study-commit", required=True)
    parser.add_argument("--registered-at", required=True)
    parser.add_argument("--branch", default="fable/comp1")
    parser.add_argument("--worktree", default="/home/chao/saea-worktrees/fable-comp1")
    parser.add_argument("--check-dir", default=None)
    parser.add_argument("--append-ledger", action="store_true")
    args = parser.parse_args(argv)
    os.chdir(REPO_ROOT)
    package = args.package_dir.rstrip("/").replace("\\", "/")
    prereg = package + "-preregistration.md"
    data_root = Path(args.data_root).resolve()

    # ---- identities ------------------------------------------------------
    ids: dict[str, dict] = {}
    composed: dict[str, object] = {}
    documents: dict[str, dict] = {}
    for key, experiment in CELLS.items():
        document, cell, comp = composed_of(experiment)
        documents[key] = document
        composed[key] = comp
        split = document["population"]["split_identity_hash"]
        fit = comp.values["native_contact_fit"]
        own_supply = next(r for r in cell["readiness"]["requirements"] if r["relpath"].endswith("phase-supply-v1.json"))
        ids[key] = {
            "cell": cell["cell_id"], "experiment": experiment, "run_id": cell["run_id"], "attempt_id": cell["attempt_id"],
            "fit_run_id": fit["run_id"], "fit_attempt_id": fit["attempt_id"], "fit_contact_cap": fit["contact_cap"],
            "baseline_fragment": cell["baseline_fragment"], "dataset_fragment": cell["dataset_fragment"], "model_fragment": cell["model_fragment"],
            "arm": comp.values["arm"], "rows": document["population"]["count"], "split_identity_hash": split,
            "composed_config_hash": comp.config_hash, "protocol_hash": protocol_hash(comp.config_hash, comp.values["arm"], split),
            "family_budget": document["family_budget"], "execution_plan": document["execution_plan"],
            "readiness_state": cell["readiness"]["state"],
            "own_supply_requirement": own_supply,
            "boundary": {k: comp.values["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"].get(k) for k in ("k", "tau", "rank_weights", "fuse_coverage")},
            "boundary_facet_source_sha256": comp.values["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]["facet_source"]["sha256"],
            "declares_agreement_source": "agreement_source" in comp.values["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"],
            "policy": comp.values["policy"],
            "solver_material": comp.values["phase_material"]["solver"],
            "deliver_normaliser": comp.values["native_episode"]["deliver_normaliser"],
            "stage3_algorithm": document["stage3_algorithm"],
        }
    for key in CELLS:
        if ids[key]["readiness_state"] != "held":
            raise SystemExit(f"{key} is not held")

    # ---- the composed-config proofs -------------------------------------
    parent_doc, parent_cell, parent = composed_of(PARENT_EXPERIMENT)
    smoke_parent_doc, smoke_parent_cell, smoke_parent = composed_of(PARENT_SMOKE_EXPERIMENT)
    baseline_keys = set(json.loads(rd(f"configs/baseline/{parent_cell['baseline_fragment']}.json")))
    all_factor_paths = tuple(p for paths in FACTOR_PATHS.values() for p in paths)
    diffs = {
        "arm_vs_locked_plan": classify_diff(parent.values, composed["arm"].values, set(documents["arm"]) | set(parent_doc), baseline_keys, allowed=all_factor_paths + (RECALL_WIDTH_PATH,)),
        "aa_vs_locked_plan": classify_diff(parent.values, composed["aa"].values, set(documents["aa"]) | set(parent_doc), baseline_keys, allowed=(RECALL_WIDTH_PATH,)),
        "arm_vs_aa": classify_diff(composed["aa"].values, composed["arm"].values, set(documents["arm"]) | set(documents["aa"]), baseline_keys, allowed=all_factor_paths),
        "smoke_vs_locked_plan_smoke": classify_diff(smoke_parent.values, composed["smoke"].values, set(documents["smoke"]) | set(smoke_parent_doc), baseline_keys, allowed=all_factor_paths + (RECALL_WIDTH_PATH,)),
    }
    for name, diff in diffs.items():
        if diff["anything_else"]:
            raise SystemExit(f"{name}: the composed config differs beyond the registered factors and bookkeeping: {diff['anything_else']}")
    for factor, paths in FACTOR_PATHS.items():
        for path in paths:
            hit = [k for k in diffs["arm_vs_aa"]["factor_paths"] if k == path or (path.endswith(".") and k.startswith(path))]
            if not hit:
                raise SystemExit(f"{factor}: {path} did not move between the A/A and the arm")
    if RECALL_WIDTH_PATH not in diffs["aa_vs_locked_plan"]["factor_paths"] or len(diffs["aa_vs_locked_plan"]["factor_paths"]) != 1:
        raise SystemExit("the A/A must differ from the locked plan by the recall width alone (plus bookkeeping)")
    if RECALL_WIDTH_PATH in diffs["arm_vs_aa"]["factor_paths"]:
        raise SystemExit("the arm and the A/A must share the recall width")
    arm_p = composed["arm"].values["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
    agree_p = json.loads(rd("configs/baseline/slurp-native-stage3-agree-w1-fold-a-baseline-v1.json"))["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
    kprobe_p = json.loads(rd("configs/baseline/slurp-native-stage3-kprobe-fold-a-55-baseline-v1.json"))["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
    if arm_p["agreement_source"] != agree_p["agreement_source"] or arm_p["rank_weights"] != agree_p["rank_weights"] or arm_p["k"] != agree_p["k"]:
        raise SystemExit("the arm's agreement term is not the AGREE arm's, byte for byte")
    if arm_p["facet_source"] != kprobe_p["facet_source"]:
        raise SystemExit("the arm's boundary key is not KPROBE's pin, byte for byte")
    if arm_p["fuse_coverage"] != {"m": 8, "c": 1, "top_l": 8} or arm_p["tau"] != 0.0:
        raise SystemExit("the arm's delivered width or tau moved")
    arm_receipts = {r["relpath"]: r for r in composed["arm"].values["preparation_source_receipts"]}
    parent_receipts = {r["relpath"]: r for r in parent.values["preparation_source_receipts"]}
    added = sorted(set(arm_receipts) - set(parent_receipts))
    if set(parent_receipts) - set(arm_receipts) or any(arm_receipts[k] != parent_receipts[k] for k in parent_receipts) or len(added) != 2:
        raise SystemExit("preparation_source_receipts is not the parent's list plus the two factor receipts")

    # ---- the prepared supplies and the byte identity ---------------------
    supplies = {key: supply_facts(data_root, ids[key]["own_supply_requirement"]["relpath"]) for key in CELLS}
    for key in CELLS:
        if supplies[key]["file_sha256"] != ids[key]["own_supply_requirement"]["sha256"]:
            raise SystemExit(f"{key}: the committed supply requirement does not hash to the artifact on the data root")
    if supplies["aa"]["output_sha256"] != PLAN_SUPPLY_OUTPUT_SHA:
        raise SystemExit("the A/A's prepared output digest is not the sealed comparator's ba5e1faa...")
    if supplies["aa"]["rows_seeded"] != 1080 or supplies["aa"]["selected_value_ids"] != 8624:
        raise SystemExit("the A/A's prepared supply is not 1,080 rows / 8,624 ids")
    if supplies["arm"]["output_sha256"] == PLAN_SUPPLY_OUTPUT_SHA:
        raise SystemExit("the composed arm's prepared output digest equals the default's; the composition is inert")

    # ---- the attribution classes -----------------------------------------
    classes_relpath = package + "/attribution-classes-v1.json"
    classes = json.loads(rd(classes_relpath))
    if classes["inputs"]["arm_supply"]["sha256"] != supplies["arm"]["file_sha256"] or classes["inputs"]["aa_supply"]["sha256"] != supplies["aa"]["file_sha256"]:
        raise SystemExit("the attribution classes were derived from other prepared supplies; re-run comp1_attribution_classes.py")
    summary = classes["summary"]
    class_counts = {k: {kk: vv for kk, vv in v.items() if kk not in ("ids", "outcome_under_comp1")} for k, v in classes["classes"].items()}
    unseeded = classes["rows_seeded_with_no_boundary_entry_under_comp1"]

    fit = fold_check(args.check_dir, CELLS)
    caps = ids["arm"]["family_budget"]
    smoke_caps = ids["smoke"]["family_budget"]

    measurement = {
        ids["arm"]["run_id"]: {
            "claims_benefit": True,
            "expected_effect_pp": PLACEHOLDER,
            "measurement_design": "cross-flight-with-in-chain-replicate",
            "primary_metric": "intent accuracy (scenario_action exact), official pooled SLU-F1 the non-inferiority guard (owner decision 133)",
            "replicate_run_id": ids["aa"]["run_id"],
            "rows": 1080,
            "note": (
                "The FIRST COMPOSED arm (owner decisions 138 and 152): the locked plan + the agreement term "
                "+ the centroid boundary key + the citation contract, read against the in-chain A/A at intent "
                "primary and official SLU-F1 as the guard. expected_effect_pp is DELIBERATELY the literal string "
                + PLACEHOLDER
                + ": owner decision 139 forbids a prior, and decision 152 says the number is composed by the "
                "coordinator from the AGREE and KPROBE reads' measured m values (m_agree = 32 of 70 is read; "
                "m_kprobe is pending) over the class table registered here (the two newly-delivered sets overlap "
                "on 47 of their 78 rows, so they do not add) at the registered per-row headroom of 0.092615 pp "
                "intent. Until the coordinator replaces this string with a number here AND in the "
                "preregistration fence, scripts/checks/stage3_effect_floor_check.py refuses this cell as "
                "unparsable-declaration -- the intended state. A composed round that fails to improve is read as "
                "a CONFLICT DIAGNOSIS over the per-class attribution table, never as a null (decision 138). "
                "Delivery is not correctness."
            ),
        },
        ids["aa"]["run_id"]: {
            "claims_benefit": False,
            "expected_effect_pp": 0.0,
            "measurement_design": "cross-flight-with-in-chain-replicate",
            "primary_metric": "intent accuracy (scenario_action exact), official pooled SLU-F1 the guard",
            "replicate_run_id": ids["arm"]["run_id"],
            "rows": 1080,
            "note": (
                "The A/A replicate is the INSTRUMENT, not a claim: it re-flies the locked plan's own bytes "
                "(w_agree 0.0, the written key, the un-armed citation default, recall k 60 which is a proven "
                "no-op) so the composed delta is read against a within-chain null. Its expected effect is "
                "exactly zero by construction; a non-zero read on it is a measurement of the instrument."
            ),
        },
        ids["smoke"]["run_id"]: {
            "claims_benefit": False,
            "expected_effect_pp": 0.0,
            "measurement_design": "form-proof",
            "primary_metric": "intent accuracy (scenario_action exact)",
            "rows": 4,
            "note": (
                "Four rows prove FORM and nothing else: the agreement table and the centroid key file load and "
                "hash-verify, the boundary channel still delivers, the Solver answers under the cited-answer "
                "contract and the unwrapping normaliser delivers the answer's own bytes, every request fits and "
                "the episode completes. Scored by no one, read by no one; under the instrument's rule 5 a "
                "batch of four rows can never be evidence of benefit."
            ),
        },
    }

    where_to_fill = [
        {"file": package + "/registered-facts-v1.json", "json_path": f"stage3_measurement.{ids['arm']['run_id']}.expected_effect_pp", "currently": PLACEHOLDER},
        {"file": prereg, "location": f"the fenced json block under '## The measurement declaration', key stage3_measurement.{ids['arm']['run_id']}.expected_effect_pp", "currently": PLACEHOLDER},
    ]

    facts = {
        "schema": "saea-registered-facts-v1",
        "_note": (
            "Every model-free measured fact this registration rests on, and the CANONICAL stage3_measurement "
            "block scripts/checks/stage3_effect_floor_check.py resolves. The same block is repeated in the "
            "preregistration's fenced json for readability; this copy has precedence. The arm's "
            "expected_effect_pp is a placeholder string BY DESIGN (see the_expectation_the_coordinator_declares)."
        ),
        "registered_at_utc": args.registered_at,
        "study_commit_at_registration": args.study_commit,
        "owner_decisions": {"138": "the composed round is the cumulative check; no improvement = conflict diagnosis with the per-class table", "152": "COMP-1 = PLAN lock + agreement term + centroid key + citation contract; expectation composed from the AGREE and KPROBE reads", "133": "intent primary, official SLU-F1 the guard", "139": "no prior, no pre-committed if-then", "127": "the citation part is a no-harm base item"},
        "rows": 1080,
        "stage3_measurement": measurement,
        "the_expectation_the_coordinator_declares": {
            "placeholder": PLACEHOLDER,
            "where_to_fill": where_to_fill,
            "gate_state_until_then": "scripts/checks/stage3_effect_floor_check.py: FAIL [unparsable-declaration] on the arm (expected_effect_pp must be a number) -- INTENDED; the A/A and the smoke parse.",
            "what_composes_it": {
                "m_agree": {"value": "32 of 70", "rate": 0.4571, "source": CONV_READ, "status": "read"},
                "m_kprobe": {"value": "pending", "source": KPROBE_PACKAGE + " (its read, once sealed)", "status": "pending"},
                "per_row_headroom_pp_intent": round(HEADROOM_INTENT, 6),
                "per_row_headroom_pp_slu_guard": round(HEADROOM_SLU, 6),
                "the_two_newly_delivered_sets_overlap": {
                    "newly_by_agree_only": class_counts["newly-by-agree"]["rows"],
                    "newly_by_centroid_only": class_counts["newly-by-centroid"]["rows"],
                    "newly_by_both": class_counts["newly-by-both"]["rows"],
                    "union": summary["union_of_the_two_newly_delivered_sets"],
                    "catch_all_delivered_only_under_the_composition": len(summary["catch_all_rows_delivered_only_under_the_composition"]),
                    "rows_a_single_factor_or_the_plan_delivers_but_the_composition_does_not": len(summary["rows_delivered_by_plan_or_a_single_factor_but_not_under_comp1"]),
                    "note": "the two conversion probes measured m on DISJOINT-looking rosters that in fact share 47 rows, so m_agree x headroom + m_kprobe x headroom double-counts; the coordinator composes over the four exclusive classes registered in attribution-classes-v1.json",
                },
                "bar_at_n_1080_pp": BAR_PP,
                "rule": "declared from measured m values only (decision 139); never a midpoint, never a prior; the citation part contributes no expected gain (a no-harm base item, decision 152)",
            },
        },
        "cells": {key: {k: v for k, v in ids[key].items() if k not in ("own_supply_requirement", "family_budget", "execution_plan", "solver_material")} for key in CELLS},
        "the_composition": {
            "factor_1_agreement_term": {
                "as_registered_by": AGREE_PACKAGE,
                "rank_weights": arm_p["rank_weights"], "k": arm_p["k"], "fuse_coverage": arm_p["fuse_coverage"], "tau": arm_p["tau"],
                "agreement_source": arm_p["agreement_source"],
                "agreement_receipt": arm_receipts["prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-A-V1/receipt.json"],
                "measured_alone": "wrong-row delivery 45.0 % -> 81.7 % on Fold A; CONV: m = 32 of 70 newly delivered rows converted (45.71 %, Wilson [34.57, 57.30])",
            },
            "factor_2_centroid_key": {
                "as_registered_by": KPROBE_PACKAGE,
                "facet_source": arm_p["facet_source"],
                "centroid_receipt": arm_receipts["prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/receipt.json"],
                "measured_alone": "wrong-row delivery 45.0 % -> 71.2 % on Fold A at zero token cost; KPROBE (55 rows) reads its conversion; the 211 committed configs are NOT re-pinned",
            },
            "factor_3_citation_contract": {
                "policy": ids["arm"]["policy"],
                "solver_response_format_id": ids["arm"]["solver_material"]["response_format_id"],
                "solver_instruction_template": ids["arm"]["solver_material"]["instruction_template"],
                "deliver_normaliser": ids["arm"]["deliver_normaliser"],
                "module": CITATION_MODULE,
                "one_arming": "rails.native_episode_config refuses the contract without one of the two unwrapping normalisers and a normaliser without the contract, fail-closed, before any contact",
                "delivered_text": "the answer object's OWN bytes cut from the envelope by rails.solver_citation.answer_span, then the locked plan's v3 projection (invariant I7n); a citation of an unsupplied id is refused at the seal, never dropped",
                "byte_identical_default": "un-armed (every fragment before this seam, the v2.0 lock and this A/A included) no function of the module is reachable; the AGREE identity proof and this A/A both reproduce the sealed prepared-output digest " + PLAN_SUPPLY_OUTPUT_SHA,
                "token_cost_measured_on_the_sealed_plan_trace": {
                    "source": f"{CITATION_COST_SCRIPT} over the sealed PLAN trace's 625 Solver contacts with the local tokenizer (zero model contacts), recorded in owner decision 152 ({OWNER_DECISIONS})",
                    "instruction_tokens_per_solver_contact": 134,
                    "output_envelope_skeleton_tokens": 26,
                    "output_tokens_per_cited_id": 12.71,
                    "contract_cap_ids": "3 intent + 6 entities x 3 = 21 ids, about 353 output tokens at the cap, inside the 512-token completion ceiling",
                    "contacts": "unchanged: the contract adds tokens per Solver contact, never contacts, so every cap is the PLAN family's own",
                },
                "admission_mode": "a row-127 no-harm base item folded into the composed arm (decision 152): it is admitted on the composed arm's own guards and may never be reported as a gain; its deliverable is the per-entry credit table (" + CREDIT_MODULE + ", saea-citation-credit-table-v1)",
            },
            "nothing_else": "proven below from the composed configs and re-proven by " + CONFIG_TEST,
        },
        "composed_config_diffs": {
            **diffs,
            "note": (
                "Each entry flattens two composed configs (core.config.compose) and lists every path whose value "
                "differs. arm_vs_locked_plan: the three factor groups plus the recall width k (8 -> 60), the "
                "baseline's per-flight bookkeeping (this cell's FIT identities and cap, the dropped "
                "prepared_phase_supply, the two appended receipts, what_this_is) and the experiment fragment's own "
                "block; aa_vs_locked_plan: k alone plus bookkeeping; arm_vs_aa: the three factor groups ALONE. "
                "anything_else is empty in every entry or this writer refuses."
            ),
            "preparation_source_receipts": "the parent's list plus two appended entries: " + ", ".join(added),
        },
        "prepared_supplies": supplies,
        "default_byte_identity": {
            "what_is_claimed": "The A/A flies the locked plan's own bytes: its own prepared first-phase supply, minted at this implementation with the widened recall and no committed pin, carries the sealed comparator's output digest.",
            "sealed_comparator_output_sha256": PLAN_SUPPLY_OUTPUT_SHA,
            "aa_output_sha256": supplies["aa"]["output_sha256"],
            "verified": supplies["aa"]["output_sha256"] == PLAN_SUPPLY_OUTPUT_SHA,
            "arm_output_sha256": supplies["arm"]["output_sha256"],
            "smoke_output_sha256": supplies["smoke"]["output_sha256"],
            "how_it_is_proven": "core.preparation.digest over the {facets, values} payload: equality means the same value ids in the same order on every one of the 1,080 rows",
        },
        "composed_delivery_model_free": {
            "source": {"relpath": classes_relpath, "sha256": sha_file(classes_relpath), "script": {"relpath": CLASSES_SCRIPT, "sha256": sha_file(CLASSES_SCRIPT)}},
            "intent_wrong_rows": classes["intent_wrong_rows"],
            "summary": summary,
            "classes": class_counts,
            "all_rows_by_bank_class": classes["all_rows_by_bank_class"],
            "boundary_width_histogram": classes["comp1_boundary_width_histogram"],
            "rows_seeded_with_no_boundary_entry_under_comp1": unseeded,
            "why_one_row_is_unseeded": (
                "A property of the centroid key alone, measured: that row's sealed speech vector has cosine "
                "-0.0039 to its NEAREST centroid key (negative to all 60; +0.0533 to the nearest written key, 30 "
                "non-negative), and the fuser saea-fuse-associated-values-v1 admits a candidate only at cosine "
                ">= tau 0.0, so no boundary entry is admitted and rails.phase_supply.build_bootstrap_selection "
                "seeds nothing for it. The A/A seeds it with 8. It is an INTENT-UNCOVERED, catch-all row, already "
                "intent-wrong in the comparator; the flight tolerates an unseeded row (rails.runner "
                "_per_sample_bootstrap) and the read reports it explicitly."
            ),
            "what_this_is": "membership and delivery only, before contact; a delivery count is never a correctness count",
        },
        "fit": {
            "rule": "the pre-flight prompt budget binds to the LIVE slot (24,576 tokens on the SLURP np4 session) with a reserve of one eighth of the slot (3,072); the Solver phase of the locked plan already reads COMPACT_REQUIRED with a positive physical margin and proceeds under context_fit_policy compact-or-abstain",
            "expected_from_the_agree_measurement": {"perception": 19449, "reviewer": 19313, "planner": 19252, "solver": 21278, "solver_with_the_cited_instruction": 21278 + 134, "solver_physical_margin_after": 2755 - 134},
            "measured": fit,
        },
        "budget_arithmetic": {
            "family_budget": caps,
            "smoke_family_budget": smoke_caps,
            "derivation": [
                "generation_calls_cap = 1,080 rows x 11 contacts per row (perception 1, solver 1, reviewer 3, planner 1, max_revisions 1 -> 1 + 2 * (3 + 1 + 1)) = 11,880, the PLAN family's own; the citation contract adds tokens per Solver contact, never contacts",
                "fit_endpoint_calls_cap = 4 x 11,880 = 47,520; native_task_contract_calls_cap = 1,080 x 6 = 6,480; repeated_speech_audio_seconds_cap 33,930; gpu_hours_fit_inclusive 12.0 per generation cell (the sealed PLAN arm realized 5,425 contacts and 3.6819 GPU hours)",
                "the smoke: 44 / 176 / 24 / 117 s / 1.0 GPU hour, no score",
                "one official complete score per generation cell over the complete 1,080-row manifest through core.scoring_batch, never sharded",
            ],
            "run_cumulative": "every cap binds across ALL attempts of a run id",
        },
        "reported_beside": {"note": "CONTEXT ONLY. None of these is this cell's bar.", "train_fold_a_plan": {"run_id": COMPARATOR_RUN, **COMPARATOR_OFFICIAL}, "train_fold_a_own_null": OWN_NULL, "cross_flight_aa_offset_pp": 1.87},
        "authority_relpaths": [OWNER_DECISIONS, AGREE_PACKAGE + "/README.md", KPROBE_PACKAGE + "/README.md", CONV_READ, RANK_DIAGNOSTIC, KEY_DIAGNOSTIC, INSTRUMENT, BAD_CASE_BANK_DOC, CITATION_MODULE],
        "prohibitions": [
            "No flight before the coordinator declares expected_effect_pp in both places, root mints the decision receipt and all three cells are flipped.",
            "No re-flying of the sealed comparator; no test-split, Fold B or DEV contact or read.",
            "No fourth factor; no k, tau, fuse_coverage, w_prior, store, release, snapshot or roster change; no re-pin of the 211 committed configs.",
            "The citation part may never be reported as a gain (decision 127); two base items are never assumed to add.",
            "No paper-scale profile. --allow-output-change is never passed.",
        ],
    }
    facts_sha = wjson(package + "/registered-facts-v1.json", facts)

    decision_rule = (
        "Read against the IN-CHAIN A/A, never against the sealed comparator alone (instrument rules 3 and 4). "
        "PRIMARY: intent accuracy (scenario_action exact), paired per row, 10,000 bootstrap draws. GUARD: official "
        "pooled SLU-F1 non-inferior at the plan's own null (h_SLU 1.2485). ADMITTED: the intent CI95 lower bound "
        "above zero AND the guard holds AND the declared expected_effect_pp was declared before the seal. NEUTRAL: "
        "both guards non-inferior at the own null (h_intent 0.9943 / h_SLU 1.2485) without an admitted gain -- read "
        "under owner decision 138 as a CONFLICT DIAGNOSIS over the per-class attribution table, never as 'no gain'; "
        "no further element is admitted on top of an unresolved conflict. HARMFUL: a measured loss on either guard "
        "(decision 25). The citation part (decision 152) is admitted on the composed arm's own no-harm reading and is "
        "never reported as a gain. Every verdict carries the per-class attribution table with each row's outcome, "
        "the per-stratum tables in both weightings, the frontier row, the delivery check and the token delta."
    )

    protocol = {
        "schema": "saea-registered-protocol-v1",
        "protocol_id": f"slurp-stage3-comp1-fold-a-protocol-v1",
        "registered_at_utc": args.registered_at,
        "study_commit_at_registration": args.study_commit,
        "source_tree": f"studies/speech-aware-evidence-acquisition, worktree {args.worktree}, branch {args.branch}",
        "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_EXPECTATION_AND_READINESS_FLIP",
        "the_question": (
            "Does the COMPOSITION of the agreement term, the centroid boundary key and the citation contract raise "
            "intent-recognition accuracy over the locked plan on TRAIN Fold A 1,080, read at the in-chain A/A, with "
            "official SLU-F1 non-inferior -- and if it does not, on WHICH class of the 191 intent-wrong rows do the "
            "elements conflict?"
        ),
        "the_composition": facts["the_composition"],
        "unchanged": (
            "the roster (TRAIN Fold A 1,080), the serving geometry (np4 x 24,576), the session " + SESSION + ", the phase "
            "program's 11-contact ceiling, all three stores' snapshot and release pins, the exemplar k of 20, the role graph, "
            "the Perception / Reviewer / Planner templates and response formats, the scorers and every budget"
        ),
        "cells": {key: {k: ids[key][k] for k in ("cell", "experiment", "run_id", "attempt_id", "fit_run_id", "fit_attempt_id", "rows", "composed_config_hash", "protocol_hash", "split_identity_hash", "declares_agreement_source", "boundary_facet_source_sha256", "policy")} for key in CELLS},
        "comparator": {
            "run_id": COMPARATOR_RUN, "attempt_id": COMPARATOR_ATTEMPT, "official": COMPARATOR_OFFICIAL, "never_reflown": True,
            "in_chain_replicate": {"run_id": ids["aa"]["run_id"], "why": "rule 4: a cross-flight contrast with no in-chain replicate is refused outright; the A/A is the locked plan's own bytes re-flown in the same chain"},
            "margins": {**OWN_NULL, "source": "the plan's own null on this roster, cell PLANr"},
        },
        "decision_rule_fixed_here": decision_rule,
        "expectation": facts["the_expectation_the_coordinator_declares"],
        "model_free_proofs_landed_before_contact": {
            "composed_config_diffs": facts["composed_config_diffs"],
            "default_byte_identity": facts["default_byte_identity"],
            "composed_delivery": facts["composed_delivery_model_free"]["summary"],
            "prepared_supplies": {key: {k: supplies[key][k] for k in ("relpath", "file_sha256", "output_sha256", "rows_seeded", "selected_value_ids")} for key in CELLS},
        },
        "development_numbers_only": "Every number this cell will produce is a TRAIN Fold A construction-fold development number (owner decisions 28 and 86) and is never a test claim.",
        "failure_policy": "Stop and preserve on the first failure. AT MOST ONE root-diagnosed recovery re-registration; a second failure closes the cell and the fix is proven on a four-row dry run. Budgets are run-cumulative across attempts.",
        "authority": f"owner decisions 138 and 152 ({OWNER_DECISIONS}); the AGREE registration {AGREE_PACKAGE} and the CONV read {CONV_READ}; the KPROBE registration {KPROBE_PACKAGE}; the two diagnostics {RANK_DIAGNOSTIC} and {KEY_DIAGNOSTIC}; the instrument {INSTRUMENT}; the class headroom of {BAD_CASE_BANK_DOC}; decisions 127 (no-harm base items), 133 (intent primary), 139 (no prior), 101 (the Stage-3 label)",
        "prohibitions": facts["prohibitions"],
    }
    protocol_sha = wjson(package + "/protocol-registered-v1.json", protocol)

    plan_shas: dict[str, str] = {}
    for key in ("arm", "aa", "smoke"):
        identity = ids[key]
        for kind in ("generation", "fit"):
            is_fit = kind == "fit"
            budget = identity["family_budget"]
            plan = {
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
                    "carrier_lock_key": "slurp",
                    "run_id": identity["fit_run_id"] if is_fit else identity["run_id"],
                    "attempt_id": identity["fit_attempt_id"] if is_fit else identity["attempt_id"],
                    "execution_profile": "bounded-discovery-probe",
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
                    if is_fit
                    else (
                        f"Shared core.flight.cli campaign over the committed campaign plan {CAMPAIGN_PLAN}, which carries the A/A replicate AND the COMP-1 arm so the two fly in ONE chain; the campaign acquires its own GenerationLease against the resident session and schedules one official score per generation cell at finalize."
                        if key != "smoke"
                        else "Shared core.flight.cli worker on this cell alone; the smoke is deliberately outside the campaign plan and is never scored."
                    )
                ),
                "prepared_phase_supply": {
                    "relpath": identity["own_supply_requirement"]["relpath"],
                    "sha256": identity["own_supply_requirement"]["sha256"],
                    "output_sha256": supplies[key]["output_sha256"],
                    "note": "THIS CELL'S OWN artifact, built model-free under its own run id by core.flight.cli prepare-supply in this registration (item E16). --allow-output-change must never be passed.",
                },
                "protocol_document": {"relpath": package + "/protocol-registered-v1.json", "sha256": protocol_sha},
                "the_composition": THE_COMPOSITION_SHORT,
                "purpose": (
                    f"{identity['run_id']}: " + (
                        "It measures request envelopes only and reads nothing." if is_fit
                        else decision_rule if key == "arm"
                        else "It supplies the within-chain null the composed delta is read at and makes no claim of its own." if key == "aa"
                        else "Structural form proof only: no score and no read."
                    )
                ),
                "quality_read_gate": "No task-quality read before the complete sealed manifest, the exact ordered outputs, the native phase summary and the single successful complete official TRAIN score all exist for BOTH the COMP-1 arm and its in-chain A/A replicate, and before the coordinator's declared expected_effect_pp is on the record. A verdict computed against the sealed comparator alone is refused.",
            }
            if key == "aa" and not is_fit:
                plan["byte_identity_obligation"] = {"sealed_comparator_output_sha256": PLAN_SUPPLY_OUTPUT_SHA, "this_cell_output_sha256": supplies["aa"]["output_sha256"], "verified": True}
            prefix = {"arm": "", "smoke": "smoke-", "aa": "aa-"}[key]
            plan_shas[f"{key}:{kind}"] = wjson(f"{package}/{prefix}{kind}-plan-registered-v1.json", plan)

    recipe = {
        "schema": "saea-slurp-paired-analysis-recipe-v1",
        "recipe_id": "slurp-stage3-comp1-fold-a-paired-analysis-v1",
        "title": "Cell COMP-1 -- the composed read against the in-chain A/A, with the per-class attribution table owner decision 138 requires",
        "registered_at_utc": args.registered_at,
        "arms": {
            "arm": {"run_id": ids["arm"]["run_id"], "attempt_id": ids["arm"]["attempt_id"], "fit_run_id": ids["arm"]["fit_run_id"], "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL", "outputs_sha256": "PENDING_SEAL"},
            "in_chain_replicate": {"run_id": ids["aa"]["run_id"], "attempt_id": ids["aa"]["attempt_id"], "fit_run_id": ids["aa"]["fit_run_id"], "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL", "outputs_sha256": "PENDING_SEAL", "role": "the within-chain null the delta is read at"},
            "comparator": {"run_id": COMPARATOR_RUN, "attempt_id": COMPARATOR_ATTEMPT, "role": "the sealed locked plan, context beside the A/A, never the bar"},
        },
        "resampling": {"bootstrap_draws": 10000, "metrics": ["scenario_action_exact", "slu_f1_f1"], "seed": 20260927, "unit": "row (paired)"},
        "attribution_classes": {
            "relpath": classes_relpath, "sha256": sha_file(classes_relpath), "membership_fixed_before_contact": True,
            "classes": list(classes["class_order"]), "counts": {k: v["rows"] for k, v in class_counts.items()},
            "columns_read_after_the_seal": [
                "rows", "gold boundary entry delivered under COMP-1 (flown, must equal the membership file's prediction)",
                "intent exact under the sealed PLAN (0 on every row of the table by construction)", "intent exact under the in-chain A/A",
                "intent exact under COMP-1", "wrong -> gold", "gold (A/A) -> wrong (COMP-1)", "same wrong intent", "different wrong intent",
                "beside the single-factor conversion rates: CONV m/70 for the agreement classes, KPROBE m/55 for the centroid classes",
            ],
            "how_it_is_read": "a composed round that does not improve is resolved to the class where its elements conflict -- e.g. newly-by-both rows converting below either single-factor rate, or delivered-but-wrong rows lost under the composition -- and no further element is admitted on top of an unresolved conflict (owner decision 138)",
        },
        "steps": [
            "1. Refuse unless BOTH the arm and the A/A manifests are COMPLETE at 1,080 rows with this registration's composed config hashes, sealed, each with one successful complete official TRAIN score, and unless the coordinator's declared expected_effect_pp is on the record (a number, not the placeholder) before either seal is opened.",
            "2. THE DELIVERY CHECK: from the flown Perception consumption, the rows on which the arm delivered the row's own gold boundary value id must equal attribution-classes-v1.json's per-row delivered_comp1 exactly (162 of the 191 intent-wrong rows; whole-roster table beside it), and the A/A's must equal the locked plan's (86). A mismatch is an engineering defect, not an effect, and closes the read.",
            "3. Score once per arm over the complete manifest with the standard scorer (slurp-slu-official-train through core.scoring_batch, never sharded). Primary: intent accuracy (scenario_action_exact) paired per row against the IN-CHAIN A/A, 10,000 bootstrap draws, seed 20260927. Guard: official pooled SLU-F1, the same pairing. Report the sealed PLAN arm beside both as context, never as the bar.",
            "4. Apply the decision rule fixed in the protocol (ADMITTED / NEUTRAL-as-conflict-diagnosis / HARMFUL) at the own-null margins h_intent 0.9943 and h_SLU 1.2485, against the declared expected_effect_pp.",
            "5. THE PER-CLASS ATTRIBUTION TABLE (owner decisions 138 and 152): for each of the five classes fixed in attribution-classes-v1.json, the columns above, per row and aggregated, with the single-factor conversion rates beside the agreement and centroid classes; and the same transition split over the 889 rows the comparator gets right, by bank class, so harm is visible where it lands.",
            "6. The unseeded row and the seven rows that lose delivery under the composition are reported by id with their outcomes.",
            "7. THE CITATION CREDIT TABLE (decision 152): the per-entry table over the arm's sealed Solver states (analysis/citation_credit.py, saea-citation-credit-table-v1): supplied / cited / cited_correct / supplied_uncited per value id with its digest; the cited-envelope parse rate on every Solver stop and the count of non-authoritative finishes; and the per-contact token delta of the Solver request against the A/A (expected +134 instruction tokens) and completion (expected +26 skeleton +12.71 per cited id).",
            "8. The per-scenario tables in the natural-mixture and equal-stratum weightings, the frontier row (effect x prefilled tokens per row x GPU hours per 1,080 rows), and the realized spend against the caps.",
            "9. Write the read under its own later-registered read id; state that every number is a TRAIN Fold A development number, never a test claim; never write 'no gain'.",
        ],
        "output": {"analysis_root": "analysis/SAEA-SLURP-STAGE3-COMP1-FOLD-A-PAIRED-ANALYSIS-V1"},
        "boundary": "A development read on a TRAIN construction fold (owner decisions 28 and 86); never a test claim, never a generalisation claim, and it admits nothing by itself. No utterance text, transcript, gold label string, intent name as content or model output is printed or persisted: ids, counts, rates and hashes only.",
    }
    recipe_sha = wjson(package + "/analysis-recipe-v1.json", recipe)

    eligible = [ids["arm"]["run_id"], ids["arm"]["fit_run_id"], ids["aa"]["run_id"], ids["aa"]["fit_run_id"], ids["smoke"]["run_id"], ids["smoke"]["fit_run_id"]]
    draft = {
        "_draft_note": "A DRAFT written by the registration agent, in the repository, for root to mint on the data root with scripts/flights/comp1/comp1_mint_receipt.py, which sets status 'decided', stamps recorded_at_utc, re-hashes every antecedent path at mint time and refuses to overwrite. It authorises nothing while its status is not 'decided'. Root mints it ONLY after the coordinator has declared expected_effect_pp in both places.",
        "schema": "saea-campaign-decision-v1",
        "decision_id": DECISION_ID,
        "status": "DRAFT-NOT-MINTED",
        "recorded_at_utc": None,
        "owner": "root",
        "coordinator": "Fable5.1",
        "eligible_run_ids": eligible,
        "cell_kind": "Stage-3 composed system-policy arm (label sealed-credit-system-policy-v1, operator context_application) with its four-row smoke and its in-chain A/A replicate: three cells, six run ids, one chain for the A/A and the arm.",
        "decision": "Fly cell COMP-1 (owner decisions 138 and 152): the locked v2.0 plan with the agreement term (as AGREE), the centroid boundary key (as KPROBE) and the citation contract composed, on TRAIN Fold A 1,080, beside its in-chain A/A in one campaign chain after its four-row smoke; read at intent primary with official SLU-F1 the guard against the coordinator's declared expected_effect_pp; a round that does not improve is a conflict diagnosis over the per-class attribution table.",
        "authorization_basis": f"Owner decision 152 (fold the citation contract into COMP-1 = PLAN lock + agreement term + centroid key + citation, on Fold A 1,080 with an in-chain A/A, intent primary; the expectation composed from the AGREE and KPROBE reads) and decision 138 (the composed round is the cumulative no-harm check; no improvement is a conflict diagnosis). Standing: 133 (intent primary), 139 (no prior), 127 (the citation part is a no-harm base item), 101 (the Stage-3 label), 77 (flights only through the batch driver), and the binding instrument note {INSTRUMENT}.",
        "antecedents": {
            "owner_decisions_138_152": {"path": OWNER_DECISIONS, "sha256": sha_file(OWNER_DECISIONS)},
            "preregistration": {"path": prereg, "sha256": None},
            "readiness_readme": {"path": package + "/README.md", "sha256": None},
            "protocol": {"path": package + "/protocol-registered-v1.json", "sha256": protocol_sha},
            "registered_facts": {"path": package + "/registered-facts-v1.json", "sha256": facts_sha},
            "analysis_recipe": {"path": package + "/analysis-recipe-v1.json", "sha256": recipe_sha},
            "attribution_classes": {"path": classes_relpath, "sha256": sha_file(classes_relpath)},
            "config_proof": {"path": CONFIG_TEST, "sha256": sha_file(CONFIG_TEST) if Path(CONFIG_TEST).is_file() else None},
            "agree_registration": {"path": AGREE_PACKAGE + "/registered-facts-v1.json", "sha256": sha_file(AGREE_PACKAGE + "/registered-facts-v1.json")},
            "kprobe_registration": {"path": KPROBE_PACKAGE + "/registered-facts-v1.json", "sha256": sha_file(KPROBE_PACKAGE + "/registered-facts-v1.json")},
            "conv_read": {"path": CONV_READ, "sha256": sha_file(CONV_READ)},
            "instrument_note": {"path": INSTRUMENT, "sha256": sha_file(INSTRUMENT)},
            "base_cell": f"the LOCKED default plan, cell PLAN ({COMPARATOR_RUN}, v2.0 lock 2026-09-22)",
            "registration_base_commit": args.study_commit,
        },
        "budget": {**{k: caps[k] for k in sorted(caps)}, "smoke": smoke_caps, "paid_api_calls": 0, "plan_budget_is_run_cumulative": True, "ceiling_note": "11 contacts per row = 1 + 2 x (1 + 3 + 1) at max_revisions 1; the citation contract adds tokens per Solver contact, never contacts"},
        "claim_boundary": "No superiority, generalisation, component-causal, held-out, confirmatory or paper-scale claim. The citation part is never reported as a gain. Development numbers only.",
        "failure_policy": protocol["failure_policy"],
        "not_authorized": [
            "any flight before expected_effect_pp is declared in both places, the receipt is minted and all three cells are flipped",
            "touching the resident np4 session by anyone but the coordinator",
            "any ASR, transcript, encoder or paid-API contact",
            "re-flying or re-scoring any sealed cell",
            "--allow-output-change on the re-pin tool",
            "any fourth factor or any k, tau, fuse-policy, w_prior, store, release, snapshot, roster or geometry change",
            "re-pinning the 211 committed configs",
        ],
        "population": {"count": 1080, "split_identity_hash": ids["arm"]["split_identity_hash"], "split_role": "discovery", "partition": "TRAIN Fold A 1,080, unchanged; the smoke flies its first four rows", "fold_b_contact_authorized": False, "test_contact_authorized": False},
        "prepared_phase_supply": {"note": "each cell's own, minted in this registration and re-minted by scripts/flights/repin_cell.py at the flip (item E16); not pinned by this receipt"},
        "registered_hashes": {key: {"composed_config": ids[key]["composed_config_hash"], "protocol": ids[key]["protocol_hash"]} for key in CELLS} | {"note": f"the values of the fragments exactly as committed at {args.study_commit} (readiness held, no decision requirement); repin_cell.py recomputes them at the flip"},
        "service": {"expected_session_id": SESSION, "model_fragment": ids["arm"]["model_fragment"], "slots": 4, "slot_tokens": 24576, "decoder_only": True, "mmproj": "absent", "no_child_start_stop": True, "note": "the resident SLURP np4 session; the flight attaches only, never spawns or stops"},
    }
    draft_sha = wjson(package + "/root-admission-draft-v1.json", draft)

    fence = json.dumps({"stage3_measurement": measurement}, indent=2, ensure_ascii=False, sort_keys=True)
    cc = class_counts
    readme = f"""# Cell COMP-1: the first composed Stage-3 arm

Registered before contact {args.registered_at[:10]} at study commit `{args.study_commit}` (owner decisions 138 and 152);
all three cells **held**. Nothing here authorises a flight, a flip or an admission entry.

**THE EXPECTATION IS NOT DECLARED YET, ON PURPOSE.** `stage3_measurement.{ids['arm']['run_id']}.expected_effect_pp`
is the literal string `{PLACEHOLDER}` in BOTH places the gate reads:
`registered-facts-v1.json` (top-level `stage3_measurement`, canonical) and the fenced json block of
`../{Path(prereg).name}`. Owner decision 139 forbids a prior; decision 152 says the number is composed by the
coordinator from the AGREE and KPROBE reads' measured m values. Until the coordinator replaces the string with
a number in both places, `scripts/checks/stage3_effect_floor_check.py` refuses the arm as
`unparsable-declaration` -- **that refusal is the intended state of this package**, and the flip must not be
run before it clears. What the coordinator composes over is registered here: m_agree = 32 of 70 (read), m_kprobe
(pending), the per-row headroom 0.092615 pp intent, and the four exclusive classes below -- the two
newly-delivered sets share {cc['newly-by-both']['rows']} of their {summary['union_of_the_two_newly_delivered_sets']} rows, so the two m values do not add.

**What COMP-1 is.** The locked v2.0 plan (the sealed PLAN arm `{COMPARATOR_RUN}`) with FOUR changes composed,
each registered and measured separately, and nothing else: (1) the agreement term exactly as cell AGREE carries
it -- `w_agree` 1.0 over the self-excluded exemplar-intent vote, recall `k` 60, delivered `fuse_coverage` 8-1-8
([`{AGREE_PACKAGE}`](../{Path(AGREE_PACKAGE).name}/README.md)); (2) the centroid boundary key exactly as cell KPROBE pins it --
`facet_source` `{arm_p['facet_source']['relpath']}` sha256 `{arm_p['facet_source']['sha256']}`
([`{KPROBE_PACKAGE}`](../{Path(KPROBE_PACKAGE).name}/README.md)); (3) the citation contract as a row-127 no-harm base item (decision
152): policy `{ids['arm']['policy']}`, Solver `response_format_id` `{ids['arm']['solver_material']['response_format_id']}`,
instruction `{ids['arm']['solver_material']['instruction_template']}`, `deliver_normaliser`
`{ids['arm']['deliver_normaliser']['normaliser']}` (`rails/solver_citation.py`; +134 instruction tokens per Solver contact,
+26 output skeleton and 12.71 per cited id, measured on the sealed PLAN trace; byte-identical default); (4) nothing
else. The composed-config diff against the locked PLAN cell is proven in `registered-facts-v1.json`
(`composed_config_diffs`: `arm_vs_locked_plan` = the three factor groups + `k` 8 -> 60 + bookkeeping;
`aa_vs_locked_plan` = `k` alone + bookkeeping; `arm_vs_aa` = the three factor groups ALONE; `anything_else` empty
in every entry) and re-proven by `{CONFIG_TEST}`.

**Three cells, one chain.** `{CAMPAIGN_PLAN}` carries the A/A replicate **and** the arm (instrument rule 4); the
four-row smoke is outside the plan and never scored. The A/A is the PLAN lock's own bytes -- `w_agree` 0.0, no
`agreement_source`, the written key, the un-armed citation default -- at the same recall `k` 60, so the two arms
differ in the three composed factors alone. **Its prepared first-phase supply reproduces the sealed comparator's
output digest `{PLAN_SUPPLY_OUTPUT_SHA}` on all 1,080 rows (verified in this registration; 8,624 selected value ids).**
The arm's own prepared supply carries output digest `{supplies['arm']['output_sha256']}` (1,079 rows seeded, 8,626 ids)
and the smoke's `{supplies['smoke']['output_sha256']}` (4 rows).

**Composed delivery, measured model-free before contact** (`attribution-classes-v1.json`, by `{CLASSES_SCRIPT}`):
of the 191 PLAN intent-wrong rows the locked plan delivers the gold boundary entry on 86, the agreement term alone on
156, the centroid key alone on 136, and **the composition on {summary['delivered_under_comp1']} ({summary['delivered_under_comp1_pct_of_intent_wrong']} %)**. The five exclusive classes decision
152's read is attributed over, membership fixed now, outcome read after the seal:

| class | rows | delivered under COMP-1 | by bank class |
| --- | ---: | ---: | --- |
| delivered-but-wrong (delivered under the locked plan) | {cc['delivered-but-wrong']['rows']} | {cc['delivered-but-wrong']['delivered_under_comp1']} | {cc['delivered-but-wrong']['by_plan_class']} |
| newly-by-both (in CONV's 70 and KPROBE's 55) | {cc['newly-by-both']['rows']} | {cc['newly-by-both']['delivered_under_comp1']} | {cc['newly-by-both']['by_plan_class']} |
| newly-by-agree (CONV's roster only) | {cc['newly-by-agree']['rows']} | {cc['newly-by-agree']['delivered_under_comp1']} | {cc['newly-by-agree']['by_plan_class']} |
| newly-by-centroid (KPROBE's roster only) | {cc['newly-by-centroid']['rows']} | {cc['newly-by-centroid']['delivered_under_comp1']} | {cc['newly-by-centroid']['by_plan_class']} |
| catch-all | {cc['catch-all']['rows']} | {cc['catch-all']['delivered_under_comp1']} | {cc['catch-all']['by_plan_class']} |

Seven rows a single factor or the plan delivers are NOT delivered under the composition, and five catch-all rows are
delivered only under it (ids in the file). On the whole roster the composition gains delivery on 107 rows and loses
it on 6 (by bank class in the file; the harm side of the read). **One row is seeded with no boundary entry at
all** (`{unseeded[0]}`, INTENT-UNCOVERED, catch-all): its sealed speech vector has cosine -0.0039 to its nearest
centroid key (negative to all 60, against +0.0533 to the nearest written key), the fuser admits a candidate only at
cosine >= tau 0.0, so nothing is admitted -- a property of the centroid key alone, tolerated by the runtime and
reported by the read.

**Fit.** The prompt budget binds to the live 24,576-token slot with a one-eighth reserve; the locked plan's Solver
phase already reads COMPACT_REQUIRED with a positive physical margin (2,755 tokens at 21,278 rendered) and proceeds
under `compact-or-abstain`; the cited Solver instruction adds 134 tokens, leaving a positive physical margin of about
2,621 before compaction. The runtime's own `check` measurement is folded into `registered-facts-v1.json` (`fit`).

**`stage3_algorithm`.** The arm and the smoke carry `sealed-credit-system-policy-v1` with `operators_used`
`["context_application"]` -- the family's step (iv), the re-execution of a composed policy chosen and credited over
sealed bytes, beside its in-chain replicate; this cell performs no rollout, scoring, credit or update of its own, and
the citation credit table it seals is the INPUT to the next round's credit. The A/A carries `none`.

| file | what it holds |
| --- | --- |
| `../{Path(prereg).name}` | the preregistration proper, including the `stage3_measurement` fence (placeholder to be filled) |
| `registered-facts-v1.json` | every model-free fact, the composed-config diffs, the CANONICAL `stage3_measurement` (placeholder to be filled), the two fill points |
| `protocol-registered-v1.json` | identities, hashes, budgets, the decision rule, the claim boundary |
| `generation-plan-registered-v1.json` / `fit-plan-registered-v1.json` | the arm's plans |
| `aa-generation-plan-registered-v1.json` / `aa-fit-plan-registered-v1.json` | the in-chain A/A's plans |
| `smoke-generation-plan-registered-v1.json` / `smoke-fit-plan-registered-v1.json` | the four-row smoke's plans |
| `analysis-recipe-v1.json` | the paired read and the per-class attribution table, step by step |
| `attribution-classes-v1.json` | the 191 rows' class membership and composed delivery, fixed before contact |
| `root-admission-draft-v1.json` | the decision receipt root mints with `scripts/flights/comp1/comp1_mint_receipt.py` |

**Budgets (the AGREE arithmetic; the citation adds tokens, never contacts).** Per generation cell {caps['generation_calls_cap']} contacts
(1,080 x 11, run-cumulative), {caps['fit_endpoint_calls_cap']} FIT endpoints, {caps['native_task_contract_calls_cap']} native task-contract calls,
{caps['repeated_speech_audio_seconds_cap']} repeated speech seconds, {caps['gpu_hours_fit_inclusive']} GPU hours, one official complete score; the smoke
{smoke_caps['generation_calls_cap']} / {smoke_caps['fit_endpoint_calls_cap']} / {smoke_caps['repeated_speech_audio_seconds_cap']} s, no score.

**Declare, mint, flip, queue.** (1) The coordinator replaces the placeholder with the composed number in the two
places named above and commits. (2) Root countersigns the seven DRAFT exposure rows and mints
`{DECISION_RELPATH}` from the draft with `scripts/flights/comp1/comp1_mint_receipt.py` (decision id `{DECISION_ID}`,
the six eligible run ids). (3) `scripts/flights/comp1/comp1_flip.sh` re-pins smoke, A/A and arm through
`repin_loop_generic.sh` until the package converges at one HEAD; `--allow-output-change` is never passed; the flip
re-mints each cell's own supply and the A/A's output digest must again be `ba5e1faa...`. (4)
`scripts/flights/comp1/batch_chain_comp1.sh` queues the smoke, then the A/A + arm campaign, behind whatever occupies
the np4 session (decision 77).

**Not authorised by this package.** No flight before the expectation is declared, the receipt is minted and all
three cells are flipped; no contact by this registration; no re-flying of the comparator; no test-split, Fold B or
DEV read; no fourth factor; no store rebuild or release; no re-pin of the 211 committed configs; the citation part is
never reported as a gain.
"""
    readme_sha = wr(package + "/README.md", readme)

    prereg_text = f"""# Cell COMP-1: preregistration

Registered {args.registered_at[:10]} at study commit `{args.study_commit}`, before any contact, from the sealed cell PLAN
fragments by script (decision 58) with the agreement term, the centroid boundary key and the citation contract
composed, under owner decisions 138 and 152. Development numbers only (owner decisions 28 and 86); never a test
claim.

**The declared expectation is a placeholder until the coordinator fills it** (decision 139: no prior; decision 152:
composed from the AGREE and KPROBE reads). The two places: `{package}/registered-facts-v1.json`
(`stage3_measurement.{ids['arm']['run_id']}.expected_effect_pp`) and the fence below. The effect-floor gate refuses the arm
until both carry a number; that is intended.

## The cell

| item | value |
| --- | --- |
| base | the locked v2.0 plan, the sealed PLAN arm `{COMPARATOR_RUN}` ({COMPARATOR_OFFICIAL['slu_f1']} / {COMPARATOR_OFFICIAL['intent_accuracy']}) |
| composition | {THE_COMPOSITION_SHORT} |
| unchanged | roster (TRAIN Fold A 1,080), geometry (np4 x 24,576), session, program and its 11-contact ceiling, all three stores' pins, exemplar k = 20, role graph, the Perception / Reviewer / Planner templates, scorers, budgets |
| comparator | `{COMPARATOR_RUN}`, sealed, never re-flown |
| in-chain replicate | `{ids['aa']['run_id']}`: the locked plan's own bytes (w_agree 0.0, written key, un-armed citation default, recall k 60 -- a proven no-op) re-flown in the SAME campaign chain; prepared output digest `{PLAN_SUPPLY_OUTPUT_SHA}` verified |
| margins | the plan's own null on this roster (PLANr): h_SLU 1.2485, h_intent 0.9943 |
| smoke | four engineering rows, structural acceptance, never scored |
| runs | `{ids['arm']['run_id']}` / `{ids['arm']['fit_run_id']}`; `{ids['aa']['run_id']}` / `{ids['aa']['fit_run_id']}`; `{ids['smoke']['run_id']}` / `{ids['smoke']['fit_run_id']}` |
| composed config hashes | arm `{ids['arm']['composed_config_hash']}`; A/A `{ids['aa']['composed_config_hash']}`; smoke `{ids['smoke']['composed_config_hash']}` |
| protocol hashes | arm `{ids['arm']['protocol_hash']}`; A/A `{ids['aa']['protocol_hash']}`; smoke `{ids['smoke']['protocol_hash']}` |
| prepared supplies (own, E16) | arm `{supplies['arm']['relpath']}` output `{supplies['arm']['output_sha256']}`; A/A `{supplies['aa']['relpath']}` output `{supplies['aa']['output_sha256']}`; smoke output `{supplies['smoke']['output_sha256']}` |
| authority | {protocol['authority']} |

## Decision rule (fixed here)

{decision_rule}

## The measurement declaration

```json
{fence}
```

## What the coordinator composes the expectation from

m_agree = 32 of 70 (read, {CONV_READ}); m_kprobe pending ({KPROBE_PACKAGE}); the per-row headroom of the class the gain
lands on, 0.092615 pp intent (0.041615 pp SLU-F1 for the guard); and the four exclusive classes of
`{package}/attribution-classes-v1.json`: newly-by-agree {cc['newly-by-agree']['rows']}, newly-by-centroid {cc['newly-by-centroid']['rows']},
newly-by-both {cc['newly-by-both']['rows']}, catch-all {cc['catch-all']['rows']} (delivered-but-wrong 86). The two newly-delivered sets share
{cc['newly-by-both']['rows']} of their {summary['union_of_the_two_newly_delivered_sets']} rows, so m_agree x headroom + m_kprobe x headroom double-counts; the composition delivers the gold
entry on {summary['delivered_under_comp1']} of the 191 intent-wrong rows. The citation part contributes no expected gain (a no-harm base item). The bar at
n = 1,080 is {BAR_PP} pp intent. DELIVERY IS NOT CORRECTNESS.

## Budgets and failure rule

Per generation cell: {caps['generation_calls_cap']} generation calls (run-cumulative), {caps['fit_endpoint_calls_cap']} FIT endpoints,
{caps['repeated_speech_audio_seconds_cap']} repeated speech seconds, {caps['gpu_hours_fit_inclusive']} GPU hours, one official complete score. The smoke:
{smoke_caps['generation_calls_cap']} / {smoke_caps['fit_endpoint_calls_cap']} / {smoke_caps['repeated_speech_audio_seconds_cap']} s, no score. The citation contract adds
+134 instruction tokens and +26 (+12.71 per cited id) output tokens per Solver contact and no contacts. {protocol['failure_policy']}

## Prohibitions

{chr(10).join('- ' + line for line in facts['prohibitions'])}
"""
    prereg_sha = wr(prereg, prereg_text)

    ledger_state = "not-requested"
    if args.append_ledger:
        ledger_state = append_ledger(args, ids=ids, supplies=supplies, plan_shas=plan_shas, package=package, classes_relpath=classes_relpath, summary=summary, class_counts=class_counts)

    print(json.dumps({
        "package": package,
        "written": {package + "/README.md": readme_sha, package + "/registered-facts-v1.json": facts_sha, package + "/protocol-registered-v1.json": protocol_sha,
                    package + "/analysis-recipe-v1.json": recipe_sha, package + "/root-admission-draft-v1.json": draft_sha, prereg: prereg_sha, **{f"{package}/{k}": v for k, v in plan_shas.items()}},
        "exposure_ledger": ledger_state,
        "identities": {key: {k: ids[key][k] for k in ("run_id", "fit_run_id", "composed_config_hash", "protocol_hash", "rows")} for key in CELLS},
        "prepared_supplies": {key: {k: supplies[key][k] for k in ("output_sha256", "file_sha256", "rows_seeded", "selected_value_ids")} for key in CELLS},
        "composed_config_diffs": {k: {kk: (len(vv) if isinstance(vv, list) else vv) for kk, vv in v.items()} for k, v in diffs.items()},
        "where_to_fill": where_to_fill,
        "fit": fit["status"],
    }, indent=2, sort_keys=True))
    return 0


THE_COMPOSITION_SHORT = (
    "the locked v2.0 plan + (1) the agreement term as AGREE carries it (w_agree 1.0 over the self-excluded "
    "exemplar-intent vote, recall k 60, delivered 8-1-8) + (2) the centroid boundary key as KPROBE pins it "
    "(facet_source prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/facets.jsonl) + (3) the citation contract "
    "(policy phase-native-candidates-review-revise-cited-v1, Solver response_format_id saea-solver-cited-answer-v1, "
    "instruction probes/slurp_native_role_solver_cited_v1.txt, deliver_normaliser "
    "saea-deliver-cited-answer-normalise-v3-v1) + (4) nothing else"
)

MODEL_TOOL = (
    "Frozen Q4_K_M decoder-only c98304 np4 max512; promoted EVO-FOLDS-V2 speech packets; NO native tool authority on "
    "any role; Perception / Reviewer / Planner prompt bytes the sealed PLAN arm's; the Solver under the cited-answer "
    "contract (+134 instruction tokens) on the arm and the smoke, the locked plan's on the A/A"
)
INHERITED = (
    "TRAIN Fold A discovery rows already exposed by the sealed dual-store anchor, the released direct anchor, cells "
    "B0/B0r, B1 and its twin, B4b, B4b-rep, B5e, B7a, B7a-v2, B8b-anchor, B1-notool, PLAN, PLANr, ROLL-2, CONV and "
    "KPROBE; this cell adds no new row to the fold and opens no split. Prior exposure is inherited in full."
)


def append_ledger(args, *, ids, supplies, plan_shas, package, classes_relpath, summary, class_counts) -> str:
    """Seven rows: six unconsumed flight rows (DRAFT) and one model-free row for the
    attribution-class derivation. Idempotent: replaces its own rows in place, refuses a
    partial set. No cell may contain a literal '|'."""

    text = rd(LEDGER)
    stamp = args.registered_at
    prose = {
        "arm": "Cell COMP-1, the FIRST COMPOSED Stage-3 arm (owner decisions 138 and 152): the locked v2.0 plan + the agreement term (as AGREE: w_agree 1.0, k 60, 8-1-8) + the centroid boundary key (as KPROBE) + the citation contract (saea-solver-cited-answer-v1 with the unwrapping normaliser), nothing else",
        "aa": "The in-chain A/A replicate of cell COMP-1: the locked plan's own bytes (w_agree 0.0, no agreement_source, the written key, the un-armed citation default) at the same recall k 60, re-flown in the same chain as the within-chain null; its prepared supply reproduces the sealed comparator's output digest exactly",
        "smoke": "Four-row form smoke of cell COMP-1: the same three composed actions on the first four rows of the unchanged roster",
    }
    rows: list[tuple[str, str]] = []
    for key in ("arm", "aa", "smoke"):
        identity = ids[key]
        budget = identity["family_budget"]
        for kind in ("generation", "fit"):
            is_fit = kind == "fit"
            run_id = identity["fit_run_id"] if is_fit else identity["run_id"]
            attempt = identity["fit_attempt_id"] if is_fit else identity["attempt_id"]
            prefix = {"arm": "", "smoke": "smoke-", "aa": "aa-"}[key]
            artifact = f"{package}/{prefix}{kind}-plan-registered-v1.json"
            notes = (
                f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending; the arm's expected_effect_pp is the placeholder "
                f"{PLACEHOLDER} until the coordinator declares it from the AGREE and KPROBE reads, decision 139/152) {stamp[:10]} at "
                f"study commit {args.study_commit} by the COMP-1 registration agent (worktree {args.worktree}, branch {args.branch}). "
                f"This registration performs no contact and authorises none. Plan SHA256 {plan_shas[f'{key}:{kind}']}; attempt {attempt}. "
                f"Protocol hash {identity['protocol_hash']}; composed config {identity['composed_config_hash']}; expected session {SESSION} "
                f"(attach only, never spawn or stop). READINESS HELD: root mints {DECISION_RELPATH} (decision id {DECISION_ID}) from the "
                f"package's root-admission-draft-v1.json with the six eligible run ids and this family's caps, then re-pins with "
                f"scripts/flights/repin_cell.py --set-ready, which re-mints each cell's OWN first-phase supply under its own run id (item E16); "
                f"--allow-output-change must never be passed. Every hash in this row moves at the flip and the re-pin tool rewrites it. "
                f"THE COMPOSITION: {THE_COMPOSITION_SHORT}; the composed-config diff against the locked PLAN cell is the three factor groups "
                f"plus k 8 to 60 and bookkeeping, proven in {package}/registered-facts-v1.json and by {CONFIG_TEST}. Prepared supplies minted "
                f"model-free in this registration: arm output {supplies['arm']['output_sha256']} (1,079 rows seeded; one row admits no boundary "
                f"entry under the centroid key at the tau 0.0 cosine floor), A/A output {supplies['aa']['output_sha256']} (the sealed "
                f"comparator's own, verified), smoke output {supplies['smoke']['output_sha256']}. Measurement declaration "
                f"(scripts/checks/stage3_effect_floor_check.py): measurement_design {'form-proof' if key == 'smoke' else 'cross-flight-with-in-chain-replicate'}, "
                f"expected_effect_pp {PLACEHOLDER if key == 'arm' else '0.0'}, claims_benefit {'true' if key == 'arm' else 'false'}, rows {identity['rows']}, "
                f"replicate_run_id {ids['aa']['run_id'] if key == 'arm' else ids['arm']['run_id'] if key == 'aa' else 'n/a (form proof)'}, primary metric intent "
                f"accuracy with official SLU-F1 the guard (decision 133) -- declared at the top level of {package}/registered-facts-v1.json and repeated in the "
                f"preregistration fence; the gate refuses the arm as unparsable-declaration until the number is declared, which is intended. Composed delivery "
                f"measured model-free before contact ({classes_relpath}): the composition delivers the gold boundary entry on {summary['delivered_under_comp1']} of the 191 "
                f"intent-wrong rows (locked plan 86); classes newly-by-agree {class_counts['newly-by-agree']['rows']}, newly-by-centroid {class_counts['newly-by-centroid']['rows']}, "
                f"newly-by-both {class_counts['newly-by-both']['rows']}, catch-all {class_counts['catch-all']['rows']}, delivered-but-wrong 86; the read is a paired read against "
                f"the in-chain A/A at intent primary, and a round that does not improve is a CONFLICT DIAGNOSIS over that table (decision 138), never 'no gain'. "
                f"The citation part is a row-127 no-harm base item and is never reported as a gain; its credit table is the reward signal later rounds read "
                f"(decision 152). Ceiling {budget['generation_calls_cap']} = {identity['rows']} rows x 11 contacts; the citation adds tokens per Solver contact, "
                f"never contacts; budgets are run-cumulative. Stop and preserve on the first failure; AT MOST ONE root-diagnosed recovery re-registration. No "
                f"paper-scale profile, no confirmatory split, no test-split contact, no comparator re-flight and no admission entry from this row."
            )
            scope = prose[key] + (" -- FIT spend identity, request envelopes only, no generation" if is_fit else "")
            cells = [
                "", stamp, run_id, "bounded-discovery-probe", scope, MODEL_TOOL, f"slurp TRAIN Fold A {identity['rows']}", "discovery",
                identity["split_identity_hash"], "no", str(budget["fit_endpoint_calls_cap"] if is_fit else budget["generation_calls_cap"]),
                str(budget["repeated_speech_audio_seconds_cap"]), str(budget["gpu_hours_fit_inclusive"]), INHERITED, artifact, notes, "",
            ]
            rows.append((run_id, " | ".join(cells).strip()))

    model_free = " | ".join([
        "", stamp[:10], CLASSES_ROW, "model-free-check",
        (
            "Derive cell COMP-1's per-class attribution membership over the 191 PLAN intent-wrong TRAIN Fold A rows (owner decisions 138 "
            "and 152): from the bad-case bank's plan_class and gold intent (scoring side only), cell CONV's 70-row and cell KPROBE's 55-row "
            "committed rosters, and the A/A and COMP-1 cells' own prepared first-phase supplies -- whether each row's gold boundary entry is "
            "inside the eight the composition seeds. Zero model, server, encoder, embedder, scorer, tokenizer, network, GPU and paid-API contacts."
        ),
        "no model or tool contact; local arithmetic over receipt-pinned and committed files",
        "slurp TRAIN Fold A 1080, scoring-side gold only",
        "discovery", ids["arm"]["split_identity_hash"], "no", "0", "0", "0",
        "No new speech exposure: every byte read was already exposed by the cells that sealed it. Prior exposure inherited in full.",
        classes_relpath,
        (
            f"REGISTERED BEFORE RESULT READING (DRAFT, root countersignature pending) {stamp[:10]} at study commit {args.study_commit}. "
            f"Script {CLASSES_SCRIPT}; output sha256 {sha_file(classes_relpath)}. Measured: locked plan delivers 86 of 191, the composition "
            f"{summary['delivered_under_comp1']}; newly-by-agree {class_counts['newly-by-agree']['rows']}, newly-by-centroid {class_counts['newly-by-centroid']['rows']}, "
            f"newly-by-both {class_counts['newly-by-both']['rows']}, catch-all {class_counts['catch-all']['rows']}; the two newly-delivered sets share "
            f"{class_counts['newly-by-both']['rows']} of {summary['union_of_the_two_newly_delivered_sets']} rows; one row seeded with no boundary entry under the composition. "
            f"Membership and delivery only -- a delivery count is never a correctness count; it constructs no ExecutionPlan, reserves no contact and "
            f"authorises nothing; it exists because a pre-computation is registered before its result is read, even when it is model-free."
        ),
        "",
    ]).strip()
    rows.append((CLASSES_ROW, model_free))

    for run_id, line in rows:
        if len(line.split("|")) != 17:
            raise SystemExit(f"ledger row {run_id} does not have exactly fifteen cells; a literal '|' slipped into a cell")

    header = (
        "\n## Cell COMP-1: the first composed Stage-3 arm -- the agreement term, the centroid boundary key and the citation contract "
        "on the locked plan, with its in-chain A/A and its four-row smoke (DRAFT, root countersignature pending)\n\n"
        "Six unconsumed flight rows -- the COMP-1 arm, the in-chain A/A replicate, the four-row form smoke and their three FIT spend "
        f"identities -- plus one model-free row for the per-class attribution derivation. Owner decisions 138 and 152; authority {AGREE_PACKAGE} "
        f"and {KPROBE_PACKAGE}. The arm's expected_effect_pp is a placeholder until the coordinator declares it (decision 139). None of these rows "
        "is countersigned and none authorises a contact.\n\n"
        "| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | split role | split identity hash | consumed | "
        "calls | speech audio seconds | gpu hours | inherited exposure | artifacts | notes |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
    )
    fresh = dict(rows)
    lines = text.split("\n")
    replaced = 0
    for index, line in enumerate(lines):
        if line.startswith("|") and len(line.split("|")) > 3 and line.split("|")[2].strip() in fresh:
            lines[index] = fresh.pop(line.split("|")[2].strip())
            replaced += 1
    if replaced and fresh:
        raise SystemExit("the ledger carries some but not all COMP-1 rows; refusing to guess")
    if replaced:
        wr(LEDGER, "\n".join(lines))
        return f"replaced-{replaced}"
    suffix = "" if text.endswith("\n") else "\n"
    wr(LEDGER, text + suffix + header + "\n".join(line for _run, line in rows) + "\n")
    return "appended"


if __name__ == "__main__":
    raise SystemExit(main())
