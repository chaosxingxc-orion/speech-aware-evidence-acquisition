"""Scoring phase: outputs JSONL + reference layers -> frozen-scoring results.

This is the ONLY module allowed to import data.references (AST contract
test). It runs strictly after the runtime phase, on recorded outputs — never
inside a request loop.

Registered SCORERS (R0 repair T8): ``asr-wer`` (WER against the carrier's
frozen ``.nlp`` reference layer) and ``cost`` (the run manifest's cost
block). ``scoring/entity.py`` and ``scoring/qa.py`` are frozen, hash-pinned
functions but have NO registered adapter here: the reference-layer format an
entity/QA adapter would need to consume (the Earnings21 ``wer_tags`` sidecar
JSON + the ``.nlp`` file's own ``wer_tags`` column, which is Python-repr list
syntax, not JSON, and encodes multi-token entity spans by shared entity ID)
was never pinned by an owner-approved readiness memo, and no spoken-QA
carrier has any reference layer wired into ``data/identity.py`` at all. See
``docs/owner-decisions-pending.md`` for what was inspected and what remains
open; do not add a guessed adapter here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from ..data.references import reference_tokens
from ..e0.artifacts import REPO_ROOT
from ..scoring import align, tokens_v1
from ..scoring.transitions import flag_transitions
from .base import SCORERS


class ScoringPhaseError(RuntimeError):
    """Outputs are malformed or reference/hypothesis pairing is impossible."""


def score_asr_outputs(
    outputs_path: Path, lock: Mapping[str, object], root: Path
) -> dict[str, object]:
    try:
        text = Path(outputs_path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ScoringPhaseError(f"cannot read outputs {outputs_path}: {error}") from error
    # Split on the record separator only: json.dumps(ensure_ascii=False) leaves
    # U+2028/U+2029 raw inside string values, and str.splitlines() treats those
    # as line breaks too, which would cut a single valid JSONL row in two.
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if not lines:
        raise ScoringPhaseError(f"outputs file {outputs_path} is empty")
    per_sample: list[dict[str, object]] = []
    for number, line in enumerate(lines, start=1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise ScoringPhaseError(f"outputs line {number} malformed: {error}") from error
        ref = tokens_v1(
            " ".join(reference_tokens(lock, root, row["carrier_lock_key"], row["sample_id"]))
        )
        result = align(ref, tokens_v1(row["text"]))
        per_sample.append(
            {
                "sample_id": row["sample_id"],
                "wer": result.wer,
                "hits": result.hits,
                "substitutions": result.substitutions,
                "deletions": result.deletions,
                "insertions": result.insertions,
                "ref_hit_mask": list(result.ref_hit_mask),
            }
        )
    mean_wer = sum(entry["wer"] for entry in per_sample) / len(per_sample)
    return {
        "per_sample": per_sample,
        "aggregate": {"mean_wer": mean_wer, "samples": len(per_sample)},
    }


def transition_report(
    baseline: Mapping[str, object], treatment: Mapping[str, object]
) -> dict[str, int]:
    base_by_id = {entry["sample_id"]: entry for entry in baseline["per_sample"]}
    treat_by_id = {entry["sample_id"]: entry for entry in treatment["per_sample"]}
    if set(base_by_id) != set(treat_by_id):
        raise ScoringPhaseError("baseline/treatment sample sets differ")
    totals = {
        "correct_to_correct": 0,
        "correct_to_wrong": 0,
        "wrong_to_correct": 0,
        "wrong_to_wrong": 0,
    }
    for sample_id, base in base_by_id.items():
        base_mask = base["ref_hit_mask"]
        treat_mask = treat_by_id[sample_id]["ref_hit_mask"]
        try:
            transitions = flag_transitions(base_mask, treat_mask)
        except ValueError as error:
            raise ScoringPhaseError(str(error)) from error
        totals["correct_to_correct"] += transitions.correct_to_correct
        totals["correct_to_wrong"] += transitions.correct_to_wrong
        totals["wrong_to_correct"] += transitions.wrong_to_correct
        totals["wrong_to_wrong"] += transitions.wrong_to_wrong
    return totals


SCORERS.register("asr-wer", score_asr_outputs)


# ---------------------------------------------------------------------------
# Cost scorer (R0 repair T8, scorer seam): the ONLY scorer that reads the run
# manifest's cost block instead of the outputs JSONL. `score_bundle` calls
# every registered scorer through the SAME uniform signature
# `scorer(outputs_path, lock, root)` -- no special-cased wiring was added for
# "cost" here, deliberately (the anti-fragmentation contract in `core.base`:
# a new component registers, it never grows new driver/score_bundle wiring).
# Instead this scorer reads the ACTUAL T6 run-manifest.json that already
# lives beside `outputs_path` (same run_dir, same run_id stem -- the exact
# naming convention `core.bundle.build_manifest`/`_manifest_document` already
# use) and returns its `cost` block. This is "read the manifest and
# integrate", not a parallel accounting path: no cost number here is computed
# independently of `core.model.FrozenCoreAdapter.cost_summary()`, which is
# the one true place cost is metered (see `core/model.py`).
# ---------------------------------------------------------------------------

_OUTPUTS_SUFFIX = ".outputs.jsonl"
_MANIFEST_SUFFIX = ".run-manifest.json"


def _manifest_path_for_outputs(outputs_path: Path) -> Path:
    outputs_path = Path(outputs_path)
    name = outputs_path.name
    if not name.endswith(_OUTPUTS_SUFFIX):
        raise ScoringPhaseError(
            f"cost scorer requires an outputs artifact named '<run_id>{_OUTPUTS_SUFFIX}', "
            f"got {name!r} -- it cannot locate that run's manifest without the shared "
            "run_id stem core.bundle.build_manifest already uses"
        )
    run_id = name[: -len(_OUTPUTS_SUFFIX)]
    manifest_path = outputs_path.parent / f"{run_id}{_MANIFEST_SUFFIX}"
    if not manifest_path.is_file():
        raise ScoringPhaseError(
            f"cost scorer requires a sibling run manifest at {manifest_path} (same run_dir, "
            f"same run_id as {outputs_path}); none found -- cost is recorded only in the run "
            "manifest, never in outputs.jsonl itself"
        )
    return manifest_path


def score_cost_outputs(
    outputs_path: Path, lock: Mapping[str, object], root: Path
) -> dict[str, object]:
    """Cost scorer: no per-sample breakdown exists (cost is metered per attempt,
    not per sample -- see ``core.model.FrozenCoreAdapter.cost_summary``), so
    ``per_sample`` is always empty and every field lives in ``aggregate``."""

    # Deferred import (not at module top level): `core.bundle` imports THIS
    # module at its own top level (to call `score_bundle` from
    # `finalize_bundle`); importing `core.bundle` back at this module's top
    # level would be a circular import -- same reasoning as `score_bundle`'s
    # own deferred `VerifiedBundle` import below.
    from .bundle import RUN_MANIFEST_SCHEMA

    manifest_path = _manifest_path_for_outputs(Path(outputs_path))
    try:
        raw = manifest_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ScoringPhaseError(f"cannot read run manifest {manifest_path}: {error}") from error
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ScoringPhaseError(f"run manifest {manifest_path} is not valid JSON: {error}") from error
    if not isinstance(document, dict) or document.get("schema") != RUN_MANIFEST_SCHEMA:
        raise ScoringPhaseError(
            f"run manifest {manifest_path} does not carry schema {RUN_MANIFEST_SCHEMA!r}"
        )
    cost = document.get("cost")
    if not isinstance(cost, dict) or not cost:
        raise ScoringPhaseError(
            f"run manifest {manifest_path} carries no cost block to score (an ABORTED attempt "
            "before any request was sent, or a manifest older than the T8 cost scorer)"
        )
    return {"per_sample": [], "aggregate": dict(cost)}


SCORERS.register("cost", score_cost_outputs)


def _assert_scoring_entry_gate(
    bundle: object, lock: Mapping[str, object], repo_root: Path
) -> None:
    """CRITICAL fix (round-2 external-threat-model review): re-verify, IN
    THIS PROCESS, everything a model touch already proves before scoring
    computes or writes anything.

    Before this fix, ``contracts.FrozenCoreGate._validate_scoring_freeze``
    was reachable ONLY via ``contracts.assert_model_touch_allowed`` -- the
    ``saea-driver run`` process, which computes no scores. The processes
    that DO score (``score_bundle``, and everything that calls it --
    ``finalize_bundle``, ``saea-driver score --manifest``, ``saea-driver
    finalize``) constructed no gate at all: with ``align()`` overridden to
    always report a perfect transcription, the model-touch gate correctly
    refused ("scoring freeze drift"), but ``finalize_bundle`` on the SAME
    tree succeeded outright -- a scores artifact was written and the attempt
    FINALIZED. The same root cause left the speech-only scope controls
    (``general_audio_deny_lock_keys``, ``ALLOWED_CARRIER_PROFILES``), which
    also live only inside ``assert_model_touch_allowed``, entirely absent
    from the path that produces the FORMAL record.

    This reuses -- never duplicates -- ``contracts.FrozenCoreGate``'s own
    verification logic (``contracts.py`` is concurrently under edit as part
    of this same review round, so no new hashing/scope logic is added here
    or there; a future public ``contracts.assert_scoring_freeze``-style
    function, if one lands, can replace this construction without changing
    any caller of this function):

    - ``_validate_e0()`` re-verifies the E0 closure receipt's D1-D4 artifact
      hashes and, as part of D3, re-hashes every frozen scoring source
      against the live tree and refuses any unlisted module under
      ``scoring/`` (``FrozenCoreGate._validate_scoring_freeze``).
    - ``_resolve_carrier_dataset_entry(carrier_lock_key, lock)`` is the SAME
      speech-only scope check the model-touch gate applies: refuses a
      general-audio deny-lock-key carrier, or one whose lock profiles do
      not intersect this study's ``ALLOWED_CARRIER_PROFILES``.

    Both methods only ever read ``self.e0_receipt``/``self.source_root``
    (always the REAL checkout, ``REPO_ROOT`` -- the same package
    ``core.scorers`` itself imports ``..scoring`` from; there is exactly one
    scoring package actually executing, never a caller-supplied stand-in)
    and the explicit ``lock`` passed in here; the gate's runtime/session-only
    fields are never read by either method and are filled with an inert
    placeholder (``FrozenCoreGate.for_study_repo``'s own ``repo_root``
    argument, reused for all three positions).

    ``repo_root`` additionally gates a plain clean-tree check
    (``core.bundle.require_clean_study_repo`` -- the SAME rule the run path
    already enforces before spending any budget). The D3 freeze covers only
    ``scoring/*.py``: ``score_asr_outputs`` also imports
    ``data.references.reference_tokens``, which lives OUTSIDE that frozen
    package, so an uncommitted edit there would defeat the freeze check
    alone. Unlike the E0/scope check, this DOES take ``repo_root`` as an
    explicit parameter (default ``REPO_ROOT``, matching
    ``run_experiment_bundled``'s own convention) so tests can point it at an
    isolated synthetic repo rather than depending on this checkout's own
    ambient git status.

    Order matters here: the E0/D3 freeze (and carrier scope) check runs
    BEFORE the clean-tree check, deliberately -- an uncommitted edit to a
    tracked ``scoring/*.py`` file is ALSO, unavoidably, a dirty tree (the
    file lives inside ``repo_root`` too), so checking clean-tree first would
    surface a generic "uncommitted changes" refusal instead of the specific
    "scoring freeze drift" one a reviewer probing the freeze itself expects.
    Reversing the order does not weaken either guarantee: a dirty tree whose
    only change is OUTSIDE ``scoring/`` (e.g. ``data/references.py``) still
    reaches and trips the clean-tree check exactly as before.
    """

    from ..contracts import FrozenCoreGate
    from .bundle import require_clean_study_repo

    plan_meta = bundle.manifest.get("plan")
    carrier_lock_key = (
        plan_meta.get("carrier_lock_key") if isinstance(plan_meta, Mapping) else None
    )
    if not isinstance(carrier_lock_key, str) or not carrier_lock_key.strip():
        raise ScoringPhaseError(
            "verified bundle carries no usable plan.carrier_lock_key; refusing to score "
            "an unscoped bundle"
        )
    gate = FrozenCoreGate.for_study_repo(REPO_ROOT, REPO_ROOT, REPO_ROOT)
    gate._validate_e0()
    gate._resolve_carrier_dataset_entry(carrier_lock_key, lock)
    require_clean_study_repo(Path(repo_root))


def score_bundle(
    bundle: object, lock: Mapping[str, object], root: Path, *, repo_root: Path = REPO_ROOT
) -> dict[str, object]:
    """Manifest-entry scoring seam (R0 repair T6, invariant I7): the ONLY way
    to reach a scorer through this function is with a genuine
    ``core.bundle.VerifiedBundle`` -- something only ``core.bundle.verify_bundle``
    can construct, and only after every I7 cross-check (outputs<->split,
    outputs<->trace, trace-manifest<->raw-trace, every artifact hash) already
    passed. A bare manifest path, a dict, or any other stand-in is refused
    before a single scorer runs -- "refuse to score an unverified bundle" is
    enforced structurally, not by convention.

    Before any scorer runs, :func:`_assert_scoring_entry_gate` re-verifies (in
    THIS process, which never otherwise constructs a
    ``contracts.FrozenCoreGate``) the D3 scoring-source freeze, this study's
    speech-only carrier scope, and a clean study tree -- see that function's
    docstring for the CRITICAL finding this closes.

    Deferred import (not at module top level): ``core.bundle`` imports THIS
    module at its own top level (to call ``score_bundle`` from
    ``finalize_bundle``); importing ``core.bundle`` back at this module's top
    level would be a circular import. By the time this function is actually
    CALLED, both modules have always already finished loading.
    """

    from .bundle import VerifiedBundle

    if not isinstance(bundle, VerifiedBundle):
        raise ScoringPhaseError(
            "score_bundle requires a core.bundle.VerifiedBundle produced by "
            f"core.bundle.verify_bundle; got {type(bundle).__name__} (refusing to score "
            "an unverified bundle)"
        )
    if bundle.outputs_path is None:
        raise ScoringPhaseError("verified bundle carries no outputs artifact to score")
    _assert_scoring_entry_gate(bundle, lock, repo_root)
    scorer_names = bundle.manifest.get("scorers")
    if not isinstance(scorer_names, list) or not scorer_names:
        raise ScoringPhaseError("run manifest carries no configured scorers to run")
    results: dict[str, object] = {}
    for name in scorer_names:
        scorer_fn = SCORERS.resolve(str(name))
        results[str(name)] = scorer_fn(bundle.outputs_path, lock, root)
    return results
