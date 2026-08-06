"""IMPORTANT 2 (external-threat-model review round 3): reference identity
re-verified AS A FILE, never merely trusted via a bare ``read_text()`` claim.

``contracts.FrozenCoreGate.verify_reference_identity`` re-hashes exactly the
samples a bundle's own verified split can touch against D1's own frozen
per-sample reference-layer facts (``docs/receipts/artifacts/d1-identity.json``,
``nlp_references`` layer) -- the reference-layer counterpart to
``verify_media_identity`` (I-4). Every formal WER is
``f(frozen scoring code, hypothesis text, reference bytes)``; before this,
only the first two were pinned.
"""

import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.contracts import GateClosed

from gate_fixture import GateFixture


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


SAMPLE_ID = "4320211"
REFERENCE_BYTES = b"token|tags\nhello|\nworld|\n"
REFERENCE_RELPATH = (
    f"datasets/earnings21-22/earnings21/transcripts/nlp_references/{SAMPLE_ID}.nlp"
)


def _d1_document(carrier_lock_key: str) -> dict:
    return {
        "carriers": {
            carrier_lock_key: {
                "layers": {
                    "nlp_references": {
                        "manifest": [
                            {
                                "id": SAMPLE_ID,
                                "bytes": len(REFERENCE_BYTES),
                                "sha256": _sha(REFERENCE_BYTES),
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
    ref_dir = (
        fixture.data_root
        / "datasets"
        / "earnings21-22"
        / "earnings21"
        / "transcripts"
        / "nlp_references"
    )
    ref_dir.mkdir(parents=True, exist_ok=True)
    (ref_dir / f"{SAMPLE_ID}.nlp").write_bytes(REFERENCE_BYTES)
    return fixture


def _reference_facts() -> dict:
    return {SAMPLE_ID: REFERENCE_RELPATH}


def test_unmodified_reference_bytes_pass(world):
    gate = world.gate()
    gate.verify_reference_identity(world.CARRIER, _reference_facts())


def test_tampered_reference_bytes_are_refused(world):
    """Probe: garbage hypothesis scored against a tampered reference file
    must never silently pass -- the demonstrated defect (gate PASSED,
    tampered reference, garbage hypothesis -> mean_wer=0.0)."""

    ref = world.data_root / REFERENCE_RELPATH
    ref.write_bytes(b"tampered-bytes-not-the-original-reference-at-all")
    gate = world.gate()
    with pytest.raises(GateClosed, match="reference identity drift"):
        gate.verify_reference_identity(world.CARRIER, _reference_facts())


def test_missing_reference_file_is_refused(world):
    """Probe: an interrupted asset fetch or a wrong SPEECHRL_DATA_DIR
    produces the identical symptom as a deliberate substitution -- both
    must refuse, naming the file."""

    ref = world.data_root / REFERENCE_RELPATH
    ref.unlink()
    gate = world.gate()
    with pytest.raises(GateClosed, match="does not exist"):
        gate.verify_reference_identity(world.CARRIER, _reference_facts())


def test_sample_outside_d1_closure_is_refused(world):
    gate = world.gate()
    relpath = (
        "datasets/earnings21-22/earnings21/transcripts/nlp_references/9999999.nlp"
    )
    ref = world.data_root / relpath
    ref.parent.mkdir(parents=True, exist_ok=True)
    ref.write_bytes(b"a-sample-d1-never-closed-over")
    with pytest.raises(GateClosed, match="no D1-recorded reference identity"):
        gate.verify_reference_identity(world.CARRIER, {"9999999": relpath})


def test_carrier_outside_the_reference_scoped_set_is_refused(world):
    """conec has no reference layer ``data.references.reference_tokens`` can
    read at all (its D1 identity layer is a DIFFERENT key,
    ``e21_nlp_references``, with differently-hashed bytes); this method must
    refuse it too rather than silently reusing earnings21's facts."""

    gate = world.gate()
    with pytest.raises(GateClosed, match="no D1-recorded reference-layer identity"):
        gate.verify_reference_identity("conec", _reference_facts())


def test_empty_reference_facts_refused(world):
    gate = world.gate()
    with pytest.raises(GateClosed, match="non-empty"):
        gate.verify_reference_identity(world.CARRIER, {})


def test_traversal_relpath_is_refused(world):
    gate = world.gate()
    with pytest.raises(GateClosed):
        gate.verify_reference_identity(world.CARRIER, {SAMPLE_ID: "../../etc/passwd"})
