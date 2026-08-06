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


def test_conec_carrier_resolves_to_earnings21_media_identity(world):
    """D1: conec.canonical_identity == "earnings21-original media" -- conec
    carries no media of its own."""

    gate = world.gate()
    gate.verify_media_identity("conec", _media_facts(PLAUSIBLE_SECONDS))


def test_empty_media_facts_refused(world):
    gate = world.gate()
    with pytest.raises(GateClosed, match="non-empty"):
        gate.verify_media_identity(world.CARRIER, {})
