#!/usr/bin/env python3
"""Gold position inside the delivered block, and the Solver's freedom over the intent.

A model-free read over sealed bytes.  Zero model, server, tokenizer, encoder,
embedder, scorer, network, GPU and paid-API contacts.  Three questions:

A.  May the Solver deliver an intent outside Perception's k=8 boundary block, and
    does it?  The code answer is a trace of the flown v2.0 plan (in the markdown);
    the empirical answer counts, on the three sealed rosters, the delivered
    intents outside the block and outside Perception's own hypothesis list, and
    how often those are right.
B.  Does the POSITION of the gold entry inside the rendered block predict
    correctness?  Boundary block positions 1-8 are the rendered order the trace
    records; the exemplar block is rendered in value-id order, so both the
    rendered position and the retrieval rank are measured.  The delivered-but-
    wrong rows (86 on TRAIN Fold A) are called out, and the agree-1 reorder of
    the rank diagnostic is replayed offline to see where gold would move.
C.  A contact-free split of the entity residual: for each missed gold entity
    item, does the delivered answer carry a same-type filler that string-matches
    a supplied exemplar's filler, a filler that appears in no supplied body, or
    no filler at all?

Gold discipline.  Gold is read offline on the scoring side only: the sealed
bad-case bank, the sealed ROLL-1 official score file, and the governed TRAIN /
DEVEL splits through ``data.slurp.load_slurp_split``.  No gold value reaches a
query, key, selector or config; this script writes a report and nothing else.

Text discipline.  No utterance text, transcript, delivered answer, gold filler,
predicted filler, candidate distinction or knowledge body is written or printed.
Fillers and bodies are compared inside this process and leave it only as
counts, positions, ids and rates.

Reproducibility.  Deterministic apart from ``generated_at``: every container is
sorted before it is consumed and there is no resampling.
"""

from __future__ import annotations
import os

import argparse
import hashlib
import importlib.util
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.data.lock import load_lock  # noqa: E402
from speech_aware_evidence_acquisition.data.slurp import load_slurp_split  # noqa: E402
from speech_aware_evidence_acquisition.rails.phase_supply import (  # noqa: E402
    load_sealed_segment_vectors,
)
from speech_aware_evidence_acquisition.rails.slurp_projection_v3 import (  # noqa: E402
    apply_slurp_projection_v3_delivery,
)
from speech_aware_evidence_acquisition.reproduction.slurp_official_eval import (  # noqa: E402
    load_legal_intent_inventory,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (  # noqa: E402
    parse_slu_response,
)

READ_ID = "SAEA-SLURP-MF-GOLD-POSITION-SOLVER-FREEDOM-V1"
RECIPE = "slurp-gold-position-and-solver-freedom-read-v1"
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
DEFAULT_MARKDOWN = "docs/results/2026-09-26-slurp-gold-position-and-solver-freedom-read.md"
DEFAULT_ANALYSIS_DIR = "analysis/SLURP-GOLD-POSITION-SOLVER-FREEDOM-V1"
RANK_DIAGNOSTIC = REPO_ROOT / "scripts/analysis/slurp_intent_retrieval_rank_diagnostic.py"
CONV_DERIVATION = REPO_ROOT / "docs/readiness/2026-09-26-slurp-stage3-conv-fold-a-70-v1/roster-derivation-v1.json"
CONV_CLASS = "INTENT-UNCOVERED"  # the bank's name for: intent wrong, gold not on Perception's list

BANK = "analysis/SLURP-PLAN-BAD-CASE-BANK-V1/bank.jsonl"
EX_SNAPSHOT = "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json"
EX_R01_SNAPSHOT = ("knowledge/slurp/saea-kb-distmodel-v1/"
                   "size-pool-annotated-exemplars-minus-r01/snapshot.json")
SC_SNAPSHOT = "knowledge/slurp/semantic/slot-contracts-v2/snapshot.json"
IB_PREFIX = "intent-boundaries::intent-boundary:"
EX_PREFIX = "train-exemplars::value:"
EX_FACET_PREFIX = "train-exemplars::facet:content:"
SC_PREFIX = "slot-contracts::slot-contract:"
FLOWN_K = 8
EX_K = 20
AGREE_WEIGHT = 1.0

ARMS = (
    {"label": "roll1", "title": "ROLL-1 as-flown pool (R01C construction roster, 625 rows)",
     "run_id": "SAEA-SLURP-STAGE3-ROLLOUT-R01-V1",
     "attempt": "attempt-slurp-native-stage3-rollout-r01-generation-v1",
     "roster": None, "split": "train", "exemplars": EX_R01_SNAPSHOT,
     "query": "vectors/slurp-stage3-construction-r01c-v1/query-vectors-speech-segments.jsonl",
     "query_sha": "ebaa743241a67a2cb759353fa8a9f58a3f09d27c00c8c66cb3172958dcccc1b8",
     "scores": ("analysis/SLURP-SAMPLE-AGGREGATION-OFFLINE-READ-V1/"
                "PS-registered-support-3-slurp-slu-official-projected-v3-train-scores.json"),
     "scorer_id": "slurp-slu-official-projected-v3-train"},
    {"label": "train-fold-a-plan", "title": "TRAIN Fold A PLAN (construction roster, 1,080 rows)",
     "run_id": "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1",
     "attempt": "attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1",
     "roster": "train-fold-a", "split": "train", "exemplars": EX_SNAPSHOT,
     "query": "vectors/slurp-intent-boundaries-train-fold-a-1080-v1/query-vectors-speech-segments.jsonl",
     "query_sha": "e7a5b2264dc61fcab3c63d50fb645d4629d3f0a99f83ad5fbe323c73884e5f0b",
     "scores": None, "scorer_id": None},
    {"label": "dev2000-added-plan", "title": "DEV-2000-ADDED PLAN (fresh roster, 1,000 rows)",
     "run_id": "SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1",
     "attempt": "attempt-slurp-native-default-plan-dev2000-added-generation-v1",
     "roster": "dev2000-added", "split": "devel", "exemplars": EX_SNAPSHOT,
     "query": "vectors/slurp-dev2000-added-v1/query-vectors-speech-segments.jsonl",
     "query_sha": "e2a5fd046dac7c87fcf53830955e41e69d20402a2305a02ebf2bfc1a33001b9d",
     "scores": None, "scorer_id": None},
)

ENTITY_CLASSES = ("ENTITY-MIXED", "ENTITY-FN-ONLY")
COUNT_BUCKETS = (("0", 0, 0), ("1-2", 1, 2), ("3-5", 3, 5), ("6-10", 6, 10), ("11-20", 11, 20))
RANK_BUCKETS = (("1", 1, 1), ("2-3", 2, 3), ("4-8", 4, 8), ("9-20", 9, 20))
POS_BUCKETS = (("1-5", 1, 5), ("6-10", 6, 10), ("11-15", 11, 15), ("16-20", 16, 20))
C_KINDS = ("copied-exemplar-filler", "in-supplied-body-text", "not-from-supply",
           "type-swapped", "ignored-available", "ignored-unavailable")

_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\s'-]", re.UNICODE)


class ReadError(RuntimeError):
    pass


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pct(num: float, den: float) -> float:
    return 100.0 * num / den if den else 0.0


def fold(text: str) -> str:
    """Casefold, NFKC, punctuation stripped except apostrophes and hyphens,
    whitespace collapsed -- the bank's own P2r1 rung, applied identically to
    both sides of every comparison so no comparison favours one side."""
    return _WS_RE.sub(" ", _PUNCT_RE.sub(" ", unicodedata.normalize("NFKC", text).casefold())).strip()


def edit_distance(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left or not right:
        return len(left) + len(right)
    previous = list(range(len(right) + 1))
    for i, lchar in enumerate(left, start=1):
        current = [i]
        for j, rchar in enumerate(right, start=1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (lchar != rchar)))
        previous = current
    return previous[-1]


def bucket(value, table):
    for label, low, high in table:
        if low <= value <= high:
            return label
    return "none"


def load_rank_diagnostic():
    spec = importlib.util.spec_from_file_location("slurp_intent_retrieval_rank_diagnostic", RANK_DIAGNOSTIC)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# gold, populations, stores


def load_gold(lock, data_root: Path, split_id: str) -> dict:
    records = load_slurp_split(lock, data_root, split_id, workers=4)
    by_sample, by_utterance = {}, {}
    for record in records:
        entities = tuple((entity.type, entity.filler) for entity in record.entities)
        by_sample[record.sample_id] = {"intent": record.intent, "entities": entities}
        key = str(record.utterance_id)
        key = str(int(key)) if key.isdigit() else key
        by_utterance.setdefault(key, record.intent)
    return {"by_sample": by_sample, "by_utterance": by_utterance, "rows": len(records)}


def load_bank(data_root: Path) -> dict:
    path = data_root / BANK
    rosters: dict[str, dict] = defaultdict(dict)
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        rosters[entry["roster"]][entry["sample_id"]] = {
            "class": {"INTENT-UNCOVERED": "INTENT-WRONG", "INTENT-COVERED": "INTENT-WRONG"}.get(
                entry["plan_class"], entry["plan_class"]),
            "plan_class": entry["plan_class"], "gold_intent": entry["gold_intent"],
            "span_fn": entry["span_fn"], "span_fp": entry["span_fp"],
            "fn_types": sorted(entry["fn_types"])}
    return {"sha256": digest(path), "rosters": {k: dict(sorted(v.items())) for k, v in sorted(rosters.items())}}


def load_population(data_root: Path, arm: dict, bank: dict, gold: dict) -> dict:
    if arm["roster"] is not None:
        return {"rows": dict(bank["rosters"][arm["roster"]]),
                "source": "bad-case bank roster " + arm["roster"], "sha256": bank["sha256"]}
    path = data_root / arm["scores"]
    block = json.loads(path.read_text(encoding="utf-8"))[arm["scorer_id"]]
    rows = {}
    for sample in block["per_sample"]:
        sample_id = str(sample["sample_id"])
        wrong = not bool(sample["scenario_action_exact"])
        fp, fn = float(sample["slot_f1_exact_fp"]), float(sample["slot_f1_exact_fn"])
        klass = ("INTENT-WRONG" if wrong else "ENTITY-MIXED" if fp and fn else "ENTITY-FN-ONLY"
                 if fn else "ENTITY-FP-ONLY" if fp else "CORRECT")
        if not sample.get("parsed", True):
            klass = "MALFORMED"
        rows[sample_id] = {"class": klass, "plan_class": klass,
                           "gold_intent": gold["by_sample"].get(sample_id, {}).get("intent"),
                           "span_fn": fn, "span_fp": fp, "fn_types": None}
    return {"rows": dict(sorted(rows.items())), "source": arm["scorer_id"], "sha256": digest(path)}


def load_exemplar_pool(data_root: Path, relpath: str) -> dict:
    """value key -> (intent, fillers by type, folded utterance).  Bodies stay in-process."""
    path = data_root / relpath
    document = json.loads(path.read_text(encoding="utf-8"))
    pool = {}
    for value in document["values"]:
        parts = [part.strip() for part in (value.get("content") or "").split(" | ")]
        if len(parts) != 3:
            raise ReadError(f"{relpath}: an exemplar body does not carry three fields")
        fillers: dict[str, list[str]] = defaultdict(list)
        if parts[2] and parts[2] != "none":
            for chunk in parts[2].split("; "):
                name, _, filler = chunk.partition("=")
                if name.strip():
                    fillers[name.strip()].append(fold(filler))
        pool[value["value_id"].split("value:", 1)[-1]] = {
            "intent": parts[1], "fillers": dict(fillers), "utterance": fold(parts[0])}
    return {"relpath": relpath, "sha256": digest(path), "content_sha256": document.get("snapshot_sha256"),
            "values": pool}


def load_contract_bodies(data_root: Path) -> dict:
    path = data_root / SC_SNAPSHOT
    document = json.loads(path.read_text(encoding="utf-8"))
    return {"relpath": SC_SNAPSHOT, "sha256": digest(path),
            "bodies": {v["value_id"].split("slot-contract:", 1)[-1]: fold(v.get("content") or "")
                       for v in document["values"]}}


# ---------------------------------------------------------------------------
# sealed rows


def load_phases(data_root: Path, arm: dict) -> dict:
    directory = data_root / "runs" / arm["run_id"] / arm["attempt"]
    path = directory / f"{arm['run_id']}.phases.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema") != "saea-flight-phase-summaries-v1" or len(document["phases"]) != 1:
        raise ReadError(f"{arm['label']}: unexpected phase artefact")
    rows, checks = {}, Counter()
    for result in document["phases"][0]["results"]:
        sample_id = result["sample_id"]
        boundary = [v.split(IB_PREFIX, 1)[-1] for v in result["initial_query_state"]["retrieved_value_ids"]
                    if v.startswith(IB_PREFIX)]
        ex_rank, ex_rendered, acquired, solver_ids = [], [], [], None
        for wave in result.get("waves") or ():
            fusion = wave.get("fusion_decision") or {}
            selected = fusion.get("selected_value_ids") or []
            if not any(v.startswith(EX_PREFIX) for v in selected):
                continue
            candidates = (wave.get("rank_result") or {}).get("candidates") or []
            scores = [c["score"] for c in candidates if str(c["facet_id"]).startswith(EX_FACET_PREFIX)]
            checks["exemplar_rank_scores_descending"] += int(scores == sorted(scores, reverse=True))
            ex_rank = [str(c["facet_id"]).split(EX_FACET_PREFIX, 1)[-1] for c in candidates
                       if str(c["facet_id"]).startswith(EX_FACET_PREFIX)]
            ex_rendered = [v.split(EX_PREFIX, 1)[-1] for v in selected if v.startswith(EX_PREFIX)]
            acquired = list((wave.get("transition") or {}).get("new_value_ids") or [])
            solver_ids = list(result["initial_query_state"]["retrieved_value_ids"]) + acquired
            break
        checks["exemplar_rendered_is_sorted_value_ids"] += int(ex_rendered == sorted(ex_rendered))
        checks["exemplar_rank_set_equals_rendered_set"] += int(set(ex_rank) == set(ex_rendered))
        candidates_intents, perception_parsed = [], False
        for state in result.get("agent_states") or ():
            if state.get("state_kind") == "phase:perception":
                try:
                    payload = json.loads(state.get("content") or "")
                    candidates_intents = [str(c.get("intent_id")) for c in payload.get("candidates") or ()]
                    perception_parsed = True
                except (ValueError, AttributeError, TypeError):
                    candidates_intents = []
                break
        checks["perception_state_parsed"] += int(perception_parsed)
        receipt = result.get("native_episode_receipt") or {}
        normaliser = receipt.get("deliver_normaliser") or {}
        rows[sample_id] = {
            "boundary": boundary, "ex_rank": ex_rank, "ex_rendered": ex_rendered,
            "contracts": sorted(v.split(SC_PREFIX, 1)[-1] for v in acquired if v.startswith(SC_PREFIX)),
            "perception": candidates_intents, "solver_ids": solver_ids,
            "label_branch": normaliser.get("label_branch")}
        checks["rows"] += 1
    del document
    return {"rows": rows, "checks": dict(sorted(checks.items())), "relpath": str(path.relative_to(data_root)),
            "sha256": digest(path), "directory": directory}


def load_delivered(directory: Path, arm: dict, inventory) -> dict:
    path = directory / f"{arm['run_id']}.outputs.jsonl"
    rows, projected_changed = {}, 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            text = record.get("text") or ""
            outcome = apply_slurp_projection_v3_delivery(text, carrier_lock_key="slurp", inventory=inventory)
            projected_changed += int(outcome.changed)
            scenario, action, entities, parsed = parse_slu_response(outcome.text)
            rows[record["sample_id"]] = {
                "parsed": bool(parsed),
                "intent": f"{scenario}_{action}" if parsed and scenario is not None and action is not None else None,
                "entities": tuple((e.type, e.filler) for e in entities)}
    return {"rows": rows, "relpath": path.name, "sha256": digest(path), "projection_changed_rows": projected_changed}


def verify_trace(directory: Path, arm: dict, phases: dict) -> dict:
    """The model-facing order: every perception and first solver MODEL_REQUEST's
    ``supplied_evidence`` ids against the sealed query-state order this read
    uses as the rendered block order.  Streams the trace once; keeps ids only."""
    path = directory / f"{arm['run_id']}.trace.jsonl"
    seen_solver, counts = set(), Counter()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if '"MODEL_REQUEST"' not in line[:200]:
                continue
            record = json.loads(line)
            if record.get("channel") != "MODEL_REQUEST":
                continue
            payload = (record.get("payload") or {}).get("payload") or {}
            key = str(payload.get("key_representation_id") or "")
            sample_id = payload.get("sample_id")
            row = phases["rows"].get(sample_id)
            if row is None:
                continue
            ids = [item.get("evidence_id") for item in payload.get("supplied_evidence") or ()]
            if key.endswith(":perception"):
                counts["perception_contacts"] += 1
                counts["perception_order_agrees"] += int([i.split(IB_PREFIX, 1)[-1] for i in ids] == row["boundary"])
            elif key.endswith(":solver") and sample_id not in seen_solver:
                seen_solver.add(sample_id)
                counts["first_solver_contacts"] += 1
                counts["solver_order_agrees"] += int(row["solver_ids"] is not None and ids == row["solver_ids"])
    return {"relpath": path.name, "sha256": None, **dict(sorted(counts.items()))}


# ---------------------------------------------------------------------------
# per-row derivation


def derive_rows(*, arm, population, phases, delivered, gold, pool, contracts, cosines, own_key) -> dict:
    rows, checks = {}, Counter()
    for sample_id, verdict in sorted(population["rows"].items()):
        sealed, answer = phases["rows"].get(sample_id), delivered["rows"].get(sample_id)
        gold_row = gold["by_sample"].get(sample_id)
        if sealed is None or answer is None or gold_row is None or verdict["gold_intent"] is None:
            checks["skipped"] += 1
            continue
        klass, gold_intent = verdict["class"], verdict["gold_intent"]
        intent_ok = klass not in ("INTENT-WRONG", "MALFORMED")
        checks["rows"] += 1
        checks["parsed_intent_agrees_with_class"] += int((answer["intent"] == gold_intent) == intent_ok)
        # exact-match FN per the official matcher (bank step 1)
        remaining = list(gold_row["entities"])
        unmatched_pred = []
        for entity in answer["entities"]:
            if entity in remaining:
                remaining.remove(entity)
            else:
                unmatched_pred.append(entity)
        if verdict["span_fn"] is not None:
            checks["fn_count_agrees_with_sealed"] += int(abs(len(remaining) - float(verdict["span_fn"])) < 1e-9)
        # boundary block
        boundary = sealed["boundary"]
        gold_pos = boundary.index(gold_intent) + 1 if gold_intent in boundary else None
        delivered_pos = boundary.index(answer["intent"]) + 1 if answer["intent"] in boundary else None
        # exemplar block: rank and rendered position of gold-intent exemplars
        rank_of = {key: i + 1 for i, key in enumerate(sealed["ex_rank"])}
        pos_of = {key: i + 1 for i, key in enumerate(sealed["ex_rendered"])}
        gold_ex = sorted(k for k in sealed["ex_rendered"] if pool["values"].get(k, {}).get("intent") == gold_intent)
        # per-type first exemplar carrying that type
        type_first_rank, type_first_pos = {}, {}
        for key in sealed["ex_rendered"]:
            for slot_type in pool["values"].get(key, {}).get("fillers", {}):
                type_first_rank[slot_type] = min(type_first_rank.get(slot_type, 99), rank_of.get(key, 99))
                type_first_pos[slot_type] = min(type_first_pos.get(slot_type, 99), pos_of.get(key, 99))
        # agree-1 replay (rank diagnostic arithmetic) on the recomputed cosines
        cos = cosines.get(sample_id)
        agree_rank = None
        if cos is not None:
            mine, votes = own_key(sample_id), Counter()
            for key in sealed["ex_rendered"]:
                if mine is not None and key == mine:
                    continue
                intent = pool["values"].get(key, {}).get("intent")
                if intent is not None:
                    votes[intent] += 1
            total = sum(votes.values())
            share = {i: votes[i] / total for i in votes} if total else {}
            ordering = sorted(cos, key=lambda i: (-(cos[i] + AGREE_WEIGHT * share.get(i, 0.0)), i))
            agree_rank = ordering.index(gold_intent) + 1 if gold_intent in ordering else None
        # C: per missed gold item
        supplied_fillers, bodies = set(), []
        for key in sealed["ex_rendered"]:
            entry = pool["values"].get(key)
            if entry is None:
                continue
            for values in entry["fillers"].values():
                supplied_fillers.update(values)
            bodies.append(entry["utterance"])
        bodies.extend(contracts["bodies"].get(t, "") for t in sealed["contracts"])
        body_text = "\n".join(bodies)
        items = []
        pred_by_type: dict[str, list[tuple[int, str]]] = defaultdict(list)
        for index, (ptype, pfiller) in enumerate(unmatched_pred):
            pred_by_type[ptype].append((index, fold(pfiller)))
        used_pred: set[int] = set()
        pairs = []
        for gindex, (gtype, gfiller) in enumerate(remaining):
            for pindex, pfold in pred_by_type.get(gtype, ()):
                left = fold(gfiller)
                pairs.append((edit_distance(pfold, left) / max(len(pfold), len(left), 1), pindex, gindex, pfold))
        paired: dict[int, str] = {}
        for _, pindex, gindex, pfold in sorted(pairs):
            if pindex in used_pred or gindex in paired:
                continue
            used_pred.add(pindex)
            paired[gindex] = pfold
        for gindex, (gtype, gfiller) in enumerate(remaining):
            gfold = fold(gfiller)
            available = gfold in supplied_fillers or (bool(gfold) and gfold in body_text)
            if gindex in paired:
                pfold = paired[gindex]
                kind = ("copied-exemplar-filler" if pfold in supplied_fillers
                        else "in-supplied-body-text" if pfold and pfold in body_text
                        else "not-from-supply")
                span_related = bool(pfold) and (pfold in gfold or gfold in pfold)
            else:
                swapped = any(fold(pf) == gfold for i, (pt, pf) in enumerate(unmatched_pred)
                              if i not in used_pred and pt != gtype)
                kind = "type-swapped" if swapped else ("ignored-available" if available else "ignored-unavailable")
                span_related = False
            items.append({"type": gtype, "kind": kind, "gold_available_in_supply": available,
                          "span_related": span_related,
                          "type_first_rank": type_first_rank.get(gtype), "type_first_pos": type_first_pos.get(gtype)})
        rows[sample_id] = {
            "class": klass, "plan_class": verdict["plan_class"], "intent_ok": intent_ok,
            "gold_intent": gold_intent, "delivered_intent": answer["intent"], "parsed": answer["parsed"],
            "label_branch": sealed["label_branch"],
            "boundary_width": len(boundary), "gold_pos": gold_pos, "delivered_pos": delivered_pos,
            "gold_in_perception": gold_intent in sealed["perception"],
            "delivered_in_perception": answer["intent"] in sealed["perception"],
            "perception_width": len(sealed["perception"]),
            "gold_ex_count": len(gold_ex),
            "gold_ex_first_rank": min((rank_of.get(k, 99) for k in gold_ex), default=None),
            "gold_ex_first_pos": min((pos_of.get(k, 99) for k in gold_ex), default=None),
            "gold_types": sorted({t for t, _ in gold_row["entities"]}),
            "type_first_rank": type_first_rank, "type_first_pos": type_first_pos,
            "fn_items": items, "fn_count": len(remaining), "fp_count": len(unmatched_pred),
            "cos_rank": (sorted(cos, key=lambda i: (-cos[i], i)).index(gold_intent) + 1
                         if cos is not None and gold_intent in cos else None),
            "agree_rank": agree_rank}
    return {"rows": rows, "checks": dict(sorted(checks.items()))}


# ---------------------------------------------------------------------------
# tables


def rate(rows, key=lambda r: r["intent_ok"]):
    return {"n": len(rows), "correct": sum(1 for r in rows if key(r)), "pct": round(pct(sum(1 for r in rows if key(r)), len(rows)), 1)}


def freedom_table(rows) -> dict:
    parsed = [r for r in rows.values() if r["delivered_intent"] is not None]
    out = {"rows": len(rows), "parsed": len(parsed),
           "delivered_outside_block": rate([r for r in parsed if r["delivered_pos"] is None]),
           "delivered_inside_block": rate([r for r in parsed if r["delivered_pos"] is not None]),
           "delivered_outside_perception": rate([r for r in parsed if not r["delivered_in_perception"]]),
           "delivered_inside_perception": rate([r for r in parsed if r["delivered_in_perception"]]),
           "correct_with_gold_outside_block": sum(1 for r in parsed if r["intent_ok"] and r["gold_pos"] is None),
           "correct_with_gold_outside_perception": sum(1 for r in parsed if r["intent_ok"] and not r["gold_in_perception"]),
           "gold_in_block": rate([r for r in parsed if r["gold_pos"] is not None]),
           "gold_in_perception": rate([r for r in parsed if r["gold_in_perception"]]),
           "gold_in_block_and_perception": rate([r for r in parsed if r["gold_pos"] is not None and r["gold_in_perception"]]),
           "gold_in_block_not_perception": rate([r for r in parsed if r["gold_pos"] is not None and not r["gold_in_perception"]]),
           "gold_not_block_in_perception": rate([r for r in parsed if r["gold_pos"] is None and r["gold_in_perception"]]),
           "label_branches": dict(sorted(Counter(str(r["label_branch"]) for r in rows.values()).items())),
           "perception_widths": dict(sorted(Counter(r["perception_width"] for r in rows.values()).items()))}
    return out


def boundary_position_table(rows) -> dict:
    with_gold = [r for r in rows.values() if r["gold_pos"] is not None]
    per_pos = {}
    for p in range(1, FLOWN_K + 1):
        subset = [r for r in with_gold if r["gold_pos"] == p]
        per_pos[p] = {**rate(subset), "in_perception": sum(1 for r in subset if r["gold_in_perception"]),
                      "correct_given_perception": rate([r for r in subset if r["gold_in_perception"]])["pct"]}
    wrong = [r for r in with_gold if r["class"] == "INTENT-WRONG"]
    right = [r for r in with_gold if r["intent_ok"]]

    def dist(subset):
        return {p: sum(1 for r in subset if r["gold_pos"] == p) for p in range(1, FLOWN_K + 1)}

    def mean_pos(subset):
        return round(sum(r["gold_pos"] for r in subset) / len(subset), 2) if subset else None

    wrong_both = [r for r in wrong if r["delivered_pos"] is not None]
    return {"rows_with_gold": len(with_gold), "per_position": per_pos,
            "wrong": {"n": len(wrong), "dist": dist(wrong), "mean_pos": mean_pos(wrong),
                      "gold_in_perception": sum(1 for r in wrong if r["gold_in_perception"]),
                      "delivered_in_block": len(wrong_both),
                      "delivered_above_gold": sum(1 for r in wrong_both if r["delivered_pos"] < r["gold_pos"]),
                      "delivered_at_1": sum(1 for r in wrong_both if r["delivered_pos"] == 1),
                      "delivered_in_perception": sum(1 for r in wrong if r["delivered_in_perception"]),
                      "delivered_at_1_given_gold_in_perception": sum(
                          1 for r in wrong_both if r["gold_in_perception"] and r["delivered_pos"] == 1),
                      "gold_pos_5_to_8": sum(1 for r in wrong if r["gold_pos"] >= 5)},
            "correct": {"n": len(right), "dist": dist(right), "mean_pos": mean_pos(right),
                        "gold_pos_5_to_8": sum(1 for r in right if r["gold_pos"] >= 5)},
            "tail_5_to_8": rate([r for r in with_gold if r["gold_pos"] >= 5]),
            "not_top_2_to_8": rate([r for r in with_gold if r["gold_pos"] >= 2]),
            "pass_through_5_to_8": {"n": sum(1 for r in with_gold if r["gold_pos"] >= 5),
                                    "in_perception": sum(1 for r in with_gold if r["gold_pos"] >= 5 and r["gold_in_perception"])},
            "head_1": rate([r for r in with_gold if r["gold_pos"] == 1])}


def agree_table(rows, per_pos, conv_receipt) -> dict:
    with_cos = [r for r in rows.values() if r["cos_rank"] is not None and r["agree_rank"] is not None]
    delivered_wrong = [r for r in with_cos if r["class"] == "INTENT-WRONG" and r["gold_pos"] is not None]
    newly = [r for r in with_cos if r["cos_rank"] > FLOWN_K and r["agree_rank"] <= FLOWN_K]
    lost = [r for r in with_cos if r["cos_rank"] <= FLOWN_K and r["agree_rank"] > FLOWN_K]

    def entry(subset):
        counts = Counter(r["agree_rank"] for r in subset)
        matched = sum(per_pos[p]["pct"] * counts[p] for p in counts) / len(subset) if subset else None
        return {"n": len(subset), "entry_positions": {p: counts[p] for p in range(1, FLOWN_K + 1)},
                "position_matched_correct_pct": round(matched, 1) if matched is not None else None,
                "at_position_1": counts[1]}

    conv_ids = sorted(sid for sid, r in rows.items()
                      if r in newly and r["class"] == "INTENT-WRONG" and not r["gold_in_perception"])
    bank_agrees = all(rows[sid]["plan_class"] in (CONV_CLASS, "INTENT-WRONG") for sid in conv_ids)
    conv = [rows[sid] for sid in conv_ids]
    conv_sha = hashlib.sha256("\n".join(conv_ids).encode("utf-8")).hexdigest()
    registered = conv_receipt or {}
    return {"rows": len(with_cos),
            "cos_rank_equals_sealed_position": sum(1 for r in with_cos if r["gold_pos"] is not None and r["cos_rank"] == r["gold_pos"]),
            "rows_with_gold_in_block": sum(1 for r in with_cos if r["gold_pos"] is not None),
            "delivered_wrong": {"n": len(delivered_wrong),
                                "moved_up": sum(1 for r in delivered_wrong if r["agree_rank"] < r["gold_pos"]),
                                "unchanged": sum(1 for r in delivered_wrong if r["agree_rank"] == r["gold_pos"]),
                                "moved_down_in_block": sum(1 for r in delivered_wrong if r["gold_pos"] < r["agree_rank"] <= FLOWN_K),
                                "dropped_out": sum(1 for r in delivered_wrong if r["agree_rank"] > FLOWN_K),
                                "to_rank_1": sum(1 for r in delivered_wrong if r["agree_rank"] == 1),
                                "mean_pos_before": round(sum(r["gold_pos"] for r in delivered_wrong) / len(delivered_wrong), 2) if delivered_wrong else None,
                                "mean_pos_after": round(sum(min(r["agree_rank"], 9) for r in delivered_wrong) / len(delivered_wrong), 2) if delivered_wrong else None},
            "newly_all": entry(newly),
            "newly_intent_wrong": entry([r for r in newly if r["class"] == "INTENT-WRONG"]),
            "newly_correct_today": sum(1 for r in newly if r["intent_ok"]),
            "conv_roster": {**entry(conv), "id_list_sha256": conv_sha, "bank_class_agrees": bank_agrees,
                            "registered_count": registered.get("count"),
                            "registered_id_list_sha256": registered.get("id_list_sha256"),
                            "matches_registered": bool(registered) and conv_sha == registered.get("id_list_sha256")
                            and len(conv_ids) == registered.get("count")},
            "dropped_out_of_block": {"n": len(lost), "correct": sum(1 for r in lost if r["intent_ok"]),
                                     "by_plan_class": dict(sorted(Counter(r["plan_class"] for r in lost).items()))}}


def exemplar_table(rows) -> dict:
    def by(key_fn, table):
        out = {}
        for label, _, _ in table:
            subset = [r for r in rows.values() if key_fn(r) == label]
            out[label] = rate(subset)
        return out

    wrong = [r for r in rows.values() if r["class"] == "INTENT-WRONG"]
    right = [r for r in rows.values() if r["intent_ok"]]
    fixed = {}
    for label, low, high in COUNT_BUCKETS[1:3]:
        subset = [r for r in rows.values() if low <= r["gold_ex_count"] <= high]
        fixed[label] = {
            "by_first_pos": {pl: rate([r for r in subset if bucket(r["gold_ex_first_pos"] or 99, POS_BUCKETS) == pl]) for pl, _, _ in POS_BUCKETS},
            "by_first_rank": {rl: rate([r for r in subset if bucket(r["gold_ex_first_rank"] or 99, RANK_BUCKETS) == rl]) for rl, _, _ in RANK_BUCKETS}}
    return {"fixed_count": fixed,
            "by_count": by(lambda r: bucket(r["gold_ex_count"], COUNT_BUCKETS), COUNT_BUCKETS),
            "by_first_rank": by(lambda r: bucket(r["gold_ex_first_rank"] or 99, RANK_BUCKETS), RANK_BUCKETS),
            "by_first_pos": by(lambda r: bucket(r["gold_ex_first_pos"] or 99, POS_BUCKETS), POS_BUCKETS),
            "wrong_count_dist": {label: sum(1 for r in wrong if bucket(r["gold_ex_count"], COUNT_BUCKETS) == label) for label, _, _ in COUNT_BUCKETS},
            "correct_count_dist": {label: sum(1 for r in right if bucket(r["gold_ex_count"], COUNT_BUCKETS) == label) for label, _, _ in COUNT_BUCKETS},
            "delivered_wrong_count_dist": {label: sum(1 for r in wrong if r["gold_pos"] is not None and bucket(r["gold_ex_count"], COUNT_BUCKETS) == label) for label, _, _ in COUNT_BUCKETS}}


def entity_position_table(rows) -> dict:
    out = {}
    for klass in ENTITY_CLASSES:
        subset = [r for r in rows.values() if r["class"] == klass]
        first_pos = [item["type_first_pos"] or 99 for r in subset for item in r["fn_items"]]
        first_rank = [item["type_first_rank"] or 99 for r in subset for item in r["fn_items"]]
        out[klass] = {"rows": len(subset), "missed_items": len(first_pos),
                      "pos": {label: sum(1 for v in first_pos if bucket(v, POS_BUCKETS) == label) for label, _, _ in POS_BUCKETS},
                      "pos_none": sum(1 for v in first_pos if v == 99),
                      "rank": {label: sum(1 for v in first_rank if bucket(v, RANK_BUCKETS) == label) for label, _, _ in RANK_BUCKETS},
                      "rank_none": sum(1 for v in first_rank if v == 99)}
    correct = [r for r in rows.values() if r["class"] == "CORRECT"]
    first_pos = [r["type_first_pos"].get(t, 99) for r in correct for t in r["gold_types"]]
    first_rank = [r["type_first_rank"].get(t, 99) for r in correct for t in r["gold_types"]]
    out["CORRECT"] = {"rows": len(correct), "missed_items": len(first_pos),
                      "pos": {label: sum(1 for v in first_pos if bucket(v, POS_BUCKETS) == label) for label, _, _ in POS_BUCKETS},
                      "pos_none": sum(1 for v in first_pos if v == 99),
                      "rank": {label: sum(1 for v in first_rank if bucket(v, RANK_BUCKETS) == label) for label, _, _ in RANK_BUCKETS},
                      "rank_none": sum(1 for v in first_rank if v == 99)}
    return out


def residual_split_table(rows) -> dict:
    out = {}
    for klass in ENTITY_CLASSES + ("INTENT-WRONG",):
        items = [item for r in rows.values() if r["class"] == klass for item in r["fn_items"]]
        kinds = Counter(item["kind"] for item in items)
        out[klass] = {"items": len(items), "kinds": {k: kinds.get(k, 0) for k in C_KINDS},
                      "gold_available_in_supply": sum(1 for item in items if item["gold_available_in_supply"]),
                      "copied_span_related": sum(1 for item in items if item["kind"] == "copied-exemplar-filler" and item["span_related"]),
                      "not_from_supply_span_related": sum(1 for item in items if item["kind"] == "not-from-supply" and item["span_related"])}
    return out


# ---------------------------------------------------------------------------
# markdown


def fmt_rate(cell) -> str:
    return f"{cell['correct']}/{cell['n']} ({cell['pct']:.1f} %)"


def write_markdown(path: Path, report: dict) -> None:
    lines: list[str] = []
    add = lines.append
    arms = report["arms"]
    labels = [a["label"] for a in ARMS]
    add("# SLURP: where the gold entry sits in the delivered block, and how free the Solver is over the intent")
    add("")
    add(f"Date: 2026-09-26. Read id `{READ_ID}`, recipe `{RECIPE}`. Generated `{report['generated_at']}`. "
        "A model-free read over sealed bytes: zero model, server, tokenizer, encoder, embedder, scorer, network, GPU and paid-API contacts. "
        "A DIAGNOSTIC, never a gate: it registers no cell, admits no mechanism, authorises no flight and states no effectiveness, superiority or generalisation claim; "
        "every roster is a discovery or dev roster and every number is a development number (owner decisions 28 and 86). "
        "No utterance text, transcript, delivered answer, gold filler, predicted filler, candidate distinction or knowledge body is written or printed: every cell is an id, a position, a count, a rate or a hash. "
        "Gold is read offline on the scoring side only (the sealed bad-case bank, the sealed ROLL-1 official score file, the governed TRAIN and DEVEL splits through `data.slurp.load_slurp_split`) and reaches no query, key, selector or config.")
    add("")
    add("## 0. Inputs")
    add("")
    add("| Artefact | Relpath under `SPEECHRL_DATA_DIR` | sha256 |")
    add("| --- | --- | --- |")
    add(f"| bad-case bank | `{BANK}` | `{report['bank_sha256']}` |")
    add(f"| slot-contracts-v2 snapshot | `{SC_SNAPSHOT}` | `{report['contracts_sha256']}` |")
    for label in labels:
        a = arms[label]
        add(f"| `{label}` phases | `{a['phases_relpath']}` | `{a['phases_sha256']}` |")
        add(f"| `{label}` outputs | `{a['outputs_relpath']}` | `{a['outputs_sha256']}` |")
        add(f"| `{label}` exemplar pool | `{a['pool_relpath']}` | `{a['pool_sha256']}` |")
    add(f"| ROLL-1 official score file | `{ARMS[0]['scores']}` | `{arms['roll1']['population_sha256']}` |")
    add("")
    add("**Structural checks, all rows.** Delivered answers are parsed after `apply_slurp_projection_v3_delivery` (idempotent on the two PLAN rosters, whose deliver node already applied it; the ROLL-1 pool has no deliver node and its scorer projects at scoring time), "
        "so the parsed intent and the exact-match entity counts reproduce the sealed classes. "
        "The rendered block order is the sealed query-state order: `rails.kb_policy.fuse_associated_values_factory` (kb_policy.py:893-960) walks the boundary candidates in rank order, so positions 1-8 ARE cosine ranks 1-8; "
        "`_fuse_supply_filter` returns `tuple(sorted(set(selected_value_ids)))` (kb_policy.py:859), so the twenty exemplars are rendered in string order of their value ids and the retrieval rank is not visible to the model; "
        "`core.model.transport` renders `supplied_evidence` in list order (transport.py:889-896). The trace pass below checks that order against every perception contact and every row's first Solver contact.")
    add("")
    add("| Arm | rows | parsed intent == sealed class | exact FN == sealed FN | exemplar rank scores descending | exemplar block rendered in sorted id order | Perception state parsed | perception contacts: order agrees | first Solver contacts: order agrees | cosine rank == sealed position |")
    add("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for label in labels:
        a = arms[label]
        c, p, t, g = a["derive_checks"], a["phase_checks"], a["trace"], a["agree"]
        add(f"| `{label}` | {c['rows']} | {c['parsed_intent_agrees_with_class']} | {c.get('fn_count_agrees_with_sealed', 'n/a')} | "
            f"{p['exemplar_rank_scores_descending']} | {p['exemplar_rendered_is_sorted_value_ids']} | {p['perception_state_parsed']} | "
            f"{t['perception_order_agrees']}/{t['perception_contacts']} | {t['solver_order_agrees']}/{t['first_solver_contacts']} | "
            f"{g['cos_rank_equals_sealed_position']}/{g['rows_with_gold_in_block']} |")
    add("")
    add("## A. Is delivery necessary, or only persuasive?")
    add("")
    add("**The code answer: nothing ties the delivered intent to the eight.** Two candidate sets exist and neither binds the Solver. "
        "(1) Perception's block is the k=8 boundary retrieval, but Perception's OUTPUT is constrained only by the structured-output schema, whose `intent_id` enum is `validator.legal_intent_ids` -- all 60 -- not the delivered eight (`rails/artifact_results.py:275-278`); the projection that reads it keeps at most three distinct ids (`configs/baseline/slurp-native-default-plan-lock-baseline-v1.json`, `candidate_supply.solver.max_candidates` 3). "
        "(2) The Solver receives those hypotheses as a sealed `phase:perception` state in its history, the same 8+20+contracts evidence block, and the full inventory in the shared task instruction (`configs/probes/slurp_native_role_context_v3.txt:5-8`, rendered by `data/slurp.py:1236-1250`); its own instruction says 'choose one of those candidate intents' and 'use the scenario/action pair belonging to the selected candidate' (`configs/probes/slurp_native_role_solver_v2.txt:1,6`), and that sentence is the ONLY tie. "
        "The Solver phase declares no response format (`configs/policy/phase-native-candidates-review-revise-v1.json`, solver `response_format_id: null`); `parse_slu_response` accepts any scenario/action strings (`reproduction/slurp_scoring.py:349-370`); the deliver node projects an illegal pair onto the 60-pair inventory, never onto the candidates (`rails/delivery_normalisers.py:84-110`, `rails/slurp_projection_v3.py:387-447`); "
        "the candidate route itself states that hypotheses 'never restrict the Solver's legal answer space' and indexes contracts against the full inventory (`rails/candidate_semantic_supply.py:5-6, 611-636`); the commit policy takes a plurality over parsed votes with no legality check (`rails/commit_policies.py:168-196, 267-347`); "
        "the Reviewer's verdicts steer nothing (`rails/controllers.py:666-675`) and its tool was retired (decision 135); the Planner may only route and cannot deliver (`rails/controllers.py:993-995`); and the ACCEPT route delivers the latest delivery-eligible Solver draft as is (`reproduction/ojw/native_episode.py:1023-1033`). "
        "So the Solver is free over all 60, and beyond them up to projection.")
    add("")
    add("**The empirical answer.** Delivered intents by where they sit; correctness is the sealed class.")
    add("")
    add("| Arm | parsed | delivered outside the 8 (n, correct) | delivered inside the 8 | delivered outside Perception's list | delivered inside the list | correct rows whose gold was NOT in the 8 | correct rows whose gold was NOT in the list | Perception widths |")
    add("| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- |")
    for label in labels:
        f = arms[label]["freedom"]
        add(f"| `{label}` | {f['parsed']} | {fmt_rate(f['delivered_outside_block'])} | {fmt_rate(f['delivered_inside_block'])} | "
            f"{fmt_rate(f['delivered_outside_perception'])} | {fmt_rate(f['delivered_inside_perception'])} | "
            f"{f['correct_with_gold_outside_block']} | {f['correct_with_gold_outside_perception']} | {f['perception_widths']} |")
    add("")
    add("| Arm | gold in the 8 | gold in Perception's list | gold in both | gold in the 8 but not the list | gold in the list but not the 8 | deliver-node label branches |")
    add("| --- | --- | --- | --- | --- | --- | --- |")
    for label in labels:
        f = arms[label]["freedom"]
        add(f"| `{label}` | {fmt_rate(f['gold_in_block'])} | {fmt_rate(f['gold_in_perception'])} | {fmt_rate(f['gold_in_block_and_perception'])} | "
            f"{fmt_rate(f['gold_in_block_not_perception'])} | {fmt_rate(f['gold_not_block_in_perception'])} | {f['label_branches']} |")
    add("")
    fa = arms["train-fold-a-plan"]["freedom"]
    add(f"**Reading.** The Solver does leave the block, and it is usually wrong when it does: on TRAIN Fold A {fa['delivered_outside_block']['n']} delivered intents sit outside the eight and {fa['delivered_outside_block']['correct']} of them are right ({fa['delivered_outside_block']['pct']:.1f} %), against {fa['delivered_inside_block']['pct']:.1f} % inside. "
        f"It almost never leaves Perception's list ({fa['delivered_outside_perception']['n']} rows), so the practical selector is the 1-3 hypotheses, not the eight. "
        f"Correct answers whose gold entry was never delivered exist -- {fa['correct_with_gold_outside_block']} on Fold A -- so delivery is not NECESSARY; the block persuades Perception, Perception's list persuades the Solver, and the funnel is what section B measures. "
        f"Rows whose gold sits in the block but not in the list convert at {fa['gold_in_block_not_perception']['pct']:.1f} %; rows whose gold reached the list convert at {fa['gold_in_perception']['pct']:.1f} %.")
    add("")
    add("## B. Does position inside the delivered block predict correctness?")
    add("")
    add("### B.1 Boundary block: P(intent correct | gold at position p), and Perception pass-through by position")
    add("")
    add("| Arm | " + " | ".join(f"p={p}" for p in range(1, FLOWN_K + 1)) + " | p=1 | p=5-8 |")
    add("| --- | " + " | ".join("---" for _ in range(FLOWN_K)) + " | --- | --- |")
    for label in labels:
        b = arms[label]["boundary"]
        add(f"| `{label}` correct | " + " | ".join(fmt_rate(b["per_position"][p]) for p in range(1, FLOWN_K + 1))
            + f" | {fmt_rate(b['head_1'])} | {fmt_rate(b['tail_5_to_8'])} |")
        add(f"| `{label}` gold reaches Perception's list | " + " | ".join(
            f"{b['per_position'][p]['in_perception']}/{b['per_position'][p]['n']}" for p in range(1, FLOWN_K + 1)) + " | | |")
    add("")
    add("### B.2 The delivered-but-wrong rows: where gold sat, where the wrong answer sat")
    add("")
    add("| Arm | delivered-but-wrong rows | gold position 1..8 (counts) | mean pos | gold at 5-8 | gold was in Perception's list | wrong answer in the block | wrong answer ABOVE gold | wrong answer at position 1 | ... and gold in the list too | wrong answer in Perception's list | intent-correct rows: position 1..8 | mean pos | at 5-8 |")
    add("| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |")
    for label in labels:
        b = arms[label]["boundary"]
        w, c = b["wrong"], b["correct"]
        add(f"| `{label}` | {w['n']} | {list(w['dist'].values())} | {w['mean_pos']} | {w['gold_pos_5_to_8']} | {w['gold_in_perception']} | {w['delivered_in_block']} | {w['delivered_above_gold']} | {w['delivered_at_1']} | {w['delivered_at_1_given_gold_in_perception']} | {w['delivered_in_perception']} | "
            f"{list(c['dist'].values())} | {c['mean_pos']} | {c['gold_pos_5_to_8']} |")
    add("")
    add("### B.3 What the agree-1 reorder does to those rows (offline replay of the rank diagnostic's arithmetic)")
    add("")
    add("Votes are the frozen pool intent labels of the row's own twenty delivered exemplars, self-excluded; weight 1.0 on the recomputed cosine, the rank diagnostic's `agree-1`. The CONV column is the newly delivered rows that are intent-wrong today with gold NOT on Perception's list (the bank's `INTENT-UNCOVERED`), hashed by the registered convention; on Fold A it is checked against the registered roster's id-list sha256.")
    add("")
    add("| Arm | delivered-but-wrong rows | gold moves UP | unchanged | moves down, stays in | drops out of the 8 | lands at position 1 | mean pos before -> after | newly delivered: all rows | correct today | intent-wrong today | CONV analogue (intent-wrong, gold off the list) | CONV entry positions 1..8 | CONV at position 1 | position-matched P(correct) on CONV | id list matches the registered roster | rows whose gold drops out (by class) |")
    add("| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | --- |")
    for label in labels:
        g = arms[label]["agree"]
        d, cv, l = g["delivered_wrong"], g["conv_roster"], g["dropped_out_of_block"]
        add(f"| `{label}` | {d['n']} | {d['moved_up']} | {d['unchanged']} | {d['moved_down_in_block']} | {d['dropped_out']} | {d['to_rank_1']} | {d['mean_pos_before']} -> {d['mean_pos_after']} | "
            f"{g['newly_all']['n']} | {g['newly_correct_today']} | {g['newly_intent_wrong']['n']} | {cv['n']} | {list(cv['entry_positions'].values())} | {cv['at_position_1']} | {cv['position_matched_correct_pct']} % | "
            f"{'yes (' + str(cv['registered_count']) + ' rows, sha256 ' + str(cv['registered_id_list_sha256'])[:12] + ')' if cv['matches_registered'] else 'n/a' if cv['registered_count'] is None else 'NO'} | {l['n']} {l['by_plan_class']} |")
    add("")
    add("### B.4 Exemplar block: gold-intent exemplars among the twenty")
    add("")
    add("Rendered position is string order of value ids (arbitrary with respect to similarity); retrieval rank is the sealed cosine order the model never sees.")
    add("")
    add("| Arm | gold-intent exemplars: " + " | ".join(l for l, _, _ in COUNT_BUCKETS) + " | first by rank: " + " | ".join(l for l, _, _ in RANK_BUCKETS) + " | first by rendered position: " + " | ".join(l for l, _, _ in POS_BUCKETS) + " |")
    add("| --- | " + " | ".join("---" for _ in COUNT_BUCKETS) + " | " + " | ".join("---" for _ in RANK_BUCKETS) + " | " + " | ".join("---" for _ in POS_BUCKETS) + " |")
    for label in labels:
        e = arms[label]["exemplar"]
        add(f"| `{label}` | " + " | ".join(fmt_rate(e["by_count"][l]) for l, _, _ in COUNT_BUCKETS)
            + " | " + " | ".join(fmt_rate(e["by_first_rank"][l]) for l, _, _ in RANK_BUCKETS)
            + " | " + " | ".join(fmt_rate(e["by_first_pos"][l]) for l, _, _ in POS_BUCKETS) + " |")
    add("")
    add("At fixed count (rows with exactly 1-2, then 3-5, gold-intent exemplars), the same two orderings:")
    add("")
    add("| Arm | count | rendered position " + " / ".join(l for l, _, _ in POS_BUCKETS) + " | retrieval rank " + " / ".join(l for l, _, _ in RANK_BUCKETS) + " |")
    add("| --- | --- | --- | --- |")
    for label in labels:
        for cl, block in arms[label]["exemplar"]["fixed_count"].items():
            add(f"| `{label}` | {cl} | " + " / ".join(fmt_rate(block["by_first_pos"][pl]) for pl, _, _ in POS_BUCKETS)
                + " | " + " / ".join(fmt_rate(block["by_first_rank"][rl]) for rl, _, _ in RANK_BUCKETS) + " |")
    add("")
    add("| Arm | intent-wrong rows by gold-exemplar count " + " / ".join(l for l, _, _ in COUNT_BUCKETS) + " | delivered-but-wrong rows | intent-correct rows |")
    add("| --- | --- | --- | --- |")
    for label in labels:
        e = arms[label]["exemplar"]
        add(f"| `{label}` | {list(e['wrong_count_dist'].values())} | {list(e['delivered_wrong_count_dist'].values())} | {list(e['correct_count_dist'].values())} |")
    add("")
    add("### B.5 Entity classes: where the first exemplar carrying the missed type sits")
    add("")
    add("| Arm | class | rows | items | first exemplar with the type, rendered position " + " / ".join(l for l, _, _ in POS_BUCKETS) + " / none | by retrieval rank " + " / ".join(l for l, _, _ in RANK_BUCKETS) + " / none |")
    add("| --- | --- | ---: | ---: | --- | --- |")
    for label in labels:
        for klass in ENTITY_CLASSES + ("CORRECT",):
            t = arms[label]["entity_position"][klass]
            add(f"| `{label}` | `{klass}`{' (gold types, all hit)' if klass == 'CORRECT' else ' (missed types)'} | {t['rows']} | {t['missed_items']} | "
                f"{list(t['pos'].values())} / {t['pos_none']} | {list(t['rank'].values())} / {t['rank_none']} |")
    add("")
    add("## C. The entity residual, split without contacts")
    add("")
    add("Per missed gold entity item (exact-match FN, the official matcher). A same-type unmatched predicted filler is paired to it greedily by normalised edit distance, as the bank does; the pair's predicted filler is then looked up, after the bank's P2r1 folding, in the row's supplied exemplar `type=filler` fields, then as a substring of the supplied exemplar utterances and slot-contract bodies. "
        "`available` says whether the GOLD filler itself sat in the supply. `span-related` counts pairs where one filler contains the other.")
    add("")
    add("| Arm | class | items | copied an exemplar filler | in a supplied body's text | not from supply (speech or invented) | type-swapped | ignored, gold available in supply | ignored, gold not in supply | gold available (any) | copied and span-related | not-from-supply and span-related |")
    add("| --- | --- | ---: | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: |")
    for label in labels:
        for klass in ENTITY_CLASSES + ("INTENT-WRONG",):
            s = arms[label]["residual"][klass]
            n = s["items"]
            cells = " | ".join(f"{s['kinds'][k]} ({pct(s['kinds'][k], n):.1f} %)" for k in C_KINDS)
            add(f"| `{label}` | `{klass}` | {n} | {cells} | {s['gold_available_in_supply']} | {s['copied_span_related']} | {s['not_from_supply_span_related']} |")
    add("")
    add("## D. Reading")
    add("")
    for paragraph in report["reading"]:
        add(paragraph)
        add("")
    add("## E. Boundary")
    add("")
    add("Zero model, server, tokenizer, encoder, embedder, scorer, network, GPU and paid-API contacts: no server was started, stopped or probed, no waveform decoded, no embedding computed and no subprocess run. "
        "Tools: `json` reads of three sealed `*.phases.json`, `*.outputs.jsonl` and `*.trace.jsonl` (ids only kept from the trace), the sealed bank and the ROLL-1 official score file; `data.slurp.load_slurp_split` for TRAIN and DEVEL gold; "
        "`rails.slurp_projection_v3.apply_slurp_projection_v3_delivery` and `reproduction.slurp_scoring.parse_slu_response` over delivered text in-process; the rank diagnostic's own cosine recomputation over the pinned vector files for the agree-1 replay; `hashlib` for every hash. "
        "This read admits nothing, promotes nothing, preregisters no cell, releases no store, draws no roster and reaches no superiority, generalisation or Stage-3 conclusion. Byte-reproducible apart from `generated_at`.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def spread(cells, minimum=10) -> float:
    values = [c["pct"] for c in cells.values() if c["n"] >= minimum]
    return round(max(values) - min(values), 1) if len(values) >= 2 else 0.0


def monotone(cells, minimum=10) -> bool:
    """Non-increasing P(correct) from the first bucket to the last, over buckets with at least ``minimum`` rows."""
    values = [c["pct"] for c in cells.values() if c["n"] >= minimum]
    return all(a >= b for a, b in zip(values, values[1:]))


def smallest_cell(cells, minimum=10) -> int:
    values = [c["n"] for c in cells.values() if c["n"] >= minimum]
    return min(values) if values else 0


def reading(arms: dict, conv_receipt) -> list[str]:
    fa, r1, dv = arms["train-fold-a-plan"], arms["roll1"], arms["dev2000-added-plan"]
    b, g, f, e = fa["boundary"], fa["agree"], fa["freedom"], fa["exemplar"]
    w, pp = b["wrong"], b["per_position"]
    out = []
    illegal = sum(v for k, v in f["label_branches"].items() if k not in ("already-legal", "None"))
    out.append(
        f"**A. Delivery is persuasion, not admission.** No rail binds the delivered intent to the eight or to the 60: on TRAIN Fold A the deliver node repaired {illegal} pairs that were outside the legal inventory altogether, "
        f"the Solver answered outside the eight on {f['delivered_outside_block']['n']} rows and was right on {f['delivered_outside_block']['correct']} of them ({f['delivered_outside_block']['pct']:.1f} %; ROLL-1 {r1['freedom']['delivered_outside_block']['pct']:.1f} %, DEV {dv['freedom']['delivered_outside_block']['pct']:.1f} %), "
        f"and {f['correct_with_gold_outside_block']} correct Fold A rows never received their gold entry at all. What it almost never leaves is Perception's 1-3 list ({f['delivered_outside_perception']['n']} Fold A rows): "
        f"gold in the block but dropped by Perception converts at {f['gold_in_block_not_perception']['pct']:.1f} % ({f['gold_in_block_not_perception']['correct']}/{f['gold_in_block_not_perception']['n']}), gold on the list at {f['gold_in_perception']['pct']:.1f} %. The block persuades Perception; the list is what the Solver chooses from.")
    pt = b["pass_through_5_to_8"]
    out.append(
        f"**B. Position predicts correctness, and the step is between position 1 and everything else.** P(correct | gold at 1) is {pp[1]['pct']:.1f} % on Fold A, {pp[2]['pct']:.1f} % at 2, {b['not_top_2_to_8']['pct']:.1f} % pooled over 2-8 and {b['tail_5_to_8']['pct']:.1f} % at 5-8 "
        f"(ROLL-1 {r1['boundary']['head_1']['pct']:.1f} / {r1['boundary']['not_top_2_to_8']['pct']:.1f} / {r1['boundary']['tail_5_to_8']['pct']:.1f} %; DEV {dv['boundary']['head_1']['pct']:.1f} / {dv['boundary']['not_top_2_to_8']['pct']:.1f} / {dv['boundary']['tail_5_to_8']['pct']:.1f} %). "
        f"Gold at position 1 reaches Perception's list on {pp[1]['in_perception']}/{pp[1]['n']} Fold A rows; at 5-8 on {pt['in_perception']}/{pt['n']}. "
        f"The {w['n']} delivered-but-wrong Fold A rows sit at mean position {w['mean_pos']} against {b['correct']['mean_pos']} on intent-correct rows, only {w['gold_pos_5_to_8']} of them at 5-8 -- so they are NOT a low-position tail; they are rows where another entry held the top. "
        f"The wrong answer was itself in the block on {w['delivered_in_block']} of the {w['n']}, ABOVE gold on {w['delivered_above_gold']}, and at position 1 on {w['delivered_at_1']}. Perception shortlisted gold on {w['gold_in_perception']} of the {w['n']}, and on {w['delivered_at_1_given_gold_in_perception']} of those the Solver still took the position-1 entry over the shortlisted gold; on the other {w['n'] - w['gold_in_perception']} Perception dropped gold before the Solver saw it. "
        f"Either way the deciding property is which entry is on top, so re-ranking inside the delivered set is a lever on the {w['n']} as much as on the newly delivered rows. The same shape holds on ROLL-1 ({r1['boundary']['wrong']['delivered_at_1']}/{r1['boundary']['wrong']['n']} wrong answers at position 1) and DEV ({dv['boundary']['wrong']['delivered_at_1']}/{dv['boundary']['wrong']['n']}).")
    d, cv = g["delivered_wrong"], g["conv_roster"]
    out.append(
        f"**The agree-1 reorder acts on both populations.** Replayed offline, it moves gold UP on {d['moved_up']} of the {d['n']} delivered-but-wrong Fold A rows ({d['to_rank_1']} land at position 1; mean position {d['mean_pos_before']} -> {d['mean_pos_after']}), leaves {d['unchanged']} unchanged, moves {d['moved_down_in_block']} down inside the block and drops {d['dropped_out']} out "
        f"(ROLL-1: {r1['agree']['delivered_wrong']['moved_up']}/{r1['agree']['delivered_wrong']['n']} up, {r1['agree']['delivered_wrong']['to_rank_1']} to position 1; DEV: {dv['agree']['delivered_wrong']['moved_up']}/{dv['agree']['delivered_wrong']['n']} up, {dv['agree']['delivered_wrong']['to_rank_1']} to position 1). "
        f"It newly delivers {g['newly_all']['n']} Fold A rows: {g['newly_correct_today']} already correct without the entry, {g['newly_intent_wrong']['n']} intent-wrong today, of which {cv['n']} are the registered CONV roster (intent-wrong with gold off Perception's list, the bank's `INTENT-UNCOVERED`; the id list hashes to the registered roster: {'yes' if cv['matches_registered'] else 'NO'}), entering at positions {list(cv['entry_positions'].values())} -- {cv['at_position_1']} of {cv['n']} at position 1.")
    fixed_cells = [(arm["exemplar"]["fixed_count"][cl], arm_label) for arm_label, arm in (("roll1", r1), ("train-fold-a-plan", fa), ("dev2000-added-plan", dv)) for cl in ("1-2", "3-5")]
    pos_mono = sum(1 for block, _ in fixed_cells if monotone(block["by_first_pos"]))
    rank_mono = sum(1 for block, _ in fixed_cells if monotone(block["by_first_rank"]))
    pos_spreads = [spread(block["by_first_pos"]) for block, _ in fixed_cells]
    rank_spreads = [spread(block["by_first_rank"]) for block, _ in fixed_cells]
    cell_floor = min(min(smallest_cell(block["by_first_pos"]), smallest_cell(block["by_first_rank"])) for block, _ in fixed_cells)
    out.append(
        f"**The exemplar block: the COUNT of gold-intent exemplars is the signal; neither ordering shows a stable position effect.** Across all rows P(correct) climbs with how many of the twenty carry the gold intent ({e['by_count']['0']['pct']:.1f} % at 0 to {e['by_count']['11-20']['pct']:.1f} % at 11-20 on Fold A; the same on both other rosters), and the raw rendered-position gradient ({e['by_first_pos']['1-5']['pct']:.1f} % at 1-5, {e['by_first_pos']['16-20']['pct']:.1f} % at 16-20 on Fold A) is that count in disguise, because a row with many gold exemplars has its first one early under any ordering. "
        f"Held at a fixed count (1-2, then 3-5 gold exemplars; six roster-by-count cells, bucket sizes from {cell_floor} rows), the bucket rates move by {min(pos_spreads)}-{max(pos_spreads)} pp across rendered-position buckets and by {min(rank_spreads)}-{max(rank_spreads)} pp across retrieval-rank buckets, and they are monotone in only {pos_mono} of 6 cells for rendered position and {rank_mono} of 6 for retrieval rank -- movement of the size of the cells' own sampling noise, in no consistent direction. "
        f"Two facts stand regardless: the block is rendered in string order of value ids (`_fuse_supply_filter`, kb_policy.py:859), so the rank the retrieval computed never reaches the model; and the agreement vote, which the Solver only ever sees as an unordered pile, is the strongest single correlate of intent correctness in this table. On the entity classes the first exemplar carrying the missed type sits where it sits on correct rows: position is not the entity story.")
    c = fa["residual"]
    m, fn = c["ENTITY-MIXED"], c["ENTITY-FN-ONLY"]
    ign = m["kinds"]["ignored-available"] + m["kinds"]["ignored-unavailable"]
    out.append(
        f"**C. The entity residual splits, and copying from the supply is the smallest part.** Fold A ENTITY-MIXED, {m['items']} missed items: {m['kinds']['copied-exemplar-filler']} ({pct(m['kinds']['copied-exemplar-filler'], m['items']):.1f} %) carry a same-type filler that string-matches a supplied exemplar filler ({m['copied_span_related']} of those are also span-related to gold, so the match may be coincidence), "
        f"{m['kinds']['in-supplied-body-text']} ({pct(m['kinds']['in-supplied-body-text'], m['items']):.1f} %) a filler found only inside a supplied body's text, {m['kinds']['not-from-supply']} ({pct(m['kinds']['not-from-supply'], m['items']):.1f} %) a filler in no supplied body -- speech or invention, {m['not_from_supply_span_related']} of them span-related to gold -- "
        f"{m['kinds']['type-swapped']} ({pct(m['kinds']['type-swapped'], m['items']):.1f} %) the gold filler under another type, and {ign} ({pct(ign, m['items']):.1f} %) no filler of the type at all, {m['kinds']['ignored-available']} of them with the gold filler sitting in the supply. "
        f"ENTITY-FN-ONLY is 'ignored' by construction (no unmatched prediction exists to pair), and its informative split is {fn['kinds']['ignored-available']}/{fn['items']} with the gold filler available in the supply. ROLL-1 and DEV carry the same shape (copied {pct(r1['residual']['ENTITY-MIXED']['kinds']['copied-exemplar-filler'], r1['residual']['ENTITY-MIXED']['items']):.1f} % / {pct(dv['residual']['ENTITY-MIXED']['kinds']['copied-exemplar-filler'], dv['residual']['ENTITY-MIXED']['items']):.1f} %). "
        f"Used-but-wrong-source is one item in five at most; the residual is span boundary and omission.")
    naive = f["gold_in_block"]
    needed = (conv_receipt or {}).get("rows_needed_to_clear_the_arm_bar")
    factor = (conv_receipt or {}).get("declared_persuasion_factor")
    matched = cv["position_matched_correct_pct"]
    expected = round(cv["n"] * matched / 100.0, 1) if matched is not None else None
    out.append(
        f"**Re-aim, and the honest prior.** Presence is the wrong target once an entry is inside the block; SALIENCE is -- being the top entry of the eight decides Perception's list and, through it, the Solver's pick, on every roster. The retrieval line should be aimed at rank inside the delivered set, which the agreement term already moves, not at presence alone. The exemplar block is a different case: its rendered order is string order today, and this read finds no stable position effect at fixed count, so whether ordering it by rank buys anything is an open and cheap question rather than an evidenced lever; what that block demonstrably carries is the count of gold-intent exemplars, which is the agreement vote. "
        f"For the CONV probe the record now holds four numbers where it held a midpoint: the naive P(intent correct | gold delivered) on Fold A is {naive['pct']:.1f} % ({naive['correct']}/{naive['n']}, the complement of the {w['n']}); the flown conversion at the positions the {cv['n']} CONV rows would enter is {matched} %; gold delivered but NOT at position 1 converts at {b['not_top_2_to_8']['pct']:.1f} %; and gold on Perception's list converts at {f['gold_in_perception']['pct']:.1f} % while gold in the block but off the list converts at {f['gold_in_block_not_perception']['pct']:.1f} %. "
        f"The honest prior is the position-matched {matched} %, bounded above by {naive['pct']:.1f} % and below by the not-top rate {b['not_top_2_to_8']['pct']:.1f} %; the declared persuasion factor of {factor} sits below the whole band. It is still a prior and not a measurement, because every number above is read on rows whose cosine already ranked gold, and the CONV rows are exactly the rows where it did not. "
        f"At {matched} % the expected conversions are {expected} of {cv['n']} against the {needed} the AGREE arm needs to clear its bar, so the probe sits close to the decision it was flown to make.")
    return out


# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lock", default=DEFAULT_LOCK)
    parser.add_argument("--data-root", default=DEFAULT_DATA_ROOT)
    parser.add_argument("--markdown", default=str(REPO_ROOT / DEFAULT_MARKDOWN))
    parser.add_argument("--out", default=None)
    parser.add_argument("--skip-trace-check", action="store_true")
    args = parser.parse_args(argv)
    data_root = Path(args.data_root)
    lock = load_lock(Path(args.lock))
    diagnostic = load_rank_diagnostic()
    store = diagnostic.load_store(data_root)
    inventory = load_legal_intent_inventory(lock, data_root)
    bank = load_bank(data_root)
    contracts = load_contract_bodies(data_root)
    conv_receipt = None
    if CONV_DERIVATION.is_file():
        derivation = json.loads(CONV_DERIVATION.read_text(encoding="utf-8"))
        quantity = derivation["the_quantity_this_roster_measures"]
        conv_receipt = {"count": derivation["roster"]["count"], "id_list_sha256": derivation["roster"]["id_list_sha256"],
                        "rows_needed_to_clear_the_arm_bar": quantity["rows_needed_to_clear_the_arm_bar"],
                        "conversion_needed": quantity["conversion_needed_to_clear_the_arm_bar"],
                        "declared_persuasion_factor": quantity["arm_declared_persuasion_factor"],
                        "sha256": digest(CONV_DERIVATION), "relpath": str(CONV_DERIVATION.relative_to(REPO_ROOT))}
    gold_by_split = {"train": load_gold(lock, data_root, "train"), "devel": load_gold(lock, data_root, "devel")}
    pools = {}
    arms = {}
    for arm in ARMS:
        gold = gold_by_split[arm["split"]]
        if arm["exemplars"] not in pools:
            pools[arm["exemplars"]] = load_exemplar_pool(data_root, arm["exemplars"])
        pool = pools[arm["exemplars"]]
        population = load_population(data_root, arm, bank, gold)
        phases = load_phases(data_root, arm)
        delivered = load_delivered(phases["directory"], arm, inventory)
        trace = ({"perception_contacts": 0, "perception_order_agrees": 0, "first_solver_contacts": 0,
                  "solver_order_agrees": 0, "skipped": True} if args.skip_trace_check
                 else verify_trace(phases["directory"], arm, phases))
        queries = load_sealed_segment_vectors(data_root / arm["query"], expected_sha256=arm["query_sha"],
                                              dimensions=(diagnostic.IB_DIM,))
        cosines = diagnostic.recompute(store, queries, sorted(population["rows"]))
        derived = derive_rows(arm=arm, population=population, phases=phases, delivered=delivered, gold=gold,
                              pool=pool, contracts=contracts, cosines=cosines, own_key=diagnostic.own_key)
        rows = derived["rows"]
        boundary = boundary_position_table(rows)
        arms[arm["label"]] = {
            "title": arm["title"], "run_id": arm["run_id"], "attempt": arm["attempt"],
            "phases_relpath": phases["relpath"], "phases_sha256": phases["sha256"],
            "outputs_relpath": str((phases["directory"] / delivered["relpath"]).relative_to(data_root)),
            "outputs_sha256": delivered["sha256"], "projection_changed_rows": delivered["projection_changed_rows"],
            "pool_relpath": pool["relpath"], "pool_sha256": pool["sha256"],
            "population_source": population["source"], "population_sha256": population["sha256"],
            "phase_checks": phases["checks"], "derive_checks": derived["checks"], "trace": trace,
            "class_rows": dict(sorted(Counter(r["class"] for r in rows.values()).items())),
            "freedom": freedom_table(rows), "boundary": boundary,
            "agree": agree_table(rows, boundary["per_position"], conv_receipt if arm["label"] == "train-fold-a-plan" else None),
            "exemplar": exemplar_table(rows),
            "entity_position": entity_position_table(rows), "residual": residual_split_table(rows)}
        del phases, delivered, queries, cosines, derived, rows
    report = {"read_id": READ_ID, "recipe": RECIPE,
              "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "embedder": 0, "scorer": 0,
                           "network": 0, "gpu": 0, "paid_api": 0},
              "bank_sha256": bank["sha256"], "contracts_sha256": contracts["sha256"],
              "gold_rows": {k: v["rows"] for k, v in gold_by_split.items()},
              "agree_weight": AGREE_WEIGHT, "conv_receipt": conv_receipt, "arms": arms}
    report["reading"] = reading(arms, conv_receipt)
    out = Path(args.out) if args.out else data_root / DEFAULT_ANALYSIS_DIR / "report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    write_markdown(Path(args.markdown), report)
    print("wrote", out)
    print("wrote", args.markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
