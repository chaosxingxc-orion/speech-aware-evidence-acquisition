"""Unit tests for the SLURP slot knowledge-view family (KV).

Every test here is pure: no umbrella lock, no data root, no TRAIN file, no
model, no tokeniser. The renderers take injected material by design, which is
what makes the family testable without opening the corpus -- the corpus-facing
half is the ``rails.phase_material`` factory, exercised by the preparation
pass's own receipt.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.analysis.slurp_slot_vocabulary import (
    SLOT_CLASS_CLOSED,
    SLOT_CLASS_MIXED,
    SLOT_CLASS_OPEN,
    build_vocabulary_card,
    containment_collisions,
    derange_card_mapping,
    token_proxy,
)
from speech_aware_evidence_acquisition.rails import phase_material as pm
from speech_aware_evidence_acquisition.rails.slurp_knowledge_views import (
    CLASS_GLOSSES,
    DESCRIPTION_HEADER,
    FEWSHOT_HEADER,
    FEWSHOT_K,
    FEWSHOT_SEED,
    KV0_SCHEMA_HEADER,
    KV_CELL_IDS,
    KV_VIEWS,
    KV_VIEW_CARDS,
    KV_VIEW_DESCRIPTIONS,
    KV_VIEW_EXAMPLES_FREE,
    KV_VIEW_FEWSHOT,
    Exemplar,
    SlurpKnowledgeViewError,
    assert_view,
    build_type_description,
    compose_view,
    derange_description_mapping,
    donor_intent_mapping,
    render_description_block,
    render_examples_free_block,
    render_fewshot_block,
    select_exemplars,
    view_payloads,
)

# --------------------------------------------------------------------------
# Fixtures: a three-intent toy schema and a TRAIN filler table.
# --------------------------------------------------------------------------

TYPE_TABLES = {
    "alarm_set": (("date", 6, 0.5), ("time", 4, 0.3333), ("alarm_type", 2, 0.1667)),
    "alarm_remove": (("date", 3, 0.6), ("time", 2, 0.4)),
    "music_query": (("artist_name", 5, 1.0),),
    "general_quirky": (),
}
UTTERANCES = {"alarm_set": 40, "alarm_remove": 20, "music_query": 25, "general_quirky": 9}
MENTIONS = {"alarm_set": 12, "alarm_remove": 5, "music_query": 5, "general_quirky": 0}
BLOCK_TYPES = {
    intent: tuple(name for name, _count, _share in table)
    for intent, table in TYPE_TABLES.items()
}

TRAIN_FORMS = {
    "date": {"tomorrow": 6, "friday": 3, "next week": 1},
    "time": {"nine am": 4, "six thirty": 2},
    "alarm_type": {"wake up": 2},
    "artist_name": {"the beatles": 3, "prince": 1, "elton john": 1},
}
CLASSES = {
    "date": SLOT_CLASS_CLOSED,
    "time": SLOT_CLASS_MIXED,
    "alarm_type": SLOT_CLASS_CLOSED,
    "artist_name": SLOT_CLASS_OPEN,
}


def _schema_text(intent: str) -> str:
    return render_examples_free_block(
        TYPE_TABLES,
        intents=(intent,),
        utterances=UTTERANCES,
        mentions=MENTIONS,
        min_share=0.02,
    )


def _descriptions(names):
    return [
        build_type_description(name, TRAIN_FORMS[name], slot_class=CLASSES[name])
        for name in names
    ]


def _cards(names):
    return [build_vocabulary_card(name, TRAIN_FORMS[name]) for name in names]


EXEMPLAR_POOL = (
    Exemplar("slurp:train:000001", "wake me at nine am on friday", (("time", "nine am"), ("date", "friday"))),
    Exemplar("slurp:train:000002", "set an alarm for tomorrow", (("date", "tomorrow"),)),
    Exemplar("slurp:train:000003", "wake up alarm please", (("alarm_type", "wake up"),)),
    Exemplar("slurp:train:000004", "alarm at six thirty", (("time", "six thirty"),)),
    Exemplar("slurp:train:000005", "just set an alarm", ()),
)


# --------------------------------------------------------------------------
# KV-0 -- the example-free block
# --------------------------------------------------------------------------


def test_examples_free_block_prints_no_filler_and_no_false_absence_claim():
    text = _schema_text("alarm_set")
    assert text.startswith(KV0_SCHEMA_HEADER)
    # Not one TRAIN filler survives.
    for forms in TRAIN_FORMS.values():
        for form in forms:
            assert form not in text
    # And the block never claims the corpus recorded none, which is what
    # `examples_per_type=0` through the admitted renderer would have said.
    assert "no example filler recorded" not in text
    assert "- date (50.0 percent of slot mentions)" in text
    assert "== alarm_set == 40 TRAIN utterances, 12 slot mentions" in text


def test_examples_free_block_keeps_the_empty_intent_instruction():
    text = _schema_text("general_quirky")
    assert "no entity type reaches the 2 percent floor" in text


def test_examples_free_block_refuses_an_unknown_intent():
    with pytest.raises(SlurpKnowledgeViewError):
        render_examples_free_block(
            TYPE_TABLES,
            intents=("no_such_intent",),
            utterances=UTTERANCES,
            mentions=MENTIONS,
            min_share=0.02,
        )


# --------------------------------------------------------------------------
# KV-1 -- descriptions
# --------------------------------------------------------------------------


def test_description_lines_carry_statistics_and_never_a_filler_value():
    block = render_description_block(_descriptions(BLOCK_TYPES["alarm_set"]))
    assert block.startswith(DESCRIPTION_HEADER)
    for name, forms in TRAIN_FORMS.items():
        for form in forms:
            assert form not in block, f"{name} description leaked the filler {form!r}"
    assert CLASS_GLOSSES[SLOT_CLASS_CLOSED] in block
    assert "3 distinct TRAIN forms over 10 mentions" in block


def test_description_statistics_are_the_declared_ones():
    described = build_type_description("date", TRAIN_FORMS["date"], slot_class=SLOT_CLASS_CLOSED)
    assert described.train_mentions == 10
    assert described.distinct_forms == 3
    assert described.min_words == 1
    assert described.max_words == 2
    assert described.median_words == 1
    assert described.digit_share == 0.0
    assert described.top_form_share == pytest.approx(0.6)
    assert described.digit_habit == "written without digits"


def test_description_digit_habit_moves_with_the_declared_thresholds():
    mostly_digits = build_type_description(
        "time", {"9 am": 7, "six thirty": 3}, slot_class=SLOT_CLASS_MIXED
    )
    assert mostly_digits.digit_habit == "usually written with digits"
    sometimes = build_type_description(
        "time", {"9 am": 2, "six thirty": 8}, slot_class=SLOT_CLASS_MIXED
    )
    assert sometimes.digit_habit == "sometimes written with digits"


def test_description_builder_is_fail_closed():
    with pytest.raises(SlurpKnowledgeViewError):
        build_type_description("date", {}, slot_class=SLOT_CLASS_CLOSED)
    with pytest.raises(SlurpKnowledgeViewError):
        build_type_description("date", TRAIN_FORMS["date"], slot_class="INVENTED")


def test_description_twin_is_token_matched_by_construction():
    remap = derange_description_mapping(BLOCK_TYPES, TRAIN_FORMS)
    described = {
        name: build_type_description(name, TRAIN_FORMS[name], slot_class=CLASSES[name])
        for name in TRAIN_FORMS
    }
    for intent in ("alarm_set", "alarm_remove"):
        arm = render_description_block([described[name] for name in BLOCK_TYPES[intent]])
        substitution = remap[intent]
        twin = render_description_block(
            [described[substitution[name]] for name in BLOCK_TYPES[intent]]
        )
        # The bodies are re-paired, never re-written: same characters, same
        # proxy tokens, different pairing.
        assert len(twin) == len(arm)
        assert token_proxy(twin) == token_proxy(arm)
        assert twin != arm


def test_description_twin_never_leaves_a_type_its_own_line():
    remap = derange_description_mapping(BLOCK_TYPES, TRAIN_FORMS)
    for intent, mapping in remap.items():
        for name, donor in mapping.items():
            assert name != donor, f"{name} kept its own line in {intent}"


def test_description_twin_refuses_a_single_described_type():
    with pytest.raises(SlurpKnowledgeViewError):
        derange_description_mapping({"only": ("date",)}, ("date",))


def test_description_twin_pools_singleton_intents():
    # `music_query` lists exactly one described type, so it cannot rotate in
    # place and is served from the pool -- the same resolution MF-10's card
    # derangement uses.
    remap = derange_description_mapping(BLOCK_TYPES, TRAIN_FORMS)
    assert remap["music_query"]["artist_name"] != "artist_name"


# --------------------------------------------------------------------------
# KV-2 -- cards (MF-10's library, reused not re-implemented)
# --------------------------------------------------------------------------


def test_card_block_carries_every_train_form_with_its_count():
    block = compose_view(
        intent="alarm_set",
        view=KV_VIEW_CARDS,
        twin=False,
        schema_text=_schema_text("alarm_set"),
        cards=_cards(("date", "alarm_type")),
    )
    assert "tomorrow (6)" in block.view_text
    assert "next week (1)" in block.view_text
    assert "wake up (2)" in block.view_text


def test_card_twin_is_mf10s_own_per_intent_derangement():
    carded = ("date", "time", "alarm_type")
    remap = derange_card_mapping(BLOCK_TYPES, carded)
    cards = {name: build_vocabulary_card(name, TRAIN_FORMS[name]) for name in carded}
    arm = compose_view(
        intent="alarm_set",
        view=KV_VIEW_CARDS,
        twin=False,
        schema_text=_schema_text("alarm_set"),
        cards=[cards[name] for name in BLOCK_TYPES["alarm_set"]],
    )
    twin = compose_view(
        intent="alarm_set",
        view=KV_VIEW_CARDS,
        twin=True,
        schema_text=_schema_text("alarm_set"),
        cards=[cards[remap["alarm_set"][name]] for name in BLOCK_TYPES["alarm_set"]],
    )
    assert len(twin.view_text) == len(arm.view_text)
    assert twin.view_text != arm.view_text


# --------------------------------------------------------------------------
# KV-3 -- exemplars
# --------------------------------------------------------------------------


def test_exemplar_selection_is_deterministic_and_seeded():
    first = select_exemplars(EXEMPLAR_POOL, BLOCK_TYPES["alarm_set"])
    second = select_exemplars(EXEMPLAR_POOL, BLOCK_TYPES["alarm_set"])
    assert [item.utterance_id for item in first] == [item.utterance_id for item in second]
    other = select_exemplars(EXEMPLAR_POOL, BLOCK_TYPES["alarm_set"], seed=1)
    assert isinstance(other, tuple)
    assert len(other) == FEWSHOT_K


def test_exemplar_selection_covers_the_intents_types_before_it_repeats():
    chosen = select_exemplars(EXEMPLAR_POOL, BLOCK_TYPES["alarm_set"], k=FEWSHOT_K)
    covered = {name for item in chosen for name, _filler in item.slots}
    assert set(BLOCK_TYPES["alarm_set"]) <= covered
    assert len({item.utterance_id for item in chosen}) == len(chosen)


def test_exemplar_selection_stops_at_k_and_at_the_pool():
    assert len(select_exemplars(EXEMPLAR_POOL, BLOCK_TYPES["alarm_set"], k=2)) == 2
    assert len(select_exemplars(EXEMPLAR_POOL[:1], BLOCK_TYPES["alarm_set"], k=5)) == 1
    assert select_exemplars((), BLOCK_TYPES["alarm_set"]) == ()


def test_exemplar_selection_refuses_a_non_positive_k():
    with pytest.raises(SlurpKnowledgeViewError):
        select_exemplars(EXEMPLAR_POOL, BLOCK_TYPES["alarm_set"], k=0)


def test_fewshot_block_renders_transcript_then_slots():
    block = render_fewshot_block(EXEMPLAR_POOL[:2])
    assert block.startswith(FEWSHOT_HEADER)
    assert '1. "wake me at nine am on friday" -> time=nine am; date=friday' in block
    assert '2. "set an alarm for tomorrow" -> date=tomorrow' in block


def test_fewshot_block_says_so_when_an_exemplar_carries_no_slot():
    assert "-> no slot" in render_fewshot_block(EXEMPLAR_POOL[4:5])


def test_donor_mapping_stays_inside_the_scenario_and_never_self_donates():
    donors = donor_intent_mapping(
        {
            "alarm": ["alarm_set", "alarm_remove", "alarm_query"],
            "music": ["music_query", "music_likeness"],
        }
    )
    for intent, donor in donors.items():
        assert intent != donor
        assert intent.split("_", 1)[0] == donor.split("_", 1)[0]


def test_donor_mapping_pools_single_intent_scenarios():
    donors = donor_intent_mapping({"alarm": ["alarm_set"], "music": ["music_query"]})
    assert donors == {"alarm_set": "music_query", "music_query": "alarm_set"}


# --------------------------------------------------------------------------
# Composition, containment and cost
# --------------------------------------------------------------------------


def test_compose_view_is_fail_closed_on_missing_or_surplus_material():
    with pytest.raises(SlurpKnowledgeViewError):
        compose_view(
            intent="alarm_set",
            view=KV_VIEW_EXAMPLES_FREE,
            twin=False,
            schema_text=_schema_text("alarm_set"),
            cards=_cards(("date",)),
        )
    with pytest.raises(SlurpKnowledgeViewError):
        compose_view(
            intent="alarm_set",
            view=KV_VIEW_DESCRIPTIONS,
            twin=False,
            schema_text=_schema_text("alarm_set"),
        )
    with pytest.raises(SlurpKnowledgeViewError):
        compose_view(
            intent="alarm_set",
            view=KV_VIEW_FEWSHOT,
            twin=False,
            schema_text=_schema_text("alarm_set"),
        )
    with pytest.raises(SlurpKnowledgeViewError):
        compose_view(
            intent="alarm_set",
            view=KV_VIEW_CARDS,
            twin=False,
            schema_text="   ",
            cards=_cards(("date",)),
        )


def test_kv0_is_the_base_every_other_view_extends():
    base = compose_view(
        intent="alarm_set",
        view=KV_VIEW_EXAMPLES_FREE,
        twin=False,
        schema_text=_schema_text("alarm_set"),
    )
    assert base.view_text == ""
    assert base.text == base.schema_text
    assert base.view_token_proxy == 0
    for view, material in (
        (KV_VIEW_DESCRIPTIONS, {"descriptions": _descriptions(BLOCK_TYPES["alarm_set"])}),
        (KV_VIEW_CARDS, {"cards": _cards(("date", "alarm_type"))}),
        (KV_VIEW_FEWSHOT, {"exemplars": list(EXEMPLAR_POOL[:3])}),
    ):
        rendered = compose_view(
            intent="alarm_set",
            view=view,
            twin=False,
            schema_text=_schema_text("alarm_set"),
            **material,
        )
        assert rendered.text.startswith(base.text + "\n\n")
        assert rendered.token_proxy > base.token_proxy
        assert rendered.as_json()["view"] == view


def test_containment_the_view_never_writes_itself_into_the_arms_directive():
    """C1: the arm's own CONTROL text is view-independent.

    Every KV arm sends the same directive; the view lives only in the
    per-sample block. This is the containment property that holds for every
    view in the family, and the one a fragment could break.
    """

    directive = (
        "Fill the slots for the utterance you just heard. Answer with the "
        "entity list only, using the types named for this intent."
    )
    for view, material in (
        (KV_VIEW_DESCRIPTIONS, {"descriptions": _descriptions(BLOCK_TYPES["alarm_set"])}),
        (KV_VIEW_CARDS, {"cards": _cards(("date", "alarm_type"))}),
        (KV_VIEW_FEWSHOT, {"exemplars": list(EXEMPLAR_POOL[:3])}),
    ):
        rendered = compose_view(
            intent="alarm_set",
            view=view,
            twin=False,
            schema_text=_schema_text("alarm_set"),
            **material,
        )
        assert containment_collisions(view_payloads(rendered), directive) == ()


def test_view_payloads_are_the_block_lines_under_its_header():
    rendered = compose_view(
        intent="alarm_set",
        view=KV_VIEW_CARDS,
        twin=False,
        schema_text=_schema_text("alarm_set"),
        cards=_cards(("date", "alarm_type")),
    )
    payloads = view_payloads(rendered)
    assert len(payloads) == 2
    assert all(line.startswith("- ") for line in payloads)
    base = compose_view(
        intent="alarm_set",
        view=KV_VIEW_EXAMPLES_FREE,
        twin=False,
        schema_text=_schema_text("alarm_set"),
    )
    assert view_payloads(base) == ()


def test_assert_view_refuses_anything_unregistered():
    for view in KV_VIEWS:
        assert assert_view(view) == view
        assert view in KV_CELL_IDS
    for bad in ("cards-v2", "", None, 3):
        with pytest.raises(SlurpKnowledgeViewError):
            assert_view(bad)


# --------------------------------------------------------------------------
# The registered state fill and its hash-pinned class artifact
# --------------------------------------------------------------------------


def test_the_knowledge_view_state_fill_is_registered_on_the_base():
    assert "slurp-slot-knowledge-view-for-state" in pm.PHASE_STATE_FILLS.names()
    assert (
        pm.PHASE_STATE_FILLS.resolve("slurp-slot-knowledge-view-for-state")
        is pm._slurp_slot_knowledge_view_state_fill
    )


def _write_class_artifact(tmp_path, monkeypatch, payload):
    from speech_aware_evidence_acquisition.data import lock as lock_module

    relpath = "docs/receipts/knowledge/kv-classes-test.json"
    path = tmp_path / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
    path.write_bytes(raw)
    monkeypatch.setattr(lock_module, "REPO_ROOT", tmp_path)
    return relpath, hashlib.sha256(raw).hexdigest()


def test_class_artifact_loads_when_its_bytes_match_the_pin(tmp_path, monkeypatch):
    relpath, digest = _write_class_artifact(
        tmp_path, monkeypatch, {"slot_class_by_type": CLASSES}
    )
    assert pm._kv_class_table(relpath, digest) == dict(sorted(CLASSES.items()))


def test_class_artifact_is_fail_closed(tmp_path, monkeypatch):
    relpath, digest = _write_class_artifact(
        tmp_path, monkeypatch, {"slot_class_by_type": CLASSES}
    )
    with pytest.raises(pm.PhaseMaterialError):
        pm._kv_class_table(relpath, "0" * 64)
    with pytest.raises(pm.PhaseMaterialError):
        pm._kv_class_table(relpath, "not-a-digest")
    with pytest.raises(pm.PhaseMaterialError):
        pm._kv_class_table(None, digest)
    with pytest.raises(pm.PhaseMaterialError):
        pm._kv_class_table("../escape.json", digest)
    with pytest.raises(pm.PhaseMaterialError):
        pm._kv_class_table("docs/receipts/knowledge/absent.json", digest)
    empty_relpath, empty_digest = _write_class_artifact(
        tmp_path, monkeypatch, {"slot_class_by_type": {}}
    )
    with pytest.raises(pm.PhaseMaterialError):
        pm._kv_class_table(empty_relpath, empty_digest)


def test_the_fill_factory_refuses_its_own_parameters_before_it_reads_train():
    with pytest.raises(SlurpKnowledgeViewError):
        pm._slurp_slot_knowledge_view_state_fill(view="not-a-view")
    with pytest.raises(pm.PhaseMaterialError):
        pm._slurp_slot_knowledge_view_state_fill(
            view=KV_VIEW_EXAMPLES_FREE, twin="yes"
        )
    with pytest.raises(pm.PhaseMaterialError):
        pm._slurp_slot_knowledge_view_state_fill(view=KV_VIEW_FEWSHOT, k=0)
    with pytest.raises(pm.PhaseMaterialError):
        pm._slurp_slot_knowledge_view_state_fill(view=KV_VIEW_FEWSHOT, seed="20260903")
    # The declared defaults are the ones the family is preregistered under.
    assert FEWSHOT_K == 3
    assert FEWSHOT_SEED == 20260903
