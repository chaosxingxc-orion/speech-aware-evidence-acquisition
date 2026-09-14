"""``rails.task_adapter.TaskAdapter`` base defaults (C2 consolidation):

- the bare-base fallback defaults (``serving_geometry``/``strata_of``/
  ``information_spec``/``preprocess_plan``) on a minimal dummy subclass;
- the new ``instruction``/``gold``/``score_response`` hooks fail loudly
  (``NotImplementedError``), not at class-definition time, when a subclass
  relies on the default ``assemble_prompt``/``score`` without implementing
  them (module docstring: several ``rails.probes.*`` adapters predate this
  refactor and never touch these hooks at all -- they must stay
  instantiable);
- ``audio_ref``/``_audio_ref`` backward-compat identity;
- byte-identity of the default ``assemble_prompt`` against the exact shape
  ``Audio2ToolAdapter``/``SlurpAdapter`` hand-built before this refactor;
- ``score`` identity against calling each carrier's own scoring function
  directly;
- the carrier-specific ``serving_geometry`` overrides;
- a gold-leak guard (string search) on both adapters' default prompts.
"""

from __future__ import annotations

import json

import pytest

from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.rails import CandidateInventory
from speech_aware_evidence_acquisition.rails.supply import (
    SupplyDose,
    SupplyForm,
    SupplyItem,
    SupplyPacket,
)
from speech_aware_evidence_acquisition.rails.task_adapter import TaskAdapter


# ---------------------------------------------------------------------------
# Bare-base defaults on a minimal dummy subclass.
# ---------------------------------------------------------------------------


class _DummyTaskAdapter(TaskAdapter):
    def load_split(self, split_id):  # noqa: D102
        return ()

    def build_task_contract(self, sample, obs):  # noqa: D102
        return "contract"


def test_base_serving_geometry_strata_information_and_preprocess_defaults():
    adapter = _DummyTaskAdapter()
    assert adapter.serving_geometry() == {"slots": 1, "slot_tokens": 8192, "max_tokens": 512}
    assert adapter.information_spec() == {}
    assert adapter.preprocess_plan() == {"kind": "speech-packets", "workers": 8}
    assert adapter.strata_of(object()) == "all"


def test_base_candidate_inventory_is_absent_without_a_contract_provider():
    assert _DummyTaskAdapter().candidate_inventory() is None


def test_base_candidate_inventory_delegates_to_the_existing_provider():
    class _Provider:
        candidate_ids = ("first_candidate", "second_candidate")
        source_sha256 = "a" * 64

    class _ProviderAdapter(_DummyTaskAdapter):
        def candidate_contract_provider(self, *, excluded_construction_ids=()):
            assert excluded_construction_ids == ()
            return _Provider()

    assert _ProviderAdapter().candidate_inventory() == CandidateInventory(
        candidate_ids=("first_candidate", "second_candidate"),
        source_sha256="a" * 64,
        source_authority="task-adapter-candidate-contract-provider",
    )


def test_base_candidate_inventory_refuses_a_provider_without_an_inventory():
    class _LookupOnlyProvider:
        source_sha256 = "a" * 64

    class _ProviderAdapter(_DummyTaskAdapter):
        def candidate_contract_provider(self, *, excluded_construction_ids=()):
            return _LookupOnlyProvider()

    with pytest.raises(ValueError, match="candidate_ids must be a tuple"):
        _ProviderAdapter().candidate_inventory()


@pytest.mark.parametrize(
    ("values", "message"),
    [
        (
            {
                "candidate_ids": (),
                "source_sha256": "a" * 64,
                "source_authority": "authority",
            },
            "non-empty",
        ),
        (
            {
                "candidate_ids": ("same", "same"),
                "source_sha256": "a" * 64,
                "source_authority": "authority",
            },
            "duplicate",
        ),
        (
            {
                "candidate_ids": (" leading-space",),
                "source_sha256": "a" * 64,
                "source_authority": "authority",
            },
            "candidate_ids",
        ),
        (
            {
                "candidate_ids": ("candidate",),
                "source_sha256": "A" * 64,
                "source_authority": "authority",
            },
            "source_sha256",
        ),
        (
            {
                "candidate_ids": ("candidate",),
                "source_sha256": "a" * 64,
                "source_authority": " ",
            },
            "source_authority",
        ),
    ],
)
def test_candidate_inventory_refuses_empty_duplicate_or_invalid_values(values, message):
    with pytest.raises(ValueError, match=message):
        CandidateInventory(**values)


def test_candidate_inventory_has_no_task_occurrence_or_roster_size_cap():
    candidate_ids = tuple(f"tool_{index:03d}" for index in range(152))
    assert CandidateInventory(
        candidate_ids=candidate_ids,
        source_sha256="a" * 64,
        source_authority="synthetic-public-registry",
    ).candidate_ids == candidate_ids


def test_base_instruction_gold_score_response_are_not_abc_abstract():
    # Instantiation itself must succeed -- these hooks are deliberately NOT
    # declared via @abc.abstractmethod (module docstring): several
    # rails.probes.* adapters predate this refactor, fully override
    # assemble_prompt/score, and never implement instruction/gold/
    # score_response at all.
    adapter = _DummyTaskAdapter()
    with pytest.raises(NotImplementedError, match="instruction"):
        adapter.instruction(object())
    with pytest.raises(NotImplementedError, match="gold"):
        adapter.gold(object())
    with pytest.raises(NotImplementedError, match="score_response"):
        adapter.score_response(object(), "a response")


def test_base_assemble_prompt_default_fails_loud_without_instruction():
    adapter = _DummyTaskAdapter()

    class _Sample:
        sample_id = "s1"
        media_relpath = "clip.wav"

    with pytest.raises(NotImplementedError, match="instruction"):
        adapter.assemble_prompt(_Sample(), None)


def test_base_score_default_fails_loud_without_gold():
    adapter = _DummyTaskAdapter()
    with pytest.raises(NotImplementedError, match="gold"):
        adapter.score(object(), "a response")


def test_base_extract_consumption_default_is_the_shared_helper():
    adapter = _DummyTaskAdapter()
    trace = adapter.extract_consumption(object(), None, "anything")
    assert trace.records == ()
    assert trace.copy_rate == 0.0


def test_base_audio_ref_and_backward_compatible_alias(tmp_path):
    class _RootedDummy(_DummyTaskAdapter):
        def __init__(self, root):
            self._root = root

    media = tmp_path / "clip.wav"
    media.write_bytes(b"some audio bytes")
    adapter = _RootedDummy(tmp_path)

    ref = adapter.audio_ref("clip.wav")
    alias_ref = adapter._audio_ref("clip.wav")
    assert ref == alias_ref
    assert ref.path == "clip.wav"
    assert len(ref.sha256) == 64


# ---------------------------------------------------------------------------
# Audio2Tool: assemble_prompt byte-identity, score identity, gold-leak guard,
# serving_geometry/strata_of.
# ---------------------------------------------------------------------------


def _audio2tool_adapter(world):
    from speech_aware_evidence_acquisition.rails.adapters.audio2tool import Audio2ToolAdapter

    return Audio2ToolAdapter(load_lock(world.lock_path), world.data_root, repo_root=world.repo_root)


def test_audio2tool_assemble_prompt_is_byte_identical_to_the_frozen_shape(audio2tool_world):
    from speech_aware_evidence_acquisition.rails.adapters.audio2tool import (
        render_audio2tool_instruction,
        render_tool_schemas,
    )

    lock = load_lock(audio2tool_world.lock_path)
    adapter = _audio2tool_adapter(audio2tool_world)
    sample = adapter.load_split("discovery")[0]
    expected_instruction = render_audio2tool_instruction(
        render_tool_schemas(lock, audio2tool_world.data_root)
    )

    zero_supply = adapter.assemble_prompt(sample, None)
    assert zero_supply == (
        {"role": "system", "content": expected_instruction},
        {"role": "user", "content": [{"type": "input_audio", "media_relpath": sample.media_relpath}]},
    )

    supply = SupplyPacket(
        form=SupplyForm.ROSTER,
        dose=SupplyDose(n_items=1, token_count=2),
        prompt_block="Known tools: setLighting",
        assembly_template_id="roster-v1",
        items=(SupplyItem(item_id="i1", text="setLighting"),),
    )
    supplied = adapter.assemble_prompt(sample, supply)
    assert supplied == (
        {"role": "system", "content": expected_instruction},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Known tools: setLighting"},
                {"type": "input_audio", "media_relpath": sample.media_relpath},
            ],
        },
    )


def test_audio2tool_score_matches_score_item_directly(audio2tool_world):
    from speech_aware_evidence_acquisition.data.audio2tool import load_expected_calls
    from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import (
        parse_tool_calls_text,
        score_item,
    )

    lock = load_lock(audio2tool_world.lock_path)
    adapter = _audio2tool_adapter(audio2tool_world)
    sample = adapter.load_split("discovery")[0]
    response = json.dumps([{"name": "setLighting", "arguments": {}}])

    expected_calls = load_expected_calls(
        lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root
    )[sample.sample_id]
    predicted, parsed = parse_tool_calls_text(response)
    item = score_item(expected_calls, predicted)
    expected_metrics = {
        "tool_accuracy": item.tool_accuracy,
        "exact_match": item.exact_match,
        "slot_precision": item.slot_precision,
        "slot_recall": item.slot_recall,
        "slot_f1": item.slot_f1,
        "parsed": parsed,
    }

    assert adapter.gold(sample) == expected_calls
    assert adapter.score_response(adapter.gold(sample), response) == expected_metrics
    assert adapter.score(sample, response) == expected_metrics


def test_audio2tool_assemble_prompt_never_leaks_the_specific_sample_gold(audio2tool_world):
    adapter = _audio2tool_adapter(audio2tool_world)
    sample = next(
        s for s in adapter.load_split("discovery") if s.sample_id == "tier3_multi_intent:000004"
    )
    messages = adapter.assemble_prompt(sample, None)
    rendered = messages[0]["content"] + " ".join(
        part.get("text", "") for part in messages[1]["content"] if part.get("type") == "text"
    )
    # Gold-specific to THIS sample only (module docstring's gold discipline):
    # the tool registry legitimately discloses "Armed_Away" (it is a
    # documented value in setSecurityMode's own argument_constraints), so it
    # is not a leak; these two values are neither a registered tool nor a
    # documented constraint value, and must never appear.
    for leaked_value in ("68.0", "calibrateThermostat"):
        assert leaked_value not in rendered


def test_audio2tool_serving_geometry_and_strata_of_defaults(audio2tool_world):
    adapter = _audio2tool_adapter(audio2tool_world)
    assert adapter.serving_geometry() == {"slots": 2, "slot_tokens": 32768, "max_tokens": 1024}
    sample = adapter.load_split("discovery")[0]
    assert adapter.strata_of(sample) == "all"


# ---------------------------------------------------------------------------
# SLURP: assemble_prompt byte-identity, score identity, gold-leak guard,
# serving_geometry/strata_of.
# ---------------------------------------------------------------------------


def _slurp_adapter(world):
    from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpAdapter

    return SlurpAdapter(load_lock(world.lock_path), world.data_root)


def test_slurp_assemble_prompt_is_byte_identical_to_the_frozen_shape(slurp_world):
    from speech_aware_evidence_acquisition.rails.adapters.slurp import _INSTRUCTION

    adapter = _slurp_adapter(slurp_world)
    sample = adapter.load_split("devel")[0]

    zero_supply = adapter.assemble_prompt(sample, None)
    assert zero_supply == (
        {"role": "system", "content": _INSTRUCTION},
        {"role": "user", "content": [{"type": "input_audio", "media_relpath": sample.media_relpath}]},
    )

    supply = SupplyPacket(
        form=SupplyForm.ROSTER,
        dose=SupplyDose(n_items=1, token_count=1),
        prompt_block="Known entity types: house_place",
        assembly_template_id="roster-v1",
        items=(SupplyItem(item_id="i1", text="house_place"),),
    )
    supplied = adapter.assemble_prompt(sample, supply)
    assert supplied == (
        {"role": "system", "content": _INSTRUCTION},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Known entity types: house_place"},
                {"type": "input_audio", "media_relpath": sample.media_relpath},
            ],
        },
    )


def test_slurp_score_matches_score_slu_directly(slurp_world):
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (
        parse_slu_response,
        score_slu,
    )

    adapter = _slurp_adapter(slurp_world)
    sample = adapter.load_split("devel")[0]
    response = json.dumps(
        {
            "scenario": sample.scenario,
            "action": sample.action,
            "entities": [{"type": e.type, "filler": e.filler} for e in sample.entities],
        }
    )
    predicted_scenario, predicted_action, predicted_entities, parsed = parse_slu_response(response)
    result = score_slu(
        gold_scenario=sample.scenario,
        gold_action=sample.action,
        gold_entities=sample.entities,
        predicted_scenario=predicted_scenario,
        predicted_action=predicted_action,
        predicted_entities=tuple(predicted_entities),
    )
    expected_metrics = dict(result.as_metrics_dict())
    expected_metrics["parsed"] = parsed

    assert adapter.gold(sample) is sample
    assert adapter.score_response(adapter.gold(sample), response) == expected_metrics
    assert adapter.score(sample, response) == expected_metrics


def test_slurp_assemble_prompt_never_leaks_gold_text(slurp_world):
    adapter = _slurp_adapter(slurp_world)
    sample = adapter.load_split("devel")[0]  # kitchen/house_place/iot/hue_lighton
    messages = adapter.assemble_prompt(sample, None)
    rendered = messages[0]["content"] + " ".join(
        part.get("text", "") for part in messages[1]["content"] if part.get("type") == "text"
    )
    assert "kitchen" not in rendered
    assert sample.scenario not in rendered
    assert sample.action not in rendered
    assert sample.intent not in rendered


def test_slurp_serving_geometry_and_strata_of_defaults(slurp_world):
    adapter = _slurp_adapter(slurp_world)
    assert adapter.serving_geometry() == {"slots": 8, "slot_tokens": 8192, "max_tokens": 64}
    sample = adapter.load_split("devel")[0]
    assert adapter.strata_of(sample) == "all"
