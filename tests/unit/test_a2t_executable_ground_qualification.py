"""Frozen mechanics for Audio2Tool executable-ground qualification."""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.rails.probes.a2t_executable_ground_qualification_flight import (
    GroundQualificationFlightError,
    REGISTRY_DIRECT,
    FULL_EXECUTABLE_GROUND,
    render_qualification_contract,
    run_direct_qualification_phase,
    select_resend_ids,
)


def _tiers() -> dict[str, str]:
    return {
        f"tier{tier}:sample-{index:02d}": f"tier{tier}"
        for tier in range(1, 9)
        for index in range(13)
    }


def test_resend_selection_is_two_per_tier_and_order_invariant() -> None:
    tiers = _tiers()
    selected = select_resend_ids(tiers)
    reversed_selected = select_resend_ids(dict(reversed(tuple(tiers.items()))))
    assert selected == reversed_selected
    assert len(selected) == 16
    assert len(set(selected)) == 16
    assert {
        tier: sum(tiers[sample_id] == tier for sample_id in selected)
        for tier in sorted(set(tiers.values()))
    } == {f"tier{tier}": 2 for tier in range(1, 9)}


def test_resend_selection_refuses_wrong_tier_geometry() -> None:
    tiers = _tiers()
    tiers.pop(next(iter(tiers)))
    with pytest.raises(GroundQualificationFlightError):
        select_resend_ids(tiers)


def test_contract_renderer_changes_only_the_registered_knowledge_source() -> None:
    registry = "TOOL x"
    handbook = "AUDIO2TOOL EXECUTABLE HANDBOOK\n\nReturn only JSON."
    assert (
        render_qualification_contract(
            mode=REGISTRY_DIRECT,
            registry_contract=registry,
            handbook=handbook,
        )
        == (
            "You control tools. Available tools:\nTOOL x\n\n"
            'Respond with ONLY a JSON array of tool calls, e.g. '
            '[{"name": "x", "arguments": {}}].'
        )
    )
    assert (
        render_qualification_contract(
            mode=FULL_EXECUTABLE_GROUND,
            registry_contract=registry,
            handbook=handbook,
        )
        == handbook
    )


@pytest.mark.parametrize(
    "mode,registry,handbook",
    [
        ("unknown", "registry", "handbook"),
        (REGISTRY_DIRECT, "", "handbook"),
        (FULL_EXECUTABLE_GROUND, "registry", ""),
        (FULL_EXECUTABLE_GROUND, "registry", "non-English: \u4e2d"),
    ],
)
def test_contract_renderer_refuses_drift(mode: str, registry: str, handbook: str) -> None:
    with pytest.raises(GroundQualificationFlightError):
        render_qualification_contract(
            mode=mode,
            registry_contract=registry,
            handbook=handbook,
        )


def test_direct_runner_can_preserve_registered_source_slots() -> None:
    class Sample:
        def __init__(self, sample_id: str) -> None:
            self.sample_id = sample_id

    class Adapter:
        def load_split(self, split_id: str):
            assert split_id == "frozen"
            return (Sample("a"), Sample("b"))

        def assemble_prompt(self, sample: Sample, supply: object):
            assert supply is None
            return (
                {"role": "system", "content": "contract"},
                {"role": "user", "content": []},
            )

    class Client:
        def __init__(self) -> None:
            self.slots: dict[str, int] = {}

        def complete(self, messages, **kwargs):
            del messages
            sample_id = kwargs["speech_feature_sample_id"]
            self.slots[sample_id] = kwargs["decoding_params"]["id_slot"]
            return "[]"

    client = Client()
    summary = run_direct_qualification_phase(
        adapter=Adapter(),
        core_client=client,
        split_id="frozen",
        speech_packet_bindings={
            "a": {"packet_id": "a", "sha256": "a" * 64},
            "b": {"packet_id": "b", "sha256": "b" * 64},
        },
        slot_count=2,
        decoding_params={"temperature": 0},
        key_representation_id="key",
        matcher_policy_id="policy",
        slot_by_sample={"a": 1, "b": 0},
    )
    assert [row.sample_id for row in summary.results] == ["a", "b"]
    assert client.slots == {"a": 1, "b": 0}
