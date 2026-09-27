#!/usr/bin/env python3
"""Derive cell DET -- the single-slot, prompt-cache-off request-identical pair
of the locked v2.0 plan -- from the sealed PLAN lock fragments (decision 58:
script-derived registrations).

THE HYPOTHESIS. The binding instrument note
``docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md``
records that two REQUEST-IDENTICAL flights of the locked plan differ by
+1.87 pp SLU at n = 625 (VAR1 PLAN against PLANR), and that even inside one
flight only 91.5 % of delivered answers are byte-identical (ROLL-AA). That
offset set the programme's cross-flight admission bar at 2.5-3.0 pp. But the
locked arm decodes at temperature 0 on a server that runs FOUR slots under
continuous batching with the prompt cache ON and a q8_0 KV cache -- exactly
the configuration in which llama.cpp greedy decoding is known not to be
bitwise reproducible, because a request's numerics depend on which other
requests share its batch and on cache state. Nobody has measured whether a
SINGLE-slot server with the prompt cache OFF makes the same flight
reproducible. If it does, the between-flight offset is an engineering
artefact and collapses; if it does not, the offset is intrinsic.

THE CELL. The locked PLAN arm (``SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1``),
byte-identical in every knob -- baseline, stores, pins, policies, program,
templates, normaliser, scorers, decoding params, prompt order, speech packets
-- flown TWICE in one chain (pass A, then pass B) on the first 50 rows of
TRAIN Fold A in roster order, on a NEW serving geometry: one 24,576-token
slot (``-np 1 -c 24576``, the same slot size, so prompt fit is unchanged),
``--no-cache-prompt`` in place of ``--cache-prompt`` (llama.cpp defaults
``cache_prompt`` to TRUE, so "off" must be spelled explicitly), no
``--slot-prompt-similarity`` (moot with one slot and no cache), everything
else the resident geometry's own bytes: the same model file and sha256,
``-fa on``, ``-ctk q8_0 -ctv q8_0``, ``-b 2048 -ub 512``, ``-ngl 999``,
``--cache-ram 0 --no-cache-idle-slots``, the same runtime receipt (so
``--no-mmproj`` is injected exactly as before), the same server_env.

WHERE THE GEOMETRY LIVES. The harness declares a serving geometry in TWO
places that must agree, and refuses when they do not: the model fragment's
``server_args`` (``-np``/``-c``, what llama-server is handed, cross-checked
by ``core.session.serving.resolve_serving_profile``) and the baseline's
``serving_slots``/``serving_slot_tokens`` (the adapter's flight-side
geometry, which ``core.session.serving.merge_server_args`` writes back over
``-np``/``-c`` at attach time and which sizes the dispatcher's concurrency:
``workers = slots``). A flight whose baseline still said ``serving_slots``
4 would therefore attach with ``-np 4 -c 98304`` and be refused by the
resident-session identity check. So the derived baseline moves EXACTLY ONE
non-bookkeeping key against the PLAN lock baseline -- ``serving_slots`` 4 ->
1 -- and the composed-config diff this package registers names it as the
geometry key it is. No code change is needed to express the geometry.

WHAT DOES NOT MOVE. ``native_episode`` (role graph, policies, normaliser),
``knowledge_stores`` (all three stores, their release/snapshot pins, k,
fuse, rank weights), ``phase_material``, ``policy``, ``scorers``,
``decoding_params`` (temperature 0, seed 20260913, max_tokens 512, id_slot
per-sample), ``prompt_order``, ``speech_feature_root``, ``server_env``,
``task_instruction_*``, ``preparation_source_receipts``, the speech-feature
identity ids and the packet promotion receipt. The proof is
``tests/unit/test_stage3_det_np1_cells.py``, and the registration package's
``geometry-diff-v1.json`` lists the composed diff key by key with the
fragment each key comes from.

PASS A AND PASS B are two cells that differ ONLY in their run, attempt and
FIT identities and their prose -- the same shape as VAR1-PLAN and VAR1-PLANR.
Each carries no committed ``prepared_phase_supply``: the flip mints each
cell's own under its own run id (item E16) and pass B's output block MUST
reproduce pass A's byte for byte; a different value means the pair is not
request-identical -- stop and report, never pass ``--allow-output-change``.

MODEL-FREE. This script writes CONFIG ONLY: one model fragment, one roster
receipt, two baselines, two experiment fragments and two campaign plans. It
performs no contact, writes no ledger row, mints no decision receipt and
flips nothing. Zero model, tokenizer, encoder, scorer, server, GPU and
network contacts; no audio sample is decoded and no utterance text, gold
label or model output is read, printed or persisted.

    python scripts/flights/derive_slurp_det_np1_cells.py --write
    python scripts/flights/derive_slurp_det_np1_cells.py --check   # write nothing
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

sys.stdout.reconfigure(encoding="utf-8")

REPO_DEFAULT = Path(__file__).resolve().parents[2]

DATE = "2026-09-26"
CARRIER = "slurp"

# ---- the parents -------------------------------------------------------------
RESIDENT_MODEL = "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1"
PARENT_BASELINE = "configs/baseline/slurp-native-default-plan-lock-baseline-v1.json"
PARENT_EXPERIMENT = "configs/experiment/slurp-native-default-plan-lock-v1.json"
PARENT_RUN = "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1"
PARENT_ROSTER = "docs/receipts/rosters/slurp-evo-fold-a-v2.json"
RUNTIME_VIEW = "configs/dataset/slurp-speech-native-evo-fold-a-1080.json"
DATASET_FRAGMENT = "slurp-speech-native-evo-fold-a-1080"
RESIDENT_SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"

# ---- the new identities --------------------------------------------------------
DET_MODEL = (
    "q4km-mmproj-free-slurp-native-bounded-perception-proof-np1-nocache-ctx24k-max512-v1"
)
SESSION = "serving-slurp-native-det-np1-nocache-v1"
ROSTER_OUT = "docs/receipts/rosters/slurp-stage3-det-fold-a-50-v1.json"
ROSTER_ID = "SLURP-STAGE3-DET-FOLD-A-50-V1"
PACKAGE = "docs/readiness/2026-09-26-slurp-stage3-det-np1-fold-a-50-v1"
PREREG = PACKAGE + "-preregistration.md"
DECISION_ID = "slurp-stage3-det-np1-fold-a-50-admission-v1"
DECISION_RELPATH = "coordination/slurp-stage3-det-np1-fold-a-50-v1/root-admission-v1.json"
SLUG = "slurp-native-stage3-det-np1-fold-a-50"
RUN_STEM = "SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50"
READ_RUN = RUN_STEM + "-READ-V1"

ROWS = 50
#: The locked plan's own per-row contact ceiling: perception 1, solver 1,
#: reviewer 3, planner 1, max_revisions 1 -> 1 + 2 * (1 + 3 + 1) = 11.
CEILING = 11
#: The PLAN family's own ratios, reproduced rather than re-invented.
FIT_MULTIPLIER = 4
NATIVE_CONTRACT_PER_ROW = 6
#: The sealed PLAN arm's realised rate: 5,425 contacts over 1,080 rows and
#: 3.6819 GPU hours over those 5,425 contacts, on the np4 geometry.
PLAN_CONTACTS = 5425
PLAN_ROWS = 1080
PLAN_GPU_HOURS = 3.6819
#: A single slot serves one request at a time where four slots overlapped
#: four; the cost per contact is assumed to rise by up to this factor. It is
#: an assumption the flight measures, not a fact.
NP1_SLOWDOWN_ASSUMED = 4.0
GPU_HOURS_CAP = 2.0

MODEL_OUT = f"configs/model/{DET_MODEL}.json"


def pass_identity(p: str) -> dict[str, str]:
    P = p.upper()
    cell = f"{SLUG}-{p}-v1"
    return {
        "pass": p,
        "cell": cell,
        "experiment": cell,
        "baseline": f"{SLUG}-{p}-baseline-v1",
        "run_id": f"{RUN_STEM}-{P}-V1",
        "fit_run_id": f"{RUN_STEM}-{P}-FIT-V1",
        "attempt_id": f"attempt-{SLUG}-{p}-generation-v1",
        "fit_attempt_id": f"attempt-{SLUG}-{p}-fit-v1",
        "baseline_relpath": f"configs/baseline/{SLUG}-{p}-baseline-v1.json",
        "experiment_relpath": f"configs/experiment/{cell}.json",
        "campaign_relpath": f"configs/campaign/{cell}.json",
        "plan_prefix": p,
    }


PASSES = {p: pass_identity(p) for p in ("a", "b")}


class DetDeriveError(RuntimeError):
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
        raise DetDeriveError(f"{path} is unreadable: {error}") from error


def dump_like(raw: str, obj: Any) -> str:
    match = re.search(r"\n( +)\"", raw)
    indent = len(match.group(1)) if match else 2
    return json.dumps(obj, indent=indent, ensure_ascii=False, sort_keys=True) + (
        "\n" if raw.endswith("\n") else ""
    )


def dump(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def write_text(path: Path, text: str, *, write: bool) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if path.is_file() and rd(path) == text:
        print(f"  = {path.as_posix()} already present and identical ({digest[:16]})")
        return digest
    if not write:
        print(f"  (dry) would write {path.as_posix()} ({digest[:16]})")
        return digest
    path.parent.mkdir(parents=True, exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="").write(text)
    print(f"  + wrote {path.as_posix()} ({digest[:16]})")
    return digest


def import_repo(repo_root: Path):
    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from speech_aware_evidence_acquisition.core import roster as roster_module  # noqa: PLC0415
    from speech_aware_evidence_acquisition.data import splits  # noqa: PLC0415

    return roster_module, splits


# ---------------------------------------------------------------------------
# the serving geometry
# ---------------------------------------------------------------------------


def argv_flags(args: list[str]) -> dict[str, list[object]]:
    """``{flag: [value or True, ...]}`` -- the same shape
    ``core.session.serving._argv_map`` diffs, so the registered flag-by-flag
    diff is the one the resident-session identity check would print."""

    mapped: dict[str, list[object]] = {}
    index = 0
    while index < len(args):
        token = args[index]
        if not token.startswith("-"):
            mapped.setdefault("<positional>", []).append(token)
            index += 1
            continue
        value: object = True
        if index + 1 < len(args) and not args[index + 1].startswith("-"):
            value = args[index + 1]
            index += 2
        else:
            index += 1
        mapped.setdefault(token, []).append(value)
    return mapped


def geometry_flag_diff(resident_args: list[str], det_args: list[str]) -> list[dict[str, object]]:
    left, right = argv_flags(resident_args), argv_flags(det_args)
    diff = []
    for flag in sorted(set(left) | set(right)):
        if left.get(flag) != right.get(flag):
            diff.append({"flag": flag, "resident_np4": left.get(flag), "det_np1": right.get(flag)})
    return diff


#: The exact edits, so a drift in the resident fragment is a refusal here and
#: never a silently different geometry.
EXPECTED_RESIDENT_ARGS = [
    "-c", "98304", "-np", "4", "-b", "2048", "-ub", "512", "-fa", "on",
    "-ngl", "999", "-ctk", "q8_0", "-ctv", "q8_0", "--cache-prompt",
    "--cache-ram", "0", "--no-cache-idle-slots", "--slot-prompt-similarity", "0",
]
DET_ARGS = [
    "-c", "24576", "-np", "1", "-b", "2048", "-ub", "512", "-fa", "on",
    "-ngl", "999", "-ctk", "q8_0", "-ctv", "q8_0", "--no-cache-prompt",
    "--cache-ram", "0", "--no-cache-idle-slots",
]

GEOMETRY_BASIS = (
    "ONE decoder-only 24,576-token slot under c24576 np1 with the PROMPT CACHE OFF, "
    "for the Stage-3 determinism probe (cell DET). Against the resident geometry "
    f"({RESIDENT_MODEL}) exactly four flags move and nothing else: -np 4 -> 1 and -c 98304 "
    "-> 24576 (the slot stays 24,576 tokens, so prompt fit is unchanged), --cache-prompt -> "
    "--no-cache-prompt (llama.cpp defaults cache_prompt to TRUE and the transport sends no "
    "per-request cache_prompt field, so OFF must be the explicit server flag; with it the "
    "server sets n_past = 0 for every request and re-processes the whole prompt from an "
    "empty KV cache), and --slot-prompt-similarity 0 removed (slot selection by prompt "
    "similarity has no object with one slot and no cache). The same model file and sha256, "
    "the same runtime receipt (so --no-mmproj is injected exactly as before), -fa on, "
    "-ctk q8_0 -ctv q8_0, -b 2048 -ub 512, -ngl 999, --cache-ram 0, --no-cache-idle-slots, "
    "the same prepared speech packets, the same decoding params (temperature 0, seed "
    "20260913, max_tokens 512, id_slot per-sample), the same prompt order and the same "
    "server_env. The geometry is the ONE experimental variable of cell DET: greedy decoding "
    "under four-slot continuous batching with a prompt cache and a quantised KV cache is "
    "exactly the configuration in which llama.cpp is known not to be bitwise reproducible, "
    "and this fragment removes the batch-composition and cache-state terms so the flight "
    "can measure whether the programme's between-flight offset survives without them. A "
    "flight on this fragment attaches ONLY to a resident session started from it (the "
    "identity check compares server_argv flag by flag), which is why it queues behind the "
    "resident np4 session: one resident server per geometry, and the coordinator swaps it."
)


def build_model_fragment(repo_root: Path) -> tuple[str, str]:
    raw = rd(repo_root / "configs" / "model" / f"{RESIDENT_MODEL}.json")
    resident = json.loads(raw)
    if list(resident["server_args"]) != EXPECTED_RESIDENT_ARGS:
        raise DetDeriveError(
            f"the resident fragment's server_args are not the ones this derivation was "
            f"written against: {resident['server_args']!r}"
        )
    if resident.get("profile_slot_count") != 4:
        raise DetDeriveError("the resident fragment's profile_slot_count is not 4")
    if resident.get("decoding_params") != {
        "temperature": 0, "seed": 20260913, "max_tokens": 512, "id_slot": "per-sample"
    }:
        raise DetDeriveError("the resident fragment's decoding_params are not the locked ones")
    document = json.loads(json.dumps(resident))
    document["server_args"] = list(DET_ARGS)
    document["profile_slot_count"] = 1
    document["geometry_basis"] = GEOMETRY_BASIS
    # The key SET is the resident's: the fragment diff is exactly server_args,
    # profile_slot_count and geometry_basis, and nothing enters the composed
    # config that the resident does not already declare.
    if set(document) != set(resident):
        raise DetDeriveError("the derived model fragment must keep the resident's key set")
    return raw, dump_like(raw, document)


# ---------------------------------------------------------------------------
# the roster: a pure prefix of the committed Fold A receipt
# ---------------------------------------------------------------------------


def roster_facts(repo_root: Path) -> dict[str, Any]:
    _roster_module, splits = import_repo(repo_root)
    parent = read_json(repo_root / PARENT_ROSTER)
    view = read_json(repo_root / RUNTIME_VIEW)
    plan = read_json(repo_root / PARENT_EXPERIMENT)
    items = parent["items"][:ROWS]
    ids = [str(item["sample_id"]) for item in items]
    view_ids = [str(item["sample_id"]) for item in view["items"]]
    plan_ids = [str(sid) for sid in plan["populations"][0]["ids"]]
    if view_ids[:ROWS] != ids or plan_ids[:ROWS] != ids:
        raise DetDeriveError(
            "the first rows of the Fold A receipt, the runtime view and the PLAN "
            "populations list disagree; the prefix is not well defined"
        )
    seconds = {str(row["sample_id"]): float(row["audio_seconds"]) for row in view["items"]}
    total = sum(seconds[sid] for sid in ids)
    strata = dict(sorted(Counter(str(item["stratum"]) for item in items).items()))
    generation = ROWS * CEILING
    per_contact_np4 = PLAN_GPU_HOURS / PLAN_CONTACTS
    expected_contacts = round(ROWS * PLAN_CONTACTS / PLAN_ROWS)
    return {
        "ids": ids,
        "rows": ROWS,
        "audio_seconds_total": total,
        "split_identity_hash": splits.split_identity_hash(splits.prefixed(CARRIER, ids)),
        "id_list_sha256": hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest(),
        "strata": strata,
        "strata_covered": len(strata),
        "strata_in_parent": len(parent["strata_counts"]),
        "generation_calls_cap": generation,
        "fit_endpoint_calls_cap": generation * FIT_MULTIPLIER,
        "native_task_contract_calls_cap": ROWS * NATIVE_CONTRACT_PER_ROW,
        "repeated_speech_audio_seconds_cap": math.ceil(total * CEILING),
        "gpu_hours_fit_inclusive": GPU_HOURS_CAP,
        "expected_contacts": expected_contacts,
        "expected_gpu_hours_at_np4_rate": round(expected_contacts * per_contact_np4, 4),
        "expected_gpu_hours_at_assumed_np1_rate": round(
            expected_contacts * per_contact_np4 * NP1_SLOWDOWN_ASSUMED, 4
        ),
        "ceiling_gpu_hours_at_assumed_np1_rate": round(
            generation * per_contact_np4 * NP1_SLOWDOWN_ASSUMED, 4
        ),
        "np4_gpu_hours_per_contact": per_contact_np4,
    }


def build_roster(repo_root: Path) -> tuple[dict[str, Any], str]:
    roster_module, splits = import_repo(repo_root)
    parent = read_json(repo_root / PARENT_ROSTER)
    roster_module.verify_roster(parent)
    parent_items = parent["items"]
    if len(parent_items) < ROWS:
        raise DetDeriveError(f"{PARENT_ROSTER} carries fewer than {ROWS} items")
    items = [dict(item) for item in parent_items[:ROWS]]
    ids = [str(item["sample_id"]) for item in items]
    counts = dict(sorted(Counter(str(item["stratum"]) for item in items).items()))
    receipt: dict[str, Any] = {
        "schema": parent["schema"],
        "roster_id": ROSTER_ID,
        "carrier_lock_key": CARRIER,
        "split_role": "discovery",
        "roster_role": "construction",
        "seed": parent.get("seed"),
        "per_stratum": counts,
        "strata_counts": counts,
        "items": items,
        "excluded_count": len(parent_items) - len(items),
        "split_identity_hash": splits.split_identity_hash(splits.prefixed(CARRIER, ids)),
        "authority": (
            "Cell DET (the Stage-3 determinism probe): the flown population of both passes. "
            "A construction-role receipt of its own is required because the population is "
            "not the parent's: core.flight.campaign and contracts.gate_exposure bind a flight "
            "to the split identity of the rows it actually flies, and the ROLL-AA prefix "
            "receipt (SLURP-STAGE3-ROLL-AA-R01C-200-V1) is the precedent for committing a "
            "narrower construction population as its own receipt. The read driver "
            "scripts/analysis/slurp_paired_roster_read.py also needs a receipt whose items "
            "are exactly the flown rows."
        ),
        "roster_role_note": (
            "construction: cell DET reads no gold at runtime and produces no admission "
            "verdict. These TRAIN Fold A rows carry construction gold that the OFFLINE read "
            "scores both passes against for the pair's DESCRIPTIVE SLU-F1 and intent "
            "difference; the flight itself is the locked plan, unchanged, on a single-slot "
            "cache-off serving geometry, and the primary read -- per-row byte identity of "
            "the delivered answer between the two passes -- needs no gold at all."
        ),
        "draw_method": (
            "No draw. This receipt is a pure SELECTION of the parent receipt's frozen items: "
            "every surviving item is the parent's item verbatim, in the parent's order (the "
            "order the committed runtime view and the sealed PLAN arm's populations list "
            "share). The seed is the parent's and is carried for provenance only -- no rng is "
            "consulted anywhere in this build."
        ),
        "selection_rule": (
            f"The FIRST {ROWS} items of {PARENT_ROSTER}, in the parent's own order; order "
            "preserved. They are the first 50 rows the sealed PLAN arm "
            f"{PARENT_RUN} flew."
        ),
        "generator": "scripts/flights/derive_slurp_det_np1_cells.py",
        "parent": {
            "roster_id": parent.get("roster_id"),
            "count": len(parent_items),
            "relpath": PARENT_ROSTER,
            "split_identity_hash": parent.get("split_identity_hash"),
        },
        "stratum_coverage_note": (
            f"A PREFIX of the Fold A receipt is NOT scenario-stratified: these {ROWS} rows "
            f"cover {len(counts)} of the parent's {len(parent['strata_counts'])} scenario "
            f"strata ({', '.join(sorted(counts))}). The selection rule was specified as the "
            "first-N prefix and is registered as such; the per-stratum table is reported "
            "with that fact beside it. For a byte-identity question the mixture matters "
            "less than for a score: a row either repeats or it does not."
        ),
        "offline_guard": {"attempted_targets": [], "outbound_connection_attempts": 0},
    }
    for carried in ("d1_supplement", "disjointness_proof", "knowledge_source_guard"):
        if carried in parent:
            receipt[carried] = parent[carried]
    roster_module.verify_roster(receipt)
    return receipt, dump(receipt)


# ---------------------------------------------------------------------------
# baselines and experiments
# ---------------------------------------------------------------------------

BASELINE_BOOKKEEPING = ("native_contact_fit", "prepared_phase_supply", "what_this_is")


def what_this_is(p: str, facts: Mapping[str, Any]) -> str:
    ident = PASSES[p]
    other = PASSES["b" if p == "a" else "a"]
    return (
        f"Cell DET pass {p.upper()} ({ident['run_id']}): the LOCKED v2.0 plan, cell PLAN "
        f"({PARENT_RUN}), byte-identical in every knob -- the same three knowledge stores "
        "and their release/snapshot pins, the same k / fuse / rank weights, the same role "
        "graph, program, policies, normaliser, templates, scorers, decoding params, prompt "
        "order and prepared speech packets -- flown on the first "
        f"{ROWS} rows of TRAIN Fold A in roster order on a NEW serving geometry: one "
        "24,576-token slot (np1 c24576) with the prompt cache OFF (--no-cache-prompt) and no "
        f"--slot-prompt-similarity, model fragment {DET_MODEL}, resident session {SESSION}. "
        "Against configs/baseline/slurp-native-default-plan-lock-baseline-v1.json exactly ONE "
        "non-bookkeeping key moves: serving_slots 4 -> 1, the flight-side half of the "
        "geometry (rails.adapters.runtime_view reads it, core.session.serving.merge_server_args "
        "writes it back over -np/-c, and the dispatcher sizes its concurrency by it); "
        "serving_slot_tokens stays 24,576 so prompt fit is unchanged. The bookkeeping keys "
        "(native_contact_fit, the dropped prepared_phase_supply pin, this text) are per-cell. "
        f"Pass {p.upper()} and pass {other['pass'].upper()} ({other['run_id']}) are two cells "
        "that differ ONLY in their run, attempt and FIT identities and this text -- the "
        "VAR1-PLAN / VAR1-PLANR shape -- flown consecutively in ONE chain on ONE resident "
        "session, so that the per-row byte identity of the delivered answer between the two "
        "passes measures whether the programme's between-flight offset survives when batch "
        "composition and cache state are removed. Derived "
        f"{DATE} by scripts/flights/derive_slurp_det_np1_cells.py from {PARENT_BASELINE}. "
        "No committed prepared_phase_supply: the flip mints this cell's own under its own "
        "run id (item E16); pass B's output block must reproduce pass A's byte for byte, "
        "and --allow-output-change must never be passed."
    )


def build_baseline(repo_root: Path, p: str, facts: Mapping[str, Any]) -> tuple[str, str]:
    ident = PASSES[p]
    raw = rd(repo_root / PARENT_BASELINE)
    document = json.loads(raw)
    if document.get("serving_slots") != 4 or document.get("serving_slot_tokens") != 24576:
        raise DetDeriveError("the PLAN lock baseline's serving geometry is not np4 x 24,576")
    if "prepared_phase_supply" not in document:
        raise DetDeriveError("the PLAN lock baseline carries no prepared_phase_supply to drop")
    document["serving_slots"] = 1
    document["native_contact_fit"] = {
        "attempt_id": ident["fit_attempt_id"],
        "contact_cap": facts["fit_endpoint_calls_cap"],
        "max_speech_packets": 1,
        "run_id": ident["fit_run_id"],
    }
    document.pop("prepared_phase_supply")
    document["what_this_is"] = what_this_is(p, facts)
    return raw, dump_like(raw, document)


PURPOSE_COMMON = (
    "Cell DET, the Stage-3 determinism probe: is the programme's measurement floor an "
    "engineering artefact of the serving geometry or a property of the model? Two "
    "request-identical flights of the locked plan differ by +1.87 pp SLU at n = 625 (VAR1 "
    "PLAN vs PLANR, CI95 excluding zero) while inside one flight only 91.5 % of delivered "
    "answers are byte-identical (ROLL-AA, 183 of 200) -- on a server running FOUR slots "
    "under continuous batching with the prompt cache ON and a q8_0 KV cache, the "
    "configuration in which llama.cpp greedy decoding is known not to be bitwise "
    "reproducible. This cell flies the locked plan TWICE in one chain (pass A, pass B) on "
    f"the first {ROWS} rows of TRAIN Fold A, on ONE 24,576-token slot with the prompt cache "
    "OFF, everything else byte-identical, and reads per row whether the delivered answer "
    "repeats. If 50 of 50 rows are byte-identical across the passes the between-flight "
    "offset is an artefact of batch composition and cache state and the coordinator scales "
    "the probe to 200 rows for a floor re-estimate; if they are not, the offset is intrinsic "
    "to the model's numerics on this hardware and the programme stops hoping for a "
    "cheaper instrument along this axis. A 50-row cell cannot support a floor re-estimate "
    "-- it decides only whether the 200-row re-estimate is worth flying. FORM PROOF: "
    "claims_benefit false, expected_effect_pp 0.0, no admission mode; development numbers "
    "only (owner decisions 28 and 86); never a test claim. Nothing here authorises a flight, "
    "a readiness flip or an admission entry."
)


def build_experiment(repo_root: Path, p: str, facts: Mapping[str, Any]) -> tuple[str, str]:
    ident = PASSES[p]
    raw = rd(repo_root / PARENT_EXPERIMENT)
    document = json.loads(raw)
    cell = document["cells"][0]
    if cell["run_id"] != PARENT_RUN or cell["model_fragment"] != RESIDENT_MODEL:
        raise DetDeriveError("the PLAN lock experiment is not the one this derivation expects")
    cell["attempt_id"] = ident["attempt_id"]
    cell["baseline_fragment"] = ident["baseline"]
    cell["cell_id"] = ident["cell"]
    cell["model_fragment"] = DET_MODEL
    cell["run_id"] = ident["run_id"]
    cell["readiness"] = {
        "reason": (
            f"Cell DET pass {p.upper()}, registered before contact on {DATE} from the sealed "
            "PLAN lock fragments by script (decision 58): the locked plan on a single-slot, "
            "prompt-cache-off serving geometry, flown twice in one chain. HELD: root stops "
            f"the resident np4 session, starts {SESSION} from {DET_MODEL}, mints "
            f"{DECISION_RELPATH} (decision id {DECISION_ID}) with the four eligible run ids "
            "and re-pins with scripts/flights/repin_cell.py --set-ready, which also mints "
            "this cell's own first-phase supply under its own run id (item E16) and appends "
            "the preparation requirement. The requirements list is empty by design "
            "(core.flight.repin._set_preparation_requirement rewrites every preparation "
            "entry) and --allow-output-change must never be passed: pass B's supply must "
            "reproduce pass A's byte for byte. Nothing here authorises a flight, a "
            "readiness flip or an admission entry."
        ),
        "requirements": [],
        "state": "held",
    }
    document["date"] = DATE
    document["execution_plan"] = {
        "execution_profile": "bounded-discovery-probe",
        "planned_gpu_hours": facts["gpu_hours_fit_inclusive"],
        "planned_model_calls": facts["generation_calls_cap"],
        "planned_speech_audio_seconds": facts["repeated_speech_audio_seconds_cap"],
        "split_role": "discovery",
    }
    document["experiment_id"] = ident["run_id"]
    document["failure_policy"] = (
        "Stop and preserve on the first failure. No automatic restart, replay, row "
        "filtering, roster, role-graph, prompt, knowledge, geometry or cap change. AT MOST "
        "ONE root-diagnosed recovery re-registration for this run, and a second failure "
        "closes the pass: the fix is proven on a four-row dry run first. A resident-session "
        "identity refusal (the np4 session still resident, or a session started from a "
        "different fragment) is not a flight failure and spends no contact: the coordinator "
        "swaps the session and relaunches. A partial manifest is never scored and never "
        "read, and a pass that seals alone answers nothing: the read needs both."
    )
    document["family_budget"] = {
        "asr_calls": 0,
        "ceilings_are_not_targets": True,
        "encoder_calls": 0,
        "fit_endpoint_calls_cap": facts["fit_endpoint_calls_cap"],
        "generation_calls_cap": facts["generation_calls_cap"],
        "gpu_hours_fit_inclusive": facts["gpu_hours_fit_inclusive"],
        "native_task_contract_calls_cap": facts["native_task_contract_calls_cap"],
        "official_complete_scoring_jobs": 1,
        "repeated_speech_audio_seconds_cap": facts["repeated_speech_audio_seconds_cap"],
    }
    document["fragment_kind"] = f"saea-{SLUG}-{p}-v1"
    document["generation_budget"] = {
        "cap": facts["generation_calls_cap"],
        "definition": (
            "The locked plan's role graph is unchanged: perception 1, solver 1, reviewer 3, "
            "planner 1, max_revisions 1, so rails.native_episode_config.load_native_episode_"
            f"config resolves the program ceiling 1 + 2 * (1 + 3 + 1) = {CEILING} contacts "
            f"per row and {ROWS} x {CEILING} = {facts['generation_calls_cap']} is the exact "
            "program maximum rather than a conservative safety bound. The sealed PLAN arm's "
            f"realised rate was {PLAN_CONTACTS:,} contacts over {PLAN_ROWS:,} rows (5.023 per "
            f"row), which on these {ROWS} rows is about {facts['expected_contacts']} contacts "
            f"per pass. GPU hours: PLAN's own {PLAN_GPU_HOURS} h per {PLAN_CONTACTS:,} contacts "
            f"is {facts['np4_gpu_hours_per_contact']:.6f} h per contact on FOUR overlapping "
            "slots; a single slot serves one request at a time, so the per-contact cost is "
            f"assumed to rise by up to {NP1_SLOWDOWN_ASSUMED:g}x -- about "
            f"{facts['expected_gpu_hours_at_assumed_np1_rate']} h expected and "
            f"{facts['ceiling_gpu_hours_at_assumed_np1_rate']} h at the whole contact ceiling, "
            f"registered as {facts['gpu_hours_fit_inclusive']} h per pass. Both figures are "
            "assumptions the flight measures. The budget is RUN-CUMULATIVE across every "
            "attempt of this run id."
        ),
        "target": facts["expected_contacts"],
    }
    document["population"] = {
        "count": ROWS,
        "dataset_fragment": DATASET_FRAGMENT,
        "decision_population": (
            f"The first {ROWS} rows, in roster order, of TRAIN Fold A (SLURP-EVO-FOLD-A-V2), "
            f"committed as {ROSTER_OUT} ({ROSTER_ID}); the same first {ROWS} rows the sealed "
            f"PLAN arm {PARENT_RUN} flew, so a third comparison -- against the sealed np4 "
            "answers of the same rows -- is available offline at no cost. A PREFIX of the "
            f"Fold A receipt is not scenario-stratified: these rows cover "
            f"{facts['strata_covered']} of the parent's {facts['strata_in_parent']} scenario "
            "strata; the per-stratum table is reported with that fact beside it."
        ),
        "roster_receipt": ROSTER_OUT,
        "split_identity_hash": facts["split_identity_hash"],
    }
    document["populations"] = [{"dataset_fragment": DATASET_FRAGMENT, "ids": list(facts["ids"])}]
    document["purpose"] = (
        f"Pass {p.upper()} ({ident['run_id']}) of cell DET. " + PURPOSE_COMMON
    )
    document["service_session"] = SESSION
    document["stage3_algorithm"] = {
        "id": "none",
        "operators_used": [],
        "note": (
            "This cell carries NO training-free RL operator and says so explicitly: it is "
            "the locked plan, byte-identical, re-flown on a different serving geometry to "
            "measure the MEASUREMENT INSTRUMENT -- no rollout, no per-sample scoring, no "
            "credit assignment, no update operator, no evolving store, no learned context. "
            "The nearest labelled precedent, ROLL-AA, was declared shared-rollout because it "
            "exercised the grouped-Solver substrate; DET exercises no substrate beyond the "
            "plan itself and is a property of the rig, not of any algorithm."
        ),
    }
    return raw, dump_like(raw, document)


def build_campaign(p: str) -> str:
    ident = PASSES[p]
    return json.dumps(
        {"cells": [{"cell": ident["cell"], "experiment": ident["experiment"]}],
         "schema": "saea-campaign-plan-v1"},
        indent=2, ensure_ascii=False, sort_keys=True,
    ) + "\n"


def derived_artifacts(repo_root: Path) -> list[tuple[str, str]]:
    """Every file this derivation owns, as ``(relpath, text)``, in memory."""

    facts = roster_facts(repo_root)
    out: list[tuple[str, str]] = []
    out.append((MODEL_OUT, build_model_fragment(repo_root)[1]))
    out.append((ROSTER_OUT, build_roster(repo_root)[1]))
    for p in ("a", "b"):
        out.append((PASSES[p]["baseline_relpath"], build_baseline(repo_root, p, facts)[1]))
        out.append((PASSES[p]["experiment_relpath"], build_experiment(repo_root, p, facts)[1]))
        out.append((PASSES[p]["campaign_relpath"], build_campaign(p)))
    return out


def cmd_write(repo_root: Path, *, write: bool) -> int:
    facts = roster_facts(repo_root)
    print(json.dumps({k: v for k, v in facts.items() if k != "ids"}, indent=2, sort_keys=True))
    print("flag diff:", json.dumps(geometry_flag_diff(EXPECTED_RESIDENT_ARGS, DET_ARGS)))
    for relpath, text in derived_artifacts(repo_root):
        write_text(repo_root / relpath, text, write=write)
    return 0


def cmd_check(repo_root: Path) -> int:
    bad = 0
    roster_module, _splits = import_repo(repo_root)
    for relpath, text in derived_artifacts(repo_root):
        path = repo_root / relpath
        ok = path.is_file() and rd(path) == text
        print(f"verify {relpath}: {'OK' if ok else 'DISAGREES'}")
        bad += 0 if ok else 1
    if (repo_root / ROSTER_OUT).is_file():
        measured = roster_module.verify_roster(read_json(repo_root / ROSTER_OUT))
        expected = roster_facts(repo_root)["split_identity_hash"]
        ok = measured == expected
        print(f"verify roster identity {ROSTER_OUT}: {'OK' if ok else 'DISAGREES'} ({measured})")
        bad += 0 if ok else 1
    return 0 if bad == 0 else 3


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_DEFAULT))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="write the derived files")
    mode.add_argument("--dry", action="store_true", help="derive, print, write nothing")
    mode.add_argument("--check", action="store_true", help="re-derive and compare with disk")
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    if args.check:
        return cmd_check(repo_root)
    return cmd_write(repo_root, write=args.write)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DetDeriveError as error:  # pragma: no cover - CLI surface
        print(f"derive_slurp_det_np1_cells: FAIL: {error}", file=sys.stderr)
        raise SystemExit(2) from None
