"""I-4 (external-threat-model review): media identity re-verified AS A FILE,
never merely as a claim, at model-touch time.

``contracts.FrozenCoreGate.verify_media_identity`` re-hashes exactly the
samples a run's verified split can touch against D1's own frozen per-sample
media facts (``docs/receipts/artifacts/d1-identity.json``), and sanity-checks
the loader-reported ``audio_seconds`` against that same frozen byte size for
MP3-bitrate plausibility -- see the method's own docstring and
``docs/owner-decisions-pending.md`` item 4 for exactly what is and is not
bound.
"""

import hashlib
import json
from dataclasses import replace

import pytest

from speech_aware_evidence_acquisition.contracts import GateClosed

from gate_fixture import GateFixture


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


SAMPLE_ID = "4320211"
MEDIA_BYTES = b"real-earnings21-media-bytes-fixture" * 100
MEDIA_RELPATH = f"datasets/earnings21-22/earnings21/media/{SAMPLE_ID}.mp3"
# 32 kbps: comfortably inside the plausible band and close to the real
# earnings21/earnings22 median bitrate observed in docs/owner-decisions-pending.md.
PLAUSIBLE_SECONDS = (len(MEDIA_BYTES) * 8 / 1000.0) / 32.0


def _d1_document(carrier_lock_key: str) -> dict:
    return {
        "carriers": {
            carrier_lock_key: {
                "layers": {
                    "media": {
                        "manifest": [
                            {
                                "id": SAMPLE_ID,
                                "bytes": len(MEDIA_BYTES),
                                "sha256": _sha(MEDIA_BYTES),
                            }
                        ]
                    }
                }
            }
        }
    }


@pytest.fixture()
def world(tmp_path):
    fixture = GateFixture(tmp_path)
    d1_bytes = json.dumps(_d1_document(fixture.CARRIER)).encode("utf-8")
    (fixture.receipts / "e0" / "d1_identity.json").write_bytes(d1_bytes)
    fixture.deliverables["d1_identity"]["sha256"] = _sha(d1_bytes)
    media_dir = fixture.data_root / "datasets" / "earnings21-22" / "earnings21" / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    (media_dir / f"{SAMPLE_ID}.mp3").write_bytes(MEDIA_BYTES)
    return fixture


def _media_facts(audio_seconds: float) -> dict:
    return {SAMPLE_ID: (MEDIA_RELPATH, audio_seconds)}


def test_unmodified_media_and_plausible_seconds_pass(world):
    gate = world.gate()
    gate.verify_media_identity(world.CARRIER, _media_facts(PLAUSIBLE_SECONDS))


def test_replaced_media_bytes_are_refused(world):
    """Probe: replace one media file's bytes for a sample in the run's split."""

    media = (
        world.data_root
        / "datasets"
        / "earnings21-22"
        / "earnings21"
        / "media"
        / f"{SAMPLE_ID}.mp3"
    )
    media.write_bytes(b"tampered-bytes-not-the-original-media-at-all")
    gate = world.gate()
    with pytest.raises(GateClosed, match="media identity drift"):
        gate.verify_media_identity(world.CARRIER, _media_facts(PLAUSIBLE_SECONDS))


def test_deflated_audio_seconds_csv_edit_is_refused(world):
    """Probe: the demonstrated attack -- a metadata cell edited so real,
    metered audio reads as (near) zero seconds -- implies an astronomically
    high bitrate against the frozen media size and is refused."""

    gate = world.gate()
    with pytest.raises(GateClosed, match="plausible MP3 bitrate"):
        gate.verify_media_identity(world.CARRIER, _media_facts(0.001))


def test_inflated_audio_seconds_csv_edit_is_refused(world):
    gate = world.gate()
    with pytest.raises(GateClosed, match="plausible MP3 bitrate"):
        gate.verify_media_identity(world.CARRIER, _media_facts(10_000_000.0))


def test_sample_outside_d1_closure_is_refused(world):
    gate = world.gate()
    relpath = "datasets/earnings21-22/earnings21/media/9999999.mp3"
    media = world.data_root / relpath
    media.parent.mkdir(parents=True, exist_ok=True)
    media.write_bytes(b"a-sample-d1-never-closed-over")
    with pytest.raises(GateClosed, match="no D1-recorded media identity"):
        gate.verify_media_identity(world.CARRIER, {"9999999": (relpath, 100.0)})


def _supplemented_gate(world, *, parent_hash=None, recorded_relpath=None):
    sample_id = "supplemented-train-sample"
    relpath = recorded_relpath or "datasets/extra/train.flac"
    raw = b"bounded-train-speech" * 100
    media = world.data_root / "datasets/extra/train.flac"
    media.parent.mkdir(parents=True, exist_ok=True)
    media.write_bytes(raw)
    d1_path = world.receipts / "e0" / "d1_identity.json"
    manifest = [
        {
            "id": sample_id,
            "media_relpath": relpath,
            "bytes": len(raw),
            "sha256": _sha(raw),
            "audio_seconds": 1.25,
            "sample_rate_hz": 16000,
            "roles": ["query"],
        }
    ]
    canonical_manifest = json.dumps(
        manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    supplement = {
        "schema": "saea-d1-media-supplement-v1",
        "study": "speech-aware-evidence-acquisition",
        "carrier_lock_key": world.CARRIER,
        "parent_d1_sha256": parent_hash or _sha(d1_path.read_bytes()),
        "source_binding_sha256": "a" * 64,
        "count": 1,
        "ids_sha256": _sha(sample_id.encode("utf-8")),
        "manifest": manifest,
        "manifest_sha256": _sha(canonical_manifest),
        "total_bytes": len(raw),
    }
    path = world.receipts / "d1-media-supplement.json"
    path.write_text(json.dumps(supplement), encoding="utf-8")
    return replace(
        world.gate(),
        d1_media_supplement=path,
        d1_media_supplement_sha256=_sha(path.read_bytes()),
    ), sample_id


def test_d1_media_supplement_admits_only_its_exact_media_and_duration(world):
    gate, sample_id = _supplemented_gate(world)
    gate.verify_media_identity(
        world.CARRIER,
        {sample_id: ("datasets/extra/train.flac", 1.25)},
    )
    with pytest.raises(GateClosed, match="recorded duration"):
        gate.verify_media_identity(
            world.CARRIER,
            {sample_id: ("datasets/extra/train.flac", 1.0)},
        )


def test_d1_media_supplement_is_bound_to_parent_d1_and_media_path(world):
    gate, sample_id = _supplemented_gate(world, parent_hash="f" * 64)
    with pytest.raises(GateClosed, match="parent D1"):
        gate.verify_media_identity(
            world.CARRIER,
            {sample_id: ("datasets/extra/train.flac", 1.25)},
        )
    gate, sample_id = _supplemented_gate(
        world, recorded_relpath="datasets/extra/different.flac"
    )
    with pytest.raises(GateClosed, match="media_relpath"):
        gate.verify_media_identity(
            world.CARRIER,
            {sample_id: ("datasets/extra/train.flac", 1.25)},
        )


def test_conec_carrier_resolves_to_earnings21_media_identity(world):
    """D1: conec.canonical_identity == "earnings21-original media" -- conec
    carries no media of its own."""

    gate = world.gate()
    gate.verify_media_identity("conec", _media_facts(PLAUSIBLE_SECONDS))


def test_empty_media_facts_refused(world):
    gate = world.gate()
    with pytest.raises(GateClosed, match="non-empty"):
        gate.verify_media_identity(world.CARRIER, {})
