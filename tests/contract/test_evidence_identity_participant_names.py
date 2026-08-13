"""Routing-matrix tests for the ``e21_participant_names`` D1 layer
(``conec-names`` gate-closure incident, 2026-08-13).

Before ``contracts.gate_evidence_identity``'s relpath routing existed, EVERY
conec evidence relpath -- a context file or a participant-names roster
alike -- was checked against the SAME single D1 layer (``e21_contexts``),
because ``_evidence_manifest`` built exactly one ``sample_id -> (bytes,
sha256)`` mapping per call, keyed only by sample id. A names-roster file's
own bytes were then compared against the CONTEXTS file's D1-recorded
size/hash for the same sample id -- two different files sharing only the
``sample_id`` key -- which is exactly the "evidence identity drift" a real
run hit despite the file never being tampered (task incident report:
"D1 recorded 13832 bytes ..., the live file is now 120 bytes ...").

``_route_evidence_layer_key`` (module under test) now routes each relpath,
individually, to the correct D1 layer key: a relpath directly under the
layer's own subdir keeps resolving to ``e21_contexts`` (byte-identical to
before this rail existed -- ``test_evidence_identity.py`` already proves
this unmodified), a ``participant_names/`` relpath resolves to the new
``e21_participant_names`` layer, and anything else refuses, fail-closed.
"""

import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.contracts import GateClosed

from gate_fixture import GateFixture


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


SAMPLE_ID = "4320211"
OTHER_SAMPLE_ID = "4330115"

CONTEXT_BYTES = b"a conec context, much longer than the names roster below"
NAMES_BYTES = b"Jane Doe - CEO\nJohn Roe - CFO\n"
OTHER_NAMES_BYTES = b"Alice Smith - COO\n"

CONTEXT_RELPATH = f"datasets/conec/earnings21/contexts/{SAMPLE_ID}.txt"
NAMES_RELPATH = (
    f"datasets/conec/earnings21/contexts/participant_names/{SAMPLE_ID}.names.txt"
)
OTHER_NAMES_RELPATH = (
    f"datasets/conec/earnings21/contexts/participant_names/{OTHER_SAMPLE_ID}.names.txt"
)
# A directory conec ships alongside contexts/participant_names but that D1
# has never recorded any identity contract for (core.evidence module
# docstring / d1-identity.json's own e21_contexts.excluded_non_layer_files).
UNKNOWN_SUBDIR_RELPATH = f"datasets/conec/earnings21/contexts/pdfs/{SAMPLE_ID}.pdf"
# A relpath that never names a file under the layer's own subdir at all.
OUTSIDE_SUBDIR_RELPATH = f"datasets/conec/earnings21/some_other_place/{SAMPLE_ID}.txt"


def _d1_document(*, include_participant_names_layer: bool = True) -> dict:
    layers = {
        "e21_contexts": {
            "manifest": [
                {"id": SAMPLE_ID, "bytes": len(CONTEXT_BYTES), "sha256": _sha(CONTEXT_BYTES)}
            ]
        }
    }
    if include_participant_names_layer:
        layers["e21_participant_names"] = {
            "manifest": [
                {"id": SAMPLE_ID, "bytes": len(NAMES_BYTES), "sha256": _sha(NAMES_BYTES)},
                {
                    "id": OTHER_SAMPLE_ID,
                    "bytes": len(OTHER_NAMES_BYTES),
                    "sha256": _sha(OTHER_NAMES_BYTES),
                },
            ]
        }
    return {"carriers": {"conec": {"layers": layers}}}


def _write_d1(fixture: GateFixture, document: dict) -> None:
    d1_bytes = json.dumps(document).encode("utf-8")
    (fixture.receipts / "e0" / "d1_identity.json").write_bytes(d1_bytes)
    fixture.deliverables["d1_identity"]["sha256"] = _sha(d1_bytes)


@pytest.fixture()
def world(tmp_path):
    fixture = GateFixture(tmp_path)
    _write_d1(fixture, _d1_document())

    contexts_dir = fixture.data_root / "datasets" / "conec" / "earnings21" / "contexts"
    contexts_dir.mkdir(parents=True, exist_ok=True)
    (contexts_dir / f"{SAMPLE_ID}.txt").write_bytes(CONTEXT_BYTES)

    names_dir = contexts_dir / "participant_names"
    names_dir.mkdir(parents=True, exist_ok=True)
    (names_dir / f"{SAMPLE_ID}.names.txt").write_bytes(NAMES_BYTES)
    (names_dir / f"{OTHER_SAMPLE_ID}.names.txt").write_bytes(OTHER_NAMES_BYTES)

    pdfs_dir = contexts_dir / "pdfs"
    pdfs_dir.mkdir(parents=True, exist_ok=True)
    (pdfs_dir / f"{SAMPLE_ID}.pdf").write_bytes(b"%PDF-fake-not-a-real-pdf")

    return fixture


# ---------------------------------------------------------------------------
# Routing matrix: contexts -> e21_contexts (unchanged); participant_names ->
# e21_participant_names (new); unknown prefix -> refused.
# ---------------------------------------------------------------------------


def test_contexts_relpath_routes_to_e21_contexts_unchanged(world):
    gate = world.gate()
    gate.verify_evidence_identity(world.CARRIER, {SAMPLE_ID: CONTEXT_RELPATH})


def test_participant_names_relpath_routes_to_new_layer(world):
    gate = world.gate()
    gate.verify_evidence_identity(world.CARRIER, {SAMPLE_ID: NAMES_RELPATH})


def test_names_bytes_are_never_checked_against_the_contexts_layer(world):
    """The exact incident reproduced: the names file is a DIFFERENT size
    than the contexts file recorded for the same sample_id. Pre-fix routing
    (always e21_contexts) would raise 'evidence identity drift' here even
    though nothing was tampered; post-fix routing checks the names file
    against its own layer's facts and passes."""

    assert len(NAMES_BYTES) != len(CONTEXT_BYTES)
    gate = world.gate()
    gate.verify_evidence_identity(world.CARRIER, {SAMPLE_ID: NAMES_RELPATH})


def test_mixed_relpaths_route_independently_in_one_call(world):
    """A context relpath and a participant-names relpath in the SAME
    evidence_facts mapping each resolve against their own layer -- proves
    routing is per-item, not a single carrier-wide decision for the call."""

    gate = world.gate()
    gate.verify_evidence_identity(
        world.CARRIER,
        {SAMPLE_ID: CONTEXT_RELPATH, OTHER_SAMPLE_ID: OTHER_NAMES_RELPATH},
    )


def test_unknown_subdir_relpath_is_refused(world):
    gate = world.gate()
    with pytest.raises(GateClosed, match="no known routing rule"):
        gate.verify_evidence_identity(world.CARRIER, {SAMPLE_ID: UNKNOWN_SUBDIR_RELPATH})


def test_relpath_outside_evidence_subdir_is_refused(world):
    gate = world.gate()
    outside_dir = world.data_root / "datasets" / "conec" / "earnings21" / "some_other_place"
    outside_dir.mkdir(parents=True, exist_ok=True)
    (outside_dir / f"{SAMPLE_ID}.txt").write_bytes(b"whatever-this-is-not-a-layer-file")
    with pytest.raises(GateClosed, match="does not name a file under"):
        gate.verify_evidence_identity(world.CARRIER, {SAMPLE_ID: OUTSIDE_SUBDIR_RELPATH})


# ---------------------------------------------------------------------------
# The new layer gets the SAME tamper/refusal discipline e21_contexts already had.
# ---------------------------------------------------------------------------


def test_tampered_participant_names_bytes_are_refused_against_own_layer(world):
    names_path = world.data_root / NAMES_RELPATH
    names_path.write_bytes(b"tampered-bytes-not-the-original-roster-at-all")
    gate = world.gate()
    with pytest.raises(GateClosed, match="evidence identity drift"):
        gate.verify_evidence_identity(world.CARRIER, {SAMPLE_ID: NAMES_RELPATH})


def test_participant_names_sample_outside_d1_closure_is_refused(world):
    gate = world.gate()
    relpath = "datasets/conec/earnings21/contexts/participant_names/9999999.names.txt"
    names_path = world.data_root / relpath
    names_path.parent.mkdir(parents=True, exist_ok=True)
    names_path.write_bytes(b"a-sample-d1-never-closed-over")
    with pytest.raises(GateClosed, match="no D1-recorded evidence identity"):
        gate.verify_evidence_identity(world.CARRIER, {"9999999": relpath})


def test_participant_names_layer_missing_from_d1_is_refused(tmp_path):
    """Before the coordinator inserts the frozen e21_participant_names
    fragment into d1-identity.json, a conec-names relpath must keep
    refusing -- never silently fall back to e21_contexts."""

    fixture = GateFixture(tmp_path)
    _write_d1(fixture, _d1_document(include_participant_names_layer=False))

    contexts_dir = fixture.data_root / "datasets" / "conec" / "earnings21" / "contexts"
    names_dir = contexts_dir / "participant_names"
    names_dir.mkdir(parents=True, exist_ok=True)
    (names_dir / f"{SAMPLE_ID}.names.txt").write_bytes(NAMES_BYTES)

    gate = fixture.gate()
    with pytest.raises(GateClosed, match="lacks a 'e21_participant_names' manifest"):
        gate.verify_evidence_identity(fixture.CARRIER, {SAMPLE_ID: NAMES_RELPATH})


def test_participant_names_missing_evidence_file_is_refused(world):
    names_path = world.data_root / NAMES_RELPATH
    names_path.unlink()
    gate = world.gate()
    with pytest.raises(GateClosed, match="does not exist"):
        gate.verify_evidence_identity(world.CARRIER, {SAMPLE_ID: NAMES_RELPATH})
