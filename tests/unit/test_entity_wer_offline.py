"""Offline/deferred entity-wer CLI (owner decision D-3): a tmpdir fake run,
fail-closed cases, and a full ``main()`` round trip that never touches the
attempt directory."""

import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis import entity_wer_offline as offline
from speech_aware_evidence_acquisition.core.attempts import STATE_FINALIZED, STATE_OPENED
from speech_aware_evidence_acquisition.core.bundle import RUN_MANIFEST_SCHEMA, STATUS_COMPLETED


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_fake_run(
    tmp_path,
    run_id,
    attempt_id,
    *,
    carrier_lock_key,
    samples,
    state=STATE_FINALIZED,
    manifest_status=STATUS_COMPLETED,
    tamper_outputs_after_hashing=False,
):
    """Builds the SAME on-disk shape ``core.bundle.build_manifest`` +
    ``core.attempts.AttemptStore`` produce for a real run: outputs.jsonl and
    the run-manifest.json under ``<run_dir_parent>/<run_id>/<attempt_id>/``,
    and a SEPARATE attempt-state file under ``<attempts_root>/<run_id>/``."""

    runs_root = tmp_path / "runs"
    attempt_dir = runs_root / run_id / attempt_id
    attempt_dir.mkdir(parents=True)
    outputs_path = attempt_dir / f"{run_id}.outputs.jsonl"
    outputs_text = "".join(
        json.dumps(
            {"sample_id": sample_id, "carrier_lock_key": carrier_lock_key, "text": text},
            sort_keys=True,
        )
        + "\n"
        for sample_id, text in samples
    )
    outputs_path.write_text(outputs_text, encoding="utf-8")
    outputs_sha256 = _sha256_text(outputs_text)
    if tamper_outputs_after_hashing:
        outputs_path.write_text(outputs_text + "\n", encoding="utf-8")

    attempts_root = tmp_path / "attempts"
    attempt_state_dir = attempts_root / run_id
    attempt_state_dir.mkdir(parents=True, exist_ok=True)
    state_path = attempt_state_dir / f"{attempt_id}.json"
    state_path.write_text(
        json.dumps(
            {
                "schema": "saea-attempt-v1",
                "run_id": run_id,
                "attempt_id": attempt_id,
                "state": state,
                "reserved": {"calls": 1, "audio_seconds": 1.0},
                "actual": {"calls": 1, "audio_seconds": 1.0},
            }
        ),
        encoding="utf-8",
    )

    manifest = {
        "schema": RUN_MANIFEST_SCHEMA,
        "run_id": run_id,
        "created_at": "2026-08-13T00:00:00+00:00",
        "status": manifest_status,
        "failure_reason": None,
        "plan": {"carrier_lock_key": carrier_lock_key},
        "outputs": {"path": str(outputs_path.resolve()), "sha256": outputs_sha256},
        "attempt": {"run_id": run_id, "attempt_id": attempt_id, "state_path": str(state_path)},
    }
    manifest_path = attempt_dir / f"{run_id}.run-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return runs_root / run_id, manifest_path, outputs_path


# ---------------------------------------------------------------------------
# find_finalized_attempt: selection + fail-closed cases
# ---------------------------------------------------------------------------


def test_find_finalized_attempt_picks_the_finalized_one(tmp_path):
    run_id, attempt_id = "SAEA-TEST-001", "attempt-0001-aaaaaa"
    run_dir, _manifest_path, outputs_path = _write_fake_run(
        tmp_path,
        run_id,
        attempt_id,
        carrier_lock_key="earnings21-original",
        samples=[("4000001", "hello world")],
    )
    attempt = offline.find_finalized_attempt(run_dir, run_id)
    assert attempt.run_id == run_id
    assert attempt.attempt_id == attempt_id
    assert attempt.outputs_path == outputs_path.resolve()


def test_find_finalized_attempt_with_explicit_attempt_id(tmp_path):
    run_id, attempt_id = "SAEA-TEST-002", "attempt-0001-aaaaaa"
    run_dir, _, _ = _write_fake_run(
        tmp_path,
        run_id,
        attempt_id,
        carrier_lock_key="earnings21-original",
        samples=[("4000001", "hello world")],
    )
    attempt = offline.find_finalized_attempt(run_dir, run_id, attempt_id=attempt_id)
    assert attempt.attempt_id == attempt_id


def test_find_finalized_attempt_refuses_a_completed_but_not_yet_finalized_attempt(tmp_path):
    run_id, attempt_id = "SAEA-TEST-003", "attempt-0001-aaaaaa"
    run_dir, _, _ = _write_fake_run(
        tmp_path,
        run_id,
        attempt_id,
        carrier_lock_key="earnings21-original",
        samples=[("4000001", "hello world")],
        state=STATE_OPENED,
    )
    with pytest.raises(offline.EntityWerOfflineError, match="FINALIZED"):
        offline.find_finalized_attempt(run_dir, run_id)


def test_find_finalized_attempt_refuses_an_unknown_run(tmp_path):
    with pytest.raises(offline.EntityWerOfflineError, match="unknown run"):
        offline.find_finalized_attempt(tmp_path / "runs" / "never-existed", "never-existed")


def test_find_finalized_attempt_refuses_an_unknown_attempt_id(tmp_path):
    run_id, attempt_id = "SAEA-TEST-004", "attempt-0001-aaaaaa"
    run_dir, _, _ = _write_fake_run(
        tmp_path,
        run_id,
        attempt_id,
        carrier_lock_key="earnings21-original",
        samples=[("4000001", "hello world")],
    )
    with pytest.raises(offline.EntityWerOfflineError, match="no run-manifest.json"):
        offline.find_finalized_attempt(run_dir, run_id, attempt_id="attempt-never-existed")


def test_find_finalized_attempt_refuses_a_run_id_mismatch(tmp_path):
    run_id, attempt_id = "SAEA-TEST-005", "attempt-0001-aaaaaa"
    run_dir, _, _ = _write_fake_run(
        tmp_path,
        run_id,
        attempt_id,
        carrier_lock_key="earnings21-original",
        samples=[("4000001", "hello world")],
    )
    with pytest.raises(offline.EntityWerOfflineError, match="run_id"):
        offline.find_finalized_attempt(run_dir, "SAEA-TEST-DIFFERENT")


def test_find_finalized_attempt_refuses_a_tampered_outputs_file(tmp_path):
    run_id, attempt_id = "SAEA-TEST-006", "attempt-0001-aaaaaa"
    run_dir, _, _ = _write_fake_run(
        tmp_path,
        run_id,
        attempt_id,
        carrier_lock_key="earnings21-original",
        samples=[("4000001", "hello world")],
        tamper_outputs_after_hashing=True,
    )
    with pytest.raises(offline.EntityWerOfflineError, match="sha256"):
        offline.find_finalized_attempt(run_dir, run_id)


def test_verdict_output_path_is_under_derived_entity_wer():
    path = offline.verdict_output_path(Path("/data"), "R1", "A1")
    assert path == Path("/data/derived/entity-wer/R1/R1.A1.entity-wer.json")


# ---------------------------------------------------------------------------
# score_finalized_attempt / verdict_document: reuses the SAME registered
# scorer the in-run path uses.
# ---------------------------------------------------------------------------


def test_score_finalized_attempt_matches_the_registered_scorer(tmp_path, synthetic_world):
    from speech_aware_evidence_acquisition.core.scorers import score_entity_wer_outputs
    from speech_aware_evidence_acquisition.data.lock import load_lock

    nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp"
    nlp.parent.mkdir(parents=True, exist_ok=True)
    nlp.write_text("token|speaker|tags|wer_tags\nAcme|0||['0']\n", encoding="utf-8")
    sidecar = synthetic_world.e21 / "transcripts" / "wer_tags" / "4000001.wer_tag.json"
    sidecar.write_text(json.dumps({"0": {"entity_type": "ORG"}}), encoding="utf-8")

    run_id, attempt_id = "SAEA-TEST-007", "attempt-0001-aaaaaa"
    run_dir, _, outputs_path = _write_fake_run(
        tmp_path,
        run_id,
        attempt_id,
        carrier_lock_key="earnings21-original",
        samples=[("4000001", "Acme")],
    )
    lock = load_lock(synthetic_world.lock_path)
    attempt = offline.find_finalized_attempt(run_dir, run_id)
    scores = offline.score_finalized_attempt(attempt, lock, synthetic_world.data_root)
    expected = score_entity_wer_outputs(outputs_path, lock, synthetic_world.data_root)
    assert scores == expected
    assert scores["per_sample"][0]["entity_wer"] == 0.0

    document = offline.verdict_document(attempt, scores, generated_at="2026-08-13T00:00:00+00:00")
    assert document["run_id"] == run_id
    assert document["attempt_id"] == attempt_id
    assert document["aggregate"] == scores["aggregate"]


# ---------------------------------------------------------------------------
# Full main() round trip: verdict written next to (never inside) the attempt
# dir; attempt dir bytes provably untouched.
# ---------------------------------------------------------------------------


def test_main_writes_a_verdict_and_never_touches_the_attempt_dir(
    tmp_path, monkeypatch, synthetic_world
):
    import speech_aware_evidence_acquisition.data.lock as lock_module

    nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp"
    nlp.parent.mkdir(parents=True, exist_ok=True)
    nlp.write_text("token|speaker|tags|wer_tags\nAcme|0||['0']\n", encoding="utf-8")
    sidecar = synthetic_world.e21 / "transcripts" / "wer_tags" / "4000001.wer_tag.json"
    sidecar.write_text(json.dumps({"0": {"entity_type": "ORG"}}), encoding="utf-8")

    run_id, attempt_id = "SAEA-TEST-008", "attempt-0001-aaaaaa"
    runs_root, manifest_path, outputs_path = _write_fake_run(
        synthetic_world.data_root,
        run_id,
        attempt_id,
        carrier_lock_key="earnings21-original",
        samples=[("4000001", "Acme")],
    )
    manifest_bytes_before = manifest_path.read_bytes()
    outputs_bytes_before = outputs_path.read_bytes()
    attempt_dir_entries_before = sorted(
        p.relative_to(synthetic_world.data_root) for p in (synthetic_world.data_root / "runs").rglob("*")
    )

    monkeypatch.setattr(lock_module, "data_root", lambda: synthetic_world.data_root)
    monkeypatch.setattr(
        lock_module, "umbrella_lock_path", lambda repo_root=None: synthetic_world.lock_path
    )

    exit_code = offline.main(["--run", run_id])
    assert exit_code == 0

    verdict_path = offline.verdict_output_path(synthetic_world.data_root, run_id, attempt_id)
    assert verdict_path.is_file()
    document = json.loads(verdict_path.read_text(encoding="utf-8"))
    assert document["run_id"] == run_id
    assert document["attempt_id"] == attempt_id
    assert document["aggregate"]["samples"] == 1
    assert document["per_sample"][0]["entity_wer"] == 0.0

    # The attempt directory (runs/<run_id>/...) is provably untouched: same
    # bytes, same file set, no new/removed entries.
    assert manifest_path.read_bytes() == manifest_bytes_before
    assert outputs_path.read_bytes() == outputs_bytes_before
    attempt_dir_entries_after = sorted(
        p.relative_to(synthetic_world.data_root) for p in (synthetic_world.data_root / "runs").rglob("*")
    )
    assert attempt_dir_entries_after == attempt_dir_entries_before
    # The verdict landed in its OWN directory, never under runs/ or attempts/.
    assert "runs" not in verdict_path.relative_to(synthetic_world.data_root).parts
    assert "attempts" not in verdict_path.relative_to(synthetic_world.data_root).parts


def test_main_refuses_an_unknown_run(tmp_path, monkeypatch, synthetic_world, capsys):
    import speech_aware_evidence_acquisition.data.lock as lock_module

    monkeypatch.setattr(lock_module, "data_root", lambda: synthetic_world.data_root)
    monkeypatch.setattr(
        lock_module, "umbrella_lock_path", lambda repo_root=None: synthetic_world.lock_path
    )
    exit_code = offline.main(["--run", "never-existed-run"])
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "REFUSED" in captured.err
    verdict_path = offline.verdict_output_path(
        synthetic_world.data_root, "never-existed-run", "irrelevant"
    ).parent
    assert not verdict_path.exists()
