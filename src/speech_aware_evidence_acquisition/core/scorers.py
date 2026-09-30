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


REFERENCE_READING_SCORERS = frozenset(
    {
        "asr-wer",
        "entity-wer",
        "asr-wer-whisper",
        # 2026-09-06 Earnings agentic-metric block (bottom of this module):
        # all three read the same ``.nlp`` bytes through
        # ``data.references.reference_tokens`` (and, for the ConEC mirror,
        # ``reference_entity_mentions``), so all three must trigger the D1
        # reference-identity re-verification in ``_assert_scoring_entry_gate``.
        "conec-entity-wer-official",
        "numeric-value-accuracy-v1",
        "semantic-high-impact-error-rate-v1",
    }
)


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
    from .bundle import RUN_MANIFEST_SCHEMA, BundleError, verify_bundle
    from .bundle.delivery import DELIVERY_MANIFEST_SCHEMA

    manifest_path = _manifest_path_for_outputs(Path(outputs_path))
    try:
        raw = manifest_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ScoringPhaseError(f"cannot read run manifest {manifest_path}: {error}") from error
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ScoringPhaseError(f"run manifest {manifest_path} is not valid JSON: {error}") from error
    if isinstance(document, dict) and document.get("schema") == DELIVERY_MANIFEST_SCHEMA:
        # A derivative has no independent generation cost. Recompute the
        # complete parent/rule/output binding before returning its zero-extra
        # accounting block and explicit shared-parent attribution.
        try:
            document = dict(verify_bundle(manifest_path).manifest)
        except BundleError as error:
            raise ScoringPhaseError(f"derived cost provenance refused: {error}") from error
    elif not isinstance(document, dict) or document.get("schema") != RUN_MANIFEST_SCHEMA:
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

    ``repo_root`` additionally gates a clean-tree check over the LOAD-BEARING
    SURFACE (``core.bundle.git_commit.require_clean_load_bearing_surface`` --
    ``src/``, ``configs/``, ``docs/arms/``, ``scripts/``). The D3 freeze
    covers only ``scoring/*.py``: ``score_asr_outputs`` also imports
    ``data.references.reference_tokens``, which lives OUTSIDE that frozen
    package, so an uncommitted edit there would defeat the freeze check
    alone -- and ``src/`` is inside the load-bearing surface, so that hole is
    closed exactly as before. Unlike the E0/scope check, this DOES take
    ``repo_root`` as an explicit parameter (default ``REPO_ROOT``, matching
    ``run_experiment_bundled``'s own convention) so tests can point it at an
    isolated synthetic repo rather than depending on this checkout's own
    ambient git status.

    IMPORTANT 3 (2026-09-09, the seal/score symmetry repair). This check used
    to be ``core.bundle.require_clean_study_repo``, which refuses ANY dirt.
    That was the launch-time rule, and applying it here contradicted the
    2026-08-16 flight-protection fix on the other half of the same seal: a
    COMPLETED manifest binds its commit through
    ``_study_commit_for_completed_manifest``, which tolerates and RECORDS
    dirt confined outside the load-bearing surface. From that commit onward a
    run could therefore seal COMPLETED over a stray readiness note and then
    be permanently unscoreable and unfinalizable on the same tree -- the
    2026-08-16 incident, moved one step later, and measured as the Audio2Tool
    wire checks' ``seal_and_score = SCORING_FAILED`` on 2026-09-09. Both
    halves now share ONE rule, so whatever seals can be scored. Nothing whose
    bytes can change a score became tolerable: every such file lives under
    ``src/``, ``configs/``, ``docs/arms/`` or ``scripts/`` and still refuses,
    and ``require_clean_study_repo`` itself is untouched and still strict
    where it belongs, at launch, before any budget is spent.

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
    ``require_clean_load_bearing_surface(repo_root)`` already treats its own
    git-status check, and every real caller's ``repo_root`` defaults to the same
    ``REPO_ROOT`` regardless (``score_bundle``'s own default, matching
    ``finalize_bundle``/``run_experiment_bundled``).
    """

    from ..contracts import FrozenCoreGate
    from ..data.references import ReferenceError, reference_file_relpath
    from .bundle.git_commit import require_clean_load_bearing_surface

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

    require_clean_load_bearing_surface(Path(repo_root))


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
    from .bundle import BundleError
    from .bundle.delivery import assert_raw_parent_scoreable, reused_delivery_scores
    from .config import ConfigError

    try:
        assert_raw_parent_scoreable(bundle, repo_root)
    except (BundleError, ConfigError, ValueError, TypeError) as error:
        raise ScoringPhaseError(
            f"delivery scoring refused: {error}; use build-delivery, then score "
            "the derived manifest through score-batch"
        ) from error
    _assert_scoring_entry_gate(bundle, lock, root, repo_root)
    try:
        reused = reused_delivery_scores(bundle)
    except BundleError as error:
        raise ScoringPhaseError(f"score reuse refused: {error}") from error
    if reused is not None:
        return reused
    scorer_names = bundle.manifest.get("scorers")
    if not isinstance(scorer_names, list) or not scorer_names:
        raise ScoringPhaseError("run manifest carries no configured scorers to run")
    from copy import deepcopy

    results: dict[str, object] = {}
    scored_callables: dict[int, object] = {}
    for name in scorer_names:
        scorer_fn = SCORERS.resolve(str(name))
        identity = id(scorer_fn)
        if identity in scored_callables:
            # Aliases retain independent result values without launching the
            # identical official evaluator twice. Distinct partials/configured
            # callable instances intentionally retain distinct invocations.
            results[str(name)] = deepcopy(scored_callables[identity])
        else:
            result = scorer_fn(bundle.outputs_path, lock, root)
            scored_callables[identity] = result
            results[str(name)] = result
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

from ..reproduction.slurp_official_eval import (  # noqa: E402
    score_slurp_outputs_official,
    score_slurp_outputs_official_aligned,
    score_slurp_outputs_official_projected,
    score_slurp_outputs_official_projected_v2,
    score_slurp_outputs_official_projected_v2_train,
    score_slurp_outputs_official_projected_v3,
    score_slurp_outputs_official_projected_v3_train,
    score_slurp_outputs_official_test,
    score_slurp_outputs_official_train,
    score_slurp_outputs_slu_normalized,
    score_slurp_outputs_slu_normalized_train,
)

SCORERS.register("slurp-slu", score_slurp_outputs_official)
SCORERS.register("slurp-slu-official", score_slurp_outputs_official)
# The TEST sibling (one-read protocol section 3.4): the same evaluator at the
# same pinned commit, gold from ``test``. Inert until a sealed final-report
# manifest exists; it refuses any non-test row before the data root is touched.
SCORERS.register("slurp-slu-official-test", score_slurp_outputs_official_test)

# ---------------------------------------------------------------------------
# The same scorer with the LEGAL-LABEL PROJECTION on (owner ruling 2026-09-06:
# a model-usage local optimization, allowed before any mechanism, zero model
# contacts; preregistration
# docs/readiness/2026-09-06-slurp-legal-label-projection-relock-v1-preregistration.md).
#
# A predicted (scenario, action) pair outside the 60 TRAIN intents cannot be
# right -- the gold vocabulary does not contain it -- so it is mapped onto the
# nearest legal pair BEFORE the official evaluate.py sees it. The parse stays
# byte-identical, an unparsed response stays unparsed, and entities are never
# touched, so every entity-side metric is structurally unchanged.
#
# Registered under BOTH names for exactly the reason the unprojected pair is:
# "slurp-slu-projected" mirrors data.carriers' short SLURP spelling and
# "slurp-slu-official-projected" is the explicit one; both resolve the same
# function object, which is itself a keyword binding of
# score_slurp_outputs_official rather than a second implementation. A run
# manifest that declares one of these names scores through core.scoring_batch
# over a complete manifest exactly like any other registered scorer.
# ---------------------------------------------------------------------------

SCORERS.register("slurp-slu-projected", score_slurp_outputs_official_projected)
SCORERS.register("slurp-slu-official-projected", score_slurp_outputs_official_projected)

# ---------------------------------------------------------------------------
# The SUCCESSOR rule slurp-legal-label-projection-v2 (preregistration
# docs/readiness/2026-09-06-slurp-legal-label-projection-v2-preregistration.md).
#
# v1 repairs LEGALITY by spelling, which sends `locations` to `lists` because
# that is what `locations` is spelled like. v2 first asks whether the illegal
# SCENARIO slot holds a legal ACTION name -- the model answering
# recommendation_locations as `locations`/`query` -- and if so promotes it back
# to the scenario that owns it, falling through to v1 unchanged otherwise.
#
# v1 stays registered beside it, deliberately: the two rules are SIBLINGS, not
# a revision chain, so a verdict can pair a cell against either one and v1's
# own 2026-09-06 lock stays readable from its own scorer id whatever v2's read
# decides. All four projected ids are keyword bindings of the same
# score_slurp_outputs_official, never independent implementations.
# ---------------------------------------------------------------------------

SCORERS.register("slurp-slu-projected-v2", score_slurp_outputs_official_projected_v2)
SCORERS.register(
    "slurp-slu-official-projected-v2", score_slurp_outputs_official_projected_v2
)

# ---------------------------------------------------------------------------
# The v3 SUCCESSOR: module M3 (SLURP v2 base program, ``docs/superpowers/
# specs/2026-09-16-slurp-v2-base-program-design.md`` section 3), decided by
# the A1 USE-projection audit (``docs/results/
# 2026-09-17-slurp-a1-use-projection-audit-v1.md``).
#
# v3 is TWO halves applied together, never one alone: the label half (rule
# ``R_action`` then the registered v2 fallback,
# ``rails.slurp_projection_v3.project_slu_label_v3``) and the filler half
# (surface normalisation P2, all four rungs, no support filter). v1 and v2
# stay registered beside it for exactly the reason v1 stayed beside v2: the
# three rules are SIBLINGS, not a revision chain, and a verdict can pair a
# cell against any one of them. All ids below are keyword bindings of the
# same ``score_slurp_outputs_official``, never independent implementations.
# ---------------------------------------------------------------------------

SCORERS.register("slurp-slu-projected-v3", score_slurp_outputs_official_projected_v3)
SCORERS.register(
    "slurp-slu-official-projected-v3", score_slurp_outputs_official_projected_v3
)

# ---------------------------------------------------------------------------
# The SAME official scorer against TRAIN gold, for the construction-role
# rosters every EVO cell rewards on.
#
# The default binding resolves gold from ``devel`` and refuses a TRAIN
# prediction outright -- correctly, because a devel read must never silently
# score against another split's gold. But an EVO fold IS train: its rows are
# construction-role discovery utterances drawn from ``train.jsonl``, and
# scoring them needs the same official ``evaluate.py`` at the same pinned
# commit pointed at the split those rows came from. Declaring it as its own
# registered id is what makes a run manifest state WHICH gold it was scored
# against, instead of a keyword hidden in a call site.
#
# Both are keyword bindings of ``score_slurp_outputs_official``, never
# independent implementations, exactly like the four projected ids above.
# ---------------------------------------------------------------------------

SCORERS.register("slurp-slu-train", score_slurp_outputs_official_train)
SCORERS.register("slurp-slu-official-train", score_slurp_outputs_official_train)
SCORERS.register(
    "slurp-slu-official-projected-v2-train",
    score_slurp_outputs_official_projected_v2_train,
)
SCORERS.register(
    "slurp-slu-official-projected-v3-train",
    score_slurp_outputs_official_projected_v3_train,
)


# ---------------------------------------------------------------------------
# The NORMALIZED SLU scorer (MF-10, readiness note
# docs/readiness/2026-09-08-mf10-slot-vocabulary-cards-and-normalized-slu-v1.md):
# the Whisper-normalizer analogue for slot VALUES.
#
# It is registered here for exactly the reason ``asr-wer-whisper`` is
# registered beside ``asr-wer`` one block below, and with exactly the same
# standing: an ADDITIONAL, field-convention number reported SIDE BY SIDE with
# the primary, never a replacement for it. The paper-facing SLURP number stays
# the official ``evaluate.py`` one -- and this scorer proves that on every
# call, because it RUNS the official subprocess on the raw inputs first,
# reports its numbers unchanged, refuses to compute anything if the port
# disagrees with them, and only then adds a ``normalized`` block computed with
# ``reproduction.slurp_slot_normalizer`` applied SYMMETRICALLY to the gold and
# the predicted filler.
#
# Symmetry is what makes it a metric rather than a mechanism: an arm cannot
# gain under it by writing its answers differently from the corpus, only by
# saying the same thing the corpus says. The one rung with a corpus dependency
# (the leading-token strip) is learned from TRAIN fillers alone.
#
# Not in ``REFERENCE_READING_SCORERS``: like every ``slurp-slu*`` id, its gold
# comes from ``data.slurp``, never from ``data.references``.
# ---------------------------------------------------------------------------

SCORERS.register("slurp-slu-f1-normalized-v1", score_slurp_outputs_slu_normalized)

# The SAME symmetric scorer against TRAIN gold -- owner decision 14 of
# 2026-09-17 (``docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md``).
#
# Decision 7 requires the symmetric-normalised number BESIDE every official
# number. The DEV binding above resolves gold from ``devel`` and refuses a
# TRAIN prediction outright, so on the SLURP v2 base program's TRAIN A roster
# that number was simply not evaluable -- cells B0r and B4b record the refusal
# in their own verdicts. This id is the same function pointed at the split the
# construction fold's rows came from, registered exactly as
# ``slurp-slu-official-train`` is registered beside ``slurp-slu-official``:
# a keyword binding of the SAME implementation, never a second one, so the
# gold a number was computed against is named by the scorer id in the manifest
# instead of hidden in a call site.
SCORERS.register(
    "slurp-slu-f1-normalized-v1-train", score_slurp_outputs_slu_normalized_train
)

# One registered callable owns the aligned projected-v2 primary and raw-label
# normalized secondary. Keeping both views inside this result lets
# ``score_bundle`` invoke the official evaluator once for a complete manifest.
SCORERS.register("slurp-slu-official-aligned-v1", score_slurp_outputs_official_aligned)


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


# ---------------------------------------------------------------------------
# Audio2Tool tool-call scorer, v2 (slice C3c): the slice-S1 zero-contact
# re-scoring study's adopted V2e semantics
# (docs/readiness/2026-09-03-a2t-scorer-v2-zero-contact-study.md), registered
# alongside ``a2t-toolcall`` above -- v1 stays UNCHANGED and registered; v2 is
# reported side by side, never a replacement. Same registration pattern:
# the function lives in ``reproduction/a2t_scorer.py`` (deliberately OUTSIDE
# the E0 D3 frozen scoring package), imported here with the SAME uniform
# ``scorer(outputs_path, lock, root)`` signature. Gold enters scorer-side
# only, via ``data.audio2tool.load_expected_calls``/``load_tool_registry`` --
# never through ``data.references``.
# ---------------------------------------------------------------------------

from ..reproduction.a2t_scorer import score_audio2tool_outputs_v2  # noqa: E402

SCORERS.register("a2t-toolcall-v2", score_audio2tool_outputs_v2)


# ---------------------------------------------------------------------------
# Audio2Tool tool-call scorer, OFFICIAL (2026-09-04): the pinned Audio2Tool
# release's own metric code (github.com/audio2tool/Audio2Tool, MIT, commit
# b9d5383ca30945fbafb965a04bea40117e1e8a82) applied to this repository's
# sealed outputs -- the paper-facing scorer the owner's standard-scoring rule
# requires for this carrier, now that the benchmark's evaluation code is
# published. ``a2t-toolcall`` (v1) and ``a2t-toolcall-v2`` above are
# UNCHANGED and stay registered; the official number is reported beside them,
# never as a silent replacement. Same registration pattern and the same
# uniform ``scorer(outputs_path, lock, root)`` signature; gold enters
# scorer-side only, via ``data.audio2tool.load_official_gold`` (the release's
# own QuerySample shape) -- never through ``data.references``.
# ---------------------------------------------------------------------------

from ..reproduction.a2t_scorer import score_audio2tool_outputs_official  # noqa: E402

SCORERS.register("a2t-toolcall-official", score_audio2tool_outputs_official)


# ---------------------------------------------------------------------------
# ESB Earnings-22 utterance scorers (2026-09-04): the utterance-scoped twins of
# ``asr-wer-whisper`` and ``asr-wer`` above, for the ONE same-model published
# target this study can align against -- Qwen3-Omni-30B-A3B-Instruct's 9.79
# zero-shot WER on the 2,735-utterance ESB "Earnings22" test subset.
#
# Why they are separate registrations rather than the existing two scorers:
# an ESB utterance is not a carrier sample. ``data.references.reference_tokens``
# resolves exactly one ``.nlp`` file per CALL id under the locked carrier tree,
# and ``contracts.FrozenCoreGate.verify_reference_identity`` fails closed for
# any id D1 does not record in that carrier's ``nlp_references`` manifest -- an
# utterance is neither, and manufacturing 2,735 ``.nlp`` files inside a locked
# dataset tree D1 hashed is not an option. So the utterance references travel
# their own hash-pinned rail, exactly as ``a2t-toolcall``/``slurp-slu`` already
# reach their gold through ``data.audio2tool``/``data.slurp`` instead of
# ``data.references``. That identity guarantee is NOT skipped: it is supplied
# fail-closed inside ``reproduction.esb_reference.load_esb_references``, which
# re-hashes the derived reference layer against its committed receipt before a
# single reference word is read. See that module's own docstring.
#
# Same registration pattern and the same uniform ``scorer(outputs_path, lock,
# root)`` signature as every other scorer here; the bodies live in
# ``reproduction/esb_reference.py`` (outside the E0 D3 frozen scoring package,
# and importing ``data.references`` nowhere) and use the SAME frozen
# ``scoring.wer.align``, the SAME ``scoring.normalize.tokens_v1`` and the SAME
# vendored Whisper normalizer the two carrier-layer scorers use, so the two
# Earnings numbers stay comparable metric for metric.
# ---------------------------------------------------------------------------

from ..reproduction.esb_reference import (  # noqa: E402
    score_esb_outputs,
    score_esb_outputs_whisper,
)

SCORERS.register("asr-wer-esb", score_esb_outputs)
SCORERS.register("asr-wer-esb-whisper", score_esb_outputs_whisper)


# ---------------------------------------------------------------------------
# Earnings agentic-metric block (2026-09-06, owner ruling "WER is not a
# reasonable speech-agentic task"): corpus WER stays the alignment anchor
# against the published Earnings-21 rows, and the paper-facing line for
# Earnings MECHANISM cells becomes entity-level metrics with published numbers
# plus a semantic high-impact error rate. Three scorers register in this
# block, beside -- never instead of -- ``asr-wer-whisper`` / ``asr-wer`` /
# ``entity-wer``, one metric per commit:
#
#   ``conec-entity-wer-official``          ConEC Table 2's per-entity-type WER
#   ``numeric-value-accuracy-v1``          did the figures survive at all
#   ``semantic-high-impact-error-rate-v1`` HIGH-impact reference-word mass
#
# All three live HERE rather than in ``reproduction/`` for the same reason
# ``score_asr_outputs_whisper`` and ``score_entity_wer_outputs`` already do:
# they resolve gold through ``data.references``, and
# ``tests/contract/test_reference_import_isolation.py`` AST-enforces that this
# module is that package's only importer. Their reference-free definitions --
# the alignment trace, the fstalign accounting, the numeric-value contract, the
# taxonomy interface -- live in ``reproduction.conec_entity_scoring``,
# ``reproduction.numeric_value_accuracy`` and ``reproduction.semantic_impact``,
# imported at append time exactly as the blocks above import theirs.
#
# NAMING, stated plainly because the suffix carries a promise elsewhere in this
# module: ``a2t-toolcall-official`` runs the Audio2Tool release's own vendored
# Python metric code and ``slurp-slu-official`` subprocesses SLURP's real
# ``evaluate.py``. ``conec-entity-wer-official`` CANNOT do that -- ConEC's
# metric tool is fstalign, a C++/OpenFST binary this repository does not
# install and has never run -- so it is a DEFINITION MIRROR of fstalign's own
# ``RecordTagWer`` accounting, read out of that project's source at a pinned
# commit. That is not left to a docstring: every aggregate this scorer emits
# carries ``official_tool_run: false`` and the pinned ``definition_source``,
# so no table can quote it as an executed official metric by accident.
# ---------------------------------------------------------------------------

from ..reproduction import conec_entity_scoring as _conec  # noqa: E402
from ..reproduction import numeric_value_accuracy as _numeric  # noqa: E402
from ..reproduction import semantic_impact as _semantic  # noqa: E402


CONEC_ALIGNMENT_SCHEMA = "saea-conec-alignment-v1"


def _conec_alignment_payload(
    reference_words: list[str],
    hypothesis_words: list[str],
    operations: list[tuple[str, int | None, int | None]],
    reference_owners: list[tuple[str, ...] | None],
    entity_types: Mapping[str, str],
) -> dict[str, object]:
    """Encode the scorer's complete normalized alignment without changing it."""

    return {
        "schema": CONEC_ALIGNMENT_SCHEMA,
        "reference_words": list(reference_words),
        "hypothesis_words": list(hypothesis_words),
        "operations": [list(operation) for operation in operations],
        "reference_owners": [
            None if owners is None else list(owners) for owners in reference_owners
        ],
        "entity_types": dict(sorted(entity_types.items())),
    }


def _outputs_rows(outputs_path: Path) -> list[dict[str, object]]:
    """The shared JSONL read every scorer in this module performs, with the
    identical malformed/empty refusals ``score_asr_outputs`` makes."""

    try:
        text = Path(outputs_path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ScoringPhaseError(f"cannot read outputs {outputs_path}: {error}") from error
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if not lines:
        raise ScoringPhaseError(f"outputs file {outputs_path} is empty")
    rows: list[dict[str, object]] = []
    for number, line in enumerate(lines, start=1):
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as error:
            raise ScoringPhaseError(f"outputs line {number} malformed: {error}") from error
    return rows


def score_conec_entity_wer_outputs(
    outputs_path: Path, lock: Mapping[str, object], root: Path
) -> dict[str, object]:
    """ConEC per-entity-type WER (definition mirror; see
    ``reproduction.conec_entity_scoring`` for the paper quote, the pinned
    fstalign source, and the two named differences from that tool).

    Per sample: the raw ``.nlp`` reference tokens are Whisper-normalized once
    as a whole string -- byte-identically to ``asr-wer-whisper`` -- and aligned
    against the Whisper-normalized hypothesis, so this scorer's ``__ALL__``
    bucket reproduces that scorer's own per-call and corpus WER exactly and
    acts as its own identity anchor. ``wer_tags`` entity IDs are carried onto
    that normalized sequence from a run-chunked normalization, and each
    reference word's errors are charged to every entity ID it carries, then
    pooled by the sidecar's ``entity_type`` -- fstalign's ``RecordTagWer``
    rule, insertions unattributed.

    Scope is ``data.carriers.entity_scoped_carrier_lock_keys()`` (today
    ``earnings21-original`` alone), same as ``entity-wer``; any other carrier
    fails closed.
    """

    rows = _outputs_rows(outputs_path)
    scoped_carriers = entity_scoped_carrier_lock_keys()
    per_sample: list[dict[str, object]] = []
    bucket_rows: list[dict[str, dict[str, object]]] = []
    for row in rows:
        carrier_lock_key = row["carrier_lock_key"]
        sample_id = row["sample_id"]
        if carrier_lock_key not in scoped_carriers:
            raise ScoringPhaseError(
                f"conec-entity-wer-official has no registered entity layer for carrier "
                f"{carrier_lock_key!r} (sample {sample_id!r}); supported carriers: "
                f"{sorted(scoped_carriers)}"
            )
        try:
            raw_tokens = reference_tokens(lock, root, carrier_lock_key, sample_id)
            mentions = reference_entity_mentions(lock, root, carrier_lock_key, sample_id)
        except ReferenceError as error:
            raise ScoringPhaseError(
                f"cannot resolve entity references for sample {sample_id!r} "
                f"(carrier {carrier_lock_key!r}): {error}"
            ) from error

        owners_by_index: list[list[str]] = [[] for _ in raw_tokens]
        entity_types: dict[str, str] = {}
        for mention in mentions:
            entity_types[mention.entity_id] = mention.entity_type
            for index in mention.token_indices:
                owners_by_index[index].append(mention.entity_id)
        owners = [tuple(sorted(ids)) for ids in owners_by_index]

        whole_words = _conec.whole_string_whisper_words(raw_tokens)
        chunked_words, chunked_owners = _conec.run_chunked_whisper_words(raw_tokens, owners)
        transferred = _conec.transfer_owners(chunked_words, chunked_owners, whole_words)
        hypothesis_words = _conec.hypothesis_whisper_words(str(row["text"]))
        operations = _conec.aligned_operations(whole_words, hypothesis_words)
        _conec.operation_counts(operations, len(whole_words), len(hypothesis_words))
        buckets = _conec.entity_wer_buckets(operations, transferred, entity_types)
        bucket_rows.append(buckets)
        per_sample.append(
            {
                "sample_id": sample_id,
                "wer": buckets[_conec.OVERALL_BUCKET]["wer"],
                "reference_words": buckets[_conec.OVERALL_BUCKET]["reference_words"],
                "unlabelled_reference_words": (
                    buckets[_conec.UNLABELLED_BUCKET]["reference_words"]
                ),
                "by_entity_type": buckets,
                "alignment": _conec_alignment_payload(
                    whole_words,
                    hypothesis_words,
                    operations,
                    transferred,
                    entity_types,
                ),
            }
        )

    merged = _conec.merge_buckets(bucket_rows)
    aggregate: dict[str, object] = {
        "samples": len(per_sample),
        "by_entity_type": merged,
        "corpus_wer": merged[_conec.OVERALL_BUCKET]["wer"],
        "reference_words": merged[_conec.OVERALL_BUCKET]["reference_words"],
        "unlabelled_reference_words": merged[_conec.UNLABELLED_BUCKET]["reference_words"],
    }
    aggregate.update(_conec.scorer_provenance())
    return {"per_sample": per_sample, "aggregate": aggregate}


SCORERS.register("conec-entity-wer-official", score_conec_entity_wer_outputs)

def score_numeric_value_accuracy_outputs(
    outputs_path: Path, lock: Mapping[str, object], root: Path
) -> dict[str, object]:
    """``numeric-value-accuracy-v1``: the share of the reference's numeric
    values (numbers, currencies, percentages and the digit-bearing parts of
    dates, all after the Whisper normalizer) that the hypothesis reproduces
    exactly, bag-matched per call and pooled over the corpus.

    Needs only a reference layer -- no entity annotation -- so it is scoped to
    any carrier ``data.references`` can resolve, unlike the two entity scorers.
    See ``reproduction.numeric_value_accuracy`` for the definition.
    """

    rows = _outputs_rows(outputs_path)
    per_sample: list[dict[str, object]] = []
    for row in rows:
        carrier_lock_key = row["carrier_lock_key"]
        sample_id = row["sample_id"]
        try:
            raw_tokens = reference_tokens(lock, root, carrier_lock_key, sample_id)
        except ReferenceError as error:
            raise ScoringPhaseError(
                f"cannot resolve references for sample {sample_id!r} "
                f"(carrier {carrier_lock_key!r}): {error}"
            ) from error
        counts = _numeric.numeric_value_counts(
            _numeric.reference_whisper_words(raw_tokens),
            _numeric.whisper_words(str(row["text"])),
        )
        counts["sample_id"] = sample_id
        per_sample.append(counts)
    return {
        "per_sample": per_sample,
        "aggregate": _numeric.merge_numeric_counts(per_sample),
    }


SCORERS.register("numeric-value-accuracy-v1", score_numeric_value_accuracy_outputs)

def score_semantic_high_impact_outputs(
    outputs_path: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    repo_root: Path = REPO_ROOT,
) -> dict[str, object]:
    """``semantic-high-impact-error-rate-v1``: HIGH-impact reference-word mass
    over reference words, under the Earnings-22 semantic scan's taxonomy.

    The taxonomy is the scan's deliverable, not this scorer's invention, so
    this registration is a HOOK: it resolves
    ``reproduction.semantic_impact.ACTIVE_TAXONOMY_RELPATH`` inside the study
    checkout and fails closed, naming the scan, until that file lands. The
    metric itself is implemented and tested against a synthetic taxonomy
    (``tests/unit/test_semantic_high_impact.py``); only its Earnings-21 VALUE
    waits.
    """

    taxonomy_path = Path(repo_root) / _semantic.ACTIVE_TAXONOMY_RELPATH
    if not taxonomy_path.is_file():
        raise ScoringPhaseError(
            f"semantic-high-impact-error-rate-v1 needs an impact taxonomy at "
            f"{taxonomy_path}; none exists yet. The taxonomy is the deliverable of the "
            "Earnings-22 semantic scan (branch wt/e22); this scorer refuses to invent "
            "impact levels of its own. See reproduction/semantic_impact.py for the file "
            "contract the scan must satisfy."
        )
    try:
        taxonomy = _semantic.load_taxonomy(taxonomy_path)
    except _semantic.TaxonomyError as error:
        raise ScoringPhaseError(str(error)) from error

    rows = _outputs_rows(outputs_path)
    per_sample: list[dict[str, object]] = []
    for row in rows:
        carrier_lock_key = row["carrier_lock_key"]
        sample_id = row["sample_id"]
        try:
            raw_tokens = reference_tokens(lock, root, carrier_lock_key, sample_id)
        except ReferenceError as error:
            raise ScoringPhaseError(
                f"cannot resolve references for sample {sample_id!r} "
                f"(carrier {carrier_lock_key!r}): {error}"
            ) from error
        reference_words = _conec.whole_string_whisper_words(raw_tokens)
        hypothesis_words = _conec.hypothesis_whisper_words(str(row["text"]))
        operations = _conec.aligned_operations(reference_words, hypothesis_words)
        _conec.operation_counts(operations, len(reference_words), len(hypothesis_words))
        counts = _semantic.semantic_impact_counts(
            operations, reference_words, hypothesis_words, taxonomy
        )
        counts["sample_id"] = sample_id
        per_sample.append(counts)
    return {
        "per_sample": per_sample,
        "aggregate": _semantic.merge_semantic_counts(per_sample, taxonomy),
    }


SCORERS.register("semantic-high-impact-error-rate-v1", score_semantic_high_impact_outputs)


# ---------------------------------------------------------------------------
# Earnings-22 brief-term recall (2026-09-07, KC-E2 / KU-E2c): how much of what
# the pre-meeting brief NAMES the transcript actually keeps. Registered here
# because a knowledge cell needs a metric its knowledge could plausibly move --
# five metadata facts cannot shift 26,251 reference words of corpus WER, and a
# cell that only reported WER would measure runtime noise. Definition, the
# homograph dilution it does NOT correct for, and why it needs no entity
# annotation: ``reproduction.brief_term_recall``'s own module docstring.
#
# Same uniform ``scorer(outputs_path, lock, root)`` signature as every other
# registration above; references come from the SAME hash-pinned ESB layer
# ``asr-wer-esb-whisper`` reads and the terms from the carrier's own metadata
# table, resolved through the SAME ``core.evidence.e22_metadata_file_relpath``
# the evidence source resolves it with.
# ---------------------------------------------------------------------------

from ..reproduction.brief_term_recall import (  # noqa: E402
    score_brief_term_recall_outputs,
)

SCORERS.register("brief-term-recall-v1", score_brief_term_recall_outputs)
