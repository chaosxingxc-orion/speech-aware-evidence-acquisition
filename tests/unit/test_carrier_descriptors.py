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

import pytest

from speech_aware_evidence_acquisition.core import carriers as _register_core_carriers  # noqa: F401
from speech_aware_evidence_acquisition.core.base import CARRIERS
from speech_aware_evidence_acquisition.data.carriers import (
    CarrierDescriptor,
    CarrierDescriptorError,
    MetadataColumns,
    ReferenceLayout,
    get_carrier_descriptor,
    reference_scoped_carrier_lock_keys,
    register_carrier_descriptor,
)
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.data.loader import load_carrier
from speech_aware_evidence_acquisition.data.references import reference_tokens
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
