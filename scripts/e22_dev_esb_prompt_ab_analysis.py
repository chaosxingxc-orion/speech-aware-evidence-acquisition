#!/usr/bin/env python3
"""Paired reader for the Earnings-22 DEV ESB prompt A/B experiment.

Zero model contact, strictly post-hoc. Reads only artifacts the two flights
already sealed: each arm's finalize ``<run_id>.scores.json`` (per-sample rows
for both ESB scorers), the ``score-batch/*.score.json`` that
``core.scoring_batch`` wrote as one whole-manifest verified job per arm, the run
manifests, the sealed ``<run_id>.outputs.jsonl``, the flight receipts, the
committed roster receipt, and -- for the error-shape diagnostics only -- the
hash-pinned derived reference layer.

Reuse, not reimplementation:

* the per-arm corpus arithmetic and the whole error-shape decomposition come
  from ``scripts/build_e22_esb_verdict.py`` (``_corpus`` / ``_decompose``),
  loaded by path the same way this repository's own tests load a script module.
  Those are the transforms the 2026-09-04 test verdict established, unchanged;
* the paired contrast comes from ``analysis.paired.paired_contrast``, the one
  place in this repository that computes delta / saves / harms / ties / an exact
  sign test / a stratified bootstrap CI.

**The decomposition transforms are diagnostics, never a second number.** Each
arm's verdict figure is its sealed ``asr-wer-esb-whisper`` corpus WER and
nothing else. Two transforms are ORACLE transforms -- they use the reference's
own length -- so they bound a component from above and are not achievable
results. They are labelled as such in the output and must be reported that way.

Metric convention, stated once and carried everywhere: ``analysis.paired``
defines ``delta = right - left`` and counts a "save" where ``right > left``,
i.e. it assumes HIGHER IS BETTER. WER is the opposite, so the per-utterance
metric passed in is **negated** WER: ``delta`` is then ``A_wer - B_wer``, which
is POSITIVE when arm B is better, and ``saves`` counts utterances arm B
improves. The raw ``B - A`` WER delta is reported beside it.

2026-09-05 generalization (the shape-C flight). The reader takes N arms and N
paired contrasts instead of exactly two arms and one contrast:
--arm NAME=run_id,run_dir,receipt (repeatable) and --contrast RIGHT-LEFT
(repeatable, RIGHT minus LEFT). The legacy --run-dir-a/-b flags still work
and still default to the single B-A contrast, so the invocation that
produced the sealed A/B verdict reproduces it unchanged; the document keeps
paired_contrast_b_minus_a and corpus_level_delta as aliases whenever
that contrast is among the ones requested.

Usage::

    python scripts/e22_dev_esb_prompt_ab_analysis.py \
        --run-dir-a <...> --receipt-a <...> \
        --run-dir-b <...> --receipt-b <...> --write

    python scripts/e22_dev_esb_prompt_ab_analysis.py \
        --arm A=<run>,<dir>,<receipt> --arm B=... --arm C=... \
        --contrast C-A --contrast C-B --primary-contrast C-A --write
"""

from __future__ import annotations
import os

import argparse
import hashlib
import importlib.util
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO = Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
)
CHECK = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-05-e22-dev-esb-prompt-ab-v1"
)
ROSTER = CHECK / "roster" / "flight-roster-receipt.json"

RUN_A = "SAEA-E22-DEV-ESB-PROMPT-A-V1"
RUN_B = "SAEA-E22-DEV-ESB-PROMPT-B-V1"
RUN_C = "SAEA-E22-DEV-ESB-SHAPE-C-V1"

SEED = 20260903
N_REPLICATES = 10_000
CI_LEVEL = 0.90

# Orientation only. No published number covers these ten dev calls.
PAPER_WER = 9.79
CROSS_READ_WER = 12.3
BAND = 3.0
SEALED_TEST_CORPUS_WER = 15.937  # SAEA-E22-ESB-SHORTFORM-ALIGNMENT-V1, six ESB TEST calls


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _verdict_module():
    """``scripts/build_e22_esb_verdict.py``, loaded by path.

    The repository's own tests load script modules this way; ``scripts`` is not
    an importable package here (and a third-party ``scripts`` package in the
    shared venv shadows it), so a path load is the reliable form.
    """

    spec = importlib.util.spec_from_file_location(
        "_e22_esb_verdict", REPO / "scripts" / "build_e22_esb_verdict.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _paired_module():
    import sys

    if str(REPO / "src") not in sys.path:
        sys.path.insert(0, str(REPO / "src"))
    from speech_aware_evidence_acquisition.analysis import paired  # noqa: PLC0415

    return paired


def _outputs(run_dir: Path, run_id: str) -> dict[str, str]:
    rows: dict[str, str] = {}
    text = (run_dir / f"{run_id}.outputs.jsonl").read_text(encoding="utf-8")
    for line in text.split("\n"):
        if not line.strip():
            continue
        row = json.loads(line)
        rows[str(row["sample_id"])] = str(row["text"])
    return rows


def _instruction_of(manifest: Mapping[str, Any]) -> tuple[str, str]:
    """``(baseline fragment name, its task_instruction)``.

    The sealed manifest records the fragment NAMES and the config hash, not the
    composed values, so the instruction is read back from the committed fragment
    the manifest names -- which is the same file the run composed, pinned by that
    config hash.
    """

    fragments = (manifest.get("config") or {}).get("fragments") or {}
    baseline = str(fragments.get("baseline", ""))
    if not baseline:
        return "", ""
    doc = _load(REPO / "configs" / "baseline" / f"{baseline}.json")
    return baseline, str(doc.get("task_instruction", ""))


def _cost_facts(receipt: Mapping[str, Any], cost_aggregate: Mapping[str, Any]) -> dict[str, Any]:
    stages = receipt["stages"]
    dispatch = float(stages["run_phases"]["wall_seconds"])
    startup = float(stages["serve"]["startup_seconds"])
    calls = int(cost_aggregate["calls_used"])
    audio = float(cost_aggregate["audio_seconds_used"])
    return {
        "contacts": calls,
        "speech_audio_seconds": round(audio, 6),
        "dispatch_wall_seconds": round(dispatch, 1),
        "server_startup_seconds": round(startup, 1),
        "gpu_hours": round((dispatch + startup) / 3600.0, 4),
        "realtime_factor": round(audio / dispatch, 2) if dispatch else 0.0,
        "contacts_per_second": round(calls / dispatch, 3) if dispatch else 0.0,
        "mean_latency_seconds": round(
            float(cost_aggregate["latency_seconds_total"]) / calls, 4
        )
        if calls
        else 0.0,
        "prompt_tokens_total": cost_aggregate["prompt_tokens_total"],
        "prompt_tokens_mean": round(
            float(cost_aggregate["prompt_tokens_total"]) / calls, 2
        )
        if calls
        else 0.0,
        "completion_tokens_total": cost_aggregate["completion_tokens_total"],
        "completion_tokens_mean": round(
            float(cost_aggregate["completion_tokens_total"]) / calls, 2
        )
        if calls
        else 0.0,
    }


def _token_extremes(run_dir: Path, run_id: str) -> dict[str, int]:
    largest_prompt = largest_completion = 0
    path = Path(run_dir) / f"{run_id}.trace.jsonl"
    for line in io_open_lines(path):
        if '"COST"' not in line:
            continue
        payload = json.loads(line)["payload"]
        largest_prompt = max(largest_prompt, int(payload["prompt_tokens"]))
        largest_completion = max(largest_completion, int(payload["completion_tokens"]))
    return {
        "largest_prompt_tokens": largest_prompt,
        "largest_completion_tokens": largest_completion,
    }


def io_open_lines(path: Path):
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            yield line


def _arm(run_dir: Path, run_id: str, receipt_path: Path) -> dict[str, Any]:
    run_dir = Path(run_dir)
    manifest_path = run_dir / f"{run_id}.run-manifest.json"
    batch_files = sorted((run_dir / "score-batch").glob("*.score.json"))
    batch = _load(batch_files[0]) if batch_files else {}
    batch_scores = batch.get("scores", batch.get("results", {}))
    return {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "scores": _load(run_dir / f"{run_id}.scores.json"),
        "manifest": _load(manifest_path),
        "manifest_path": manifest_path,
        "manifest_sha256_recomputed": sha256_file(manifest_path),
        "receipt": _load(receipt_path),
        "outputs": _outputs(run_dir, run_id),
        "batch_verified": batch.get("verified"),
        "batch_aggregates": {
            name: value.get("aggregate")
            for name, value in (
                batch_scores.items() if isinstance(batch_scores, dict) else []
            )
            if isinstance(value, dict) and "aggregate" in value
        },
    }


def _per_call(
    corpus, rows: Sequence[Mapping[str, Any]], items: Mapping[str, Any], calls: Sequence[str]
) -> dict[str, Any]:
    by_id = {row["sample_id"]: row for row in rows}
    out: dict[str, Any] = {}
    for call in calls:
        ids = [sid for sid, item in items.items() if item["parent_sample_id"] == call]
        out[call] = corpus([by_id[sid] for sid in ids])
    return out


def _length_shape(references: Mapping[str, str], outputs: Mapping[str, str]) -> dict[str, Any]:
    import sys

    if str(REPO / "src") not in sys.path:
        sys.path.insert(0, str(REPO / "src"))
    from speech_aware_evidence_acquisition.reproduction.asr_wer_whisper import (  # noqa: PLC0415
        normalize_whisper_english,
    )

    reference_words = hypothesis_words = longer = shorter = 0
    for sid, reference in references.items():
        ref = normalize_whisper_english(reference).split()
        hyp = normalize_whisper_english(outputs[sid]).split()
        reference_words += len(ref)
        hypothesis_words += len(hyp)
        if len(hyp) > len(ref):
            longer += 1
        elif len(hyp) < len(ref):
            shorter += 1
    return {
        "reference_words": reference_words,
        "hypothesis_words": hypothesis_words,
        "ratio": round(hypothesis_words / reference_words, 4) if reference_words else 0.0,
        "utterances_with_a_longer_hypothesis": longer,
        "utterances_with_a_shorter_hypothesis": shorter,
    }


def _parse_arm_spec(spec: str) -> tuple[str, str, Path, Path]:
    """``NAME=run_id,run_dir,receipt`` -> ``(name, run_id, run_dir, receipt)``."""

    name, _, rest = spec.partition("=")
    parts = [part for part in rest.split(",")]
    if not name or len(parts) != 3 or not all(parts):
        raise SystemExit(
            "--arm expects NAME=run_id,run_dir,receipt; got %r" % (spec,)
        )
    return name, parts[0], Path(parts[1]), Path(parts[2])


def _parse_contrast_spec(spec: str) -> tuple[str, str]:
    """``RIGHT-LEFT`` -> ``(right, left)``, i.e. "RIGHT minus LEFT"."""

    right, _, left = spec.partition("-")
    if not right or not left:
        raise SystemExit("--contrast expects RIGHT-LEFT; got %r" % (spec,))
    return right, left


def _corpus_wer_pct(rows_by_id: Mapping[str, Mapping[str, Any]], ids: Sequence[str]) -> float:
    errors = words = 0
    for sid in ids:
        row = rows_by_id[sid]
        errors += int(row["substitutions"]) + int(row["deletions"]) + int(row["insertions"])
        words += len(row["ref_hit_mask"])
    return 100.0 * errors / words if words else 0.0


def main() -> int:
    parser = argparse.ArgumentParser()
    # Legacy A/B flags: the exact invocation that produced the sealed
    # 2026-09-05 prompt A/B verdict still works unchanged.
    parser.add_argument("--run-dir-a", type=Path, default=None)
    parser.add_argument("--receipt-a", type=Path, default=None)
    parser.add_argument("--run-dir-b", type=Path, default=None)
    parser.add_argument("--receipt-b", type=Path, default=None)
    parser.add_argument("--run-id-a", default=RUN_A)
    parser.add_argument("--run-id-b", default=RUN_B)
    # N-arm form (2026-09-05, shape-C flight): repeatable, and it composes
    # with the legacy flags rather than replacing them.
    parser.add_argument(
        "--arm",
        action="append",
        default=None,
        metavar="NAME=run_id,run_dir,receipt",
        help="repeatable; one sealed arm to read",
    )
    parser.add_argument(
        "--contrast",
        action="append",
        default=None,
        metavar="RIGHT-LEFT",
        help="repeatable; a paired contrast, RIGHT minus LEFT (default B-A)",
    )
    parser.add_argument(
        "--primary-contrast",
        default=None,
        help="the contrast the preregistered decision rule is stated on",
    )
    parser.add_argument("--experiment-id", default="SAEA-E22-DEV-ESB-PROMPT-AB-V1")
    parser.add_argument(
        "--preregistration",
        default="docs/readiness/2026-09-05-e22-dev-esb-prompt-ab-v1-preregistration.md",
    )
    parser.add_argument("--output-dir", type=Path, default=CHECK / "verdict")
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path((os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")),
    )
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    arm_specs: dict[str, tuple[str, Path, Path]] = {}
    if args.run_dir_a is not None:
        arm_specs["A"] = (args.run_id_a, args.run_dir_a, args.receipt_a)
    if args.run_dir_b is not None:
        arm_specs["B"] = (args.run_id_b, args.run_dir_b, args.receipt_b)
    for spec in args.arm or ():
        name, run_id, run_dir, receipt = _parse_arm_spec(spec)
        arm_specs[name] = (run_id, run_dir, receipt)
    if len(arm_specs) < 2:
        raise SystemExit("at least two arms are needed for a paired contrast")
    arm_names = sorted(arm_specs)
    contrasts_wanted = [
        _parse_contrast_spec(spec) for spec in (args.contrast or ["B-A"])
    ]
    for right, left in contrasts_wanted:
        for name in (right, left):
            if name not in arm_specs:
                raise SystemExit("contrast names arm %r, which was not supplied" % name)
    primary = args.primary_contrast or "%s-%s" % contrasts_wanted[0]

    verdict_module = _verdict_module()
    corpus = verdict_module._corpus
    decompose = verdict_module._decompose
    paired = _paired_module()

    roster = _load(ROSTER)
    items = {item["sample_id"]: item for item in roster["items"]}
    calls = sorted({item["parent_sample_id"] for item in items.values()})

    import sys

    if str(REPO / "src") not in sys.path:
        sys.path.insert(0, str(REPO / "src"))
    from speech_aware_evidence_acquisition.reproduction.esb_reference import (  # noqa: PLC0415
        load_esb_references,
    )

    all_references = load_esb_references(args.data_root, repo_root=REPO)
    references = {sid: all_references[sid] for sid in items}

    arms = {
        name: _arm(run_dir, run_id, receipt)
        for name, (run_id, run_dir, receipt) in arm_specs.items()
    }

    summary_arms: dict[str, Any] = {}
    per_utterance: dict[str, dict[str, dict[str, float]]] = {}
    whisper_by_id: dict[str, dict[str, Mapping[str, Any]]] = {}
    for name in arm_names:
        arm = arms[name]
        whisper_rows = list(arm["scores"]["asr-wer-esb-whisper"]["per_sample"])
        frozen_rows = list(arm["scores"]["asr-wer-esb"]["per_sample"])
        if len(whisper_rows) != len(items):
            raise SystemExit(
                f"arm {name}: {len(whisper_rows)} scored rows against {len(items)} roster rows"
            )
        overall_whisper = corpus(whisper_rows)
        overall_frozen = corpus(frozen_rows)
        per_call_whisper = _per_call(corpus, whisper_rows, items, calls)
        per_call_frozen = _per_call(corpus, frozen_rows, items, calls)
        equal_call = round(
            statistics.fmean(
                per_call_whisper[call]["corpus_wer_pct"] for call in calls
            ),
            4,
        )
        shape = decompose(
            references, arm["outputs"], items, overall_whisper["corpus_wer_pct"]
        )
        stages = arm["receipt"]["stages"]
        baseline_fragment, instruction = _instruction_of(arm["manifest"])
        baseline_doc = (
            _load(REPO / "configs" / "baseline" / f"{baseline_fragment}.json")
            if baseline_fragment
            else {}
        )
        summary_arms[name] = {
            "run_id": arm["run_id"],
            "attempt_id": arm["receipt"]["attempt_id"],
            "cell_id": arm["receipt"]["cell_id"],
            "study_commit": stages["preflight"]["study_commit"],
            "config_hash": stages["preflight"]["config_hash"],
            "protocol_hash": stages["preflight"]["protocol_hash"],
            "split_identity_hash": stages["preflight"]["split_identity_hash"],
            "manifest_sha256": stages["seal"]["manifest_sha256"],
            "manifest_path_sha256_recomputed": arm["manifest_sha256_recomputed"],
            "attempt_state": stages["seal"]["finalize"]["attempt_state"],
            "baseline_fragment": baseline_fragment,
            "task_instruction": instruction,
            "request_shape": {
                "omit_system_message": bool(baseline_doc.get("omit_system_message", False)),
                "user_turn_text": baseline_doc.get("user_turn_text"),
                "user_turn_audio_first": bool(
                    baseline_doc.get("user_turn_audio_first", True)
                ),
                "wire_messages": (
                    "[user: audio, text]"
                    if baseline_doc.get("omit_system_message")
                    else "[system: instruction][user: audio]"
                ),
            },
            "cost": _cost_facts(arm["receipt"], arm["scores"]["cost"]["aggregate"]),
            "token_extremes": _token_extremes(Path(arm["run_dir"]), arm["run_id"]),
            "completion_ceiling_tokens": 1024,
            "scorers_declared": arm["manifest"].get("scorers"),
            "scoring_batch_verified": arm["batch_verified"],
            "scoring_batch_aggregates": arm["batch_aggregates"],
            "headline": {
                "corpus_wer_whisper_pct": overall_whisper["corpus_wer_pct"],
                "mean_of_per_utterance_wer_whisper_pct": overall_whisper["mean_wer_pct"],
                "corpus_wer_saea_scoring_v1_pct": overall_frozen["corpus_wer_pct"],
                "mean_of_per_utterance_wer_saea_scoring_v1_pct": overall_frozen["mean_wer_pct"],
                "equal_call_weighted_whisper_pct": equal_call,
            },
            "counts_whisper": overall_whisper,
            "counts_saea_scoring_v1": overall_frozen,
            "per_call_whisper": per_call_whisper,
            "per_call_saea_scoring_v1": per_call_frozen,
            "error_shape": shape,
            "length_shape_direct": _length_shape(references, arm["outputs"]),
        }
        per_utterance[name] = {
            str(row["sample_id"]): {
                "wer": float(row["wer"]),
                "neg_wer": -float(row["wer"]),
            }
            for row in whisper_rows
        }
        whisper_by_id[name] = {
            str(row["sample_id"]): row for row in whisper_rows
        }

    # ---- the paired contrasts -------------------------------------------
    ordered_ids = tuple(sorted(items))
    strata: dict[str, tuple[str, ...]] = {}
    for sid in ordered_ids:
        strata.setdefault(items[sid]["parent_sample_id"], ())
    for call in list(strata):
        strata[call] = tuple(
            sid for sid in ordered_ids if items[sid]["parent_sample_id"] == call
        )

    contrast_objects: dict[str, Any] = {}
    paired_contrasts: dict[str, Any] = {}
    for right, left in contrasts_wanted:
        key = f"{right}-{left}"
        result = paired.paired_contrast(
            per_utterance[left],
            per_utterance[right],
            metrics=["neg_wer"],
            strata_of=lambda sid: items[sid]["parent_sample_id"],
            seed=SEED,
            n_replicates=N_REPLICATES,
            ci_level=CI_LEVEL,
        )
        contrast = result["neg_wer"]
        contrast_objects[key] = result

        def corpus_delta(ids: Sequence[str], _left=left, _right=right) -> float:
            """LEFT minus RIGHT in corpus WER points: POSITIVE when RIGHT is better."""

            return _corpus_wer_pct(whisper_by_id[_left], ids) - _corpus_wer_pct(
                whisper_by_id[_right], ids
            )

        corpus_boot = paired._bootstrap_result(
            ids=ordered_ids,
            statistic=corpus_delta,
            n_replicates=N_REPLICATES,
            seed=SEED,
            ci_level=CI_LEVEL,
            strata={name: strata[name] for name in sorted(strata)},
            clusters={},
        )
        wer_left = summary_arms[left]["headline"]["corpus_wer_whisper_pct"]
        wer_right = summary_arms[right]["headline"]["corpus_wer_whisper_pct"]
        ci_low = contrast.bootstrap.ci_low if contrast.bootstrap is not None else float("nan")
        ci_high = contrast.bootstrap.ci_high if contrast.bootstrap is not None else float("nan")
        paired_contrasts[key] = {
            "right_arm": right,
            "left_arm": left,
            "convention": (
                f"metric = NEGATED per-utterance Whisper-normalized WER, so delta = "
                f"{left}_wer - {right}_wer is POSITIVE when arm {right} is better and "
                f"'saves' counts utterances arm {right} improves"
            ),
            "n": contrast.n,
            "left_mean_neg_wer": contrast.left_mean,
            "right_mean_neg_wer": contrast.right_mean,
            "delta_neg_wer": contrast.delta,
            f"mean_per_utterance_wer_{left.lower()}": -contrast.left_mean,
            f"mean_per_utterance_wer_{right.lower()}": -contrast.right_mean,
            "mean_per_utterance_wer_delta_right_minus_left": -contrast.delta,
            "saves_right_better": contrast.saves,
            "harms_right_worse": contrast.harms,
            "ties": contrast.ties,
            "sign_test_p": contrast.sign_test_p,
            "bootstrap": {
                "seed": SEED,
                "n_replicates": N_REPLICATES,
                "ci_level": CI_LEVEL,
                "strata": "source call (10)",
                "point_estimate": contrast.bootstrap.point_estimate
                if contrast.bootstrap
                else None,
                "ci_low": ci_low,
                "ci_high": ci_high,
                "sigma_hat": contrast.bootstrap.sigma_hat if contrast.bootstrap else None,
            },
            "ci90_lower_bound_above_zero": bool(ci_low > 0.0),
            "corpus_level_delta": {
                "convention": (
                    f"{left}_corpus_wer - {right}_corpus_wer in points: POSITIVE when "
                    f"arm {right} is better"
                ),
                "point_estimate": corpus_boot.point_estimate,
                "ci_low": corpus_boot.ci_low,
                "ci_high": corpus_boot.ci_high,
                "sigma_hat": corpus_boot.sigma_hat,
                "seed": SEED,
                "n_replicates": N_REPLICATES,
                "ci_level": CI_LEVEL,
                "strata": "source call (10)",
                "raw_right_minus_left_points": round(wer_right - wer_left, 4),
                "note": (
                    "the same stratified resampling rule and seed the per-utterance "
                    "contrast uses, applied to the corpus statistic, which is the "
                    "paper-facing aggregation"
                ),
            },
            "per_stratum": paired.per_stratum_table(contrast),
        }

    lowest = min(arm_names, key=lambda name: summary_arms[name]["headline"]["corpus_wer_whisper_pct"])
    primary_block = paired_contrasts[primary]
    primary_right = primary_block["right_arm"]
    primary_left = primary_block["left_arm"]
    wer_right = summary_arms[primary_right]["headline"]["corpus_wer_whisper_pct"]
    wer_left = summary_arms[primary_left]["headline"]["corpus_wer_whisper_pct"]
    ratio_right = summary_arms[primary_right]["error_shape"]["length"]["ratio"]
    ratio_left = summary_arms[primary_left]["error_shape"]["length"]["ratio"]

    document = {
        "schema": "saea-e22-esb-prompt-arm-result-summary-v1",
        "study": "speech-aware-evidence-acquisition",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "experiment_id": args.experiment_id,
        "preregistration": args.preregistration,
        "population": {
            "roster_sha256": sha256_file(ROSTER),
            "utterances": len(items),
            "calls": calls,
            "audio_seconds_total": roster["audio_seconds_total"],
            "clamped_to_decoded_parent": roster.get("clamped_to_decoded_parent", []),
            "split_role": "dev",
            "boundary": (
                "this study's own registered earnings22-original dev subset10; no "
                "confirmatory call is named, loaded, decoded, scored or read, and the six "
                "calibration-exposed ESB test calls are not read again"
            ),
        },
        "arms": summary_arms,
        "arm_names": arm_names,
        "held_constant": (
            "the roster, the derived media bytes, the derived reference layer, the "
            "scorers, the build, the quantization, the audio path, the serving geometry, "
            "the decoding parameters, the harness and the entry point. Arms A and B "
            "differ from each other in the instruction TEXT only; arm C differs from arm "
            "B in the request SHAPE only, at a byte-identical instruction string."
        ),
        "paired_contrasts": paired_contrasts,
        "primary_contrast": primary,
        "decision": {
            "rule": (
                f"the preregistered rule is stated on contrast {primary}: arm "
                f"{primary_right} is adopted if its pooled corpus Whisper-normalized WER "
                f"beats arm {primary_left}, the paired CI90 lower bound is above 0, and "
                "the hypothesis-to-reference length ratio falls toward 1.0"
            ),
            f"corpus_wer_{primary_right.lower()}_pct": wer_right,
            f"corpus_wer_{primary_left.lower()}_pct": wer_left,
            "right_minus_left_points": round(wer_right - wer_left, 4),
            "right_arm_is_lower": wer_right < wer_left,
            "ci90_lower_bound_above_zero": primary_block["ci90_lower_bound_above_zero"],
            f"length_ratio_{primary_right.lower()}": ratio_right,
            f"length_ratio_{primary_left.lower()}": ratio_left,
            "length_ratio_falls_toward_one": ratio_right < ratio_left,
            "length_ratio_condition_as_preregistered": (
                "strictly below the left arm's pooled hypothesis/reference word ratio"
            ),
            "distance_from_one": {
                primary_right: round(abs(ratio_right - 1.0), 4),
                primary_left: round(abs(ratio_left - 1.0), 4),
            },
            "length_ratio_closer_to_one": abs(ratio_right - 1.0) < abs(ratio_left - 1.0),
            "why_both_readings_are_reported": (
                "the preregistered clause reads 'strictly below', which a catastrophic "
                "UNDER-generation would also satisfy while overshooting 1.0. It cannot "
                "change the outcome, because the rule is a conjunction whose first "
                "condition is that the arm's corpus WER actually beats the control, and "
                "under-generation raises WER. Both readings are printed so a reader never "
                "has to take that on trust."
            ),
            "all_three_conditions_hold": bool(
                wer_right < wer_left
                and primary_block["ci90_lower_bound_above_zero"]
                and ratio_right < ratio_left
            ),
            "lowest_corpus_wer_arm": lowest,
        },
        "band_indication_only": {
            "published_same_model_test_subset_wer": PAPER_WER,
            "cross_read_wer": CROSS_READ_WER,
            "band": BAND,
            "per_arm": {
                name: {
                    "corpus_wer_whisper_pct": summary_arms[name]["headline"][
                        "corpus_wer_whisper_pct"
                    ],
                    "inside_band_of_9_79": summary_arms[name]["headline"][
                        "corpus_wer_whisper_pct"
                    ]
                    <= PAPER_WER + BAND,
                    "inside_band_of_12_3": summary_arms[name]["headline"][
                        "corpus_wer_whisper_pct"
                    ]
                    <= CROSS_READ_WER + BAND,
                }
                for name in arm_names
            },
            "caveat": (
                "INDICATION ONLY. These ten calls are this study's dev subset10, not the "
                "published ESB test subset, and no published number covers them. No "
                "alignment verdict is issued here."
            ),
        },
        "sealed_test_flight_for_context": {
            "run_id": "SAEA-E22-ESB-SHORTFORM-ALIGNMENT-V1",
            "population": "the six ESB TEST calls, 2,735 utterances",
            "corpus_wer_whisper_pct": SEALED_TEST_CORPUS_WER,
            "verdict": "NOT ALIGNED",
            "caveat": (
                "a DIFFERENT population. Arm A here sends that flight's instruction byte "
                "for byte, so the two arm-A numbers are protocol-comparable, but the "
                "corpora differ and the difference between them is not an effect of "
                "anything this experiment manipulated."
            ),
        },
    }
    if "B-A" in paired_contrasts:
        # Backwards-compatible alias: the sealed 2026-09-05 A/B verdict cites
        # this key by name.
        document["paired_contrast_b_minus_a"] = paired_contrasts["B-A"]
        document["corpus_level_delta"] = paired_contrasts["B-A"]["corpus_level_delta"]

    output_dir = Path(args.output_dir)
    text = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    markdown = _render_markdown(document, paired, contrast_objects)
    if args.write:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "result-summary.json").write_text(
            text, encoding="utf-8", newline="\n"
        )
        (output_dir / "per-arm-tables.md").write_text(
            markdown, encoding="utf-8", newline="\n"
        )
    print(
        json.dumps(
            {
                "corpus_wer_pct": {
                    name: summary_arms[name]["headline"]["corpus_wer_whisper_pct"]
                    for name in arm_names
                },
                "length_ratio": {
                    name: summary_arms[name]["error_shape"]["length"]["ratio"]
                    for name in arm_names
                },
                "contrasts": {
                    key: {
                        "delta_neg_wer": block["delta_neg_wer"],
                        "ci90": [
                            block["bootstrap"]["ci_low"],
                            block["bootstrap"]["ci_high"],
                        ],
                        "saves": block["saves_right_better"],
                        "harms": block["harms_right_worse"],
                        "ties": block["ties"],
                        "sign_test_p": block["sign_test_p"],
                        "corpus_delta_points": block["corpus_level_delta"][
                            "point_estimate"
                        ],
                        "corpus_delta_ci90": [
                            block["corpus_level_delta"]["ci_low"],
                            block["corpus_level_delta"]["ci_high"],
                        ],
                    }
                    for key, block in paired_contrasts.items()
                },
                "decision": document["decision"],
                "output_dir": str(output_dir),
                "written": args.write,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _render_markdown(document, paired, contrast_objects) -> str:
    arms = document["arms"]
    arm_names = document["arm_names"]
    calls = document["population"]["calls"]
    lines: list[str] = []
    lines.append("# Earnings-22 DEV ESB arms — tables")
    lines.append("")
    lines.append("## Headline, per arm")
    lines.append("")
    lines.append(
        "| arm | request shape | instruction | corpus WER % (Whisper) | mean per-utt % | "
        "equal-call % | corpus WER % (saea-scoring-v1) | S | D | I | ref words | "
        "hyp/ref length |"
    )
    lines.append("|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for name in arm_names:
        arm = arms[name]
        counts = arm["counts_whisper"]
        shape = arm["error_shape"]["length"]
        lines.append(
            "| %s | `%s` | `%s` | **%.3f** | %.3f | %.3f | %.3f | %d | %d | %d | %d | %.4f |"
            % (
                name,
                arm["request_shape"]["wire_messages"],
                (arm.get("task_instruction") or "")[:70],
                arm["headline"]["corpus_wer_whisper_pct"],
                arm["headline"]["mean_of_per_utterance_wer_whisper_pct"],
                arm["headline"]["equal_call_weighted_whisper_pct"],
                arm["headline"]["corpus_wer_saea_scoring_v1_pct"],
                counts["substitutions"],
                counts["deletions"],
                counts["insertions"],
                counts["reference_words"],
                shape["ratio"],
            )
        )
    lines.append("")
    lines.append("## Per call, corpus WER % under the Whisper normalizer")
    lines.append("")
    lines.append(
        "| call | utterances | ref words | "
        + " | ".join("arm %s" % name for name in arm_names)
        + " |"
    )
    lines.append("|---|---:|---:|" + "---:|" * len(arm_names))
    for call in calls:
        first = arms[arm_names[0]]["per_call_whisper"][call]
        cells = " | ".join(
            "%.3f" % arms[name]["per_call_whisper"][call]["corpus_wer_pct"]
            for name in arm_names
        )
        lines.append(
            "| %s | %d | %d | %s |"
            % (call, first["utterances"], first["reference_words"], cells)
        )
    lines.append("")
    lines.append("## Length ratio and WER by utterance duration")
    lines.append("")
    lines.append(
        "| duration | utterances | "
        + " | ".join(
            "%s ratio | %s WER %%" % (name, name) for name in arm_names
        )
        + " |"
    )
    lines.append("|---|---:|" + "---:|---:|" * len(arm_names))
    buckets = {
        name: {
            (block["seconds_from"], block["seconds_to"]): block
            for block in arms[name]["error_shape"]["by_duration_bucket"]
        }
        for name in arm_names
    }
    for key in sorted(buckets[arm_names[0]]):
        row = buckets[arm_names[0]][key]
        cells = " | ".join(
            "%.3f | %.2f"
            % (
                buckets[name][key]["length_ratio"],
                buckets[name][key]["corpus_wer_pct"],
            )
            for name in arm_names
        )
        lines.append(
            "| %g–%g s | %d | %s |" % (key[0], key[1], row["utterances"], cells)
        )
    lines.append("")
    for name, contrasts in contrast_objects.items():
        lines.append("## Paired per-utterance contrast %s (negated WER; positive = %s better)"
                     % (name, name.split("-")[0]))
        lines.append("")
        lines.append(paired.render_markdown(contrasts))
        lines.append("")
    lines.append("## Error shape, per arm")
    lines.append("")
    lines.append(
        "| arm | insertions share of errors % | hyp/ref length ratio | longer hyp | shorter hyp |"
    )
    lines.append("|---|---:|---:|---:|---:|")
    for name in arm_names:
        counts = arms[name]["counts_whisper"]
        shape = arms[name]["error_shape"]["length"]
        errors = counts["errors"]
        lines.append(
            "| %s | %.2f | %.4f | %d | %d |"
            % (
                name,
                100.0 * counts["insertions"] / errors if errors else 0.0,
                shape["ratio"],
                shape["utterances_with_a_longer_hypothesis"],
                shape["utterances_with_a_shorter_hypothesis"],
            )
        )
    lines.append("")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
