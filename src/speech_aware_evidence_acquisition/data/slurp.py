"""SLURP slot-filling carrier loading (governed-metadata-scoped, fail-closed).

Layout facts (verified against the materialized asset, 2026-08-17): the
umbrella lock's own ``slurp`` entry names two DISTINCT trees under the
controlled data root -- ``local_subdir`` (``repos/slurp/scripts/audio``, the
raw upstream audio-only download, no metadata alongside it) and
``annotations.governed_copy`` (``datasets/slurp/metadata``, the governed,
hash-pinned copy of the SLURP GitHub repository's own JSON-lines label files
at the pinned commit, placed alongside a real+synthetic audio tree of its
own). This module resolves the SECOND tree -- always read from the lock,
never a hardcoded path (:func:`_governed_roots`) -- because the annotation
placement receipt (``datasets/slurp/annotation-receipt.json``) itself
reconciled every ``recordings[].file`` reference against exactly that
tree's ``slurp_real``/``slurp_synth`` subdirectories (100% match, 141,648 /
141,648 unique recording refs across all four splits); this loader mirrors
the SAME base the governance receipt already verified.

Split discipline (Stage-2A, this study's own CLAUDE.md research boundary --
"gold labels, reference transcripts, test annotations, and future turns must
never enter runtime; discovery and confirmatory stay isolated"): ``devel``
is this study's discovery surface. ``test`` is HELD OUT -- refused by
:func:`load_slurp_split` unless the caller passes ``allow_heldout=True``
explicitly (a deliberate, auditable opt-in a pre-registered confirmatory
read would set, never a default touched during discovery iteration).
``train``/``train_synthetic`` are available for roster/knowledge-base
construction only (:func:`load_slurp_ontology` below), never as a
discovery/dev probe target through this function. ``train_synthetic`` is
additionally TTS-synthesized audio, not real speech -- refused unless
``allow_synthetic=True`` (real audio only by default, per this mission's own
instruction).

Entity fillers -- a metadata-field surprise against the task brief's "type +
filler spans" phrasing: the governed jsonl's own ``entities[]`` carries only
``{"span": [token_id, ...], "type": ...}``, NOT filler text directly. The
real release requires joining ``tokens[]`` surfaces at the listed ids to
recover filler text (every observed ``span`` in the governed devel.jsonl is
a contiguous, ascending run of token ids, verified against all 2,033
records). :func:`_entity_filler` does exactly that join, lowercased, exactly
matching the official SLURP eval script's own gold-side join
(``reproduction.slurp_scoring`` module docstring) -- so every downstream
consumer reads a plain ``reproduction.slurp_scoring.SlotEntity(type,
filler)`` pair, never a raw span.

A second metadata-field surprise: the governed jsonl's own ``intent`` field
is NOT always ``f"{scenario}_{action}"`` (verified: 30 of 2,033 devel
records diverge, e.g. ``scenario="play", action="music", intent="music"``
rather than ``"play_music"``). The task brief's own parenthetical --
"intent (scenario_action)" -- defines intent AS the scenario/action pair;
:attr:`SlurpRecord.intent` below is therefore the COMPUTED
``f"{scenario}_{action}"`` string, not the raw (occasionally inconsistent)
jsonl field, which this module does not even read.

Gold/runtime separation: :func:`load_slurp_split` returns
:class:`SlurpRecord` -- carrying ``scenario``/``action``/``intent``/
``entities`` (the SLU gold layer) alongside media identity, deliberately
WITHOUT the raw ``sentence``/``sentence_annotation`` text (not needed by
either the five ``TaskAdapter`` methods or by scoring -- SLURP scoring is a
scenario_action match plus per-entity type+filler comparison, never a
text-level sentence compare). Every field this module returns is
loader-legal to CARRY (this module is not itself a runtime request path);
``rails.adapters.slurp.SlurpAdapter.assemble_prompt`` is the boundary that
must never render these fields into prompt text, and is the boundary this
mission's own gold-leak test checks.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from ..reproduction.slurp_scoring import SlotEntity
from .loader import LoaderError
from .lock import AssetResolutionError, lock_entry

SLURP_LOCK_KEY = "slurp"

_SPLIT_FILES: Mapping[str, str] = {
    "devel": "devel.jsonl",
    "test": "test.jsonl",
    "train": "train.jsonl",
    "train_synthetic": "train_synthetic.jsonl",
}
_HELD_OUT_SPLITS = frozenset({"test"})
_SYNTHETIC_SPLITS = frozenset({"train_synthetic"})
_AUDIO_SUBDIR_FOR_SPLIT: Mapping[str, str] = {
    "devel": "slurp_real",
    "test": "slurp_real",
    "train": "slurp_real",
    "train_synthetic": "slurp_synth",
}
# The task brief's own "roster/KB construction only" split scope --
# load_slurp_ontology mines from this pool, text-only (no audio touched;
# distinct from actually RUNNING train_synthetic samples through the rails
# runner, which still requires allow_synthetic=True). ``train_synthetic`` is
# EXCLUDED by default -- see load_slurp_ontology's own docstring for the
# 64.8% devel-overlap finding that makes it ceiling-tier, not legal, for any
# roster a devel-split probe consumes.
_ROSTER_SPLITS_LEGAL: tuple[str, ...] = ("train",)
_ROSTER_SPLITS_WITH_SYNTHETIC: tuple[str, ...] = ("train", "train_synthetic")
_ONTOLOGY_EXAMPLES_PER_TYPE = 5


@dataclass(frozen=True)
class SlurpRecord:
    """One (SLURP sentence, recording) pair's loader-legal identity + SLU
    gold layer -- the shape ``rails.adapters.slurp.SlurpSample`` hydrates
    from directly (module docstring)."""

    sample_id: str
    utterance_id: str
    split: str
    media_relpath: str
    audio_seconds: float
    scenario: str
    action: str
    intent: str
    entities: tuple[SlotEntity, ...]


@dataclass(frozen=True)
class SlurpOntology:
    """Deterministic user-ontology roster (module docstring, entity clause's
    own "user-ontology matching" probe scope) -- unique scenario/action
    names and, per entity type, up to :data:`_ONTOLOGY_EXAMPLES_PER_TYPE`
    distinct example filler values, all sorted for determinism."""

    scenarios: tuple[str, ...]
    actions: tuple[str, ...]
    entity_types: Mapping[str, tuple[str, ...]]


def _governed_roots(lock: Mapping[str, object], root: Path) -> tuple[str, Path, Path]:
    """(audio-root path relative to ``root``, audio-root absolute
    ``Path``, metadata absolute ``Path``) -- both trees resolved from the
    lock's own ``slurp`` entry (module docstring), never a hardcoded path."""

    entry = lock_entry(lock, SLURP_LOCK_KEY)
    annotations = entry.get("annotations")
    if not isinstance(annotations, Mapping):
        raise AssetResolutionError(f"asset {SLURP_LOCK_KEY!r} lacks an annotations block in the lock")
    governed_copy = annotations.get("governed_copy")
    if not isinstance(governed_copy, str) or not governed_copy.endswith("/metadata"):
        raise AssetResolutionError(
            f"asset {SLURP_LOCK_KEY!r} annotations.governed_copy must be a '.../metadata' path, "
            f"got {governed_copy!r}"
        )
    audio_root_relpath = governed_copy[: -len("/metadata")]
    audio_root = Path(root) / audio_root_relpath
    metadata_dir = Path(root) / governed_copy
    if not metadata_dir.is_dir():
        raise AssetResolutionError(f"SLURP governed metadata directory missing: {metadata_dir}")
    if not audio_root.is_dir():
        raise AssetResolutionError(f"SLURP audio root missing: {audio_root}")
    return audio_root_relpath, audio_root, metadata_dir


def _entity_filler(tokens_by_id: Mapping[int, str], span: object, context: str) -> str:
    """Join ``tokens[]`` surfaces at the ids in ``span``, lowercased --
    EXACTLY the official SLURP eval script's own gold-side join (module
    docstring)."""

    if not isinstance(span, list) or not span or any(isinstance(item, bool) for item in span):
        raise LoaderError(f"{context}: entity span must be a non-empty list of token ids, got {span!r}")
    surfaces: list[str] = []
    for token_id in span:
        if not isinstance(token_id, int):
            raise LoaderError(f"{context}: entity span token id must be an int, got {token_id!r}")
        surface = tokens_by_id.get(token_id)
        if surface is None:
            raise LoaderError(f"{context}: entity span references unknown token id {token_id}")
        surfaces.append(surface.lower())
    return " ".join(surfaces)


def _entity_type(entity: object, context: str) -> str:
    if not isinstance(entity, Mapping):
        raise LoaderError(f"{context}: entity entry must be an object")
    entity_type = entity.get("type")
    if not isinstance(entity_type, str) or not entity_type:
        raise LoaderError(f"{context}: entity type must be a non-empty string, got {entity_type!r}")
    return entity_type


def _tokens_by_id(tokens: object, context: str) -> dict[int, str]:
    if not isinstance(tokens, list):
        raise LoaderError(f"{context}: tokens must be a list")
    by_id: dict[int, str] = {}
    for token in tokens:
        if not isinstance(token, Mapping):
            raise LoaderError(f"{context}: token entry must be an object")
        token_id = token.get("id")
        surface = token.get("surface")
        if isinstance(token_id, bool) or not isinstance(token_id, int) or not isinstance(surface, str):
            raise LoaderError(f"{context}: token entry malformed: {token!r}")
        by_id[token_id] = surface
    return by_id


def _validate_recording_filename(filename: object, context: str) -> str:
    if not isinstance(filename, str) or not filename:
        raise LoaderError(f"{context}: recording file name must be a non-empty string")
    if "/" in filename or "\\" in filename or filename in (".", ".."):
        raise LoaderError(f"{context}: recording file name {filename!r} is not a plain file name")
    if not filename.endswith(".flac"):
        raise LoaderError(f"{context}: recording file name {filename!r} is not a .flac file")
    return filename


def _audio_seconds(path: Path, context: str) -> float:
    if not path.is_file():
        raise LoaderError(f"{context}: media missing: {path}")
    import soundfile  # deferred: heavy import stays function-local (repo convention)

    try:
        info = soundfile.info(str(path))
    except Exception as error:  # soundfile raises its own libsndfile error types
        raise LoaderError(f"{context}: cannot read flac header of {path}: {error}") from error
    if not info.samplerate:
        raise LoaderError(f"{context}: flac header of {path} reports zero sample rate")
    duration = float(info.frames) / float(info.samplerate)
    if duration <= 0.0:
        raise LoaderError(f"{context}: flac header of {path} reports non-positive duration")
    return duration


def _parse_record(
    raw: Mapping[str, object],
    split_id: str,
    audio_dir_relpath: str,
    audio_dir: Path,
    line_no: int,
) -> list[SlurpRecord]:
    context = f"SLURP {split_id}.jsonl line {line_no}"
    slurp_id = raw.get("slurp_id")
    if isinstance(slurp_id, bool) or not isinstance(slurp_id, int):
        raise LoaderError(f"{context}: slurp_id must be an int, got {slurp_id!r}")
    scenario = raw.get("scenario")
    action = raw.get("action")
    if not isinstance(scenario, str) or not scenario:
        raise LoaderError(f"{context}: scenario must be a non-empty string")
    if not isinstance(action, str) or not action:
        raise LoaderError(f"{context}: action must be a non-empty string")
    tokens_by_id = _tokens_by_id(raw.get("tokens"), context)
    raw_entities = raw.get("entities")
    if not isinstance(raw_entities, list):
        raise LoaderError(f"{context}: entities must be a list")
    entities = tuple(
        SlotEntity(
            type=_entity_type(entity, context),
            filler=_entity_filler(tokens_by_id, entity.get("span") if isinstance(entity, Mapping) else None, context),
        )
        for entity in raw_entities
    )
    recordings = raw.get("recordings")
    if not isinstance(recordings, list) or not recordings:
        raise LoaderError(f"{context}: recordings must be a non-empty list")
    intent = f"{scenario}_{action}"
    records: list[SlurpRecord] = []
    seen_files: set[str] = set()
    for recording in recordings:
        if not isinstance(recording, Mapping):
            raise LoaderError(f"{context}: recording entry must be an object")
        filename = _validate_recording_filename(recording.get("file"), context)
        if filename in seen_files:
            raise LoaderError(f"{context}: duplicate recording file {filename!r}")
        seen_files.add(filename)
        media_path = audio_dir / filename
        records.append(
            SlurpRecord(
                sample_id=f"slurp:{split_id}:{slurp_id:06d}:{filename[: -len('.flac')]}",
                utterance_id=str(slurp_id),
                split=split_id,
                media_relpath=f"{audio_dir_relpath}/{filename}",
                audio_seconds=_audio_seconds(media_path, context),
                scenario=scenario,
                action=action,
                intent=intent,
                entities=entities,
            )
        )
    return records


def _read_jsonl(path: Path) -> list[Mapping[str, object]]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise LoaderError(f"cannot read SLURP split metadata {path}: {error}") from error
    documents: list[Mapping[str, object]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            raw = json.loads(stripped)
        except json.JSONDecodeError as error:
            raise LoaderError(f"{path} line {line_no}: invalid JSON: {error}") from error
        if not isinstance(raw, Mapping):
            raise LoaderError(f"{path} line {line_no} must be a JSON object")
        documents.append(raw)
    return documents


def load_slurp_split(
    lock: Mapping[str, object],
    root: Path,
    split_id: str,
    *,
    allow_heldout: bool = False,
    allow_synthetic: bool = False,
) -> list[SlurpRecord]:
    """Every SLURP (sentence, recording) sample in ``split_id``, sorted by
    sample id, with media re-verified against the flac headers (module
    docstring: split discipline + entity-filler derivation)."""

    if split_id not in _SPLIT_FILES:
        raise LoaderError(f"unknown SLURP split {split_id!r}; known splits are {sorted(_SPLIT_FILES)}")
    if split_id in _HELD_OUT_SPLITS and not allow_heldout:
        raise LoaderError(
            f"SLURP split {split_id!r} is HELD OUT (Stage-2A split discipline: this study's own "
            "CLAUDE.md research boundary -- gold labels, reference transcripts and test annotations "
            "must never enter runtime; discovery and confirmatory stay isolated); pass "
            "allow_heldout=True explicitly for a pre-registered confirmatory read, never during "
            "discovery iteration"
        )
    if split_id in _SYNTHETIC_SPLITS and not allow_synthetic:
        raise LoaderError(
            f"SLURP split {split_id!r} is TTS-synthesized audio, not real speech; pass "
            "allow_synthetic=True explicitly to opt in (real audio only by default)"
        )
    audio_root_relpath, audio_root, metadata_dir = _governed_roots(lock, root)
    subdir_name = _AUDIO_SUBDIR_FOR_SPLIT[split_id]
    audio_dir_relpath = f"{audio_root_relpath}/{subdir_name}"
    audio_dir = audio_root / subdir_name
    if not audio_dir.is_dir():
        raise LoaderError(f"SLURP audio directory missing: {audio_dir}")
    metadata_path = metadata_dir / _SPLIT_FILES[split_id]
    if not metadata_path.is_file():
        raise LoaderError(f"SLURP split metadata file missing: {metadata_path}")

    records: list[SlurpRecord] = []
    seen_ids: set[str] = set()
    for line_no, raw in enumerate(_read_jsonl(metadata_path), start=1):
        for record in _parse_record(raw, split_id, audio_dir_relpath, audio_dir, line_no):
            if record.sample_id in seen_ids:
                raise LoaderError(f"duplicate SLURP sample id {record.sample_id!r}")
            seen_ids.add(record.sample_id)
            records.append(record)
    if not records:
        raise LoaderError(f"SLURP split {split_id!r} resolved to zero samples")
    records.sort(key=lambda record: record.sample_id)
    return records


def load_slurp_ontology(
    lock: Mapping[str, object], root: Path, *, include_synthetic: bool = False
) -> SlurpOntology:
    """Deterministic user-ontology roster mined from ``train`` (module
    docstring: the task brief's own "roster/KB construction only" split
    scope) -- text-only, no audio file is opened and no per-recording
    existence check runs (this is NOT :func:`load_slurp_split`).

    ``include_synthetic`` (default ``False``, 2026-08-17 finding): mining
    ``train_synthetic.jsonl`` alongside ``train.jsonl`` was the PRIOR
    unconditional behaviour, but measurement on the real governed corpus
    found 1,317 of 2,033 ``devel.jsonl`` ``slurp_id``s (64.8%) recur
    VERBATIM in ``train_synthetic.jsonl`` -- identical sentence AND
    identical entity set. A roster mined from ``train_synthetic`` therefore
    places a majority of the devel evaluation surface's own gold entity
    fillers directly into the "legal-tier" roster text: CEILING tier by the
    either-field doctrine (``core.legality`` module docstring), not legal,
    for any probe that reads the ``devel`` split. ``train.jsonl`` alone has
    ZERO overlap with ``devel`` (verified on the real corpus,
    ``configs/probes/g0-binding/pslu-rosters-train-only.json``'s own
    ``train_synthetic_refused`` block) and is the only legal-tier roster
    source for a devel-split read. Passing ``include_synthetic=True`` is an
    explicit, auditable opt-in for a caller that has already accepted
    ceiling-tier provenance (e.g. building an oracle/ceiling companion arm
    on purpose) -- never the default for a legal-tier read."""

    _, _, metadata_dir = _governed_roots(lock, root)
    scenarios: set[str] = set()
    actions: set[str] = set()
    fillers_by_type: dict[str, set[str]] = {}
    roster_splits = _ROSTER_SPLITS_WITH_SYNTHETIC if include_synthetic else _ROSTER_SPLITS_LEGAL
    for split_id in roster_splits:
        metadata_path = metadata_dir / _SPLIT_FILES[split_id]
        if not metadata_path.is_file():
            raise LoaderError(f"SLURP split metadata file missing: {metadata_path}")
        for line_no, raw in enumerate(_read_jsonl(metadata_path), start=1):
            context = f"SLURP {split_id}.jsonl line {line_no}"
            scenario = raw.get("scenario")
            action = raw.get("action")
            if isinstance(scenario, str) and scenario:
                scenarios.add(scenario)
            if isinstance(action, str) and action:
                actions.add(action)
            try:
                tokens_by_id = _tokens_by_id(raw.get("tokens"), context)
            except LoaderError:
                continue
            raw_entities = raw.get("entities")
            if not isinstance(raw_entities, list):
                continue
            for entity in raw_entities:
                if not isinstance(entity, Mapping):
                    continue
                entity_type = entity.get("type")
                if not isinstance(entity_type, str) or not entity_type:
                    continue
                try:
                    filler = _entity_filler(tokens_by_id, entity.get("span"), context)
                except LoaderError:
                    continue
                fillers_by_type.setdefault(entity_type, set()).add(filler)
    entity_types = {
        entity_type: tuple(sorted(fillers)[:_ONTOLOGY_EXAMPLES_PER_TYPE])
        for entity_type, fillers in fillers_by_type.items()
    }
    return SlurpOntology(
        scenarios=tuple(sorted(scenarios)),
        actions=tuple(sorted(actions)),
        entity_types=entity_types,
    )


def render_slurp_ontology(ontology: SlurpOntology) -> str:
    """Deterministic single-line JSON rendering of ``ontology`` -- the
    ``{tool_schemas}``-equivalent fixed text ``SlurpAdapter.build_query``
    returns (mirrors ``data.audio2tool.render_tool_schemas``'s own
    one-canonical-document convention)."""

    document = {
        "scenarios": list(ontology.scenarios),
        "actions": list(ontology.actions),
        "entity_types": {
            entity_type: list(fillers) for entity_type, fillers in sorted(ontology.entity_types.items())
        },
    }
    return json.dumps(document, ensure_ascii=False, sort_keys=True)


__all__ = [
    "SLURP_LOCK_KEY",
    "SlurpOntology",
    "SlurpRecord",
    "load_slurp_ontology",
    "load_slurp_split",
    "render_slurp_ontology",
]
