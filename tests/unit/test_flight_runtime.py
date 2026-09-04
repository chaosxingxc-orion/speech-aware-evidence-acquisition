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

import hashlib
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
from speech_aware_evidence_acquisition.e0.d2_leakage import ARM_VISIBLE_FIELDS
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
    """Mirrors rails.core_client.RequestTiming, including the per-request
    identity hashes core.bundle.verify_bundle requires an outputs row to
    carry (2026-09-04)."""

    def __init__(
        self,
        latency_seconds: float = 0.05,
        sample_id: str = "s1",
        request_id: str = "req-0001",
    ) -> None:
        self.latency_seconds = latency_seconds
        self.sample_id = sample_id
        self.request_id = request_id
        self.request_sha256 = "a" * 64
        self.response_sha256 = "b" * 64
        self.response_text_sha256 = hashlib.sha256(b"resp").hexdigest()


class _FakeClient:
    def __init__(self, **kwargs: object) -> None:
        self.constructor_kwargs = dict(kwargs)
        self.arm = kwargs.get("arm", "test-arm")
        self.timings = (
            _FakeTiming(sample_id="s1", request_id="req-0001"),
            _FakeTiming(sample_id="s2", request_id="req-0002"),
        )
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


def _fake_session_stopper(session, **kwargs) -> Mapping[str, object]:
    # Faked for the same reason every other seam is (module docstring): the
    # real core.session.stop_session re-verifies a live process image and
    # socket ownership, which a _FakeSession has none of.
    return {"termination_signal": "SIGTERM", "forced": False}


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
    model_extra: Mapping[str, object] | None = None,
    baseline_extra: Mapping[str, object] | None = None,
) -> None:
    model_document: dict[str, object] = {"model_lock_key": "fake-lock", "transport": "fake"}
    model_document.update(dict(model_extra or {}))
    _write_json(repo_root / "configs" / "model" / "m.json", model_document)
    _write_json(
        repo_root / "configs" / "dataset" / "d.json",
        {"carrier_lock_key": carrier_lock_key, "split_id": "fake-split"},
    )
    baseline_document: dict[str, object] = {"arm": arm, "policy": policy}
    baseline_document.update(dict(baseline_extra or {}))
    _write_json(repo_root / "configs" / "baseline" / "b.json", baseline_document)
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
    "session_stopper": _fake_session_stopper,
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


def test_preflight_checks_attempt_availability_without_consuming_it(tmp_path):
    """preflight must NOT open the attempt: core.model.adapter.
    FrozenCoreAdapter -- the only model request path -- opens the same
    (run_id, attempt_id) pair when run_phases builds the client, and the
    pair is a one-time key. Double-opening it made every real flight die at
    client construction."""

    from speech_aware_evidence_acquisition.core.attempts.store import AttemptStore

    runtime = _make_runtime(tmp_path, happy_path=True)
    runtime.preflight()

    store = AttemptStore(tmp_path / "data" / "attempts")
    path = store.handle("SAEA-TEST-RUN-001", "attempt-001").path
    assert not path.exists()
    # Nothing was reserved, so there is nothing to abort yet.
    assert runtime.abort("nothing was ever opened") is False


def test_preflight_refuses_an_attempt_id_that_was_already_used(tmp_path):
    from speech_aware_evidence_acquisition.core.attempts.store import AttemptStore

    repo_root = _make_repo(tmp_path, "SAEA-TEST-RUN-001")
    store = AttemptStore(tmp_path / "data" / "attempts")
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)
    store.open_attempt(
        "SAEA-TEST-RUN-001",
        "attempt-001",
        carrier_lock_key="fake-carrier",
        reserved_calls=10,
        reserved_audio_seconds=100.0,
    )
    runtime = _make_runtime(tmp_path, happy_path=True, repo_root=repo_root)
    with pytest.raises(FlightRuntimeError, match="one-time key"):
        runtime.preflight()


def test_abort_marks_an_attempt_the_adapter_opened_aborted(tmp_path):
    """The attempt an adapter reserved is still abortable through the
    runtime -- the failure path core.attempts.AttemptStore.abort_if_opened
    documents."""

    from speech_aware_evidence_acquisition.core.attempts.store import AttemptStore

    runtime = _make_runtime(tmp_path, happy_path=True)
    runtime.preflight()
    # Stand in for FrozenCoreAdapter's own one-time reservation.
    AttemptStore(tmp_path / "data" / "attempts").open_attempt(
        "SAEA-TEST-RUN-001",
        "attempt-001",
        carrier_lock_key="fake-carrier",
        reserved_calls=10,
        reserved_audio_seconds=100.0,
    )
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


# ---------------------------------------------------------------------------
# Phase 2a: the four config-driven seam defaults, and the packet direct arm.
# Every test below still runs entirely through fakes -- no server, no GPU, no
# real promotion, no network.
# ---------------------------------------------------------------------------


from speech_aware_evidence_acquisition.core.flight import runtime as _runtime_module  # noqa: E402
from speech_aware_evidence_acquisition.core.flight.runtime import (  # noqa: E402
    arm_uses_speech_feature_packets,
    merge_server_args,
    packet_id_for_sample,
    sample_id_for_packet,
)

_PROMOTION_DIR = "feature-root"
_LEGACY_DIR = "legacy-cache"
_BUILTIN_PROMOTER = _runtime_module._default_packet_promoter


class _FakePacket:
    def __init__(self, packet_id: str, packet_sha256: str) -> None:
        self.packet_id = packet_id
        self.packet_sha256 = packet_sha256


def _write_promotion_receipt(
    tmp_path: Path,
    *,
    packet_ids=("s1", "s2"),
    feature_root: str | None = None,
) -> Path:
    path = tmp_path / "promotion.json"
    _write_json(
        path,
        {
            "schema": "saea-a2t-speech-packet-promotion-receipt-v1",
            "feature_root": feature_root or str(tmp_path / _PROMOTION_DIR),
            "legacy_cache_dir": str(tmp_path / _LEGACY_DIR),
            "runtime_receipt_sha256": "e" * 64,
            "packets": [
                {
                    "packet_id": packet_id,
                    "packet_sha256": f"{packet_id}-sha",
                    "decoder_gguf_sha256": "d" * 64,
                    "mmproj_sha256": "m" * 64,
                }
                for packet_id in packet_ids
            ],
        },
    )
    return path


def _packet_config_kwargs(
    tmp_path: Path,
    promotion_receipt: Path,
    *,
    arm: str = "speech-feature-query",
    speech_feature_root: str | None = None,
) -> dict[str, object]:
    return {
        "arm": arm,
        "policy": "fixed",
        "model_extra": {
            "speech_feature_root": speech_feature_root or str(tmp_path / _PROMOTION_DIR)
        },
        "baseline_extra": {
            "speech_packet_promotion_receipt": str(promotion_receipt),
            "speech_feature_key_representation_id": "key-rep-v1",
            "speech_feature_matcher_policy_id": "matcher-v1",
        },
    }


# -- (a) serve() preserves the fragment's server_args ----------------------


def test_merge_server_args_overrides_only_np_and_c() -> None:
    merged = merge_server_args(
        ["-c", "65536", "-np", "2", "-fa", "on", "-ngl", "999", "-ctk", "q8_0"],
        slots=3,
        context_tokens=49152,
    )
    assert merged == ["-c", "49152", "-np", "3", "-fa", "on", "-ngl", "999", "-ctk", "q8_0"]


def test_merge_server_args_appends_missing_flags_and_keeps_the_rest() -> None:
    assert merge_server_args(["-ngl", "999"], slots=2, context_tokens=4096) == [
        "-ngl",
        "999",
        "-np",
        "2",
        "-c",
        "4096",
    ]


def test_merge_server_args_fails_closed_on_bad_shapes() -> None:
    with pytest.raises(FlightRuntimeError, match="list of strings"):
        merge_server_args("-ngl 999", slots=1, context_tokens=1)
    with pytest.raises(FlightRuntimeError, match="no value"):
        merge_server_args(["-ngl", "999", "-np"], slots=1, context_tokens=1)


def test_serve_passes_the_whole_fragment_argv_role_and_model_root(tmp_path):
    captured: dict[str, object] = {}

    def _capturing_session_starter(**kwargs):
        captured.update(kwargs)
        return _FakeSession(str(kwargs["session_id"]))

    def _receipt_loader(path: Path):
        return {"schema": "fake", "gguf_files": [], "role": "inference"}

    runtime = _make_runtime(
        tmp_path,
        happy_path=True,
        session_starter=_capturing_session_starter,
        runtime_receipt_loader=_receipt_loader,
        config_kwargs={
            "model_extra": {
                "server_args": ["-c", "1", "-np", "1", "-ngl", "999", "-fa", "on"],
                "model_materialization_root": "/home/chao",
            }
        },
    )
    runtime.preflight()
    runtime.preprocess()
    receipt = runtime.serve()

    # -ngl/-fa survive; -np/-c come from the adapter geometry (2 x 4096).
    assert captured["extra_argv"] == ["-c", "8192", "-np", "2", "-ngl", "999", "-fa", "on"]
    assert captured["role"] == "inference"
    assert captured["model_root"] == Path("/home/chao")
    assert receipt["session_role"] == "inference"
    assert receipt["model_root"] == "/home/chao"


def test_serve_defaults_role_to_legacy_when_the_receipt_declares_none(tmp_path):
    captured: dict[str, object] = {}

    def _capturing_session_starter(**kwargs):
        captured.update(kwargs)
        return _FakeSession(str(kwargs["session_id"]))

    runtime = _make_runtime(
        tmp_path, happy_path=True, session_starter=_capturing_session_starter
    )
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()

    assert captured["role"] == "legacy"
    assert captured["model_root"] is None
    # No server_args in the fragment: the derived pair is still appended.
    assert captured["extra_argv"] == ["-np", "2", "-c", "8192"]


# -- (b) speech-feature client bindings ------------------------------------


def test_arm_classification_reads_the_d2_field_set() -> None:
    assert arm_uses_speech_feature_packets("speech-feature-query") is True
    assert arm_uses_speech_feature_packets("speech-feature-query-native-tools") is True
    assert arm_uses_speech_feature_packets("bare-core") is False
    assert arm_uses_speech_feature_packets("bare-core-native-tools") is False
    # An arm this module has never heard of answers False rather than raising;
    # FrozenCoreClient owns the "unknown D2 arm" refusal.
    assert arm_uses_speech_feature_packets("not-an-arm") is False


def test_packet_id_convention_round_trips() -> None:
    assert packet_id_for_sample("tier1_direct:000045") == "tier1_direct/000045"
    assert sample_id_for_packet("tier1_direct/000045") == "tier1_direct:000045"


def test_client_kwargs_carry_speech_feature_bindings_for_a_packet_arm(tmp_path):
    promotion = _write_promotion_receipt(tmp_path)
    runtime = _make_runtime(
        tmp_path,
        happy_path=True,
        config_kwargs=_packet_config_kwargs(tmp_path, promotion),
    )
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    kwargs = runtime.frozen_core_client_kwargs()

    assert kwargs["speech_feature_root"] == tmp_path / _PROMOTION_DIR
    assert kwargs["speech_packet_bindings"] == {
        "s1": {"packet_id": "s1", "sha256": "s1-sha"},
        "s2": {"packet_id": "s2", "sha256": "s2-sha"},
    }


def test_client_kwargs_omit_speech_feature_bindings_for_a_raw_arm(tmp_path):
    runtime = _make_runtime(
        tmp_path,
        happy_path=True,
        config_kwargs={"arm": "bare-core", "policy": "fixed"},
    )
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    kwargs = runtime.frozen_core_client_kwargs()

    assert "speech_feature_root" not in kwargs
    assert "speech_packet_bindings" not in kwargs


def test_speech_packet_bindings_fail_closed_on_an_unpromoted_sample(tmp_path):
    promotion = _write_promotion_receipt(tmp_path, packet_ids=("s1",))
    runtime = _make_runtime(
        tmp_path,
        happy_path=True,
        config_kwargs=_packet_config_kwargs(tmp_path, promotion),
    )
    runtime.preflight()
    with pytest.raises(FlightRuntimeError, match="no promoted packet"):
        runtime.speech_packet_bindings()


def test_speech_feature_root_must_agree_with_the_promotion_receipt(tmp_path):
    promotion = _write_promotion_receipt(tmp_path)
    runtime = _make_runtime(
        tmp_path,
        happy_path=True,
        config_kwargs=_packet_config_kwargs(
            tmp_path, promotion, speech_feature_root=str(tmp_path / "somewhere-else")
        ),
    )
    runtime.preflight()
    with pytest.raises(FlightRuntimeError, match="disagrees with the promotion receipt"):
        runtime._speech_feature_root()


def test_packet_arm_without_a_promotion_receipt_fails_closed(tmp_path):
    runtime = _make_runtime(
        tmp_path,
        happy_path=True,
        config_kwargs={
            "arm": "speech-feature-query",
            "policy": "fixed",
            "baseline_extra": {
                "speech_feature_key_representation_id": "k",
                "speech_feature_matcher_policy_id": "m",
            },
        },
    )
    runtime.preflight()
    with pytest.raises(FlightRuntimeError, match="speech_packet_promotion_receipt"):
        runtime.speech_packet_bindings()


# -- (c) the default tool-schema resolver ----------------------------------


class _FakeFillRegistry:
    def __init__(self, schemas) -> None:
        self.schemas = schemas
        self.resolved: list[str] = []

    def resolve(self, name: str):
        self.resolved.append(name)
        return lambda lock, data_root: self.schemas


def test_default_tool_schema_resolver_goes_through_the_policy_registry(
    tmp_path, monkeypatch
):
    schemas = [{"type": "function", "function": {"name": "t"}}]
    registry = _FakeFillRegistry(schemas)
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.policies.TOOL_SCHEMA_FILLS", registry
    )
    runtime = _make_runtime(
        tmp_path,
        happy_path=True,
        config_kwargs={
            "arm": "bare-core-native-tools",
            "policy": "fixed",
            "baseline_extra": {"tool_schema_fill": "audio2tool-openai-tools"},
        },
    )
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    kwargs = runtime.frozen_core_client_kwargs()

    assert kwargs["tool_schemas"] == schemas
    assert registry.resolved == ["audio2tool-openai-tools"]


def test_native_tools_arm_without_a_fill_still_fails_closed(tmp_path):
    runtime = _make_runtime(
        tmp_path,
        happy_path=True,
        config_kwargs={"arm": "bare-core-native-tools", "policy": "fixed"},
    )
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    with pytest.raises(FlightRuntimeError, match="tool_schema_fill"):
        runtime.frozen_core_client_kwargs()


# -- (d) the default packet promoter ---------------------------------------


def test_default_promoter_promotes_nothing_for_a_raw_audio_arm(tmp_path):
    runtime = _make_runtime(
        tmp_path,
        happy_path=True,
        packet_promoter=_BUILTIN_PROMOTER,
        config_kwargs={"arm": "bare-core", "policy": "fixed"},
    )
    runtime.preflight()
    receipt = runtime.preprocess()

    assert receipt["packet_count"] == 0
    assert receipt["promoter_meta"]["packets_required"] is False
    assert receipt["promoter_meta"]["audio_path"] == "raw-audio-mmproj"
    assert receipt["packets_per_second"] >= 0


def test_installing_the_sentinel_directly_still_refuses(tmp_path):
    runtime = _make_runtime(
        tmp_path,
        happy_path=True,
        config_kwargs={"arm": "bare-core", "policy": "fixed"},
    )
    runtime._packet_promoter = _BUILTIN_PROMOTER
    runtime.preflight()
    with pytest.raises(FlightRuntimeError, match="fail-closed sentinel"):
        runtime.preprocess()


def test_default_promoter_materializes_the_registered_packets(tmp_path, monkeypatch):
    promotion = _write_promotion_receipt(tmp_path)
    calls: dict[str, object] = {}

    def _fake_materialize(**kwargs):
        calls.update(kwargs)
        return (_FakePacket("s1", "s1-sha"), _FakePacket("s2", "s2-sha"))

    monkeypatch.setattr(
        _runtime_module,
        "materialize_legacy_cached_speech_feature_packets",
        _fake_materialize,
    )
    runtime = _make_runtime(
        tmp_path,
        happy_path=True,
        packet_promoter=_BUILTIN_PROMOTER,
        config_kwargs=_packet_config_kwargs(tmp_path, promotion),
    )
    runtime.preflight()
    receipt = runtime.preprocess(workers=5)

    assert receipt["packet_count"] == 2
    assert receipt["promoter_meta"]["packets_required"] is True
    assert receipt["promoter_meta"]["feature_root"] == str(tmp_path / _PROMOTION_DIR)
    assert receipt["promoter_meta"]["promotion_receipt"] == str(promotion)
    assert calls["feature_root"] == tmp_path / _PROMOTION_DIR
    assert calls["legacy_cache_dir"] == tmp_path / _LEGACY_DIR
    assert calls["encoder_receipt_sha256"] == "e" * 64
    assert calls["decoder_gguf_sha256"] == "d" * 64
    assert calls["mmproj_sha256"] == "m" * 64
    assert calls["workers"] == 5
    assert [binding["packet_id"] for binding in calls["bindings"]] == ["s1", "s2"]


def test_default_promoter_refuses_a_packet_the_receipt_does_not_pin(tmp_path, monkeypatch):
    promotion = _write_promotion_receipt(tmp_path)

    def _fake_materialize(**kwargs):
        return (_FakePacket("s1", "s1-sha"), _FakePacket("s2", "TAMPERED"))

    monkeypatch.setattr(
        _runtime_module,
        "materialize_legacy_cached_speech_feature_packets",
        _fake_materialize,
    )
    runtime = _make_runtime(
        tmp_path,
        happy_path=True,
        packet_promoter=_BUILTIN_PROMOTER,
        config_kwargs=_packet_config_kwargs(tmp_path, promotion),
    )
    runtime.preflight()
    with pytest.raises(FlightRuntimeError, match="does not match the registered"):
        runtime.preprocess()


# -- blocker 2: the one-contact packet direct arm --------------------------


class _RecordingClient(_FakeClient):
    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.completions: list[dict[str, object]] = []

    def complete(self, messages, **kwargs):
        self.completions.append({"messages": list(messages), **kwargs})
        return "[]"


def test_run_phases_carries_the_packet_arm_with_one_contact_per_sample(tmp_path):
    promotion = _write_promotion_receipt(tmp_path)
    rails_calls = {"count": 0}

    def _rails_runner(**kwargs):
        rails_calls["count"] += 1
        return _fake_rails_runner(**kwargs)

    runtime = _make_runtime(
        tmp_path,
        happy_path=True,
        client_factory=_RecordingClient,
        rails_runner=_rails_runner,
        config_kwargs=_packet_config_kwargs(tmp_path, promotion),
    )
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    receipt = runtime.run_phases()

    assert receipt["policy_kind"] == "direct-speech-feature-packets"
    assert receipt["contact_count"] == 2
    assert rails_calls["count"] == 0

    client = runtime._client
    assert len(client.completions) == 2
    first = client.completions[0]
    assert first["speech_feature_sample_id"] == "s1"
    assert first["key_representation_id"] == "key-rep-v1"
    assert first["matcher_policy_id"] == "matcher-v1"
    system, user = first["messages"]
    assert system == {"role": "system", "content": "instruction"}
    parts = user["content"]
    assert [part["type"] for part in parts] == ["input_speech_features"]
    assert parts[0]["speech_features"] == {
        "packet_id": "s1",
        "sha256": "s1-sha",
        "role": "query",
    }
    assert sum(part["speech_features"]["role"] == "query" for part in parts) == 1


def test_packet_arm_requires_both_trace_ids(tmp_path):
    promotion = _write_promotion_receipt(tmp_path)
    config_kwargs = _packet_config_kwargs(tmp_path, promotion)
    del config_kwargs["baseline_extra"]["speech_feature_matcher_policy_id"]
    runtime = _make_runtime(
        tmp_path,
        happy_path=True,
        client_factory=_RecordingClient,
        config_kwargs=config_kwargs,
    )
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    with pytest.raises(FlightRuntimeError, match="speech_feature_matcher_policy_id"):
        runtime.run_phases()


def test_raw_audio_fixed_policy_still_routes_through_rails_runner(tmp_path):
    calls = {"count": 0}

    def _rails_runner(**kwargs):
        calls["count"] += 1
        return _fake_rails_runner(**kwargs)

    runtime = _make_runtime(
        tmp_path,
        happy_path=True,
        rails_runner=_rails_runner,
        config_kwargs={"arm": "bare-core", "policy": "fixed"},
    )
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    receipt = runtime.run_phases()

    assert receipt["policy_kind"] == "direct"
    assert calls["count"] == 1


# -- Phase 2b: serve() finally has a counterpart ---------------------------


def test_stop_serving_stops_the_session_this_flight_started(tmp_path):
    stopped: list[object] = []

    def _stopper(session, **kwargs):
        stopped.append((session, kwargs))
        return {"termination_signal": "SIGTERM", "forced": False}

    runtime = _make_runtime(tmp_path, happy_path=True, session_stopper=_stopper)
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    receipt = runtime.stop_serving()

    assert receipt == {"termination_signal": "SIGTERM", "forced": False}
    assert len(stopped) == 1
    session, kwargs = stopped[0]
    assert session.session_id.startswith("SAEA-TEST-RUN-001")
    assert kwargs["force_after_timeout"] is True
    assert str(kwargs["receipt_path"]).endswith(".session-stop-receipt.json")
    # Idempotent: a second call stops nothing.
    assert runtime.stop_serving() is None
    assert len(stopped) == 1


def test_stop_serving_is_a_noop_before_serve(tmp_path):
    stopped: list[object] = []

    def _stopper(session, **kwargs):
        stopped.append(session)
        return {}

    runtime = _make_runtime(tmp_path, happy_path=True, session_stopper=_stopper)
    assert runtime.stop_serving() is None
    runtime.preflight()
    runtime.preprocess()
    assert runtime.stop_serving() is None
    assert stopped == []


def test_stop_serving_never_stops_a_reused_server(tmp_path):
    stopped: list[str] = []

    def _stopper(session, **kwargs):
        stopped.append(session.session_id)
        return {"termination_signal": "SIGTERM"}

    repo_a = _make_repo(tmp_path / "a", "SAEA-TEST-A")
    repo_b = _make_repo(tmp_path / "b", "SAEA-TEST-B")
    owner = _make_runtime(
        tmp_path,
        run_id="SAEA-TEST-A",
        attempt_id="attempt-a",
        happy_path=True,
        repo_root=repo_a,
        session_stopper=_stopper,
    )
    borrower = _make_runtime(
        tmp_path,
        run_id="SAEA-TEST-B",
        attempt_id="attempt-b",
        happy_path=True,
        repo_root=repo_b,
        session_stopper=_stopper,
    )
    owner.preflight()
    owner.preprocess()
    owner.serve()
    borrower.preflight()
    borrower.preprocess()
    borrower.serve(reuse=owner)

    # The borrower must not stop a server it does not own.
    assert borrower.stop_serving() is None
    assert stopped == []
    # The owner still can.
    assert owner.stop_serving() is not None
    assert len(stopped) == 1


# ---------------------------------------------------------------------------
# Phase 2d: wire_check() -- the contact-free wiring proof.
# ---------------------------------------------------------------------------


from speech_aware_evidence_acquisition.core.flight.runtime import (  # noqa: E402
    WIRE_CHECK_RUN_ID_PREFIX,
    WireCheckGate,
    WireCheckTransport,
)


class _TransportDrivingClient(_FakeClient):
    """A client double that actually reaches the transport, so wire_check's
    payload assertions have something to inspect. It emits the arm's own
    declared field set, which is what the real FrozenCoreAdapter enforces."""

    drop_key: str | None = None
    force_id_slot: object = 0

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._transport = kwargs["transport"]
        self._arm_fields = ARM_VISIBLE_FIELDS.get(str(kwargs.get("arm")), ())
        self._tool_schemas = kwargs.get("tool_schemas")

    def complete(self, messages, **_kwargs):
        payload = {field: "x" for field in self._arm_fields}
        payload["decoding_params"] = {"id_slot": type(self).force_id_slot}
        if "tool_schemas" in payload:
            payload["tool_schemas"] = list(self._tool_schemas or [{"t": 1}])
        if type(self).drop_key is not None:
            payload.pop(type(self).drop_key, None)
        self._transport(json.dumps(payload).encode("utf-8"))
        return "[]"


def _calling_rails_runner(**kwargs):
    """Mirrors rails.runner._run_one_arm: one complete() per sample. The
    plain _fake_rails_runner never calls the client at all, so a wire check
    driven by it would see zero requests reach the transport."""

    adapter = kwargs["adapter"]
    client = kwargs["core_client"]
    results = []
    for sample in adapter.load_split(kwargs["split_id"]):
        client.complete(
            adapter.assemble_prompt(sample, None),
            decoding_params=kwargs.get("decoding_params"),
        )
        results.append(_FakeArmResult(sample.sample_id))
    return _FakeRunSummary(results)


def _wire_runtime(tmp_path, **kwargs):
    merged = {
        "happy_path": True,
        "client_factory": _TransportDrivingClient,
        "rails_runner": _calling_rails_runner,
        "config_kwargs": {"arm": "bare-core", "policy": "fixed"},
    }
    merged.update(kwargs)
    return _make_runtime(tmp_path, **merged)


def test_wire_check_returns_a_zero_contact_receipt(tmp_path):
    runtime = _wire_runtime(tmp_path)
    receipt = runtime.wire_check(seal_and_score=False)

    assert receipt["schema"] == "saea-flight-wire-check-v1"
    assert receipt["model_contacts"] == 0
    assert receipt["arm"] == "bare-core"
    assert receipt["native_tools_arm"] is False
    assert receipt["tool_schemas_count"] == 0
    assert receipt["contact_count"] == receipt["sample_count"] == 2
    assert receipt["payload_keys"] == sorted(ARM_VISIBLE_FIELDS["bare-core"])
    assert receipt["payload_keys_equal_arm_visible_fields"] is True
    assert receipt["id_slot"] == 0
    assert len(receipt["request_body_sha256"]) == 2
    assert receipt["seal_and_score"]["status"] == "SKIPPED"


def test_wire_check_never_touches_the_registered_run_id(tmp_path):
    runtime = _wire_runtime(tmp_path)
    receipt = runtime.wire_check(seal_and_score=False)

    assert receipt["flight_run_id"] == "SAEA-TEST-RUN-001"
    assert receipt["wire_check_run_id"].startswith(
        WIRE_CHECK_RUN_ID_PREFIX + "SAEA-TEST-RUN-001"
    )
    assert receipt["wire_check_run_id"] != "SAEA-TEST-RUN-001"
    assert receipt["attempt_id"].startswith("attempt-wire-check-")
    # Nothing was written under the registered run's own attempt tree.
    from speech_aware_evidence_acquisition.core.attempts.store import AttemptStore

    store = AttemptStore(tmp_path / "data" / "attempts")
    assert not store.handle("SAEA-TEST-RUN-001", "attempt-001").path.exists()


def test_wire_check_run_ids_are_unique_across_invocations(tmp_path):
    """Attempt budget is run-cumulative, so a fixed wire-check run id would
    let one cell's contacts exhaust the next cell's budget."""

    clock = {"t": 1000.0}

    def _tick():
        clock["t"] += 1.0
        return clock["t"]

    first = _wire_runtime(tmp_path / "a", clock=_tick).wire_check(seal_and_score=False)
    second = _wire_runtime(tmp_path / "b", clock=_tick).wire_check(seal_and_score=False)
    assert first["wire_check_run_id"] != second["wire_check_run_id"]


def test_wire_check_carries_tool_schemas_only_for_a_native_arm(tmp_path):
    runtime = _wire_runtime(
        tmp_path,
        config_kwargs={
            "arm": "bare-core-native-tools",
            "policy": "fixed",
            "baseline_extra": {"tool_schema_fill": "audio2tool-openai-tools"},
        },
        tool_schema_resolver=lambda lock, root, name: [
            {"type": "function", "function": {"name": "t"}}
        ],
    )
    receipt = runtime.wire_check(seal_and_score=False)

    assert receipt["native_tools_arm"] is True
    assert receipt["tool_schemas_count"] == 1
    assert "tool_schemas" in receipt["payload_keys"]


def test_wire_check_refuses_a_payload_that_misses_a_declared_field(tmp_path):
    class _Dropping(_TransportDrivingClient):
        drop_key = "task_instruction"

    runtime = _wire_runtime(tmp_path, client_factory=_Dropping)
    with pytest.raises(FlightRuntimeError, match="payload keys differ"):
        runtime.wire_check(seal_and_score=False)


def test_wire_check_refuses_an_unresolved_id_slot(tmp_path):
    class _Sentinel(_TransportDrivingClient):
        force_id_slot = "per-sample"

    runtime = _wire_runtime(tmp_path, client_factory=_Sentinel)
    with pytest.raises(FlightRuntimeError, match="not an integer"):
        runtime.wire_check(seal_and_score=False)


def test_wire_check_seals_and_scores_when_the_links_are_available(tmp_path):
    runtime = _wire_runtime(tmp_path)
    receipt = runtime.wire_check(seal_and_score=True)

    seal = receipt["seal_and_score"]
    assert seal["status"] == "OK"
    assert seal["outputs_row_count"] == 2
    assert seal["manifest_sha256"]
    assert seal["score_result"] == {"job_count": 1}


def test_wire_check_records_a_refused_seal_instead_of_raising(tmp_path):
    def _refusing_manifest_builder(**_kwargs):
        raise BundleError("study repo has uncommitted changes inside the load-bearing surface")

    runtime = _wire_runtime(tmp_path, manifest_builder=_refusing_manifest_builder)
    receipt = runtime.wire_check(seal_and_score=True)

    seal = receipt["seal_and_score"]
    assert seal["status"] == "REFUSED"
    assert "uncommitted changes" in seal["reason"]
    # The client half still reported its findings.
    assert receipt["contact_count"] == 2
    assert receipt["model_contacts"] == 0


def test_wire_check_doubles_never_open_a_socket(tmp_path):
    gate = WireCheckGate()
    transport = WireCheckTransport()
    plan = object()
    assert gate.assert_model_touch_allowed(plan) == "0" * 64
    assert gate.checked_plans == [plan]
    body = transport(json.dumps({"a": 1}).encode("utf-8"))
    assert transport.payloads == [{"a": 1}]
    assert json.loads(body.decode("utf-8"))["text"]
    with pytest.raises(FlightRuntimeError, match="bytes"):
        transport("not bytes")


# ---------------------------------------------------------------------------
# Phase 2e: outputs rows must satisfy the bundle contract.
#
# core.bundle.verify_bundle refuses any outputs row missing one of
# core.bundle.outputs._REQUIRED_OUTPUTS_FIELDS, and binds each row's
# carrier_lock_key/arm to the manifest while re-deriving
# response_text_sha256 from the row's own text. seal() used to write a loose
# diagnostic dict instead, so a sealed rails flight could never verify --
# and the refusal landed AFTER every contact had been spent.
# ---------------------------------------------------------------------------


from speech_aware_evidence_acquisition.core.bundle.outputs import (  # noqa: E402
    _REQUIRED_OUTPUTS_FIELDS,
)


def test_canonical_output_rows_satisfy_the_bundle_contract(tmp_path):
    runtime = _wire_runtime(tmp_path)
    runtime.wire_check(seal_and_score=False)

    rows = runtime._canonical_output_rows(runtime._client)
    assert len(rows) == 2
    for row in rows:
        assert _REQUIRED_OUTPUTS_FIELDS <= set(row)
        assert row["carrier_lock_key"] == "fake-carrier"
        assert row["arm"] == "bare-core"
        assert row["admitted"] is True
        assert isinstance(row["text"], str)
        assert len(row["request_sha256"]) == 64
        assert len(row["response_sha256"]) == 64
    assert sorted(row["sample_id"] for row in rows) == ["s1", "s2"]
    # One row per sample: the contract refuses duplicates.
    assert len({row["sample_id"] for row in rows}) == len(rows)


def test_canonical_output_rows_bind_text_to_its_recorded_hash(tmp_path):
    """verify_bundle recomputes sha256(text) and refuses on a mismatch, so
    the row's text and its recorded hash must come from the same response."""

    runtime = _wire_runtime(tmp_path)
    runtime.wire_check(seal_and_score=False)
    rows = runtime._canonical_output_rows(runtime._client)
    for row in rows:
        recomputed = hashlib.sha256(str(row["text"]).encode("utf-8")).hexdigest()
        assert recomputed == row["response_text_sha256"]


def test_canonical_output_rows_fail_closed_without_response_hashes(tmp_path):
    class _HashlessTiming(_FakeTiming):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.request_sha256 = None
            self.response_sha256 = None
            self.response_text_sha256 = None

    class _HashlessClient(_TransportDrivingClient):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.timings = (
                _HashlessTiming(sample_id="s1"),
                _HashlessTiming(sample_id="s2"),
            )

    runtime = _wire_runtime(tmp_path, client_factory=_HashlessClient)
    runtime.wire_check(seal_and_score=False)
    with pytest.raises(FlightRuntimeError, match="bundle contract binds an outputs row"):
        runtime._canonical_output_rows(runtime._client)


def test_canonical_output_rows_fail_closed_without_a_per_request_record(tmp_path):
    class _NoTimingClient(_TransportDrivingClient):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.timings = ()

    runtime = _wire_runtime(tmp_path, client_factory=_NoTimingClient)
    runtime.wire_check(seal_and_score=False)
    with pytest.raises(FlightRuntimeError, match="no per-request record"):
        runtime._canonical_output_rows(runtime._client)
