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
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Mapping

import pytest

from speech_aware_evidence_acquisition.core.bundle import BundleError
from speech_aware_evidence_acquisition.core.flight.runtime import (
    FlightRuntime,
    FlightRuntimeError,
    FlightServeGeometryMismatchError,
    FlightServingSessionMismatchError,
    FlightStageOrderError,
)
from speech_aware_evidence_acquisition.e0.d2_leakage import ARM_VISIBLE_FIELDS
from speech_aware_evidence_acquisition.rails.context_budget import ContextBudgetRefusal
from speech_aware_evidence_acquisition.rails.task_adapter import TaskAdapter

# ---------------------------------------------------------------------------
# Minimal fakes. This file never touches a server.
# ---------------------------------------------------------------------------


class _FakeAudioRef:
    def __init__(self, path: str, sha256: str) -> None:
        self.path = path
        self.sha256 = sha256

    def validate(self) -> "_FakeAudioRef":
        # rails.obs.ObsPacket.validate() calls this; the phase-envelope path
        # builds a default ObsPacket to reach the adapter's task contract.
        return self


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


class _WideCompletionFakeAdapter(_FakeAdapter):
    """The same resident service dimensions with a wider request ceiling."""

    SERVING_MAX_TOKENS = 256


class _LegacyWideBudgetFakeAdapter(_FakeAdapter):
    """A legacy adapter whose historical reserve exceeds the model request cap."""

    SERVING_MAX_TOKENS = 512


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
        native_tool_calls: int | None = None,
    ) -> None:
        self.latency_seconds = latency_seconds
        self.sample_id = sample_id
        self.request_id = request_id
        self.native_tool_calls = native_tool_calls
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
        self.completions: list[dict] = []
        self._lock = threading.Lock()

    def complete(self, messages, **kwargs):
        """A client that cannot complete is not a client. The concurrent
        dispatcher calls this directly (the serial raw path still goes
        through rails_runner), so the double has to answer."""

        with self._lock:
            self.completions.append({"messages": list(messages), **kwargs})
        return "resp"

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
    def __init__(self, sample_id: str, final_response_text: str = "resp") -> None:
        self.sample_id = sample_id
        self.final_response_text = final_response_text
        self.contacts = (object(),)


class _FakePhaseSummary:
    """Mirrors rails.runner.AgentLoopSummary's own surface as far as
    FlightRuntime reads it: results, controller_policy_id, and the
    as_json() seal() writes into `<run_id>.phases.json`."""

    def __init__(self, results, controller_policy_id: str = "phase-direct-only-v1") -> None:
        self.results = tuple(results)
        self.controller_policy_id = controller_policy_id

    def as_json(self) -> dict:
        return {
            "controller_policy_id": self.controller_policy_id,
            "results": [
                {
                    "sample_id": result.sample_id,
                    "final_response_text": result.final_response_text,
                }
                for result in self.results
            ],
        }


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


def _fake_ledger_validator(bundle, cells):
    """core.tracking.ledger_row_for_bundle reads a REAL VerifiedBundle; this
    double asserts the same contract the real one enforces -- every
    caller-owned column present -- without needing one."""

    missing = [
        column
        for column in FlightRuntime.CALLER_LEDGER_COLUMNS
        if column not in dict(cells or {})
    ]
    assert not missing, f"ledger row is missing {missing}"
    return ({}, dict(cells))


def _fake_bundle_finalizer(
    manifest_path, lock, root, *, repo_root, ledger_cells=None
) -> _FakeFinalizeResult:
    """The real core.bundle.finalize_bundle validates the COMPLETE 21-column
    ledger surface before it will score, so a caller supplying none of the
    twelve caller-owned columns is refused. This double asserts the same
    contract rather than ignoring the argument."""

    missing = [
        column
        for column in FlightRuntime.CALLER_LEDGER_COLUMNS
        if column not in dict(ledger_cells or {})
    ]
    assert not missing, f"finalize_bundle was given no value for {missing}"
    return _FakeFinalizeResult()


def _fake_score_batch(jobs, *, output_dir, max_workers, **_kwargs) -> Mapping[str, object]:
    """Mirrors core.scoring_batch.run_score_batch's own success shape: it
    reports per-job outcomes in the RESULT rather than raising, so a caller
    that only watches for exceptions cannot tell a green batch from a red
    one."""

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    return {
        "job_count": len(jobs),
        "succeeded": len(jobs),
        "failed": 0,
        "jobs": [
            {"job_id": getattr(job, "job_id", "j"), "status": "succeeded"}
            for job in jobs
        ],
    }


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
    experiment_extra: Mapping[str, object] | None = None,
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
    experiment_document.update(dict(experiment_extra or {}))
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
    "carrier_root_resolver": lambda lock, carrier_lock_key, data_root: (
        Path(data_root) / carrier_lock_key
    ),
    "client_factory": _FakeClient,
    "manifest_builder": _fake_manifest_builder,
    "bundle_verifier": _fake_bundle_verifier,
    "bundle_finalizer": _fake_bundle_finalizer,
    "ledger_validator": _fake_ledger_validator,
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


def test_serve_reuses_same_resident_for_a_different_completion_ceiling(tmp_path):
    calls = {"starts": 0}

    def _counting_session_starter(**kwargs):
        calls["starts"] += 1
        return _FakeSession(str(kwargs["session_id"]))

    repo_a = _make_repo(tmp_path / "a", "SAEA-TEST-A")
    repo_b = _make_repo(tmp_path / "b", "SAEA-TEST-B")
    owner = _make_runtime(
        tmp_path, run_id="SAEA-TEST-A", attempt_id="attempt-a", happy_path=True,
        repo_root=repo_a, session_starter=_counting_session_starter,
    )
    borrower = _make_runtime(
        tmp_path, run_id="SAEA-TEST-B", attempt_id="attempt-b", happy_path=True,
        repo_root=repo_b, adapter_cls=_WideCompletionFakeAdapter,
        session_starter=_counting_session_starter,
    )
    owner.preflight()
    owner.preprocess()
    owner.serve()
    borrower.preflight()
    borrower.preprocess()
    assert borrower.serving_profile_fingerprint() == owner.serving_profile_fingerprint()
    receipt = borrower.serve(reuse=owner)
    assert calls["starts"] == 1
    assert receipt["reused"] is True


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
    # workers=1 is the SERIAL path, and the serial raw path is the one
    # that goes through rails_runner; the concurrent path dispatches
    # contacts itself and never reaches that seam.
    receipt = runtime.run_phases(workers=1)

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


def _two_phase_runner(**kwargs: object):
    """A select-then-fill shaped fake: two whole-roster phases over the SAME
    two samples, the second one carrying the text that must be sealed."""

    return (
        _FakePhaseSummary(
            (
                _FakePhaseResult("s1", final_response_text="draft-1"),
                _FakePhaseResult("s2", final_response_text="draft-2"),
            ),
            controller_policy_id="phase-select-then-fill-v1:select",
        ),
        _FakePhaseSummary(
            (_FakePhaseResult("s1"), _FakePhaseResult("s2")),
            controller_policy_id="phase-select-then-fill-v1:fill",
        ),
    )


def _bound_phase_runtime(tmp_path, phase_runner, *, policy="phase-select-then-fill-v1"):
    runtime = _make_runtime(
        tmp_path,
        happy_path=True,
        config_kwargs={"policy": policy},
        phase_runner=phase_runner,
    )
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    runtime.bind_phase_program_material(
        knowledge_snapshot="fake-snapshot",
        speech_packet_bindings={},
        material_for_phase=lambda *a, **kw: None,
    )
    return runtime


def test_run_phases_seals_one_row_per_sample_from_the_last_phase(tmp_path):
    """The multi-phase seal contract: a two-phase program answers each
    sample ONCE, with the final phase's text, and the receipt still accounts
    for every phase's contacts. Emitting one row per (phase, sample) gave
    duplicate sample ids that core.bundle.outputs.seal refused AFTER the
    contacts were spent."""

    runtime = _bound_phase_runtime(tmp_path, _two_phase_runner)
    receipt = runtime.run_phases()

    assert receipt["policy_kind"] == "phase-program"
    assert receipt["contact_count"] == 4
    assert receipt["phases"] == [
        {"phase": "phase-select-then-fill-v1:select", "rows": 2, "contacts": 2},
        {"phase": "phase-select-then-fill-v1:fill", "rows": 2, "contacts": 2},
    ]

    seal = runtime.seal()
    assert seal["outputs_row_count"] == 2
    rows = [
        json.loads(line)
        for line in Path(seal["outputs_path"]).read_text(encoding="utf-8").splitlines()
    ]
    assert [row["sample_id"] for row in rows] == ["s1", "s2"]
    # The LAST phase's response is what stands, not the first phase's draft.
    assert {row["text"] for row in rows} == {"resp"}

    assert seal["phase_count"] == 2
    phases_path = Path(seal["phases_path"])
    assert phases_path.name == "SAEA-TEST-RUN-001.phases.json"
    document = json.loads(phases_path.read_text(encoding="utf-8"))
    assert document["schema"] == "saea-flight-phase-summaries-v1"
    assert [phase["controller_policy_id"] for phase in document["phases"]] == [
        "phase-select-then-fill-v1:select",
        "phase-select-then-fill-v1:fill",
    ]
    assert (
        seal["phases_sha256"]
        == hashlib.sha256(phases_path.read_bytes()).hexdigest()
    )


def test_run_phases_refuses_phases_that_ran_different_sample_sets(tmp_path):
    """Refused BEFORE the seal, naming the program: a phase that silently
    dropped a row would otherwise seal a roster the earlier phases never
    conditioned on."""

    def _runner(**kwargs: object):
        return (
            _FakePhaseSummary(
                (_FakePhaseResult("s1"), _FakePhaseResult("s3")),
                controller_policy_id="phase-select-then-fill-v1:select",
            ),
            _FakePhaseSummary(
                (_FakePhaseResult("s1"), _FakePhaseResult("s2")),
                controller_policy_id="phase-select-then-fill-v1:fill",
            ),
        )

    runtime = _bound_phase_runtime(tmp_path, _runner)
    with pytest.raises(FlightRuntimeError, match="phase-select-then-fill-v1"):
        runtime.run_phases()


def test_seal_writes_no_phases_file_for_a_fixed_policy_flight(tmp_path):
    runtime = _make_runtime(tmp_path, happy_path=True)
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    receipt = runtime.run_phases()
    assert receipt["phases"] == []
    seal = runtime.seal()
    assert seal["phases_path"] is None
    assert seal["phases_sha256"] is None
    assert seal["phase_count"] == 0


def test_canonical_output_rows_refuse_duplicate_sample_ids(tmp_path):
    """The defensive check, independent of how the rows were built: the
    bundle contract accepts one row per sample and says so here, where the
    failure is still free."""

    runtime = _make_runtime(tmp_path, happy_path=True)
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    runtime.run_phases()
    runtime._output_rows = list(runtime._output_rows) + list(runtime._output_rows)
    with pytest.raises(FlightRuntimeError, match="appear more than once"):
        runtime.seal()


def test_run_phases_refuses_an_empty_phase_summary_sequence(tmp_path):
    runtime = _bound_phase_runtime(tmp_path, lambda **kwargs: ())
    with pytest.raises(FlightRuntimeError, match="no phase summaries"):
        runtime.run_phases()


def test_run_phases_refuses_a_phase_program_on_a_non_packet_arm(tmp_path):
    """Since E1 a phase program with no explicit bind builds its own binding
    from the baseline fragment, so the refusal is no longer "call
    bind_phase_program_material" -- it names the actual reason. The agent
    loop admits explicit feature or raw-native arms, and this arm is neither."""

    runtime = _make_runtime(
        tmp_path,
        happy_path=True,
        config_kwargs={"policy": "phase-direct-only-v1"},
    )
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    with pytest.raises(
        FlightRuntimeError, match="require an explicit feature or raw speech arm"
    ):
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
        return "resp"


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
    receipt = runtime.run_phases(workers=1)

    assert receipt["policy_kind"] == "direct"
    assert receipt["dispatch"]["dispatch"] == "serial"
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
        self.timings = ()
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
        response = json.loads(
            self._transport(json.dumps(payload).encode("utf-8")).decode("utf-8")
        )
        # Mirror rails.core_client.FrozenCoreClient: record one timing per
        # call, carrying how the response arrived. Without this the arrival
        # accounting would be asserted against a fixture rather than against
        # what the transport actually returned.
        calls = response.get("tool_calls")
        self.timings = tuple(self.timings) + (
            _FakeTiming(
                sample_id=f"s{len(self.timings) + 1}",
                request_id=f"req-{len(self.timings) + 1:04d}",
                native_tool_calls=len(calls) if isinstance(calls, list) else None,
            ),
        )
        return "resp"


def _calling_rails_runner(**kwargs):
    """Mirrors rails.runner._run_one_arm: one complete() per sample. The
    plain _fake_rails_runner never calls the client at all, so a wire check
    driven by it would see zero requests reach the transport.

    ``decoding_params`` may be a per-sample CALLABLE rather than a mapping
    (``rails.runner.run_rails_experiment``'s own contract, the seam a
    per-sample ``max_tokens`` rule travels); this double resolves it exactly
    where the real runner does, so a wire check driven by it proves something
    about the runner rather than about a second copy of it."""

    adapter = kwargs["adapter"]
    client = kwargs["core_client"]
    decoding_params = kwargs.get("decoding_params")
    results = []
    for sample in adapter.load_split(kwargs["split_id"]):
        client.complete(
            adapter.assemble_prompt(sample, None),
            decoding_params=(
                decoding_params(sample) if callable(decoding_params) else decoding_params
            ),
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
    # E6: a cell that supplies nothing carries no typed knowledge block, and
    # the receipt says so per request rather than staying silent.
    assert receipt["typed_knowledge_blocks"] == [0, 0]
    assert receipt["typed_knowledge_blocks_total"] == 0
    assert receipt["phase_supply"] is None


def _synthetic_obs_wire_runtime(tmp_path, *, abort_attempt=None):
    from types import MethodType

    from speech_aware_evidence_acquisition.core.base import RunResult
    from speech_aware_evidence_acquisition.core.preparation_windows import (
        WindowRequestBatch,
    )

    runtime = _wire_runtime(
        tmp_path,
        config_kwargs={"arm": "bare-core", "policy": "obs-agent-loop-ojw"},
        **({"abort_attempt": abort_attempt} if abort_attempt is not None else {}),
    )
    payloads = []
    sources = []
    for index in range(4):
        sample_id = "s1" if index < 2 else "s2"
        request_id = f"WIRECHECK-route-{sample_id}#w{index + 1:04d}"
        media_relpath = f"derived/obs-slices/WIRECHECK-route/{sample_id}/i{index:04d}.wav"
        payloads.append(
            {
                "request_id": request_id,
                "carrier_lock_key": "fake-carrier",
                "sample_id": sample_id,
                "speech_ref": media_relpath,
                "media_relpath": media_relpath,
                "audio_seconds": 1.0,
                "sample_rate_hz": 16_000,
                "task_instruction": "Synthetic speech task.",
                "history": [],
                "decoding_params": {"temperature": 0, "id_slot": index},
            }
        )
        sources.append({"sample_id": sample_id, "media_relpath": media_relpath})
    batch = WindowRequestBatch(
        tuple(payloads),
        tuple(f"{payload['sample_id']}#w{index + 1:04d}" for index, payload in enumerate(payloads)),
        tuple(sources),
    )
    runtime.materialize_window_batch = lambda **_kwargs: batch

    def dispatch(self, plan):
        self._gate.assert_model_touch_allowed(plan, arm="bare-core")
        # Reverse arrival order to prove parity is route/content based rather
        # than scheduler order based.
        for payload in reversed(payloads):
            self._transport(json.dumps(payload).encode("utf-8"))
        result = RunResult(
            run_id=plan.run_id,
            arm="bare-core",
            outputs_path=tmp_path / "synthetic.outputs.jsonl",
            trace_manifest_hash="a" * 64,
            cost={"calls_used": 4},
        )
        return (
            [{"sample_id": "s1"}, {"sample_id": "s2"}],
            4,
            "obs-loop",
            {"contacts_per_sample": 2.0},
            result,
        )

    runtime._dispatch_obs_policy = MethodType(dispatch, runtime)
    return runtime


def test_obs_wire_check_restores_runtime_and_observes_only_after_abort(tmp_path):
    events = []

    def abort(*_args, **_kwargs):
        events.append("abort")
        return True

    runtime = _synthetic_obs_wire_runtime(tmp_path, abort_attempt=abort)
    original = {
        name: getattr(runtime, name)
        for name in (
            "_run_id",
            "_attempt_id",
            "_plan",
            "_gate",
            "_transport",
            "_explicit_run_dir",
        )
    }
    receipt = runtime.wire_check(
        seal_and_score=False,
        request_payload_observer=lambda _payload: events.append("observe"),
    )

    assert receipt["selected_window_count"] == 4
    assert receipt["contact_count"] == 4
    assert receipt["fake_gate_attempts"] == 1
    assert receipt["fake_transport_requests"] == 4
    assert receipt["model_contacts"] == 0
    assert events == ["abort", "observe", "observe", "observe", "observe"]
    assert {name: getattr(runtime, name) for name in original} == original


def test_obs_wire_check_abort_failure_still_restores_runtime(tmp_path):
    def abort(*_args, **_kwargs):
        raise RuntimeError("synthetic abort failure")

    runtime = _synthetic_obs_wire_runtime(tmp_path, abort_attempt=abort)
    original = (runtime._run_id, runtime._attempt_id, runtime._gate, runtime._transport)
    with pytest.raises(RuntimeError, match="synthetic abort failure"):
        runtime.wire_check(seal_and_score=False)
    assert (runtime._run_id, runtime._attempt_id, runtime._gate, runtime._transport) == original


def test_obs_wire_check_materialization_failure_leaves_registered_state_untouched(tmp_path):
    aborts = []
    runtime = _synthetic_obs_wire_runtime(
        tmp_path, abort_attempt=lambda *args, **kwargs: aborts.append((args, kwargs))
    )
    runtime._explicit_run_dir = tmp_path / "registered-attempt"
    registered_dir = runtime._explicit_run_dir
    original = (runtime._run_id, runtime._attempt_id, runtime._gate, runtime._transport)

    def fail(**_kwargs):
        raise RuntimeError("synthetic materialization failure")

    runtime.materialize_window_batch = fail
    with pytest.raises(RuntimeError, match="synthetic materialization failure"):
        runtime.wire_check(seal_and_score=False)

    assert not aborts
    assert not registered_dir.exists()
    assert (runtime._run_id, runtime._attempt_id, runtime._gate, runtime._transport) == original


def test_obs_wire_check_dispatch_failure_aborts_and_restores_before_callback(tmp_path):
    from types import MethodType

    events = []

    def abort(*_args, **_kwargs):
        events.append("abort")
        return True

    runtime = _synthetic_obs_wire_runtime(tmp_path, abort_attempt=abort)
    original = (runtime._run_id, runtime._attempt_id, runtime._gate, runtime._transport)

    def fail_dispatch(self, plan):
        self._gate.assert_model_touch_allowed(plan, arm="bare-core")
        raise RuntimeError("synthetic dispatch failure")

    runtime._dispatch_obs_policy = MethodType(fail_dispatch, runtime)
    with pytest.raises(RuntimeError, match="synthetic dispatch failure"):
        runtime.wire_check(
            seal_and_score=False,
            request_payload_observer=lambda _payload: events.append("observe"),
        )

    assert events == ["abort"]
    assert (runtime._run_id, runtime._attempt_id, runtime._gate, runtime._transport) == original


@pytest.mark.parametrize("wrong_ids", [("s1", "s1"), ("s1", "foreign")])
def test_obs_wire_check_refuses_same_size_wrong_stitched_roster(tmp_path, wrong_ids):
    runtime = _synthetic_obs_wire_runtime(tmp_path)
    dispatch = runtime._dispatch_obs_policy

    def wrong_roster(plan):
        _rows, count, kind, details, result = dispatch(plan)
        return [{"sample_id": value} for value in wrong_ids], count, kind, details, result

    runtime._dispatch_obs_policy = wrong_roster
    with pytest.raises(FlightRuntimeError, match="stitched output roster"):
        runtime.wire_check(seal_and_score=False)


def test_obs_wire_check_refuses_scoring_and_worker_override_before_materialization(tmp_path):
    runtime = _synthetic_obs_wire_runtime(tmp_path)
    runtime.materialize_window_batch = lambda **_kwargs: pytest.fail(
        "refusal must happen before materialization"
    )
    with pytest.raises(FlightRuntimeError, match="seal_and_score=True"):
        runtime.wire_check(seal_and_score=True)
    with pytest.raises(FlightRuntimeError, match="do not accept workers"):
        runtime.wire_check(seal_and_score=False, workers=2)


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
    assert seal["score_result"]["job_count"] == 1
    assert seal["score_result"]["succeeded"] == 1
    assert seal["score_result"]["failed"] == 0


def test_wire_check_refuses_to_call_a_failed_score_batch_green(tmp_path):
    """A score batch reports a failed job in its result dict rather than
    raising. Reporting OK on "no exception" was a false green: the first
    clean-tree wire check said OK for all four cells while every scoring job
    had in fact failed."""

    def _failing_score_batch(jobs, *, output_dir, max_workers, **_kwargs):
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        return {
            "job_count": len(jobs),
            "succeeded": 0,
            "failed": len(jobs),
            "jobs": [
                {
                    "job_id": "j1",
                    "status": "failed",
                    "error": "official scorer exited with status 1",
                    "returncode": 1,
                    "stderr_log": "j1.stderr.log",
                }
            ],
        }

    runtime = _wire_runtime(tmp_path, score_batch=_failing_score_batch)
    receipt = runtime.wire_check(seal_and_score=True)

    seal = receipt["seal_and_score"]
    assert seal["status"] == "SCORING_FAILED"
    assert seal["job_failures"][0]["error"] == "official scorer exited with status 1"
    assert "manifest_sha256" in seal


def test_wire_check_seal_names_the_outputs_artifact_with_the_run_id_stem(tmp_path):
    """core.scorers._manifest_path_for_outputs locates a run's manifest by
    the shared run_id stem and refuses any other name, so a bare
    'outputs.jsonl' made official scoring fail after every contact."""

    written: dict[str, object] = {}

    def _capturing_manifest_builder(**kwargs):
        written["run_dir"] = Path(kwargs["run_dir"])
        written["run_id"] = kwargs["plan"].run_id
        return _fake_manifest_builder(**kwargs)

    runtime = _wire_runtime(tmp_path, manifest_builder=_capturing_manifest_builder)
    runtime.wire_check(seal_and_score=True)

    outputs = list(Path(written["run_dir"]).glob("*.outputs.jsonl"))
    assert len(outputs) == 1
    assert outputs[0].name == f"{written['run_id']}.outputs.jsonl"


def test_wire_check_validates_the_full_ledger_surface(tmp_path):
    """seal() calls core.bundle.finalize_bundle, which validates the
    COMPLETE 21-column ledger surface before it will score. A wire check
    that skipped that let a flight die at finalize after its contacts were
    spent (defect 9), so the check now validates the same surface."""

    seen: dict[str, object] = {}

    def _validator(bundle, cells):
        seen["cells"] = dict(cells)
        return ({}, dict(cells))

    runtime = _wire_runtime(tmp_path, ledger_validator=_validator)
    receipt = runtime.wire_check(seal_and_score=True)

    assert receipt["seal_and_score"]["status"] == "OK"
    assert receipt["seal_and_score"]["ledger_surface_validated"] is True
    for column in FlightRuntime.CALLER_LEDGER_COLUMNS:
        assert column in seen["cells"]
    assert seen["cells"]["decision"] == FlightRuntime.PENDING_JUDGMENT
    assert "fake-carrier" in seen["cells"]["speech task/carrier"]


def test_seal_refuses_when_a_caller_owned_ledger_column_is_missing(tmp_path):
    runtime = _make_runtime(tmp_path, happy_path=True)
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    runtime.run_phases()
    original = FlightRuntime._default_ledger_cells

    def _short(self, plan):
        cells = original(self, plan)
        cells.pop("decision")
        return cells

    FlightRuntime._default_ledger_cells = _short
    try:
        with pytest.raises(FlightRuntimeError, match="caller-owned column"):
            runtime.seal()
    finally:
        FlightRuntime._default_ledger_cells = original


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
    runtime = _wire_runtime(tmp_path)
    runtime.wire_check(seal_and_score=False)
    # Blank the response identity hashes the bundle contract binds a row to;
    # sealing must refuse rather than emit an unverifiable row.
    for timing in runtime._client.timings:
        timing.request_sha256 = None
        timing.response_sha256 = None
        timing.response_text_sha256 = None
    with pytest.raises(FlightRuntimeError, match="bundle contract binds an outputs row"):
        runtime._canonical_output_rows(runtime._client)


def test_canonical_output_rows_fail_closed_without_a_per_request_record(tmp_path):
    runtime = _wire_runtime(tmp_path)
    runtime.wire_check(seal_and_score=False)
    # Drop the per-request records the rows are built from; sealing must
    # refuse rather than emit a row the bundle contract cannot verify.
    runtime._client.timings = ()
    with pytest.raises(FlightRuntimeError, match="no per-request record"):
        runtime._canonical_output_rows(runtime._client)


# ---------------------------------------------------------------------------
# Phase 2f (E4, SLURP v2 base program module M3): the USE projection v3
# runtime delivery transform, switched on by the ONE flat run-level config
# key ``slurp_projection_v3_delivery``
# (``rails.slurp_projection_v3.SLURP_PROJECTION_V3_DELIVERY_KEY``). The real
# transform is monkeypatched here (module attribute -- the deferred import
# inside ``_canonical_output_rows`` re-reads it fresh on every call, so
# patching ``rails.slurp_projection_v3.apply_slurp_projection_v3_delivery``
# is visible to it) so these tests exercise the WIRING (switch gating,
# custody field, hash recomputation) without needing the real TRAIN-mined
# inventory or a SLURP-shaped fake response body.
# ---------------------------------------------------------------------------


def _slurp_wire_runtime(tmp_path, *, projection_on: bool):
    baseline_extra = {"slurp_projection_v3_delivery": 1} if projection_on else {}
    return _wire_runtime(
        tmp_path,
        config_kwargs={
            "carrier_lock_key": "slurp",
            "arm": "bare-core",
            "policy": "fixed",
            "baseline_extra": baseline_extra,
        },
    )


def test_the_switch_off_seals_a_row_byte_identical_to_before_the_module_existed(tmp_path):
    """OFF (the key absent) must reproduce exactly what
    ``test_canonical_output_rows_satisfy_the_bundle_contract`` already
    asserts for a plain carrier: no ``pre_projection_text``, no
    ``projection_v3``, and ``response_text_sha256`` bound to the row's own
    unmodified ``text`` -- the SAME two properties that test already pins,
    now proved again on the SLURP carrier with the module wired in but
    switched off."""

    runtime = _slurp_wire_runtime(tmp_path, projection_on=False)
    runtime.wire_check(seal_and_score=False)
    rows = runtime._canonical_output_rows(runtime._client)
    assert len(rows) == 2
    for row in rows:
        assert row["carrier_lock_key"] == "slurp"
        assert "pre_projection_text" not in row
        assert "projection_v3" not in row
        assert row["response_text_sha256"] == hashlib.sha256(
            str(row["text"]).encode("utf-8")
        ).hexdigest()


def test_the_switch_on_keeps_the_raw_text_in_custody_and_reseals_the_delivered_one(
    tmp_path, monkeypatch
):
    from speech_aware_evidence_acquisition.rails import slurp_projection_v3

    fake_delivered_text = '{"scenario": "play", "action": "music", "entities": []}'

    def _fake_transform(text, *, carrier_lock_key, inventory=None):
        assert carrier_lock_key == "slurp"
        assert text == "resp"
        return slurp_projection_v3.SlurpProjectionV3DeliveryResult(
            text=fake_delivered_text,
            changed=True,
            metadata={
                "rule_id": slurp_projection_v3.SLURP_PROJECTION_V3_ID,
                "applied": True,
                "label_branch": "r-action",
                "label_changed": True,
                "fillers_changed": 0,
                "changed": True,
            },
        )

    monkeypatch.setattr(
        slurp_projection_v3, "apply_slurp_projection_v3_delivery", _fake_transform
    )
    runtime = _slurp_wire_runtime(tmp_path, projection_on=True)
    runtime.wire_check(seal_and_score=False)
    rows = runtime._canonical_output_rows(runtime._client)
    assert len(rows) == 2
    for row in rows:
        # The RAW response is never overwritten -- it is kept in custody
        # beside the delivered one.
        assert row["pre_projection_text"] == "resp"
        assert row["text"] == fake_delivered_text
        assert row["projection_v3"]["label_branch"] == "r-action"
        assert row["projection_v3"]["changed"] is True
        # response_text_sha256 is rebound to the DELIVERED text, exactly the
        # same self-consistency contract every other row already carries
        # (test_canonical_output_rows_bind_text_to_its_recorded_hash).
        assert row["response_text_sha256"] == hashlib.sha256(
            fake_delivered_text.encode("utf-8")
        ).hexdigest()
        assert row["response_text_sha256"] != hashlib.sha256(b"resp").hexdigest()


def test_the_switch_on_is_a_no_op_when_the_transform_reports_no_change(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.rails import slurp_projection_v3

    def _fake_unparsed(text, *, carrier_lock_key, inventory=None):
        return slurp_projection_v3.SlurpProjectionV3DeliveryResult(
            text=text, changed=False, metadata={"applied": False, "reason": "unparsed"}
        )

    monkeypatch.setattr(
        slurp_projection_v3, "apply_slurp_projection_v3_delivery", _fake_unparsed
    )
    runtime = _slurp_wire_runtime(tmp_path, projection_on=True)
    runtime.wire_check(seal_and_score=False)
    rows = runtime._canonical_output_rows(runtime._client)
    for row in rows:
        assert row["text"] == "resp"
        assert "pre_projection_text" not in row
        assert "projection_v3" not in row
        assert row["response_text_sha256"] == hashlib.sha256(b"resp").hexdigest()


def test_the_switch_on_refuses_a_non_slurp_carrier(tmp_path):
    baseline_extra = {"slurp_projection_v3_delivery": 1}
    runtime = _wire_runtime(
        tmp_path,
        config_kwargs={
            "carrier_lock_key": "fake-carrier",
            "arm": "bare-core",
            "policy": "fixed",
            "baseline_extra": baseline_extra,
        },
    )
    runtime.wire_check(seal_and_score=False)
    with pytest.raises(FlightRuntimeError, match="only defined for the 'slurp' carrier"):
        runtime._canonical_output_rows(runtime._client)


# ---------------------------------------------------------------------------
# Phase 3a: native tool calls versus text, recorded where it is still known.
#
# core.model.transport canonicalizes a native message.tool_calls into the SAME
# [{"name": ..., "arguments": {...}}] text a free-text arm produces. That is
# what lets one scorer serve both arms -- and it is why a sealed outputs row
# cannot be read back to tell the two apart. The calibration smoke hit exactly
# that: three of four native-arm rows were canonical JSON arrays and nothing
# recorded which mechanism produced them.
# ---------------------------------------------------------------------------


def test_response_arrival_counts_separates_native_calls_from_text() -> None:
    class _Client:
        timings = (
            _FakeTiming(sample_id="s1", native_tool_calls=2),
            _FakeTiming(sample_id="s2", native_tool_calls=None),
            _FakeTiming(sample_id="s3", native_tool_calls=1),
        )

    counts = FlightRuntime.response_arrival_counts(_Client())
    assert counts["rows_total"] == 3
    assert counts["rows_with_native_tool_calls"] == 2
    assert counts["rows_answered_as_text"] == 1
    assert counts["native_tool_calls_total"] == 3


def test_response_arrival_counts_call_zero_is_not_text() -> None:
    """A row whose envelope carried an EMPTY tool_calls list is still a
    native-arm response, not a text answer; only a missing key means text."""

    class _Client:
        timings = (_FakeTiming(sample_id="s1", native_tool_calls=0),)

    counts = FlightRuntime.response_arrival_counts(_Client())
    assert counts["rows_with_native_tool_calls"] == 1
    assert counts["rows_answered_as_text"] == 0
    assert counts["native_tool_calls_total"] == 0


def test_run_phases_receipt_reports_how_responses_arrived(tmp_path):
    runtime = _make_runtime(
        tmp_path,
        happy_path=True,
        config_kwargs={"arm": "bare-core", "policy": "fixed"},
    )
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    receipt = runtime.run_phases()

    arrival = receipt["response_arrival"]
    assert arrival["rows_total"] == 2
    assert arrival["rows_answered_as_text"] == 2
    assert arrival["rows_with_native_tool_calls"] == 0
    assert receipt["client_initialization_seconds"] >= 0.0


def test_wire_check_reports_and_asserts_native_arrival_for_a_native_arm(tmp_path):
    """The fake transport imitates exactly one native envelope for a native
    arm, so the check proves the accounting distinguishes the two rather
    than merely reporting a constant."""

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

    arrival = receipt["response_arrival"]
    assert arrival["rows_with_native_tool_calls"] == 1
    assert arrival["rows_answered_as_text"] == 1
    assert arrival["native_tool_calls_total"] == 1


def test_wire_check_reports_all_text_for_a_non_native_arm(tmp_path):
    runtime = _wire_runtime(tmp_path)
    receipt = runtime.wire_check(seal_and_score=False)

    arrival = receipt["response_arrival"]
    assert arrival["rows_with_native_tool_calls"] == 0
    assert arrival["rows_answered_as_text"] == 2


def test_wire_check_refuses_when_arrival_accounting_disagrees(tmp_path):
    """If the accounting cannot see the native envelope the transport
    emitted, the check must refuse -- a count that reports the same number
    either way is the ambiguity this field exists to remove."""

    class _BlindClient(_TransportDrivingClient):
        def complete(self, messages, **kwargs):
            out = super().complete(messages, **kwargs)
            self.timings = tuple(
                _FakeTiming(sample_id=t.sample_id, request_id=t.request_id)
                for t in self.timings
            )
            return out

    runtime = _wire_runtime(
        tmp_path,
        client_factory=_BlindClient,
        config_kwargs={
            "arm": "bare-core-native-tools",
            "policy": "fixed",
            "baseline_extra": {"tool_schema_fill": "audio2tool-openai-tools"},
        },
        tool_schema_resolver=lambda lock, root, name: [
            {"type": "function", "function": {"name": "t"}}
        ],
    )
    with pytest.raises(FlightRuntimeError, match="native tool-call row"):
        runtime.wire_check(seal_and_score=False)


def test_wire_check_transport_emits_a_native_envelope_only_on_the_first_call() -> None:
    transport = WireCheckTransport(native_tool_calls_on_first=True)
    first = json.loads(transport(b"{}").decode("utf-8"))
    second = json.loads(transport(b"{}").decode("utf-8"))
    assert isinstance(first["tool_calls"], list) and len(first["tool_calls"]) == 1
    assert first["tool_calls"][0]["function"]["name"] == "wire-check"
    assert "tool_calls" not in second
    # Default stays text-only, so no pre-existing caller changes shape.
    assert "tool_calls" not in json.loads(WireCheckTransport()(b"{}").decode("utf-8"))


# ---------------------------------------------------------------------------
# Phase 3b-prep: concurrent dispatch. The owner asked for batched parallel
# calls against the loaded model; both fixed-policy branches dispatched one
# contact at a time. These tests pin the invariants that make concurrency
# safe rather than merely fast.
# ---------------------------------------------------------------------------


class _ConcurrencyRecordingClient(_FakeClient):
    """Records what actually ran in parallel: peak in-flight, the id_slot
    each contact used, and the order contacts started in."""

    delay = 0.02
    fail_on: str | None = None

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.in_flight = 0
        self.max_in_flight = 0
        self.slots_seen: list[int] = []
        self.slot_by_thread: dict[int, set[int]] = {}
        self.started: list[str] = []
        self.timings = ()
        self._guard = threading.Lock()

    def complete(self, messages, **kwargs):
        decoding = dict(kwargs.get("decoding_params") or {})
        slot = decoding.get("id_slot")
        with self._guard:
            self.in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self.in_flight)
            self.slots_seen.append(slot)
            self.slot_by_thread.setdefault(threading.get_ident(), set()).add(slot)
            self.started.append(str(kwargs.get("speech_feature_sample_id") or len(self.started)))
            in_flight_now = self.in_flight
        assert in_flight_now <= _CONCURRENCY_LIMIT["slots"], (
            f"{in_flight_now} requests in flight for "
            f"{_CONCURRENCY_LIMIT['slots']} slot(s)"
        )
        time.sleep(self.delay)
        with self._guard:
            self.in_flight -= 1
            self.timings = tuple(self.timings) + (
                _FakeTiming(
                    sample_id=f"s{len(self.timings) + 1}",
                    request_id=f"req-{len(self.timings) + 1:04d}",
                ),
            )
        if type(self).fail_on is not None and type(self).fail_on in json.dumps(
            list(messages), default=str
        ):
            raise RuntimeError("contact failed on purpose")
        return "resp"


_CONCURRENCY_LIMIT = {"slots": 2}


class _ManySampleAdapter(_FakeAdapter):
    """Eight samples over two slots, so a serial dispatch and a concurrent
    one are distinguishable."""

    def __init__(self, lock, root) -> None:
        super().__init__(lock, root)
        self.samples = tuple(_FakeSample(f"s{index}") for index in range(1, 9))


def _concurrent_runtime(tmp_path, **kwargs):
    merged = {
        "happy_path": True,
        "adapter_cls": _ManySampleAdapter,
        "client_factory": _ConcurrencyRecordingClient,
        "config_kwargs": {"arm": "bare-core", "policy": "fixed"},
    }
    merged.update(kwargs)
    return _make_runtime(tmp_path, **merged)


def test_concurrent_dispatch_holds_at_most_slots_requests_in_flight(tmp_path):
    _CONCURRENCY_LIMIT["slots"] = 2
    runtime = _concurrent_runtime(tmp_path)
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    receipt = runtime.run_phases()

    client = runtime._client
    assert receipt["dispatch"]["dispatch"] == "concurrent"
    assert receipt["dispatch"]["workers"] == 2  # _FakeAdapter.SERVING_SLOTS
    assert client.max_in_flight > 1, "nothing actually ran in parallel"
    assert client.max_in_flight <= 2
    assert receipt["dispatch"]["max_in_flight"] == client.max_in_flight
    assert receipt["contact_count"] == 8


def test_each_worker_is_pinned_to_its_own_slot(tmp_path):
    _CONCURRENCY_LIMIT["slots"] = 2
    runtime = _concurrent_runtime(tmp_path)
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    receipt = runtime.run_phases()

    client = runtime._client
    # Every slot id is a real slot index, and one thread never used two.
    assert set(client.slots_seen) <= {0, 1}
    for slots in client.slot_by_thread.values():
        assert len(slots) == 1, f"a worker used more than one slot: {slots}"
    # Distinct threads hold distinct slots, so no two in-flight requests
    # ever share one.
    held = [next(iter(slots)) for slots in client.slot_by_thread.values()]
    assert len(held) == len(set(held))
    assert receipt["dispatch"]["slot_ids_used"] == sorted(set(client.slots_seen))


def test_concurrent_results_come_back_in_sample_order(tmp_path):
    _CONCURRENCY_LIMIT["slots"] = 2
    runtime = _concurrent_runtime(tmp_path)
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    runtime.run_phases()

    ordered = [row["sample_id"] for row in runtime._output_rows]
    assert ordered == [sample.sample_id for sample in runtime._samples]


def test_one_failed_contact_aborts_without_losing_completed_traces(tmp_path):
    _CONCURRENCY_LIMIT["slots"] = 2
    flushed: list[object] = []

    class _BufferingClient(_ConcurrencyRecordingClient):
        fail_on = "s4"

        def new_trace_buffer(self):
            return {"buffer": len(flushed)}

        def flush_trace_buffer(self, buffer):
            flushed.append(buffer)

    runtime = _concurrent_runtime(tmp_path, client_factory=_BufferingClient)
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    with pytest.raises(RuntimeError, match="on purpose"):
        runtime.run_phases()

    # The contacts that DID complete still had their traces flushed rather
    # than lost to the abort.
    assert flushed, "a failing dispatch discarded every completed trace buffer"


def test_workers_one_keeps_the_serial_path_reproducible(tmp_path):
    calls = {"count": 0}

    def _rails_runner(**kwargs):
        calls["count"] += 1
        return _fake_rails_runner(**kwargs)

    runtime = _concurrent_runtime(tmp_path, rails_runner=_rails_runner)
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    receipt = runtime.run_phases(workers=1)

    assert calls["count"] == 1
    assert receipt["dispatch"]["dispatch"] == "serial"
    assert receipt["dispatch"]["max_in_flight"] == 1
    assert runtime._client.max_in_flight == 0  # the client was never called directly


def test_concurrent_dispatch_refuses_a_bad_worker_count(tmp_path):
    runtime = _concurrent_runtime(tmp_path)
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    with pytest.raises(FlightRuntimeError, match="workers must be a positive integer"):
        runtime._dispatch_concurrent(runtime._client_factory(arm="bare-core"), workers=0)


def test_slot_occupancy_is_measured_against_the_slots_actually_used(tmp_path):
    """A serial dispatch on a two-slot server occupies ONE slot; reporting
    it as a half would understate exactly what the number is for."""

    runtime = _concurrent_runtime(tmp_path)
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    receipt = runtime.run_phases(workers=1)

    assert receipt["serving_slots"] == 2
    assert receipt["occupancy_slots"] == 1


# ---------------------------------------------------------------------------
# score(include_per_sample=...) -- what the evolution loop reads.
# ---------------------------------------------------------------------------


def _capturing_score_batch(seen: dict):
    def _score_batch(jobs, **kwargs):
        seen.update(kwargs)
        Path(kwargs["output_dir"]).mkdir(parents=True, exist_ok=True)
        return {"job_count": len(jobs), "succeeded": len(jobs), "failed": 0, "jobs": []}

    return _score_batch


def _sealed_runtime(tmp_path, **runtime_kwargs):
    runtime = _make_runtime(tmp_path, happy_path=True, **runtime_kwargs)
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    runtime.run_phases()
    runtime.seal()
    return runtime


def test_score_defaults_to_per_sample_off_and_says_so_in_its_receipt(tmp_path):
    seen: dict = {}
    runtime = _sealed_runtime(tmp_path, score_batch=_capturing_score_batch(seen))
    receipt = runtime.score()

    assert seen["include_per_sample"] is False
    assert receipt["include_per_sample"] is False


def test_score_forwards_include_per_sample_to_the_batch(tmp_path):
    seen: dict = {}
    runtime = _sealed_runtime(tmp_path, score_batch=_capturing_score_batch(seen))
    receipt = runtime.score(include_per_sample=True)

    assert seen["include_per_sample"] is True
    assert seen["max_workers"] == 1
    assert receipt["include_per_sample"] is True


# ---------------------------------------------------------------------------
# E1.3: the pinned phase prompt-fit receipt, verified at preflight.
#
# The whole point is that the receipt describes the envelope this flight
# would ACTUALLY send. The tests below build the receipt the way the
# measurement script builds it -- through the same
# ``render_phase_prompt_envelopes`` -- then check that preflight accepts it,
# and refuses the moment either the receipt's bytes or the rendered envelope
# stops matching.
# ---------------------------------------------------------------------------

PHASE_PROGRAM = "phase-draft-revise-v1"
_PHASE_MATERIAL = {
    "draft": {
        "instruction_template": "probes/draft.txt",
        "predecessor_binding": "none",
    },
    "revise": {
        "instruction_template": "probes/revise.txt",
        "predecessor_binding": "append-sealed-state",
    },
}


def _phase_prompt_fit_repo(tmp_path, run_id: str) -> tuple[Path, Path, Path]:
    """A synthetic repo carrying a two-phase packet cell, its phase
    templates, and its promotion receipt -- everything but the receipt, which
    the caller writes before the tree is committed (preflight asserts a clean
    study tree, so nothing may be added afterwards)."""

    repo_root = tmp_path / "repo"
    data_root = tmp_path / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    promotion_receipt = _write_promotion_receipt(tmp_path)
    _write_configs(
        repo_root,
        arm="speech-feature-query",
        policy=PHASE_PROGRAM,
        model_extra={"speech_feature_root": str(tmp_path / _PROMOTION_DIR)},
        baseline_extra={
            "speech_packet_promotion_receipt": str(promotion_receipt),
            "speech_feature_key_representation_id": "key-rep-v1",
            "speech_feature_matcher_policy_id": "matcher-v1",
            "phase_material": _PHASE_MATERIAL,
            "prompt_fit_receipt": "docs/checks/phase-prompt-fit.json",
            "prompt_fit_receipt_sha256": "0" * 64,
        },
    )
    for phase, body in (("draft", "Draft the tool call."), ("revise", "Revise it.")):
        template = repo_root / "configs" / "probes" / f"{phase}.txt"
        template.parent.mkdir(parents=True, exist_ok=True)
        template.write_text(body + "\n", encoding="utf-8")
    _write_exposure_ledger(repo_root, run_id)
    return repo_root, data_root, promotion_receipt


def _rendered_phase_envelope_sha256(repo_root: Path, data_root: Path) -> dict[str, str]:
    """``{phase: envelope_sha256}`` for sample ``s1``, rendered exactly as
    ``scripts/a2t_calibration_prompt_fit.py --phase-program`` renders it."""

    from speech_aware_evidence_acquisition.core.config import compose
    from speech_aware_evidence_acquisition.core.flight.runtime import (
        phase_envelope_sha256,
        phase_program_system_text,
        render_phase_prompt_envelopes,
    )
    from speech_aware_evidence_acquisition.rails.controllers import (
        default_phase_program,
    )
    from speech_aware_evidence_acquisition.rails.phase_material import (
        load_phase_material_specs,
        render_static_instruction,
    )

    composed = compose(repo_root, "m", "d", "b", "e")
    program = default_phase_program(PHASE_PROGRAM)
    specs = load_phase_material_specs(composed.values, program)
    static_text = {
        phase: render_static_instruction(spec, repo_root, {}, data_root)
        for phase, spec in specs.items()
    }
    adapter = _FakeAdapter({}, data_root)
    sample = adapter.samples[0]
    envelopes = render_phase_prompt_envelopes(
        program_id=program.program_id,
        phase_names=program.phase_names(),
        specs=specs,
        static_text_by_phase=static_text,
        system_text=phase_program_system_text(adapter, sample),
        prompt_order="speech-query-prefix-v2",
        packet_descriptor={"packet_id": "s1", "sha256": "s1-sha"},
        sample_id=sample.sample_id,
        completion_token_ceiling=_FakeAdapter.SERVING_MAX_TOKENS,
    )
    return {phase: phase_envelope_sha256(envelope) for phase, envelope in envelopes.items()}


def _write_phase_prompt_fit_receipt(
    repo_root: Path, data_root: Path, *, mutate: str | None = None
) -> str:
    """Write the receipt and return its sha256, patching the fragment's own
    ``prompt_fit_receipt_sha256`` to match. ``mutate='envelope'`` records a
    hash no rendering can reproduce."""

    from speech_aware_evidence_acquisition.core.config import compose
    from speech_aware_evidence_acquisition.core.flight.runtime import (
        PHASE_PROMPT_FIT_SCHEMA,
    )

    composed = compose(repo_root, "m", "d", "b", "e")
    digests = _rendered_phase_envelope_sha256(repo_root, data_root)
    if mutate == "envelope":
        digests["revise"] = "9" * 64
    receipt = {
        "schema": PHASE_PROMPT_FIT_SCHEMA,
        "cells": [
            {
                "cell_id": "test-cell",
                "model_fragment": "m",
                "dataset_fragment": "d",
                "baseline_fragment": "b",
                "experiment_fragment": "e",
                # Provenance only: pinning the receipt changes this hash, so
                # the runtime matches the cell by its four fragment names.
                "config_hash": composed.config_hash,
                "phases": [
                    {
                        "phase": phase,
                        "max_sample_id": "s1",
                        "envelope_sha256": digests[phase],
                        "max_text_prompt_tokens": 100,
                        "every_request_fits": True,
                    }
                    for phase in ("draft", "revise")
                ],
            }
        ],
    }
    path = repo_root / "docs" / "checks" / "phase-prompt-fit.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    baseline_path = repo_root / "configs" / "baseline" / "b.json"
    document = json.loads(baseline_path.read_text(encoding="utf-8"))
    document["prompt_fit_receipt_sha256"] = digest
    baseline_path.write_text(json.dumps(document), encoding="utf-8")
    return digest


def _phase_prompt_fit_runtime(tmp_path, repo_root: Path, data_root: Path, run_id: str):
    _git_init_commit(repo_root)
    merged = dict(_HAPPY_PATH_KWARGS)
    return FlightRuntime(
        repo_root,
        data_root,
        model="m",
        dataset="d",
        baseline="b",
        experiment="e",
        run_id=run_id,
        attempt_id="attempt-001",
        runtime_root=tmp_path / "runtime",
        adapter_factory=lambda lock, root: _FakeAdapter(lock, root),
        gate_factory=lambda *a, **kw: _FakeGate(),
        lock={},
        **merged,
    )


def test_preflight_accepts_a_receipt_whose_envelopes_still_render(tmp_path):
    run_id = "SAEA-TEST-RUN-001"
    repo_root, data_root, _ = _phase_prompt_fit_repo(tmp_path, run_id)
    digest = _write_phase_prompt_fit_receipt(repo_root, data_root)
    runtime = _phase_prompt_fit_runtime(tmp_path, repo_root, data_root, run_id)

    receipt = runtime.preflight()

    fit = receipt["phase_prompt_fit"]
    assert fit["schema"] == "saea-phase-prompt-fit-v1"
    assert fit["cell_id"] == "test-cell"
    assert fit["prompt_fit_receipt_sha256"] == digest
    assert fit["program_id"] == PHASE_PROGRAM
    assert [entry["phase"] for entry in fit["phases"]] == ["draft", "revise"]
    assert all(len(entry["envelope_sha256"]) == 64 for entry in fit["phases"])


def test_preflight_refuses_a_receipt_whose_envelope_drifted(tmp_path):
    run_id = "SAEA-TEST-RUN-001"
    repo_root, data_root, _ = _phase_prompt_fit_repo(tmp_path, run_id)
    _write_phase_prompt_fit_receipt(repo_root, data_root, mutate="envelope")
    runtime = _phase_prompt_fit_runtime(tmp_path, repo_root, data_root, run_id)

    with pytest.raises(FlightRuntimeError, match="phase 'revise' recorded envelope"):
        runtime.preflight()


def test_preflight_refuses_a_receipt_whose_bytes_drifted(tmp_path):
    run_id = "SAEA-TEST-RUN-001"
    repo_root, data_root, _ = _phase_prompt_fit_repo(tmp_path, run_id)
    _write_phase_prompt_fit_receipt(repo_root, data_root)
    # The receipt is edited after its hash was pinned.
    path = repo_root / "docs" / "checks" / "phase-prompt-fit.json"
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    runtime = _phase_prompt_fit_runtime(tmp_path, repo_root, data_root, run_id)

    with pytest.raises(FlightRuntimeError, match="hashes to"):
        runtime.preflight()


def test_preflight_refuses_a_receipt_measured_for_another_cell(tmp_path):
    run_id = "SAEA-TEST-RUN-001"
    repo_root, data_root, _ = _phase_prompt_fit_repo(tmp_path, run_id)
    _write_phase_prompt_fit_receipt(repo_root, data_root)
    path = repo_root / "docs" / "checks" / "phase-prompt-fit.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["cells"][0]["baseline_fragment"] = "some-other-baseline"
    path.write_text(json.dumps(document, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    baseline_path = repo_root / "configs" / "baseline" / "b.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    baseline["prompt_fit_receipt_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    runtime = _phase_prompt_fit_runtime(tmp_path, repo_root, data_root, run_id)

    with pytest.raises(FlightRuntimeError, match="0 cell\\(s\\) for fragments"):
        runtime.preflight()


def test_preflight_refuses_a_receipt_path_with_no_pinned_hash(tmp_path):
    run_id = "SAEA-TEST-RUN-001"
    repo_root, data_root, _ = _phase_prompt_fit_repo(tmp_path, run_id)
    _write_phase_prompt_fit_receipt(repo_root, data_root)
    baseline_path = repo_root / "configs" / "baseline" / "b.json"
    document = json.loads(baseline_path.read_text(encoding="utf-8"))
    document.pop("prompt_fit_receipt_sha256")
    baseline_path.write_text(json.dumps(document), encoding="utf-8")
    runtime = _phase_prompt_fit_runtime(tmp_path, repo_root, data_root, run_id)

    with pytest.raises(FlightRuntimeError, match="64-character"):
        runtime.preflight()


def test_a_flight_that_declares_no_receipt_verifies_nothing(tmp_path):
    """The pre-existing behaviour, unchanged: no keys, no verification, and
    the estimate still runs."""

    runtime = _make_runtime(tmp_path, happy_path=True)
    receipt = runtime.preflight()

    assert receipt["phase_prompt_fit"] is None
    assert receipt["prompt_budget"]


def test_render_phase_prompt_envelopes_reproduces_the_estimator_bytes(tmp_path):
    """One authority for the envelope. ``_phase_prompt_payloads`` (the
    pre-flight ESTIMATE) and ``render_phase_prompt_envelopes`` (what the
    measurement and its verification use) must build the same bytes for the
    same inputs, or a receipt could certify a fit for a prompt the estimate
    never saw."""

    from speech_aware_evidence_acquisition.core.flight.runtime import (
        phase_program_system_text,
        render_phase_prompt_envelopes,
    )
    from speech_aware_evidence_acquisition.rails.controllers import (
        default_phase_program,
    )
    from speech_aware_evidence_acquisition.rails.phase_material import (
        load_phase_material_specs,
        render_static_instruction,
    )

    run_id = "SAEA-TEST-RUN-001"
    repo_root, data_root, _ = _phase_prompt_fit_repo(tmp_path, run_id)
    _write_phase_prompt_fit_receipt(repo_root, data_root)
    runtime = _phase_prompt_fit_runtime(tmp_path, repo_root, data_root, run_id)
    runtime.preflight()

    program = default_phase_program(PHASE_PROGRAM)
    sample = runtime._samples[0]
    estimated = runtime._phase_prompt_payloads((sample,), program)

    specs = load_phase_material_specs(runtime._composed.values, program)
    rendered = render_phase_prompt_envelopes(
        program_id=program.program_id,
        phase_names=program.phase_names(),
        specs=specs,
        static_text_by_phase={
            phase: render_static_instruction(spec, repo_root, {}, data_root)
            for phase, spec in specs.items()
        },
        system_text=phase_program_system_text(runtime._adapter, sample),
        prompt_order="speech-query-prefix-v2",
        packet_descriptor=runtime.speech_packet_bindings()[sample.sample_id],
        sample_id=sample.sample_id,
        completion_token_ceiling=_FakeAdapter.SERVING_MAX_TOKENS,
    )
    for phase in program.phase_names():
        assert (
            json.dumps(list(rendered[phase]), ensure_ascii=False, sort_keys=True).encode(
                "utf-8"
            )
            == estimated[phase]
        )


# ---------------------------------------------------------------------------
# The pre-flight estimate over the WHOLE roster (KC-S1 defect 3, 2026-09-05)
# ---------------------------------------------------------------------------


class _PerSampleAdapter(_FakeAdapter):
    """A fake whose system instruction GROWS with the sample.

    A real roster looks like this -- KC-S1b's per-sample slot block is the
    example that produced the defect -- and an estimate that renders one
    representative row cannot see it.
    """

    WIDE_SAMPLE_ID = "s2"
    WIDE_PAD = "w" * 4000

    def instruction(self, sample) -> str:
        if sample.sample_id == self.WIDE_SAMPLE_ID:
            return f"instruction {self.WIDE_PAD}"
        return "instruction"


_STATE_FILL_NAME = "flight-runtime-test-state-fill"


def _phase_packet_repo(tmp_path, run_id: str, *, phase_material=None):
    """A committed two-phase packet repo with NO pinned prompt-fit receipt --
    the estimate is the only thing under test here."""

    repo_root = tmp_path / "repo"
    data_root = tmp_path / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    promotion_receipt = _write_promotion_receipt(tmp_path)
    _write_configs(
        repo_root,
        arm="speech-feature-query",
        policy=PHASE_PROGRAM,
        model_extra={"speech_feature_root": str(tmp_path / _PROMOTION_DIR)},
        baseline_extra={
            "speech_packet_promotion_receipt": str(promotion_receipt),
            "speech_feature_key_representation_id": "key-rep-v1",
            "speech_feature_matcher_policy_id": "matcher-v1",
            "phase_material": phase_material or _PHASE_MATERIAL,
        },
    )
    for phase, body in (("draft", "Draft the tool call."), ("revise", "Revise it.")):
        template = repo_root / "configs" / "probes" / f"{phase}.txt"
        template.parent.mkdir(parents=True, exist_ok=True)
        template.write_text(body + "\n", encoding="utf-8")
    _write_exposure_ledger(repo_root, run_id)
    _git_init_commit(repo_root)
    return repo_root, data_root


def test_the_phase_estimate_takes_the_max_over_every_sample(tmp_path):
    """The estimate must not under-count a phase cell: it renders every
    sample of the roster and keeps the widest payload per phase."""

    from speech_aware_evidence_acquisition.rails.controllers import (
        default_phase_program,
    )

    run_id = "SAEA-TEST-RUN-001"
    repo_root, _data_root = _phase_packet_repo(tmp_path, run_id)
    runtime = _make_runtime(
        tmp_path,
        run_id=run_id,
        repo_root=repo_root,
        adapter_cls=_PerSampleAdapter,
        happy_path=True,
    )
    receipt = runtime.preflight()
    program = default_phase_program(PHASE_PROGRAM)
    narrow_sample, wide_sample = runtime._samples
    assert wide_sample.sample_id == _PerSampleAdapter.WIDE_SAMPLE_ID

    narrow = runtime._phase_prompt_payloads((narrow_sample,), program)
    wide = runtime._phase_prompt_payloads((wide_sample,), program)
    both = runtime._phase_prompt_payloads(runtime._samples, program)
    reversed_order = runtime._phase_prompt_payloads(
        tuple(reversed(runtime._samples)), program
    )

    for phase in program.phase_names():
        assert len(wide[phase]) - len(narrow[phase]) >= len(_PerSampleAdapter.WIDE_PAD)
        # The max, and it does not depend on roster order.
        assert both[phase] == wide[phase]
        assert reversed_order[phase] == wide[phase]

    # And the receipt the estimate lands is the WIDE payload's, not the
    # representative row's -- payload_sha256 is the exact byte identity.
    wide_digests = {
        phase: hashlib.sha256(payload).hexdigest() for phase, payload in wide.items()
    }
    assert [entry["phase"] for entry in receipt["prompt_budget"]] == list(
        program.phase_names()
    )
    for entry in receipt["prompt_budget"]:
        assert entry["payload_sha256"] == wide_digests[entry["phase"]]
        assert entry["decision"] == "ALLOW"


def test_the_phase_estimate_renders_the_declared_state_fill(tmp_path):
    """A phase declaring a ``state_fill`` sends the fill's per-sample text on
    the wire, so the estimate has to render it too -- not rendering it is
    exactly what made KC-S1b's estimate roughly 7,500 tokens short."""

    from speech_aware_evidence_acquisition.rails.controllers import (
        default_phase_program,
    )
    from speech_aware_evidence_acquisition.rails.phase_material import (
        PHASE_STATE_FILLS,
    )

    fill_text = "F" * 3000
    seen: list[str] = []

    def _factory():
        def _fill(state_content: str) -> str:
            seen.append(state_content)
            return fill_text

        return _fill

    run_id = "SAEA-TEST-RUN-001"
    with_fill = {
        "draft": dict(_PHASE_MATERIAL["draft"]),
        "revise": dict(_PHASE_MATERIAL["revise"], state_fill=_STATE_FILL_NAME),
    }
    repo_root, _data_root = _phase_packet_repo(
        tmp_path, run_id, phase_material=with_fill
    )
    plain_root, _plain_data = _phase_packet_repo(
        tmp_path / "plain", "SAEA-TEST-RUN-002"
    )

    runtime = _make_runtime(
        tmp_path, run_id=run_id, repo_root=repo_root, happy_path=True
    )
    plain = _make_runtime(
        tmp_path / "plain",
        run_id="SAEA-TEST-RUN-002",
        repo_root=plain_root,
        happy_path=True,
    )
    program = default_phase_program(PHASE_PROGRAM)
    PHASE_STATE_FILLS.register(_STATE_FILL_NAME, _factory)
    try:
        runtime.preflight()
        plain.preflight()
        filled = runtime._phase_prompt_payloads(runtime._samples, program)
        unfilled = plain._phase_prompt_payloads(plain._samples, program)
    finally:
        PHASE_STATE_FILLS._entries.pop(_STATE_FILL_NAME, None)

    # The fill is a pure per-sample SUFFIX on the phase that declares it, and
    # the phase that does not declare one is untouched.
    assert filled["draft"] == unfilled["draft"]
    assert len(filled["revise"]) - len(unfilled["revise"]) >= len(fill_text)
    # It is called over the pad that bounds the predecessor this run has not
    # produced yet, once per sample per render.
    assert seen
    assert set(seen) == {"x" * (4 * _FakeAdapter.SERVING_MAX_TOKENS)}


def test_a_state_fill_that_renders_nothing_is_refused() -> None:
    """Fail-closed: a declared fill that renders no text would silently
    under-count the prompt it is part of."""

    from speech_aware_evidence_acquisition.core.flight.runtime import (
        render_phase_prompt_envelopes,
    )
    from speech_aware_evidence_acquisition.rails.phase_material import (
        PhaseMaterialSpec,
    )

    spec = PhaseMaterialSpec(
        phase="revise",
        purpose="revise",
        instruction_template="probes/revise.txt",
        predecessor_binding="append-sealed-state",
    )
    with pytest.raises(FlightRuntimeError, match="rendered no text"):
        render_phase_prompt_envelopes(
            program_id="p",
            phase_names=("revise",),
            specs={"revise": spec},
            static_text_by_phase={"revise": "Revise it."},
            system_text="sys",
            prompt_order="speech-query-prefix-v2",
            packet_descriptor={"packet_id": "s1", "sha256": "s1-sha"},
            sample_id="s1",
            state_fill_by_phase={"revise": lambda content: "   "},
            completion_token_ceiling=8,
        )


def test_render_phase_prompt_envelopes_is_unchanged_without_a_state_fill() -> None:
    """The default is byte-identical, so a prompt-fit receipt measured before
    the seam existed still verifies."""

    from speech_aware_evidence_acquisition.core.flight.runtime import (
        phase_envelope_sha256,
        render_phase_prompt_envelopes,
    )
    from speech_aware_evidence_acquisition.rails.phase_material import (
        PhaseMaterialSpec,
    )

    spec = PhaseMaterialSpec(
        phase="revise",
        purpose="revise",
        instruction_template="probes/revise.txt",
        predecessor_binding="append-sealed-state",
    )
    kwargs = {
        "program_id": "p",
        "phase_names": ("revise",),
        "specs": {"revise": spec},
        "static_text_by_phase": {"revise": "Revise it."},
        "system_text": "sys",
        "prompt_order": "speech-query-prefix-v2",
        "packet_descriptor": {"packet_id": "s1", "sha256": "s1-sha"},
        "sample_id": "s1",
        "completion_token_ceiling": 8,
    }
    default = render_phase_prompt_envelopes(**kwargs)
    explicit_none = render_phase_prompt_envelopes(**kwargs, state_fill_by_phase=None)
    empty = render_phase_prompt_envelopes(**kwargs, state_fill_by_phase={})
    assert phase_envelope_sha256(default["revise"]) == phase_envelope_sha256(
        explicit_none["revise"]
    )
    assert phase_envelope_sha256(default["revise"]) == phase_envelope_sha256(
        empty["revise"]
    )


def test_the_fixed_policy_estimate_is_byte_identical_to_the_direct_payload(tmp_path):
    """``policy == "fixed"`` never enters ``_phase_prompt_payloads``: the
    estimate is still ONE representative ``assemble_prompt``, over one
    ``direct`` phase."""

    promotion_receipt = _write_promotion_receipt(tmp_path)
    runtime = _make_runtime(
        tmp_path,
        happy_path=True,
        adapter_cls=_PerSampleAdapter,
        config_kwargs=_packet_config_kwargs(tmp_path, promotion_receipt),
    )

    def _refuse(*args, **kwargs):
        raise AssertionError("the fixed policy must not render phase payloads")

    runtime._phase_prompt_payloads = _refuse
    receipt = runtime.preflight()

    representative = runtime._samples[0]
    expected = hashlib.sha256(
        json.dumps(
            list(runtime._adapter.assemble_prompt(representative, None)),
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    assert [entry["phase"] for entry in receipt["prompt_budget"]] == ["direct"]
    assert receipt["prompt_budget"][0]["payload_sha256"] == expected


def test_the_phase_estimate_passes_fill_params_to_the_state_fill_factory(tmp_path):
    """``fill_params`` reach the FACTORY on the flight path
    (``rails.phase_material._resolved_state_fills``), and the prompt-budget
    estimate has to call it the same way. It did not, and the divergence was
    fail-closed rather than cosmetic: EVO-S1's evolved fill opens a committed
    artifact named by ``artifact_relpath``/``artifact_sha256`` and cannot be
    built without them, so the one pre-flight stage whose job is to render the
    widest real request died before the arm it was budgeting for could fly."""

    from speech_aware_evidence_acquisition.rails.controllers import (
        default_phase_program,
    )
    from speech_aware_evidence_acquisition.rails.phase_material import (
        PHASE_STATE_FILLS,
    )

    got: list[dict] = []

    def _factory(**params):
        got.append(dict(params))
        if "artifact_relpath" not in params:
            raise TypeError("missing required keyword-only argument: 'artifact_relpath'")

        def _fill(state_content: str) -> str:
            return "F" * 128

        return _fill

    name = "test-fill-with-params-v1"
    run_id = "SAEA-TEST-RUN-003"
    with_fill = {
        "draft": dict(_PHASE_MATERIAL["draft"]),
        "revise": dict(
            _PHASE_MATERIAL["revise"],
            state_fill=name,
            fill_params={"artifact_relpath": "configs/knowledge/x.json",
                         "artifact_sha256": "0" * 64},
        ),
    }
    repo_root, _data_root = _phase_packet_repo(tmp_path, run_id, phase_material=with_fill)
    runtime = _make_runtime(tmp_path, run_id=run_id, repo_root=repo_root, happy_path=True)
    program = default_phase_program(PHASE_PROGRAM)
    PHASE_STATE_FILLS.register(name, _factory)
    try:
        runtime.preflight()
        runtime._phase_prompt_payloads(runtime._samples, program)
    finally:
        PHASE_STATE_FILLS._entries.pop(name, None)

    assert got and got[0] == {
        "artifact_relpath": "configs/knowledge/x.json",
        "artifact_sha256": "0" * 64,
    }


# ---------------------------------------------------------------------------
# The per-sample decoding_params.max_tokens seam (E22 cell (b), 2026-09-06).
#
# A fragment normally declares one integer cap for the whole cell. It may
# instead declare a rule object naming a core.base.MAX_TOKENS_POLICIES id, and
# this runtime resolves it to an integer per sample from that sample's own
# audio_seconds -- in the same three places it already resolves the id_slot
# slot-affinity sentinel. See core.flight.runtime.MAX_TOKENS_POLICY_KEY.
# ---------------------------------------------------------------------------


_DURATION_RULE = {
    "policy": "duration-proportional-v1",
    "alpha": 1.5,
    "words_per_second_p95": 4.999220954734555,
    "tokens_per_word": 1.2991996296395218,
    "floor": 1,
    "ceiling": 1024,
}


class _TwoDurationAdapter(_FakeAdapter):
    """Two samples whose durations differ, so a per-sample cap is observable as
    two different integers rather than one repeated one."""

    def __init__(self, lock, root: Path) -> None:
        super().__init__(lock, root)
        self.samples = (
            _FakeSample("s1", audio_seconds=5.0),
            _FakeSample("s2", audio_seconds=32.88),
        )


class _EchoingDecodingClient(_TransportDrivingClient):
    """Like ``_TransportDrivingClient``, but the payload it emits carries the
    decoding params it was actually HANDED and the real sample's own
    ``sample_id``/``audio_seconds`` -- recovered from the audio part's
    ``media_relpath``, exactly as the real ``FrozenCoreClient`` recovers them
    from the sample binding. Without that the wire check would be asserting
    against a fixture instead of against what crossed the seam."""

    _DURATIONS = {"s1": 5.0, "s2": 32.88}

    def complete(self, messages, **kwargs):
        payload = {field: "x" for field in self._arm_fields}
        media_relpath = ""
        for message in messages:
            content = message.get("content")
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, Mapping) and part.get("type") == "input_audio":
                        media_relpath = str(part.get("media_relpath") or "")
        sample_id = media_relpath.rsplit("/", 1)[-1].removesuffix(".wav")
        payload["sample_id"] = sample_id
        payload["media_relpath"] = media_relpath
        payload["audio_seconds"] = self._DURATIONS.get(sample_id, 2.0)
        decoding = dict(kwargs.get("decoding_params") or {})
        decoding.setdefault("id_slot", 0)
        payload["decoding_params"] = decoding
        response = json.loads(
            self._transport(json.dumps(payload).encode("utf-8")).decode("utf-8")
        )
        calls = response.get("tool_calls")
        with self._lock:
            self.timings = tuple(self.timings) + (
                _FakeTiming(
                    sample_id=sample_id or f"s{len(self.timings) + 1}",
                    request_id=f"req-{len(self.timings) + 1:04d}",
                    native_tool_calls=len(calls) if isinstance(calls, list) else None,
                ),
            )
        return "resp"


def _cap_runtime(tmp_path, max_tokens, **kwargs):
    adapter_cls = kwargs.pop("adapter_cls", _TwoDurationAdapter)
    config_kwargs = {
        "arm": "bare-core",
        "policy": "fixed",
        "model_extra": {
            "decoding_params": {
                "temperature": 0,
                "seed": 20260803,
                "max_tokens": max_tokens,
                "id_slot": "per-sample",
            }
        },
    }
    config_kwargs.update(kwargs.pop("config_kwargs", {}))
    return _wire_runtime(
        tmp_path,
        adapter_cls=adapter_cls,
        client_factory=_EchoingDecodingClient,
        config_kwargs=config_kwargs,
        **kwargs,
    )


def test_request_completion_override_changes_payload_and_preflight_reserve(tmp_path):
    baseline = _cap_runtime(tmp_path / "base", 64)
    widened = _cap_runtime(
        tmp_path / "wide", 64,
        config_kwargs={
            "arm": "bare-core",
            "policy": "fixed",
            "model_extra": {
                "decoding_params": {
                    "temperature": 0,
                    "seed": 20260803,
                    "max_tokens": 64,
                    "id_slot": "per-sample",
                }
            },
            "experiment_extra": {"request_decoding_overrides": {"max_tokens": 256}},
        },
    )
    base_receipt = baseline.wire_check(seal_and_score=False)
    wide_receipt = widened.wire_check(seal_and_score=False)
    assert base_receipt["max_tokens"] == 64
    assert wide_receipt["max_tokens"] == 256
    assert baseline._completion_token_ceiling() == 64
    assert widened._completion_token_ceiling() == 256
    assert base_receipt["request_body_sha256"] != wide_receipt["request_body_sha256"]
    budget = widened._assess_prompt_budget(widened._samples)
    assert budget[0]["breakdown"]["completion_token_ceiling"] == 256


def test_completion_override_preserves_the_legacy_adapter_reserve_when_absent(tmp_path):
    legacy = _cap_runtime(tmp_path / "legacy", 64, adapter_cls=_LegacyWideBudgetFakeAdapter)
    overridden = _cap_runtime(
        tmp_path / "override", 64, adapter_cls=_LegacyWideBudgetFakeAdapter,
        config_kwargs={
            "arm": "bare-core", "policy": "fixed",
            "model_extra": {"decoding_params": {"max_tokens": 64}},
            "experiment_extra": {"request_decoding_overrides": {"max_tokens": 256}},
        },
    )
    legacy._prepare()
    overridden._prepare()
    assert legacy._completion_token_ceiling() == 512
    assert overridden._completion_token_ceiling() == 256


@pytest.mark.parametrize(
    "override",
    [{"server_args": []}, {"max_tokens": True}, {"max_tokens": 0}],
)
def test_request_completion_override_refuses_unknown_boolean_or_nonpositive(tmp_path, override):
    runtime = _cap_runtime(
        tmp_path,
        64,
        config_kwargs={
            "arm": "bare-core",
            "policy": "fixed",
            "model_extra": {"decoding_params": {"max_tokens": 64}},
            "experiment_extra": {"request_decoding_overrides": override},
        },
    )
    runtime._prepare()
    with pytest.raises(Exception, match="request_decoding_overrides"):
        runtime._decoding_params()


def test_a_plain_integer_max_tokens_is_handed_on_by_identity(tmp_path):
    """Byte identity, at the seam itself: with no rule declared the resolver
    returns the SAME mapping object it was given, so nothing is rebuilt, no key
    is reordered, and a fragment that predates this seam renders exactly the
    request it always did."""

    runtime = _cap_runtime(tmp_path, 1024)
    runtime._prepare()
    base = runtime._decoding_params()
    assert base["max_tokens"] == 1024
    for sample in runtime._samples:
        assert runtime._sample_decoding_params(sample, base) is base


def test_a_per_sample_rule_resolves_from_each_samples_own_audio_seconds(tmp_path):
    """Two samples, two durations, two different caps -- and each is the
    integer the registered policy resolves for THAT sample."""

    runtime = _cap_runtime(tmp_path, dict(_DURATION_RULE))
    receipt = runtime.wire_check(seal_and_score=False)

    assert receipt["max_tokens_policy"] == "duration-proportional-v1"
    assert receipt["max_tokens_rule"] == _DURATION_RULE
    # 5.00 s -> 49 tokens and 32.88 s -> 321, the ladder section 2.1 of the
    # preregistration published before any capped request existed.
    assert receipt["max_tokens_per_sample"] == {"s1": 49, "s2": 321}
    assert receipt["max_tokens"] in (49, 321)


def test_a_token_matched_rule_dispatches_byte_identically_to_the_integer(tmp_path):
    """The byte-identity pin. A rule whose floor and ceiling force every sample
    to 1,024 must produce the SAME request bytes as the plain integer 1,024:
    the seam moves the resolution of ``max_tokens`` and nothing else about the
    request."""

    plain = _cap_runtime(tmp_path / "plain", 1024).wire_check(seal_and_score=False)
    ruled = _cap_runtime(
        tmp_path / "ruled", dict(_DURATION_RULE, floor=1024, ceiling=1024)
    ).wire_check(seal_and_score=False)

    assert plain["request_body_sha256"] == ruled["request_body_sha256"]
    assert plain["max_tokens"] == ruled["max_tokens"] == 1024
    assert plain["max_tokens_per_sample"] is None
    assert ruled["max_tokens_per_sample"] == {"s1": 1024, "s2": 1024}


def test_the_serial_rails_path_resolves_the_cap_per_sample(tmp_path):
    """``workers=1`` dispatches through ``rails.runner.run_rails_experiment``
    rather than the concurrent dispatcher, so the resolver has to reach that
    path too -- it travels there as a per-sample callable."""

    runtime = _cap_runtime(tmp_path, dict(_DURATION_RULE))
    receipt = runtime.wire_check(seal_and_score=False, workers=1)

    assert receipt["dispatch"]["dispatch"] == "serial"
    assert receipt["max_tokens_per_sample"] == {"s1": 49, "s2": 321}


def test_the_serial_rails_path_passes_a_plain_mapping_through_unchanged(tmp_path):
    """And with no rule declared the runner is handed the mapping itself, not a
    resolver -- the serial half of the byte-identity pin."""

    seen: dict[str, object] = {}

    def _recording_rails_runner(**kwargs):
        seen["decoding_params"] = kwargs.get("decoding_params")
        return _calling_rails_runner(**kwargs)

    runtime = _cap_runtime(tmp_path, 1024, rails_runner=_recording_rails_runner)
    runtime.wire_check(seal_and_score=False, workers=1)

    assert not callable(seen["decoding_params"])
    assert seen["decoding_params"] == {
        "temperature": 0,
        "seed": 20260803,
        "max_tokens": 1024,
        "id_slot": 0,
    }


def test_an_unregistered_max_tokens_policy_is_refused(tmp_path):
    runtime = _cap_runtime(tmp_path, dict(_DURATION_RULE, policy="cap-by-vibes"))
    runtime._prepare()
    with pytest.raises(FlightRuntimeError, match="unknown max-tokens policy"):
        runtime._decoding_params()


def test_a_max_tokens_rule_without_a_policy_id_is_refused(tmp_path):
    rule = {key: value for key, value in _DURATION_RULE.items() if key != "policy"}
    runtime = _cap_runtime(tmp_path, rule)
    runtime._prepare()
    with pytest.raises(FlightRuntimeError, match="registered in core.base"):
        runtime._decoding_params()


def test_a_malformed_max_tokens_rule_is_refused_before_any_sample_runs(tmp_path):
    runtime = _cap_runtime(tmp_path, dict(_DURATION_RULE, alpha=0))
    runtime._prepare()
    with pytest.raises(FlightRuntimeError, match="alpha"):
        runtime._decoding_params()


def test_a_max_tokens_that_is_neither_an_integer_nor_a_rule_is_refused(tmp_path):
    runtime = _cap_runtime(tmp_path, "1024")
    runtime._prepare()
    with pytest.raises(FlightRuntimeError, match="integer or a per-sample rule"):
        runtime._decoding_params()


def test_a_phase_program_refuses_a_per_sample_max_tokens_rule(tmp_path):
    """The seam resolves where a fixed direct arm builds its request. A phase
    program's contacts are built by ``rails.phase_runner`` from ONE run-level
    mapping, so a rule there would travel unresolved and die at the first
    contact -- after a server start. Refused before one."""

    runtime = _cap_runtime(tmp_path, dict(_DURATION_RULE))
    runtime._prepare()
    with pytest.raises(FlightRuntimeError, match="fixed-policy direct-arm seam"):
        runtime._phase_decoding_params()


# ---------------------------------------------------------------------------
# E7: the always-on serving session (owner rule 2026-09-07).
#
# A flight that finds the coordinator's resident server ATTACHES to it, never
# stops it, and seals the monitor summary for its own contact window. A
# resident server serving something else is a refusal naming the differing
# field, never a second 18.5 GB spawn. A host with no serving session keeps
# today's behaviour exactly: spawn, own, stop.
# ---------------------------------------------------------------------------


_SERVING_FRAGMENT = {
    "runtime_receipt": "receipts/runtime-fake.json",
    # -c / -np agree with _FakeAdapter's own geometry (2 slots x 4096).
    "server_args": ["-c", "8192", "-np", "2", "-ngl", "999"],
    "serving_geometry": {"slots": 2, "slot_tokens": 4096, "max_tokens": 64},
    "server_env": {"GGML_CUDA_DISABLE_GRAPHS": "1"},
}

_SERVING_RUN_ID = "SAEA-TEST-SERVING"


class _SteppingClock:
    """A deterministic wall clock: every call advances by ``step``."""

    def __init__(self, start: float = 1000.0, step: float = 10.0) -> None:
        self._next = start
        self._step = step

    def __call__(self) -> float:
        value = self._next
        self._next += self._step
        return value


def _write_parked_monitor(path: Path, *, start: float, count: int, step: float) -> None:
    """A monitor JSONL in which every sample is PARKED (no busy slot, cold
    card), so a summary over any sub-window of it must report a parked
    fraction of exactly 1.0."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for index in range(count):
            handle.write(
                json.dumps(
                    {
                        "schema": "saea-serving-monitor-sample-v1",
                        "sampled_at": start + index * step,
                        "gpu": {
                            "utilization_percent": 0.0,
                            "power_watts": 32.0,
                            "memory_used_mib": 18000.0,
                        },
                        "slots": {"total": 2, "busy": 0, "idle": 2},
                        "metrics": None,
                        "requests_total": index,
                        "server_ok": True,
                    },
                    sort_keys=True,
                )
                + "\n"
            )


def _serving_world(tmp_path: Path):
    """A repo whose model fragment declares a real serving profile, plus the
    runtime root / data root / runtime receipt that profile resolves to.

    ``runtime_root``/``data_root`` are the SAME two paths ``_make_runtime``
    hands every flight in this module (``tmp_path/runtime``, ``tmp_path/
    data``), so a runtime built by that helper resolves exactly these files.
    """

    repo_root = _make_repo(tmp_path, _SERVING_RUN_ID, model_extra=dict(_SERVING_FRAGMENT))
    runtime_root = tmp_path / "runtime"
    data_root = tmp_path / "data"
    binary = runtime_root / "llama.cpp" / "build" / "bin" / "llama-server"
    binary.parent.mkdir(parents=True, exist_ok=True)
    binary.write_bytes(b"fake-llama-server")
    model_relpath = "models/fake/model.gguf"
    (data_root / model_relpath).parent.mkdir(parents=True, exist_ok=True)
    (data_root / model_relpath).write_bytes(b"fake-main-gguf")

    receipt = {
        "schema": "saea-runtime-receipt-v2",
        "study": "speech-aware-evidence-acquisition",
        "llama_cpp": {
            "binary_path": "llama.cpp/build/bin/llama-server",
            "binary_sha256": hashlib.sha256(b"fake-llama-server").hexdigest(),
        },
        "gguf_files": [
            {"path": model_relpath, "sha256": hashlib.sha256(b"fake-main-gguf").hexdigest()}
        ],
    }
    receipt_path = repo_root / "docs" / "receipts" / "runtime-fake.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-q", "-m", "serving profile")
    return repo_root, runtime_root, data_root


def _write_serving_session(
    repo_root: Path,
    runtime_root: Path,
    data_root: Path,
    *,
    session_id: str = "serving-test",
    argv_overrides: Mapping[str, str] | None = None,
    pid: int = 4242,
) -> Path:
    """The session document the OPERATOR path writes -- built through
    ``resolve_serving_profile`` + ``build_server_command``, the same two
    functions ``scripts/serving_session.sh`` calls, so these tests prove the
    operator path and the flight path agree rather than comparing a function
    with itself."""

    from speech_aware_evidence_acquisition.core.session import build_server_command
    from speech_aware_evidence_acquisition.core.session.serving import (
        SESSION_DOCUMENT_NAME,
        build_session_document,
        resolve_serving_profile,
        serving_identity,
        serving_session_dir,
        write_json_document,
    )

    profile = resolve_serving_profile(repo_root, "m")
    command = build_server_command(
        runtime_root=runtime_root,
        data_root=data_root,
        runtime_receipt=profile["runtime_receipt"],
        host="127.0.0.1",
        port=8080,
        extra_argv=tuple(profile["extra_argv"]),
        extra_env=dict(profile["server_env"]),
        role=str(profile["session_role"]),
    )
    argv = list(command.argv)
    for flag, value in dict(argv_overrides or {}).items():
        argv[argv.index(flag) + 1] = value
    geometry = dict(profile["serving_geometry"])
    identity = serving_identity(
        model_fragment="m",
        model_fragment_sha256=str(profile["model_fragment_sha256"]),
        runtime_receipt_relpath=str(profile["runtime_receipt_relpath"]),
        runtime_receipt_sha256=str(profile["runtime_receipt_sha256"]),
        binary_path=command.binary_path,
        binary_sha256=command.binary_sha256,
        model_files=[{"path": e.path, "sha256": e.sha256} for e in command.model_files],
        session_role=str(profile["session_role"]),
        model_root=profile["model_root"],
        server_argv=argv,
        server_env=dict(profile["server_env"]),
        host="127.0.0.1",
        port=8080,
        props={
            "total_slots": int(geometry["slots"]),
            "default_generation_settings": {
                "n_ctx": int(argv[argv.index("-c") + 1]) // int(geometry["slots"])
            },
            "model_path": argv[argv.index("-m") + 1],
            "build_info": "version: 1 (04ccc72a)",
        },
    )
    session_dir = serving_session_dir(data_root, session_id)
    write_json_document(
        session_dir / SESSION_DOCUMENT_NAME,
        build_session_document(
            session_id=session_id,
            identity=identity,
            pid=pid,
            started_at="2026-09-07T00:00:00+00:00",
            serving_geometry=geometry,
            props=None,
            session_receipt_path=str(session_dir / "session-receipt.json"),
            server_log_path=str(session_dir / "server.log"),
            monitor_path=str(session_dir / "monitor.jsonl"),
        ),
    )
    return session_dir


class _CountingStarter:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, **kwargs: object) -> _FakeSession:
        self.calls += 1
        return _FakeSession(str(kwargs["session_id"]))


def _serving_runtime(tmp_path, repo_root, **overrides):
    starter = _CountingStarter()
    attached: list[Path] = []

    def _attacher(receipt_path, **_kwargs):
        attached.append(Path(receipt_path))
        return _FakeSession("resident-session", pid=4242)

    kwargs: dict[str, object] = {
        "session_starter": starter,
        "session_attacher": _attacher,
        "runtime_receipt_loader": lambda path: json.loads(Path(path).read_text(encoding="utf-8")),
    }
    kwargs.update(overrides)
    runtime = _make_runtime(
        tmp_path,
        run_id=_SERVING_RUN_ID,
        attempt_id="attempt-serving",
        happy_path=True,
        repo_root=repo_root,
        **kwargs,
    )
    return runtime, starter, attached


def test_a_flight_attaches_to_a_matching_resident_serving_session(tmp_path):
    repo_root, runtime_root, data_root = _serving_world(tmp_path)
    session_dir = _write_serving_session(repo_root, runtime_root, data_root)
    runtime, starter, attached = _serving_runtime(tmp_path, repo_root)

    runtime.preflight()
    runtime.preprocess()
    receipt = runtime.serve()

    assert starter.calls == 0, "attaching must never spawn a second server"
    assert attached == [session_dir / "session-receipt.json"]
    assert receipt["session_reused"] is True
    assert receipt["session_source"] == "attached-serving-session"
    assert receipt["session_id"] == "serving-test"
    assert receipt["serving_session_dir"] == str(session_dir)
    assert receipt["startup_seconds"] == 0.0
    # A flight NEVER stops the coordinator's server.
    assert runtime._owns_session is False
    assert runtime.stop_serving() is None


def test_the_attach_receipt_lands_beside_the_attempt(tmp_path):
    repo_root, runtime_root, data_root = _serving_world(tmp_path)
    _write_serving_session(repo_root, runtime_root, data_root)
    runtime, _starter, _attached = _serving_runtime(tmp_path, repo_root)
    runtime.preflight()
    runtime.preprocess()
    receipt = runtime.serve()

    path = Path(receipt["session_attach_receipt_path"])
    document = json.loads(path.read_text(encoding="utf-8"))
    assert document["schema"] == "saea-session-attach-receipt-v1"
    assert document["session_reused"] is True
    assert document["session_id"] == "serving-test"
    assert document["run_id"] == _SERVING_RUN_ID
    assert document["monitor_summary"] is None  # filled at seal
    assert document["identity"]["server_argv"][0].endswith("llama-server")


def test_a_resident_session_with_a_different_context_size_is_refused_by_name(tmp_path):
    repo_root, runtime_root, data_root = _serving_world(tmp_path)
    _write_serving_session(repo_root, runtime_root, data_root, argv_overrides={"-c": "40960"})
    runtime, starter, _attached = _serving_runtime(tmp_path, repo_root)
    runtime.preflight()
    runtime.preprocess()

    with pytest.raises(FlightServingSessionMismatchError) as excinfo:
        runtime.serve()
    assert "server_argv[-c]" in str(excinfo.value)
    fields = [entry["field"] for entry in excinfo.value.mismatches]
    assert "server_argv[-c]" in fields
    assert "props_identity.slot_n_ctx" in fields
    assert starter.calls == 0, "a mismatch must never fall back to a second spawn"


def test_a_flight_with_no_resident_session_still_spawns_and_owns_its_own(tmp_path):
    repo_root, _runtime_root, _data_root = _serving_world(tmp_path)
    runtime, starter, attached = _serving_runtime(tmp_path, repo_root)
    runtime.preflight()
    runtime.preprocess()
    receipt = runtime.serve()

    assert starter.calls == 1
    assert attached == []
    assert receipt["session_reused"] is False
    assert receipt["session_source"] == "spawned"
    assert runtime._owns_session is True


def test_the_seal_receipt_carries_the_monitor_summary_for_this_attempts_window(tmp_path):
    repo_root, runtime_root, data_root = _serving_world(tmp_path)
    session_dir = _write_serving_session(repo_root, runtime_root, data_root)
    _write_parked_monitor(session_dir / "monitor.jsonl", start=1000.0, count=60, step=10.0)

    runtime, _starter, _attached = _serving_runtime(
        tmp_path, repo_root, clock=_SteppingClock(start=1100.0, step=10.0)
    )
    runtime.run_all()

    window = runtime.receipts.require("run_phases")["contact_window"]
    seal = runtime.receipts.require("seal")
    summary = seal["serving_monitor_summary"]
    assert summary is not None
    assert summary["schema"] == "saea-serving-monitor-summary-v1"
    assert summary["window"] == {"from": window["from"], "to": window["to"]}
    assert summary["sample_count"] >= 2
    # Every sample in the file is parked (idle slots, cold card).
    assert summary["parked_fraction"] == 1.0
    assert summary["active_seconds"] == 0.0
    assert seal["session_reused"] is True

    document = json.loads(
        Path(seal["session_attach_receipt_path"]).read_text(encoding="utf-8")
    )
    assert document["monitor_summary"]["parked_fraction"] == 1.0
    assert document["contact_window"] == {"from": window["from"], "to": window["to"]}


def test_a_spawning_flight_seals_no_monitor_summary(tmp_path):
    repo_root, _runtime_root, _data_root = _serving_world(tmp_path)
    runtime, _starter, _attached = _serving_runtime(tmp_path, repo_root)
    runtime.run_all()
    assert runtime.receipts.require("seal")["serving_monitor_summary"] is None
    assert runtime.receipts.require("seal")["session_reused"] is False
    assert runtime.serving_monitor_summary() is None


# ---------------------------------------------------------------------------
# An attached flight must never take the coordinator's server with it
# (E7b defect 3, 2026-09-07).
#
# The suspicion was that an attached flight's teardown had killed the
# resident server: in the test session llama-server was found <defunct>
# shortly after the flight finalized. The session's own records say
# otherwise -- the server logged "all slots are idle" for 27 more minutes
# after that flight's receipts were written (11:20:08Z), the monitor still
# saw eight idle slots at 11:47:19Z, and its final log line is llama.cpp's
# graceful signal-handler shutdown at ~11:47:25Z, matching the coordinator's
# own record that its first `stop` sent SIGTERM there. The dev session died
# the same way. The flight teardown never reached the server.
#
# The invariant is worth pinning anyway, because nothing else would notice
# if it broke: the two tests below drive a real flight process -- attach,
# phases, seal, stop_serving, and the interpreter exiting -- past a fake
# server that records every signal it receives, and require that it records
# none. The fake shares this test's process group, so a stray killpg or a
# teardown that signalled the inherited pid would be caught too.
# ---------------------------------------------------------------------------

_SIGNAL_RECORDING_SERVER = """
import os
import signal
import sys
import time

record_path, ready_path = sys.argv[1], sys.argv[2]


def _record(signum, _frame):
    with open(record_path, "a", encoding="utf-8") as handle:
        handle.write("%d\\n" % signum)
        handle.flush()


for name in ("SIGTERM", "SIGINT", "SIGHUP"):
    number = getattr(signal, name, None)
    if number is not None:
        signal.signal(number, _record)
with open(ready_path, "w", encoding="utf-8") as handle:
    handle.write(str(os.getpid()))
deadline = time.time() + 180.0
while time.time() < deadline:
    time.sleep(0.05)
"""


# The flight side, run as its own process so that "the flight exits" is a
# real process exit (atexit handlers, garbage collection, the lot) rather
# than a function returning.
_ATTACHED_FLIGHT = '''
import importlib.util
import json
import os
import signal
import sys
from pathlib import Path

test_module_path, world, server_pid, result_path = sys.argv[1:5]
world = Path(world)
server_pid = int(server_pid)

spec = importlib.util.spec_from_file_location("saea_flight_runtime_tests", test_module_path)
tests = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tests)

repo_root, runtime_root, data_root = tests._serving_world(world)
tests._write_serving_session(repo_root, runtime_root, data_root, pid=server_pid)

signalled = []


def trap_stopper(session, **_kwargs):
    """What stopping the resident server would actually do."""

    signalled.append(session.pid)
    os.kill(session.pid, signal.SIGTERM)
    return {"termination_signal": "SIGTERM"}


def attacher(receipt_path, **_kwargs):
    return tests._FakeSession("resident-session", pid=server_pid)


runtime, starter, _attached = tests._serving_runtime(
    world,
    repo_root,
    session_attacher=attacher,
    session_stopper=trap_stopper,
)
runtime.run_all()
# Exactly what scripts/flights/run_e22_esb_cell.py does in its finally.
stopped = runtime.stop_serving()
Path(result_path).write_text(
    json.dumps(
        {
            "serve": dict(runtime.receipts.require("serve")),
            "stop_serving": stopped,
            "signalled": signalled,
            "owns_session": runtime._owns_session,
            "spawns": starter.calls,
        },
        default=str,
    ),
    encoding="utf-8",
)
'''


def _start_signal_recording_server(tmp_path: Path):
    """A stand-in for the coordinator's llama-server: a process this test
    does not own the way a flight does not own it, recording every signal it
    is sent."""

    script = tmp_path / "fake_server.py"
    script.write_text(_SIGNAL_RECORDING_SERVER, encoding="utf-8")
    record = tmp_path / "signals.txt"
    ready = tmp_path / "server.pid"
    process = subprocess.Popen(
        [sys.executable, str(script), str(record), str(ready)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.monotonic() + 30.0
    while not ready.is_file():
        if time.monotonic() >= deadline or process.poll() is not None:
            process.kill()
            raise AssertionError("the fake server never came up")
        time.sleep(0.02)
    return process, record


@pytest.mark.skipif(os.name == "nt", reason="signal delivery semantics are POSIX")
def test_an_attached_flight_process_never_signals_the_resident_server(tmp_path):
    server, record = _start_signal_recording_server(tmp_path)
    try:
        world = tmp_path / "world"
        world.mkdir()
        result_path = tmp_path / "flight-result.json"
        flight_script = tmp_path / "flight.py"
        flight_script.write_text(_ATTACHED_FLIGHT, encoding="utf-8")
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        completed = subprocess.run(
            [
                sys.executable,
                str(flight_script),
                str(Path(__file__).resolve()),
                str(world),
                str(server.pid),
                str(result_path),
            ],
            capture_output=True,
            text=True,
            timeout=300,
            env=environment,
        )
        assert completed.returncode == 0, completed.stderr[-4000:]

        result = json.loads(result_path.read_text(encoding="utf-8"))
        assert result["serve"]["session_source"] == "attached-serving-session"
        assert result["spawns"] == 0, "attaching must never spawn a second server"
        assert result["owns_session"] is False
        assert result["stop_serving"] is None, "an attached flight stops nothing"
        assert result["signalled"] == [], "the stopper was never reached"

        # The flight process is gone; the server it attached to is not.
        deadline = time.monotonic() + 10.0
        while server.poll() is None and time.monotonic() < deadline:
            time.sleep(0.05)
        assert server.poll() is None, "the coordinator's server outlives every flight"
        # The recorder writes the file only when it is signalled at all.
        received = record.read_text(encoding="utf-8") if record.is_file() else ""
        assert received == "", (
            f"an attached flight sent the resident server signal(s): {received!r}"
        )
    finally:
        server.kill()
        server.wait(timeout=10)


def test_stop_serving_refuses_outright_if_a_flight_ever_claims_an_attached_session(tmp_path):
    """The second guard, exercised directly.

    ``_owns_session`` is false for every attached flight, so this state is
    unreachable today; the guard exists because the failure it prevents is
    the coordinator's whole GPU day, and a future serve path that set the
    flag would otherwise stop the resident server silently.
    """

    repo_root, runtime_root, data_root = _serving_world(tmp_path)
    _write_serving_session(repo_root, runtime_root, data_root)
    runtime, _starter, _attached = _serving_runtime(tmp_path, repo_root)
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()

    runtime._owns_session = True  # the bug this guard is here to survive
    with pytest.raises(FlightRuntimeError, match="always-on serving session"):
        runtime.stop_serving()


# ---------------------------------------------------------------------------
# The Earnings carrier path (owner Decision 12-F item #9, 2026-09-08)
# ---------------------------------------------------------------------------
#
# Earnings used to be the one carrier outside this harness: it flew on plain
# Python through ``core.driver.run.run_experiment`` with its own receipt
# shape, while SLURP and Audio2Tool flew here. #9 moves it inside WITHOUT
# giving it a second obs implementation -- ``run_phases`` dispatches an obs
# policy through the SAME obs driver, and this harness contributes the
# envelope that driver never had (preflight, preprocess, attach to the
# resident session, seal, score once through core.scoring_batch).
#
# What these tests pin is exactly that: the branch is taken for every
# registered obs policy, the driver receives THIS flight's own composed
# config / plan / gate / lock / data root / run dir / transport, no
# FrozenCoreClient is built (it would open the attempt a second time), the
# sealed rows are the driver's own rows unmodified, and seal reads the
# driver's RunResult instead of closing a client the obs path never had.

_OBS_BASELINE_EXTRA: dict[str, object] = {
    "obs_buffer_seconds": 90,
    "obs_min_advance_seconds": 20,
    "obs_max_advance_seconds": 55,
    "obs_boundary_mode": "fixed",
    "obs_vad_trim_min_seconds": 0,
    "obs_condition_tail_chars": 0,
    "obs_batch_samples": 1,
    "obs_batch_slices": 8,
    "obs_prefetch_depth": 1,
}

_OBS_ROWS = (
    {
        "request_id": "req-0001",
        "sample_id": "s1",
        "carrier_lock_key": "fake-carrier",
        "arm": "test-arm",
        "text": "stitched one",
        "admitted": True,
        "request_sha256": "a" * 64,
        "response_sha256": "b" * 64,
        "response_text_sha256": "c" * 64,
    },
    {
        "request_id": "req-0002",
        "sample_id": "s2",
        "carrier_lock_key": "fake-carrier",
        "arm": "test-arm",
        "text": "stitched two",
        "admitted": True,
        "request_sha256": "d" * 64,
        "response_sha256": "e" * 64,
        "response_text_sha256": "f" * 64,
    },
)


def _fake_obs_runner(seen: dict):
    """Stand in for ``core.driver.run.run_experiment`` and record exactly
    what the flight handed it. Writes the outputs file the real driver
    writes, in the real driver's own field set and byte shape."""

    from speech_aware_evidence_acquisition.core.base import RunResult

    def _runner(composed, plan, gate, lock, root, run_dir, transport, *, repo_root):
        seen.update(
            composed=composed,
            plan=plan,
            gate=gate,
            lock=lock,
            root=root,
            run_dir=run_dir,
            transport=transport,
            repo_root=repo_root,
        )
        outputs_path = Path(run_dir) / f"{plan.run_id}.outputs.jsonl"
        outputs_path.parent.mkdir(parents=True, exist_ok=True)
        with outputs_path.open("w", encoding="utf-8") as handle:
            for row in _OBS_ROWS:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        return RunResult(
            run_id=plan.run_id,
            arm=composed.values["arm"],
            outputs_path=outputs_path,
            trace_manifest_hash="9" * 64,
            cost={
                "calls_used": 6,
                "audio_seconds_used": 540.0,
                "latency_seconds_total": 3.0,
                "completion_tokens_total": 1200,
                "saturated_slice_count": 0,
                "skipped_slice_count": 1,
            },
        )

    return _runner


def _obs_runtime(tmp_path, seen, *, policy="obs-agent-loop-ojw", **overrides):
    kwargs = dict(
        happy_path=True,
        config_kwargs={
            "policy": policy,
            "baseline_extra": dict(_OBS_BASELINE_EXTRA),
        },
        obs_runner=_fake_obs_runner(seen),
    )
    kwargs.update(overrides)
    return _make_runtime(tmp_path, **kwargs)


@pytest.mark.parametrize(
    "policy",
    ("obs-agent-loop", "obs-agent-loop-ojw", "obs-repair-loop", "obs-repair-loop-ojw"),
)
def test_run_phases_routes_every_obs_policy_through_the_obs_driver(tmp_path, policy):
    """All four registered obs policies -- the two executors times the two
    passes -- reach the obs driver, and none of them reaches the rails
    runner, the phase runner or the client factory."""

    calls = {"rails_runner": 0, "phase_runner": 0, "client_factory": 0}

    def _rails(**kwargs):
        calls["rails_runner"] += 1
        return _fake_rails_runner(**kwargs)

    def _phases(**kwargs):
        calls["phase_runner"] += 1
        return _fake_phase_runner(**kwargs)

    def _client(**kwargs):
        calls["client_factory"] += 1
        return _FakeClient(**kwargs)

    seen: dict = {}
    runtime = _obs_runtime(
        tmp_path, seen, policy=policy,
        rails_runner=_rails, phase_runner=_phases, client_factory=_client,
    )
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    receipt = runtime.run_phases()

    assert calls == {"rails_runner": 0, "phase_runner": 0, "client_factory": 0}
    assert receipt["policy"] == policy
    assert receipt["policy_kind"] == "obs-loop"
    assert receipt["contact_count"] == 6
    assert receipt["dispatch"]["dispatch"] == "obs-loop"
    assert receipt["dispatch"]["obs_prefetch_depth"] == 1
    assert receipt["obs_skipped_slice_count"] == 1


def test_the_obs_driver_receives_this_flights_own_objects(tmp_path):
    """ "Same harness for every arm" is a claim about identity, not about
    similarity: the driver must be handed the flight's OWN composed config,
    ExecutionPlan, gate, lock, data root, run dir and transport -- never a
    second copy resolved here."""

    seen: dict = {}
    runtime = _obs_runtime(tmp_path, seen)
    runtime.preflight()
    runtime.preprocess()
    serve_receipt = runtime.serve()
    runtime.run_phases()

    assert seen["composed"] is runtime._composed
    assert seen["plan"] is runtime.plan
    assert seen["gate"] is runtime._gate
    assert seen["lock"] is runtime._lock
    assert Path(seen["root"]) == runtime._data_root
    assert Path(seen["repo_root"]) == runtime._repo_root
    assert seen["transport"] is runtime._transport
    assert serve_receipt is not None


def test_the_sentinel_reaches_the_obs_driver_unresolved(tmp_path):
    """``_decoding_params`` collapses ``id_slot='per-sample'`` to slot 0
    because the phase harness dispatches one contact at a time. The obs
    executors resolve it themselves, per sample, from the run's dispatch
    pool -- so the composed value must reach the driver exactly as the
    fragment wrote it, and the receipt must say so rather than claim a
    resolution that did not happen."""

    seen: dict = {}
    runtime = _obs_runtime(
        tmp_path,
        seen,
        config_kwargs={
            "policy": "obs-agent-loop-ojw",
            "baseline_extra": dict(_OBS_BASELINE_EXTRA),
            "model_extra": {
                "model_lock_key": "fake-lock",
                "transport": "fake",
                "decoding_params": {"temperature": 0, "id_slot": "per-sample"},
            },
        },
    )
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    receipt = runtime.run_phases()

    composed_decoding = seen["composed"].values["decoding_params"]
    assert composed_decoding["id_slot"] == "per-sample"
    assert receipt["id_slot"] == "per-sample"
    assert "UNRESOLVED" in receipt["id_slot_resolution"]


def test_seal_writes_the_obs_drivers_own_rows_and_reads_its_run_result(tmp_path):
    """The obs driver is the authority for a stitched hypothesis' identity:
    its three hashes are STITCH descriptors over a sample's per-window
    requests and responses, and no client timing exists (or could) for a
    multi-window stitch. seal must pass them through and must not try to
    close a client the obs path never built."""

    seen: dict = {}
    runtime = _obs_runtime(tmp_path, seen)
    runtime.run_all()

    assert runtime.receipts.completed_stages() == (
        "preflight", "preprocess", "serve", "run_phases", "seal", "score",
    )
    seal = runtime.receipts.as_json()["stages"]["seal"]
    assert seal["outputs_row_count"] == 2
    assert seal["trace_manifest_hash"] == "9" * 64
    assert seal["cost"]["calls_used"] == 6
    sealed = [
        json.loads(line)
        for line in Path(seal["outputs_path"]).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert sealed == [dict(row) for row in _OBS_ROWS]


def test_an_obs_dispatch_refuses_without_a_transport(tmp_path):
    seen: dict = {}
    runtime = _obs_runtime(tmp_path, seen)
    runtime.preflight()
    runtime.preprocess()
    with pytest.raises(FlightStageOrderError):
        runtime.run_phases()


def test_the_prompt_budget_estimates_a_window_not_a_whole_call(tmp_path):
    """An Earnings call is 40-75 minutes and never reaches the core as one
    request. Estimating the whole call would refuse every legal Earnings
    flight on a ceiling no request of it approaches, so the speech term is
    the configured buffer plus its silence tail -- one window."""

    seen: dict = {}
    runtime = _obs_runtime(tmp_path, seen)
    receipt = runtime.preflight()
    (budget,) = receipt["prompt_budget"]
    assert budget["phase"] == "obs-window"
    # 90 s buffer + 2 s tail at the declared 14.4 tokens/s.
    runtime_two = _obs_runtime(
        tmp_path / "second",
        {},
        run_id="SAEA-TEST-RUN-002",
        config_kwargs={
            "policy": "obs-agent-loop-ojw",
            "baseline_extra": {
                **_OBS_BASELINE_EXTRA,
                "obs_slice_tail_silence_seconds": 2.0,
            },
        },
    )
    receipt_two = runtime_two.preflight()
    (budget_two,) = receipt_two["prompt_budget"]
    assert budget_two["breakdown"]["speech_feature_tokens"] > budget["breakdown"]["speech_feature_tokens"]
    assert budget_two["breakdown"]["speech_feature_tokens"] == round(92.0 * 14.4)


def test_wire_check_observer_receives_exact_boundary_after_abort(tmp_path):
    runtime = _wire_runtime(tmp_path)
    captured = []
    receipt = runtime.wire_check(seal_and_score=False,
                                 request_payload_observer=captured.append)
    assert receipt["schema"] == "saea-flight-wire-check-v1"
    assert len(captured) == receipt["contact_count"] == 2
    assert captured[0]["decoding_params"] == {"id_slot": 0}


def test_preparation_gate_uses_explicit_tokenizer_cap_and_exposure(tmp_path, monkeypatch):
    from unittest.mock import Mock
    runtime = _wire_runtime(tmp_path)
    runtime._gate_touch = Mock()
    runtime._require_exposure_row_unconsumed = Mock()
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.flight.runtime.require_clean_study_repo",
        lambda root: "a" * 40)
    plan = runtime.authorize_preparation_contacts(contact_cap=3001)
    assert plan.planned_model_calls == 3001
    assert runtime._gate_touch.call_args.args[1] == plan
    runtime._require_exposure_row_unconsumed.assert_called_once_with(plan.run_id)
    for cap in (0, -1, True):
        with pytest.raises(ValueError, match="cap"):
            runtime.authorize_preparation_contacts(contact_cap=cap)


@pytest.mark.parametrize("stage", ["preflight", "preparation"])
@pytest.mark.parametrize("evidence_supplement", [False, True])
def test_dataset_evidence_identity_reaches_both_shared_gates(
    tmp_path, stage, evidence_supplement,
):
    run_id = "SAEA-EVIDENCE-GATE-BINDING"
    repo = _make_repo(tmp_path, run_id)
    path = repo / "configs/dataset/d.json"
    dataset = json.loads(path.read_text())
    if evidence_supplement:
        dataset.update(
            d1_evidence_supplement="receipts/artifacts/evidence.json",
            d1_evidence_supplement_sha256="a" * 64,
        )
        path.write_text(json.dumps(dataset))
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "bind evidence identity")
    runtime = _make_runtime(tmp_path, run_id=run_id, repo_root=repo)
    observed = {}

    def gate_factory(*args, **kwargs):
        observed.update(kwargs)
        return _FakeGate()

    runtime._gate_factory = gate_factory
    if stage == "preflight":
        runtime.preflight()
    else:
        runtime.authorize_preparation_client(contact_cap=10)
    assert observed["d1_evidence_supplement_relpath"] == (
        "receipts/artifacts/evidence.json" if evidence_supplement else None
    )
    assert observed["d1_evidence_supplement_sha256"] == (
        "a" * 64 if evidence_supplement else None
    )
    assert observed["d1_media_supplement_relpath"] is None


def test_artifact_common_runtime_closes_with_worker_policy_and_zero_score_jobs(
    tmp_path,
):
    from speech_aware_evidence_acquisition.data.splits import (
        prefixed,
        split_identity_hash,
    )

    class QualityForbiddenAdapter(_FakeAdapter):
        def gold(self, sample):
            raise AssertionError("artifact runtime must not load task gold")

        def score_response(self, gold, response):
            raise AssertionError("artifact runtime must not score task answers")

        def extract_consumption(self, sample, supply, response):
            raise AssertionError("artifact runtime must not derive task consumption")

    identity = split_identity_hash(prefixed("fake-carrier", ("s1", "s2")))
    repo = _make_repo(
        tmp_path,
        "SAEA-TEST-ARTIFACT-001",
        arm="speech-feature-query",
        policy="phase-direct-only-v1",
        carrier_lock_key="fake-carrier",
        baseline_extra={
            "scorers": [],
            "result_kind": "artifact",
            "artifact_result": {
                "schema": "saea-artifact-result-binding-v1",
                "role": "training-feedback-proposal",
                "construction_roster": {
                    "repo_relpath": "docs/rosters/train.json",
                    "sha256": "0" * 64,
                },
            },
        },
    )
    promotion_receipt = _write_promotion_receipt(tmp_path)
    template_path = repo / "configs" / "probes" / "artifact_direct.txt"
    template_path.parent.mkdir(parents=True, exist_ok=True)
    template_path.write_text("Propose a training strategy.\n", encoding="utf-8")
    roster_path = repo / "docs" / "rosters" / "train.json"
    roster_path.parent.mkdir(parents=True)
    roster = {
        "schema": "saea-roster-receipt-v1",
        "roster_id": "SYNTHETIC-TRAIN-CONSTRUCTION",
        "carrier_lock_key": "fake-carrier",
        "split_role": "discovery",
        "roster_role": "construction",
        "seed": 1,
        "per_stratum": {"all": 2},
        "strata_counts": {"all": 2},
        "items": [
            {"sample_id": "s1", "stratum": "all"},
            {"sample_id": "s2", "stratum": "all"},
        ],
        "excluded_count": 0,
        "split_identity_hash": identity,
    }
    roster_path.write_text(json.dumps(roster))
    baseline_path = repo / "configs" / "baseline" / "b.json"
    baseline = json.loads(baseline_path.read_text())
    baseline["speech_packet_promotion_receipt"] = str(promotion_receipt)
    baseline["speech_feature_key_representation_id"] = "key-rep-v1"
    baseline["speech_feature_matcher_policy_id"] = "matcher-v1"
    model_path = repo / "configs" / "model" / "m.json"
    model = json.loads(model_path.read_text())
    model["speech_feature_root"] = str(tmp_path / _PROMOTION_DIR)
    model_path.write_text(json.dumps(model))
    baseline["phase_material"] = {
        "direct": {
            "instruction_template": "probes/artifact_direct.txt",
            "predecessor_binding": "none",
        }
    }
    baseline["artifact_result"]["construction_roster"]["sha256"] = hashlib.sha256(
        roster_path.read_bytes()
    ).hexdigest()
    baseline_path.write_text(json.dumps(baseline))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "artifact fixture")

    class ArtifactFinalize:
        scores_path = None
        ledger_markdown_path = Path("artifact-ledger.md")
        ledger_json_path = Path("artifact-ledger.json")
        attempt_state = "FINALIZED"

    class ArtifactVerified:
        def __init__(self, state):
            self.attempt_state = state
            self.manifest = {"scores": None, "scorers": []}

    verification_states = iter(("OPENED", "FINALIZED"))
    runtime = _make_runtime(
        tmp_path,
        run_id="SAEA-TEST-ARTIFACT-001",
        repo_root=repo,
        adapter_cls=QualityForbiddenAdapter,
        happy_path=True,
        bundle_verifier=lambda _path: ArtifactVerified(next(verification_states)),
        bundle_finalizer=lambda *_args, **_kwargs: ArtifactFinalize(),
        score_batch=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("artifact score stage must schedule zero score jobs")
        ),
    )
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    runtime.bind_phase_program_material(
        knowledge_snapshot="fake-snapshot",
        speech_packet_bindings={},
        material_for_phase=lambda *args, **kwargs: None,
    )
    run = runtime.run_phases()
    # A campaign worker binds this before seal; its presence must not force
    # proposal artifacts into the deferred task-scoring path.
    runtime._execution_policy = object()
    sealed = runtime.seal()
    scored = runtime.score()

    assert run["result_kind"] == "artifact"
    assert sealed["finalize"] == {
        "scores_path": None,
        "ledger_markdown_path": "artifact-ledger.md",
        "attempt_state": "FINALIZED",
        "status": "not-applicable",
        "result_kind": "artifact",
    }
    assert scored["status"] == "not-applicable"
    assert scored["job_count"] == 0
    rows = [
        json.loads(line)
        for line in Path(sealed["outputs_path"]).read_text().splitlines()
    ]
    assert all(
        row["result_kind"] == "artifact"
        and row["artifact_role"] == "training-feedback-proposal"
        for row in rows
    )


class _ConfiguredWideBudgetFakeAdapter(_FakeAdapter):
    SERVING_SLOTS = 2
    SERVING_SLOT_TOKENS = 49_152
    SERVING_MAX_TOKENS = 2_048


def test_preflight_uses_explicit_geometry_bound_context_budget_and_keeps_fit_check(
    tmp_path, monkeypatch
):
    runtime = _make_runtime(
        tmp_path,
        adapter_cls=_ConfiguredWideBudgetFakeAdapter,
        token_counter=lambda _payload: 32_789,
        config_kwargs={
            "baseline_extra": {
                "context_budget_limits": {
                    "slot_limit_tokens": 49_152,
                    "operational_reserve_tokens": 8_192,
                }
            }
        },
    )
    fit_receipt = {"actual_request_fit": "still-required"}
    monkeypatch.setattr(runtime, "_verify_phase_prompt_fit", lambda: fit_receipt)

    receipt = runtime.preflight()

    assert receipt["phase_prompt_fit"] == fit_receipt
    assert receipt["prompt_budget"][0]["decision"] == "ALLOW"
    assert receipt["prompt_budget"][0]["slot_limit_tokens"] == 49_152


def test_preflight_refuses_context_budget_limit_that_differs_from_geometry(tmp_path):
    runtime = _make_runtime(
        tmp_path,
        adapter_cls=_ConfiguredWideBudgetFakeAdapter,
        config_kwargs={
            "baseline_extra": {
                "context_budget_limits": {
                    "slot_limit_tokens": 32_768,
                    "operational_reserve_tokens": 8_192,
                }
            }
        },
    )

    with pytest.raises(ContextBudgetRefusal, match="serving geometry"):
        runtime.preflight()
