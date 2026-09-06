"""Zero-contact re-score of the sealed Earnings-21 full-44 direct baseline
under the 2026-09-06 agentic metrics.

Owner ruling 2026-09-06: WER is not a reasonable speech-agentic task. Corpus
WER stays the alignment anchor against the published Earnings-21 rows; the
paper-facing line for Earnings MECHANISM cells becomes entity-level metrics
with published numbers plus a semantic high-impact error rate. This module
produces the comparator every Earnings mechanism cell pairs against from now
on, from bytes a separately registered flight already wrote. No model, GPU,
tool, embedding, network or audio contact: gold enters only through the
registered scorers, exactly as it does when a flight finalizes.

HOW THE SEALED RUN IS RE-SCORED WITHOUT TOUCHING IT
---------------------------------------------------
``core.scorers.score_bundle`` runs a manifest's OWN ``scorers`` list, and the
sealed manifest declares ``["asr-wer-whisper", "asr-wer", "entity-wer",
"cost"]``. Resolving new scorer objects against the sealed ``outputs.jsonl``
directly -- what the 2026-09-04 alignment audit did -- is the very defect the
full-44 preregistration named ("the number was produced out of band"), because
it bypasses ``core.bundle.verify_bundle`` entirely.

So instead each metric gets a RE-SCORING BUNDLE: a new directory under
``$SPEECHRL_DATA_DIR/runs/<this run id>/`` holding BYTE-IDENTICAL copies of the
sealed outputs, raw trace, trace manifest, scores artifact and session receipt,
plus a manifest that differs from the sealed one in exactly two respects --
the artifact ``path`` fields point at the copies, and ``scorers`` names the one
metric. Everything else (``protocol_hash``, ``config``, ``split``, ``plan``,
``cost``, ``arm``, ``study_commit``, ``status``) is carried over unchanged, so
``verify_bundle`` re-derives every hash and every cross-check from the copied
bytes and gets the sealed values -- split identity, protocol hash,
outputs<->split<->trace binding, the lot. The sealed attempt directory is never
written to and never modified; ``docs/checks/.../2026-09-06-...`` records each
copy's sha256 beside the sealed one so the identity is auditable after the fact.

Scoring then runs through ``core.scoring_batch`` -- one complete manifest per
process, never sharded, never averaged across shards -- which is the verified
path the owner's standard-scoring rule requires.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Mapping, Sequence

from ..core.scoring_batch import ScoreJob, run_score_batch
from ..data.lock import data_root
from ..e0.artifacts import REPO_ROOT

RUN_ID = "SAEA-E21-MF-AGENTIC-METRIC-BASELINE-V1"
SEALED_RUN_ID = "SAEA-E21-FULL44-DIRECT-BASELINE-V2"
SEALED_ATTEMPT = "attempt-20260904T233816Z-bcd338"

SEALED_CHECK_DIR = (
    REPO_ROOT
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-e21-full44-direct-baseline-v1"
)
CHECK_DIR = (
    REPO_ROOT
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-06-e21-agentic-metric-baseline"
)

#: One job per metric. The corpus-WER job is the identity anchor: it must
#: reproduce the sealed 8.200 corpus figure and all 44 sealed per-call values.
JOBS: tuple[tuple[str, str], ...] = (
    ("corpus-wer-anchor", "asr-wer-whisper"),
    ("conec-entity-wer", "conec-entity-wer-official"),
    ("numeric-value-accuracy", "numeric-value-accuracy-v1"),
)

#: The E5 split. The ten calls of the frozen ``r4-e21-sub10`` subset are this
#: carrier's EVALUATION roster (the 2026-08-14/15 N10 arms and every read since
#: are on them); the other 34 are the kb-construction half
#: (``SAEA-BENCH-kb34-floor``, 2026-08-14). Reported separately so a mechanism
#: cell can never quote a construction-contaminated number as an evaluation one.
EVALUATION_CALLS = (
    "4330115",
    "4365024",
    "4365948",
    "4366429",
    "4366522",
    "4384964",
    "4385072",
    "4387383",
    "4389907",
    "4397829",
)

#: ConEC Table 2 (LREC-COLING 2024, aclanthology.org/2024.lrec-main.328),
#: entity WER %, the eight non-numeric classes the paper publishes. Row 1 is
#: the unbiased 71.5M zipformer (the biasing floor), row 8 is Whisper large
#: without biasing (the only row comparable in kind to a frozen general model),
#: row 5 is the post-hoc context-supply oracle ceiling. Sentence-segmented,
#: fstalign-scored, against ConEC's corrected references -- see
#: docs/readiness/2026-09-06-earnings-agentic-metric-literature.md section 4.3
#: for the four differences any comparison must carry.
CONEC_TABLE2 = {
    "PERSON": {"row1_no_biasing": 45.9, "row8_whisper_large": 28.9, "row5_oracle": 13.0},
    "ORG": {"row1_no_biasing": 29.5, "row8_whisper_large": 19.6, "row5_oracle": 17.7},
    "GPE": {"row1_no_biasing": 18.8, "row8_whisper_large": 17.0, "row5_oracle": 12.9},
    "LOC": {"row1_no_biasing": 5.85, "row8_whisper_large": 5.85, "row5_oracle": 5.46},
    "PRODUCT": {"row1_no_biasing": 24.2, "row8_whisper_large": 18.7, "row5_oracle": 19.2},
    "EVENT": {"row1_no_biasing": 43.1, "row8_whisper_large": 2.78, "row5_oracle": 35.6},
    "NORP": {"row1_no_biasing": 9.55, "row8_whisper_large": 8.54, "row5_oracle": 5.53},
    "FAC": {"row1_no_biasing": 28.7, "row8_whisper_large": 21.6, "row5_oracle": 16.6},
}

CONEC_OVERALL = {"row1_no_biasing": 10.41, "row8_whisper_large": 7.98, "row5_oracle": 9.69}

_ARTIFACTS = ("outputs", "raw_trace", "trace_manifest", "scores", "session_receipt")


def sealed_attempt_dir() -> Path:
    return data_root() / "runs" / SEALED_RUN_ID / SEALED_ATTEMPT


def rescore_root(run_id: str = RUN_ID) -> Path:
    """This row's own scratch root under the data root. ``run_id`` is a
    parameter, not a constant, because a LATER model-free re-score of the same
    sealed run needs its own directory: ``core.scoring_batch`` refuses a
    non-empty output dir, and a second row sharing this one's root could not
    run at all (E5's ``analysis.e21_semantic_impact_baseline``, which fills the
    fourth metric this row left blank)."""

    return data_root() / "runs" / run_id


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_rescore_bundle(
    job_slug: str, scorer: str, *, run_id: str = RUN_ID
) -> dict[str, object]:
    """Copy the sealed artifacts into this job's own directory and write a
    manifest that differs only in artifact paths and the scorer list."""

    sealed_dir = sealed_attempt_dir()
    manifest_path = sealed_dir / f"{SEALED_RUN_ID}.run-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    destination = rescore_root(run_id) / f"rescore-{job_slug}"
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
    target_manifest = destination / f"{SEALED_RUN_ID}.run-manifest.json"
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


def build_all_bundles() -> list[dict[str, object]]:
    return [build_rescore_bundle(slug, scorer) for slug, scorer in JOBS]


def run_scoring(bundles: Sequence[Mapping[str, object]], output_dir: Path) -> dict[str, object]:
    """One complete verified manifest per process, one worker: each job holds a
    full |ref| x |hyp| alignment matrix for a 14k-word call, so the bound here
    is memory, not cores."""

    jobs = [
        ScoreJob(job_id=str(bundle["job_id"]), manifest=Path(str(bundle["manifest"])))
        for bundle in bundles
    ]
    return run_score_batch(
        jobs,
        output_dir=Path(output_dir),
        max_workers=1,
        operation="score",
        include_per_sample=True,
    )


def _sealed_whisper_read() -> dict[str, object]:
    document = json.loads(
        (SEALED_CHECK_DIR / "scoring" / "verified-score-read.json").read_text(encoding="utf-8")
    )
    return document["scores"]["asr-wer-whisper"]


def sealed_whisper_corpus() -> dict[str, object]:
    """The sealed ``asr-wer-whisper`` corpus aggregate (the published 8.200)."""

    return dict(_sealed_whisper_read()["aggregate"])


def sealed_whisper_per_call() -> dict[str, dict[str, float]]:
    """The sealed ``asr-wer-whisper`` per-call rows, for the identity anchor."""

    document = {"scores": {"asr-wer-whisper": _sealed_whisper_read()}}
    return {
        str(row["sample_id"]): {
            "wer": float(row["wer"]),
            "substitutions": int(row["substitutions"]),
            "deletions": int(row["deletions"]),
            "insertions": int(row["insertions"]),
        }
        for row in document["scores"]["asr-wer-whisper"]["per_sample"]
    }
