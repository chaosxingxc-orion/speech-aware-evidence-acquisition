"""Plain-English Audio2Tool cards and bounded hierarchical retrieval."""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.rails import a2t_plain_english_cards as cards
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import A2tKbRow


def _registry_row(
    name: str,
    description: str,
    *,
    signature: str | None = None,
    category: str = "lighting",
    defaults: str = "",
    constraints: str = "",
) -> dict[str, str]:
    return {
        "tool_id": "1",
        "domain": "smart_home",
        "category": category,
        "tool_name": name,
        "signature": signature or f"{name}()",
        "description": description,
        "argument_defaults": defaults,
        "argument_constraints": constraints,
    }


def _row(
    index: int,
    *,
    tier: str,
    tool: str,
    pairs: tuple[tuple[str, str], ...] = (),
    text: str = "PRIVATE CONSTRUCTION UTTERANCE",
    extra_calls: tuple[str, ...] = (),
    sample_id: str | None = None,
) -> A2tKbRow:
    sequence = (tool, *extra_calls)
    return A2tKbRow(
        unit_id=f"{tier}:{index:06d}",
        tier=tier,
        query_idx=index,
        text=text,
        domain="smart_home",
        category="lighting",
        tool_id=1,
        tool_name=tool,
        arg_signature=tuple(key for key, _value in pairs),
        arg_pairs=pairs,
        call_render=" ".join(f"{name}()" for name in sequence),
        extra_call_names=extra_calls,
        call_count=len(sequence),
        sample_ids=(sample_id or f"{tier}:{index:06d}",),
        item_ids=(index,),
        media_relpath_by_sample_id={},
        speaker_ids=("speaker",),
    )


def _world() -> tuple[tuple[dict[str, str], ...], tuple[A2tKbRow, ...]]:
    registry = (
        _registry_row(
            "getLightState",
            "Read the current state of a light.",
            signature="getLightState(deviceId: String)",
            category="status",
        ),
        _registry_row(
            "sendMessage",
            "Send a message to a named recipient.",
            signature="sendMessage(recipient: String, message: String)",
            category="communication",
            defaults="recipient=null",
        ),
        _registry_row(
            "setLightState",
            "Change a light to the requested state.",
            signature="setLightState(deviceId: String, state: LightState)",
            defaults="state='On'",
        ),
        _registry_row(
            "setLightLevel",
            "Change the brightness level of a light.",
            signature="setLightLevel(deviceId: String, level: Integer)",
        ),
    )
    rows: list[A2tKbRow] = []
    for index in range(1, 6):
        rows.append(
            _row(
                index,
                tier="tier1_direct",
                tool="setLightState",
                pairs=(("deviceId", f"PRIVATE-LAMP-{index}"), ("state", "On")),
                text=f"Please switch private lamp {index} on",
            )
        )
    rows.extend(
        (
            _row(
                10,
                tier="tier2_parametric",
                tool="setLightState",
                pairs=(("deviceId", "PRIVATE-X"),),
                text="Turn the private light off",
            ),
            _row(
                11,
                tier="tier1_direct",
                tool="getLightState",
                pairs=(("deviceId", "PRIVATE-X"),),
                text="What is the private light state",
            ),
            _row(
                12,
                tier="tier2_parametric",
                tool="setLightLevel",
                pairs=(("deviceId", "PRIVATE-X"), ("level", "37")),
                text="Dim the private lamp",
            ),
            _row(
                13,
                tier="tier1_direct",
                tool="sendMessage",
                pairs=(("recipient", "PRIVATE-PERSON"), ("message", "PRIVATE-MESSAGE")),
                text="Send the private note",
            ),
            _row(
                14,
                tier="tier3_multi_intent",
                tool="setLightLevel",
                pairs=(("deviceId", "PRIVATE-X"), ("level", "55")),
                text="Dim the light and send a message",
                extra_calls=("sendMessage",),
            ),
        )
    )
    return registry, tuple(rows)


def test_corpus_is_complete_plain_english_and_tier_conditioned() -> None:
    registry, rows = _world()

    corpus = cards.build_plain_english_card_corpus(registry, rows)

    assert corpus.report["registry_tool_count"] == 4
    assert corpus.report["detailed_tool_card_count"] == 4
    assert corpus.index_text.count(" - ") == 4
    assert "setLightState - Change a light to the requested state." in corpus.index_text
    assert corpus.corpus_text.isascii()
    detail = corpus.tool_cards_by_name["setLightState"].text
    assert "Tool name: setLightState" in detail
    assert "Meaning: Change a light to the requested state." in detail
    assert "Nearest tool contrasts:" in detail
    assert "getLightState" in detail
    assert "deviceId (String)" in detail
    assert "state (LightState)" in detail
    assert "For tier1_direct, observed argument inclusion patterns:" in detail
    assert "deviceId and state" in detail
    assert "For tier2_parametric, observed argument inclusion patterns:" in detail
    assert "deviceId" in detail
    assert "Required in every tier" not in detail
    assert "U000" not in corpus.corpus_text
    assert "K00" not in corpus.corpus_text
    assert "P T1" not in corpus.corpus_text


def test_only_registry_confirmed_construction_stable_defaults_are_rendered() -> None:
    registry, rows = _world()

    corpus = cards.build_plain_english_card_corpus(
        registry,
        rows,
        stable_default_min_observations=5,
    )

    detail = corpus.tool_cards_by_name["setLightState"].text
    assert 'Construction-stable default: state = "On"' in detail
    assert "PRIVATE-LAMP" not in corpus.corpus_text
    assert "PRIVATE-X" not in corpus.corpus_text
    assert "PRIVATE-PERSON" not in corpus.corpus_text
    assert "PRIVATE-MESSAGE" not in corpus.corpus_text
    assert corpus.report["stable_default_count"] == 1


def test_detailed_cards_preserve_public_argument_constraints() -> None:
    registry, rows = _world()
    constrained = tuple(
        {
            **row,
            "argument_constraints": "level: [0-100]"
            if row["tool_name"] == "setLightLevel"
            else row["argument_constraints"],
        }
        for row in registry
    )

    corpus = cards.build_plain_english_card_corpus(constrained, rows)

    detail = corpus.tool_cards_by_name["setLightLevel"].text
    assert "Public argument constraints: level: [0-100]" in detail


def test_corpus_does_not_render_source_text_or_identity_and_rejects_overlap() -> None:
    registry, rows = _world()
    private_texts = tuple(row.text for row in rows)
    private_ids = tuple(sample_id for row in rows for sample_id in row.sample_ids)

    corpus = cards.build_plain_english_card_corpus(registry, rows)

    assert all(text not in corpus.corpus_text for text in private_texts)
    assert all(sample_id not in corpus.corpus_text for sample_id in private_ids)
    assert corpus.report["source_utterances_rendered"] == 0
    assert corpus.report["sample_ids_rendered"] == 0
    assert corpus.report["row_argument_values_rendered"] == 0
    assert corpus.report["construction_retrieval_document_count"] == len(rows)
    assert corpus.report["construction_access_sha256"] == corpus.construction_access_sha256
    with pytest.raises(cards.PlainEnglishCardError, match="forbidden sample"):
        cards.build_plain_english_card_corpus(
            registry,
            rows,
            forbidden_sample_ids={private_ids[0]},
        )


def test_corpus_is_deterministic_and_obeys_corpus_and_card_caps() -> None:
    registry, rows = _world()

    first = cards.build_plain_english_card_corpus(registry, rows)
    second = cards.build_plain_english_card_corpus(
        tuple(reversed(registry)), tuple(reversed(rows))
    )

    assert first == second
    assert first.report["corpus_utf8_bytes"] <= first.report["max_corpus_utf8_bytes"]
    assert first.report["largest_tool_card_utf8_bytes"] <= first.report[
        "max_tool_card_utf8_bytes"
    ]
    with pytest.raises(cards.PlainEnglishCardError, match="corpus byte budget"):
        cards.build_plain_english_card_corpus(registry, rows, max_corpus_utf8_bytes=100)
    with pytest.raises(cards.PlainEnglishCardError, match="tool-card byte budget"):
        cards.build_plain_english_card_corpus(registry, rows, max_tool_card_utf8_bytes=100)


def test_hierarchical_retrieval_returns_bounded_matched_and_shuffled_packets() -> None:
    registry, rows = _world()
    corpus = cards.build_plain_english_card_corpus(registry, rows)

    route = cards.retrieve_plain_english_packets(
        "Dim the private lamp",
        corpus,
        detailed_tool_limit=2,
        behavior_card_limit=2,
        shuffle_seed=20260902,
    )

    assert route.matched_tool_names[0] == "setLightLevel"
    assert len(route.matched_tool_names) == 2
    assert len(route.matched_behavior_ids) == 2
    assert set(route.matched_tool_names).isdisjoint(route.shuffled_tool_names)
    assert set(route.matched_behavior_ids).isdisjoint(route.shuffled_behavior_ids)
    assert route.matched_packet != route.shuffled_packet
    assert route.matched_packet.startswith("AUDIO2TOOL PLAIN-ENGLISH FULL-GROUND PACKET")
    assert "COMPLETE TOOL NAME AND MEANING INDEX (4 tools)" in route.matched_packet
    assert route.matched_packet.count("Tool name:") == 2
    assert len(route.matched_packet.encode("utf-8")) <= route.packet_utf8_byte_cap
    assert len(route.shuffled_packet.encode("utf-8")) <= route.packet_utf8_byte_cap
    assert route.group_ranking
    assert all(isinstance(score, int) for _name, score in route.tool_ranking)

    repeated = cards.retrieve_plain_english_packets(
        "Dim the private lamp",
        corpus,
        detailed_tool_limit=2,
        behavior_card_limit=2,
        shuffle_seed=20260902,
    )
    assert route == repeated

    action_route = cards.retrieve_plain_english_packets(
        "Turn the kitchen light on",
        corpus,
        detailed_tool_limit=2,
        behavior_card_limit=2,
    )
    assert action_route.matched_tool_names[0] == "setLightState"


def test_construction_bm25_projects_complete_multi_intent_sequence() -> None:
    registry, rows = _world()
    corpus = cards.build_plain_english_card_corpus(registry, rows)

    route = cards.retrieve_plain_english_packets(
        "Dim the light and send a message",
        corpus,
        detailed_tool_limit=2,
        behavior_card_limit=1,
    )

    assert route.matched_tool_names == ("setLightLevel", "sendMessage")
    assert len(route.construction_unit_ranking) == 1
    assert route.construction_unit_ranking[0][1] > 0.0


def test_k32_access_is_order_invariant_bounded_and_has_disjoint_shuffle() -> None:
    registry = tuple(
        _registry_row(
            f"tool{index:03d}",
            f"Perform operation number {index}.",
            category=f"category{index % 5}",
        )
        for index in range(70)
    )
    rows = tuple(
        _row(
            index + 1,
            tier="tier1_direct",
            tool=f"tool{index:03d}",
            text=f"Other operation number {index}",
        )
        for index in range(70)
    ) + tuple(
        _row(
            100 + index,
            tier="tier1_direct",
            tool="tool000",
            text="Perform operation target",
        )
        for index in range(40)
    )
    first = cards.build_plain_english_card_corpus(registry, rows)
    second = cards.build_plain_english_card_corpus(
        tuple(reversed(registry)), tuple(reversed(rows))
    )

    first_route = cards.retrieve_plain_english_packets(
        "Perform operation target",
        first,
        detailed_tool_limit=32,
        behavior_card_limit=4,
        shuffle_seed=9,
    )
    second_route = cards.retrieve_plain_english_packets(
        "Perform operation target",
        second,
        detailed_tool_limit=32,
        behavior_card_limit=4,
        shuffle_seed=9,
    )

    assert first_route == second_route
    assert len(first_route.matched_tool_names) == 32
    assert first_route.matched_tool_names[0] == "tool000"
    assert len(first_route.construction_unit_ranking) > 32
    assert set(first_route.matched_tool_names).isdisjoint(
        first_route.shuffled_tool_names
    )
    assert len(first_route.matched_packet.encode("utf-8")) <= first_route.packet_utf8_byte_cap


@pytest.mark.parametrize(
    ("observation", "match"),
    (("", "non-empty"), ("caf\u00e9", "ASCII English"), ("x" * 4097, "character cap")),
)
def test_retrieval_rejects_invalid_or_overlong_observations(
    observation: str, match: str
) -> None:
    registry, rows = _world()
    corpus = cards.build_plain_english_card_corpus(registry, rows)

    with pytest.raises(cards.PlainEnglishCardError, match=match):
        cards.retrieve_plain_english_packets(observation, corpus)


def test_retrieval_refuses_impossible_limits_and_packet_cap() -> None:
    registry, rows = _world()
    corpus = cards.build_plain_english_card_corpus(registry, rows)

    with pytest.raises(cards.PlainEnglishCardError, match="detailed_tool_limit"):
        cards.retrieve_plain_english_packets("light", corpus, detailed_tool_limit=33)
    with pytest.raises(cards.PlainEnglishCardError, match="behavior_card_limit"):
        cards.retrieve_plain_english_packets("light", corpus, behavior_card_limit=5)
    with pytest.raises(cards.PlainEnglishCardError, match="packet byte budget"):
        cards.retrieve_plain_english_packets("light", corpus, packet_utf8_byte_cap=100)
