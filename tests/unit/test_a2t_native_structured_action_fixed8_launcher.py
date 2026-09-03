"""Contact-free tests for the native structured-action fixed-eight launcher."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


REPO = Path(__file__).resolve().parents[2]
LAUNCHER = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-03-a2t-native-structured-action-fixed8-v1/launcher/"
    "launch_native_structured_action_fixed8.py"
)


def _launcher():
    name = "test_a2t_native_structured_action_fixed8_launcher_module"
    spec = importlib.util.spec_from_file_location(name, LAUNCHER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _roster() -> dict[str, object]:
    return {
        "schema": "saea-a2t-native-schema-roster-v1",
        "split_name": "A2T-NATIVE-STRUCTURED-ACTION-FIXED8",
        "split_role": "discovery",
        "split_identity_hash": (
            "f95efe70b615d71bb082f9ef804d1fa2b6f04ce4114d5d2694151cbaf44019ba"
        ),
        "count": 8,
        "audio_seconds_total": 45.096,
        "source": {
            "count": 104,
            "sha256": (
                "eeb90abbe8695e449c676f18339db6618cb6d606d6c1e7c656626e4e9b6b6c16"
            ),
            "split_identity_hash": (
                "c6bb080bb264733087b3da352fe930702ec6509bc02e6a639b0f4c30c5017dac"
            ),
        },
        "items": [
            {
                "sample_id": f"tier{index}_kind:{index:06d}",
                "tier": f"tier{index}_kind",
                "packet_id": f"tier{index}_kind/{index:06d}",
                "audio_sha256": f"{index:x}" * 64,
                "media_relpath": f"datasets/audio2tool/tier{index}/{index}.wav",
                "audio_seconds": 45.096 / 8,
                "query_block": f"tier{index}_kind:query-{index:05d}",
            }
            for index in range(1, 9)
        ],
    }


def _schema() -> dict[str, object]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "audio2tool_calls",
            "strict": True,
            "schema": {"type": "array", "items": {"oneOf": []}},
        },
    }


def _source_request_bindings(
    launcher: object,
    sample_ids: tuple[str, ...],
    packet_bindings: dict[str, dict[str, str]],
) -> dict[str, dict[str, dict[str, object]]]:
    return {
        arm: {
            sample_id: {
                "sample_id": sample_id,
                "id_slot": index % 2,
                "source_request_id": f"source-{arm.lower()}-{index:04d}",
                "source_payload_sha256": f"{index + arm_index + 1:x}"[-1] * 64,
                "speech_packet_sha256": packet_bindings[sample_id]["sha256"],
            }
            for index, sample_id in enumerate(sample_ids)
        }
        for arm_index, arm in enumerate(launcher.ARM_ORDER)
    }


@dataclass(frozen=True)
class _Sample:
    sample_id: str


class _Adapter:
    def __init__(self, sample_ids: tuple[str, ...], instruction: str) -> None:
        self._samples = tuple(_Sample(sample_id) for sample_id in sample_ids)
        self._instruction = instruction

    def load_split(self, split_id: str):
        assert split_id == "A2T-GROUND-QUAL-104"
        return self._samples

    def assemble_prompt(self, sample: _Sample, supply: object):
        assert supply is None
        return (
            {"role": "system", "content": self._instruction},
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_audio",
                        "media_relpath": f"audio/{sample.sample_id}.wav",
                    }
                ],
            },
        )


class _Core:
    def __init__(self, events: list[tuple[str, str]]) -> None:
        self.events = events
        self.calls: list[tuple[object, dict[str, object]]] = []

    def complete(self, messages: object, **kwargs: object) -> str:
        sample_id = str(kwargs["speech_feature_sample_id"])
        self.events.append(("send", sample_id))
        self.calls.append((messages, kwargs))
        return "[]"


def test_contract_binds_two_ordered_arms_and_exact_total_budget() -> None:
    launcher = _launcher()
    plan = launcher.execution_plan("attempt-fixed8-test")

    assert launcher.RUN_ID == "SAEA-A2T-NATIVE-STRUCTURED-ACTION-FIXED8-V1"
    assert launcher.ARM_ORDER == (
        "REGISTRY_STRICT_ACTION",
        "HANDBOOK_STRICT_ACTION",
    )
    assert launcher.SAMPLE_COUNT == 8
    assert launcher.BATCH_SIZE == launcher.CONCURRENCY == 2
    assert launcher.QUEUE_DEPTH == 4
    assert launcher.EXPECTED_MODEL_CONTACTS == launcher.MAX_MODEL_CONTACTS == 16
    assert launcher.EXACT_AUDIO_SECONDS == 90.192
    assert launcher.PLANNED_AUDIO_SECONDS == 91
    assert plan.split_role == "discovery"
    assert plan.split_identity_hash == launcher.SPLIT_IDENTITY_HASH
    assert plan.planned_model_calls == 16
    assert plan.planned_speech_audio_seconds == 91
    assert plan.planned_gpu_hours == 0.2
    assert plan.protocol_hash == launcher.PROTOCOL_SHA256
    assert launcher.SPECIAL_TOKEN_RESERVE == 512


def test_roster_requires_one_unique_row_per_tier_and_exact_identity() -> None:
    launcher = _launcher()
    roster = _roster()

    validated = launcher.validate_roster(roster)

    assert len(validated["sample_ids"]) == 8
    assert validated["audio_seconds_total"] == pytest.approx(45.096)
    drifted = json.loads(json.dumps(roster))
    drifted["items"][1]["tier"] = drifted["items"][0]["tier"]
    with pytest.raises(RuntimeError, match="one row per tier"):
        launcher.validate_roster(drifted)


def test_governed_hash_rejects_any_byte_drift(tmp_path: Path) -> None:
    launcher = _launcher()
    artifact = tmp_path / "artifact.json"
    artifact.write_bytes(b"fixed")
    expected = launcher.sha256_file(artifact)

    launcher.require_file_hash(artifact, expected, "artifact")
    artifact.write_bytes(b"drifted")

    with pytest.raises(RuntimeError, match="artifact SHA-256 drift"):
        launcher.require_file_hash(artifact, expected, "artifact")


def test_registered_flight_plan_freezes_both_exact_execution_plans(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = _launcher()
    registered_path = launcher.REPO / launcher.REGISTERED_PLAN_RELPATH

    registered = launcher.load_registered_flight_plan(registered_path)

    assert registered["flight_id"] == "flight-20260903T013000Z"
    assert tuple(registered["arm_order"]) == launcher.ARM_ORDER
    assert {
        arm: registered["validated_plans"][arm].attempt_id for arm in launcher.ARM_ORDER
    } == launcher.ATTEMPT_IDS
    assert all(
        registered["validated_plans"][arm].planned_gpu_hours == 0.2
        for arm in launcher.ARM_ORDER
    )

    copied = tmp_path / registered_path.name
    copied.write_bytes(registered_path.read_bytes())
    with pytest.raises(RuntimeError, match="not the frozen input"):
        launcher.load_registered_flight_plan(copied)

    monkeypatch.setattr(launcher, "REGISTERED_PLAN_SHA256", "0" * 64)
    with pytest.raises(RuntimeError, match="registered flight plan SHA-256 drift"):
        launcher.load_registered_flight_plan(registered_path)


def test_preexisting_attempt_record_closes_the_registered_flight(
    tmp_path: Path,
) -> None:
    launcher = _launcher()
    attempt_root = tmp_path / "attempts" / launcher.RUN_ID
    attempt_root.mkdir(parents=True)
    launcher.assert_run_has_no_attempt_records(tmp_path)

    (attempt_root / "prior.json").write_text("{}", encoding="ascii")
    with pytest.raises(RuntimeError, match="already has an attempt record"):
        launcher.assert_run_has_no_attempt_records(tmp_path)


def test_parent_request_receipt_binds_arm_specific_source_slots_and_packets() -> None:
    launcher = _launcher()
    document = json.loads(
        (launcher.REPO / launcher.PARENT_REQUESTS_RELPATH).read_text(encoding="utf-8")
    )
    sample_ids = tuple(
        sorted(row["sample_id"] for row in document["requests"][launcher.ARM_ORDER[0]])
    )
    packet_bindings = {
        row["sample_id"]: {
            "packet_id": f"packet/{index}",
            "sha256": row["speech_packet_sha256"],
        }
        for index, row in enumerate(document["requests"][launcher.ARM_ORDER[0]])
    }

    validated = launcher.validate_parent_request_bindings(
        document,
        sample_ids=sample_ids,
        packet_bindings=packet_bindings,
    )

    assert tuple(validated) == launcher.ARM_ORDER
    assert all(len(validated[arm]) == 8 for arm in launcher.ARM_ORDER)
    assert any(
        validated[launcher.ARM_ORDER[0]][sample_id]["id_slot"]
        != validated[launcher.ARM_ORDER[1]][sample_id]["id_slot"]
        for sample_id in sample_ids
    )


def test_precontact_plan_hashes_all_sixteen_requests_and_preserves_schema_object() -> (
    None
):
    launcher = _launcher()
    sample_ids = tuple(f"sample-{index}" for index in range(8))
    schema = _schema()
    bindings = {
        sample_id: {"packet_id": f"packet/{index}", "sha256": f"{index:x}" * 64}
        for index, sample_id in enumerate(sample_ids, start=1)
    }
    packet_tokens = {
        sample_id: 100 + index for index, sample_id in enumerate(sample_ids)
    }

    plan = launcher.build_precontact_plan(
        adapters={
            launcher.ARM_ORDER[0]: _Adapter(sample_ids, "registry"),
            launcher.ARM_ORDER[1]: _Adapter(sample_ids, "handbook"),
        },
        packet_bindings=bindings,
        packet_tokens=packet_tokens,
        response_format=schema,
        text_prompt_tokens={
            launcher.ARM_ORDER[0]: 13_236,
            launcher.ARM_ORDER[1]: 12_557,
        },
        source_request_bindings=_source_request_bindings(
            launcher, sample_ids, bindings
        ),
    )

    assert [arm["arm"] for arm in plan["arms"]] == list(launcher.ARM_ORDER)
    rows = [row for arm in plan["arms"] for row in arm["requests"]]
    assert len(rows) == 16
    assert len({row["request_sha256"] for row in rows}) == 16
    assert all(
        row["response_format_sha256"] == launcher.canonical_sha256(schema)
        for row in rows
    )
    assert [row["id_slot"] for row in plan["arms"][0]["requests"]] == [0, 1] * 4
    assert max(row["total_tokens"] for row in rows) <= 24_576
    assert min(row["remaining_tokens"] for row in rows) >= 8_192
    assert plan["response_format"] is schema


def test_guard_measures_immediately_before_each_send_and_forwards_schema_unchanged() -> (
    None
):
    launcher = _launcher()
    events: list[tuple[str, str]] = []
    core = _Core(events)
    schema = _schema()
    guarded = launcher.PromptGuardedCoreClient(
        core,
        arm=launcher.ARM_ORDER[0],
        response_format=schema,
        packet_tokens={"sample-a": 123},
        text_prompt_tokens=13_236,
        expected_request_hashes={},
        record=lambda row: events.append(("measure", str(row["sample_id"]))),
    )
    messages = (
        {"role": "system", "content": "registry"},
        {
            "role": "user",
            "content": [
                {
                    "type": "input_speech_features",
                    "speech_features": {
                        "packet_id": "packet/a",
                        "sha256": "a" * 64,
                        "role": "query",
                    },
                }
            ],
        },
    )
    decoding = {
        "temperature": 0,
        "seed": 20260803,
        "max_tokens": 1024,
        "id_slot": 0,
        "response_format": schema,
    }
    expected = launcher.request_measurement(
        arm=launcher.ARM_ORDER[0],
        sample_id="sample-a",
        messages=messages,
        decoding_params=decoding,
        packet_tokens=123,
        text_prompt_tokens=13_236,
    )
    guarded.expected_request_hashes["sample-a"] = expected["request_sha256"]

    assert (
        guarded.complete(
            messages,
            decoding_params=decoding,
            speech_feature_sample_id="sample-a",
            key_representation_id=launcher.KEY_REPRESENTATION_IDS[
                launcher.ARM_ORDER[0]
            ],
            matcher_policy_id=launcher.MATCHER_POLICY_IDS[launcher.ARM_ORDER[0]],
        )
        == "[]"
    )

    assert events == [("measure", "sample-a"), ("send", "sample-a")]
    forwarded = core.calls[0][1]["decoding_params"]
    assert forwarded["response_format"] is schema


def test_prompt_guard_refuses_before_send_when_headroom_is_too_small() -> None:
    launcher = _launcher()
    events: list[tuple[str, str]] = []
    core = _Core(events)
    schema = _schema()
    guarded = launcher.PromptGuardedCoreClient(
        core,
        arm=launcher.ARM_ORDER[0],
        response_format=schema,
        packet_tokens={"sample-a": 1},
        text_prompt_tokens=23_550,
        expected_request_hashes={},
        record=lambda row: events.append(("measure", str(row["sample_id"]))),
    )
    messages = (
        {"role": "system", "content": "registry"},
        {
            "role": "user",
            "content": [
                {
                    "type": "input_speech_features",
                    "speech_features": {
                        "packet_id": "packet/a",
                        "sha256": "a" * 64,
                        "role": "query",
                    },
                }
            ],
        },
    )
    with pytest.raises(RuntimeError, match="8192 tokens"):
        guarded.complete(
            messages,
            decoding_params={
                "temperature": 0,
                "seed": 20260803,
                "max_tokens": 1024,
                "id_slot": 0,
                "response_format": schema,
            },
            speech_feature_sample_id="sample-a",
            key_representation_id=launcher.KEY_REPRESENTATION_IDS[
                launcher.ARM_ORDER[0]
            ],
            matcher_policy_id=launcher.MATCHER_POLICY_IDS[launcher.ARM_ORDER[0]],
        )
    assert events == []
    assert core.calls == []


def test_only_response_format_factor_allows_accounting_identity_changes() -> None:
    launcher = _launcher()
    schema = _schema()
    parent = {
        "sample-a": {
            "request_id": "historical-1",
            "sample_id": "sample-a",
            "task_instruction": "registry",
            "decoding_params": {
                "temperature": 0,
                "seed": 20260803,
                "max_tokens": 1024,
                "id_slot": 0,
            },
            "speech_feature_parts": [
                {"packet_id": "packet/a", "sha256": "a" * 64, "role": "query"}
            ],
        }
    }
    strict = json.loads(json.dumps(parent))
    strict["sample-a"]["request_id"] = "strict-1"
    strict["sample-a"]["decoding_params"]["response_format"] = schema

    launcher.assert_only_response_format_factor(parent, strict, schema)

    strict["sample-a"]["task_instruction"] = "changed"
    with pytest.raises(RuntimeError, match="only response_format"):
        launcher.assert_only_response_format_factor(parent, strict, schema)


def test_two_arm_runner_batches_two_without_retry_and_keeps_arm_order() -> None:
    launcher = _launcher()
    sample_ids = tuple(f"sample-{index}" for index in range(8))
    events: list[tuple[str, tuple[str, ...]]] = []

    def phase_runner(*, arm: str, sample_batch: tuple[str, ...]):
        events.append((arm, sample_batch))
        return tuple(
            SimpleNamespace(sample_id=value, final_response_text="[]")
            for value in sample_batch
        )

    result = launcher.run_two_arms_batched(sample_ids, phase_runner=phase_runner)

    assert [arm for arm, _batch in events] == [launcher.ARM_ORDER[0]] * 4 + [
        launcher.ARM_ORDER[1]
    ] * 4
    assert all(len(batch) == 2 for _arm, batch in events)
    assert {arm: len(rows) for arm, rows in result.items()} == {
        launcher.ARM_ORDER[0]: 8,
        launcher.ARM_ORDER[1]: 8,
    }

    failing_events: list[tuple[str, tuple[str, ...]]] = []

    def fail_once(*, arm: str, sample_batch: tuple[str, ...]):
        failing_events.append((arm, sample_batch))
        raise RuntimeError("terminal failure")

    with pytest.raises(RuntimeError, match="terminal failure"):
        launcher.run_two_arms_batched(sample_ids, phase_runner=fail_once)
    assert len(failing_events) == 1


def test_launcher_has_no_gold_scorer_or_retry_surface() -> None:
    source = LAUNCHER.read_text(encoding="utf-8")

    assert "load_expected_calls" not in source
    assert "score_item" not in source
    assert "evaluate_parallel" not in source
    assert "retry" not in source.lower()
    assert "requests.get" not in source
    assert "requests.post" not in source


def test_preflight_only_never_enters_contact_path(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    launcher = _launcher()
    sentinel = {
        "commit": "a" * 40,
        "sample_ids": tuple(f"sample-{index}" for index in range(8)),
        "precontact_plan_sha256": "b" * 64,
        "execution_plan_sha256": "c" * 64,
    }
    monkeypatch.setattr(launcher, "data_root", lambda: Path("/fixed/data"))
    monkeypatch.setattr(
        launcher, "static_preflight", lambda root, registered_plan_path=None: sentinel
    )

    def forbidden_launch(root: Path):
        raise AssertionError(f"contact path entered for {root}")

    monkeypatch.setattr(launcher, "launch", forbidden_launch)
    assert launcher.main(["--preflight-only"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["contacts"] == {
        "gold": 0,
        "model": 0,
        "network": 0,
        "scorer": 0,
        "tokenizer": 0,
    }
    assert result["arms"] == list(launcher.ARM_ORDER)
    assert result["samples"] == 8


def test_static_preflight_builds_real_sixteen_request_plan_without_contacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = _launcher()
    roster = _roster()
    schema = _schema()
    schema_path = tmp_path / launcher.SCHEMA_RELPATH
    schema_path.parent.mkdir(parents=True)
    schema_path.write_bytes(b"x" * launcher.SCHEMA_BYTES)
    handbook_path = tmp_path / launcher.HANDBOOK_RELPATH
    handbook_path.parent.mkdir(parents=True)
    handbook_path.write_text("handbook", encoding="ascii")
    carrier_root = tmp_path / "datasets" / "audio2tool"
    carrier_root.mkdir(parents=True)
    sample_ids = tuple(sorted(row["sample_id"] for row in roster["items"]))
    bindings = {
        sample_id: {"packet_id": f"packet/{index}", "sha256": f"{index:x}" * 64}
        for index, sample_id in enumerate(sample_ids, start=1)
    }
    packet_tokens = {sample_id: 100 for sample_id in sample_ids}
    source_bindings = _source_request_bindings(launcher, sample_ids, bindings)
    values = {
        "profile_slot_count": 2,
        "profile_queue_depth_multiplier": 2,
        "obs_batch_samples": 2,
        "max_concurrent_model_requests": 2,
        "queue_depth": 4,
        "per_slot_context_tokens": 32_768,
        "prompt_plus_completion_cap_per_slot": 24_576,
        "operational_headroom_token_minimum": 8_192,
        "special_token_reserve": 512,
        "repair_contacts": 0,
        "retries": 0,
        "resends": 0,
        "network_jitter_testing": False,
        "speech_native_contact_ceiling_per_task": 1,
        "contact_budget": {
            "sample_count": 8,
            "new_model_calls": 16,
            "planned_model_calls": 16,
            "exact_speech_audio_seconds": 90.192,
            "planned_speech_audio_seconds": 91,
            "planned_gpu_hours": 0.2,
            "tokenizer_contacts": 0,
        },
        "execution_protocol": {
            "new_cell_order": list(launcher.ARM_ORDER),
            "batch_slots": 2,
            "max_concurrent_model_requests": 2,
            "queue_depth": 4,
            "expected_and_maximum_new_calls": 16,
        },
        "decoding_params": {
            "temperature": 0,
            "seed": 20260803,
            "max_tokens": 1024,
            "id_slot": "per-sample",
        },
    }
    composed = SimpleNamespace(
        config_hash=launcher.COMPOSED_CONFIG_SHA256,
        values=values,
    )

    monkeypatch.setattr(launcher, "require_clean_study_repo", lambda repo: "a" * 40)
    monkeypatch.setattr(
        launcher,
        "load_registered_flight_plan",
        lambda path: {
            "flight_id": "flight-20260903T013000Z",
            "validated_plans": {
                arm: launcher.execution_plan(launcher.ATTEMPT_IDS[arm])
                for arm in launcher.ARM_ORDER
            },
        },
    )
    monkeypatch.setattr(launcher, "compose", lambda *args: composed)
    monkeypatch.setattr(launcher, "require_file_hash", lambda *args: None)
    monkeypatch.setattr(launcher, "load_lock", lambda path: {})
    monkeypatch.setattr(launcher, "umbrella_lock_path", lambda repo: tmp_path / "lock")
    monkeypatch.setattr(launcher, "asset_dir", lambda lock, key, root: carrier_root)
    monkeypatch.setattr(
        launcher, "load_runtime_receipt", lambda path: {"runtime": "receipt"}
    )
    monkeypatch.setattr(launcher, "_validate_runtime_receipt", lambda document: None)
    monkeypatch.setattr(
        launcher, "_validate_prompt_token_evidence", lambda registry, handbook: None
    )
    monkeypatch.setattr(
        launcher, "_validate_rendered_text_surfaces", lambda adapters: None
    )
    monkeypatch.setattr(
        launcher,
        "_load_packet_surface",
        lambda roster, promotion: (bindings, packet_tokens),
    )
    monkeypatch.setattr(
        launcher,
        "validate_parent_request_bindings",
        lambda document, **kwargs: source_bindings,
    )

    def read_json(path: Path):
        if path == launcher.REPO / launcher.ROSTER_RELPATH:
            return roster
        if path == schema_path:
            return schema
        if path == launcher.PROMOTION_RECEIPT:
            return {"count": 104, "packets": []}
        return {"schema": "runtime"}

    monkeypatch.setattr(launcher, "_read_json", read_json)

    def adapter_factory(lock, root, *, repo_root, receipt_items, mode, handbook):
        del lock, root, repo_root, receipt_items, handbook
        instruction = (
            "registry" if mode == launcher.ground_flight.REGISTRY_DIRECT else "handbook"
        )
        return _Adapter(sample_ids, instruction)

    monkeypatch.setattr(
        launcher.ground_flight, "GroundQualificationAdapter", adapter_factory
    )

    context = launcher.static_preflight(tmp_path)

    assert context["sample_ids"] == sample_ids
    assert len(context["precontact_plan"]["arms"]) == 2
    assert sum(len(arm["requests"]) for arm in context["precontact_plan"]["arms"]) == 16
    assert context["execution_plan_sha256"] == {
        arm: launcher.canonical_sha256(
            asdict(launcher.execution_plan(launcher.ATTEMPT_IDS[arm]))
        )
        for arm in launcher.ARM_ORDER
    }


def test_run_arm_uses_four_fixed_batches_and_seals_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = _launcher()
    sample_ids = tuple(f"sample-{index}" for index in range(8))
    adapter = _Adapter(sample_ids, "registry")
    schema = _schema()
    bindings = {
        sample_id: {"packet_id": f"packet/{index}", "sha256": f"{index + 1:x}" * 64}
        for index, sample_id in enumerate(sample_ids)
    }
    packet_tokens = {sample_id: 100 for sample_id in sample_ids}
    precontact = launcher.build_precontact_plan(
        adapters={
            launcher.ARM_ORDER[0]: adapter,
            launcher.ARM_ORDER[1]: _Adapter(sample_ids, "handbook"),
        },
        packet_bindings=bindings,
        packet_tokens=packet_tokens,
        response_format=schema,
        text_prompt_tokens=launcher.TEXT_PROMPT_TOKENS,
        source_request_bindings=_source_request_bindings(
            launcher, sample_ids, bindings
        ),
    )
    context = {
        "adapters": {launcher.ARM_ORDER[0]: adapter},
        "carrier_root": tmp_path,
        "packet_bindings": bindings,
        "packet_tokens": packet_tokens,
        "precontact_plan": precontact,
        "response_format": schema,
        "sample_ids": sample_ids,
        "source_request_bindings": _source_request_bindings(
            launcher, sample_ids, bindings
        ),
    }
    sent: list[str] = []
    observed_slots: list[tuple[str, int]] = []

    class Core:
        def __init__(self, **kwargs):
            del kwargs

        def complete(self, messages, **kwargs):
            del messages
            sent.append(kwargs["speech_feature_sample_id"])
            return "[]"

        def close(self):
            return {
                "request_count": len(sent),
                "trace_manifest_hash": "a" * 64,
                "cost": {"umbrella_lock_sha256": "b" * 64},
            }

    def phase(**kwargs):
        subset = kwargs["adapter"]
        core = kwargs["core_client"]
        decoding = kwargs["decoding_params"]
        slots = kwargs["slot_by_sample"]
        results = []
        for sample in subset.load_split(launcher.ground_flight.SPLIT_ID):
            observed_slots.append((sample.sample_id, slots[sample.sample_id]))
            messages = launcher._speech_messages(
                subset, sample, bindings[sample.sample_id]
            )
            per_sample = dict(decoding)
            per_sample["id_slot"] = slots[sample.sample_id]
            text = core.complete(
                messages,
                decoding_params=per_sample,
                speech_feature_sample_id=sample.sample_id,
                key_representation_id=kwargs["key_representation_id"],
                matcher_policy_id=kwargs["matcher_policy_id"],
            )
            results.append(
                launcher.ground_flight.GroundDirectResult(sample.sample_id, text)
            )
        return launcher.ground_flight.GroundDirectSummary(tuple(results))

    sealed: list[object] = []
    monkeypatch.setattr(launcher, "build_payload_binding", lambda **kwargs: object())
    monkeypatch.setattr(launcher, "FrozenCoreClient", Core)
    monkeypatch.setattr(launcher.ground_flight, "run_direct_qualification_phase", phase)
    monkeypatch.setattr(
        launcher,
        "_seal_arm",
        lambda **kwargs: sealed.append(kwargs["summary"]) or {"sealed": True},
    )

    result = launcher._run_arm(
        root=tmp_path,
        context=context,
        gate=object(),
        transport=object(),
        arm=launcher.ARM_ORDER[0],
        plan=launcher.execution_plan(launcher.ATTEMPT_IDS[launcher.ARM_ORDER[0]]),
        run_dir=tmp_path / "arm",
        session_receipt_path=tmp_path / "session.json",
    )

    assert result == {"sealed": True}
    assert sent == list(sample_ids)
    assert observed_slots == [
        (
            sample_id,
            context["source_request_bindings"][launcher.ARM_ORDER[0]][sample_id][
                "id_slot"
            ],
        )
        for sample_id in sample_ids
    ]
    assert len(sealed) == 1
    assert len(sealed[0].results) == 8
    plan_doc = json.loads((tmp_path / "arm" / "execution-plan.json").read_text())
    assert plan_doc == asdict(
        launcher.execution_plan(launcher.ATTEMPT_IDS[launcher.ARM_ORDER[0]])
    )


def test_launch_starts_one_session_runs_ordered_arms_and_returns_unscored_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = _launcher()
    events: list[str] = []
    values = {
        "model_lock_key": "model",
        "model_materialization_root": "/runtime",
        "base_url": "http://127.0.0.1:8090",
        "server_args": [],
        "server_env": {},
        "transport": "fake",
    }
    context = {
        "commit": "a" * 40,
        "launcher_sha256": "b" * 64,
        "config_sha256": launcher.COMPOSED_CONFIG_SHA256,
        "precontact_plan_sha256": "c" * 64,
        "precontact_plan": {"schema": "plan"},
        "runtime_receipt": {"runtime": "receipt"},
        "composed": SimpleNamespace(values=values),
        "registered_flight_plan_sha256": launcher.REGISTERED_PLAN_SHA256,
        "registered_flight_plan": {"flight_id": "flight-20260903T013000Z"},
        "registered_plans": {
            arm: launcher.execution_plan(launcher.ATTEMPT_IDS[arm])
            for arm in launcher.ARM_ORDER
        },
        "execution_plan_sha256": {
            arm: launcher.canonical_sha256(
                asdict(launcher.execution_plan(launcher.ATTEMPT_IDS[arm]))
            )
            for arm in launcher.ARM_ORDER
        },
    }

    class Gate:
        @classmethod
        def for_study_repo(cls, *args, **kwargs):
            del args, kwargs
            return cls()

        def assert_model_touch_allowed(self, plan, full_hash):
            del plan, full_hash
            events.append("gate")
            return "d" * 64

    class Transports:
        def resolve(self, name):
            assert name == "fake"
            return lambda *args, **kwargs: object()

    monkeypatch.setattr(
        launcher, "static_preflight", lambda root, registered_plan_path=None: context
    )
    monkeypatch.setattr(launcher, "FrozenCoreGate", Gate)
    monkeypatch.setattr(launcher, "TRANSPORTS", Transports())
    monkeypatch.setattr(
        launcher,
        "start_session",
        lambda **kwargs: events.append("start") or object(),
    )
    monkeypatch.setattr(
        launcher,
        "_stop",
        lambda session, runtime, path: events.append("stop"),
    )

    def run_arm(**kwargs):
        arm = kwargs["arm"]
        events.append(arm)
        return {"arm": arm, "request_count": 8}

    monkeypatch.setattr(launcher, "_run_arm", run_arm)

    receipt = launcher.launch(tmp_path)

    assert events == ["gate", "gate", "start", *launcher.ARM_ORDER, "stop"]
    assert receipt["status"] == "SEALED_UNSCORED"
    assert receipt["contacts"] == 16
    assert receipt["scorer_contacts"] == 0
    assert receipt["gold_opened"] is False
