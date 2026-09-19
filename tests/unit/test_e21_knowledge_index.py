"""Item E21 (the knowledge index; not the Earnings-21 carrier): the knowledge
INDEX and index-based context assembly.

Design: ``docs/superpowers/specs/2026-09-19-knowledge-index-and-context-assembly
-design.md`` (sections 3, 4, 6 and 7.0) and the item note
``docs/superpowers/specs/2026-09-19-e21-knowledge-index-design.md``.

Every test here is model-free, tokenizer-free and offline: the view under test
is a SYNTHETIC store built in this module, the one test that touches the
sealed B1 arm reads HASHES ONLY and skips when the controlled data root is not
mounted, and no utterance text or gold of any evaluated row appears anywhere.

The proofs, in the order the item's design note lists them:

1. the eight fail-closed loader refusals of design section 6.4;
2. the key's own falsifier -- with the key ABSENT the composed request is
   byte-identical and the receipt carries no block;
3. the layout rule and the truncation property of design sections 4.1/4.4;
4. ordering determinism;
5. id-grammar membership against the closed inventory;
6. the hoist is lossless: index text = header + per-card residue;
7. the receipt's schema;
8. the render proof, end to end, on the synthetic store.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails import knowledge_index as ki
from speech_aware_evidence_acquisition.rails.config_tables import (
    EPISODE_LEVEL_SWITCH_KEYS,
    is_episode_null_arm,
    resolve_episode_switch_key,
)
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    load_native_episode_config,
)

from test_native_episode_config import config as _episode_values
from test_native_episode_config import program as _episode_program

# ---------------------------------------------------------------------------
# A synthetic released view. Three scenarios, six intents, three slot types,
# two edges -- small enough to assert on by hand, shaped exactly like the
# released one.
# ---------------------------------------------------------------------------

SHARED_INTENT = (
    "Uncertainty behavior: Keep plausible alternatives when the request stays "
    "ambiguous."
)
SHARED_SLOT_A = "Missing behavior: Omit this slot when no supported mention is present."
SHARED_SLOT_B = "Missing behavior: Emit this slot whenever the period is spoken."

LEGAL_INTENTS = (
    "alarm_query", "alarm_set", "play_music", "play_radio", "qa_factoid", "qa_maths",
)
LEGAL_SLOTS = ("artist_name", "date", "song_name", "unused_type")
CARDED_SLOTS = ("artist_name", "date", "song_name")
SCENARIO_OF = {
    "alarm_query": "alarm", "alarm_set": "alarm",
    "play_music": "play", "play_radio": "play",
    "qa_factoid": "qa", "qa_maths": "qa",
}
ROWS = {
    "alarm_query": 85, "alarm_set": 120, "play_music": 300, "play_radio": 90,
    "qa_factoid": 40, "qa_maths": 40,
}
EDGES = (("play_music", "play_radio", 60), ("alarm_set", "alarm_query", 30))


def _intent_card(name: str) -> str:
    return (
        f"Intent {name}.\n"
        f"Activation boundary:\n- The {name.replace('_', ' ')} request.\n"
        f"Confusable exclusions:\n"
        f"- play_radio: A station is a radio request, a track is not.\n"
        f"{SHARED_INTENT}\n"
        f"Limitations:\n- Bounded TRAIN support."
    )


def _slot_card(name: str) -> str:
    shared = SHARED_SLOT_A if name != "date" else SHARED_SLOT_B
    return (
        f"Slot {name}.\n"
        f"Intent bindings and semantic roles:\n"
        f"- play_music: The {name.replace('_', ' ')} spoken in the request\n"
        f"Extraction cues:\n- Listen for the spoken {name.replace('_', ' ')}.\n"
        f"Admissible formats:\n- Keep the spoken form; never normalise it.\n"
        f"{shared}\n"
        f"Ambiguity behavior:\n- Prefer the nearer mention.\n"
        f"Limitations:\n- Bounded TRAIN support."
    )


def _labels_for(card: str, texts: dict[str, str]) -> dict[str, str]:
    sections = ki.parse_card_sections(card)
    return {
        section.text: texts[section.text]
        for section in sections
        if section.text in texts
    }


def synthetic_snapshot() -> dict:
    shared_texts = {
        SHARED_INTENT: "IU-1", SHARED_SLOT_A: "SM-1", SHARED_SLOT_B: "SM-2",
    }
    entries = []
    for name in LEGAL_INTENTS:
        card = _intent_card(name)
        sections = [
            section for section in ki.parse_card_sections(card)
            if section.name in ki.HOISTED_SECTIONS["intent"]
        ]
        residue, hoisted = ki.hoist_sections(
            card, sections=sections, labels=_labels_for(card, shared_texts)
        )
        by_name = {s.name: s for s in ki.parse_card_sections(card)}
        entries.append(
            ki.IndexEntry(
                entry_id=ki.intent_id(name), kind="intent", group=SCENARIO_OF[name],
                rank=ROWS[name],
                l1={
                    key: ki.section_body(by_name[key])
                    for key in ("Activation boundary", "Confusable exclusions")
                },
                residue=residue, hoisted=hoisted,
            ).as_json()
        )
    for name in CARDED_SLOTS:
        card = _slot_card(name)
        sections = [
            section for section in ki.parse_card_sections(card)
            if section.name in ki.HOISTED_SECTIONS["slot"]
        ]
        residue, hoisted = ki.hoist_sections(
            card, sections=sections, labels=_labels_for(card, shared_texts)
        )
        by_name = {s.name: s for s in ki.parse_card_sections(card)}
        entries.append(
            ki.IndexEntry(
                entry_id=ki.slot_id(name), kind="slot", group="", rank=1,
                l1={
                    key: ki.section_body(by_name[key])
                    for key in ("Admissible formats", "Extraction cues")
                },
                residue=residue, hoisted=hoisted,
            ).as_json()
        )
    for source, neighbour, leaked in EDGES:
        entries.append(
            ki.IndexEntry(
                entry_id=ki.edge_id(source, neighbour), kind="edge",
                group=SCENARIO_OF[source], rank=leaked,
                l1={"Confusable exclusions": f"{leaked} neighbours of {source} carry "
                                             f"{neighbour}."},
            ).as_json()
        )
    return {
        "schema": ki.KNOWLEDGE_INDEX_VIEW_SCHEMA,
        "view_id": ki.KNOWLEDGE_INDEX_VIEW_ID,
        "builder_policy_id": ki.KNOWLEDGE_INDEX_BUILDER_POLICY_ID,
        "carrier": "slurp",
        "ordering": ki.TAXONOMY_FREQUENCY_ORDERING,
        "source_split": "train",
        "source_split_identity_hash": "0" * 64,
        "construction_utterance_count": 9354,
        "legal_intents": list(LEGAL_INTENTS),
        "legal_slot_types": list(LEGAL_SLOTS),
        "store_pins": {},
        "shared_sections": [
            {"label": "IU-1", "kind": "intent", "section": "Uncertainty behavior",
             "text": SHARED_INTENT},
            {"label": "SM-1", "kind": "slot", "section": "Missing behavior",
             "text": SHARED_SLOT_A},
            {"label": "SM-2", "kind": "slot", "section": "Missing behavior",
             "text": SHARED_SLOT_B},
        ],
        "entries": entries,
    }


@pytest.fixture()
def table():
    return ki.table_from_snapshot(synthetic_snapshot())


def _pins(view=ki.KNOWLEDGE_INDEX_VIEW_ID):
    return {
        "view": view,
        "release": {
            "relpath": f"knowledge/slurp/semantic/{ki.KNOWLEDGE_INDEX_VIEW_ID}/release.json",
            "root": "data", "sha256": "a" * 64,
        },
        "snapshot": {
            "relpath": f"knowledge/slurp/semantic/{ki.KNOWLEDGE_INDEX_VIEW_ID}/snapshot.json",
            "root": "data", "sha256": "b" * 64,
        },
    }


@pytest.fixture()
def plan():
    return ki.parse_knowledge_index_config(_pins())


def _selection():
    return ki.RowSelection(
        candidates=("play_music", "play_radio", "qa_factoid"),
        exemplar_votes=(("play_music", 15), ("play_radio", 3), ("qa_factoid", 2)),
        slot_types=("song_name", "artist_name", "date"),
        exemplars=tuple((str(10000 + index), f"utterance {index} | play_music | none")
                        for index in range(8)),
    )


# ---------------------------------------------------------------------------
# 1. The switch key itself.
# ---------------------------------------------------------------------------


def test_the_key_resolves_in_the_episode_class_and_its_off_arm_is_its_absence():
    key = "native_episode.knowledge_index"
    assert key in EPISODE_LEVEL_SWITCH_KEYS
    assert resolve_episode_switch_key(key) == key
    assert is_episode_null_arm(key, None) is True
    assert is_episode_null_arm(key, _pins()) is False


# ---------------------------------------------------------------------------
# 2. The id grammar and its membership check.
# ---------------------------------------------------------------------------


def test_the_id_grammar_is_the_closed_inventory_verbatim():
    assert ki.intent_id("play_music") == "I/play_music"
    assert ki.slot_id("artist_name") == "S/artist_name"
    assert ki.edge_id("play_music", "play_radio") == "E/play_music~play_radio"
    assert ki.exemplar_id(10005) == "X/10005"
    assert ki.parse_index_id("E/play_music~play_radio") == (
        "edge", ("play_music", "play_radio")
    )
    # Rule 1: a synonym, a capitalised spelling or a number is not a name.
    for bad in ("I/Play_Music", "I/play music", "I/", "Q/play_music", "play_music"):
        assert ki.is_index_id(bad) is False
    # An edge joins two DIFFERENT intents.
    with pytest.raises(ki.KnowledgeIndexError):
        ki.edge_id("play_music", "play_music")


def test_every_entry_id_is_a_member_of_the_closed_inventory(table):
    for entry in table.entries:
        kind, parts = ki.parse_index_id(entry.entry_id)
        if kind == "intent":
            assert parts[0] in table.legal_intents
        elif kind == "slot":
            assert parts[0] in table.legal_slot_types
        else:
            assert all(part in table.legal_intents for part in parts)
    # Membership, not parsing: a well-formed id the view does not carry does
    # NOT resolve, which is what makes a hallucinated citation detectable.
    assert table.resolves("I/play_music") is True
    assert table.resolves("S/unused_type") is False
    assert table.resolves("I/email_query") is False


def test_a_citation_is_extracted_from_free_text_and_checked_by_membership(table):
    cited = ki.extract_citations(
        "The request is I/play_music, not I/play_radio; the filler is S/song_name. "
        "I also considered I/email_query."
    )
    assert cited == ("I/play_music", "I/play_radio", "S/song_name", "I/email_query")
    assert [table.resolves(value) for value in cited] == [True, True, True, False]


# ---------------------------------------------------------------------------
# 3. The hoist is lossless (design Q6, finding F-5).
# ---------------------------------------------------------------------------


def test_the_hoist_preserves_every_card_byte_for_byte(table):
    shared = table.shared()
    originals = {
        **{ki.intent_id(name): _intent_card(name) for name in LEGAL_INTENTS},
        **{ki.slot_id(name): _slot_card(name) for name in CARDED_SLOTS},
    }
    hoisted_entries = [entry for entry in table.entries if entry.hoisted]
    assert len(hoisted_entries) == len(LEGAL_INTENTS) + len(CARDED_SLOTS)
    for entry in hoisted_entries:
        restored = ki.restore_card(entry.residue, entry.hoisted, shared)
        assert restored == originals[entry.entry_id]
        # The residue really is SHORTER -- a hoist that saved nothing would
        # be a second copy of the store in the index header.
        assert len(entry.residue) < len(restored)
        for item in entry.hoisted:
            assert shared[item.label] not in entry.residue


def test_the_view_round_trips_and_its_content_hash_is_its_own_bytes(table):
    """The loader re-types nothing: a view's content hash is a function of the
    released BYTES, not of the loader that read them, so a receipt's
    ``content_hash`` and the released snapshot's own sha256 are one number."""

    document = synthetic_snapshot()
    assert ki.table_from_snapshot(document).as_json() == document
    assert table.content_hash() == hashlib.sha256(
        ki.canonical_json(document).encode("utf-8")
    ).hexdigest()


def test_a_shared_section_the_view_does_not_carry_is_refused(table):
    entry = next(item for item in table.entries if item.hoisted)
    with pytest.raises(ki.KnowledgeIndexError, match="absent"):
        ki.restore_card(entry.residue, entry.hoisted, {})


# ---------------------------------------------------------------------------
# 4. Ordering determinism (design section 3.4).
# ---------------------------------------------------------------------------


def test_the_ordering_is_registered_declared_and_total(table):
    assert ki.TAXONOMY_FREQUENCY_ORDERING in ki.registered_orderings()
    order = ki.resolve_ordering(ki.TAXONOMY_FREQUENCY_ORDERING)
    first = order(table.entries)
    # Deterministic: the same input, and any permutation of it, orders the
    # same way. A rendered index is a pure function of the view.
    assert order(tuple(reversed(table.entries))) == first
    ids = [entry.entry_id for entry in first]
    assert len(ids) == len(set(ids)) == len(table.entries)
    # (a) taxonomy first, (b) construction frequency within a scenario,
    # (c) an intent's edges on the line after it.
    assert ids.index("I/alarm_set") < ids.index("I/alarm_query")
    assert ids.index("E/alarm_set~alarm_query") == ids.index("I/alarm_set") + 1
    assert ids.index("I/play_music") < ids.index("I/play_radio")
    assert ids.index("E/play_music~play_radio") == ids.index("I/play_music") + 1
    # Slots are their own group, last.
    assert min(ids.index(ki.slot_id(name)) for name in CARDED_SLOTS) > max(
        ids.index(ki.intent_id(name)) for name in LEGAL_INTENTS
    )


def test_an_unregistered_ordering_is_refused():
    with pytest.raises(ki.KnowledgeIndexError, match="ordering"):
        ki.resolve_ordering("alphabetical-v1")
    with pytest.raises(ki.KnowledgeIndexError):
        ki.parse_knowledge_index_config({**_pins(), "ordering": "alphabetical-v1"})


# ---------------------------------------------------------------------------
# 5. The constant index.
# ---------------------------------------------------------------------------


def test_the_index_is_constant_and_the_granularity_is_a_config_value(table, plan):
    text = ki.render_constant_index(table, plan)
    assert ki.render_constant_index(table, plan) == text  # pure
    assert ki.index_suffix(table, plan) == f"\n\n{text}"
    # L1 carries the operative line, L0 carries the id alone and is strictly
    # shorter -- which is what makes the L1 -> L0 degradation step real.
    assert "I/play_music  The play music request." in text
    l0 = ki.render_constant_index(
        table,
        ki.parse_knowledge_index_config(
            {**_pins(), "granularity": {"intent": "L0", "slot": "L0", "edge": "L0"}}
        ),
    )
    assert "I/play_music" in l0
    assert "The play music request." not in l0
    assert len(l0) < len(text)
    # Q3/Q4 answered as config: which section is the L1 line.
    cues = ki.render_constant_index(
        table,
        ki.parse_knowledge_index_config(
            {**_pins(),
             "granularity": {"slot": {"level": "L1", "section": "Extraction cues"}}}
        ),
    )
    assert "S/song_name  Listen for the spoken song name." in cues
    # The shared guidance is paid for ONCE, in the header, not per card.
    assert text.count(SHARED_INTENT) == 1
    assert text.count(SHARED_SLOT_A) == 1


def test_the_exemplar_kind_is_never_in_the_constant_index(table):
    assert "exemplar" not in ki.CONSTANT_INDEX_KINDS
    assert table.kinds <= set(ki.CONSTANT_INDEX_KINDS)
    with pytest.raises(ki.KnowledgeIndexError, match="pointer-and-expansion only"):
        ki.IndexEntry(
            entry_id="X/10005", kind="exemplar", group="", rank=0, l1={"a": "b"}
        )


# ---------------------------------------------------------------------------
# 6. The assembly: layout and truncation (design sections 4.1 and 4.4).
# ---------------------------------------------------------------------------


def test_the_pointer_block_names_ids_and_ranks_and_nothing_else(table, plan):
    block = ki.assemble(table, plan, _selection(), role_id="solver")
    assert "I/play_music (rank 1)" in block.pointer_block
    assert "I/play_music x 15" in block.pointer_block
    assert "S/song_name" in block.pointer_block
    # The pointer block carries no card text at all: that is the whole point.
    assert SHARED_INTENT not in block.pointer_block
    assert "The play music request." not in block.pointer_block
    assert block.pointer_ids[0] == "I/play_music"
    # Budgets bound it, highest rank / vote first.
    narrow = ki.assemble(
        table,
        ki.parse_knowledge_index_config(
            {**_pins(), "pointer_budget": {"intent": 1, "slot": 0, "exemplar_vote": 1}}
        ),
        _selection(),
        role_id="solver",
    )
    assert "I/play_radio" not in narrow.pointer_block
    assert ki.NO_SLOT_TYPES in narrow.pointer_block


def test_an_empty_selection_uses_the_closed_empty_phrases(table, plan):
    block = ki.assemble(table, plan, ki.RowSelection(), role_id="solver")
    for phrase in ki.POINTER_VOCABULARY:
        assert phrase in block.pointer_block
    assert block.expansions == ()
    assert block.expansion_text == ""


def test_the_expansion_block_is_last_and_ordered_by_class(table, plan):
    block = ki.assemble(table, plan, _selection(), role_id="solver")
    ids = block.expanded_ids
    assert ids[:5] == tuple(f"X/1000{index}" for index in range(5))
    assert set(ids[5:]) == {"S/song_name", "S/artist_name", "S/date"}
    parts = block.content_parts()
    assert parts[0]["evidence_id"] == ki.POINTER_BLOCK_EVIDENCE_ID
    assert [part["evidence_id"] for part in parts[1:]] == list(ids)
    # An expanded card reads as its residue plus a REFERENCE to the shared
    # guidance the index header already carries -- never a second copy.
    card = next(part for part in parts if part["evidence_id"] == "S/date")
    assert SHARED_SLOT_B not in card["text"]
    assert "Shared guidance: SM-2" in card["text"]


def test_truncating_the_expansion_tail_moves_no_byte_before_it(table, plan):
    full = ki.assemble(table, plan, _selection(), role_id="solver")
    reduced = ki.assemble(
        table,
        ki.parse_knowledge_index_config(
            {**_pins(), "expansion_budget": {"slot_card": 0}}
        ),
        _selection(),
        role_id="solver",
    )
    full_parts = full.content_parts()
    reduced_parts = reduced.content_parts()
    kept = len(reduced.expansions)
    assert kept < len(full.expansions)
    # The narrowed block is the full block with a CONTIGUOUS run removed from
    # the END, and every byte before that point is identical.
    assert reduced_parts == full_parts[: 1 + kept]
    assert reduced.pointer_block == full.pointer_block
    assert full.expansion_text.startswith(reduced.expansion_text)
    # Zero is a legal value of the slot-card budget (design question Q8).
    assert ki.DEFAULT_EXPANSION_BUDGET["slot_card"] == 4
    assert reduced.expansions


def test_the_degradation_ladder_spends_the_tail_first_and_never_l0(table, plan):
    block = ki.assemble(table, plan, _selection(), role_id="solver")
    items = ki.index_droppable_items(block)
    blocks = [item.block for item in items]
    assert blocks[: len(block.expansions)] == [ki.INDEX_EXPANSION_BLOCK] * len(
        block.expansions
    )
    assert blocks[-2:] == [ki.INDEX_POINTER_BLOCK, ki.INDEX_GRANULARITY_BLOCK]
    # Tail first: the LAST expansion is the FIRST thing dropped.
    assert items[0].identifier == f"value:{block.expanded_ids[-1]}"
    # Pointers and the granularity fall in a later tranche than expansions.
    assert {item.tranche for item in items if item.block == ki.INDEX_EXPANSION_BLOCK} == {1}
    assert {item.tranche for item in items if item.block != ki.INDEX_EXPANSION_BLOCK} == {2}
    # Rule 4: the L0 index, the contract, the speech packet and the states are
    # never droppable, and a recorded step says so out loud.
    step = ki.degradation_step(items[0], pass_index=1)
    assert step["never_droppable"] == list(ki.INDEX_NEVER_DROPPABLE)
    assert "l0-index" in ki.INDEX_NEVER_DROPPABLE


def test_a_per_role_budget_override_is_off_by_default_and_expressible(table):
    default = ki.parse_knowledge_index_config(_pins())
    assert default.role_budgets == {}
    # Q12's default: every role receives the Solver's own block.
    assert default.budget_for("planner") == default.budget_for("solver")
    override = ki.parse_knowledge_index_config(
        {
            **_pins(),
            "roles": {
                "planner": {
                    "pointer_budget": {"intent": 0, "slot": 0, "exemplar_vote": 0},
                    "expansion_budget": {
                        "exemplar": 0, "slot_card": 0, "intent_card": 0,
                    },
                }
            },
        }
    )
    planner = ki.assemble(table, override, _selection(), role_id="planner")
    solver = ki.assemble(table, override, _selection(), role_id="solver")
    assert planner.expansions == ()
    assert planner.pointer_ids == ()
    assert solver.expansions


# ---------------------------------------------------------------------------
# 7. The loader's eight refusals (design section 6.4).
# ---------------------------------------------------------------------------


def _armed_values(index_block=None, **overrides):
    values = _episode_values()
    values["carrier_lock_key"] = overrides.pop("carrier_lock_key", "slurp")
    values["phase_tools"] = {
        "reviewer": {
            "mode": "native-tools", "source_authority_role": "reviewer",
            "allowed_tools": ["analyze"],
        }
    }
    values["native_episode"]["tool_schema_rendering"] = overrides.pop(
        "tool_schema_rendering", "constant"
    )
    values["knowledge_stores"] = overrides.pop(
        "knowledge_stores",
        {
            "train-exemplars": {
                "store_role": "train-exemplars",
                "phase_supply": {"solver": {"k": 20}},
            },
            "slot-contracts": {
                "store_role": "slot-contracts",
                "candidate_supply": {
                    "solver": {"max_candidates": 3, "max_total_values": 28},
                },
            },
        },
    )
    values["native_episode"]["knowledge_index"] = (
        _pins() if index_block is None else index_block
    )
    for key, value in overrides.items():
        values[key] = value
    return values


def test_the_armed_key_composes_and_carries_its_canonical_text():
    parsed = load_native_episode_config(_armed_values(), _episode_program())
    assert parsed.knowledge_index_json is not None
    document = json.loads(parsed.knowledge_index_json)
    assert document["view"] == ki.KNOWLEDGE_INDEX_VIEW_ID
    assert document["ordering"] == ki.TAXONOMY_FREQUENCY_ORDERING
    assert document["solver_citation"] == "permitted"
    assert document["granularity"]["intent"] == {
        "level": "L1", "section": "Activation boundary"
    }
    assert document["granularity"]["slot"] == {
        "level": "L1", "section": "Admissible formats"
    }
    assert document["expansion_budget"]["slot_card"] == 4
    # Two spellings of one arm compose ONE identity: the canonical text is a
    # function of meaning, not of how the fragment wrote it.
    spelled = _armed_values(
        {**_pins(), "granularity": {"intent": {"level": "L1",
                                               "section": "Activation boundary"}}}
    )
    assert (
        load_native_episode_config(spelled, _episode_program()).knowledge_index_json
        == parsed.knowledge_index_json
    )


def test_refusal_1_an_unreleased_view():
    with pytest.raises(ValueError, match="not a released knowledge-index view"):
        load_native_episode_config(
            _armed_values(_pins(view="slurp-knowledge-index-v2")), _episode_program()
        )
    for field in ("release", "snapshot"):
        broken = _pins()
        broken[field] = {**broken[field], "root": "repo"}
        with pytest.raises(ValueError, match="controlled data root"):
            load_native_episode_config(_armed_values(broken), _episode_program())


def test_refusal_2_a_granularity_the_view_does_not_carry():
    with pytest.raises(ValueError, match="pointer-and-expansion only"):
        load_native_episode_config(
            _armed_values({**_pins(), "granularity": {"exemplar": "L1"}}),
            _episode_program(),
        )
    with pytest.raises(ValueError, match="level must be one of"):
        load_native_episode_config(
            _armed_values({**_pins(), "granularity": {"intent": "L2"}}),
            _episode_program(),
        )


def test_refusal_3_exemplar_expansions_with_no_exemplar_store():
    values = _armed_values(
        knowledge_stores={
            "slot-contracts": {
                "store_role": "slot-contracts",
                "candidate_supply": {
                    "solver": {"max_candidates": 3, "max_total_values": 28},
                },
            }
        }
    )
    with pytest.raises(ValueError, match="no store of role 'train-exemplars'"):
        load_native_episode_config(values, _episode_program())
    # With the exemplar expansion at 0 the same config is admitted.
    values["native_episode"]["knowledge_index"] = {
        **_pins(), "expansion_budget": {"exemplar": 0},
    }
    assert load_native_episode_config(values, _episode_program()) is not None


def test_refusal_4_more_pointers_than_the_projection_produced():
    with pytest.raises(ValueError, match="pointer_budget.intent"):
        load_native_episode_config(
            _armed_values({**_pins(), "pointer_budget": {"intent": 4}}),
            _episode_program(),
        )


def test_refusal_5_more_slot_cards_than_the_candidate_supply_selected():
    with pytest.raises(ValueError, match="expansion_budget.slot_card"):
        load_native_episode_config(
            _armed_values({**_pins(), "expansion_budget": {"slot_card": 29}}),
            _episode_program(),
        )


def test_refusal_6_an_unregistered_ordering():
    with pytest.raises(ValueError, match="ordering"):
        load_native_episode_config(
            _armed_values({**_pins(), "ordering": "alphabetical-v1"}),
            _episode_program(),
        )


def test_refusal_7_the_key_requires_constant_tool_rendering():
    for rendering in ("per-role", None):
        values = _armed_values(tool_schema_rendering="per-role")
        if rendering is None:
            values["native_episode"].pop("tool_schema_rendering")
        with pytest.raises(ValueError, match="tool_schema_rendering 'constant'"):
            load_native_episode_config(values, _episode_program())


def test_refusal_8_a_carrier_with_no_knowledge_layer():
    with pytest.raises(ValueError, match="declares no knowledge_layer"):
        load_native_episode_config(
            _armed_values(carrier_lock_key="earnings21-original"), _episode_program()
        )
    values = _armed_values()
    values.pop("carrier_lock_key")
    with pytest.raises(ValueError, match="declared carrier_lock_key"):
        load_native_episode_config(values, _episode_program())


def test_the_role_override_and_the_module_are_one_module():
    values = _armed_values()
    values["native_episode"]["roles"]["planner"]["knowledge_index_budget"] = {
        "expansion_budget": {"exemplar": 0, "slot_card": 0, "intent_card": 0},
    }
    parsed = load_native_episode_config(values, _episode_program())
    document = json.loads(parsed.knowledge_index_json)
    assert document["roles"]["planner"]["expansion_budget"] == {
        "exemplar": 0, "slot_card": 0, "intent_card": 0,
    }
    # The override without the module is refused by name, exactly as E18's
    # roles.acquisition is refused without native_episode.acquisition.
    values["native_episode"].pop("knowledge_index")
    with pytest.raises(ValueError, match="one module"):
        load_native_episode_config(values, _episode_program())
    # And two spellings of one override are refused too.
    both = _armed_values({**_pins(), "roles": {"planner": {"expansion_budget": {}}}})
    with pytest.raises(ValueError, match="two spellings"):
        load_native_episode_config(both, _episode_program())


def test_solver_citation_required_is_refused_until_its_own_cell_exists():
    with pytest.raises(ValueError, match="second factor"):
        load_native_episode_config(
            _armed_values({**_pins(), "solver_citation": "required"}),
            _episode_program(),
        )


# ---------------------------------------------------------------------------
# 8. The key's own falsifier: absent means byte-identical.
# ---------------------------------------------------------------------------


def test_the_absent_key_composes_the_pre_e21_episode():
    values = _armed_values()
    values["native_episode"].pop("knowledge_index")
    parsed = load_native_episode_config(values, _episode_program())
    assert parsed.knowledge_index_json is None


def test_the_absent_key_moves_no_payload_byte():
    payload = {
        "task_instruction": "Task contract.",
        "supplied_evidence": [
            {"evidence_id": "intent-boundaries::intent-boundary:play_music",
             "content": "card", "knowledge_role": "value"},
        ],
        "history": [],
        "sample_id": "s1",
    }
    assert ki.apply_to_payload(payload, index_text=None, assembly=None) == payload
    # The two halves are one mechanism: arming one without the other refuses.
    with pytest.raises(ki.KnowledgeIndexError, match="two halves"):
        ki.apply_to_payload(payload, index_text="index", assembly=None)


SEALED_RUN = "SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-RECOVERY-V2"
SEALED_ATTEMPT = (
    "attempt-slurp-native-exemplars-k20-anchor-train-fold-a-generation-recovery-v2"
)


def _sealed_trace() -> Path | None:
    root = os.environ.get("SPEECHRL_DATA_DIR", "").strip()
    if not root:
        return None
    path = (
        Path(root) / "runs" / SEALED_RUN / SEALED_ATTEMPT
        / f"{SEALED_RUN}.trace.jsonl"
    )
    return path if path.is_file() else None


def test_the_absent_key_reproduces_the_sealed_b1_request_hashes():
    """The falsifier E11/E12/E14/E17/E18 all carry, against the SEALED bytes.

    Read-only, hashes only: each sealed request payload is re-composed with
    the key absent and its canonical digest must equal the sealed
    ``payload_sha256`` the trace recorded. No utterance text, no gold and no
    payload field is copied out of the run directory.
    """

    trace = _sealed_trace()
    if trace is None:
        pytest.skip("the controlled data root is not mounted")
    checked = 0
    with trace.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            if record.get("channel") != "MODEL_REQUEST":
                continue
            envelope = record["payload"]
            composed = ki.apply_to_payload(
                envelope["payload"], index_text=None, assembly=None
            )
            digest = hashlib.sha256(
                json.dumps(
                    composed, ensure_ascii=False, sort_keys=True,
                    separators=(",", ":"), allow_nan=False,
                ).encode("utf-8")
            ).hexdigest()
            assert digest == envelope["payload_sha256"]
            checked += 1
            if checked >= 25:
                break
    assert checked == 25


# ---------------------------------------------------------------------------
# 9. The receipt.
# ---------------------------------------------------------------------------


def test_the_receipt_records_ids_digests_and_citations_never_text(table, plan):
    block = ki.assemble(table, plan, _selection(), role_id="solver")
    index_text = ki.render_constant_index(table, plan)
    system_message = f"Task contract.\n\n{index_text}"
    row = ki.contact_receipt(
        contact_id="flight-0005/request", role_id="solver", assembly=block,
        system_message=system_message, index_text=index_text,
        cited_ids=("I/play_music", "I/email_query"), table=table,
    )
    receipt = ki.knowledge_index_receipt(
        plan=plan, table=table, index_text=index_text, contacts=[row],
    )
    assert receipt["schema"] == ki.KNOWLEDGE_INDEX_RECEIPT_SCHEMA
    assert receipt["ordering"] == ki.TAXONOMY_FREQUENCY_ORDERING
    assert receipt["granularity"]["intent"]["section"] == "Activation boundary"
    assert receipt["pointer_budget"] == dict(ki.DEFAULT_POINTER_BUDGET)
    assert receipt["expansion_budget"] == dict(ki.DEFAULT_EXPANSION_BUDGET)
    assert receipt["index_chars"] == len(index_text)
    assert receipt["distinct_system_message_sha256"] == 1
    assert receipt["citations_resolved"] == 1
    assert receipt["citations_unresolved"] == 1
    assert row["unresolved_ids"] == ["I/email_query"]
    assert row["degradation"] == []
    assert row["pointer_ids"][0] == "I/play_music"
    assert row["expanded_ids"] == list(block.expanded_ids)
    # Digests and counts only -- no rendered text anywhere in the block.
    serialised = json.dumps(receipt)
    assert SHARED_INTENT not in serialised
    assert "The play music request." not in serialised
    assert block.pointer_block not in serialised


def test_a_degradation_step_is_recorded_never_silent(table, plan):
    block = ki.assemble(table, plan, _selection(), role_id="solver")
    items = ki.index_droppable_items(block)
    steps = [ki.degradation_step(item, pass_index=1) for item in items[:2]]
    row = ki.contact_receipt(
        contact_id="c", role_id="solver", assembly=block,
        system_message="s", index_text="i", table=table, degradation=steps,
    )
    receipt = ki.knowledge_index_receipt(
        plan=plan, table=table, index_text="i", contacts=[row],
    )
    assert receipt["degradation_steps"] == 2
    assert row["degradation"][0]["block"] == ki.INDEX_EXPANSION_BLOCK


# ---------------------------------------------------------------------------
# 10. The render proof, on the synthetic store (design section 7.0).
# ---------------------------------------------------------------------------


def test_the_render_proof_reproduces_its_three_properties(table, plan):
    """The same three properties the CLI proves over the 100 sealed contacts,
    here over a synthetic five-contact row so the proof form itself is
    covered by the offline suite."""

    payload = {
        "task_instruction": "Task contract.",
        "supplied_evidence": [
            {"evidence_id": "intent-boundaries::intent-boundary:play_music",
             "content": "a card", "knowledge_role": "value"},
            {"evidence_id": "slot-contracts::slot-contract:song_name",
             "content": "another card", "knowledge_role": "value"},
            {"evidence_id": "key:facet:content:1", "content": "a key",
             "knowledge_role": "key"},
        ],
        "history": [],
        "sample_id": "s1",
    }
    index_text = ki.render_constant_index(table, plan)
    selection = _selection()
    systems = set()
    for role_id in ("perception", "solver", "reviewer", "reviewer", "planner"):
        block = ki.assemble(table, plan, selection, role_id=role_id)
        armed = ki.apply_to_payload(payload, index_text=index_text, assembly=block)
        systems.add(ki.sha256_text(armed["task_instruction"]))
        # The key parts survive untouched; every value item is now the
        # pointer block plus the bounded expansion.
        ids = [item["evidence_id"] for item in armed["supplied_evidence"]]
        assert ids[0] == "key:facet:content:1"
        assert ids[1] == ki.POINTER_BLOCK_EVIDENCE_ID
        assert ids[2:] == list(block.expanded_ids)
        assert not any(value.startswith("intent-boundaries::") for value in ids)
    # P1: ONE system message over every contact of the row.
    assert len(systems) == 1
    # P3: reducing the expansion budget moves no byte before the block.
    full = ki.apply_to_payload(
        payload, index_text=index_text,
        assembly=ki.assemble(table, plan, selection, role_id="solver"),
    )
    reduced_plan = ki.parse_knowledge_index_config(
        {**_pins(), "expansion_budget": {"slot_card": 0}}
    )
    reduced = ki.apply_to_payload(
        payload, index_text=index_text,
        assembly=ki.assemble(table, reduced_plan, selection, role_id="solver"),
    )
    kept = len(reduced["supplied_evidence"])
    assert reduced["supplied_evidence"] == full["supplied_evidence"][:kept]
    assert reduced["task_instruction"] == full["task_instruction"]


def test_the_index_and_its_estimate_are_derived_never_tokenized(table, plan):
    text = ki.render_constant_index(table, plan)
    assert ki.estimated_tokens(len(text)) == int(round(len(text) / ki.CHARS_PER_TOKEN))
    assert ki.CHARS_PER_TOKEN == 4.60
