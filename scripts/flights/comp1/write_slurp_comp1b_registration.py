#!/usr/bin/env python3
"""Write cell COMP-1b's registration package -- COMP-1 minus the citation
contract -- from the committed configs cell COMP-1b's own derive script wrote.

Reads the two derived fragments (arm, smoke), recomposes every hash, PROVES from
the composed configs that each differs from cell COMP-1's own committed,
already-flown fragment by EXACTLY the citation-contract's four leaf paths (one
arming across three JSON locations) plus per-flight bookkeeping and the
experiment fragment's own block, and writes the package documents: registered
facts, protocol, two plan documents per cell, the analysis recipe, a draft
decision receipt for root and the README/preregistration.

The comparator is the EXISTING SEALED in-chain A/A cell COMP-1 already flew
(``SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1``); this registration does not derive,
register or fly a new A/A. ``expected_effect_pp`` is DECLARED here, not left a
placeholder: 4.26 pp intent (the measured COMP-1-vs-A/A intent gain,
``docs/results/2026-09-29-slurp-comp1-fold-a-read.md``), because the 2026-09-29
SLU-harm attribution note (branch fable/comp1slu) shows the removed citation
contract adds 0 to the intent side on identical shortlists and is not the
source of any intent gain, so the composed intent effect the agreement term and
the centroid key alone produce is not expected to move.

Config and receipt-pinned bytes alone: no adapter contact, no server, no lock,
no model, tokenizer, encoder, embedder or scorer contact; it flips nothing and
mints nothing.

    python scripts/flights/comp1/write_slurp_comp1b_registration.py \\
        --package-dir docs/readiness/2026-09-29-slurp-stage3-comp1b-fold-a-v1 \\
        --study-commit <sha> --registered-at 2026-09-29T12:00:00.000000+00:00 \\
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

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash  # noqa: E402

PARENT_EXPERIMENT = "slurp-native-stage3-comp1-fold-a-v1"
PARENT_SMOKE_EXPERIMENT = "slurp-native-stage3-comp1-fold-a-smoke-4-v1"
COMPARATOR_RUN = "SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1"
COMPARATOR_FIT_RUN = "SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-FIT-V1"
COMPARATOR_ATTEMPT = "attempt-slurp-native-stage3-comp1-aa-fold-a-generation-v1"
COMPARATOR_OFFICIAL = {"slu_f1": 64.21, "intent_accuracy": 81.85}
COMP1_ARM_RUN = "SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1"
SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"

CELLS = {
    "arm": "slurp-native-stage3-comp1b-fold-a-v1",
    "smoke": "slurp-native-stage3-comp1b-fold-a-smoke-4-v1",
}
PACKAGE_NAME = "slurp-stage3-comp1b-fold-a-v1"
DECISION_ID = "slurp-stage3-comp1b-fold-a-admission-v1"
DECISION_RELPATH = f"coordination/{PACKAGE_NAME}/root-admission-v1.json"
CAMPAIGN_PLAN = "configs/campaign/slurp-native-stage3-comp1b-fold-a-v1.json"

COMP1_PACKAGE = "docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1"
COMP1_READ = "docs/results/2026-09-29-slurp-comp1-fold-a-read.md"
ATTRIBUTION_NOTE = "docs/results/2026-09-29-slurp-comp1-slu-harm-attribution.md"
ATTRIBUTION_BRANCH = "fable/comp1slu"
ATTRIBUTION_COMMIT = "e30aa1b61"
AGREE_PACKAGE = "docs/readiness/2026-09-26-slurp-stage3-agree-w1-fold-a-v1"
KPROBE_PACKAGE = "docs/readiness/2026-09-27-slurp-stage3-kprobe-fold-a-55-v1"
INSTRUMENT = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"
OWNER_DECISIONS = "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md"
CITATION_MODULE = "src/speech_aware_evidence_acquisition/rails/solver_citation.py"
CONFIG_TEST = "tests/unit/test_comp1b_config.py"
DERIVE_SCRIPT = "scripts/flights/comp1/derive_slurp_comp1b_cell.py"
DIFF_PROOF_SCRIPT = "scripts/analysis/slurp_comp1b_diff_proof.py"
LEDGER = "docs/exposure-ledger.md"

OWN_NULL = {"h_slu": 1.2485, "h_intent": 0.9943, "n": 1080}
BAR_PP = 2.5
EXPECTED_EFFECT_PP = 4.26
TUNING_ROSTER = "slurp-train-construction-pool-agree-kprobe-r01-excluded"
READ_ROSTER = "SLURP-EVO-FOLD-A-V2"

BOOKKEEPING_PREFIXES = ("native_contact_fit.", "prepared_phase_supply", "preparation_source_receipts", "what_this_is")
CITATION_FACTOR_PATHS = (
    "policy",
    "phase_material.solver.instruction_template",
    "phase_material.solver.response_format_id",
    "native_episode.deliver_normaliser.normaliser",
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


def classify_diff(parent_values: dict, mine: dict, experiment_keys: set, *, allowed: tuple[str, ...]) -> dict:
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


def fold_check(check_dir: str | None, cells: dict) -> dict:
    if not check_dir:
        return {"status": "PENDING_CHECK", "note": "run core.flight.cli check on the two cells and re-run this writer with --check-dir"}
    out = {"status": "MEASURED_BY_CHECK", "cells": {}}
    for key, cell_id in cells.items():
        path = Path(check_dir) / f"check-{cell_id}.json"
        if not path.is_file():
            out["cells"][key] = {"status": "MISSING", "path": str(path)}
            continue
        report = json.loads(path.read_text(encoding="utf-8"))
        out["cells"][key] = {"check_path": str(path), "scientific_readiness": report.get("scientific_readiness"), "blockers": report.get("blockers")}
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--package-dir", required=True)
    parser.add_argument("--study-commit", required=True)
    parser.add_argument("--registered-at", required=True)
    parser.add_argument("--branch", default="fable/comp1b")
    parser.add_argument("--worktree", default="/home/chao/saea-worktrees/fable-comp1b")
    parser.add_argument("--check-dir", default=None)
    parser.add_argument("--append-ledger", action="store_true")
    args = parser.parse_args(argv)
    os.chdir(REPO_ROOT)
    package = args.package_dir.rstrip("/").replace("\\", "/")
    prereg = package + "-preregistration.md"

    # ---- identities ---------------------------------------------------------
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

    # ---- the composed-config diff proofs against cell COMP-1's own ----------
    comp1_doc, comp1_cell, comp1 = composed_of(PARENT_EXPERIMENT)
    comp1_smoke_doc, comp1_smoke_cell, comp1_smoke = composed_of(PARENT_SMOKE_EXPERIMENT)
    diffs = {
        "arm_vs_comp1": classify_diff(comp1.values, composed["arm"].values, set(documents["arm"]) | set(comp1_doc), allowed=CITATION_FACTOR_PATHS),
        "smoke_vs_comp1_smoke": classify_diff(comp1_smoke.values, composed["smoke"].values, set(documents["smoke"]) | set(comp1_smoke_doc), allowed=CITATION_FACTOR_PATHS),
    }
    for name, diff in diffs.items():
        if diff["anything_else"]:
            raise SystemExit(f"{name}: the composed config differs beyond the citation-contract factor and bookkeeping: {diff['anything_else']}")
        if sorted(diff["factor_paths"]) != sorted(CITATION_FACTOR_PATHS):
            raise SystemExit(f"{name}: the citation-contract factor did not move exactly: {diff['factor_paths']}")
    # The agreement term and the centroid key must be UNTOUCHED between COMP-1
    # and COMP-1b: neither may appear anywhere in either diff.
    boundary = "knowledge_stores.intent-boundaries.phase_supply.perception."
    for name, diff in diffs.items():
        touched = [k for group in ("factor_paths", "bookkeeping", "experiment_fragment_own_block", "anything_else") for k in diff[group] if k.startswith(boundary)]
        if touched:
            raise SystemExit(f"{name}: the agreement term or the centroid key moved, which COMP-1b must never do: {touched}")

    arm_p = composed["arm"].values["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
    comp1_p = comp1.values["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
    if arm_p != comp1_p:
        raise SystemExit("the arm's boundary channel (agreement term + centroid key) is not COMP-1's own, byte for byte")
    if composed["arm"].values["preparation_source_receipts"] != comp1.values["preparation_source_receipts"]:
        raise SystemExit("the arm's preparation_source_receipts is not COMP-1's own, byte for byte")

    fit = fold_check(args.check_dir, CELLS)
    caps = ids["arm"]["family_budget"]
    smoke_caps = ids["smoke"]["family_budget"]

    measurement = {
        ids["arm"]["run_id"]: {
            "claim": "nominated",
            "claims_benefit": True,
            "expected_effect_pp": EXPECTED_EFFECT_PP,
            "measurement_design": "cross-flight-with-in-chain-replicate",
            "primary_metric": "intent accuracy (scenario_action exact), official pooled SLU-F1 the non-inferiority guard (owner decision 133)",
            "primary_metric_key": "intent",
            "replicate_run_id": COMPARATOR_RUN,
            "rows": 1080,
            "tuning_roster": TUNING_ROSTER,
            "read_roster": READ_ROSTER,
            "note": (
                "COMP-1 minus the citation contract (2026-09-29 SLU-harm attribution, branch "
                f"{ATTRIBUTION_BRANCH} commit {ATTRIBUTION_COMMIT}): the agreement term and the centroid "
                "boundary key alone, COMP-1's own committed bytes, read against the SAME sealed in-chain "
                f"A/A {COMPARATOR_RUN} COMP-1 used (reused cross-flight, never re-flown -- decision 160's "
                "shared-A/A pattern, as cell G5 reused it). expected_effect_pp 4.26 is the measured "
                f"COMP-1-vs-A/A intent delta from {COMP1_READ} (CI95 [+2.41, +6.11]); the attribution note "
                "shows the citation contract does not move the Solver's intent choice on identical "
                "shortlists (COMP-1 vs A/A: 170 identical shortlists, 166 vs 166 rank-1 picks) and adds 0 "
                "entities on the unwrap side, so removing it is not expected to move the intent gain. The "
                "SLU-F1 guard is the SAME Fold A own null h_SLU 1.2485 COMP-1's own rule used; the "
                "attribution note's whole point is that this guard should now HOLD (COMP-1's own loss, "
                "-2.24 [-3.97, -0.47], is attributed entirely to the removed citation contract's zero-gold "
                "over-emission, +102 FP of the +114 total). tuning_roster and read_roster are declared "
                "under item D3 (owner decision 190, 2026-09-29): the agreement table and the centroid key "
                "were each built from a TRAIN construction pool disjoint from Fold A recordings by "
                "construction (the agreement table self-excludes the row's own utterance identity; the "
                "centroid key is the R01-excluded construction-pool mean), and their conversion probes "
                "(CONV, KPROBE) were read on Fold A subsets; this cell reads the composed effect on the "
                "whole Fold A roster, the same circularity COMP-1's own read already carries and discloses. "
                "No disjointness receipt for the construction pool is committed yet, so the tuning/read "
                "overlap check is expected to report tuning-roster-unverified, advisory."
            ),
        },
        ids["smoke"]["run_id"]: {
            "claim": "nominated",
            "claims_benefit": False,
            "expected_effect_pp": 0.0,
            "measurement_design": "form-proof",
            "primary_metric": "intent accuracy (scenario_action exact)",
            "primary_metric_key": "intent",
            "rows": 4,
            "tuning_roster": "none",
            "read_roster": READ_ROSTER,
            "note": (
                "Four rows prove FORM and nothing else: the agreement table and the centroid key file load "
                "and hash-verify, the boundary channel still delivers eight entries, the Solver answers "
                "under the locked plan's own non-cited program and every request fits and the episode "
                "completes. Scored by no one, read by no one; under the instrument's rule 5 a batch of four "
                "rows can never be evidence of benefit."
            ),
        },
    }

    facts = {
        "schema": "saea-registered-facts-v1",
        "_note": (
            "Every model-free measured fact cell COMP-1b's registration rests on, and the CANONICAL "
            "stage3_measurement block scripts/checks/stage3_effect_floor_check.py resolves. Unlike cell "
            "COMP-1, expected_effect_pp is declared HERE, at registration, from measured numbers already on "
            "the record (owner decision 139: no prior, but a number derived from a measured cross-flight "
            "read is not a prior)."
        ),
        "registered_at_utc": args.registered_at,
        "study_commit_at_registration": args.study_commit,
        "owner_decisions": {
            "25": "a measured loss on either guard is HARMFUL",
            "127": "the citation part (when present) is a no-harm base item; not applicable here since it is removed",
            "133": "intent primary, official SLU-F1 the guard",
            "138": "a composed round's read against the lock is the cumulative check",
            "139": "no prior, no pre-committed if-then; a number derived from a measured read is not a prior",
            "152": "COMP-1 = PLAN lock + agreement term + centroid key + citation contract",
            "160": "one shared in-chain A/A may serve more than one composed family in the same chain",
            "190": "primary_metric_key and the tuning_roster / read_roster split (item D3), 2026-09-29",
        },
        "rows": 1080,
        "the_basis": (
            f"COMP-1 read on TRAIN Fold A vs the in-chain A/A {COMPARATOR_RUN} ({COMP1_READ}): intent +4.26 "
            "[+2.41, +6.11], official SLU-F1 -2.24 [-3.97, -0.47]. The attribution note on branch "
            f"{ATTRIBUTION_BRANCH} (commit {ATTRIBUTION_COMMIT}, {ATTRIBUTION_NOTE}) names the Solver "
            "cited-answer contract saea-solver-cited-answer-v1 as the SLU cause: +102 false-positive "
            "entities on the 414 zero-gold rows (89% of the +114 total FP), worth -2.83 pp of pooled "
            "SLU-F1 by counterfactual row-swap; the I7n unwrap adds 0 entities (byte-proven on 1,080/1,080 "
            "rows); the AGREE supply is not the cause (AGREE vs its own A/A is FP -5 [-32,+22], SLU "
            "+1.85). On the intent side the contract does not move the Solver's choice on identical "
            "shortlists (COMP-1 vs A/A: 170 identical shortlists, 6 differ, 166 vs 166 rank-1 picks); the "
            "extra intent harms come with Perception's changed shortlist, which is the supply (agreement "
            "term + centroid key), not the contract. The note recommends the smallest next cell: COMP-1 "
            "minus the citation contract, i.e. AGREE + centroid, Solver policy "
            "phase-native-candidates-review-revise-v1, template slurp_native_role_solver_v2.txt, no "
            "response format, normaliser saea-deliver-normalise-v3, read against the SAME in-chain A/A."
        ),
        "stage3_measurement": measurement,
        "cells": {key: {k: v for k, v in ids[key].items() if k not in ("own_supply_requirement", "family_budget", "execution_plan", "solver_material")} for key in CELLS},
        "the_one_change": {
            "reverted_factor": "the citation contract (COMP-1's factor 3), four leaf JSON paths, one arming",
            "keys": {
                "policy": {"old": "phase-native-candidates-review-revise-cited-v1", "new": "phase-native-candidates-review-revise-v1"},
                "phase_material.solver.instruction_template": {"old": "probes/slurp_native_role_solver_cited_v1.txt", "new": "probes/slurp_native_role_solver_v2.txt"},
                "phase_material.solver.response_format_id": {"old": "saea-solver-cited-answer-v1", "new": None},
                "native_episode.deliver_normaliser.normaliser": {"old": "saea-deliver-cited-answer-normalise-v3-v1", "new": "saea-deliver-normalise-v3"},
            },
            "unchanged": (
                "the agreement term (rank_weights.w_agree 1.0, w_cos 1.0, w_prior 0.0, agreement_source the "
                "sealed exemplar-intent vote, recall k 60, fuse_coverage m 8 / c 1 / top_l 8, tau 0.0), the "
                "centroid boundary key (facet_source the released centroid vectors), the whole "
                "preparation_source_receipts list, the roster, geometry, session, phase-program 11-contact "
                "ceiling, the three stores' snapshot and release pins, the exemplar k of 20, the role graph, "
                "the Perception / Reviewer / Planner templates and the scorers -- proven byte-identical to "
                "COMP-1's own committed values by this writer and by " + CONFIG_TEST
            ),
            "proof_script": {"relpath": DIFF_PROOF_SCRIPT, "sha256": sha_file(DIFF_PROOF_SCRIPT)},
            "derive_script": {"relpath": DERIVE_SCRIPT, "sha256": sha_file(DERIVE_SCRIPT)},
        },
        "composed_config_diffs": {
            **diffs,
            "note": (
                "Each entry flattens two composed configs (core.config.compose) and lists every path whose "
                "value differs, comparing cell COMP-1b against cell COMP-1's own committed, already-flown "
                "config (NOT the locked plan). Both entries: the citation-contract factor's four leaf paths "
                "ALONE, plus per-flight bookkeeping (this cell's FIT identities, the dropped "
                "prepared_phase_supply, what_this_is) and the experiment fragment's own block (cells, date, "
                "experiment_id, fragment_kind, purpose, stage3_algorithm.note). anything_else is empty in "
                "every entry or this writer refuses."
            ),
        },
        "comparator": {
            "run_id": COMPARATOR_RUN,
            "fit_run_id": COMPARATOR_FIT_RUN,
            "attempt_id": COMPARATOR_ATTEMPT,
            "official": COMPARATOR_OFFICIAL,
            "sealed": True,
            "reused_not_reflown": True,
            "registered_by": COMP1_PACKAGE,
            "shared_aa_pattern": "owner decision 160: one shared, already-sealed in-chain A/A may serve more than one composed family in the same chain; cell G5 reused this exact A/A the same way. COMP-1b goes one step further: it reuses the A/A as a pure CROSS-FLIGHT comparator with no re-flight of any kind in this family's own chain -- the A/A's bytes were already flown and sealed by cell COMP-1's own campaign.",
            "margins": {**OWN_NULL, "source": "the plan's own null on this roster, cell PLANr, the same margins COMP-1's own rule used"},
        },
        "fit": {"measured": fit},
        "budget_arithmetic": {
            "family_budget": caps,
            "smoke_family_budget": smoke_caps,
            "derivation": [
                "generation_calls_cap = 1,080 rows x 11 contacts per row, the PLAN/COMP-1 family's own ceiling (removing the citation contract removes tokens, never contacts)",
                "fit_endpoint_calls_cap = 4 x 11,880 = 47,520; native_task_contract_calls_cap = 1,080 x 6 = 6,480; repeated_speech_audio_seconds_cap 33,930; gpu_hours_fit_inclusive 12.0 per generation cell",
                "the smoke: 44 / 176 / 24 / 117 s / 1.0 GPU hour, no score",
                "one official complete score per generation cell over the complete 1,080-row manifest through core.scoring_batch, never sharded",
            ],
            "run_cumulative": "every cap binds across ALL attempts of a run id",
        },
        "reported_beside": {
            "note": "CONTEXT ONLY. None of these is this cell's bar.",
            "train_fold_a_plan": {"run_id": "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1", "slu_f1": 63.6304, "intent_accuracy": 82.2222},
            "train_fold_a_in_chain_aa": COMPARATOR_OFFICIAL,
            "comp1_arm": {"run_id": COMP1_ARM_RUN, "slu_f1": 61.97, "intent_accuracy": 86.11},
            "train_fold_a_own_null": OWN_NULL,
        },
        "authority_relpaths": [OWNER_DECISIONS, COMP1_PACKAGE + "/README.md", COMP1_READ, ATTRIBUTION_NOTE, AGREE_PACKAGE + "/README.md", KPROBE_PACKAGE + "/README.md", INSTRUMENT, CITATION_MODULE],
        "prohibitions": [
            "No flight before root mints the decision receipt and both cells are flipped.",
            "No re-flying of the sealed comparator (the in-chain A/A) or the sealed PLAN arm; no test-split, Fold B or DEV contact or read.",
            "No re-introducing the citation contract; no k, tau, fuse_coverage, w_prior, store, release, snapshot or roster change; no re-pin of the 213 committed configs.",
            "No paper-scale profile. --allow-output-change is never passed.",
        ],
    }
    facts_sha = wjson(package + "/registered-facts-v1.json", facts)

    decision_rule = (
        "Read against the SAME sealed in-chain A/A cell COMP-1 used, reused cross-flight and never "
        "re-flown (owner decision 160's shared-A/A pattern). PRIMARY: intent accuracy (scenario_action "
        "exact), paired per row, 10,000 bootstrap draws. GUARD: official pooled SLU-F1 non-inferior at the "
        "plan's own null (h_SLU 1.2485). ADMITTED: the intent CI95 lower bound above zero, the point at or "
        "above the declared 4.26 pp and the 2.5 pp cross-flight bar, AND the guard holds. NEUTRAL: both "
        "guards non-inferior at the own null (h_intent 0.9943 / h_SLU 1.2485) without an admitted gain. "
        "HARMFUL: a measured loss on either guard (decision 25). Every verdict carries the per-channel "
        "table the attribution note (a) / (b) / (c) split uses, the per-stratum tables in both weightings, "
        "and the same-shortlist intent-choice check."
    )

    protocol = {
        "schema": "saea-registered-protocol-v1",
        "protocol_id": "slurp-stage3-comp1b-fold-a-protocol-v1",
        "registered_at_utc": args.registered_at,
        "study_commit_at_registration": args.study_commit,
        "source_tree": f"studies/speech-aware-evidence-acquisition, worktree {args.worktree}, branch {args.branch}",
        "status": "REGISTERED_BEFORE_CONTACT_AWAITING_ROOT_ADMISSION_AND_READINESS_FLIP",
        "the_question": (
            "With the Solver cited-answer contract removed (the 2026-09-29 attribution note's named cause "
            "of COMP-1's official SLU-F1 guard loss), does the two-factor composition of the agreement term "
            "and the centroid boundary key alone raise intent-recognition accuracy on TRAIN Fold A 1,080, "
            "read at the SAME sealed in-chain A/A cell COMP-1 used, with official SLU-F1 non-inferior?"
        ),
        "the_one_change": facts["the_one_change"],
        "unchanged": (
            "the roster (TRAIN Fold A 1,080), the serving geometry (np4 x 24,576), the session " + SESSION + ", "
            "the phase program's 11-contact ceiling, all three stores' snapshot and release pins, the "
            "exemplar k of 20, the role graph, the Perception / Reviewer / Planner templates and response "
            "formats, the scorers, every budget, and the whole boundary channel (agreement term + centroid "
            "key) -- all COMP-1's own committed bytes"
        ),
        "cells": {key: {k: ids[key][k] for k in ("cell", "experiment", "run_id", "attempt_id", "fit_run_id", "fit_attempt_id", "rows", "composed_config_hash", "protocol_hash", "split_identity_hash", "declares_agreement_source", "boundary_facet_source_sha256", "policy")} for key in CELLS},
        "comparator": facts["comparator"],
        "decision_rule_fixed_here": decision_rule,
        "stage3_measurement": measurement,
        "model_free_proofs_landed_before_contact": {"composed_config_diffs": facts["composed_config_diffs"]},
        "development_numbers_only": "Every number this cell will produce is a TRAIN Fold A construction-fold development number (owner decisions 28 and 86) and is never a test claim.",
        "failure_policy": "Stop and preserve on the first failure. AT MOST ONE root-diagnosed recovery re-registration; a second failure closes the cell and the fix is proven on a four-row dry run. Budgets are run-cumulative across attempts.",
        "authority": (
            f"the 2026-09-29 SLU-harm attribution note (branch {ATTRIBUTION_BRANCH} commit {ATTRIBUTION_COMMIT}, "
            f"{ATTRIBUTION_NOTE}) and the COMP-1 read it explains ({COMP1_READ}); owner decisions 138 and 152 "
            f"({OWNER_DECISIONS}); the AGREE registration {AGREE_PACKAGE}; the KPROBE registration "
            f"{KPROBE_PACKAGE}; the instrument {INSTRUMENT}; decisions 25 (harm), 127, 133, 139, 160, 190 (item D3)"
        ),
        "prohibitions": facts["prohibitions"],
    }
    protocol_sha = wjson(package + "/protocol-registered-v1.json", protocol)

    plan_shas: dict[str, str] = {}
    for key in ("arm", "smoke"):
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
                        f"Shared core.flight.cli campaign over the committed campaign plan {CAMPAIGN_PLAN}, which carries the COMP-1b arm ALONE (the comparator is the existing sealed A/A, reused, never re-flown); the campaign acquires its own GenerationLease against the resident session and schedules one official score per generation cell at finalize."
                        if key != "smoke"
                        else "Shared core.flight.cli worker on this cell alone; the smoke is deliberately outside the campaign plan and is never scored."
                    )
                ),
                "prepared_phase_supply": {
                    "relpath": identity["own_supply_requirement"]["relpath"],
                    "sha256": identity["own_supply_requirement"]["sha256"],
                    "note": "THIS CELL'S OWN artifact, minted model-free under its own run id at the flip by core.flight.cli prepare-supply (item E16); expected to reproduce COMP-1's own arm supply digest ce68bebc... exactly, since the citation contract never touches the first-phase supply. --allow-output-change must never be passed.",
                },
                "protocol_document": {"relpath": package + "/protocol-registered-v1.json", "sha256": protocol_sha},
                "purpose": (
                    f"{identity['run_id']}: " + (
                        "It measures request envelopes only and reads nothing." if is_fit
                        else decision_rule if key == "arm"
                        else "Structural form proof only: no score and no read."
                    )
                ),
                "quality_read_gate": "No task-quality read before the complete sealed manifest, the exact ordered outputs, the native phase summary and the single successful complete official TRAIN score all exist for the COMP-1b arm. A verdict computed against the sealed comparator alone, without re-verifying the shared A/A's byte identity, is refused.",
            }
            prefix = {"arm": "", "smoke": "smoke-"}[key]
            plan_shas[f"{key}:{kind}"] = wjson(f"{package}/{prefix}{kind}-plan-registered-v1.json", plan)

    recipe = {
        "schema": "saea-slurp-paired-analysis-recipe-v1",
        "recipe_id": "slurp-stage3-comp1b-fold-a-paired-analysis-v1",
        "read_run_id": "SAEA-SLURP-STAGE3-COMP1B-FOLD-A-PAIRED-ANALYSIS-V1",
        "title": "Cell COMP-1b -- the composed (agreement + centroid) read against the SAME in-chain A/A cell COMP-1 used, with the same-shortlist intent-choice check and the channel (a)/(b)/(c) split the attribution note used",
        "registered_at_utc": args.registered_at,
        "arms": {
            "arm": {"run_id": ids["arm"]["run_id"], "attempt_id": ids["arm"]["attempt_id"], "fit_run_id": ids["arm"]["fit_run_id"], "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL", "outputs_sha256": "PENDING_SEAL"},
            "in_chain_replicate": {"run_id": COMPARATOR_RUN, "attempt_id": COMPARATOR_ATTEMPT, "role": "the SAME sealed in-chain A/A cell COMP-1 used; reused cross-flight, never re-flown"},
            "comparator": {"run_id": COMP1_ARM_RUN, "attempt_id": "attempt-slurp-native-stage3-comp1-fold-a-generation-v1", "role": "context only: cell COMP-1's own cited arm, the one this cell removes the citation contract from"},
        },
        "resampling": {"bootstrap_draws": 10000, "metrics": ["scenario_action_exact", "slu_f1_f1"], "seed": 20260929, "unit": "row (paired)"},
        "steps": [
            "1. Refuse unless the arm manifest is COMPLETE at 1,080 rows with this registration's composed config hash, sealed, with one successful complete official TRAIN score; the comparator is already sealed and consumed and is read, never re-flown.",
            "2. Re-verify the shared-A/A byte identity is still what cell COMP-1's own shared-aa-proof-v1.json established (prepared output digest ba5e1faa... on all 1,080 rows) before reading any delta against it.",
            "3. Score once over the complete manifest with the standard scorer (slurp-slu-official-train through core.scoring_batch, never sharded). Primary: intent accuracy (scenario_action_exact) paired per row against the in-chain A/A, 10,000 bootstrap draws, seed 20260929. Guard: official pooled SLU-F1, the same pairing.",
            "4. Apply the decision rule fixed in the protocol (ADMITTED / NEUTRAL / HARMFUL) at the own-null margins h_intent 0.9943 and h_SLU 1.2485, against the declared expected_effect_pp 4.26 and the 2.5 pp cross-flight bar.",
            "5. THE ATTRIBUTION PREDICTION CHECK (this cell exists to test it): (a) the zero-gold false-positive delta against the A/A should sit inside the same-bytes null band (about [-27, +29], the attribution note's channel (c) null); (b) official SLU-F1 should be no worse than -h_SLU (-1.2485); (c) the intent gain on identical Perception shortlists should reproduce the 3-to-gold / 1-from-gold pattern the note measured on COMP-1's own 170 identical-shortlist rows.",
            "6. Report the per-scenario tables in both weightings (natural-mixture and equal-stratum), the recording-channel split (far-field / headset), and the same channel (a)/(b)/(c) accounting the attribution note used, so a reader can see directly whether removing the contract closed the gap the note predicted.",
            "7. Write the read under its own later-registered read id; state that every number is a TRAIN Fold A development number, never a test claim.",
        ],
        "output": {"analysis_root": "analysis/SAEA-SLURP-STAGE3-COMP1B-FOLD-A-PAIRED-ANALYSIS-V1"},
        "boundary": "A development read on a TRAIN construction fold (owner decisions 28 and 86); never a test claim, never a generalisation claim. No utterance text, transcript, gold label string, intent name as content or model output is printed or persisted: ids, counts, rates and hashes only.",
    }
    recipe_sha = wjson(package + "/analysis-recipe-v1.json", recipe)

    eligible = [ids["arm"]["run_id"], ids["arm"]["fit_run_id"], ids["smoke"]["run_id"], ids["smoke"]["fit_run_id"]]
    draft = {
        "_draft_note": "A DRAFT written by the registration agent, in the repository, for root to mint on the data root with scripts/flights/comp1/comp1b_mint_receipt.py (pattern of comp1_mint_receipt.py), which sets status 'decided', stamps recorded_at_utc, re-hashes every antecedent path at mint time and refuses to overwrite. It authorises nothing while its status is not 'decided'.",
        "schema": "saea-campaign-decision-v1",
        "decision_id": DECISION_ID,
        "status": "DRAFT-NOT-MINTED",
        "recorded_at_utc": None,
        "owner": "root",
        "coordinator": "Fable5.1",
        "eligible_run_ids": eligible,
        "cell_kind": "Stage-3 composed system-policy arm (label sealed-credit-system-policy-v1, operator context_application), COMP-1 minus its citation contract, with its four-row smoke; the comparator is the SAME sealed in-chain A/A cell COMP-1 used, reused cross-flight and never re-flown.",
        "decision": "Fly cell COMP-1b: cell COMP-1's own committed agreement term and centroid boundary key, with the citation contract reverted to the locked plan's own non-cited program, on TRAIN Fold A 1,080, read against the existing sealed in-chain A/A after its four-row smoke; read at intent primary against the declared 4.26 pp with official SLU-F1 the non-inferiority guard.",
        "authorization_basis": (
            f"The 2026-09-29 SLU-harm attribution note ({ATTRIBUTION_NOTE}, branch {ATTRIBUTION_BRANCH}) names "
            "the Solver cited-answer contract as the cause of COMP-1's official SLU-F1 guard loss and "
            "recommends this exact smallest-next-cell. Owner decisions 138/152 (the composed-round "
            "discipline), 160 (the shared-A/A pattern), 25 (harm), 133 (intent primary), 139 (no prior), "
            "190 (item D3 tuning/read declaration)."
        ),
        "antecedents": {
            "attribution_note": {"path": ATTRIBUTION_NOTE, "branch": ATTRIBUTION_BRANCH, "commit": ATTRIBUTION_COMMIT},
            "comp1_read": {"path": COMP1_READ, "sha256": sha_file(COMP1_READ)},
            "owner_decisions": {"path": OWNER_DECISIONS, "sha256": sha_file(OWNER_DECISIONS)},
            "preregistration": {"path": prereg, "sha256": None},
            "readiness_readme": {"path": package + "/README.md", "sha256": None},
            "protocol": {"path": package + "/protocol-registered-v1.json", "sha256": protocol_sha},
            "registered_facts": {"path": package + "/registered-facts-v1.json", "sha256": facts_sha},
            "analysis_recipe": {"path": package + "/analysis-recipe-v1.json", "sha256": recipe_sha},
            "config_proof": {"path": CONFIG_TEST, "sha256": sha_file(CONFIG_TEST) if Path(CONFIG_TEST).is_file() else None},
            "comp1_registration": {"path": COMP1_PACKAGE + "/registered-facts-v1.json", "sha256": sha_file(COMP1_PACKAGE + "/registered-facts-v1.json")},
            "base_cell": f"cell COMP-1's own committed, flown and sealed fragments ({COMP1_ARM_RUN})",
            "comparator_cell": f"cell COMP-1's own committed, flown and sealed in-chain A/A ({COMPARATOR_RUN}), reused",
            "registration_base_commit": args.study_commit,
        },
        "budget": {**{k: caps[k] for k in sorted(caps)}, "smoke": smoke_caps, "paid_api_calls": 0, "plan_budget_is_run_cumulative": True, "ceiling_note": "11 contacts per row = 1 + 2 x (1 + 3 + 1) at max_revisions 1; removing the citation contract removes tokens, never contacts"},
        "claim_boundary": "No superiority, generalisation, component-causal, held-out, confirmatory or paper-scale claim. Development numbers only. claim: nominated.",
        "failure_policy": protocol["failure_policy"],
        "not_authorized": [
            "any flight before the receipt is minted and both cells are flipped",
            "touching the resident np4 session by anyone but the coordinator",
            "any ASR, transcript, encoder or paid-API contact",
            "re-flying or re-scoring any sealed cell, including the reused in-chain A/A",
            "--allow-output-change on the re-pin tool",
            "any factor other than removing the citation contract; no k, tau, fuse-policy, w_prior, store, release, snapshot, roster or geometry change",
            "re-pinning the 213 committed configs",
        ],
        "population": {"count": 1080, "split_identity_hash": ids["arm"]["split_identity_hash"], "split_role": "discovery", "partition": "TRAIN Fold A 1,080, unchanged; the smoke flies its first four rows", "fold_b_contact_authorized": False, "test_contact_authorized": False},
        "prepared_phase_supply": {"note": "each cell's own, minted at the flip (item E16); not pinned by this receipt"},
        "registered_hashes": {key: {"composed_config": ids[key]["composed_config_hash"], "protocol": ids[key]["protocol_hash"]} for key in CELLS} | {"note": f"the values of the fragments exactly as committed at {args.study_commit} (readiness held, no decision requirement); repin_cell.py recomputes them at the flip"},
        "service": {"expected_session_id": SESSION, "model_fragment": ids["arm"]["model_fragment"], "slots": 4, "slot_tokens": 24576, "decoder_only": True, "mmproj": "absent", "no_child_start_stop": True, "note": "the resident SLURP np4 session; the flight attaches only, never spawns or stops"},
    }
    draft_sha = wjson(package + "/root-admission-draft-v1.json", draft)

    fence = json.dumps({"stage3_measurement": measurement}, indent=2, ensure_ascii=False, sort_keys=True)

    readme = f"""# Cell COMP-1b: COMP-1 minus the citation contract

Registered before contact {args.registered_at[:10]} at study commit `{args.study_commit}`; both cells **held**.
Nothing here authorises a flight, a flip or an admission entry.

**Why.** The 2026-09-29 SLU-harm attribution note on branch `{ATTRIBUTION_BRANCH}` (commit `{ATTRIBUTION_COMMIT}`,
[`{ATTRIBUTION_NOTE}`](../../{ATTRIBUTION_NOTE.split('/', 1)[1]})) reads cell COMP-1's read
([`{COMP1_READ}`](../../{COMP1_READ.split('/', 1)[1]}): intent +4.26 [+2.41, +6.11], official SLU-F1
-2.24 [-3.97, -0.47] against the in-chain A/A `{COMPARATOR_RUN}`) and names the Solver cited-answer contract
`saea-solver-cited-answer-v1` as the SLU cause: +102 false-positive entities on the 414 zero-gold rows (89% of the
whole +114 FP delta), worth -2.83 pp of pooled SLU-F1 by counterfactual row-swap. The I7n unwrap normaliser adds 0
entities (byte-proven on 1,080/1,080 rows) and the AGREE supply is not the cause (AGREE vs its own A/A is FP -5
[-32,+22], SLU +1.85). On the intent side the contract does not move the Solver's choice on identical Perception
shortlists (COMP-1 vs A/A: 170 identical shortlists, only 6 differ, 166 vs 166 rank-1 picks); the extra intent harms
track Perception's changed shortlist -- the supply (agreement term + centroid key), not the contract. The note's
channel table:

| channel | what was measured | pp |
| --- | --- | ---: |
| (a) the cited-answer unwrap (I7n) | 0 entities added, byte-proven 1,080/1,080 | 0.00 |
| (b) the Solver emitting more entities under the contract | +122 raw entities, +114 exact FP (+102 on zero-gold rows) | -2.83 (the whole guard loss and more) |
| (c) the AGREE / centroid supply changing the Solver's input | AGREE vs its own A/A: FP -5, SLU +1.85 (inside the null) | +0.15 to +0.29 (inside the null; not the cause) |

The note's own recommendation, verbatim: **"COMP-1 minus the citation contract, that is, AGREE + centroid key, on
TRAIN Fold A. The Solver setting is: policy `phase-native-candidates-review-revise-v1`; Solver template
`slurp_native_role_solver_v2.txt`; no response format; deliver normaliser `saea-deliver-normalise-v3`. Everything else
keeps COMP-1's bytes. Read it against the same in-chain A/A `{COMPARATOR_RUN}`."** This package is exactly that cell.

**The one change.** Cell COMP-1b is cell COMP-1's OWN committed, already-flown baseline and experiment fragments
(`configs/{{baseline,experiment}}/slurp-native-stage3-comp1-fold-a-{{baseline-}}v1.json`) with the citation
contract's four leaf paths reverted, one arming across three JSON locations, and nothing else:

| key | COMP-1 (old) | COMP-1b (new) |
| --- | --- | --- |
| `policy` | `phase-native-candidates-review-revise-cited-v1` | `phase-native-candidates-review-revise-v1` |
| `phase_material.solver.instruction_template` | `probes/slurp_native_role_solver_cited_v1.txt` | `probes/slurp_native_role_solver_v2.txt` |
| `phase_material.solver.response_format_id` | `saea-solver-cited-answer-v1` | `null` |
| `native_episode.deliver_normaliser.normaliser` | `saea-deliver-cited-answer-normalise-v3-v1` | `saea-deliver-normalise-v3` |

Proven by [`{DIFF_PROOF_SCRIPT}`](../../../{DIFF_PROOF_SCRIPT}) (re-run by `{CONFIG_TEST}`): the composed config of
the COMP-1b arm differs from cell COMP-1's own committed arm by EXACTLY these four leaf paths plus per-flight
bookkeeping (this cell's own FIT ids, the dropped `prepared_phase_supply`, `what_this_is`) and the experiment
fragment's own metadata block (`cells`, `date`, `experiment_id`, `fragment_kind`, `purpose`,
`stage3_algorithm.note`) -- `anything_else` empty. The agreement term (`rank_weights.w_agree` 1.0, `agreement_source`
the sealed exemplar-intent vote, recall `k` 60) and the centroid boundary key (`facet_source` the released centroid
vectors) are asserted byte-for-byte equal to COMP-1's own, and the writer refuses otherwise. Same for the smoke.

**No new A/A.** The comparator is the EXISTING SEALED in-chain A/A `{COMPARATOR_RUN}` cell COMP-1 already flew and
consumed (owner decision 160's shared-A/A pattern, as cell G5 reused it) -- reused purely cross-flight, never
re-flown. `{CAMPAIGN_PLAN}` therefore carries the COMP-1b arm **alone**.

**`stage3_measurement`.** Unlike COMP-1, the expectation is DECLARED here, not a placeholder: `expected_effect_pp`
**4.26** (the measured COMP-1-vs-A/A intent delta, CI95 [+2.41, +6.11]), `claims_benefit` true, `measurement_design`
`cross-flight-with-in-chain-replicate`, `primary_metric_key` `intent` (owner decision 190, item D3), `replicate_run_id`
`{COMPARATOR_RUN}`, guard `h_SLU` **1.2485** (the Fold A own null, the SAME margin COMP-1's own rule used). Against the
2.5 pp cross-flight floor at n = 1,080 (`scripts/checks/stage3_effect_floor_check.py`) the declared 4.26 clears it.
`tuning_roster` `{TUNING_ROSTER}` / `read_roster` `{READ_ROSTER}` (item D3): the agreement table and the centroid key
were built from a TRAIN construction pool disjoint from Fold A by construction, and their conversion probes were read
on Fold A subsets -- the same disclosed circularity COMP-1's own read already carries; no disjointness receipt is
committed for the construction pool yet, so `tuning-roster-unverified` (advisory) is the expected finding.

**`stage3_algorithm`.** The arm and the smoke carry `sealed-credit-system-policy-v1` with `operators_used`
`["context_application"]`, the same label COMP-1 carries: two typed, executable consumption actions (a rank weight
over a pre-computed vote, a retrieval key file) chosen and credited offline over sealed bytes, composed into every
row's Perception supply; this cell performs no rollout, scoring, credit or update of its own.

| file | what it holds |
| --- | --- |
| `../{Path(prereg).name}` | the preregistration proper, including the `stage3_measurement` fence |
| `registered-facts-v1.json` | every model-free fact, the composed-config diff against COMP-1, the CANONICAL `stage3_measurement` |
| `protocol-registered-v1.json` | identities, hashes, budgets, the decision rule, the claim boundary |
| `generation-plan-registered-v1.json` / `fit-plan-registered-v1.json` | the arm's plans |
| `smoke-generation-plan-registered-v1.json` / `smoke-fit-plan-registered-v1.json` | the four-row smoke's plans |
| `analysis-recipe-v1.json` | the paired read, the attribution-prediction check, step by step |
| `root-admission-draft-v1.json` | the decision receipt root mints with `scripts/flights/comp1/comp1b_mint_receipt.py` |

**Budgets (COMP-1's own arithmetic; removing the citation contract removes tokens, never contacts).** Per generation
cell {caps['generation_calls_cap']} contacts (1,080 x 11, run-cumulative), {caps['fit_endpoint_calls_cap']} FIT
endpoints, {caps['native_task_contract_calls_cap']} native task-contract calls, {caps['repeated_speech_audio_seconds_cap']}
repeated speech seconds, {caps['gpu_hours_fit_inclusive']} GPU hours, one official complete score; the smoke
{smoke_caps['generation_calls_cap']} / {smoke_caps['fit_endpoint_calls_cap']} / {smoke_caps['repeated_speech_audio_seconds_cap']} s, no score.

**Mint, flip, queue (not performed by this registration).** (1) Root countersigns the DRAFT exposure rows and mints
`{DECISION_RELPATH}` from the draft (decision id `{DECISION_ID}`, the four eligible run ids). (2) A flip script
extending `scripts/flights/comp1/` re-pins smoke and arm through `repin_loop_generic.sh` until the package converges
at one HEAD; `--allow-output-change` is never passed; the flip mints each cell's own supply, expected to reproduce
COMP-1's own arm supply digest exactly (the citation contract never touches the first-phase supply). (3) A batch
chain script queues the smoke then the arm campaign behind whatever occupies the np4 session (decision 77).

**Not authorised by this package.** No flight before the receipt is minted and both cells are flipped; no contact by
this registration; no re-flying of the comparator or the sealed PLAN arm; no test-split, Fold B or DEV read; no
factor other than removing the citation contract; no store rebuild or release; no re-pin of the 213 committed
configs.
"""
    readme_sha = wr(package + "/README.md", readme)

    prereg_text = f"""# Cell COMP-1b: preregistration

Registered {args.registered_at[:10]} at study commit `{args.study_commit}`, before any contact, from cell COMP-1's
own committed, already-flown fragments (decision 58: script-derived registrations) by reverting the citation
contract alone. Development numbers only (owner decisions 28 and 86); never a test claim.

## The cell

| item | value |
| --- | --- |
| base | cell COMP-1's own committed arm `{COMP1_ARM_RUN}` (61.97 SLU / 86.11 intent) |
| composition | AGREE + centroid key alone, COMP-1's own bytes, byte for byte; the citation contract reverted to the locked plan's non-cited program |
| unchanged | roster (TRAIN Fold A 1,080), geometry (np4 x 24,576), session, program and its 11-contact ceiling, all three stores' pins, exemplar k = 20, role graph, the Perception / Reviewer / Planner templates, scorers, budgets, the whole boundary channel |
| comparator | `{COMPARATOR_RUN}`, sealed, REUSED cross-flight, never re-flown (owner decision 160's shared-A/A pattern) |
| margins | the plan's own null on this roster (PLANr): h_SLU 1.2485, h_intent 0.9943 |
| smoke | four engineering rows, structural acceptance, never scored |
| runs | `{ids['arm']['run_id']}` / `{ids['arm']['fit_run_id']}`; `{ids['smoke']['run_id']}` / `{ids['smoke']['fit_run_id']}` |
| composed config hashes | arm `{ids['arm']['composed_config_hash']}`; smoke `{ids['smoke']['composed_config_hash']}` |
| protocol hashes | arm `{ids['arm']['protocol_hash']}`; smoke `{ids['smoke']['protocol_hash']}` |
| authority | {protocol['authority']} |

## Decision rule (fixed here)

{decision_rule}

## The measurement declaration

```json
{fence}
```

## Where the declared 4.26 pp comes from

The measured COMP-1-vs-A/A intent delta, {COMP1_READ}: +4.26 pp CI95 [+2.41, +6.11]. The 2026-09-29 attribution note
({ATTRIBUTION_NOTE}, branch {ATTRIBUTION_BRANCH}) shows the citation contract does not move the Solver's intent
choice on identical Perception shortlists (170 of 1,080 rows identical between COMP-1 and its A/A; only 6 differ, 166
vs 166 rank-1 picks) and that the extra intent harms track the supply's changed shortlist, not the contract; removing
the contract is therefore not expected to move the intent gain. The 2.5 pp cross-flight bar at n = 1,080 is cleared.
DELIVERY IS NOT CORRECTNESS; this is a prediction to be tested, not a foregone conclusion.

## Budgets and failure rule

Per generation cell: {caps['generation_calls_cap']} generation calls (run-cumulative), {caps['fit_endpoint_calls_cap']} FIT endpoints,
{caps['repeated_speech_audio_seconds_cap']} repeated speech seconds, {caps['gpu_hours_fit_inclusive']} GPU hours, one official complete score. The smoke:
{smoke_caps['generation_calls_cap']} / {smoke_caps['fit_endpoint_calls_cap']} / {smoke_caps['repeated_speech_audio_seconds_cap']} s, no score. {protocol['failure_policy']}

## Prohibitions

{chr(10).join('- ' + line for line in facts['prohibitions'])}
"""
    prereg_sha = wr(prereg, prereg_text)

    print(json.dumps({
        "package": package,
        "written": {package + "/README.md": readme_sha, package + "/registered-facts-v1.json": facts_sha, package + "/protocol-registered-v1.json": protocol_sha,
                    package + "/analysis-recipe-v1.json": recipe_sha, package + "/root-admission-draft-v1.json": draft_sha, prereg: prereg_sha, **{f"{package}/{k}": v for k, v in plan_shas.items()}},
        "identities": {key: {k: ids[key][k] for k in ("run_id", "fit_run_id", "composed_config_hash", "protocol_hash", "rows")} for key in CELLS},
        "composed_config_diffs": {k: {kk: (len(vv) if isinstance(vv, list) else vv) for kk, vv in v.items()} for k, v in diffs.items()},
        "fit": fit["status"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
