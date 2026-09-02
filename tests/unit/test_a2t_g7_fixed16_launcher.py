"""Contact-free tests for the G7 fixed16 launcher."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-g7-exhaustive-example-ground-fixed16-v1/launcher/"
    "launch_a2t_g7_fixed16.py"
)
SPEC = importlib.util.spec_from_file_location("g7_launcher", LAUNCHER)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def test_openjiuwen_runtime_version_is_frozen_to_installed_receipt() -> None:
    assert module.OPENJIUWEN_VERSION == "0.1.16.post2"


def _ground():
    bundles = []
    for family in range(28):
        tools = tuple(
            SimpleNamespace(
                tool_name=f"t_{family}_{index}",
                operation="Operate.",
                types=(),
                legal_key_skeletons=((),),
                patterns=(),
            )
            for index in range(6 if family < 12 else 5)
        )
        bundles.append(
            SimpleNamespace(
                family_tag=f"f-{family}",
                family_label=f"F {family}",
                tools=tools,
                tool_names=tuple(tool.tool_name for tool in tools),
                text=f"Family {family} examples.",
                sha256=f"{family:064x}",
                ascii_bytes=24,
            )
        )
    return SimpleNamespace(
        bundles=tuple(bundles),
        bundles_by_family={bundle.family_tag: bundle for bundle in bundles},
        tool_names=tuple(name for bundle in bundles for name in bundle.tool_names),
        sha256=module.GROUND_SHA256,
        receipt={"schema": "saea-a2t-construction-example-ground-receipt-v1"},
    )


def test_preflight_binds_identity_builder_and_exact_protocol() -> None:
    report = module.preflight_ground(_ground(), speech_feature_tokens_max=100)

    assert report["split_identity_hash"] == (
        "94a10c359dfe9e6a96cd63940c4dcb52fc7206e4c0e7d855733b21b69b987212"
    )
    assert report["contacts"] == 480
    assert report["family_count"] == 28
    assert report["tool_count"] == 152
    assert report["slots"] == report["max_concurrent_model_requests"] == 2
    assert report["queue_depth"] == 4
    assert report["audio_contacts_per_sample"] == 2
    assert report["builder_commit"] == "7046ce6e7fbbba67ddbae5f122748e2158761e23"


def test_committed_structured_ground_round_trips_without_construction_rows() -> None:
    ground = module.load_ground()

    assert ground.sha256 == module.GROUND_SHA256
    assert len(ground.bundles) == 28
    assert len(ground.tool_names) == 152


def test_byte_upper_bound_preflight_measures_all_static_prompts() -> None:
    report = module.preflight_ground(_ground(), speech_feature_tokens_max=100)

    assert report["token_counter"] == "utf8-byte-construction-upper-bound"
    assert report["worst_observation_ascii_bytes"] == 1_024
    assert report["obs_prompt"]["completion_tokens"] == 512
    assert len(report["evidence_prompts"]) == 28
    assert all(row["remaining_tokens"] >= 8192 for row in report["evidence_prompts"])
    assert report["resolve_empty_assessment_base_prompt"]["remaining_tokens"] >= 8192
    assert report["resolve_worst_normalized_assessment_prompt"]["remaining_tokens"] >= 8192
    assert report["resolve_measurement"] == "dynamic-after-152-assessments-seal"


def test_committed_ground_worst_case_uses_full_observation_and_keeps_headroom() -> None:
    report = module.preflight_ground(module.load_ground(), speech_feature_tokens_max=182)

    assert report["worst_observation_ascii_bytes"] == 1_024
    assert max(row["total_tokens"] for row in report["evidence_prompts"]) == 12_534
    assert report["resolve_worst_normalized_assessment_prompt"] == {
        "completion_tokens": 1_024,
        "contact_id": "g7-resolve",
        "prompt_tokens": 23_070,
        "remaining_tokens": 8_674,
        "total_tokens": 24_094,
    }


def test_execution_plan_binds_exact_population_and_budget() -> None:
    plan = module.execution_plan("attempt-g7-unit")

    assert plan.split_identity_hash == module.SPLIT_IDENTITY_HASH
    assert plan.protocol_hash == module.PROTOCOL_SHA256
    assert plan.planned_model_calls == 480
    assert plan.planned_speech_audio_seconds == 2769


def test_exact_evidence_render_names_schema_once_and_resolve_is_official_array() -> None:
    ground = _ground()
    core = module.G7ExampleGround(ground.bundles)
    observation = module.parse_observation("A device action is requested.", core.tool_names)
    context = core.build_evidence_contexts(observation)[0]
    state = SimpleNamespace(
        stage="EVIDENCE", packet_binding={"packet_id": "p", "sha256": "a" * 64}
    )
    messages = module._contact_messages(state, context)

    assert "assessments" in messages[0]["content"]
    assert "tool_name" in messages[0]["content"]
    assert messages[0]["content"] not in str(messages[1])
    assert '"agent_control"' not in module._exact_request(
        messages, context, with_control=False
    )


def test_openjiuwen_phase_has_32_audio_and_448_text_only_contacts() -> None:
    ids = tuple(f"sample-{index}" for index in range(16))
    surface = module.RuntimeSurface(
        samples=tuple(SimpleNamespace(sample_id=value) for value in ids),
        packet_bindings={value: {"packet_id": value, "sha256": "b" * 64} for value in ids},
        speech_feature_tokens_by_sample={value: 10 for value in ids},
    )

    class Client:
        def __init__(self) -> None:
            self.calls = []

        def complete(self, _messages, **kwargs):
            self.calls.append(kwargs)
            if kwargs.get("agent_contact_id") == "g7-obs":
                return "The speaker requests a device action."
            if kwargs.get("text_only_sample_id"):
                return "{}"
            return '{"calls":[]}'

    class Sink:
        def __init__(self) -> None:
            self.rows = []

        def emit(self, *args):
            self.rows.append(args)

    def runner(states, **kwargs):
        for state in states:
            while kwargs["should_continue"](state):
                count = kwargs["prepare_wave"](state, object())
                responses = tuple(
                    kwargs["invoke_contact"](state, index, 0) for index in range(count)
                )
                kwargs["aggregate_wave"](state, responses, object())
        return states

    client = Client()
    sink = Sink()
    summary = module.run_openjiuwen_phase(
        surface=surface,
        ground=_ground(),
        client=client,
        trace_sink=sink,
        workflow_runner=runner,
    )

    assert len(summary.results) == 16
    assert sum("speech_feature_sample_id" in call for call in client.calls) == 32
    assert sum("text_only_sample_id" in call for call in client.calls) == 448
    assert len(client.calls) == 480
    assert len(sink.rows) == 64


def test_recovery_reuses_bound_response_without_recontact() -> None:
    ground = _ground()
    sample_id = "sample-0"
    surface = module.RuntimeSurface(
        samples=(SimpleNamespace(sample_id=sample_id),),
        packet_bindings={sample_id: {"packet_id": sample_id, "sha256": "b" * 64}},
        speech_feature_tokens_by_sample={sample_id: 10},
    )
    obs_context = SimpleNamespace(contact_id="g7-obs", instruction=module._render_obs())
    state = SimpleNamespace(
        stage="OBS", packet_binding=surface.packet_bindings[sample_id]
    )
    messages = module._contact_messages(state, obs_context)
    recovered_text = "The speaker requests a device action."
    source = module.RecoveryContact(
        request_id="old-1",
        sample_id=sample_id,
        contact_id="g7-obs",
        semantic_sha256=module._message_semantic_sha256(
            sample_id, obs_context, messages
        ),
        response_text=recovered_text,
        response_sha256=module.hashlib.sha256(recovered_text.encode()).hexdigest(),
        slot_id=0,
        cost={},
    )
    recovery = module.RecoveryBundle(
        trace_path=Path("old.jsonl"),
        trace_sha256="c" * 64,
        contacts={(sample_id, "g7-obs"): source},
        cost={},
    )

    class Client:
        def __init__(self) -> None:
            self.count = 0

        def complete(self, _messages, **_kwargs):
            self.count += 1
            return "{}" if self.count <= 28 else '{"calls":[]}'

    class Sink:
        def emit(self, *_args):
            return None

    def runner(states, **kwargs):
        for current in states:
            while kwargs["should_continue"](current):
                count = kwargs["prepare_wave"](current, object())
                responses = tuple(
                    kwargs["invoke_contact"](current, index, 0)
                    for index in range(count)
                )
                kwargs["aggregate_wave"](current, responses, object())
        return states

    client = Client()
    with pytest.raises(RuntimeError, match="exactly 480"):
        module.run_openjiuwen_phase(
            surface=surface,
            ground=ground,
            client=client,
            trace_sink=Sink(),
            workflow_runner=runner,
            recovery=recovery,
        )

    assert client.count == 29
