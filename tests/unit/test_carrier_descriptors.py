"""``data.carriers.CarrierDescriptor``: one descriptor, no per-module editing.

R0 repair refactor stage 2 (part B): before this module existed, adding a
carrier meant editing ``data/loader.py`` (media subdir/extension, metadata
filename, metadata column names), ``data/references.py`` (a carrier ->
reference-subdir mapping), ``core/evidence.py`` (a hardcoded ConEC context
path), and ``contracts/gate_identity.py`` (a hand-maintained reference-scoped
carrier set) -- four places, independently.

The tests below build a THIRD carrier -- one this repository's production
code has never heard of, with its own media extension, metadata column
names, and reference-file extension, none of which match either of the two
built-in carriers -- purely from a :class:`~speech_aware_evidence_acquisition
.data.carriers.CarrierDescriptor`, and load/score it through the SAME,
completely unmodified ``data.loader``/``data.references``/``core.scorers``
machinery the two built-in carriers use. No loader/reference/evidence/gate
module is touched to make this carrier work.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core import carriers as _register_core_carriers  # noqa: F401
from speech_aware_evidence_acquisition.core.base import CARRIERS
from speech_aware_evidence_acquisition.data.carriers import (
    AUDIO2TOOL,
    SLURP,
    CarrierDescriptor,
    CarrierDescriptorError,
    EntityLayout,
    EvidenceLayout,
    MetadataColumns,
    ReferenceLayout,
    TaskLayout,
    carrier_task_layout,
    get_carrier_descriptor,
    reference_scoped_carrier_lock_keys,
    register_carrier_descriptor,
    resolve_media_identity_carrier,
    task_scoped_carrier_lock_keys,
)
from speech_aware_evidence_acquisition.data.audio2tool import AUDIO2TOOL_LOCK_KEY
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.data.loader import LoaderError, load_carrier
from speech_aware_evidence_acquisition.data.references import reference_tokens
from speech_aware_evidence_acquisition.data.slurp import SLURP_LOCK_KEY
from speech_aware_evidence_acquisition.core.scorers import score_asr_outputs

_LOCK_KEY = "synthetic-lecture-original"
_IDS = ("lec-001", "lec-002")


@pytest.fixture()
def synthetic_carrier_world(tmp_path):
    """A THIRD carrier's media/metadata/reference layout, built with column
    names, a media extension, and a reference extension that match NEITHER
    Earnings21 nor Earnings22 -- so a test passing only because the loader
    happens to reuse a built-in's column name is structurally impossible."""

    data_root = tmp_path / "speechrl-data"
    carrier_dir = data_root / "datasets" / "synthetic-lecture"
    for sample_id, seconds, hz in zip(_IDS, (12.5, 30.0), (16000, 22050)):
        (carrier_dir / "audio" / f"{sample_id}.flac").parent.mkdir(parents=True, exist_ok=True)
        (carrier_dir / "audio" / f"{sample_id}.flac").write_text(f"fake-audio-{sample_id}", encoding="utf-8")
        ref_path = carrier_dir / "text" / "refs" / f"{sample_id}.ref"
        ref_path.parent.mkdir(parents=True, exist_ok=True)
        ref_path.write_text("token|tags\nHELLO|\nWORLD|\n", encoding="utf-8")
    metadata = carrier_dir / "lecture-meta.csv"
    metadata.write_text(
        "clip_id,seconds,hz\n"
        + "\n".join(
            f"{sample_id},{seconds},{hz}"
            for sample_id, seconds, hz in zip(_IDS, (12.5, 30.0), (16000, 22050))
        )
        + "\n",
        encoding="utf-8",
    )
    lock_path = tmp_path / "datasets.lock.json"
    lock_path.write_text(
        json.dumps(
            {
                "datasets": [
                    {
                        "name": _LOCK_KEY,
                        "kind": "dataset",
                        "local_subdir": "datasets/synthetic-lecture",
                        "profiles": ["speech-aware-core"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return data_root, lock_path


@pytest.fixture()
def synthetic_descriptor():
    """Registered fresh per test (module-global registry) so a prior test's
    registration never leaks into another; ``register_carrier_descriptor``
    itself refuses a duplicate key, which is exactly the guarantee this
    fixture's teardown protects."""

    descriptor = CarrierDescriptor(
        lock_key=_LOCK_KEY,
        media_subdir="audio",
        media_extension=".flac",
        metadata_filename="lecture-meta.csv",
        metadata_columns=MetadataColumns(
            id_column="clip_id", duration_column="seconds", sample_rate_column="hz"
        ),
        reference=ReferenceLayout(subdir="text/refs", extension=".ref"),
        evidence=None,
    )
    register_carrier_descriptor(descriptor)
    try:
        yield descriptor
    finally:
        from speech_aware_evidence_acquisition.data import carriers as _carriers_module

        _carriers_module._REGISTRY.pop(_LOCK_KEY, None)
        if _LOCK_KEY in CARRIERS._entries:
            del CARRIERS._entries[_LOCK_KEY]


def test_get_carrier_descriptor_round_trips(synthetic_descriptor):
    assert get_carrier_descriptor(_LOCK_KEY) is synthetic_descriptor


def test_unregistered_carrier_fails_closed():
    with pytest.raises(CarrierDescriptorError, match="no carrier descriptor registered"):
        get_carrier_descriptor("never-registered-carrier")


def test_duplicate_registration_refused(synthetic_descriptor):
    with pytest.raises(CarrierDescriptorError, match="already registered"):
        register_carrier_descriptor(synthetic_descriptor)


def test_reference_scoped_carrier_lock_keys_includes_the_new_carrier(synthetic_descriptor):
    assert _LOCK_KEY in reference_scoped_carrier_lock_keys()


def test_synthetic_carrier_loads_through_the_unmodified_generic_loader(
    synthetic_carrier_world, synthetic_descriptor
):
    data_root, lock_path = synthetic_carrier_world
    lock = load_lock(lock_path)
    samples = load_carrier(synthetic_descriptor, lock, data_root)
    assert [s.sample_id for s in samples] == sorted(_IDS)
    first = samples[0]
    assert first.carrier_lock_key == _LOCK_KEY
    assert first.media_relpath == "datasets/synthetic-lecture/audio/lec-001.flac"
    assert first.audio_seconds == 12.5
    assert first.sample_rate_hz == 16000


def test_synthetic_carrier_loads_through_a_registered_carriers_loader(
    synthetic_carrier_world, synthetic_descriptor
):
    """The realistic production path: register ONE lambda loader for the new
    descriptor (mirroring ``core/carriers.py``'s own registration pattern for
    the two built-ins), then resolve/call it exactly the way
    ``core.driver.run_experiment`` resolves every carrier's loader -- no new
    carrier-specific wiring anywhere else."""

    data_root, lock_path = synthetic_carrier_world
    CARRIERS.register(
        _LOCK_KEY, lambda lock, root, d=synthetic_descriptor: load_carrier(d, lock, root)
    )
    lock = load_lock(lock_path)
    samples = CARRIERS.resolve(_LOCK_KEY)(lock, data_root)
    assert len(samples) == 2


def test_synthetic_carrier_reference_tokens_resolve_through_the_descriptor(
    synthetic_carrier_world, synthetic_descriptor
):
    data_root, lock_path = synthetic_carrier_world
    lock = load_lock(lock_path)
    tokens = reference_tokens(lock, data_root, _LOCK_KEY, "lec-001")
    assert tokens == ["HELLO", "WORLD"]


# ---------------------------------------------------------------------------
# MINOR 2 (external-threat-model review round 4): the "conec" media-identity
# alias is now registry-driven (media_identity_aliases /
# resolve_media_identity_carrier), not a hand-coded ternary at the gate call
# site.
# ---------------------------------------------------------------------------


def test_earnings21_original_declares_the_conec_media_identity_alias():
    descriptor = get_carrier_descriptor("earnings21-original")
    assert "conec" in descriptor.media_identity_aliases


def test_resolve_media_identity_carrier_aliases_conec_to_earnings21_original():
    assert resolve_media_identity_carrier("conec") == "earnings21-original"


def test_resolve_media_identity_carrier_is_identity_for_an_unaliased_key():
    assert resolve_media_identity_carrier("earnings22-original") == "earnings22-original"
    assert resolve_media_identity_carrier("never-heard-of-this-one") == "never-heard-of-this-one"


def test_evidence_layout_d1_layer_key_is_explicit_and_not_derived_from_subdir():
    """D1 records ConEC's context layer as "e21_contexts" -- not derivable
    from EvidenceLayout.subdir ("earnings21/contexts") by any fixed rule, so
    it must be its own explicit field."""

    descriptor = get_carrier_descriptor("earnings21-original")
    assert descriptor.evidence.d1_layer_key == "e21_contexts"
    assert descriptor.evidence.subdir != descriptor.evidence.d1_layer_key


def test_a_new_carrier_can_register_its_own_media_identity_alias():
    """A THIRD carrier, mirroring this file's own synthetic_descriptor
    pattern: register_carrier_descriptor threads media_identity_aliases into
    the SAME registry-driven index the built-in earnings21-original/conec
    pairing uses -- no gate-side special case needed for a new carrier
    either."""

    alias_key = "synthetic-lecture-alt-identity"
    descriptor = CarrierDescriptor(
        lock_key=_LOCK_KEY,
        media_subdir="audio",
        media_extension=".flac",
        metadata_filename="lecture-meta.csv",
        metadata_columns=MetadataColumns(
            id_column="clip_id", duration_column="seconds", sample_rate_column="hz"
        ),
        media_identity_aliases=frozenset({alias_key}),
    )
    register_carrier_descriptor(descriptor)
    try:
        assert resolve_media_identity_carrier(alias_key) == _LOCK_KEY
    finally:
        from speech_aware_evidence_acquisition.data import carriers as _carriers_module

        _carriers_module._REGISTRY.pop(_LOCK_KEY, None)
        _carriers_module._MEDIA_IDENTITY_ALIAS_INDEX.pop(alias_key, None)


def test_duplicate_media_identity_alias_registration_refused(synthetic_descriptor):
    colliding = CarrierDescriptor(
        lock_key="another-synthetic-carrier",
        media_subdir="audio",
        media_extension=".flac",
        metadata_filename="lecture-meta.csv",
        metadata_columns=MetadataColumns(
            id_column="clip_id", duration_column="seconds", sample_rate_column="hz"
        ),
        media_identity_aliases=frozenset({_LOCK_KEY}),  # collides with a registered carrier
    )
    with pytest.raises(CarrierDescriptorError, match="collides"):
        register_carrier_descriptor(colliding)


# ---------------------------------------------------------------------------
# MINOR (fifth external-threat-model review): the alias-collision check was
# previously one-directional -- an ALIAS colliding with an existing lock key
# was refused (test above), but registering a real CarrierDescriptor whose
# OWN lock_key equalled an already-registered ALIAS succeeded silently, and
# resolve_media_identity_carrier then redirected that carrier's whole
# media-identity rail to the ALIASING carrier's D1 media layer with no
# signal. Both directions are probed here so the symmetry is pinned.
# ---------------------------------------------------------------------------


def test_alias_registration_refused_when_it_collides_with_a_lock_key_direction_one(
    synthetic_descriptor,
):
    """Direction 1 (pre-existing): a NEW alias colliding with an
    already-registered carrier lock key is refused."""

    colliding = CarrierDescriptor(
        lock_key="another-synthetic-carrier",
        media_subdir="audio",
        media_extension=".flac",
        metadata_filename="lecture-meta.csv",
        metadata_columns=MetadataColumns(
            id_column="clip_id", duration_column="seconds", sample_rate_column="hz"
        ),
        media_identity_aliases=frozenset({_LOCK_KEY}),
    )
    with pytest.raises(CarrierDescriptorError, match="collides"):
        register_carrier_descriptor(colliding)


def test_lock_key_registration_refused_when_it_collides_with_an_existing_alias_direction_two():
    """Direction 2 (the fix): registering a REAL carrier under a lock key an
    earlier descriptor already declared as its own media-identity alias must
    be refused too -- demonstrated exactly as the review reported it:
    "zz-future-carrier" registered as an alias first, then a second
    descriptor tries to claim "zz-future-carrier" as its own lock key."""

    aliaser = CarrierDescriptor(
        lock_key="zz-owner-carrier",
        media_subdir="audio",
        media_extension=".flac",
        metadata_filename="owner-meta.csv",
        metadata_columns=MetadataColumns(
            id_column="clip_id", duration_column="seconds", sample_rate_column="hz"
        ),
        media_identity_aliases=frozenset({"zz-future-carrier"}),
    )
    register_carrier_descriptor(aliaser)
    try:
        colliding = CarrierDescriptor(
            lock_key="zz-future-carrier",
            media_subdir="audio",
            media_extension=".flac",
            metadata_filename="future-meta.csv",
            metadata_columns=MetadataColumns(
                id_column="clip_id", duration_column="seconds", sample_rate_column="hz"
            ),
        )
        with pytest.raises(CarrierDescriptorError, match="collides"):
            register_carrier_descriptor(colliding)
        # Before the fix this succeeded silently and resolve_media_identity_carrier
        # kept redirecting "zz-future-carrier" to "zz-owner-carrier" -- confirm the
        # refusal above actually prevented that redirection from ever being set up.
        assert resolve_media_identity_carrier("zz-future-carrier") == "zz-owner-carrier"
    finally:
        from speech_aware_evidence_acquisition.data import carriers as _carriers_module

        _carriers_module._REGISTRY.pop("zz-owner-carrier", None)
        _carriers_module._MEDIA_IDENTITY_ALIAS_INDEX.pop("zz-future-carrier", None)


def test_synthetic_carrier_scores_through_the_unmodified_scoring_machinery(
    synthetic_carrier_world, synthetic_descriptor, tmp_path
):
    """Proves the descriptor reaches all the way through
    ``core.scorers.score_asr_outputs`` -- the SAME registered ``asr-wer``
    scorer every real carrier's outputs are scored with -- without that
    module (or ``data.references``) ever naming this carrier."""

    data_root, lock_path = synthetic_carrier_world
    lock = load_lock(lock_path)
    outputs_path = tmp_path / "synthetic.outputs.jsonl"
    outputs_path.write_text(
        json.dumps(
            {
                "sample_id": "lec-001",
                "carrier_lock_key": _LOCK_KEY,
                "text": "HELLO WORLD",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    result = score_asr_outputs(outputs_path, lock, data_root)
    assert result["aggregate"]["samples"] == 1
    assert result["per_sample"][0]["wer"] == 0.0


# ---------------------------------------------------------------------------
# Consolidation slice C1 ("one carrier registry"): TaskLayout, the optional
# metadata layer, and the two new receipt/governed-metadata carriers
# (audio2tool, slurp) registered at data.carriers import time.
# ---------------------------------------------------------------------------


def test_audio2tool_lock_key_matches_the_canonical_loader_constant():
    """The literal ``"audio2tool"`` quoted in data.carriers (module docstring's
    own "quoted literally, not imported" note) must never silently drift from
    ``data.audio2tool.AUDIO2TOOL_LOCK_KEY``."""

    assert AUDIO2TOOL.lock_key == AUDIO2TOOL_LOCK_KEY


def test_slurp_lock_key_matches_the_canonical_loader_constant():
    assert SLURP.lock_key == SLURP_LOCK_KEY


def test_audio2tool_descriptor_has_no_metadata_reference_evidence_entity_layer():
    assert AUDIO2TOOL.metadata_filename is None
    assert AUDIO2TOOL.metadata_columns is None
    assert AUDIO2TOOL.reference is None
    assert AUDIO2TOOL.evidence is None
    assert AUDIO2TOOL.entity is None


def test_slurp_descriptor_has_no_metadata_reference_evidence_entity_layer():
    assert SLURP.metadata_filename is None
    assert SLURP.metadata_columns is None
    assert SLURP.reference is None
    assert SLURP.evidence is None
    assert SLURP.entity is None


def test_audio2tool_task_layout_is_the_official_scorer_binding():
    layout = carrier_task_layout(AUDIO2TOOL_LOCK_KEY)
    assert layout == TaskLayout(
        task_kind="speech-tool-use",
        official_scorer_id="a2t-toolcall",
        knowledge_layer="tool-registry",
        stratum_key="tier",
    )


def test_slurp_task_layout_is_the_official_scorer_binding():
    layout = carrier_task_layout(SLURP_LOCK_KEY)
    assert layout == TaskLayout(
        task_kind="slot-slu",
        official_scorer_id="slurp-slu",
        knowledge_layer="train-ontology",
        stratum_key="scenario",
    )


def test_task_scoped_carrier_lock_keys_is_exactly_audio2tool_slurp_and_earnings21():
    # Item E35 (owner decision 89, 2026-09-21) adds earnings21-original's
    # contextual-asr TaskLayout; earnings22-original still declares none.
    assert task_scoped_carrier_lock_keys() == frozenset(
        {AUDIO2TOOL_LOCK_KEY, SLURP_LOCK_KEY, "earnings21-original"}
    )


def test_task_scoped_carrier_lock_keys_excludes_earnings22_only():
    scoped = task_scoped_carrier_lock_keys()
    assert "earnings21-original" in scoped
    assert "earnings22-original" not in scoped


def test_earnings21_task_layout_is_the_contextual_asr_binding():
    layout = carrier_task_layout("earnings21-original")
    assert layout == TaskLayout(
        task_kind="contextual-asr",
        official_scorer_id="asr-wer-whisper",
        knowledge_layer="conec-contexts",
        stratum_key="file_id",
    )


def test_carrier_task_layout_refuses_a_carrier_with_no_task_layer():
    with pytest.raises(CarrierDescriptorError, match="declares no task layer"):
        carrier_task_layout("earnings22-original")


def test_carrier_task_layout_refuses_an_unregistered_carrier():
    with pytest.raises(CarrierDescriptorError, match="no carrier descriptor registered"):
        carrier_task_layout("never-registered-carrier")


def test_earnings22_descriptor_declares_no_task_layer():
    assert get_carrier_descriptor("earnings22-original").task is None


def test_earnings21_descriptor_declares_a_task_layer():
    assert get_carrier_descriptor("earnings21-original").task is not None


# ---------------------------------------------------------------------------
# The two earnings descriptors' full field values, frozen here so a future
# edit to data.carriers cannot silently change either built-in carrier's
# layout facts while adding the C1 fields above.
# ---------------------------------------------------------------------------


def test_earnings21_original_descriptor_fields_are_unchanged():
    # Item E35 (owner decision 89, 2026-09-21) adds ONLY the ``task`` field
    # (a TaskLayout) -- every other field is byte-identical to the pre-E35
    # descriptor; see test_earnings21_task_layout_is_the_contextual_asr_
    # binding above for the task field's own dedicated assertion.
    descriptor = get_carrier_descriptor("earnings21-original")
    assert descriptor == CarrierDescriptor(
        lock_key="earnings21-original",
        media_subdir="media",
        media_extension=".mp3",
        metadata_filename="earnings21-file-metadata.csv",
        metadata_columns=MetadataColumns(
            id_column="file_id",
            duration_column="audio_length",
            sample_rate_column="sample_rate",
        ),
        reference=ReferenceLayout(subdir="transcripts/nlp_references", extension=".nlp"),
        evidence=EvidenceLayout(
            lock_key="conec",
            subdir="earnings21/contexts",
            extension=".txt",
            d1_layer_key="e21_contexts",
        ),
        media_identity_aliases=frozenset({"conec"}),
        entity=EntityLayout(subdir="transcripts/wer_tags", extension=".wer_tag.json"),
        task=TaskLayout(
            task_kind="contextual-asr",
            official_scorer_id="asr-wer-whisper",
            knowledge_layer="conec-contexts",
            stratum_key="file_id",
        ),
    )


def test_earnings22_original_descriptor_fields_are_unchanged():
    descriptor = get_carrier_descriptor("earnings22-original")
    assert descriptor == CarrierDescriptor(
        lock_key="earnings22-original",
        media_subdir="media",
        media_extension=".mp3",
        metadata_filename="metadata.csv",
        metadata_columns=MetadataColumns(
            id_column="File ID",
            duration_column="File Length (seconds)",
            sample_rate_column="Sampling Rate (Hz)",
        ),
        reference=ReferenceLayout(subdir="transcripts/nlp_references", extension=".nlp"),
        evidence=None,
        media_identity_aliases=frozenset(),
        entity=None,
        task=None,
    )


def test_load_carrier_refuses_a_descriptor_with_no_metadata_layer():
    """The one-line fail-closed guard added to ``data.loader.load_carrier``:
    a descriptor whose sample universe is receipt/governed-metadata-scoped
    (no per-carrier metadata CSV) must never fall through to a bare
    ``TypeError`` from ``Path / None``."""

    lock = {
        "datasets": [
            {
                "name": AUDIO2TOOL_LOCK_KEY,
                "kind": "dataset",
                "local_subdir": "datasets/audio2tool",
                "profiles": ["speech-aware-core"],
            }
        ]
    }
    with pytest.raises(LoaderError, match="declares no metadata layer"):
        load_carrier(AUDIO2TOOL, lock, Path("/nonexistent"))
