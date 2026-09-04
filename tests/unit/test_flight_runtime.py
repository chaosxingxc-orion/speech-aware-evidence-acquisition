"""Unit tests for ``core.flight.runtime.FlightRuntime`` (C4c).

Every test here drives ``FlightRuntime`` entirely through fakes injected at
every seam (``session_starter``, ``transport_factory``, ``gate_factory``,
``rails_runner``, ``phase_runner``, ``score_batch``, ``packet_promoter``,
``client_factory``, ``manifest_builder``, ``bundle_verifier``,
``bundle_finalizer``, ``runtime_receipt_loader``) -- no model, GPU,
llama-server, embedding, or network contact anywhere in this file. The two
pieces this module deliberately does NOT seam (``core.bundle.git_commit.
require_clean_study_repo`` and the exposure-ledger read) are exercised
against a small, throwaway, local git repository created under ``tmp_path``
-- the same technique ``tests/unit/test_bundle.py``'s own ``bundled_repo``
fixture already uses in this test suite.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Mapping

import pytest

from speech_aware_evidence_acquisition.core.bundle import BundleError
from speech_aware_evidence_acquisition.core.flight.runtime import (
    FlightRuntime,
    FlightRuntimeError,
    FlightServeGeometryMismatchError,
    FlightStageOrderError,
)
from speech_aware_evidence_acquisition.rails.task_adapter import TaskAdapter

# ---------------------------------------------------------------------------
# Minimal fakes. This file never touches a server.
# ---------------------------------------------------------------------------


class _FakeAudioRef:
    def __init__(self, path: str, sha256: str) -> None:
        self.path = path
        self.sha256 = sha256


class _FakeSample:
    def __init__(self, sample_id: str, audio_seconds: float = 2.0) -> None:
        self.sample_id = sample_id
        self.audio_ref = _FakeAudioRef(f"{sample_id}.wav", "0" * 64)
        self.audio_seconds = audio_seconds
        self.media_relpath = f"{sample_id}.wav"


class _FakeAdapter(TaskAdapter):
    """A minimal, fully-fake TaskAdapter -- exercises the real base-class
    defaults (assemble_prompt/score/extract_consumption) without needing any
    real carrier's on-disk layout."""

    SERVING_SLOTS = 2
    SERVING_SLOT_TOKENS = 4096
    SERVING_MAX_TOKENS = 64

    def __init__(self, lock: Mapping[str, object], root: Path) -> None:
        self._lock = lock
        self._root = Path(root)
        self.samples = (_FakeSample("s1"), _FakeSample("s2"))

    def load_split(self, split_id: str):
        return self.samples

    def build_task_contract(self, sample, obs) -> str:
        return "contract"

    def instruction(self, sample) -> str:
        return "instruction"

    def gold(self, sample) -> object:
        return "gold"

    def score_response(self, gold, response: str) -> Mapping[str, object]:
        return {"ok": True}


class _WideFakeAdapter(_FakeAdapter):
    """Same fake, a different serving geometry -- used to exercise geometry
    mismatch/reuse behavior."""

    SERVING_SLOTS = 4
    SERVING_SLOT_TOKENS = 2048
    SERVING_MAX_TOKENS = 32


class _FakeGate:
    def __init__(self) -> None:
        self.calls = 0

    def assert_model_touch_allowed(self, plan) -> None:
        self.calls += 1


class _FakeSession:
    def __init__(self, session_id: str, host: str = "127.0.0.1", port: int = 8080, pid: int = 4242) -> None:
        self.session_id = session_id
        self.host = host
        self.port = port
        self.pid = pid


class _FakeTiming:
    def __init__(self, latency_seconds: float = 0.05) -> None:
        self.latency_seconds = latency_seconds


class _FakeClient:
    def __init__(self, **kwargs: object) -> None:
        self.constructor_kwargs = dict(kwargs)
        self.arm = kwargs.get("arm", "test-arm")
        self.timings = (_FakeTiming(), _FakeTiming())
        self.closed = False

    def close(self) -> Mapping[str, object]:
        self.closed = True
        return {"trace_manifest_hash": "trace-hash", "cost": {"calls_used": 2}, "arm": self.arm}


class _FakeArmResult:
    def __init__(self, sample_id: str) -> None:
        self.sample_id = sample_id
        self.arm = "test-arm"
        self.messages = []
        self.response_text = "resp"
        self.metrics = {}
        self.consumption = None


class _FakeRunSummary:
    def __init__(self, results) -> None:
        self.results = tuple(results)


class _FakePhaseResult:
    def __init__(self, sample_id: str) -> None:
        self.sample_id = sample_id
        self.final_response_text = "resp"
        self.contacts = (object(),)


class _FakePhaseSummary:
    def __init__(self, results, controller_policy_id: str = "phase-direct-only-v1") -> None:
        self.results = tuple(results)
        self.controller_policy_id = controller_policy_id


class _FakeVerified:
    attempt_state = "OPENED"


class _FakeFinalizeResult:
    scores_path = Path("fake-scores.json")
    ledger_markdown_path = Path("fake-ledger.md")
    ledger_json_path = Path("fake-ledger.json")
    attempt_state = "FINALIZED"


def _fake_session_starter(**kwargs: object) -> _FakeSession:
    return _FakeSession(str(kwargs["session_id"]))


def _fake_transport_factory(values, root, *, session, runtime_receipt, runtime_root):
    return object()


def _fake_runtime_receipt_loader(path: Path) -> Mapping[str, object]:
    return {"schema": "fake-runtime-receipt", "gguf_files": []}


def _fake_packet_promoter(*, adapter, data_root, samples, workers):
    return (["packet-1", "packet-2"], {"note": "fake"})


def _fake_payload_binding_factory(**kwargs: object) -> object:
    return object()


def _fake_manifest_builder(**kwargs: object) -> Path:
    run_dir = Path(kwargs["run_dir"])
    run_dir.mkdir(parents=True, exist_ok=True)
    plan = kwargs["plan"]
    path = run_dir / f"{plan.run_id}.run-manifest.json"
    path.write_text(json.dumps({"schema": "fake"}), encoding="utf-8")
    return path


def _fake_bundle_verifier(manifest_path: Path) -> _FakeVerified:
    return _FakeVerified()


def _fake_bundle_finalizer(manifest_path, lock, root, *, repo_root) -> _FakeFinalizeResult:
    return _FakeFinalizeResult()


def _fake_score_batch(jobs, *, output_dir, max_workers, **_kwargs) -> Mapping[str, object]:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    return {"job_count": len(jobs)}


def _fake_rails_runner(**kwargs: object) -> _FakeRunSummary:
    return _FakeRunSummary((_FakeArmResult("s1"), _FakeArmResult("s2")))


def _fake_phase_runner(**kwargs: object):
    return (_FakePhaseSummary((_FakePhaseResult("s1"), _FakePhaseResult("s2"))),)


# ---------------------------------------------------------------------------
# Synthetic repo/config plumbing.
# ---------------------------------------------------------------------------


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo_root, check=True, capture_output=True)


def _git_init_commit(repo_root: Path) -> None:
    _git(repo_root, "init", "-q")
    _git(repo_root, "config", "user.email", "test@example.com")
    _git(repo_root, "config", "user.name", "Test")
    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-q", "-m", "test snapshot")


def _write_json(path: Path, document: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document), encoding="utf-8")


def _write_configs(
    repo_root: Path,
    *,
    arm: str = "test-arm",
    policy: str = "fixed",
    carrier_lock_key: str = "fake-carrier",
    execution_plan_overrides: Mapping[str, object] | None = None,
    execution_plan_present: bool = True,
) -> None:
    _write_json(
        repo_root / "configs" / "model" / "m.json",
        {"model_lock_key": "fake-lock", "transport": "fake"},
    )
    _write_json(
        repo_root / "configs" / "dataset" / "d.json",
        {"carrier_lock_key": carrier_lock_key, "split_id": "fake-split"},
    )
    _write_json(repo_root / "configs" / "baseline" / "b.json", {"arm": arm, "policy": policy})
    experiment_document: dict[str, object] = {}
    if execution_plan_present:
        execution_plan = {
            "execution_profile": "bounded-discovery-probe",
            "split_role": "discovery",
            "planned_model_calls": 10,
            "planned_gpu_hours": 1.0,
            "planned_speech_audio_seconds": 100,
        }
        if execution_plan_overrides:
            execution_plan.update(execution_plan_overrides)
        experiment_document["execution_plan"] = execution_plan
    _write_json(repo_root / "configs" / "experiment" / "e.json", experiment_document)


def _write_exposure_ledger(repo_root: Path, run_id: str, *, consumed: str = "no") -> None:
    content = (
        "| run/experiment id | consumed |\n"
        "| --- | --- |\n"
        f"| {run_id} | {consumed} |\n"
    )
    path = repo_root / "docs" / "exposure-ledger.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_repo(
    tmp_path: Path,
    run_id: str,
    *,
    write_ledger: bool = True,
    ledger_consumed: str = "no",
    **config_kwargs: object,
) -> Path:
    repo_root = tmp_path / "repo"
    _write_configs(repo_root, **config_kwargs)
    if write_ledger:
        _write_exposure_ledger(repo_root, run_id, consumed=ledger_consumed)
    _git_init_commit(repo_root)
    return repo_root


_HAPPY_PATH_KWARGS: dict[str, object] = {
    "session_starter": _fake_session_starter,
    "transport_factory": _fake_transport_factory,
    "runtime_receipt_loader": _fake_runtime_receipt_loader,
    "packet_promoter": _fake_packet_promoter,
    "payload_binding_factory": _fake_payload_binding_factory,
    "carrier_root_resolver": lambda lock, carrier_lock_key, data_root: Path(data_root) / carrier_lock_key,
    "client_factory": _FakeClient,
    "manifest_builder": _fake_manifest_builder,
    "bundle_verifier": _fake_bundle_verifier,
    "bundle_finalizer": _fake_bundle_finalizer,
    "score_batch": _fake_score_batch,
    "rails_runner": _fake_rails_runner,
    "phase_runner": _fake_phase_runner,
}


def _make_runtime(
    tmp_path: Path,
    *,
    run_id: str = "SAEA-TEST-RUN-001",
    attempt_id: str = "attempt-001",
    gate: object | None = None,
    adapter_cls: type = _FakeAdapter,
    happy_path: bool = False,
    repo_root: Path | None = None,
    write_ledger: bool = True,
    ledger_consumed: str = "no",
    config_kwargs: Mapping[str, object] | None = None,
    **runtime_kwargs: object,
) -> FlightRuntime:
    config_kwargs = dict(config_kwargs or {})
    if repo_root is None:
        repo_root = _make_repo(
            tmp_path, run_id, write_ledger=write_ledger, ledger_consumed=ledger_consumed, **config_kwargs
        )
    data_root = tmp_path / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    fake_gate = gate if gate is not None else _FakeGate()
    merged_kwargs: dict[str, object] = {}
    if happy_path:
        merged_kwargs.update(_HAPPY_PATH_KWARGS)
    merged_kwargs.update(runtime_kwargs)
    return FlightRuntime(
        repo_root,
        data_root,
        model="m",
        dataset="d",
        baseline="b",
        experiment="e",
        run_id=run_id,
        attempt_id=attempt_id,
        runtime_root=tmp_path / "runtime",
        adapter_factory=lambda lock, root: adapter_cls(lock, root),
        gate_factory=lambda *a, **kw: fake_gate,
        lock={},
        **merged_kwargs,
    )


# ---------------------------------------------------------------------------
# Stage ordering.
# ---------------------------------------------------------------------------


def test_stages_refuse_to_run_before_preflight(tmp_path):
    runtime = _make_runtime(tmp_path)
    for stage in ("preprocess", "serve", "run_phases", "seal", "score"):
        with pytest.raises(FlightStageOrderError):
            getattr(runtime, stage)()


def test_preflight_refuses_to_run_twice(tmp_path):
    runtime = _make_runtime(tmp_path)
    runtime.preflight()
    with pytest.raises(FlightStageOrderError):
        runtime.preflight()


def test_preprocess_refuses_to_run_before_earlier_stage_but_preflight_succeeds(tmp_path):
    runtime = _make_runtime(tmp_path, happy_path=True)
    receipt = runtime.preflight()
    assert receipt["run_id"] == "SAEA-TEST-RUN-001"
    assert runtime.receipts.has("preflight")
    with pytest.raises(FlightStageOrderError):
        runtime.run_phases()


def test_full_happy_path_runs_every_stage_in_order(tmp_path):
    runtime = _make_runtime(tmp_path, happy_path=True)
    runtime.run_all()
    assert runtime.receipts.completed_stages() == (
        "preflight",
        "preprocess",
        "serve",
        "run_phases",
        "seal",
        "score",
    )
    document = runtime.receipts.as_json()
    assert document["run_id"] == "SAEA-TEST-RUN-001"
    for stage_payload in document["stages"].values():
        assert "stage_hash" in stage_payload


# ---------------------------------------------------------------------------
# preflight() fail-closed behavior.
# ---------------------------------------------------------------------------


def test_preflight_fails_closed_on_missing_exposure_row(tmp_path):
    runtime = _make_runtime(tmp_path, write_ledger=False)
    with pytest.raises(FlightRuntimeError, match="exposure ledger"):
        runtime.preflight()


def test_preflight_fails_closed_on_unregistered_run_id(tmp_path):
    repo_root = _make_repo(tmp_path, "SOME-OTHER-RUN-ID")
    runtime = _make_runtime(tmp_path, run_id="SAEA-TEST-RUN-001", repo_root=repo_root)
    with pytest.raises(FlightRuntimeError, match="no pre-registered exposure row"):
        runtime.preflight()


def test_preflight_fails_closed_on_consumed_exposure_row(tmp_path):
    runtime = _make_runtime(tmp_path, ledger_consumed="yes")
    with pytest.raises(FlightRuntimeError, match="not consumed=no"):
        runtime.preflight()


def test_preflight_fails_closed_on_dirty_study_tree(tmp_path):
    runtime = _make_runtime(tmp_path)
    # Dirty the tree AFTER the fixture's own commit -- require_clean_study_repo
    # must catch this even though the tree was clean when the repo was built.
    (runtime._repo_root / "docs" / "exposure-ledger.md").write_text(
        "| run/experiment id | consumed |\n| --- | --- |\n"
        "| SAEA-TEST-RUN-001 | no |\n| dirtied | yes |\n",
        encoding="utf-8",
    )
    with pytest.raises(BundleError):
        runtime.preflight()


def test_preflight_fails_closed_on_missing_execution_plan_field(tmp_path):
    repo_root = _make_repo(
        tmp_path,
        "SAEA-TEST-RUN-001",
        execution_plan_overrides={"planned_model_calls": None},
    )
    # Remove the field entirely rather than nulling it, by rewriting the file.
    experiment_path = repo_root / "configs" / "experiment" / "e.json"
    document = json.loads(experiment_path.read_text(encoding="utf-8"))
    del document["execution_plan"]["planned_model_calls"]
    experiment_path.write_text(json.dumps(document), encoding="utf-8")
    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-q", "-m", "drop a required field")
    runtime = _make_runtime(tmp_path, repo_root=repo_root)
    with pytest.raises(FlightRuntimeError, match="planned_model_calls"):
        runtime.preflight()


def test_preflight_fails_closed_on_missing_execution_plan_object(tmp_path):
    repo_root = _make_repo(tmp_path, "SAEA-TEST-RUN-001", execution_plan_present=False)
    runtime = _make_runtime(tmp_path, repo_root=repo_root)
    with pytest.raises(FlightRuntimeError, match="execution_plan"):
        runtime.preflight()


def test_preflight_fails_closed_on_prompt_budget_overflow(tmp_path):
    # A token_counter that reports an enormous rendered-token count forces
    # rails.context_budget.assess_context_budget away from ALLOW -- this
    # runtime treats anything short of a clean ALLOW as fail-closed at
    # preflight time (no live compaction mechanism exists yet).
    runtime = _make_runtime(tmp_path, token_counter=lambda payload_bytes: 1_000_000)
    with pytest.raises(FlightRuntimeError, match="prompt budget"):
        runtime.preflight()


# ---------------------------------------------------------------------------
# serve() geometry handling.
# ---------------------------------------------------------------------------


def test_serve_refuses_to_reuse_a_different_geometry(tmp_path):
    narrow_repo = _make_repo(tmp_path / "narrow", "SAEA-TEST-NARROW")
    wide_repo = _make_repo(tmp_path / "wide", "SAEA-TEST-WIDE")

    narrow = _make_runtime(
        tmp_path,
        run_id="SAEA-TEST-NARROW",
        attempt_id="attempt-narrow",
        happy_path=True,
        repo_root=narrow_repo,
        adapter_cls=_FakeAdapter,
    )
    wide = _make_runtime(
        tmp_path,
        run_id="SAEA-TEST-WIDE",
        attempt_id="attempt-wide",
        happy_path=True,
        repo_root=wide_repo,
        adapter_cls=_WideFakeAdapter,
    )

    narrow.preflight()
    narrow.preprocess()
    narrow.serve()
    wide.preflight()
    wide.preprocess()

    with pytest.raises(FlightServeGeometryMismatchError):
        wide.serve(reuse=narrow)


def test_serve_reuses_a_matching_geometry_without_a_fresh_spawn(tmp_path):
    calls = {"starts": 0}

    def _counting_session_starter(**kwargs):
        calls["starts"] += 1
        return _FakeSession(str(kwargs["session_id"]))

    repo_a = _make_repo(tmp_path / "a", "SAEA-TEST-A")
    repo_b = _make_repo(tmp_path / "b", "SAEA-TEST-B")

    flight_a = _make_runtime(
        tmp_path,
        run_id="SAEA-TEST-A",
        attempt_id="attempt-a",
        happy_path=True,
        repo_root=repo_a,
        session_starter=_counting_session_starter,
    )
    flight_b = _make_runtime(
        tmp_path,
        run_id="SAEA-TEST-B",
        attempt_id="attempt-b",
        happy_path=True,
        repo_root=repo_b,
        session_starter=_counting_session_starter,
    )

    flight_a.preflight()
    flight_a.preprocess()
    flight_a.serve()
    flight_b.preflight()
    flight_b.preprocess()
    receipt = flight_b.serve(reuse=flight_a)

    assert calls["starts"] == 1
    assert receipt["reused"] is True
    assert receipt["reused_from_attempt_id"] == "attempt-a"


# ---------------------------------------------------------------------------
# run_phases() routing.
# ---------------------------------------------------------------------------


def test_run_phases_routes_fixed_policy_through_rails_runner(tmp_path):
    calls = {"rails_runner": 0, "phase_runner": 0}

    def _rails_runner(**kwargs):
        calls["rails_runner"] += 1
        return _fake_rails_runner(**kwargs)

    def _phase_runner(**kwargs):
        calls["phase_runner"] += 1
        return _fake_phase_runner(**kwargs)

    runtime = _make_runtime(
        tmp_path,
        happy_path=True,
        config_kwargs={"policy": "fixed"},
        rails_runner=_rails_runner,
        phase_runner=_phase_runner,
    )
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    receipt = runtime.run_phases()

    assert calls == {"rails_runner": 1, "phase_runner": 0}
    assert receipt["policy_kind"] == "direct"
    assert receipt["contact_count"] == 2


def test_run_phases_routes_phase_program_policy_through_phase_runner(tmp_path):
    calls = {"rails_runner": 0, "phase_runner": 0}

    def _rails_runner(**kwargs):
        calls["rails_runner"] += 1
        return _fake_rails_runner(**kwargs)

    def _phase_runner(**kwargs):
        calls["phase_runner"] += 1
        return _fake_phase_runner(**kwargs)

    runtime = _make_runtime(
        tmp_path,
        happy_path=True,
        config_kwargs={"policy": "phase-direct-only-v1"},
        rails_runner=_rails_runner,
        phase_runner=_phase_runner,
    )
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    runtime.bind_phase_program_material(
        knowledge_snapshot="fake-snapshot",
        speech_packet_bindings={},
        material_for_phase=lambda *a, **kw: None,
    )
    receipt = runtime.run_phases()

    assert calls == {"rails_runner": 0, "phase_runner": 1}
    assert receipt["policy_kind"] == "phase-program"
    assert receipt["contact_count"] == 2


def test_run_phases_refuses_a_phase_program_without_bound_material(tmp_path):
    runtime = _make_runtime(
        tmp_path,
        happy_path=True,
        config_kwargs={"policy": "phase-direct-only-v1"},
    )
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    with pytest.raises(FlightRuntimeError, match="bind_phase_program_material"):
        runtime.run_phases()


# ---------------------------------------------------------------------------
# seal() refuses twice; abort().
# ---------------------------------------------------------------------------


def test_seal_refuses_to_run_twice(tmp_path):
    runtime = _make_runtime(tmp_path, happy_path=True)
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    runtime.run_phases()
    runtime.seal()
    with pytest.raises(FlightStageOrderError):
        runtime.seal()


def test_abort_marks_an_opened_attempt_aborted(tmp_path):
    runtime = _make_runtime(tmp_path, happy_path=True)
    runtime.preflight()
    assert runtime.abort("test abort") is True
    # A second abort on an already-terminal attempt is a documented no-op.
    assert runtime.abort("test abort again") is False


# ---------------------------------------------------------------------------
# Identity-shaped test: FrozenCoreClient kwargs match the A0 launcher shape.
# ---------------------------------------------------------------------------


def test_frozen_core_client_kwargs_matches_the_a0_launcher_keyword_set(tmp_path):
    """docs/checks/speech-aware-evidence-acquisition/2026-08-18-pa2t-a0-flight/
    launcher/launch_pa2t_a0.py (lines ~322-329) constructs::

        FrozenCoreClient(
            plan=plan, gate=gate, transport=transport, run_dir=run_dir,
            binding=binding, request_id_prefix="pa2t",
        )

    for its direct ``bare-core`` flight, relying on ``FrozenCoreClient``'s own
    ``arm`` DEFAULT (``DEFAULT_RAILS_ARM``) rather than naming it. This
    runtime always names ``arm`` explicitly (it is config-driven, not a
    hidden default) -- the one intentional divergence. After removing every
    seam-object-valued key (``plan``/``gate``/``transport``/``run_dir``/
    ``binding``), the remaining keyword set must be exactly
    ``{"arm", "request_id_prefix"}`` for the ``bare-core`` arm (no
    ``tool_schemas``, no speech-feature-query fields -- ``bare-core`` declares
    none of them)."""

    runtime = _make_runtime(
        tmp_path,
        happy_path=True,
        config_kwargs={"arm": "bare-core", "policy": "fixed"},
    )
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    kwargs = runtime.frozen_core_client_kwargs()

    seam_keys = {"plan", "gate", "transport", "run_dir", "binding"}
    non_seam_keys = set(kwargs) - seam_keys
    assert non_seam_keys == {"arm", "request_id_prefix"}
    assert kwargs["arm"] == "bare-core"
    assert isinstance(kwargs["request_id_prefix"], str) and kwargs["request_id_prefix"]
    assert seam_keys <= set(kwargs)
