#!/usr/bin/env python3
"""CLI: an OFFLINE, zero-model read of inference-time SAMPLE AGGREGATION over
the sealed ROLL-1 grouped-Solver rollout (owner decision 112, step 1).

The question: does committing N Solver samples by a deterministic rule beat
delivering a single sample, and by how much, BEFORE any GPU is spent on it?

Inputs, all sealed, all read-only:

* the five per-sample-index rendered answer COPIES and their five official
  scorings that ``scripts/analysis/stage3_rollout_score.py`` (S3-3) already
  wrote under its ``--analysis-root``;
* that same read's ``per_row.json`` (per-row stratum = the construction
  roster's gold SCENARIO, plus the per-sample official count fields);
* the sealed run's own ``<run_id>.outputs.jsonl`` -- for each row's
  ``solver_group`` custody (per-sample ``parse_status`` / ``parsed_answer``),
  its delivered ``text``, and its ``native_episode_receipt.role_visits``
  contact counts (the cost table).

Zero model, tokenizer, encoder, ASR, server and network contacts. The only
contacts this CLI makes are SCORER-ON-COPIES contacts: the rules that EDIT
the delivered answer (R3 and the registered plurality-support policy at
s in {2,3,4}) produce answer text that no sealed scoring covers, so each such
arm is rendered into one canonical outputs COPY under ``--analysis-root`` and
scored ONCE through the registered scorer -- exactly the idiom
``stage3_rollout_score.score_copy`` / ``slurp_verifier_measurement.score_copy``
already use, and never ``core.scoring_batch`` (every side here is a derived
copy with no manifest and no bundle).

The SELECTION rules (R0, R1, R2, Oracle) deliver one of the five sampled
responses verbatim, so their official numbers are RECONSTRUCTED exactly from
the sealed per-row count fields rather than re-scored: the official SLU-F1 is
a micro F1 over the pooled word- and char-distance TP/FP/FN
(``reproduction.slurp_scoring.SluScore.slu_f1``), the official span-F1 the
micro F1 over the exact-match counts, and intent accuracy the mean of
``scenario_action_exact``. One selection arm (R1) is ALSO scored as a copy,
so the reconstruction identity is proved rather than asserted.

NO utterance text, transcript, model output text, gold slot filler or gold
annotation is ever printed or persisted by this CLI. ``report.json`` and
``report.md`` carry ids, entity-TYPE labels, scenario labels, counts, scores
and hashes only. The rendered outputs copies under ``--analysis-root`` do
carry the rendered JSON answer text, because the registered scorer needs it
to score against gold -- exactly as every other ``score_copy`` caller in this
repository writes; they are written under ``--analysis-root``, never under
the repository.

Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:<worktree>/src \\
    SPEECHRL_DATA_DIR=$SAEA_DATA_ROOT \\
    nice -n 10 python scripts/analysis/slurp_sample_aggregation_offline_read.py \\
      --run SAEA-SLURP-STAGE3-ROLLOUT-R01-V1 \\
      --attempt attempt-slurp-native-stage3-rollout-r01-generation-v1 \\
      --rollout-score-root "$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-ROLLOUT-R01-SCORE-V1" \\
      --analysis-root "$SPEECHRL_DATA_DIR/analysis/SLURP-SAMPLE-AGGREGATION-OFFLINE-READ-V1"
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

SCHEMA = "saea-slurp-sample-aggregation-offline-read-v1"
READ_ID = "SAEA-SLURP-SAMPLE-AGGREGATION-OFFLINE-READ-V1"
DEFAULT_SCORER_ID = "slurp-slu-official-projected-v3-train"
#: The registered commit policy cell ROLL-1 actually flew, and the parameters
#: it flew with (``configs/baseline/slurp-native-stage3-rollout-baseline-v1``).
FLOWN_COMMIT_POLICY = "saea-commit-plurality-support-v1"
FLOWN_MIN_SUPPORT = 3
FLOWN_SIMILARITY_THRESHOLD = 0.8
#: The paired row bootstrap, fixed by this read's own registration.
BOOTSTRAP_DRAWS = 10_000
BOOTSTRAP_SEED = 20260915
#: The locked v2.0 PLAN arm's contacts per row, the figure every cost
#: statement in this repository compares against.
PLAN_CONTACTS_PER_ROW = 4.1

COUNT_FIELDS = (
    "slu_f1_word_tp", "slu_f1_word_fp", "slu_f1_word_fn",
    "slu_f1_char_tp", "slu_f1_char_fp", "slu_f1_char_fn",
    "slot_f1_exact_tp", "slot_f1_exact_fp", "slot_f1_exact_fn",
)
EMPTY_ANSWER = json.dumps(
    {"scenario": "", "action": "", "entities": []}, ensure_ascii=False, sort_keys=True
)


class AggregationReadError(RuntimeError):
    """A sealed input is missing or does not have the shape this read needs."""


# ---------------------------------------------------------------------------
# small shared helpers (the stage3_rollout_score idiom, unchanged)
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def render_answer(payload: Mapping[str, Any] | None) -> str:
    """The canonical delivered payload, byte for byte the form
    ``scripts.analysis.stage3_rollout_score.render_answer`` /
    ``analysis.native_commit_replay.replay_row`` write."""

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


def prf_f1(tp: float, fp: float, fn: float) -> float:
    """``reproduction.slurp_scoring._prf``'s F1 half, on pooled counts."""

    precision = 0.0 if (tp == 0.0 and fp == 0.0) else tp / (tp + fp)
    recall = 0.0 if (tp == 0.0 and fn == 0.0) else tp / (tp + fn)
    if precision == 0.0 and recall == 0.0:
        return 0.0
    return 2.0 * precision * recall / (precision + recall)


# ---------------------------------------------------------------------------
# sample-vs-sample agreement (never against gold)
# ---------------------------------------------------------------------------


def _safe_word_distance(truth: str, hypothesis: str) -> float:
    """``reproduction.slurp_scoring._word_distance`` with one guard.

    ``jiwer.wer`` refuses an empty reference. Gold fillers are never empty,
    so the official path never reaches that case -- but a SAMPLE's filler
    can be, and this function is only ever used sample-against-sample, never
    against gold. An empty truth therefore scores 0.0 against an equally
    empty hypothesis and 1.0 otherwise, which is what the char-distance rung
    already does. No official number depends on this branch.
    """

    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (  # noqa: PLC0415
        _word_distance,
    )

    if not truth or not hypothesis:
        return 0.0 if truth == hypothesis else 1.0
    return _word_distance(truth, hypothesis)


def pairwise_agreement(left: Any, right: Any) -> float:
    """Normalised SLU-F1 of one sample's structured answer against another's.

    Computed with THIS repository's own scorer ingredients
    (``reproduction.slurp_scoring._distance_based_counts`` through the same
    pooled word+char micro F1 the official SLU-F1 is), symmetrised over the
    two directions so the value cannot depend on which side plays gold --
    the greedy same-type matching ``_lowest_distance`` performs is not
    guaranteed symmetric. Entity-only, exactly as the official SLU-F1 is:
    the intent is handled by R2's own plurality stage, never smuggled in
    here.
    """

    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (  # noqa: PLC0415
        _char_distance,
        _distance_based_counts,
    )

    def directed(gold, predicted) -> float:
        wtp, wfp, wfn = _distance_based_counts(
            gold.entities, predicted.entities, _safe_word_distance
        )
        ctp, cfp, cfn = _distance_based_counts(
            gold.entities, predicted.entities, _char_distance
        )
        return prf_f1(wtp + ctp, wfp + cfp, wfn + cfn)

    return 0.5 * (directed(right, left) + directed(left, right))


# ---------------------------------------------------------------------------
# the sealed inputs
# ---------------------------------------------------------------------------


def load_rollout_score_root(root: Path, scorer_id: str, samples: int) -> dict[str, Any]:
    """The S3-3 deliverables: the render manifest, the five rendered copies
    and the five official scorings, verified against their own hashes."""

    manifest = json.loads((root / "render-manifest.json").read_text(encoding="utf-8"))
    if int(manifest["samples"]) != samples:
        raise AggregationReadError(
            f"render manifest carries {manifest['samples']} samples, expected {samples}"
        )
    rendered: dict[int, dict[str, str]] = {}
    scored: dict[int, dict[str, dict[str, Any]]] = {}
    pooled: dict[int, dict[str, float]] = {}
    for index in range(samples):
        entry = manifest["copies"][f"sample_{index}"]
        path = Path(entry["path"])
        if sha256_file(path) != entry["sha256"]:
            raise AggregationReadError(f"{path} drifted from its render manifest sha256")
        rendered[index] = {str(row["sample_id"]): str(row["text"]) for row in iter_jsonl(path)}
        result_path = root / f"sample_{index}-{scorer_id}-scores.json"
        result = json.loads(result_path.read_text(encoding="utf-8"))[scorer_id]
        if not result["aggregate"]["identity_check"]["passed"]:
            raise AggregationReadError(f"{result_path}: the sealed identity check did not pass")
        scored[index] = {str(row["sample_id"]): row for row in result["per_sample"]}
        pooled[index] = {
            "slu_f1_pp": 100.0 * float(result["aggregate"]["official"]["slu_f1"]),
            "intent_pp": 100.0 * float(result["aggregate"]["official"]["intent_accuracy"]),
        }
    return {"manifest": manifest, "rendered": rendered, "scored": scored, "pooled": pooled}


def load_sealed_run(directory: Path, run_id: str) -> dict[str, dict[str, Any]]:
    """Per row: the five samples' parse status and parsed answers, the
    delivered text, and the per-stage contact counts of the episode."""

    out: dict[str, dict[str, Any]] = {}
    for row in iter_jsonl(directory / f"{run_id}.outputs.jsonl"):
        sample_id = str(row["sample_id"])
        group = row.get("solver_group")
        if not isinstance(group, Mapping):
            raise AggregationReadError(f"row {sample_id} carries no solver_group custody")
        samples = []
        for record in group["samples"]:
            samples.append({
                "sample_index": int(record["sample_index"]),
                "parse_status": record.get("parse_status"),
                "parsed_answer": (
                    record["parsed_answer"] if record.get("parse_status") == "ok" else None
                ),
                "seed": record.get("seed"),
                "temperature": record.get("temperature"),
            })
        samples.sort(key=lambda entry: entry["sample_index"])
        contacts_by_stage: dict[str, int] = {}
        receipt = row.get("native_episode_receipt")
        if isinstance(receipt, Mapping):
            for visit in receipt.get("role_visits") or ():
                if not isinstance(visit, Mapping):
                    continue
                stage = str(visit.get("stage") or "unknown")
                execution = visit.get("execution_receipt")
                contacts = (
                    execution.get("contacts") if isinstance(execution, Mapping) else None
                )
                count = len(contacts) if isinstance(contacts, list) else 0
                contacts_by_stage[stage] = contacts_by_stage.get(stage, 0) + count
        out[sample_id] = {
            "samples": samples,
            "delivered_text": row.get("text"),
            "contacts_by_stage": contacts_by_stage,
            "commit_policy_id": group.get("commit_policy_id"),
            "commit_params": group.get("commit_params"),
        }
    return out


# ---------------------------------------------------------------------------
# the rules
# ---------------------------------------------------------------------------


def _parsed_answers(record: Mapping[str, Any]):
    """``{sample_index: ParsedSlurpAnswer}`` over the VALID (parsed) samples,
    in the shape ``rails.commit_policies`` works in."""

    from speech_aware_evidence_acquisition.rails.commit_policies import (  # noqa: PLC0415
        ParsedSlurpAnswer,
    )
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (  # noqa: PLC0415
        SlotEntity,
    )

    answers = {}
    for entry in record["samples"]:
        payload = entry["parsed_answer"]
        if payload is None:
            continue
        answers[entry["sample_index"]] = ParsedSlurpAnswer(
            scenario=str(payload.get("scenario", "")),
            action=str(payload.get("action", "")),
            entities=tuple(
                SlotEntity(type=str(e["type"]), filler=str(e["filler"]))
                for e in payload.get("entities", ())
            ),
        )
    return answers


def medoid_index(answers: Mapping[int, Any], candidates: Sequence[int]) -> tuple[int, dict]:
    """The candidate with the highest mean pairwise agreement to the other
    candidates; ties -> lowest sample index. A single candidate is its own
    medoid. When every pairwise agreement is 0.0 -- which is what happens
    when no candidate proposes any entity at all -- the rule degenerates to
    the lowest candidate index, and this function says so."""

    ordered = sorted(candidates)
    if len(ordered) == 1:
        return ordered[0], {"degenerate": False, "mean_agreement": None, "candidates": 1}
    means = {}
    for i in ordered:
        total = sum(pairwise_agreement(answers[i], answers[j]) for j in ordered if j != i)
        means[i] = total / (len(ordered) - 1)
    best = max(means.values())
    chosen = min(i for i in ordered if means[i] == best)
    return chosen, {
        "degenerate": bool(best == 0.0),
        "mean_agreement": best,
        "candidates": len(ordered),
    }


def plurality_intent_members(answers: Mapping[int, Any]) -> tuple[tuple[str, str] | None, list[int]]:
    """``rails.commit_policies._plurality_intent``'s own race and tie-break
    (plurality over ``(scenario, action)``; tie -> the lowest
    first-occurrence sample index), reused here rather than re-invented."""

    from speech_aware_evidence_acquisition.rails.commit_policies import (  # noqa: PLC0415
        SolverSampleVote,
        _plurality_intent,
    )

    votes = [
        SolverSampleVote(sample_index=index, parsed=answers[index])
        for index in sorted(answers)
    ]
    if not votes:
        return None, []
    intent, _support, members, _tie = _plurality_intent(votes)
    return intent, list(members)


def support_of_entity(entity, answers: Mapping[int, Any], threshold: float) -> int:
    """How many VALID samples support one ``(type, filler)`` mention: a
    sample supports it when it carries an entity of the SAME type whose
    normalized filler has character-level F1 ``>= threshold`` with it. The
    similarity function and the normalisation are the registered policy's
    own (``rails.commit_policies.character_level_f1`` /
    ``scoring.normalize.normalize_text_v1``), never a second implementation.
    """

    from speech_aware_evidence_acquisition.rails.commit_policies import (  # noqa: PLC0415
        character_level_f1,
    )
    from speech_aware_evidence_acquisition.scoring.normalize import (  # noqa: PLC0415
        normalize_text_v1,
    )

    target = normalize_text_v1(entity.filler)
    support = 0
    for answer in answers.values():
        for other in answer.entities:
            if other.type != entity.type:
                continue
            if character_level_f1(target, normalize_text_v1(other.filler)) >= threshold:
                support += 1
                break
    return support


def build_arms(
    sealed: Mapping[str, Mapping[str, Any]],
    ids: Sequence[str],
    samples: int,
    *,
    support_levels: Sequence[int],
    threshold: float,
) -> dict[str, Any]:
    """Every rule's per-row decision, in one deterministic pass.

    Returns ``{"selection": {arm: {sample_id: index}}, "constructed":
    {arm: {sample_id: rendered_text}}, "diagnostics": {...}}``.
    """

    r1: dict[str, int] = {}
    r2: dict[str, int] = {}
    r3: dict[int, dict[str, str]] = {level: {} for level in support_levels}
    degenerate_r1 = 0
    degenerate_r2 = 0
    rows_with_a_malformed_sample = 0
    intent_support_hist: dict[int, int] = {}
    dropped_by_level: dict[int, int] = {level: 0 for level in support_levels}
    kept_by_level: dict[int, int] = {level: 0 for level in support_levels}
    rows_edited_by_level: dict[int, int] = {level: 0 for level in support_levels}

    for sample_id in ids:
        record = sealed[sample_id]
        answers = _parsed_answers(record)
        if len(answers) < samples:
            rows_with_a_malformed_sample += 1
        if not answers:
            # Every sample malformed: every rule falls back to sample 0,
            # whose rendered answer is the empty answer. Deterministic, and
            # identical across the arms, so it cannot move a delta.
            r1[sample_id] = 0
            r2[sample_id] = 0
            for level in support_levels:
                r3[level][sample_id] = EMPTY_ANSWER
            continue
        chosen, diag = medoid_index(answers, sorted(answers))
        r1[sample_id] = chosen
        degenerate_r1 += 1 if diag["degenerate"] else 0

        intent, members = plurality_intent_members(answers)
        intent_support_hist[len(members)] = intent_support_hist.get(len(members), 0) + 1
        chosen2, diag2 = medoid_index(answers, members)
        r2[sample_id] = chosen2
        degenerate_r2 += 1 if diag2["degenerate"] else 0

        base = answers[chosen]
        for level in support_levels:
            kept, dropped = [], 0
            for entity in base.entities:
                if support_of_entity(entity, answers, threshold) >= level:
                    kept.append({"type": entity.type, "filler": entity.filler})
                else:
                    dropped += 1
            kept_by_level[level] += len(kept)
            dropped_by_level[level] += dropped
            rows_edited_by_level[level] += 1 if dropped else 0
            r3[level][sample_id] = render_answer(
                {"scenario": base.scenario, "action": base.action, "entities": kept}
            )

    return {
        "selection": {"R1-medoid": r1, "R2-intent-plurality-medoid": r2},
        "constructed": {f"R3-support-{level}-of-{samples}": r3[level] for level in support_levels},
        "diagnostics": {
            "rows_with_a_malformed_sample": rows_with_a_malformed_sample,
            "r1_rows_with_zero_agreement_everywhere": degenerate_r1,
            "r2_rows_with_zero_agreement_everywhere": degenerate_r2,
            "r2_intent_plurality_support_histogram": {
                str(k): intent_support_hist[k] for k in sorted(intent_support_hist)
            },
            "r3_entities_kept_by_level": {str(k): v for k, v in kept_by_level.items()},
            "r3_entities_dropped_by_level": {str(k): v for k, v in dropped_by_level.items()},
            "r3_rows_edited_by_level": {str(k): v for k, v in rows_edited_by_level.items()},
        },
    }


def build_registered_commit_arms(
    sealed: Mapping[str, Mapping[str, Any]],
    ids: Sequence[str],
    support_levels: Sequence[int],
    threshold: float,
) -> dict[str, dict[str, str]]:
    """The REGISTERED ``saea-commit-plurality-support-v1`` policy re-applied
    at each ``min_support``, through ``core.base.COMMIT_POLICIES`` -- the same
    resolution path invariant I7g itself re-runs when it verifies a grouped
    row. At ``min_support = 3`` this reproduces cell ROLL-1's own delivered
    bytes, which this CLI checks rather than assumes."""

    from speech_aware_evidence_acquisition.core.base import COMMIT_POLICIES  # noqa: PLC0415
    from speech_aware_evidence_acquisition.rails import commit_policies  # noqa: PLC0415, F401
    from speech_aware_evidence_acquisition.rails.commit_policies import (  # noqa: PLC0415
        SolverSampleVote,
    )

    policy = COMMIT_POLICIES.resolve(FLOWN_COMMIT_POLICY)
    arms: dict[str, dict[str, str]] = {}
    for level in support_levels:
        rendered: dict[str, str] = {}
        for sample_id in ids:
            answers = _parsed_answers(sealed[sample_id])
            votes = [
                SolverSampleVote(sample_index=index, parsed=answers.get(index))
                for index in range(len(sealed[sample_id]["samples"]))
            ]
            outcome = policy(votes, min_support=level, similarity_threshold=threshold)
            rendered[sample_id] = render_answer({
                "scenario": outcome.answer.scenario,
                "action": outcome.answer.action,
                "entities": [
                    {"type": e.type, "filler": e.filler} for e in outcome.answer.entities
                ],
            })
        arms[f"PS-registered-support-{level}"] = rendered
    return arms


# ---------------------------------------------------------------------------
# scoring the constructed arms on COPIES
# ---------------------------------------------------------------------------


def score_copy(
    scorer_id: str, outputs_copy: Path, result_path: Path, lock: Mapping[str, object], root: Path
) -> tuple[dict[str, Any], float]:
    """One complete registered scoring over a COPY, cached by its result
    file (the ``stage3_rollout_score.score_copy`` idiom, unchanged)."""

    from speech_aware_evidence_acquisition.core.base import SCORERS  # noqa: PLC0415
    import speech_aware_evidence_acquisition.core.scorers  # noqa: PLC0415, F401

    if result_path.exists():
        return json.loads(result_path.read_text(encoding="utf-8"))[scorer_id], 0.0
    scorer = SCORERS.resolve(scorer_id)
    started = time.time()
    result = scorer(outputs_copy, lock, root)
    elapsed = time.time() - started
    if not result["aggregate"]["identity_check"]["passed"]:
        raise AggregationReadError(
            f"{scorer_id} port/official identity check failed on {outputs_copy}"
        )
    write_json(result_path, {scorer_id: result})
    return result, elapsed


# ---------------------------------------------------------------------------
# aggregation, the paired row bootstrap
# ---------------------------------------------------------------------------


def counts_matrix(per_row: Mapping[str, Mapping[str, Any]], ids: Sequence[str]):
    """``(n, 10)``: the nine official count fields plus the intent indicator,
    in ``ids`` order."""

    import numpy as np  # noqa: PLC0415

    matrix = np.zeros((len(ids), 10), dtype=np.float64)
    for position, sample_id in enumerate(ids):
        row = per_row[sample_id]
        for column, field in enumerate(COUNT_FIELDS):
            matrix[position, column] = float(row[field])
        matrix[position, 9] = 1.0 if float(row["scenario_action_exact"]) >= 1.0 else 0.0
    return matrix


def pooled_from_sums(sums):
    """``(slu_f1_pp, span_f1_pp)`` from a ``(..., 10)`` array of
    pooled counts. Vectorised over any leading axis."""

    import numpy as np  # noqa: PLC0415

    def f1(tp, fp, fn):
        precision = np.where((tp == 0) & (fp == 0), 0.0, tp / np.maximum(tp + fp, 1e-12))
        recall = np.where((tp == 0) & (fn == 0), 0.0, tp / np.maximum(tp + fn, 1e-12))
        denominator = precision + recall
        return np.where(denominator == 0, 0.0, 2.0 * precision * recall / np.maximum(denominator, 1e-12))

    slu = f1(
        sums[..., 0] + sums[..., 3], sums[..., 1] + sums[..., 4], sums[..., 2] + sums[..., 5]
    )
    span = f1(sums[..., 6], sums[..., 7], sums[..., 8])
    return 100.0 * slu, 100.0 * span


def summarise(matrix, row_f1, weights=None) -> dict[str, float]:
    """Pooled official SLU-F1 / span-F1 / intent exact plus the per-row SLU
    mean, over one weighting of the rows (``None`` = every row once)."""

    import numpy as np  # noqa: PLC0415

    if weights is None:
        sums = matrix.sum(axis=0)
        total = float(matrix.shape[0])
        mean_row = float(np.mean(row_f1))
    else:
        sums = weights @ matrix
        total = float(weights.sum())
        mean_row = float((weights @ row_f1) / total)
    slu, span = pooled_from_sums(sums)
    return {
        "slu_f1_pp": float(slu),
        "span_f1_pp": float(span),
        "intent_exact_pp": 100.0 * float(sums[9]) / total,
        "per_row_slu_mean_pp": 100.0 * mean_row,
    }


def bootstrap(arms: Mapping[str, Any], ids: Sequence[str], baseline_key: str) -> dict[str, Any]:
    """Paired row bootstrap: resample the rows with replacement (cluster =
    row, so every arm is resampled the SAME way on every draw), recompute
    each arm's pooled and per-row statistics, and report the percentile CI95
    of each arm's delta against ``baseline_key``."""

    import numpy as np  # noqa: PLC0415

    n = len(ids)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    indices = rng.integers(0, n, size=(BOOTSTRAP_DRAWS, n))
    weights = np.zeros((BOOTSTRAP_DRAWS, n), dtype=np.float64)
    for draw in range(BOOTSTRAP_DRAWS):
        weights[draw] = np.bincount(indices[draw], minlength=n)

    draws: dict[str, dict[str, Any]] = {}
    for name, arm in arms.items():
        sums = weights @ arm["matrix"]
        slu, span = pooled_from_sums(sums)
        draws[name] = {
            "slu_f1_pp": slu,
            "span_f1_pp": span,
            "intent_exact_pp": 100.0 * sums[:, 9] / n,
            "per_row_slu_mean_pp": 100.0 * (weights @ arm["row_f1"]) / n,
        }

    base = draws[baseline_key]
    out: dict[str, Any] = {}
    for name in arms:
        entry: dict[str, Any] = {}
        for metric in ("slu_f1_pp", "span_f1_pp", "intent_exact_pp", "per_row_slu_mean_pp"):
            delta = draws[name][metric] - base[metric]
            entry[metric] = {
                "lo": float(np.percentile(delta, 2.5)),
                "hi": float(np.percentile(delta, 97.5)),
            }
        out[name] = entry
    return out


# ---------------------------------------------------------------------------
# entity FP / FN mass by slot TYPE
# ---------------------------------------------------------------------------


def type_mass(
    rendered: Mapping[str, str], ids: Sequence[str], gold_by_id: Mapping[str, Any]
) -> dict[str, dict[str, float]]:
    """Official FP/FN mass, in SLU-F1 units (word + char blocks pooled),
    attributed to the slot TYPE that carries it.

    The matching is the scorer's own -- ``_lowest_distance`` inside the same
    greedy same-type walk ``reproduction.slurp_scoring._distance_based_counts``
    performs -- and the predicted fillers are normalised by the same
    ``rails.slurp_projection_v3.normalize_filler_p2`` rule the projected-v3
    scorer applies, so the totals reconcile with the pooled numbers. A
    matched pair contributes its distance to the FP and FN of its own type;
    an unmatched prediction contributes 1.0 FP to its own type; a leftover
    gold contributes 1.0 FN to its own type. TYPE LABELS AND MASS ONLY: no
    filler text of either side leaves this function.
    """

    from speech_aware_evidence_acquisition.rails.slurp_projection_v3 import (  # noqa: PLC0415
        normalize_filler_p2,
    )
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (  # noqa: PLC0415
        SlotEntity,
        _char_distance,
        _lowest_distance,
        _word_distance,
        parse_slu_response,
    )

    buckets: dict[str, dict[str, float]] = {}

    def bucket(name: str) -> dict[str, float]:
        return buckets.setdefault(
            name, {"fp": 0.0, "fn": 0.0, "tp": 0.0, "spurious": 0.0, "missing": 0.0}
        )

    for sample_id in ids:
        _scenario, _action, entities, _parsed = parse_slu_response(rendered[sample_id])
        predicted = [
            SlotEntity(type=e.type, filler=normalize_filler_p2(e.filler)) for e in entities
        ]
        gold = list(gold_by_id[sample_id].entities)
        for distance_fn in (_word_distance, _char_distance):
            remaining_types = [e.type for e in gold]
            remaining_fillers = [e.filler for e in gold]
            for entity in predicted:
                if entity.type in remaining_types:
                    index, distance = _lowest_distance(
                        entity, remaining_types, remaining_fillers, distance_fn
                    )
                    cell = bucket(entity.type)
                    cell["tp"] += 1.0
                    cell["fp"] += float(distance)
                    cell["fn"] += float(distance)
                    del remaining_types[index]
                    del remaining_fillers[index]
                else:
                    cell = bucket(entity.type)
                    cell["fp"] += 1.0
                    cell["spurious"] += 0.5
            for gold_type in remaining_types:
                cell = bucket(gold_type)
                cell["fn"] += 1.0
                cell["missing"] += 0.5
    return buckets


def entities_emitted(rendered: Mapping[str, str], ids: Sequence[str]) -> dict[str, int]:
    """How many entities each row's delivered answer carries. Counts only --
    the parse is thrown away immediately."""

    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (  # noqa: PLC0415
        parse_slu_response,
    )

    out: dict[str, int] = {}
    for sample_id in ids:
        _scenario, _action, entities, _parsed = parse_slu_response(rendered[sample_id])
        out[sample_id] = len(entities)
    return out


# ---------------------------------------------------------------------------
# markdown
# ---------------------------------------------------------------------------


def _fmt(value: float | None, digits: int = 2) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def _ci(entry: Mapping[str, float] | None) -> str:
    if entry is None:
        return "n/a"
    return f"[{entry['lo']:+.2f}, {entry['hi']:+.2f}]"


def render_markdown(payload: Mapping[str, Any]) -> str:
    lines: list[str] = []
    add = lines.append
    add(f"# {READ_ID}")
    add("")
    add(
        "Offline, zero-model-contact read of inference-time sample aggregation over the "
        f"sealed ROLL-1 rollout (`{payload['run_id']}` / `{payload['attempt_id']}`), "
        f"{payload['rows']} rows x {payload['samples']} Solver samples."
    )
    add("")
    add("## Decoding of the five samples")
    add("")
    for key, value in payload["decoding"].items():
        add(f"- `{key}`: {value}")
    add("")

    add("## 1. Every rule on all rows")
    add("")
    add(
        "| rule | I7 | pooled SLU-F1 | span-F1 | intent exact | per-row SLU mean | "
        "dSLU vs R0-mean | CI95 | saves | harms | ties |"
    )
    add("| --- | --- | ---: | ---: | ---: | ---: | ---: | :---: | ---: | ---: | ---: |")
    for name in payload["arm_order"]:
        arm = payload["arms"][name]
        block = arm["all"]
        add(
            f"| {name} | {arm['i7']} | {_fmt(block['slu_f1_pp'])} | {_fmt(block['span_f1_pp'])} | "
            f"{_fmt(block['intent_exact_pp'])} | {_fmt(block['per_row_slu_mean_pp'])} | "
            f"{_fmt(block['delta_slu_f1_pp'], 2)} | {_ci(block.get('ci_slu_f1_pp'))} | "
            f"{block['saves']} | {block['harms']} | {block['ties']} |"
        )
    add("")

    for subset in ("disagreeing", "agreeing"):
        add(f"## 2. Restricted to the {payload['subset_sizes'][subset]} {subset} rows")
        add("")
        add(
            "| rule | pooled SLU-F1 | span-F1 | intent exact | per-row SLU mean | "
            "dSLU vs R0-mean | CI95 |"
        )
        add("| --- | ---: | ---: | ---: | ---: | ---: | :---: |")
        for name in payload["arm_order"]:
            block = payload["arms"][name][subset]
            add(
                f"| {name} | {_fmt(block['slu_f1_pp'])} | {_fmt(block['span_f1_pp'])} | "
                f"{_fmt(block['intent_exact_pp'])} | {_fmt(block['per_row_slu_mean_pp'])} | "
                f"{_fmt(block['delta_slu_f1_pp'], 2)} | {_ci(block.get('ci_slu_f1_pp'))} |"
            )
        add("")

    add("## 3. Per scenario")
    add("")
    add(
        "| scenario | rows | R0-mean SLU | "
        + " | ".join(f"{name} SLU (d)" for name in payload["per_scenario_arms"])
        + " |"
    )
    add("| --- | ---: | ---: | " + " | ".join("---:" for _ in payload["per_scenario_arms"]) + " |")
    for scenario in payload["scenario_order"]:
        entry = payload["per_scenario"][scenario]
        cells = []
        for name in payload["per_scenario_arms"]:
            value = entry["arms"][name]
            cells.append(f"{_fmt(value['slu_f1_pp'])} ({value['delta_slu_f1_pp']:+.2f})")
        add(
            f"| {scenario} | {entry['rows']} | {_fmt(entry['baseline_slu_f1_pp'])} | "
            + " | ".join(cells) + " |"
        )
    add("")

    add("## 4. Entity FP / FN mass by slot TYPE (SLU-F1 units, word+char pooled)")
    add("")
    header = ["slot type"]
    for name in payload["type_mass_arms"]:
        header += [f"{name} FP", f"{name} FN"]
    add("| " + " | ".join(header) + " |")
    add("| --- | " + " | ".join("---:" for _ in header[1:]) + " |")
    for slot_type in payload["type_mass_order"]:
        cells = [slot_type]
        for name in payload["type_mass_arms"]:
            entry = payload["type_mass"][name].get(slot_type, {"fp": 0.0, "fn": 0.0})
            cells += [f"{entry['fp']:.2f}", f"{entry['fn']:.2f}"]
        add("| " + " | ".join(cells) + " |")
    totals = ["TOTAL"]
    for name in payload["type_mass_arms"]:
        block = payload["type_mass"][name]
        totals += [
            f"{sum(v['fp'] for v in block.values()):.2f}",
            f"{sum(v['fn'] for v in block.values()):.2f}",
        ]
    add("| " + " | ".join(totals) + " |")
    add("")

    add("## 4b. Where the constructed gain comes from (mechanism partition)")
    add("")
    add(
        "Rows split by whether the row's GOLD answer carries any entity at all and by "
        "whether the five samples' official per-row SLU-F1 all agree. A row with no gold "
        "entity scores per-row F1 0 whatever it predicts, so dropping a spurious entity "
        "there cannot move the per-row mean -- only the POOLED micro precision, which is "
        "the paper-facing number."
    )
    add("")
    add(
        "| partition | rows | "
        + " | ".join(f"{name} SLU / entities" for name in payload["mechanism_arms"])
        + " |"
    )
    add("| --- | ---: | " + " | ".join("---:" for _ in payload["mechanism_arms"]) + " |")
    for key in payload["mechanism_order"]:
        entry = payload["mechanism"][key]
        cells = []
        for name in payload["mechanism_arms"]:
            value = entry["arms"][name]
            cells.append(f"{_fmt(value['slu_f1_pp'])} / {value['entities']}")
        add(f"| {key} | {entry['rows']} | " + " | ".join(cells) + " |")
    add("")

    add("## 5. Cost")
    add("")
    for key, value in payload["cost"].items():
        add(f"- `{key}`: {value}")
    add("")

    add("## Diagnostics")
    add("")
    for key, value in payload["diagnostics"].items():
        add(f"- `{key}`: {json.dumps(value, sort_keys=True)}")
    add("")
    add("## Contacts")
    add("")
    add(f"`{json.dumps(payload['contacts'], sort_keys=True)}`")
    add("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", default="SAEA-SLURP-STAGE3-ROLLOUT-R01-V1")
    parser.add_argument(
        "--attempt", default="attempt-slurp-native-stage3-rollout-r01-generation-v1"
    )
    parser.add_argument(
        "--roster", default="docs/receipts/rosters/slurp-stage3-construction-r01c.json"
    )
    parser.add_argument("--rollout-score-root", required=True)
    parser.add_argument("--analysis-root", required=True)
    parser.add_argument("--scorer-id", default=DEFAULT_SCORER_ID)
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument("--support-levels", default="2,3,4")
    parser.add_argument(
        "--similarity-threshold", type=float, default=FLOWN_SIMILARITY_THRESHOLD
    )
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--data-root", default=None, help="defaults to data.lock.data_root()")
    args = parser.parse_args(argv)

    import numpy as np

    from speech_aware_evidence_acquisition.data.lock import (
        data_root as resolve_data_root, load_lock, umbrella_lock_path,
    )
    from speech_aware_evidence_acquisition.data.slurp import load_slurp_split

    repo_root = Path(args.repo_root)
    root = Path(args.data_root) if args.data_root else resolve_data_root()
    lock = load_lock(umbrella_lock_path(repo_root))
    out_dir = Path(args.analysis_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    support_levels = [int(part) for part in args.support_levels.split(",") if part.strip()]
    samples = args.samples

    directory = root / "runs" / args.run / args.attempt
    if not directory.is_dir():
        raise AggregationReadError(f"no sealed attempt directory at {directory}")

    score_root = Path(args.rollout_score_root)
    sealed_scores = load_rollout_score_root(score_root, args.scorer_id, samples)
    sealed_run = load_sealed_run(directory, args.run)

    per_row_doc = json.loads((score_root / "per_row.json").read_text(encoding="utf-8"))
    stratum = {str(row["sample_id"]): str(row["stratum"]) for row in per_row_doc["rows"]}
    disagreement = {
        str(row["sample_id"]): float(row["disagreement"]) for row in per_row_doc["rows"]
    }
    best_index = {str(row["sample_id"]): int(row["best_index"]) for row in per_row_doc["rows"]}
    ids = sorted(stratum)
    missing = sorted(set(ids) - set(sealed_run))
    if missing:
        raise AggregationReadError(
            f"{len(missing)} scored row(s) absent from the sealed outputs; first {missing[0]}"
        )

    # -- the decoding facts, from the sealed custody -----------------------
    seeds = sorted({entry["seed"] for record in sealed_run.values() for entry in record["samples"]})
    temperatures = sorted(
        {entry["temperature"] for record in sealed_run.values() for entry in record["samples"]}
    )
    first = sealed_run[ids[0]]["samples"]
    decoding = {
        "samples_per_row": samples,
        "temperature (every sample)": json.dumps(temperatures),
        "greedy sample present": (
            "no -- every one of the five samples decodes at temperature "
            f"{json.dumps(temperatures)} with its own seed (seed = fragment_seed + "
            "seed_offset + sample_index, seed_offset 0); none is greedy"
        ),
        "distinct seeds observed": len(seeds),
        "seed of sample_index 0..4 on the first row": json.dumps(
            [entry["seed"] for entry in first]
        ),
        "flown commit policy": f"{sealed_run[ids[0]]['commit_policy_id']} "
                               f"{json.dumps(sealed_run[ids[0]]['commit_params'], sort_keys=True)}",
    }

    # -- the rules ---------------------------------------------------------
    built = build_arms(
        sealed_run, ids, samples,
        support_levels=support_levels, threshold=args.similarity_threshold,
    )
    registered = build_registered_commit_arms(
        sealed_run, ids, support_levels, args.similarity_threshold
    )

    # I7g proof: the registered policy at the flown min_support must
    # reproduce the sealed delivered bytes.
    flown_key = f"PS-registered-support-{FLOWN_MIN_SUPPORT}"
    reproduced = sum(
        1 for sample_id in ids
        if registered[flown_key][sample_id] == sealed_run[sample_id]["delivered_text"]
    )

    # -- selection arms: reconstruct, never re-score -----------------------
    arms: dict[str, Any] = {}
    arm_order: list[str] = []
    # ``scorer`` counts the scorings THIS invocation actually executed;
    # ``scorer_reused_from_cache`` counts the ones read back from a result
    # file a previous invocation wrote, and the two always sum to
    # ``scorer_copies``. A re-run of a completed read therefore honestly
    # reports zero fresh scorer work rather than re-declaring seven.
    contacts = {"model": 0, "tokenizer": 0, "encoder": 0, "asr": 0, "server": 0, "network": 0,
                "scorer": 0, "scorer_reused_from_cache": 0, "scorer_copies": 0}

    def register_selection(name: str, chooser, i7: str) -> None:
        per_row = {
            sample_id: sealed_scores["scored"][chooser(sample_id)][sample_id] for sample_id in ids
        }
        arms[name] = {"per_row": per_row, "i7": i7, "kind": "selection"}
        arm_order.append(name)

    for index in range(samples):
        register_selection(
            f"R0-sample-{index}", (lambda i: (lambda _s: i))(index),
            "OK (one sampled response, verbatim)",
        )
    register_selection(
        "R1-medoid", lambda s: built["selection"]["R1-medoid"][s],
        "OK (one sampled response, verbatim)",
    )
    register_selection(
        "R2-intent-plurality-medoid", lambda s: built["selection"]["R2-intent-plurality-medoid"][s],
        "OK (one sampled response, verbatim)",
    )
    register_selection(
        "ORACLE-best-of-5", lambda s: best_index[s],
        "OK (one sampled response) -- UPPER BOUND, never a policy",
    )

    # -- constructed arms: render one copy, score it once ------------------
    constructed = dict(built["constructed"])
    constructed.update(registered)
    scored_copies: dict[str, Any] = {}
    for name in sorted(constructed):
        rendered = constructed[name]
        copy_path = out_dir / f"{name}-outputs.jsonl"
        digest = write_jsonl(
            copy_path, [{"sample_id": sample_id, "text": rendered[sample_id]} for sample_id in ids]
        )
        result, elapsed = score_copy(
            args.scorer_id, copy_path, out_dir / f"{name}-{args.scorer_id}-scores.json", lock, root
        )
        contacts["scorer_copies"] += 1
        contacts["scorer" if elapsed > 0.0 else "scorer_reused_from_cache"] += 1
        scored_copies[name] = {
            "outputs_sha256": digest,
            "scoring_seconds": elapsed,
            "official_slu_f1_pp": 100.0 * float(result["aggregate"]["official"]["slu_f1"]),
        }
        per_row = {str(row["sample_id"]): row for row in result["per_sample"]}
        i7 = (
            "NOT one sampled response -- held to I7g (a registered, deterministic "
            "COMMIT policy that re-derives the delivered bytes)"
        )
        arms[name] = {"per_row": per_row, "i7": i7, "kind": "constructed"}
        arm_order.append(name)

    # -- the R1 reconstruction proof: score R1 as a copy too ---------------
    r1_copy = out_dir / "R1-medoid-outputs.jsonl"
    r1_digest = write_jsonl(
        r1_copy,
        [
            {
                "sample_id": sample_id,
                "text": sealed_scores["rendered"][built["selection"]["R1-medoid"][sample_id]][
                    sample_id
                ],
            }
            for sample_id in ids
        ],
    )
    r1_result, r1_elapsed = score_copy(
        args.scorer_id, r1_copy, out_dir / f"R1-medoid-{args.scorer_id}-scores.json", lock, root
    )
    contacts["scorer_copies"] += 1
    contacts["scorer" if r1_elapsed > 0.0 else "scorer_reused_from_cache"] += 1

    # -- matrices, subsets, bootstrap --------------------------------------
    disagreeing_ids = [s for s in ids if disagreement[s] > 0]
    agreeing_ids = [s for s in ids if disagreement[s] <= 0]
    subsets = {"all": ids, "disagreeing": disagreeing_ids, "agreeing": agreeing_ids}

    for name, arm in arms.items():
        arm["matrix_all"] = counts_matrix(arm["per_row"], ids)
        arm["row_f1_all"] = np.array(
            [float(arm["per_row"][s]["slu_f1_f1"]) for s in ids], dtype=np.float64
        )

    baseline_rows = np.mean(
        np.stack([arms[f"R0-sample-{i}"]["row_f1_all"] for i in range(samples)]), axis=0
    )

    results: dict[str, Any] = {name: {} for name in arms}
    for subset_name, subset_ids in subsets.items():
        position = {s: i for i, s in enumerate(ids)}
        take = np.array([position[s] for s in subset_ids], dtype=np.int64)
        sub_arms = {
            name: {
                "matrix": arms[name]["matrix_all"][take],
                "row_f1": arms[name]["row_f1_all"][take],
            }
            for name in arms
        }
        # R0-mean-single is the mean of the five single-sample arms.
        mean_matrix = np.mean(
            np.stack([sub_arms[f"R0-sample-{i}"]["matrix"] for i in range(samples)]), axis=0
        )
        mean_rows = np.mean(
            np.stack([sub_arms[f"R0-sample-{i}"]["row_f1"] for i in range(samples)]), axis=0
        )
        sub_arms["R0-mean-single"] = {"matrix": mean_matrix, "row_f1": mean_rows}
        ci = bootstrap(sub_arms, subset_ids, "R0-mean-single")
        base_summary = summarise(mean_matrix, mean_rows)
        for name in arms:
            block = summarise(sub_arms[name]["matrix"], sub_arms[name]["row_f1"])
            block["delta_slu_f1_pp"] = block["slu_f1_pp"] - base_summary["slu_f1_pp"]
            block["delta_span_f1_pp"] = block["span_f1_pp"] - base_summary["span_f1_pp"]
            block["delta_intent_exact_pp"] = (
                block["intent_exact_pp"] - base_summary["intent_exact_pp"]
            )
            block["delta_per_row_slu_mean_pp"] = (
                block["per_row_slu_mean_pp"] - base_summary["per_row_slu_mean_pp"]
            )
            block["ci_slu_f1_pp"] = ci[name]["slu_f1_pp"]
            block["ci_span_f1_pp"] = ci[name]["span_f1_pp"]
            block["ci_intent_exact_pp"] = ci[name]["intent_exact_pp"]
            block["ci_per_row_slu_mean_pp"] = ci[name]["per_row_slu_mean_pp"]
            rows = sub_arms[name]["row_f1"]
            block["saves"] = int(np.sum(rows > mean_rows + 1e-12))
            block["harms"] = int(np.sum(rows < mean_rows - 1e-12))
            block["ties"] = int(len(rows) - block["saves"] - block["harms"])
            results[name][subset_name] = block
        results.setdefault("R0-mean-single", {})[subset_name] = {
            **base_summary,
            "delta_slu_f1_pp": 0.0, "delta_span_f1_pp": 0.0,
            "delta_intent_exact_pp": 0.0, "delta_per_row_slu_mean_pp": 0.0,
            "ci_slu_f1_pp": ci["R0-mean-single"]["slu_f1_pp"],
            "ci_span_f1_pp": ci["R0-mean-single"]["span_f1_pp"],
            "ci_intent_exact_pp": ci["R0-mean-single"]["intent_exact_pp"],
            "ci_per_row_slu_mean_pp": ci["R0-mean-single"]["per_row_slu_mean_pp"],
            "saves": 0, "harms": 0, "ties": len(subset_ids),
        }

    arm_order = ["R0-mean-single"] + arm_order
    arms["R0-mean-single"] = {"i7": "OK (reference: the mean of the five single-sample arms)"}

    # -- per scenario ------------------------------------------------------
    per_scenario_arms = [
        "R2-intent-plurality-medoid", f"R3-support-3-of-{samples}", "R1-medoid",
    ]
    scenarios = sorted(set(stratum.values()))
    per_scenario: dict[str, Any] = {}
    position = {s: i for i, s in enumerate(ids)}
    for scenario in scenarios:
        take = np.array(
            [position[s] for s in ids if stratum[s] == scenario], dtype=np.int64
        )
        base_matrix = np.mean(
            np.stack([arms[f"R0-sample-{i}"]["matrix_all"][take] for i in range(samples)]), axis=0
        )
        base_rows = np.mean(
            np.stack([arms[f"R0-sample-{i}"]["row_f1_all"][take] for i in range(samples)]), axis=0
        )
        base = summarise(base_matrix, base_rows)
        entry = {"rows": int(len(take)), "baseline_slu_f1_pp": base["slu_f1_pp"], "arms": {}}
        for name in per_scenario_arms:
            block = summarise(arms[name]["matrix_all"][take], arms[name]["row_f1_all"][take])
            block["delta_slu_f1_pp"] = block["slu_f1_pp"] - base["slu_f1_pp"]
            block["delta_intent_exact_pp"] = block["intent_exact_pp"] - base["intent_exact_pp"]
            entry["arms"][name] = block
        per_scenario[scenario] = entry

    # -- entity FP/FN mass by slot TYPE ------------------------------------
    gold_records = load_slurp_split(lock, root, "train", allow_heldout=False)
    gold_by_id = {record.sample_id: record for record in gold_records}
    mass_arms = {
        "R2": {
            sample_id: sealed_scores["rendered"][
                built["selection"]["R2-intent-plurality-medoid"][sample_id]
            ][sample_id]
            for sample_id in ids
        },
        "R3-s3": built["constructed"][f"R3-support-3-of-{samples}"],
    }
    # R0 as the MEAN over the five single-sample arms.
    per_sample_mass = [type_mass(sealed_scores["rendered"][i], ids, gold_by_id) for i in range(samples)]
    r0_mass: dict[str, dict[str, float]] = {}
    for block in per_sample_mass:
        for slot_type, cell in block.items():
            target = r0_mass.setdefault(
                slot_type, {"fp": 0.0, "fn": 0.0, "tp": 0.0, "spurious": 0.0, "missing": 0.0}
            )
            for key, value in cell.items():
                target[key] += value / samples
    type_mass_blocks = {
        "R0-mean": r0_mass,
        "R2": type_mass(mass_arms["R2"], ids, gold_by_id),
        "R3(s=3)": type_mass(mass_arms["R3-s3"], ids, gold_by_id),
    }
    type_mass_order = sorted(
        {t for block in type_mass_blocks.values() for t in block},
        key=lambda t: -(r0_mass.get(t, {}).get("fp", 0.0) + r0_mass.get(t, {}).get("fn", 0.0)),
    )

    # -- mechanism partition ------------------------------------------------
    mechanism_arms = [
        "R0-sample-0", "R1-medoid", "R2-intent-plurality-medoid",
        f"R3-support-3-of-{samples}", f"PS-registered-support-{FLOWN_MIN_SUPPORT}",
    ]
    mechanism_rendered = {
        "R0-sample-0": sealed_scores["rendered"][0],
        "R1-medoid": {
            sample_id: sealed_scores["rendered"][built["selection"]["R1-medoid"][sample_id]][
                sample_id
            ]
            for sample_id in ids
        },
        "R2-intent-plurality-medoid": mass_arms["R2"],
        f"R3-support-3-of-{samples}": built["constructed"][f"R3-support-3-of-{samples}"],
        f"PS-registered-support-{FLOWN_MIN_SUPPORT}": registered[flown_key],
    }
    emitted = {
        name: entities_emitted(rendered, ids) for name, rendered in mechanism_rendered.items()
    }
    has_gold_entities = {
        sample_id: bool(gold_by_id[sample_id].entities) for sample_id in ids
    }
    partitions = {
        "gold entities, samples disagree": [
            s for s in ids if has_gold_entities[s] and disagreement[s] > 0
        ],
        "gold entities, samples agree": [
            s for s in ids if has_gold_entities[s] and disagreement[s] <= 0
        ],
        "no gold entity, samples disagree": [
            s for s in ids if not has_gold_entities[s] and disagreement[s] > 0
        ],
        "no gold entity, samples agree": [
            s for s in ids if not has_gold_entities[s] and disagreement[s] <= 0
        ],
    }
    mechanism: dict[str, Any] = {}
    for key, subset_ids in partitions.items():
        take = np.array([position[s] for s in subset_ids], dtype=np.int64)
        entry: dict[str, Any] = {"rows": int(len(take)), "arms": {}}
        if len(take):
            for name in mechanism_arms:
                block = summarise(
                    arms[name]["matrix_all"][take], arms[name]["row_f1_all"][take]
                )
                block["entities"] = int(sum(emitted[name][s] for s in subset_ids))
                entry["arms"][name] = block
        else:
            for name in mechanism_arms:
                entry["arms"][name] = {
                    "slu_f1_pp": 0.0, "span_f1_pp": 0.0, "intent_exact_pp": 0.0,
                    "per_row_slu_mean_pp": 0.0, "entities": 0,
                }
        mechanism[key] = entry
    mechanism["ALL 625"] = {
        "rows": len(ids),
        "arms": {
            name: {
                **summarise(arms[name]["matrix_all"], arms[name]["row_f1_all"]),
                "entities": int(sum(emitted[name].values())),
            }
            for name in mechanism_arms
        },
    }

    # -- cost --------------------------------------------------------------
    stage_totals: dict[str, int] = {}
    for record in sealed_run.values():
        for stage, count in record["contacts_by_stage"].items():
            stage_totals[stage] = stage_totals.get(stage, 0) + count
    total_contacts = sum(stage_totals.values())
    solver_contacts = stage_totals.get("solver", 0)
    non_solver = total_contacts - solver_contacts
    per_sample_solver = solver_contacts / (samples * len(ids))
    cost = {
        "ROLL-1 contacts sealed (all stages)": total_contacts,
        "contacts per row at N=5 (as flown)": round(total_contacts / len(ids), 4),
        "per-stage contacts per row": json.dumps(
            {k: round(v / len(ids), 4) for k, v in sorted(stage_totals.items())}
        ),
        "non-Solver contacts per row (Perception + Reviewer + Planner + Acquisition)":
            round(non_solver / len(ids), 4),
        "Solver contacts per row per sample": round(per_sample_solver, 4),
        "implied contacts per row at N": (
            f"{round(non_solver / len(ids), 4)} + N x {round(per_sample_solver, 4)}"
        ),
        "N=1 (the plan's own grouped-solver-free shape)": round(
            non_solver / len(ids) + per_sample_solver, 4
        ),
        "N=3": round(non_solver / len(ids) + 3 * per_sample_solver, 4),
        "N=5": round(non_solver / len(ids) + 5 * per_sample_solver, 4),
        "locked v2.0 PLAN contacts per row (reference)": PLAN_CONTACTS_PER_ROW,
        "multiplier vs PLAN at N=5": round(
            (non_solver / len(ids) + 5 * per_sample_solver) / PLAN_CONTACTS_PER_ROW, 3
        ),
        "multiplier vs PLAN at N=3": round(
            (non_solver / len(ids) + 3 * per_sample_solver) / PLAN_CONTACTS_PER_ROW, 3
        ),
    }

    diagnostics = dict(built["diagnostics"])
    diagnostics["registered_policy_reproduces_sealed_delivered_bytes"] = (
        f"{reproduced}/{len(ids)} at min_support={FLOWN_MIN_SUPPORT} "
        f"(I7g re-derivation of cell ROLL-1's own delivered text)"
    )
    reconstruction = {
        "R1 pooled SLU-F1 reconstructed from sealed per-row counts":
            results["R1-medoid"]["all"]["slu_f1_pp"],
        "R1 pooled SLU-F1 from a freshly scored COPY":
            100.0 * float(r1_result["aggregate"]["official"]["slu_f1"]),
        "R1 copy sha256": r1_digest,
        "R1 copy scoring seconds": r1_elapsed,
    }
    reconstruction["absolute difference"] = abs(
        reconstruction["R1 pooled SLU-F1 reconstructed from sealed per-row counts"]
        - reconstruction["R1 pooled SLU-F1 from a freshly scored COPY"]
    )
    diagnostics["selection_reconstruction_identity"] = reconstruction

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "read_id": READ_ID,
        "run_id": args.run,
        "attempt_id": args.attempt,
        "scorer_id": args.scorer_id,
        "rows": len(ids),
        "samples": samples,
        "roster": per_row_doc["roster"],
        "rollout_score_root": str(score_root),
        "bootstrap": {"draws": BOOTSTRAP_DRAWS, "seed": BOOTSTRAP_SEED, "cluster": "row"},
        "decoding": decoding,
        "arm_order": arm_order,
        "arms": {
            name: {"i7": arms[name]["i7"], **results[name]} for name in arm_order
        },
        "subset_sizes": {
            "all": len(ids), "disagreeing": len(disagreeing_ids), "agreeing": len(agreeing_ids),
        },
        "per_scenario_arms": per_scenario_arms,
        "scenario_order": scenarios,
        "per_scenario": per_scenario,
        "type_mass_arms": ["R0-mean", "R2", "R3(s=3)"],
        "type_mass_order": type_mass_order,
        "type_mass": type_mass_blocks,
        "mechanism_arms": mechanism_arms,
        "mechanism_order": [
            "gold entities, samples disagree", "gold entities, samples agree",
            "no gold entity, samples disagree", "no gold entity, samples agree", "ALL 625",
        ],
        "mechanism": mechanism,
        "cost": cost,
        "diagnostics": diagnostics,
        "scored_copies": scored_copies,
        "contacts": contacts,
    }

    report_json = out_dir / "report.json"
    write_json(report_json, payload)
    report_md = out_dir / "report.md"
    report_md.write_text(render_markdown(payload), encoding="utf-8", newline="\n")
    print(json.dumps({
        "read_id": READ_ID,
        "rows": len(ids),
        "contacts": contacts,
        "report_json": str(report_json),
        "report_json_sha256": sha256_file(report_json),
        "report_md": str(report_md),
        "report_md_sha256": sha256_file(report_md),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
