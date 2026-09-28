#!/usr/bin/env python3
"""CLI: the offline NULL of a sealed five-sample pool, then an explicit empty-entity rule read against it.

Owner decision 171 (2026-09-27); registration
``docs/readiness/2026-09-27-slurp-stage3-empty-entity-offline-v1/``. Read id
``SAEA-SLURP-STAGE3-EMPTY-ENTITY-OFFLINE-V1``. Primary pool: DEV-2000-ADDED's
sealed ROLL-3 pool (1,000 rows x 5 samples, scored per sample under
``slurp-slu-official-projected-v3``); TRAIN Fold A's ROLL-2 pool is read
beside it once its registered stage 1-3 read exists.

STAGE ``null`` (no scorer contact). The paired CI95 half-width between two
samples' entity answers under the projected-v3 scorer, measured with the
resampling that produced the instrument note's one-pool offline floor
(section 2c / 2d: 0.67 pp at n = 625): the aggregation read's own
``bootstrap`` (``scripts/analysis/slurp_sample_aggregation_offline_read.py``,
imported byte-unchanged) -- a PAIRED ROW bootstrap, rows resampled with
replacement by ``numpy.random.default_rng(20260915).integers(0, n, (10000,
n))``, each arm's pooled official counts re-summed on the SAME draws, the
percentile CI95 of the delta. The pooled official SLU-F1 (micro over the
word- and char-distance TP/FP/FN, the entity-only metric) is the primary
quantity; per-row SLU-F1, span-F1 and intent are reported beside it. It is
read for all ten sample-index pairs, and for each sample against
``R0-mean-single``. THE NULL is the MEAN over the ten pairs of the pooled
SLU-F1 half-width (the maximum is reported beside it). ``--with-cluster-variant``
adds the same ten pairs under the whole-utterance cluster bootstrap of the
instrument note's section 2e (``analysis.paired.resampled_statistic``), for
comparison only.

STAGE ``rule`` (five scorer contacts, on copies). THE RULE (registered, one
primary form): a row's EMPTINESS VOTE is the number of its well-formed
samples whose answer carries no entity; when the vote is at least
``--min-empty`` (registered 3 of 5, a majority), every sample of that row is
delivered with an EMPTY entity list and its scenario and action unchanged.
A malformed sample is never edited and never votes. Each edited copy is
scored ONCE through the registered scorer (``score_copy``: gold enters only
inside the official scorer), and the contrast is ``RULE-mean-single`` against
``R0-mean-single`` under the same bootstrap.

THE DECISION (fixed here, before any number is read). Primary metric: the
pooled official SLU-F1. The rule CLEARS on the pool when the SLU-F1 delta's
CI95 lower bound is above zero AND the point delta is at least the pool's
NULL from stage ``null`` (read from ``null.json``, never re-derived after the
rule is scored) AND the intent guard holds: the intent delta's CI95 lower
bound is at least minus the mean pairwise intent half-width of the same null.

No utterance text, transcript, gold label or model output is printed or
persisted: ``null.json`` and ``rule.json`` carry ids, counts, scores and
hashes. The edited copies under ``--out-dir`` carry rendered answer JSON, as
every score_copy caller's copies do, under the data root only.

``--dry-run`` validates every input and prints row, sample, vote and edit
COUNTS only; it computes no interval, scores nothing and writes nothing.

Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src python \\
      scripts/analysis/empty_entity_offline_read.py --pool dev2000-added --stage null \\
      --data-root "$SPEECHRL_DATA_DIR" [--dry-run]
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

READ_ID = "SAEA-SLURP-STAGE3-EMPTY-ENTITY-OFFLINE-V1"
SCHEMA_NULL = "saea-slurp-empty-entity-pool-null-v1"
SCHEMA_RULE = "saea-slurp-empty-entity-rule-read-v1"
AGGREGATION_READ = Path("scripts/analysis/slurp_sample_aggregation_offline_read.py")
SAMPLES = 5
REGISTERED_MIN_EMPTY = 3
METRICS = ("slu_f1_pp", "span_f1_pp", "intent_exact_pp", "per_row_slu_mean_pp")

POOLS: dict[str, dict[str, str]] = {
    "dev2000-added": {
        "role": "primary",
        "run_id": "SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-V1",
        "score_root": "analysis/SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-READ-V1",
        "scorer_id": "slurp-slu-official-projected-v3",
        "roster": "docs/receipts/rosters/slurp-dev-2000-added-v1.json",
    },
    "fold-a": {
        "role": "beside (after its registered stage 1-3 read exists)",
        "run_id": "SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-V1",
        "score_root": "analysis/SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-READ-V1",
        "scorer_id": "slurp-slu-official-projected-v3-train",
        "roster": "docs/receipts/rosters/slurp-evo-fold-a-v2.json",
    },
}


class EmptyEntityReadError(RuntimeError):
    """A sealed input is missing or does not have the shape this read needs."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def import_file(relpath: Path, name: str):
    path = REPO_ROOT / relpath
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise EmptyEntityReadError(f"cannot import {relpath}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module, sha256_file(path)


def sample_state(text: str) -> str:
    """``malformed`` / ``empty`` / ``entities`` for one rendered sample."""

    payload = json.loads(text)
    if not payload.get("scenario") and not payload.get("action"):
        return "malformed"
    return "empty" if not payload.get("entities") else "entities"


def half_width(interval) -> float:
    return (interval["hi"] - interval["lo"]) / 2.0


def load_pool(agg, root: Path, pool: dict[str, str]):
    score_root = root / pool["score_root"]
    if not (score_root / "render-manifest.json").is_file():
        raise EmptyEntityReadError(
            f"the pool's stage 1-3 read is absent at {score_root}; run its registered read first")
    sealed = agg.load_rollout_score_root(score_root, pool["scorer_id"], SAMPLES)
    ids = sorted(sealed["rendered"][0])
    for index in range(SAMPLES):
        if sorted(sealed["rendered"][index]) != ids or sorted(sealed["scored"][index]) != ids:
            raise EmptyEntityReadError(f"sample {index}: copy and score rows differ from sample 0")
    return score_root, sealed, ids


def base_arms(agg, sealed, ids):
    import numpy as np  # noqa: PLC0415

    arms = {}
    for index in range(SAMPLES):
        rows = sealed["scored"][index]
        arms[f"R0-sample-{index}"] = {
            "matrix": agg.counts_matrix(rows, ids),
            "row_f1": np.array([float(rows[s]["slu_f1_f1"]) for s in ids]),
        }
    arms["R0-mean-single"] = {
        "matrix": np.mean(np.stack([arms[f"R0-sample-{i}"]["matrix"] for i in range(SAMPLES)]), axis=0),
        "row_f1": np.mean(np.stack([arms[f"R0-sample-{i}"]["row_f1"] for i in range(SAMPLES)]), axis=0),
    }
    return arms


def cluster_variant(sealed, ids, roster_path: Path) -> dict[str, Any]:
    """The instrument note's section 2e resampling (whole-utterance clusters), for comparison."""

    from speech_aware_evidence_acquisition.analysis.paired import resampled_statistic  # noqa: PLC0415

    document = json.loads(roster_path.read_text(encoding="utf-8"))
    cluster = {}
    for item in document["items"]:
        sid = str(item["sample_id"])
        value = item.get("utterance_id")
        cluster[sid] = value if isinstance(value, str) and value else ":".join(sid.split(":")[:3])
    fields = ("slu_f1_word_tp", "slu_f1_word_fp", "slu_f1_word_fn",
              "slu_f1_char_tp", "slu_f1_char_fp", "slu_f1_char_fn")
    counts = {i: {s: tuple(float(sealed["scored"][i][s][f]) for f in fields) for s in ids} for i in range(SAMPLES)}

    def micro(c, chosen):
        tp = sum(c[s][0] + c[s][3] for s in chosen)
        fp = sum(c[s][1] + c[s][4] for s in chosen)
        fn = sum(c[s][2] + c[s][5] for s in chosen)
        p = 0.0 if tp == fp == 0 else tp / (tp + fp)
        r = 0.0 if tp == fn == 0 else tp / (tp + fn)
        return 0.0 if p == r == 0 else 2 * p * r / (p + r)

    widths = {}
    for i, j in itertools.combinations(range(SAMPLES), 2):
        result = resampled_statistic(
            sample_ids=ids, statistic=lambda chosen, i=i, j=j: micro(counts[j], chosen) - micro(counts[i], chosen),
            seed=20260915, n_replicates=10_000, ci_level=0.95, cluster_of=cluster.__getitem__,
        )
        widths[f"{i}-{j}"] = 100.0 * (result.ci_high - result.ci_low) / 2.0
    return {"pooled_slu_f1_half_width_pp": widths,
            "mean": statistics.mean(widths.values()), "max": max(widths.values()),
            "resampling": "whole-utterance cluster bootstrap (analysis.paired.resampled_statistic), section 2e"}


def stage_null(agg, sealed, ids, pool, args, out_dir: Path) -> dict[str, Any]:
    arms = base_arms(agg, sealed, ids)
    pairs: dict[str, Any] = {}
    widths = {metric: [] for metric in METRICS}
    for i, j in itertools.combinations(range(SAMPLES), 2):
        ci = agg.bootstrap({"L": arms[f"R0-sample-{i}"], "R": arms[f"R0-sample-{j}"]}, ids, "L")["R"]
        pairs[f"{i}-{j}"] = {metric: {"ci95": ci[metric], "half_width_pp": half_width(ci[metric])} for metric in METRICS}
        for metric in METRICS:
            widths[metric].append(half_width(ci[metric]))
    versus_mean = agg.bootstrap(arms, ids, "R0-mean-single")
    single = {
        f"sample_{i}": {metric: half_width(versus_mean[f"R0-sample-{i}"][metric]) for metric in METRICS}
        for i in range(SAMPLES)
    }
    summary = {metric: {"mean": statistics.mean(v), "median": statistics.median(v), "min": min(v), "max": max(v)}
               for metric, v in widths.items()}
    document = {
        "schema": SCHEMA_NULL, "read_id": READ_ID, "pool": args.pool, "pool_role": pool["role"],
        "authority": "owner decision 171 (2026-09-27)",
        "rows": len(ids), "samples": SAMPLES,
        "resampling": {"draws": agg.BOOTSTRAP_DRAWS, "seed": agg.BOOTSTRAP_SEED, "cluster": "row",
                       "implementation": ("slurp_sample_aggregation_offline_read.bootstrap, imported unchanged: "
                                          "the instrument note's section 2c/2d one-pool offline floor method")},
        "pairs": pairs,
        "pairwise_half_width_summary_pp": summary,
        "single_sample_vs_mean_single_half_width_pp": single,
        "null_pp": summary["slu_f1_pp"]["mean"],
        "null_definition": "mean over the ten sample-index pairs of the pooled official SLU-F1 CI95 half-width",
        "intent_guard_pp": summary["intent_exact_pp"]["mean"],
        "cluster_variant": (cluster_variant(sealed, ids, REPO_ROOT / pool["roster"])
                            if args.with_cluster_variant else None),
        "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "network": 0, "gpu": 0, "scorer": 0},
    }
    return document


def stage_rule(agg, sealed, ids, pool, args, out_dir: Path, null_doc) -> dict[str, Any]:
    import numpy as np  # noqa: PLC0415

    from speech_aware_evidence_acquisition.data.lock import load_lock  # noqa: PLC0415

    lock = load_lock(Path(args.lock))
    root = Path(args.data_root)
    arms = base_arms(agg, sealed, ids)
    votes = {s: sum(1 for i in range(SAMPLES) if sample_state(sealed["rendered"][i][s]) == "empty") for s in ids}
    fires = {s: votes[s] >= args.min_empty for s in ids}
    copies = {}
    edits = 0
    for index in range(SAMPLES):
        rows_out = []
        for s in ids:
            text = sealed["rendered"][index][s]
            if fires[s] and sample_state(text) == "entities":
                payload = json.loads(text)
                payload["entities"] = []
                text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
                edits += 1
            rows_out.append({"sample_id": s, "text": text})
        path = out_dir / f"rule-min{args.min_empty}-sample-{index}-outputs.jsonl"
        digest = agg.write_jsonl(path, rows_out)
        result, seconds = agg.score_copy(
            pool["scorer_id"], path, out_dir / f"rule-min{args.min_empty}-sample-{index}-{pool['scorer_id']}-scores.json",
            lock, root)
        scored = {str(r["sample_id"]): r for r in result["per_sample"]}
        arms[f"RULE-sample-{index}"] = {
            "matrix": agg.counts_matrix(scored, ids),
            "row_f1": np.array([float(scored[s]["slu_f1_f1"]) for s in ids]),
        }
        copies[f"sample_{index}"] = {"outputs_sha256": digest, "scoring_seconds": seconds}
    arms["RULE-mean-single"] = {
        "matrix": np.mean(np.stack([arms[f"RULE-sample-{i}"]["matrix"] for i in range(SAMPLES)]), axis=0),
        "row_f1": np.mean(np.stack([arms[f"RULE-sample-{i}"]["row_f1"] for i in range(SAMPLES)]), axis=0),
    }
    ci = agg.bootstrap(arms, ids, "R0-mean-single")["RULE-mean-single"]
    base = agg.summarise(arms["R0-mean-single"]["matrix"], arms["R0-mean-single"]["row_f1"])
    rule = agg.summarise(arms["RULE-mean-single"]["matrix"], arms["RULE-mean-single"]["row_f1"])
    delta = {metric: rule[metric] - base[metric] for metric in METRICS}
    null_pp, guard_pp = float(null_doc["null_pp"]), float(null_doc["intent_guard_pp"])
    clears = bool(ci["slu_f1_pp"]["lo"] > 0.0 and delta["slu_f1_pp"] >= null_pp
                  and ci["intent_exact_pp"]["lo"] >= -guard_pp)
    # FP / TP mass the rule removed, from the scorer's own counts (no gold is opened here).
    base_sum = arms["R0-mean-single"]["matrix"].sum(axis=0)
    rule_sum = arms["RULE-mean-single"]["matrix"].sum(axis=0)
    return {
        "schema": SCHEMA_RULE, "read_id": READ_ID, "pool": args.pool, "pool_role": pool["role"],
        "authority": "owner decision 171 (2026-09-27)",
        "rows": len(ids), "samples": SAMPLES, "min_empty": args.min_empty,
        "registered_min_empty": REGISTERED_MIN_EMPTY,
        "rows_fired": sum(fires.values()), "sample_edits": edits,
        "vote_histogram": {str(k): sum(1 for v in votes.values() if v == k) for k in range(SAMPLES + 1)},
        "null_pp": null_pp, "intent_guard_pp": guard_pp,
        "null_sha256": null_doc.get("_sha256"),
        "baseline_R0_mean_single": base, "rule_mean_single": rule,
        "delta_pp": delta, "ci95": ci,
        "mean_single_counts_removed": {
            "slu_word_plus_char_tp": float((base_sum[0] + base_sum[3]) - (rule_sum[0] + rule_sum[3])),
            "slu_word_plus_char_fp": float((base_sum[1] + base_sum[4]) - (rule_sum[1] + rule_sum[4])),
        },
        "decision_rule": ("CLEARS iff SLU-F1 CI95 lower bound > 0 AND SLU-F1 delta >= the pool NULL AND intent "
                          "CI95 lower bound >= -(mean pairwise intent half-width)"),
        "clears": clears if args.min_empty == REGISTERED_MIN_EMPTY else None,
        "copies": copies,
        "claim_boundary": ("OFFLINE, one sealed pool, development numbers only (decisions 28 and 86); a clear "
                           "licenses registering a flight with an in-chain A/A, never a gain claim. A --min-empty "
                           "other than the registered 3 is DESCRIPTIVE and carries no decision."),
        "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "network": 0, "gpu": 0,
                     "scorer": SAMPLES},
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pool", choices=sorted(POOLS), default="dev2000-added")
    parser.add_argument("--stage", choices=("null", "rule"), required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--lock", default="/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json")
    parser.add_argument("--out-dir", default=None, help=f"default: <data-root>/analysis/{READ_ID}/<pool>")
    parser.add_argument("--min-empty", type=int, default=REGISTERED_MIN_EMPTY)
    parser.add_argument("--with-cluster-variant", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if not 1 <= args.min_empty <= SAMPLES:
        raise EmptyEntityReadError(f"--min-empty must be in 1..{SAMPLES}")

    started = time.time()
    pool = POOLS[args.pool]
    root = Path(args.data_root)
    agg, agg_sha = import_file(AGGREGATION_READ, "_saea_sample_aggregation_offline_read")
    score_root, sealed, ids = load_pool(agg, root, pool)
    states = {s: [sample_state(sealed["rendered"][i][s]) for i in range(SAMPLES)] for s in ids}
    votes = {s: states[s].count("empty") for s in ids}
    counts = {
        "pool": args.pool, "stage": args.stage, "rows": len(ids), "samples": SAMPLES,
        "malformed_samples": sum(v.count("malformed") for v in states.values()),
        "empty_samples": sum(v.count("empty") for v in states.values()),
        "rows_all_samples_empty": sum(1 for v in votes.values() if v == SAMPLES),
        "rows_fired_at_min_empty": sum(1 for v in votes.values() if v >= args.min_empty),
        "sample_edits_at_min_empty": sum(
            states[s].count("entities") for s in ids if votes[s] >= args.min_empty),
        "min_empty": args.min_empty,
    }
    if args.dry_run:
        print(json.dumps({"dry_run": True, **counts}, indent=1, sort_keys=True))
        return 0

    out_dir = Path(args.out_dir) if args.out_dir else root / "analysis" / READ_ID / args.pool
    out_dir.mkdir(parents=True, exist_ok=True)
    inputs = {**pool, "aggregation_read_sha256": agg_sha,
              "render_manifest_sha256": sha256_file(score_root / "render-manifest.json")}
    if args.stage == "null":
        document = stage_null(agg, sealed, ids, pool, args, out_dir)
        document["inputs"] = inputs
        document["elapsed_seconds"] = time.time() - started
        digest = agg.write_json(out_dir / "null.json", document)
        print(json.dumps({"null_pp": document["null_pp"], "intent_guard_pp": document["intent_guard_pp"],
                          "pairwise": document["pairwise_half_width_summary_pp"]["slu_f1_pp"],
                          "null_sha256": digest, **counts}, indent=1, sort_keys=True))
        return 0
    null_path = out_dir / "null.json"
    if not null_path.is_file():
        raise EmptyEntityReadError("stage 'rule' reads the sealed null.json of stage 'null'; run it first")
    null_doc = json.loads(null_path.read_text(encoding="utf-8"))
    null_doc["_sha256"] = sha256_file(null_path)
    document = stage_rule(agg, sealed, ids, pool, args, out_dir, null_doc)
    document["inputs"] = inputs
    document["elapsed_seconds"] = time.time() - started
    digest = agg.write_json(out_dir / f"rule-min{args.min_empty}.json", document)
    print(json.dumps({"clears": document["clears"], "delta_slu_f1_pp": document["delta_pp"]["slu_f1_pp"],
                      "ci95_slu_f1": document["ci95"]["slu_f1_pp"], "null_pp": document["null_pp"],
                      "rule_sha256": digest, **counts}, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
