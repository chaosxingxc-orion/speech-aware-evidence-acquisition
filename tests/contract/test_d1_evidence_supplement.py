"""The additive D1 EVIDENCE-layer supplement (2026-09-06, KC-E1 precondition 1).

``contracts.gate_evidence_identity`` has always been able to ROUTE a
``contexts/participant_names/<call>.names.txt`` relpath to the D1 layer key
``e21_participant_names`` and has never been able to RESOLVE it: the immutable E0
D1 artifact records four ConEC layers and not that one. The layer now arrives the
way a bounded media slice already does -- as one additive, hash-pinned
``saea-d1-evidence-supplement-v1`` document -- and this module is the refusal
matrix for it.

The theme of every negative case: a supplement ADDS one layer to a frozen
identity closure and may never widen, shadow, or drift from it.
"""

import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.contracts import GateClosed
from speech_aware_evidence_acquisition.contracts.gate_evidence_identity import (
    EVIDENCE_SUPPLEMENT_SCHEMA,
)

from gate_fixture import GateFixture


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


SAMPLE_ID = "4320211"
OTHER_SAMPLE_ID = "4330115"

CONTEXT_BYTES = b"a conec context document, longer than the roster"
OTHER_CONTEXT_BYTES = b"another conec context document"
NAMES_BYTES = b"Jane Doe - CEO\nJohn Roe - CFO\n"
OTHER_NAMES_BYTES = b"Alice Smith - COO\n"

CONTEXT_RELPATH = f"datasets/conec/earnings21/contexts/{SAMPLE_ID}.txt"
NAMES_RELPATH = (
    f"datasets/conec/earnings21/contexts/participant_names/{SAMPLE_ID}.names.txt"
)
OTHER_NAMES_RELPATH = (
    f"datasets/conec/earnings21/contexts/participant_names/{OTHER_SAMPLE_ID}.names.txt"
)

CARRIER = GateFixture.CARRIER
LAYER_KEY = "e21_participant_names"


def _ids_sha256(ids) -> str:
    return _sha("\n".join(sorted(ids)).encode("utf-8"))


def _manifest_sha256(manifest) -> str:
    lines = "\n".join(
        f"{entry['id']},{entry['bytes']},{entry['sha256']}"
        for entry in sorted(manifest, key=lambda row: row["id"])
    )
    return _sha(lines.encode("utf-8"))


def _context_layer() -> dict:
    manifest = [
        {"id": SAMPLE_ID, "bytes": len(CONTEXT_BYTES), "sha256": _sha(CONTEXT_BYTES)},
        {
            "id": OTHER_SAMPLE_ID,
            "bytes": len(OTHER_CONTEXT_BYTES),
            "sha256": _sha(OTHER_CONTEXT_BYTES),
        },
    ]
    return {
        "count": len(manifest),
        "ids_sha256": _ids_sha256([entry["id"] for entry in manifest]),
        "manifest": manifest,
        "manifest_sha256": _manifest_sha256(manifest),
        "excluded_non_layer_files": ["participant_names", "pdfs"],
    }


def _names_manifest() -> list[dict]:
    return [
        {"id": SAMPLE_ID, "bytes": len(NAMES_BYTES), "sha256": _sha(NAMES_BYTES)},
        {
            "id": OTHER_SAMPLE_ID,
            "bytes": len(OTHER_NAMES_BYTES),
            "sha256": _sha(OTHER_NAMES_BYTES),
        },
    ]


class World:
    """A gate world whose base D1 carries ``e21_contexts`` and NOT the roster
    layer -- exactly the committed artifact's own shape."""

    def __init__(self, tmp_path):
        self.fixture = GateFixture(tmp_path)
        self.d1 = {"carriers": {"conec": {"layers": {"e21_contexts": _context_layer()}}}}
        self._write_d1()

        contexts = self.fixture.data_root / "datasets" / "conec" / "earnings21" / "contexts"
        contexts.mkdir(parents=True, exist_ok=True)
        (contexts / f"{SAMPLE_ID}.txt").write_bytes(CONTEXT_BYTES)
        (contexts / f"{OTHER_SAMPLE_ID}.txt").write_bytes(OTHER_CONTEXT_BYTES)
        names = contexts / "participant_names"
        names.mkdir(parents=True, exist_ok=True)
        (names / f"{SAMPLE_ID}.names.txt").write_bytes(NAMES_BYTES)
        (names / f"{OTHER_SAMPLE_ID}.names.txt").write_bytes(OTHER_NAMES_BYTES)

        self.supplement_path = tmp_path / "d1-evidence-supplement.json"

    def _write_d1(self) -> None:
        raw = json.dumps(self.d1).encode("utf-8")
        (self.fixture.receipts / "e0" / "d1_identity.json").write_bytes(raw)
        self.fixture.deliverables["d1_identity"]["sha256"] = _sha(raw)
        self.d1_sha256 = _sha(raw)

    def supplement(self, **overrides) -> dict:
        manifest = overrides.pop("manifest", None) or _names_manifest()
        document = {
            "schema": EVIDENCE_SUPPLEMENT_SCHEMA,
            "study": "speech-aware-evidence-acquisition",
            "carrier_lock_key": "conec",
            "d1_layer_key": LAYER_KEY,
            "parent_d1_sha256": self.d1_sha256,
            "source_binding_sha256": self.d1["carriers"]["conec"]["layers"]["e21_contexts"][
                "ids_sha256"
            ],
            "count": len(manifest),
            "ids_sha256": _ids_sha256([entry["id"] for entry in manifest]),
            "manifest": manifest,
            "manifest_sha256": _manifest_sha256(manifest),
            "total_bytes": sum(entry["bytes"] for entry in manifest),
            "excluded_non_layer_files": ["names.txt"],
        }
        document.update(overrides)
        return document

    def gate(self, document: dict | None, *, sha256: str | None = None, **fields):
        if document is None:
            return self.fixture.gate(**fields)
        raw = json.dumps(document).encode("utf-8")
        self.supplement_path.write_bytes(raw)
        return self.fixture.gate(
            d1_evidence_supplement=self.supplement_path,
            d1_evidence_supplement_sha256=sha256 or _sha(raw),
            **fields,
        )


@pytest.fixture()
def world(tmp_path):
    return World(tmp_path)


# ---------------------------------------------------------------------------
# The gap it closes, and the two rails it closes it on.
# ---------------------------------------------------------------------------


def test_without_a_supplement_the_roster_layer_still_refuses(world):
    gate = world.gate(None)
    with pytest.raises(GateClosed) as error:
        gate.verify_evidence_identity(CARRIER, {SAMPLE_ID: NAMES_RELPATH})
    assert LAYER_KEY in str(error.value)
    assert "no D1 evidence supplement declares that layer" in str(error.value)


def test_the_supplement_resolves_the_roster_layer_on_the_file_rail(world):
    gate = world.gate(world.supplement())
    gate.verify_evidence_identity(
        CARRIER, {SAMPLE_ID: NAMES_RELPATH, OTHER_SAMPLE_ID: OTHER_NAMES_RELPATH}
    )


def test_the_supplement_resolves_the_roster_layer_on_the_content_rail(world):
    gate = world.gate(world.supplement())
    gate.verify_evidence_content_identity(
        CARRIER, {SAMPLE_ID: NAMES_BYTES}, {SAMPLE_ID: NAMES_RELPATH}
    )


def test_a_tampered_roster_byte_is_still_refused(world):
    gate = world.gate(world.supplement())
    with pytest.raises(GateClosed) as error:
        gate.verify_evidence_content_identity(
            CARRIER, {SAMPLE_ID: NAMES_BYTES + b" "}, {SAMPLE_ID: NAMES_RELPATH}
        )
    assert "evidence content identity drift" in str(error.value)


def test_a_context_relpath_still_resolves_from_the_base_d1(world):
    """One supplement carries ONE layer: a relpath routed anywhere else is
    answered from the base artifact, exactly as before the supplement existed."""

    gate = world.gate(world.supplement())
    gate.verify_evidence_identity(CARRIER, {SAMPLE_ID: CONTEXT_RELPATH})


def test_a_supplement_for_another_layer_does_not_answer_this_one(world):
    gate = world.gate(world.supplement(d1_layer_key="e21_wer_tags"))
    with pytest.raises(GateClosed) as error:
        gate.verify_evidence_identity(CARRIER, {SAMPLE_ID: NAMES_RELPATH})
    assert "no D1 evidence supplement declares that layer" in str(error.value)


# ---------------------------------------------------------------------------
# Refusal matrix: additive, never a rewrite.
# ---------------------------------------------------------------------------


def test_a_supplement_may_not_shadow_a_base_layer(world):
    world.d1["carriers"]["conec"]["layers"][LAYER_KEY] = {"manifest": _names_manifest()}
    world._write_d1()
    gate = world.gate(world.supplement())
    with pytest.raises(GateClosed) as error:
        gate.verify_evidence_identity(CARRIER, {SAMPLE_ID: NAMES_RELPATH})
    assert "never shadow one" in str(error.value)


def test_hash_drift_between_the_configured_digest_and_the_file_refuses(world):
    gate = world.gate(world.supplement(), sha256="0" * 64)
    with pytest.raises(GateClosed) as error:
        gate.verify_evidence_identity(CARRIER, {SAMPLE_ID: NAMES_RELPATH})
    assert "hash drift" in str(error.value)


def test_a_supplement_built_against_another_d1_refuses(world):
    gate = world.gate(world.supplement(parent_d1_sha256="1" * 64))
    with pytest.raises(GateClosed) as error:
        gate.verify_evidence_identity(CARRIER, {SAMPLE_ID: NAMES_RELPATH})
    assert "parent D1 hash mismatch" in str(error.value)


def test_a_supplement_for_another_carrier_refuses(world):
    gate = world.gate(world.supplement(carrier_lock_key="slurp"))
    with pytest.raises(GateClosed) as error:
        gate.verify_evidence_identity(CARRIER, {SAMPLE_ID: NAMES_RELPATH})
    assert "carrier does not match" in str(error.value)


def test_a_source_binding_that_is_not_the_carrier_universe_refuses(world):
    gate = world.gate(world.supplement(source_binding_sha256="2" * 64))
    with pytest.raises(GateClosed) as error:
        gate.verify_evidence_identity(CARRIER, {SAMPLE_ID: NAMES_RELPATH})
    assert "source binding does not name the carrier's own" in str(error.value)


def test_a_supplement_that_widens_the_sample_universe_refuses(world):
    """The digests stay self-consistent -- what fails is that the layer covers a
    sample the carrier's frozen universe does not."""

    manifest = _names_manifest() + [
        {"id": "9999999", "bytes": 7, "sha256": _sha(b"intruder")}
    ]
    gate = world.gate(world.supplement(manifest=manifest))
    with pytest.raises(GateClosed) as error:
        gate.verify_evidence_identity(CARRIER, {SAMPLE_ID: NAMES_RELPATH})
    assert "different sample set" in str(error.value)


def test_a_wrong_ids_digest_refuses(world):
    gate = world.gate(world.supplement(ids_sha256="3" * 64))
    with pytest.raises(GateClosed) as error:
        gate.verify_evidence_identity(CARRIER, {SAMPLE_ID: NAMES_RELPATH})
    assert "count or ids SHA-256 mismatch" in str(error.value)


def test_a_wrong_manifest_digest_refuses(world):
    gate = world.gate(world.supplement(manifest_sha256="4" * 64))
    with pytest.raises(GateClosed) as error:
        gate.verify_evidence_identity(CARRIER, {SAMPLE_ID: NAMES_RELPATH})
    assert "manifest SHA-256 mismatch" in str(error.value)


def test_a_wrong_total_bytes_refuses(world):
    gate = world.gate(world.supplement(total_bytes=1))
    with pytest.raises(GateClosed) as error:
        gate.verify_evidence_identity(CARRIER, {SAMPLE_ID: NAMES_RELPATH})
    assert "total_bytes mismatch" in str(error.value)


def test_a_wrong_schema_refuses(world):
    gate = world.gate(world.supplement(schema="saea-d1-media-supplement-v1"))
    with pytest.raises(GateClosed) as error:
        gate.verify_evidence_identity(CARRIER, {SAMPLE_ID: NAMES_RELPATH})
    assert "schema mismatch" in str(error.value)


def test_an_extra_key_refuses(world):
    document = world.supplement()
    document["surprise"] = True
    gate = world.gate(document)
    with pytest.raises(GateClosed) as error:
        gate.verify_evidence_identity(CARRIER, {SAMPLE_ID: NAMES_RELPATH})
    assert "exact keys" in str(error.value)


def test_a_missing_key_refuses(world):
    document = world.supplement()
    document.pop("excluded_non_layer_files")
    gate = world.gate(document)
    with pytest.raises(GateClosed) as error:
        gate.verify_evidence_identity(CARRIER, {SAMPLE_ID: NAMES_RELPATH})
    assert "exact keys" in str(error.value)


def test_an_unpaired_digest_refuses(world):
    raw = json.dumps(world.supplement()).encode("utf-8")
    world.supplement_path.write_bytes(raw)
    gate = world.fixture.gate(d1_evidence_supplement=world.supplement_path)
    with pytest.raises(GateClosed) as error:
        gate.verify_evidence_identity(CARRIER, {SAMPLE_ID: NAMES_RELPATH})
    assert "must be paired" in str(error.value)


# ---------------------------------------------------------------------------
# One supplement per gate.
# ---------------------------------------------------------------------------


def test_a_gate_refuses_to_carry_two_supplements(world):
    raw = json.dumps(world.supplement()).encode("utf-8")
    world.supplement_path.write_bytes(raw)
    with pytest.raises(ValueError) as error:
        world.fixture.gate(
            d1_evidence_supplement=world.supplement_path,
            d1_evidence_supplement_sha256=_sha(raw),
            d1_media_supplement=world.supplement_path,
            d1_media_supplement_sha256=_sha(raw),
        )
    assert "AT MOST ONE supplement" in str(error.value)
