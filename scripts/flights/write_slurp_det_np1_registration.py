#!/usr/bin/env python3
"""Write cell DET's registration package from the committed configs.

Reads the derived fragments (``scripts/flights/derive_slurp_det_np1_cells.py``),
recomposes both passes' hashes through ``core.config.compose`` /
``core.config.protocol_hash``, computes the composed-config diff against the
LOCKED PLAN cell key by key and fragment by fragment, resolves both serving
profiles through ``core.session.serving.resolve_serving_profile`` (the exact
function the serving wrapper uses), and writes the package documents, the
preregistration, a DRAFT of the root-admission receipt and -- with
``--append-ledger`` -- the five DRAFT exposure rows.

Config alone: no adapter, no split load, no lock, no contact of any kind, and
it flips nothing and mints nothing. Zero model, tokenizer, encoder, scorer,
server, GPU and network contacts; no utterance text, gold label or model
output is read, printed or persisted.

    python scripts/flights/write_slurp_det_np1_registration.py \\
        --study-commit 9255ac71 --registered-at 2026-09-26T09:40:00.000000+00:00 --append-ledger
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
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
    read_fragment,
)
from speech_aware_evidence_acquisition.core.session.serving import (  # noqa: E402
    merge_server_args,
    resolve_serving_profile,
)


def _load_derive():
    path = REPO_ROOT / "scripts" / "flights" / "derive_slurp_det_np1_cells.py"
    spec = importlib.util.spec_from_file_location("derive_slurp_det_np1_cells", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


D = _load_derive()

PACKAGE = D.PACKAGE
PREREG = D.PREREG
LEDGER = "docs/exposure-ledger.md"
INSTRUMENT = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"
WITHIN_FLIGHT_NULL = "docs/results/2026-09-24-slurp-stage3-roll-aa-within-flight-null-read.md"
VAR1_EVIDENCE = "docs/results/2026-09-25-slurp-var1-complete-evidence.md"
ROLL_AA_PACKAGE = "docs/readiness/2026-09-24-slurp-stage3-roll-aa-v1"
CONFIG_PROOF = "tests/unit/test_stage3_det_np1_cells.py"
READ_DRIVER = "scripts/analysis/slurp_det_pair_read.py"
PAIRED_DRIVER = "scripts/analysis/slurp_paired_roster_read.py"

#: Decision 140's reference throughput: cell ROLL-2's sealed np4 arm.
ROLL2 = {
    "run_id": "SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-V1",
    "contacts": 8996,
    "prompt_tokens": 81435827,
    "window_utc": "16:00:01Z to 18:22:39Z",
    "wall_seconds": 8558,
}
ROLL2["contacts_per_minute"] = round(ROLL2["contacts"] / (ROLL2["wall_seconds"] / 60.0), 2)
ROLL2["prompt_tokens_per_second"] = round(ROLL2["prompt_tokens"] / ROLL2["wall_seconds"], 1)

DECISION_140 = (
    "Owner decision 140 (2026-09-26): the np1 cache-off test is authorised as a CHEAP TEST, but "
    "ADOPTION of any geometry is decided on THROUGHPUT, because future rounds need massive "
    "sampling. This cell decides a DETERMINISM question and INFORMS a THROUGHPUT one; the "
    "coordinator will not adopt np1 for sampling-heavy work on determinism alone. The read "
    "therefore reports, beside per-row byte identity, contacts per minute and prompt tokens per "
    "second for each pass at the np1 cache-off geometry -- from the sealed dispatch window "
    "(flight-receipts.json run_phases: wall_seconds, contact_window, contact_count) and the sealed "
    "generation manifest's cost block (prompt_tokens_total) -- and the same two numbers for the "
    f"resident np4 geometry from ROLL-2's sealed arm ({ROLL2['contacts']:,} contacts, "
    f"{ROLL2['prompt_tokens']:,} prompt tokens, {ROLL2['window_utc']}, {ROLL2['wall_seconds']:,} s: "
    f"{ROLL2['contacts_per_minute']} contacts per minute, {ROLL2['prompt_tokens_per_second']:,} "
    "prompt tokens per second), so the trade is one table."
)

MODEL_TOOL = (
    "Frozen Q4_K_M decoder-only, ONE 24,576-token slot (c24576 np1) with the PROMPT CACHE OFF "
    "(--no-cache-prompt), no --slot-prompt-similarity, otherwise the resident geometry's own flags "
    "(-fa on, -ctk/-ctv q8_0, -b 2048 -ub 512, -ngl 999, --cache-ram 0, --no-cache-idle-slots), the "
    "same GGUF and sha256, the same runtime receipt; promoted EVO-FOLDS-V2 speech packets; NO "
    "native tool authority on any role; prompt bytes the sealed PLAN arm's, unchanged"
)
INHERITED = (
    "TRAIN Fold A discovery rows already exposed by the sealed dual-store anchor, the released "
    "direct anchor, cells B0/B0r, B1 and its twin, B4b, B4b-rep, B5e, B7a, B7a-v2, B8b-anchor, "
    "B1-notool, PLAN, PLANr, ROLL-2, AGREE (registered) and CONV (registered); this cell adds no "
    "new row to the fold, re-flies a strict 50-row prefix of it twice and opens no split. Prior "
    "exposure is inherited in full."
)
CARRIER_SPLIT = "slurp TRAIN Fold A first-50 prefix"


def rd(path: str) -> str:
    return io.open(REPO_ROOT / path, encoding="utf-8", newline="").read()


def wr(path: str, text: str) -> str:
    target = REPO_ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    io.open(target, "w", encoding="utf-8", newline="").write(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def wjson(path: str, obj: object) -> str:
    return wr(path, json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def sha_of(path: str) -> str:
    return hashlib.sha256((REPO_ROOT / path).read_bytes()).hexdigest()


def origins(model: str, baseline: str, experiment: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for kind, name in (("model", model), ("dataset", D.DATASET_FRAGMENT),
                       ("baseline", baseline), ("experiment", experiment)):
        for key in read_fragment(REPO_ROOT, kind, name):
            out[key] = kind
    return out


def composed_diff(left, left_origins, right, right_origins) -> dict[str, object]:
    moved: dict[str, list[str]] = {"model": [], "dataset": [], "baseline": [], "experiment": []}
    values: dict[str, object] = {}
    for key in sorted(set(left.values) | set(right.values)):
        if left.values.get(key) != right.values.get(key):
            origin = right_origins.get(key) or left_origins[key]
            moved[origin].append(key)
            if key in ("serving_slots", "profile_slot_count", "server_args", "policy"):
                values[key] = {"left": left.values.get(key), "right": right.values.get(key)}
    unchanged = sorted(k for k in set(left.values) & set(right.values)
                       if left.values[k] == right.values[k])
    return {"moved_by_fragment": moved, "moved_values": values, "unchanged_keys": unchanged}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-commit", required=True, help="the registration base commit")
    parser.add_argument("--registered-at", required=True)
    parser.add_argument("--branch", default="fable/det")
    parser.add_argument("--worktree", default="/home/chao/saea-worktrees/fable-det")
    parser.add_argument("--append-ledger", action="store_true")
    args = parser.parse_args(argv)

    facts = D.roster_facts(REPO_ROOT)
    rows = facts["rows"]

    # ---- identities ---------------------------------------------------------
    cells: dict[str, dict] = {}
    composed_by_pass = {}
    for p, ident in D.PASSES.items():
        document = json.loads(rd(ident["experiment_relpath"]))
        cell = document["cells"][0]
        composed = compose(REPO_ROOT, cell["model_fragment"], cell["dataset_fragment"],
                           cell["baseline_fragment"], ident["experiment"])
        split = document["population"]["split_identity_hash"]
        if split != facts["split_identity_hash"]:
            raise SystemExit("the experiment's split identity is not the roster's")
        phash = protocol_hash(composed.config_hash, composed.values["arm"], split)
        fit = composed.values["native_contact_fit"]
        composed_by_pass[p] = composed
        cells[p] = {
            "pass": p,
            "cell_id": cell["cell_id"],
            "experiment": ident["experiment"],
            "run_id": cell["run_id"],
            "attempt_id": cell["attempt_id"],
            "fit_run_id": fit["run_id"],
            "fit_attempt_id": fit["attempt_id"],
            "baseline_fragment": cell["baseline_fragment"],
            "dataset_fragment": cell["dataset_fragment"],
            "model_fragment": cell["model_fragment"],
            "arm": composed.values["arm"],
            "composed_config_hash": composed.config_hash,
            "protocol_hash": phash,
            "split_identity_hash": split,
            "service_session": document["service_session"],
            "campaign_plan": ident["campaign_relpath"],
            "declares_prepared_phase_supply": "prepared_phase_supply" in composed.values,
            "serving_slots": composed.values["serving_slots"],
            "serving_slot_tokens": composed.values["serving_slot_tokens"],
            "policy": composed.values["policy"],
            "scorers": composed.values["scorers"],
            "native_episode_policies": {
                key: composed.values["native_episode"].get(key)
                for key in ("finite_completion_policy", "react_exhaustion_policy")
            },
            "decoding_params": composed.values["decoding_params"],
            "family_budget": document["family_budget"],
            "execution_plan": document["execution_plan"],
            "generation_budget_target": document["generation_budget"]["target"],
        }
        if cell["model_fragment"] != D.DET_MODEL or document["service_session"] != D.SESSION:
            raise SystemExit("the experiment does not name the DET model fragment and session")

    # ---- the geometry diff ----------------------------------------------------
    resident_fragment = read_fragment(REPO_ROOT, "model", D.RESIDENT_MODEL)
    det_fragment = read_fragment(REPO_ROOT, "model", D.DET_MODEL)
    fragment_moved = sorted(k for k in set(resident_fragment) | set(det_fragment)
                            if resident_fragment.get(k) != det_fragment.get(k))
    if fragment_moved != ["geometry_basis", "profile_slot_count", "server_args"]:
        raise SystemExit(f"the model fragment moves unexpected keys: {fragment_moved}")
    resident_profile = resolve_serving_profile(REPO_ROOT, D.RESIDENT_MODEL)
    det_profile = resolve_serving_profile(REPO_ROOT, D.DET_MODEL)
    baseline_a = read_fragment(REPO_ROOT, "baseline", D.PASSES["a"]["baseline"])
    merged = merge_server_args(
        det_fragment["server_args"], slots=baseline_a["serving_slots"],
        context_tokens=baseline_a["serving_slots"] * baseline_a["serving_slot_tokens"],
    )
    if merged != list(det_fragment["server_args"]):
        raise SystemExit("merge_server_args is not the identity: the two geometry halves disagree")
    plan_composed = compose(REPO_ROOT, D.RESIDENT_MODEL, D.DATASET_FRAGMENT,
                            "slurp-native-default-plan-lock-baseline-v1",
                            "slurp-native-default-plan-lock-v1")
    plan_origins = origins(D.RESIDENT_MODEL, "slurp-native-default-plan-lock-baseline-v1",
                           "slurp-native-default-plan-lock-v1")
    diffs = {}
    for p in ("a", "b"):
        det_origins = origins(D.DET_MODEL, D.PASSES[p]["baseline"], D.PASSES[p]["experiment"])
        diffs[f"pass_{p}"] = composed_diff(plan_composed, plan_origins, composed_by_pass[p], det_origins)
        moved = diffs[f"pass_{p}"]["moved_by_fragment"]
        if moved["model"] != ["geometry_basis", "profile_slot_count", "server_args"]:
            raise SystemExit(f"pass {p}: unexpected model keys moved: {moved['model']}")
        if moved["baseline"] != ["native_contact_fit", "prepared_phase_supply", "serving_slots", "what_this_is"]:
            raise SystemExit(f"pass {p}: unexpected baseline keys moved: {moved['baseline']}")
        if moved["dataset"]:
            raise SystemExit(f"pass {p}: dataset keys moved: {moved['dataset']}")
        allowed_experiment = {"cells", "date", "execution_plan", "experiment_id", "failure_policy",
                              "family_budget", "fragment_kind", "generation_budget", "population",
                              "populations", "purpose", "service_session", "stage3_algorithm"}
        if not set(moved["experiment"]) <= allowed_experiment:
            raise SystemExit(f"pass {p}: unexpected experiment keys moved: {moved['experiment']}")
    a_vs_b = composed_diff(composed_by_pass["a"],
                           origins(D.DET_MODEL, D.PASSES["a"]["baseline"], D.PASSES["a"]["experiment"]),
                           composed_by_pass["b"],
                           origins(D.DET_MODEL, D.PASSES["b"]["baseline"], D.PASSES["b"]["experiment"]))
    if a_vs_b["moved_by_fragment"] != {"model": [], "dataset": [],
                                       "baseline": ["native_contact_fit", "what_this_is"],
                                       "experiment": ["cells", "experiment_id", "fragment_kind", "purpose"]}:
        raise SystemExit(f"pass A and pass B differ in more than their identities: {a_vs_b['moved_by_fragment']}")

    geometry_diff = {
        "schema": "saea-det-geometry-diff-v1",
        "_note": (
            "The ONE experimental variable of cell DET, proved model-free at registration through the "
            "harness's own functions: the model-fragment diff, the server argv diff flag by flag (the "
            "shape core.session.serving.identity_mismatches would print), both resolved serving "
            "profiles, the proof that the baseline's serving_slots/serving_slot_tokens and the "
            "fragment's -np/-c agree (merge_server_args is the identity), and the composed-config diff "
            "of each pass against the LOCKED PLAN cell, key by key and fragment by fragment."
        ),
        "resident_model_fragment": D.RESIDENT_MODEL,
        "det_model_fragment": D.DET_MODEL,
        "model_fragment_keys_moved": fragment_moved,
        "server_argv_flag_diff": D.geometry_flag_diff(list(resident_fragment["server_args"]),
                                                       list(det_fragment["server_args"])),
        "server_args": {"resident_np4": resident_fragment["server_args"], "det_np1": det_fragment["server_args"]},
        "why_no_cache_prompt_is_explicit": (
            "llama.cpp (the pinned featcache checkout, common/common.h) defaults cache_prompt to TRUE "
            "and exposes --cache-prompt / --no-cache-prompt as a boolean pair (common/arg.cpp); the "
            "server's per-request cache_prompt field defaults to the server value "
            "(tools/server/server-schema.cpp) and this study's transport sends none, so the prompt "
            "cache is OFF only when the server is started with --no-cache-prompt. With it the server "
            "sets n_past = 0 for every request (tools/server/server-context.cpp: 'if we don't cache "
            "the prompt, we have to remove all previous tokens') and re-processes the whole prompt "
            "from an empty KV cache. --slot-prompt-similarity governs which idle slot a request is "
            "routed to by cached-prefix similarity; with one slot and no cache it has no object."
        ),
        "serving_profiles": {
            "resident_np4": {
                "serving_geometry": resident_profile["serving_geometry"],
                "extra_argv": resident_profile["extra_argv"],
                "session_role": resident_profile["session_role"],
                "runtime_receipt_relpath": resident_profile["runtime_receipt_relpath"],
                "runtime_receipt_sha256": resident_profile["runtime_receipt_sha256"],
                "model_fragment_sha256": resident_profile["model_fragment_sha256"],
                "model_root": resident_profile["model_root"],
                "server_env": resident_profile["server_env"],
            },
            "det_np1": {
                "serving_geometry": det_profile["serving_geometry"],
                "extra_argv": det_profile["extra_argv"],
                "session_role": det_profile["session_role"],
                "runtime_receipt_relpath": det_profile["runtime_receipt_relpath"],
                "runtime_receipt_sha256": det_profile["runtime_receipt_sha256"],
                "model_fragment_sha256": det_profile["model_fragment_sha256"],
                "model_root": det_profile["model_root"],
                "server_env": det_profile["server_env"],
            },
            "same_runtime_receipt": det_profile["runtime_receipt_sha256"] == resident_profile["runtime_receipt_sha256"],
            "same_server_env": det_profile["server_env"] == resident_profile["server_env"],
            "same_model_root_and_role": (
                det_profile["model_root"] == resident_profile["model_root"]
                and det_profile["session_role"] == resident_profile["session_role"]
            ),
        },
        "two_halves_of_the_geometry": {
            "baseline_serving_slots": baseline_a["serving_slots"],
            "baseline_serving_slot_tokens": baseline_a["serving_slot_tokens"],
            "fragment_np": int(det_fragment["server_args"][det_fragment["server_args"].index("-np") + 1]),
            "fragment_c": int(det_fragment["server_args"][det_fragment["server_args"].index("-c") + 1]),
            "merge_server_args_is_identity": merged == list(det_fragment["server_args"]),
            "why_both": (
                "rails.adapters.runtime_view reads serving_slots/serving_slot_tokens from the composed "
                "values as the adapter's flight-side geometry; core.flight.FlightRuntime.serve writes "
                "that geometry back over the fragment's -np/-c through merge_server_args and builds the "
                "required session identity from the result, and the dispatcher sizes its concurrency by "
                "slots (workers = slots, so this flight submits ONE request at a time). A baseline that "
                "still said serving_slots 4 would demand -np 4 -c 98304 of the resident session and be "
                "refused. The geometry therefore moves serving_slots in the baseline as well as the "
                "fragment's flags, and the composed diff below names it as the one non-bookkeeping "
                "baseline key that moves. No code change is needed to express -np 1 or the prompt cache "
                "off; the legacy speech-native PROFILE driver's KV-policy binder "
                "(core.driver.speech_native.profile_agent_kv_policy) does require --cache-prompt, but "
                "it is reached only from the saea-driver speech-native-profile CLI, never from "
                "FlightRuntime."
            ),
        },
        "composed_diff_against_plan_lock": diffs,
        "composed_diff_pass_a_vs_pass_b": a_vs_b,
        "plan_lock_composed_config_hash": plan_composed.config_hash,
    }
    geometry_sha = wjson(PACKAGE + "/geometry-diff-v1.json", geometry_diff)

    # ---- the measurement declaration -------------------------------------------
    measurement_block = {
        "claims_benefit": False,
        "expected_effect_pp": 0.0,
        "measurement_design": "form-proof",
        "primary_metric": (
            "per-row byte identity of the delivered answer between pass A and pass B (the count of "
            "identical rows out of 50), with the pair's pooled SLU-F1 and intent difference "
            "reported as descriptive numbers and, under decision 140, contacts per minute and "
            "prompt tokens per second per pass beside ROLL-2's np4 numbers"
        ),
        "rows": rows,
        "note": (
            "The cell measures REPRODUCIBILITY -- per-row byte identity of the delivered answer "
            "across two request-identical passes on a single-slot, prompt-cache-off serving geometry, "
            "and the SLU/intent difference of the pair -- and makes NO effectiveness claim. Its 50 "
            "rows are under the measurement instrument's MIN_BENEFIT_ROWS, so under rule 5 this is a "
            "form proof by size; claims_benefit is false and expected_effect_pp is 0.0 because the "
            "cell registers no effect to look for: the passes are the same request and any "
            "difference between them is the instrument, not a mechanism. It is NOT an admission "
            "request: no admission mode is declared and no harm margin is claimed. A 50-row cell "
            "cannot support a floor re-estimate; it decides only whether the 200-row re-estimate is "
            "worth flying, and (decision 140) it decides a determinism question while merely "
            "informing a throughput one."
        ),
    }
    measurement = {cells[p]["run_id"]: dict(measurement_block) for p in ("a", "b")}

    # ---- registered facts -------------------------------------------------------
    facts_doc = {
        "schema": "saea-registered-facts-v1",
        "_note": (
            "Every model-free measured fact this registration rests on, and the CANONICAL "
            "stage3_measurement block scripts/checks/stage3_effect_floor_check.py resolves (a mapping "
            "keyed by run id: both passes declare the same block). The same block is repeated in the "
            "preregistration's fenced json for readability; this copy has precedence. Every value was "
            "measured or derived MODEL-FREE at registration: the composed and protocol hashes through "
            "core.config.compose / core.config.protocol_hash, the split identity through "
            "data.splits.split_identity_hash, the roster arithmetic from the committed Fold A receipt "
            "and runtime view, the serving profiles through core.session.serving.resolve_serving_profile. "
            "Zero model, tokenizer, encoder, scorer, GPU and network contacts; no audio sample decoded."
        ),
        "registered_at_utc": args.registered_at,
        "study_commit_at_registration": args.study_commit,
        "rows": rows,
        "stage3_measurement": measurement,
        "decision_140": DECISION_140,
        "hypothesis": {
            "question": (
                "Is the programme's between-flight measurement floor an engineering artefact of the "
                "serving geometry -- greedy decoding under four-slot continuous batching with a prompt "
                "cache and a quantised KV cache -- or a property of the model's numerics on this "
                "hardware?"
            ),
            "measured_offsets_on_np4": {
                "var1_plan_vs_planr_n625": {"slu_pp": 1.87, "ci95_pp": [0.41, 3.36], "intent_pp": -1.28,
                                             "source": VAR1_EVIDENCE},
                "plan_vs_planr_fold_a_n1080": {"slu_pp": 0.17, "h_slu": 1.2485, "h_intent": 0.9943},
                "b6_pair_dev2000_added_n1000": {"slu_pp": -0.25, "h_slu": 1.2525, "h_intent": 1.1520},
                "roll_aa_within_flight_n200": {"byte_identical_share": 0.915, "byte_identical": "183 / 200",
                                                "intent_flips": 0, "h_within_slu": 0.735,
                                                "source": WITHIN_FLIGHT_NULL},
                "source": INSTRUMENT + " sections 2a-2d",
            },
            "if_all_50_repeat": (
                "the between-flight offset is an artefact of batch composition and cache state; the "
                "cross-flight bar (2.5-3.0 pp) would collapse toward the within-flight 0.735 pp or "
                "lower at this geometry, at a throughput cost decision 140 weighs separately; the "
                "coordinator scales the probe to 200 rows (a separate registration) for the floor "
                "re-estimate"
            ),
            "if_not_all_50_repeat": (
                "single-slot, cache-off serving does not make the flight reproducible: the offset is "
                "intrinsic to the model's numerics on this hardware and the programme stops hoping for "
                "a cheaper instrument along this axis"
            ),
        },
        "cells": cells,
        "geometry": {
            "det_model_fragment": D.DET_MODEL,
            "resident_model_fragment": D.RESIDENT_MODEL,
            "service_session": D.SESSION,
            "resident_service_session": D.RESIDENT_SESSION,
            "serving_geometry": det_profile["serving_geometry"],
            "server_argv_flag_diff": geometry_diff["server_argv_flag_diff"],
            "geometry_diff_document": {"relpath": PACKAGE + "/geometry-diff-v1.json", "sha256": geometry_sha},
            "one_resident_server_per_geometry": (
                "Flying this cell requires the coordinator to STOP the resident np4 session "
                f"{D.RESIDENT_SESSION} and START {D.SESSION} from {D.DET_MODEL} "
                "(scripts/flights/det/serving_task_entry_det.sh); core.session.serving refuses two "
                "resident sessions and a listening port, and a flight attaches only to a session whose "
                "identity matches flag by flag. That is why this cell queues behind the CONV probe now "
                "in the air and why the np4 session is restored afterwards."
            ),
        },
        "roster": {
            "relpath": D.ROSTER_OUT,
            "roster_id": D.ROSTER_ID,
            "sha256": sha_of(D.ROSTER_OUT),
            "rows": rows,
            "selection_rule": f"the FIRST {rows} items of {D.PARENT_ROSTER} in the parent's own order; a pure selection, no draw",
            "split_identity_hash": facts["split_identity_hash"],
            "id_list_sha256": facts["id_list_sha256"],
            "audio_seconds_total": facts["audio_seconds_total"],
            "strata": facts["strata"],
            "strata_covered": facts["strata_covered"],
            "strata_in_parent": facts["strata_in_parent"],
            "same_rows_as": f"the first {rows} rows the sealed PLAN arm {D.PARENT_RUN} flew (its populations list, the runtime view and the Fold A receipt share one order)",
        },
        "budget_arithmetic": {
            "per_pass": {
                "generation_calls_cap": facts["generation_calls_cap"],
                "fit_endpoint_calls_cap": facts["fit_endpoint_calls_cap"],
                "native_task_contract_calls_cap": facts["native_task_contract_calls_cap"],
                "repeated_speech_audio_seconds_cap": facts["repeated_speech_audio_seconds_cap"],
                "gpu_hours_fit_inclusive": facts["gpu_hours_fit_inclusive"],
                "official_complete_scoring_jobs": 1,
            },
            "derivation": [
                f"generation_calls_cap = {rows} rows x {D.CEILING} contacts per row (perception 1, solver 1, reviewer 3, planner 1, max_revisions 1 -> 1 + 2 * (1 + 3 + 1)) = {facts['generation_calls_cap']} per pass",
                f"fit_endpoint_calls_cap = 4 x {facts['generation_calls_cap']} = {facts['fit_endpoint_calls_cap']} per pass, the PLAN family's own ratio",
                f"native_task_contract_calls_cap = {rows} x 6 = {facts['native_task_contract_calls_cap']} per pass, the PLAN family's own per-row figure on a tool-free form (expected 0)",
                f"repeated_speech_audio_seconds_cap = ceil({facts['audio_seconds_total']} roster seconds x {D.CEILING}) = {facts['repeated_speech_audio_seconds_cap']} per pass",
                f"expected contacts per pass = {rows} x {D.PLAN_CONTACTS} / {D.PLAN_ROWS} = {facts['expected_contacts']} at the sealed PLAN arm's realised 5.023 per row; two passes about {2 * facts['expected_contacts']}",
                f"GPU hours: PLAN's {D.PLAN_GPU_HOURS} h / {D.PLAN_CONTACTS:,} contacts = {facts['np4_gpu_hours_per_contact']:.6f} h per contact on FOUR overlapping slots; ONE slot serves one request at a time, so up to {D.NP1_SLOWDOWN_ASSUMED:g}x per contact is assumed: expected {facts['expected_gpu_hours_at_assumed_np1_rate']} h per pass ({facts['expected_gpu_hours_at_np4_rate']} h at the np4 rate), {facts['ceiling_gpu_hours_at_assumed_np1_rate']} h at the whole contact ceiling, registered as {facts['gpu_hours_fit_inclusive']} h per pass; both figures are assumptions the flight measures (decision 140 makes the measured number a deliverable)",
                "official_complete_scoring_jobs = 1 per pass, one job over the complete 50-row manifest through core.scoring_batch, never sharded; the byte-identity read needs none of it, the descriptive SLU/intent difference does",
            ],
            "run_cumulative": "every cap binds across ALL attempts of a run id, so the one permitted recovery re-registration spends from the same ceiling",
            "whole_cell_expected": {
                "contacts": 2 * facts["expected_contacts"],
                "gpu_hours_at_assumed_np1_rate": round(2 * facts["expected_gpu_hours_at_assumed_np1_rate"], 4),
                "gpu_hours_at_np4_rate": round(2 * facts["expected_gpu_hours_at_np4_rate"], 4),
            },
        },
        "throughput_reference_np4": ROLL2,
        "what_does_not_move": {
            "against_the_plan_lock": diffs["pass_a"]["unchanged_keys"],
            "note": (
                "native_episode (role graph, both failure-mode policies, the deliver normaliser, review "
                "loop on, max_revisions 1), all three knowledge_stores with their release/snapshot pins, "
                "k, fuse and rank weights, phase_material, policy, scorers, decoding_params (temperature "
                "0, seed 20260913, max_tokens 512, id_slot per-sample), prompt_order, speech_feature_root, "
                "server_env, the task instruction template and fill, preparation_source_receipts, the "
                "speech-feature identity ids and the packet promotion receipt -- byte-identical to the "
                "locked PLAN cell (tests/unit/test_stage3_det_np1_cells.py)."
            ),
        },
        "committed_artifacts": {
            "model_fragment": {"relpath": f"configs/model/{D.DET_MODEL}.json", "sha256": sha_of(f"configs/model/{D.DET_MODEL}.json")},
            "roster": {"relpath": D.ROSTER_OUT, "sha256": sha_of(D.ROSTER_OUT)},
            **{f"pass_{p}_{kind}": {"relpath": rel, "sha256": sha_of(rel)}
               for p in ("a", "b")
               for kind, rel in (("baseline", D.PASSES[p]["baseline_relpath"]),
                                 ("experiment", D.PASSES[p]["experiment_relpath"]),
                                 ("campaign_plan", D.PASSES[p]["campaign_relpath"]))},
            "read_driver": {"relpath": READ_DRIVER, "sha256": sha_of(READ_DRIVER)},
            "sha_note": (
                "Every configs/baseline and configs/experiment hash above MOVES at the readiness flip "
                "(the re-pin writes each cell's prepared-supply pin into its baseline and the requirements "
                "into its experiment). The model fragment, roster, campaign plans and read driver do not: "
                "nothing in the flip touches them."
            ),
            "prepared_phase_supply": (
                "NONE COMMITTED, by design: the flip mints each pass's own under its own run id (item "
                "E16); pass B's output block must reproduce pass A's byte for byte, and "
                "--allow-output-change must never be passed. The requirements lists are empty because "
                "core.flight.repin._set_preparation_requirement rewrites every preparation entry."
            ),
        },
        "authority_relpaths": [INSTRUMENT, WITHIN_FLIGHT_NULL, VAR1_EVIDENCE,
                               ROLL_AA_PACKAGE + "/README.md", CONFIG_PROOF],
        "prohibitions": [
            "No effectiveness, superiority, generalisation, admission or floor-re-estimate claim from this cell: 50 rows decide only whether the 200-row re-estimate is worth flying.",
            "No adoption of the np1 geometry for sampling-heavy work on determinism alone (decision 140): adoption is decided on throughput.",
            "No test-split, Fold B or DEV contact or read.",
            "No change to any knob of the locked plan; the geometry is the one variable and it is already fixed here.",
            "No paper-scale profile.",
            "No flight before root mints the decision receipt, countersigns the five rows, flips both passes, and swaps the resident session; the resident np4 session is never touched by the registration agent.",
            "--allow-output-change is never passed.",
        ],
    }
    facts_sha = wjson(PACKAGE + "/registered-facts-v1.json", facts_doc)

    # ---- protocol ---------------------------------------------------------------
    protocol = {
        "schema": "saea-registered-protocol-v1",
        "protocol_id": "slurp-stage3-det-np1-fold-a-50-protocol-v1",
        "registered_at_utc": args.registered_at,
        "study_commit_at_registration": args.study_commit,
        "source_tree": f"studies/speech-aware-evidence-acquisition, worktree {args.worktree}, branch {args.branch}",
        "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP",
        "the_question": facts_doc["hypothesis"]["question"],
        "one_factor": (
            "The serving geometry, and nothing else: one 24,576-token slot (np1 c24576) with the prompt "
            "cache OFF (--no-cache-prompt) and no --slot-prompt-similarity, against the resident np4 "
            "c98304 prompt-cache-on geometry. In the composed config it is the model fragment's "
            "server_args / profile_slot_count / geometry_basis plus the baseline's serving_slots 4 -> 1; "
            "every other non-bookkeeping key is the locked PLAN cell's own bytes."
        ),
        "unchanged": facts_doc["what_does_not_move"]["note"],
        "cells": {p: {k: cells[p][k] for k in ("cell_id", "experiment", "run_id", "attempt_id", "fit_run_id",
                                                 "fit_attempt_id", "composed_config_hash", "protocol_hash",
                                                 "split_identity_hash", "service_session", "campaign_plan")}
                  for p in ("a", "b")},
        "rows": rows,
        "decision_140": DECISION_140,
        "decision_rule_fixed_here": (
            "DESCRIPTIVE; there is no verdict and no admission. The deliverable is a COUNT: the number of "
            f"the {rows} rows whose delivered answer (the sealed outputs row's text, whose "
            "response_text_sha256 the read re-derives) is byte-identical between pass A and pass B, "
            "reported beside the same statistic ROLL-AA produced at np4 within one flight (183 of 200, "
            "91.5 %) and the cross-flight np4 disagreement the instrument note records (about 28 % of raw "
            "outputs); the pair's pooled SLU-F1 and intent paired deltas with a CI95 by row bootstrap "
            "(10,000 draws, seed 20260915) as descriptive numbers; the intent-flip and entity-set-flip "
            "shares where the sealed per-sample scores carry the parsed prediction; and (decision 140) "
            "contacts per minute and prompt tokens per second per pass beside ROLL-2's np4 numbers, in "
            f"one table. ROUTING: {rows} of {rows} identical -> the coordinator scales to 200 rows for the "
            "floor re-estimate (a separate registration); fewer -> the offset is intrinsic and the axis "
            "closes. A 50-row cell cannot support a floor re-estimate."
        ),
        "read_recipe": {"relpath": PACKAGE + "/analysis-recipe-v1.json"},
        "development_numbers_only": "TRAIN Fold A construction rows (owner decisions 28 and 86); never a test claim.",
        "failure_policy": (
            "Stop and preserve on the first failure. AT MOST ONE root-diagnosed recovery re-registration per "
            "pass; a second failure closes the pass and the fix is proven on a four-row dry run. A "
            "resident-session identity refusal spends no contact and is not a flight failure. A pass that "
            "seals alone answers nothing: the read needs both."
        ),
        "claim_boundary": (
            "No superiority, generalisation, component-causal, bar, admission, held-out, confirmatory or "
            "paper-scale claim of any kind. A byte-identity count measures the instrument, not an effect; "
            "50 of 50 would not make a 200-row floor, and fewer would not make a defect."
        ),
        "prohibitions": facts_doc["prohibitions"],
    }
    protocol_sha = wjson(PACKAGE + "/protocol-registered-v1.json", protocol)

    # ---- the four plan documents ----------------------------------------------------
    plan_shas: dict[str, str] = {}
    for p in ("a", "b"):
        c = cells[p]
        for kind in ("generation", "fit"):
            generation = kind == "generation"
            plan_doc = {
                "schema": f"saea-registered-{kind}-plan-v1",
                "plan_kind": kind,
                "cell": c["cell_id"],
                "experiment": c["experiment"],
                "composed_config_hash": c["composed_config_hash"],
                "execution_plan": {
                    "attempt_id": c["attempt_id"] if generation else c["fit_attempt_id"],
                    "carrier_lock_key": "slurp",
                    "execution_profile": "bounded-discovery-probe",
                    "planned_gpu_hours": facts["gpu_hours_fit_inclusive"],
                    "planned_model_calls": facts["generation_calls_cap"] if generation else facts["fit_endpoint_calls_cap"],
                    "planned_speech_audio_seconds": facts["repeated_speech_audio_seconds_cap"],
                    "protocol_hash": c["protocol_hash"],
                    "run_id": c["run_id"] if generation else c["fit_run_id"],
                    "schema": "saea-execution-plan-v1",
                    "split_identity_hash": c["split_identity_hash"],
                    "split_role": "discovery",
                    "study": "speech-aware-evidence-acquisition",
                },
                "execution_route": (
                    f"Shared core.flight.cli campaign over the committed campaign plan {c['campaign_plan']}, "
                    "step " + ("1" if p == "a" else "2") + " of the two-step DET chain "
                    "(scripts/flights/det/batch_chain_det.sh) on the DET serving session; the campaign "
                    "acquires its own GenerationLease against the resident session and schedules one "
                    "official score over the complete manifest at finalize."
                    if generation else
                    "The shared core.flight.cli FIT path under this cell's own native_contact_fit ids; it "
                    "measures request envelopes and produces no generation."
                ),
                "expected_session_id": D.SESSION,
                "family_budget": c["family_budget"],
                "one_factor": protocol["one_factor"],
                "preparation_base_commit": args.study_commit,
                "prepared_phase_supply": {
                    "note": facts_doc["committed_artifacts"]["prepared_phase_supply"],
                    "relpath": f"prepared/{c['run_id']}/phase-supply-v1.json",
                    "sha256": "MINTED_AT_THE_FLIP",
                },
                "protocol_document": {"relpath": PACKAGE + "/protocol-registered-v1.json", "sha256": protocol_sha},
                "purpose": (
                    f"{c['run_id']}: cell DET pass {p.upper()}. " + protocol["decision_rule_fixed_here"]
                    if generation else
                    f"{c['fit_run_id']}: cell DET pass {p.upper()} FIT identity. It measures request envelopes only and reads nothing."
                ),
                "quality_read_gate": (
                    "No read before BOTH passes' complete sealed manifests, exact ordered outputs, native phase "
                    "summaries and single successful complete official TRAIN scores exist, and before the stop "
                    "stage of scripts/analysis/slurp_det_pair_read.py has verified both attempts FINALIZED, both "
                    f"manifests COMPLETED on the {rows}-row split identity, and every delivered text re-hashing "
                    "to its recorded digest. A partial manifest is never scored and never read."
                ),
                "registered_at_utc": args.registered_at,
                "source_tree": protocol["source_tree"],
                "status": protocol["status"],
                "unused_budget_is_not_attempt_authority": True,
            }
            rel = f"{PACKAGE}/{p}-{kind}-plan-registered-v1.json"
            plan_shas[f"{p}-{kind}"] = wjson(rel, plan_doc)

    # ---- the analysis recipe ----------------------------------------------------------
    recipe = {
        "schema": "saea-stage3-det-pair-read-recipe-v1",
        "recipe_id": "slurp-stage3-det-np1-fold-a-50-pair-read-v1",
        "title": "Cell DET -- does the locked plan repeat byte for byte on a single-slot, cache-off server?",
        "registered_at_utc": args.registered_at,
        "read_run_id": D.READ_RUN,
        "execution_profile": "model-free-check",
        "contacts": {"model": 0, "tokenizer": 0, "encoder": 0, "scorer": 0, "server": 0, "network": 0},
        "drivers": {
            "primary": {"relpath": READ_DRIVER, "sha256": sha_of(READ_DRIVER)},
            "descriptive": {"relpath": PAIRED_DRIVER, "sha256": sha_of(PAIRED_DRIVER)},
            "runbook": "scripts/flights/det/det_read.sh",
        },
        "arms": {
            "pass_a": {"run_id": cells["a"]["run_id"], "attempt_id": cells["a"]["attempt_id"],
                       "outputs_sha256": "PENDING_SEAL", "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL"},
            "pass_b": {"run_id": cells["b"]["run_id"], "attempt_id": cells["b"]["attempt_id"],
                       "outputs_sha256": "PENDING_SEAL", "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL"},
        },
        "roster": {"relpath": D.ROSTER_OUT, "sha256": sha_of(D.ROSTER_OUT), "rows": rows,
                   "split_identity_hash": facts["split_identity_hash"], "id_list_sha256": facts["id_list_sha256"]},
        "steps": [
            "1. STOP: refuse unless both attempts are FINALIZED, both manifests COMPLETED with an empty study_repo_dirt, both manifests bind the roster's split identity, both outputs files carry exactly the roster's ids, and every outputs row's delivered text re-hashes to its recorded response_text_sha256. Record both study commits (the same chain, one flight commit) and the expected session id.",
            f"2. PER ROW: the two delivered digests and byte_identical = (digest A == digest B); the count of identical rows out of {rows}; the per-stratum table (10 strata of the prefix) with that count.",
            "3. REPORTED BESIDE, never as a comparator: ROLL-AA's within-flight np4 statistic (183 of 200 byte-identical, 91.5 %, 0 intent flips) and the cross-flight np4 disagreement the instrument note records (about 28 % of raw outputs, about 5 % of intents; VAR1 PLAN vs PLANR +1.87 pp SLU).",
            "4. DESCRIPTIVE: from the sealed official per-sample scores (slurp-slu-official-train, already sealed at finalize; no scorer contact) each pass's slu_f1_f1 and scenario_action_exact per row, the paired deltas B - A, their pooled mean with CI95 by row bootstrap (10,000 draws, seed 20260915); where the per-sample rows carry the parsed prediction, the intent-flip and entity-set-flip shares with denominators. Then scripts/analysis/slurp_paired_roster_read.py (pass B against pass A on the 50-row receipt, utterance_id clustering) for the programme-standard paired blocks, for the record.",
            "5. THROUGHPUT (decision 140): for each pass, contacts per minute = contact_count / (wall_seconds / 60) and prompt tokens per second = prompt_tokens_total / wall_seconds, from the sealed flight-receipts.json run_phases receipt (wall_seconds, contact_window, contact_count) and the sealed generation manifest's cost block; beside them ROLL-2's np4 numbers (8,996 contacts, 81,435,827 prompt tokens, 16:00:01Z-18:22:39Z = 8,558 s: 63.07 contacts per minute, 9,515.8 prompt tokens per second), in ONE table. The window definitions are stated beside the table.",
            f"6. ROUTE: {rows} of {rows} identical -> the coordinator registers the 200-row re-estimate; fewer -> the offset is intrinsic and this axis closes. State in the same paragraph that a 50-row cell cannot support a floor re-estimate, that the cell decides a determinism question and informs a throughput one, and that np1 is not adopted for sampling-heavy work on determinism alone.",
        ],
        "output": {
            "analysis_root": f"analysis/{D.READ_RUN}",
            "files": ["stop.json", "per_row.json", "summary.json", "paired-roster-read/ (the descriptive driver's own files)"],
            "privacy": (
                "No utterance text, gold label, transcript or model output is printed or persisted: ids, "
                "stratum names, digests, flags, scores, counts and rates only. The delivered text is read "
                "into memory only to re-hash it against its recorded digest."
            ),
        },
        "what_is_not_here": (
            "No comparator block, no margins block, no gate, no verdict document, no frontier row and no "
            "plan_cell_read.py invocation: the pair is its own control and claims nothing."
        ),
    }
    recipe_sha = wjson(PACKAGE + "/analysis-recipe-v1.json", recipe)

    # ---- the draft root-admission receipt -----------------------------------------------
    draft = {
        "schema": "saea-campaign-decision-v1",
        "decision_id": D.DECISION_ID,
        "status": "DRAFT-NOT-MINTED",
        "_draft_note": (
            "A DRAFT written by the registration agent, in the repository, for root to mint on the data "
            "root with scripts/flights/det/det_mint_receipt.py, which sets status 'decided', stamps "
            "recorded_at_utc, re-hashes every antecedent path at mint time and refuses to overwrite. It "
            "authorises nothing while its status is not 'decided' (core.flight.campaign.declared_readiness "
            "refuses it)."
        ),
        "recorded_at_utc": None,
        "owner": "root",
        "coordinator": "Fable5.1",
        "eligible_run_ids": [cells["a"]["run_id"], cells["a"]["fit_run_id"], cells["b"]["run_id"], cells["b"]["fit_run_id"]],
        "cell_kind": (
            "Stage-3 determinism probe (owner decision 140): the locked v2.0 plan, byte-identical, flown "
            "twice in one chain on a single-slot, prompt-cache-off serving geometry; DESCRIPTIVE, yields "
            "the per-row byte-identity count and the geometry's throughput."
        ),
        "decision": (
            "Cell DET is admitted as a cheap test: the locked plan on one 24,576-token slot with the prompt "
            f"cache off, pass A then pass B, on the first {rows} rows of TRAIN Fold A; the read is "
            "DESCRIPTIVE and yields the per-row byte-identity count of the delivered answer between the "
            "passes and the geometry's contacts per minute and prompt tokens per second beside ROLL-2's. "
            "It decides a determinism question and informs a throughput one; adoption of any geometry is "
            "decided on throughput."
        ),
        "authorization_basis": (
            "Owner decision 140 (2026-09-26); the measurement instrument note " + INSTRUMENT +
            " (sections 2a-2d, rule 5); the within-flight null " + WITHIN_FLIGHT_NULL +
            "; the VAR-1 evidence " + VAR1_EVIDENCE + "; preregistration " + PREREG +
            "; owner decisions 28 and 86 (development numbers) and 101 (the Stage-3 algorithm label)."
        ),
        "antecedents": {
            "preregistration": {"path": PREREG, "sha256": None},
            "readiness_readme": {"path": PACKAGE + "/README.md", "sha256": None},
            "protocol": {"path": PACKAGE + "/protocol-registered-v1.json", "sha256": protocol_sha},
            "analysis_recipe": {"path": PACKAGE + "/analysis-recipe-v1.json", "sha256": recipe_sha},
            "geometry_diff": {"path": PACKAGE + "/geometry-diff-v1.json", "sha256": geometry_sha},
            "registered_facts": {"path": PACKAGE + "/registered-facts-v1.json", "sha256": facts_sha},
            "instrument_note": {"path": INSTRUMENT, "sha256": sha_of(INSTRUMENT)},
            "within_flight_null_read": {"path": WITHIN_FLIGHT_NULL, "sha256": sha_of(WITHIN_FLIGHT_NULL)},
            "config_proof": {"path": CONFIG_PROOF, "sha256": sha_of(CONFIG_PROOF)},
            "read_driver": {"path": READ_DRIVER, "sha256": sha_of(READ_DRIVER)},
            "registration_base_commit": args.study_commit,
            "base_cell": (
                f"the LOCKED default plan, cell PLAN ({D.PARENT_RUN}, v2.0 lock 2026-09-22): DET is that "
                "fragment byte for byte on a different serving geometry"
            ),
            "clause_comparator": "none: the pair is its own control; no admission read",
        },
        "registered_hashes": {
            "pass_a_composed_config": cells["a"]["composed_config_hash"],
            "pass_a_protocol": cells["a"]["protocol_hash"],
            "pass_b_composed_config": cells["b"]["composed_config_hash"],
            "pass_b_protocol": cells["b"]["protocol_hash"],
            "note": f"the values of the fragments exactly as committed at {args.study_commit} (readiness held, no decision requirement); repin_cell.py recomputes them at the flip.",
        },
        "prepared_phase_supply": {
            "note": "minted by scripts/flights/repin_cell.py at the flip (each pass's own prepared first-phase supply under its run id, item E16); pass B's must reproduce pass A's byte for byte; not pinned by this receipt"
        },
        "population": {
            "pass_a": {"count": rows, "partition": f"the first {rows} rows of TRAIN Fold A in roster order ({D.ROSTER_OUT}; {facts['strata_covered']} of 18 scenarios)",
                       "split_role": "discovery", "split_identity_hash": facts["split_identity_hash"]},
            "pass_b": {"count": rows, "partition": "the same rows, request-identical",
                       "split_role": "discovery", "split_identity_hash": facts["split_identity_hash"]},
            "fold_b_contact_authorized": False,
            "test_contact_authorized": False,
        },
        "service": {
            "expected_session_id": D.SESSION,
            "model_fragment": D.DET_MODEL,
            "decoder_only": True,
            "mmproj": "absent",
            "total_context": 24576,
            "slots": 1,
            "slot_tokens": 24576,
            "prompt_cache": "off (--no-cache-prompt)",
            "slot_prompt_similarity": "absent",
            "no_child_start_stop": True,
            "note": (
                f"the coordinator stops the resident np4 session {D.RESIDENT_SESSION} and starts this one "
                "(scripts/flights/det/serving_task_entry_det.sh) before launch, restores the np4 session "
                "after the read; the flight attaches only, never spawns or stops. The geometry IS the "
                "factor."
            ),
        },
        "budget": {
            "pass_a": {**facts_doc["budget_arithmetic"]["per_pass"], "expected_contacts": facts["expected_contacts"],
                       "expected_gpu_hours": facts["expected_gpu_hours_at_assumed_np1_rate"],
                       "ceiling_note": f"{D.CEILING} contacts per row = 1 + 2 x (1 + 3 + 1); GPU hours at an assumed {D.NP1_SLOWDOWN_ASSUMED:g}x np1 per-contact cost"},
            "pass_b": {**facts_doc["budget_arithmetic"]["per_pass"], "expected_contacts": facts["expected_contacts"],
                       "expected_gpu_hours": facts["expected_gpu_hours_at_assumed_np1_rate"]},
            "encoder_calls": 0,
            "asr_calls": 0,
            "paid_api_calls": 0,
            "ceilings_are_not_targets": True,
            "plan_budget_is_run_cumulative": True,
        },
        "claim_boundary": protocol["claim_boundary"],
        "failure_policy": protocol["failure_policy"],
        "not_authorized": [
            "any flight before both passes are flipped and the DET session is the resident session",
            "touching the resident np4 session by anyone but the coordinator",
            "any ASR, transcript, encoder or paid-API contact",
            "re-flying or re-scoring any sealed cell",
            "--allow-output-change on the re-pin tool",
            "any geometry, roster, prompt, store, k, fuse-policy or rank-weight change beyond the one registered geometry",
            "adopting np1 for sampling-heavy work on determinism alone (decision 140)",
            "a floor re-estimate from 50 rows; the 200-row re-estimate is a separate registration",
        ],
    }
    draft_sha = wjson(PACKAGE + "/root-admission-draft-v1.json", draft)

    # ---- README -----------------------------------------------------------------------
    flag_rows = "\n".join(
        f"| `{entry['flag']}` | {entry['resident_np4']} | {entry['det_np1']} |"
        for entry in geometry_diff["server_argv_flag_diff"]
    )
    strata_text = ", ".join(f"{k} {v}" for k, v in facts["strata"].items())
    readme = f"""# Cell DET: is the measurement floor an engineering artefact?

Registered before contact {args.registered_at[:10]} at study commit `{args.study_commit}` (worktree
`{args.worktree}`, branch `{args.branch}`); both cells are **held**. Nothing here authorises a
flight, a flip, a serving-session change or an admission entry, and the registration made zero model,
tokenizer, encoder, scorer, server, GPU and network contacts.

**The hypothesis.** The binding instrument note
[`{INSTRUMENT}`](../{INSTRUMENT.split('/', 1)[1]}) records that two **request-identical** flights of
the locked plan differ by +1.87 pp SLU at n = 625 (VAR1 PLAN vs PLANR, CI95 [+0.41, +3.36]), +0.17 at
Fold A 1,080 and -0.25 at DEV 1,000, and that even inside one flight only 91.5 % of delivered answers
are byte-identical ([`{WITHIN_FLIGHT_NULL}`](../../{WITHIN_FLIGHT_NULL}), 183 of 200). From that the
programme set a cross-flight admission bar of 2.5-3.0 pp, which no single mechanism has cleared. But
the locked arm decodes at **temperature 0** on a server running **four slots under continuous
batching with the prompt cache on and a q8_0 KV cache** -- exactly the configuration in which
llama.cpp greedy decoding is known not to be bitwise reproducible: a request's numerics depend on
which other requests share its batch and on cache state. Nobody has measured whether a **single-slot
server with the prompt cache off** makes the flight reproducible. If it does, the between-flight
offset collapses and the programme can see effects it currently cannot; if it does not, the offset is
intrinsic and the programme stops hoping.

**The cell.** The locked PLAN arm (`{D.PARENT_RUN}`), byte-identical in every knob, flown **twice
in one chain** -- pass A (`{cells['a']['run_id']}`), then pass B (`{cells['b']['run_id']}`) -- on the
**first {rows} rows of TRAIN Fold A** in roster order (the same first {rows} rows PLAN flew; {strata_text};
{facts['strata_covered']} of 18 scenarios, a stated limitation), on a **new serving geometry**
`{D.DET_MODEL}`, resident session `{D.SESSION}`. Per row the read asks one thing: are the two delivered
answers the same bytes?

**The one variable, flag by flag** (the resident `{D.RESIDENT_MODEL}` against the DET fragment;
everything not in this table is identical, including the model file and sha256, the runtime receipt,
`-fa on`, `-ctk q8_0 -ctv q8_0`, `-b 2048 -ub 512`, `-ngl 999`, `--cache-ram 0`, `--no-cache-idle-slots`,
the server_env, the decoding params, the prompt order and the speech packets):

| flag | resident np4 | DET np1 |
| --- | --- | --- |
{flag_rows}

`--no-cache-prompt` is explicit because llama.cpp defaults `cache_prompt` to **true** and the transport
sends no per-request override; with it the server sets `n_past = 0` for every request and re-processes
the whole prompt from an empty KV cache. `--slot-prompt-similarity` routes requests among idle slots by
cached-prefix similarity and has no object with one slot and no cache. The slot stays 24,576 tokens, so
prompt fit is unchanged.

**Where the geometry lives, and the composed-config proof.** The harness declares a geometry in two
places that must agree: the fragment's `-np`/`-c` (what llama-server is handed) and the baseline's
`serving_slots`/`serving_slot_tokens` (the adapter's flight-side geometry, which
`core.session.serving.merge_server_args` writes back over `-np`/`-c` at attach time and which sizes the
dispatcher's concurrency, `workers = slots`). So the derived baselines move **exactly one**
non-bookkeeping key against the PLAN lock baseline -- `serving_slots` 4 -> 1 -- and the composed diff
against the locked PLAN cell ([`geometry-diff-v1.json`](geometry-diff-v1.json)) is, fragment by fragment:
model `{{geometry_basis, profile_slot_count, server_args}}`; baseline `{{serving_slots}}` plus the per-cell
bookkeeping `{{native_contact_fit, prepared_phase_supply (dropped), what_this_is}}`; dataset nothing;
experiment the per-cell identities, budgets, population and prose only. `native_episode`,
`knowledge_stores`, `phase_material`, `policy`, `scorers`, `decoding_params`, `prompt_order`,
`server_env`, `speech_feature_root` and every other key are the PLAN cell's own bytes
(`{CONFIG_PROOF}`). Pass B differs from pass A only in its FIT identity and its prose. **No code change
is needed** to express `-np 1` or the prompt cache off: `merge_server_args` is the identity on the DET
fragment, `resolve_serving_profile` resolves one 24,576-token slot, and the only `--cache-prompt`
requirement in the tree (`core.driver.speech_native.profile_agent_kv_policy`) is reached from the legacy
`speech-native-profile` CLI, never from `FlightRuntime`.

**Declarations.** `stage3_measurement` (both run ids): `measurement_design` `form-proof`, `rows` {rows},
`claims_benefit` **false**, `expected_effect_pp` **0.0** -- the cell measures reproducibility (per-row byte
identity across two passes and the SLU/intent difference of the pair) and makes no effectiveness claim;
no `admission` mode. `stage3_algorithm` `none`: no rollout, no per-sample scoring, no credit assignment,
no update operator, no evolving store; the cell is a property of the rig, not of any algorithm.

**Decision 140.** {DECISION_140}

| geometry | contacts per minute | prompt tokens per second | source |
| --- | ---: | ---: | --- |
| np4 x 24,576, prompt cache on (resident) | {ROLL2['contacts_per_minute']} | {ROLL2['prompt_tokens_per_second']:,} | ROLL-2 sealed arm, {ROLL2['contacts']:,} contacts / {ROLL2['prompt_tokens']:,} prompt tokens / {ROLL2['wall_seconds']:,} s |
| np1 x 24,576, prompt cache off (pass A) | measured | measured | sealed `run_phases` window + generation manifest cost |
| np1 x 24,576, prompt cache off (pass B) | measured | measured | sealed `run_phases` window + generation manifest cost |

**Budgets, as arithmetic (per pass).** {facts['generation_calls_cap']} generation contacts ({rows} x the
program's own {D.CEILING}-contact ceiling, run-cumulative), {facts['fit_endpoint_calls_cap']} FIT
endpoints (4 x), {facts['native_task_contract_calls_cap']} native task-contract calls ({rows} x 6, a
tool-free form; expected 0), {facts['repeated_speech_audio_seconds_cap']} repeated speech seconds
(ceil({facts['audio_seconds_total']} x {D.CEILING})), {facts['gpu_hours_fit_inclusive']} GPU hours, one
official complete score. Expected spend about {facts['expected_contacts']} contacts per pass (PLAN's
realised 5.023 per row) and about {facts['expected_gpu_hours_at_assumed_np1_rate']} GPU hours per pass at an
assumed {D.NP1_SLOWDOWN_ASSUMED:g}x np1 per-contact cost ({facts['expected_gpu_hours_at_np4_rate']} at the np4
rate); the whole cell about {2 * facts['expected_contacts']} contacts and
{round(2 * facts['expected_gpu_hours_at_assumed_np1_rate'], 2)} GPU hours. The brief's own estimate of
about 850 contacts assumed 8.5 per row; PLAN realised 5.0.

| file | what it holds |
| --- | --- |
| `../{os.path.basename(PREREG)}` | the preregistration proper, including the `stage3_measurement` fence |
| `registered-facts-v1.json` | every model-free measured fact, and the CANONICAL `stage3_measurement` |
| `geometry-diff-v1.json` | the flag-by-flag argv diff, both serving profiles, the two-halves proof, the composed diff by fragment |
| `protocol-registered-v1.json` | identities, hashes, budgets, the read rule, the claim boundary |
| `a-generation-plan-registered-v1.json` / `a-fit-plan-registered-v1.json` | pass A's two plans |
| `b-generation-plan-registered-v1.json` / `b-fit-plan-registered-v1.json` | pass B's two plans |
| `analysis-recipe-v1.json` | the read, step by step (`scripts/analysis/slurp_det_pair_read.py`, run by `scripts/flights/det/det_read.sh`) |
| `root-admission-draft-v1.json` | the decision receipt for root to mint (`scripts/flights/det/det_mint_receipt.py`) |

**Registered identities.**

| pass | run id | FIT run id | composed config | protocol |
| --- | --- | --- | --- | --- |
| A | `{cells['a']['run_id']}` | `{cells['a']['fit_run_id']}` | `{cells['a']['composed_config_hash']}` | `{cells['a']['protocol_hash']}` |
| B | `{cells['b']['run_id']}` | `{cells['b']['fit_run_id']}` | `{cells['b']['composed_config_hash']}` | `{cells['b']['protocol_hash']}` |

Split identity `{facts['split_identity_hash']}`; id-list sha256 `{facts['id_list_sha256']}`; roster
`{D.ROSTER_OUT}`. Every configs/baseline and configs/experiment hash moves at the flip and the re-pin
tool rewrites this package.

**No committed `prepared_phase_supply`, empty requirements lists.** The flip mints each pass's own
first-phase supply under its own run id (item E16); pass B's output block must reproduce pass A's byte
for byte -- a different value means the pair is not request-identical: stop and report, never pass
`--allow-output-change`.

**Mint, flip, swap, launch, read, restore** (the coordinator; this package authorises none of it):

1. Let the CONV probe seal; confirm no flight, lease or driver process and no `locks/flight.lock`.
2. `python scripts/flights/det/det_mint_receipt.py` -- mints `{D.DECISION_RELPATH}` (decision id
   `{D.DECISION_ID}`) from the draft with the four eligible run ids; countersign the five DRAFT
   exposure rows (A, A-FIT, B, B-FIT, READ).
3. `bash scripts/flights/det/det_flip_all.sh` -- pass A then pass B through `repin_loop_generic.sh`
   (the check attaches to nothing; the np4 session may still be resident here). The last flip's commit
   is the flight commit (`/home/chao/det-flight-commit.txt`).
4. Swap the serving session: stop the Windows task that owns the np4 wrapper, `bash
   scripts/serving_session.sh stop --session-id {D.RESIDENT_SESSION}`, confirm `serving_session.sh
   resident` exits 3, the card is free and port 8080 is closed; then run
   `scripts/flights/det/serving_task_entry_det.sh` as the task action (it refuses while the np4 session
   is recorded resident) and `bash scripts/flights/det/det_wait_ready.sh`, which proves `/props`
   `total_slots` 1 / `n_ctx` 24576 and the recorded argv (`--no-cache-prompt`, no `--cache-prompt`, no
   `--slot-prompt-similarity`).
5. `bash scripts/flights/det/batch_chain_det.sh` -- two steps, pass A then pass B, `BATCH_SESSION`
   the DET session; the driver's prelaunch requires that session idle and healthy.
6. `bash scripts/flights/det/det_read.sh` once both passes are sealed.
7. Stop the DET session and restore the np4 session (`scripts/flights/batch/serving_task_entry.sh`)
   so the np4 queue resumes.

**Not authorised by this package.** No flight before the receipt is minted, the rows are
countersigned, both passes are flipped and the DET session is resident; no contact by this
registration; no test-split, Fold B or DEV contact or read; no knob change; no floor re-estimate from
50 rows; no adoption of np1 for sampling-heavy work on determinism alone.
"""
    readme_sha = wr(PACKAGE + "/README.md", readme)

    # ---- the preregistration ---------------------------------------------------------------
    prereg = f"""# Cell DET: preregistration

Registered {args.registered_at[:10]} at study commit `{args.study_commit}`, before any contact, from the sealed
PLAN lock fragments by script (decision 58; `scripts/flights/derive_slurp_det_np1_cells.py`,
`scripts/flights/write_slurp_det_np1_registration.py`). Development numbers only (owner decisions 28
and 86); never a test claim. **READINESS HELD on both cells.**

## 1. The question

Is the programme's between-flight measurement floor -- +1.87 pp SLU between two request-identical
flights at n = 625, 91.5 % byte identity even inside one flight -- an engineering artefact of the serving
geometry (four slots under continuous batching, prompt cache on, q8_0 KV cache: the configuration in
which llama.cpp greedy decoding is not bitwise reproducible) or a property of the model's numerics on
this hardware? Nobody has measured a single-slot, prompt-cache-off server. This cell does.

## 2. The cell

| item | value |
| --- | --- |
| base | the LOCKED v2.0 plan, cell PLAN (`{D.PARENT_RUN}`), byte-identical in every knob |
| the one variable | the serving geometry: one 24,576-token slot (`-np 1 -c 24576`), `--no-cache-prompt`, no `--slot-prompt-similarity`; model fragment `{D.DET_MODEL}`, session `{D.SESSION}`; in the baseline `serving_slots` 4 -> 1 (the flight-side half of the same geometry) |
| not variables | everything else: `native_episode`, `knowledge_stores`, `phase_material`, `policy`, `scorers`, `decoding_params` (temperature 0, seed 20260913, max_tokens 512), `prompt_order`, `server_env`, the model file and sha256, the runtime receipt, `-fa on`, `-ctk/-ctv q8_0`, `-b 2048 -ub 512`, `-ngl 999`, `--cache-ram 0`, `--no-cache-idle-slots`, the speech packets (`{CONFIG_PROOF}`, `geometry-diff-v1.json`) |
| design | pass A then pass B, two cells that differ only in their run/attempt/FIT identities and prose, consecutively in ONE chain on ONE resident session (the VAR1 PLAN / PLANR shape) |
| roster | the first {rows} rows of TRAIN Fold A in roster order, `{D.ROSTER_OUT}` (`{D.ROSTER_ID}`); {facts['strata_covered']} of 18 scenarios; the same first {rows} rows PLAN flew |
| runs | A `{cells['a']['run_id']}` / `{cells['a']['fit_run_id']}`; B `{cells['b']['run_id']}` / `{cells['b']['fit_run_id']}`; read `{D.READ_RUN}` |
| composed config hashes | A `{cells['a']['composed_config_hash']}`; B `{cells['b']['composed_config_hash']}` |
| protocol hashes | A `{cells['a']['protocol_hash']}`; B `{cells['b']['protocol_hash']}` |
| split identity | `{facts['split_identity_hash']}` |
| id-list sha256 | `{facts['id_list_sha256']}` |
| comparator | none: the pair is its own control; the sealed np4 answers of the same {rows} rows (PLAN) are available offline for a third, descriptive comparison |
| authority | owner decision 140; {INSTRUMENT}; {WITHIN_FLIGHT_NULL}; {VAR1_EVIDENCE}; owner decisions 28, 86 and 101 |

## 3. The read rule (fixed here)

DESCRIPTIVE; no verdict, no admission. Per row: byte identity of the delivered answer between pass A
and pass B (the sealed outputs row's `text`, whose `response_text_sha256` the read re-derives); the
count of identical rows out of {rows}; and, beside it, ROLL-AA's within-flight np4 statistic (183 of 200,
91.5 %) and the cross-flight np4 disagreement the instrument note records (about 28 % of raw outputs).
Then the pair's pooled SLU-F1 and intent paired deltas (row bootstrap, 10,000 draws, seed 20260915) as
descriptive numbers, and the intent-flip and entity-set-flip shares where the sealed per-sample scores
carry the parsed prediction. Driver `{READ_DRIVER}`, runbook `scripts/flights/det/det_read.sh`, recipe
`{PACKAGE}/analysis-recipe-v1.json`.

**Routing.** {rows} of {rows} identical -> the coordinator registers the 200-row re-estimate; fewer -> the
offset is intrinsic and this axis closes. **A 50-row cell cannot support a floor re-estimate**; it decides
only whether the 200-row re-estimate is worth flying.

## 4. Decision 140: determinism decided, throughput informed

{DECISION_140}

| geometry | contacts per minute | prompt tokens per second |
| --- | ---: | ---: |
| np4 x 24,576, prompt cache on (ROLL-2 sealed arm) | {ROLL2['contacts_per_minute']} | {ROLL2['prompt_tokens_per_second']:,} |
| np1 x 24,576, prompt cache off (pass A) | measured from the sealed dispatch window | measured |
| np1 x 24,576, prompt cache off (pass B) | measured from the sealed dispatch window | measured |

## 5. The measurement declaration

```json
{json.dumps({"stage3_measurement": measurement}, indent=2, ensure_ascii=False, sort_keys=True)}
```

`{rows}` rows is under the instrument's `MIN_BENEFIT_ROWS` of 200, so rule 5 makes this a form proof by
size: `form-proof`, `claims_benefit` false, `expected_effect_pp` 0.0. No `admission` mode is declared.
`stage3_algorithm` is `none` on both cells.

## 6. Budgets and failure rule

Per pass: {facts['generation_calls_cap']} generation contacts ({rows} x {D.CEILING}, run-cumulative),
{facts['fit_endpoint_calls_cap']} FIT endpoints, {facts['native_task_contract_calls_cap']} native
task-contract calls (tool-free form, expected 0), {facts['repeated_speech_audio_seconds_cap']} repeated
speech seconds, {facts['gpu_hours_fit_inclusive']} GPU hours, one official complete score. Expected about
{facts['expected_contacts']} contacts and about {facts['expected_gpu_hours_at_assumed_np1_rate']} GPU hours per
pass at an assumed {D.NP1_SLOWDOWN_ASSUMED:g}x np1 per-contact cost (PLAN's realised
{facts['np4_gpu_hours_per_contact']:.6f} h per contact on four slots); both assumptions are what the flight
measures. Stop and preserve on the first failure; AT MOST ONE root-diagnosed recovery re-registration per
pass; a second failure closes the pass and the fix is proven on a four-row dry run. A resident-session
identity refusal spends no contact and is not a flight failure. A pass that seals alone answers nothing.

## 7. What this registration does NOT authorise

`readiness.state` is `held` on both cells and `requirements` is empty (the flip appends the decision and
preparation requirements). No flight before root mints `{D.DECISION_RELPATH}` (decision id
`{D.DECISION_ID}`, four eligible run ids), countersigns the five DRAFT rows, flips both passes and swaps
the resident session (stop `{D.RESIDENT_SESSION}`, start `{D.SESSION}`); the registration agent never
touched the np4 session, any lock, any scheduled task or any batch script. No contact of any kind was
made. No test-split, Fold B or DEV contact or read; no knob change; no floor re-estimate from 50 rows;
no adoption of np1 for sampling-heavy work on determinism alone; `--allow-output-change` is never passed.

## 8. Claim boundary

No superiority, generalisation, component-causal, bar, admission, held-out, confirmatory or paper-scale
claim of any kind. A byte-identity count measures the instrument, not an effect; {rows} of {rows} would not
make a 200-row floor, and fewer would not make a defect.
"""
    prereg_sha = wr(PREREG, prereg)

    # ---- the exposure rows -------------------------------------------------------------------
    ledger_state = "not-requested"
    if args.append_ledger:
        text = rd(LEDGER)
        if cells["a"]["run_id"] in text:
            ledger_state = "already-present"
        else:
            def notes(p: str, kind: str) -> str:
                c = cells[p]
                attempt = c["attempt_id"] if kind == "generation" else c["fit_attempt_id"]
                return (
                    f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) {args.registered_at[:10]} "
                    f"at study commit {args.study_commit} by the DET registration agent (worktree {args.worktree}, "
                    f"branch {args.branch}). This registration performs no contact and authorises none. "
                    f"Plan SHA256 {plan_shas[f'{p}-{kind}']}; attempt {attempt}. Protocol hash {c['protocol_hash']}; "
                    f"composed config {c['composed_config_hash']}; expected session {D.SESSION} (attach only, "
                    f"never spawn or stop; the coordinator stops the resident np4 session {D.RESIDENT_SESSION} and "
                    f"starts this one from {D.DET_MODEL} before launch, and restores the np4 session after the "
                    f"read). READINESS HELD: root mints {D.DECISION_RELPATH} (decision id {D.DECISION_ID}) with the "
                    f"four eligible run ids {cells['a']['run_id']}, {cells['a']['fit_run_id']}, {cells['b']['run_id']}, "
                    f"{cells['b']['fit_run_id']} and this cell's caps, then re-pins pass A then pass B with "
                    "scripts/flights/repin_cell.py --set-ready, which mints each cell's OWN first-phase supply under "
                    "its own run id (item E16); no committed prepared_phase_supply, empty requirements lists, pass B's "
                    "supply must reproduce pass A's byte for byte, and --allow-output-change must never be passed. "
                    "Every hash in this row moves at the flip and the re-pin tool rewrites it. Measurement "
                    "declaration (scripts/checks/stage3_effect_floor_check.py): measurement_design form-proof, "
                    f"expected_effect_pp 0.0, claims_benefit false, rows {rows}, no admission mode -- declared at "
                    f"the top level of {PACKAGE}/registered-facts-v1.json and repeated in the preregistration "
                    "fence. THE ONE VARIABLE IS THE SERVING GEOMETRY: one 24,576-token slot with the prompt cache "
                    "off (-np 1 -c 24576 --no-cache-prompt, no --slot-prompt-similarity) against the resident np4 "
                    "c98304 prompt-cache-on geometry; every other non-bookkeeping key is the locked PLAN cell's "
                    f"own bytes ({PACKAGE}/geometry-diff-v1.json). The read is DESCRIPTIVE: per-row byte identity "
                    f"of the delivered answer between the two passes ({rows} of {rows} routes to a 200-row "
                    "re-estimate; fewer closes the axis), the pair's pooled SLU-F1 and intent difference as "
                    "numbers, and (owner decision 140) contacts per minute and prompt tokens per second per pass "
                    "beside ROLL-2's np4 numbers: the cell decides a determinism question and informs a "
                    "throughput one, and np1 is not adopted for sampling-heavy work on determinism alone. "
                    f"Ceiling {facts['generation_calls_cap']} = {rows} rows x {D.CEILING} contacts per row; expected "
                    f"about {facts['expected_contacts']} contacts and about "
                    f"{facts['expected_gpu_hours_at_assumed_np1_rate']} GPU hours per pass at an assumed "
                    f"{D.NP1_SLOWDOWN_ASSUMED:g}x np1 per-contact cost -- a ceiling is a BOUND, never a target, and "
                    "budgets are run-cumulative across every attempt of a run id. Shared core.flight.cli campaign "
                    f"over the committed single-cell campaign plan {c['campaign_plan']}, step "
                    + ("1" if p == "a" else "2") + " of the two-step chain scripts/flights/det/batch_chain_det.sh; "
                    f"ONE official complete score at finalize over the complete {rows}-row manifest, never sharded. "
                    "Stop and preserve on the first failure; AT MOST ONE root-diagnosed recovery re-registration. "
                    "No paper-scale profile, no confirmatory split, no test-split contact, no comparator flight, "
                    "no floor re-estimate from 50 rows and no admission entry from this cell."
                )

            def row(p: str, kind: str) -> str:
                c = cells[p]
                generation = kind == "generation"
                return " | ".join([
                    "",
                    args.registered_at,
                    c["run_id"] if generation else c["fit_run_id"],
                    "bounded-discovery-probe",
                    (
                        f"Cell DET pass {p.upper()}: the locked v2.0 plan, byte-identical, on a single-slot "
                        "prompt-cache-off serving geometry (np1 x 24,576, --no-cache-prompt), the "
                        + ("first" if p == "a" else "request-identical second")
                        + f" of two passes in one chain on the first {rows} TRAIN Fold A rows, to read per-row byte "
                        "identity of the delivered answer between the passes and the geometry's throughput "
                        "(decision 140)."
                        if generation else
                        f"Cell DET pass {p.upper()} -- FIT spend identity, request envelopes only, no generation: "
                        f"the locked plan on the np1 cache-off geometry on the same {rows} rows."
                    ),
                    MODEL_TOOL,
                    CARRIER_SPLIT,
                    "discovery",
                    c["split_identity_hash"],
                    "no",
                    str(facts["generation_calls_cap"] if generation else facts["fit_endpoint_calls_cap"]),
                    str(facts["repeated_speech_audio_seconds_cap"]),
                    str(facts["gpu_hours_fit_inclusive"]),
                    INHERITED,
                    f"{PACKAGE}/{p}-{kind}-plan-registered-v1.json",
                    notes(p, kind),
                    "",
                ]).strip()

            read_row = " | ".join([
                "",
                args.registered_at,
                D.READ_RUN,
                "model-free-check",
                (
                    f"The cell DET read: per-row byte identity of the delivered answer between pass A and pass B on "
                    f"the {rows}-row Fold A prefix, the pair's pooled SLU-F1 and intent difference from the sealed "
                    "official per-sample scores, the flip shares, and (decision 140) contacts per minute and prompt "
                    "tokens per second per pass beside ROLL-2's np4 numbers. Zero model, tokenizer, encoder, scorer, "
                    "server, GPU and network contacts: every byte read is already sealed."
                ),
                "no model or tool contact; offline arithmetic over the two sealed passes' bytes",
                CARRIER_SPLIT,
                "discovery",
                facts["split_identity_hash"],
                "no",
                "0",
                "0",
                "0",
                "No new speech exposure: every byte read was already exposed by the two DET passes. Prior exposure inherited in full.",
                f"{PACKAGE}/analysis-recipe-v1.json",
                (
                    f"REGISTERED BEFORE RESULT READING (DRAFT, root countersignature pending) {args.registered_at[:10]} "
                    f"at study commit {args.study_commit}. Driver {READ_DRIVER} (sha256 {sha_of(READ_DRIVER)}) through "
                    "scripts/flights/det/det_read.sh, then scripts/analysis/slurp_paired_roster_read.py for the "
                    "programme-standard paired blocks; analysis root analysis/" + D.READ_RUN + ". It constructs no "
                    "ExecutionPlan, reserves no contact and authorises nothing; it exists because a read is registered "
                    "before its result is read, even when it is model-free. No utterance text, gold label, transcript "
                    "or model output is printed or persisted: ids, digests, flags, scores, counts and rates only. "
                    "DESCRIPTIVE: no verdict, no admission, no floor re-estimate from 50 rows."
                ),
                "",
            ]).strip()

            header = (
                "\n## Cell DET: the single-slot, prompt-cache-off determinism probe of the locked plan "
                "(DRAFT, root countersignature pending)\n\n"
                f"Four unconsumed flight rows -- pass A, pass B and their FIT spend identities -- and one model-free "
                f"read row for the locked v2.0 plan flown twice in one chain on the first {rows} rows of TRAIN Fold A "
                f"({D.ROSTER_OUT}) on a NEW serving geometry: one 24,576-token slot with the prompt cache off "
                f"({D.DET_MODEL}, session {D.SESSION}). The geometry is the one variable; every other "
                f"non-bookkeeping key is the sealed PLAN cell's own bytes ({PACKAGE}/geometry-diff-v1.json). Owner "
                f"decision 140: determinism decided, throughput informed, adoption on throughput. Authority "
                f"{INSTRUMENT} and {WITHIN_FLIGHT_NULL}. No row is countersigned and none authorises a contact; "
                "flying them requires the coordinator to stop the resident np4 session and start the DET one.\n\n"
                "| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | "
                "split role | split identity hash | consumed | calls | speech audio seconds | gpu hours | "
                "inherited exposure | artifacts | notes |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            )
            suffix = "" if text.endswith("\n") else "\n"
            wr(LEDGER, text + suffix + header
               + row("a", "generation") + "\n" + row("a", "fit") + "\n"
               + row("b", "generation") + "\n" + row("b", "fit") + "\n"
               + read_row + "\n")
            ledger_state = "appended"

    print(json.dumps({
        "package": PACKAGE,
        "written": {
            PACKAGE + "/README.md": readme_sha,
            PACKAGE + "/analysis-recipe-v1.json": recipe_sha,
            PACKAGE + "/geometry-diff-v1.json": geometry_sha,
            PACKAGE + "/protocol-registered-v1.json": protocol_sha,
            PACKAGE + "/registered-facts-v1.json": facts_sha,
            PACKAGE + "/root-admission-draft-v1.json": draft_sha,
            **{f"{PACKAGE}/{k}-plan-registered-v1.json": v for k, v in plan_shas.items()},
            PREREG: prereg_sha,
        },
        "exposure_ledger": ledger_state,
        "identities": {p: {k: cells[p][k] for k in ("run_id", "fit_run_id", "attempt_id", "fit_attempt_id",
                                                     "composed_config_hash", "protocol_hash", "split_identity_hash")}
                       for p in ("a", "b")},
        "server_argv_flag_diff": geometry_diff["server_argv_flag_diff"],
        "composed_diff_pass_a_vs_plan": diffs["pass_a"]["moved_by_fragment"],
        "composed_diff_pass_a_vs_pass_b": a_vs_b["moved_by_fragment"],
        "throughput_reference_np4": ROLL2,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
