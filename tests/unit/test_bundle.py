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

import contextlib
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import speech_aware_evidence_acquisition.core  # noqa: F401 (populate registries)
from speech_aware_evidence_acquisition.contracts import ExecutionPlan, GateClosed
from speech_aware_evidence_acquisition.core.attempts import (
    AttemptError,
    AttemptHandle,
    AttemptStore,
)
from speech_aware_evidence_acquisition.core.bundle import (
    STATUS_ABORTED,
    STATUS_COMPLETED,
    UNAVAILABLE_COMMIT_PREFIX,
    BundleError,
    VerifiedBundle,
    _confine_child_path,
    build_manifest,
    finalize_bundle,
    verify_bundle,
)
from speech_aware_evidence_acquisition.core.bundle.git_commit import (
    require_clean_load_bearing_surface,
    require_clean_study_repo,
)
from speech_aware_evidence_acquisition.core.bundle.outputs import (
    _minimum_model_calls_from_trace,
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
from speech_aware_evidence_acquisition.e0.artifacts import (
    REPO_ROOT,
    sha256_file,
    write_json_artifact,
)


class _OpenGate:
    def assert_model_touch_allowed(self, plan):
        pass


def _transport(request_bytes):
    return json.dumps({"text": "token tags", "usage": {"prompt_tokens": 3}}).encode()


def _failing_transport(request_bytes):
    raise RuntimeError("transport exploded")


def test_composite_trace_cost_floor_counts_model_requests_not_tool_outputs(tmp_path):
    source = tmp_path / "frozen.outputs.jsonl"
    source.write_text("source bytes\n", encoding="utf-8")
    source_sha256 = sha256_file(source)
    trace = {
        "model-1/request": {
            "arm": "speech-feature-query",
            "payload": {"sample_id": "sample-1"},
            "payload_sha256": "a" * 64,
        },
        "model-1/response": {"text": "answer"},
        "composite-1/request": {
            "tool_id": "deterministic-composite-v1",
            "source": {"source_request_id": "model-1"},
        },
        "composite-2/request": {
            "tool_id": "deterministic-composite-v1",
            "source": {
                "source_artifact_path": str(source),
                "source_artifact_sha256": source_sha256,
            },
        },
    }
    assert _minimum_model_calls_from_trace(trace) == 1


def test_cost_floor_does_not_misclassify_legacy_observation_root_as_tool_output():
    trace = {
        "sample-1/request": {
            "obs_regions": ["sample-1-i0000", "sample-1-i0001"],
        },
        "sample-1-i0000/request": {
            "arm": "bare-core",
            "payload": {"sample_id": "sample-1"},
            "payload_sha256": "a" * 64,
        },
        "sample-1-i0000/response": {"text": "answer"},
    }
    assert _minimum_model_calls_from_trace(
        trace,
        output_request_ids=frozenset({"sample-1"}),
    ) == 1


def test_composite_trace_cost_floor_rejects_unbound_tool_provenance(tmp_path):
    missing = tmp_path / "missing.outputs.jsonl"
    with pytest.raises(BundleError, match="source provenance"):
        _minimum_model_calls_from_trace(
            {
                "composite/request": {
                    "tool_id": "deterministic-composite-v1",
                    "source": {},
                }
            }
        )
    with pytest.raises(BundleError, match="source artifact"):
        _minimum_model_calls_from_trace(
            {
                "composite/request": {
                    "tool_id": "deterministic-composite-v1",
                    "source": {
                        "source_artifact_path": str(missing),
                        "source_artifact_sha256": "b" * 64,
                    },
                }
            }
        )


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


@contextlib.contextmanager
def _tamper_real_scoring_source():
    """CRITICAL-fix probes (round-2 external-threat-model review): prove
    finalize_bundle/score_bundle/the CLI scoring paths refuse when a REAL
    frozen scoring source is edited -- the D3 freeze binds THIS checkout's
    actual scoring/ package (see core.scorers._assert_scoring_entry_gate's
    docstring), never any synthetic stand-in. Mirrors the established,
    self-cleaning pattern already used against the real gate in
    tests/contract/test_real_receipts.py: the file is restored to its EXACT
    original bytes in `finally`, so this never leaves the checkout modified
    even if the assertion inside the `with` block fails."""

    path = REPO_ROOT / "src" / "speech_aware_evidence_acquisition" / "scoring" / "wer.py"
    original = path.read_bytes()
    try:
        path.write_bytes(original + b"\n# tampered-by-round2-review-test\n")
        yield path
    finally:
        path.write_bytes(original)


def _git_init_commit(repo_root: Path) -> None:
    _git(repo_root, "init", "-q")
    _git(repo_root, "config", "user.email", "test@example.com")
    _git(repo_root, "config", "user.name", "Test")
    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-q", "-m", "test snapshot")


_E21_SCORED_IDS = ("4000001", "4000002", "4000003")


def _write_real_reference_tokens(synthetic_world) -> None:
    """conftest.SyntheticWorld's default e21 nlp_references carry only a
    header row (no token rows) -- fine for tests that never score, but
    score_asr_outputs (run for real inside finalize_bundle) needs at least
    one token row per sample. Mirrors conftest.py's own E21_IDS tuple."""

    for sample_id in _E21_SCORED_IDS:
        nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / f"{sample_id}.nlp"
        nlp.write_text(f"token|tags\nhello-{sample_id}|\nworld|\n", encoding="utf-8")


def _write_reference_d1_receipt(synthetic_world, receipts_dir: Path) -> None:
    """IMPORTANT 2 (fix-wave3, external-threat-model review round 3):
    ``core.scorers._assert_scoring_entry_gate`` now re-verifies the reference
    (``.nlp``) bytes ``score_asr_outputs`` is about to read against a D1
    identity artifact -- write a minimal, genuinely matching one (computed
    from the bytes :func:`_write_real_reference_tokens` JUST wrote, so it is
    never out of sync with them) into THIS fixture's own synthetic repo, the
    same way ``tests/contract/test_media_identity.py`` builds one for
    ``verify_media_identity``. Mirrors the real
    ``docs/receipts/artifacts/d1-identity.json`` shape exactly (``carriers ->
    layers -> nlp_references -> manifest``), just scoped to only the ids this
    test fixture's runs ever score."""

    manifest_entries = []
    for sample_id in _E21_SCORED_IDS:
        nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / f"{sample_id}.nlp"
        raw = nlp.read_bytes()
        manifest_entries.append(
            {"id": sample_id, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        )
    d1_document = {
        "carriers": {
            "earnings21-original": {
                "layers": {"nlp_references": {"manifest": manifest_entries}}
            }
        }
    }
    artifacts_dir = receipts_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / "d1-identity.json").write_text(json.dumps(d1_document), encoding="utf-8")
    e0_document = {
        "deliverables": {"d1_identity": {"artifact": "artifacts/d1-identity.json"}}
    }
    (receipts_dir / "e0-closure.json").write_text(json.dumps(e0_document), encoding="utf-8")


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
    _write_reference_d1_receipt(synthetic_world, receipts)
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
    # An empty list must write a genuinely EMPTY file (0 bytes), never a lone
    # "\n" -- core.bundle.outputs._verify_raw_trace's own empty-trace branch
    # only special-cases a 0-byte file; one blank line still fails
    # json.loads("") on the leftover empty element. A resumed bundle whose
    # OWN trace covers zero samples (every one of them kept by a
    # predecessor -- E10d's seal-only case) is exactly the shape this must
    # not misrepresent.
    content = "\n".join(lines) + "\n" if lines else ""
    path.write_text(content, encoding="utf-8", newline="\n")


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
    assert manifest["study_repo_dirt"] == []
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
    """E0-prime flight protection (2026-08-16): dirt INSIDE the load-bearing
    surface (src/, configs/, docs/arms/, scripts/) still refuses
    build_manifest(status=COMPLETED) outright -- unchanged. See the
    load-bearing-surface parametrized probe below for all four prefixes, and
    the sibling "outside the surface" probe proving that class now
    SURVIVES instead."""

    lock, repo_root = bundled_repo
    ids, split_hash, split_role = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed()
    plan = _plan(split_hash, protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash))
    result = run_experiment(
        composed, plan, _OpenGate(), lock, synthetic_world.data_root,
        tmp_path / "run", _transport, repo_root=repo_root,
    )
    (repo_root / "src" / "uncommitted.py").parent.mkdir(parents=True, exist_ok=True)
    (repo_root / "src" / "uncommitted.py").write_text("dirty", encoding="utf-8")
    verified_split = load_verified_split(repo_root, "discovery", lock, synthetic_world.data_root)
    with pytest.raises(BundleError, match="load-bearing"):
        build_manifest(
            repo_root=repo_root, data_root=synthetic_world.data_root, composed=composed,
            plan=plan, verified_split=verified_split, session_receipt_path=None,
            run_dir=tmp_path / "run", status=STATUS_COMPLETED, result=result,
        )


@pytest.mark.parametrize(
    "relpath",
    [
        "src/tampered.py",
        "configs/tampered.yaml",
        "docs/arms/tampered.arms",
        "scripts/tampered.sh",
    ],
)
def test_build_manifest_completed_status_refuses_dirt_anywhere_in_load_bearing_surface(
    synthetic_world, bundled_repo, tmp_path, relpath
):
    """E0-prime flight protection fixture (b): a mid-flight edit under any of
    the four load-bearing prefixes still refuses build_manifest(status=
    COMPLETED) -- code, config fragments, arm files, and launch scripts
    describe WHAT the run executed, so dirt there is still "the commit is a
    lie"."""

    lock, repo_root = bundled_repo
    ids, split_hash, split_role = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed()
    plan = _plan(split_hash, protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash))
    result = run_experiment(
        composed, plan, _OpenGate(), lock, synthetic_world.data_root,
        tmp_path / "run", _transport, repo_root=repo_root,
    )
    target = repo_root / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("tampered mid-flight", encoding="utf-8")
    verified_split = load_verified_split(repo_root, "discovery", lock, synthetic_world.data_root)
    with pytest.raises(BundleError, match="load-bearing"):
        build_manifest(
            repo_root=repo_root, data_root=synthetic_world.data_root, composed=composed,
            plan=plan, verified_split=verified_split, session_receipt_path=None,
            run_dir=tmp_path / "run", status=STATUS_COMPLETED, result=result,
        )


def test_build_manifest_completed_status_survives_dirt_outside_load_bearing_surface(
    synthetic_world, bundled_repo, tmp_path
):
    """E0-prime flight protection fixture (a): a mid-flight edit to a
    docs/*.md file OUTSIDE docs/arms/ (a governance-document shape, exactly
    the 2026-08-16 00:21Z incident's defect class) now SURVIVES
    build_manifest(status=COMPLETED) -- the manifest still binds a real,
    well-shaped study_commit, and the tolerated path is recorded on the
    manifest for auditability rather than silently dropped."""

    lock, repo_root = bundled_repo
    ids, split_hash, split_role = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed()
    plan = _plan(split_hash, protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash))
    result = run_experiment(
        composed, plan, _OpenGate(), lock, synthetic_world.data_root,
        tmp_path / "run", _transport, repo_root=repo_root,
    )
    # A NEW subdirectory (e.g. docs/readiness/) that is WHOLLY untracked
    # collapses in `git status --porcelain` output to just its own directory
    # entry (git's default untracked-file rendering) -- placed directly
    # under docs/ instead, which already has tracked content (docs/receipts,
    # written by freeze_splits below), so git lists this new file
    # individually, matching how a governance-doc edit shows up in the real
    # study repo (docs/ is a long-tracked directory there too).
    governance_doc = repo_root / "docs" / "mid-flight-note.md"
    governance_doc.write_text("a governance edit landed mid-flight", encoding="utf-8")
    verified_split = load_verified_split(repo_root, "discovery", lock, synthetic_world.data_root)
    manifest_path = build_manifest(
        repo_root=repo_root, data_root=synthetic_world.data_root, composed=composed,
        plan=plan, verified_split=verified_split, session_receipt_path=None,
        run_dir=tmp_path / "run", status=STATUS_COMPLETED, result=result,
    )
    manifest = _read_manifest(manifest_path)
    assert manifest["status"] == STATUS_COMPLETED
    assert len(manifest["study_commit"]) == 40
    assert manifest["study_repo_dirt"] == ["docs/mid-flight-note.md"]


@pytest.mark.parametrize(
    "relpath,seals",
    [
        ("src/tampered.py", False),
        ("configs/tampered.json", False),
        ("docs/arms/tampered.arms", False),
        ("scripts/tampered.sh", False),
        ("docs/2026-09-09-readiness-note.md", True),
        ("README-note.md", True),
    ],
)
def test_the_seal_half_and_the_score_half_share_one_load_bearing_rule(
    bundled_repo, relpath, seals
):
    """REGRESSION (2026-09-09): the two halves of one seal must agree.

    ``_study_commit_for_completed_manifest`` (the SEAL half) and
    ``core.scorers._assert_scoring_entry_gate`` (the SCORE half) both go
    through ``require_clean_load_bearing_surface`` now. Before this repair
    the score half called ``require_clean_study_repo`` instead, which refuses
    ANY dirt -- so a manifest could seal COMPLETED over an untracked
    readiness note and then never be scored or finalized on the same tree
    (measured as the Audio2Tool wire checks' ``seal_and_score =
    SCORING_FAILED``, receipt ``docs/checks/
    speech-aware-evidence-acquisition/
    2026-09-09-a2t-official-scorer-seal-and-score-diagnosis/``).

    This probes the shared rule directly, over both classes of dirt, so the
    two can never drift apart again without a red test.
    """

    _lock, repo_root = bundled_repo
    target = repo_root / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("landed after launch", encoding="utf-8")
    if seals:
        commit, tolerated = require_clean_load_bearing_surface(repo_root)
        assert len(commit) == 40
        assert tolerated == [relpath]
        # Same tree, the strict launch-time rule, which is deliberately NOT
        # what either half of the seal uses.
        with pytest.raises(BundleError, match="uncommitted"):
            require_clean_study_repo(repo_root)
    else:
        with pytest.raises(BundleError, match="load-bearing"):
            require_clean_load_bearing_surface(repo_root)


def test_run_experiment_bundled_toctou_dirty_tree_outside_load_bearing_surface_still_completes(
    synthetic_world, bundled_repo, tmp_path
):
    """The EXACT 2026-08-16 00:21Z incident, reproduced end to end and now
    repaired: the tree is clean when run_experiment_bundled's OWN preflight
    (require_clean_study_repo, unchanged/still strict) runs, a governance-
    document-shaped edit lands OUTSIDE the load-bearing surface DURING
    run_experiment (simulated via a transport whose side effect dirties the
    repo on its first call), and the run succeeds. BEFORE this fix,
    build_manifest(status=COMPLETED) then refused outright over ANY dirt,
    forcing the attempt to ABORTED -- and I7 forbids ever finalizing an
    ABORTED manifest as COMPLETED afterward, permanently stranding the real,
    complete outputs already on disk (156 minutes of inference, in the real
    incident). Now: the manifest is COMPLETED, binds a real study_commit,
    and the attempt stays OPENED (finalizable), never forced to ABORTED."""

    lock, repo_root = bundled_repo
    ids, split_hash, split_role = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed()
    plan = _plan(
        split_hash, run_id="SAEA-E-000-flightprotect", attempt_id="attempt-flightprotect",
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )

    dirtied = {"done": False}

    def _dirty_then_succeed(request_bytes):
        if not dirtied["done"]:
            # Placed directly under docs/ (already tracked in bundled_repo --
            # it holds docs/receipts), not in a brand-new subdirectory: an
            # entirely NEW, wholly-untracked directory collapses in `git
            # status --porcelain` to just its own directory entry, which
            # would defeat this test's point (it wants the full per-file
            # path git actually reports for a new file under an EXISTING
            # tracked directory -- exactly how a governance-doc edit shows
            # up in the real study repo, where docs/ is long-tracked).
            (repo_root / "docs" / "mid-flight-note.md").write_text(
                "a governance edit landed mid-flight", encoding="utf-8"
            )
            dirtied["done"] = True
        return _transport(request_bytes)

    manifest_path = run_experiment_bundled(
        composed, plan, _OpenGate(), lock, synthetic_world.data_root,
        tmp_path / "run", _dirty_then_succeed, repo_root=repo_root,
    )
    manifest = _read_manifest(manifest_path)
    assert manifest["status"] == STATUS_COMPLETED
    assert len(manifest["study_commit"]) == 40
    assert manifest["study_repo_dirt"] == ["docs/mid-flight-note.md"]

    store = AttemptStore(synthetic_world.data_root / "attempts")
    assert store.handle(plan.run_id, plan.attempt_id).state() == "OPENED"


def _write_flight_lock(
    data_root: Path, *, run_ids: list, study_head: str, pid: int = 999999,
    started_at: str = "2026-08-16T00:00:00Z",
) -> Path:
    path = Path(data_root) / "locks" / "flight.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "run_ids": list(run_ids), "pid": pid, "started_at": started_at, "study_head": study_head,
    }
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_build_manifest_completed_status_tolerates_dirt_when_flight_lock_head_matches(
    synthetic_world, bundled_repo, tmp_path
):
    """A flight lock's presence is not itself a refusal reason: when its
    recorded study_head still matches the tree's current HEAD, non-load-
    bearing dirt is tolerated exactly as with no lock present at all."""

    lock, repo_root = bundled_repo
    ids, split_hash, split_role = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed()
    plan = _plan(
        split_hash, run_id="SAEA-E-000-lockmatch", attempt_id="attempt-lockmatch",
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    result = run_experiment(
        composed, plan, _OpenGate(), lock, synthetic_world.data_root,
        tmp_path / "run", _transport, repo_root=repo_root,
    )
    current_head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_root, check=True, capture_output=True, text=True,
    ).stdout.strip()
    _write_flight_lock(synthetic_world.data_root, run_ids=[plan.run_id], study_head=current_head)
    (repo_root / "readiness-note.md").write_text("mid-flight note", encoding="utf-8")
    verified_split = load_verified_split(repo_root, "discovery", lock, synthetic_world.data_root)
    manifest_path = build_manifest(
        repo_root=repo_root, data_root=synthetic_world.data_root, composed=composed,
        plan=plan, verified_split=verified_split, session_receipt_path=None,
        run_dir=tmp_path / "run", status=STATUS_COMPLETED, result=result,
    )
    manifest = _read_manifest(manifest_path)
    assert manifest["status"] == STATUS_COMPLETED
    assert manifest["study_repo_dirt"] == ["readiness-note.md"]


def test_build_manifest_completed_status_refuses_when_head_moved_since_flight_lock(
    synthetic_world, bundled_repo, tmp_path
):
    """E0-prime flight protection fixture (c): even with a PERFECTLY clean
    tree, a HEAD that moved since the flight lock's recorded study_head
    still refuses build_manifest(status=COMPLETED) -- a moved HEAD is a
    different checked-out CODE identity, not mere dirt, and the load-
    bearing-surface carve-out was never meant to tolerate that."""

    lock, repo_root = bundled_repo
    ids, split_hash, split_role = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed()
    plan = _plan(
        split_hash, run_id="SAEA-E-000-headmoved", attempt_id="attempt-headmoved",
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    result = run_experiment(
        composed, plan, _OpenGate(), lock, synthetic_world.data_root,
        tmp_path / "run", _transport, repo_root=repo_root,
    )
    launch_head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_root, check=True, capture_output=True, text=True,
    ).stdout.strip()
    _write_flight_lock(synthetic_world.data_root, run_ids=[plan.run_id], study_head=launch_head)
    (repo_root / "committed-after-launch.txt").write_text("x", encoding="utf-8")
    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-q", "-m", "moved head mid-flight")
    verified_split = load_verified_split(repo_root, "discovery", lock, synthetic_world.data_root)
    with pytest.raises(BundleError, match="HEAD moved"):
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


# ---------------------------------------------------------------------------
# E1-prime (deliverable 3, docs/readiness/2026-08-15-legality-doctrine.md):
# the run manifest carries span_source/reference_source/legality_tier
# verbatim, plus the independently-recomputed oracle-lineage verdict and
# grandfathering warning. Exercised via the SAME lightweight ABORTED-manifest
# pattern as the fixture above -- build_manifest's own recomputation
# (core.legality.describe_legality_for_manifest) never depends on the run
# having actually succeeded.
# ---------------------------------------------------------------------------


def _build_probe_manifest(synthetic_world, bundled_repo, tmp_path, *, composed, run_dir_name):
    lock, repo_root = bundled_repo
    ids, split_hash, split_role = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    plan = _plan(split_hash, protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash))
    verified_split = load_verified_split(repo_root, "discovery", lock, synthetic_world.data_root)
    manifest_path = build_manifest(
        repo_root=repo_root, data_root=synthetic_world.data_root, composed=composed,
        plan=plan, verified_split=verified_split, session_receipt_path=None,
        run_dir=tmp_path / run_dir_name, status=STATUS_ABORTED, failure_reason="legality probe",
    )
    return _read_manifest(manifest_path)


def test_build_manifest_records_a_correctly_declared_legality_tier_verbatim(
    synthetic_world, bundled_repo, tmp_path
):
    composed = _composed(
        evidence_source="conec-contexts",
        span_source="roster-band-flag",
        reference_source="metadata-roster",
        legality_tier="legal",
    )
    manifest = _build_probe_manifest(
        synthetic_world, bundled_repo, tmp_path, composed=composed, run_dir_name="run-legality-clean"
    )
    assert manifest["legality"] == {
        "span_source": "roster-band-flag",
        "reference_source": "metadata-roster",
        "legality_tier": "legal",
        "evidence_materialization_id": None,
        "oracle_lineage_materialization": False,
        "declaration_warning": None,
    }


def test_build_manifest_records_the_grandfathering_warning_for_missing_declarations(
    synthetic_world, bundled_repo, tmp_path
):
    composed = _composed(evidence_source="conec-contexts")
    manifest = _build_probe_manifest(
        synthetic_world, bundled_repo, tmp_path, composed=composed, run_dir_name="run-legality-missing"
    )
    legality = manifest["legality"]
    assert legality["span_source"] is None
    assert legality["reference_source"] is None
    assert legality["legality_tier"] is None
    assert legality["declaration_warning"] is not None
    assert "GRANDFATHERED" in legality["declaration_warning"]


def test_build_manifest_never_raises_for_a_refused_legality_declaration(
    synthetic_world, bundled_repo, tmp_path
):
    """A REFUSED declaration (the either-field rule) must still produce a
    manifest -- deliverable 3's "carries the three fields verbatim" applies
    even to an attempt core.driver.run.run_experiment already aborted for
    this exact reason; build_manifest must never itself crash re-deriving
    it."""

    composed = _composed(
        evidence_source="conec-contexts", legality_tier="legal", reference_source="oracle-lineage"
    )
    manifest = _build_probe_manifest(
        synthetic_world, bundled_repo, tmp_path, composed=composed, run_dir_name="run-legality-refused"
    )
    legality = manifest["legality"]
    assert legality["reference_source"] == "oracle-lineage"
    assert legality["legality_tier"] == "legal"
    assert legality["declaration_warning"].startswith("REFUSED:")


def test_build_manifest_records_oracle_lineage_materialization_true(
    synthetic_world, bundled_repo, tmp_path
):
    composed = _composed(
        evidence_source="derived-candidates",
        evidence_materialization_id="p1-oracle-v2",
        span_source="roster-band-flag",
        reference_source="oracle-lineage",
        legality_tier="ceiling",
    )
    manifest = _build_probe_manifest(
        synthetic_world, bundled_repo, tmp_path, composed=composed, run_dir_name="run-legality-oracle"
    )
    legality = manifest["legality"]
    assert legality["oracle_lineage_materialization"] is True
    assert legality["declaration_warning"] is None


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


def test_verify_bundle_accepts_a_manifest_missing_study_repo_dirt_field(
    synthetic_world, bundled_repo, tmp_path
):
    """Backward compatibility (E0-prime flight protection): a manifest built
    BEFORE this fix never carried a study_repo_dirt field at all --
    verify_bundle must accept it exactly as before. The field is additive,
    never required."""

    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    manifest = _read_manifest(manifest_path)
    assert "study_repo_dirt" in manifest  # sanity: build_manifest DOES write it
    del manifest["study_repo_dirt"]
    write_json_artifact(manifest_path, manifest)
    bundle = verify_bundle(manifest_path)
    assert isinstance(bundle, VerifiedBundle)


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
# IMPORTANT fix (round-2 external-threat-model review): an outputs row's own
# carrier_lock_key/arm must BIND to the manifest's verified split
# carrier/arm, never merely be internally present.
#
# Demonstrated PoC: manifest split carrier earnings21-original, outputs rows
# rewritten to carrier_lock_key=earnings22-original (text and every row hash
# untouched, only the outer outputs artifact hash re-hashed) -- verify_bundle
# ACCEPTED this and finalize scored a "totally wrong" hypothesis against the
# OTHER carrier's references. The bundle is internally inconsistent; this is
# not the already-disclosed forged-bundle boundary (core.bundle's own
# ACCEPTED SCOPE BOUNDARY docstring), since nothing here requires forging an
# external anchor -- only rewriting a field verify_bundle never checked.
# ---------------------------------------------------------------------------


def test_verify_bundle_refuses_an_outputs_row_carrier_that_disagrees_with_the_split(
    synthetic_world, bundled_repo, tmp_path
):
    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    manifest = _read_manifest(manifest_path)
    assert manifest["split"]["carrier_lock_key"] == "earnings21-original"
    outputs_path = Path(manifest["outputs"]["path"])
    lines = _read_jsonl_lines(outputs_path)
    row = json.loads(lines[0])
    row["carrier_lock_key"] = "earnings22-original"
    lines[0] = json.dumps(row, ensure_ascii=False, sort_keys=True)
    _write_jsonl_lines(outputs_path, lines)
    _rehash_manifest_entry(manifest_path, "outputs")
    with pytest.raises(BundleError, match="carrier_lock_key"):
        verify_bundle(manifest_path)


def test_verify_bundle_refuses_an_outputs_row_arm_that_disagrees_with_the_manifest(
    synthetic_world, bundled_repo, tmp_path
):
    """Minor (same review round): arm is load-bearing for the protocol-hash
    re-derivation and must bind to the manifest's own arm, not merely be
    present on each row."""

    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    manifest = _read_manifest(manifest_path)
    outputs_path = Path(manifest["outputs"]["path"])
    lines = _read_jsonl_lines(outputs_path)
    row = json.loads(lines[0])
    row["arm"] = "some-other-arm"
    lines[0] = json.dumps(row, ensure_ascii=False, sort_keys=True)
    _write_jsonl_lines(outputs_path, lines)
    _rehash_manifest_entry(manifest_path, "outputs")
    with pytest.raises(BundleError, match="arm"):
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
# Minor hardening (round-2 external-threat-model review): a manifest artifact
# path must resolve under the manifest's OWN run directory -- before this,
# only manifest_path's own directory was ever checked against anything (a
# repo EXCLUSION, not artifact-path confinement), so a manifest could bind
# ANOTHER run's outputs (or an arbitrary filesystem file) as its own, as long
# as the attacker also supplied that file's correct hash.
# ---------------------------------------------------------------------------


def test_verify_bundle_refuses_an_outputs_path_outside_its_own_run_directory(
    synthetic_world, bundled_repo, tmp_path
):
    """Two independent, legitimately-produced runs; run A's manifest is then
    hand-edited (hash recomputed to genuinely match, exactly the attacker
    model this module's own docstring names) to point its own 'outputs' at
    run B's outputs.jsonl instead. Must be refused for path confinement, not
    silently accepted just because the hash happens to be internally
    consistent."""

    manifest_path_a, _, _, _ = _run_completed(
        synthetic_world, bundled_repo, tmp_path, run_id="SAEA-E-000-a", attempt_id="attempt-a",
        run_dir_name="run-a",
    )
    manifest_path_b, _, _, _ = _run_completed(
        synthetic_world, bundled_repo, tmp_path, run_id="SAEA-E-000-b", attempt_id="attempt-b",
        run_dir_name="run-b",
    )
    manifest_b = _read_manifest(manifest_path_b)
    other_run_outputs_path = Path(manifest_b["outputs"]["path"])
    other_run_outputs_hash = manifest_b["outputs"]["sha256"]

    manifest_a = _read_manifest(manifest_path_a)
    manifest_a["outputs"]["path"] = str(other_run_outputs_path)
    manifest_a["outputs"]["sha256"] = other_run_outputs_hash
    write_json_artifact(manifest_path_a, manifest_a)

    with pytest.raises(BundleError, match="does not resolve under this bundle's own run directory"):
        verify_bundle(manifest_path_a)


def test_verify_bundle_accepts_a_legitimate_manifest_whose_artifacts_stay_in_its_own_run_dir(
    synthetic_world, bundled_repo, tmp_path
):
    """Positive control for the confinement check above: an untouched,
    legitimately-produced manifest (every artifact where build_manifest
    always places it -- inside its own run directory) must still verify."""

    manifest_path, *_ = _run_completed(synthetic_world, bundled_repo, tmp_path)
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
    # IMPORTANT fix (round-2 external-threat-model review): a dev/discovery
    # bundle (the only kind Stage-2 can ever produce) must derive "no", not
    # the old hard-coded "yes".
    assert merged["consumed"] == "no"
    assert row.startswith("|") and row.endswith("|")


# ---------------------------------------------------------------------------
# Required probe 7: a legitimate synthetic run finalizes end to end.
# ---------------------------------------------------------------------------


def test_finalize_bundle_end_to_end_produces_a_ledger_row(synthetic_world, bundled_repo, tmp_path):
    _, repo_root = bundled_repo
    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    result = finalize_bundle(
        manifest_path, lock, synthetic_world.data_root, repo_root=repo_root,
        ledger_cells=_HUMAN_LEDGER_CELLS,
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
    # IMPORTANT fix (round-2 external-threat-model review): `consumed` means
    # CONFIRMATORY exposure was read, never "this bundle finalized" -- this
    # is a dev/discovery bundle (the only kind Stage-2 can ever produce), so
    # it must derive "no", not the old hard-coded "yes".
    assert ledger_cells["consumed"] == "no"
    assert ledger_cells["experiment_id"] == "SAEA-E-000"

    store = AttemptStore(synthetic_world.data_root / "attempts")
    assert store.handle(plan.run_id, plan.attempt_id).state() == "FINALIZED"

    # A second finalize on the identical manifest must now refuse -- the
    # attempt is no longer OPENED.
    with pytest.raises(BundleError, match="FINALIZED"):
        finalize_bundle(
            manifest_path, lock, synthetic_world.data_root, repo_root=repo_root,
            ledger_cells=_HUMAN_LEDGER_CELLS,
        )


def test_finalize_bundle_refuses_incomplete_ledger_before_scoring(
    synthetic_world, bundled_repo, tmp_path, monkeypatch
):
    from speech_aware_evidence_acquisition.core.bundle import finalize as finalizer

    _, repo_root = bundled_repo
    manifest_path, _composed_config, plan, lock = _run_completed(
        synthetic_world,
        bundled_repo,
        tmp_path,
        run_id="SAEA-E-000-ledger-preflight",
        attempt_id="attempt-ledger-preflight",
        run_dir_name="run-ledger-preflight",
    )

    def scorer_must_not_run(*_args, **_kwargs):
        raise AssertionError("scorer ran before ledger preflight")

    monkeypatch.setattr(finalizer, "score_bundle", scorer_must_not_run)

    with pytest.raises(ValueError, match="ledger row"):
        finalize_bundle(
            manifest_path,
            lock,
            synthetic_world.data_root,
            repo_root=repo_root,
            ledger_cells={},
        )

    assert _read_manifest(manifest_path)["scores"] is None
    store = AttemptStore(synthetic_world.data_root / "attempts")
    assert store.handle(plan.run_id, plan.attempt_id).state() == "OPENED"


def test_finalize_bundle_uploads_via_stubbed_mlflow(synthetic_world, bundled_repo, tmp_path, monkeypatch):
    import sys
    import types

    _, repo_root = bundled_repo
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
        manifest_path, lock, synthetic_world.data_root, repo_root=repo_root,
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
# IMPORTANT 3 fix-wave3 (round-3 external-threat-model review): a run_id (or
# attempt_id) that would steer a manifest/scores/ledger path OUTSIDE its own
# run directory -- via `/`, `\`, or a `..` traversal segment -- must be
# refused, even for a plan that was NEVER validated by
# contracts.ExecutionPlan.validate() (the demonstrated pre-gate reachability:
# core.driver.run_experiment_bundled's ABORTED-manifest path calls
# build_manifest with the SAME plan whenever run_experiment fails for ANY
# reason -- including core.tracing.TraceSink's OWN run_id check raising
# first, before the gate/adapter would ever validate the plan).
# ---------------------------------------------------------------------------


def test_build_manifest_refuses_a_run_id_that_would_escape_the_run_directory(
    synthetic_world, bundled_repo, tmp_path
):
    """The exact reviewer PoC: a plan constructed directly (bypassing
    ExecutionPlan.validate() entirely, exactly as an operator-supplied JSON
    file read by core.driver._cli_run would) with
    run_id='../../VICTIM/pwned' must never let build_manifest write a
    manifest outside its own run_dir."""

    lock, repo_root = bundled_repo
    ids, split_hash, split_role = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed()
    plan = ExecutionPlan(
        run_id="../../VICTIM/pwned",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="earnings21-original",
        split_role="discovery",
        split_identity_hash=split_hash,
        planned_model_calls=10,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=1000,
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
        attempt_id="attempt-evil",
    )
    verified_split = load_verified_split(repo_root, "discovery", lock, synthetic_world.data_root)
    run_dir = tmp_path / "run-confine"
    with pytest.raises(BundleError, match="would not land directly inside"):
        build_manifest(
            repo_root=repo_root, data_root=synthetic_world.data_root, composed=composed,
            plan=plan, verified_split=verified_split, session_receipt_path=None,
            run_dir=run_dir, status=STATUS_ABORTED, failure_reason="path-confinement probe",
        )
    # Nothing escaped: the sibling "VICTIM" directory the traversal targeted
    # was never created.
    assert not (tmp_path / "VICTIM").exists()


def test_build_manifest_still_works_for_a_legitimate_run_id(synthetic_world, bundled_repo, tmp_path):
    """Regression: the confinement fix must not disturb an ordinary,
    legitimate run_id -- build_manifest still writes directly inside its own
    run_dir."""

    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    assert manifest_path.is_file()
    assert manifest_path.parent == (tmp_path / "run").resolve()
    assert manifest_path.name == f"{plan.run_id}.run-manifest.json"


def test_confine_child_path_refuses_traversal_and_accepts_legitimate_filenames(tmp_path):
    """Direct unit coverage of the shared confinement helper itself."""

    parent = tmp_path / "run"
    parent.mkdir()
    with pytest.raises(BundleError, match="would not land directly inside"):
        _confine_child_path(parent, "../../VICTIM/pwned.run-manifest.json", "test path")
    with pytest.raises(BundleError, match="would not land directly inside"):
        _confine_child_path(parent, "sub/pwned.json", "test path")
    resolved = _confine_child_path(parent, "SAEA-E-000.run-manifest.json", "test path")
    assert resolved.parent == parent.resolve()


def test_confine_child_path_refuses_landing_inside_the_repo(tmp_path):
    with pytest.raises(BundleError, match="inside the study repository"):
        _confine_child_path(REPO_ROOT, "sneaky-confine-probe.run-manifest.json", "test path")


# ---------------------------------------------------------------------------
# IMPORTANT 4: saea-driver score --manifest is the authoritative path;
# --outputs is explicit, unverified, ad-hoc scoring only.
# ---------------------------------------------------------------------------


def test_cli_score_manifest_mode_is_verified_and_authoritative(
    synthetic_world, bundled_repo, tmp_path, capsys, monkeypatch
):
    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    from speech_aware_evidence_acquisition.core.driver import cli

    _, source_repo = bundled_repo
    monkeypatch.setattr(
        cli, "__file__",
        str(source_repo / "src/speech_aware_evidence_acquisition/core/driver/cli.py"),
    )
    monkeypatch.setenv("SPEECHRL_DATA_DIR", str(synthetic_world.data_root))
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.data.lock.umbrella_lock_path",
        lambda *a, **k: synthetic_world.lock_path,
    )
    # Score against the explicit synthetic source checkout so its recorded
    # Git commit is available. Reference identity has separate contract tests;
    # the real D1 receipt cannot contain these synthetic sample ids.
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.contracts.FrozenCoreGate.verify_reference_identity",
        lambda self, *a, **k: None,
    )
    exit_code = driver_main(["score", "--manifest", str(manifest_path), "--repo-root", str(source_repo)])
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
# CRITICAL fix (round-2 external-threat-model review): the D3 scoring-source
# freeze and this study's speech-only scope controls were reachable ONLY via
# the model-touch gate (contracts.assert_model_touch_allowed -> the
# `saea-driver run` process, which computes no scores) -- the processes that
# DO score (finalize_bundle, score_bundle, `saea-driver score --manifest`,
# `saea-driver finalize`) constructed no gate at all. Required probes: edit a
# frozen scoring source -> refuse, at EVERY one of those four entry points; a
# dirty tree -> refuse; unmodified tree + legitimate bundle -> still
# finalizes (already covered by the still-passing end-to-end tests above and
# the CLI-authoritative test below). The general-audio-carrier probe is
# exercised directly against score_bundle in tests/unit/test_scorers.py
# (finalize_bundle/both CLI paths inherit it for free, since all three call
# score_bundle -- not duplicated here).
# ===========================================================================


def test_finalize_bundle_refuses_when_a_frozen_scoring_source_is_edited(
    synthetic_world, bundled_repo, tmp_path
):
    _, repo_root = bundled_repo
    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    with _tamper_real_scoring_source():
        with pytest.raises(GateClosed, match="freeze drift"):
            finalize_bundle(
                manifest_path,
                lock,
                synthetic_world.data_root,
                repo_root=repo_root,
                ledger_cells=_HUMAN_LEDGER_CELLS,
            )
    # No lingering write from the refused attempt: it must still be OPENED,
    # not FINALIZED, and a legitimate finalize must still succeed afterward.
    store = AttemptStore(synthetic_world.data_root / "attempts")
    assert store.handle(plan.run_id, plan.attempt_id).state() == "OPENED"
    result = finalize_bundle(
        manifest_path, lock, synthetic_world.data_root, repo_root=repo_root,
        ledger_cells=_HUMAN_LEDGER_CELLS,
    )
    assert result.attempt_state == "FINALIZED"


def test_finalize_bundle_refuses_load_bearing_dirt_at_scoring_time(
    synthetic_world, bundled_repo, tmp_path
):
    """The load-bearing-surface requirement applies at SCORING time too, not
    merely at run time: the D3 freeze covers only scoring/*.py, but
    score_asr_outputs also imports data.references.reference_tokens, which
    lives outside that frozen package -- an uncommitted edit there would
    defeat the freeze check alone, so finalize_bundle must independently
    refuse before scoring anything. src/ is inside the surface, so that hole
    stays closed."""

    _, repo_root = bundled_repo
    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    (repo_root / "src").mkdir(parents=True, exist_ok=True)
    (repo_root / "src" / "edited-at-scoring-time.py").write_text("dirty", encoding="utf-8")
    with pytest.raises(BundleError, match="load-bearing"):
        finalize_bundle(
            manifest_path,
            lock,
            synthetic_world.data_root,
            repo_root=repo_root,
            ledger_cells=_HUMAN_LEDGER_CELLS,
        )


def test_finalize_bundle_completes_through_dirt_outside_the_load_bearing_surface(
    synthetic_world, bundled_repo, tmp_path
):
    """REGRESSION (2026-09-09), the incident's second half: a manifest that
    SEALED COMPLETED over a governance document must still FINALIZE.

    build_manifest(status=COMPLETED) has tolerated and recorded dirt outside
    the load-bearing surface since 2026-08-16, but the scoring entry gate
    finalize_bundle passes through kept refusing ANY dirt -- so the outputs
    were sealed and then permanently unfinalizable on the same tree, which is
    exactly the 2026-08-16 incident one step later. Both halves share one
    rule now."""

    _, repo_root = bundled_repo
    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    # Under docs/, which bundled_repo already tracks: a brand-new untracked
    # DIRECTORY collapses in `git status --porcelain` to its own entry, which
    # is not the shape a readiness note takes in the real study repo.
    (repo_root / "docs" / "2026-09-09-readiness-note.md").write_text(
        "a readiness note landed before finalize", encoding="utf-8"
    )
    result = finalize_bundle(
        manifest_path,
        lock,
        synthetic_world.data_root,
        repo_root=repo_root,
        ledger_cells=_HUMAN_LEDGER_CELLS,
    )
    assert result.attempt_state == "FINALIZED"


def test_cli_score_manifest_mode_refuses_when_a_frozen_scoring_source_is_edited(
    synthetic_world, bundled_repo, tmp_path, monkeypatch
):
    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    from speech_aware_evidence_acquisition.core.driver import cli

    _, source_repo = bundled_repo
    monkeypatch.setattr(
        cli, "__file__",
        str(source_repo / "src/speech_aware_evidence_acquisition/core/driver/cli.py"),
    )
    monkeypatch.setenv("SPEECHRL_DATA_DIR", str(synthetic_world.data_root))
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.data.lock.umbrella_lock_path",
        lambda *a, **k: synthetic_world.lock_path,
    )
    with _tamper_real_scoring_source():
        with pytest.raises(GateClosed, match="freeze drift"):
            driver_main(["score", "--manifest", str(manifest_path), "--repo-root", str(source_repo)])


def test_cli_finalize_refuses_when_a_frozen_scoring_source_is_edited(
    synthetic_world, bundled_repo, tmp_path, monkeypatch
):
    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    from speech_aware_evidence_acquisition.core.driver import cli

    _, source_repo = bundled_repo
    monkeypatch.setattr(
        cli, "__file__",
        str(source_repo / "src/speech_aware_evidence_acquisition/core/driver/cli.py"),
    )
    monkeypatch.setenv("SPEECHRL_DATA_DIR", str(synthetic_world.data_root))
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.data.lock.umbrella_lock_path",
        lambda *a, **k: synthetic_world.lock_path,
    )
    ledger_cells = tmp_path / "ledger-cells.json"
    ledger_cells.write_text(json.dumps(_HUMAN_LEDGER_CELLS), encoding="utf-8")
    with _tamper_real_scoring_source():
        with pytest.raises(GateClosed, match="freeze drift"):
            driver_main(
                [
                    "finalize",
                    "--manifest",
                    str(manifest_path),
                    "--repo-root",
                    str(source_repo),
                    "--ledger-cells",
                    str(ledger_cells),
                ]
            )
    store = AttemptStore(synthetic_world.data_root / "attempts")
    assert store.handle(plan.run_id, plan.attempt_id).state() == "OPENED"


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


# ===========================================================================
# External-threat-model review, finding I-1: verify_bundle never re-derived
# the manifest's OWN identity block (split.identity_hash, the plan block,
# protocol_hash) -- it treated split["ids"] and the plan dict as truth.
# Required probes (task brief), each proved ACCEPT -> REJECT (or, for the
# legitimate flow, REJECT-everywhere-else -> ACCEPT end to end):
#
# 1. the exact PoC: a legitimate COMPLETED dev bundle relabelled to the two
#    CONFIRMATORY sample ids, both hashes left at their dev values.
# 2. plan.execution_profile mutated to paper-scale-confirmatory.
# 3. plan.split_role mutated to confirmatory.
# 4. planned_model_calls inflated to 999999.
# 5. cost.calls_used zeroed (contradicts the verified outputs row count).
# 6. a legitimate bundle still verifies AND finalizes end to end.
# ===========================================================================


def test_verify_bundle_refuses_the_exact_i1_dev_to_confirmatory_relabel_poc(
    synthetic_world, bundled_repo, tmp_path
):
    """I-1 exact PoC: a legitimate COMPLETED dev-split bundle (10 real dev
    sample ids, earnings22-original) is relabelled to the two CONFIRMATORY
    sample ids (E22_IDS[10:12] in tests/unit/conftest.py -- disjoint from the
    dev subset10) while split.identity_hash AND protocol_hash are left
    UNTOUCHED at their original dev values. Before I-1, verify_bundle treated
    split["ids"] as truth and never re-derived split.identity_hash from it,
    so this passed verify_bundle, finalize_bundle, scoring, and FINALIZED the
    attempt outright. Must now REJECT -- and REJECT specifically on the
    split identity re-derivation, before outputs/trace are ever inspected."""

    lock, repo_root = bundled_repo
    ids, split_hash, split_role = load_split(repo_root, "dev", lock, synthetic_world.data_root)
    assert split_role == "dev"
    composed = _composed(carrier_lock_key="earnings22-original", split_name="dev")
    plan = _plan(
        split_hash, run_id="SAEA-E-000-i1poc", attempt_id="attempt-i1poc",
        carrier_lock_key="earnings22-original", split_role="dev",
        # The dev split carries 10 samples at 1200 audio seconds each (see
        # tests/unit/conftest.py's E22 metadata fixture) -- well over the
        # default _plan() helper's 1000-second discovery-sized budget.
        planned_speech_audio_seconds=20000,
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    manifest_path = run_experiment_bundled(
        composed, plan, _OpenGate(), lock, synthetic_world.data_root,
        tmp_path / "run-i1poc", _transport, repo_root=repo_root,
    )
    manifest = _read_manifest(manifest_path)
    assert manifest["status"] == STATUS_COMPLETED
    assert manifest["split"]["role"] == "dev"
    assert len(manifest["split"]["ids"]) == 10
    # The two CONFIRMATORY sample ids -- E22_IDS[10:12] -- relabelled in,
    # split.identity_hash and protocol_hash deliberately left at their
    # original dev values, exactly the reviewed attack.
    manifest["split"]["ids"] = ["50000010", "50000011"]
    manifest["split"]["count"] = 2
    write_json_artifact(manifest_path, manifest)
    with pytest.raises(BundleError, match="split.identity_hash"):
        verify_bundle(manifest_path)
    with pytest.raises(BundleError, match="split.identity_hash"):
        finalize_bundle(manifest_path, lock, synthetic_world.data_root)


def test_verify_bundle_refuses_plan_execution_profile_mutated_to_paper_scale_confirmatory(
    synthetic_world, bundled_repo, tmp_path
):
    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    manifest = _read_manifest(manifest_path)
    manifest["plan"]["execution_profile"] = "paper-scale-confirmatory"
    write_json_artifact(manifest_path, manifest)
    with pytest.raises(BundleError, match="paper-scale"):
        verify_bundle(manifest_path)


def test_verify_bundle_refuses_plan_split_role_mutated_to_confirmatory(
    synthetic_world, bundled_repo, tmp_path
):
    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    manifest = _read_manifest(manifest_path)
    manifest["plan"]["split_role"] = "confirmatory"
    write_json_artifact(manifest_path, manifest)
    with pytest.raises(BundleError, match="confirmatory"):
        verify_bundle(manifest_path)


def test_verify_bundle_accepts_planned_model_calls_far_beyond_the_former_first_slice_cap(
    synthetic_world, bundled_repo, tmp_path
):
    """Owner amendment 2026-08-06 (SAEA-OWNER-AMENDMENT-2026-08-06-BUDGET-CAPS)
    retired the first-slice numeric caps ``ExecutionPlan.validate()`` used to
    enforce transitively here; a manifest whose plan block declares a huge
    ``planned_model_calls`` (still a finite positive integer -- field-shape
    validation stays) no longer fails verify_bundle on that basis alone."""

    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    manifest = _read_manifest(manifest_path)
    manifest["plan"]["planned_model_calls"] = 999999
    write_json_artifact(manifest_path, manifest)
    bundle = verify_bundle(manifest_path)
    assert isinstance(bundle, VerifiedBundle)


def test_verify_bundle_refuses_cost_calls_used_zeroed_against_the_verified_outputs_count(
    synthetic_world, bundled_repo, tmp_path
):
    """cost.calls_used is derivable, for a COMPLETED bundle with verified
    outputs rows, as a lower bound: core.model.FrozenCoreAdapter.request
    durably records a call before any outputs row can exist. Zeroing it
    contradicts that derivable bound."""

    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    manifest = _read_manifest(manifest_path)
    assert manifest["cost"]["calls_used"] == 3
    manifest["cost"]["calls_used"] = 0
    write_json_artifact(manifest_path, manifest)
    with pytest.raises(BundleError, match="less than"):
        verify_bundle(manifest_path)


def test_verify_bundle_and_finalize_still_accept_a_legitimate_bundle_after_i1(
    synthetic_world, bundled_repo, tmp_path
):
    """Required probe 6: none of the I-1 hardening above may reject a
    genuinely legitimate bundle -- verify AND finalize must still both
    succeed end to end."""

    _, repo_root = bundled_repo
    manifest_path, composed, plan, lock = _run_completed(
        synthetic_world, bundled_repo, tmp_path, run_id="SAEA-E-000-i1legit",
        attempt_id="attempt-i1legit",
    )
    bundle = verify_bundle(manifest_path)
    assert isinstance(bundle, VerifiedBundle)
    result = finalize_bundle(
        manifest_path, lock, synthetic_world.data_root, repo_root=repo_root,
        ledger_cells=_HUMAN_LEDGER_CELLS,
    )
    assert result.attempt_state == "FINALIZED"


# ---------------------------------------------------------------------------
# Direct unit coverage of the new re-derivation logic itself (not just the
# ExecutionPlan.validate()-transitive refusals above).
# ---------------------------------------------------------------------------


def test_verify_bundle_refuses_a_split_count_that_disagrees_with_len_ids(
    synthetic_world, bundled_repo, tmp_path
):
    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    manifest = _read_manifest(manifest_path)
    manifest["split"]["count"] = manifest["split"]["count"] + 1
    write_json_artifact(manifest_path, manifest)
    with pytest.raises(BundleError, match="split.count"):
        verify_bundle(manifest_path)


def test_verify_bundle_refuses_a_config_hash_edited_without_recomputing_protocol_hash(
    synthetic_world, bundled_repo, tmp_path
):
    """config.config_hash is not covered by any outer artifact-hash check
    (it is not an {path, sha256} artifact entry) -- protocol_hash
    re-derivation is what catches a manifest whose config_hash was edited
    without a matching protocol_hash update."""

    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    manifest = _read_manifest(manifest_path)
    manifest["config"]["config_hash"] = "f" * 64
    write_json_artifact(manifest_path, manifest)
    with pytest.raises(BundleError, match="protocol_hash"):
        verify_bundle(manifest_path)


def test_verify_bundle_refuses_a_plan_attempt_id_mismatch(synthetic_world, bundled_repo, tmp_path):
    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    manifest = _read_manifest(manifest_path)
    manifest["plan"]["attempt_id"] = "some-other-attempt-id"
    write_json_artifact(manifest_path, manifest)
    with pytest.raises(BundleError, match="attempt_id"):
        verify_bundle(manifest_path)


# ---------------------------------------------------------------------------
# MINOR 2 (external-threat-model review round 3): three "machine-derived"
# ledger cells (study_commit, config.config_hash, scorers) were previously
# asserted, not derived -- any self-consistent-LOOKING value passed. These
# are now genuinely shape-checked (a residue remains -- see
# docs/owner-decisions-pending.md item 6 -- full re-derivation of
# config_hash/scorers against the composed config needs repo_root + real
# config-fragment files verify_bundle has no access to).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_commit",
    ["not-a-commit", "f" * 39, "g" * 40, "", "UNAVAILABLE:", 12345, None],
)
def test_verify_bundle_refuses_a_malshaped_study_commit(
    synthetic_world, bundled_repo, tmp_path, bad_commit
):
    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    manifest = _read_manifest(manifest_path)
    manifest["study_commit"] = bad_commit
    write_json_artifact(manifest_path, manifest)
    with pytest.raises(BundleError, match="study_commit"):
        verify_bundle(manifest_path)


def test_verify_bundle_accepts_a_wellshaped_unavailable_study_commit_on_an_aborted_manifest(
    synthetic_world, bundled_repo, tmp_path
):
    """Regression: the genuine ABORTED-only UNAVAILABLE:<reason> marker
    (build_manifest's own real output shape) must still verify."""

    lock, repo_root = bundled_repo
    ids, split_hash, split_role = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    (repo_root / "dirty-for-shape-probe.txt").write_text("dirty", encoding="utf-8")
    composed = _composed()
    plan = _plan(
        split_hash, run_id="SAEA-E-000-commitshape", attempt_id="attempt-commitshape",
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    verified_split = load_verified_split(repo_root, "discovery", lock, synthetic_world.data_root)
    manifest_path = build_manifest(
        repo_root=repo_root, data_root=synthetic_world.data_root, composed=composed,
        plan=plan, verified_split=verified_split, session_receipt_path=None,
        run_dir=tmp_path / "run-commitshape", status=STATUS_ABORTED,
        failure_reason="dirty-tree shape probe",
    )
    manifest = _read_manifest(manifest_path)
    assert manifest["study_commit"].startswith(UNAVAILABLE_COMMIT_PREFIX)
    bundle = verify_bundle(manifest_path)
    assert bundle.manifest["study_commit"] == manifest["study_commit"]


@pytest.mark.parametrize("bad_hash", ["not-a-hash", "f" * 63, "g" * 64, "", 12345, None])
def test_verify_bundle_refuses_a_malshaped_config_hash(
    synthetic_world, bundled_repo, tmp_path, bad_hash
):
    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    manifest = _read_manifest(manifest_path)
    manifest["config"]["config_hash"] = bad_hash
    write_json_artifact(manifest_path, manifest)
    with pytest.raises(BundleError, match="config_hash"):
        verify_bundle(manifest_path)


@pytest.mark.parametrize(
    "bad_scorers",
    [[], ["not-a-registered-scorer"], ["asr-wer", ""], "asr-wer", None, ["asr-wer", 7]],
)
def test_verify_bundle_refuses_malformed_or_unregistered_scorers(
    synthetic_world, bundled_repo, tmp_path, bad_scorers
):
    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    manifest = _read_manifest(manifest_path)
    manifest["scorers"] = bad_scorers
    write_json_artifact(manifest_path, manifest)
    with pytest.raises(BundleError, match="scorers"):
        verify_bundle(manifest_path)


def test_verify_bundle_accepts_legitimate_study_commit_config_hash_and_scorers(
    synthetic_world, bundled_repo, tmp_path
):
    """Regression: the new shape checks must not disturb an ordinary,
    legitimate manifest -- verify_bundle still accepts it end to end."""

    manifest_path, composed, plan, lock = _run_completed(synthetic_world, bundled_repo, tmp_path)
    bundle = verify_bundle(manifest_path)
    assert bundle.manifest["scorers"] == ["asr-wer"]
    assert len(bundle.manifest["study_commit"]) == 40
    assert len(bundle.manifest["config"]["config_hash"]) == 64


def _finalized_artifact_bundle(
    synthetic_world, bundled_repo, tmp_path, monkeypatch, *, run_dir_name="run-artifact"
):
    from speech_aware_evidence_acquisition.contracts import TraceRecord
    from speech_aware_evidence_acquisition.core.bundle import finalize as finalizer
    from speech_aware_evidence_acquisition.core.config import compose

    _, repo_root = bundled_repo
    manifest_path, _composed, plan, lock = _run_completed(
        synthetic_world,
        bundled_repo,
        tmp_path,
        run_id="SAEA-E-000-artifact",
        attempt_id="attempt-artifact",
        run_dir_name=run_dir_name,
    )
    manifest = _read_manifest(manifest_path)
    sample_ids = manifest["split"]["ids"]
    roster = {
        "schema": "saea-roster-receipt-v1",
        "roster_id": "SYNTHETIC-ARTIFACT-CONSTRUCTION",
        "carrier_lock_key": manifest["split"]["carrier_lock_key"],
        "split_role": "discovery",
        "roster_role": "construction",
        "seed": 1,
        "per_stratum": {"all": len(sample_ids)},
        "strata_counts": {"all": len(sample_ids)},
        "items": [{"sample_id": sid, "stratum": "all"} for sid in sample_ids],
        "excluded_count": 0,
        "split_identity_hash": manifest["split"]["identity_hash"],
    }
    roster_path = repo_root / "docs" / "rosters" / "train.json"
    roster_path.parent.mkdir(parents=True)
    roster_path.write_text(json.dumps(roster))
    binding = {
        "schema": "saea-artifact-result-binding-v1",
        "role": "training-feedback-proposal",
        "construction_roster": {
            "repo_relpath": "docs/rosters/train.json",
            "sha256": sha256_file(roster_path),
        },
    }
    values = {
        "arm": "speech-feature-query",
        "policy": "phase-direct-only-v1",
        "scorers": [],
        "result_kind": "artifact",
        "artifact_result": binding,
    }
    for kind, document in (
        ("model", values),
        ("dataset", {}),
        ("baseline", {}),
        ("experiment", {}),
    ):
        path = repo_root / "configs" / kind / f"{kind[0]}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document))
    composed = compose(repo_root, model="m", dataset="d", baseline="b", experiment="e")

    outputs_path = Path(manifest["outputs"]["path"])
    outputs = [
        json.loads(line) for line in outputs_path.read_text().splitlines() if line
    ]
    for row in outputs:
        row.update(
            arm="speech-feature-query",
            result_kind="artifact",
            artifact_role="training-feedback-proposal",
        )
    outputs_path.write_text("".join(json.dumps(row) + "\n" for row in outputs))
    manifest["outputs"]["sha256"] = sha256_file(outputs_path)

    trace_path = Path(manifest["raw_trace"]["path"])
    documents = [
        json.loads(line) for line in trace_path.read_text().splitlines() if line
    ]
    records = []
    for row in documents:
        if row["channel"] == "MODEL_REQUEST":
            row["payload"]["arm"] = "speech-feature-query"
        records.append(TraceRecord(row["channel"], row["record_id"], row["payload"]))
    trace_path.write_text("".join(record.serialize() + "\n" for record in records))
    trace_manifest_path = Path(manifest["trace_manifest"]["path"])
    trace_manifest_path.write_text(
        json.dumps(
            {"records": {record.record_id: record.content_hash() for record in records}}
        )
    )
    manifest["raw_trace"]["sha256"] = sha256_file(trace_path)
    manifest["trace_manifest"]["sha256"] = sha256_file(trace_manifest_path)

    manifest.update(
        arm="speech-feature-query",
        result_kind="artifact",
        artifact_result=binding,
        scorers=[],
    )
    manifest["config"]["config_hash"] = composed.config_hash
    new_protocol = protocol_hash(
        composed.config_hash, "speech-feature-query", manifest["split"]["identity_hash"]
    )
    manifest["protocol_hash"] = new_protocol
    manifest["plan"]["protocol_hash"] = new_protocol
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-q", "-m", "artifact fixture")

    monkeypatch.setattr(
        finalizer,
        "score_bundle",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("artifact finalization must not run task scorers")
        ),
    )
    dirty_source = repo_root / "src" / "dirty_artifact_finalizer.py"
    dirty_source.parent.mkdir(parents=True, exist_ok=True)
    dirty_source.write_text("dirty = True\n", encoding="utf-8")
    with pytest.raises(BundleError, match="load-bearing surface"):
        finalize_bundle(
            manifest_path,
            lock,
            synthetic_world.data_root,
            repo_root=repo_root,
            ledger_cells=_HUMAN_LEDGER_CELLS,
        )
    dirty_source.unlink()

    result = finalize_bundle(
        manifest_path,
        lock,
        synthetic_world.data_root,
        repo_root=repo_root,
        ledger_cells=_HUMAN_LEDGER_CELLS,
    )

    assert result.scores_path is None
    assert result.attempt_state == "FINALIZED"
    assert _read_manifest(manifest_path)["scores"] is None
    store = AttemptStore(synthetic_world.data_root / "attempts")
    assert store.handle(plan.run_id, plan.attempt_id).state() == "FINALIZED"

    return manifest_path, plan


def test_finalize_artifact_bundle_skips_task_scorers_and_finalizes(
    synthetic_world, bundled_repo, tmp_path, monkeypatch
):
    _finalized_artifact_bundle(synthetic_world, bundled_repo, tmp_path, monkeypatch)


def test_bundle_result_kind_keeps_task_answer_scorers_and_artifact_binding_strict(
    synthetic_world, bundled_repo, tmp_path
):
    manifest_path, _composed, _plan, _lock = _run_completed(
        synthetic_world,
        bundled_repo,
        tmp_path,
        run_id="SAEA-E-000-artifact-header",
        attempt_id="attempt-artifact-header",
        run_dir_name="run-artifact-header",
    )
    manifest = _read_manifest(manifest_path)
    manifest["scorers"] = []
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(BundleError, match="non-empty"):
        verify_bundle(manifest_path)

    manifest["result_kind"] = "artifact"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(BundleError, match="artifact_result"):
        verify_bundle(manifest_path)

    manifest["artifact_result"] = {
        "schema": "saea-artifact-result-binding-v1",
        "role": "training-feedback-proposal",
        "construction_roster": {
            "repo_relpath": "docs/rosters/train.json",
            "sha256": "a" * 64,
        },
    }
    manifest["scorers"] = ["asr-wer"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(BundleError, match="empty scorers"):
        verify_bundle(manifest_path)


def test_verify_bundle_accepts_and_revalidates_typed_hypothesis_artifact(
    synthetic_world, bundled_repo, tmp_path
):
    from speech_aware_evidence_acquisition.contracts import TraceRecord
    from speech_aware_evidence_acquisition.rails.candidate_contract_lookup import (
        canonical_sha256,
    )
    from speech_aware_evidence_acquisition.rails.slurp_intent_hypotheses import (
        canonicalize_slurp_intent_hypothesis_response,
    )

    manifest_path, _composed, _plan, _lock = _run_completed(
        synthetic_world,
        bundled_repo,
        tmp_path,
        run_id="SAEA-E-000-typed-artifact",
        attempt_id="attempt-typed-artifact",
        run_dir_name="run-typed-artifact",
    )
    catalog = {
        "schema": "saea-slurp-candidate-contract-catalog-v1",
        "projection_version": "saea-slurp-candidate-contract-projection-v1",
        "source_schema_id": "fixture",
        "source_schema_sha256": "a" * 64,
        "source_split": "train",
        "source_identity_sha256": "b" * 64,
        "source_utterance_count": 2,
        "retention": {"min_share": 0.02, "examples_per_type": 0},
        "profiles": [
            {"candidate_id": value, "utterances": 1, "slot_mentions": 0, "types": []}
            for value in ("alarm_set", "weather_query")
        ],
    }
    catalog_path = synthetic_world.data_root / "prepared" / "contracts" / "catalog.json"
    catalog_path.parent.mkdir(parents=True)
    catalog_path.write_text(json.dumps(catalog, sort_keys=True) + "\n")
    contract = {
        "id": "slurp-intent-hypotheses-v1",
        "max_candidates": 2,
        "source_catalog": {
            "data_relpath": "prepared/contracts/catalog.json",
            "sha256": sha256_file(catalog_path),
            "source_sha256": canonical_sha256(catalog),
        },
    }
    binding = {
        "schema": "saea-artifact-result-binding-v2",
        "role": "slurp-intent-hypotheses",
        "source_roster": {"repo_relpath": "docs/rosters/dev.json", "sha256": "c" * 64},
        "content_contract": contract,
    }
    raw = json.dumps(
        {
            "candidates": [
                {
                    "intent_id": "alarm_set",
                    "distinction": "Observed alarm request.",
                    "evidence_refs": [],
                    "unresolved_fields": [],
                }
            ]
        },
        sort_keys=True,
    )
    raw_sha = hashlib.sha256(raw.encode()).hexdigest()
    manifest = _read_manifest(manifest_path)
    outputs_path = Path(manifest["outputs"]["path"])
    rows = [json.loads(line) for line in outputs_path.read_text().splitlines() if line]
    by_request = {}
    for row in rows:
        canonical = canonicalize_slurp_intent_hypothesis_response(
            raw,
            sample_id=row["sample_id"],
            legal_intent_ids=("alarm_set", "weather_query"),
            max_candidates=2,
        )
        row.update(
            text=raw,
            response_text_sha256=raw_sha,
            result_kind="artifact",
            artifact_role="slurp-intent-hypotheses",
            artifact_content=canonical,
            artifact_content_sha256=hashlib.sha256(canonical.encode()).hexdigest(),
            artifact_source_sha256=contract["source_catalog"]["source_sha256"],
        )
        by_request[row["request_id"]] = row
    outputs_path.write_text("".join(json.dumps(row) + "\n" for row in rows))

    trace_path = Path(manifest["raw_trace"]["path"])
    records = []
    for line in trace_path.read_text().splitlines():
        document = json.loads(line)
        if document["record_id"].endswith("/response"):
            request_id = document["record_id"][: -len("/response")]
            if request_id in by_request:
                document["payload"]["text"] = raw
                document["payload"]["response_text_sha256"] = raw_sha
        records.append(
            TraceRecord(document["channel"], document["record_id"], document["payload"])
        )
    trace_path.write_text("".join(record.serialize() + "\n" for record in records))
    trace_manifest_path = Path(manifest["trace_manifest"]["path"])
    trace_manifest_path.write_text(
        json.dumps({"records": {r.record_id: r.content_hash() for r in records}})
    )
    manifest.update(
        result_kind="artifact",
        artifact_result=binding,
        artifact_content_source={"path": str(catalog_path), "sha256": sha256_file(catalog_path)},
        scorers=[],
    )
    for key in ("outputs", "raw_trace", "trace_manifest"):
        manifest[key]["sha256"] = sha256_file(Path(manifest[key]["path"]))
    manifest_path.write_text(json.dumps(manifest))

    verified = verify_bundle(manifest_path)
    assert all(row["text"] == raw for row in verified.outputs_rows)
    assert all(row["artifact_content"] != raw for row in verified.outputs_rows)

    rows[0]["artifact_content"] = rows[0]["artifact_content"].replace("alarm_set", "weather_query")
    outputs_path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    manifest["outputs"]["sha256"] = sha256_file(outputs_path)
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(BundleError, match="canonical content"):
        verify_bundle(manifest_path)


def test_verify_bundle_resolves_typed_train_proposals_through_content_registry(
    synthetic_world, bundled_repo, tmp_path
):
    from speech_aware_evidence_acquisition.contracts import TraceRecord
    from test_training_feedback_artifacts import (
        _contract,
        _prepared_contexts,
        _response,
    )

    manifest_path, _composed, _plan, _lock = _run_completed(
        synthetic_world,
        bundled_repo,
        tmp_path,
        run_id="SAEA-E-000-typed-train-proposal",
        attempt_id="attempt-typed-train-proposal",
        run_dir_name="run-typed-train-proposal",
    )
    manifest = _read_manifest(manifest_path)
    outputs_path = Path(manifest["outputs"]["path"])
    rows = [json.loads(line) for line in outputs_path.read_text().splitlines() if line]
    prepared_path = synthetic_world.data_root / "prepared" / "proposal-contexts.json"
    prepared, prepared_sha = _prepared_contexts(
        prepared_path,
        {row["sample_id"]: ("option-1", "option-2") for row in rows},
    )
    contract = _contract(
        "prepared/proposal-contexts.json",
        prepared_sha,
        prepared["output_sha256"],
        applicability={
            "allowed_task_ids": [manifest["split"]["carrier_lock_key"]],
            "allowed_roles": ["solver"],
            "allowed_component_tags": ["org", "use"],
        },
    )
    binding = {
        "schema": "saea-artifact-result-binding-v3",
        "role": "training-feedback-proposal",
        "construction_roster": {
            "repo_relpath": "docs/rosters/train.json",
            "sha256": "c" * 64,
        },
        "content_contract": contract,
    }
    raw = _response()
    from speech_aware_evidence_acquisition.rails.training_feedback_artifacts import (
        build_training_feedback_artifact_validator,
    )

    validator = build_training_feedback_artifact_validator(
        contract, data_root=synthetic_world.data_root
    )
    by_request = {}
    for row in rows:
        proposal = json.loads(raw)
        proposal["proposals"][0]["applicability"]["task_ids"] = [
            manifest["split"]["carrier_lock_key"]
        ]
        row_raw = json.dumps(proposal)
        row_raw_sha = hashlib.sha256(row_raw.encode()).hexdigest()
        canonical = validator.canonicalize(row_raw, sample_id=row["sample_id"])
        row.update(
            text=row_raw,
            response_text_sha256=row_raw_sha,
            result_kind="artifact",
            artifact_role="training-feedback-proposal",
            artifact_content=canonical,
            artifact_content_sha256=hashlib.sha256(canonical.encode()).hexdigest(),
            artifact_source_sha256=prepared_sha,
        )
        by_request[row["request_id"]] = row
    outputs_path.write_text("".join(json.dumps(row) + "\n" for row in rows))

    trace_path = Path(manifest["raw_trace"]["path"])
    records = []
    for line in trace_path.read_text().splitlines():
        document = json.loads(line)
        if document["record_id"].endswith("/response"):
            request_id = document["record_id"][: -len("/response")]
            if request_id in by_request:
                output = by_request[request_id]
                document["payload"]["text"] = output["text"]
                document["payload"]["response_text_sha256"] = output[
                    "response_text_sha256"
                ]
        records.append(
            TraceRecord(document["channel"], document["record_id"], document["payload"])
        )
    trace_path.write_text("".join(record.serialize() + "\n" for record in records))
    trace_manifest_path = Path(manifest["trace_manifest"]["path"])
    trace_manifest_path.write_text(
        json.dumps({"records": {r.record_id: r.content_hash() for r in records}})
    )
    manifest.update(
        result_kind="artifact",
        artifact_result=binding,
        artifact_content_source={
            "path": str(prepared_path),
            "sha256": prepared_sha,
        },
        scorers=[],
    )
    for key in ("outputs", "raw_trace", "trace_manifest"):
        manifest[key]["sha256"] = sha256_file(Path(manifest[key]["path"]))
    manifest_path.write_text(json.dumps(manifest))

    verified = verify_bundle(manifest_path)
    assert all(row["text"] != row["artifact_content"] for row in verified.outputs_rows)
    assert all(
        json.loads(row["artifact_content"])["status"] == "provisional"
        for row in verified.outputs_rows
    )
    fresh = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from speech_aware_evidence_acquisition.core.bundle import verify_bundle; "
                "import sys; verify_bundle(sys.argv[1])"
            ),
            str(manifest_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert fresh.returncode == 0, fresh.stderr

    rows[0]["artifact_content"] = rows[0]["artifact_content"].replace(
        "option-2", "option-9"
    )
    outputs_path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    manifest["outputs"]["sha256"] = sha256_file(outputs_path)
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(BundleError, match="canonical content"):
        verify_bundle(manifest_path)


def test_artifact_finalizer_rejects_syntactic_relabel_without_frozen_binding(
    synthetic_world, bundled_repo, tmp_path, monkeypatch
):
    from speech_aware_evidence_acquisition.core.bundle import finalize as finalizer

    _, repo_root = bundled_repo
    manifest_path, _composed, _plan, lock = _run_completed(
        synthetic_world,
        bundled_repo,
        tmp_path,
        run_id="SAEA-E-000-fake-artifact",
        attempt_id="attempt-fake-artifact",
        run_dir_name="run-fake-artifact",
    )
    manifest = _read_manifest(manifest_path)
    manifest.update(
        result_kind="artifact",
        artifact_result={
            "schema": "saea-artifact-result-binding-v1",
            "role": "training-feedback-proposal",
            "construction_roster": {
                "repo_relpath": "docs/rosters/missing.json",
                "sha256": "a" * 64,
            },
        },
        scorers=[],
    )
    manifest_path.write_text(json.dumps(manifest))
    monkeypatch.setattr(
        finalizer,
        "score_bundle",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("scorer must remain behind artifact binding validation")
        ),
    )
    with pytest.raises(BundleError, match="artifact finalization binding"):
        finalize_bundle(
            manifest_path,
            lock,
            synthetic_world.data_root,
            repo_root=repo_root,
            ledger_cells=_HUMAN_LEDGER_CELLS,
        )


# ---------------------------------------------------------------------------
# E10 (owner decision 22, 2026-09-18): resume-recovery custody across a
# predecessor attempt's trace. A merged manifest declares the aborted attempt
# whose COMPLETE rows it kept; verify_bundle re-derives that declaration from
# the bytes on disk and holds every kept row against THAT trace, byte for
# byte, exactly as I7 holds every other row against this attempt's own.
# ---------------------------------------------------------------------------


def _kept_ids_sha256(sample_ids) -> str:
    return hashlib.sha256(
        json.dumps(sorted(sample_ids), ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _split_bundle_for_resume(
    manifest_path: Path, tmp_path: Path, *, kept: tuple[str, ...], also_recovery=(),
) -> Path:
    """Turn a legitimate COMPLETED bundle into a resumed one, in place.

    Every record of a ``kept`` sample moves out of this attempt's trace and
    into a predecessor attempt's trace file; the outputs rows are untouched,
    which is the point -- a kept row is the SAME row, verified against the
    other trace. ``also_recovery`` names samples whose records are left in
    BOTH traces, the defect the custody rule must refuse.
    """

    manifest = _read_manifest(manifest_path)
    run_id = manifest["run_id"]
    trace_path = Path(manifest["raw_trace"]["path"])
    records = [json.loads(line) for line in _read_jsonl_lines(trace_path)]
    request_sample = {
        record["record_id"][: -len("/request")]: record["payload"]["payload"]["sample_id"]
        for record in records
        if record["record_id"].endswith("/request")
        and isinstance(record["payload"].get("payload"), dict)
    }

    def owner(record) -> str | None:
        head = record["record_id"].split("/")[0]
        return request_sample.get(head)

    predecessor_dir = tmp_path / "predecessor-attempt"
    predecessor_dir.mkdir(parents=True, exist_ok=True)
    predecessor_path = predecessor_dir / f"{run_id}.trace.jsonl"
    moved = [record for record in records if owner(record) in kept]
    stayed = [
        record
        for record in records
        if owner(record) not in kept or owner(record) in set(also_recovery)
    ]
    _write_jsonl_lines(
        predecessor_path,
        [json.dumps(record, ensure_ascii=False, sort_keys=True) for record in moved],
    )
    _write_jsonl_lines(
        trace_path,
        [json.dumps(record, ensure_ascii=False, sort_keys=True) for record in stayed],
    )
    trace_manifest_path = Path(manifest["trace_manifest"]["path"])
    trace_manifest = _read_manifest(trace_manifest_path)
    trace_manifest["records"] = {
        record["record_id"]: trace_manifest["records"][record["record_id"]]
        for record in stayed
    }
    write_json_artifact(trace_manifest_path, trace_manifest)

    manifest["predecessor_attempt"] = {
        "schema": "saea-resume-predecessor-attempt-v1",
        "run_id": run_id,
        "attempt_id": "attempt-bundle-aborted",
        "trace_path": str(predecessor_path),
        "trace_sha256": sha256_file(predecessor_path),
        "kept_sample_ids": sorted(kept),
        "kept_sample_ids_sha256": _kept_ids_sha256(kept),
        "counts": {
            "kept": len(kept),
            "flown": len(manifest["split"]["ids"]) - len(kept),
            "partial": 0,
        },
    }
    write_json_artifact(manifest_path, manifest)
    _rehash_manifest_entry(manifest_path, "raw_trace")
    _rehash_manifest_entry(manifest_path, "trace_manifest")
    return predecessor_path


def test_verify_bundle_accepts_a_resumed_bundle_whose_kept_rows_live_in_the_predecessor(
    synthetic_world, bundled_repo, tmp_path
):
    manifest_path, _composed, _plan, _lock = _run_completed(
        synthetic_world, bundled_repo, tmp_path
    )
    _split_bundle_for_resume(manifest_path, tmp_path, kept=("4000001",))

    verified = verify_bundle(manifest_path)

    # The kept row is still sealed, still one row per split id, and its own
    # request record no longer exists in THIS attempt's trace at all.
    assert {row["sample_id"] for row in verified.outputs_rows} == set(
        _read_manifest(manifest_path)["split"]["ids"]
    )
    kept_row = next(
        row for row in verified.outputs_rows if row["sample_id"] == "4000001"
    )
    assert f"{kept_row['request_id']}/request" not in verified.trace_records


def test_verify_bundle_refuses_a_predecessor_trace_whose_hash_does_not_match(
    synthetic_world, bundled_repo, tmp_path
):
    manifest_path, _composed, _plan, _lock = _run_completed(
        synthetic_world, bundled_repo, tmp_path
    )
    _split_bundle_for_resume(manifest_path, tmp_path, kept=("4000001",))
    manifest = _read_manifest(manifest_path)
    manifest["predecessor_attempt"]["trace_sha256"] = "0" * 64
    write_json_artifact(manifest_path, manifest)

    with pytest.raises(BundleError, match="hashes to"):
        verify_bundle(manifest_path)


def test_verify_bundle_refuses_a_predecessor_trace_edited_after_it_was_declared(
    synthetic_world, bundled_repo, tmp_path
):
    """The other direction of the same pin: the declaration is untouched and
    the trace file itself is edited."""

    manifest_path, _composed, _plan, _lock = _run_completed(
        synthetic_world, bundled_repo, tmp_path
    )
    predecessor_path = _split_bundle_for_resume(manifest_path, tmp_path, kept=("4000001",))
    lines = _read_jsonl_lines(predecessor_path)
    _write_jsonl_lines(predecessor_path, lines[:-1])

    with pytest.raises(BundleError, match="changed after it was declared"):
        verify_bundle(manifest_path)


def test_verify_bundle_refuses_a_tampered_kept_row_list(
    synthetic_world, bundled_repo, tmp_path
):
    manifest_path, _composed, _plan, _lock = _run_completed(
        synthetic_world, bundled_repo, tmp_path
    )
    _split_bundle_for_resume(manifest_path, tmp_path, kept=("4000001",))
    manifest = _read_manifest(manifest_path)
    # A row quietly added to the kept list (its hash left stale) -- the exact
    # shape a selection would take.
    manifest["predecessor_attempt"]["kept_sample_ids"] = ["4000001", "4000002"]
    manifest["predecessor_attempt"]["counts"]["kept"] = 2
    write_json_artifact(manifest_path, manifest)

    with pytest.raises(BundleError, match="kept_sample_ids_sha256"):
        verify_bundle(manifest_path)


def test_verify_bundle_refuses_a_kept_row_list_rehashed_to_match_its_edit(
    synthetic_world, bundled_repo, tmp_path
):
    """Recomputing the hash does not help: the added row's contacts are in
    THIS attempt's trace, so declaring it kept claims two custodies for one
    row -- which is exactly what a selection would need."""

    manifest_path, _composed, _plan, _lock = _run_completed(
        synthetic_world, bundled_repo, tmp_path
    )
    _split_bundle_for_resume(manifest_path, tmp_path, kept=("4000001",))
    manifest = _read_manifest(manifest_path)
    kept = ["4000001", "4000002"]
    manifest["predecessor_attempt"]["kept_sample_ids"] = kept
    manifest["predecessor_attempt"]["kept_sample_ids_sha256"] = _kept_ids_sha256(kept)
    manifest["predecessor_attempt"]["counts"]["kept"] = 2
    write_json_artifact(manifest_path, manifest)

    with pytest.raises(BundleError, match="never both"):
        verify_bundle(manifest_path)


def test_verify_bundle_refuses_a_kept_row_absent_from_the_predecessor_trace(
    synthetic_world, bundled_repo, tmp_path
):
    """A row claimed as kept whose contacts are in neither trace: it was
    flown by nobody, so nothing can verify it."""

    manifest_path, _composed, _plan, _lock = _run_completed(
        synthetic_world, bundled_repo, tmp_path
    )
    predecessor_path = _split_bundle_for_resume(
        manifest_path, tmp_path, kept=("4000001", "4000003"),
    )
    keep = [
        line
        for line in _read_jsonl_lines(predecessor_path)
        if "4000003" not in line
    ]
    _write_jsonl_lines(predecessor_path, keep)
    manifest = _read_manifest(manifest_path)
    # Re-pin the trace hash so the declaration stays self-consistent and the
    # refusal below is about custody, not about the pin.
    manifest["predecessor_attempt"]["trace_sha256"] = sha256_file(predecessor_path)
    write_json_artifact(manifest_path, manifest)

    with pytest.raises(BundleError, match="no request in the predecessor trace"):
        verify_bundle(manifest_path)


def test_verify_bundle_refuses_a_kept_row_that_was_also_flown_again(
    synthetic_world, bundled_repo, tmp_path
):
    manifest_path, _composed, _plan, _lock = _run_completed(
        synthetic_world, bundled_repo, tmp_path
    )
    _split_bundle_for_resume(
        manifest_path, tmp_path, kept=("4000001",), also_recovery=("4000001",),
    )

    with pytest.raises(BundleError, match="never both"):
        verify_bundle(manifest_path)


def test_verify_bundle_refuses_a_predecessor_block_that_is_not_this_run(
    synthetic_world, bundled_repo, tmp_path
):
    manifest_path, _composed, _plan, _lock = _run_completed(
        synthetic_world, bundled_repo, tmp_path
    )
    _split_bundle_for_resume(manifest_path, tmp_path, kept=("4000001",))
    manifest = _read_manifest(manifest_path)
    manifest["predecessor_attempt"]["run_id"] = "SAEA-E-000-some-other-run"
    write_json_artifact(manifest_path, manifest)

    with pytest.raises(BundleError, match="must be this manifest's own run id"):
        verify_bundle(manifest_path)


def test_verify_bundle_refuses_a_predecessor_attempt_that_is_this_attempt(
    synthetic_world, bundled_repo, tmp_path
):
    manifest_path, _composed, _plan, _lock = _run_completed(
        synthetic_world, bundled_repo, tmp_path
    )
    _split_bundle_for_resume(manifest_path, tmp_path, kept=("4000001",))
    manifest = _read_manifest(manifest_path)
    manifest["predecessor_attempt"]["attempt_id"] = manifest["attempt"]["attempt_id"]
    write_json_artifact(manifest_path, manifest)

    with pytest.raises(BundleError, match="different, non-empty attempt"):
        verify_bundle(manifest_path)


def test_build_manifest_refuses_a_predecessor_declaration_on_an_aborted_manifest(
    synthetic_world, bundled_repo, tmp_path
):
    """Only a COMPLETED manifest keeps rows: an ABORTED attempt sealed none,
    so a predecessor declaration on one is a defect, refused before the
    manifest is written."""

    lock, repo_root = bundled_repo
    _ids, split_hash, _role = load_split(
        repo_root, "discovery", lock, synthetic_world.data_root
    )
    with pytest.raises(BundleError, match="only a COMPLETED manifest"):
        build_manifest(
            repo_root=repo_root,
            data_root=synthetic_world.data_root,
            composed=_composed(),
            plan=_plan(split_hash),
            verified_split=load_verified_split(
                repo_root, "discovery", lock, synthetic_world.data_root
            ),
            session_receipt_path=None,
            run_dir=tmp_path / "manifest-run",
            status=STATUS_ABORTED,
            failure_reason="probe",
            predecessor_attempt={"schema": "saea-resume-predecessor-attempt-v1"},
        )


# ---------------------------------------------------------------------------
# E10d (2026-09-29): MULTI-predecessor, seal-only resume completion. Each
# kept row binds to exactly ONE of the N declared predecessor traces (I7r
# generalized); this is the bundle-level counterpart to
# core.flight.resume.MergedPredecessors's own writing-side disjointness check.
# ---------------------------------------------------------------------------


def _split_bundle_for_multi_resume(
    manifest_path: Path, tmp_path: Path, *, kept_by_attempt: dict,
) -> dict:
    """Turn a legitimate COMPLETED bundle into one resumed from MULTIPLE
    predecessor attempts, in place. Every record of a sample kept by SOME
    predecessor moves out of this attempt's trace into THAT predecessor's own
    trace file. ``kept_by_attempt`` maps attempt_id -> a tuple of sample ids
    it alone kept (must be pairwise disjoint across attempts -- this helper
    builds the legitimate case; an overlap is exercised by hand-editing the
    manifest afterward, not by this helper)."""

    manifest = _read_manifest(manifest_path)
    run_id = manifest["run_id"]
    trace_path = Path(manifest["raw_trace"]["path"])
    records = [json.loads(line) for line in _read_jsonl_lines(trace_path)]
    request_sample = {
        record["record_id"][: -len("/request")]: record["payload"]["payload"]["sample_id"]
        for record in records
        if record["record_id"].endswith("/request")
        and isinstance(record["payload"].get("payload"), dict)
    }

    def owner(record) -> str | None:
        head = record["record_id"].split("/")[0]
        return request_sample.get(head)

    all_kept = {
        sample_id for ids in kept_by_attempt.values() for sample_id in ids
    }
    assert sum(len(ids) for ids in kept_by_attempt.values()) == len(all_kept), (
        "test setup error: kept_by_attempt must be pairwise disjoint"
    )

    predecessor_paths: dict[str, Path] = {}
    blocks = []
    for attempt_id, kept in kept_by_attempt.items():
        predecessor_dir = tmp_path / f"predecessor-{attempt_id}"
        predecessor_dir.mkdir(parents=True, exist_ok=True)
        predecessor_path = predecessor_dir / f"{run_id}.trace.jsonl"
        moved = [record for record in records if owner(record) in kept]
        _write_jsonl_lines(
            predecessor_path,
            [json.dumps(record, ensure_ascii=False, sort_keys=True) for record in moved],
        )
        predecessor_paths[attempt_id] = predecessor_path
        blocks.append({
            "schema": "saea-resume-predecessor-attempt-v1",
            "run_id": run_id,
            "attempt_id": attempt_id,
            "trace_path": str(predecessor_path),
            "trace_sha256": sha256_file(predecessor_path),
            "kept_sample_ids": sorted(kept),
            "kept_sample_ids_sha256": _kept_ids_sha256(kept),
            "counts": {
                "kept": len(kept),
                "flown": len(manifest["split"]["ids"]) - len(all_kept),
                "partial": 0,
            },
        })

    stayed = [record for record in records if owner(record) not in all_kept]
    _write_jsonl_lines(
        trace_path,
        [json.dumps(record, ensure_ascii=False, sort_keys=True) for record in stayed],
    )
    trace_manifest_path = Path(manifest["trace_manifest"]["path"])
    trace_manifest = _read_manifest(trace_manifest_path)
    trace_manifest["records"] = {
        record["record_id"]: trace_manifest["records"][record["record_id"]]
        for record in stayed
    }
    write_json_artifact(trace_manifest_path, trace_manifest)

    manifest["predecessor_attempts"] = blocks
    write_json_artifact(manifest_path, manifest)
    _rehash_manifest_entry(manifest_path, "raw_trace")
    _rehash_manifest_entry(manifest_path, "trace_manifest")
    return predecessor_paths


def test_verify_bundle_accepts_a_bundle_resumed_from_two_predecessors(
    synthetic_world, bundled_repo, tmp_path
):
    manifest_path, _composed, _plan, _lock = _run_completed(
        synthetic_world, bundled_repo, tmp_path
    )
    _split_bundle_for_multi_resume(
        manifest_path, tmp_path,
        kept_by_attempt={
            "attempt-bundle-aborted-a": ("4000001",),
            "attempt-bundle-aborted-b": ("4000002",),
        },
    )

    verified = verify_bundle(manifest_path)

    assert {row["sample_id"] for row in verified.outputs_rows} == set(
        _read_manifest(manifest_path)["split"]["ids"]
    )
    for sample_id in ("4000001", "4000002"):
        kept_row = next(
            row for row in verified.outputs_rows if row["sample_id"] == sample_id
        )
        assert f"{kept_row['request_id']}/request" not in verified.trace_records


def test_verify_bundle_refuses_two_predecessor_blocks_claiming_the_same_sample(
    synthetic_world, bundled_repo, tmp_path
):
    """Cross-block disjointness, checked independently of whatever built the
    manifest -- the writing-side check (MergedPredecessors) is not trusted."""

    manifest_path, _composed, _plan, _lock = _run_completed(
        synthetic_world, bundled_repo, tmp_path
    )
    _split_bundle_for_multi_resume(
        manifest_path, tmp_path,
        kept_by_attempt={
            "attempt-bundle-aborted-a": ("4000001",),
            "attempt-bundle-aborted-b": ("4000002",),
        },
    )
    manifest = _read_manifest(manifest_path)
    # Claim 4000001 a second time from the OTHER predecessor's block, hash
    # re-derived so the tamper is not caught by the cheaper hash check first.
    second = manifest["predecessor_attempts"][1]
    kept = sorted(set(second["kept_sample_ids"]) | {"4000001"})
    second["kept_sample_ids"] = kept
    second["kept_sample_ids_sha256"] = _kept_ids_sha256(kept)
    second["counts"]["kept"] = len(kept)
    write_json_artifact(manifest_path, manifest)

    with pytest.raises(BundleError, match="in two predecessor attempts"):
        verify_bundle(manifest_path)


def test_verify_bundle_refuses_a_multi_predecessor_trace_hash_mismatch(
    synthetic_world, bundled_repo, tmp_path
):
    manifest_path, _composed, _plan, _lock = _run_completed(
        synthetic_world, bundled_repo, tmp_path
    )
    _split_bundle_for_multi_resume(
        manifest_path, tmp_path,
        kept_by_attempt={
            "attempt-bundle-aborted-a": ("4000001",),
            "attempt-bundle-aborted-b": ("4000002",),
        },
    )
    manifest = _read_manifest(manifest_path)
    manifest["predecessor_attempts"][0]["trace_sha256"] = "0" * 64
    write_json_artifact(manifest_path, manifest)

    with pytest.raises(BundleError, match="hashes to"):
        verify_bundle(manifest_path)


def test_verify_bundle_refuses_a_row_relabelled_to_a_predecessor_that_never_flew_it(
    synthetic_world, bundled_repo, tmp_path
):
    """A kept row bound (by manifest edit) to the WRONG predecessor's trace --
    that predecessor's own trace has no request for it -- must refuse, never
    silently verify against whichever trace happens to be handed to it."""

    manifest_path, _composed, _plan, _lock = _run_completed(
        synthetic_world, bundled_repo, tmp_path
    )
    # B keeps two samples so removing one from it later still leaves it
    # non-empty (a predecessor_attempt block may never declare zero kept ids).
    _split_bundle_for_multi_resume(
        manifest_path, tmp_path,
        kept_by_attempt={
            "attempt-bundle-aborted-a": ("4000001",),
            "attempt-bundle-aborted-b": ("4000002", "4000003"),
        },
    )
    manifest = _read_manifest(manifest_path)
    first, second = manifest["predecessor_attempts"]
    # Re-declare predecessor A as keeping 4000003 too -- A's OWN trace file
    # was never given 4000003's records (only B's was, at trace-construction
    # time above), so A's claim cannot be verified against A's own trace.
    kept = sorted(set(first["kept_sample_ids"]) | {"4000003"})
    first["kept_sample_ids"] = kept
    first["kept_sample_ids_sha256"] = _kept_ids_sha256(kept)
    first["counts"]["kept"] = len(kept)
    # Drop 4000003 from B's declared block so the two blocks stay disjoint
    # (the cross-block disjointness check above would otherwise catch this a
    # different, less specific way than the one this test isolates).
    remaining = sorted(set(second["kept_sample_ids"]) - {"4000003"})
    second["kept_sample_ids"] = remaining
    second["kept_sample_ids_sha256"] = _kept_ids_sha256(remaining)
    second["counts"]["kept"] = len(remaining)
    write_json_artifact(manifest_path, manifest)

    with pytest.raises(BundleError, match="no request in the predecessor trace"):
        verify_bundle(manifest_path)


def test_verify_bundle_refuses_predecessor_attempt_and_predecessor_attempts_together(
    synthetic_world, bundled_repo, tmp_path
):
    manifest_path, _composed, _plan, _lock = _run_completed(
        synthetic_world, bundled_repo, tmp_path
    )
    predecessor_path = _split_bundle_for_resume(manifest_path, tmp_path, kept=("4000001",))
    manifest = _read_manifest(manifest_path)
    manifest["predecessor_attempts"] = [dict(manifest["predecessor_attempt"])]
    manifest["predecessor_attempts"][0]["attempt_id"] = "attempt-bundle-aborted-2"
    manifest["predecessor_attempts"][0]["trace_path"] = str(predecessor_path)
    write_json_artifact(manifest_path, manifest)

    with pytest.raises(BundleError, match="declares both"):
        verify_bundle(manifest_path)


def test_build_manifest_refuses_predecessor_attempt_and_predecessor_attempts_together(
    synthetic_world, bundled_repo, tmp_path
):
    lock, repo_root = bundled_repo
    _ids, split_hash, _role = load_split(
        repo_root, "discovery", lock, synthetic_world.data_root
    )
    with pytest.raises(BundleError, match="never both"):
        build_manifest(
            repo_root=repo_root,
            data_root=synthetic_world.data_root,
            composed=_composed(),
            plan=_plan(split_hash),
            verified_split=load_verified_split(
                repo_root, "discovery", lock, synthetic_world.data_root
            ),
            session_receipt_path=None,
            run_dir=tmp_path / "manifest-run",
            status=STATUS_ABORTED,
            failure_reason="probe",
            predecessor_attempt={"schema": "saea-resume-predecessor-attempt-v1"},
            predecessor_attempts=[{"schema": "saea-resume-predecessor-attempt-v1"}],
        )


def test_build_manifest_refuses_an_empty_predecessor_attempts_list(
    synthetic_world, bundled_repo, tmp_path
):
    lock, repo_root = bundled_repo
    _ids, split_hash, _role = load_split(
        repo_root, "discovery", lock, synthetic_world.data_root
    )
    with pytest.raises(BundleError, match="non-empty list"):
        build_manifest(
            repo_root=repo_root,
            data_root=synthetic_world.data_root,
            composed=_composed(),
            plan=_plan(split_hash),
            verified_split=load_verified_split(
                repo_root, "discovery", lock, synthetic_world.data_root
            ),
            session_receipt_path=None,
            run_dir=tmp_path / "manifest-run",
            status=STATUS_ABORTED,
            failure_reason="probe",
            predecessor_attempts=[],
        )
