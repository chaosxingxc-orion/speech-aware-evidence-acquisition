#!/usr/bin/env python3
"""The BAD-CASE BANK of the locked SLURP v2.0 plan.

A typed, counted, RUNTIME-OBSERVABLE taxonomy of where the locked plan loses, on the
TRAIN Fold A construction roster and on the fresh DEV-2000-ADDED roster, so that a
training-free RL rollout can be designed against a named failure mass instead of against
a global score. Owner directive 2026-09-24: analyse the bad cases first; training-free RL
gains come from rolling out variations of prompts, data and content construction over an
optimisation space, not from appending advice text.

Six things are produced, per roster:

1. a row-level error taxonomy of the PLAN arm -- intent wrong split by whether the gold
   intent was inside Perception's own candidate list (a SELECTION failure) or outside it
   (a COVERAGE failure), with the top confusion pairs; intent right but entities wrong,
   split FN-only / FP-only / mixed, by slot TYPE, and by whether the gold row carries any
   entity at all; the same-type filler mismatch and the equal-filler type swap, both as
   SHAPE statistics; and the malformed / abstained / revision-limit rows;
2. the stability classes PLAN vs the request-identical replicate PLANr -- STABLE-RIGHT,
   STABLE-WRONG and FLIPPING for intent and for entity exactness. FLIPPING is the roster's
   own noise band; STABLE-WRONG is the optimisation target, and its class composition is
   read off item 1;
3. what the plan already fixed against the bare core (the ``direct-only`` arm on the same
   roster and the same split identity): the class transition matrix direct -> PLAN, and
   the classes the plan leaves untouched;
4. runtime-observable signatures of every bad class -- things a policy may key on WITHOUT
   gold: Perception's candidate width, whether its candidate distinctions are distinct at
   all, scenario cohesion, delivered-candidate rank, the supplied exemplar count and their
   intent agreement with the top candidate, whether the supplied slot contracts carry the
   types the candidates usually carry, the Planner route and revision count, the deliver
   normaliser's own edits, context-fit compaction, far-field vs headset, utterance
   duration, response length and emitted entity count. Each is reported as a univariate
   distribution in the class against the STABLE-RIGHT rows; no model is fitted;
5. the exemplar and contract angle on the STABLE-WRONG entity rows -- what the twenty
   supplied exemplars looked like (count, intent agreement, entity-type coverage of the
   gold slot types, share carrying no entity at all) against the STABLE-RIGHT rows of the
   same delivered intent, and, on the date / time FN rows, whether the row's own supplied
   slot contract mentioned that slot at all;
6. a headroom table -- for every class, the pooled official SLU-F1 and intent accuracy in
   pp that a perfect repair of that class alone would return, on each roster, plus the
   STABLE-WRONG-only version, so rollout designs can be ranked by recoverable mass.

ZERO CONTACTS. No model, tokenizer, encoder, ASR, scorer, embedder, server, network, GPU
or paid-API contact of any kind. Every number comes from sealed per-row outputs, sealed
phase summaries, sealed flight receipts, sealed per-sample official scores, committed
roster receipts, released store snapshots, and the frozen SLURP gold read offline through
``data.slurp.load_slurp_split`` exactly as ``core.scoring_batch`` reads it.

LABELS, IDS, COUNTS, SHAPES AND HASHES ONLY. No utterance text, no transcript, no
delivered text, no gold filler, no predicted filler and no knowledge content is printed,
cached, or committed. Gold is a scoring input and appears only in aggregate tables. The
per-row bank this read writes (``bank.jsonl``) carries sample ids, class labels, slot TYPE
names, integers and booleans exclusively. The shape statistics -- token counts, digit
presence, ordinal and relative regex classes, normalised edit-distance buckets -- are
derived in-process from fillers that are never written anywhere.

REUSED LOADERS. The per-sample official projection and the pooled-F1 statistic are
``analysis.null_calibration_cli.rows_for`` and ``analysis.null_calibration.pooled_f1``;
the delivered-label parse is ``reproduction.slurp_scoring.parse_slu_response``; the gold
projection is ``data.slurp.load_slurp_split``; the phase-summary reader is
``scripts/analysis/stage3_delta_consumption_read.load_phase_results``; the per-slot-TYPE
exact decomposition is ``scripts/analysis/slurp_cell3_fresh_roster_loss_diagnostic``'s,
re-derived here and checked against the sealed official ``slot_f1_exact_{tp,fp,fn}``
totals of every arm before any table is rendered.

A DIAGNOSTIC, never a gate. It decides no cell, admits no mechanism, releases no store and
states no effectiveness, superiority or generalisation claim. TRAIN Fold A and
DEV-2000-ADDED numbers are development numbers (owner decisions 28 and 86) and are never a
test claim.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import re
import unicodedata
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))
_ANALYSIS_DIR = str(Path(__file__).resolve().parent)
if _ANALYSIS_DIR not in sys.path:
    sys.path.insert(0, _ANALYSIS_DIR)

from speech_aware_evidence_acquisition.analysis.null_calibration import (  # noqa: E402
    pooled_f1,
)
from speech_aware_evidence_acquisition.analysis.null_calibration_cli import (  # noqa: E402
    rows_for,
)
from speech_aware_evidence_acquisition.data.lock import load_lock  # noqa: E402
from speech_aware_evidence_acquisition.data.slurp import (  # noqa: E402
    _SPLIT_FILES,
    _governed_roots,
    load_slurp_split,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (  # noqa: E402
    parse_slu_response,
)

from stage3_delta_consumption_read import load_phase_results  # noqa: E402

RECIPE_ID = "slurp-plan-bad-case-bank-v1"
SCHEMA = "saea-slurp-plan-bad-case-bank-v1"
RUN_ID = "SAEA-SLURP-PLAN-BAD-CASE-BANK-V1"
OUT_DIRNAME = "SLURP-PLAN-BAD-CASE-BANK-V1"
DEFAULT_MARKDOWN = "docs/results/2026-09-24-slurp-plan-bad-case-bank.md"
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"

EXEMPLAR_STORE = "train-exemplars"
CONTRACT_STORE = "slot-contracts"
EXEMPLAR_SNAPSHOT = (
    "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json"
)
CONTRACT_SNAPSHOT = "knowledge/slurp/semantic/slot-contracts-v2/snapshot.json"

UNPARSED = "<unparsed>"

#: The two rosters this bank is built on. ``key`` names the roster everywhere; ``scorer``
#: is the sealed official scorer of that split role, and ``arms`` names the three sealed
#: attempts -- the locked PLAN, its request-identical replicate PLANr (the roster's own
#: null) and the bare-core ``direct-only`` arm flown on the same roster and the same split
#: identity hash.
ROSTERS = (
    {
        "key": "train-fold-a",
        "label": "TRAIN Fold A (construction roster, 1,080 rows)",
        "roster_relpath": "docs/receipts/rosters/slurp-evo-fold-a-v2.json",
        "split_id": "train",
        "scorer": "slurp-slu-official-train",
        "arms": {
            "plan": (
                "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1",
                "attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1",
            ),
            "planr": (
                "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-REPLICATE-V1",
                "attempt-slurp-native-default-plan-lock-replicate-train-fold-a-generation-v1",
            ),
            "direct": (
                "SAEA-SLURP-DIRECT-MAX512-TRAIN-FOLD-A-SOURCE-RECOVERY-V1",
                "attempt-slurp-direct-max512-train-fold-a-source-recovery-generation-v1",
            ),
        },
    },
    {
        "key": "dev2000-added",
        "label": "DEV-2000-ADDED (fresh roster, 1,000 rows)",
        "roster_relpath": "docs/receipts/rosters/slurp-dev-2000-added-v1.json",
        "split_id": "devel",
        "scorer": "slurp-slu-official",
        "arms": {
            "plan": (
                "SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1",
                "attempt-slurp-native-default-plan-dev2000-added-generation-v1",
            ),
            "planr": (
                "SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-REPLICATE-V1",
                "attempt-slurp-native-default-plan-dev2000-added-replicate-generation-v1",
            ),
            "direct": (
                "SAEA-SLURP-DIRECT-MAX512-DEV2000-ADDED-V1",
                "attempt-slurp-direct-max512-dev2000-added-generation-v1",
            ),
        },
    },
)
ARM_KEYS = ("plan", "planr", "direct")

PER_ROW_METRICS = ("scenario_action_exact", "scenario_exact", "action_exact", "slu_f1_f1")
MICRO_METRICS = {
    "slu_f1_micro": (
        ("slu_f1_word_tp", "slu_f1_char_tp"),
        ("slu_f1_word_fp", "slu_f1_char_fp"),
        ("slu_f1_word_fn", "slu_f1_char_fn"),
    ),
    "span_f1_micro": (
        ("slot_f1_exact_tp",),
        ("slot_f1_exact_fp",),
        ("slot_f1_exact_fn",),
    ),
}
OFFICIAL_FIELD = {"slu_f1_micro": "slu_f1", "span_f1_micro": "span_f1"}
COUNT_FIELDS = ("slot_f1_exact_tp", "slot_f1_exact_fp", "slot_f1_exact_fn", "parsed")
SCORE_FIELDS = tuple(
    dict.fromkeys(
        list(PER_ROW_METRICS)
        + [name for groups in MICRO_METRICS.values() for group in groups for name in group]
        + list(COUNT_FIELDS)
    )
)

#: The seven row classes. Mutually exclusive and exhaustive over a roster, evaluated in
#: this order, so a malformed row is never also counted as an intent error and an intent
#: error is never also counted as an entity error.
CLASSES = (
    "MALFORMED",
    "INTENT-UNCOVERED",
    "INTENT-COVERED",
    "ENTITY-FN-ONLY",
    "ENTITY-FP-ONLY",
    "ENTITY-MIXED",
    "CORRECT",
)
BAD_CLASSES = tuple(name for name in CLASSES if name != "CORRECT")
#: ``INTENT-UNCOVERED`` / ``INTENT-COVERED`` need Perception's candidate list, which a
#: direct arm does not have; on a direct arm the two collapse to ``INTENT-WRONG``.
DIRECT_CLASSES = (
    "MALFORMED",
    "INTENT-WRONG",
    "ENTITY-FN-ONLY",
    "ENTITY-FP-ONLY",
    "ENTITY-MIXED",
    "CORRECT",
)


class BankError(SystemExit):
    """Refuse rather than report a number this read cannot bind to sealed bytes."""


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            sha.update(chunk)
    return sha.hexdigest()


def sha_of(obj: object) -> str:
    return hashlib.sha256(
        json.dumps(obj, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def pct(value: float) -> float:
    return 100.0 * float(value)


def mean(values) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


# --------------------------------------------------------------------------
# Filler SHAPE features. Fillers enter these functions and never leave them:
# every return value is an integer, a boolean or a short class NAME.
# --------------------------------------------------------------------------

_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\s'-]", re.UNICODE)
_DIGIT_RE = re.compile(r"\d")
#: Numeric ordinals (``3rd``) and the written ordinals SLURP dates and times use.
_ORDINAL_RE = re.compile(
    r"\b(\d+(st|nd|rd|th)|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|"
    r"eleventh|twelfth|thirteenth|fourteenth|fifteenth|sixteenth|seventeenth|eighteenth|"
    r"nineteenth|twentieth|thirtieth)\b"
)
#: Deictic / relative temporal forms -- the family the A1 audit's P2 rungs cannot repair,
#: because they are a resolution question rather than a surface one.
_RELATIVE_RE = re.compile(
    r"\b(today|tonight|tomorrow|yesterday|now|next|last|this|coming|following|previous|"
    r"upcoming|weekend|morning|afternoon|evening|noon|midnight|current|later|soon)\b"
)
_MERIDIEM_RE = re.compile(r"\b([ap])\.?\s?m\.?\b")


def _fold(text: str) -> str:
    """Rung P2r0 of the A1 projection audit: casefold plus whitespace collapse."""
    return _WS_RE.sub(" ", unicodedata.normalize("NFKC", text).casefold()).strip()


def _fold_punct(text: str) -> str:
    """Rung P2r1: P2r0 plus punctuation stripped except apostrophes and hyphens."""
    return _WS_RE.sub(" ", _PUNCT_RE.sub(" ", _fold(text))).strip()


def _fold_meridiem(text: str) -> str:
    """Rung P2r2: P2r1 plus ``a.m.`` / ``p. m.`` folded to ``am`` / ``pm``."""
    return _WS_RE.sub(" ", _MERIDIEM_RE.sub(lambda m: m.group(1) + "m", _fold_punct(text))).strip()


def _edit_distance(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    previous = list(range(len(right) + 1))
    for i, lchar in enumerate(left, start=1):
        current = [i]
        for j, rchar in enumerate(right, start=1):
            current.append(
                min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (lchar != rchar))
            )
        previous = current
    return previous[-1]


def _distance_bucket(ratio: float) -> str:
    if ratio <= 0.0:
        return "0 (equal after folding)"
    if ratio <= 0.20:
        return "(0, 0.20]"
    if ratio <= 0.50:
        return "(0.20, 0.50]"
    if ratio <= 0.80:
        return "(0.50, 0.80]"
    return "(0.80, 1.00]"


def filler_shape(text: str) -> dict:
    """Shape of ONE filler. No character of ``text`` survives this call."""
    folded = _fold_punct(text)
    return {
        "tokens": len(folded.split()) if folded else 0,
        "chars": len(text),
        "has_digit": bool(_DIGIT_RE.search(text)),
        "has_ordinal": bool(_ORDINAL_RE.search(_fold(text))),
        "has_relative": bool(_RELATIVE_RE.search(_fold(text))),
        "has_meridiem": bool(_MERIDIEM_RE.search(_fold(text))),
    }


def pair_shape(predicted: str, gold: str) -> dict:
    """Shape of a same-type (predicted, gold) mismatch pair. Text never leaves this call.

    ``repair_rung`` names the cheapest A1 projection rung that would have made the two
    equal -- ``case-whitespace``, ``punctuation``, ``meridiem``, ``none`` -- which is the
    difference between a RENDERING defect the USE axis can normalise away and a real
    observation or resolution defect that only a different OBS / SUPPLY construction can
    reach. ``boundary`` marks the containment case: one side is a span of the other.
    """
    pshape = filler_shape(predicted)
    gshape = filler_shape(gold)
    rung = "none"
    if predicted == gold:
        rung = "identical"
    elif _fold(predicted) == _fold(gold):
        rung = "case-whitespace"
    elif _fold_punct(predicted) == _fold_punct(gold):
        rung = "punctuation"
    elif _fold_meridiem(predicted) == _fold_meridiem(gold):
        rung = "meridiem"
    left, right = _fold_punct(predicted), _fold_punct(gold)
    distance = _edit_distance(left, right)
    ratio = distance / max(len(left), len(right), 1)
    contained = bool(left) and bool(right) and (left in right or right in left) and left != right
    return {
        "repair_rung": rung,
        "boundary_containment": contained,
        "predicted_tokens": pshape["tokens"],
        "gold_tokens": gshape["tokens"],
        "token_delta": pshape["tokens"] - gshape["tokens"],
        "predicted_has_digit": pshape["has_digit"],
        "gold_has_digit": gshape["has_digit"],
        "gold_has_ordinal": gshape["has_ordinal"],
        "gold_has_relative": gshape["has_relative"],
        "gold_has_meridiem": gshape["has_meridiem"],
        "distance_bucket": _distance_bucket(ratio),
    }


# --------------------------------------------------------------------------
# Loading: rosters, manifests, sealed scores, sealed outputs, sealed phases
# --------------------------------------------------------------------------


def load_roster(repo: Path, relpath: str) -> dict:
    """Ids plus the two runtime-observable carrier facts: channel and duration."""
    path = repo / relpath
    document = json.loads(path.read_text(encoding="utf-8"))
    items = document.get("items") or []
    ids: list[str] = []
    channel: dict[str, str] = {}
    seconds: dict[str, float] = {}
    stratum: dict[str, str] = {}
    for item in items:
        sample_id = item.get("sample_id") or item.get("id")
        if not isinstance(sample_id, str):
            raise BankError(f"{path}: an item carries no sample_id")
        ids.append(sample_id)
        channel[sample_id] = "headset" if item.get("headset") else "far_field"
        duration = item.get("audio_seconds")
        if not isinstance(duration, (int, float)) or isinstance(duration, bool):
            raise BankError(f"{path}: item {sample_id!r} carries no audio_seconds")
        seconds[sample_id] = float(duration)
        value = item.get("stratum")
        stratum[sample_id] = value if isinstance(value, str) else "<none>"
    if len(set(ids)) != len(ids):
        raise BankError(f"{path}: repeats a sample_id")
    return {
        "relpath": relpath,
        "path": str(path),
        "sha256": digest(path),
        "roster_id": document.get("roster_id"),
        "split_role": document.get("split_role"),
        "split_identity_hash": document.get("split_identity_hash"),
        "ids": sorted(ids),
        "channel": channel,
        "audio_seconds": seconds,
        "stratum": stratum,
    }


def arm_dir(data_root: Path, run_id: str, attempt_id: str) -> Path:
    directory = data_root / "runs" / run_id / attempt_id
    if not directory.is_dir():
        raise BankError(f"sealed attempt directory missing: {directory}")
    return directory


def load_manifest(directory: Path, run_id: str, expected_hash: str) -> dict:
    path = directory / f"{run_id}.run-manifest.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("status") != "COMPLETED":
        raise BankError(f"{run_id}: manifest is not COMPLETED")
    if document.get("study_repo_dirt"):
        raise BankError(f"{run_id}: sealed with a dirty study tree")
    split = document.get("split") or {}
    if split.get("identity_hash") != expected_hash:
        raise BankError(
            f"{run_id}: manifest split identity {split.get('identity_hash')} is not the roster's"
        )
    return {
        "path": str(path),
        "sha256": digest(path),
        "status": document.get("status"),
        "study_commit": document.get("study_commit"),
        "config_hash": ((document.get("config") or {}).get("config_hash")),
        "fragments": ((document.get("config") or {}).get("fragments") or {}),
        "split_role": split.get("role"),
        "split_count": split.get("count"),
        "split_identity_hash": split.get("identity_hash"),
    }


def load_scores(directory: Path, run_id: str, scorer: str, ids: list[str]) -> dict:
    """Sealed per-sample official rows, verified to reproduce the sealed aggregate."""
    path = directory / f"{run_id}.scores.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = rows_for({"verified": True, "scores": raw}, scorer, SCORE_FIELDS)
    missing = sorted(set(ids) - set(rows))
    if missing:
        raise BankError(f"{run_id}: per_sample is missing {len(missing)} roster rows")
    official = ((raw.get(scorer) or {}).get("aggregate") or {}).get("official") or {}
    for metric, groups in MICRO_METRICS.items():
        field = OFFICIAL_FIELD[metric]
        published = official.get(field)
        recomputed = pooled_f1(rows, ids, groups)
        if not isinstance(published, (int, float)) or isinstance(published, bool):
            raise BankError(f"{run_id}: official aggregate has no numeric {field!r}")
        if abs(recomputed - float(published)) > 1e-6:
            raise BankError(
                f"{run_id}: recomputed {metric} {recomputed} does not reproduce the official "
                f"{published} to 1e-6"
            )
    return {
        "path": str(path),
        "sha256": digest(path),
        "rows": rows,
        "official": {
            "slu_f1": float(official.get("slu_f1")),
            "span_f1": float(official.get("span_f1")),
            "intent_accuracy": float(official.get("intent_accuracy")),
            "action_accuracy": float(official.get("action_accuracy")),
        },
    }


def load_delivered(directory: Path, run_id: str, wanted: set[str]) -> dict:
    """Delivered LABELS and the (type, filler) pairs of every wanted row.

    The fillers never leave this process: they are consumed by :func:`row_entity_view` and
    only per-TYPE integer counts and SHAPE class names are written anywhere.
    """
    path = directory / f"{run_id}.outputs.jsonl"
    rows: dict[str, dict] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            sample_id = record.get("sample_id")
            if sample_id not in wanted:
                continue
            text = record.get("text") or ""
            scenario, action, entities, parsed = parse_slu_response(text)
            rows[sample_id] = {
                "parsed": bool(parsed),
                "scenario": scenario if isinstance(scenario, str) else None,
                "action": action if isinstance(action, str) else None,
                "intent": (
                    f"{scenario}_{action}"
                    if parsed and isinstance(scenario, str) and isinstance(action, str)
                    else UNPARSED
                ),
                "entities": list(entities),
                "entity_count": len(entities),
                "entity_types": sorted(entity.type for entity in entities),
                "response_chars": len(text),
            }
    missing = sorted(wanted - set(rows))
    if missing:
        raise BankError(f"{run_id}: outputs are missing {len(missing)} roster rows")
    return {"path": str(path), "sha256": digest(path), "rows": rows}


def load_plan_runtime(directory: Path, run_id: str, wanted: set[str]) -> dict:
    """The PLAN arm's own runtime-observable per-row state, from the sealed phase summaries.

    Everything here is available to a policy at RUNTIME without gold: Perception's own
    candidate list and how committed it was, the value ids the E6 acquire transition
    actually delivered to the Solver, the Planner's route and revision count, the deliver
    normaliser's edits, and the context-fit compaction.

    ``distinct_distinctions`` counts the DISTINCT candidate distinction strings by sha256
    -- the strings themselves never leave this function. A Perception state that proposes
    three candidates with one single distinction has not distinguished anything, and that
    is a signal a rollout may key on.
    """
    phases = load_phase_results(directory, run_id)
    per_row: dict[str, dict] = {}
    parse_failures = 0
    for result in phases["results"]:
        sample_id = result.get("sample_id")
        if sample_id not in wanted:
            continue
        first: list[str] | None = None
        union: list[str] = []
        perception_states = 0
        distinction_hashes: list[str] = []
        unresolved = 0
        for state in result.get("agent_states") or ():
            if state.get("state_kind") != "phase:perception":
                continue
            perception_states += 1
            try:
                payload = json.loads(state.get("content") or "")
            except (TypeError, ValueError):
                parse_failures += 1
                continue
            candidates = payload.get("candidates") if isinstance(payload, dict) else None
            if not isinstance(candidates, list):
                parse_failures += 1
                continue
            ids = []
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    continue
                intent_id = candidate.get("intent_id")
                if isinstance(intent_id, str):
                    ids.append(intent_id)
                if first is None:
                    distinction = candidate.get("distinction")
                    if isinstance(distinction, str):
                        distinction_hashes.append(sha_of(distinction))
                    fields = candidate.get("unresolved_fields")
                    unresolved += len(fields) if isinstance(fields, list) else 0
            if first is None:
                first = list(ids)
            for intent_id in ids:
                if intent_id not in union:
                    union.append(intent_id)
        first = first or []
        supplied: dict[str, list[str]] = defaultdict(list)
        for wave in result.get("waves") or ():
            transition = wave.get("transition")
            if not isinstance(transition, dict):
                continue
            for value_id in transition.get("new_value_ids") or ():
                if not isinstance(value_id, str) or "::" not in value_id:
                    continue
                store, bare = value_id.split("::", 1)
                if bare not in supplied[store]:
                    supplied[store].append(bare)
        receipt = result.get("native_episode_receipt") or {}
        routes = [r for r in (receipt.get("planner_routes") or ()) if isinstance(r, dict)]
        visits = [v for v in (receipt.get("role_visits") or ()) if isinstance(v, dict)]
        normaliser = receipt.get("deliver_normaliser") or {}
        fit = receipt.get("context_fit") or {}
        metrics = result.get("metrics") or {}
        per_row[sample_id] = {
            "perception_states": perception_states,
            "candidates_first": first,
            "candidates_union": union,
            "candidate_width": len(first),
            "distinct_distinctions": len(set(distinction_hashes)),
            "candidate_scenarios": sorted({cid.split("_", 1)[0] for cid in first if "_" in cid}),
            "unresolved_fields": unresolved,
            "supplied": {store: sorted(values) for store, values in sorted(supplied.items())},
            "planner_actions": [str(r.get("action")) for r in routes],
            "revision_count": max((int(r.get("revision_count") or 0) for r in routes), default=0),
            "role_visits": Counter(str(v.get("role_id")) for v in visits),
            "normaliser_applied": bool(normaliser.get("applied")),
            "normaliser_changed": bool(normaliser.get("changed")),
            "normaliser_fillers_changed": int(normaliser.get("fillers_changed") or 0),
            "normaliser_labels_changed": int(normaliser.get("labels_changed") or 0),
            "compacted_contacts": int(fit.get("compacted_contacts") or 0),
            "slot_tokens": int(fit.get("slot_tokens") or 0),
            "contacts": len(result.get("contacts") or ()),
            "response_chars": int(metrics.get("response_chars") or 0),
        }
    missing = sorted(wanted - set(per_row))
    if missing:
        raise BankError(f"{run_id}: phase results are missing {len(missing)} roster rows")
    return {
        "path": phases["path"],
        "sha256": phases["sha256"],
        "controller_policy_id": phases["controller_policy_id"],
        "candidate_parse_failures": parse_failures,
        "rows": per_row,
    }


def verify_supply_against_receipt(directory: Path, run_id: str, runtime: dict) -> dict:
    """Cross-check the transition-derived slot-contract supply against the flight receipt.

    The sealed ``phase_supply.candidate_selections`` block is the flight's own receipt of
    what the candidate-semantic provider selected per row; the transitions are what the
    episode actually carried. They must agree on every row, or this read refuses.
    """
    path = directory / "flight-receipts.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    supply = ((document.get("stages") or {}).get("run_phases") or {}).get("phase_supply") or {}
    selections = supply.get("candidate_selections") or {}
    if not selections:
        raise BankError(f"{run_id}: flight receipt carries no candidate_selections")
    receipted: dict[str, set[str]] = defaultdict(set)
    for entry in selections.values():
        sample_id = entry.get("sample_id")
        if not isinstance(sample_id, str):
            continue
        for value_id in entry.get("qualified_selected_value_ids") or ():
            if isinstance(value_id, str) and value_id.startswith(f"{CONTRACT_STORE}::"):
                receipted[sample_id].add(value_id.split("::", 1)[1])
    disagreements = 0
    for sample_id, state in runtime["rows"].items():
        carried = set(state["supplied"].get(CONTRACT_STORE) or ())
        if sample_id in receipted and receipted[sample_id] != carried:
            disagreements += 1
    if disagreements:
        raise BankError(
            f"{run_id}: {disagreements} rows disagree between the sealed candidate-selection "
            "receipt and the transitions the episode carried"
        )
    return {
        "path": str(path),
        "sha256": digest(path),
        "selection_events": len(selections),
        "rows_with_receipt": len(receipted),
        "disagreements": 0,
    }


def load_exemplar_labels(data_root: Path) -> dict:
    """``value_id -> {intent, entity_types}`` for the released exemplar store.

    Each exemplar renders as ``<utterance> | <scenario>_<action> | type=filler; ...``
    (KB view ``annotated-exemplars``). Only the middle label and the TYPE names of the
    third field are kept; the utterance and every filler are discarded here and never
    written.
    """
    path = data_root / EXEMPLAR_SNAPSHOT
    document = json.loads(path.read_text(encoding="utf-8"))
    labels: dict[str, dict] = {}
    for value in document["values"]:
        content = value.get("content") or ""
        parts = [part.strip() for part in content.split("|")]
        intent = parts[1] if len(parts) > 1 else UNPARSED
        types: list[str] = []
        if len(parts) > 2 and parts[2]:
            for chunk in parts[2].split(";"):
                name = chunk.split("=", 1)[0].strip()
                if name:
                    types.append(name)
        labels[value["value_id"]] = {
            "intent": intent,
            "entity_types": sorted(set(types)),
            "entity_type_count": len(types),
        }
    spread = Counter(entry["entity_type_count"] for entry in labels.values())
    return {
        "path": str(path),
        "sha256": digest(path),
        "declared_snapshot_sha256": document.get("snapshot_sha256"),
        "values": labels,
        "composition": {
            "values": len(labels),
            "entity_free_values": spread.get(0, 0),
            "entity_count_spread": dict(sorted(spread.items())),
            "distinct_intents": len({entry["intent"] for entry in labels.values()}),
        },
    }


def load_contract_types(data_root: Path) -> dict:
    """``value_id -> slot TYPE`` for the released slot-contract store."""
    path = data_root / CONTRACT_SNAPSHOT
    document = json.loads(path.read_text(encoding="utf-8"))
    types = {
        value["value_id"]: value["value_id"].split(":", 1)[1]
        for value in document["values"]
        if isinstance(value.get("value_id"), str) and ":" in value["value_id"]
    }
    return {
        "path": str(path),
        "sha256": digest(path),
        "declared_snapshot_sha256": document.get("snapshot_sha256"),
        "types": types,
    }


def gold_records(lock_path: Path, data_root: Path, split_id: str) -> dict:
    """The frozen gold of ``split_id``, read through the study's own governed loader.

    The loader re-verifies every recording against its flac header, which is slow on the
    first call of a session; the DERIVED per-row counts are cached by :func:`derive_rows`
    so a re-run costs nothing. Gold fillers exist only inside this process.
    """
    lock = load_lock(lock_path)
    metadata_path = _governed_roots(lock, data_root)[2] / _SPLIT_FILES[split_id]
    records = load_slurp_split(lock, data_root, split_id)
    return {
        "metadata_path": str(metadata_path),
        "metadata_sha256": digest(metadata_path),
        "records": {record.sample_id: record for record in records},
    }


# --------------------------------------------------------------------------
# Per-row entity decomposition
# --------------------------------------------------------------------------


def row_entity_view(gold_entities, predicted_entities) -> dict:
    """Decompose one row's entity outcome into the four loss components.

    Step 1 is the official matcher: ``SpanFMeasure`` matches a predicted entity to a gold
    entity only on an exact ``(type, filler)`` equality, so ``per_type`` reproduces the
    sealed ``slot_f1_exact_{tp,fp,fn}`` of the row exactly (asserted by the caller).

    Steps 2-4 then attribute the UNMATCHED remainder, following the 2026-09-16 handoff
    report's own decomposition so the two are comparable:

    * ``same_type`` -- a predicted entity of type ``t`` sits beside an unmatched gold entity
      of the same type: the filler is wrong, the type is right. Paired greedily by
      normalised edit distance, ties broken by position, so the pairing is deterministic.
    * ``type_swap`` -- an unmatched predicted filler equals an unmatched gold filler under a
      DIFFERENT type (the handoff's equal-filler heuristic, applied after folding).
    * ``over_emission`` -- a predicted entity with no unmatched gold left to explain it.
    * ``omission`` -- an unmatched gold entity with nothing predicted of that type.

    Fillers enter here and leave only as integers and SHAPE class names.
    """
    remaining_gold = list(gold_entities)
    tp: Counter = Counter()
    fp: Counter = Counter()
    unmatched_pred = []
    for entity in predicted_entities:
        if entity in remaining_gold:
            tp[entity.type] += 1
            remaining_gold.remove(entity)
        else:
            fp[entity.type] += 1
            unmatched_pred.append(entity)
    fn = Counter(entity.type for entity in remaining_gold)

    by_type_pred: dict[str, list] = defaultdict(list)
    for index, entity in enumerate(unmatched_pred):
        by_type_pred[entity.type].append((index, entity))
    by_type_gold: dict[str, list] = defaultdict(list)
    for index, entity in enumerate(remaining_gold):
        by_type_gold[entity.type].append((index, entity))

    same_type: list[dict] = []
    used_pred: set[int] = set()
    used_gold: set[int] = set()
    for slot_type in sorted(set(by_type_pred) & set(by_type_gold)):
        options = []
        for pindex, pentity in by_type_pred[slot_type]:
            for gindex, gentity in by_type_gold[slot_type]:
                left, right = _fold_punct(pentity.filler), _fold_punct(gentity.filler)
                distance = _edit_distance(left, right) / max(len(left), len(right), 1)
                options.append((distance, pindex, gindex, pentity, gentity))
        for _, pindex, gindex, pentity, gentity in sorted(options, key=lambda o: o[:3]):
            if pindex in used_pred or gindex in used_gold:
                continue
            used_pred.add(pindex)
            used_gold.add(gindex)
            shape = pair_shape(pentity.filler, gentity.filler)
            shape["slot_type"] = slot_type
            same_type.append(shape)

    swap: list[dict] = []
    gold_by_filler: dict[str, list[int]] = defaultdict(list)
    for gindex, gentity in enumerate(remaining_gold):
        if gindex not in used_gold:
            gold_by_filler[_fold_punct(gentity.filler)].append(gindex)
    for pindex, pentity in enumerate(unmatched_pred):
        if pindex in used_pred:
            continue
        key = _fold_punct(pentity.filler)
        matches = [g for g in gold_by_filler.get(key, ()) if g not in used_gold]
        if not matches:
            continue
        gindex = matches[0]
        used_pred.add(pindex)
        used_gold.add(gindex)
        swap.append(
            {
                "predicted_type": pentity.type,
                "gold_type": remaining_gold[gindex].type,
            }
        )

    over = Counter(
        entity.type for index, entity in enumerate(unmatched_pred) if index not in used_pred
    )
    omitted = Counter(
        entity.type for index, entity in enumerate(remaining_gold) if index not in used_gold
    )
    return {
        "per_type": {"tp": dict(tp), "fp": dict(fp), "fn": dict(fn)},
        "same_type": same_type,
        "type_swap": swap,
        "over_emission": dict(over),
        "omission": dict(omitted),
        "gold_entity_types": sorted({entity.type for entity in gold_entities}),
        "gold_entity_count": len(list(gold_entities)),
    }


def derive_rows(*, ids, gold, delivered, scores, run_id) -> dict:
    """Per row, the entity view plus the gold labels, checked against the sealed counts."""
    rows: dict[str, dict] = {}
    for sample_id in ids:
        record = gold["records"].get(sample_id)
        if record is None:
            raise BankError(f"{run_id}: gold is missing roster row {sample_id!r}")
        view = row_entity_view(record.entities, delivered["rows"][sample_id]["entities"])
        sealed = scores["rows"][sample_id]
        for name, key in (("tp", "slot_f1_exact_tp"), ("fp", "slot_f1_exact_fp"), ("fn", "slot_f1_exact_fn")):
            derived = sum(view["per_type"][name].values())
            if abs(derived - sealed[key]) > 1e-9:
                raise BankError(
                    f"{run_id}: row {sample_id} derived {name}={derived} does not reproduce the "
                    f"sealed official {key}={sealed[key]}"
                )
        view["gold_intent"] = record.intent
        view["gold_scenario"] = record.scenario
        rows[sample_id] = view
    return rows


def classify(*, ids, derived, delivered, scores, runtime) -> dict:
    """The seven exclusive classes plus the cross-cutting disposition flags.

    Ordered attribution: a malformed delivery is never also an intent error, and an intent
    error is never also an entity error. ``runtime`` is ``None`` for the bare-core direct
    arm, which has no Perception candidate list; there the two intent classes collapse to
    ``INTENT-WRONG``.
    """
    classes: dict[str, str] = {}
    detail: dict[str, dict] = {}
    for sample_id in ids:
        sealed = scores["rows"][sample_id]
        view = derived[sample_id]
        out = delivered["rows"][sample_id]
        intent_ok = sealed["scenario_action_exact"] >= 0.5
        fp = sum(view["per_type"]["fp"].values())
        fn = sum(view["per_type"]["fn"].values())
        if sealed["parsed"] < 0.5:
            name = "MALFORMED"
        elif not intent_ok:
            if runtime is None:
                name = "INTENT-WRONG"
            else:
                covered = view["gold_intent"] in runtime["rows"][sample_id]["candidates_union"]
                name = "INTENT-COVERED" if covered else "INTENT-UNCOVERED"
        elif fp and fn:
            name = "ENTITY-MIXED"
        elif fn:
            name = "ENTITY-FN-ONLY"
        elif fp:
            name = "ENTITY-FP-ONLY"
        else:
            name = "CORRECT"
        classes[sample_id] = name
        state = runtime["rows"][sample_id] if runtime is not None else {}
        detail[sample_id] = {
            "intent_ok": intent_ok,
            "entity_exact": (not fp) and (not fn),
            "fp": fp,
            "fn": fn,
            "gold_has_entity": view["gold_entity_count"] > 0,
            "emitted": out["entity_count"],
            "abstained": out["entity_count"] == 0 and out["intent"] == UNPARSED,
            "revision_limit": bool(state) and state.get("revision_count", 0) >= 1,
        }
    return {"classes": classes, "detail": detail}


def stability(*, ids, plan_classes, planr_classes, plan_detail, planr_detail) -> dict:
    """STABLE-RIGHT / STABLE-WRONG / FLIPPING for intent and for entity exactness.

    FLIPPING is the roster's own run-to-run noise band on a request-identical replicate:
    a rollout that only moves flipping rows has moved nothing. STABLE-WRONG is the target.
    """
    intent: dict[str, str] = {}
    entity: dict[str, str] = {}
    joint: dict[str, str] = {}
    for sample_id in ids:
        left, right = plan_detail[sample_id], planr_detail[sample_id]
        for bucket, field in ((intent, "intent_ok"), (entity, "entity_exact")):
            a, b = left[field], right[field]
            bucket[sample_id] = (
                "STABLE-RIGHT" if a and b else "STABLE-WRONG" if not a and not b else "FLIPPING"
            )
        a = left["intent_ok"] and left["entity_exact"]
        b = right["intent_ok"] and right["entity_exact"]
        joint[sample_id] = (
            "STABLE-RIGHT" if a and b else "STABLE-WRONG" if not a and not b else "FLIPPING"
        )
    return {
        "intent": intent,
        "entity": entity,
        "joint": joint,
        "counts": {
            axis: dict(Counter(bucket.values()))
            for axis, bucket in (("intent", intent), ("entity", entity), ("joint", joint))
        },
        "plan_classes_by_stability": {
            axis: {
                state: dict(
                    Counter(plan_classes[sid] for sid in ids if bucket[sid] == state)
                )
                for state in ("STABLE-RIGHT", "STABLE-WRONG", "FLIPPING")
            }
            for axis, bucket in (("intent", intent), ("entity", entity), ("joint", joint))
        },
    }


# --------------------------------------------------------------------------
# Headroom
# --------------------------------------------------------------------------


def headroom(*, ids, rows, members) -> dict:
    """Pooled official SLU-F1 and span-F1 if every row of ``members`` were repaired.

    A perfectly repaired row delivers gold exactly, so every unmatched gold unit becomes a
    matched one and nothing spurious remains: ``tp -> tp + fn``, ``fp -> 0``, ``fn -> 0``,
    at word, char and exact-span level alike. That identity makes this an EXACT upper
    bound on the pooled statistic, not an estimate -- the roster's other rows are untouched.
    """
    member_set = set(members)
    result = {}
    for metric, groups in MICRO_METRICS.items():
        tp_names, fp_names, fn_names = groups
        base = [0.0, 0.0, 0.0]
        fixed = [0.0, 0.0, 0.0]
        for sample_id in ids:
            row = rows[sample_id]
            tp = sum(row[name] for name in tp_names)
            fp = sum(row[name] for name in fp_names)
            fn = sum(row[name] for name in fn_names)
            base[0] += tp
            base[1] += fp
            base[2] += fn
            if sample_id in member_set:
                fixed[0] += tp + fn
            else:
                fixed[0] += tp
                fixed[1] += fp
                fixed[2] += fn
        def f1(totals):
            tp, fp, fn = totals
            return 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0
        now, repaired = pct(f1(base)), pct(f1(fixed))
        result[metric] = {"now": now, "repaired": repaired, "recoverable_pp": repaired - now}
    return result


def intent_headroom(*, ids, rows, members) -> dict:
    member_set = set(members)
    now = sum(1 for sid in ids if rows[sid]["scenario_action_exact"] >= 0.5)
    repaired = now + sum(
        1 for sid in ids if sid in member_set and rows[sid]["scenario_action_exact"] < 0.5
    )
    total = len(ids)
    return {
        "now": pct(now / total),
        "repaired": pct(repaired / total),
        "recoverable_pp": pct((repaired - now) / total),
    }


# --------------------------------------------------------------------------
# Runtime-observable signatures
# --------------------------------------------------------------------------

#: Every signature a policy may key on at RUNTIME, without gold. ``kind`` decides how the
#: univariate table summarises it: ``share`` prints the percentage of rows for which the
#: boolean holds, ``mean`` prints the arithmetic mean.
SIGNATURES = (
    ("candidate_width", "mean", "Perception candidates proposed (1-3)"),
    ("distinct_distinctions", "mean", "distinct candidate distinctions"),
    ("degenerate_distinctions", "share", "candidates share one distinction"),
    ("candidate_scenarios", "mean", "distinct scenarios among the candidates"),
    ("delivered_in_candidates", "share", "delivered intent was a candidate"),
    ("delivered_candidate_rank", "mean", "rank of the delivered intent (0 = off-list)"),
    ("exemplars_supplied", "mean", "exemplars delivered to the Solver"),
    ("exemplar_top_agreement", "mean", "share of exemplars whose intent is candidate 1"),
    ("exemplar_no_entity_share", "mean", "share of exemplars carrying no entity"),
    ("exemplar_covers_contract_types", "mean", "share of supplied contract types an exemplar shows"),
    ("contracts_supplied", "mean", "slot contracts delivered to the Solver"),
    ("contract_has_date", "share", "the date contract was supplied"),
    ("contract_has_time", "share", "the time contract was supplied"),
    ("planner_revise", "share", "the Planner routed REVISE at least once"),
    ("revision_count", "mean", "revisions executed"),
    ("reviewer_visits", "mean", "Reviewer visits"),
    ("normaliser_changed", "share", "the deliver normaliser changed the answer"),
    ("normaliser_fillers_changed", "mean", "fillers the normaliser rewrote"),
    ("compacted", "share", "context-fit compaction fired"),
    ("far_field", "share", "far-field recording (not headset)"),
    ("audio_seconds", "mean", "utterance duration, seconds"),
    ("response_chars", "mean", "delivered response length, characters"),
    ("emitted_entities", "mean", "entities the Solver emitted"),
)


def signature_row(*, sample_id, state, roster, delivered, exemplars, contracts) -> dict:
    """One row's runtime-observable signature vector. No gold of any kind enters here."""
    first = state["candidates_first"]
    top = first[0] if first else None
    supplied_exemplars = state["supplied"].get(EXEMPLAR_STORE) or []
    supplied_contracts = state["supplied"].get(CONTRACT_STORE) or []
    contract_types = sorted(
        {contracts["types"][value] for value in supplied_contracts if value in contracts["types"]}
    )
    labels = [exemplars["values"][value] for value in supplied_exemplars if value in exemplars["values"]]
    exemplar_types: set[str] = set()
    for label in labels:
        exemplar_types.update(label["entity_types"])
    out = delivered["rows"][sample_id]
    intent = out["intent"]
    return {
        "candidate_width": state["candidate_width"],
        "distinct_distinctions": state["distinct_distinctions"],
        "degenerate_distinctions": state["distinct_distinctions"] < state["candidate_width"],
        "candidate_scenarios": len(state["candidate_scenarios"]),
        "delivered_in_candidates": intent in first,
        "delivered_candidate_rank": (first.index(intent) + 1) if intent in first else 0,
        "exemplars_supplied": len(supplied_exemplars),
        "exemplar_top_agreement": (
            mean(1.0 if label["intent"] == top else 0.0 for label in labels) if labels else 0.0
        ),
        "exemplar_no_entity_share": (
            mean(1.0 if not label["entity_types"] else 0.0 for label in labels) if labels else 0.0
        ),
        "exemplar_covers_contract_types": (
            mean(1.0 if name in exemplar_types else 0.0 for name in contract_types)
            if contract_types
            else 0.0
        ),
        "contracts_supplied": len(supplied_contracts),
        "contract_has_date": "date" in contract_types,
        "contract_has_time": "time" in contract_types,
        "planner_revise": any(action == "REVISE" for action in state["planner_actions"]),
        "revision_count": state["revision_count"],
        "reviewer_visits": state["role_visits"].get("reviewer", 0),
        "normaliser_changed": state["normaliser_changed"],
        "normaliser_fillers_changed": state["normaliser_fillers_changed"],
        "compacted": state["compacted_contacts"] > 0,
        "far_field": roster["channel"][sample_id] == "far_field",
        "audio_seconds": roster["audio_seconds"][sample_id],
        "response_chars": out["response_chars"],
        "emitted_entities": out["entity_count"],
        "_contract_types": contract_types,
        "_exemplar_types": sorted(exemplar_types),
        "_exemplar_intents": [label["intent"] for label in labels],
    }


def summarise_signature(values, kind: str) -> float:
    values = list(values)
    if not values:
        return 0.0
    if kind == "share":
        return pct(mean(1.0 if bool(value) else 0.0 for value in values))
    return mean(float(value) for value in values)


def signature_table(*, signatures, members, reference) -> list[dict]:
    """A univariate separation table: the signature in a class against STABLE-RIGHT rows.

    No model is fitted. ``lift`` is simply the class value minus the reference value, in
    the signature's own units, so a rollout designer can read which observable actually
    moves with the failure and gate on it without gold.
    """
    table = []
    for name, kind, label in SIGNATURES:
        in_class = summarise_signature((signatures[sid][name] for sid in members), kind)
        in_ref = summarise_signature((signatures[sid][name] for sid in reference), kind)
        table.append(
            {
                "signature": name,
                "label": label,
                "kind": kind,
                "class_value": in_class,
                "reference_value": in_ref,
                "lift": in_class - in_ref,
            }
        )
    return table


# --------------------------------------------------------------------------
# The exemplar and contract angle (item 5)
# --------------------------------------------------------------------------


def exemplar_angle(*, members, reference, signatures, derived, delivered) -> dict:
    """What the supplied exemplars looked like on the target rows against the right ones.

    ``matched_reference`` re-weights the STABLE-RIGHT rows to the delivered-intent mixture
    of the target rows, so the comparison is not an intent-mixture artefact: an intent
    whose rows are all hard would otherwise make its exemplars look bad by construction.
    """
    by_intent: dict[str, list[str]] = defaultdict(list)
    for sample_id in reference:
        by_intent[delivered["rows"][sample_id]["intent"]].append(sample_id)
    fields = (
        "exemplars_supplied",
        "exemplar_top_agreement",
        "exemplar_no_entity_share",
        "exemplar_covers_contract_types",
        "contracts_supplied",
    )
    target = {name: mean(signatures[sid][name] for sid in members) for name in fields}
    weights: Counter = Counter()
    for sample_id in members:
        intent = delivered["rows"][sample_id]["intent"]
        if by_intent.get(intent):
            weights[intent] += 1
    matched = {}
    covered = sum(weights.values())
    for name in fields:
        if not covered:
            matched[name] = 0.0
            continue
        matched[name] = sum(
            weight * mean(signatures[sid][name] for sid in by_intent[intent])
            for intent, weight in weights.items()
        ) / covered
    plain = {name: mean(signatures[sid][name] for sid in reference) for name in fields}

    gold_cover = []
    for sample_id in members:
        gold_types = set(derived[sample_id]["gold_entity_types"])
        if not gold_types:
            continue
        exemplar_types = set(signatures[sample_id]["_exemplar_types"])
        gold_cover.append(len(gold_types & exemplar_types) / len(gold_types))
    ref_gold_cover = []
    for sample_id in reference:
        gold_types = set(derived[sample_id]["gold_entity_types"])
        if not gold_types:
            continue
        exemplar_types = set(signatures[sample_id]["_exemplar_types"])
        ref_gold_cover.append(len(gold_types & exemplar_types) / len(gold_types))
    return {
        "rows": len(members),
        "reference_rows": len(reference),
        "intent_matched_reference_rows": covered,
        "target": target,
        "reference": plain,
        "matched_reference": matched,
        "gold_type_coverage_by_exemplars": mean(gold_cover),
        "reference_gold_type_coverage_by_exemplars": mean(ref_gold_cover),
    }


def contract_coverage_on_fn(*, ids, derived, signatures, classes) -> list[dict]:
    """On every FN of slot TYPE ``t``, was ``slot-contract:t`` supplied to that row at all?

    A supply that never mentions the slot is a SUPPLY defect a rollout can fix by changing
    what is constructed; a supply that mentions it and is still omitted is an OBS or USE
    defect, and no amount of contract text will repair it.
    """
    per_type: dict[str, dict] = defaultdict(lambda: {"fn_rows": 0, "contract_supplied": 0, "fn": 0})
    for sample_id in ids:
        if classes[sample_id] == "CORRECT":
            continue
        supplied = set(signatures[sample_id]["_contract_types"])
        for slot_type, count in derived[sample_id]["per_type"]["fn"].items():
            entry = per_type[slot_type]
            entry["fn_rows"] += 1
            entry["fn"] += int(count)
            if slot_type in supplied:
                entry["contract_supplied"] += 1
    table = []
    for slot_type, entry in per_type.items():
        table.append(
            {
                "slot_type": slot_type,
                "fn": entry["fn"],
                "fn_rows": entry["fn_rows"],
                "contract_supplied_rows": entry["contract_supplied"],
                "contract_supplied_share": pct(entry["contract_supplied"] / entry["fn_rows"])
                if entry["fn_rows"]
                else 0.0,
            }
        )
    table.sort(key=lambda entry: (-entry["fn"], entry["slot_type"]))
    return table


# --------------------------------------------------------------------------
# Taxonomy tables (item 1)
# --------------------------------------------------------------------------


def taxonomy(*, ids, derived, delivered, scores, classes, detail, runtime) -> dict:
    """Item 1: the row-level error taxonomy of one arm, with mass per class."""
    counts = Counter(classes[sid] for sid in ids)
    mass = {}
    for name in CLASSES:
        members = [sid for sid in ids if classes[sid] == name]
        mass[name] = {
            "rows": len(members),
            "share": pct(len(members) / len(ids)) if ids else 0.0,
            "intent_wrong": sum(1 for sid in members if not detail[sid]["intent_ok"]),
            "span_fp": sum(detail[sid]["fp"] for sid in members),
            "span_fn": sum(detail[sid]["fn"] for sid in members),
            "gold_entities": sum(derived[sid]["gold_entity_count"] for sid in members),
            "emitted_entities": sum(detail[sid]["emitted"] for sid in members),
        }

    wrong = [sid for sid in ids if not detail[sid]["intent_ok"] and classes[sid] != "MALFORMED"]
    confusion: Counter = Counter()
    for sample_id in wrong:
        confusion[(derived[sample_id]["gold_intent"], delivered["rows"][sample_id]["intent"])] += 1
    top_pairs = []
    for (gold_intent, delivered_intent), n in sorted(
        confusion.items(), key=lambda item: (-item[1], item[0])
    )[:15]:
        rows = [
            sid
            for sid in wrong
            if derived[sid]["gold_intent"] == gold_intent
            and delivered["rows"][sid]["intent"] == delivered_intent
        ]
        covered = sum(1 for sid in rows if classes[sid] == "INTENT-COVERED")
        top_pairs.append(
            {
                "gold": gold_intent,
                "delivered": delivered_intent,
                "rows": n,
                "share_of_intent_errors": pct(n / len(wrong)) if wrong else 0.0,
                "within_scenario": gold_intent.split("_", 1)[0] == delivered_intent.split("_", 1)[0],
                "covered": covered,
                "uncovered": n - covered,
            }
        )

    coverage = {
        "intent_error_rows": len(wrong),
        "covered": sum(1 for sid in wrong if classes[sid] == "INTENT-COVERED"),
        "uncovered": sum(1 for sid in wrong if classes[sid] == "INTENT-UNCOVERED"),
        "distinct_pairs": len(confusion),
        "within_scenario": sum(
            1
            for sid in wrong
            if derived[sid]["gold_intent"].split("_", 1)[0]
            == delivered["rows"][sid]["intent"].split("_", 1)[0]
        ),
    }
    if runtime is not None:
        ranks: Counter = Counter()
        for sample_id in wrong:
            union = runtime["rows"][sample_id]["candidates_first"]
            gold_intent = derived[sample_id]["gold_intent"]
            ranks[(union.index(gold_intent) + 1) if gold_intent in union else 0] += 1
        coverage["gold_rank_in_first_candidates"] = dict(sorted(ranks.items()))
        right = [sid for sid in ids if detail[sid]["intent_ok"]]
        right_ranks: Counter = Counter()
        for sample_id in right:
            union = runtime["rows"][sample_id]["candidates_first"]
            gold_intent = derived[sample_id]["gold_intent"]
            right_ranks[(union.index(gold_intent) + 1) if gold_intent in union else 0] += 1
        coverage["gold_rank_when_right"] = dict(sorted(right_ranks.items()))

    entity_rows = [
        sid for sid in ids if classes[sid] in ("ENTITY-FN-ONLY", "ENTITY-FP-ONLY", "ENTITY-MIXED")
    ]
    fn_by_type: Counter = Counter()
    fp_by_type: Counter = Counter()
    fp_empty_gold: Counter = Counter()
    over_by_type: Counter = Counter()
    omission_by_type: Counter = Counter()
    same_type_by_type: Counter = Counter()
    swap_pairs: Counter = Counter()
    rungs: Counter = Counter()
    buckets: Counter = Counter()
    token_delta: Counter = Counter()
    boundary = 0
    gold_digit = 0
    gold_ordinal = 0
    gold_relative = 0
    same_type_total = 0
    # The decomposition runs over EVERY row, not only the intent-correct ones, so the
    # shares below are shares of the roster's whole official FP+FN loss mass and are
    # directly comparable with the 2026-09-16 handoff report's own decomposition. The
    # intent-correct subset is reported separately as ``entity_rows``.
    for sample_id in ids:
        view = derived[sample_id]
        fn_by_type.update(view["per_type"]["fn"])
        fp_by_type.update(view["per_type"]["fp"])
        over_by_type.update(view["over_emission"])
        omission_by_type.update(view["omission"])
        if not view["gold_entity_count"]:
            fp_empty_gold.update(view["per_type"]["fp"])
        for pair in view["same_type"]:
            same_type_total += 1
            same_type_by_type[pair["slot_type"]] += 1
            rungs[pair["repair_rung"]] += 1
            buckets[pair["distance_bucket"]] += 1
            token_delta[max(-3, min(3, pair["token_delta"]))] += 1
            boundary += 1 if pair["boundary_containment"] else 0
            gold_digit += 1 if pair["gold_has_digit"] else 0
            gold_ordinal += 1 if pair["gold_has_ordinal"] else 0
            gold_relative += 1 if pair["gold_has_relative"] else 0
        for swap in view["type_swap"]:
            swap_pairs[(swap["predicted_type"], swap["gold_type"])] += 1

    empty_gold_rows = [sid for sid in ids if not derived[sid]["gold_entity_count"]]
    over_emitting = [sid for sid in empty_gold_rows if detail[sid]["emitted"] > 0]

    malformed = [sid for sid in ids if classes[sid] == "MALFORMED"]
    dispositions = {
        "malformed_rows": len(malformed),
        "abstained_rows": sum(1 for sid in ids if detail[sid]["abstained"]),
        "revision_limit_rows": sum(1 for sid in ids if detail[sid]["revision_limit"]),
        "zero_entity_rows": sum(1 for sid in ids if detail[sid]["emitted"] == 0),
    }

    total_fp = sum(detail[sid]["fp"] for sid in ids)
    total_fn = sum(detail[sid]["fn"] for sid in ids)
    swap_total = sum(swap_pairs.values())
    over_total = sum(over_by_type.values())
    omission_total = sum(omission_by_type.values())
    loss_total = total_fp + total_fn
    return {
        "class_counts": {name: counts.get(name, 0) for name in CLASSES},
        "class_mass": mass,
        "intent_confusion_top": top_pairs,
        "coverage": coverage,
        "entity_rows": len(entity_rows),
        "entity_split": {
            "fn_only": counts.get("ENTITY-FN-ONLY", 0),
            "fp_only": counts.get("ENTITY-FP-ONLY", 0),
            "mixed": counts.get("ENTITY-MIXED", 0),
            "fp_on_intent_correct_rows": sum(detail[sid]["fp"] for sid in entity_rows),
            "fn_on_intent_correct_rows": sum(detail[sid]["fn"] for sid in entity_rows),
        },
        "fn_by_type": [
            {"slot_type": name, "fn": n, "share": pct(n / total_fn) if total_fn else 0.0}
            for name, n in sorted(fn_by_type.items(), key=lambda item: (-item[1], item[0]))
        ],
        "fp_by_type": [
            {
                "slot_type": name,
                "fp": n,
                "share": pct(n / total_fp) if total_fp else 0.0,
                "fp_on_empty_gold_rows": fp_empty_gold.get(name, 0),
            }
            for name, n in sorted(fp_by_type.items(), key=lambda item: (-item[1], item[0]))
        ],
        "empty_gold": {
            "rows": len(empty_gold_rows),
            "rows_emitting_entities": len(over_emitting),
            "share": pct(len(over_emitting) / len(empty_gold_rows)) if empty_gold_rows else 0.0,
            "entities_emitted": sum(detail[sid]["emitted"] for sid in over_emitting),
        },
        "loss_components": {
            "total_fp": total_fp,
            "total_fn": total_fn,
            "same_type_pairs": same_type_total,
            "same_type_share_of_loss": pct(2 * same_type_total / loss_total) if loss_total else 0.0,
            "type_swap_pairs": swap_total,
            "type_swap_share_of_loss": pct(2 * swap_total / loss_total) if loss_total else 0.0,
            "over_emission": over_total,
            "over_emission_share_of_loss": pct(over_total / loss_total) if loss_total else 0.0,
            "omission": omission_total,
            "omission_share_of_loss": pct(omission_total / loss_total) if loss_total else 0.0,
        },
        "same_type_shapes": {
            "pairs": same_type_total,
            "by_type": [
                {"slot_type": name, "pairs": n}
                for name, n in sorted(same_type_by_type.items(), key=lambda i: (-i[1], i[0]))[:12]
            ],
            "repair_rung": dict(sorted(rungs.items())),
            "distance_bucket": dict(sorted(buckets.items())),
            "token_delta_clipped": dict(sorted(token_delta.items())),
            "boundary_containment": boundary,
            "gold_has_digit": gold_digit,
            "gold_has_ordinal": gold_ordinal,
            "gold_has_relative": gold_relative,
        },
        "type_swap_top": [
            {"predicted_type": pair[0], "gold_type": pair[1], "pairs": n}
            for pair, n in sorted(swap_pairs.items(), key=lambda i: (-i[1], i[0]))[:10]
        ],
        "dispositions": dispositions,
        "omission_by_type_top": [
            {"slot_type": name, "omitted": n}
            for name, n in sorted(omission_by_type.items(), key=lambda i: (-i[1], i[0]))[:12]
        ],
        "over_emission_by_type_top": [
            {"slot_type": name, "spurious": n}
            for name, n in sorted(over_by_type.items(), key=lambda i: (-i[1], i[0]))[:12]
        ],
    }


def direct_transitions(*, ids, direct_classes, plan_classes) -> dict:
    """Item 3: the bare core's class -> the plan's class, on the same rows."""
    matrix: Counter = Counter()
    for sample_id in ids:
        matrix[(direct_classes[sample_id], plan_classes[sample_id])] += 1
    rows = []
    for source in DIRECT_CLASSES:
        total = sum(n for (src, _), n in matrix.items() if src == source)
        if not total:
            continue
        entry = {"direct_class": source, "rows": total}
        for target in CLASSES:
            entry[target] = matrix.get((source, target), 0)
        entry["repaired_to_correct"] = matrix.get((source, "CORRECT"), 0)
        rows.append(entry)
    fixed = sum(n for (src, dst), n in matrix.items() if src != "CORRECT" and dst == "CORRECT")
    broken = sum(n for (src, dst), n in matrix.items() if src == "CORRECT" and dst != "CORRECT")
    survived = {
        name: matrix.get((name, name), 0)
        for name in DIRECT_CLASSES
        if name != "CORRECT" and matrix.get((name, name), 0)
    }
    return {
        "matrix": rows,
        "direct_counts": {name: sum(n for (src, _), n in matrix.items() if src == name) for name in DIRECT_CLASSES},
        "repaired_rows": fixed,
        "broken_rows": broken,
        "net_rows": fixed - broken,
        "survived_in_place": survived,
    }


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------

#: Bumped whenever the DERIVED per-row projection changes shape, so a stale cache can
#: never be mistaken for a fresh one.
DERIVATION_VERSION = "v1"


def cache_path(out_root: Path, roster_key: str, arm: str) -> Path:
    return out_root / "cache" / f"derived-{roster_key}-{arm}.json"


def load_derived_cache(path: Path, *, outputs_sha: str, gold_sha: str | None) -> dict | None:
    if not path.is_file():
        return None
    cached = json.loads(path.read_text(encoding="utf-8"))
    if cached.get("schema") != "saea-slurp-plan-bad-case-derivation-v1":
        return None
    if cached.get("derivation_version") != DERIVATION_VERSION:
        return None
    if cached.get("outputs_sha256") != outputs_sha:
        return None
    if gold_sha is not None and cached.get("gold_metadata_sha256") != gold_sha:
        return None
    return cached


def write_derived_cache(path: Path, *, outputs_sha: str, gold_sha: str, rows: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema": "saea-slurp-plan-bad-case-derivation-v1",
                "derivation_version": DERIVATION_VERSION,
                "outputs_sha256": outputs_sha,
                "gold_metadata_sha256": gold_sha,
                "rows": rows,
            },
            indent=1,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def analyse_roster(*, spec, repo, data_root, lock_path, out_root, refresh) -> dict:
    """Everything this read says about one roster, from the sealed bytes of its three arms."""
    roster = load_roster(repo, spec["roster_relpath"])
    ids = roster["ids"]
    wanted = set(ids)
    identity = roster["split_identity_hash"]

    arms: dict[str, dict] = {}
    for arm in ARM_KEYS:
        run_id, attempt_id = spec["arms"][arm]
        directory = arm_dir(data_root, run_id, attempt_id)
        manifest = load_manifest(directory, run_id, identity)
        if manifest["split_count"] != len(ids):
            raise BankError(
                f"{run_id}: manifest split count {manifest['split_count']} is not the roster's {len(ids)}"
            )
        scores = load_scores(directory, run_id, spec["scorer"], ids)
        delivered = load_delivered(directory, run_id, wanted)
        arms[arm] = {
            "run_id": run_id,
            "attempt_id": attempt_id,
            "directory": directory,
            "manifest": manifest,
            "scores": scores,
            "delivered": delivered,
        }

    # The PLAN arm's runtime state. Loaded once, reduced to the per-row projection, freed.
    plan = arms["plan"]
    runtime = load_plan_runtime(plan["directory"], plan["run_id"], wanted)
    receipt_check = verify_supply_against_receipt(plan["directory"], plan["run_id"], runtime)
    gc.collect()

    exemplars = load_exemplar_labels(data_root)
    contracts = load_contract_types(data_root)

    # Derivation, cached on (gold metadata, sealed outputs) so a re-run never re-reads the
    # governed corpus. The gold loader is touched only when a cache is missing or stale.
    caches = {
        arm: load_derived_cache(
            cache_path(out_root, spec["key"], arm),
            outputs_sha=arms[arm]["delivered"]["sha256"],
            gold_sha=None,
        )
        for arm in ARM_KEYS
    }
    gold_meta_sha = None
    if refresh or any(entry is None for entry in caches.values()):
        gold = gold_records(lock_path, data_root, spec["split_id"])
        gold_meta_sha = gold["metadata_sha256"]
        gold_metadata_path = gold["metadata_path"]
        for arm in ARM_KEYS:
            rows = derive_rows(
                ids=ids,
                gold=gold,
                delivered=arms[arm]["delivered"],
                scores=arms[arm]["scores"],
                run_id=arms[arm]["run_id"],
            )
            write_derived_cache(
                cache_path(out_root, spec["key"], arm),
                outputs_sha=arms[arm]["delivered"]["sha256"],
                gold_sha=gold_meta_sha,
                rows=rows,
            )
            arms[arm]["derived"] = rows
        del gold
        gc.collect()
    else:
        shas = {entry["gold_metadata_sha256"] for entry in caches.values()}
        if len(shas) != 1:
            raise BankError(f"{spec['key']}: the derived caches disagree on the gold metadata")
        gold_meta_sha = shas.pop()
        lock = load_lock(lock_path)
        gold_metadata_path = str(
            _governed_roots(lock, data_root)[2] / _SPLIT_FILES[spec["split_id"]]
        )
        for arm in ARM_KEYS:
            arms[arm]["derived"] = caches[arm]["rows"]

    # Classification, stability, transitions.
    for arm in ARM_KEYS:
        state = runtime if arm in ("plan",) else None
        if arm == "planr":
            # PLANr is the same program; it has its own candidates, but the bank's classes
            # are read on PLAN. Its rows only need the right / wrong split, so the two
            # intent classes collapse exactly as they do for a direct arm.
            state = None
        verdict = classify(
            ids=ids,
            derived=arms[arm]["derived"],
            delivered=arms[arm]["delivered"],
            scores=arms[arm]["scores"],
            runtime=state,
        )
        arms[arm].update(verdict)

    stability_result = stability(
        ids=ids,
        plan_classes=arms["plan"]["classes"],
        planr_classes=arms["planr"]["classes"],
        plan_detail=arms["plan"]["detail"],
        planr_detail=arms["planr"]["detail"],
    )

    signatures = {
        sample_id: signature_row(
            sample_id=sample_id,
            state=runtime["rows"][sample_id],
            roster=roster,
            delivered=plan["delivered"],
            exemplars=exemplars,
            contracts=contracts,
        )
        for sample_id in ids
    }

    plan_tax = taxonomy(
        ids=ids,
        derived=plan["derived"],
        delivered=plan["delivered"],
        scores=plan["scores"],
        classes=plan["classes"],
        detail=plan["detail"],
        runtime=runtime,
    )
    direct_tax = taxonomy(
        ids=ids,
        derived=arms["direct"]["derived"],
        delivered=arms["direct"]["delivered"],
        scores=arms["direct"]["scores"],
        classes=arms["direct"]["classes"],
        detail=arms["direct"]["detail"],
        runtime=None,
    )

    stable_right = [sid for sid in ids if stability_result["joint"][sid] == "STABLE-RIGHT"]
    stable_wrong = set(sid for sid in ids if stability_result["joint"][sid] == "STABLE-WRONG")

    signature_tables = {}
    for name in BAD_CLASSES:
        members = [sid for sid in ids if plan["classes"][sid] == name]
        if not members:
            continue
        signature_tables[name] = {
            "rows": len(members),
            "table": signature_table(
                signatures=signatures, members=members, reference=stable_right
            ),
        }

    entity_stable_wrong = [
        sid
        for sid in ids
        if sid in stable_wrong
        and plan["classes"][sid] in ("ENTITY-FN-ONLY", "ENTITY-FP-ONLY", "ENTITY-MIXED")
    ]
    angle = exemplar_angle(
        members=entity_stable_wrong,
        reference=stable_right,
        signatures=signatures,
        derived=plan["derived"],
        delivered=plan["delivered"],
    )
    contract_table = contract_coverage_on_fn(
        ids=ids, derived=plan["derived"], signatures=signatures, classes=plan["classes"]
    )

    rows = plan["scores"]["rows"]
    head = {}
    for name in BAD_CLASSES:
        members = [sid for sid in ids if plan["classes"][sid] == name]
        restricted = [sid for sid in members if sid in stable_wrong]
        head[name] = {
            "rows": len(members),
            "stable_wrong_rows": len(restricted),
            "all": {
                "slu": headroom(ids=ids, rows=rows, members=members)["slu_f1_micro"],
                "span": headroom(ids=ids, rows=rows, members=members)["span_f1_micro"],
                "intent": intent_headroom(ids=ids, rows=rows, members=members),
            },
            "stable_wrong": {
                "slu": headroom(ids=ids, rows=rows, members=restricted)["slu_f1_micro"],
                "span": headroom(ids=ids, rows=rows, members=restricted)["span_f1_micro"],
                "intent": intent_headroom(ids=ids, rows=rows, members=restricted),
            },
        }
    all_bad = [sid for sid in ids if plan["classes"][sid] != "CORRECT"]
    head["ALL-BAD"] = {
        "rows": len(all_bad),
        "stable_wrong_rows": len([sid for sid in all_bad if sid in stable_wrong]),
        "all": {
            "slu": headroom(ids=ids, rows=rows, members=all_bad)["slu_f1_micro"],
            "span": headroom(ids=ids, rows=rows, members=all_bad)["span_f1_micro"],
            "intent": intent_headroom(ids=ids, rows=rows, members=all_bad),
        },
        "stable_wrong": {
            "slu": headroom(
                ids=ids, rows=rows, members=[sid for sid in all_bad if sid in stable_wrong]
            )["slu_f1_micro"],
            "span": headroom(
                ids=ids, rows=rows, members=[sid for sid in all_bad if sid in stable_wrong]
            )["span_f1_micro"],
            "intent": intent_headroom(
                ids=ids, rows=rows, members=[sid for sid in all_bad if sid in stable_wrong]
            ),
        },
    }

    bank = []
    for sample_id in ids:
        signature = signatures[sample_id]
        view = plan["derived"][sample_id]
        detail = plan["detail"][sample_id]
        entry = {
            "sample_id": sample_id,
            "roster": spec["key"],
            "stratum": roster["stratum"][sample_id],
            "gold_intent": view["gold_intent"],
            "delivered_intent": plan["delivered"]["rows"][sample_id]["intent"],
            "plan_class": plan["classes"][sample_id],
            "planr_class": arms["planr"]["classes"][sample_id],
            "direct_class": arms["direct"]["classes"][sample_id],
            "stability_intent": stability_result["intent"][sample_id],
            "stability_entity": stability_result["entity"][sample_id],
            "stability_joint": stability_result["joint"][sample_id],
            "span_fp": detail["fp"],
            "span_fn": detail["fn"],
            "gold_entity_count": view["gold_entity_count"],
            "gold_entity_types": view["gold_entity_types"],
            "fn_types": sorted(view["per_type"]["fn"]),
            "fp_types": sorted(view["per_type"]["fp"]),
            "same_type_pairs": len(view["same_type"]),
            "same_type_repair_rungs": sorted(
                {pair["repair_rung"] for pair in view["same_type"]}
            ),
            "type_swap_pairs": len(view["type_swap"]),
            "over_emission": sum(view["over_emission"].values()),
            "omission": sum(view["omission"].values()),
            "abstained": detail["abstained"],
            "revision_limit": detail["revision_limit"],
        }
        for name, _, _ in SIGNATURES:
            entry[name] = signature[name]
        entry["supplied_contract_types"] = signature["_contract_types"]
        entry["supplied_exemplar_types"] = signature["_exemplar_types"]
        entry["supplied_exemplar_intents"] = dict(
            sorted(Counter(signature["_exemplar_intents"]).items())
        )
        bank.append(entry)

    return {
        "key": spec["key"],
        "label": spec["label"],
        "roster": {
            "relpath": roster["relpath"],
            "sha256": roster["sha256"],
            "roster_id": roster["roster_id"],
            "split_role": roster["split_role"],
            "split_identity_hash": identity,
            "rows": len(ids),
            "far_field_rows": sum(1 for sid in ids if roster["channel"][sid] == "far_field"),
        },
        "scorer": spec["scorer"],
        "gold": {"metadata_path": gold_metadata_path, "metadata_sha256": gold_meta_sha},
        "arms": {
            arm: {
                "run_id": arms[arm]["run_id"],
                "attempt_id": arms[arm]["attempt_id"],
                "study_commit": arms[arm]["manifest"]["study_commit"],
                "config_hash": arms[arm]["manifest"]["config_hash"],
                "baseline_fragment": arms[arm]["manifest"]["fragments"].get("baseline"),
                "outputs_sha256": arms[arm]["delivered"]["sha256"],
                "scores_sha256": arms[arm]["scores"]["sha256"],
                "manifest_sha256": arms[arm]["manifest"]["sha256"],
                "official": arms[arm]["scores"]["official"],
                "class_counts": {
                    name: sum(1 for sid in ids if arms[arm]["classes"][sid] == name)
                    for name in (CLASSES if arm == "plan" else DIRECT_CLASSES)
                },
            }
            for arm in ARM_KEYS
        },
        "plan_runtime": {
            "path": runtime["path"],
            "sha256": runtime["sha256"],
            "controller_policy_id": runtime["controller_policy_id"],
            "candidate_parse_failures": runtime["candidate_parse_failures"],
            "flight_receipts": receipt_check,
        },
        "stores": {
            "train-exemplars": {
                "path": exemplars["path"],
                "sha256": exemplars["sha256"],
                "values": len(exemplars["values"]),
                "composition": exemplars["composition"],
            },
            "slot-contracts": {
                "path": contracts["path"],
                "sha256": contracts["sha256"],
                "values": len(contracts["types"]),
            },
        },
        "taxonomy_plan": plan_tax,
        "taxonomy_direct": direct_tax,
        "stability": stability_result,
        "direct_transitions": direct_transitions(
            ids=ids,
            direct_classes=arms["direct"]["classes"],
            plan_classes=plan["classes"],
        ),
        "signatures": signature_tables,
        "exemplar_angle": angle,
        "contract_coverage_on_fn": contract_table,
        "headroom": head,
        "bank": bank,
    }


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------


def fmt(value: float, places: int = 2) -> str:
    return f"{value:+.{places}f}" if value < 0 or value > 0 else f"{value:.{places}f}"


def num(value: float, places: int = 2) -> str:
    return f"{value:.{places}f}"


def signed(value: float, places: int = 2) -> str:
    return f"{value:+.{places}f}"


def render(payload: dict) -> str:
    lines: list[str] = []
    add = lines.append
    add("# The bad-case bank of the locked SLURP v2.0 plan")
    add("")
    add(
        f"Date: {payload['date']}. Recipe `{RECIPE_ID}`, schema `{SCHEMA}`, run id `{RUN_ID}`. "
        "A model-free read: zero model, tokenizer, encoder, ASR, scorer, embedder, server, "
        "network, GPU and paid-API contacts."
    )
    add("")
    add(
        "Owner directive of 2026-09-24: analyse the bad cases first, because a training-free RL "
        "gain comes from rolling out variations of prompts, data and content construction over an "
        "optimisation space, not from appending advice text. This note is that inventory. It types "
        "every row of the locked plan on two rosters, counts the mass each type carries, states "
        "which types survive the run-to-run noise of a request-identical replicate, says which the "
        "plan already repaired against the bare core, and gives each type a set of "
        "RUNTIME-OBSERVABLE signatures -- things a rollout may condition on without gold."
    )
    add("")
    add(
        "A DIAGNOSTIC, never a gate. It decides no cell, admits no mechanism, releases no store, "
        "authorises no flight and states no effectiveness, superiority or generalisation claim. "
        "TRAIN Fold A and DEV-2000-ADDED numbers are development numbers (owner decisions 28 and "
        "86) and are never a test claim."
    )
    add("")
    add(
        "No utterance text, transcript, delivered text, gold filler, predicted filler or knowledge "
        "content appears anywhere below. Every cell is a label, a slot TYPE name, an identifier, a "
        "count, a share, a shape statistic or a hash. Gold is used offline as a scoring key exactly "
        "as `core.scoring_batch` uses it."
    )
    add("")

    add("## 0. Inputs and identity")
    add("")
    add(
        "| Roster | Rows | Split role | Split identity | Arm | Run id | Study commit | Official SLU / intent |"
    )
    add("| --- | ---: | --- | --- | --- | --- | --- | --- |")
    for roster in payload["rosters"]:
        for arm in ARM_KEYS:
            entry = roster["arms"][arm]
            official = entry["official"]
            add(
                f"| {roster['label']} | {roster['roster']['rows']} | "
                f"{roster['roster']['split_role']} | "
                f"`{roster['roster']['split_identity_hash'][:12]}` | {arm.upper()} | "
                f"`{entry['run_id']}` | `{(entry['study_commit'] or '')[:10]}` | "
                f"{num(pct(official['slu_f1']))} / {num(pct(official['intent_accuracy']))} |"
            )
    add("")
    add(
        "Every arm's sealed per-sample rows reproduce its own sealed official pooled SLU-F1 and "
        "span-F1 to 1e-6 before any table below is built, and every row's derived per-slot-TYPE "
        "exact decomposition reproduces that row's sealed `slot_f1_exact_{tp,fp,fn}` exactly. The "
        "PLAN arm's transition-derived slot-contract supply was checked row by row against the "
        "sealed `phase_supply.candidate_selections` receipt of the same flight; disagreements "
        "would have refused the read."
    )
    add("")
    add("| Artefact | sha256 |")
    add("| --- | --- |")
    for roster in payload["rosters"]:
        for arm in ARM_KEYS:
            entry = roster["arms"][arm]
            add(f"| {roster['key']} {arm} outputs.jsonl | `{entry['outputs_sha256'][:16]}` |")
            add(f"| {roster['key']} {arm} scores.json | `{entry['scores_sha256'][:16]}` |")
        add(f"| {roster['key']} PLAN phases.json | `{roster['plan_runtime']['sha256'][:16]}` |")
        add(
            f"| {roster['key']} PLAN flight-receipts.json | "
            f"`{roster['plan_runtime']['flight_receipts']['sha256'][:16]}` |"
        )
        add(f"| {roster['key']} roster receipt | `{roster['roster']['sha256'][:16]}` |")
        add(f"| {roster['key']} gold split metadata | `{(roster['gold']['metadata_sha256'] or '')[:16]}` |")
    first = payload["rosters"][0]
    add(f"| train-exemplars snapshot | `{first['stores']['train-exemplars']['sha256'][:16]}` |")
    add(f"| slot-contracts snapshot | `{first['stores']['slot-contracts']['sha256'][:16]}` |")
    add("")

    add("## 1. Row-level error taxonomy of the locked plan")
    add("")
    add(
        "Seven exclusive classes, attributed in order, so a malformed delivery is never also "
        "counted as an intent error and an intent error is never also counted as an entity error. "
        "`INTENT-UNCOVERED` means Perception's own candidate list never contained the gold intent "
        "(a COVERAGE failure of the observation stage); `INTENT-COVERED` means it did and the "
        "Solver still delivered another (a SELECTION failure). The two need different rollouts."
    )
    add("")
    add("| Class | " + " | ".join(r["label"].split(" (")[0] for r in payload["rosters"]) + " |")
    add("| --- | " + " | ".join("---:" for _ in payload["rosters"]) + " |")
    for name in CLASSES:
        cells = []
        for roster in payload["rosters"]:
            mass = roster["taxonomy_plan"]["class_mass"][name]
            cells.append(f"{mass['rows']} ({num(mass['share'], 1)} %)")
        add(f"| {name} | " + " | ".join(cells) + " |")
    add("")
    add("### 1a. Intent errors: coverage against selection")
    add("")
    add(
        "| Roster | Intent-error rows | Covered (selection failure) | Uncovered (coverage failure) "
        "| Within scenario | Distinct gold -> delivered pairs |"
    )
    add("| --- | ---: | ---: | ---: | ---: | ---: |")
    for roster in payload["rosters"]:
        cov = roster["taxonomy_plan"]["coverage"]
        add(
            f"| {roster['key']} | {cov['intent_error_rows']} | {cov['covered']} | "
            f"{cov['uncovered']} | {cov['within_scenario']} | {cov['distinct_pairs']} |"
        )
    add("")
    add(
        "Where the gold intent sat in Perception's FIRST candidate list (rank 0 = absent). The "
        "right-hand block is the same statistic on the rows the plan got right, which is what makes "
        "the left-hand block readable: rank 1 on a correct row is the normal case."
    )
    add("")
    add("| Roster | Gold rank on intent-error rows | Gold rank on intent-correct rows |")
    add("| --- | --- | --- |")
    for roster in payload["rosters"]:
        cov = roster["taxonomy_plan"]["coverage"]
        wrong = ", ".join(
            f"{rank}: {n}" for rank, n in sorted(cov.get("gold_rank_in_first_candidates", {}).items())
        )
        right = ", ".join(
            f"{rank}: {n}" for rank, n in sorted(cov.get("gold_rank_when_right", {}).items())
        )
        add(f"| {roster['key']} | {wrong} | {right} |")
    add("")
    for roster in payload["rosters"]:
        add(f"#### Top confusion pairs -- {roster['label']}")
        add("")
        add("| Gold -> delivered | Rows | Share of intent errors | Within scenario | Covered / uncovered |")
        add("| --- | ---: | ---: | --- | --- |")
        for pair in roster["taxonomy_plan"]["intent_confusion_top"]:
            add(
                f"| `{pair['gold']}` -> `{pair['delivered']}` | {pair['rows']} | "
                f"{num(pair['share_of_intent_errors'], 1)} % | "
                f"{'yes' if pair['within_scenario'] else 'no'} | "
                f"{pair['covered']} / {pair['uncovered']} |"
            )
        add("")

    add("### 1b. Entity errors on intent-correct rows")
    add("")
    add(
        "The class split counts INTENT-CORRECT rows only; the two right-hand columns give the "
        "roster's WHOLE official FP / FN mass, which also includes the entity defects sitting "
        "underneath the intent errors of section 1a. Every per-TYPE and per-component table below "
        "is a decomposition of that whole mass, so its shares sum over the roster and are directly "
        "comparable with the 2026-09-16 handoff report."
    )
    add("")
    add(
        "| Roster | FN-only | FP-only | Mixed | Entity-error rows | FP / FN on those rows | "
        "Whole-roster span FP | Whole-roster span FN |"
    )
    add("| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |")
    for roster in payload["rosters"]:
        tax = roster["taxonomy_plan"]
        split = tax["entity_split"]
        add(
            f"| {roster['key']} | {split['fn_only']} | {split['fp_only']} | {split['mixed']} | "
            f"{tax['entity_rows']} | {split['fp_on_intent_correct_rows']} / "
            f"{split['fn_on_intent_correct_rows']} | {tax['loss_components']['total_fp']} | "
            f"{tax['loss_components']['total_fn']} |"
        )
    add("")
    add(
        "The four loss components of the unmatched remainder, decomposed exactly as the 2026-09-16 "
        "handoff report decomposed the released anchor, so the two are comparable. A same-type pair "
        "and a type swap each consume one FP and one FN, so their share of the FP+FN mass counts "
        "two units per pair."
    )
    add("")
    add(
        "| Roster | Same-type filler distance | Equal-filler type swap | Over-emission (spurious) | "
        "Omission (nothing of that type) |"
    )
    add("| --- | --- | --- | --- | --- |")
    for roster in payload["rosters"]:
        loss = roster["taxonomy_plan"]["loss_components"]
        add(
            f"| {roster['key']} | {loss['same_type_pairs']} pairs, "
            f"{num(loss['same_type_share_of_loss'], 1)} % | {loss['type_swap_pairs']} pairs, "
            f"{num(loss['type_swap_share_of_loss'], 1)} % | {loss['over_emission']}, "
            f"{num(loss['over_emission_share_of_loss'], 1)} % | {loss['omission']}, "
            f"{num(loss['omission_share_of_loss'], 1)} % |"
        )
    add("")
    for roster in payload["rosters"]:
        tax = roster["taxonomy_plan"]
        add(f"#### FN and FP by slot TYPE -- {roster['label']}")
        add("")
        add("| Slot TYPE | FN | FN share | FP | FP share | FP on rows whose gold carries no entity |")
        add("| --- | ---: | ---: | ---: | ---: | ---: |")
        fp_index = {entry["slot_type"]: entry for entry in tax["fp_by_type"]}
        fn_index = {entry["slot_type"]: entry for entry in tax["fn_by_type"]}
        names = sorted(
            set(fp_index) | set(fn_index),
            key=lambda name: (
                -(fn_index.get(name, {}).get("fn", 0) + fp_index.get(name, {}).get("fp", 0)),
                name,
            ),
        )[:14]
        for name in names:
            fn_entry = fn_index.get(name, {"fn": 0, "share": 0.0})
            fp_entry = fp_index.get(name, {"fp": 0, "share": 0.0, "fp_on_empty_gold_rows": 0})
            add(
                f"| `{name}` | {fn_entry['fn']} | {num(fn_entry['share'], 1)} % | "
                f"{fp_entry['fp']} | {num(fp_entry['share'], 1)} % | "
                f"{fp_entry.get('fp_on_empty_gold_rows', 0)} |"
            )
        add("")
    add("Over-emission on rows whose gold carries no entity at all:")
    add("")
    add("| Roster | Rows with empty gold | Of those, emitting entities | Share | Entities emitted |")
    add("| --- | ---: | ---: | ---: | ---: |")
    for roster in payload["rosters"]:
        empty = roster["taxonomy_plan"]["empty_gold"]
        add(
            f"| {roster['key']} | {empty['rows']} | {empty['rows_emitting_entities']} | "
            f"{num(empty['share'], 1)} % | {empty['entities_emitted']} |"
        )
    add("")

    add("### 1c. Same-type filler mismatch -- SHAPE only")
    add("")
    add(
        "`repair_rung` names the cheapest surface projection that would have made the two fillers "
        "equal, on the A1 projection audit's own rungs: `case-whitespace`, `punctuation`, "
        "`meridiem`, or `none` when no surface rung reaches it. A rung that is not `none` is a "
        "RENDERING defect the USE axis can normalise; `none` is an observation or resolution "
        "defect that only a different OBS or SUPPLY construction can reach."
    )
    add("")
    add("| Roster | Pairs | case-whitespace | punctuation | meridiem | none | Boundary containment |")
    add("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for roster in payload["rosters"]:
        shapes = roster["taxonomy_plan"]["same_type_shapes"]
        rungs = shapes["repair_rung"]
        add(
            f"| {roster['key']} | {shapes['pairs']} | {rungs.get('case-whitespace', 0)} | "
            f"{rungs.get('punctuation', 0)} | {rungs.get('meridiem', 0)} | {rungs.get('none', 0)} | "
            f"{shapes['boundary_containment']} |"
        )
    add("")
    add("| Roster | Normalised edit-distance buckets | Gold side carries a digit / ordinal / relative form |")
    add("| --- | --- | --- |")
    for roster in payload["rosters"]:
        shapes = roster["taxonomy_plan"]["same_type_shapes"]
        buckets = ", ".join(f"{key}: {value}" for key, value in shapes["distance_bucket"].items())
        add(
            f"| {roster['key']} | {buckets} | {shapes['gold_has_digit']} / "
            f"{shapes['gold_has_ordinal']} / {shapes['gold_has_relative']} |"
        )
    add("")
    add("| Roster | Token-count delta (predicted minus gold, clipped to +-3) | Top slot TYPEs by pairs |")
    add("| --- | --- | --- |")
    for roster in payload["rosters"]:
        shapes = roster["taxonomy_plan"]["same_type_shapes"]
        deltas = ", ".join(f"{key}: {value}" for key, value in shapes["token_delta_clipped"].items())
        types = ", ".join(
            f"`{entry['slot_type']}` {entry['pairs']}" for entry in shapes["by_type"][:8]
        )
        add(f"| {roster['key']} | {deltas} | {types} |")
    add("")
    add("### 1d. Equal-filler type swap, and the disposition rows")
    add("")
    add("| Roster | Top swaps (predicted TYPE <- gold TYPE) |")
    add("| --- | --- |")
    for roster in payload["rosters"]:
        swaps = ", ".join(
            f"`{entry['predicted_type']}` <- `{entry['gold_type']}` {entry['pairs']}"
            for entry in roster["taxonomy_plan"]["type_swap_top"][:8]
        )
        add(f"| {roster['key']} | {swaps or 'none'} |")
    add("")
    add(
        "Disposition rows. The locked plan sets `max_revisions = 1`, so a row with an executed "
        "revision has spent its whole revision budget; that column is the revision-limit column."
    )
    add("")
    add(
        "| Roster | Malformed | Abstained | Executed its single allowed revision | "
        "Emitted no entity at all |"
    )
    add("| --- | ---: | ---: | ---: | ---: |")
    for roster in payload["rosters"]:
        disp = roster["taxonomy_plan"]["dispositions"]
        add(
            f"| {roster['key']} | {disp['malformed_rows']} | {disp['abstained_rows']} | "
            f"{disp['revision_limit_rows']} | {disp['zero_entity_rows']} |"
        )
    add("")
    add("### 1e. The supply's own composition, against the rows it has to serve")
    add("")
    add(
        "The released `train-exemplars` pool is entity-bearing BY CONSTRUCTION. Against a roster "
        "where a large minority of rows carry no gold entity at all, the supply therefore never "
        "shows the Solver a single example of the correct empty answer. This is a property of the "
        "constructed content, not of the model, and it is exactly the kind of thing a construction "
        "rollout can vary."
    )
    add("")
    composition = payload["rosters"][0]["stores"]["train-exemplars"]["composition"]
    add("| Exemplar pool | Values | Carrying no entity | Entity-count spread | Distinct intents |")
    add("| --- | ---: | ---: | --- | ---: |")
    add(
        f"| `train-exemplars` (size-pool-annotated-exemplars) | {composition['values']} | "
        f"{composition['entity_free_values']} | "
        + ", ".join(f"{key}: {value}" for key, value in composition["entity_count_spread"].items())
        + f" | {composition['distinct_intents']} |"
    )
    add("")
    add("| Roster | Rows whose gold carries no entity | Share of the roster |")
    add("| --- | ---: | ---: |")
    for roster in payload["rosters"]:
        empty = roster["taxonomy_plan"]["empty_gold"]
        add(
            f"| {roster['key']} | {empty['rows']} | "
            f"{num(pct(empty['rows'] / roster['roster']['rows']), 1)} % |"
        )
    add("")
    return lines


def render_rest(payload: dict, lines: list[str]) -> list[str]:
    add = lines.append

    add("## 2. Stability classes: PLAN against its request-identical replicate")
    add("")
    add(
        "PLANr re-flew the identical requests. A row the two arms disagree on is inside the "
        "roster's own run-to-run noise: a rollout that only moves FLIPPING rows has moved nothing "
        "that will replicate. STABLE-WRONG is the optimisation target."
    )
    add("")
    add("| Roster | Axis | STABLE-RIGHT | STABLE-WRONG | FLIPPING | Flipping share |")
    add("| --- | --- | ---: | ---: | ---: | ---: |")
    for roster in payload["rosters"]:
        total = roster["roster"]["rows"]
        for axis in ("intent", "entity", "joint"):
            counts = roster["stability"]["counts"][axis]
            flip = counts.get("FLIPPING", 0)
            add(
                f"| {roster['key']} | {axis} | {counts.get('STABLE-RIGHT', 0)} | "
                f"{counts.get('STABLE-WRONG', 0)} | {flip} | {num(pct(flip / total), 1)} % |"
            )
    add("")
    add(
        "Class composition of the STABLE-WRONG set on the joint axis (intent AND entities right in "
        "both arms is STABLE-RIGHT; neither in either is STABLE-WRONG). This is the bank proper: "
        "the mass a rollout must move."
    )
    add("")
    add("| Roster | " + " | ".join(BAD_CLASSES) + " |")
    add("| --- | " + " | ".join("---:" for _ in BAD_CLASSES) + " |")
    for roster in payload["rosters"]:
        composition = roster["stability"]["plan_classes_by_stability"]["joint"]["STABLE-WRONG"]
        add(
            f"| {roster['key']} | "
            + " | ".join(str(composition.get(name, 0)) for name in BAD_CLASSES)
            + " |"
        )
    add("")
    add("The same composition for the FLIPPING rows, i.e. the noise band's own shape:")
    add("")
    add("| Roster | " + " | ".join(BAD_CLASSES + ("CORRECT",)) + " |")
    add("| --- | " + " | ".join("---:" for _ in BAD_CLASSES + ("CORRECT",)) + " |")
    for roster in payload["rosters"]:
        composition = roster["stability"]["plan_classes_by_stability"]["joint"]["FLIPPING"]
        add(
            f"| {roster['key']} | "
            + " | ".join(str(composition.get(name, 0)) for name in BAD_CLASSES + ("CORRECT",))
            + " |"
        )
    add("")

    add("## 3. What the plan already fixed, and what it never touched")
    add("")
    add(
        "The bare core is the `direct-only` arm flown on the same roster, the same split identity "
        "and the same serving geometry -- one contact, no Perception, no exemplar supply, no slot "
        "contracts, no review loop. Its two intent classes collapse to `INTENT-WRONG` because it "
        "has no candidate list to be covered by."
    )
    add("")
    add("| Roster | Direct SLU / intent | PLAN SLU / intent | Rows repaired | Rows broken | Net |")
    add("| --- | --- | --- | ---: | ---: | ---: |")
    for roster in payload["rosters"]:
        direct = roster["arms"]["direct"]["official"]
        plan = roster["arms"]["plan"]["official"]
        trans = roster["direct_transitions"]
        add(
            f"| {roster['key']} | {num(pct(direct['slu_f1']))} / "
            f"{num(pct(direct['intent_accuracy']))} | {num(pct(plan['slu_f1']))} / "
            f"{num(pct(plan['intent_accuracy']))} | {trans['repaired_rows']} | "
            f"{trans['broken_rows']} | {trans['net_rows']:+d} |"
        )
    add("")
    for roster in payload["rosters"]:
        add(f"#### Direct class -> PLAN class -- {roster['label']}")
        add("")
        add("| Direct class | Rows | " + " | ".join(CLASSES) + " |")
        add("| --- | ---: | " + " | ".join("---:" for _ in CLASSES) + " |")
        for entry in roster["direct_transitions"]["matrix"]:
            add(
                f"| {entry['direct_class']} | {entry['rows']} | "
                + " | ".join(str(entry.get(name, 0)) for name in CLASSES)
                + " |"
            )
        add("")
    add(
        "Rows that entered the plan in a bad class and left it in the SAME bad class are the ones "
        "the review loop, the exemplar supply and the slot store never reached. They are where a "
        "new construction has to act, because every module the plan already carries has had its "
        "chance at them."
    )
    add("")
    add("| Roster | " + " | ".join(name for name in DIRECT_CLASSES if name != "CORRECT") + " |")
    add("| --- | " + " | ".join("---:" for name in DIRECT_CLASSES if name != "CORRECT") + " |")
    for roster in payload["rosters"]:
        survived = roster["direct_transitions"]["survived_in_place"]
        add(
            f"| {roster['key']} | "
            + " | ".join(
                str(survived.get(name, 0)) for name in DIRECT_CLASSES if name != "CORRECT"
            )
            + " |"
        )
    add("")

    add("## 4. Runtime-observable signatures of each bad class")
    add("")
    add(
        "Every signature below is available to a policy at the moment it runs, without gold: it "
        "comes from Perception's own state, the supply the episode carried, the Planner's route, "
        "the deliver normaliser's receipt, the carrier metadata and the response itself. The "
        "reference column is the STABLE-RIGHT rows of the same roster. `lift` is the class value "
        "minus the reference value in the signature's own units -- a univariate separation, not a "
        "fitted model. A signature with a large lift is a gate a rollout can actually apply."
    )
    add("")
    for roster in payload["rosters"]:
        add(f"### {roster['label']}")
        add("")
        classes_present = [name for name in BAD_CLASSES if name in roster["signatures"]]
        add(
            "| Signature | reference STABLE-RIGHT | "
            + " | ".join(f"{name} (n={roster['signatures'][name]['rows']})" for name in classes_present)
            + " |"
        )
        add("| --- | ---: | " + " | ".join("---:" for _ in classes_present) + " |")
        reference_table = roster["signatures"][classes_present[0]]["table"]
        for index, entry in enumerate(reference_table):
            cells = []
            for name in classes_present:
                row = roster["signatures"][name]["table"][index]
                cells.append(f"{num(row['class_value'])} ({signed(row['lift'])})")
            add(
                f"| {entry['label']} | {num(entry['reference_value'])} | "
                + " | ".join(cells)
                + " |"
            )
        add("")
        add(
            "Three signatures are CONSTANTS of the locked plan on both rosters -- twenty exemplars "
            "on every row, zero exemplars carrying no entity, and no context-fit compaction -- so "
            "they separate nothing and cannot be gated on. They are listed because a rollout that "
            "varies the supply will make them vary, and they are the baseline it will vary from."
        )
        add("")
        add(
            "The strongest separators per class, ranked inside their own unit family. A relative "
            "lift on a signature whose STABLE-RIGHT reference is itself near zero -- `revisions "
            "executed` is the clear case, at 0.02 on TRAIN Fold A -- is arithmetically large and "
            "practically thin; read it beside the absolute share column, which is the honest one."
        )
        add("")
        add("| Class | Strongest share-type separators (pp) | Strongest mean-type separators (relative) |")
        add("| --- | --- | --- |")
        for name in classes_present:
            table = roster["signatures"][name]["table"]
            shares = sorted(
                (row for row in table if row["kind"] == "share" and abs(row["lift"]) > 1e-9),
                key=lambda row: -abs(row["lift"]),
            )[:3]
            means = sorted(
                (
                    row
                    for row in table
                    if row["kind"] == "mean" and abs(row["reference_value"]) > 1e-9
                    and abs(row["lift"] / row["reference_value"]) > 1e-9
                ),
                key=lambda row: -abs(row["lift"] / row["reference_value"]),
            )[:3]
            add(
                f"| {name} | "
                + "; ".join(f"{row['label']} {signed(row['lift'], 1)}" for row in shares)
                + " | "
                + "; ".join(
                    f"{row['label']} {signed(100.0 * row['lift'] / row['reference_value'], 0)} %"
                    for row in means
                )
                + " |"
            )
        add("")

    add("## 5. The exemplar and the contract angle")
    add("")
    add(
        "On the STABLE-WRONG entity rows, what did the twenty supplied exemplars look like against "
        "the STABLE-RIGHT rows? `matched reference` re-weights the STABLE-RIGHT rows to the "
        "delivered-intent mixture of the target rows, so the contrast is not an artefact of which "
        "intents are hard."
    )
    add("")
    add(
        "| Roster | Rows | Measure | STABLE-WRONG entity rows | STABLE-RIGHT (plain) | "
        "STABLE-RIGHT (intent-matched) |"
    )
    add("| --- | ---: | --- | ---: | ---: | ---: |")
    labels = {
        "exemplars_supplied": "exemplars delivered",
        "exemplar_top_agreement": "share whose intent is candidate 1",
        "exemplar_no_entity_share": "share carrying no entity",
        "exemplar_covers_contract_types": "share of supplied contract TYPEs an exemplar shows",
        "contracts_supplied": "slot contracts delivered",
    }
    for roster in payload["rosters"]:
        angle = roster["exemplar_angle"]
        for key, label in labels.items():
            add(
                f"| {roster['key']} | {angle['rows']} | {label} | "
                f"{num(angle['target'][key], 3)} | {num(angle['reference'][key], 3)} | "
                f"{num(angle['matched_reference'][key], 3)} |"
            )
        add(
            f"| {roster['key']} | {angle['rows']} | share of the row's GOLD slot TYPEs that some "
            f"supplied exemplar shows | {num(angle['gold_type_coverage_by_exemplars'], 3)} | "
            f"{num(angle['reference_gold_type_coverage_by_exemplars'], 3)} | -- |"
        )
    add("")
    add(
        "On every FN of slot TYPE `t`, was `slot-contract:t` supplied to that row at all? A supply "
        "that never mentions the slot is a SUPPLY defect a rollout can repair by changing what is "
        "constructed. A supply that mentions it and is still omitted is an OBS or USE defect, and "
        "no amount of contract text will reach it."
    )
    add("")
    for roster in payload["rosters"]:
        add(f"#### {roster['label']}")
        add("")
        add("| Slot TYPE | FN | Rows with an FN of this type | Contract supplied on those rows | Share |")
        add("| --- | ---: | ---: | ---: | ---: |")
        for entry in roster["contract_coverage_on_fn"][:12]:
            add(
                f"| `{entry['slot_type']}` | {entry['fn']} | {entry['fn_rows']} | "
                f"{entry['contract_supplied_rows']} | {num(entry['contract_supplied_share'], 1)} % |"
            )
        add("")

    add("## 6. Headroom: the recoverable mass of each class")
    add("")
    add(
        "An EXACT upper bound, not an estimate. A perfectly repaired row delivers gold, so every "
        "unmatched gold unit becomes a matched one and nothing spurious remains -- `tp -> tp + fn`, "
        "`fp -> 0`, `fn -> 0` at word, char and exact-span level alike -- while every other row of "
        "the roster is left exactly as flown. No rollout can exceed these numbers by repairing that "
        "class; most will reach a fraction of them. The STABLE-WRONG column is the honest target, "
        "because the rest of the class is inside the replicate's own noise."
    )
    add("")
    for roster in payload["rosters"]:
        add(f"### {roster['label']}")
        add("")
        add(
            "| Class | Rows | SLU now | SLU if fixed | SLU pp | Intent pp | STABLE-WRONG rows | "
            "SLU pp (stable-wrong only) | Intent pp (stable-wrong only) |"
        )
        add("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
        order = sorted(
            [name for name in BAD_CLASSES if roster["headroom"][name]["rows"]],
            key=lambda name: -roster["headroom"][name]["all"]["slu"]["recoverable_pp"],
        )
        for name in order + ["ALL-BAD"]:
            entry = roster["headroom"][name]
            add(
                f"| {name} | {entry['rows']} | {num(entry['all']['slu']['now'])} | "
                f"{num(entry['all']['slu']['repaired'])} | "
                f"{signed(entry['all']['slu']['recoverable_pp'])} | "
                f"{signed(entry['all']['intent']['recoverable_pp'])} | "
                f"{entry['stable_wrong_rows']} | "
                f"{signed(entry['stable_wrong']['slu']['recoverable_pp'])} | "
                f"{signed(entry['stable_wrong']['intent']['recoverable_pp'])} |"
            )
        add("")

    add("## 7. Reconciliation with the earlier audits")
    add("")
    add(
        "The 2026-09-17 Phase A audits and the 2026-09-16 handoff report measured the RELEASED "
        "ANCHOR, an earlier arm on the same TRAIN Fold A roster; this bank measures the LOCKED "
        "v2.0 PLAN, which is the base every Stage-3 cell derives from. The two are expected to "
        "differ in level and to agree in structure, and they broadly do: the same four components "
        "carry the loss, same-type filler distance leads both and the equal-filler swap is a "
        "residue in both, the over-emission on reference-empty rows is unchanged in kind, and the "
        "intent-error split is still dominated by rows whose gold intent Perception never proposed. "
        "The one reordering is that over-emission has overtaken omission in the plan. The anchor "
        "column is quoted from those notes; the plan column is this read's own TRAIN Fold A number."
    )
    add("")
    train = payload["rosters"][0]["taxonomy_plan"]
    loss = train["loss_components"]
    empty = train["empty_gold"]
    coverage = train["coverage"]
    add("| Statistic | Released anchor (2026-09-16 / -17, TRAIN Fold A) | Locked plan (this read, TRAIN Fold A) |")
    add("| --- | --- | --- |")
    add(
        "| Same-type filler distance, share of FP+FN mass | 35.04 % | "
        f"{num(loss['same_type_share_of_loss'], 2)} % |"
    )
    add(
        "| Equal-filler type swap, share of FP+FN mass | 4.65 % | "
        f"{num(loss['type_swap_share_of_loss'], 2)} % |"
    )
    add(
        "| Unmatched reference (omission), share of FP+FN mass | 31.49 % | "
        f"{num(loss['omission_share_of_loss'], 2)} % |"
    )
    add(
        "| Unmatched prediction (over-emission), share of FP+FN mass | 28.82 % | "
        f"{num(loss['over_emission_share_of_loss'], 2)} % |"
    )
    add(
        "| Reference-empty rows emitting entities | 184 of 414 | "
        f"{empty['rows_emitting_entities']} of {empty['rows']} |"
    )
    add(
        "| Intent errors: gold never a candidate / covered but wrong | 143 / 95 (238 total) | "
        f"{coverage['uncovered']} / {coverage['covered']} ({coverage['intent_error_rows']} total) |"
    )
    add(
        "| Correct-intent rows with non-exact entities: FN-only / FP-only / mixed | 127 / 134 / 264 "
        f"| {train['entity_split']['fn_only']} / {train['entity_split']['fp_only']} / "
        f"{train['entity_split']['mixed']} |"
    )
    add("")
    add(
        "One difference is worth naming, descriptively and without attributing a cause: the "
        "covered-but-wrong rows are a SMALLER share of the plan's intent errors than of the "
        "anchor's (31.9 % against 39.9 %), so what remains is more sharply a coverage problem -- "
        "Perception's list, rather than the Solver's choice inside it. The two arms differ in "
        "several respects at once (the tool-free B1 base, the v2 slot store, the deliver "
        "normaliser), so no single module can be credited from this comparison; that is what a "
        "rollout is for."
    )
    add("")
    add("## 8. What this read does not say")
    add("")
    add(
        "It states no effectiveness, superiority or generalisation claim, admits no module, "
        "releases no store and authorises no flight. The headroom column is an upper bound on a "
        "PERFECT repair of a class and is not a forecast of any rollout. The class boundaries are "
        "an attribution convention, not a causal claim: a row typed `INTENT-UNCOVERED` may also "
        "carry entity defects that the convention hides behind its first failure, and the "
        "same-type / swap / over-emission / omission split of the unmatched remainder is a "
        "heuristic decomposition, deterministic but not a statement about what the model heard. "
        "Every number is a development number on a TRAIN construction fold or on a DEV roster "
        "(owner decisions 28 and 86) and is never a test claim."
    )
    add("")
    add(
        f"Machine-readable payload: `$SPEECHRL_DATA_DIR/analysis/{OUT_DIRNAME}/bad-case-bank.json` "
        f"(schema `{SCHEMA}`, recipe `{RECIPE_ID}`); per-row typed bank "
        f"`$SPEECHRL_DATA_DIR/analysis/{OUT_DIRNAME}/bank.jsonl` (ids, class labels, slot TYPE "
        "names, counts and signatures only -- no text and no filler); derived per-row caches under "
        "`cache/`. Script `scripts/analysis/slurp_plan_bad_case_bank.py`."
    )
    add("")
    return lines


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--data-root",
        default=None,
        help="SPEECHRL_DATA_DIR (default: the environment variable)",
    )
    parser.add_argument("--repo", default=str(REPO), help="study repository checkout")
    parser.add_argument("--umbrella-lock", default=DEFAULT_LOCK, help="umbrella datasets.lock.json")
    parser.add_argument("--markdown", default=DEFAULT_MARKDOWN, help="rendered note, repo-relative")
    parser.add_argument(
        "--refresh-gold",
        action="store_true",
        help="ignore the derived per-row caches and re-read the governed gold split",
    )
    args = parser.parse_args(argv)

    import os

    data_root = Path(args.data_root or os.environ.get("SPEECHRL_DATA_DIR", ""))
    if not data_root.is_dir():
        raise BankError("--data-root (or SPEECHRL_DATA_DIR) does not resolve to a directory")
    repo = Path(args.repo).resolve()
    out_root = data_root / "analysis" / OUT_DIRNAME
    out_root.mkdir(parents=True, exist_ok=True)

    rosters = [
        analyse_roster(
            spec=spec,
            repo=repo,
            data_root=data_root,
            lock_path=Path(args.umbrella_lock),
            out_root=out_root,
            refresh=args.refresh_gold,
        )
        for spec in ROSTERS
    ]

    bank_rows = []
    for roster in rosters:
        bank_rows.extend(roster.pop("bank"))
    bank_path = out_root / "bank.jsonl"
    with bank_path.open("w", encoding="utf-8", newline="\n") as handle:
        for entry in sorted(bank_rows, key=lambda row: (row["roster"], row["sample_id"])):
            handle.write(json.dumps(entry, ensure_ascii=True, sort_keys=True) + "\n")

    payload = {
        "schema": SCHEMA,
        "recipe": RECIPE_ID,
        "run_id": RUN_ID,
        "date": "2026-09-24",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "script": {
            "relpath": "scripts/analysis/slurp_plan_bad_case_bank.py",
            "sha256": digest(Path(__file__).resolve()),
        },
        "umbrella_lock": str(Path(args.umbrella_lock)),
        "contacts": {
            "model": 0,
            "tokenizer": 0,
            "encoder": 0,
            "scorer": 0,
            "server": 0,
            "network": 0,
            "gpu_hours": 0.0,
        },
        "rosters": rosters,
        "bank": {"path": str(bank_path), "rows": len(bank_rows), "sha256": digest(bank_path)},
    }
    payload["payload_sha256"] = sha_of(
        {key: value for key, value in payload.items() if key != "generated_at"}
    )

    json_path = out_root / "bad-case-bank.json"
    json_path.write_text(
        json.dumps(payload, indent=1, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8"
    )

    lines = render(payload)
    lines = render_rest(payload, lines)
    markdown_path = repo / args.markdown
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text("\n".join(lines), encoding="utf-8", newline="\n")

    print(f"payload  {json_path}")
    print(f"bank     {bank_path} ({len(bank_rows)} rows)")
    print(f"markdown {markdown_path}")
    for roster in rosters:
        head = roster["headroom"]
        top = max(
            (name for name in BAD_CLASSES if head[name]["rows"]),
            key=lambda name: head[name]["all"]["slu"]["recoverable_pp"],
        )
        print(
            f"  {roster['key']}: rows {roster['roster']['rows']}, "
            f"stable-wrong {roster['stability']['counts']['joint'].get('STABLE-WRONG', 0)}, "
            f"flipping {roster['stability']['counts']['joint'].get('FLIPPING', 0)}, "
            f"largest class by SLU headroom {top} "
            f"({head[top]['all']['slu']['recoverable_pp']:+.2f} pp)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
