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

import hashlib
import json
import math
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Callable, Mapping, Sequence

from ..reproduction.slurp_scoring import SlotEntity, parse_slu_response
from .loader import LoaderError, SampleRef
from .lock import REPO_ROOT, AssetResolutionError, lock_entry

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
    distinct example filler values, all sorted for determinism.

    ``actions_by_scenario`` (added 2026-09-05) carries the PAIRING the three
    flat rosters above throw away. ``scenarios`` and ``actions`` are two
    independent sets, so a consumer reading them alone sees the 18 x 46 =
    828 implied cross-product combinations when only 60 (scenario, action)
    pairs actually occur in ``train``. That gap is what
    :func:`render_slurp_label_inventory` closes and what the 2026-09-04
    scoring-alignment audit named as the last unmatched element of the
    published prompt-only SLURP protocol (He & Garner arXiv:2305.13512 list
    the intent inventory IN the prompt). Defaulted to an empty mapping so
    every caller that constructs a ``SlurpOntology`` positionally keeps
    working unchanged.
    """

    scenarios: tuple[str, ...]
    actions: tuple[str, ...]
    entity_types: Mapping[str, tuple[str, ...]]
    actions_by_scenario: Mapping[str, tuple[str, ...]] = MappingProxyType({})

    @property
    def intents(self) -> tuple[str, ...]:
        """The observed ``f"{scenario}_{action}"`` vocabulary, sorted -- the
        SAME spelling :func:`_parse_record` gives ``SlurpRecord.intent``, so
        an inventory rendered from here and a gold label compare directly."""

        return tuple(
            sorted(
                f"{scenario}_{action}"
                for scenario, actions in self.actions_by_scenario.items()
                for action in actions
            )
        )


@dataclass(frozen=True)
class SlurpTrainRecording:
    """One real train recording with the speaker identity needed for
    query/key isolation during model-free split binding."""

    sample_id: str
    media_relpath: str
    speaker_id: str


@dataclass(frozen=True)
class SlurpTrainMaterial:
    """One train utterance's key-card text and natural recordings.

    This type is for offline binding only. Query inference continues to use
    :class:`SlurpRecord`, which deliberately carries no reference sentence.

    ``entities`` carries the same ``{type, filler}`` gold slots
    :class:`SlurpRecord` does, derived through the same
    :func:`_entity_filler` join the official ``evaluate.py`` gold side uses,
    so a TRAIN filler and a DEV gold filler compare byte-for-byte without a
    second normalizer. ``entity_types`` stays the deduplicated type roster it
    always was.
    """

    utterance_id: str
    scenario: str
    action: str
    sentence: str
    recordings: tuple[SlurpTrainRecording, ...]
    entity_types: tuple[str, ...] = ()
    entities: tuple[SlotEntity, ...] = ()


@dataclass(frozen=True)
class SlurpEngineeringSample:
    """One label-free, byte-bound sample from an engineering gate view."""

    sample_id: str
    media_relpath: str
    audio_sha256: str
    audio_seconds: float
    sample_rate_hz: int
    packet_id: str


@dataclass(frozen=True)
class SlurpEngineeringGate:
    """The verified label-free ENG-GATE8 view shared by rails and core."""

    split_identity_hash: str
    runtime_view_sha256: str
    # ``None`` when the view's media is already inside the immutable E0 D1
    # closure and needs no additive successor -- see
    # ``_RUNTIME_VIEW_SPLIT_ROLES``/the supplement nullability comment in
    # ``load_slurp_engineering_gate``.
    d1_media_supplement: str | None
    d1_media_supplement_sha256: str | None
    samples: tuple[SlurpEngineeringSample, ...]


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


def _audio_seconds(
    path: Path, context: str, cache: Mapping[Path, float] | None = None
) -> float:
    """One recording's duration from its flac header.

    ``cache`` is an already-resolved ``{path: seconds}`` mapping (see
    :func:`_prefetch_audio_seconds`). A hit returns the same float this
    function would have computed; a miss falls through to the real probe, so
    a caller that passes a partial cache -- which the prefetch deliberately
    is -- gets identical values and identical refusals.
    """

    if cache is not None:
        cached = cache.get(path)
        if cached is not None:
            return cached
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


def _audio_probe_workers(requested: object) -> int:
    """How many threads probe flac headers, decided in ONE place.

    Deferred import on purpose: ``analysis.parallel`` is stdlib-only, but this
    loader's module-level import graph stays exactly as light as it was.
    """

    from ..analysis.parallel import resolve_workers  # noqa: PLC0415

    return resolve_workers(requested)


def _prefetch_audio_seconds(
    rows: Sequence[Mapping[str, object]], audio_dir: Path, *, workers: int
) -> dict[Path, float]:
    """Resolve every recording's flac-header duration concurrently, best-effort.

    BEST-EFFORT is the whole safety argument: a probe that raises is simply
    left out of the returned mapping, so the serial :func:`_parse_record` loop
    still reaches that file, still calls :func:`_audio_seconds` on it, and
    still raises the same :class:`LoaderError` with the same message at the
    same point in the same order. Nothing here validates anything; it only
    pays the filesystem latency ahead of time, in parallel.

    Threads rather than processes: both ``Path.is_file`` and
    ``soundfile.info`` release the GIL for the duration of the syscall, so a
    thread pool is the right tool and carries none of a fork's hazards. The
    durations are a pure function of the file, so the mapping does not depend
    on how many threads resolved it.
    """

    candidates: list[Path] = []
    seen: set[Path] = set()
    for raw in rows:
        recordings = raw.get("recordings")
        if not isinstance(recordings, list):
            continue
        for recording in recordings:
            if not isinstance(recording, Mapping):
                continue
            try:
                # The loader's OWN name rule, reused rather than restated: a
                # name the parse would refuse is never probed here either, so
                # the prefetch cannot read outside the governed audio directory.
                filename = _validate_recording_filename(recording.get("file"), "prefetch")
            except LoaderError:
                continue
            path = audio_dir / filename
            if path in seen:
                continue
            seen.add(path)
            candidates.append(path)
    if len(candidates) < 2 or workers <= 1:
        return {}

    import soundfile  # noqa: F401, PLC0415 -- load it BEFORE any thread needs it

    def probe(path: Path) -> float | None:
        try:
            return _audio_seconds(path, "prefetch")
        except LoaderError:
            return None

    with ThreadPoolExecutor(
        max_workers=min(workers, len(candidates)),
        thread_name_prefix="saea-slurp-flac",
    ) as pool:
        measured = tuple(pool.map(probe, candidates))
    return {
        path: seconds
        for path, seconds in zip(candidates, measured, strict=True)
        if seconds is not None
    }


def _parse_record(
    raw: Mapping[str, object],
    split_id: str,
    audio_dir_relpath: str,
    audio_dir: Path,
    line_no: int,
    durations: Mapping[Path, float] | None = None,
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
                audio_seconds=_audio_seconds(media_path, context, durations),
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


def _slurp_speaker_index(metadata_dir: Path) -> Mapping[str, str]:
    path = metadata_dir / "metadata.json"
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise LoaderError(f"cannot read SLURP speaker metadata {path}: {error}") from error
    if not isinstance(document, Mapping):
        raise LoaderError(f"SLURP speaker metadata {path} must be an object")
    speakers: dict[str, str] = {}
    for entry in document.values():
        if not isinstance(entry, Mapping):
            continue
        recordings = entry.get("recordings")
        if not isinstance(recordings, Mapping):
            continue
        for filename, recording in recordings.items():
            if not isinstance(filename, str) or not isinstance(recording, Mapping):
                continue
            speaker_id = recording.get("usrid")
            if not isinstance(speaker_id, str) or not speaker_id:
                continue
            previous = speakers.get(filename)
            if previous is not None and previous != speaker_id:
                raise LoaderError(
                    f"SLURP recording {filename!r} has conflicting speaker identities"
                )
            speakers[filename] = speaker_id
    if not speakers:
        raise LoaderError(f"SLURP speaker metadata {path} resolved no speaker identity records")
    return speakers


def _missing_media_paths(
    paths: Sequence[Path],
    *,
    workers: int = 16,
    probe: Callable[[Path], bool] = Path.is_file,
) -> tuple[Path, ...]:
    """Return missing paths in input order using bounded parallel metadata I/O.

    File existence checks are independent and release the GIL while waiting on
    the filesystem. A small bounded pool therefore removes the avoidable
    serialization cost of validating SLURP material across filesystem mounts
    without changing selection order or failure semantics.
    """

    if isinstance(workers, bool) or not isinstance(workers, int) or not 1 <= workers <= 64:
        raise ValueError("media validation workers must be an integer in [1, 64]")
    if not paths:
        return ()
    worker_count = min(workers, len(paths))
    if worker_count == 1:
        exists = tuple(probe(path) for path in paths)
    else:
        with ThreadPoolExecutor(
            max_workers=worker_count,
            thread_name_prefix="saea-slurp-media",
        ) as pool:
            exists = tuple(pool.map(probe, paths))
    return tuple(path for path, is_present in zip(paths, exists, strict=True) if not is_present)


def _canonical_sha256(document: Mapping[str, object]) -> str:
    payload = json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _probe_engineering_media(path: Path) -> tuple[str, float, int]:
    import soundfile  # deferred: keep package import light

    digest = hashlib.sha256()
    try:
        with Path(path).open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
        info = soundfile.info(str(path))
    except Exception as error:
        raise LoaderError(f"cannot measure engineering speech media {path}: {error}") from error
    if info.frames <= 0 or info.samplerate <= 0:
        raise LoaderError(f"engineering speech media {path} has invalid header facts")
    return digest.hexdigest(), float(info.frames / info.samplerate), int(info.samplerate)


# A speech-native runtime view may name either Stage-2 split role. Mirrors
# ``contracts.plan.STAGE2_SPLIT_ROLES`` and
# ``reproduction.probe_split._STAGE2_SPLIT_ROLES`` (duplicated as a literal
# rather than imported: ``contracts`` imports ``data.carriers``, so importing
# it back here would close a package cycle). ``dev`` was admitted for the
# DEV-100/500/1000 optimization ladder (owner ruling
# ``docs/readiness/2026-08-23-knowledge-plane-baseline-rulings.md`` section
# 2.2); ``confirmatory`` stays refused here exactly as before -- a runtime
# view can never name a confirmatory split.
#
# ``final-report`` (owner decisions 99 of 2026-09-22 and 107 of 2026-09-23;
# one-shot read protocol section 6.3) is admitted here too, because the ONE
# complete SLURP test-split read and its label-free preparation passes bind a
# runtime view exactly as every development roster does. Naming the role in a
# runtime view is a STATEMENT, never an authority: a speech-native runtime view
# carries media identity only -- relpath, bytes, sha256, header duration, sample
# rate, packet id -- and no annotation, so admitting the role here cannot make a
# gold field reachable. The authority lives entirely in
# ``contracts.plan.require_owner_split_allowance``, which refuses every
# ``final-report`` ExecutionPlan until the committed owner-allowance receipt
# says ``authorised``.
_RUNTIME_VIEW_SPLIT_ROLES = frozenset({"discovery", "dev", "final-report"})


def load_slurp_engineering_gate(
    path: Path,
    *,
    data_root: Path,
    expected_count: int = 8,
    expected_split_name: str = "ENG-GATE8",
    workers: int = 8,
    media_probe: Callable[[Path], tuple[str, float, int]] = _probe_engineering_media,
) -> SlurpEngineeringGate:
    """Verify one exact label-free speech-native view and its live media bytes.

    This is the single parser used by both the P-SLU rail and the generic
    experiment driver's SLURP carrier. It reads no SLURP annotation file and
    rejects any item field beyond the explicitly safe media identity set.
    """

    if (
        isinstance(expected_count, bool)
        or not isinstance(expected_count, int)
        or expected_count <= 0
    ):
        raise LoaderError("engineering gate expected_count must be positive")
    if isinstance(workers, bool) or not isinstance(workers, int) or not 1 <= workers <= 64:
        raise LoaderError("engineering gate workers must be an integer in [1, 64]")
    if not isinstance(expected_split_name, str) or not expected_split_name:
        raise LoaderError("speech-native runtime view expected_split_name must be non-empty")
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise LoaderError(f"cannot read speech-native engineering gate {path}: {error}") from error
    required = {
        "schema",
        "study",
        "status",
        "carrier_lock_key",
        "split_name",
        "split_role",
        "seed",
        "split_identity_hash",
        "source_binding_sha256",
        "d1_media_supplement",
        "d1_media_supplement_sha256",
        "d1_manifest_sha256",
        "count",
        "audio_seconds_total",
        "items",
        "runtime_view_sha256",
    }
    if not isinstance(document, Mapping) or set(document) != required:
        raise LoaderError(
            f"speech-native engineering gate must carry exact keys {sorted(required)}"
        )
    allowed_schemas = {"saea-speech-native-runtime-view-v1"}
    if expected_split_name == "ENG-GATE8":
        allowed_schemas.add("saea-speech-native-engineering-gate-view-v1")
    if document["schema"] not in allowed_schemas:
        raise LoaderError("speech-native engineering gate schema mismatch")
    if (
        document["study"] != "speech-aware-evidence-acquisition"
        or document["carrier_lock_key"] != SLURP_LOCK_KEY
        or document["split_name"] != expected_split_name
        or document["split_role"] not in _RUNTIME_VIEW_SPLIT_ROLES
    ):
        raise LoaderError("speech-native engineering gate identity mismatch")
    items = document["items"]
    if not isinstance(items, list) or len(items) != expected_count or document["count"] != len(items):
        raise LoaderError(
            f"speech-native engineering gate must carry exactly {expected_count} items"
        )
    item_keys = {
        "sample_id",
        "media_relpath",
        "audio_sha256",
        "audio_seconds",
        "sample_rate_hz",
        "packet_id",
    }
    if any(not isinstance(item, Mapping) or set(item) != item_keys for item in items):
        raise LoaderError(
            "speech-native engineering gate items must be label-free and carry "
            f"exact keys {sorted(item_keys)}"
        )
    unsigned = {key: value for key, value in document.items() if key != "runtime_view_sha256"}
    if document["runtime_view_sha256"] != _canonical_sha256(unsigned):
        raise LoaderError("speech-native engineering gate runtime view SHA-256 mismatch")
    for field in (
        "split_identity_hash",
        "source_binding_sha256",
        "runtime_view_sha256",
    ):
        value = document[field]
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(ch not in "0123456789abcdef" for ch in value)
        ):
            raise LoaderError(f"speech-native engineering gate {field} is malformed")

    # A D1 media SUPPLEMENT is an ADDITIVE successor for a carrier slice that
    # sits OUTSIDE the immutable E0 D1 closure, and
    # ``contracts.gate_media_identity._d1_media_supplement_records`` refuses --
    # correctly -- any supplement entry that duplicates a base D1 sample. The
    # DEV ladder is drawn from SLURP devel, and base D1 already records every
    # one of the 8,690 devel recordings, so a DEV runtime view has nothing to
    # supplement: its three supplement fields are all null and the gate reads
    # media identity straight from D1. All-or-nothing, exactly as
    # ``core.config._d1_media_supplement_pair`` already requires; a partially
    # null triple is a defect, not a shorthand.
    supplement_fields = (
        document["d1_media_supplement"],
        document["d1_media_supplement_sha256"],
        document["d1_manifest_sha256"],
    )
    if all(value is None for value in supplement_fields):
        supplement_path = None
    else:
        for field in ("d1_media_supplement_sha256", "d1_manifest_sha256"):
            value = document[field]
            if (
                not isinstance(value, str)
                or len(value) != 64
                or any(ch not in "0123456789abcdef" for ch in value)
            ):
                raise LoaderError(f"speech-native engineering gate {field} is malformed")
        supplement_path = document["d1_media_supplement"]
        if (
            not isinstance(supplement_path, str)
            or not supplement_path
            or "\\" in supplement_path
            or Path(supplement_path).is_absolute()
            or any(part in ("", ".", "..") for part in Path(supplement_path).parts)
        ):
            raise LoaderError("speech-native engineering gate D1 supplement path is unsafe")

    root = Path(data_root).resolve(strict=True)
    prepared: list[tuple[Mapping[str, object], Path]] = []
    sample_ids: set[str] = set()
    packet_ids: set[str] = set()
    for item in items:
        sample_id = item["sample_id"]
        packet_id = item["packet_id"]
        media_relpath = item["media_relpath"]
        if (
            not isinstance(sample_id, str)
            or sample_id in sample_ids
            or not sample_id.startswith("slurp:")
            or not isinstance(packet_id, str)
            or packet_id in packet_ids
            or packet_id != sample_id.replace(":", "/")
            or not isinstance(media_relpath, str)
            or "\\" in media_relpath
        ):
            raise LoaderError("engineering gate sample/packet/media identity is malformed")
        sample_ids.add(sample_id)
        packet_ids.add(packet_id)
        relative = Path(media_relpath)
        if relative.is_absolute() or any(part in ("", ".", "..") for part in relative.parts):
            raise LoaderError("engineering gate media path is unsafe")
        try:
            media_path = (root / relative).resolve(strict=True)
        except OSError as error:
            raise LoaderError(
                f"engineering gate media {media_relpath!r} is unavailable: {error}"
            ) from error
        if not media_path.is_file() or not media_path.is_relative_to(root):
            raise LoaderError("engineering gate media escapes the governed data root")
        prepared.append((item, media_path))
    worker_count = min(workers, len(prepared))
    if worker_count == 1:
        measured = tuple(media_probe(media_path) for _item, media_path in prepared)
    else:
        with ThreadPoolExecutor(
            max_workers=worker_count,
            thread_name_prefix="saea-eng-gate-media",
        ) as pool:
            measured = tuple(pool.map(media_probe, (entry[1] for entry in prepared)))
    samples: list[SlurpEngineeringSample] = []
    for (item, _media_path), facts in zip(prepared, measured, strict=True):
        actual_sha256, actual_seconds, actual_rate = facts
        expected_seconds = item["audio_seconds"]
        expected_rate = item["sample_rate_hz"]
        if actual_sha256 != item["audio_sha256"]:
            raise LoaderError(f"engineering gate media hash drift for {item['sample_id']!r}")
        if (
            isinstance(expected_seconds, bool)
            or not isinstance(expected_seconds, (int, float))
            or not math.isfinite(expected_seconds)
            or abs(float(expected_seconds) - float(actual_seconds)) > 1e-6
            or isinstance(expected_rate, bool)
            or not isinstance(expected_rate, int)
            or expected_rate != actual_rate
        ):
            raise LoaderError(
                f"engineering gate media header drift for {item['sample_id']!r}"
            )
        samples.append(
            SlurpEngineeringSample(
                sample_id=item["sample_id"],
                media_relpath=item["media_relpath"],
                audio_sha256=item["audio_sha256"],
                audio_seconds=float(expected_seconds),
                sample_rate_hz=expected_rate,
                packet_id=item["packet_id"],
            )
        )
    expected_total = document["audio_seconds_total"]
    actual_total = sum(sample.audio_seconds for sample in samples)
    if (
        isinstance(expected_total, bool)
        or not isinstance(expected_total, (int, float))
        or abs(float(expected_total) - actual_total) > 1e-6
    ):
        raise LoaderError("speech-native engineering gate audio total mismatch")
    return SlurpEngineeringGate(
        split_identity_hash=document["split_identity_hash"],
        runtime_view_sha256=document["runtime_view_sha256"],
        d1_media_supplement=supplement_path,
        d1_media_supplement_sha256=document["d1_media_supplement_sha256"],
        samples=tuple(samples),
    )


def slurp_governed_carrier_root(lock: Mapping[str, object], root: Path) -> Path:
    """Return the governed audio root, not SLURP's unrelated raw checkout."""

    _relpath, audio_root, _metadata_dir = _governed_roots(lock, root)
    return audio_root


def _speech_native_gate_sample_refs(
    gate: SlurpEngineeringGate,
    *,
    lock: Mapping[str, object],
    root: Path,
) -> list[SampleRef]:
    carrier_root = slurp_governed_carrier_root(lock, root).resolve(strict=True)
    data_root = Path(root).resolve(strict=True)
    samples: list[SampleRef] = []
    for sample in gate.samples:
        resolved = (data_root / sample.media_relpath).resolve(strict=True)
        if not resolved.is_relative_to(carrier_root):
            raise LoaderError(
                f"speech-native sample {sample.sample_id!r} is outside the governed "
                "SLURP root"
            )
        samples.append(
            SampleRef(
                carrier_lock_key=SLURP_LOCK_KEY,
                sample_id=sample.sample_id,
                media_relpath=sample.media_relpath,
                audio_seconds=sample.audio_seconds,
                sample_rate_hz=sample.sample_rate_hz,
            )
        )
    return samples


def load_slurp_engineering_carrier(
    lock: Mapping[str, object],
    root: Path,
    *,
    config_path: Path | None = None,
    expected_count: int = 8,
    workers: int = 8,
) -> list[SampleRef]:
    """Load only the committed label-free engineering view for core runs."""

    gate_path = (
        Path(config_path)
        if config_path is not None
        else REPO_ROOT / "configs" / "dataset" / "slurp-speech-native-eng-gate8.json"
    )
    gate = load_slurp_engineering_gate(
        gate_path,
        data_root=root,
        expected_count=expected_count,
        workers=workers,
    )
    return _speech_native_gate_sample_refs(gate, lock=lock, root=root)


def load_slurp_speech_native_carrier(
    lock: Mapping[str, object],
    root: Path,
    *,
    config_path: Path,
    expected_split_name: str,
    expected_count: int,
    workers: int = 16,
) -> list[SampleRef]:
    """Load a composed label-free speech-native dataset fragment.

    This is the generalized path used by the experiment driver. The older
    :func:`load_slurp_engineering_carrier` remains the no-argument compatibility
    entry point for ENG-GATE8 and direct registry callers.
    """

    gate = load_slurp_engineering_gate(
        Path(config_path),
        data_root=root,
        expected_count=expected_count,
        expected_split_name=expected_split_name,
        workers=workers,
    )
    return _speech_native_gate_sample_refs(gate, lock=lock, root=root)


def load_slurp_train_material(
    lock: Mapping[str, object],
    root: Path,
    *,
    media_validation_workers: int = 16,
) -> tuple[SlurpTrainMaterial, ...]:
    """Load real ``train.jsonl`` text/audio/speaker provenance for binding.

    The function never reads ``train_synthetic`` and never exposes this text
    through the runtime query loader. Every listed recording must resolve to
    a speaker in the governed release's ``metadata.json`` and to an existing
    natural-audio file.
    """

    audio_root_relpath, audio_root, metadata_dir = _governed_roots(lock, root)
    metadata_path = metadata_dir / _SPLIT_FILES["train"]
    if not metadata_path.is_file():
        raise LoaderError(f"SLURP train metadata file missing: {metadata_path}")
    speakers = _slurp_speaker_index(metadata_dir)
    audio_dir = audio_root / _AUDIO_SUBDIR_FOR_SPLIT["train"]
    audio_dir_relpath = f"{audio_root_relpath}/{_AUDIO_SUBDIR_FOR_SPLIT['train']}"
    material: list[SlurpTrainMaterial] = []
    media_paths: list[Path] = []
    for line_no, raw in enumerate(_read_jsonl(metadata_path), start=1):
        context = f"SLURP train.jsonl line {line_no}"
        slurp_id = raw.get("slurp_id")
        scenario = raw.get("scenario")
        action = raw.get("action")
        sentence = raw.get("sentence")
        if isinstance(slurp_id, bool) or not isinstance(slurp_id, int):
            raise LoaderError(f"{context}: slurp_id must be an int")
        if not isinstance(scenario, str) or not scenario:
            raise LoaderError(f"{context}: scenario must be a non-empty string")
        if not isinstance(action, str) or not action:
            raise LoaderError(f"{context}: action must be a non-empty string")
        if not isinstance(sentence, str) or not sentence.strip():
            raise LoaderError(f"{context}: sentence must be a non-empty string")
        raw_entities = raw.get("entities")
        if not isinstance(raw_entities, list):
            raise LoaderError(f"{context}: entities must be a list")
        entity_types = tuple(
            sorted({_entity_type(entity, context) for entity in raw_entities})
        )
        tokens_by_id = _tokens_by_id(raw.get("tokens"), context)
        entities = tuple(
            SlotEntity(
                type=_entity_type(entity, context),
                filler=_entity_filler(
                    tokens_by_id,
                    entity.get("span") if isinstance(entity, Mapping) else None,
                    context,
                ),
            )
            for entity in raw_entities
        )
        raw_recordings = raw.get("recordings")
        if not isinstance(raw_recordings, list) or not raw_recordings:
            raise LoaderError(f"{context}: recordings must be a non-empty list")
        recordings: list[SlurpTrainRecording] = []
        for raw_recording in raw_recordings:
            if not isinstance(raw_recording, Mapping):
                raise LoaderError(f"{context}: recording entry must be an object")
            filename = _validate_recording_filename(raw_recording.get("file"), context)
            speaker_id = speakers.get(filename)
            if speaker_id is None:
                raise LoaderError(
                    f"{context}: recording {filename!r} lacks governed speaker identity"
                )
            media_path = audio_dir / filename
            media_paths.append(media_path)
            recordings.append(
                SlurpTrainRecording(
                    sample_id=(
                        f"slurp:train:{slurp_id:06d}:{filename[: -len('.flac')]}"
                    ),
                    media_relpath=f"{audio_dir_relpath}/{filename}",
                    speaker_id=speaker_id,
                )
            )
        material.append(
            SlurpTrainMaterial(
                utterance_id=str(slurp_id),
                scenario=scenario,
                action=action,
                sentence=sentence.strip(),
                recordings=tuple(sorted(recordings, key=lambda item: item.sample_id)),
                entity_types=entity_types,
                entities=entities,
            )
        )
    if not material:
        raise LoaderError("SLURP train material resolved to zero utterances")
    missing_paths = _missing_media_paths(
        media_paths,
        workers=media_validation_workers,
    )
    if missing_paths:
        raise LoaderError(
            "SLURP train material media validation failed: "
            f"{len(missing_paths)} file(s) missing; first missing path: {missing_paths[0]}"
        )
    return tuple(sorted(material, key=lambda item: (item.scenario, item.utterance_id)))


def load_slurp_split(
    lock: Mapping[str, object],
    root: Path,
    split_id: str,
    *,
    allow_heldout: bool = False,
    allow_synthetic: bool = False,
    workers: int | None = None,
) -> list[SlurpRecord]:
    """Every SLURP (sentence, recording) sample in ``split_id``, sorted by
    sample id, with media re-verified against the flac headers (module
    docstring: split discipline + entity-filler derivation).

    ``workers`` bounds the THREAD pool that pays the flac-header latency ahead
    of the parse (:func:`_prefetch_audio_seconds`); ``None`` takes
    ``analysis.parallel``'s own default, the campaign preparation cap. The
    records this returns -- their order, their durations, and every refusal
    the parse can raise -- do not depend on it: the prefetch is best-effort
    and the parse is the same serial loop it always was.
    """

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

    rows = _read_jsonl(metadata_path)
    # Pay the ~50,000 flac-header round-trips concurrently, THEN parse exactly
    # as before. Only successful probes are cached, so the parse below still
    # raises every LoaderError itself, for the same file, in the same order.
    durations = _prefetch_audio_seconds(
        rows, audio_dir, workers=_audio_probe_workers(workers)
    )
    records: list[SlurpRecord] = []
    seen_ids: set[str] = set()
    for line_no, raw in enumerate(rows, start=1):
        for record in _parse_record(
            raw, split_id, audio_dir_relpath, audio_dir, line_no, durations
        ):
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
    actions_by_scenario: dict[str, set[str]] = {}
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
            # The pairing, mined from the SAME line the two flat sets above
            # are mined from, so the inventory can never disagree with them
            # about which labels exist. Recorded only when BOTH fields are
            # present and non-empty -- a half-labelled line contributes to
            # neither the pair nor a phantom scenario with no actions.
            if isinstance(scenario, str) and scenario and isinstance(action, str) and action:
                actions_by_scenario.setdefault(scenario, set()).add(action)
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
        actions_by_scenario={
            scenario: tuple(sorted(scenario_actions))
            for scenario, scenario_actions in sorted(actions_by_scenario.items())
        },
    )


def render_slurp_ontology(ontology: SlurpOntology) -> str:
    """Deterministic single-line JSON rendering of ``ontology`` -- the
    ``{tool_schemas}``-equivalent fixed text ``SlurpAdapter.build_task_contract``
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


_LABEL_INVENTORY_HEADER = (
    "Closed label inventory. Choose the scenario, the action and every entity "
    "type ONLY from the lists below. Never invent a label, never abbreviate "
    "one, and never pair a scenario with an action that is not listed on its "
    "own line."
)


def render_slurp_label_inventory(ontology: SlurpOntology) -> str:
    """The COMPACT closed label inventory: one line per scenario naming the
    actions observed with it, then one line naming every entity type.

    Deliberately NOT another JSON document (that is
    :func:`render_slurp_ontology`'s job) and deliberately carrying no example
    fillers: this block's whole content is the closed LABEL space -- the 18
    scenarios, the actions legal under each of them (60 pairs on the real
    ``train`` corpus), and the 55 entity type names. Adding examples here
    would make it a few-shot block instead of the zero-shot label inventory
    the published prompt-only protocol uses.

    Determinism: scenarios sorted, actions sorted within a scenario, entity
    types sorted -- the same ordering discipline
    :func:`render_slurp_ontology` already applies, so the rendered bytes are
    a pure function of the pinned ``train.jsonl``.

    Fails closed on an ontology with no pairing (e.g. one built before
    ``actions_by_scenario`` existed): an inventory that silently omitted the
    intent pairing would be exactly the defect this function exists to fix.
    """

    if not ontology.actions_by_scenario:
        raise LoaderError(
            "SlurpOntology carries no actions_by_scenario pairing; refusing to render a "
            "label inventory whose whole purpose is the scenario/action pairing"
        )
    pair_lines = [
        f"{scenario}: {', '.join(actions)}"
        for scenario, actions in sorted(ontology.actions_by_scenario.items())
    ]
    pair_count = sum(len(actions) for actions in ontology.actions_by_scenario.values())
    entity_types = sorted(ontology.entity_types)
    return "\n".join(
        (
            _LABEL_INVENTORY_HEADER,
            f"Legal scenario -> action pairs ({pair_count} intents in total; the "
            'value of "action" must appear on the line of the chosen "scenario"):',
            *pair_lines,
            f'Entity types ({len(entity_types)} in total; every "type" must be '
            f"exactly one of these): {', '.join(entity_types)}",
        )
    )


def render_slurp_closed_label_inventory(lock: Mapping[str, object], root: Path) -> str:
    """``core.base.INSTRUCTION_FILLS`` entry ``"slurp-label-inventory"``:
    the UNCHANGED :func:`render_slurp_ontology` task contract, followed by
    the compact closed inventory of :func:`render_slurp_label_inventory`.

    The ordering and the blank-line join are load-bearing. The first half is
    byte-identical to the task contract the sealed 2026-08-25 DEV-1000 M0
    arm already sent (``rails.runner._agent_messages`` appended exactly this
    rendering under a ``"Task contract:"`` header), so an arm using this
    fill differs from that sealed comparator by a pure SUFFIX and by nothing
    else -- which is what makes the paired contrast a measurement of the
    closed inventory rather than of a rewritten prompt.

    Signature matches every other instruction fill: ``(lock, root) -> str``.
    """

    ontology = load_slurp_ontology(lock, root)
    return f"{render_slurp_ontology(ontology)}\n\n{render_slurp_label_inventory(ontology)}"


# ---------------------------------------------------------------------------
# Per-intent slot schema (program prerequisite MF-3)
# ---------------------------------------------------------------------------

#: Identity of the slot-schema construction rule this module implements. Bumped
#: only when the RULE changes (threshold, example cap, counting unit, ordering);
#: the corpus it is measured on is pinned by the umbrella lock instead.
SLURP_INTENT_SLOT_SCHEMA_ID = "slurp-intent-slot-schema-v1"

#: Receipt document schema of :func:`slurp_intent_slot_schema_receipt`.
SLURP_INTENT_SLOT_SCHEMA_RECEIPT_SCHEMA = "saea-slurp-intent-slot-schema-v1"

#: A type is listed for an intent only when it carries at least this share of
#: that intent's TRAIN slot mentions (the preregistration's "at least 2 %").
_INTENT_SLOT_MIN_SHARE = 0.02

#: Example fillers kept per (intent, entity type), in first-seen TRAIN order.
_INTENT_SLOT_EXAMPLES_PER_TYPE = 5

#: Decimal places the stored/hashed share keeps. The FILTER always runs on the
#: exact ratio; only the recorded number is rounded, so the schema's content
#: hash is stable across platforms with different float repr behaviour.
_INTENT_SLOT_SHARE_DIGITS = 6

#: The two committed receipts that already establish this construction source's
#: decontamination: the KB-BUILD receipt (verdict "clean" over its checked TRAIN
#: sample ids against every frozen roster) and the frozen devel/test identity
#: enumeration it was checked against. This module adds no new split read.
SLURP_INTENT_SLOT_DECONTAMINATION_RECEIPTS: tuple[str, ...] = (
    "docs/receipts/knowledge/slurp-kb-size-full.json",
    "docs/receipts/knowledge/slurp-split-identity.json",
)

_SLOT_SCHEMA_HEADER = (
    "Slot schema measured on the TRAIN split, one block per intent. A block "
    "names the entity types that intent draws its slots from, how much of the "
    "intent's slot mentions each type carries, and fillers heard with that "
    "type. Use a type only when the speech supports it, and write each filler "
    "exactly as it was spoken, in lower case, without translating, expanding, "
    "abbreviating or reordering it."
)


@dataclass(frozen=True)
class SlurpIntentSlots:
    """One intent's TRAIN slot profile.

    ``types`` is the ordered ``(entity_type, count, share)`` table kept after
    the share floor, most frequent first, ties broken by type name. ``count``
    is a MENTION count -- how many entity mentions of that type occur across
    this intent's TRAIN utterances -- and ``share`` is that count divided by
    ``mentions``, this intent's total mention mass. The mention unit is what
    makes the shares a partition of one intent's slot mass (the exact ratios
    sum to 1 before the floor drops the tail, and the RECORDED shares sum to
    1 up to their own rounding); the UTTERANCE-level
    quantity ``rails.knowledge_build`` renders as ``facet:prior`` is a
    different measurement of the same rows and its shares routinely sum above
    1 (17 of the 60 TRAIN intents, up to 1.97), which is why this table is
    computed here rather than read off that facet.

    ``fillers`` maps a listed entity type to up to
    :data:`_INTENT_SLOT_EXAMPLES_PER_TYPE` distinct example fillers in
    first-seen TRAIN order, each already lower-cased by :func:`_entity_filler`
    exactly as the official SLURP eval script lower-cases the gold side.
    """

    intent: str
    n: int
    mentions: int
    types: tuple[tuple[str, int, float], ...]
    fillers: Mapping[str, tuple[str, ...]] = MappingProxyType({})

    @property
    def entity_types(self) -> tuple[str, ...]:
        """The listed type names, in table order."""

        return tuple(entity_type for entity_type, _count, _share in self.types)

    def as_json(self) -> dict[str, object]:
        return {
            "intent": self.intent,
            "utterances": self.n,
            "slot_mentions": self.mentions,
            "types": [
                {
                    "entity_type": entity_type,
                    "count": count,
                    "share": share,
                    "fillers": list(self.fillers.get(entity_type, ())),
                }
                for entity_type, count, share in self.types
            ],
        }


@dataclass(frozen=True)
class SlurpIntentSlotSchema:
    """The whole per-intent slot schema plus the identity of the split it was
    mined from -- TRAIN and nothing else (:data:`_ROSTER_SPLITS_LEGAL`).

    ``source_identity_hash`` is the sha256 of the newline-joined, sorted
    ``slurp:train:{slurp_id:06d}`` utterance ids that were actually read, so a
    receipt can bind the schema to a corpus state without carrying the rows.
    ``intents`` is keyed by the SAME ``f"{scenario}_{action}"`` spelling
    :func:`_parse_record` gives ``SlurpRecord.intent`` and
    :class:`SlurpOntology.intents` renders, so a schema block, an inventory
    line and a gold label all compare directly. Non-empty
    ``excluded_train_utterance_ids`` records the canonical utterance-level
    construction exclusions; it is omitted from the legacy JSON projection
    when empty so existing identities remain exact.
    """

    schema_id: str
    source_split: str
    source_identity_hash: str
    utterance_count: int
    min_share: float
    examples_per_type: int
    intents: Mapping[str, SlurpIntentSlots]
    excluded_train_utterance_ids: tuple[str, ...] = ()

    @property
    def intent_ids(self) -> tuple[str, ...]:
        """The intents carrying a profile, sorted (construction order)."""

        return tuple(sorted(self.intents))

    def as_json(self) -> dict[str, object]:
        document = {
            "schema_id": self.schema_id,
            "source_split": self.source_split,
            "source_identity_hash": self.source_identity_hash,
            "utterance_count": self.utterance_count,
            "min_share": self.min_share,
            "examples_per_type": self.examples_per_type,
            "intents": [self.intents[intent].as_json() for intent in self.intent_ids],
        }
        if self.excluded_train_utterance_ids:
            document["excluded_train_utterance_ids"] = list(
                self.excluded_train_utterance_ids
            )
        return document

    def content_hash(self) -> str:
        """Canonical-JSON sha256 of :meth:`as_json` (the same canonicalization
        every other hashable document in this module uses)."""

        return _canonical_sha256(self.as_json())


def _train_utterance_id(raw: Mapping[str, object], context: str) -> str:
    slurp_id = raw.get("slurp_id")
    if isinstance(slurp_id, bool) or not isinstance(slurp_id, int):
        raise LoaderError(f"{context}: slurp_id must be an int")
    return f"slurp:train:{slurp_id:06d}"


def normalize_slurp_train_utterance_exclusions(
    excluded_train_utterance_ids: Sequence[str] | None,
) -> tuple[str, ...]:
    """Validate and canonically order TRAIN utterance exclusions.

    Each ID names an utterance, not one recording, and has the exact form
    ``slurp:train:000001``. A caller that starts from recording-scoped roster
    IDs must collapse their shared utterance prefix before calling this
    helper. Excluding that utterance then excludes every sibling recording
    represented by its governed TRAIN row.
    """

    if excluded_train_utterance_ids is None:
        return ()
    if isinstance(excluded_train_utterance_ids, (str, bytes)) or not isinstance(
        excluded_train_utterance_ids, Sequence
    ):
        raise LoaderError(
            "excluded_train_utterance_ids must be a sequence of canonical "
            "SLURP TRAIN utterance IDs"
        )
    normalized: list[str] = []
    seen: set[str] = set()
    for index, utterance_id in enumerate(excluded_train_utterance_ids):
        context = f"excluded_train_utterance_ids[{index}]"
        if not isinstance(utterance_id, str):
            raise LoaderError(f"{context} must be text")
        parts = utterance_id.split(":")
        if (
            len(parts) != 3
            or parts[:2] != ["slurp", "train"]
            or len(parts[2]) != 6
            or not parts[2].isdigit()
        ):
            raise LoaderError(
                f"{context} must have the canonical form 'slurp:train:<six digits>'"
            )
        canonical = _train_utterance_id({"slurp_id": int(parts[2])}, context)
        if canonical != utterance_id:
            raise LoaderError(
                f"{context} must have the canonical form 'slurp:train:<six digits>'"
            )
        if canonical in seen:
            raise LoaderError(
                f"excluded_train_utterance_ids contains duplicate ID {canonical!r}"
            )
        seen.add(canonical)
        normalized.append(canonical)
    return tuple(sorted(normalized))


def load_slurp_intent_slot_schema(
    lock: Mapping[str, object],
    root: Path,
    *,
    min_share: float = _INTENT_SLOT_MIN_SHARE,
    examples_per_type: int = _INTENT_SLOT_EXAMPLES_PER_TYPE,
    excluded_train_utterance_ids: Sequence[str] | None = None,
) -> SlurpIntentSlotSchema:
    """Mine the per-intent slot schema from ``train.jsonl`` -- and only from
    ``train.jsonl``.

    Split discipline. The one metadata file this function opens is named by
    ``_SPLIT_FILES[_ROSTER_SPLITS_LEGAL[0]]``, a module constant: there is no
    ``split`` parameter, no ``include_synthetic`` widening (the 64.8 % devel
    recurrence documented on :func:`load_slurp_ontology` makes the synthetic
    pool ceiling-tier for any devel read, and this schema exists to be sent
    during a devel-split flight), and no caller-supplied path, so a devel or
    test file cannot be reached through this entry point at all.

    Text-only, like :func:`load_slurp_ontology`: no audio is opened and no
    per-recording existence check runs.

    Determinism. Utterances are read in file order; the mention counters and
    the first-seen filler lists are therefore a pure function of the pinned
    bytes, the type table is sorted by ``(-count, entity_type)``, and the
    recorded share is rounded to :data:`_INTENT_SLOT_SHARE_DIGITS` places
    AFTER the floor test has run on the exact ratio.

    Optional construction exclusion. ``excluded_train_utterance_ids`` uses
    canonical IDs such as ``slurp:train:000001``. The loader validates their
    form before reading TRAIN, refuses unknown IDs after validating source
    membership, and removes matching utterances before accumulating observed
    counts or fillers. The full source label inventory remains available, so
    a label whose observations were all excluded has an explicit empty
    profile.

    Tolerance mirrors :func:`load_slurp_ontology` deliberately: a row with an
    unusable ``tokens`` block or a malformed entity contributes no slot
    mentions but still counts toward its intent's ``n``, so ``n`` always means
    "TRAIN utterances with this intent". A row without a usable ``slurp_id``
    is the one hard failure -- the schema's identity hash would otherwise be
    unbound.
    """

    exclusions = normalize_slurp_train_utterance_exclusions(
        excluded_train_utterance_ids
    )
    exclusion_set = frozenset(exclusions)
    if isinstance(min_share, bool) or not isinstance(min_share, (int, float)):
        raise LoaderError(f"min_share must be a number, got {min_share!r}")
    if not 0.0 <= float(min_share) <= 1.0:
        raise LoaderError(f"min_share must lie in [0, 1], got {min_share!r}")
    if isinstance(examples_per_type, bool) or not isinstance(examples_per_type, int):
        raise LoaderError(f"examples_per_type must be an int, got {examples_per_type!r}")
    if examples_per_type < 0:
        raise LoaderError("examples_per_type must not be negative")

    split_id = _ROSTER_SPLITS_LEGAL[0]
    _, _, metadata_dir = _governed_roots(lock, root)
    metadata_path = metadata_dir / _SPLIT_FILES[split_id]
    if not metadata_path.is_file():
        raise LoaderError(f"SLURP split metadata file missing: {metadata_path}")

    available_utterance_ids: set[str] = set()
    utterance_ids: set[str] = set()
    legal_intents: set[str] = set()
    utterances_by_intent: dict[str, int] = {}
    mentions_by_intent: dict[str, dict[str, int]] = {}
    fillers_by_intent_type: dict[tuple[str, str], list[str]] = {}
    for line_no, raw in enumerate(_read_jsonl(metadata_path), start=1):
        context = f"SLURP {split_id}.jsonl line {line_no}"
        scenario = raw.get("scenario")
        action = raw.get("action")
        if not isinstance(scenario, str) or not scenario:
            continue
        if not isinstance(action, str) or not action:
            continue
        utterance_id = _train_utterance_id(raw, context)
        intent = f"{scenario}_{action}"
        available_utterance_ids.add(utterance_id)
        legal_intents.add(intent)
        if utterance_id in exclusion_set:
            continue
        utterance_ids.add(utterance_id)
        utterances_by_intent[intent] = utterances_by_intent.get(intent, 0) + 1
        mentions_by_intent.setdefault(intent, {})
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
            counts = mentions_by_intent[intent]
            counts[entity_type] = counts.get(entity_type, 0) + 1
            examples = fillers_by_intent_type.setdefault((intent, entity_type), [])
            if filler and len(examples) < examples_per_type and filler not in examples:
                examples.append(filler)

    unknown_exclusions = sorted(exclusion_set - available_utterance_ids)
    if unknown_exclusions:
        raise LoaderError(
            "excluded_train_utterance_ids contains ID absent from governed TRAIN "
            f"metadata: {unknown_exclusions[0]}"
        )
    if not utterance_ids:
        raise LoaderError(
            f"SLURP {split_id} metadata {metadata_path} yielded no labelled utterance; "
            "refusing to build an empty slot schema"
        )

    profiles: dict[str, SlurpIntentSlots] = {}
    for intent in sorted(legal_intents):
        counts = mentions_by_intent.get(intent, {})
        mentions = sum(counts.values())
        kept = [
            (entity_type, count)
            for entity_type, count in counts.items()
            if mentions and count / mentions >= float(min_share)
        ]
        kept.sort(key=lambda item: (-item[1], item[0]))
        types = tuple(
            (entity_type, count, round(count / mentions, _INTENT_SLOT_SHARE_DIGITS))
            for entity_type, count in kept
        )
        profiles[intent] = SlurpIntentSlots(
            intent=intent,
            n=utterances_by_intent.get(intent, 0),
            mentions=mentions,
            types=types,
            fillers=MappingProxyType(
                {
                    entity_type: tuple(
                        fillers_by_intent_type.get((intent, entity_type), ())
                    )
                    for entity_type, _count, _share in types
                }
            ),
        )
    identity_hash = hashlib.sha256(
        "\n".join(sorted(utterance_ids)).encode("utf-8")
    ).hexdigest()
    return SlurpIntentSlotSchema(
        schema_id=SLURP_INTENT_SLOT_SCHEMA_ID,
        source_split=split_id,
        source_identity_hash=identity_hash,
        utterance_count=len(utterance_ids),
        min_share=float(min_share),
        examples_per_type=examples_per_type,
        intents=MappingProxyType(profiles),
        excluded_train_utterance_ids=exclusions,
    )


def render_slurp_intent_slot_schema(
    schema: SlurpIntentSlotSchema, *, intents: Sequence[str] | None = None
) -> str:
    """Render ``schema`` as compact instruction text: one shared header, then
    one block per requested intent (all of them, sorted, when ``intents`` is
    ``None``).

    The wording is deliberately NOT the ``facet:prior`` representation
    ``rails.knowledge_build`` builds from the same rows. Two reasons, one
    mechanical and one scientific. Mechanically, ``rails.runner.
    _assert_agent_control_excludes_knowledge_payloads`` refuses any CONTROL
    instruction that embeds a frozen snapshot's own facet/value payload, so a
    schema phrased like a facet would be unsendable beside a knowledge
    snapshot. Scientifically, this block is a USE-side instruction (which
    types to fill and how to write a filler), not a retrieved knowledge
    payload, and it must read as one: prose sentences, percentages and example
    fillers rather than ``type=0.4321 (56/130)`` count pairs.

    Measured on the real corpus against the full committed snapshot: zero
    ``facet:prior`` texts are substrings of this rendering and zero rendered
    lines are substrings of a ``facet:prior`` text.  Fourteen ``facet:content``
    payloads ARE -- one-word or two-word TRAIN utterances such as "calendar",
    "shopping" or "next episode" that also occur verbatim as entity fillers.
    That overlap is a property of the corpus, not of the wording, and it is
    harmless for the cells this schema was built for (their slot phase declares
    ``knowledge: "none"``, so no snapshot is in play and the guard has nothing
    to protect).  A future cell that wants BOTH this schema and a live snapshot
    on the same contact has to resolve it deliberately -- by excluding the
    content dimension from that snapshot, not by trimming the schema, because
    the fillers are what the block is for.
    """

    requested = tuple(schema.intent_ids) if intents is None else tuple(intents)
    unknown = [intent for intent in requested if intent not in schema.intents]
    if unknown:
        raise LoaderError(
            f"slot schema {schema.schema_id!r} has no block for intents {sorted(unknown)}"
        )
    floor_pct = f"{schema.min_share * 100:g}"
    lines: list[str] = [_SLOT_SCHEMA_HEADER]
    for intent in requested:
        profile = schema.intents[intent]
        lines.append(
            f"== {intent} == {profile.n} TRAIN utterances, "
            f"{profile.mentions} slot mentions"
        )
        if not profile.types:
            lines.append(
                f"- no entity type reaches the {floor_pct} percent floor for this "
                "intent; leave the entity list empty unless the speech plainly "
                "carries one"
            )
            continue
        for entity_type, _count, share in profile.types:
            fillers = profile.fillers.get(entity_type, ())
            spoken = "; ".join(fillers) if fillers else "no example filler recorded"
            lines.append(
                f"- {entity_type} ({share * 100:.1f} percent of slot mentions): {spoken}"
            )
    return "\n".join(lines)


def render_slurp_closed_label_inventory_with_slot_schema(
    lock: Mapping[str, object], root: Path
) -> str:
    """``core.base.INSTRUCTION_FILLS`` entry ``"slurp-intent-slot-schema"``:
    the closed-list fill's bytes UNCHANGED, followed by the full per-intent
    slot schema.

    The pure-suffix discipline is the same one
    :func:`render_slurp_closed_label_inventory` follows against the sealed M0
    task contract, one layer out: an arm naming this fill differs from the
    sealed closed-list direct baseline by a suffix and by nothing else, so a
    paired contrast measures the slot schema rather than a rewritten prompt.
    """

    inventory = render_slurp_closed_label_inventory(lock, root)
    schema = load_slurp_intent_slot_schema(lock, root)
    return f"{inventory}\n\n{render_slurp_intent_slot_schema(schema)}"


#: Process-local cache for the per-sample renderer below: the slot phase asks
#: for one block per row, and re-mining 11,514 TRAIN utterances per row would
#: dominate a 1,000-row flight. Keyed by the resolved governed metadata
#: directory, which the umbrella lock pins. :func:`load_slurp_intent_slot_schema`
#: itself is never cached, so a test that rewrites a corpus in place still sees
#: its own bytes.
_INTENT_SLOT_SCHEMA_CACHE: dict[str, SlurpIntentSlotSchema] = {}


def _cached_intent_slot_schema(
    lock: Mapping[str, object], root: Path
) -> SlurpIntentSlotSchema:
    _, _, metadata_dir = _governed_roots(lock, root)
    key = str(metadata_dir)
    cached = _INTENT_SLOT_SCHEMA_CACHE.get(key)
    if cached is None:
        cached = load_slurp_intent_slot_schema(lock, root)
        _INTENT_SLOT_SCHEMA_CACHE[key] = cached
    return cached


def slurp_intent_from_state_content(
    state_content: object,
    *,
    projection: Callable[..., object] | None = None,
) -> str | None:
    """The ``f"{scenario}_{action}"`` intent a sealed closed-list response
    carries, or ``None`` when the response does not parse or names only half
    of the pair.

    Parsing is delegated to
    :func:`reproduction.slurp_scoring.parse_slu_response` -- the same
    fail-closed parser the official scorer's prediction side uses -- so the
    slot phase conditions on EXACTLY the label the comparator scored.

    ``projection``, when given, is a legal-label projection rule already
    bound to its inventory -- ``project_slu_label`` or ``project_slu_label_v2``
    partially applied -- called as ``projection(scenario, action,
    parsed=True)`` and returning a
    :class:`reproduction.slurp_scoring.LabelProjection`. It exists so a cell
    can select its per-intent block from a REPAIRED label: 3.9 % of the
    sealed closed-list rows name a (scenario, action) pair TRAIN never
    carries, and those rows otherwise fall back to the full 60-intent schema.
    The default is no projection, so every already-flown cell keeps its own
    selection byte for byte.
    """

    if not isinstance(state_content, str) or not state_content.strip():
        return None
    scenario, action, _entities, parsed = parse_slu_response(state_content)
    if not parsed:
        return None
    if projection is not None:
        projected = projection(scenario, action, parsed=parsed)
        if not getattr(projected, "eligible", False):
            return None
        scenario, action = projected.scenario, projected.action
    if not isinstance(scenario, str) or not scenario:
        return None
    if not isinstance(action, str) or not action:
        return None
    return f"{scenario}_{action}"


def render_slurp_slot_schema_for_state_detail(
    lock: Mapping[str, object],
    root: Path,
    state_content: object,
    *,
    schema: SlurpIntentSlotSchema | None = None,
    projection: Callable[..., object] | None = None,
) -> tuple[str, str | None, bool]:
    """``(text, used_intent, fallback)`` for one sealed closed-list response.

    When the response parses to an intent the schema knows, ``text`` is that
    intent's block alone and ``fallback`` is ``False``. When it does not parse,
    names only half a pair, or names an intent absent from TRAIN, ``text`` is
    the FULL schema, ``used_intent`` is ``None`` and ``fallback`` is ``True`` --
    the row still gets a legal slot instruction, and the flight can report how
    often that happened instead of silently dropping rows.

    ``schema=`` lets a caller (the phase-material seam) hand in a schema it
    already holds; otherwise the process-local cache is used.
    """

    resolved = schema if schema is not None else _cached_intent_slot_schema(lock, root)
    intent = slurp_intent_from_state_content(state_content, projection=projection)
    if intent is not None and intent in resolved.intents:
        return render_slurp_intent_slot_schema(resolved, intents=(intent,)), intent, False
    return render_slurp_intent_slot_schema(resolved), None, True


def render_slurp_slot_schema_for_state(
    lock: Mapping[str, object],
    root: Path,
    state_content: object,
    *,
    schema: SlurpIntentSlotSchema | None = None,
    projection: Callable[..., object] | None = None,
) -> str:
    """The text half of :func:`render_slurp_slot_schema_for_state_detail`."""

    text, _used_intent, _fallback = render_slurp_slot_schema_for_state_detail(
        lock, root, state_content, schema=schema, projection=projection
    )
    return text


def slurp_intent_slot_schema_receipt(
    schema: SlurpIntentSlotSchema, *, generator: str
) -> dict[str, object]:
    """The TRAIN-only governance receipt document for ``schema`` (pure: the
    caller writes it with a canonical JSON writer).

    Carries the construction rule, the source split identity, the per-intent
    tables with their counts, shares and filler lists, the schema content hash,
    the rendered full text's sha256 and size, and the decontamination statement
    -- which cites, rather than repeats, the two committed receipts that
    already established this source's cleanliness
    (:data:`SLURP_INTENT_SLOT_DECONTAMINATION_RECEIPTS`).
    """

    rendered = render_slurp_intent_slot_schema(schema)
    document = schema.as_json()
    intent_blocks = document.pop("intents")
    listed_types = sum(len(block["types"]) for block in intent_blocks)
    filler_count = sum(
        len(entry["fillers"]) for block in intent_blocks for entry in block["types"]
    )
    return {
        "schema": SLURP_INTENT_SLOT_SCHEMA_RECEIPT_SCHEMA,
        "generator": generator,
        "carrier": SLURP_LOCK_KEY,
        "construction": {
            **document,
            "count_unit": "entity mention",
            "share_denominator": "this intent's TRAIN entity mentions",
            "type_order": "descending count, ties by entity type name",
            "filler_order": "first seen in TRAIN file order, distinct, lower case",
        },
        "content_hash": schema.content_hash(),
        "rendered_full_text": {
            "sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
            "characters": len(rendered),
            "lines": len(rendered.split("\n")),
        },
        "totals": {
            "intents": len(intent_blocks),
            "listed_type_rows": listed_types,
            "example_fillers": filler_count,
            "distinct_listed_types": len(
                {
                    entry["entity_type"]
                    for block in intent_blocks
                    for entry in block["types"]
                }
            ),
        },
        "intents": intent_blocks,
        "decontamination": {
            "verdict": "clean",
            "statement": (
                "Built from the governed SLURP train.jsonl alone: no devel or test "
                "metadata file is opened by load_slurp_intent_slot_schema, which "
                "names its split from a module constant and takes no split "
                "argument. The cleanliness of that TRAIN source against the frozen "
                "devel/test identity enumeration and the DEV rosters was measured "
                "once by the KB-BUILD receipt cited below and is not re-measured "
                "here, because re-measuring it would mean opening those splits "
                "again."
            ),
            "cited_receipts": list(SLURP_INTENT_SLOT_DECONTAMINATION_RECEIPTS),
        },
    }

#: Identity of the ROW-level per-intent profile :func:`load_slurp_intent_row_profiles`
#: mines (E12, 2026-09-19, owner directive 26). Distinct from
#: :data:`SLURP_INTENT_SLOT_SCHEMA_ID` because the unit differs: that schema
#: counts entity MENTIONS, this one counts UTTERANCES (rows).
SLURP_INTENT_ROW_PROFILE_ID = "slurp-intent-row-profile-v1"


@dataclass(frozen=True)
class SlurpIntentRowProfile:
    """One intent's ROW-level construction profile.

    ``rows`` is how many construction utterances carry this intent;
    ``rows_with_entity`` how many of them carry at least one annotated entity
    of any type; ``type_rows`` maps an entity type to the number of this
    intent's rows carrying AT LEAST ONE mention of it. A type's row share is
    therefore ``type_rows[t] / rows`` and the shares do NOT partition one --
    a row carrying a ``date`` and a ``time`` counts once under each. That is
    the right unit for the two questions the Reviewer slot-audit block asks
    ("how often does a row of this intent carry this type at all?" and "how
    often does a row of this intent carry no entity at all?"), which the
    mention-unit table of :class:`SlurpIntentSlots` cannot answer.
    """

    intent: str
    rows: int
    rows_with_entity: int
    type_rows: Mapping[str, int] = MappingProxyType({})

    def as_json(self) -> dict[str, object]:
        return {
            "intent": self.intent,
            "rows": self.rows,
            "rows_with_entity": self.rows_with_entity,
            "type_rows": [
                {"entity_type": entity_type, "rows": self.type_rows[entity_type]}
                for entity_type in sorted(
                    self.type_rows,
                    key=lambda name: (-self.type_rows[name], name),
                )
            ],
        }


@dataclass(frozen=True)
class SlurpIntentRowProfiles:
    """Every intent's row-level profile plus the identity of what was read."""

    profile_id: str
    source_split: str
    source_identity_hash: str
    utterance_count: int
    intents: Mapping[str, SlurpIntentRowProfile]
    excluded_train_utterance_ids: tuple[str, ...] = ()

    @property
    def intent_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self.intents))

    def as_json(self) -> dict[str, object]:
        document: dict[str, object] = {
            "profile_id": self.profile_id,
            "source_split": self.source_split,
            "source_identity_hash": self.source_identity_hash,
            "utterance_count": self.utterance_count,
            "intents": [self.intents[intent].as_json() for intent in self.intent_ids],
        }
        if self.excluded_train_utterance_ids:
            document["excluded_train_utterance_ids"] = list(
                self.excluded_train_utterance_ids
            )
        return document

    def content_hash(self) -> str:
        return _canonical_sha256(self.as_json())


def load_slurp_train_utterance_ids(
    lock: Mapping[str, object], root: Path,
) -> tuple[str, ...]:
    """Every labelled governed TRAIN utterance id, sorted.

    The same split discipline as :func:`load_slurp_intent_slot_schema`: the one
    metadata file opened is named by a module constant, there is no ``split``
    parameter and no caller-supplied path. It exists so a construction builder
    can PROVE its retained pool is disjoint from a forbidden roster rather than
    assert it, without carrying any label, filler or media fact out of TRAIN.
    """

    split_id = _ROSTER_SPLITS_LEGAL[0]
    _, _, metadata_dir = _governed_roots(lock, root)
    metadata_path = metadata_dir / _SPLIT_FILES[split_id]
    if not metadata_path.is_file():
        raise LoaderError(f"SLURP split metadata file missing: {metadata_path}")
    utterance_ids: set[str] = set()
    for line_no, raw in enumerate(_read_jsonl(metadata_path), start=1):
        context = f"SLURP {split_id}.jsonl line {line_no}"
        scenario = raw.get("scenario")
        action = raw.get("action")
        if not isinstance(scenario, str) or not scenario:
            continue
        if not isinstance(action, str) or not action:
            continue
        utterance_ids.add(_train_utterance_id(raw, context))
    if not utterance_ids:
        raise LoaderError(
            f"SLURP {split_id} metadata {metadata_path} yielded no labelled utterance"
        )
    return tuple(sorted(utterance_ids))


def load_slurp_intent_row_profiles(
    lock: Mapping[str, object],
    root: Path,
    *,
    excluded_train_utterance_ids: Sequence[str] | None = None,
) -> SlurpIntentRowProfiles:
    """Mine the ROW-level per-intent profile from ``train.jsonl`` alone.

    Split discipline, determinism and exclusion semantics are exactly
    :func:`load_slurp_intent_slot_schema`'s -- the split file is named by a
    module constant, there is no ``split`` parameter and no caller-supplied
    path, exclusions are canonical utterance IDs validated before TRAIN is
    read and refused when unknown, and a row with an unusable ``tokens``
    block or a malformed entity still counts toward its intent's ``rows``.

    What differs is only the UNIT: this function counts utterances, so it can
    answer "what share of this intent's construction rows carry a ``date`` at
    all?" and "what share carry no entity at all?". The mention-unit table of
    :func:`load_slurp_intent_slot_schema` answers neither.
    """

    exclusions = normalize_slurp_train_utterance_exclusions(
        excluded_train_utterance_ids
    )
    exclusion_set = frozenset(exclusions)
    split_id = _ROSTER_SPLITS_LEGAL[0]
    _, _, metadata_dir = _governed_roots(lock, root)
    metadata_path = metadata_dir / _SPLIT_FILES[split_id]
    if not metadata_path.is_file():
        raise LoaderError(f"SLURP split metadata file missing: {metadata_path}")

    available_utterance_ids: set[str] = set()
    utterance_ids: set[str] = set()
    legal_intents: set[str] = set()
    rows_by_intent: dict[str, int] = {}
    rows_with_entity_by_intent: dict[str, int] = {}
    type_rows_by_intent: dict[str, dict[str, int]] = {}
    for line_no, raw in enumerate(_read_jsonl(metadata_path), start=1):
        context = f"SLURP {split_id}.jsonl line {line_no}"
        scenario = raw.get("scenario")
        action = raw.get("action")
        if not isinstance(scenario, str) or not scenario:
            continue
        if not isinstance(action, str) or not action:
            continue
        utterance_id = _train_utterance_id(raw, context)
        intent = f"{scenario}_{action}"
        available_utterance_ids.add(utterance_id)
        legal_intents.add(intent)
        if utterance_id in exclusion_set:
            continue
        utterance_ids.add(utterance_id)
        rows_by_intent[intent] = rows_by_intent.get(intent, 0) + 1
        rows_with_entity_by_intent.setdefault(intent, 0)
        type_rows_by_intent.setdefault(intent, {})
        try:
            tokens_by_id = _tokens_by_id(raw.get("tokens"), context)
        except LoaderError:
            continue
        raw_entities = raw.get("entities")
        if not isinstance(raw_entities, list):
            continue
        present: set[str] = set()
        for entity in raw_entities:
            if not isinstance(entity, Mapping):
                continue
            entity_type = entity.get("type")
            if not isinstance(entity_type, str) or not entity_type:
                continue
            try:
                _entity_filler(tokens_by_id, entity.get("span"), context)
            except LoaderError:
                continue
            present.add(entity_type)
        if not present:
            continue
        rows_with_entity_by_intent[intent] += 1
        counts = type_rows_by_intent[intent]
        for entity_type in present:
            counts[entity_type] = counts.get(entity_type, 0) + 1

    unknown_exclusions = sorted(exclusion_set - available_utterance_ids)
    if unknown_exclusions:
        raise LoaderError(
            "excluded_train_utterance_ids contains ID absent from governed TRAIN "
            f"metadata: {unknown_exclusions[0]}"
        )
    if not utterance_ids:
        raise LoaderError(
            f"SLURP {split_id} metadata {metadata_path} yielded no labelled utterance; "
            "refusing to build an empty row profile"
        )
    profiles = {
        intent: SlurpIntentRowProfile(
            intent=intent,
            rows=rows_by_intent.get(intent, 0),
            rows_with_entity=rows_with_entity_by_intent.get(intent, 0),
            type_rows=MappingProxyType(dict(type_rows_by_intent.get(intent, {}))),
        )
        for intent in sorted(legal_intents)
    }
    identity_hash = hashlib.sha256(
        "\n".join(sorted(utterance_ids)).encode("utf-8")
    ).hexdigest()
    return SlurpIntentRowProfiles(
        profile_id=SLURP_INTENT_ROW_PROFILE_ID,
        source_split=split_id,
        source_identity_hash=identity_hash,
        utterance_count=len(utterance_ids),
        intents=MappingProxyType(profiles),
        excluded_train_utterance_ids=exclusions,
    )


#: Identity of the per-utterance CONSTRUCTION TEXT pool
#: :func:`load_slurp_construction_utterances` mines (E14, 2026-09-19, owner
#: directive 26). Distinct from :data:`SLURP_INTENT_ROW_PROFILE_ID` because the
#: SHAPE differs: that reader returns per-intent aggregates, this one returns
#: one row per construction utterance, carrying its own tokens -- which is what
#: a neighbour-and-cue builder needs and what an aggregate cannot supply.
SLURP_CONSTRUCTION_TEXT_POOL_ID = "slurp-construction-text-pool-v1"


@dataclass(frozen=True)
class SlurpConstructionUtterance:
    """One construction utterance: its identity, its intent and its tokens.

    ``tokens`` are the governed annotation's own token surfaces, in the
    annotation's own ``id`` order, lower-cased and otherwise untouched -- no
    stemming, no stopword filtering and no de-duplication happen here. A row
    whose ``tokens`` block is unusable keeps an empty tuple rather than
    disappearing, exactly as :func:`load_slurp_intent_row_profiles` still
    counts it toward its intent's rows.
    """

    utterance_id: str
    slurp_id: int
    intent: str
    tokens: tuple[str, ...] = ()


@dataclass(frozen=True)
class SlurpConstructionTextPool:
    """Every retained construction utterance plus the identity of the pool."""

    pool_id: str
    source_split: str
    source_identity_hash: str
    utterance_count: int
    #: Sorted by ``utterance_id``, so the pool is a deterministic sequence.
    utterances: tuple[SlurpConstructionUtterance, ...]
    excluded_train_utterance_ids: tuple[str, ...] = ()

    @property
    def utterance_ids(self) -> tuple[str, ...]:
        return tuple(row.utterance_id for row in self.utterances)

    @property
    def intent_ids(self) -> tuple[str, ...]:
        return tuple(sorted({row.intent for row in self.utterances}))


def load_slurp_construction_utterances(
    lock: Mapping[str, object],
    root: Path,
    *,
    excluded_train_utterance_ids: Sequence[str] | None = None,
) -> SlurpConstructionTextPool:
    """Mine the per-utterance construction TEXT pool from ``train.jsonl`` alone.

    Split discipline, determinism and exclusion semantics are exactly
    :func:`load_slurp_intent_row_profiles`'s -- the split file is named by a
    module constant, there is no ``split`` parameter and no caller-supplied
    path, exclusions are canonical utterance IDs validated before TRAIN is read
    and refused when unknown -- and the identity hash is computed over the same
    retained id set, so a table built from this pool and a table built from
    that one bind the SAME ``source_identity_hash`` and can be cross-checked.

    It carries SENTENCE TOKENS, which is why it lives beside
    :func:`load_slurp_train_construction_rows` under the same one-reader
    discipline: a devel or test row cannot be reached through this entry point
    at all. It carries no entity annotation, no filler, no recording and no
    media fact -- a neighbour-and-cue builder needs the words and the label,
    and nothing else.
    """

    exclusions = normalize_slurp_train_utterance_exclusions(
        excluded_train_utterance_ids
    )
    exclusion_set = frozenset(exclusions)
    split_id = _ROSTER_SPLITS_LEGAL[0]
    _, _, metadata_dir = _governed_roots(lock, root)
    metadata_path = metadata_dir / _SPLIT_FILES[split_id]
    if not metadata_path.is_file():
        raise LoaderError(f"SLURP split metadata file missing: {metadata_path}")

    available_utterance_ids: set[str] = set()
    retained: dict[str, SlurpConstructionUtterance] = {}
    for line_no, raw in enumerate(_read_jsonl(metadata_path), start=1):
        context = f"SLURP {split_id}.jsonl line {line_no}"
        scenario = raw.get("scenario")
        action = raw.get("action")
        if not isinstance(scenario, str) or not scenario:
            continue
        if not isinstance(action, str) or not action:
            continue
        utterance_id = _train_utterance_id(raw, context)
        available_utterance_ids.add(utterance_id)
        if utterance_id in exclusion_set:
            continue
        if utterance_id in retained:
            raise LoaderError(
                f"{context}: SLURP TRAIN repeats utterance {utterance_id}"
            )
        try:
            tokens_by_id = _tokens_by_id(raw.get("tokens"), context)
        except LoaderError:
            tokens_by_id = {}
        tokens = tuple(
            str(tokens_by_id[token_id]).lower() for token_id in sorted(tokens_by_id)
        )
        retained[utterance_id] = SlurpConstructionUtterance(
            utterance_id=utterance_id,
            slurp_id=int(utterance_id.rsplit(":", 1)[1]),
            intent=f"{scenario}_{action}",
            tokens=tokens,
        )

    unknown_exclusions = sorted(exclusion_set - available_utterance_ids)
    if unknown_exclusions:
        raise LoaderError(
            "excluded_train_utterance_ids contains ID absent from governed TRAIN "
            f"metadata: {unknown_exclusions[0]}"
        )
    if not retained:
        raise LoaderError(
            f"SLURP {split_id} metadata {metadata_path} yielded no labelled utterance; "
            "refusing to build an empty construction text pool"
        )
    identity_hash = hashlib.sha256(
        "\n".join(sorted(retained)).encode("utf-8")
    ).hexdigest()
    return SlurpConstructionTextPool(
        pool_id=SLURP_CONSTRUCTION_TEXT_POOL_ID,
        source_split=split_id,
        source_identity_hash=identity_hash,
        utterance_count=len(retained),
        utterances=tuple(retained[key] for key in sorted(retained)),
        excluded_train_utterance_ids=exclusions,
    )


def load_slurp_train_construction_rows(
    lock: Mapping[str, object],
    root: Path,
    sample_ids: Sequence[str],
) -> dict[str, dict[str, object]]:
    """The construction material of EXACTLY the named TRAIN recordings.

    The SLURP twin of ``data.audio2tool.load_query_rows`` plus
    ``load_media_rows``, in one pass: per sample id, the intent, the sentence
    the speaker read, the gold ``(entity type, filler)`` pairs joined exactly
    as the official eval script joins them, and the three measured media facts
    a roster receipt records (``media_relpath``, ``audio_seconds``,
    ``audio_sha256``).

    Split discipline, the same as :func:`load_slurp_intent_slot_schema`'s:
    the one metadata file this function opens is named by
    ``_SPLIT_FILES[_ROSTER_SPLITS_LEGAL[0]]``, a module constant. There is no
    ``split`` parameter and no caller-supplied path, so a devel or test row
    cannot be reached through this entry point at all -- which is what makes
    it safe to be the one reader that carries SENTENCE TEXT beside gold. The
    EVO-S1 proposer arm is the single caller licensed to send that pair to the
    frozen core (owner decision 2026-09-05, construction rows only), and the
    rows it may send are exactly those a committed
    ``roster_role == "construction"`` receipt names.

    Identity-scoped rather than roster-scoped for the same reason its
    Audio2Tool twin is: the loop's exemplar pool sits outside every
    probe-sample receipt, so a receipt-scoped loader cannot see it.
    """

    if isinstance(sample_ids, (str, bytes)):
        raise LoaderError("sample_ids must be a sequence of SLURP sample ids")
    split_id = _ROSTER_SPLITS_LEGAL[0]
    wanted: dict[int, set[str]] = {}
    for sample_id in sample_ids:
        if not isinstance(sample_id, str):
            raise LoaderError("every sample id must be text")
        parts = sample_id.split(":", 3)
        if len(parts) != 4 or parts[0] != "slurp" or parts[1] != split_id:
            raise LoaderError(
                f"{sample_id!r} is not a SLURP {split_id} sample id of the shape "
                f"'slurp:{split_id}:<six digits>:<recording stem>'"
            )
        if not parts[2].isdigit() or len(parts[2]) != 6 or not parts[3]:
            raise LoaderError(
                f"{sample_id!r} is not a SLURP {split_id} sample id of the shape "
                f"'slurp:{split_id}:<six digits>:<recording stem>'"
            )
        wanted.setdefault(int(parts[2]), set()).add(parts[3])
    if not wanted:
        raise LoaderError("sample_ids must name at least one construction row")

    audio_root_relpath, audio_root, metadata_dir = _governed_roots(lock, root)
    metadata_path = metadata_dir / _SPLIT_FILES[split_id]
    if not metadata_path.is_file():
        raise LoaderError(f"SLURP {split_id} metadata file missing: {metadata_path}")
    audio_dir = audio_root / _AUDIO_SUBDIR_FOR_SPLIT[split_id]
    audio_dir_relpath = f"{audio_root_relpath}/{_AUDIO_SUBDIR_FOR_SPLIT[split_id]}"

    rows: dict[str, dict[str, object]] = {}
    for line_no, raw in enumerate(_read_jsonl(metadata_path), start=1):
        slurp_id = raw.get("slurp_id")
        if isinstance(slurp_id, bool) or not isinstance(slurp_id, int):
            raise LoaderError(f"SLURP {split_id}.jsonl line {line_no}: slurp_id must be an int")
        stems = wanted.get(slurp_id)
        if not stems:
            continue
        context = f"SLURP {split_id}.jsonl line {line_no}"
        scenario = raw.get("scenario")
        action = raw.get("action")
        sentence = raw.get("sentence")
        if not isinstance(scenario, str) or not scenario:
            raise LoaderError(f"{context}: scenario must be a non-empty string")
        if not isinstance(action, str) or not action:
            raise LoaderError(f"{context}: action must be a non-empty string")
        if not isinstance(sentence, str) or not sentence.strip():
            raise LoaderError(f"{context}: sentence must be a non-empty string")
        tokens_by_id = _tokens_by_id(raw.get("tokens"), context)
        raw_entities = raw.get("entities")
        if not isinstance(raw_entities, list):
            raise LoaderError(f"{context}: entities must be a list")
        entities = tuple(
            (
                _entity_type(entity, context),
                _entity_filler(
                    tokens_by_id,
                    entity.get("span") if isinstance(entity, Mapping) else None,
                    context,
                ),
            )
            for entity in raw_entities
        )
        recordings = raw.get("recordings")
        if not isinstance(recordings, list) or not recordings:
            raise LoaderError(f"{context}: recordings must be a non-empty list")
        for recording in recordings:
            if not isinstance(recording, Mapping):
                raise LoaderError(f"{context}: recording entry must be an object")
            filename = _validate_recording_filename(recording.get("file"), context)
            stem = filename[: -len(".flac")]
            if stem not in stems:
                continue
            media_path = audio_dir / filename
            rows[f"slurp:{split_id}:{slurp_id:06d}:{stem}"] = {
                "utterance_id": f"slurp:{split_id}:{slurp_id:06d}",
                "scenario": scenario,
                "action": action,
                "intent": f"{scenario}_{action}",
                "sentence": sentence.strip(),
                "entities": entities,
                "media_relpath": f"{audio_dir_relpath}/{filename}",
                "audio_seconds": _audio_seconds(media_path, context),
                "audio_sha256": hashlib.sha256(media_path.read_bytes()).hexdigest(),
            }
    missing = sorted(
        f"slurp:{split_id}:{slurp_id:06d}:{stem}"
        for slurp_id, stems in wanted.items()
        for stem in stems
        if f"slurp:{split_id}:{slurp_id:06d}:{stem}" not in rows
    )
    if missing:
        raise LoaderError(
            f"{len(missing)} construction row(s) have no {split_id} recording; first: "
            f"{missing[0]}"
        )
    return rows


__all__ = [
    "SLURP_CONSTRUCTION_TEXT_POOL_ID",
    "SLURP_INTENT_ROW_PROFILE_ID",
    "SLURP_INTENT_SLOT_DECONTAMINATION_RECEIPTS",
    "SLURP_INTENT_SLOT_SCHEMA_ID",
    "SLURP_INTENT_SLOT_SCHEMA_RECEIPT_SCHEMA",
    "SLURP_LOCK_KEY",
    "SlurpConstructionTextPool",
    "SlurpConstructionUtterance",
    "SlurpIntentRowProfile",
    "SlurpIntentRowProfiles",
    "SlurpIntentSlotSchema",
    "SlurpIntentSlots",
    "SlurpOntology",
    "SlurpRecord",
    "SlurpTrainMaterial",
    "SlurpTrainRecording",
    "load_slurp_construction_utterances",
    "load_slurp_intent_row_profiles",
    "load_slurp_intent_slot_schema",
    "load_slurp_train_utterance_ids",
    "load_slurp_ontology",
    "load_slurp_split",
    "load_slurp_train_construction_rows",
    "load_slurp_train_material",
    "normalize_slurp_train_utterance_exclusions",
    "render_slurp_closed_label_inventory",
    "render_slurp_closed_label_inventory_with_slot_schema",
    "render_slurp_intent_slot_schema",
    "render_slurp_label_inventory",
    "render_slurp_ontology",
    "render_slurp_slot_schema_for_state",
    "render_slurp_slot_schema_for_state_detail",
    "slurp_intent_from_state_content",
    "slurp_intent_slot_schema_receipt",
]
