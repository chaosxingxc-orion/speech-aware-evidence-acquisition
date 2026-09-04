#!/usr/bin/env python3
"""Zero-contact re-scoring of the sealed Earnings-21 N10 direct-baseline block.

Reads three already-sealed, FINALIZED attempt bundles and re-scores their
persisted outputs through the SAME registered scorers the in-run path uses
(``core.base.SCORERS``): ``asr-wer`` (frozen saea-scoring-v1), ``asr-wer-whisper``
(vendored Whisper EnglishTextNormalizer) and ``entity-wer`` (mention-level, the
wer_tags sidecar).  No model, GPU, network or audio contact of any kind: every
number is a pure function of (sealed outputs bytes, frozen reference layer).

Both aggregations are reported for every WER family:
  * corpus-level (micro): sum(S+D+I) / sum(reference words) -- the convention of
    every published Earnings row;
  * mean of per-call WER (macro) -- what ``asr-wer``'s own aggregate prints.
Corpus-level is derived from the per-sample error/reference-word counts each
scorer already records; alignment is never re-implemented here.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(sys.argv[1]).resolve()
OUT_PATH = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.base import SCORERS  # noqa: E402
import speech_aware_evidence_acquisition.core.scorers  # noqa: F401,E402
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.e0.artifacts import sha256_file  # noqa: E402

RUNS = Path(os.environ["SPEECHRL_DATA_DIR"]) / "runs"

ARMS = [
    ("SAEA-E-005B-N10-zero", "attempt-20260814T235515Z-044ccc", "bare-core / no ConEC context"),
    ("SAEA-E-005B-N10-matched", "attempt-20260815T011459Z-30cb33", "ConEC matched context"),
    ("SAEA-E-005B-N10-names", "attempt-20260815T025126Z-30d1a1", "ConEC names list"),
]


def corpus_from_per_sample(per_sample):
    s = sum(int(r["substitutions"]) for r in per_sample)
    d = sum(int(r["deletions"]) for r in per_sample)
    i = sum(int(r["insertions"]) for r in per_sample)
    h = sum(int(r["hits"]) for r in per_sample)
    ref_words = h + s + d
    return {
        "substitutions": s,
        "deletions": d,
        "insertions": i,
        "hits": h,
        "reference_words": ref_words,
        "errors": s + d + i,
        "corpus_wer": (s + d + i) / ref_words if ref_words else 0.0,
    }


def main() -> int:
    lock = load_lock(umbrella_lock_path())
    root = data_root()
    report = {
        "schema": "saea-earnings21-scoring-alignment-v1",
        "zero_contact": {
            "model_calls": 0,
            "gpu_seconds": 0,
            "audio_seconds": 0,
            "tool_contacts": 0,
            "network_contacts": 0,
        },
        "data_root": str(root),
        "umbrella_lock_sha256": sha256_file(umbrella_lock_path()),
        "arms": {},
    }
    for run_id, attempt_id, description in ARMS:
        attempt_dir = RUNS / run_id / attempt_id
        manifest_path = attempt_dir / f"{run_id}.run-manifest.json"
        outputs_path = attempt_dir / f"{run_id}.outputs.jsonl"
        scores_path = attempt_dir / f"{run_id}.scores.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        sealed = json.loads(scores_path.read_text(encoding="utf-8"))

        outputs_sha = sha256_file(outputs_path)
        if outputs_sha != manifest["outputs"]["sha256"]:
            raise SystemExit(f"{run_id}: outputs sha256 drift; refusing to score")

        durations = {}
        for obs in sorted(attempt_dir.glob(f"{run_id}.obs-derivation.*.json")):
            doc = json.loads(obs.read_text(encoding="utf-8"))
            durations[str(doc["sample_id"])] = {
                "decoded_duration_seconds": doc["decoded_duration_seconds"],
                "slices": len(doc["slices"]),
                "boundary_mode": doc["boundary_mode"],
                "slice_seconds": (
                    doc["slices"][0]["audio_seconds"] if doc["slices"] else None
                ),
            }

        arm_report = {
            "description": description,
            "attempt_id": attempt_id,
            "manifest_sha256": sha256_file(manifest_path),
            "outputs_sha256": outputs_sha,
            "sealed_scores_sha256": sha256_file(scores_path),
            "manifest_status": manifest["status"],
            "manifest_scorers": manifest["scorers"],
            "config_fragments": manifest["config"]["fragments"],
            "split_ids": manifest["split"]["ids"],
            "sealed_asr_wer_mean": sealed["asr-wer"]["aggregate"]["mean_wer"],
            "observation": durations,
            "scorers": {},
        }

        for name in ("asr-wer", "asr-wer-whisper", "entity-wer"):
            result = SCORERS.resolve(name)(outputs_path, lock, root)
            arm_report["scorers"][name] = result

        # Identity anchor: the freshly recomputed asr-wer aggregate must equal
        # the sealed one before any new number from this run is trusted.
        fresh_mean = arm_report["scorers"]["asr-wer"]["aggregate"]["mean_wer"]
        arm_report["identity_check"] = {
            "sealed_mean_wer": sealed["asr-wer"]["aggregate"]["mean_wer"],
            "recomputed_mean_wer": fresh_mean,
            "abs_diff": abs(fresh_mean - sealed["asr-wer"]["aggregate"]["mean_wer"]),
            "passed": abs(fresh_mean - sealed["asr-wer"]["aggregate"]["mean_wer"]) < 1e-12,
        }
        if not arm_report["identity_check"]["passed"]:
            raise SystemExit(f"{run_id}: recomputed asr-wer does not match the sealed value")

        asr = arm_report["scorers"]["asr-wer"]
        whi = arm_report["scorers"]["asr-wer-whisper"]
        arm_report["aggregations"] = {
            "saea-scoring-v1": {
                "corpus": corpus_from_per_sample(asr["per_sample"]),
                "mean_of_per_call_wer": asr["aggregate"]["mean_wer"],
                "samples": asr["aggregate"]["samples"],
            },
            "whisper-EnglishTextNormalizer": {
                "corpus": corpus_from_per_sample(whi["per_sample"]),
                "corpus_wer_from_scorer_aggregate": whi["aggregate"]["corpus_wer"],
                "mean_of_per_call_wer": sum(r["wer"] for r in whi["per_sample"])
                / len(whi["per_sample"]),
                "samples": whi["aggregate"]["samples"],
                "scorer_version": whi["aggregate"]["scorer_version"],
                "normalizer": whi["aggregate"]["normalizer"],
            },
        }
        cross = abs(
            arm_report["aggregations"]["whisper-EnglishTextNormalizer"]["corpus"]["corpus_wer"]
            - whi["aggregate"]["corpus_wer"]
        )
        arm_report["aggregations"]["whisper_corpus_cross_check_abs_diff"] = cross
        if cross > 1e-12:
            raise SystemExit(f"{run_id}: whisper corpus cross-check failed")

        report["arms"][run_id] = arm_report

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
