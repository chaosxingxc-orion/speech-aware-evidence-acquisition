#!/usr/bin/env python3
"""rankvis_probe_read.py -- the READ DRIVER for cell RANKVIS, the rank-ordered
rank-visible rendering conversion probe (owner decision 171; the read owed by
root per docs/readiness/2026-09-27-slurp-stage3-rankvis-probe-fold-a-v1's own
registered-facts-v1.json, ``read_rule``, written here in KPROBE's shape --
scripts/analysis/slurp_kprobe_read.py -- and CONV's -- scripts/analysis/
slurp_conv_probe_read.py).

WHAT IT MEASURES. Of the 119 TRAIN Fold A rows where the sealed AGREE arm
delivered the gold intent's boundary entry and still answered a wrong intent,
how many move to the gold intent when the delivered boundary and exemplar
blocks are rendered in retrieval-rank order with the rank shown, and nothing
else changes. ``m`` is read against the no-op expectation (15.906 rows, the
error-source read's own null save rates applied to this roster), never
against zero, and beside the 89-row synthesis subset (no-op 11.459).

THE RECIPE (preregistration.md / registered-facts-v1.json ``read_rule``),
followed step by step, refusals honoured before any number is written:

  1. the committed registered facts and roster derivation hash to their own
     pins, and the sealed manifest is COMPLETED at 119 rows with the
     registered id-list hash and this cell's registered config hash (the
     generation plan the flip mints, ``generation-plan-registered-v1.json``,
     is what names the flown attempt and the composed config hash: this
     driver refuses before that file exists, i.e. before the cell is
     flipped);
  2. THE RENDERING GATE, two parts:
       (a) the registered baseline fragment -- the one byte the flown config
           differs from AGREE's by -- declares the expected
           ``knowledge_value_rendering`` block (order retrieval-rank,
           rank_visible true, the two named stores): a flight composed from
           it renders EVERY value of those stores with the
           ``retrieval rank <r>: `` label, by construction of the merged and
           unit-tested renderer (tests/unit/test_knowledge_value_rendering.py);
       (b) PER ROW and per named store, the flown order equals the
           recomputed retrieval-rank order:
             - ``intent-boundaries`` never reorders under this key (the
               associated-values fuser already delivers it in rank order,
               proven once by the roster derivation's own Proof B), so the
               check is that the probe's own sealed first-phase seed
               (``initial_query_state.retrieved_value_ids``, filtered to this
               store) equals the same row's sealed AGREE seed -- the
               treatment changes no byte of the seed, only the label;
             - ``train-exemplars`` DOES reorder, so its recomputation calls
               the REAL ``rails.runner.order_supply_by_retrieval_rank`` (the
               same function ``rails.runner._invoke_native_role_episode``
               calls at a flight's own supply step, and the same one
               ``analysis.native_episode_dry_run`` now calls) over a sealed
               ``retrieval-rank-inputs`` sidecar this driver reads beside the
               run (schema below); absent that sidecar, or on any mismatch,
               the row is UNVERIFIED and the read refuses;
     the read refuses -- and writes a refusal receipt, never a conversion
     number -- unless every one of the 119 rows is verified on both stores;
  3. the official scorer already ran ONCE over the complete manifest at
     finalize (``core.scoring_batch``); this driver READS its sealed
     per-sample ``scenario_action_exact`` and never re-runs it;
  4. the comparator (the sealed AGREE arm) is intent-wrong on all 119 rows
     BY CONSTRUCTION (the roster's own definition); the read refuses if the
     sealed official score disagrees on any row;
  5. ``m`` = rows whose probe verdict is exact; there is no reverse count
     (the comparator holds no correct row on this roster to lose);
  6. Wilson score CI95 with the exact Clopper-Pearson CI95 beside it, no
     bootstrap, reported for the full 119 and for the pre-declared 89-row
     synthesis subset;
  7. the four-way transition split (wrong to gold; the reverse, zero by
     construction; the same wrong intent; a different wrong intent), and the
     split by stage (PERCEPTION-DROP / SOLVER-CHOICE / UNPARSED);
  8. the re-declaration arithmetic, STATED and not applied:
     ``(m - 15.906) x 0.092615`` pp intent accuracy, the 43-row threshold, and
     which side of it ``m`` falls.

THE RETRIEVAL-RANK-INPUTS SIDECAR (schema
``saea-rankvis-retrieval-rank-inputs-v1``, this driver's own contract, not
yet sealed by any flight -- RANKVIS has not flown; see the report this
driver's caller returns). Expected beside the sealed run at
``<run_dir>/<run_id>.retrieval-rank-inputs.json``::

    {"schema": "saea-rankvis-retrieval-rank-inputs-v1",
     "rows": {"<sample_id>": {"train-exemplars": {
         "snapshot_sha256": "<hex>", "query_state_sha256": "<hex>",
         "ranking_policy_id": "<id>", "fusion_policy_id": "<id>",
         "candidates": [{"facet_id": "<id>", "score": <float>}, ...],
         "supporting_facet_ids": ["<id>", ...],
         "values": [{"value_id": "<id>", "associated_facet_ids": ["<id>", ...]}, ...]
     }}}}

Ids, hashes, policy ids and float scores only -- never a value's text.

MODEL-FREE. Zero model, tokenizer, encoder, embedder, scorer, llama-server
and network contacts; nothing under the sealed run directory is opened for
writing; nothing is written anywhere except under ``--output-root``.

TEXT DISCIPLINE. No utterance text, transcript, gold label string, intent
name, value id content or delivered answer is printed or persisted: sample
ids, store ids, counts, rates and hashes only. Gold and delivered intents
are compared in memory and discarded.

Byte-reproducible apart from ``generated_at_utc``.

    PYTHONDONTWRITEBYTECODE=1 python scripts/analysis/rankvis_probe_read.py \
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

from speech_aware_evidence_acquisition.rails import controllers as rc  # noqa: E402
from speech_aware_evidence_acquisition.rails.knowledge import (  # noqa: E402
    FusionDecision,
    RankedFacet,
    RankResult,
)
from speech_aware_evidence_acquisition.rails.runner import (  # noqa: E402
    order_supply_by_retrieval_rank,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (  # noqa: E402
    parse_slu_response,
)

DRIVER_ID = "slurp-rankvis-probe-read-v1"
PACKAGE = Path("docs/readiness/2026-09-27-slurp-stage3-rankvis-probe-fold-a-v1")
FACTS_RELPATH = PACKAGE / "registered-facts-v1.json"
ROSTER_RELPATH = PACKAGE / "roster-derivation-v1.json"
GENERATION_PLAN_RELPATH = PACKAGE / "generation-plan-registered-v1.json"
FACTS_SCHEMA = "saea-registered-facts-v1"
PROBE_RUN_ID = "SAEA-SLURP-STAGE3-RANKVIS-FOLD-A-119-V1"
COMPARATOR_RUN_ID = "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1"
COMPARATOR_ATTEMPT_ID = "attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1"
SCORER = "slurp-slu-official-train"
FIELD = "scenario_action_exact"
UNPARSED = "<unparsed>"
Z95 = 1.959963984540054

#: The two stores the registered treatment names, in the order the
#: preregistration lists them.
RANK_VISIBLE_STORES = ("intent-boundaries", "train-exemplars")
#: The store whose order never moves under this key (already rank-ordered by
#: the associated-values fuser); checked by seed equality, not recomputation.
SEED_ORDER_STORE = "intent-boundaries"
#: The store whose order DOES move (today lexicographic); checked by
#: recomputation through the real ``order_supply_by_retrieval_rank``.
REORDERED_STORE = "train-exemplars"
EXPECTED_RENDERING = {
    "schema": "saea-knowledge-value-rendering-v1",
    "order": "retrieval-rank",
    "rank_visible": True,
    "stores": list(RANK_VISIBLE_STORES),
}
RENDERING_SIDECAR_SCHEMA = "saea-rankvis-retrieval-rank-inputs-v1"

#: The 2.5 pp bar is a cross-cell owner constant (decision 133); everything
#: else this driver needs -- the per-row pp headroom, the row threshold, the
#: null save rate by gold-position band and the no-op expectations -- is
#: DERIVED from the registered facts document, never hardcoded here, so this
#: driver is exercised on a synthetic roster of any size (no coincidental
#: agreement with the real 119-row sums is required).
ARM_BAR_PP = 2.5


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


def id_list_sha256(ids) -> str:
    return digest_text("\n".join(sorted(str(i) for i in ids)))


def _store_of(value_id: str) -> str | None:
    store, sep, _local = value_id.partition("::")
    return store if sep else None


def _store_slice(value_ids, store_id: str) -> tuple[str, ...]:
    return tuple(v for v in value_ids if _store_of(v) == store_id)


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
    for _ in range(iterations):
        mid = 0.5 * (lo + hi)
        if func(mid) > target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def clopper_pearson_ci95(successes: int, trials: int) -> tuple[float, float]:
    alpha = 0.05
    if successes <= 0:
        lower = 0.0
    else:
        lower = _bisect(lambda p: _binom_cdf(successes - 1, trials, p), 1.0 - alpha / 2.0)
    if successes >= trials:
        upper = 1.0
    else:
        upper = _bisect(lambda p: _binom_cdf(successes, trials, p), alpha / 2.0)
    return lower, upper


def rate_block(m: int, n: int, *, no_op_expected: float) -> dict:
    wilson = wilson_ci95(m, n)
    exact = clopper_pearson_ci95(m, n)
    return {
        "estimand": f"m / {n}, rows moved wrong to gold, one binomial proportion over independent rows",
        "m": m,
        "n": n,
        "point": round(m / n, 6),
        "wilson_ci95": [round(wilson[0], 6), round(wilson[1], 6)],
        "clopper_pearson_ci95": [round(exact[0], 6), round(exact[1], 6)],
        "no_bootstrap_because": "the estimand is one binomial proportion, not a paired difference of pooled metrics",
        "no_op_expectation": no_op_expected,
        "m_minus_no_op": round(m - no_op_expected, 6),
        "read_against_no_op_never_zero": True,
    }


def redeclaration_block(
    m: int, *, no_op_expected_full: float, intent_pp_per_row: float, rows_needed_net_of_no_op: int,
) -> dict:
    net = m - no_op_expected_full
    return {
        "stated_not_applied": True,
        "rule": (
            "a later 1,080-row arm with an in-chain A/A declares expected_effect_pp = "
            "(m - no-op) x intent_pp_per_row pp intent accuracy (owner decision 139)"
        ),
        "m": m,
        "no_op_expectation": no_op_expected_full,
        "net_conversions_m_minus_no_op": round(net, 6),
        "intent_pp_per_row": intent_pp_per_row,
        "expected_effect_pp": round(net * intent_pp_per_row, 6),
        "bar_pp": ARM_BAR_PP,
        "rows_needed_net_of_no_op": rows_needed_net_of_no_op,
        "m_clears_the_bar": m >= rows_needed_net_of_no_op,
        "boundary": (
            "a CONDITIONAL rate on a gold-selected TRAIN roster: not a pooled effect, not a "
            "roster-level claim; this cell cannot see harm on rows AGREE answers correctly"
        ),
    }


# --------------------------------------------------------------------------- loaders


def load_facts(repo: Path) -> tuple[dict, str]:
    path = repo / FACTS_RELPATH
    facts = load_json(path)
    if facts.get("schema") != FACTS_SCHEMA:
        raise ReadRefused(0, f"the committed registered facts carry schema {facts.get('schema')!r}, not {FACTS_SCHEMA!r}")
    if str(facts.get("cell", {}).get("run_id")) != PROBE_RUN_ID:
        raise ReadRefused(0, "the committed registered facts do not name this cell's run id")
    return facts, digest_file(path)


def load_roster(repo: Path, facts: dict) -> dict:
    roster_meta = facts["roster"]
    derivation_meta = facts["roster_derivation"]
    path = repo / ROSTER_RELPATH
    sha = digest_file(path)
    if sha != derivation_meta["sha256"]:
        raise ReadRefused(0, "the committed roster derivation does not hash to the registered facts' pin")
    document = load_json(path)
    per_row = document["roster"]["per_row"]
    ids = [str(row["sample_id"]) for row in per_row]
    if len(ids) != int(roster_meta["rows"]) or len(set(ids)) != len(ids):
        raise ReadRefused(0, "the roster derivation does not carry the registered number of distinct ids")
    listed = id_list_sha256(ids)
    if listed != roster_meta["id_list_sha256"] or listed != document["roster"]["id_list_sha256"]:
        raise ReadRefused(0, "the roster id list does not hash to the registered id-list sha256")
    synthesis_meta = facts["synthesis_subset"]
    synthesis_ids = sorted(str(row["sample_id"]) for row in per_row if bool(row.get("in_synthesis_subset")))
    if len(synthesis_ids) != int(synthesis_meta["rows"]):
        raise ReadRefused(0, "the synthesis subset row count does not match the registered facts")
    synthesis_listed = id_list_sha256(synthesis_ids)
    if synthesis_listed != synthesis_meta["id_list_sha256"] or synthesis_listed != document["synthesis_subset"]["id_list_sha256"]:
        raise ReadRefused(0, "the synthesis subset id list does not hash to the registered id-list sha256")
    null_save_rate = {str(k): float(v) for k, v in facts["no_op_expectation"]["null_save_rate"].items()}
    band_by_id = {str(row["sample_id"]): str(row["agree_gold_position_band"]) for row in per_row}
    if set(band_by_id.values()) - set(null_save_rate):
        raise ReadRefused(0, "the roster derivation names a gold-position band the registered facts do not carry a null save rate for")
    primary_by_id = {str(row["sample_id"]): str(row["primary"]) for row in per_row}
    stage_by_id = {str(row["sample_id"]): str(row["stage"]) for row in per_row}
    # A cross-check the recipe reports beside every number: the registered
    # no-op expectation reproduces from the per-row bands, exactly.
    no_op_full = float(facts["no_op_expectation"]["expected_null_conversions"])
    no_op_subset = float(facts["no_op_expectation"]["expected_null_conversions_synthesis_subset"])
    recomputed_full = sum(null_save_rate[band_by_id[i]] for i in ids)
    recomputed_subset = sum(null_save_rate[band_by_id[i]] for i in synthesis_ids)
    if abs(recomputed_full - no_op_full) > 1e-6:
        raise ReadRefused(0, "the roster's per-row gold-position bands do not reproduce the registered no-op expectation")
    if abs(recomputed_subset - no_op_subset) > 1e-6:
        raise ReadRefused(0, "the synthesis subset's per-row gold-position bands do not reproduce its registered no-op expectation")
    re_decl = facts["re_declaration_rule"]
    return {
        "relpath": str(ROSTER_RELPATH).replace("\\", "/"),
        "sha256": sha,
        "ids": sorted(ids),
        "id_list_sha256": listed,
        "split_identity_hash": document["roster"]["split_identity_hash"],
        "synthesis_subset_ids": synthesis_ids,
        "band_by_id": band_by_id,
        "primary_by_id": primary_by_id,
        "stage_by_id": stage_by_id,
        "no_op_expected_full": no_op_full,
        "no_op_expected_subset": no_op_subset,
        "intent_pp_per_row": float(re_decl["pp_per_row"]),
        "rows_needed_net_of_no_op": int(re_decl["m_needed_for_the_2p5_pp_bar"]),
    }


def load_generation_plan(repo: Path) -> dict:
    path = repo / GENERATION_PLAN_RELPATH
    if not path.is_file():
        raise ReadRefused(
            0,
            "no generation-plan-registered-v1.json: this cell has not been flipped "
            "(scripts/flights/repin_cell.py --set-ready) yet, so there is no flown attempt to read",
        )
    plan = load_json(path)
    for key in ("composed_config_hash", "attempt_id"):
        if not plan.get(key):
            raise ReadRefused(0, f"the generation plan carries no {key!r}")
    return plan


def load_baseline_rendering(repo: Path, facts: dict) -> dict:
    relpath = Path(str(facts["cell"]["baseline"]))
    path = repo / relpath
    sha = digest_file(path)
    if sha != facts["cell"]["baseline_sha256"]:
        raise ReadRefused(1, "the committed baseline fragment does not hash to the registered facts' pin")
    baseline = load_json(path)
    rendering = (baseline.get("native_episode") or {}).get("knowledge_value_rendering")
    if rendering != EXPECTED_RENDERING:
        raise ReadRefused(
            1,
            "the registered baseline fragment does not declare the expected knowledge_value_rendering "
            "block: the flown requests would not carry the rank labels",
        )
    return {"relpath": str(relpath).replace("\\", "/"), "sha256": sha, "rendering": rendering}


def load_probe(data_root: Path, facts: dict, roster: dict, plan: dict) -> dict:
    run_id = str(facts["cell"]["run_id"])
    attempt_id = str(plan["attempt_id"])
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
    flown_config = (manifest.get("config") or {}).get("config_hash")
    if flown_config != plan["composed_config_hash"]:
        raise ReadRefused(1, "the sealed manifest's config hash is not the registered generation plan's")

    attempt_path = data_root / "attempts" / run_id / f"{attempt_id}.json"
    attempt = load_json(attempt_path)
    if attempt.get("state") != "FINALIZED":
        raise ReadRefused(1, f"the attempt record is {attempt.get('state')!r}, not FINALIZED")

    outputs_path = run_dir / f"{run_id}.outputs.jsonl"
    scores_path = run_dir / f"{run_id}.scores.json"
    phases_path = run_dir / f"{run_id}.phases.json"
    hashes = {
        "run_manifest": digest_file(manifest_path),
        "outputs": digest_file(outputs_path),
        "scores": digest_file(scores_path),
        "phases": digest_file(phases_path),
        "attempt_record": digest_file(attempt_path),
    }
    if hashes["outputs"] != manifest["outputs"]["sha256"]:
        raise ReadRefused(1, "the outputs file does not hash to the manifest's pin")
    if hashes["scores"] != manifest["scores"]["sha256"]:
        raise ReadRefused(1, "the scores file does not hash to the manifest's pin")

    jobs_path = run_dir / "score-jobs.jsonl"
    summary_path = run_dir / "score-batch" / "batch-summary.json"
    jobs = [json.loads(line) for line in jobs_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    summary = load_json(summary_path)
    if len(jobs) != 1 or int(summary.get("job_count", 0)) != 1 or int(summary.get("succeeded", 0)) != 1:
        raise ReadRefused(3, "the sealed attempt does not carry exactly one succeeded official scoring job")
    job = summary["jobs"][0]
    score_result_path = run_dir / "score-batch" / str(job["result_file"])
    if digest_file(score_result_path) != job["result_sha256"]:
        raise ReadRefused(3, "the official scoring result does not hash to the batch summary's pin")
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

    phases_doc = load_json(phases_path)
    if phases_doc.get("schema") != "saea-flight-phase-summaries-v1":
        raise ReadRefused(2, "unexpected phase artefact schema")
    results = {str(r["sample_id"]): r for r in phases_doc["phases"][0]["results"]}
    if sorted(results) != roster["ids"]:
        raise ReadRefused(2, "the phase artefact's result rows are not the committed roster")

    return {
        "run_id": run_id,
        "attempt_id": attempt_id,
        "run_dir": run_dir,
        "manifest": manifest,
        "attempt": attempt,
        "scores_block": block,
        "per_sample": per_sample,
        "outputs": outputs,
        "phase_results": results,
        "hashes": hashes,
        "score_job": {
            "job_id": job["job_id"], "status": job["status"],
            "result_file": job["result_file"], "result_sha256": job["result_sha256"],
        },
    }


def load_comparator(data_root: Path, roster: dict) -> dict:
    run_id, attempt_id = COMPARATOR_RUN_ID, COMPARATOR_ATTEMPT_ID
    run_dir = data_root / "runs" / run_id / attempt_id
    manifest_path = run_dir / f"{run_id}.run-manifest.json"
    manifest = load_json(manifest_path)
    if manifest.get("status") != "COMPLETED":
        raise ReadRefused(4, "the sealed comparator manifest is not COMPLETED")
    scores_path = run_dir / f"{run_id}.scores.json"
    outputs_path = run_dir / f"{run_id}.outputs.jsonl"
    phases_path = run_dir / f"{run_id}.phases.json"
    hashes = {
        "run_manifest": digest_file(manifest_path),
        "scores": digest_file(scores_path),
        "outputs": digest_file(outputs_path),
        "phases": digest_file(phases_path),
    }
    if hashes["scores"] != manifest["scores"]["sha256"] or hashes["outputs"] != manifest["outputs"]["sha256"]:
        raise ReadRefused(4, "the comparator's sealed files do not hash to its manifest's pins")
    block = load_json(scores_path)[SCORER]
    wanted = set(roster["ids"])
    per_sample = {str(r["sample_id"]): r for r in block["per_sample"] if str(r["sample_id"]) in wanted}
    if sorted(per_sample) != sorted(wanted):
        raise ReadRefused(4, "the comparator's official per-sample rows do not cover the probe roster")
    wrong = [sid for sid, row in per_sample.items() if float(row[FIELD]) >= 0.5]
    if wrong:
        raise ReadRefused(
            4, f"{len(wrong)} comparator row(s) are intent-CORRECT, not intent-wrong as registered"
        )
    outputs: dict[str, dict] = {}
    with outputs_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            sample_id = str(record.get("sample_id"))
            if sample_id in wanted:
                outputs[sample_id] = {"text": record.get("text") or ""}
    if sorted(outputs) != sorted(wanted):
        raise ReadRefused(4, "the comparator's outputs do not cover the probe roster")
    phases_doc = load_json(phases_path)
    results = {str(r["sample_id"]): r for r in phases_doc["phases"][0]["results"]}
    if not wanted <= set(results):
        raise ReadRefused(4, "the comparator's phase artefact does not cover the probe roster")
    initial_boundary_ids: dict[str, tuple[str, ...]] = {}
    exemplar_ids: dict[str, tuple[str, ...]] = {}
    for sample_id in roster["ids"]:
        result = results[sample_id]
        initial_ids = tuple(result["initial_query_state"]["retrieved_value_ids"])
        final_ids = tuple(result["final_query_state"]["retrieved_value_ids"])
        initial_boundary_ids[sample_id] = _store_slice(initial_ids, SEED_ORDER_STORE)
        exemplar_ids[sample_id] = _store_slice(final_ids, REORDERED_STORE)
    return {
        "run_id": run_id, "attempt_id": attempt_id, "hashes": hashes,
        "per_sample": per_sample, "outputs": outputs,
        "initial_boundary_value_ids": initial_boundary_ids,
        "exemplar_value_ids": exemplar_ids,
    }


def load_retrieval_rank_inputs(run_dir: Path, run_id: str) -> dict | None:
    """The optional sidecar the rendering gate's train-exemplars leg needs
    (module docstring). None when absent -- which is every sealed run today,
    since RANKVIS has not flown and no flight yet seals it."""

    path = run_dir / f"{run_id}.retrieval-rank-inputs.json"
    if not path.is_file():
        return None
    document = load_json(path)
    if document.get("schema") != RENDERING_SIDECAR_SCHEMA:
        raise ReadRefused(2, f"the retrieval-rank-inputs sidecar carries an unexpected schema {document.get('schema')!r}")
    return document.get("rows") or {}


def _recomputed_exemplar_order(row_inputs: dict, selected_ids: tuple[str, ...]) -> tuple[str, ...]:
    """The real rails.runner.order_supply_by_retrieval_rank over one row's
    sealed retrieval-rank inputs -- reused, never re-implemented."""

    from types import SimpleNamespace

    snapshot_sha256 = str(row_inputs["snapshot_sha256"])
    query_state_sha256 = str(row_inputs["query_state_sha256"])
    rank_result = RankResult(
        snapshot_sha256=snapshot_sha256,
        query_state_sha256=query_state_sha256,
        ranking_policy_id=str(row_inputs["ranking_policy_id"]),
        candidates=tuple(
            RankedFacet(facet_id=str(c["facet_id"]), score=float(c["score"]))
            for c in row_inputs["candidates"]
        ),
    ).validate()
    fusion_decision = FusionDecision(
        snapshot_sha256=snapshot_sha256,
        query_state_sha256=query_state_sha256,
        rank_result_sha256=rank_result.content_hash(),
        fusion_policy_id=str(row_inputs["fusion_policy_id"]),
        supporting_facet_ids=tuple(str(f) for f in row_inputs["supporting_facet_ids"]),
        selected_value_ids=tuple(selected_ids),
    ).validate()
    supply = rc.PhaseSupply(
        rank_result=rank_result, fusion_decision=fusion_decision,
        action_target_ref="rankvis-probe-read-retrieval-rank-inputs-v1",
    ).validate()
    snapshot = SimpleNamespace(
        values=tuple(
            SimpleNamespace(
                value_id=str(v["value_id"]),
                associated_facet_ids=tuple(str(f) for f in v["associated_facet_ids"]),
            )
            for v in row_inputs["values"]
        )
    )
    reordered = order_supply_by_retrieval_rank(supply, snapshot, (REORDERED_STORE,))
    return tuple(reordered.fusion_decision.selected_value_ids)


# --------------------------------------------------------------------------- the rendering gate


def rendering_gate(roster: dict, probe: dict, comparator: dict, rank_inputs: dict | None) -> dict:
    """Step 2 of the recipe. Returns a report; never raises by itself -- the
    caller (run) turns an incomplete report into a refusal, so the report
    itself carries the count of rows verified either way."""

    seed_verified: list[str] = []
    seed_mismatched: list[str] = []
    exemplar_verified: list[str] = []
    exemplar_mismatched: list[str] = []
    exemplar_set_mismatched: list[str] = []
    exemplar_unverifiable: list[str] = []

    for sample_id in roster["ids"]:
        result = probe["phase_results"][sample_id]
        probe_initial = tuple(result["initial_query_state"]["retrieved_value_ids"])
        probe_final = tuple(result["final_query_state"]["retrieved_value_ids"])
        probe_seed = _store_slice(probe_initial, SEED_ORDER_STORE)
        if probe_seed == comparator["initial_boundary_value_ids"][sample_id]:
            seed_verified.append(sample_id)
        else:
            seed_mismatched.append(sample_id)

        probe_exemplars = _store_slice(probe_final, REORDERED_STORE)
        comparator_exemplars = comparator["exemplar_value_ids"][sample_id]
        if set(probe_exemplars) != set(comparator_exemplars):
            exemplar_set_mismatched.append(sample_id)
            continue
        row_inputs = (rank_inputs or {}).get(sample_id, {}).get(REORDERED_STORE)
        if row_inputs is None:
            exemplar_unverifiable.append(sample_id)
            continue
        expected = _recomputed_exemplar_order(row_inputs, probe_exemplars)
        if expected == probe_exemplars:
            exemplar_verified.append(sample_id)
        else:
            exemplar_mismatched.append(sample_id)

    n = len(roster["ids"])
    all_verified = (
        len(seed_verified) == n
        and len(exemplar_verified) == n
        and not seed_mismatched
        and not exemplar_mismatched
        and not exemplar_set_mismatched
        and not exemplar_unverifiable
    )
    return {
        "expected_rendering": EXPECTED_RENDERING,
        "labels_guaranteed_by_baseline_config": True,
        "rows_total": n,
        "stores": {
            SEED_ORDER_STORE: {
                "method": "equals the comparator's own sealed first-phase seed order (already rank-ordered)",
                "rows_verified": len(seed_verified),
                "rows_mismatched": len(seed_mismatched),
            },
            REORDERED_STORE: {
                "method": "rails.runner.order_supply_by_retrieval_rank over the sealed retrieval-rank-inputs sidecar",
                "sidecar_present": rank_inputs is not None,
                "rows_verified": len(exemplar_verified),
                "rows_set_mismatched": len(exemplar_set_mismatched),
                "rows_order_mismatched": len(exemplar_mismatched),
                "rows_unverifiable_no_sidecar_row": len(exemplar_unverifiable),
            },
        },
        "all_rows_verified": all_verified,
    }


# --------------------------------------------------------------------------- the conversion contrast


def parsed_intent(text: str) -> str:
    scenario, action, _entities, parsed = parse_slu_response(text or "")
    if parsed and isinstance(scenario, str) and isinstance(action, str):
        return f"{scenario}_{action}"
    return UNPARSED


def contrast(ids: list[str], probe: dict, comparator: dict) -> dict:
    per_row: list[dict] = []
    classes: Counter = Counter()
    for sample_id in ids:
        probe_exact = float(probe["per_sample"][sample_id][FIELD]) >= 0.5
        probe_text = str(probe["outputs"][sample_id].get("text") or "")
        comparator_text = str(comparator["outputs"][sample_id]["text"])
        probe_intent = parsed_intent(probe_text)
        comparator_intent = parsed_intent(comparator_text)
        if probe_exact:
            transition = "wrong-to-gold"
        elif probe_intent == comparator_intent:
            transition = "unchanged-wrong"
        else:
            transition = "different-wrong"
        classes[transition] += 1
        per_row.append({
            "sample_id": sample_id, "probe_intent_exact": probe_exact, "transition": transition,
        })
    m = classes["wrong-to-gold"]
    n = len(ids)
    return {
        "rows": n,
        "m_wrong_to_gold": m,
        "r_gold_to_wrong": 0,
        "r_is_zero_by_construction": "the comparator holds no correct row on this roster to lose",
        "four_way_split": {
            "wrong_to_gold": m, "gold_to_wrong": 0,
            "same_wrong_intent": classes["unchanged-wrong"],
            "different_wrong_intent": classes["different-wrong"],
        },
        "per_row": per_row,
    }


def by_stage_block(ids: list[str], contrast_rows: dict, roster: dict) -> dict:
    by_row = {row["sample_id"]: row for row in contrast_rows["per_row"]}
    stages: dict[str, Counter] = {}
    for sample_id in ids:
        stage = roster["stage_by_id"][sample_id]
        stages.setdefault(stage, Counter())["rows"] += 1
        if by_row[sample_id]["probe_intent_exact"]:
            stages[stage]["m"] += 1
    return {
        stage: {"rows": counts["rows"], "m": counts["m"]}
        for stage, counts in sorted(stages.items())
    }


# --------------------------------------------------------------------------- rendering


def fmt_ci(bounds: list[float]) -> str:
    return f"[{100 * bounds[0]:.2f} %, {100 * bounds[1]:.2f} %]"


def render_markdown(result: dict) -> str:
    c = result["contrast"]
    rate = result["rate"]
    subset_rate = result["subset_rate"]
    g = result["rendering_gate"]
    r = result["redeclaration"]
    store_names = list(g["stores"])
    lines = [
        f"# Cell RANKVIS read: m = {c['m_wrong_to_gold']} of {c['rows']}",
        "",
        f"Generated {result['generated_at_utc']}; driver `{result['driver']['relpath']}` "
        f"sha256 `{result['driver']['sha256']}`.",
        "",
        "## Rendering gate",
        "",
        "| store | method | rows verified / total |",
        "| --- | --- | ---: |",
        f"| {store_names[0]} | {g['stores'][store_names[0]]['method']} | "
        f"{g['stores'][store_names[0]]['rows_verified']} / {g['rows_total']} |",
        f"| {store_names[1]} | {g['stores'][store_names[1]]['method']} | "
        f"{g['stores'][store_names[1]]['rows_verified']} / {g['rows_total']} |",
        "",
        f"All rows verified: **{g['all_rows_verified']}**.",
        "",
        "## The number",
        "",
        "| quantity | value |",
        "| --- | ---: |",
        f"| m, rows moved wrong to gold (of {rate['n']}) | **{rate['m']}** |",
        f"| Wilson CI95 | {fmt_ci(rate['wilson_ci95'])} |",
        f"| Clopper-Pearson CI95 (exact) | {fmt_ci(rate['clopper_pearson_ci95'])} |",
        f"| no-op expectation (never zero) | {rate['no_op_expectation']:.3f} |",
        f"| m - no-op | {rate['m_minus_no_op']:.3f} |",
        "",
        f"Synthesis subset (n = {subset_rate['n']}): m = {subset_rate['m']}, "
        f"Wilson {fmt_ci(subset_rate['wilson_ci95'])}, no-op expectation {subset_rate['no_op_expectation']:.3f}.",
        "",
        "## Four-way split",
        "",
        "| transition | rows |",
        "| --- | ---: |",
        f"| wrong to gold (m) | {c['four_way_split']['wrong_to_gold']} |",
        f"| gold to wrong (zero by construction) | {c['four_way_split']['gold_to_wrong']} |",
        f"| the same wrong intent | {c['four_way_split']['same_wrong_intent']} |",
        f"| a different wrong intent | {c['four_way_split']['different_wrong_intent']} |",
        "",
        "## By stage",
        "",
        "| stage | rows | m |",
        "| --- | ---: | ---: |",
    ]
    for stage, counts in result["by_stage"].items():
        lines.append(f"| {stage} | {counts['rows']} | {counts['m']} |")
    lines += [
        "",
        "## Re-declaration arithmetic, stated and not applied",
        "",
        f"expected_effect_pp = (m - no-op) x 0.092615 = **{r['expected_effect_pp']} pp**; "
        f"clears the {r['bar_pp']} pp bar at m >= {r['rows_needed_net_of_no_op']} net of the no-op: "
        f"**{r['m_clears_the_bar']}**.",
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
    driver = {
        # Relative to REPO_ROOT (this file's own checkout), not --repo-root:
        # a synthetic --repo-root used to unit-test this driver against a
        # fixture tree is not where rankvis_probe_read.py itself lives.
        "relpath": str(Path(__file__).resolve().relative_to(REPO_ROOT)).replace("\\", "/"),
        "sha256": digest_file(Path(__file__)),
    }
    facts, facts_sha = load_facts(repo)
    output_root = (
        Path(args.output_root) if args.output_root
        else data_root / "analysis" / f"{PROBE_RUN_ID}-READ-V1"
    )
    output_root.mkdir(parents=True, exist_ok=True)

    try:
        roster = load_roster(repo, facts)
        plan = load_generation_plan(repo)
        load_baseline_rendering(repo, facts)
        probe = load_probe(data_root, facts, roster, plan)
        comparator = load_comparator(data_root, roster)
        rank_inputs = load_retrieval_rank_inputs(probe["run_dir"], probe["run_id"])
        gate = rendering_gate(roster, probe, comparator, rank_inputs)
        if not gate["all_rows_verified"]:
            raise ReadRefused(
                2,
                "the rendering gate did not verify every row on both configured stores "
                f"({json.dumps(gate['stores'], sort_keys=True)}); no conversion number is produced",
            )
        contrast_block = contrast(roster["ids"], probe, comparator)
    except ReadRefused as refused:
        receipt = {
            "schema": "saea-rankvis-read-refusal-v1",
            "driver": driver,
            "generated_at_utc": generated,
            "facts_sha256": facts_sha,
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

    ids = roster["ids"]
    subset_ids = roster["synthesis_subset_ids"]
    m_full = contrast_block["m_wrong_to_gold"]
    subset_rows = [row for row in contrast_block["per_row"] if row["sample_id"] in set(subset_ids)]
    m_subset = sum(1 for row in subset_rows if row["probe_intent_exact"])

    result = {
        "schema": "saea-rankvis-read-v1",
        "driver": driver,
        "generated_at_utc": generated,
        "facts": {"relpath": str(FACTS_RELPATH).replace("\\", "/"), "sha256": facts_sha},
        "roster": {
            k: v for k, v in roster.items()
            if k not in ("ids", "synthesis_subset_ids", "band_by_id", "primary_by_id", "stage_by_id")
        },
        "probe": {
            "run_id": probe["run_id"], "attempt_id": probe["attempt_id"],
            "manifest_status": probe["manifest"]["status"], "attempt_state": probe["attempt"]["state"],
            "study_commit": probe["manifest"].get("study_commit"), "hashes": probe["hashes"],
        },
        "comparator": {
            "run_id": comparator["run_id"], "attempt_id": comparator["attempt_id"], "hashes": comparator["hashes"],
        },
        "rendering_gate": gate,
        "contrast": contrast_block,
        "rate": rate_block(m_full, len(ids), no_op_expected=roster["no_op_expected_full"]),
        "subset_rate": rate_block(m_subset, len(subset_ids), no_op_expected=roster["no_op_expected_subset"]),
        "by_stage": by_stage_block(ids, contrast_block, roster),
        "redeclaration": redeclaration_block(
            m_full,
            no_op_expected_full=roster["no_op_expected_full"],
            intent_pp_per_row=roster["intent_pp_per_row"],
            rows_needed_net_of_no_op=roster["rows_needed_net_of_no_op"],
        ),
        "boundary": (
            "A development read on a TRAIN construction fold: never a test claim, never a "
            "generalisation claim. SELECTED USING GOLD, OFFLINE: a conditional rate only, no "
            "pooled or roster-level claim. This cell cannot see harm on rows AGREE answers correctly."
        ),
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
    parser.add_argument("--output-root", default=None, help="defaults to analysis/<run-id>-READ-V1 under --data-root")
    return parser


def main(argv: list[str] | None = None) -> int:
    return run(build_arg_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
