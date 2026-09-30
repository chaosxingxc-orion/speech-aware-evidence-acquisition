"""slurp_paired_roster_read.py -- the reusable READ DRIVER for cell B6 (owner decision 58:
reads are executed by script, never by hand).

Cell B6 is a paired, REPORT-ONLY read of two arms flown on the SAME 1,000-row DEV-2000-ADDED
roster: the bare-core direct arm (left) and the locked v2.0 default-plan arm (right). It is the
fresh-roster generalisation read of the already-locked plan against the bare frozen core -- not a
new module decision. No ADMITTED/HARMFUL verdict, no bar (owner decision 86: development numbers
carry no bar; decision 28: DEV-2000-ADDED is a development roster).

Stages, in the order they must run (``--stage all`` runs every one in order):

  stop         verify both attempts FINALIZED, both manifests COMPLETED, the roster identity, that
               each arm carries exactly one score job, that the two per-sample id sets equal the
               roster ids exactly, and that the official aggregate reproduces from per-sample counts
               to 1e-6. Refuses loudly (raises ``StopStageError``) on any mismatch and writes nothing.
  structural   counts only: rows, parsed rows, admission dispositions, tool calls (must be zero),
               and -- for the plan arm only, where the sealed rows carry a
               ``native_episode_receipt`` -- planner route/action histograms, revisions executed,
               role-visits-per-row histogram, delivery-normaliser receipt counts and E20 context-fit
               compaction counts.
  contrast     the paired estimators: pooled micro SLU-F1 / span-F1 (paired whole-utterance-cluster
               bootstrap over the resampled counts) and the five per-row exact-match metrics
               (``paired_contrast``'s own per-sample mean-difference bootstrap), both with CI90/CI95,
               saves/harms/ties and the exact McNemar sign-test p. A per-channel (headset vs
               far-field) breakdown is reported from the roster's own ``headset`` field. A
               per-scenario table is NOT AVAILABLE for this roster (see the docstring of
               :func:`stage_contrast` for why) and is reported as such, never silently omitted.
  efficiency   contacts, contacts per row, GPU-active seconds and GPU hours per 1,000 rows (from
               ``flight-receipts.json``'s ``stages.seal.serving_monitor_summary``, mirroring
               ``plan_cell_read.costs_block``), and prompt/completion tokens per row (from the
               generation manifest's own ``cost`` block).
  verdict      assemble ``README.md`` (the tables in Markdown) and ``verdict.json`` (``status``
               is always ``"DESCRIPTIVE"``) from the artefacts the earlier stages wrote, plus the
               sha256 of every artefact and of this driver file itself.

Model-free. Zero model, tokenizer, encoder, scorer, llama-server or network contact of any kind:
every artefact this driver writes carries ``"contacts": {"model": 0, "tokenizer": 0, "encoder": 0,
"scorer": 0}``. Every sealed byte this driver reads is opened read-only; nothing sealed is copied,
moved or modified, and nothing is written anywhere except under ``--analysis-root``.

No utterance text, gold label, delivered filler or model output is ever printed or persisted: this
driver reads and reports counts, rates, ids, scenario/channel names and content hashes only. The
``<run>.outputs.jsonl`` rows this driver reads carry a ``"text"`` field (the delivered response);
every row reader in this module drops it on read and never re-serialises it into any artefact.

Estimators mirrored (owner decision 58's own citation discipline: cite which functions were
mirrored, never re-derive them by hand):
  - ``speech_aware_evidence_acquisition.analysis.bootstrap.paired_cluster_bootstrap`` (the shared
    per-sample/per-cluster resampling core; imported, not reimplemented).
  - ``speech_aware_evidence_acquisition.analysis.paired.paired_contrast`` and
    ``.resampled_statistic`` (the per-row and pooled-statistic paired contrast machinery; imported
    directly, exactly as ``analysis/SAEA-SLURP-DEFAULT-PLAN-LOCK-REPLICATE-PAIRED-ANALYSIS-V1/
    plan_cell_read.py`` -- read-only, TRAIN Fold A precedent, cell PLAN's own read driver -- imports
    them). ``paired.mcnemar_exact`` is ``paired_contrast``'s own sign-test, reused via its
    ``sign_test_p`` field.
  - ``speech_aware_evidence_acquisition.analysis.null_calibration.pooled_f1`` (the pooled
    tp/fp/fn micro-F1 recomputation used both for the stop-stage 1e-6 reproduction check and for
    the pooled-micro contrast statistic); the ``MICRO_METRICS`` field groups below are copied
    unchanged from ``plan_cell_read.MICRO_METRICS``.
  - ``speech_aware_evidence_acquisition.data.splits.split_identity_hash`` / ``.prefixed`` (the
    registered split-identity convention: sha256 over the LF-joined sorted carrier-prefixed sample
    ids) for the stop-stage roster-identity check.
  - The ``interval_block`` shape (point estimate, sigma-hat, CI90/CI95 with half-widths, both
    computed from the SAME replicate set rather than two separate bootstrap runs) mirrors
    ``plan_cell_read.interval_block`` / ``.percentiles``.

Deliberately NOT copied from ``plan_cell_read.py``: its TRAIN-A registered-facts table
(``DEFAULT_REGISTERED``), its LOCK/frontier/server-log-join stages, and its companion-scorer
rescoring machinery. Cell B6 has no registered comparator facts to reproduce, no LOCK arm, no
frontier row and no companion scorers -- it is a plain paired report on one already-sealed scorer
per arm.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Sequence

# --------------------------------------------------------------------------
# Path setup -- this file always lives at <repo_root>/scripts/analysis/, so
# its own location (never --repo-root, which only steers where the roster and
# provenance paths below are resolved) fixes where the shared estimator
# library is imported from.
# --------------------------------------------------------------------------

_DRIVER_PATH = Path(__file__).resolve()
_DRIVER_REPO_ROOT = _DRIVER_PATH.parents[2]
_src = str(_DRIVER_REPO_ROOT / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from speech_aware_evidence_acquisition.analysis import bootstrap as bs  # noqa: E402
from speech_aware_evidence_acquisition.analysis.null_calibration import pooled_f1  # noqa: E402
from speech_aware_evidence_acquisition.analysis.paired import (  # noqa: E402
    paired_contrast,
    resampled_statistic,
)
from speech_aware_evidence_acquisition.data.splits import (  # noqa: E402
    prefixed,
    split_identity_hash,
)

SCHEMA_STOP = "saea-slurp-b6-paired-roster-read-stop-v1"
SCHEMA_STRUCTURAL = "saea-slurp-b6-paired-roster-read-structural-v1"
SCHEMA_CONTRAST = "saea-slurp-b6-paired-roster-read-contrast-v1"
SCHEMA_SCENARIO = "saea-slurp-b6-paired-roster-read-per-scenario-v1"
SCHEMA_EFFICIENCY = "saea-slurp-b6-paired-roster-read-efficiency-v1"
SCHEMA_VERDICT = "saea-slurp-b6-paired-roster-read-verdict-v1"

DEFAULT_SCORER = "slurp-slu-official"
DEFAULT_ROSTER = "docs/receipts/rosters/slurp-dev-2000-added-v1.json"
DEFAULT_CLUSTER_KEY = "utterance_id"
#: ``"final-report"`` added by the 2026-09-29 milestone fix: a signed test-sample roster may be
#: read ONLY under the owner-allowance / recipe-scorer / aggregate-stratification / countersign
#: conditions ``stage3_paired_read.run_package`` enforces before it ever builds this argv; this
#: driver's own contribution is the scorer-identity check beside ``stage_stop``'s existing
#: "discovery requires the TRAIN scorer" block, below.
ALLOWED_SOURCE_SPLIT_ROLES = ("dev", "discovery", "final-report")
DEFAULT_SEED = 20260915
DEFAULT_DRAWS = 10_000
DEFAULT_TITLE = "SLURP cell B6: DEV-2000-ADDED paired read (direct vs locked v2.0 default plan)"

STAGES = ("stop", "structural", "contrast", "efficiency", "verdict")

#: The five per-row exact-match/F1 metrics carried by every ``slurp-slu-official`` per-sample row.
PER_ROW_METRICS = (
    "scenario_action_exact",
    "scenario_exact",
    "action_exact",
    "slot_f1_exact_f1",
    "slu_f1_f1",
)

#: Copied unchanged from ``plan_cell_read.MICRO_METRICS`` (TRAIN Fold A precedent, read-only):
#: the (tp-fields, fp-fields, fn-fields) each pooled micro-F1 is recomputed from.
MICRO_METRICS: dict[str, tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = {
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

#: Which top-level ``aggregate.official`` field each pooled micro-metric reproduces, for the
#: stop-stage 1e-6 check.
OFFICIAL_FIELD = {"slu_f1_micro": "slu_f1", "span_f1_micro": "span_f1"}

CONTACTS_ZERO = {"model": 0, "tokenizer": 0, "encoder": 0, "scorer": 0}


class StopStageError(RuntimeError):
    """The stop stage refuses: a sealed byte does not match what it must pin, or the roster/score
    identity does not reproduce. Raised loudly; no artefact is written when this fires."""


class ReadDriverError(RuntimeError):
    """A later stage cannot proceed -- e.g. an earlier stage's artefact is missing."""


# --------------------------------------------------------------------------
# Small utilities
# --------------------------------------------------------------------------


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _sha_of(obj: object) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> str:
    """Write ``payload`` as UTF-8 with ``\\n`` newlines only (never the platform default -- this
    driver may run under Windows Python, whose ``open()`` default encoding is not UTF-8), and
    return the written file's own sha256."""

    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return digest(path)


def _percentile(values: Sequence[float], fraction: float) -> float:
    return bs._percentile(sorted(values), fraction)


def _ci(replicates: Sequence[float], level: float) -> tuple[float, float]:
    tail = (1.0 - level) / 2.0
    return (_percentile(replicates, tail), _percentile(replicates, 1.0 - tail))


def interval_block(
    replicates: Sequence[float], point_estimate: float, seed: int
) -> dict[str, object]:
    """CI90 and CI95 computed from the SAME replicate set (never two separate bootstrap runs) --
    mirrors ``plan_cell_read.interval_block`` / ``.percentiles``."""

    ci95 = _ci(replicates, 0.95)
    ci90 = _ci(replicates, 0.90)
    return {
        "point_estimate_pp": 100 * point_estimate,
        "sigma_hat_pp": 100 * (statistics.pstdev(replicates) if len(replicates) > 1 else 0.0),
        "ci95_pp": [100 * ci95[0], 100 * ci95[1]],
        "ci95_half_width_pp": 100 * (ci95[1] - ci95[0]) / 2.0,
        "ci90_pp": [100 * ci90[0], 100 * ci90[1]],
        "ci90_half_width_pp": 100 * (ci90[1] - ci90[0]) / 2.0,
        "n_replicates": len(replicates),
        "seed": seed,
        "resampling": "paired whole-cluster bootstrap",
    }


def _fmt(value, digits: int = 2, dash: str = "--") -> str:
    if value is None:
        return dash
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        return f"{value:.{digits}f}"
    return str(value)


# --------------------------------------------------------------------------
# Arm loading
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ArmSpec:
    label: str
    run_id: str
    attempt_id: str
    #: owner decision 172, docs/superpowers/specs/2026-09-27-same-flight-supply-variant-
    #: instrument-design.md section 3: when set, this arm is a SAME-FLIGHT SUPPLY-VARIANT
    #: COLUMN of the sealed run named by ``run_id``/``attempt_id`` -- ``load_arm`` reads the
    #: renderer's derived per-arm score and its receipt instead of ``<run_id>.scores.json``.
    #: ``None`` (the default) is the ordinary, byte-identical arm read.
    column: str | None = None


@dataclass
class Arm:
    """Everything the stages need about one sealed arm, resolved once."""

    spec: ArmSpec
    run_dir: Path
    manifest: dict
    manifest_path: Path
    manifest_sha256: str
    scores: dict
    scores_path: Path
    scores_sha256: str
    generation_manifest: dict
    generation_manifest_path: Path
    generation_manifest_sha256: str
    attempt_record: dict
    attempt_record_path: Path
    score_jobs_path: Path
    score_jobs: list[dict]
    flight_receipts: dict | None
    flight_receipts_path: Path
    #: Set only for a column arm (``spec.column is not None``): the derived score receipt's own
    #: ``parent_manifest_sha256`` (owner decision 172 section 3, AT4 same-parent refusal).
    parent_manifest_sha256: str | None = None

    def artifact(self, suffix: str) -> Path:
        return self.run_dir / f"{self.spec.run_id}.{suffix}"

    @property
    def rows(self) -> int:
        return int(self.manifest.get("split", {}).get("count") or 0)


#: owner decision 172 section 3: where a column's derived score and its receipt live, relative
#: to the arm's own sealed run directory -- alongside every other sealed artefact ``Arm`` already
#: reads from that SAME directory, since a column is not a new run, only a different score of the
#: one sealed flight. ``scripts/analysis/stage3_rollout_score.py``'s ``score_supply_variant_copies``
#: names the file itself (``arm-<arm>-<scorer>-scores.json``); a coordinator registering the first
#: instrument cell points that script's ``--analysis-root`` here.
SUPPLY_VARIANT_COLUMN_DIR = "supply-variants"


def load_arm(data_root: Path, spec: ArmSpec, *, scorer_id: str | None = None) -> Arm:
    run_dir = data_root / "runs" / spec.run_id / spec.attempt_id
    manifest_path = run_dir / f"{spec.run_id}.run-manifest.json"
    generation_manifest_path = run_dir / f"{spec.run_id}.generation-manifest.json"
    attempt_record_path = data_root / "attempts" / spec.run_id / f"{spec.attempt_id}.json"
    score_jobs_path = run_dir / "score-jobs.jsonl"
    flight_receipts_path = run_dir / "flight-receipts.json"

    receipt_path: Path | None = None
    if spec.column is not None:
        if not scorer_id:
            raise StopStageError(
                f"{spec.label}: a column arm ({spec.column!r}) needs its scorer id to locate "
                "the derived score"
            )
        scores_path = (
            run_dir / SUPPLY_VARIANT_COLUMN_DIR / f"arm-{spec.column}-{scorer_id}-scores.json"
        )
        receipt_path = scores_path.with_name(scores_path.name + ".receipt.json")
    else:
        scores_path = run_dir / f"{spec.run_id}.scores.json"

    required_files = [manifest_path, scores_path, generation_manifest_path, attempt_record_path]
    if receipt_path is not None:
        required_files.append(receipt_path)
    for required in required_files:
        if not required.exists():
            raise StopStageError(f"{spec.label}: missing required sealed file {required}")

    manifest = load_json(manifest_path)
    scores = load_json(scores_path)
    generation_manifest = load_json(generation_manifest_path)
    attempt_record = load_json(attempt_record_path)
    score_jobs = [
        json.loads(line)
        for line in score_jobs_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    flight_receipts = load_json(flight_receipts_path) if flight_receipts_path.exists() else None

    parent_manifest_sha256 = None
    if receipt_path is not None:
        receipt = load_json(receipt_path)
        parent_manifest_sha256 = receipt.get("parent_manifest_sha256")
        if not isinstance(parent_manifest_sha256, str) or not parent_manifest_sha256:
            raise StopStageError(
                f"{spec.label}: derived-column receipt {receipt_path} names no "
                "parent_manifest_sha256"
            )
        # The receipt's claim is verified against the manifest actually sitting in THIS arm's
        # own run directory, not merely trusted: a column is bound to the sealed flight it was
        # rendered from, and AT4 (same-parent refusal) is only as strong as this check.
        actual_manifest_sha256 = digest(manifest_path)
        if parent_manifest_sha256 != actual_manifest_sha256:
            raise StopStageError(
                f"{spec.label}: derived-column receipt {receipt_path} names parent_manifest_sha256 "
                f"{parent_manifest_sha256!r}, but {manifest_path} hashes to "
                f"{actual_manifest_sha256!r}"
            )

    return Arm(
        spec=spec,
        run_dir=run_dir,
        manifest=manifest,
        manifest_path=manifest_path,
        manifest_sha256=digest(manifest_path),
        scores=scores,
        scores_path=scores_path,
        scores_sha256=digest(scores_path),
        generation_manifest=generation_manifest,
        generation_manifest_path=generation_manifest_path,
        generation_manifest_sha256=digest(generation_manifest_path),
        attempt_record=attempt_record,
        attempt_record_path=attempt_record_path,
        score_jobs_path=score_jobs_path,
        score_jobs=score_jobs,
        flight_receipts=flight_receipts,
        flight_receipts_path=flight_receipts_path,
        parent_manifest_sha256=parent_manifest_sha256,
    )


# --------------------------------------------------------------------------
# Roster
# --------------------------------------------------------------------------


@dataclass
class Roster:
    path: Path
    sha256: str
    document: dict
    ids: tuple[str, ...]
    carrier_lock_key: str
    cluster_of_id: dict[str, str]
    channel_of_id: dict[str, str]


def load_roster(repo_root: Path, roster_relpath: str, cluster_key: str) -> Roster:
    path = repo_root / roster_relpath
    if not path.exists():
        raise StopStageError(f"roster not found at {path}")
    document = load_json(path)
    items = document.get("items")
    if not isinstance(items, list) or not items:
        raise StopStageError(f"roster {path} carries no items")
    ids: list[str] = []
    cluster_of_id: dict[str, str] = {}
    channel_of_id: dict[str, str] = {}
    for item in items:
        sample_id = item.get("sample_id") or item.get("id")
        if not isinstance(sample_id, str) or not sample_id:
            raise StopStageError(f"roster {path} has an item with no usable sample_id")
        if "id" in item and item["id"] != sample_id:
            raise StopStageError(
                f"roster {path} item {sample_id!r} has id != sample_id "
                "(this driver assumes they agree)"
            )
        if sample_id in cluster_of_id:
            raise StopStageError(f"roster {path} repeats sample_id {sample_id!r}")
        cluster_value = item.get(cluster_key)
        if not isinstance(cluster_value, str) or not cluster_value:
            raise StopStageError(
                f"roster {path} item {sample_id!r} has no usable {cluster_key!r} field"
            )
        ids.append(sample_id)
        cluster_of_id[sample_id] = cluster_value
        channel_of_id[sample_id] = "headset" if item.get("headset") else "far_field"
    carrier_lock_key = document.get("carrier_lock_key")
    if not isinstance(carrier_lock_key, str) or not carrier_lock_key:
        raise StopStageError(f"roster {path} has no carrier_lock_key")
    return Roster(
        path=path,
        sha256=digest(path),
        document=document,
        ids=tuple(sorted(ids)),
        carrier_lock_key=carrier_lock_key,
        cluster_of_id=cluster_of_id,
        channel_of_id=channel_of_id,
    )


# --------------------------------------------------------------------------
# Args
# --------------------------------------------------------------------------


@dataclass
class Args:
    stage: str
    left: ArmSpec
    right: ArmSpec
    scorer_id: str
    roster_relpath: str
    cluster_key: str
    analysis_root: Path
    repo_root: Path
    data_root: Path
    seed: int
    draws: int
    recipe_id: str | None
    title: str
    split_identity_hash: str | None
    expected_split_role: str = "dev"
    #: Owner decision 101: the Stage-3 algorithm block echoed into verdict.json
    #: (``None`` for the Stage-2 reads this driver was written for).
    stage3_algorithm: dict | None = None


def parse_args(argv: Sequence[str] | None = None) -> Args:
    parser = argparse.ArgumentParser(
        description="Cell B6 reusable paired roster read (owner decision 58)."
    )
    parser.add_argument("--stage", choices=(*STAGES, "all"), default="all")
    parser.add_argument("--left-run", required=True)
    parser.add_argument("--left-attempt", required=True)
    parser.add_argument("--left-label", default="direct")
    parser.add_argument(
        "--left-column", default=None,
        help="owner decision 172: read this arm as a supply-variant COLUMN of --left-run",
    )
    parser.add_argument("--right-run", required=True)
    parser.add_argument("--right-attempt", required=True)
    parser.add_argument("--right-label", default="plan")
    parser.add_argument(
        "--right-column", default=None,
        help="owner decision 172: read this arm as a supply-variant COLUMN of --right-run",
    )
    parser.add_argument("--scorer-id", default=DEFAULT_SCORER)
    parser.add_argument("--roster", default=DEFAULT_ROSTER)
    parser.add_argument("--cluster-key", default=DEFAULT_CLUSTER_KEY)
    parser.add_argument("--analysis-root", required=True)
    parser.add_argument("--repo-root", default=str(_DRIVER_REPO_ROOT))
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--draws", type=int, default=DEFAULT_DRAWS)
    parser.add_argument("--recipe-id", default=None)
    parser.add_argument("--title", default=DEFAULT_TITLE)
    parser.add_argument("--split-identity-hash", default=None)
    parser.add_argument(
        "--expected-split-role", choices=ALLOWED_SOURCE_SPLIT_ROLES, default="dev",
        help="source roster and manifest role; discovery requires the TRAIN official scorer, "
             "final-report requires the TEST official scorer (stage3_paired_read.run_package "
             "gates final-report further: owner allowance, recipe scorer, aggregate "
             "stratification and countersignature, before this argv is ever built)",
    )
    parser.add_argument(
        "--stage3-algorithm", default=None,
        help=(
            "registered Stage-3 algorithm id (core.base.STAGE3_ALGORITHMS); the default "
            "resolves the label from the experiment fragment that owns --right-run"
        ),
    )
    ns = parser.parse_args(argv)
    return Args(
        stage=ns.stage,
        left=ArmSpec(ns.left_label, ns.left_run, ns.left_attempt, ns.left_column),
        right=ArmSpec(ns.right_label, ns.right_run, ns.right_attempt, ns.right_column),
        scorer_id=ns.scorer_id,
        roster_relpath=ns.roster,
        cluster_key=ns.cluster_key,
        analysis_root=Path(ns.analysis_root),
        repo_root=Path(ns.repo_root),
        data_root=Path(ns.data_root),
        seed=ns.seed,
        draws=ns.draws,
        recipe_id=ns.recipe_id,
        title=ns.title,
        split_identity_hash=ns.split_identity_hash,
        expected_split_role=ns.expected_split_role,
        stage3_algorithm=_stage3_algorithm_block(
            Path(ns.repo_root), ns.right_run, ns.stage3_algorithm
        ),
    )


def _stage3_algorithm_block(
    repo_root: Path, run_id: str, override_id: str | None
) -> dict | None:
    """The right arm's Stage-3 algorithm label, or ``None`` (owner decision
    101). A Stage-2 read of two sealed arms has no label and writes none."""

    src = str(Path(repo_root) / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    from speech_aware_evidence_acquisition.core.stage3_algorithms import (  # noqa: PLC0415
        summary_for_run_id,
    )

    return summary_for_run_id(Path(repo_root), run_id, override_id)


# --------------------------------------------------------------------------
# Stage: stop
# --------------------------------------------------------------------------


def _check_score_job(arm: Arm) -> None:
    if len(arm.score_jobs) != 1:
        raise StopStageError(
            f"{arm.spec.label}: expected exactly one score job, found {len(arm.score_jobs)}"
        )
    job = arm.score_jobs[0]
    if job.get("job_id") != arm.spec.attempt_id:
        raise StopStageError(
            f"{arm.spec.label}: score job id {job.get('job_id')!r} != attempt "
            f"{arm.spec.attempt_id!r}"
        )


def _check_manifest(
    arm: Arm, roster: Roster, expected_split_hash: str, expected_split_role: str
) -> None:
    if arm.manifest.get("status") != "COMPLETED":
        raise StopStageError(f"{arm.spec.label}: manifest status is not COMPLETED")
    if arm.spec.column is None:
        pin = arm.manifest.get("scores") or {}
        if pin.get("sha256") != arm.scores_sha256:
            raise StopStageError(f"{arm.spec.label}: manifest does not pin the sealed score bytes")
        if Path(pin.get("path", "")).name != arm.scores_path.name:
            raise StopStageError(f"{arm.spec.label}: manifest score path does not name this file")
    # A column's score is a SEPARATELY sealed derived artifact, not what this manifest's own
    # ``scores`` pin names -- its binding to this exact manifest is the derived receipt's own
    # ``parent_manifest_sha256`` (checked at load time in ``load_arm`` and, for a pair, by
    # ``_assert_column_pair_invariants``'s AT4 refusal), so the ordinary pin check above does not
    # apply to it.
    split = arm.manifest.get("split") or {}
    if split.get("role") != expected_split_role:
        raise StopStageError(
            f"{arm.spec.label}: split role is not {expected_split_role!r}"
        )
    if split.get("identity_hash") != expected_split_hash:
        raise StopStageError(
            f"{arm.spec.label}: manifest split identity_hash does not match the roster"
        )
    dirt = arm.manifest.get("study_repo_dirt")
    if dirt != []:
        raise StopStageError(f"{arm.spec.label}: manifest was sealed with a dirty study tree")


def _check_attempt_finalized(arm: Arm) -> None:
    if arm.attempt_record.get("state") != "FINALIZED":
        raise StopStageError(f"{arm.spec.label}: attempt state is not FINALIZED")


def _per_sample_ids(arm: Arm, scorer_id: str) -> set[str]:
    entry = arm.scores.get(scorer_id)
    if not isinstance(entry, dict):
        raise StopStageError(f"{arm.spec.label}: scores carry no scorer {scorer_id!r}")
    rows = entry.get("per_sample")
    if not isinstance(rows, list) or not rows:
        raise StopStageError(f"{arm.spec.label}: scorer {scorer_id!r} has no per_sample rows")
    ids: set[str] = set()
    for row in rows:
        sid = row.get("sample_id")
        if not isinstance(sid, str) or not sid:
            raise StopStageError(f"{arm.spec.label}: a per_sample row has no usable sample_id")
        if sid in ids:
            raise StopStageError(f"{arm.spec.label}: per_sample repeats sample_id {sid!r}")
        ids.add(sid)
    return ids


def _reproduce_official(arm: Arm, scorer_id: str, roster: Roster) -> dict[str, dict]:
    entry = arm.scores[scorer_id]
    official = (entry.get("aggregate") or {}).get("official") or {}
    rows = {row["sample_id"]: row for row in entry["per_sample"]}
    result: dict[str, dict] = {}
    for metric, groups in MICRO_METRICS.items():
        recomputed = pooled_f1(rows, roster.ids, groups)
        published = official.get(OFFICIAL_FIELD[metric])
        if not isinstance(published, (int, float)) or isinstance(published, bool):
            raise StopStageError(
                f"{arm.spec.label}: official aggregate has no numeric "
                f"{OFFICIAL_FIELD[metric]!r} field"
            )
        diff = abs(recomputed - float(published))
        if diff > 1e-6:
            raise StopStageError(
                f"{arm.spec.label}: recomputed {metric} ({recomputed}) does not reproduce the "
                f"official aggregate ({published}) to 1e-6 (diff {diff})"
            )
        result[metric] = {"recomputed": recomputed, "official": float(published), "diff": diff}
    return result


def stage_stop(args: Args, left: Arm, right: Arm, roster: Roster) -> dict:
    """Verify the sealed bytes; raise :class:`StopStageError` loudly on any mismatch and write
    NOTHING in that case. On success, write and return ``stop.json``."""

    computed_hash = split_identity_hash(prefixed(roster.carrier_lock_key, roster.ids))
    registered_hash = roster.document.get("split_identity_hash")
    if computed_hash != registered_hash:
        raise StopStageError(
            "roster's own recorded split_identity_hash does not reproduce from its ids "
            f"(computed {computed_hash}, recorded {registered_hash})"
        )
    if args.split_identity_hash and args.split_identity_hash != computed_hash:
        raise StopStageError(
            "roster split_identity_hash does not match --split-identity-hash "
            f"(computed {computed_hash}, expected {args.split_identity_hash})"
        )

    if args.expected_split_role not in ALLOWED_SOURCE_SPLIT_ROLES:
        raise StopStageError("source split role is not permitted for this read")
    if roster.document.get("split_role") != args.expected_split_role:
        raise StopStageError("roster split role does not match the expected source role")
    if args.expected_split_role == "discovery":
        if args.scorer_id != "slurp-slu-official-train":
            raise StopStageError("discovery source requires the TRAIN official scorer")
        if roster.carrier_lock_key != "slurp" or any(
            not sid.startswith("slurp:train:") for sid in roster.ids
        ):
            raise StopStageError("discovery source requires SLURP TRAIN sample identities")
    if args.expected_split_role == "final-report":
        # Defense in depth beside ``run_package``'s own condition (b): this driver never opens a
        # final-report roster's scores under any scorer but the TEST official one, whoever calls it.
        if args.scorer_id != "slurp-slu-official-test":
            raise StopStageError("final-report source requires the TEST official scorer")

    for arm in (left, right):
        _check_attempt_finalized(arm)
        _check_manifest(arm, roster, computed_hash, args.expected_split_role)
        _check_score_job(arm)
        sample_ids = _per_sample_ids(arm, args.scorer_id)
        if sample_ids != set(roster.ids):
            missing = sorted(set(roster.ids) - sample_ids)[:5]
            extra = sorted(sample_ids - set(roster.ids))[:5]
            raise StopStageError(
                f"{arm.spec.label}: per_sample ids do not equal the roster ids "
                f"(missing sample {missing}, extra sample {extra})"
            )

    reproduction = {
        left.spec.label: _reproduce_official(left, args.scorer_id, roster),
        right.spec.label: _reproduce_official(right, args.scorer_id, roster),
    }

    payload = {
        "schema": SCHEMA_STOP,
        "contacts": dict(CONTACTS_ZERO),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scorer_id": args.scorer_id,
        "roster": {
            "relpath": args.roster_relpath,
            "sha256": roster.sha256,
            "rows": len(roster.ids),
            "split_identity_hash": computed_hash,
            "carrier_lock_key": roster.carrier_lock_key,
            **({"split_role": "discovery"} if args.expected_split_role == "discovery" else {}),
        },
        "left": {
            "label": left.spec.label,
            "run_id": left.spec.run_id,
            "attempt_id": left.spec.attempt_id,
            "manifest_sha256": left.manifest_sha256,
            "scores_sha256": left.scores_sha256,
        },
        "right": {
            "label": right.spec.label,
            "run_id": right.spec.run_id,
            "attempt_id": right.spec.attempt_id,
            "manifest_sha256": right.manifest_sha256,
            "scores_sha256": right.scores_sha256,
        },
        "official_reproduction_1e6": reproduction,
        "status": "PASSED",
        "driver_sha256": digest(_DRIVER_PATH),
    }
    write_json(args.analysis_root / "stop.json", payload)
    return payload


# --------------------------------------------------------------------------
# Stage: structural
# --------------------------------------------------------------------------


def _iter_outputs_structural(path: Path) -> list[dict]:
    """Read ``<run>.outputs.jsonl`` and drop the ``"text"`` (and every other free-text) field on
    read -- only ids and structural sub-objects (``native_episode_receipt``, ``admitted``, ...)
    survive into the returned rows. Never re-serialised with ``text`` present."""

    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            row.pop("text", None)
            rows.append(row)
    return rows


def _arm_structural_summary(arm: Arm) -> dict:
    rows = _iter_outputs_structural(arm.artifact("outputs.jsonl"))
    admitted_counts = Counter(bool(row.get("admitted")) for row in rows)
    generation_cost = arm.generation_manifest.get("cost") or {}

    has_native_episode = any("native_episode_receipt" in row for row in rows)
    summary: dict[str, object] = {
        "rows": len(rows),
        "admitted_true": admitted_counts.get(True, 0),
        "admitted_false": admitted_counts.get(False, 0),
        "tool_calls": generation_cost.get("tool_calls"),
        "tool_calls_zero": generation_cost.get("tool_calls") == 0,
        "has_native_episode_receipt": has_native_episode,
    }

    if has_native_episode:
        planner_actions: Counter = Counter()
        revisions_executed = 0
        role_visit_counts: Counter = Counter()
        normaliser_applied: Counter = Counter()
        normaliser_changed: Counter = Counter()
        normaliser_label_branch: Counter = Counter()
        compacted_rows = 0
        compacted_contacts_total = 0
        for row in rows:
            receipt = row.get("native_episode_receipt") or {}
            for route in receipt.get("planner_routes") or []:
                planner_actions[route.get("action")] += 1
                revisions_executed += int(route.get("revision_count") or 0)
            role_visit_counts[len(receipt.get("role_visits") or [])] += 1
            normaliser = receipt.get("deliver_normaliser") or {}
            normaliser_applied[bool(normaliser.get("applied"))] += 1
            normaliser_changed[bool(normaliser.get("changed"))] += 1
            if normaliser.get("label_branch") is not None:
                normaliser_label_branch[normaliser["label_branch"]] += 1
            context_fit = receipt.get("context_fit") or {}
            compacted = int(context_fit.get("compacted_contacts") or 0)
            compacted_contacts_total += compacted
            if compacted > 0:
                compacted_rows += 1
        summary.update(
            {
                "planner_action_histogram": dict(planner_actions),
                "revisions_executed": revisions_executed,
                "role_visits_per_row_histogram": {
                    str(k): v for k, v in sorted(role_visit_counts.items())
                },
                "deliver_normaliser_applied_histogram": {
                    str(k): v for k, v in normaliser_applied.items()
                },
                "deliver_normaliser_changed_histogram": {
                    str(k): v for k, v in normaliser_changed.items()
                },
                "deliver_normaliser_label_branch_histogram": dict(normaliser_label_branch),
                "context_fit_compacted_rows": compacted_rows,
                "context_fit_compacted_contacts_total": compacted_contacts_total,
            }
        )
    return summary


def stage_structural(args: Args, left: Arm, right: Arm) -> dict:
    payload = {
        "schema": SCHEMA_STRUCTURAL,
        "contacts": dict(CONTACTS_ZERO),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "left": {"label": left.spec.label, **_arm_structural_summary(left)},
        "right": {"label": right.spec.label, **_arm_structural_summary(right)},
        "inputs_sha256": {
            "left_outputs": digest(left.artifact("outputs.jsonl")),
            "right_outputs": digest(right.artifact("outputs.jsonl")),
        },
        "driver_sha256": digest(_DRIVER_PATH),
    }
    write_json(args.analysis_root / "structural.json", payload)
    return payload


# --------------------------------------------------------------------------
# Stage: contrast
# --------------------------------------------------------------------------


def _rows_table(arm: Arm, scorer_id: str) -> dict[str, dict[str, float]]:
    """``{sample_id: {field: float}}`` for every numeric/boolean field a per_sample row carries.
    Refuses (rather than silently drops) any field whose value is a string -- the one shape a
    stray text field would take."""

    entry = arm.scores[scorer_id]
    table: dict[str, dict[str, float]] = {}
    for row in entry["per_sample"]:
        sid = row["sample_id"]
        values: dict[str, float] = {}
        for key, value in row.items():
            if key == "sample_id":
                continue
            if isinstance(value, str):
                raise ReadDriverError(
                    f"per_sample row {sid!r} field {key!r} is text; refusing to load it into a "
                    "contrast table"
                )
            if isinstance(value, bool):
                values[key] = 1.0 if value else 0.0
            elif isinstance(value, (int, float)):
                values[key] = float(value)
        table[sid] = values
    return table


def _pooled_contrast_block(
    left_rows: Mapping[str, Mapping[str, float]],
    right_rows: Mapping[str, Mapping[str, float]],
    ids: Sequence[str],
    groups: tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]],
    *,
    cluster_of: Callable[[str], str],
    seed: int,
    draws: int,
) -> dict:
    def statistic(resampled: Sequence[str]) -> float:
        return pooled_f1(right_rows, resampled, groups) - pooled_f1(left_rows, resampled, groups)

    result = resampled_statistic(
        sample_ids=ids,
        statistic=statistic,
        seed=seed,
        n_replicates=draws,
        ci_level=0.95,
        cluster_of=cluster_of,
    )
    return {
        "left_pct": 100 * pooled_f1(left_rows, ids, groups),
        "right_pct": 100 * pooled_f1(right_rows, ids, groups),
        "delta_pp": 100 * result.point_estimate,
        "cluster_bootstrap": interval_block(result.replicates, result.point_estimate, seed),
    }


def _per_row_block(
    left_rows: Mapping[str, Mapping[str, float]],
    right_rows: Mapping[str, Mapping[str, float]],
    ids: Sequence[str],
    *,
    cluster_of: Callable[[str], str] | None,
    strata_of: Callable[[str], str] | None,
    seed: int,
    draws: int,
) -> dict[str, dict]:
    contrasts = paired_contrast(
        left_rows,
        right_rows,
        metrics=PER_ROW_METRICS,
        sample_ids=ids,
        cluster_of=cluster_of,
        strata_of=strata_of,
        seed=seed,
        n_replicates=draws,
        ci_level=0.95,
    )
    out: dict[str, dict] = {}
    for metric, contrast in contrasts.items():
        entry: dict[str, object] = {
            "estimand": "mean-per-row",
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
        if contrast.per_stratum:
            entry["per_stratum"] = {
                name: row.as_dict() for name, row in sorted(contrast.per_stratum.items())
            }
        out[metric] = entry
    return out


CONSTRUCTION_SCENARIO_REASON = (
    "This paired driver does not compute a per-scenario table on the TRAIN "
    "construction roster. The separately registered VAR-1 family read derives "
    "that table from the roster receipt's per-item stratum; no per-row scenario "
    "is inferred from model output or opened from gold here."
)

PER_SCENARIO_NOT_AVAILABLE_REASON = (
    "No model-free per-row scenario label exists for this roster. The roster "
    "(docs/receipts/rosters/slurp-dev-2000-added-v1.json) sets "
    "\"stratum_withheld_per_item\": true and its items carry only "
    "{audio_seconds, headset, id, key, sample_id, utterance_id} -- no scenario field -- "
    "and the official slurp-slu-official per_sample rows carry only exact-match flags and "
    "tp/fp/fn counts (no scenario field either; verified against the sealed TRAIN Fold A "
    "precedent's per_sample schema, which is identical). The roster's own "
    "scenario_allocation/strata_counts blocks are AGGREGATE roster-design totals, not a "
    "per-row join key, and reading gold to recover a per-row scenario would violate the "
    "runtime-gold-free discipline. Per owner decision 79 D3 both weightings would be reported "
    "if a per-row scenario were available; neither the natural-mixture per-scenario table nor "
    "the equal-scenario weighting can be computed here."
)


def stage_contrast(args: Args, left: Arm, right: Arm, roster: Roster) -> tuple[dict, dict]:
    """The paired estimators.

    Per-scenario table: NOT AVAILABLE. Cell B6's roster withholds the per-item scenario
    (``stratum_withheld_per_item: true``) and the ``slurp-slu-official`` per_sample rows carry no
    scenario field either (checked against both this cell's own sealed direct-arm scores and the
    read-only TRAIN Fold A precedent). Reading SLURP's gold annotations to recover it would put
    gold into a runtime read, which this repository's research boundary forbids. The recipe's
    ``reported_beside``/decision-79-D3 per-scenario and equal-scenario-weighting tables are
    therefore written to ``per-scenario-tables.json`` as an explicit NOT AVAILABLE record with the
    reason above, never silently dropped.
    """

    left_rows = _rows_table(left, args.scorer_id)
    right_rows = _rows_table(right, args.scorer_id)
    ids = list(roster.ids)

    def cluster_of(sample_id: str) -> str:
        return roster.cluster_of_id[sample_id]

    def channel_of(sample_id: str) -> str:
        return roster.channel_of_id[sample_id]

    pooled_micro: dict[str, dict] = {}
    for metric, groups in MICRO_METRICS.items():
        pooled_micro[metric] = {
            "estimand": "pooled-count-f1",
            "official_check_field": OFFICIAL_FIELD[metric],
            "fields": {"tp": list(groups[0]), "fp": list(groups[1]), "fn": list(groups[2])},
            **_pooled_contrast_block(
                left_rows,
                right_rows,
                ids,
                groups,
                cluster_of=cluster_of,
                seed=args.seed,
                draws=args.draws,
            ),
        }

    per_row = _per_row_block(
        left_rows, right_rows, ids, cluster_of=cluster_of, strata_of=None,
        seed=args.seed, draws=args.draws,
    )

    # Per-channel breakdown is deliberately UNCLUSTERED: a doubled utterance's two recordings can
    # differ in channel (headset vs far-field is a property of the RECORDING, cluster_key=
    # utterance_id is a property of the UTTERANCE), so a channel stratum can legitimately split a
    # cluster across itself -- paired_contrast refuses that combination when cluster_of and
    # strata_of are both given (every cluster member must share one stratum). The per-channel
    # table is therefore the plain per-row descriptive breakdown (paired.PairedContrast's own
    # per_stratum rows: n/left/right/delta/saves/harms/ties, no per-stratum CI is computed by that
    # machinery either way), never a clustered one.
    per_channel = _per_row_block(
        left_rows, right_rows, ids, cluster_of=None, strata_of=channel_of,
        seed=args.seed, draws=args.draws,
    )
    per_channel_table = {
        metric: entry.get("per_stratum", {}) for metric, entry in per_channel.items()
    }

    # Q4 ruling (owner decision 172): a same-flight column pair resamples by row, but the
    # utterance-level number (the ROLL-3 whole-utterance bootstrap) is reported BESIDE it and
    # never gates -- computed here from the SAME roster document's own utterance_id field (no
    # second roster load), added only for a column pair so an ordinary pair's score-contrasts.json
    # stays byte-identical to its pre-decision-172 self.
    utterance_level_reported = None
    if left.spec.column is not None or right.spec.column is not None:
        utterance_of_id = {
            item.get("sample_id") or item.get("id"): item.get("utterance_id")
            for item in roster.document.get("items", [])
        }
        if all(isinstance(utterance_of_id.get(sid), str) for sid in ids):
            utterance_level_reported = {
                "cluster_key": "utterance_id",
                "note": (
                    "ROLL-3 whole-utterance bootstrap, reported beside the row-clustered read "
                    "above; never gates (Q4 ruling)"
                ),
                "per_row": _per_row_block(
                    left_rows, right_rows, ids, cluster_of=utterance_of_id.get, strata_of=None,
                    seed=args.seed, draws=args.draws,
                ),
            }

    score_contrasts = {
        "schema": SCHEMA_CONTRAST,
        "contacts": dict(CONTACTS_ZERO),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scorer_id": args.scorer_id,
        "cluster_key": args.cluster_key,
        "sign_convention": (
            f"delta = right({right.spec.label}) minus left({left.spec.label}); "
            + (
                "positive means the plan arm scores higher"
                if args.expected_split_role == "dev"
                else "positive means the right variant scores higher"
            )
        ),
        "left": left.spec.label,
        "right": right.spec.label,
        "n_rows": len(ids),
        "pooled_micro": pooled_micro,
        "per_row": per_row,
        "per_channel": per_channel_table,
        "driver_sha256": digest(_DRIVER_PATH),
    }
    if utterance_level_reported is not None:
        score_contrasts["utterance_level_reported"] = utterance_level_reported

    scenario_reason = (
        CONSTRUCTION_SCENARIO_REASON if args.expected_split_role == "discovery"
        else PER_SCENARIO_NOT_AVAILABLE_REASON
    )
    per_scenario_tables = {
        "schema": SCHEMA_SCENARIO,
        "contacts": dict(CONTACTS_ZERO),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "natural_mixture": {"status": "NOT_AVAILABLE", "reason": scenario_reason},
        "equal_scenario_weighting": {
            "status": "NOT_AVAILABLE",
            "reason": scenario_reason,
        },
        "roster_scenario_allocation_aggregate_only": roster.document.get("scenario_allocation"),
        "driver_sha256": digest(_DRIVER_PATH),
    }

    write_json(args.analysis_root / "score-contrasts.json", score_contrasts)
    write_json(args.analysis_root / "per-scenario-tables.json", per_scenario_tables)
    return score_contrasts, per_scenario_tables


# --------------------------------------------------------------------------
# Stage: efficiency
# --------------------------------------------------------------------------


def _arm_efficiency(arm: Arm) -> dict:
    cost = arm.generation_manifest.get("cost") or {}
    rows = arm.rows or 1
    entry: dict[str, object] = {
        "rows": arm.rows,
        "contacts": cost.get("calls_used"),
        "contacts_per_row": (cost.get("calls_used") or 0) / rows,
        "repeated_speech_seconds": cost.get("audio_seconds_used"),
        "prompt_tokens_total": cost.get("prompt_tokens_total"),
        "prompt_tokens_per_row": (cost.get("prompt_tokens_total") or 0) / rows,
        "completion_tokens_total": cost.get("completion_tokens_total"),
        "completion_tokens_per_row": (cost.get("completion_tokens_total") or 0) / rows,
        "tool_calls": cost.get("tool_calls"),
    }
    rec = arm.flight_receipts
    if rec:
        seal = (rec.get("stages") or {}).get("seal") or {}
        monitor = seal.get("serving_monitor_summary")
        if monitor:
            gpu_hours = monitor["active_seconds"] / 3600.0
            entry.update(
                {
                    "gpu_active_seconds": monitor["active_seconds"],
                    "gpu_hours": gpu_hours,
                    "gpu_hours_per_1000_rows": gpu_hours * 1000.0 / rows,
                    "monitor_wall_seconds": monitor.get("wall_seconds"),
                    "mean_utilization_percent": monitor.get("mean_utilization_percent"),
                }
            )
        run_phases = (rec.get("stages") or {}).get("run_phases")
        if run_phases:
            entry.update(
                {
                    "generation_wall_seconds": run_phases.get("wall_seconds"),
                    "contacts_per_minute": (run_phases.get("contacts_per_second") or 0) * 60.0,
                }
            )
    return entry


def stage_efficiency(args: Args, left: Arm, right: Arm) -> dict:
    left_entry = _arm_efficiency(left)
    right_entry = _arm_efficiency(right)
    delta: dict[str, float] = {}
    for key in sorted(set(left_entry) & set(right_entry)):
        lv, rv = left_entry[key], right_entry[key]
        if isinstance(lv, (int, float)) and not isinstance(lv, bool) and isinstance(
            rv, (int, float)
        ) and not isinstance(rv, bool):
            delta[key] = rv - lv

    inputs = {
        "left_generation_manifest": left.generation_manifest_sha256,
        "right_generation_manifest": right.generation_manifest_sha256,
    }
    if left.flight_receipts_path.exists():
        inputs["left_flight_receipts"] = digest(left.flight_receipts_path)
    if right.flight_receipts_path.exists():
        inputs["right_flight_receipts"] = digest(right.flight_receipts_path)

    payload = {
        "schema": SCHEMA_EFFICIENCY,
        "contacts": dict(CONTACTS_ZERO),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "left": {"label": left.spec.label, **left_entry},
        "right": {"label": right.spec.label, **right_entry},
        "delta_right_minus_left": delta,
        "inputs_sha256": inputs,
        "driver_sha256": digest(_DRIVER_PATH),
    }
    write_json(args.analysis_root / "efficiency.json", payload)
    return payload


# --------------------------------------------------------------------------
# Stage: verdict
# --------------------------------------------------------------------------

CONSTRUCTION_NOT_CLAIMED = (
    "NO ADMISSION OR SUPERIORITY VERDICT.",
    "NO GENERALIZATION OR PAPER-SCALE CLAIM: this is a TRAIN construction roster.",
    "NO CLAIM ABOUT OTHER CARRIERS.",
)

NOT_CLAIMED = (
    "NO ADMISSION OR SUPERIORITY VERDICT.",
    "NO GENERALIZATION OR PAPER-SCALE CLAIM: DEV-2000-ADDED is a development roster "
    "(owner decision 28).",
    "NO CLAIM ABOUT OTHER CARRIERS.",
)


def _require_artifact(analysis_root: Path, name: str) -> dict:
    path = analysis_root / name
    if not path.exists():
        raise ReadDriverError(
            f"verdict stage requires {name}, which has not been written -- run the earlier "
            "stages first (or --stage all)"
        )
    return load_json(path)


def _render_pooled_table(pooled_micro: dict) -> list[str]:
    lines = [
        "| metric | left % | right % | delta pp | CI95 pp | CI90 pp |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for metric in sorted(pooled_micro):
        entry = pooled_micro[metric]
        cb = entry["cluster_bootstrap"]
        lines.append(
            f"| {metric} | {_fmt(entry['left_pct'])} | {_fmt(entry['right_pct'])} | "
            f"{_fmt(entry['delta_pp'])} | [{_fmt(cb['ci95_pp'][0])}, {_fmt(cb['ci95_pp'][1])}] | "
            f"[{_fmt(cb['ci90_pp'][0])}, {_fmt(cb['ci90_pp'][1])}] |"
        )
    return lines


def _render_per_row_table(per_row: dict) -> list[str]:
    lines = [
        "| metric | left % | right % | delta pp | saves | harms | ties | McNemar p | CI95 pp |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for metric in sorted(per_row):
        entry = per_row[metric]
        cb = entry.get("cluster_bootstrap") or {}
        ci95 = cb.get("ci95_pp", [None, None])
        lines.append(
            f"| {metric} | {_fmt(entry['left_pct'])} | {_fmt(entry['right_pct'])} | "
            f"{_fmt(entry['delta_pp'])} | {entry['saves']} | {entry['harms']} | {entry['ties']} | "
            f"{_fmt(entry['mcnemar_p'], 6)} | [{_fmt(ci95[0])}, {_fmt(ci95[1])}] |"
        )
    return lines


def _render_channel_table(per_channel: dict) -> list[str]:
    lines = [
        "| metric | channel | n | left % | right % | delta pp | saves | harms | ties |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for metric in sorted(per_channel):
        for channel in sorted(per_channel[metric]):
            row = per_channel[metric][channel]
            lines.append(
                f"| {metric} | {channel} | {row['n']} | {_fmt(row['left_mean'] * 100)} | "
                f"{_fmt(row['right_mean'] * 100)} | {_fmt(row['delta'] * 100)} | "
                f"{row['saves']} | {row['harms']} | {row['ties']} |"
            )
    return lines


def _render_efficiency_table(efficiency: dict) -> list[str]:
    left_e, right_e, delta = efficiency["left"], efficiency["right"], efficiency["delta_right_minus_left"]
    fields = [
        ("contacts", 0),
        ("contacts_per_row", 4),
        ("prompt_tokens_per_row", 1),
        ("completion_tokens_per_row", 1),
        ("gpu_hours", 4),
        ("gpu_hours_per_1000_rows", 4),
    ]
    lines = ["| field | left | right | delta (right-left) |", "| --- | --- | --- | --- |"]
    for field_name, digits in fields:
        lines.append(
            f"| {field_name} | {_fmt(left_e.get(field_name), digits)} | "
            f"{_fmt(right_e.get(field_name), digits)} | {_fmt(delta.get(field_name), digits)} |"
        )
    return lines


def _readme(args: Args, stop: dict, structural: dict, contrast: dict, per_scenario: dict,
            efficiency: dict, written: dict[str, str]) -> str:
    lines = [f"# {args.title}", "", f"Generated: {datetime.now(timezone.utc).isoformat()}", ""]
    if args.recipe_id:
        lines += [f"Recipe: `{args.recipe_id}`", ""]
    construction = args.expected_split_role == "discovery"
    claimed = CONSTRUCTION_NOT_CLAIMED if construction else NOT_CLAIMED
    status_explanation = (
        "**DESCRIPTIVE.** This TRAIN construction-roster paired read reports no "
        "admission or superiority verdict. The registered VAR-1 family read "
        "applies the roster's own null before any variant is interpreted."
        if construction else
        "**DESCRIPTIVE.** No admission or superiority verdict is read from this cell "
        "(owner decision 86: development numbers carry no bar). This is the fresh-roster "
        "generalisation read of the already-locked v2.0 default plan against the bare "
        "frozen core."
    )
    lines += [
        "## Status",
        "",
        status_explanation,
        "",
        "Not claimed:",
        "",
    ]
    lines += [f"- {item}" for item in claimed]
    lines += [
        "",
        "## Arms",
        "",
        f"- left ({stop['left']['label']}): `{stop['left']['run_id']}` / "
        f"`{stop['left']['attempt_id']}`",
        f"- right ({stop['right']['label']}): `{stop['right']['run_id']}` / "
        f"`{stop['right']['attempt_id']}`",
        f"- scorer: `{stop['scorer_id']}`; roster rows: {stop['roster']['rows']}; "
        f"cluster key: `{contrast['cluster_key']}`",
        "",
        "## Pooled micro (official-check fields)",
        "",
        *_render_pooled_table(contrast["pooled_micro"]),
        "",
        "## Per-row metrics",
        "",
        *_render_per_row_table(contrast["per_row"]),
        "",
        "## Per-channel (headset vs far-field)",
        "",
        *_render_channel_table(contrast["per_channel"]),
        "",
        "## Per-scenario",
        "",
        f"NOT AVAILABLE. {per_scenario['natural_mixture']['reason']}",
        "",
        "## Efficiency",
        "",
        *_render_efficiency_table(efficiency),
        "",
        "## Structural",
        "",
        f"- left rows: {structural['left']['rows']}, tool_calls_zero: "
        f"{structural['left']['tool_calls_zero']}",
        f"- right rows: {structural['right']['rows']}, tool_calls_zero: "
        f"{structural['right']['tool_calls_zero']}",
        "",
        "## Artefact hashes",
        "",
        "| artefact | sha256 |",
        "| --- | --- |",
    ]
    for name in sorted(written):
        lines.append(f"| {name} | {written[name]} |")
    lines.append("")
    return "\n".join(lines)


def stage_verdict(args: Args) -> dict:
    stop = _require_artifact(args.analysis_root, "stop.json")
    structural = _require_artifact(args.analysis_root, "structural.json")
    contrast = _require_artifact(args.analysis_root, "score-contrasts.json")
    per_scenario = _require_artifact(args.analysis_root, "per-scenario-tables.json")
    efficiency = _require_artifact(args.analysis_root, "efficiency.json")

    written = {
        "stop.json": digest(args.analysis_root / "stop.json"),
        "structural.json": digest(args.analysis_root / "structural.json"),
        "score-contrasts.json": digest(args.analysis_root / "score-contrasts.json"),
        "per-scenario-tables.json": digest(args.analysis_root / "per-scenario-tables.json"),
        "efficiency.json": digest(args.analysis_root / "efficiency.json"),
    }
    written["driver.py"] = digest(_DRIVER_PATH)

    readme_text = _readme(args, stop, structural, contrast, per_scenario, efficiency, written)
    readme_path = args.analysis_root / "README.md"
    readme_path.parent.mkdir(parents=True, exist_ok=True)
    with readme_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(readme_text)
    written["README.md"] = digest(readme_path)

    verdict = {
        "schema": SCHEMA_VERDICT,
        "contacts": dict(CONTACTS_ZERO),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "DESCRIPTIVE",
        "not_claimed": list(
            CONSTRUCTION_NOT_CLAIMED if args.expected_split_role == "discovery" else NOT_CLAIMED
        ),
        "recipe_id": args.recipe_id,
        "artifact_sha256": written,
    }
    # Owner decision 101: every Stage-3 verdict table names its training-free RL.
    if args.stage3_algorithm is not None:
        verdict["stage3_algorithm"] = dict(args.stage3_algorithm)
    # AT5 / Q6 ruling (owner decision 172): a Solver-local column effect never supports a
    # system-level claim -- the field is added ONLY for a column pair, so an ordinary
    # (non-column) verdict stays byte-identical to its pre-decision-172 self.
    if args.left.column is not None or args.right.column is not None:
        verdict["claim"] = "nominated"
    write_json(args.analysis_root / "verdict.json", verdict)
    return verdict


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------


def _assert_column_pair_invariants(left: Arm, right: Arm, args: Args) -> None:
    """Owner decision 172 section 3: a column pair's two invariants.

    AT4 same-parent refusal: a column pair compares two arms of the SAME sealed flight, so both
    columns must carry the same ``parent_manifest_sha256``. Q4 ruling: a column pair resamples by
    row (``cluster_key`` ``sample_id``), never by utterance. Both are no-ops for an ordinary
    (non-column) pair.
    """

    if left.spec.column is None and right.spec.column is None:
        return
    if args.cluster_key != "sample_id":
        raise StopStageError(
            "a same-flight supply-variant column pair resamples by row (cluster_key "
            f"'sample_id'); {args.cluster_key!r} is refused (Q4 ruling)"
        )
    if left.spec.column is not None and right.spec.column is not None:
        if left.parent_manifest_sha256 != right.parent_manifest_sha256:
            raise StopStageError(
                "AT4: column pair refused -- left and right columns carry different "
                f"parent_manifest_sha256 ({left.parent_manifest_sha256!r} != "
                f"{right.parent_manifest_sha256!r}); a column pair compares two arms of the "
                "SAME sealed flight"
            )


def run_stages(args: Args) -> None:
    stages = STAGES if args.stage == "all" else (args.stage,)
    roster = None
    left = right = None
    if {"stop", "structural", "contrast", "efficiency"} & set(stages):
        left = load_arm(args.data_root, args.left, scorer_id=args.scorer_id)
        right = load_arm(args.data_root, args.right, scorer_id=args.scorer_id)
        _assert_column_pair_invariants(left, right, args)
    if {"stop", "contrast"} & set(stages):
        roster = load_roster(args.repo_root, args.roster_relpath, args.cluster_key)

    for stage in stages:
        if stage == "stop":
            stage_stop(args, left, right, roster)
        elif stage == "structural":
            stage_structural(args, left, right)
        elif stage == "contrast":
            stage_contrast(args, left, right, roster)
        elif stage == "efficiency":
            stage_efficiency(args, left, right)
        elif stage == "verdict":
            stage_verdict(args)
        else:  # pragma: no cover - argparse already restricts choices
            raise ReadDriverError(f"unknown stage {stage!r}")


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        run_stages(args)
    except (StopStageError, ReadDriverError) as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
