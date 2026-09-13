"""Real prepared-source verification and delivery without model contacts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from test_slurp_topn_diagnostics_cli import _raw_entry_fixture
from speech_aware_evidence_acquisition.contracts import TraceRecord
from speech_aware_evidence_acquisition.core.bundle import BundleError
from speech_aware_evidence_acquisition.core.bundle.artifacts import VerifiedBundle
from speech_aware_evidence_acquisition.core.bundle.hypothesis_source import (
    FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
    prepare_hypothesis_source,
)
from speech_aware_evidence_acquisition.core.bundle.verify import verify_bundle
from speech_aware_evidence_acquisition.core.preparation import canonical_bytes
from speech_aware_evidence_acquisition.rails.candidate_contract_lookup import canonical_sha256
from speech_aware_evidence_acquisition.rails.phase_material import sealed_states_from_manifest
from speech_aware_evidence_acquisition.rails.slurp_candidate_contracts import PROVIDER_SCHEMA

COMMIT = "a" * 40
PRODUCER = "phase-intent-hypotheses-only-v1"


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _pin(path):
    return {"path": str(path), "sha256": _sha(path.read_bytes())}


def _fixture(tmp_path):
    previous = _raw_entry_fixture(tmp_path)
    raw = previous["analysis"]["raw_source_diagnostics"]
    trace = Path(raw["raw_trace"]["path"])
    records = [json.loads(line) for line in trace.read_text().splitlines()]
    for sid in ("s1", "s2"):
        payload = {"use_controller_policy_id": PRODUCER}
        TraceRecord("USE", sid + "/runtime", payload).validate()
        records.append({"channel": "USE", "record_id": sid + "/runtime", "payload": payload})
    trace.write_text("".join(json.dumps(row) + "\n" for row in records))
    data = tmp_path / "data"
    data.mkdir()
    catalog = {"schema": PROVIDER_SCHEMA, "profiles": [
        {"candidate_id": "a"}, {"candidate_id": "b"}, {"candidate_id": "c"},
    ]}
    catalog_path = data / "catalog.json"
    catalog_path.write_text(json.dumps(catalog))
    baseline = tmp_path / "source-config.json"
    baseline.write_text(json.dumps({
        "policy": PRODUCER,
        "artifact_result": {"content_contract": {
            "id": "slurp-intent-hypotheses-v1", "min_candidates": 3, "max_candidates": 3,
            "source_catalog": {"data_relpath": "catalog.json",
                               "sha256": _sha(catalog_path.read_bytes()),
                               "source_sha256": canonical_sha256(catalog)},
        }},
    }))
    registration = {
        "schema": "saea-model-free-hypothesis-recovery-registration-v1",
        "experiment_id": "synthetic-derived-source",
        "execution_profile": "model-free-check", "recovery_number": 1,
        "original_attempt_state_required": "ABORTED",
        "projection_policy": FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
        "contacts": {"model": 0, "tokenizer": 0, "encoder": 0, "asr": 0, "official_scorer": 0},
        "full_roster": previous["analysis"]["full_roster"],
        "split_identity_hash": raw["split_identity_hash"],
        "source_config": _pin(baseline), "source_attempt": raw["attempt"],
        "source_trace": _pin(trace), "source_generation_plan": raw["generation_plan"],
        "output_relpath": "prepared/hypothesis-source",
    }
    reg_path = tmp_path / "registration.json"
    reg_path.write_text(json.dumps(registration))
    path = data / registration["output_relpath"] / "hypotheses.source.json"
    return reg_path, data, path, registration


def _prepare(tmp_path):
    reg, data, path, registration = _fixture(tmp_path)
    receipt = prepare_hypothesis_source(
        registration_path=reg, data_root=data, implementation_commit=COMMIT
    )
    return reg, data, path, registration, receipt


def test_prepares_all_rows_and_reuses_cache_without_altering_source(tmp_path):
    reg, data, path, registration, receipt = _prepare(tmp_path)
    source_paths = [Path(registration[key]["path"])
                    for key in ("source_attempt", "source_trace", "source_generation_plan")]
    before = [p.read_bytes() for p in source_paths]
    verified = verify_bundle(path)
    assert verified.attempt_state == "DERIVED"
    assert verified.outputs_path is None
    assert verified.manifest["status"] == "COMPLETED_DERIVATION"
    assert verified.manifest["contact_accounting"]["source_model_calls"] == 2
    assert verified.split_ids == frozenset({"s1", "s2"})
    assert receipt["new_model_calls"] == 0
    for row in verified.outputs_rows:
        raw = json.loads(row["text"])["candidates"]
        projected = json.loads(row["artifact_content"])["candidates"]
        assert len(raw) == 3 and len(projected) == 2
        assert [candidate["intent_id"] for candidate in projected] == list(
            dict.fromkeys(candidate["intent_id"] for candidate in raw)
        )
        assert len(row["raw_positions"]) == 3
        assert row["original_text_sha256"] == _sha(row["text"].encode())
    sealed = path.read_bytes()
    cached = prepare_hypothesis_source(
        registration_path=reg, data_root=data, implementation_commit=COMMIT
    )
    assert cached["cache"] == "warm"
    assert path.read_bytes() == sealed
    assert [p.read_bytes() for p in source_paths] == before
    states = sealed_states_from_manifest(
        path, expected_sha256=_sha(sealed), phase_name="slots",
        producer_policy_id=PRODUCER, sample_ids=("s1", "s2"),
    )
    for row in verified.outputs_rows:
        assert states[row["sample_id"]].content == row["artifact_content"]
        assert states[row["sample_id"]].source_response_sha256 == row["artifact_content_sha256"]


def test_rejects_changed_projection_even_if_outer_digest_is_recomputed(tmp_path):
    _reg, _data, path, _registration, _receipt = _prepare(tmp_path)
    document = json.loads(path.read_text())
    document["output"]["rows"][0]["artifact_content"] = "replaced"
    document["output_sha256"] = _sha(canonical_bytes(document["output"]))
    path.write_text(json.dumps(document))
    with pytest.raises(BundleError, match="deterministic source replay"):
        verify_bundle(path)


def test_rejects_changed_original_source_and_other_output_path(tmp_path):
    _reg, data, path, registration, _receipt = _prepare(tmp_path)
    relocated = data / "different.source.json"
    relocated.write_bytes(path.read_bytes())
    with pytest.raises(BundleError, match="path differs"):
        verify_bundle(relocated)
    attempt = Path(registration["source_attempt"]["path"])
    document = json.loads(attempt.read_text())
    document["state"] = "FINALIZED"
    attempt.write_text(json.dumps(document))
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_bundle(path)


def test_rejects_nonzero_contact_registration_before_artifact_write(tmp_path):
    reg, data, path, registration = _fixture(tmp_path)
    registration["contacts"]["model"] = 1
    reg.write_text(json.dumps(registration))
    with pytest.raises(BundleError, match="identity or scope"):
        prepare_hypothesis_source(
            registration_path=reg, data_root=data, implementation_commit=COMMIT
        )
    assert not path.exists()


def test_delivery_replays_the_exact_derived_predecessor_without_bundle_mock(tmp_path):
    from speech_aware_evidence_acquisition.core.bundle.delivery_replay import (
        SEALED_STATE_RESPONSE_PAIR_SCHEMA, replay_sealed_state_response_delivery,
    )
    from speech_aware_evidence_acquisition.rails.controllers import default_phase_program

    _reg, data, path, _registration, _receipt = _prepare(tmp_path)
    states = sealed_states_from_manifest(
        path, expected_sha256=_sha(path.read_bytes()), phase_name="slots",
        producer_policy_id=PRODUCER, sample_ids=("s1", "s2"),
    )
    program_id = "phase-slots-given-intent-v1"
    outputs, traces = [], {}
    for sid, state in states.items():
        state_history = {
            "turn": 1, "role": "agent_state",
            **{k: v for k, v in state.as_json().items() if k != "state_artifact_version"},
            "content_sha256": _sha(state.content.encode()),
        }
        contact_id = f"{program_id}:slots:{sid}"
        payload = {
            "request_id": sid + "-request", "sample_id": sid,
            "history": [state_history, {
                "turn": 2, "role": "control", "contact_id": contact_id,
                "content": "Respond.", "content_sha256": _sha(b"Respond."),
            }],
            "decoding_params": {"max_tokens": 256},
        }
        request = {"payload": payload, "payload_sha256": _sha(canonical_bytes(payload))}
        response = {
            "text": "synthetic final answer", "response_text_sha256": _sha(b"synthetic final answer"),
            "response_sha256": "2" * 64, "usage": {"completion_tokens": 4},
        }
        traces[sid + "-request/request"] = request
        traces[sid + "-request/response"] = response
        outputs.append({
            "request_id": sid + "-request", "sample_id": sid, "carrier_lock_key": "slurp",
            "arm": "test", "admitted": True, "request_sha256": request["payload_sha256"],
            **{key: response[key] for key in ("text", "response_sha256", "response_text_sha256")},
        })
    parent = VerifiedBundle(data / "parent.json", {"status": "COMPLETED"}, None,
                            tuple(outputs), traces, frozenset(states), "FINALIZED")
    source = {"manifest_relpath": str(path.relative_to(data)),
              "manifest_sha256": _sha(path.read_bytes()), "producer_policy_id": PRODUCER}
    values = {"policy": program_id, "phase_material": {"slots": {
        "instruction_template": "probes/unused.txt", "instruction_fill": None,
        "response_format_id": None, "predecessor_binding": "sealed-manifest",
        "predecessor_source": source,
    }}}
    declaration = {
        "cell_id": "derived-pair", "parent_cell_id": "parent",
        "response_postprocessor": "e21-free-refresh-delivery-v1",
        "response_postprocessor_params": {},
        "source_selector": {
            "schema": SEALED_STATE_RESPONSE_PAIR_SCHEMA, "program_id": program_id,
            "program_sha256": _sha(canonical_bytes(default_phase_program(program_id).as_json())),
            "response_phase": "slots",
        },
    }
    delivered, links = replay_sealed_state_response_delivery(
        parent, declaration, values, data_root=data
    )
    assert [row["text"] for row in delivered] == ["synthetic final answer"] * 2
    assert {row["sealed_state_sha256"] for row in links} == {
        state.content_hash() for state in states.values()
    }
