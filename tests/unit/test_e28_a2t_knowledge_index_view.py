"""Item E28 (2026-09-21): the Audio2Tool knowledge-INDEX id grammar and view
builder.

Design: ``docs/superpowers/specs/2026-09-21-a2t-engineering-base-index-design
.md`` sections 3 and 4, the paragraph beginning "E28 --". Item E27 (already
merged) added the ``audio2tool`` :class:`~speech_aware_evidence_acquisition
.rails.knowledge_index.KnowledgeIndexCarrierProfile` as DATA ONLY; this item
extends the id grammar to the ``domain``/``tool`` sigils the profile declares
and adds the view builder that renders the 152-tool registry as a released,
pinned knowledge index.

Every test here is model-free, tokenizer-free and offline. The builder test
uses a tiny SYNTHETIC registry authored in this file -- no row of
``tools_registry.csv``, no probe-sample receipt and no gold tool call is read
anywhere in this suite. The one test that reads the released view is
READ-ONLY and skips with a reason when the view is not mounted.

The proofs:

1. the id grammar: ``domain``/``tool`` ids round-trip beside the SLURP kinds;
   a SLURP id is refused under the ``audio2tool`` profile and an Audio2Tool
   id is refused under the ``slurp`` profile; the id grammar is otherwise
   unchanged for SLURP (``KIND_SIGILS`` untouched, ``IndexEntry`` for the
   pre-E28 kinds unaffected);
2. the builder, on a tiny synthetic 2-domain registry, produces deterministic
   domain/tool/edge counts and exactly the edges the rule predicts (one by a
   shared argument name, one by shared description tokens, and a same-domain
   pair that is NOT an edge under either signal);
3. the twin properties (T1 zero fixed points, T2 multiset equality, T3 equal
   rendered length) on that same synthetic view;
4. the edge rule's thresholds (``MIN_SHARED_TOKENS``, ``MIN_TOKEN_LENGTH``)
   and its recorded shape;
5. the released view (if mounted) matches its pins document by sha256.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails import knowledge_index as ki

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_builder():
    """Load ``scripts/build_a2t_knowledge_index_view.py`` by PATH, not by
    dotted import: a third-party package (``verl``) installs a top-level
    ``scripts`` package in the shared venv, so ``import scripts.*`` collides
    unless the repo root is first on ``sys.path``. Loading by file location
    sidesteps the collision entirely."""

    path = REPO_ROOT / "scripts" / "build_a2t_knowledge_index_view.py"
    spec = importlib.util.spec_from_file_location("e28_a2t_builder_under_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(spec.name, module)
    spec.loader.exec_module(module)
    return module


BUILDER = _load_builder()


# ---------------------------------------------------------------------------
# 1. The id grammar.
# ---------------------------------------------------------------------------


def test_domain_and_tool_ids_round_trip():
    domain = ki.domain_id("smart_car")
    assert domain == "D/smart_car"
    assert ki.parse_index_id(domain) == ("domain", ("smart_car",))

    tool = ki.tool_id("setZoneTemperature")
    assert tool == "T/setZoneTemperature"
    assert ki.parse_index_id(tool) == ("tool", ("setZoneTemperature",))


def test_tool_id_accepts_camel_case_and_refuses_non_registry_shapes():
    for bad in ("", "not a name", "has space", "123startsWithDigit", "with-dash"):
        with pytest.raises(ki.KnowledgeIndexError):
            ki.tool_id(bad)


def test_domain_id_still_requires_lower_snake_case():
    with pytest.raises(ki.KnowledgeIndexError):
        ki.domain_id("SmartCar")
    with pytest.raises(ki.KnowledgeIndexError):
        ki.domain_id("smart-car")


def test_edge_id_accepts_camel_case_tool_names_and_lower_snake_intents():
    tool_edge = ki.edge_id("setZoneTemperature", "setFanSpeed")
    assert tool_edge == "E/setZoneTemperature~setFanSpeed"
    assert ki.parse_index_id(tool_edge) == (
        "edge", ("setZoneTemperature", "setFanSpeed"),
    )
    intent_edge = ki.edge_id("play_music", "play_radio")
    assert ki.parse_index_id(intent_edge) == ("edge", ("play_music", "play_radio"))


def test_slurp_ids_are_unchanged_by_the_grammar_extension():
    assert dict(ki.KIND_SIGILS) == {
        "intent": "I", "slot": "S", "edge": "E", "exemplar": "X",
    }
    assert ki.intent_id("play_music") == "I/play_music"
    assert ki.slot_id("artist_name") == "S/artist_name"
    assert ki.parse_index_id("I/play_music") == ("intent", ("play_music",))
    assert ki.parse_index_id("S/artist_name") == ("slot", ("artist_name",))
    # A domain/tool id parses under the default (union) grammar -- this is
    # what lets IndexEntry validate an entry of ANY registered carrier -- but
    # a SLURP-shaped id is refused when it is not one, and vice versa, is
    # what the next two tests prove.
    assert ki.is_index_id("D/smart_car")
    assert ki.is_index_id("T/setZoneTemperature")


def test_audio2tool_id_is_refused_under_the_slurp_profile():
    slurp_profile = ki.knowledge_index_profile("slurp")
    with pytest.raises(ki.KnowledgeIndexError, match="slurp"):
        ki.parse_index_id(ki.tool_id("setZoneTemperature"), profile=slurp_profile)
    with pytest.raises(ki.KnowledgeIndexError, match="slurp"):
        ki.parse_index_id(ki.domain_id("smart_car"), profile=slurp_profile)


def test_slurp_id_is_refused_under_the_audio2tool_profile():
    a2t_profile = ki.knowledge_index_profile("audio2tool")
    with pytest.raises(ki.KnowledgeIndexError, match="audio2tool"):
        ki.parse_index_id(ki.intent_id("play_music"), profile=a2t_profile)
    with pytest.raises(ki.KnowledgeIndexError, match="audio2tool"):
        ki.parse_index_id(ki.slot_id("artist_name"), profile=a2t_profile)


def test_edge_and_exemplar_ids_parse_under_either_profile():
    """``edge``/``exemplar`` are the two kinds every registered profile
    shares (same sigil, same meaning), so an edge or exemplar id is NEVER
    refused purely for being read under "the other" profile."""

    edge = ki.edge_id("setZoneTemperature", "setFanSpeed")
    slurp_profile = ki.knowledge_index_profile("slurp")
    a2t_profile = ki.knowledge_index_profile("audio2tool")
    assert ki.parse_index_id(edge, profile=slurp_profile) == (
        "edge", ("setZoneTemperature", "setFanSpeed"),
    )
    assert ki.parse_index_id(edge, profile=a2t_profile) == (
        "edge", ("setZoneTemperature", "setFanSpeed"),
    )
    exemplar = ki.exemplar_id("10005")
    assert ki.parse_index_id(exemplar, profile=slurp_profile) == ("exemplar", ("10005",))
    assert ki.parse_index_id(exemplar, profile=a2t_profile) == ("exemplar", ("10005",))


def test_index_entry_admits_domain_and_tool_kinds():
    tool_entry = ki.IndexEntry(
        entry_id=ki.tool_id("setZoneTemperature"), kind="tool", group="smart_car",
        rank=0, l1={"Activation boundary": "text"},
    )
    assert tool_entry.line(level="L0", section="") == "T/setZoneTemperature"
    assert tool_entry.line(level="L1", section="Activation boundary") == (
        "T/setZoneTemperature  text"
    )
    domain_entry = ki.IndexEntry(
        entry_id=ki.domain_id("smart_car"), kind="domain", group="smart_car",
        rank=1, l1={"Header": "SMART CAR"},
    )
    assert domain_entry.entry_id == "D/smart_car"


def test_index_entry_still_refuses_a_pointer_only_kind():
    with pytest.raises(ki.KnowledgeIndexError):
        ki.IndexEntry(
            entry_id=ki.exemplar_id("10005"), kind="exemplar", group="", rank=0,
            l1={"x": "y"},
        )


def test_citation_extraction_finds_domain_and_tool_ids():
    text = "See D/smart_car and T/setZoneTemperature, then I/play_music."
    citations = ki.extract_citations(text)
    assert citations == ("D/smart_car", "T/setZoneTemperature", "I/play_music")


# ---------------------------------------------------------------------------
# 2. The edge rule's thresholds and shape.
# ---------------------------------------------------------------------------


def test_edge_rule_shape_and_thresholds():
    assert BUILDER.MIN_SHARED_TOKENS == 3
    assert BUILDER.MIN_TOKEN_LENGTH == 4
    rule = BUILDER.EDGE_RULE
    assert rule["gold_free"] is True
    assert rule["min_shared_tokens"] == 3
    assert rule["min_token_length"] == 4
    assert "rule_id" in rule and "statement" in rule


def test_content_tokens_drops_short_words_and_stopwords():
    tokens = BUILDER.content_tokens("Sets the zone level for the current mode.")
    assert "the" not in tokens
    assert "for" not in tokens
    assert "sets" not in tokens  # length 4 but a generic verb, not asserted here
    assert "zone" in tokens
    assert "level" in tokens
    assert "mode" in tokens
    assert all(len(token) >= BUILDER.MIN_TOKEN_LENGTH for token in tokens)


# ---------------------------------------------------------------------------
# 3. The builder on a tiny synthetic 2-domain registry.
# ---------------------------------------------------------------------------


def _registry_row(
    tool_id: int, domain: str, tool_name: str, signature: str, description: str,
) -> dict[str, str]:
    return {
        "tool_id": str(tool_id),
        "domain": domain,
        "category": "test",
        "tool_name": tool_name,
        "signature": signature,
        "description": description,
        "argument_defaults": "",
        "argument_constraints": "",
    }


def synthetic_registry() -> list[dict[str, str]]:
    """4 tools over 2 domains: a triangle in ``alpha`` exercising all three
    edge outcomes, plus one spectator tool alone in ``beta`` proving edges
    never cross a domain boundary.

    * ``adjustZoneLevel`` / ``setZoneMode`` share the argument ``zone`` --
      an edge by SHARED ARGUMENT, regardless of their descriptions (which
      share no content token).
    * ``adjustZoneLevel`` / ``reportBeaconStatus`` share no argument, but
      their descriptions share three distinctive content tokens (``harbor``,
      ``lighthouse``, ``compass``) -- an edge by SHARED TOKENS.
    * ``setZoneMode`` / ``reportBeaconStatus`` share neither an argument nor
      any content token -- NOT an edge.
    """

    return [
        _registry_row(
            0, "alpha", "adjustZoneLevel", "adjustZoneLevel(zone: Zone, level: Int)",
            "Sets harbor lighthouse compass beacon readings for travel.",
        ),
        _registry_row(
            1, "alpha", "setZoneMode", "setZoneMode(zone: Zone, mode: Mode)",
            "Switches operating profile for weather control.",
        ),
        _registry_row(
            2, "alpha", "reportBeaconStatus", "reportBeaconStatus(status: Status)",
            "Displays harbor lighthouse compass reading for sailors.",
        ),
        _registry_row(
            3, "beta", "toggleBetaSwitch", "toggleBetaSwitch(enabled: Boolean)",
            "Independent beta control action for unrelated tasks.",
        ),
    ]


def synthetic_stores() -> tuple[dict[str, str], dict[str, str]]:
    rows = synthetic_registry()
    activation = {
        row["tool_name"]: f"Activation boundary text for {row['tool_name']}."
        for row in rows
    }
    parameter_meaning = {
        row["tool_name"]: f"Parameter meaning card for {row['tool_name']}."
        for row in rows
    }
    return activation, parameter_meaning


def synthetic_snapshot() -> dict[str, object]:
    rows = synthetic_registry()
    activation, parameter_meaning = synthetic_stores()
    entries = BUILDER.build_entries(rows, activation, parameter_meaning)
    return {
        "schema": ki.KNOWLEDGE_INDEX_VIEW_SCHEMA,
        "view_id": BUILDER.VIEW_ID,
        "builder_policy_id": "saea-a2t-knowledge-index-construction-v1",
        "carrier": "audio2tool",
        "ordering": ki.DOMAIN_ALPHABETICAL_ORDERING,
        "source_split": "train",
        "source_split_identity_hash": "0" * 64,
        "construction_utterance_count": 0,
        "legal_intents": [],
        "legal_slot_types": [],
        "store_pins": {},
        "shared_sections": [],
        "entries": [entry.as_json() for entry in entries],
    }


def test_build_edges_finds_exactly_the_predicted_pairs():
    rows = synthetic_registry()
    edges = BUILDER.build_edges(rows)
    pairs = {(edge["source"], edge["neighbour"]) for edge in edges}
    assert pairs == {
        ("adjustZoneLevel", "setZoneMode"),
        ("adjustZoneLevel", "reportBeaconStatus"),
    }
    assert ("setZoneMode", "reportBeaconStatus") not in pairs
    assert ("reportBeaconStatus", "setZoneMode") not in pairs

    by_pair = {(edge["source"], edge["neighbour"]): edge for edge in edges}
    arg_edge = by_pair[("adjustZoneLevel", "setZoneMode")]
    assert arg_edge["shared_arguments"] == ["zone"]
    token_edge = by_pair[("adjustZoneLevel", "reportBeaconStatus")]
    assert token_edge["shared_arguments"] == []
    assert set(token_edge["shared_tokens"]) >= {"harbor", "lighthouse", "compass"}

    # No edge ever crosses the alpha/beta domain boundary.
    assert all(edge["domain"] == "alpha" for edge in edges)


def test_build_entries_counts_are_deterministic():
    rows = synthetic_registry()
    activation, parameter_meaning = synthetic_stores()
    entries = BUILDER.build_entries(rows, activation, parameter_meaning)
    counts = BUILDER.totals_from_entries(entries)
    assert counts == {"domain": 2, "tool": 4, "edge": 2}

    # Rebuilding from the same inputs is byte-for-byte the same JSON.
    again = BUILDER.build_entries(rows, activation, parameter_meaning)
    assert [e.as_json() for e in entries] == [e.as_json() for e in again]


def test_build_entries_refuses_a_tool_missing_from_a_named_store():
    rows = synthetic_registry()
    activation, parameter_meaning = synthetic_stores()
    del activation["setZoneMode"]
    with pytest.raises(SystemExit):
        BUILDER.build_entries(rows, activation, parameter_meaning)


def test_domain_entries_carry_the_header_text_and_no_l2():
    snapshot = synthetic_snapshot()
    domain_entries = [e for e in snapshot["entries"] if e["kind"] == "domain"]
    ids = {e["id"] for e in domain_entries}
    assert ids == {"D/alpha", "D/beta"}
    for entry in domain_entries:
        assert entry["residue"] == ""


def test_ordering_is_domain_alphabetical():
    snapshot = synthetic_snapshot()
    entries = [ki.entry_from_json(row) for row in snapshot["entries"]]
    ordered = ki.domain_alphabetical_order(entries)
    groups = [entry.group for entry in ordered]
    assert groups == sorted(groups)


# ---------------------------------------------------------------------------
# 4. The derangement twin, on the same synthetic view.
# ---------------------------------------------------------------------------


def test_twin_properties_on_the_synthetic_view():
    source = synthetic_snapshot()
    twin = BUILDER.build_twin(source, seed=20260921)

    assert twin["derangement"]["fixed_points"] == 0
    assert set(twin["derangement"]["kinds"]) <= {"domain", "tool", "edge"}

    before = ki.twin_line_multisets(source)
    after = ki.twin_line_multisets(twin["snapshot"])
    assert before == after

    for field in ("id", "kind", "group", "rank"):
        assert [row[field] for row in source["entries"]] == [
            row[field] for row in twin["snapshot"]["entries"]
        ]

    form = twin["form_match"]
    assert form["rendered_chars"] == form["source_rendered_chars"]
    assert form["rendered_sha256"] != form["source_rendered_sha256"]


def test_twin_reproduces_from_its_seed():
    source = synthetic_snapshot()
    first = BUILDER.build_twin(source, seed=4242)
    second = BUILDER.build_twin(source, seed=4242)
    assert first["snapshot"] == second["snapshot"]
    assert first["derangement"]["permutation_sha256"] == (
        second["derangement"]["permutation_sha256"]
    )


def test_twin_seed_changes_the_permutation():
    source = synthetic_snapshot()
    first = BUILDER.build_twin(source, seed=1)
    second = BUILDER.build_twin(source, seed=2)
    assert first["derangement"]["permutation_sha256"] != (
        second["derangement"]["permutation_sha256"]
    )


def test_render_a2t_constant_index_is_deterministic_and_carrier_specific():
    snapshot = synthetic_snapshot()
    first = BUILDER.render_a2t_constant_index(snapshot)
    second = BUILDER.render_a2t_constant_index(snapshot)
    assert first == second
    assert "ALPHA" in first
    assert "BETA" in first
    assert "T/adjustZoneLevel" in first


def test_render_constant_index_refuses_the_audio2tool_table():
    """The shared SLURP renderer (item E21) must not silently mis-render an
    Audio2Tool table; item E28 leaves that to E29/E30."""

    snapshot = synthetic_snapshot()
    table = ki.table_from_snapshot(snapshot)
    # The kind guard is the FIRST thing render_constant_index checks, before
    # it ever looks at the plan -- an audio2tool table is refused without
    # needing a matching released IndexPlan to exist.
    with pytest.raises(NotImplementedError):
        ki.render_constant_index(table, plan=None)


# ---------------------------------------------------------------------------
# 5. The released view (if mounted) matches its pins document by sha256.
# ---------------------------------------------------------------------------

_PINS_RELPATH = "docs/readiness/2026-09-21-a2t-knowledge-index-release-pins-v1.json"
_RELEASED_RELPATH = "knowledge/audio2tool/semantic/a2t-knowledge-index-v1/release.json"
_TWIN_RELEASED_RELPATH = (
    "knowledge/audio2tool/semantic/a2t-knowledge-index-twin-v1/release.json"
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _pins_document() -> dict[str, object] | None:
    path = REPO_ROOT / _PINS_RELPATH
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _released_path(relpath: str) -> Path | None:
    root = os.environ.get("SPEECHRL_DATA_DIR")
    if not root:
        return None
    path = Path(root) / relpath
    return path if path.is_file() else None


@pytest.mark.skipif(
    _pins_document() is None,
    reason=f"{_PINS_RELPATH} is not present in this checkout",
)
def test_released_view_matches_its_pins_document_by_sha256():
    pins = _pins_document()
    assert pins is not None
    view_pins = pins["views"]["a2t-knowledge-index-v1"]
    released = _released_path(_RELEASED_RELPATH)
    if released is None:
        pytest.skip(
            "the released a2t-knowledge-index-v1 view is not present under "
            "SPEECHRL_DATA_DIR on this machine"
        )
    assert _sha256_file(released) == view_pins["release"]["sha256"]


@pytest.mark.skipif(
    _pins_document() is None,
    reason=f"{_PINS_RELPATH} is not present in this checkout",
)
def test_released_twin_matches_its_pins_document_by_sha256():
    pins = _pins_document()
    assert pins is not None
    twin_pins = pins["views"].get("a2t-knowledge-index-twin-v1")
    if twin_pins is None:
        pytest.skip("the pins document does not (yet) name the twin view")
    released = _released_path(_TWIN_RELEASED_RELPATH)
    if released is None:
        pytest.skip(
            "the released a2t-knowledge-index-twin-v1 view is not present under "
            "SPEECHRL_DATA_DIR on this machine"
        )
    assert _sha256_file(released) == twin_pins["release"]["sha256"]
