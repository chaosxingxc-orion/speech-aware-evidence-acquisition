"""SlurpAdapter (B0 rails): the governed-metadata-backed implementation that
supersedes the former interface-complete stub, plus the mission's own
required "runner executes end-to-end with the mock core client" test.
"""

from __future__ import annotations

import json

import pytest

from speech_aware_evidence_acquisition.contracts import ExecutionPlan
from speech_aware_evidence_acquisition.core.config import protocol_hash
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.data.loader import LoaderError
from speech_aware_evidence_acquisition.rails import (
    ConsumptionOutcome,
    MockCoreClient,
    SupplyDose,
    SupplyForm,
    SupplyItem,
    SupplyPacket,
    TaskAdapter,
    run_rails_experiment,
)
from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpAdapter
from speech_aware_evidence_acquisition.rails.obs import default_obs_packet
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity

_SHA_A = "a" * 64


def _adapter(world) -> SlurpAdapter:
    lock = load_lock(world.lock_path)
    return SlurpAdapter(lock, world.data_root)


def test_slurp_adapter_is_constructible_and_is_a_task_adapter(slurp_world):
    assert isinstance(_adapter(slurp_world), TaskAdapter)


# ---------------------------------------------------------------------------
# load_split / split discipline
# ---------------------------------------------------------------------------


def test_load_split_devel_returns_every_recording_sorted(slurp_world):
    samples = _adapter(slurp_world).load_split("devel")
    assert [s.sample_id for s in samples] == [
        "slurp:devel:000101:audio-101",
        "slurp:devel:000101:audio-101-headset",
        "slurp:devel:000102:audio-102",
    ]
    kitchen = samples[0]
    assert kitchen.utterance_id == "101"
    assert kitchen.scenario == "iot"
    assert kitchen.action == "hue_lighton"
    assert kitchen.intent == "iot_hue_lighton"
    assert kitchen.entities == (SlotEntity(type="house_place", filler="kitchen"),)
    assert kitchen.audio_ref.path == kitchen.media_relpath
    assert len(kitchen.audio_ref.sha256) == 64
    assert kitchen.audio_seconds > 0
    no_entities = samples[2]
    assert no_entities.entities == ()


def test_load_split_unknown_split_raises(slurp_world):
    with pytest.raises(LoaderError, match="unknown SLURP split"):
        _adapter(slurp_world).load_split("bogus")


def test_load_split_test_without_allow_heldout_raises(slurp_world):
    with pytest.raises(LoaderError, match="HELD OUT"):
        _adapter(slurp_world).load_split("test")


def test_load_split_test_with_allow_heldout_succeeds(slurp_world):
    samples = _adapter(slurp_world).load_split("test", allow_heldout=True)
    assert [s.sample_id for s in samples] == ["slurp:test:000201:audio-201"]


def test_load_split_train_synthetic_without_allow_synthetic_raises(slurp_world):
    with pytest.raises(LoaderError, match="TTS-synthesized"):
        _adapter(slurp_world).load_split("train_synthetic")


def test_load_split_train_synthetic_with_allow_synthetic_succeeds(slurp_world):
    samples = _adapter(slurp_world).load_split("train_synthetic", allow_synthetic=True)
    assert [s.sample_id for s in samples] == ["slurp:train_synthetic:000401:audio-401-synth"]


def test_load_split_train_is_real_audio_and_needs_no_flag(slurp_world):
    samples = _adapter(slurp_world).load_split("train")
    assert [s.sample_id for s in samples] == [
        "slurp:train:000301:audio-301",
        "slurp:train:000302:audio-302",
    ]


# ---------------------------------------------------------------------------
# build_task_contract -- ontology roster
# ---------------------------------------------------------------------------


def test_build_task_contract_is_the_ontology_roster_from_train_split_only(slurp_world):
    adapter = _adapter(slurp_world)
    sample = adapter.load_split("devel")[0]
    obs = default_obs_packet(sample)
    task_contract = adapter.build_task_contract(sample, obs)
    document = json.loads(task_contract)
    assert "weather" in document["scenarios"]  # train.jsonl only
    assert "house_place" in document["entity_types"]
    assert "kitchen" in document["entity_types"]["house_place"]
    # train_synthetic must NOT feed the roster by default (2026-08-17 fix:
    # data.slurp.load_slurp_ontology's include_synthetic defaults False --
    # the fixture's only synthetic record is scenario="alarm",
    # type="time"/filler="six", present ONLY in train_synthetic.jsonl).
    assert "alarm" not in document["scenarios"]
    assert "time" not in document["entity_types"]
    # devel's own gold ("iot"/"email") must NOT leak in merely by loading a
    # devel sample -- the roster is mined from train only.
    assert "email" not in document["scenarios"]


# ---------------------------------------------------------------------------
# assemble_prompt -- shape + gold-leak boundary
# ---------------------------------------------------------------------------


def test_assemble_prompt_zero_supply_has_no_text_content_part(slurp_world):
    adapter = _adapter(slurp_world)
    sample = adapter.load_split("devel")[0]
    messages = adapter.assemble_prompt(sample, None)
    assert messages[0]["role"] == "system"
    user_content = messages[1]["content"]
    assert all(part["type"] != "text" for part in user_content)
    assert user_content[-1] == {"type": "input_audio", "media_relpath": sample.media_relpath}


def test_assemble_prompt_with_supply_includes_the_prompt_block(slurp_world):
    adapter = _adapter(slurp_world)
    sample = adapter.load_split("devel")[0]
    supply = SupplyPacket(
        form=SupplyForm.ROSTER,
        dose=SupplyDose(n_items=1, token_count=1),
        prompt_block="Known entity types: house_place",
        assembly_template_id="roster-v1",
        items=(SupplyItem(item_id="i1", text="house_place"),),
    )
    messages = adapter.assemble_prompt(sample, supply)
    user_content = messages[1]["content"]
    assert user_content[0] == {"type": "text", "text": "Known entity types: house_place"}
    assert user_content[-1]["type"] == "input_audio"


def test_assemble_prompt_never_leaks_gold_text(slurp_world):
    """Gold-leak boundary (mission instruction): assemble_prompt's rendered
    output must never contain the gold sentence/filler/scenario/action text
    unless it arrived via a SupplyPacket the caller explicitly built."""

    adapter = _adapter(slurp_world)
    sample = adapter.load_split("devel")[0]  # kitchen/house_place/iot/hue_lighton
    assert sample.scenario == "iot"
    assert sample.action == "hue_lighton"
    assert sample.entities[0].filler == "kitchen"

    def rendered_text(messages) -> str:
        parts = [messages[0]["content"]]
        for part in messages[1]["content"]:
            if part["type"] == "text":
                parts.append(part["text"])
        return " ".join(parts)

    zero_supply_text = rendered_text(adapter.assemble_prompt(sample, None))
    assert "kitchen" not in zero_supply_text
    assert "house_place" not in zero_supply_text
    assert sample.scenario not in zero_supply_text
    assert sample.action not in zero_supply_text
    assert sample.intent not in zero_supply_text

    unrelated_supply = SupplyPacket(
        form=SupplyForm.ROSTER,
        dose=SupplyDose(n_items=1, token_count=1),
        prompt_block="Known entity types: currency_name, food_type",
        assembly_template_id="roster-v1",
        items=(SupplyItem(item_id="i1", text="currency_name"),),
    )
    supplied_text = rendered_text(adapter.assemble_prompt(sample, unrelated_supply))
    assert "kitchen" not in supplied_text
    assert "house_place" not in supplied_text
    assert sample.scenario not in supplied_text
    assert sample.action not in supplied_text


# ---------------------------------------------------------------------------
# score -- exact match, partial (distance-based) match, unparseable
# ---------------------------------------------------------------------------


def test_score_exact_match_scores_perfectly(slurp_world):
    adapter = _adapter(slurp_world)
    sample = adapter.load_split("devel")[0]  # iot/hue_lighton, house_place=kitchen
    response = json.dumps(
        {
            "scenario": "iot",
            "action": "hue_lighton",
            "entities": [{"type": "house_place", "filler": "kitchen"}],
        }
    )
    metrics = adapter.score(sample, response)
    assert metrics["parsed"] is True
    assert metrics["scenario_action_exact"] == 1.0
    assert metrics["slot_f1_exact_f1"] == 1.0
    assert metrics["slu_f1_f1"] == 1.0
    assert metrics["slu_f1_word_f1"] == 1.0
    assert metrics["slu_f1_char_f1"] == 1.0


def test_score_partial_filler_gets_distance_credit_but_not_exact_credit(slurp_world):
    adapter = _adapter(slurp_world)
    sample = adapter.load_split("devel")[0]  # gold filler "kitchen"
    response = json.dumps(
        {
            "scenario": "iot",
            "action": "hue_lighton",
            "entities": [{"type": "house_place", "filler": "the kitchen"}],
        }
    )
    metrics = adapter.score(sample, response)
    # Exact dict match fails (extra "the").
    assert metrics["slot_f1_exact_tp"] == 0.0
    assert metrics["slot_f1_exact_fp"] == 1.0
    assert metrics["slot_f1_exact_fn"] == 1.0
    # Distance-based match still counts a TP (type matches) with a
    # partial-credit distance charged to both FP and FN, never the full
    # exact-match penalty. Word-distance is WER = edit_ops / len(gold
    # words); the gold filler is a single word ("kitchen"), so inserting
    # one extra word saturates WER at exactly 1.0 -- that is the official
    # metric's own arithmetic for a one-word reference, not a bug here.
    assert metrics["slu_f1_word_tp"] == 1.0
    assert metrics["slu_f1_word_fp"] == 1.0
    assert metrics["slu_f1_word_fn"] == 1.0
    # Char-distance normalizes by string length ("kitchen" is 7 chars, "the
    # kitchen" is 11), so the SAME pair gets genuine fractional credit here.
    assert metrics["slu_f1_char_tp"] == 1.0
    assert 0.0 < metrics["slu_f1_char_fp"] < 1.0
    assert 0.0 < metrics["slu_f1_char_fn"] < 1.0


def test_score_unparseable_response_scores_as_a_full_miss(slurp_world):
    adapter = _adapter(slurp_world)
    sample = adapter.load_split("devel")[0]
    metrics = adapter.score(sample, "not json at all")
    assert metrics["parsed"] is False
    assert metrics["scenario_action_exact"] == 0.0
    assert metrics["slot_f1_exact_tp"] == 0.0
    assert metrics["slot_f1_exact_fn"] == 1.0  # the one gold entity, missed


def test_score_no_gold_entities_and_no_predicted_entities_is_zero_not_nan(slurp_world):
    adapter = _adapter(slurp_world)
    sample = adapter.load_split("devel")[2]  # email query, no entities
    response = json.dumps({"scenario": "email", "action": "query", "entities": []})
    metrics = adapter.score(sample, response)
    assert metrics["scenario_action_exact"] == 1.0
    assert metrics["slot_f1_exact_precision"] == 0.0
    assert metrics["slot_f1_exact_recall"] == 0.0
    assert metrics["slot_f1_exact_f1"] == 0.0


# ---------------------------------------------------------------------------
# extract_consumption
# ---------------------------------------------------------------------------


def test_extract_consumption_zero_supply_is_empty(slurp_world):
    adapter = _adapter(slurp_world)
    sample = adapter.load_split("devel")[0]
    trace = adapter.extract_consumption(sample, None, "anything")
    assert trace.records == ()


def test_extract_consumption_with_supply_detects_the_copy(slurp_world):
    adapter = _adapter(slurp_world)
    sample = adapter.load_split("devel")[0]
    supply = SupplyPacket(
        form=SupplyForm.ROSTER,
        dose=SupplyDose(n_items=1, token_count=1),
        prompt_block="house_place",
        assembly_template_id="roster-v1",
        items=(SupplyItem(item_id="i1", text="house_place"),),
    )
    response = json.dumps(
        {"scenario": "iot", "action": "hue_lighton", "entities": [{"type": "house_place", "filler": "kitchen"}]}
    )
    trace = adapter.extract_consumption(sample, supply, response)
    assert trace.records[0].outcome == ConsumptionOutcome.COPY
    assert trace.copy_rate == 1.0


# ---------------------------------------------------------------------------
# Mission-required test: runner executes end-to-end with the mock core
# client on the SLURP adapter.
# ---------------------------------------------------------------------------


def _plan() -> ExecutionPlan:
    return ExecutionPlan(
        run_id="SAEA-E-TEST-rails-slurp",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="slurp",
        split_role="discovery",
        split_identity_hash=_SHA_A,
        planned_model_calls=10,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=1000,
        protocol_hash=protocol_hash("f" * 64, "bare-core", _SHA_A),
        attempt_id="attempt-rails-slurp-0001",
    )


def test_runner_executes_end_to_end_with_the_mock_core_client_on_slurp(slurp_world, tmp_path):
    adapter = _adapter(slurp_world)
    devel_samples = adapter.load_split("devel")
    gold_by_relpath = {
        sample.media_relpath: json.dumps(
            {
                "scenario": sample.scenario,
                "action": sample.action,
                "entities": [{"type": e.type, "filler": e.filler} for e in sample.entities],
            }
        )
        for sample in devel_samples
    }
    has_gold_entities_by_relpath = {
        sample.media_relpath: bool(sample.entities) for sample in devel_samples
    }

    def responder(messages):
        media_relpath = messages[1]["content"][-1]["media_relpath"]
        return gold_by_relpath[media_relpath]

    client = MockCoreClient(responder=responder)

    def supply_builder(sample, obs, task_contract):
        return SupplyPacket(
            form=SupplyForm.ROSTER,
            dose=SupplyDose(n_items=1, token_count=1),
            prompt_block="house_place",
            assembly_template_id="roster-v1",
            items=(SupplyItem(item_id="i1", text="house_place"),),
        )

    summary = run_rails_experiment(
        data_root=tmp_path,
        plan=_plan(),
        adapter=adapter,
        core_client=client,
        split_id="devel",
        supply_builder=supply_builder,
    )

    # 3 recordings x 2 arms (zero-supply, supplied)
    assert len(summary.results) == 6
    assert len(client.calls) == 6
    zero_supply = [r for r in summary.results if r.arm == "zero-supply"]
    supplied = [r for r in summary.results if r.arm == "supplied"]
    assert len(zero_supply) == len(supplied) == 3
    # Every response matched its own sample's gold exactly (the responder
    # keys off media_relpath, never gold text baked into the prompt).
    assert all(r.metrics["scenario_action_exact"] == 1.0 for r in summary.results)
    # slot_f1_exact_f1 is 1.0 for the samples that actually carry a gold
    # entity (the "kitchen" recordings); the no-entity sample (102) legally
    # scores precision=recall=f1=0.0 under the official zero-guard
    # convention (TP=FP=FN=0 -- nothing was there to have used), matching
    # test_score_no_gold_entities_and_no_predicted_entities_is_zero_not_nan.
    for result in summary.results:
        media_relpath = result.messages[1]["content"][-1]["media_relpath"]
        expected_f1 = 1.0 if has_gold_entities_by_relpath[media_relpath] else 0.0
        assert result.metrics["slot_f1_exact_f1"] == expected_f1
    assert all(r.consumption.records == () for r in zero_supply)
