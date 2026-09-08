#!/usr/bin/env python3
"""Post-hoc scoring of the Earnings-21 own-null replicate under the four agentic metrics.

The replicate's manifest declares the sealed comparator's own four scorers, because
``scorers`` is a baseline-fragment key and therefore enters ``config_hash`` ->
``protocol_hash`` -- the identity this cell exists to hold fixed (preregistration
section 1.1).  The three remaining agentic metrics are produced exactly as the
COMPARATOR's own were: one re-scoring bundle per metric, holding byte-identical
copies of the sealed artifacts and a manifest that differs from the sealed one in
exactly two respects (the artifact ``path`` fields point at the copies, and
``scorers`` names the one metric), scored through ``core.scoring_batch`` -- one
complete VERIFIED manifest per process, never sharded.

This is ``analysis.e21_agentic_metric_baseline``'s own mechanism, parameterised by
attempt rather than pinned to the comparator's; ``run_scoring`` is imported from
that module unchanged, so the batch settings (one worker, ``include_per_sample``)
are the registered ones and not a second dialect.

    python e21_null_replicate_rescore.py build <attempt_dir> <run_id> <out_root>
    python e21_null_replicate_rescore.py score <out_root>
    python e21_null_replicate_rescore.py read  <out_root> <read.json>
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Mapping

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.analysis.e21_agentic_metric_baseline import (  # noqa: E402
    run_scoring,
    sha256_file,
)

#: One job per metric.  ``asr-wer-whisper`` is the replicate's own internal
#: anchor: this bundle must reproduce what ``finalize`` already sealed.
JOBS: tuple[tuple[str, str], ...] = (
    ("corpus-wer-anchor", "asr-wer-whisper"),
    ("conec-entity-wer", "conec-entity-wer-official"),
    ("numeric-value-accuracy", "numeric-value-accuracy-v1"),
    ("semantic-high-impact", "semantic-high-impact-error-rate-v1"),
)

_ARTIFACTS = ("outputs", "raw_trace", "trace_manifest", "scores", "session_receipt")


def build_bundle(
    attempt_dir: Path, run_id: str, out_root: Path, job_slug: str, scorer: str
) -> dict[str, object]:
    manifest_path = attempt_dir / f"{run_id}.run-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "COMPLETED":
        raise SystemExit(f"refusing to re-score a {manifest.get('status')!r} manifest")
    destination = out_root / f"rescore-{job_slug}"
    destination.mkdir(parents=True, exist_ok=True)

    copies: dict[str, dict[str, str]] = {}
    for key in _ARTIFACTS:
        entry = manifest.get(key)
        if not isinstance(entry, Mapping):
            continue
        source = Path(str(entry["path"]))
        target = destination / source.name
        if not target.is_file() or sha256_file(target) != entry["sha256"]:
            shutil.copyfile(source, target)
        recomputed = sha256_file(target)
        if recomputed != entry["sha256"]:
            raise RuntimeError(
                f"copy of {key} at {target} hashes {recomputed}, sealed manifest says "
                f"{entry['sha256']}"
            )
        manifest[key] = {**dict(entry), "path": str(target)}
        copies[key] = {
            "sealed_path": str(source),
            "copy_path": str(target),
            "sha256": recomputed,
        }
    manifest["scorers"] = [scorer]
    target_manifest = destination / f"{run_id}.run-manifest.json"
    target_manifest.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    return {
        "job_id": job_slug,
        "scorer": scorer,
        "manifest": str(target_manifest),
        "manifest_sha256": sha256_file(target_manifest),
        "artifacts": copies,
    }


def stage_build(attempt_dir: Path, run_id: str, out_root: Path) -> int:
    bundles = [
        build_bundle(attempt_dir, run_id, out_root, slug, scorer) for slug, scorer in JOBS
    ]
    (out_root / "bundles").mkdir(parents=True, exist_ok=True)
    (out_root / "bundles" / "rescore-bundles.json").write_text(
        json.dumps({"run_id": run_id, "attempt_dir": str(attempt_dir), "bundles": bundles},
                   indent=1) + "\n",
        encoding="utf-8", newline="\n",
    )
    (out_root / "bundles" / "jobs.jsonl").write_text(
        "".join(
            json.dumps({"job_id": b["job_id"], "manifest": b["manifest"]}) + "\n"
            for b in bundles
        ),
        encoding="utf-8", newline="\n",
    )
    for bundle in bundles:
        print(f"{bundle['job_id']:24s} {bundle['scorer']:36s} {bundle['manifest']}")
    return 0


def stage_score(out_root: Path) -> int:
    table = json.loads(
        (out_root / "bundles" / "rescore-bundles.json").read_text(encoding="utf-8")
    )
    output_dir = out_root / "scoring"
    if output_dir.exists() and any(output_dir.iterdir()):
        raise SystemExit(f"{output_dir} is not empty; core.scoring_batch refuses to overwrite")
    summary = run_scoring(table["bundles"], output_dir)
    (output_dir / "batch-summary.json").write_text(
        json.dumps(summary, indent=1, default=str) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps({key: summary[key] for key in ("succeeded", "failed", "job_count")}))
    return 0 if summary["failed"] == 0 else 1


def stage_read(out_root: Path, out_path: Path) -> int:
    """Collapse the four one-scorer score files into ONE score-read document of
    the shape ``build_e21_tail2s_verdict.call_rows_from_score_read`` consumes."""

    scores: dict[str, object] = {}
    provenance: dict[str, object] = {}
    for slug, scorer in JOBS:
        path = out_root / "scoring" / f"{slug}.score.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        if not document.get("verified"):
            raise SystemExit(f"{path} is not a verified score read; refusing to read it")
        block = document.get("scores", document)
        if scorer not in block:
            raise SystemExit(f"{path} carries no {scorer!r} block; keys {sorted(block)}")
        scores[scorer] = block[scorer]
        provenance[scorer] = {
            "job_id": slug,
            "score_file": str(path),
            "score_file_sha256": sha256_file(path),
            "verified": document.get("verified"),
        }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"schema": "saea-e21-null-replicate-score-read-v1",
                    "scores": scores, "jobs": provenance}, indent=1) + "\n",
        encoding="utf-8", newline="\n",
    )
    print(json.dumps({
        "out": str(out_path),
        "scorers": sorted(scores),
        "aggregates": {
            scorer: {k: v for k, v in (scores[scorer].get("aggregate") or {}).items()
                     if isinstance(v, (int, float))}
            for scorer in sorted(scores)
        },
    }, indent=1))
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    stage = argv[1]
    if stage == "build":
        return stage_build(Path(argv[2]), argv[3], Path(argv[4]))
    if stage == "score":
        return stage_score(Path(argv[2]))
    if stage == "read":
        return stage_read(Path(argv[2]), Path(argv[3]))
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
