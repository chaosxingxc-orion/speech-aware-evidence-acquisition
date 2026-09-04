"""Scoring phase: outputs JSONL + reference layers -> frozen-scoring results.

This is the ONLY module allowed to import data.references (AST contract
test). It runs strictly after the runtime phase, on recorded outputs — never
inside a request loop.

Registered SCORERS: ``asr-wer`` (R0 repair T8, WER against the carrier's
frozen ``.nlp`` reference layer), ``cost`` (R0 repair T8, the run manifest's
cost block), ``a2t-toolcall`` (P1 scaffold), and ``entity-wer`` (owner
decision D-3, entity-class WER scorer admission -- see
:func:`score_entity_wer_outputs` below). ``scoring/qa.py`` remains frozen,
hash-pinned pure functions with NO registered adapter here: no spoken-QA
carrier has any reference layer wired into ``data/identity.py`` at all, so
registering a QA adapter would mean inventing a new carrier's reference
contract from scratch, not wiring an existing one. See
``docs/owner-decisions-pending.md`` for what remains open there; do not add a
guessed QA adapter here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from ..data.carriers import entity_scoped_carrier_lock_keys
from ..data.references import ReferenceError, reference_entity_mentions, reference_tokens
from ..e0.artifacts import REPO_ROOT
from ..scoring import align, score_entities, tokens_v1
from ..scoring.transitions import flag_transitions
from .base import SCORERS


class ScoringPhaseError(RuntimeError):
    """Outputs are malformed or reference/hypothesis pairing is impossible."""


REFERENCE_READING_SCORERS = frozenset({"asr-wer", "entity-wer", "asr-wer-whisper"})


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


# ---------------------------------------------------------------------------
# Audio2Tool tool-call scorer (P1 scaffold): the function lives in
# reproduction/a2t_scorer.py -- deliberately OUTSIDE the E0 D3 frozen scoring
# package (reproduction/__init__.py's own contract) -- and registers HERE,
# alongside asr-wer/cost, because this module is the one scorer-registration
# site score_bundle resolves names through. Same uniform
# `scorer(outputs_path, lock, root)` signature; gold (expected tool calls)
# enters scorer-side only, via data.audio2tool.load_expected_calls -- never
# through data.references, so this module's "ONLY importer of
# data.references" contract above is untouched.
# ---------------------------------------------------------------------------

from ..reproduction.a2t_scorer import score_audio2tool_outputs  # noqa: E402

SCORERS.register("a2t-toolcall", score_audio2tool_outputs)


# ---------------------------------------------------------------------------
# Entity-class WER scorer (owner decision D-3, entity-class WER scorer
# admission -- carried from the W-A..W-D validation plan's item 6a and
# 2026-08-12-a2-experiment-plan.md's D-3): wires the previously-unregistered
# ``scoring/entity.py`` (``score_entities``) to a reference layer, following
# owner-decisions-pending.md item 1's own format decisions, now resolved:
#
#   1. the ``.nlp`` file's ``wer_tags`` column is Python-repr list syntax,
#      parsed with ``ast.literal_eval`` -- see
#      ``data.references.reference_entity_mentions``.
#   2. an entity ID's member tokens are grouped in reference order, never
#      assumed contiguous -- same function.
#   3. the string ``scoring.entity.score_entities`` compares is the entity
#      MENTION TEXT (the raw reference tokens joined by a space; ``
#      score_entities`` normalizes it internally through the SAME frozen
#      ``scoring.normalize.normalize_text_v1`` every other scorer uses) --
#      never the ``entity_type`` label or a composite. ``entity_type`` is
#      carried alongside as metadata for the per-class ("entity-class")
#      breakdown the plan's own terminology asks for, not baked into the
#      compared string.
#   4. scope: exactly ``data.carriers.entity_scoped_carrier_lock_keys()`` --
#      today, ``earnings21-original`` only (``earnings22-original`` has no
#      ``wer_tags`` layer at all, E0 D1). A row naming any other carrier
#      fails closed.
#
# "Entity token" (for the notes this scorer's docstring is required to state
# precisely): a reference token position that the SAME ``.nlp`` file's own
# ``wer_tags`` column tags with at least one entity ID -- i.e. exactly the
# tokens Earnings21's own annotation already marks as part of a named
# entity/number/date/etc. span (``entity_type`` values observed in the real
# corpus: YEAR, CARDINAL, ORG, PERSON, DATE, MONEY, PERCENT, TIME, WEBSITE,
# ABBREVIATION, CONTRACTION, ALPHANUMERIC, ...). No new taxonomy is invented
# here; the classes are whatever ``entity_type`` values the frozen
# ``wer_tag.json`` sidecar already assigns.
#
# Gold discipline (same as ``score_asr_outputs``): the ``.nlp`` reference
# file and the ``wer_tag.json`` sidecar are read HERE, at scoring time, on
# already-recorded outputs -- never inside a request loop, never by any
# runtime-phase module (this file is the ONLY module allowed to import
# ``data.references``, AST-enforced; ``data.carriers`` is plain layout data,
# not gold content).
# ---------------------------------------------------------------------------

ENTITY_WER_ADAPTER_VERSION = "entity-wer-v1"


def _normalized_span_offsets(raw_tokens: list[str]) -> list[tuple[int, int]]:
    """For each RAW reference token (in order), the ``[start, end)`` half-open
    range of positions it occupies in ``tokens_v1(" ".join(raw_tokens))`` --
    the SAME normalized sequence :func:`score_asr_outputs`/this module's own
    ``align()`` call aligns against. A raw token that normalizes to zero
    tokens (e.g. a stray punctuation-only cell) maps to an EMPTY range; one
    that normalizes to more than one space-separated piece maps to a
    multi-position range.

    This holds because ``normalize_text_v1`` processes text character by
    character and collapses whitespace: normalizing the whole
    space-joined string is equivalent to normalizing each raw token on its
    own and concatenating the resulting pieces in order. (Exercised directly
    by ``tests/unit/test_entity_wer_scorer.py``, not merely assumed.)
    """

    spans: list[tuple[int, int]] = []
    cursor = 0
    for token in raw_tokens:
        count = len(tokens_v1(token))
        spans.append((cursor, cursor + count))
        cursor += count
    return spans


def _mention_fully_hit(
    token_indices: tuple[int, ...],
    spans: list[tuple[int, int]],
    ref_hit_mask: tuple[bool, ...],
) -> bool:
    """An entity mention counts as correctly recognized only if EVERY one of
    its member reference tokens survived ``align()`` as an exact hit at every
    normalized position it maps to -- no partial credit. A mention that
    normalizes to zero positions (all its raw tokens vanished under
    normalization -- not observed in real data, but handled explicitly
    rather than raising) is conservatively NOT counted correct."""

    positions: list[int] = []
    for raw_index in token_indices:
        start, end = spans[raw_index]
        positions.extend(range(start, end))
    if not positions:
        return False
    return all(ref_hit_mask[position] for position in positions)


def _entity_score_summary(score) -> dict[str, object]:
    """Render one :class:`scoring.entity.EntityScore` as a JSON-able summary,
    plus this scorer's own ``entity_wer`` field.

    ``entity_wer := 1.0 - recall`` when ``expected_total > 0`` -- the
    fraction of gold entity mentions this sample/class/corpus did NOT
    reproduce verbatim, the natural "error rate" reading of the plan's own
    "entity-class WER" name. When ``expected_total == 0`` this deliberately
    reports ``0.0`` ("nothing to get wrong"), NOT ``EntityScore.recall``'s own
    ``0.0``-when-empty convention run through ``1 - recall`` -- that would
    read as a MISLEADING 100% error rate for a sample/class with no gold
    entities at all, rather than an undefined-but-harmless case.

    ``precision`` is always ``1.0`` whenever any mention was predicted
    correct (and ``0.0``/undefined only when nothing was, per
    ``EntityScore``'s own convention) by this adapter's construction: a
    mention is only ever added to ``predicted`` as the EXACT SAME string
    already in ``expected`` when every one of its positions was an exact
    ``ref_hit_mask`` hit (see ``_mention_fully_hit``), so ``predicted`` is
    always a subset of ``expected`` and never contains anything spurious.
    This is a genuine scoping limit, not an oversight: ``scoring.wer.align``
    (frozen, E0 D3) exposes only a per-reference-position boolean hit mask,
    never a hypothesis-side backtrace, so this adapter has no way to name
    WHAT incorrect text a hypothesis substituted for a missed entity --
    ``entity_wer`` (recall-based) is therefore the metric of interest here,
    not this scorer's own always-trivial precision."""

    entity_wer = 0.0 if score.expected_total == 0 else 1.0 - score.recall
    return {
        "expected_total": score.expected_total,
        "correct": score.true_positives,
        "precision": score.precision,
        "recall": score.recall,
        "f1": score.f1,
        "entity_wer": entity_wer,
    }


def score_entity_wer_outputs(
    outputs_path: Path, lock: Mapping[str, object], root: Path
) -> dict[str, object]:
    """Entity-class WER scorer (owner decision D-3): registered as
    ``entity-wer``, usable exactly like ``asr-wer`` -- same
    ``scorer(outputs_path, lock, root)`` signature, same outputs.jsonl rows
    (``sample_id``, ``carrier_lock_key``, ``text``) -- both in-run (via
    ``core.scorers.score_bundle``/``SCORERS.resolve("entity-wer")``) and
    OFFLINE/deferred over an already-finalized attempt's persisted outputs
    (``scripts/score_entity_wer.py`` /
    ``speech_aware_evidence_acquisition.analysis.entity_wer_offline``) --
    both call this exact function, so the two modes are bit-identical.

    GOLD DISCIPLINE: the reference ``.nlp`` file and the entity-type sidecar
    are read HERE, at scoring time, over already-recorded outputs -- never at
    runtime, never inside a request loop (same discipline as
    ``score_asr_outputs``; see this module's own docstring for the AST
    contract that enforces it).

    See the module-level comment block just above this function for the
    resolved format decisions (owner-decisions-pending.md item 1) and the
    precise definition of "entity token"/"entity mention" this scorer uses --
    unchanged from what ``data.references.reference_entity_mentions`` already
    defines; no new taxonomy is invented here.

    Fails closed (:class:`ScoringPhaseError`) on: unreadable/empty/malformed
    outputs (identical checks to ``score_asr_outputs``); a row naming a
    carrier outside ``data.carriers.entity_scoped_carrier_lock_keys()``
    (today, exactly ``{"earnings21-original"}``); or any
    ``data.references.ReferenceError`` raised while resolving a sample's
    reference tokens or entity mentions (missing/malformed sidecar, missing
    ``wer_tags`` column, etc.) -- re-raised as ``ScoringPhaseError`` so every
    scorer in this module fails through the one exception type callers
    already handle.
    """

    try:
        text = Path(outputs_path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ScoringPhaseError(f"cannot read outputs {outputs_path}: {error}") from error
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if not lines:
        raise ScoringPhaseError(f"outputs file {outputs_path} is empty")

    scoped_carriers = entity_scoped_carrier_lock_keys()

    per_sample: list[dict[str, object]] = []
    corpus_expected: list[str] = []
    corpus_predicted: list[str] = []
    corpus_by_type_expected: dict[str, list[str]] = {}
    corpus_by_type_predicted: dict[str, list[str]] = {}
    samples_with_entities = 0
    macro_entity_wer_values: list[float] = []

    for number, line in enumerate(lines, start=1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise ScoringPhaseError(f"outputs line {number} malformed: {error}") from error
        carrier_lock_key = row["carrier_lock_key"]
        sample_id = row["sample_id"]
        if carrier_lock_key not in scoped_carriers:
            raise ScoringPhaseError(
                f"entity-wer has no registered entity layer for carrier "
                f"{carrier_lock_key!r} (sample {sample_id!r}); supported carriers: "
                f"{sorted(scoped_carriers)}"
            )
        try:
            raw_ref_tokens = reference_tokens(lock, root, carrier_lock_key, sample_id)
            mentions = reference_entity_mentions(lock, root, carrier_lock_key, sample_id)
        except ReferenceError as error:
            raise ScoringPhaseError(
                f"cannot resolve entity references for sample {sample_id!r} "
                f"(carrier {carrier_lock_key!r}): {error}"
            ) from error

        ref = tokens_v1(" ".join(raw_ref_tokens))
        hyp = tokens_v1(row["text"])
        alignment = align(ref, hyp)
        spans = _normalized_span_offsets(raw_ref_tokens)

        expected_texts: list[str] = []
        predicted_texts: list[str] = []
        by_type_expected: dict[str, list[str]] = {}
        by_type_predicted: dict[str, list[str]] = {}
        for mention in mentions:
            mention_text = " ".join(mention.tokens)
            expected_texts.append(mention_text)
            by_type_expected.setdefault(mention.entity_type, []).append(mention_text)
            if _mention_fully_hit(mention.token_indices, spans, alignment.ref_hit_mask):
                predicted_texts.append(mention_text)
                by_type_predicted.setdefault(mention.entity_type, []).append(mention_text)

        overall_score = score_entities(expected_texts, predicted_texts)
        sample_summary = _entity_score_summary(overall_score)
        sample_summary["sample_id"] = sample_id
        sample_summary["by_entity_type"] = {
            entity_type: _entity_score_summary(
                score_entities(exp_list, by_type_predicted.get(entity_type, []))
            )
            for entity_type, exp_list in sorted(by_type_expected.items())
        }
        per_sample.append(sample_summary)

        corpus_expected.extend(expected_texts)
        corpus_predicted.extend(predicted_texts)
        for entity_type, exp_list in by_type_expected.items():
            corpus_by_type_expected.setdefault(entity_type, []).extend(exp_list)
        for entity_type, pred_list in by_type_predicted.items():
            corpus_by_type_predicted.setdefault(entity_type, []).extend(pred_list)
        if overall_score.expected_total > 0:
            samples_with_entities += 1
            macro_entity_wer_values.append(sample_summary["entity_wer"])

    corpus_score = score_entities(corpus_expected, corpus_predicted)
    aggregate: dict[str, object] = {
        "adapter_version": ENTITY_WER_ADAPTER_VERSION,
        "samples": len(per_sample),
        "samples_with_entities": samples_with_entities,
        "macro_entity_wer": (
            sum(macro_entity_wer_values) / len(macro_entity_wer_values)
            if macro_entity_wer_values
            else 0.0
        ),
    }
    aggregate.update(_entity_score_summary(corpus_score))
    aggregate["by_entity_type"] = {
        entity_type: _entity_score_summary(
            score_entities(exp_list, corpus_by_type_predicted.get(entity_type, []))
        )
        for entity_type, exp_list in sorted(corpus_by_type_expected.items())
    }
    return {"per_sample": per_sample, "aggregate": aggregate}


SCORERS.register("entity-wer", score_entity_wer_outputs)


def _assert_scoring_entry_gate(
    bundle: object, lock: Mapping[str, object], root: Path, repo_root: Path
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

    IMPORTANT 2 (external-threat-model review round 3; widened by owner
    decision D-3 to cover ``entity-wer`` too -- see below): between the
    carrier-scope check and the clean-tree check, when this bundle's
    configured scorers include ``asr-wer`` OR ``entity-wer`` (the scorers
    that read ``data.references.reference_tokens``/
    ``data.references.reference_entity_mentions``, both of which read the
    SAME ``.nlp`` file's bytes), re-verify the reference (``.nlp``)
    bytes about to be read against D1's frozen per-file identity --
    ``contracts.FrozenCoreGate.verify_reference_identity``, the reference-
    layer counterpart to the media-side ``verify_media_identity`` I-4 already
    added. Scoped to exactly ``bundle.split_ids`` (the bundle's own verified
    split, never the whole corpus). Deliberately on a SEPARATE gate instance
    bound to ``repo_root`` (the test-overridable parameter, exactly like the
    clean-tree check just below) rather than the hardcoded ``REPO_ROOT`` the
    E0/D3/scope gate above uses: unlike the D3 SOURCE-CODE freeze (which can
    only ever mean anything against the REAL checkout this process actually
    imported ``scoring/`` from), the D1 reference-IDENTITY receipt is a data
    fact, not a code-identity fact -- pointing it at an isolated synthetic
    ``repo_root``/``docs/receipts`` for test isolation is exactly as sound as
    ``require_clean_study_repo(repo_root)`` already treats its own git-status
    check, and every real caller's ``repo_root`` defaults to the same
    ``REPO_ROOT`` regardless (``score_bundle``'s own default, matching
    ``finalize_bundle``/``run_experiment_bundled``).
    """

    from ..contracts import FrozenCoreGate
    from ..data.references import ReferenceError, reference_file_relpath
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

    scorer_names = bundle.manifest.get("scorers")
    # Every scorer that reads the .nlp reference layer must trigger the D1
    # reference-identity re-verification: asr-wer, entity-wer, and (slice C3b,
    # 2026-09-03) asr-wer-whisper, which reads the same bytes through
    # data.references.reference_tokens under a different normalizer.
    if isinstance(scorer_names, list) and any(
        name in scorer_names for name in REFERENCE_READING_SCORERS
    ):
        split_ids = getattr(bundle, "split_ids", None)
        if not split_ids:
            raise ScoringPhaseError(
                "verified bundle carries no split_ids to scope the reference-identity "
                "check to; refusing to score with an unbounded/unknown sample set"
            )
        try:
            reference_facts = {
                sample_id: reference_file_relpath(lock, carrier_lock_key, sample_id)
                for sample_id in split_ids
            }
        except ReferenceError as error:
            raise ScoringPhaseError(
                f"cannot resolve reference file paths for carrier {carrier_lock_key!r}: "
                f"{error}"
            ) from error
        reference_gate = FrozenCoreGate.for_study_repo(Path(repo_root), Path(root), Path(repo_root))
        reference_gate.verify_reference_identity(carrier_lock_key, reference_facts)

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
    _assert_scoring_entry_gate(bundle, lock, root, repo_root)
    scorer_names = bundle.manifest.get("scorers")
    if not isinstance(scorer_names, list) or not scorer_names:
        raise ScoringPhaseError("run manifest carries no configured scorers to run")
    results: dict[str, object] = {}
    for name in scorer_names:
        scorer_fn = SCORERS.resolve(str(name))
        results[str(name)] = scorer_fn(bundle.outputs_path, lock, root)
    return results


# ---------------------------------------------------------------------------
# SLURP official-evaluator identity-check scorer (consolidation slice C3a):
# runs BOTH the per-sample port (``reproduction.slurp_scoring``) and the
# REAL, unmodified official ``evaluate.py`` subprocess over the same outputs,
# and reports their numeric identity. Same registration pattern as
# ``a2t-toolcall`` above -- the function lives in
# ``reproduction/slurp_official_eval.py`` (deliberately OUTSIDE the E0 D3
# frozen scoring package), imported here (the one scorer-registration site
# ``score_bundle`` resolves names through) with the same uniform
# ``scorer(outputs_path, lock, root)`` signature. Registered under BOTH
# names: ``"slurp-slu"`` is the name ``data.carriers``' own SLURP
# ``TaskLayout.official_scorer_id`` already names (``data/carriers.py``),
# and ``"slurp-slu-official"`` is this slice's own explicit name -- both
# resolve the exact SAME function object, never two independent
# implementations to keep in sync.
# ---------------------------------------------------------------------------

from ..reproduction.slurp_official_eval import score_slurp_outputs_official  # noqa: E402

SCORERS.register("slurp-slu", score_slurp_outputs_official)
SCORERS.register("slurp-slu-official", score_slurp_outputs_official)


# ---------------------------------------------------------------------------
# Whisper-normalizer WER scorer (consolidation slice C3b): the field-standard
# WER convention most published ASR papers use on Earnings-21/22 -- OpenAI
# Whisper's ``EnglishTextNormalizer`` (vendored read-only under
# ``reproduction/whisper_normalizer/``, upstream tag ``v20240930`` -- see
# that package's own ``PROVENANCE.md`` for the pinned per-file SHA-256s and
# license), applied to BOTH reference and hypothesis text before alignment.
# Registered as ``"asr-wer-whisper"``, reported SIDE BY SIDE with
# ``"asr-wer"`` above -- never a replacement for it; the E0 D3 frozen
# ``saea-scoring-v1`` stack (``scoring/normalize.py``) is untouched by this
# addition.
#
# Housing note (deliberate deviation from the ``a2t-toolcall``/``slurp-slu``
# lazy-import-a-whole-function pattern used immediately above): this
# function's whole BODY lives here, in ``core/scorers.py``, rather than
# being imported whole from ``reproduction/asr_wer_whisper.py``. Reason: it
# resolves each sample's reference tokens via
# ``data.references.reference_tokens`` -- the exact same call
# ``score_asr_outputs`` above makes -- and
# ``tests/contract/test_reference_import_isolation.py`` AST-enforces that
# ``data.references`` is imported ONLY by this module (plus
# ``data/references.py`` itself) across the whole ``src/`` tree; exactly the
# same reason ``score_entity_wer_outputs`` above already lives here rather
# than in a ``reproduction/`` module (unlike ``a2t-toolcall``/``slurp-slu``,
# whose gold comes from ``data.audio2tool``/``data.slurp`` instead and so
# never touches ``data.references`` at all). Only the reference-free pieces
# -- the vendored normalizer wrapper and its version constants -- are
# imported from ``reproduction.asr_wer_whisper``, via the SAME
# lazy-import-at-append-time pattern the ``a2t-toolcall``/``slurp-slu``
# blocks use.
#
# RESIDUAL (reported in this slice's own delivery report, not fixed here):
# ``_assert_scoring_entry_gate``'s reference-identity re-verification
# (IMPORTANT 2 in that function's own docstring, above) triggers only when a
# bundle's configured scorers include the literal string ``"asr-wer"`` or
# ``"entity-wer"``. This scorer ALSO reads the same ``.nlp`` reference bytes
# (via the same ``reference_tokens`` call), but is not named in that
# trigger -- a bundle configured with ``"asr-wer-whisper"`` and neither of
# the other two scorers skips the D1 reference-identity re-verification.
# This block does not edit ``_assert_scoring_entry_gate`` (out of scope for
# this slice; that gate's trigger condition needs its own follow-up
# decision to add ``"asr-wer-whisper"``).
# ---------------------------------------------------------------------------

from ..reproduction.asr_wer_whisper import (  # noqa: E402
    WHISPER_NORMALIZER_NAME,
    WHISPER_WER_SCORER_VERSION,
    normalize_whisper_english,
)


def score_asr_outputs_whisper(
    outputs_path: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    repo_root: Path = REPO_ROOT,
) -> dict[str, object]:
    """Whisper-normalized WER scorer: same JSONL reading and reference
    resolution as :func:`score_asr_outputs` above, but BOTH the reference
    text (the sample's raw reference tokens, space-joined -- the same
    reconstruction ``score_asr_outputs`` itself uses) and the hypothesis
    text are normalized with the vendored Whisper ``EnglishTextNormalizer``
    (``reproduction.asr_wer_whisper.normalize_whisper_english``) and then
    tokenized on whitespace (``str.split()``) -- NOT through the frozen
    ``scoring.normalize.tokens_v1`` -- before ``scoring.wer.align``.

    ``repo_root`` is accepted (default ``REPO_ROOT``, the same
    test-overridable-default convention ``score_bundle``/
    ``_assert_scoring_entry_gate`` already use) for signature symmetry with
    this study's other scorers that DO need it (e.g.
    ``reproduction.a2t_scorer.score_audio2tool_outputs``); this scorer's own
    reference resolution only ever needs ``root`` (the controlled DATA
    root), never the study checkout, so ``repo_root`` is currently unused.

    Per-sample dict shape: the same keys as ``score_asr_outputs`` --
    ``sample_id``, ``wer``, ``hits``, ``substitutions``, ``deletions``,
    ``insertions``, ``ref_hit_mask`` -- plus ``normalizer`` (always
    ``WHISPER_NORMALIZER_NAME``). Aggregate reports CORPUS (micro-averaged)
    WER -- ``sum(errors) / sum(reference words)`` across the whole outputs
    file -- unlike ``score_asr_outputs``'s own ``mean_wer`` (a macro average
    of per-sample WER values): a corpus-level number is what the papers this
    scorer exists to compare against report. ``scorer_version`` pins
    ``WHISPER_WER_SCORER_VERSION``.
    """

    try:
        text = Path(outputs_path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ScoringPhaseError(f"cannot read outputs {outputs_path}: {error}") from error
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if not lines:
        raise ScoringPhaseError(f"outputs file {outputs_path} is empty")

    per_sample: list[dict[str, object]] = []
    total_substitutions = total_deletions = total_insertions = total_ref_words = 0
    for number, line in enumerate(lines, start=1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise ScoringPhaseError(f"outputs line {number} malformed: {error}") from error
        raw_ref_tokens = reference_tokens(lock, root, row["carrier_lock_key"], row["sample_id"])
        ref = normalize_whisper_english(" ".join(raw_ref_tokens)).split()
        hyp = normalize_whisper_english(row["text"]).split()
        result = align(ref, hyp)
        total_substitutions += result.substitutions
        total_deletions += result.deletions
        total_insertions += result.insertions
        total_ref_words += result.reference_length
        per_sample.append(
            {
                "sample_id": row["sample_id"],
                "wer": result.wer,
                "hits": result.hits,
                "substitutions": result.substitutions,
                "deletions": result.deletions,
                "insertions": result.insertions,
                "ref_hit_mask": list(result.ref_hit_mask),
                "normalizer": WHISPER_NORMALIZER_NAME,
            }
        )

    total_errors = total_substitutions + total_deletions + total_insertions
    corpus_wer = (total_errors / total_ref_words) if total_ref_words else 0.0
    return {
        "per_sample": per_sample,
        "aggregate": {
            "corpus_wer": corpus_wer,
            "substitutions": total_substitutions,
            "deletions": total_deletions,
            "insertions": total_insertions,
            "reference_words": total_ref_words,
            "samples": len(per_sample),
            "scorer_version": WHISPER_WER_SCORER_VERSION,
            "normalizer": WHISPER_NORMALIZER_NAME,
        },
    }


SCORERS.register("asr-wer-whisper", score_asr_outputs_whisper)
