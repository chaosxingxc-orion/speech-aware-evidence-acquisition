"""Item E24 (2026-09-20): the DERANGEMENT TWIN of the knowledge index.

"E21" in this repository is also the shorthand for the Earnings-21 carrier;
everywhere below, item E21 is the KNOWLEDGE INDEX and item E24 is its twin.

Design: ``docs/superpowers/specs/2026-09-19-knowledge-index-and-context-
assembly-design.md`` section 7.2 (owner decisions 48, 50 and 53) and the item
note ``docs/superpowers/specs/2026-09-20-e24-knowledge-index-twin-design.md``.

Every test here is model-free, tokenizer-free and offline: the views under
test are SYNTHETIC and built in this module (one of them reused from the E21
suite), nothing is written outside ``tmp_path``, and no utterance text or gold
of any row appears anywhere.

The proofs, in the order the item note lists them:

* **T1** zero fixed points, over several seeds and every kind, checked by
  CONTENT and not only by position;
* **T2** the per-kind multiset of L1 lines and L2 cards is unchanged -- a
  twin is a re-assignment, never a rewrite;
* **T3** the rendered index has the SAME character count as the source's, and
  the same line count, with the intent lines re-assigned;
* **T4** one permutation moves the L1 line and its L2 card together;
* **T5** the build reproduces from its seed (what ``--check`` verifies);
* **T6** the loader accepts the twin through its own release pins exactly
  like the source, refuses a twin without its derangement record and a source
  wearing one, and the receipt names the twin and carries ``twin_of``;
* **T7** the assembly produces byte-equal pointer and expansion block SIZES
  on the two arms, with different contents.
"""

from __future__ import annotations

import hashlib

import pytest

from speech_aware_evidence_acquisition.rails import knowledge_index as ki

from test_e21_knowledge_index import synthetic_snapshot

SEED = 20260920


# ---------------------------------------------------------------------------
# T1: the derangement itself.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("count", [2, 3, 5, 54, 60, 81, 195])
@pytest.mark.parametrize("seed", [0, 1, 20260920, 999983])
def test_sattolo_has_no_fixed_point_and_is_one_cycle(count, seed):
    order = ki.sattolo_derangement(count, stream=f"t:{seed}")
    assert sorted(order) == list(range(count)), "a derangement is a permutation"
    assert all(order[i] != i for i in range(count)), "zero fixed points"
    # Sattolo draws strictly BELOW the position, which makes the result a
    # SINGLE cycle; walking it visits every position exactly once.
    seen, position = set(), 0
    for _step in range(count):
        seen.add(position)
        position = order[position]
    assert seen == set(range(count))
    assert position == 0


def test_sattolo_refuses_a_count_with_no_derangement():
    for count in (0, 1):
        with pytest.raises(ki.KnowledgeIndexError):
            ki.sattolo_derangement(count, stream="t")


def test_sattolo_is_deterministic_and_seed_sensitive():
    first = ki.sattolo_derangement(60, stream=ki._twin_stream(SEED, "intent"))
    assert first == ki.sattolo_derangement(60, stream=ki._twin_stream(SEED, "intent"))
    assert first != ki.sattolo_derangement(60, stream=ki._twin_stream(SEED + 1, "intent"))
    assert first != ki.sattolo_derangement(60, stream=ki._twin_stream(SEED, "slot"))


@pytest.mark.parametrize("seed", [7, SEED, 4242])
def test_no_entry_keeps_its_own_line_in_any_kind(seed):
    source = synthetic_snapshot()
    twin, record = ki.derange_snapshot(source, seed=seed)
    assert record["fixed_points"] == 0
    assert set(record["kinds"]) == {"intent", "slot", "edge"}
    before = {row["id"]: row for row in source["entries"]}
    for row in twin["entries"]:
        was = before[row["id"]]
        assert row["kind"] == was["kind"]
        moved = [field for field in ki.TWIN_MOVED_FIELDS if row[field] != was[field]]
        assert moved, f"{row['id']} kept its own content"


def test_the_derangement_stays_inside_each_kind():
    source = synthetic_snapshot()
    twin, _record = ki.derange_snapshot(source, seed=SEED)
    donors = {
        ki.canonical_json({field: row[field] for field in ki.TWIN_MOVED_FIELDS}): row["kind"]
        for row in source["entries"]
    }
    for row in twin["entries"]:
        key = ki.canonical_json(
            {field: row[field] for field in ki.TWIN_MOVED_FIELDS}
        )
        assert donors[key] == row["kind"], "a line moved across kinds"


# ---------------------------------------------------------------------------
# T2 / T4: what moves, what is held, and that one permutation does both.
# ---------------------------------------------------------------------------


def test_multiset_of_lines_and_cards_is_unchanged_per_kind():
    source = synthetic_snapshot()
    twin, _record = ki.derange_snapshot(source, seed=SEED)
    assert ki.twin_line_multisets(source) == ki.twin_line_multisets(twin)


def test_ids_groups_ranks_and_shared_sections_are_held():
    source = synthetic_snapshot()
    twin, _record = ki.derange_snapshot(source, seed=SEED)
    for field in ki.TWIN_HELD_FIELDS:
        assert [row[field] for row in source["entries"]] == [
            row[field] for row in twin["entries"]
        ]
    assert source["shared_sections"] == twin["shared_sections"]
    assert source["legal_intents"] == twin["legal_intents"]
    assert source["ordering"] == twin["ordering"]
    assert twin["view_id"] == ki.KNOWLEDGE_INDEX_TWIN_VIEW_ID


def test_one_permutation_moves_the_l1_line_and_its_l2_card_together():
    source = synthetic_snapshot()
    twin, _record = ki.derange_snapshot(source, seed=SEED)
    by_l1 = {ki.canonical_json(row["l1"]): row["id"] for row in source["entries"]}
    by_card = {
        ki.canonical_json([row["residue"], row["hoisted"]]): row["id"]
        for row in source["entries"]
        if row["residue"]
    }
    for row in twin["entries"]:
        donor = by_l1[ki.canonical_json(row["l1"])]
        if row["residue"]:
            card_donor = by_card[ki.canonical_json([row["residue"], row["hoisted"]])]
            assert donor == card_donor, (
                f"{row['id']} shows {donor}'s line beside {card_donor}'s card"
            )


def test_the_twin_card_still_restores_its_donors_released_card():
    source = synthetic_snapshot()
    twin, _record = ki.derange_snapshot(source, seed=SEED)
    table = ki.table_from_snapshot(twin)
    shared = table.shared()
    donors = {
        ki.canonical_json([row["residue"], row["hoisted"]]): row["id"]
        for row in source["entries"]
        if row["residue"]
    }
    for entry in table.entries:
        if not entry.residue:
            continue
        restored = ki.restore_card(entry.residue, entry.hoisted, shared)
        assert restored, "the hoist must still splice back"
        key = ki.canonical_json(
            [entry.residue, [item.as_json() for item in entry.hoisted]]
        )
        assert key in donors


# ---------------------------------------------------------------------------
# T3: the rendered form is matched.
# ---------------------------------------------------------------------------


def _tables(seed=SEED, snapshot=None):
    source = snapshot if snapshot is not None else synthetic_snapshot()
    twin_snapshot, record = ki.derange_snapshot(source, seed=seed)
    return (
        ki.table_from_snapshot(source),
        ki.table_from_snapshot(
            twin_snapshot, render_label=str(source["view_id"])
        ),
        record,
    )


def test_rendered_index_has_the_same_length_and_different_text():
    source_table, twin_table, _record = _tables()
    plan = ki.default_index_plan()
    twin_plan = ki.default_index_plan(ki.KNOWLEDGE_INDEX_TWIN_VIEW_ID)
    source_text = ki.render_constant_index(source_table, plan)
    twin_text = ki.render_constant_index(twin_table, twin_plan)
    assert len(source_text) == len(twin_text)
    assert source_text != twin_text
    assert source_text.split("\n")[0] == twin_text.split("\n")[0], (
        "the header must not announce the arm: the model can read it"
    )
    assert ki.KNOWLEDGE_INDEX_TWIN_VIEW_ID not in twin_text
    assert len(source_text.split("\n")) == len(twin_text.split("\n"))


def test_the_rendered_line_multiset_is_unchanged_per_kind():
    source_table, twin_table, _record = _tables()
    plan = ki.default_index_plan()

    def lines(table):
        buckets: dict[str, list[str]] = {}
        for entry in table.entries:
            buckets.setdefault(entry.kind, []).append(
                entry.line(
                    level=plan.granularity[entry.kind],
                    section=plan.l1_sections[entry.kind],
                )
            )
        return {kind: sorted(rows) for kind, rows in buckets.items()}

    # The ids are held and the lines are re-assigned within a kind, so the
    # SORTED lines are not equal -- what is equal is the multiset of the L1
    # STATEMENTS, which is what makes the rendered total identical.
    def statements(table):
        buckets: dict[str, list[str]] = {}
        for entry in table.entries:
            section = plan.l1_sections[entry.kind]
            buckets.setdefault(entry.kind, []).append(entry.l1.get(section, ""))
        return {kind: sorted(rows) for kind, rows in buckets.items()}

    assert statements(source_table) == statements(twin_table)
    assert sum(
        len(line) for rows in lines(source_table).values() for line in rows
    ) == sum(len(line) for rows in lines(twin_table).values() for line in rows)


def test_the_twin_renders_the_source_view_id_in_its_header():
    _source_table, twin_table, _record = _tables()
    assert twin_table.view_id == ki.KNOWLEDGE_INDEX_TWIN_VIEW_ID
    assert twin_table.header_view_id == ki.KNOWLEDGE_INDEX_VIEW_ID
    # A twin loaded WITHOUT its release states its own id, which is why the
    # loader -- never the snapshot -- is what sets the label.
    bare = ki.table_from_snapshot(ki.derange_snapshot(synthetic_snapshot(), seed=SEED)[0])
    assert bare.header_view_id == ki.KNOWLEDGE_INDEX_TWIN_VIEW_ID


# ---------------------------------------------------------------------------
# T5: reproduction (what ``--check`` verifies).
# ---------------------------------------------------------------------------


def test_the_twin_reproduces_from_its_seed():
    source = synthetic_snapshot()
    first, first_record = ki.derange_snapshot(source, seed=SEED)
    second, second_record = ki.derange_snapshot(source, seed=SEED)
    assert ki.canonical_json(first) == ki.canonical_json(second)
    assert first_record == second_record
    other, other_record = ki.derange_snapshot(source, seed=SEED + 1)
    assert ki.canonical_json(other) != ki.canonical_json(first)
    assert other_record["permutation_sha256"] != first_record["permutation_sha256"]


def test_the_derangement_record_states_what_a_reader_needs():
    _source, record = ki.derange_snapshot(synthetic_snapshot(), seed=SEED)
    assert record["seed"] == SEED
    assert record["fixed_points"] == 0
    assert len(record["permutation_sha256"]) == 64
    assert record["moved_fields"] == list(ki.TWIN_MOVED_FIELDS)
    assert record["held_fields"] == list(ki.TWIN_HELD_FIELDS)
    assert record["algorithm"] == "sattolo-cycle-sha256-stream-v1"


def test_a_non_integer_seed_is_refused():
    for seed in ("20260920", 1.0, True, None):
        with pytest.raises(ki.KnowledgeIndexError):
            ki.derange_snapshot(synthetic_snapshot(), seed=seed)


# ---------------------------------------------------------------------------
# T6: the loader, its refusals and the receipt.
# ---------------------------------------------------------------------------


def _release_twin(tmp_path, *, seed=SEED, mutate=None, view_id=None):
    """Write the synthetic TWIN as a released, hash-pinned pair on disk."""

    source = synthetic_snapshot()
    twin_snapshot, record = ki.derange_snapshot(source, seed=seed)
    if view_id is not None:
        twin_snapshot["view_id"] = view_id
    name = str(twin_snapshot["view_id"])
    raw = ki.canonical_json(twin_snapshot).encode("utf-8")
    directory = tmp_path / "knowledge/slurp/semantic" / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "snapshot.json").write_bytes(raw)
    snapshot_sha = hashlib.sha256(raw).hexdigest()
    release = {
        "schema": ki.KNOWLEDGE_INDEX_RELEASE_SCHEMA,
        "view_id": name,
        "builder_policy_id": ki.KNOWLEDGE_INDEX_BUILDER_POLICY_ID,
        "snapshot_sha256": snapshot_sha,
        "source_split_identity_hash": twin_snapshot["source_split_identity_hash"],
        "twin_of": {
            "view_id": ki.KNOWLEDGE_INDEX_VIEW_ID,
            "snapshot_content_hash": hashlib.sha256(
                ki.canonical_json(source).encode("utf-8")
            ).hexdigest(),
        },
        "derangement": record,
        "gold_read": False,
    }
    if mutate is not None:
        mutate(release)
    release_raw = ki.canonical_json(release).encode("utf-8")
    (directory / "release.json").write_bytes(release_raw)
    base = f"knowledge/slurp/semantic/{name}"
    pins = {
        "view": name,
        "release": {
            "relpath": f"{base}/release.json", "root": "data",
            "sha256": hashlib.sha256(release_raw).hexdigest(),
        },
        "snapshot": {
            "relpath": f"{base}/snapshot.json", "root": "data",
            "sha256": snapshot_sha,
        },
    }
    return pins


def test_the_config_admits_the_twin_view_id(tmp_path):
    plan = ki.parse_knowledge_index_config(_release_twin(tmp_path))
    assert plan.view_id == ki.KNOWLEDGE_INDEX_TWIN_VIEW_ID
    assert ki.KNOWLEDGE_INDEX_TWIN_VIEW_ID in ki.KNOWLEDGE_INDEX_VIEW_IDS
    with pytest.raises(ki.KnowledgeIndexError):
        ki.parse_knowledge_index_config(
            {**_release_twin(tmp_path), "view": "slurp-knowledge-index-twin-v2"}
        )


def test_the_twin_view_is_registered_like_the_source():
    from speech_aware_evidence_acquisition.core.base import KNOWLEDGE_INDEX_VIEWS

    ki.registered_orderings()  # populates the three registries
    assert ki.KNOWLEDGE_INDEX_TWIN_VIEW_ID in KNOWLEDGE_INDEX_VIEWS.names()
    assert KNOWLEDGE_INDEX_VIEWS.resolve(
        ki.KNOWLEDGE_INDEX_TWIN_VIEW_ID
    ) == ki.KNOWLEDGE_INDEX_BUILDER_POLICY_ID


def test_the_loader_accepts_the_twin_through_its_own_pins(tmp_path):
    pins = _release_twin(tmp_path)
    table = ki.load_knowledge_index_table(
        tmp_path, release=pins["release"], snapshot=pins["snapshot"],
        view_id=pins["view"],
    )
    assert table.view_id == ki.KNOWLEDGE_INDEX_TWIN_VIEW_ID
    assert table.is_twin
    assert table.twin_of["view_id"] == ki.KNOWLEDGE_INDEX_VIEW_ID
    assert table.header_view_id == ki.KNOWLEDGE_INDEX_VIEW_ID
    assert table.content_hash() == pins["snapshot"]["sha256"], (
        "the snapshot's file sha256 and the view's content hash are ONE number, "
        "for the twin exactly as for the source"
    )


def test_the_binding_loads_the_twin_and_renders_it(tmp_path):
    pins = _release_twin(tmp_path)
    document = ki.parse_knowledge_index_config(pins).as_json()
    binding = ki.build_knowledge_index_binding(
        knowledge_index_json=ki.canonical_json(document), data_root=tmp_path,
    )
    assert binding.table.view_id == ki.KNOWLEDGE_INDEX_TWIN_VIEW_ID
    assert ki.KNOWLEDGE_INDEX_TWIN_VIEW_ID not in binding.index_text
    assert binding.suffix().startswith("\n\n")


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(lambda release: release.pop("twin_of"), id="no-twin_of"),
        pytest.param(lambda release: release.pop("derangement"), id="no-derangement"),
        pytest.param(lambda release: release.pop("gold_read"), id="no-gold_read"),
        pytest.param(
            lambda release: release.update(gold_read=True), id="gold_read-true"
        ),
        pytest.param(
            lambda release: release["derangement"].update(fixed_points=1),
            id="fixed-points",
        ),
        pytest.param(
            lambda release: release["derangement"].update(seed="20260920"),
            id="seed-not-an-integer",
        ),
        pytest.param(
            lambda release: release["derangement"].update(permutation_sha256="0"),
            id="short-permutation-hash",
        ),
        pytest.param(
            lambda release: release["twin_of"].update(view_id="something-else"),
            id="twin_of-names-another-view",
        ),
    ],
)
def test_a_twin_without_its_proof_is_refused(tmp_path, mutate):
    pins = _release_twin(tmp_path, mutate=mutate)
    with pytest.raises(ki.KnowledgeIndexError):
        ki.load_knowledge_index_table(
            tmp_path, release=pins["release"], snapshot=pins["snapshot"],
            view_id=pins["view"],
        )


def test_a_source_view_wearing_a_derangement_is_refused(tmp_path):
    pins = _release_twin(tmp_path, view_id=ki.KNOWLEDGE_INDEX_VIEW_ID)
    with pytest.raises(ki.KnowledgeIndexError):
        ki.load_knowledge_index_table(
            tmp_path, release=pins["release"], snapshot=pins["snapshot"],
            view_id=pins["view"],
        )


def test_the_receipt_names_the_twin_and_carries_twin_of(tmp_path):
    pins = _release_twin(tmp_path)
    table = ki.load_knowledge_index_table(
        tmp_path, release=pins["release"], snapshot=pins["snapshot"],
        view_id=pins["view"],
    )
    plan = ki.parse_knowledge_index_config(pins)
    receipt = ki.knowledge_index_receipt(
        plan=plan, table=table, index_text="x", contacts=[],
    )
    assert receipt["view"]["view_id"] == ki.KNOWLEDGE_INDEX_TWIN_VIEW_ID
    assert receipt["view"]["twin_of"]["view_id"] == ki.KNOWLEDGE_INDEX_VIEW_ID
    assert len(receipt["view"]["twin_of"]["snapshot_content_hash"]) == 64
    # The SOURCE arm's receipt keeps exactly the bytes it has today.
    source = ki.table_from_snapshot(synthetic_snapshot())
    assert "twin_of" not in ki.knowledge_index_receipt(
        plan=ki.default_index_plan(), table=source, index_text="x", contacts=[],
    )["view"]


# ---------------------------------------------------------------------------
# T7: the assembly is form-matched.
# ---------------------------------------------------------------------------

#: An equal-width synthetic view: four intents, four slot types and two edges
#: whose cards differ in CONTENT but not in length, so the two arms' expansion
#: blocks are byte-equal in SIZE. (On the released view the per-row expansion
#: size varies with which cards a row expands; what is matched there is the
#: constant prefix and the multiset of cards, which is T2/T3 above.)
_EQUAL_SHARED = "Missing behavior: Omit this slot when nothing supports it."
_EQUAL_INTENT_SHARED = "Uncertainty behavior: Keep the plausible alternatives."


def _equal_width_snapshot() -> dict:
    intents = ("aaa_one", "bbb_two", "ccc_six", "ddd_ten")
    slots = ("aaa_name", "bbb_name", "ccc_name", "ddd_name")
    groups = {"aaa_one": "aaa", "bbb_two": "bbb", "ccc_six": "ccc", "ddd_ten": "ddd"}
    entries = []
    for rank, name in enumerate(intents, start=1):
        card = (
            f"Intent {name}.\n"
            f"Activation boundary:\n- The {name} request.\n"
            f"{_EQUAL_INTENT_SHARED}\n"
            f"Limitations:\n- Bounded {name} support."
        )
        sections = [
            section for section in ki.parse_card_sections(card)
            if section.name in ki.HOISTED_SECTIONS["intent"]
        ]
        residue, hoisted = ki.hoist_sections(
            card, sections=sections, labels={_EQUAL_INTENT_SHARED: "IU-1"}
        )
        entries.append(
            ki.IndexEntry(
                entry_id=ki.intent_id(name), kind="intent", group=groups[name],
                rank=rank, l1={"Activation boundary": f"- The {name} request."},
                residue=residue, hoisted=hoisted,
            ).as_json()
        )
    for rank, name in enumerate(slots, start=1):
        card = (
            f"Slot {name}.\n"
            f"Admissible formats:\n- Keep the spoken {name} form.\n"
            f"{_EQUAL_SHARED}\n"
            f"Limitations:\n- Bounded {name} support."
        )
        sections = [
            section for section in ki.parse_card_sections(card)
            if section.name in ki.HOISTED_SECTIONS["slot"]
        ]
        residue, hoisted = ki.hoist_sections(
            card, sections=sections, labels={_EQUAL_SHARED: "SM-1"}
        )
        entries.append(
            ki.IndexEntry(
                entry_id=ki.slot_id(name), kind="slot", group="", rank=rank,
                l1={"Admissible formats": f"- Keep the spoken {name} form."},
                residue=residue, hoisted=hoisted,
            ).as_json()
        )
    for source, neighbour in (("aaa_one", "bbb_two"), ("ccc_six", "ddd_ten")):
        entries.append(
            ki.IndexEntry(
                entry_id=ki.edge_id(source, neighbour), kind="edge",
                group=groups[source], rank=1,
                l1={"Confusable exclusions": f"- {source} is not {neighbour}."},
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
        "legal_intents": list(intents),
        "legal_slot_types": list(slots),
        "store_pins": {},
        "shared_sections": [
            {"label": "IU-1", "kind": "intent", "section": "Uncertainty behavior",
             "text": _EQUAL_INTENT_SHARED},
            {"label": "SM-1", "kind": "slot", "section": "Missing behavior",
             "text": _EQUAL_SHARED},
        ],
        "entries": entries,
    }


def test_pointer_and_expansion_blocks_match_in_size_and_differ_in_content():
    snapshot = _equal_width_snapshot()
    source_table, twin_table, _record = _tables(snapshot=snapshot)
    selection = ki.RowSelection(
        candidates=("aaa_one", "bbb_two"),
        exemplar_votes=(("aaa_one", 3),),
        slot_types=("aaa_name", "bbb_name", "ccc_name", "ddd_name"),
    )
    source = ki.assemble(source_table, ki.default_index_plan(), selection)
    twin = ki.assemble(
        twin_table,
        ki.default_index_plan(ki.KNOWLEDGE_INDEX_TWIN_VIEW_ID),
        selection,
    )

    # The pointer block is IDS and RANKS only, so it is byte-identical.
    assert source.pointer_block == twin.pointer_block
    assert source.pointer_ids == twin.pointer_ids

    # The expansion block names the same ids, in the same order, at the same
    # size -- and shows different cards.
    assert source.expanded_ids == twin.expanded_ids
    assert len(source.expansion_text) == len(twin.expansion_text)
    assert source.expansion_text != twin.expansion_text
    assert [item.chars for item in source.expansions] == [
        item.chars for item in twin.expansions
    ]
    source_parts = source.content_parts()
    twin_parts = twin.content_parts()
    assert len(source_parts) == len(twin_parts)
    for left, right in zip(source_parts, twin_parts):
        assert left["evidence_id"] == right["evidence_id"]
        assert len(str(left["text"])) == len(str(right["text"]))
    assert [
        str(part["text"]) for part in source_parts
    ] != [str(part["text"]) for part in twin_parts]


def test_the_twin_names_itself_in_provenance_only():
    snapshot = _equal_width_snapshot()
    _source_table, twin_table, _record = _tables(snapshot=snapshot)
    selection = ki.RowSelection(candidates=("aaa_one",), slot_types=("aaa_name",))
    assembly = ki.assemble(
        twin_table, ki.default_index_plan(ki.KNOWLEDGE_INDEX_TWIN_VIEW_ID), selection
    )
    assert assembly.view_id == ki.KNOWLEDGE_INDEX_TWIN_VIEW_ID
    for item in assembly.evidence_items():
        assert str(item["source_uri"]).startswith(
            f"knowledge-index://{ki.KNOWLEDGE_INDEX_TWIN_VIEW_ID}/"
        )
        # Provenance renders NO byte of the prompt; the rendered content does
        # not name the arm.
        assert ki.KNOWLEDGE_INDEX_TWIN_VIEW_ID not in str(item["content"])
    narrowed = ki.narrow_assembly(assembly, ["value:index-pointers"])
    assert narrowed.view_id == ki.KNOWLEDGE_INDEX_TWIN_VIEW_ID
