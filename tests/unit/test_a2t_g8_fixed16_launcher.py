"""Contact-free tests for the executable G8 fixed16 launcher."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-03-a2t-g8-action-support-reachability-fixed16-v1/launcher/"
    "launch_a2t_g8_fixed16.py"
)
SPEC = importlib.util.spec_from_file_location("g8_launcher", LAUNCHER)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


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
                family_label=f"Family {family}",
                tools=tools,
                tool_names=tuple(tool.tool_name for tool in tools),
                text=f"Family {family} construction examples.",
            )
        )
    return SimpleNamespace(
        bundles=tuple(bundles),
        tool_names=tuple(name for bundle in bundles for name in bundle.tool_names),
        sha256=module.GROUND_SHA256,
        receipt={"schema": "saea-a2t-construction-example-ground-receipt-v1"},
    )


def test_baseline_freezes_g8_geometry_without_authorizing_a_contact() -> None:
    baseline = json.loads(module.BASELINE.read_text(encoding="utf-8"))

    assert baseline["speech_native_contact_ceiling_per_task"] == 34
    assert baseline["obs_contacts_per_task"] == 1
    assert baseline["evidence_contacts_per_task"] == 28
    assert baseline["resolve_contacts_per_task"] == 5
    assert baseline["max_concurrent_model_requests"] == 2
    assert baseline["queue_depth"] == 4
    assert baseline["retries"] == baseline["resends"] == baseline["repair_contacts"] == 0
    assert baseline["network_jitter_testing"] is False


def test_execution_plan_and_wave_geometry_are_receipt_bound() -> None:
    plan = module.execution_plan("attempt-g8-unit")

    assert plan.split_identity_hash == module.SPLIT_IDENTITY_HASH
    assert plan.planned_model_calls == 544
    assert plan.planned_speech_audio_seconds == 2728
    assert module.SHARED_CONTACTS_PER_SAMPLE == 29
    assert module.BRANCH_CONTACTS_PER_SAMPLE == 5
    assert module.CONTACTS_PER_SAMPLE == 34
    assert module.SAMPLE_COUNT == 16
    assert module.MODEL_CONTACTS == 544
    assert module.WAVE_ORDER == (
        "OBS",
        "EVIDENCE",
        "BRANCH_ROUND_1",
        "DECOMPOSED_BIND",
        "DECOMPOSED_RESOLVE",
    )


def test_committed_g7_ground_is_reused_without_construction_row_access() -> None:
    ground = module.load_ground()

    assert ground.sha256 == module.GROUND_SHA256
    assert len(ground.bundles) == 28
    assert len(ground.tool_names) == 152


def test_preflight_measures_every_wave_and_keeps_headroom() -> None:
    report = module.preflight_ground(_ground(), speech_feature_tokens_max=100)

    assert report["contacts"] == 544
    assert report["family_count"] == 28
    assert report["tool_count"] == 152
    assert report["slots"] == report["max_concurrent_model_requests"] == 2
    assert report["queue_depth"] == 4
    assert report["dynamic_measurement"] == "immediately-before-every-contact"
    assert report["serialized_request_counter"] == "utf8-byte-upper-bound"
    assert report["special_token_reserve"] == 512
    assert set(report["prompt_fits"]) == {
        "obs",
        "evidence",
        "exhaustive_resolve",
        "support_only_resolve",
        "decomposed_select",
        "decomposed_bind_maximum",
        "decomposed_resolve_maximum",
    }
    assert all(
        row["remaining_tokens"] >= 8192
        for row in report["prompt_fits"]["evidence"]
    )
    assert report["prompt_fits"]["decomposed_select"]["completion_tokens"] == 4096
    assert report["prompt_fits"]["decomposed_bind_maximum"]["completion_tokens"] == 12288
    assert all(
        fit["remaining_tokens"] >= 8192
        for key, value in report["prompt_fits"].items()
        for fit in (value if key == "evidence" else [value])
    )


def test_preflight_refuses_ground_identity_or_schema_drift() -> None:
    bad_hash = _ground()
    bad_hash.sha256 = "0" * 64
    with pytest.raises(ValueError, match="SHA-256"):
        module.preflight_ground(bad_hash, speech_feature_tokens_max=0)

    bad_schema = _ground()
    bad_schema.receipt = {"schema": "wrong"}
    with pytest.raises(ValueError, match="schema"):
        module.preflight_ground(bad_schema, speech_feature_tokens_max=0)


def test_dynamic_measurement_uses_serialized_bytes_and_refuses_overflow() -> None:
    fit = module._measure(
        contact_id="g8-unit",
        rendered_request="x" * 23_040,
        completion_tokens=1024,
        speech_feature_tokens=0,
    )

    assert fit.total_tokens == 24_576
    with pytest.raises(ValueError, match="refused"):
        module._measure(
            contact_id="g8-unit",
            rendered_request="x" * 23_041,
            completion_tokens=1024,
            speech_feature_tokens=0,
        )


def test_branch_derivatives_keep_exact_identity_and_m0_is_zero_contact() -> None:
    sample_ids = ("tier1:1", "tier2:2")
    finals = {
        "EXHAUSTIVE_G7": {sample_id: f"exhaustive:{sample_id}" for sample_id in sample_ids},
        "SUPPORT_ONLY_RESOLVE": {sample_id: f"support:{sample_id}" for sample_id in sample_ids},
        "DECOMPOSED_SELECT_BIND_RESOLVE": {
            sample_id: f"decomposed:{sample_id}" for sample_id in sample_ids
        },
    }
    m0 = {sample_id: f"m0:{sample_id}" for sample_id in sample_ids}

    derivatives = module.build_branch_derivatives(
        sample_ids=sample_ids,
        m0_texts=m0,
        branch_final_texts=finals,
    )

    assert tuple(derivatives) == module.BRANCH_ORDER
    assert derivatives["STOP_M0"].new_model_contacts == 0
    assert derivatives["STOP_M0"].texts == m0
    assert derivatives["EXHAUSTIVE_G7"].new_model_contacts == 16
    assert derivatives["SUPPORT_ONLY_RESOLVE"].new_model_contacts == 16
    assert derivatives["DECOMPOSED_SELECT_BIND_RESOLVE"].new_model_contacts == 48
    assert all(tuple(derivative.texts) == sample_ids for derivative in derivatives.values())


def test_branch_derivatives_refuse_missing_or_unexpected_identity() -> None:
    with pytest.raises(ValueError, match="exact identity"):
        module.build_branch_derivatives(
            sample_ids=("a", "b"),
            m0_texts={"a": "m0-a", "b": "m0-b"},
            branch_final_texts={
                "EXHAUSTIVE_G7": {"a": "a", "b": "b"},
                "SUPPORT_ONLY_RESOLVE": {"a": "a", "b": "b"},
                "DECOMPOSED_SELECT_BIND_RESOLVE": {"a": "a", "extra": "x"},
            },
        )


def test_client_summary_requires_exact_contact_count_and_transport_trace_hash() -> None:
    summary = {
        "request_count": 544,
        "trace_manifest_hash": "a" * 64,
        "cost": {"calls_used": 544},
    }

    assert module._validate_client_summary(summary) is summary
    with pytest.raises(RuntimeError, match="request count"):
        module._validate_client_summary({**summary, "request_count": 543})
    with pytest.raises(RuntimeError, match="trace manifest"):
        module._validate_client_summary({**summary, "trace_manifest_hash": "bad"})

    with pytest.raises(ValueError, match="unique"):
        module.build_branch_derivatives(
            sample_ids=("a", "a"),
            m0_texts={"a": "m0"},
            branch_final_texts={},
        )


def test_score_plan_has_one_whole_manifest_job_per_branch() -> None:
    manifests = {
        branch: Path(f"/sealed/{branch}.run-manifest.json")
        for branch in module.BRANCH_ORDER
    }
    plan = module.parallel_score_plan(manifests)

    assert plan["workers"] == 4
    assert plan["processes_per_job"] == 1
    assert plan["dataset_sharding"] is False
    assert plan["shard_metric_averaging"] is False
    assert [row["branch"] for row in plan["jobs"]] == list(module.BRANCH_ORDER)
    assert all(row["row_count"] == 16 for row in plan["jobs"])
    assert all(row["manifest"] == str(manifests[row["branch"]]) for row in plan["jobs"])
    assert plan["include_per_sample"] is True
    assert "--include-per-sample" in plan["invocation"]


def test_future_oracle_builder_is_model_free_and_requires_all_branches() -> None:
    result = module.future_oracle_manifest_spec(
        branch_manifests={branch: Path(f"/tmp/{branch}.run-manifest.json") for branch in module.BRANCH_ORDER}
    )

    assert result["model_contacts"] == 0
    assert result["scoring_invocations"] == 1
    assert result["source_branch_order"] == list(module.BRANCH_ORDER)
    with pytest.raises(ValueError, match="all four"):
        module.future_oracle_manifest_spec(branch_manifests={})


def test_launch_default_is_a_complete_contact_free_preflight(monkeypatch: pytest.MonkeyPatch) -> None:
    report = {"status": "PREFLIGHT_PASSED", "surface": object()}
    monkeypatch.setattr(module, "static_preflight", lambda _root: report)

    result = module.launch(Path("/unused"), "attempt-g8-unit", execute=False)

    assert result["status"] == "PREFLIGHT_PASSED"


def test_m0_loader_requires_exact_identity_and_preserves_source(tmp_path: Path) -> None:
    path = tmp_path / "m0.jsonl"
    path.write_text(
        "".join(
            json.dumps({"sample_id": sample_id, "text": f"m0:{sample_id}"}) + "\n"
            for sample_id in ("b", "a", "outside-g8")
        ),
        encoding="utf-8",
    )

    loaded = module.load_m0_outputs(path, ("a", "b"))

    assert tuple(loaded) == ("a", "b")
    assert loaded["a"] == "m0:a"
    assert "outside-g8" not in loaded
    path.write_text(
        json.dumps({"sample_id": "a", "text": "one"}) + "\n"
        + json.dumps({"sample_id": "a", "text": "two"}) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="duplicate"):
        module.load_m0_outputs(path, ("a",))


def test_openjiuwen_five_waves_use_544_contacts_and_terminalize_bad_select() -> None:
    ids = tuple(f"sample-{index}" for index in range(16))
    surface = module.RuntimeSurface(
        samples=tuple(SimpleNamespace(sample_id=value) for value in ids),
        packet_bindings={value: {"packet_id": value, "sha256": "b" * 64} for value in ids},
        speech_feature_tokens_by_sample={value: 10 for value in ids},
    )

    class Client:
        def __init__(self, invalid_select: bool = False) -> None:
            self.invalid_select = invalid_select
            self.calls = []

        def complete(self, _messages, **kwargs):
            self.calls.append(kwargs)
            contact = kwargs["agent_contact_id"]
            if contact == "g8-obs":
                return "The speaker requests a device action."
            if contact.startswith("g8-evidence-"):
                return "{}"
            if contact == "g8-decomposed-select":
                return "not json" if self.invalid_select else "[]"
            if contact == "g8-decomposed-bind":
                return "[]"
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
                    kwargs["invoke_contact"](state, index, index % 2)
                    for index in range(count)
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
    assert len(client.calls) == 544
    contact_audits = [row for row in sink.rows if row[0] == "COST"]
    assert len(contact_audits) == 544
    assert all("prompt_fit" in row[2] and "response_sha256" in row[2] for row in contact_audits)
    assert all("speech_feature_sample_id" in call for call in client.calls)
    assert module.physical_and_logical_costs()["physical_model_contacts"] == 544
    assert module.physical_and_logical_costs()["logical_action_contacts"] == {
        "STOP_M0": 0,
        "EXHAUSTIVE_G7": 480,
        "SUPPORT_ONLY_RESOLVE": 480,
        "DECOMPOSED_SELECT_BIND_RESOLVE": 512,
    }

    bad = Client(invalid_select=True)
    terminal_blocked = []

    def terminal_runner(states, **kwargs):
        first, second = states[:2]
        try:
            while kwargs["should_continue"](first):
                count = kwargs["prepare_wave"](first, object())
                responses = tuple(
                    kwargs["invoke_contact"](first, index, index % 2)
                    for index in range(count)
                )
                kwargs["aggregate_wave"](first, responses, object())
        except module.G8ActionSupportError as error:
            kwargs["prepare_wave"](second, object())
            calls_before = len(bad.calls)
            with pytest.raises(RuntimeError, match="terminal"):
                kwargs["invoke_contact"](second, 0, 1)
            terminal_blocked.append(len(bad.calls) == calls_before)
            raise error
        return states

    with pytest.raises(module.G8ActionSupportError, match="selection"):
        module.run_openjiuwen_phase(
            surface=surface,
            ground=_ground(),
            client=bad,
            trace_sink=Sink(),
            workflow_runner=terminal_runner,
        )
    assert terminal_blocked == [True]
    assert bad.calls[-1]["agent_contact_id"] == "g8-decomposed-select"
    assert not any(row["agent_contact_id"] == "g8-decomposed-bind" for row in bad.calls)


def test_static_preflight_checks_hashes_configuration_and_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    m0 = tmp_path / "m0.jsonl"
    m0.write_text("opaque", encoding="utf-8")
    monkeypatch.setattr(module, "M0_RELPATH", Path("m0.jsonl"))
    expected = {
        module.G8_ROSTER: module.ROSTER_SHA256,
        module.G1_RECEIPT: module.G1_RECEIPT_SHA256,
        module.GROUND_CORPUS: module.GROUND_SHA256,
        module.GROUND_STRUCTURED: module.GROUND_STRUCTURED_SHA256,
        module.GROUND_RECEIPT: module.GROUND_RECEIPT_SHA256,
        module.RUNTIME_RECEIPT: module.RUNTIME_RECEIPT_SHA256,
        m0: module.M0_SHA256,
    }
    monkeypatch.setattr(module, "_sha256", lambda path: expected[Path(path)])
    monkeypatch.setattr(module, "require_clean_study_repo", lambda _repo: "commit")
    monkeypatch.setattr(module.importlib.metadata, "version", lambda _name: module.OPENJIUWEN_VERSION)
    monkeypatch.setattr(module, "load_ground", _ground)
    surface = module.RuntimeSurface(
        samples=tuple(SimpleNamespace(sample_id=f"s-{index}") for index in range(16)),
        packet_bindings={f"s-{index}": {} for index in range(16)},
        speech_feature_tokens_by_sample={f"s-{index}": 169 for index in range(16)},
    )
    monkeypatch.setattr(module, "load_runtime_surface", lambda: surface)
    monkeypatch.setattr(
        module,
        "load_m0_outputs",
        lambda _path, ids: {sample_id: "m0" for sample_id in ids},
    )
    monkeypatch.setattr(module, "load_lock", lambda _path: object())
    monkeypatch.setattr(
        module,
        "compose",
        lambda *_args: SimpleNamespace(
            config_hash=module.COMPOSED_CONFIG_SHA256,
            values={
                "arm": "speech-feature-query",
                "profile_slot_count": 2,
                "max_concurrent_model_requests": 2,
                "queue_depth": 4,
                "repair_contacts": 0,
                "retries": 0,
                "resends": 0,
                "network_jitter_testing": False,
            },
        ),
    )
    monkeypatch.setattr(module, "protocol_hash", lambda *_args: module.PROTOCOL_SHA256)

    report = module.static_preflight(tmp_path)

    assert report["status"] == "PREFLIGHT_PASSED"
    assert report["prompt_fit"]["contacts"] == 544
    assert report["repeated_speech_audio_seconds"] == 80.213
    assert report["planned_speech_audio_seconds"] == 2728


def test_static_preflight_refuses_composed_config_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    m0 = tmp_path / "m0.jsonl"
    m0.write_text("opaque", encoding="utf-8")
    monkeypatch.setattr(module, "M0_RELPATH", Path("m0.jsonl"))
    expected = {
        module.G8_ROSTER: module.ROSTER_SHA256,
        module.G1_RECEIPT: module.G1_RECEIPT_SHA256,
        module.GROUND_CORPUS: module.GROUND_SHA256,
        module.GROUND_STRUCTURED: module.GROUND_STRUCTURED_SHA256,
        module.GROUND_RECEIPT: module.GROUND_RECEIPT_SHA256,
        module.RUNTIME_RECEIPT: module.RUNTIME_RECEIPT_SHA256,
        m0: module.M0_SHA256,
    }
    monkeypatch.setattr(module, "_sha256", lambda path: expected[Path(path)])
    monkeypatch.setattr(module, "require_clean_study_repo", lambda _repo: "commit")
    monkeypatch.setattr(
        module,
        "compose",
        lambda *_args: SimpleNamespace(config_hash="0" * 64, values={"arm": "x"}),
    )

    with pytest.raises(RuntimeError, match="configuration hash"):
        module.static_preflight(tmp_path)


def test_execute_path_starts_one_loopback_session_and_seals_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    surface = module.RuntimeSurface(
        samples=(SimpleNamespace(sample_id="a"),),
        packet_bindings={"a": {}},
        speech_feature_tokens_by_sample={"a": 1},
    )
    values = {
        "model_lock_key": "model",
        "model_materialization_root": str(tmp_path / "model"),
        "base_url": "http://127.0.0.1:8123",
        "server_args": [],
        "server_env": {},
        "transport": "fake",
    }
    context = {
        "composed": SimpleNamespace(values=values),
        "lock": object(),
        "surface": surface,
        "ground": object(),
        "prompt_fit": {},
        "commit": "a" * 40,
        "m0_texts": {"a": "m0"},
    }
    monkeypatch.setattr(module, "static_preflight", lambda _root: context)

    class Gate:
        def assert_model_touch_allowed(self, plan, *, full_hash):
            assert plan.planned_model_calls == 544 and full_hash is True

    monkeypatch.setattr(
        module.FrozenCoreGate,
        "for_study_repo",
        lambda *_args, **_kwargs: Gate(),
    )
    monkeypatch.setattr(module, "load_runtime_receipt", lambda _path: object())
    monkeypatch.setattr(module, "start_session", lambda **_kwargs: object())
    stops = []
    monkeypatch.setattr(module, "stop_session", lambda *args, **kwargs: stops.append((args, kwargs)))
    monkeypatch.setattr(module.TRANSPORTS, "resolve", lambda _name: lambda *_args, **_kwargs: object())
    monkeypatch.setattr(module, "asset_dir", lambda *_args: tmp_path)
    monkeypatch.setattr(module, "build_payload_binding", lambda **_kwargs: object())

    class Client:
        def __init__(self, **_kwargs):
            pass

        def close(self):
            return {
                "request_count": 544,
                "trace_manifest_hash": "e" * 64,
                "cost": {"calls_used": 544},
            }

    class Sink:
        def __init__(self, path, _run_id):
            self.path = path

        def close(self):
            return "c" * 64

    monkeypatch.setattr(module, "FrozenCoreClient", Client)
    monkeypatch.setattr(module, "TraceSink", Sink)
    monkeypatch.setattr(module, "run_openjiuwen_phase", lambda **_kwargs: object())
    monkeypatch.setattr(module, "_seal_branches", lambda **_kwargs: {"branches": {}})

    receipt = module.launch(tmp_path, "attempt-g8-execute", execute=True)

    assert receipt["status"] == "SEALED_FOUR_BRANCHES_UNSCORED"
    assert receipt["physical_cost"]["model_contacts_once"] == 544
    assert receipt["gold_opened"] is False
    assert len(stops) == 1


def test_seal_emits_four_complete_branch_manifests_and_score_jobs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ids = tuple(f"s-{index}" for index in range(16))
    summary = module.FlightSummary(
        tuple(
            SimpleNamespace(
                sample=SimpleNamespace(sample_id=sample_id),
                branch_texts={
                    branch: f"{branch}:{sample_id}" for branch in module.BRANCH_ORDER[1:]
                },
            )
            for sample_id in ids
        )
    )
    agent_trace = tmp_path / "agent.jsonl"
    agent_trace.write_text("trace\n", encoding="utf-8")

    class Sink:
        def __init__(self, path, run_id):
            self.path = path
            self.run_id = run_id

        def emit(self, *_args):
            return None

        def close(self):
            self.path.mkdir(parents=True, exist_ok=True)
            (self.path / f"{self.run_id}.trace.jsonl").write_text("trace\n", encoding="utf-8")
            (self.path / f"{self.run_id}.trace-manifest.json").write_text("{}\n", encoding="utf-8")
            return "d" * 64

    def manifest(**kwargs):
        path = kwargs["run_dir"] / f"{module.RUN_ID}.run-manifest.json"
        path.write_text('{"scorers": []}\n', encoding="utf-8")
        return path

    monkeypatch.setattr(module, "TraceSink", Sink)
    monkeypatch.setattr(module, "build_manifest", manifest)
    monkeypatch.setattr(module, "verify_bundle", lambda _path: SimpleNamespace(outputs_rows=({},) * 16))
    monkeypatch.setattr(module, "_verified_split", lambda: object())

    sealed = module._seal_branches(
        root=tmp_path,
        context={
            "m0_texts": {sample_id: f"m0:{sample_id}" for sample_id in ids},
            "composed": object(),
        },
        plan=module.execution_plan("attempt-g8-seal"),
        summary=summary,
        client_summary={
            "trace_manifest_hash": "e" * 64,
            "cost": {"calls_used": 544},
        },
        run_dir=tmp_path / "run",
        agent_trace_path=agent_trace,
        agent_trace_hash="c" * 64,
        session_receipt=tmp_path / "session.json",
    )

    assert set(sealed["branches"]) == set(module.BRANCH_ORDER)
    assert all(Path(row["manifest"]).is_file() for row in sealed["branches"].values())
    assert (tmp_path / "run" / "official-score-jobs.jsonl").read_text().count("\n") == 4
    exhaustive_outputs = Path(sealed["branches"]["EXHAUSTIVE_G7"]["outputs"])
    first = json.loads(exhaustive_outputs.read_text(encoding="utf-8").splitlines()[0])
    assert first["composite_source"]["source_transport_trace_manifest_sha256"] == "e" * 64
