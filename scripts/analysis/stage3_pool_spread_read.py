#!/usr/bin/env python3
"""CLI: the within-flight SPREAD and the oracle CEILING of a sealed k-sample
Solver pool (recipe stage ``4_spread`` of a ``saea-stage3-rollout-analysis-
recipe-v1`` recipe; first use: cell ROLL-3 on DEV-2000-ADDED, registered as
``SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-READ-V1``).

Derived from the cell ROLL-AA within-flight null (the stage-4 block of
``scripts/flights/batch/rollaa_read.sh``, two samples, row-paired bootstrap)
with the minimal generalisation a five-sample pool on an evaluation roster
needs: every sample-index PAIR is read (k choose 2 paired deltas per row),
the bootstrap resamples WHOLE UTTERANCES (``analysis.paired.resampled_
statistic`` with ``cluster_of``, exactly the resampling the DEV-2000-ADDED
cross-flight own null used; 87 utterances carry two recordings), the roster
that withholds its stratum per item is tabulated by recording CHANNEL
(headset / far-field), and the oracle best-of-k ceiling is stated as an
UPPER BOUND beside the sealed delivered score.

Model-free, scorer-free: zero model / tokenizer / encoder / scorer / server /
network contacts. Everything it reads is already on disk: the pinned
``per_row.json`` and the five ``sample_<i>-<scorer>-scores.json`` files that
stages 1-3 (``stage3_rollout_score.py``) wrote under the analysis root, the
sealed ``<run>.outputs.jsonl`` (for the per-sample raw-response digests, the
parsed intent / entity keys, the custody fields and the delivered bytes) and
the sealed ``<run>.scores.json`` (the delivered answer's own official score,
under the scorer id the flight sealed it with -- read, never rescored).

The official SLU-F1 of an oracle selection is RECOMPUTED here from the
per-row official count fields (word- and char-distance TP/FP/FN summed, then
P/R/F1 -- ``reproduction.slurp_scoring.SluScore.slu_f1``) and that
recomputation is SELF-CHECKED first: applied to each of the five copies it
must reproduce that copy's own ``aggregate.official.slu_f1`` to 1e-9, or the
read refuses. Intent accuracy is the mean of ``scenario_action_exact``.

No utterance text, gold label, transcript or model output is printed or
persisted: ``spread.json``, ``ceiling.json`` and ``per_row_spread.json``
carry ids, channel labels, sample indices, scores, flags, counts and hashes
only. Parsed answers are opened in memory to derive the intent-flip and
entity-set-flip flags and discarded.

Run in WSL2 (from a COPY beside the output, as ``det_read.sh`` pins its
drivers)::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src python \\
      stage3_pool_spread_read.py --run SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-V1 \\
      --attempt attempt-slurp-native-stage3-roll-3-dev2000-added-v1-generation \\
      --roster docs/receipts/rosters/slurp-dev-2000-added-v1.json \\
      --scorer-id slurp-slu-official-projected-v3 --repo-root <repo> \\
      --analysis-root "$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-READ-V1"
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

SCHEMA_SPREAD = "saea-stage3-pool-spread-v1"
SCHEMA_CEILING = "saea-stage3-pool-ceiling-v1"
SCHEMA_PER_ROW = "saea-stage3-pool-per-row-spread-v1"
DEFAULT_SEED = 20260915
DEFAULT_DRAWS = 10_000
COUNT_FIELDS = (
    "slu_f1_word_tp", "slu_f1_word_fp", "slu_f1_word_fn",
    "slu_f1_char_tp", "slu_f1_char_fp", "slu_f1_char_fn",
)
SELF_CHECK_TOLERANCE = 1e-9


class PoolSpreadError(RuntimeError):
    """A pinned or sealed input is missing or does not have the shape this CLI needs."""


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Mapping[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )
    return sha256_file(path)


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def prf(tp: float, fp: float, fn: float) -> tuple[float, float, float]:
    """``reproduction.slurp_scoring._prf`` -- the official ``compute_metrics``."""

    precision = 0.0 if tp == 0.0 and fp == 0.0 else tp / (tp + fp)
    recall = 0.0 if tp == 0.0 and fn == 0.0 else tp / (tp + fn)
    f1 = 0.0 if precision == 0.0 and recall == 0.0 else 2 * precision * recall / (precision + recall)
    return precision, recall, f1


def micro_slu_f1(counts: Mapping[str, Sequence[float]], ids: Sequence[str]) -> float:
    """The official combined SLU-F1 over ``ids`` (ids may REPEAT under a
    bootstrap draw): word- and char-distance TP/FP/FN summed, then P/R/F1."""

    tp = fp = fn = 0.0
    for sample_id in ids:
        c = counts[sample_id]
        tp += c[0] + c[3]
        fp += c[1] + c[4]
        fn += c[2] + c[5]
    return prf(tp, fp, fn)[2]


def render_answer_local(payload: Mapping[str, Any] | None) -> str:
    """The canonical delivered rendering (``stage3_rollout_score.render_answer``)."""

    if payload is None:
        return json.dumps({"scenario": "", "action": "", "entities": []},
                          ensure_ascii=False, sort_keys=True)
    body = {
        "scenario": payload.get("scenario", ""),
        "action": payload.get("action", ""),
        "entities": [{"type": e["type"], "filler": e["filler"]} for e in payload.get("entities", [])],
    }
    return json.dumps(body, ensure_ascii=False, sort_keys=True)


def entity_key(answer: Mapping[str, Any] | None):
    """The ROLL-AA entity-set key: sorted (type, filler) pairs under the
    scorer's own case / whitespace normalisation."""

    if not isinstance(answer, Mapping):
        return None
    return tuple(sorted(
        (str(e.get("type", "")).strip().lower(), " ".join(str(e.get("filler", "")).split()).lower())
        for e in (answer.get("entities") or [])
    ))


def intent_key(answer: Mapping[str, Any] | None):
    if not isinstance(answer, Mapping):
        return None
    return (answer.get("scenario"), answer.get("action"))


def bootstrap_block(values: Mapping[str, float], ids: Sequence[str], *, cluster_of, seed: int,
                    draws: int, scale: float = 100.0,
                    statistic: Callable[[Sequence[str]], float] | None = None) -> dict[str, Any]:
    """Mean of a per-row value (or an arbitrary pooled ``statistic``) with its
    CI95 by whole-cluster bootstrap -- ``analysis.paired.resampled_statistic``,
    the same draws the programme's paired roster read makes."""

    from speech_aware_evidence_acquisition.analysis.paired import (  # noqa: PLC0415
        resampled_statistic,
    )

    if statistic is None:
        getter = values.__getitem__

        def statistic(resampled: Sequence[str]) -> float:  # noqa: E306
            return sum(map(getter, resampled)) / len(resampled)

    result = resampled_statistic(
        sample_ids=ids, statistic=statistic, seed=seed, n_replicates=draws,
        ci_level=0.95, cluster_of=cluster_of,
    )
    return {
        "point_estimate_pp": scale * result.point_estimate,
        "sigma_hat_pp": scale * result.sigma_hat,
        "ci95_pp": [scale * result.ci_low, scale * result.ci_high],
        "ci95_half_width_pp": scale * (result.ci_high - result.ci_low) / 2.0,
        "n_replicates": result.n_replicates,
        "seed": result.seed,
        "resampling": "paired whole-cluster bootstrap (analysis.paired.resampled_statistic)",
    }


def share(flags: Sequence[bool | None]) -> dict[str, Any]:
    known = [f for f in flags if f is not None]
    return {
        "share": (sum(1 for f in known if f) / len(known)) if known else None,
        "count": sum(1 for f in known if f), "denominator": len(known),
        "unknown": len(flags) - len(known),
    }


# ---------------------------------------------------------------------------
# inputs
# ---------------------------------------------------------------------------


def load_roster(repo_root: Path, relpath: str, *, cluster_key: str, channel_key: str):
    path = repo_root / relpath
    document = json.loads(path.read_text(encoding="utf-8"))
    cluster_of: dict[str, str] = {}
    channel_of: dict[str, str] = {}
    derived_clusters = 0
    for item in document["items"]:
        sample_id = str(item["sample_id"])
        cluster = item.get(cluster_key)
        if not isinstance(cluster, str) or not cluster:
            # slurp:<split>:<utterance>:<recording> -> the utterance prefix
            cluster = ":".join(sample_id.split(":")[:3])
            derived_clusters += 1
        cluster_of[sample_id] = cluster
        channel = item.get(channel_key)
        channel_of[sample_id] = (
            ("headset" if channel else "far-field") if isinstance(channel, bool) else "unknown"
        )
    return {
        "relpath": relpath, "sha256": sha256_file(path), "rows": len(cluster_of),
        "roster_id": document.get("roster_id"), "roster_role": document.get("roster_role"),
        "split_identity_hash": document.get("split_identity_hash"),
        "stratum_withheld_per_item": document.get("stratum_withheld_per_item"),
        "cluster_key": cluster_key, "clusters": len(set(cluster_of.values())),
        "clusters_derived_from_sample_id": derived_clusters,
        "clusters_with_two_or_more_rows": sum(
            1 for c in set(cluster_of.values()) if sum(1 for v in cluster_of.values() if v == c) >= 2
        ),
        "channel_key": channel_key,
        "channel_counts": {c: sum(1 for v in channel_of.values() if v == c) for c in sorted(set(channel_of.values()))},
    }, cluster_of, channel_of


def load_copies(analysis_root: Path, scorer_id: str, samples: int) -> dict[int, dict[str, Any]]:
    """Each copy's official aggregate and per-row rows, from the pinned score files."""

    copies: dict[int, dict[str, Any]] = {}
    for index in range(samples):
        path = analysis_root / f"sample_{index}-{scorer_id}-scores.json"
        if not path.is_file():
            raise PoolSpreadError(f"stage 2 score file missing: {path}")
        result = json.loads(path.read_text(encoding="utf-8"))[scorer_id]
        official = result["aggregate"]["official"]
        copies[index] = {
            "path": str(path), "sha256": sha256_file(path),
            "official": {
                "slu_f1": float(official["slu_f1"]),
                "intent_accuracy": float(official["intent_accuracy"]),
                "scenario_accuracy": float(official.get("scenario_accuracy", float("nan"))),
                "action_accuracy": float(official.get("action_accuracy", float("nan"))),
                "span_f1": float(official.get("span_f1", official.get("raw", {}).get("entities", {}).get("f_measure", float("nan")))),
            },
            "identity_check_passed": bool(result["aggregate"]["identity_check"]["passed"]),
            "per_sample": {str(r["sample_id"]): r for r in result["per_sample"]},
        }
    return copies


def load_sealed(directory: Path, run_id: str, ids: Sequence[str], samples: int):
    """Digests, custody, parsed keys and delivered bytes per row -- never any text out."""

    wanted = set(ids)
    sealed: dict[str, dict[str, Any]] = {}
    for row in iter_jsonl(directory / f"{run_id}.outputs.jsonl"):
        sample_id = str(row["sample_id"])
        if sample_id not in wanted:
            continue
        group = row.get("solver_group")
        if not isinstance(group, Mapping):
            raise PoolSpreadError(f"row {sample_id} carries no solver_group custody")
        records = group["samples"]
        if len(records) != samples:
            raise PoolSpreadError(f"row {sample_id} carries {len(records)} samples, expected {samples}")
        parsed = [r.get("parsed_answer") if r.get("parse_status") == "ok" else None for r in records]
        sealed[sample_id] = {
            "digests": [r["contacts"][-1]["response_text_sha256"] for r in records],
            "seeds": [r["seed"] for r in records],
            "temperatures": [float(r["temperature"]) for r in records],
            "parse_ok": [r.get("parse_status") == "ok" for r in records],
            "intent_keys": [intent_key(p) for p in parsed],
            "entity_keys": [entity_key(p) for p in parsed],
            "rendered": [render_answer_local(p) for p in parsed],
            "delivered_text": row.get("text"),
            "delivered_sha256": row.get("response_text_sha256"),
            "commit_policy_id": group.get("commit_policy_id"),
            "commit_params": dict(group.get("commit_params") or {}),
            "row": row,
        }
    missing = sorted(wanted - set(sealed))
    if missing:
        raise PoolSpreadError(f"{len(missing)} roster row(s) absent from the sealed outputs; first {missing[0]}")
    return sealed


def load_sealed_delivered(directory: Path, run_id: str, sealed_scorer_id: str | None):
    """The delivered answer's own sealed official score (aggregate + per row),
    under the scorer id the flight sealed it with. Absent -> reported absent."""

    path = directory / f"{run_id}.scores.json"
    if not path.is_file():
        return None, f"no sealed scores file at {path}"
    document = json.loads(path.read_text(encoding="utf-8"))
    if sealed_scorer_id is None or sealed_scorer_id not in document:
        return None, f"sealed scores carry {sorted(document)}; requested {sealed_scorer_id!r}"
    block = document[sealed_scorer_id]
    aggregate = block.get("aggregate", {})
    official = aggregate.get("official", {}) if isinstance(aggregate, Mapping) else {}
    per_sample = {str(r["sample_id"]): r for r in block.get("per_sample", [])}
    return {
        "scorer_id": sealed_scorer_id, "scores_sha256": sha256_file(path),
        "official": {k: official.get(k) for k in ("slu_f1", "intent_accuracy", "scenario_accuracy", "action_accuracy", "span_f1")},
        "per_sample": per_sample,
    }, "sealed"


# ---------------------------------------------------------------------------
# the read
# ---------------------------------------------------------------------------


def commit_replay(sealed: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    from speech_aware_evidence_acquisition.core.base import COMMIT_POLICIES  # noqa: PLC0415
    from speech_aware_evidence_acquisition.rails import commit_policies  # noqa: PLC0415, F401
    from speech_aware_evidence_acquisition.analysis.native_commit_replay import (  # noqa: PLC0415
        replay_row,
    )

    policies: dict[str, Any] = {}
    text_equal = sha_equal = 0
    policy_ids: dict[str, int] = {}
    params: dict[str, int] = {}
    failures: list[dict[str, str]] = []
    for sample_id, entry in sealed.items():
        pid = str(entry["commit_policy_id"])
        policy_ids[pid] = policy_ids.get(pid, 0) + 1
        key = json.dumps(entry["commit_params"], sort_keys=True)
        params[key] = params.get(key, 0) + 1
        if pid not in policies:
            policies[pid] = COMMIT_POLICIES.resolve(pid)
        try:
            out = replay_row(entry["row"], policy=policies[pid], commit_params=entry["commit_params"])
        except Exception as error:  # noqa: BLE001
            failures.append({"sample_id": sample_id, "error": type(error).__name__})
            continue
        text = out["final_response_text"]
        text_equal += 1 if text == entry["delivered_text"] else 0
        sha_equal += 1 if hashlib.sha256(text.encode("utf-8")).hexdigest() == entry["delivered_sha256"] else 0
    return {
        "policy_ids": policy_ids, "commit_params": params,
        "rows_replay_text_equals_sealed_delivered_text": text_equal,
        "rows_replay_sha256_equals_sealed_response_text_sha256": sha_equal,
        "replay_failures": failures,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", required=True)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--roster", required=True, help="roster receipt relpath (repo-root relative)")
    parser.add_argument("--analysis-root", required=True, help="where stages 1-3 wrote per_row.json and the score files")
    parser.add_argument("--out-dir", default=None, help="where to write (default: --analysis-root)")
    parser.add_argument("--scorer-id", required=True, help="the copies' registered scorer id (stage 2)")
    parser.add_argument("--sealed-scorer-id", default="slurp-slu-official",
                        help="the scorer id the FLIGHT sealed the delivered answer under (read, never rescored)")
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--data-root", default=None)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--draws", type=int, default=DEFAULT_DRAWS)
    parser.add_argument("--cluster-key", default="utterance_id")
    parser.add_argument("--channel-key", default="headset")
    parser.add_argument("--recipe-id", default=None)
    parser.add_argument("--read-run-id", default=None, help="the registered model-free read row this output belongs to")
    parser.add_argument("--expected-seeds", default=None, help="comma-separated per-index seeds the registration pins")
    parser.add_argument("--expected-temperature", type=float, default=None)
    parser.add_argument("--context-json", default=None,
                        help="optional JSON file of reported-beside context (never a comparator); copied verbatim")
    args = parser.parse_args(argv)

    from speech_aware_evidence_acquisition.data.lock import data_root as resolve_data_root  # noqa: PLC0415

    started = time.time()
    repo_root = Path(args.repo_root)
    root = Path(args.data_root) if args.data_root else resolve_data_root()
    analysis_root = Path(args.analysis_root)
    out_dir = Path(args.out_dir) if args.out_dir else analysis_root
    out_dir.mkdir(parents=True, exist_ok=True)
    directory = root / "runs" / args.run / args.attempt
    if not directory.is_dir():
        raise PoolSpreadError(f"no sealed attempt directory at {directory}")

    per_row_path = analysis_root / "per_row.json"
    if not per_row_path.is_file():
        raise PoolSpreadError(f"stage 3 output missing: {per_row_path}")
    per_row_doc = json.loads(per_row_path.read_text(encoding="utf-8"))
    samples = int(per_row_doc["samples"])
    rows = {str(r["sample_id"]): r for r in per_row_doc["rows"]}
    ids = sorted(rows)
    n = len(ids)

    roster_facts, cluster_of_map, channel_of_map = load_roster(
        repo_root, args.roster, cluster_key=args.cluster_key, channel_key=args.channel_key)
    if set(cluster_of_map) != set(ids):
        raise PoolSpreadError("per_row.json ids and the roster's ids differ")
    cluster_of = cluster_of_map.__getitem__
    copies = load_copies(analysis_root, args.scorer_id, samples)
    sealed = load_sealed(directory, args.run, ids, samples)
    delivered, delivered_status = load_sealed_delivered(directory, args.run, args.sealed_scorer_id)

    # ---- per-sample per-row values -------------------------------------------------------------
    slu = {i: {sid: float(rows[sid]["samples"][i]["slu_f1_f1"]) for sid in ids} for i in range(samples)}
    intent = {i: {sid: 1.0 if rows[sid]["samples"][i]["scenario_action_exact"] else 0.0 for sid in ids}
              for i in range(samples)}
    counts = {i: {sid: tuple(float(copies[i]["per_sample"][sid][f]) for f in COUNT_FIELDS) for sid in ids}
              for i in range(samples)}

    # ---- self-check: the micro recomputation reproduces each copy's official aggregate --------
    self_check = {}
    for i in range(samples):
        recomputed = micro_slu_f1(counts[i], ids)
        official = copies[i]["official"]["slu_f1"]
        self_check[f"sample_{i}"] = {"recomputed": recomputed, "official": official,
                                     "abs_diff": abs(recomputed - official)}
        if abs(recomputed - official) > SELF_CHECK_TOLERANCE:
            raise PoolSpreadError(
                f"micro SLU-F1 recomputation drifts from the official aggregate on sample {i}: "
                f"{recomputed} vs {official}")
        recomputed_intent = sum(intent[i].values()) / n
        if abs(recomputed_intent - copies[i]["official"]["intent_accuracy"]) > 1e-6:
            raise PoolSpreadError(f"intent recomputation drifts on sample {i}")

    # ---- custody ---------------------------------------------------------------------------------
    expected_seeds = [int(s) for s in args.expected_seeds.split(",")] if args.expected_seeds else None
    custody = {
        "rows": n, "samples_per_row": samples,
        "rows_with_k_samples": sum(1 for sid in ids if len(sealed[sid]["digests"]) == samples),
        "distinct_seed_sets": sorted({tuple(sealed[sid]["seeds"]) for sid in ids}),
        "distinct_temperature_sets": sorted({tuple(sealed[sid]["temperatures"]) for sid in ids}),
        "rows_with_expected_seeds": (sum(1 for sid in ids if sealed[sid]["seeds"] == expected_seeds)
                                     if expected_seeds else None),
        "rows_with_expected_temperature": (
            sum(1 for sid in ids if all(t == args.expected_temperature for t in sealed[sid]["temperatures"]))
            if args.expected_temperature is not None else None),
        "malformed_samples": sum(sum(1 for ok in sealed[sid]["parse_ok"] if not ok) for sid in ids),
        "rows_with_a_malformed_sample": sum(1 for sid in ids if not all(sealed[sid]["parse_ok"])),
        "commit_replay": commit_replay(sealed),
    }

    # ---- pairwise spread -------------------------------------------------------------------------
    pairs = list(itertools.combinations(range(samples), 2))
    pair_blocks: dict[str, Any] = {}
    per_row_pair_flags: dict[str, dict[str, dict[str, Any]]] = {sid: {} for sid in ids}
    pair_half_widths_slu: list[float] = []
    pair_half_widths_intent: list[float] = []
    pair_half_widths_micro: list[float] = []
    for i, j in pairs:
        name = f"{i}-{j}"
        d_slu = {sid: slu[j][sid] - slu[i][sid] for sid in ids}
        d_int = {sid: intent[j][sid] - intent[i][sid] for sid in ids}
        byte_identical = [sealed[sid]["digests"][i] == sealed[sid]["digests"][j] for sid in ids]
        intent_flip = [None if sealed[sid]["intent_keys"][i] is None or sealed[sid]["intent_keys"][j] is None
                       else sealed[sid]["intent_keys"][i] != sealed[sid]["intent_keys"][j] for sid in ids]
        entity_flip = [None if sealed[sid]["entity_keys"][i] is None or sealed[sid]["entity_keys"][j] is None
                       else sealed[sid]["entity_keys"][i] != sealed[sid]["entity_keys"][j] for sid in ids]
        for k, sid in enumerate(ids):
            per_row_pair_flags[sid][name] = {
                "delta_slu_pp": 100.0 * d_slu[sid], "delta_intent": int(d_int[sid]),
                "byte_identical": byte_identical[k], "intent_flip": intent_flip[k], "entity_set_flip": entity_flip[k],
            }
        ci = counts[i]
        cj = counts[j]

        def micro_delta(resampled: Sequence[str], ci=ci, cj=cj) -> float:
            return micro_slu_f1(cj, resampled) - micro_slu_f1(ci, resampled)

        block = {
            "sample_indices": [i, j],
            "delta_slu_mean_per_row": bootstrap_block(d_slu, ids, cluster_of=cluster_of, seed=args.seed, draws=args.draws),
            "delta_intent_mean_per_row": bootstrap_block(d_int, ids, cluster_of=cluster_of, seed=args.seed, draws=args.draws),
            "delta_slu_micro_official": bootstrap_block({}, ids, cluster_of=cluster_of, seed=args.seed,
                                                        draws=args.draws, statistic=micro_delta),
            "sd_per_row_delta_slu_pp": 100.0 * statistics.pstdev(d_slu.values()),
            "byte_identical": share(byte_identical), "intent_flip": share(intent_flip),
            "entity_set_flip": share(entity_flip),
        }
        pair_half_widths_slu.append(block["delta_slu_mean_per_row"]["ci95_half_width_pp"])
        pair_half_widths_intent.append(block["delta_intent_mean_per_row"]["ci95_half_width_pp"])
        pair_half_widths_micro.append(block["delta_slu_micro_official"]["ci95_half_width_pp"])
        pair_blocks[name] = block

    # ---- pooled over all pairs: one value per row (the mean over its k choose 2 paired deltas) --
    pooled_abs_slu = {sid: statistics.mean(abs(v["delta_slu_pp"]) for v in per_row_pair_flags[sid].values()) / 100.0 for sid in ids}
    row_sd_slu = {sid: statistics.pstdev(slu[i][sid] for i in range(samples)) for sid in ids}
    all_byte_identical = [len(set(sealed[sid]["digests"])) == 1 for sid in ids]
    all_same_intent = [None if any(k is None for k in sealed[sid]["intent_keys"]) else len(set(sealed[sid]["intent_keys"])) == 1 for sid in ids]
    all_same_entities = [None if any(k is None for k in sealed[sid]["entity_keys"]) else len(set(sealed[sid]["entity_keys"])) == 1 for sid in ids]
    all_same_slu = [len({round(slu[i][sid], 12) for i in range(samples)}) == 1 for sid in ids]

    def summary(values: Sequence[float]) -> dict[str, float]:
        return {"mean": statistics.mean(values), "min": min(values), "max": max(values),
                "median": statistics.median(values)}

    # ---- oracle ceiling ------------------------------------------------------------------------
    def best_index(sid: str) -> int:
        return max(range(samples), key=lambda i: (slu[i][sid], intent[i][sid], -i))

    def worst_index(sid: str) -> int:
        return min(range(samples), key=lambda i: (slu[i][sid], intent[i][sid], i))

    best_of = {sid: best_index(sid) for sid in ids}
    worst_of = {sid: worst_index(sid) for sid in ids}
    best_counts = {sid: counts[best_of[sid]][sid] for sid in ids}
    worst_counts = {sid: counts[worst_of[sid]][sid] for sid in ids}
    any_intent = {sid: max(intent[i][sid] for i in range(samples)) for sid in ids}
    all_intent = {sid: min(intent[i][sid] for i in range(samples)) for sid in ids}
    mean_of_samples_slu = statistics.mean(copies[i]["official"]["slu_f1"] for i in range(samples))
    mean_of_samples_intent = statistics.mean(copies[i]["official"]["intent_accuracy"] for i in range(samples))

    # delivered vs sample rendering identity (the delivered bytes are a plurality composite;
    # where they equal one sample's canonical rendering, that sample's projected score IS the
    # delivered answer's projected score)
    delivered_equals_sample = {}
    for sid in ids:
        matches = [i for i in range(samples) if sealed[sid]["rendered"][i] == sealed[sid]["delivered_text"]]
        delivered_equals_sample[sid] = matches
    rows_delivered_equal_some_sample = sum(1 for sid in ids if delivered_equals_sample[sid])
    attributed = {sid: delivered_equals_sample[sid][0] for sid in ids if delivered_equals_sample[sid]}
    attributed_ids = sorted(attributed)
    attributed_counts = {sid: counts[attributed[sid]][sid] for sid in attributed_ids}

    ceiling = {
        "schema": SCHEMA_CEILING, "recipe_id": args.recipe_id, "read_run_id": args.read_run_id,
        "run_id": args.run, "attempt_id": args.attempt, "rows": n, "samples": samples,
        "scorer_id_copies": args.scorer_id,
        "claim": ("UPPER BOUND: the oracle best-of-k picks, per row, the sample with the highest official "
                  "SLU-F1 (ties by intent, then the lowest index) AFTER seeing the gold; no selection policy "
                  "can exceed it and none is claimed to reach it. Never an achieved result."),
        "self_check_micro_recomputation": self_check,
        "per_sample_official_pp": {
            f"sample_{i}": {"slu_f1": 100 * copies[i]["official"]["slu_f1"],
                            "intent_accuracy": 100 * copies[i]["official"]["intent_accuracy"],
                            "scenario_accuracy": 100 * copies[i]["official"]["scenario_accuracy"],
                            "action_accuracy": 100 * copies[i]["official"]["action_accuracy"],
                            "span_f1": 100 * copies[i]["official"]["span_f1"],
                            "identity_check_passed": copies[i]["identity_check_passed"],
                            "score_file_sha256": copies[i]["sha256"]}
            for i in range(samples)
        },
        "mean_of_samples_pp": {"slu_f1": 100 * mean_of_samples_slu, "intent_accuracy": 100 * mean_of_samples_intent},
        "oracle_best_of_k_pp": {
            "slu_f1_micro_official": 100 * micro_slu_f1(best_counts, ids),
            "slu_f1_mean_per_row": 100 * statistics.mean(slu[best_of[sid]][sid] for sid in ids),
            "intent_any_sample_correct": 100 * statistics.mean(any_intent.values()),
            "best_index_histogram": {str(i): sum(1 for sid in ids if best_of[sid] == i) for i in range(samples)},
        },
        "oracle_worst_of_k_pp": {
            "slu_f1_micro_official": 100 * micro_slu_f1(worst_counts, ids),
            "intent_all_samples_correct": 100 * statistics.mean(all_intent.values()),
        },
        "oracle_minus_mean_sample_pp": {
            "slu_f1_micro_official": 100 * (micro_slu_f1(best_counts, ids) - mean_of_samples_slu),
            "intent": 100 * (statistics.mean(any_intent.values()) - mean_of_samples_intent),
        },
        "oracle_vs_each_sample_micro_slu_ci95": {
            f"sample_{i}": bootstrap_block(
                {}, ids, cluster_of=cluster_of, seed=args.seed, draws=args.draws,
                statistic=(lambda resampled, ci=counts[i]: micro_slu_f1(best_counts, resampled) - micro_slu_f1(ci, resampled)))
            for i in range(samples)
        },
        "delivered_sealed": {
            "status": delivered_status,
            "scorer_id": (delivered or {}).get("scorer_id"),
            "note": ("The delivered (plurality-commit) answer's official score as the FLIGHT sealed it at "
                     "finalize, under the flight's own scorer id -- read, never rescored. A grouped Solver "
                     "carries no deliver_normaliser, so this sealed number is UNPROJECTED while the five "
                     "copies above are scored under the projected scorer; the two are reported side by side, "
                     "never subtracted. A like-for-like projected delivered number would need a sixth scorer "
                     "contact, which this read does not register."),
            "official_pp": ({k: (100 * v if isinstance(v, (int, float)) else None)
                             for k, v in delivered["official"].items()} if delivered else None),
            "scores_sha256": (delivered or {}).get("scores_sha256"),
        },
        "delivered_equals_one_sample_rendering": {
            "rows": rows_delivered_equal_some_sample, "share": rows_delivered_equal_some_sample / n,
            "rows_composite": n - rows_delivered_equal_some_sample,
            "note": ("On the rows whose delivered bytes equal one sample's canonical rendering, the delivered "
                     "answer's PROJECTED per-row score is that sample's; the micro SLU-F1 over those rows only "
                     "is reported for the record (a SUBSET, never the pool's delivered score)."),
            "subset_micro_slu_f1_pp_attributed_sample": (100 * micro_slu_f1(attributed_counts, attributed_ids)) if attributed_ids else None,
            "subset_micro_slu_f1_pp_oracle_same_rows": (100 * micro_slu_f1({sid: best_counts[sid] for sid in attributed_ids}, attributed_ids)) if attributed_ids else None,
            "subset_intent_pp_attributed_sample": (100 * statistics.mean(intent[attributed[sid]][sid] for sid in attributed_ids)) if attributed_ids else None,
        },
        "contacts": {"asr": 0, "encoder": 0, "model": 0, "network": 0, "scorer": 0, "server": 0, "tokenizer": 0},
    }

    # ---- per channel -----------------------------------------------------------------------------
    channels = sorted(set(channel_of_map.values()))
    per_channel = {}
    for channel in channels:
        cids = [sid for sid in ids if channel_of_map[sid] == channel]
        if not cids:
            continue
        per_channel[channel] = {
            "rows": len(cids),
            "clusters": len({cluster_of_map[sid] for sid in cids}),
            "per_sample_micro_slu_f1_pp": {f"sample_{i}": 100 * micro_slu_f1(counts[i], cids) for i in range(samples)},
            "per_sample_intent_pp": {f"sample_{i}": 100 * statistics.mean(intent[i][sid] for sid in cids) for i in range(samples)},
            "oracle_best_of_k_micro_slu_f1_pp": 100 * micro_slu_f1(best_counts, cids),
            "oracle_intent_any_pp": 100 * statistics.mean(any_intent[sid] for sid in cids),
            "mean_pairwise_delta_slu_pp": statistics.mean(
                statistics.mean(v["delta_slu_pp"] for v in per_row_pair_flags[sid].values()) for sid in cids),
            "mean_pairwise_abs_delta_slu_pp": 100 * statistics.mean(pooled_abs_slu[sid] for sid in cids),
            "mean_pairwise_delta_intent_pp": 100 * statistics.mean(
                statistics.mean(v["delta_intent"] for v in per_row_pair_flags[sid].values()) for sid in cids),
            "all_k_byte_identical_share": statistics.mean(1.0 if all_byte_identical[ids.index(sid)] else 0.0 for sid in cids),
            "mean_pairwise_byte_identical_share": statistics.mean(
                statistics.mean(1.0 if v["byte_identical"] else 0.0 for v in per_row_pair_flags[sid].values()) for sid in cids),
            "mean_pairwise_intent_flip_share": statistics.mean(
                statistics.mean(1.0 if v["intent_flip"] else 0.0 for v in per_row_pair_flags[sid].values() if v["intent_flip"] is not None)
                if any(v["intent_flip"] is not None for v in per_row_pair_flags[sid].values()) else 0.0 for sid in cids),
            "mean_pairwise_entity_set_flip_share": statistics.mean(
                statistics.mean(1.0 if v["entity_set_flip"] else 0.0 for v in per_row_pair_flags[sid].values() if v["entity_set_flip"] is not None)
                if any(v["entity_set_flip"] is not None for v in per_row_pair_flags[sid].values()) else 0.0 for sid in cids),
        }

    context = None
    if args.context_json:
        context = json.loads(Path(args.context_json).read_text(encoding="utf-8"))

    spread = {
        "schema": SCHEMA_SPREAD, "recipe_id": args.recipe_id, "read_run_id": args.read_run_id,
        "run_id": args.run, "attempt_id": args.attempt, "rows": n, "samples": samples,
        "scorer_id_copies": args.scorer_id, "roster": roster_facts,
        "resampling": {"draws": args.draws, "seed": args.seed, "unit": f"whole cluster by {args.cluster_key} (paired)",
                       "ci_level": 0.95, "implementation": "analysis.paired.resampled_statistic"},
        "custody": custody,
        "pairs": pair_blocks,
        "implied_half_widths_pp": {
            "note": ("The within-pool paired instrument at this n: the CI95 half-width of the mean per-row "
                     "paired SLU-F1 / intent delta between two sample indices (10 pairs), and of the pooled "
                     "micro official SLU-F1 difference between two copies. Reported beside the Fold A pool's "
                     "offline floor and the cross-flight own null as CONTEXT, never as a comparator or a bar."),
            "per_pair_mean_per_row_slu": summary(pair_half_widths_slu),
            "per_pair_mean_per_row_intent": summary(pair_half_widths_intent),
            "per_pair_micro_official_slu": summary(pair_half_widths_micro),
        },
        "per_row_dispersion": {
            "mean_sd_slu_across_samples_pp": 100 * statistics.mean(row_sd_slu.values()),
            "mean_pairwise_abs_delta_slu_pp": 100 * statistics.mean(pooled_abs_slu.values()),
            "rows_all_k_same_slu": sum(all_same_slu), "rows_all_k_same_slu_share": sum(all_same_slu) / n,
        },
        "flip_shares_all_k": {
            "all_k_byte_identical": share(all_byte_identical),
            "all_k_same_intent": share(all_same_intent),
            "all_k_same_entity_set": share(all_same_entities),
        },
        "flip_shares_pairwise_mean": {
            "byte_identical": statistics.mean(b["byte_identical"]["share"] for b in pair_blocks.values()),
            "intent_flip": statistics.mean(b["intent_flip"]["share"] for b in pair_blocks.values()),
            "entity_set_flip": statistics.mean(b["entity_set_flip"]["share"] for b in pair_blocks.values()),
        },
        "per_channel": per_channel,
        "reported_beside": context,
        "claim_boundary": (
            "DESCRIPTIVE. The spread is a measurement of the sealed pool itself at this n, on this roster, "
            "at these samples and this serving geometry. No transfer, superiority, generalisation, "
            "component-causal, admission or confirmatory claim; no verdict and no disposition."),
        "contacts": {"asr": 0, "encoder": 0, "model": 0, "network": 0, "scorer": 0, "server": 0, "tokenizer": 0},
        "stage3_algorithm": per_row_doc.get("stage3_algorithm"),
        "elapsed_seconds": None,
    }

    per_row_records = []
    for sid in ids:
        per_row_records.append({
            "sample_id": sid, "cluster": cluster_of_map[sid], "channel": channel_of_map[sid],
            "slu_f1_f1": [slu[i][sid] for i in range(samples)],
            "scenario_action_exact": [bool(intent[i][sid]) for i in range(samples)],
            "raw_response_sha256": sealed[sid]["digests"],
            "parse_ok": sealed[sid]["parse_ok"],
            "best_index": best_of[sid], "worst_index": worst_of[sid],
            "delivered_sha256": sealed[sid]["delivered_sha256"],
            "delivered_equals_sample_indices": delivered_equals_sample[sid],
            "delivered_sealed_slu_f1_f1": (float(delivered["per_sample"][sid]["slu_f1_f1"])
                                           if delivered and sid in delivered["per_sample"] and "slu_f1_f1" in delivered["per_sample"][sid] else None),
            "delivered_sealed_scenario_action_exact": (bool(float(delivered["per_sample"][sid]["scenario_action_exact"]) >= 1.0)
                                                       if delivered and sid in delivered["per_sample"] and "scenario_action_exact" in delivered["per_sample"][sid] else None),
            "pairs": per_row_pair_flags[sid],
        })

    spread["elapsed_seconds"] = time.time() - started
    hashes = {
        "ceiling.json": write_json(out_dir / "ceiling.json", ceiling),
        "per_row_spread.json": write_json(out_dir / "per_row_spread.json",
                                          {"schema": SCHEMA_PER_ROW, "run_id": args.run, "rows": per_row_records}),
    }
    spread["output_sha256"] = hashes
    hashes["spread.json"] = write_json(out_dir / "spread.json", spread)
    print(json.dumps({
        "rows": n, "samples": samples,
        "per_sample_official_pp": ceiling["per_sample_official_pp"],
        "oracle_best_of_k_pp": ceiling["oracle_best_of_k_pp"],
        "delivered_sealed": ceiling["delivered_sealed"],
        "implied_half_widths_pp": spread["implied_half_widths_pp"],
        "flip_shares_all_k": spread["flip_shares_all_k"],
        "flip_shares_pairwise_mean": spread["flip_shares_pairwise_mean"],
        "custody": {k: v for k, v in custody.items() if k != "commit_replay"},
        "commit_replay": custody["commit_replay"],
        "per_channel_rows": {c: v["rows"] for c, v in per_channel.items()},
        "output_sha256": hashes,
        "elapsed_seconds": spread["elapsed_seconds"],
    }, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
