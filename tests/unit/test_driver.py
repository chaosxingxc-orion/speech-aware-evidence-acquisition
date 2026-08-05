"""End-to-end wiring on the synthetic world with a fake transport."""

import json

import pytest

import speech_aware_evidence_acquisition.core  # noqa: F401 (populate registries)
from speech_aware_evidence_acquisition.contracts import ExecutionPlan
from speech_aware_evidence_acquisition.core.attempts import AttemptStore
from speech_aware_evidence_acquisition.core.base import CoreError, RunResult
from speech_aware_evidence_acquisition.core.config import ComposedConfig, protocol_hash
from speech_aware_evidence_acquisition.core.driver import load_split, run_experiment
from speech_aware_evidence_acquisition.core.resources import NOT_AVAILABLE
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.data.splits import discovery_split, freeze_splits
from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT


class _OpenGate:
    def assert_model_touch_allowed(self, plan):
        pass


def _composed(**overrides):
    values = {
        "carrier_lock_key": "earnings21-original",
        "split_name": "discovery",
        "arm": "bare-core",
        "policy": "fixed",
        "evidence_source": "none",
        "evidence_mismatch": False,
        "scorers": ["asr-wer"],
        "task_instruction": "Transcribe.",
        "decoding_params": {"temperature": 0, "seed": 20260803},
        "experiment_id": "SAEA-E-000",
    }
    values.update(overrides)
    return ComposedConfig(
        values=values, config_hash="d" * 64,
        fragments={"model": "m", "dataset": "d", "baseline": "b", "experiment": "e"},
    )


def _plan(split_hash, **overrides):
    base = dict(
        run_id="SAEA-E-000-driver",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="earnings21-original",
        split_role="discovery",
        split_identity_hash=split_hash,
        planned_model_calls=10,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=1000,
        protocol_hash="b" * 64,
        attempt_id="attempt-0001",
    )
    base.update(overrides)
    return ExecutionPlan(**base)


def _transport(request_bytes):
    return json.dumps({"text": "token tags", "usage": {"prompt_tokens": 3}}).encode()


def _frozen_world(synthetic_world, tmp_path):
    lock = load_lock(synthetic_world.lock_path)
    receipts = tmp_path / "repo" / "docs" / "receipts"
    freeze_splits(lock, synthetic_world.data_root, receipts)
    return lock, tmp_path / "repo"


def test_run_experiment_end_to_end(synthetic_world, tmp_path):
    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    ids, split_hash, split_role = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    assert len(ids) == 3
    assert split_role == "discovery"
    composed = _composed()
    plan = _plan(
        split_hash,
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    result = run_experiment(
        composed=composed,
        plan=plan,
        gate=_OpenGate(),
        lock=lock,
        root=synthetic_world.data_root,
        run_dir=tmp_path / "run",
        transport=_transport,
        repo_root=repo_root,
    )
    assert isinstance(result, RunResult)
    lines = result.outputs_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    assert result.cost["calls_used"] == 3
    manifest = json.loads(
        (tmp_path / "run" / "SAEA-E-000-driver.trace-manifest.json").read_text("utf-8")
    )["records"]
    assert any(record_id.endswith("/obs") for record_id in manifest)
    assert any(record_id.endswith("/use") for record_id in manifest)


def test_run_experiment_persists_attempt_usage_matching_the_run_cost(synthetic_world, tmp_path):
    """R0 repair T4, probe 6: a legitimate first attempt end to end through
    run_experiment still works, AND its durable attempt file (not just the
    in-process RunResult.cost) carries exactly what was spent."""

    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    ids, split_hash, split_role = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed()
    plan = _plan(
        split_hash,
        attempt_id="attempt-e2e",
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    result = run_experiment(
        composed=composed,
        plan=plan,
        gate=_OpenGate(),
        lock=lock,
        root=synthetic_world.data_root,
        run_dir=tmp_path / "run",
        transport=_transport,
        repo_root=repo_root,
    )
    store = AttemptStore(synthetic_world.data_root / "attempts")
    calls, audio = store.prior_actual_usage(plan.run_id)
    assert calls == result.cost["calls_used"] == len(ids)
    assert audio == result.cost["audio_seconds_used"]
    attempt_path = synthetic_world.data_root / "attempts" / plan.run_id / "attempt-e2e.json"
    assert attempt_path.is_file()
    import json as _json

    document = _json.loads(attempt_path.read_text(encoding="utf-8"))
    # Finalization (RESERVED/OPENED -> FINALIZED/ABORTED) is T6, out of scope
    # here: a successful run leaves the attempt OPENED, not silently dropped.
    assert document["state"] == "OPENED"


def test_run_experiment_refuses_wrong_split_hash(synthetic_world, tmp_path):
    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    with pytest.raises(CoreError, match="split"):
        run_experiment(
            composed=_composed(),
            plan=_plan("f" * 64),
            gate=_OpenGate(),
            lock=lock,
            root=synthetic_world.data_root,
            run_dir=tmp_path / "run",
            transport=_transport,
            repo_root=repo_root,
        )


def test_run_experiment_refuses_receipt_dev_role_mismatch(synthetic_world, tmp_path):
    """A plan labeled 'discovery' must not be able to run against the dev split."""

    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, dev_hash, dev_role = load_split(repo_root, "dev", lock, synthetic_world.data_root)
    assert dev_role == "dev"
    with pytest.raises(CoreError, match="split role"):
        run_experiment(
            composed=_composed(
                carrier_lock_key="earnings22-original",
                split_name="dev",
            ),
            plan=_plan(dev_hash, split_role="discovery"),
            gate=_OpenGate(),
            lock=lock,
            root=synthetic_world.data_root,
            run_dir=tmp_path / "run",
            transport=_transport,
            repo_root=repo_root,
        )


def test_run_experiment_refuses_confirmatory_split_under_a_dev_labeled_plan(
    synthetic_world, tmp_path
):
    """A confirmatory split can never run, even mislabeled as a 'dev' plan."""

    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, confirmatory_hash, confirmatory_role = load_split(repo_root, "confirmatory", lock, synthetic_world.data_root)
    assert confirmatory_role == "confirmatory"
    with pytest.raises(CoreError, match="split role"):
        run_experiment(
            composed=_composed(
                carrier_lock_key="earnings22-original",
                split_name="confirmatory",
            ),
            plan=_plan(confirmatory_hash, split_role="dev"),
            gate=_OpenGate(),
            lock=lock,
            root=synthetic_world.data_root,
            run_dir=tmp_path / "run",
            transport=_transport,
            repo_root=repo_root,
        )


def test_run_experiment_supplies_evidence_with_org_and_supply_traces(
    synthetic_world, tmp_path
):
    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, split_hash, _ = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed(arm="fixed-legal-context", evidence_source="conec-contexts")
    plan = _plan(
        split_hash,
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    result = run_experiment(
        composed=composed,
        plan=plan,
        gate=_OpenGate(),
        lock=lock,
        root=synthetic_world.data_root,
        run_dir=tmp_path / "run2",
        transport=_transport,
        repo_root=repo_root,
    )
    manifest = json.loads(
        (tmp_path / "run2" / "SAEA-E-000-driver.trace-manifest.json").read_text("utf-8")
    )["records"]
    assert any(record_id.endswith("/org") for record_id in manifest)
    assert any(record_id.endswith("/supply") for record_id in manifest)
    assert result.arm == "fixed-legal-context"


def test_run_experiment_refuses_wrong_protocol_hash(synthetic_world, tmp_path):
    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, split_hash, _ = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    with pytest.raises(CoreError, match="protocol hash"):
        run_experiment(
            composed=_composed(),
            plan=_plan(split_hash, protocol_hash="c" * 64),
            gate=_OpenGate(),
            lock=lock,
            root=synthetic_world.data_root,
            run_dir=tmp_path / "run",
            transport=_transport,
            repo_root=repo_root,
        )


def test_run_experiment_refuses_preexisting_outputs_file(synthetic_world, tmp_path):
    """A fresh sink dir (no trace files) but a manually pre-existing outputs
    file must still fail closed — the driver's own "x"-mode open, not just
    the sink's pre-existence check, is the belt-and-suspenders guard."""

    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, split_hash, _ = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed()
    plan = _plan(
        split_hash,
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    run_dir = tmp_path / "run3"
    run_dir.mkdir(parents=True)
    (run_dir / f"{plan.run_id}.outputs.jsonl").write_text("stale\n", encoding="utf-8")
    with pytest.raises(CoreError, match="exists"):
        run_experiment(
            composed=composed,
            plan=plan,
            gate=_OpenGate(),
            lock=lock,
            root=synthetic_world.data_root,
            run_dir=run_dir,
            transport=_transport,
            repo_root=repo_root,
        )


def test_run_experiment_refuses_wrong_carrier_lock_key(synthetic_world, tmp_path):
    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, split_hash, _ = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed()
    plan = _plan(
        split_hash,
        carrier_lock_key="earnings22-original",
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    with pytest.raises(CoreError, match="carrier"):
        run_experiment(
            composed=composed,
            plan=plan,
            gate=_OpenGate(),
            lock=lock,
            root=synthetic_world.data_root,
            run_dir=tmp_path / "run",
            transport=_transport,
            repo_root=repo_root,
        )


# ---------------------------------------------------------------------------
# R0 repair T8: the formal `configs/baseline/*.json` engineering-control
# fragments -- loaded from the ACTUAL committed files, not retyped by hand --
# each drive a real synthetic end-to-end run through run_experiment. This is
# the P1-3 gap: previously only bare-core.json was a runnable named config,
# and fixed-legal-context/fixed-retrieval/mismatched-evidence were only
# exercised by ad-hoc inline dicts or unit-level payload-builder tests.
# ---------------------------------------------------------------------------


def _baseline_fragment(name):
    path = REPO_ROOT / "configs" / "baseline" / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _raw_trace_records(run_dir, run_id):
    path = run_dir / f"{run_id}.trace.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _sample_id_by_request_id(outputs_path):
    rows = [
        json.loads(line)
        for line in outputs_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    return {row["request_id"]: row["sample_id"] for row in rows}


def _supply_evidence_ids_by_sample(run_dir, run_id, outputs_path):
    sample_id_by_request = _sample_id_by_request_id(outputs_path)
    by_sample: dict[str, list[str]] = {}
    for record in _raw_trace_records(run_dir, run_id):
        if record["channel"] != "SUPPLY":
            continue
        request_id = record["record_id"].removesuffix("/supply")
        sample_id = sample_id_by_request[request_id]
        by_sample[sample_id] = record["payload"]["supply_evidence_ids"]
    return by_sample


def test_run_experiment_bare_core_config_has_no_org_or_supply_records(synthetic_world, tmp_path):
    """Contrast case (brief requirement): the same real config file mechanism
    used for the three evidence-bearing controls below, but for bare-core --
    proving ORG/SUPPLY are genuinely ABSENT, not merely unchecked."""

    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, split_hash, _ = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed(**_baseline_fragment("bare-core"))
    plan = _plan(
        split_hash,
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    run_dir = tmp_path / "run-bare-core"
    result = run_experiment(
        composed=composed,
        plan=plan,
        gate=_OpenGate(),
        lock=lock,
        root=synthetic_world.data_root,
        run_dir=run_dir,
        transport=_transport,
        repo_root=repo_root,
    )
    assert result.arm == "bare-core"
    lines = result.outputs_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    manifest = json.loads(
        (run_dir / f"{plan.run_id}.trace-manifest.json").read_text("utf-8")
    )["records"]
    assert any(record_id.endswith("/obs") for record_id in manifest)
    assert any(record_id.endswith("/use") for record_id in manifest)
    assert not any(record_id.endswith("/org") for record_id in manifest)
    assert not any(record_id.endswith("/supply") for record_id in manifest)


def test_run_experiment_fixed_legal_context_config_end_to_end(synthetic_world, tmp_path):
    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, split_hash, _ = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed(**_baseline_fragment("fixed-legal-context"))
    plan = _plan(
        split_hash,
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    run_dir = tmp_path / "run-fixed-legal-context"
    result = run_experiment(
        composed=composed,
        plan=plan,
        gate=_OpenGate(),
        lock=lock,
        root=synthetic_world.data_root,
        run_dir=run_dir,
        transport=_transport,
        repo_root=repo_root,
    )
    assert result.arm == "fixed-legal-context"
    lines = result.outputs_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    manifest = json.loads(
        (run_dir / f"{plan.run_id}.trace-manifest.json").read_text("utf-8")
    )["records"]
    assert any(record_id.endswith("/obs") for record_id in manifest)
    assert any(record_id.endswith("/org") for record_id in manifest)
    assert any(record_id.endswith("/supply") for record_id in manifest)
    assert any(record_id.endswith("/use") for record_id in manifest)
    # Not a mismatch config: every sample's own evidence is supplied.
    supply_by_sample = _supply_evidence_ids_by_sample(run_dir, plan.run_id, result.outputs_path)
    assert supply_by_sample
    for sample_id, evidence_ids in supply_by_sample.items():
        assert evidence_ids == [f"conec/{sample_id}"]


def test_run_experiment_fixed_retrieval_config_end_to_end(synthetic_world, tmp_path):
    """The fixed-retrieval arm needs a retrieval_query: the config supplies
    one as a top-level composed value (``values.get("retrieval_query")`` in
    core.driver.run_experiment), which flows into SampleContext.retrieval_query
    and then into core.policies.build_arm_payload's ``retrieval_query``
    argument -- the same field the D2 freeze names for this arm."""

    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, split_hash, _ = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    fragment = _baseline_fragment("fixed-retrieval")
    assert fragment["retrieval_query"].strip()
    composed = _composed(**fragment)
    plan = _plan(
        split_hash,
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    run_dir = tmp_path / "run-fixed-retrieval"
    result = run_experiment(
        composed=composed,
        plan=plan,
        gate=_OpenGate(),
        lock=lock,
        root=synthetic_world.data_root,
        run_dir=run_dir,
        transport=_transport,
        repo_root=repo_root,
    )
    assert result.arm == "fixed-retrieval"
    lines = result.outputs_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    manifest = json.loads(
        (run_dir / f"{plan.run_id}.trace-manifest.json").read_text("utf-8")
    )["records"]
    assert any(record_id.endswith("/org") for record_id in manifest)
    assert any(record_id.endswith("/supply") for record_id in manifest)


def test_run_experiment_mismatched_evidence_config_rotates_supply(synthetic_world, tmp_path):
    """The mismatched-evidence config sets evidence_mismatch: true; the SUPPLY
    channel must carry another sample's evidence, never the sample's own."""

    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, split_hash, _ = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    fragment = _baseline_fragment("mismatched-evidence")
    assert fragment["evidence_mismatch"] is True
    composed = _composed(**fragment)
    plan = _plan(
        split_hash,
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    run_dir = tmp_path / "run-mismatched-evidence"
    result = run_experiment(
        composed=composed,
        plan=plan,
        gate=_OpenGate(),
        lock=lock,
        root=synthetic_world.data_root,
        run_dir=run_dir,
        transport=_transport,
        repo_root=repo_root,
    )
    assert result.arm == "fixed-legal-context"
    manifest = json.loads(
        (run_dir / f"{plan.run_id}.trace-manifest.json").read_text("utf-8")
    )["records"]
    assert any(record_id.endswith("/org") for record_id in manifest)
    assert any(record_id.endswith("/supply") for record_id in manifest)
    # rotated_mismatch is a full derangement (each sample gets the NEXT sorted
    # sample's evidence): with 3 discovery samples, every single one must
    # receive evidence that is NOT its own -- never merely "some of them".
    supply_by_sample = _supply_evidence_ids_by_sample(run_dir, plan.run_id, result.outputs_path)
    assert len(supply_by_sample) == 3
    ordered = sorted(supply_by_sample)
    for index, sample_id in enumerate(ordered):
        expected_donor = ordered[(index + 1) % len(ordered)]
        assert supply_by_sample[sample_id] == [f"conec/{expected_donor}"]


# ---------------------------------------------------------------------------
# R0 repair T7, invariant I8: cost accounting completion. The run aggregate
# (``RunResult.cost``) must add GPU/VRAM (via an injectable sampler,
# NOT_AVAILABLE + reason when no sampler is supplied), CPU seconds, gate/setup
# latency, supplied/admitted evidence bytes and failed-attempt cost -- on top
# of the pre-existing calls/audio/latency/tokens fields.
# ---------------------------------------------------------------------------


class _FakeSampler:
    """A model-free, thread-free test double for
    ``speech_aware_evidence_acquisition.core.resources.ResourceSampler`` --
    never shells out to a real ``nvidia-smi``."""

    def __init__(self, gpu_seconds=12.5, peak_vram_mib=4096.0):
        self.start_calls = 0
        self.stop_calls = 0
        self._gpu_seconds = gpu_seconds
        self._peak_vram_mib = peak_vram_mib

    def start(self):
        self.start_calls += 1

    def stop(self):
        self.stop_calls += 1

    def summary(self):
        return {
            "gpu_seconds": self._gpu_seconds,
            "peak_vram_mib": self._peak_vram_mib,
            "gpu_sampling_reason": None,
        }


def test_run_experiment_cost_includes_injected_sampler_readings(synthetic_world, tmp_path):
    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, split_hash, _ = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed()
    plan = _plan(
        split_hash,
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    sampler = _FakeSampler(gpu_seconds=7.25, peak_vram_mib=8192.0)
    result = run_experiment(
        composed=composed,
        plan=plan,
        gate=_OpenGate(),
        lock=lock,
        root=synthetic_world.data_root,
        run_dir=tmp_path / "run-cost-sampler",
        transport=_transport,
        repo_root=repo_root,
        resource_sampler=sampler,
    )
    assert sampler.start_calls == 1
    assert sampler.stop_calls == 1
    cost = result.cost
    assert cost["gpu_seconds"] == 7.25
    assert cost["peak_vram_mib"] == 8192.0
    assert cost["gpu_sampling_reason"] is None
    assert cost["cost_unavailable_reason"] is None
    assert isinstance(cost["cpu_seconds"], float) and cost["cpu_seconds"] >= 0.0
    assert isinstance(cost["gate_setup_seconds"], float) and cost["gate_setup_seconds"] >= 0.0
    assert cost["tool_calls"] == 0
    # bare-core arm: no evidence at all.
    assert cost["supplied_evidence_bytes"] == 0
    assert cost["admitted_evidence_bytes"] == 0
    assert cost["failed_attempt_calls"] == 0
    assert cost["failed_attempt_audio_seconds"] == 0.0


def test_run_experiment_without_a_resource_sampler_reports_gpu_not_available(
    synthetic_world, tmp_path
):
    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, split_hash, _ = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed()
    plan = _plan(
        split_hash,
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    result = run_experiment(
        composed=composed,
        plan=plan,
        gate=_OpenGate(),
        lock=lock,
        root=synthetic_world.data_root,
        run_dir=tmp_path / "run-cost-no-sampler",
        transport=_transport,
        repo_root=repo_root,
        # resource_sampler omitted entirely -- must never shell out to a real
        # nvidia-smi; must instead be an explicit, reasoned NOT_AVAILABLE.
    )
    cost = result.cost
    assert cost["gpu_seconds"] == NOT_AVAILABLE
    assert cost["peak_vram_mib"] == NOT_AVAILABLE
    assert isinstance(cost["gpu_sampling_reason"], str) and cost["gpu_sampling_reason"].strip()
    # Every OTHER T7 field is still genuinely measured -- the sampler gap
    # never degrades the fields that do not depend on it.
    assert cost["cost_unavailable_reason"] is None
    assert isinstance(cost["cpu_seconds"], float)
    assert isinstance(cost["gate_setup_seconds"], float)


def test_run_experiment_aggregates_supplied_and_admitted_evidence_bytes(synthetic_world, tmp_path):
    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, split_hash, _ = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed(**_baseline_fragment("fixed-legal-context"))
    plan = _plan(
        split_hash,
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    run_dir = tmp_path / "run-cost-evidence"
    result = run_experiment(
        composed=composed,
        plan=plan,
        gate=_OpenGate(),
        lock=lock,
        root=synthetic_world.data_root,
        run_dir=run_dir,
        transport=_transport,
        repo_root=repo_root,
    )
    supply_by_sample = _supply_evidence_ids_by_sample(run_dir, plan.run_id, result.outputs_path)
    assert supply_by_sample  # every discovery sample carries its own conec context
    expected_bytes = 3 * len(supply_by_sample)  # each synthetic context is the 3-byte string "ctx"
    assert result.cost["supplied_evidence_bytes"] == expected_bytes
    # FixedPolicy always admits (R0's only registered policy) -- supplied and
    # admitted coincide today; the two fields exist as SEPARATE counters for
    # a future rejecting policy (e.g. X3), not merged into one.
    assert result.cost["admitted_evidence_bytes"] == expected_bytes


def test_run_experiment_reports_failed_attempt_cost_from_a_prior_aborted_sibling(
    synthetic_world, tmp_path
):
    """A prior attempt on the SAME run_id crashed (state stuck ABORTED) after
    spending real calls/audio; a fresh, successful attempt's own cost block
    must surface that wasted spend under failed_attempt_calls/
    failed_attempt_audio_seconds -- never silently drop it, and never fold it
    into this attempt's OWN calls_used/audio_seconds_used."""

    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    ids, split_hash, _ = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed()
    run_id = "SAEA-E-000-failedcost"

    store = AttemptStore(synthetic_world.data_root / "attempts")
    prior_handle = store.open_attempt(
        run_id, "attempt-prior",
        carrier_lock_key="earnings21-original", reserved_calls=5, reserved_audio_seconds=500.0,
    )
    prior_handle.record_usage(calls=2, audio_seconds=50.0)
    prior_handle.mark_aborted("simulated crash before this test's fresh attempt")

    plan = _plan(
        split_hash, run_id=run_id, attempt_id="attempt-fresh",
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    result = run_experiment(
        composed=composed,
        plan=plan,
        gate=_OpenGate(),
        lock=lock,
        root=synthetic_world.data_root,
        run_dir=tmp_path / "run-failed-cost",
        transport=_transport,
        repo_root=repo_root,
    )
    assert result.cost["failed_attempt_calls"] == 2
    assert result.cost["failed_attempt_audio_seconds"] == 50.0
    # This attempt's own spend is reported separately, un-mixed with the
    # sibling's failed spend.
    assert result.cost["calls_used"] == len(ids)
    calls, audio = store.prior_actual_usage(run_id, exclude_attempt_id="attempt-prior")
    assert calls == result.cost["calls_used"]
    assert audio == result.cost["audio_seconds_used"]
