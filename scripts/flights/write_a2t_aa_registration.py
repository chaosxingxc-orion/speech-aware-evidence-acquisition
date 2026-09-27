#!/usr/bin/env python3
"""Write cell A2T-AA's registration package from the committed configs.

Reads the three derived experiment fragments (smoke, pass A, pass B), the
frozen paired-400 roster receipt and its comparator rows, recomposes every
cell's own hashes through ``core.config.compose`` / ``protocol_hash`` exactly
as ``core.flight.cli`` does, and writes the package documents, the
preregistration note and -- with ``--append-ledger`` -- the seven unconsumed
exposure rows (one model-free roster row, three generation rows, three live
phase-fit rows). Config alone: no adapter, no split load, no lock, no
contact, and it flips nothing and mints nothing.

    python -B scripts/flights/write_a2t_aa_registration.py \\
        --study-commit 66373032 --registered-at 2026-09-27T00:40:00.000000+00:00 --append-ledger
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
if str(REPO_ROOT / "scripts" / "flights") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts" / "flights"))

from derive_a2t_aa_cells import (  # noqa: E402
    CELLS,
    COMPARATOR_RUN,
    DATASET,
    INSTRUMENT,
    DECISIONS,
    MODEL,
    ONE_FACTOR,
    PACKAGE_STEM,
    ROSTER,
    SESSION,
)
from speech_aware_evidence_acquisition.core.config import (  # noqa: E402
    compose,
    protocol_hash,
)

DATE = "2026-09-27"
PACKAGE = f"docs/readiness/{DATE}-{PACKAGE_STEM}"
PREREG = f"docs/readiness/{DATE}-{PACKAGE_STEM}-preregistration.md"
LEDGER = "docs/exposure-ledger.md"
COMPARATOR_ROWS = "docs/receipts/rosters/a2t-paired-400-v1.comparator-rows.json"
ROSTER_ROW_ID = "SAEA-SN-MF-A2T-PAIRED-400-ROSTER-V1"
DECISION_RELPATH = f"coordination/{PACKAGE_STEM}/root-admission-v1.json"
DECISION_ID = "a2t-stage3-aa-paired-400-admission-v1"
SLURP_SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"
SLURP_MODEL = "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1"
RESULTS_LEDGER = "docs/results/stage2-results-ledger.md"
BOOTSTRAP_SEED = 20260903
PRIMARY_METRIC = (
    "official Audio2Tool tool accuracy (scorer a2t-toolcall-official, the pinned release's "
    "own metrics.py; the repository scorer a2t-toolcall reported beside it), pooled over the "
    "400 rows in the natural-mixture weighting, with the equal-tier weighting beside it"
)

MODEL_TOOL = (
    "Frozen Q4_K_M decoder-only build 04ccc72a, c98304 np3 x 32768 max2048 "
    f"({MODEL}); promoted union-4000 speech packets (SAEA-A2T-NATIVE-SYSTEM-PACKETS-V1); "
    "official-protocol compact registry; direct-only phase program; no native tool authority"
)
INHERITED = (
    "Already-exposed discovery identities of the sealed union-4000 (2026-09-04 official-protocol "
    "flights, 2026-09-05 ORG-1, 2026-09-12 native-system, 2026-09-15 native-role direct and "
    "dual-store); this cell re-flies a strict subset, adds no new row and opens no split. Prior "
    "exposure is inherited in full."
)
GEOMETRY_FINDING = (
    "The last flown Audio2Tool cells (SAEA-A2T-NATIVE-ROLE-DIRECT-UNION4000-V1 and its dual-store "
    "sibling, 2026-09-15) served " + MODEL + ": -c 98304 -np 3 (three 32,768-token slots), "
    "max_tokens 2048, --no-mmproj, LLAMA_SPEECH_FEATURE_ROOT /home/chao/feat-cache/"
    "a2t-native-system-4000-packets-04ccc72a, port 8080, session serving-a2t-native-role-base-"
    "np3-max2048-v2. The resident SLURP session " + SLURP_SESSION + " serves " + SLURP_MODEL
    + ": -c 98304 -np 4 (four 24,576-token slots), max_tokens 512, LLAMA_SPEECH_FEATURE_ROOT "
    "/home/chao/feat-cache/slurp-q4km-packets-04ccc72a. FlightRuntime.serve attaches only to a "
    "session whose recorded identity (model fragment and its sha256, argv flag by flag, env) "
    "matches the cell's fragment, and the runtime refuses a speech_feature_root that disagrees "
    "with the promotion receipt's feature_root; the two sessions therefore differ in identity "
    "twice over (slot count and packet root) and NO Audio2Tool cell can attach to the resident "
    "SLURP session. Consequence: Audio2Tool cells do not interleave with SLURP cells inside one "
    "session. They fly only after the SLURP session is stopped and SAEA-Serving-A2T is resident "
    "(one geometry swap in, one back), which is why decision 69 pays the swap only when at least "
    "two Audio2Tool cells are ready -- this chain is three flights on one session."
)
PACKET_FINDING = (
    "Every one of the 400 rows already holds a promoted SpeechFeaturePacketV1 under "
    "/home/chao/feat-cache/a2t-native-system-4000-packets-04ccc72a, pinned by the sealed 2026-09-12 "
    "promotion receipt prepared/SAEA-A2T-NATIVE-SYSTEM-PACKETS-V1/promotion.json (sha256 "
    "720d81f63a1923f19893c0ee171e1ab7b47f9a946c1e62a06bdddd839243de8a) that the committed direct "
    "baseline pins; the roster builder proved 400 of 400 packet ids present. No CPU packet "
    "preparation is registered because none is owed: zero encoder contacts."
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


def sha256_file(relpath: str) -> str:
    return hashlib.sha256(Path(relpath).read_bytes()).hexdigest()


def compose_cell(key: str) -> dict:
    spec = CELLS[key]
    document = json.loads(rd(f"configs/experiment/{spec['cell']}.json"))
    cell = document["cells"][0]
    composed = compose(REPO_ROOT, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], spec["cell"])
    split = document["population"]["split_identity_hash"]
    phash = protocol_hash(composed.config_hash, composed.values["arm"], split)
    fit = composed.values["live_phase_fit"]
    if fit["run_id"] != spec["fit_run"] or fit["attempt_id"] != spec["fit_attempt"]:
        raise SystemExit(f"{key}: the composed live_phase_fit identity is not the registered one")
    if cell["run_id"] != spec["run"] or cell["attempt_id"] != spec["attempt"]:
        raise SystemExit(f"{key}: the composed cell identity is not the registered one")
    rows = int(document["population"]["count"])
    if fit["contact_cap"] != 1 + 3 * rows:
        raise SystemExit(f"{key}: live fit contact_cap {fit['contact_cap']} is not 1 + 3 x {rows}")
    return {
        "key": key,
        "spec": spec,
        "document": document,
        "cell": cell,
        "composed": composed,
        "config_hash": composed.config_hash,
        "protocol_hash": phash,
        "split": split,
        "fit": fit,
        "rows": rows,
        "caps": document["family_budget"],
        "serving_geometry": composed.values["serving_geometry"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-commit", required=True)
    parser.add_argument("--registered-at", required=True)
    parser.add_argument("--branch", default="fable/a2taa")
    parser.add_argument("--worktree", default="/home/chao/saea-worktrees/fable-a2taa")
    parser.add_argument("--append-ledger", action="store_true")
    args = parser.parse_args(argv)

    roster = json.loads(rd(ROSTER))
    comparator_rows = json.loads(rd(COMPARATOR_ROWS))
    if roster["comparator_rows"]["sha256"] != sha256_file(COMPARATOR_ROWS):
        raise SystemExit("the comparator rows file does not hash to the roster's pin")
    cells = {key: compose_cell(key) for key in ("smoke", "a", "b")}
    a, b, smoke = cells["a"], cells["b"], cells["smoke"]
    for pair in ((a, b), (b, a)):
        left, right = pair
        if left["split"] != right["split"] or left["split"] != roster["flight_split_identity_hash"]:
            raise SystemExit("pass A and pass B do not share the frozen roster identity")
    if smoke["split"] != roster["smoke_four"]["flight_split_identity_hash"]:
        raise SystemExit("the smoke does not fly the frozen smoke four")
    # Request identity across the two passes: every composed value except the
    # fit identity and the registration prose is byte-equal. The prose keys are
    # named one by one; each names the cell's own run or fit identity and none
    # of them reaches a request (the experiment fragment's cells, purpose,
    # experiment_id and own_null_pair; the baseline's live_phase_fit and
    # what_this_is; generation_budget, whose definition names the fit run id --
    # its numbers are asserted equal below).
    prose = {"live_phase_fit", "what_this_is", "cells", "purpose", "experiment_id", "own_null_pair", "generation_budget"}
    for name in set(a["composed"].values) | set(b["composed"].values):
        if name in prose:
            continue
        if a["composed"].values.get(name) != b["composed"].values.get(name):
            raise SystemExit(f"pass A and pass B differ in composed key {name!r}; they are not request-identical")
    for field in ("cap", "target"):
        if a["composed"].values["generation_budget"][field] != b["composed"].values["generation_budget"][field]:
            raise SystemExit(f"pass A and pass B differ in generation_budget.{field}")
    run_ids = {key: cells[key]["spec"]["run"] for key in cells}
    fit_ids = {key: cells[key]["spec"]["fit_run"] for key in cells}
    all_run_ids = [run_ids["smoke"], fit_ids["smoke"], run_ids["a"], fit_ids["a"], run_ids["b"], fit_ids["b"]]
    source_tree = f"studies/speech-aware-evidence-acquisition, worktree {args.worktree}, branch {args.branch}"

    # ---- the measurement declaration ------------------------------------
    def block(key: str) -> dict:
        if key == "smoke":
            return {
                "claims_benefit": False,
                "expected_effect_pp": 0.0,
                "measurement_design": "form-proof",
                "primary_metric": "none: a four-row form smoke reads no metric",
                "rows": 4,
                "note": (
                    "The four-row smoke of cell A2T-AA proves the request form, the packet plane, "
                    "the live phase fit and the seal on the Audio2Tool session before the two "
                    "400-row passes. Under instrument rule 5 four rows are a form proof by size; it "
                    "claims nothing and no number from it is a task measurement."
                ),
            }
        other = run_ids["b"] if key == "a" else run_ids["a"]
        return {
            "claims_benefit": False,
            "expected_effect_pp": 0.0,
            "measurement_design": "cross-flight-with-in-chain-replicate",
            "primary_metric": PRIMARY_METRIC,
            "replicate_run_id": other,
            "rows": 400,
            "note": (
                "The cell measures the paired-400 roster's OWN NULL and claims nothing: pass "
                + ("A" if key == "a" else "B")
                + " and its request-identical replicate "
                + other
                + " fly in the same chain on the same resident session, and the CI95 half-width "
                "of their paired difference on the official tool accuracy becomes h_A2T, the "
                "margin every later Audio2Tool interval is read at (owner decision 68). "
                "expected_effect_pp is 0.0 because a request-identical pair is registered to look "
                "for no effect; claims_benefit is false because an instrument admits nothing."
            ),
        }

    measurement = {run_ids[key]: block(key) for key in ("a", "b", "smoke")}

    # ---- registered facts ------------------------------------------------
    def identity(entry: dict) -> dict:
        return {
            "cell": entry["spec"]["cell"],
            "experiment": entry["spec"]["cell"],
            "run_id": entry["spec"]["run"],
            "attempt_id": entry["spec"]["attempt"],
            "fit_run_id": entry["spec"]["fit_run"],
            "fit_attempt_id": entry["spec"]["fit_attempt"],
            "fit_contact_cap": entry["fit"]["contact_cap"],
            "baseline_fragment": entry["cell"]["baseline_fragment"],
            "dataset_fragment": entry["cell"]["dataset_fragment"],
            "model_fragment": entry["cell"]["model_fragment"],
            "arm": entry["composed"].values["arm"],
            "policy": entry["composed"].values["policy"],
            "composed_config_hash": entry["config_hash"],
            "protocol_hash": entry["protocol_hash"],
            "split_identity_hash": entry["split"],
            "rows": entry["rows"],
            "service_session": SESSION,
            "serving_geometry": entry["serving_geometry"],
            "declares_prepared_phase_supply": "prepared_phase_supply" in entry["composed"].values,
        }

    def arithmetic(entry: dict) -> dict:
        rows = entry["rows"]
        caps = entry["caps"]
        seconds = float(roster["smoke_four"]["audio_seconds_total"]) if entry["key"] == "smoke" else float(roster["audio_seconds_total"])
        return {
            "contacts_per_row_program_ceiling": 1,
            "derivation": [
                f"generation_calls_cap = {rows} rows x 1 contact (phase-direct-only-v1: one phase, max_contacts 1, always-run-full-program) = {caps['generation_calls_cap']}, the program's exact maximum and its expectation at once",
                f"fit_endpoint_calls_cap = 1 + (2 + 1) x {rows} = {caps['fit_endpoint_calls_cap']} (core.preparation_fit.complete_phase_endpoint_count with one phase and one media packet per row); the live fit gate refuses any other contact_cap, so the baseline's live_phase_fit.contact_cap is this number to the unit",
                f"repeated_speech_audio_seconds_cap = ceil({seconds} roster seconds x 1 contact) = {caps['repeated_speech_audio_seconds_cap']}",
                f"gpu_hours_fit_inclusive = {caps['gpu_hours_fit_inclusive']}, a ceiling: the sealed direct baseline flew 4,000 contacts in 1,518.57 s of generation wall at np3 (2.634 contacts per second, 3,733 prompt tokens and 17 completion tokens per contact), so {rows} contacts cost about {rows / 2.634048545456778:.0f} s of generation plus the fit, the packet validation (about 41 packets per second) and the 36 s client initialisation",
                f"native_task_contract_calls_cap = 0: the direct-only program grants no tool authority",
                f"official_complete_scoring_jobs = {caps['official_complete_scoring_jobs']}" + (": one job over the complete manifest through core.scoring_batch at finalize, never sharded, scorers a2t-toolcall-official / a2t-toolcall-v2 / a2t-toolcall / cost" if caps["official_complete_scoring_jobs"] else ": a form smoke is sealed and inspected, never scored"),
            ],
            "expected_contacts": caps["generation_calls_cap"],
            "family_budget": caps,
            "run_cumulative": "every cap binds across ALL attempts of this run id, so the one permitted recovery re-registration spends from the same ceiling",
        }

    facts = {
        "schema": "saea-registered-facts-v1",
        "_note": (
            "Every model-free measured fact this registration rests on, and the CANONICAL "
            "stage3_measurement block scripts/checks/stage3_effect_floor_check.py resolves (a "
            "mapping of run id to block: three cells, one package). The same mapping is repeated "
            "in the preregistration's fenced json for readability; this copy has precedence."
        ),
        "registered_at_utc": args.registered_at,
        "study_commit_at_registration": args.study_commit,
        "source_tree": source_tree,
        "rows": 400,
        "stage3_measurement": measurement,
        "what_this_cell_is": (
            "Audio2Tool's own request-identical null on the paired 400: two passes of the sealed "
            "direct baseline in one chain on one resident session, read for per-row byte identity "
            "and for the CI95 half-width of their paired difference on the official tool accuracy. "
            "It is an INSTRUMENT: it claims no benefit, admits nothing and compares no mechanism."
        ),
        "roster": {
            "roster_id": roster["roster_id"],
            "count": roster["count"],
            "seed": roster["seed"],
            "selection_rule": roster["selection_rule"],
            "receipt": {"relpath": ROSTER, "sha256": sha256_file(ROSTER)},
            "flight_roster_receipt": {"relpath": roster["flight_roster_receipt"], "sha256": sha256_file(roster["flight_roster_receipt"])},
            "dataset_fragment": {"relpath": roster["dataset_fragment"], "sha256": sha256_file(roster["dataset_fragment"])},
            "comparator_rows": {"relpath": COMPARATOR_ROWS, "sha256": roster["comparator_rows"]["sha256"]},
            "split_identity_hash": roster["flight_split_identity_hash"],
            "probe_receipt_split_identity_hash": roster["probe_receipt_split_identity_hash"],
            "tier_counts": roster["tier_counts"],
            "domain_counts": roster["domain_counts"],
            "distinct_query_idx_blocks": roster["distinct_query_idx_blocks"],
            "audio_seconds_total": roster["audio_seconds_total"],
            "audio_seconds_longest_item": roster["audio_seconds_longest_item"],
            "rows_at_the_654_second_synthesis_defect": roster["rows_at_the_654_second_synthesis_defect"],
            "overlap_with_sibling_rosters": roster["overlap_with_sibling_rosters"],
            "smoke_four": roster["smoke_four"],
            "coverage": roster["coverage"],
            "exposure_row": ROSTER_ROW_ID,
            "authority": roster["authority"],
        },
        "packets": {**roster["packet_coverage"], "finding": PACKET_FINDING},
        "geometry": {
            "model_fragment": MODEL,
            "serving_geometry": a["serving_geometry"],
            "server_args": a["composed"].values["server_args"],
            "speech_feature_root": a["composed"].values["speech_feature_root"],
            "session_id": SESSION,
            "predecessor_sessions": ["serving-a2t-native-role-base-np3-max2048-v1", "serving-a2t-native-role-base-np3-max2048-v2"],
            "resident_slurp_session": SLURP_SESSION,
            "same_as_the_resident_slurp_geometry": False,
            "finding": GEOMETRY_FINDING,
            "swap_scripts": [
                "scripts/flights/batch/serving_switch_to_a2t.sh (stop the SLURP session cleanly; refuses under a flight.lock or a live driver)",
                "scripts/flights/batch/serving_task_entry_a2t.sh (Windows Scheduled Task SAEA-Serving-A2T: the resident A2T wrapper)",
                "scripts/flights/batch/serving_monitor_start_a2t.sh (SAEA-Monitor-A2T)",
                "scripts/flights/batch/a2t_wait_ready.sh (readiness wait on /health and /slots)",
                "scripts/flights/batch/serving_switch_a2t_to_slurp.sh (stop the A2T session; SAEA-Serving and SAEA-Monitor restart from Windows; slurp_wait_ready.sh)",
            ],
        },
        "comparator": {
            **{key: comparator_rows["comparator"][key] for key in ("run_id", "attempt_id", "config_hash", "protocol_hash", "run_manifest", "outputs", "scores", "session_receipt", "cost", "scorers", "rows_covered")},
            "role": comparator_rows["comparator"]["role"],
            "secondary_comparators": comparator_rows["comparator"]["secondary_comparators"],
            "how_it_is_read": (
                "REPORTED BESIDE, never a gate: each pass is joined to the sealed direct rows of the "
                "same 400 ids on request_sha256 and response_text_sha256 (a cross-campaign, "
                "cross-session A/A) and on the official per-sample scores; the null this cell "
                "registers is the IN-CHAIN pair, pass A against pass B."
            ),
        },
        "identity": {key: identity(cells[key]) for key in ("smoke", "a", "b")},
        "request_identity_proof_before_contact": {
            "composed_keys_that_differ_between_pass_a_and_pass_b": sorted(
                name for name in set(a["composed"].values) | set(b["composed"].values)
                if a["composed"].values.get(name) != b["composed"].values.get(name)
            ),
            "none_of_them_enters_a_request": True,
            "one_factor": ONE_FACTOR,
        },
        "budget_arithmetic": {key: arithmetic(cells[key]) for key in ("smoke", "a", "b")},
        "read_rule": {
            "kind": "DESCRIPTIVE; no verdict, no admission, no comparator claim",
            "primary_metric": PRIMARY_METRIC,
            "deliverable": (
                "h_A2T: the CI95 half-width of the paired per-row difference (pass B minus pass A) "
                "on the official tool accuracy, tier-stratified paired bootstrap, 10,000 draws, seed "
                f"{BOOTSTRAP_SEED} (the seed every Audio2Tool table in the results ledger already "
                "uses), in the natural-mixture weighting with the equal-tier weighting beside it; "
                "the same half-width on official exact match and on the repository scorer "
                "a2t-toolcall beside it; the count of rows whose delivered tool call is "
                "byte-identical between the passes (response_text_sha256 equal) out of 400, and "
                "the count whose request bytes are identical (request_sha256 equal), which must be "
                "400 of 400 for the pair to be read as request-identical."
            ),
            "reported_beside": [
                "per-tier table (50 rows per tier) with the paper column beside the repo column",
                "per-domain table (smart_home 306 / wearables 74 / smart_car 20), domain resolved at analysis time from the released manifests",
                f"each pass against the sealed direct rows of the same 400 ids ({COMPARATOR_RUN}): byte-identity counts and the paired official tool-accuracy delta with CI95 -- a cross-campaign A/A, reported and never a gate",
                "contacts per minute, prompt and completion tokens per contact, GPU-hours from the session monitor summary, per pass (owner decision 140: sampling throughput is first-class)",
                "parse rate and the count of rows whose response named more than one call, per pass",
            ],
            "what_it_never_is": "a benefit, an admission, a replication of a mechanism, a superiority or generalisation claim, or a test claim",
        },
        "authority_relpaths": [DECISIONS, INSTRUMENT, RESULTS_LEDGER, ROSTER, COMPARATOR_ROWS, "configs/baseline/a2t-native-role-direct-union4000-v1.json", "configs/experiment/a2t-native-role-direct-union4000-v1.json"],
        "prohibitions": [
            "No benefit, superiority, generalisation or admission claim from this cell, ever: it is an instrument.",
            "No mechanism, no knowledge supply, no tool authority, no prompt or geometry change between the passes.",
            "No flight on the resident SLURP session; the chain attaches only to " + SESSION + " and never spawns or stops it.",
            "No test-split contact, no confirmatory split, no paper-scale profile.",
            "No re-flying of the sealed direct comparator; its rows are read from the seal.",
            "No flight before root mints the decision receipt and the three cells are flipped at one commit; --allow-output-change is never passed.",
            "No number from the smoke is a task measurement.",
        ],
    }
    facts_sha = wjson(PACKAGE + "/registered-facts-v1.json", facts)

    # ---- protocol --------------------------------------------------------
    protocol = {
        "schema": "saea-registered-protocol-v1",
        "protocol_id": f"{PACKAGE_STEM}-protocol",
        "registered_at_utc": args.registered_at,
        "study_commit_at_registration": args.study_commit,
        "source_tree": source_tree,
        "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP",
        "the_question": (
            "When the sealed Audio2Tool direct baseline is flown twice, request for request, on the "
            "same 400 rows in one chain on one resident session, how far do its numbers move? That "
            "distance is the carrier's own null, and every later Audio2Tool interval is read at it."
        ),
        "one_factor": ONE_FACTOR,
        "unchanged": (
            "the baseline content (direct-only phase program, official-protocol compact registry, "
            "knowledge snapshot pin, preparation source receipts, scorers, prompt-fit multiple, "
            "whole-roster wave barrier), the model fragment and c98304 np3 x 32,768 max2048 geometry, "
            "the promoted packet root and promotion receipt, the session, the roster and its order"
        ),
        "comparator": facts["comparator"],
        "cells": {key: identity(cells[key]) for key in ("smoke", "a", "b")},
        "decision_rule_fixed_here": (
            "NONE. The read is descriptive: it delivers h_A2T and the byte-identity counts and states "
            "no verdict. Nothing is admitted, refuted or compared; the half-width is registered as "
            "the margin of every later Audio2Tool contrast on this roster (owner decision 68)."
        ),
        "read_rule": facts["read_rule"],
        "weightings": "natural mixture (50 per tier is the roster's own mixture) and equal-tier, both reported (owner decision 71)",
        "geometry_and_session": facts["geometry"],
        "packets": facts["packets"],
        "development_numbers_only": "Every number this cell will produce is a discovery-roster development number (owner decisions 28 and 86) and is never a test claim.",
        "failure_policy": a["document"]["failure_policy"],
        "model_free_proofs_landed_before_contact": {
            "roster_receipt": facts["roster"]["receipt"],
            "flight_roster_receipt": facts["roster"]["flight_roster_receipt"],
            "comparator_rows": facts["roster"]["comparator_rows"],
            "packet_coverage": {key: roster["packet_coverage"][key] for key in ("promotion_receipt", "promotion_receipt_sha256", "drawn_ids_with_a_promoted_packet", "packet_preparation_required")},
            "d1_media_identity_closure": {key: roster["coverage"][key] for key in ("d1_base_ids", "d1_union_supplement_ids", "d1_ids_outside_the_closure", "new_d1_media_supplement_required")},
            "request_identity": facts["request_identity_proof_before_contact"],
        },
        "prohibitions": facts["prohibitions"],
        "authority": (
            f"{DECISIONS} rows 67, 68, 71, 76a and 139; {INSTRUMENT} rules 3 and 6 and section 2b; "
            f"{RESULTS_LEDGER} row A2T-NULL (NOT MEASURED); owner decisions 28 and 86 (development numbers), "
            "101 (the Stage-3 algorithm label) and 140 (throughput reported beside)"
        ),
    }
    protocol_sha = wjson(PACKAGE + "/protocol-registered-v1.json", protocol)

    # ---- the plan documents ----------------------------------------------
    plan_shas: dict[str, str] = {}

    def plan_document(entry: dict, kind: str) -> dict:
        generation = kind == "generation"
        spec = entry["spec"]
        caps = entry["caps"]
        document = {
            "schema": "saea-registered-" + kind + "-plan-v1",
            "plan_kind": kind,
            "cell": spec["cell"],
            "experiment": spec["cell"],
            "composed_config_hash": entry["config_hash"],
            "execution_plan": {
                "attempt_id": spec["attempt"] if generation else spec["fit_attempt"],
                "carrier_lock_key": "audio2tool",
                "execution_profile": "bounded-discovery-probe",
                "planned_gpu_hours": caps["gpu_hours_fit_inclusive"],
                "planned_model_calls": caps["generation_calls_cap"] if generation else caps["fit_endpoint_calls_cap"],
                "planned_speech_audio_seconds": caps["repeated_speech_audio_seconds_cap"],
                "protocol_hash": entry["protocol_hash"],
                "run_id": spec["run"] if generation else spec["fit_run"],
                "schema": "saea-execution-plan-v1",
                "split_identity_hash": entry["split"],
                "split_role": "discovery",
                "study": "speech-aware-evidence-acquisition",
            },
            "expected_session_id": SESSION,
            "family_budget": caps,
            "one_factor": ONE_FACTOR,
            "preparation_base_commit": args.study_commit,
            "protocol_document": {"relpath": PACKAGE + "/protocol-registered-v1.json", "sha256": protocol_sha},
            "registered_at_utc": args.registered_at,
            "source_tree": source_tree,
            "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP",
            "unused_budget_is_not_attempt_authority": True,
        }
        if generation:
            if entry["key"] == "smoke":
                document["execution_route"] = (
                    "The batch driver's smoke path: core.flight.lease_cli --stage worker plus "
                    "core.flight.cli worker for this one cell on the resident Audio2Tool session, "
                    "then batch_inspect.py in smoke mode (4 rows, ceiling 1 per row, notool)."
                )
                document["purpose"] = spec["run"] + ": the four-row form smoke of cell A2T-AA. No score, no read."
                document["quality_read_gate"] = "None: a smoke is inspected for structure and never read for a number."
            else:
                document["execution_route"] = (
                    "Shared core.flight.cli campaign over the committed single-cell campaign plan "
                    f"configs/campaign/{spec['cell']}.json; the campaign acquires its own GenerationLease "
                    "against the resident Audio2Tool session and schedules one official score over the "
                    "complete manifest at finalize. Pass A and pass B are consecutive steps of ONE "
                    "batch-driver chain (scripts/flights/batch/batch_chain_a2taa.sh) on ONE session."
                )
                document["purpose"] = (
                    spec["run"] + ": cell A2T-AA " + spec["role"] + ", one of the two request-identical "
                    "passes whose paired difference is the Audio2Tool carrier's own null. " + protocol["decision_rule_fixed_here"]
                )
                document["quality_read_gate"] = (
                    "No read before BOTH passes' complete sealed manifests, exact ordered outputs, phase "
                    "summaries and single complete official scores exist, both attempts are FINALIZED at "
                    "the same flight commit on the same session, and request_sha256 agrees on 400 of 400 "
                    "rows. A partial manifest is never scored and never read."
                )
            document["scoring"] = (
                "One first complete official score after a successful seal; no partial score."
                if caps["official_complete_scoring_jobs"] else "No score: a form smoke."
            )
        else:
            document["attached_generation_run_id"] = spec["run"]
            document["contact_cap"] = entry["fit"]["contact_cap"]
            document["max_speech_packets"] = 1
            document["execution_route"] = (
                "The shared live phase-fit path (core.preparation_fit.build_live_phase_fit_gate) under "
                "this cell's own live_phase_fit identity, run by the same campaign or worker before its "
                "first generation wave; it tokenizes request envelopes and produces no generation."
            )
            document["purpose"] = spec["fit_run"] + ": the live phase-fit spend identity of " + spec["run"] + ". It measures request envelopes only and reads nothing."
            document["scoring"] = "No fit score."
        return document

    for key in ("smoke", "a", "b"):
        plan_shas[f"{key}-generation"] = wjson(f"{PACKAGE}/{key}-generation-plan-registered-v1.json", plan_document(cells[key], "generation"))
        plan_shas[f"{key}-fit"] = wjson(f"{PACKAGE}/{key}-fit-plan-registered-v1.json", plan_document(cells[key], "fit"))

    # ---- the analysis recipe --------------------------------------------
    recipe = {
        "schema": "saea-a2t-own-null-analysis-recipe-v1",
        "recipe_id": f"{PACKAGE_STEM}-own-null-read",
        "title": "Cell A2T-AA -- Audio2Tool's own request-identical null on the paired 400",
        "registered_at_utc": args.registered_at,
        "cell_kind": "A/A NULL -- two request-identical passes of the sealed direct baseline in one chain on one resident session; DESCRIPTIVE, no admission verdict, no comparator claim, no gate.",
        "run_ids": {"pass_a": run_ids["a"], "pass_b": run_ids["b"], "smoke": run_ids["smoke"], "fit_a": fit_ids["a"], "fit_b": fit_ids["b"], "fit_smoke": fit_ids["smoke"], "read": "SAEA-A2T-STAGE3-AA-PAIRED-400-READ-V1"},
        "roster": {"relpath": ROSTER, "roster_id": roster["roster_id"], "rows": 400, "split_identity_hash": roster["flight_split_identity_hash"], "comparator_rows": COMPARATOR_ROWS},
        "arms": {
            "pass_a": {"run_id": run_ids["a"], "attempt_id": CELLS["a"]["attempt"], "outputs_sha256": "PENDING_SEAL", "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL"},
            "pass_b": {"run_id": run_ids["b"], "attempt_id": CELLS["b"]["attempt"], "outputs_sha256": "PENDING_SEAL", "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL"},
            "sealed_direct_comparator": {key: comparator_rows["comparator"][key] for key in ("run_id", "attempt_id", "outputs", "scores", "run_manifest")},
        },
        "steps": [
            "1. Refuse unless both passes' manifests are COMPLETED at 400 rows, both attempts FINALIZED, both manifests carry the same study_commit and the same session receipt path, and each manifest's id set equals the frozen roster's ids exactly (compare the id-list identity hash, not a count).",
            "2. Request identity: join the two outputs files on sample_id and count rows whose request_sha256 is equal. The pair is read as request-identical only at 400 of 400; any other count is reported as the finding and the null is NOT registered from it.",
            "3. Byte identity: count rows whose response_text_sha256 is equal between the passes (identical of 400); report the count of rows whose official primary tool differs and whose official exact-match verdict differs.",
            f"4. Scores: read each pass's sealed scores.json (already produced ONCE per complete manifest at finalize through core.scoring_batch; nothing is re-scored). Primary: a2t-toolcall-official per-sample tool accuracy. Beside: official exact match, official parameter F1 (macro and micro), a2t-toolcall tool accuracy and exact match, a2t-toolcall-v2 ordered tool accuracy, parse rate.",
            f"5. The null: per row delta = pass B minus pass A on each metric; pooled mean delta with a tier-stratified paired bootstrap CI95 (10,000 draws, seed {BOOTSTRAP_SEED}, the row as the resampling unit within tier) in the natural-mixture weighting and in the equal-tier weighting; h_A2T = the CI95 half-width on the official tool accuracy; the same half-widths on official exact match and on a2t-toolcall beside it.",
            "6. Per-tier table (50 rows each) and per-domain table (domain resolved at analysis time from the released tier manifests, never at request time), each carrying the paper column (a2t-toolcall-official) beside the repo column (a2t-toolcall).",
            f"7. Cross-campaign context, REPORTED BESIDE and never a gate: each pass joined to the sealed direct rows of the same 400 ids ({COMPARATOR_RUN}) on request_sha256 and response_text_sha256 (identity counts) and on the official per-sample scores (paired delta with the same bootstrap); the comparator flew the same fragment bytes on a different day and session (v2 against v3).",
            "8. Throughput (owner decision 140): contacts per minute, prompt and completion tokens per contact, generation wall seconds and the session monitor summary (active seconds, mean and peak power) per pass.",
            "9. Write per_row.json (sample_id, tier, the two request and response hashes, the identity flags, the per-metric deltas; ids, flags, scores and hashes only) and null.json (the pooled numbers, both weightings, per-tier and per-domain tables, the comparator context, the throughput block, the registered h_A2T) under the analysis root; append the results-ledger row A2T-NULL with its status word MEASURED and the two half-widths.",
        ],
        "interval": {"kind": "paired bootstrap", "draws": 10000, "seed": BOOTSTRAP_SEED, "stratification": "tier", "level": "CI95", "half_width_is_the_deliverable": True},
        "decision_rule": {"rule": "NONE -- descriptive; the deliverable is h_A2T and the byte-identity counts", "output": "h_A2T (official tool accuracy), h_A2T_em (official exact match), h_A2T_repo (a2t-toolcall), each in both weightings; they become the registered margins of every later Audio2Tool contrast on this roster"},
        "output": {"analysis_root": "analysis/SAEA-A2T-STAGE3-AA-PAIRED-400-READ-V1"},
        "privacy": "No query text, transcript, gold tool, expected call, model output text or annotation is printed or persisted by the read: per_row.json and null.json carry ids, tier names, flags, scores and hashes only.",
        "claim_boundary": "No superiority, generalisation, component-causal, bar, admission or confirmatory claim of any kind. The only output is a measurement floor, valid at n = 400 on the paired 400 under the c98304 np3 x 32,768 max2048 Audio2Tool geometry with the sealed direct baseline's request form.",
        "contacts": {"model": 0, "server": 0, "encoder": 0, "tokenizer": 0, "scorer": 0, "asr": 0},
    }
    recipe_sha = wjson(PACKAGE + "/analysis-recipe-v1.json", recipe)

    caps_a = a["caps"]
    caps_s = smoke["caps"]
    seconds = float(roster["audio_seconds_total"])
    # ---- README ----------------------------------------------------------
    readme = f"""# Cell A2T-AA: Audio2Tool's own request-identical null on the paired 400

Registered before contact {args.registered_at[:10]} at study commit `{args.study_commit}`; all three cells are
**held**. Nothing here authorises a flight, a flip or an admission entry.

**Why an own null and not a mechanism.** Every Audio2Tool interval in `{RESULTS_LEDGER}` is read
against zero: row A2T-NULL says NOT MEASURED. The measurement instrument
(`{INSTRUMENT}`) shows what that costs: on SLURP two request-identical
flights of the same 625 rows differ by +1.87 pp SLU-F1 with a CI95 that excludes zero. Owner decision 68
orders the null FIRST on the paired 400 of decisions 67 and 71; decision 139 (2026-09-27) puts it on the
GPU queue; instrument rule 6 seals a roster's own null BEFORE any contrast on it. The 2026-09-04
official-protocol replication failed on seven tiers within noise and the construction pool cannot reward
the dominant lighting confusion, so no mechanism is proposed here: the instrument is established.

**The treatment is the sealed direct baseline, twice.** `a2t-native-role-direct-union4000-v1` -- the
direct-only phase program of the shared controller (`phase-direct-only-v1`) through `FlightRuntime` and
the OpenJiuwen executor, official-protocol compact registry, promoted speech packets, c98304 np3 max2048
-- flies as pass A and pass B in ONE batch-driver chain on ONE resident Audio2Tool session, after a
four-row smoke. Between the passes the only config bytes that differ are the `live_phase_fit`
identities and the `what_this_is` prose, neither of which enters a request (proved by composing both
cells: `registered-facts-v1.json` `request_identity_proof_before_contact`). No separate code path exists
for the baseline: the same harness that flies every arm flies this one.

**The roster.** `{ROSTER}` -- `A2T-PAIRED-400-V1`, 50 rows per tier over the eight tiers,
one seeded draw (seed 20260921, decision 71) by `core.roster.freeze_roster` from the sealed union-4000;
{seconds:.3f} s of speech, {roster['distinct_query_idx_blocks']} distinct query blocks, domains
{', '.join(f'{k} {v}' for k, v in sorted(roster['domain_counts'].items(), key=lambda kv: -kv[1]))};
{len(roster['rows_at_the_654_second_synthesis_defect'])} of the union's four 654-second synthesis-defect
rows kept. Every row already carries a sealed direct comparator row
(`{COMPARATOR_RUN}`), whose per-row request and response hashes are frozen in
`{COMPARATOR_ROWS}` -- never the text. Split identity `{roster['flight_split_identity_hash']}`.

**Geometry: NOT the resident SLURP geometry.** {GEOMETRY_FINDING}

**Packets: already promoted; no preparation registered.** {PACKET_FINDING}

**The read** (`analysis-recipe-v1.json`) is descriptive. Request identity first (`request_sha256` equal on
400 of 400), then per-row byte identity of the delivered tool call (identical of 400), then the pair's
paired difference on the official tool accuracy (`a2t-toolcall-official`, the repo scorer `a2t-toolcall`
beside it) with a tier-stratified paired bootstrap CI95 (10,000 draws, seed {BOOTSTRAP_SEED}) in the
natural-mixture and the equal-tier weighting; its half-width is **h_A2T**, the margin every later
Audio2Tool interval is read at. Beside it: each pass against the sealed direct rows of the same ids, and
contacts per minute (decision 140). There is no verdict and no admission.

**`stage3_measurement`.** Pass A and pass B: `cross-flight-with-in-chain-replicate`, `rows` 400,
`expected_effect_pp` 0.0, `claims_benefit` false, `replicate_run_id` the other pass. The smoke:
`form-proof`, `claims_benefit` false. `stage3_algorithm`: `none` -- an instrument carries no operator.

| cell | run id | attempt | fit run id (contact cap) | rows | composed config | protocol |
| --- | --- | --- | --- | ---: | --- | --- |
| smoke | `{run_ids['smoke']}` | `{CELLS['smoke']['attempt']}` | `{fit_ids['smoke']}` ({smoke['fit']['contact_cap']}) | 4 | `{smoke['config_hash']}` | `{smoke['protocol_hash']}` |
| pass A | `{run_ids['a']}` | `{CELLS['a']['attempt']}` | `{fit_ids['a']}` ({a['fit']['contact_cap']}) | 400 | `{a['config_hash']}` | `{a['protocol_hash']}` |
| pass B | `{run_ids['b']}` | `{CELLS['b']['attempt']}` | `{fit_ids['b']}` ({b['fit']['contact_cap']}) | 400 | `{b['config_hash']}` | `{b['protocol_hash']}` |

**Budgets, as arithmetic.** Per pass: {caps_a['generation_calls_cap']} generation contacts (400 rows x 1,
the direct-only program's exact maximum), {caps_a['fit_endpoint_calls_cap']} live-fit endpoints
(1 + 3 x 400, the count the fit gate requires), {caps_a['repeated_speech_audio_seconds_cap']} speech seconds
(one pass over the roster), {caps_a['gpu_hours_fit_inclusive']} GPU hours (a ceiling: the sealed direct
flew 4,000 contacts in 1,518.6 s at np3, so 400 cost about {400 / 2.634048545456778:.0f} s of generation),
one official complete score. Smoke: {caps_s['generation_calls_cap']} contacts, {caps_s['fit_endpoint_calls_cap']}
fit endpoints, {caps_s['repeated_speech_audio_seconds_cap']} s, {caps_s['gpu_hours_fit_inclusive']} GPU hours, no score.
Whole chain: at most 804 contacts, 2,415 fit endpoints, 1.2 GPU hours; expected about 0.15 GPU hours.

| file | what it holds |
| --- | --- |
| `../{DATE}-{PACKAGE_STEM}-preregistration.md` | the preregistration proper, including the `stage3_measurement` fence |
| `registered-facts-v1.json` | every model-free measured fact, the geometry and packet findings, and the CANONICAL `stage3_measurement` |
| `protocol-registered-v1.json` | identities, hashes, budgets, the read rule, the claim boundary |
| `smoke-generation-plan-registered-v1.json` / `smoke-fit-plan-registered-v1.json` | the smoke's two plans |
| `a-generation-plan-registered-v1.json` / `a-fit-plan-registered-v1.json` | pass A's two plans |
| `b-generation-plan-registered-v1.json` / `b-fit-plan-registered-v1.json` | pass B's two plans |
| `analysis-recipe-v1.json` | how the null is read, step by step |

**Mint, flip, swap, queue.** (1) Root mints `{DECISION_RELPATH}` (decision id `{DECISION_ID}`,
`eligible_run_ids` = the six run ids above) and countersigns the seven exposure rows. (2) Root flips all
three cells at ONE commit: `bash scripts/flights/batch/a2taa_flip_all.sh` (one `repin_cell.py --set-ready`
call over the three cells, so the shared protocol document and every plan sha are rewritten once; the
program has no supplied first phase, item E38, so no artifact is prepared). The flight commit lands in
`/home/chao/a2taa-flight-commit.txt`. (3) When the SLURP queue is idle (no `flight.lock`, no driver):
`bash scripts/flights/batch/serving_switch_to_a2t.sh`; from Windows stop `SAEA-Serving` and
`SAEA-Monitor`, register and start `SAEA-Serving-A2T` on `serving_task_entry_a2t.sh` and `SAEA-Monitor-A2T`
on `serving_monitor_start_a2t.sh`; `bash scripts/flights/batch/a2t_wait_ready.sh`. (4) Register and start
`SAEA-Batch-Driver` on `batch_chain_a2taa.sh` (steps: smoke + pass A, then pass B). (5) After the seal:
`bash scripts/flights/batch/serving_switch_a2t_to_slurp.sh`, restart `SAEA-Serving` and `SAEA-Monitor`,
`slurp_wait_ready.sh`. (6) The read, model-free, per the recipe.

**Not authorised by this package.** No flight before the receipt is minted and the cells are flipped; no
contact by this registration; no benefit or admission claim; no test-split contact; no re-flying of the
comparator; no flight on the SLURP session.
"""
    readme_sha = wr(PACKAGE + "/README.md", readme)

    # ---- the preregistration --------------------------------------------
    prereg = f"""# Cell A2T-AA: preregistration

Registered {args.registered_at[:10]} at study commit `{args.study_commit}`, before any contact, from the
sealed direct baseline's own fragments by script (decision 58). Development numbers only (owner
decisions 28 and 86); never a test claim.

## The cell

| item | value |
| --- | --- |
| question | When the sealed Audio2Tool direct baseline flies twice, request for request, on the same 400 rows in one chain on one resident session, how far do its numbers move? |
| treatment | `a2t-native-role-direct-union4000-v1` unchanged: the direct-only phase program of the shared controller, official-protocol compact registry, promoted speech packets, c98304 np3 max2048 |
| changed | the roster (400 of the same 4,000 ids), the run / attempt / live-fit identities, the ceilings rescaled to 400 rows. Between pass A and pass B only the `live_phase_fit` identities and the `what_this_is` prose differ, and neither enters a request. |
| comparator | none flown; the sealed direct rows of the same 400 ids (`{COMPARATOR_RUN}`) are reported beside, never a gate |
| in-chain replicate | pass B is pass A's replicate and pass A is pass B's; both fly in one chain on one session |
| runs | `{run_ids['smoke']}` / `{fit_ids['smoke']}`; `{run_ids['a']}` / `{fit_ids['a']}`; `{run_ids['b']}` / `{fit_ids['b']}` |
| rows | 4 (smoke), 400, 400 |
| composed config hash | smoke `{smoke['config_hash']}`; pass A `{a['config_hash']}`; pass B `{b['config_hash']}` |
| protocol hash | smoke `{smoke['protocol_hash']}`; pass A `{a['protocol_hash']}`; pass B `{b['protocol_hash']}` |
| split identity | `{roster['flight_split_identity_hash']}` (smoke `{roster['smoke_four']['flight_split_identity_hash']}`) |
| roster | `{ROSTER}` (sha256 `{facts['roster']['receipt']['sha256']}`), seed 20260921, owner decisions 67 and 71 |
| comparator rows | `{COMPARATOR_ROWS}` (sha256 `{roster['comparator_rows']['sha256']}`) |
| session | `{SESSION}` -- the Audio2Tool np3 x 32,768 session, NOT the resident SLURP np4 x 24,576 session |
| authority | {DECISIONS} rows 67, 68, 71, 76a, 139; {INSTRUMENT} rules 3 and 6; {RESULTS_LEDGER} row A2T-NULL; owner decisions 28, 86, 101, 140 |

## The read rule (fixed here)

There is no verdict and no admission. Request identity is proven first: `request_sha256` equal on 400 of
400 rows, or the pair is not read as request-identical and the count is the finding. Then, per row, byte
identity of the delivered tool call (`response_text_sha256` equal; the count identical of 400). Then the
paired difference, pass B minus pass A, on the official tool accuracy (`a2t-toolcall-official`; the repo
scorer `a2t-toolcall` beside it, official exact match beside it) with a tier-stratified paired bootstrap
CI95 (10,000 draws, seed {BOOTSTRAP_SEED}), in the natural-mixture and the equal-tier weighting. **The
CI95 half-width is h_A2T**, the margin every later Audio2Tool interval on this roster is read at (owner
decision 68). Reported beside: the per-tier and per-domain tables with the paper column beside the repo
column; each pass against the sealed direct rows of the same ids; contacts per minute and tokens per
contact (decision 140).

## The measurement declaration

```json
{json.dumps({"stage3_measurement": measurement}, indent=2, ensure_ascii=False, sort_keys=True)}
```

Both passes declare `cross-flight-with-in-chain-replicate` with `claims_benefit` false and
`expected_effect_pp` 0.0: a request-identical pair is registered to look for no effect and to deliver a
floor. The floor gate's arithmetic at n = 400 (`stage3_effect_floor_check.py --explain`): sampling
half-width 1.474 x sqrt(625 / 400) = 1.8425 pp, rule-3 admission bar 3 x sqrt(625 / 400) = 3.75 pp,
floor 3.75 pp; an expected effect of 0 is below it and that is the point, because this cell claims no
benefit and no finding is raised for a cell that claims nothing. The smoke is `form-proof` by size.

## Geometry and packets

{GEOMETRY_FINDING}

{PACKET_FINDING}

## Budgets and failure rule

Per pass: {caps_a['generation_calls_cap']} generation contacts (run-cumulative; 400 x the direct-only
program's 1-contact maximum), {caps_a['fit_endpoint_calls_cap']} live-fit endpoints (1 + 3 x 400, the count
the fit gate requires to the unit), {caps_a['repeated_speech_audio_seconds_cap']} speech seconds,
{caps_a['gpu_hours_fit_inclusive']} GPU hours, one official complete score. Smoke:
{caps_s['generation_calls_cap']} contacts, {caps_s['fit_endpoint_calls_cap']} fit endpoints,
{caps_s['repeated_speech_audio_seconds_cap']} speech seconds, {caps_s['gpu_hours_fit_inclusive']} GPU hours, no
score. Expected spend: about {400 / 2.634048545456778:.0f} s of generation wall per pass at the sealed direct's
own realised rate; the whole chain about 0.15 GPU hours against a 1.2 GPU-hour ceiling. Stop and preserve
on the first failure; a smoke failure closes the chain before pass A, a pass-A failure before pass B. AT
MOST ONE root-diagnosed recovery re-registration per run id (fresh generation AND fit identities); a second
failure closes the cell and the fix is proven on a four-row dry run.

## Prohibitions

No benefit, superiority, generalisation or admission claim from this cell, ever. No mechanism, no
knowledge supply, no tool authority, no prompt or geometry change between the passes. No flight on the
resident SLURP session. No test-split contact, no confirmatory split, no paper-scale profile. No re-flying
of the sealed comparator. No flight before root mints the decision receipt and the three cells are flipped
at one commit, and `--allow-output-change` is never passed.
"""
    prereg_sha = wr(PREREG, prereg)

    # ---- the exposure rows ----------------------------------------------
    ledger_state = "not-requested"
    if args.append_ledger:
        text = rd(LEDGER)
        if run_ids["a"] in text or ROSTER_ROW_ID in text:
            ledger_state = "already-present"
        else:
            def notes_generation(entry: dict) -> str:
                spec = entry["spec"]
                key = entry["key"]
                caps = entry["caps"]
                plan_relpath = f"{PACKAGE}/{key}-generation-plan-registered-v1.json"
                declared = (
                    "measurement_design form-proof, rows 4, expected_effect_pp 0.0, claims_benefit false"
                    if key == "smoke"
                    else "measurement_design cross-flight-with-in-chain-replicate, rows 400, expected_effect_pp 0.0, claims_benefit false, replicate_run_id "
                    + (run_ids["b"] if key == "a" else run_ids["a"])
                    + ", primary metric official Audio2Tool tool accuracy (a2t-toolcall-official, a2t-toolcall beside it)"
                )
                route = (
                    "the batch driver's smoke path (lease + worker + batch_inspect smoke)"
                    if key == "smoke"
                    else f"shared core.flight.cli campaign over configs/campaign/{spec['cell']}.json; ONE official complete score at finalize over the complete 400-row manifest through core.scoring_batch, never sharded (scorers a2t-toolcall-official / a2t-toolcall-v2 / a2t-toolcall / cost)"
                )
                return (
                    "REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) " + args.registered_at[:10]
                    + " at study commit " + args.study_commit + " by the A2T-AA registration agent (worktree "
                    + args.worktree + ", branch " + args.branch + "). This registration performs no contact and "
                    "authorises none. Plan SHA256 " + plan_shas[f"{key}-generation"] + "; attempt " + spec["attempt"]
                    + ". Protocol hash " + entry["protocol_hash"] + "; composed config " + entry["config_hash"]
                    + "; expected session " + SESSION + " (attach only, never spawn or stop; the Audio2Tool "
                    "c98304 np3 x 32768 max2048 session with the A2T packet root, NOT the resident SLURP np4 "
                    "session -- no Audio2Tool cell can attach to the SLURP session, so the chain flies only "
                    "after the swap scripts/flights/batch/serving_switch_to_a2t.sh + serving_task_entry_a2t.sh). "
                    "READINESS HELD: root mints " + DECISION_RELPATH + " (decision id " + DECISION_ID
                    + ") with the six eligible run ids " + ", ".join(all_run_ids) + " and this package's caps, then "
                    "flips the smoke, pass A and pass B at ONE commit with scripts/flights/repin_cell.py --set-ready "
                    "through scripts/flights/batch/a2taa_flip_all.sh; the program has no supplied first phase (item "
                    "E38), so no prepared artifact is created, the requirements list is empty by design and "
                    "--allow-output-change is never passed. Every hash in this row moves at the flip and the "
                    "re-pin tool rewrites it. Measurement declaration (scripts/checks/stage3_effect_floor_check.py): "
                    + declared + " -- declared at the top level of " + PACKAGE + "/registered-facts-v1.json (a mapping "
                    "of run id to block) and repeated in the preregistration fence; the cell measures the roster's "
                    "own null and claims nothing. Ceiling " + str(caps["generation_calls_cap"]) + " = " + str(entry["rows"])
                    + " rows x 1 contact (the direct-only program's exact maximum); " + str(caps["fit_endpoint_calls_cap"])
                    + " live-fit endpoints under " + spec["fit_run"] + " (1 + 3 x " + str(entry["rows"]) + ", the count the "
                    "fit gate requires); " + str(caps["repeated_speech_audio_seconds_cap"]) + " speech seconds = one pass over "
                    "the rows; " + str(caps["gpu_hours_fit_inclusive"]) + " GPU hours a ceiling: the sealed direct baseline "
                    "flew 4,000 contacts in 1,518.6 s of generation wall at np3 (2.63 contacts per second), so "
                    + str(entry["rows"]) + " contacts cost about " + f"{entry['rows'] / 2.634048545456778:.0f}"
                    + " s of generation plus fit, packet validation and client initialisation; a ceiling is a BOUND, "
                    "never a target, and budgets are run-cumulative across every attempt of a run id. Route: " + route
                    + ". Roster A2T-PAIRED-400-V1 (" + ROSTER + ", seed 20260921, owner decisions 67 and 71); packets "
                    "already promoted under SAEA-A2T-NATIVE-SYSTEM-PACKETS-V1 (400 of 400 packet ids present; zero "
                    "encoder contacts owed); comparator rows of " + COMPARATOR_RUN + " frozen in " + COMPARATOR_ROWS
                    + " and reported beside, never a gate. Stop and preserve on the first failure; AT MOST ONE "
                    "root-diagnosed recovery re-registration (fresh generation AND fit identities). No paper-scale "
                    "profile, no confirmatory split, no test-split contact, no benefit claim and no admission entry "
                    "from this cell."
                )

            def notes_fit(entry: dict) -> str:
                spec = entry["spec"]
                key = entry["key"]
                return (
                    "REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) " + args.registered_at[:10]
                    + " at study commit " + args.study_commit + " by the A2T-AA registration agent (worktree "
                    + args.worktree + ", branch " + args.branch + "). The live phase-fit spend identity of "
                    + spec["run"] + ": 1 + (2 + 1) x " + str(entry["rows"]) + " = " + str(entry["fit"]["contact_cap"])
                    + " tokenizer endpoint calls under the whole-roster wave barrier, producing no generation "
                    "(core.preparation_fit.build_live_phase_fit_gate refuses any other cap and refuses a fit identity "
                    "equal to the generation plan's). Attempt " + spec["fit_attempt"] + ". Plan document " + PACKAGE + "/"
                    + key + "-fit-plan-registered-v1.json; its composed config and protocol hashes are those of the "
                    "generation row " + spec["run"] + ", which the re-pin tool rewrites at the flip, and this row "
                    "quotes no hash of its own so that nothing here can go stale. Speech seconds and GPU hours are "
                    "the generation row's ceilings, shared and not additive (the sealed direct baseline's own "
                    "convention). Expected session " + SESSION + ". Performs no contact and authorises none."
                )

            def row(entry: dict, kind: str) -> str:
                spec = entry["spec"]
                caps = entry["caps"]
                generation = kind == "generation"
                key = entry["key"]
                scope = (
                    ("Cell A2T-AA " + spec["role"] + ": Audio2Tool's own request-identical null -- the sealed direct baseline flown on the paired 400 as one of two passes of one chain on one resident session; an instrument, no mechanism, no claim.")
                    if key != "smoke"
                    else "Cell A2T-AA four-row form smoke on the Audio2Tool session: the same fragment content as pass A on the first row of tiers 1, 2, 5 and 6 of the paired 400; no score, no read."
                ) if generation else (
                    "Cell A2T-AA " + spec["role"] + " -- live phase-fit spend identity, request envelopes only, no generation."
                )
                carrier = "audio2tool A2T-PAIRED-400-V1 (400 rows, 50 per tier, of the sealed union-4000)" if key != "smoke" else "audio2tool A2T-PAIRED-400-V1 smoke four"
                return " | ".join(
                    [
                        "",
                        args.registered_at,
                        spec["run"] if generation else spec["fit_run"],
                        "bounded-discovery-probe",
                        scope,
                        MODEL_TOOL,
                        carrier,
                        "discovery",
                        entry["split"],
                        "no",
                        str(caps["generation_calls_cap"] if generation else caps["fit_endpoint_calls_cap"]),
                        str(caps["repeated_speech_audio_seconds_cap"]),
                        str(caps["gpu_hours_fit_inclusive"]),
                        INHERITED,
                        f"{PACKAGE}/{key}-" + ("generation" if generation else "fit") + "-plan-registered-v1.json",
                        notes_generation(entry) if generation else notes_fit(entry),
                        "",
                    ]
                ).strip()

            roster_row = " | ".join(
                [
                    "",
                    args.registered_at,
                    ROSTER_ROW_ID,
                    "model-free-check",
                    "Draw and freeze the PAIRED 400 (A2T-PAIRED-400-V1): 50 rows per tier, one seeded draw (seed 20260921) by core.roster.freeze_roster from the sample ids of the sealed A2T-ORG1-UNION-4000, receipted with the sample ids and their sealed direct comparator rows (owner decisions 67 and 71). Zero model, server, encoder, tokenizer, scorer, network, GPU and paid-API contacts.",
                    "no model or tool contact; wav bytes hashed and wav headers read for duration; the sealed comparator's per-row request and response hashes copied out of its sealed outputs file, never the text",
                    "audio2tool A2T-PAIRED-400-V1 (400 rows, 50 per tier, of the sealed union-4000)",
                    "discovery",
                    roster["flight_split_identity_hash"],
                    "no",
                    "0",
                    "0",
                    "0",
                    "No new speech identity: every drawn id is an already-exposed discovery identity of the sealed union-4000 (2026-09-04, 2026-09-05, 2026-09-12 and 2026-09-15 flights). Prior exposure is inherited in full.",
                    ROSTER,
                    (
                        "REGISTERED (DRAFT, root countersignature pending) " + args.registered_at[:10] + " at study commit "
                        + args.study_commit + " by the A2T-AA registration agent (worktree " + args.worktree + ", branch "
                        + args.branch + "). Built model-free by scripts/build_a2t_paired_400_roster.py: receipt " + ROSTER
                        + " SHA256 " + facts["roster"]["receipt"]["sha256"] + "; comparator rows " + COMPARATOR_ROWS + " SHA256 "
                        + roster["comparator_rows"]["sha256"] + "; flight-roster receipt " + roster["flight_roster_receipt"]
                        + " SHA256 " + facts["roster"]["flight_roster_receipt"]["sha256"] + "; dataset fragment " + roster["dataset_fragment"]
                        + " SHA256 " + facts["roster"]["dataset_fragment"]["sha256"] + ". Measured: 400 rows, 50 per tier, "
                        + f"{seconds:.6f}" + " s of speech, longest row " + str(roster["audio_seconds_longest_item"]) + " s, "
                        + str(roster["distinct_query_idx_blocks"]) + " distinct query blocks, domains "
                        + ", ".join(f"{k} {v}" for k, v in sorted(roster["domain_counts"].items(), key=lambda kv: -kv[1]))
                        + "; every id resolves in a committed probe-sample receipt (" + str(roster["coverage"]["probe_sample_ids_covered"])
                        + " of 400), sits in the D1 identity closure (" + str(roster["coverage"]["d1_base_ids"]) + " base + "
                        + str(roster["coverage"]["d1_union_supplement_ids"]) + " union supplement) and holds a promoted speech packet "
                        "in SAEA-A2T-NATIVE-SYSTEM-PACKETS-V1 (400 of 400), so no probe view, no D1 supplement and no packet "
                        "preparation is needed; overlap with a2t-construction-800-v1 is 0 and with a2t-evo-curve-400-v1 "
                        + str(roster["overlap_with_sibling_rosters"].get("a2t-evo-curve-400-v1")) + " (reported). The smoke four are "
                        + ", ".join(roster["smoke_four"]["ids"]) + ". Offline guard: 0 outbound connection attempts. It admits nothing, "
                        "releases nothing and states no effectiveness claim."
                    ),
                    "",
                ]
            ).strip()
            header = (
                "\n## Cell A2T-AA: Audio2Tool's own request-identical null on the paired 400 (DRAFT, root countersignature pending)\n\n"
                "Seven unconsumed rows -- the model-free roster draw, the four-row smoke and its fit identity, pass A and its fit "
                "identity, pass B and its fit identity -- for the carrier's own null on A2T-PAIRED-400-V1 (owner decisions 67, 68, 71 "
                f"and 139; measurement instrument rules 3 and 6). Package {PACKAGE}. The chain flies only on the Audio2Tool session "
                f"{SESSION} after a geometry swap, never on the resident SLURP session. No row is countersigned and no row authorises a contact.\n\n"
                "| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | split role | split identity hash | consumed | calls | speech audio seconds | gpu hours | inherited exposure | artifacts | notes |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            )
            rows = [roster_row]
            for key in ("smoke", "a", "b"):
                rows.append(row(cells[key], "generation"))
                rows.append(row(cells[key], "fit"))
            for line in rows + [header]:
                if line.count("\n") > (header.count("\n") if line is header else 0):
                    raise SystemExit("a ledger row carries a newline")
            for line in rows:
                if line.count("|") != 16:
                    raise SystemExit(f"a ledger row has {line.count('|')} pipes, expected 16")
            suffix = "" if text.endswith("\n") else "\n"
            wr(LEDGER, text + suffix + header + "\n".join(rows) + "\n")
            ledger_state = "appended"

    print(
        json.dumps(
            {
                "package": PACKAGE,
                "written": {
                    PACKAGE + "/README.md": readme_sha,
                    PACKAGE + "/analysis-recipe-v1.json": recipe_sha,
                    PACKAGE + "/protocol-registered-v1.json": protocol_sha,
                    PACKAGE + "/registered-facts-v1.json": facts_sha,
                    PREREG: prereg_sha,
                    **{f"{PACKAGE}/{name}-plan-registered-v1.json": sha for name, sha in plan_shas.items()},
                },
                "exposure_ledger": ledger_state,
                "identity": {
                    key: {
                        "run_id": cells[key]["spec"]["run"],
                        "attempt_id": cells[key]["spec"]["attempt"],
                        "fit_run_id": cells[key]["spec"]["fit_run"],
                        "fit_attempt_id": cells[key]["spec"]["fit_attempt"],
                        "fit_contact_cap": cells[key]["fit"]["contact_cap"],
                        "composed_config_hash": cells[key]["config_hash"],
                        "protocol_hash": cells[key]["protocol_hash"],
                        "split_identity_hash": cells[key]["split"],
                        "rows": cells[key]["rows"],
                        "caps": cells[key]["caps"],
                    }
                    for key in ("smoke", "a", "b")
                },
                "request_identity_keys_that_differ": facts["request_identity_proof_before_contact"]["composed_keys_that_differ_between_pass_a_and_pass_b"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
