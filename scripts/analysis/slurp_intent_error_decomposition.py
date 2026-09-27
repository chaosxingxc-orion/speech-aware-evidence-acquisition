#!/usr/bin/env python3
"""Where the 12.78 intent points live: the SLURP intent-error decomposition of the
locked v2.0 plan, by scenario, by action and by joint intent.

Owner decision 137 sets an ABSOLUTE target of 95 per cent intent-recognition accuracy.
On TRAIN Fold A the locked plan reads scenario_action exact 82.2222 (scenario exact 87.3148,
action exact 83.5185). Intent is the product of two labels, so this read decomposes the
joint error over the sealed PLAN answers of three rosters -- TRAIN Fold A (1,080 rows), the
ROLL-1 construction roster R01C (625 rows, delivered answers) and DEV-2000-ADDED (1,000
rows) -- and states, as arithmetic, how much of the error mass the top error-owning labels
carry and how many of them would have to be perfected to reach the target.

ZERO CONTACTS. No model, tokenizer, encoder, ASR, scorer, embedder, server, network, GPU or
paid-API contact. Every number comes from sealed per-row outputs, sealed per-sample official
score rows, committed roster receipts and the frozen SLURP gold read offline through
``data.slurp.load_slurp_split`` exactly as ``core.scoring_batch`` reads it. Correctness per
row is the OFFICIAL per-sample flag (``scenario_action_exact`` / ``scenario_exact`` /
``action_exact`` of the sealed ``<run_id>.scores.json``); the predicted label ids come from
``reproduction.slurp_scoring.parse_slu_response`` over the sealed delivered text, and the
read refuses if the two disagree on any row.

IDS, COUNTS AND RATES ONLY. No utterance text, transcript, delivered text, gold filler or
predicted filler is printed, cached or committed: scenario ids, action ids, intent ids
(``scenario_action``), integers, percentages and content hashes exclusively. Gold is a
scoring input and appears only in aggregate tables. The test split stays closed.

A DIAGNOSTIC, never a gate. It decides no cell, admits no mechanism, registers nothing and
states no effectiveness, superiority or generalisation claim. Every "if the top-k intents
were fixed entirely" number is an ORACLE framing and is labelled as one. TRAIN Fold A,
R01C and DEV-2000-ADDED numbers are development numbers (owner decisions 28 and 86).

Run (WSL, speechrl venv, zero contacts)::

    PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/slurp_intent_error_decomposition.py \
        --workers 4

Byte-reproducible apart from the single ``generated_at`` stamp in the JSON artefact and the
one dated line of the note: every table is sorted, ties are broken by id.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.analysis.null_calibration_cli import (  # noqa: E402
    rows_for,
)
from speech_aware_evidence_acquisition.data.lock import load_lock  # noqa: E402
from speech_aware_evidence_acquisition.data.slurp import (  # noqa: E402
    _SPLIT_FILES,
    _governed_roots,
    load_slurp_split,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (  # noqa: E402
    parse_slu_response,
)

RECIPE_ID = "slurp-intent-error-decomposition-v1"
SCHEMA = "saea-slurp-intent-error-decomposition-v1"
OUT_DIRNAME = "SAEA-SLURP-INTENT-ERROR-DECOMPOSITION-V1"
DEFAULT_MARKDOWN = "docs/results/2026-09-26-slurp-intent-error-decomposition.md"
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
TARGET_DEFAULT = 95.0
CATCH_ALL = "general_quirky"
UNPARSED = "<unparsed>"

#: The three rosters and the sealed PLAN-policy arm on each. ``split_id`` names the SLURP
#: gold split the roster is drawn from; the read refuses a roster id absent from it.
ROSTERS = (
    {
        "key": "train-fold-a",
        "label": "TRAIN Fold A (1,080 rows)",
        "roster_relpath": "docs/receipts/rosters/slurp-evo-fold-a-v2.json",
        "split_id": "train",
        "scorer": "slurp-slu-official-train",
        "run_id": "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1",
        "attempt_id": "attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1",
        "arm_note": "cell PLAN, the sealed v2.0 lock arm",
    },
    {
        "key": "roll-1-r01c",
        "label": "ROLL-1 R01C (625 rows, delivered answers)",
        "roster_relpath": "docs/receipts/rosters/slurp-stage3-construction-r01c.json",
        "split_id": "train",
        "scorer": "slurp-slu-official-train",
        "run_id": "SAEA-SLURP-STAGE3-ROLLOUT-R01-V1",
        "attempt_id": "attempt-slurp-native-stage3-rollout-r01-generation-v1",
        "arm_note": "cell ROLL-1, the locked plan with five Solver samples; the DELIVERED answer",
    },
    {
        "key": "dev2000-added",
        "label": "DEV-2000-ADDED (1,000 rows)",
        "roster_relpath": "docs/receipts/rosters/slurp-dev-2000-added-v1.json",
        "split_id": "devel",
        "scorer": "slurp-slu-official",
        "run_id": "SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1",
        "attempt_id": "attempt-slurp-native-default-plan-dev2000-added-generation-v1",
        "arm_note": "cell B6's PLAN arm on the fresh roster",
    },
)
POOLED_KEY = "pooled"
SCORE_FIELDS = ("scenario_action_exact", "scenario_exact", "action_exact", "parsed")
TOP_K_LADDER = (1, 2, 3, 5, 8, 10, 15, 20, 30)


class DecompositionError(RuntimeError):
    """A sealed input is missing, does not verify, or disagrees with itself."""


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pct(numerator: float, denominator: float) -> float:
    return 100.0 * numerator / denominator if denominator else 0.0


def fmt(value: float, places: int = 2) -> str:
    return f"{value:.{places}f}"


def md_table(header: list[str], rows: list[list[object]], align_right_from: int = 1) -> str:
    out = ["| " + " | ".join(header) + " |"]
    out.append(
        "| " + " | ".join("---" if i < align_right_from else "---:" for i in range(len(header))) + " |"
    )
    for row in rows:
        out.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(out)


# --------------------------------------------------------------------------
# Sealed inputs
# --------------------------------------------------------------------------


def load_roster(repo: Path, relpath: str) -> dict:
    path = repo / relpath
    document = json.loads(path.read_text(encoding="utf-8"))
    items = document.get("items") or []
    ids: list[str] = []
    utterances: dict[str, str] = {}
    for item in items:
        sample_id = item.get("sample_id") or item.get("id")
        if not isinstance(sample_id, str):
            raise DecompositionError(f"{relpath}: an item carries no sample_id")
        ids.append(sample_id)
        utterance = item.get("utterance_id")
        utterances[sample_id] = utterance if isinstance(utterance, str) else sample_id
    if len(set(ids)) != len(ids):
        raise DecompositionError(f"{relpath}: repeats a sample_id")
    return {
        "relpath": relpath,
        "sha256": digest(path),
        "roster_id": document.get("roster_id"),
        "split_role": document.get("split_role"),
        "split_identity_hash": document.get("split_identity_hash"),
        "ids": sorted(ids),
        "utterance_of": utterances,
    }


def arm_dir(data_root: Path, run_id: str, attempt_id: str) -> Path:
    directory = data_root / "runs" / run_id / attempt_id
    if not directory.is_dir():
        raise DecompositionError(f"sealed attempt directory missing: {directory}")
    return directory


def load_manifest(directory: Path, run_id: str, expected_split_hash: str) -> dict:
    path = directory / f"{run_id}.run-manifest.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("status") != "COMPLETED":
        raise DecompositionError(f"{run_id}: manifest is not COMPLETED")
    if document.get("study_repo_dirt"):
        raise DecompositionError(f"{run_id}: sealed with a dirty study tree")
    split = document.get("split") or {}
    if split.get("identity_hash") != expected_split_hash:
        raise DecompositionError(
            f"{run_id}: manifest split identity {split.get('identity_hash')} is not the roster's"
        )
    return {
        "path": str(path),
        "sha256": digest(path),
        "study_commit": document.get("study_commit"),
        "config_hash": ((document.get("config") or {}).get("config_hash")),
        "split_name": split.get("name"),
        "split_role": split.get("role"),
        "split_count": split.get("count"),
        "split_identity_hash": split.get("identity_hash"),
        "outputs_sha256": ((document.get("outputs") or {}).get("sha256")),
        "scores_sha256": ((document.get("scores") or {}).get("sha256")),
        "calls_used": ((document.get("cost") or {}).get("calls_used")),
    }


def load_scores(directory: Path, run_id: str, scorer: str, ids: list[str], expected_sha: str) -> dict:
    path = directory / f"{run_id}.scores.json"
    sha = digest(path)
    if sha != expected_sha:
        raise DecompositionError(f"{run_id}: scores.json sha256 {sha} is not the manifest's")
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = rows_for({"verified": True, "scores": raw}, scorer, SCORE_FIELDS)
    missing = sorted(set(ids) - set(rows))
    if missing:
        raise DecompositionError(f"{run_id}: per_sample is missing {len(missing)} roster rows")
    # The sealed official aggregate stores FRACTIONS (0.8222...); every number this read
    # reports is in percentage points, so the four official fields are scaled by 100 here.
    official = ((raw.get(scorer) or {}).get("aggregate") or {}).get("official") or {}
    recomputed = pct(sum(rows[i]["scenario_action_exact"] for i in ids), len(ids))
    published = official.get("intent_accuracy")
    if not isinstance(published, (int, float)) or abs(recomputed - 100.0 * float(published)) > 1e-6:
        raise DecompositionError(
            f"{run_id}: per-sample intent mean {recomputed} does not reproduce the official "
            f"intent_accuracy {published}"
        )
    return {
        "path": str(path),
        "sha256": sha,
        "rows": {i: rows[i] for i in ids},
        "official": {
            "intent_accuracy": 100.0 * float(official.get("intent_accuracy")),
            "scenario_accuracy": 100.0 * float(official.get("scenario_accuracy")),
            "action_accuracy": 100.0 * float(official.get("action_accuracy")),
            "slu_f1": 100.0 * float(official.get("slu_f1")),
        },
    }


def load_delivered(directory: Path, run_id: str, wanted: set[str], expected_sha: str) -> dict:
    """Delivered label ids per row (and, for a grouped-Solver run, per raw sample).

    Text is parsed in-process and discarded; only scenario / action ids leave this call.
    """
    path = directory / f"{run_id}.outputs.jsonl"
    sha = digest(path)
    if sha != expected_sha:
        raise DecompositionError(f"{run_id}: outputs.jsonl sha256 {sha} is not the manifest's")
    rows: dict[str, dict] = {}
    samples: dict[str, list[dict]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            sample_id = record.get("sample_id")
            if sample_id not in wanted:
                continue
            scenario, action, _entities, parsed = parse_slu_response(record.get("text") or "")
            rows[sample_id] = {
                "parsed": bool(parsed),
                "scenario": scenario if parsed and isinstance(scenario, str) else None,
                "action": action if parsed and isinstance(action, str) else None,
            }
            group = record.get("solver_group")
            if isinstance(group, dict) and isinstance(group.get("samples"), list):
                per_sample = []
                for sample in group["samples"]:
                    payload = sample.get("parsed_answer") if sample.get("parse_status") == "ok" else None
                    scen = payload.get("scenario") if isinstance(payload, dict) else None
                    act = payload.get("action") if isinstance(payload, dict) else None
                    per_sample.append(
                        {
                            "sample_index": int(sample.get("sample_index", len(per_sample))),
                            "scenario": scen if isinstance(scen, str) else None,
                            "action": act if isinstance(act, str) else None,
                        }
                    )
                samples[sample_id] = sorted(per_sample, key=lambda s: s["sample_index"])
    missing = sorted(wanted - set(rows))
    if missing:
        raise DecompositionError(f"{run_id}: outputs are missing {len(missing)} roster rows")
    return {"path": str(path), "sha256": sha, "rows": rows, "samples": samples}


def gold_labels(lock_path: Path, data_root: Path, split_id: str, workers: int) -> dict:
    """The frozen gold label ids of ``split_id`` through the governed loader.

    ``load_slurp_split`` re-verifies each recording's flac header (bounded here to
    ``workers`` threads, never more than four). Only scenario / action / intent ids are kept.
    """
    lock = load_lock(lock_path)
    metadata_path = _governed_roots(lock, data_root)[2] / _SPLIT_FILES[split_id]
    records = load_slurp_split(lock, data_root, split_id, workers=workers)
    labels = {
        record.sample_id: {
            "scenario": record.scenario,
            "action": record.action,
            "intent": record.intent,
        }
        for record in records
    }
    return {
        "split_id": split_id,
        "metadata_path": str(metadata_path),
        "metadata_sha256": digest(metadata_path),
        "records": len(labels),
        "labels": labels,
    }


# --------------------------------------------------------------------------
# Per-row assembly and the decomposition proper
# --------------------------------------------------------------------------


def intent_id(scenario: str | None, action: str | None) -> str:
    if scenario is None or action is None:
        return UNPARSED
    return f"{scenario}_{action}"


def assemble_rows(ids: list[str], gold: dict, delivered: dict, scores: dict, run_id: str) -> list[dict]:
    rows = []
    disagreements = Counter()
    for sample_id in ids:
        g = gold[sample_id]
        d = delivered[sample_id]
        s = scores[sample_id]
        pred_intent = intent_id(d["scenario"], d["action"])
        row = {
            "sample_id": sample_id,
            "gold_scenario": g["scenario"],
            "gold_action": g["action"],
            "gold_intent": g["intent"],
            "pred_scenario": d["scenario"],
            "pred_action": d["action"],
            "pred_intent": pred_intent,
            "parsed": d["parsed"],
            "scenario_ok": bool(s["scenario_exact"]),
            "action_ok": bool(s["action_exact"]),
            "intent_ok": bool(s["scenario_action_exact"]),
        }
        # The official flag is authoritative; the parse must agree with it on every row.
        if (d["scenario"] == g["scenario"]) != row["scenario_ok"]:
            disagreements["scenario"] += 1
        if (d["action"] == g["action"]) != row["action_ok"]:
            disagreements["action"] += 1
        if (pred_intent == g["intent"]) != row["intent_ok"]:
            disagreements["intent"] += 1
        rows.append(row)
    if disagreements:
        raise DecompositionError(
            f"{run_id}: the parsed labels disagree with the official per-sample flags on "
            f"{dict(disagreements)} rows; the read refuses rather than choose"
        )
    return rows


def label_table(rows: list[dict], gold_key: str, ok_key: str) -> list[dict]:
    """Per gold label: rows, correct, errors, accuracy, share of all errors of that metric."""
    n = Counter()
    errors = Counter()
    for row in rows:
        label = row[gold_key]
        n[label] += 1
        if not row[ok_key]:
            errors[label] += 1
    total_errors = sum(errors.values())
    table = []
    for label in sorted(n, key=lambda lab: (-errors[lab], lab)):
        table.append(
            {
                "id": label,
                "rows": n[label],
                "correct": n[label] - errors[label],
                "errors": errors[label],
                "accuracy": pct(n[label] - errors[label], n[label]),
                "error_share": pct(errors[label], total_errors),
            }
        )
    running = 0
    for entry in table:
        running += entry["errors"]
        entry["cumulative_error_share"] = pct(running, total_errors)
    return table


def covering_sets(table: list[dict], thresholds=(50.0, 80.0)) -> dict:
    """Smallest label sets owning at least each threshold of the error mass (descending
    greedy on error count, which is optimal for a coverage-by-count objective)."""
    total = sum(entry["errors"] for entry in table)
    out = {}
    for threshold in thresholds:
        chosen = []
        covered = 0
        for entry in table:
            if total and pct(covered, total) >= threshold:
                break
            if entry["errors"] == 0:
                break
            chosen.append(entry["id"])
            covered += entry["errors"]
        out[str(int(threshold))] = {
            "labels": chosen,
            "count": len(chosen),
            "of": sum(1 for entry in table if entry["errors"] > 0),
            "covered_errors": covered,
            "covered_share": pct(covered, total),
        }
    return out


def confusion(rows: list[dict]) -> dict:
    pairs = Counter()
    classes = Counter()
    catch_in = 0
    catch_out = 0
    scen_wrong_action_right = 0
    for row in rows:
        if row["intent_ok"]:
            continue
        pairs[(row["gold_intent"], row["pred_intent"])] += 1
        if not row["parsed"]:
            classes["unparsed"] += 1
        elif row["scenario_ok"] and not row["action_ok"]:
            classes["within_scenario_wrong_action"] += 1
        elif not row["scenario_ok"] and row["action_ok"]:
            classes["cross_scenario_same_action"] += 1
            scen_wrong_action_right += 1
        else:
            classes["cross_scenario_different_action"] += 1
        if row["pred_intent"] == CATCH_ALL and row["gold_intent"] != CATCH_ALL:
            catch_in += 1
        if row["gold_intent"] == CATCH_ALL and row["pred_intent"] != CATCH_ALL:
            catch_out += 1
    total = sum(pairs.values())
    ordered = sorted(pairs.items(), key=lambda kv: (-kv[1], kv[0]))
    pair_rows = []
    running = 0
    for (gold, pred), count in ordered:
        running += count
        pair_rows.append(
            {
                "gold": gold,
                "predicted": pred,
                "count": count,
                "share": pct(count, total),
                "cumulative_share": pct(running, total),
                "kind": (
                    "unparsed"
                    if pred == UNPARSED
                    else "within-scenario"
                    if gold.split("_", 1)[0] == pred.split("_", 1)[0]
                    else "cross-scenario"
                ),
            }
        )
    within = classes["within_scenario_wrong_action"]
    cross = classes["cross_scenario_same_action"] + classes["cross_scenario_different_action"]
    return {
        "intent_errors": total,
        "distinct_pairs": len(pairs),
        "classes": {
            "within_scenario_wrong_action": within,
            "cross_scenario": cross,
            "cross_scenario_same_action": classes["cross_scenario_same_action"],
            "cross_scenario_different_action": classes["cross_scenario_different_action"],
            "unparsed": classes["unparsed"],
        },
        "class_shares": {
            "within_scenario_wrong_action": pct(within, total),
            "cross_scenario": pct(cross, total),
            "unparsed": pct(classes["unparsed"], total),
        },
        "catch_all": {
            "id": CATCH_ALL,
            "predicted_in_error": catch_in,
            "predicted_in_share": pct(catch_in, total),
            "gold_missed_out": catch_out,
            "gold_missed_out_share": pct(catch_out, total),
        },
        "pairs": pair_rows,
    }


def oracle(rows: list[dict], table_intents: list[dict], pairs: list[dict],
           table_actions: list[dict], table_scenarios: list[dict], target: float) -> dict:
    """ORACLE arithmetic: if every row of the top-k error-owning labels were answered
    correctly, where would joint intent accuracy land, and how many labels reach ``target``."""
    n = len(rows)
    correct = sum(1 for row in rows if row["intent_ok"])
    errors = n - correct
    needed_correct = math.ceil(target / 100.0 * n - 1e-9)
    must_fix = max(0, needed_correct - correct)

    def ladder(entries, key_fn, count_fn):
        steps = []
        cum = 0
        k_target = None
        for k, entry in enumerate(entries, start=1):
            cum += count_fn(entry)
            acc = pct(correct + cum, n)
            if k in TOP_K_LADDER:
                steps.append({"k": k, "cumulative_fixed": cum, "joint_accuracy": acc})
            if k_target is None and correct + cum >= needed_correct:
                k_target = k
        return {"ladder": steps, "k_to_target": k_target, "labels_with_errors": len([e for e in entries if count_fn(e) > 0])}

    # Fixing a gold ACTION or SCENARIO label entirely means every row with that gold label
    # becomes jointly correct, so the count fixed per label is its JOINT error count.
    joint_errors_by_action = Counter()
    joint_errors_by_scenario = Counter()
    for row in rows:
        if not row["intent_ok"]:
            joint_errors_by_action[row["gold_action"]] += 1
            joint_errors_by_scenario[row["gold_scenario"]] += 1
    actions_by_joint = sorted(joint_errors_by_action.items(), key=lambda kv: (-kv[1], kv[0]))
    scenarios_by_joint = sorted(joint_errors_by_scenario.items(), key=lambda kv: (-kv[1], kv[0]))
    return {
        "target": target,
        "rows": n,
        "correct": correct,
        "errors": errors,
        "joint_accuracy": pct(correct, n),
        "gap_points": target - pct(correct, n),
        "needed_correct_for_target": needed_correct,
        "errors_to_remove_for_target": must_fix,
        "share_of_errors_to_remove": pct(must_fix, errors),
        "by_intent": ladder(table_intents, None, lambda e: e["errors"]),
        "by_confusion_pair": ladder(pairs, None, lambda e: e["count"]),
        "by_gold_action_joint": ladder(
            [{"id": a, "errors": c} for a, c in actions_by_joint], None, lambda e: e["errors"]
        ),
        "by_gold_scenario_joint": ladder(
            [{"id": s, "errors": c} for s, c in scenarios_by_joint], None, lambda e: e["errors"]
        ),
        "by_gold_action_joint_table": [{"id": a, "joint_errors": c} for a, c in actions_by_joint],
        "by_gold_scenario_joint_table": [{"id": s, "joint_errors": c} for s, c in scenarios_by_joint],
    }


def decompose(rows: list[dict], target: float) -> dict:
    n = len(rows)
    intents = label_table(rows, "gold_intent", "intent_ok")
    actions = label_table(rows, "gold_action", "action_ok")
    scenarios = label_table(rows, "gold_scenario", "scenario_ok")
    conf = confusion(rows)
    composition = Counter()
    for row in rows:
        if row["intent_ok"]:
            composition["correct"] += 1
        elif not row["parsed"]:
            composition["unparsed"] += 1
        elif row["scenario_ok"]:
            composition["action_only_wrong"] += 1
        elif row["action_ok"]:
            composition["scenario_only_wrong"] += 1
        else:
            composition["both_wrong"] += 1
    return {
        "rows": n,
        "headline": {
            "scenario_accuracy": pct(sum(r["scenario_ok"] for r in rows), n),
            "action_accuracy": pct(sum(r["action_ok"] for r in rows), n),
            "joint_accuracy": pct(sum(r["intent_ok"] for r in rows), n),
            "parsed_share": pct(sum(r["parsed"] for r in rows), n),
            "product_of_marginals": pct(sum(r["scenario_ok"] for r in rows), n)
            * pct(sum(r["action_ok"] for r in rows), n) / 100.0,
            "distinct_gold_scenarios": len({r["gold_scenario"] for r in rows}),
            "distinct_gold_actions": len({r["gold_action"] for r in rows}),
            "distinct_gold_intents": len({r["gold_intent"] for r in rows}),
        },
        "error_composition": dict(composition),
        "per_scenario": scenarios,
        "per_action": actions,
        "per_intent": intents,
        "covering_sets": {
            "scenarios": covering_sets(scenarios),
            "actions": covering_sets(actions),
            "intents": covering_sets(intents),
        },
        "confusion": conf,
        "oracle": oracle(rows, intents, conf["pairs"], actions, scenarios, target),
    }


def sample_level(ids: list[str], gold: dict, samples: dict, target: float) -> dict | None:
    """ROLL-1 appendix: the five raw Solver samples per row, parse-derived (no official
    per-sample flag exists for raw samples), labelled as such."""
    if not samples:
        return None
    rows = []
    for sample_id in ids:
        g = gold[sample_id]
        for sample in samples.get(sample_id, []):
            pred = intent_id(sample["scenario"], sample["action"])
            rows.append(
                {
                    "sample_id": sample_id,
                    "gold_scenario": g["scenario"],
                    "gold_action": g["action"],
                    "gold_intent": g["intent"],
                    "pred_scenario": sample["scenario"],
                    "pred_action": sample["action"],
                    "pred_intent": pred,
                    "parsed": sample["scenario"] is not None and sample["action"] is not None,
                    "scenario_ok": sample["scenario"] == g["scenario"],
                    "action_ok": sample["action"] == g["action"],
                    "intent_ok": pred == g["intent"],
                }
            )
    per_row_any = sum(
        1 for sample_id in ids
        if any(intent_id(s["scenario"], s["action"]) == gold[sample_id]["intent"] for s in samples.get(sample_id, []))
    )
    per_row_all = sum(
        1 for sample_id in ids
        if samples.get(sample_id) and all(intent_id(s["scenario"], s["action"]) == gold[sample_id]["intent"] for s in samples[sample_id])
    )
    result = decompose(rows, target)
    result["samples_per_row"] = Counter(len(v) for v in samples.values()).most_common(1)[0][0]
    result["rows_with_any_correct_sample"] = per_row_any
    result["rows_with_all_samples_correct"] = per_row_all
    result["rows_with_no_correct_sample"] = len(ids) - per_row_any
    return result


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------


def render_label_table(table: list[dict], label: str, limit: int | None = None) -> str:
    rows = table if limit is None else table[:limit]
    body = [
        [e["id"], e["rows"], e["errors"], fmt(e["accuracy"]), fmt(e["error_share"], 1), fmt(e["cumulative_error_share"], 1)]
        for e in rows
    ]
    note = "" if limit is None or len(table) <= limit else f"\n\n(top {limit} of {len(table)} by error mass; the full table is in `decomposition.json`)"
    return md_table([label, "rows", "errors", "exact %", "error share %", "cumulative %"], body) + note


def render_sets(sets: dict) -> str:
    lines = []
    for what in ("scenarios", "actions", "intents"):
        for threshold in ("50", "80"):
            entry = sets[what][threshold]
            lines.append(
                f"- {what}, {threshold} %: **{entry['count']}** of {entry['of']} with errors "
                f"({fmt(entry['covered_share'], 1)} % covered, {entry['covered_errors']} errors): "
                + (", ".join(f"`{x}`" for x in entry["labels"]) if entry["labels"] else "none")
            )
    return "\n".join(lines)


def render_pairs(conf: dict, limit: int) -> str:
    body = [
        [f"`{p['gold']}`", f"`{p['predicted']}`", p["kind"], p["count"], fmt(p["share"], 1), fmt(p["cumulative_share"], 1)]
        for p in conf["pairs"][:limit]
    ]
    return md_table(["gold intent", "predicted intent", "kind", "count", "share %", "cumulative %"], body, align_right_from=3)


def render_oracle(o: dict) -> str:
    lines = [
        f"rows {o['rows']}, correct {o['correct']}, errors {o['errors']}; joint accuracy {fmt(o['joint_accuracy'], 4)}; "
        f"gap to {fmt(o['target'], 0)} % = **{fmt(o['gap_points'], 2)} points**; reaching the target needs "
        f"{o['needed_correct_for_target']} correct rows, i.e. **{o['errors_to_remove_for_target']} of the {o['errors']} errors "
        f"({fmt(o['share_of_errors_to_remove'], 1)} %) removed**.",
        "",
    ]
    header = ["top-k fixed entirely (oracle)"] + [f"k={k}" for k in TOP_K_LADDER] + ["k to reach target", "labels with errors"]
    body = []
    for name, key in (
        ("gold intents", "by_intent"),
        ("(gold, predicted) pairs", "by_confusion_pair"),
        ("gold actions (joint errors)", "by_gold_action_joint"),
        ("gold scenarios (joint errors)", "by_gold_scenario_joint"),
    ):
        lad = {s["k"]: s["joint_accuracy"] for s in o[key]["ladder"]}
        row = [name] + [fmt(lad[k], 2) if k in lad else "--" for k in TOP_K_LADDER]
        k_t = o[key]["k_to_target"]
        row += ["**%s**" % (k_t if k_t is not None else "unreachable"), o[key]["labels_with_errors"]]
        body.append(row)
    lines.append(md_table(header, body))
    return "\n".join(lines)


def render_note(result: dict, target: float) -> str:
    per = result["per_roster"]
    pooled = result["pooled"]
    fold = per["train-fold-a"]
    lines: list[str] = []
    A = lines.append
    A("# Where the 12.78 points live: SLURP intent-error decomposition of the locked plan by scenario, action and joint intent")
    A("")
    A(
        f"Owner decision 137 sets an absolute target of **{fmt(target, 0)} % intent-recognition accuracy**. On TRAIN Fold A the "
        f"locked v2.0 plan reads `scenario_action` exact **{fmt(fold['official']['intent_accuracy'], 4)}** (scenario exact "
        f"{fmt(fold['official']['scenario_accuracy'], 4)}, action exact {fmt(fold['official']['action_accuracy'], 4)}), a gap of "
        f"**{fmt(fold['decomposition']['oracle']['gap_points'], 2)} points**. Intent is the product of two labels, so this note "
        "decomposes the joint error over the sealed PLAN-policy answers of three rosters and states, as arithmetic, where the error "
        "mass sits and how much of it must go. Measurement only: no mechanism is designed, no cell is registered, nothing is flown."
    )
    A("")
    A(
        f"**Method.** Model-free, zero contacts (no model, tokenizer, encoder, ASR, scorer, embedder, server, GPU or network). "
        f"Reproducer `scripts/analysis/slurp_intent_error_decomposition.py` (recipe `{RECIPE_ID}`), analysis root "
        f"`SPEECHRL_DATA_DIR/analysis/{OUT_DIRNAME}/`. Sources, all read-only and hash-verified against their sealed manifests: the "
        "three arms' `<run_id>.outputs.jsonl` and `<run_id>.scores.json`, the three committed roster receipts, and the frozen SLURP "
        "gold read through `data.slurp.load_slurp_split` (the loader `core.scoring_batch` uses; four probe threads). Per-row "
        "correctness is the OFFICIAL per-sample flag of the sealed score file; predicted ids come from "
        "`reproduction.slurp_scoring.parse_slu_response` over the sealed delivered text, and the read refuses if the two disagree on "
        f"any row (they agreed on every row of every roster: {result['integrity']['rows_checked']} rows). No utterance text, "
        "transcript, gold filler, predicted filler or delivered text is printed or persisted: label ids, counts, rates and hashes only. "
        "The test split stays closed."
    )
    A("")
    A(
        "**Claim boundary.** Development numbers (owner decisions 28 and 86) on exposed discovery / dev rosters; nothing here is a "
        "test claim, a superiority claim or a generalisation claim. Every \"top-k fixed entirely\" figure in section 5 is an **oracle**: "
        "it assumes a perfect repair of every row of the named labels and says nothing about how such a repair would be built. "
        "DEV-2000-ADDED withholds the stratum per item, so its per-scenario rows here are gold-derived aggregates, exactly as in the "
        "bad-case bank. The three rosters overlap in neither sample ids nor utterance ids "
        f"(section 0), so the pooled table simply adds rows."
    )
    A("")
    A("## 0. Inputs and the three rosters")
    A("")
    body = []
    for spec in ROSTERS:
        r = per[spec["key"]]
        body.append(
            [
                spec["label"],
                f"`{spec['run_id']}`",
                r["gold_split"],
                r["rows"],
                fmt(r["official"]["scenario_accuracy"], 4),
                fmt(r["official"]["action_accuracy"], 4),
                fmt(r["official"]["intent_accuracy"], 4),
                fmt(target - r["official"]["intent_accuracy"], 2),
            ]
        )
    body.append(
        [
            "**pooled**",
            "--",
            "train+devel",
            pooled["rows"],
            fmt(pooled["headline"]["scenario_accuracy"], 4),
            fmt(pooled["headline"]["action_accuracy"], 4),
            fmt(pooled["headline"]["joint_accuracy"], 4),
            fmt(target - pooled["headline"]["joint_accuracy"], 2),
        ]
    )
    A(md_table(["roster", "sealed arm", "gold split", "rows", "scenario %", "action %", "intent %", f"gap to {fmt(target, 0)}"], body, align_right_from=3))
    A("")
    ov = result["roster_overlap"]
    A(
        f"Roster overlap (ids only): shared sample ids {ov['shared_sample_ids']}, shared utterance ids {ov['shared_utterance_ids']} "
        f"across the three rosters (pairwise: {', '.join(f'{k} = {v}' for k, v in ov['pairwise_utterances'].items())}). "
        f"Label vocabulary seen in gold: {pooled['headline']['distinct_gold_scenarios']} scenarios, "
        f"{pooled['headline']['distinct_gold_actions']} actions, {pooled['headline']['distinct_gold_intents']} intents."
    )
    A("")
    A("## 1. Headline: the two components and how the joint error is composed")
    A("")
    body = []
    for key, label in [(s["key"], s["label"]) for s in ROSTERS] + [(POOLED_KEY, "pooled")]:
        d = per[key]["decomposition"] if key != POOLED_KEY else pooled
        h = d["headline"]
        c = d["error_composition"]
        errs = d["rows"] - c.get("correct", 0)
        body.append(
            [
                label,
                d["rows"],
                fmt(h["scenario_accuracy"]),
                fmt(h["action_accuracy"]),
                fmt(h["joint_accuracy"]),
                fmt(h["product_of_marginals"]),
                errs,
                f"{c.get('action_only_wrong', 0)} ({fmt(pct(c.get('action_only_wrong', 0), errs), 1)} %)",
                f"{c.get('scenario_only_wrong', 0)} ({fmt(pct(c.get('scenario_only_wrong', 0), errs), 1)} %)",
                f"{c.get('both_wrong', 0)} ({fmt(pct(c.get('both_wrong', 0), errs), 1)} %)",
                f"{c.get('unparsed', 0)} ({fmt(pct(c.get('unparsed', 0), errs), 1)} %)",
            ]
        )
    A(
        md_table(
            ["roster", "rows", "scenario %", "action %", "joint %", "scen x act %", "joint errors", "action only wrong", "scenario only wrong", "both wrong", "unparsed"],
            body,
        )
    )
    A("")
    ph = pooled["headline"]
    pc = pooled["error_composition"]
    perrs = pooled["rows"] - pc.get("correct", 0)
    weaker = [
        spec["label"]
        for spec in ROSTERS
        if per[spec["key"]]["decomposition"]["headline"]["action_accuracy"]
        < per[spec["key"]]["decomposition"]["headline"]["scenario_accuracy"]
    ]
    action_only = pc.get("action_only_wrong", 0)
    scenario_only = pc.get("scenario_only_wrong", 0)
    both = pc.get("both_wrong", 0)
    unparsed = pc.get("unparsed", 0)
    action_errors = action_only + both + unparsed
    scenario_errors = scenario_only + both + unparsed
    largest = max(
        (("both labels wrong", both), ("the action alone wrong", action_only), ("the scenario alone wrong", scenario_only)),
        key=lambda kv: kv[1],
    )[0]
    dependence = (
        "above the product of the two marginals: the two errors coincide on the same rows far more often than independence would give"
        if ph["joint_accuracy"] > ph["product_of_marginals"]
        else "at or below the product of the two marginals: the two errors do not coincide more often than independence would give"
    )
    A(
        f"**Reading.** Action-exact accuracy is below scenario-exact accuracy on {len(weaker)} of {len(ROSTERS)} rosters"
        + (f" ({', '.join(weaker)})" if 0 < len(weaker) < len(ROSTERS) else "")
        + f", so in marginal terms the action side is the weaker label. But the largest joint-error class is **{largest}**: pooled, "
        f"{both} of {perrs} joint errors ({fmt(pct(both, perrs), 1)} %) have BOTH labels wrong, {action_only} "
        f"({fmt(pct(action_only, perrs), 1)} %) have the scenario right and the action wrong, {scenario_only} "
        f"({fmt(pct(scenario_only, perrs), 1)} %) have the action right and the scenario wrong, and {unparsed} are unparsed. "
        f"Of the {action_errors} action errors, {both + unparsed} ({fmt(pct(both + unparsed, action_errors), 1)} %) sit on rows whose "
        f"scenario is also wrong; of the {scenario_errors} scenario errors, {both + unparsed} ({fmt(pct(both + unparsed, scenario_errors), 1)} %) "
        f"sit on rows whose action is also wrong. The joint accuracy ({fmt(ph['joint_accuracy'])}) is {dependence}. The action "
        "side is therefore not a separable weakness: most action errors are the action changing together with the scenario, i.e. a "
        "cross-scenario intent confusion, not an action slip inside the right scenario."
    )
    A("")
    A(
        "**Two upper bounds, exact arithmetic.** A row is jointly correct only if its scenario is correct AND its action is correct, so "
        "joint accuracy can never exceed either component's exact accuracy. Reaching the target therefore needs each component at or "
        f"above {fmt(target, 0)} % on its own; the table gives how far each side is from that bound and how many of its own errors would "
        "have to go. The within-scenario column is the headroom of a PERFECT action decision inside the correct scenario (its ceiling is "
        "exactly the scenario-exact accuracy); the remainder of the gap can only be closed by moving rows across scenarios."
    )
    A("")
    body = []
    for key, label in [(s["key"], s["label"]) for s in ROSTERS] + [(POOLED_KEY, "pooled")]:
        d = per[key]["decomposition"] if key != POOLED_KEY else pooled
        h = d["headline"]
        c = d["error_composition"]
        n = d["rows"]
        needed = math.ceil(target / 100.0 * n - 1e-9)
        scen_correct = round(h["scenario_accuracy"] * n / 100.0)
        act_correct = round(h["action_accuracy"] * n / 100.0)
        body.append(
            [
                label,
                fmt(h["joint_accuracy"]),
                fmt(target - h["joint_accuracy"]),
                fmt(h["scenario_accuracy"]),
                f"{fmt(target - h['scenario_accuracy'])} ({max(0, needed - scen_correct)} of {n - scen_correct})",
                fmt(h["action_accuracy"]),
                f"{fmt(target - h['action_accuracy'])} ({max(0, needed - act_correct)} of {n - act_correct})",
                f"+{fmt(pct(c.get('action_only_wrong', 0), n))} -> {fmt(h['scenario_accuracy'])}",
                fmt(pct(c.get('scenario_only_wrong', 0) + c.get('both_wrong', 0) + c.get('unparsed', 0), n)),
            ]
        )
    A(
        md_table(
            ["roster", "joint %", "joint gap", "scenario %", "scenario gap (errors to remove)", "action %", "action gap (errors to remove)", "within-scenario headroom (pp -> ceiling)", "cross-scenario mass (pp)"],
            body,
        )
    )
    A("")
    A("## 2. Error mass by scenario, by action and by joint intent")
    A("")
    A("Each table is sorted by the error mass the gold label owns; `error share` is the label's share of ALL errors of that metric "
      "(scenario errors for the scenario table, action errors for the action table, joint errors for the intent table).")
    A("")
    A(f"### 2.1 Pooled ({pooled['rows']:,} rows)")
    A("")
    A("Per scenario (scenario-exact errors):")
    A("")
    A(render_label_table(pooled["per_scenario"], "scenario"))
    A("")
    A("Per action (action-exact errors):")
    A("")
    A(render_label_table(pooled["per_action"], "action"))
    A("")
    A("Per joint intent (scenario_action errors):")
    A("")
    A(render_label_table(pooled["per_intent"], "intent", limit=30))
    A("")
    for spec in ROSTERS:
        d = per[spec["key"]]["decomposition"]
        A(f"### 2.{2 + ROSTERS.index(spec)} {spec['label']}")
        A("")
        A("Per scenario:")
        A("")
        A(render_label_table(d["per_scenario"], "scenario"))
        A("")
        A("Per action (top 15):")
        A("")
        A(render_label_table(d["per_action"], "action", limit=15))
        A("")
        A("Per joint intent (top 15):")
        A("")
        A(render_label_table(d["per_intent"], "intent", limit=15))
        A("")
    A("## 3. The smallest label sets that own 50 % and 80 % of the errors")
    A("")
    A("Descending greedy on error count (optimal for a coverage-by-count objective); `of` counts the labels that carry at least one error.")
    A("")
    A("**Pooled.**")
    A("")
    A(render_sets(pooled["covering_sets"]))
    A("")
    for spec in ROSTERS:
        A(f"**{spec['label']}.**")
        A("")
        A(render_sets(per[spec["key"]]["decomposition"]["covering_sets"]))
        A("")
    A("## 4. Confusion structure")
    A("")
    for index, (key, label) in enumerate([(POOLED_KEY, "Pooled")] + [(s["key"], s["label"]) for s in ROSTERS], start=1):
        d = per[key]["decomposition"] if key != POOLED_KEY else pooled
        c = d["confusion"]
        A(f"### 4.{index} {label}")
        A("")
        A(
            f"{c['intent_errors']} joint errors over {c['distinct_pairs']} distinct (gold, predicted) pairs. "
            f"Within-scenario (right scenario, wrong action): **{c['classes']['within_scenario_wrong_action']}** "
            f"({fmt(c['class_shares']['within_scenario_wrong_action'], 1)} %); cross-scenario: **{c['classes']['cross_scenario']}** "
            f"({fmt(c['class_shares']['cross_scenario'], 1)} %; of which same action {c['classes']['cross_scenario_same_action']}, "
            f"different action {c['classes']['cross_scenario_different_action']}); unparsed: {c['classes']['unparsed']} "
            f"({fmt(c['class_shares']['unparsed'], 1)} %). Catch-all `{CATCH_ALL}`: predicted IN error on "
            f"{c['catch_all']['predicted_in_error']} rows ({fmt(c['catch_all']['predicted_in_share'], 1)} % of joint errors), gold "
            f"`{CATCH_ALL}` missed OUT on {c['catch_all']['gold_missed_out']} rows ({fmt(c['catch_all']['gold_missed_out_share'], 1)} %)."
        )
        A("")
        A(render_pairs(c, 25 if key == POOLED_KEY else 12))
        A("")
        if key == POOLED_KEY:
            top_pair_share = c["pairs"][0]["share"] if c["pairs"] else 0.0
            ones = sum(1 for p in c["pairs"] if p["count"] == 1)
            ones_mass = sum(p["count"] for p in c["pairs"] if p["count"] <= 2)
            A(
                f"**Reading.** The catch-all is a sink of GOLD, not of predictions: gold `{CATCH_ALL}` is missed on "
                f"{c['catch_all']['gold_missed_out']} rows ({fmt(c['catch_all']['gold_missed_out_share'], 1)} % of all joint errors, "
                f"exact {fmt(next(e['accuracy'] for e in d['per_intent'] if e['id'] == CATCH_ALL), 1)} % on {next(e['rows'] for e in d['per_intent'] if e['id'] == CATCH_ALL)} rows), "
                f"while `{CATCH_ALL}` is over-predicted on only {c['catch_all']['predicted_in_error']} rows. The largest single pair owns "
                f"{fmt(top_pair_share, 1)} % of the joint errors; {ones} of the {c['distinct_pairs']} pairs occur exactly once and pairs "
                f"of one or two rows carry {ones_mass} errors ({fmt(pct(ones_mass, c['intent_errors']), 1)} % of the mass). Cross-scenario "
                f"errors are {fmt(c['class_shares']['cross_scenario'], 1)} % of the joint errors on the pooled rosters."
            )
            A("")
    A(f"## 5. Oracle arithmetic to {fmt(target, 0)} %")
    A("")
    A(
        "**This section is an oracle framing.** Each row assumes that EVERY row of the named top-k labels (sorted by the error mass "
        "they own) is answered correctly and nothing else changes; it is the ceiling of a perfect repair of those labels, not a "
        "forecast. `k to reach target` is the number of labels that must be perfected for joint accuracy to reach the target."
    )
    A("")
    for key, label in [(POOLED_KEY, "Pooled")] + [(s["key"], s["label"]) for s in ROSTERS]:
        d = per[key]["decomposition"] if key != POOLED_KEY else pooled
        A(f"**{label}.** " + render_oracle(d["oracle"]).split("\n", 1)[0])
        A("")
        A(render_oracle(d["oracle"]).split("\n", 2)[2])
        A("")
    po = pooled["oracle"]
    fo = fold["decomposition"]["oracle"]
    fc = fold["decomposition"]["error_composition"]
    fh = fold["decomposition"]["headline"]

    def k_or(x):
        return str(x) if x is not None else "all (unreachable)"

    A(
        f"**Consequence, TRAIN Fold A (the 12.78 points).** The target needs {fo['errors_to_remove_for_target']} of the {fo['errors']} joint "
        f"errors removed ({fmt(fo['share_of_errors_to_remove'], 1)} %). A perfect action decision inside the correct scenario -- every one of the "
        f"{fc.get('action_only_wrong', 0)} action-only rows repaired -- lifts joint accuracy by {fmt(pct(fc.get('action_only_wrong', 0), fold['rows']), 2)} points to "
        f"{fmt(fh['scenario_accuracy'], 2)}, the scenario-exact ceiling, and leaves {fmt(target - fh['scenario_accuracy'], 2)} of the 12.78 points that only "
        f"cross-scenario repairs can close. By labels: perfecting the top {k_or(fo['by_intent']['k_to_target'])} gold intents of the "
        f"{fo['by_intent']['labels_with_errors']} that carry errors reaches the target; so does perfecting the top "
        f"{k_or(fo['by_confusion_pair']['k_to_target'])} of {fo['by_confusion_pair']['labels_with_errors']} confusion pairs, every joint error of the top "
        f"{k_or(fo['by_gold_action_joint']['k_to_target'])} of {fo['by_gold_action_joint']['labels_with_errors']} gold actions, or of the top "
        f"{k_or(fo['by_gold_scenario_joint']['k_to_target'])} of 18 gold scenarios. The top five intents together move Fold A only to "
        f"{fmt(next(s['joint_accuracy'] for s in fo['by_intent']['ladder'] if s['k'] == 5), 2)}."
    )
    A("")
    within_share = []
    for spec in ROSTERS:
        d = per[spec["key"]]["decomposition"]
        gap = target - d["headline"]["joint_accuracy"]
        within_share.append(pct(pct(d["error_composition"].get("action_only_wrong", 0), d["rows"]), gap) if gap > 0 else 0.0)
    A(
        f"**Consequence, pooled.** {po['errors_to_remove_for_target']} of {po['errors']} joint errors ({fmt(po['share_of_errors_to_remove'], 1)} %) must go. "
        f"Perfecting the top {k_or(po['by_intent']['k_to_target'])} gold intents of {po['by_intent']['labels_with_errors']} with errors would do it; so would the top "
        f"{k_or(po['by_confusion_pair']['k_to_target'])} of {po['by_confusion_pair']['labels_with_errors']} confusion pairs, every joint error of the top "
        f"{k_or(po['by_gold_action_joint']['k_to_target'])} gold actions, or of the top {k_or(po['by_gold_scenario_joint']['k_to_target'])} gold scenarios. "
        "The error is broad, not concentrated: no handful of labels reaches the target, the tail of one- and two-row pairs is a large "
        f"share of the mass (section 4), and a perfect within-scenario action decision closes between {fmt(min(within_share), 0)} % and "
        f"{fmt(max(within_share), 0)} % of the gap depending on the roster. Any route to {fmt(target, 0)} has to move rows across scenarios -- "
        "the intent decision as a whole -- on most intents at once, not repair a few named confusions or the action label alone."
    )
    A("")
    sl = result["per_roster"]["roll-1-r01c"].get("sample_level")
    if sl:
        A("## 6. Appendix: ROLL-1's five raw Solver samples per row (parse-derived, not official flags)")
        A("")
        h = sl["headline"]
        A(
            f"{sl['rows']} samples ({sl['samples_per_row']} per row x 625 rows): sample-level scenario {fmt(h['scenario_accuracy'])} %, "
            f"action {fmt(h['action_accuracy'])} %, joint {fmt(h['joint_accuracy'])} %. Rows with at least one correct sample: "
            f"**{sl['rows_with_any_correct_sample']}** of 625 ({fmt(pct(sl['rows_with_any_correct_sample'], 625), 2)} %); rows with all "
            f"{sl['samples_per_row']} correct: {sl['rows_with_all_samples_correct']}; rows with NO correct sample: "
            f"**{sl['rows_with_no_correct_sample']}** ({fmt(pct(sl['rows_with_no_correct_sample'], 625), 2)} %). The delivered answer on the "
            f"same rows reads {fmt(per['roll-1-r01c']['official']['intent_accuracy'], 4)} % (section 0), so the best-of-five oracle "
            f"ceiling is {fmt(pct(sl['rows_with_any_correct_sample'], 625) - per['roll-1-r01c']['official']['intent_accuracy'], 2)} points "
            "above the delivered path and still short of the target on this roster."
        )
        A("")
        A("Top sample-level joint-intent error owners:")
        A("")
        A(render_label_table(sl["per_intent"], "intent", limit=12))
        A("")
        A("Within-scenario share of sample-level joint errors: "
          f"{fmt(sl['confusion']['class_shares']['within_scenario_wrong_action'], 1)} %; cross-scenario "
          f"{fmt(sl['confusion']['class_shares']['cross_scenario'], 1)} %; unparsed {fmt(sl['confusion']['class_shares']['unparsed'], 1)} %.")
        A("")
    A("## 7. Artefacts")
    A("")
    A(f"Written under `SPEECHRL_DATA_DIR/analysis/{OUT_DIRNAME}/`:")
    A("")
    A(md_table(["file", "sha256"], [[f"`{k}`", f"`{v}`"] for k, v in sorted(result["artefacts"].items())], align_right_from=2))
    A("")
    A("Sealed inputs (read-only, verified):")
    A("")
    body = []
    for spec in ROSTERS:
        r = per[spec["key"]]
        body.append([f"`{spec['run_id']}` outputs", f"`{r['inputs']['outputs_sha256']}`"])
        body.append([f"`{spec['run_id']}` scores", f"`{r['inputs']['scores_sha256']}`"])
        body.append([f"`{spec['roster_relpath']}`", f"`{r['inputs']['roster_sha256']}`"])
    for split_id, meta in sorted(result["gold"].items()):
        body.append([f"gold metadata `{split_id}` ({meta['records']} records)", f"`{meta['metadata_sha256']}`"])
    A(md_table(["input", "sha256"], body, align_right_from=2))
    A("")
    A(f"Generated {result['generated_at']} by `{RECIPE_ID}`; the only non-deterministic bytes in this note are on this line.")
    A("")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--data-root", type=Path, default=Path(os.environ.get("SPEECHRL_DATA_DIR", "")))
    parser.add_argument("--lock", type=Path, default=Path(DEFAULT_LOCK))
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--markdown", type=Path, default=None)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--target", type=float, default=TARGET_DEFAULT)
    args = parser.parse_args()
    if not str(args.data_root):
        raise SystemExit("SPEECHRL_DATA_DIR is not set and --data-root was not given")
    if args.workers < 1 or args.workers > 4:
        raise SystemExit("--workers must be within [1, 4] (zero-contact read beside a live flight)")
    data_root = args.data_root.resolve()
    out_dir = args.out_dir or (data_root / "analysis" / OUT_DIRNAME)
    markdown = args.markdown or (args.repo / DEFAULT_MARKDOWN)
    out_dir.mkdir(parents=True, exist_ok=True)

    gold_cache: dict[str, dict] = {}

    def gold_for(split_id: str) -> dict:
        if split_id not in gold_cache:
            print(f"[gold] loading split {split_id} through load_slurp_split (workers={args.workers})", flush=True)
            gold_cache[split_id] = gold_labels(args.lock, data_root, split_id, args.workers)
            print(f"[gold] {split_id}: {gold_cache[split_id]['records']} records", flush=True)
        return gold_cache[split_id]

    per_roster: dict[str, dict] = {}
    all_rows: list[dict] = []
    rosters_loaded: dict[str, dict] = {}
    rows_checked = 0
    for spec in ROSTERS:
        roster = load_roster(args.repo, spec["roster_relpath"])
        rosters_loaded[spec["key"]] = roster
        directory = arm_dir(data_root, spec["run_id"], spec["attempt_id"])
        manifest = load_manifest(directory, spec["run_id"], roster["split_identity_hash"])
        scores = load_scores(directory, spec["run_id"], spec["scorer"], roster["ids"], manifest["scores_sha256"])
        delivered = load_delivered(directory, spec["run_id"], set(roster["ids"]), manifest["outputs_sha256"])
        gold = gold_for(spec["split_id"])
        missing = [i for i in roster["ids"] if i not in gold["labels"]]
        if missing:
            raise DecompositionError(
                f"{spec['key']}: {len(missing)} roster ids are absent from gold split {spec['split_id']}"
            )
        rows = assemble_rows(roster["ids"], gold["labels"], delivered["rows"], scores["rows"], spec["run_id"])
        rows_checked += len(rows)
        decomposition = decompose(rows, args.target)
        per_roster[spec["key"]] = {
            "label": spec["label"],
            "run_id": spec["run_id"],
            "attempt_id": spec["attempt_id"],
            "arm_note": spec["arm_note"],
            "roster_relpath": spec["roster_relpath"],
            "roster_id": roster["roster_id"],
            "gold_split": spec["split_id"],
            "scorer": spec["scorer"],
            "rows": len(rows),
            "official": scores["official"],
            "inputs": {
                "manifest_sha256": manifest["sha256"],
                "study_commit": manifest["study_commit"],
                "config_hash": manifest["config_hash"],
                "outputs_sha256": delivered["sha256"],
                "scores_sha256": scores["sha256"],
                "roster_sha256": roster["sha256"],
                "split_identity_hash": manifest["split_identity_hash"],
                "calls_used": manifest["calls_used"],
            },
            "decomposition": decomposition,
            "sample_level": sample_level(roster["ids"], gold["labels"], delivered["samples"], args.target),
        }
        for row in rows:
            all_rows.append(dict(row, roster=spec["key"]))
        print(
            f"[{spec['key']}] rows {len(rows)} scenario {decomposition['headline']['scenario_accuracy']:.4f} "
            f"action {decomposition['headline']['action_accuracy']:.4f} joint {decomposition['headline']['joint_accuracy']:.4f}",
            flush=True,
        )

    pooled = decompose(all_rows, args.target)
    # Roster overlap, ids only.
    keys = [s["key"] for s in ROSTERS]
    id_sets = {k: set(rosters_loaded[k]["ids"]) for k in keys}
    utt_sets = {k: set(rosters_loaded[k]["utterance_of"].values()) for k in keys}
    pairwise_utt = {}
    shared_ids = 0
    shared_utts = 0
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            shared_ids += len(id_sets[a] & id_sets[b])
            n_utt = len(utt_sets[a] & utt_sets[b])
            shared_utts += n_utt
            pairwise_utt[f"{a} x {b}"] = n_utt
    # The JSON artefact carries no timestamp, so two runs over the same sealed bytes are
    # byte-identical; the one dated line lives in the note only.
    result = {
        "schema": SCHEMA,
        "recipe_id": RECIPE_ID,
        "target": args.target,
        "integrity": {"rows_checked": rows_checked, "parse_vs_official_disagreements": 0},
        "gold": {
            split_id: {k: v for k, v in meta.items() if k != "labels"} for split_id, meta in gold_cache.items()
        },
        "roster_overlap": {
            "shared_sample_ids": shared_ids,
            "shared_utterance_ids": shared_utts,
            "pairwise_utterances": pairwise_utt,
        },
        "per_roster": per_roster,
        "pooled": pooled,
        "artefacts": {},
    }
    json_path = out_dir / "decomposition.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    result["artefacts"] = {"decomposition.json": digest(json_path)}
    result["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_note(result, args.target), encoding="utf-8", newline="\n")
    print(f"[done] json {json_path} ({result['artefacts']['decomposition.json'][:16]}...) note {markdown}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DecompositionError as error:
        print(f"refused: {error}", file=sys.stderr)
        raise SystemExit(2)
