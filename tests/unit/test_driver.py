"""End-to-end wiring on the synthetic world with a fake transport."""

import hashlib
import json

import pytest

import subprocess

import speech_aware_evidence_acquisition.core  # noqa: F401 (populate registries)
from speech_aware_evidence_acquisition.contracts import ExecutionPlan
from speech_aware_evidence_acquisition.core.attempts import AttemptStore
from speech_aware_evidence_acquisition.core.base import CoreError, EvidenceError, RunResult
from speech_aware_evidence_acquisition.core.bundle import verify_bundle
from speech_aware_evidence_acquisition.core.config import ComposedConfig, compose, protocol_hash
from speech_aware_evidence_acquisition.core.driver import (
    load_split,
    run_experiment,
    run_experiment_bundled,
)
from speech_aware_evidence_acquisition.core.resources import NOT_AVAILABLE
from speech_aware_evidence_acquisition.core.scorers import score_bundle
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


# ---------------------------------------------------------------------------
# IMPORTANT 1 (external-threat-model review round 4): run_experiment builds
# the D1 evidence-identity rail's facts (core.evidence.evidence_file_relpath)
# for exactly the discovery samples the evidence source actually supplied
# evidence for, and threads them into the binding context a gate that
# implements verify_evidence_identity can then check at adapter construction.
# ---------------------------------------------------------------------------


class _EvidenceCheckingGate:
    def __init__(self):
        self.checked = []
        self.content_checked = []

    def assert_model_touch_allowed(self, plan):
        return None

    def verify_evidence_identity(self, carrier_lock_key, evidence_facts):
        self.checked.append((carrier_lock_key, dict(evidence_facts)))

    def verify_evidence_content_identity(self, carrier_lock_key, evidence_contents, evidence_relpaths):
        self.content_checked.append(
            (carrier_lock_key, dict(evidence_contents), dict(evidence_relpaths))
        )


def test_run_experiment_wires_evidence_relpaths_into_the_evidence_identity_gate(
    synthetic_world, tmp_path
):
    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, split_hash, _ = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed(arm="fixed-legal-context", evidence_source="conec-contexts")
    plan = _plan(
        split_hash,
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    gate = _EvidenceCheckingGate()
    run_experiment(
        composed=composed,
        plan=plan,
        gate=gate,
        lock=lock,
        root=synthetic_world.data_root,
        run_dir=tmp_path / "run-evidence-identity",
        transport=_transport,
        repo_root=repo_root,
    )
    assert len(gate.checked) == 1
    carrier_lock_key, evidence_facts = gate.checked[0]
    assert carrier_lock_key == "earnings21-original"
    assert evidence_facts == {
        "4000001": "datasets/conec/earnings21/contexts/4000001.txt",
        "4000002": "datasets/conec/earnings21/contexts/4000002.txt",
        "4000003": "datasets/conec/earnings21/contexts/4000003.txt",
    }
    # IMPROVEMENT (fifth external-threat-model review): the same run also
    # wires the ALREADY-READ evidence content (never a second file read) into
    # the content-identity rail, keyed identically.
    assert len(gate.content_checked) == 1
    content_carrier_lock_key, evidence_contents, content_evidence_relpaths = gate.content_checked[0]
    assert content_carrier_lock_key == "earnings21-original"
    assert evidence_contents == {
        "4000001": b"ctx",
        "4000002": b"ctx",
        "4000003": b"ctx",
    }
    # conec-names follow-up (2026-08-13): the content-identity rail now gets
    # the SAME relpaths the file rail got, threaded from the SAME binding, so
    # it can route each sample's content against its own D1 layer.
    assert content_evidence_relpaths == evidence_facts


def test_run_experiment_skips_the_evidence_identity_gate_when_evidence_source_is_none(
    synthetic_world, tmp_path
):
    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, split_hash, _ = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed()  # evidence_source: "none" (default)
    plan = _plan(
        split_hash,
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    gate = _EvidenceCheckingGate()
    run_experiment(
        composed=composed,
        plan=plan,
        gate=gate,
        lock=lock,
        root=synthetic_world.data_root,
        run_dir=tmp_path / "run-evidence-identity-none",
        transport=_transport,
        repo_root=repo_root,
    )
    assert gate.checked == []
    assert gate.content_checked == []


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


def test_run_experiment_refuses_split_receipt_carrier_mismatched_with_plan(synthetic_world, tmp_path):
    """M-2 (external-threat-model review): the split RECEIPT's own
    carrier_lock_key must agree with the plan's, independent of the config's.

    Both the config's and the plan's carrier_lock_key are set to
    "earnings21-original" here (so the OLDER `values["carrier_lock_key"] !=
    plan.carrier_lock_key` check would pass) -- only the split RECEIPT loaded
    for "dev" (whose own carrier is "earnings22-original") disagrees. Without
    the M-2 check this is masked today only because earnings21-original's and
    earnings22-original's sample ids never overlap, so the loader's filtered
    sample set would end up empty and get caught later by a differently
    worded, indirect check ("split ids missing from the carrier's loaded
    samples") -- an accident of today's two carriers, not a guarantee."""

    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, dev_hash, dev_role = load_split(repo_root, "dev", lock, synthetic_world.data_root)
    assert dev_role == "dev"
    composed = _composed(carrier_lock_key="earnings21-original", split_name="dev")
    plan = _plan(
        dev_hash,
        carrier_lock_key="earnings21-original",
        split_role="dev",
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], dev_hash),
    )
    with pytest.raises(CoreError, match="frozen splits receipt carrier_lock_key"):
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
# R0 repair T8 fix round (review IMPORTANT 1): compose() alone proves only
# "disjoint keys", never "this pairing can actually complete a run" --
# evidence_source: "conec-contexts" only has data for earnings21-original
# samples, but the only PRE-EXISTING dataset fragment was
# earnings22-dev-subset10 (carrier earnings22-original), so a real run over
# the real 4-fragment composition of an evidence-bearing baseline used to
# raise EvidenceError for essentially every sample -- masked because
# test_run_experiment_*_config_end_to_end above go through _composed(), whose
# defaults hardcode carrier earnings21-original regardless of what any
# baseline fragment says. These tests instead call core.config.compose()
# directly against the REAL committed fragments -- model, the NEW
# configs/dataset/earnings21-discovery.json (carrier_lock_key
# earnings21-original, split_name discovery -- the frozen splits receipt
# names exactly that pairing), the baseline under test, and r0-smoke -- with
# no _composed() defaults and no hardcoded overrides, then drive the result
# through run_experiment with the fake transport. Chosen fix: a new dataset
# fragment, not a carrier-aware evidence_source (the alternative the review
# offered) -- core.driver.run_experiment's evidence-source call site
# (`source(lock, root, s.sample_id)`) does not pass a carrier through, and
# core/driver.py is owned by another agent this session; adding a dataset
# fragment needed no change to any file outside this task's own scope.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "baseline_name, expected_arm",
    [
        ("fixed-legal-context", "fixed-legal-context"),
        ("fixed-retrieval", "fixed-retrieval"),
        ("mismatched-evidence", "fixed-legal-context"),
    ],
)
def test_run_experiment_real_four_fragment_composition_for_evidence_bearing_baselines(
    synthetic_world, tmp_path, baseline_name, expected_arm
):
    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, split_hash, _ = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = compose(
        REPO_ROOT, "qwen3-omni-llamacpp", "earnings21-discovery", baseline_name, "r0-smoke"
    )
    assert composed.values["carrier_lock_key"] == "earnings21-original"
    assert composed.values["split_name"] == "discovery"
    plan = _plan(
        split_hash,
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    run_dir = tmp_path / f"run-real-{baseline_name}"
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
    assert result.arm == expected_arm
    lines = result.outputs_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    manifest = json.loads(
        (run_dir / f"{plan.run_id}.trace-manifest.json").read_text("utf-8")
    )["records"]
    assert any(record_id.endswith("/org") for record_id in manifest)
    assert any(record_id.endswith("/supply") for record_id in manifest)


# ---------------------------------------------------------------------------
# R0 repair T8 fix round (review IMPORTANT 2): no config fragment anywhere
# set "scorers", so core.bundle.build_manifest baked composed.values.get(
# "scorers", []) -> [] into every real manifest, and core.scorers.score_bundle
# then refused every real run with "no configured scorers to run" -- asr-wer
# and cost were unreachable outside tests whose _composed() helper hardcoded
# scorers by hand. bare-core.json/fixed-legal-context.json/fixed-retrieval.
# json/mismatched-evidence.json now all set "scorers": ["asr-wer", "cost"];
# this test proves a REAL composed config's manifest carries that non-empty
# list AND that score_bundle genuinely runs both scorers end to end.
# ---------------------------------------------------------------------------


def _git(repo_root, *args):
    subprocess.run(["git", *args], cwd=repo_root, check=True, capture_output=True, text=True)


def _git_init_commit(repo_root):
    _git(repo_root, "init", "-q")
    _git(repo_root, "config", "user.email", "test@example.com")
    _git(repo_root, "config", "user.name", "Test")
    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-q", "-m", "test snapshot")


def test_real_composed_config_manifest_scorers_are_reachable_end_to_end(synthetic_world, tmp_path):
    sample_ids = ("4000001", "4000002", "4000003")
    for sample_id in sample_ids:
        nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / f"{sample_id}.nlp"
        nlp.write_text(f"token|tags\nhello-{sample_id}|\nworld|\n", encoding="utf-8")
    lock = load_lock(synthetic_world.lock_path)
    repo_root = tmp_path / "repo"
    receipts = repo_root / "docs" / "receipts"
    freeze_splits(lock, synthetic_world.data_root, receipts)
    # IMPORTANT 2 (fix-wave3, external-threat-model review round 3):
    # core.scorers._assert_scoring_entry_gate now re-verifies the reference
    # (.nlp) bytes score_asr_outputs is about to read, bound to THIS test's
    # own synthetic repo_root (the SAME test-overridable parameter
    # require_clean_study_repo already uses) -- write a minimal, genuinely
    # matching D1 identity artifact, committed alongside the frozen splits
    # receipt below, so it is never out of sync with the bytes just written.
    manifest_entries = []
    for sample_id in sample_ids:
        raw = (
            synthetic_world.e21 / "transcripts" / "nlp_references" / f"{sample_id}.nlp"
        ).read_bytes()
        manifest_entries.append(
            {"id": sample_id, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        )
    artifacts_dir = receipts / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / "d1-identity.json").write_text(
        json.dumps(
            {
                "carriers": {
                    "earnings21-original": {
                        "layers": {"nlp_references": {"manifest": manifest_entries}}
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    (receipts / "e0-closure.json").write_text(
        json.dumps({"deliverables": {"d1_identity": {"artifact": "artifacts/d1-identity.json"}}}),
        encoding="utf-8",
    )
    _git_init_commit(repo_root)
    _, split_hash, _ = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    # bare-core has no evidence constraint (evidence_source: "none"), so it
    # composes and runs equally well against either real dataset fragment;
    # earnings21-discovery.json is used here purely because it matches the
    # synthetic world's already-frozen "discovery" split above -- no
    # test-only override of a compose() result, a genuinely real composition.
    composed = compose(
        REPO_ROOT, "qwen3-omni-llamacpp", "earnings21-discovery", "bare-core", "r0-smoke"
    )
    assert composed.values["scorers"] == ["asr-wer", "cost"]
    plan = _plan(
        split_hash,
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    manifest_path = run_experiment_bundled(
        composed, plan, _OpenGate(), lock, synthetic_world.data_root,
        tmp_path / "run-real-scorers", _transport, repo_root=repo_root,
    )
    bundle = verify_bundle(manifest_path)
    assert bundle.manifest["scorers"] == ["asr-wer", "cost"]
    results = score_bundle(bundle, lock, synthetic_world.data_root, repo_root=repo_root)
    assert set(results) == {"asr-wer", "cost"}
    assert results["asr-wer"]["aggregate"]["samples"] == 3
    assert results["cost"]["aggregate"]["calls_used"] == 3


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


def test_run_experiment_feeds_measured_gpu_seconds_back_into_the_durable_attempt_record(
    synthetic_world, tmp_path
):
    """fix-wave2 Minor: gpu hours had no derived counterpart -- calls/audio
    seconds were fed into the durable per-attempt record (core.attempts) on
    every request, but gpu_seconds, though measured for the whole run
    (RunResult.cost["gpu_seconds"]), was never written back to that durable
    file, so a reader of AttemptStore.all_actual_usage() could never see it.
    Proves the durable file itself, not merely the in-memory RunResult.cost,
    now carries it."""

    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, split_hash, _ = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed()
    plan = _plan(
        split_hash,
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    sampler = _FakeSampler(gpu_seconds=9.75, peak_vram_mib=2048.0)
    run_experiment(
        composed=composed,
        plan=plan,
        gate=_OpenGate(),
        lock=lock,
        root=synthetic_world.data_root,
        run_dir=tmp_path / "run-cost-sampler-durable",
        transport=_transport,
        repo_root=repo_root,
        resource_sampler=sampler,
    )
    store = AttemptStore(synthetic_world.data_root / "attempts")
    handle = store.handle(plan.run_id, plan.attempt_id)
    assert handle.actual_gpu_seconds() == 9.75
    assert store.all_actual_usage()[2] == 9.75


def test_run_experiment_without_a_resource_sampler_leaves_gpu_seconds_unrecorded(
    synthetic_world, tmp_path
):
    """The feed-back is best-effort and conditional on a REAL measurement:
    when no sampler is supplied (NOT_AVAILABLE), the durable attempt record
    must stay at the field's own zero default, never raise, and never record
    the NOT_AVAILABLE sentinel string as if it were a number."""

    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, split_hash, _ = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed()
    plan = _plan(
        split_hash,
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    run_experiment(
        composed=composed,
        plan=plan,
        gate=_OpenGate(),
        lock=lock,
        root=synthetic_world.data_root,
        run_dir=tmp_path / "run-cost-no-sampler-durable",
        transport=_transport,
        repo_root=repo_root,
    )
    store = AttemptStore(synthetic_world.data_root / "attempts")
    handle = store.handle(plan.run_id, plan.attempt_id)
    assert handle.actual_gpu_seconds() == 0.0


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


# ---------------------------------------------------------------------------
# SUPPLY dose knob (evidence_budget_bytes, core.evidence_budget): absent/0 is
# byte-identical to the sibling test above; a positive value truncates ONCE
# per sample, before _emit_sample_preamble's byte accounting -- so both the
# aggregated cost fields AND the bytes actually sent reflect the
# POST-truncation size; a bad value refuses at composition time, before any
# other per-run work.
# ---------------------------------------------------------------------------


def test_run_experiment_zero_evidence_budget_matches_the_unlimited_default(
    synthetic_world, tmp_path
):
    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, split_hash, _ = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed(**_baseline_fragment("fixed-legal-context"), evidence_budget_bytes=0)
    plan = _plan(
        split_hash,
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    run_dir = tmp_path / "run-cost-evidence-budget-zero"
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
    # same expected figure as the sibling absent-key test above -- 0 is
    # unlimited exactly like omitting the key entirely.
    expected_bytes = 3 * len(supply_by_sample)
    assert result.cost["supplied_evidence_bytes"] == expected_bytes
    request_records = [
        record
        for record in _raw_trace_records(run_dir, plan.run_id)
        if record["record_id"].endswith("/request")
    ]
    assert request_records
    for record in request_records:
        content = record["payload"]["payload"]["supplied_evidence"][0]["content"]
        assert content == "ctx"  # byte-identical to today's un-truncated context


def test_run_experiment_positive_evidence_budget_truncates_supplied_and_admitted_bytes(
    synthetic_world, tmp_path
):
    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, split_hash, _ = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed(**_baseline_fragment("fixed-legal-context"), evidence_budget_bytes=2)
    plan = _plan(
        split_hash,
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    run_dir = tmp_path / "run-cost-evidence-budget-positive"
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
    # the shipped conec fixture context is "ctx" (3 bytes); budget=2 caps
    # every sample's supplied evidence at exactly 2 (post-truncation) bytes
    # -- the SAME figure the existing supply_content_bytes/cost aggregation
    # already computes, no new field needed.
    expected_bytes = 2 * len(supply_by_sample)
    assert result.cost["supplied_evidence_bytes"] == expected_bytes
    assert result.cost["admitted_evidence_bytes"] == expected_bytes
    request_records = [
        record
        for record in _raw_trace_records(run_dir, plan.run_id)
        if record["record_id"].endswith("/request")
    ]
    assert request_records
    for record in request_records:
        content = record["payload"]["payload"]["supplied_evidence"][0]["content"]
        assert content == "ct"
        assert len(content.encode("utf-8")) <= 2


def test_run_experiment_refuses_a_negative_evidence_budget(synthetic_world, tmp_path):
    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, split_hash, _ = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed(evidence_budget_bytes=-1)
    plan = _plan(
        split_hash,
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    with pytest.raises(EvidenceError, match="evidence_budget_bytes"):
        run_experiment(
            composed=composed,
            plan=plan,
            gate=_OpenGate(),
            lock=lock,
            root=synthetic_world.data_root,
            run_dir=tmp_path / "run-evidence-budget-negative",
            transport=_transport,
            repo_root=repo_root,
        )


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


# ---------------------------------------------------------------------------
# Per-slice decode-cap saturation, aggregated per run (2026-08-09, continues
# the obs-loop E-001 retry finding): a real end-to-end run_experiment call
# through the obs-agent-loop policy over all 3 discovery samples, with a fake
# transport that pins each sample's completion_tokens deliberately either
# side of the configured cap -- proves the sequential per-sample loop in
# core.driver.run.run_experiment sums SampleOutcome.saturated_slices and
# collects sample ids correctly, not merely that a single sample's own count
# is right (already covered at the policy level in test_obs_loop_policy.py).
# ---------------------------------------------------------------------------

from array import array as _array  # noqa: E402

from speech_aware_evidence_acquisition.reproduction import obs_loop as _obs_loop  # noqa: E402


def _saturation_config(**overrides):
    """Single-iteration-per-sample fixed-mode obs-loop config: no boundary
    prompt template needed, one slice per sample (buffer covers the whole
    synthetic PCM in one shot -- is_final on iteration 0)."""

    values = {
        "obs_buffer_seconds": 40,
        "obs_min_advance_seconds": 40,
        "obs_max_advance_seconds": 40,
        "obs_fallback_advance_seconds": 40,
        "obs_silence_snap_seconds": 0,
        "obs_boundary_mode": "fixed",
        "obs_vad_trim_min_seconds": 0,
    }
    values.update(overrides)
    return values


def test_run_experiment_aggregates_saturated_slices_across_samples(
    synthetic_world, tmp_path, monkeypatch
):
    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    ids, split_hash, _ = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    assert ids == {"4000001", "4000002", "4000003"}

    # 30s of fake PCM per sample -- well inside the loader-fact 100.5s parent
    # duration (+1s tolerance) the slice-derivation chain checks against
    # (core.model.slices.PARENT_DURATION_TOLERANCE_SECONDS); the monkeypatch
    # only replaces the DECODE step, never the real on-disk parent bytes the
    # slice's own parent_sha256 chains to.
    pcm = _array("h", [1000] * (30 * 16000))
    monkeypatch.setattr(_obs_loop, "decode_parent_pcm", lambda path, rate=16000: pcm)

    # Each sample's completion_tokens sits deliberately either side of the
    # configured cap (5): 4000001 well over, 4000002 well under, 4000003
    # exactly AT the cap (the >= boundary case).
    completion_tokens_by_sample = {"4000001": 10, "4000002": 2, "4000003": 5}

    def _transport(request_bytes):
        payload = json.loads(request_bytes.decode("utf-8"))
        completion_tokens = completion_tokens_by_sample[payload["sample_id"]]
        return json.dumps(
            {"text": "hello", "usage": {"completion_tokens": completion_tokens}}
        ).encode()

    composed = _composed(
        policy="obs-agent-loop",
        decoding_params={"temperature": 0, "seed": 20260803, "max_tokens": 5},
        **_saturation_config(),
    )
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
        run_dir=tmp_path / "run-saturation",
        transport=_transport,
        repo_root=repo_root,
    )
    assert result.cost["saturated_slice_count"] == 2
    assert result.cost["saturated_sample_ids"] == ["4000001", "4000003"]


# ---------------------------------------------------------------------------
# Exhausted-slice skip, aggregated per run (Task 2, 2026-08-09, continues the
# obs-loop E-001 retry finding): a real end-to-end run_experiment call through
# the obs-agent-loop policy over all 3 discovery samples, with a fake
# transport that times out (retryable) BOTH attempts of one sample's FIRST
# slice -- proving the sequential per-sample loop in core.driver.run.
# run_experiment sums SampleOutcome.skipped_slices and collects sample ids
# correctly (mirrors test_run_experiment_aggregates_saturated_slices_across_
# samples immediately above, exactly the pattern the skip aggregate copies).
# ---------------------------------------------------------------------------


def test_run_experiment_aggregates_skipped_slices_across_samples(
    synthetic_world, tmp_path, monkeypatch
):
    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    ids, split_hash, _ = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    assert ids == {"4000001", "4000002", "4000003"}

    # 40s of fake PCM per sample, TWO 20s iterations each (not one -- an
    # exhausted lone iteration would hit the pre-existing empty-hypothesis
    # guard instead of completing the sample, which is not what this test is
    # proving) -- well inside the loader-fact 100.5s parent duration
    # tolerance; the monkeypatch only replaces the DECODE step, never the
    # real on-disk parent bytes the slice's own parent_sha256 chains to.
    pcm = _array("h", [1000] * (40 * 16000))
    monkeypatch.setattr(_obs_loop, "decode_parent_pcm", lambda path, rate=16000: pcm)

    # Only sample 4000001's FIRST slice ever times out -- both its original
    # attempt AND its retry -- exhausting obs_slice_retry_max=1 (the
    # from_values default) and skipping it; every other request across all
    # 3 samples succeeds normally.
    def _transport(request_bytes):
        payload = json.loads(request_bytes.decode("utf-8"))
        if payload["sample_id"] == "4000001" and payload["request_id"] in (
            "req-0001-i0000",
            "req-0001-i0000-r1",
        ):
            raise TimeoutError("simulated slice stall")
        return json.dumps({"text": "hello", "usage": {}}).encode()

    composed = _composed(
        policy="obs-agent-loop",
        decoding_params={"temperature": 0, "seed": 20260803},
        **_saturation_config(
            obs_buffer_seconds=20,
            obs_min_advance_seconds=20,
            obs_max_advance_seconds=20,
            obs_fallback_advance_seconds=20,
        ),
    )
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
        run_dir=tmp_path / "run-skip",
        transport=_transport,
        repo_root=repo_root,
    )
    assert result.cost["skipped_slice_count"] == 1
    assert result.cost["skipped_sample_ids"] == ["4000001"]
    # key-shape parity with the saturation pair -- both aggregates ride the
    # SAME cost block every run produces, never one without the other.
    assert result.cost["saturated_slice_count"] == 0
    assert result.cost["saturated_sample_ids"] == []
    # the skipped sample still completed and produced a real (non-empty)
    # output row -- the SURVIVING slice's content, not an abort.
    lines = result.outputs_path.read_text(encoding="utf-8").splitlines()
    rows = {json.loads(line)["sample_id"]: json.loads(line) for line in lines}
    assert set(rows) == {"4000001", "4000002", "4000003"}
    assert rows["4000001"]["text"]


# ---------------------------------------------------------------------------
# Sample-batched dispatch (owner directive 2026-08-08): obs_batch_samples > 1
# routes through a batch-capable policy's run_samples with per-sample
# TraceBuffers; outputs rows and trace blocks land in split-id order, byte-
# identical per sample to the sequential path. The batch contract: the policy
# sets the current trace buffer (core.tracing.set_current_trace_buffer) per
# sample so the shared adapter's emissions route to that sample's buffer.
# ---------------------------------------------------------------------------

from speech_aware_evidence_acquisition.core.base import POLICIES  # noqa: E402
from speech_aware_evidence_acquisition.core.policies import FixedPolicy  # noqa: E402
from speech_aware_evidence_acquisition.core.tracing import (  # noqa: E402
    set_current_trace_buffer,
)


class _BatchFixedPolicy(FixedPolicy):
    """FixedPolicy plus the batch seam: per-sample contextvar routing, then
    the exact per-sample logic -- the minimal honest batch-capable policy."""

    def run_samples(self, contexts):
        outcomes = []
        for ctx in contexts:
            set_current_trace_buffer(ctx.sink)
            try:
                outcomes.append(self.run_sample(ctx))
            finally:
                set_current_trace_buffer(None)
        return outcomes


POLICIES.register("fixed-batch-test", _BatchFixedPolicy())


def _record_ids(run_dir, run_id="SAEA-E-000-driver"):
    raw = (run_dir / f"{run_id}.trace.jsonl").read_text(encoding="utf-8")
    return [json.loads(line)["record_id"] for line in raw.splitlines() if line]


def test_batched_run_matches_sequential_rows_and_groups_trace_per_sample(
    synthetic_world, tmp_path
):
    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    ids, split_hash, _ = load_split(
        repo_root, "discovery", lock, synthetic_world.data_root
    )

    def run(policy_name, run_id, run_dir, extra_values):
        composed = _composed(policy=policy_name, **extra_values)
        plan = _plan(
            split_hash,
            run_id=run_id,
            attempt_id=f"attempt-{run_id}",
            protocol_hash=protocol_hash(
                composed.config_hash, composed.values["arm"], split_hash
            ),
        )
        return run_experiment(
            composed=composed,
            plan=plan,
            gate=_OpenGate(),
            lock=lock,
            root=synthetic_world.data_root,
            run_dir=run_dir,
            transport=_transport,
            repo_root=repo_root,
        )

    sequential = run("fixed", "SAEA-E-000-seq", tmp_path / "seq", {})
    batched = run(
        "fixed-batch-test",
        "SAEA-E-000-bat",
        tmp_path / "bat",
        {"obs_batch_samples": 2},
    )

    sequential_rows = [
        json.loads(line)
        for line in sequential.outputs_path.read_text(encoding="utf-8").splitlines()
    ]
    batched_rows = [
        json.loads(line)
        for line in batched.outputs_path.read_text(encoding="utf-8").splitlines()
    ]
    assert batched_rows == sequential_rows  # split-id order, identical rows
    assert batched.cost["calls_used"] == sequential.cost["calls_used"] == len(ids)

    sequential_ids = _record_ids(tmp_path / "seq", "SAEA-E-000-seq")
    batched_ids = _record_ids(tmp_path / "bat", "SAEA-E-000-bat")
    assert batched_ids == sequential_ids  # per-sample grouping preserved


def test_batching_a_sequential_only_policy_refuses(synthetic_world, tmp_path):
    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, split_hash, _ = load_split(
        repo_root, "discovery", lock, synthetic_world.data_root
    )
    composed = _composed(obs_batch_samples=2)  # policy "fixed": no run_samples
    plan = _plan(
        split_hash,
        protocol_hash=protocol_hash(
            composed.config_hash, composed.values["arm"], split_hash
        ),
    )
    with pytest.raises(CoreError, match="batch-capable"):
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


@pytest.mark.parametrize("bad", [0, -1, True, 1.5, "four"])
def test_bad_obs_batch_samples_refuses(synthetic_world, tmp_path, bad):
    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, split_hash, _ = load_split(
        repo_root, "discovery", lock, synthetic_world.data_root
    )
    composed = _composed(obs_batch_samples=bad)
    plan = _plan(
        split_hash,
        protocol_hash=protocol_hash(
            composed.config_hash, composed.values["arm"], split_hash
        ),
    )
    with pytest.raises(CoreError, match="obs_batch_samples"):
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
# Derivation-chain rail wiring (2026-08-09, docs/readiness/2026-08-09-conec-
# evidence-shape.md "Blocking gap"): run_experiment hands every evidence
# item's DerivedEvidenceRecord to core.evidence_derivation.
# DerivedEvidenceRegistry before a run proceeds, and only carrier_bound
# records ever reach the (unchanged) D1 evidence-identity rail. Two test-only
# evidence sources, registered here (module scope, like _BatchFixedPolicy
# above) so a duplicate-registration refusal can never fire across reruns of
# a single test function within one process.
# ---------------------------------------------------------------------------

from speech_aware_evidence_acquisition.core.base import (  # noqa: E402
    EVIDENCE_SOURCES,
    DerivedEvidenceRecord,
    EvidenceItem,
)
from speech_aware_evidence_acquisition.core.evidence_derivation import (  # noqa: E402
    canonical_params_hash,
)


def _no_derivation_evidence_source(lock, root, sample_id, carrier_lock_key, values=None):
    """A misbehaving evidence source: real content, NO derivation record --
    exactly what any evidence source predating this rail looked like."""

    return [
        EvidenceItem(
            evidence_id=f"test-no-derivation/{sample_id}",
            source_uri="test-no-derivation://x",
            content="some evidence text",
            provenance={"lock_key": "conec", "relpath": "r", "sha256": "0" * 64},
        )
    ]


EVIDENCE_SOURCES.register("test-no-derivation-evidence", _no_derivation_evidence_source)


def _carrier_independent_evidence_source(lock, root, sample_id, carrier_lock_key, values=None):
    """A test double for a carrier-independent source (deliverable 3): its
    own honest ``carrier_bound=False`` record, chained to a combined
    (non-per-sample) source via the ``identity`` transform for simplicity --
    the point under test is run_experiment's ROUTING, not any particular
    transform's content logic (that is covered by
    core.bias_lists/distractor-only-bias-list's own tests)."""

    text = "combined bias-lists-style evidence for this test"
    source_bytes = text.encode("utf-8")
    derivation = DerivedEvidenceRecord(
        sample_id=sample_id,
        source_relpath="test/combined-a.txt+test/combined-b.txt",
        source_sha256=hashlib.sha256(source_bytes).hexdigest(),
        transform_name="identity",
        transform_version="v1",
        params_hash=canonical_params_hash({}),
        derived_sha256=hashlib.sha256(source_bytes).hexdigest(),
        carrier_bound=False,
    )
    return [
        EvidenceItem(
            evidence_id=f"test-carrier-independent/{sample_id}",
            source_uri="test-carrier-independent://x",
            content=text,
            provenance={"lock_key": "conec", "relpath": "r", "sha256": "0" * 64},
            derivation=derivation,
            derivation_source_bytes=source_bytes,
        )
    ]


EVIDENCE_SOURCES.register(
    "test-carrier-independent-evidence", _carrier_independent_evidence_source
)


def test_run_experiment_refuses_evidence_with_no_derivation_record(synthetic_world, tmp_path):
    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, split_hash, _ = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed(
        arm="fixed-legal-context", evidence_source="test-no-derivation-evidence"
    )
    plan = _plan(
        split_hash,
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    with pytest.raises(CoreError, match="no derivation record"):
        run_experiment(
            composed=composed,
            plan=plan,
            gate=_OpenGate(),
            lock=lock,
            root=synthetic_world.data_root,
            run_dir=tmp_path / "run-no-derivation",
            transport=_transport,
            repo_root=repo_root,
        )


def test_run_experiment_excludes_a_carrier_independent_record_from_the_d1_rail(
    synthetic_world, tmp_path
):
    """The honest treatment (deliverable 3): a carrier_bound=False record's
    sample never reaches the (unchanged) D1 evidence-identity rail at all --
    there is no D1 record to check it against -- yet the run still completes,
    because the derivation chain's own self-verification
    (DerivedEvidenceRegistry) is a genuine, independent identity anchor."""

    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, split_hash, _ = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed(
        arm="fixed-legal-context", evidence_source="test-carrier-independent-evidence"
    )
    plan = _plan(
        split_hash,
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    gate = _EvidenceCheckingGate()
    result = run_experiment(
        composed=composed,
        plan=plan,
        gate=gate,
        lock=lock,
        root=synthetic_world.data_root,
        run_dir=tmp_path / "run-carrier-independent",
        transport=_transport,
        repo_root=repo_root,
    )
    assert isinstance(result, RunResult)
    assert gate.checked == []
    assert gate.content_checked == []


# ---------------------------------------------------------------------------
# Acoustic exemplar banks (core.exemplars, M-C-prime prep infrastructure):
# exemplar_manifest_id key legality (against the composed config's own
# prompt_order), byte-identity when the key is absent, and per-sample
# manifest-id/sha256/count provenance traced the same "ORG" way evidence
# sources already are.
# ---------------------------------------------------------------------------


def _write_exemplar_manifest(data_root, manifest_id, samples):
    import json as _json

    path = data_root / "derived" / "exemplar-pairs" / manifest_id / "manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        _json.dumps(
            {"schema": "saea-mc2-exemplar-pairs-manifest-v1", "samples": samples},
        ),
        encoding="utf-8",
    )
    return path


def test_run_experiment_without_exemplar_manifest_id_emits_no_exemplar_trace(
    synthetic_world, tmp_path
):
    """Deliverable 1's byte-identity contract at the run_experiment seam:
    the absent key must add no trace record at all -- checked directly,
    beyond merely "the pre-existing test suite still passes"."""

    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, split_hash, _ = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed()
    plan = _plan(
        split_hash,
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    run_experiment(
        composed=composed,
        plan=plan,
        gate=_OpenGate(),
        lock=lock,
        root=synthetic_world.data_root,
        run_dir=tmp_path / "run-no-exemplars",
        transport=_transport,
        repo_root=repo_root,
    )
    manifest = json.loads(
        (tmp_path / "run-no-exemplars" / "SAEA-E-000-driver.trace-manifest.json").read_text(
            "utf-8"
        )
    )["records"]
    assert not any("org-exemplars" in record_id for record_id in manifest)


def test_run_experiment_refuses_exemplar_manifest_id_without_v3_prompt_order(
    synthetic_world, tmp_path
):
    from speech_aware_evidence_acquisition.core.exemplars import ExemplarError

    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, split_hash, _ = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed(exemplar_manifest_id="mc2-test")  # no prompt_order declared
    plan = _plan(
        split_hash,
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    with pytest.raises(ExemplarError, match="prompt_order"):
        run_experiment(
            composed=composed,
            plan=plan,
            gate=_OpenGate(),
            lock=lock,
            root=synthetic_world.data_root,
            run_dir=tmp_path / "run-exemplar-illegal",
            transport=_transport,
            repo_root=repo_root,
        )


def test_run_experiment_resolves_exemplar_manifest_and_traces_provenance(
    synthetic_world, tmp_path
):
    """Deliverable 2/4 end to end: a real manifest on disk resolves into a
    per-sample bank and an ORG record carrying the manifest id, its own
    sha256, and this sample's exemplar count -- for every sample once the
    key is declared, including samples with zero "found" exemplars
    (empty-bank is legal, module docstring)."""

    manifest_id = "mc2-test"
    content = b"exemplar-audio-bytes"
    wav_path = (
        synthetic_world.data_root
        / "derived"
        / "exemplar-pairs"
        / manifest_id
        / "4000001"
        / "alpha.wav"
    )
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    wav_path.write_bytes(content)
    _write_exemplar_manifest(
        synthetic_world.data_root,
        manifest_id,
        {
            "4000001": {
                "alpha": {
                    "term": "alpha",
                    "status": "found",
                    "span_sha256": hashlib.sha256(content).hexdigest(),
                }
            },
            "4000002": {"beta": {"term": "beta", "status": "no-cross-call-occurrence"}},
            # 4000003 deliberately absent from the manifest entirely.
        },
    )

    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, split_hash, _ = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed(prompt_order="evidence-first-system-v3", exemplar_manifest_id=manifest_id)
    plan = _plan(
        split_hash,
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    run_dir = tmp_path / "run-exemplar-trace"
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
    assert isinstance(result, RunResult)
    raw = (run_dir / "SAEA-E-000-driver.trace.jsonl").read_text(encoding="utf-8")
    records = {
        document["record_id"]: document["payload"]
        for document in (json.loads(line) for line in raw.splitlines() if line)
    }
    # ordered_samples is sorted by sample_id: 4000001 -> req-0001, etc.
    found = records["req-0001/org-exemplars"]
    assert found["org_exemplar_manifest_id"] == manifest_id
    assert len(found["org_exemplar_manifest_sha256"]) == 64
    assert found["org_exemplar_count"] == 1
    rejected_only = records["req-0002/org-exemplars"]
    assert rejected_only["org_exemplar_count"] == 0
    absent_from_manifest = records["req-0003/org-exemplars"]
    assert absent_from_manifest["org_exemplar_count"] == 0
    assert absent_from_manifest["org_exemplar_manifest_id"] == manifest_id
