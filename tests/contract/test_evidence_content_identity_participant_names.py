"""Routing-matrix tests for ``verify_evidence_content_identity``'s
``e21_participant_names`` routing (``conec-names`` gate-closure incident,
follow-up, 2026-08-13, second check point).

The relpath-routing fix (``test_evidence_identity_participant_names.py``)
landed for ``verify_evidence_identity`` (the FILE rail) alone first.
``verify_evidence_content_identity`` (the CONTENT rail,
``core.model.lifecycle`` calls both back to back on the SAME binding) kept
resolving every sample's expected facts from the carrier's single default
layer (``e21_contexts``) by ``sample_id`` alone -- so a real gated run using
``conec-names`` passed the file check (routed correctly) and then failed at
the content check for the identical underlying reason, one call later:
"evidence content identity drift ... D1 recorded 13832 bytes ..., the
in-memory content this run already read is 120 bytes ...".
``verify_evidence_content_identity`` now takes a second required mapping,
``evidence_relpaths`` (the SAME per-sample relpaths the file check itself
routes by, threaded from the SAME ``binding.evidence_relpaths``), and routes
each sample's content via the SAME ``_route_evidence_layer_key`` the file
rail uses -- not a second, parallel routing implementation.
"""

import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.contracts import GateClosed

from gate_fixture import GateFixture

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
UNKNOWN_SUBDIR_RELPATH = f"datasets/conec/earnings21/contexts/pdfs/{SAMPLE_ID}.pdf"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


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
    return fixture


# ---------------------------------------------------------------------------
# Routing matrix, content path: contexts -> e21_contexts (unchanged);
# participant_names -> e21_participant_names (new); no matching relpath ->
# refused; unknown prefix -> refused.
# ---------------------------------------------------------------------------


def test_contexts_content_routes_to_e21_contexts_unchanged(world):
    gate = world.gate()
    gate.verify_evidence_content_identity(
        world.CARRIER, {SAMPLE_ID: CONTEXT_BYTES}, {SAMPLE_ID: CONTEXT_RELPATH}
    )


def test_participant_names_content_routes_to_new_layer(world):
    gate = world.gate()
    gate.verify_evidence_content_identity(
        world.CARRIER, {SAMPLE_ID: NAMES_BYTES}, {SAMPLE_ID: NAMES_RELPATH}
    )


def test_names_content_is_never_checked_against_the_contexts_layer(world):
    """The exact follow-up incident reproduced, at the content-identity
    check point: the names bytes are a DIFFERENT size than e21_contexts'
    own recorded size for the same sample_id. Pre-fix behaviour (always
    the carrier's default layer) would raise 'evidence content identity
    drift' here even though nothing was tampered; post-fix routing checks
    the names content against its own layer's facts and passes."""

    assert len(NAMES_BYTES) != len(CONTEXT_BYTES)
    gate = world.gate()
    gate.verify_evidence_content_identity(
        world.CARRIER, {SAMPLE_ID: NAMES_BYTES}, {SAMPLE_ID: NAMES_RELPATH}
    )


def test_mixed_samples_route_independently_in_one_call(world):
    gate = world.gate()
    gate.verify_evidence_content_identity(
        world.CARRIER,
        {SAMPLE_ID: CONTEXT_BYTES, OTHER_SAMPLE_ID: OTHER_NAMES_BYTES},
        {SAMPLE_ID: CONTEXT_RELPATH, OTHER_SAMPLE_ID: OTHER_NAMES_RELPATH},
    )


def test_content_with_no_matching_relpath_entry_is_refused(world):
    """A sample present in evidence_contents but absent from
    evidence_relpaths (a non-empty mapping that simply does not cover this
    sample_id) can never be routed -- refuses fail-closed rather than
    falling back to the carrier's default layer."""

    gate = world.gate()
    with pytest.raises(GateClosed, match="no matching"):
        gate.verify_evidence_content_identity(
            world.CARRIER,
            {SAMPLE_ID: NAMES_BYTES},
            {OTHER_SAMPLE_ID: OTHER_NAMES_RELPATH},
        )


def test_empty_evidence_relpaths_mapping_is_refused(world):
    gate = world.gate()
    with pytest.raises(GateClosed, match="non-empty"):
        gate.verify_evidence_content_identity(world.CARRIER, {SAMPLE_ID: CONTEXT_BYTES}, {})


def test_unknown_subdir_content_relpath_is_refused(world):
    gate = world.gate()
    with pytest.raises(GateClosed, match="no known routing rule"):
        gate.verify_evidence_content_identity(
            world.CARRIER, {SAMPLE_ID: b"whatever"}, {SAMPLE_ID: UNKNOWN_SUBDIR_RELPATH}
        )


# ---------------------------------------------------------------------------
# The new layer gets the SAME tamper/refusal discipline e21_contexts content
# checks already had.
# ---------------------------------------------------------------------------


def test_tampered_participant_names_content_is_refused_against_own_layer(world):
    gate = world.gate()
    with pytest.raises(GateClosed, match="evidence content identity drift"):
        gate.verify_evidence_content_identity(
            world.CARRIER,
            {SAMPLE_ID: b"tampered-bytes-not-the-original-roster-at-all"},
            {SAMPLE_ID: NAMES_RELPATH},
        )


def test_participant_names_content_sample_outside_d1_closure_is_refused(world):
    gate = world.gate()
    relpath = "datasets/conec/earnings21/contexts/participant_names/9999999.names.txt"
    with pytest.raises(GateClosed, match="no D1-recorded evidence identity"):
        gate.verify_evidence_content_identity(
            world.CARRIER, {"9999999": b"a-sample-d1-never-closed-over"}, {"9999999": relpath}
        )


def test_participant_names_content_layer_missing_from_d1_is_refused(tmp_path):
    """Before the e21_participant_names fragment is inserted into
    d1-identity.json, conec-names content must keep refusing -- never
    silently fall back to e21_contexts."""

    fixture = GateFixture(tmp_path)
    _write_d1(fixture, _d1_document(include_participant_names_layer=False))
    gate = fixture.gate()
    with pytest.raises(GateClosed, match="lacks a 'e21_participant_names' manifest"):
        gate.verify_evidence_content_identity(
            fixture.CARRIER, {SAMPLE_ID: NAMES_BYTES}, {SAMPLE_ID: NAMES_RELPATH}
        )
