"""Read side of the 2026-09-06 Earnings-21 agentic-metric baseline: turn the
three verified score jobs into the comparator table, the E5 split, and the
identity anchor. Pure functions over already-written score JSON; no contact of
any kind. See ``analysis.e21_agentic_metric_baseline`` for how the jobs are
built and run."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Mapping, Sequence

from ..reproduction.conec_entity_scoring import (
    NON_ENTITY_BUCKET,
    OVERALL_BUCKET,
    UNLABELLED_BUCKET,
    merge_buckets,
)
from ..reproduction.numeric_value_accuracy import merge_numeric_counts
from .e21_agentic_metric_baseline import (
    CHECK_DIR,
    CONEC_OVERALL,
    CONEC_TABLE2,
    EVALUATION_CALLS,
    JOBS,
    sealed_whisper_corpus,
    sealed_whisper_per_call,
    sha256_file,
)

CONEC_CLASSES = tuple(CONEC_TABLE2)


def load_scores(result_path: Path, scorer: str) -> dict[str, object]:
    document = json.loads(Path(result_path).read_text(encoding="utf-8"))
    if not document.get("verified"):
        raise RuntimeError(f"{result_path} is not a verified score read")
    return document["scores"][scorer]


def _corpus_wer(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    substitutions = sum(int(row["substitutions"]) for row in rows)
    deletions = sum(int(row["deletions"]) for row in rows)
    insertions = sum(int(row["insertions"]) for row in rows)
    reference_words = sum(
        int(row["hits"]) + int(row["substitutions"]) + int(row["deletions"]) for row in rows
    )
    errors = substitutions + deletions + insertions
    return {
        "calls": len(rows),
        "substitutions": substitutions,
        "deletions": deletions,
        "insertions": insertions,
        "reference_words": reference_words,
        "corpus_wer_percent": 100.0 * errors / reference_words if reference_words else 0.0,
    }


def identity_anchor(whisper_rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """The re-scored ``asr-wer-whisper`` job must reproduce the sealed
    2026-09-04 numbers to the digit, on every call. Anything else means the
    re-scoring bundle is not the sealed run."""

    sealed = sealed_whisper_per_call()
    mismatches = []
    for row in whisper_rows:
        sample_id = str(row["sample_id"])
        expected = sealed.get(sample_id)
        if expected is None:
            mismatches.append({"sample_id": sample_id, "reason": "not in the sealed read"})
            continue
        for key in ("wer", "substitutions", "deletions", "insertions"):
            if row[key] != expected[key]:
                mismatches.append(
                    {
                        "sample_id": sample_id,
                        "field": key,
                        "sealed": expected[key],
                        "rescored": row[key],
                    }
                )
    corpus = _corpus_wer(whisper_rows)
    sealed_corpus = sealed_whisper_corpus()
    for key in ("substitutions", "deletions", "insertions", "reference_words"):
        if corpus[key] != sealed_corpus[key]:
            mismatches.append(
                {"field": f"corpus.{key}", "sealed": sealed_corpus[key], "rescored": corpus[key]}
            )
    return {
        "sealed_corpus_wer_percent": 100.0 * float(sealed_corpus["corpus_wer"]),
        "rescored_corpus_wer_percent": corpus["corpus_wer_percent"],
        "calls_compared": len(whisper_rows),
        "per_call_mismatches": mismatches,
        "identity_holds": not mismatches,
        **corpus,
    }


def _subset(rows: Sequence[Mapping[str, object]], ids: Sequence[str]) -> list[Mapping[str, object]]:
    wanted = set(ids)
    return [row for row in rows if str(row["sample_id"]) in wanted]


def split_rosters(rows: Sequence[Mapping[str, object]]) -> dict[str, list[Mapping[str, object]]]:
    evaluation = _subset(rows, EVALUATION_CALLS)
    construction = [
        row for row in rows if str(row["sample_id"]) not in set(EVALUATION_CALLS)
    ]
    return {"all_44": list(rows), "evaluation_10": evaluation, "construction_34": construction}


def conec_entity_table(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Pool the per-call bucket counts over a roster and put ConEC's published
    columns beside the eight classes it publishes."""

    merged = merge_buckets([row["by_entity_type"] for row in rows])
    published = {}
    for entity_type in CONEC_CLASSES:
        ours = merged.get(entity_type)
        published[entity_type] = {
            "ours_entity_wer_percent": (100.0 * ours["wer"]) if ours else None,
            "ours_reference_words": (ours["reference_words"] if ours else 0),
            "ours_substitutions": (ours["substitutions"] if ours else 0),
            "ours_deletions": (ours["deletions"] if ours else 0),
            **CONEC_TABLE2[entity_type],
        }
    overall = merged[OVERALL_BUCKET]
    return {
        "calls": len(rows),
        "overall_wer_percent": 100.0 * overall["wer"],
        "overall_reference_words": overall["reference_words"],
        "non_entity_wer_percent": 100.0 * merged[NON_ENTITY_BUCKET]["wer"],
        "non_entity_reference_words": merged[NON_ENTITY_BUCKET]["reference_words"],
        "unlabelled_reference_words": merged[UNLABELLED_BUCKET]["reference_words"],
        "conec_published_overall": dict(CONEC_OVERALL),
        "conec_eight_classes": published,
        "all_classes": {
            name: {
                "entity_wer_percent": 100.0 * values["wer"],
                "reference_words": values["reference_words"],
                "substitutions": values["substitutions"],
                "deletions": values["deletions"],
            }
            for name, values in sorted(merged.items())
        },
    }


def numeric_table(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    merged = merge_numeric_counts(rows)
    return {
        "calls": merged["samples"],
        "accuracy_percent": 100.0 * float(merged["accuracy"]),
        "expected_numeric_words": merged["expected_numeric_words"],
        "matched_numeric_words": merged["matched_numeric_words"],
        "spurious_numeric_words": merged["spurious_numeric_words"],
        "by_kind": {
            kind: {
                "accuracy_percent": 100.0 * float(values["accuracy"]),
                "expected": values["expected"],
                "matched": values["matched"],
                "hypothesis": values["hypothesis"],
            }
            for kind, values in merged["by_kind"].items()
        },
    }


def build_summary(
    whisper_rows: Sequence[Mapping[str, object]],
    conec_rows: Sequence[Mapping[str, object]],
    numeric_rows: Sequence[Mapping[str, object]],
    conec_aggregate: Mapping[str, object],
) -> dict[str, object]:
    whisper_split = split_rosters(whisper_rows)
    conec_split = split_rosters(conec_rows)
    numeric_split = split_rosters(numeric_rows)
    return {
        "schema": "saea-e21-agentic-metric-baseline-v1",
        "identity_anchor": identity_anchor(whisper_rows),
        "corpus_wer": {name: _corpus_wer(rows) for name, rows in whisper_split.items()},
        "conec_entity_wer": {
            name: conec_entity_table(rows) for name, rows in conec_split.items()
        },
        "numeric_value_accuracy": {
            name: numeric_table(rows) for name, rows in numeric_split.items()
        },
        "conec_scorer_provenance": {
            key: conec_aggregate[key]
            for key in (
                "scorer_version",
                "normalizer",
                "implementation",
                "official_tool_run",
                "official_tool",
                "definition_source",
                "paper_source",
                "insertions_attributed_to_entities",
            )
        },
        "semantic_high_impact_error_rate": {
            "status": "AWAITING TAXONOMY",
            "scorer": "semantic-high-impact-error-rate-v1",
            "blocked_on": "the Earnings-22 semantic scan (branch wt/e22) has not landed its taxonomy",
            "expected_at": "docs/taxonomies/semantic-high-impact/ACTIVE.json",
        },
    }


def per_call_table(
    whisper_rows: Sequence[Mapping[str, object]],
    conec_rows: Sequence[Mapping[str, object]],
    numeric_rows: Sequence[Mapping[str, object]],
) -> str:
    conec_by_id = {str(row["sample_id"]): row for row in conec_rows}
    numeric_by_id = {str(row["sample_id"]): row for row in numeric_rows}
    lines = [
        "| call | roster | corpus WER % | ConEC entity WER % (8 classes) | entity ref words | "
        "numeric accuracy % | numeric values | unlabelled ref words |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in sorted(whisper_rows, key=lambda item: str(item["sample_id"])):
        sample_id = str(row["sample_id"])
        roster = "eval" if sample_id in set(EVALUATION_CALLS) else "constr"
        conec = conec_by_id[sample_id]
        merged = merge_buckets([conec["by_entity_type"]])
        errors = sum(
            merged[name]["errors"] for name in CONEC_CLASSES if name in merged
        )
        words = sum(
            merged[name]["reference_words"] for name in CONEC_CLASSES if name in merged
        )
        numeric = numeric_by_id[sample_id]
        accuracy = 100.0 * float(numeric["accuracy"])
        lines.append(
            f"| {sample_id} | {roster} | {100.0 * float(row['wer']):.2f} | "
            f"{(100.0 * errors / words) if words else 0.0:.2f} | {words} | "
            f"{accuracy:.2f} | {numeric['expected_numeric_words']} | "
            f"{conec['unlabelled_reference_words']} |"
        )
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Receipt writing. Kept here rather than in the CLI so the script stays a thin
# entry point (this repository's <=150-line rule for scripts/).
# ---------------------------------------------------------------------------


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )


def _drop(rows: Sequence[Mapping[str, object]], fields: tuple[str, ...]) -> list[dict]:
    return [{key: value for key, value in row.items() if key not in fields} for row in rows]


def write_manifest_sha256(check_dir: Path) -> Path:
    """Every file under the receipt directory, hashed, sorted by relative path
    -- the same MANIFEST.sha256 convention the 2026-09-04 receipt uses."""

    manifest_path = Path(check_dir) / "MANIFEST.sha256"
    if manifest_path.exists():
        manifest_path.unlink()
    lines = []
    for path in sorted(Path(check_dir).rglob("*")):
        if path.is_file():
            lines.append(f"{sha256_file(path)}  {path.relative_to(check_dir).as_posix()}")
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return manifest_path


def write_receipts(
    scores: Mapping[str, Mapping[str, object]],
    scratch_scoring: Path,
    bundles_dir: Path,
) -> dict[str, object]:
    """Write the whole 2026-09-06 receipt directory and return the summary."""

    whisper = scores["asr-wer-whisper"]
    conec = scores["conec-entity-wer-official"]
    numeric = scores["numeric-value-accuracy-v1"]
    summary = build_summary(
        whisper["per_sample"], conec["per_sample"], numeric["per_sample"], conec["aggregate"]
    )
    summary["jobs"] = [
        {
            "job_id": slug,
            "scorer": scorer,
            "result_file": f"{slug}.score.json",
            "result_sha256": sha256_file(Path(scratch_scoring) / f"{slug}.score.json"),
        }
        for slug, scorer in JOBS
    ]
    receipt_scoring = CHECK_DIR / "scoring"
    receipt_scoring.mkdir(parents=True, exist_ok=True)
    for name, source_dir in (
        ("batch-summary.json", scratch_scoring),
        ("jobs.jsonl", bundles_dir),
        ("rescore-bundles.json", bundles_dir),
    ):
        shutil.copyfile(Path(source_dir) / name, receipt_scoring / name)
    write_json(
        receipt_scoring / "verified-score-read.json",
        {
            "_receipt_note": (
                "core.scoring_batch --include-per-sample verified reads of the three "
                "re-scoring manifests, one complete manifest per process, never sharded. "
                "Per-sample ref_hit_mask arrays are dropped for size (the same reduction the "
                "2026-09-04 receipt made); every count is retained verbatim, and the "
                "unreduced files' sha256s are in verdict/result-summary.json's jobs block."
            ),
            "scores": {
                "asr-wer-whisper": {
                    "aggregate": whisper["aggregate"],
                    "per_sample": _drop(whisper["per_sample"], ("ref_hit_mask",)),
                },
                "conec-entity-wer-official": conec,
                "numeric-value-accuracy-v1": numeric,
            },
        },
    )
    write_json(CHECK_DIR / "verdict" / "result-summary.json", summary)
    (CHECK_DIR / "verdict" / "per-call-table.md").write_text(
        per_call_table(whisper["per_sample"], conec["per_sample"], numeric["per_sample"]),
        encoding="utf-8",
        newline="\n",
    )
    return summary
