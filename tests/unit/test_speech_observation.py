from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.attempts import AttemptStore
from speech_aware_evidence_acquisition.core.preparation import canonical_bytes, digest
from speech_aware_evidence_acquisition.rails.knowledge import QueryState
from speech_aware_evidence_acquisition.rails.runner import AgentRuntimeContext
from speech_aware_evidence_acquisition.rails.errors import RailsError
from speech_aware_evidence_acquisition.rails.speech_observation import (
    PREPARED_SPEECH_OBSERVATION_TOOL,
    SpeechObservationError,
    SpeechObservationSelection,
    load_speech_observation_catalog,
)


SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
SHA_D = "d" * 64
SHA_E = "e" * 64


def _write_pinned(root: Path, relpath: str, content: str) -> str:
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _context(sample_id: str = "sample-1") -> AgentRuntimeContext:
    query = QueryState(
        query_id=f"run:{sample_id}:step0",
        query_sample_id=sample_id,
        speech_packet_id=f"packet:{sample_id}",
        speech_packet_sha256=SHA_A,
        use_split_identity_hash=SHA_B,
    ).validate()
    return AgentRuntimeContext(
        sample_id=sample_id,
        knowledge_snapshot_sha256=SHA_C,
        catalog_facet_ids=(),
        catalog_value_ids=(),
        query_state=query,
        task_contract="Return the task answer.",
        agent_states=(),
        prior_response_sha256s=(),
        contact_index=1,
    )


def _artifact_inputs(row: dict, catalog: dict) -> dict:
    producer = catalog["producer"]
    return {
        "config_sha256": catalog["decoding_config_sha256"],
        "split_identity_hash": catalog["use_split_identity_hash"],
        "sources": {
            "sample_id": row["sample_id"],
            "speech_packet_id": row["speech_packet_id"],
            "speech_packet_sha256": row["speech_packet_sha256"],
            "source_audio_relpath": row["source_audio_relpath"],
            "source_audio_sha256": row["source_audio_sha256"],
            "source_audio_duration_seconds": row[
                "source_audio_duration_seconds"
            ],
            "span": row["span"],
            "checkpoint_receipt": catalog["checkpoint_receipt"],
            "producer_run_id": producer["run_id"],
            "producer_attempt_id": producer["attempt_id"],
            "execution_plan": producer["execution_plan"],
            "protocol_sha256": producer["protocol_sha256"],
            "ledger_row": producer["ledger_row"],
        },
    }


def _world(
    tmp_path: Path,
    *,
    status: str = "ok",
    transcript: str = "The café order is ready.",
    finalize: bool = True,
    producer_calls: int = 1,
    producer_audio_seconds: float = 2.5,
    extra_row: bool = False,
    catalog_mutator=None,
    artifact_mutator=None,
):
    data_root = tmp_path / "data"
    repo_root = tmp_path / "repo"
    checkpoint_sha = _write_pinned(repo_root, "receipts/checkpoint.json", "checkpoint")
    plan_document = {
        "execution_plan": {
            "run_id": "speech-observation-preparation-v1",
            "execution_profile": "bounded-discovery-probe",
            "carrier_lock_key": "slurp-original",
            "split_role": "dev",
            "split_identity_hash": SHA_B,
            "planned_model_calls": 1,
            "planned_gpu_hours": 0.1,
            "planned_speech_audio_seconds": 3,
            "protocol_hash": SHA_A,
            "attempt_id": "attempt-001",
        }
    }
    plan_sha = _write_pinned(
        repo_root, "plans/speech-observation.json", json.dumps(plan_document)
    )
    ledger = "\n".join(
        (
            "| run/experiment id | speech carrier + split | execution profile | split role | split identity hash | consumed | calls | speech audio seconds | gpu hours |",
            "|---|---|---|---|---|---|---|---|---|",
            f"| speech-observation-preparation-v1 | slurp-original, dev | bounded-discovery-probe | dev | {SHA_B} | yes | 1 | 3 | 0.1 |",
        )
    )
    ledger_sha = _write_pinned(repo_root, "docs/exposure-ledger.md", ledger)
    row = {
        "sample_id": "sample-1",
        "speech_packet_id": "packet:sample-1",
        "speech_packet_sha256": SHA_A,
        "source_audio_relpath": "audio/sample-1.wav",
        "source_audio_sha256": SHA_C,
        "source_audio_duration_seconds": 2.5,
        "span": {
            "kind": "full-utterance",
            "start_seconds": 0.0,
            "end_seconds": 2.5,
        },
        "artifact_relpath": "prepared/speech/sample-1.json",
        "artifact_sha256": "pending",
        "output_sha256": "pending",
    }
    catalog = {
        "schema": "saea-prepared-speech-observation-catalog-v1",
        "catalog_id": "speech-observations-test-v1",
        "use_split_identity_hash": SHA_B,
        "checkpoint_receipt": {
            "relpath": "receipts/checkpoint.json",
            "sha256": checkpoint_sha,
        },
        "decoding_config_sha256": SHA_D,
        "producer": {
            "run_id": "speech-observation-preparation-v1",
            "attempt_id": "attempt-001",
            "execution_plan": {
                "relpath": "plans/speech-observation.json",
                "sha256": plan_sha,
            },
            "protocol_sha256": SHA_A,
            "ledger_row": {
                "relpath": "docs/exposure-ledger.md",
                "sha256": ledger_sha,
                "row_id": "speech-observation-preparation-v1",
            },
            "contacts": {
                "calls": producer_calls,
                "audio_seconds": producer_audio_seconds,
            },
        },
        "observations": [row],
    }
    output = {
        "schema": "saea-prepared-speech-observation-v1",
        "status": status,
        "transcript": transcript,
        "diagnostics": {"language": "en"},
    }
    if artifact_mutator:
        artifact_mutator(output)
    row["output_sha256"] = digest(output)
    artifact = {
        "schema": "saea-prepared-artifact-v1",
        "kind": "prepared-speech-observation-v1",
        "inputs": _artifact_inputs(row, catalog),
        "contact_class": "speech-tool",
        "output": output,
        "output_sha256": row["output_sha256"],
    }
    artifact_path = data_root / row["artifact_relpath"]
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_bytes(canonical_bytes(artifact))
    row["artifact_sha256"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    if extra_row:
        catalog["observations"].append(
            {
                **row,
                "sample_id": "sample-2",
                "speech_packet_id": "packet:sample-2",
                "source_audio_relpath": "audio/sample-2.wav",
                "artifact_relpath": "prepared/speech/sample-2.json",
            }
        )
    if catalog_mutator:
        catalog_mutator(catalog)
    catalog_relpath = "prepared/speech/catalog.json"
    catalog_path = data_root / catalog_relpath
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_bytes(canonical_bytes(catalog))
    catalog_sha = hashlib.sha256(catalog_path.read_bytes()).hexdigest()

    store = AttemptStore(data_root / "attempts")
    handle = store.open_attempt(
        catalog["producer"]["run_id"],
        catalog["producer"]["attempt_id"],
        carrier_lock_key="slurp-original",
        reserved_calls=1,
        reserved_audio_seconds=2.5,
    )
    handle.record_usage(calls=producer_calls, audio_seconds=producer_audio_seconds)
    if finalize:
        handle.finalize_with_receipt(
            catalog_relpath, catalog_sha, "speech-observation-catalog"
        )
    config = {
        "prepared_speech_observations": {
            "relpath": catalog_relpath,
            "sha256": catalog_sha,
        }
    }
    source_bindings = {
        "sample-1": {
            "packet_id": "packet:sample-1",
            "packet_sha256": SHA_A,
            "source_audio_relpath": "audio/sample-1.wav",
            "source_audio_sha256": SHA_C,
            "source_audio_duration_seconds": 2.5,
        }
    }
    if extra_row:
        source_bindings["sample-2"] = {
            **source_bindings["sample-1"],
            "packet_id": "packet:sample-2",
            "source_audio_relpath": "audio/sample-2.wav",
        }
    return config, data_root, repo_root, source_bindings, catalog


def _load(world):
    config, data_root, repo_root, sources, _ = world
    return load_speech_observation_catalog(
        config,
        data_root=data_root,
        source_audio_bindings=sources,
        split_identity_hash=SHA_B,
        repo_root=repo_root,
    )


def test_absent_or_empty_config_is_opt_out(tmp_path):
    for config in ({}, {"prepared_speech_observations": None}, {"prepared_speech_observations": {}}):
        assert load_speech_observation_catalog(
            config,
            data_root=tmp_path,
            source_audio_bindings={},
            split_identity_hash=SHA_B,
            repo_root=tmp_path,
        ) is None


def test_contract_error_is_a_shared_rails_error():
    assert issubclass(SpeechObservationError, RailsError)


def test_load_select_and_receipt_preserve_binding_and_accounting(tmp_path):
    catalog = _load(_world(tmp_path))
    selection = catalog.select(context=_context())

    assert PREPARED_SPEECH_OBSERVATION_TOOL == "saea-tool-prepared-speech-observation-v1"
    assert isinstance(selection, SpeechObservationSelection)
    assert selection.visible["schema"] == "saea-speech-observation-selection-v1"
    assert selection.visible["transcript"] == "The café order is ready."
    assert selection.visible["sample_id"] == "sample-1"
    assert selection.visible["use_split_identity_hash"] == SHA_B
    assert selection.visible["speech_packet_id"] == "packet:sample-1"
    assert selection.visible["speech_packet_sha256"] == SHA_A
    assert selection.visible["artifact_sha256"] == selection.lineage["artifact_sha256"]
    assert selection.lineage["preparation_contacts"] == {
        "calls": 1,
        "audio_seconds": 2.5,
    }
    receipt = catalog.receipt()
    assert receipt["prepared_count"] == 1
    assert receipt["producer_contacts"] == {"calls": 1, "audio_seconds": 2.5}
    assert "transcript" not in json.dumps(receipt)


@pytest.mark.parametrize("status", ["empty", "timeout", "unsupported"])
def test_fallback_status_has_deterministic_nonanswering_evidence(tmp_path, status):
    selection = _load(_world(tmp_path, status=status, transcript="")).select(
        context=_context()
    )
    assert selection.visible["status"] == status
    assert selection.visible["transcript"] == (
        f"The prepared speech observation returned status: {status}. "
        "Keep the prior draft unless other evidence supports a change."
    )


@pytest.mark.parametrize(
    "change,match",
    [
        (lambda c: c["observations"].append(dict(c["observations"][0], sample_id="extra")), "roster"),
        (lambda c: c["observations"][0].update(speech_packet_sha256=SHA_D), "source binding"),
        (lambda c: c["observations"][0]["span"].update(start_seconds=0.1), "full-utterance"),
        (lambda c: c["observations"][0]["span"].update(end_seconds=2.4), "full-utterance"),
        (lambda c: c["producer"]["contacts"].update(calls=2), "actual accounting"),
    ],
)
def test_catalog_refuses_roster_source_span_and_accounting_drift(tmp_path, change, match):
    with pytest.raises(SpeechObservationError, match=match):
        _load(_world(tmp_path, catalog_mutator=change))


def test_catalog_requires_finalized_attempt_bound_to_it(tmp_path):
    with pytest.raises(SpeechObservationError, match="FINALIZED"):
        _load(_world(tmp_path, finalize=False))


@pytest.mark.parametrize(
    "change,match",
    [
        (lambda o: o.update(schema="wrong"), "output"),
        (lambda o: o.update(status="other"), "status"),
        (lambda o: o.update(status="ok", transcript=""), "non-empty transcript"),
        (lambda o: o.update(status="empty", transcript="unexpected"), "empty transcript"),
    ],
)
def test_artifact_output_contract_is_fail_closed(tmp_path, change, match):
    with pytest.raises(SpeechObservationError, match=match):
        _load(_world(tmp_path, artifact_mutator=change))


def test_artifact_contact_class_and_identity_are_verified(tmp_path):
    world = _world(tmp_path)
    config, data_root, _, _, catalog = world
    path = data_root / catalog["observations"][0]["artifact_relpath"]
    document = json.loads(path.read_text())
    document["contact_class"] = "model-free"
    path.write_bytes(canonical_bytes(document))
    catalog["observations"][0]["artifact_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    catalog_path = data_root / config["prepared_speech_observations"]["relpath"]
    catalog_path.write_bytes(canonical_bytes(catalog))
    config["prepared_speech_observations"]["sha256"] = hashlib.sha256(catalog_path.read_bytes()).hexdigest()
    attempt = data_root / "attempts/speech-observation-preparation-v1/attempt-001.json"
    state = json.loads(attempt.read_text())
    state["finalization"]["sha256"] = config["prepared_speech_observations"]["sha256"]
    attempt.write_text(json.dumps(state), encoding="utf-8")
    with pytest.raises(SpeechObservationError, match="speech-tool"):
        _load(world)


@pytest.mark.parametrize(
    "context",
    [
        _context("other"),
        replace(_context(), sample_id="other"),
        replace(_context(), query_state=replace(_context().query_state, use_split_identity_hash=SHA_D)),
        replace(_context(), query_state=replace(_context().query_state, speech_packet_sha256=SHA_D)),
    ],
)
def test_select_refuses_cross_sample_split_or_packet_context(tmp_path, context):
    with pytest.raises(SpeechObservationError, match="context"):
        _load(_world(tmp_path)).select(context=context)


def test_config_and_pinned_repo_paths_are_confined(tmp_path):
    world = _world(tmp_path)
    config, data_root, repo_root, sources, _ = world
    config["prepared_speech_observations"]["relpath"] = "../outside.json"
    with pytest.raises(SpeechObservationError, match="confined"):
        load_speech_observation_catalog(
            config,
            data_root=data_root,
            source_audio_bindings=sources,
            split_identity_hash=SHA_B,
            repo_root=repo_root,
        )


@pytest.mark.parametrize(
    "relpath",
    [
        r"prepared\speech\catalog.json",
        "C:prepared/speech/catalog.json",
        "prepared/./speech/catalog.json",
        "prepared//speech/catalog.json",
    ],
)
def test_config_pin_requires_canonical_posix_relative_path(tmp_path, relpath):
    world = _world(tmp_path)
    config, data_root, repo_root, sources, _ = world
    config["prepared_speech_observations"]["relpath"] = relpath
    with pytest.raises(SpeechObservationError, match="canonical POSIX"):
        load_speech_observation_catalog(
            config,
            data_root=data_root,
            source_audio_bindings=sources,
            split_identity_hash=SHA_B,
            repo_root=repo_root,
        )


def test_catalog_calls_cover_every_prepared_observation(tmp_path):
    with pytest.raises(SpeechObservationError, match="one contact per observation"):
        _load(_world(tmp_path, extra_row=True))


def test_catalog_audio_accounting_covers_every_full_utterance(tmp_path):
    with pytest.raises(SpeechObservationError, match="full-utterance durations"):
        _load(_world(tmp_path, producer_audio_seconds=2.49))
