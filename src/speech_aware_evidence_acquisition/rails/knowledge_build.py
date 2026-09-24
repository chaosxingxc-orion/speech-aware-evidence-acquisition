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
larger than 100 (SLURP train, MEASURED: 60 intents plus 55 entity types =
115 label entries) never silently loses knowledge the way per-label-uniform
sampling would (the 2026-08-08 unified-agent-abstraction long-tail clause
this ruling document restates). Both floors are applied UNCONDITIONALLY --
neither is gated on the vocabulary size -- so the clause is satisfied under
any reading of its threshold.

This parenthetical read "91 intents" until 2026-08-25, and that number was
wrong for the quantity this sentence is about. 91 is the count of distinct
``intent`` FIELD STRINGS in ``train.jsonl``, and 31 of those 91 are
prefix-stripped ALIASES of an intent already counted: SLURP writes the bare
action ("query") instead of "scenario_action" on 162 of its 11,514 train
rows, so 40 of the 60 (scenario, action) pairs carry two spellings of one
intent. The vocabulary this sampler actually strata on is the synthesized
``f"{scenario}_{action}"`` key that every label facet, prior facet and
``task_target`` uses, and that vocabulary is 60; devel adds none of its own
(59 of the 60, no new ones). Measured over the governed bytes in
``docs/readiness/2026-08-25-slurp-intent-coverage-check.md``.

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
from .knowledge_build_common import (
    distribution_sample,
    greedy_diverse_pick,
    hamilton_apportion,
    jaccard,
    shingles,
)

KB_BUILD_POLICY_ID = "saea-kb-distmodel-v1"
_ALLOWED_DIMENSIONS = frozenset({"content", "label", "speaker", "prior"})
_DEFAULT_DIMENSIONS: tuple[str, ...] = ("content", "label", "speaker", "prior")

#: The default rendering of a content facet and of every value: the exemplar
#: view every committed snapshot carries. A content facet's representation is
#: the TRAIN utterance verbatim and a value is the exemplar sentence, its
#: intent, its slot type=filler pairs, TRAIN's other surface forms for those
#: types and (when the ``prior`` dimension is built) the intent's entity-type
#: prior.
VIEW_EXEMPLAR = "exemplar"

#: The SLOT-FILLER view (2026-09-07, cell KU-S3). Same selection, same facet
#: ids, same value ids, same ``prior_score``s, same provenance -- only the two
#: rendered strings change:
#:
#: * a content facet's representation becomes a DESCRIPTOR that quotes the
#:   utterance instead of BEING it, exactly as the ``label``/``speaker``/
#:   ``prior`` dimensions already do;
#: * a value's content becomes that utterance's slot ``type=filler`` pairs
#:   alone -- no exemplar sentence, no intent name, no surface-form variants,
#:   no entity-type prior.
#:
#: Both changes are forced by what a SUPPLIED content dimension does to a
#: SLURP phase cell, and both were measured before they were written.
#:
#: The representation. ``rails.runner._assert_agent_control_excludes_knowledge_
#: payloads`` protects every facet representation and every value content of
#: the BOUND snapshot by raw substring, at an eight-character floor. The
#: exemplar view's content facets are 11,514 raw TRAIN utterances and SLURP
#: has one- and two-word ones, so ``next episode``, ``next podcast`` and
#: ``how much`` are protected payloads and the per-intent slot schema KC-S1b
#: sends contains all three: measured 2026-09-07, the exemplar view refuses
#: **1,000 of 1,000** KU-S3 instructions, while its VALUES collide with
#: **0 of 1,000** -- the values are paragraphs and can never be substrings of
#: an instruction. KC-S1a/b dodged this by dropping the ``content`` dimension
#: (``scripts/build_knowledge_snapshot.py``, 2026-09-05); a cell that RECALLS
#: on content facets cannot, which is the ruling KC-S1b's deviation 1 asked
#: for. Quoting the utterance inside a descriptor keeps the leakage rule at
#: full strength over everything a control turn could actually paste -- every
#: value, and the utterance itself the moment anyone tries to send it with its
#: own key text -- and removes only substring hits on ordinary English.
#:
#: The value. Neighbour retrieval on SLURP INTENT is CLOSED (the 2026-09-06
#: MF-7b audit), and this view is the one that keeps a supplied cell inside
#: what MF-7b handed on: filler recall. An exemplar value names the
#: neighbour's own intent and re-states the entity-type prior the phase's
#: schema block already carries, so it would supply a closed mechanism and
#: duplicate an admitted one. The filler view supplies fillers.
VIEW_SLOT_FILLERS = "slot-fillers"

#: The ANNOTATED-EXEMPLAR view (2026-09-17, SLURP v2 base program item E3 /
#: cell B1). Same selection, same facet ids, same value ids, same
#: ``prior_score``s, same provenance as :data:`VIEW_EXEMPLAR` -- only the two
#: rendered strings change, exactly the discipline :data:`VIEW_SLOT_FILLERS`
#: already established:
#:
#: * a content facet's representation gets the same quoted-descriptor
#:   treatment as :data:`VIEW_SLOT_FILLERS` (module docstring reasoning
#:   applies unchanged: the descriptor is the protected payload, never a bare
#:   English phrase);
#: * a value's content becomes one line: the utterance, its
#:   ``scenario_action`` label, and its slot ``type=filler`` pairs, each on
#:   its own semicolon-separated entry (``type=filler; type=filler ...``, or
#:   ``none`` when the utterance carries no entity).
#:
#: The Solver-phase exemplar supply (``docs/results/
#: 2026-09-17-slurp-a2-exemplar-headroom-audit-v1.md``) needs the exemplar
#: sentence AND its scenario/action AND its fillers together -- unlike
#: :data:`VIEW_SLOT_FILLERS`, whose filler-only rendering was forced by
#: SLURP intent retrieval being closed (that view's own docstring). This
#: view is deliberately NOT that constraint: M1 supplies exemplars to the
#: SOLVER phase, which already sees the full candidate contract, so a
#: neighbour's own label is additional convention-transfer signal rather than
#: a duplicate of a closed mechanism.
VIEW_ANNOTATED_EXEMPLARS = "annotated-exemplars"

#: The SLURP Solver's own EMPTY form for the entity list, transcribed from
#: its output contract ``configs/probes/slurp_native_role_solver_v2.txt``:
#: the Solver returns
#: ``{"scenario":"...","action":"...","entities":[{"type":"...","filler":"..."}]}``
#: and that template's own closing sentence is "If no entity is expressed,
#: return an empty entities array" -- so the exact bytes a CORRECT empty
#: answer carries are ``"entities":[]``. This constant exists so the
#: rendering below cannot drift from the contract it is supposed to
#: demonstrate; ``tests/unit/test_knowledge_build_empty_contract_view.py``
#: reads that template and pins the two together.
SOLVER_EMPTY_ENTITY_LIST_FORM = '"entities":[]'

#: The EMPTY-CONTRACT annotated-exemplar view (2026-09-24). A ONE-FACTOR
#: derivation of :data:`VIEW_ANNOTATED_EXEMPLARS`: same selection, same facet
#: ids, same facet REPRESENTATIONS (byte for byte -- the descriptor still
#: says ``annotated-exemplar retrieval key``, so the retrieval key side is
#: untouched and the sealed KU-S3 facet vectors keep binding by id), same
#: value ids, same ``prior_score``s, same ``task_target``s, same provenance.
#: Exactly one string changes, on exactly the utterances that carry no
#: entity annotation: the raw line's third field renders
#: :data:`SOLVER_EMPTY_ENTITY_LIST_FORM` instead of the bare word ``none``.
#:
#: Why. The 2026-09-24 bad-case bank (``docs/results/
#: 2026-09-24-slurp-plan-bad-case-bank.md``) measures an ENTITY-FP-ONLY mass
#: of 12.1 % / 10.8 % of rows carrying +4.76 / +3.47 pp of pooled official
#: SLU headroom, on rosters where 38.3 % / 31.4 % of rows carry no gold
#: entity at all. The released pool already CONTAINS entity-free exemplars
#: (2,949 of 9,354; that note's 'zero entity-free values' is a parser
#: artefact of counting the literal token ``none`` as an entity type named
#: "none"), so the supply is not missing the CASE -- what it never shows is
#: the correct empty ANSWER. ``none`` is an English word that appears in no
#: legal Solver response. Module M1's admitted gain was convention transfer
#: from the raw line, and this view extends exactly that mechanism to the
#: empty case: an exemplar whose answer is empty now shows the bytes the
#: Solver would itself have to emit.
#:
#: NOT a value-content superset of the parent store, and that is stated
#: rather than hidden: the entity-bearing values are byte identical, the
#: entity-free values differ in their third field alone. Every facet, id,
#: prior score and provenance ref is identical on every selected utterance.
VIEW_ANNOTATED_EXEMPLARS_EMPTY_CONTRACT = "annotated-exemplars-empty-contract"

_ALLOWED_VIEWS: tuple[str, ...] = (
    VIEW_EXEMPLAR,
    VIEW_SLOT_FILLERS,
    VIEW_ANNOTATED_EXEMPLARS,
    VIEW_ANNOTATED_EXEMPLARS_EMPTY_CONTRACT,
)
_CONTENT_RECALL_VIEWS: tuple[str, ...] = (
    VIEW_SLOT_FILLERS,
    VIEW_ANNOTATED_EXEMPLARS,
    VIEW_ANNOTATED_EXEMPLARS_EMPTY_CONTRACT,
)
#: The annotated-exemplar views, whose rendered lines differ ONLY in the
#: field an entity-free utterance puts last.
_ANNOTATED_EXEMPLAR_VIEWS: tuple[str, ...] = (
    VIEW_ANNOTATED_EXEMPLARS,
    VIEW_ANNOTATED_EXEMPLARS_EMPTY_CONTRACT,
)
#: That field, per view.
_ANNOTATED_EXEMPLAR_EMPTY_FORM: dict[str, str] = {
    VIEW_ANNOTATED_EXEMPLARS: "none",
    VIEW_ANNOTATED_EXEMPLARS_EMPTY_CONTRACT: SOLVER_EMPTY_ENTITY_LIST_FORM,
}

# Value-only representations preserve the established retrieval-key view.
# A label-only projection removes information; the intent frame adds a TRAIN
# relation. ``typed-fillers`` reorganizes filler content without loss, while
# ``span-role-frame`` retains the governed token and annotation structure.
VALUE_FORMATS = (
    "historical",
    "typed-fillers",
    "slot-type-set",
    "intent-slot-frame",
    "span-role-frame",
    "intent-role-coverage",
)

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
class KbSourceToken:
    """One governed TRAIN token in source order."""

    token_id: int
    surface: str


@dataclass(frozen=True)
class KbEntityMention:
    """One governed TRAIN entity annotation, retaining occurrence multiplicity."""

    entity_type: str
    token_ids: tuple[int, ...]
    filler: str


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
    source_tokens: tuple[KbSourceToken, ...] = ()
    entity_mentions: tuple[KbEntityMention, ...] = ()

    @property
    def primary_speaker_id(self) -> str:
        """Deterministic single-speaker attribution for an utterance that may
        carry more than one recording: the speaker of the lexicographically
        smallest ``sample_id`` (never pool/dict-iteration order)."""

        return self.speaker_by_sample_id[min(self.speaker_by_sample_id)]


def _train_entity_annotations(
    lock: Mapping[str, object], root: Path
) -> tuple[
    dict[str, dict[str, tuple[str, ...]]],
    dict[str, tuple[KbSourceToken, ...]],
    dict[str, tuple[KbEntityMention, ...]],
]:
    """Read governed TRAIN tokens and mentions once.

    Historical filler maps keep their grouped, sorted, deduplicated behavior.
    The additive mention view separately retains source order, exact token
    surfaces, and every annotation occurrence.
    """

    _audio_relpath, _audio_root, metadata_dir = _governed_roots(lock, root)
    metadata_path = metadata_dir / _SPLIT_FILES["train"]
    fillers_by_utterance: dict[str, dict[str, tuple[str, ...]]] = {}
    tokens_by_utterance: dict[str, tuple[KbSourceToken, ...]] = {}
    mentions_by_utterance: dict[str, tuple[KbEntityMention, ...]] = {}
    for line_no, raw in enumerate(_read_jsonl(metadata_path), start=1):
        context = f"SLURP train.jsonl line {line_no} (KB-BUILD annotation pass)"
        slurp_id = raw.get("slurp_id")
        if isinstance(slurp_id, bool) or not isinstance(slurp_id, int):
            raise RailsError(f"{context}: slurp_id must be an int")
        utterance_id = str(slurp_id)
        raw_tokens = raw.get("tokens")
        tokens_by_id = _tokens_by_id(raw_tokens, context)
        if not isinstance(raw_tokens, list):
            raise RailsError(f"{context}: tokens must be a list")
        source_tokens: list[KbSourceToken] = []
        seen_token_ids: set[int] = set()
        for raw_token in raw_tokens:
            if not isinstance(raw_token, Mapping):
                raise RailsError(f"{context}: token entry must be an object")
            token_id = raw_token.get("id")
            surface = raw_token.get("surface")
            if (
                isinstance(token_id, bool)
                or not isinstance(token_id, int)
                or not isinstance(surface, str)
            ):
                raise RailsError(f"{context}: token entry malformed")
            if token_id in seen_token_ids:
                raise RailsError(f"{context}: token IDs must be unique")
            seen_token_ids.add(token_id)
            source_tokens.append(KbSourceToken(token_id, surface))
        tokens_by_utterance[utterance_id] = tuple(source_tokens)

        raw_entities = raw.get("entities")
        if not isinstance(raw_entities, list):
            raise RailsError(f"{context}: entities must be a list")
        type_fillers: dict[str, list[str]] = {}
        mentions: list[KbEntityMention] = []
        for entity_index, entity in enumerate(raw_entities):
            if not isinstance(entity, Mapping):
                raise RailsError(
                    f"{context}: entity {entity_index} must be an object"
                )
            entity_type = entity.get("type")
            if not isinstance(entity_type, str) or not entity_type:
                raise RailsError(
                    f"{context}: entity {entity_index} type must be non-empty"
                )
            raw_span = entity.get("span")
            normalized_filler = _entity_filler(tokens_by_id, raw_span, context)
            if not isinstance(raw_span, list):
                raise RailsError(f"{context}: entity span must be a list")
            token_ids = tuple(raw_span)
            if len(token_ids) != len(set(token_ids)):
                raise RailsError(
                    f"{context}: entity {entity_index} token IDs must be unique"
                )
            exact_filler = " ".join(tokens_by_id[token_id] for token_id in token_ids)
            type_fillers.setdefault(entity_type, []).append(normalized_filler)
            mentions.append(KbEntityMention(entity_type, token_ids, exact_filler))
        fillers_by_utterance[utterance_id] = {
            entity_type: tuple(sorted(set(values)))
            for entity_type, values in type_fillers.items()
        }
        mentions_by_utterance[utterance_id] = tuple(mentions)
    return fillers_by_utterance, tokens_by_utterance, mentions_by_utterance


def governed_train_jsonl_relpath(lock: Mapping[str, object], root: Path) -> str:
    """The governed ``train.jsonl`` path, resolved from the lock (never
    hardcoded) -- used only for descriptive provenance text."""

    audio_root_relpath, _audio_root, _metadata_dir = _governed_roots(lock, root)
    return f"{audio_root_relpath}/metadata/{_SPLIT_FILES['train']}"


def slurp_kb_rows(lock: Mapping[str, object], root: Path) -> tuple[KbRow, ...]:
    """Adapt ``data.slurp.load_slurp_train_material`` into task-neutral KB
    rows (module docstring), sorted by ``utterance_id``."""

    material = load_slurp_train_material(lock, root)
    (
        fillers_by_utterance,
        tokens_by_utterance,
        mentions_by_utterance,
    ) = _train_entity_annotations(lock, root)
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
                source_tokens=tokens_by_utterance[entry.utterance_id],
                entity_mentions=mentions_by_utterance[entry.utterance_id],
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
    view: str = VIEW_EXEMPLAR
    value_format: str = "historical"

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
        if self.view not in _ALLOWED_VIEWS:
            raise RailsError(
                f"KnowledgeBuildSpec.view must be one of {list(_ALLOWED_VIEWS)}, got "
                f"{self.view!r}"
            )
        if self.value_format not in VALUE_FORMATS:
            raise RailsError(f"KnowledgeBuildSpec.value_format must be one of {VALUE_FORMATS}")
        if self.value_format != "historical" and self.view != VIEW_SLOT_FILLERS:
            raise RailsError("nonhistorical value_format requires the slot-fillers key view")
        if self.view in _CONTENT_RECALL_VIEWS and "content" not in set(self.dimensions):
            raise RailsError(
                f"KnowledgeBuildSpec.view={self.view!r} exists to be RECALLED on "
                "per-utterance content facets, so it requires the 'content' dimension"
            )
        return self


# ---------------------------------------------------------------------------
# Distribution-modeled sampling
# ---------------------------------------------------------------------------


def _shingles(text: str) -> frozenset[str]:
    """Alias kept for backward compatibility; moved to
    :func:`.knowledge_build_common.shingles` (C4b consolidation)."""

    return shingles(text)


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    """Alias kept for backward compatibility; moved to
    :func:`.knowledge_build_common.jaccard` (C4b consolidation)."""

    return jaccard(a, b)


def _greedy_diverse_pick(
    candidates: Sequence[KbRow],
    count: int,
    already_selected: Sequence[KbRow],
    rng: random.Random,
    *,
    speaker_of: Callable[[KbRow], str],
    speaker_cap: int,
) -> list[KbRow]:
    """Alias kept for backward compatibility, same call signature as before
    C4b consolidation: delegates to the shared, row-shape-generalized
    :func:`.knowledge_build_common.greedy_diverse_pick` with SLURP's own
    ``content``/``utterance_id`` accessors plugged in."""

    return greedy_diverse_pick(
        candidates,
        count,
        already_selected,
        rng,
        text_of=lambda row: row.content,
        id_of=lambda row: row.utterance_id,
        group_of=speaker_of,
        group_cap=speaker_cap,
    )


def _hamilton_apportion(capacity_by_key: Mapping[str, int], total: int) -> dict[str, int]:
    """Alias kept for backward compatibility; moved to
    :func:`.knowledge_build_common.hamilton_apportion` (C4b consolidation)."""

    return hamilton_apportion(capacity_by_key, total)


# ``distribution_sample`` itself moved to ``.knowledge_build_common`` verbatim
# (C4b consolidation) and is imported above; re-exported here unchanged so
# every existing importer (this module's own ``__all__``,
# ``analysis.slurp_intent_coverage_check``, this module's own test suite)
# keeps resolving ``rails.knowledge_build.distribution_sample`` to the exact
# same function object.


# ---------------------------------------------------------------------------
# Facet / value emission
# ---------------------------------------------------------------------------


def _content_facet_representation(row: KbRow, view: str) -> str:
    """The content facet's key text under ``view``.

    :data:`VIEW_EXEMPLAR` is the utterance verbatim, which is what every
    committed snapshot carries and what the MF-7b key vectors embedded.
    :data:`VIEW_SLOT_FILLERS` QUOTES it inside a descriptor instead, so the
    key still says exactly which TRAIN utterance it is (and still shows the
    utterance whenever a cell sets ``expose_facets``) while the protected
    payload the leakage rule tests is the descriptor and not a bare English
    phrase. See :data:`VIEW_SLOT_FILLERS` for the measurement that forced it.
    """

    if view == VIEW_SLOT_FILLERS:
        return (
            f"TRAIN utterance {row.utterance_id} (slot-filler retrieval key): "
            f"\"{row.content}\""
        )
    if view in _ANNOTATED_EXEMPLAR_VIEWS:
        # Byte-identical across BOTH annotated-exemplar views on purpose: the
        # empty-contract derivation moves the VALUE side only, so the key side
        # -- and every cell that recalls on it -- stays untouched.
        return (
            f"TRAIN utterance {row.utterance_id} (annotated-exemplar retrieval key): "
            f"\"{row.content}\""
        )
    return row.content


def _annotated_exemplar_value_content(row: KbRow, *, empty_form: str = "none") -> str:
    """A value's payload under :data:`VIEW_ANNOTATED_EXEMPLARS`: one line of
    ``<utterance> | <scenario>_<action> | <type>=<filler>; type=filler ...``.

    One ``type=filler`` entry per observed filler occurrence (a type with two
    fillers in one utterance renders two entries), lower-case as annotated;
    ``empty_form`` when the utterance carries no entity annotation at all. See
    :data:`VIEW_ANNOTATED_EXEMPLARS` for why the exemplar sentence, its label
    and its fillers travel together here, unlike the filler-only
    :data:`VIEW_SLOT_FILLERS` rendering.

    ``empty_form`` defaults to ``"none"``, which is what every snapshot built
    before 2026-09-24 carries and what the locked SLURP v2.0 plan's pinned
    store hash covers -- the default keeps those bytes frozen.
    :data:`VIEW_ANNOTATED_EXEMPLARS_EMPTY_CONTRACT` passes
    :data:`SOLVER_EMPTY_ENTITY_LIST_FORM` instead, and nothing else moves.
    """

    pairs = [
        f"{entity_type}={filler}"
        for entity_type in sorted(row.entity_fillers)
        for filler in row.entity_fillers[entity_type]
    ]
    body = "; ".join(pairs) if pairs else empty_form
    return f"{row.content} | {row.scenario}_{row.action} | {body}"


def _slot_filler_value_content(row: KbRow) -> str:
    """A value's payload under :data:`VIEW_SLOT_FILLERS`: this utterance's
    slot ``type=filler`` pairs and nothing else.

    No exemplar sentence, no intent name, no surface-form variants and no
    entity-type prior -- see :data:`VIEW_SLOT_FILLERS` for why each of those
    is deliberately absent. A TRAIN utterance carrying no entity still gets a
    value, because every selected utterance must have one and a neighbour
    that happens to carry no filler is a real property of the retrieval, not
    something to hide.
    """

    pairs = "; ".join(
        f"{entity_type}={'|'.join(row.entity_fillers[entity_type])}"
        for entity_type in sorted(row.entity_fillers)
    )
    body = pairs if pairs else "none recorded"
    return (
        f"Slot type=filler pairs observed in TRAIN utterance {row.utterance_id}: {body}."
    )

SPAN_ROLE_FRAME_SCHEMA = "saea-slurp-span-role-frame-v1"


def _span_role_frame_value_content(row: KbRow) -> str:
    """Render source tokens and mention roles without adding intent labels.

    A delexicalized template is included only when every span is contiguous
    in source order and no two mention occurrences overlap. Ambiguous spans
    remain fully represented in ordered_mentions while the optional template
    is null.
    """

    if not isinstance(row.source_tokens, tuple) or not row.source_tokens:
        raise RailsError("span-role-frame source_tokens must be a non-empty tuple")
    if not isinstance(row.entity_mentions, tuple):
        raise RailsError("span-role-frame entity_mentions must be a tuple")

    token_ids: list[int] = []
    token_surfaces: dict[int, str] = {}
    positions: dict[int, int] = {}
    sentence_tokens: list[dict[str, object]] = []
    for position, token in enumerate(row.source_tokens):
        if not isinstance(token, KbSourceToken):
            raise RailsError(
                "span-role-frame source tokens must be KbSourceToken values"
            )
        if isinstance(token.token_id, bool) or not isinstance(token.token_id, int):
            raise RailsError("span-role-frame token ID must be an int")
        if not isinstance(token.surface, str):
            raise RailsError("span-role-frame token surface must be a string")
        if token.token_id in token_surfaces:
            raise RailsError("span-role-frame token IDs must be unique")
        token_ids.append(token.token_id)
        token_surfaces[token.token_id] = token.surface
        positions[token.token_id] = position
        sentence_tokens.append({"id": token.token_id, "surface": token.surface})

    ordered_mentions: list[dict[str, object]] = []
    span_positions: list[tuple[int, ...]] = []
    template_is_unambiguous = True
    occupied_positions: set[int] = set()
    for mention_index, mention in enumerate(row.entity_mentions):
        if not isinstance(mention, KbEntityMention):
            raise RailsError(
                "span-role-frame mentions must be KbEntityMention values"
            )
        if not isinstance(mention.entity_type, str) or not mention.entity_type:
            raise RailsError(
                f"span-role-frame mention {mention_index} type must be non-empty"
            )
        if not isinstance(mention.token_ids, tuple) or not mention.token_ids:
            raise RailsError(
                f"span-role-frame mention {mention_index} requires non-empty token IDs"
            )
        if any(
            isinstance(token_id, bool) or not isinstance(token_id, int)
            for token_id in mention.token_ids
        ):
            raise RailsError(
                f"span-role-frame mention {mention_index} token IDs must be ints"
            )
        if len(set(mention.token_ids)) != len(mention.token_ids):
            raise RailsError(
                f"span-role-frame mention {mention_index} token IDs must be unique"
            )
        unknown = [
            token_id
            for token_id in mention.token_ids
            if token_id not in token_surfaces
        ]
        if unknown:
            raise RailsError(
                f"span-role-frame mention {mention_index} references unknown token ID "
                f"{unknown[0]}"
            )
        expected_filler = " ".join(
            token_surfaces[token_id] for token_id in mention.token_ids
        )
        if mention.filler != expected_filler:
            raise RailsError(
                f"span-role-frame mention {mention_index} filler disagrees with "
                "its source token span"
            )
        mention_positions = tuple(
            positions[token_id] for token_id in mention.token_ids
        )
        contiguous = mention_positions == tuple(
            range(
                mention_positions[0],
                mention_positions[0] + len(mention_positions),
            )
        )
        if not contiguous or occupied_positions.intersection(mention_positions):
            template_is_unambiguous = False
        occupied_positions.update(mention_positions)
        span_positions.append(mention_positions)
        ordered_mentions.append(
            {
                "type": mention.entity_type,
                "token_ids": list(mention.token_ids),
                "filler": mention.filler,
            }
        )

    template: str | None = None
    if template_is_unambiguous:
        starts = {
            positions_tuple[0]: (positions_tuple, mention.entity_type)
            for positions_tuple, mention in zip(
                span_positions,
                row.entity_mentions,
                strict=True,
            )
        }
        template_parts: list[str] = []
        position = 0
        while position < len(token_ids):
            start = starts.get(position)
            if start is None:
                template_parts.append(row.source_tokens[position].surface)
                position += 1
            else:
                positions_tuple, entity_type = start
                template_parts.append(f"{{{entity_type}}}")
                position += len(positions_tuple)
        template = " ".join(template_parts)

    document = {
        "schema": SPAN_ROLE_FRAME_SCHEMA,
        "sentence_tokens": sentence_tokens,
        "ordered_mentions": ordered_mentions,
        "delexicalized_typed_template": template,
    }
    return json.dumps(
        document,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )

def _selected_intent_role_coverage(
    selected_by_intent: Mapping[str, Sequence[KbRow]],
    *,
    governed_train_relpath: str,
) -> dict[str, tuple[dict[str, object], str]]:
    """Aggregate observed annotations over selected, uniquely identified TRAIN utterances.

    Bind each aggregate to its complete membership without replacing the local
    exemplar association. Empty annotations do not establish entity absence.
    """
    coverage_by_intent: dict[str, tuple[dict[str, object], str]] = {}
    for intent, intent_rows in selected_by_intent.items():
        role_counts: Counter[str] = Counter()
        without_annotations = 0
        for row in intent_rows:
            if row.intent != f"{row.scenario}_{row.action}":
                raise RailsError("intent-role-coverage requires canonical scenario_action intent")
            observed_roles = {role for role, fillers in row.entity_fillers.items() if fillers}
            role_counts.update(observed_roles)
            without_annotations += not observed_roles
        membership_hash = hashlib.sha256(
            "\n".join(sorted(row.utterance_id for row in intent_rows)).encode("utf-8")
        ).hexdigest()
        coverage_by_intent[intent] = (
            {
                "support_unit": "selected TRAIN utterance",
                "utterance_count": len(intent_rows),
                "utterances_without_entity_annotations": without_annotations,
                "observed_utterance_counts_by_role": dict(sorted(role_counts.items())),
                "interpretation": (
                    "Observed roles are not required or exhaustive slots. "
                    "Current speech determines entity presence and values."
                ),
            },
            f"governed-jsonl:{governed_train_relpath}#slurp_ids_sha256={membership_hash}",
        )
    return coverage_by_intent


def _processed_value_content(
    row: KbRow,
    value_format: str,
    *,
    intent_role_coverage: Mapping[str, object] | None = None,
) -> str:
    """Render admitted TRAIN facts, without inferring current-query labels.

    Keep filler spelling, numbers, negation and modifier content unchanged.
    Empty observed slots say nothing about whether an intent requires slots.
    Keys and all source/value identities are constructed independently.
    """
    examples = {kind: list(row.entity_fillers[kind]) for kind in sorted(row.entity_fillers)}
    if value_format == "typed-fillers":
        document = {"observed_slot_examples": examples}
    elif value_format == "slot-type-set":
        document = {"observed_slot_types": sorted(row.entity_fillers)}
    elif value_format in {"intent-slot-frame", "intent-role-coverage"}:
        document = {"observed_intent": row.intent, "observed_slot_examples": examples}
        if value_format == "intent-role-coverage":
            if intent_role_coverage is None:
                raise RailsError("intent-role-coverage requires selected TRAIN coverage")
            document["intent_role_coverage"] = dict(intent_role_coverage)
    elif value_format == "span-role-frame":
        return _span_role_frame_value_content(row)
    else:
        raise RailsError(f"unknown processed value_format {value_format!r}")
    return json.dumps(document, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


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

    role_coverage = (
        _selected_intent_role_coverage(
            selected_by_intent, governed_train_relpath=governed_train_relpath,
        )
        if spec.value_format == "intent-role-coverage"
        else {}
    )

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
                    representation=_content_facet_representation(row, spec.view),
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
        if spec.value_format != "historical":
            content_text = _processed_value_content(
                row, spec.value_format,
                intent_role_coverage=role_coverage[row.intent][0] if role_coverage else None,
            )
        elif spec.view == VIEW_SLOT_FILLERS:
            content_text = _slot_filler_value_content(row)
        elif spec.view in _ANNOTATED_EXEMPLAR_VIEWS:
            content_text = _annotated_exemplar_value_content(
                row, empty_form=_ANNOTATED_EXEMPLAR_EMPTY_FORM[spec.view]
            )
        else:
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
                    *([role_coverage[row.intent][1]] if role_coverage else []),
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
    if spec.view != VIEW_EXEMPLAR:
        # Appended only for a non-default view, so every snapshot built before
        # 2026-09-07 keeps its build hash, its snapshot id and its bytes.
        build_descriptor["view"] = spec.view
    if spec.value_format != "historical":
        build_descriptor["value_format"] = spec.value_format
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
    "VIEW_EXEMPLAR",
    "VIEW_SLOT_FILLERS",
    "VIEW_ANNOTATED_EXEMPLARS",
    "VIEW_ANNOTATED_EXEMPLARS_EMPTY_CONTRACT",
    "SOLVER_EMPTY_ENTITY_LIST_FORM",
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


# ---------------------------------------------------------------------------
# Audio2Tool builder registration (E2.1, 2026-09-05)
# ---------------------------------------------------------------------------
# The Audio2Tool builder lives in its own module (``knowledge_build_a2t``: the
# SLURP builder above stays byte-frozen because the locked baseline cites its
# snapshot hash), but the owner engineering base rule names THIS file as one
# of the six canonical registration sites, so the registration itself belongs
# here rather than beside the implementation. A BOTTOM import, not a
# top-of-file one: ``knowledge_build_a2t`` imports nothing from this module,
# so there is no cycle either way, and placing it here keeps the module's own
# import block untouched.
from .knowledge_build_a2t import (  # noqa: E402  (deliberate bottom import)
    A2T_KB_BUILD_POLICY_ID,
    build_a2t_knowledge_snapshot_from_lock,
)

KNOWLEDGE_BUILDERS.register(
    A2T_KB_BUILD_POLICY_ID, build_a2t_knowledge_snapshot_from_lock
)


# Authored semantic stores retain the canonical registration site while their
# thin compilers live beside the shared knowledge contracts.
from .semantic_knowledge_build import (  # noqa: E402
    FACTORED_INTENT_BOUNDARY_BUILD_POLICY_ID,
    INTENT_BOUNDARY_BUILD_POLICY_ID,
    SLOT_CONTRACT_BUILD_POLICY_ID,
    STAGE3_DELTA_BUILD_POLICY_ID,
    STAGE3_DELTA_V2_BUILD_POLICY_ID,
    build_factored_intent_boundary_snapshot,
    build_intent_boundary_snapshot,
    build_slot_contract_snapshot,
    build_stage3_delta_snapshot,
    build_stage3_delta_snapshot_v2,
)

KNOWLEDGE_BUILDERS.register(
    INTENT_BOUNDARY_BUILD_POLICY_ID, build_intent_boundary_snapshot
)
KNOWLEDGE_BUILDERS.register(
    FACTORED_INTENT_BOUNDARY_BUILD_POLICY_ID,
    build_factored_intent_boundary_snapshot,
)
KNOWLEDGE_BUILDERS.register(
    SLOT_CONTRACT_BUILD_POLICY_ID, build_slot_contract_snapshot
)
# Stage-3 S3-5 (2026-09-22): the append-only delta store's builder,
# registered the same way its two authored siblings above are -- the
# canonical registration site stays here even though the compiler itself
# lives beside the shared knowledge contracts in semantic_knowledge_build.py.
KNOWLEDGE_BUILDERS.register(
    STAGE3_DELTA_BUILD_POLICY_ID, build_stage3_delta_snapshot
)
# Stage-3 S3-4s (owner decision 106, 2026-09-23): the NODE-TARGETED delta
# builder, registered BESIDE v1 so a v1 release stays flyable and a v2
# release can be built without a migration.
KNOWLEDGE_BUILDERS.register(
    STAGE3_DELTA_V2_BUILD_POLICY_ID, build_stage3_delta_snapshot_v2
)

__all__ += [
    "FACTORED_INTENT_BOUNDARY_BUILD_POLICY_ID",
    "INTENT_BOUNDARY_BUILD_POLICY_ID",
    "SLOT_CONTRACT_BUILD_POLICY_ID",
    "STAGE3_DELTA_BUILD_POLICY_ID",
    "STAGE3_DELTA_V2_BUILD_POLICY_ID",
    "build_factored_intent_boundary_snapshot",
    "build_intent_boundary_snapshot",
    "build_slot_contract_snapshot",
    "build_stage3_delta_snapshot",
    "build_stage3_delta_snapshot_v2",
]


# Source-governed builders use the same canonical registration boundary.
from .governed_context_build import (  # noqa: E402
    GOVERNED_CONTEXT_BUILD_POLICY_ID,
    build_governed_context_snapshot,
)

KNOWLEDGE_BUILDERS.register(
    GOVERNED_CONTEXT_BUILD_POLICY_ID, build_governed_context_snapshot
)
