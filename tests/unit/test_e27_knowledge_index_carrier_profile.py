"""Item E27 (2026-09-21): the knowledge-INDEX rail as a carrier PROFILE.

Design: ``docs/superpowers/specs/2026-09-21-a2t-engineering-base-index-design
.md`` section 4. ``rails.knowledge_index`` was written for the SLURP carrier
by construction; this item factors every SLURP-specific constant and
callable into a :class:`~speech_aware_evidence_acquisition.rails
.knowledge_index.KnowledgeIndexCarrierProfile`, registered by
``carrier_lock_key``, and adds a second, DATA-ONLY ``audio2tool`` profile
beside it.

Every test here is model-free, tokenizer-free and offline: no utterance text
or gold of any row appears anywhere, and the one test that reads the sealed
SLURP view reads it READ-ONLY and skips when it is not mounted.

The proofs:

1. the ``slurp`` profile equals the pre-refactor literals, pinned here so a
   future edit to the profile cannot silently drift from what shipped before
   this item;
2. :func:`knowledge_index_profile` resolves the ``audio2tool`` profile at
   the values design section 3/4 fix, and refuses an unknown carrier by
   naming both it and the registered carriers;
3. ``domain-alphabetical-v1`` orders a tiny synthetic registry exactly as
   ``data.audio2tool_tools.render_registry_grouped``'s upstream algorithm
   does (sorted domain, then sorted tool name within it);
4. the Audio2Tool ``perception_candidates`` reader extracts
   ``actions[].candidate_tools`` in first-seen order and tolerates the
   malformed shapes a live row's Perception state might return;
5. THE BYTE GUARD: the released SLURP view, re-rendered at the recommended
   ("decision-52") defaults through the unchanged :func:`render_constant_
   index`, reproduces the sealed IDX receipts' system-message sha256 and
   character count byte for byte after the refactor.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails import knowledge_index as ki

# ---------------------------------------------------------------------------
# 1. The slurp profile equals the pre-refactor literals, pinned by hand.
# ---------------------------------------------------------------------------


def test_slurp_profile_pins_the_pre_refactor_literals():
    profile = ki.knowledge_index_profile("slurp")

    assert profile.carrier == "slurp"
    assert profile.pin_namespace == "knowledge/slurp/semantic/"
    assert dict(profile.view_ids) == {
        "slurp-knowledge-index-v1": None,
        "slurp-knowledge-index-twin-v1": "slurp-knowledge-index-v1",
    }
    assert profile.entry_kinds == ("intent", "slot", "edge", "exemplar")
    assert profile.constant_index_kinds == ("intent", "slot", "edge")
    assert dict(profile.kind_sigils) == {
        "intent": "I", "slot": "S", "edge": "E", "exemplar": "X",
    }
    assert dict(profile.l1_section_choices) == {
        "intent": ("Activation boundary", "Confusable exclusions"),
        "slot": ("Admissible formats", "Extraction cues"),
        "edge": ("Confusable exclusions",),
    }
    assert dict(profile.default_l1_sections) == {
        "intent": "Activation boundary",
        "slot": "Admissible formats",
        "edge": "Confusable exclusions",
    }
    assert dict(profile.hoisted_sections) == {
        "intent": ("Uncertainty behavior",),
        "slot": ("Missing behavior",),
    }
    assert dict(profile.default_granularity) == {
        "intent": "L1", "slot": "L1", "edge": "L0",
    }
    assert dict(profile.default_pointer_budget) == {
        "intent": 3, "slot": 8, "exemplar_vote": 3,
    }
    assert dict(profile.default_expansion_budget) == {
        "exemplar": 5, "slot_card": 4, "intent_card": 0,
    }
    assert profile.exemplar_store_role == "train-exemplars"
    assert dict(profile.evidence_prefixes) == {
        "intent": "intent-boundaries::intent-boundary:",
        "slot": "slot-contracts::slot-contract:",
        "exemplar": "train-exemplars::value:",
    }
    assert ki.TAXONOMY_FREQUENCY_ORDERING in profile.orderings
    assert profile.orderings[ki.TAXONOMY_FREQUENCY_ORDERING] is ki.taxonomy_frequency_order


def test_slurp_profile_fields_are_the_module_level_names_by_identity():
    """Every historic module-level import keeps working -- and reads the
    SAME object the profile carries, not a copy."""

    profile = ki.knowledge_index_profile("slurp")
    assert profile.carrier == ki.KNOWLEDGE_INDEX_CARRIER
    assert profile.pin_namespace == ki.PIN_NAMESPACE
    assert profile.kind_sigils is ki.KIND_SIGILS
    assert profile.entry_kinds is ki.ENTRY_KINDS
    assert profile.constant_index_kinds is ki.CONSTANT_INDEX_KINDS
    assert profile.l1_section_choices is ki.L1_SECTION_CHOICES
    assert profile.default_l1_sections is ki.DEFAULT_L1_SECTIONS
    assert profile.hoisted_sections is ki.HOISTED_SECTIONS
    assert profile.default_granularity is ki.DEFAULT_GRANULARITY
    assert profile.default_pointer_budget is ki.DEFAULT_POINTER_BUDGET
    assert profile.default_expansion_budget is ki.DEFAULT_EXPANSION_BUDGET
    assert profile.exemplar_store_role == ki.EXEMPLAR_STORE_ROLE
    assert set(profile.view_ids) == set(ki.KNOWLEDGE_INDEX_VIEW_IDS)


# ---------------------------------------------------------------------------
# 2. The audio2tool profile, and the unknown-carrier refusal.
# ---------------------------------------------------------------------------


def test_audio2tool_profile_matches_the_design():
    profile = ki.knowledge_index_profile("audio2tool")

    assert profile.carrier == "audio2tool"
    assert dict(profile.view_ids) == {
        "a2t-knowledge-index-v1": None,
        "a2t-knowledge-index-twin-v1": "a2t-knowledge-index-v1",
    }
    assert profile.pin_namespace == "knowledge/audio2tool/semantic/"
    assert profile.entry_kinds == ("domain", "tool", "edge", "exemplar")
    assert profile.constant_index_kinds == ("domain", "tool", "edge")
    assert dict(profile.kind_sigils) == {
        "domain": "D", "tool": "T", "edge": "E", "exemplar": "X",
    }
    assert dict(profile.l1_section_choices) == {
        "tool": (
            "Activation boundary", "Admissible arguments", "Confusable exclusions",
        ),
    }
    assert dict(profile.default_l1_sections) == {"tool": "Activation boundary"}
    assert dict(profile.hoisted_sections) == {}
    assert dict(profile.default_granularity) == {
        "tool": "L1", "domain": "L0", "edge": "L0",
    }
    assert dict(profile.default_pointer_budget) == {
        "tool": 8, "domain": 3, "edge": 4, "exemplar_vote": 0,
    }
    assert dict(profile.default_expansion_budget) == {
        "exemplar": 0, "tool_card": 4, "domain_card": 0,
    }
    assert profile.exemplar_store_role == "construction-exemplars"
    assert dict(profile.evidence_prefixes) == {
        "tool": "tool-activation::tool:",
        "edge": "tool-edges::edge:",
        "exemplar": "construction-exemplars::value:",
    }
    assert ki.DOMAIN_ALPHABETICAL_ORDERING in profile.orderings
    assert (
        profile.orderings[ki.DOMAIN_ALPHABETICAL_ORDERING] is ki.domain_alphabetical_order
    )
    assert profile.perception_candidates is ki._a2t_perception_candidates


def test_unknown_carrier_names_itself_and_the_known_carriers():
    with pytest.raises(ValueError) as excinfo:
        ki.knowledge_index_profile("earnings21")
    message = str(excinfo.value)
    assert "earnings21" in message
    assert "audio2tool" in message
    assert "slurp" in message


def test_registered_carriers_are_exactly_slurp_and_audio2tool():
    assert set(ki.KNOWLEDGE_INDEX_CARRIER_PROFILES) == {"slurp", "audio2tool"}
    assert ki.knowledge_index_profile("slurp") is ki.KNOWLEDGE_INDEX_CARRIER_PROFILES["slurp"]


# ---------------------------------------------------------------------------
# 3. domain-alphabetical-v1: a tiny synthetic registry, ORG-1's own order.
# ---------------------------------------------------------------------------


def test_domain_alphabetical_order_registered_beside_taxonomy_frequency():
    assert ki.DOMAIN_ALPHABETICAL_ORDERING in ki.registered_orderings()
    assert (
        ki.resolve_ordering(ki.DOMAIN_ALPHABETICAL_ORDERING) is ki.domain_alphabetical_order
    )


def test_domain_alphabetical_order_matches_org1_upstream_algorithm():
    """``for domain, domain_tools in sorted(domains.items()): ... for tool in
    sorted(domain_tools, key=lambda x: x['name'])`` -- reproduced by hand
    over a tiny synthetic registry, then checked against the function under
    test. Stand-ins use the ``edge`` kind (already legal to construct) with
    ``group`` set to the domain and the tool name embedded as the edge's
    source, because sorting by a fixed-prefix id sorts by the name it
    embeds -- the same property the real ``tool`` entries item E28 builds
    will have.
    """

    registry = [
        ("music", "play_music"),
        ("music", "adjust_volume"),
        ("navigation", "set_destination"),
        ("alarm", "snooze_alarm"),
        ("alarm", "cancel_alarm"),
    ]
    domains: dict[str, list[str]] = {}
    for domain, name in registry:
        domains.setdefault(domain, []).append(name)
    expected: list[tuple[str, str]] = []
    for domain, tools in sorted(domains.items()):
        for name in sorted(tools):
            expected.append((domain, name))

    entries = tuple(
        ki.IndexEntry(
            entry_id=ki.edge_id(name, "reference_pair"),
            kind="edge",
            group=domain,
            rank=0,
            l1={"Confusable exclusions": f"{name} is distinct from reference_pair."},
        )
        for domain, name in registry
    )
    ordered = ki.domain_alphabetical_order(entries)
    actual = [
        (entry.group, ki.parse_index_id(entry.entry_id)[1][0]) for entry in ordered
    ]
    assert actual == expected


# ---------------------------------------------------------------------------
# 4. The A2T Perception-candidate reader.
# ---------------------------------------------------------------------------


def test_a2t_perception_candidates_reads_actions_shape():
    document = {
        "actions": [
            {"action_id": "a1", "candidate_tools": ["play_music", "adjust_volume"]},
            {"action_id": "a2", "candidate_tools": ["adjust_volume", "set_alarm"]},
        ],
        "global_constraints": [],
    }
    assert ki._a2t_perception_candidates(document) == (
        "play_music", "adjust_volume", "set_alarm",
    )


@pytest.mark.parametrize(
    "document",
    [
        None,
        {},
        {"actions": "not-a-list"},
        {"actions": [{"candidate_tools": "not-a-list"}]},
        {"actions": [{"candidate_tools": [1, None, ""]}]},
        {"actions": [None, {"candidate_tools": ["x"]}]},
    ],
)
def test_a2t_perception_candidates_tolerates_malformed_shapes(document):
    result = ki._a2t_perception_candidates(document)
    assert isinstance(result, tuple)


def test_slurp_perception_candidates_document_reader():
    document = {
        "candidates": [
            {"intent_id": "play_music"}, {"intent_id": "play_radio"},
            {"intent_id": "play_music"},
        ],
    }
    assert ki._slurp_perception_candidates(document) == (
        "play_music", "play_radio", "play_music",
    )
    assert ki._slurp_perception_candidates({"candidates": "nope"}) == ()
    assert ki._slurp_perception_candidates(None) == ()


# ---------------------------------------------------------------------------
# 5. THE BYTE GUARD: the released SLURP view is unchanged by this refactor.
# ---------------------------------------------------------------------------

_RELEASED_SNAPSHOT_RELPATH = (
    "knowledge/slurp/semantic/slurp-knowledge-index-v1/snapshot.json"
)
_EXPECTED_SHA256 = (
    "b279dcc016d8fea5bc22f942a404dbcd87c36294780e9b977a4b2da6238d4438"
)
_EXPECTED_CHARS = 17265


def _released_snapshot_path() -> Path | None:
    root = os.environ.get("SPEECHRL_DATA_DIR")
    if not root:
        return None
    path = Path(root) / _RELEASED_SNAPSHOT_RELPATH
    return path if path.is_file() else None


@pytest.mark.skipif(
    _released_snapshot_path() is None,
    reason="the released slurp-knowledge-index-v1 snapshot is not present under "
           "SPEECHRL_DATA_DIR on this machine",
)
def test_byte_guard_released_slurp_view_renders_identical_bytes():
    path = _released_snapshot_path()
    assert path is not None
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    table = ki.table_from_snapshot(snapshot)

    # The decision-52 defaults: a config declaring only the pins, exactly as
    # scripts/slurp_knowledge_index_render_proof.py resolves its "armed
    # -defaults" arm.
    pins = {
        "view": table.view_id,
        "release": {
            "relpath": f"knowledge/slurp/semantic/{table.view_id}/release.json",
            "root": "data", "sha256": "0" * 64,
        },
        "snapshot": {
            "relpath": f"knowledge/slurp/semantic/{table.view_id}/snapshot.json",
            "root": "data", "sha256": "0" * 64,
        },
    }
    plan = ki.parse_knowledge_index_config(pins)
    index_text = ki.render_constant_index(table, plan)

    assert len(index_text) == _EXPECTED_CHARS
    assert ki.sha256_text(index_text) == _EXPECTED_SHA256

    # And the recommended-defaults helper agrees, with no pins at all.
    default_text = ki.render_constant_index(table, ki.default_index_plan())
    assert default_text == index_text
