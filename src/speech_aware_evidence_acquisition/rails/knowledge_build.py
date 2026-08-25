"""KB-BUILD v1: train-scale, distribution-modeled, MODEL-FREE knowledge
construction (work item C1, owner-approved 2026-08-23 knowledge-plane
baseline program; authority
``docs/readiness/2026-08-23-knowledge-plane-baseline-rulings.md`` sections 1
and 5, the Q-K-V rulings in section 1 govern this module's design).

Scope discipline: text facets and metadata ONLY. No embeddings, no model
contacts anywhere in this module -- everything here is pure Python over
already-loaded, gold-legal TRAIN metadata (SLURP ``train.jsonl`` is a
BUILD-time input per this study's split-usage rulings; the frozen
:class:`~.knowledge.KnowledgeSnapshot` this module produces is TRAIN-only by
contract and is independently decontamination-checked against devel/test
identity before it is trusted).

Q-K-V mapping realized here (ruling section 1.3): **K is multi-dimensional**
-- ``content``/``label``/``speaker``/``prior`` facets, each independently
matchable and hierarchically linked where that adds task information (label
facets form a scenario -> action -> intent chain; content facets are
children of their intent facet). **V is consumed, never embedded** -- every
:class:`~.knowledge.ValueBundle` is a plain English payload (exemplar
sentence, slot type=filler pairs, entity-type priors, normalization
exemplars) plus a train-derived ``prior_score``, sample-linked back to the
exact recordings it was built from.

Fatal-flaw repair realized here (ruling section 1.4): the datastore is
selected by :func:`distribution_sample`, a DIMENSION-BASED (proportional
over intent, not per-label-uniform) sampler with two HARD long-tail floors --
every intent keeps at least one utterance and every entity type observed
anywhere in TRAIN keeps at least one filler exemplar -- so a vocabulary
larger than 100 (SLURP train: 91 intents, 55 entity types) never silently
loses knowledge the way per-label-uniform sampling would (the 2026-08-08
unified-agent-abstraction long-tail clause this ruling document restates).

Decontamination (belt and braces): :func:`slurp_split_sample_ids` is an
IDENTITY-ONLY enumerator over SLURP ``devel``/``test`` -- it reads
``slurp_id`` and ``recordings[].file`` alone, never ``scenario``, ``action``,
``entities``, ``tokens`` or ``sentence`` (the SLU gold layer). It is called
exactly ONCE, by :func:`freeze_slurp_split_identity`, to freeze
``docs/receipts/knowledge/slurp-split-identity.json``.
:func:`build_knowledge_snapshot` never re-reads the live devel/test metadata
files itself; it loads ONLY that frozen receipt (plus the FINAL60/DEV-100/
DEV-500/DEV-1000 governance receipts under ``docs/receipts/probe-samples/``,
redundantly -- those ids are already devel ids, so this is a deliberate
belt-and-braces re-check, not a new information source) and refuses fail-
closed if any selected TRAIN sample id intersects that frozen roster.

Provenance format: :class:`~.knowledge.ValueBundle.provenance_refs` follows
``rails.probes.pslu_flight.build_speech_native_knowledge_snapshot``'s own
prefixed-identifier convention (``sample:``/``utterance:``/``speaker:``)
rather than inventing a new scheme, plus one additional
``governed-jsonl:{relpath}#slurp_id={utterance_id}`` ref that names the exact
governed source file (resolved from the lock, never hardcoded) and anchors
on ``slurp_id`` rather than a raw line number -- SLURP's own upstream jsonl
gives no stability guarantee across regenerations for a bare line offset,
while ``slurp_id`` is the stable identity key this whole module already
keys every other index by.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ..core.base import KNOWLEDGE_BUILDERS
from ..data.lock import REPO_ROOT
from ..data.slurp import (
    SLURP_LOCK_KEY,
    _SPLIT_FILES,  # noqa: SLF001 -- reused, not reimplemented; see module docstring
    _entity_filler,  # noqa: SLF001
    _governed_roots,  # noqa: SLF001
    _read_jsonl,  # noqa: SLF001
    _tokens_by_id,  # noqa: SLF001
    _validate_recording_filename,  # noqa: SLF001
    load_slurp_train_material,
)
from .errors import RailsError
from .hashing import content_hash
from .knowledge import (
    KeyFacet,
    KnowledgeSnapshot,
    ValueBundle,
    assert_prior_scores_are_probabilities,
)

KB_BUILD_POLICY_ID = "saea-kb-distmodel-v1"
_ALLOWED_DIMENSIONS = frozenset({"content", "label", "speaker", "prior"})
_DEFAULT_DIMENSIONS: tuple[str, ...] = ("content", "label", "speaker", "prior")

SPLIT_IDENTITY_SCHEMA = "saea-kb-split-identity-v1"
SPLIT_IDENTITY_RECEIPT_RELPATH = "docs/receipts/knowledge/slurp-split-identity.json"
_DEV_LADDER_RECEIPT_DIR_RELPATH = "docs/receipts/probe-samples"
_DEV_LADDER_RECEIPT_NAMES: tuple[str, ...] = (
    "FINAL60.json",
    "DEV-100.json",
    "DEV-500.json",
    "DEV-1000.json",
)
_RULING_AUTHORITY = "docs/readiness/2026-08-23-knowledge-plane-baseline-rulings.md section 5"
_LONG_TAIL_THRESHOLD = 5


# ---------------------------------------------------------------------------
# Task-neutral TRAIN rows
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KbRow:
    """One TRAIN utterance's task-neutral row: everything a distribution-
    modeled, task-independent knowledge builder needs, independent of the
    SLU-specific :class:`~..data.slurp.SlurpTrainMaterial` shape this is
    adapted from."""

    utterance_id: str
    content: str
    scenario: str
    action: str
    intent: str
    entity_types: tuple[str, ...]
    entity_fillers: Mapping[str, tuple[str, ...]]
    sample_ids: tuple[str, ...]
    speaker_by_sample_id: Mapping[str, str]
    media_relpath_by_sample_id: Mapping[str, str]

    @property
    def primary_speaker_id(self) -> str:
        """Deterministic single-speaker attribution for an utterance that may
        carry more than one recording: the speaker of the lexicographically
        smallest ``sample_id`` (never pool/dict-iteration order)."""

        return self.speaker_by_sample_id[min(self.speaker_by_sample_id)]


def _train_entity_fillers(
    lock: Mapping[str, object], root: Path
) -> dict[str, dict[str, tuple[str, ...]]]:
    """Per-utterance entity type -> filler-surface exemplars, read directly
    from ``train.jsonl`` a second time (module docstring):
    ``load_slurp_train_material`` validates and returns TYPES only, never
    filler text. This reuses ``data.slurp``'s own private tokens/entity-span
    join helpers (never reimplemented) so the join is byte-for-byte the same
    one the rest of this codebase already trusts."""

    _audio_relpath, _audio_root, metadata_dir = _governed_roots(lock, root)
    metadata_path = metadata_dir / _SPLIT_FILES["train"]
    fillers_by_utterance: dict[str, dict[str, tuple[str, ...]]] = {}
    for line_no, raw in enumerate(_read_jsonl(metadata_path), start=1):
        context = f"SLURP train.jsonl line {line_no} (KB-BUILD filler pass)"
        slurp_id = raw.get("slurp_id")
        if isinstance(slurp_id, bool) or not isinstance(slurp_id, int):
            raise RailsError(f"{context}: slurp_id must be an int")
        raw_entities = raw.get("entities")
        if not isinstance(raw_entities, list) or not raw_entities:
            continue
        tokens_by_id = _tokens_by_id(raw.get("tokens"), context)
        type_fillers: dict[str, list[str]] = {}
        for entity in raw_entities:
            if not isinstance(entity, Mapping):
                continue
            entity_type = entity.get("type")
            if not isinstance(entity_type, str) or not entity_type:
                continue
            filler = _entity_filler(tokens_by_id, entity.get("span"), context)
            type_fillers.setdefault(entity_type, []).append(filler)
        fillers_by_utterance[str(slurp_id)] = {
            entity_type: tuple(sorted(set(values)))
            for entity_type, values in type_fillers.items()
        }
    return fillers_by_utterance


def governed_train_jsonl_relpath(lock: Mapping[str, object], root: Path) -> str:
    """The governed ``train.jsonl`` path, resolved from the lock (never
    hardcoded) -- used only for descriptive provenance text."""

    audio_root_relpath, _audio_root, _metadata_dir = _governed_roots(lock, root)
    return f"{audio_root_relpath}/metadata/{_SPLIT_FILES['train']}"


def slurp_kb_rows(lock: Mapping[str, object], root: Path) -> tuple[KbRow, ...]:
    """Adapt ``data.slurp.load_slurp_train_material`` into task-neutral KB
    rows (module docstring), sorted by ``utterance_id``."""

    material = load_slurp_train_material(lock, root)
    fillers_by_utterance = _train_entity_fillers(lock, root)
    rows: list[KbRow] = []
    for entry in material:
        sample_ids = tuple(recording.sample_id for recording in entry.recordings)
        speaker_by_sample_id = {
            recording.sample_id: recording.speaker_id for recording in entry.recordings
        }
        media_relpath_by_sample_id = {
            recording.sample_id: recording.media_relpath for recording in entry.recordings
        }
        rows.append(
            KbRow(
                utterance_id=entry.utterance_id,
                content=entry.sentence,
                scenario=entry.scenario,
                action=entry.action,
                intent=f"{entry.scenario}_{entry.action}",
                entity_types=entry.entity_types,
                entity_fillers=fillers_by_utterance.get(entry.utterance_id, {}),
                sample_ids=sample_ids,
                speaker_by_sample_id=speaker_by_sample_id,
                media_relpath_by_sample_id=media_relpath_by_sample_id,
            )
        )
    return tuple(sorted(rows, key=lambda row: row.utterance_id))


# ---------------------------------------------------------------------------
# Model-free build spec
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KnowledgeBuildSpec:
    """Model-free KB-BUILD configuration. ``datastore_size=None`` selects the
    entire TRAIN pool (the 'full' tier)."""

    carrier_lock_key: str
    datastore_size: int | None = None
    seed: int = 20260823
    dimensions: tuple[str, ...] = _DEFAULT_DIMENSIONS

    def validate(self) -> "KnowledgeBuildSpec":
        if not isinstance(self.carrier_lock_key, str) or not self.carrier_lock_key.strip():
            raise RailsError("KnowledgeBuildSpec.carrier_lock_key must be a non-empty string")
        if self.datastore_size is not None and (
            isinstance(self.datastore_size, bool)
            or not isinstance(self.datastore_size, int)
            or self.datastore_size <= 0
        ):
            raise RailsError(
                "KnowledgeBuildSpec.datastore_size must be a positive int or None"
            )
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise RailsError("KnowledgeBuildSpec.seed must be an int")
        if (
            not isinstance(self.dimensions, tuple)
            or not self.dimensions
            or len(set(self.dimensions)) != len(self.dimensions)
            or not set(self.dimensions) <= _ALLOWED_DIMENSIONS
        ):
            raise RailsError(
                "KnowledgeBuildSpec.dimensions must be a non-empty, duplicate-free tuple "
                f"drawn from {sorted(_ALLOWED_DIMENSIONS)}"
            )
        if not ({"content", "label"} & set(self.dimensions)):
            raise RailsError(
                "KnowledgeBuildSpec.dimensions must include 'content' or 'label' so every "
                "value has at least one grounded facet"
            )
        return self


# ---------------------------------------------------------------------------
# Distribution-modeled sampling
# ---------------------------------------------------------------------------


def _shingles(text: str) -> frozenset[str]:
    """Word-bigram shingle fingerprint (unigrams if the text is too short)."""

    tokens = text.lower().split()
    if len(tokens) < 2:
        return frozenset(tokens)
    return frozenset(f"{a} {b}" for a, b in zip(tokens, tokens[1:]))


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _greedy_diverse_pick(
    candidates: Sequence[KbRow],
    count: int,
    already_selected: Sequence[KbRow],
    rng: random.Random,
    *,
    speaker_of: Callable[[KbRow], str],
    speaker_cap: int,
) -> list[KbRow]:
    """Greedy farthest-point content-diversity selection (module docstring):
    the "greedy content-cluster coverage via token-shingle Jaccard medoids"
    step. At each round, picks the remaining candidate whose bigram-shingle
    Jaccard similarity to its CLOSEST already-selected row is lowest -- the
    biggest novelty, a model-free proxy for an uncovered content-cluster
    medoid -- honoring a soft per-speaker cap (bypassed only when every
    remaining candidate is already at the cap, so a pick is never refused
    outright). Ties are broken via ``rng`` over the ``utterance_id``-sorted
    tied set, so the result is pool-order independent and reproducible for a
    fixed seed.
    """

    selected_shingles = [_shingles(row.content) for row in already_selected]
    speaker_counts: Counter[str] = Counter(speaker_of(row) for row in already_selected)
    remaining = sorted(candidates, key=lambda row: row.utterance_id)
    shingle_of = {row.utterance_id: _shingles(row.content) for row in remaining}
    picked: list[KbRow] = []
    while remaining and len(picked) < count:
        capped = {speaker for speaker, n in speaker_counts.items() if n >= speaker_cap}
        eligible = [row for row in remaining if speaker_of(row) not in capped] or remaining
        best_score: float | None = None
        best_rows: list[KbRow] = []
        for row in eligible:
            shingles = shingle_of[row.utterance_id]
            max_sim = max(
                (_jaccard(shingles, other) for other in selected_shingles), default=0.0
            )
            novelty = 1.0 - max_sim
            if best_score is None or novelty > best_score + 1e-12:
                best_score, best_rows = novelty, [row]
            elif abs(novelty - best_score) <= 1e-12:
                best_rows.append(row)
        chosen = (
            sorted(best_rows, key=lambda row: row.utterance_id)[rng.randrange(len(best_rows))]
            if len(best_rows) > 1
            else best_rows[0]
        )
        picked.append(chosen)
        selected_shingles.append(shingle_of[chosen.utterance_id])
        speaker_counts[speaker_of(chosen)] += 1
        remaining = [row for row in remaining if row.utterance_id != chosen.utterance_id]
    return picked


def _hamilton_apportion(capacity_by_key: Mapping[str, int], total: int) -> dict[str, int]:
    """Largest-remainder (Hamilton) apportionment of ``total`` seats across
    ``capacity_by_key``'s keys, weighted by capacity and capped at each key's
    own capacity. Deterministic: fractional-remainder ties are broken by
    ascending key name. Requires ``0 <= total <= sum(capacity_by_key.values())``.
    """

    if isinstance(total, bool) or not isinstance(total, int) or total < 0:
        raise RailsError("_hamilton_apportion: total must be a non-negative int")
    keys = sorted(capacity_by_key)
    total_capacity = sum(capacity_by_key[key] for key in keys)
    if total > total_capacity:
        raise RailsError("_hamilton_apportion: total exceeds total capacity")
    result = {key: 0 for key in keys}
    if total == 0 or total_capacity == 0:
        return result
    raw = {key: total * capacity_by_key[key] / total_capacity for key in keys}
    for key in keys:
        result[key] = min(int(raw[key]), capacity_by_key[key])
    remainder = total - sum(result.values())
    order = sorted(keys, key=lambda key: (-(raw[key] - int(raw[key])), key))
    guard = 0
    while remainder > 0:
        progressed = False
        for key in order:
            if remainder <= 0:
                break
            if result[key] < capacity_by_key[key]:
                result[key] += 1
                remainder -= 1
                progressed = True
        if not progressed:
            raise RailsError("_hamilton_apportion: failed to converge (internal invariant)")
        guard += 1
        if guard > 10_000:
            raise RailsError("_hamilton_apportion: exceeded iteration guard")
    return result


def distribution_sample(
    rows: Sequence[KbRow], size: int | None, seed: int
) -> tuple[KbRow, ...]:
    """Distribution-modeled TRAIN datastore selection (module docstring):
    proportional allocation over INTENT with two hard floors -- every intent
    keeps at least one utterance and every entity type observed anywhere in
    TRAIN keeps at least one exemplar utterance -- then greedy content-
    diversity picks (:func:`_greedy_diverse_pick`) fill the remainder of each
    intent's Hamilton-apportioned quota, honoring a soft per-speaker cap.

    ``size=None`` selects the entire pool (the 'full' tier). When the hard
    floors alone already meet or exceed ``size``, the floor set IS the
    returned (larger) selection: floors are a HARD requirement, ``size`` is a
    best-effort target, never the other way around.

    Deterministic and pool-order independent: every random draw samples from
    a ``utterance_id``-sorted candidate list via ``random.Random`` seeded by
    ``f"{seed}:{stratum}"`` (stratum = intent name, for both the per-intent
    floor draw and the per-intent diversity fill); the entity-type floor draw
    uses the namespaced tag ``f"{seed}:entity:{entity_type}"`` since it is not
    itself a per-stratum draw.
    """

    rows = tuple(rows)
    if not rows:
        raise RailsError("distribution_sample: rows must be non-empty")
    rows_by_id = {row.utterance_id: row for row in rows}
    if len(rows_by_id) != len(rows):
        raise RailsError("distribution_sample: rows must have unique utterance_id values")

    if size is None or size >= len(rows):
        return tuple(sorted(rows, key=lambda row: row.utterance_id))
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        raise RailsError("distribution_sample: size must be a positive int or None")

    rows_by_intent: dict[str, list[KbRow]] = defaultdict(list)
    for row in rows:
        rows_by_intent[row.intent].append(row)

    selected_ids: set[str] = set()

    # Phase 1: every intent keeps >=1 utterance.
    for intent in sorted(rows_by_intent):
        candidates = sorted(rows_by_intent[intent], key=lambda row: row.utterance_id)
        rng = random.Random(f"{seed}:{intent}")
        selected_ids.add(candidates[rng.randrange(len(candidates))].utterance_id)

    # Phase 2: every entity type observed anywhere in TRAIN keeps >=1 exemplar.
    rows_by_entity_type: dict[str, list[KbRow]] = defaultdict(list)
    all_entity_types: set[str] = set()
    for row in rows:
        for entity_type in row.entity_types:
            rows_by_entity_type[entity_type].append(row)
            all_entity_types.add(entity_type)
    covered_types = {
        entity_type
        for utterance_id in selected_ids
        for entity_type in rows_by_id[utterance_id].entity_types
    }
    for entity_type in sorted(all_entity_types - covered_types):
        candidates = sorted(rows_by_entity_type[entity_type], key=lambda row: row.utterance_id)
        unselected = [row for row in candidates if row.utterance_id not in selected_ids]
        pool = unselected or candidates
        rng = random.Random(f"{seed}:entity:{entity_type}")
        selected_ids.add(pool[rng.randrange(len(pool))].utterance_id)

    floor_count = len(selected_ids)
    if size <= floor_count:
        return tuple(
            sorted((rows_by_id[i] for i in selected_ids), key=lambda row: row.utterance_id)
        )

    # Phase 3: Hamilton-apportion the remaining budget over intents by
    # remaining (post-floor) capacity, then fill each intent's extra quota
    # with a diversity-seeking pick.
    remaining_budget = size - floor_count
    floor_by_intent: Counter[str] = Counter(rows_by_id[i].intent for i in selected_ids)
    capacity_by_intent = {
        intent: len(members) - floor_by_intent.get(intent, 0)
        for intent, members in rows_by_intent.items()
    }
    additional_by_intent = _hamilton_apportion(capacity_by_intent, remaining_budget)

    for intent in sorted(rows_by_intent):
        extra = additional_by_intent.get(intent, 0)
        if extra <= 0:
            continue
        already_selected_rows = [
            rows_by_id[i] for i in selected_ids if rows_by_id[i].intent == intent
        ]
        candidate_pool = [
            row for row in rows_by_intent[intent] if row.utterance_id not in selected_ids
        ]
        target_stratum_size = len(already_selected_rows) + extra
        speaker_cap = max(1, math.ceil(0.10 * target_stratum_size))
        rng = random.Random(f"{seed}:{intent}")
        picked = _greedy_diverse_pick(
            candidate_pool,
            extra,
            already_selected_rows,
            rng,
            speaker_of=lambda row: row.primary_speaker_id,
            speaker_cap=speaker_cap,
        )
        for row in picked:
            selected_ids.add(row.utterance_id)

    return tuple(
        sorted((rows_by_id[i] for i in selected_ids), key=lambda row: row.utterance_id)
    )


# ---------------------------------------------------------------------------
# Facet / value emission
# ---------------------------------------------------------------------------


def _build_facets_and_values(
    selected: Sequence[KbRow],
    rows: Sequence[KbRow],
    spec: KnowledgeBuildSpec,
    *,
    governed_train_relpath: str,
) -> tuple[list[KeyFacet], list[ValueBundle]]:
    dims = set(spec.dimensions)

    rows_by_intent_full: dict[str, list[KbRow]] = defaultdict(list)
    rows_by_scenario_full: dict[str, list[KbRow]] = defaultdict(list)
    # The JOINT count -- rows carrying this intent AND this scenario. It
    # exists so the value-side prior can condition on the scenario instead of
    # dividing two independently-keyed global counts; see the prior_score
    # comment below.
    rows_by_intent_in_scenario_full: Counter[tuple[str, str]] = Counter()
    entity_fillers_all: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        rows_by_intent_full[row.intent].append(row)
        rows_by_scenario_full[row.scenario].append(row)
        rows_by_intent_in_scenario_full[(row.scenario, row.intent)] += 1
        for entity_type, fillers in row.entity_fillers.items():
            entity_fillers_all[entity_type].update(fillers)

    selected_by_intent: dict[str, list[KbRow]] = defaultdict(list)
    for row in selected:
        selected_by_intent[row.intent].append(row)

    facets: list[KeyFacet] = []
    content_facet_id: dict[str, str] = {}
    intent_facet_id: dict[str, str] = {}
    speaker_facet_id: dict[str, str] = {}
    prior_facet_id: dict[str, str] = {}
    prior_representation_by_intent: dict[str, str] = {}

    # ---- label dimension: scenario -> action -> intent hierarchy ------
    if "label" in dims:
        for scenario in sorted({row.scenario for row in selected}):
            scenario_rows = [row for row in selected if row.scenario == scenario]
            scenario_source_ids = tuple(
                sorted({sid for row in scenario_rows for sid in row.sample_ids})
            )
            scenario_fid = f"facet:label:scenario:{scenario}"
            facets.append(
                KeyFacet(
                    facet_id=scenario_fid,
                    dimension="label",
                    representation_kind="text",
                    representation=(
                        f"Scenario '{scenario}' ({len(scenario_rows)} TRAIN utterances "
                        "in this snapshot)."
                    ),
                    source_sample_ids=scenario_source_ids,
                ).validate()
            )
            for action in sorted({row.action for row in scenario_rows}):
                action_rows = [row for row in scenario_rows if row.action == action]
                action_source_ids = tuple(
                    sorted({sid for row in action_rows for sid in row.sample_ids})
                )
                action_fid = f"facet:label:action:{scenario}:{action}"
                facets.append(
                    KeyFacet(
                        facet_id=action_fid,
                        dimension="label",
                        representation_kind="text",
                        representation=(
                            f"Action '{action}' under scenario '{scenario}' "
                            f"({len(action_rows)} TRAIN utterances in this snapshot)."
                        ),
                        source_sample_ids=action_source_ids,
                        parent_facet_ids=(scenario_fid,),
                    ).validate()
                )
                for intent in sorted({row.intent for row in action_rows}):
                    intent_rows = [row for row in action_rows if row.intent == intent]
                    intent_source_ids = tuple(
                        sorted({sid for row in intent_rows for sid in row.sample_ids})
                    )
                    intent_fid = f"facet:label:intent:{intent}"
                    facets.append(
                        KeyFacet(
                            facet_id=intent_fid,
                            dimension="label",
                            representation_kind="text",
                            representation=(
                                f"Intent '{intent}' (scenario='{scenario}', "
                                f"action='{action}'); {len(intent_rows)} TRAIN "
                                "utterances in this snapshot."
                            ),
                            source_sample_ids=intent_source_ids,
                            parent_facet_ids=(action_fid,),
                        ).validate()
                    )
                    intent_facet_id[intent] = intent_fid

    # ---- content dimension: one facet per selected utterance ----------
    if "content" in dims:
        for row in selected:
            parent = (intent_facet_id[row.intent],) if row.intent in intent_facet_id else ()
            content_fid = f"facet:content:{row.utterance_id}"
            facets.append(
                KeyFacet(
                    facet_id=content_fid,
                    dimension="content",
                    representation_kind="text",
                    representation=row.content,
                    source_sample_ids=row.sample_ids,
                    parent_facet_ids=parent,
                ).validate()
            )
            content_facet_id[row.utterance_id] = content_fid

    # ---- speaker dimension ---------------------------------------------
    if "speaker" in dims:
        rows_by_speaker: dict[str, list[KbRow]] = defaultdict(list)
        for row in selected:
            rows_by_speaker[row.primary_speaker_id].append(row)
        for speaker_id in sorted(rows_by_speaker):
            speaker_rows = rows_by_speaker[speaker_id]
            source_ids = tuple(sorted({sid for row in speaker_rows for sid in row.sample_ids}))
            scenario_hist = Counter(row.scenario for row in speaker_rows)
            hist_text = ", ".join(
                f"{scenario}={count}"
                for scenario, count in sorted(
                    scenario_hist.items(), key=lambda item: (-item[1], item[0])
                )
            )
            speaker_fid = f"facet:speaker:{speaker_id}"
            facets.append(
                KeyFacet(
                    facet_id=speaker_fid,
                    dimension="speaker",
                    representation_kind="text",
                    representation=(
                        f"Speaker '{speaker_id}': {len(speaker_rows)} TRAIN utterances in "
                        f"this snapshot; scenario histogram: {hist_text}."
                    ),
                    source_sample_ids=source_ids,
                ).validate()
            )
            speaker_facet_id[speaker_id] = speaker_fid

    # ---- prior dimension: p(entity_type | intent) from FULL train -----
    if "prior" in dims:
        for intent in sorted(selected_by_intent):
            intent_rows_full = rows_by_intent_full.get(intent, ())
            total = len(intent_rows_full)
            type_counts: Counter[str] = Counter()
            for row in intent_rows_full:
                type_counts.update(set(row.entity_types))
            if type_counts:
                table_text = "; ".join(
                    f"{etype}={count / total:.4f} ({count}/{total})"
                    for etype, count in sorted(
                        type_counts.items(), key=lambda item: (-item[1], item[0])
                    )
                )
                representation = (
                    f"Entity-type prior for intent '{intent}' from full TRAIN counts "
                    f"(n={total} utterances): {table_text}."
                )
            else:
                representation = (
                    f"Entity-type prior for intent '{intent}' from full TRAIN counts "
                    f"(n={total} utterances): no entity types observed."
                )
            source_ids = tuple(
                sorted({sid for row in selected_by_intent[intent] for sid in row.sample_ids})
            )
            prior_fid = f"facet:prior:{intent}"
            facets.append(
                KeyFacet(
                    facet_id=prior_fid,
                    dimension="prior",
                    representation_kind="text",
                    representation=representation,
                    source_sample_ids=source_ids,
                ).validate()
            )
            prior_facet_id[intent] = prior_fid
            prior_representation_by_intent[intent] = representation

    # ---- values: one ValueBundle per selected utterance ----------------
    values: list[ValueBundle] = []
    for row in selected:
        entity_lines = []
        normalization_lines = []
        for entity_type in sorted(row.entity_fillers):
            fillers = row.entity_fillers[entity_type]
            entity_lines.append(f"{entity_type}={'|'.join(fillers)}")
            variants = sorted(entity_fillers_all.get(entity_type, set()) - set(fillers))[:5]
            if variants:
                normalization_lines.append(
                    f"{entity_type} surface-form variants observed elsewhere in TRAIN: "
                    f"{', '.join(variants)}"
                )
        slot_text = "; ".join(entity_lines) if entity_lines else "no slot entities"
        normalization_text = (
            " ".join(normalization_lines)
            if normalization_lines
            else "no additional surface-form variants observed for this utterance's entity types"
        )
        content_text = (
            f"Exemplar sentence: \"{row.content}\" -> intent {row.intent} "
            f"(scenario={row.scenario}, action={row.action}). "
            f"Slot type=filler pairs: {slot_text}. {normalization_text}."
        )
        if row.intent in prior_representation_by_intent:
            content_text += f" {prior_representation_by_intent[row.intent]}"

        # p(intent | scenario). BOTH counts range over the SAME population --
        # the rows of this one scenario -- because that is what conditioning
        # on the scenario MEANS. Before 2026-08-25 the numerator was
        # ``len(rows_by_intent_full[intent])``, this intent's rows over ALL
        # scenarios, while the local was already NAMED
        # ``intent_total_in_scenario``: the name asserted a restriction the
        # expression did not perform. The sibling Audio2Tool builder wrote the
        # same shape and it broke there (supremum 4.1, 193 values above 1).
        #
        # THIS REPAIR IS AN EXACT IDENTITY ON SLURP, and here is why. ``intent``
        # is built as ``f"{entry.scenario}_{entry.action}"`` (see
        # :func:`slurp_kb_rows`), so a row's intent DETERMINES its scenario:
        # every row with this intent necessarily has this scenario. The
        # restricted row set is therefore the SAME SET as the unrestricted
        # one, not merely the same size, and the numerator is unchanged on
        # every intent. The old expression was right by accident of the label
        # vocabulary, never by construction -- swap in a label scheme that does
        # not nest and it breaks exactly as A2T's did. Measured over the real
        # TRAIN rows in
        # ``docs/readiness/2026-08-25-prior-score-semantics-repair.md``.
        scenario_total = len(rows_by_scenario_full.get(row.scenario, ()))
        intent_total_in_scenario = rows_by_intent_in_scenario_full.get(
            (row.scenario, row.intent), 0
        )
        prior_score = intent_total_in_scenario / scenario_total if scenario_total else 0.0

        associated: list[str] = []
        if row.intent in intent_facet_id:
            associated.append(intent_facet_id[row.intent])
        if row.utterance_id in content_facet_id:
            associated.append(content_facet_id[row.utterance_id])
        if row.primary_speaker_id in speaker_facet_id:
            associated.append(speaker_facet_id[row.primary_speaker_id])
        if row.intent in prior_facet_id:
            associated.append(prior_facet_id[row.intent])
        if not associated:
            raise RailsError(
                f"KB-BUILD value for utterance {row.utterance_id!r} has no associated facet"
            )

        provenance_refs = tuple(
            sorted(
                {
                    *(f"sample:{sid}" for sid in row.sample_ids),
                    f"utterance:{row.utterance_id}",
                    f"speaker:{row.primary_speaker_id}",
                    f"governed-jsonl:{governed_train_relpath}#slurp_id={row.utterance_id}",
                }
            )
        )

        values.append(
            ValueBundle(
                value_id=f"value:{row.utterance_id}",
                content=content_text,
                associated_facet_ids=tuple(sorted(set(associated))),
                source_sample_ids=row.sample_ids,
                provenance_refs=provenance_refs,
                task_target=row.intent,
                prior_score=prior_score,
            ).validate()
        )

    return facets, values


# ---------------------------------------------------------------------------
# Decontamination
# ---------------------------------------------------------------------------


def slurp_split_sample_ids(
    lock: Mapping[str, object], root: Path, split: str
) -> tuple[str, ...]:
    """Identity-only SLURP sample id enumeration for ``split`` (``devel``/
    ``test``). Reads ONLY ``slurp_id`` and ``recordings[].file`` from the
    governed jsonl -- never ``scenario``/``action``/``entities``/``tokens``/
    ``sentence`` (the SLU gold layer). This is the ONE place in this module
    that reads a devel/test metadata file at all, and it is used exactly
    once, by :func:`freeze_slurp_split_identity`, to freeze a decontamination
    receipt; :func:`build_knowledge_snapshot` never calls this function or
    the real devel/test loader itself -- it only compares selected TRAIN
    sample ids against the frozen receipt this function's caller produces.
    """

    if split not in _SPLIT_FILES:
        raise RailsError(f"unknown SLURP split {split!r}")
    _audio_relpath, _audio_root, metadata_dir = _governed_roots(lock, root)
    metadata_path = metadata_dir / _SPLIT_FILES[split]
    if not metadata_path.is_file():
        raise RailsError(f"SLURP split metadata file missing: {metadata_path}")
    ids: list[str] = []
    seen: set[str] = set()
    for line_no, raw in enumerate(_read_jsonl(metadata_path), start=1):
        context = f"SLURP {split}.jsonl line {line_no} (identity-only pass)"
        slurp_id = raw.get("slurp_id")
        if isinstance(slurp_id, bool) or not isinstance(slurp_id, int):
            raise RailsError(f"{context}: slurp_id must be an int")
        recordings = raw.get("recordings")
        if not isinstance(recordings, list) or not recordings:
            raise RailsError(f"{context}: recordings must be a non-empty list")
        for recording in recordings:
            if not isinstance(recording, Mapping):
                raise RailsError(f"{context}: recording entry must be an object")
            filename = _validate_recording_filename(recording.get("file"), context)
            sample_id = f"slurp:{split}:{slurp_id:06d}:{filename[: -len('.flac')]}"
            if sample_id in seen:
                raise RailsError(f"{context}: duplicate recording file {filename!r}")
            seen.add(sample_id)
            ids.append(sample_id)
    if not ids:
        raise RailsError(f"SLURP split {split!r} resolved to zero identity-only sample ids")
    return tuple(sorted(ids))


def freeze_slurp_split_identity(
    lock: Mapping[str, object], root: Path
) -> dict[str, object]:
    """Build the decontamination receipt document (module docstring). Not
    written to disk here -- callers write it via a canonical JSON writer
    (e.g. ``e0.artifacts.write_json_artifact``) exactly once, before any
    KB-BUILD run."""

    splits: dict[str, object] = {}
    for split in ("devel", "test"):
        ids = slurp_split_sample_ids(lock, root, split)
        splits[split] = {
            "count": len(ids),
            "ids": list(ids),
            "identity_hash": hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest(),
        }
    return {
        "schema": SPLIT_IDENTITY_SCHEMA,
        "generator": (
            "speech_aware_evidence_acquisition.rails.knowledge_build."
            "freeze_slurp_split_identity"
        ),
        "authority": _RULING_AUTHORITY,
        "carrier": SLURP_LOCK_KEY,
        "note": (
            "Identity-only enumeration (slurp_id + recordings[].file); scenario, action, "
            "entities, tokens and sentence are never read (see slurp_split_sample_ids "
            "docstring). build_knowledge_snapshot's decontamination check reads ONLY this "
            "frozen receipt -- the live devel/test governed jsonl is read exactly once, "
            "here, to produce it."
        ),
        "splits": splits,
    }


def _load_split_identity_ids(path: Path) -> tuple[str, ...]:
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    ids: list[str] = []
    for split_name in ("devel", "test"):
        block = document["splits"][split_name]
        block_ids = tuple(block["ids"])
        recomputed = hashlib.sha256("\n".join(sorted(block_ids)).encode("utf-8")).hexdigest()
        if recomputed != block["identity_hash"]:
            raise RailsError(
                f"split identity receipt {path} hash mismatch for {split_name!r}"
            )
        ids.extend(block_ids)
    return tuple(ids)


def _load_dev_ladder_ids(path: Path) -> tuple[str, ...]:
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    return tuple(item["id"] for item in document["items"])


def _default_forbidden_sample_ids(repo_root: Path) -> frozenset[str]:
    split_identity_path = Path(repo_root) / SPLIT_IDENTITY_RECEIPT_RELPATH
    if not split_identity_path.is_file():
        raise RailsError(
            f"decontamination receipt missing: {split_identity_path}; run "
            "freeze_slurp_split_identity (once) before any KB-BUILD"
        )
    ids: set[str] = set(_load_split_identity_ids(split_identity_path))
    for name in _DEV_LADDER_RECEIPT_NAMES:
        path = Path(repo_root) / _DEV_LADDER_RECEIPT_DIR_RELPATH / name
        if not path.is_file():
            raise RailsError(f"decontamination receipt missing: {path}")
        ids.update(_load_dev_ladder_ids(path))
    return frozenset(ids)


# ---------------------------------------------------------------------------
# Snapshot build
# ---------------------------------------------------------------------------


def build_knowledge_snapshot(
    spec: KnowledgeBuildSpec,
    *,
    lock: Mapping[str, object] | None = None,
    root: Path | None = None,
    rows: Sequence[KbRow] | None = None,
    forbidden_sample_ids: frozenset[str] | None = None,
    repo_root: Path | None = None,
) -> KnowledgeSnapshot:
    """Build one standalone, model-free TRAIN :class:`KnowledgeSnapshot`
    (module docstring).

    ``rows``, when supplied, bypasses filesystem loading entirely (unit
    tests build a synthetic :class:`KbRow` corpus this way); otherwise
    ``lock``/``root`` are required and :func:`slurp_kb_rows` loads them.
    ``forbidden_sample_ids``, when supplied, bypasses reading the
    decontamination receipts from disk (again, for tests); otherwise they
    are loaded from ``repo_root`` (default the study repo root).
    """

    spec.validate()
    if spec.carrier_lock_key != SLURP_LOCK_KEY:
        raise RailsError(
            f"KB-BUILD v1 is SLURP-only; got carrier_lock_key={spec.carrier_lock_key!r}"
        )

    if rows is None:
        if lock is None or root is None:
            raise RailsError(
                "build_knowledge_snapshot requires lock and root when rows is not supplied"
            )
        rows = slurp_kb_rows(lock, root)
    rows = tuple(rows)
    if not rows:
        raise RailsError("build_knowledge_snapshot: zero TRAIN rows")

    selected = distribution_sample(rows, spec.datastore_size, spec.seed)

    forbidden = (
        forbidden_sample_ids
        if forbidden_sample_ids is not None
        else _default_forbidden_sample_ids(repo_root if repo_root is not None else REPO_ROOT)
    )
    selected_sample_ids = {sid for row in selected for sid in row.sample_ids}
    contaminated = selected_sample_ids & forbidden
    if contaminated:
        preview = sorted(contaminated)[:5]
        raise RailsError(
            "KB-BUILD selection intersects the frozen devel/test/FINAL60/DEV-tier "
            f"decontamination roster: {preview}"
            + (f" (+{len(contaminated) - 5} more)" if len(contaminated) > 5 else "")
        )

    governed_relpath = (
        governed_train_jsonl_relpath(lock, root)
        if lock is not None and root is not None
        else "slurp/metadata/train.jsonl"
    )
    facets, values = _build_facets_and_values(
        selected, rows, spec, governed_train_relpath=governed_relpath
    )
    # The prior-score range contract, construction side (see
    # ``knowledge.assert_prior_scores_are_probabilities``): a builder that
    # emits a non-probability has computed the wrong quantity, so it is
    # refused here, at the earliest point the values exist, rather than
    # later at freeze time.
    assert_prior_scores_are_probabilities(values, builder="KB-BUILD")

    source_sample_ids = tuple(sorted(selected_sample_ids))
    source_split_identity_hash = hashlib.sha256(
        "\n".join(source_sample_ids).encode("utf-8")
    ).hexdigest()
    build_descriptor = {
        "schema": "saea-kb-distmodel-build-v1",
        "carrier_lock_key": spec.carrier_lock_key,
        "datastore_size": spec.datastore_size,
        "seed": spec.seed,
        "dimensions": list(spec.dimensions),
        "source_split_identity_hash": source_split_identity_hash,
        "utterance_count": len(selected),
    }
    build_sha256 = content_hash(build_descriptor)
    return KnowledgeSnapshot(
        snapshot_id=f"slurp-kb-distmodel-{build_sha256[:16]}",
        source_split_identity_hash=source_split_identity_hash,
        source_sample_ids=source_sample_ids,
        builder_policy_id=KB_BUILD_POLICY_ID,
        facets=tuple(facets),
        values=tuple(values),
    ).validate()


KNOWLEDGE_BUILDERS.register(KB_BUILD_POLICY_ID, build_knowledge_snapshot)


# ---------------------------------------------------------------------------
# Coverage report
# ---------------------------------------------------------------------------


def _selected_rows_from_snapshot(
    snapshot: KnowledgeSnapshot, rows: Sequence[KbRow]
) -> tuple[KbRow, ...]:
    rows_by_sample_id = {sid: row for row in rows for sid in row.sample_ids}
    selected_utterance_ids: set[str] = set()
    selected: list[KbRow] = []
    for sample_id in snapshot.source_sample_ids:
        row = rows_by_sample_id.get(sample_id)
        if row is None:
            raise RailsError(
                f"snapshot sample id {sample_id!r} not found in the provided TRAIN rows"
            )
        if row.utterance_id not in selected_utterance_ids:
            selected_utterance_ids.add(row.utterance_id)
            selected.append(row)
    return tuple(sorted(selected, key=lambda row: row.utterance_id))


def coverage_report(snapshot: KnowledgeSnapshot, rows: Sequence[KbRow]) -> dict[str, object]:
    """Coverage/diversity/decontamination-adjacent statistics for a built
    snapshot, measured against the FULL TRAIN population ``rows``."""

    rows = tuple(rows)
    selected = _selected_rows_from_snapshot(snapshot, rows)

    train_intent_counts: Counter[str] = Counter(row.intent for row in rows)
    selected_intent_counts: Counter[str] = Counter(row.intent for row in selected)
    train_scenario_counts: Counter[str] = Counter(row.scenario for row in rows)
    selected_scenario_counts: Counter[str] = Counter(row.scenario for row in selected)
    train_action_counts: Counter[tuple[str, str]] = Counter(
        (row.scenario, row.action) for row in rows
    )
    selected_action_counts: Counter[tuple[str, str]] = Counter(
        (row.scenario, row.action) for row in selected
    )

    train_entity_types: Counter[str] = Counter()
    for row in rows:
        train_entity_types.update(set(row.entity_types))
    selected_entity_types: Counter[str] = Counter()
    for row in selected:
        selected_entity_types.update(set(row.entity_types))

    def _coverage_pct(train_counts: Mapping[object, int], selected_counts: Mapping[object, int]) -> float:
        if not train_counts:
            return 1.0
        covered = sum(1 for key in train_counts if selected_counts.get(key, 0) > 0)
        return covered / len(train_counts)

    long_tail_intents = {
        key for key, count in train_intent_counts.items() if count < _LONG_TAIL_THRESHOLD
    }
    long_tail_intent_covered = {
        key for key in long_tail_intents if selected_intent_counts.get(key, 0) > 0
    }
    long_tail_entity_types = {
        key for key, count in train_entity_types.items() if count < _LONG_TAIL_THRESHOLD
    }
    long_tail_entity_covered = {
        key for key in long_tail_entity_types if selected_entity_types.get(key, 0) > 0
    }

    total_train = sum(train_intent_counts.values())
    total_selected = sum(selected_intent_counts.values())
    kl = 0.0
    for intent, selected_count in selected_intent_counts.items():
        p = selected_count / total_selected
        q = train_intent_counts.get(intent, 0) / total_train
        if q <= 0:
            raise RailsError(f"selected intent {intent!r} absent from TRAIN population")
        if p > 0:
            kl += p * math.log(p / q)

    train_shingles: set[str] = set()
    for row in rows:
        train_shingles |= _shingles(row.content)
    selected_shingles: set[str] = set()
    for row in selected:
        selected_shingles |= _shingles(row.content)
    cluster_coverage_proxy = (
        len(selected_shingles) / len(train_shingles) if train_shingles else 1.0
    )

    speaker_counts: Counter[str] = Counter(row.primary_speaker_id for row in selected)
    total_selected_rows = len(selected)
    top_speakers = [
        {"speaker_id": speaker_id, "count": count}
        for speaker_id, count in sorted(
            speaker_counts.items(), key=lambda item: (-item[1], item[0])
        )[:10]
    ]
    max_speaker_share = (
        max(speaker_counts.values()) / total_selected_rows if total_selected_rows else 0.0
    )

    return {
        "datastore_size_actual": len(selected),
        "intent_coverage": _coverage_pct(train_intent_counts, selected_intent_counts),
        "scenario_coverage": _coverage_pct(train_scenario_counts, selected_scenario_counts),
        "action_coverage": _coverage_pct(train_action_counts, selected_action_counts),
        "entity_type_coverage": _coverage_pct(train_entity_types, selected_entity_types),
        "long_tail_coverage": {
            "intent": {
                "train_long_tail_count": len(long_tail_intents),
                "covered_count": len(long_tail_intent_covered),
                "coverage": (
                    len(long_tail_intent_covered) / len(long_tail_intents)
                    if long_tail_intents
                    else 1.0
                ),
                "threshold": _LONG_TAIL_THRESHOLD,
            },
            "entity_type": {
                "train_long_tail_count": len(long_tail_entity_types),
                "covered_count": len(long_tail_entity_covered),
                "coverage": (
                    len(long_tail_entity_covered) / len(long_tail_entity_types)
                    if long_tail_entity_types
                    else 1.0
                ),
                "threshold": _LONG_TAIL_THRESHOLD,
            },
        },
        "cluster_coverage_proxy": cluster_coverage_proxy,
        "kl_selected_given_train_over_intent": kl,
        "speaker_histogram_summary": {
            "distinct_speakers": len(speaker_counts),
            "max_speaker_share": max_speaker_share,
            "top_speakers": top_speakers,
        },
        "counts": {
            "train_utterances": len(rows),
            "selected_utterances": len(selected),
            "train_intents": len(train_intent_counts),
            "selected_intents": len(selected_intent_counts),
            "train_entity_types": len(train_entity_types),
            "selected_entity_types": len(selected_entity_types),
        },
    }


__all__ = [
    "KB_BUILD_POLICY_ID",
    "SPLIT_IDENTITY_RECEIPT_RELPATH",
    "SPLIT_IDENTITY_SCHEMA",
    "KbRow",
    "KnowledgeBuildSpec",
    "build_knowledge_snapshot",
    "coverage_report",
    "distribution_sample",
    "freeze_slurp_split_identity",
    "governed_train_jsonl_relpath",
    "slurp_kb_rows",
    "slurp_split_sample_ids",
]
