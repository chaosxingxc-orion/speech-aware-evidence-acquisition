"""C4b consolidation: ``rails.knowledge_build_common`` -- the shared helpers
factored out of ``rails.knowledge_build`` (SLURP) and
``rails.knowledge_build_a2t`` (Audio2Tool).

The byte-identity tests below assert against FIXED expected values captured
from the pre-consolidation code (the on-disk ``_shingles``/``_jaccard``/
``_greedy_diverse_pick``/``_hamilton_apportion``/``distribution_sample``
BEFORE this module existed), on the exact synthetic inputs reproduced here.
Both build modules' OLD call paths (their still-present private aliases)
must keep reproducing those same numbers after the consolidation.
"""

from __future__ import annotations

import random

import pytest

from speech_aware_evidence_acquisition.rails import knowledge_build as kb
from speech_aware_evidence_acquisition.rails import knowledge_build_a2t as kba2t
from speech_aware_evidence_acquisition.rails import knowledge_build_common as common
from speech_aware_evidence_acquisition.rails.errors import RailsError
from speech_aware_evidence_acquisition.rails.knowledge_build import KbRow
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import A2tKbRow


# ---------------------------------------------------------------------------
# shingles / jaccard
# ---------------------------------------------------------------------------


def test_shingles_matches_captured_pre_edit_values():
    assert sorted(common.shingles("the quick brown fox jumps")) == [
        "brown fox",
        "fox jumps",
        "quick brown",
        "the quick",
    ]
    assert sorted(common.shingles("alarm")) == ["alarm"]
    assert sorted(common.shingles("")) == []


def test_jaccard_matches_captured_pre_edit_values():
    a = frozenset({"the quick", "quick brown", "brown fox"})
    b = frozenset({"quick brown", "brown fox", "fox jumps"})
    assert common.jaccard(a, b) == 0.5
    assert common.jaccard(frozenset(), frozenset()) == 1.0
    assert common.jaccard(frozenset(), a) == 0.0


def test_both_build_modules_private_aliases_match_common_module():
    assert kb._shingles("red green blue") == common.shingles("red green blue")
    assert kba2t._shingles("red green blue") == common.shingles("red green blue")
    a = frozenset({"a b", "b c"})
    b = frozenset({"b c", "c d"})
    assert kb._jaccard(a, b) == common.jaccard(a, b)
    assert kba2t._jaccard(a, b) == common.jaccard(a, b)


# ---------------------------------------------------------------------------
# hamilton_apportion
# ---------------------------------------------------------------------------


def test_hamilton_apportion_matches_captured_pre_edit_values():
    cap = {"alpha": 3, "beta": 5, "gamma": 2, "delta": 7}
    assert common.hamilton_apportion(cap, 6) == {
        "alpha": 1,
        "beta": 2,
        "delta": 2,
        "gamma": 1,
    }
    assert common.hamilton_apportion(cap, 0) == {
        "alpha": 0,
        "beta": 0,
        "delta": 0,
        "gamma": 0,
    }
    assert common.hamilton_apportion(cap, sum(cap.values())) == {
        "alpha": 3,
        "beta": 5,
        "delta": 7,
        "gamma": 2,
    }


def test_both_build_modules_hamilton_alias_matches_common_module():
    cap = {"x": 4, "y": 1, "z": 9}
    assert kb._hamilton_apportion(cap, 5) == common.hamilton_apportion(cap, 5)
    assert kba2t._hamilton_apportion(cap, 5) == common.hamilton_apportion(cap, 5)


def test_hamilton_apportion_refuses_total_over_capacity():
    with pytest.raises(RailsError):
        common.hamilton_apportion({"a": 1}, 2)


# ---------------------------------------------------------------------------
# greedy_diverse_pick -- generalized, SLURP call path (via KbRow accessors)
# ---------------------------------------------------------------------------


def _kb_row(uid: str, content: str, speaker: str) -> KbRow:
    sample_id = f"slurp:train:{uid}:audio"
    return KbRow(
        utterance_id=uid,
        content=content,
        scenario="alarm",
        action="set",
        intent="alarm_set",
        entity_types=(),
        entity_fillers={},
        sample_ids=(sample_id,),
        speaker_by_sample_id={sample_id: speaker},
        media_relpath_by_sample_id={sample_id: f"{uid}.flac"},
    )


_SLURP_CANDIDATES = [
    _kb_row("u1", "wake me up at seven am", "spk1"),
    _kb_row("u2", "wake me up at eight am", "spk1"),
    _kb_row("u3", "set an alarm for tomorrow morning", "spk2"),
    _kb_row("u4", "play some jazz music please", "spk2"),
    _kb_row("u5", "turn off the kitchen lights", "spk3"),
    _kb_row("u6", "what is the weather today", "spk3"),
]
_SLURP_ALREADY = [_kb_row("u0", "wake me up early", "spk0")]

# Captured from the pre-consolidation ``rails.knowledge_build._greedy_diverse_pick``
# on this exact input with ``random.Random("capture-seed-slurp")``.
_SLURP_EXPECTED_PICK_IDS = ["u4", "u6", "u3", "u5"]


def test_slurp_greedy_diverse_pick_alias_matches_captured_pre_edit_values():
    rng = random.Random("capture-seed-slurp")
    picked = kb._greedy_diverse_pick(
        _SLURP_CANDIDATES,
        4,
        _SLURP_ALREADY,
        rng,
        speaker_of=lambda row: row.primary_speaker_id,
        speaker_cap=2,
    )
    assert [row.utterance_id for row in picked] == _SLURP_EXPECTED_PICK_IDS


def test_slurp_greedy_diverse_pick_alias_matches_common_module_directly():
    rng_alias = random.Random("capture-seed-slurp")
    rng_common = random.Random("capture-seed-slurp")
    picked_alias = kb._greedy_diverse_pick(
        _SLURP_CANDIDATES,
        4,
        _SLURP_ALREADY,
        rng_alias,
        speaker_of=lambda row: row.primary_speaker_id,
        speaker_cap=2,
    )
    picked_common = common.greedy_diverse_pick(
        _SLURP_CANDIDATES,
        4,
        _SLURP_ALREADY,
        rng_common,
        text_of=lambda row: row.content,
        id_of=lambda row: row.utterance_id,
        group_of=lambda row: row.primary_speaker_id,
        group_cap=2,
    )
    assert [row.utterance_id for row in picked_alias] == [
        row.utterance_id for row in picked_common
    ]


# ---------------------------------------------------------------------------
# greedy_diverse_pick -- generalized, Audio2Tool call path (via A2tKbRow)
# ---------------------------------------------------------------------------


def _a2t_row(uid: str, text: str, tool: str) -> A2tKbRow:
    sample_id = f"tier1_direct:{uid}"
    return A2tKbRow(
        unit_id=f"tier1_direct:{uid}",
        tier="tier1_direct",
        query_idx=int(uid),
        text=text,
        domain="lighting",
        category="control",
        tool_id=1,
        tool_name=tool,
        arg_signature=(),
        arg_pairs=(),
        call_render=f"{tool}()",
        extra_call_names=(),
        call_count=1,
        sample_ids=(sample_id,),
        item_ids=(int(uid),),
        media_relpath_by_sample_id={sample_id: f"{uid}.wav"},
        speaker_ids=("voice1",),
    )


_A2T_CANDIDATES = [
    _a2t_row("1", "turn on the kitchen lights", "setLighting"),
    _a2t_row("2", "turn on the bedroom lights", "setLighting"),
    _a2t_row("3", "dim the living room lights", "setLighting"),
    _a2t_row("4", "play some jazz music please", "playMusic"),
    _a2t_row("5", "turn off the kitchen fan", "setFan"),
    _a2t_row("6", "what is the weather today", "getWeather"),
]
_A2T_ALREADY = [_a2t_row("0", "turn on the porch lights", "setLighting")]

# Captured from the pre-consolidation ``rails.knowledge_build_a2t._greedy_diverse_pick``
# on this exact input with ``random.Random("capture-seed-a2t")``.
_A2T_EXPECTED_PICK_UNIT_IDS = [
    "tier1_direct:6",
    "tier1_direct:3",
    "tier1_direct:5",
    "tier1_direct:4",
]


def test_a2t_greedy_diverse_pick_alias_matches_captured_pre_edit_values():
    rng = random.Random("capture-seed-a2t")
    picked = kba2t._greedy_diverse_pick(_A2T_CANDIDATES, 4, _A2T_ALREADY, rng, tool_cap=2)
    assert [row.unit_id for row in picked] == _A2T_EXPECTED_PICK_UNIT_IDS


def test_a2t_greedy_diverse_pick_alias_matches_common_module_directly():
    rng_alias = random.Random("capture-seed-a2t")
    rng_common = random.Random("capture-seed-a2t")
    picked_alias = kba2t._greedy_diverse_pick(
        _A2T_CANDIDATES, 4, _A2T_ALREADY, rng_alias, tool_cap=2
    )
    picked_common = common.greedy_diverse_pick(
        _A2T_CANDIDATES,
        4,
        _A2T_ALREADY,
        rng_common,
        text_of=lambda row: row.text,
        id_of=lambda row: row.unit_id,
        group_of=lambda row: row.tool_name,
        group_cap=2,
    )
    assert [row.unit_id for row in picked_alias] == [
        row.unit_id for row in picked_common
    ]


# ---------------------------------------------------------------------------
# distribution_sample -- SLURP-only, moved verbatim, re-exported unchanged
# ---------------------------------------------------------------------------


def _ds_row(uid: str, scenario: str, action: str, speaker: str, entity_types=()) -> KbRow:
    sample_id = f"slurp:train:{uid}:audio"
    return KbRow(
        utterance_id=uid,
        content=f"utterance content {uid}",
        scenario=scenario,
        action=action,
        intent=f"{scenario}_{action}",
        entity_types=entity_types,
        entity_fillers={et: (f"{et}-filler",) for et in entity_types},
        sample_ids=(sample_id,),
        speaker_by_sample_id={sample_id: speaker},
        media_relpath_by_sample_id={sample_id: f"{uid}.flac"},
    )


_DS_ROWS = [
    _ds_row("u1", "alarm", "set", "spk1", ("time",)),
    _ds_row("u2", "alarm", "set", "spk1", ("time",)),
    _ds_row("u3", "alarm", "cancel", "spk2"),
    _ds_row("u4", "music", "play", "spk2", ("artist",)),
    _ds_row("u5", "music", "play", "spk3", ("artist", "genre")),
    _ds_row("u6", "weather", "query", "spk3"),
    _ds_row("u7", "weather", "query", "spk1"),
    _ds_row("u8", "iot", "on", "spk2", ("device",)),
]

# Captured from the pre-consolidation ``rails.knowledge_build.distribution_sample``
# on this exact corpus with size=5/seed=20260901 (the two hard floors alone
# already select 6 rows here, so the returned set is larger than the
# requested size -- exactly the documented "floors are a hard requirement"
# behavior) and size=None/seed=20260901 (the full pool, sorted).
_DS_EXPECTED_SELECTED_IDS = ["u2", "u3", "u4", "u5", "u6", "u8"]
_DS_EXPECTED_FULL_IDS = ["u1", "u2", "u3", "u4", "u5", "u6", "u7", "u8"]


def test_distribution_sample_matches_captured_pre_edit_values():
    selected = common.distribution_sample(_DS_ROWS, 5, 20260901)
    assert [row.utterance_id for row in selected] == _DS_EXPECTED_SELECTED_IDS
    full = common.distribution_sample(_DS_ROWS, None, 20260901)
    assert [row.utterance_id for row in full] == _DS_EXPECTED_FULL_IDS


def test_knowledge_build_distribution_sample_is_the_same_function_object():
    # rails.knowledge_build.distribution_sample must be the EXACT function
    # object moved to knowledge_build_common, not a re-implementation --
    # every existing importer (analysis.slurp_intent_coverage_check, this
    # module's own historical test suite) resolves this dotted path.
    assert kb.distribution_sample is common.distribution_sample


def test_knowledge_build_distribution_sample_matches_captured_pre_edit_values():
    selected = kb.distribution_sample(_DS_ROWS, 5, 20260901)
    assert [row.utterance_id for row in selected] == _DS_EXPECTED_SELECTED_IDS
