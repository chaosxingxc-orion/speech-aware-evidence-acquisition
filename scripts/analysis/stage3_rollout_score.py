#!/usr/bin/env python3
"""CLI (S3-3): score a grouped-Solver rollout's five raw samples on COPIES and
select the best/worst disagreement pair per row.

Model-free. The five raw Solver samples already exist in the sealed run's
``solver_group`` custody (I7g); this CLI renders each sample index's answer
across every row into one canonical outputs COPY (``analysis.
native_commit_replay.replay_row``'s / ``scripts.analysis.
slurp_verifier_measurement.render_answer``'s exact rendering, byte for byte),
scores each of the five copies ONCE through the registered official scorer
(never ``core.scoring_batch``, which scores a bundle-verified run directory
and every side here is a derived copy with no manifest and no bundle -- the
precedent is ``analysis.b8a_delivery_node_read`` /
``scripts.analysis.slurp_verifier_measurement.score_copy``), and picks the
best and worst sample per row by ``(slu_f1_f1, scenario_action_exact)`` with
a deterministic ascending-``sample_index`` tie-break. The delivered answer's
own official score is read from the run's SEALED ``<run_id>.scores.json``
(``sealed_per_sample``) -- never rescored -- which is why the contacts block
below reads ``scorer: <samples>`` and not ``<samples> + 1``.

No utterance text, gold label, transcript or model output is printed or
persisted anywhere by this CLI: ``per_row.json`` and ``pairs.json`` carry
ids, stratum names, sample indices, scores and hashes only. The rendered
outputs copies themselves DO carry the rendered JSON answer text (scenario /
action / entity type+filler), because the registered scorer needs it to
score against gold -- exactly as every other ``score_copy`` caller in this
repository writes; they are written under ``--analysis-root``, never under
the repository.

Stages (``--stage``): ``render`` (write the five per-sample-index outputs
copies), ``score`` (score each rendered copy once through ``--scorer-id``),
``pairs`` (build ``per_row.json`` and ``pairs.json`` from the scored sides
plus the sealed delivered scores and the roster's stratum), ``all`` (the
three in sequence). Every stage is idempotent: a copy or score file that
already exists on disk is read back, never rewritten.

Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src python \\
      scripts/analysis/stage3_rollout_score.py \\
      --run SAEA-SLURP-STAGE3-ROLLOUT-R01-V1 \\
      --attempt attempt-slurp-native-stage3-rollout-r01-generation-v1 \\
      --roster docs/receipts/rosters/slurp-stage3-construction-r01.json \\
      --analysis-root "$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-ROLLOUT-R01-SCORE-V1" \\
      --scorer-id slurp-slu-official-projected-v3-train --stage all
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

SCHEMA = "saea-stage3-rollout-score-v1"
DEFAULT_SCORER_ID = "slurp-slu-official-projected-v3-train"
COUNT_FIELDS = (
    "slu_f1_word_tp", "slu_f1_word_fp", "slu_f1_word_fn",
    "slu_f1_char_tp", "slu_f1_char_fp", "slu_f1_char_fn",
    "slot_f1_exact_tp", "slot_f1_exact_fp", "slot_f1_exact_fn",
)
EMPTY_ANSWER = json.dumps(
    {"scenario": "", "action": "", "entities": []}, ensure_ascii=False, sort_keys=True
)


class Stage3ScoreError(RuntimeError):
    """A sealed input is missing or does not have the shape this CLI needs."""


# ---------------------------------------------------------------------------
# Small shared helpers (the ``slurp_verifier_measurement`` idiom, module docstring)
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(document: object) -> str:
    return hashlib.sha256(
        json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    return sha256_file(path)


def write_json(path: Path, payload: Mapping[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )
    return sha256_file(path)


def run_dir(root: Path, run_id: str, attempt_id: str) -> Path:
    directory = root / "runs" / run_id / attempt_id
    if not directory.is_dir():
        raise Stage3ScoreError(f"no sealed attempt directory at {directory}")
    return directory


def load_roster(repo_root: Path, relpath: str) -> tuple[dict[str, str], str, str]:
    """``{sample_id: stratum}`` plus the roster file's sha256 and (if present)
    ``split_identity_hash``. Generic on purpose (the ``slurp_verifier_
    measurement.load_roster`` idiom): a construction roster (``saea-roster-
    receipt-v1``) and an older evaluation-roster receipt (e.g. TRAIN Fold A)
    both carry ``items[].sample_id`` / ``items[].stratum``, and neither is
    re-verified here -- this CLI reads identity, not authorises a draw."""

    path = repo_root / relpath
    file_sha256 = sha256_file(path)
    document = json.loads(path.read_text(encoding="utf-8"))
    strata: dict[str, str] = {}
    for item in document["items"]:
        sample_id = str(item["sample_id"])
        stratum = item.get("stratum")
        if not isinstance(stratum, str) or not stratum:
            raise Stage3ScoreError(f"roster item {sample_id!r} carries no stratum")
        strata[sample_id] = stratum
    split_identity_hash = str(document.get("split_identity_hash") or "")
    return strata, file_sha256, split_identity_hash


def render_answer(payload: Mapping[str, Any] | None) -> str:
    """Render one parsed Solver answer to the canonical delivered payload,
    byte for byte the form ``analysis.native_commit_replay.replay_row`` /
    ``scripts.analysis.slurp_verifier_measurement.render_answer`` write."""

    if payload is None:
        return EMPTY_ANSWER
    body = {
        "scenario": payload.get("scenario", ""),
        "action": payload.get("action", ""),
        "entities": [
            {"type": entity["type"], "filler": entity["filler"]}
            for entity in payload.get("entities", [])
        ],
    }
    return json.dumps(body, ensure_ascii=False, sort_keys=True)


def sealed_per_sample(directory: Path, run_id: str, scorer_id: str) -> dict[str, dict[str, Any]]:
    """The arm's own sealed official per-row scores for the DELIVERED
    (committed) answer -- read, never recomputed (module docstring)."""

    path = directory / f"{run_id}.scores.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    if scorer_id not in document:
        raise Stage3ScoreError(
            f"{path} carries no sealed score for {scorer_id!r}; known: {sorted(document)}"
        )
    rows = document[scorer_id]["per_sample"]
    return {str(row["sample_id"]): row for row in rows}


def correctness_fields(row: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "scenario_action_exact": bool(float(row["scenario_action_exact"]) >= 1.0),
        "slu_f1_f1": float(row["slu_f1_f1"]),
    }
    for field in COUNT_FIELDS:
        if field in row:
            out[field] = row[field]
    return out


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------


def detect_samples(directory: Path, run_id: str) -> int:
    for row in iter_jsonl(directory / f"{run_id}.outputs.jsonl"):
        group = row.get("solver_group")
        if isinstance(group, Mapping) and isinstance(group.get("samples"), list):
            return len(group["samples"])
    raise Stage3ScoreError(f"{run_id}: no row carries a solver_group to size samples from")


def render(
    directory: Path, run_id: str, roster: Mapping[str, str], samples: int, out_dir: Path
) -> dict[str, Any]:
    samples_text: list[dict[str, str]] = [dict() for _ in range(samples)]
    rows_seen: set[str] = set()
    malformed_samples = 0
    rows_with_a_malformed_sample = 0
    for row in iter_jsonl(directory / f"{run_id}.outputs.jsonl"):
        sample_id = str(row["sample_id"])
        if sample_id not in roster:
            continue
        group = row.get("solver_group")
        if not isinstance(group, Mapping):
            raise Stage3ScoreError(f"row {sample_id} carries no solver_group custody")
        records = group["samples"]
        if len(records) != samples:
            raise Stage3ScoreError(
                f"row {sample_id} carries {len(records)} samples, expected {samples}"
            )
        row_malformed = 0
        for record in records:
            index = int(record["sample_index"])
            payload = record["parsed_answer"] if record["parse_status"] == "ok" else None
            if payload is None:
                row_malformed += 1
            samples_text[index][sample_id] = render_answer(payload)
        malformed_samples += row_malformed
        rows_with_a_malformed_sample += 1 if row_malformed else 0
        rows_seen.add(sample_id)

    missing = sorted(set(roster) - rows_seen)
    if missing:
        raise Stage3ScoreError(
            f"{len(missing)} roster row(s) absent from {run_id}.outputs.jsonl; first: {missing[0]}"
        )

    ids = sorted(rows_seen)
    manifest: dict[str, Any] = {
        "schema": SCHEMA, "stage": "render", "run_id": run_id, "samples": samples,
        "rows": len(ids), "malformed_samples": malformed_samples,
        "rows_with_a_malformed_sample": rows_with_a_malformed_sample,
        "copies": {},
    }
    for index in range(samples):
        path = out_dir / f"sample-{index}-outputs.jsonl"
        digest = write_jsonl(path, [{"sample_id": i, "text": samples_text[index][i]} for i in ids])
        manifest["copies"][f"sample_{index}"] = {"path": str(path), "sha256": digest, "rows": len(ids)}
    write_json(out_dir / "render-manifest.json", manifest)
    return manifest


# ---------------------------------------------------------------------------
# score
# ---------------------------------------------------------------------------


def score_copy(
    scorer_id: str, outputs_copy: Path, result_path: Path, lock: Mapping[str, object], root: Path
) -> tuple[dict[str, Any], float]:
    """One complete registered scoring over a COPY, cached by its result
    file (module docstring; the ``slurp_verifier_measurement.score_copy``
    idiom, unchanged)."""

    from speech_aware_evidence_acquisition.core.base import SCORERS  # noqa: PLC0415
    import speech_aware_evidence_acquisition.core.scorers  # noqa: PLC0415, F401

    if result_path.exists():
        return json.loads(result_path.read_text(encoding="utf-8"))[scorer_id], 0.0
    scorer = SCORERS.resolve(scorer_id)
    started = time.time()
    result = scorer(outputs_copy, lock, root)
    elapsed = time.time() - started
    aggregate = result["aggregate"]
    if not aggregate["identity_check"]["passed"]:
        raise Stage3ScoreError(f"{scorer_id} port/official identity check failed on {outputs_copy}")
    write_json(result_path, {scorer_id: result})
    return result, elapsed


def score(
    scorer_id: str, manifest: Mapping[str, Any], out_dir: Path, lock: Mapping[str, object], root: Path
) -> dict[str, Any]:
    scored: dict[str, Any] = {}
    for name, copy_entry in sorted(manifest["copies"].items()):
        path = Path(copy_entry["path"])
        measured = sha256_file(path)
        if measured != copy_entry["sha256"]:
            raise Stage3ScoreError(f"{path} drifted from its render manifest sha256")
        result, elapsed = score_copy(
            scorer_id, path, out_dir / f"{name}-{scorer_id}-scores.json", lock, root
        )
        scored[name] = {
            "outputs_sha256": measured,
            "official_slu_f1_pp": 100 * float(result["aggregate"]["official"]["slu_f1"]),
            "official_intent_pp": 100 * float(result["aggregate"]["official"]["intent_accuracy"]),
            "per_sample": {str(r["sample_id"]): correctness_fields(r) for r in result["per_sample"]},
            "scoring_seconds": elapsed,
        }
    write_json(
        out_dir / "score-summary.json",
        {
            "schema": SCHEMA, "stage": "score", "scorer_id": scorer_id,
            "sides": {k: {kk: vv for kk, vv in v.items() if kk != "per_sample"} for k, v in scored.items()},
        },
    )
    return scored


# ---------------------------------------------------------------------------
# pairs
# ---------------------------------------------------------------------------


def best_worst(samples_correct: Sequence[dict[str, Any]]) -> tuple[int, int]:
    """Best/worst sample index by ``(slu_f1_f1, scenario_action_exact)``,
    ties broken by ascending ``sample_index`` (module docstring)."""

    def key(entry: tuple[int, dict[str, Any]]) -> tuple[float, bool]:
        _, scores = entry
        return (scores["slu_f1_f1"], scores["scenario_action_exact"])

    indexed = list(enumerate(samples_correct))
    best_index, _ = max(indexed, key=lambda e: (key(e), -e[0]))
    worst_index, _ = min(indexed, key=lambda e: (key(e), e[0]))
    return best_index, worst_index


def pairs(
    run_id: str, attempt_id: str, scorer_id: str, roster: Mapping[str, str],
    roster_relpath: str, roster_sha256: str, roster_split_identity_hash: str,
    scored: Mapping[str, Any], delivered: Mapping[str, Mapping[str, Any]], samples: int,
    out_dir: Path, stage3_algorithm: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    ids = sorted(roster)
    rows: list[dict[str, Any]] = []
    for sample_id in ids:
        per_sample = [scored[f"sample_{index}"]["per_sample"][sample_id] for index in range(samples)]
        best_index, worst_index = best_worst(per_sample)
        best_f1 = per_sample[best_index]["slu_f1_f1"]
        worst_f1 = per_sample[worst_index]["slu_f1_f1"]
        delivered_scores = correctness_fields(delivered[sample_id]) if sample_id in delivered else None
        rows.append({
            "sample_id": sample_id,
            "stratum": roster[sample_id],
            "samples": [
                {"sample_index": index, **per_sample[index]} for index in range(samples)
            ],
            "best_index": best_index,
            "worst_index": worst_index,
            "best_slu_f1_f1": best_f1,
            "worst_slu_f1_f1": worst_f1,
            "disagreement": best_f1 - worst_f1,
            "group_mean_slu_f1_f1": sum(s["slu_f1_f1"] for s in per_sample) / samples,
            "delivered": delivered_scores,
        })

    disagreeing = [row for row in rows if row["disagreement"] > 0]
    strata = sorted({row["stratum"] for row in rows})
    coverage: dict[str, Any] = {}
    for stratum in strata:
        stratum_rows = [row for row in rows if row["stratum"] == stratum]
        stratum_disagreeing = [row for row in stratum_rows if row["disagreement"] > 0]
        coverage[stratum] = {
            "rows": len(stratum_rows),
            "disagreeing_rows": len(stratum_disagreeing),
            "disagreement_rate": len(stratum_disagreeing) / len(stratum_rows) if stratum_rows else None,
            "mean_disagreement": (
                sum(row["disagreement"] for row in stratum_rows) / len(stratum_rows)
                if stratum_rows else None
            ),
        }

    header = {
        "schema": SCHEMA, "stage": "pairs", "run_id": run_id, "attempt_id": attempt_id,
        "scorer_id": scorer_id, "samples": samples,
        "roster": {
            "relpath": roster_relpath, "sha256": roster_sha256,
            "split_identity_hash": roster_split_identity_hash, "rows": len(ids),
        },
        "contacts": {"model": 0, "tokenizer": 0, "encoder": 0, "asr": 0, "server": 0,
                     "network": 0, "scorer": samples},
    }
    # Owner decision 101: a Stage-3 read says which training-free RL it reads.
    if stage3_algorithm is not None:
        header["stage3_algorithm"] = dict(stage3_algorithm)
    per_row_payload = {**header, "rows": rows}
    pairs_payload = {
        **header,
        "count": len(disagreeing),
        "pairs": [
            {
                "sample_id": row["sample_id"], "stratum": row["stratum"],
                "best_index": row["best_index"], "worst_index": row["worst_index"],
                "disagreement": row["disagreement"],
            }
            for row in disagreeing
        ],
        "coverage_by_stratum": coverage,
    }
    write_json(out_dir / "per_row.json", per_row_payload)
    write_json(out_dir / "pairs.json", pairs_payload)
    return per_row_payload, pairs_payload


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="sealed run id")
    parser.add_argument("--attempt", required=True, help="sealed attempt id")
    parser.add_argument("--roster", required=True, help="roster receipt relpath (repo-root relative)")
    parser.add_argument("--analysis-root", required=True, help="output directory for this read")
    parser.add_argument("--scorer-id", default=DEFAULT_SCORER_ID, help="registered scorer id")
    parser.add_argument("--samples", type=int, default=None, help="override sample count (auto-detected)")
    parser.add_argument(
        "--stage", choices=("render", "score", "pairs", "all"), default="all"
    )
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--data-root", default=None, help="defaults to data.lock.data_root()")
    parser.add_argument(
        "--stage3-algorithm", default=None,
        help=(
            "registered Stage-3 algorithm id (core.base.STAGE3_ALGORITHMS); the default "
            "resolves the label from the experiment fragment that owns --run"
        ),
    )
    args = parser.parse_args(argv)

    from speech_aware_evidence_acquisition.core.stage3_algorithms import (  # noqa: PLC0415
        summary_for_run_id,
    )
    from speech_aware_evidence_acquisition.data.lock import (  # noqa: PLC0415
        data_root as resolve_data_root, load_lock, umbrella_lock_path,
    )

    repo_root = Path(args.repo_root)
    stage3_algorithm = summary_for_run_id(repo_root, args.run, args.stage3_algorithm)
    root = Path(args.data_root) if args.data_root else resolve_data_root()
    lock = load_lock(umbrella_lock_path(repo_root))
    directory = run_dir(root, args.run, args.attempt)
    roster, roster_sha256, roster_split_identity_hash = load_roster(repo_root, args.roster)
    out_dir = Path(args.analysis_root)
    out_dir.mkdir(parents=True, exist_ok=True)

    samples = args.samples or detect_samples(directory, args.run)
    needs_pairs = args.stage in ("pairs", "all")

    manifest = None
    if args.stage in ("render", "all"):
        manifest = render(directory, args.run, roster, samples, out_dir)
        print(json.dumps({"stage": "render", "rows": manifest["rows"],
                           "malformed_samples": manifest["malformed_samples"]}, indent=2))
    else:
        manifest_path = out_dir / "render-manifest.json"
        if not manifest_path.is_file():
            raise Stage3ScoreError(f"--stage {args.stage} requires a prior render (no {manifest_path})")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    scored = None
    if args.stage in ("score", "all"):
        scored = score(args.scorer_id, manifest, out_dir, lock, root)
        print(json.dumps(
            {"stage": "score", "sides": {k: v["official_slu_f1_pp"] for k, v in scored.items()}},
            indent=2,
        ))
    elif args.stage == "pairs":
        scored = {}
        for name in manifest["copies"]:
            result_path = out_dir / f"{name}-{args.scorer_id}-scores.json"
            if not result_path.is_file():
                raise Stage3ScoreError(f"--stage {args.stage} requires a prior score (no {result_path})")
            result = json.loads(result_path.read_text(encoding="utf-8"))[args.scorer_id]
            scored[name] = {
                "outputs_sha256": manifest["copies"][name]["sha256"],
                "official_slu_f1_pp": 100 * float(result["aggregate"]["official"]["slu_f1"]),
                "official_intent_pp": 100 * float(result["aggregate"]["official"]["intent_accuracy"]),
                "per_sample": {str(r["sample_id"]): correctness_fields(r) for r in result["per_sample"]},
                "scoring_seconds": 0.0,
            }

    if needs_pairs:
        try:
            delivered = sealed_per_sample(directory, args.run, args.scorer_id)
        except Stage3ScoreError as error:
            # The delivered score is auxiliary (module docstring): a sealed
            # run scored online under a DIFFERENT scorer id (e.g. a
            # grouped-solver precedent flown before the v3-projection
            # convention existed) still yields a complete best/worst read
            # from the five samples alone.
            print(f"[pairs] no sealed delivered score for {args.scorer_id!r}: {error}")
            delivered = {}
        _, pairs_payload = pairs(
            args.run, args.attempt, args.scorer_id, roster, args.roster, roster_sha256,
            roster_split_identity_hash, scored, delivered, samples, out_dir,
            stage3_algorithm,
        )
        print(json.dumps(
            {
                "stage": "pairs",
                "pair_count": pairs_payload["count"],
                "stage3_algorithm": pairs_payload.get("stage3_algorithm"),
                "coverage_by_stratum": pairs_payload["coverage_by_stratum"],
            },
            indent=2, sort_keys=True,
        ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
