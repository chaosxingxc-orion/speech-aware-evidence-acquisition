"""External sealed-state response delivery uses the same state as generation."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.bundle import BundleError
from speech_aware_evidence_acquisition.core.bundle.artifacts import VerifiedBundle
from speech_aware_evidence_acquisition.core.bundle.delivery_replay import (
    SEALED_STATE_RESPONSE_PAIR_SCHEMA,
    canonical,
    replay_delivery,
    validate_phase_delivery_sources,
)
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.knowledge import AgentStateArtifact

PROGRAM_ID = "phase-slots-given-intent-v1"
SOURCE_POLICY = "phase-direct-only-v1"
SAMPLE_ID = "sample-1"


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _world(tmp_path: Path, *, saturated: bool = False):
    source_manifest = tmp_path / "source" / "manifest.json"
    source_manifest.parent.mkdir()
    source_manifest.write_text("{}", encoding="utf-8")
    source_text = "sealed first decision"
    source_row = {
        "sample_id": SAMPLE_ID,
        "text": source_text,
        "request_sha256": "1" * 64,
        "response_text_sha256": _sha(source_text.encode()),
    }
    predecessor = VerifiedBundle(
        source_manifest,
        {"status": "COMPLETED", "run_id": "source-run"},
        None,
        (source_row,),
        {
            f"{SAMPLE_ID}/{SOURCE_POLICY}/runtime-use": {
                "use_controller_policy_id": SOURCE_POLICY
            }
        },
        frozenset({SAMPLE_ID}),
        "FINALIZED",
    )
    state = AgentStateArtifact(
        state_id=f"slots:{SAMPLE_ID}",
        state_kind="phase:slots",
        content=source_text,
        source_query_state_sha256=source_row["request_sha256"],
        source_response_sha256=source_row["response_text_sha256"],
        producer_policy_id=SOURCE_POLICY,
        cited_value_ids=(),
    ).validate()
    state_history = {
        "turn": 1,
        "role": "agent_state",
        **{key: value for key, value in state.as_json().items() if key != "state_artifact_version"},
        "content_sha256": _sha(source_text.encode()),
    }
    control = {
        "turn": 2,
        "role": "control",
        "contact_id": f"{PROGRAM_ID}:slots:{SAMPLE_ID}",
        "content": "Respond.",
        "content_sha256": _sha(b"Respond."),
    }
    request_payload = {
        "request_id": "request-1",
        "sample_id": SAMPLE_ID,
        "history": [state_history, control],
        "decoding_params": {"max_tokens": 2},
    }
    request = {
        "payload": request_payload,
        "payload_sha256": _sha(canonical(request_payload)),
    }
    response_text = "second decision"
    response = {
        "text": response_text,
        "response_text_sha256": _sha(response_text.encode()),
        "response_sha256": "2" * 64,
        "usage": {"completion_tokens": 2 if saturated else 1},
    }
    output = {
        "request_id": "request-1",
        "sample_id": SAMPLE_ID,
        "carrier_lock_key": "slurp",
        "arm": "test",
        "text": response_text,
        "admitted": True,
        "request_sha256": request["payload_sha256"],
        "response_sha256": response["response_sha256"],
        "response_text_sha256": response["response_text_sha256"],
    }
    parent = VerifiedBundle(
        tmp_path / "parent.json",
        {"status": "COMPLETED"},
        None,
        (output,),
        {"request-1/request": request, "request-1/response": response},
        frozenset({SAMPLE_ID}),
        "FINALIZED",
    )
    source = {
        "manifest_relpath": "source/manifest.json",
        "manifest_sha256": _sha(source_manifest.read_bytes()),
        "producer_policy_id": SOURCE_POLICY,
    }
    values = {
        "policy": PROGRAM_ID,
        "phase_material": {
            "slots": {
                "instruction_template": "probes/unused.txt",
                "instruction_fill": None,
                "response_format_id": None,
                "predecessor_binding": "sealed-manifest",
                "predecessor_source": source,
            }
        },
    }
    program = default_phase_program(PROGRAM_ID)
    declaration = {
        "cell_id": "sealed-pair",
        "parent_cell_id": "parent",
        "response_postprocessor": "e21-free-refresh-delivery-v1",
        "response_postprocessor_params": {},
        "source_selector": {
            "schema": SEALED_STATE_RESPONSE_PAIR_SCHEMA,
            "program_id": PROGRAM_ID,
            "program_sha256": _sha(canonical(program.as_json())),
            "response_phase": "slots",
        },
    }
    return parent, predecessor, values, declaration


def test_replays_terminal_response_against_exact_external_sealed_state(
    tmp_path, monkeypatch
):
    parent, predecessor, values, declaration = _world(tmp_path)
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.bundle.verify.verify_bundle",
        lambda _path: predecessor,
    )
    rows, sources = replay_delivery(
        parent, None, declaration, values, data_root=tmp_path
    )
    assert rows[0]["text"] == "second decision"
    assert sources[0]["sealed_state_sha256"] == AgentStateArtifact.from_json(
        {
            "state_artifact_version": "knowledge-agent-state-artifact-v1",
            **{
                key: value
                for key, value in parent.trace_records["request-1/request"]["payload"][
                    "history"
                ][0].items()
                if key
                not in {"turn", "role", "content_sha256"}
            },
        }
    ).content_hash()
    assert sources[0]["response_saturated"] is False


def test_saturation_uses_common_delivery_normalization(tmp_path, monkeypatch):
    parent, predecessor, values, declaration = _world(tmp_path, saturated=True)
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.bundle.verify.verify_bundle",
        lambda _path: predecessor,
    )
    rows, sources = replay_delivery(
        parent, None, declaration, values, data_root=tmp_path
    )
    assert rows[0]["text"] == "sealed first decision"
    assert sources[0]["response_saturated"] is True
    assert sources[0]["normalized_response_sha256"] == _sha(b"")


def test_selector_is_validated_through_shared_delivery_declarations(tmp_path):
    _parent, _predecessor, values, declaration = _world(tmp_path)
    values["delivery_derivatives"] = [declaration]
    assert validate_phase_delivery_sources(values) == (declaration,)


def test_precontact_validation_refuses_missing_sealed_binding(tmp_path):
    _parent, _predecessor, values, declaration = _world(tmp_path)
    values["delivery_derivatives"] = [declaration]
    values["phase_material"]["slots"]["predecessor_binding"] = "none"
    values["phase_material"]["slots"]["predecessor_source"] = None
    with pytest.raises(BundleError, match="sealed manifest"):
        validate_phase_delivery_sources(values)


def test_delivery_rule_diagnostics_are_preserved(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core.base import RESPONSE_POSTPROCESSORS

    parent, predecessor, values, declaration = _world(tmp_path)
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.bundle.verify.verify_bundle",
        lambda _path: predecessor,
    )
    monkeypatch.setattr(
        RESPONSE_POSTPROCESSORS,
        "resolve",
        lambda _name: lambda **_params: lambda _predecessor, response: SimpleNamespace(
            text=response,
            refusal_reason=None,
            diagnostics={
                "attempted_intent_switch": True,
                "closed_shortlist_escape": False,
            },
        ),
    )
    _rows, sources = replay_delivery(
        parent, None, declaration, values, data_root=tmp_path
    )
    assert sources[0]["delivery_diagnostics"] == {
        "attempted_intent_switch": True,
        "closed_shortlist_escape": False,
    }


@pytest.mark.parametrize(
    "mutation",
    [
        "relative-escape",
        "changed-source-hash",
        "wrong-roster",
        "wrong-producer",
        "missing-state",
        "changed-state",
        "wrong-response-phase",
    ],
)
def test_refuses_foreign_missing_or_changed_external_source(
    tmp_path, monkeypatch, mutation
):
    parent, predecessor, values, declaration = _world(tmp_path)
    source = values["phase_material"]["slots"]["predecessor_source"]
    if mutation == "relative-escape":
        source["manifest_relpath"] = "../source/manifest.json"
    elif mutation == "changed-source-hash":
        source["manifest_sha256"] = "0" * 64
    elif mutation == "wrong-roster":
        predecessor = replace(predecessor, split_ids=frozenset({"foreign"}))
    elif mutation == "wrong-producer":
        predecessor = replace(
            predecessor,
            trace_records={"x/runtime-use": {"use_controller_policy_id": "foreign"}},
        )
    elif mutation == "missing-state":
        parent.trace_records["request-1/request"]["payload"]["history"].pop(0)
        parent.trace_records["request-1/request"]["payload_sha256"] = _sha(
            canonical(parent.trace_records["request-1/request"]["payload"])
        )
    elif mutation == "changed-state":
        parent.trace_records["request-1/request"]["payload"]["history"][0][
            "content"
        ] = "changed"
        parent.trace_records["request-1/request"]["payload"]["history"][0][
            "content_sha256"
        ] = _sha(b"changed")
        parent.trace_records["request-1/request"]["payload_sha256"] = _sha(
            canonical(parent.trace_records["request-1/request"]["payload"])
        )
    else:
        declaration["source_selector"]["response_phase"] = "missing"
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.bundle.verify.verify_bundle",
        lambda _path: predecessor,
    )
    with pytest.raises(BundleError):
        replay_delivery(parent, None, declaration, values, data_root=tmp_path)


def test_existing_phase_pair_and_legacy_dispatch_are_unchanged(monkeypatch):
    from speech_aware_evidence_acquisition.core.bundle import delivery_replay

    parent = object()
    declaration = {"source_selector": {"schema": "saea-phase-response-pair-v1"}}
    monkeypatch.setattr(
        delivery_replay,
        "replay_phase_pair_delivery",
        lambda actual, declared, values: ([actual], [declared, values]),
    )
    assert replay_delivery(parent, None, declaration, {"old": True}) == (
        [parent],
        [declaration, {"old": True}],
    )


def _control_state_parent(parent):
    from speech_aware_evidence_acquisition.rails.phase_material import _appended

    request = parent.trace_records["request-1/request"]
    history = request["payload"]["history"]
    state = AgentStateArtifact.from_json({
        "state_artifact_version": "knowledge-agent-state-artifact-v1",
        **{key: value for key, value in history[0].items()
           if key not in {"turn", "role", "content_sha256"}},
    })
    content = _appended("Respond.", state) + "\n\nCandidate contracts."
    control = {
        "turn": 1, "role": "control",
        "contact_id": f"{PROGRAM_ID}:slots:{SAMPLE_ID}",
        "content": content, "content_sha256": _sha(content.encode()),
    }
    request["payload"]["history"] = [control]
    request["payload_sha256"] = _sha(canonical(request["payload"]))
    parent.outputs_rows[0]["request_sha256"] = request["payload_sha256"]
    return control


def test_replay_accepts_exact_state_in_shared_control_instruction(tmp_path, monkeypatch):
    parent, predecessor, values, declaration = _world(tmp_path)
    control = _control_state_parent(parent)
    original = dict(control)
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.bundle.verify.verify_bundle",
        lambda _path: predecessor,
    )
    rows, sources = replay_delivery(parent, None, declaration, values, data_root=tmp_path)
    assert rows[0]["text"] == "second decision"
    assert sources[0]["sealed_state_sha256"]
    assert control == original


@pytest.mark.parametrize(
    "mutation",
    ["changed-state", "changed-content-hash", "wrong-contact", "duplicate-block", "unbounded-suffix"],
)
def test_replay_rejects_foreign_or_ambiguous_control_state(tmp_path, monkeypatch, mutation):
    parent, predecessor, values, declaration = _world(tmp_path)
    control = _control_state_parent(parent)
    if mutation == "changed-state":
        control["content"] = control["content"].replace("sealed first decision", "foreign decision")
    elif mutation == "changed-content-hash":
        control["content_sha256"] = "0" * 64
    elif mutation == "wrong-contact":
        control["contact_id"] = f"{PROGRAM_ID}:slots:foreign"
    elif mutation == "duplicate-block":
        control["content"] += "\n\nPrior phase response (phase:slots):\nsealed first decision"
    elif mutation == "unbounded-suffix":
        control["content"] = control["content"].replace(
            "sealed first decision\n\n", "sealed first decision forged\n\n"
        )
    if mutation != "changed-content-hash":
        control["content_sha256"] = _sha(control["content"].encode())
    request = parent.trace_records["request-1/request"]
    request["payload_sha256"] = _sha(canonical(request["payload"]))
    parent.outputs_rows[0]["request_sha256"] = request["payload_sha256"]
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.bundle.verify.verify_bundle",
        lambda _path: predecessor,
    )
    with pytest.raises(BundleError):
        replay_delivery(parent, None, declaration, values, data_root=tmp_path)
