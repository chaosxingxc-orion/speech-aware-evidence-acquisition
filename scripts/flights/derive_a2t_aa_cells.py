#!/usr/bin/env python3
"""Derive cell A2T-AA -- Audio2Tool's own request-identical null -- from the
sealed direct baseline's own fragments (decision 58: script-derived
registrations).

WHAT THE CELL IS FOR. Every Audio2Tool interval in the results ledger is read
against ZERO because the carrier has no measured null
(``docs/results/stage2-results-ledger.md``, row A2T-NULL: NOT MEASURED). The
measurement instrument note shows why that is not a detail: on SLURP two
request-identical flights of the same 625 rows differ by +1.87 pp with a CI95
that excludes zero. Owner decision 68 orders the null FIRST, on the paired 400
of decisions 67 and 71; decision 139 puts it on the GPU queue; instrument rule
6 seals a roster's own null BEFORE any contrast on it.

NO MECHANISM. The treatment is the sealed direct baseline
``configs/baseline/a2t-native-role-direct-union4000-v1.json`` -- the
direct-only phase program (``phase-direct-only-v1``) of the shared controller
through ``FlightRuntime`` and the OpenJiuwen executor, the official-protocol
compact registry, promoted speech packets, c98304 np3 max2048 -- flown TWICE
as one chain on one resident session (pass A, pass B) on the paired 400.
Exactly four things differ from the sealed direct's fragments, none of which
enters a request: the roster (400 of the same 4,000 ids), the run / attempt /
live-fit identities, the ceilings rescaled to 400 rows, and the readiness and
Stage-3 declarations.

WHY THREE BASELINE FILES. ``live_phase_fit`` lives in the baseline and binds
one fit journal to one generation attempt: ``core.preparation_fit
.build_live_phase_fit_gate`` refuses a fit identity equal to the generation
plan's, refuses a ``contact_cap`` other than ``1 + (2 + 1) x rows`` to the
unit, and a journaled fit cannot be retried under the same identity. So the
smoke, pass A and pass B each carry their own baseline, differing ONLY in the
``live_phase_fit`` block and the ``what_this_is`` prose.

This script writes CONFIG ONLY: three baselines, three experiment fragments
and two campaign plans. It performs no contact, writes no ledger row, mints
no decision receipt and flips nothing.

    python -B scripts/flights/derive_a2t_aa_cells.py --date 2026-09-27
"""

from __future__ import annotations

import argparse
import io
import json
import math
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

PARENT_BASELINE = "configs/baseline/a2t-native-role-direct-union4000-v1.json"
PARENT_EXPERIMENT = "configs/experiment/a2t-native-role-direct-union4000-v1.json"
ROSTER = "docs/receipts/rosters/a2t-paired-400-v1.json"
DATASET = "audio2tool-paired-400"
MODEL = "q4km-mmproj-free-a2t-native-role-np3-max2048-v1"
SESSION = "serving-a2t-native-role-base-np3-max2048-v3"
COMPARATOR_RUN = "SAEA-A2T-NATIVE-ROLE-DIRECT-UNION4000-V1"
PACKAGE_STEM = "a2t-stage3-aa-paired-400-v1"
DECISIONS = "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md"
INSTRUMENT = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"

#: The direct-only phase program makes exactly one contact per row.
CONTACTS_PER_ROW = 1
#: ``core.preparation_fit.complete_phase_endpoint_count(1, rows, media_count=1)``.
FIT_ENDPOINTS = lambda rows: 1 * (1 + (2 + 1) * rows)  # noqa: E731
#: The sealed direct baseline's realised generation rate on the union-4000
#: (flight-receipts.json, stage run_phases): 4,000 contacts in 1,518.57 s.
SEALED_CONTACTS_PER_SECOND = 4000 / 1518.5748975276947

CELLS = {
    "a": {
        "cell": "a2t-stage3-aa-paired-400-a-v1",
        "run": "SAEA-A2T-STAGE3-AA-PAIRED-400-A-V1",
        "fit_run": "SAEA-A2T-STAGE3-AA-PAIRED-400-A-FIT-V1",
        "attempt": "attempt-a2t-stage3-aa-paired-400-a-generation-v1",
        "fit_attempt": "attempt-a2t-stage3-aa-paired-400-a-fit-v1",
        "gpu_hours": 0.5,
        "scoring_jobs": 1,
        "role": "pass A",
    },
    "b": {
        "cell": "a2t-stage3-aa-paired-400-b-v1",
        "run": "SAEA-A2T-STAGE3-AA-PAIRED-400-B-V1",
        "fit_run": "SAEA-A2T-STAGE3-AA-PAIRED-400-B-FIT-V1",
        "attempt": "attempt-a2t-stage3-aa-paired-400-b-generation-v1",
        "fit_attempt": "attempt-a2t-stage3-aa-paired-400-b-fit-v1",
        "gpu_hours": 0.5,
        "scoring_jobs": 1,
        "role": "pass B",
    },
    "smoke": {
        "cell": "a2t-stage3-aa-paired-400-smoke-4-v1",
        "run": "SAEA-A2T-STAGE3-AA-PAIRED-400-SMOKE-4-V1",
        "fit_run": "SAEA-A2T-STAGE3-AA-PAIRED-400-SMOKE-4-FIT-V1",
        "attempt": "attempt-a2t-stage3-aa-paired-400-smoke-4-generation-v1",
        "fit_attempt": "attempt-a2t-stage3-aa-paired-400-smoke-4-fit-v1",
        "gpu_hours": 0.2,
        "scoring_jobs": 0,
        "role": "four-row smoke",
    },
}

STAGE3_ALGORITHM_NOTE = (
    "This cell carries NO training-free RL operator and says so explicitly: it is the "
    "carrier's own measurement instrument -- two request-identical passes of the sealed "
    "direct baseline -- with no rollout, no per-sample scoring, no credit assignment, no "
    "update operator, no evolving store and no mechanism. It exists so that every later "
    "Audio2Tool cell, including the Audio2Tool instance of the locked families, is read at "
    "a measured margin rather than against zero (owner decision 68; instrument rule 6)."
)

ONE_FACTOR = (
    "None. The two passes are request-identical by construction: the same baseline "
    "content as the sealed direct SAEA-A2T-NATIVE-ROLE-DIRECT-UNION4000-V1 (the direct-only "
    "phase program of the shared controller, official-protocol compact registry, the "
    "same promoted speech packets, the same knowledge snapshot pin, the same scorers), the "
    "same model fragment and c98304 np3 max2048 geometry, the same resident session, the "
    "same 400 rows in the same order. Between pass A and pass B the only config bytes that "
    "differ are the live_phase_fit identities and the what_this_is prose, neither of which "
    "enters a request; between the passes and the sealed direct, the roster (400 of the "
    "same 4,000 ids) and the ceilings rescaled to it."
)


def rd(path: str) -> str:
    return io.open(path, encoding="utf-8", newline="").read()


def wr(path: str, text: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def dump_like(raw: str, obj: object) -> str:
    match = re.search(r"\n( +)\"", raw)
    indent = len(match.group(1)) if match else 2
    return json.dumps(obj, indent=indent, ensure_ascii=False, sort_keys=True) + (
        "\n" if raw.endswith("\n") else ""
    )


def budgets(rows: int, audio_seconds: float, gpu_hours: float, scoring_jobs: int) -> dict:
    generation = rows * CONTACTS_PER_ROW
    return {
        "asr_calls": 0,
        "ceilings_are_not_targets": True,
        "encoder_calls": 0,
        "fit_endpoint_calls_cap": FIT_ENDPOINTS(rows),
        "generation_calls_cap": generation,
        "gpu_hours_fit_inclusive": gpu_hours,
        "native_task_contract_calls_cap": 0,
        "official_complete_scoring_jobs": scoring_jobs,
        "repeated_speech_audio_seconds_cap": math.ceil(audio_seconds * CONTACTS_PER_ROW),
    }


def derive_baseline(key: str, spec: dict, rows: int) -> str:
    raw = rd(PARENT_BASELINE)
    document = json.loads(raw)
    for field in ("live_phase_fit", "whole_roster_wave_barrier", "policy", "speech_packet_promotion_receipt"):
        if field not in document:
            raise SystemExit(f"the parent baseline declares no {field}")
    if document["policy"] != "phase-direct-only-v1":
        raise SystemExit("the parent baseline is not the direct-only phase program")
    if document["whole_roster_wave_barrier"] is not True:
        raise SystemExit("the parent baseline does not declare the whole-roster wave barrier")
    if "prepared_phase_supply" in document:
        raise SystemExit("the parent baseline must carry no prepared_phase_supply")
    document["live_phase_fit"] = {
        "attempt_id": spec["fit_attempt"],
        "contact_cap": FIT_ENDPOINTS(rows),
        "run_id": spec["fit_run"],
    }
    document["what_this_is"] = (
        "Cell A2T-AA " + spec["role"] + ": the sealed direct baseline "
        "a2t-native-role-direct-union4000-v1, byte-for-byte in every request-shaping "
        "field, re-declared under its own live phase-fit identity for a flight on the "
        "paired 400 (A2T-PAIRED-400-V1). One complete direct answer per row through the "
        "shared controller's direct-only phase program, FlightRuntime and OpenJiuwen; no "
        "knowledge supply, no analytical tools, no native tool authority. It is the "
        "Audio2Tool carrier's own request-identical null: nothing here is a mechanism and "
        "nothing here claims a benefit."
    )
    name = spec["cell"][: -len("-v1")] + "-baseline-v1"
    wr(f"configs/baseline/{name}.json", dump_like(raw, document))
    return name


def derive_experiment(args: argparse.Namespace, key: str, spec: dict, roster: dict, baseline: str) -> None:
    raw = rd(PARENT_EXPERIMENT)
    parent = json.loads(raw)
    if parent["cells"][0]["model_fragment"] != MODEL:
        raise SystemExit("the parent experiment does not fly the expected model fragment")
    smoke = key == "smoke"
    ids = list(roster["smoke_four"]["ids"]) if smoke else None
    rows = len(ids) if smoke else int(roster["count"])
    seconds = float(roster["smoke_four"]["audio_seconds_total"]) if smoke else float(roster["audio_seconds_total"])
    split = roster["smoke_four"]["flight_split_identity_hash"] if smoke else roster["flight_split_identity_hash"]
    caps = budgets(rows, seconds, spec["gpu_hours"], spec["scoring_jobs"])
    pass_a, pass_b, smoke_run = CELLS["a"]["run"], CELLS["b"]["run"], CELLS["smoke"]["run"]
    other = pass_b if key == "a" else pass_a
    expected_generation_seconds = rows / SEALED_CONTACTS_PER_SECOND

    if smoke:
        purpose = (
            "Four-row form smoke of cell A2T-AA on the Audio2Tool session: the same fragment "
            "content as pass A on the lexicographically first row of tiers 1, 2, 5 and 6 of "
            "the paired 400 (the rule the 2026-09-04 calibration smoke and the 2026-09-05 "
            "phase smoke used), to prove the request form, the packet plane, the live phase "
            "fit, the seal and the batch driver's structural inspector before the two 400-row "
            "passes. No score, no read; no number from it is ever a task measurement. Under "
            "the measurement instrument's rule 5 four rows are a form proof by size."
        )
        decision_population = (
            "The four smoke rows of A2T-PAIRED-400-V1: the lexicographically first sample of "
            "tiers 1, 2, 5 and 6 of the paired 400, named in the frozen roster receipt "
            "(smoke_four) and here; " + f"{seconds:.6f}" + " s of speech. Already-exposed "
            "discovery identities; no new speech identity."
        )
    else:
        purpose = (
            "Cell A2T-AA " + spec["role"] + ": Audio2Tool's own same-request null, the number "
            "every later Audio2Tool interval is read against (owner decision 68; instrument "
            "rule 6: the roster's own null is sealed BEFORE any contrast on it; decision 139 "
            "puts it on the GPU queue). Two request-identical passes of the sealed direct "
            "baseline fly on the paired 400 in ONE chain on ONE resident session -- pass A, "
            "then pass B -- and each pass attaches to the session and never spawns or stops "
            "it. The read (docs/readiness/" + args.date + "-" + PACKAGE_STEM + "/analysis-recipe-v1.json) "
            "is DESCRIPTIVE: request identity per row is proven first (request_sha256 equal on "
            "400 of 400); then per-row byte identity of the delivered tool call between the "
            "passes (the count identical of 400); then the pair's difference on the official "
            "Audio2Tool tool accuracy (a2t-toolcall-official, the paper-facing scorer, with the "
            "repository scorer a2t-toolcall beside it) with a tier-stratified paired bootstrap "
            "CI95 whose half-width becomes h_A2T, reported in the natural-mixture and the "
            "equal-tier weighting (decision 71) and per tier; beside it, each pass against the "
            "sealed direct union-4000 rows of the same 400 ids (" + COMPARATOR_RUN + ", a "
            "cross-campaign A/A reported and never a gate), and contacts per minute (decision "
            "140). It claims no benefit, admits nothing and compares no mechanism. Development "
            "numbers only (owner decisions 28 and 86); never a test claim. Nothing here "
            "authorises a flight, a readiness flip or an admission entry."
        )
        decision_population = (
            "A2T-PAIRED-400-V1 (" + ROSTER + "): 50 rows per tier over the eight Audio2Tool "
            "tiers, one seeded draw (seed 20260921) by core.roster.freeze_roster from the "
            "sample ids of the sealed A2T-ORG1-UNION-4000 -- owner decisions 67 and 71; roster "
            "role evaluation, split role discovery; domains "
            + ", ".join(f"{name} {count}" for name, count in sorted(roster["domain_counts"].items(), key=lambda kv: -kv[1]))
            + "; " + f"{seconds:.6f}" + " s of speech, "
            + str(len(roster["rows_at_the_654_second_synthesis_defect"]))
            + " 654-second synthesis-defect row(s) kept because the comparator rows were "
            "sealed on exactly these rows. Every row already carries a sealed direct "
            "comparator row (" + COMPARATOR_RUN + ") whose per-row hashes are frozen beside the "
            "roster; no new speech identity; the full 4,000 flies only for an admitted form."
        )

    document = {
        "cells": [
            {
                "allowed_execution_stages": ["check", "wire-check", "prompt-fit", "worker", "campaign"],
                "attempt_id": spec["attempt"],
                "baseline_fragment": baseline,
                "cell_id": spec["cell"],
                "dataset_fragment": DATASET,
                "model_fragment": MODEL,
                "readiness": {
                    "reason": (
                        "Cell A2T-AA " + spec["role"] + " -- the Audio2Tool carrier's own "
                        "request-identical null on the paired 400 (owner decisions 67, 68, 71 and "
                        "139; measurement instrument rules 3 and 6), registered before contact on "
                        + args.date
                        + " by script from the sealed direct baseline's own fragments (decision 58). "
                        "HELD: root mints coordination/" + PACKAGE_STEM + "/root-admission-v1.json "
                        "(decision id a2t-stage3-aa-paired-400-admission-v1) naming the six eligible "
                        "run ids and this package's caps, then flips the smoke, pass A and pass B "
                        "with scripts/flights/repin_cell.py --set-ready through "
                        "scripts/flights/batch/a2taa_flip_all.sh. The program declares no supplied "
                        "first phase (item E38), so the re-pin creates no prepared artifact and no "
                        "preparation requirement; the requirements list is empty by design and "
                        "--allow-output-change is never passed. The chain flies only on the "
                        "Audio2Tool session " + SESSION + " (c98304 np3 x 32,768 max2048, the A2T "
                        "packet root), never on the resident SLURP np4 session. Nothing here "
                        "authorises a flight, a readiness flip or an admission entry."
                    ),
                    "requirements": [],
                    "state": "held",
                },
                "run_id": spec["run"],
            }
        ],
        "date": args.date,
        "execution_plan": {
            "execution_profile": "bounded-discovery-probe",
            "planned_gpu_hours": caps["gpu_hours_fit_inclusive"],
            "planned_model_calls": caps["generation_calls_cap"],
            "planned_speech_audio_seconds": caps["repeated_speech_audio_seconds_cap"],
            "split_role": "discovery",
        },
        "execution_profile": "bounded-discovery-probe",
        "experiment_id": spec["run"],
        "failure_policy": (
            "Stop and preserve on the first failure. No automatic restart, replay, row "
            "filtering, roster, prompt, knowledge, geometry or cap change. A failure in the "
            "smoke stops the chain and pass A does not open; a failure in pass A stops the "
            "chain and pass B does not open. AT MOST ONE root-diagnosed recovery "
            "re-registration per run id, which needs BOTH a new generation attempt id AND a "
            "new live_phase_fit run and attempt id (a journaled fit cannot be retried under a "
            "spent fit identity); a second failure closes the cell and the fix is proven on a "
            "four-row dry run. RESUME-RECOVERY CLAUSE (owner decision 22 of 2026-09-18): an "
            "INFRASTRUCTURE abort with code and request bytes unchanged takes the "
            "resume-recovery form of harness item E10 -- the same run id, a fresh attempt id, a "
            "resume_from declaration naming the predecessor attempt and its trace SHA-256, "
            "every COMPLETE row kept without selection under invariant I7r, every partial or "
            "unstarted row re-flown in full, no change to the roster, comparator, decision "
            "rule or caps, and the run-cumulative budget re-checked; otherwise the one recovery "
            "is a full re-fly under fresh identities. A partial manifest is never scored and "
            "never read. If pass A and pass B do not seal on ONE resident session, the pair is "
            "not request-identical and the null is not read from it."
        ),
        "family_budget": caps,
        "fragment_kind": f"saea-{PACKAGE_STEM}",
        "generation_budget": {
            "cap": caps["generation_calls_cap"],
            "definition": (
                "The direct-only phase program (configs/policy/phase-direct-only-v1.json: one "
                "phase, max_contacts 1, always-run-full-program) makes exactly ONE contact per "
                "row, so " + str(rows) + " x 1 = " + str(caps["generation_calls_cap"]) + " is the "
                "program's exact maximum and its expectation at once; the sealed direct baseline "
                "realised 4,000 contacts on 4,000 rows. The live phase fit makes 1 + (2 + 1) x "
                + str(rows) + " = " + str(caps["fit_endpoint_calls_cap"]) + " tokenizer endpoint "
                "calls under its own run id " + spec["fit_run"] + " -- the count "
                "core.preparation_fit.complete_phase_endpoint_count requires to the unit; the fit "
                "gate refuses any other cap. At the sealed direct baseline's own realised rate "
                "(4,000 contacts in 1,518.6 s of generation wall at np3) the generation wall is "
                "about " + f"{expected_generation_seconds:.0f}" + " s; the GPU-hour ceiling of "
                + str(caps["gpu_hours_fit_inclusive"]) + " covers fit, packet validation and "
                "client initialisation many times over and is a BOUND, never a target. Budgets "
                "are run-cumulative across every attempt of a run id."
            ),
            "target": caps["generation_calls_cap"],
        },
        "own_null_pair": {
            "chain": "one batch-driver chain on one resident session: smoke, pass A, pass B",
            "comparator_run_id": COMPARATOR_RUN,
            "comparator_rows": "docs/receipts/rosters/a2t-paired-400-v1.comparator-rows.json",
            "pass_a_run_id": pass_a,
            "pass_b_run_id": pass_b,
            "request_identical_to": (
                "the smoke's form and the other pass's bytes" if smoke else other + " (" + ONE_FACTOR + ")"
            ),
            "roster_receipt": ROSTER,
            "smoke_run_id": smoke_run,
            "this_cell": spec["role"],
        },
        "population": {
            "count": rows,
            "dataset_fragment": DATASET,
            "decision_population": decision_population,
            "split_identity_hash": split,
        },
        "preserve_wire_responses": True,
        "purpose": purpose,
        "service_session": SESSION,
        "stage3_algorithm": {
            "id": "none",
            "note": STAGE3_ALGORITHM_NOTE,
            "operators_used": [],
        },
    }
    if smoke:
        document["populations"] = [{"dataset_fragment": DATASET, "ids": ids}]
    wr(f"configs/experiment/{spec['cell']}.json", dump_like(raw, document))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", required=True)
    args = parser.parse_args(argv)

    roster = json.loads(rd(ROSTER))
    if roster["schema"] != "saea-roster-receipt-v1" or roster["roster_id"] != "A2T-PAIRED-400-V1":
        raise SystemExit("the roster receipt is not the frozen paired 400")
    if roster["count"] != 400 or roster["seed"] != 20260921:
        raise SystemExit("the roster receipt is not the 400-row seed-20260921 draw")
    if roster["dataset_fragment"] != f"configs/dataset/{DATASET}.json":
        raise SystemExit("the roster receipt names a different dataset fragment")

    written = []
    for key, spec in CELLS.items():
        rows = 4 if key == "smoke" else 400
        baseline = derive_baseline(key, spec, rows)
        derive_experiment(args, key, spec, roster, baseline)
        written.extend([f"configs/baseline/{baseline}.json", f"configs/experiment/{spec['cell']}.json"])
    for key in ("a", "b"):
        path = f"configs/campaign/{CELLS[key]['cell']}.json"
        wr(
            path,
            json.dumps(
                {"cells": [{"cell": CELLS[key]["cell"], "experiment": CELLS[key]["cell"]}], "schema": "saea-campaign-plan-v1"},
                indent=2,
                sort_keys=True,
            )
            + "\n",
        )
        written.append(path)
    print(
        json.dumps(
            {
                "written": written,
                "rows": {"a": 400, "b": 400, "smoke": 4},
                "caps": {
                    key: budgets(4 if key == "smoke" else 400, float(roster["smoke_four"]["audio_seconds_total"]) if key == "smoke" else float(roster["audio_seconds_total"]), spec["gpu_hours"], spec["scoring_jobs"])
                    for key, spec in CELLS.items()
                },
                "split_identity_hash": roster["flight_split_identity_hash"],
                "smoke_split_identity_hash": roster["smoke_four"]["flight_split_identity_hash"],
                "session": SESSION,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
