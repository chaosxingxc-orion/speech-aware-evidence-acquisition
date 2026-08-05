"""Atomic run bundle: manifest build + verify + finalize (R0 repair T6, I7).

Required regression probes (task-6 brief), each proved ACCEPT -> REJECT (or,
for the legitimate flow, REJECT-everywhere-else -> ACCEPT end to end):

1. mutated outputs text with a stale response_text_sha256 -> refused.
2. outputs sample set != frozen split (missing / extra / duplicate) -> refused.
3. trace manifest not matching the raw trace -> refused.
4. any artifact hash mismatch in the manifest -> refused.
5. finalizing an ABORTED attempt as COMPLETED -> refused (two shapes: a
   genuinely aborted run, and a COMPLETED manifest whose attempt was
   independently marked ABORTED afterward -- the durable attempt file, not
   the manifest's self-reported status, is authoritative).
6. a hand-supplied ledger cell that contradicts the verified manifest -> refused.
7. a legitimate synthetic run finalizes end to end and produces a ledger row.

T6 fix-round regression probes (independent review PoCs against the
committed T6 code), each also proved ACCEPT -> REJECT:

C1. forged outputs text covered only by an emptied raw trace + emptied trace
    manifest (all outer hashes recomputed to match) -> refused; plus a
    non-empty-trace-missing-one-record variant.
C2. a dirty study repo is refused BEFORE run_experiment spends any attempt
    budget; a manifest-build failure after a successful run still forces the
    attempt to ABORTED (never left OPENED with no manifest at all).
I3. a run manifest (and a finalize call) may never land inside the study
    repository.
I4. `saea-driver score --manifest` is the authoritative, verified path;
    `--outputs` is explicitly unverified.

T6 fix-2 round (re-review found finding 2's SIBLING path still open, plus a
LOW/INFO hedge in the request-record check):

C2b. dirty-tree TOCTOU DURING a failing run (tree clean when
     require_clean_study_repo ran, dirtied before the ABORTED-path manifest
     write, run fails for an unrelated reason) -> the original exception
     still propagates (never masked/replaced) AND an ABORTED manifest still
     exists, carrying an UNAVAILABLE:<reason> study_commit marker; a
     COMPLETED manifest can never carry that marker.
L1.  a non-empty trace missing exactly one outputs row's {request_id}/request
     record (previously hedged, so a forged request_sha256 passed) -> refused.
"""

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import speech_aware_evidence_acquisition.core  # noqa: F401 (populate registries)
from speech_aware_evidence_acquisition.contracts import ExecutionPlan
from speech_aware_evidence_acquisition.core.attempts import AttemptError, AttemptHandle, AttemptStore
from speech_aware_evidence_acquisition.core.bundle import (
    STATUS_ABORTED,
    STATUS_COMPLETED,
    UNAVAILABLE_COMMIT_PREFIX,
    BundleError,
    VerifiedBundle,
    build_manifest,
    finalize_bundle,
    verify_bundle,
)
from speech_aware_evidence_acquisition.core.base import CoreError
from speech_aware_evidence_acquisition.core.config import ComposedConfig, protocol_hash
from speech_aware_evidence_acquisition.core.driver import (
    load_split,
    main as driver_main,
    run_experiment,
    run_experiment_bundled,
)
from speech_aware_evidence_acquisition.core.split_receipt import load_verified_split
from speech_aware_evidence_acquisition.core.tracking import ledger_row_for_bundle
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.data.splits import freeze_splits
from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT, sha256_file, write_json_artifact


class _OpenGate:
    def assert_model_touch_allowed(self, plan):
        pass


def _transport(request_bytes):
    return json.dumps({"text": "token tags", "usage": {"prompt_tokens": 3}}).encode()


def _failing_transport(request_bytes):
    raise RuntimeError("transport exploded")


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
        run_id="SAEA-E-000-bundle",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="earnings21-original",
        split_role="discovery",
        split_identity_hash=split_hash,
        planned_model_calls=10,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=1000,
        protocol_hash="b" * 64,
        attempt_id="attempt-bundle",
    )
    base.update(overrides)
    return ExecutionPlan(**base)


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo_root, check=True, capture_output=True, text=True)


def _git_init_commit(repo_root: Path) -> None:
    _git(repo_root, "init", "-q")
    _git(repo_root, "config", "user.email", "test@example.com")
    _git(repo_root, "config", "user.name", "Test")
    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-q", "-m", "test snapshot")


def _write_real_reference_tokens(synthetic_world) -> None:
    """conftest.SyntheticWorld's default e21 nlp_references carry only a
    header row (no token rows) -- fine for tests that never score, but
    score_asr_outputs (run for real inside finalize_bundle) needs at least
    one token row per sample. Mirrors conftest.py's own E21_IDS tuple."""

    e21_ids = ("4000001", "4000002", "4000003")
    for sample_id in e21_ids:
        nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / f"{sample_id}.nlp"
        nlp.write_text(f"token|tags\nhello-{sample_id}|\nworld|\n", encoding="utf-8")


@pytest.fixture()
def bundled_repo(synthetic_world, tmp_path):
    """A study-repo-shaped, ACTUAL git repo (frozen splits receipt + a real
    commit) distinct from the real study checkout -- ``core.tracing.TraceSink``
    only refuses the real ``REPO_ROOT`` constant, never this fixture's path,
    so run artifacts under a sibling ``run_dir`` are unaffected either way."""

    _write_real_reference_tokens(synthetic_world)
    lock = load_lock(synthetic_world.lock_path)
    repo_root = tmp_path / "repo"
    receipts = repo_root / "docs" / "receipts"
    freeze_splits(lock, synthetic_world.data_root, receipts)
    _git_init_commit(repo_root)
    return lock, repo_root


def _run_completed(
    synthetic_world, bundled_repo, tmp_path, *, run_id="SAEA-E-000-bundle",
    attempt_id="attempt-bundle", transport=_transport, run_dir_name="run",
):
    lock, repo_root = bundled_repo
    ids, split_hash, split_role = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed()
    plan = _plan(
        split_hash, run_id=run_id, attempt_id=attempt_id,
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    manifest_path = run_experiment_bundled(
        composed, plan, _OpenGate(), lock, synthetic_world.data_root,
        tmp_path / run_dir_name, transport, repo_root=repo_root,
    )
    return manifest_path, composed, plan, lock


def _read_manifest(manifest_path: Path) -> dict:
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _read_jsonl_lines(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return lines


def _write_jsonl_lines(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _rehash_manifest_entry(manifest_path: Path, key: str) -> None:
    """Simulate an attacker who controls BOTH an artifact file AND their own
    outer-hash claim about it in the manifest: recompute only ``key``'s
    sha256 to match the mutated bytes, so tests exercise the DEEPER
    cross-checks (per-row text hash, trace binding, sample-set membership)
    rather than merely the outer artifact-hash guard."""

    manifest = _read_manifest(manifest_path)
    path = Path(manifest[key]["path"])
    manifest[key]["sha256"] = sha256_file(path)
    write_json_artifact(manifest_path, manifest)


_HUMAN_LEDGER_CELLS = {
    "experiment_id": "SAEA-E-000",
    "speech task/carrier": "earnings21-original discovery",
    "changed axes": "none (T6 probe)",
    "shared code revision": "n/a",
    "model rev": "n/a",
    "dataset rev": "n/a",
    "MLflow run": "n/a",
    "effectiveness": "n/a",
    "reasonableness": "n/a",
    "efficiency": "n/a",
    "deviations": "none",
    "decision": "test",
}


# ---------------------------------------------------------------------------
# build_manifest / _study_commit.
# ---------------------------------------------------------------------------


def test_build_manifest_binds_study_commit_config_plan_split_and_artifacts(
    synthetic_world, bundled_repo, tmp_path
):
    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    manifest = _read_manifest(manifest_path)
    assert manifest["schema"] == "saea-run-manifest-v1"
    assert manifest["status"] == STATUS_COMPLETED
    assert len(manifest["study_commit"]) == 40
    assert manifest["config"]["config_hash"] == composed.config_hash
    assert manifest["config"]["fragments"] == dict(composed.fragments)
    assert manifest["protocol_hash"] == plan.protocol_hash
    assert manifest["plan"]["attempt_id"] == plan.attempt_id
    assert manifest["exposure_run_id"] == plan.run_id
    assert manifest["split"]["role"] == "discovery"
    assert len(manifest["split"]["ids"]) == 3
    assert manifest["outputs"]["sha256"] == sha256_file(Path(manifest["outputs"]["path"]))
    assert manifest["raw_trace"]["sha256"] == sha256_file(Path(manifest["raw_trace"]["path"]))
    assert manifest["scores"] is None


def test_build_manifest_completed_status_refuses_a_dirty_study_repo(synthetic_world, bundled_repo, tmp_path):
    """A COMPLETED manifest's strictness is UNCHANGED by the T6 fix-2 round's
    ABORTED-only tolerance below: a dirty tree still refuses
    build_manifest(status=COMPLETED) outright."""

    lock, repo_root = bundled_repo
    ids, split_hash, split_role = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed()
    plan = _plan(split_hash, protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash))
    result = run_experiment(
        composed, plan, _OpenGate(), lock, synthetic_world.data_root,
        tmp_path / "run", _transport, repo_root=repo_root,
    )
    (repo_root / "uncommitted.txt").write_text("dirty", encoding="utf-8")
    verified_split = load_verified_split(repo_root, "discovery", lock, synthetic_world.data_root)
    with pytest.raises(BundleError, match="uncommitted"):
        build_manifest(
            repo_root=repo_root, data_root=synthetic_world.data_root, composed=composed,
            plan=plan, verified_split=verified_split, session_receipt_path=None,
            run_dir=tmp_path / "run", status=STATUS_COMPLETED, result=result,
        )


def test_build_manifest_aborted_status_tolerates_a_dirty_study_repo(synthetic_world, bundled_repo, tmp_path):
    """T6 fix-2 round: unlike COMPLETED, an ABORTED manifest tolerates a
    dirty/unreadable study repo -- it records the UNAVAILABLE:<reason>
    study_commit marker instead of refusing outright, so a run that already
    failed for one reason does not ALSO lose its audit record over the tree
    going dirty."""

    lock, repo_root = bundled_repo
    (repo_root / "uncommitted.txt").write_text("dirty", encoding="utf-8")
    ids, split_hash, split_role = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed()
    plan = _plan(split_hash, protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash))
    verified_split = load_verified_split(repo_root, "discovery", lock, synthetic_world.data_root)
    manifest_path = build_manifest(
        repo_root=repo_root, data_root=synthetic_world.data_root, composed=composed,
        plan=plan, verified_split=verified_split, session_receipt_path=None,
        run_dir=tmp_path / "run", status=STATUS_ABORTED, failure_reason="dirty-tree probe",
    )
    manifest = _read_manifest(manifest_path)
    assert manifest["status"] == STATUS_ABORTED
    assert manifest["study_commit"].startswith(UNAVAILABLE_COMMIT_PREFIX)
    assert "uncommitted" in manifest["study_commit"]


def test_build_manifest_refuses_a_non_git_repo_root(synthetic_world, tmp_path):
    lock = load_lock(synthetic_world.lock_path)
    repo_root = tmp_path / "not-a-repo"
    receipts = repo_root / "docs" / "receipts"
    freeze_splits(lock, synthetic_world.data_root, receipts)
    ids, split_hash, split_role = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed()
    plan = _plan(split_hash, protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash))
    verified_split = load_verified_split(repo_root, "discovery", lock, synthetic_world.data_root)
    result = run_experiment(
        composed, plan, _OpenGate(), lock, synthetic_world.data_root,
        tmp_path / "run", _transport, repo_root=repo_root,
    )
    with pytest.raises(BundleError, match="git status|HEAD"):
        build_manifest(
            repo_root=repo_root, data_root=synthetic_world.data_root, composed=composed,
            plan=plan, verified_split=verified_split, session_receipt_path=None,
            run_dir=tmp_path / "run", status=STATUS_COMPLETED, result=result,
        )


# ---------------------------------------------------------------------------
# Required probe 1: mutated outputs text, stale response_text_sha256.
# ---------------------------------------------------------------------------


def test_verify_bundle_accepts_a_legitimate_completed_bundle(synthetic_world, bundled_repo, tmp_path):
    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    bundle = verify_bundle(manifest_path)
    assert isinstance(bundle, VerifiedBundle)
    assert len(bundle.outputs_rows) == 3
    assert bundle.split_ids == {row["sample_id"] for row in bundle.outputs_rows}
    assert bundle.attempt_state == "OPENED"


def test_verify_bundle_refuses_mutated_text_with_stale_response_text_hash(
    synthetic_world, bundled_repo, tmp_path
):
    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    manifest = _read_manifest(manifest_path)
    outputs_path = Path(manifest["outputs"]["path"])
    lines = _read_jsonl_lines(outputs_path)
    row = json.loads(lines[0])
    row["text"] = row["text"] + " TAMPERED"
    # response_sha256 / response_text_sha256 deliberately left stale --
    # exactly the reproduced defect (task-6 brief): a row whose text was
    # mutated while keeping its old hash.
    lines[0] = json.dumps(row, ensure_ascii=False, sort_keys=True)
    _write_jsonl_lines(outputs_path, lines)
    # The attacker also "fixes" the manifest's own outer outputs hash, so
    # this probe exercises the DEEP per-row text<->hash binding, not merely
    # the outer artifact-hash guard (covered separately below).
    _rehash_manifest_entry(manifest_path, "outputs")
    with pytest.raises(BundleError, match="response_text_sha256"):
        verify_bundle(manifest_path)


# ---------------------------------------------------------------------------
# Required probe 2: outputs sample set != frozen split.
# ---------------------------------------------------------------------------


def test_verify_bundle_refuses_a_missing_sample_id(synthetic_world, bundled_repo, tmp_path):
    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    manifest = _read_manifest(manifest_path)
    outputs_path = Path(manifest["outputs"]["path"])
    lines = _read_jsonl_lines(outputs_path)
    _write_jsonl_lines(outputs_path, lines[1:])
    _rehash_manifest_entry(manifest_path, "outputs")
    with pytest.raises(BundleError, match="missing frozen split ids"):
        verify_bundle(manifest_path)


def test_verify_bundle_refuses_an_extra_sample_id(synthetic_world, bundled_repo, tmp_path):
    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    manifest = _read_manifest(manifest_path)
    outputs_path = Path(manifest["outputs"]["path"])
    lines = _read_jsonl_lines(outputs_path)
    extra = json.loads(lines[0])
    extra["sample_id"] = "9999999"
    extra["request_id"] = "req-9999"
    lines.append(json.dumps(extra, ensure_ascii=False, sort_keys=True))
    _write_jsonl_lines(outputs_path, lines)
    _rehash_manifest_entry(manifest_path, "outputs")
    with pytest.raises(BundleError, match="outside the frozen split"):
        verify_bundle(manifest_path)


def test_verify_bundle_refuses_a_duplicate_sample_id(synthetic_world, bundled_repo, tmp_path):
    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    manifest = _read_manifest(manifest_path)
    outputs_path = Path(manifest["outputs"]["path"])
    lines = _read_jsonl_lines(outputs_path)
    lines.append(lines[0])
    _write_jsonl_lines(outputs_path, lines)
    _rehash_manifest_entry(manifest_path, "outputs")
    with pytest.raises(BundleError, match="duplicate sample ids"):
        verify_bundle(manifest_path)


# ---------------------------------------------------------------------------
# Required probe 3: trace manifest not matching the raw trace.
# ---------------------------------------------------------------------------


def test_verify_bundle_refuses_trace_manifest_disagreeing_with_raw_trace(
    synthetic_world, bundled_repo, tmp_path
):
    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    manifest = _read_manifest(manifest_path)
    raw_trace_path = Path(manifest["raw_trace"]["path"])
    lines = _read_jsonl_lines(raw_trace_path)
    obs_index = next(i for i, line in enumerate(lines) if '"channel":"OBS"' in line)
    document = json.loads(lines[obs_index])
    document["payload"]["obs_audio_seconds"] = 999999.0
    lines[obs_index] = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    _write_jsonl_lines(raw_trace_path, lines)
    # Fix the raw trace's own outer hash (attacker controls the file) but
    # leave the trace-manifest's per-record hash for this record stale.
    _rehash_manifest_entry(manifest_path, "raw_trace")
    with pytest.raises(BundleError, match="trace manifest"):
        verify_bundle(manifest_path)


# ---------------------------------------------------------------------------
# Required probe 4: any artifact hash mismatch in the manifest.
# ---------------------------------------------------------------------------


def test_verify_bundle_refuses_any_artifact_hash_mismatch(synthetic_world, bundled_repo, tmp_path):
    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    manifest = _read_manifest(manifest_path)
    raw_trace_path = Path(manifest["raw_trace"]["path"])
    # Mutate the artifact WITHOUT recomputing the manifest's recorded hash --
    # the outer-hash guard alone must catch this.
    with raw_trace_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write('{"channel":"COST","record_id":"tamper","payload":{"calls":1}}\n')
    with pytest.raises(BundleError, match="hash mismatch"):
        verify_bundle(manifest_path)


def test_verify_bundle_refuses_a_missing_artifact_file(synthetic_world, bundled_repo, tmp_path):
    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    manifest = _read_manifest(manifest_path)
    Path(manifest["outputs"]["path"]).unlink()
    with pytest.raises(BundleError, match="cannot read"):
        verify_bundle(manifest_path)


# ---------------------------------------------------------------------------
# Required probe 5: finalizing an ABORTED attempt as COMPLETED.
# ---------------------------------------------------------------------------


def test_finalize_bundle_refuses_a_genuinely_aborted_manifest(synthetic_world, bundled_repo, tmp_path):
    lock, repo_root = bundled_repo
    ids, split_hash, split_role = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed()
    plan = _plan(
        split_hash, run_id="SAEA-E-000-abort", attempt_id="attempt-abort",
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    with pytest.raises(RuntimeError, match="transport exploded"):
        run_experiment_bundled(
            composed, plan, _OpenGate(), lock, synthetic_world.data_root,
            tmp_path / "run-abort", _failing_transport, repo_root=repo_root,
        )
    manifest_path = tmp_path / "run-abort" / f"{plan.run_id}.run-manifest.json"
    assert manifest_path.is_file()
    manifest = _read_manifest(manifest_path)
    assert manifest["status"] == STATUS_ABORTED
    assert manifest["failure_reason"]
    store = AttemptStore(synthetic_world.data_root / "attempts")
    assert store.handle(plan.run_id, plan.attempt_id).state() == "ABORTED"
    with pytest.raises(BundleError, match="COMPLETED"):
        finalize_bundle(manifest_path, lock, synthetic_world.data_root)


def test_finalize_bundle_refuses_when_attempt_is_aborted_even_if_manifest_still_says_completed(
    synthetic_world, bundled_repo, tmp_path
):
    """The deeper shape of probe 5: the manifest's OWN status field still
    reads COMPLETED (never hand-edited), but the attempt's durable state was
    independently marked ABORTED after the fact -- finalize must trust the
    attempt file, not the manifest's self-report."""

    manifest_path, composed, plan, lock = _run_completed(
        synthetic_world, bundled_repo, tmp_path, run_id="SAEA-E-000-postabort",
        attempt_id="attempt-postabort",
    )
    manifest = _read_manifest(manifest_path)
    assert manifest["status"] == STATUS_COMPLETED
    attempt_meta = manifest["attempt"]
    AttemptHandle(
        path=Path(attempt_meta["state_path"]), run_id=attempt_meta["run_id"],
        attempt_id=attempt_meta["attempt_id"],
    ).mark_aborted("operator discovered a post-hoc problem")
    with pytest.raises(BundleError, match="durable state"):
        finalize_bundle(manifest_path, lock, synthetic_world.data_root)


# ---------------------------------------------------------------------------
# Required probe 6: hand-supplied ledger cell contradicting the manifest.
# ---------------------------------------------------------------------------


def test_ledger_row_for_bundle_refuses_a_contradicting_hand_supplied_cell(
    synthetic_world, bundled_repo, tmp_path
):
    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    bundle = verify_bundle(manifest_path)
    bad_cells = {**_HUMAN_LEDGER_CELLS, "study commit": "0" * 40}
    with pytest.raises(ValueError, match="contradict"):
        ledger_row_for_bundle(bundle, bad_cells)


def test_ledger_row_for_bundle_accepts_a_matching_hand_supplied_cell(
    synthetic_world, bundled_repo, tmp_path
):
    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    bundle = verify_bundle(manifest_path)
    good_cells = {**_HUMAN_LEDGER_CELLS, "study commit": bundle.manifest["study_commit"]}
    row, merged = ledger_row_for_bundle(bundle, good_cells)
    assert merged["study commit"] == bundle.manifest["study_commit"]
    assert merged["consumed"] == "yes"
    assert row.startswith("|") and row.endswith("|")


# ---------------------------------------------------------------------------
# Required probe 7: a legitimate synthetic run finalizes end to end.
# ---------------------------------------------------------------------------


def test_finalize_bundle_end_to_end_produces_a_ledger_row(synthetic_world, bundled_repo, tmp_path):
    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    result = finalize_bundle(
        manifest_path, lock, synthetic_world.data_root, ledger_cells=_HUMAN_LEDGER_CELLS
    )
    assert result.scores_path.is_file()
    assert result.ledger_markdown_path.is_file()
    assert result.ledger_json_path.is_file()
    assert result.attempt_state == "FINALIZED"
    assert result.mlflow_run_id is None

    manifest = _read_manifest(manifest_path)
    assert manifest["scores"]["sha256"] == sha256_file(Path(manifest["scores"]["path"]))
    scores = json.loads(Path(manifest["scores"]["path"]).read_text(encoding="utf-8"))
    assert "asr-wer" in scores
    assert scores["asr-wer"]["aggregate"]["samples"] == 3

    ledger_cells = json.loads(result.ledger_json_path.read_text(encoding="utf-8"))
    assert ledger_cells["consumed"] == "yes"
    assert ledger_cells["experiment_id"] == "SAEA-E-000"

    store = AttemptStore(synthetic_world.data_root / "attempts")
    assert store.handle(plan.run_id, plan.attempt_id).state() == "FINALIZED"

    # A second finalize on the identical manifest must now refuse -- the
    # attempt is no longer OPENED.
    with pytest.raises(BundleError, match="FINALIZED"):
        finalize_bundle(manifest_path, lock, synthetic_world.data_root, ledger_cells=_HUMAN_LEDGER_CELLS)


def test_finalize_bundle_uploads_via_stubbed_mlflow(synthetic_world, bundled_repo, tmp_path, monkeypatch):
    import sys
    import types

    manifest_path, composed, plan, lock = _run_completed(
        synthetic_world, bundled_repo, tmp_path, run_id="SAEA-E-000-mlflow",
        attempt_id="attempt-mlflow", run_dir_name="run-mlflow",
    )
    calls = {"artifacts": []}

    class _ActiveRunStub:
        def __enter__(self):
            return types.SimpleNamespace(info=types.SimpleNamespace(run_id="mlrun-bundle-1"))

        def __exit__(self, *exc_info):
            return False

    stub = types.SimpleNamespace(
        set_tracking_uri=lambda uri: None,
        set_experiment=lambda name: None,
        start_run=lambda run_name: _ActiveRunStub(),
        log_params=lambda params: None,
        log_metrics=lambda metrics: None,
        log_artifact=lambda path: calls["artifacts"].append(path),
    )
    monkeypatch.setitem(sys.modules, "mlflow", stub)

    result = finalize_bundle(
        manifest_path, lock, synthetic_world.data_root,
        ledger_cells=_HUMAN_LEDGER_CELLS, tracking_uri=str(tmp_path / "mlruns"),
    )
    assert result.mlflow_run_id == "mlrun-bundle-1"
    # outputs, raw trace, trace manifest, scores, manifest itself -- 5 artifacts.
    assert len(calls["artifacts"]) == 5
    ledger_cells = json.loads(result.ledger_json_path.read_text(encoding="utf-8"))
    assert ledger_cells["MLflow run"] == "mlrun-bundle-1"


# ===========================================================================
# T6 fix-round regression probes (independent review, all against the
# COMMITTED T6 code, all reproduced live before the fix and REJECTed after).
# ===========================================================================


# ---------------------------------------------------------------------------
# CRITICAL 1: _verify_outputs_trace_binding's "return early when trace_records
# is empty" no-op let a forged outputs text sail through whenever the trace
# was also emptied (outer hashes recomputed to match) -- the per-row hash
# check alone was never enough; nothing was cross-checking against the trace
# at all once the trace was hollowed out.
# ---------------------------------------------------------------------------


def test_verify_bundle_refuses_forged_text_covered_only_by_an_emptied_trace(
    synthetic_world, bundled_repo, tmp_path
):
    """The exact reviewer PoC: mutate outputs text + response_text_sha256
    CONSISTENTLY (defeats the per-row hash check on its own), then truncate
    the raw trace to empty and the trace manifest's records to {}, and
    recompute all three outer artifact hashes. Before the fix, verify_bundle
    ACCEPTED this. Must now REJECT."""

    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    manifest = _read_manifest(manifest_path)
    outputs_path = Path(manifest["outputs"]["path"])
    lines = _read_jsonl_lines(outputs_path)
    row = json.loads(lines[0])
    forged_text = "FORGED " + row["text"]
    row["text"] = forged_text
    row["response_text_sha256"] = hashlib.sha256(forged_text.encode("utf-8")).hexdigest()
    lines[0] = json.dumps(row, ensure_ascii=False, sort_keys=True)
    _write_jsonl_lines(outputs_path, lines)

    raw_trace_path = Path(manifest["raw_trace"]["path"])
    trace_manifest_path = Path(manifest["trace_manifest"]["path"])
    raw_trace_path.write_text("", encoding="utf-8", newline="\n")
    write_json_artifact(trace_manifest_path, {"run_id": plan.run_id, "records": {}})

    _rehash_manifest_entry(manifest_path, "outputs")
    _rehash_manifest_entry(manifest_path, "raw_trace")
    _rehash_manifest_entry(manifest_path, "trace_manifest")

    with pytest.raises(BundleError, match="no matching trace record"):
        verify_bundle(manifest_path)


def test_verify_bundle_refuses_an_emptied_trace_against_nonempty_outputs(
    synthetic_world, bundled_repo, tmp_path
):
    """Named probe (b) from the review: emptied trace + emptied manifest
    records, outer hashes recomputed, outputs untouched (still non-empty) ->
    REJECT."""

    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    manifest = _read_manifest(manifest_path)
    raw_trace_path = Path(manifest["raw_trace"]["path"])
    trace_manifest_path = Path(manifest["trace_manifest"]["path"])
    raw_trace_path.write_text("", encoding="utf-8", newline="\n")
    write_json_artifact(trace_manifest_path, {"run_id": plan.run_id, "records": {}})
    _rehash_manifest_entry(manifest_path, "raw_trace")
    _rehash_manifest_entry(manifest_path, "trace_manifest")
    with pytest.raises(BundleError, match="no matching trace record"):
        verify_bundle(manifest_path)


def test_verify_bundle_refuses_when_trace_is_missing_one_outputs_request_id_record(
    synthetic_world, bundled_repo, tmp_path
):
    """Named probe (a) from the review: an otherwise-valid, non-empty trace
    that is missing exactly ONE request_id's /response record (raw trace AND
    trace manifest agree with each other -- both genuinely lack it, outer
    hashes recomputed) -> REJECT. Isolates the outputs<->trace binding check
    from the separate trace-manifest<->raw-trace agreement check."""

    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    manifest = _read_manifest(manifest_path)
    raw_trace_path = Path(manifest["raw_trace"]["path"])
    trace_manifest_path = Path(manifest["trace_manifest"]["path"])

    target_record_id = "req-0002/response"
    lines = _read_jsonl_lines(raw_trace_path)
    kept = [line for line in lines if f'"record_id":"{target_record_id}"' not in line]
    assert len(kept) == len(lines) - 1, "the target record must have existed exactly once"
    _write_jsonl_lines(raw_trace_path, kept)

    tm_doc = json.loads(trace_manifest_path.read_text(encoding="utf-8"))
    del tm_doc["records"][target_record_id]
    write_json_artifact(trace_manifest_path, tm_doc)

    _rehash_manifest_entry(manifest_path, "raw_trace")
    _rehash_manifest_entry(manifest_path, "trace_manifest")

    with pytest.raises(BundleError, match="no matching trace record"):
        verify_bundle(manifest_path)


# ---------------------------------------------------------------------------
# CRITICAL 2: a successful, budget-consuming run must never end with NO
# manifest and its attempt stuck OPENED forever.
# ---------------------------------------------------------------------------


def test_run_experiment_bundled_refuses_a_dirty_repo_before_spending_any_budget(
    synthetic_world, bundled_repo, tmp_path
):
    lock, repo_root = bundled_repo
    (repo_root / "uncommitted.txt").write_text("dirty", encoding="utf-8")
    ids, split_hash, split_role = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed()
    plan = _plan(
        split_hash, run_id="SAEA-E-000-dirtybudget", attempt_id="attempt-dirtybudget",
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    with pytest.raises(BundleError, match="uncommitted"):
        run_experiment_bundled(
            composed, plan, _OpenGate(), lock, synthetic_world.data_root,
            tmp_path / "run-dirtybudget", _transport, repo_root=repo_root,
        )
    # No budget spent: the attempt was never even opened.
    store = AttemptStore(synthetic_world.data_root / "attempts")
    assert store.prior_actual_usage(plan.run_id) == (0, 0.0)
    assert not (synthetic_world.data_root / "attempts" / plan.run_id).exists()
    # No model call: no outputs, no manifest, nothing written to run_dir at all.
    run_dir = tmp_path / "run-dirtybudget"
    assert not (run_dir / f"{plan.run_id}.outputs.jsonl").exists()
    assert not (run_dir / f"{plan.run_id}.run-manifest.json").exists()


def test_run_experiment_bundled_forces_attempt_aborted_when_manifest_build_fails_after_success(
    synthetic_world, bundled_repo, tmp_path, monkeypatch
):
    """A successful run (budget spent, outputs/trace durable) whose trailing
    COMPLETED-manifest build itself fails must still end with the attempt
    ABORTED and a best-effort ABORTED manifest on disk -- never OPENED
    forever with no manifest at all."""

    import speech_aware_evidence_acquisition.core.driver as driver_module

    lock, repo_root = bundled_repo
    ids, split_hash, split_role = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed()
    plan = _plan(
        split_hash, run_id="SAEA-E-000-manifestfail", attempt_id="attempt-manifestfail",
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )

    real_build_manifest = driver_module.build_manifest
    calls = {"n": 0}

    def _flaky_build_manifest(**kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("disk full (simulated)")
        return real_build_manifest(**kwargs)

    monkeypatch.setattr(driver_module, "build_manifest", _flaky_build_manifest)
    run_dir = tmp_path / "run-manifestfail"
    with pytest.raises(RuntimeError, match="disk full"):
        driver_module.run_experiment_bundled(
            composed, plan, _OpenGate(), lock, synthetic_world.data_root,
            run_dir, _transport, repo_root=repo_root,
        )
    # The run itself succeeded -- outputs really were written -- but the
    # attempt must be ABORTED, not left OPENED, and a best-effort ABORTED
    # manifest must exist.
    assert (run_dir / f"{plan.run_id}.outputs.jsonl").is_file()
    store = AttemptStore(synthetic_world.data_root / "attempts")
    assert store.handle(plan.run_id, plan.attempt_id).state() == "ABORTED"
    manifest_path = run_dir / f"{plan.run_id}.run-manifest.json"
    assert manifest_path.is_file()
    assert _read_manifest(manifest_path)["status"] == STATUS_ABORTED


# ---------------------------------------------------------------------------
# IMPORTANT 3: no bundle artifact may ever be written inside the repository.
# ---------------------------------------------------------------------------


def test_build_manifest_refuses_a_run_dir_inside_the_repository(synthetic_world, bundled_repo):
    lock, repo_root = bundled_repo
    ids, split_hash, split_role = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed()
    plan = _plan(split_hash, protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash))
    verified_split = load_verified_split(repo_root, "discovery", lock, synthetic_world.data_root)
    sneaky_run_dir = REPO_ROOT / "docs" / "sneaky-t6-run-dir-must-not-be-created"
    try:
        with pytest.raises(BundleError, match="repository"):
            build_manifest(
                repo_root=repo_root, data_root=synthetic_world.data_root, composed=composed,
                plan=plan, verified_split=verified_split, session_receipt_path=None,
                run_dir=sneaky_run_dir, status=STATUS_ABORTED,
                failure_reason="repo-confinement probe",
            )
        assert not sneaky_run_dir.exists(), "no artifact may ever be written inside the repository"
    finally:
        if sneaky_run_dir.exists():
            shutil.rmtree(sneaky_run_dir)


def test_finalize_bundle_refuses_a_manifest_path_inside_the_repository(tmp_path):
    fake_manifest_path = REPO_ROOT / "docs" / "sneaky-t6-finalize-manifest-must-not-be-read.json"
    assert not fake_manifest_path.exists()
    with pytest.raises(BundleError, match="repository"):
        finalize_bundle(fake_manifest_path, {}, tmp_path)
    assert not fake_manifest_path.exists()


# ---------------------------------------------------------------------------
# IMPORTANT 4: saea-driver score --manifest is the authoritative path;
# --outputs is explicit, unverified, ad-hoc scoring only.
# ---------------------------------------------------------------------------


def test_cli_score_manifest_mode_is_verified_and_authoritative(
    synthetic_world, bundled_repo, tmp_path, capsys, monkeypatch
):
    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    monkeypatch.setenv("SPEECHRL_DATA_DIR", str(synthetic_world.data_root))
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.data.lock.umbrella_lock_path",
        lambda *a, **k: synthetic_world.lock_path,
    )
    exit_code = driver_main(["score", "--manifest", str(manifest_path)])
    assert exit_code == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["verified"] is True
    assert payload["scores"]["asr-wer"]["samples"] == 3
    assert "WARNING" not in captured.err


def test_cli_score_raw_outputs_mode_prints_a_loud_unverified_warning(
    synthetic_world, tmp_path, capsys, monkeypatch
):
    nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp"
    nlp.write_text("token|tags\nhello|\nworld|\n", encoding="utf-8")
    outputs = tmp_path / "raw.outputs.jsonl"
    outputs.write_text(
        json.dumps(
            {
                "sample_id": "4000001", "carrier_lock_key": "earnings21-original",
                "arm": "bare-core", "request_id": "req-0001", "text": "hello world",
                "request_sha256": "0" * 64, "response_sha256": "0" * 64,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SPEECHRL_DATA_DIR", str(synthetic_world.data_root))
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.data.lock.umbrella_lock_path",
        lambda *a, **k: synthetic_world.lock_path,
    )
    exit_code = driver_main(["score", "--outputs", str(outputs)])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "WARNING" in captured.err
    assert "NOT an audit record" in captured.err
    payload = json.loads(captured.out)
    assert payload["verified"] is False


def test_cli_score_refuses_both_manifest_and_outputs_together(tmp_path):
    with pytest.raises(SystemExit):
        driver_main(["score", "--manifest", str(tmp_path / "m.json"), "--outputs", str(tmp_path / "o.jsonl")])


def test_cli_score_refuses_neither_manifest_nor_outputs():
    with pytest.raises(SystemExit):
        driver_main(["score"])


# ===========================================================================
# T6 fix-2 round: finding 2's SIBLING path (the ABORTED-on-failure manifest
# write had no wrapping at all, unlike the success-path fix from the first
# fix round) + a LOW/INFO hedge in the request-record check.
# ===========================================================================


def test_verify_bundle_refuses_when_trace_is_missing_the_request_record_for_a_row(
    synthetic_world, bundled_repo, tmp_path
):
    """LOW/INFO fix: the request_sha256 cross-check was hedged
    (`if request_payload is not None and ...`), so deleting the
    {request_id}/request trace record (and its trace-manifest entry,
    self-consistently, outer hashes recomputed) let a hand-forged
    request_sha256 pass silently. Must now REJECT, mirroring the
    unconditional /response check."""

    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    manifest = _read_manifest(manifest_path)
    raw_trace_path = Path(manifest["raw_trace"]["path"])
    trace_manifest_path = Path(manifest["trace_manifest"]["path"])

    target_record_id = "req-0001/request"
    lines = _read_jsonl_lines(raw_trace_path)
    kept = [line for line in lines if f'"record_id":"{target_record_id}"' not in line]
    assert len(kept) == len(lines) - 1, "the target record must have existed exactly once"
    _write_jsonl_lines(raw_trace_path, kept)

    tm_doc = json.loads(trace_manifest_path.read_text(encoding="utf-8"))
    del tm_doc["records"][target_record_id]
    write_json_artifact(trace_manifest_path, tm_doc)

    _rehash_manifest_entry(manifest_path, "raw_trace")
    _rehash_manifest_entry(manifest_path, "trace_manifest")

    with pytest.raises(BundleError, match="no matching trace record"):
        verify_bundle(manifest_path)


def test_run_experiment_bundled_toctou_dirty_tree_during_a_failing_run_still_records_an_aborted_manifest(
    synthetic_world, bundled_repo, tmp_path
):
    """The reviewer's exact re-attack: the tree is CLEAN when
    require_clean_study_repo runs, becomes dirty DURING run_experiment (a
    real TOCTOU window in a long model-facing run -- simulated here via a
    transport whose side effect is dirtying the repo right before it fails
    for an unrelated reason), and the run then fails. Before this fix,
    build_manifest(status=ABORTED) raised its own BundleError over the dirty
    tree, masking the original failure and leaving zero manifest on disk.
    Now: the original exception still propagates, AND an ABORTED manifest
    exists, carrying the UNAVAILABLE:<reason> study_commit marker (root-cause
    fix: core.bundle._resolve_study_commit tolerates this for ABORTED)."""

    lock, repo_root = bundled_repo
    ids, split_hash, split_role = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed()
    plan = _plan(
        split_hash, run_id="SAEA-E-000-toctou", attempt_id="attempt-toctou",
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )

    def _dirty_then_fail(request_bytes):
        (repo_root / "toctou-dirty.txt").write_text("dirtied mid-run", encoding="utf-8")
        raise RuntimeError("model-facing transport exploded for an unrelated reason")

    run_dir = tmp_path / "run-toctou"
    with pytest.raises(RuntimeError, match="unrelated reason"):
        run_experiment_bundled(
            composed, plan, _OpenGate(), lock, synthetic_world.data_root,
            run_dir, _dirty_then_fail, repo_root=repo_root,
        )
    manifest_path = run_dir / f"{plan.run_id}.run-manifest.json"
    assert manifest_path.is_file(), "an ABORTED manifest must still exist despite the TOCTOU"
    manifest = _read_manifest(manifest_path)
    assert manifest["status"] == STATUS_ABORTED
    assert "unrelated reason" in manifest["failure_reason"]
    assert manifest["study_commit"].startswith(UNAVAILABLE_COMMIT_PREFIX)
    store = AttemptStore(synthetic_world.data_root / "attempts")
    assert store.handle(plan.run_id, plan.attempt_id).state() == "ABORTED"


def test_run_experiment_bundled_aborted_manifest_write_failure_never_masks_the_original_exception(
    synthetic_world, bundled_repo, tmp_path, monkeypatch
):
    """Defense in depth beyond the root-cause TOCTOU fix: even if
    build_manifest fails for some OTHER, unrelated reason on the ABORTED
    path (simulated here by monkeypatching it to always raise), the
    ORIGINAL run failure must still be what propagates -- chained
    (__context__), never replaced or silently dropped."""

    import speech_aware_evidence_acquisition.core.driver as driver_module

    lock, repo_root = bundled_repo
    ids, split_hash, split_role = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed()
    plan = _plan(
        split_hash, run_id="SAEA-E-000-maskcheck", attempt_id="attempt-maskcheck",
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )

    def _always_fail_build_manifest(**kwargs):
        raise RuntimeError("manifest write exploded too (simulated, unrelated)")

    monkeypatch.setattr(driver_module, "build_manifest", _always_fail_build_manifest)
    run_dir = tmp_path / "run-maskcheck"
    with pytest.raises(RuntimeError, match="transport exploded") as excinfo:
        driver_module.run_experiment_bundled(
            composed, plan, _OpenGate(), lock, synthetic_world.data_root,
            run_dir, _failing_transport, repo_root=repo_root,
        )
    assert "manifest write exploded too" not in str(excinfo.value)
    assert excinfo.value.__context__ is not None
    assert "manifest write exploded too" in str(excinfo.value.__context__)
    # No manifest could be written at all here (build_manifest itself is
    # fully broken by the monkeypatch) -- the guarantee under test is "the
    # ORIGINAL exception propagates," not "a manifest always exists when the
    # manifest-writer itself cannot write anything."
    assert not (run_dir / f"{plan.run_id}.run-manifest.json").exists()


# ===========================================================================
# R0 repair T7, invariant I8: cost accounting completion. An ABORTED manifest
# must never carry cost=None (silently omitting failed-attempt cost); a
# manifest built before T7 (the old 5-field cost shape) must still verify --
# the schema decision this task made instead of bumping RUN_MANIFEST_SCHEMA.
# ===========================================================================


def test_build_manifest_aborted_status_includes_a_best_effort_cost_block(
    synthetic_world, bundled_repo, tmp_path
):
    """An ABORTED manifest must never carry cost=None -- that would silently
    omit whatever this (now-failed) attempt genuinely spent before it failed,
    which contradicts I8's "no silent omission" requirement just as much as
    omitting the field from a successful run would."""

    lock, repo_root = bundled_repo
    ids, split_hash, split_role = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed()
    plan = _plan(
        split_hash, run_id="SAEA-E-000-abortcost", attempt_id="attempt-abortcost",
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    with pytest.raises(RuntimeError, match="transport exploded"):
        run_experiment_bundled(
            composed, plan, _OpenGate(), lock, synthetic_world.data_root,
            tmp_path / "run-abortcost", _failing_transport, repo_root=repo_root,
        )
    manifest_path = tmp_path / "run-abortcost" / f"{plan.run_id}.run-manifest.json"
    manifest = _read_manifest(manifest_path)
    assert manifest["status"] == STATUS_ABORTED
    cost = manifest["cost"]
    assert cost is not None
    # FrozenCoreAdapter.request persists attempt usage BEFORE invoking the
    # transport (R0 repair T4, I6) -- the first (and only, since it always
    # raises) sample's spend is durably recorded even though the run failed.
    assert cost["calls_used"] == 1
    assert cost["audio_seconds_used"] > 0.0
    # No sibling ABORTED attempt exists yet on this run_id.
    assert cost["failed_attempt_calls"] == 0
    assert cost["failed_attempt_audio_seconds"] == 0.0
    for key in (
        "latency_seconds_total", "prompt_tokens_total", "completion_tokens_total",
        "tool_calls", "cpu_seconds", "gate_setup_seconds",
        "supplied_evidence_bytes", "admitted_evidence_bytes",
        "gpu_seconds", "peak_vram_mib",
    ):
        assert cost[key] == "NOT_AVAILABLE", key
    assert cost["gpu_sampling_reason"]
    assert cost["cost_unavailable_reason"]


def test_build_manifest_aborted_status_folds_in_failed_attempt_cost_from_a_prior_sibling(
    synthetic_world, bundled_repo, tmp_path
):
    lock, repo_root = bundled_repo
    ids, split_hash, split_role = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed()
    run_id = "SAEA-E-000-abortcost-sibling"

    store = AttemptStore(synthetic_world.data_root / "attempts")
    prior_handle = store.open_attempt(
        run_id, "attempt-prior",
        carrier_lock_key="earnings21-original", reserved_calls=5, reserved_audio_seconds=500.0,
    )
    prior_handle.record_usage(calls=2, audio_seconds=50.0)
    prior_handle.mark_aborted("simulated earlier crash")

    plan = _plan(
        split_hash, run_id=run_id, attempt_id="attempt-fresh-fails",
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    with pytest.raises(RuntimeError, match="transport exploded"):
        run_experiment_bundled(
            composed, plan, _OpenGate(), lock, synthetic_world.data_root,
            tmp_path / "run-abortcost-sibling", _failing_transport, repo_root=repo_root,
        )
    manifest_path = tmp_path / "run-abortcost-sibling" / f"{plan.run_id}.run-manifest.json"
    cost = _read_manifest(manifest_path)["cost"]
    assert cost["failed_attempt_calls"] == 2
    assert cost["failed_attempt_audio_seconds"] == 50.0
    # This attempt's own spend is reported separately, unmixed with the
    # sibling's failed spend.
    assert cost["calls_used"] == 1


def test_build_manifest_aborted_status_never_opened_attempt_reports_zero_cost_not_none(
    synthetic_world, bundled_repo, tmp_path
):
    """A failure BEFORE FrozenCoreAdapter ever constructs (e.g. a
    protocol-hash mismatch) leaves no attempt file at all -- the best-effort
    cost block must degrade to zeros, never raise, and still be present
    (never None)."""

    lock, repo_root = bundled_repo
    ids, split_hash, split_role = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed()
    plan = _plan(
        split_hash, run_id="SAEA-E-000-neveropened", attempt_id="attempt-neveropened",
        protocol_hash="0" * 64,  # deliberately wrong -> CoreError before the adapter is built
    )
    with pytest.raises(CoreError, match="protocol hash"):
        run_experiment_bundled(
            composed, plan, _OpenGate(), lock, synthetic_world.data_root,
            tmp_path / "run-neveropened", _transport, repo_root=repo_root,
        )
    manifest_path = tmp_path / "run-neveropened" / f"{plan.run_id}.run-manifest.json"
    cost = _read_manifest(manifest_path)["cost"]
    assert cost is not None
    assert cost["calls_used"] == 0
    assert cost["audio_seconds_used"] == 0.0
    assert cost["failed_attempt_calls"] == 0


def test_run_experiment_bundled_completes_despite_a_corrupted_sibling_attempt_file(
    synthetic_world, bundled_repo, tmp_path, monkeypatch
):
    """T7 fix (reviewer-flagged IMPORTANT): the exact false-failure scenario.
    Before the fix, an unreadable sibling ABORTED attempt file for the same
    run_id raised AttemptError out of run_experiment's (then-unguarded)
    failed-attempt-cost lookup; run_experiment_bundled's `except Exception`
    then marked this genuinely successful, budget-spent run ABORTED. The run
    must now COMPLETE, with only failed_attempt_calls/audio_seconds degraded
    to NOT_AVAILABLE.

    Simulated via monkeypatching ``AttemptStore.actual_usage_in_states``
    (see the matching unit-level test in ``tests/unit/test_driver.py`` for
    why a literal corrupted sibling file on disk cannot isolate this
    specific call site: it would ALSO break the pre-existing, unrelated,
    by-design-strict I6 budget check inside ``FrozenCoreAdapter.__init__``
    before the run ever got this far)."""

    lock, repo_root = bundled_repo
    ids, split_hash, split_role = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed()
    run_id = "SAEA-E-000-corruptsibling-bundle"

    def _raising_actual_usage_in_states(self, run_id, states, *, exclude_attempt_id=None):
        raise AttemptError(
            f"cannot read prior attempt state {run_id}/attempt-corrupt.json: "
            "Expecting property name enclosed in double quotes (simulated corruption)"
        )

    monkeypatch.setattr(AttemptStore, "actual_usage_in_states", _raising_actual_usage_in_states)

    plan = _plan(
        split_hash, run_id=run_id, attempt_id="attempt-fresh",
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    manifest_path = run_experiment_bundled(
        composed, plan, _OpenGate(), lock, synthetic_world.data_root,
        tmp_path / "run-corruptsibling-bundle", _transport, repo_root=repo_root,
    )
    manifest = _read_manifest(manifest_path)
    assert manifest["status"] == STATUS_COMPLETED
    cost = manifest["cost"]
    assert cost["failed_attempt_calls"] == "NOT_AVAILABLE"
    assert cost["failed_attempt_audio_seconds"] == "NOT_AVAILABLE"
    assert cost["failed_attempt_cost_reason"]
    assert cost["calls_used"] == len(ids)
    store = AttemptStore(synthetic_world.data_root / "attempts")
    assert store.handle(run_id, "attempt-fresh").state() == "OPENED"


def test_verify_bundle_accepts_a_pre_t7_five_field_cost_shape(synthetic_world, bundled_repo, tmp_path):
    """R0 repair T7 schema decision: ``RUN_MANIFEST_SCHEMA`` stays
    ``saea-run-manifest-v1`` -- no version bump. ``verify_bundle`` performs
    no fixed-key-set check on the ``cost`` block (only ``core.scorers.
    score_cost_outputs`` requires it be a non-empty dict, with no key-set
    check either), so a manifest carrying the OLD, pre-T7 5-field cost shape
    (``calls_used``/``audio_seconds_used``/``latency_seconds_total``/
    ``prompt_tokens_total``/``completion_tokens_total`` only) still verifies
    and still scores end to end."""

    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    manifest = _read_manifest(manifest_path)
    manifest["cost"] = {
        "calls_used": 3,
        "audio_seconds_used": 301.5,
        "latency_seconds_total": 0.02,
        "prompt_tokens_total": 9,
        "completion_tokens_total": 0,
    }
    write_json_artifact(manifest_path, manifest)

    bundle = verify_bundle(manifest_path)
    assert isinstance(bundle, VerifiedBundle)

    from speech_aware_evidence_acquisition.core.scorers import score_cost_outputs

    result = score_cost_outputs(bundle.outputs_path, lock, synthetic_world.data_root)
    assert result["aggregate"]["calls_used"] == 3
    assert result["aggregate"]["audio_seconds_used"] == 301.5


def test_verify_bundle_refuses_a_completed_manifest_carrying_an_unavailable_commit_marker(
    synthetic_world, bundled_repo, tmp_path
):
    """A COMPLETED manifest may never carry the ABORTED-only
    UNAVAILABLE:<reason> study_commit marker -- structurally build_manifest
    never produces this combination, but verify_bundle refuses it
    independently too (defense in depth against a hand-tampered manifest)."""

    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    manifest = _read_manifest(manifest_path)
    assert manifest["status"] == STATUS_COMPLETED
    manifest["study_commit"] = f"{UNAVAILABLE_COMMIT_PREFIX}hand-forged, pretend git was fine"
    write_json_artifact(manifest_path, manifest)
    with pytest.raises(BundleError, match=UNAVAILABLE_COMMIT_PREFIX):
        verify_bundle(manifest_path)
