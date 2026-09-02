"""G4 executable-microground OpenJiuwen flight boundary."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails.adapters.audio2tool import (
    Audio2ToolSample,
)
from speech_aware_evidence_acquisition.rails.obs import AudioRef
from speech_aware_evidence_acquisition.rails.probes.a2t_g4_microground_flight import (
    G4_EXPECTED_SCREEN_ROWS,
    G4_MICROGROUND_E_PHASE,
    G4_MICROGROUND_SE_PHASE,
    G4_SCREEN_SPLIT_ID,
    G4_SE_STATE_UTF8_BYTE_CAP,
    G4_STATE_UTF8_BYTE_CAP,
    G4MicrogroundAdapter,
    G4MicrogroundFlightError,
    G4SingleContactController,
    run_g4_microground_phase,
)


def _samples(count: int = G4_EXPECTED_SCREEN_ROWS) -> tuple[Audio2ToolSample, ...]:
    return tuple(
        Audio2ToolSample(
            sample_id=f"tier{index % 8 + 1}:sample-{index:02d}",
            audio_ref=AudioRef(path=f"audio/{index:02d}.wav", sha256=f"{index:064x}"),
            audio_seconds=1.0 + index,
            media_relpath=f"audio/{index:02d}.wav",
        )
        for index in range(count)
    )


def _state(sample_id: str) -> str:
    return f"Turn 1 user request for {sample_id.replace(':', ' ')}."


def _packet(sample_id: str) -> str:
    return f"EXECUTABLE MICROGROUND PACKET\nRoute for {sample_id.replace(':', ' ')}."


def _maps(
    samples: tuple[Audio2ToolSample, ...],
) -> tuple[dict[str, str], dict[str, str]]:
    return (
        {sample.sample_id: _state(sample.sample_id) for sample in samples},
        {sample.sample_id: _packet(sample.sample_id) for sample in samples},
    )


@dataclass(frozen=True)
class _Result:
    sample_id: str
    final_response_text: str
    contacts: tuple[object, ...]


def _summary(samples: tuple[Audio2ToolSample, ...], *, contacts: int = 1) -> object:
    return SimpleNamespace(
        agent_executor_id="openjiuwen-workflow-v1",
        results=tuple(
            _Result(
                sample.sample_id,
                '[{"name":"setLightState","arguments":{}}]',
                tuple(object() for _ in range(contacts)),
            )
            for sample in samples
        ),
    )


@pytest.mark.parametrize(
    ("phase", "representation_label"),
    (
        (G4_MICROGROUND_E_PHASE, "task-blind English observation"),
        (G4_MICROGROUND_SE_PHASE, "validated structured dialogue state"),
    ),
)
def test_adapter_renders_bounded_sample_local_state_packet_and_original_speech(
    phase: str,
    representation_label: str,
) -> None:
    samples = _samples()
    states, packets = _maps(samples)
    adapter = G4MicrogroundAdapter(
        samples,
        phase=phase,
        state_by_sample=states,
        packet_by_sample=packets,
    )

    sample = samples[0]
    contract = adapter.build_task_contract(sample, object())
    prompt = adapter.assemble_prompt(sample, None)

    assert representation_label in contract
    assert states[sample.sample_id] in contract
    assert packets[sample.sample_id] in contract
    assert sample.sample_id not in contract
    assert prompt[1]["content"][0]["media_relpath"] == sample.media_relpath
    assert adapter.load_split(G4_SCREEN_SPLIT_ID) == tuple(
        sorted(samples, key=lambda item: item.sample_id)
    )
    assert adapter.score(sample, "[]") == {"scoring_deferred": True}
    assert adapter.extract_consumption(sample, None, "[]").records == ()


def test_adapter_rejects_incomplete_leaky_non_ascii_or_oversize_surfaces() -> None:
    samples = _samples()
    states, packets = _maps(samples)
    first = samples[0].sample_id

    with pytest.raises(G4MicrogroundFlightError, match="exactly 16"):
        G4MicrogroundAdapter(
            samples[:-1],
            phase=G4_MICROGROUND_E_PHASE,
            state_by_sample={
                key: value for key, value in states.items() if key != first
            },
            packet_by_sample={
                key: value for key, value in packets.items() if key != first
            },
        )
    with pytest.raises(G4MicrogroundFlightError, match="unknown G4 phase"):
        G4MicrogroundAdapter(
            samples,
            phase="unknown",
            state_by_sample=states,
            packet_by_sample=packets,
        )
    with pytest.raises(G4MicrogroundFlightError, match="one state and packet"):
        G4MicrogroundAdapter(
            samples,
            phase=G4_MICROGROUND_E_PHASE,
            state_by_sample={
                key: value for key, value in states.items() if key != first
            },
            packet_by_sample=packets,
        )
    with pytest.raises(G4MicrogroundFlightError, match="ASCII English"):
        G4MicrogroundAdapter(
            samples,
            phase=G4_MICROGROUND_E_PHASE,
            state_by_sample={**states, first: "caf\u00e9"},
            packet_by_sample=packets,
        )
    with pytest.raises(G4MicrogroundFlightError, match="state byte cap"):
        G4MicrogroundAdapter(
            samples,
            phase=G4_MICROGROUND_E_PHASE,
            state_by_sample={**states, first: "x" * 4097},
            packet_by_sample=packets,
        )
    se_adapter = G4MicrogroundAdapter(
        samples,
        phase=G4_MICROGROUND_SE_PHASE,
        state_by_sample={**states, first: "x" * (G4_STATE_UTF8_BYTE_CAP + 1)},
        packet_by_sample=packets,
    )
    assert len(se_adapter._states[first]) == G4_STATE_UTF8_BYTE_CAP + 1
    with pytest.raises(G4MicrogroundFlightError, match="state byte cap"):
        G4MicrogroundAdapter(
            samples,
            phase=G4_MICROGROUND_SE_PHASE,
            state_by_sample={**states, first: "x" * (G4_SE_STATE_UTF8_BYTE_CAP + 1)},
            packet_by_sample=packets,
        )
    with pytest.raises(G4MicrogroundFlightError, match="packet byte cap"):
        G4MicrogroundAdapter(
            samples,
            phase=G4_MICROGROUND_E_PHASE,
            state_by_sample=states,
            packet_by_sample={**packets, first: "x" * 16385},
        )


def test_adapter_rejects_second_supply_wrong_split_and_forbidden_runtime_labels() -> (
    None
):
    samples = _samples()
    states, packets = _maps(samples)
    adapter = G4MicrogroundAdapter(
        samples,
        phase=G4_MICROGROUND_E_PHASE,
        state_by_sample=states,
        packet_by_sample=packets,
    )

    with pytest.raises(G4MicrogroundFlightError, match="serves only"):
        adapter.load_split("wrong")
    with pytest.raises(G4MicrogroundFlightError, match="second supply"):
        adapter.assemble_prompt(samples[0], object())
    for forbidden in ("gold_tool", "expected_calls", "tier_hint", "sample_id"):
        with pytest.raises(G4MicrogroundFlightError, match="forbidden runtime field"):
            G4MicrogroundAdapter(
                samples,
                phase=G4_MICROGROUND_E_PHASE,
                state_by_sample={
                    **states,
                    samples[0].sample_id: f"{forbidden}: secret",
                },
                packet_by_sample=packets,
            )


def test_single_contact_controller_never_repairs_or_appends_history() -> None:
    controller = G4SingleContactController()
    context = SimpleNamespace(
        query_state=SimpleNamespace(loop_step=0, content_hash=lambda: "a" * 64),
        knowledge_snapshot_sha256="b" * 64,
    )

    contact = controller.initial_contact(context)
    advance = controller.advance(context, contact, "[]")

    assert contact.decoding_params == {"max_tokens": 1024, "temperature": 0}
    assert advance.next_contact is None
    assert advance.final_response_contact_id == contact.contact_id


def test_runner_binds_openjiuwen_two_slots_one_contact_and_exact_id_surface(
    tmp_path: Path,
) -> None:
    samples = _samples()
    states, packets = _maps(samples)
    adapter = G4MicrogroundAdapter(
        samples,
        phase=G4_MICROGROUND_E_PHASE,
        state_by_sample=states,
        packet_by_sample=packets,
    )
    bindings = {sample.sample_id: {"packet_id": sample.sample_id} for sample in samples}
    calls: list[dict[str, object]] = []

    def agent_runner(**kwargs):
        calls.append(kwargs)
        factory = kwargs["controller_registry"].resolve(kwargs["controller_policy_id"])
        assert isinstance(factory(samples[0].sample_id), G4SingleContactController)
        return _summary(samples)

    summary = run_g4_microground_phase(
        data_root=tmp_path,
        plan=object(),
        adapter=adapter,
        core_client=object(),
        knowledge_snapshot=object(),
        speech_packet_bindings=bindings,
        trace_sink=object(),
        agent_runner=agent_runner,
    )

    assert len(summary.results) == 16
    assert calls[0]["split_id"] == G4_SCREEN_SPLIT_ID
    assert calls[0]["agent_executor_id"] == "openjiuwen-workflow-v1"
    assert calls[0]["max_contacts"] == 1
    assert calls[0]["slot_count"] == 2
    assert calls[0]["queue_depth"] == 4
    assert calls[0]["bootstrap_facet_ids"] == ()
    assert calls[0]["bootstrap_value_ids"] == ()


def test_runner_rejects_contact_or_identity_drift(tmp_path: Path) -> None:
    samples = _samples()
    states, packets = _maps(samples)
    adapter = G4MicrogroundAdapter(
        samples,
        phase=G4_MICROGROUND_E_PHASE,
        state_by_sample=states,
        packet_by_sample=packets,
    )
    bindings = {sample.sample_id: {"packet_id": sample.sample_id} for sample in samples}

    with pytest.raises(G4MicrogroundFlightError, match="exactly one contact"):
        run_g4_microground_phase(
            data_root=tmp_path,
            plan=object(),
            adapter=adapter,
            core_client=object(),
            knowledge_snapshot=object(),
            speech_packet_bindings=bindings,
            trace_sink=object(),
            agent_runner=lambda **_kwargs: _summary(samples, contacts=2),
        )
    with pytest.raises(G4MicrogroundFlightError, match="identity surface"):
        run_g4_microground_phase(
            data_root=tmp_path,
            plan=object(),
            adapter=adapter,
            core_client=object(),
            knowledge_snapshot=object(),
            speech_packet_bindings=bindings,
            trace_sink=object(),
            agent_runner=lambda **_kwargs: _summary(samples[:-1]),
        )
