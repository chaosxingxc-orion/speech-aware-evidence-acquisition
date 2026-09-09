#!/usr/bin/env python3
"""The single registered read of the SLURP silence-tail cell.

Scoring-side only. **Zero model, GPU, tool, embedding and network contacts.**
Preregistration:
``docs/readiness/2026-09-07-cross-carrier-silence-tail-v1-preregistration.md``
sections 1.2, 2, 3 and 4.1.

The cell ``SAEA-SLURP-DEV1000-CLOSED-LIST-TAIL2S-V1`` and its sealed comparator
``SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1`` are each scored ONCE over their
complete 1,000-row manifest through ``core.scoring_batch`` with
``include_per_sample=True``, one job per manifest, never sharded, under the
paper-facing ``slurp-slu-official-projected-v2`` and the secondary
``slurp-slu-f1-normalized-v1``.

Both scorers need a manifest that declares them, and ``core.bundle
.verify_bundle`` confines every artifact path a manifest names to the
manifest's own directory. So ONE derived manifest is written beside each sealed
one, differing from it only in the ``scorers`` list; its sha256 goes into this
read's output and neither replaces a sealed manifest.

Pairing is per row on the published key recovered by splitting the ``@ts2``
suffix (``data.variant_ids.published_sample_key``). Strata are the gold
scenario, read only inside this analysis and never in a request path; clusters
are the SLURP speaker (``usrid``), because one speaker's utterances are not
independent draws. The two interval families are reported side by side and the
speaker-clustered one is read as the honest interval, exactly as the
Earnings-21 cell reads its call-clustered one.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
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

SCHEMA = "saea-slurp-silence-tail-v1-read-v1"
ROW_ID = "SAEA-SLURP-DEV1000-CLOSED-LIST-TAIL2S-V1"
SEED = 20260903
N_REPLICATES = 10000
CI_LEVEL = 0.90

OFFICIAL = "slurp-slu-official-projected-v2"
NORMALIZED = "slurp-slu-f1-normalized-v1"
DERIVED_SUFFIX = ".silence-tail-v1-read.run-manifest.json"

CELL = (ROW_ID, None)  # attempt id supplied on the command line
COMPARATOR = ("SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1", "attempt-20260905T060424Z-2c5596")

#: Section 1.2's sealed anchors for the comparator under the paper-facing
#: scorer. The identity gate of section 2: no contrast is computed until the
#: sealed comparator reproduces these to the digit from its own sealed bytes.
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

PAIRED_METRICS = (
    "scenario_action_exact",
    "scenario_exact",
    "action_exact",
    "slot_f1_exact_f1",
    "slu_f1_word_f1",
    "slu_f1_char_f1",
    "slu_f1_f1",
)

#: Section 4.1, quoted so the rule this read applies is the rule that was
#: fixed before any number existed.
RULE_4_1 = (
    "ADMITTED as a model-usage local optimization iff all three hold: "
    "(1) Intent accuracy (scenario+action), the paper-facing headline. The CI90 "
    "lower bound on the delta is > +0.60 pp -- above zero and above the imported "
    "null margin. Point estimate positive. "
    "(2) SLU-F1 does not worsen. Its CI90 lower bound is above -0.60 pp "
    "(non-inferiority at the same imported margin), and scenario and action "
    "accuracy are both non-inferior on the same rule. "
    "(3) No stratum is harmed beyond the carrier's own rule. SLURP's per-scenario "
    "harm bound, as EVO-S1 already uses it: no scenario loses more than 3.0 pp of "
    "intent accuracy, and at most 2 of the 18 scenarios lose anything at all."
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


def official_per_sample(result):
    """``{published key: {metric: value}}`` from one official-scorer result."""
    table = {}
    for row in result["per_sample"]:
        key = published_sample_key(str(row["sample_id"]))
        if key in table:
            raise SystemExit("duplicate published key %r" % key)
        table[key] = {metric: float(row[metric]) for metric in PAIRED_METRICS}
    return table


def normalized_per_sample(result):
    table = {}
    for row in result["per_sample"]:
        key = published_sample_key(str(row["sample_id"]))
        values = row["normalized"]
        table[key] = {metric: float(values[metric]) for metric in PAIRED_METRICS}
    return table


def contrast_block(left, right, ids, stratum_of, cluster_of):
    """Both interval families for every paired metric, on the same rows."""

    out = {}
    for family, kwargs in (
        ("stratified_by_scenario", {"strata_of": stratum_of}),
        ("clustered_by_speaker", {"cluster_of": cluster_of}),
    ):
        contrasts = paired_contrast(
            left,
            right,
            metrics=PAIRED_METRICS,
            sample_ids=sorted(ids),
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
            entry["left_pct"] = round(100.0 * document["left_mean"], 4)
            entry["right_pct"] = round(100.0 * document["right_mean"], 4)
            entry["delta_pp"] = round(100.0 * document["delta"], 4)
            entry["saves"] = document["saves"]
            entry["harms"] = document["harms"]
            entry["ties"] = document["ties"]
            entry["sign_test_p"] = document["sign_test_p"]
            entry[family + "_ci90_pp"] = [
                round(100.0 * bootstrap.get("ci_low", 0.0), 4),
                round(100.0 * bootstrap.get("ci_high", 0.0), 4),
            ]
            if family == "stratified_by_scenario":
                entry["per_stratum"] = {
                    name: {
                        "n": row["n"],
                        "left_pct": round(100.0 * row["left_mean"], 4),
                        "right_pct": round(100.0 * row["right_mean"], 4),
                        "delta_pp": round(100.0 * row["delta"], 4),
                        "saves": row["saves"],
                        "harms": row["harms"],
                    }
                    for name, row in document["per_stratum"].items()
                }
    return out


def equal_stratum_block(left, right, ids, stratum_of, cluster_of):
    """The equal-stratum weighting: the unweighted mean over scenarios of each
    scenario's own mean per-row delta, with its own CI90 under both resampling
    rules. A resample that misses a scenario averages over the scenarios it
    drew, which is what an equal-stratum estimator under resampling is."""

    ordered = sorted(ids)
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

        entry = {"point_pp": round(100.0 * statistic(ordered), 4)}
        for family, kwargs in (
            ("stratified_by_scenario", {"strata_of": stratum_of}),
            ("clustered_by_speaker", {"cluster_of": cluster_of}),
        ):
            bootstrap = resampled_statistic(
                sample_ids=ordered,
                statistic=statistic,
                seed=SEED + offset,
                n_replicates=N_REPLICATES,
                ci_level=CI_LEVEL,
                **kwargs,
            ).as_json()
            entry[family + "_ci90_pp"] = [
                round(100.0 * bootstrap.get("ci_low", 0.0), 4),
                round(100.0 * bootstrap.get("ci_high", 0.0), 4),
            ]
        out[metric] = entry
    return out


def decide(contrasts, family):
    """Section 4.1, applied to one interval family."""

    intent = contrasts["scenario_action_exact"]
    slu = contrasts["slu_f1_f1"]
    scenario = contrasts["scenario_exact"]
    action = contrasts["action_exact"]
    key = family + "_ci90_pp"

    clause1 = intent[key][0] > 0.60 and intent["delta_pp"] > 0.0
    clause2 = (
        slu[key][0] > -0.60 and scenario[key][0] > -0.60 and action[key][0] > -0.60
    )
    losers = {
        name: row["delta_pp"]
        for name, row in intent["per_stratum"].items()
        if row["delta_pp"] < 0.0
    }
    worst = min(losers.values()) if losers else 0.0
    clause3 = len(losers) <= 2 and worst >= -3.0

    inside_imported_margin = (
        intent[key][0] >= -0.60 and intent[key][1] <= 0.60
    )
    return {
        "family": family,
        "clause_1_intent_lb_gt_0_60": clause1,
        "clause_1_detail": {
            "intent_delta_pp": intent["delta_pp"],
            "intent_ci90_pp": intent[key],
        },
        "clause_2_non_inferiority": clause2,
        "clause_2_detail": {
            "slu_f1_ci90_pp": slu[key],
            "scenario_ci90_pp": scenario[key],
            "action_ci90_pp": action[key],
        },
        "clause_3_per_scenario_harm_bound": clause3,
        "clause_3_detail": {
            "scenarios_losing_intent": len(losers),
            "worst_scenario_delta_pp": round(worst, 4),
            "losers": {name: round(value, 4) for name, value in sorted(losers.items())},
        },
        "inside_imported_null_margin": inside_imported_margin,
        "verdict": (
            "ADMITTED"
            if (clause1 and clause2 and clause3)
            else (
                "HARMFUL"
                if (intent["delta_pp"] < 0.0 and intent[key][1] < -0.60)
                else "NOT ADMITTED"
            )
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt-id", required=True, help="the cell's sealed attempt")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--score-dir", type=Path, default=None)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--reuse-score-dir", action="store_true")
    args = parser.parse_args()

    lock = load_lock(umbrella_lock_path())
    root = Path(data_root())
    started = datetime.now(timezone.utc)

    arms = {
        "CELL": (ROW_ID, args.attempt_id),
        "COMPARATOR": COMPARATOR,
    }

    score_dir = Path(args.score_dir or (root / "runs" / ROW_ID / "silence-tail-read-score-batch"))
    if score_dir.exists() and any(score_dir.iterdir()) and not args.reuse_score_dir:
        raise SystemExit("score directory is not empty: %s" % score_dir)

    manifests = {}
    jobs = []
    for arm, (run_id, attempt_id) in arms.items():
        sealed = sealed_manifest_path(root, run_id, attempt_id)
        if not sealed.is_file():
            raise SystemExit("sealed manifest missing for %s: %s" % (arm, sealed))
        derived = write_derived_manifest(sealed, [OFFICIAL, NORMALIZED])
        manifests[arm] = {
            "run_id": run_id,
            "attempt_id": attempt_id,
            "sealed_manifest": str(sealed),
            "sealed_manifest_sha256": sha256_file(sealed),
            "sealed_manifest_scorers": read_json(sealed)["scorers"],
            "derived_manifest": str(derived),
            "derived_manifest_sha256": sha256_file(derived),
            "derived_manifest_scorers": [OFFICIAL, NORMALIZED],
            "status": read_json(sealed)["status"],
            "study_commit": read_json(sealed)["study_commit"],
            "cost": read_json(sealed)["cost"],
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

    # ---------------- the identity gate, section 2 -----------------------
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
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(
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
    left = official_per_sample(results["COMPARATOR"][OFFICIAL])
    right = official_per_sample(results["CELL"][OFFICIAL])
    left_norm = normalized_per_sample(results["COMPARATOR"][NORMALIZED])
    right_norm = normalized_per_sample(results["CELL"][NORMALIZED])

    ids = sorted(set(left) & set(right))
    if len(ids) != len(left) or len(ids) != len(right):
        raise SystemExit(
            "the two arms do not pair row for row: %d common, %d comparator, %d cell"
            % (len(ids), len(left), len(right))
        )

    gold = {record.sample_id: record for record in load_slurp_split(lock, root, "devel")}
    speakers = _slurp_speaker_index(_governed_roots(lock, root)[2])

    def stratum_of(sample_id):
        return str(gold[sample_id].scenario)

    def recording_of(sample_id):
        return sample_id.rsplit(":", 1)[-1] + ".flac"

    def cluster_of(sample_id):
        return "spk:" + str(speakers[recording_of(sample_id)])

    contrasts = contrast_block(left, right, ids, stratum_of, cluster_of)
    contrasts_normalized = contrast_block(left_norm, right_norm, ids, stratum_of, cluster_of)
    equal_stratum = equal_stratum_block(left, right, ids, stratum_of, cluster_of)
    equal_stratum_normalized = equal_stratum_block(
        left_norm, right_norm, ids, stratum_of, cluster_of
    )

    decisions = {
        family: decide(contrasts, family)
        for family in ("clustered_by_speaker", "stratified_by_scenario")
    }
    honest = decisions["clustered_by_speaker"]

    sign_agreement = {
        metric: {
            "official_delta_pp": contrasts[metric]["delta_pp"],
            "normalized_delta_pp": contrasts_normalized[metric]["delta_pp"],
            "same_sign": (
                (contrasts[metric]["delta_pp"] > 0) == (contrasts_normalized[metric]["delta_pp"] > 0)
                and (contrasts[metric]["delta_pp"] < 0)
                == (contrasts_normalized[metric]["delta_pp"] < 0)
            ),
        }
        for metric in PAIRED_METRICS
    }

    cluster_sizes = {}
    for sample_id in ids:
        name = cluster_of(sample_id)
        cluster_sizes[name] = cluster_sizes.get(name, 0) + 1

    document = {
        "schema": SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "row": ROW_ID,
        "generated_at": started.isoformat(),
        "preregistration": (
            "docs/readiness/2026-09-07-cross-carrier-silence-tail-v1-preregistration.md"
        ),
        "rule_4_1_verbatim": RULE_4_1,
        "null": {
            "measured_on_this_carrier": False,
            "margin_pp": 0.60,
            "provenance": (
                "IMPORTED, not measured. Section 3: no same-request null has been measured "
                "on SLURP, so the admission clause uses zero as the null and adds a margin "
                "of 0.60 pp, section 4.1's own figure, taken from the Earnings-22 null's "
                "half-width on the same scale. A result inside that margin is NOT ADMITTED "
                "and NOT REFUTED, and measuring this carrier's own null becomes the named "
                "next cell rather than a footnote."
            ),
        },
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
        "contrasts_official_projected_v2": contrasts,
        "contrasts_normalized_secondary": contrasts_normalized,
        "equal_stratum_official_projected_v2": equal_stratum,
        "equal_stratum_normalized_secondary": equal_stratum_normalized,
        "secondary_sign_agreement": sign_agreement,
        "decisions": decisions,
        "verdict": honest["verdict"],
        "verdict_family": "clustered_by_speaker",
        "verdict_families_agree": (
            decisions["clustered_by_speaker"]["verdict"]
            == decisions["stratified_by_scenario"]["verdict"]
        ),
    }

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(
        json.dumps(document, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print("identity gate: PASS")
    print(json.dumps(official, indent=2, sort_keys=True))
    print(json.dumps(normalized, indent=2, sort_keys=True))
    for metric in PAIRED_METRICS:
        row = contrasts[metric]
        print(
            "%-22s %8.4f -> %8.4f  delta %+8.4f  clustered %s  stratified %s  saves %d harms %d"
            % (
                metric,
                row["left_pct"],
                row["right_pct"],
                row["delta_pp"],
                row["clustered_by_speaker_ci90_pp"],
                row["stratified_by_scenario_ci90_pp"],
                row["saves"],
                row["harms"],
            )
        )
    print(json.dumps(decisions, indent=2, sort_keys=True))
    print("VERDICT: %s" % document["verdict"])
    print("read -> %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
