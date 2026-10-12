#!/usr/bin/env python3
"""Node information-gain ledger of the current best SLURP system on TRAIN Fold A.

Owner principle (2026-09-28): every node must produce an effective information
gain; where a node does not, it is redesigned or supplemented.  Intent and slots
are treated separately.  This read measures, per row and per gold entity item,
the state of the gold answer after every node of the flown program
``phase-native-candidates-review-revise-v1`` and the gain or loss each node
contributes, on two sealed flights of the SAME plan bytes:

* primary   ``SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1`` (the AGREE arm);
* replicate ``SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1`` (the wave A/A: the same
  bytes re-flown), used to show which node gains are stable.

Nodes in flight order (read from the sealed phase records and the trace):

  B  boundary block   -- ``initial_query_state.retrieved_value_ids``: the 8
                         intent-boundary entries retrieved BEFORE Perception
                         (Perception's only supplied evidence);
  P  Perception       -- ``agent_states`` kind ``phase:perception``: the
                         ``slurp-intent-hypotheses-v1`` note (1-3 candidates:
                         intent_id, distinction, evidence_refs, unresolved_fields);
  K  knowledge wave 0 -- the fused supply acquired after Perception: 20
                         annotated train exemplars + the slot-contract cards;
  S1 Solver (first)   -- the first ``phase:solver`` state;
  R  Reviewer/Planner -- ``phase:reviewer`` + ``phase:planner`` and the
                         ``planner_routes`` receipt; on REVISE a second Solver
                         state follows (S2 = the last Solver state);
  D  delivery         -- the sealed ``outputs.jsonl`` text (after the deliver
                         normaliser), the bytes the official scorer read.

Access pattern (copied from the 2026-09-27 error-source read,
``scripts/analysis/slurp_agree_arm_error_sources.py``, which this script imports
unchanged): sealed phases through ``GP.load_phases``, outputs through
``ES.load_outputs`` (``parse_slu_response`` on the delivered text), scores through
``ES.load_scores``, gold OFFLINE through ``ES.load_gold`` (``data.slurp.
load_slurp_split`` on the governed TRAIN split), the entity item classes through
``ES.entity_items`` (FORMAT / BOUNDARY / NEAR / WRONG-VALUE / WRONG-TYPE / MISSING /
SPURIOUS).  "Delivered knowledge contains the gold value" uses the W5 estimate's
method (``scripts/analysis/slurp_w5_fold_a_offline_estimate.py``:
``printed_pairs`` over the pinned M1 exemplar snapshot, restricted to the row's
rendered exemplars).  The trace pass mirrors ``GP.verify_trace``.

Gold discipline: gold reaches no query, key, selector, config or runtime; this
script writes an analysis report and nothing else.  Text discipline: no
utterance text, transcript, gold label value, filler, tool argument, Perception
note or model output is printed or persisted -- only ids, counts, ranks, rates,
intent/slot TYPE names, class names and hashes.  Zero model, server, tokenizer,
encoder, embedder, scorer-subprocess, network and GPU contacts.

Deterministic apart from ``generated_at``; the paired row bootstrap
(``analysis.bootstrap.paired_cluster_bootstrap``, seed 20260807, 10,000
replicates, 95 % percentile CI) is seeded.  ``--check`` re-derives and compares.

    PYTHONDONTWRITEBYTECODE=1 python scripts/analysis/slurp_node_gain_ledger.py \\
        --data-root "$SPEECHRL_DATA_DIR" \\
        --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
"""

from __future__ import annotations
import os

import argparse
import hashlib
import importlib.util
import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT / "src"), str(REPO_ROOT / "scripts" / "analysis")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from speech_aware_evidence_acquisition.analysis.bootstrap import paired_cluster_bootstrap  # noqa: E402
from speech_aware_evidence_acquisition.data.lock import load_lock  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import parse_slu_response  # noqa: E402
from speech_aware_evidence_acquisition.analysis.sealed_credit.entity_states import (  # noqa: E402
    NEAR_THRESHOLD,
    PARTIAL_STOP,
    gold_item_states,
    note_state,
)
# note_state/gold_item_states/NEAR_THRESHOLD/PARTIAL_STOP are the lifted primitives (design spec
# 2026-09-29, sealed-credit inner loop, task 2): imported under their original names so every call
# site below is unchanged and ``--check`` reproduces the sealed report byte-for-byte.

READ_ID = "SLURP-NODE-GAIN-LEDGER-FOLD-A-V1"
RECIPE = "slurp-node-information-gain-ledger-v1"
ANALYSIS_DIR = "analysis/" + READ_ID
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
PROGRAM = "phase-native-candidates-review-revise-v1"
ROWS = 1080
BOOT_SEED = 20260807
BOOT_N = 10_000
BOOT_LEVEL = 0.95
# NEAR_THRESHOLD / PARTIAL_STOP are imported from analysis.sealed_credit.entity_states (unchanged).

ARMS = (
    {"label": "agree", "title": "AGREE (primary)", "run_id": "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1",
     "attempt": "attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1", "trace": True},
    {"label": "wave_aa", "title": "wave A/A (replicate, same bytes re-flown)",
     "run_id": "SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1",
     "attempt": "attempt-slurp-native-stage3-wave1-aa-fold-a-generation-v1", "trace": True},
)
GOLD_KINDS = ("EXACT", "FORMAT", "BOUNDARY", "NEAR", "WRONG-VALUE", "WRONG-TYPE", "MISSING")
NOTE_STATES = ("CONTIGUOUS", "NEAR", "PARTIAL", "ABSENT")
RELISTEN_KINDS = ("BOUNDARY", "NEAR", "FORMAT")


class ReadError(RuntimeError):
    pass


def import_path(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ES = import_path(REPO_ROOT / "scripts/analysis/slurp_agree_arm_error_sources.py", "slurp_agree_arm_error_sources")
W5 = import_path(REPO_ROOT / "scripts/analysis/slurp_w5_fold_a_offline_estimate.py", "slurp_w5_fold_a_offline_estimate")
GP = ES.GP
RD = ES.RD


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pct(num, den) -> float:
    return round(100.0 * num / den, 2) if den else 0.0


# ---------------------------------------------------------------------------
# sealed node states


def parse_answer(text: str) -> dict:
    scenario, action, entities, parsed = parse_slu_response(text or "")
    return {"parsed": bool(parsed),
            "intent": f"{scenario}_{action}" if parsed and scenario is not None and action is not None else None,
            "entities": tuple(ES.SlotEntity(e.type, e.filler) for e in entities)}


def load_node_states(data_root: Path, arm: dict) -> dict:
    """Per row: Perception note (candidate ids + canonical note tokens, in memory
    only), every Solver answer, the Planner routes, the visited roles, and the
    deliver normaliser receipt."""

    directory = data_root / "runs" / arm["run_id"] / arm["attempt"]
    path = directory / f"{arm['run_id']}.phases.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("policy") != PROGRAM:
        raise ReadError(f"{arm['label']}: program is {document.get('policy')!r}, not {PROGRAM}")
    rows, checks = {}, Counter()
    for result in document["phases"][0]["results"]:
        sid = result["sample_id"]
        perception, solvers, kinds = None, [], []
        for state in result.get("agent_states") or ():
            kind = state.get("state_kind")
            kinds.append(kind)
            if kind == "phase:perception" and perception is None:
                payload = json.loads(state.get("content") or "")
                parts, ids = [], []
                for cand in payload.get("candidates") or ():
                    ids.append(str(cand.get("intent_id")))
                    parts.append(str(cand.get("distinction") or ""))
                    parts.extend(str(u) for u in cand.get("unresolved_fields") or ())
                    checks["perception_evidence_refs_nonempty"] += int(bool(cand.get("evidence_refs")))
                perception = {"ids": ids, "tokens": ES.canonical(" ".join(parts)).split()}
            elif kind == "phase:solver":
                solvers.append(parse_answer(state.get("content") or ""))
        receipt = result.get("native_episode_receipt") or {}
        routes = [r.get("action") for r in receipt.get("planner_routes") or ()]
        normaliser = receipt.get("deliver_normaliser") or {}
        final_text = result.get("final_response_text") or ""
        last_solver_text = next((s.get("content") for s in reversed(result.get("agent_states") or ())
                                 if s.get("state_kind") == "phase:solver"), None)
        checks["rows"] += 1
        checks["last_solver_state_equals_final_response_text"] += int(last_solver_text == final_text)
        checks["perception_state_present"] += int(perception is not None)
        rows[sid] = {"perception": perception, "solvers": solvers, "routes": routes,
                     "reviewer_visited": "phase:reviewer" in kinds,
                     "normaliser_changed": bool(normaliser.get("changed")),
                     "normaliser_labels_changed": bool(normaliser.get("labels_changed")),
                     "normaliser_fillers_changed": bool(normaliser.get("fillers_changed"))}
    del document
    return {"rows": rows, "checks": dict(sorted(checks.items())), "sha256": digest(path),
            "relpath": str(path.relative_to(data_root))}


def trace_pass(directory: Path, arm: dict, phases: dict) -> dict:
    """Mirror of ``GP.verify_trace`` (Perception and first-Solver supplied-evidence
    order against the sealed query state), extended with what each role receives:
    speech feature parts and the history state kinds.  Ids and counts only."""

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
            role = key.rsplit(":", 1)[-1]
            sample_id = payload.get("sample_id")
            row = phases["rows"].get(sample_id)
            if row is None:
                continue
            counts[f"{role}.contacts"] += 1
            counts[f"{role}.speech_feature_parts_present"] += int(bool(payload.get("speech_feature_parts")))
            counts[f"{role}.mmproj_loaded"] += int(bool(payload.get("mmproj_loaded")))
            history = {str(h.get("state_kind")) for h in payload.get("history") or ()}
            counts[f"{role}.history_carries_perception_note"] += int("phase:perception" in history)
            ids = [item.get("evidence_id") for item in payload.get("supplied_evidence") or ()]
            counts[f"{role}.supplied_exemplars_present"] += int(any(str(i).startswith(GP.EX_PREFIX) for i in ids))
            if role == "perception":
                counts["perception_order_agrees"] += int([i.split(GP.IB_PREFIX, 1)[-1] for i in ids] == row["boundary"])
                counts["perception_supplied_only_boundaries"] += int(all(str(i).startswith(GP.IB_PREFIX) for i in ids))
            elif role == "solver" and sample_id not in seen_solver:
                seen_solver.add(sample_id)
                counts["first_solver_order_agrees"] += int(row["solver_ids"] is not None and ids == row["solver_ids"])
    return {"relpath": path.name, **dict(sorted(counts.items()))}


# ---------------------------------------------------------------------------
# per-row / per-item derivation
#
# note_state / gold_item_states are imported from analysis.sealed_credit.entity_states (design spec
# 2026-09-29, sealed-credit inner loop, task 2); both are byte-identical to the versions this module
# used to define locally (they called ES.canonical / ES.contiguous_in / ES.norm_distance / ES.entity_items,
# which are the exact functions entity_states now re-exports under the same names).


def vote_rank(votes: Counter, intent: str):
    if votes.get(intent, 0) == 0:
        return None
    return 1 + sum(1 for v in votes.values() if v > votes[intent])


def derive_arm(arm: dict, gold: dict, ids: list, pool: dict, m1_values: dict) -> dict:
    phases, nodes, outs, scores = arm["phases"], arm["nodes"], arm["outputs"], arm["scores"]
    m1_by_key = {vid.split("value:", 1)[-1]: v for vid, v in m1_values.items()}
    rows, items, checks = {}, [], Counter()
    for sid in ids:
        g = gold[sid]
        gi = g["intent"]
        ph, nd, out = phases[sid], nodes[sid], outs[sid]
        block = ph["boundary"]
        perc = nd["perception"]["ids"] if nd["perception"] else []
        votes = Counter()
        own = RD.own_key(sid)
        for key in ph["ex_rendered"]:
            intent = pool["values"].get(key, {}).get("intent")
            if intent is not None:
                votes[intent] += 1
        s1 = nd["solvers"][0] if nd["solvers"] else {"parsed": False, "intent": None, "entities": ()}
        s2 = nd["solvers"][-1] if nd["solvers"] else s1
        delivered_ok = bool(scores[sid]["scenario_action_exact"])
        checks["delivered_parse_intent_agrees_with_sealed"] += int((out["intent"] == gi) == delivered_ok)
        checks["own_exemplar_rendered"] += int(own is not None and own in ph["ex_rendered"])
        checks["exemplar_keys_unresolved_in_m1_snapshot"] += sum(1 for k in ph["ex_rendered"] if k not in m1_by_key)
        total_votes = sum(votes.values())
        entropy = -sum((c / total_votes) * math.log2(c / total_votes) for c in votes.values()) if total_votes else 0.0
        row = {
            "block_n": len(block), "block_pos": block.index(gi) + 1 if gi in block else None,
            "perc_n": len(perc), "perc_rank": perc.index(gi) + 1 if gi in perc else None,
            "perc_first_in_block": bool(perc) and perc[0] in block,
            "ex_gold_votes": votes.get(gi, 0), "ex_gold_rank": vote_rank(votes, gi),
            "ex_distinct_intents": len(votes), "ex_entropy_bits": entropy,
            "ex_gold_share": votes.get(gi, 0) / total_votes if total_votes else 0.0,
            "s1_parsed": s1["parsed"], "s1_ok": s1["intent"] == gi, "s1_intent_in_perc": s1["intent"] in perc,
            "s2_ok": s2["intent"] == gi, "revised": len(nd["solvers"]) > 1,
            "s1_intent": s1["intent"], "s2_intent": s2["intent"],
            "s1_entities_hash": hashlib.sha256(repr(sorted((e.type, e.filler) for e in s1["entities"])).encode("utf-8")).hexdigest(),
            "s2_entities_hash": hashlib.sha256(repr(sorted((e.type, e.filler) for e in s2["entities"])).encode("utf-8")).hexdigest(),
            "routes": nd["routes"], "reviewer_visited": nd["reviewer_visited"],
            "d_ok": delivered_ok, "d_parsed": out["parsed"],
            "normaliser_changed": nd["normaliser_changed"],
            "normaliser_labels_changed": nd["normaliser_labels_changed"],
            "catch_all": gi in ES.CATCH_ALL,
        }
        # slots
        tokens = nd["perception"]["tokens"] if nd["perception"] else []
        printed = set()
        for key in ph["ex_rendered"]:
            value = m1_by_key.get(key)
            if value is not None:
                printed |= W5.printed_pairs(value.content)
        cards = set(ph["contracts"])
        st1, sp1 = gold_item_states(g["entities"], s1["entities"])
        st2, sp2 = gold_item_states(g["entities"], s2["entities"])
        std, spd = gold_item_states(g["entities"], out["entities"])
        row["spurious"] = {"s1": len(sp1), "s2": len(sp2), "d": len(spd)}
        row["spurious_d_heard"] = sum(
            1 for pi in spd if ES.contiguous_in(ES.canonical(out["entities"][pi].filler).split(), tokens))
        row["slu_counts"] = {"s1": ES.slu_counts(g["entities"], s1["entities"]),
                             "s2": ES.slu_counts(g["entities"], s2["entities"]),
                             "d": ES.slu_counts(g["entities"], out["entities"])}
        for index, entity in enumerate(g["entities"]):
            items.append({
                "sample_id": sid, "gold_index": index, "type": entity.type,
                "note": note_state(entity.filler, tokens),
                "k_value_printed": (entity.type, ES.fold(entity.filler)) in printed,
                "k_value_printed_any_type": any(v == ES.fold(entity.filler) for _, v in printed),
                "k_type_card": entity.type in cards,
                "s1": st1[index], "s2": st2[index], "d": std[index],
                "intent_ok": delivered_ok, "revised": row["revised"]})
        rows[sid] = row
    return {"rows": rows, "items": items, "checks": dict(sorted(checks.items()))}


# ---------------------------------------------------------------------------
# aggregation: intent


def rank_bucket(r) -> str:
    return "absent" if r is None else "1" if r == 1 else "2" if r == 2 else "3+"


def pos_bucket(p) -> str:
    return "absent" if p is None else "1" if p == 1 else "2-3" if p <= 3 else "4-8"


INTENT_NODES = (
    ("B", "boundary block (before Perception)", lambda r: r["block_pos"] == 1, lambda r: r["block_pos"] is not None),
    ("P", "Perception note", lambda r: r["perc_rank"] == 1, lambda r: r["perc_rank"] is not None),
    ("K", "exemplar supply (20, vote)", lambda r: r["ex_gold_rank"] == 1, lambda r: r["ex_gold_votes"] > 0),
    ("S1", "Solver first answer", lambda r: r["s1_ok"], lambda r: r["s1_ok"]),
    ("R", "after Reviewer/Planner", lambda r: r["s2_ok"], lambda r: r["s2_ok"]),
    ("D", "delivered (sealed, scored)", lambda r: r["d_ok"], lambda r: r["d_ok"]),
)
DECISION_EDGES = (("B", "P"), ("P", "S1"), ("S1", "R"), ("R", "D"))


def intent_ledger(rows: dict, ids: list) -> dict:
    node = {code: (title, top, present) for code, title, top, present in INTENT_NODES}
    states = {}
    for code, title, top, present in INTENT_NODES:
        states[code] = {"title": title, "gold_top1": sum(top(rows[s]) for s in ids),
                        "gold_present": sum(present(rows[s]) for s in ids)}
    states["B"]["mean_set_size"] = round(sum(rows[s]["block_n"] for s in ids) / len(ids), 3)
    states["B"]["mean_log2_set_size_bits"] = round(sum(math.log2(max(rows[s]["block_n"], 1)) for s in ids) / len(ids), 3)
    states["P"]["mean_set_size"] = round(sum(rows[s]["perc_n"] for s in ids) / len(ids), 3)
    states["P"]["set_size_distribution"] = dict(sorted(Counter(rows[s]["perc_n"] for s in ids).items()))
    states["P"]["mean_log2_set_size_bits"] = round(sum(math.log2(max(rows[s]["perc_n"], 1)) for s in ids) / len(ids), 3)
    states["K"]["mean_vote_entropy_bits"] = round(sum(rows[s]["ex_entropy_bits"] for s in ids) / len(ids), 3)
    states["K"]["mean_distinct_intents"] = round(sum(rows[s]["ex_distinct_intents"] for s in ids) / len(ids), 3)
    present_k = [s for s in ids if rows[s]["ex_gold_votes"] > 0]
    states["K"]["mean_gold_surprisal_bits_when_present"] = round(
        sum(-math.log2(rows[s]["ex_gold_share"]) for s in present_k) / len(present_k), 3) if present_k else None
    for code in ("S1", "R", "D"):
        states[code]["mean_log2_set_size_bits"] = 0.0
    edges = {}
    for a, b in DECISION_EDGES:
        _, top_a, pres_a = node[a]
        _, top_b, pres_b = node[b]
        c = Counter()
        for s in ids:
            ta, tb = top_a(rows[s]), top_b(rows[s])
            c["top1_improves"] += int(not ta and tb)
            c["top1_worsens"] += int(ta and not tb)
            c["top1_stays_right"] += int(ta and tb)
            c["top1_stays_wrong"] += int(not ta and not tb)
            pa, pb = pres_a(rows[s]), pres_b(rows[s])
            c["presence_gained"] += int(not pa and pb)
            c["presence_lost"] += int(pa and not pb)
            c["present_at_a"] += int(pa)
            c["present_at_a_and_top1_at_b"] += int(pa and tb)
        c["net_top1_gain"] = c["top1_improves"] - c["top1_worsens"]
        c["conversion_top1_b_given_present_a_pct"] = pct(c["present_at_a_and_top1_at_b"], c["present_at_a"])
        edges[f"{a}->{b}"] = dict(sorted(c.items()))
    # conversions
    conv = {}
    by_pos = defaultdict(Counter)
    by_rank = defaultdict(Counter)
    for s in ids:
        r = rows[s]
        pb = pos_bucket(r["block_pos"])
        by_pos[pb]["rows"] += 1
        by_pos[pb]["perception_lists_gold"] += int(r["perc_rank"] is not None)
        by_pos[pb]["perception_rank1"] += int(r["perc_rank"] == 1)
        by_pos[pb]["solver_first_correct"] += int(r["s1_ok"])
        by_pos[pb]["delivered_correct"] += int(r["d_ok"])
        rb = rank_bucket(r["perc_rank"])
        by_rank[rb]["rows"] += 1
        by_rank[rb]["solver_first_correct"] += int(r["s1_ok"])
        by_rank[rb]["solver_answer_on_list"] += int(r["s1_intent_in_perc"])
        by_rank[rb]["delivered_correct"] += int(r["d_ok"])
        by_rank[rb]["gold_in_block"] += int(r["block_pos"] is not None)
    conv["by_block_position"] = {k: dict(sorted(v.items())) for k, v in sorted(by_pos.items())}
    conv["by_perception_rank"] = {k: dict(sorted(v.items())) for k, v in sorted(by_rank.items())}
    by_k = defaultdict(Counter)
    for s in ids:
        r = rows[s]
        kb = "0 votes" if r["ex_gold_votes"] == 0 else "top vote" if r["ex_gold_rank"] == 1 else "outvoted"
        on = "on list" if r["perc_rank"] is not None else "off list"
        by_k[f"{on} / {kb}"]["rows"] += 1
        by_k[f"{on} / {kb}"]["solver_first_correct"] += int(r["s1_ok"])
    conv["by_list_and_exemplar_vote"] = {k: dict(sorted(v.items())) for k, v in sorted(by_k.items())}
    rp = Counter()
    for s in ids:
        r = rows[s]
        rp["reviewer_visited"] += int(r["reviewer_visited"])
        rp["route_revise_any"] += int("REVISE" in r["routes"])
        rp["revised_solver_rows"] += int(r["revised"])
        rp["revised_changed_correctness"] += int(r["revised"] and r["s1_ok"] != r["s2_ok"])
        rp["revised_intent_changed"] += int(r["revised"] and r["s1_intent"] != r["s2_intent"])
        rp["revised_entities_changed"] += int(r["revised"] and r["s1_entities_hash"] != r["s2_entities_hash"])
        rp["revised_wrong_to_right"] += int(r["revised"] and not r["s1_ok"] and r["s2_ok"])
        rp["revised_right_to_wrong"] += int(r["revised"] and r["s1_ok"] and not r["s2_ok"])
        rp["accepted_first_answer_while_wrong"] += int(not r["revised"] and r["reviewer_visited"] and not r["s1_ok"])
        rp["accepted_first_answer_while_right"] += int(not r["revised"] and r["reviewer_visited"] and r["s1_ok"])
        rp["revise_on_wrong_first"] += int(r["revised"] and not r["s1_ok"])
        rp["revise_on_right_first"] += int(r["revised"] and r["s1_ok"])
        rp["normaliser_changed_rows"] += int(r["normaliser_changed"])
        rp["normaliser_labels_changed_rows"] += int(r["normaliser_labels_changed"])
    conv["reviewer_planner"] = dict(sorted(rp.items()))
    wrong = [s for s in ids if not rows[s]["d_ok"]]
    sizing = Counter()
    for s in wrong:
        r = rows[s]
        rb = rank_bucket(r["perc_rank"])
        sizing[f"perception_rank_{rb}"] += 1
        if rb == "absent":
            sizing["absent_but_in_block" if r["block_pos"] is not None else "absent_not_in_block"] += 1
        if rb in ("1", "2"):
            sizing[f"perception_rank_{rb}_perc_size_{r['perc_n']}"] += 1
        sizing["catch_all_gold"] += int(r["catch_all"])
        sizing["unparsed"] += int(not r["d_parsed"])
    sizing["intent_wrong_rows"] = len(wrong)
    return {"states": states, "edges": edges, "conversions": conv, "top2_sizing": dict(sorted(sizing.items()))}


# ---------------------------------------------------------------------------
# aggregation: slots


def slot_ledger(rows: dict, items: list, ids: list) -> dict:
    out = {}
    node_dist = {}
    for node in ("s1", "s2", "d"):
        dist = Counter(i[node] for i in items)
        totals = [sum(rows[s]["slu_counts"][node][k] for s in ids) for k in range(3)]
        node_dist[node] = {"states": {k: dist.get(k, 0) for k in GOLD_KINDS},
                           "spurious": sum(rows[s]["spurious"][node] for s in ids),
                           "slu_f1_micro": round(ES.micro_f1(totals), 2)}
    out["gold_items"] = len(items)
    out["node_states"] = node_dist
    out["note_states"] = {k: sum(1 for i in items if i["note"] == k) for k in NOTE_STATES}
    note_conv = {}
    for k in NOTE_STATES:
        sub = [i for i in items if i["note"] == k]
        note_conv[k] = {"items": len(sub), "s1_exact": sum(i["s1"] == "EXACT" for i in sub),
                        "d_exact": sum(i["d"] == "EXACT" for i in sub),
                        "d_kinds": dict(sorted(Counter(i["d"] for i in sub).items()))}
    out["note_to_solver_conversion"] = note_conv
    kc = {}
    for label, pred in (("gold value printed (type + value)", lambda i: i["k_value_printed"]),
                        ("value printed under another type only", lambda i: not i["k_value_printed"] and i["k_value_printed_any_type"]),
                        ("value not printed", lambda i: not i["k_value_printed_any_type"])):
        sub = [i for i in items if pred(i)]
        kc[label] = {"items": len(sub), "type_card_delivered": sum(i["k_type_card"] for i in sub),
                     "s1_exact": sum(i["s1"] == "EXACT" for i in sub), "d_exact": sum(i["d"] == "EXACT" for i in sub)}
    out["knowledge_to_solver_conversion"] = kc
    out["type_card_delivered_items"] = sum(i["k_type_card"] for i in items)
    for a, b in (("s1", "s2"), ("s2", "d"), ("s1", "d")):
        table = {}
        for kind in GOLD_KINDS:
            sub = [i for i in items if i[a] == kind]
            c = Counter()
            for i in sub:
                if i[a] == i[b]:
                    c["unchanged"] += 1
                elif i[b] == "EXACT":
                    c["repaired"] += 1
                elif kind == "EXACT":
                    c["broken"] += 1
                else:
                    c["changed_kind"] += 1
            table[kind] = {"items": len(sub), **{k: c.get(k, 0) for k in ("repaired", "broken", "changed_kind", "unchanged")}}
        out[f"edge_{a}_to_{b}"] = table
    out["spurious_edges"] = {
        "s1": sum(rows[s]["spurious"]["s1"] for s in ids), "s2": sum(rows[s]["spurious"]["s2"] for s in ids),
        "d": sum(rows[s]["spurious"]["d"] for s in ids),
        "d_spurious_filler_contiguous_in_note": sum(rows[s]["spurious_d_heard"] for s in ids)}
    # origin split of the delivered gold-side errors
    errs = [i for i in items if i["d"] != "EXACT"]
    origin = defaultdict(Counter)

    def origin_of(i) -> str:
        # precedence: an item right at the Solver's first answer and wrong at delivery was introduced later;
        # otherwise the Perception note decides whether the error was already visible upstream
        if i["s1"] == "EXACT":
            return ("consumption: broken at Reviewer/Planner revision" if i["s2"] != "EXACT"
                    else "consumption: broken at delivery normaliser")
        if i["note"] == "CONTIGUOUS":
            return "consumption: note carries the gold span, Solver first answer wrong"
        if i["note"] in ("NEAR", "PARTIAL"):
            return f"hearing/span: note carries a {i['note'].lower()} form"
        return "undetermined: note silent (value absent from the note)"

    for i in errs:
        where = origin_of(i)
        i["origin"] = where
        origin[where][i["d"]] += 1
        origin[where]["_all"] += 1
    out["origin_split"] = {k: dict(sorted(v.items())) for k, v in sorted(origin.items())}
    out["origin_totals"] = {
        "delivered_gold_side_errors": len(errs),
        "hearing_span_visible_near_or_partial": sum(1 for i in errs if i["origin"].startswith("hearing")),
        "undetermined_note_silent": sum(1 for i in errs if i["origin"].startswith("undetermined")),
        "consumption_origin": sum(1 for i in errs if i["origin"].startswith("consumption")),
        "consumption_origin_at_solver": sum(1 for i in errs if i["origin"].startswith("consumption: note")),
        "consumption_origin_introduced_after_solver": sum(1 for i in errs if i["origin"].startswith("consumption: broken")),
        "consumption_origin_value_printed_in_knowledge": sum(1 for i in errs if i["origin"].startswith("consumption")
                                                             and i["k_value_printed"]),
        "base_rate_delivered_exact_items_contiguous_in_note": sum(1 for i in items if i["d"] == "EXACT" and i["note"] == "CONTIGUOUS"),
        "base_rate_delivered_exact_items": sum(1 for i in items if i["d"] == "EXACT")}
    rl = Counter()
    for i in errs:
        if i["d"] in RELISTEN_KINDS:
            rl[f"{i['d']}.{'contiguous_in_note' if i['note'] == 'CONTIGUOUS' else 'not_contiguous'}"] += 1
            rl["contiguous_in_note" if i["note"] == "CONTIGUOUS" else "not_contiguous"] += 1
            rl[f"not_contiguous.{i['note']}"] += int(i["note"] != "CONTIGUOUS")
    out["relisten_addressable"] = dict(sorted(rl.items()))
    out["by_type_delivered_errors"] = {t: dict(sorted(Counter(i["note"] for i in errs if i["type"] == t).items()))
                                       for t, _ in Counter(i["type"] for i in errs).most_common(10)}
    return out


# ---------------------------------------------------------------------------
# replicate stability and bootstrap


def boot(ids: list, values: dict) -> dict:
    result = paired_cluster_bootstrap(sample_ids=ids, statistic=lambda xs: 100.0 * sum(values[x] for x in xs) / len(xs),
                                      n_replicates=BOOT_N, seed=BOOT_SEED, ci_level=BOOT_LEVEL)
    return {"point_pp": round(result.point_estimate, 2), "ci95": [round(result.ci_low, 2), round(result.ci_high, 2)]}


def boot_f1(ids: list, counts_a: dict, counts_b: dict) -> dict:
    def stat(xs):
        ta = [sum(counts_a[x][k] for x in xs) for k in range(3)]
        tb = [sum(counts_b[x][k] for x in xs) for k in range(3)]
        return ES.micro_f1(tb) - ES.micro_f1(ta)
    result = paired_cluster_bootstrap(sample_ids=ids, statistic=stat, n_replicates=BOOT_N, seed=BOOT_SEED,
                                      ci_level=BOOT_LEVEL)
    return {"point_pp": round(result.point_estimate, 2), "ci95": [round(result.ci_low, 2), round(result.ci_high, 2)]}


def stability(derived: dict, ids: list) -> dict:
    a, b = derived["agree"]["rows"], derived["wave_aa"]["rows"]
    node = {code: top for code, _, top, _ in INTENT_NODES}
    out = {"intent_edges_rows_in_both": {}, "intent_node_rate_difference_agree_minus_wave_aa": {},
           "intent_edge_net_gain_within_arm": {}}
    for x, y in DECISION_EDGES:
        c = Counter()
        for s in ids:
            ia = (not node[x](a[s])) and node[y](a[s])
            ib = (not node[x](b[s])) and node[y](b[s])
            wa = node[x](a[s]) and not node[y](a[s])
            wb = node[x](b[s]) and not node[y](b[s])
            c["improves_agree"] += int(ia)
            c["improves_wave_aa"] += int(ib)
            c["improves_both"] += int(ia and ib)
            c["worsens_agree"] += int(wa)
            c["worsens_wave_aa"] += int(wb)
            c["worsens_both"] += int(wa and wb)
        out["intent_edges_rows_in_both"][f"{x}->{y}"] = dict(sorted(c.items()))
        for label, rows in (("agree", a), ("wave_aa", b)):
            values = {s: int(node[y](rows[s])) - int(node[x](rows[s])) for s in ids}
            out["intent_edge_net_gain_within_arm"][f"{label}:{x}->{y}"] = boot(ids, values)
    for code, _, top, _ in INTENT_NODES:
        values = {s: int(top(a[s])) - int(top(b[s])) for s in ids}
        out["intent_node_rate_difference_agree_minus_wave_aa"][code] = boot(ids, values)
    # slot: SLU-F1 node gains within arm and item-level stability of delivered errors
    slot = {}
    for label in ("agree", "wave_aa"):
        rows = derived[label]["rows"]
        s1 = {s: rows[s]["slu_counts"]["s1"] for s in ids}
        s2 = {s: rows[s]["slu_counts"]["s2"] for s in ids}
        d = {s: rows[s]["slu_counts"]["d"] for s in ids}
        slot[f"{label}:S1->R"] = boot_f1(ids, s1, s2)
        slot[f"{label}:R->D"] = boot_f1(ids, s2, d)
    slot["D agree minus wave_aa"] = boot_f1(ids, {s: b[s]["slu_counts"]["d"] for s in ids},
                                           {s: a[s]["slu_counts"]["d"] for s in ids})
    out["slot_f1_node_gain"] = slot
    ia = {(i["sample_id"], i["gold_index"]): i for i in derived["agree"]["items"]}
    ib = {(i["sample_id"], i["gold_index"]): i for i in derived["wave_aa"]["items"]}
    c = Counter()
    for key, i in ia.items():
        j = ib[key]
        if i["d"] != "EXACT":
            c["agree_delivered_errors"] += 1
            c["also_error_in_wave_aa"] += int(j["d"] != "EXACT")
            c["same_kind_in_wave_aa"] += int(j["d"] == i["d"])
            c["same_note_state_in_wave_aa"] += int(j["note"] == i["note"])
        c["note_state_agrees_all_items"] += int(i["note"] == j["note"])
        c["items"] += 1
    out["slot_item_stability"] = dict(sorted(c.items()))
    return out


# ---------------------------------------------------------------------------
# markdown


def md_table(header: list, rows: list) -> str:
    lines = ["| " + " | ".join(str(h) for h in header) + " |",
             "| " + " | ".join("---" if i == 0 else "---:" for i in range(len(header))) + " |"]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


def ci(cell) -> str:
    return f"{cell['point_pp']:+.2f} [{cell['ci95'][0]:+.2f}, {cell['ci95'][1]:+.2f}]"


def render(report: dict) -> str:
    A = report["arms"]
    out = [f"# {READ_ID} tables", "", f"Generated `{report['generated_at']}`. Counts only; 1 row = 0.0926 pp.", ""]
    out += ["## Intent: node states", ""]
    hdr = ["node", "agree gold top-1", "agree gold present", "wave A/A gold top-1", "wave A/A gold present",
           "agree mean log2 set size (bits)", "top-1 rate agree minus wave A/A pp [95 % CI]"]
    rows = []
    for code, title, _, _ in INTENT_NODES:
        sa, sb = A["agree"]["intent"]["states"][code], A["wave_aa"]["intent"]["states"][code]
        bits = sa.get("mean_log2_set_size_bits", sa.get("mean_vote_entropy_bits", ""))
        rows.append([f"{code} {title}", sa["gold_top1"], sa["gold_present"], sb["gold_top1"], sb["gold_present"],
                     bits, ci(report["stability"]["intent_node_rate_difference_agree_minus_wave_aa"][code])])
    out += [md_table(hdr, rows), ""]
    out += ["## Intent: decision-edge gains (gold top-1 status)", ""]
    hdr = ["edge", "arm", "improves", "worsens", "stays right", "stays wrong", "net", "net pp [95 % CI]",
           "presence lost", "presence gained", "P(top-1 at b | present at a) %"]
    rows = []
    for x, y in DECISION_EDGES:
        e = f"{x}->{y}"
        for label in ("agree", "wave_aa"):
            c = A[label]["intent"]["edges"][e]
            rows.append([e, label, c["top1_improves"], c["top1_worsens"], c["top1_stays_right"], c["top1_stays_wrong"],
                         c["net_top1_gain"], ci(report["stability"]["intent_edge_net_gain_within_arm"][f"{label}:{e}"]),
                         c["presence_lost"], c["presence_gained"], c["conversion_top1_b_given_present_a_pct"]])
    out += [md_table(hdr, rows), ""]
    hdr = ["edge", "improves agree", "improves wave A/A", "improves in both", "worsens agree", "worsens wave A/A",
           "worsens in both"]
    out += [md_table(hdr, [[e, c["improves_agree"], c["improves_wave_aa"], c["improves_both"], c["worsens_agree"],
                            c["worsens_wave_aa"], c["worsens_both"]]
                           for e, c in report["stability"]["intent_edges_rows_in_both"].items()]), ""]
    for label in ("agree", "wave_aa"):
        conv = A[label]["intent"]["conversions"]
        out += [f"### Conversions ({label})", ""]
        out += [md_table(["gold block position", "rows", "Perception lists gold", "Perception rank 1",
                          "Solver first correct", "delivered correct"],
                         [[k, v["rows"], v["perception_lists_gold"], v["perception_rank1"], v["solver_first_correct"],
                           v["delivered_correct"]] for k, v in conv["by_block_position"].items()]), ""]
        out += [md_table(["gold Perception rank", "rows", "gold in block", "Solver first correct",
                          "Solver answer on the list", "delivered correct", "P(Solver correct) %"],
                         [[k, v["rows"], v["gold_in_block"], v["solver_first_correct"], v["solver_answer_on_list"],
                           v["delivered_correct"], pct(v["solver_first_correct"], v["rows"])]
                          for k, v in conv["by_perception_rank"].items()]), ""]
        out += [md_table(["list / exemplar vote", "rows", "Solver first correct", "%"],
                         [[k, v["rows"], v["solver_first_correct"], pct(v["solver_first_correct"], v["rows"])]
                          for k, v in conv["by_list_and_exemplar_vote"].items()]), ""]
        out += [md_table(["Reviewer/Planner/delivery", "rows"], [[k, v] for k, v in conv["reviewer_planner"].items()]), ""]
    out += ["## Intent: top-2 sizing on delivered-wrong rows", ""]
    keys = sorted(set(A["agree"]["intent"]["top2_sizing"]) | set(A["wave_aa"]["intent"]["top2_sizing"]))
    out += [md_table(["quantity", "agree", "wave A/A"],
                     [[k, A["agree"]["intent"]["top2_sizing"].get(k, 0), A["wave_aa"]["intent"]["top2_sizing"].get(k, 0)]
                      for k in keys]), ""]
    out += ["## Slots: node states per gold item", ""]
    hdr = ["node", "arm"] + list(GOLD_KINDS) + ["SPURIOUS", "SLU-F1 micro"]
    rows = []
    for node, name in (("s1", "S1 Solver first"), ("s2", "R after Reviewer/Planner"), ("d", "D delivered")):
        for label in ("agree", "wave_aa"):
            nd = A[label]["slots"]["node_states"][node]
            rows.append([name, label] + [nd["states"][k] for k in GOLD_KINDS] + [nd["spurious"], nd["slu_f1_micro"]])
    out += [md_table(hdr, rows), ""]
    sg = report["stability"]["slot_f1_node_gain"]
    out += [md_table(["SLU-F1 contrast", "pp [95 % CI]"], [[k, ci(v)] for k, v in sg.items()]), ""]
    for label in ("agree", "wave_aa"):
        s = A[label]["slots"]
        out += [f"### Slot node detail ({label})", ""]
        out += [md_table(["Perception note state", "gold items", "S1 exact", "D exact", "D kinds"],
                         [[k, v["items"], v["s1_exact"], v["d_exact"], ", ".join(f"{a} {b}" for a, b in v["d_kinds"].items())]
                          for k, v in s["note_to_solver_conversion"].items()]), ""]
        out += [md_table(["delivered knowledge (W5 method)", "gold items", "type card delivered", "S1 exact", "D exact"],
                         [[k, v["items"], v["type_card_delivered"], v["s1_exact"], v["d_exact"]]
                          for k, v in s["knowledge_to_solver_conversion"].items()]), ""]
        for edge in ("s1_to_s2", "s2_to_d"):
            out += [f"Edge {edge}:", "",
                    md_table(["state at a", "items", "repaired", "broken", "changed kind", "unchanged"],
                             [[k, v["items"], v["repaired"], v["broken"], v["changed_kind"], v["unchanged"]]
                              for k, v in s[f"edge_{edge}"].items()]), ""]
        out += [md_table(["spurious", "count"], [[k, v] for k, v in s["spurious_edges"].items()]), ""]
        out += [md_table(["origin of delivered gold-side errors", "items", "by delivered kind"],
                         [[k, v["_all"], ", ".join(f"{a} {b}" for a, b in v.items() if a != "_all")]
                          for k, v in s["origin_split"].items()]), ""]
        out += [md_table(["origin total", "count"], [[k, v] for k, v in s["origin_totals"].items()]), ""]
        out += [md_table(["re-listen addressable (BOUNDARY + NEAR + FORMAT)", "count"],
                         [[k, v] for k, v in s["relisten_addressable"].items()]), ""]
    out += [md_table(["slot item stability", "count"], [[k, v] for k, v in report["stability"]["slot_item_stability"].items()]), ""]
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------


def build(args) -> dict:
    data_root = Path(args.data_root)
    lock = load_lock(Path(args.lock))
    gold = ES.load_gold(lock, data_root)
    pool = GP.load_exemplar_pool(data_root, ES.EX_SNAPSHOT)
    m1_values = W5.snapshot_values(data_root, W5.M1_SNAPSHOT)
    arms, derived, inputs, structural = {}, {}, {}, {}
    ids = None
    for spec in ARMS:
        phases = GP.load_phases(data_root, spec)
        directory = phases["directory"]
        outputs = ES.load_outputs(directory, spec["run_id"])
        scores = ES.load_scores(directory, spec["run_id"])
        nodes = load_node_states(data_root, spec)
        arm = {"label": spec["label"], "phases": phases["rows"], "outputs": outputs["rows"], "scores": scores["rows"],
               "nodes": nodes["rows"]}
        arm_ids = sorted(scores["rows"])
        if len(arm_ids) != ROWS or (ids is not None and arm_ids != ids):
            raise ReadError(f"{spec['label']}: roster is not the 1,080-row Fold A roster")
        ids = arm_ids
        trace = trace_pass(directory, spec, phases) if not args.skip_trace else None
        structural[spec["label"]] = {"es_structural_checks": ES.structural_checks(arm, gold),
                                     "phase_checks": phases["checks"], "node_state_checks": nodes["checks"],
                                     "trace": trace, "official_intent_accuracy": scores["official_intent_accuracy"]}
        inputs[spec["label"]] = {"run_id": spec["run_id"], "attempt": spec["attempt"], "program": PROGRAM,
                                 "phases": [phases["relpath"], phases["sha256"]],
                                 "outputs": [str((directory / outputs["relpath"]).relative_to(data_root)), outputs["sha256"]],
                                 "scores": [str((directory / scores["relpath"]).relative_to(data_root)), scores["sha256"]]}
        d = derive_arm(arm, gold, ids, pool, m1_values)
        structural[spec["label"]]["derivation_checks"] = d["checks"]
        derived[spec["label"]] = d
        arms[spec["label"]] = {"title": spec["title"], "intent": intent_ledger(d["rows"], ids),
                               "slots": slot_ledger(d["rows"], d["items"], ids)}
        del arm, phases, nodes
    inputs["exemplar_pool"] = [pool["relpath"], pool["sha256"]]
    inputs["m1_snapshot_content_hash"] = [W5.M1_SNAPSHOT["relpath"], W5.M1_SNAPSHOT["sha256"]]
    return {"read_id": READ_ID, "recipe": RECIPE, "status": "DESCRIPTIVE",
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "embedder": 0,
                         "official_scorer_subprocess": 0, "network": 0, "gpu": 0, "paid_api": 0},
            "roster_rows": ROWS, "program": PROGRAM, "near_threshold": NEAR_THRESHOLD,
            "bootstrap": {"primitive": "analysis.bootstrap.paired_cluster_bootstrap", "seed": BOOT_SEED,
                          "replicates": BOOT_N, "ci_level": BOOT_LEVEL},
            "drivers": {name: [str(p.relative_to(REPO_ROOT)), digest(p)] for name, p in (
                ("error_sources", REPO_ROOT / "scripts/analysis/slurp_agree_arm_error_sources.py"),
                ("w5_estimate", REPO_ROOT / "scripts/analysis/slurp_w5_fold_a_offline_estimate.py"),
                ("gold_position", REPO_ROOT / "scripts/analysis/slurp_gold_position_and_solver_freedom_read.py"))},
            "inputs": inputs, "structural": structural, "arms": arms, "stability": stability(derived, ids)}


def strip_time(text: str) -> str:
    return re.sub(r'"generated_at": "[^"]*"|Generated `[^`]*`', "", text)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lock", default=DEFAULT_LOCK)
    parser.add_argument("--data-root", default=DEFAULT_DATA_ROOT)
    parser.add_argument("--skip-trace", action="store_true")
    parser.add_argument("--check", action="store_true", help="re-derive and compare with the written outputs")
    args = parser.parse_args(argv)
    report = build(args)
    out_dir = Path(args.data_root) / ANALYSIS_DIR
    texts = {"report.json": json.dumps(report, indent=2, sort_keys=True) + "\n", "ledger.md": render(report)}
    if args.check:
        bad = [n for n, t in texts.items() if strip_time((out_dir / n).read_text(encoding="utf-8")) != strip_time(t)]
        print("check:", "IDENTICAL apart from generated_at" if not bad else f"DIFFERS in {bad}")
        return 1 if bad else 0
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, text in texts.items():
        (out_dir / name).write_text(text, encoding="utf-8", newline="\n")
    manifest = {n: hashlib.sha256(strip_time(t).encode("utf-8")).hexdigest() for n, t in sorted(texts.items())}
    (out_dir / "content-sha256.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                                                 encoding="utf-8", newline="\n")
    print("wrote", out_dir)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
