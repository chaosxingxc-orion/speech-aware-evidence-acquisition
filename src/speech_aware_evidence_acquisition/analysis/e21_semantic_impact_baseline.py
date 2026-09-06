"""Zero-contact re-score of the sealed Earnings-21 full-44 direct baseline under
``semantic-high-impact-error-rate-v1``, now that its taxonomy has landed.

The 2026-09-06 agentic-metric baseline
(``analysis.e21_agentic_metric_baseline``) produced three of the four metrics
the owner's ruling names and left the fourth blank, because the scorer fails
closed until ``docs/taxonomies/semantic-high-impact/ACTIVE.json`` exists. E5
landed that file as a projection of the Earnings-22 scan's own content-impact
model (``analysis.semantic_impact_taxonomy``), so this module fills the blank
with one more job through exactly the same machinery: a RE-SCORING BUNDLE of
byte-identical copies of the sealed artifacts whose manifest differs from the
sealed one only in artifact paths and the ``scorers`` list, scored through
``core.scoring_batch`` as one complete verified manifest in one process.

Nothing here re-measures the run; it re-reads it. ``core.bundle.verify_bundle``
re-derives split identity, protocol hash and the outputs<->split<->trace binding
from the copied bytes and gets the sealed values, and the sealed attempt
directory is never written to.

WHAT THE NUMBER IS, AND IS NOT
------------------------------
Under the landed taxonomy the HIGH tier is E22's NEGATION trigger alone -- the
digit and call-entity triggers are not expressible as exact-word keys and were
deliberately left out rather than approximated (see
``analysis.semantic_impact_taxonomy`` and the taxonomy receipt). So this job
reports a **negation-critical error rate**, a strict lower bound on E22's own
content-impact HIGH rate, beside a NONE/LOW/HIGH decomposition of the whole
reference-word error mass. On Earnings-21 the two missing triggers are already
carried, on better anchors, by ``numeric-value-accuracy-v1`` and
``conec-entity-wer-official``, both of which the 2026-09-06 baseline reports.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Sequence

from ..e0.artifacts import REPO_ROOT
from .e21_agentic_metric_baseline import (
    EVALUATION_CALLS,
    build_rescore_bundle,
    rescore_root,
    run_scoring,
    sha256_file,
)

RUN_ID = "SAEA-E21-MF-SEMANTIC-IMPACT-BASELINE-V1"
SCORER = "semantic-high-impact-error-rate-v1"
JOB_SLUG = "semantic-high-impact"

CHECK_DIR = (
    REPO_ROOT
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-06-e21-semantic-impact-baseline"
)

#: The three metrics the 2026-09-06 baseline already landed, for the receipt's
#: own cross-reference. Pooled corpus figures on all 44, from that note.
COMPANION_METRICS = {
    "asr-wer-whisper": {"all_44_corpus_wer_percent": 8.200},
    "conec-entity-wer-official": {"all_44_person_entity_wer_percent": 22.5},
    "numeric-value-accuracy-v1": {"all_44_accuracy_percent": 90.73},
}


def build() -> dict[str, object]:
    return build_rescore_bundle(JOB_SLUG, SCORER, run_id=RUN_ID)


def score(bundles: Sequence[Mapping[str, object]], output_dir: Path) -> dict[str, object]:
    return run_scoring(bundles, output_dir)


def load_scores(result_path: Path) -> dict[str, object]:
    document = json.loads(Path(result_path).read_text(encoding="utf-8"))
    if not document.get("verified"):
        raise RuntimeError(f"{result_path} is not a verified score read")
    return document["scores"][SCORER]


def _pool(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Sum the counts, then divide once -- the same discipline
    ``reproduction.semantic_impact.merge_semantic_counts`` applies, restated
    here because a roster is a SUBSET of the samples that function pooled."""

    reference_words = sum(int(row["reference_words"]) for row in rows)
    high = sum(int(row["high_impact_reference_words"]) for row in rows)
    unclassified = sum(int(row["unclassified_reference_words"]) for row in rows)
    insertions = sum(int(row["high_impact_insertions"]) for row in rows)
    by_level: dict[str, int] = {}
    insertions_by_level: dict[str, int] = {}
    by_rule: dict[str, int] = {}
    for row in rows:
        for source, target in (
            (row["reference_words_by_level"], by_level),
            (row["insertions_by_level"], insertions_by_level),
            (row["reference_words_by_rule"], by_rule),
        ):
            assert isinstance(source, Mapping)
            for key, value in source.items():
                target[key] = target.get(key, 0) + int(value)
    return {
        "calls": len(rows),
        "reference_words": reference_words,
        "high_impact_reference_words": high,
        "high_impact_error_rate_percent": (
            100.0 * high / reference_words if reference_words else 0.0
        ),
        "unclassified_reference_words": unclassified,
        "high_impact_insertions": insertions,
        "reference_words_by_level": dict(sorted(by_level.items())),
        "reference_words_by_level_percent": {
            level: (100.0 * count / reference_words if reference_words else 0.0)
            for level, count in sorted(by_level.items())
        },
        "insertions_by_level": dict(sorted(insertions_by_level.items())),
        "top_rules": dict(
            sorted(by_rule.items(), key=lambda item: (-item[1], item[0]))[:20]
        ),
    }


def split_rosters(rows: Sequence[Mapping[str, object]]) -> dict[str, list[Mapping[str, object]]]:
    evaluation = set(EVALUATION_CALLS)
    return {
        "all_44": list(rows),
        "construction_34": [row for row in rows if str(row["sample_id"]) not in evaluation],
        "evaluation_10": [row for row in rows if str(row["sample_id"]) in evaluation],
    }


def build_summary(scores: Mapping[str, object], result_path: Path) -> dict[str, object]:
    rows = list(scores["per_sample"])  # type: ignore[index]
    aggregate = dict(scores["aggregate"])  # type: ignore[index]
    rosters = split_rosters(rows)
    pooled = {name: _pool(subset) for name, subset in rosters.items()}
    # The pooled all-44 figure must reproduce the scorer's own aggregate, which
    # is a different code path over the same per-sample rows.
    if pooled["all_44"]["reference_words"] != aggregate["reference_words"]:
        raise RuntimeError(
            "pooled reference words disagree with the scorer's own aggregate: "
            f"{pooled['all_44']['reference_words']} vs {aggregate['reference_words']}"
        )
    return {
        "schema": "saea-e21-semantic-impact-baseline-v1",
        "run_id": RUN_ID,
        "scorer": SCORER,
        "taxonomy_id": aggregate["taxonomy_id"],
        "normalizer": aggregate["normalizer"],
        "high_tier_is": (
            "the E22 NEGATION trigger alone -- the digit and call-entity triggers are not "
            "expressible as exact-word taxonomy keys and were left out rather than "
            "approximated, so this rate is a strict LOWER BOUND on E22's content-impact "
            "HIGH rate and must be quoted as the negation-critical rate"
        ),
        "companion_metrics": COMPANION_METRICS,
        "result_file": str(result_path),
        "result_sha256": sha256_file(result_path),
        "aggregate": aggregate,
        "semantic_high_impact_error_rate": pooled,
        "per_call": [
            {
                "sample_id": str(row["sample_id"]),
                "roster": (
                    "evaluation" if str(row["sample_id"]) in set(EVALUATION_CALLS) else "construction"
                ),
                "reference_words": int(row["reference_words"]),
                "high_impact_reference_words": int(row["high_impact_reference_words"]),
                "high_impact_error_rate_percent": 100.0 * float(row["high_impact_error_rate"]),
                "unclassified_reference_words": int(row["unclassified_reference_words"]),
                "high_impact_insertions": int(row["high_impact_insertions"]),
                "reference_words_by_level": dict(row["reference_words_by_level"]),  # type: ignore[arg-type]
            }
            for row in sorted(rows, key=lambda item: str(item["sample_id"]))
        ],
    }


def per_call_table(summary: Mapping[str, object]) -> str:
    lines = [
        "| call | roster | ref words | HIGH (negation-critical) % | NONE % | LOW % | "
        "unclassified | HIGH insertions |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary["per_call"]:  # type: ignore[union-attr]
        levels = row["reference_words_by_level"]
        total = int(row["reference_words"]) or 1
        lines.append(
            f"| {row['sample_id']} | {row['roster'][:6]} | {row['reference_words']:,} | "
            f"{row['high_impact_error_rate_percent']:.4f} | "
            f"{100.0 * int(levels.get('NONE', 0)) / total:.2f} | "
            f"{100.0 * int(levels.get('LOW', 0)) / total:.2f} | "
            f"{row['unclassified_reference_words']} | {row['high_impact_insertions']} |"
        )
    return "\n".join(lines) + "\n"


def write_json(path: Path, document: Mapping[str, object]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    return path


def write_manifest(directory: Path) -> Path:
    lines = []
    for path in sorted(Path(directory).rglob("*")):
        if not path.is_file() or path.name == "MANIFEST.sha256":
            continue
        lines.append(f"{sha256_file(path)}  {path.relative_to(directory).as_posix()}")
    target = Path(directory) / "MANIFEST.sha256"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return target


def scratch_root() -> Path:
    return rescore_root(RUN_ID)
