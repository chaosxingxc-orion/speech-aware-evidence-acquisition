"""End-to-end obs-agent-loop: run_experiment_bundled -> verify_bundle ->
score_bundle on the synthetic world (owner directive 2026-08-08).

Proves the three seams no unit test can prove alone:

1. the driver wires the SAME SliceRegistry into both the adapter (rail) and
   the policy (extras), so a multi-iteration run flows through the real
   FrozenCoreAdapter with real budget metering per slice;
2. the stitched outputs row survives ``core.bundle.verify_bundle``'s I7
   outputs<->trace binding (the policy's terminal /request + /response
   stitch records ARE what the row binds to);
3. the stitched hypothesis scores through the frozen ``asr-wer`` scorer with
   the reference-identity gate scoped to the whole-call sample ids
   (untouched by segmentation -- one row per parent call).
"""

import hashlib
import json
import random
import subprocess
from array import array

import pytest

import speech_aware_evidence_acquisition.core  # noqa: F401 (populate registries)
from speech_aware_evidence_acquisition.contracts import ExecutionPlan
from speech_aware_evidence_acquisition.core.bundle import verify_bundle
from speech_aware_evidence_acquisition.core.config import ComposedConfig, protocol_hash
from speech_aware_evidence_acquisition.core.driver import (
    load_split,
    run_experiment_bundled,
)
from speech_aware_evidence_acquisition.core.scorers import score_bundle
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.data.splits import freeze_splits
from speech_aware_evidence_acquisition.reproduction import obs_loop

RATE = 16000
RUN_ID = "SAEA-E-000-obsloop-e2e"


def _noise(seconds: float, seed: int = 11) -> array:
    rng = random.Random(seed)
    return array(
        "h", (int(6000 * (2 * rng.random() - 1)) for _ in range(int(seconds * RATE)))
    )


def _git(repo_root, *args):
    subprocess.run(["git", *args], cwd=repo_root, check=True, capture_output=True, text=True)


def _transport(request_bytes):
    payload = json.loads(request_bytes.decode("utf-8"))
    # Echo a per-slice transcript with a clean boundary so the loop advances.
    slice_name = payload["media_relpath"].rsplit("/", 1)[-1]
    return json.dumps(
        {
            "text": f"TRANSCRIPT:\nhello world {slice_name}.\nBOUNDARY_SECONDS: 45",
            "usage": {"prompt_tokens": 3},
        }
    ).encode()


class _OpenGate:
    def assert_model_touch_allowed(self, plan):
        pass


def _composed(**overrides):
    values = {
        "carrier_lock_key": "earnings21-original",
        "split_name": "discovery",
        "arm": "bare-core",
        "policy": "obs-agent-loop",
        "evidence_source": "none",
        "evidence_mismatch": False,
        "scorers": ["asr-wer"],
        "task_instruction": "Transcribe the speech verbatim.",
        "decoding_params": {"temperature": 0, "seed": 20260803},
        "experiment_id": "SAEA-E-000",
        "obs_buffer_seconds": 60,
        "obs_min_advance_seconds": 20,
        "obs_max_advance_seconds": 55,
        "obs_silence_snap_seconds": 2.0,
        "obs_fallback_advance_seconds": 50,
        "obs_boundary_mode": "model",
        "obs_boundary_prompt": "probes/obs_boundary_v1.txt",
        "obs_vad": "energy",
        "obs_vad_trim_min_seconds": 5.0,
        "obs_preprocess": [],
        "obs_condition_tail_chars": 400,
    }
    values.update(overrides)
    return ComposedConfig(
        values=values, config_hash="d" * 64,
        fragments={"model": "m", "dataset": "d", "baseline": "b", "experiment": "e"},
    )


@pytest.fixture()
def obs_repo(synthetic_world, tmp_path, monkeypatch):
    # 90s of speech-like PCM per call (CSV says 100.5s; within the slice
    # rail's parent-duration tolerance)
    monkeypatch.setattr(
        obs_loop, "decode_parent_pcm", lambda path, rate=RATE: _noise(90.0)
    )
    lock = load_lock(synthetic_world.lock_path)
    repo_root = tmp_path / "repo"
    receipts = repo_root / "docs" / "receipts"
    freeze_splits(lock, synthetic_world.data_root, receipts)
    # boundary prompt template lives under the (synthetic) study repo
    template = repo_root / "configs" / "probes" / "obs_boundary_v1.txt"
    template.parent.mkdir(parents=True, exist_ok=True)
    template.write_text("Report BOUNDARY_SECONDS after the transcript.\n", encoding="utf-8")
    # real reference tokens + a matching synthetic D1 receipt so the scoring
    # entry gate's reference-identity rail passes (mirrors test_bundle.py)
    manifest_entries = []
    for sample_id in ("4000001", "4000002", "4000003"):
        nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / f"{sample_id}.nlp"
        nlp.write_text("token|tags\nhello|\nworld|\n", encoding="utf-8")
        raw = nlp.read_bytes()
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
    _git(repo_root, "init", "-q")
    _git(repo_root, "config", "user.email", "test@example.com")
    _git(repo_root, "config", "user.name", "Test")
    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-q", "-m", "obs e2e snapshot")
    return lock, repo_root


def test_obs_loop_end_to_end_bundle_verifies_and_scores(
    synthetic_world, tmp_path, obs_repo
):
    lock, repo_root = obs_repo
    ids, split_hash, _ = load_split(
        repo_root, "discovery", lock, synthetic_world.data_root
    )
    assert len(ids) == 3
    composed = _composed()
    plan = ExecutionPlan(
        run_id=RUN_ID,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="earnings21-original",
        split_role="discovery",
        split_identity_hash=split_hash,
        planned_model_calls=10,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=1000,
        protocol_hash=protocol_hash(composed.config_hash, "bare-core", split_hash),
        attempt_id="attempt-obs-e2e",
    )
    manifest_path = run_experiment_bundled(
        composed, plan, _OpenGate(), lock, synthetic_world.data_root,
        tmp_path / "run", _transport, repo_root=repo_root,
    )

    # ---- the run's shape: 2 slice requests per 90s call (45s advance) ----
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "COMPLETED"
    assert manifest["cost"]["calls_used"] == 6
    assert manifest["cost"]["audio_seconds_used"] == pytest.approx(3 * (60 + 45), abs=0.1)

    outputs_path = tmp_path / "run" / f"{RUN_ID}.outputs.jsonl"
    rows = [
        json.loads(line)
        for line in outputs_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    assert sorted(row["sample_id"] for row in rows) == sorted(ids)
    for row in rows:
        # one stitched hypothesis per whole call, two spans joined
        assert row["text"].count("hello world") == 2
        assert (
            hashlib.sha256(row["text"].encode("utf-8")).hexdigest()
            == row["response_text_sha256"]
        )

    # ---- I7: the bundle verifies (stitch records bind the outputs rows) ----
    bundle = verify_bundle(manifest_path)
    assert bundle.attempt_state == "OPENED"

    # ---- frozen asr-wer scores the stitched rows, whole-call sample ids ----
    results = score_bundle(bundle, lock, synthetic_world.data_root, repo_root=repo_root)
    assert results["asr-wer"]["aggregate"]["samples"] == 3
    scored_ids = {entry["sample_id"] for entry in results["asr-wer"]["per_sample"]}
    assert scored_ids == set(ids)

    # ---- per-sample obs derivation records landed beside the bundle ----
    for sample_id in ids:
        record_path = tmp_path / "run" / f"{RUN_ID}.obs-derivation.{sample_id}.json"
        document = json.loads(record_path.read_text(encoding="utf-8"))
        assert len(document["slices"]) == 2
        assert document["slices"][1]["start_seconds"] == pytest.approx(45.0)


def test_obs_loop_evidence_budget_is_identical_across_every_slice(
    synthetic_world, tmp_path, obs_repo
):
    """SUPPLY dose knob (evidence_budget_bytes, core.evidence_budget):
    truncated ONCE per sample in core.driver.run.run_experiment, before
    ObsAgentLoopPolicy's per-slice fan-out even starts -- every one of a
    sample's N slice requests must carry the SAME truncated evidence text,
    never a fresh/independent truncation per slice."""

    lock, repo_root = obs_repo
    _, split_hash, _ = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed(
        arm="fixed-legal-context",
        evidence_source="conec-contexts",
        evidence_budget_bytes=2,
    )
    plan = ExecutionPlan(
        run_id="SAEA-E-000-obsloop-evbudget",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="earnings21-original",
        split_role="discovery",
        split_identity_hash=split_hash,
        planned_model_calls=10,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=1000,
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
        attempt_id="attempt-obs-evbudget",
    )
    seen_contents = []

    def _capturing_transport(request_bytes):
        payload = json.loads(request_bytes.decode("utf-8"))
        seen_contents.append(payload["supplied_evidence"][0]["content"])
        slice_name = payload["media_relpath"].rsplit("/", 1)[-1]
        return json.dumps(
            {
                "text": f"TRANSCRIPT:\nhello world {slice_name}.\nBOUNDARY_SECONDS: 45",
                "usage": {"prompt_tokens": 3},
            }
        ).encode()

    run_experiment_bundled(
        composed, plan, _OpenGate(), lock, synthetic_world.data_root,
        tmp_path / "run-evbudget", _capturing_transport, repo_root=repo_root,
    )
    # 2 slices per 90s call (45s advance, module docstring above) x 3 calls
    assert len(seen_contents) == 6
    # every slice's evidence is the SAME truncated 2-byte prefix (the shipped
    # conec fixture "ctx" -- see tests/unit/conftest.py) -- never a
    # per-slice-independent truncation, and always within the configured
    # budget.
    assert set(seen_contents) == {"ct"}


def test_obs_loop_slice_budget_is_charged_per_slice_not_per_parent(
    synthetic_world, tmp_path, obs_repo
):
    """The audio budget rail sees slice seconds: a plan too small for the
    slices (but big enough for one whole call) refuses mid-run and the
    attempt aborts -- proving metering is per actually-sent slice.

    Task 2 (2026-08-09) changed WHICH exception surfaces here, not WHETHER
    the attempt aborts: "audio budget exhausted" is a FrozenCoreError, which
    was already retryable before this task (2026-08-08 comment at
    obs_loop.SLICE_RETRYABLE_EXCEPTIONS -- "a budget/binding refusal
    retried once fails identically and spends nothing, so no carve-out is
    needed"). A budget refusal never recovers between attempts, so it now
    exhausts retries, skips, and -- because the SAME refusal recurs on every
    following slice -- crosses obs_slice_skip_max within a couple of slices
    either way. The attempt still aborts (proving the same underlying
    invariant this test exists for), just via the skip-bound message rather
    than the raw budget one.
    """

    lock, repo_root = obs_repo
    ids, split_hash, _ = load_split(
        repo_root, "discovery", lock, synthetic_world.data_root
    )
    composed = _composed()
    plan = ExecutionPlan(
        run_id="SAEA-E-000-obsloop-budget",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="earnings21-original",
        split_role="discovery",
        split_identity_hash=split_hash,
        planned_model_calls=10,
        planned_gpu_hours=1.0,
        # 3 calls x 105 slice-seconds = 315 needed; 200 is not enough
        planned_speech_audio_seconds=200,
        protocol_hash=protocol_hash(composed.config_hash, "bare-core", split_hash),
        attempt_id="attempt-obs-budget",
    )
    with pytest.raises(Exception, match="obs_slice_skip_max"):
        run_experiment_bundled(
            composed, plan, _OpenGate(), lock, synthetic_world.data_root,
            tmp_path / "run-budget", _transport, repo_root=repo_root,
        )
