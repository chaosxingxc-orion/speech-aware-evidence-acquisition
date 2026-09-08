#!/usr/bin/env python3
"""MF-9 -- the SLURP slot-filling gap audit (model-free).

Opened by the owner's 2026-09-08 question: our SLU-F1, and slot filling
especially, does not align with the industry best -- is there an improvement
plan. Readiness note and boundary:
``docs/readiness/2026-09-08-mf9-slurp-slot-gap-audit-v1.md``.
Exposure row ``SAEA-SLURP-MF9-SLOT-GAP-AUDIT-V1``.

**Zero model, GPU, tool, embedding, network and audio-decode contacts.** The
one subprocess this script runs is the PINNED official SLURP ``evaluate.py``
in ``~/.venvs/slurp-official-eval`` -- the scorer, never a model. No server is
started, no model is loaded, no waveform is decoded.

Boundary enforced in code, not only in prose: no devel ``sentence`` string is
ever read (``data.slurp.load_slurp_split`` does not carry one); the DEV gold
ENTITY ANNOTATIONS that do enter are read on the SCORING side, exactly where
the official scorer already reads them, and are never an input to any rule
this audit prices -- the value-projection judge of ``projection`` is mined
from TRAIN alone and refuses any other split; the held-out ``test`` split is
never named, loaded, hashed or scored.

Subcommands
-----------
``decompose``
    Question 1: where KC-S1b's SLU-F1 44.35 loss mass actually goes, attributed
    exhaustively and additively over the official metric's own TP/FP/FN
    ingredients, per slot type, ranked by lost mass.
``projection``
    Question 2: the TRAIN-only same-type value projection
    (``reproduction.slurp_value_projection``), swept over thresholds and
    re-scored against the sealed KC-S1b rows with paired CI90.
``schema``
    Question 3: schema conformance of the sealed slot outputs against the
    per-intent block each row actually received, and the source reading of
    whether grammar-constrained decoding is reachable.
``headroom``
    Question 4: per slot type, how much of the DEV gold VALUE space TRAIN
    already carries, what the KU-S3 retrieved top-5 could reach, and how many
    rows have a same-speaker TRAIN exemplar of the same slot type.
``ladder``
    Question 5: the priced improvement ladder, assembled from the four
    receipts above. It admits nothing and preregisters nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

ROW_ID = "SAEA-SLURP-MF9-SLOT-GAP-AUDIT-V1"
RECEIPT_DIRNAME = "2026-09-08-mf9-slurp-slot-gap-audit"
DEFAULT_OUT_DIR = REPO_ROOT / "docs/checks/speech-aware-evidence-acquisition" / RECEIPT_DIRNAME

SEED = 20260903
N_REPLICATES = 10000
CI_LEVEL = 0.90

#: The ADMITTED slot arm this audit decomposes.
KC_S1B_RUN = "SAEA-SLURP-KC-S1B-SLOTS-SCHEMA-DEV1000-V1"
KC_S1B_ATTEMPT = "attempt-20260906T025102Z-af6b04"
#: The sealed comparator whose per-row label chose each KC-S1b schema block.
CLOSED_LIST_RUN = "SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1"
CLOSED_LIST_ATTEMPT = "attempt-20260905T060424Z-2c5596"

DEV1000_CONFIG = "configs/dataset/slurp-speech-native-dev1000.json"
NEW500_RECEIPT = "docs/receipts/probe-samples/DEV-1000-NEW500.json"
OLD500_RECEIPT = "docs/receipts/probe-samples/DEV-500.json"
KC_S1B_PROMPT_FIT = (
    "docs/checks/speech-aware-evidence-acquisition/2026-09-05-slurp-slot-stage-kc-s1-v1/"
    "prompt-fit.json"
)
MF8_STATE_INVENTORY = (
    "docs/checks/speech-aware-evidence-acquisition/2026-09-08-mf8-speech-to-knowledge-audit/"
    "state-inventory.json"
)
SEALED_VECTOR_DIR = "vectors/slurp-kus3"

#: KC-S1b's own published verdict, hard-coded so every read below FAILS CLOSED
#: if the same sealed bytes stop reproducing it
#: (``docs/readiness/2026-09-05-slurp-slot-stage-kc-s1-v1-verdict.md`` section 1).
KC_S1B_PUBLISHED = {
    "entities_strict": 31.37,
    "word_f1": 41.58,
    "char_f1": 47.51,
    "slu_f1": 44.35,
}
#: The prompt-fit receipt's own schema-block accounting, same purpose.
KC_S1B_SCHEMA_ANCHORS = {"full_schema_fallback_rows": 42, "distinct_intents_used": 58}
#: MF-7b's published filler recall@5 for the sealed speech key, on NEW500 and
#: pooled (``docs/readiness/2026-09-06-slurp-retrieval-key-audit-v2.md`` section 1
#: and its per-query-set table), recomputed here from the sealed KU-S3 floats.
MF7B_FILLER_RECALL_ANCHORS = {"new500": 43.46, "pooled_1000": 41.90}

PAIRED_METRICS = (
    "slu_f1_f1",
    "slu_f1_word_f1",
    "slu_f1_char_f1",
    "slot_f1_exact_f1",
)

#: The thresholds question 2 sweeps. 0.0 is the pure-normalization anchor (an
#: exact match after case folding and nothing else); the brief's own range is
#: 0.1 to 0.4.
PROJECTION_THRESHOLDS = (0.0, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40)


# ---------------------------------------------------------------------------
# Shared I/O
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: Path, document: object) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def resolve_lock_and_root():
    from speech_aware_evidence_acquisition.data.lock import (
        data_root,
        load_lock,
        umbrella_lock_path,
    )

    lock_path = umbrella_lock_path()
    return load_lock(lock_path), Path(data_root()), Path(lock_path)


def attempt_dir(root: Path, run_id: str, attempt_id: str) -> Path:
    return Path(root) / "runs" / run_id / attempt_id


def sealed_outputs_path(root: Path, run_id: str, attempt_id: str) -> Path:
    return attempt_dir(root, run_id, attempt_id) / f"{run_id}.outputs.jsonl"


def sealed_manifest_path(root: Path, run_id: str, attempt_id: str) -> Path:
    return attempt_dir(root, run_id, attempt_id) / f"{run_id}.run-manifest.json"


def read_sealed_outputs(path: Path) -> dict[str, str]:
    """``sample_id -> response text`` from a sealed outputs JSONL."""

    texts: dict[str, str] = {}
    for line_no, line in enumerate(Path(path).read_text(encoding="utf-8").split("\n"), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        record = json.loads(stripped)
        sample_id = record.get("sample_id")
        text = record.get("text")
        if not isinstance(sample_id, str) or not isinstance(text, str):
            raise SystemExit(f"{path} line {line_no}: malformed sealed output row")
        if sample_id in texts:
            raise SystemExit(f"{path} line {line_no}: duplicate sample id {sample_id!r}")
        texts[sample_id] = text
    if not texts:
        raise SystemExit(f"{path} carries no sealed rows")
    return texts


def roster_sample_ids(config_path: Path) -> tuple[str, ...]:
    document = read_json(Path(config_path))
    ids = [str(item["sample_id"]) for item in document["items"]]
    if len(set(ids)) != len(ids):
        raise SystemExit(f"{config_path} repeats a sample id")
    return tuple(ids)


def receipt_ids(relpath: str) -> set[str]:
    return {str(item["id"]) for item in read_json(REPO_ROOT / relpath)["items"]}


def populations(roster: Sequence[str]) -> dict[str, list[str]]:
    ids = sorted(roster)
    old500 = sorted(receipt_ids(OLD500_RECEIPT) & set(ids))
    new500 = sorted(receipt_ids(NEW500_RECEIPT) & set(ids))
    if len(old500) != 500 or len(new500) != 500 or set(old500) & set(new500):
        raise SystemExit("the OLD500 / NEW500 partition of DEV-1000 does not reconstruct")
    return {"pooled_1000": ids, "old500": old500, "new500": new500}


def percent(count: float, total: float) -> float:
    return round(100.0 * count / total, 2) if total else 0.0


def official_block(result: Mapping[str, object]) -> dict[str, object]:
    """The official numbers of one registered-scorer result, in percent."""

    aggregate = result["aggregate"]  # type: ignore[index]
    official = aggregate["official"]
    raw = official["raw"]
    per_sample = result["per_sample"]  # type: ignore[index]
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
        "identity_check_passed": bool(aggregate["identity_check"]["passed"]),
    }


def by_sample(result: Mapping[str, object]) -> dict[str, dict]:
    return {row["sample_id"]: row for row in result["per_sample"]}  # type: ignore[index]


def write_outputs(rows: Sequence[Mapping[str, object]], path: Path) -> Path:
    Path(path).write_text(
        "\n".join(
            json.dumps({"sample_id": row["sample_id"], "text": row["text"]}, ensure_ascii=False)
            for row in rows
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return Path(path)


def prediction_text(
    scenario: str | None, action: str | None, entities: Sequence[object]
) -> str:
    """The canonical prediction envelope ``parse_slu_response`` reads back.

    Re-emitting a parsed prediction is parse-identical by construction, which
    is what lets a counterfactual change ONE field and leave the metric's view
    of everything else untouched. Every read below proves that rather than
    asserting it, by scoring an unmodified re-emission and requiring KC-S1b's
    published entity columns back to the last decimal.
    """

    return json.dumps(
        {
            "scenario": scenario,
            "action": action,
            "entities": [
                {"type": entity.type, "filler": entity.filler} for entity in entities
            ],
        },
        ensure_ascii=False,
    )


def score_outputs(path: Path, lock, root: Path) -> dict:
    from speech_aware_evidence_acquisition.reproduction.slurp_official_eval import (
        score_slurp_outputs_official,
    )

    return score_slurp_outputs_official(Path(path), lock, root, split_id="devel")


def assert_published(block: Mapping[str, object], anchors: Mapping[str, float], label: str) -> None:
    for metric, expected in anchors.items():
        actual = block[metric]
        if abs(float(actual) - float(expected)) > 1e-9:
            raise SystemExit(
                f"IDENTITY ANCHOR FAILED for {label}: {metric} is {actual}, "
                f"the published verdict says {expected}"
            )


def contrast_block(
    left: Mapping[str, Mapping[str, float]],
    right: Mapping[str, Mapping[str, float]],
    ids: Sequence[str],
    stratum_of: Callable[[str], str],
    metrics: Sequence[str] = PAIRED_METRICS,
) -> dict[str, dict]:
    from speech_aware_evidence_acquisition.analysis.paired import paired_contrast

    contrasts = paired_contrast(
        left,
        right,
        metrics=list(metrics),
        sample_ids=sorted(ids),
        strata_of=stratum_of,
        seed=SEED,
        n_replicates=N_REPLICATES,
        ci_level=CI_LEVEL,
    )
    out: dict[str, dict] = {}
    for metric, contrast in contrasts.items():
        document = contrast.as_dict()
        bootstrap = document.get("bootstrap") or {}
        out[metric] = {
            "n": document["n"],
            "left_pct": round(100.0 * document["left_mean"], 2),
            "right_pct": round(100.0 * document["right_mean"], 2),
            "delta_pp": round(100.0 * document["delta"], 2),
            "saves": document["saves"],
            "harms": document["harms"],
            "ties": document["ties"],
            "sign_test_p": document["sign_test_p"],
            "ci90_pp": [
                round(100.0 * bootstrap.get("ci_low", 0.0), 2),
                round(100.0 * bootstrap.get("ci_high", 0.0), 2),
            ],
        }
    return out


# ---------------------------------------------------------------------------
# The loss attribution -- question 1's engine
# ---------------------------------------------------------------------------


def _match_block(gold, predicted, distance_fn):
    """One official distance block's matching, with the pairs kept.

    Mirrors ``reproduction.slurp_scoring._distance_based_counts`` exactly --
    same order, same argmin, same deletions -- but returns WHICH gold each
    prediction consumed and at what distance, which is the only thing the
    counts themselves do not say. The caller checks the reconstructed
    TP/FP/FN against the scorer's own.
    """

    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (
        _lowest_distance,
    )

    remaining_types = [entity.type for entity in gold]
    remaining_fillers = [entity.filler for entity in gold]
    matched: list[tuple[str, str, str, float]] = []
    unmatched_predictions: list[tuple[str, str]] = []
    tp = fp = fn = 0.0
    for entity in predicted:
        if entity.type in remaining_types:
            index, distance = _lowest_distance(
                entity, remaining_types, remaining_fillers, distance_fn
            )
            tp += 1.0
            fp += distance
            fn += distance
            matched.append(
                (entity.type, remaining_fillers[index], entity.filler, float(distance))
            )
            del remaining_types[index]
            del remaining_fillers[index]
        else:
            unmatched_predictions.append((entity.type, entity.filler))
            fp += 1.0
    leftover = list(zip(remaining_types, remaining_fillers))
    fn += float(len(remaining_types))
    return matched, unmatched_predictions, leftover, (tp, fp, fn)


def attribute_row(gold, predicted):
    """One row's SLU-F1 loss mass, attributed exhaustively.

    The official SLU-F1 is ``2TP / (2TP + FP + FN)`` over the SUM of the word-
    and char-distance blocks, so the loss mass of a row is exactly
    ``FP + FN`` summed over both blocks. Every unit of that mass lands in
    exactly one of four buckets:

    * ``surface`` -- a prediction whose TYPE matched a gold slot but whose
      value is not the gold surface form: it pays ``d`` on FP and ``d`` on FN
      in each block, so ``2 * (d_word + d_char)``;
    * ``type_swap`` -- an unmatched prediction and an unmatched gold that
      carry the SAME value under the projection's own normalization but
      different types: 2 units from the prediction's FP plus 2 from the gold's
      FN;
    * ``spurious`` -- every other unmatched prediction, 2 units of FP;
    * ``missing`` -- every other unmatched gold, 2 units of FN.

    The word and char blocks can consume DIFFERENT gold rows when one row
    carries two gold slots of the same type, but the COUNT of unmatched
    predictions and unmatched gold is identical in both blocks (the type test
    is block-independent). The refinement therefore runs on the char block's
    assignment and the function asserts the counts agree.
    """

    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (
        _char_distance,
        _word_distance,
    )
    from speech_aware_evidence_acquisition.reproduction.slurp_value_projection import (
        normalize_filler,
    )

    word = _match_block(gold, predicted, _word_distance)
    char = _match_block(gold, predicted, _char_distance)
    if len(word[1]) != len(char[1]) or len(word[2]) != len(char[2]):
        raise SystemExit("the word and char blocks disagree on how many spans matched")

    surface_mass = 2.0 * sum(pair[3] for pair in word[0]) + 2.0 * sum(
        pair[3] for pair in char[0]
    )
    unmatched_predictions = list(char[1])
    leftover_gold = list(char[2])

    type_swaps: list[dict[str, object]] = []
    remaining_gold = list(leftover_gold)
    remaining_predictions: list[tuple[str, str]] = []
    for pred_type, pred_filler in unmatched_predictions:
        normalized = normalize_filler(pred_filler)
        hit = None
        for index, (gold_type, gold_filler) in enumerate(remaining_gold):
            if gold_type != pred_type and normalize_filler(gold_filler) == normalized:
                hit = index
                break
        if hit is None:
            remaining_predictions.append((pred_type, pred_filler))
            continue
        gold_type, gold_filler = remaining_gold.pop(hit)
        type_swaps.append(
            {
                "gold_type": gold_type,
                "gold_filler": gold_filler,
                "predicted_type": pred_type,
                "predicted_filler": pred_filler,
            }
        )

    # Both blocks walk the predictions in the SAME order and apply the SAME
    # (block-independent) type test, so index i of one matched list is index i
    # of the other: the same prediction, possibly against a different gold row
    # when the row carries two gold slots of one type.
    surface_pairs = [
        {
            "type": word_pair[0],
            "gold_filler": word_pair[1],
            "gold_filler_char_block": char_pair[1],
            "predicted_filler": word_pair[2],
            "word_distance": word_pair[3],
            "char_distance": char_pair[3],
        }
        for word_pair, char_pair in zip(word[0], char[0])
    ]

    total_mass = sum(word[3][1:]) + sum(char[3][1:])
    accounted = (
        surface_mass + 4.0 * len(type_swaps) + 2.0 * len(remaining_predictions)
        + 2.0 * len(remaining_gold)
    )
    if abs(total_mass - accounted) > 1e-9:
        raise SystemExit(
            f"the loss attribution does not close: mass {total_mass} against "
            f"{accounted} attributed"
        )
    return {
        "tp": word[3][0] + char[3][0],
        "mass": total_mass,
        "surface_mass": surface_mass,
        "surface_pairs": surface_pairs,
        "type_swaps": type_swaps,
        "spurious": remaining_predictions,
        "missing": remaining_gold,
        "predicted_count": len(predicted),
        "gold_count": len(gold),
    }


def _f1(tp: float, fp: float, fn: float) -> float:
    if tp == 0.0 and fp == 0.0:
        precision = 0.0
    else:
        precision = tp / (tp + fp)
    if tp == 0.0 and fn == 0.0:
        recall = 0.0
    else:
        recall = tp / (tp + fn)
    if precision == 0.0 and recall == 0.0:
        return 0.0
    return 2.0 * precision * recall / (precision + recall)


# ---------------------------------------------------------------------------
# Question 1 -- the loss decomposition
# ---------------------------------------------------------------------------


def command_decompose(args: argparse.Namespace) -> int:
    from speech_aware_evidence_acquisition.core.scoring_batch import ScoreJob, run_score_batch
    from speech_aware_evidence_acquisition.data.slurp import (
        load_slurp_intent_slot_schema,
        load_slurp_split,
    )
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (
        parse_slu_response,
    )

    lock, root, lock_path = resolve_lock_and_root()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    roster = roster_sample_ids(REPO_ROOT / DEV1000_CONFIG)
    pops = populations(roster)
    gold = {record.sample_id: record for record in load_slurp_split(lock, root, "devel")}

    sealed_manifest = sealed_manifest_path(root, KC_S1B_RUN, KC_S1B_ATTEMPT)
    sealed_outputs = sealed_outputs_path(root, KC_S1B_RUN, KC_S1B_ATTEMPT)
    score_dir = Path(args.score_dir or (root / "runs" / ROW_ID / "score-batch-decompose"))
    if score_dir.exists():
        shutil.rmtree(score_dir)
    batch = run_score_batch(
        [ScoreJob(job_id="kc-s1b-sealed", manifest=sealed_manifest)],
        output_dir=score_dir,
        max_workers=1,
        include_per_sample=True,
    )
    if batch["failed"]:
        raise SystemExit(f"score batch failed: {json.dumps(batch['jobs'])[:2000]}")
    sealed_result = read_json(score_dir / "kc-s1b-sealed.score.json")["scores"][
        "slurp-slu-official"
    ]
    sealed_official = official_block(sealed_result)
    assert_published(sealed_official, KC_S1B_PUBLISHED, "KC-S1b as sealed")

    texts = read_sealed_outputs(sealed_outputs)
    if sorted(texts) != sorted(roster):
        raise SystemExit("the sealed KC-S1b outputs do not cover the DEV-1000 roster")

    # --- the attribution, row by row ---------------------------------------
    rows: dict[str, dict] = {}
    corpus_tp = corpus_mass = 0.0
    for sample_id in roster:
        _, _, entities, parsed = parse_slu_response(texts[sample_id])
        record = attribute_row(gold[sample_id].entities, entities)
        record["parsed"] = parsed
        rows[sample_id] = record
        corpus_tp += record["tp"]
        corpus_mass += record["mass"]

    # The official SLU-F1 rebuilt from the port's own per-sample ingredients,
    # so the decomposition is proved to be a decomposition OF THE PUBLISHED
    # NUMBER rather than of something adjacent to it.
    per_sample = by_sample(sealed_result)
    tp_sum = sum(
        per_sample[sid]["slu_f1_word_tp"] + per_sample[sid]["slu_f1_char_tp"] for sid in roster
    )
    fp_sum = sum(
        per_sample[sid]["slu_f1_word_fp"] + per_sample[sid]["slu_f1_char_fp"] for sid in roster
    )
    fn_sum = sum(
        per_sample[sid]["slu_f1_word_fn"] + per_sample[sid]["slu_f1_char_fn"] for sid in roster
    )
    if abs(tp_sum - corpus_tp) > 1e-6 or abs(fp_sum + fn_sum - corpus_mass) > 1e-6:
        raise SystemExit(
            "the attribution's TP/mass do not reproduce the scorer's own corpus totals"
        )
    rebuilt = 100.0 * _f1(tp_sum, fp_sum, fn_sum)
    if abs(rebuilt - KC_S1B_PUBLISHED["slu_f1"]) > 0.005:
        raise SystemExit(
            f"SLU-F1 rebuilt from the ingredients is {rebuilt:.4f}, published 44.35"
        )

    # --- category mass and per-type tables ---------------------------------
    mass = {"surface": 0.0, "type_swap": 0.0, "spurious": 0.0, "missing": 0.0}
    counts = {"surface": 0, "type_swap": 0, "spurious": 0, "missing": 0, "exact": 0}
    per_type: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "gold_mentions": 0.0,
            "surface_mass": 0.0,
            "type_swap_mass": 0.0,
            "missing_mass": 0.0,
            "spurious_mass": 0.0,
            "surface_pairs": 0.0,
            "type_swaps": 0.0,
            "missing": 0.0,
            "spurious": 0.0,
            "exact": 0.0,
        }
    )
    swap_pairs: Counter[str] = Counter()
    surface_examples: list[dict[str, object]] = []
    rows_with_no_entity = 0
    missing_on_silent_rows = 0
    for sample_id in roster:
        record = rows[sample_id]
        for entity in gold[sample_id].entities:
            per_type[entity.type]["gold_mentions"] += 1
        silent = record["predicted_count"] == 0
        if silent:
            rows_with_no_entity += 1
        for pair in record["surface_pairs"]:
            block = 2.0 * (float(pair["word_distance"]) + float(pair["char_distance"]))
            mass["surface"] += block
            per_type[pair["type"]]["surface_mass"] += block
            if block == 0.0:
                counts["exact"] += 1
                per_type[pair["type"]]["exact"] += 1
            else:
                counts["surface"] += 1
                per_type[pair["type"]]["surface_pairs"] += 1
                if len(surface_examples) < 400:
                    surface_examples.append(
                        {
                            "sample_id": sample_id,
                            "type": pair["type"],
                            "gold": pair["gold_filler"],
                            "predicted": pair["predicted_filler"],
                            "word_distance": round(pair["word_distance"], 4),
                            "char_distance": round(float(pair["char_distance"]), 4),
                            "mass": round(block, 4),
                        }
                    )
        for swap in record["type_swaps"]:
            mass["type_swap"] += 4.0
            counts["type_swap"] += 1
            per_type[str(swap["gold_type"])]["type_swap_mass"] += 4.0
            per_type[str(swap["gold_type"])]["type_swaps"] += 1
            swap_pairs[f"{swap['gold_type']} <- {swap['predicted_type']}"] += 1
        for entity_type, _filler in record["spurious"]:
            mass["spurious"] += 2.0
            counts["spurious"] += 1
            per_type[entity_type]["spurious_mass"] += 2.0
            per_type[entity_type]["spurious"] += 1
        for entity_type, _filler in record["missing"]:
            mass["missing"] += 2.0
            counts["missing"] += 1
            per_type[entity_type]["missing_mass"] += 2.0
            per_type[entity_type]["missing"] += 1
            if silent:
                missing_on_silent_rows += 1

    total_mass = sum(mass.values())
    if abs(total_mass - corpus_mass) > 1e-6:
        raise SystemExit("the per-category mass does not sum to the corpus mass")

    # --- per-category counterfactual ceilings ------------------------------
    def ceiling(delta_tp: float, delta_mass: float) -> float:
        tp = tp_sum + delta_tp
        remaining = corpus_mass - delta_mass
        return round(100.0 * _f1(tp, remaining / 2.0, remaining / 2.0), 2)

    ceilings = {
        # surface forms all become exact: TP unchanged, the distance mass goes.
        "surface_perfect": ceiling(0.0, mass["surface"]),
        # every spurious prediction is withheld: its FP mass goes, TP unchanged.
        "no_spurious": ceiling(0.0, mass["spurious"]),
        # every missing gold is answered exactly: +2 TP and -2 FN each.
        "no_missing": ceiling(2.0 * counts["missing"], mass["missing"]),
        # every type swap is re-typed onto its gold: +2 TP, -4 mass each.
        "no_type_swap": ceiling(2.0 * counts["type_swap"], mass["type_swap"]),
        "all_four": ceiling(
            2.0 * (counts["missing"] + counts["type_swap"]), total_mass
        ),
    }

    # --- the intent counterfactual (question 1a) ---------------------------
    workdir = Path(tempfile.mkdtemp(prefix="saea-mf9-decompose-", dir=str(root)))
    try:
        identity_rows = []
        gold_intent_rows = []
        for sample_id in roster:
            scenario, action, entities, parsed = parse_slu_response(texts[sample_id])
            if not parsed:
                identity_rows.append({"sample_id": sample_id, "text": texts[sample_id]})
                gold_intent_rows.append({"sample_id": sample_id, "text": texts[sample_id]})
                continue
            identity_rows.append(
                {
                    "sample_id": sample_id,
                    "text": prediction_text(scenario, action, entities),
                }
            )
            gold_intent_rows.append(
                {
                    "sample_id": sample_id,
                    "text": prediction_text(
                        gold[sample_id].scenario, gold[sample_id].action, entities
                    ),
                }
            )
        identity_path = write_outputs(identity_rows, workdir / "reemitted.outputs.jsonl")
        gold_intent_path = write_outputs(
            gold_intent_rows, workdir / "gold-intent.outputs.jsonl"
        )
        identity_result = score_outputs(identity_path, lock, root)
        gold_intent_result = score_outputs(gold_intent_path, lock, root)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    identity_official = official_block(identity_result)
    gold_intent_official = official_block(gold_intent_result)
    assert_published(identity_official, KC_S1B_PUBLISHED, "KC-S1b re-emitted")
    assert_published(
        {k: gold_intent_official[k] for k in KC_S1B_PUBLISHED},
        KC_S1B_PUBLISHED,
        "KC-S1b with the gold intent substituted",
    )

    # --- the schema-selection half of question 1a --------------------------
    closed_texts = read_sealed_outputs(
        sealed_outputs_path(root, CLOSED_LIST_RUN, CLOSED_LIST_ATTEMPT)
    )
    schema = load_slurp_intent_slot_schema(lock, root)
    fit_rows = {
        row["sample_id"]: row
        for row in read_json(REPO_ROOT / KC_S1B_PROMPT_FIT)["rows"]
        if row["cell_id"] == "kc-s1b"
    }
    if len(fit_rows) != 1000:
        raise SystemExit("the prompt-fit receipt does not carry 1,000 kc-s1b rows")

    intent_right = intent_wrong = 0
    mass_by_intent_correct = {"correct": 0.0, "wrong": 0.0}
    tp_by_intent_correct = {"correct": 0.0, "wrong": 0.0}
    gold_types_outside_block = 0
    gold_types_recovered_by_gold_block = 0
    gold_mentions_considered = 0
    for sample_id in roster:
        predicted_scenario, predicted_action, _, parsed = parse_slu_response(
            closed_texts[sample_id]
        )
        predicted_intent = (
            f"{predicted_scenario}_{predicted_action}"
            if parsed and predicted_scenario and predicted_action
            else None
        )
        gold_intent = gold[sample_id].intent
        key = "correct" if predicted_intent == gold_intent else "wrong"
        if key == "correct":
            intent_right += 1
        else:
            intent_wrong += 1
        mass_by_intent_correct[key] += rows[sample_id]["mass"]
        tp_by_intent_correct[key] += rows[sample_id]["tp"]

        fit = fit_rows[sample_id]
        block_intent = fit["schema_block_intent"]
        fallback = bool(fit["schema_full_fallback"])
        sent_types = (
            set(schema.intents[block_intent].entity_types)
            if not fallback and block_intent in schema.intents
            else None
        )
        gold_block = schema.intents.get(gold_intent)
        gold_block_types = set(gold_block.entity_types) if gold_block else set()
        for entity in gold[sample_id].entities:
            gold_mentions_considered += 1
            if sent_types is not None and entity.type not in sent_types:
                gold_types_outside_block += 1
                if entity.type in gold_block_types:
                    gold_types_recovered_by_gold_block += 1

    ranked = sorted(
        per_type.items(),
        key=lambda item: -(
            item[1]["surface_mass"]
            + item[1]["type_swap_mass"]
            + item[1]["missing_mass"]
            + item[1]["spurious_mass"]
        ),
    )
    type_table = [
        {
            "entity_type": entity_type,
            "gold_mentions": int(values["gold_mentions"]),
            "exact_matches": int(values["exact"]),
            "surface_pairs": int(values["surface_pairs"]),
            "type_swaps": int(values["type_swaps"]),
            "missing": int(values["missing"]),
            "spurious": int(values["spurious"]),
            "surface_mass": round(values["surface_mass"], 3),
            "type_swap_mass": round(values["type_swap_mass"], 3),
            "missing_mass": round(values["missing_mass"], 3),
            "spurious_mass": round(values["spurious_mass"], 3),
            "total_mass": round(
                values["surface_mass"]
                + values["type_swap_mass"]
                + values["missing_mass"]
                + values["spurious_mass"],
                3,
            ),
            "share_of_loss_pct": percent(
                values["surface_mass"]
                + values["type_swap_mass"]
                + values["missing_mass"]
                + values["spurious_mass"],
                total_mass,
            ),
        }
        for entity_type, values in ranked
    ]

    per_population = {}
    for name, ids in pops.items():
        pop_mass = sum(rows[sid]["mass"] for sid in ids)
        pop_tp = sum(rows[sid]["tp"] for sid in ids)
        per_population[name] = {
            "n": len(ids),
            "slu_f1": round(100.0 * _f1(pop_tp, pop_mass / 2.0, pop_mass / 2.0), 2),
            "loss_mass": round(pop_mass, 3),
        }

    document = {
        "schema": "saea-slurp-mf9-loss-decomposition-v1",
        "row_id": ROW_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "contacts": {
            "model": 0, "gpu_hours": 0, "tool": 0, "embedding": 0,
            "network": 0, "audio_decode": 0,
        },
        "sources": {
            "umbrella_lock": str(lock_path),
            "sealed_manifest": str(sealed_manifest),
            "sealed_manifest_sha256": sha256_file(sealed_manifest),
            "sealed_outputs": str(sealed_outputs),
            "sealed_outputs_sha256": sha256_file(sealed_outputs),
            "closed_list_outputs_sha256": sha256_file(
                sealed_outputs_path(root, CLOSED_LIST_RUN, CLOSED_LIST_ATTEMPT)
            ),
            "prompt_fit_receipt": KC_S1B_PROMPT_FIT,
            "intent_slot_schema_content_hash": schema.content_hash(),
        },
        "identity_anchors": {
            "kc_s1b_sealed": sealed_official,
            "kc_s1b_reemitted": identity_official,
            "slu_f1_rebuilt_from_ingredients": round(rebuilt, 4),
            "published": KC_S1B_PUBLISHED,
        },
        "corpus": {
            "slu_f1": round(100.0 * _f1(tp_sum, fp_sum, fn_sum), 2),
            "true_positive_mass": round(tp_sum, 3),
            "loss_mass": round(total_mass, 3),
            "gold_mentions": int(sum(v["gold_mentions"] for v in per_type.values())),
            "predicted_mentions": int(sum(r["predicted_count"] for r in rows.values())),
            "rows_with_no_predicted_entity": rows_with_no_entity,
            "unparsed_rows": sum(1 for r in rows.values() if not r["parsed"]),
        },
        "categories": {
            name: {
                "mass": round(mass[name], 3),
                "share_of_loss_pct": percent(mass[name], total_mass),
                "count": counts[name],
            }
            for name in ("missing", "spurious", "surface", "type_swap")
        },
        "exact_matches": counts["exact"],
        "missing_on_silent_rows": missing_on_silent_rows,
        "ceilings_slu_f1": ceilings,
        "intent_counterfactual": {
            "what_it_is": (
                "the SAME sealed entity outputs re-scored with the row's GOLD "
                "(scenario, action) substituted for whatever the response carried -- a "
                "SCORING-SIDE counterfactual, never a runtime design, and it reads gold "
                "on the scoring side alone"
            ),
            "as_sealed": identity_official,
            "gold_intent_substituted": gold_intent_official,
            "slu_f1_delta": round(
                float(gold_intent_official["slu_f1"]) - float(identity_official["slu_f1"]), 4
            ),
            "entity_columns_identical": all(
                identity_official[key] == gold_intent_official[key]
                for key in ("entities_strict", "word_f1", "char_f1", "slu_f1")
            ),
        },
        "intent_as_schema_selector": {
            "what_it_is": (
                "the indirect channel: KC-S1b's per-intent schema block was chosen by the "
                "sealed closed-list arm's UNPROJECTED label, so an intent error sends the "
                "wrong intent's type list"
            ),
            "rows_with_correct_block_intent": intent_right,
            "rows_with_wrong_block_intent": intent_wrong,
            "slu_f1_on_correct_block_rows": round(
                100.0
                * _f1(
                    tp_by_intent_correct["correct"],
                    mass_by_intent_correct["correct"] / 2.0,
                    mass_by_intent_correct["correct"] / 2.0,
                ),
                2,
            ),
            "slu_f1_on_wrong_block_rows": round(
                100.0
                * _f1(
                    tp_by_intent_correct["wrong"],
                    mass_by_intent_correct["wrong"] / 2.0,
                    mass_by_intent_correct["wrong"] / 2.0,
                ),
                2,
            ),
            "gold_mentions_considered": gold_mentions_considered,
            "gold_mentions_whose_type_was_not_in_the_block_sent": gold_types_outside_block,
            "of_those_present_in_the_gold_intents_block": gold_types_recovered_by_gold_block,
        },
        "per_population": per_population,
        "per_entity_type": type_table,
        "top_type_swaps": dict(swap_pairs.most_common(25)),
        "surface_examples": surface_examples[:120],
    }
    write_json(out_dir / "loss-decomposition.json", document)
    summary = dict(document)
    summary.pop("surface_examples")
    summary["per_entity_type"] = type_table[:12]
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


# ---------------------------------------------------------------------------
# Question 2 -- the value-projection judge
# ---------------------------------------------------------------------------


def command_projection(args: argparse.Namespace) -> int:
    from speech_aware_evidence_acquisition.data.slurp import load_slurp_split
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (
        parse_slu_response,
    )
    from speech_aware_evidence_acquisition.reproduction.slurp_value_projection import (
        SLURP_VALUE_PROJECTION_ID,
        branch_counts,
        load_value_projection_inventory,
        project_slu_entities,
    )

    lock, root, lock_path = resolve_lock_and_root()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    roster = roster_sample_ids(REPO_ROOT / DEV1000_CONFIG)
    pops = populations(roster)
    gold = {record.sample_id: record for record in load_slurp_split(lock, root, "devel")}
    texts = read_sealed_outputs(sealed_outputs_path(root, KC_S1B_RUN, KC_S1B_ATTEMPT))

    inventory = load_value_projection_inventory(lock, root)
    parsed_rows = {
        sample_id: parse_slu_response(texts[sample_id]) for sample_id in roster
    }

    workdir = Path(tempfile.mkdtemp(prefix="saea-mf9-projection-", dir=str(root)))
    cache: dict[tuple[str, str], tuple[str, float] | None] = {}
    try:
        arms: dict[str, Path] = {}
        branch_tables: dict[str, dict[str, int]] = {}
        changed_examples: dict[str, list[dict[str, object]]] = {}
        changed_counts: dict[str, dict[str, int]] = {}
        for threshold in (None, *PROJECTION_THRESHOLDS):
            name = "baseline" if threshold is None else f"tau-{threshold:.2f}"
            rows = []
            outcomes_all = []
            changed_rows = 0
            changed_values = 0
            examples: list[dict[str, object]] = []
            for sample_id in roster:
                scenario, action, entities, parsed = parsed_rows[sample_id]
                if not parsed:
                    rows.append({"sample_id": sample_id, "text": texts[sample_id]})
                    continue
                if threshold is None:
                    projected = entities
                else:
                    projected, outcomes = project_slu_entities(
                        entities, inventory, threshold=threshold, nearest_cache=cache
                    )
                    outcomes_all.extend(outcomes)
                    row_changed = [o for o in outcomes if o.changed]
                    if row_changed:
                        changed_rows += 1
                        changed_values += len(row_changed)
                        for outcome in row_changed:
                            if len(examples) < 200:
                                examples.append(
                                    {
                                        "sample_id": sample_id,
                                        "type": outcome.entity_type,
                                        "from": outcome.source_filler,
                                        "to": outcome.projected_filler,
                                        "branch": outcome.branch,
                                        "distance": round(float(outcome.distance or 0.0), 4),
                                    }
                                )
                rows.append(
                    {
                        "sample_id": sample_id,
                        "text": prediction_text(scenario, action, projected),
                    }
                )
            arms[name] = write_outputs(rows, workdir / f"{name}.outputs.jsonl")
            if threshold is not None:
                branch_tables[name] = branch_counts(outcomes_all)
                changed_examples[name] = examples
                changed_counts[name] = {
                    "rows_changed": changed_rows,
                    "values_changed": changed_values,
                }

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            scored = dict(
                zip(
                    arms,
                    pool.map(lambda path: score_outputs(path, lock, root), arms.values()),
                )
            )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    baseline_official = official_block(scored["baseline"])
    assert_published(baseline_official, KC_S1B_PUBLISHED, "KC-S1b re-emitted (projection arm)")

    def stratum_of(sample_id: str) -> str:
        return gold[sample_id].scenario

    baseline_samples = by_sample(scored["baseline"])
    table: list[dict[str, object]] = []
    for threshold in PROJECTION_THRESHOLDS:
        name = f"tau-{threshold:.2f}"
        official = official_block(scored[name])
        entry: dict[str, object] = {
            "threshold": threshold,
            "official": official,
            "delta_vs_baseline": {
                metric: round(
                    float(official[metric]) - float(baseline_official[metric]), 2
                )
                for metric in ("entities_strict", "word_f1", "char_f1", "slu_f1")
            },
            "branch_counts": branch_tables[name],
            "changed": changed_counts[name],
            "paired": {},
        }
        right = by_sample(scored[name])
        for population, ids in pops.items():
            entry["paired"][population] = contrast_block(
                baseline_samples, right, ids, stratum_of
            )
        table.append(entry)

    best = max(table, key=lambda entry: entry["official"]["slu_f1"])
    best_pooled = best["paired"]["pooled_1000"]["slu_f1_f1"]
    best_new500 = best["paired"]["new500"]["slu_f1_f1"]
    relock_candidate = bool(
        float(best["delta_vs_baseline"]["slu_f1"]) >= 1.0
        and float(best_pooled["ci90_pp"][0]) > 0.0
        and float(best_new500["ci90_pp"][0]) > 0.0
    )

    document = {
        "schema": "saea-slurp-mf9-value-projection-v1",
        "row_id": ROW_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "contacts": {
            "model": 0, "gpu_hours": 0, "tool": 0, "embedding": 0,
            "network": 0, "audio_decode": 0,
        },
        "rule": {
            "projection_id": SLURP_VALUE_PROJECTION_ID,
            "module": "reproduction.slurp_value_projection",
            "statement": (
                "project a predicted slot filler onto the nearest TRAIN surface form OF "
                "THE SAME SLOT TYPE when the official scorer's own normalized character "
                "distance is at or below the threshold; the comparison string is the "
                "prediction case-folded with whitespace collapsed, ties break on the "
                "larger TRAIN mention count then lexicographically, and the rule never "
                "changes a slot type, invents a filler, or deletes a prediction"
            ),
            "inventory": inventory.as_json(),
        },
        "sources": {
            "umbrella_lock": str(lock_path),
            "sealed_outputs": str(sealed_outputs_path(root, KC_S1B_RUN, KC_S1B_ATTEMPT)),
            "sealed_outputs_sha256": sha256_file(
                sealed_outputs_path(root, KC_S1B_RUN, KC_S1B_ATTEMPT)
            ),
        },
        "identity_anchor": {
            "baseline_reemitted": baseline_official,
            "published": KC_S1B_PUBLISHED,
        },
        "paired_settings": {
            "seed": SEED,
            "n_replicates": N_REPLICATES,
            "ci_level": CI_LEVEL,
            "strata": "gold scenario",
            "delta": "projected - baseline, on per-sample official scores",
        },
        "sweep": table,
        "best_threshold": best["threshold"],
        "relock_candidate": relock_candidate,
        "relock_rule_if_taken": (
            "the comparator's slot arm becomes the sealed KC-S1b rows PLUS "
            f"{SLURP_VALUE_PROJECTION_ID} at threshold {best['threshold']:.2f}, scored "
            "through a registered scorer id that applies it between the parse and the "
            "official prediction file -- the exact shape "
            "slurp-slu-official-projected-v2 already has for labels. OWNER GO REQUIRED; "
            "this read does not re-lock anything"
        ),
        "examples": changed_examples.get(f"tau-{best['threshold']:.2f}", [])[:80],
    }
    write_json(out_dir / "value-projection.json", document)
    summary = dict(document)
    summary.pop("examples")
    summary["sweep"] = [
        {
            "threshold": entry["threshold"],
            "slu_f1": entry["official"]["slu_f1"],
            "delta": entry["delta_vs_baseline"],
            "changed": entry["changed"],
            "pooled_slu_f1_ci90": entry["paired"]["pooled_1000"]["slu_f1_f1"]["ci90_pp"],
            "pooled_saves_harms": [
                entry["paired"]["pooled_1000"]["slu_f1_f1"]["saves"],
                entry["paired"]["pooled_1000"]["slu_f1_f1"]["harms"],
            ],
        }
        for entry in table
    ]
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir", default=str(DEFAULT_OUT_DIR), help="receipt directory"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    decompose = subparsers.add_parser("decompose", help="question 1")
    decompose.add_argument("--score-dir", default=None)
    decompose.set_defaults(func=command_decompose)

    projection = subparsers.add_parser("projection", help="question 2")
    projection.add_argument("--workers", type=int, default=3)
    projection.set_defaults(func=command_projection)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
