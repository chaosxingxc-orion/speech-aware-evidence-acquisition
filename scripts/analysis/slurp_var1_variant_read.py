#!/usr/bin/env python3
"""VAR-1 VARIANT READ -- the committed driver for registered open items ``VAR1-OPEN-1`` and
``VAR1-OPEN-2`` of ``docs/readiness/2026-09-24-slurp-stage3-var1-v1/``.

WHAT THIS IS
------------
``scripts/analysis/slurp_paired_roster_read.py`` produces the pooled paired contrast, the
per-channel table, the structural counts and the efficiency block of ONE pair of arms, and it
hard-codes "per-scenario NOT AVAILABLE" for its own roster. That is ``VAR1-OPEN-1``. The entity
FP/FN decomposition by slot TYPE, the Perception coverage read and the group-relative advantage
table have no committed driver at all. That is ``VAR1-OPEN-2``. This module is both, for the
whole six-cell VAR-1 family at once, and it satisfies the contract in the package's
``analysis-recipe-v1.json``.

It reads ONLY sealed bytes -- per-sample official scores, sealed outputs, sealed phase summaries,
the run and generation manifests, the flight receipts, the roster receipt, the pinned knowledge
release -- plus the frozen TRAIN gold, offline, through the study's own governed loader. It makes
ZERO model, tokenizer, encoder, server, scorer and network contacts, and it is registered as the
model-free-check read rows ``SAEA-SLURP-STAGE3-VAR1-OWN-NULL-V1`` and
``SAEA-SLURP-STAGE3-VAR1-VARIANT-READ-V1``.

THE HARM RULE, ENFORCED BY CONSTRUCTION
---------------------------------------
No utterance, transcript, delivered filler, gold filler or model output text is printed or
persisted anywhere. Gold entities and delivered entities exist only inside
``slurp_plan_bad_case_bank.row_entity_view``'s call frame; what leaves this process is labels
(intent ids, scenario names, slot TYPE names), sample ids, integer counts, rates, scores and
hashes. The exemplar store is read for its ``task_target`` label alone -- never its ``content``.

THE ORDER IS PART OF THE REGISTRATION
-------------------------------------
``own-null.json`` is written FIRST and its own sha256 is embedded into
``variant-contrasts.json``; the variant stage REFUSES if that artefact is absent. The margin
table appears above the variant table in ``README.md``. ``h_cross_r01c`` is the CI95 half-width
VAR1-PLAN against VAR1-PLANR produces on THIS roster, and it is never adjusted afterwards. The
within-flight null ``h_within`` (ROLL-AA, 0.735 SLU / 0.000 intent), the TRAIN Fold A margins and
the DEV-2000-ADDED margins are printed beside it as CONTEXT ONLY: a margin is a property of a
roster, never of a mechanism.

WHAT IT DOES NOT DO
-------------------
It attaches no ADMITTED / NEUTRAL / HARMFUL label to any cell, admits no module, releases no
store and locks nothing. A variant whose CI95 excludes zero AND whose point estimate lies outside
+-h is called SEPARATED FROM THE NULL; anything else is INSIDE THE NULL. R01C is a CONSTRUCTION
roster (``split_role: discovery``), so a separated variant is a CANDIDATE for an out-of-fold
re-read, not a result.

REUSE
-----
Loaders are reused, not re-implemented: ``slurp_plan_bad_case_bank`` supplies the sealed-score,
delivered-output, phase-summary and gold loaders, the per-row entity decomposition that
reproduces the sealed ``slot_f1_exact_{tp,fp,fn}`` counts exactly, and the seven-class row
taxonomy; ``slurp_paired_roster_read`` supplies the shared interval block, the pooled micro-F1
field groups and the UTF-8/LF JSON writer; ``analysis.paired`` and ``analysis.null_calibration``
supply the estimators the recipe names.
"""

from __future__ import annotations

import argparse
import functools
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Sequence

REPO = Path(__file__).resolve().parents[2]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))
_ANALYSIS_DIR = str(Path(__file__).resolve().parent)
if _ANALYSIS_DIR not in sys.path:
    sys.path.insert(0, _ANALYSIS_DIR)

from speech_aware_evidence_acquisition.analysis.null_calibration import pooled_f1  # noqa: E402
from speech_aware_evidence_acquisition.analysis.paired import (  # noqa: E402
    paired_contrast,
    paired_contrast_bootstrap_tasks,
    resampled_statistic,
)
from speech_aware_evidence_acquisition.analysis.parallel import (  # noqa: E402
    add_workers_argument,
    map_by_key,
    resolve_workers,
)

import slurp_paired_roster_read as prr  # noqa: E402
import slurp_plan_bad_case_bank as bank  # noqa: E402

DRIVER_PATH = Path(__file__).resolve()

RECIPE_ID = "slurp-stage3-var1-construction-variant-read-v1"
OWN_NULL_RECIPE_ID = "slurp-stage3-var1-own-null-v1"
SCHEMA_STOP = "saea-slurp-var1-variant-read-stop-v1"
SCHEMA_OWN_NULL = "saea-slurp-var1-variant-read-own-null-v1"
SCHEMA_CONTRASTS = "saea-slurp-var1-variant-read-contrasts-v1"
SCHEMA_SLOT_TYPES = "saea-slurp-var1-variant-read-slot-types-v1"
SCHEMA_COVERAGE = "saea-slurp-var1-variant-read-coverage-v1"
SCHEMA_SCENARIO = "saea-slurp-var1-variant-read-per-scenario-v1"
SCHEMA_ADVANTAGE = "saea-slurp-var1-variant-read-advantage-v1"
SCHEMA_POLICY = "saea-slurp-var1-variant-read-policy-table-v1"
SCHEMA_COST = "saea-slurp-var1-variant-read-cost-v1"

OUT_DIRNAME = "SLURP-VAR1-VARIANT-READ-V1"
DEFAULT_PACKAGE = "docs/readiness/2026-09-24-slurp-stage3-var1-v1"
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_SEED = 20260915
DEFAULT_DRAWS = 10_000
DEFAULT_MIN_STATE_ROWS = 60
DEFAULT_SPLIT_ID = "train"

#: The registered VAR-1 arm set. ``plan`` is the comparator and ``planr`` its request-identical
#: replicate (the roster's own null, and the A/A control row of the variant table).
EXPECTED_ARMS = ("exdiv", "exk10", "exk30", "perk16c5", "plan", "planr")
COMPARATOR_ARM = "plan"
OWN_NULL_ARM = "planr"

#: The GROUP the group-relative advantage is taken over: the five DISTINCT constructions flown on
#: every row. ``planr`` is deliberately NOT a group member -- it is the same construction as
#: ``plan`` and would double-weight the plan form inside the group mean. Its advantage under the
#: substituted group is reported instead as the noise floor of the advantage quantity itself.
ADVANTAGE_GROUP = ("exdiv", "exk10", "exk30", "perk16c5", "plan")
ADVANTAGE_GROUP_REPLICATE = ("exdiv", "exk10", "exk30", "perk16c5", "planr")

CONTACTS_ZERO = {
    "asr": 0,
    "encoder": 0,
    "model": 0,
    "network": 0,
    "scorer": 0,
    "server": 0,
    "tokenizer": 0,
}

PENDING = "PENDING_SEAL"

#: The two pooled micro-F1 estimands, with the sealed count fields each is pooled from
#: (``slurp_paired_roster_read.MICRO_METRICS``, itself copied from the TRAIN Fold A precedent).
POOLED_METRICS: dict[str, str] = {
    "pooled_slu_f1": "slu_f1_micro",
    "span_f1": "span_f1_micro",
}
#: The two per-row estimands, in the order ``paired_contrast`` is handed them (its per-metric
#: seed offset is positional, so this order is part of the read's determinism).
ROW_METRICS: tuple[tuple[str, str], ...] = (
    ("intent_exact", "scenario_action_exact"),
    ("per_row_slu", "slu_f1_f1"),
)
#: Which own-null half-width each reported metric is read at.
MARGIN_OF = {
    "pooled_slu_f1": "h_slu",
    "span_f1": "h_slu",
    "per_row_slu": "h_slu",
    "intent_exact": "h_intent",
}

#: Context-only nulls, printed beside ``h_cross_r01c`` and never used as this family's bar.
CONTEXT_NULLS = {
    "h_within_roll_aa": {
        "h_slu": 0.735,
        "h_intent": 0.000,
        "n": 200,
        "roster": "SLURP-STAGE3-CONSTRUCTION-R01C subset (ROLL-AA)",
        "source": (
            "docs/results/2026-09-24-slurp-stage3-roll-aa-within-flight-null-read.md -- the "
            "WITHIN-flight A/A null: two request-identical arms inside one flight"
        ),
    },
    "h_train_fold_a": {
        "h_slu": 1.2485,
        "h_intent": 0.9943,
        "n": 1080,
        "roster": "TRAIN Fold A",
        "source": "registered-facts-v1.json comparator_context_only.train_fold_a_margins",
    },
    "h_dev_2000_added": {
        "h_slu": 1.2525,
        "h_intent": 1.1520,
        "n": 1000,
        "roster": "DEV-2000-ADDED",
        "source": "registered-facts-v1.json comparator_context_only.dev2000_added_margins",
    },
}

#: The five runtime-observable state keys the advantage is grouped by. Every one of them is
#: derived from the COMPARATOR arm's own runtime state or from the roster receipt -- never from
#: the variant's own episode, because a selector must be able to read the state BEFORE it picks a
#: construction, and VAR1-PER-K16C5 changes the candidate count itself.
STATE_KEYS = (
    "predicted_scenario",
    "candidate_count",
    "exemplar_top_agreement",
    "channel",
    "duration_tercile",
)

#: Fixed (never data-dependent) bands for the exemplar/candidate-1 intent agreement share.
AGREEMENT_BANDS = (
    (0.25, "agree-lt-0.25"),
    (0.50, "agree-0.25-0.50"),
    (0.75, "agree-0.50-0.75"),
)
AGREEMENT_TOP = "agree-ge-0.75"
AGREEMENT_NONE = "no-exemplars"

#: The per-row scores the advantage is taken on. ``per_row_slu`` is primary.
ADVANTAGE_SCORES = (("per_row_slu", "slu_f1_f1"), ("intent_exact", "scenario_action_exact"))

ARTEFACTS = (
    "stop.json",
    "own-null.json",
    "variant-contrasts.json",
    "slot-type-decomposition.json",
    "perception-coverage.json",
    "per-scenario.json",
    "group-relative-advantage.json",
    "policy-table.json",
    "cost.json",
    "README.md",
)


class Var1ReadError(RuntimeError):
    """This read refuses rather than report a number it cannot bind to sealed bytes.

    Every refusal names the arm and the byte that disagrees. Nothing is written when a stop-stage
    refusal fires.
    """


# --------------------------------------------------------------------------
# Small utilities (thin wrappers over the reused helpers, so the reuse is visible)
# --------------------------------------------------------------------------

digest = bank.digest
write_json = prr.write_json
interval_block = prr.interval_block
MICRO_METRICS = prr.MICRO_METRICS


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def content_sha256(path: Path) -> str:
    """The sha256 of an artefact's CONTENT -- its JSON re-serialised canonically with
    ``generated_at_utc`` removed.

    The stage chain binds on this rather than on the file's raw bytes so that two runs over the
    same sealed inputs agree exactly: a read is only reproducible if the thing that changes
    between two runs of it (the wall clock) is not fed back into the chain. The raw byte digest of
    any artefact beside it remains available to an auditor.
    """

    payload = dict(load_json(path))
    payload.pop("generated_at_utc", None)
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def mean(values: Sequence[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _bank(call: Callable, *args, **kwargs):
    """Run a reused ``slurp_plan_bad_case_bank`` loader, translating its ``BankError`` (a
    ``SystemExit`` subclass) into this module's own refusal type so every refusal this driver
    can emit is one exception class."""

    try:
        return call(*args, **kwargs)
    except bank.BankError as error:  # pragma: no cover - exercised through the refusal tests
        raise Var1ReadError(str(error)) from None


def _fmt(value, digits: int = 2, dash: str = "--") -> str:
    if value is None:
        return dash
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (int, float)):
        return f"{value:.{digits}f}"
    return str(value)


def _signed(value, digits: int = 2, dash: str = "--") -> str:
    if value is None:
        return dash
    return f"{value:+.{digits}f}"


def _is_hex64(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def load_gold(lock_path: Path, data_root: Path, split_id: str) -> dict:
    """The frozen gold of ``split_id``, through the study's own governed loader.

    A module-level seam on purpose: this is the one function in the read that touches the corpus,
    and the unit tests replace this NAME with a synthetic records mapping so no test ever reads a
    real byte of ``SPEECHRL_DATA_DIR``. Loaded ONCE per invocation and shared by all six arms --
    the governed loader re-verifies every recording against its flac header, which is the single
    slow step of this read.
    """

    return _bank(bank.gold_records, lock_path, data_root, split_id)


def load_exemplar_targets(data_root: Path, release_relpath: str, release_sha256: str) -> dict:
    """``value_id -> task_target`` for the pinned exemplar release.

    ``task_target`` IS the SLURP intent id of an exemplar value (registered facts
    ``store_facts.train_exemplars``), so the exemplar/candidate-1 agreement state key needs no
    part of a value's ``content`` and this loader never reads one.
    """

    release_path = data_root / release_relpath
    if not release_path.exists():
        raise Var1ReadError(f"pinned exemplar release missing: {release_path}")
    actual = digest(release_path)
    if actual != release_sha256:
        raise Var1ReadError(
            f"pinned exemplar release {release_relpath} hashes {actual} but the registered facts "
            f"pin {release_sha256}"
        )
    snapshot_path = release_path.parent / "snapshot.json"
    if not snapshot_path.exists():
        raise Var1ReadError(f"pinned exemplar snapshot missing: {snapshot_path}")
    document = load_json(snapshot_path)
    targets: dict[str, str] = {}
    for value in document.get("values") or ():
        value_id = value.get("value_id")
        if not isinstance(value_id, str) or not value_id:
            continue
        target = value.get("task_target")
        targets[value_id] = target if isinstance(target, str) and target else "<none>"
    if not targets:
        raise Var1ReadError(f"pinned exemplar snapshot {snapshot_path} carries no values")
    return {
        "release_relpath": release_relpath,
        "release_sha256": actual,
        "snapshot_relpath": str(Path(release_relpath).parent / "snapshot.json"),
        "snapshot_sha256": digest(snapshot_path),
        "declared_snapshot_sha256": document.get("snapshot_sha256"),
        "values": targets,
        "value_count": len(targets),
        "distinct_task_targets": len(set(targets.values())),
    }


# --------------------------------------------------------------------------
# Arms
# --------------------------------------------------------------------------


@dataclass
class Arm:
    """One sealed VAR-1 cell, resolved once."""

    key: str
    run_id: str
    attempt_id: str
    directory: Path
    manifest: dict
    scores: dict
    delivered: dict
    runtime: dict
    outputs_sha256: str
    generation_cost: dict
    generation_manifest_sha256: str
    flight_receipts: dict | None
    flight_receipts_sha256: str | None
    derived: dict = field(default_factory=dict)
    classes: dict = field(default_factory=dict)

    @property
    def rows_table(self) -> dict[str, dict[str, float]]:
        return self.scores["rows"]

    @property
    def rows(self) -> int:
        return len(self.manifest["ids"])


def _load_run_manifest(directory: Path, run_id: str, expected_split_hash: str) -> dict:
    """The sealed run manifest, with this read's own refusals.

    Deliberately NOT ``slurp_plan_bad_case_bank.load_manifest``: this read needs the manifest's
    own ``split.ids`` (the row-id coverage refusal) and its ``protocol_hash`` (the registered-hash
    refusal), and it wants every refusal to be a :class:`Var1ReadError` naming the disagreeing
    byte. The COMPLETED / dirty-tree / split-identity clauses are the same three the bank applies.
    """

    path = directory / f"{run_id}.run-manifest.json"
    if not path.exists():
        raise Var1ReadError(f"{run_id}: sealed run manifest missing at {path}")
    document = load_json(path)
    status = document.get("status")
    if status != "COMPLETED":
        raise Var1ReadError(
            f"{run_id}: manifest status is {status!r}, not COMPLETED -- this read never reads an "
            "unsealed or mid-flight run"
        )
    if document.get("study_repo_dirt"):
        raise Var1ReadError(f"{run_id}: sealed with a dirty study tree")
    split = document.get("split") or {}
    if split.get("identity_hash") != expected_split_hash:
        raise Var1ReadError(
            f"{run_id}: manifest split identity {split.get('identity_hash')} is not the roster's "
            f"{expected_split_hash}"
        )
    ids = split.get("ids")
    if not isinstance(ids, list) or not ids:
        raise Var1ReadError(f"{run_id}: manifest split carries no ids")
    if len(set(ids)) != len(ids):
        raise Var1ReadError(f"{run_id}: manifest split repeats a sample id")
    count = split.get("count")
    if count != len(ids):
        raise Var1ReadError(f"{run_id}: manifest split count {count} != {len(ids)} ids")
    scores_pin = document.get("scores") or {}
    scores_path = directory / f"{run_id}.scores.json"
    if not scores_path.exists():
        raise Var1ReadError(f"{run_id}: sealed scores missing at {scores_path}")
    scores_sha = digest(scores_path)
    if scores_pin.get("sha256") != scores_sha:
        raise Var1ReadError(
            f"{run_id}: manifest pins score bytes {scores_pin.get('sha256')} but the sealed file "
            f"hashes {scores_sha}"
        )
    config = document.get("config") or {}
    fragments = config.get("fragments") or {}
    experiment = fragments.get("experiment")
    if not isinstance(experiment, str) or not experiment:
        raise Var1ReadError(f"{run_id}: manifest names no experiment fragment")
    return {
        "path": str(path),
        "sha256": digest(path),
        "status": status,
        "study_commit": document.get("study_commit"),
        "config_hash": config.get("config_hash"),
        "protocol_hash": document.get("protocol_hash"),
        "experiment_fragment": experiment,
        "fragments": fragments,
        "split_role": split.get("role"),
        "split_count": count,
        "split_identity_hash": split.get("identity_hash"),
        "ids": sorted(ids),
        "scores_sha256": scores_sha,
    }


def load_arm(
    *,
    key: str,
    run_id: str,
    attempt_id: str,
    data_root: Path,
    roster: dict,
    scorer_id: str,
) -> Arm:
    directory = _bank(bank.arm_dir, data_root, run_id, attempt_id)
    manifest = _load_run_manifest(directory, run_id, roster["split_identity_hash"])
    ids = roster["ids"]
    scores = _bank(bank.load_scores, directory, run_id, scorer_id, ids)
    wanted = set(ids)
    delivered = _bank(bank.load_delivered, directory, run_id, wanted)
    runtime = _bank(bank.load_plan_runtime, directory, run_id, wanted)

    generation_path = directory / f"{run_id}.generation-manifest.json"
    if not generation_path.exists():
        raise Var1ReadError(f"{run_id}: sealed generation manifest missing at {generation_path}")
    generation = load_json(generation_path)
    receipts_path = directory / "flight-receipts.json"
    receipts = load_json(receipts_path) if receipts_path.exists() else None

    score_jobs_path = directory / "score-jobs.jsonl"
    if not score_jobs_path.exists():
        raise Var1ReadError(f"{run_id}: score-jobs.jsonl missing at {score_jobs_path}")
    jobs = [
        json.loads(line)
        for line in score_jobs_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(jobs) != 1:
        raise Var1ReadError(
            f"{run_id}: expected exactly one official scoring job (the recipe's "
            f"'once per complete manifest, never sharded'), found {len(jobs)}"
        )
    if jobs[0].get("job_id") != attempt_id:
        raise Var1ReadError(
            f"{run_id}: score job id {jobs[0].get('job_id')!r} != attempt {attempt_id!r}"
        )

    return Arm(
        key=key,
        run_id=run_id,
        attempt_id=attempt_id,
        directory=directory,
        manifest=manifest,
        scores=scores,
        delivered=delivered,
        runtime=runtime,
        outputs_sha256=delivered["sha256"],
        generation_cost=generation.get("cost") or {},
        generation_manifest_sha256=digest(generation_path),
        flight_receipts=receipts,
        flight_receipts_sha256=digest(receipts_path) if receipts is not None else None,
    )


# --------------------------------------------------------------------------
# Stage: stop -- the cross-checks the recipe requires
# --------------------------------------------------------------------------


def _arm_specs(recipe: dict, expect_arms: tuple[str, ...]) -> dict[str, dict]:
    arms = recipe.get("arms")
    if not isinstance(arms, dict) or not arms:
        raise Var1ReadError("analysis recipe carries no arms block")
    present = tuple(sorted(arms))
    if present != tuple(sorted(expect_arms)):
        raise Var1ReadError(
            f"analysis recipe arms {present} are not the expected family {tuple(sorted(expect_arms))}"
        )
    for name in (COMPARATOR_ARM, OWN_NULL_ARM):
        if name not in arms:
            raise Var1ReadError(f"analysis recipe has no {name!r} arm")
    comparator = (recipe.get("comparator") or {}).get("arm")
    if comparator != COMPARATOR_ARM:
        raise Var1ReadError(
            f"analysis recipe comparator arm is {comparator!r}, not {COMPARATOR_ARM!r}"
        )
    own_null = recipe.get("own_null") or {}
    if own_null.get("left") != arms[COMPARATOR_ARM].get("run_id"):
        raise Var1ReadError("analysis recipe own_null.left is not the comparator arm's run id")
    if own_null.get("right") != arms[OWN_NULL_ARM].get("run_id"):
        raise Var1ReadError("analysis recipe own_null.right is not the replicate arm's run id")
    specs: dict[str, dict] = {}
    for name, spec in sorted(arms.items()):
        run_id = spec.get("run_id")
        attempt_id = spec.get("attempt_id")
        if not isinstance(run_id, str) or not run_id:
            raise Var1ReadError(f"analysis recipe arm {name!r} carries no run_id")
        if not isinstance(attempt_id, str) or not attempt_id:
            raise Var1ReadError(f"analysis recipe arm {name!r} carries no attempt_id")
        specs[name] = dict(spec)
    return specs


def _check_registered_hashes(arm: Arm, recipe_arm: dict, facts: dict) -> dict:
    """Every pinned hash the registration carries, against the sealed bytes.

    Three families. (1) The recipe's own per-arm seal pins -- ``run_manifest_sha256``,
    ``scores_sha256``, ``outputs_sha256`` -- which are literal ``PENDING_SEAL`` in the registered
    package and are written by the coordinator after the seal; an unpinned value is RECORDED as
    unpinned, a pinned value that disagrees is a refusal. (2) The registered composed-config and
    protocol hashes of the arm's own identity, looked up by the sealed manifest's OWN experiment
    fragment name so the binding cannot be typed wrong. (3) The run id and attempt id.
    """

    if recipe_arm.get("run_id") != arm.run_id:
        raise Var1ReadError(
            f"{arm.key}: recipe run id {recipe_arm.get('run_id')!r} != loaded {arm.run_id!r}"
        )
    if recipe_arm.get("attempt_id") != arm.attempt_id:
        raise Var1ReadError(
            f"{arm.key}: recipe attempt id {recipe_arm.get('attempt_id')!r} != loaded "
            f"{arm.attempt_id!r}"
        )

    seal_pins = {
        "run_manifest_sha256": arm.manifest["sha256"],
        "scores_sha256": arm.manifest["scores_sha256"],
        "outputs_sha256": arm.outputs_sha256,
    }
    pinned: dict[str, object] = {}
    for name, actual in sorted(seal_pins.items()):
        declared = recipe_arm.get(name)
        if declared == PENDING or declared is None:
            pinned[name] = {"declared": PENDING, "actual": actual, "pinned": False}
            continue
        if declared != actual:
            raise Var1ReadError(
                f"{arm.key}: recipe pins {name} {declared} but the sealed bytes hash {actual}"
            )
        pinned[name] = {"declared": declared, "actual": actual, "pinned": True}

    fragment = arm.manifest["experiment_fragment"]
    registered = (facts.get("hashes") or {}).get(fragment)
    if not isinstance(registered, dict):
        raise Var1ReadError(
            f"{arm.key}: the registered facts carry no hashes for the sealed manifest's own "
            f"experiment fragment {fragment!r}"
        )
    for manifest_key, registered_key in (
        ("config_hash", "composed_config_hash"),
        ("protocol_hash", "protocol_hash"),
    ):
        declared = registered.get(registered_key)
        actual = arm.manifest[manifest_key]
        if declared != actual:
            raise Var1ReadError(
                f"{arm.key}: registered {registered_key} {declared} disagrees with the sealed "
                f"manifest {manifest_key} {actual}"
            )
    return {
        "experiment_fragment": fragment,
        "composed_config_hash": arm.manifest["config_hash"],
        "protocol_hash": arm.manifest["protocol_hash"],
        "seal_pins": pinned,
    }


def stage_stop(
    *,
    arms: dict[str, Arm],
    arm_specs: dict[str, dict],
    recipe: dict,
    recipe_sha256: str,
    facts: dict,
    facts_sha256: str,
    roster: dict,
    args: "Args",
    gold: dict,
    exemplars: dict,
) -> dict:
    """Refuse on any disagreement between the registration and the sealed bytes; write nothing on
    a refusal. On success, write and return ``stop.json``."""

    # --- the roster and the registration agree on the venue
    pins = facts.get("pins") or {}
    roster_pin = pins.get("roster") or {}
    if roster_pin.get("relpath") != args.roster_relpath:
        raise Var1ReadError(
            f"registered roster relpath {roster_pin.get('relpath')!r} != the read's "
            f"{args.roster_relpath!r}"
        )
    if roster_pin.get("sha256") != roster["sha256"]:
        raise Var1ReadError(
            f"roster {args.roster_relpath} hashes {roster['sha256']} but the registered facts pin "
            f"{roster_pin.get('sha256')}"
        )
    driver_block = recipe.get("driver") or {}
    if driver_block.get("roster") != args.roster_relpath:
        raise Var1ReadError(
            f"recipe driver.roster {driver_block.get('roster')!r} != the read's "
            f"{args.roster_relpath!r}"
        )
    population = facts.get("population") or {}
    for label, declared in (
        ("registered facts population.split_identity_hash", population.get("split_identity_hash")),
        ("recipe driver.split_identity_hash", driver_block.get("split_identity_hash")),
    ):
        if declared is None:
            continue
        if declared != roster["split_identity_hash"]:
            raise Var1ReadError(
                f"{label} {declared} != the roster receipt's {roster['split_identity_hash']}"
            )
    if population.get("rows") != len(roster["ids"]):
        raise Var1ReadError(
            f"registered facts population.rows {population.get('rows')} != the roster's "
            f"{len(roster['ids'])} items"
        )
    resampling = recipe.get("resampling") or {}
    if resampling.get("seed") != args.seed:
        raise Var1ReadError(
            f"recipe resampling.seed {resampling.get('seed')} != the read's seed {args.seed}"
        )
    if resampling.get("draws") != args.draws:
        raise Var1ReadError(
            f"recipe resampling.draws {resampling.get('draws')} != the read's draws {args.draws}"
        )
    if resampling.get("cluster_key") != args.cluster_key:
        raise Var1ReadError(
            f"recipe resampling.cluster_key {resampling.get('cluster_key')!r} != the read's "
            f"{args.cluster_key!r}"
        )
    scorer_block = recipe.get("scorer") or {}
    if scorer_block.get("id") != args.scorer_id:
        raise Var1ReadError(
            f"recipe scorer.id {scorer_block.get('id')!r} != the read's {args.scorer_id!r}"
        )
    if recipe.get("recipe_id") != RECIPE_ID:
        raise Var1ReadError(
            f"recipe_id {recipe.get('recipe_id')!r} is not this driver's {RECIPE_ID!r}"
        )

    # --- every arm covers exactly the roster's rows
    expected_ids = tuple(roster["ids"])
    coverage: dict[str, dict] = {}
    for key, arm in sorted(arms.items()):
        manifest_ids = tuple(arm.manifest["ids"])
        if manifest_ids != expected_ids:
            missing = sorted(set(expected_ids) - set(manifest_ids))
            extra = sorted(set(manifest_ids) - set(expected_ids))
            raise Var1ReadError(
                f"{key} ({arm.run_id}): the sealed split does not cover the roster's "
                f"{len(expected_ids)} row ids -- {len(missing)} missing, {len(extra)} extra "
                "(the six VAR-1 runs must be paired row for row)"
            )
        score_ids = tuple(sorted(arm.rows_table))
        if score_ids != expected_ids:
            raise Var1ReadError(
                f"{key} ({arm.run_id}): the sealed per-sample scores do not cover the roster's "
                f"row ids exactly"
            )
        coverage[key] = {
            "rows": len(manifest_ids),
            "split_role": arm.manifest["split_role"],
            "study_commit": arm.manifest["study_commit"],
        }

    # --- the registered hashes
    identities = {
        key: _check_registered_hashes(arm, arm_specs[key], facts)
        for key, arm in sorted(arms.items())
    }

    # --- the gold join is total and the roster's stratum IS the gold scenario
    scenario_disagreements = 0
    for sample_id in roster["ids"]:
        record = gold["records"].get(sample_id)
        if record is None:
            raise Var1ReadError(f"gold is missing roster row {sample_id!r}")
        if roster["stratum"][sample_id] != record.scenario:
            scenario_disagreements += 1
    if scenario_disagreements:
        raise Var1ReadError(
            f"{scenario_disagreements} roster items carry a stratum that is not the row's gold "
            "scenario -- the gold per-scenario table would be keyed on the wrong label"
        )

    payload = {
        "schema": SCHEMA_STOP,
        "recipe_id": RECIPE_ID,
        "contacts": dict(CONTACTS_ZERO),
        "generated_at_utc": args.now,
        "driver_sha256": digest(DRIVER_PATH),
        "reused_loaders": {
            "slurp_plan_bad_case_bank": digest(Path(bank.__file__).resolve()),
            "slurp_paired_roster_read": digest(Path(prr.__file__).resolve()),
        },
        "package": {
            "analysis_recipe_sha256": recipe_sha256,
            "registered_facts_sha256": facts_sha256,
            "relpath": args.package_relpath,
        },
        "roster": {
            "relpath": args.roster_relpath,
            "sha256": roster["sha256"],
            "roster_id": roster["roster_id"],
            "split_role": roster["split_role"],
            "split_identity_hash": roster["split_identity_hash"],
            "rows": len(roster["ids"]),
            "distinct_clusters": len(set(roster["cluster"].values())),
            "strata": {name: count for name, count in sorted(roster["strata_counts"].items())},
            "channel_counts": {
                name: count for name, count in sorted(Counter(roster["channel"].values()).items())
            },
        },
        "gold": {
            "split_id": args.split_id,
            "metadata_sha256": gold["metadata_sha256"],
            "roster_stratum_equals_gold_scenario": True,
        },
        "exemplar_store": {
            key: value for key, value in exemplars.items() if key != "values"
        },
        "arms": {
            key: {
                "run_id": arm.run_id,
                "attempt_id": arm.attempt_id,
                "outputs_sha256": arm.outputs_sha256,
                "phases_sha256": arm.runtime["sha256"],
                "run_manifest_sha256": arm.manifest["sha256"],
                "scores_sha256": arm.manifest["scores_sha256"],
                "generation_manifest_sha256": arm.generation_manifest_sha256,
                "flight_receipts_sha256": arm.flight_receipts_sha256,
                "controller_policy_id": arm.runtime["controller_policy_id"],
                "candidate_parse_failures": arm.runtime["candidate_parse_failures"],
                "official": arm.scores["official"],
                **coverage[key],
                **identities[key],
            }
            for key, arm in sorted(arms.items())
        },
        "estimators": recipe.get("estimators"),
        "resampling": {
            "cluster_key": args.cluster_key,
            "draws": args.draws,
            "seed": args.seed,
            "interval_form": "percentile pairs of the same retained replicate sequence",
        },
        "claim_boundary": recipe.get("claim_boundary"),
    }
    write_json(args.out_root / "stop.json", payload)
    return payload


# --------------------------------------------------------------------------
# Estimators
# --------------------------------------------------------------------------


def _pooled_statistic(
    left: Mapping[str, Mapping[str, float]],
    right: Mapping[str, Mapping[str, float]],
    groups,
) -> Callable[[Sequence[str]], float]:
    """The pooled-count-F1 difference, as ``resampled_statistic`` consumes it."""

    def statistic(resampled: Sequence[str]) -> float:
        return pooled_f1(right, resampled, groups) - pooled_f1(left, resampled, groups)

    return statistic


def _contrast_tasks(
    left: Arm,
    right: Arm,
    ids: Sequence[str],
    *,
    cluster_of: Callable[[str], str],
    seed: int,
    draws: int,
    prefix: str,
) -> dict[str, Callable[[], object]]:
    """One arm pair's FOUR bootstraps, as four independent zero-argument tasks.

    Each is 10,000 draws over the roster and each seeds its own
    ``random.Random``, so the four -- and the four of every other arm pair --
    are mutually independent and may run in any order, in any process. The
    keys are ``<prefix>|pooled|<estimand>`` and ``<prefix>|row|<sealed
    field>``, which is what makes the collected mapping sorted and reviewable.

    The per-row seed offsets are NOT reconstructed here: they come from
    ``analysis.paired.paired_contrast_bootstrap_tasks``, the one place that
    owns the ``seed + position-in-metrics`` convention, so the tasks cannot
    drift from the ``paired_contrast`` call that consumes them.
    """

    tasks: dict[str, Callable[[], object]] = {}
    for name, group_key in sorted(POOLED_METRICS.items()):
        tasks[f"{prefix}|pooled|{name}"] = functools.partial(
            resampled_statistic,
            sample_ids=ids,
            statistic=_pooled_statistic(
                left.rows_table, right.rows_table, MICRO_METRICS[group_key]
            ),
            seed=seed,
            n_replicates=draws,
            ci_level=0.95,
            cluster_of=cluster_of,
        )
    for field_name, task in paired_contrast_bootstrap_tasks(
        left.rows_table,
        right.rows_table,
        metrics=[field_name for _, field_name in ROW_METRICS],
        sample_ids=ids,
        cluster_of=cluster_of,
        seed=seed,
        n_replicates=draws,
        ci_level=0.95,
    ).items():
        tasks[f"{prefix}|row|{field_name}"] = task
    return tasks


def _contrast(
    left: Arm,
    right: Arm,
    ids: Sequence[str],
    *,
    cluster_of: Callable[[str], str],
    seed: int,
    draws: int,
    prefix: str,
    bootstraps: Mapping[str, object],
) -> dict:
    """One arm pair's four reported estimands -- two pooled micro-F1 and two per-row means.

    ``bootstraps`` is the collected result of this pair's own
    :func:`_contrast_tasks`, so this function does no resampling at all: it
    reads point estimates and replicate sequences that are already computed
    and turns them into the reported blocks.
    """

    metrics: dict[str, dict] = {}
    for name, group_key in sorted(POOLED_METRICS.items()):
        groups = MICRO_METRICS[group_key]
        result = bootstraps[f"{prefix}|pooled|{name}"]
        metrics[name] = {
            "estimand": "pooled count F1",
            "left_pct": 100 * pooled_f1(left.rows_table, ids, groups),
            "right_pct": 100 * pooled_f1(right.rows_table, ids, groups),
            "delta_pp": 100 * result.point_estimate,
            "cluster_bootstrap": interval_block(
                result.replicates, result.point_estimate, seed
            ),
        }
    contrasts = paired_contrast(
        left.rows_table,
        right.rows_table,
        metrics=[field_name for _, field_name in ROW_METRICS],
        sample_ids=ids,
        cluster_of=cluster_of,
        seed=seed,
        n_replicates=draws,
        ci_level=0.95,
        bootstraps={
            field_name: bootstraps[f"{prefix}|row|{field_name}"]
            for _, field_name in ROW_METRICS
        },
    )
    for name, field_name in ROW_METRICS:
        contrast = contrasts[field_name]
        entry: dict[str, object] = {
            "estimand": "mean-per-row",
            "sealed_field": field_name,
            "n": contrast.n,
            "left_pct": 100 * contrast.left_mean,
            "right_pct": 100 * contrast.right_mean,
            "delta_pp": 100 * contrast.delta,
            "saves": contrast.saves,
            "harms": contrast.harms,
            "ties": contrast.ties,
            "mcnemar_p": contrast.sign_test_p,
        }
        if contrast.bootstrap is not None:
            entry["cluster_bootstrap"] = interval_block(
                contrast.bootstrap.replicates, contrast.bootstrap.point_estimate, seed
            )
        metrics[name] = entry
    # The pooled rows borrow the row-level win/loss counts of the same metric family, so the
    # variant table can print saves / harms / ties beside a pooled estimand honestly labelled.
    metrics["pooled_slu_f1"]["row_level_counts_from"] = "per_row_slu"
    metrics["span_f1"]["row_level_counts_from"] = "per_row_slu"
    for name in ("pooled_slu_f1", "span_f1"):
        for count in ("saves", "harms", "ties", "mcnemar_p"):
            metrics[name][count] = metrics["per_row_slu"][count]
    return metrics


def _flagged(metrics: dict, own_null: dict) -> dict:
    """Attach the two reading flags the decision rule needs to every metric."""

    out: dict[str, dict] = {}
    for name, entry in sorted(metrics.items()):
        block = dict(entry)
        bootstrap = entry.get("cluster_bootstrap") or {}
        low, high = (bootstrap.get("ci95_pp") or [None, None])[:2]
        margin_key = MARGIN_OF[name]
        margin = own_null["h_cross_r01c"][margin_key]
        point = entry["delta_pp"]
        ci95_excludes_zero = None
        if low is not None and high is not None:
            ci95_excludes_zero = low > 0.0 or high < 0.0
        block["read_flags"] = {
            "margin_key": margin_key,
            "h_cross_r01c_pp": margin,
            "ci95_lower_above_zero": None if low is None else low > 0.0,
            "ci95_excludes_zero": ci95_excludes_zero,
            "point_estimate_outside_margin": abs(point) > margin,
            "separated_from_null": bool(ci95_excludes_zero) and abs(point) > margin,
        }
        out[name] = block
    return out


def stage_own_null(
    *, arms: dict[str, Arm], roster: dict, args: "Args", stop_sha256: str
) -> dict:
    """The R01C own null -- VAR1-PLAN against VAR1-PLANR. READ FIRST, sealed before any variant
    contrast, never adjusted afterwards."""

    ids = roster["ids"]
    cluster_of = roster["cluster"].__getitem__
    tasks = _contrast_tasks(
        arms[COMPARATOR_ARM],
        arms[OWN_NULL_ARM],
        ids,
        cluster_of=cluster_of,
        seed=args.seed,
        draws=args.draws,
        prefix=OWN_NULL_ARM,
    )
    # The own null is READ FIRST and sealed before any variant contrast, so its
    # bootstraps are their own fan-out rather than part of the variant batch.
    metrics = _contrast(
        arms[COMPARATOR_ARM],
        arms[OWN_NULL_ARM],
        ids,
        cluster_of=cluster_of,
        seed=args.seed,
        draws=args.draws,
        prefix=OWN_NULL_ARM,
        bootstraps=map_by_key(
            tasks, workers=resolve_workers(args.workers, cap=len(tasks))
        ),
    )
    h_slu = metrics["pooled_slu_f1"]["cluster_bootstrap"]["ci95_half_width_pp"]
    h_intent = metrics["intent_exact"]["cluster_bootstrap"]["ci95_half_width_pp"]
    payload = {
        "schema": SCHEMA_OWN_NULL,
        "recipe_id": OWN_NULL_RECIPE_ID,
        "root_id": "SAEA-SLURP-STAGE3-VAR1-OWN-NULL-V1",
        "contacts": dict(CONTACTS_ZERO),
        "generated_at_utc": args.now,
        "order": (
            "READ FIRST. h_cross_r01c is sealed before any variant contrast is read and is never "
            "adjusted afterwards."
        ),
        "left": {"arm": COMPARATOR_ARM, "run_id": arms[COMPARATOR_ARM].run_id},
        "right": {"arm": OWN_NULL_ARM, "run_id": arms[OWN_NULL_ARM].run_id},
        "n": len(ids),
        "distinct_clusters": len(set(roster["cluster"].values())),
        "h_cross_r01c": {
            "h_slu": h_slu,
            "h_intent": h_intent,
            "kind": "CROSS-FLIGHT A/A on R01C: two separate flights of one request-identical form",
            "estimator": "paired whole-cluster bootstrap, CI95 half-width, 10,000 draws",
        },
        "context_only_nulls": CONTEXT_NULLS,
        "decomposition_note": (
            "h_cross_r01c is a BETWEEN-flight quantity. h_within (ROLL-AA) is the WITHIN-flight "
            "A/A null of the same form, 0.735 pp SLU and 0.000 pp intent at n = 200, so the part "
            "of h_cross_r01c above h_within is flight-to-flight diffuseness, not per-row noise."
        ),
        "metrics": metrics,
        "inputs_sha256": {"stop_content": stop_sha256},
        "driver_sha256": digest(DRIVER_PATH),
    }
    write_json(args.out_root / "own-null.json", payload)
    return payload


def stage_variants(
    *, arms: dict[str, Arm], roster: dict, args: "Args", own_null: dict
) -> dict:
    """Every non-comparator arm against VAR1-PLAN, read at the sealed margin.

    REFUSES if ``own-null.json`` is not already on disk: the margin table is part of the
    registration's order and the variant table is derived from it, not beside it.
    """

    own_null_path = args.out_root / "own-null.json"
    if not own_null_path.exists():
        raise Var1ReadError(
            "the own-null artefact is not sealed: the R01C margin table is READ FIRST and the "
            "variant table is never computed before it"
        )
    ids = roster["ids"]
    cluster_of = roster["cluster"].__getitem__
    variant_keys = tuple(key for key in sorted(arms) if key != COMPARATOR_ARM)
    # Every variant's four bootstraps in ONE flat batch: five arms x four
    # estimands is twenty independent units, and batching them flat keeps the
    # workers busy to the last unit instead of draining one arm at a time.
    tasks: dict[str, Callable[[], object]] = {}
    for key in variant_keys:
        tasks.update(
            _contrast_tasks(
                arms[COMPARATOR_ARM],
                arms[key],
                ids,
                cluster_of=cluster_of,
                seed=args.seed,
                draws=args.draws,
                prefix=key,
            )
        )
    bootstraps = map_by_key(tasks, workers=resolve_workers(args.workers, cap=len(tasks)))
    variants: dict[str, dict] = {}
    for key in variant_keys:
        metrics = _contrast(
            arms[COMPARATOR_ARM],
            arms[key],
            ids,
            cluster_of=cluster_of,
            seed=args.seed,
            draws=args.draws,
            prefix=key,
            bootstraps=bootstraps,
        )
        variants[key] = {
            "run_id": arms[key].run_id,
            "role": (
                "A/A control row (same construction as the comparator)"
                if key == OWN_NULL_ARM
                else "construction variant"
            ),
            "official": arms[key].scores["official"],
            "metrics": _flagged(metrics, own_null),
        }
    payload = {
        "schema": SCHEMA_CONTRASTS,
        "recipe_id": RECIPE_ID,
        "contacts": dict(CONTACTS_ZERO),
        "generated_at_utc": args.now,
        "delta_convention": "delta = variant minus VAR1-PLAN, in percentage points; negative is worse",
        "comparator": {"arm": COMPARATOR_ARM, "run_id": arms[COMPARATOR_ARM].run_id,
                       "official": arms[COMPARATOR_ARM].scores["official"]},
        "margins": own_null["h_cross_r01c"],
        "reading_rule": (
            "SEPARATED FROM THE NULL = the CI95 excludes zero AND the point estimate lies outside "
            "+-h_cross_r01c. Anything else is INSIDE THE NULL. No ADMITTED / NEUTRAL / HARMFUL "
            "label is attached to any VAR-1 cell."
        ),
        "variants": variants,
        "inputs_sha256": {"own_null_content": content_sha256(own_null_path)},
        "driver_sha256": digest(DRIVER_PATH),
    }
    write_json(args.out_root / "variant-contrasts.json", payload)
    return payload


# --------------------------------------------------------------------------
# Stage: entity FP / FN by slot TYPE
# --------------------------------------------------------------------------


def _slot_type_mass(arm: Arm, ids: Sequence[str]) -> dict:
    """Per-slot-TYPE FP and FN mass, asserted against the arm's sealed official totals."""

    fp: Counter = Counter()
    fn: Counter = Counter()
    tp: Counter = Counter()
    omission: Counter = Counter()
    over_emission: Counter = Counter()
    same_type = 0
    type_swap = 0
    empty_gold_rows = 0
    empty_gold_emitting = 0
    for sample_id in ids:
        view = arm.derived[sample_id]
        for name, target in (("tp", tp), ("fp", fp), ("fn", fn)):
            for slot_type, count in view["per_type"][name].items():
                target[slot_type] += count
        for slot_type, count in view["omission"].items():
            omission[slot_type] += count
        for slot_type, count in view["over_emission"].items():
            over_emission[slot_type] += count
        same_type += len(view["same_type"])
        type_swap += len(view["type_swap"])
        if view["gold_entity_count"] == 0:
            empty_gold_rows += 1
            if arm.delivered["rows"][sample_id]["entity_count"] > 0:
                empty_gold_emitting += 1

    sealed = {
        "slot_f1_exact_tp": sum(arm.rows_table[sid]["slot_f1_exact_tp"] for sid in ids),
        "slot_f1_exact_fp": sum(arm.rows_table[sid]["slot_f1_exact_fp"] for sid in ids),
        "slot_f1_exact_fn": sum(arm.rows_table[sid]["slot_f1_exact_fn"] for sid in ids),
    }
    derived_totals = {
        "slot_f1_exact_tp": sum(tp.values()),
        "slot_f1_exact_fp": sum(fp.values()),
        "slot_f1_exact_fn": sum(fn.values()),
    }
    for name, value in sorted(derived_totals.items()):
        if abs(value - sealed[name]) > 1e-9:
            raise Var1ReadError(
                f"{arm.key} ({arm.run_id}): the per-TYPE decomposition totals {name}={value} but "
                f"the sealed official rows total {sealed[name]}"
            )
    return {
        "run_id": arm.run_id,
        "sealed_totals": sealed,
        "derived_totals": derived_totals,
        "reproduces_sealed_totals": True,
        "per_type": {
            slot_type: {
                "tp": tp.get(slot_type, 0),
                "fp": fp.get(slot_type, 0),
                "fn": fn.get(slot_type, 0),
                "omission": omission.get(slot_type, 0),
                "over_emission": over_emission.get(slot_type, 0),
            }
            for slot_type in sorted(set(tp) | set(fp) | set(fn))
        },
        "unmatched_attribution": {
            "same_type_wrong_filler": same_type,
            "type_swap": type_swap,
            "omission_total": sum(omission.values()),
            "over_emission_total": sum(over_emission.values()),
        },
        "empty_gold_rows": empty_gold_rows,
        "empty_gold_emitting_rows": empty_gold_emitting,
        "empty_gold_emission_rate_pct": (
            100.0 * empty_gold_emitting / empty_gold_rows if empty_gold_rows else 0.0
        ),
    }


def stage_slot_types(*, arms: dict[str, Arm], roster: dict, args: "Args") -> dict:
    ids = roster["ids"]
    per_arm = {key: _slot_type_mass(arm, ids) for key, arm in sorted(arms.items())}
    base = per_arm[COMPARATOR_ARM]
    deltas: dict[str, dict] = {}
    for key, entry in sorted(per_arm.items()):
        if key == COMPARATOR_ARM:
            continue
        types = sorted(set(entry["per_type"]) | set(base["per_type"]))
        deltas[key] = {
            "per_type": {
                slot_type: {
                    "fp": entry["per_type"].get(slot_type, {}).get("fp", 0)
                    - base["per_type"].get(slot_type, {}).get("fp", 0),
                    "fn": entry["per_type"].get(slot_type, {}).get("fn", 0)
                    - base["per_type"].get(slot_type, {}).get("fn", 0),
                }
                for slot_type in types
            },
            "fp_total": entry["derived_totals"]["slot_f1_exact_fp"]
            - base["derived_totals"]["slot_f1_exact_fp"],
            "fn_total": entry["derived_totals"]["slot_f1_exact_fn"]
            - base["derived_totals"]["slot_f1_exact_fn"],
            "empty_gold_emission_rate_pp": entry["empty_gold_emission_rate_pct"]
            - base["empty_gold_emission_rate_pct"],
        }
    payload = {
        "schema": SCHEMA_SLOT_TYPES,
        "recipe_id": RECIPE_ID,
        "contacts": dict(CONTACTS_ZERO),
        "generated_at_utc": args.now,
        "matcher": (
            "the official exact (type, filler) matcher, so per_type tp/fp/fn reproduces each "
            "run's sealed slot_f1_exact_{tp,fp,fn} totals; the unmatched remainder is then "
            "attributed to same-type / type-swap / over-emission / omission"
        ),
        "per_arm": per_arm,
        "delta_vs_comparator": deltas,
        "driver_sha256": digest(DRIVER_PATH),
    }
    write_json(args.out_root / "slot-type-decomposition.json", payload)
    return payload


# --------------------------------------------------------------------------
# Stage: Perception candidate coverage
# --------------------------------------------------------------------------


def stage_coverage(*, arms: dict[str, Arm], roster: dict, args: "Args") -> dict:
    ids = roster["ids"]
    per_arm: dict[str, dict] = {}
    for key, arm in sorted(arms.items()):
        covered_union = 0
        covered_first = 0
        widths: Counter = Counter()
        distinct_ok = 0
        empty_lists = 0
        rank_hist: Counter = Counter()
        for sample_id in ids:
            state = arm.runtime["rows"][sample_id]
            gold_intent = arm.derived[sample_id]["gold_intent"]
            first = state["candidates_first"]
            union = state["candidates_union"]
            if gold_intent in union:
                covered_union += 1
            if gold_intent in first:
                covered_first += 1
                rank_hist[first.index(gold_intent) + 1] += 1
            else:
                rank_hist[0] += 1
            widths[state["candidate_width"]] += 1
            if len(first) == len(set(first)):
                distinct_ok += 1
            if not first:
                empty_lists += 1
        classes = Counter(arm.classes["classes"][sample_id] for sample_id in ids)
        per_arm[key] = {
            "run_id": arm.run_id,
            "rows": len(ids),
            "gold_intent_in_candidate_union_rate_pct": 100.0 * covered_union / len(ids),
            "gold_intent_in_first_list_rate_pct": 100.0 * covered_first / len(ids),
            "candidate_width_histogram": {str(k): v for k, v in sorted(widths.items())},
            "mean_candidate_width": mean(
                [arm.runtime["rows"][sid]["candidate_width"] for sid in ids]
            ),
            "distinct_candidate_ids_rate_pct": 100.0 * distinct_ok / len(ids),
            "empty_candidate_list_rows": empty_lists,
            "gold_intent_rank_histogram": {str(k): v for k, v in sorted(rank_hist.items())},
            "taxonomy": {name: classes.get(name, 0) for name in bank.CLASSES},
            "intent_uncovered": classes.get("INTENT-UNCOVERED", 0),
            "intent_covered": classes.get("INTENT-COVERED", 0),
        }
    base = per_arm[COMPARATOR_ARM]
    deltas = {
        key: {
            "coverage_union_pp": entry["gold_intent_in_candidate_union_rate_pct"]
            - base["gold_intent_in_candidate_union_rate_pct"],
            "coverage_first_pp": entry["gold_intent_in_first_list_rate_pct"]
            - base["gold_intent_in_first_list_rate_pct"],
            "intent_uncovered_delta": entry["intent_uncovered"] - base["intent_uncovered"],
            "intent_covered_delta": entry["intent_covered"] - base["intent_covered"],
            "mean_candidate_width_delta": entry["mean_candidate_width"]
            - base["mean_candidate_width"],
        }
        for key, entry in sorted(per_arm.items())
        if key != COMPARATOR_ARM
    }
    payload = {
        "schema": SCHEMA_COVERAGE,
        "recipe_id": RECIPE_ID,
        "contacts": dict(CONTACTS_ZERO),
        "generated_at_utc": args.now,
        "join": (
            "gold intent joined OFFLINE onto the sealed Perception receipts. The primary rate is "
            "the candidate UNION over the row's Perception states (the list the taxonomy's "
            "INTENT-COVERED / INTENT-UNCOVERED classes use); the first-list rate and the gold "
            "intent's rank in that list are reported beside it."
        ),
        "taxonomy_order": list(bank.CLASSES),
        "per_arm": per_arm,
        "delta_vs_comparator": deltas,
        "driver_sha256": digest(DRIVER_PATH),
    }
    write_json(args.out_root / "perception-coverage.json", payload)
    return payload


# --------------------------------------------------------------------------
# Stage: gold per-scenario table
# --------------------------------------------------------------------------


def stage_per_scenario(*, arms: dict[str, Arm], roster: dict, args: "Args") -> dict:
    by_scenario: dict[str, list[str]] = defaultdict(list)
    for sample_id in roster["ids"]:
        by_scenario[roster["stratum"][sample_id]].append(sample_id)
    scenarios = sorted(by_scenario)
    base = arms[COMPARATOR_ARM]
    per_variant: dict[str, dict] = {}
    for key, arm in sorted(arms.items()):
        if key == COMPARATOR_ARM:
            continue
        cells: dict[str, dict] = {}
        for scenario in scenarios:
            members = sorted(by_scenario[scenario])
            left_slu = 100 * pooled_f1(base.rows_table, members, MICRO_METRICS["slu_f1_micro"])
            right_slu = 100 * pooled_f1(arm.rows_table, members, MICRO_METRICS["slu_f1_micro"])
            left_intent = 100 * mean(
                [base.rows_table[sid]["scenario_action_exact"] for sid in members]
            )
            right_intent = 100 * mean(
                [arm.rows_table[sid]["scenario_action_exact"] for sid in members]
            )
            cells[scenario] = {
                "n": len(members),
                "left_slu_pct": left_slu,
                "right_slu_pct": right_slu,
                "slu_delta_pp": right_slu - left_slu,
                "left_intent_pct": left_intent,
                "right_intent_pct": right_intent,
                "intent_delta_pp": right_intent - left_intent,
            }
        all_ids = roster["ids"]
        natural_slu = 100 * (
            pooled_f1(arm.rows_table, all_ids, MICRO_METRICS["slu_f1_micro"])
            - pooled_f1(base.rows_table, all_ids, MICRO_METRICS["slu_f1_micro"])
        )
        natural_intent = 100 * (
            mean([arm.rows_table[sid]["scenario_action_exact"] for sid in all_ids])
            - mean([base.rows_table[sid]["scenario_action_exact"] for sid in all_ids])
        )
        per_variant[key] = {
            "run_id": arm.run_id,
            "per_scenario": cells,
            "weightings": {
                "natural_mixture": {
                    "slu_delta_pp": natural_slu,
                    "intent_delta_pp": natural_intent,
                    "definition": "pooled over all roster rows in their own mixture",
                },
                "equal_scenario": {
                    "slu_delta_pp": mean([cells[s]["slu_delta_pp"] for s in scenarios]),
                    "intent_delta_pp": mean([cells[s]["intent_delta_pp"] for s in scenarios]),
                    "definition": "unweighted mean of the per-scenario deltas over the strata",
                },
            },
        }
    payload = {
        "schema": SCHEMA_SCENARIO,
        "recipe_id": RECIPE_ID,
        "contacts": dict(CONTACTS_ZERO),
        "generated_at_utc": args.now,
        "availability": (
            "AVAILABLE on R01C: the roster receipt carries a per-item stratum and that stratum is "
            "verified row by row to equal the gold scenario, so the table is derivable offline "
            "with no gold at runtime. DEV-2000-ADDED withheld it."
        ),
        "diagnostic_only": "descriptive; no CI and no per-scenario reading clause",
        "scenarios": scenarios,
        "row_counts": {scenario: len(by_scenario[scenario]) for scenario in scenarios},
        "per_variant": per_variant,
        "driver_sha256": digest(DRIVER_PATH),
    }
    write_json(args.out_root / "per-scenario.json", payload)
    return payload


# --------------------------------------------------------------------------
# Stage: group-relative advantage per runtime-observable state
# --------------------------------------------------------------------------


def _agreement_bucket(share: float, has_exemplars: bool) -> str:
    if not has_exemplars:
        return AGREEMENT_NONE
    for edge, name in AGREEMENT_BANDS:
        if share < edge:
            return name
    return AGREEMENT_TOP


def _predicted_scenario(state: dict) -> str:
    names = [cid.split("_", 1)[0] for cid in state["candidates_first"] if "_" in cid]
    if not names:
        return "<none>"
    counts = Counter(names)
    top = max(counts.values())
    return sorted(name for name, count in counts.items() if count == top)[0]


def _duration_terciles(roster: dict) -> dict[str, str]:
    """Contiguous terciles of the roster's own ``audio_seconds``, ordered by (seconds, id) so the
    banding is deterministic and independent of any score."""

    order = sorted(roster["ids"], key=lambda sid: (roster["audio_seconds"][sid], sid))
    total = len(order)
    names = ("duration-t1-short", "duration-t2-mid", "duration-t3-long")
    return {sid: names[min(2, (index * 3) // total)] for index, sid in enumerate(order)}


def build_states(*, comparator: Arm, roster: dict, exemplars: dict) -> dict[str, dict[str, str]]:
    """``state_key -> {sample_id -> cell}``, every cell runtime-observable and taken from the
    COMPARATOR arm or the roster receipt only."""

    terciles = _duration_terciles(roster)
    states: dict[str, dict[str, str]] = {key: {} for key in STATE_KEYS}
    for sample_id in roster["ids"]:
        state = comparator.runtime["rows"][sample_id]
        first = state["candidates_first"]
        top = first[0] if first else None
        supplied = state["supplied"].get(bank.EXEMPLAR_STORE) or []
        labels = [exemplars["values"].get(value_id) for value_id in supplied]
        labels = [label for label in labels if label is not None]
        share = mean([1.0 if label == top else 0.0 for label in labels]) if labels else 0.0
        states["predicted_scenario"][sample_id] = _predicted_scenario(state)
        states["candidate_count"][sample_id] = f"candidates-{state['candidate_width']}"
        states["exemplar_top_agreement"][sample_id] = _agreement_bucket(share, bool(labels))
        states["channel"][sample_id] = roster["channel"][sample_id]
        states["duration_tercile"][sample_id] = terciles[sample_id]
    return states


def _advantages(
    *, arms: dict[str, Arm], ids: Sequence[str], group: Sequence[str], field_name: str
) -> dict[str, dict[str, float]]:
    """``arm -> {sample_id -> advantage}``: the per-row score minus the mean over ``group`` on
    that row (the GRPO-style group-relative quantity), in percentage points."""

    out: dict[str, dict[str, float]] = {key: {} for key in arms}
    for sample_id in ids:
        scores = {key: arm.rows_table[sample_id][field_name] for key, arm in arms.items()}
        baseline = mean([scores[key] for key in group])
        for key, value in scores.items():
            out[key][sample_id] = 100.0 * (value - baseline)
    return out


def _leave_one_scenario_out(
    *, members: Sequence[str], advantage: Mapping[str, float], scenario_of: Mapping[str, str]
) -> dict:
    """Recompute the cell's mean advantage once per scenario present in the cell, each time with
    that scenario's rows dropped, and report whether the SIGN survived every drop."""

    full = mean([advantage[sid] for sid in members])
    present = sorted({scenario_of[sid] for sid in members})
    values: list[float] = []
    empty_drops: list[str] = []
    for scenario in present:
        kept = [sid for sid in members if scenario_of[sid] != scenario]
        if not kept:
            empty_drops.append(scenario)
            continue
        values.append(mean([advantage[sid] for sid in kept]))
    if not values or empty_drops:
        return {
            "full_mean_pp": full,
            "scenarios_present": len(present),
            "min_pp": None,
            "max_pp": None,
            "sign_stable": False,
            "reason": "a leave-one-scenario-out subset is empty" if empty_drops else "no drop possible",
        }
    if full > 0:
        stable = all(value > 0 for value in values)
    elif full < 0:
        stable = all(value < 0 for value in values)
    else:
        stable = False
    return {
        "full_mean_pp": full,
        "scenarios_present": len(present),
        "min_pp": min(values),
        "max_pp": max(values),
        "sign_stable": stable,
        "reason": None if stable else "the sign flips when a scenario is dropped",
    }


def stage_advantage(
    *, arms: dict[str, Arm], roster: dict, states: dict[str, dict[str, str]], args: "Args"
) -> tuple[dict, dict]:
    ids = roster["ids"]
    scenario_of = roster["stratum"]
    group = tuple(key for key in ADVANTAGE_GROUP if key in arms)
    group_replicate = tuple(key for key in ADVANTAGE_GROUP_REPLICATE if key in arms)
    if COMPARATOR_ARM not in group:
        raise Var1ReadError("the advantage group must contain the comparator arm")

    blocks: dict[str, dict] = {}
    policy_rows: list[dict] = []
    for score_name, field_name in ADVANTAGE_SCORES:
        advantage = _advantages(arms=arms, ids=ids, group=group, field_name=field_name)
        advantage_r = _advantages(
            arms=arms, ids=ids, group=group_replicate, field_name=field_name
        )
        per_state: dict[str, dict] = {}
        for state_key in STATE_KEYS:
            cells: dict[str, list[str]] = defaultdict(list)
            for sample_id in ids:
                cells[states[state_key][sample_id]].append(sample_id)
            state_block: dict[str, dict] = {}
            for cell, members in sorted(cells.items()):
                members = sorted(members)
                means = {
                    key: mean([advantage[key][sid] for sid in members]) for key in sorted(group)
                }
                best = sorted(means.items(), key=lambda item: (-item[1], item[0]))[0][0]
                loo = _leave_one_scenario_out(
                    members=members, advantage=advantage[best], scenario_of=scenario_of
                )
                enough_rows = len(members) >= args.min_state_rows
                reportable = enough_rows and loo["sign_stable"]
                reasons: list[str] = []
                if not enough_rows:
                    reasons.append(f"cell holds {len(members)} rows, below the {args.min_state_rows}-row floor")
                if not loo["sign_stable"]:
                    reasons.append(loo["reason"] or "leave-one-scenario-out sign not stable")
                planr_gap = None
                if OWN_NULL_ARM in arms:
                    planr_gap = mean(
                        [advantage_r[OWN_NULL_ARM][sid] for sid in members]
                    ) - mean([advantage[COMPARATOR_ARM][sid] for sid in members])
                entry = {
                    "n": len(members),
                    "advantage_pp": means,
                    "best_variant": best,
                    "best_advantage_pp": means[best],
                    "leave_one_scenario_out": loo,
                    "reportable": reportable,
                    "reasons": reasons,
                    "planr_minus_plan_advantage_pp": planr_gap,
                }
                state_block[cell] = entry
                if score_name == ADVANTAGE_SCORES[0][0]:
                    policy_rows.append(
                        {
                            "state_key": state_key,
                            "state_cell": cell,
                            "n": len(members),
                            "best_variant": best,
                            "best_advantage_pp": means[best],
                            "reportable": reportable,
                            "reasons": reasons,
                            "leave_one_scenario_out_sign_stable": loo["sign_stable"],
                            "advantage_noise_floor_pp": planr_gap,
                        }
                    )
            per_state[state_key] = state_block
        blocks[score_name] = {
            "sealed_field": field_name,
            "group": list(group),
            "group_replicate": list(group_replicate),
            "per_state": per_state,
            "whole_roster_advantage_pp": {
                key: mean([advantage[key][sid] for sid in ids]) for key in sorted(arms)
            },
        }

    advantage_payload = {
        "schema": SCHEMA_ADVANTAGE,
        "recipe_id": RECIPE_ID,
        "contacts": dict(CONTACTS_ZERO),
        "generated_at_utc": args.now,
        "quantity": (
            "group-relative advantage: on every row, each construction's own per-row score minus "
            "the mean over the GROUP on that row, in percentage points -- the quantity a "
            "training-free RL policy would be learned from"
        ),
        "group_choice": (
            "the five DISTINCT constructions. VAR1-PLANR is excluded from the group because it is "
            "the same construction as VAR1-PLAN and would double-weight the plan form inside the "
            "group mean; its advantage under the substituted group (PLANR in PLAN's place) is "
            "reported per cell as planr_minus_plan_advantage_pp, the noise floor of the advantage "
            "quantity itself."
        ),
        "state_source": (
            "every state cell is read from the COMPARATOR arm's own sealed runtime receipts or "
            "from the roster receipt -- never from the variant's own episode, because a selector "
            "must read the state BEFORE it picks a construction and VAR1-PER-K16C5 moves the "
            "candidate count itself"
        ),
        "state_keys": list(STATE_KEYS),
        "reportability_rule": (
            f"an action is reportable only when its state cell holds >= {args.min_state_rows} "
            "rows AND the sign of the best variant's mean advantage survives dropping each gold "
            "scenario in turn"
        ),
        "min_state_rows": args.min_state_rows,
        "scores": blocks,
        "driver_sha256": digest(DRIVER_PATH),
    }
    write_json(args.out_root / "group-relative-advantage.json", advantage_payload)

    policy_payload = {
        "schema": SCHEMA_POLICY,
        "recipe_id": RECIPE_ID,
        "contacts": dict(CONTACTS_ZERO),
        "generated_at_utc": args.now,
        "score": ADVANTAGE_SCORES[0][0],
        "sealed_field": ADVANTAGE_SCORES[0][1],
        "group": list(group),
        "min_state_rows": args.min_state_rows,
        "not_a_policy_release": (
            "a table of per-state best constructions on a CONSTRUCTION roster. Nothing here is "
            "admitted, locked or released; a reportable cell is a CANDIDATE for an out-of-fold "
            "re-read."
        ),
        "rows": sorted(policy_rows, key=lambda row: (row["state_key"], row["state_cell"])),
        "reportable_cells": sum(1 for row in policy_rows if row["reportable"]),
        "cells": len(policy_rows),
        "driver_sha256": digest(DRIVER_PATH),
    }
    write_json(args.out_root / "policy-table.json", policy_payload)
    return advantage_payload, policy_payload


# --------------------------------------------------------------------------
# Stage: cost and supply realisation
# --------------------------------------------------------------------------


def _arm_cost(arm: Arm, ids: Sequence[str], reference_rows: int) -> dict:
    cost = arm.generation_cost
    rows = arm.rows or 1
    entry: dict[str, object] = {
        "run_id": arm.run_id,
        "rows": arm.rows,
        "contacts": cost.get("calls_used"),
        "contacts_per_row": (cost.get("calls_used") or 0) / rows,
        "prompt_tokens_total": cost.get("prompt_tokens_total"),
        "prompt_tokens_per_row": (cost.get("prompt_tokens_total") or 0) / rows,
        "completion_tokens_total": cost.get("completion_tokens_total"),
        "completion_tokens_per_row": (cost.get("completion_tokens_total") or 0) / rows,
        "repeated_speech_seconds": cost.get("audio_seconds_used"),
        "tool_calls": cost.get("tool_calls"),
        "gpu_hours": None,
        "gpu_hours_per_reference_rows": None,
        "reference_rows": reference_rows,
    }
    receipts = arm.flight_receipts or {}
    monitor = ((receipts.get("stages") or {}).get("seal") or {}).get("serving_monitor_summary")
    if monitor and isinstance(monitor.get("active_seconds"), (int, float)):
        gpu_hours = monitor["active_seconds"] / 3600.0
        entry["gpu_hours"] = gpu_hours
        entry["gpu_hours_per_reference_rows"] = gpu_hours * reference_rows / rows
        entry["mean_utilization_percent"] = monitor.get("mean_utilization_percent")
    run_phases = (receipts.get("stages") or {}).get("run_phases") or {}
    if run_phases:
        entry["generation_wall_seconds"] = run_phases.get("wall_seconds")
        entry["contacts_per_minute"] = (run_phases.get("contacts_per_second") or 0) * 60.0
    # supply realisation, from the episode's own transitions
    exemplar_counts = [
        len(arm.runtime["rows"][sid]["supplied"].get(bank.EXEMPLAR_STORE) or ()) for sid in ids
    ]
    contract_counts = [
        len(arm.runtime["rows"][sid]["supplied"].get(bank.CONTRACT_STORE) or ()) for sid in ids
    ]
    card_counts = [arm.runtime["rows"][sid]["candidate_width"] for sid in ids]
    compacted = sum(1 for sid in ids if arm.runtime["rows"][sid]["compacted_contacts"] > 0)
    entry["supply_realisation"] = {
        "exemplar_values_per_row_mean": mean(exemplar_counts),
        "exemplar_values_per_row_min": min(exemplar_counts) if exemplar_counts else 0,
        "exemplar_values_per_row_max": max(exemplar_counts) if exemplar_counts else 0,
        "slot_contract_values_per_row_mean": mean(contract_counts),
        "perception_candidates_per_row_mean": mean(card_counts),
        "context_fit_compacted_rows": compacted,
    }
    entry["official"] = arm.scores["official"]
    return entry


def stage_cost(*, arms: dict[str, Arm], roster: dict, args: "Args") -> dict:
    ids = roster["ids"]
    reference_rows = len(ids)
    per_arm = {key: _arm_cost(arm, ids, reference_rows) for key, arm in sorted(arms.items())}
    # Pareto frontier over (official pooled SLU-F1 high, GPU hours low).
    points = {
        key: (entry["official"]["slu_f1"], entry["gpu_hours"])
        for key, entry in per_arm.items()
        if entry["gpu_hours"] is not None
    }
    frontier: list[str] = []
    for key, (slu, hours) in sorted(points.items()):
        dominated = any(
            other != key
            and points[other][0] >= slu
            and points[other][1] <= hours
            and (points[other][0] > slu or points[other][1] < hours)
            for other in points
        )
        if not dominated:
            frontier.append(key)
    base = per_arm[COMPARATOR_ARM]
    deltas = {
        key: {
            "contacts_per_row": (entry["contacts_per_row"] or 0) - (base["contacts_per_row"] or 0),
            "prompt_tokens_per_row": (entry["prompt_tokens_per_row"] or 0)
            - (base["prompt_tokens_per_row"] or 0),
            "gpu_hours_per_reference_rows": (
                None
                if entry["gpu_hours_per_reference_rows"] is None
                or base["gpu_hours_per_reference_rows"] is None
                else entry["gpu_hours_per_reference_rows"] - base["gpu_hours_per_reference_rows"]
            ),
        }
        for key, entry in sorted(per_arm.items())
        if key != COMPARATOR_ARM
    }
    payload = {
        "schema": SCHEMA_COST,
        "recipe_id": RECIPE_ID,
        "contacts": dict(CONTACTS_ZERO),
        "generated_at_utc": args.now,
        "reference_rows": reference_rows,
        "per_arm": per_arm,
        "delta_vs_comparator": deltas,
        "pareto_frontier": sorted(frontier),
        "frontier_axes": "official pooled SLU-F1 (maximise) against GPU hours (minimise)",
        "driver_sha256": digest(DRIVER_PATH),
    }
    write_json(args.out_root / "cost.json", payload)
    return payload


# --------------------------------------------------------------------------
# Rendering -- the own-null table is written ABOVE the variant table, always
# --------------------------------------------------------------------------

SECTION_OWN_NULL = "## 1. The R01C own null -- the margin every variant is read at"
SECTION_VARIANTS = "## 2. The variant table"

NOT_CLAIMED = (
    "NO ADMISSION VERDICT. No ADMITTED / NEUTRAL / HARMFUL label is attached to any VAR-1 cell, "
    "no module is admitted, no store is released and nothing is locked.",
    "NO TEST CLAIM AND NO GENERALISATION. R01C is a CONSTRUCTION roster with split role "
    "discovery; a variant that separates from the null here is a CANDIDATE for an out-of-fold "
    "re-read on TRAIN Fold A and DEV-2000-ADDED, each at that roster's own null.",
    "NO POLICY RELEASE. policy-table.json is a table of per-state best constructions on the "
    "selection venue, not a selected policy.",
    "NO PROMPT-FIT MEASUREMENT (VAR1-OPEN-3): no tokenizer was contacted by this read.",
)


def _own_null_table(own_null: dict) -> list[str]:
    lines = [
        SECTION_OWN_NULL,
        "",
        f"VAR1-PLAN against VAR1-PLANR on {own_null['n']} rows, "
        f"{own_null['distinct_clusters']} clusters, paired whole-cluster bootstrap. "
        "READ FIRST and never adjusted afterwards.",
        "",
        "| null | SLU half-width (pp) | intent half-width (pp) | n | roster | kind |",
        "| --- | ---: | ---: | ---: | --- | --- |",
    ]
    cross = own_null["h_cross_r01c"]
    lines.append(
        f"| **h_cross_r01c (THIS family's bar)** | **{_fmt(cross['h_slu'], 4)}** | "
        f"**{_fmt(cross['h_intent'], 4)}** | {own_null['n']} | R01C | cross-flight A/A |"
    )
    for name, entry in sorted(CONTEXT_NULLS.items()):
        lines.append(
            f"| {name} (context only) | {_fmt(entry['h_slu'], 4)} | "
            f"{_fmt(entry['h_intent'], 4)} | {entry['n']} | {entry['roster']} | "
            f"{'within-flight A/A' if name.startswith('h_within') else 'cross-flight A/A'} |"
        )
    lines += ["", own_null["decomposition_note"], ""]
    lines += [
        "| estimand | VAR1-PLAN | VAR1-PLANR | delta (pp) | CI95 (pp) | CI90 (pp) | h (pp) |",
        "| --- | ---: | ---: | ---: | --- | --- | ---: |",
    ]
    for name in sorted(own_null["metrics"]):
        entry = own_null["metrics"][name]
        boot = entry.get("cluster_bootstrap") or {}
        ci95 = boot.get("ci95_pp") or [None, None]
        ci90 = boot.get("ci90_pp") or [None, None]
        lines.append(
            f"| {name} | {_fmt(entry['left_pct'])} | {_fmt(entry['right_pct'])} | "
            f"{_signed(entry['delta_pp'])} | [{_fmt(ci95[0])}, {_fmt(ci95[1])}] | "
            f"[{_fmt(ci90[0])}, {_fmt(ci90[1])}] | {_fmt(boot.get('ci95_half_width_pp'), 4)} |"
        )
    return lines + [""]


def _variant_table(contrasts: dict) -> list[str]:
    margins = contrasts["margins"]
    lines = [
        SECTION_VARIANTS,
        "",
        f"Read at h_slu {_fmt(margins['h_slu'], 4)} pp and h_intent "
        f"{_fmt(margins['h_intent'], 4)} pp (section 1). "
        + contrasts["reading_rule"],
        "",
        "| variant | estimand | VAR1-PLAN | variant | delta (pp) | CI95 (pp) | CI90 (pp) | "
        "saves/harms/ties | McNemar p | CI95 excl. 0 | outside h | separated |",
        "| --- | --- | ---: | ---: | ---: | --- | --- | --- | ---: | --- | --- | --- |",
    ]
    for key in sorted(contrasts["variants"]):
        block = contrasts["variants"][key]
        for name in sorted(block["metrics"]):
            entry = block["metrics"][name]
            boot = entry.get("cluster_bootstrap") or {}
            ci95 = boot.get("ci95_pp") or [None, None]
            ci90 = boot.get("ci90_pp") or [None, None]
            flags = entry["read_flags"]
            lines.append(
                f"| {key} | {name} | {_fmt(entry['left_pct'])} | {_fmt(entry['right_pct'])} | "
                f"{_signed(entry['delta_pp'])} | [{_fmt(ci95[0])}, {_fmt(ci95[1])}] | "
                f"[{_fmt(ci90[0])}, {_fmt(ci90[1])}] | "
                f"{entry['saves']}/{entry['harms']}/{entry['ties']} | "
                f"{_fmt(entry['mcnemar_p'], 4)} | {_fmt(flags['ci95_excludes_zero'])} | "
                f"{_fmt(flags['point_estimate_outside_margin'])} | "
                f"{_fmt(flags['separated_from_null'])} |"
            )
    return lines + [""]


def _slot_type_table(payload: dict) -> list[str]:
    lines = [
        "## 3. Entity FP / FN by slot TYPE",
        "",
        payload["matcher"],
        "",
        "| arm | FP total | FN total | omission | over-emission | same-type wrong filler | "
        "type swap | empty-gold rows | empty-gold emitting | emission rate (%) |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key in sorted(payload["per_arm"]):
        entry = payload["per_arm"][key]
        attribution = entry["unmatched_attribution"]
        lines.append(
            f"| {key} | {_fmt(entry['derived_totals']['slot_f1_exact_fp'], 0)} | "
            f"{_fmt(entry['derived_totals']['slot_f1_exact_fn'], 0)} | "
            f"{attribution['omission_total']} | {attribution['over_emission_total']} | "
            f"{attribution['same_type_wrong_filler']} | {attribution['type_swap']} | "
            f"{entry['empty_gold_rows']} | {entry['empty_gold_emitting_rows']} | "
            f"{_fmt(entry['empty_gold_emission_rate_pct'])} |"
        )
    types = sorted(
        {
            slot_type
            for entry in payload["per_arm"].values()
            for slot_type in entry["per_type"]
        }
    )
    arms = sorted(payload["per_arm"])
    lines += [
        "",
        "Per slot TYPE, FP then FN, and the delta of each variant against VAR1-PLAN.",
        "",
        "| slot TYPE | " + " | ".join(f"{key} FP/FN" for key in arms) + " |",
        "| --- | " + " | ".join("---:" for _ in arms) + " |",
    ]
    for slot_type in types:
        cells = []
        for key in arms:
            per_type = payload["per_arm"][key]["per_type"].get(slot_type, {})
            cell = f"{per_type.get('fp', 0)}/{per_type.get('fn', 0)}"
            if key != COMPARATOR_ARM:
                delta = payload["delta_vs_comparator"][key]["per_type"].get(slot_type, {})
                cell += f" ({delta.get('fp', 0):+d}/{delta.get('fn', 0):+d})"
            cells.append(cell)
        lines.append(f"| {slot_type} | " + " | ".join(cells) + " |")
    return lines + [""]


def _coverage_table(payload: dict) -> list[str]:
    lines = [
        "## 4. Perception candidate coverage",
        "",
        payload["join"],
        "",
        "| arm | gold intent in candidate union (%) | in first list (%) | mean candidates | "
        "candidate-width histogram | distinct ids (%) | INTENT-UNCOVERED | INTENT-COVERED |",
        "| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |",
    ]
    for key in sorted(payload["per_arm"]):
        entry = payload["per_arm"][key]
        histogram = ", ".join(
            f"{width}:{count}" for width, count in sorted(entry["candidate_width_histogram"].items())
        )
        lines.append(
            f"| {key} | {_fmt(entry['gold_intent_in_candidate_union_rate_pct'])} | "
            f"{_fmt(entry['gold_intent_in_first_list_rate_pct'])} | "
            f"{_fmt(entry['mean_candidate_width'])} | {histogram} | "
            f"{_fmt(entry['distinct_candidate_ids_rate_pct'])} | {entry['intent_uncovered']} | "
            f"{entry['intent_covered']} |"
        )
    lines += [
        "",
        "| arm | " + " | ".join(name for name in bank.CLASSES) + " |",
        "| --- | " + " | ".join("---:" for _ in bank.CLASSES) + " |",
    ]
    for key in sorted(payload["per_arm"]):
        taxonomy = payload["per_arm"][key]["taxonomy"]
        lines.append(
            f"| {key} | " + " | ".join(str(taxonomy.get(name, 0)) for name in bank.CLASSES) + " |"
        )
    return lines + [""]


def _scenario_table(payload: dict) -> list[str]:
    variants = sorted(payload["per_variant"])
    lines = [
        "## 5. The gold per-scenario table",
        "",
        payload["availability"],
        "",
        "| scenario | n | " + " | ".join(f"{key} SLU / intent" for key in variants) + " |",
        "| --- | ---: | " + " | ".join("---:" for _ in variants) + " |",
    ]
    for scenario in payload["scenarios"]:
        cells = []
        for key in variants:
            cell = payload["per_variant"][key]["per_scenario"][scenario]
            cells.append(f"{_signed(cell['slu_delta_pp'])} / {_signed(cell['intent_delta_pp'])}")
        lines.append(
            f"| {scenario} | {payload['row_counts'][scenario]} | " + " | ".join(cells) + " |"
        )
    lines += [
        "",
        "| weighting | " + " | ".join(f"{key} SLU / intent" for key in variants) + " |",
        "| --- | " + " | ".join("---:" for _ in variants) + " |",
    ]
    for weighting in ("natural_mixture", "equal_scenario"):
        cells = []
        for key in variants:
            block = payload["per_variant"][key]["weightings"][weighting]
            cells.append(
                f"{_signed(block['slu_delta_pp'])} / {_signed(block['intent_delta_pp'])}"
            )
        lines.append(f"| {weighting} | " + " | ".join(cells) + " |")
    return lines + [""]


def _advantage_table(payload: dict, policy: dict) -> list[str]:
    primary = ADVANTAGE_SCORES[0][0]
    block = payload["scores"][primary]
    group = block["group"]
    lines = [
        "## 6. Group-relative advantage per runtime-observable state",
        "",
        payload["quantity"],
        "",
        payload["group_choice"],
        "",
        payload["state_source"],
        "",
        payload["reportability_rule"] + ".",
        "",
        f"Primary score: {primary} (sealed field `{block['sealed_field']}`). Group: "
        + ", ".join(group)
        + ".",
        "",
        "| state key | cell | n | "
        + " | ".join(group)
        + " | best | best advantage (pp) | LOO min/max | reportable |",
        "| --- | --- | ---: | " + " | ".join("---:" for _ in group) + " | --- | ---: | --- | --- |",
    ]
    for state_key in payload["state_keys"]:
        for cell in sorted(block["per_state"][state_key]):
            entry = block["per_state"][state_key][cell]
            loo = entry["leave_one_scenario_out"]
            lines.append(
                f"| {state_key} | {cell} | {entry['n']} | "
                + " | ".join(_signed(entry["advantage_pp"][key]) for key in group)
                + f" | {entry['best_variant']} | {_signed(entry['best_advantage_pp'])} | "
                f"[{_fmt(loo['min_pp'])}, {_fmt(loo['max_pp'])}] | "
                f"{_fmt(entry['reportable'])} |"
            )
    lines += [
        "",
        f"`policy-table.json`: {policy['reportable_cells']} of {policy['cells']} state cells are "
        "reportable. " + policy["not_a_policy_release"],
        "",
    ]
    return lines


def _cost_table(payload: dict) -> list[str]:
    lines = [
        "## 7. Cost and the frontier",
        "",
        f"Per {payload['reference_rows']} rows. " + payload["frontier_axes"] + ".",
        "",
        "| arm | official SLU-F1 | contacts | contacts/row | prompt tokens/row | GPU-h | "
        f"GPU-h per {payload['reference_rows']} rows | exemplars/row | cards/row | compacted rows |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key in sorted(payload["per_arm"]):
        entry = payload["per_arm"][key]
        supply = entry["supply_realisation"]
        lines.append(
            f"| {key} | {_fmt(entry['official']['slu_f1'])} | "
            f"{_fmt(entry['contacts'], 0)} | {_fmt(entry['contacts_per_row'], 3)} | "
            f"{_fmt(entry['prompt_tokens_per_row'], 1)} | {_fmt(entry['gpu_hours'], 3)} | "
            f"{_fmt(entry['gpu_hours_per_reference_rows'], 3)} | "
            f"{_fmt(supply['exemplar_values_per_row_mean'], 2)} | "
            f"{_fmt(supply['perception_candidates_per_row_mean'], 2)} | "
            f"{supply['context_fit_compacted_rows']} |"
        )
    lines += ["", "Pareto frontier: " + (", ".join(payload["pareto_frontier"]) or "--"), ""]
    return lines


def render(
    *,
    stop: dict,
    own_null: dict,
    contrasts: dict,
    slot_types: dict,
    coverage: dict,
    scenario: dict,
    advantage: dict,
    policy: dict,
    cost: dict,
    args: "Args",
) -> str:
    lines = [
        f"# VAR-1: the construction-variant read on the {stop['roster']['rows']}-row "
        f"{stop['roster']['roster_id']} roster",
        "",
        f"Recipe `{RECIPE_ID}`. Model-free: "
        + ", ".join(f"{name} {count}" for name, count in sorted(CONTACTS_ZERO.items()))
        + ".",
        f"Driver `scripts/analysis/slurp_var1_variant_read.py` sha256 "
        f"`{stop['driver_sha256'][:16]}`.",
        f"Generated at: {args.now}.",
        "",
        "Read rows `SAEA-SLURP-STAGE3-VAR1-OWN-NULL-V1` and "
        "`SAEA-SLURP-STAGE3-VAR1-VARIANT-READ-V1` (both model-free-check). "
        "No utterance, transcript, delivered filler, gold filler or model output text appears "
        "anywhere in this document or the artefacts beside it: labels, slot TYPE names, ids, "
        "counts, rates, scores and hashes only.",
        "",
        "| arm | run id | rows | official SLU-F1 | official intent | composed config | protocol |",
        "| --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for key in sorted(stop["arms"]):
        entry = stop["arms"][key]
        lines.append(
            f"| {key} | `{entry['run_id']}` | {entry['rows']} | "
            f"{_fmt(entry['official']['slu_f1'])} | {_fmt(entry['official']['intent_accuracy'])} | "
            f"`{(entry['composed_config_hash'] or '')[:12]}` | "
            f"`{(entry['protocol_hash'] or '')[:12]}` |"
        )
    lines.append("")
    lines += _own_null_table(own_null)
    lines += _variant_table(contrasts)
    lines += _slot_type_table(slot_types)
    lines += _coverage_table(coverage)
    lines += _scenario_table(scenario)
    lines += _advantage_table(advantage, policy)
    lines += _cost_table(cost)
    lines += ["## 8. What this read does not claim", ""]
    lines += [f"{index}. {text}" for index, text in enumerate(NOT_CLAIMED, start=1)]
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Args and main
# --------------------------------------------------------------------------


@dataclass
class Args:
    repo_root: Path
    data_root: Path
    out_root: Path
    package_relpath: str
    lock_path: Path
    roster_relpath: str
    scorer_id: str
    split_id: str
    cluster_key: str
    seed: int
    draws: int
    min_state_rows: int
    expect_arms: tuple[str, ...]
    now: str
    #: Worker processes for this read's independent bootstraps. ``None`` means
    #: ``analysis.parallel``'s own default (the campaign preparation cap). The
    #: numbers this read produces never depend on it.
    workers: int | None = None


def parse_args(argv: Sequence[str] | None = None) -> Args:
    parser = argparse.ArgumentParser(
        description=(
            "VAR-1 construction-variant read (registered open items VAR1-OPEN-1 / VAR1-OPEN-2). "
            "Model-free; reads sealed bytes only."
        )
    )
    parser.add_argument("--repo-root", default=str(REPO))
    parser.add_argument(
        "--data-root",
        default=os.environ.get("SPEECHRL_DATA_DIR"),
        help="SPEECHRL_DATA_DIR; large bytes never enter Git",
    )
    parser.add_argument("--out-root", default=None, help=f"default <data-root>/analysis/{OUT_DIRNAME}")
    parser.add_argument("--package", default=DEFAULT_PACKAGE)
    parser.add_argument("--lock", default=DEFAULT_LOCK)
    parser.add_argument("--roster", default=None, help="default: the recipe's own driver.roster")
    parser.add_argument("--scorer-id", default=None, help="default: the recipe's own scorer.id")
    parser.add_argument("--split-id", default=DEFAULT_SPLIT_ID)
    parser.add_argument("--cluster-key", default=None, help="default: the recipe's own cluster key")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--draws", type=int, default=DEFAULT_DRAWS)
    parser.add_argument("--min-state-rows", type=int, default=DEFAULT_MIN_STATE_ROWS)
    parser.add_argument(
        "--expect-arms",
        default=",".join(EXPECTED_ARMS),
        help="the arm keys the recipe must carry; the default is the registered VAR-1 family",
    )
    add_workers_argument(
        parser,
        help_suffix="This read has 24 independent bootstraps: 4 for the own null, 20 for the "
        "five variants.",
    )
    ns = parser.parse_args(argv)
    if not ns.data_root:
        parser.error("--data-root is required (or set SPEECHRL_DATA_DIR)")
    data_root = Path(ns.data_root)
    repo_root = Path(ns.repo_root)
    package_relpath = ns.package.replace("\\", "/").rstrip("/")
    recipe = load_json(repo_root / package_relpath / "analysis-recipe-v1.json")
    driver_block = recipe.get("driver") or {}
    return Args(
        repo_root=repo_root,
        data_root=data_root,
        out_root=Path(ns.out_root) if ns.out_root else data_root / "analysis" / OUT_DIRNAME,
        package_relpath=package_relpath,
        lock_path=Path(ns.lock),
        roster_relpath=ns.roster or driver_block.get("roster") or "",
        scorer_id=ns.scorer_id or (recipe.get("scorer") or {}).get("id") or "",
        split_id=ns.split_id,
        cluster_key=ns.cluster_key or driver_block.get("cluster_key") or "utterance_id",
        seed=ns.seed,
        draws=ns.draws,
        min_state_rows=ns.min_state_rows,
        expect_arms=tuple(part for part in ns.expect_arms.split(",") if part),
        now=datetime.now(timezone.utc).isoformat(),
        workers=ns.workers,
    )


def load_roster(repo_root: Path, relpath: str, cluster_key: str) -> dict:
    """The roster receipt, with the per-item cluster key and the per-item gold stratum."""

    base = _bank(bank.load_roster, repo_root, relpath)
    document = load_json(repo_root / relpath)
    cluster: dict[str, str] = {}
    for item in document.get("items") or ():
        sample_id = item.get("sample_id") or item.get("id")
        value = item.get(cluster_key)
        if not isinstance(value, str) or not value:
            raise Var1ReadError(
                f"roster {relpath} item {sample_id!r} carries no usable {cluster_key!r} field"
            )
        cluster[sample_id] = value
    base["cluster"] = cluster
    base["strata_counts"] = Counter(base["stratum"][sid] for sid in base["ids"])
    if "<none>" in base["strata_counts"]:
        raise Var1ReadError(
            f"roster {relpath} withholds the per-item stratum, so the gold per-scenario table is "
            "not derivable on this venue"
        )
    return base


def run(args: Args) -> dict:
    recipe_path = args.repo_root / args.package_relpath / "analysis-recipe-v1.json"
    facts_path = args.repo_root / args.package_relpath / "registered-facts-v1.json"
    for path in (recipe_path, facts_path):
        if not path.exists():
            raise Var1ReadError(f"registered package file missing: {path}")
    recipe = load_json(recipe_path)
    facts = load_json(facts_path)
    arm_specs = _arm_specs(recipe, args.expect_arms)
    roster = load_roster(args.repo_root, args.roster_relpath, args.cluster_key)

    arms: dict[str, Arm] = {}
    for key, spec in sorted(arm_specs.items()):
        arms[key] = load_arm(
            key=key,
            run_id=spec["run_id"],
            attempt_id=spec["attempt_id"],
            data_root=args.data_root,
            roster=roster,
            scorer_id=args.scorer_id,
        )

    gold = load_gold(args.lock_path, args.data_root, args.split_id)
    release = (facts.get("pins") or {}).get("train_exemplars_release") or {}
    exemplars = load_exemplar_targets(
        args.data_root, release.get("relpath") or "", release.get("sha256") or ""
    )

    stop = stage_stop(
        arms=arms,
        arm_specs=arm_specs,
        recipe=recipe,
        recipe_sha256=digest(recipe_path),
        facts=facts,
        facts_sha256=digest(facts_path),
        roster=roster,
        args=args,
        gold=gold,
        exemplars=exemplars,
    )

    for key, arm in sorted(arms.items()):
        arm.derived = _bank(
            bank.derive_rows,
            ids=roster["ids"],
            gold=gold,
            delivered=arm.delivered,
            scores=arm.scores,
            run_id=arm.run_id,
        )
        arm.classes = _bank(
            bank.classify,
            ids=roster["ids"],
            derived=arm.derived,
            delivered=arm.delivered,
            scores=arm.scores,
            runtime=arm.runtime,
        )

    own_null = stage_own_null(
        arms=arms,
        roster=roster,
        args=args,
        stop_sha256=content_sha256(args.out_root / "stop.json"),
    )
    contrasts = stage_variants(arms=arms, roster=roster, args=args, own_null=own_null)
    slot_types = stage_slot_types(arms=arms, roster=roster, args=args)
    coverage = stage_coverage(arms=arms, roster=roster, args=args)
    scenario = stage_per_scenario(arms=arms, roster=roster, args=args)
    states = build_states(
        comparator=arms[COMPARATOR_ARM], roster=roster, exemplars=exemplars
    )
    advantage, policy = stage_advantage(arms=arms, roster=roster, states=states, args=args)
    cost = stage_cost(arms=arms, roster=roster, args=args)

    markdown = render(
        stop=stop,
        own_null=own_null,
        contrasts=contrasts,
        slot_types=slot_types,
        coverage=coverage,
        scenario=scenario,
        advantage=advantage,
        policy=policy,
        cost=cost,
        args=args,
    )
    readme = args.out_root / "README.md"
    readme.parent.mkdir(parents=True, exist_ok=True)
    with readme.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(markdown)
    return {
        "out_root": str(args.out_root),
        "artefacts": list(ARTEFACTS),
        "own_null": own_null["h_cross_r01c"],
        "reportable_cells": policy["reportable_cells"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        summary = run(args)
    except Var1ReadError as error:
        print(f"VAR-1 VARIANT READ REFUSED: {error}", file=sys.stderr)
        return 2
    print(
        "VAR-1 variant read written to "
        f"{summary['out_root']} (h_slu {summary['own_null']['h_slu']:.4f}, "
        f"h_intent {summary['own_null']['h_intent']:.4f}, "
        f"{summary['reportable_cells']} reportable state cells)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
