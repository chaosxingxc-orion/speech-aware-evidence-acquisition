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

#: Two rule families. ``rule`` is the committed projection alone. ``normalized``
#: adds a NORMALIZATION FLOOR under it: a filler the projection does not move is
#: still emitted in the corpus's own surface convention. The floor is free and
#: needs no inventory, and it exists because the official script lower-cases the
#: gold side and deliberately does not lower-case the prediction side, so a
#: correctly heard span written in title case pays a word distance of 1.0.
PROJECTION_FAMILIES = ("rule", "normalized")


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
# The loss attribution -- shared implementation with historical error surface
# ---------------------------------------------------------------------------
def _match_block(gold, predicted, distance_fn):
    from speech_aware_evidence_acquisition.analysis.slurp_entity_attribution import (
        _match_block as _shared_match_block,
    )

    try:
        return _shared_match_block(gold, predicted, distance_fn)
    except ValueError as error:
        raise SystemExit(str(error)) from error


def attribute_row(gold, predicted):
    from speech_aware_evidence_acquisition.analysis.slurp_entity_attribution import (
        attribute_row as _shared_attribute_row,
    )

    try:
        return _shared_attribute_row(gold, predicted)
    except ValueError as error:
        raise SystemExit(str(error)) from error


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
        SlotEntity,
        parse_slu_response,
    )
    from speech_aware_evidence_acquisition.reproduction.slurp_value_projection import (
        SLURP_VALUE_PROJECTION_ID,
        VALUE_BRANCH_NO_INVENTORY,
        VALUE_BRANCH_TOO_FAR,
        ValueProjection,
        branch_counts,
        load_value_projection_inventory,
        normalize_filler,
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
        plans: list[tuple[str, str | None, float | None]] = [("baseline", None, None)]
        for family in PROJECTION_FAMILIES:
            for threshold in PROJECTION_THRESHOLDS:
                plans.append((f"{family}-tau-{threshold:.2f}", family, threshold))
        for name, family, threshold in plans:
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
                if family is None or threshold is None:
                    projected = entities
                else:
                    projected, outcomes = project_slu_entities(
                        entities, inventory, threshold=threshold, nearest_cache=cache
                    )
                    if family == "normalized":
                        # The normalization FLOOR: a filler the projection left
                        # alone is still emitted in the corpus's own surface
                        # convention (case-folded, whitespace collapsed). The
                        # official script lower-cases the gold side and not the
                        # prediction side, so this half of the repair costs
                        # nothing and needs no inventory at all.
                        projected = tuple(
                            SlotEntity(type=entity.type, filler=normalize_filler(entity.filler))
                            if outcome.branch
                            in (VALUE_BRANCH_TOO_FAR, VALUE_BRANCH_NO_INVENTORY)
                            else entity
                            for entity, outcome in zip(projected, outcomes)
                        )
                        outcomes = tuple(
                            outcome
                            if outcome.branch
                            not in (VALUE_BRANCH_TOO_FAR, VALUE_BRANCH_NO_INVENTORY)
                            else ValueProjection(
                                entity_type=outcome.entity_type,
                                source_filler=outcome.source_filler,
                                projected_filler=normalize_filler(outcome.source_filler),
                                branch=outcome.branch,
                                distance=outcome.distance,
                                changed=normalize_filler(outcome.source_filler)
                                != outcome.source_filler,
                            )
                            for outcome in outcomes
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
            if family is not None:
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
    for family in PROJECTION_FAMILIES:
        for threshold in PROJECTION_THRESHOLDS:
            name = f"{family}-tau-{threshold:.2f}"
            official = official_block(scored[name])
            entry: dict[str, object] = {
                "family": family,
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
    best_name = f"{best['family']}-tau-{best['threshold']:.2f}"
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
        "best_family": best["family"],
        "families": {
            "rule": "the committed rule alone: a filler the projection does not move keeps "
            "its own bytes",
            "normalized": "the same rule over a NORMALIZATION FLOOR -- a filler the "
            "projection does not move is still emitted case-folded with whitespace "
            "collapsed, which is the corpus's own surface convention and needs no "
            "inventory at all",
        },
        "relock_candidate": relock_candidate,
        "relock_rule_if_taken": (
            "the comparator's slot arm becomes the sealed KC-S1b rows PLUS "
            f"{SLURP_VALUE_PROJECTION_ID} at threshold {best['threshold']:.2f} in family "
            f"{best['family']!r}, scored "
            "through a registered scorer id that applies it between the parse and the "
            "official prediction file -- the exact shape "
            "slurp-slu-official-projected-v2 already has for labels. OWNER GO REQUIRED; "
            "this read does not re-lock anything"
        ),
        "examples": changed_examples.get(best_name, [])[:80],
    }
    write_json(out_dir / "value-projection.json", document)
    summary = dict(document)
    summary.pop("examples")
    summary["sweep"] = [
        {
            "family": entry["family"],
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


# ---------------------------------------------------------------------------
# Question 3 -- schema conformance and constrained decoding
# ---------------------------------------------------------------------------


#: The transport and pinned-server seam, read from source. Every entry is
#: ``(path, line span, what it establishes)``; the paths under ``tools/`` and
#: ``common/`` are the PINNED llama.cpp build the runtime receipt names,
#: ``/home/chao/llama.cpp-featcache`` at commit
#: ``04ccc72a2207347ca76161b93fd9d846dd0a8675``.
CONSTRAINED_DECODING_CITATIONS = (
    (
        "src/speech_aware_evidence_acquisition/core/model/request_types.py",
        "33",
        "response_format is one of the exact decoding_params keys the frozen core "
        "accepts, described in its own comment as llama-server's OpenAI-compatible "
        "schema-constrained decoding",
    ),
    (
        "src/speech_aware_evidence_acquisition/core/model/adapter.py",
        "172-197",
        "the adapter validates the wrapper before the transport sees it: json_object "
        "with a mapping schema, or json_schema with a mapping json_schema.schema; any "
        "other type is refused",
    ),
    (
        "src/speech_aware_evidence_acquisition/core/model/transport.py",
        "878-884",
        "every decoding_params key is copied verbatim onto the chat-completions body, "
        "refusing only a key that would collide with the constructed body",
    ),
    (
        "src/speech_aware_evidence_acquisition/rails/controllers.py",
        "531-532",
        "decoding_params['response_format'] = dict(material.response_format) -- the "
        "phase's resolved format becomes the request's decoding parameter",
    ),
    (
        "src/speech_aware_evidence_acquisition/rails/phase_material.py",
        "613-637",
        "resolve_response_formats renders one document per PHASE through "
        "core.base.RESPONSE_FORMATS, from (lock, root, **fill_params) -- there is no "
        "sample argument, so a PER-SAMPLE schema is not reachable through this seam",
    ),
    (
        "src/speech_aware_evidence_acquisition/core/base.py",
        "88-97",
        "RESPONSE_FORMATS is the one registry a config's response_format_id resolves "
        "in, the same one-Registry discipline every other component id uses",
    ),
    (
        "src/speech_aware_evidence_acquisition/rails/a2t_response_schema.py",
        "449-524, 636-717",
        "the precedent: audio2tool_selection_response_format and "
        "audio2tool_outer_call_array_response_format build real exact-name enum schemas "
        "over the pinned 152-tool registry",
    ),
    (
        "tools/server/server-common.cpp (pinned llama.cpp 04ccc72a)",
        "1280-1300",
        "the server reads json_schema and grammar off the request body, refuses both at "
        "once, and maps an OpenAI response_format of type json_object or json_schema "
        "onto that same json_schema",
    ),
    (
        "tools/server/server-schema.cpp (pinned llama.cpp 04ccc72a)",
        "246-277",
        "the json_schema request field carries grammar as an ALIAS; a schema is "
        "converted with json_schema_to_grammar(schema) at :256 and installed as "
        "COMMON_GRAMMAR_TYPE_OUTPUT_FORMAT, and a raw GBNF grammar string is installed "
        "as COMMON_GRAMMAR_TYPE_USER",
    ),
    (
        "common/json-schema-to-grammar.cpp (pinned llama.cpp 04ccc72a)",
        "1158",
        "json_schema_to_grammar itself -- the conversion is in the build, not a "
        "server-side approximation",
    ),
)


def command_schema(args: argparse.Namespace) -> int:
    import inspect

    from speech_aware_evidence_acquisition.core.base import RESPONSE_FORMATS
    from speech_aware_evidence_acquisition.core.model.request_types import (
        ALLOWED_DECODING_KEYS,
    )
    from speech_aware_evidence_acquisition.data.slurp import (
        load_slurp_intent_slot_schema,
        load_slurp_ontology,
        load_slurp_split,
    )
    from speech_aware_evidence_acquisition.rails.phase_material import (
        resolve_response_formats,
    )
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (
        parse_slu_response,
    )

    lock, root, lock_path = resolve_lock_and_root()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    roster = roster_sample_ids(REPO_ROOT / DEV1000_CONFIG)
    gold = {record.sample_id: record for record in load_slurp_split(lock, root, "devel")}
    texts = read_sealed_outputs(sealed_outputs_path(root, KC_S1B_RUN, KC_S1B_ATTEMPT))
    ontology = load_slurp_ontology(lock, root)
    schema = load_slurp_intent_slot_schema(lock, root)
    vocabulary = set(ontology.entity_types)
    full_block_types = {
        entity_type
        for profile in schema.intents.values()
        for entity_type in profile.entity_types
    }

    fit_document = read_json(REPO_ROOT / KC_S1B_PROMPT_FIT)
    fit_rows = {
        row["sample_id"]: row for row in fit_document["rows"] if row["cell_id"] == "kc-s1b"
    }
    blocks = fit_document["schema_blocks"]
    if (
        blocks["full_schema_fallback_rows"]
        != KC_S1B_SCHEMA_ANCHORS["full_schema_fallback_rows"]
        or blocks["distinct_intents_used"] != KC_S1B_SCHEMA_ANCHORS["distinct_intents_used"]
    ):
        raise SystemExit("the prompt-fit receipt no longer reproduces its own block accounting")
    fallback_ids = set(blocks["full_schema_fallback_sample_ids"])
    if len(fallback_ids) != KC_S1B_SCHEMA_ANCHORS["full_schema_fallback_rows"]:
        raise SystemExit("the fallback id list disagrees with its own count")

    rows: dict[str, dict] = {}
    counts = {
        "unparsed": 0,
        "fenced_or_prefixed_text": 0,
        "illegal_type_for_block": 0,
        "unknown_type": 0,
        "duplicate_type": 0,
        "fully_conforming": 0,
    }
    mention_counts = {"total": 0, "illegal_for_block": 0, "unknown": 0}
    illegal_by_type: Counter[str] = Counter()
    gold_duplicate_rows = 0
    for sample_id in roster:
        text = texts[sample_id]
        scenario, action, entities, parsed = parse_slu_response(text)
        fit = fit_rows[sample_id]
        fallback = bool(fit["schema_full_fallback"])
        if fallback != (sample_id in fallback_ids):
            raise SystemExit(f"{sample_id}: prompt-fit row and fallback id list disagree")
        block_types = (
            full_block_types
            if fallback
            else set(schema.intents[fit["schema_block_intent"]].entity_types)
        )
        types = [entity.type for entity in entities]
        illegal = [t for t in types if t not in block_types]
        unknown = [t for t in types if t not in vocabulary]
        duplicated = sorted({t for t, n in Counter(types).items() if n > 1})
        gold_types = [entity.type for entity in gold[sample_id].entities]
        if len(set(gold_types)) != len(gold_types):
            gold_duplicate_rows += 1
        mention_counts["total"] += len(types)
        mention_counts["illegal_for_block"] += len(illegal)
        mention_counts["unknown"] += len(unknown)
        for entity_type in illegal:
            illegal_by_type[entity_type] += 1
        if not parsed:
            counts["unparsed"] += 1
        if text.strip() != text.strip().strip("`") or "```" in text:
            counts["fenced_or_prefixed_text"] += 1
        if illegal:
            counts["illegal_type_for_block"] += 1
        if unknown:
            counts["unknown_type"] += 1
        if duplicated:
            counts["duplicate_type"] += 1
        if parsed and not illegal and not duplicated:
            counts["fully_conforming"] += 1
        rows[sample_id] = {
            "parsed": parsed,
            "fallback": fallback,
            "block_intent": fit["schema_block_intent"],
            "types": types,
            "illegal": sorted(set(illegal)),
            "unknown": sorted(set(unknown)),
            "duplicated": duplicated,
            "entities": entities,
            "scenario": scenario,
            "action": action,
        }

    violating = sorted(
        sample_id
        for sample_id, row in rows.items()
        if row["illegal"] or not row["parsed"] or row["duplicated"]
    )
    conforming = sorted(set(roster) - set(violating))

    # An "illegal" type is one the row's per-intent BLOCK did not list, not one
    # SLURP does not have: the block keeps types holding at least 2 % of the
    # intent's TRAIN slot mass, so a rare but REAL type is illegal by
    # construction. This counts how often the model was right anyway, and how
    # much gold a hard constraint to the block would put out of reach.
    illegal_but_in_gold = 0
    gold_mentions_outside_block = 0
    unparsed_ids = sorted(sid for sid, row in rows.items() if not row["parsed"])
    unparsed_gold_mentions = 0
    for sample_id in roster:
        row = rows[sample_id]
        gold_pairs = {
            (entity.type, entity.filler) for entity in gold[sample_id].entities
        }
        illegal_types = set(row["illegal"])
        for entity in row["entities"]:
            if entity.type in illegal_types and (entity.type, entity.filler) in gold_pairs:
                illegal_but_in_gold += 1
        block_types = (
            full_block_types
            if row["fallback"]
            else set(schema.intents[row["block_intent"]].entity_types)
        )
        gold_mentions_outside_block += sum(
            1 for entity in gold[sample_id].entities if entity.type not in block_types
        )
        if not row["parsed"]:
            unparsed_gold_mentions += len(gold[sample_id].entities)

    workdir = Path(tempfile.mkdtemp(prefix="saea-mf9-schema-", dir=str(root)))
    try:
        baseline_rows = []
        suppressed_rows = []
        unknown_suppressed_rows = []
        for sample_id in roster:
            row = rows[sample_id]
            if not row["parsed"]:
                for bucket in (baseline_rows, suppressed_rows, unknown_suppressed_rows):
                    bucket.append({"sample_id": sample_id, "text": texts[sample_id]})
                continue
            baseline_rows.append(
                {
                    "sample_id": sample_id,
                    "text": prediction_text(row["scenario"], row["action"], row["entities"]),
                }
            )
            illegal_types = set(row["illegal"])
            suppressed_rows.append(
                {
                    "sample_id": sample_id,
                    "text": prediction_text(
                        row["scenario"],
                        row["action"],
                        [e for e in row["entities"] if e.type not in illegal_types],
                    ),
                }
            )
            unknown_types = set(row["unknown"])
            unknown_suppressed_rows.append(
                {
                    "sample_id": sample_id,
                    "text": prediction_text(
                        row["scenario"],
                        row["action"],
                        [e for e in row["entities"] if e.type not in unknown_types],
                    ),
                }
            )
        paths = {
            "baseline": write_outputs(baseline_rows, workdir / "baseline.outputs.jsonl"),
            "illegal_suppressed": write_outputs(
                suppressed_rows, workdir / "illegal-suppressed.outputs.jsonl"
            ),
            "unknown_suppressed": write_outputs(
                unknown_suppressed_rows, workdir / "unknown-suppressed.outputs.jsonl"
            ),
        }
        with ThreadPoolExecutor(max_workers=3) as pool:
            scored = dict(
                zip(
                    paths,
                    pool.map(lambda path: score_outputs(path, lock, root), paths.values()),
                )
            )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    baseline_official = official_block(scored["baseline"])
    assert_published(baseline_official, KC_S1B_PUBLISHED, "KC-S1b re-emitted (schema arm)")
    baseline_samples = by_sample(scored["baseline"])

    def slu_over(ids, samples):
        tp = sum(samples[sid]["slu_f1_word_tp"] + samples[sid]["slu_f1_char_tp"] for sid in ids)
        fp = sum(samples[sid]["slu_f1_word_fp"] + samples[sid]["slu_f1_char_fp"] for sid in ids)
        fn = sum(samples[sid]["slu_f1_word_fn"] + samples[sid]["slu_f1_char_fn"] for sid in ids)
        return {
            "n": len(ids),
            "slu_f1": round(100.0 * _f1(tp, fp, fn), 2),
            "loss_mass": round(fp + fn, 3),
        }

    def stratum_of(sample_id: str) -> str:
        return gold[sample_id].scenario

    declared = []
    for path in sorted((REPO_ROOT / "configs/baseline").glob("slurp-*.json")):
        body = path.read_text(encoding="utf-8")
        if "response_format_id" in body and '"response_format_id": null' not in body:
            declared.append(str(path.relative_to(REPO_ROOT)).replace("\\", "/"))

    document = {
        "schema": "saea-slurp-mf9-schema-conformance-v1",
        "row_id": ROW_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "contacts": {
            "model": 0,
            "gpu_hours": 0,
            "tool": 0,
            "embedding": 0,
            "network": 0,
            "audio_decode": 0,
        },
        "sources": {
            "umbrella_lock": str(lock_path),
            "sealed_outputs_sha256": sha256_file(
                sealed_outputs_path(root, KC_S1B_RUN, KC_S1B_ATTEMPT)
            ),
            "prompt_fit_receipt": KC_S1B_PROMPT_FIT,
            "intent_slot_schema_content_hash": schema.content_hash(),
        },
        "identity_anchors": {
            "prompt_fit_schema_blocks": KC_S1B_SCHEMA_ANCHORS,
            "baseline_reemitted": baseline_official,
        },
        "vocabulary": {
            "slurp_entity_types": len(vocabulary),
            "types_listed_by_at_least_one_intent_block": len(full_block_types),
            "full_schema_fallback_rows": len(fallback_ids),
        },
        "conformance": {
            "rows": counts,
            "mentions": mention_counts,
            "rows_fully_conforming_pct": percent(counts["fully_conforming"], len(roster)),
            "illegal_mentions_by_type": dict(illegal_by_type.most_common()),
            "gold_rows_carrying_two_mentions_of_one_type": gold_duplicate_rows,
        },
        "what_the_violating_rows_lose": {
            "violating": slu_over(violating, baseline_samples),
            "conforming": slu_over(conforming, baseline_samples),
            "unparsed_sample_ids": unparsed_ids,
            "unparsed_gold_mentions": unparsed_gold_mentions,
        },
        "the_block_is_not_a_superset_of_the_gold": {
            "note": (
                "a per-intent block lists the types holding at least 2 % of that intent's "
                "TRAIN slot mass, so a rare but REAL type is 'illegal' by construction. "
                "Constraining decoding to the block would therefore put reachable gold out "
                "of reach, and that cost is measured rather than assumed"
            ),
            "illegal_mentions_that_matched_gold_exactly": illegal_but_in_gold,
            "gold_mentions_whose_type_the_block_did_not_list": gold_mentions_outside_block,
        },
        "suppression_counterfactuals": {
            "note": (
                "a scoring-side LOWER bound on what a grammar constraint buys: the "
                "constraint would force a LEGAL type rather than delete the mention, so "
                "deleting it can only under-state the gain on recall while over-stating "
                "it on precision. Reported as a bound, never as the module's value"
            ),
            "baseline": baseline_official,
            "illegal_for_block_suppressed": official_block(scored["illegal_suppressed"]),
            "unknown_type_suppressed": official_block(scored["unknown_suppressed"]),
            "paired_illegal_suppressed_pooled": contrast_block(
                baseline_samples,
                by_sample(scored["illegal_suppressed"]),
                sorted(roster),
                stratum_of,
            ),
        },
        "constrained_decoding": {
            "verdict": (
                "AVAILABLE AND WIRED END TO END for a PHASE-LEVEL, sample-independent "
                "schema, and turning it on is one config key: a phase's "
                "response_format_id. NOT reachable for a PER-SAMPLE schema, which is what "
                "KC-S1b's per-intent block would need -- resolve_response_formats renders "
                "one document per phase from (lock, root, **fill_params) and never sees a "
                "sample"
            ),
            "response_format_in_allowed_decoding_keys": "response_format"
            in ALLOWED_DECODING_KEYS,
            "registered_response_format_ids": sorted(RESPONSE_FORMATS.names()),
            "resolve_response_formats_parameters": sorted(
                inspect.signature(resolve_response_formats).parameters
            ),
            "slurp_configs_declaring_a_response_format": declared,
            "citations": [
                {"path": path, "lines": lines, "establishes": what}
                for path, lines, what in CONSTRAINED_DECODING_CITATIONS
            ],
            "what_is_missing_for_a_per_intent_schema": (
                "one seam, the same shape rails.phase_material.PHASE_STATE_FILLS already "
                "has: a per-sample response format resolved beside the per-sample state "
                "fill. Today PhaseMaterial.response_format is filled from a phase-level "
                "mapping inside build_material_for_phase; a PHASE_RESPONSE_FILLS registry "
                "keyed the same way would put a per-row schema on the wire with no change "
                "to the transport, the adapter, or the server"
            ),
        },
    }
    write_json(out_dir / "schema-conformance.json", document)
    print(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


# ---------------------------------------------------------------------------
# Question 4 -- knowledge headroom for VALUES
# ---------------------------------------------------------------------------


def recording_filename(sample_id: str) -> str:
    """``slurp:devel:000011:audio-1497266596`` to ``audio-1497266596.flac``."""

    parts = sample_id.split(":")
    if len(parts) != 4 or not parts[3]:
        raise SystemExit(f"not a SLURP sample id: {sample_id!r}")
    return f"{parts[3]}.flac"


def load_dimension_vectors(path: Path, dimension: str = "content"):
    """``(ids, matrix)`` from a sealed ``{"id", "vectors": {...}}`` JSONL.

    The sealed KU-S3 vector files carry one named dimension per row, which is
    a different interchange shape from ``analysis.slurp_retrieval_key_audit``'s
    single-``vector`` schema; everything downstream (normalisation, cosine,
    top-k) is that module's own code.
    """

    import numpy as np

    ids: list[str] = []
    rows: list[list[float]] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            record = json.loads(stripped)
            identity = record.get("id")
            vectors = record.get("vectors")
            if not isinstance(identity, str) or not isinstance(vectors, Mapping):
                raise SystemExit(f"{path} line {line_no}: malformed sealed vector row")
            vector = vectors.get(dimension)
            if not isinstance(vector, list) or not vector:
                raise SystemExit(f"{path} line {line_no}: no {dimension!r} vector")
            ids.append(identity)
            rows.append(vector)
    if len(set(ids)) != len(ids):
        raise SystemExit(f"{path}: duplicate ids")
    return tuple(ids), np.asarray(rows, dtype=np.float64)


def command_headroom(args: argparse.Namespace) -> int:
    from speech_aware_evidence_acquisition.analysis.slurp_retrieval_key_audit import (
        cosine_matrix,
        top_k_indices,
    )
    from speech_aware_evidence_acquisition.data.slurp import (
        _governed_roots,
        _slurp_speaker_index,
        load_slurp_split,
        load_slurp_train_material,
    )
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (
        SlotEntity,
        parse_slu_response,
    )
    from speech_aware_evidence_acquisition.reproduction.slurp_value_projection import (
        build_value_projection_inventory,
        normalize_filler,
    )

    lock, root, lock_path = resolve_lock_and_root()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    roster = roster_sample_ids(REPO_ROOT / DEV1000_CONFIG)
    pops = populations(roster)
    gold = {record.sample_id: record for record in load_slurp_split(lock, root, "devel")}
    train = load_slurp_train_material(lock, root)
    inventory = build_value_projection_inventory(train)
    _, _, metadata_dir = _governed_roots(lock, root)
    speaker_of_file = _slurp_speaker_index(metadata_dir)

    # --- (a) does TRAIN already carry the DEV gold VALUE? ------------------
    per_type: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "gold_mentions": 0.0,
            "verbatim_same_type": 0.0,
            "verbatim_any_type": 0.0,
            "distinct_gold_values": 0.0,
            "distinct_verbatim": 0.0,
        }
    )
    any_type_index: dict[str, set[str]] = defaultdict(set)
    for (entity_type, filler) in inventory.counts:
        any_type_index[filler].add(entity_type)
    distinct_gold: dict[str, set[str]] = defaultdict(set)
    distinct_hit: dict[str, set[str]] = defaultdict(set)
    for sample_id in roster:
        for entity in gold[sample_id].entities:
            value = normalize_filler(entity.filler)
            row = per_type[entity.type]
            row["gold_mentions"] += 1
            distinct_gold[entity.type].add(value)
            if value in inventory.fillers.get(entity.type, ()) or (
                entity.type in any_type_index.get(value, set())
            ):
                row["verbatim_same_type"] += 1
                distinct_hit[entity.type].add(value)
            if value in any_type_index:
                row["verbatim_any_type"] += 1
    for entity_type, row in per_type.items():
        row["distinct_gold_values"] = float(len(distinct_gold[entity_type]))
        row["distinct_verbatim"] = float(len(distinct_hit[entity_type]))

    state = read_json(REPO_ROOT / MF8_STATE_INVENTORY)
    partition = _mf8_type_partition(state)

    # --- (b) the KU-S3 retrieved top-5 ceiling -----------------------------
    query_ids, queries = load_dimension_vectors(
        root / SEALED_VECTOR_DIR / "query-vectors-speech.jsonl"
    )
    facet_ids, keys = load_dimension_vectors(root / SEALED_VECTOR_DIR / "facet-vectors.jsonl")
    entities_by_utterance = {
        utterance.utterance_id: tuple(
            (entity.type, entity.filler) for entity in utterance.entities
        )
        for utterance in train
    }
    # ``rails.knowledge_build`` mints a content facet as
    # ``facet:content:{KbRow.utterance_id}``, and ``KbRow.utterance_id`` is
    # ``SlurpTrainMaterial.utterance_id``, which is the bare ``str(slurp_id)``
    # (``data.slurp.load_slurp_train_material``). So the suffix is that id
    # verbatim, and the join is exact rather than reformatted.
    key_entities = []
    for facet_id in facet_ids:
        utterance_id = facet_id.rsplit(":", 1)[-1]
        if utterance_id not in entities_by_utterance:
            raise SystemExit(f"sealed facet {facet_id!r} has no TRAIN utterance")
        key_entities.append(set(entities_by_utterance[utterance_id]))
    query_position = {sample_id: index for index, sample_id in enumerate(query_ids)}
    if any(sample_id not in query_position for sample_id in roster):
        raise SystemExit("the sealed speech query set does not cover the DEV-1000 roster")

    order = [query_position[sample_id] for sample_id in roster]
    scores = cosine_matrix(queries[order], keys)
    neighbours = top_k_indices(scores, args.k)

    retrieved: dict[str, set[tuple[str, str]]] = {}
    recall_rows: dict[str, float] = {}
    per_type_retrieved: dict[str, dict[str, float]] = defaultdict(
        lambda: {"gold_mentions": 0.0, "in_retrieved": 0.0}
    )
    for position, sample_id in enumerate(roster):
        available: set[tuple[str, str]] = set()
        for index in neighbours[position]:
            available |= key_entities[int(index)]
        retrieved[sample_id] = available
        gold_pairs = {(entity.type, entity.filler) for entity in gold[sample_id].entities}
        if gold_pairs:
            recall_rows[sample_id] = len(gold_pairs & available) / len(gold_pairs)
        for entity in gold[sample_id].entities:
            bucket = per_type_retrieved[entity.type]
            bucket["gold_mentions"] += 1
            if (entity.type, entity.filler) in available:
                bucket["in_retrieved"] += 1

    filler_recall = {
        name: round(
            100.0
            * sum(recall_rows[sid] for sid in ids if sid in recall_rows)
            / max(1, sum(1 for sid in ids if sid in recall_rows)),
            2,
        )
        for name, ids in pops.items()
    }
    for name, expected in MF7B_FILLER_RECALL_ANCHORS.items():
        if abs(filler_recall[name] - expected) > 0.005:
            raise SystemExit(
                f"IDENTITY ANCHOR FAILED: filler recall@{args.k} on {name} is "
                f"{filler_recall[name]}, MF-7b published {expected}"
            )

    # --- the retrieved-filler oracle ceiling -------------------------------
    texts = read_sealed_outputs(sealed_outputs_path(root, KC_S1B_RUN, KC_S1B_ATTEMPT))
    workdir = Path(tempfile.mkdtemp(prefix="saea-mf9-headroom-", dir=str(root)))
    try:
        baseline_rows = []
        oracle_rows = []
        added = 0
        for sample_id in roster:
            scenario, action, entities, parsed = parse_slu_response(texts[sample_id])
            if not parsed:
                baseline_rows.append({"sample_id": sample_id, "text": texts[sample_id]})
                oracle_rows.append({"sample_id": sample_id, "text": texts[sample_id]})
                continue
            baseline_rows.append(
                {"sample_id": sample_id, "text": prediction_text(scenario, action, entities)}
            )
            have = {(entity.type, entity.filler) for entity in entities}
            extra = [
                SlotEntity(type=entity.type, filler=entity.filler)
                for entity in gold[sample_id].entities
                if (entity.type, entity.filler) in retrieved[sample_id]
                and (entity.type, entity.filler) not in have
            ]
            added += len(extra)
            oracle_rows.append(
                {
                    "sample_id": sample_id,
                    "text": prediction_text(scenario, action, list(entities) + extra),
                }
            )
        paths = {
            "baseline": write_outputs(baseline_rows, workdir / "baseline.outputs.jsonl"),
            "retrieved_oracle": write_outputs(
                oracle_rows, workdir / "retrieved-oracle.outputs.jsonl"
            ),
        }
        with ThreadPoolExecutor(max_workers=2) as pool:
            scored = dict(
                zip(
                    paths,
                    pool.map(lambda path: score_outputs(path, lock, root), paths.values()),
                )
            )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    baseline_official = official_block(scored["baseline"])
    assert_published(baseline_official, KC_S1B_PUBLISHED, "KC-S1b re-emitted (headroom arm)")

    # --- (c) same-speaker slot exemplars -----------------------------------
    speaker_types: dict[str, Counter] = defaultdict(Counter)
    for utterance in train:
        types = {entity.type for entity in utterance.entities}
        speakers = {recording.speaker_id for recording in utterance.recordings}
        for speaker in speakers:
            for entity_type in types:
                speaker_types[speaker][entity_type] += 1

    thresholds = (1, 3, 5)
    pair_counts = {f">={threshold}": 0 for threshold in thresholds}
    row_counts = {f">={threshold}": 0 for threshold in thresholds}
    pairs_total = 0
    rows_with_gold = 0
    rows_without_speaker = 0
    per_type_speaker: dict[str, dict[str, float]] = defaultdict(
        lambda: {"pairs": 0.0, **{f">={t}": 0.0 for t in thresholds}}
    )
    for sample_id in roster:
        speaker = speaker_of_file.get(recording_filename(sample_id))
        gold_types = sorted({entity.type for entity in gold[sample_id].entities})
        if not gold_types:
            continue
        rows_with_gold += 1
        if speaker is None:
            rows_without_speaker += 1
        available = speaker_types.get(speaker or "", Counter())
        per_row = {}
        for entity_type in gold_types:
            pairs_total += 1
            count = int(available.get(entity_type, 0))
            per_row[entity_type] = count
            bucket = per_type_speaker[entity_type]
            bucket["pairs"] += 1
            for threshold in thresholds:
                if count >= threshold:
                    pair_counts[f">={threshold}"] += 1
                    bucket[f">={threshold}"] += 1
        for threshold in thresholds:
            if all(count >= threshold for count in per_row.values()):
                row_counts[f">={threshold}"] += 1

    ranked = sorted(per_type.items(), key=lambda item: -item[1]["gold_mentions"])
    type_table = [
        {
            "entity_type": entity_type,
            "gold_mentions": int(values["gold_mentions"]),
            "distinct_gold_values": int(values["distinct_gold_values"]),
            "verbatim_in_train_same_type": int(values["verbatim_same_type"]),
            "verbatim_share_pct": percent(values["verbatim_same_type"], values["gold_mentions"]),
            "distinct_values_in_train": int(values["distinct_verbatim"]),
            "train_surface_forms": len(inventory.fillers.get(entity_type, ())),
            "mf8_partition": partition.get(entity_type, "unclassified"),
            "in_retrieved_top_k": int(per_type_retrieved[entity_type]["in_retrieved"]),
            "retrieved_share_pct": percent(
                per_type_retrieved[entity_type]["in_retrieved"], values["gold_mentions"]
            ),
            "same_speaker_pairs_ge_1_pct": percent(
                per_type_speaker[entity_type][">=1"], per_type_speaker[entity_type]["pairs"]
            ),
            "same_speaker_pairs_ge_5_pct": percent(
                per_type_speaker[entity_type][">=5"], per_type_speaker[entity_type]["pairs"]
            ),
        }
        for entity_type, values in ranked
    ]

    partition_totals = {"standing": {"gold": 0, "verbatim": 0}, "utterance-local": {"gold": 0, "verbatim": 0}, "unclassified": {"gold": 0, "verbatim": 0}}
    for entity_type, values in per_type.items():
        bucket = partition_totals[partition.get(entity_type, "unclassified")]
        bucket["gold"] += int(values["gold_mentions"])
        bucket["verbatim"] += int(values["verbatim_same_type"])

    document = {
        "schema": "saea-slurp-mf9-value-headroom-v1",
        "row_id": ROW_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "contacts": {
            "model": 0,
            "gpu_hours": 0,
            "tool": 0,
            "embedding": 0,
            "network": 0,
            "audio_decode": 0,
        },
        "sources": {
            "umbrella_lock": str(lock_path),
            "train_inventory": inventory.as_json(),
            "sealed_query_vectors": str(root / SEALED_VECTOR_DIR / "query-vectors-speech.jsonl"),
            "sealed_facet_vectors": str(root / SEALED_VECTOR_DIR / "facet-vectors.jsonl"),
            "mf8_state_inventory": MF8_STATE_INVENTORY,
        },
        "identity_anchors": {
            "filler_recall_at_k": filler_recall,
            "mf7b_published": MF7B_FILLER_RECALL_ANCHORS,
            "baseline_reemitted": baseline_official,
        },
        "train_verbatim_coverage": {
            "gold_mentions": int(sum(v["gold_mentions"] for v in per_type.values())),
            "verbatim_same_type": int(sum(v["verbatim_same_type"] for v in per_type.values())),
            "verbatim_any_type": int(sum(v["verbatim_any_type"] for v in per_type.values())),
            "share_same_type_pct": percent(
                sum(v["verbatim_same_type"] for v in per_type.values()),
                sum(v["gold_mentions"] for v in per_type.values()),
            ),
            "by_mf8_partition": partition_totals,
        },
        "retrieved_top_k": {
            "k": args.k,
            "key": "q-speech-nemotron (the sealed KU-S3 speech query), cosine over the "
            "11,514 TRAIN content facets",
            "filler_recall_pct": filler_recall,
            "gold_mentions_in_retrieved_union": int(
                sum(v["in_retrieved"] for v in per_type_retrieved.values())
            ),
            "oracle_added_mentions": added,
            "oracle_ceiling": official_block(scored["retrieved_oracle"]),
            "oracle_note": (
                "an UPPER BOUND, and a generous one: the arm keeps every mention it "
                "already made and additionally emits every gold value the retrieval "
                "supplied. A real consumption cell has to find those values in the "
                "supplied block and no mechanism reaches this"
            ),
        },
        "same_speaker_slot_exemplars": {
            "unit": "one (DEV row, gold slot TYPE) pair; the count is TRAIN utterances by "
            "that row's own speaker carrying that slot type",
            "rows_with_at_least_one_gold_entity": rows_with_gold,
            "rows_whose_speaker_is_absent_from_train": rows_without_speaker,
            "pairs": pairs_total,
            "pairs_at_threshold": pair_counts,
            "pairs_at_threshold_pct": {
                key: percent(value, pairs_total) for key, value in pair_counts.items()
            },
            "rows_where_every_gold_type_reaches": row_counts,
            "rows_where_every_gold_type_reaches_pct": {
                key: percent(value, rows_with_gold) for key, value in row_counts.items()
            },
        },
        "per_entity_type": type_table,
    }
    write_json(out_dir / "value-headroom.json", document)
    summary = dict(document)
    summary["per_entity_type"] = type_table[:15]
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _mf8_type_partition(state: Mapping[str, object]) -> dict[str, str]:
    """MF-8's own standing-state / utterance-local split of the 55 entity types.

    Read out of that audit's committed receipt rather than re-derived, so the
    two notes cannot drift apart. MF-8 fixed the partition BEFORE any count was
    read and names it ``state_bearing_types`` (35 types the assistant can
    legitimately HOLD) against ``other_types`` (20 the utterance itself says);
    this audit only reuses those two lists.
    """

    inventory = state.get("device_and_entity_inventory")
    if not isinstance(inventory, Mapping):
        raise SystemExit(f"{MF8_STATE_INVENTORY} carries no device_and_entity_inventory")
    standing = inventory.get("state_bearing_types")
    local = inventory.get("other_types")
    if not isinstance(standing, Mapping) or not isinstance(local, Mapping):
        raise SystemExit(
            f"{MF8_STATE_INVENTORY} carries no state_bearing_types / other_types partition"
        )
    if len(standing) != int(inventory["state_bearing_type_count"]) or len(local) != int(
        inventory["other_type_count"]
    ):
        raise SystemExit(f"{MF8_STATE_INVENTORY}: the partition disagrees with its own counts")
    out = {str(name): "standing" for name in standing}
    out.update({str(name): "utterance-local" for name in local})
    if len(out) != len(standing) + len(local):
        raise SystemExit(f"{MF8_STATE_INVENTORY}: a type is in both halves of the partition")
    return out


# ---------------------------------------------------------------------------
# Question 5 -- the priced improvement ladder
# ---------------------------------------------------------------------------


#: KC-S1b's own realized cost, from its verdict's section 9: 1,000 contacts in
#: 735.9 s for about 0.20 GPU-h. Every module below is priced against it,
#: because every module below is one contact per row on the same geometry.
KC_S1B_COST = {"contacts": 1000, "gpu_hours": 0.20, "audio_seconds": 2884.7937}

#: The published SLURP lines this ladder is measured against
#: (umbrella `published-baselines.md`, SLURP section). Every one is the official
#: TEST split and a natural mixture; DEV-1000 is a scenario-stratified dev
#: roster, so NONE of these is a like-for-like target and none is claimed as one.
PUBLISHED_SLURP_LINES = {
    "trained pipelines (2020 paper)": [69.5, 70.8],
    "CTI": 71.1,
    "SFT Qwen2-Audio-7B": 76.75,
    "WHISMA zero-shot": 63.3,
    "WHISMA supervised reference": 69.9,
    "NLU over gold transcripts": 78.19,
    "ChatGPT over oracle transcripts (slot F1, a DIFFERENT metric)": [12.0, 13.0],
}


def command_ladder(args: argparse.Namespace) -> int:
    from speech_aware_evidence_acquisition.data.slurp import (
        load_slurp_intent_slot_schema,
        load_slurp_split,
    )
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (
        parse_slu_response,
    )
    from speech_aware_evidence_acquisition.reproduction.slurp_value_projection import (
        VALUE_BRANCH_NO_INVENTORY,
        VALUE_BRANCH_TOO_FAR,
        load_value_projection_inventory,
        project_slu_entities,
    )

    lock, root, lock_path = resolve_lock_and_root()
    out_dir = Path(args.out_dir)
    decomposition = read_json(out_dir / "loss-decomposition.json")
    projection = read_json(out_dir / "value-projection.json")
    conformance = read_json(out_dir / "schema-conformance.json")
    headroom = read_json(out_dir / "value-headroom.json")

    tp = float(decomposition["corpus"]["true_positive_mass"])
    mass = float(decomposition["corpus"]["loss_mass"])
    base_slu = float(decomposition["corpus"]["slu_f1"])

    def ceiling(delta_tp: float, delta_mass: float) -> float:
        remaining = mass - delta_mass
        return round(100.0 * _f1(tp + delta_tp, remaining / 2.0, remaining / 2.0), 2)

    # --- the judges, and what they flag -----------------------------------
    roster = roster_sample_ids(REPO_ROOT / DEV1000_CONFIG)
    gold = {record.sample_id: record for record in load_slurp_split(lock, root, "devel")}
    texts = read_sealed_outputs(sealed_outputs_path(root, KC_S1B_RUN, KC_S1B_ATTEMPT))
    inventory = load_value_projection_inventory(lock, root)
    schema = load_slurp_intent_slot_schema(lock, root)
    fit_rows = {
        row["sample_id"]: row
        for row in read_json(REPO_ROOT / KC_S1B_PROMPT_FIT)["rows"]
        if row["cell_id"] == "kc-s1b"
    }
    full_block_types = {
        entity_type
        for profile in schema.intents.values()
        for entity_type in profile.entity_types
    }

    cache: dict[tuple[str, str], tuple[str, float] | None] = {}
    flags: dict[str, set[str]] = {
        "silent": set(),
        "schema_violating": set(),
        "value_suspect": set(),
    }
    missing_by_flag: dict[str, int] = {}
    for sample_id in roster:
        _, _, entities, parsed = parse_slu_response(texts[sample_id])
        fit = fit_rows[sample_id]
        block_types = (
            full_block_types
            if bool(fit["schema_full_fallback"])
            else set(schema.intents[fit["schema_block_intent"]].entity_types)
        )
        if parsed and not entities:
            flags["silent"].add(sample_id)
        types = [entity.type for entity in entities]
        if (
            not parsed
            or any(entity_type not in block_types for entity_type in types)
            or len(set(types)) != len(types)
        ):
            flags["schema_violating"].add(sample_id)
        if entities:
            _, outcomes = project_slu_entities(
                entities, inventory, threshold=args.flag_threshold, nearest_cache=cache
            )
            if any(
                outcome.branch in (VALUE_BRANCH_TOO_FAR, VALUE_BRANCH_NO_INVENTORY)
                for outcome in outcomes
            ):
                flags["value_suspect"].add(sample_id)

    flags["any"] = flags["silent"] | flags["schema_violating"] | flags["value_suspect"]

    # The gold mentions a re-ask on each flagged set could in principle recover:
    # a gold mention on a flagged row that the arm did not match at all.
    unmatched_gold_rows: dict[str, int] = {}
    for sample_id in roster:
        _, _, entities, _ = parse_slu_response(texts[sample_id])
        have = Counter(entity.type for entity in entities)
        unmatched = 0
        for entity in gold[sample_id].entities:
            if have[entity.type] > 0:
                have[entity.type] -= 1
            else:
                unmatched += 1
        unmatched_gold_rows[sample_id] = unmatched
    productive_by_flag: dict[str, int] = {}
    for name, ids in flags.items():
        missing_by_flag[name] = sum(unmatched_gold_rows[sid] for sid in ids)
        productive_by_flag[name] = sum(1 for sid in ids if unmatched_gold_rows[sid] > 0)
    rows_with_no_gold = sum(1 for sid in roster if not gold[sid].entities)
    silent_with_no_gold = sum(1 for sid in flags["silent"] if not gold[sid].entities)

    total_missing = sum(unmatched_gold_rows.values())
    if total_missing != int(decomposition["categories"]["missing"]["count"]) + int(
        decomposition["categories"]["type_swap"]["count"]
    ):
        raise SystemExit(
            "the flag read's unmatched-gold count does not agree with the decomposition"
        )

    best = next(
        entry
        for entry in projection["sweep"]
        if entry["family"] == projection["best_family"]
        and abs(float(entry["threshold"]) - float(projection["best_threshold"])) < 1e-9
    )

    contacts_per_row = {
        "intent_narrowing": 1.0,
        "value_projection": 0.0,
        "constrained_decoding": 1.0,
        "retrieved_fillers": 1.0,
        "same_speaker_exemplars": 1.0,
        "targeted_reask": round(len(flags["any"]) / len(roster), 3),
    }

    def gpu_hours(rate: float) -> float:
        return round(KC_S1B_COST["gpu_hours"] * rate, 3)

    rungs = [
        {
            "rung": 1,
            "module": "value projection (question 2)",
            "what_it_is": (
                "a deterministic scoring-side post-processor over the SEALED rows -- no "
                "contact, no GPU, no flight"
            ),
            "measured_not_ceiling": True,
            "slu_f1": best["official"]["slu_f1"],
            "gain": best["delta_vs_baseline"]["slu_f1"],
            "paired_ci90_new500": best["paired"]["new500"]["slu_f1_f1"]["ci90_pp"],
            "contacts": 0,
            "gpu_hours": 0.0,
            "gain_per_gpu_hour": None,
            "status": (
                "MEASURED. Clears its own CI bar but NOT the 1-point bar this audit set "
                "for a re-lock candidate"
                if not projection["relock_candidate"]
                else "MEASURED and clears the re-lock bar; OWNER GO REQUIRED"
            ),
        },
        {
            "rung": 2,
            "module": "constrained decoding, structure + 55-type enum (question 3)",
            "what_it_is": "one config key on the slots phase: `response_format_id`",
            "measured_not_ceiling": False,
            "slu_f1_ceiling": ceiling(
                2.0 * int(conformance["what_the_violating_rows_lose"]["unparsed_gold_mentions"]),
                2.0 * int(conformance["what_the_violating_rows_lose"]["unparsed_gold_mentions"]),
            ),
            "ceiling_gain": None,
            "contacts": KC_S1B_COST["contacts"],
            "gpu_hours": gpu_hours(1.0),
            "why_the_ceiling_is_small": (
                "zero of 682 predicted mentions violate the 55-type vocabulary, so the "
                "enum is a guarantee rather than a repair; all it can recover is the 3 "
                "unparsed rows' 10 gold mentions"
            ),
        },
        {
            "rung": 3,
            "module": "intent narrowing applied to block selection (question 1a)",
            "what_it_is": (
                "a better predicted intent selects a better per-intent schema block; the "
                "coordinator reports a cell under the name KU-S4N as already GO, and THIS "
                "REPOSITORY CARRIES NO PREREGISTRATION OR OWNER RECORD UNDER THAT NAME, so "
                "this rung prices the mechanism and does not confirm its authorization"
            ),
            "measured_not_ceiling": False,
            "slu_f1_ceiling": ceiling(
                2.0
                * int(
                    decomposition["intent_as_schema_selector"][
                        "of_those_present_in_the_gold_intents_block"
                    ]
                ),
                2.0
                * int(
                    decomposition["intent_as_schema_selector"][
                        "of_those_present_in_the_gold_intents_block"
                    ]
                ),
            ),
            "contacts": KC_S1B_COST["contacts"],
            "gpu_hours": gpu_hours(1.0),
            "why_the_ceiling_is_an_oracle": (
                "it assumes PERFECT intent AND that every one of the 51 newly-legal gold "
                "mentions is then filled exactly. Real intent narrowing tops out around "
                "96.4 by MF-8's own candidate-recall ceiling, and the slot stage would "
                "still have to fill them"
            ),
        },
        {
            "rung": 4,
            "module": "retrieved fillers, KU-S3 (question 4)",
            "what_it_is": (
                "the row's own SPEECH vector retrieves the top-5 TRAIN utterances and "
                "their slot fillers are supplied as typed content; already preregistered "
                "and flyable"
            ),
            "measured_not_ceiling": False,
            "slu_f1_ceiling": headroom["retrieved_top_k"]["oracle_ceiling"]["slu_f1"],
            "contacts": KC_S1B_COST["contacts"],
            "gpu_hours": gpu_hours(1.0),
            "why_the_ceiling_is_an_oracle": (
                "the arm keeps every mention it already made AND emits every gold value "
                "the retrieval supplied; a real consumption cell has to find them"
            ),
        },
        {
            "rung": 5,
            "module": "same-speaker slot exemplars (KU-S4 applied to slots)",
            "what_it_is": (
                "the same-speaker exemplar supply MF-8 priced for intent, pointed at the "
                "slot stage"
            ),
            "measured_not_ceiling": False,
            "slu_f1_ceiling": None,
            "availability": headroom["same_speaker_slot_exemplars"],
            "contacts": KC_S1B_COST["contacts"],
            "gpu_hours": gpu_hours(1.0),
            "note": (
                "no scoring ceiling is claimed: this is a SUPPLY channel, and this audit "
                "measures only whether the supply exists"
            ),
        },
        {
            "rung": 6,
            "module": "targeted slot re-ask on judge-flagged rows (Observer selective listening)",
            "what_it_is": (
                "one EXTRA contact on flagged rows only; the judges are question 3's "
                "schema judge, question 2's value judge, and the free silent-row judge"
            ),
            "measured_not_ceiling": False,
            "flagged_rows": {name: len(ids) for name, ids in sorted(flags.items())},
            "unmatched_gold_mentions_on_flagged_rows": missing_by_flag,
            "unmatched_gold_mentions_total": total_missing,
            "slu_f1_ceiling": ceiling(
                2.0 * missing_by_flag["any"], 2.0 * missing_by_flag["any"]
            ),
            "per_judge_ceiling": {
                name: {
                    "rows": len(flags[name]),
                    "unmatched_gold_mentions": missing_by_flag[name],
                    "precision_pct": percent(productive_by_flag[name], len(flags[name])),
                    "slu_f1_ceiling": ceiling(
                        2.0 * missing_by_flag[name], 2.0 * missing_by_flag[name]
                    ),
                    "gpu_hours": gpu_hours(len(flags[name]) / len(roster)),
                    "ceiling_gain_per_gpu_hour": round(
                        (
                            ceiling(2.0 * missing_by_flag[name], 2.0 * missing_by_flag[name])
                            - base_slu
                        )
                        / max(1e-9, gpu_hours(len(flags[name]) / len(roster))),
                        1,
                    ),
                }
                for name in sorted(flags)
            },
            "contacts": len(flags["any"]),
            "gpu_hours": gpu_hours(len(flags["any"]) / len(roster)),
            "note": (
                "the ceiling assumes every re-asked row then answers every missed gold "
                "mention exactly, which nothing does. It is here to say which judge points "
                "at the most gold per contact, not to promise a number"
            ),
        },
    ]
    for rung in rungs:
        if rung.get("slu_f1_ceiling") is not None:
            rung["ceiling_gain"] = round(float(rung["slu_f1_ceiling"]) - base_slu, 2)
            hours = float(rung["gpu_hours"] or 0.0)
            rung["ceiling_gain_per_gpu_hour"] = (
                round(float(rung["ceiling_gain"]) / hours, 1) if hours else None
            )

    everything = ceiling(
        2.0
        * (
            int(decomposition["categories"]["missing"]["count"])
            + int(decomposition["categories"]["type_swap"]["count"])
        ),
        mass,
    )

    document = {
        "schema": "saea-slurp-mf9-improvement-ladder-v1",
        "row_id": ROW_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "contacts": {
            "model": 0,
            "gpu_hours": 0,
            "tool": 0,
            "embedding": 0,
            "network": 0,
            "audio_decode": 0,
        },
        "status": (
            "PRICED, NOT PREREGISTERED. No cell below is admitted, promoted or registered; "
            "no owner decision is anticipated and nothing here is flyable on the strength "
            "of this note"
        ),
        "sources": {
            "umbrella_lock": str(lock_path),
            "loss_decomposition": "loss-decomposition.json",
            "value_projection": "value-projection.json",
            "schema_conformance": "schema-conformance.json",
            "value_headroom": "value-headroom.json",
        },
        "baseline": {
            "arm": KC_S1B_RUN,
            "slu_f1": base_slu,
            "true_positive_mass": tp,
            "loss_mass": mass,
            "cost": KC_S1B_COST,
        },
        "judges": {
            "flag_threshold": args.flag_threshold,
            "definitions": {
                "silent": "the row parsed and predicted NO entity at all",
                "schema_violating": "unparsed, or a type the row's own block did not list, "
                "or the same type twice",
                "value_suspect": "at least one predicted filler whose nearest TRAIN surface "
                "form of that type is further than the flag threshold, or whose type has no "
                "TRAIN inventory at all",
                "any": "the union",
            },
            "rows": {name: len(ids) for name, ids in sorted(flags.items())},
            "rows_pct": {
                name: percent(len(ids), len(roster)) for name, ids in sorted(flags.items())
            },
            "rows_carrying_unmatched_gold": productive_by_flag,
            "precision_pct": {
                name: percent(productive_by_flag[name], len(ids))
                for name, ids in sorted(flags.items())
            },
            "dev_rows_with_no_gold_entity_at_all": rows_with_no_gold,
            "silent_rows_that_are_correctly_silent": silent_with_no_gold,
            "silent_judge_note": (
                "a third of the roster carries no gold slot at all, so a judge that fires "
                "on silence is mostly firing on rows that are RIGHT to be silent; its "
                "precision is what decides whether an extra contact is worth spending"
            ),
        },
        "contacts_per_row": contacts_per_row,
        "rungs": rungs,
        "if_every_module_delivered_its_ceiling": {
            "note": (
                "not a sum of the rungs: the rungs overlap, and this row is the arithmetic "
                "ceiling of the whole decomposition -- every missing gold answered, every "
                "type swap re-typed, every surface form exact, every spurious mention "
                "withheld"
            ),
            "slu_f1": everything,
        },
        "published_lines": PUBLISHED_SLURP_LINES,
        "measurement_rules_any_of_these_would_inherit": {
            "population": "DEV-1000, decision on the unexposed NEW500 (n = 500 >= 400)",
            "comparator": "the SEALED KC-S1b rows, never a re-flight",
            "greedy_noise_floor": (
                "EVO-S1 round 1 measured 286 of 1,019 byte-identically prompted rows "
                "(28.1 %) returning different text on this carrier and this build; a claim "
                "read off a handful of moved rows sits below the noise"
            ),
            "power": "paired effectiveness needs n >= 400 (owner 2026-09-03)",
        },
    }
    write_json(out_dir / "improvement-ladder.json", document)
    print(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True))
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

    schema = subparsers.add_parser("schema", help="question 3")
    schema.set_defaults(func=command_schema)

    headroom = subparsers.add_parser("headroom", help="question 4")
    headroom.add_argument("--k", type=int, default=5)
    headroom.set_defaults(func=command_headroom)

    ladder = subparsers.add_parser("ladder", help="question 5")
    ladder.add_argument("--flag-threshold", type=float, default=0.20)
    ladder.set_defaults(func=command_ladder)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
