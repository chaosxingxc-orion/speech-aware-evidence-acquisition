"""E5b: the SLURP semantic store revisions v2 (intent v3 / slot v2).

Two kinds of assertion, deliberately separate:

1. CONFIG facts, which always run: the two held fragments pin the v2 store
   namespaces exactly as ``docs/readiness/2026-09-17-slurp-semantic-store-
   release-pins-v2.json`` and the two preparation registrations do, leave the
   other store on v1, stay held, and carry their own speech-feature identity.
2. STORE facts, which need the controlled data root: the released v2 snapshots
   carry the same value inventory as v1, every unchanged card is byte-identical,
   the changed set is exactly the set ``CHANGES.json`` declares, every retrieval
   key text is byte-identical (so the sealed intent key vectors still bind), and
   no changed card text collides with the anchor's control turns under
   ``rails.runner._assert_agent_control_excludes_knowledge_payloads``.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.slurp_slot_vocabulary import (
    containment_collisions,
)
from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot
from speech_aware_evidence_acquisition.rails.runner import (
    _protected_knowledge_material,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PINS_RELPATH = "docs/readiness/2026-09-17-slurp-semantic-store-release-pins-v2.json"
REGISTRATIONS = {
    "intent-boundaries-v2": (
        "docs/readiness/2026-09-17-slurp-intent-boundaries-preparation-registration-v3.json"
    ),
    "slot-contracts-v2": (
        "docs/readiness/2026-09-17-slurp-slot-contracts-preparation-registration-v2.json"
    ),
}
FRAGMENTS = {
    "intent-boundaries": "configs/baseline/slurp-native-dual-store-train-fold-a-intent-v2-v1.json",
    "slot-contracts": "configs/baseline/slurp-native-dual-store-train-fold-a-slot-v2-v1.json",
}
HELD_BASE = "configs/baseline/slurp-native-dual-store-train-fold-a-held-v1.json"
V1_NAMESPACES = {
    "intent-boundaries": "knowledge/slurp/semantic/intent-boundaries-v1",
    "slot-contracts": "knowledge/slurp/semantic/slot-contracts-v1",
}
# The control turns the anchor sends; the containment rule reads exactly these.
ANCHOR_CONTROL_TURNS = (
    "configs/probes/slurp_native_role_perception_v3.txt",
    "configs/probes/slurp_native_role_planner_v1.txt",
    "configs/probes/slurp_native_role_reviewer_v1.txt",
    "configs/probes/slurp_native_role_solver_v2.txt",
)
ANCHOR_TASK_CONTRACT = "configs/probes/slurp_native_role_context_v3.txt"
SEALED_FACET_INDEX = "prepared/SAEA-SLURP-INTENT-BOUNDARY-KEY-ENCODING-V1/index.json"
CHANGES_RELPATH = "prepared/SAEA-SLURP-SEMANTIC-AUTHORING-PREPARE-V2/CHANGES.json"
PREDECESSOR_REGISTRATIONS = {
    "intent-boundaries-v2": (
        "docs/readiness/2026-09-13-slurp-intent-boundaries-preparation-registration-v2.json"
    ),
    "slot-contracts-v2": (
        "docs/readiness/2026-09-13-slurp-slot-contracts-preparation-registration-v1.json"
    ),
}


def _json(path: Path) -> dict:
    return json.loads(path.read_bytes())


def _pins() -> dict:
    return _json(REPO_ROOT / PINS_RELPATH)


def _data_root() -> Path | None:
    root = os.environ.get("SPEECHRL_DATA_DIR")
    if not root:
        return None
    path = Path(root)
    return path if path.is_dir() else None


def _require_data_root() -> Path:
    root = _data_root()
    if root is None:
        pytest.skip(
            "the controlled data root is absent on this machine "
            "($SPEECHRL_DATA_DIR); the released v2 stores live only there"
        )
    return root


def _snapshot(root: Path, relpath: str) -> KnowledgeSnapshot:
    return KnowledgeSnapshot.from_frozen_json(_json(root / relpath))


def _released_pair(store: str) -> tuple[KnowledgeSnapshot, KnowledgeSnapshot]:
    root = _require_data_root()
    pins = _pins()["stores"][store]
    base = store.rsplit("-", 1)[0]
    return (
        _snapshot(root, f"{V1_NAMESPACES[base]}/snapshot.json"),
        _snapshot(root, pins["snapshot"]["relpath"]),
    )


# --- configuration ---------------------------------------------------------


def test_the_pins_document_agrees_with_both_registrations():
    pins = _pins()
    assert pins["schema"] == "saea-reviewed-semantic-store-release-pins-v2"
    assert set(pins["stores"]) == set(REGISTRATIONS)
    for store, relpath in REGISTRATIONS.items():
        raw = (REPO_ROOT / relpath).read_bytes()
        entry = pins["stores"][store]
        assert entry["registration"] == {
            "relpath": relpath,
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
        registration = json.loads(raw)
        assert registration["output_namespace"] == f"knowledge/slurp/semantic/{store}"
        assert registration["store_id"] == entry["store_id"]
        assert registration["store_role"] == entry["store_role"]
        assert registration["authored_source"]["relpath"] == (
            entry["authored_source"]["relpath"]
        )
        assert registration["authored_source"]["sha256"] == (
            entry["authored_source"]["sha256"]
        )
        # the revision changes the source only: builder, partition, split
        # identity, construction scope, permitted roster and the three
        # exclusion rosters are the v1 registration's, byte for byte.
        predecessor = _json(REPO_ROOT / PREDECESSOR_REGISTRATIONS[store])
        for field in (
            "carrier_lock_key",
            "source_partition_role",
            "source_split_identity_hash",
            "builder_policy_id",
            "store_id",
            "store_role",
            "construction_scope",
            "permitted_roster",
            "forbidden_rosters",
        ):
            assert registration[field] == predecessor[field], field


@pytest.mark.parametrize("store", sorted(FRAGMENTS))
def test_each_held_fragment_moves_exactly_one_store_to_v2(store: str):
    base = _json(REPO_ROOT / HELD_BASE)
    fragment = _json(REPO_ROOT / FRAGMENTS[store])
    pins = _pins()["stores"][f"{store}-v2"]
    other = next(name for name in FRAGMENTS if name != store)

    assert fragment["knowledge_stores"][store]["snapshot"] == {
        "relpath": pins["snapshot"]["relpath"],
        "sha256": pins["snapshot"]["sha256"],
    }
    assert fragment["knowledge_stores"][store]["release"] == {
        "relpath": pins["release"]["relpath"],
        "sha256": pins["release"]["sha256"],
    }
    assert fragment["knowledge_stores"][other] == base["knowledge_stores"][other]
    # the supply geometry of the moved store is the anchor's, untouched
    for key, value in base["knowledge_stores"][store].items():
        if key not in {"snapshot", "release"}:
            assert fragment["knowledge_stores"][store][key] == value, key

    moved = [
        receipt
        for receipt in fragment["preparation_source_receipts"]
        if receipt not in base["preparation_source_receipts"]
    ]
    assert sorted(receipt["relpath"] for receipt in moved) == sorted(
        (pins["completion"]["relpath"], pins["release"]["relpath"])
    )
    assert len(fragment["preparation_source_receipts"]) == len(
        base["preparation_source_receipts"]
    )

    assert fragment["prospective_phase_supply"]["state"] == "held"
    assert "native_contact_fit" not in fragment
    assert "prepared_phase_supply" not in fragment
    assert fragment["what_this_is"] != base["what_this_is"]

    for field in (
        "speech_feature_key_representation_id",
        "speech_feature_matcher_policy_id",
    ):
        assert fragment[field] != base[field]
        assert fragment[field].startswith("saea-slurp-task-agent-v1")
    # every other key is the held anchor's, byte for byte
    changed = {
        key
        for key in set(base) | set(fragment)
        if base.get(key) != fragment.get(key)
    }
    assert changed == {
        "knowledge_stores",
        "preparation_source_receipts",
        "prospective_phase_supply",
        "speech_feature_key_representation_id",
        "speech_feature_matcher_policy_id",
        "what_this_is",
    }


def test_the_two_fragments_do_not_share_a_speech_feature_identity():
    values = [
        (
            _json(REPO_ROOT / relpath)["speech_feature_key_representation_id"],
            _json(REPO_ROOT / relpath)["speech_feature_matcher_policy_id"],
        )
        for relpath in FRAGMENTS.values()
    ]
    assert len(set(values)) == len(values)


# --- released stores -------------------------------------------------------


@pytest.mark.parametrize("store", sorted(REGISTRATIONS))
def test_only_the_declared_cards_changed(store: str):
    before, after = _released_pair(store)
    root = _require_data_root()
    pins = _pins()["stores"][store]
    changes = _json(root / CHANGES_RELPATH)
    assert hashlib.sha256((root / CHANGES_RELPATH).read_bytes()).hexdigest() == (
        _pins()["revision_changes"]["sha256"]
    )
    declared = set(changes["stores"][store]["changed_ids"])
    dimension = "intent-boundary" if store.startswith("intent") else "slot-contract"

    old = {value.value_id: value.content for value in before.values}
    new = {value.value_id: value.content for value in after.values}
    assert set(old) == set(new)
    assert len(new) == pins["value_count"]
    moved = {name for name in new if new[name] != old[name]}
    assert moved == {f"{dimension}:{name}" for name in declared}
    assert len(new) - len(moved) == pins["unchanged_value_count"]
    for name in set(new) - moved:
        assert new[name] == old[name]


@pytest.mark.parametrize("store", sorted(REGISTRATIONS))
def test_every_retrieval_key_text_is_byte_identical(store: str):
    before, after = _released_pair(store)
    assert {facet.facet_id: facet.representation for facet in before.facets} == {
        facet.facet_id: facet.representation for facet in after.facets
    }


def test_the_sealed_intent_key_vectors_still_bind():
    """The facet text the key encoding run hashed is the text v2 renders."""
    root = _require_data_root()
    _, after = _released_pair("intent-boundaries-v2")
    sealed = {
        row["id"]: row["text_sha256"]
        for row in _json(root / SEALED_FACET_INDEX)["inputs"]["facets"]
    }
    built = {
        facet.facet_id: hashlib.sha256(
            facet.representation.encode("utf-8")
        ).hexdigest()
        for facet in after.facets
    }
    assert built == sealed


def test_the_slot_store_keeps_all_402_intent_bindings():
    root = _require_data_root()
    source = _json(
        root
        / "prepared/SAEA-SLURP-SEMANTIC-AUTHORING-PREPARE-V2/authored-slot-contracts-v2.json"
    )
    bindings = sum(len(row["intent_bindings"]) for row in source["rows"])
    assert bindings == _pins()["stores"]["slot-contracts-v2"]["intent_binding_count"]
    assert bindings == 402
    assert _pins()["stores"]["slot-contracts-v2"]["intent_bindings_added"] == []


@pytest.mark.parametrize("store", sorted(REGISTRATIONS))
def test_no_card_text_collides_with_the_anchor_control_turns(store: str):
    _, after = _released_pair(store)
    material = _protected_knowledge_material(after)
    assert material
    for relpath in (*ANCHOR_CONTROL_TURNS, ANCHOR_TASK_CONTRACT):
        instruction = (REPO_ROOT / relpath).read_text(encoding="utf-8")
        assert containment_collisions(material, instruction) == ()
        assert containment_collisions(material, instruction.casefold()) == ()


@pytest.mark.requires_umbrella_checkout
@pytest.mark.parametrize("store", sorted(REGISTRATIONS))
def test_no_card_text_collides_with_the_rendered_task_contract(store: str):
    from speech_aware_evidence_acquisition.core.instructions import (
        render_template_with_fill,
    )
    from speech_aware_evidence_acquisition.data.lock import (
        data_root,
        load_lock,
        umbrella_lock_path,
    )

    _, after = _released_pair(store)
    rendered = render_template_with_fill(
        "probes/slurp_native_role_context_v3.txt",
        "slurp-label-inventory",
        REPO_ROOT,
        load_lock(umbrella_lock_path(REPO_ROOT)),
        data_root(),
        None,
    )
    assert containment_collisions(_protected_knowledge_material(after), rendered) == ()


@pytest.mark.parametrize("store", sorted(REGISTRATIONS))
def test_the_released_bytes_are_the_pinned_bytes(store: str):
    root = _require_data_root()
    pins = _pins()["stores"][store]
    for key in ("snapshot", "release", "completion"):
        raw = (root / pins[key]["relpath"]).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        expected = (
            pins["snapshot_file_sha256"] if key == "snapshot" else pins[key]["sha256"]
        )
        assert digest == expected, key
    snapshot = _snapshot(root, pins["snapshot"]["relpath"])
    assert snapshot.content_hash() == pins["snapshot"]["sha256"]
    assert len(snapshot.source_sample_ids) == pins["source_recordings"]
