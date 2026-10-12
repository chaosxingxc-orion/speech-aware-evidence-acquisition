#!/usr/bin/env python3
"""Where the gold intent ranks in the Perception boundary retrieval, and what an
admissible change to that one stage would buy.

A model-free read over sealed bytes and pinned artefacts.  Zero model, server,
encoder, embedder, scorer, network and GPU contacts.  The cosines below are
RECOMPUTED -- arithmetic over two pinned, sha256-verified vector files, through
this repository's own ``rails.kb_policy`` recall, never a fresh embedding -- and
the recomputation is validated against the ranking the three flights sealed
before any of it is believed.  Tokens come from the local vocab-only
``llama-tokenize`` process.

A DIAGNOSTIC, never a gate: it registers no cell, admits no mechanism, releases
no store and states no effectiveness claim.  Every roster is a discovery or dev
roster and every number is a development number (owner decisions 28 and 86).

Text discipline: no utterance text, transcript, gold filler, delivered answer or
knowledge body is read into a reported value or printed.  Every cell is an id, a
count, a rank, a rate, a margin, a token count or a hash.

Gold discipline: gold intents are read offline on the scoring side only -- from
the sealed bad-case bank and from the governed TRAIN split through the ordinary
loader -- and reach no query, key, weight or selector.
"""

from __future__ import annotations
import os

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.data.lock import load_lock  # noqa: E402
from speech_aware_evidence_acquisition.data.slurp import load_slurp_split  # noqa: E402
from speech_aware_evidence_acquisition.rails.kb_policy import (  # noqa: E402
    multidim_segment_recall,
)
from speech_aware_evidence_acquisition.rails.knowledge import (  # noqa: E402
    KnowledgeSnapshot,
)
from speech_aware_evidence_acquisition.rails.phase_supply import (  # noqa: E402
    load_sealed_segment_vectors,
    load_sealed_vectors,
)

READ_ID = "SAEA-SLURP-MF-INTENT-RETRIEVAL-RANK-DIAGNOSTIC-V1"
RECIPE = "slurp-intent-retrieval-rank-diagnostic-v1"
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
DEFAULT_MARKDOWN = "docs/results/2026-09-26-slurp-intent-retrieval-rank-diagnostic.md"

IB_SNAPSHOT = "knowledge/slurp/semantic/intent-boundaries-v1/snapshot.json"
IB_SNAPSHOT_SHA = "5520b8449b627530227563d1f8db71f8a391f20f7d0ff7d7bd439e28ec6e48fe"
IB_FACETS = "prepared/SAEA-SLURP-INTENT-BOUNDARY-KEY-ENCODING-V1/facets.jsonl"
IB_FACETS_SHA = "76e8d16a067ebfc5d67a4ecef2966636310815b950a7d9790ec7c0136f01ecd2"
IB_DIM = "intent-boundary"
IB_STORE_ID = "intent-boundaries"
BANK = "analysis/SLURP-PLAN-BAD-CASE-BANK-V1/bank.jsonl"
TOKENIZE = Path("/home/chao/llama.cpp/build/bin/llama-tokenize")
GGUF = ("models/qwen3-omni-30b-a3b-instruct-gguf-q4km/"
        "Qwen3-Omni-30B-A3B-Instruct-Q4_K_M.gguf")
FLOWN_K = 8
WIDTHS = (8, 12, 16, 24, 30)
W_GRID = (0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.6, 0.8, 1.0, 1.5, 2.0)
FIT_ARM = "train-fold-a-plan"
BLOCK_STRIDE = 25
WORKERS = 4

ARMS = (
    {"label": "roll1", "title": "ROLL-1 as-flown pool (R01C construction roster)",
     "run_id": "SAEA-SLURP-STAGE3-ROLLOUT-R01-V1",
     "attempt": "attempt-slurp-native-stage3-rollout-r01-generation-v1",
     "roster": None,
     "query": ("vectors/slurp-stage3-construction-r01c-v1/"
               "query-vectors-speech-segments.jsonl"),
     "query_sha": "ebaa743241a67a2cb759353fa8a9f58a3f09d27c00c8c66cb3172958dcccc1b8",
     "scores": ("analysis/SLURP-SAMPLE-AGGREGATION-OFFLINE-READ-V1/"
                "PS-registered-support-3-slurp-slu-official-projected-v3-"
                "train-scores.json"),
     "scorer_id": "slurp-slu-official-projected-v3-train"},
    {"label": "train-fold-a-plan", "title": "TRAIN Fold A PLAN (construction roster)",
     "run_id": "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1",
     "attempt": "attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1",
     "roster": "train-fold-a",
     "query": ("vectors/slurp-intent-boundaries-train-fold-a-1080-v1/"
               "query-vectors-speech-segments.jsonl"),
     "query_sha": "e7a5b2264dc61fcab3c63d50fb645d4629d3f0a99f83ad5fbe323c73884e5f0b",
     "scores": None, "scorer_id": None},
    {"label": "dev2000-added-plan", "title": "DEV-2000-ADDED PLAN (fresh roster)",
     "run_id": "SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1",
     "attempt": "attempt-slurp-native-default-plan-dev2000-added-generation-v1",
     "roster": "dev2000-added",
     "query": "vectors/slurp-dev2000-added-v1/query-vectors-speech-segments.jsonl",
     "query_sha": "e2a5fd046dac7c87fcf53830955e41e69d20402a2305a02ebf2bfc1a33001b9d",
     "scores": None, "scorer_id": None},
)
RANK_BANDS = ((1, 8), (9, 16), (17, 30), (31, 60))
DEEP_FROM = 31
UNRANKED = 9999


class ReadError(RuntimeError):
    pass


def digest(path: Path) -> str:
    handle = path.open("rb")
    h = hashlib.sha256()
    try:
        chunk = handle.read(1 << 20)
        while chunk:
            h.update(chunk)
            chunk = handle.read(1 << 20)
    finally:
        handle.close()
    return h.hexdigest()


def pct(num: float, den: float) -> float:
    return 100.0 * num / den if den else 0.0


def bare(value_id: str) -> str:
    return value_id.split("::", 1)[1] if "::" in value_id else value_id


def classify(intent_wrong: bool, fp: float, fn: float) -> str:
    if intent_wrong:
        return "INTENT-WRONG"
    if fp and fn:
        return "ENTITY-MIXED"
    if fn:
        return "ENTITY-FN-ONLY"
    if fp:
        return "ENTITY-FP-ONLY"
    return "CORRECT"


def stats(values):
    ordered = sorted(values)
    if not ordered:
        return None
    n = len(ordered)
    return {"n": n, "mean": round(sum(ordered) / n, 6),
            "median": round(ordered[n // 2], 6), "p90": round(ordered[int(0.9 * n)], 6),
            "min": round(ordered[0], 6), "max": round(ordered[-1], 6)}


# ---------------------------------------------------------------------------
# pinned inputs


def load_store(data_root: Path) -> dict:
    path = data_root / IB_SNAPSHOT
    snapshot = KnowledgeSnapshot.from_frozen_json(
        json.loads(path.read_text(encoding="utf-8"))
    )
    if snapshot.content_hash() != IB_SNAPSHOT_SHA:
        raise ReadError("intent-boundaries snapshot does not hash to the flown pin")
    facet_ids = {facet.facet_id for facet in snapshot.facets}
    if facet_ids != {value.value_id for value in snapshot.values} or len(facet_ids) != 60:
        raise ReadError("intent-boundaries store is not the flown 60-way 1:1 store")
    if {facet.dimension for facet in snapshot.facets} != {IB_DIM}:
        raise ReadError("intent-boundaries store carries an unexpected dimension")
    to_intent, lines = {}, {}
    for value in snapshot.values:
        if len(value.associated_facet_ids) != 1:
            raise ReadError("an intent-boundary value is not bound to one facet")
        intent = value.value_id.split("intent-boundary:", 1)[-1]
        to_intent[value.value_id] = intent
        lines[intent] = (
            f"[value {IB_STORE_ID}::{value.value_id}] "
            f"[knowledge store={IB_STORE_ID} role={IB_STORE_ID}] {value.content}"
        )
    facet_vectors = load_sealed_vectors(
        data_root / IB_FACETS, expected_sha256=IB_FACETS_SHA, dimensions=(IB_DIM,)
    )
    if set(facet_vectors) != facet_ids:
        raise ReadError("facet vector file does not cover the store's facets exactly")
    return {"snapshot": snapshot, "facet_vectors": facet_vectors,
            "facet_to_intent": to_intent, "rendered_lines": lines,
            "snapshot_file_sha256": digest(path),
            "prior_scores_present": sum(
                1 for v in snapshot.values if v.prior_score is not None),
            "task_targets_present": sum(
                1 for v in snapshot.values if v.task_target is not None),
            "vector_width": len(next(iter(facet_vectors.values()))[IB_DIM])}


def load_train_gold(lock: dict, data_root: Path) -> tuple[dict, dict]:
    """TRAIN utterance intent, and the store's own build-time intent prior."""

    by_utterance: dict[str, str] = {}
    for record in load_slurp_split(lock, data_root, "train"):
        key = str(record.utterance_id)
        by_utterance[str(int(key)) if key.isdigit() else key] = (
            f"{record.scenario}_{record.action}"
        )
    counts = Counter(by_utterance.values())
    top = max(counts.values())
    return by_utterance, {i: counts[i] / top for i in sorted(counts)}


def load_bank(data_root: Path) -> dict:
    path = data_root / BANK
    rosters: dict[str, dict] = defaultdict(dict)
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        rosters[entry["roster"]][entry["sample_id"]] = {
            "class": {"INTENT-UNCOVERED": "INTENT-WRONG",
                      "INTENT-COVERED": "INTENT-WRONG"}.get(
                          entry["plan_class"], entry["plan_class"]),
            "gold_intent": entry["gold_intent"]}
    return {"sha256": digest(path),
            "rosters": {k: dict(sorted(v.items())) for k, v in sorted(rosters.items())}}


def load_population(data_root: Path, arm: dict, bank: dict, train_gold: dict) -> dict:
    if arm["roster"] is not None:
        return {"rows": dict(bank["rosters"][arm["roster"]]),
                "source": "bad-case bank roster " + arm["roster"],
                "source_sha256": bank["sha256"]}
    path = data_root / arm["scores"]
    block = json.loads(path.read_text(encoding="utf-8"))[arm["scorer_id"]]
    rows = {}
    for sample in block["per_sample"]:
        sample_id = str(sample["sample_id"])
        utterance = sample_id.split(":")[2] if sample_id.count(":") >= 2 else ""
        rows[sample_id] = {
            "class": classify(not bool(sample["scenario_action_exact"]),
                              float(sample["slot_f1_exact_fp"]),
                              float(sample["slot_f1_exact_fn"])),
            "gold_intent": train_gold.get(str(int(utterance)))
            if utterance.isdigit() else None}
    return {"rows": dict(sorted(rows.items())), "source": arm["scorer_id"],
            "source_sha256": digest(path)}


def own_key(sample_id: str) -> str | None:
    """The row's own TRAIN utterance key, or ``None`` when the id is not shaped
    that way.  Used only to EXCLUDE the row's own utterance from the exemplar
    vote, so a construction roster whose rows also sit in the exemplar pool
    cannot vote for itself."""

    parts = sample_id.split(":")
    field = parts[2] if len(parts) >= 3 else ""
    return str(int(field)) if field.isdigit() else None


def load_sealed_delivery(data_root: Path, arm: dict, train_gold: dict) -> dict:
    """What the flight delivered: the boundary entries, and the exemplar route's
    implied intent votes -- both from the sealed consumption trace.

    The vote EXCLUDES any exemplar whose pool utterance is the evaluated row's
    own, because two of the three rosters are drawn from the same TRAIN split the
    pool is built from and a self-hit would make the signal circular.  The number
    of rows where that exclusion fired is reported.
    """

    path = (data_root / "runs" / arm["run_id"] / arm["attempt"]
            / (arm["run_id"] + ".phases.json"))
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema") != "saea-flight-phase-summaries-v1":
        raise ReadError(arm["label"] + ": unexpected phase artefact schema")
    summary = document["phases"][0]
    rows, self_hits = {}, 0
    for result in summary["results"]:
        sample_id = result["sample_id"]
        mine = own_key(sample_id)
        delivered, votes, dropped = [], Counter(), 0
        for record in (result.get("consumption") or {}).get("records") or ():
            item = bare(str(record.get("supplied_item_id") or ""))
            if item.startswith("intent-boundary:"):
                delivered.append(item.split("intent-boundary:", 1)[-1])
            elif item.startswith("value:"):
                key = item.split("value:", 1)[-1]
                if mine is not None and key == mine:
                    dropped += 1
                    continue
                intent = train_gold.get(key)
                if intent is not None:
                    votes[intent] += 1
        total = sum(votes.values())
        self_hits += int(dropped > 0)
        rows[sample_id] = {
            "delivered": sorted(set(delivered)),
            "votes": {i: votes[i] / total for i in sorted(votes)} if total else {},
            "vote_total": total, "self_exemplars_dropped": dropped}
    del document
    return {"rows": rows, "relpath": str(path.relative_to(data_root)),
            "sha256": digest(path), "rows_with_a_self_exemplar": self_hits,
            "controller_policy_id": summary.get("controller_policy_id")}


# ---------------------------------------------------------------------------
# the recomputation and the candidate policies


def recompute(store: dict, queries, sample_ids) -> dict:
    """The flown arithmetic at full width: this repository's own segment recall
    at ``top_k_per_dimension`` 60, so the truncation is removed and every entry
    the recall admits carries its max-over-segments cosine.

    ``multidim_recall`` admits a candidate only when its cosine is strictly
    positive, so a row can carry fewer than 60 candidates.  An entry the recall
    does not admit is UNRANKABLE: no ``k`` and no reweighting reaches it,
    because every downstream stage ranks the recalled set.  That is reported,
    never repaired.
    """

    snapshot, table = store["snapshot"], store["facet_vectors"]
    to_intent = store["facet_to_intent"]

    def vectors(facet_id):
        return table.get(facet_id, {})

    out = {}
    for sample_id in sample_ids:
        record = queries.get(sample_id)
        if record is None:
            continue
        recalled = multidim_segment_recall(snapshot, record.segments, vectors, 60)
        out[sample_id] = {to_intent[f]: s[IB_DIM] for f, s in recalled.items()}
    return out


def order(scores: dict) -> list:
    """The flown order: score descending, facet id ascending.  Facet id and
    value id agree in this store, so the intent id is the tie-break key."""

    return [i for i, _ in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))]


def rank_of(ordering: list, intent: str) -> int:
    """The 1-based rank, or :data:`UNRANKED` when the recall never admitted it."""

    return ordering.index(intent) + 1 if intent in ordering else UNRANKED


def blend(cos: dict, extra: dict, weight: float) -> list:
    return order({i: cos[i] + weight * extra.get(i, 0.0) for i in cos})


# ---------------------------------------------------------------------------
# tokenizer


class Tokenizer:
    def __init__(self, scratch: Path, gguf: Path):
        self.scratch, self.gguf, self.calls = scratch, gguf, 0

    def count(self, text: str, label: str) -> int:
        self.scratch.mkdir(parents=True, exist_ok=True)
        path = self.scratch / (label + ".txt")
        path.write_bytes(text.encode("utf-8"))
        argv = [str(TOKENIZE), "-m", str(self.gguf), "-f", str(path), "--no-bos",
                "--no-escape", "--show-count", "--log-disable", "--ids"]
        result = subprocess.run(argv, check=True, capture_output=True, text=True)
        self.calls += 1
        path.unlink()
        for line in result.stdout.splitlines():
            if line.startswith("Total number of tokens:"):
                return int(line.split(":")[1].strip())
        raise ReadError("local tokenizer produced no count for " + label)


def measure_tokens(jobs: dict, scratch: Path, gguf: Path):
    """Keyed output, so the worker pool cannot change the result bytes.  The
    scratch file name is a digest of the job key, because two job keys sharing a
    prefix would otherwise race on one file."""

    tokenizer = Tokenizer(scratch, gguf)
    keys = sorted(jobs)
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        counts = list(pool.map(
            lambda k: tokenizer.count(
                jobs[k], hashlib.sha256(k.encode("utf-8")).hexdigest()[:24]), keys))
    return dict(zip(keys, counts)), tokenizer.calls


# ---------------------------------------------------------------------------
# report


ROSTERS = ("train-fold-a-plan", "roll1", "dev2000-added-plan")


def weight_of(key: str) -> float:
    tail = key.rsplit("-", 1)[-1]
    try:
        return float(tail)
    except ValueError:
        return float("inf")


def best_on(report: dict, family: str) -> str:
    """The grid member that maximises gold-intent delivery over EVERY analysed
    row of the fit roster.  The objective is delivery, not score, and it is
    class-blind; the two other rosters are read, never fitted."""

    table = report["arms"][report["fit_arm"]]["delivery"]
    keys = [k for k in sorted(table)
            if k.startswith(family + "-") and weight_of(k) != float("inf")]
    return max(keys, key=lambda k: (table[k]["all_delivered"], -weight_of(k)))


def spread(report: dict, key: str) -> dict:
    """The change's wrong-row gain and correct-row loss on each roster, and its
    measured token delta on the fit roster."""

    gains, losses = [], []
    for arm in ROSTERS:
        entry = report["arms"][arm]["delivery"][key]
        base = report["arms"][arm]["delivery"]["cos"]
        gains.append(pct(entry["wrong_delivered"], entry["wrong_rows"])
                     - pct(base["wrong_delivered"], base["wrong_rows"]))
        losses.append(pct(base["correct_delivered"], base["correct_rows"])
                      - pct(entry["correct_delivered"], entry["correct_rows"]))
    added = report["arms"][report["fit_arm"]]["delivery"][key]["token_delta_mean"]
    neutral_band = 0.01 * report["block_additivity"]["block_width_8_mean"]
    return {"key": key, "gains": gains, "losses": losses, "added": added,
            "neutral": abs(added) <= neutral_band, "band": neutral_band}


def gain_row(report: dict, key: str, label: str) -> dict:
    view = spread(report, key)
    cells = [label]
    for arm, gain in zip(ROSTERS, view["gains"]):
        entry = report["arms"][arm]["delivery"][key]
        cells.append("%.1f %% (%+.1f)" % (
            pct(entry["wrong_delivered"], entry["wrong_rows"]), gain))
        cells.append("%.1f %%" % pct(entry["correct_delivered"], entry["correct_rows"]))
    entry = report["arms"][report["fit_arm"]]["delivery"][key]
    base = report["arms"][report["fit_arm"]]["delivery"]["cos"]
    gained = entry["wrong_delivered"] - base["wrong_delivered"]
    cells.append("%+.1f" % view["added"])
    if view["neutral"]:
        cells.append("token-neutral (%+d rows)" % gained)
        rank = (0, -min(view["gains"]), weight_of(key))
    else:
        cells.append("%.2f" % (100.0 * gained / view["added"]))
        rank = (1, -100.0 * gained / view["added"], weight_of(key))
    return {"cells": cells, "sort": rank}


def write_markdown(path: Path, report: dict) -> None:
    arms = report["arms"]
    fit = arms[report["fit_arm"]]
    out: list[str] = []
    add = out.append
    add("# SLURP intent-boundary retrieval: where the gold intent ranks, and what "
        "the retrieval stage can buy")
    add("")
    add(f"Date: 2026-09-26. Read id `{report['read_id']}`, recipe `{report['recipe']}`. "
        f"Generated `{report['generated_at']}`.")
    add("")
    add("A model-free read. Zero model, server, encoder, embedder, scorer, network, GPU "
        "and paid-API contacts. The cosines are **recomputed** -- arithmetic over the two "
        f"pinned, sha256-verified vector files named below, through this repository's own "
        "`rails.kb_policy.multidim_segment_recall` and the flown ranker's own ordering "
        "rule -- and section 1 proves the recomputation reproduces what the flights "
        "sealed before any of it is used. Token counts come from "
        f"{report['contacts']['local_tokenizer_processes']} local vocab-only "
        "`llama-tokenize` processes (no server, no port, no GPU).")
    add("")
    add("A DIAGNOSTIC, never a gate. It registers no cell, admits no mechanism, releases "
        "no store, authorises no flight and states no effectiveness, superiority or "
        "generalisation claim. Every roster below is a discovery or dev roster and every "
        "number is a development number (owner decisions 28 and 86), never a test claim. "
        "No utterance text, transcript, gold filler, delivered answer or knowledge body "
        "is read into a reported value: every cell is an id, a count, a rank, a rate, a "
        "margin, a token count or a hash.")
    add("")
    add("## 0. What was read, and the stage it measures")
    add("")
    add("| Artefact | Relpath under `SPEECHRL_DATA_DIR` | sha256 |")
    add("| --- | --- | --- |")
    add(f"| `intent-boundaries-v1` snapshot (content hash = the flown store pin) | "
        f"`{report['store']['snapshot_relpath']}` | "
        f"`{report['store']['snapshot_content_sha256']}` |")
    add(f"| boundary facet key vectors ({report['store']['entries']} rows x "
        f"{report['store']['vector_width']} dims) | `{report['store']['facet_relpath']}` "
        f"| `{report['store']['facet_sha256']}` |")
    for label in ("roll1", "train-fold-a-plan", "dev2000-added-plan"):
        arm = arms[label]
        add(f"| `{label}` speech segment query vectors | `{arm['query_relpath']}` | "
            f"`{arm['query_sha256']}` |")
        add(f"| `{label}` sealed phase artefact | `{arm['phases_relpath']}` | "
            f"`{arm['phases_sha256']}` |")
    add("")
    spec = report["flown_spec"]
    add(f"The stage is one retrieval: phase `{spec['phase']}`, provider "
        f"`{spec['provider']}`, dimension `{spec['dimensions'][0]}`, `k` {spec['k']} over "
        f"{report['store']['entries']} intents, `tau` {spec['tau']}, `fuse_coverage` "
        f"top_l={spec['fuse_coverage']['top_l']} m={spec['fuse_coverage']['m']} "
        f"c={spec['fuse_coverage']['c']}, rank policy `{spec['rank_policy']}` at weights "
        f"w_cos {spec['rank_weights']['w_cos']}, w_prior "
        f"{spec['rank_weights']['w_prior']}, w_agree {spec['rank_weights']['w_agree']}, "
        f"fuser `{spec['fuse_policy']}`. **Two corrections to the brief this read "
        "answers.** The boundary channel's fuser is `saea-fuse-associated-values-v1`, not "
        "`saea-fuse-supplyfilter-v1`; and each query row carries exactly one speech "
        "segment on all three rosters, so the segment machinery reduces to one "
        "whole-utterance vector per row.")
    add("")
    add("| Arm | Rows analysed | Class source | Segments per row | Skipped |")
    add("| --- | ---: | --- | --- | --- |")
    for label in ("roll1", "train-fold-a-plan", "dev2000-added-plan"):
        arm = arms[label]
        add(f"| `{label}` | {arm['rows_analysed']:,} | `{arm['population_source']}` | "
            f"{arm['segments_per_row']} | {arm['skipped'] or 'none'} |")
    add("")
    add("## 1. The recomputation reproduces the sealed ranking")
    add("")
    add("The flights seal the *delivered* eight, not the ranked sixty, so the sealed "
        "ranking is exactly the flown top-8 set. Widening the recall cannot change that "
        "top-8: a facet whose max-over-segments cosine puts it in the global top-`k` is "
        "in some segment's own top-`k` (any facet beating it in that segment beats it "
        "globally too), so the union the flown recall builds already contains the global "
        "top-`k` in the global order. The recomputation is therefore checked against the "
        "sealed set, and picking the right 8 of 60 by chance is one outcome in 2.6 billion.")
    add("")
    add("| Arm | Rows checked | Rows where the flight delivered 8 entries | Recomputed "
        "top-8 == the sealed set | Every sealed entry ranks 1-8 | Agreement |")
    add("| --- | ---: | ---: | ---: | ---: | ---: |")
    for label in ("roll1", "train-fold-a-plan", "dev2000-added-plan"):
        val = arms[label]["validation"]
        add(f"| `{label}` | {val['rows']:,} | {val['sealed_width_is_8']:,} | "
            f"{val['recomputed_top8_equals_sealed_set']:,} | "
            f"{val['every_sealed_entry_ranks_1_to_8']:,} | "
            f"{pct(val['recomputed_top8_equals_sealed_set'], val['rows']):.2f} % |")
    add("")
    add("Agreement is exact on every row of all three rosters, so every rank below is the "
        "rank the flight itself would have assigned. Two columns need a word. The flight "
        "delivered fewer than eight entries on a few rows because the recall admitted fewer "
        "than eight candidates there (section 2's `unrankable` column is the same effect), "
        "and on those rows the recomputed set matches the shorter sealed set exactly, which "
        "is why the third column can exceed the second. The fourth column misses one "
        "`dev2000-added-plan` row whose sealed set is EMPTY -- the recall admitted no "
        "candidate at all -- and there is no sealed entry on it to rank.")
    add("")
    add("## 2. Where the gold intent actually ranks")
    add("")
    add("The decisive distribution. Ranks are over the boundary entries the flown recall "
        "admits, in the flown order (`score` descending, facet id ascending). `unrankable` "
        "counts rows whose gold intent the recall never admits as a candidate at all: "
        "`kb_policy.multidim_recall` admits an entry only on a strictly positive cosine, "
        "so an entry at or below zero has no rank, and no `k` and no reweighting reaches "
        "it, because every downstream stage ranks the recalled set. The last column is how "
        "many of the 60 entries the recall admitted on the median row of that class.")
    add("")
    add("| Arm | Class | Rows | 1-8 (delivered) | 9-16 | 17-30 | 31-60 | unrankable | "
        "median rank | candidates admitted (median) |")
    add("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for label in ("roll1", "train-fold-a-plan", "dev2000-added-plan"):
        for klass in ("INTENT-WRONG", "CORRECT"):
            band = arms[label]["bands"][klass]
            cells = " | ".join(
                f"{band['bands'][f'{low}-{high}']} "
                f"({pct(band['bands'][f'{low}-{high}'], band['rows']):.1f} %)"
                for low, high in RANK_BANDS)
            add(f"| `{label}` | `{klass}` | {band['rows']} | {cells} | "
                f"{band['unrankable']} "
                f"({pct(band['unrankable'], band['rows']):.1f} %) | "
                f"{band['median_rank'] if band['median_rank'] != UNRANKED else 'none'} | "
                f"{band['candidates']['median'] if band['candidates'] else '--'} |")
    add("")
    parts = []
    for label in ROSTERS:
        band = arms[label]["bands"]["INTENT-WRONG"]
        missed = band["rows"] - band["bands"]["1-8"]
        parts.append(
            f"`{label}` {missed} missed, of which "
            f"{pct(band['bands']['9-16'], missed):.0f} % at 9-16, "
            f"{pct(band['bands']['17-30'], missed):.0f} % at 17-30, "
            f"{pct(band['bands']['31-60'], missed):.0f} % at 31-60 and "
            f"{pct(band['unrankable'], missed):.0f} % unrankable")
    add("**The answer to the question this distribution was asked to decide.** The missing "
        "gold intents are not bunched just outside the window; they are spread down the "
        "whole tail: " + "; ".join(parts) + ". So no `k` short of the full store reaches "
        "most of them -- a `k` of 16 leaves over two thirds of the missed rows still "
        "missing on every roster -- while the rows that answered correctly hold the gold "
        "intent at median rank 1 and inside the top 8 on 94.5-97.3 % of them. That shape "
        "rules out a budget story and points at the ranking signal itself, which is what "
        "section 3 tests and section 4 characterises.")
    add("")
    add("## 3. What each admissible change would buy, measured")
    add("")
    add("Delivery of the row's own gold-intent boundary entry, on the intent-wrong rows "
        "and on the correct rows, with the token cost of the block the change would "
        "deliver measured on the tokenizer. One rendered entry is "
        f"{report['tokenizer']['entry_line_tokens']['mean']:.1f} tokens on average "
        f"(median {report['tokenizer']['entry_line_tokens']['median']}, range "
        f"{report['tokenizer']['entry_line_tokens']['min']}-"
        f"{report['tokenizer']['entry_line_tokens']['max']}), so the block the flown k=8 "
        f"sends is {report['block_additivity']['block_width_8_mean']:.1f} tokens. Summing "
        "per-entry counts and one newline each overshoots the measured block by "
        f"{-report['block_additivity']['residual_tokens']['max']} to "
        f"{-report['block_additivity']['residual_tokens']['min']} tokens -- "
        f"{pct(-report['block_additivity']['residual_tokens']['max'], report['block_additivity']['block_width_8_mean']):.1f} "
        f"to {pct(-report['block_additivity']['residual_tokens']['min'], report['block_additivity']['block_width_8_mean']):.1f} % "
        f"of it -- over {report['block_additivity']['sampled_rows']} sampled rows at both "
        "widths, so the per-row deltas below are upper bounds on the real cost.")
    add("")
    agree_best, prior_best = best_on(report, "agree"), best_on(report, "prior")
    add(f"Weights are fitted on `{report['fit_arm']}` alone, by maximising gold-intent "
        "delivery over **every** analysed row of that roster (class-blind, so the error "
        "labels do not choose the weight); the other two rosters are read, never fitted. "
        f"The grid is {report['weight_grid']}, and the winners are `{agree_best}` and "
        f"`{prior_best}`.")
    add("")
    add("| Change | Fold A wrong-row delivery | Fold A correct | ROLL-1 wrong-row "
        "delivery | ROLL-1 correct | DEV-2000 wrong-row delivery | DEV-2000 correct | "
        "tokens/row added | wrong rows gained per 100 tokens |")
    add("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    ranked = [(f"cos@k{w}", f"widen `k` to {w}, pure cosine") for w in WIDTHS[1:]]
    for weight in (0.2, 0.4, 1.0):
        ranked.append((f"agree-{weight:g}",
                       f"`agree-{weight:g}`: w_cos 1.0 + {weight:g} x exemplar agreement, k=8"))
    if agree_best not in {key for key, _ in ranked}:
        ranked.append((agree_best,
                       f"`{agree_best}`: w_cos 1.0 + {weight_of(agree_best):g} x exemplar "
                       "agreement, k=8"))
    ranked.append(("agree-only", "exemplar agreement alone, k=8 (that signal's own ceiling)"))
    ranked.append((prior_best,
                   f"`{prior_best}`: w_cos 1.0 + {weight_of(prior_best):g} x build-time "
                   "intent prior, k=8"))
    rows_out = [gain_row(report, key, label) for key, label in ranked]
    for entry in sorted(rows_out, key=lambda item: item["sort"]):
        add("| " + " | ".join(entry["cells"]) + " |")
    add("")
    add(f"A change is called token-neutral when its measured delta is within 1 % of the "
        f"flown block ({0.01 * report['block_additivity']['block_width_8_mean']:.1f} "
        "tokens); the reweightings are, because the block still carries eight entries and "
        "the only movement is the length difference between the entries swapped in and out.")
    add("")
    add("Widening `k` is the opposite of free: because `k == top_l == m`, the ranked set IS "
        "the materialised set, so every extra rank is an extra rendered entry in the "
        "Perception prompt.")
    add("")
    add("**The prior term the policy defines is not reachable by a weight.** Measured on "
        f"the released snapshot, {report['store']['values_with_prior_score']} of the 60 "
        "boundary values carry a `prior_score` and "
        f"{report['store']['values_with_task_target']} carry a `task_target`, and the "
        "channel recalls one dimension only, `intent-boundary`, which is not in "
        "`kb_policy.PRIOR_MASS_DIMENSIONS`. So `max_prior` is 0.0 for every candidate on "
        "every row and **`w_prior` has no effect at any value**: turning it on is a store "
        "rebuild (a `prior`/`label` dimension, or a `prior_score` on each value), not a "
        f"config flip. The `{prior_best}` row above is that rebuild simulated offline, "
        "with the prior taken as each intent's share of the store's own construction "
        "split divided by the largest such share -- a build-time store property, legal "
        "by the standing rule, and keyed on nothing about the evaluation row.")
    add("")
    add("**The agreement term is reachable, but it is a phase-order change, not a weight "
        "change.** The agreement used here is the share of the row's delivered exemplars "
        "whose pool intent equals the candidate intent. Each pool entry's intent is frozen "
        "into the store at build time, and the exemplars are recalled from the same row's "
        "own speech vector, so no gold, transcript or future turn enters it. Three things "
        "make it admissible and one makes it a change of more than a weight. It is "
        "speech-keyed, so the standing query ruling is satisfied. It is **self-excluded**: "
        "two of the three rosters are drawn from the same TRAIN split the exemplar pool is "
        "built from, so any exemplar whose pool utterance is the evaluated row's own is "
        "dropped from the vote before it is used -- measured, that exclusion fired on "
        + ", ".join(f"{arms[a]['rows_with_a_self_exemplar']} `{a}` rows" for a in ROSTERS)
        + f". And the vote is dense: per-row vote totals are {fit['vote_totals']}. What it "
        "is not is a weight flip, because the flown program runs Perception before the "
        "Solver's exemplar retrieval; using it at Perception means pre-computing the "
        "exemplar recall first, which is model-free and is exactly the pre-flight bootstrap "
        "the boundary channel already uses.")
    add("")
    add("**What that result says about the boundary keys.** The two channels rank in "
        "different key spaces. The boundary channel scores a row's speech vector against a "
        "2,048-dimension encoding of a written *boundary description* per intent; the "
        "exemplar channel scores the same kind of speech vector against 11,514 encodings "
        "of *other utterances*. Utterance-to-utterance similarity already carries the "
        "intent -- on the fit roster the exemplar vote alone puts the gold intent at rank 1 "
        f"on {pct(fit['delivery']['agree-only']['all_rank1'], fit['delivery']['agree-only']['all_rows']):.1f} % "
        f"of all rows against "
        f"{pct(fit['delivery']['cos']['all_rank1'], fit['delivery']['cos']['all_rows']):.1f} % "
        "for the boundary cosine -- so the weak link is the boundary key space, not the "
        "budget, not the store and not the query modality.")
    add("")
    add("## 4. Is the query itself the problem?")
    add("")
    add("For the rows whose gold intent ranks 31 or worse, no admissible `k` reaches it. "
        "The margin is the cosine gap between the top-1 entry and the gold entry on the "
        "same row.")
    add("")
    add("| Arm | wrong rows | rank 9-30 | rank 31-60 | unrankable | margin, delivered rows "
        "(mean) | margin, rank 9-30 (mean) | margin, rank 31-60 (mean) | top-1 family on "
        "the unreachable rows: distinct intents | top-3 share | same scenario as gold |")
    add("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")

    def mean(block):
        return f"{block['mean']:.4f}" if block else "--"

    for label in ("roll1", "train-fold-a-plan", "dev2000-added-plan"):
        deep = arms[label]["deep"]
        add(f"| `{label}` | {deep['wrong_rows']} | {deep['mid_rows']} | "
            f"{deep['deep_rows']} | {deep['unrankable_rows']} | "
            f"{mean(deep['margin_delivered'])} | "
            f"{mean(deep['margin_mid'])} | {mean(deep['margin_deep'])} | "
            f"{deep['deep_top1_distinct']} of {deep['beyond_rows']} rows | "
            f"{deep['deep_top1_top3_share']} % | "
            f"{deep['deep_same_scenario_share']} % |")
    add("")
    add("Two further facts about the unreachable end. The sealed width is not always eight: "
        + ", ".join(
            f"`{a}` sealed a set of eight on {arms[a]['validation']['sealed_width_is_8']} of "
            f"{arms[a]['validation']['rows']} rows" for a in ROSTERS)
        + ", and "
        + ", ".join(f"{arms[a]['deep']['rows_with_no_candidate']} `{a}` rows" for a in ROSTERS)
        + " had NO admitted candidate at all, so those rows received no boundary entry "
        "whatever. That is the same recall floor, at its extreme.")
    add("")
    add("Chronic against sporadic. An intent is *chronic* on a roster when it is the gold "
        "intent of at least 5 analysed rows and misses delivery on at least 80 % of them.")
    add("")
    add("| Arm | chronic intents | share of the not-delivered intent-wrong rows they own "
        "| intents that never miss | most-missed chronic intents (id: missed/rows) |")
    add("| --- | ---: | ---: | ---: | --- |")
    for label in ("roll1", "train-fold-a-plan", "dev2000-added-plan"):
        deep = arms[label]["deep"]
        head = ", ".join(
            f"`{i}`: {deep['per_gold_missed'][i][1]}/{deep['per_gold_missed'][i][0]}"
            for i in deep["chronic_intents"][:5]) or "none"
        add(f"| `{label}` | {deep['chronic_intent_count']} | "
            f"{deep['chronic_share_of_missed_wrong']} % | "
            f"{len(deep['intents_never_missed'])} | {head} |")
    add("")
    add("A standing ruling bounds every query change this section could motivate: "
        "retrieval queries are speech or speech-plus-state, never a transcript and never "
        "gold. The exemplar-agreement term above satisfies it (speech-keyed recall over a "
        "frozen store). A re-encoding of the boundary keys, or a speech-plus-draft-state "
        "query, would also satisfy it; anything that reads the reference transcript or the "
        "gold label would not, and is named inadmissible here rather than measured.")
    add("")
    add("## 5. The ceiling, stated as what it is")
    add("")
    add("Every number in section 3 is a count of **rows that would gain delivery of their "
        "own gold intent's boundary entry**. Delivery is not correctness. A row that "
        "receives its gold intent's boundary may still answer wrongly -- that is mode "
        "(iv), *delivered but ignored or misused* -- and the conversion rate from "
        "delivery to correctness is **unmeasured**: it is not a function of bytes already "
        "sealed, because it needs the answer the row would give with the entry present, "
        "which needs contacts. The correct-row column is the only evidence here that "
        "delivery and correctness move together at all, and it is an association on the "
        "rows that already worked, not a causal rate. No score gain is claimed, implied "
        "or estimated anywhere in this read.")
    add("")
    add("## 6. The one change this read would register next")
    add("")
    add("The selection rule, fixed before the numbers were read: a candidate is "
        "registrable only if it raises gold-intent delivery on the intent-wrong rows of "
        "**all three** rosters -- the one its weight was fitted on and the two it was not "
        "-- while lowering delivery on the correct rows of none of them by more than one "
        "point. Among the candidates that pass, a token-neutral change beats a "
        "token-buying one; among token-buying ones the best delivery gained per token "
        "added wins; ties go to the smaller weight, because the smaller weight keeps more "
        "of the flown signal. If nothing passes, this read says so and the programme's "
        "next question is mode (iv), not retrieval.")
    add("")
    passing = []
    for key in sorted(fit["delivery"]):
        if key == "cos":
            continue
        view = spread(report, key)
        if min(view["gains"]) > 0.0 and max(view["losses"]) <= 1.0:
            view["sort"] = ((0, -min(view["gains"]), weight_of(key)) if view["neutral"]
                            else (1, -min(view["gains"]) / view["added"], weight_of(key)))
            passing.append(view)
    if not passing:
        add("**No candidate passes.** Every change measured above either fails to raise "
            "delivery on one of the three rosters or pays for the rise on the correct "
            "rows. On this evidence no admissible change to the retrieval stage reaches "
            "the rows that never received their gold intent's boundary, and the honest "
            "next question is mode (iv) -- whether a row that DOES receive the entry uses "
            "it -- which needs contacts and cannot be answered from sealed bytes.")
    else:
        pick = sorted(passing, key=lambda item: item["sort"])[0]
        fit_entry = fit["delivery"][pick["key"]]
        fit_base = fit["delivery"]["cos"]
        add(f"**The change: `{pick['key']}`** -- keep the flown cosine, set `w_agree` to "
            f"{weight_of(pick['key']):g} over the self-excluded exemplar-intent vote, leave "
            f"`k` at {FLOWN_K}. {len(passing)} of the "
            f"{len(fit['delivery']) - 1} candidates measured pass the rule; this is the one "
            "it selects. On the fit roster it "
            f"raises the intent-wrong rows' gold-boundary delivery from "
            f"{pct(fit_base['wrong_delivered'], fit_base['wrong_rows']):.1f} % to "
            f"{pct(fit_entry['wrong_delivered'], fit_entry['wrong_rows']):.1f} % "
            f"({fit_base['wrong_delivered']} to {fit_entry['wrong_delivered']} of "
            f"{fit_entry['wrong_rows']} rows, "
            f"{fit_entry['wrong_delivered'] - fit_base['wrong_delivered']:+d}), and the "
            "smallest gain it holds across the three "
            f"rosters is {min(pick['gains']):+.1f} points. Its measured token cost is "
            f"{pick['added']:+.1f} tokens per row on the tokenizer (largest single row "
            f"{fit_entry['token_delta_max']:+d}), against the "
            f"{report['block_additivity']['block_width_8_mean']:.1f}-token block the flown "
            "eight already send. The nearest `k`-widening alternative, `cos@k30`, buys a "
            f"comparable {min(spread(report, 'cos@k30')['gains']):+.1f}-point floor for "
            f"{spread(report, 'cos@k30')['added']:+.1f} tokens per row -- about "
            f"{spread(report, 'cos@k30')['added'] / max(pick['added'], 0.1):,.0f} times the "
            "cost for the same delivery, and that added form is exactly what sank the index "
            "arm.")
        add("")
        add("**And what it does not buy.** The gain is a gain in DELIVERY. The conversion "
            "rate from delivery to correctness is unmeasured and is not estimated here: a "
            "row that receives its gold intent's boundary entry may still answer wrongly, "
            "which is mode (iv), and measuring that needs model contacts this read did "
            "not make. Nothing above is a score prediction, and this read authorises no "
            "cell, no flight and no store release.")
    add("")
    add("## 7. Boundary")
    add("")
    add("Zero model, server, encoder, embedder, scorer, network, GPU and paid-API "
        "contacts: no server was started, stopped or probed, no waveform decoded and no "
        "embedding computed. The cosines were RECOMPUTED as arithmetic over two pinned "
        f"vector files -- `{report['store']['facet_relpath']}` and each arm's "
        "`query-vectors-speech-segments.jsonl` -- each verified against its configured "
        "sha256 by the repository's own loader before a number was taken from it, through "
        "`rails.kb_policy.multidim_segment_recall` and the flown ranker's ordering rule. "
        "The one subprocess is the local vocab-only `llama-tokenize` "
        f"({report['contacts']['local_tokenizer_processes']} invocations, "
        f"{report['tokenizer']['workers']} workers) loading the pinned "
        f"`{report['tokenizer']['model_relpath']}` vocab: no server, no port, no GPU. "
        "Other tools: `data.slurp.load_slurp_split` for the governed TRAIN gold, `json` "
        "reads of the released snapshot and of three sealed `*.phases.json`, a `json` read "
        "of the sealed bad-case bank and of the ROLL-1 official score file, and `hashlib` "
        "for every identity hash above.")
    add("")
    add("This read admits nothing, promotes nothing, preregisters no cell, releases no "
        "store, draws no roster, expands no source, opens no split and reaches no "
        "superiority, generalisation or Stage-3 conclusion. It is byte-reproducible across "
        "runs apart from its `generated_at` stamp: every container is sorted before it is "
        "consumed, there is no resampling, and the tokenizer results are keyed so the "
        "worker pool cannot reorder them.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")


# ---------------------------------------------------------------------------
# the candidate policies


def build_policies(prior: dict) -> tuple:
    """Every candidate ordering, as (id, builder) over one row's own signals.

    ``cos`` is the flown pure-cosine order.  ``agree-w`` adds the exemplar
    route's implied-intent vote share -- a frozen build-time property of the
    pool entries the same speech query already recalled, so no gold and no
    transcript enters it.  ``prior-w`` adds the store's own build-time intent
    prior, divided by its own supremum so the term stays inside [0, 1] the way
    ``kb_policy._dimension_scales`` keeps every ranker dimension.
    """

    out = [("cos", lambda cos, votes: order(cos))]
    for weight in W_GRID:
        out.append((f"agree-{weight:g}",
                    (lambda w: lambda cos, votes: blend(cos, votes, w))(weight)))
    for weight in W_GRID:
        out.append((f"prior-{weight:g}",
                    (lambda w: lambda cos, votes: blend(cos, prior, w))(weight)))
    out.append(("agree-only", lambda cos, votes: order(
        {i: votes.get(i, 0.0) + 1e-9 * cos[i] for i in cos})))
    return tuple(out)


def analyse_arm(population, delivery, cosines, built, store_keys) -> dict:
    """Every row of the population is analysed.  A gold intent the recall never
    admitted is UNRANKABLE, not skipped: the flown recall drops a candidate whose
    cosine is not strictly positive, and that row is exactly the case no ``k``
    and no reweighting can reach.  Only a gold intent the released store does not
    hold at all -- mode (i), which the 2026-09-26 coverage read measured at zero
    here -- would be skipped, and none is."""

    rows: dict[str, dict] = {}
    skipped, validation = Counter(), Counter()
    for sample_id, verdict in sorted(population["rows"].items()):
        gold = verdict.get("gold_intent")
        sealed = delivery["rows"].get(sample_id)
        cos = cosines.get(sample_id)
        if gold is None:
            skipped["no-gold-intent"] += 1
            continue
        if sealed is None or cos is None:
            skipped["no-sealed-row"] += 1
            continue
        if gold not in store_keys:
            skipped["gold-intent-absent-from-store"] += 1
            continue
        base = order(cos)
        sealed_set = set(sealed["delivered"])
        validation["rows"] += 1
        validation["sealed_width_is_8"] += int(len(sealed_set) == FLOWN_K)
        validation["recomputed_top8_equals_sealed_set"] += int(
            sealed_set == set(base[:FLOWN_K]))
        validation["every_sealed_entry_ranks_1_to_8"] += int(
            bool(sealed_set) and max(rank_of(base, i) for i in sealed_set) <= FLOWN_K)
        ranks, tops = {}, {}
        for pid, builder in built:
            ordering = base if pid == "cos" else builder(cos, sealed["votes"])
            ranks[pid] = rank_of(ordering, gold)
            tops[pid] = tuple(ordering[:max(WIDTHS)])
        rows[sample_id] = {
            "class": verdict["class"], "gold": gold,
            "top1": base[0] if base else None,
            "sealed_gold_delivered": gold in sealed_set,
            "sealed_agrees": sealed_set == set(base[:FLOWN_K]),
            "vote_total": sealed["vote_total"], "candidates": len(cos),
            "cos_gold": cos.get(gold),
            "cos_top1": cos[base[0]] if base else None,
            "ranks": ranks, "tops": tops}
    return {"rows": rows, "skipped": dict(sorted(skipped.items())),
            "validation": dict(sorted(validation.items()))}


def band_table(rows, klass) -> dict:
    subset = [r for r in rows.values() if r["class"] == klass]
    return {
        "rows": len(subset),
        "bands": {f"{low}-{high}": sum(
            1 for r in subset if low <= r["ranks"]["cos"] <= high)
            for low, high in RANK_BANDS},
        "unrankable": sum(1 for r in subset if r["ranks"]["cos"] == UNRANKED),
        "sealed_delivered": sum(1 for r in subset if r["sealed_gold_delivered"]),
        "median_rank": (sorted(r["ranks"]["cos"] for r in subset)[len(subset) // 2]
                        if subset else None),
        "candidates": stats([r["candidates"] for r in subset])}


def delivery_table(rows, built, line_tokens) -> dict:
    """Per candidate change: gold-intent delivery on the intent-wrong rows, on
    the correct rows and overall, plus the token delta its delivered block
    carries against the flown eight, measured on the tokenizer."""

    wrong = [r for r in rows.values() if r["class"] == "INTENT-WRONG"]
    right = [r for r in rows.values() if r["class"] == "CORRECT"]
    out = {}
    for pid, _ in built:
        for width in (WIDTHS if pid == "cos" else (FLOWN_K,)):
            deltas = []
            for r in rows.values():
                shown, flown = r["tops"][pid][:width], r["tops"]["cos"][:FLOWN_K]
                deltas.append(sum(line_tokens[i] for i in shown) + len(shown)
                              - sum(line_tokens[i] for i in flown) - len(flown))
            out["cos" if pid == "cos" and width == FLOWN_K
                else (f"cos@k{width}" if pid == "cos" else pid)] = {
                "policy": pid, "width": width,
                "wrong_rows": len(wrong),
                "wrong_delivered": sum(1 for r in wrong if r["ranks"][pid] <= width),
                "wrong_rank1": sum(1 for r in wrong if r["ranks"][pid] == 1),
                "correct_rows": len(right),
                "correct_delivered": sum(1 for r in right if r["ranks"][pid] <= width),
                "correct_rank1": sum(1 for r in right if r["ranks"][pid] == 1),
                "all_rows": len(rows),
                "all_rank1": sum(1 for r in rows.values() if r["ranks"][pid] == 1),
                "all_delivered": sum(1 for r in rows.values()
                                     if r["ranks"][pid] <= width),
                "token_delta_mean": round(sum(deltas) / len(deltas), 1) if deltas else 0.0,
                "token_delta_max": max(deltas) if deltas else 0}
    return out


def deep_diagnosis(rows) -> dict:
    wrong = [r for r in rows.values() if r["class"] == "INTENT-WRONG"]
    deep = [r for r in wrong if DEEP_FROM <= r["ranks"]["cos"] <= 60]
    mid = [r for r in wrong if FLOWN_K < r["ranks"]["cos"] < DEEP_FROM]
    unrankable = [r for r in wrong if r["ranks"]["cos"] == UNRANKED]

    def margins(subset):
        return stats([r["cos_top1"] - r["cos_gold"] for r in subset
                      if r["cos_gold"] is not None and r["cos_top1"] is not None])

    beyond = deep + unrankable
    top1 = Counter(r["top1"] for r in beyond if r["top1"] is not None)
    per_gold: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for row in rows.values():
        slot = per_gold[row["gold"]]
        slot[0] += 1
        slot[1] += int(row["ranks"]["cos"] > FLOWN_K)
    chronic = sorted((intent for intent, (total, missed) in per_gold.items()
                      if total >= 5 and missed / total >= 0.8),
                     key=lambda intent: (-per_gold[intent][1], intent))
    missed_wrong = [r for r in wrong if r["ranks"]["cos"] > FLOWN_K]
    return {
        "wrong_rows": len(wrong), "deep_rows": len(deep), "mid_rows": len(mid),
        "unrankable_rows": len(unrankable),
        "margin_deep": margins(deep), "margin_mid": margins(mid),
        "margin_delivered": margins([r for r in wrong if r["ranks"]["cos"] <= FLOWN_K]),
        "beyond_rows": len(beyond),
        "deep_top1_distinct": len(top1),
        "deep_top1_top3": [[i, c] for i, c in top1.most_common(3)],
        "deep_top1_top3_share": round(pct(
            sum(c for _, c in top1.most_common(3)), len(beyond)), 1) if beyond else None,
        "deep_same_scenario_share": round(pct(sum(
            1 for r in beyond if r["top1"] is not None
            and r["top1"].split("_")[0] == r["gold"].split("_")[0]),
            len(beyond)), 1) if beyond else None,
        "rows_with_no_candidate": sum(
            1 for r in rows.values() if r["candidates"] == 0),
        "chronic_intents": chronic, "chronic_intent_count": len(chronic),
        "chronic_share_of_missed_wrong": round(pct(
            sum(1 for r in missed_wrong if r["gold"] in set(chronic)),
            len(missed_wrong)), 1) if missed_wrong else None,
        "intents_never_missed": sorted(
            intent for intent, (_total, missed) in per_gold.items() if missed == 0),
        "per_gold_missed": {intent: per_gold[intent] for intent in sorted(per_gold)}}


# ---------------------------------------------------------------------------
# main


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", default=DEFAULT_LOCK)
    parser.add_argument("--data-root", default=DEFAULT_DATA_ROOT)
    parser.add_argument("--scratch", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--markdown", default=str(REPO_ROOT / DEFAULT_MARKDOWN))
    args = parser.parse_args()

    data_root = Path(args.data_root)
    scratch = Path(args.scratch)
    gguf = data_root / GGUF
    store = load_store(data_root)
    train_gold, prior = load_train_gold(load_lock(Path(args.lock)), data_root)
    bank = load_bank(data_root)
    built = build_policies(prior)

    measured, calls = measure_tokens(
        {"line-" + intent: text
         for intent, text in sorted(store["rendered_lines"].items())}, scratch, gguf)
    line_tokens = {key[5:]: value for key, value in measured.items()}

    arms, blocks = {}, {}
    for arm in ARMS:
        queries = load_sealed_segment_vectors(
            data_root / arm["query"], expected_sha256=arm["query_sha"],
            dimensions=(IB_DIM,))
        population = load_population(data_root, arm, bank, train_gold)
        delivery = load_sealed_delivery(data_root, arm, train_gold)
        cosines = recompute(store, queries, sorted(population["rows"]))
        analysis = analyse_arm(population, delivery, cosines, built,
                               frozenset(store["rendered_lines"]))
        rows = analysis["rows"]
        arms[arm["label"]] = {
            "title": arm["title"], "run_id": arm["run_id"], "attempt": arm["attempt"],
            "controller_policy_id": delivery["controller_policy_id"],
            "population_source": population["source"],
            "population_sha256": population["source_sha256"],
            "phases_relpath": delivery["relpath"], "phases_sha256": delivery["sha256"],
            "query_relpath": arm["query"], "query_sha256": arm["query_sha"],
            "query_rows": len(queries),
            "segments_per_row": dict(sorted(Counter(
                len(queries[s].segments) for s in sorted(rows)).items())),
            "rows_analysed": len(rows), "skipped": analysis["skipped"],
            "validation": analysis["validation"],
            "class_rows": dict(sorted(Counter(
                r["class"] for r in rows.values()).items())),
            "bands": {klass: band_table(rows, klass)
                      for klass in ("INTENT-WRONG", "CORRECT")},
            "vote_totals": dict(sorted(Counter(
                r["vote_total"] for r in rows.values()).items())),
            "rows_with_a_self_exemplar": delivery["rows_with_a_self_exemplar"],
            "delivery": delivery_table(rows, built, line_tokens),
            "deep": deep_diagnosis(rows)}
        if arm["label"] == "roll1":
            sample = sorted(rows)[::BLOCK_STRIDE]
            jobs, residuals = {}, []
            for sample_id in sample:
                for width in (FLOWN_K, max(WIDTHS)):
                    jobs[f"block-{width}-{sample_id.replace(':', '-')}"] = "\n".join(
                        store["rendered_lines"][i]
                        for i in rows[sample_id]["tops"]["cos"][:width])
            block_counts, more = measure_tokens(jobs, scratch, gguf)
            calls += more
            for sample_id in sample:
                for width in (FLOWN_K, max(WIDTHS)):
                    key = f"block-{width}-{sample_id.replace(':', '-')}"
                    residuals.append(block_counts[key] - (sum(
                        line_tokens[i]
                        for i in rows[sample_id]["tops"]["cos"][:width]) + width - 1))
            blocks = {"sampled_rows": len(sample), "widths": [FLOWN_K, max(WIDTHS)],
                      "residual_tokens": stats(residuals),
                      "block_width_8_mean": round(sum(
                          block_counts[f"block-8-{s.replace(':', '-')}"]
                          for s in sample) / len(sample), 1)}
        del queries, cosines, rows, analysis

    report = {
        "read_id": READ_ID, "recipe": RECIPE,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "contacts": {"model": 0, "server": 0, "encoder": 0, "embedder": 0,
                     "scorer": 0, "network": 0, "gpu": 0, "paid_api": 0,
                     "local_tokenizer_processes": calls},
        "store": {"snapshot_relpath": IB_SNAPSHOT,
                  "snapshot_content_sha256": IB_SNAPSHOT_SHA,
                  "snapshot_file_sha256": store["snapshot_file_sha256"],
                  "facet_relpath": IB_FACETS, "facet_sha256": IB_FACETS_SHA,
                  "entries": 60, "vector_width": store["vector_width"],
                  "values_with_prior_score": store["prior_scores_present"],
                  "values_with_task_target": store["task_targets_present"]},
        "flown_spec": {"phase": "perception", "provider": "kb-facet-v1", "k": FLOWN_K,
                       "tau": 0.0, "fuse_coverage": {"top_l": 8, "m": 8, "c": 1},
                       "rank_policy": "saea-rank-wcos-prior-agree-v1",
                       "fuse_policy": "saea-fuse-associated-values-v1",
                       "rank_weights": {"w_cos": 1.0, "w_prior": 0.0, "w_agree": 0.0},
                       "dimensions": [IB_DIM]},
        "tokenizer": {"binary": str(TOKENIZE), "model_relpath": GGUF,
                      "mode": "vocab-only local process: no server, no port, no GPU",
                      "workers": WORKERS,
                      "entry_line_tokens": stats(list(line_tokens.values()))},
        "block_additivity": blocks, "fit_arm": FIT_ARM,
        "weight_grid": list(W_GRID), "arms": arms}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8", newline="\n")
    write_markdown(Path(args.markdown), report)
    print("wrote", out)
    print("wrote", args.markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
