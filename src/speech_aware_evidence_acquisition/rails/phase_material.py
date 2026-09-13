"""E1 config seam: a phase program's per-phase material, from config alone.

``rails.controllers.EvidenceAgentController`` has always taken its per-phase
instruction and response format from an injected
``material_for_phase(phase_name, context)`` callable, and
``rails.phase_runner.run_program`` from the richer
``material_for_phase(phase_name, context, sealed_states)``. Nothing built
either from config, so every multi-contact cell needed a launcher script to
hand-write one -- which is exactly the fragmentation the owner's 2026-09-03
"one base, thin derivations" rule forbids, and why
``core.flight.FlightRuntime.bind_phase_program_material`` had no callers at
all.

This module is that missing builder. A baseline fragment declares

.. code-block:: json

    "phase_material": {
      "select": {
        "instruction_template": "probes/a2t_phase_select.txt",
        "instruction_fill": "audio2tool-registry-compact",
        "response_format_id": "select-response-v1"
      },
      "fill": {
        "instruction_template": "probes/a2t_phase_fill.txt",
        "predecessor_binding": "append-sealed-state"
      }
    }

and :func:`load_phase_material_specs` turns it into one
:class:`PhaseMaterialSpec` per phase of the program, fail-closed against the
program's own ``PhaseSpec`` list. Identity is the same as every other
instruction in this study: the config hash pins the template PATH and the
fill NAME, ``configs/probes/manifest.json`` pins the template BYTES, and the
umbrella lock pins the carrier data the fill reads.

Three things this module deliberately does NOT do:

* it never ranks, retrieves or fuses evidence (that is ``rails.supply`` /
  ``rails.kb_policy``, reached through ``supply_for_phase``);
* it never reads gold, and never reads the adapter's sample object -- the
  material callable sees only ``rails.runner.AgentRuntimeContext``;
* it never writes the system message. The system message is
  ``adapter.instruction(sample)`` plus the adapter's task contract, assembled
  by ``rails.runner._agent_messages``; a phase's instruction rides the
  payload ``history`` CONTROL turn (``rails.core_client._agent_history``).

One thing in a phase instruction is genuinely per sample and still config
expressible: text derived from the PREDECESSOR STATE this phase is bound to.
The SLURP slot stage needs the TRAIN slot schema of the intent the sealed
closed-list contact predicted for THAT row, and there are sixty such blocks.
A phase therefore also declares

.. code-block:: json

    "slots": {
      "instruction_template": "probes/slurp_phase_slots.txt",
      "predecessor_binding": "sealed-manifest",
      "predecessor_source": {"...": "..."},
      "state_fill": "slurp-intent-slot-schema-for-state"
    }

and :data:`PHASE_STATE_FILLS` resolves that name to a
``(state_content) -> str`` callable whose output is appended after the state
block. Still config alone, still hashed by the config hash, still no
launcher.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence

from ..core.base import RESPONSE_FORMATS, Registry
from ..core.instructions import (
    TOOL_SCHEMAS_PLACEHOLDER,
    _TEMPLATE_RELPATH_PATTERN,
    render_template_with_fill,
)
from .controllers import PhaseProgram
from .errors import RailsError
from .knowledge import AgentStateArtifact
from .material import PhaseMaterial

#: How a phase's instruction is conditioned on what ran before it.
#:
#: ``"none"``      -- the rendered static text, and nothing else.
#: ``"append-sealed-state"`` -- append THIS run's immediately preceding
#:                    phase's sealed ``AgentStateArtifact`` for the same
#:                    sample (``run_program`` threads it in as
#:                    ``sealed_states``).
#: ``"sealed-manifest"`` -- append a state rebuilt from an ALREADY SEALED
#:                    bundle of a different run (see
#:                    :func:`sealed_states_from_manifest`). This is how a
#:                    slot-stage cell conditions on the sealed closed-list
#:                    intent without re-flying the contact that produced it.
PREDECESSOR_BINDINGS = frozenset({"none", "append-sealed-state", "sealed-manifest"})

_SPEC_KEYS = frozenset(
    {
        "instruction_template",
        "instruction_fill",
        "fill_params",
        "response_format_id",
        "predecessor_binding",
        "predecessor_source",
        "state_fill",
    }
)
_PREDECESSOR_SOURCE_KEYS = frozenset(
    {"manifest_relpath", "manifest_sha256", "producer_policy_id"}
)

#: The exact prefix an appended predecessor state carries. Fixed here rather
#: than made configurable: a two-contact cell's paired contrast is only a
#: single-factor contrast if this framing is the same in every arm.
PREDECESSOR_PREFIX = "Prior phase response"

#: Registered PER-SAMPLE state fills: ``name -> (() -> (state_content) -> str)``.
#:
#: A phase whose ``predecessor_binding`` carries a state can declare
#: ``"state_fill": "<name>"``. :func:`build_material_for_phase` then appends
#: ``fill(state.content)`` AFTER the appended state, so an arm that declares a
#: state fill differs from the otherwise identical arm that does not by a pure
#: per-sample SUFFIX -- the same single-factor discipline
#: ``data.slurp.render_slurp_closed_label_inventory`` follows for the system
#: message, one layer out.
#:
#: A registry ENTRY is a zero-argument factory returning the fill, not the fill
#: itself, so a fill that has to read pinned carrier data pays for it once per
#: run and only when a config actually names it. The factory resolves the
#: umbrella lock and the data root the same way every flight entry point does
#: (``data.lock.load_lock(umbrella_lock_path())`` / ``data.lock.data_root()``);
#: ``build_material_for_phase``'s own ``state_fill_by_phase=`` argument stays
#: the explicit seam for a caller that already holds them (and for tests).
PHASE_STATE_FILLS = Registry("phase state fill")


#: The registered legal-label projection rules a SLURP state fill may select
#: its block through, by the SAME ids ``core.scorers`` registers the scoring
#: side under. Config names one of these; nothing else is resolvable, and the
#: default is no projection at all, so every already-flown cell keeps its own
#: selection byte for byte.
SLURP_STATE_INTENT_PROJECTIONS = (
    "slurp-legal-label-projection-v1",
    "slurp-legal-label-projection-v2",
)


def _slurp_intent_projection(projection: str | None):
    """A projection id from ``fill_params`` as a bound rule, or ``None``.

    THE SEAM, and why it is here rather than in the scorer. The re-lock of
    2026-09-06 changed which SCORER the SLURP comparator is read through;
    this is the other half of the same rule, applied at SELECTION time. A
    sealed closed-list response naming a pair TRAIN never carries -- 3.9 % of
    DEV-1000 -- otherwise sends its row to the 26,720-character full-schema
    fallback, and under v2 seventeen of those rows would instead get their
    gold intent's own block.

    It is a per-arm config switch rather than a global default precisely
    because it is not free: an arm that projects while its sealed comparator
    did not would beat that comparator partly by better block selection, so
    the switch is set per read population and identically across the arms of
    one contrast (preregistration section 4).
    """

    if projection is None:
        return None
    if not isinstance(projection, str) or projection not in (
        SLURP_STATE_INTENT_PROJECTIONS
    ):
        raise PhaseMaterialError(
            f"unknown SLURP intent projection {projection!r}; the registered rules are "
            f"{list(SLURP_STATE_INTENT_PROJECTIONS)}"
        )
    from ..data.lock import (  # noqa: PLC0415 (cycle guard, and lazily paid)
        data_root,
        load_lock,
        umbrella_lock_path,
    )
    from ..reproduction.slurp_official_eval import (  # noqa: PLC0415
        load_legal_intent_inventory,
    )
    from ..reproduction.slurp_scoring import (  # noqa: PLC0415
        project_slu_label,
        project_slu_label_v2,
    )

    rule = {
        SLURP_STATE_INTENT_PROJECTIONS[0]: project_slu_label,
        SLURP_STATE_INTENT_PROJECTIONS[1]: project_slu_label_v2,
    }[projection]
    inventory = load_legal_intent_inventory(load_lock(umbrella_lock_path()), data_root())

    def project(scenario, action, *, parsed: bool = True):
        return rule(scenario, action, inventory, parsed=parsed)

    return project


def _slurp_intent_slot_schema_state_fill(*, projection: str | None = None):
    """Factory for ``"slurp-intent-slot-schema-for-state"``.

    The returned fill renders, for ONE sealed closed-list SLU response, the
    per-intent TRAIN slot schema block of the intent that response names
    (``data.slurp.render_slurp_slot_schema_for_state_detail``), falling back
    to the full schema when the response does not parse or names a
    (scenario, action) pair TRAIN never carries. TRAIN only: the loader it
    calls has no ``split`` parameter and can reach no devel or test file.

    ``projection`` (a ``fill_params`` key, absent by default) names a
    registered legal-label projection applied to the sealed label BEFORE the
    block is selected; see :func:`_slurp_intent_projection`. KC-S1b's own
    fragment declares none and is unchanged.
    """

    from ..data.lock import (  # noqa: PLC0415 (cycle guard, and lazily paid)
        data_root,
        load_lock,
        umbrella_lock_path,
    )
    from ..data.slurp import (  # noqa: PLC0415 (cycle guard)
        load_slurp_intent_slot_schema,
        render_slurp_slot_schema_for_state_detail,
    )

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    schema = load_slurp_intent_slot_schema(lock, root)
    project = _slurp_intent_projection(projection)

    def fill(state_content: str) -> str:
        text, _used_intent, _fallback = render_slurp_slot_schema_for_state_detail(
            lock, root, state_content, schema=schema, projection=project
        )
        return text

    return fill


PHASE_STATE_FILLS.register(
    "slurp-intent-slot-schema-for-state", _slurp_intent_slot_schema_state_fill
)


def _slurp_intent_hypotheses_state_fill(*, max_candidates: int):
    """Build the source-bound ranked-alternative view from TRAIN legal IDs."""

    from ..data.lock import data_root, load_lock, umbrella_lock_path  # noqa: PLC0415
    from ..reproduction.slurp_official_eval import (  # noqa: PLC0415
        load_legal_intent_inventory,
    )
    from .slurp_intent_hypotheses import (  # noqa: PLC0415
        SlurpIntentHypothesisStateFill,
    )

    inventory = load_legal_intent_inventory(
        load_lock(umbrella_lock_path()), data_root()
    )
    legal_intent_ids = {
        f"{scenario}_{action}" for scenario, action in inventory.pairs
    }
    return SlurpIntentHypothesisStateFill(
        legal_intent_ids=legal_intent_ids, max_candidates=max_candidates
    )


PHASE_STATE_FILLS.register(
    "slurp-intent-hypotheses-for-joint-resolution-v1",
    _slurp_intent_hypotheses_state_fill,
)


def _slurp_evolved_slot_schema_state_fill(
    *,
    artifact_relpath: str,
    artifact_sha256: str,
    projection: str | None = None,
    **provenance: object,
):
    """Factory for ``"slurp-evolved-slot-schema-for-state"`` (EVO-S1).

    A sibling of ``"slurp-intent-slot-schema-for-state"`` and deliberately
    nothing more: same selection rule (the intent parsed out of the SEALED
    closed-list response), same grammar, same one-block-per-row shape, same
    FULL-schema fallback when the response does not parse or names a
    (scenario, action) pair TRAIN never carries. The single difference is
    WHICH blocks it renders -- the evolved ones a round's committed artifact
    names.

    ``artifact_relpath`` and ``artifact_sha256`` come from the phase's
    ``fill_params``, which ``rails.evolution.write_candidate_fragments``
    emits, and the digest is re-checked over the file's own bytes here: a
    fragment can therefore never fly against an artifact edited after the
    fragment was written. ``provenance`` absorbs the writer's other pinning
    keys (``portfolio_sha256``, ``round``, ``k``); they are inside the config
    hash so a receipt says which portfolio flew, and this factory does not
    read them. ``projection`` is the one fill param the writer does NOT own:
    it is declared on the base fragment and carried through unchanged, so the
    incumbent arm and every candidate arm of one fold select their block from
    the same sealed label (:func:`_slurp_intent_projection`).

    Every intent the artifact does not name keeps its ``A_0`` block byte for
    byte (``rails.proposer.slurp_candidate_schema``), and every count and
    share in every block is re-derived from the unfloored TRAIN table, so a
    candidate can never write a number.

    The returned fill counts what it did: ``fill.counts["rows"]`` and
    ``fill.counts["fallback"]`` are the per-read fallback tally the
    preregistration requires beside every number (section 3: 42 of 1,000 rows
    on DEV-1000).
    """

    from ..data.lock import (  # noqa: PLC0415 (cycle guard, and lazily paid)
        REPO_ROOT,
        data_root,
        load_lock,
        umbrella_lock_path,
    )
    from ..data.slurp import (  # noqa: PLC0415 (cycle guard)
        load_slurp_intent_slot_schema,
        render_slurp_slot_schema_for_state_detail,
    )
    from .proposer import ProposerError, slurp_candidate_schema  # noqa: PLC0415

    if not isinstance(artifact_relpath, str) or not artifact_relpath.strip():
        raise PhaseMaterialError(
            "slurp-evolved-slot-schema-for-state needs an artifact_relpath"
        )
    if not isinstance(artifact_sha256, str) or not re.fullmatch(
        r"[0-9a-f]{64}", artifact_sha256
    ):
        raise PhaseMaterialError(
            "slurp-evolved-slot-schema-for-state needs a sha256 hex artifact_sha256"
        )
    if Path(artifact_relpath).is_absolute() or ".." in Path(artifact_relpath).parts:
        raise PhaseMaterialError(
            f"artifact_relpath {artifact_relpath!r} is not a plain relative path"
        )
    path = Path(REPO_ROOT) / artifact_relpath
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise PhaseMaterialError(f"evolved slot-schema artifact missing: {path}") from error
    measured = hashlib.sha256(raw).hexdigest()
    if measured != artifact_sha256:
        raise PhaseMaterialError(
            f"evolved slot-schema artifact {artifact_relpath} hashes to {measured}, not "
            f"the {artifact_sha256} its fragment names"
        )
    try:
        blocks = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise PhaseMaterialError(
            f"evolved slot-schema artifact {artifact_relpath} is not JSON: {error}"
        ) from error

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    base = load_slurp_intent_slot_schema(lock, root)
    unfloored = load_slurp_intent_slot_schema(lock, root, min_share=0.0)
    try:
        schema = slurp_candidate_schema(blocks, unfloored=unfloored, base=base)
    except ProposerError as error:
        raise PhaseMaterialError(
            f"evolved slot-schema artifact {artifact_relpath} is not a legal candidate: "
            f"{error}"
        ) from error

    project = _slurp_intent_projection(projection)
    counts = {"rows": 0, "fallback": 0}

    def fill(state_content: str) -> str:
        text, _used_intent, fallback = render_slurp_slot_schema_for_state_detail(
            lock, root, state_content, schema=schema, projection=project
        )
        counts["rows"] += 1
        counts["fallback"] += int(bool(fallback))
        return text

    fill.counts = counts  # type: ignore[attr-defined]
    return fill


PHASE_STATE_FILLS.register(
    "slurp-evolved-slot-schema-for-state", _slurp_evolved_slot_schema_state_fill
)


def _kv_class_table(relpath: object, sha256: object) -> dict[str, str]:
    """``{entity_type: slot class}`` from a committed, hash-pinned artifact.

    The KV family's CLOSED/MIXED/OPEN split is MF-10's measurement, not a
    quantity a flight may recompute: its coverage statistic is read out of
    MF-9's committed receipt, and re-deriving it inside a fill would make a
    cell's block depend on which receipts happened to be on disk. So it
    enters exactly as EVO-S1's evolved schema does -- a relative path plus a
    sha256 re-checked over the file's own bytes, both inside the config hash.
    """

    from ..data.lock import REPO_ROOT  # noqa: PLC0415 (cycle guard, lazily paid)

    if not isinstance(relpath, str) or not relpath.strip():
        raise PhaseMaterialError(
            "slurp-slot-knowledge-view-for-state needs a class_artifact_relpath for "
            "the descriptions and cards views"
        )
    if not isinstance(sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", sha256):
        raise PhaseMaterialError(
            "slurp-slot-knowledge-view-for-state needs a sha256 hex "
            "class_artifact_sha256"
        )
    if Path(relpath).is_absolute() or ".." in Path(relpath).parts:
        raise PhaseMaterialError(
            f"class_artifact_relpath {relpath!r} is not a plain relative path"
        )
    path = Path(REPO_ROOT) / relpath
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise PhaseMaterialError(f"KV slot-class artifact missing: {path}") from error
    measured = hashlib.sha256(raw).hexdigest()
    if measured != sha256:
        raise PhaseMaterialError(
            f"KV slot-class artifact {relpath} hashes to {measured}, not the {sha256} "
            "its fragment names"
        )
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise PhaseMaterialError(
            f"KV slot-class artifact {relpath} is not JSON: {error}"
        ) from error
    table = document.get("slot_class_by_type") if isinstance(document, dict) else None
    if not isinstance(table, dict) or not table:
        raise PhaseMaterialError(
            f"KV slot-class artifact {relpath} carries no 'slot_class_by_type' object"
        )
    return {str(name): str(value) for name, value in sorted(table.items())}


def _slurp_slot_knowledge_view_state_fill(
    *,
    view: str,
    twin: bool = False,
    class_artifact_relpath: object = None,
    class_artifact_sha256: object = None,
    k: object = None,
    seed: object = None,
    projection: str | None = None,
    **provenance: object,
):
    """Factory for ``"slurp-slot-knowledge-view-for-state"`` (the KV family).

    A sibling of ``"slurp-intent-slot-schema-for-state"`` and deliberately
    nothing more: same selection rule (the intent parsed out of the SEALED
    closed-list response), same one-block-per-row shape, same FULL-schema
    fallback when the response does not parse or names a (scenario, action)
    pair TRAIN never carries, same pure per-sample SUFFIX position. The single
    difference is WHAT the block says -- ``rails.slurp_knowledge_views``
    renders the example-free schema and, for a view above KV-0, one further
    block of TRAIN knowledge.

    ``view`` is one of ``rails.slurp_knowledge_views.KV_VIEWS``; ``twin``
    selects that view's form control. ``class_artifact_relpath`` /
    ``class_artifact_sha256`` pin the CLOSED/MIXED/OPEN table the
    ``descriptions`` and ``cards`` views need (:func:`_kv_class_table`); the
    ``examples-free`` and ``fewshot`` views take none. ``k`` and ``seed``
    default to the module's declared ``FEWSHOT_K`` / ``FEWSHOT_SEED`` and are
    inside the config hash whenever a fragment states them. ``projection`` is
    the same per-arm block-selection switch every SLURP state fill takes, and
    the KV family declares NONE for the same reason KU-S3 does: its comparator
    chose its blocks from unprojected bytes.

    Every block is rendered ONCE per intent at factory time (sixty intents
    plus the fallback), so the per-row fill is a dictionary lookup and a
    1,000-row flight pays for the TRAIN mining once. ``fill.counts`` carries
    the per-read ``rows``/``fallback`` tally every SLURP verdict reports.
    """

    from collections import Counter, defaultdict  # noqa: PLC0415

    from ..analysis.slurp_slot_vocabulary import (  # noqa: PLC0415 (cycle guard)
        SLOT_CLASS_CLOSED,
        build_vocabulary_card,
    )
    from ..data.lock import (  # noqa: PLC0415 (cycle guard, and lazily paid)
        data_root,
        load_lock,
        umbrella_lock_path,
    )
    from ..data.slurp import (  # noqa: PLC0415 (cycle guard)
        load_slurp_intent_slot_schema,
        load_slurp_train_material,
        slurp_intent_from_state_content,
    )
    from .slurp_knowledge_views import (  # noqa: PLC0415 (cycle guard)
        FEWSHOT_K,
        FEWSHOT_SEED,
        KV_VIEW_CARDS,
        KV_VIEW_DESCRIPTIONS,
        KV_VIEW_EXAMPLES_FREE,
        KV_VIEW_FEWSHOT,
        Exemplar,
        assert_view,
        build_type_description,
        compose_view,
        derange_card_mapping,
        derange_description_mapping,
        donor_intent_mapping,
        render_examples_free_block,
        select_exemplars,
    )

    resolved_view = assert_view(view)
    if not isinstance(twin, bool):
        raise PhaseMaterialError("slurp-slot-knowledge-view-for-state twin must be bool")
    exemplar_k = FEWSHOT_K if k is None else k
    if isinstance(exemplar_k, bool) or not isinstance(exemplar_k, int) or exemplar_k <= 0:
        raise PhaseMaterialError(
            f"slurp-slot-knowledge-view-for-state k must be a positive int, got {k!r}"
        )
    exemplar_seed = FEWSHOT_SEED if seed is None else seed
    if isinstance(exemplar_seed, bool) or not isinstance(exemplar_seed, int):
        raise PhaseMaterialError(
            f"slurp-slot-knowledge-view-for-state seed must be an int, got {seed!r}"
        )

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    schema = load_slurp_intent_slot_schema(lock, root)
    intents = tuple(schema.intent_ids)
    block_types = {
        intent: tuple(schema.intents[intent].entity_types) for intent in intents
    }
    utterances = {intent: schema.intents[intent].n for intent in intents}
    mentions = {intent: schema.intents[intent].mentions for intent in intents}
    type_tables = {intent: schema.intents[intent].types for intent in intents}
    fallback_types = tuple(
        sorted({name for types in block_types.values() for name in types})
    )

    schema_by_intent = {
        intent: render_examples_free_block(
            type_tables,
            intents=(intent,),
            utterances=utterances,
            mentions=mentions,
            min_share=schema.min_share,
        )
        for intent in intents
    }
    fallback_schema = render_examples_free_block(
        type_tables,
        intents=intents,
        utterances=utterances,
        mentions=mentions,
        min_share=schema.min_share,
    )

    cards_by_type: dict[str, object] = {}
    descriptions_by_type: dict[str, object] = {}
    exemplars_by_intent: dict[str, tuple[object, ...]] = {}
    fallback_exemplars: tuple[object, ...] = ()
    if resolved_view != KV_VIEW_EXAMPLES_FREE:
        train = load_slurp_train_material(lock, root)
        if resolved_view in (KV_VIEW_DESCRIPTIONS, KV_VIEW_CARDS):
            classes = _kv_class_table(class_artifact_relpath, class_artifact_sha256)
            forms: dict[str, Counter] = defaultdict(Counter)
            for utterance in train:
                for entity in utterance.entities:
                    name = str(entity.type).strip()
                    filler = str(entity.filler).strip()
                    if name and filler:
                        forms[name][filler] += 1
            if resolved_view == KV_VIEW_CARDS:
                cards_by_type = {
                    name: build_vocabulary_card(name, dict(table))
                    for name, table in sorted(forms.items())
                    if classes.get(name) == SLOT_CLASS_CLOSED
                }
            else:
                descriptions_by_type = {
                    name: build_type_description(
                        name, dict(table), slot_class=classes[name]
                    )
                    for name, table in sorted(forms.items())
                    if name in classes
                }
        else:
            pool_by_intent: dict[str, list[object]] = defaultdict(list)
            whole_pool: list[object] = []
            for utterance in train:
                exemplar = Exemplar(
                    utterance_id=utterance.utterance_id,
                    sentence=utterance.sentence.strip(),
                    slots=tuple(
                        (str(entity.type), str(entity.filler))
                        for entity in utterance.entities
                        if str(entity.type).strip() and str(entity.filler).strip()
                    ),
                )
                pool_by_intent[f"{utterance.scenario}_{utterance.action}"].append(
                    exemplar
                )
                whole_pool.append(exemplar)
            donors = (
                donor_intent_mapping(
                    {
                        scenario: sorted(
                            {
                                intent
                                for intent in intents
                                if intent.startswith(f"{scenario}_")
                            }
                        )
                        for scenario in sorted(
                            {intent.split("_", 1)[0] for intent in intents}
                        )
                    }
                )
                if twin
                else {}
            )
            for intent in intents:
                source = donors.get(intent, intent) if twin else intent
                exemplars_by_intent[intent] = select_exemplars(
                    pool_by_intent.get(source, ()),
                    block_types[intent],
                    k=exemplar_k,
                    seed=exemplar_seed,
                )
            fallback_exemplars = select_exemplars(
                whole_pool, fallback_types, k=exemplar_k, seed=exemplar_seed
            )

    card_remap = (
        derange_card_mapping(block_types, cards_by_type)
        if twin and resolved_view == KV_VIEW_CARDS
        else {}
    )
    description_remap = (
        derange_description_mapping(block_types, descriptions_by_type)
        if twin and resolved_view == KV_VIEW_DESCRIPTIONS
        else {}
    )

    def _material(intent: str | None) -> dict[str, object]:
        types = fallback_types if intent is None else block_types[intent]
        substitution: Mapping[str, str] = {}
        if resolved_view == KV_VIEW_CARDS:
            substitution = card_remap.get(intent or "", {}) if intent else {}
            return {
                "cards": [
                    cards_by_type[substitution.get(name, name)]
                    for name in types
                    if name in cards_by_type
                    and substitution.get(name, name) in cards_by_type
                ]
            }
        if resolved_view == KV_VIEW_DESCRIPTIONS:
            substitution = description_remap.get(intent or "", {}) if intent else {}
            return {
                "descriptions": [
                    descriptions_by_type[substitution.get(name, name)]
                    for name in types
                    if name in descriptions_by_type
                    and substitution.get(name, name) in descriptions_by_type
                ]
            }
        if resolved_view == KV_VIEW_FEWSHOT:
            return {
                "exemplars": list(
                    fallback_exemplars
                    if intent is None
                    else exemplars_by_intent.get(intent, ())
                )
            }
        return {}

    rendered_by_intent = {
        intent: compose_view(
            intent=intent,
            view=resolved_view,
            twin=twin,
            schema_text=schema_by_intent[intent],
            **_material(intent),
        ).text
        for intent in intents
    }
    rendered_fallback = compose_view(
        intent=None,
        view=resolved_view,
        twin=twin,
        schema_text=fallback_schema,
        **_material(None),
    ).text

    project = _slurp_intent_projection(projection)
    counts = {"rows": 0, "fallback": 0}

    def fill(state_content: str) -> str:
        intent = slurp_intent_from_state_content(state_content, projection=project)
        counts["rows"] += 1
        if intent is not None and intent in rendered_by_intent:
            return rendered_by_intent[intent]
        counts["fallback"] += 1
        return rendered_fallback

    fill.counts = counts  # type: ignore[attr-defined]
    fill.view = resolved_view  # type: ignore[attr-defined]
    fill.twin = twin  # type: ignore[attr-defined]
    return fill


PHASE_STATE_FILLS.register(
    "slurp-slot-knowledge-view-for-state", _slurp_slot_knowledge_view_state_fill
)



def _slurp_hypothesis_candidate_contracts_state_fill(
    *, candidate_source_sha256: str, max_candidates: int = 3
):
    """Build a shared, source-bound contract view for hypothesis consumers."""
    from ..data.lock import data_root, load_lock, umbrella_lock_path  # noqa: PLC0415
    from .slurp_hypothesis_candidate_contract_view import (  # noqa: PLC0415
        build_slurp_hypothesis_candidate_contract_view,
    )

    return build_slurp_hypothesis_candidate_contract_view(
        load_lock(umbrella_lock_path()), data_root(),
        candidate_source_sha256=candidate_source_sha256,
        max_candidates=max_candidates,
    )


PHASE_STATE_FILLS.register(
    "slurp-hypothesis-candidate-contracts-for-state-v1",
    _slurp_hypothesis_candidate_contracts_state_fill,
)


class PhaseMaterialError(RailsError):
    """A ``phase_material`` config fragment, or the material built from it,
    is invalid."""


@dataclass(frozen=True)
class PhaseMaterialSpec:
    """One phase's config-declared material, before rendering."""

    phase: str
    purpose: str
    instruction_template: str
    instruction_fill: str | None = None
    fill_params: Mapping[str, object] = field(default_factory=dict)
    response_format_id: str | None = None
    predecessor_binding: str = "none"
    predecessor_source: Mapping[str, object] | None = None
    state_fill: str | None = None

    def validate(self) -> "PhaseMaterialSpec":
        for name in ("phase", "purpose", "instruction_template"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise PhaseMaterialError(
                    f"PhaseMaterialSpec.{name} must be a non-empty string"
                )
        if not _TEMPLATE_RELPATH_PATTERN.fullmatch(self.instruction_template):
            raise PhaseMaterialError(
                f"phase {self.phase!r} instruction_template "
                f"{self.instruction_template!r} is not a plain relative path under "
                "configs/ (no absolute paths, no '..', no backslashes)"
            )
        if self.instruction_fill is not None and (
            not isinstance(self.instruction_fill, str) or not self.instruction_fill.strip()
        ):
            raise PhaseMaterialError(
                f"phase {self.phase!r} instruction_fill must be a non-empty string or null"
            )
        if not isinstance(self.fill_params, Mapping):
            raise PhaseMaterialError(
                f"phase {self.phase!r} fill_params must be an object"
            )
        if (
            self.fill_params
            and self.instruction_fill is None
            and self.state_fill is None
            and self.response_format_id is None
        ):
            raise PhaseMaterialError(
                f"phase {self.phase!r} declares fill_params but no registered "
                "instruction, state or response-format consumer"
            )
        if self.fill_params and self.instruction_fill is not None and (
            self.state_fill is not None
        ):
            raise PhaseMaterialError(
                f"phase {self.phase!r} declares fill_params with BOTH an "
                "instruction_fill and a state_fill; the params have exactly one "
                "consumer, and silently handing them to two builders would make the "
                "prompt depend on which one read them"
            )
        if self.fill_params and self.state_fill is not None and (
            self.response_format_id is not None
        ):
            raise PhaseMaterialError(
                f"phase {self.phase!r} declares fill_params with BOTH a state_fill and "
                "a response_format_id; resolve_response_formats would read the state "
                "fill's own params"
            )
        if self.response_format_id is not None and (
            not isinstance(self.response_format_id, str)
            or not self.response_format_id.strip()
        ):
            raise PhaseMaterialError(
                f"phase {self.phase!r} response_format_id must be a non-empty string "
                "or null"
            )
        if self.predecessor_binding not in PREDECESSOR_BINDINGS:
            raise PhaseMaterialError(
                f"phase {self.phase!r} predecessor_binding must be one of "
                f"{sorted(PREDECESSOR_BINDINGS)}, got {self.predecessor_binding!r}"
            )
        if self.predecessor_binding == "sealed-manifest":
            source = self.predecessor_source
            if not isinstance(source, Mapping) or set(source) != _PREDECESSOR_SOURCE_KEYS:
                raise PhaseMaterialError(
                    f"phase {self.phase!r} predecessor_binding 'sealed-manifest' requires "
                    f"a predecessor_source object with exactly "
                    f"{sorted(_PREDECESSOR_SOURCE_KEYS)}"
                )
            for key in sorted(_PREDECESSOR_SOURCE_KEYS):
                if not isinstance(source[key], str) or not source[key].strip():
                    raise PhaseMaterialError(
                        f"phase {self.phase!r} predecessor_source.{key} must be a "
                        "non-empty string"
                    )
        elif self.predecessor_source is not None:
            raise PhaseMaterialError(
                f"phase {self.phase!r} declares predecessor_source but its "
                f"predecessor_binding is {self.predecessor_binding!r}"
            )
        if self.state_fill is not None:
            if not isinstance(self.state_fill, str) or not self.state_fill.strip():
                raise PhaseMaterialError(
                    f"phase {self.phase!r} state_fill must be a non-empty string or null"
                )
            if self.predecessor_binding == "none":
                raise PhaseMaterialError(
                    f"phase {self.phase!r} declares state_fill "
                    f"{self.state_fill!r} but predecessor_binding 'none'; a state fill "
                    "reads the predecessor state, so there has to be one"
                )
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "phase": self.phase,
            "purpose": self.purpose,
            "instruction_template": self.instruction_template,
            "instruction_fill": self.instruction_fill,
            "fill_params": dict(self.fill_params),
            "response_format_id": self.response_format_id,
            "predecessor_binding": self.predecessor_binding,
            "predecessor_source": (
                dict(self.predecessor_source)
                if self.predecessor_source is not None
                else None
            ),
            "state_fill": self.state_fill,
        }


def load_phase_material_specs(
    values: Mapping[str, object], program: PhaseProgram
) -> Mapping[str, PhaseMaterialSpec]:
    """Parse the baseline fragment's ``phase_material`` object against
    ``program``.

    Refuses: a missing or non-object ``phase_material``; a phase the program
    does not declare; a program phase with no material; an unknown key in a
    phase entry; and any disagreement between a phase's declared
    ``response_format_id`` and the program's own ``PhaseSpec`` -- both
    present and equal, or both absent, nothing in between (the same rule
    ``EvidenceAgentController._dispatch`` enforces at contact time, moved
    forward to config-load time where it is free).
    """

    program.validate()
    declared = values.get("phase_material")
    if not isinstance(declared, Mapping) or not declared:
        raise PhaseMaterialError(
            f"policy {program.program_id!r} is a phase program; its baseline fragment "
            "must declare a non-empty 'phase_material' object keyed by phase name "
            f"({list(program.phase_names())})"
        )
    known = set(program.phase_names())
    unknown = sorted(set(declared) - known)
    if unknown:
        raise PhaseMaterialError(
            f"phase_material names phase(s) {unknown} that program "
            f"{program.program_id!r} does not declare; its phases are "
            f"{sorted(known)}"
        )
    missing = sorted(known - set(declared))
    if missing:
        raise PhaseMaterialError(
            f"phase_material has no entry for program {program.program_id!r} phase(s) "
            f"{missing}; every phase must declare its own material"
        )

    specs: dict[str, PhaseMaterialSpec] = {}
    for phase in program.phases:
        entry = declared[phase.name]
        if not isinstance(entry, Mapping):
            raise PhaseMaterialError(
                f"phase_material[{phase.name!r}] must be an object"
            )
        extra = sorted(set(entry) - _SPEC_KEYS)
        if extra:
            raise PhaseMaterialError(
                f"phase_material[{phase.name!r}] carries unknown key(s) {extra}; "
                f"known keys are {sorted(_SPEC_KEYS)}"
            )
        spec = PhaseMaterialSpec(
            phase=phase.name,
            purpose=phase.purpose,
            instruction_template=entry.get("instruction_template"),
            instruction_fill=entry.get("instruction_fill"),
            fill_params=dict(entry.get("fill_params") or {}),
            response_format_id=entry.get("response_format_id"),
            predecessor_binding=str(entry.get("predecessor_binding", "none")),
            predecessor_source=entry.get("predecessor_source"),
            state_fill=entry.get("state_fill"),
        ).validate()
        if spec.response_format_id != phase.response_format_id:
            raise PhaseMaterialError(
                f"phase {phase.name!r} declares response_format_id "
                f"{phase.response_format_id!r} in program {program.program_id!r} but "
                f"{spec.response_format_id!r} in phase_material; a phase's output "
                "contract has exactly one authority"
            )
        specs[phase.name] = spec
    return specs


def render_static_instruction(
    spec: PhaseMaterialSpec, repo_root: Path, lock: Mapping[str, object], root: Path
) -> str:
    """The phase's sample-independent instruction text.

    With an ``instruction_fill`` this is ``core.instructions.
    render_template_with_fill`` -- the same frozen-template-plus-registered-
    fill path every baseline ``task_instruction_template`` already uses,
    with ``fill_params`` passed as keyword arguments only when non-empty.
    Without one it is the template's own bytes, and a template that still
    carries the ``{tool_schemas}`` placeholder is refused rather than sent
    half-rendered.
    """

    spec.validate()
    if spec.instruction_fill is not None:
        return render_template_with_fill(
            spec.instruction_template,
            spec.instruction_fill,
            repo_root,
            lock,
            root,
            spec.fill_params,
        )
    template_path = Path(repo_root) / "configs" / spec.instruction_template
    if not template_path.is_file():
        raise PhaseMaterialError(f"phase instruction template missing: {template_path}")
    try:
        text = template_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise PhaseMaterialError(
            f"cannot read phase instruction template {template_path}: {error}"
        ) from error
    if TOOL_SCHEMAS_PLACEHOLDER in text:
        raise PhaseMaterialError(
            f"phase {spec.phase!r} template {template_path} carries a "
            f"{TOOL_SCHEMAS_PLACEHOLDER!r} placeholder but the phase declares no "
            "instruction_fill; an unfilled template must never reach the model"
        )
    if not text.strip():
        raise PhaseMaterialError(
            f"phase {spec.phase!r} template {template_path} is empty"
        )
    return text


def resolve_response_formats(
    specs: Mapping[str, PhaseMaterialSpec], lock: Mapping[str, object], root: Path
) -> Mapping[str, Mapping[str, object]]:
    """``{phase: response_format}`` for every phase that declares a
    ``response_format_id``, resolved through ``core.base.RESPONSE_FORMATS``
    (a ``(lock, root, **params) -> Mapping`` thunk registered in
    ``rails.controllers``). Phases without an id contribute no entry."""

    formats: dict[str, Mapping[str, object]] = {}
    for phase, spec in specs.items():
        if spec.response_format_id is None:
            continue
        builder = RESPONSE_FORMATS.resolve(spec.response_format_id)
        if not callable(builder):
            raise PhaseMaterialError(
                f"registered response format {spec.response_format_id!r} is not callable"
            )
        document = builder(lock, root, **dict(spec.fill_params))
        if not isinstance(document, Mapping) or not document:
            raise PhaseMaterialError(
                f"response format {spec.response_format_id!r} rendered an empty result "
                f"for phase {phase!r}"
            )
        formats[phase] = document
    return formats


def render_phase_predecessor_block(state: AgentStateArtifact) -> str:
    """Render the exact predecessor block shared by requests and replay checks."""
    return f"{PREDECESSOR_PREFIX} ({state.state_kind}):\n{state.content}"


def _appended(instruction: str, state: AgentStateArtifact) -> str:
    return f"{instruction}\n\n{render_phase_predecessor_block(state)}"


def _joined(instruction: str, rendered: str) -> str:
    """Append a per-sample state fill's text after the instruction,
    separated by one blank line -- the same join :func:`_appended` uses for
    the predecessor state block itself."""

    return instruction + "\n\n" + rendered


def _resolved_state_fills(
    specs: Mapping[str, PhaseMaterialSpec],
    explicit: Mapping[str, object] | None,
) -> dict[str, object]:
    """``{phase: (state_content) -> str}`` for every phase declaring one.

    An explicitly supplied callable wins over the config-declared name (that
    is what makes ``state_fill_by_phase=`` a seam a test or a caller holding
    its own lock/root can use); otherwise the name is resolved through
    :data:`PHASE_STATE_FILLS` and its factory is called ONCE, here, so a fill
    that reads pinned carrier data pays for it before the first contact
    rather than per sample. Refuses an explicit entry for a phase that
    declares no ``state_fill``: a fill nobody declared would be an
    undeclared, unhashed prompt difference.
    """

    supplied = dict(explicit or {})
    declared = {phase for phase, spec in specs.items() if spec.state_fill is not None}
    undeclared = sorted(set(supplied) - declared)
    if undeclared:
        raise PhaseMaterialError(
            f"state_fill_by_phase names phase(s) {undeclared} whose material declares no "
            "'state_fill'; a per-sample fill must be declared in config to be part of "
            "the run's hashed identity"
        )
    fills: dict[str, object] = {}
    for phase in sorted(declared):
        fill = supplied.get(phase)
        if fill is None:
            factory = PHASE_STATE_FILLS.resolve(str(specs[phase].state_fill))
            if not callable(factory):
                raise PhaseMaterialError(
                    f"registered phase state fill {specs[phase].state_fill!r} is not "
                    "callable"
                )
            # ``fill_params`` reach the FACTORY, not the per-sample fill: a
            # fill that has to open a committed artifact (EVO-S1's evolved
            # slot schema, named by relpath and sha256) pays for it once per
            # run, and the params are inside the config hash either way.
            fill = factory(**dict(specs[phase].fill_params))
        if not callable(fill):
            raise PhaseMaterialError(
                f"phase {phase!r} state fill {specs[phase].state_fill!r} did not resolve "
                "to a callable (state_content) -> str"
            )
        fills[phase] = fill
    return fills


def render_phase_state_fill(
    fill: object, *, state: AgentStateArtifact | None, sample_id: str,
    fallback_content: str | None = None,
) -> str:
    """Render the same state view for live material and request-capacity checks."""
    renderer = getattr(fill, "render_state", None)
    if callable(renderer):
        if state is None:
            raise PhaseMaterialError(
                "state view requires the full predecessor artifact; "
                "an unsealed padding estimate cannot supply its source binding"
            )
        return renderer(state, sample_id=sample_id)
    content = state.content if state is not None else fallback_content
    if content is None or not callable(fill):
        raise PhaseMaterialError("state fill requires callable content rendering")
    return fill(content)


def build_material_for_phase(
    specs: Mapping[str, PhaseMaterialSpec],
    *,
    program_id: str,
    static_text_by_phase: Mapping[str, str],
    response_format_by_phase: Mapping[str, Mapping[str, object]],
    per_sample_states: Mapping[str, Mapping[str, AgentStateArtifact]] | None = None,
    state_fill_by_phase: Mapping[str, object] | None = None,
):
    """Build the ``rails.phase_runner.ProgramMaterialForPhase`` callable.

    ``(phase_name, context, sealed_states) -> PhaseMaterial``. The
    instruction is the phase's already-rendered static text, plus -- under
    ``append-sealed-state`` -- this run's immediately preceding phase's
    sealed state for THIS sample, or -- under ``sealed-manifest`` -- the
    state ``per_sample_states[phase][sample_id]`` rebuilt from another run's
    sealed bundle. ``contact_id`` is ``"{program_id}:{phase}:{sample_id}"``,
    the same shape ``rails.controllers._default_material_for_phase`` mints.

    A phase that declares ``state_fill`` gets ONE more thing, LAST: the
    registered per-sample fill's text (:data:`PHASE_STATE_FILLS`), appended
    after the state block. Appending last is what makes the arm that
    declares a fill differ from the otherwise identical arm that does not by
    a pure per-sample suffix, so their paired contrast measures the fill and
    nothing else. ``state_fill_by_phase`` overrides the registered lookup
    with an already-built callable for a caller that holds its own lock and
    data root; it can only override a phase whose config declares a fill.

    Fail-closed on every missing piece: an unknown phase, a sample with no
    predecessor state, a phase whose response format was not resolved. All
    of them would otherwise become a silently weaker prompt on the wire.
    """

    if not isinstance(program_id, str) or not program_id:
        raise PhaseMaterialError("build_material_for_phase requires a program_id")
    states = dict(per_sample_states or {})
    state_fills = _resolved_state_fills(specs, state_fill_by_phase)

    def material_for_phase(
        phase_name: str,
        context: object,
        sealed_states: Mapping[str, AgentStateArtifact],
    ) -> PhaseMaterial:
        try:
            spec = specs[phase_name]
        except KeyError:
            raise PhaseMaterialError(
                f"no phase material for phase {phase_name!r}; known phases are "
                f"{sorted(specs)}"
            ) from None
        sample_id = getattr(context, "sample_id", None)
        if not isinstance(sample_id, str) or not sample_id:
            raise PhaseMaterialError(
                "material_for_phase needs an AgentRuntimeContext carrying a sample_id"
            )
        try:
            instruction = static_text_by_phase[phase_name]
        except KeyError:
            raise PhaseMaterialError(
                f"phase {phase_name!r} has no rendered instruction text"
            ) from None

        state: AgentStateArtifact | None = None
        if spec.predecessor_binding == "append-sealed-state":
            state = (sealed_states or {}).get(sample_id)
            if state is None:
                raise PhaseMaterialError(
                    f"phase {phase_name!r} binds its predecessor's sealed state but the "
                    f"preceding phase sealed none for sample {sample_id!r}"
                )
            instruction = _appended(instruction, state)
        elif spec.predecessor_binding == "sealed-manifest":
            state = states.get(phase_name, {}).get(sample_id)
            if state is None:
                raise PhaseMaterialError(
                    f"phase {phase_name!r} binds a sealed-manifest predecessor but no "
                    f"state was loaded for sample {sample_id!r}"
                )
            instruction = _appended(instruction, state)
        fill = state_fills.get(phase_name)
        if fill is not None:
            if state is None:
                raise PhaseMaterialError(
                    f"phase {phase_name!r} declares a state fill but bound no predecessor "
                    f"state for sample {sample_id!r}"
                )
            rendered = render_phase_state_fill(
                fill, state=state, sample_id=sample_id,
            )
            if not isinstance(rendered, str) or not rendered.strip():
                raise PhaseMaterialError(
                    f"phase {phase_name!r} state fill {spec.state_fill!r} rendered no text "
                    f"for sample {sample_id!r}"
                )
            instruction = _joined(instruction, rendered)

        response_format = response_format_by_phase.get(phase_name)
        if (spec.response_format_id is not None) != (response_format is not None):
            raise PhaseMaterialError(
                f"phase {phase_name!r} declares response_format_id "
                f"{spec.response_format_id!r} but "
                f"{'no' if response_format is None else 'a'} response format was "
                "resolved for it"
            )
        return PhaseMaterial(
            instruction=instruction,
            response_format=response_format,
            contact_id=f"{program_id}:{phase_name}:{sample_id}",
            purpose=spec.purpose,
        ).validate()

    return material_for_phase


def sealed_states_from_manifest(
    manifest_path: Path,
    *,
    expected_sha256: str,
    phase_name: str,
    producer_policy_id: str,
    sample_ids: Sequence[str],
    bundle_verifier=None,
) -> Mapping[str, AgentStateArtifact]:
    """Rebuild ``{sample_id: AgentStateArtifact}`` from an ALREADY SEALED
    bundle.

    This is how a later cell conditions on a sealed predecessor answer -- the
    SLURP slot stage on the sealed closed-list intent, say -- without
    re-flying the contact that produced it, and without inventing the
    provenance: the state's two source hashes are the sealed row's own
    ``request_sha256``/``response_text_sha256``, so the artifact is bound to
    the exact bytes the frozen core actually answered with.

    Fail-closed on a manifest whose bytes do not hash to ``expected_sha256``,
    on any requested sample the bundle does not carry, and on anything
    ``core.bundle.verify_bundle`` itself refuses.
    """

    from ..core.bundle.verify import verify_bundle  # noqa: PLC0415 (cycle guard)

    verifier = bundle_verifier if bundle_verifier is not None else verify_bundle
    manifest_path = Path(manifest_path)
    import hashlib  # noqa: PLC0415 (used only here)

    digest = hashlib.sha256()
    try:
        with manifest_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
    except OSError as error:
        raise PhaseMaterialError(
            f"cannot read sealed predecessor manifest {manifest_path}: {error}"
        ) from error
    measured = digest.hexdigest()
    if measured != expected_sha256:
        raise PhaseMaterialError(
            f"sealed predecessor manifest {manifest_path} hashes to {measured}, not the "
            f"configured {expected_sha256}"
        )

    verified = verifier(manifest_path)
    verified_manifest = getattr(verified, "manifest", None)
    artifact_result = (
        verified_manifest.get("artifact_result")
        if isinstance(verified_manifest, Mapping)
        else None
    )
    typed_hypothesis_manifest = (
        isinstance(verified_manifest, Mapping)
        and verified_manifest.get("result_kind") == "artifact"
        and isinstance(artifact_result, Mapping)
        and artifact_result.get("schema") == "saea-artifact-result-binding-v2"
        and artifact_result.get("role") == "slurp-intent-hypotheses"
    )
    by_sample: dict[str, Mapping[str, object]] = {}
    for row in verified.outputs_rows:
        sample_id = str(row.get("sample_id"))
        if sample_id in by_sample:
            raise PhaseMaterialError(
                f"sealed predecessor manifest {manifest_path} carries duplicate rows "
                f"for sample {sample_id!r}"
            )
        by_sample[sample_id] = row

    wanted = tuple(sample_ids)
    missing = sorted(set(wanted) - set(by_sample))
    if missing:
        raise PhaseMaterialError(
            f"sealed predecessor manifest {manifest_path} has no row for "
            f"{len(missing)} requested sample(s), e.g. {missing[:5]}"
        )
    states: dict[str, AgentStateArtifact] = {}
    for sample_id in wanted:
        row = by_sample[sample_id]
        content = row["text"]
        content_sha256 = row["response_text_sha256"]
        row_claims_hypotheses = row.get("artifact_role") == "slurp-intent-hypotheses"
        if row_claims_hypotheses != typed_hypothesis_manifest:
            raise PhaseMaterialError(
                "sealed hypothesis artifact row conflicts with its verified manifest binding"
            )
        if typed_hypothesis_manifest:
            content = row.get("artifact_content")
            content_sha256 = row.get("artifact_content_sha256")
            if not isinstance(content, str) or not isinstance(content_sha256, str):
                raise PhaseMaterialError(
                    "SLURP hypothesis artifact row lacks validated canonical content"
                )
        states[sample_id] = AgentStateArtifact(
            state_id=f"{phase_name}:{sample_id}",
            state_kind=f"phase:{phase_name}",
            content=str(content),
            source_query_state_sha256=str(row["request_sha256"]),
            source_response_sha256=str(content_sha256),
            producer_policy_id=producer_policy_id,
            cited_value_ids=(),
        ).validate()
    return states


def render_phase_envelope(
    system_text: str,
    instruction: str,
    *,
    prompt_order: str,
    packet_descriptor: Mapping[str, object],
    contact_id: str,
    agent_state: Sequence[Mapping[str, object]] = (),
    supply_blocks: Sequence[tuple[str, str]] = (),
) -> tuple[Mapping[str, object], ...]:
    """The EXACT transport message pair one phase contact crosses the wire as.

    Lifted verbatim from ``rails.probes.a2t_select_fill_agentloop.
    render_phase_request`` lines 781-828 (the ``feature`` part, the
    ``_agent_history`` call, ``_speech_history_texts``,
    ``_ordered_speech_feature_content`` with empty ``evidence_texts`` and
    empty ``knowledge_roles``, ``_assert_agent_history_suffix``, and the
    ``(system, user)`` tuple built from the result) rather than imported
    from it: that module is a probe, scheduled for disposal, and the owner
    rule forbids new code depending on ``rails/probes/``. A unit test pins
    byte equality against the probe's own function for the same inputs for
    as long as the probe exists.

    Nothing here talks to a server. This is the preflight/wire-check view of
    a contact: ``rails.core_client.FrozenCoreClient`` assembles the identical
    shape at request time from ``agent_state``/``agent_contact_id``/
    ``contact_instruction``.

    ``supply_blocks`` (E6) is the traced knowledge a SUPPLIED phase carries:
    ``(rendered_text, knowledge_role)`` pairs in the exact
    ``"[evidence <id>] <content>"`` form
    ``core.model.transport.LlamaServerTransport`` builds from a payload's
    ``supplied_evidence``, with ``knowledge_role`` ``"key"`` or ``"value"``.
    Empty by default, and the rendering is then byte-identical to what it
    always was, so a pinned prompt-fit receipt measured before this
    parameter existed still verifies. A caller that renders a supplied phase
    and does NOT pass its blocks is counting a prompt shorter than the one
    that goes on the wire.
    """

    from ..core.model import FrozenCoreError  # noqa: PLC0415 (cycle guard)
    from ..core.model.transport import (  # noqa: PLC0415 (cycle guard)
        _assert_agent_history_suffix,
        _ordered_speech_feature_content,
        _speech_history_texts,
    )
    from .core_client import _agent_history  # noqa: PLC0415 (cycle guard)

    if not isinstance(system_text, str) or not system_text:
        raise PhaseMaterialError("render_phase_envelope requires a system message")
    if not isinstance(packet_descriptor, Mapping) or set(packet_descriptor) != {
        "packet_id",
        "sha256",
    }:
        raise PhaseMaterialError(
            "packet_descriptor must carry exactly packet_id and sha256"
        )
    feature = {
        "type": "input_speech_features",
        "speech_features": {
            "packet_id": packet_descriptor["packet_id"],
            "sha256": packet_descriptor["sha256"],
            "role": "query",
        },
    }
    history = list(
        _agent_history(
            agent_state=tuple(agent_state),
            agent_contact_id=contact_id,
            contact_instruction=instruction,
        )
    )
    roles = tuple(role for _text, role in supply_blocks)
    if any(role not in {"key", "value"} for role in roles):
        raise PhaseMaterialError(
            "render_phase_envelope supply_blocks roles must be 'key' or 'value'"
        )
    try:
        state_texts = _speech_history_texts(history)
        ordered_content = _ordered_speech_feature_content(
            prompt_order=prompt_order,
            evidence_texts=[text for text, _role in supply_blocks],
            feature_parts=[feature],
            state_texts=state_texts,
            knowledge_roles=roles,
        )
        _assert_agent_history_suffix(
            prompt_order=prompt_order,
            content=ordered_content,
            state_texts=state_texts,
        )
    except FrozenCoreError as error:
        raise PhaseMaterialError(
            f"unsupported or invalid transport prompt order: {error}"
        ) from error
    return (
        {"role": "system", "content": system_text},
        {"role": "user", "content": ordered_content},
    )


def phase_material_receipt(
    specs: Mapping[str, PhaseMaterialSpec],
    static_text_by_phase: Mapping[str, str],
    response_format_by_phase: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    """A hashable identity record for what this run's phase material is --
    the spec plus the rendered instruction's length and sha256 plus the
    response format's sha256, per phase. Never the instruction text itself:
    it can be the whole 152-tool registry."""

    import hashlib  # noqa: PLC0415 (used only here)

    phases: list[Mapping[str, object]] = []
    for phase in sorted(specs):
        text = static_text_by_phase[phase]
        document = response_format_by_phase.get(phase)
        phases.append(
            {
                "spec": specs[phase].as_json(),
                "instruction_chars": len(text),
                "instruction_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "response_format_sha256": (
                    hashlib.sha256(
                        json.dumps(document, sort_keys=True, ensure_ascii=False).encode(
                            "utf-8"
                        )
                    ).hexdigest()
                    if document is not None
                    else None
                ),
            }
        )
    return {"schema": "saea-phase-material-v1", "phases": phases}


__all__ = [
    "PHASE_STATE_FILLS",
    "PREDECESSOR_BINDINGS",
    "PREDECESSOR_PREFIX",
    "PhaseMaterialError",
    "PhaseMaterialSpec",
    "build_material_for_phase",
    "load_phase_material_specs",
    "phase_material_receipt",
    "render_phase_envelope",
    "render_static_instruction",
    "resolve_response_formats",
    "sealed_states_from_manifest",
]
