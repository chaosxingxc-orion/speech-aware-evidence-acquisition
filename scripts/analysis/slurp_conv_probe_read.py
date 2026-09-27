#!/usr/bin/env python3
"""slurp_conv_probe_read.py -- the READ DRIVER for cell CONV, the 70-row conversion probe of
the AGREE arm (registered recipe ``slurp-stage3-conv-fold-a-70-conditional-rate-v1``).

WHAT IT MEASURES. One binomial proportion: of the 70 TRAIN Fold A rows whose gold intent's
boundary entry the agreement term NEWLY delivers, how many move from a wrong intent in the
sealed PLAN comparator to the gold intent under the treatment. That count, ``m``, is the AGREE
arm's persuasion factor measured, and it is the number the arm's re-declared expectation is
arithmetic on (owner decisions 133 and 134).

THE RECIPE IS FOLLOWED STEP BY STEP, and its two refusals are honoured before any number is
written:

  1. the sealed manifest is COMPLETED at 70 rows and its id list hashes to the committed
     roster's id-list sha256 (compared as a hash, never as a count);
  2. the flown Perception consumption delivered the row's own gold intent boundary value id on
     ALL 70 rows -- the delivery check. The offline derivation predicts 70; anything less is an
     engineering defect and CLOSES THE READ WITH NO CONVERSION NUMBER (a defect receipt is
     written instead and the process exits 2);
  3. the official scorer already ran ONCE over the complete manifest at finalize
     (``core.scoring_batch``, one job, never sharded); this driver READS its sealed per-sample
     ``scenario_action_exact`` and never re-runs it;
  4. the comparator's per-row verdict is established two ways -- the bad-case bank's
     ``plan_class`` (INTENT-UNCOVERED implies intent-wrong, digest pinned in the recipe) and the
     sealed PLAN arm's own official per-sample score -- and the read refuses on any disagreement;
  5. ``m`` is the forward count and ``r`` the reverse count; ``r`` must be 0 on this roster;
  6. Wilson score CI95 with the exact Clopper-Pearson CI95 beside it, no bootstrap;
  7. the companion split of the stay-wrong rows: byte-identical delivered answer versus a
     different wrong intent (and the residual: the same wrong intent in different bytes);
  8. the re-declaration arithmetic, STATED and not applied: m x 0.041615 pp SLU-F1 and
     m x 0.092615 pp intent, the retired 61-row SLU-F1 threshold and the decision-133 27-row
     intent threshold, and which side of each ``m`` falls -- together with the statement that
     this is a CONDITIONAL rate on a gold-selected roster and never a pooled effect.

Beside the recipe's numbers the driver reports what the coordinator asked for: the four-way
transition split, the within-pair byte identity of the delivered answer on rows whose intent
did not change, contacts against the 770 cap, GPU minutes from the sealed serving monitor, and
every episode disposition (finite completion, revision limit, illegal Planner action, ReAct
exhaustion, context compaction).

MODEL-FREE. Zero model, tokenizer, encoder, embedder, scorer, llama-server and network contacts;
nothing under the sealed run directory is opened for writing; nothing is written anywhere except
under ``--output-root``. Every sealed byte read is hashed and the hash is carried in the receipt.

TEXT DISCIPLINE. No utterance text, transcript, gold label string, intent name, value id or
delivered answer is printed or persisted: sample ids, counts, rates and hashes only. Gold and
delivered intents are compared in memory and discarded; a boundary value id is tested for
membership and discarded.

Byte-reproducible apart from ``generated_at_utc``.

    PYTHONDONTWRITEBYTECODE=1 python scripts/analysis/slurp_conv_probe_read.py \
        --repo-root . --data-root "$SPEECHRL_DATA_DIR"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import speech_aware_evidence_acquisition as _pkg  # noqa: E402

if not Path(_pkg.__file__).resolve().is_relative_to(SRC.resolve()):
    raise SystemExit(
        f"refusing: the imported package resolves to {_pkg.__file__}, not this checkout's src/"
    )

from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (  # noqa: E402
    parse_slu_response,
)

DRIVER_ID = "slurp-conv-probe-read-v1"
PACKAGE = Path("docs/readiness/2026-09-26-slurp-stage3-conv-fold-a-70-v1")
RECIPE_RELPATH = PACKAGE / "analysis-recipe-v1.json"
RECIPE_ID = "slurp-stage3-conv-fold-a-70-conditional-rate-v1"
SCORER = "slurp-slu-official-train"
FIELD = "scenario_action_exact"
BOUNDARY_PREFIX = "intent-boundary:"
PLAN_CLASS = "INTENT-UNCOVERED"
BANK_ROSTER = "train-fold-a"
UNPARSED = "<unparsed>"
Z95 = 1.959963984540054
FIT_RUN_ID = "SAEA-SLURP-STAGE3-CONV-FOLD-A-70-FIT-V1"

#: The registered per-row headroom of the class the gain lands on (the parent package's
#: expected_effect_derivation, not re-derived here) and the arm's own bar.
INTENT_PP_PER_ROW = 0.092615
SLU_PP_PER_ROW = 0.041615
ARM_BAR_PP = 2.5
ARM_ROWS = 1080
ARM_CEILING_INTENT_PP = 6.4831
ARM_CEILING_SLU_PP = 2.9131
#: The only directly observable prior, from the parent package's measured_inputs.
PRIOR_ALREADY_DELIVERED_AND_WRONG = 86
PRIOR_INTENT_WRONG_FOLD_A_ROWS = 191


class ReadRefused(RuntimeError):
    """A recipe gate failed; the read closes without a conversion number."""

    def __init__(self, step: int, message: str) -> None:
        super().__init__(f"step {step}: {message}")
        self.step = step


def digest_file(path: Path) -> str:
    measured = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            measured.update(chunk)
    return measured.hexdigest()


def digest_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def bare(value_id: str) -> str:
    return value_id.split("::", 1)[1] if "::" in value_id else value_id


def iso_utc(epoch: float | None) -> str | None:
    if epoch is None:
        return None
    return datetime.fromtimestamp(float(epoch), tz=timezone.utc).isoformat()


def id_list_sha256(ids) -> str:
    return digest_text("\n".join(sorted(str(i) for i in ids)))


# --------------------------------------------------------------------------- intervals


def wilson_ci95(successes: int, trials: int) -> tuple[float, float]:
    if trials <= 0:
        raise ValueError("trials must be positive")
    p = successes / trials
    z2 = Z95 * Z95
    denominator = 1.0 + z2 / trials
    centre = (p + z2 / (2.0 * trials)) / denominator
    half = Z95 * math.sqrt(p * (1.0 - p) / trials + z2 / (4.0 * trials * trials)) / denominator
    return max(0.0, centre - half), min(1.0, centre + half)


def _binom_cdf(k: int, n: int, p: float) -> float:
    if p <= 0.0:
        return 1.0
    if p >= 1.0:
        return 1.0 if k >= n else 0.0
    total = 0.0
    for i in range(0, k + 1):
        total += math.comb(n, i) * (p**i) * ((1.0 - p) ** (n - i))
    return min(1.0, total)


def _bisect(func, target: float, lo: float = 0.0, hi: float = 1.0, iterations: int = 200) -> float:
    """Solve func(p) = target for a monotone-decreasing func on [lo, hi]."""

    for _ in range(iterations):
        mid = 0.5 * (lo + hi)
        if func(mid) > target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def clopper_pearson_ci95(successes: int, trials: int) -> tuple[float, float]:
    """Exact binomial CI95 by inverting the binomial CDF (no scipy): the lower bound
    solves P(X >= m | p) = 0.025 and the upper bound solves P(X <= m | p) = 0.025."""

    alpha = 0.05
    if successes <= 0:
        lower = 0.0
    else:
        # P(X >= m | p) = alpha/2  <=>  P(X <= m-1 | p) = 1 - alpha/2; the CDF decreases in p.
        lower = _bisect(lambda p: _binom_cdf(successes - 1, trials, p), 1.0 - alpha / 2.0)
    if successes >= trials:
        upper = 1.0
    else:
        upper = _bisect(lambda p: _binom_cdf(successes, trials, p), alpha / 2.0)
    return lower, upper


# --------------------------------------------------------------------------- loaders


def load_recipe(repo: Path) -> tuple[dict, str]:
    path = repo / RECIPE_RELPATH
    recipe = load_json(path)
    if recipe.get("recipe_id") != RECIPE_ID:
        raise ReadRefused(0, f"the committed recipe is {recipe.get('recipe_id')!r}, not {RECIPE_ID!r}")
    return recipe, digest_file(path)


def load_roster(repo: Path, recipe: dict) -> dict:
    roster = recipe["roster"]
    path = repo / str(roster["relpath"])
    sha = digest_file(path)
    if sha != roster["sha256"]:
        raise ReadRefused(0, "the committed roster derivation does not hash to the recipe's pin")
    document = load_json(path)
    ids = [str(i) for i in document["roster"]["ids"]]
    if len(ids) != int(roster["count"]) or len(set(ids)) != len(ids):
        raise ReadRefused(0, "the roster derivation does not carry the registered number of distinct ids")
    listed = id_list_sha256(ids)
    if listed != roster["id_list_sha256"] or listed != document["roster"]["id_list_sha256"]:
        raise ReadRefused(0, "the roster id list does not hash to the registered id-list sha256")
    return {
        "relpath": str(roster["relpath"]),
        "sha256": sha,
        "ids": sorted(ids),
        "id_list_sha256": listed,
        "split_identity_hash": document["roster"]["split_identity_hash"],
        "audio_seconds_total": document["roster"]["audio_seconds_total"],
    }


def load_probe(data_root: Path, recipe: dict, roster: dict) -> dict:
    arm = recipe["arms"]["probe"]
    run_id, attempt_id = str(arm["run_id"]), str(arm["attempt_id"])
    run_dir = data_root / "runs" / run_id / attempt_id
    if not run_dir.is_dir():
        raise ReadRefused(1, f"no sealed attempt directory for {run_id}/{attempt_id}")
    manifest_path = run_dir / f"{run_id}.run-manifest.json"
    manifest = load_json(manifest_path)
    if manifest.get("status") != "COMPLETED":
        raise ReadRefused(1, f"the sealed manifest is {manifest.get('status')!r}, not COMPLETED")
    if manifest.get("run_id") != run_id or (manifest.get("attempt") or {}).get("attempt_id") != attempt_id:
        raise ReadRefused(1, "the sealed manifest does not name this run and attempt")
    split = manifest["split"]
    if int(split["count"]) != len(roster["ids"]) or len(split["ids"]) != len(roster["ids"]):
        raise ReadRefused(1, f"the sealed manifest carries {split['count']} rows, not {len(roster['ids'])}")
    if id_list_sha256(split["ids"]) != roster["id_list_sha256"]:
        raise ReadRefused(1, "the sealed manifest's id list does not hash to the committed roster's")
    if split.get("identity_hash") != roster["split_identity_hash"]:
        raise ReadRefused(1, "the sealed manifest's split identity is not the committed roster's")
    if manifest.get("study_repo_dirt"):
        raise ReadRefused(1, "the sealed manifest records a dirty study tree")

    attempt_path = data_root / "attempts" / run_id / f"{attempt_id}.json"
    attempt = load_json(attempt_path)
    if attempt.get("state") != "FINALIZED":
        raise ReadRefused(1, f"the attempt record is {attempt.get('state')!r}, not FINALIZED")

    outputs_path = run_dir / f"{run_id}.outputs.jsonl"
    scores_path = run_dir / f"{run_id}.scores.json"
    phases_path = run_dir / f"{run_id}.phases.json"
    generation_path = run_dir / f"{run_id}.generation-manifest.json"
    receipts_path = run_dir / "flight-receipts.json"
    jobs_path = run_dir / "score-jobs.jsonl"
    summary_path = run_dir / "score-batch" / "batch-summary.json"
    hashes = {
        "run_manifest": digest_file(manifest_path),
        "outputs": digest_file(outputs_path),
        "scores": digest_file(scores_path),
        "phases": digest_file(phases_path),
        "generation_manifest": digest_file(generation_path),
        "flight_receipts": digest_file(receipts_path),
        "attempt_record": digest_file(attempt_path),
    }
    if hashes["outputs"] != manifest["outputs"]["sha256"]:
        raise ReadRefused(1, "the outputs file does not hash to the manifest's pin")
    if hashes["scores"] != manifest["scores"]["sha256"]:
        raise ReadRefused(1, "the scores file does not hash to the manifest's pin")
    receipts = load_json(receipts_path)
    seal = receipts["stages"]["seal"]
    if seal.get("phases_sha256") != hashes["phases"]:
        raise ReadRefused(1, "the phase artefact does not hash to the seal receipt's pin")
    if seal.get("generation_manifest_sha256") != hashes["generation_manifest"]:
        raise ReadRefused(1, "the generation manifest does not hash to the seal receipt's pin")
    # The seal pins the manifest as sealed; finalize rewrites it with the score block, and the
    # score stage pins that finalized manifest, which is the one on disk.
    if (receipts["stages"].get("score") or {}).get("finalized_manifest_sha256") != hashes["run_manifest"]:
        raise ReadRefused(1, "the run manifest does not hash to the score stage's finalized-manifest pin")
    hashes["sealed_manifest_before_finalize"] = seal.get("manifest_sha256")
    if int(seal.get("outputs_row_count", -1)) != len(roster["ids"]):
        raise ReadRefused(1, "the seal receipt's output row count is not the roster size")

    # One official complete score, never sharded.
    jobs = [json.loads(line) for line in jobs_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    summary = load_json(summary_path)
    if len(jobs) != 1 or int(summary.get("job_count", 0)) != 1 or int(summary.get("succeeded", 0)) != 1:
        raise ReadRefused(3, "the sealed attempt does not carry exactly one succeeded official scoring job")
    job = summary["jobs"][0]
    score_result_path = run_dir / "score-batch" / str(job["result_file"])
    if digest_file(score_result_path) != job["result_sha256"]:
        raise ReadRefused(3, "the official scoring result does not hash to the batch summary's pin")
    hashes["score_batch_result"] = job["result_sha256"]
    if SCORER not in manifest.get("scorers", []):
        raise ReadRefused(3, f"the sealed manifest does not name the {SCORER} scorer")

    scores = load_json(scores_path)
    block = scores[SCORER]
    per_sample = {str(row["sample_id"]): row for row in block["per_sample"]}
    if sorted(per_sample) != roster["ids"]:
        raise ReadRefused(3, "the official per-sample id set is not the committed roster")
    if int(block["aggregate"]["samples"]) != len(roster["ids"]):
        raise ReadRefused(3, "the official aggregate does not count the roster")
    mean_exact = sum(float(r[FIELD]) for r in per_sample.values()) / len(per_sample)
    official_intent = float(block["aggregate"]["official"]["intent_accuracy"])
    if abs(mean_exact - official_intent) > 1e-9:
        raise ReadRefused(3, "the per-sample scenario_action_exact mean does not reproduce the official intent accuracy")

    outputs: dict[str, dict] = {}
    with outputs_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            outputs[str(record["sample_id"])] = record
    if sorted(outputs) != roster["ids"]:
        raise ReadRefused(1, "the outputs file's id set is not the committed roster")

    return {
        "run_id": run_id,
        "attempt_id": attempt_id,
        "run_dir": str(run_dir),
        "manifest": manifest,
        "attempt": attempt,
        "receipts": receipts,
        "generation": load_json(generation_path),
        "phases_path": phases_path,
        "scores_block": block,
        "per_sample": per_sample,
        "outputs": outputs,
        "hashes": hashes,
        "score_job": {
            "job_id": job["job_id"],
            "status": job["status"],
            "result_file": job["result_file"],
            "result_sha256": job["result_sha256"],
            "elapsed_seconds": job["elapsed_seconds"],
        },
    }


def load_bank_rows(data_root: Path, recipe: dict, ids: list[str]) -> dict:
    pin = recipe["arms"]["comparator"]["per_row_intent_verdict_authority"]
    path = data_root / str(pin["relpath"])
    sha = digest_file(path)
    if sha != pin["sha256"]:
        raise ReadRefused(4, "the bad-case bank does not hash to the recipe's pin")
    wanted = set(ids)
    rows: dict[str, dict] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry.get("roster") != BANK_ROSTER or entry.get("sample_id") not in wanted:
                continue
            if entry["sample_id"] in rows:
                raise ReadRefused(4, "the bank carries a roster row twice")
            rows[str(entry["sample_id"])] = {
                "plan_class": entry.get("plan_class"),
                "gold_intent": entry.get("gold_intent"),
                "delivered_intent": entry.get("delivered_intent"),
            }
    if sorted(rows) != sorted(ids):
        raise ReadRefused(4, f"the bank's {BANK_ROSTER} roster carries {len(rows)} of the {len(ids)} probe rows")
    classes = Counter(row["plan_class"] for row in rows.values())
    if set(classes) != {PLAN_CLASS}:
        raise ReadRefused(4, f"the bank classes of the probe rows are {dict(classes)}, not all {PLAN_CLASS}")
    if any(not row["gold_intent"] for row in rows.values()):
        raise ReadRefused(4, "a bank row carries no gold intent")
    return {"relpath": str(pin["relpath"]), "sha256": sha, "rows": rows, "plan_classes": dict(classes)}


def load_comparator(data_root: Path, recipe: dict, ids: list[str]) -> dict:
    arm = recipe["arms"]["comparator"]
    run_id, attempt_id = str(arm["run_id"]), str(arm["attempt_id"])
    run_dir = data_root / "runs" / run_id / attempt_id
    manifest_path = run_dir / f"{run_id}.run-manifest.json"
    manifest = load_json(manifest_path)
    if manifest.get("status") != "COMPLETED":
        raise ReadRefused(4, "the sealed comparator manifest is not COMPLETED")
    scores_path = run_dir / f"{run_id}.scores.json"
    outputs_path = run_dir / f"{run_id}.outputs.jsonl"
    hashes = {
        "run_manifest": digest_file(manifest_path),
        "scores": digest_file(scores_path),
        "outputs": digest_file(outputs_path),
    }
    if hashes["scores"] != manifest["scores"]["sha256"] or hashes["outputs"] != manifest["outputs"]["sha256"]:
        raise ReadRefused(4, "the comparator's sealed files do not hash to its manifest's pins")
    block = load_json(scores_path)[SCORER]
    wanted = set(ids)
    per_sample = {str(r["sample_id"]): r for r in block["per_sample"] if str(r["sample_id"]) in wanted}
    if sorted(per_sample) != sorted(ids):
        raise ReadRefused(4, "the comparator's official per-sample rows do not cover the probe roster")
    outputs: dict[str, dict] = {}
    with outputs_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            sample_id = str(record.get("sample_id"))
            if sample_id in wanted:
                outputs[sample_id] = {
                    "text": record.get("text") or "",
                    "response_text_sha256": record.get("response_text_sha256"),
                }
    if sorted(outputs) != sorted(ids):
        raise ReadRefused(4, "the comparator's outputs do not cover the probe roster")
    return {
        "run_id": run_id,
        "attempt_id": attempt_id,
        "manifest_rows": int(manifest["split"]["count"]),
        "study_commit": manifest.get("study_commit"),
        "hashes": hashes,
        "per_sample": per_sample,
        "outputs": outputs,
    }


# --------------------------------------------------------------------------- steps


def delivery_check(phases_path: Path, ids: list[str], bank_rows: dict) -> dict:
    document = load_json(phases_path)
    if document.get("schema") != "saea-flight-phase-summaries-v1":
        raise ReadRefused(2, "unexpected phase artefact schema")
    if len(document.get("phases") or []) != 1:
        raise ReadRefused(2, "the phase artefact does not bind exactly one phase program")
    summary = document["phases"][0]
    results = {str(r["sample_id"]): r for r in summary["results"]}
    if sorted(results) != sorted(ids):
        raise ReadRefused(2, "the phase artefact's result rows are not the committed roster")
    delivered = 0
    width_histogram: Counter = Counter()
    gold_outcomes: Counter = Counter()
    record_outcomes: Counter = Counter()
    missing: list[str] = []
    for sample_id in sorted(ids):
        records = ((results[sample_id].get("consumption") or {}).get("records")) or ()
        boundary_items: dict[str, list[str]] = {}
        for record in records:
            item = bare(str(record.get("supplied_item_id") or ""))
            if item.startswith(BOUNDARY_PREFIX):
                boundary_items.setdefault(item, []).append(str(record.get("outcome")))
                record_outcomes[str(record.get("outcome"))] += 1
        width_histogram[len(boundary_items)] += 1
        gold_id = f"{BOUNDARY_PREFIX}{bank_rows[sample_id]['gold_intent']}"
        if gold_id in boundary_items:
            delivered += 1
            for outcome in boundary_items[gold_id]:
                gold_outcomes[outcome] += 1
        else:
            missing.append(sample_id)
    return {
        "rows": len(ids),
        "gold_boundary_delivered_rows": delivered,
        "predicted_by_the_offline_derivation": len(ids),
        "rows_missing_the_gold_entry": missing,
        "boundary_items_per_row_histogram": {str(k): v for k, v in sorted(width_histogram.items())},
        "gold_entry_record_outcomes": dict(sorted(gold_outcomes.items())),
        "all_boundary_record_outcomes": dict(sorted(record_outcomes.items())),
        "controller_policy_id": summary.get("controller_policy_id"),
        "knowledge_snapshot_sha256": summary.get("knowledge_snapshot_sha256"),
    }


def parsed_intent(text: str) -> str:
    scenario, action, _entities, parsed = parse_slu_response(text or "")
    if parsed and isinstance(scenario, str) and isinstance(action, str):
        return f"{scenario}_{action}"
    return UNPARSED


def contrast(ids: list[str], probe: dict, comparator: dict, bank_rows: dict) -> dict:
    per_row: list[dict] = []
    classes: Counter = Counter()
    disagreements: list[dict] = []
    bank_parse_disagreements = 0
    probe_parse_vs_scorer_disagreements = 0
    byte_identical_unchanged = 0
    raw_identical_unchanged = 0
    byte_identical_all_stay_wrong = 0
    byte_identical_converted = 0
    normaliser_changed_rows = 0
    unparsed_probe = 0
    for sample_id in sorted(ids):
        probe_exact = float(probe["per_sample"][sample_id][FIELD]) >= 0.5
        comparator_exact = float(comparator["per_sample"][sample_id][FIELD]) >= 0.5
        bank_wrong = bank_rows[sample_id]["plan_class"] == PLAN_CLASS
        if comparator_exact == bank_wrong:
            disagreements.append({"sample_id": sample_id, "bank_says_wrong": bank_wrong, "official_exact": comparator_exact})
        gold = str(bank_rows[sample_id]["gold_intent"])
        probe_text = str(probe["outputs"][sample_id].get("text") or "")
        comparator_text = str(comparator["outputs"][sample_id]["text"])
        probe_intent = parsed_intent(probe_text)
        comparator_intent = parsed_intent(comparator_text)
        bank_delivered = bank_rows[sample_id]["delivered_intent"]
        if (bank_delivered or UNPARSED) != comparator_intent and not (bank_delivered is None and comparator_intent == UNPARSED):
            bank_parse_disagreements += 1
        if (probe_intent == gold) != probe_exact:
            probe_parse_vs_scorer_disagreements += 1
        if probe_intent == UNPARSED:
            unparsed_probe += 1
        receipt = probe["outputs"][sample_id].get("native_episode_receipt") or {}
        if (receipt.get("deliver_normaliser") or {}).get("changed"):
            normaliser_changed_rows += 1
        bytes_identical = probe_text == comparator_text
        raw_identical = (
            probe["outputs"][sample_id].get("response_text_sha256") is not None
            and probe["outputs"][sample_id].get("response_text_sha256") == comparator["outputs"][sample_id]["response_text_sha256"]
        )
        if probe_exact and not comparator_exact:
            transition = "wrong-to-gold"
            byte_identical_converted += int(bytes_identical)
        elif comparator_exact and not probe_exact:
            transition = "gold-to-wrong"
        elif probe_intent == comparator_intent:
            transition = "unchanged-wrong"
            byte_identical_unchanged += int(bytes_identical)
            raw_identical_unchanged += int(raw_identical)
            byte_identical_all_stay_wrong += int(bytes_identical)
        else:
            transition = "different-wrong"
            byte_identical_all_stay_wrong += int(bytes_identical)
        classes[transition] += 1
        per_row.append(
            {
                "sample_id": sample_id,
                "comparator_intent_exact": comparator_exact,
                "probe_intent_exact": probe_exact,
                "transition": transition,
                "delivered_text_byte_identical": bytes_identical,
                "raw_response_text_sha256_identical": raw_identical,
                "probe_text_sha256": digest_text(probe_text),
                "comparator_text_sha256": digest_text(comparator_text),
            }
        )
    if disagreements:
        raise ReadRefused(4, f"the bank and the sealed official score disagree on {len(disagreements)} comparator verdicts")
    if bank_parse_disagreements:
        raise ReadRefused(4, f"the bank's delivered intent disagrees with the parsed comparator output on {bank_parse_disagreements} rows")
    m = classes["wrong-to-gold"]
    r = classes["gold-to-wrong"]
    if r != 0:
        raise ReadRefused(5, f"the reverse count is {r}, not 0: the roster or the comparator was misread")
    n = len(ids)
    unchanged = classes["unchanged-wrong"]
    different = classes["different-wrong"]
    stay_wrong = n - m
    return {
        "rows": n,
        "m_wrong_to_gold": m,
        "r_gold_to_wrong": r,
        "r_is_zero_by_construction": True,
        "unchanged_wrong": unchanged,
        "different_wrong": different,
        "stay_wrong": stay_wrong,
        "stay_wrong_split": {
            "byte_identical_answer": byte_identical_all_stay_wrong,
            "different_wrong_intent": different,
            "same_wrong_intent_different_bytes": unchanged - byte_identical_unchanged,
        },
        "within_pair_identity_on_unchanged_intent_rows": {
            "rows": unchanged,
            "delivered_text_byte_identical": byte_identical_unchanged,
            "rate": round(byte_identical_unchanged / unchanged, 6) if unchanged else None,
            "raw_response_text_sha256_identical": raw_identical_unchanged,
        },
        "byte_identical_among_converted_rows": byte_identical_converted,
        "probe_rows_unparsed": unparsed_probe,
        "probe_parse_vs_scorer_disagreements": probe_parse_vs_scorer_disagreements,
        "bank_delivered_intent_vs_parsed_comparator_disagreements": bank_parse_disagreements,
        "deliver_normaliser_changed_rows": normaliser_changed_rows,
        "per_row": per_row,
    }


def rate_block(m: int, n: int) -> dict:
    wilson = wilson_ci95(m, n)
    exact = clopper_pearson_ci95(m, n)
    return {
        "estimand": "P(correct | newly delivered) = m / 70, one binomial proportion over independent rows",
        "m": m,
        "n": n,
        "point": round(m / n, 6),
        "wilson_ci95": [round(wilson[0], 6), round(wilson[1], 6)],
        "clopper_pearson_ci95": [round(exact[0], 6), round(exact[1], 6)],
        "no_bootstrap_because": "the estimand is one binomial proportion, not a paired difference of pooled metrics",
    }


def redeclaration_block(m: int, n: int) -> dict:
    rows_to_clear_intent = math.ceil(ARM_BAR_PP / INTENT_PP_PER_ROW)
    rows_to_clear_slu = math.ceil(ARM_BAR_PP / SLU_PP_PER_ROW)
    return {
        "stated_not_applied": True,
        "rule": (
            "the AGREE arm's re-declared expected_effect_pp = m x 0.041615 pp SLU-F1 and "
            "m x 0.092615 pp intent accuracy (equivalently the 2.9131 / 6.4831 pp ceilings x m/70)"
        ),
        "intent_framing_owner_decision_133": {
            "primary_metric": "intent accuracy",
            "expected_effect_pp": round(m * INTENT_PP_PER_ROW, 4),
            "ceiling_times_conversion_pp": round(ARM_CEILING_INTENT_PP * m / n, 4),
            "bar_pp_at_n_1080": ARM_BAR_PP,
            "rows_needed_to_clear_the_bar": rows_to_clear_intent,
            "m_clears_the_bar": m >= rows_to_clear_intent,
            "guard": "official SLU-F1 as the non-inferiority guard",
        },
        "slu_f1_framing_retired": {
            "primary_metric": "official SLU-F1 (the framing decision 133 retired for this mechanism)",
            "expected_effect_pp": round(m * SLU_PP_PER_ROW, 4),
            "ceiling_times_conversion_pp": round(ARM_CEILING_SLU_PP * m / n, 4),
            "bar_pp_at_n_1080": ARM_BAR_PP,
            "rows_needed_to_clear_the_bar": rows_to_clear_slu,
            "m_clears_the_bar": m >= rows_to_clear_slu,
        },
        "the_only_directly_observable_prior": {
            "already_delivered_and_still_wrong": PRIOR_ALREADY_DELIVERED_AND_WRONG,
            "of_intent_wrong_fold_a_rows": PRIOR_INTENT_WRONG_FOLD_A_ROWS,
        },
        "boundary": (
            "a CONDITIONAL rate on a gold-selected TRAIN roster: not a pooled effect, not a "
            "roster-level claim, and this cell cannot see harm on already-correct rows. Whether the "
            "arm is re-declared, flown as a no-harm base item or closed is not decided here."
        ),
    }


def spend_block(probe: dict, data_root: Path) -> dict:
    manifest = probe["manifest"]
    cost = manifest["cost"]
    plan = manifest["plan"]
    receipts = probe["receipts"]["stages"]
    seal = receipts["seal"]
    run_phases = receipts.get("run_phases") or {}
    monitor = seal.get("serving_monitor_summary") or {}
    dispatch = run_phases.get("dispatch") or {}
    per_row_contacts = Counter(int(e["contacts"]) for e in dispatch.get("contacts_per_sample_observed") or [])
    fit_receipts = dispatch.get("native_contact_fit_receipts") or []
    fit_classes = Counter(str(e.get("contact_class")) for e in fit_receipts)
    reasons: Counter = Counter()
    actions: Counter = Counter()
    revisions: Counter = Counter()
    illegal_rows = 0
    react_rows = 0
    compaction_contacts = 0
    role_visits: Counter = Counter()
    admitted = 0
    for record in probe["outputs"].values():
        admitted += int(bool(record.get("admitted")))
        receipt = record.get("native_episode_receipt") or {}
        for route in receipt.get("planner_routes") or []:
            actions[str(route.get("action"))] += 1
            revisions[int(route.get("revision_count", 0))] += 1
        disposition = receipt.get("terminal_disposition")
        if isinstance(disposition, dict):
            reason = str(disposition.get("reason"))
            reasons[reason] += 1
            if "exhaust" in reason:
                react_rows += 1
        if isinstance(receipt.get("planner_action_illegal"), dict):
            illegal_rows += 1
        compaction_contacts += int((receipt.get("context_fit") or {}).get("compacted_contacts") or 0)
        role_visits[len(receipt.get("role_visits") or [])] += 1
    fit_run_dir = data_root / "runs" / FIT_RUN_ID
    fit_attempt_dir = data_root / "attempts" / FIT_RUN_ID
    return {
        "contacts_used": int(cost["calls_used"]),
        "contacts_cap": int(plan["planned_model_calls"]),
        "contacts_per_row": round(int(cost["calls_used"]) / int(manifest["split"]["count"]), 4),
        "contacts_per_row_histogram": {str(k): v for k, v in sorted(per_row_contacts.items())},
        "contacts_per_row_ceiling": dispatch.get("contacts_per_sample_ceiling"),
        "audio_seconds_used": float(cost["audio_seconds_used"]),
        "audio_seconds_cap": int(plan["planned_speech_audio_seconds"]),
        "attempt_record_actual": probe["attempt"].get("actual"),
        "attempt_record_reserved": probe["attempt"].get("reserved"),
        "prompt_tokens_total": int(cost["prompt_tokens_total"]),
        "completion_tokens_total": int(cost["completion_tokens_total"]),
        "latency_seconds_total": float(cost["latency_seconds_total"]),
        "tool_calls": int(cost["tool_calls"]),
        "gpu": {
            "source": "flight-receipts.json stages.seal.serving_monitor_summary (nvidia-smi sampler)",
            "active_seconds": monitor.get("active_seconds"),
            "active_minutes": round(float(monitor["active_seconds"]) / 60.0, 3) if monitor.get("active_seconds") is not None else None,
            "active_gpu_hours": round(float(monitor["active_seconds"]) / 3600.0, 5) if monitor.get("active_seconds") is not None else None,
            "wall_seconds": monitor.get("wall_seconds"),
            "wall_minutes": round(float(monitor["wall_seconds"]) / 60.0, 3) if monitor.get("wall_seconds") is not None else None,
            "mean_utilization_percent": monitor.get("mean_utilization_percent"),
            "parked_fraction": monitor.get("parked_fraction"),
            "mean_power_watts": monitor.get("mean_power_watts"),
            "sample_count": monitor.get("sample_count"),
            "window_utc": {
                "from": iso_utc((monitor.get("window") or {}).get("from")),
                "to": iso_utc((monitor.get("window") or {}).get("to")),
            },
            "planned_gpu_hours_cap": plan.get("planned_gpu_hours"),
        },
        "contact_window_utc": {
            "from": iso_utc((run_phases.get("contact_window") or {}).get("from")),
            "to": iso_utc((run_phases.get("contact_window") or {}).get("to")),
        },
        "dispositions": {
            "run_phases_native_episode_dispositions": run_phases.get("native_episode_dispositions"),
            "terminal_disposition_reasons": dict(sorted(reasons.items())),
            "finite_completion_rows": reasons.get("finite_completion", 0),
            "revision_limit_rows": reasons.get("revision_limit", 0),
            "planner_action_illegal_rows": illegal_rows,
            "react_exhaustion_rows": react_rows,
            "context_compaction_contacts": compaction_contacts,
            "planner_route_actions": dict(sorted(actions.items())),
            "revision_count_histogram": {str(k): v for k, v in sorted(revisions.items())},
            "role_visits_per_row_histogram": {str(k): v for k, v in sorted(role_visits.items())},
            "admitted_rows": admitted,
        },
        "fit": {
            "fit_run_id": FIT_RUN_ID,
            "fit_run_directory_exists": fit_run_dir.exists(),
            "fit_attempt_record_exists": fit_attempt_dir.exists(),
            "native_contact_fit_receipts_inside_the_generation_attempt": len(fit_receipts),
            "fit_receipt_contact_classes": dict(sorted(fit_classes.items())),
        },
        "official_scoring": probe["score_job"],
        "study_commit": manifest.get("study_commit"),
        "session_receipt_sha256": (manifest.get("session_receipt") or {}).get("sha256"),
        "config_hash": (manifest.get("config") or {}).get("config_hash"),
        "protocol_hash": manifest.get("protocol_hash"),
    }


# --------------------------------------------------------------------------- rendering


def fmt_ci(bounds: list[float]) -> str:
    return f"[{100 * bounds[0]:.2f} %, {100 * bounds[1]:.2f} %]"


def render_markdown(result: dict) -> str:
    c = result["contrast"]
    rate = result["rate"]
    d = result["delivery_check"]
    s = result["spend"]
    r = result["redeclaration"]
    g = s["gpu"]
    lines = [
        f"# Cell CONV read: m = {c['m_wrong_to_gold']} of {c['rows']}",
        "",
        f"Recipe `{result['recipe']['recipe_id']}`; generated {result['generated_at_utc']}; driver "
        f"`{result['driver']['relpath']}` sha256 `{result['driver']['sha256']}`.",
        "",
        "## Gates",
        "",
        "| step | gate | result |",
        "| --- | --- | --- |",
        f"| 1 | manifest COMPLETED at {c['rows']} rows, id-list sha256 equal to the committed roster | held |",
        f"| 2 | gold boundary entry delivered on all rows | {d['gold_boundary_delivered_rows']} / {d['rows']} (derivation predicted {d['predicted_by_the_offline_derivation']}) |",
        f"| 3 | one official complete score, per-sample `{FIELD}` read from the seal | held (job `{s['official_scoring']['status']}`) |",
        "| 4 | comparator verdict: bank class and sealed official score agree on every row | held |",
        f"| 5 | reverse count r | {c['r_gold_to_wrong']} |",
        "",
        "## The number",
        "",
        "| quantity | value |",
        "| --- | ---: |",
        f"| m, rows moved wrong to gold | **{c['m_wrong_to_gold']}** |",
        f"| P(correct given newly delivered) | **{100 * rate['point']:.2f} %** |",
        f"| Wilson CI95 | {fmt_ci(rate['wilson_ci95'])} |",
        f"| Clopper-Pearson CI95 (exact) | {fmt_ci(rate['clopper_pearson_ci95'])} |",
        "",
        "## Four-way row split",
        "",
        "| transition | rows |",
        "| --- | ---: |",
        f"| wrong to gold (m) | {c['m_wrong_to_gold']} |",
        f"| gold to wrong (r, zero by construction) | {c['r_gold_to_wrong']} |",
        f"| unchanged wrong (same wrong intent) | {c['unchanged_wrong']} |",
        f"| a different wrong intent | {c['different_wrong']} |",
        "",
        f"Stay-wrong split of the {c['stay_wrong']} rows: byte-identical delivered answer "
        f"{c['stay_wrong_split']['byte_identical_answer']}, different wrong intent "
        f"{c['stay_wrong_split']['different_wrong_intent']}, same wrong intent in different bytes "
        f"{c['stay_wrong_split']['same_wrong_intent_different_bytes']}.",
        "",
        "## Within-pair identity on rows whose intent did not change",
        "",
        f"{c['within_pair_identity_on_unchanged_intent_rows']['delivered_text_byte_identical']} of "
        f"{c['within_pair_identity_on_unchanged_intent_rows']['rows']} delivered answers byte-identical "
        f"({(100 * (c['within_pair_identity_on_unchanged_intent_rows']['rate'] or 0)):.1f} %); "
        f"raw response text sha256 identical on "
        f"{c['within_pair_identity_on_unchanged_intent_rows']['raw_response_text_sha256_identical']}. "
        f"Deliver-normaliser changed {c['deliver_normaliser_changed_rows']} probe rows; "
        f"probe rows unparsed {c['probe_rows_unparsed']}.",
        "",
        "## Spend",
        "",
        "| quantity | value |",
        "| --- | ---: |",
        f"| contacts used / cap | {s['contacts_used']} / {s['contacts_cap']} ({s['contacts_per_row']} per row) |",
        f"| speech audio seconds used / cap | {s['audio_seconds_used']:.3f} / {s['audio_seconds_cap']} |",
        f"| GPU active minutes (monitor) | {g['active_minutes']} ({g['active_gpu_hours']} GPU-h) |",
        f"| GPU wall minutes (monitor window) | {g['wall_minutes']} at mean utilisation {g['mean_utilization_percent']:.1f} %, parked fraction {g['parked_fraction']:.3f} |",
        f"| prompt / completion tokens | {s['prompt_tokens_total']:,} / {s['completion_tokens_total']:,} |",
        f"| tool calls | {s['tool_calls']} |",
        f"| dispositions | finite_completion {s['dispositions']['finite_completion_rows']}, revision_limit {s['dispositions']['revision_limit_rows']}, planner_action_illegal {s['dispositions']['planner_action_illegal_rows']}, react_exhaustion {s['dispositions']['react_exhaustion_rows']}, context compaction contacts {s['dispositions']['context_compaction_contacts']} |",
        f"| terminal disposition reasons | {s['dispositions']['terminal_disposition_reasons']} |",
        f"| planner route actions | {s['dispositions']['planner_route_actions']} |",
        f"| fit receipts inside the generation attempt | {s['fit']['native_contact_fit_receipts_inside_the_generation_attempt']} ({s['fit']['fit_receipt_contact_classes']}); FIT run id opened an attempt: {s['fit']['fit_attempt_record_exists']} |",
        "",
        "## Re-declaration arithmetic, stated and not applied",
        "",
        "| framing | expected effect | rows needed | m clears |",
        "| --- | ---: | ---: | --- |",
        f"| intent primary (decision 133) | {r['intent_framing_owner_decision_133']['expected_effect_pp']} pp | {r['intent_framing_owner_decision_133']['rows_needed_to_clear_the_bar']} | {r['intent_framing_owner_decision_133']['m_clears_the_bar']} |",
        f"| SLU-F1 primary (retired) | {r['slu_f1_framing_retired']['expected_effect_pp']} pp | {r['slu_f1_framing_retired']['rows_needed_to_clear_the_bar']} | {r['slu_f1_framing_retired']['m_clears_the_bar']} |",
        "",
        f"Prior: {r['the_only_directly_observable_prior']['already_delivered_and_still_wrong']} of the "
        f"{r['the_only_directly_observable_prior']['of_intent_wrong_fold_a_rows']} intent-wrong Fold A rows already "
        "received the gold entry in the sealed comparator and were wrong anyway.",
        "",
        r["boundary"],
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- main


def run(args: argparse.Namespace) -> int:
    repo = Path(args.repo_root).resolve()
    data_root = Path(args.data_root).resolve()
    generated = datetime.now(timezone.utc).isoformat()
    recipe, recipe_sha = load_recipe(repo)
    output_root = Path(args.output_root) if args.output_root else data_root / str(recipe["output"]["analysis_root"])
    output_root.mkdir(parents=True, exist_ok=True)
    driver = {"relpath": str(Path(__file__).resolve().relative_to(repo)), "sha256": digest_file(Path(__file__))}
    try:
        roster = load_roster(repo, recipe)
        probe = load_probe(data_root, recipe, roster)
        bank = load_bank_rows(data_root, recipe, roster["ids"])
        delivery = delivery_check(probe["phases_path"], roster["ids"], bank["rows"])
        if delivery["gold_boundary_delivered_rows"] != delivery["rows"]:
            raise ReadRefused(
                2,
                f"the flown Perception consumption delivered the gold boundary entry on "
                f"{delivery['gold_boundary_delivered_rows']} of {delivery['rows']} rows, not all of them: "
                "an engineering defect, and the read closes with no conversion number",
            )
        comparator = load_comparator(data_root, recipe, roster["ids"])
        contrast_block = contrast(roster["ids"], probe, comparator, bank["rows"])
    except ReadRefused as refused:
        receipt = {
            "schema": "saea-conv-probe-read-refusal-v1",
            "driver": driver,
            "generated_at_utc": generated,
            "recipe_id": recipe["recipe_id"],
            "recipe_sha256": recipe_sha,
            "refused_at_step": refused.step,
            "reason": str(refused),
            "conversion_number_written": False,
            "contacts": {"model": 0, "tokenizer": 0, "encoder": 0, "embedder": 0, "scorer": 0, "server": 0, "network": 0},
        }
        path = output_root / "refusal-v1.json"
        path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"READ REFUSED at {refused}", file=sys.stderr)
        print(f"refusal receipt: {path}", file=sys.stderr)
        return 2

    m, n = contrast_block["m_wrong_to_gold"], contrast_block["rows"]
    result = {
        "schema": "saea-conv-probe-read-v1",
        "driver": driver,
        "generated_at_utc": generated,
        "recipe": {"recipe_id": recipe["recipe_id"], "relpath": str(RECIPE_RELPATH), "sha256": recipe_sha},
        "roster": {k: v for k, v in roster.items() if k != "ids"},
        "probe": {
            "run_id": probe["run_id"],
            "attempt_id": probe["attempt_id"],
            "manifest_status": probe["manifest"]["status"],
            "attempt_state": probe["attempt"]["state"],
            "study_commit": probe["manifest"].get("study_commit"),
            "hashes": probe["hashes"],
            "official_aggregate": {
                "intent_accuracy": probe["scores_block"]["aggregate"]["official"]["intent_accuracy"],
                "scenario_accuracy": probe["scores_block"]["aggregate"]["official"]["scenario_accuracy"],
                "action_accuracy": probe["scores_block"]["aggregate"]["official"]["action_accuracy"],
                "slu_f1": probe["scores_block"]["aggregate"]["official"]["slu_f1"],
                "span_f1": probe["scores_block"]["aggregate"]["official"]["span_f1"],
                "samples": probe["scores_block"]["aggregate"]["samples"],
                "note": "reported for the record only; a pooled number over a gold-selected roster is a selection artefact and is not a claim",
            },
        },
        "comparator": {
            "run_id": comparator["run_id"],
            "attempt_id": comparator["attempt_id"],
            "manifest_rows": comparator["manifest_rows"],
            "study_commit": comparator["study_commit"],
            "hashes": comparator["hashes"],
            "bank": {"relpath": bank["relpath"], "sha256": bank["sha256"], "plan_classes_of_the_probe_rows": bank["plan_classes"]},
        },
        "delivery_check": delivery,
        "contrast": contrast_block,
        "rate": rate_block(m, n),
        "redeclaration": redeclaration_block(m, n),
        "spend": spend_block(probe, data_root),
        "boundary": recipe["boundary"],
        "contacts": {"model": 0, "tokenizer": 0, "encoder": 0, "embedder": 0, "scorer": 0, "server": 0, "network": 0},
    }
    json_path = output_root / "read-v1.json"
    json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown = render_markdown(result)
    md_path = output_root / "read-v1.md"
    md_path.write_text(markdown, encoding="utf-8")
    print(markdown)
    print(f"read-v1.json sha256 {digest_file(json_path)}")
    print(f"read-v1.md sha256 {digest_file(md_path)}")
    print(f"written under {output_root}")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--output-root", default=None, help="defaults to the recipe's analysis_root under --data-root")
    return parser


def main(argv: list[str] | None = None) -> int:
    return run(build_arg_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
