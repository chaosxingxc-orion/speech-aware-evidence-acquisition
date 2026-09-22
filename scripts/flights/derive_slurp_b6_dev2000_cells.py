#!/usr/bin/env python3
"""Idempotent generator for cell B6 (SLURP direct-vs-plan paired read on the
fresh DEV-2000-ADDED roster; owner decisions 34, 35, 78, 79, 86, 88).

MODEL-FREE. Profile ``model-free-check``. Derives, by string/JSON edit of two
already-sealed precedents, every registration artefact this cell needs:

* the direct arm's baseline + experiment fragment, from the sealed
  ``slurp-direct-max512-dev1000-base-replication-v1`` pair (DEV-1000);
* the plan arm's baseline + experiment fragment, from the sealed
  ``slurp-native-default-plan-lock-*`` pair (cell PLAN, TRAIN Fold A);
* the readiness package under
  ``docs/readiness/2026-09-22-slurp-b6-dev2000-added-v1/`` (generation + fit
  plans, fresh and ``-registered``, for both arms; the protocol document; the
  analysis recipe; the README) and the sibling preregistration note;
* the five new ``docs/exposure-ledger.md`` rows this registration needs.

Every composed/protocol hash embedded in the readiness package is computed
live through ``core.config.compose`` / ``core.config.protocol_hash`` over the
fragments this script itself writes -- never hand-typed -- so a re-run after
``scripts/flights/repin_cell.py`` changes those fragments reproduces the same
values from the same bytes.

Idempotent: re-running with no intervening edits is a no-op (every target
file's freshly generated content is byte-identical to what is already on
disk). Refuses to overwrite a config/readiness file whose on-disk content
differs from what this run would produce (no silent overwrite), and refuses
to touch any exposure-ledger row already marked ``consumed = yes``.

Writes nothing under ``$SPEECHRL_DATA_DIR``: the two arms' registrations pin
the query-content derivative that
``scripts/build_slurp_query_content_derivative.py`` already produced at
``vectors/slurp-dev2000-added-v1/query-vectors-speech-content-v1.jsonl``
(item 1), and no ``prepared_phase_supply`` artefact -- the plan arm's own
first-phase Perception supply is left for ``scripts/flights/repin_cell.py``
to build model-free at flip time, exactly as that tool's own
``_set_preparation_requirement`` fallback documents for "a cell registered
before its supply could be prepared".

Usage::

    python scripts/flights/derive_slurp_b6_dev2000_cells.py
    python scripts/flights/derive_slurp_b6_dev2000_cells.py --check   # dry run, write nothing
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.config import (  # noqa: E402
    compose,
    protocol_hash as compute_protocol_hash,
)

# ---------------------------------------------------------------------------
# Fixed identity: bindings the task hands down, verified against real bytes
# below when $SPEECHRL_DATA_DIR is reachable.
# ---------------------------------------------------------------------------

DATASET_FRAGMENT = "slurp-speech-native-dev2000-added"
SPLIT_NAME = "DEV-2000-ADDED"
SPLIT_IDENTITY_HASH = "ee6c43cd4dd8fc2a583d2dd053e799c2d002efa3755fcd092ba7c7565431bf67"
ROSTER_RELPATH_REPO = "docs/receipts/rosters/slurp-dev-2000-added-v1.json"
ROSTER_SHA256 = "f78dd8ad2894b1fd02bfe6050e39e3fb2c5d178a649e5d20e85ea4ecf4b8dc58"
ROW_COUNT = 1000
TOTAL_AUDIO_SECONDS = 2983.527  # docs/receipts/rosters/slurp-dev-2000-added-v1.json / dataset fragment
DIRECT_AUDIO_CEIL = 2984
PLAN_AUDIO_CEIL = 32819  # ceil(2983.527 * 11)
MODEL_FRAGMENT = "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1"

PACKET_PROMOTION_RECEIPT = "/home/chao/feat-cache/slurp-q4km-packets-04ccc72a/DEV-2000-ADDED-promotion.json"
PACKET_PROMOTION_SHA256 = "978fc63888b99fa73ec5ca51ebb03676cb853f052125212f48326e213cf35091"

INTENT_BOUNDARY_QUERY_RELPATH = "vectors/slurp-dev2000-added-v1/query-vectors-speech-segments.jsonl"
INTENT_BOUNDARY_QUERY_SHA256 = "e2a5fd046dac7c87fcf53830955e41e69d20402a2305a02ebf2bfc1a33001b9d"

CONTENT_QUERY_RELPATH = "vectors/slurp-dev2000-added-v1/query-vectors-speech-content-v1.jsonl"
CONTENT_QUERY_SHA256 = "7d4ebdce553fd897fa86cc6b6d878ebf2298e19ee509eeceaf1aa0aca4855ee0"

TOOL_CONTACT_LEDGER_ROW = "SAEA-SLURP-DEV2000-ADDED-SPEECH-QUERY-ENCODING-V1"

ALIAS_RECEIPT_RELPATH_DATA = "prepared/SAEA-SLURP-DEV2000-ADDED-ALIAS-V1/query-dimension-alias.json"
ALIAS_RECEIPT_SHA256 = "9d41262d18b7dc524807e36fb1d97b859f43920524a6dfe85f1bead2b07a5768"
OLD_ALIAS_RELPATH_DATA = "prepared/SAEA-SLURP-INTENT-BOUNDARY-TRAIN-FOLD-A-ALIAS-V1/query-dimension-alias.json"

ENCODING_RECEIPT_RELPATH_DATA = (
    "preparation-runs/SAEA-SLURP-DEV2000-ADDED-SPEECH-QUERY-ENCODING-V1/encode-v1/receipt.json"
)
ENCODING_RECEIPT_SHA256 = "9c2b6cdcb17ca3b1ad35b599217ca4e7d84f3c7e5a5d55056bdbf7d92fc9dc9d"

DECISION_ID = "slurp-b6-dev2000-added-admission-v1"
DECISION_RELPATH = "coordination/slurp-b6-dev2000-added-v1/root-admission-v1.json"
PLACEHOLDER_SHA256 = "0" * 64

REGISTERED_AT_UTC = "2026-09-22T12:00:00.000000+00:00"
REGISTRATION_DATE = "2026-09-22"
SOURCE_TREE = (
    "studies/speech-aware-evidence-acquisition, worktree /home/chao/saea-worktrees/fable-b6, branch fable/b6"
)

# ---------------------------------------------------------------------------
# Names.
# ---------------------------------------------------------------------------

DIRECT_BASELINE_PRECEDENT = "slurp-direct-max512-dev1000-base-replication-v1"
DIRECT_EXPERIMENT_PRECEDENT = "slurp-direct-max512-dev1000-base-replication-v1"
PLAN_BASELINE_PRECEDENT = "slurp-native-default-plan-lock-baseline-v1"
PLAN_EXPERIMENT_PRECEDENT = "slurp-native-default-plan-lock-v1"

DIRECT_BASELINE_NAME = "slurp-direct-max512-dev2000-added-v1"
DIRECT_EXPERIMENT_NAME = "slurp-direct-max512-dev2000-added-v1"
PLAN_BASELINE_NAME = "slurp-native-default-plan-dev2000-added-baseline-v1"
PLAN_EXPERIMENT_NAME = "slurp-native-default-plan-dev2000-added-v1"

DIRECT_RUN_ID = "SAEA-SLURP-DIRECT-MAX512-DEV2000-ADDED-V1"
DIRECT_FIT_RUN_ID = "SAEA-SLURP-DIRECT-MAX512-DEV2000-ADDED-FIT-V1"
PLAN_RUN_ID = "SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1"
PLAN_FIT_RUN_ID = "SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-FIT-V1"
ANALYSIS_RUN_ID = "SAEA-SLURP-B6-DEV2000-ADDED-PAIRED-ANALYSIS-V1"

DIRECT_GEN_ATTEMPT = "attempt-slurp-direct-max512-dev2000-added-generation-v1"
DIRECT_FIT_ATTEMPT = "attempt-slurp-direct-max512-dev2000-added-fit-v1"
PLAN_GEN_ATTEMPT = "attempt-slurp-native-default-plan-dev2000-added-generation-v1"
PLAN_FIT_ATTEMPT = "attempt-slurp-native-default-plan-dev2000-added-fit-v1"

READINESS_DIR = REPO_ROOT / "docs" / "readiness" / "2026-09-22-slurp-b6-dev2000-added-v1"
PREREG_PATH = REPO_ROOT / "docs" / "readiness" / "2026-09-22-slurp-b6-dev2000-added-v1-preregistration.md"
LEDGER_PATH = REPO_ROOT / "docs" / "exposure-ledger.md"
BASELINE_DIR = REPO_ROOT / "configs" / "baseline"
EXPERIMENT_DIR = REPO_ROOT / "configs" / "experiment"

PROTOCOL_DOC_NAME = "protocol-registered-v1.json"
ANALYSIS_RECIPE_NAME = "analysis-recipe-v1.json"

DIRECT_MODULES_KEY = "TOTAL_AUDIO_SECONDS placeholder"  # unused, kept out of hashed docs

DEV1000_ANALYSIS_RECIPE_RELPATH = (
    "docs/readiness/2026-09-14-slurp-direct-vs-native-dual-store-base-replication-analysis-recipe-v1.json"
)

_VERIFY_BINDINGS = (
    (INTENT_BOUNDARY_QUERY_RELPATH, INTENT_BOUNDARY_QUERY_SHA256),
    (CONTENT_QUERY_RELPATH, CONTENT_QUERY_SHA256),
    (ALIAS_RECEIPT_RELPATH_DATA, ALIAS_RECEIPT_SHA256),
    (ENCODING_RECEIPT_RELPATH_DATA, ENCODING_RECEIPT_SHA256),
)


class DeriveError(RuntimeError):
    pass


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical(document: object) -> str:
    return json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def verify_bindings() -> None:
    """Re-hash every data-root binding this registration pins, when
    ``$SPEECHRL_DATA_DIR`` is reachable, instead of trusting hand-typed
    constants -- item 6(e)'s proof discipline applied at generation time."""

    raw = os.environ.get("SPEECHRL_DATA_DIR", "").strip()
    if not raw or not Path(raw).is_dir():
        print("SPEECHRL_DATA_DIR not reachable; skipping live binding verification", file=sys.stderr)
        return
    root = Path(raw)
    for relpath, expected in _VERIFY_BINDINGS:
        path = root / relpath
        if not path.is_file():
            raise DeriveError(f"binding file missing on data root: {relpath}")
        measured = _sha256_file(path)
        if measured != expected:
            raise DeriveError(f"{relpath} hashes to {measured}, not the pinned {expected}")
    roster_path = REPO_ROOT / ROSTER_RELPATH_REPO
    if not roster_path.is_file():
        raise DeriveError(f"roster receipt missing in-repo: {ROSTER_RELPATH_REPO}")
    if _sha256_file(roster_path) != ROSTER_SHA256:
        raise DeriveError(f"{ROSTER_RELPATH_REPO} does not hash to the pinned {ROSTER_SHA256}")


def _write_if_needed(path: Path, content: str, *, check: bool) -> str:
    """Write ``content`` to ``path`` unless it is already there byte for
    byte; refuse to overwrite differing content. Returns 'written',
    'unchanged' or 'would-write'."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        existing = path.read_text(encoding="utf-8")
        if existing == content:
            return "unchanged"
        raise DeriveError(
            f"refusing to overwrite {path}: on-disk content differs from the freshly generated content"
        )
    if check:
        return "would-write"
    path.write_text(content, encoding="utf-8", newline="\n")
    return "written"


def _load_baseline(name: str) -> dict:
    return json.loads((BASELINE_DIR / f"{name}.json").read_text(encoding="utf-8"))


def _load_experiment(name: str) -> dict:
    return json.loads((EXPERIMENT_DIR / f"{name}.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Direct arm.
# ---------------------------------------------------------------------------

DIRECT_WHAT_THIS_IS = (
    "Cell B6 direct arm (owner decisions 34, 35, 78, 79, 86, 88): the sealed slurp-direct-max512 form, "
    "unmodified in method, flown on the fresh DEV-2000-ADDED roster (1,000 rows, split identity "
    f"{SPLIT_IDENTITY_HASH}) instead of DEV-1000. Send one direct-only task request per existing "
    "DEV-2000-ADDED sample through the shared controller, FlightRuntime and OpenJiuwen executor, "
    "retaining all 60 legal labels and the same max512 geometry, frozen weights, promoted speech "
    "packets and prompts as the sealed DEV-1000 and TRAIN Fold A direct forms. No retrieved knowledge, "
    "intermediate candidate state or analytical tools enter this direct arm. This is a fresh-roster "
    "generalisation read of an already-sealed method, not a new form: no smoke is registered because "
    "the form has already been flown twice (DEV-1000 and TRAIN Fold A) and left no open form question. "
    "Any second failure closes this generation flight."
)


def build_direct_baseline() -> dict:
    doc = _load_baseline(DIRECT_BASELINE_PRECEDENT)
    doc["live_phase_fit"]["attempt_id"] = DIRECT_FIT_ATTEMPT
    doc["live_phase_fit"]["run_id"] = DIRECT_FIT_RUN_ID
    doc["speech_packet_promotion_receipt"] = PACKET_PROMOTION_RECEIPT
    doc["speech_packet_promotion_receipt_sha256"] = PACKET_PROMOTION_SHA256
    doc["what_this_is"] = DIRECT_WHAT_THIS_IS
    return doc


def build_direct_experiment(analysis_recipe_sha256: str) -> dict:
    doc = _load_experiment(DIRECT_EXPERIMENT_PRECEDENT)
    doc["analysis_recipe"] = {
        "repo_relpath": f"docs/readiness/2026-09-22-slurp-b6-dev2000-added-v1/{ANALYSIS_RECIPE_NAME}",
        "sha256": analysis_recipe_sha256,
    }
    cell = doc["cells"][0]
    cell["attempt_id"] = DIRECT_GEN_ATTEMPT
    cell["baseline_fragment"] = DIRECT_BASELINE_NAME
    cell["cell_id"] = DIRECT_EXPERIMENT_NAME
    cell["dataset_fragment"] = DATASET_FRAGMENT
    cell["run_id"] = DIRECT_RUN_ID
    cell["readiness"] = {
        "reason": (
            "Cell B6 direct arm: the sealed slurp-direct-max512 form flown unmodified on the fresh "
            "DEV-2000-ADDED roster (owner decisions 34, 35, 78, 79, 86, 88), registered before contact "
            f"on {REGISTRATION_DATE} from the sealed DEV-1000 base-replication registration by script "
            "(scripts/flights/derive_slurp_b6_dev2000_cells.py). Held pending the coordinator's root "
            "admission decision and scripts/flights/repin_cell.py."
        ),
        "requirements": [
            {
                "kind": "decision",
                "expected_decision_id": DECISION_ID,
                "relpath": DECISION_RELPATH,
                "sha256": PLACEHOLDER_SHA256,
                "reason": (
                    "Root B6 admission (placeholder sha256 of 64 zeros: the coordinator mints this "
                    "receipt on the data root after merge and scripts/flights/repin_cell.py re-pins the "
                    "real hash; see the package README)."
                ),
            }
        ],
        "state": "held",
    }
    doc["date"] = REGISTRATION_DATE
    doc["execution_plan"] = {
        "execution_profile": "bounded-discovery-probe",
        "planned_gpu_hours": 1.0,
        "planned_model_calls": ROW_COUNT,
        "planned_speech_audio_seconds": DIRECT_AUDIO_CEIL,
        "split_role": "dev",
    }
    doc["experiment_id"] = DIRECT_RUN_ID
    doc["failure_policy"] = (
        "Stop and preserve on any failure. This fresh-roster generalisation read is not a replay of a "
        "closed attempt. At most one named recovery may be registered; a second failure closes this "
        "flight. Do not alter caps, prompts, methods or geometry during an attempt."
    )
    doc["population"] = {
        "count": ROW_COUNT,
        "dataset_fragment": DATASET_FRAGMENT,
        "decision_population": (
            "The fresh DEV-2000-ADDED roster (1,000 rows never before flown for generation; the roster's "
            "audio was previously contact-only for the model-free speech-query encoding pass that built "
            "this cell's own query vectors, docs/receipts/rosters/slurp-dev-2000-added-v1.json). Keep all "
            "rows and actual candidate widths."
        ),
        "split_identity_hash": SPLIT_IDENTITY_HASH,
    }
    doc["purpose"] = (
        "Read the sealed slurp-direct-max512 form against the sealed default-plan system arm (cell B6 "
        "plan arm, this same package) on the identical fresh DEV-2000-ADDED roster: a paired, "
        "report-only generalisation read of the locked v2.0 plan against the bare frozen core, not a "
        "new admission decision."
    )
    doc["service_session"] = "serving-slurp-dual-store-base-replication-np4-v1"
    doc["split_id"] = SPLIT_NAME
    return doc


# ---------------------------------------------------------------------------
# Plan arm.
# ---------------------------------------------------------------------------

PLAN_WHAT_THIS_IS = (
    "Cell B6 plan arm (owner decisions 34, 35, 78, 79, 86, 88): the locked v2.0 default plan (cell PLAN's "
    "fragment: the sealed B1-notool base plus slot-contracts v2, deliver_normaliser v3 and the "
    "review-loop marker 'on') flown unmodified on the fresh DEV-2000-ADDED roster (1,000 rows, split "
    f"identity {SPLIT_IDENTITY_HASH}) instead of TRAIN Fold A. Only the roster-bound bindings move: the "
    "dataset fragment, the promoted speech packets, the two row-side query_source pins (both stores' "
    "query vectors are this roster's own, built model-free by "
    "scripts/build_slurp_query_content_derivative.py for the content dimension and by the prior "
    "DEV-2000-ADDED speech-query encoding pass for the intent-boundary dimension), the "
    "preparation_source_receipts, the devel-gold scorer and the per-flight ids. The native_episode "
    "block, phase_material, policy, all three knowledge-store releases/snapshots, the geometry and the "
    "E13/E20/E22 declarations stay byte-identical to cell PLAN. This is a fresh-roster generalisation "
    "read of an already-locked plan, not a new form: no smoke is registered because the form has "
    "already been flown on TRAIN Fold A (cell PLAN) and left no open form question. Any second failure "
    "closes this generation flight. Neither this baseline nor cell B6's readiness requirements carry a "
    "prepared_phase_supply pin: this cell's own first-phase Perception supply is built model-free by "
    "scripts/flights/repin_cell.py at flip time, so this registration writes nothing under "
    "$SPEECHRL_DATA_DIR beyond the query-content derivative of item 1."
)

WHAT_THE_TRAIN_EXEMPLARS_STORE_IS_DEV2000 = (
    "SLURP v2 base program module M1 / cell B1, read unmodified on the fresh DEV-2000-ADDED roster: the "
    "top-20 TRAIN construction-pool exemplars (excluding every utterance with a recording in TRAIN Fold "
    "A, Fold B or DEV-1000; 9,354-facet pool) recalled by cosine against this row's OWN sealed "
    "DEV-2000-ADDED speech vector, ranked by saea-rank-wcos-prior-agree-v1 (identity on cosine: w_cos=1, "
    "w_prior=0, w_agree=0) and passed through saea-fuse-supplyfilter-v1 with m=c=top_l=20 -- twenty in, "
    "twenty out on every row, the same 'no coverage reshaping' discipline cell KU-S3 established. Each "
    "value renders as '<utterance> | <scenario>_<action> | type=filler; ...' (KB view "
    "annotated-exemplars, scripts/build_knowledge_snapshot.py). The decision is delivered to the SOLVER "
    "phase (the program's LAST phase) through the E6 acquire transition, exactly as on TRAIN Fold A; the "
    "Solver's instruction bytes are byte-identical to the unmodified cell PLAN's. The composed acquire "
    "transition also carries the slot-contracts store's own candidate_supply.solver decision on the same "
    "wave; both compose into one PhaseSupply via rails.knowledge_stores._compose_supplies."
)


def build_plan_baseline() -> dict:
    doc = _load_baseline(PLAN_BASELINE_PRECEDENT)

    ib_qs = doc["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]["query_source"]
    ib_qs["embedded_signal"] = (
        "speech: complete original DEV-2000-ADDED recordings represented by sealed full-utterance "
        "segments in the intent-boundary retrieval dimension; segment identities are preserved and no "
        "flattening, re-encoding, transcript, answer or future turn enters this query."
    )
    ib_qs["relpath"] = INTENT_BOUNDARY_QUERY_RELPATH
    ib_qs["sha256"] = INTENT_BOUNDARY_QUERY_SHA256
    ib_qs["tool_contact_ledger_row"] = TOOL_CONTACT_LEDGER_ROW

    te_qs = doc["knowledge_stores"]["train-exemplars"]["phase_supply"]["solver"]["query_source"]
    te_qs["embedded_signal"] = (
        "speech: complete original DEV-2000-ADDED recordings represented by the sealed full-utterance "
        "speech vector of the row's own recording, in the content retrieval dimension; flattened from "
        "the sealed intent-boundary full-utterance SEGMENT vectors "
        "(vectors/slurp-dev2000-added-v1/query-vectors-speech-content-v1.provenance.json -- one segment "
        "per row, dimension renamed intent-boundary to content, every float byte-identical to the "
        "parent) because docs/results/2026-09-17-slurp-a2-exemplar-headroom-audit-v1.md establishes "
        "intent-boundary as an alias of the content embedding space; no flattening of MEANING, "
        "re-encoding, transcript, answer or future turn enters this query."
    )
    te_qs["relpath"] = CONTENT_QUERY_RELPATH
    te_qs["sha256"] = CONTENT_QUERY_SHA256
    te_qs["tool_contact_ledger_row"] = TOOL_CONTACT_LEDGER_ROW

    doc["native_contact_fit"]["attempt_id"] = PLAN_FIT_ATTEMPT
    doc["native_contact_fit"]["run_id"] = PLAN_FIT_RUN_ID
    doc["native_contact_fit"]["contact_cap"] = ROW_COUNT * 11 * 4

    receipts = []
    for receipt in doc["preparation_source_receipts"]:
        if receipt.get("relpath") == OLD_ALIAS_RELPATH_DATA:
            receipts.append({"relpath": ALIAS_RECEIPT_RELPATH_DATA, "root": "data", "sha256": ALIAS_RECEIPT_SHA256})
        else:
            receipts.append(receipt)
    receipts.append({"relpath": ENCODING_RECEIPT_RELPATH_DATA, "root": "data", "sha256": ENCODING_RECEIPT_SHA256})
    receipts.append({"relpath": ROSTER_RELPATH_REPO, "root": "repository", "sha256": ROSTER_SHA256})
    doc["preparation_source_receipts"] = receipts

    doc["scorers"] = ["slurp-slu-official", "cost"]
    doc["speech_packet_promotion_receipt"] = PACKET_PROMOTION_RECEIPT
    doc["speech_packet_promotion_receipt_sha256"] = PACKET_PROMOTION_SHA256
    doc["what_this_is"] = PLAN_WHAT_THIS_IS
    doc["what_the_train_exemplars_store_is"] = WHAT_THE_TRAIN_EXEMPLARS_STORE_IS_DEV2000
    doc.pop("prepared_phase_supply", None)
    return doc


def build_plan_experiment() -> dict:
    doc = _load_experiment(PLAN_EXPERIMENT_PRECEDENT)
    doc.pop("populations", None)
    cell = doc["cells"][0]
    cell["attempt_id"] = PLAN_GEN_ATTEMPT
    cell["baseline_fragment"] = PLAN_BASELINE_NAME
    cell["cell_id"] = PLAN_EXPERIMENT_NAME
    cell["dataset_fragment"] = DATASET_FRAGMENT
    cell["run_id"] = PLAN_RUN_ID
    cell["readiness"] = {
        "reason": (
            "Cell B6 plan arm: the locked v2.0 default plan flown unmodified on the fresh "
            "DEV-2000-ADDED roster (owner decisions 34, 35, 78, 79, 86, 88), registered before contact "
            f"on {REGISTRATION_DATE} from the sealed cell PLAN registration by script "
            "(scripts/flights/derive_slurp_b6_dev2000_cells.py): only the roster-bound bindings moved; "
            "comparator is the paired direct arm of this same package. Held pending the coordinator's "
            "root admission decision and scripts/flights/repin_cell.py, which also builds this cell's "
            "own prepared_phase_supply artifact model-free at flip time (no such pin is carried here)."
        ),
        "requirements": [
            {
                "kind": "decision",
                "expected_decision_id": DECISION_ID,
                "relpath": DECISION_RELPATH,
                "sha256": PLACEHOLDER_SHA256,
                "reason": (
                    "Root B6 admission (placeholder sha256 of 64 zeros: the coordinator mints this "
                    "receipt on the data root after merge and scripts/flights/repin_cell.py re-pins the "
                    "real hash and adds this cell's own preparation requirement; see the package README)."
                ),
            }
        ],
        "state": "held",
    }
    doc["date"] = REGISTRATION_DATE
    doc["execution_plan"] = {
        "execution_profile": "bounded-discovery-probe",
        "planned_gpu_hours": 12.0,
        "planned_model_calls": ROW_COUNT * 11,
        "planned_speech_audio_seconds": PLAN_AUDIO_CEIL,
        "split_role": "dev",
    }
    doc["execution_profile"] = "bounded-discovery-probe"
    doc["experiment_id"] = PLAN_RUN_ID
    doc["failure_policy"] = (
        "Stop and preserve on the first failure. No automatic restart, replay, row filtering, roster, "
        "role-graph, prompt, knowledge, geometry or cap change. AT MOST ONE root-diagnosed recovery "
        "re-registration for this run, and a second failure closes this flight: no third registration, "
        "and the fix must be proven on a four-row dry run before another mechanism is admitted. "
        "RESUME-RECOVERY CLAUSE (owner decision 22 of 2026-09-18, copied unchanged from cell PLAN's own "
        "failure policy): if the abort is an INFRASTRUCTURE failure with code and request bytes "
        "unchanged, the one recovery takes the resume-recovery form of harness item E10 -- the same run "
        "id, a fresh attempt id, a resume_from declaration naming the predecessor attempt and its trace "
        "SHA-256, every COMPLETE row kept without selection under invariant I7r, every partial or "
        "unstarted row re-flown in full, no change to the question, roster, comparator, decision rule or "
        "caps, and the run-cumulative budget re-checked; otherwise the one recovery is a full re-fly. A "
        "partial manifest is never scored and never read."
    )
    doc["family_budget"] = {
        "asr_calls": 0,
        "ceilings_are_not_targets": True,
        "encoder_calls": 0,
        "fit_endpoint_calls_cap": ROW_COUNT * 11 * 4,
        "generation_calls_cap": ROW_COUNT * 11,
        "gpu_hours_fit_inclusive": 12.0,
        "native_task_contract_calls_cap": ROW_COUNT * 6,
        "official_complete_scoring_jobs": 1,
        "repeated_speech_audio_seconds_cap": PLAN_AUDIO_CEIL,
    }
    doc["generation_budget"] = {
        "cap": ROW_COUNT * 11,
        "definition": (
            "The sealed B1-notool base's role graph is unchanged (perception 1, solver 1, reviewer 3, "
            "planner 1, max_revisions 1), so rails.native_episode_config.load_native_episode_config "
            f"resolves the program ceiling 1 + 2 * (3 + 1 + 1) = 11 contacts per row and {ROW_COUNT} * 11 "
            f"= {ROW_COUNT * 11} is the exact program maximum, not a conservative safety bound. Cell "
            "PLAN's own registered rate on TRAIN Fold A (cell B1's realized cost) was 5.023 contacts per "
            f"row; applied to this roster that projects to about {round(ROW_COUNT * 5.023)} contacts, an "
            "ESTIMATE only -- this roster has not been flown before."
        ),
        "target": round(ROW_COUNT * 5.023),
    }
    doc["population"] = {
        "count": ROW_COUNT,
        "dataset_fragment": DATASET_FRAGMENT,
        "decision_population": (
            "The fresh DEV-2000-ADDED roster (1,000 rows never before flown for generation; the roster's "
            "audio was previously contact-only for the model-free speech-query encoding pass that built "
            "this cell's own query vectors, docs/receipts/rosters/slurp-dev-2000-added-v1.json). Every "
            "row is preserved so the paired contrast against cell B6's direct arm covers the whole "
            "roster. TRAIN Fold A/B, DEV-1000 and the test split stay untouched and unread."
        ),
        "split_identity_hash": SPLIT_IDENTITY_HASH,
    }
    doc["purpose"] = (
        "Cell B6 plan arm: read the locked v2.0 default plan against the sealed direct arm (cell B6 "
        "direct arm, this same package) on the identical fresh DEV-2000-ADDED roster: a paired, "
        "report-only generalisation read of the locked plan against the bare frozen core, not a new "
        "admission decision (owner decisions 34, 35, 78, 79, 86, 88)."
    )
    doc["service_session"] = "serving-slurp-native-candidate-five-train-a-np4-v1"
    doc["split_id"] = SPLIT_NAME
    return doc


# ---------------------------------------------------------------------------
# Readiness package: analysis recipe, protocol, plan docs, README, prereg.
# ---------------------------------------------------------------------------


def build_analysis_recipe() -> dict:
    return {
        "schema": "saea-slurp-b6-dev2000-added-paired-analysis-recipe-v1",
        "question": (
            "On the fresh DEV-2000-ADDED roster (1,000 rows), does the locked v2.0 default plan (cell B6 "
            "plan arm) differ from the bare frozen core (cell B6 direct arm) in official pooled SLU "
            "micro F1, intent, scenario and action accuracy? Report only -- no admission verdict."
        ),
        "arms": {
            "direct": DIRECT_RUN_ID,
            "plan": PLAN_RUN_ID,
        },
        "population": {
            "roster_relpath": ROSTER_RELPATH_REPO,
            "roster_sha256": ROSTER_SHA256,
            "rows": ROW_COUNT,
            "split_identity_hash": SPLIT_IDENTITY_HASH,
            "split_name": SPLIT_NAME,
            "split_role": "dev",
        },
        "metrics": {
            "primary": "official pooled SLU micro F1 (slurp-slu-official, devel gold scorer)",
            "secondaries": ["intent accuracy", "scenario accuracy", "action accuracy"],
            "reported_beside": ["per-scenario table (natural mixture and equal-scenario weighting)"],
            "delta_convention": "delta = plan arm minus direct arm, in percentage points",
        },
        "resampling": {
            "primary": "paired bootstrap over utterance id (87 utterances carry two recordings; clustered "
            "on the utterance id per owner decision 79 D2, never on the recording id)",
            "draws": 10000,
            "seed": 20260915,
            "intervals": ["CI95"],
            "tables": ["natural mixture", "equal-scenario weighting"],
        },
        "scoring": {
            "official_scorer": "pinned SLURP official evaluate.py through core.scoring_batch",
            "complete_jobs": 2,
            "no_sharding": True,
            "scorers_direct": ["slurp-slu-official", "slurp-slu", "cost"],
            "scorers_plan": ["slurp-slu-official", "cost"],
        },
        "decision_rule": {
            "kind": "report only",
            "statement": (
                "No admission verdict is read from this cell: it is the fresh-roster generalisation read "
                "of the already-locked v2.0 plan against the bare frozen core, not a new module decision. "
                "The paired deltas and their CI95 are reported per owner decision 86 (development numbers "
                "carry no bar) and decision 79 D3 (both weightings reported)."
            ),
        },
        "not_claimed": [
            "NO ADMISSION OR SUPERIORITY VERDICT.",
            "NO GENERALIZATION OR PAPER-SCALE CLAIM: DEV-2000-ADDED is a development roster (decision 28).",
            "NO CLAIM ABOUT OTHER CARRIERS.",
        ],
        "why_no_smoke": (
            "Both forms are already sealed and flown: the direct max512 form on DEV-1000 and TRAIN Fold "
            "A, and the locked plan form on TRAIN Fold A (cell PLAN). Neither form raises a new structural "
            "question a four-row smoke would answer; only the roster-bound bindings moved, and those are "
            "proven by tests/unit/test_slurp_b6_dev2000_cells.py rather than by a smoke flight."
        ),
        "read_by": "script (owner decision 58)",
    }


def build_protocol(
    *,
    direct_config_hash: str,
    direct_protocol_hash: str,
    plan_config_hash: str,
    plan_protocol_hash: str,
) -> dict:
    return {
        "schema": "saea-slurp-b6-dev2000-added-protocol-v1",
        "protocol_id": "slurp-b6-dev2000-added-protocol-v1",
        "cell_kind": (
            "paired report-only generalisation read of the locked v2.0 default plan against the bare "
            "frozen core, on a fresh DEV-2000-ADDED roster neither arm has flown before"
        ),
        "authority": {
            "owner_decisions": (
                "34, 35 (B6 scoped and admitted), 78 (the seal path names B6 after the plan lock), 79 "
                "(D2 cluster on utterance id, D3 both weightings), 86 (development numbers carry no bar), "
                "88 (this exact derivation of both arms from their sealed precedents)"
            ),
            "evidence_base": (
                "docs/readiness/2026-09-13-slurp-direct-vs-native-system-dev1000-replication-v1/ (the "
                "sealed direct max512 form), docs/readiness/2026-09-21-slurp-default-plan-lock-v1/ (cell "
                "PLAN, the locked v2.0 default plan)"
            ),
            "engineering": (
                "tests/unit/test_slurp_b6_dev2000_cells.py proves the direct arm baseline/experiment "
                "differ from the DEV-1000 precedent, and the plan arm baseline/experiment differ from "
                "cell PLAN's, only in the enumerated roster-bound keys; no code change"
            ),
        },
        "cells": {
            "direct": {
                "cell": DIRECT_EXPERIMENT_NAME,
                "run_id": DIRECT_RUN_ID,
                "fit_run_id": DIRECT_FIT_RUN_ID,
                "attempt_id": DIRECT_GEN_ATTEMPT,
                "fit_attempt_id": DIRECT_FIT_ATTEMPT,
                "baseline_fragment": f"configs/baseline/{DIRECT_BASELINE_NAME}.json",
                "experiment_fragment": f"configs/experiment/{DIRECT_EXPERIMENT_NAME}.json",
                "composed_config_hash": direct_config_hash,
                "protocol_hash": direct_protocol_hash,
                "rows": ROW_COUNT,
                "split_identity_hash": SPLIT_IDENTITY_HASH,
                "readiness": "held; decision requirement placeholder; no preparation pin (direct arm needs none)",
            },
            "plan": {
                "cell": PLAN_EXPERIMENT_NAME,
                "run_id": PLAN_RUN_ID,
                "fit_run_id": PLAN_FIT_RUN_ID,
                "attempt_id": PLAN_GEN_ATTEMPT,
                "fit_attempt_id": PLAN_FIT_ATTEMPT,
                "baseline_fragment": f"configs/baseline/{PLAN_BASELINE_NAME}.json",
                "experiment_fragment": f"configs/experiment/{PLAN_EXPERIMENT_NAME}.json",
                "composed_config_hash": plan_config_hash,
                "protocol_hash": plan_protocol_hash,
                "rows": ROW_COUNT,
                "split_identity_hash": SPLIT_IDENTITY_HASH,
                "readiness": (
                    "held; decision requirement placeholder; NO preparation pin -- "
                    "scripts/flights/repin_cell.py builds this cell's own prepared_phase_supply "
                    "model-free at flip time"
                ),
            },
        },
        "comparator": {
            "kind": "paired, within this package: plan arm minus direct arm on the same 1,000 rows",
            "never_reflown": True,
        },
        "population": {
            "roster": {"relpath": ROSTER_RELPATH_REPO, "sha256": ROSTER_SHA256},
            "rows": ROW_COUNT,
            "split_id": SPLIT_NAME,
            "split_identity_hash": SPLIT_IDENTITY_HASH,
            "split_role": "dev",
            "total_audio_seconds": TOTAL_AUDIO_SECONDS,
        },
        "accounting": {
            "direct_family_budget": {
                "generation_calls_cap": ROW_COUNT,
                "fit_endpoint_calls_cap": 3001,
                "repeated_speech_audio_seconds_cap": 3500,
                "gpu_hours_fit_inclusive": 1.0,
                "official_complete_scoring_jobs": 1,
            },
            "plan_family_budget": {
                "generation_calls_cap": ROW_COUNT * 11,
                "fit_endpoint_calls_cap": ROW_COUNT * 11 * 4,
                "native_task_contract_calls_cap": ROW_COUNT * 6,
                "repeated_speech_audio_seconds_cap": PLAN_AUDIO_CEIL,
                "gpu_hours_fit_inclusive": 12.0,
                "official_complete_scoring_jobs": 1,
            },
            "ceilings_are_not_targets": True,
            "unused_budget_is_not_attempt_authority": True,
            "plan_budget_is_run_cumulative": True,
        },
        "metrics": build_analysis_recipe()["metrics"],
        "resampling": build_analysis_recipe()["resampling"],
        "decision_rule": build_analysis_recipe()["decision_rule"],
        "not_authorized": [
            "no readiness flip -- both cells stay held until the coordinator mints "
            f"{DECISION_RELPATH} and runs scripts/flights/repin_cell.py",
            "no model, tokenizer, encoder, ASR, scorer, server or paid-API contact",
            "no smoke flight -- both forms are already sealed and flown elsewhere",
            "no admission verdict -- this is a report-only fresh-roster generalisation read",
        ],
        "not_claimed": build_analysis_recipe()["not_claimed"],
        "failure_policy": (
            "Stop and preserve on the first failure in either arm. At most one root-diagnosed recovery "
            "re-registration per flight. RESUME-RECOVERY CLAUSE (owner decision 22 of 2026-09-18, copied "
            "unchanged from cell PLAN's failure policy): an infrastructure death with code and request "
            "bytes unchanged may be recovered as a resume-recovery under item E10, keeping every complete "
            "row without selection under invariant I7r, re-flying every partial or unstarted row under "
            "the same run id, changing no question, roster, comparator, decision rule or cap, and "
            "re-checking the run-cumulative budget. A partial manifest is never scored and never read."
        ),
        "why_no_smoke": build_analysis_recipe()["why_no_smoke"],
        "registered_at_utc": REGISTERED_AT_UTC,
        "source_tree": SOURCE_TREE,
        "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP",
    }


def build_plan_document(
    *,
    plan_kind: str,
    arm: str,
    cell_id: str,
    run_id: str,
    attempt_id: str,
    composed_config_hash: str,
    protocol_hash_value: str,
    expected_session_id: str,
    execution_route: str,
    family_budget: dict,
    planned_model_calls: int,
    planned_speech_audio_seconds: int,
    planned_gpu_hours: float,
    purpose: str,
    protocol_document_sha256: str,
) -> dict:
    return {
        "schema": f"saea-registered-{plan_kind}-plan-v1",
        "plan_kind": plan_kind,
        "cell": cell_id,
        "composed_config_hash": composed_config_hash,
        "execution_plan": {
            "attempt_id": attempt_id,
            "carrier_lock_key": "slurp",
            "execution_profile": "bounded-discovery-probe",
            "planned_gpu_hours": planned_gpu_hours,
            "planned_model_calls": planned_model_calls,
            "planned_speech_audio_seconds": planned_speech_audio_seconds,
            "protocol_hash": protocol_hash_value,
            "run_id": run_id,
            "schema": "saea-execution-plan-v1",
            "split_identity_hash": SPLIT_IDENTITY_HASH,
            "split_role": "dev",
            "study": "speech-aware-evidence-acquisition",
        },
        "execution_route": execution_route,
        "expected_session_id": expected_session_id,
        "experiment": arm,
        "family_budget": family_budget,
        "protocol_document": {
            "relpath": f"docs/readiness/2026-09-22-slurp-b6-dev2000-added-v1/{PROTOCOL_DOC_NAME}",
            "sha256": protocol_document_sha256,
        },
        "purpose": purpose,
        "quality_read_gate": (
            "No task-quality read before the complete sealed manifest and the single successful complete "
            "official score exist on BOTH arms of this package."
        ),
        "registered_at_utc": REGISTERED_AT_UTC,
        "source_tree": SOURCE_TREE,
        "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP",
        "unused_budget_is_not_attempt_authority": True,
    }


def build_readme(*, direct_config_hash, direct_protocol_hash, plan_config_hash, plan_protocol_hash) -> str:
    return f"""# Cell B6 -- DEV-2000-ADDED direct-vs-plan paired read

Registered before contact on {REGISTRATION_DATE} by script
(`scripts/flights/derive_slurp_b6_dev2000_cells.py`) from two already-sealed precedents: the direct
max512 form (DEV-1000) and the locked v2.0 default plan (cell PLAN, TRAIN Fold A). Both forms fly
unmodified on the fresh DEV-2000-ADDED roster (1,000 rows, split identity `{SPLIT_IDENTITY_HASH}`); only
the roster-bound bindings moved. No smoke: both forms are already sealed and flown elsewhere (see
`{ANALYSIS_RECIPE_NAME}`'s `why_no_smoke`).

## Cells

| arm | run id | fit run id | baseline fragment | experiment fragment |
| --- | --- | --- | --- | --- |
| direct | `{DIRECT_RUN_ID}` | `{DIRECT_FIT_RUN_ID}` | `configs/baseline/{DIRECT_BASELINE_NAME}.json` | `configs/experiment/{DIRECT_EXPERIMENT_NAME}.json` |
| plan | `{PLAN_RUN_ID}` | `{PLAN_FIT_RUN_ID}` | `configs/baseline/{PLAN_BASELINE_NAME}.json` | `configs/experiment/{PLAN_EXPERIMENT_NAME}.json` |

Composed/protocol hashes at generation time (recomputed live by this script from the committed
fragments; a merge or re-pin that changes either fragment changes these, and this README along with
every other package file must be re-derived rather than hand-edited):

* direct: composed `{direct_config_hash}`, protocol `{direct_protocol_hash}`
* plan: composed `{plan_config_hash}`, protocol `{plan_protocol_hash}`

## Readiness

Both cells stay `held`. Their `decision` readiness requirement carries a **placeholder sha256 of 64
zeros** at `{DECISION_RELPATH}` (decision id `{DECISION_ID}`): the coordinator mints that receipt on the
data root *after* this branch merges, then runs `scripts/flights/repin_cell.py` to re-pin the real hash,
flip readiness to `ready`, and -- for the plan arm only -- build and pin its own `prepared_phase_supply`
artifact model-free under its own run id (see `scripts/flights/repin.py`'s documented fallback for "a
cell registered before its supply could be prepared"). Neither cell carries a `prepared_phase_supply` pin
today, and this registration writes nothing under `$SPEECHRL_DATA_DIR` beyond the query-content
derivative of item 1 (`vectors/slurp-dev2000-added-v1/query-vectors-speech-content-v1.jsonl`, sha256
`{CONTENT_QUERY_SHA256}`, 1,000 rows).

## Re-deriving this package

`python scripts/flights/derive_slurp_b6_dev2000_cells.py` regenerates every file in this directory, the
sibling preregistration note and the five exposure-ledger rows from the committed baseline/experiment
fragments; it is idempotent (a re-run with no intervening edits is a no-op) and refuses to overwrite a
file whose on-disk content differs from what it would generate, or to touch an exposure-ledger row
already marked `consumed = yes`.

## Read

Paired, report-only: plan arm minus direct arm on the same 1,000 DEV-2000-ADDED rows. See
`{ANALYSIS_RECIPE_NAME}` for the metrics, resampling and decision rule, and the sibling preregistration
note for the full statement. No admission verdict is read from this cell.
"""


def build_preregistration(*, direct_config_hash, direct_protocol_hash, plan_config_hash, plan_protocol_hash) -> str:
    return f"""# Preregistration -- cell B6, DEV-2000-ADDED direct-vs-plan paired read

Registered before contact on {REGISTRATION_DATE} (owner decisions 34, 35, 78, 79, 86, 88), by script
(`scripts/flights/derive_slurp_b6_dev2000_cells.py`, decision 58).

## Question

On the fresh DEV-2000-ADDED roster (1,000 rows, split identity `{SPLIT_IDENTITY_HASH}`, never before
flown for generation), how does the locked v2.0 default plan (cell B6 plan arm) compare with the bare
frozen core (cell B6 direct arm) in official pooled SLU micro F1, intent, scenario and action accuracy?
This is a **report-only fresh-roster generalisation read**, not a new admission decision: the plan was
already locked on TRAIN Fold A evidence (cell PLAN) and the direct form was already sealed on DEV-1000
and TRAIN Fold A.

## Arms

* **Direct** (`{DIRECT_RUN_ID}`): the sealed `slurp-direct-max512` form, unmodified, flown on
  DEV-2000-ADDED. Composed config hash `{direct_config_hash}`, protocol hash `{direct_protocol_hash}`.
* **Plan** (`{PLAN_RUN_ID}`): the locked v2.0 default plan (cell PLAN's fragment), unmodified, flown on
  DEV-2000-ADDED. Composed config hash `{plan_config_hash}`, protocol hash `{plan_protocol_hash}`.

## Bindings

* Dataset fragment `slurp-speech-native-dev2000-added` (`configs/dataset/slurp-speech-native-dev2000-added.json`),
  roster receipt `{ROSTER_RELPATH_REPO}` (sha256 `{ROSTER_SHA256}`).
* Speech packet promotion receipt `{PACKET_PROMOTION_RECEIPT}` (sha256 `{PACKET_PROMOTION_SHA256}`).
* Intent-boundary query vectors `{INTENT_BOUNDARY_QUERY_RELPATH}` (sha256 `{INTENT_BOUNDARY_QUERY_SHA256}`,
  1,000 rows, one segment each).
* Train-exemplars content-dimension query vectors `{CONTENT_QUERY_RELPATH}` (sha256
  `{CONTENT_QUERY_SHA256}`, 1,000 rows), built model-free by
  `scripts/build_slurp_query_content_derivative.py` from the intent-boundary file above (item 1 of this
  registration; tool-contact ledger row `{TOOL_CONTACT_LEDGER_ROW}`).
* Alias receipt `{ALIAS_RECEIPT_RELPATH_DATA}` (sha256 `{ALIAS_RECEIPT_SHA256}`), encoding receipt
  `{ENCODING_RECEIPT_RELPATH_DATA}` (sha256 `{ENCODING_RECEIPT_SHA256}`), all `root: data`.

## No four-row smoke

Both forms are already sealed and flown: the direct max512 form on DEV-1000 and TRAIN Fold A, and the
locked plan on TRAIN Fold A (cell PLAN). Neither raises a new structural question a smoke would answer;
the only thing that moved is the roster-bound bindings enumerated above, and
`tests/unit/test_slurp_b6_dev2000_cells.py` proves those are the *only* things that moved, against both
precedents, byte for byte.

## No twin

Not registered; this cell reads two already-decided forms on a fresh roster, not a new mechanism.

## Metrics

Primary: official pooled SLU micro F1 (`slurp-slu-official`, devel gold scorer -- **not** the `-train`
sibling, since this is a `dev`-role roster). Secondaries: intent, scenario and action accuracy. Reported
beside: the per-scenario table in both the natural-mixture and the equal-scenario weighting (owner
decision 79 D3).

## Resampling

Paired bootstrap, 10,000 draws, seed 20260915, CI95, clustered on the **utterance id** (87 utterances
carry two recordings; owner decision 79 D2 clusters on the utterance, never on the individual recording,
so a paired draw never splits a twin-recording utterance across arms).

## Decision rule

**Report only.** No admission verdict is read from this cell: it reports the paired deltas (plan minus
direct) and their CI95, in both weightings, per owner decision 86 (development numbers carry no bar).

## What is not claimed

No admission or superiority verdict; no generalization or paper-scale claim (DEV-2000-ADDED is a
development roster, owner decision 28); no claim about other carriers; nothing about any in-flight cell.

## Resume-recovery clause

Copied unchanged from cell PLAN's own failure policy (owner decision 22 of 2026-09-18): if an attempt
dies of an INFRASTRUCTURE failure with code and request bytes unchanged -- never a harness or config
defect -- the one allowed recovery may be a RESUME-RECOVERY under item E10 instead of a re-fly: every
complete row of the aborted attempt is kept without selection, every partial or unstarted row is flown
under the same run id, and the merged manifest declares the predecessor attempt with its trace hash,
kept-row list and that list's hash. It changes no question, roster, factor, comparator, decision rule or
cap, and the run-cumulative budget must be re-checked because a resumed attempt and its predecessor share
one run id. A resumed EFFICIENCY read must additionally state the split of its GPU hours and prefilled
tokens across attempts.

## Readiness

Both cells `held`; decision readiness requirement carries a placeholder sha256 of 64 zeros pending the
coordinator's root admission decision and `scripts/flights/repin_cell.py` (see the package README).
"""


# ---------------------------------------------------------------------------
# Exposure ledger.
# ---------------------------------------------------------------------------

_LEDGER_HEADER_RUN = "run/experiment id"
_LEDGER_HEADER_CONSUMED = "consumed"


def _split_row_cells(line: str) -> list[str] | None:
    stripped = line.strip()
    if len(stripped) < 2 or not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    return [cell.strip() for cell in stripped[1:-1].split("|")]


def _find_ledger_row(text: str, run_id: str) -> str | None:
    header: list[str] | None = None
    lines = text.splitlines()
    for index, line in enumerate(lines):
        cells = _split_row_cells(line)
        if cells is None:
            continue
        next_cells = _split_row_cells(lines[index + 1]) if index + 1 < len(lines) else None
        if next_cells is not None and all(not c.strip("-: ") for c in next_cells):
            lowered = [c.lower() for c in cells]
            header = lowered if _LEDGER_HEADER_RUN in lowered else None
            continue
        if header is not None and len(cells) == len(header):
            run_col = header.index(_LEDGER_HEADER_RUN)
            if cells[run_col] == run_id:
                return line
    return None


def build_ledger_row(
    *,
    run_id: str,
    execution_profile: str,
    scope: str,
    model_tool: str,
    carrier_split: str,
    split_role: str,
    calls: int,
    audio_seconds: int,
    gpu_hours: float,
    inherited_exposure: str,
    artifacts: str,
    notes: str,
) -> str:
    cells = [
        REGISTERED_AT_UTC,
        run_id,
        execution_profile,
        scope,
        model_tool,
        carrier_split,
        split_role,
        SPLIT_IDENTITY_HASH,
        "no",
        str(calls),
        str(audio_seconds),
        str(gpu_hours),
        inherited_exposure,
        artifacts,
        notes,
    ]
    return "| " + " | ".join(cells) + " |"


INHERITED_EXPOSURE = (
    "DEV-2000-ADDED dev rows: this roster's audio was previously contact-only for the model-free speech-query "
    "encoding pass that built this cell's own query vectors (SAEA-SLURP-DEV2000-ADDED-SPEECH-QUERY-ENCODING-V1, "
    "1,000 encoder contacts, closed at study commit c8cd2442, sealed at b03ee619; no generation task performed). "
    "This is the FIRST generation/task-answering exposure of this roster. No gold, reference or future turn is "
    "read. DEV-1000, TRAIN Fold A/B and the test split stay untouched by this cell."
)

MODEL_TOOL_DIRECT = (
    "Frozen Q4_K_M decoder-only c98304 np4 max512; promoted DEV-2000-ADDED speech packets; closed-list direct "
    "task prompts, no retrieved knowledge, no tools; prompt bytes the sealed slurp-direct-max512 form's."
)
MODEL_TOOL_PLAN = (
    "Frozen Q4_K_M decoder-only c98304 np4 max512; promoted DEV-2000-ADDED speech packets; NO native tool "
    "authority on any role (native task-contract call ceiling 0); one normaliser receipt per row; prompt bytes "
    "otherwise the locked v2.0 default plan's (cell PLAN) with this roster's own query-vector bindings."
)


def append_ledger_rows(*, direct_protocol_doc_sha256: str, plan_protocol_doc_sha256: str, analysis_recipe_sha256: str, check: bool) -> list[str]:
    text = LEDGER_PATH.read_text(encoding="utf-8")

    rows_spec = [
        (
            DIRECT_RUN_ID,
            build_ledger_row(
                run_id=DIRECT_RUN_ID,
                execution_profile="bounded-discovery-probe",
                scope="Cell B6 direct arm: the sealed slurp-direct-max512 form flown unmodified on the fresh DEV-2000-ADDED roster; generation.",
                model_tool=MODEL_TOOL_DIRECT,
                carrier_split="slurp DEV-2000-ADDED 1000",
                split_role="dev",
                calls=ROW_COUNT,
                audio_seconds=DIRECT_AUDIO_CEIL,
                gpu_hours=1.0,
                inherited_exposure=INHERITED_EXPOSURE,
                artifacts="docs/readiness/2026-09-22-slurp-b6-dev2000-added-v1/direct-generation-plan-registered-v1.json",
                notes=(
                    f"Plan SHA256 {direct_protocol_doc_sha256}; attempt {DIRECT_GEN_ATTEMPT}. Shared controller, "
                    "FlightRuntime and OpenJiuwen executor, same policy as the sealed DEV-1000/TRAIN Fold A direct "
                    "forms. No smoke: form already sealed and flown twice elsewhere. Report-only paired read "
                    f"against {PLAN_RUN_ID}, no admission verdict. Preregistration: "
                    "docs/readiness/2026-09-22-slurp-b6-dev2000-added-v1-preregistration.md; runbook: "
                    "docs/readiness/2026-09-22-slurp-b6-dev2000-added-v1/README.md. Registered before contact at "
                    "study commit b03ee619 by the B6 registration agent (worktree /home/chao/saea-worktrees/fable-b6, "
                    "branch fable/b6)."
                ),
            ),
        ),
        (
            DIRECT_FIT_RUN_ID,
            build_ledger_row(
                run_id=DIRECT_FIT_RUN_ID,
                execution_profile="bounded-discovery-probe",
                scope="Cell B6 direct arm: the sealed slurp-direct-max512 form flown unmodified on the fresh DEV-2000-ADDED roster; live phase fit.",
                model_tool=MODEL_TOOL_DIRECT,
                carrier_split="slurp DEV-2000-ADDED 1000",
                split_role="dev",
                calls=3001,
                audio_seconds=3500,
                gpu_hours=1.0,
                inherited_exposure=INHERITED_EXPOSURE,
                artifacts="docs/readiness/2026-09-22-slurp-b6-dev2000-added-v1/direct-fit-plan-registered-v1.json",
                notes=(
                    f"Plan SHA256 {direct_protocol_doc_sha256}; attempt {DIRECT_FIT_ATTEMPT}. Fitted inside the "
                    f"same campaign under the same lease as {DIRECT_RUN_ID}; coordinate-fit is not run. Caps "
                    "unchanged from the DEV-1000 precedent (1,000 rows on both rosters). Preregistration: "
                    "docs/readiness/2026-09-22-slurp-b6-dev2000-added-v1-preregistration.md; runbook: "
                    "docs/readiness/2026-09-22-slurp-b6-dev2000-added-v1/README.md. Registered before contact at "
                    "study commit b03ee619 by the B6 registration agent (worktree /home/chao/saea-worktrees/fable-b6, "
                    "branch fable/b6)."
                ),
            ),
        ),
        (
            PLAN_RUN_ID,
            build_ledger_row(
                run_id=PLAN_RUN_ID,
                execution_profile="bounded-discovery-probe",
                scope="Cell B6 plan arm: the locked v2.0 default plan flown unmodified on the fresh DEV-2000-ADDED roster; generation.",
                model_tool=MODEL_TOOL_PLAN,
                carrier_split="slurp DEV-2000-ADDED 1000",
                split_role="dev",
                calls=ROW_COUNT * 11,
                audio_seconds=PLAN_AUDIO_CEIL,
                gpu_hours=12.0,
                inherited_exposure=INHERITED_EXPOSURE,
                artifacts="docs/readiness/2026-09-22-slurp-b6-dev2000-added-v1/plan-generation-plan-registered-v1.json",
                notes=(
                    f"Plan SHA256 {plan_protocol_doc_sha256}; attempt {PLAN_GEN_ATTEMPT}. Shared core.flight.cli "
                    "campaign; the SAME cell PLAN bytes with only this roster's own bindings (dataset fragment, "
                    "promoted packets, the two row-side query_source pins, preparation_source_receipts, devel-gold "
                    "scorer). No smoke: form already sealed and flown on TRAIN Fold A. Report-only paired read "
                    f"against {DIRECT_RUN_ID}, no admission verdict. Neither cell carries a prepared_phase_supply "
                    "pin; scripts/flights/repin_cell.py builds it model-free at flip time. Preregistration: "
                    "docs/readiness/2026-09-22-slurp-b6-dev2000-added-v1-preregistration.md; runbook: "
                    "docs/readiness/2026-09-22-slurp-b6-dev2000-added-v1/README.md. Registered before contact at "
                    "study commit b03ee619 by the B6 registration agent (worktree /home/chao/saea-worktrees/fable-b6, "
                    "branch fable/b6)."
                ),
            ),
        ),
        (
            PLAN_FIT_RUN_ID,
            build_ledger_row(
                run_id=PLAN_FIT_RUN_ID,
                execution_profile="bounded-discovery-probe",
                scope="Cell B6 plan arm: the locked v2.0 default plan flown unmodified on the fresh DEV-2000-ADDED roster; native contact fit.",
                model_tool=MODEL_TOOL_PLAN,
                carrier_split="slurp DEV-2000-ADDED 1000",
                split_role="dev",
                calls=ROW_COUNT * 11 * 4,
                audio_seconds=PLAN_AUDIO_CEIL,
                gpu_hours=12.0,
                inherited_exposure=INHERITED_EXPOSURE,
                artifacts="docs/readiness/2026-09-22-slurp-b6-dev2000-added-v1/plan-fit-plan-registered-v1.json",
                notes=(
                    f"Plan SHA256 {plan_protocol_doc_sha256}; attempt {PLAN_FIT_ATTEMPT}. "
                    f"{ROW_COUNT} rows * 11 native contacts * (1 speech packet + 3 endpoints) = "
                    f"{ROW_COUNT * 11 * 4}. Fitted inside the same campaign under the same lease; coordinate-fit "
                    "is not run. Caps rescaled from cell PLAN's 1,080-row ceilings to this roster's 1,000 rows "
                    "using the same per-row arithmetic. Preregistration: "
                    "docs/readiness/2026-09-22-slurp-b6-dev2000-added-v1-preregistration.md; runbook: "
                    "docs/readiness/2026-09-22-slurp-b6-dev2000-added-v1/README.md. Registered before contact at "
                    "study commit b03ee619 by the B6 registration agent (worktree /home/chao/saea-worktrees/fable-b6, "
                    "branch fable/b6)."
                ),
            ),
        ),
        (
            ANALYSIS_RUN_ID,
            build_ledger_row(
                run_id=ANALYSIS_RUN_ID,
                execution_profile="model-free-check",
                scope="Cell B6: the paired direct-vs-plan analysis over the two sealed manifests above; model-free.",
                model_tool="No model, tokenizer, encoder or server contact: a pure paired-bootstrap analysis of two already-scored, sealed manifests.",
                carrier_split="slurp DEV-2000-ADDED 1000",
                split_role="dev",
                calls=0,
                audio_seconds=0,
                gpu_hours=0.0,
                inherited_exposure="Reads only the two sealed manifests of this same package; no new audio, gold or reference exposure.",
                artifacts=f"docs/readiness/2026-09-22-slurp-b6-dev2000-added-v1/{ANALYSIS_RECIPE_NAME}",
                notes=(
                    f"Recipe SHA256 {analysis_recipe_sha256}. Paired bootstrap over the utterance id, 10,000 "
                    "draws, seed 20260915, CI95, both weightings (owner decision 79 D2/D3). Report only: no "
                    "admission verdict (owner decision 86). Read by script (owner decision 58). Preregistration: "
                    "docs/readiness/2026-09-22-slurp-b6-dev2000-added-v1-preregistration.md. Registered before "
                    "contact at study commit b03ee619 by the B6 registration agent (worktree "
                    "/home/chao/saea-worktrees/fable-b6, branch fable/b6)."
                ),
            ),
        ),
    ]

    appended: list[str] = []
    new_text = text
    for run_id, row in rows_spec:
        existing = _find_ledger_row(new_text, run_id)
        if existing is not None:
            existing_cells = _split_row_cells(existing)
            if existing_cells is not None and existing_cells[8].strip().lower() == "yes":
                raise DeriveError(f"exposure ledger row {run_id!r} is already consumed = yes; refusing to touch it")
            if existing.strip() != row.strip():
                raise DeriveError(
                    f"exposure ledger already carries a row for {run_id!r} that differs from the freshly "
                    "generated row; refusing to overwrite"
                )
            continue
        if not new_text.endswith("\n"):
            new_text += "\n"
        new_text += row + "\n"
        appended.append(run_id)

    if appended and not check:
        LEDGER_PATH.write_text(new_text, encoding="utf-8", newline="\n")
    return appended


# ---------------------------------------------------------------------------
# Orchestration.
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="dry run: write nothing")
    args = parser.parse_args(argv)
    check = args.check

    verify_bindings()

    # 1. Analysis recipe (no dependency on the fragments' own hashes).
    analysis_recipe = build_analysis_recipe()
    analysis_recipe_text = _canonical(analysis_recipe)
    analysis_recipe_path = READINESS_DIR / ANALYSIS_RECIPE_NAME
    status_recipe = _write_if_needed(analysis_recipe_path, analysis_recipe_text, check=check)
    analysis_recipe_sha256 = _sha256_bytes(analysis_recipe_text.encode("utf-8"))

    # 2. Baseline + experiment fragments for both arms.
    direct_baseline = build_direct_baseline()
    direct_experiment = build_direct_experiment(analysis_recipe_sha256)
    plan_baseline = build_plan_baseline()
    plan_experiment = build_plan_experiment()

    statuses = {}
    statuses["direct_baseline"] = _write_if_needed(
        BASELINE_DIR / f"{DIRECT_BASELINE_NAME}.json", _canonical(direct_baseline), check=check
    )
    statuses["direct_experiment"] = _write_if_needed(
        EXPERIMENT_DIR / f"{DIRECT_EXPERIMENT_NAME}.json", _canonical(direct_experiment), check=check
    )
    statuses["plan_baseline"] = _write_if_needed(
        BASELINE_DIR / f"{PLAN_BASELINE_NAME}.json", _canonical(plan_baseline), check=check
    )
    statuses["plan_experiment"] = _write_if_needed(
        EXPERIMENT_DIR / f"{PLAN_EXPERIMENT_NAME}.json", _canonical(plan_experiment), check=check
    )

    if check and any(status == "would-write" for status in statuses.values()):
        print(json.dumps({"check": True, "statuses": statuses}, indent=2))
        return 0

    # 3. Compose hashes from the fragments actually on disk (post-write, or
    #    already-identical pre-existing ones).
    direct_composed = compose(REPO_ROOT, MODEL_FRAGMENT, DATASET_FRAGMENT, DIRECT_BASELINE_NAME, DIRECT_EXPERIMENT_NAME)
    direct_arm = direct_composed.values["arm"]
    direct_protocol_hash = compute_protocol_hash(direct_composed.config_hash, direct_arm, SPLIT_IDENTITY_HASH)

    plan_composed = compose(REPO_ROOT, MODEL_FRAGMENT, DATASET_FRAGMENT, PLAN_BASELINE_NAME, PLAN_EXPERIMENT_NAME)
    plan_arm = plan_composed.values["arm"]
    plan_protocol_hash = compute_protocol_hash(plan_composed.config_hash, plan_arm, SPLIT_IDENTITY_HASH)

    # 4. Protocol document (references both arms' real hashes).
    protocol = build_protocol(
        direct_config_hash=direct_composed.config_hash,
        direct_protocol_hash=direct_protocol_hash,
        plan_config_hash=plan_composed.config_hash,
        plan_protocol_hash=plan_protocol_hash,
    )
    protocol_text = _canonical(protocol)
    protocol_path = READINESS_DIR / PROTOCOL_DOC_NAME
    statuses["protocol"] = _write_if_needed(protocol_path, protocol_text, check=check)
    protocol_sha256 = _sha256_bytes(protocol_text.encode("utf-8"))

    # 5. Generation + fit plan docs (fresh and -registered) for both arms.
    direct_family_budget = {
        "asr_calls": 0,
        "ceilings_are_not_targets": True,
        "encoder_calls": 0,
        "fit_endpoint_calls_cap": 3001,
        "generation_calls_cap": ROW_COUNT,
        "gpu_hours_fit_inclusive": 1.0,
        "official_complete_scoring_jobs": 1,
        "repeated_speech_audio_seconds_cap": 3500,
    }
    plan_family_budget = plan_experiment["family_budget"]

    direct_gen_doc = build_plan_document(
        plan_kind="generation",
        arm=DIRECT_EXPERIMENT_NAME,
        cell_id=DIRECT_EXPERIMENT_NAME,
        run_id=DIRECT_RUN_ID,
        attempt_id=DIRECT_GEN_ATTEMPT,
        composed_config_hash=direct_composed.config_hash,
        protocol_hash_value=direct_protocol_hash,
        expected_session_id=direct_experiment["service_session"],
        execution_route=(
            "Shared core.flight.cli campaign over a committed single-cell campaign plan; direct-only phase "
            "program through the shared controller, FlightRuntime and OpenJiuwen executor."
        ),
        family_budget=direct_family_budget,
        planned_model_calls=ROW_COUNT,
        planned_speech_audio_seconds=DIRECT_AUDIO_CEIL,
        planned_gpu_hours=1.0,
        purpose=direct_experiment["purpose"],
        protocol_document_sha256=protocol_sha256,
    )
    direct_fit_doc = dict(direct_gen_doc)
    direct_fit_doc["schema"] = "saea-registered-fit-plan-v1"
    direct_fit_doc["plan_kind"] = "fit"
    direct_fit_doc["execution_plan"] = dict(direct_gen_doc["execution_plan"])
    direct_fit_doc["execution_plan"]["attempt_id"] = DIRECT_FIT_ATTEMPT
    direct_fit_doc["execution_plan"]["run_id"] = DIRECT_FIT_RUN_ID
    direct_fit_doc["execution_plan"]["planned_model_calls"] = 3001
    direct_fit_doc["execution_route"] = "Live-phase fit inside the same campaign and lease as the generation cell; coordinate-fit is not run."

    plan_gen_doc = build_plan_document(
        plan_kind="generation",
        arm=PLAN_EXPERIMENT_NAME,
        cell_id=PLAN_EXPERIMENT_NAME,
        run_id=PLAN_RUN_ID,
        attempt_id=PLAN_GEN_ATTEMPT,
        composed_config_hash=plan_composed.config_hash,
        protocol_hash_value=plan_protocol_hash,
        expected_session_id=plan_experiment["service_session"],
        execution_route=(
            "Shared core.flight.cli campaign over a committed single-cell campaign plan; the campaign "
            "acquires its own GenerationLease against the resident session and schedules the one official "
            "score at finalize. coordinate-fit must NOT be run."
        ),
        family_budget=plan_family_budget,
        planned_model_calls=ROW_COUNT * 11,
        planned_speech_audio_seconds=PLAN_AUDIO_CEIL,
        planned_gpu_hours=12.0,
        purpose=plan_experiment["purpose"],
        protocol_document_sha256=protocol_sha256,
    )
    plan_fit_doc = dict(plan_gen_doc)
    plan_fit_doc["schema"] = "saea-registered-fit-plan-v1"
    plan_fit_doc["plan_kind"] = "fit"
    plan_fit_doc["execution_plan"] = dict(plan_gen_doc["execution_plan"])
    plan_fit_doc["execution_plan"]["attempt_id"] = PLAN_FIT_ATTEMPT
    plan_fit_doc["execution_plan"]["run_id"] = PLAN_FIT_RUN_ID
    plan_fit_doc["execution_plan"]["planned_model_calls"] = ROW_COUNT * 11 * 4
    plan_fit_doc["execution_route"] = (
        f"{ROW_COUNT} rows * 11 native contacts * (1 speech packet + 3 endpoints) = {ROW_COUNT * 11 * 4}. "
        "Fitted inside the same campaign under the same lease; coordinate-fit is not run."
    )

    for stem, doc in (
        ("direct-generation-plan", direct_gen_doc),
        ("direct-fit-plan", direct_fit_doc),
        ("plan-generation-plan", plan_gen_doc),
        ("plan-fit-plan", plan_fit_doc),
    ):
        text = _canonical(doc)
        for suffix in ("-v1.json", "-registered-v1.json"):
            statuses[stem + suffix] = _write_if_needed(READINESS_DIR / (stem + suffix), text, check=check)

    # 6. README + preregistration.
    readme_text = build_readme(
        direct_config_hash=direct_composed.config_hash,
        direct_protocol_hash=direct_protocol_hash,
        plan_config_hash=plan_composed.config_hash,
        plan_protocol_hash=plan_protocol_hash,
    )
    statuses["README"] = _write_if_needed(READINESS_DIR / "README.md", readme_text, check=check)

    prereg_text = build_preregistration(
        direct_config_hash=direct_composed.config_hash,
        direct_protocol_hash=direct_protocol_hash,
        plan_config_hash=plan_composed.config_hash,
        plan_protocol_hash=plan_protocol_hash,
    )
    statuses["preregistration"] = _write_if_needed(PREREG_PATH, prereg_text, check=check)

    # 7. Exposure ledger.
    appended = append_ledger_rows(
        direct_protocol_doc_sha256=protocol_sha256,
        plan_protocol_doc_sha256=protocol_sha256,
        analysis_recipe_sha256=analysis_recipe_sha256,
        check=check,
    )

    print(
        json.dumps(
            {
                "check": check,
                "statuses": statuses,
                "ledger_rows_appended": appended,
                "direct_config_hash": direct_composed.config_hash,
                "direct_protocol_hash": direct_protocol_hash,
                "plan_config_hash": plan_composed.config_hash,
                "plan_protocol_hash": plan_protocol_hash,
                "protocol_document_sha256": protocol_sha256,
                "analysis_recipe_sha256": analysis_recipe_sha256,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
