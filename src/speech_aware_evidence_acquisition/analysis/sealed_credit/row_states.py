"""Row-state extraction for every sealed-credit pool kind (design spec task 2).

The design spec's own inventory (section 1c) records that the pre-existing node-gain
ledger's ``derive_arm`` is "two-arm, single-sample, Fold A only" and does not
generalise. This module is the NEW, general extractor the spec calls for, built on
top of the primitives ``analysis.sealed_credit.entity_states`` lifted out of the
ledger and the error-source script (``note_state``, ``gold_item_states``,
``entity_items``, and their own transitive closure), plus a fresh phases/scores/
outputs reader that tolerates any number of Solver samples per row (1 for a
single-sample arm, N for a grouped-multi-sample rollout) instead of assuming
exactly one first-plus-revised pair.

Two pool kinds (``analysis.sealed_credit.pools.POOL_KINDS``):

* ``single-sample-arm`` -- one Solver sample, optionally revised by the Reviewer/
  Planner, then the deliver normaliser: AGREE, wave A/A, W1, W3a, W4, every VAR-1
  family pool. ``s1``/``s_last`` are the first and last Solver state; ``revised``,
  ``reviewer_visited`` and ``normaliser_changed`` are meaningful.
* ``grouped-multi-sample`` -- N independent Solver samples (ROLL-1, ROLL-2; N =
  ``samples_per_row``), no Reviewer/Planner and no deliver-normaliser node (the
  design spec section 2b: "For grouped pools S1 becomes five samples plus the
  commit, and the normaliser node is absent"). The already-sealed delivered
  answer and official score already reflect whichever commit rule produced it;
  this module does not re-derive the commit (decision 179: commit-rule tuning
  is excluded from run 1's policy space).

Deliberately NOT reproduced here: the ledger's exemplar-vote (K-node) diagnostic.
No knob in the design spec's own policy-space table (section 2c) needs a
per-exemplar vote breakdown as its conversion source (``rank_weights.w_agree``'s
source is an AGGREGATE AGREE-vs-PLAN comparison, not the K-node vote), so this
extractor reports the B (boundary)/P (perception)/S (solver)/R (reviewer)/N
(normaliser)/D (delivered) node states the run's own knobs actually consume and
omits K -- a deliberate, documented scope reduction, not an oversight.

Gold discipline: gold reaches this module only as already-loaded ``SlurpRecord``
data (the governed ``data.slurp.load_slurp_split`` loader, called by the CLI, never
here); this module compares gold and predicted entities in-process and returns only
indices, booleans, counts and class names -- never filler text.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from speech_aware_evidence_acquisition.analysis.sealed_credit.entity_states import (
    canonical,
    gold_item_states,
    note_state,
)

IB_PREFIX = "intent-boundaries::intent-boundary:"


class RowStatesError(RuntimeError):
    """A sealed artefact could not be read or does not carry the expected shape."""


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _rank_bucket(rank: int | None) -> str:
    if rank is None:
        return "absent"
    if rank == 1:
        return "1"
    if rank == 2:
        return "2"
    return "3+"


# ---------------------------------------------------------------------------
# sealed artefact readers (generic: any run id, any scorer key, any solver count)


def load_scores(directory: Path, run_id: str, scorer: str) -> dict[str, Any]:
    """Per-sample official counts from ``<run_id>.scores.json[scorer]``.

    Fields kept per row: ``scenario_action_exact`` (bool), the official per-sample
    ``slu_f1_f1`` (already the scorer's own word+char-distance F1 for that row --
    used, mean-over-rows, as this module's SLU-F1 proxy; NOTE this is the mean of
    a PER-ROW F1, not the pooled/micro aggregate the paper-facing number is, and
    every caller that reports it says so), and the pooled SLU-F1 ingredient counts
    (``tp``/``fp``/``fn``, word+char summed -- the same convention
    ``slurp_agree_arm_error_sources.slu_counts`` uses), all read directly off the
    sealed official scorer's own per-sample record rather than re-scored: the
    sealed count IS the number the paper-facing metric used.
    """

    path = directory / f"{run_id}.scores.json"
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RowStatesError(f"{run_id}: cannot read {path}: {error}") from error
    if scorer not in document:
        raise RowStatesError(f"{run_id}: scorer {scorer!r} not in {path} (has {sorted(document)})")
    block = document[scorer]
    rows = {}
    for sample in block["per_sample"]:
        rows[str(sample["sample_id"])] = {
            "scenario_action_exact": bool(sample["scenario_action_exact"]),
            "slu_f1_f1": float(sample.get("slu_f1_f1", 0.0)),
            "tp": float(sample["slu_f1_word_tp"]) + float(sample["slu_f1_char_tp"]),
            "fp": float(sample["slu_f1_word_fp"]) + float(sample["slu_f1_char_fp"]),
            "fn": float(sample["slu_f1_word_fn"]) + float(sample["slu_f1_char_fn"]),
        }
    return {"rows": rows, "sha256": _digest(path), "relpath": path.name}


def load_outputs(directory: Path, run_id: str) -> dict[str, Any]:
    """Per-sample delivered answer from ``<run_id>.outputs.jsonl``."""

    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (
        SlotEntity,
        parse_slu_response,
    )

    path = directory / f"{run_id}.outputs.jsonl"
    rows: dict[str, Any] = {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                record = json.loads(line)
                scenario, action, entities, parsed = parse_slu_response(record.get("text") or "")
                rows[str(record["sample_id"])] = {
                    "parsed": bool(parsed),
                    "intent": (
                        f"{scenario}_{action}"
                        if parsed and scenario is not None and action is not None
                        else None
                    ),
                    "entities": tuple(SlotEntity(e.type, e.filler) for e in entities),
                }
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RowStatesError(f"{run_id}: cannot read {path}: {error}") from error
    return {"rows": rows, "sha256": _digest(path), "relpath": path.name}


def load_phases(directory: Path, run_id: str) -> dict[str, Any]:
    """Per-sample node states from ``<run_id>.phases.json``, tolerant of any number
    of Solver samples per row (single-sample-arm: 1, optionally revised;
    grouped-multi-sample: N independent samples, no Reviewer/Planner)."""

    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (
        SlotEntity,
        parse_slu_response,
    )

    path = directory / f"{run_id}.phases.json"
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RowStatesError(f"{run_id}: cannot read {path}: {error}") from error
    if document.get("schema") != "saea-flight-phase-summaries-v1" or len(document.get("phases", [])) != 1:
        raise RowStatesError(f"{run_id}: unexpected phase artefact shape at {path}")

    def parse_answer(text: str) -> dict[str, Any]:
        scenario, action, entities, parsed = parse_slu_response(text or "")
        return {
            "parsed": bool(parsed),
            "intent": f"{scenario}_{action}" if parsed and scenario is not None and action is not None else None,
            "entities": tuple(SlotEntity(e.type, e.filler) for e in entities),
        }

    rows: dict[str, Any] = {}
    for result in document["phases"][0]["results"]:
        sample_id = str(result["sample_id"])
        boundary = [
            v.split(IB_PREFIX, 1)[-1]
            for v in result.get("initial_query_state", {}).get("retrieved_value_ids", [])
            if isinstance(v, str) and v.startswith(IB_PREFIX)
        ]
        perc_ids: list[str] = []
        perc_tokens: list[str] = []
        solvers: list[dict[str, Any]] = []
        kinds: list[str] = []
        perception_seen = False
        for state in result.get("agent_states") or ():
            kind = state.get("state_kind")
            kinds.append(kind)
            if kind == "phase:perception" and not perception_seen:
                perception_seen = True
                try:
                    payload = json.loads(state.get("content") or "")
                except (ValueError, TypeError):
                    payload = {}
                parts: list[str] = []
                for cand in payload.get("candidates") or ():
                    perc_ids.append(str(cand.get("intent_id")))
                    parts.append(str(cand.get("distinction") or ""))
                    parts.extend(str(u) for u in cand.get("unresolved_fields") or ())
                perc_tokens = canonical(" ".join(parts)).split()
            elif kind == "phase:solver":
                solvers.append(parse_answer(state.get("content") or ""))
        receipt = result.get("native_episode_receipt") or {}
        routes = [r.get("action") for r in receipt.get("planner_routes") or ()]
        normaliser = receipt.get("deliver_normaliser") or {}
        rows[sample_id] = {
            "boundary": boundary,
            "perc_ids": perc_ids,
            "perc_tokens": perc_tokens,
            "solvers": solvers,
            "reviewer_visited": "phase:reviewer" in kinds,
            "routes": routes,
            "normaliser_changed": bool(normaliser.get("changed")),
        }
    return {"rows": rows, "sha256": _digest(path), "relpath": path.name}


# ---------------------------------------------------------------------------
# row-state / item-state derivation


def derive_rows(
    pool_kind: str,
    gold_by_sid: Mapping[str, Any],
    phases_rows: Mapping[str, Any],
    scores_rows: Mapping[str, Any],
    outputs_rows: Mapping[str, Any],
    ids: list[str],
) -> dict[str, Any]:
    """Per-row node states and per-gold-item entity classes, for either pool kind.

    ``gold_by_sid[sid]`` must carry ``.intent`` and ``.entities`` (a
    ``SlurpRecord``-shaped object or an equivalent mapping/namedtuple).
    """

    rows: dict[str, Any] = {}
    items: list[dict[str, Any]] = []
    for sid in ids:
        gold = gold_by_sid[sid]
        gold_intent = gold.intent if hasattr(gold, "intent") else gold["intent"]
        gold_entities = gold.entities if hasattr(gold, "entities") else gold["entities"]
        ph = phases_rows[sid]
        block, perc_ids = ph["boundary"], ph["perc_ids"]
        solvers = ph["solvers"]
        s1 = solvers[0] if solvers else {"parsed": False, "intent": None, "entities": ()}
        s_last = solvers[-1] if solvers else s1
        out = outputs_rows[sid]
        score = scores_rows[sid]
        perc_rank = perc_ids.index(gold_intent) + 1 if gold_intent in perc_ids else None
        revised = pool_kind == "single-sample-arm" and len(solvers) > 1
        row = {
            "block_n": len(block),
            "block_pos": block.index(gold_intent) + 1 if gold_intent in block else None,
            "perc_n": len(perc_ids),
            "perc_rank": perc_rank,
            "perc_rank_bucket": _rank_bucket(perc_rank),
            "s1_ok": s1["intent"] == gold_intent,
            "s1_intent_in_perc": s1["intent"] in perc_ids,
            "s_last_ok": s_last["intent"] == gold_intent,
            "revised": revised,
            "reviewer_visited": bool(ph["reviewer_visited"]) if pool_kind == "single-sample-arm" else False,
            "normaliser_changed": (
                bool(ph["normaliser_changed"]) if pool_kind == "single-sample-arm" else None
            ),
            "d_ok": bool(score["scenario_action_exact"]),
            "d_parsed": bool(out["parsed"]),
            "d_slu_f1": float(score["slu_f1_f1"]),
            "samples_ok": [s["intent"] == gold_intent for s in solvers] or [s1["intent"] == gold_intent],
            "samples_n": max(len(solvers), 1),
        }
        rows[sid] = row
        st1, _ = gold_item_states(gold_entities, s1["entities"]) if solvers else ((None,) * len(gold_entities), [])
        std, _ = gold_item_states(gold_entities, out["entities"])
        tokens = ph["perc_tokens"]
        for index, entity in enumerate(gold_entities):
            items.append({
                "sample_id": sid,
                "gold_index": index,
                "type": entity.type,
                "note": note_state(entity.filler, tokens) if tokens else "ABSENT",
                "s1": st1[index] if solvers else None,
                "d": std[index],
            })
    return {"rows": rows, "items": items}


def extract_pool(
    pool: Mapping[str, Any],
    data_root: Path,
    gold_by_sid: Mapping[str, Any],
    attempt_dir: Path,
    phases_dir: Path | None = None,
) -> dict[str, Any]:
    """Load and derive one pool's full row/item state. ``attempt_dir`` is the sealed
    attempt directory carrying ``<run_id>.{phases.json,scores.json,outputs.jsonl}``
    (``analysis.sealed_credit.pools.attempt_dir``). ``phases_dir`` (run 2) reads the
    phases file from a different attempt of the same run: a seal-only completion keeps
    every row of its predecessor but seals no ``phases.json`` of its own, so its node
    states come from the predecessor attempt (the pool's ``phases_attempt``)."""

    run_id = pool["run_id"]
    phases = load_phases(phases_dir if phases_dir is not None else attempt_dir, run_id)
    scores = load_scores(attempt_dir, run_id, pool["scorer"])
    outputs = load_outputs(attempt_dir, run_id)
    ids = sorted(set(phases["rows"]) & set(scores["rows"]) & set(outputs["rows"]) & set(gold_by_sid))
    missing = (set(phases["rows"]) | set(scores["rows"]) | set(outputs["rows"])) - set(ids)
    derived = derive_rows(pool["kind"], gold_by_sid, phases["rows"], scores["rows"], outputs["rows"], ids)
    return {
        "label": pool["label"],
        "run_id": run_id,
        "kind": pool["kind"],
        "roster": pool["roster"],
        "use": pool["use"],
        "rows": derived["rows"],
        "items": derived["items"],
        "row_count": len(ids),
        "rows_missing_from_some_artefact": len(missing),
        "provenance": {
            "phases": [phases["relpath"], phases["sha256"]],
            "scores": [scores["relpath"], scores["sha256"]],
            "outputs": [outputs["relpath"], outputs["sha256"]],
        },
    }


__all__ = [
    "RowStatesError", "load_scores", "load_outputs", "load_phases",
    "derive_rows", "extract_pool",
]
