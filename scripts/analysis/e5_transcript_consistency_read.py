#!/usr/bin/env python3
"""E5-1: the offline transcript-consistency ORACLE read (model-free; read row
``SAEA-SLURP-E5-TRANSCRIPT-CONSISTENCY-READ-V1``).

Owner decision 201 (option A, 2026-09-29) and the owner supplement of the same day: tools must be
invoked by the MODEL on its own initiative, never applied by the system by default, or the study
falls into a self-proof trap (ASR + LLM rather than an omni agent system). So this read is an
INSTRUMENT. It bounds what a perfect ASR tool call could yield for slot-value verification and
measures the decision the model would have to learn; nothing it computes becomes a delivery step.
The three deterministic rules below are ORACLE BOUNDS of a system-applied check, never runtime
candidates. The runtime form (E5-2, not built) is the frozen core OFFERED a pinned ASR tool through
the native tool-calling path and DECIDING itself whether to call it.

Inputs (all sealed; read-only):

* an E5-0 transcript catalog: ``$DATA/prepared/SAEA-SLURP-ASR-TRANSCRIPTS-V1/<roster>/`` (catalog.json
  pinned by receipt.json; every per-row artifact re-hashed before its transcript is read);
* one or more sealed arms (``--arm LABEL=RUN_ID/ATTEMPT``): AGREE (primary), the wave A/A (replicate),
  later COMP-1b; their ``<RUN>.outputs.jsonl`` delivered column (and ``.scores.json`` to prove the
  in-process official arithmetic reproduces the sealed totals, ``.trace.jsonl`` / ``.phases.json`` for
  the model-visible signals);
* optionally E4-1 (``--e4 RUN_ID/ATTEMPT``): its delivered column, its ``relisten-replace-only`` shadow
  column (the EXACT -> BOUNDARY items) and its per-row relisten receipts (a model-visible signal);
* governed TRAIN gold through ``data.slurp.load_slurp_split``, OFFLINE and on the scoring side only.

Metrics (per the design spec, section 2.2, and the brief):

1. gold-span containment (Q6): the share of gold entities whose canonical value occurs as a contiguous
   token run in the canonical transcript; precondition >= 0.80;
2. exact-value preservation on the E4-broken items (Q3): of E4-1's EXACT -> BOUNDARY items, the share
   whose delivered EXACT value the transcript contains (a check would have KEPT them); precondition >= 0.85;
3. delivered-wrong-value containment (Q2): per error kind, the share of wrong delivered values the
   transcript contains (a transcript check would NOT reject them);
4. three deterministic rules -- R-FLAG (no change; counts flags), R-DROP (drop an inconsistent entity),
   R-SWAP (replace it by the same-token-count transcript n-gram of minimum token edit distance whose
   character similarity is >= theta) -- each scored with the official in-process arithmetic, official
   pooled SLU-F1 delta vs the delivered column with a paired row bootstrap (10,000 draws, seed
   20260929, CI95), per-entity-type tables, transitions into FORMAT / BOUNDARY reported separately;
5. the TOOL-CALL DECISION ORACLE (owner supplement): per row, whether a tool call WOULD have helped
   (a delivered value the transcript does not contain, whose matched gold span the transcript does
   contain), the count of such rows, and the AUC of each model-visible signal for predicting them
   (Perception candidate-list length, note_parse_status, delivered entity count and types, E4-1's
   blind / forced-choice disagreement, the entity-free exemplar share).

Tuning discipline: ``--mode tune`` runs only on a TRAIN Fold B catalog and writes ``params.json`` (the
chosen theta and near-containment switch); ``--mode read`` runs only on a TRAIN Fold A catalog, needs
the pinned ``params.json`` and always also reports the two pre-set values theta 0.6 and 0.8.

Text discipline: no utterance text, transcript, gold value, filler or model output is printed or
persisted -- only ids, counts, rates, pp, AUCs, slot TYPE names, class names and hashes. Zero model,
server, tokenizer, encoder, embedder, scorer-subprocess, network and GPU contacts.

    PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/e5_transcript_consistency_read.py --mode read \\
        --roster fold-a --params <tune out>/params.json --params-sha256 <sha> \\
        --arm agree=SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1/attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1 \\
        --arm wave_aa=SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1/attempt-slurp-native-stage3-wave1-aa-fold-a-generation-v1 \\
        --replicate wave_aa \\
        --e4 SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-V1/attempt-slurp-native-stage3-relisten-fold-a-generation-v1-seal-only
"""

from __future__ import annotations
import os

import argparse
import hashlib
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

READ_ID = "SAEA-SLURP-E5-TRANSCRIPT-CONSISTENCY-READ-V1"
SCHEMA = "saea-slurp-e5-transcript-consistency-read-v1"
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
CATALOG_ROOT = "prepared/SAEA-SLURP-ASR-TRANSCRIPTS-V1"
SCORER = "slurp-slu-official-train"
FOLD_SPLITS = {
    "fold-a": "61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6",
    "fold-b": "4407794c4a5d2e8883d93fdf242deb33c0987405d62e05a7d8416f5251a3484a",
}
MODE_ROSTER = {"tune": "fold-b", "read": "fold-a"}
BOOT_DRAWS = 10_000
BOOT_SEED = 20260929
BOOT_LEVEL = 0.95
GATE_GOLD_SPAN = 0.80
GATE_E4_KEEP = 0.85
E5_2A_FLOOR_PP = 1.49          # decision 190 same-flight SLU floor at n = 1,080 (coordinator ruling Q2)
REPLICATE_MIN_PP = 1.0
THETA_PRESET = (0.6, 0.8)
THETA_GRID = (0.5, 0.6, 0.7, 0.8, 0.9)
NEAR_OPTIONS = (False, True)
NEAR_MIN_TOKENS = 3
E4_SHADOW = "relisten-replace-only"
GOLD_KINDS = ("EXACT", "FORMAT", "BOUNDARY", "NEAR", "WRONG-VALUE", "WRONG-TYPE", "MISSING")
WRONG_KINDS = ("FORMAT", "BOUNDARY", "NEAR", "WRONG-VALUE", "WRONG-TYPE", "SPURIOUS")
RULES = ("R-FLAG", "R-DROP", "R-SWAP")
EX_FACET_PREFIX = "train-exemplars::facet:content:"


class ReadError(RuntimeError):
    pass


# ---------------------------------------------------------------------------- canonical forms (pure)


def canon_tokens(text: str) -> list:
    """The runtime-side, gold-free canonicaliser the spec names: ``rails.relisten.canonical_value``
    (the pinned P2 filler normaliser, then ``fold_number_words``), split into tokens."""
    from speech_aware_evidence_acquisition.rails.relisten import canonical_value

    return canonical_value(text).split()


def surface_tokens(text: str) -> list:
    from speech_aware_evidence_acquisition.analysis.sealed_credit.entity_states import fold

    return fold(text or "").split()


def token_edit(a: list, b: list) -> int:
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def similarity(a: list, b: list) -> float:
    from speech_aware_evidence_acquisition.analysis.sealed_credit.entity_states import norm_distance

    return 1.0 - norm_distance(" ".join(a), " ".join(b))


def contiguous(short: list, long: list) -> bool:
    if not short or len(short) > len(long):
        return False
    return any(long[i:i + len(short)] == short for i in range(len(long) - len(short) + 1))


def near_contained(short: list, long: list, min_tokens: int = NEAR_MIN_TOKENS) -> bool:
    """Token edit distance <= 1 against some transcript run of length n-1, n or n+1 (runs of n >= 3)."""
    n = len(short)
    if n < min_tokens:
        return False
    for width in (n - 1, n, n + 1):
        if width < 1 or width > len(long):
            continue
        for i in range(len(long) - width + 1):
            if token_edit(short, long[i:i + width]) <= 1:
                return True
    return False


def consistent(value: str, transcript_canon: list, near: bool = False) -> bool | None:
    """Whether the transcript supports ``value``: True, False, or None when unverifiable (empty value)."""
    tokens = canon_tokens(value)
    if not tokens:
        return None
    if contiguous(tokens, transcript_canon):
        return True
    return bool(near and near_contained(tokens, transcript_canon))


def swap_candidate(value: str, transcript_text: str, theta: float) -> str | None:
    """The same-token-count transcript n-gram of minimum token edit distance to ``value`` whose character
    similarity is >= theta (ties: higher similarity, then earlier position); None if none qualifies."""
    n = len(surface_tokens(value))
    target = canon_tokens(value)
    words = surface_tokens(transcript_text)
    if n == 0 or not target or n > len(words):
        return None
    best = None
    for i in range(len(words) - n + 1):
        window = words[i:i + n]
        cand = canon_tokens(" ".join(window))
        if not cand or cand == target:
            continue
        sim = similarity(target, cand)
        if sim < theta:
            continue
        key = (token_edit(target, cand), -sim, i)
        if best is None or key < best[0]:
            best = (key, " ".join(window))
    return None if best is None else best[1]


# ---------------------------------------------------------------------------- rules and scoring (pure)


def apply_rule(pred: tuple, transcript: dict | None, rule: str, *, theta: float = 0.8, near: bool = False,
               entity=None) -> tuple:
    """(new prediction tuple, per-entity action records) of one row under one rule.

    ``transcript`` is ``{"status", "text", "canon"}`` or None; a row without a usable transcript is
    unverifiable and left unchanged."""
    if entity is None:
        from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity as entity
    actions, out = [], []
    usable = transcript is not None and transcript.get("status") == "ok" and transcript.get("canon")
    for index, ent in enumerate(pred):
        verdict = consistent(ent.filler, transcript["canon"], near) if usable else None
        action = "keep"
        new = ent
        if verdict is False:
            if rule == "R-DROP":
                action, new = "drop", None
            elif rule == "R-SWAP":
                cand = swap_candidate(ent.filler, transcript["text"], theta)
                if cand is not None:
                    action, new = "swap", entity(ent.type, cand)
                else:
                    action = "keep-no-candidate"
            else:
                action = "flag"
        actions.append({"index": index, "type": ent.type, "consistent": verdict, "action": action})
        if new is not None:
            out.append(new)
    return tuple(out), actions


def slu_counts(gold: tuple, pred: tuple) -> tuple:
    """Pooled SLU-F1 ingredients (word + char TP/FP/FN) of one row by the official arithmetic."""
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import score_slu

    s = score_slu(gold_scenario="s", gold_action="a", gold_entities=list(gold), predicted_scenario="s",
                  predicted_action="a", predicted_entities=list(pred))
    return (s.slu_f1_word_tp + s.slu_f1_char_tp, s.slu_f1_word_fp + s.slu_f1_char_fp,
            s.slu_f1_word_fn + s.slu_f1_char_fn)


def pooled_f1(totals) -> float:
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import _prf

    return 100.0 * _prf(*totals)[2]


def totals(ids, counts) -> tuple:
    return tuple(sum(counts[s][k] for s in ids) for k in range(3))


def paired_delta(ids: list, counts_a: dict, counts_b: dict, draws: int = BOOT_DRAWS, seed: int = BOOT_SEED) -> dict:
    """Pooled SLU-F1 of b minus a with a paired row (cluster) bootstrap CI."""
    from speech_aware_evidence_acquisition.analysis.bootstrap import paired_cluster_bootstrap

    def stat(xs):
        return pooled_f1(totals(xs, counts_b)) - pooled_f1(totals(xs, counts_a))

    r = paired_cluster_bootstrap(sample_ids=list(ids), statistic=stat, n_replicates=draws, seed=seed,
                                 ci_level=BOOT_LEVEL)
    return {"point_pp": round(r.point_estimate, 4), "ci95": [round(r.ci_low, 4), round(r.ci_high, 4)],
            "draws": draws, "seed": seed}


def gold_kinds(gold: tuple, pred: tuple) -> tuple:
    """({gold_index: (kind, pred_index)}, [spurious pred indices]) with EXACT for exact matches."""
    from speech_aware_evidence_acquisition.analysis.sealed_credit.entity_states import entity_items

    states = {}
    taken = set()
    for pi, ent in enumerate(pred):
        hit = next((gi for gi, g in enumerate(gold) if gi not in taken and g == ent), None)
        if hit is not None:
            taken.add(hit)
            states[hit] = ("EXACT", pi)
    spurious = []
    for it in entity_items(gold, pred):
        if it["gold_index"] is None:
            spurious.append(it["pred_index"])
        else:
            states[it["gold_index"]] = (it["kind"], it["pred_index"])
    return states, spurious


def gold_span_containment(ids, gold: dict, transcripts: dict) -> dict:
    by_type, n, hit, no_tx = defaultdict(Counter), 0, 0, 0
    for sid in ids:
        tx = transcripts.get(sid)
        for g in gold[sid]:
            n += 1
            ok = bool(tx and tx["status"] == "ok" and contiguous(canon_tokens(g.filler), tx["canon"]))
            no_tx += int(not (tx and tx["status"] == "ok"))
            hit += int(ok)
            by_type[g.type]["items"] += 1
            by_type[g.type]["contained"] += int(ok)
    return {"items": n, "contained": hit, "rate": round(hit / n, 4) if n else None,
            "items_on_rows_without_usable_transcript": no_tx,
            "by_type": {t: {**dict(c), "rate": round(c["contained"] / c["items"], 4)} for t, c in sorted(by_type.items())}}


def wrong_value_containment(ids, gold: dict, pred: dict, transcripts: dict) -> dict:
    out = {k: Counter() for k in WRONG_KINDS}
    for sid in ids:
        tx = transcripts.get(sid)
        if not (tx and tx["status"] == "ok"):
            continue
        states, spurious = gold_kinds(gold[sid], pred[sid])
        for gi, (kind, pi) in states.items():
            if kind in WRONG_KINDS and pi is not None:
                out[kind]["items"] += 1
                out[kind]["contained"] += int(contiguous(canon_tokens(pred[sid][pi].filler), tx["canon"]))
        for pi in spurious:
            out["SPURIOUS"]["items"] += 1
            out["SPURIOUS"]["contained"] += int(contiguous(canon_tokens(pred[sid][pi].filler), tx["canon"]))
    return {k: {**dict(c), "rate": round(c["contained"] / c["items"], 4) if c["items"] else None}
            for k, c in out.items()}


def e4_broken_items(ids, gold: dict, delivered: dict, shadow: dict) -> list:
    """(sample_id, gold_index) of every gold item EXACT in E4-1's delivered column and BOUNDARY in its shadow."""
    items = []
    for sid in ids:
        d_states, _ = gold_kinds(gold[sid], delivered[sid])
        s_states, _ = gold_kinds(gold[sid], shadow[sid])
        for gi in range(len(gold[sid])):
            if d_states.get(gi, ("MISSING", None))[0] == "EXACT" and \
                    s_states.get(gi, ("MISSING", None))[0] == "BOUNDARY":
                items.append((sid, gi))
    return items


def exact_preservation(items: list, gold: dict, transcripts: dict, near: bool = False) -> dict:
    kept = Counter()
    for sid, gi in items:
        tx = transcripts.get(sid)
        verdict = consistent(gold[sid][gi].filler, tx["canon"], near) if tx and tx["status"] == "ok" else None
        kept["kept" if verdict is not False else "rejected"] += 1
        kept["by_type:" + gold[sid][gi].type] += int(verdict is not False)
    n = len(items)
    return {"items": n, "kept": kept["kept"], "rate": round(kept["kept"] / n, 4) if n else None,
            "kept_by_type": {k.split(":", 1)[1]: v for k, v in sorted(kept.items()) if k.startswith("by_type:")}}


def rule_column(ids, pred: dict, transcripts: dict, rule: str, theta: float, near: bool) -> tuple:
    column, actions = {}, {}
    for sid in ids:
        column[sid], actions[sid] = apply_rule(pred[sid], transcripts.get(sid), rule, theta=theta, near=near)
    return column, actions


def rule_report(ids, gold: dict, pred: dict, column: dict, actions: dict, base_counts: dict,
                draws: int = BOOT_DRAWS) -> dict:
    counts = {sid: slu_counts(gold[sid], column[sid]) for sid in ids}
    act, trans, by_type = Counter(), Counter(), defaultdict(Counter)
    for sid in ids:
        for a in actions[sid]:
            act[a["action"]] += 1
            by_type[a["type"]][a["action"]] += 1
        before, spur_b = gold_kinds(gold[sid], pred[sid])
        after, spur_a = gold_kinds(gold[sid], column[sid])
        for gi in range(len(gold[sid])):
            a = before.get(gi, ("MISSING", None))[0]
            b = after.get(gi, ("MISSING", None))[0]
            if a != b:
                trans[f"{a}->{b}"] += 1
                by_type[gold[sid][gi].type][f"{a}->{b}"] += 1
        trans["SPURIOUS removed"] += max(0, len(spur_b) - len(spur_a))
        trans["SPURIOUS added"] += max(0, len(spur_a) - len(spur_b))
    exact_lost = sum(n for k, n in trans.items() if k.startswith("EXACT->"))
    converted = sum(n for k, n in trans.items() if k.endswith("->EXACT"))
    return {
        "slu_f1": round(pooled_f1(totals(ids, counts)), 4),
        "delta_vs_delivered": paired_delta(ids, base_counts, counts, draws=draws),
        "actions": dict(sorted(act.items())),
        "gold_transitions": dict(sorted(trans.items())),
        "into_format": sum(n for k, n in trans.items() if k.endswith("->FORMAT")),
        "into_boundary": sum(n for k, n in trans.items() if k.endswith("->BOUNDARY")),
        "exact_lost": exact_lost, "converted_to_exact": converted,
        "rows_changed": sum(1 for sid in ids if column[sid] != pred[sid]),
        "by_type": {t: dict(sorted(c.items())) for t, c in sorted(by_type.items())},
    }


# ---------------------------------------------------------------------------- the tool-call decision oracle (pure)


def decision_oracle(ids, gold: dict, pred: dict, transcripts: dict, near: bool = False) -> dict:
    """Per row: would a tool call have helped? An entity 'would help' when its delivered value is NOT
    supported by the transcript while its matched gold span IS contained (so a verifying call could
    have repaired it). MISSING gold spans the transcript contains are counted separately."""
    rows, entity_rows = {}, []
    for sid in ids:
        tx = transcripts.get(sid)
        usable = bool(tx and tx["status"] == "ok")
        states, spurious = gold_kinds(gold[sid], pred[sid])
        pred_to_gold = {pi: (gi, kind) for gi, (kind, pi) in states.items() if pi is not None}
        helps, flags, missing_helps = 0, 0, 0
        for pi, ent in enumerate(pred[sid]):
            verdict = consistent(ent.filler, tx["canon"], near) if usable else None
            gi_kind = pred_to_gold.get(pi)
            gold_in = bool(usable and gi_kind and contiguous(canon_tokens(gold[sid][gi_kind[0]].filler), tx["canon"]))
            helpful = bool(verdict is False and gi_kind and gi_kind[1] != "EXACT" and gold_in)
            flags += int(verdict is False)
            helps += int(helpful)
            entity_rows.append({"sample_id": sid, "type": ent.type, "kind": gi_kind[1] if gi_kind else "SPURIOUS",
                                "flagged": verdict is False, "helpful": helpful})
        for gi, g in enumerate(gold[sid]):
            if states.get(gi, ("MISSING", None))[0] == "MISSING" and usable and \
                    contiguous(canon_tokens(g.filler), tx["canon"]):
                missing_helps += 1
        rows[sid] = {"usable_transcript": usable, "flags": flags, "helpful_entities": helps,
                     "helpful_missing": missing_helps, "helpful": helps > 0}
    flagged = [e for e in entity_rows if e["flagged"]]
    by_type = defaultdict(Counter)
    for e in entity_rows:
        by_type[e["type"]]["delivered"] += 1
        by_type[e["type"]]["flagged"] += int(e["flagged"])
        by_type[e["type"]]["helpful"] += int(e["helpful"])
    return {
        "rows": rows,
        "helpful_rows": sorted(s for s, r in rows.items() if r["helpful"]),
        "counts": {
            "rows": len(ids), "helpful_rows": sum(r["helpful"] for r in rows.values()),
            "helpful_entities": sum(r["helpful_entities"] for r in rows.values()),
            "rows_with_helpful_missing": sum(r["helpful_missing"] > 0 for r in rows.values()),
            "helpful_missing_items": sum(r["helpful_missing"] for r in rows.values()),
            "flagged_entities": len(flagged),
            "flag_precision": round(sum(e["helpful"] for e in flagged) / len(flagged), 4) if flagged else None,
            "rows_without_usable_transcript": sum(not r["usable_transcript"] for r in rows.values()),
        },
        "entity_by_type": {t: {**dict(c), "helpful_rate": round(c["helpful"] / c["delivered"], 4)}
                           for t, c in sorted(by_type.items())},
    }


def auc(scores: list, labels: list) -> float | None:
    """Mann-Whitney AUC (ties count one half): P(score of a helpful row > score of an unhelpful row)."""
    pos = [s for s, y in zip(scores, labels) if y]
    neg = [s for s, y in zip(scores, labels) if not y]
    if not pos or not neg:
        return None
    wins = 0.0
    for p in pos:
        for q in neg:
            wins += 1.0 if p > q else 0.5 if p == q else 0.0
    return wins / (len(pos) * len(neg))


def signal_aucs(rows: dict, signals: dict) -> dict:
    """AUC of every row signal for the ``helpful`` label; a categorical signal gets one one-vs-rest AUC
    per level. Rows lacking a signal are left out of that signal only."""
    out = {}
    for name, values in sorted(signals.items()):
        ids = [s for s in rows if values.get(s) is not None]
        labels = [rows[s]["helpful"] for s in ids]
        sample = [values[s] for s in ids]
        if sample and all(isinstance(v, str) for v in sample):
            levels = {}
            for level in sorted(set(sample)):
                ind = [1.0 if v == level else 0.0 for v in sample]
                levels[level] = {"rows": sum(ind), "auc": None if auc(ind, labels) is None else round(auc(ind, labels), 4)}
            out[name] = {"kind": "categorical", "rows": len(ids), "positives": sum(labels), "levels": levels}
        else:
            a = auc([float(v) for v in sample], labels)
            out[name] = {"kind": "numeric", "rows": len(ids), "positives": sum(labels),
                         "auc": None if a is None else round(a, 4)}
    return out


# ---------------------------------------------------------------------------- tuning (pure)


def tune(ids, gold, pred, transcripts, base_counts, thetas=THETA_GRID, nears=NEAR_OPTIONS) -> dict:
    """Pick theta and the near switch on the tuning roster by the point SLU-F1 delta of R-SWAP (the
    near switch for R-DROP likewise); no bootstrap (draws=1 keeps tuning cheap and point-only)."""
    grid = []
    for near in nears:
        col, act = rule_column(ids, pred, transcripts, "R-DROP", 0.0, near)
        drop = rule_report(ids, gold, pred, col, act, base_counts, draws=1)["delta_vs_delivered"]["point_pp"]
        for theta in thetas:
            col, act = rule_column(ids, pred, transcripts, "R-SWAP", theta, near)
            swap = rule_report(ids, gold, pred, col, act, base_counts, draws=1)["delta_vs_delivered"]["point_pp"]
            grid.append({"theta": theta, "near": near, "r_swap_point_pp": swap, "r_drop_point_pp": drop})
    best_swap = max(grid, key=lambda g: (g["r_swap_point_pp"], -g["theta"], not g["near"]))
    best_drop = max(grid, key=lambda g: (g["r_drop_point_pp"], not g["near"]))
    return {"grid": grid, "params": {"schema": "saea-e5-1-params-v1", "theta": best_swap["theta"],
                                     "near_swap": best_swap["near"], "near_drop": best_drop["near"]}}


# ---------------------------------------------------------------------------- IO (sealed inputs)


def import_path(path: Path, name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def load_catalog(data_root: Path, roster: str) -> tuple:
    """(transcripts by sample id, catalog facts). Every artifact is re-hashed before it is read."""
    base = data_root / CATALOG_ROOT / roster
    receipt = json.loads((base / "receipt.json").read_text(encoding="utf-8"))
    catalog_path = base / "catalog.json"
    sha = sha256_file(catalog_path)
    if receipt.get("catalog", {}).get("sha256") != sha:
        raise ReadError("the transcript catalog differs from its E5-0 receipt pin")
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if catalog.get("schema") != "saea-prepared-speech-observation-catalog-v1":
        raise ReadError("transcript catalog schema is not the prepared speech observation catalog")
    if catalog["use_split_identity_hash"] != FOLD_SPLITS[roster]:
        raise ReadError(f"transcript catalog split is not the {roster} roster")
    transcripts, status = {}, Counter()
    for row in catalog["observations"]:
        path = data_root / row["artifact_relpath"]
        if sha256_file(path) != row["artifact_sha256"]:
            raise ReadError(f"artifact hash mismatch for {row['sample_id']}")
        wrapper = json.loads(path.read_text(encoding="utf-8"))
        if wrapper.get("contact_class") != "speech-tool" or wrapper.get("output_sha256") != row["output_sha256"]:
            raise ReadError(f"artifact lineage differs for {row['sample_id']}")
        out = wrapper["output"]
        text = out["transcript"] if out["status"] == "ok" else ""
        transcripts[row["sample_id"]] = {"status": out["status"], "text": text, "canon": canon_tokens(text)}
        status[out["status"]] += 1
    facts = {"relpath": f"{CATALOG_ROOT}/{roster}/catalog.json", "sha256": sha,
             "receipt_sha256": sha256_file(base / "receipt.json"), "rows": len(transcripts),
             "status": dict(sorted(status.items())), "decoding_config_sha256": catalog["decoding_config_sha256"],
             "producer_run_id": catalog["producer"]["run_id"]}
    return transcripts, facts


def load_column(path: Path) -> dict:
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity, parse_slu_response

    rows = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            _s, _a, entities, _ok = parse_slu_response(record.get("text") or "")
            rows[record["sample_id"]] = tuple(SlotEntity(e.type, e.filler) for e in entities)
    return rows


def run_dir(data_root: Path, spec: str) -> tuple:
    run_id, _, attempt = spec.partition("/")
    if not run_id or not attempt:
        raise ReadError(f"arm spec {spec!r} is not RUN_ID/ATTEMPT")
    return data_root / "runs" / run_id / attempt, run_id


def load_arm(data_root: Path, spec: str, ids_expected: set) -> dict:
    directory, run_id = run_dir(data_root, spec)
    outputs = directory / f"{run_id}.outputs.jsonl"
    pred = load_column(outputs)
    if set(pred) != ids_expected:
        raise ReadError(f"{run_id}: the delivered roster is not the catalog roster")
    arm = {"run_id": run_id, "directory": directory, "pred": pred,
           "outputs": {"relpath": str(outputs.relative_to(data_root)), "sha256": sha256_file(outputs)}}
    scores = directory / f"{run_id}.scores.json"
    if scores.exists():
        from speech_aware_evidence_acquisition.analysis.sealed_credit import row_states as RS

        sealed = RS.load_scores(directory, run_id, SCORER)
        arm["sealed_totals"] = tuple(sum(sealed["rows"][s][k] for s in ids_expected) for k in ("tp", "fp", "fn"))
        arm["scores_sha256"] = sha256_file(scores)
    return arm


def perception_signals(directory: Path, run_id: str) -> dict:
    """sample_id -> (note_parse_status, candidate-list length) of the delivered Perception note."""
    from speech_aware_evidence_acquisition.rails.native_episode_receipt import parse_perception_branch_note

    path = directory / f"{run_id}.trace.jsonl"
    out = {}
    if not path.exists():
        return out
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            if record.get("channel") != "ORG":
                continue
            sid = record["record_id"].split("/", 1)[0]
            for state in record["payload"].get("org_agent_states") or ():
                if state.get("state_kind") == "phase:perception":
                    status, candidates, raw = parse_perception_branch_note(state.get("content"))
                    out[sid] = (status, len(candidates))
                    break
    return out


def entity_free_share(directory: Path, run_id: str, data_root: Path) -> dict:
    """sample_id -> the share of the row's ranked exemplars that carry no entity (content, not a score)."""
    path = directory / f"{run_id}.phases.json"
    if not path.exists():
        return {}
    NG = import_path(REPO_ROOT / "scripts/analysis/slurp_node_gain_ledger.py", "slurp_node_gain_ledger")
    pool = NG.GP.load_exemplar_pool(data_root, NG.ES.EX_SNAPSHOT)["values"]
    doc = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for res in doc["phases"][0]["results"]:
        for wave in res.get("waves") or ():
            cands = (wave.get("rank_result") or {}).get("candidates") or []
            ex = [str(c["facet_id"]).split(EX_FACET_PREFIX, 1)[-1] for c in cands
                  if str(c["facet_id"]).startswith(EX_FACET_PREFIX)]
            if ex:
                free = sum(1 for e in ex if e in pool and not pool[e]["fillers"])
                out[res["sample_id"]] = round(free / len(ex), 6)
                break
    return out


def relisten_disagreement(e4_outputs: Path) -> dict:
    """sample_id -> the number of E4-1 relisten entities whose blind listen disagreed with the delivered
    value (a forced choice fired) or came back unheard / unparsed."""
    out = {}
    with e4_outputs.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            rec = row.get("relisten") or {}
            n = 0
            for e in rec.get("entities") or ():
                blind = (e.get("blind") or {}).get("disposition")
                n += int(isinstance(e.get("confirm"), dict) or blind in ("unheard", "unparsed"))
            out[row["sample_id"]] = n
    return out


def load_gold(lock_path: Path, data_root: Path, ids: set) -> dict:
    from speech_aware_evidence_acquisition.data.lock import load_lock
    from speech_aware_evidence_acquisition.data.slurp import load_slurp_split
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity

    records = load_slurp_split(load_lock(lock_path), data_root, "train", workers=4)
    gold = {r.sample_id: tuple(SlotEntity(e.type, e.filler) for e in r.entities) for r in records if r.sample_id in ids}
    if set(gold) != ids:
        raise ReadError("the governed TRAIN loader does not cover the roster")
    return gold


# ---------------------------------------------------------------------------- build


def rule_settings(params: dict) -> list:
    """(rule, label, theta, near) of every reported column: R-FLAG and R-DROP do not depend on theta;
    R-SWAP is reported at the Fold-B-tuned theta and at both pre-set values."""
    return [("R-FLAG", "tuned", None, params["near_drop"]),
            ("R-DROP", "tuned", None, params["near_drop"]),
            ("R-DROP", "preset", None, False),
            ("R-SWAP", "tuned", params["theta"], params["near_swap"]),
            *(("R-SWAP", f"preset-theta-{t}", t, False) for t in THETA_PRESET)]


def arm_block(ids, gold, arm, transcripts, params, draws) -> dict:
    pred = arm["pred"]
    base_counts = {sid: slu_counts(gold[sid], pred[sid]) for sid in ids}
    base_totals = totals(ids, base_counts)
    if "sealed_totals" in arm and any(abs(a - b) > 1e-6 for a, b in zip(base_totals, arm["sealed_totals"])):
        raise ReadError(f"{arm['run_id']}: in-process totals do not reproduce the sealed official totals")
    settings = rule_settings(params)
    rules = {}
    for rule, label, theta, near in settings:
        col, act = rule_column(ids, pred, transcripts, rule, theta or 0.0, near)
        rules[f"{rule}|{label}"] = {"theta": theta, "near": near,
                                    **rule_report(ids, gold, pred, col, act, base_counts, draws=draws)}
    return {"run_id": arm["run_id"], "outputs": arm["outputs"], "scores_sha256": arm.get("scores_sha256"),
            "delivered_slu_f1": round(pooled_f1(base_totals), 4),
            "sealed_totals_reproduced": "sealed_totals" in arm,
            "wrong_value_containment": wrong_value_containment(ids, gold, pred, transcripts),
            "rules": rules}


def build(args) -> dict:
    data_root = Path(args.data_root)
    roster = MODE_ROSTER[args.mode]
    if args.roster != roster:
        raise ReadError(f"mode {args.mode} reads only the {roster} catalog (tuning on Fold B, reading on Fold A)")
    transcripts, catalog = load_catalog(data_root, roster)
    ids = sorted(transcripts)
    idset = set(ids)
    arms = {}
    for spec in args.arm:
        label, _, rest = spec.partition("=")
        arms[label] = load_arm(data_root, rest, idset)
    if not arms:
        raise ReadError("at least one --arm is required")
    primary = args.primary or next(iter(arms))
    gold = load_gold(Path(args.lock), data_root, idset)
    report = {"schema": SCHEMA, "read_id": READ_ID, "mode": args.mode, "roster": roster,
              "generated_at": datetime.now(timezone.utc).isoformat(),
              "role": "INSTRUMENT / ORACLE (owner supplement to decision 201): the rules are oracle bounds of a "
                      "system-applied check, never delivery candidates; the runtime form is a core-initiated tool call",
              "catalog": catalog, "rows": len(ids), "primary": primary, "replicate": args.replicate}
    report["gold_span_containment"] = gold_span_containment(ids, gold, transcripts)
    if args.mode == "tune":
        arm = arms[primary]
        base_counts = {sid: slu_counts(gold[sid], arm["pred"][sid]) for sid in ids}
        tuned = tune(ids, gold, arm["pred"], transcripts, base_counts)
        report["tuning"] = tuned
        report["params"] = tuned["params"]
        return report
    params_raw = Path(args.params).read_bytes()
    if hashlib.sha256(params_raw).hexdigest() != args.params_sha256:
        raise ReadError("params.json differs from its pinned sha256")
    params = json.loads(params_raw)
    report["params"] = {**params, "sha256": args.params_sha256}
    draws = args.draws
    report["arms"] = {label: arm_block(ids, gold, arm, transcripts, params, draws) for label, arm in arms.items()}
    if args.e4:
        directory, run_id = run_dir(data_root, args.e4)
        delivered = load_column(directory / f"{run_id}.outputs.jsonl")
        shadow = load_column(directory / "supply-variants" / f"arm-{E4_SHADOW}-shadow-outputs.jsonl")
        if set(delivered) != idset or set(shadow) != idset:
            raise ReadError("E4-1 columns do not cover the catalog roster")
        items = e4_broken_items(ids, gold, delivered, shadow)
        if args.expect_e4_broken is not None and len(items) != args.expect_e4_broken:
            raise ReadError(f"E4-1 EXACT -> BOUNDARY items: {len(items)}, expected {args.expect_e4_broken}")
        report["e4_exact_preservation"] = {**exact_preservation(items, gold, transcripts),
                                           "near_variant": exact_preservation(items, gold, transcripts, near=True),
                                           "run_id": run_id}
    # the tool-call decision oracle on the primary arm and its model-visible signals
    arm = arms[primary]
    oracle = decision_oracle(ids, gold, arm["pred"], transcripts, near=params.get("near_drop", False))
    signals = {"delivered_entity_count": {sid: len(arm["pred"][sid]) for sid in ids}}
    perception = perception_signals(arm["directory"], arm["run_id"])
    if perception:
        signals["perception_candidate_list_length"] = {s: v[1] for s, v in perception.items() if s in idset}
        signals["note_parse_status"] = {s: v[0] for s, v in perception.items() if s in idset}
    types = sorted({e.type for sid in ids for e in arm["pred"][sid]})
    for t in types:
        signals[f"delivered_type:{t}"] = {sid: float(any(e.type == t for e in arm["pred"][sid])) for sid in ids}
    share = entity_free_share(arm["directory"], arm["run_id"], data_root)
    if share:
        signals["entity_free_exemplar_share"] = {s: v for s, v in share.items() if s in idset}
    if args.e4:
        directory, run_id = run_dir(data_root, args.e4)
        signals["e4_relisten_disagreement"] = {
            s: v for s, v in relisten_disagreement(directory / f"{run_id}.outputs.jsonl").items() if s in idset}
    report["tool_call_decision_oracle"] = {
        "definition": "an entity would have been helped by a tool call when its delivered value is not supported by "
                      "the transcript while its matched gold span is contained; a row is helpful when any entity is",
        "arm": primary, **{k: v for k, v in oracle.items() if k != "rows"},
        "signal_auc": signal_aucs(oracle["rows"], signals)}
    # verdicts (pre-declared before E5-0 exists; the E5-2a bar is an oracle bound, not an admission)
    gsc = report["gold_span_containment"]["rate"]
    keep = (report.get("e4_exact_preservation") or {}).get("rate")
    pre = {"gold_span_containment": {"value": gsc, "threshold": GATE_GOLD_SPAN,
                                     "pass": gsc is not None and gsc >= GATE_GOLD_SPAN},
           "e4_exact_preservation": {"value": keep, "threshold": GATE_E4_KEEP,
                                     "pass": keep is not None and keep >= GATE_E4_KEEP}}
    bound = {}
    prim = report["arms"][primary]["rules"]
    rep = report["arms"].get(args.replicate, {}).get("rules", {}) if args.replicate else {}
    for key, r in prim.items():
        if not key.startswith(("R-DROP", "R-SWAP")):
            continue
        d = r["delta_vs_delivered"]
        rd = rep.get(key, {}).get("delta_vs_delivered", {}).get("point_pp")
        net = r["converted_to_exact"] + r["gold_transitions"].get("SPURIOUS removed", 0) - r["exact_lost"]
        bound[key] = {"point_pp": d["point_pp"], "ci95": d["ci95"], "replicate_point_pp": rd,
                      "clears_oracle_bar": bool(d["point_pp"] >= E5_2A_FLOOR_PP and d["ci95"][0] > 0
                                                and rd is not None and rd >= REPLICATE_MIN_PP
                                                and r["exact_lost"] * 5 <= max(net, 0))}
    report["verdicts"] = {"precondition": pre, "precondition_pass": all(v["pass"] for v in pre.values()),
                          "oracle_bound_of_a_system_applied_check": bound,
                          "note": "E5-2a is not a runtime candidate (owner supplement); these numbers bound what a "
                                  "perfect, core-initiated verification call could add"}
    return report


def md_table(header, rows) -> str:
    return "\n".join(["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
                     + ["| " + " | ".join(str(c) for c in row) + " |" for row in rows])


def render(r: dict) -> str:
    lines = [f"# E5-1 transcript-consistency read ({r['read_id']}, mode {r['mode']}, roster {r['roster']})", "",
             f"Generated {r['generated_at']}. {r['role']}.", ""]
    g = r["gold_span_containment"]
    lines += ["## Gold-span containment (Q6)", "", f"{g['contained']} / {g['items']} = {g['rate']}", "",
              md_table(["type", "items", "contained", "rate"],
                       [[t, v["items"], v["contained"], v["rate"]] for t, v in g["by_type"].items()]), ""]
    if "tuning" in r:
        lines += ["## Tuning grid (Fold B)", "", md_table(["theta", "near", "R-SWAP pp", "R-DROP pp"],
                  [[x["theta"], x["near"], x["r_swap_point_pp"], x["r_drop_point_pp"]] for x in r["tuning"]["grid"]]),
                  "", f"Chosen: {json.dumps(r['params'], sort_keys=True)}", ""]
        return "\n".join(lines)
    if "e4_exact_preservation" in r:
        e = r["e4_exact_preservation"]
        lines += ["## E4-1 EXACT -> BOUNDARY items kept (Q3)", "", f"{e['kept']} / {e['items']} = {e['rate']}", ""]
    for label, arm in r["arms"].items():
        lines += [f"## Arm {label} ({arm['run_id']}), delivered SLU-F1 {arm['delivered_slu_f1']}", "",
                  md_table(["rule", "theta", "near", "delta pp", "CI95", "exact lost", "converted", "into FORMAT",
                            "into BOUNDARY", "actions"],
                           [[k, v["theta"], v["near"], v["delta_vs_delivered"]["point_pp"], v["delta_vs_delivered"]["ci95"],
                             v["exact_lost"], v["converted_to_exact"], v["into_format"], v["into_boundary"],
                             json.dumps(v["actions"], sort_keys=True)] for k, v in arm["rules"].items()]), "",
                  "Wrong-value containment (Q2): " + json.dumps(arm["wrong_value_containment"], sort_keys=True), ""]
    o = r["tool_call_decision_oracle"]
    lines += ["## Tool-call decision oracle", "", json.dumps(o["counts"], sort_keys=True), "",
              md_table(["signal", "kind", "rows", "positives", "AUC / levels"],
                       [[k, v["kind"], v["rows"], v["positives"],
                         v.get("auc") if v["kind"] == "numeric" else json.dumps(v["levels"], sort_keys=True)]
                        for k, v in o["signal_auc"].items()]), "",
              "## Verdicts", "", "```json", json.dumps(r["verdicts"], indent=1, sort_keys=True), "```", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mode", choices=sorted(MODE_ROSTER), required=True)
    parser.add_argument("--roster", choices=sorted(FOLD_SPLITS), required=True)
    parser.add_argument("--arm", action="append", default=[], help="LABEL=RUN_ID/ATTEMPT (repeatable)")
    parser.add_argument("--primary")
    parser.add_argument("--replicate")
    parser.add_argument("--e4", help="RUN_ID/ATTEMPT of the sealed E4-1 attempt (Fold A read only)")
    parser.add_argument("--expect-e4-broken", type=int, default=None)
    parser.add_argument("--params", help="the tune run's params.json (read mode)")
    parser.add_argument("--params-sha256")
    parser.add_argument("--draws", type=int, default=BOOT_DRAWS)
    parser.add_argument("--lock", default=DEFAULT_LOCK)
    parser.add_argument("--data-root", default=DEFAULT_DATA_ROOT)
    parser.add_argument("--label", default=None, help="output sub-directory (default <mode>-<roster>)")
    args = parser.parse_args(argv)
    if args.mode == "read" and not (args.params and args.params_sha256):
        parser.error("read mode needs --params and --params-sha256 (the Fold B tuning output)")
    out = Path(args.data_root) / "analysis" / READ_ID / (args.label or f"{args.mode}-{args.roster}")
    if out.exists() and any(out.iterdir()):
        print(f"REFUSED: {out} already holds files", file=sys.stderr)
        return 5
    try:
        report = build(args)
    except ReadError as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1
    out.mkdir(parents=True, exist_ok=True)
    files = {"report.json": json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
             "tables.md": render(report)}
    if args.mode == "tune":
        files["params.json"] = json.dumps(report["params"], indent=2, sort_keys=True) + "\n"
    for name, text in files.items():
        (out / name).write_text(text, encoding="utf-8", newline="\n")
    content = {name: sha256_file(out / name) for name in sorted(files)}
    (out / "content-sha256.json").write_text(json.dumps(content, indent=2, sort_keys=True) + "\n",
                                             encoding="utf-8", newline="\n")
    print(json.dumps({"out": str(out), "content_sha256": content,
                      "verdicts": report.get("verdicts"), "params": report.get("params")}, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
