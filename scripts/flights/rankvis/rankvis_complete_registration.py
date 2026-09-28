#!/usr/bin/env python3
"""Complete cell RANKVIS's flight registration from the committed configs (owner decision 171).

The registration merged at dc794346 carried the fragments, the roster derivation, the registered facts,
the preregistration and three DRAFT ledger rows, but none of the documents the shared flip and launch
tools consume: the single-cell campaign plan, the protocol document, the generation and FIT plan
documents (the re-pin tool rewrites the composed / protocol hashes it finds in them; it does not write
them), the analysis recipe with its declared READ run id (``scripts/checks/flight_registration_check.py``,
owner decision 163), the READ exposure row, and the root-admission draft the mint script copies. This
writer adds exactly those, in KPROBE's shape (``scripts/flights/write_slurp_kprobe_registration.py``),
and points the two flight rows' artifacts column at their plan documents with the plan / protocol /
composed hashes appended to their notes, as every sibling package does.

Config alone: compose + protocol_hash over committed fragments. No adapter, no split load, no model,
server, tokenizer, encoder or scorer contact. It flips nothing, mints nothing and countersigns nothing.
Idempotent: refuses to run twice (the campaign plan or the READ row already present).

    python scripts/flights/rankvis/rankvis_complete_registration.py --study-commit <sha> --registered-at <iso>
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash  # noqa: E402

PACKAGE = "docs/readiness/2026-09-27-slurp-stage3-rankvis-probe-fold-a-v1"
PREREG = PACKAGE + "-preregistration.md"
EXPERIMENT = "slurp-native-stage3-rankvis-fold-a-119-v1"
PACKAGE_NAME = "slurp-stage3-rankvis-fold-a-119-v1"
DECISION_ID = "slurp-stage3-rankvis-fold-a-119-admission-v1"
DECISION_RELPATH = f"coordination/{PACKAGE_NAME}/root-admission-v1.json"
CAMPAIGN = f"configs/campaign/{EXPERIMENT}.json"
SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"
COMPARATOR_RUN = "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1"
READ_DRIVER = "scripts/analysis/rankvis_probe_read.py"
READ_WRAPPER = "scripts/flights/rankvis/rankvis_read.sh"
LEDGER = "docs/exposure-ledger.md"
SYNTHESIS = "docs/results/2026-09-27-slurp-mechanism-synthesis.md"
ERROR_SOURCES = "docs/results/2026-09-27-slurp-agree-arm-error-sources.md"
INSTRUMENT = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"
OWNER_DECISIONS = "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md"
CONFIG_TESTS = ["tests/unit/test_rankvis_config.py", "tests/unit/test_knowledge_value_rendering.py",
                "tests/unit/test_rankvis_probe_read.py"]
ROSTER_ROW = "SAEA-SLURP-MF-RANKVIS-ROSTER-DERIVATION-V1"


def rd(rel: str) -> str:
    return io.open(REPO_ROOT / rel, encoding="utf-8", newline="").read()


def wr(rel: str, text: str) -> str:
    path = REPO_ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="").write(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def wjson(rel: str, obj: object) -> str:
    return wr(rel, json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def sha_file(rel: str) -> str | None:
    path = REPO_ROOT / rel
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--study-commit", required=True)
    parser.add_argument("--registered-at", required=True)
    args = parser.parse_args(argv)

    if (REPO_ROOT / CAMPAIGN).exists():
        raise SystemExit(f"refusing to run twice: {CAMPAIGN} exists")
    facts = json.loads(rd(PACKAGE + "/registered-facts-v1.json"))
    document = json.loads(rd(f"configs/experiment/{EXPERIMENT}.json"))
    cell = document["cells"][0]
    composed = compose(REPO_ROOT, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], EXPERIMENT)
    split = document["population"]["split_identity_hash"]
    phash = protocol_hash(composed.config_hash, composed.values["arm"], split)
    caps = document["family_budget"]
    fit = composed.values["native_contact_fit"]
    run_id, fit_run = cell["run_id"], fit["run_id"]
    read_run = f"{run_id}-READ-V1"  # the read driver's own default analysis root
    rows = int(document["population"]["count"])
    if rows != 119 or facts["cell"]["run_id"] != run_id or facts["cell"]["fit_run_id"] != fit_run:
        raise SystemExit("the committed fragments disagree with the registered facts")
    ledger = rd(LEDGER)
    if f"| {read_run} |" in ledger:
        raise SystemExit(f"refusing to run twice: ledger already has {read_run}")

    wjson(CAMPAIGN, {"cells": [{"cell": cell["cell_id"], "experiment": EXPERIMENT}], "schema": "saea-campaign-plan-v1"})

    status = "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP"
    source_tree = f"studies/speech-aware-evidence-acquisition, master at {args.study_commit} (registration completed by the flight-operations agent under owner decision 171)"
    protocol = {
        "schema": "saea-registered-protocol-v1",
        "registered_at_utc": args.registered_at,
        "source_tree": source_tree,
        "status": status,
        "authority": (
            f"owner decision 171 ({OWNER_DECISIONS}); the mechanism synthesis {SYNTHESIS} (section 5, rank 2); the AGREE "
            f"error-source read {ERROR_SOURCES}; the measurement instrument {INSTRUMENT} (rule 5, the form-proof row); owner "
            "decisions 28 and 86 (development numbers), 101 (the Stage-3 algorithm label), 134 (probe before arm) and 139 "
            "(an arm declares its expectation from its probe)"
        ),
        "the_question": facts.get("read_rule", {}).get("deliverable"),
        "one_factor": (
            "ONE KEY. native_episode.knowledge_value_rendering {schema saea-knowledge-value-rendering-v1, order "
            "retrieval-rank, rank_visible true, stores [intent-boundaries, train-exemplars]} added to the registered AGREE "
            "arm's baseline; every other composed byte is the AGREE arm's (tests/unit/test_rankvis_config.py)."
        ),
        "the_one_change": facts["the_one_change"],
        "comparator": facts["comparator"],
        "cells": {
            "probe": {
                "cell": cell["cell_id"], "experiment": EXPERIMENT, "run_id": run_id, "attempt_id": cell["attempt_id"],
                "fit_run_id": fit_run, "fit_attempt_id": fit["attempt_id"], "composed_config_hash": composed.config_hash,
                "protocol_hash": phash, "split_identity_hash": split, "rows": rows,
            }
        },
        "read_rule": facts["read_rule"],
        "no_op_expectation": facts["no_op_expectation"],
        "re_declaration_rule": facts["re_declaration_rule"],
        "stage3_measurement": facts["stage3_measurement"],
        "stage3_algorithm": facts["stage3_algorithm"],
        "gold_selection": facts["gold_selection"],
        "family_budget": caps,
        "expected_session_id": SESSION,
        "no_smoke": (
            "No smoke, as the CONV (70 rows) and KPROBE (55 rows) precedents: 119 rows is itself a form proof "
            "(claims_benefit false) and no smoke row was registered. The rendering code path is exercised by two real "
            "native episodes in tests/unit/test_knowledge_value_rendering.py, and the read's rendering gate refuses a "
            "number unless the flown Solver requests carry the labels on every row."
        ),
        "failure_policy": document["failure_policy"],
    }
    protocol_sha = wjson(PACKAGE + "/protocol-registered-v1.json", protocol)

    def plan_document(kind: str) -> dict:
        generation = kind == "generation"
        return {
            "schema": f"saea-registered-{kind}-plan-v1",
            "plan_kind": kind,
            "cell": cell["cell_id"],
            "experiment": EXPERIMENT,
            "composed_config_hash": composed.config_hash,
            "execution_plan": {
                "attempt_id": cell["attempt_id"] if generation else fit["attempt_id"],
                "carrier_lock_key": composed.values["carrier_lock_key"],
                "execution_profile": document["execution_profile"],
                "planned_gpu_hours": caps["gpu_hours_fit_inclusive"],
                "planned_model_calls": caps["generation_calls_cap"] if generation else caps["fit_endpoint_calls_cap"],
                "planned_speech_audio_seconds": caps["repeated_speech_audio_seconds_cap"],
                "protocol_hash": phash,
                "run_id": run_id if generation else fit_run,
                "schema": "saea-execution-plan-v1",
                "split_identity_hash": split,
                "split_role": "discovery",
                "study": "speech-aware-evidence-acquisition",
            },
            "execution_route": (
                f"Shared core.flight.cli campaign over the committed campaign plan {CAMPAIGN}, a single-cell chain; the "
                "campaign acquires its own GenerationLease against the resident session and schedules one official score "
                "over the complete manifest at finalize."
                if generation
                else "The shared core.flight.cli FIT path under this cell's own native_contact_fit ids; it measures request envelopes and produces no generation."
            ),
            "expected_session_id": SESSION,
            "family_budget": caps,
            "one_factor": protocol["one_factor"],
            "preparation_base_commit": args.study_commit,
            "prepared_phase_supply": {
                "note": "NONE COMMITTED, by design: the flip mints this cell's own under its own run id (item E16) and --allow-output-change must never be passed.",
                "relpath": f"prepared/{run_id}/phase-supply-v1.json",
                "sha256": "MINTED_AT_THE_FLIP",
            },
            "protocol_document": {"relpath": PACKAGE + "/protocol-registered-v1.json", "sha256": protocol_sha},
            "purpose": (
                f"{run_id}: cell RANKVIS, the rank-visible rendering conversion probe. There is no verdict and no admission: "
                f"the deliverable is m of {rows} wrong-to-gold conversions read against the no-op expectation 15.906."
                if generation
                else f"{run_id}: cell RANKVIS. It measures request envelopes only and reads nothing."
            ),
            "quality_read_gate": (
                "No read before the complete sealed manifest, the exact ordered outputs, the native phase summary and the "
                "single successful complete official TRAIN score all exist, and before the rendering gate verifies the rank "
                f"labels and order from the sealed MODEL_REQUEST records on all {rows} rows. A partial manifest is never scored and never read."
            ),
            "registered_at_utc": args.registered_at,
            "source_tree": source_tree,
            "status": status,
            "unused_budget_is_not_attempt_authority": True,
        }

    gen_sha = wjson(PACKAGE + "/generation-plan-registered-v1.json", plan_document("generation"))
    fit_sha = wjson(PACKAGE + "/fit-plan-registered-v1.json", plan_document("fit"))

    derivation_rel = PACKAGE + "/roster-derivation-v1.json"
    recipe = {
        "schema": "saea-slurp-conditional-rate-recipe-v1",
        "recipe_id": f"slurp-stage3-rankvis-fold-a-{rows}-conditional-rate-v1",
        "read_run_id": read_run,
        "title": "Cell RANKVIS -- m of 119 wrong-to-gold conversions under rank-ordered, rank-visible rendering, against the no-op expectation",
        "registered_at_utc": args.registered_at,
        "arms": {
            "probe": {"run_id": run_id, "attempt_id": cell["attempt_id"], "fit_run_id": fit_run,
                      "outputs_sha256": "PENDING_SEAL", "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL"},
            "comparator": {"run_id": COMPARATOR_RUN, "role": facts["comparator"]},
        },
        "roster": {"relpath": derivation_rel, "sha256": sha_file(derivation_rel), "count": rows,
                   "id_list_sha256": facts["roster"]["id_list_sha256"], "split_identity_hash": split},
        "read_rule": facts["read_rule"],
        "no_op_expectation": facts["no_op_expectation"],
        "re_declaration_rule": facts["re_declaration_rule"],
        "metrics": ["scenario_action_exact"],
        "interval": {"kind": "binomial", "primary": "Wilson score CI95", "reported_beside": "exact Clopper-Pearson CI95"},
        "output": {"analysis_root": f"analysis/{read_run}"},
        "read_driver": READ_DRIVER,
        "read_wrapper": READ_WRAPPER,
        "boundary": (
            "A development read on a TRAIN construction fold (owner decisions 28 and 86); never a test claim, never a pooled "
            "or roster-level claim, and it admits nothing. No utterance text, transcript, gold label string or model output "
            "is printed or persisted: ids, counts, rates and hashes only."
        ),
    }
    recipe_sha = wjson(PACKAGE + "/analysis-recipe-v1.json", recipe)

    draft = {
        "_draft_note": (
            "A DRAFT in the repository for root to mint on the data root with scripts/flights/rankvis/rankvis_mint_receipt.py, "
            "which sets status 'decided', stamps recorded_at_utc, re-hashes every antecedent path at mint time and refuses to "
            "overwrite. It authorises nothing while its status is not 'decided'."
        ),
        "schema": "saea-campaign-decision-v1",
        "decision_id": DECISION_ID,
        "status": "DRAFT-NOT-MINTED",
        "recorded_at_utc": None,
        "owner": "root",
        "coordinator": "Fable5.1",
        "eligible_run_ids": [run_id, fit_run],
        "cell_kind": (
            f"Stage-3 conditional-rate probe (label none). One arm, {rows} rows, no smoke and no comparator flight: the "
            "rank-ordered, rank-visible rendering of the delivered boundary and exemplar blocks, converted on AGREE's "
            "delivered-but-wrong rows."
        ),
        "decision": (
            f"Fly cell RANKVIS (owner decision 171): the registered AGREE arm with one native_episode key added "
            f"(knowledge_value_rendering), on exactly the {rows} TRAIN Fold A rows AGREE delivered the gold boundary entry "
            f"for and still answered wrong. The read is m of {rows} with a Wilson CI95 and Clopper-Pearson beside it, "
            "against the no-op expectation 15.906, gated on the rendering verified from the sealed request records."
        ),
        "authorization_basis": (
            "Owner decision 171; standing decisions 134 (probe before arm), 139 (the arm declares its expectation from the "
            "probe's m against the no-op expectation), 101 (algorithm label, honestly none), 77 (flights only through the "
            f"batch driver), 163 (registration gate) and the binding instrument note {INSTRUMENT}. The population was "
            "selected using gold OFFLINE: a conditional estimate only, never a pooled claim."
        ),
        "antecedents": {
            "owner_decisions": {"path": OWNER_DECISIONS, "sha256": sha_file(OWNER_DECISIONS)},
            "synthesis": {"path": SYNTHESIS, "sha256": sha_file(SYNTHESIS)},
            "error_sources": {"path": ERROR_SOURCES, "sha256": sha_file(ERROR_SOURCES)},
            "preregistration": {"path": PREREG, "sha256": None},
            "readiness_readme": {"path": PACKAGE + "/README.md", "sha256": None},
            "protocol": {"path": PACKAGE + "/protocol-registered-v1.json", "sha256": protocol_sha},
            "registered_facts": {"path": PACKAGE + "/registered-facts-v1.json", "sha256": sha_file(PACKAGE + "/registered-facts-v1.json")},
            "analysis_recipe": {"path": PACKAGE + "/analysis-recipe-v1.json", "sha256": recipe_sha},
            "roster_derivation": {"path": derivation_rel, "sha256": sha_file(derivation_rel)},
            "read_driver": {"path": READ_DRIVER, "sha256": sha_file(READ_DRIVER)},
            "config_proofs": [{"path": p, "sha256": sha_file(p)} for p in CONFIG_TESTS],
            "instrument_note": {"path": INSTRUMENT, "sha256": sha_file(INSTRUMENT)},
            "clause_comparator": f"the sealed AGREE arm {COMPARATOR_RUN} on the same rows, never re-flown; no admission read",
            "registration_base_commit": args.study_commit,
        },
        "budget": {**{k: caps[k] for k in sorted(caps)}, "paid_api_calls": 0, "plan_budget_is_run_cumulative": True,
                   "ceiling_note": "11 contacts per row = 1 + 2 x (1 + 3 + 1) at max_revisions 1; 1.5 GPU-h is a ceiling"},
        "claim_boundary": "No superiority, generalisation, component-causal, bar, admission, held-out, confirmatory or paper-scale claim; a conditional rate on a gold-selected roster only.",
        "failure_policy": "Stop and preserve on the first failure. AT MOST ONE root-diagnosed recovery re-registration; a second failure closes the cell and the fix is proven on a four-row dry run. The budget is run-cumulative across attempts.",
        "not_authorized": [
            "any flight before the cell is flipped and the receipt is minted",
            "touching the resident np4 session by anyone but the coordinator",
            "any ASR, transcript, encoder or paid-API contact",
            "re-flying or re-scoring any sealed cell (AGREE included)",
            "--allow-output-change on the re-pin tool",
            "any change beyond the one registered key",
            "a pooled, roster-level or admission read from this cell",
        ],
        "population": {"count": rows, "split_identity_hash": split, "split_role": "discovery",
                       "partition": facts["roster"]["definition"], "fold_b_contact_authorized": False, "test_contact_authorized": False},
        "prepared_phase_supply": {"note": "minted by scripts/flights/repin_cell.py at the flip (this cell's own, item E16); not pinned by this receipt"},
        "registered_hashes": {"composed_config": composed.config_hash, "protocol": phash,
                              "note": f"as composed at {args.study_commit} (readiness held); repin_cell.py recomputes them at the flip."},
        "service": {"decoder_only": True, "expected_session_id": SESSION, "mmproj": "absent", "model_fragment": cell["model_fragment"],
                    "no_child_start_stop": True, "slot_tokens": 24576, "slots": 4,
                    "note": "the resident SLURP np4 session; the flight attaches only, never spawns or stops"},
    }
    wjson(PACKAGE + "/root-admission-draft-v1.json", draft)

    # ---- ledger: point the two flight rows at their plans, append the plan hashes, add the READ row ----
    plan_shas = {"generation": gen_sha, "fit": fit_sha}
    out, done = [], {run_id: False, fit_run: False}
    completion = (
        " REGISTRATION COMPLETED {when} at study commit {commit} by the flight-operations agent (owner decision 171): "
        "the plan documents, protocol document, campaign plan {campaign}, analysis recipe (READ run id {read}) and "
        "root-admission draft written by scripts/flights/rankvis/rankvis_complete_registration.py; no contact. Plan SHA256 "
        "{plan}; attempt {attempt}. Protocol hash {phash}; composed config {chash}; expected session {session} (attach only, "
        "never spawn or stop). Every hash in this row moves at the flip and the re-pin tool rewrites it."
    )
    for line in ledger.split("\n"):
        for rid, kind, attempt in ((run_id, "generation", cell["attempt_id"]), (fit_run, "fit", fit["attempt_id"])):
            if line.startswith("| ") and f"| {rid} |" in line and not done[rid]:
                cells = line.split(" | ")
                facts_rel = PACKAGE + "/registered-facts-v1.json"
                if cells[-2].strip() != facts_rel:
                    raise SystemExit(f"unexpected artifacts column on {rid}: {cells[-2]!r}")
                cells[-2] = PACKAGE + ("/generation-plan-registered-v1.json" if kind == "generation" else "/fit-plan-registered-v1.json")
                last = cells[-1]
                assert last.endswith(" |"), last[-20:]
                cells[-1] = last[:-2].rstrip() + completion.format(
                    when=args.registered_at[:10], commit=args.study_commit, campaign=CAMPAIGN, read=read_run,
                    plan=plan_shas[kind], attempt=attempt, phash=phash, chash=composed.config_hash, session=SESSION) + " |"
                line = " | ".join(cells)
                done[rid] = True
        out.append(line)
        if f"| {ROSTER_ROW} |" in line:
            read_cells = [
                "", args.registered_at, read_run, "model-free-check",
                (f"The cell RANKVIS read (recipe {recipe['recipe_id']}): m of {rows} wrong-to-gold conversions of the probe "
                 f"{run_id} against the sealed AGREE arm {COMPARATOR_RUN}, read against the no-op expectation 15.906 (11.459 on the "
                 "89-row synthesis subset), Wilson CI95 with Clopper-Pearson beside it, the four-way transition split and the split "
                 "by stage, behind the rendering gate verified from the sealed MODEL_REQUEST records."),
                f"No model, tokenizer, encoder or server contact: {READ_DRIVER} via {READ_WRAPPER} over the sealed manifest, trace and per-sample official scores",
                f"slurp TRAIN Fold A conversion subset {rows} (sealed RANKVIS and AGREE arms, after the seal)", "discovery", split, "no",
                "0", "0", "0.0",
                "No new speech exposure; reads sealed outputs, request records and official scores only. Prior exposure inherited in full.",
                PACKAGE + "/analysis-recipe-v1.json",
                (f"REGISTERED WITH THE FLIGHT (DRAFT, root countersignature pending; countersigned after the seal and before any "
                 f"number is read) {args.registered_at[:10]} at study commit {args.study_commit}. Recipe {recipe['recipe_id']}; "
                 f"output analysis/{read_run}. It admits nothing."),
                "",
            ]
            out.append(" | ".join(read_cells).strip())
    if not all(done.values()):
        raise SystemExit(f"flight rows not found: {done}")
    wr(LEDGER, "\n".join(out))
    print(json.dumps({"composed_config_hash": composed.config_hash, "protocol_hash": phash, "generation_plan": gen_sha,
                      "fit_plan": fit_sha, "protocol_document": protocol_sha, "recipe": recipe_sha, "read_run_id": read_run,
                      "campaign": CAMPAIGN}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
