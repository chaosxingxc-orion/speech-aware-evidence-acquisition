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
    # Item E27: the loader now names the carrier profile before it names the
    # view (the same fact -- an unreleased view id -- stated one lookup
    # earlier than the config parser's own view check).
    with pytest.raises(ValueError, match="names released view id"):
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


def test_refusal_7_is_lifted_when_no_role_holds_tool_authority():
    """Owner decision 53 (2026-09-20): with no tools array anywhere the prefix is
    constant by construction, so the key loads under per-role rendering."""
    for rendering in ("per-role", None):
        values = _armed_values(tool_schema_rendering="per-role")
        values.pop("phase_tools")
        if rendering is None:
            values["native_episode"].pop("tool_schema_rendering")
        config = load_native_episode_config(values, _episode_program())
        assert config is not None and config.knowledge_index_json is not None


def test_refusal_8_a_carrier_with_no_knowledge_layer():
    # Item E35 (owner decision 89, 2026-09-21) gives earnings21-original its
    # own TaskLayout with a real knowledge_layer ("conec-contexts"), so
    # refusal 8's "no knowledge_layer at all" guard no longer fires for it --
    # correctly: it now goes one refusal deeper, into the actual
    # knowledge-index carrier-profile registry (rails.knowledge_index),
    # which still fails closed because earnings21-original has no registered
    # profile there (only audio2tool/slurp do).
    with pytest.raises(ValueError, match="has no registered knowledge-index carrier profile"):
        load_native_episode_config(
            _armed_values(carrier_lock_key="earnings21-original"), _episode_program()
        )
    # earnings22-original still declares no task layer at all, so refusal 8
    # itself is still reachable and still fires for it.
    with pytest.raises(ValueError, match="declares no knowledge_layer"):
        load_native_episode_config(
            _armed_values(carrier_lock_key="earnings22-original"), _episode_program()
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
# ---------------------------------------------------------------------------
# 11. Item E21w: the LIVE runner wiring.
#
# Every proof below is model-free and offline: the view is the same synthetic
# store, the "flight" is ``rails.runner._agent_messages`` driven directly, and
# no transport, tokenizer, encoder or server is imported anywhere.
# ---------------------------------------------------------------------------

from speech_aware_evidence_acquisition.rails import runner as rails_runner
from speech_aware_evidence_acquisition.rails.context_fit import (
    CompactableRequest, apply_drops, droppable_items,
)
from speech_aware_evidence_acquisition.rails.core_client import _supply_provenance
from speech_aware_evidence_acquisition.rails.knowledge import (
    KeyFacet, KnowledgeSnapshot, QueryState, ValueBundle,
)

EXEMPLARS = tuple(
    (f"train-exemplars::value:{10000 + index}",
     f"utterance {index} | play_music | type=song_name; ...")
    for index in range(8)
)
SLOT_ITEMS = tuple(
    (f"slot-contracts::slot-contract:{name}", f"card for {name}")
    for name in ("song_name", "artist_name", "date")
)
INTENT_ITEMS = (
    ("intent-boundaries::intent-boundary:play_music", "card for play_music"),
    ("intent-boundaries::intent-boundary:play_radio", "card for play_radio"),
)
PERCEPTION_STATE = {
    "state_id": "state-perception-1",
    "state_kind": "phase:perception",
    "content": json.dumps(
        {"candidates": [
            {"intent_id": "play_music"}, {"intent_id": "play_radio"},
            {"intent_id": "email_query"},
        ]}
    ),
}


def _evidence_items():
    return [
        {"evidence_id": value_id, "content": content, "knowledge_role": "value"}
        for value_id, content in INTENT_ITEMS + SLOT_ITEMS + EXEMPLARS
    ]


def _released_view(tmp_path):
    """Write the synthetic view as a RELEASED, hash-pinned pair on disk."""

    document = synthetic_snapshot()
    raw = ki.canonical_json(document).encode("utf-8")
    directory = tmp_path / "knowledge/slurp/semantic" / ki.KNOWLEDGE_INDEX_VIEW_ID
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "snapshot.json").write_bytes(raw)
    snapshot_sha = hashlib.sha256(raw).hexdigest()
    release = {
        "schema": ki.KNOWLEDGE_INDEX_RELEASE_SCHEMA,
        "view_id": ki.KNOWLEDGE_INDEX_VIEW_ID,
        "builder_policy_id": ki.KNOWLEDGE_INDEX_BUILDER_POLICY_ID,
        "snapshot_sha256": snapshot_sha,
        "source_split_identity_hash": document["source_split_identity_hash"],
    }
    release_raw = ki.canonical_json(release).encode("utf-8")
    (directory / "release.json").write_bytes(release_raw)
    base = f"knowledge/slurp/semantic/{ki.KNOWLEDGE_INDEX_VIEW_ID}"
    pins = {
        "view": ki.KNOWLEDGE_INDEX_VIEW_ID,
        "release": {
            "relpath": f"{base}/release.json", "root": "data",
            "sha256": hashlib.sha256(release_raw).hexdigest(),
        },
        "snapshot": {
            "relpath": f"{base}/snapshot.json", "root": "data",
            "sha256": snapshot_sha,
        },
    }
    return pins, directory


def _binding(tmp_path, overrides=None, **kwargs):
    pins, _directory = _released_view(tmp_path)
    document = ki.parse_knowledge_index_config({**pins, **(overrides or {})}).as_json()
    return ki.build_knowledge_index_binding(
        knowledge_index_json=ki.canonical_json(document),
        data_root=tmp_path, **kwargs,
    )


class _Adapter:
    def __init__(self, system_text):
        self._system_text = system_text

    def assemble_prompt(self, _sample, _selection):
        return (
            {"role": "system", "content": self._system_text},
            {"role": "user", "content": []},
        )


class _State:
    def __init__(self, document):
        self._document = document
        self.state_kind = document["state_kind"]
        self.content = document["content"]

    def as_json(self):
        return dict(self._document)


SYSTEM_TEXT = "Contract fill."


def _seam(index=None, role_kind=None, states=(), sink=None):
    """ONE contact through the production seam, offline."""

    items = _evidence_items()
    snapshot = KnowledgeSnapshot(
        snapshot_id="wire", source_split_identity_hash="0" * 64,
        source_sample_ids=("train-0",), builder_policy_id="wire",
        facets=(
            KeyFacet(
                facet_id="facet:content:1", dimension="content",
                representation_kind="text", representation="a key",
                source_sample_ids=("train-0",),
            ),
        ),
        values=tuple(
            ValueBundle(
                value_id=item["evidence_id"], content=item["content"],
                associated_facet_ids=("facet:content:1",),
                source_sample_ids=("train-0",), provenance_refs=("wire",),
            )
            for item in items
        ),
    )
    query_state = QueryState(
        query_id="q", query_sample_id="sample-1", speech_packet_id="packet-1",
        speech_packet_sha256="1" * 64, use_split_identity_hash="0" * 64,
        visible_facet_ids=("facet:content:1",),
        retrieved_value_ids=tuple(item["evidence_id"] for item in items),
    )
    return rails_runner._agent_messages(
        adapter=_Adapter(SYSTEM_TEXT), sample=None, task_contract=SYSTEM_TEXT,
        snapshot=snapshot, snapshot_sha256="2" * 64, query_state=query_state,
        agent_states=tuple(_State(row) for row in states),
        knowledge_value_renderer=lambda _s, _q, _a: [
            {
                "type": "text", "text": item["content"],
                "evidence_id": item["evidence_id"],
                "source_uri": f"knowledge-snapshot://{'2' * 64}/{item['evidence_id']}",
                "knowledge_role": "value",
            }
            for item in items
        ],
        knowledge_index=index, index_role_kind=role_kind, index_sink=sink,
    )


# -- A. the binding ---------------------------------------------------------


def test_the_binding_loads_the_released_view_and_renders_the_index_once(tmp_path):
    binding = _binding(tmp_path)
    assert binding.table.view_id == ki.KNOWLEDGE_INDEX_VIEW_ID
    assert binding.index_text == ki.render_constant_index(binding.table, binding.plan)
    assert binding.suffix() == f"\n\n{binding.index_text}"
    # The snapshot's FILE digest and the view's own content hash are one
    # number: the loader re-types nothing.
    assert binding.table.content_hash() == binding.plan.snapshot["sha256"]


def test_the_binding_refuses_a_missing_root_a_moved_byte_and_a_wrong_content_hash(
    tmp_path,
):
    pins, directory = _released_view(tmp_path)
    document = ki.canonical_json(ki.parse_knowledge_index_config(pins).as_json())
    with pytest.raises(ki.KnowledgeIndexError, match="no controlled data root"):
        ki.build_knowledge_index_binding(
            knowledge_index_json=document, data_root=None
        )
    with pytest.raises(ki.KnowledgeIndexError, match="names no file"):
        ki.build_knowledge_index_binding(
            knowledge_index_json=document, data_root=tmp_path / "elsewhere"
        )
    # One byte moved under the pin: refused by DIGEST, not by shape.
    snapshot_path = directory / "snapshot.json"
    raw = snapshot_path.read_bytes()
    snapshot_path.write_bytes(raw + b" ")
    with pytest.raises(ki.KnowledgeIndexError, match="hashes to"):
        ki.build_knowledge_index_binding(
            knowledge_index_json=document, data_root=tmp_path
        )
    snapshot_path.write_bytes(raw)
    # A released snapshot whose FILE digest is not its own content hash: the
    # same document, written non-canonically. Both pins are re-pinned to the
    # new bytes so the loader's byte check passes and ONLY the content-hash
    # identity is left to fail -- which is the whole point of pinning the
    # release by file bytes and the snapshot by content hash.
    loose = json.dumps(
        json.loads(raw.decode("utf-8")), ensure_ascii=False, indent=1,
    ).encode("utf-8")
    snapshot_path.write_bytes(loose)
    moved = hashlib.sha256(loose).hexdigest()
    assert moved != hashlib.sha256(raw).hexdigest()
    release = json.loads((directory / "release.json").read_text(encoding="utf-8"))
    release["snapshot_sha256"] = moved
    release_raw = ki.canonical_json(release).encode("utf-8")
    (directory / "release.json").write_bytes(release_raw)
    broken = dict(ki.parse_knowledge_index_config(pins).as_json())
    broken["snapshot"] = {**pins["snapshot"], "sha256": moved}
    broken["release"] = {
        **pins["release"], "sha256": hashlib.sha256(release_raw).hexdigest(),
    }
    assert ki.table_from_snapshot(
        json.loads(loose.decode("utf-8"))
    ).content_hash() != moved
    with pytest.raises(ki.KnowledgeIndexError, match="one number"):
        ki.build_knowledge_index_binding(
            knowledge_index_json=ki.canonical_json(broken), data_root=tmp_path
        )


# -- B. the row selector ----------------------------------------------------


def test_the_selector_reads_the_perception_state_the_exemplars_and_the_slots(table):
    selection, provenance = ki.derive_row_selection(
        evidence_items=_evidence_items(), agent_states=[PERCEPTION_STATE],
        table=table,
    )
    assert provenance["candidate_source"] == "perception-state"
    # ``email_query`` is a well-formed name the synthetic view does not
    # carry: dropped and COUNTED, never rendered.
    assert selection.candidates == ("play_music", "play_radio")
    assert provenance["refused_candidates"] == ["email_query"]
    assert selection.slot_types == ("song_name", "artist_name", "date")
    assert selection.exemplar_votes == (("play_music", 8),)
    assert [key for key, _text in selection.exemplars] == [
        str(10000 + index) for index in range(8)
    ]
    assert provenance["exemplar_order"] == "supplied-order"


def test_the_selector_falls_back_to_the_retrieval_order_before_perception(table):
    selection, provenance = ki.derive_row_selection(
        evidence_items=_evidence_items(), agent_states=(), table=table,
    )
    assert provenance["candidate_source"] == "retrieval-order"
    assert selection.candidates == ("play_music", "play_radio")
    selection, provenance = ki.derive_row_selection(
        evidence_items=[], agent_states=(), table=table,
    )
    assert provenance["candidate_source"] == "none"
    assert selection.candidates == ()


def test_the_selector_is_deterministic(table):
    first = ki.derive_row_selection(
        evidence_items=_evidence_items(), agent_states=[PERCEPTION_STATE],
        table=table,
    )
    second = ki.derive_row_selection(
        evidence_items=_evidence_items(), agent_states=[PERCEPTION_STATE],
        table=table,
    )
    assert first == second


def test_a_malformed_perception_state_never_kills_the_row(table):
    for content in ("not json", json.dumps({"candidates": "x"}), ""):
        selection, provenance = ki.derive_row_selection(
            evidence_items=_evidence_items(),
            agent_states=[{**PERCEPTION_STATE, "content": content}], table=table,
        )
        assert provenance["candidate_source"] == "retrieval-order"
        assert selection.candidates == ("play_music", "play_radio")


# -- C. the retrieval rank --------------------------------------------------


class _Ranked:
    def __init__(self, facet_id, score):
        self.facet_id, self.score = facet_id, score


class _RankResult:
    ranking_policy_id = "saea-rank-wcos-prior-agree-v1"

    def __init__(self, candidates):
        self.candidates = candidates

    def content_hash(self):
        return "3" * 64


class _Fusion:
    fusion_policy_id = "saea-fuse-supplyfilter-v1"

    def __init__(self, supporting, selected):
        self.supporting_facet_ids = supporting
        self.selected_value_ids = selected


class _Value:
    def __init__(self, value_id, facets):
        self.value_id, self.associated_facet_ids = value_id, facets


def test_the_retrieval_rank_is_recorded_and_names_its_similarity():
    rank_result = _RankResult(
        (_Ranked("f:a", 0.9), _Ranked("f:b", 0.5), _Ranked("f:c", 0.1))
    )
    fusion = _Fusion(
        ("f:a", "f:b", "f:c"),
        # The lexicographic order the supply returns today, which carries no
        # rank at all (M1 analysis section 4.2).
        ("train-exemplars::value:10000", "train-exemplars::value:10001",
         "train-exemplars::value:10002"),
    )
    values = [
        _Value("train-exemplars::value:10000", ("f:c",)),
        _Value("train-exemplars::value:10001", ("f:a",)),
        _Value("train-exemplars::value:10002", ("f:b",)),
    ]
    ranks = ki.value_retrieval_ranks(
        rank_result=rank_result, fusion_decision=fusion, values=values,
    )
    assert [
        value_id for value_id, row in sorted(
            ranks.items(), key=lambda item: item[1]["rank"]
        )
    ] == [
        "train-exemplars::value:10001",
        "train-exemplars::value:10002",
        "train-exemplars::value:10000",
    ]
    assert ranks["train-exemplars::value:10001"] == {
        "rank": 1, "score": 0.9, "supporting_facet_id": "f:a",
    }
    similarity = ki.retrieval_similarity(
        rank_result=rank_result, fusion_decision=fusion,
    )
    assert similarity["schema"] == ki.RETRIEVAL_RANK_SCHEMA
    assert similarity["ranking_policy_id"] == "saea-rank-wcos-prior-agree-v1"
    assert similarity["fusion_policy_id"] == "saea-fuse-supplyfilter-v1"


def test_a_recorded_rank_reorders_the_expansion_block(table):
    items = [
        {"evidence_id": value_id, "content": content, "knowledge_role": "value"}
        for value_id, content in EXEMPLARS
    ]
    ranks = {
        "train-exemplars::value:10007": {"rank": 1, "score": 0.9},
        "train-exemplars::value:10003": {"rank": 2, "score": 0.8},
    }
    selection, provenance = ki.derive_row_selection(
        evidence_items=items, agent_states=(), table=table, exemplar_ranks=ranks,
    )
    assert provenance["exemplar_order"] == "retrieval-rank"
    assert [key for key, _text in selection.exemplars][:2] == ["10007", "10003"]


def test_the_supply_arms_its_rank_record_only_when_a_caller_asks():
    """``rails.phase_supply`` records the rank ONLY into a dict a caller
    handed over; with the attribute left at None nothing is computed and no
    supply byte moves."""

    from speech_aware_evidence_acquisition.rails import phase_supply

    source = Path(phase_supply.__file__).read_text(encoding="utf-8")
    assert "supply_for_phase.retrieval_ranks = None" in source
    assert 'ranks = getattr(supply_for_phase, "retrieval_ranks", None)' in source


# -- D/E. the seam swap, the absent key and the per-role budgets ------------


def test_the_seam_appends_the_index_and_replaces_the_value_blocks(tmp_path):
    binding = _binding(tmp_path)
    off = _seam()
    record = {}
    on = _seam(
        index=binding, role_kind="solver", states=[PERCEPTION_STATE],
        sink=lambda assembly, selection, provenance: record.update(
            assembly=assembly, provenance=provenance
        ),
    )
    assert on[0]["content"] == f"{SYSTEM_TEXT}{binding.suffix()}"
    assert on[0]["content"].startswith(off[0]["content"])
    ids = [
        part["evidence_id"] for part in on[1]["content"]
        if part.get("type") == "text"
    ]
    assert ids[0] == "key:facet:content:1"
    assert ids[1] == ki.POINTER_BLOCK_EVIDENCE_ID
    assert ids[2:] == list(record["assembly"].expanded_ids)
    assert not any(value.startswith("train-exemplars::") for value in ids)
    # The speech packet reference is untouched and still first.
    assert on[1]["content"][0]["type"] == "input_speech_features"


def test_the_absent_key_moves_no_seam_byte(tmp_path):
    binding = _binding(tmp_path)
    off = _seam()
    again = _seam(index=None, role_kind="solver", states=[PERCEPTION_STATE])
    assert off == again
    on = _seam(index=binding, role_kind="solver", sink=lambda *a: None)
    assert on != off


def test_the_per_role_budget_override_is_honoured_at_request_composition(tmp_path):
    binding = _binding(
        tmp_path,
        overrides={
            "roles": {
                "planner": {
                    "expansion_budget": {
                        "exemplar": 0, "slot_card": 0, "intent_card": 0,
                    }
                }
            }
        },
    )
    seen = {}
    for role_kind in ("solver", "planner"):
        _seam(
            index=binding, role_kind=role_kind, states=[PERCEPTION_STATE],
            sink=lambda assembly, _s, _p, role=role_kind: seen.__setitem__(
                role, assembly
            ),
        )
    assert seen["solver"].expanded_ids
    # OFF by default everywhere else: the Planner's override is the only one
    # declared, and it is the only role whose block changes.
    assert seen["planner"].expanded_ids == ()
    assert seen["planner"].pointer_ids == seen["solver"].pointer_ids


def test_the_pointer_and_expansion_parts_carry_index_provenance(tmp_path):
    binding = _binding(tmp_path)
    record = {}
    on = _seam(
        index=binding, role_kind="solver", states=[PERCEPTION_STATE],
        sink=lambda assembly, _s, _p: record.update(assembly=assembly),
    )
    parts = [part for part in on[1]["content"] if part.get("type") == "text"]
    index_parts = [
        part for part in parts
        if str(part["source_uri"]).startswith("knowledge-index://")
    ]
    assert len(index_parts) == len(record["assembly"].expansions) + 1
    rows = [
        _supply_provenance(part, part["text"], request_id="r-0001", index=index)
        for index, part in enumerate(parts)
    ]
    assert rows[0]["lock_key"] == "rails-supply"
    for part, row in zip(parts[1:], rows[1:], strict=True):
        assert row["lock_key"] == "knowledge-index"
        assert row["relpath"] == (
            f"{ki.KNOWLEDGE_INDEX_VIEW_ID}/{part['evidence_id']}"
        )


def test_the_framework_envelope_is_rewritten_and_rehashed(table, plan):
    from speech_aware_evidence_acquisition.core.model.native_framework_history import (
        validate_native_framework_contact,
    )

    envelope = {
        "schema": "saea-native-framework-contact-v1",
        "role_id": "solver", "sample_id": "s1", "contact_id": "c1",
        "messages": [
            {"role": "system", "content": "Contract fill."},
            {"role": "user", "content": "query"},
        ],
        "local_tool_result_ids": [],
    }
    content = json.dumps(
        envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    )
    payload = {
        "sample_id": "s1",
        "task_instruction": "Contract fill.",
        "supplied_evidence": [],
        "history": [
            {"role": "control", "contact_id": "c1", "content": content,
             "content_sha256": ki.sha256_text(content)},
        ],
    }
    assert validate_native_framework_contact(payload) is not None
    index_text = ki.render_constant_index(table, plan)
    armed = ki.apply_to_payload(
        payload, index_text=index_text,
        assembly=ki.assemble(table, plan, _selection(), role_id="solver"),
    )
    # The envelope's own system message moved with the payload's, and its
    # digest was recomputed rather than left stale.
    control = armed["history"][-1]
    assert json.loads(control["content"])["messages"][0]["content"] == (
        armed["task_instruction"]
    )
    assert control["content_sha256"] == ki.sha256_text(control["content"])
    assert validate_native_framework_contact(armed) is not None


# -- F. the ladder, through E20's own apply_drops ---------------------------


def test_the_index_ladder_drives_e20s_apply_drops(tmp_path):
    binding = _binding(tmp_path)
    record = {}
    on = _seam(
        index=binding, role_kind="solver", states=[PERCEPTION_STATE],
        sink=lambda assembly, _s, _p: record.update(assembly=assembly),
    )
    assembly = record["assembly"]
    view = CompactableRequest(
        content=tuple(on[1]["content"]), agent_states=(),
        index_assembly=assembly,
    )
    items = droppable_items(view)
    index_items = [
        item for item in items
        if item.block in (ki.INDEX_EXPANSION_BLOCK, ki.INDEX_POINTER_BLOCK)
    ]
    # The declared order: every expansion from the TAIL, then the pointer
    # block -- and never before it.
    assert [item.block for item in index_items] == (
        [ki.INDEX_EXPANSION_BLOCK] * len(assembly.expansions)
        + [ki.INDEX_POINTER_BLOCK]
    )
    assert [item.identifier for item in index_items[:-1]] == [
        f"value:{item.entry_id}" for item in reversed(assembly.expansions)
    ]
    assert index_items[-1].tranche == 2
    # The L1 -> L0 granularity step is NOT executed at this seam: it
    # re-renders the constant prefix, which the dispatch view may not touch.
    assert all(item.block != ki.INDEX_GRANULARITY_BLOCK for item in items)
    narrowed = apply_drops(view, index_items[:2])
    assert len(narrowed.content) == len(view.content) - 2
    kept = [
        part["evidence_id"] for part in narrowed.content
        if part.get("type") == "text"
    ]
    assert kept[-1] == assembly.expansions[-3].entry_id
    # E20's own ladder is unchanged with no armed index.
    plain = CompactableRequest(content=tuple(on[1]["content"]), agent_states=())
    assert all(
        item.block not in (ki.INDEX_EXPANSION_BLOCK, ki.INDEX_POINTER_BLOCK)
        for item in droppable_items(plain)
    )


def test_a_narrowed_assembly_names_what_was_actually_sent(table, plan):
    assembly = ki.assemble(table, plan, _selection(), role_id="solver")
    dropped = (f"value:{assembly.expansions[-1].entry_id}",)
    narrowed = ki.narrow_assembly(assembly, dropped)
    assert narrowed.expanded_ids == assembly.expanded_ids[:-1]
    assert narrowed.pointer_block == assembly.pointer_block
    gone = ki.narrow_assembly(
        assembly, dropped + (f"value:{ki.POINTER_BLOCK_EVIDENCE_ID}",)
    )
    assert gone.pointer_block == ""
    assert gone.pointer_ids == ()


# -- G. the receipt ---------------------------------------------------------


def test_the_binding_receipt_carries_the_view_the_budgets_and_the_rank_source(
    tmp_path,
):
    binding = _binding(tmp_path)
    record = {}
    _seam(
        index=binding, role_kind="solver", states=[PERCEPTION_STATE],
        sink=lambda assembly, selection, provenance: record.update(
            assembly=assembly, provenance=provenance
        ),
    )
    row = ki.contact_receipt(
        contact_id="c1", role_id="solver", assembly=record["assembly"],
        system_message=f"{SYSTEM_TEXT}{binding.suffix()}",
        index_text=binding.index_text, cited_ids=("I/play_music", "I/email_query"),
        table=binding.table,
    )
    receipt = binding.receipt([row])
    assert receipt["schema"] == ki.KNOWLEDGE_INDEX_RECEIPT_SCHEMA
    assert receipt["view"]["snapshot_sha256"] == binding.plan.snapshot["sha256"]
    assert receipt["view"]["content_hash"] == binding.table.content_hash()
    assert receipt["distinct_system_message_sha256"] == 1
    assert receipt["citations_resolved"] == 1
    assert receipt["citations_unresolved"] == 1
    # The rank source is NAMED, never implied: this binding recorded none.
    assert receipt["retrieval_rank"] == {"recorded": False}
    serialised = json.dumps(receipt)
    assert binding.index_text not in serialised
    assert record["assembly"].pointer_block not in serialised


def test_the_receipt_names_the_similarity_once_the_supply_records_one(tmp_path):
    similarity = {}
    binding = _binding(tmp_path, similarity=similarity)
    assert binding.receipt([])["retrieval_rank"] == {"recorded": False}
    # The supply fills the record DURING the flight; the binding carries it
    # by reference, so the receipt sees it.
    similarity.update(
        ki.retrieval_similarity(
            rank_result=_RankResult((_Ranked("f:a", 0.9),)),
            fusion_decision=_Fusion(("f:a",), ("v1",)),
        )
    )
    document = binding.receipt([])["retrieval_rank"]
    assert document["recorded"] is True
    assert document["schema"] == ki.RETRIEVAL_RANK_SCHEMA
    assert document["fusion_policy_id"] == "saea-fuse-supplyfilter-v1"


def test_the_runner_refuses_a_binding_with_no_armed_key():
    """The other half of the item note's fail-closed guard: an index the
    config hash does not claim would move request bytes outside the cell
    identity."""

    source = Path(rails_runner.__file__).read_text(encoding="utf-8")
    assert (
        "the episode binding carries a knowledge-index binding but" in source
    )
    assert "native_episode.knowledge_index is armed but the episode binding" in source
