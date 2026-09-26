#!/usr/bin/env python3
"""CLI (S3-3): score a grouped-Solver rollout's five raw samples on COPIES and
select the best/worst disagreement pair per row.

Model-free. The five raw Solver samples already exist in the sealed run's
``solver_group`` custody (I7g); this CLI renders each sample index's answer
across every row into one canonical outputs COPY (``analysis.
native_commit_replay.replay_row``'s / ``scripts.analysis.
slurp_verifier_measurement.render_answer``'s exact rendering, byte for byte),
scores each of the five copies ONCE through the registered official scorer
(never ``core.scoring_batch``, which scores a bundle-verified run directory
and every side here is a derived copy with no manifest and no bundle -- the
precedent is ``analysis.b8a_delivery_node_read`` /
``scripts.analysis.slurp_verifier_measurement.score_copy``), and picks the
best and worst sample per row by ``(slu_f1_f1, scenario_action_exact)`` with
a deterministic ascending-``sample_index`` tie-break. The delivered answer's
own official score is read from the run's SEALED ``<run_id>.scores.json``
(``sealed_per_sample``) -- never rescored -- which is why the contacts block
below reads ``scorer: <samples>`` and not ``<samples> + 1``.

No utterance text, gold label, transcript or model output is printed or
persisted anywhere by this CLI: ``per_row.json`` and ``pairs.json`` carry
ids, stratum names, sample indices, scores and hashes only. The rendered
outputs copies themselves DO carry the rendered JSON answer text (scenario /
action / entity type+filler), because the registered scorer needs it to
score against gold -- exactly as every other ``score_copy`` caller in this
repository writes; they are written under ``--analysis-root``, never under
the repository.

Stages (``--stage``): ``render`` (write the five per-sample-index outputs
copies), ``score`` (score each rendered copy once through ``--scorer-id``),
``pairs`` (build ``per_row.json`` and ``pairs.json`` from the scored sides
plus the sealed delivered scores and the roster's stratum), ``all`` (the
three in sequence). Every stage is idempotent: a copy or score file that
already exists on disk is read back, never rewritten.

S3-4s (owner decision 106, 2026-09-23): the whole TRAJECTORY
--------------------------------------------------------------
"Roll out as much information as possible; we are doing SYSTEM-level
optimisation." ``pairs.json`` therefore carries, per DISAGREEING row, a
``trajectory`` block rebuilt from the SEALED episode receipt (cell ROLL-1 is
not re-flown): the Perception candidate ids in order and whether the
construction gold intent is among them, the best and worst Solver sample
indices with their answer hashes, the delivered path after the commit (the
Reviewer verdict labels and primitive ids per iteration, the Planner action
labels, the revision count, the delivery kind and whether the delivered
answer scores below the best sample), and the per-node completion tokens and
truncation flags. IDS, LABELS, COUNTS AND HASHES ONLY -- exactly the
discipline the rest of this CLI keeps; no statement, transcript, gold label
or model output text is ever written to ``pairs.json``.

Two of those facts do not live in the episode receipt and are read from the
sealed attempt's own ``<run_id>.trace.jsonl`` instead, joined by request id:
per-contact ``usage.completion_tokens`` (``MODEL_RESPONSE``) and per-contact
``finish_reason`` (``MODEL_WIRE_RESPONSE``), and, for the Perception visit
ONLY, the response text -- opened here to read back the ordered candidate
``intent_id``s and discarded, exactly as this CLI already opens sealed
Solver answers to render and score them. One more fact does not live in
either: the construction GOLD intent. It is read, when available, from the
construction roster's own annotation or from an explicit ``--gold-intents``
map, and it enters ``pairs.json`` only as the boolean
``gold_intent_in_candidates`` and a count.

Whatever a given seal does not carry is reported ABSENT with a named reason
rather than guessed: cell ROLL-1's own ``native_episode`` fragment arms
neither ``reviewer_verdict`` (item E37) nor ``role_context``, so its receipt
carries no ``reviewer_verdicts`` key -- the Reviewer verdict labels are then
re-derived from the sealed Reviewer response text with the registered
closed-vocabulary parser (``rails.review_primitives.parse_review_primitive``),
which is the same reading the armed path would have sealed, and the block
says which source it used.

Parallelism (2026-09-26)
------------------------
``--workers`` fans the ``score`` stage out over the rendered copies through
``analysis.parallel.map_by_key``: one worker process per COMPLETE official
scoring, collected by copy name and read back in sorted name order. Nothing
is sharded -- each task is the same whole ``score_copy`` over the same whole
copy -- and the numbers do not depend on the worker count.

``render`` and ``pairs`` stay in one process: they are seconds of work beside
minutes of scoring. ``--mode supply-variants``'s own scoring stays serial too,
deliberately: it validates each arm's row identities AGAINST THE PREVIOUS
arm's while it iterates, and each call writes an exclusive source-bound
receipt through ``core.scoring_batch.score_complete_derived_copy``, so making
it concurrent is a change to that receipt's exclusivity rather than a
scheduling change.

Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src python \\
      scripts/analysis/stage3_rollout_score.py \\
      --run SAEA-SLURP-STAGE3-ROLLOUT-R01-V1 \\
      --attempt attempt-slurp-native-stage3-rollout-r01-generation-v1 \\
      --roster docs/receipts/rosters/slurp-stage3-construction-r01.json \\
      --analysis-root "$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-ROLLOUT-R01-SCORE-V1" \\
      --scorer-id slurp-slu-official-projected-v3-train --stage all
"""

from __future__ import annotations

import argparse
import functools
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

SCHEMA = "saea-stage3-rollout-score-v1"
#: S3-4s: the ``pairs.json`` payload version. Bumped because the file gained
#: a per-row ``trajectory`` block and a loader-shaped ``rows`` array; the
#: pre-existing ``pairs`` array, its fields and its ordering are unchanged,
#: so a reader written against v1 keeps reading v1's fields.
PAIRS_SCHEMA = "saea-stage3-rollout-pairs-v2"
#: The episode STAGE names (``reproduction.ojw.native_episode``) whose
#: per-node tokens and truncation this block reports. The reviewer PHASE is
#: spelled ``reviewer`` and its episode STAGE is spelled ``review``; both are
#: written out so a reader never has to know that.
TRAJECTORY_STAGES = ("perception", "solver", "review", "planner", "acquisition")
DEFAULT_SCORER_ID = "slurp-slu-official-projected-v3-train"
COUNT_FIELDS = (
    "slu_f1_word_tp", "slu_f1_word_fp", "slu_f1_word_fn",
    "slu_f1_char_tp", "slu_f1_char_fp", "slu_f1_char_fn",
    "slot_f1_exact_tp", "slot_f1_exact_fp", "slot_f1_exact_fn",
)
EMPTY_ANSWER = json.dumps(
    {"scenario": "", "action": "", "entities": []}, ensure_ascii=False, sort_keys=True
)


class Stage3ScoreError(RuntimeError):
    """A sealed input is missing or does not have the shape this CLI needs."""


# ---------------------------------------------------------------------------
# Small shared helpers (the ``slurp_verifier_measurement`` idiom, module docstring)
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(document: object) -> str:
    return hashlib.sha256(
        json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    return sha256_file(path)


def write_json(path: Path, payload: Mapping[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )
    return sha256_file(path)


def run_dir(root: Path, run_id: str, attempt_id: str) -> Path:
    directory = root / "runs" / run_id / attempt_id
    if not directory.is_dir():
        raise Stage3ScoreError(f"no sealed attempt directory at {directory}")
    return directory


def load_roster(repo_root: Path, relpath: str) -> tuple[dict[str, str], str, str]:
    """``{sample_id: stratum}`` plus the roster file's sha256 and (if present)
    ``split_identity_hash``. Generic on purpose (the ``slurp_verifier_
    measurement.load_roster`` idiom): a construction roster (``saea-roster-
    receipt-v1``) and an older evaluation-roster receipt (e.g. TRAIN Fold A)
    both carry ``items[].sample_id`` / ``items[].stratum``, and neither is
    re-verified here -- this CLI reads identity, not authorises a draw."""

    path = repo_root / relpath
    file_sha256 = sha256_file(path)
    document = json.loads(path.read_text(encoding="utf-8"))
    strata: dict[str, str] = {}
    for item in document["items"]:
        sample_id = str(item["sample_id"])
        stratum = item.get("stratum")
        if not isinstance(stratum, str) or not stratum:
            raise Stage3ScoreError(f"roster item {sample_id!r} carries no stratum")
        strata[sample_id] = stratum
    split_identity_hash = str(document.get("split_identity_hash") or "")
    return strata, file_sha256, split_identity_hash


def render_answer(payload: Mapping[str, Any] | None) -> str:
    """Render one parsed Solver answer to the canonical delivered payload,
    byte for byte the form ``analysis.native_commit_replay.replay_row`` /
    ``scripts.analysis.slurp_verifier_measurement.render_answer`` write."""

    if payload is None:
        return EMPTY_ANSWER
    body = {
        "scenario": payload.get("scenario", ""),
        "action": payload.get("action", ""),
        "entities": [
            {"type": entity["type"], "filler": entity["filler"]}
            for entity in payload.get("entities", [])
        ],
    }
    return json.dumps(body, ensure_ascii=False, sort_keys=True)


def sealed_per_sample(directory: Path, run_id: str, scorer_id: str) -> dict[str, dict[str, Any]]:
    """The arm's own sealed official per-row scores for the DELIVERED
    (committed) answer -- read, never recomputed (module docstring)."""

    path = directory / f"{run_id}.scores.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    if scorer_id not in document:
        raise Stage3ScoreError(
            f"{path} carries no sealed score for {scorer_id!r}; known: {sorted(document)}"
        )
    rows = document[scorer_id]["per_sample"]
    return {str(row["sample_id"]): row for row in rows}


def correctness_fields(row: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "scenario_action_exact": bool(float(row["scenario_action_exact"]) >= 1.0),
        "slu_f1_f1": float(row["slu_f1_f1"]),
    }
    for field in COUNT_FIELDS:
        if field in row:
            out[field] = row[field]
    return out


# ---------------------------------------------------------------------------
# S3-4s: the sealed trajectory, rebuilt model-free
# ---------------------------------------------------------------------------


def load_gold_intents(
    roster_path: Path, gold_path: Path | None
) -> tuple[dict[str, str], str]:
    """``({sample_id: "<scenario>_<action>"}, source)``.

    The construction gold intent is legal to READ here (construction rows,
    owner decision 82) and illegal to WRITE anywhere: it leaves this
    function only as the boolean ``gold_intent_in_candidates`` and a count.

    Two sources, in order. (1) An explicit ``--gold-intents`` JSON map --
    the coordinator's own model-free export over the construction roster.
    (2) The roster receipt's own per-item annotation, when it carries one
    (``gold_intent``/``scenario_action``/``intent_id``). The R01/R01C
    receipts as committed carry ``stratum`` (the SCENARIO) and no
    scenario_action, so without (1) this returns an empty map and the block
    says ``"unavailable"`` rather than silently answering the question with
    a scenario-level match that is not the question.
    """

    if gold_path is not None:
        document = json.loads(gold_path.read_text(encoding="utf-8"))
        if not isinstance(document, Mapping):
            raise Stage3ScoreError("--gold-intents must be a JSON object")
        return {str(k): str(v) for k, v in document.items()}, "gold-intents-file"
    document = json.loads(roster_path.read_text(encoding="utf-8"))
    annotated: dict[str, str] = {}
    for item in document.get("items", ()):
        for field in ("gold_intent", "scenario_action", "intent_id"):
            value = item.get(field)
            if isinstance(value, str) and value:
                annotated[str(item["sample_id"])] = value
                break
    return annotated, ("roster-annotation" if annotated else "unavailable")


def scan_trace(path: Path) -> dict[str, dict[str, Any]]:
    """``{request_id: {completion_tokens, finish_reason, text}}`` from one
    sealed ``<run_id>.trace.jsonl``.

    Streamed, like ``analysis.finite_completion_exposure_scan.scan_trace``,
    and reduced to the three facts the trajectory needs. ``text`` is kept in
    memory only so the Perception visit's ordered candidate ids can be read
    back; it is never printed and never written. The ``MODEL_WIRE_RESPONSE``
    channel's base64 body is deliberately not decoded or retained.
    """

    facts: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(record, Mapping):
                continue
            channel = record.get("channel")
            record_id = str(record.get("record_id", ""))
            payload = record.get("payload")
            payload = payload if isinstance(payload, Mapping) else {}
            if channel == "MODEL_RESPONSE" and record_id.endswith("/response"):
                request_id = record_id[: -len("/response")]
                usage = payload.get("usage")
                usage = usage if isinstance(usage, Mapping) else {}
                tokens = usage.get("completion_tokens")
                entry = facts.setdefault(request_id, {})
                entry["completion_tokens"] = tokens if isinstance(tokens, int) else None
                body = payload.get("text")
                entry["text"] = body if isinstance(body, str) else None
            elif channel == "MODEL_WIRE_RESPONSE" and record_id.endswith("/wire-response"):
                request_id = record_id[: -len("/wire-response")]
                reason = payload.get("finish_reason")
                facts.setdefault(request_id, {})["finish_reason"] = (
                    reason if isinstance(reason, str) else None
                )
    return facts


def _contacts_of(visit: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    receipt = visit.get("execution_receipt")
    if not isinstance(receipt, Mapping):
        return []
    contacts = receipt.get("contacts")
    if not isinstance(contacts, list):
        return []
    return [contact for contact in contacts if isinstance(contact, Mapping)]


def _candidate_intent_ids(response_text: object) -> tuple[list[str], int, str]:
    """``(ordered distinct intent ids, raw count, reading)``.

    The Perception phase answers under the registered
    ``slurp-intent-hypotheses-v1`` response format, so its response IS the
    JSON candidate document. The ids are reported in first-occurrence
    distinct order -- the same ordering rule the bounded projection policy
    applies (``bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1``)
    -- and the raw count is reported beside it, so a duplicate a projection
    would have folded is visible rather than invented.
    """

    if not isinstance(response_text, str) or not response_text.strip():
        return [], 0, "absent"
    try:
        document = json.loads(response_text)
    except json.JSONDecodeError:
        return [], 0, "unparseable"
    rows = document.get("candidates") if isinstance(document, Mapping) else None
    if not isinstance(rows, list):
        return [], 0, "no-candidates-field"
    ordered: list[str] = []
    raw = 0
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        intent_id = row.get("intent_id")
        if not isinstance(intent_id, str) or not intent_id:
            continue
        raw += 1
        if intent_id not in ordered:
            ordered.append(intent_id)
    return ordered, raw, "sealed-perception-response"


def _reviewer_verdicts(
    receipt: Mapping[str, Any], visits: Sequence[Mapping[str, Any]],
    trace: Mapping[str, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], str]:
    """The Reviewer's verdict LABELS per review visit, and where they came
    from.

    An E37-armed row seals them itself (``reviewer_verdicts``). An unarmed
    row -- which is every row of cell ROLL-1 -- does not, so the same
    closed-vocabulary parser the armed path uses is applied here to the
    sealed Reviewer response text. Only the token and the disposition are
    kept; the free-text rationale is never parsed, printed or stored.
    """

    sealed = receipt.get("reviewer_verdicts")
    if isinstance(sealed, list) and sealed:
        return (
            [
                {
                    "visit": mark.get("visit"),
                    "token": mark.get("token"),
                    "disposition": mark.get("disposition"),
                }
                for mark in sealed if isinstance(mark, Mapping)
            ],
            "sealed-reviewer-verdicts",
        )
    from speech_aware_evidence_acquisition.rails.review_primitives import (  # noqa: PLC0415
        REVIEW_VERDICT_ILLEGAL,
        parse_review_primitive,
    )

    marks: list[dict[str, Any]] = []
    visit_number = 0
    for visit in visits:
        if visit.get("stage") != "review":
            continue
        contacts = _contacts_of(visit)
        body = None
        if contacts:
            body = trace.get(str(contacts[-1].get("request_id")), {}).get("text")
        if not isinstance(body, str):
            marks.append({"visit": visit_number, "token": None, "disposition": "unavailable"})
        else:
            token, _head, _rest = parse_review_primitive(body)
            marks.append(
                {
                    "visit": visit_number,
                    "token": None if token == REVIEW_VERDICT_ILLEGAL else token,
                    "disposition": (
                        "review_verdict_illegal"
                        if token == REVIEW_VERDICT_ILLEGAL else "legal"
                    ),
                }
            )
        visit_number += 1
    return marks, ("derived-from-sealed-response" if marks else "no-review-visit")


def _delivery_kind(receipt: Mapping[str, Any]) -> str:
    """The delivery kind, through the SAME validator the seal used."""

    try:
        from speech_aware_evidence_acquisition.rails.native_episode_receipt import (  # noqa: PLC0415
            validate_native_episode_delivery_receipt,
        )

        return validate_native_episode_delivery_receipt(receipt).kind
    except Exception:  # noqa: BLE001 -- a post-seal READER never stops a read
        disposition = receipt.get("terminal_disposition")
        if isinstance(disposition, Mapping):
            reason = disposition.get("reason")
            if isinstance(reason, str) and reason:
                return f"unclassified:{reason}"
        if receipt.get("accepted_solver_receipt") is not None:
            return "accepted"
        return "unclassified"


def build_trajectory(
    row: Mapping[str, Any], *, best_index: int, worst_index: int,
    rendered: Mapping[int, str], trace: Mapping[str, Mapping[str, Any]],
    gold_intent: str | None, delivered_f1: float | None, best_f1: float,
) -> dict[str, Any]:
    """One disagreeing row's whole trajectory, as ids, labels, counts and
    hashes. Never raises on a seal that carries less than this wants: the
    missing part is reported absent with a named reason."""

    trajectory: dict[str, Any] = {
        "schema": "saea-stage3-rollout-trajectory-v1",
        "trace_joined": bool(trace),
    }

    # -- the two compared samples ----------------------------------------
    group = row.get("solver_group")
    samples = group.get("samples") if isinstance(group, Mapping) else None
    samples = samples if isinstance(samples, list) else []
    by_index = {
        int(record["sample_index"]): record
        for record in samples
        if isinstance(record, Mapping) and isinstance(record.get("sample_index"), int)
    }

    def _sample_block(index: int) -> dict[str, Any]:
        record = by_index.get(index)
        contacts = record.get("contacts") if isinstance(record, Mapping) else None
        contacts = [c for c in contacts if isinstance(c, Mapping)] if isinstance(contacts, list) else []
        last = contacts[-1] if contacts else {}
        request_id = str(last.get("request_id") or "")
        return {
            "sample_index": index,
            "parse_status": record.get("parse_status") if isinstance(record, Mapping) else None,
            # The hash of the CANONICAL RENDERED answer -- the exact bytes
            # the ADV-1 instruction will carry for this sample.
            "answer_sha256": hashlib.sha256(
                rendered.get(index, EMPTY_ANSWER).encode("utf-8")
            ).hexdigest(),
            # The sealed raw contact's own custody, when the seal carries it.
            "contact_response_text_sha256": last.get("response_text_sha256"),
            "completion_tokens": trace.get(request_id, {}).get("completion_tokens"),
        }

    trajectory["best"] = _sample_block(best_index)
    trajectory["worst"] = _sample_block(worst_index)

    receipt = row.get("native_episode_receipt")
    if not isinstance(receipt, Mapping):
        trajectory["available"] = False
        trajectory["reason"] = "the sealed row carries no native_episode_receipt"
        return trajectory
    trajectory["available"] = True

    visits = receipt.get("role_visits")
    visits = [v for v in visits if isinstance(v, Mapping)] if isinstance(visits, list) else []

    # -- Perception candidates -------------------------------------------
    perception_visits = [v for v in visits if v.get("stage") == "perception"]
    candidate_ids: list[str] = []
    raw_count = 0
    reading = "no-perception-visit"
    if perception_visits:
        contacts = _contacts_of(perception_visits[-1])
        body = trace.get(str(contacts[-1].get("request_id")), {}).get("text") if contacts else None
        candidate_ids, raw_count, reading = _candidate_intent_ids(body)
    trajectory["perception"] = {
        "candidate_intent_ids": candidate_ids,
        "candidate_count": len(candidate_ids),
        "raw_candidate_count": raw_count,
        "reading": reading,
        "gold_intent_known": gold_intent is not None,
        "gold_intent_in_candidates": (
            None if gold_intent is None else gold_intent in candidate_ids
        ),
        "gold_intent_rank": (
            None if gold_intent is None or gold_intent not in candidate_ids
            else candidate_ids.index(gold_intent)
        ),
    }

    # -- the delivered path ----------------------------------------------
    marks, verdict_source = _reviewer_verdicts(receipt, visits, trace)
    routes = receipt.get("planner_routes")
    routes = [r for r in routes if isinstance(r, Mapping)] if isinstance(routes, list) else []
    revision_counts = [
        r["revision_count"] for r in routes
        if isinstance(r.get("revision_count"), int) and not isinstance(r["revision_count"], bool)
    ]
    trajectory["delivered"] = {
        "kind": _delivery_kind(receipt),
        "reviewer_verdicts": marks,
        "reviewer_verdict_source": verdict_source,
        "planner_actions": [
            {
                "action": route.get("action"),
                "legal": route.get("legal", True),
                "disposition": route.get("disposition"),
                "revision_count": route.get("revision_count"),
            }
            for route in routes
        ],
        "revision_count": max(revision_counts) if revision_counts else 0,
        "delivered_slu_f1_f1": delivered_f1,
        "delivered_below_best": (
            None if delivered_f1 is None else bool(delivered_f1 < best_f1)
        ),
    }

    # -- per-node tokens and truncation ----------------------------------
    nodes: list[dict[str, Any]] = []
    tokens_by_stage: dict[str, int] = {}
    known_by_stage: dict[str, int] = {}
    unknown_by_stage: dict[str, int] = {}
    truncated_stages: list[str] = []
    for index, visit in enumerate(visits):
        stage = str(visit.get("stage") or "unknown")
        contacts = _contacts_of(visit)
        tokens = [
            trace.get(str(contact.get("request_id")), {}).get("completion_tokens")
            for contact in contacts
        ]
        finish_reasons = [
            trace.get(str(contact.get("request_id")), {}).get("finish_reason")
            for contact in contacts
        ]
        truncated = bool(visit.get("truncated")) or any(
            reason == "length" for reason in finish_reasons
        )
        if truncated:
            truncated_stages.append(stage)
        known = [value for value in tokens if isinstance(value, int)]
        tokens_by_stage[stage] = tokens_by_stage.get(stage, 0) + sum(known)
        known_by_stage[stage] = known_by_stage.get(stage, 0) + len(known)
        unknown_by_stage[stage] = unknown_by_stage.get(stage, 0) + (len(tokens) - len(known))
        nodes.append({
            "role_visit_index": index,
            "stage": stage,
            "role_id": visit.get("role_id"),
            "contacts": len(contacts),
            "completion_tokens": tokens,
            "finish_reasons": finish_reasons,
            "truncated": truncated,
        })
    truncation_events = receipt.get("truncation_events")
    trajectory["nodes"] = nodes
    # Only a stage whose contacts actually reported a token count appears:
    # a stage that reported none would otherwise read as a genuine zero.
    trajectory["completion_tokens_by_stage"] = {
        stage: tokens_by_stage[stage] for stage in TRAJECTORY_STAGES
        if known_by_stage.get(stage)
    }
    trajectory["unknown_completion_tokens_by_stage"] = {
        stage: count for stage, count in sorted(unknown_by_stage.items()) if count
    }
    trajectory["truncated_stages"] = sorted(set(truncated_stages))
    trajectory["sealed_truncation_event_count"] = (
        truncation_events.get("count") if isinstance(truncation_events, Mapping) else 0
    )
    return trajectory


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------


def load_sealed_rows(
    directory: Path, run_id: str, roster: Mapping[str, str], samples: int
) -> dict[str, dict[str, Any]]:
    """``{sample_id: {"row": <sealed row>, "rendered": {index: text}}}``.

    Re-reads the sealed ``outputs.jsonl`` -- the same file :func:`render`
    reads, with the same canonical rendering -- so the ``pairs`` stage can
    rebuild a trajectory on its own, without a prior ``render`` in the same
    process. Zero contacts of any kind.
    """

    out: dict[str, dict[str, Any]] = {}
    for row in iter_jsonl(directory / f"{run_id}.outputs.jsonl"):
        sample_id = str(row["sample_id"])
        if sample_id not in roster:
            continue
        group = row.get("solver_group")
        records = group["samples"] if isinstance(group, Mapping) else []
        rendered = {}
        for record in records:
            index = int(record["sample_index"])
            payload = record["parsed_answer"] if record["parse_status"] == "ok" else None
            rendered[index] = render_answer(payload)
        out[sample_id] = {"row": row, "rendered": rendered}
    return out


def detect_samples(directory: Path, run_id: str) -> int:
    for row in iter_jsonl(directory / f"{run_id}.outputs.jsonl"):
        group = row.get("solver_group")
        if isinstance(group, Mapping) and isinstance(group.get("samples"), list):
            return len(group["samples"])
    raise Stage3ScoreError(f"{run_id}: no row carries a solver_group to size samples from")


def render(
    directory: Path, run_id: str, roster: Mapping[str, str], samples: int, out_dir: Path
) -> dict[str, Any]:
    samples_text: list[dict[str, str]] = [dict() for _ in range(samples)]
    rows_seen: set[str] = set()
    malformed_samples = 0
    rows_with_a_malformed_sample = 0
    for row in iter_jsonl(directory / f"{run_id}.outputs.jsonl"):
        sample_id = str(row["sample_id"])
        if sample_id not in roster:
            continue
        group = row.get("solver_group")
        if not isinstance(group, Mapping):
            raise Stage3ScoreError(f"row {sample_id} carries no solver_group custody")
        records = group["samples"]
        if len(records) != samples:
            raise Stage3ScoreError(
                f"row {sample_id} carries {len(records)} samples, expected {samples}"
            )
        row_malformed = 0
        for record in records:
            index = int(record["sample_index"])
            payload = record["parsed_answer"] if record["parse_status"] == "ok" else None
            if payload is None:
                row_malformed += 1
            samples_text[index][sample_id] = render_answer(payload)
        malformed_samples += row_malformed
        rows_with_a_malformed_sample += 1 if row_malformed else 0
        rows_seen.add(sample_id)

    missing = sorted(set(roster) - rows_seen)
    if missing:
        raise Stage3ScoreError(
            f"{len(missing)} roster row(s) absent from {run_id}.outputs.jsonl; first: {missing[0]}"
        )

    ids = sorted(rows_seen)
    manifest: dict[str, Any] = {
        "schema": SCHEMA, "stage": "render", "run_id": run_id, "samples": samples,
        "rows": len(ids), "malformed_samples": malformed_samples,
        "rows_with_a_malformed_sample": rows_with_a_malformed_sample,
        "copies": {},
    }
    for index in range(samples):
        path = out_dir / f"sample-{index}-outputs.jsonl"
        digest = write_jsonl(path, [{"sample_id": i, "text": samples_text[index][i]} for i in ids])
        manifest["copies"][f"sample_{index}"] = {"path": str(path), "sha256": digest, "rows": len(ids)}
    write_json(out_dir / "render-manifest.json", manifest)
    return manifest


# ---------------------------------------------------------------------------
# score
# ---------------------------------------------------------------------------


def map_by_key(tasks, *, workers):
    """``analysis.parallel.map_by_key``, imported lazily.

    This module is executed as a COPY beside a read (``cp`` then ``python
    stage3_rollout_score.py``), so it resolves the package only through
    ``sys.path`` at call time, exactly as every other package use here does.
    """

    from speech_aware_evidence_acquisition.analysis.parallel import (  # noqa: PLC0415
        map_by_key as _map_by_key,
    )

    return _map_by_key(tasks, workers=workers)


def resolve_workers(requested, *, cap=None):
    """``analysis.parallel.resolve_workers``, imported lazily (see above)."""

    from speech_aware_evidence_acquisition.analysis.parallel import (  # noqa: PLC0415
        resolve_workers as _resolve_workers,
    )

    return _resolve_workers(requested, cap=cap)


def score_copy(
    scorer_id: str, outputs_copy: Path, result_path: Path, lock: Mapping[str, object], root: Path
) -> tuple[dict[str, Any], float]:
    """One complete registered scoring over a COPY, cached by its result
    file (module docstring; the ``slurp_verifier_measurement.score_copy``
    idiom, unchanged)."""

    from speech_aware_evidence_acquisition.core.base import SCORERS  # noqa: PLC0415
    import speech_aware_evidence_acquisition.core.scorers  # noqa: PLC0415, F401

    if result_path.exists():
        return json.loads(result_path.read_text(encoding="utf-8"))[scorer_id], 0.0
    scorer = SCORERS.resolve(scorer_id)
    started = time.time()
    result = scorer(outputs_copy, lock, root)
    elapsed = time.time() - started
    aggregate = result["aggregate"]
    if not aggregate["identity_check"]["passed"]:
        raise Stage3ScoreError(f"{scorer_id} port/official identity check failed on {outputs_copy}")
    write_json(result_path, {scorer_id: result})
    return result, elapsed


def score(
    scorer_id: str, manifest: Mapping[str, Any], out_dir: Path, lock: Mapping[str, object],
    root: Path, *, workers: int | None = None,
) -> dict[str, Any]:
    """One complete registered scoring per rendered copy, the copies in parallel.

    Each task is a WHOLE :func:`score_copy` over a complete manifest copy --
    five complete official scorings, never one scoring sharded five ways -- so
    the engineering-base rule that the paper-facing number comes from the
    standard scorer run once per complete manifest is untouched. The official
    ``evaluate.py`` subprocess inside each task stays exactly as serial as it
    always was; what runs concurrently is whole scorings of DIFFERENT copies.

    Every copy's render-manifest hash is verified BEFORE any scoring starts
    (it used to be verified just before that copy's own scoring), so a drifted
    copy now refuses before the first scorer contact rather than after some of
    them. Results are collected by copy name and read back in sorted name
    order, so ``scored`` is populated exactly as the serial loop populated it.
    """

    copies = sorted(manifest["copies"].items())
    verified: dict[str, str] = {}
    for name, copy_entry in copies:
        path = Path(copy_entry["path"])
        measured = sha256_file(path)
        if measured != copy_entry["sha256"]:
            raise Stage3ScoreError(f"{path} drifted from its render manifest sha256")
        verified[name] = measured
    tasks: dict[str, Callable[[], tuple[dict[str, Any], float]]] = {
        name: functools.partial(
            score_copy,
            scorer_id,
            Path(copy_entry["path"]),
            out_dir / f"{name}-{scorer_id}-scores.json",
            lock,
            root,
        )
        for name, copy_entry in copies
    }
    outcomes = map_by_key(tasks, workers=resolve_workers(workers, cap=len(tasks)))
    scored: dict[str, Any] = {}
    for name, _copy_entry in copies:
        result, elapsed = outcomes[name]
        scored[name] = {
            "outputs_sha256": verified[name],
            "official_slu_f1_pp": 100 * float(result["aggregate"]["official"]["slu_f1"]),
            "official_intent_pp": 100 * float(result["aggregate"]["official"]["intent_accuracy"]),
            "per_sample": {str(r["sample_id"]): correctness_fields(r) for r in result["per_sample"]},
            "scoring_seconds": elapsed,
        }
    write_json(
        out_dir / "score-summary.json",
        {
            "schema": SCHEMA, "stage": "score", "scorer_id": scorer_id,
            "sides": {k: {kk: vv for kk, vv in v.items() if kk != "per_sample"} for k, v in scored.items()},
        },
    )
    return scored


# ---------------------------------------------------------------------------
# Supply-variant first Solver visit (VAR-2). Grouped Solver remains the default.
# ---------------------------------------------------------------------------

SUPPLY_RENDER_SCHEMA = "saea-stage3-supply-variant-first-visit-v1"


def _immutable_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> str:
    raw = ("\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
           + "\n").encode("utf-8")
    if path.exists():
        if path.read_bytes() != raw:
            raise Stage3ScoreError(f"existing derived copy differs from sealed source: {path}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("xb") as stream:
                stream.write(raw)
        except FileExistsError as error:
            raise Stage3ScoreError(f"derived copy appeared concurrently: {path}") from error
    return hashlib.sha256(raw).hexdigest()


def _immutable_json(path: Path, payload: Mapping[str, Any]) -> str:
    raw = (json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n").encode("utf-8")
    if path.exists():
        if path.read_bytes() != raw:
            raise Stage3ScoreError(f"existing derived metadata differs from sealed source: {path}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("xb") as stream:
                stream.write(raw)
        except FileExistsError as error:
            raise Stage3ScoreError(f"derived metadata appeared concurrently: {path}") from error
    return hashlib.sha256(raw).hexdigest()


def render_supply_variant_first_visit(
    bundle, group, roster: Mapping[str, str], out_dir: Path,
    *, run_id: str, attempt_id: str, roster_sha256: str, config_hash: str,
) -> dict[str, Any]:
    """Render all declared arms from FIRST Solver contacts, with no row filtering.

    A bundle-verified terminal abstention with no Solver visit is an explicit
    canonical-empty fallback in every column. A partial arm group is invalid.
    Revision visits are counted separately and never enter these copies.
    """
    from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
        validate_native_episode_delivery_receipt, validate_supply_variant_receipt,
    )
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import parse_slu_response

    if (bundle.manifest.get("status") != "COMPLETED"
            or bundle.attempt_state != "FINALIZED"
            or bundle.manifest.get("run_id") != run_id
            or bundle.manifest_path.parent.name != attempt_id):
        raise Stage3ScoreError("source bundle is not the requested finalized complete attempt")
    ids = sorted(roster)
    if set(ids) != set(bundle.split_ids) or len(ids) != len(bundle.outputs_rows):
        raise Stage3ScoreError("roster differs from complete bundle split")
    rows = {row.get("sample_id"): row for row in bundle.outputs_rows}
    if set(rows) != set(ids):
        raise Stage3ScoreError("bundle outputs have missing, extra, or duplicate roster rows")
    if bundle.manifest.get("config", {}).get("config_hash") != config_hash:
        raise Stage3ScoreError("composed config hash differs from sealed manifest")
    arms = tuple(group.arms)
    if not arms or not arms[-1].deliver:
        raise Stage3ScoreError("declared supply arms lack a final delivering arm")
    names = tuple(arm.arm_id for arm in arms)
    if any(not isinstance(name, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name) is None
           for name in names):
        raise Stage3ScoreError("supply arm IDs must be safe single path segments")
    columns = {name: [] for name in names}
    row_meta = []
    malformed = {name: 0 for name in names}
    absent = 0
    revisions = 0
    for sid in ids:
        row = rows[sid]
        episode = row.get("native_episode_receipt")
        if not isinstance(episode, Mapping):
            raise Stage3ScoreError(f"{sid}: no sealed native episode")
        visits = episode.get("role_visits")
        delivery = validate_native_episode_delivery_receipt(
            episode, error_type=Stage3ScoreError
        )
        solver = [visit for visit in visits if isinstance(visit, Mapping)
                  and visit.get("stage") == "solver"]
        revisions += max(0, len(solver) - 1)
        if not solver:
            if delivery.kind not in {"abstention", "context-abstention"} or (
                row.get("supply_variants") is not None
            ):
                raise Stage3ScoreError(f"{sid}: missing Solver visit is not a declared terminal fallback")
            absent += 1
            for name in names:
                columns[name].append({"sample_id": sid, "text": EMPTY_ANSWER})
            row_meta.append({"sample_id": sid, "availability": "no_solver_visit",
                             "fallback": "canonical_empty", "later_solver_visits": 0})
            continue
        final = row.get("supply_variants")
        if not isinstance(final, Mapping):
            raise Stage3ScoreError(f"{sid}: Solver visit has no final supply-variant custody")
        validate_supply_variant_receipt(
            final, arm_ids=names, delivered_arm_id=names[-1],
            phase_id=solver[-1].get("role_id"), error_type=Stage3ScoreError,
        )
        if final["fit_estimate"] != group.fit_estimate.as_json():
            raise Stage3ScoreError(f"{sid}: sealed fit estimate differs from declaration")
        for i, arm in enumerate(arms):
            sealed = final["arms"][i]
            declared = [{"path": k.path, "value": k.value} for k in arm.knobs]
            if sealed["resolved_knobs"] != sorted(declared, key=lambda x: x["path"]):
                raise Stage3ScoreError(f"{sid}: arm resolved knobs differ from declaration")
            if sealed["max_supplied_items"] != arm.max_supplied_items:
                raise Stage3ScoreError(f"{sid}: arm supplied-item bound differs from declaration")
        first = solver[0].get("execution_receipt")
        contacts = first.get("contacts") if isinstance(first, Mapping) else None
        if not isinstance(contacts, list) or len(contacts) != len(arms):
            raise Stage3ScoreError(f"{sid}: first Solver visit lacks a complete arm group")
        arm_meta = []
        for i, arm in enumerate(arms):
            contact = contacts[i]
            if not isinstance(contact, Mapping):
                raise Stage3ScoreError(f"{sid}: first Solver arm contact is malformed")
            request_id = contact.get("request_id")
            response = bundle.trace_records.get(f"{request_id}/response")
            request = bundle.trace_records.get(f"{request_id}/request")
            if not isinstance(response, Mapping) or not isinstance(request, Mapping):
                raise Stage3ScoreError(f"{sid}: first Solver arm trace pair is absent")
            raw = response.get("text")
            if (not isinstance(raw, str)
                    or request.get("payload_sha256") != contact.get("request_sha256")
                    or hashlib.sha256(raw.encode("utf-8")).hexdigest()
                    != contact.get("response_text_sha256")
                    or response.get("response_text_sha256") != contact.get("response_text_sha256")):
                raise Stage3ScoreError(f"{sid}: first Solver arm trace hash differs from custody")
            scenario, action, entities, ok = parse_slu_response(raw)
            parsed = ({"scenario": scenario or "", "action": action or "",
                       "entities": [{"type": x.type, "filler": x.filler} for x in entities]}
                      if ok else None)
            if not ok:
                malformed[arm.arm_id] += 1
            columns[arm.arm_id].append({"sample_id": sid, "text": render_answer(parsed)})
            arm_meta.append({
                "arm_id": arm.arm_id, "contact_id": contact.get("agent_contact_id"),
                "request_sha256": contact.get("request_sha256"),
                "response_text_sha256": contact.get("response_text_sha256"),
                "parse_status": "ok" if ok else "malformed",
                "fallback": None if ok else "canonical_empty",
            })
        row_meta.append({"sample_id": sid, "availability": "first_solver_visit",
                         "later_solver_visits": len(solver) - 1, "arms": arm_meta})
    source = {
        "run_id": run_id, "attempt_id": attempt_id,
        "manifest_path": str(bundle.manifest_path),
        "manifest_sha256": sha256_file(bundle.manifest_path),
        "outputs_sha256": bundle.manifest["outputs"]["sha256"],
        "raw_trace_sha256": bundle.manifest["raw_trace"]["sha256"],
        "sealed_scores_sha256": bundle.manifest["scores"]["sha256"],
        "config_hash": config_hash, "roster_sha256": roster_sha256,
    }
    manifest = {
        "schema": SUPPLY_RENDER_SCHEMA, "stage": "render", "source": source,
        "rows": len(ids), "arm_order": list(names),
        "arm_declarations": [
            {"arm_id": arm.arm_id, "deliver": arm.deliver,
             "resolved_knobs": [{"path": k.path, "value": k.value} for k in arm.knobs],
             "max_supplied_items": arm.max_supplied_items}
            for arm in arms
        ],
        "no_solver_visit_rows": absent, "malformed_first_visit_by_arm": malformed,
        "later_solver_visit_count": revisions,
        "meaning": "first Solver visit local arm outputs; not full-system returns",
        "arm_order_source": "declared native Solver supply_variants order; runtime invokes arms in this order",
        "copies": {},
    }
    for name in names:
        path = out_dir / f"arm-{name}-first-visit-outputs.jsonl"
        digest = _immutable_jsonl(path, columns[name])
        manifest["copies"][name] = {"path": str(path), "sha256": digest, "rows": len(ids)}
    _immutable_json(out_dir / "first-visit-rows.json", {
        "schema": SUPPLY_RENDER_SCHEMA, "source": source, "rows": row_meta,
        "note": "later visits are counted only, never mixed into first-visit columns",
    })
    _immutable_json(out_dir / "render-manifest.json", manifest)
    return manifest


def score_supply_variant_copies(
    scorer_id: str, manifest: Mapping[str, Any], out_dir: Path,
    lock: Mapping[str, object], data_root: Path, delivered: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Use score_copy once per whole-roster first-visit arm, then cache summary."""
    from speech_aware_evidence_acquisition.core.scoring_batch import (
        score_complete_derived_copy,
    )

    if manifest.get("schema") != SUPPLY_RENDER_SCHEMA:
        raise Stage3ScoreError("supply-variant score requires a first-visit render manifest")
    ids = None
    sides = {}
    for arm in manifest["arm_order"]:
        entry = manifest["copies"].get(arm)
        if not isinstance(entry, Mapping):
            raise Stage3ScoreError(f"missing rendered copy for arm {arm}")
        path = Path(entry["path"])
        if sha256_file(path) != entry["sha256"]:
            raise Stage3ScoreError(f"rendered copy hash mismatch for arm {arm}")
        copy_rows = list(iter_jsonl(path))
        current = {row.get("sample_id") for row in copy_rows}
        if len(copy_rows) != manifest["rows"] or len(current) != len(copy_rows):
            raise Stage3ScoreError(f"rendered copy has partial identities for arm {arm}")
        if ids is None:
            ids = current
        elif ids != current:
            raise Stage3ScoreError("arm copies do not share one complete roster")
        score_path = out_dir / f"arm-{arm}-{scorer_id}-scores.json"
        result = score_complete_derived_copy(
            parent_manifest=Path(manifest["source"]["manifest_path"]),
            outputs_copy=path, expected_copy_sha256=entry["sha256"],
            scorer_id=scorer_id, result_path=score_path, lock=lock,
            data_root=data_root,
            column_binding={
                "arm": arm,
                "arm_declaration": next(
                    row for row in manifest["arm_declarations"] if row["arm_id"] == arm
                ),
                "render_manifest_sha256": sha256_file(out_dir / "render-manifest.json"),
                "roster_sha256": manifest["source"]["roster_sha256"],
                "visit": "first-solver",
            },
        )
        aggregate = result.get("aggregate", {})
        scores = result.get("per_sample")
        if (not isinstance(scores, list) or len(scores) != len(current)
                or {row.get("sample_id") for row in scores} != current
                or not aggregate.get("identity_check", {}).get("passed")):
            raise Stage3ScoreError(f"official scorer returned incomplete arm {arm}")
        sides[arm] = {
            "copy_sha256": entry["sha256"], "scores_sha256": sha256_file(score_path),
            "official": aggregate["official"], "rows": len(scores),
        }
    if set(delivered) != ids:
        raise Stage3ScoreError("sealed delivered scores differ from complete roster")
    summary = {
        "schema": SUPPLY_RENDER_SCHEMA, "stage": "score",
        "source": manifest["source"], "scorer_id": scorer_id,
        "arm_order": manifest["arm_order"], "arms": sides,
        "sealed_delivered_scores_sha256": manifest["source"]["sealed_scores_sha256"],
        "sealed_delivered_rows": len(delivered),
        "meaning": "first Solver visit local branch feedback; not full-system returns",
        "contacts": {"model": 0, "tokenizer": 0, "encoder": 0, "asr": 0,
                     "server": 0, "network": 0, "scorer": len(sides)},
    }
    _immutable_json(out_dir / "score-summary.json", summary)
    return summary


def supply_variant_main(args, repo_root: Path, root: Path, lock) -> int:
    from speech_aware_evidence_acquisition.core.bundle import verify_bundle
    from speech_aware_evidence_acquisition.core.config import compose
    from speech_aware_evidence_acquisition.rails.supply_variants import parse_supply_variants

    if args.stage == "pairs" or args.samples is not None:
        raise Stage3ScoreError("supply-variants mode supports render/score/all, not pairs or samples")
    directory = run_dir(root, args.run, args.attempt)
    bundle = verify_bundle(directory / f"{args.run}.run-manifest.json")
    fragments = bundle.manifest.get("config", {}).get("fragments")
    if not isinstance(fragments, Mapping):
        raise Stage3ScoreError("sealed manifest has no composed fragments")
    composed = compose(repo_root, *(fragments[k] for k in ("model", "dataset", "baseline", "experiment")))
    if composed.config_hash != bundle.manifest["config"]["config_hash"]:
        raise Stage3ScoreError("current fragments differ from sealed composed config")
    native = composed.values.get("native_episode")
    roles = native.get("roles") if isinstance(native, Mapping) else None
    solver = roles.get("solver") if isinstance(roles, Mapping) else None
    perception = roles.get("perception") if isinstance(roles, Mapping) else None
    if not isinstance(solver, Mapping) or not isinstance(perception, Mapping):
        raise Stage3ScoreError("composed config lacks native Solver/Perception roles")
    stores = composed.values.get("knowledge_stores")
    if not isinstance(stores, Mapping):
        raise Stage3ScoreError("composed config lacks declared knowledge stores")
    group = parse_supply_variants(
        solver.get("supply_variants"), phase_id=solver.get("phase_id"),
        first_phase_id=perception.get("phase_id"), declared_stores=tuple(stores),
    )
    roster, roster_sha256, _ = load_roster(repo_root, args.roster)
    out_dir = Path(args.analysis_root)
    if args.stage in ("render", "all"):
        manifest = render_supply_variant_first_visit(
            bundle, group, roster, out_dir, run_id=args.run, attempt_id=args.attempt,
            roster_sha256=roster_sha256, config_hash=composed.config_hash,
        )
    else:
        path = out_dir / "render-manifest.json"
        if not path.is_file():
            raise Stage3ScoreError("supply-variant score requires a prior render")
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if any(not Path(entry["path"]).is_file()
               for entry in manifest.get("copies", {}).values()):
            raise Stage3ScoreError("supply-variant score requires every prior rendered copy")
        # Rebuild from the verified source before trusting cached copies.
        checked = render_supply_variant_first_visit(
            bundle, group, roster, out_dir, run_id=args.run, attempt_id=args.attempt,
            roster_sha256=roster_sha256, config_hash=composed.config_hash,
        )
        if manifest != checked:
            raise Stage3ScoreError("render manifest differs from verified source")
    if args.stage in ("score", "all"):
        delivered = sealed_per_sample(directory, args.run, args.scorer_id)
        summary = score_supply_variant_copies(
            args.scorer_id, manifest, out_dir, lock, root, delivered,
        )
        print(json.dumps({"stage": "score", "arms": list(summary["arms"]),
                          "rows": summary["sealed_delivered_rows"]}))
    else:
        print(json.dumps({"stage": "render", "arms": manifest["arm_order"],
                          "rows": manifest["rows"]}))
    return 0


# ---------------------------------------------------------------------------
# pairs
# ---------------------------------------------------------------------------


def best_worst(samples_correct: Sequence[dict[str, Any]]) -> tuple[int, int]:
    """Best/worst sample index by ``(slu_f1_f1, scenario_action_exact)``,
    ties broken by ascending ``sample_index`` (module docstring)."""

    def key(entry: tuple[int, dict[str, Any]]) -> tuple[float, bool]:
        _, scores = entry
        return (scores["slu_f1_f1"], scores["scenario_action_exact"])

    indexed = list(enumerate(samples_correct))
    best_index, _ = max(indexed, key=lambda e: (key(e), -e[0]))
    worst_index, _ = min(indexed, key=lambda e: (key(e), e[0]))
    return best_index, worst_index


def pairs(
    run_id: str, attempt_id: str, scorer_id: str, roster: Mapping[str, str],
    roster_relpath: str, roster_sha256: str, roster_split_identity_hash: str,
    scored: Mapping[str, Any], delivered: Mapping[str, Mapping[str, Any]], samples: int,
    out_dir: Path, stage3_algorithm: Mapping[str, Any] | None = None,
    sealed_rows: Mapping[str, Mapping[str, Any]] | None = None,
    trace: Mapping[str, Mapping[str, Any]] | None = None,
    gold_intents: Mapping[str, str] | None = None,
    gold_source: str = "unavailable",
    trace_relpath: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    sealed_rows = sealed_rows or {}
    trace = trace or {}
    gold_intents = gold_intents or {}
    ids = sorted(roster)
    rows: list[dict[str, Any]] = []
    for sample_id in ids:
        per_sample = [scored[f"sample_{index}"]["per_sample"][sample_id] for index in range(samples)]
        best_index, worst_index = best_worst(per_sample)
        best_f1 = per_sample[best_index]["slu_f1_f1"]
        worst_f1 = per_sample[worst_index]["slu_f1_f1"]
        delivered_scores = correctness_fields(delivered[sample_id]) if sample_id in delivered else None
        rows.append({
            "sample_id": sample_id,
            "stratum": roster[sample_id],
            "samples": [
                {"sample_index": index, **per_sample[index]} for index in range(samples)
            ],
            "best_index": best_index,
            "worst_index": worst_index,
            "best_slu_f1_f1": best_f1,
            "worst_slu_f1_f1": worst_f1,
            "disagreement": best_f1 - worst_f1,
            "group_mean_slu_f1_f1": sum(s["slu_f1_f1"] for s in per_sample) / samples,
            "delivered": delivered_scores,
        })

    disagreeing = [row for row in rows if row["disagreement"] > 0]
    strata = sorted({row["stratum"] for row in rows})
    coverage: dict[str, Any] = {}
    for stratum in strata:
        stratum_rows = [row for row in rows if row["stratum"] == stratum]
        stratum_disagreeing = [row for row in stratum_rows if row["disagreement"] > 0]
        coverage[stratum] = {
            "rows": len(stratum_rows),
            "disagreeing_rows": len(stratum_disagreeing),
            "disagreement_rate": len(stratum_disagreeing) / len(stratum_rows) if stratum_rows else None,
            "mean_disagreement": (
                sum(row["disagreement"] for row in stratum_rows) / len(stratum_rows)
                if stratum_rows else None
            ),
        }

    # -- S3-4s: one trajectory block per DISAGREEING row -----------------
    trajectories: dict[str, dict[str, Any]] = {}
    for row in disagreeing:
        sample_id = row["sample_id"]
        sealed = sealed_rows.get(sample_id) or {}
        trajectories[sample_id] = build_trajectory(
            sealed.get("row") or {},
            best_index=row["best_index"],
            worst_index=row["worst_index"],
            rendered=sealed.get("rendered") or {},
            trace=trace,
            gold_intent=gold_intents.get(sample_id),
            delivered_f1=(
                None if row["delivered"] is None else row["delivered"]["slu_f1_f1"]
            ),
            best_f1=row["best_slu_f1_f1"],
        )
    trajectory_summary = {
        "rows": len(trajectories),
        "with_episode_receipt": sum(
            1 for block in trajectories.values() if block.get("available")
        ),
        "with_candidate_list": sum(
            1 for block in trajectories.values()
            if block.get("perception", {}).get("candidate_count")
        ),
        "gold_intent_source": gold_source,
        "gold_intent_known_rows": sum(
            1 for block in trajectories.values()
            if block.get("perception", {}).get("gold_intent_known")
        ),
        "gold_intent_in_candidates_rows": sum(
            1 for block in trajectories.values()
            if block.get("perception", {}).get("gold_intent_in_candidates")
        ),
        "delivered_below_best_rows": sum(
            1 for block in trajectories.values()
            if block.get("delivered", {}).get("delivered_below_best")
        ),
        "rows_with_a_truncated_node": sum(
            1 for block in trajectories.values() if block.get("truncated_stages")
        ),
        "trace": trace_relpath,
        "trace_requests": len(trace),
    }

    header = {
        "schema": SCHEMA, "stage": "pairs", "run_id": run_id, "attempt_id": attempt_id,
        "scorer_id": scorer_id, "samples": samples,
        "roster": {
            "relpath": roster_relpath, "sha256": roster_sha256,
            "split_identity_hash": roster_split_identity_hash, "rows": len(ids),
        },
        "contacts": {"model": 0, "tokenizer": 0, "encoder": 0, "asr": 0, "server": 0,
                     "network": 0, "scorer": samples},
    }
    # Owner decision 101: a Stage-3 read says which training-free RL it reads.
    if stage3_algorithm is not None:
        header["stage3_algorithm"] = dict(stage3_algorithm)
    per_row_payload = {**header, "rows": rows}
    pairs_payload = {
        **header,
        # S3-4s: the payload version, beside (never in place of) ``schema``.
        "pairs_schema": PAIRS_SCHEMA,
        "count": len(disagreeing),
        "pairs": [
            {
                "sample_id": row["sample_id"], "stratum": row["stratum"],
                "best_index": row["best_index"], "worst_index": row["worst_index"],
                "disagreement": row["disagreement"],
                "trajectory": trajectories[row["sample_id"]],
            }
            for row in disagreeing
        ],
        # The loader-shaped view ``rails.stage3_advantage.load_advantage_pairs``
        # reads: EXACTLY ``{sample_id, best, worst}`` per row, best/worst
        # carrying the sample index and the rendered answer's own sha256.
        # Written here so the ADV-1 material loader can bind this file
        # directly instead of a hand-made copy of it; the ``pairs`` array
        # above is unchanged and stays the file's own record.
        "rows": [
            {
                "sample_id": row["sample_id"],
                "best": {
                    "sample_index": row["best_index"],
                    "response_text_sha256": trajectories[row["sample_id"]]["best"][
                        "answer_sha256"
                    ],
                },
                "worst": {
                    "sample_index": row["worst_index"],
                    "response_text_sha256": trajectories[row["sample_id"]]["worst"][
                        "answer_sha256"
                    ],
                },
            }
            for row in disagreeing
        ],
        "trajectory_summary": trajectory_summary,
        "coverage_by_stratum": coverage,
    }
    write_json(out_dir / "per_row.json", per_row_payload)
    write_json(out_dir / "pairs.json", pairs_payload)
    return per_row_payload, pairs_payload


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("grouped", "supply-variants"), default="grouped")
    parser.add_argument("--run", required=True, help="sealed run id")
    parser.add_argument("--attempt", required=True, help="sealed attempt id")
    parser.add_argument("--roster", required=True, help="roster receipt relpath (repo-root relative)")
    parser.add_argument("--analysis-root", required=True, help="output directory for this read")
    parser.add_argument("--scorer-id", default=DEFAULT_SCORER_ID, help="registered scorer id")
    parser.add_argument("--samples", type=int, default=None, help="override sample count (auto-detected)")
    parser.add_argument(
        "--stage", choices=("render", "score", "pairs", "all"), default="all"
    )
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--data-root", default=None, help="defaults to data.lock.data_root()")
    parser.add_argument(
        "--trace", default=None,
        help=(
            "the sealed attempt's own <run_id>.trace.jsonl, joined by request id for "
            "per-contact completion tokens, finish reasons and the Perception "
            "response (S3-4s). The default is that file inside the attempt "
            "directory when it exists; 'none' disables the join and the trajectory "
            "block says so."
        ),
    )
    parser.add_argument(
        "--gold-intents", default=None,
        help=(
            "optional JSON object {sample_id: '<scenario>_<action>'} over the "
            "CONSTRUCTION roster. Read only to answer whether the gold intent was "
            "among the Perception candidates; it enters pairs.json as a boolean and "
            "a count, never as a label."
        ),
    )
    parser.add_argument(
        "--stage3-algorithm", default=None,
        help=(
            "registered Stage-3 algorithm id (core.base.STAGE3_ALGORITHMS); the default "
            "resolves the label from the experiment fragment that owns --run"
        ),
    )
    from speech_aware_evidence_acquisition.analysis.parallel import (  # noqa: PLC0415
        add_workers_argument,
    )

    add_workers_argument(
        parser,
        help_suffix=(
            "Here a unit is ONE complete official scoring of ONE rendered copy; "
            "no scoring is ever sharded."
        ),
    )
    args = parser.parse_args(argv)

    from speech_aware_evidence_acquisition.core.stage3_algorithms import (  # noqa: PLC0415
        summary_for_run_id,
    )
    from speech_aware_evidence_acquisition.data.lock import (  # noqa: PLC0415
        data_root as resolve_data_root, load_lock, umbrella_lock_path,
    )

    repo_root = Path(args.repo_root)
    stage3_algorithm = summary_for_run_id(repo_root, args.run, args.stage3_algorithm)
    root = Path(args.data_root) if args.data_root else resolve_data_root()
    lock = load_lock(umbrella_lock_path(repo_root))
    directory = run_dir(root, args.run, args.attempt)
    roster, roster_sha256, roster_split_identity_hash = load_roster(repo_root, args.roster)
    if args.mode == "supply-variants":
        return supply_variant_main(args, repo_root, root, lock)
    out_dir = Path(args.analysis_root)
    out_dir.mkdir(parents=True, exist_ok=True)

    samples = args.samples or detect_samples(directory, args.run)
    needs_pairs = args.stage in ("pairs", "all")

    manifest = None
    if args.stage in ("render", "all"):
        manifest = render(directory, args.run, roster, samples, out_dir)
        print(json.dumps({"stage": "render", "rows": manifest["rows"],
                           "malformed_samples": manifest["malformed_samples"]}, indent=2))
    else:
        manifest_path = out_dir / "render-manifest.json"
        if not manifest_path.is_file():
            raise Stage3ScoreError(f"--stage {args.stage} requires a prior render (no {manifest_path})")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    scored = None
    if args.stage in ("score", "all"):
        scored = score(args.scorer_id, manifest, out_dir, lock, root, workers=args.workers)
        print(json.dumps(
            {"stage": "score", "sides": {k: v["official_slu_f1_pp"] for k, v in scored.items()}},
            indent=2,
        ))
    elif args.stage == "pairs":
        scored = {}
        for name in manifest["copies"]:
            result_path = out_dir / f"{name}-{args.scorer_id}-scores.json"
            if not result_path.is_file():
                raise Stage3ScoreError(f"--stage {args.stage} requires a prior score (no {result_path})")
            result = json.loads(result_path.read_text(encoding="utf-8"))[args.scorer_id]
            scored[name] = {
                "outputs_sha256": manifest["copies"][name]["sha256"],
                "official_slu_f1_pp": 100 * float(result["aggregate"]["official"]["slu_f1"]),
                "official_intent_pp": 100 * float(result["aggregate"]["official"]["intent_accuracy"]),
                "per_sample": {str(r["sample_id"]): correctness_fields(r) for r in result["per_sample"]},
                "scoring_seconds": 0.0,
            }

    if needs_pairs:
        # S3-4s: the trajectory inputs. All three are OPTIONAL and all three
        # are reported absent rather than guessed.
        trace_facts: dict[str, dict[str, Any]] = {}
        trace_relpath = None
        if args.trace != "none":
            trace_path = (
                Path(args.trace) if args.trace
                else directory / f"{args.run}.trace.jsonl"
            )
            if trace_path.is_file():
                trace_facts = scan_trace(trace_path)
                trace_relpath = str(trace_path)
            elif args.trace:
                raise Stage3ScoreError(f"no sealed trace at {trace_path}")
        gold_intents, gold_source = load_gold_intents(
            repo_root / args.roster,
            Path(args.gold_intents) if args.gold_intents else None,
        )
        sealed_rows = load_sealed_rows(directory, args.run, roster, samples)
        try:
            delivered = sealed_per_sample(directory, args.run, args.scorer_id)
        except Stage3ScoreError as error:
            # The delivered score is auxiliary (module docstring): a sealed
            # run scored online under a DIFFERENT scorer id (e.g. a
            # grouped-solver precedent flown before the v3-projection
            # convention existed) still yields a complete best/worst read
            # from the five samples alone.
            print(f"[pairs] no sealed delivered score for {args.scorer_id!r}: {error}")
            delivered = {}
        _, pairs_payload = pairs(
            args.run, args.attempt, args.scorer_id, roster, args.roster, roster_sha256,
            roster_split_identity_hash, scored, delivered, samples, out_dir,
            stage3_algorithm,
            sealed_rows=sealed_rows,
            trace=trace_facts,
            gold_intents=gold_intents,
            gold_source=gold_source,
            trace_relpath=trace_relpath,
        )
        print(json.dumps(
            {
                "stage": "pairs",
                "pairs_schema": pairs_payload["pairs_schema"],
                "pair_count": pairs_payload["count"],
                "stage3_algorithm": pairs_payload.get("stage3_algorithm"),
                "trajectory_summary": pairs_payload["trajectory_summary"],
                "coverage_by_stratum": pairs_payload["coverage_by_stratum"],
            },
            indent=2, sort_keys=True,
        ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
