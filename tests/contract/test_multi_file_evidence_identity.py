"""One sample, several evidence files: both identity rails see all of them.

Routing each relpath to its own D1 layer is only worth anything if every relpath
a sample draws on actually reaches the rail. ``core.driver.run_experiment`` used
to ASSIGN rather than accumulate -- ``evidence_relpaths[sid] = record.source_relpath``
inside a loop over that sample's items -- so a source returning several
carrier-bound items per sample had all but the LAST silently dropped, unchecked.

E5's ``conec-class-lists`` is exactly that source: two items per call, the
participant roster (layer ``e21_participant_names``) and the context document
(layer ``e21_contexts``). The roster half -- the one the 2026-09-06 D1 evidence
supplement exists to make checkable at all -- was the half being dropped.

These tests pin the fixed shape from both ends: the rails accept an ordered tuple
per sample and check every member, and ``core.base.PayloadBindingContext`` keeps
the two mappings positionally paired.
"""

import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.contracts import GateClosed
from speech_aware_evidence_acquisition.core.base import CoreError, PayloadBindingContext

from gate_fixture import GateFixture


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


SAMPLE_ID = "4320211"
CONTEXT_BYTES = b"a conec context document, longer than the roster"
NAMES_BYTES = b"Jane Doe - CEO\nJohn Roe - CFO\n"
CONTEXT_RELPATH = f"datasets/conec/earnings21/contexts/{SAMPLE_ID}.txt"
NAMES_RELPATH = (
    f"datasets/conec/earnings21/contexts/participant_names/{SAMPLE_ID}.names.txt"
)
CARRIER = GateFixture.CARRIER
BOTH_RELPATHS = (NAMES_RELPATH, CONTEXT_RELPATH)
BOTH_CONTENTS = (NAMES_BYTES, CONTEXT_BYTES)


@pytest.fixture()
def world(tmp_path):
    fixture = GateFixture(tmp_path)
    d1 = {
        "carriers": {
            "conec": {
                "layers": {
                    "e21_contexts": {
                        "manifest": [
                            {
                                "id": SAMPLE_ID,
                                "bytes": len(CONTEXT_BYTES),
                                "sha256": _sha(CONTEXT_BYTES),
                            }
                        ]
                    },
                    "e21_participant_names": {
                        "manifest": [
                            {
                                "id": SAMPLE_ID,
                                "bytes": len(NAMES_BYTES),
                                "sha256": _sha(NAMES_BYTES),
                            }
                        ]
                    },
                }
            }
        }
    }
    raw = json.dumps(d1).encode("utf-8")
    (fixture.receipts / "e0" / "d1_identity.json").write_bytes(raw)
    fixture.deliverables["d1_identity"]["sha256"] = _sha(raw)

    contexts = fixture.data_root / "datasets" / "conec" / "earnings21" / "contexts"
    contexts.mkdir(parents=True, exist_ok=True)
    (contexts / f"{SAMPLE_ID}.txt").write_bytes(CONTEXT_BYTES)
    names = contexts / "participant_names"
    names.mkdir(parents=True, exist_ok=True)
    (names / f"{SAMPLE_ID}.names.txt").write_bytes(NAMES_BYTES)
    return fixture


def test_both_halves_of_one_brief_pass_the_file_rail(world):
    world.gate().verify_evidence_identity(CARRIER, {SAMPLE_ID: BOTH_RELPATHS})


def test_both_halves_of_one_brief_pass_the_content_rail(world):
    world.gate().verify_evidence_content_identity(
        CARRIER, {SAMPLE_ID: BOTH_CONTENTS}, {SAMPLE_ID: BOTH_RELPATHS}
    )


def test_a_tampered_roster_half_is_caught_even_though_the_document_half_is_clean(world):
    """The regression this exists for: with last-wins, only the document half
    reached the rail and a corrupt roster passed."""

    with pytest.raises(GateClosed) as error:
        world.gate().verify_evidence_content_identity(
            CARRIER,
            {SAMPLE_ID: (NAMES_BYTES + b"!", CONTEXT_BYTES)},
            {SAMPLE_ID: BOTH_RELPATHS},
        )
    assert "evidence content identity drift" in str(error.value)


def test_a_tampered_roster_file_is_caught_on_the_file_rail(world):
    path = (
        world.data_root
        / "datasets/conec/earnings21/contexts/participant_names"
        / f"{SAMPLE_ID}.names.txt"
    )
    path.write_bytes(NAMES_BYTES + b"!")
    with pytest.raises(GateClosed) as error:
        world.gate().verify_evidence_identity(CARRIER, {SAMPLE_ID: BOTH_RELPATHS})
    assert "evidence identity drift" in str(error.value)


def test_unpaired_contents_and_relpaths_refuse(world):
    with pytest.raises(GateClosed) as error:
        world.gate().verify_evidence_content_identity(
            CARRIER, {SAMPLE_ID: BOTH_CONTENTS}, {SAMPLE_ID: NAMES_RELPATH}
        )
    assert "positionally paired" in str(error.value)


def test_an_empty_tuple_refuses(world):
    with pytest.raises(GateClosed) as error:
        world.gate().verify_evidence_identity(CARRIER, {SAMPLE_ID: ()})
    assert "non-empty tuple" in str(error.value)


def test_a_single_relpath_still_works_unchanged(world):
    world.gate().verify_evidence_identity(CARRIER, {SAMPLE_ID: CONTEXT_RELPATH})
    world.gate().verify_evidence_content_identity(
        CARRIER, {SAMPLE_ID: CONTEXT_BYTES}, {SAMPLE_ID: CONTEXT_RELPATH}
    )


# ---------------------------------------------------------------------------
# The binding context keeps the two mappings paired.
# ---------------------------------------------------------------------------


def _binding(tmp_path, **overrides) -> PayloadBindingContext:
    data_root = tmp_path / "data"
    (data_root / "carrier").mkdir(parents=True, exist_ok=True)
    fields: dict = dict(
        carrier_lock_key=CARRIER,
        allowed_sample_ids=frozenset({SAMPLE_ID}),
        sample_facts={SAMPLE_ID: (12.5, 16000)},
        data_root=data_root,
        carrier_root=data_root / "carrier",
    )
    fields.update(overrides)
    return PayloadBindingContext(**fields)


def test_binding_accepts_a_tuple_of_relpaths_and_contents(tmp_path):
    _binding(
        tmp_path,
        evidence_relpaths={SAMPLE_ID: BOTH_RELPATHS},
        evidence_contents={SAMPLE_ID: BOTH_CONTENTS},
    ).validate()


def test_binding_refuses_an_unpaired_length(tmp_path):
    with pytest.raises(CoreError) as error:
        _binding(
            tmp_path,
            evidence_relpaths={SAMPLE_ID: NAMES_RELPATH},
            evidence_contents={SAMPLE_ID: BOTH_CONTENTS},
        ).validate()
    assert "positionally paired" in str(error.value)


def test_binding_refuses_an_empty_tuple(tmp_path):
    with pytest.raises(CoreError) as error:
        _binding(tmp_path, evidence_relpaths={SAMPLE_ID: ()}).validate()
    assert "non-empty tuple" in str(error.value)
