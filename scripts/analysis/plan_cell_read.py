"""plan_cell_read.py -- the reusable default-plan LOCK cell read.

A PARAMETERISED driver (owner decision 58: reads are executed by script),
generalised from ``analysis/SAEA-SLURP-B1-INDEX-PAIRED-ANALYSIS-V1/
index_cell_read.py``. It takes an arm, a gating comparator, a LOCK comparator,
the cell's readiness package and the margins, and produces every table the
lock verdict quotes. Nothing is computed by hand.

What changed against the index driver: the index-consumption stage and the
derangement twin are gone; a ``lock`` stage and a ``frontier`` stage are new;
the structural stage reports the delivery-normaliser receipts, the E20
context-fit / compaction receipts and the knowledge-store pins instead of the
knowledge-index receipts.

Stages, in the order they must run:

  stop         verify the sealed bytes, the roster, the registered comparator
               AND lock-comparator aggregates, and reproduce the own-null
               margins
  structural   the tool surface, the trajectory, the dispositions, the
               delivery-normaliser receipts, the E20 compaction receipts, the
               knowledge-store pins and the Perception request key delta
  contrast     the paired official / projection-v3 / TRAIN-symmetric
               contrasts, the per-scenario tables and the intent band
  lock         the LOCK comparison: the sealed lock arm's official numbers and
               its node-applied numbers, re-derived model-free by replaying the
               registered delivery normaliser over a COPY of its sealed
               outputs, then paired against the arm on the same rows
  efficiency   the server.log join, the cost block and the request-fit block
  frontier     the decision-75 frontier row, computed here because
               ``scripts/analysis/slurp_module_frontier.py`` hard-codes its
               cell list
  verdict      assemble the decision, write the deliverables and the README

Model-free. Zero model, tokenizer, encoder, ASR and server contacts. The only
scorer invocations are model-free scorings run over COPIES of sealed outputs
written under the analysis root: the projection-v3 and TRAIN-symmetric
companions, and -- in the ``lock`` stage -- the official scorer over the
normaliser-replayed copy of the lock comparator. No sealed file and no
repository file is written, moved or modified. The resident llama-server is
never started, stopped or queried -- its ``server.log`` and ``monitor.jsonl``
are read read-only, as files, and only counters are taken from them.

Estimators, seeds, draw counts and interval levels are the sealed precedent
drivers' unchanged:
  analysis/SAEA-SLURP-B1-NOTOOL-PAIRED-ANALYSIS-V1/b1nt_paired_read.py
  analysis/SAEA-SLURP-B1-REPLICATE-OWN-NULL-PAIRED-ANALYSIS-V1/
    b1r_replicate_paired_read.py
  analysis/SAEA-SLURP-B1-INDEX-PAIRED-ANALYSIS-V1/index_cell_read.py

No utterance text, no gold label, no delivered filler and no model output is
ever printed or persisted: the driver reports counts, aggregate numbers,
scenario names, sample ids and content hashes only.
"""

from __future__ import annotations
import os

import argparse
import hashlib
import json
import math
import shutil
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
)
DATA = Path((os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"))
UMBRELLA_LOCK = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json")
sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.analysis import bootstrap as bs  # noqa: E402
from speech_aware_evidence_acquisition.analysis.null_calibration import pooled_f1  # noqa: E402
from speech_aware_evidence_acquisition.analysis.null_calibration_cli import rows_for  # noqa: E402
from speech_aware_evidence_acquisition.analysis.paired import (  # noqa: E402
    paired_contrast,
    resampled_statistic,
)

SCORER = "slurp-slu-official-train"
V3_SCORER = "slurp-slu-official-projected-v3-train"
SYM_SCORER = "slurp-slu-f1-normalized-v1-train"

PER_ROW_METRICS = (
    "scenario_action_exact",
    "scenario_exact",
    "action_exact",
    "slot_f1_exact_f1",
    "slu_f1_f1",
)
MICRO_METRICS = {
    "slu_f1_micro": (
        ("slu_f1_word_tp", "slu_f1_char_tp"),
        ("slu_f1_word_fp", "slu_f1_char_fp"),
        ("slu_f1_word_fn", "slu_f1_char_fn"),
    ),
    "span_f1_micro": (
        ("slot_f1_exact_tp",),
        ("slot_f1_exact_fp",),
        ("slot_f1_exact_fn",),
    ),
}
OFFICIAL_FIELD = {"slu_f1_micro": "slu_f1", "span_f1_micro": "span_f1"}
REGISTERED_PLANNER_ACTIONS = ("ACCEPT", "REVISE")
ILLEGAL_ACTION_LABEL = "ILLEGAL-ACTION"
SLOT_TOKENS = 24576

#: The registered facts this cell reads against. Overridable with
#: ``--registered``; the defaults are cell PLAN's own, taken from the packages
#: named in ``authority_relpaths`` below and never tuned.
DEFAULT_REGISTERED = {
    "comparator_official": {
        "slu_f1": 62.1295,
        "intent_accuracy": 80.0000,
        "scenario_accuracy": 86.4815,
        "action_accuracy": 81.1111,
        "span_f1": 49.0276,
        "source": "docs/results/2026-09-20-slurp-b1-notool-verdict.md",
    },
    "lock_official": {
        "slu_f1": 62.3351,
        "intent_accuracy": 80.0926,
        "source": "docs/results/2026-09-18-slurp-b5e-combination-verdict.md",
    },
    "lock_node_applied": {
        "slu_f1": 63.7757,
        "intent_accuracy": 81.8519,
        "source": (
            "docs/results/2026-09-19-slurp-b8a-deliver-normalise-verdict.md and "
            "docs/results/2026-09-20-slurp-v2-provisional-lock-v1.md (63.78 / 81.85)"
        ),
    },
    "own_null_right_official": {
        "slu_f1": 62.23,
        "intent_accuracy": 80.09,
        "source": "docs/results/2026-09-19-slurp-b1-replicate-verdict.md",
    },
    "own_null_left_official": {
        "slu_f1": 61.14,
        "intent_accuracy": 80.19,
        "source": "docs/results/2026-09-17-slurp-b1-exemplars-k20-verdict.md",
    },
    "own_null_table": {
        "source": "docs/results/2026-09-19-slurp-b1-replicate-verdict.md, clause 2",
        "pooled_micro": {
            "slu_f1_micro": {"left": 61.14, "right": 62.23, "delta": 1.09,
                             "ci95": [-0.10, 2.37], "ci95_half_width": 1.2350},
            "span_f1_micro": {"left": 48.43, "right": 49.92, "delta": 1.49,
                              "ci95": [-0.29, 3.30], "ci95_half_width": 1.7947},
        },
        "per_row": {
            "scenario_action_exact": {"left": 80.19, "right": 80.09, "delta": -0.09,
                                      "ci95": [-1.31, 1.13], "ci95_half_width": 1.2212,
                                      "saves": 28, "harms": 29, "ties": 1023},
        },
        "margin_tolerance": 0.0001,
        "table_tolerance": 0.005,
    },
    "comparator_cost_reference": {
        "label": "cell B1-notool (the sealed tool-free base)",
        "source": (
            "docs/results/2026-09-20-slurp-b1-notool-verdict.md and "
            "analysis/SAEA-SLURP-B1-NOTOOL-PAIRED-ANALYSIS-V1/efficiency.json"
        ),
        "sealed_efficiency_path": (
            "analysis/SAEA-SLURP-B1-NOTOOL-PAIRED-ANALYSIS-V1/efficiency.json"
        ),
        "contacts": 4432,
        "prefilled_tokens_per_row": 8019.85,
        "gpu_hours_per_1080": 1.6108,
        "contacts_per_minute": 42.91,
        "contacts_per_row": 4.1037,
        "projected_read_hours_13078": 19.506,
        "cache_hit_share": 0.7576,
        "wall_seconds": 6400.412614583969,
        "finite_completion_rows": 8,
        "react_exhaustion_rows": 0,
        "planner_action_illegal_rows": 0,
        "revisions_executed": 3,
    },
    "b4b_reference": {
        "source": "docs/results/2026-09-19-slurp-throughput-root-cause-v1.md",
        "rows": 500,
        "prefilled_tokens_per_row": 26197,
        "gpu_hours_per_1080": 3.837,
        "per_position": {
            "0_perception": {"prefilled_per_row": 1374, "cached_share": 0.618},
            "1_solver": {"prefilled_per_row": 6258, "cached_share": 0.361},
            "2_reviewer_1": {"prefilled_per_row": 7505, "cached_share": 0.236},
            "3_reviewer_2": {"prefilled_per_row": 1859, "cached_share": 0.835},
            "4_planner": {"prefilled_per_row": 9109, "cached_share": 0.198},
        },
    },
    "registered_ceilings": {
        "generation_calls_run_cumulative": 11880,
        "fit_endpoints": 47520,
        "repeated_speech_seconds": 33930,
        "gpu_hours_fit_inclusive": 12.0,
        "native_task_contract_calls": 0,
        "official_scoring_jobs": 1,
    },
    "knowledge_pins": {
        "source": "configs/baseline/slurp-native-default-plan-lock-baseline-v1.json",
        "arm": {
            "slot-contracts": {
                "relpath": "knowledge/slurp/semantic/slot-contracts-v2/release.json",
                "sha256": "f8e42d4ff1b220f45b26397340149566544cf5b13d7453fbc46a2b5c3400d11b",
            },
            "intent-boundaries": {
                "relpath": "knowledge/slurp/semantic/intent-boundaries-v1/release.json",
                "sha256": "2e51c14b4f1c3a122968bc0fd7809523470aad80923ff87c1ce9992ed8d3beb4",
            },
            "train-exemplars": {
                "relpath": (
                    "knowledge/slurp/saea-kb-distmodel-v1/"
                    "size-pool-annotated-exemplars/release.json"
                ),
                "sha256": "171aa4a82c2b15fff2c72e907ea80298be8d72309cca0d7367eb50debb042129",
            },
        },
        "comparator": {
            "slot-contracts": {
                "relpath": "knowledge/slurp/semantic/slot-contracts-v1/release.json",
                "sha256": "8a29c48bfc5aed2eb27ce38073252d3fc608c9102aa8b8095a072667289b4f3e",
            },
        },
    },
    "declared_episode_keys": {
        "deliver_normaliser": {"normaliser": "saea-deliver-normalise-v3"},
        "review_loop": "on",
        "context_fit_policy": "compact-or-abstain",
        "finite_completion_policy": "deliver-latest-or-abstain",
        "react_exhaustion_policy": "continue-without-answer",
    },
    #: Decision-75 frontier rows this read places its own row beside, copied
    #: from docs/results/2026-09-21-slurp-stage3-prelude-frontier-and-verifier-v1.md
    #: table A1. They are REGISTERED values, never recomputed here.
    "frontier_registered_rows": [
        {"cell": "B8a (B5e base)", "status": "ADMITTED", "official_slu": 63.78,
         "official_intent": 81.85, "gpu_hours_per_1080": 3.8709, "contacts_per_row": 5.014,
         "prefilled_tokens_per_row": 46796.0, "token_basis": "PROXY"},
        {"cell": "B8a (B1 base)", "status": "ADMITTED", "official_slu": 62.67,
         "official_intent": 81.76, "gpu_hours_per_1080": 3.6819, "contacts_per_row": 5.023,
         "prefilled_tokens_per_row": 45730.5, "token_basis": "PROXY"},
        {"cell": "B5e", "status": "NEUTRAL vs B1", "official_slu": 62.34,
         "official_intent": 80.09, "gpu_hours_per_1080": 3.8709, "contacts_per_row": 5.014,
         "prefilled_tokens_per_row": 46796.0, "token_basis": "PROXY"},
        {"cell": "B1r", "status": "REPLICATED", "official_slu": 62.23,
         "official_intent": 80.09, "gpu_hours_per_1080": 3.8507, "contacts_per_row": 5.040,
         "prefilled_tokens_per_row": 26071.9, "token_basis": "measured"},
        {"cell": "B1-notool", "status": "NON-INFERIORITY NOT PROVEN", "official_slu": 62.13,
         "official_intent": 80.00, "gpu_hours_per_1080": 1.6108, "contacts_per_row": 4.104,
         "prefilled_tokens_per_row": 8019.8, "token_basis": "measured"},
        {"cell": "B1", "status": "ADMITTED", "official_slu": 61.14,
         "official_intent": 80.19, "gpu_hours_per_1080": 3.6819, "contacts_per_row": 5.023,
         "prefilled_tokens_per_row": 25933.0, "token_basis": "measured"},
        {"cell": "IDX", "status": "HARMFUL", "official_slu": 54.76,
         "official_intent": 77.59, "gpu_hours_per_1080": 1.3340, "contacts_per_row": 4.181,
         "prefilled_tokens_per_row": 3379.1, "token_basis": "measured"},
        {"cell": "B4b", "status": "ADMITTED", "official_slu": 51.09,
         "official_intent": 78.52, "gpu_hours_per_1080": 3.4651, "contacts_per_row": 5.006,
         "prefilled_tokens_per_row": 26197.0, "token_basis": "measured"},
        {"cell": "B0", "status": "HARMFUL", "official_slu": 48.67,
         "official_intent": 77.59, "gpu_hours_per_1080": 1.0540, "contacts_per_row": 2.000,
         "prefilled_tokens_per_row": 12328.7, "token_basis": "PROXY"},
    ],
    "frontier_source": (
        "docs/results/2026-09-21-slurp-stage3-prelude-frontier-and-verifier-v1.md, "
        "PART A table A1"
    ),
    "authority_relpaths": [
        "docs/readiness/2026-09-21-slurp-default-plan-lock-v1-preregistration.md",
        "docs/readiness/2026-09-21-slurp-default-plan-lock-v1/analysis-recipe-v1.json",
        "docs/readiness/2026-09-21-slurp-default-plan-lock-v1/protocol-registered-v1.json",
        "docs/readiness/2026-09-21-slurp-default-plan-lock-v1/README.md",
        "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md",
        "docs/results/2026-09-20-slurp-b1-notool-verdict.md",
        "docs/results/2026-09-19-slurp-b1-replicate-verdict.md",
        "docs/results/2026-09-18-slurp-b5e-combination-verdict.md",
        "docs/results/2026-09-19-slurp-b8a-deliver-normalise-verdict.md",
        "docs/results/2026-09-20-slurp-v2-provisional-lock-v1.md",
        "docs/results/2026-09-21-slurp-stage3-prelude-frontier-and-verifier-v1.md",
        "configs/baseline/slurp-native-default-plan-lock-baseline-v1.json",
        "configs/experiment/slurp-native-default-plan-lock-v1.json",
        "configs/baseline/slurp-native-anchor-exemplars-k20-notool-v1.json",
    ],
}

#: Request-payload fields that carry FLIGHT BOOKKEEPING rather than
#: model-facing content (the precedent driver's list, unchanged).
BOOKKEEPING_REQUEST_KEYS = ("request_id", "evidence_provenance")
BOOKKEEPING_DECODING_KEYS = ("id_slot",)
BOOKKEEPING_HISTORY_KEYS = (
    "state_id", "source_query_state_sha256", "source_response_sha256",
)

#: The Perception-request keys this cell's factor is ALLOWED to move: the
#: contract fill carries the v2 slot-contract cards, so the task instruction,
#: the supplied evidence, the history and the provenance content may differ.
ARMED_REQUEST_KEYS = frozenset(
    {"task_instruction", "supplied_evidence", "history", "evidence_provenance_content"}
)


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

class Cell:
    """Everything the stages need, resolved once from the command line."""

    def __init__(self, args) -> None:
        self.args = args
        self.out = Path(args.analysis_root)
        self.cache = Path(args.cache_dir or (self.out / "cache"))
        self.copies = self.out / "outputs-copies"
        self.v3_dir = self.out / "v3"
        self.sym_dir = self.out / "symmetric"
        self.lock_dir = self.out / "lock-node"
        self.rows = args.rows
        self.seed = args.seed
        self.draws = args.draws
        self.h_slu = args.h_slu
        self.h_intent = args.h_intent
        self.package = Path(args.package_dir)
        self.session_dir = Path(args.serving_session_dir)
        self.test_read_rows = args.test_read_rows
        self.normaliser_id = args.normaliser_id
        self.registered = (
            json.loads(Path(args.registered).read_text(encoding="utf-8"))
            if args.registered
            else DEFAULT_REGISTERED
        )
        self.runs: dict[str, dict] = {
            "arm": {
                "label": args.arm_label,
                "run_id": args.arm_run,
                "attempt_id": args.arm_attempt,
                "fit_run_id": args.arm_fit_run,
            },
            "comparator": {
                "label": args.comparator_label,
                "run_id": args.comparator_run,
                "attempt_id": args.comparator_attempt,
                "fit_run_id": args.comparator_fit_run,
            },
            "lock": {
                "label": args.lock_label,
                "run_id": args.lock_run,
                "attempt_id": args.lock_attempt,
                "fit_run_id": None,
            },
            "own_null_left": {
                "label": args.own_null_left_label,
                "run_id": args.own_null_left_run,
                "attempt_id": args.own_null_left_attempt,
            },
            "own_null_right": {
                "label": args.own_null_right_label,
                "run_id": args.own_null_right_run,
                "attempt_id": args.own_null_right_attempt,
            },
        }
        #: arms whose per-row OFFICIAL scores this read opens
        self.score_keys = ["arm", "comparator", "lock"]
        #: arms whose FLIGHT artefacts (phases, trace, receipts) this read opens
        self.flight_keys = ["arm", "comparator"]
        #: the gating contrast, and nothing else -- the own null is reproduced
        #: in ``stop`` and the lock comparison is built in ``lock``
        self.contrasts = [("arm_vs_comparator", "comparator", "arm")]
        self.band_contrasts = ["arm_vs_comparator"]

    # -- paths -----------------------------------------------------------
    def run_dir(self, key: str) -> Path:
        spec = self.runs[key]
        return DATA / "runs" / spec["run_id"] / spec["attempt_id"]

    def artifact(self, key: str, suffix: str) -> Path:
        return self.run_dir(key) / f"{self.runs[key]['run_id']}.{suffix}"

    def label(self, key: str) -> str:
        return f"{self.runs[key]['label']} ({self.runs[key]['run_id']})"


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _sha_of(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _percentile(values, fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    position = fraction * (len(ordered) - 1)
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    weight = position - low
    return float(ordered[low] * (1 - weight) + ordered[high] * weight)


def _stat_block(values) -> dict:
    if not values:
        return {"n": 0}
    return {
        "n": len(values),
        "median": statistics.median(values),
        "p90": _percentile(values, 0.90),
        "mean": sum(values) / len(values),
        "min": min(values),
        "max": max(values),
        "total": sum(values),
    }


# --------------------------------------------------------------------------
# Sealed-artefact loading
# --------------------------------------------------------------------------

def load_arm(cell: Cell, key: str) -> dict:
    """Open one sealed arm, verifying what the arm itself pins.

    The driver derives every digest from the bytes rather than carrying a
    table: the run manifest must be COMPLETED, must pin the very score file
    this read opens, must carry the registered split identity and must have
    been sealed from a clean study tree.
    """
    spec = cell.runs[key]
    scores_path = cell.artifact(key, "scores.json")
    manifest_path = cell.artifact(key, "run-manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    scores_sha = digest(scores_path)
    manifest_sha = digest(manifest_path)
    if manifest.get("status") != "COMPLETED":
        raise SystemExit(f"{key} manifest is not COMPLETED")
    pin = manifest.get("scores") or {}
    if pin.get("sha256") != scores_sha or Path(pin.get("path", "")) != scores_path:
        raise SystemExit(f"{key} manifest does not pin the score bytes this read used")
    split = manifest.get("split") or {}
    if split.get("identity_hash") != cell.args.split_identity_hash:
        raise SystemExit(f"{key} split identity differs from the registration")
    if split.get("role") != "discovery":
        raise SystemExit(f"{key} split role is not discovery")
    if manifest.get("study_repo_dirt"):
        raise SystemExit(f"{key} was sealed with a dirty study tree")
    scores = json.loads(scores_path.read_text(encoding="utf-8"))
    projection = scores[SCORER]["aggregate"].get("projection") or {}
    if projection.get("applied"):
        raise SystemExit(f"{key} decision score carries a label projection")
    return {
        "spec": spec,
        "scores_path": scores_path,
        "manifest_path": manifest_path,
        "manifest": manifest,
        "manifest_sha256": manifest_sha,
        "scores_sha256": scores_sha,
        "scores": scores,
        "document": {"verified": True, "manifest": str(manifest_path), "scores": scores},
        "split_ids": tuple(split.get("ids") or ()),
    }


def outputs_copy(cell: Cell, key: str) -> tuple[Path, str]:
    """A COPY of an arm's sealed outputs, verified against the sealed bytes."""
    source = cell.artifact(key, "outputs.jsonl")
    source_sha = digest(source)
    target_dir = cell.copies / cell.runs[key]["run_id"]
    target_dir.mkdir(parents=True, exist_ok=True)
    copy = target_dir / source.name
    if not copy.exists():
        shutil.copyfile(source, copy)
    if digest(copy) != source_sha:
        raise SystemExit(f"{key} outputs copy does not match the sealed bytes")
    return copy, source_sha


def roster_and_metadata(cell: Cell):
    roster_path = REPO / cell.args.roster
    roster = json.loads(roster_path.read_text(encoding="utf-8"))
    ids = sorted(item["id"] for item in roster["items"])
    if len(ids) != cell.rows or len(set(ids)) != cell.rows:
        raise SystemExit(f"roster is not {cell.rows} unique ids")
    metadata_path = DATA / cell.args.roster_metadata
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))["rows"]
    if set(metadata) != set(ids):
        raise SystemExit("roster metadata does not cover the roster exactly")
    return roster, ids, metadata, digest(roster_path), digest(metadata_path)


# --------------------------------------------------------------------------
# Intervals and contrasts (the precedent's estimator calls, unchanged)
# --------------------------------------------------------------------------

def percentiles(replicates, level: float) -> list[float]:
    tail = (1.0 - level) / 2.0
    ordered = sorted(replicates)
    return [100 * bs._percentile(ordered, tail), 100 * bs._percentile(ordered, 1.0 - tail)]


def interval_block(result, resampling: str) -> dict:
    ci95 = percentiles(result.replicates, 0.95)
    ci90 = percentiles(result.replicates, 0.90)
    return {
        "resampling": resampling,
        "point_estimate_pp": 100 * result.point_estimate,
        "sigma_hat_pp": 100 * result.sigma_hat,
        "ci95_pp": ci95,
        "ci95_half_width_pp": (ci95[1] - ci95[0]) / 2.0,
        "ci90_pp": ci90,
        "ci90_half_width_pp": (ci90[1] - ci90[0]) / 2.0,
        "n_replicates": result.n_replicates,
        "seed": result.seed,
    }


def contrast_block(cell, name, left_key, right_key, rows, ids, cluster_of, scenario_of,
                   scenarios, row_counts, *, stratified: bool = True,
                   labels: dict | None = None) -> dict:
    """The precedent's paired contrast, with the labels overridable so the lock
    stage can name a derived (node-applied) side that is not a sealed run."""
    labels = labels or {}
    left, right = rows[left_key], rows[right_key]

    def label_of(key):
        return labels.get(key) or cell.label(key)

    def short_of(key):
        return labels.get(key) or cell.runs[key]["label"]

    block: dict[str, object] = {
        "contrast": {
            "id": name,
            "left": label_of(left_key),
            "right": label_of(right_key),
            "sign": (
                f"delta = {short_of(right_key)} minus {short_of(left_key)}; "
                "negative means the right arm is worse"
            ),
        },
        "row_counts": {"left": row_counts[left_key], "right": row_counts[right_key]},
    }
    pooled: dict[str, dict] = {}
    for micro, groups in MICRO_METRICS.items():
        started = time.time()

        def statistic(resampled, groups=groups, left=left, right=right):
            return pooled_f1(right, resampled, groups) - pooled_f1(left, resampled, groups)

        clustered = resampled_statistic(
            sample_ids=ids, statistic=statistic, seed=cell.seed, n_replicates=cell.draws,
            ci_level=0.95, cluster_of=cluster_of,
        )
        entry = {
            "estimand": "pooled-count-f1",
            "direction": f"right({right_key})-minus-left({left_key})",
            "fields": {"tp": list(groups[0]), "fp": list(groups[1]), "fn": list(groups[2])},
            "left_pct": 100 * pooled_f1(left, ids, groups),
            "right_pct": 100 * pooled_f1(right, ids, groups),
            "delta_pp": 100 * statistic(ids),
            "speaker_clustered": interval_block(
                clustered, "paired whole-speaker cluster bootstrap"
            ),
        }
        if stratified:
            strat = resampled_statistic(
                sample_ids=ids, statistic=statistic, seed=cell.seed,
                n_replicates=cell.draws, ci_level=0.95, strata_of=scenario_of,
            )
            entry["scenario_stratified"] = interval_block(
                strat, "paired scenario-stratified row bootstrap"
            )
        per_scenario = {}
        for scenario in scenarios:
            members = [sid for sid in ids if scenario_of(sid) == scenario]
            lv = pooled_f1(left, members, groups)
            rv = pooled_f1(right, members, groups)
            per_scenario[scenario] = {
                "n": len(members), "left_pct": 100 * lv, "right_pct": 100 * rv,
                "delta_pp": 100 * (rv - lv),
            }
        entry["per_scenario"] = per_scenario
        entry["equal_scenario_delta_pp"] = sum(
            item["delta_pp"] for item in per_scenario.values()
        ) / len(per_scenario)
        pooled[micro] = entry
        print(f"  [{name}] pooled {micro} in {time.time() - started:.1f}s", flush=True)
    block["pooled_micro"] = pooled

    clustered_rows = paired_contrast(
        left, right, metrics=PER_ROW_METRICS, sample_ids=ids, cluster_of=cluster_of,
        seed=cell.seed, n_replicates=cell.draws, ci_level=0.95,
    )
    stratified_rows = None
    if stratified:
        stratified_rows = paired_contrast(
            left, right, metrics=PER_ROW_METRICS, sample_ids=ids, strata_of=scenario_of,
            seed=cell.seed, n_replicates=cell.draws, ci_level=0.95,
        )
    per_row: dict[str, dict] = {}
    for metric in PER_ROW_METRICS:
        contrast = clustered_rows[metric]
        entry = {
            "estimand": "mean-per-row",
            "direction": f"right({right_key})-minus-left({left_key})",
            "n": contrast.n,
            "left_pct": 100 * contrast.left_mean,
            "right_pct": 100 * contrast.right_mean,
            "delta_pp": 100 * contrast.delta,
            "saves": contrast.saves,
            "harms": contrast.harms,
            "ties": contrast.ties,
            "sign_test": "exact two-sided McNemar binomial on saves vs harms",
            "sign_test_p": contrast.sign_test_p,
            "speaker_clustered": interval_block(
                contrast.bootstrap, "paired whole-speaker cluster bootstrap"
            ),
        }
        if stratified_rows is not None:
            strat = stratified_rows[metric]
            entry["scenario_stratified"] = interval_block(
                strat.bootstrap, "paired scenario-stratified row bootstrap"
            )
            per_scenario = {
                key: {
                    "n": row.n, "left_pct": 100 * row.left_mean,
                    "right_pct": 100 * row.right_mean, "delta_pp": 100 * row.delta,
                    "saves": row.saves, "harms": row.harms, "ties": row.ties,
                }
                for key, row in strat.per_stratum.items()
            }
        else:
            per_scenario = {}
            for scenario in scenarios:
                members = [sid for sid in ids if scenario_of(sid) == scenario]
                lvals = [left[sid][metric] for sid in members]
                rvals = [right[sid][metric] for sid in members]
                saves = sum(1 for lv, rv in zip(lvals, rvals) if rv > lv)
                harms = sum(1 for lv, rv in zip(lvals, rvals) if rv < lv)
                per_scenario[scenario] = {
                    "n": len(members),
                    "left_pct": 100 * sum(lvals) / len(members),
                    "right_pct": 100 * sum(rvals) / len(members),
                    "delta_pp": 100 * (sum(rvals) - sum(lvals)) / len(members),
                    "saves": saves, "harms": harms, "ties": len(members) - saves - harms,
                }
        entry["per_scenario"] = per_scenario
        entry["equal_scenario_delta_pp"] = sum(
            item["delta_pp"] for item in per_scenario.values()
        ) / len(per_scenario)
        per_row[metric] = entry
    block["per_row"] = per_row
    return block


def _row_fields() -> tuple[str, ...]:
    return tuple(
        sorted(
            set(PER_ROW_METRICS)
            | {name for groups in MICRO_METRICS.values() for group in groups for name in group}
            | {"parsed"}
        )
    )


def _score_rows(cell: Cell, arms: dict, keys, scorer_id=SCORER):
    fields = _row_fields()
    return {key: rows_for(arms[key]["document"], scorer_id, fields) for key in keys}


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("cached ->", path, flush=True)


# --------------------------------------------------------------------------
# Stage: stop
# --------------------------------------------------------------------------

def stage_stop(cell: Cell) -> None:
    keys = list(cell.runs)
    arms = {key: load_arm(cell, key) for key in keys}
    roster, ids, metadata, roster_sha, metadata_sha = roster_and_metadata(cell)
    rows = _score_rows(cell, arms, keys)
    for key in keys:
        if set(rows[key]) != set(ids):
            raise SystemExit(f"{key} score rows do not equal the roster")
        if set(arms[key]["split_ids"]) != set(ids):
            raise SystemExit(f"{key} manifest split ids do not equal the roster")

    def cluster_of(sid: str) -> str:
        return metadata[sid]["speaker"]

    def scenario_of(sid: str) -> str:
        return metadata[sid]["scenario"]

    scenarios = sorted({scenario_of(sid) for sid in ids})
    speakers = sorted({cluster_of(sid) for sid in ids})

    consistency: dict[str, dict] = {}
    for key in keys:
        aggregate = arms[key]["scores"][SCORER]["aggregate"]["official"]
        for micro, groups in MICRO_METRICS.items():
            recomputed = pooled_f1(rows[key], ids, groups)
            official = float(aggregate[OFFICIAL_FIELD[micro]])
            consistency[f"{key}.{micro}"] = {
                "recomputed_pooled_f1": recomputed,
                "official_aggregate": official,
                "abs_diff": abs(recomputed - official),
                "matches_1e-6": abs(recomputed - official) < 1e-6,
            }
    if not all(entry["matches_1e-6"] for entry in consistency.values()):
        raise SystemExit("pooled_f1 does not reproduce an arm's official aggregate to 1e-6")

    registered = cell.registered
    stop: dict[str, object] = {}
    for key, block in (
        ("comparator", registered["comparator_official"]),
        ("lock", registered["lock_official"]),
        ("own_null_right", registered["own_null_right_official"]),
        ("own_null_left", registered["own_null_left_official"]),
    ):
        aggregate = arms[key]["scores"][SCORER]["aggregate"]["official"]
        for field, want in block.items():
            if field == "source":
                continue
            got = 100 * float(aggregate[field])
            stop[f"{key}.official.{field}"] = {
                "registered": want, "recomputed": got,
                "reproduced": abs(got - want) < 0.005 + 1e-9,
            }
    if not all(entry["reproduced"] for entry in stop.values()):
        raise SystemExit("STOP: a sealed comparator does not reproduce its registered aggregate")

    row_counts = {
        key: {
            "scored_rows": len(rows[key]),
            "parsed_rows": sum(1 for sid in ids if rows[key][sid]["parsed"] == 1.0),
            "malformed_retained_rows": sum(1 for sid in ids if rows[key][sid]["parsed"] != 1.0),
        }
        for key in keys
    }

    own_null = contrast_block(
        cell, "own_null", "own_null_left", "own_null_right", rows, ids, cluster_of,
        scenario_of, scenarios, row_counts,
    )
    table = registered["own_null_table"]
    checks: dict[str, dict] = {}

    def check(name, want, got, tol):
        checks[name] = {
            "registered": want, "recomputed": got, "abs_diff": abs(got - want),
            "reproduced": abs(got - want) < tol + 1e-9,
        }

    for micro, want in table["pooled_micro"].items():
        entry = own_null["pooled_micro"][micro]
        check(f"{micro}.left", want["left"], entry["left_pct"], table["table_tolerance"])
        check(f"{micro}.right", want["right"], entry["right_pct"], table["table_tolerance"])
        check(f"{micro}.delta", want["delta"], entry["delta_pp"], table["table_tolerance"])
        ci = entry["speaker_clustered"]["ci95_pp"]
        check(f"{micro}.ci95_lower", want["ci95"][0], ci[0], table["table_tolerance"])
        check(f"{micro}.ci95_upper", want["ci95"][1], ci[1], table["table_tolerance"])
        check(f"{micro}.ci95_half_width", want["ci95_half_width"],
              entry["speaker_clustered"]["ci95_half_width_pp"], table["margin_tolerance"])
    for metric, want in table["per_row"].items():
        entry = own_null["per_row"][metric]
        check(f"{metric}.left", want["left"], entry["left_pct"], table["table_tolerance"])
        check(f"{metric}.right", want["right"], entry["right_pct"], table["table_tolerance"])
        check(f"{metric}.delta", want["delta"], entry["delta_pp"], table["table_tolerance"])
        ci = entry["speaker_clustered"]["ci95_pp"]
        check(f"{metric}.ci95_lower", want["ci95"][0], ci[0], table["table_tolerance"])
        check(f"{metric}.ci95_upper", want["ci95"][1], ci[1], table["table_tolerance"])
        check(f"{metric}.ci95_half_width", want["ci95_half_width"],
              entry["speaker_clustered"]["ci95_half_width_pp"], table["margin_tolerance"])
        for field in ("saves", "harms", "ties"):
            check(f"{metric}.{field}", float(want[field]), float(entry[field]), 0.5)

    failed = sorted(name for name, entry in checks.items() if not entry["reproduced"])
    margins = {
        "h_slu": {
            "registered": cell.h_slu,
            "recomputed": own_null["pooled_micro"]["slu_f1_micro"]["speaker_clustered"][
                "ci95_half_width_pp"
            ],
        },
        "h_intent": {
            "registered": cell.h_intent,
            "recomputed": own_null["per_row"]["scenario_action_exact"]["speaker_clustered"][
                "ci95_half_width_pp"
            ],
        },
    }
    for entry in margins.values():
        entry["reproduced"] = abs(entry["recomputed"] - entry["registered"]) < 0.0001 + 1e-9
    if failed or not all(entry["reproduced"] for entry in margins.values()):
        raise SystemExit("STOP: the own null does not reproduce from the sealed bytes: "
                         + ", ".join(failed))
    print("  STOP passed: h_slu %.4f h_intent %.4f"
          % (margins["h_slu"]["recomputed"], margins["h_intent"]["recomputed"]), flush=True)

    payload = {
        "population": {
            "rows": len(ids),
            "roster_path": cell.args.roster,
            "roster_sha256": roster_sha,
            "roster_metadata_path": cell.args.roster_metadata,
            "roster_metadata_sha256": metadata_sha,
            "roster_id": roster.get("roster_id"),
            "scenarios": len(scenarios),
            "speakers": len(speakers),
            "headset_rows": sum(1 for sid in ids if metadata[sid]["headset"]),
            "far_field_rows": sum(1 for sid in ids if not metadata[sid]["headset"]),
            "split_identity_hash": cell.args.split_identity_hash,
            "split_role": "discovery",
        },
        "consistency_check": consistency,
        "registered_aggregate_reproduction": stop,
        "own_null_reproduction": {
            "definition": (
                "the exemplar-supplied configuration's own null, recomputed here from the "
                "sealed score bytes with this read's own estimator, seed and draws, and "
                "checked field by field against its published verdict table. Its two CI95 "
                "half-widths ARE the margins this cell reads against (owner decision 38)."
            ),
            "source": table["source"],
            "contrast": own_null,
            "field_checks": checks,
            "failures": failed,
            "margins": margins,
            "passed": True,
        },
        "row_counts": row_counts,
        "sources": {
            key: {
                "run_id": cell.runs[key]["run_id"],
                "attempt_id": cell.runs[key]["attempt_id"],
                "label": cell.runs[key]["label"],
                "arm": arms[key]["manifest"].get("arm"),
                "created_at": arms[key]["manifest"].get("created_at"),
                "study_commit": arms[key]["manifest"].get("study_commit"),
                "study_repo_dirt": arms[key]["manifest"].get("study_repo_dirt"),
                "config_hash": (arms[key]["manifest"].get("config") or {}).get("config_hash"),
                "config_fragments": (arms[key]["manifest"].get("config") or {}).get("fragments"),
                "protocol_hash": arms[key]["manifest"].get("protocol_hash"),
                "execution_profile": (arms[key]["manifest"].get("plan") or {}).get(
                    "execution_profile"
                ),
                "manifest_status": arms[key]["manifest"].get("status"),
                "manifest_path": str(arms[key]["manifest_path"]),
                "manifest_sha256": arms[key]["manifest_sha256"],
                "score_path": str(arms[key]["scores_path"]),
                "scores_sha256": arms[key]["scores_sha256"],
                "outputs_sha256": digest(cell.artifact(key, "outputs.jsonl")),
                "scorer": SCORER,
                "scorer_version": arms[key]["scores"][SCORER]["aggregate"].get("scorer_version"),
                "evaluator_commit": arms[key]["scores"][SCORER]["aggregate"].get(
                    "evaluator_commit"
                ),
                "identity_check": arms[key]["scores"][SCORER]["aggregate"].get("identity_check"),
                "official_scoring_jobs": len(
                    [
                        line
                        for line in (cell.run_dir(key) / "score-jobs.jsonl").read_text(
                            encoding="utf-8"
                        ).splitlines()
                        if line.strip()
                    ]
                ) if (cell.run_dir(key) / "score-jobs.jsonl").exists() else None,
                "official_aggregate": {
                    field: arms[key]["scores"][SCORER]["aggregate"]["official"][field]
                    for field in ("slu_f1", "span_f1", "intent_accuracy",
                                  "scenario_accuracy", "action_accuracy")
                },
                "cost": arms[key]["manifest"].get("cost"),
            }
            for key in keys
        },
        "package": {
            "dir": str(cell.package),
            "files": {
                path.name: digest(path)
                for path in sorted(cell.package.glob("*.json"))
            },
        },
    }
    _write(cell.cache / "stop-raw.json", payload)


# --------------------------------------------------------------------------
# Stage: structural
# --------------------------------------------------------------------------

def _phase_results(cell: Cell, key: str) -> dict:
    path = cell.artifact(key, "phases.json")
    document = json.loads(path.read_text(encoding="utf-8"))
    if (
        document.get("schema") != "saea-flight-phase-summaries-v1"
        or document.get("run_id") != cell.runs[key]["run_id"]
        or len(document.get("phases") or []) != 1
    ):
        raise SystemExit(f"{key} phase artefact does not bind this one system")
    summary = document["phases"][0]
    return {
        "path": path,
        "sha256": digest(path),
        "policy": document.get("policy"),
        "controller_policy_id": summary.get("controller_policy_id"),
        "agent_executor_id": summary.get("agent_executor_id"),
        "knowledge_snapshot_sha256": summary.get("knowledge_snapshot_sha256"),
        "protocol_hash": summary.get("protocol_hash"),
        "results": {row["sample_id"]: row for row in summary["results"]},
    }


def _reduce_request(inner: dict) -> dict:
    reduced = {k: v for k, v in inner.items() if k not in BOOKKEEPING_REQUEST_KEYS}
    provenance = inner.get("evidence_provenance")
    if isinstance(provenance, list):
        reduced["evidence_provenance_content"] = [
            {"lock_key": item.get("lock_key"), "sha256": item.get("sha256")}
            for item in provenance
        ]
    decoding = reduced.get("decoding_params")
    if isinstance(decoding, dict):
        reduced["decoding_params"] = {
            k: v for k, v in decoding.items() if k not in BOOKKEEPING_DECODING_KEYS
        }
    history = reduced.get("history")
    if isinstance(history, list):
        reduced["history"] = [
            {k: v for k, v in entry.items() if k not in BOOKKEEPING_HISTORY_KEYS}
            if isinstance(entry, dict) else entry
            for entry in history
        ]
    return reduced


def _scan_trace(cell: Cell, key: str) -> dict:
    """One streaming pass over an arm's sealed trace: counters and digests only."""
    path = cell.artifact(key, "trace.jsonl")
    requests: dict[str, dict] = {}
    costs: dict[str, dict] = {}
    tool_attempts: Counter = Counter()
    tool_schema_digests: Counter = Counter()
    order = 0
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if '"MODEL_REQUEST"' in line:
                record = json.loads(line)
                if record.get("channel") != "MODEL_REQUEST":
                    continue
                record_id = record["record_id"]
                if not record_id.endswith("/request"):
                    continue
                request_id = record_id[: -len("/request")]
                payload = record.get("payload") or {}
                inner = payload.get("payload") or {}
                reduced = _reduce_request(inner)
                schemas = inner.get("tool_schemas") or []
                decoding = inner.get("decoding_params") or {}
                order += 1
                tool_schema_digests[_sha_of(schemas)] += 1
                requests[request_id] = {
                    "order": order,
                    "sample_id": inner.get("sample_id"),
                    "payload_sha256": payload.get("payload_sha256"),
                    "model_facing_sha256": _sha_of(reduced),
                    "key_sha256": {k: _sha_of(v) for k, v in reduced.items()},
                    "tool_schemas_count": len(schemas),
                    "tool_choice": decoding.get("tool_choice"),
                    "id_slot": decoding.get("id_slot"),
                    "max_tokens": decoding.get("max_tokens"),
                }
            elif '"COST"' in line:
                record = json.loads(line)
                if record.get("channel") != "COST":
                    continue
                record_id = record["record_id"]
                if not record_id.endswith("/cost"):
                    continue
                payload = record["payload"]
                costs[record_id[: -len("/cost")]] = {
                    "prompt_tokens": payload.get("prompt_tokens"),
                    "completion_tokens": payload.get("completion_tokens"),
                    "audio_seconds": payload.get("audio_seconds"),
                    "latency_seconds": payload.get("latency_seconds"),
                }
            elif "/tool-attempt/" in line:
                record = json.loads(line)
                if record.get("channel") != "USE":
                    continue
                parts = record["record_id"].split("/")
                if "tool-attempt" not in parts:
                    continue
                tool_attempts[parts[parts.index("tool-attempt") - 1]] += 1
    return {
        "path": path,
        "requests": requests,
        "costs": costs,
        "tool_attempts_by_role": dict(sorted(tool_attempts.items())),
        "tool_attempt_count": sum(tool_attempts.values()),
        "distinct_tool_schemas_sha256": dict(tool_schema_digests),
    }


# B9a-rec: the Acquisition node's visit carries no execution_receipt (E36 zero-contact re-query); visits without one contribute no contacts.
def _contact_index(results: dict) -> dict:
    out: dict[str, list] = {}
    for sample_id, row in results.items():
        receipt = row["native_episode_receipt"]
        visits = list(receipt.get("role_visits") or [])
        interrupted = receipt.get("interrupted_role")
        if isinstance(interrupted, dict):
            visits.append(interrupted)
        entries = []
        for visit in visits:
            for contact in (visit.get("execution_receipt") or {}).get("contacts") or []:
                entries.append(
                    {
                        "sample_id": sample_id,
                        "role_id": visit["role_id"],
                        "stage": visit["stage"],
                        "request_id": contact["request_id"],
                    }
                )
        entries.sort(key=lambda item: int(item["request_id"].split("-")[-1]))
        for position, entry in enumerate(entries):
            entry["position"] = position
        out[sample_id] = entries
    return out


def _normaliser_block(results: dict) -> dict:
    """The saea-deliver-normaliser-v1 receipt (module M3), over every row."""
    rows_with_receipt = 0
    ids: Counter = Counter()
    versions: Counter = Counter()
    rules: Counter = Counter()
    schemas: Counter = Counter()
    carriers: Counter = Counter()
    branches: Counter = Counter()
    reasons: Counter = Counter()
    applied = changed = suppressed = 0
    rows_label_changed = rows_filler_changed = 0
    labels_total = fillers_total = 0
    text_identical = 0
    missing: list[str] = []
    for sample_id, row in sorted(results.items()):
        receipt = (row["native_episode_receipt"] or {}).get("deliver_normaliser")
        if not isinstance(receipt, dict):
            missing.append(sample_id)
            continue
        rows_with_receipt += 1
        ids[receipt.get("normaliser_id")] += 1
        versions[str(receipt.get("version"))] += 1
        rules[str(receipt.get("rule_id"))] += 1
        schemas[str(receipt.get("schema"))] += 1
        carriers[str(receipt.get("carrier_lock_key"))] += 1
        if receipt.get("applied"):
            applied += 1
            branches[str(receipt.get("label_branch"))] += 1
        else:
            reasons[str(receipt.get("reason"))] += 1
        changed += int(bool(receipt.get("changed")))
        suppressed += int(bool(receipt.get("rendering_suppressed")))
        rows_label_changed += int((receipt.get("labels_changed") or 0) > 0)
        rows_filler_changed += int((receipt.get("fillers_changed") or 0) > 0)
        labels_total += int(receipt.get("labels_changed") or 0)
        fillers_total += int(receipt.get("fillers_changed") or 0)
        if receipt.get("input_sha256") == receipt.get("output_sha256"):
            text_identical += 1
    return {
        "schema": "saea-deliver-normaliser-v1",
        "rows_with_the_receipt": rows_with_receipt,
        "rows_without_a_receipt": len(missing),
        "sample_ids_without_a_receipt": missing[:50],
        "one_receipt_per_row": not missing,
        "normaliser_id_counts": dict(ids),
        "version_counts": dict(versions),
        "rule_id_counts": dict(rules),
        "schema_counts": dict(schemas),
        "carrier_lock_key_counts": dict(carriers),
        "rows_applied": applied,
        "rows_not_applied": rows_with_receipt - applied,
        "unapplied_reason_counts": dict(sorted(reasons.items())),
        "label_branch_counts": dict(sorted(branches.items())),
        "rows_changed": changed,
        "rows_label_changed": rows_label_changed,
        "rows_filler_changed": rows_filler_changed,
        "labels_changed_total": labels_total,
        "fillers_changed_total": fillers_total,
        "rows_rendering_suppressed": suppressed,
        "rows_whose_delivered_text_is_byte_identical_to_the_solver_draft": text_identical,
    }


def _compaction_block(results: dict, receipts_dispositions: dict | None) -> dict:
    """Item E20: the saea-native-context-fit-v1 receipt, over every row.

    ``compact-or-abstain`` means the runtime drops droppable context items
    rather than truncating, and abstains rather than exceeding the slot. This
    block reports how many rows compacted, which droppable items were dropped,
    and the sample ids, so the verdict can say whether compacted rows differ
    in outcome.
    """
    policies: Counter = Counter()
    limits: Counter = Counter()
    slots: Counter = Counter()
    rows_with_receipt = 0
    contacts_seen = 0
    contacts_compacted = 0
    rows_compacted: list[str] = []
    dropped_items: Counter = Counter()
    dropped_by_role: Counter = Counter()
    compaction_keys: Counter = Counter()
    per_row: dict[str, dict] = {}
    receipt_compacted_field_total = 0
    missing: list[str] = []
    for sample_id, row in sorted(results.items()):
        fit = (row["native_episode_receipt"] or {}).get("context_fit")
        if not isinstance(fit, dict):
            missing.append(sample_id)
            continue
        rows_with_receipt += 1
        policies[str(fit.get("policy"))] += 1
        limits[str(fit.get("prompt_limit_tokens"))] += 1
        slots[str(fit.get("slot_tokens"))] += 1
        receipt_compacted_field_total += int(fit.get("compacted_contacts") or 0)
        contacts = fit.get("contacts") or []
        contacts_seen += len(contacts)
        row_compacted = 0
        for contact in contacts:
            compaction = contact.get("context_compaction")
            if not compaction:
                continue
            row_compacted += 1
            contacts_compacted += 1
            dropped_by_role[str(contact.get("role_id"))] += 1
            if isinstance(compaction, dict):
                for key in compaction:
                    compaction_keys[key] += 1
                for item in (compaction.get("dropped") or compaction.get("dropped_items") or []):
                    dropped_items[
                        json.dumps(item, sort_keys=True) if not isinstance(item, str) else item
                    ] += 1
        if row_compacted:
            rows_compacted.append(sample_id)
        per_row[sample_id] = {
            "contacts": len(contacts),
            "compacted_contacts": row_compacted,
            "receipt_compacted_contacts": int(fit.get("compacted_contacts") or 0),
        }
    return {
        "schema": "saea-native-context-fit-v1",
        "declared_policy": "compact-or-abstain (item E20)",
        "rows_with_the_receipt": rows_with_receipt,
        "rows_without_a_receipt": len(missing),
        "sample_ids_without_a_receipt": missing[:50],
        "one_receipt_per_row": not missing,
        "policy_counts": dict(policies),
        "prompt_limit_tokens_counts": dict(limits),
        "slot_tokens_counts": dict(slots),
        "contacts_seen_in_the_receipts": contacts_seen,
        "contacts_compacted": contacts_compacted,
        "contacts_compacted_from_the_receipt_field": receipt_compacted_field_total,
        "rows_compacted": len(rows_compacted),
        "sample_ids_compacted": rows_compacted,
        "dropped_items": dict(dropped_items),
        "dropped_contacts_by_role": dict(sorted(dropped_by_role.items())),
        "context_compaction_record_keys": dict(sorted(compaction_keys.items())),
        "flight_receipt_dispositions": receipts_dispositions,
        "agrees_with_the_flight_receipt": (
            receipts_dispositions is None
            or (
                int(receipts_dispositions.get("context_compaction_contacts") or 0)
                == contacts_compacted
                and int(receipts_dispositions.get("context_compaction_rows") or 0)
                == len(rows_compacted)
            )
        ),
        "per_row": per_row,
    }


def _knowledge_pins_block(cell: Cell, key: str, manifest: dict, phase: dict,
                          results: dict) -> dict:
    """The knowledge-store release pins this flight ran under, and the per-row
    evidence that each store actually supplied items.

    The per-row ``native_episode_receipt`` of this policy carries NO
    knowledge-store pin block, so the release pin is proven at the FLIGHT
    level (the sealed config fragment, whose release file is re-hashed on
    disk, plus the phase artefact's single ``knowledge_snapshot_sha256`` over
    all rows) and the per-row evidence is the supplied-item accounting below.
    """
    fragments = (manifest.get("config") or {}).get("fragments") or {}
    baseline_name = fragments.get("baseline")
    baseline_path = REPO / "configs" / "baseline" / f"{baseline_name}.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    stores = baseline.get("knowledge_stores") or {}
    releases: dict[str, dict] = {}
    for store, spec in sorted(stores.items()):
        release = spec.get("release") or {}
        relpath = release.get("relpath")
        pinned = release.get("sha256")
        on_disk = None
        if relpath:
            candidate = DATA / relpath
            if candidate.exists():
                on_disk = digest(candidate)
        releases[store] = {
            "relpath": relpath,
            "pinned_sha256": pinned,
            "release_file_sha256_on_disk": on_disk,
            "release_file_matches_the_pin": on_disk is not None and on_disk == pinned,
        }
    episode = baseline.get("native_episode") or {}
    declared = {
        name: episode.get(name)
        for name in (
            "deliver_normaliser", "review_loop", "context_fit_policy",
            "finite_completion_policy", "react_exhaustion_policy", "max_revisions",
            "episode_id",
        )
    }

    # Per-row supplied-item accounting, from the phase result's consumption
    # records. Item ids only -- never the evidence text.
    per_store_rows: Counter = Counter()
    per_store_items: dict[str, set] = defaultdict(set)
    rows_seen = 0
    for _sample_id, row in results.items():
        records = (row.get("consumption") or {}).get("records") or []
        rows_seen += 1
        seen_here: set[str] = set()
        for record in records:
            item = record.get("supplied_item_id")
            if not isinstance(item, str) or not item.startswith("knowledge:"):
                continue
            store = item.split(":", 2)[1].split("::")[0]
            per_store_items[store].add(item)
            seen_here.add(store)
        for store in seen_here:
            per_store_rows[store] += 1
    supplied = {
        store: {
            "rows_supplied_at_least_one_item": per_store_rows[store],
            "distinct_item_ids": len(per_store_items[store]),
            "item_id_set_sha256": _sha_of(sorted(per_store_items[store])),
        }
        for store in sorted(per_store_items)
    }
    return {
        "baseline_fragment": baseline_name,
        "baseline_fragment_path": str(baseline_path),
        "baseline_fragment_sha256": digest(baseline_path),
        "knowledge_store_releases": releases,
        "declared_native_episode_keys": declared,
        "phase_knowledge_snapshot_sha256": phase.get("knowledge_snapshot_sha256"),
        "rows_scanned": rows_seen,
        "supplied_items_per_store": supplied,
        "note": (
            "the per-row native_episode_receipt of this policy carries no knowledge_stores "
            "block; the release pin is a FLIGHT-level fact (the sealed config fragment plus "
            "the phase artefact's single knowledge_snapshot_sha256), and the per-row proof "
            "that the store was actually supplied is the supplied-item accounting above"
        ),
    }


def _disposition_block(results: dict) -> dict:
    finite: list[dict] = []
    illegal: list[dict] = []
    other: list[dict] = []
    actions: Counter = Counter()
    routes = 0
    revisions: Counter = Counter()
    reasons: Counter = Counter()
    for sample_id, row in sorted(results.items()):
        receipt = row["native_episode_receipt"]
        for route in receipt.get("planner_routes") or []:
            routes += 1
            action = route["action"]
            actions[action if action in REGISTERED_PLANNER_ACTIONS else ILLEGAL_ACTION_LABEL] += 1
            revisions[route["revision_count"]] += 1
        disposition = receipt.get("terminal_disposition")
        if isinstance(disposition, dict):
            reasons[disposition.get("reason")] += 1
            if disposition.get("reason") == "finite_completion":
                finite.append(
                    {
                        "sample_id": sample_id,
                        "finish_reason": disposition.get("finish_reason"),
                        "role_id": disposition.get("role_id"),
                        "stage": disposition.get("stage"),
                        "delivered_solver_draft": "terminal_solver_receipt" in receipt,
                        "delivered_abstention": "abstention_receipt" in receipt,
                    }
                )
            else:
                other.append(
                    {
                        "sample_id": sample_id,
                        "reason": disposition.get("reason"),
                        "planner_action": disposition.get("planner_action"),
                    }
                )
        mark = receipt.get("planner_action_illegal")
        if isinstance(mark, dict):
            illegal.append(
                {
                    "sample_id": sample_id,
                    "count": mark.get("count"),
                    "action_sha256": list(mark.get("action_sha256") or ()),
                    "action_chars": list(mark.get("action_chars") or ()),
                }
            )
    return {
        "finite_stops": {
            "count": len(finite),
            "sample_ids": [row["sample_id"] for row in finite],
            "rows": finite,
        },
        "planner_action_illegal": {
            "count": len(illegal),
            "sample_ids": [row["sample_id"] for row in illegal],
            "rows": illegal,
        },
        "other_terminal_dispositions": {"count": len(other), "rows": other},
        "terminal_disposition_reasons": {
            str(k): v for k, v in sorted(reasons.items(), key=lambda i: str(i[0]))
        },
        "react_exhaustion_rows": sum(
            v for k, v in reasons.items() if k and "exhaust" in str(k)
        ),
        "planner_routes": {
            "route_count": routes,
            "action_counts": dict(sorted(actions.items())),
            "revision_count_histogram": {str(k): v for k, v in sorted(revisions.items())},
            "rows_with_at_least_one_revise": sum(
                1
                for row in results.values()
                if any(
                    route["action"] == "REVISE"
                    for route in (row["native_episode_receipt"].get("planner_routes") or [])
                )
            ),
        },
    }


def _role_token_block(contacts_by_role: dict, costs: dict, requests: dict) -> dict:
    out: dict[str, dict] = {}
    for role in sorted(contacts_by_role):
        prompts, completions, latencies = [], [], []
        at_cap: Counter = Counter()
        rows_at_cap: set = set()
        caps: Counter = Counter()
        for entry in contacts_by_role[role]:
            cost = costs.get(entry["request_id"])
            request = requests.get(entry["request_id"]) or {}
            cap = request.get("max_tokens")
            if cap is not None:
                caps[cap] += 1
            if cost is None or cost.get("prompt_tokens") is None:
                continue
            prompts.append(int(cost["prompt_tokens"]))
            completion = int(cost["completion_tokens"] or 0)
            completions.append(completion)
            latencies.append(float(cost["latency_seconds"] or 0.0))
            if cap is not None and completion >= int(cap):
                at_cap[cap] += 1
                rows_at_cap.add(entry["sample_id"])
        out[role] = {
            "contacts": len(contacts_by_role[role]),
            "prompt_tokens": _stat_block(prompts),
            "completion_tokens": _stat_block(completions),
            "latency_seconds": _stat_block(latencies),
            "max_tokens_values": {str(k): v for k, v in sorted(caps.items())},
            "contacts_at_the_completion_cap": dict(sorted(at_cap.items())),
            "contacts_at_the_cap_total": sum(at_cap.values()),
            "rows_at_the_completion_cap": len(rows_at_cap),
        }
    return out


def _perception_key_delta(arm_index, base_index, arm_trace, base_trace) -> dict:
    """Per row, the Perception-request payload keys whose bookkeeping-free
    digest differs between the arm and the base. Under THIS cell the first
    request is knowingly NOT byte-identical -- it carries the v2 slot-contract
    cards -- so this is a DIAGNOSTIC that localises the difference, not a
    pass/fail wire claim."""
    rows_compared = 0
    identical_rows = 0
    key_sets: Counter = Counter()
    per_key_differs: Counter = Counter()
    rows_within_the_armed_key_set = 0
    offenders: list[dict] = []
    for sample_id, arm_entries in sorted(arm_index.items()):
        base_entries = base_index.get(sample_id) or []
        if not arm_entries or not base_entries:
            continue
        arm_request = arm_trace["requests"].get(arm_entries[0]["request_id"]) or {}
        base_request = base_trace["requests"].get(base_entries[0]["request_id"]) or {}
        if arm_entries[0]["role_id"] != base_entries[0]["role_id"]:
            continue
        rows_compared += 1
        arm_keys = arm_request.get("key_sha256") or {}
        base_keys = base_request.get("key_sha256") or {}
        differing = sorted(
            k for k in set(arm_keys) | set(base_keys) if arm_keys.get(k) != base_keys.get(k)
        )
        key_sets[json.dumps(differing)] += 1
        for key in differing:
            per_key_differs[key] += 1
        if not differing:
            identical_rows += 1
        if set(differing) <= ARMED_REQUEST_KEYS:
            rows_within_the_armed_key_set += 1
        else:
            offenders.append({"sample_id": sample_id, "differing_keys": differing})
    return {
        "definition": (
            "per row, the set of Perception-request payload keys whose bookkeeping-free "
            "digest differs between the arm and the base. This cell's factor is allowed to "
            "move the armed keys (the contract fill, the supplied evidence, the history and "
            "the evidence provenance content); a differing key outside that set is reported."
        ),
        "armed_key_set": sorted(ARMED_REQUEST_KEYS),
        "rows_compared": rows_compared,
        "rows_byte_identical": identical_rows,
        "rows_whose_delta_stays_inside_the_armed_key_set": rows_within_the_armed_key_set,
        "claim_holds": rows_compared == rows_within_the_armed_key_set,
        "differing_key_sets": {k: v for k, v in sorted(key_sets.items())},
        "rows_in_which_each_key_differs": dict(sorted(per_key_differs.items())),
        "offenders": offenders[:50],
        "offender_count": len(offenders),
    }


def stage_structural(cell: Cell) -> None:
    keys = cell.flight_keys
    phases = {key: _phase_results(cell, key) for key in keys}
    _roster, ids, _metadata, _rs, _ms = roster_and_metadata(cell)
    for key in keys:
        if set(phases[key]["results"]) != set(ids):
            raise SystemExit(f"{key} phase results do not cover the roster exactly")

    manifests = {
        key: json.loads(cell.artifact(key, "run-manifest.json").read_text(encoding="utf-8"))
        for key in keys
    }
    receipts = {}
    for key in keys:
        path = cell.run_dir(key) / "flight-receipts.json"
        receipts[key] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    normaliser = {key: _normaliser_block(phases[key]["results"]) for key in keys}
    compaction = {
        key: _compaction_block(
            phases[key]["results"],
            (((receipts[key] or {}).get("stages") or {}).get("run_phases") or {}).get(
                "native_episode_dispositions"
            ),
        )
        for key in keys
    }
    knowledge = {
        key: _knowledge_pins_block(
            cell, key, manifests[key], phases[key], phases[key]["results"]
        )
        for key in keys
    }
    dispositions = {key: _disposition_block(phases[key]["results"]) for key in keys}
    contact_index = {key: _contact_index(phases[key]["results"]) for key in keys}

    traces = {}
    for key in keys:
        started = time.time()
        traces[key] = _scan_trace(cell, key)
        print(f"  {key} trace scanned in {time.time() - started:.1f}s", flush=True)

    contacts_by_role = {key: defaultdict(list) for key in keys}
    for key in keys:
        for entries in contact_index[key].values():
            for entry in entries:
                contacts_by_role[key][entry["role_id"]].append(entry)

    role_tokens = {
        key: _role_token_block(
            contacts_by_role[key], traces[key]["costs"], traces[key]["requests"]
        )
        for key in keys
    }

    tool_surface: dict[str, dict] = {}
    for key in keys:
        counts: Counter = Counter()
        choices: Counter = Counter()
        for request in traces[key]["requests"].values():
            counts[request.get("tool_schemas_count")] += 1
            choices[request.get("tool_choice")] += 1
        tool_surface[key] = {
            "requests": sum(counts.values()),
            "tool_schemas_count_values": {
                str(k): v for k, v in sorted(counts.items(), key=lambda i: str(i[0]))
            },
            "tool_choice_values": {
                str(k): v for k, v in sorted(choices.items(), key=lambda i: str(i[0]))
            },
            "requests_carrying_a_tools_array": sum(v for k, v in counts.items() if k),
            "no_request_carries_a_tools_array": not any(k for k in counts if k),
            "every_tool_choice_is_none": set(choices) <= {"none", None},
            "distinct_tool_schemas_sha256": len(traces[key]["distinct_tool_schemas_sha256"]),
            "tool_schemas_sha256_counts": traces[key]["distinct_tool_schemas_sha256"],
            "tool_attempts_by_role": traces[key]["tool_attempts_by_role"],
            "tool_calls": traces[key]["tool_attempt_count"],
            "manifest_tool_calls": (manifests[key].get("cost") or {}).get("tool_calls"),
            "constancy_note": (
                "this arm is TOOL-FREE, so the sealed receipt carries no "
                "saea-native-tool-schema-rendering-v1 block; the equivalent constancy proof "
                "is that every request renders the SAME empty tool_schemas array (one "
                "distinct digest over the whole flight) and no role holds tool authority"
            ),
        }

    trajectory = {}
    for key in keys:
        lengths = Counter(len(entries) for entries in contact_index[key].values())
        reviewer = Counter(
            sum(1 for entry in entries if entry["role_id"] == "reviewer")
            for entries in contact_index[key].values()
        )
        trajectory[key] = {
            "contacts_per_row_histogram": {str(k): v for k, v in sorted(lengths.items())},
            "reviewer_contacts_per_row_histogram": {
                str(k): v for k, v in sorted(reviewer.items())
            },
            "contacts": sum(k * v for k, v in lengths.items()),
            "contacts_per_row": sum(k * v for k, v in lengths.items()) / float(cell.rows),
        }

    perception = {
        "arm": _perception_key_delta(
            contact_index["arm"], contact_index["comparator"],
            traces["arm"], traces["comparator"],
        )
    }

    payload = {
        "deliver_normaliser_receipts": normaliser,
        "context_fit_compaction": compaction,
        "knowledge_store_pins": knowledge,
        "tool_surface": tool_surface,
        "trajectory": trajectory,
        "dispositions": dispositions,
        "role_contacts": {
            key: {role: len(rows) for role, rows in sorted(contacts_by_role[key].items())}
            for key in keys
        },
        "role_prompt_tokens": role_tokens,
        "perception_request_delta": perception,
        "phase_artifacts": {
            key: {
                "path": str(phases[key]["path"]), "sha256": phases[key]["sha256"],
                "policy": phases[key]["policy"],
                "controller_policy_id": phases[key]["controller_policy_id"],
                "agent_executor_id": phases[key]["agent_executor_id"],
                "knowledge_snapshot_sha256": phases[key]["knowledge_snapshot_sha256"],
                "protocol_hash": phases[key]["protocol_hash"],
            }
            for key in keys
        },
        "trace_sha256": {key: digest(traces[key]["path"]) for key in keys},
    }
    _write(cell.cache / "structural-raw.json", payload)

    client_tables = {}
    for key in keys:
        rows_out = []
        for sample_id, entries in sorted(contact_index[key].items()):
            for entry in entries:
                request = traces[key]["requests"].get(entry["request_id"]) or {}
                cost = traces[key]["costs"].get(entry["request_id"]) or {}
                rows_out.append(
                    {
                        "sample_id": sample_id,
                        "request_id": entry["request_id"],
                        "order": request.get("order"),
                        "position": entry["position"],
                        "role_id": entry["role_id"],
                        "id_slot": request.get("id_slot"),
                        "prompt_tokens": cost.get("prompt_tokens"),
                        "completion_tokens": cost.get("completion_tokens"),
                        "latency_seconds": cost.get("latency_seconds"),
                        "audio_seconds": cost.get("audio_seconds"),
                    }
                )
        client_tables[key] = rows_out
    (cell.cache / "client-contacts-raw.json").write_text(
        json.dumps(client_tables, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("client contact table cached", flush=True)


# --------------------------------------------------------------------------
# Stage: contrast
# --------------------------------------------------------------------------

def _lock_document() -> dict:
    from speech_aware_evidence_acquisition.data.lock import load_lock

    return dict(load_lock(UMBRELLA_LOCK))


def _score_one_copy(scorer_id: str, copy: Path, result_path: Path) -> tuple[dict, float]:
    from speech_aware_evidence_acquisition.core.base import SCORERS

    if result_path.exists():
        return json.loads(result_path.read_text(encoding="utf-8"))[scorer_id], 0.0
    scorer = SCORERS.resolve(scorer_id)
    started = time.time()
    result = scorer(copy, _lock_document(), DATA)
    elapsed = time.time() - started
    result_path.parent.mkdir(parents=True, exist_ok=True)
    with result_path.open("x", encoding="utf-8") as handle:
        json.dump({scorer_id: result}, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return result, elapsed


def _check_scored(key: str, scorer_id: str, aggregate: dict) -> None:
    if aggregate.get("split_id") not in (None, "train"):
        raise SystemExit(f"{key} {scorer_id} did not resolve TRAIN gold")
    if not aggregate["identity_check"]["passed"]:
        raise SystemExit(f"{key} {scorer_id} port/official identity check failed")


def _score_copies(cell: Cell, scorer_id: str, target_root: Path, keys=None) -> dict:
    target_root.mkdir(parents=True, exist_ok=True)
    out: dict[str, dict] = {}
    for key in (keys or cell.score_keys):
        source, source_sha = outputs_copy(cell, key)
        target_dir = target_root / cell.runs[key]["run_id"]
        target_dir.mkdir(parents=True, exist_ok=True)
        copy = target_dir / source.name
        if not copy.exists():
            shutil.copyfile(source, copy)
        result_path = target_dir / f"{scorer_id}-scores.json"
        result, elapsed = _score_one_copy(scorer_id, copy, result_path)
        aggregate = result["aggregate"]
        _check_scored(key, scorer_id, aggregate)
        entry = {
            "scorer_id": scorer_id,
            "source_outputs_sha256": source_sha,
            "scores_path": str(result_path),
            "scores_sha256": digest(result_path),
            "seconds": elapsed,
            "official": aggregate["official"],
            "split_id": aggregate.get("split_id"),
            "scorer_version": aggregate.get("scorer_version"),
            "evaluator_commit": aggregate.get("evaluator_commit"),
        }
        if "projection" in aggregate:
            entry["projection"] = aggregate["projection"]
        if "normalized" in aggregate:
            entry["symmetric"] = aggregate["normalized"]["micro"]
            entry["symmetric_normalizer_id"] = aggregate["normalized"]["normalizer_id"]
            entry["symmetric_false_merge_count"] = aggregate["normalized"]["false_merge_count"]
        out[key] = entry
        print(f"  {scorer_id} {key}: slu_f1 "
              f"{100 * float(aggregate['official']['slu_f1']):.4f} in {elapsed:.1f}s", flush=True)
    return out


def _companion_contrasts(cell, scored, scorer_id, label, ids, metadata, scenarios,
                         contrasts, keys) -> dict:
    rows = {}
    fields = _row_fields()
    for key in keys:
        document = {
            "verified": True,
            "manifest": scored[key]["scores_path"],
            "scores": json.loads(Path(scored[key]["scores_path"]).read_text(encoding="utf-8")),
        }
        rows[key] = rows_for(document, scorer_id, fields)

    def cluster_of(sid: str) -> str:
        return metadata[sid]["speaker"]

    def scenario_of(sid: str) -> str:
        return metadata[sid]["scenario"]

    row_counts = {
        key: {"scored_rows": len(rows[key]),
              "parsed_rows": sum(1 for sid in ids if rows[key][sid]["parsed"] == 1.0)}
        for key in keys
    }
    comparisons = {}
    for name, left_key, right_key in contrasts:
        if left_key not in rows or right_key not in rows:
            continue
        comparisons[name] = contrast_block(
            cell, name, left_key, right_key, rows, ids, cluster_of, scenario_of,
            scenarios, row_counts, stratified=False,
        )
    return {"scorer_id": scorer_id, "view": label, "row_counts": row_counts,
            "comparisons": comparisons}


def stage_contrast(cell: Cell) -> None:
    keys = ["arm", "comparator"]
    arms = {key: load_arm(cell, key) for key in keys}
    _roster, ids, metadata, _rs, _ms = roster_and_metadata(cell)
    rows = _score_rows(cell, arms, keys)

    def cluster_of(sid: str) -> str:
        return metadata[sid]["speaker"]

    def scenario_of(sid: str) -> str:
        return metadata[sid]["scenario"]

    scenarios = sorted({scenario_of(sid) for sid in ids})
    row_counts = {
        key: {
            "scored_rows": len(rows[key]),
            "parsed_rows": sum(1 for sid in ids if rows[key][sid]["parsed"] == 1.0),
            "malformed_retained_rows": sum(1 for sid in ids if rows[key][sid]["parsed"] != 1.0),
        }
        for key in keys
    }
    comparisons = {}
    for name, left_key, right_key in cell.contrasts:
        comparisons[name] = contrast_block(
            cell, name, left_key, right_key, rows, ids, cluster_of, scenario_of,
            scenarios, row_counts,
        )

    band = {}
    for name in cell.band_contrasts:
        left_key, right_key = next((l, r) for n, l, r in cell.contrasts if n == name)
        per_scenario = {}
        for scenario in scenarios:
            members = sorted(sid for sid in ids if metadata[sid]["scenario"] == scenario)
            contrast = paired_contrast(
                rows[left_key], rows[right_key], metrics=("scenario_action_exact",),
                sample_ids=members, cluster_of=cluster_of, seed=cell.seed,
                n_replicates=cell.draws, ci_level=0.95,
            )["scenario_action_exact"]
            interval = interval_block(
                contrast.bootstrap, "paired whole-speaker cluster bootstrap within the scenario"
            )
            net_harmed = contrast.harms - contrast.saves
            per_scenario[scenario] = {
                "n": contrast.n,
                "left_pct": 100 * contrast.left_mean,
                "right_pct": 100 * contrast.right_mean,
                "delta_pp": 100 * contrast.delta,
                "saves": contrast.saves, "harms": contrast.harms, "ties": contrast.ties,
                "net_harmed_rows": net_harmed,
                "decision_17_flag": net_harmed >= 5,
                "sign_test_p": contrast.sign_test_p,
                "ci95_pp": interval["ci95_pp"],
                "ci90_pp": interval["ci90_pp"],
                "ci95_upper_below_zero": interval["ci95_pp"][1] < 0.0,
            }
        band[name] = {
            "definition": (
                "a scenario loses intent beyond the null band when the CI95 upper bound of "
                "that scenario's own paired intent delta is below zero; owner decision 17 "
                "additionally flags any scenario with five or more net harmed rows. Both are "
                "DIAGNOSTICS, never gates."
            ),
            "per_scenario": per_scenario,
            "scenarios_losing_beyond_the_band": sorted(
                k for k, v in per_scenario.items() if v["ci95_upper_below_zero"]
            ),
            "decision_17_flagged_scenarios": sorted(
                k for k, v in per_scenario.items() if v["decision_17_flag"]
            ),
        }
        print(f"  band {name}: "
              f"{len(band[name]['scenarios_losing_beyond_the_band'])} breaching", flush=True)

    v3 = _score_copies(cell, V3_SCORER, cell.v3_dir, keys)
    sym = _score_copies(cell, SYM_SCORER, cell.sym_dir, keys)
    v3c = _companion_contrasts(cell, v3, V3_SCORER, "projected_v3", ids, metadata, scenarios,
                               cell.contrasts, keys)
    symc = _companion_contrasts(cell, sym, SYM_SCORER, "symmetric", ids, metadata, scenarios,
                                cell.contrasts, keys)

    # The E20 compaction outcome split, if the structural stage found any
    # compacted row. With zero compacted rows there is nothing to split and the
    # block says so.
    compaction_outcome = {"compacted_rows": 0, "comparable": False,
                          "reason": "the structural cache is missing"}
    structural_path = cell.cache / "structural-raw.json"
    if structural_path.exists():
        structural = json.loads(structural_path.read_text(encoding="utf-8"))
        compacted = list(
            (structural.get("context_fit_compaction", {}).get("arm") or {}).get(
                "sample_ids_compacted"
            ) or []
        )
        rest = [sid for sid in ids if sid not in set(compacted)]
        compaction_outcome = {
            "definition": (
                "the arm's official per-row metrics on the rows the E20 context-fit policy "
                "compacted, beside the rows it did not; a descriptive split, never a gate"
            ),
            "compacted_rows": len(compacted),
            "uncompacted_rows": len(rest),
            "comparable": bool(compacted),
            "sample_ids_compacted": compacted,
        }
        if compacted:
            for group, members in (("compacted", compacted), ("uncompacted", rest)):
                compaction_outcome[group] = {
                    "n": len(members),
                    "pooled_slu_f1_pct": 100 * pooled_f1(
                        rows["arm"], members, MICRO_METRICS["slu_f1_micro"]
                    ),
                    "intent_pct": 100 * sum(
                        rows["arm"][sid]["scenario_action_exact"] for sid in members
                    ) / len(members),
                    "comparator_pooled_slu_f1_pct": 100 * pooled_f1(
                        rows["comparator"], members, MICRO_METRICS["slu_f1_micro"]
                    ),
                }
        else:
            compaction_outcome["reason"] = (
                "zero rows compacted under compact-or-abstain, so there is no outcome "
                "difference to measure"
            )

    payload = {
        "row_counts": row_counts,
        "comparisons": comparisons,
        "band": band,
        "projection_v3": v3,
        "projection_v3_contrasts": v3c,
        "train_symmetric": sym,
        "train_symmetric_contrasts": symc,
        "compaction_outcome": compaction_outcome,
        "official_aggregates": {
            key: arms[key]["scores"][SCORER]["aggregate"]["official"] for key in keys
        },
    }
    _write(cell.cache / "contrast-raw.json", payload)


# --------------------------------------------------------------------------
# Stage: lock (the LOCK COMPARISON -- reported, never a gate)
# --------------------------------------------------------------------------

def stage_lock(cell: Cell) -> None:
    """The lock comparison against the provisional v2.0 lock.

    Step 1: the lock comparator's sealed official numbers (verified in
    ``stop``). Step 2: its NODE-APPLIED numbers, re-derived model-free by
    replaying the registered delivery normaliser over a COPY of its sealed
    ``outputs.jsonl`` through the repository's own entry point
    (``analysis.deliver_normaliser_replay.replay``), then scoring the replayed
    copy ONCE with the official scorer through ``core.base.SCORERS``. Step 3:
    an independent cross-check -- the projection-v3 scorer over the untouched
    OFF copy must produce the same numbers (cell B8a's STOP clause 2). Step 4:
    the paired contrasts against the arm on the same 1,080 rows.
    """
    from speech_aware_evidence_acquisition.analysis.deliver_normaliser_replay import replay

    keys = ["arm", "lock"]
    arms = {key: load_arm(cell, key) for key in keys}
    _roster, ids, metadata, _rs, _ms = roster_and_metadata(cell)

    off_copy, off_sha = outputs_copy(cell, "lock")
    on_dir = cell.lock_dir / cell.runs["lock"]["run_id"]
    provenance_path = on_dir / "provenance.json"
    if provenance_path.exists():
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        print("  reusing the existing normaliser replay", flush=True)
    else:
        started = time.time()
        provenance = replay(
            outputs_path=off_copy, normaliser_id=cell.normaliser_id, output_dir=on_dir
        )
        print(f"  replayed {cell.normaliser_id} in {time.time() - started:.1f}s", flush=True)
    if digest(off_copy) != off_sha:
        raise SystemExit("the lock OFF copy changed during the replay")
    if provenance.get("model_calls") != 0:
        raise SystemExit("the normaliser replay reports a model call")
    if provenance.get("rows") != cell.rows:
        raise SystemExit("the normaliser replay did not return every row")
    on_outputs = on_dir / "outputs.jsonl"

    on_result_path = on_dir / f"{SCORER}-scores.json"
    on_result, on_seconds = _score_one_copy(SCORER, on_outputs, on_result_path)
    _check_scored("lock_node_applied", SCORER, on_result["aggregate"])
    on_official = on_result["aggregate"]["official"]

    # Independent cross-check: the v3 SCORER over the untouched OFF copy.
    v3_dir = cell.lock_dir / "v3-cross-check" / cell.runs["lock"]["run_id"]
    v3_dir.mkdir(parents=True, exist_ok=True)
    v3_copy = v3_dir / off_copy.name
    if not v3_copy.exists():
        shutil.copyfile(off_copy, v3_copy)
    v3_result, v3_seconds = _score_one_copy(V3_SCORER, v3_copy, v3_dir / f"{V3_SCORER}-scores.json")
    _check_scored("lock_v3_cross_check", V3_SCORER, v3_result["aggregate"])
    v3_official = v3_result["aggregate"]["official"]

    registered = cell.registered["lock_node_applied"]
    reproduction = {}
    for field in ("slu_f1", "intent_accuracy"):
        want = registered[field]
        got = 100 * float(on_official[field])
        cross = 100 * float(v3_official[field])
        reproduction[field] = {
            "registered": want,
            "node_applied_recomputed": got,
            "v3_scorer_cross_check": cross,
            "reproduced": abs(got - want) < 0.005 + 1e-9,
            "cross_check_agrees": abs(got - cross) < 1e-9,
        }
    if not all(entry["reproduced"] for entry in reproduction.values()):
        raise SystemExit(
            "LOCK: the node-applied lock numbers do not reproduce the registered pair"
        )
    if not all(entry["cross_check_agrees"] for entry in reproduction.values()):
        print("  WARNING: the v3 cross-check differs from the node-applied official number",
              flush=True)

    fields = _row_fields()
    rows = {
        "arm": rows_for(arms["arm"]["document"], SCORER, fields),
        "lock_official": rows_for(arms["lock"]["document"], SCORER, fields),
        "lock_node_applied": rows_for(
            {"verified": True, "manifest": str(on_result_path),
             "scores": {SCORER: on_result}},
            SCORER, fields,
        ),
    }
    for key, table in rows.items():
        if set(table) != set(ids):
            raise SystemExit(f"{key} rows do not cover the roster exactly")

    def cluster_of(sid: str) -> str:
        return metadata[sid]["speaker"]

    def scenario_of(sid: str) -> str:
        return metadata[sid]["scenario"]

    scenarios = sorted({scenario_of(sid) for sid in ids})
    row_counts = {
        key: {"scored_rows": len(table),
              "parsed_rows": sum(1 for sid in ids if table[sid]["parsed"] == 1.0)}
        for key, table in rows.items()
    }
    labels = {
        "arm": cell.label("arm"),
        "lock_official": f"{cell.runs['lock']['label']} official ({cell.runs['lock']['run_id']})",
        "lock_node_applied": (
            f"{cell.runs['lock']['label']} with the {cell.normaliser_id} node applied "
            f"model-free ({cell.runs['lock']['run_id']})"
        ),
    }
    comparisons = {}
    for name, left_key in (
        ("arm_vs_lock_official", "lock_official"),
        ("arm_vs_lock_node_applied", "lock_node_applied"),
    ):
        comparisons[name] = contrast_block(
            cell, name, left_key, "arm", rows, ids, cluster_of, scenario_of,
            scenarios, row_counts, labels=labels,
        )

    payload = {
        "role": (
            "LOCK_COMPARISON: reported, never a gate. A shortfall beyond cell B1r's own null "
            "against the provisional lock is a finding for the owner, not a HARMFUL."
        ),
        "method": {
            "node_applied_derivation": (
                "a COPY of the lock comparator's sealed outputs.jsonl is written under this "
                "read's analysis root and byte-verified against the sealed file; "
                "analysis.deliver_normaliser_replay.replay re-applies the registered "
                f"core.base.DELIVERY_NORMALISERS entry {cell.normaliser_id!r} to every row's "
                "delivered text (zero model calls, the sealed file never opened for writing); "
                "the replayed outputs.jsonl is then scored ONCE with the official scorer "
                f"{SCORER!r} resolved through core.base.SCORERS. This is the same path cell "
                "B8a used to produce the provisional lock numbers."
            ),
            "cross_check": (
                f"the {V3_SCORER!r} scorer over the UNTOUCHED OFF copy re-derives the same "
                "pair a second, independent way (cell B8a's STOP clause 2)"
            ),
            "pairing": (
                "both lock sides are paired against the arm row by row on the same 1,080 "
                "sample ids, with the same whole-speaker cluster bootstrap, seed and draws"
            ),
        },
        "normaliser_id": cell.normaliser_id,
        "replay_provenance": provenance,
        "replay_provenance_path": str(provenance_path),
        "replay_provenance_sha256": digest(provenance_path),
        "off_copy_path": str(off_copy),
        "off_copy_sha256": off_sha,
        "on_outputs_path": str(on_outputs),
        "on_outputs_sha256": digest(on_outputs),
        "on_scores_path": str(on_result_path),
        "on_scores_sha256": digest(on_result_path),
        "on_scoring_seconds": on_seconds,
        "v3_cross_check_scores_path": str(v3_dir / f"{V3_SCORER}-scores.json"),
        "v3_cross_check_seconds": v3_seconds,
        "lock_official_aggregate": arms["lock"]["scores"][SCORER]["aggregate"]["official"],
        "lock_node_applied_aggregate": on_official,
        "lock_v3_cross_check_aggregate": v3_official,
        "registered_reproduction": reproduction,
        "row_counts": row_counts,
        "comparisons": comparisons,
    }
    _write(cell.cache / "lock-raw.json", payload)


# --------------------------------------------------------------------------
# Stage: efficiency
# --------------------------------------------------------------------------

import re  # noqa: E402  (kept beside the log grammar it serves)

RE_TS = re.compile(r"^(\d+)\.(\d\d)\.(\d\d\d)\.(\d\d\d) ")
RE_PROMPT = re.compile(
    r"slot print_timing: id\s+(\d+) \| task (\d+) \| prompt eval time =\s+([\d.]+) ms /\s+(\d+) "
)
RE_EVAL = re.compile(
    r"slot print_timing: id\s+(\d+) \| task (\d+) \|\s+eval time =\s+([\d.]+) ms /\s+(\d+) "
)
RE_TOTAL = re.compile(
    r"slot print_timing: id\s+(\d+) \| task (\d+) \|\s+total time =\s+([\d.]+) ms /\s+(\d+) "
)
RE_RELEASE = re.compile(
    r"slot\s+release: id\s+(\d+) \| task (\d+) \| stop processing: n_tokens =\s*(\d+), "
    r"truncated = (\d+)"
)
RE_MTMD = re.compile(r"slot process_mtmd: id\s+(\d+) \| task (\d+) \|.*n_tokens =\s*(\d+)")
RE_LAUNCH = re.compile(
    r"slot launch_slot_: id\s+(\d+) \| task (\d+) \| processing task, is_child = (\d+)"
)


def _rel_seconds(line: str):
    match = RE_TS.match(line)
    if match is None:
        return None
    minutes, seconds, millis, micros = (int(part) for part in match.groups())
    return minutes * 60 + seconds + millis / 1000.0 + micros / 1_000_000.0


def _parse_server_log(path: Path, window_from_rel: float, window_to_rel: float) -> dict:
    tasks: dict[int, dict] = {}
    segment = 0
    total_lines = 0
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            total_lines += 1
            if "log_info: verbosity" in line:
                segment += 1
                tasks = {}
                continue
            if "slot " not in line:
                continue
            match = RE_LAUNCH.search(line)
            if match is not None:
                task = int(match.group(2))
                entry = tasks.setdefault(task, {"task": task})
                entry["slot"] = int(match.group(1))
                entry["launch_rel"] = _rel_seconds(line)
                continue
            match = RE_PROMPT.search(line)
            if match is not None:
                task = int(match.group(2))
                entry = tasks.setdefault(task, {"task": task})
                entry["slot"] = int(match.group(1))
                entry["prefilled"] = int(match.group(4))
                entry["prefill_ms"] = float(match.group(3))
                continue
            match = RE_EVAL.search(line)
            if match is not None:
                task = int(match.group(2))
                entry = tasks.setdefault(task, {"task": task})
                entry["generated"] = int(match.group(4))
                entry["decode_ms"] = float(match.group(3))
                continue
            match = RE_TOTAL.search(line)
            if match is not None:
                task = int(match.group(2))
                tasks.setdefault(task, {"task": task})["total_ms"] = float(match.group(3))
                continue
            match = RE_RELEASE.search(line)
            if match is not None:
                task = int(match.group(2))
                entry = tasks.setdefault(task, {"task": task})
                entry["slot"] = int(match.group(1))
                entry["release_n_tokens"] = int(match.group(3))
                entry["truncated"] = int(match.group(4))
                entry["release_rel"] = _rel_seconds(line)
                continue
            match = RE_MTMD.search(line)
            if match is not None:
                task = int(match.group(2))
                entry = tasks.setdefault(task, {"task": task})
                entry["mtmd_chunks"] = entry.get("mtmd_chunks", 0) + 1
                continue
    selected = {
        task: entry
        for task, entry in tasks.items()
        if entry.get("release_rel") is not None
        and window_from_rel - 5.0 <= entry["release_rel"] <= window_to_rel + 5.0
        and entry.get("launch_rel") is not None
        and entry["launch_rel"] >= window_from_rel - 5.0
    }
    return {
        "segments_in_file": segment,
        "total_lines": total_lines,
        "tasks_in_last_segment": len(tasks),
        "tasks_in_window": selected,
    }


def _mismatch_profile(joined: list) -> dict:
    """The contacts on which the join test does not hold exactly.

    Below 100.00 % the per-role figures are ESTIMATES. This block says HOW
    far off the estimate can be: where the mismatched contacts sit, how large
    the token discrepancy is, and what share of the flight's prefill they
    carry.
    """
    bad = [
        row for row in joined
        if row["server_prompt_len"] is None
        or row["server_prompt_len"] != row["client_prompt_tokens"]
    ]
    diffs = [
        (row["server_prompt_len"] or 0) - (row["client_prompt_tokens"] or 0)
        for row in bad
    ]
    total_prefilled = sum(row["prefilled"] for row in joined) or 1
    return {
        "definition": (
            "contacts where n_tokens at release minus generated plus one does not equal the "
            "client's usage.prompt_tokens; the per-role and per-position figures are "
            "estimates to the extent of this block"
        ),
        "count": len(bad),
        "share_of_contacts": len(bad) / len(joined) if joined else 0.0,
        "by_position": dict(
            sorted(Counter(f"{r['position']}_{r['role_id']}" for r in bad).items())
        ),
        "by_role": dict(sorted(Counter(r["role_id"] for r in bad).items())),
        "by_slot": dict(sorted(Counter(str(r["slot"]) for r in bad).items())),
        "server_minus_client_tokens": _stat_block(diffs),
        "absolute_token_discrepancy": _stat_block([abs(d) for d in diffs]),
        "prefill_carried_by_mismatched_contacts": sum(r["prefilled"] for r in bad),
        "share_of_flight_prefill": sum(r["prefilled"] for r in bad) / total_prefilled,
        "distinct_sample_ids": len({r["sample_id"] for r in bad}),
    }


def _server_join(cell: Cell, key: str, client_rows: list) -> dict:
    receipts = json.loads(
        (cell.run_dir(key) / "flight-receipts.json").read_text(encoding="utf-8")
    )
    run_phases = receipts["stages"]["run_phases"]
    window = run_phases["contact_window"]
    session_receipt = json.loads(
        (cell.session_dir / "session-receipt.json").read_text(encoding="utf-8")
    )
    started_at = datetime.fromisoformat(session_receipt["started_at"]).timestamp()
    from_rel = window["from"] - started_at
    to_rel = window["to"] - started_at
    parsed = _parse_server_log(cell.session_dir / "server.log", from_rel, to_rel)
    print(f"  [{key}] window rel {from_rel:.1f}..{to_rel:.1f}s, "
          f"{len(parsed['tasks_in_window'])} server tasks", flush=True)

    client = sorted(client_rows, key=lambda row: row["order"])
    by_slot_client: dict[int, list] = defaultdict(list)
    for row in client:
        by_slot_client[int(row["id_slot"])].append(row)
    by_slot_server: dict[int, list] = defaultdict(list)
    for entry in parsed["tasks_in_window"].values():
        by_slot_server[int(entry["slot"])].append(entry)
    for slot in by_slot_server:
        by_slot_server[slot].sort(key=lambda entry: entry["launch_rel"])

    joined: list[dict] = []
    slot_report = {}
    for slot in sorted(set(by_slot_client) | set(by_slot_server)):
        left = by_slot_client.get(slot, [])
        right = by_slot_server.get(slot, [])
        slot_report[str(slot)] = {"client_contacts": len(left), "server_tasks": len(right)}
        for row, entry in zip(left, right):
            prompt_len = None
            if entry.get("release_n_tokens") is not None:
                prompt_len = entry["release_n_tokens"] - int(entry.get("generated") or 0) + 1
            joined.append(
                {
                    "sample_id": row["sample_id"],
                    "position": row["position"],
                    "role_id": row["role_id"],
                    "slot": slot,
                    "client_prompt_tokens": row["prompt_tokens"],
                    "client_latency_seconds": row["latency_seconds"],
                    "server_prompt_len": prompt_len,
                    "prefilled": int(entry.get("prefilled") or 0),
                    "generated": int(entry.get("generated") or 0),
                    "truncated": entry.get("truncated"),
                    "mtmd_chunks": int(entry.get("mtmd_chunks") or 0),
                    "launch_rel": entry.get("launch_rel"),
                    "release_rel": entry.get("release_rel"),
                    "prefill_ms": entry.get("prefill_ms"),
                }
            )
    exact = sum(
        1 for row in joined
        if row["server_prompt_len"] is not None
        and row["server_prompt_len"] == row["client_prompt_tokens"]
    )
    join_quality = {
        "definition": (
            "the throughput report's own join test: n_tokens at release minus generated plus "
            "one must equal the client's usage.prompt_tokens. Below 100.00 % the per-role "
            "figures are ESTIMATES, not measurements."
        ),
        "scoping": (
            "the resident session serves many flights -- this arm's replicate PLANr flew on "
            "the SAME session after it -- so the join takes ONLY the server tasks whose "
            "launch and release timestamps fall inside THIS flight's own sealed contact "
            "window (flight-receipts stages.run_phases.contact_window, converted to "
            "log-relative seconds through the session receipt's started_at), and then aligns "
            "them to this flight's own client contacts PER SLOT in launch order, because the "
            "config pins decoding_params.id_slot = 'per-sample'. Every joined client contact "
            "is one of this run's own sealed request ids. No other flight's records can "
            "enter, and the exact-match share below is the proof."
        ),
        "joined_contacts": len(joined),
        "client_contacts": len(client),
        "server_tasks_in_window": len(parsed["tasks_in_window"]),
        "exact_matches": exact,
        "exact_share": exact / len(joined) if joined else 0.0,
        "is_a_measurement": bool(joined) and exact == len(joined) == len(client),
        "mismatch_profile": _mismatch_profile(joined),
        "per_slot": slot_report,
        "segments_in_server_log": parsed["segments_in_file"],
        "server_log_path": str(cell.session_dir / "server.log"),
        "server_log_size_bytes": (cell.session_dir / "server.log").stat().st_size,
        "session_started_at": session_receipt["started_at"],
        "contact_window_epoch": window,
        "contact_window_utc": {
            "from": datetime.fromtimestamp(window["from"], timezone.utc).isoformat(),
            "to": datetime.fromtimestamp(window["to"], timezone.utc).isoformat(),
        },
        "contact_window_relative_seconds": {"from": from_rel, "to": to_rel},
    }

    per_position: dict[str, dict] = {}
    groups: dict[str, list] = defaultdict(list)
    for row in joined:
        groups[f"{row['position']}_{row['role_id']}"].append(row)
    total_prefilled = sum(row["prefilled"] for row in joined)
    for name in sorted(groups, key=lambda k: (int(k.split("_")[0]), k)):
        rows = groups[name]
        prompt = [row["client_prompt_tokens"] for row in rows if row["client_prompt_tokens"]]
        prefilled = [row["prefilled"] for row in rows]
        generated = [row["generated"] for row in rows]
        lengths = [row["server_prompt_len"] for row in rows if row["server_prompt_len"]]
        latency = [row["client_latency_seconds"] for row in rows if row["client_latency_seconds"]]
        per_position[name] = {
            "role": rows[0]["role_id"],
            "contacts": len(rows),
            "client_prompt_tokens": _stat_block(prompt),
            "server_prefilled_tokens": _stat_block(prefilled),
            "generated_tokens": _stat_block(generated),
            "client_latency_seconds": _stat_block(latency),
            "cached_share": (
                1.0 - sum(prefilled) / sum(lengths) if lengths and sum(lengths) else None
            ),
            "packet_re_decoded_share": sum(1 for r in rows if r["mtmd_chunks"] > 0) / len(rows),
            "prefilled_per_row": sum(prefilled) / float(cell.rows),
            "share_of_row_prefill": (
                sum(prefilled) / total_prefilled if total_prefilled else None
            ),
            "truncations": sum(1 for row in rows if row.get("truncated")),
        }

    per_role: dict[str, dict] = {}
    role_groups: dict[str, list] = defaultdict(list)
    for row in joined:
        role_groups[row["role_id"]].append(row)
    for role in sorted(role_groups):
        rows = role_groups[role]
        prefilled = [row["prefilled"] for row in rows]
        lengths = [row["server_prompt_len"] for row in rows if row["server_prompt_len"]]
        per_role[role] = {
            "contacts": len(rows),
            "contacts_per_row": len(rows) / float(cell.rows),
            "prefilled": _stat_block(prefilled),
            "prefilled_per_row": sum(prefilled) / float(cell.rows),
            "cached_share": (
                1.0 - sum(prefilled) / sum(lengths) if lengths and sum(lengths) else None
            ),
            "packet_re_decoded_share": sum(1 for r in rows if r["mtmd_chunks"] > 0) / len(rows),
        }

    wall = run_phases["wall_seconds"]
    total_generated = sum(row["generated"] for row in joined)
    total_prompt_len = sum(row["server_prompt_len"] or 0 for row in joined)
    launches = sorted(r["launch_rel"] for r in joined if r["launch_rel"] is not None)
    releases = sorted(r["release_rel"] for r in joined if r["release_rel"] is not None)
    span = (releases[-1] - launches[0]) if releases and launches else None
    aggregate = {
        "wall_seconds": wall,
        "contacts": len(joined),
        "prefilled_tokens_total": total_prefilled,
        "prefilled_tokens_per_row": total_prefilled / float(cell.rows),
        "server_prompt_tokens_total": total_prompt_len,
        "client_prompt_tokens_per_row": sum(
            row["client_prompt_tokens"] or 0 for row in joined
        ) / float(cell.rows),
        "generated_tokens_total": total_generated,
        "generated_tokens_per_row": total_generated / float(cell.rows),
        "cache_hit_share": (
            1.0 - total_prefilled / total_prompt_len if total_prompt_len else None
        ),
        "aggregate_prefill_tokens_per_second": total_prefilled / wall if wall else None,
        "aggregate_decode_tokens_per_second": total_generated / wall if wall else None,
        "packet_re_decodes_total": sum(1 for row in joined if row["mtmd_chunks"] > 0),
        "packet_decodes_per_row": (
            sum(1 for row in joined if row["mtmd_chunks"] > 0) / float(cell.rows)
        ),
        "truncations": sum(1 for row in joined if row.get("truncated")),
        "measured_span_seconds": span,
        "contacts_per_minute_from_release_records": (
            len(joined) / (span / 60.0) if span else None
        ),
        "contacts_per_minute_over_the_sealed_wall": len(joined) / (wall / 60.0) if wall else None,
        "contacts_per_minute_definition": (
            "measured from the serving session's own server.log RELEASE records inside this "
            "flight's sealed contact window -- never from monitor.jsonl requests_total, which "
            "undercounts"
        ),
        "per_request_prefill_tokens_per_second": _stat_block(
            [
                row["prefilled"] / (row["prefill_ms"] / 1000.0)
                for row in joined
                if row.get("prefill_ms") and row["prefilled"]
            ]
        ),
    }
    return {"join_quality": join_quality, "per_position": per_position,
            "per_role": per_role, "aggregate": aggregate}


def fit_block(root: Path) -> dict:
    if root is None or not root.exists():
        return {"fit_dir": str(root), "present": False}
    receipts = sorted(root.glob("**/*.request-fit.json"))
    endpoints = 0
    per_phase: dict[str, dict] = {}
    min_margin = None
    min_margin_phase = None
    max_required = None
    every_fits = True
    for path in receipts:
        document = json.loads(path.read_text(encoding="utf-8"))
        output = document.get("output") or {}
        endpoints += int(output.get("contacts") or 0)
        if not output.get("every_request_fits", True):
            every_fits = False
        parts = str(output.get("agent_contact_id") or "").split(":")
        phase = parts[1] if len(parts) > 2 else "unknown"
        margin = output.get("minimum_margin_tokens")
        entry = per_phase.setdefault(
            phase, {"contacts": 0, "endpoints": 0, "min_margin_tokens": None,
                    "max_required_tokens": None}
        )
        entry["contacts"] += 1
        entry["endpoints"] += int(output.get("contacts") or 0)
        if isinstance(margin, (int, float)):
            if entry["min_margin_tokens"] is None or margin < entry["min_margin_tokens"]:
                entry["min_margin_tokens"] = margin
            if min_margin is None or margin < min_margin:
                min_margin = margin
                min_margin_phase = phase
        for row in output.get("rows") or []:
            if not row.get("fits", True):
                every_fits = False
            required = row.get("required_tokens")
            if isinstance(required, (int, float)):
                if entry["max_required_tokens"] is None or required > entry["max_required_tokens"]:
                    entry["max_required_tokens"] = required
                if max_required is None or required > max_required:
                    max_required = required
    return {
        "fit_dir": str(root), "present": True,
        "request_fit_receipts": len(receipts), "endpoints": endpoints,
        "per_phase": {k: per_phase[k] for k in sorted(per_phase)},
        "every_request_fits": every_fits,
        "min_margin_tokens": min_margin, "min_margin_phase": min_margin_phase,
        "max_required_tokens": max_required, "slot_tokens": SLOT_TOKENS,
    }


def costs_block(cell: Cell) -> dict:
    out: dict[str, dict] = {}
    for key in cell.flight_keys:
        generation = json.loads(
            cell.artifact(key, "generation-manifest.json").read_text(encoding="utf-8")
        )
        cost = generation["cost"]
        receipts_path = cell.run_dir(key) / "flight-receipts.json"
        rec = json.loads(receipts_path.read_text(encoding="utf-8")) if receipts_path.exists() \
            else None
        attach_path = cell.run_dir(key) / (
            f"{cell.runs[key]['run_id']}-{cell.runs[key]['attempt_id']}"
            ".session-attach-receipt.json"
        )
        att = json.loads(attach_path.read_text(encoding="utf-8")) if attach_path.exists() else None
        monitor = ((rec or {}).get("stages", {}).get("seal") or {}).get(
            "serving_monitor_summary"
        ) if rec else None
        phases = (rec or {}).get("stages", {}).get("run_phases") if rec else None
        entry = {
            "contacts": cost["calls_used"],
            "contacts_per_row": cost["calls_used"] / float(cell.rows),
            "repeated_speech_seconds": cost["audio_seconds_used"],
            "prompt_tokens_total": cost["prompt_tokens_total"],
            "prompt_tokens_per_row": cost["prompt_tokens_total"] / float(cell.rows),
            "prompt_tokens_per_contact": cost["prompt_tokens_total"] / cost["calls_used"],
            "completion_tokens_total": cost["completion_tokens_total"],
            "latency_seconds_total": cost["latency_seconds_total"],
            "tool_calls": cost["tool_calls"],
            "flight_receipts_hash": (rec or {}).get("receipts_hash"),
            "session_id": (att or {}).get("session_id"),
            "serving_geometry": (att or {}).get("serving_geometry"),
        }
        if monitor:
            entry.update({
                "gpu_active_seconds": monitor["active_seconds"],
                "gpu_hours": monitor["active_seconds"] / 3600.0,
                "monitor_wall_seconds": monitor["wall_seconds"],
                "mean_utilization_percent": monitor["mean_utilization_percent"],
                "parked_fraction": monitor["parked_fraction"],
                "parked_seconds": monitor.get("parked_seconds"),
                "mean_power_watts": monitor.get("mean_power_watts"),
                "peak_power_watts": monitor.get("peak_power_watts"),
                "monitor_requests_delta": monitor.get("requests_delta"),
            })
        if phases:
            entry.update({
                "generation_wall_seconds": phases.get("wall_seconds"),
                "wall_seconds_per_row": (phases.get("wall_seconds") or 0) / float(cell.rows),
                "slot_occupancy": phases.get("slot_occupancy"),
                "average_latency_seconds": phases.get("average_latency_seconds"),
                "serving_slots": phases.get("serving_slots"),
                "contacts_per_minute": (phases.get("contacts_per_second") or 0) * 60.0,
                "contact_window": phases.get("contact_window"),
                "native_episode_dispositions": phases.get("native_episode_dispositions"),
            })
        fit_run = cell.runs[key].get("fit_run_id")
        if fit_run:
            entry["fit"] = fit_block(DATA / "prepared" / fit_run)
        out[key] = entry

    attempts_dir = DATA / "attempts" / cell.runs["arm"]["run_id"]
    attempts = {}
    if attempts_dir.exists():
        for path in sorted(attempts_dir.glob("*.json")):
            doc = json.loads(path.read_text(encoding="utf-8"))
            actual = doc.get("actual") or {}
            attempts[doc["attempt_id"]] = {
                "state": doc.get("state"), "calls": actual.get("calls"),
                "audio_seconds": actual.get("audio_seconds"),
                "failure_reason": doc.get("failure_reason"),
            }
    ceilings = cell.registered["registered_ceilings"]
    cumulative_calls = sum(v["calls"] or 0 for v in attempts.values())
    cumulative_audio = sum(v["audio_seconds"] or 0.0 for v in attempts.values())
    out["run_cumulative"] = {
        "definition": (
            "the registered cap is enforced run-cumulatively across every attempt of this run "
            "id (core.attempts.AttemptStore.prior_actual_usage, invariants I3/I6)"
        ),
        "attempts": attempts,
        "calls": cumulative_calls,
        "audio_seconds": cumulative_audio,
        "planned_model_calls": ceilings["generation_calls_run_cumulative"],
        "within_ceiling": cumulative_calls <= ceilings["generation_calls_run_cumulative"],
        "audio_within_ceiling": cumulative_audio <= ceilings["repeated_speech_seconds"],
    }
    out["registered_ceilings"] = dict(ceilings)
    return out


def stage_efficiency(cell: Cell) -> None:
    client = json.loads((cell.cache / "client-contacts-raw.json").read_text(encoding="utf-8"))
    server = {key: _server_join(cell, key, client[key]) for key in cell.flight_keys}
    costs = costs_block(cell)
    reference = cell.registered["comparator_cost_reference"]
    sealed_reference_path = DATA / reference["sealed_efficiency_path"]
    sealed_reference = None
    if sealed_reference_path.exists():
        sealed = json.loads(sealed_reference_path.read_text(encoding="utf-8"))
        sealed_reference = {
            "path": str(sealed_reference_path),
            "sha256": digest(sealed_reference_path),
            "headline": sealed.get("headline"),
            "per_position": (sealed.get("server_join") or {}).get("per_position"),
        }
    projected = {}
    for key in cell.flight_keys:
        hours = costs[key].get("gpu_hours")
        if hours:
            projected[key] = {
                "gpu_hours_per_1080": hours,
                "test_read_hours": hours * cell.test_read_rows / float(cell.rows),
            }
    projected["comparator_reference"] = {
        "gpu_hours_per_1080": reference["gpu_hours_per_1080"],
        "test_read_hours": reference["projected_read_hours_13078"],
    }

    # Where the extra GPU hour-fraction went, position by position.
    arm_positions = server["arm"]["per_position"]
    base_positions = server["comparator"]["per_position"]
    position_delta = {}
    for name in sorted(set(arm_positions) | set(base_positions),
                       key=lambda k: (int(k.split("_")[0]), k)):
        a = arm_positions.get(name) or {}
        b = base_positions.get(name) or {}
        position_delta[name] = {
            "arm_prefilled_per_row": a.get("prefilled_per_row"),
            "comparator_prefilled_per_row": b.get("prefilled_per_row"),
            "delta_prefilled_per_row": (
                (a.get("prefilled_per_row") or 0) - (b.get("prefilled_per_row") or 0)
                if a or b else None
            ),
            "arm_contacts": a.get("contacts"),
            "comparator_contacts": b.get("contacts"),
            "arm_cached_share": a.get("cached_share"),
            "comparator_cached_share": b.get("cached_share"),
            "arm_client_prompt_tokens_median": (a.get("client_prompt_tokens") or {}).get("median"),
            "comparator_client_prompt_tokens_median": (
                b.get("client_prompt_tokens") or {}
            ).get("median"),
        }
    arm_cost = costs["arm"]
    base_cost = costs["comparator"]
    decomposition = {
        "definition": (
            "the arm's GPU hours per 1,080 rows beside the base's, with the measured "
            "quantities that move it: contacts, prefilled tokens, generated tokens and the "
            "sealed generation wall. Attribution is descriptive, not causal."
        ),
        "arm_gpu_hours": arm_cost.get("gpu_hours"),
        "comparator_gpu_hours": base_cost.get("gpu_hours"),
        "delta_gpu_hours": (
            (arm_cost.get("gpu_hours") or 0) - (base_cost.get("gpu_hours") or 0)
        ),
        "relative_increase": (
            ((arm_cost.get("gpu_hours") or 0) / base_cost["gpu_hours"] - 1.0)
            if base_cost.get("gpu_hours") else None
        ),
        "arm_contacts": arm_cost["contacts"],
        "comparator_contacts": base_cost["contacts"],
        "arm_wall_seconds": arm_cost.get("generation_wall_seconds"),
        "comparator_wall_seconds": base_cost.get("generation_wall_seconds"),
        "arm_prefilled_tokens_per_row": server["arm"]["aggregate"]["prefilled_tokens_per_row"],
        "comparator_prefilled_tokens_per_row": server["comparator"]["aggregate"][
            "prefilled_tokens_per_row"
        ],
        "arm_generated_tokens_per_row": server["arm"]["aggregate"]["generated_tokens_per_row"],
        "comparator_generated_tokens_per_row": server["comparator"]["aggregate"][
            "generated_tokens_per_row"
        ],
        "arm_client_prompt_tokens_per_row": arm_cost["prompt_tokens_per_row"],
        "comparator_client_prompt_tokens_per_row": base_cost["prompt_tokens_per_row"],
        "per_position_prefill_delta": position_delta,
        "candidate_causes": {
            "slot_contract_cards_v2": (
                "the M4b factor replaces the v1 slot-contract cards with the v2 release's, "
                "which are longer; the per-position prefill delta above localises it"
            ),
            "context_compaction": (
                "read from the E20 receipts in structural.json: if zero rows compacted, "
                "compaction contributes nothing to the cost"
            ),
            "delivery_normaliser": (
                "module M3 runs model-free at delivery and makes no model contact, so it "
                "cannot contribute GPU time"
            ),
            "review_loop": (
                "the review-loop marker changes no contact count by itself; the realised "
                "contacts-per-row histogram in structural.json is the measurement"
            ),
        },
    }

    payload = {
        "server_join": server,
        "costs": costs,
        "comparator_cost_reference": reference,
        "comparator_sealed_efficiency": sealed_reference,
        "b4b_reference": cell.registered["b4b_reference"],
        "gpu_hours_decomposition": decomposition,
        "projected_test_read": {"rows": cell.test_read_rows, "rates": projected},
    }
    _write(cell.cache / "efficiency-raw.json", payload)


# --------------------------------------------------------------------------
# Stage: frontier (owner decision 75)
# --------------------------------------------------------------------------

def stage_frontier(cell: Cell) -> None:
    """The decision-75 frontier row for this cell, beside the registered rows.

    ``scripts/analysis/slurp_module_frontier.py`` cannot take a new cell: its
    ``collect`` stage iterates two HARD-CODED module-level tables (``ARMS`` and
    ``CELLS``) and its only command-line arguments are ``--stage``,
    ``--data-root``, ``--out-dir`` and ``--self-check``. Adding this cell would
    be a source edit to a repository script, which this read is not authorised
    to make, so the row is computed here and the verdict says so.
    """
    efficiency_path = cell.cache / "efficiency-raw.json"
    if not efficiency_path.exists():
        raise SystemExit("run the efficiency stage before the frontier stage")
    efficiency = json.loads(efficiency_path.read_text(encoding="utf-8"))
    contrasts = json.loads((cell.cache / "contrast-raw.json").read_text(encoding="utf-8"))
    lock = json.loads((cell.cache / "lock-raw.json").read_text(encoding="utf-8"))
    structural = json.loads((cell.cache / "structural-raw.json").read_text(encoding="utf-8"))

    primary = contrasts["comparisons"]["arm_vs_comparator"]
    slu = primary["pooled_micro"]["slu_f1_micro"]
    intent = primary["per_row"]["scenario_action_exact"]
    arm_cost = efficiency["costs"]["arm"]
    arm_join = efficiency["server_join"]["arm"]

    row = {
        "cell": "PLAN",
        "status_source": "this read's decision block",
        "official_slu": slu["right_pct"],
        "official_intent": intent["right_pct"],
        "official_slu_delta_pp_vs_comparator": slu["delta_pp"],
        "official_intent_delta_pp_vs_comparator": intent["delta_pp"],
        "comparator": cell.label("comparator"),
        "gpu_hours_per_1080": arm_cost.get("gpu_hours"),
        "contacts_per_row": arm_cost["contacts_per_row"],
        "prefilled_tokens_per_row": arm_join["aggregate"]["prefilled_tokens_per_row"],
        "token_basis": (
            "measured" if arm_join["join_quality"]["is_a_measurement"] else "ESTIMATE"
        ),
        "contacts_per_minute": arm_join["aggregate"][
            "contacts_per_minute_from_release_records"
        ],
        "projected_read_hours_13078": efficiency["projected_test_read"]["rates"]["arm"][
            "test_read_hours"
        ],
        "rows_compacted": (structural.get("context_fit_compaction", {}).get("arm") or {}).get(
            "rows_compacted"
        ),
    }
    comparator_row = {
        "cell": "B1-notool (this read's own re-measurement)",
        "official_slu": slu["left_pct"],
        "official_intent": intent["left_pct"],
        "gpu_hours_per_1080": efficiency["costs"]["comparator"].get("gpu_hours"),
        "contacts_per_row": efficiency["costs"]["comparator"]["contacts_per_row"],
        "prefilled_tokens_per_row": efficiency["server_join"]["comparator"]["aggregate"][
            "prefilled_tokens_per_row"
        ],
        "token_basis": (
            "measured"
            if efficiency["server_join"]["comparator"]["join_quality"]["is_a_measurement"]
            else "ESTIMATE"
        ),
    }
    registered_rows = list(cell.registered["frontier_registered_rows"])

    # The decision-75 triple the brief asks for, beside the absolute-number
    # frontier the stage-3 prelude document builds.
    def triple(name, delta, prefilled, hours):
        return {
            "cell": name,
            "official_slu_delta_pp": delta,
            "prefilled_tokens_per_row": prefilled,
            "gpu_hours_per_1080": hours,
            "delta_per_gpu_hour": (delta / hours) if hours else None,
            "delta_per_1000_prefilled_tokens": (
                1000.0 * delta / prefilled if prefilled else None
            ),
        }

    lock_official = lock["comparisons"]["arm_vs_lock_official"]["pooled_micro"][
        "slu_f1_micro"
    ]["delta_pp"]
    lock_node = lock["comparisons"]["arm_vs_lock_node_applied"]["pooled_micro"][
        "slu_f1_micro"
    ]["delta_pp"]
    triples = [
        triple("PLAN vs B1-notool", slu["delta_pp"], row["prefilled_tokens_per_row"],
               row["gpu_hours_per_1080"]),
        triple("PLAN vs B5e official (lock comparison)", lock_official,
               row["prefilled_tokens_per_row"], row["gpu_hours_per_1080"]),
        triple("PLAN vs B5e node-applied (lock comparison)", lock_node,
               row["prefilled_tokens_per_row"], row["gpu_hours_per_1080"]),
    ]

    # Pareto position in each cost plane, over the registered rows plus this one.
    all_rows = registered_rows + [
        {"cell": "PLAN", "official_slu": row["official_slu"],
         "gpu_hours_per_1080": row["gpu_hours_per_1080"],
         "prefilled_tokens_per_row": row["prefilled_tokens_per_row"],
         "token_basis": row["token_basis"], "status": "this read"}
    ]

    def pareto(cost_field):
        ordered = sorted(all_rows, key=lambda r: (r[cost_field], -r["official_slu"]))
        best = float("-inf")
        front = []
        for item in ordered:
            if item["official_slu"] > best:
                best = item["official_slu"]
                front.append({"cell": item["cell"], "cost": item[cost_field],
                              "official_slu": item["official_slu"]})
        return front

    payload = {
        "definition": (
            "owner decision 75: the frontier row is this cell's official SLU-F1 (and its "
            "delta against its own comparator) against two cost axes -- prefilled tokens per "
            "row and GPU hours per 1,080 rows. The absolute-number frontier is the one the "
            "stage-3 prelude document builds; deltas are never chained across cells."
        ),
        "tool_note": (
            "scripts/analysis/slurp_module_frontier.py cannot accept a new cell: its collect "
            "stage iterates the hard-coded module-level ARMS and CELLS tables and takes only "
            "--stage / --data-root / --out-dir / --self-check. This row is therefore computed "
            "by this read; adding it to that script is a separate source edit."
        ),
        "row": row,
        "comparator_row_remeasured": comparator_row,
        "registered_rows": registered_rows,
        "registered_rows_source": cell.registered["frontier_source"],
        "decision_75_triples": triples,
        "pareto_gpu_hour_plane": pareto("gpu_hours_per_1080"),
        "pareto_prefilled_token_plane": pareto("prefilled_tokens_per_row"),
        "plan_is_on_the_gpu_hour_frontier": any(
            item["cell"] == "PLAN" for item in pareto("gpu_hours_per_1080")
        ),
        "plan_is_on_the_prefilled_token_frontier": any(
            item["cell"] == "PLAN" for item in pareto("prefilled_tokens_per_row")
        ),
    }
    _write(cell.cache / "frontier-raw.json", payload)


# --------------------------------------------------------------------------
# Stage: verdict
# --------------------------------------------------------------------------

def _decision(cell, contrasts, structural, lock, efficiency, frontier, stop) -> dict:
    primary = contrasts["comparisons"]["arm_vs_comparator"]
    slu = primary["pooled_micro"]["slu_f1_micro"]
    intent = primary["per_row"]["scenario_action_exact"]
    slu_ci = slu["speaker_clustered"]["ci95_pp"]
    intent_ci = intent["speaker_clustered"]["ci95_pp"]
    slu_point = slu["delta_pp"]
    intent_point = intent["delta_pp"]

    harmful = []
    if slu_point < -cell.h_slu:
        harmful.append(
            f"official pooled SLU-F1 point estimate {slu_point:+.4f} pp is below -{cell.h_slu}"
        )
    if intent_point < -cell.h_intent:
        harmful.append(
            f"intent point estimate {intent_point:+.4f} pp is below -{cell.h_intent}"
        )
    if slu_ci[1] < 0.0:
        harmful.append(
            f"official pooled SLU-F1 CI95 upper bound {slu_ci[1]:+.4f} pp is below zero"
        )
    if intent_ci[1] < 0.0:
        harmful.append(f"intent CI95 upper bound {intent_ci[1]:+.4f} pp is below zero")

    slu_ni = slu_ci[0] > -cell.h_slu
    intent_ni = intent_ci[0] > -cell.h_intent
    if harmful:
        status = "HARMFUL"
    elif slu_ni and intent_ni:
        status = "ADMITTED" if slu_ci[0] > 0.0 else "NEUTRAL"
    else:
        status = "NON-INFERIORITY NOT PROVEN"

    guards = {
        "official_pooled_slu_f1": {
            "metric": "official pooled SLU micro F1 (slurp-slu-official-train), natural mixture",
            "comparator_pct": slu["left_pct"], "arm_pct": slu["right_pct"],
            "delta_pp": slu_point, "ci95_pp": slu_ci,
            "ci90_pp": slu["speaker_clustered"]["ci90_pp"],
            "scenario_stratified_ci90_pp": slu["scenario_stratified"]["ci90_pp"],
            "equal_scenario_delta_pp": slu["equal_scenario_delta_pp"],
            "margin_h_pp": cell.h_slu,
            "ci95_lower_exceeds_minus_h": slu_ni,
            "ci95_lower_above_zero": slu_ci[0] > 0.0,
            "point_below_minus_h": slu_point < -cell.h_slu,
            "ci95_upper_below_zero": slu_ci[1] < 0.0,
        },
        "intent_accuracy": {
            "metric": "intent (joint scenario+action) accuracy",
            "comparator_pct": intent["left_pct"], "arm_pct": intent["right_pct"],
            "delta_pp": intent_point, "ci95_pp": intent_ci,
            "ci90_pp": intent["speaker_clustered"]["ci90_pp"],
            "scenario_stratified_ci90_pp": intent["scenario_stratified"]["ci90_pp"],
            "equal_scenario_delta_pp": intent["equal_scenario_delta_pp"],
            "margin_h_pp": cell.h_intent,
            "ci95_lower_exceeds_minus_h": intent_ni,
            "point_below_minus_h": intent_point < -cell.h_intent,
            "ci95_upper_below_zero": intent_ci[1] < 0.0,
            "saves": intent["saves"], "harms": intent["harms"], "ties": intent["ties"],
            "mcnemar_p": intent["sign_test_p"],
        },
    }

    # The LOCK statement and the LOCK COMPARISON.
    arm_slu = slu["right_pct"]
    arm_intent = intent["right_pct"]
    lock_blocks = {}
    for name, registered in (
        ("arm_vs_lock_official", cell.registered["lock_official"]),
        ("arm_vs_lock_node_applied", cell.registered["lock_node_applied"]),
    ):
        block = lock["comparisons"][name]
        b_slu = block["pooled_micro"]["slu_f1_micro"]
        b_intent = block["per_row"]["scenario_action_exact"]
        lock_blocks[name] = {
            "lock_side_slu_pct": b_slu["left_pct"],
            "lock_side_intent_pct": b_intent["left_pct"],
            "arm_slu_pct": b_slu["right_pct"],
            "arm_intent_pct": b_intent["right_pct"],
            "slu_delta_pp": b_slu["delta_pp"],
            "slu_ci95_pp": b_slu["speaker_clustered"]["ci95_pp"],
            "intent_delta_pp": b_intent["delta_pp"],
            "intent_ci95_pp": b_intent["speaker_clustered"]["ci95_pp"],
            "shortfall_beyond_the_own_null_slu": b_slu["delta_pp"] < -cell.h_slu,
            "shortfall_beyond_the_own_null_intent": b_intent["delta_pp"] < -cell.h_intent,
            "registered_lock_side": {k: v for k, v in registered.items() if k != "source"},
        }
    lock_comparison = {
        "role": lock["role"],
        "method": lock["method"],
        "registered_reproduction": lock["registered_reproduction"],
        "comparisons": lock_blocks,
        "shortfall_is_a_finding_for_the_owner": any(
            entry["shortfall_beyond_the_own_null_slu"]
            or entry["shortfall_beyond_the_own_null_intent"]
            for entry in lock_blocks.values()
        ),
    }
    lock_statement = {
        "candidate_v2_0_lock_numbers": {
            "official_pooled_slu_f1": arm_slu,
            "official_intent_accuracy": arm_intent,
            "official_span_f1": primary["pooled_micro"]["span_f1_micro"]["right_pct"],
            "scorer": SCORER,
            "roster": "TRAIN Fold A, 1,080 rows (development numbers, owner decision 28)",
        },
        "module_list": [
            "M1 exemplar supply (train-exemplars, k = 20)",
            "M4b slot store v2 (knowledge_stores['slot-contracts'] -> slot-contracts-v2)",
            "M3 delivery normaliser (native_episode.deliver_normaliser = "
            "saea-deliver-normalise-v3)",
            "the Reviewer's native toolkit RETIRED (no phase_tools, no tools array)",
            "item E13 finite_completion_policy = deliver-latest-or-abstain",
            "item E22 react_exhaustion_policy = continue-without-answer",
            "item E20 context_fit_policy = compact-or-abstain",
        ],
        "pending": (
            "v2.0 is LOCKED on these numbers once cell PLANr reproduces them within the "
            "plan's own null; until then the provisional lock on B5e plus the normaliser "
            "node (63.78 / 81.85) stands"
        ),
        "locked_now": False,
        "gating_is_not_harmful": status != "HARMFUL",
    }

    arm_costs = efficiency["costs"]["arm"]
    aggregate = efficiency["server_join"]["arm"]["aggregate"]
    reference = cell.registered["comparator_cost_reference"]
    efficiency_headline = {
        "prefilled_tokens_per_row": aggregate["prefilled_tokens_per_row"],
        "prefilled_tokens_per_row_comparator": reference["prefilled_tokens_per_row"],
        "prefilled_tokens_per_row_comparator_remeasured": efficiency["server_join"][
            "comparator"]["aggregate"]["prefilled_tokens_per_row"],
        "gpu_hours_per_1080": arm_costs.get("gpu_hours"),
        "gpu_hours_per_1080_comparator": reference["gpu_hours_per_1080"],
        "contacts_per_minute": aggregate.get("contacts_per_minute_from_release_records"),
        "contacts_per_minute_comparator": reference["contacts_per_minute"],
        "contacts_per_row": arm_costs["contacts_per_row"],
        "contacts_per_row_comparator": reference["contacts_per_row"],
        "cache_hit_share": aggregate.get("cache_hit_share"),
        "cache_hit_share_comparator": reference["cache_hit_share"],
        "packet_re_decodes_per_row": aggregate.get("packet_decodes_per_row"),
        "wall_seconds": arm_costs.get("generation_wall_seconds"),
        "slot_occupancy": arm_costs.get("slot_occupancy"),
        "mean_utilization_percent": arm_costs.get("mean_utilization_percent"),
        "parked_fraction": arm_costs.get("parked_fraction"),
        "projected_read_hours": efficiency["projected_test_read"]["rates"]["arm"][
            "test_read_hours"
        ],
        "projected_read_hours_comparator": reference["projected_read_hours_13078"],
        "join_is_a_measurement": efficiency["server_join"]["arm"]["join_quality"][
            "is_a_measurement"
        ],
        "join_exact_share": efficiency["server_join"]["arm"]["join_quality"]["exact_share"],
        "gpu_hours_decomposition": efficiency["gpu_hours_decomposition"],
        "cost_is_lower_than_the_base": (
            arm_costs.get("gpu_hours") is not None
            and arm_costs["gpu_hours"] < reference["gpu_hours_per_1080"]
        ),
    }

    arm_structural = {
        "tool_surface": structural["tool_surface"]["arm"],
        "trajectory": structural["trajectory"]["arm"],
        "dispositions": {
            "finite_completion_rows": structural["dispositions"]["arm"]["finite_stops"]["count"],
            "react_exhaustion_rows": structural["dispositions"]["arm"]["react_exhaustion_rows"],
            "planner_action_illegal_rows": structural["dispositions"]["arm"][
                "planner_action_illegal"]["count"],
            "rows_with_at_least_one_revise": structural["dispositions"]["arm"][
                "planner_routes"]["rows_with_at_least_one_revise"],
            "comparator": {
                "finite_completion_rows": structural["dispositions"]["comparator"][
                    "finite_stops"]["count"],
                "react_exhaustion_rows": structural["dispositions"]["comparator"][
                    "react_exhaustion_rows"],
                "planner_action_illegal_rows": structural["dispositions"]["comparator"][
                    "planner_action_illegal"]["count"],
                "rows_with_at_least_one_revise": structural["dispositions"]["comparator"][
                    "planner_routes"]["rows_with_at_least_one_revise"],
            },
            "registered_comparator": {
                "finite_completion_rows": reference["finite_completion_rows"],
                "react_exhaustion_rows": reference["react_exhaustion_rows"],
                "planner_action_illegal_rows": reference["planner_action_illegal_rows"],
                "revisions_executed": reference["revisions_executed"],
            },
        },
        "deliver_normaliser": {
            "one_receipt_per_row": structural["deliver_normaliser_receipts"]["arm"][
                "one_receipt_per_row"],
            "normaliser_id_counts": structural["deliver_normaliser_receipts"]["arm"][
                "normaliser_id_counts"],
            "rows_changed": structural["deliver_normaliser_receipts"]["arm"]["rows_changed"],
            "rows_label_changed": structural["deliver_normaliser_receipts"]["arm"][
                "rows_label_changed"],
            "rows_filler_changed": structural["deliver_normaliser_receipts"]["arm"][
                "rows_filler_changed"],
        },
        "slot_contracts_pin": structural["knowledge_store_pins"]["arm"][
            "knowledge_store_releases"].get("slot-contracts"),
        "comparator_slot_contracts_pin": structural["knowledge_store_pins"]["comparator"][
            "knowledge_store_releases"].get("slot-contracts"),
        "compaction": {
            "rows_compacted": structural["context_fit_compaction"]["arm"]["rows_compacted"],
            "contacts_compacted": structural["context_fit_compaction"]["arm"][
                "contacts_compacted"],
            "dropped_items": structural["context_fit_compaction"]["arm"]["dropped_items"],
            "agrees_with_the_flight_receipt": structural["context_fit_compaction"]["arm"][
                "agrees_with_the_flight_receipt"],
            "outcome_split": contrasts.get("compaction_outcome"),
        },
    }

    return {
        "status": status,
        "harmful_reasons": harmful,
        "guards": guards,
        "margins": {"h_slu_pp": cell.h_slu, "h_intent_pp": cell.h_intent,
                    "source": cell.registered["own_null_table"]["source"],
                    "reproduced": stop["own_null_reproduction"]["margins"]},
        "lock_statement": lock_statement,
        "lock_comparison": lock_comparison,
        "frontier_row": frontier["row"],
        "frontier_decision_75_triples": frontier["decision_75_triples"],
        "efficiency_headline": efficiency_headline,
        "structural_headline": arm_structural,
        "scenario_band": {
            name: {
                "scenarios_losing_beyond_the_band": block["scenarios_losing_beyond_the_band"],
                "decision_17_flagged_scenarios": block["decision_17_flagged_scenarios"],
            }
            for name, block in contrasts["band"].items()
        },
        "harness_admission_consequence": {
            "class": "none -- this cell decides no module",
            "key": None,
            "modules_already_decided": lock_statement["module_list"],
            "entry_is_written": False,
            "consequence": (
                "the plan arm decides no module: it is the LOCK EVIDENCE for the modules "
                "already decided (M1, M4b, M3, the RETIRED toolkit). No harness-admission row "
                "is written by this read. Once cell PLANr reproduces these numbers within the "
                "plan's own null, the coordinator writes the lock record, and that record "
                "supersedes docs/results/2026-09-20-slurp-v2-provisional-lock-v1.md."
            ),
            "receipt_owner": (
                "the coordinator writes the lock record from the sealed PLAN and PLANr "
                "verdicts; this read writes no row and edits no receipt"
            ),
        },
        "read_once": "read exactly once; no repeat-to-pass, no re-scoring, no second estimator",
    }


def stage_verdict(cell: Cell) -> None:
    stop = json.loads((cell.cache / "stop-raw.json").read_text(encoding="utf-8"))
    structural = json.loads((cell.cache / "structural-raw.json").read_text(encoding="utf-8"))
    contrasts = json.loads((cell.cache / "contrast-raw.json").read_text(encoding="utf-8"))
    lock = json.loads((cell.cache / "lock-raw.json").read_text(encoding="utf-8"))
    efficiency = json.loads((cell.cache / "efficiency-raw.json").read_text(encoding="utf-8"))
    frontier = json.loads((cell.cache / "frontier-raw.json").read_text(encoding="utf-8"))
    decision = _decision(cell, contrasts, structural, lock, efficiency, frontier, stop)

    cell.out.mkdir(parents=True, exist_ok=True)
    analysis_pkg = REPO / "src/speech_aware_evidence_acquisition/analysis"
    implementation = [
        {"path": str(p), "sha256": digest(p)}
        for p in (
            analysis_pkg / "paired.py",
            analysis_pkg / "bootstrap.py",
            analysis_pkg / "null_calibration.py",
            analysis_pkg / "null_calibration_cli.py",
            analysis_pkg / "deliver_normaliser_replay.py",
            REPO / "src/speech_aware_evidence_acquisition/reproduction/slurp_scoring.py",
            REPO / "src/speech_aware_evidence_acquisition/reproduction/slurp_official_eval.py",
            REPO / "src/speech_aware_evidence_acquisition/rails/delivery_normalisers.py",
            REPO / "src/speech_aware_evidence_acquisition/rails/slurp_projection_v3.py",
            REPO / "src/speech_aware_evidence_acquisition/rails/native_episode_config.py",
            REPO / "src/speech_aware_evidence_acquisition/rails/context_fit.py",
            REPO / "src/speech_aware_evidence_acquisition/core/scorers.py",
        )
        if p.exists()
    ]
    authority = [
        {"path": rel, "sha256": digest(REPO / rel)}
        for rel in cell.registered["authority_relpaths"]
        if (REPO / rel).exists()
    ]
    inputs = []
    for key in cell.runs:
        source = stop["sources"][key]
        inputs.append({"path": source["score_path"], "sha256": source["scores_sha256"],
                       "role": f"{key}: sealed official score"})
        inputs.append({"path": source["manifest_path"], "sha256": source["manifest_sha256"],
                       "role": f"{key}: sealed run manifest"})
        inputs.append({"path": str(cell.artifact(key, "outputs.jsonl")),
                       "sha256": source["outputs_sha256"],
                       "role": f"{key}: sealed per-row outputs"})
    for key in cell.flight_keys:
        inputs.append({"path": structural["phase_artifacts"][key]["path"],
                       "sha256": structural["phase_artifacts"][key]["sha256"],
                       "role": f"{key}: sealed phase artefact"})
        inputs.append({"path": str(cell.artifact(key, "trace.jsonl")),
                       "sha256": structural["trace_sha256"][key],
                       "role": f"{key}: sealed trace (streamed for digests and COST only)"})
        receipts = cell.run_dir(key) / "flight-receipts.json"
        inputs.append({"path": str(receipts), "sha256": digest(receipts),
                       "role": f"{key}: flight receipts"})
        baseline = structural["knowledge_store_pins"][key]["baseline_fragment_path"]
        inputs.append({"path": baseline,
                       "sha256": structural["knowledge_store_pins"][key][
                           "baseline_fragment_sha256"],
                       "role": f"{key}: sealed baseline config fragment"})
    inputs.append({"path": lock["on_outputs_path"], "sha256": lock["on_outputs_sha256"],
                   "role": "lock comparator: the normaliser-replayed copy written by this read"})
    inputs.append({"path": lock["on_scores_path"], "sha256": lock["on_scores_sha256"],
                   "role": "lock comparator: the node-applied official score written by this read"})
    inputs.append({"path": str(UMBRELLA_LOCK), "sha256": digest(UMBRELLA_LOCK),
                   "role": "the umbrella datasets lock the scorers resolve gold through"})
    for name in ("server.log", "monitor.jsonl", "session-receipt.json"):
        path = cell.session_dir / name
        if path.exists():
            inputs.append({
                "path": str(path),
                "sha256": digest(path) if name != "server.log" else None,
                "size_bytes": path.stat().st_size,
                "role": (
                    "the resident serving session, read read-only; server.log is still being "
                    "appended by later flights (this arm's replicate PLANr flew on the same "
                    "session), so its whole-file digest is not stable and is deliberately not "
                    "pinned -- the join is scoped to this flight's own contact window instead"
                ),
            })

    payload = {
        "recipe_id": cell.args.recipe_id,
        "driver": "plan_cell_read.py",
        "analysis_root": str(cell.out),
        "title": cell.args.title,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "execution_profile": "model-free-check",
        "contacts": {"model": 0, "tokenizer": 0, "encoder": 0, "asr": 0, "server": 0,
                     "scorer_official_on_a_sealed_manifest": 0,
                     "scorer_model_free_over_copies": 5},
        "population": stop["population"],
        "registered_aggregate_reproduction": stop["registered_aggregate_reproduction"],
        "own_null_reproduction": stop["own_null_reproduction"],
        "consistency_check": stop["consistency_check"],
        "row_counts": stop["row_counts"],
        "sources": stop["sources"],
        "package": stop["package"],
        "comparisons": contrasts["comparisons"],
        "band": contrasts["band"],
        "projection_v3": contrasts["projection_v3"],
        "projection_v3_contrasts": contrasts["projection_v3_contrasts"],
        "train_symmetric": contrasts["train_symmetric"],
        "train_symmetric_contrasts": contrasts["train_symmetric_contrasts"],
        "official_aggregates": contrasts["official_aggregates"],
        "structural": structural,
        "lock": lock,
        "frontier": frontier,
        "efficiency": efficiency,
        "decision": decision,
        "claim_boundary": (
            "Descriptive paired read on historically exposed TRAIN Fold A discovery rows, plus "
            "a cost measurement of the same flight. No superiority, generalization, "
            "component-causal, bar or confirmatory claim; no cross-carrier claim; no geometry "
            "claim. TRAIN Fold A is an exposed discovery roster and these are development "
            "numbers (owner decision 28): they are never compared with published TEST "
            "baselines."
        ),
        "authority": authority,
        "implementation": implementation,
        "inputs": inputs,
    }
    written = {}
    efficiency_doc = {"recipe_id": cell.args.recipe_id,
                      "headline": decision["efficiency_headline"], **efficiency}
    for name, content in (
        ("score-contrasts.json", payload),
        ("lock-comparison.json", {"recipe_id": cell.args.recipe_id,
                                  "decision_block": decision["lock_comparison"],
                                  "lock_statement": decision["lock_statement"],
                                  **lock}),
        ("frontier.json", {"recipe_id": cell.args.recipe_id, **frontier}),
        ("efficiency.json", efficiency_doc),
        ("throughput-tables.json", efficiency_doc),
        ("per-scenario-tables.json", {
            "recipe_id": cell.args.recipe_id,
            "natural_mixture_and_equal_scenario": {
                name: {
                    "pooled_slu_f1_per_scenario": block["pooled_micro"]["slu_f1_micro"][
                        "per_scenario"],
                    "pooled_slu_f1_equal_scenario_delta_pp": block["pooled_micro"][
                        "slu_f1_micro"]["equal_scenario_delta_pp"],
                    "pooled_span_f1_per_scenario": block["pooled_micro"]["span_f1_micro"][
                        "per_scenario"],
                    "per_row_metrics_per_scenario": {
                        metric: block["per_row"][metric]["per_scenario"]
                        for metric in PER_ROW_METRICS
                    },
                    "per_row_equal_scenario_delta_pp": {
                        metric: block["per_row"][metric]["equal_scenario_delta_pp"]
                        for metric in PER_ROW_METRICS
                    },
                }
                for name, block in list(contrasts["comparisons"].items())
                + list(lock["comparisons"].items())
            },
            "intent_band": contrasts["band"],
        }),
        ("structural.json", {"recipe_id": cell.args.recipe_id, **structural}),
        ("compaction.json", {
            "recipe_id": cell.args.recipe_id,
            "item": "E20 context_fit_policy = compact-or-abstain",
            "arm": structural["context_fit_compaction"]["arm"],
            "comparator": structural["context_fit_compaction"]["comparator"],
            "outcome_split": contrasts.get("compaction_outcome"),
        }),
    ):
        path = cell.out / name
        path.write_text(json.dumps(content, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written[name] = digest(path)
        print(name, written[name])

    script = Path(__file__).resolve()
    copied = cell.out / script.name
    if copied.resolve() != script:
        shutil.copyfile(script, copied)
    written[script.name] = digest(copied)

    readme = cell.out / "README.md"
    readme.write_text(_readme(cell, payload, written), encoding="utf-8")
    print("README.md", digest(readme))
    print("STATUS", decision["status"])


def _fmt(value, digits=2, dash="--"):
    if value is None:
        return dash
    if isinstance(value, bool):
        return "yes" if value else "no"
    return f"{value:,.{digits}f}"


def _readme(cell: Cell, payload: dict, written: dict) -> str:
    decision = payload["decision"]
    slu = decision["guards"]["official_pooled_slu_f1"]
    intent = decision["guards"]["intent_accuracy"]
    eff = decision["efficiency_headline"]
    lock = decision["lock_comparison"]["comparisons"]
    frontier = decision["frontier_row"]
    compaction = decision["structural_headline"]["compaction"]
    common = [
        f"    --arm-run {cell.runs['arm']['run_id']} \\",
        f"    --arm-attempt {cell.runs['arm']['attempt_id']} \\",
        f"    --arm-fit-run {cell.runs['arm']['fit_run_id']} \\",
        f"    --comparator-run {cell.runs['comparator']['run_id']} \\",
        f"    --comparator-attempt {cell.runs['comparator']['attempt_id']} \\",
        f"    --lock-run {cell.runs['lock']['run_id']} \\",
        f"    --lock-attempt {cell.runs['lock']['attempt_id']} \\",
        f"    --package-dir {cell.package} \\",
        f"    --h-slu {cell.h_slu} --h-intent {cell.h_intent} \\",
        f"    --normaliser-id {cell.normaliser_id} \\",
        f"    --analysis-root {cell.out}",
    ]
    lines = [
        f"# {payload['title']}",
        "",
        f"Status: **{decision['status']}**. Generated {payload['generated_at_utc']} by "
        f"`plan_cell_read.py` (sha256 `{written['plan_cell_read.py']}`), "
        "execution profile `model-free-check`, zero model / tokenizer / encoder / ASR / "
        "server contacts. Development numbers on TRAIN Fold A (owner decision 28).",
        "",
        "## Re-running every stage",
        "",
        "The stages must run in this order: `efficiency` feeds `frontier`, and `verdict` reads",
        "every cache.",
        "",
        "```bash",
        "PY=/home/chao/.venvs/speechrl/bin/python",
        "export PYTHONDONTWRITEBYTECODE=1",
        f"export PYTHONPATH={REPO}/src",
        f"export SPEECHRL_DATA_DIR={DATA}",
        f"cd {cell.out}",
        "for stage in stop structural contrast lock efficiency frontier verdict; do",
        "  $PY plan_cell_read.py --stage $stage \\",
    ] + common + [
        "done",
        "```",
        "",
        "Every number this README and the verdict quote is produced by one of these stages.",
        "",
        "| stage | what it produces | re-run |",
        "| --- | --- | --- |",
        "| `stop` | the sealed-byte verification, the roster block, the registered comparator "
        "AND lock-comparator aggregates and the own-null margin reproduction | "
        "`--stage stop` |",
        "| `structural` | the tool surface, the trajectory, the dispositions, the "
        "deliver_normaliser receipts, the E20 compaction receipts, the knowledge-store pins "
        "and the Perception key delta -> `structural.json`, `compaction.json` | "
        "`--stage structural` |",
        "| `contrast` | the paired official / v3 / symmetric contrasts, the per-scenario "
        "tables and the intent band -> `score-contrasts.json`, `per-scenario-tables.json` | "
        "`--stage contrast` |",
        "| `lock` | the normaliser replay over a copy of the lock comparator, its node-applied "
        "official score and the two paired lock contrasts -> `lock-comparison.json` | "
        "`--stage lock` |",
        "| `efficiency` | the server.log join, the cost block, the fit block and the GPU-hour "
        "decomposition -> `efficiency.json` / `throughput-tables.json` | `--stage efficiency` |",
        "| `frontier` | the decision-75 frontier row and the two Pareto planes -> "
        "`frontier.json` | `--stage frontier` |",
        "| `verdict` | the decision block, every deliverable and this README | "
        "`--stage verdict` |",
        "",
        "## Headline (gating, against the sealed tool-free base)",
        "",
        "| metric | comparator | arm | delta pp | CI95 | margin | guard |",
        "| --- | ---: | ---: | ---: | --- | ---: | --- |",
        f"| official pooled SLU-F1 | {_fmt(slu['comparator_pct'], 4)} | "
        f"{_fmt(slu['arm_pct'], 4)} | {slu['delta_pp']:+.4f} | "
        f"[{slu['ci95_pp'][0]:+.4f}, {slu['ci95_pp'][1]:+.4f}] | {cell.h_slu} | "
        f"{'non-inferior' if slu['ci95_lower_exceeds_minus_h'] else 'FAILS'} |",
        f"| intent accuracy | {_fmt(intent['comparator_pct'], 4)} | "
        f"{_fmt(intent['arm_pct'], 4)} | {intent['delta_pp']:+.4f} | "
        f"[{intent['ci95_pp'][0]:+.4f}, {intent['ci95_pp'][1]:+.4f}] | {cell.h_intent} | "
        f"{'non-inferior' if intent['ci95_lower_exceeds_minus_h'] else 'FAILS'} |",
        "",
        "## Lock comparison (reported, never a gate)",
        "",
        "| lock side | its SLU / intent | arm SLU / intent | SLU delta | CI95 | intent delta "
        "| CI95 |",
        "| --- | ---: | ---: | ---: | --- | ---: | --- |",
    ]
    for name, title in (
        ("arm_vs_lock_official", "B5e official"),
        ("arm_vs_lock_node_applied", "B5e + normaliser node (the provisional lock)"),
    ):
        block = lock[name]
        lines.append(
            f"| {title} | {_fmt(block['lock_side_slu_pct'], 4)} / "
            f"{_fmt(block['lock_side_intent_pct'], 4)} | "
            f"{_fmt(block['arm_slu_pct'], 4)} / {_fmt(block['arm_intent_pct'], 4)} | "
            f"{block['slu_delta_pp']:+.4f} | "
            f"[{block['slu_ci95_pp'][0]:+.4f}, {block['slu_ci95_pp'][1]:+.4f}] | "
            f"{block['intent_delta_pp']:+.4f} | "
            f"[{block['intent_ci95_pp'][0]:+.4f}, {block['intent_ci95_pp'][1]:+.4f}] |"
        )
    lines += [
        "",
        "## Frontier row (owner decision 75)",
        "",
        "| cell | official SLU | official intent | GPU-h / 1,080 | contacts / row | "
        "prefilled tok / row | basis |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
        f"| PLAN | {_fmt(frontier['official_slu'], 4)} | "
        f"{_fmt(frontier['official_intent'], 4)} | "
        f"{_fmt(frontier['gpu_hours_per_1080'], 4)} | "
        f"{_fmt(frontier['contacts_per_row'], 4)} | "
        f"{_fmt(frontier['prefilled_tokens_per_row'], 1)} | {frontier['token_basis']} |",
    ]
    for item in payload["frontier"]["registered_rows"]:
        lines.append(
            f"| {item['cell']} (registered) | {_fmt(item['official_slu'], 2)} | "
            f"{_fmt(item['official_intent'], 2)} | "
            f"{_fmt(item['gpu_hours_per_1080'], 4)} | "
            f"{_fmt(item['contacts_per_row'], 3)} | "
            f"{_fmt(item['prefilled_tokens_per_row'], 1)} | {item['token_basis']} |"
        )
    lines += [
        "",
        payload["frontier"]["tool_note"],
        "",
        "## E20 compaction (mandatory diagnostic)",
        "",
        f"Rows compacted: **{compaction['rows_compacted']}**; contacts compacted: "
        f"**{compaction['contacts_compacted']}**; droppable items dropped: "
        f"**{len(compaction['dropped_items'])}** distinct kinds. Agrees with the flight "
        f"receipt: {_fmt(compaction['agrees_with_the_flight_receipt'])}.",
        "",
        "## Efficiency",
        "",
        "| number | arm | comparator |",
        "| --- | ---: | ---: |",
        f"| prefilled tokens per row | {_fmt(eff['prefilled_tokens_per_row'], 1)} | "
        f"{_fmt(eff['prefilled_tokens_per_row_comparator'], 1)} |",
        f"| GPU hours per 1,080 rows | {_fmt(eff['gpu_hours_per_1080'], 4)} | "
        f"{_fmt(eff['gpu_hours_per_1080_comparator'], 4)} |",
        f"| contacts per minute | {_fmt(eff['contacts_per_minute'], 2)} | "
        f"{_fmt(eff['contacts_per_minute_comparator'], 2)} |",
        f"| contacts per row | {_fmt(eff['contacts_per_row'], 4)} | "
        f"{_fmt(eff['contacts_per_row_comparator'], 4)} |",
        f"| cache hit share | {_fmt(eff['cache_hit_share'], 4)} | "
        f"{_fmt(eff['cache_hit_share_comparator'], 4)} |",
        f"| projected {cell.test_read_rows}-row read hours | "
        f"{_fmt(eff['projected_read_hours'], 3)} | "
        f"{_fmt(eff['projected_read_hours_comparator'], 3)} |",
        "",
        "## Files",
        "",
        "| file | sha256 |",
        "| --- | --- |",
    ]
    for name in sorted(written):
        lines.append(f"| `{name}` | `{written[name]}` |")
    lines += [
        "",
        "## Inputs",
        "",
        "| path | sha256 | role |",
        "| --- | --- | --- |",
    ]
    for item in payload["inputs"]:
        lines.append(
            f"| `{item['path']}` | `{item.get('sha256') or 'not pinned'}` | {item['role']} |"
        )
    lines += [
        "",
        "## Claim boundary",
        "",
        payload["claim_boundary"],
        "",
    ]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True,
                        choices=("stop", "structural", "contrast", "lock", "frontier",
                                 "efficiency", "verdict"))
    parser.add_argument("--arm-run", required=True)
    parser.add_argument("--arm-attempt", required=True)
    parser.add_argument("--arm-fit-run", default=None)
    parser.add_argument("--arm-label", default="the default-plan arm")
    parser.add_argument("--comparator-run", required=True)
    parser.add_argument("--comparator-attempt", required=True)
    parser.add_argument("--comparator-fit-run", default=None)
    parser.add_argument("--comparator-label", default="the sealed tool-free base")
    parser.add_argument("--lock-run", required=True)
    parser.add_argument("--lock-attempt", required=True)
    parser.add_argument("--lock-label", default="the provisional lock arm B5e")
    parser.add_argument("--normaliser-id", default="saea-deliver-normalise-v3")
    parser.add_argument("--own-null-left-run",
                        default="SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-RECOVERY-V2")
    parser.add_argument(
        "--own-null-left-attempt",
        default="attempt-slurp-native-exemplars-k20-anchor-train-fold-a-generation-recovery-v2")
    parser.add_argument("--own-null-left-label", default="the sealed B1 arm")
    parser.add_argument("--own-null-right-run",
                        default="SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-REPLICATE-V1")
    parser.add_argument(
        "--own-null-right-attempt",
        default="attempt-slurp-native-exemplars-k20-anchor-replicate-train-fold-a-generation-v1")
    parser.add_argument("--own-null-right-label", default="cell B1r")
    parser.add_argument("--package-dir", required=True)
    parser.add_argument("--h-slu", type=float, required=True)
    parser.add_argument("--h-intent", type=float, required=True)
    parser.add_argument("--analysis-root", required=True)
    parser.add_argument("--cache-dir", default=None)
    parser.add_argument("--registered", default=None)
    parser.add_argument("--roster", default="docs/receipts/rosters/slurp-evo-fold-a-v2.json")
    parser.add_argument(
        "--roster-metadata",
        default=("analysis/SAEA-SLURP-TRAIN-A-DIRECT-ANCHOR-RELEASE-PAIRED-ANALYSIS-V1/"
                 "roster-metadata.json"))
    parser.add_argument(
        "--split-identity-hash",
        default="61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6")
    parser.add_argument(
        "--serving-session-dir",
        default=str(DATA / "serving/serving-slurp-native-candidate-five-train-a-np4-v1"))
    parser.add_argument("--rows", type=int, default=1080)
    parser.add_argument("--seed", type=int, default=20260915)
    parser.add_argument("--draws", type=int, default=10000)
    parser.add_argument("--test-read-rows", type=int, default=13078)
    parser.add_argument("--recipe-id", default="slurp-default-plan-lock-paired-analysis-v1")
    parser.add_argument(
        "--title",
        default=("SLURP TRAIN A: cell PLAN, the default plan flown as one arm on the tool-free "
                 "B1 base (the v2.0 lock evidence) -- paired read against the sealed B1-notool "
                 "arm at cell B1r's own-null margins, the lock comparison and the frontier row"))
    args = parser.parse_args()
    cell = Cell(args)
    cell.cache.mkdir(parents=True, exist_ok=True)
    cell.copies.mkdir(parents=True, exist_ok=True)
    {
        "stop": stage_stop,
        "structural": stage_structural,
        "contrast": stage_contrast,
        "lock": stage_lock,
        "efficiency": stage_efficiency,
        "frontier": stage_frontier,
        "verdict": stage_verdict,
    }[args.stage](cell)


if __name__ == "__main__":
    main()
