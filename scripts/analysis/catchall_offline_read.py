#!/usr/bin/env python3
"""CLI: the OFFLINE read of a catch-all intent rule over a sealed five-sample Solver pool.

Owner decision 171 (2026-09-27); registration
``docs/readiness/2026-09-27-slurp-stage3-catchall-offline-v1/``. Read id
``SAEA-SLURP-STAGE3-CATCHALL-OFFLINE-V1``.

THE RULE (registered, one primary form, no tuning). The signal is the row's
``agree-1`` vote -- the self-excluded share of the row's own top-20 sealed
TRAIN-exemplar recall whose frozen build-time ``task_target`` is each
intent, the pre-computed ``saea-phase-agreement-v1`` table the AGREE arm
consumes (``prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-*``). It reaches
the all-utterances catch-all signal of the boundary-key diagnostic (section
7) without a boundary rebuild. The rule MARKS a row when
``intent-boundary:general_quirky`` holds the STRICT maximum share of that
vote (a tie never marks). On a marked row, every sample whose parsed intent
is not ``general_quirky`` is delivered with scenario ``general`` and action
``quirky``; its entity list is left byte-unchanged. An unmarked row, and a
malformed sample, are never edited.

THE READ. The rule is applied to each of the five sample copies of the
pool's registered stage 1-3 read (``stage3_rollout_score.py`` render /
score), each edited copy is scored ONCE through the SAME registered scorer
(``score_copy``: gold enters only inside the official scorer, exactly as
every offline read of this programme), and the contrast is the aggregation
read's own (``scripts/analysis/slurp_sample_aggregation_offline_read.py``):
``RULE-mean-single`` (the mean of the five edited copies' count matrices)
against ``R0-mean-single`` (the mean of the five unedited copies'), paired
row bootstrap, 10,000 draws, seed 20260915, percentile CI95 -- the resampling
that measured the instrument note's 0.67 pp floor at n = 625 (section 2c),
imported byte-unchanged, not re-implemented.

THE DECISION (fixed here, before any number is read). Primary metric: intent
accuracy (the rule edits intents only). The rule CLEARS on a pool when the
intent delta's CI95 lower bound is above zero AND the point delta is at least
the pool's offline floor, ``0.67 * sqrt(625 / n)`` pp (the instrument note's
section 2d floor scaled by ``scripts/checks/stage3_effect_floor_check.py``'s
own arithmetic: 0.5097 pp at Fold A's 1,080 rows, 0.5299 pp at
DEV-2000-ADDED's 1,000), AND the official SLU-F1 guard does not fall: its
CI95 lower bound is at least minus that same floor. A flight is registered
only if the primary pool (ROLL-2, TRAIN Fold A) clears; DEV-2000-ADDED
(ROLL-3) is read beside it as the fresh-roster replication.

No utterance text, transcript, gold label or model output is printed or
persisted: ``report.json`` carries ids, counts, scores and hashes. The edited
COPIES under ``--out-dir`` carry rendered answer JSON, as every score_copy
caller's copies do, and are written under the data root, never the repository.

``--dry-run`` validates every input (hashes, rows, samples, the agreement
table's coverage) and prints row, mark and edit COUNTS only; it scores
nothing and writes nothing.

Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src python \\
      scripts/analysis/catchall_offline_read.py --pool fold-a --data-root "$SPEECHRL_DATA_DIR" [--dry-run]
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

READ_ID = "SAEA-SLURP-STAGE3-CATCHALL-OFFLINE-V1"
SCHEMA = "saea-slurp-catchall-offline-read-v1"
AGGREGATION_READ = Path("scripts/analysis/slurp_sample_aggregation_offline_read.py")
CATCH_ALL = "general_quirky"
CATCH_ALL_KEY = f"intent-boundary:{CATCH_ALL}"
CATCH_ALL_SCENARIO, CATCH_ALL_ACTION = "general", "quirky"
SAMPLES = 5
#: The instrument note's section 2d offline floor, anchored at n = 625.
OFFLINE_FLOOR_PP, OFFLINE_FLOOR_N = 0.67, 625

POOLS: dict[str, dict[str, str]] = {
    "fold-a": {
        "role": "primary",
        "run_id": "SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-V1",
        "attempt_id": "attempt-slurp-native-stage3-roll-2-fold-a-v1-generation",
        "score_root": "analysis/SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-READ-V1",
        "scorer_id": "slurp-slu-official-projected-v3-train",
        "agreement_relpath": "prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-A-V1/agreement.jsonl",
        "agreement_sha256": "018ca6ef0d10bbf8d19645994420820faf7f31961cf91a6080116e4b434016c1",
    },
    "dev2000-added": {
        "role": "fresh-roster replication",
        "run_id": "SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-V1",
        "attempt_id": "attempt-slurp-native-stage3-roll-3-dev2000-added-v1-generation",
        "score_root": "analysis/SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-READ-V1",
        "scorer_id": "slurp-slu-official-projected-v3",
        "agreement_relpath": "prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-DEV2000-ADDED-V1/agreement.jsonl",
        "agreement_sha256": "283bd9f58025b98a7c92f3b5f3495fce1e4b352bae52a3fc62bb8781b79e92d8",
    },
}


class CatchAllReadError(RuntimeError):
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
        raise CatchAllReadError(f"cannot import {relpath}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module, sha256_file(path)


def offline_floor_pp(rows: int) -> float:
    """``stage3_effect_floor_check``'s ``offline-sealed-pool`` floor at ``rows``."""

    return OFFLINE_FLOOR_PP * math.sqrt(OFFLINE_FLOOR_N / rows)


def load_agreement(path: Path, expected_sha256: str) -> dict[str, dict[str, float]]:
    if sha256_file(path) != expected_sha256:
        raise CatchAllReadError(f"{path} does not match its registered sha256")
    table: dict[str, dict[str, float]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                table[str(row["id"])] = {str(k): float(v) for k, v in row["scores"].items()}
    return table


def marks_catch_all(scores: Mapping[str, float]) -> bool:
    """The registered mark: ``general_quirky`` holds the STRICT maximum share."""

    share = scores.get(CATCH_ALL_KEY)
    if share is None or share <= 0.0:
        return False
    return all(value < share for key, value in scores.items() if key != CATCH_ALL_KEY)


def edit(text: str) -> tuple[str, str]:
    """``(new_text, status)`` for one rendered sample: ``malformed``,
    ``already-catch-all`` or ``edited``. Entities are carried byte-unchanged."""

    payload = json.loads(text)
    scenario, action = payload.get("scenario", ""), payload.get("action", "")
    if not scenario and not action:
        return text, "malformed"
    if (scenario, action) == (CATCH_ALL_SCENARIO, CATCH_ALL_ACTION):
        return text, "already-catch-all"
    payload["scenario"], payload["action"] = CATCH_ALL_SCENARIO, CATCH_ALL_ACTION
    return json.dumps(payload, ensure_ascii=False, sort_keys=True), "edited"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pool", choices=sorted(POOLS), required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--lock", default="/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json")
    parser.add_argument("--out-dir", default=None,
                        help=f"default: <data-root>/analysis/{READ_ID}/<pool>")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    started = time.time()
    pool = POOLS[args.pool]
    root = Path(args.data_root)
    agg, agg_sha = import_file(AGGREGATION_READ, "_saea_sample_aggregation_offline_read")
    score_root = root / pool["score_root"]
    if not (score_root / "render-manifest.json").is_file() and args.dry_run:
        agreement = load_agreement(root / pool["agreement_relpath"], pool["agreement_sha256"])
        print(json.dumps({
            "dry_run": True, "pool": args.pool, "pool_read_present": False,
            "agreement_rows": len(agreement),
            "agreement_rows_marked": sum(1 for scores in agreement.values() if marks_catch_all(scores)),
            "offline_floor_pp": offline_floor_pp(len(agreement)),
        }, indent=1, sort_keys=True))
        return 0
    if not (score_root / "render-manifest.json").is_file():
        raise CatchAllReadError(
            f"the pool's stage 1-3 read is absent at {score_root}; run its registered read first "
            "(scripts/flights/batch/roll2_read.sh for fold-a)")
    sealed = agg.load_rollout_score_root(score_root, pool["scorer_id"], SAMPLES)
    ids = sorted(sealed["rendered"][0])
    for index in range(SAMPLES):
        if sorted(sealed["rendered"][index]) != ids or sorted(sealed["scored"][index]) != ids:
            raise CatchAllReadError(f"sample {index}: copy and score rows differ from sample 0")
    agreement = load_agreement(root / pool["agreement_relpath"], pool["agreement_sha256"])
    missing = sorted(set(ids) - set(agreement))
    if missing:
        raise CatchAllReadError(f"{len(missing)} pool row(s) carry no agreement vote; first {missing[0]}")

    marked = {sid: marks_catch_all(agreement[sid]) for sid in ids}
    edited: dict[int, dict[str, str]] = {}
    status_counts: dict[str, int] = {}
    for index in range(SAMPLES):
        copy: dict[str, str] = {}
        for sid in ids:
            text = sealed["rendered"][index][sid]
            if marked[sid]:
                text, status = edit(text)
            else:
                status = "unmarked"
            status_counts[status] = status_counts.get(status, 0) + 1
            copy[sid] = text
        edited[index] = copy
    rows_marked = sum(marked.values())
    floor = offline_floor_pp(len(ids))
    counts = {
        "pool": args.pool, "rows": len(ids), "samples": SAMPLES, "rows_marked": rows_marked,
        "sample_status_counts": dict(sorted(status_counts.items())),
        "offline_floor_pp": floor,
    }
    if args.dry_run:
        print(json.dumps({"dry_run": True, **counts}, indent=1, sort_keys=True))
        return 0

    import numpy as np  # noqa: PLC0415

    from speech_aware_evidence_acquisition.data.lock import load_lock  # noqa: PLC0415

    lock = load_lock(Path(args.lock))
    out_dir = Path(args.out_dir) if args.out_dir else root / "analysis" / READ_ID / args.pool
    out_dir.mkdir(parents=True, exist_ok=True)
    arms: dict[str, dict[str, Any]] = {}
    copies: dict[str, dict[str, Any]] = {}
    for index in range(SAMPLES):
        base_rows = sealed["scored"][index]
        arms[f"R0-sample-{index}"] = {
            "matrix": agg.counts_matrix(base_rows, ids),
            "row_f1": np.array([float(base_rows[s]["slu_f1_f1"]) for s in ids]),
        }
        path = out_dir / f"rule-sample-{index}-outputs.jsonl"
        digest = agg.write_jsonl(path, [{"sample_id": s, "text": edited[index][s]} for s in ids])
        result, seconds = agg.score_copy(
            pool["scorer_id"], path, out_dir / f"rule-sample-{index}-{pool['scorer_id']}-scores.json", lock, root)
        rows = {str(r["sample_id"]): r for r in result["per_sample"]}
        arms[f"RULE-sample-{index}"] = {
            "matrix": agg.counts_matrix(rows, ids),
            "row_f1": np.array([float(rows[s]["slu_f1_f1"]) for s in ids]),
        }
        copies[f"sample_{index}"] = {"outputs_sha256": digest, "scoring_seconds": seconds}
    for prefix in ("R0", "RULE"):
        arms[f"{prefix}-mean-single"] = {
            "matrix": np.mean(np.stack([arms[f"{prefix}-sample-{i}"]["matrix"] for i in range(SAMPLES)]), axis=0),
            "row_f1": np.mean(np.stack([arms[f"{prefix}-sample-{i}"]["row_f1"] for i in range(SAMPLES)]), axis=0),
        }
    ci = agg.bootstrap(arms, ids, "R0-mean-single")
    base = agg.summarise(arms["R0-mean-single"]["matrix"], arms["R0-mean-single"]["row_f1"])
    rule = agg.summarise(arms["RULE-mean-single"]["matrix"], arms["RULE-mean-single"]["row_f1"])
    delta_intent = rule["intent_exact_pp"] - base["intent_exact_pp"]
    delta_slu = rule["slu_f1_pp"] - base["slu_f1_pp"]
    intent_ci = ci["RULE-mean-single"]["intent_exact_pp"]
    slu_ci = ci["RULE-mean-single"]["slu_f1_pp"]
    clears = bool(intent_ci["lo"] > 0.0 and delta_intent >= floor and slu_ci["lo"] >= -floor)
    per_sample = {
        f"sample_{i}": {
            "delta_intent_pp": agg.summarise(arms[f"RULE-sample-{i}"]["matrix"], arms[f"RULE-sample-{i}"]["row_f1"])["intent_exact_pp"]
            - agg.summarise(arms[f"R0-sample-{i}"]["matrix"], arms[f"R0-sample-{i}"]["row_f1"])["intent_exact_pp"],
        }
        for i in range(SAMPLES)
    }
    report = {
        "schema": SCHEMA, "read_id": READ_ID, "pool": args.pool, "pool_role": pool["role"],
        "authority": "owner decision 171 (2026-09-27)",
        "inputs": {**pool, "aggregation_read_sha256": agg_sha,
                   "render_manifest_sha256": sha256_file(score_root / "render-manifest.json")},
        **counts,
        "resampling": {"draws": agg.BOOTSTRAP_DRAWS, "seed": agg.BOOTSTRAP_SEED, "cluster": "row",
                       "implementation": "slurp_sample_aggregation_offline_read.bootstrap, imported unchanged"},
        "baseline_R0_mean_single": base, "rule_mean_single": rule,
        "delta_intent_pp": delta_intent, "delta_intent_ci95": intent_ci,
        "delta_slu_f1_pp": delta_slu, "delta_slu_f1_ci95": slu_ci,
        "per_sample_delta_intent_pp": per_sample,
        "decision_rule": ("CLEARS iff intent CI95 lower bound > 0 AND intent delta >= offline floor "
                          "0.67*sqrt(625/n) AND SLU-F1 CI95 lower bound >= -floor"),
        "clears": clears,
        "copies": copies,
        "claim_boundary": ("OFFLINE, one sealed pool, development numbers only (decisions 28 and 86); a clear "
                           "licenses registering a flight with an in-chain A/A, never a gain claim."),
        "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "network": 0, "gpu": 0,
                     "scorer": SAMPLES},
        "elapsed_seconds": time.time() - started,
    }
    digest = agg.write_json(out_dir / "report.json", report)
    print(json.dumps({"clears": clears, "delta_intent_pp": delta_intent, "delta_intent_ci95": intent_ci,
                      "delta_slu_f1_pp": delta_slu, "offline_floor_pp": floor, "report_sha256": digest,
                      **counts}, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
