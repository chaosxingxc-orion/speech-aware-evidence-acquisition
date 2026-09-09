#!/usr/bin/env python3
"""The single registered read of SLURP's own greedy replicate null.

Scoring-side only. **Zero model, GPU, tool, embedding and network contacts.**
Preregistration: ``docs/readiness/2026-09-09-slurp-own-null-replicate-v1-preregistration.md``
sections 2, 3 and 4.

``SAEA-SLURP-DEV1000-NULL-REPLICATE-V1`` and its sealed comparator
``SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1`` are each scored ONCE over their
complete 1,000-row manifest through ``core.scoring_batch`` with
``include_per_sample=True``, one job per manifest, never sharded, under the
paper-facing ``slurp-slu-official-projected-v2`` and the secondary
``slurp-slu-f1-normalized-v1``. Neither sealed manifest declares those scorers
(``scorers`` is a baseline-fragment key and therefore enters ``config_hash``,
which this cell holds fixed), so ONE derived manifest is written beside each
sealed one differing from it ONLY in the ``scorers`` list.

There is no factor and therefore no verdict. What this read produces is the
null table: for every metric, the delta, both interval families, and the CI90
HALF-WIDTH that becomes the SLURP non-inferiority margin from this cell's
closure. Deltas are signed **replicate minus comparator**; under a true null
both signs are noise.

Two estimands per entity-side metric, deliberately:

* the **micro** (pooled) figure -- the paper-facing number, ``sum(TP) /
  (sum(TP) + ...)`` over the resampled rows, bootstrapped through
  ``analysis.paired.resampled_statistic``. 35.80 is a micro figure and a margin
  for it must be measured on the same estimand;
* the **per-row mean** of the official per-row F1, through
  ``analysis.paired.paired_contrast``, which is what the silence-tail cell
  reported and what carries saves / harms / ties.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from speech_aware_evidence_acquisition.analysis.paired import (
    paired_contrast,
    resampled_statistic,
)
from speech_aware_evidence_acquisition.core.scoring_batch import ScoreJob, run_score_batch
from speech_aware_evidence_acquisition.data.lock import (
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.slurp import (
    _governed_roots,
    _slurp_speaker_index,
    load_slurp_split,
)
from speech_aware_evidence_acquisition.data.variant_ids import published_sample_key
from speech_aware_evidence_acquisition.reproduction.slurp_official_eval import (
    load_legal_intent_inventory,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (
    parse_slu_response,
    project_slu_label_v2,
)

SCHEMA = "saea-slurp-own-null-replicate-v1-read-v1"
ROW_ID = "SAEA-SLURP-DEV1000-NULL-REPLICATE-V1"
SEED = 20260903
N_REPLICATES = 10000
CI_LEVEL = 0.90

OFFICIAL = "slurp-slu-official-projected-v2"
NORMALIZED = "slurp-slu-f1-normalized-v1"
DERIVED_SUFFIX = ".own-null-replicate-v1-read.run-manifest.json"

COMPARATOR = ("SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1", "attempt-20260905T060424Z-2c5596")

#: The identity gate of section 3.2: no contrast is computed until the sealed
#: comparator reproduces the 2026-09-06 projection-v2 re-lock's own published
#: anchors, to the digit, from its own sealed bytes.
SEALED_ANCHORS = {
    "scenario": 82.60,
    "action": 74.60,
    "intent": 73.10,
    "entities_strict": 21.91,
    "word_f1": 33.69,
    "char_f1": 38.20,
    "slu_f1": 35.80,
    "unparsed": 3,
}

#: Per-row metrics paired through ``paired_contrast``.
PAIRED_METRICS = (
    "scenario_action_exact",
    "scenario_exact",
    "action_exact",
    "slot_f1_exact_f1",
    "slu_f1_word_f1",
    "slu_f1_char_f1",
    "slu_f1_f1",
)

#: Micro (pooled) metrics: name -> the TP/FP/FN field triples summed for it.
#: ``slu_f1`` sums the word- and char-distance counts before the F1, which is
#: what ``SLUScore.slu_f1`` and the official ``SLUF1.__call__`` do.
MICRO_METRICS = {
    "entities_strict": (
        ("slot_f1_exact_tp",),
        ("slot_f1_exact_fp",),
        ("slot_f1_exact_fn",),
    ),
    "word_f1": (("slu_f1_word_tp",), ("slu_f1_word_fp",), ("slu_f1_word_fn",)),
    "char_f1": (("slu_f1_char_tp",), ("slu_f1_char_fp",), ("slu_f1_char_fn",)),
    "slu_f1": (
        ("slu_f1_word_tp", "slu_f1_char_tp"),
        ("slu_f1_word_fp", "slu_f1_char_fp"),
        ("slu_f1_word_fn", "slu_f1_char_fn"),
    ),
}

MICRO_FIELDS = sorted(
    {name for triple in MICRO_METRICS.values() for group in triple for name in group}
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def attempt_dir(root, run_id, attempt_id):
    return Path(root) / "runs" / run_id / attempt_id


def sealed_manifest_path(root, run_id, attempt_id):
    return attempt_dir(root, run_id, attempt_id) / (run_id + ".run-manifest.json")


def write_derived_manifest(sealed, scorers):
    document = read_json(sealed)
    if list(document.get("scorers") or []) == list(scorers):
        raise SystemExit("derived manifest for %s would be a no-op copy" % sealed)
    document["scorers"] = list(scorers)
    derived = sealed.with_name(sealed.name.replace(".run-manifest.json", "") + DERIVED_SUFFIX)
    derived.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    return derived


def official_block(result):
    official = result["aggregate"]["official"]
    raw = official["raw"]
    per_sample = result["per_sample"]
    return {
        "scenario": round(100.0 * official["scenario_accuracy"], 2),
        "action": round(100.0 * official["action_accuracy"], 2),
        "intent": round(100.0 * official["intent_accuracy"], 2),
        "entities_strict": round(100.0 * float(raw["entities"]["f_measure"]), 2),
        "word_f1": round(100.0 * float(raw["entities_distance_word"]["f_measure"]), 2),
        "char_f1": round(100.0 * float(raw["entities_distance_char"]["f_measure"]), 2),
        "slu_f1": round(100.0 * official["slu_f1"], 2),
        "samples": len(per_sample),
        "unparsed": sum(1 for row in per_sample if not row["parsed"]),
        "identity_check_passed": bool(result["aggregate"]["identity_check"]["passed"]),
        "identity_check_slu_f1_abs_diff": result["aggregate"]["identity_check"]["slu_f1_abs_diff"],
    }


def normalized_block(result):
    micro = result["aggregate"]["normalized"]["micro"]
    return {
        "slu_f1": round(100.0 * float(micro["slu_f1"]), 2),
        "span_f1": round(100.0 * float(micro["span_f1"]), 2),
        "word_f1": round(100.0 * float(micro["word_f1"]), 2),
        "char_f1": round(100.0 * float(micro["char_f1"]), 2),
        "samples": int(micro["samples"]),
        "normalizer_id": result["aggregate"]["normalized"]["normalizer_id"],
        "false_merge_count": result["aggregate"]["normalized"]["false_merge_count"],
    }


def official_per_sample(result, fields):
    table = {}
    for row in result["per_sample"]:
        key = published_sample_key(str(row["sample_id"]))
        if key in table:
            raise SystemExit("duplicate published key %r" % key)
        table[key] = {field: float(row[field]) for field in fields}
    return table


def normalized_per_sample(result, fields):
    table = {}
    for row in result["per_sample"]:
        key = published_sample_key(str(row["sample_id"]))
        values = row["normalized"]
        table[key] = {field: float(values[field]) for field in fields}
    return table


def half_width(interval):
    return round((interval[1] - interval[0]) / 2.0, 4)


def _f1(tp, fp, fn):
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    if precision + recall == 0.0:
        return 0.0
    return 2.0 * precision * recall / (precision + recall)


def micro_block(left, right, ids, stratum_of, cluster_of):
    """The pooled (micro) F1 of each entity-side metric, and its delta, with
    both interval families. ``resampled_statistic`` hands the statistic the
    resampled id SEQUENCE -- ids repeat -- so a pooled ratio must sum over the
    sequence, which is exactly what this does."""

    out = {}
    for offset, (name, (tp_fields, fp_fields, fn_fields)) in enumerate(
        sorted(MICRO_METRICS.items())
    ):

        def pooled(table, resampled, tp_fields=tp_fields, fp_fields=fp_fields, fn_fields=fn_fields):
            tp = fp = fn = 0.0
            for sid in resampled:
                row = table[sid]
                for field in tp_fields:
                    tp += row[field]
                for field in fp_fields:
                    fp += row[field]
                for field in fn_fields:
                    fn += row[field]
            return _f1(tp, fp, fn)

        def statistic(resampled, pooled=pooled):
            return pooled(right, resampled) - pooled(left, resampled)

        entry = {
            "comparator_pct": round(100.0 * pooled(left, ids), 4),
            "replicate_pct": round(100.0 * pooled(right, ids), 4),
            "delta_pp": round(100.0 * statistic(ids), 4),
        }
        for family, kwargs in (
            ("clustered_by_speaker", {"cluster_of": cluster_of}),
            ("stratified_by_scenario", {"strata_of": stratum_of}),
        ):
            bootstrap = resampled_statistic(
                sample_ids=ids,
                statistic=statistic,
                seed=SEED + 100 + offset,
                n_replicates=N_REPLICATES,
                ci_level=CI_LEVEL,
                **kwargs,
            ).as_json()
            interval = [
                round(100.0 * bootstrap.get("ci_low", 0.0), 4),
                round(100.0 * bootstrap.get("ci_high", 0.0), 4),
            ]
            entry[family + "_ci90_pp"] = interval
            entry[family + "_half_width_pp"] = half_width(interval)
        out[name] = entry
    return out


def contrast_block(left, right, ids, stratum_of, cluster_of):
    """Both interval families, with half-widths, for every per-row metric."""

    out = {}
    for family, kwargs in (
        ("stratified_by_scenario", {"strata_of": stratum_of}),
        ("clustered_by_speaker", {"cluster_of": cluster_of}),
    ):
        contrasts = paired_contrast(
            left,
            right,
            metrics=PAIRED_METRICS,
            sample_ids=ids,
            seed=SEED,
            n_replicates=N_REPLICATES,
            ci_level=CI_LEVEL,
            **kwargs,
        )
        for metric, contrast in contrasts.items():
            document = contrast.as_dict()
            bootstrap = document.get("bootstrap") or {}
            entry = out.setdefault(metric, {})
            entry["n"] = document["n"]
            entry["comparator_pct"] = round(100.0 * document["left_mean"], 4)
            entry["replicate_pct"] = round(100.0 * document["right_mean"], 4)
            entry["delta_pp"] = round(100.0 * document["delta"], 4)
            entry["saves"] = document["saves"]
            entry["harms"] = document["harms"]
            entry["ties"] = document["ties"]
            entry["sign_test_p"] = document["sign_test_p"]
            interval = [
                round(100.0 * bootstrap.get("ci_low", 0.0), 4),
                round(100.0 * bootstrap.get("ci_high", 0.0), 4),
            ]
            entry[family + "_ci90_pp"] = interval
            entry[family + "_half_width_pp"] = half_width(interval)
            if family == "stratified_by_scenario":
                entry["per_stratum"] = {
                    name: {
                        "n": row["n"],
                        "comparator_pct": round(100.0 * row["left_mean"], 4),
                        "replicate_pct": round(100.0 * row["right_mean"], 4),
                        "delta_pp": round(100.0 * row["delta"], 4),
                        "saves": row["saves"],
                        "harms": row["harms"],
                    }
                    for name, row in document["per_stratum"].items()
                }
    return out


def equal_stratum_block(left, right, ids, stratum_of, cluster_of):
    """The equal-stratum weighting: the unweighted mean over gold scenarios of
    each scenario's own mean per-row delta, with its own CI90 under both
    resampling rules."""

    out = {}
    for offset, metric in enumerate(PAIRED_METRICS):

        def statistic(resampled, metric_name=metric):
            buckets = {}
            for sid in resampled:
                bucket = buckets.setdefault(stratum_of(sid), [0.0, 0])
                bucket[0] += right[sid][metric_name] - left[sid][metric_name]
                bucket[1] += 1
            if not buckets:
                return 0.0
            return sum(total / count for total, count in buckets.values()) / len(buckets)

        entry = {"point_pp": round(100.0 * statistic(ids), 4)}
        for family, kwargs in (
            ("stratified_by_scenario", {"strata_of": stratum_of}),
            ("clustered_by_speaker", {"cluster_of": cluster_of}),
        ):
            bootstrap = resampled_statistic(
                sample_ids=ids,
                statistic=statistic,
                seed=SEED + offset,
                n_replicates=N_REPLICATES,
                ci_level=CI_LEVEL,
                **kwargs,
            ).as_json()
            interval = [
                round(100.0 * bootstrap.get("ci_low", 0.0), 4),
                round(100.0 * bootstrap.get("ci_high", 0.0), 4),
            ]
            entry[family + "_ci90_pp"] = interval
            entry[family + "_half_width_pp"] = half_width(interval)
        out[metric] = entry
    return out


def load_outputs_text(root, run_id, attempt_id):
    path = attempt_dir(root, run_id, attempt_id) / (run_id + ".outputs.jsonl")
    table = {}
    for line in path.read_text(encoding="utf-8").split("\n"):
        if not line.strip():
            continue
        row = json.loads(line)
        table[published_sample_key(str(row["sample_id"]))] = str(row["text"])
    return table


def flip_block(left_text, right_text, ids, inventory, stratum_of, cluster_of):
    """The flip rates -- the quantity EVO-S1 round 1 estimated at 28.1 % on
    this carrier from a different arm's rows, and the reason this cell exists.

    Four surfaces, from the loosest to the one the paper-facing metric reads:
    the raw completion bytes; the parsed ``(scenario, action)``; the parsed slot
    set; and the projected intent the official scorer actually scores."""

    identical = 0
    raw_flip_ids = []
    label_flips = 0
    slot_flips = 0
    projected_flips = 0
    parse_flips = 0
    per_scenario = {}
    per_cluster_flips = Counter()
    for sample_id in ids:
        left = left_text[sample_id]
        right = right_text[sample_id]
        bucket = per_scenario.setdefault(
            stratum_of(sample_id), {"n": 0, "raw_flips": 0, "projected_intent_flips": 0}
        )
        bucket["n"] += 1
        if left == right:
            identical += 1
            continue
        raw_flip_ids.append(sample_id)
        bucket["raw_flips"] += 1
        per_cluster_flips[cluster_of(sample_id)] += 1
        left_scenario, left_action, left_entities, left_parsed = parse_slu_response(left)
        right_scenario, right_action, right_entities, right_parsed = parse_slu_response(right)
        if left_parsed != right_parsed:
            parse_flips += 1
        if (left_scenario, left_action) != (right_scenario, right_action):
            label_flips += 1
        left_slots = sorted((entity.type, entity.filler) for entity in left_entities)
        right_slots = sorted((entity.type, entity.filler) for entity in right_entities)
        if left_slots != right_slots:
            slot_flips += 1
        left_projected = project_slu_label_v2(
            left_scenario, left_action, inventory, parsed=left_parsed
        )
        right_projected = project_slu_label_v2(
            right_scenario, right_action, inventory, parsed=right_parsed
        )
        if (left_projected.scenario, left_projected.action) != (
            right_projected.scenario,
            right_projected.action,
        ):
            projected_flips += 1
            bucket["projected_intent_flips"] += 1

    total = len(ids)
    for bucket in per_scenario.values():
        bucket["raw_flip_rate_pct"] = round(100.0 * bucket["raw_flips"] / bucket["n"], 2)
    return {
        "rows": total,
        "raw_completion_identical": identical,
        "raw_completion_identity_rate_pct": round(100.0 * identical / total, 2),
        "raw_completion_flips": total - identical,
        "raw_completion_flip_rate_pct": round(100.0 * (total - identical) / total, 2),
        "parsed_label_flips": label_flips,
        "parsed_label_flip_rate_pct": round(100.0 * label_flips / total, 2),
        "parsed_slot_set_flips": slot_flips,
        "parsed_slot_set_flip_rate_pct": round(100.0 * slot_flips / total, 2),
        "parse_success_flips": parse_flips,
        "projected_intent_flips": projected_flips,
        "projected_intent_flip_rate_pct": round(100.0 * projected_flips / total, 2),
        "clusters_with_a_flip": len(per_cluster_flips),
        "per_scenario": {name: per_scenario[name] for name in sorted(per_scenario)},
        "imported_floor_being_replaced": {
            "source": "docs/readiness/2026-09-06-slurp-evo-s1-round-1-verdict.md section 1",
            "measurement": "286 of 1,019 byte-identically prompted rows (28.1 %) returned "
            "different text anyway",
            "rate_pct": 28.1,
        },
    }


def per_cluster_block(left, right, ids, cluster_of, metrics=("scenario_action_exact", "slu_f1_f1")):
    """Per-speaker-cluster deltas -- descriptive, and the covariate the cluster
    bootstrap is resampling over."""

    buckets = {}
    for sample_id in ids:
        buckets.setdefault(cluster_of(sample_id), []).append(sample_id)
    rows = []
    for name in sorted(buckets):
        members = buckets[name]
        row = {"cluster": name, "n": len(members)}
        for metric in metrics:
            delta = sum(right[sid][metric] - left[sid][metric] for sid in members) / len(members)
            row[metric + "_delta_pp"] = round(100.0 * delta, 4)
        rows.append(row)
    moved = {
        metric: sum(1 for row in rows if row[metric + "_delta_pp"] != 0.0) for metric in metrics
    }
    return {
        "clusters": len(rows),
        "largest": max(row["n"] for row in rows),
        "median": sorted(row["n"] for row in rows)[len(rows) // 2],
        "clusters_moved": moved,
        "rows": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--score-dir", type=Path, default=None)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--reuse-score-dir", action="store_true")
    args = parser.parse_args()

    lock = load_lock(umbrella_lock_path())
    root = Path(data_root())
    started = datetime.now(timezone.utc)

    arms = {"REPLICATE": (ROW_ID, args.attempt_id), "COMPARATOR": COMPARATOR}

    score_dir = Path(args.score_dir or (root / "runs" / ROW_ID / "own-null-read-score-batch"))
    if score_dir.exists() and any(score_dir.iterdir()) and not args.reuse_score_dir:
        raise SystemExit("score directory is not empty: %s" % score_dir)

    manifests = {}
    jobs = []
    for arm, (run_id, attempt_id) in arms.items():
        sealed = sealed_manifest_path(root, run_id, attempt_id)
        if not sealed.is_file():
            raise SystemExit("sealed manifest missing for %s: %s" % (arm, sealed))
        sealed_doc = read_json(sealed)
        derived = write_derived_manifest(sealed, [OFFICIAL, NORMALIZED])
        manifests[arm] = {
            "run_id": run_id,
            "attempt_id": attempt_id,
            "sealed_manifest": str(sealed),
            "sealed_manifest_sha256": sha256_file(sealed),
            "sealed_manifest_scorers": sealed_doc["scorers"],
            "derived_manifest": str(derived),
            "derived_manifest_sha256": sha256_file(derived),
            "derived_manifest_scorers": [OFFICIAL, NORMALIZED],
            "status": sealed_doc["status"],
            "study_commit": sealed_doc["study_commit"],
            "protocol_hash": sealed_doc.get("protocol_hash"),
            "cost": sealed_doc["cost"],
        }
        jobs.append(ScoreJob(job_id=arm.lower(), manifest=derived))

    if args.reuse_score_dir:
        batch = read_json(score_dir / "batch-summary.json")
    else:
        batch = run_score_batch(
            jobs, output_dir=score_dir, max_workers=args.workers, include_per_sample=True
        )
        (score_dir / "batch-summary.json").write_text(
            json.dumps(batch, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    results = {}
    for arm in arms:
        path = score_dir / (arm.lower() + ".score.json")
        document = read_json(path)
        if document.get("verified") is not True:
            raise SystemExit("score file %s is not a verified manifest score" % path)
        results[arm] = document["scores"]
        manifests[arm]["score_file"] = str(path)
        manifests[arm]["score_file_sha256"] = sha256_file(path)

    official = {arm: official_block(results[arm][OFFICIAL]) for arm in arms}
    normalized = {arm: normalized_block(results[arm][NORMALIZED]) for arm in arms}

    # ---------------- the identity gate, section 3.2 ---------------------
    gate = {}
    for name, expected in SEALED_ANCHORS.items():
        actual = official["COMPARATOR"][name]
        gate[name] = {"expected": expected, "actual": actual, "equal": actual == expected}
    gate["identity_check_passed"] = {
        "expected": True,
        "actual": official["COMPARATOR"]["identity_check_passed"],
        "equal": official["COMPARATOR"]["identity_check_passed"] is True,
    }
    gate_passed = all(entry["equal"] for entry in gate.values())
    if not gate_passed:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(
                {"schema": SCHEMA, "identity_gate": gate, "identity_gate_passed": False},
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print("IDENTITY GATE FAILED")
        print(json.dumps(gate, indent=2, sort_keys=True))
        return 1

    # ---------------- the pairing ----------------------------------------
    fields = tuple(PAIRED_METRICS) + tuple(MICRO_FIELDS)
    left = official_per_sample(results["COMPARATOR"][OFFICIAL], fields)
    right = official_per_sample(results["REPLICATE"][OFFICIAL], fields)
    left_norm = normalized_per_sample(results["COMPARATOR"][NORMALIZED], fields)
    right_norm = normalized_per_sample(results["REPLICATE"][NORMALIZED], fields)

    ids = sorted(set(left) & set(right))
    if len(ids) != len(left) or len(ids) != len(right):
        raise SystemExit(
            "the two arms do not pair row for row: %d common, %d comparator, %d replicate"
            % (len(ids), len(left), len(right))
        )

    gold = {record.sample_id: record for record in load_slurp_split(lock, root, "devel")}
    speakers = _slurp_speaker_index(_governed_roots(lock, root)[2])

    def stratum_of(sample_id):
        return str(gold[sample_id].scenario)

    def cluster_of(sample_id):
        return "spk:" + str(speakers[sample_id.rsplit(":", 1)[-1] + ".flac"])

    contrasts = contrast_block(left, right, ids, stratum_of, cluster_of)
    contrasts_normalized = contrast_block(left_norm, right_norm, ids, stratum_of, cluster_of)
    micro = micro_block(left, right, ids, stratum_of, cluster_of)
    micro_normalized = micro_block(left_norm, right_norm, ids, stratum_of, cluster_of)
    equal_stratum = equal_stratum_block(left, right, ids, stratum_of, cluster_of)

    inventory = load_legal_intent_inventory(lock, root)
    flips = flip_block(
        load_outputs_text(root, *COMPARATOR),
        load_outputs_text(root, ROW_ID, args.attempt_id),
        ids,
        inventory,
        stratum_of,
        cluster_of,
    )
    clusters = per_cluster_block(left, right, ids, cluster_of)

    # ---------------- the margins this cell publishes --------------------
    margins = {}
    for name, entry in micro.items():
        margins["micro_" + name] = {
            "margin_pp": entry["clustered_by_speaker_half_width_pp"],
            "null_interval_pp": entry["clustered_by_speaker_ci90_pp"],
            "delta_pp": entry["delta_pp"],
            "estimand": "micro (pooled) F1, the paper-facing figure",
        }
    for metric in PAIRED_METRICS:
        entry = contrasts[metric]
        margins["per_row_" + metric] = {
            "margin_pp": entry["clustered_by_speaker_half_width_pp"],
            "null_interval_pp": entry["clustered_by_speaker_ci90_pp"],
            "delta_pp": entry["delta_pp"],
            "estimand": "mean of the per-row value",
        }

    intent = contrasts["scenario_action_exact"]
    intent_margin = intent["clustered_by_speaker_half_width_pp"]
    slu_margin = micro["slu_f1"]["clustered_by_speaker_half_width_pp"]

    # ---------------- section 4.1: the silence-tail re-read --------------
    tail = {
        "cell": "SAEA-SLURP-DEV1000-CLOSED-LIST-TAIL2S-V1",
        "verdict_document": "docs/readiness/2026-09-09-slurp-silence-tail-v1-verdict.md",
        "note": (
            "a re-reading of already-sealed numbers against a new reference. The tail cell "
            "is NOT re-flown and NOT re-scored, and its NOT ADMITTED status is not reopened "
            "by this cell."
        ),
        "sealed": {
            "intent_delta_pp": 1.3000,
            "intent_ci90_clustered_pp": [0.1934, 2.4262],
            "scenario_ci90_clustered_pp": [-0.6921, 1.4085],
            "action_ci90_clustered_pp": [-0.0987, 2.1102],
            "slu_f1_per_row_ci90_clustered_pp": [0.1455, 2.4788],
            "clause_1_imported_bar_pp": 0.60,
        },
        "measured_margins": {
            "intent_per_row_half_width_pp": intent_margin,
            "intent_null_interval_pp": intent["clustered_by_speaker_ci90_pp"],
            "slu_f1_micro_half_width_pp": slu_margin,
            "slu_f1_micro_null_interval_pp": micro["slu_f1"]["clustered_by_speaker_ci90_pp"],
        },
        "clause_1_at_measured_margin": {
            "rule": "the intent CI90 lower bound must exceed the measured margin",
            "lower_bound_pp": 0.1934,
            "measured_margin_pp": intent_margin,
            "passes": 0.1934 > intent_margin,
        },
        "intent_effect_disjoint_from_null": (
            0.1934 > intent["clustered_by_speaker_ci90_pp"][1]
            or 2.4262 < intent["clustered_by_speaker_ci90_pp"][0]
        ),
        "intent_effect_in_null_half_widths": (
            round(1.3000 / intent_margin, 2) if intent_margin else None
        ),
    }

    cluster_sizes = Counter(cluster_of(sample_id) for sample_id in ids)

    document = {
        "schema": SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "row": ROW_ID,
        "generated_at": started.isoformat(),
        "preregistration": (
            "docs/readiness/2026-09-09-slurp-own-null-replicate-v1-preregistration.md"
        ),
        "there_is_no_verdict": (
            "This cell has no factor. It admits and refutes nothing, and carries no "
            "ADMITTED / NOT-ADMITTED line. Its whole output is a table of intervals."
        ),
        "contacts": {
            "frozen_core": 0,
            "gpu_hours": 0,
            "servers_started": 0,
            "network": 0,
            "paid_api_spend": 0,
        },
        "manifests": manifests,
        "score_batch": {
            "output_dir": str(score_dir),
            "jobs": [job.job_id for job in jobs],
            "include_per_sample": True,
            "sharded": False,
            "succeeded": batch.get("succeeded"),
            "failed": batch.get("failed"),
        },
        "official": official,
        "normalized": normalized,
        "identity_gate": gate,
        "identity_gate_passed": gate_passed,
        "population": {
            "paired_rows": len(ids),
            "scenarios": len(set(stratum_of(sample_id) for sample_id in ids)),
            "speaker_clusters": len(cluster_sizes),
            "largest_cluster": max(cluster_sizes.values()),
            "median_cluster": sorted(cluster_sizes.values())[len(cluster_sizes) // 2],
        },
        "flip_rates": flips,
        "null_table_micro_official": micro,
        "null_table_micro_normalized": micro_normalized,
        "null_table_per_row_official": contrasts,
        "null_table_per_row_normalized": contrasts_normalized,
        "equal_stratum_official": equal_stratum,
        "per_cluster": clusters,
        "margins": margins,
        "silence_tail_reread": tail,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(document, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print("identity gate: PASS")
    print(json.dumps(official, indent=2, sort_keys=True))
    print("flips: %s" % json.dumps({k: v for k, v in flips.items() if k != "per_scenario"}))
    print("--- micro (pooled) ---")
    for name, entry in sorted(micro.items()):
        print(
            "%-16s %8.4f -> %8.4f  delta %+8.4f  clustered %s half-width %.4f"
            % (
                name,
                entry["comparator_pct"],
                entry["replicate_pct"],
                entry["delta_pp"],
                entry["clustered_by_speaker_ci90_pp"],
                entry["clustered_by_speaker_half_width_pp"],
            )
        )
    print("--- per row ---")
    for metric in PAIRED_METRICS:
        row = contrasts[metric]
        print(
            "%-22s %8.4f -> %8.4f  delta %+8.4f  clustered %s half-width %.4f  saves %d harms %d"
            % (
                metric,
                row["comparator_pct"],
                row["replicate_pct"],
                row["delta_pp"],
                row["clustered_by_speaker_ci90_pp"],
                row["clustered_by_speaker_half_width_pp"],
                row["saves"],
                row["harms"],
            )
        )
    print("read -> %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
