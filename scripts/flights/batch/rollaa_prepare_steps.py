#!/usr/bin/env python3
"""Derive cell ROLL-AA (the Stage-3 within-flight A/A null) from the sealed ROLL-1 cell.

Board route F2 (``docs/handoff/2026-09-24-fable51/HANDOFF-STAGE3-FOR-CHATGPT-v1.md section 7.3``):
the locked v2.0 plan's Solver answers the IDENTICAL prompt TWICE for each of 200
construction rows inside ONE flight, greedy, so the program learns the WITHIN-FLIGHT
paired noise floor that the ROLL-2 variant rollouts will be read against. ROLL-1's
grouped-Solver form is the substrate; the E2b ``roles.solver.twin: "greedy-repeat"``
marker (``rails.native_episode_config``) is the ONLY registered way
``decoding_overrides.temperature`` may be 0, and it is exactly what an A/A null needs.

Model-free by construction: zero model, tokenizer, encoder, scorer, GPU and network
contacts, and no audio sample is decoded. Run from WSL2 with the study venv.

Commands
--------
``rosters``
    Write ``docs/receipts/rosters/slurp-stage3-roll-aa-r01c-200-v1.json`` (the FIRST 200
    items of the committed R01C construction receipt, in the parent's own order) and its
    four-row smoke sibling ``...-roll-aa-r01c-smoke-4-v1.json`` (the first 4 of those
    200). Both are PURE SELECTIONS: every surviving item is the parent's item verbatim,
    no rng is consulted, and the split identity is recomputed through
    ``data.splits.split_identity_hash``. The GEPA carriers/groups receipts
    (``scripts/flights/batch/gepa_prepare_steps.py``) are the minting precedent.

``policy``
    Write ``configs/policy/phase-native-candidates-review-revise-samples2-v1.json``: the
    SAME four phases and the SAME episode shape as the samples5 program ROLL-1 flies,
    with the grouped-Solver ceiling at samples 2 -- ``1 + (1 + 1) * (1 * 2 + 3 + 1) =
    13``. A separate program id, never a flag on the samples5 program, because
    ``rails.native_episode_config.load_native_episode_config`` asserts
    ``program.max_contacts`` equals the bounded graph ceiling and two program ids must
    never resolve to the same object when their ceilings differ.

``fragments``
    Write the two baselines, the two experiment fragments and the campaign plan by
    derivation from ROLL-1's committed fragments, changing exactly the announced factor
    (below) and the per-flight bookkeeping.

``verify``
    Re-derive every artifact in memory and compare it to what is committed; print the
    disagreements and exit non-zero. Nothing is written.

The ONE factor against cell ROLL-1
----------------------------------
``native_episode.roles.solver``: ``samples`` 5 -> 2, ``decoding_overrides.temperature``
0.7 -> 0.0, the explicit ``twin: "greedy-repeat"`` marker added, and
``commit.min_support`` 3 -> 2 (ROLL-1's "support >= a strict majority of the samples"
rule re-evaluated at N = 2; 3 is not expressible at N = 2 and
``rails.native_episode_config`` refuses ``min_support > samples``). ``seed_offset`` stays
0. The policy program id moves with the ceiling (19 -> 13). Everything else --
``knowledge_stores``, ``phase_material``, the task instruction template, the geometry,
``scorers``, ``evidence_source``, the arm, the filled S3-1 preparation pins -- is
ROLL-1's own bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

REPO_DEFAULT = Path(__file__).resolve().parents[3]

CARRIER = "slurp"
PARENT_ROSTER = "docs/receipts/rosters/slurp-stage3-construction-r01c.json"
RUNTIME_VIEW = "configs/dataset/slurp-speech-native-stage3-construction-r01c.json"
ROSTER_OUT = "docs/receipts/rosters/slurp-stage3-roll-aa-r01c-200-v1.json"
ROSTER_ID = "SLURP-STAGE3-ROLL-AA-R01C-200-V1"
SMOKE_ROSTER_OUT = "docs/receipts/rosters/slurp-stage3-roll-aa-r01c-smoke-4-v1.json"
SMOKE_ROSTER_ID = "SLURP-STAGE3-ROLL-AA-R01C-SMOKE-4-V1"
ARM_ROWS = 200
SMOKE_ROWS = 4

#: The bounded native graph ceiling at samples 2 (rails.native_episode_config's own
#: formula): 1 + (max_revisions + 1) * (solver.max_iterations * solver.samples +
#: reviewer.max_iterations + planner.max_iterations) = 1 + 2 * (2 + 3 + 1).
CEILING = 13
#: One speech packet plus three FIT endpoints per contact, the ROLL-1 arithmetic.
FIT_MULTIPLIER = 4

POLICY_ID = "phase-native-candidates-review-revise-samples2-v1"
POLICY_OUT = f"configs/policy/{POLICY_ID}.json"
SOURCE_POLICY = "configs/policy/phase-native-candidates-review-revise-samples5-v1.json"

SRC_BASELINE = "configs/baseline/slurp-native-stage3-rollout-baseline-v1.json"
SRC_SMOKE_BASELINE = "configs/baseline/slurp-native-stage3-rollout-smoke-4-baseline-v1.json"
SRC_EXPERIMENT = "configs/experiment/slurp-native-stage3-rollout-r01-v1.json"
SRC_SMOKE_EXPERIMENT = "configs/experiment/slurp-native-stage3-rollout-r01-smoke-4-v1.json"

OUT_BASELINE = "configs/baseline/slurp-native-stage3-roll-aa-baseline-v1.json"
OUT_SMOKE_BASELINE = "configs/baseline/slurp-native-stage3-roll-aa-smoke-4-baseline-v1.json"
OUT_EXPERIMENT = "configs/experiment/slurp-native-stage3-roll-aa-v1.json"
OUT_SMOKE_EXPERIMENT = "configs/experiment/slurp-native-stage3-roll-aa-smoke-4-v1.json"
OUT_CAMPAIGN = "configs/campaign/slurp-native-stage3-roll-aa-v1.json"

ARM_CELL = "slurp-native-stage3-roll-aa-v1"
SMOKE_CELL = "slurp-native-stage3-roll-aa-smoke-4-v1"
ARM_RUN = "SAEA-SLURP-STAGE3-ROLL-AA-V1"
ARM_FIT_RUN = "SAEA-SLURP-STAGE3-ROLL-AA-FIT-V1"
SMOKE_RUN = "SAEA-SLURP-STAGE3-ROLL-AA-SMOKE-4-V1"
SMOKE_FIT_RUN = "SAEA-SLURP-STAGE3-ROLL-AA-SMOKE-4-FIT-V1"
ARM_ATTEMPT = "attempt-slurp-native-stage3-roll-aa-v1-generation"
ARM_FIT_ATTEMPT = "attempt-slurp-native-stage3-roll-aa-v1-fit"
SMOKE_ATTEMPT = "attempt-slurp-native-stage3-roll-aa-smoke-4-v1-generation"
SMOKE_FIT_ATTEMPT = "attempt-slurp-native-stage3-roll-aa-smoke-4-v1-fit"

PACKAGE = "docs/readiness/2026-09-24-slurp-stage3-roll-aa-v1"
BOARD = "docs/handoff/2026-09-24-fable51/HANDOFF-STAGE3-FOR-CHATGPT-v1.md section 7.3"
DATE = "2026-09-24"

#: The Solver role block ROLL-AA flies. ``twin: "greedy-repeat"`` is what makes
#: ``temperature: 0.0`` legal at all (rails.native_episode_config: "the ONLY way
#: decoding_overrides.temperature may be 0"), and the E2b comment beside it states the
#: rest of this cell's thesis in the implementation's own words: "its N pinned seeds are
#: recorded custody, never a source of diversity at temperature 0".
SOLVER_ROLE = {
    "commit": {
        "min_support": 2,
        "policy": "saea-commit-plurality-support-v1",
        "similarity_threshold": 0.8,
    },
    "decoding_overrides": {"seed_offset": 0, "temperature": 0.0},
    "max_iterations": 1,
    "phase_id": "solver",
    "samples": 2,
    "twin": "greedy-repeat",
}

FACTOR = (
    "native_episode.roles.solver: samples 5 -> 2, decoding_overrides.temperature 0.7 -> "
    "0.0, the explicit twin 'greedy-repeat' marker added (rails.native_episode_config: "
    "the ONLY way temperature may be 0), commit.min_support 3 -> 2 (ROLL-1's 'support >= "
    "a strict majority of the samples' rule re-evaluated at N = 2; min_support > samples "
    "is refused); seed_offset stays 0. The policy program id moves with the bounded graph "
    "ceiling (phase-native-candidates-review-revise-samples5-v1, 19 -> "
    "phase-native-candidates-review-revise-samples2-v1, 13). Everything else is cell "
    "ROLL-1's own bytes."
)

WHAT_ARM = (
    "Cell ROLL-AA (board route F2, " + BOARD + "): the WITHIN-FLIGHT A/A null of the "
    "Stage-3 variant-rollout methodology. Cell ROLL-1's grouped-Solver fragment with "
    "EXACTLY the Solver group changed to the E2b greedy-repeat twin form at N = 2 -- the "
    "locked v2.0 plan's Solver answering the IDENTICAL prompt twice for each row, greedy "
    "-- flown on the first 200 rows of the R01C construction roster. The two samples of "
    "one Solver visit are two contacts of the SAME request (reproduction.ojw."
    "native_group_solver): same messages, same speech packet, same supplied knowledge, "
    "same response format; the ONLY field that differs between them is the composed "
    "decoding seed (reproduction.ojw.native_request.compose_solver_sample_decoding_params: "
    "seed = fragment_seed + seed_offset + sample_index), which llama.cpp's greedy path "
    "does not consult. Whatever paired per-row difference the read then measures is the "
    "measurement floor itself -- batch-composition nondeterminism and nothing else -- and "
    "that number becomes h_within, the margin every ROLL-2 variant comparison at n = 200 "
    "is read against. DESCRIPTIVE: no admission verdict, no comparator, no gate."
)

WHAT_SMOKE = (
    "Cell ROLL-AA four-row structural smoke (board route F2, " + BOARD + "): the same "
    "greedy-repeat N = 2 Solver group on the first four rows of the ROLL-AA roster, for "
    "structural acceptance only -- two raw Solver samples in solver_group custody per "
    "row (I7g), no tools array, every request fits. It produces no null and no number."
)


class RollAaPrepareError(RuntimeError):
    """An input is missing or does not have the shape this helper needs."""


# ---------------------------------------------------------------------------
# small file helpers -- explicit utf-8 everywhere, LF newlines preserved
# ---------------------------------------------------------------------------


def rd(path: Path) -> str:
    return io.open(path, encoding="utf-8", newline="").read()


def read_json(path: Path) -> Any:
    try:
        return json.loads(rd(path))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RollAaPrepareError(f"{path} is unreadable: {error}") from error


def dump_like(raw: str, obj: Any) -> str:
    match = re.search(r"\n( +)\"", raw)
    indent = len(match.group(1)) if match else 2
    return json.dumps(obj, indent=indent, ensure_ascii=False, sort_keys=True) + (
        "\n" if raw.endswith("\n") else ""
    )


def write_text(path: Path, text: str, *, write: bool) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if path.is_file() and rd(path) == text:
        print(f"  = {path.name} already present and identical ({digest[:16]})")
        return digest
    if not write:
        print(f"  (dry) would write {path.name} ({digest[:16]})")
        return digest
    path.parent.mkdir(parents=True, exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="").write(text)
    print(f"  + wrote {path.name} ({digest[:16]})")
    return digest


def import_repo(repo_root: Path):
    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from speech_aware_evidence_acquisition.core import roster as roster_module  # noqa: PLC0415
    from speech_aware_evidence_acquisition.data import splits  # noqa: PLC0415

    return roster_module, splits


# ---------------------------------------------------------------------------
# rosters
# ---------------------------------------------------------------------------


def selection_receipt(
    *, parent: Mapping[str, Any], rows: int, roster_id: str, splits, authority: str,
    selection_rule: str,
) -> dict[str, Any]:
    """A pure selection of the parent receipt's first ``rows`` items; no draw, no rng."""

    parent_items = parent.get("items")
    if not isinstance(parent_items, list) or len(parent_items) < rows:
        raise RollAaPrepareError(
            f"{PARENT_ROSTER} carries {len(parent_items or [])} items, fewer than {rows}"
        )
    items = [dict(item) for item in parent_items[:rows]]
    ids = [str(item["sample_id"]) for item in items]
    counts = dict(sorted(Counter(str(item["stratum"]) for item in items).items()))
    receipt: dict[str, Any] = {
        "schema": parent["schema"],
        "roster_id": roster_id,
        "carrier_lock_key": CARRIER,
        "split_role": "discovery",
        "roster_role": "construction",
        "seed": parent.get("seed"),
        "per_stratum": counts,
        "strata_counts": counts,
        "items": items,
        "excluded_count": len(parent_items) - len(items),
        "split_identity_hash": splits.split_identity_hash(splits.prefixed(CARRIER, ids)),
        "authority": authority,
        "roster_role_note": (
            "construction: ROLL-AA reads no gold at runtime and produces no admission "
            "verdict. These TRAIN rows carry construction gold that the OFFLINE read "
            "scores the two Solver samples against, exactly as cell ROLL-1's rows do; "
            "the flight itself is the locked plan, unchanged, with a two-sample greedy "
            "Solver group."
        ),
        "draw_method": (
            "No draw. This receipt is a pure SELECTION of the parent receipt's frozen "
            "items: every surviving item is the parent's item verbatim, in the parent's "
            "order (ascending sample_id, as core.roster.freeze_roster left it). The seed "
            "is the parent's and is carried for provenance only -- no rng is consulted "
            "anywhere in this build."
        ),
        "selection_rule": selection_rule,
        "generator": "scripts/flights/batch/rollaa_prepare_steps.py",
        "parent": {
            "roster_id": parent.get("roster_id"),
            "count": len(parent_items),
            "relpath": PARENT_ROSTER,
            "split_identity_hash": parent.get("split_identity_hash"),
        },
        "stratum_coverage_note": (
            f"A PREFIX of an ascending-sample_id roster is NOT scenario-stratified: these "
            f"{rows} rows cover {len(counts)} of the parent's 18 scenario strata "
            f"({', '.join(sorted(counts))}). The selection rule was specified as the "
            "first-N prefix and is registered as such; the preregistration's own "
            "'What this null does not measure' section states the consequence, and the "
            "alternative (a stratified 200) is recorded there as a decision NOT taken."
        ),
        "offline_guard": {"attempted_targets": [], "outbound_connection_attempts": 0},
    }
    for carried in ("d1_supplement", "disjointness_proof", "knowledge_source_guard"):
        if carried in parent:
            receipt[carried] = parent[carried]
    return receipt


def cmd_rosters(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root)
    roster_module, splits = import_repo(repo_root)
    parent = read_json(repo_root / PARENT_ROSTER)
    roster_module.verify_roster(parent)
    specs = (
        (
            ARM_ROWS, ROSTER_ID, ROSTER_OUT,
            (
                "Board route F2 (" + BOARD + "), the Stage-3 within-flight A/A null: the "
                "flown population of cell ROLL-AA. A construction-role receipt of its own "
                "is required because the population is not the parent's: "
                "core.flight.campaign and contracts.gate_exposure bind a flight to the "
                "split identity of the rows it actually flies, and the GEPA carriers "
                "receipt (SLURP-STAGE3-GEPA-R01C-CARRIERS-V1) is the precedent for "
                "committing a narrower construction population as its own receipt."
            ),
            (
                f"The FIRST {ARM_ROWS} items of {PARENT_ROSTER}, in the parent's own "
                "order; order preserved."
            ),
        ),
        (
            SMOKE_ROWS, SMOKE_ROSTER_ID, SMOKE_ROSTER_OUT,
            (
                "The four-row structural smoke population of cell ROLL-AA. The gate knows "
                "nothing about parent rosters, so those four rows need a committed "
                "receipt of their own (the GEPA smoke-roster precedent)."
            ),
            (
                f"The FIRST {SMOKE_ROWS} items of {ROSTER_OUT} -- equivalently of "
                f"{PARENT_ROSTER} -- in the parent's own order; order preserved. These "
                "are the same four rows cell ROLL-1's own smoke flies."
            ),
        ),
    )
    for rows, roster_id, out_relpath, authority, rule in specs:
        receipt = selection_receipt(
            parent=parent, rows=rows, roster_id=roster_id, splits=splits,
            authority=authority, selection_rule=rule,
        )
        measured = roster_module.verify_roster(receipt)
        out_path = repo_root / out_relpath
        raw = json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
        if out_path.is_file():
            existing = read_json(out_path)
            if existing.get("split_identity_hash") != measured:
                raise RollAaPrepareError(
                    f"{out_relpath} already exists with a different split identity; "
                    "refusing to rewrite"
                )
        print(f"roster {out_relpath} rows={rows} split_identity={measured}")
        write_text(out_path, raw, write=args.write)
    return 0


# ---------------------------------------------------------------------------
# policy program
# ---------------------------------------------------------------------------


def build_policy(repo_root: Path) -> tuple[str, str]:
    raw = rd(repo_root / SOURCE_POLICY)
    program = json.loads(raw)
    program["program_id"] = POLICY_ID
    program["max_contacts"] = CEILING
    return raw, json.dumps(program, indent=2, ensure_ascii=False) + "\n"


def cmd_policy(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root)
    raw, text = build_policy(repo_root)
    print(f"policy {POLICY_OUT} max_contacts={CEILING}")
    write_text(repo_root / POLICY_OUT, text, write=args.write)
    return 0


# ---------------------------------------------------------------------------
# fragments
# ---------------------------------------------------------------------------


def roster_facts(repo_root: Path, rows: int) -> dict[str, Any]:
    _roster_module, splits = import_repo(repo_root)
    parent = read_json(repo_root / PARENT_ROSTER)
    view = read_json(repo_root / RUNTIME_VIEW)
    seconds = {row["sample_id"]: row["audio_seconds"] for row in view["items"]}
    ids = [str(item["sample_id"]) for item in parent["items"][:rows]]
    total = sum(seconds[i] for i in ids)
    return {
        "ids": ids,
        "rows": rows,
        "audio_seconds_total": total,
        "split_identity_hash": splits.split_identity_hash(splits.prefixed(CARRIER, ids)),
        "planned_model_calls": rows * CEILING,
        "planned_speech_audio_seconds": math.ceil(total * CEILING),
        "fit_contact_cap": rows * CEILING * FIT_MULTIPLIER,
        "strata": dict(sorted(Counter(str(i["stratum"]) for i in parent["items"][:rows]).items())),
    }


def build_baseline(repo_root: Path, *, smoke: bool) -> tuple[str, str]:
    source = SRC_SMOKE_BASELINE if smoke else SRC_BASELINE
    raw = rd(repo_root / source)
    document = json.loads(raw)
    rows = SMOKE_ROWS if smoke else ARM_ROWS
    facts = roster_facts(repo_root, rows)
    document["native_episode"]["roles"]["solver"] = json.loads(json.dumps(SOLVER_ROLE))
    document["policy"] = POLICY_ID
    document["native_contact_fit"] = {
        "attempt_id": SMOKE_FIT_ATTEMPT if smoke else ARM_FIT_ATTEMPT,
        "contact_cap": facts["fit_contact_cap"],
        "max_speech_packets": 1,
        "run_id": SMOKE_FIT_RUN if smoke else ARM_FIT_RUN,
    }
    # Item E16: this cell's OWN model-free first-phase supply is minted under its own run
    # id by core.flight.repin at the readiness flip. Nothing is inherited from ROLL-1, so
    # no pin is carried here and none is invented.
    document.pop("prepared_phase_supply", None)
    document["what_this_is"] = (WHAT_SMOKE if smoke else WHAT_ARM) + " Derived " + DATE + (
        " by scripts/flights/batch/rollaa_prepare_steps.py from " + source + ". "
    ) + "ONE FACTOR: " + FACTOR
    document["roster_note"] = (
        f"The flown population is the {rows} rows of "
        f"{SMOKE_ROSTER_OUT if smoke else ROSTER_OUT} (split identity "
        f"{facts['split_identity_hash']}), a pure selection of the committed R01C "
        "construction receipt. The dataset fragment stays R01C's own runtime view: the "
        "experiment fragment's populations[].ids is what narrows the flight, exactly as "
        "cell ROLL-1's own four-row smoke narrows against the same 625-row view."
    )
    document["a_a_null_note"] = (
        "Why the two samples are a NULL and not a factor: reproduction.ojw."
        "native_group_solver.run_grouped_solver_samples composes N independent Solver "
        "invocations of ONE visit, each through the same metered request path, and "
        "reproduction.ojw.native_request.compose_solver_sample_decoding_params overrides "
        "exactly two request fields per sample -- temperature (0.0 here, for both) and "
        "seed (fragment_seed + seed_offset + sample_index, so sample 0 and sample 1 "
        "differ by one). Every other byte of the two requests is the same object. At "
        "temperature 0 llama.cpp decodes greedily and does not consult the seed, so the "
        "residual difference is batch composition alone (llama.cpp greedy decoding is "
        "not bitwise reproducible across batch shapes). rails.native_episode_config "
        "accepts temperature 0 ONLY under the explicit twin 'greedy-repeat' marker "
        "declared above, which is why that marker is part of this cell's form and not a "
        "comment."
    )
    return raw, dump_like(raw, document)


def build_experiment(repo_root: Path, *, smoke: bool) -> tuple[str, str]:
    source = SRC_SMOKE_EXPERIMENT if smoke else SRC_EXPERIMENT
    raw = rd(repo_root / source)
    document = json.loads(raw)
    rows = SMOKE_ROWS if smoke else ARM_ROWS
    facts = roster_facts(repo_root, rows)
    run = SMOKE_RUN if smoke else ARM_RUN
    cell_id = SMOKE_CELL if smoke else ARM_CELL
    document["date"] = DATE
    document["experiment_id"] = run
    document["fragment_kind"] = (
        "saea-slurp-native-stage3-roll-aa-smoke-4-v1" if smoke
        else "saea-slurp-native-stage3-roll-aa-v1"
    )
    document["execution_plan"] = {
        "execution_profile": "bounded-discovery-probe",
        "planned_gpu_hours": 1.0 if smoke else 2.0,
        "planned_model_calls": facts["planned_model_calls"],
        "planned_speech_audio_seconds": facts["planned_speech_audio_seconds"],
        "split_role": "discovery",
    }
    document["family_budget"] = {
        "asr_calls": 0,
        "ceilings_are_not_targets": True,
        "encoder_calls": 0,
        "fit_endpoint_calls_cap": facts["fit_contact_cap"],
        "generation_calls_cap": facts["planned_model_calls"],
        "gpu_hours_fit_inclusive": 1.0 if smoke else 2.0,
        "native_task_contract_calls_cap": 0,
        "official_complete_scoring_jobs": 0 if smoke else 1,
        "repeated_speech_audio_seconds_cap": facts["planned_speech_audio_seconds"],
    }
    document["generation_budget"] = {
        "cap": facts["planned_model_calls"],
        "definition": (
            f"{ARM_ROWS * CEILING} = {ARM_ROWS} rows x {CEILING} and "
            f"{SMOKE_ROWS * CEILING} = {SMOKE_ROWS} rows x {CEILING}, where {CEILING} is "
            "the grouped-Solver graph's OWN ceiling at samples 2 as rails."
            "native_episode_config.load_native_episode_config resolves it: "
            "perception.max_iterations + (max_revisions + 1) x (solver.max_iterations x "
            "solver.samples + reviewer.max_iterations + planner.max_iterations) = "
            "1 + 2 x (1 x 2 + 3 + 1). The ceiling is a BOUND, never a target: the "
            "expected spend is about 5.2 contacts per row (cell CELL-1 measured 4.216 at "
            f"samples 1; the group adds one Solver contact per visit), i.e. about "
            f"{round(ARM_ROWS * 5.2):,} contacts on the arm, so the registered ceiling is "
            "about 2.5x the expectation. Budgets are run-cumulative across every attempt "
            "of a run id."
        ),
    }
    document["population"] = {
        "count": rows,
        "dataset_fragment": "slurp-speech-native-stage3-construction-r01c",
        "decision_population": (
            f"The first {rows} rows, in roster order, of the clean construction subset "
            f"SLURP-STAGE3-CONSTRUCTION-R01C, committed as "
            f"{SMOKE_ROSTER_OUT if smoke else ROSTER_OUT} "
            f"({SMOKE_ROSTER_ID if smoke else ROSTER_ID}). "
            + (
                "Structural smoke only."
                if smoke
                else (
                    "A PREFIX of an ascending-sample_id roster is not scenario-"
                    f"stratified: these rows cover {len(facts['strata'])} of the parent's "
                    "18 scenario strata. The consequence is registered in the "
                    "preregistration's 'What this null does not measure' section."
                )
            )
        ),
        "split_identity_hash": facts["split_identity_hash"],
        "roster_receipt": SMOKE_ROSTER_OUT if smoke else ROSTER_OUT,
    }
    document["populations"] = [
        {
            "dataset_fragment": "slurp-speech-native-stage3-construction-r01c",
            "ids": facts["ids"],
        }
    ]
    document["split_id"] = "STAGE3-CONSTRUCTION-R01C"
    document["purpose"] = (WHAT_SMOKE if smoke else WHAT_ARM)
    document["stage3_algorithm"] = {
        "id": "shared-rollout",
        "operators_used": ["rollout"],
        "note": (
            "ROLL-AA exercises the SAME algorithm-neutral rollout substrate cell ROLL-1 "
            "registered -- the grouped Solver, its custody and its commit -- and applies "
            "no learned context of its own. It is the A/A NULL of that substrate: two "
            "greedy repeats of one prompt, so the paired per-row difference it measures "
            "is the methodology's own measurement floor rather than any operator's "
            "effect. Declared 'shared-rollout' for exactly that reason; it is not a "
            "family arm and carries no credit_assignment or update operator."
        ),
    }
    document["failure_policy"] = (
        "Stop and preserve on the first failure. No automatic restart, replay, row "
        "filtering, roster, role-graph, prompt, knowledge, geometry or cap change. This "
        "registration pre-authorises no recovery; a root-diagnosed recovery "
        "re-registration is a separate act once the cell is flown. A partial manifest is "
        "never read."
    )
    for cell_doc in document["cells"]:
        cell_doc["cell_id"] = cell_id
        cell_doc["run_id"] = run
        cell_doc["attempt_id"] = SMOKE_ATTEMPT if smoke else ARM_ATTEMPT
        cell_doc["baseline_fragment"] = (
            "slurp-native-stage3-roll-aa-smoke-4-baseline-v1" if smoke
            else "slurp-native-stage3-roll-aa-baseline-v1"
        )
        cell_doc["readiness"] = {
            "reason": (
                "Cell ROLL-AA (board route F2, " + BOARD + "): the within-flight A/A null "
                "of the Stage-3 variant-rollout methodology. READINESS HELD. Every "
                "roster-bound preparation cell ROLL-1 needed is already SEALED and is "
                "inherited by hash in this cell's baseline (the R01C featcache packet "
                "promotion, the intent-boundary speech-query encoding and the model-free "
                "content derivative all close over a SUPERSET of these rows and are read "
                "by id). What does NOT exist yet is this cell's OWN model-free first-phase "
                "supply (item E16: a prepared artifact is evidence only for the "
                "implementation that produced it, so nothing is inherited from ROLL-1) and "
                "the root-admission decision receipt. 'requirements' is deliberately EMPTY "
                "rather than a PENDING placeholder pair: core.flight.repin."
                "_set_preparation_requirement CREATES the preparation requirement on the "
                "first successful preparation and _upsert_decision_requirement INSERTS the "
                "decision requirement at the flip, while a placeholder decision entry "
                "without an expected_decision_id would be left behind beside the real one "
                "and refuse the campaign at load (core.flight.campaign.declared_readiness). "
                "Nothing here authorises a flight, a readiness flip, a contact or an "
                "admission entry."
            ),
            "requirements": [],
            "state": "held",
        }
    return raw, dump_like(raw, document)


def build_campaign() -> str:
    return json.dumps(
        {"cells": [{"cell": ARM_CELL, "experiment": ARM_CELL}],
         "schema": "saea-campaign-plan-v1"},
        indent=2, ensure_ascii=False,
    ) + "\n"


def derived_artifacts(repo_root: Path) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    out.append((POLICY_OUT, build_policy(repo_root)[1]))
    out.append((OUT_BASELINE, build_baseline(repo_root, smoke=False)[1]))
    out.append((OUT_SMOKE_BASELINE, build_baseline(repo_root, smoke=True)[1]))
    out.append((OUT_EXPERIMENT, build_experiment(repo_root, smoke=False)[1]))
    out.append((OUT_SMOKE_EXPERIMENT, build_experiment(repo_root, smoke=True)[1]))
    out.append((OUT_CAMPAIGN, build_campaign()))
    return out


def cmd_fragments(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root)
    for relpath, text in derived_artifacts(repo_root):
        print(f"fragment {relpath}")
        write_text(repo_root / relpath, text, write=args.write)
    return 0


def cmd_facts(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root)
    for rows in (ARM_ROWS, SMOKE_ROWS):
        facts = roster_facts(repo_root, rows)
        facts.pop("ids")
        print(json.dumps(facts, indent=2, sort_keys=True))
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root)
    bad = 0
    roster_module, splits = import_repo(repo_root)
    parent = read_json(repo_root / PARENT_ROSTER)
    for rows, roster_id, relpath in (
        (ARM_ROWS, ROSTER_ID, ROSTER_OUT), (SMOKE_ROWS, SMOKE_ROSTER_ID, SMOKE_ROSTER_OUT),
    ):
        committed = read_json(repo_root / relpath)
        measured = roster_module.verify_roster(committed)
        expected_ids = [str(i["sample_id"]) for i in parent["items"][:rows]]
        expected = splits.split_identity_hash(splits.prefixed(CARRIER, expected_ids))
        ok = (
            measured == expected
            and committed.get("roster_id") == roster_id
            and [str(i["sample_id"]) for i in committed["items"]] == expected_ids
        )
        print(f"verify roster {relpath}: {'OK' if ok else 'DISAGREES'} ({measured})")
        bad += 0 if ok else 1
    for relpath, text in derived_artifacts(repo_root):
        path = repo_root / relpath
        ok = path.is_file() and rd(path) == text
        print(f"verify {relpath}: {'OK' if ok else 'DISAGREES'}")
        bad += 0 if ok else 1
    return 0 if bad == 0 else 3


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_DEFAULT))
    parser.add_argument("--write", action="store_true")
    parser.add_argument("command", choices=("rosters", "policy", "fragments", "facts", "verify"))
    args = parser.parse_args(argv)
    return {
        "rosters": cmd_rosters, "policy": cmd_policy, "fragments": cmd_fragments,
        "facts": cmd_facts, "verify": cmd_verify,
    }[args.command](args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RollAaPrepareError as error:  # pragma: no cover - CLI surface
        print(f"rollaa_prepare_steps: FAIL: {error}", file=sys.stderr)
        raise SystemExit(2) from None
