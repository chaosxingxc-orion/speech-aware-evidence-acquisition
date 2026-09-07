"""IMPORTANT 1 (external-threat-model review round 4): evidence identity
re-verified AS A FILE, never merely trusted via a self-computed
``sha256_file()`` claim.

``contracts.FrozenCoreGate.verify_evidence_identity`` re-hashes exactly the
samples a run's own evidence source supplied non-empty evidence for against
D1's own frozen per-sample evidence-layer facts
(``docs/receipts/artifacts/d1-identity.json``, ``conec.layers.e21_contexts``)
-- the third identity rail, alongside ``verify_media_identity`` (I-4) and
``verify_reference_identity`` (IMPORTANT 2, round 3). Before this rail
existed, ``core.evidence._conec_contexts`` computed ``sha256_file(path)``
from whatever was on disk and stored that as its own provenance: a tampered
context byte returned normally with a fresh, self-consistent hash and no
refusal.
"""

import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.contracts import GateClosed

from gate_fixture import GateFixture


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


SAMPLE_ID = "4320211"
EVIDENCE_BYTES = b"ctx"
EVIDENCE_RELPATH = f"datasets/conec/earnings21/contexts/{SAMPLE_ID}.txt"


def _d1_document() -> dict:
    return {
        "carriers": {
            "conec": {
                "layers": {
                    "e21_contexts": {
                        "manifest": [
                            {
                                "id": SAMPLE_ID,
                                "bytes": len(EVIDENCE_BYTES),
                                "sha256": _sha(EVIDENCE_BYTES),
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
    d1_bytes = json.dumps(_d1_document()).encode("utf-8")
    (fixture.receipts / "e0" / "d1_identity.json").write_bytes(d1_bytes)
    fixture.deliverables["d1_identity"]["sha256"] = _sha(d1_bytes)
    evidence_dir = fixture.data_root / "datasets" / "conec" / "earnings21" / "contexts"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / f"{SAMPLE_ID}.txt").write_bytes(EVIDENCE_BYTES)
    return fixture


def _evidence_facts() -> dict:
    return {SAMPLE_ID: EVIDENCE_RELPATH}


def test_unmodified_evidence_bytes_pass(world):
    gate = world.gate()
    gate.verify_evidence_identity(world.CARRIER, _evidence_facts())


def test_tampered_evidence_bytes_are_refused(world):
    """Probe (IMPORTANT 1, demonstrated): a tampered ConEC context byte must
    refuse before any model touch, never return a fresh self-consistent hash
    computed from the tampered bytes themselves."""

    evidence = world.data_root / EVIDENCE_RELPATH
    evidence.write_bytes(b"tampered-bytes-not-the-original-context-at-all")
    gate = world.gate()
    with pytest.raises(GateClosed, match="evidence identity drift"):
        gate.verify_evidence_identity(world.CARRIER, _evidence_facts())


def test_missing_evidence_file_is_refused(world):
    """Probe: an interrupted asset fetch or a wrong SPEECHRL_DATA_DIR
    produces the identical symptom as a deliberate substitution -- both must
    refuse, naming the file."""

    evidence = world.data_root / EVIDENCE_RELPATH
    evidence.unlink()
    gate = world.gate()
    with pytest.raises(GateClosed, match="does not exist"):
        gate.verify_evidence_identity(world.CARRIER, _evidence_facts())


def test_sample_outside_d1_closure_is_refused(world):
    gate = world.gate()
    relpath = "datasets/conec/earnings21/contexts/9999999.txt"
    evidence = world.data_root / relpath
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_bytes(b"a-sample-d1-never-closed-over")
    with pytest.raises(GateClosed, match="no D1-recorded evidence identity"):
        gate.verify_evidence_identity(world.CARRIER, {"9999999": relpath})


def test_carrier_with_no_evidence_layer_is_refused(world):
    """Probe: an evidence source configured for a carrier whose descriptor
    declares no evidence layer (earnings22-original -- its ConEC contexts are
    a different-shaped, never-read per-call-PDF layer) must fail closed
    inside the gate itself, independent of core.evidence's own internal
    refusal for the same case."""

    gate = world.gate()
    with pytest.raises(GateClosed, match="no D1-recorded evidence-layer identity"):
        gate.verify_evidence_identity("earnings22-original", _evidence_facts())


def test_unregistered_carrier_is_refused(world):
    gate = world.gate()
    with pytest.raises(GateClosed, match="no registered carrier descriptor"):
        gate.verify_evidence_identity("never-registered-carrier", _evidence_facts())


def test_empty_evidence_facts_refused(world):
    gate = world.gate()
    with pytest.raises(GateClosed, match="non-empty"):
        gate.verify_evidence_identity(world.CARRIER, {})


def test_traversal_relpath_is_refused(world):
    gate = world.gate()
    with pytest.raises(GateClosed):
        gate.verify_evidence_identity(world.CARRIER, {SAMPLE_ID: "../../etc/passwd"})


# ---------------------------------------------------------------------------
# IMPROVEMENT (fifth external-threat-model review): verify_evidence_content_
# identity binds the check to the bytes ALREADY READ into memory, never a
# second read of the file -- the mirror image of the accepted check<->send
# race. No file is touched by this method at all: every probe below passes
# in-memory bytes directly, several while the on-disk file is in a DIFFERENT
# state than the bytes being checked, to prove the check never consults disk.
#
# conec-names follow-up (2026-08-13): verify_evidence_content_identity now
# ALSO takes evidence_relpaths (routes each sample's content to its own D1
# layer, gate_evidence_identity's own module docstring) -- every call below
# passes _evidence_facts(), the SAME relpath mapping verify_evidence_identity
# already used, so these probes stay byte-identical in BEHAVIOUR (same
# assertions, same refusals) to before this follow-up; only the call
# signature changed. Routing-matrix coverage for participant_names lives in
# test_evidence_content_identity_participant_names.py.
# ---------------------------------------------------------------------------


def _evidence_contents() -> dict:
    return {SAMPLE_ID: EVIDENCE_BYTES}


def test_unmodified_evidence_content_passes(world):
    gate = world.gate()
    gate.verify_evidence_content_identity(world.CARRIER, _evidence_contents(), _evidence_facts())


def test_tampered_in_memory_content_is_refused(world):
    gate = world.gate()
    with pytest.raises(GateClosed, match="evidence content identity drift"):
        gate.verify_evidence_content_identity(
            world.CARRIER,
            {SAMPLE_ID: b"tampered-bytes-not-the-original-context-at-all"},
            _evidence_facts(),
        )


def test_restored_pristine_file_does_not_launder_tampered_in_memory_content(world):
    """The exact PROBE the review demonstrated: content is read into memory
    from a TAMPERED file (what a run would actually put in the prompt), the
    file is then restored to its pristine, D1-matching bytes BEFORE any gate
    check runs. verify_evidence_identity (the file rail) now sees a pristine
    file and passes -- that is expected, unchanged behaviour. But the run
    must still refuse overall, because verify_evidence_content_identity
    checks the bytes actually consumed, which were tampered, regardless of
    what the file on disk says right now."""

    evidence_path = world.data_root / EVIDENCE_RELPATH
    tampered = b"tampered-bytes-not-the-original-context-at-all"
    evidence_path.write_bytes(tampered)
    # The read a run's evidence source would perform, captured BEFORE restore.
    content_actually_read = evidence_path.read_bytes()
    evidence_path.write_bytes(EVIDENCE_BYTES)  # restored to pristine, D1-matching bytes

    gate = world.gate()
    gate.verify_evidence_identity(world.CARRIER, _evidence_facts())  # file rail: passes
    with pytest.raises(GateClosed, match="evidence content identity drift"):
        gate.verify_evidence_content_identity(
            world.CARRIER, {SAMPLE_ID: content_actually_read}, _evidence_facts()
        )


def test_untampered_content_still_runs_after_a_pristine_restore(world):
    """The negative control for the probe above: when the content actually
    read was never tampered in the first place, both rails pass."""

    evidence_path = world.data_root / EVIDENCE_RELPATH
    content_actually_read = evidence_path.read_bytes()
    assert content_actually_read == EVIDENCE_BYTES

    gate = world.gate()
    gate.verify_evidence_identity(world.CARRIER, _evidence_facts())
    gate.verify_evidence_content_identity(
        world.CARRIER, {SAMPLE_ID: content_actually_read}, _evidence_facts()
    )


def test_content_identity_sample_outside_d1_closure_is_refused(world):
    gate = world.gate()
    relpath = "datasets/conec/earnings21/contexts/9999999.txt"
    with pytest.raises(GateClosed, match="no D1-recorded evidence identity"):
        gate.verify_evidence_content_identity(
            world.CARRIER, {"9999999": b"anything"}, {"9999999": relpath}
        )


def test_content_identity_carrier_with_no_evidence_layer_is_refused(world):
    gate = world.gate()
    with pytest.raises(GateClosed, match="no D1-recorded evidence-layer identity"):
        gate.verify_evidence_content_identity(
            "earnings22-original", _evidence_contents(), _evidence_facts()
        )


def test_content_identity_unregistered_carrier_is_refused(world):
    gate = world.gate()
    with pytest.raises(GateClosed, match="no registered carrier descriptor"):
        gate.verify_evidence_content_identity(
            "never-registered-carrier", _evidence_contents(), _evidence_facts()
        )


def test_content_identity_empty_mapping_refused(world):
    gate = world.gate()
    with pytest.raises(GateClosed, match="non-empty"):
        gate.verify_evidence_content_identity(world.CARRIER, {}, _evidence_facts())


def test_content_identity_non_bytes_value_refused(world):
    # 2026-09-06: the wording widened when a sample became able to carry SEVERAL
    # evidence files (gate_evidence_identity._as_tuple); the refusal is the same.
    gate = world.gate()
    with pytest.raises(GateClosed, match="must be a bytes/bytearray"):
        gate.verify_evidence_content_identity(
            world.CARRIER, {SAMPLE_ID: "not-bytes"}, _evidence_facts()
        )
