"""Contact-free tests for the G8B sample-local successor launcher."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-03-a2t-g8b-action-support-reachability-fixed16-v1/launcher/"
    "launch_a2t_g8b_fixed16.py"
)
SPEC = importlib.util.spec_from_file_location("g8b_launcher", LAUNCHER)
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


def _surface():
    ids = tuple(f"sample-{index}" for index in range(16))
    return module.RuntimeSurface(
        samples=tuple(SimpleNamespace(sample_id=value) for value in ids),
        packet_bindings={value: {"packet_id": value, "sha256": "b" * 64} for value in ids},
        speech_feature_tokens_by_sample={value: 10 for value in ids},
    )


class _Sink:
    def __init__(self) -> None:
        self.rows = []

    def emit(self, *args):
        self.rows.append(args)


def _runner(states, **kwargs):
    for state in states:
        while kwargs["should_continue"](state):
            count = kwargs["prepare_wave"](state, object())
            responses = tuple(
                kwargs["invoke_contact"](state, index, index % 2)
                for index in range(count)
            )
            kwargs["aggregate_wave"](state, responses, object())
    return states


def test_successor_has_new_identity_and_keeps_544_as_a_ceiling() -> None:
    plan = module.execution_plan("attempt-g8b-unit")

    assert module.RUN_ID == "SAEA-A2T-G8B-ACTION-SUPPORT-REACHABILITY-FIXED16-V1"
    assert plan.run_id == module.RUN_ID
    assert plan.planned_model_calls == 544
    assert module.MAX_MODEL_CONTACTS == 544
    assert module.MIN_MODEL_CONTACTS == 512


def test_g8b_runtime_identity_is_fresh_and_disjoint_from_consumed_g8() -> None:
    expected = json.loads(module.G8B_ROSTER.read_text(encoding="utf-8"))
    consumed = json.loads(module.G8_ROSTER.read_text(encoding="utf-8"))

    ids = module._selected_roster_ids()

    assert ids == tuple(row["sample_id"] for row in expected["selected"])
    assert set(ids).isdisjoint(row["sample_id"] for row in consumed["selected"])
    assert module.SPLIT_IDENTITY_HASH == expected["split_identity_hash"]
    assert module.PLANNED_SPEECH_AUDIO_SECONDS == 2578


def test_static_preflight_context_uses_exact_g8b_selected_ids(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ids = module._selected_roster_ids()
    m0 = tmp_path / "m0.jsonl"
    m0.write_text("opaque", encoding="utf-8")
    monkeypatch.setattr(module, "M0_RELPATH", Path("m0.jsonl"))
    hashes = {
        module.G8B_ROSTER: module.ROSTER_SHA256,
        module.G8_ROSTER: module.G8_ROSTER_SHA256,
        module.G1_RECEIPT: module.G1_RECEIPT_SHA256,
        module.GROUND_CORPUS: module.GROUND_SHA256,
        module.GROUND_STRUCTURED: module.GROUND_STRUCTURED_SHA256,
        module.GROUND_RECEIPT: module.GROUND_RECEIPT_SHA256,
        module.RUNTIME_RECEIPT: module.RUNTIME_RECEIPT_SHA256,
        m0: module.M0_SHA256,
    }
    monkeypatch.setattr(module._v1, "_sha256", lambda path: hashes[Path(path)])
    monkeypatch.setattr(module._v1, "require_clean_study_repo", lambda _repo: "commit")
    values = {
        "arm": "speech-feature-query",
        "profile_slot_count": 2,
        "max_concurrent_model_requests": 2,
        "queue_depth": 4,
        "repair_contacts": 0,
        "retries": 0,
        "resends": 0,
        "network_jitter_testing": False,
    }
    monkeypatch.setattr(
        module._v1,
        "compose",
        lambda *_args: SimpleNamespace(
            config_hash=module.COMPOSED_CONFIG_SHA256, values=values
        ),
    )
    monkeypatch.setattr(
        module._v1, "protocol_hash", lambda *_args: module.PROTOCOL_SHA256
    )
    monkeypatch.setattr(module, "_verify_repeated_speech_reservation", lambda: 75.808)
    monkeypatch.setattr(
        module.importlib.metadata, "version", lambda _name: module.OPENJIUWEN_VERSION
    )
    surface = module.RuntimeSurface(
        samples=tuple(SimpleNamespace(sample_id=sample_id) for sample_id in ids),
        packet_bindings={sample_id: {} for sample_id in ids},
        speech_feature_tokens_by_sample={sample_id: 1 for sample_id in ids},
    )
    monkeypatch.setattr(module, "load_runtime_surface", lambda: surface)
    monkeypatch.setattr(
        module._v1,
        "load_m0_outputs",
        lambda _path, expected: {sample_id: "m0" for sample_id in expected},
    )
    monkeypatch.setattr(module._v1, "load_ground", _ground)
    monkeypatch.setattr(
        module._v1, "preflight_ground", lambda *_args, **_kwargs: {"contacts": 544}
    )
    monkeypatch.setattr(module._v1, "load_lock", lambda _path: object())
    monkeypatch.setattr(module._v1, "umbrella_lock_path", lambda _repo: Path("lock"))

    context = module.static_preflight(tmp_path)

    assert tuple(sample.sample_id for sample in context["surface"].samples) == ids
    assert context["run_id"] == module.RUN_ID
    assert context["composed_config_sha256"] == module.COMPOSED_CONFIG_SHA256
    assert context["protocol_sha256"] == module.PROTOCOL_SHA256
    assert context["planned_speech_audio_seconds"] == 2578


def test_empty_selection_seals_hashable_passthrough_without_bind_contact() -> None:
    selection = module.G8ActionSupportCore(_ground().bundles).parse_selection("[]")

    bindings, transition = module.empty_bind_passthrough("sample-0076", selection)

    assert bindings == module.ToolBindings((), "[]")
    assert transition.stage == "EMPTY_BIND_PASSTHROUGH"
    assert transition.model_contacts == 0
    assert transition.canonical_json == (
        '{"bindings":[],"sample_id":"sample-0076",'
        '"selection":[],"stage":"EMPTY_BIND_PASSTHROUGH"}'
    )
    assert transition.sha256 == hashlib.sha256(
        transition.canonical_json.encode("utf-8")
    ).hexdigest()


def test_failed_0076_fenced_wrong_cardinality_empty_bind_is_irreparable() -> None:
    core = module.G8ActionSupportCore(_ground().bundles)
    selection = core.parse_selection("[]")
    invented = '[{"name":"g8-decomposed-bind","arguments":{}}]'
    raw = f"```json\n{invented}\n```"

    with pytest.raises(module.G8ActionSupportError, match="unfenced"):
        core.parse_bindings(raw, selection)
    with pytest.raises(module.G8ActionSupportError, match="one argument object"):
        core.parse_bindings(invented, selection)
    bindings, transition = module.empty_bind_passthrough("failed-0076-class", selection)
    assert bindings == module.ToolBindings((), "[]")
    assert transition.model_contacts == 0


def test_fenced_empty_select_is_also_irreparable() -> None:
    core = module.G8ActionSupportCore(_ground().bundles)
    raw = "```json\n[]\n```"

    outcome = module.classify_selection_response(core, raw)

    assert outcome.status == "INVALID_SELECT_TERMINAL_RAW_RESPONSE"
    assert outcome.raw_terminal_text == raw
    assert outcome.selection is None
    assert outcome.retry_or_repair_authorized is False


def test_nonempty_bind_keeps_the_inherited_strict_contract() -> None:
    core = module.G8ActionSupportCore(_ground().bundles)
    selection = core.parse_selection('["t_0_0"]')
    raw = '[{"name":"t_0_0","arguments":{}}]'

    outcome = module.classify_binding_response(core, raw, selection)

    assert outcome.status == "VALID_BIND"
    assert outcome.bindings == module.ToolBindings(
        (module.BoundCall("t_0_0", "{}"),), raw
    )
    assert outcome.raw_terminal_text is None


def test_empty_bind_helpers_fail_closed_when_called_on_the_wrong_path() -> None:
    core = module.G8ActionSupportCore(_ground().bundles)
    empty = core.parse_selection("[]")
    nonempty = core.parse_selection('["t_0_0"]')

    with pytest.raises(ValueError, match="must use EMPTY_BIND_PASSTHROUGH"):
        module.classify_binding_response(core, "[]", empty)
    with pytest.raises(ValueError, match="requires the exact sealed empty selection"):
        module.empty_bind_passthrough("sample", nonempty)
    with pytest.raises(RuntimeError, match="outside its registered range"):
        module._validate_client_summary({}, expected_contacts=511)
    with pytest.raises(ValueError, match="exact identity-complete"):
        module.build_branch_derivatives(
            sample_ids=("a",),
            m0_texts={"a": "m0"},
            branch_final_texts={},
            decomposed_new_contacts=1,
        )


def test_dynamic_execution_keeps_failures_sample_local_and_all_branch_texts_complete(
    tmp_path: Path,
) -> None:
    class Client:
        def __init__(self) -> None:
            self.calls = []

        def complete(self, _messages, **kwargs):
            self.calls.append(kwargs)
            sample = kwargs["speech_feature_sample_id"]
            contact = kwargs["agent_contact_id"]
            if contact == "g8-obs":
                return "The speaker requests a device action."
            if contact.startswith("g8-evidence-"):
                return "{}"
            if contact == "g8-decomposed-select":
                return {
                    "sample-0": "[]",
                    "sample-1": '["t_0_0"]',
                    "sample-2": "```json\n[]\n```",
                    "sample-3": '["t_0_0"]',
                    "sample-4": '["t_0_0"]',
                }.get(sample, "[]")
            if contact == "g8-decomposed-bind":
                return {
                    "sample-1": '[{"name":"t_0_0","arguments":{}}]',
                    "sample-3": "[]",
                    "sample-4": "```json\n[]\n```",
                }[sample]
            return '{"calls":[]}'

    client = Client()
    sink = module.TraceSink(tmp_path / "real-agent-trace", module.RUN_ID)
    summary = module.run_openjiuwen_phase(
        surface=_surface(),
        ground=_ground(),
        client=client,
        trace_sink=sink,
        workflow_runner=_runner,
    )

    by_id = {state.sample.sample_id: state for state in summary.results}
    by_sample_contacts = {
        sample_id: [
            call["agent_contact_id"]
            for call in client.calls
            if call["speech_feature_sample_id"] == sample_id
        ]
        for sample_id in by_id
    }
    assert summary.physical_model_contacts == 528
    assert len(client.calls) == 528
    assert "g8-decomposed-bind" not in by_sample_contacts["sample-0"]
    assert by_sample_contacts["sample-0"][-1] == "g8-decomposed-resolve"
    assert by_id["sample-0"].bindings == module.ToolBindings((), "[]")
    assert len(by_id["sample-0"].model_free_transitions) == 1
    assert by_sample_contacts["sample-1"][-2:] == [
        "g8-decomposed-bind",
        "g8-decomposed-resolve",
    ]
    assert by_sample_contacts["sample-2"][-1] == "g8-decomposed-select"
    assert by_id["sample-2"].invalid_stage == "DECOMPOSED_SELECT"
    assert by_id["sample-2"].branch_texts["DECOMPOSED_SELECT_BIND_RESOLVE"] == (
        "```json\n[]\n```"
    )
    assert by_sample_contacts["sample-3"][-1] == "g8-decomposed-bind"
    assert by_id["sample-3"].invalid_stage == "DECOMPOSED_BIND"
    assert by_id["sample-3"].branch_texts["DECOMPOSED_SELECT_BIND_RESOLVE"] == "[]"
    assert by_id["sample-4"].invalid_status == "INVALID_BIND_TERMINAL_RAW_RESPONSE"
    assert all(set(state.branch_texts) == set(module.BRANCH_ORDER[1:]) for state in summary.results)
    assert all(state.stage == "DONE" for state in summary.results)

    costs = module.physical_and_logical_costs(summary)
    assert costs["physical_model_contacts"] == 528
    assert costs["dynamic_formula"] == {
        "base_with_all_final_resolves": 528,
        "nonempty_valid_selections": 3,
        "invalid_selects": 1,
        "invalid_binds": 2,
    }
    assert costs["logical_action_contacts"]["DECOMPOSED_SELECT_BIND_RESOLVE"] == 496

    sink.close()
    trace_path = (
        tmp_path
        / "real-agent-trace"
        / f"{module.RUN_ID}.trace.jsonl"
    )
    trace_rows = tuple(
        json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()
    )
    categories = [row["channel"] for row in trace_rows]
    assert categories.count("COST") == 528
    assert categories.count("TOOL") == 0
    assert categories.count("OBS") == categories.count("ORG") == categories.count("SUPPLY") == 16
    assert categories.count("USE") == 60
    invalid_use = [
        row["payload"]
        for row in trace_rows
        if row["channel"] == "USE"
        and row["payload"].get("use_branch") == "DECOMPOSED_SELECT_BIND_RESOLVE"
        and row["payload"].get("use_invalid_stage")
    ]
    assert {(row["use_sample_id"], row["use_invalid_stage"]) for row in invalid_use} == {
        ("sample-2", "DECOMPOSED_SELECT"),
        ("sample-3", "DECOMPOSED_BIND"),
        ("sample-4", "DECOMPOSED_BIND"),
    }
    for row in trace_rows:
        prefix = {
            "OBS": "obs_",
            "ORG": "org_",
            "SUPPLY": "supply_",
            "USE": "use_",
        }.get(row["channel"])
        if prefix is not None:
            assert all(key.startswith(prefix) for key in row["payload"])


def test_transport_summary_reconciles_the_realized_dynamic_count() -> None:
    summary = {
        "request_count": 528,
        "trace_manifest_hash": "a" * 64,
        "cost": {"calls_used": 528},
    }

    assert module._validate_client_summary(summary, expected_contacts=528) is summary
    with pytest.raises(RuntimeError, match="realized request count"):
        module._validate_client_summary(summary, expected_contacts=529)
    with pytest.raises(RuntimeError, match="transport cost"):
        module._validate_client_summary(
            {**summary, "cost": {"calls_used": 527}}, expected_contacts=528
        )


def test_execute_path_reconciles_dynamic_transport_and_seals_four_branches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ids = tuple(f"sample-{index}" for index in range(16))
    states = tuple(
        SimpleNamespace(
            sample=SimpleNamespace(sample_id=sample_id),
            selection=module.ToolSelection((), "[]"),
            invalid_stage=None,
            branch_texts={branch: f"{branch}:{sample_id}" for branch in module.BRANCH_ORDER[1:]},
        )
        for sample_id in ids
    )
    summary = module.FlightSummary(states, 528)
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
        "surface": _surface(),
        "ground": _ground(),
        "prompt_fit": {},
        "commit": "a" * 40,
        "m0_texts": {sample_id: "m0" for sample_id in ids},
    }
    monkeypatch.setattr(module, "static_preflight", lambda _root: context)

    class Gate:
        def assert_model_touch_allowed(self, plan, *, full_hash):
            assert plan.run_id == module.RUN_ID
            assert plan.planned_model_calls == 544
            assert full_hash is True

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
                "request_count": 528,
                "trace_manifest_hash": "e" * 64,
                "cost": {"calls_used": 528},
            }

    class Sink:
        def __init__(self, path, _run_id):
            self.path = path

        def close(self):
            return "c" * 64

    monkeypatch.setattr(module, "FrozenCoreClient", Client)
    monkeypatch.setattr(module, "TraceSink", Sink)
    monkeypatch.setattr(module, "run_openjiuwen_phase", lambda **_kwargs: summary)
    monkeypatch.setattr(module, "_seal_branches", lambda **_kwargs: {"branches": {branch: {} for branch in module.BRANCH_ORDER}})

    receipt = module.launch(tmp_path, "attempt-g8b-execute", execute=True)

    assert receipt["status"] == "SEALED_FOUR_BRANCHES_UNSCORED"
    assert receipt["physical_cost"]["model_contacts_realized"] == 528
    assert receipt["physical_cost"]["model_contacts_maximum"] == 544
    assert receipt["gold_opened"] is False
    assert receipt["scorer_contacts"] == 0
    assert len(stops) == 1


def test_dynamic_sealing_emits_four_complete_unscored_manifests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ids = tuple(f"sample-{index}" for index in range(16))
    states = tuple(
        SimpleNamespace(
            sample=SimpleNamespace(sample_id=sample_id),
            selection=module.ToolSelection((), "[]"),
            invalid_stage="DECOMPOSED_SELECT" if index == 0 else None,
            invalid_status=(
                "INVALID_SELECT_TERMINAL_RAW_RESPONSE" if index == 0 else None
            ),
            branch_texts={
                branch: f"{branch}:{sample_id}" for branch in module.BRANCH_ORDER[1:]
            },
        )
        for index, sample_id in enumerate(ids)
    )
    # One invalid SELECT removes its final resolve from the all-empty baseline.
    summary = module.FlightSummary(states, 527)
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
            (self.path / f"{self.run_id}.trace.jsonl").write_text(
                "trace\n", encoding="utf-8"
            )
            (self.path / f"{self.run_id}.trace-manifest.json").write_text(
                "{}\n", encoding="utf-8"
            )
            return "d" * 64

    def manifest(**kwargs):
        path = kwargs["run_dir"] / f"{module.RUN_ID}.run-manifest.json"
        path.write_text('{"scorers": []}\n', encoding="utf-8")
        return path

    monkeypatch.setattr(module, "TraceSink", Sink)
    monkeypatch.setattr(module, "build_manifest", manifest)
    monkeypatch.setattr(
        module, "verify_bundle", lambda _path: SimpleNamespace(outputs_rows=({},) * 16)
    )
    monkeypatch.setattr(module, "_verified_split", lambda: object())

    sealed = module._seal_branches(
        root=tmp_path,
        context={
            "m0_texts": {sample_id: f"m0:{sample_id}" for sample_id in ids},
            "composed": object(),
        },
        plan=module.execution_plan("attempt-g8b-seal"),
        summary=summary,
        client_summary={
            "trace_manifest_hash": "e" * 64,
            "cost": {"calls_used": 527},
        },
        run_dir=tmp_path / "run",
        agent_trace_path=agent_trace,
        agent_trace_hash="c" * 64,
        session_receipt=tmp_path / "session.json",
    )

    assert set(sealed["branches"]) == set(module.BRANCH_ORDER)
    assert all(Path(row["manifest"]).is_file() for row in sealed["branches"].values())
    assert (tmp_path / "run" / "official-score-jobs.jsonl").read_text().count("\n") == 4
    invalid_outputs = Path(
        sealed["branches"]["DECOMPOSED_SELECT_BIND_RESOLVE"]["outputs"]
    )
    first = json.loads(invalid_outputs.read_text(encoding="utf-8").splitlines()[0])
    assert first["composite_source"]["invalid_stage"] == "DECOMPOSED_SELECT"
