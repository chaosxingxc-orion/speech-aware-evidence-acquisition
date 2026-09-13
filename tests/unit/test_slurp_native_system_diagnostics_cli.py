from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import pytest

import speech_aware_evidence_acquisition.analysis.slurp_topn_diagnostics_cli as cli
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.knowledge import AgentStateArtifact
from speech_aware_evidence_acquisition.rails.slurp_intent_hypotheses import (
    BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
    parse_slurp_intent_hypothesis_state,
)


def _pin(path: Path) -> dict[str, str]:
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def _write(path: Path, document: object) -> dict[str, str]:
    path.write_text(json.dumps(document), encoding="utf-8")
    return _pin(path)


def _candidate(intent_id: str) -> dict[str, object]:
    return {
        "intent_id": intent_id,
        "distinction": "synthetic distinction",
        "evidence_refs": [],
        "unresolved_fields": [],
    }


def _state(sample_id: str, candidate_ids: tuple[str, ...]) -> AgentStateArtifact:
    content = json.dumps(
        {"candidates": [_candidate(candidate_id) for candidate_id in candidate_ids]},
        sort_keys=True,
        separators=(",", ":"),
    )
    contact_id = f"native-policy:perception:0:{sample_id}"
    return AgentStateArtifact(
        state_id=f"{contact_id}:perception:{sample_id}",
        state_kind="phase:perception",
        content=content,
        source_query_state_sha256="a" * 64,
        source_response_sha256=hashlib.sha256(content.encode()).hexdigest(),
        producer_policy_id="native-policy",
        cited_value_ids=(),
    ).validate()


def _selection_audit(
    sample_id: str,
    state: AgentStateArtifact,
    legal_ids: frozenset[str],
) -> tuple[str, dict[str, object]]:
    parsed = parse_slurp_intent_hypothesis_state(
        state,
        expected_sample_id=sample_id,
        legal_intent_ids=legal_ids,
        max_candidates=3,
        compact_source_phase="perception",
        projection_policy=BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
    )
    audit = {
        "schema": "saea-candidate-semantic-selection-v1",
        "snapshot_sha256": "1" * 64,
        "sample_id": sample_id,
        "candidate_state_id": state.state_id,
        "candidate_state_sha256": hashlib.sha256(state.content.encode()).hexdigest(),
        "candidate_source_response_sha256": state.source_response_sha256,
        "candidate_ids": [candidate.intent_id for candidate in parsed.candidates],
        "legal_candidate_inventory_sha256": content_hash(
            {"candidate_ids": sorted(legal_ids)}
        ),
        "selection_policy_id": "saea-ranked-candidate-round-robin-v1",
        "max_candidates": 3,
        "max_values_per_candidate": 16,
        "max_total_values": 28,
        "mappings": [],
        "selected_value_ids": [],
        "compact_source_phase": "perception",
        "candidate_projection": json.loads(json.dumps(asdict(parsed.projection))),
    }
    audit["selection_sha256"] = content_hash(audit)
    audit.update(
        store_id="slot-contracts",
        store_role="slot-contracts",
        store_snapshot_sha256="2" * 64,
        store_release_sha256="3" * 64,
        store_source_sha256="4" * 64,
        composite_snapshot_sha256="5" * 64,
        query_state_sha256="6" * 64,
        qualified_selected_value_ids=[],
        supply_disposition="no-mapping",
    )
    audit["selection_receipt_sha256"] = content_hash(audit)
    return f"solver:{sample_id}:{audit['query_state_sha256']}", audit


def _stage(name: str, **values: object) -> dict[str, object]:
    result = {**values, "stage": name}
    result["stage_hash"] = content_hash(result)
    return result


def _native_fixture(
    tmp_path: Path,
    *,
    defect: str | None = None,
    with_flight_receipts: bool = False,
):
    ids = ("s1", "s2")
    legal_ids = frozenset({"a_x", "b_y", "c_z"})
    states = {
        "s1": _state("s1", ("a_x", "b_y", "a_x")),
        "s2": _state("s2", ("b_y",)),
    }
    audit_states = dict(states)
    if defect == "wrong_phase":
        states["s2"] = AgentStateArtifact.from_json(
            {**states["s2"].as_json(), "state_kind": "phase:planner"}
        )
    elif defect == "wrong_source":
        states["s2"] = AgentStateArtifact.from_json(
            {**states["s2"].as_json(), "source_response_sha256": "f" * 64}
        )
    elif defect == "wrong_sample":
        states["s2"] = AgentStateArtifact.from_json(
            {**states["s2"].as_json(), "state_id": "native-policy:perception:0:s2:perception:foreign"}
        )
    outputs = {
        "s1": '{"scenario":"a","action":"x","entities":[]}',
        "s2": '{"scenario":"b","action":"y","entities":[]}',
    }
    episode = {
        "role_visits": [], "planner_routes": [], "accepted_solver_receipt": {}
    }
    results = []
    output_rows = []
    trace_records = {}
    for sample_id in ids:
        state = states[sample_id]
        contact_id = f"native-policy:perception:0:{sample_id}"
        request_id = f"rails-{sample_id}"
        instruction = f"perception instruction for {sample_id}"
        request_sha256 = hashlib.sha256(f"request:{sample_id}".encode()).hexdigest()
        response_sha256 = hashlib.sha256(f"wire:{sample_id}".encode()).hexdigest()
        trace_records.update(
            {
                f"{request_id}/request": {
                    "payload": {
                        "request_id": request_id,
                        "sample_id": sample_id,
                        "history": [
                            {
                                "role": "control",
                                "contact_id": contact_id,
                                "content": instruction,
                            }
                        ],
                    },
                    "payload_sha256": request_sha256,
                },
                f"{request_id}/response": {
                    "text": state.content,
                    "response_sha256": response_sha256,
                    "response_text_sha256": state.source_response_sha256,
                },
                f"{request_id}/native-role-contact": {
                    "use_role_id": "perception",
                    "use_agent_contact_id": contact_id,
                    "use_request_sha256": request_sha256,
                    "use_response_sha256": response_sha256,
                    "use_response_text_sha256": state.source_response_sha256,
                },
            }
        )
        if defect == "wrong_trace" and sample_id == "s2":
            trace_records[f"{request_id}/response"]["text"] = "changed"
        elif defect == "wrong_trace_role" and sample_id == "s2":
            trace_records[f"{request_id}/native-role-contact"][
                "use_role_id"
            ] = "solver"
        results.append(
            {
                "sample_id": sample_id,
                "final_response_text": outputs[sample_id],
                "final_response_sha256": hashlib.sha256(outputs[sample_id].encode()).hexdigest(),
                "contacts": [
                    {
                        "plan": {
                            "contact_id": contact_id,
                            "query_state_sha256": state.source_query_state_sha256,
                            "instruction": instruction,
                        },
                        "query_state_sha256": state.source_query_state_sha256,
                        "response_sha256": (
                            "e" * 64 if defect == "wrong_contact" and sample_id == "s2"
                            else state.source_response_sha256
                        ),
                    }
                ],
                "agent_states": [state.as_json()],
                "native_episode_receipt": episode,
            }
        )
        output_rows.append(
            {
                "sample_id": sample_id,
                "text": outputs[sample_id],
                "native_episode_receipt": episode,
            }
        )
    protocol_hash = "7" * 64
    phases = {
        "schema": "saea-flight-phase-summaries-v1",
        "run_id": "native-run",
        "attempt_id": "native-attempt",
        "policy": "native-policy",
        "phases": [
            {
                "run_id": "native-run",
                "protocol_hash": protocol_hash,
                "controller_policy_id": "native-policy",
                "results": results,
            }
        ],
    }
    phase_path = tmp_path / "native-run.phases.json"
    phase_pin = _write(phase_path, phases)
    audits = dict(
        _selection_audit(sample_id, audit_states[sample_id], legal_ids)
        for sample_id in ids
    )
    candidate_supply = {
        "schema": "saea-candidate-semantic-supply-v1",
        "candidate_inventory_authority": "task-adapter-candidate-contract-provider",
        "specs": [
            {
                "phase": "solver",
                "store_id": "slot-contracts",
                "provider": "slurp-candidate-semantic-v1",
                "rank_policy": "saea-ranked-candidate-round-robin-v1",
                "fuse_policy": "saea-candidate-semantic-passthrough-v1",
                "candidate_state_phase": "perception",
                "compact_source_phase": "perception",
                "projection_policy": BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
                "max_candidates": 3,
            }
        ],
        "candidate_inventory_count": len(legal_ids),
        "candidate_inventory_sha256": content_hash(
            {"candidate_ids": sorted(legal_ids)}
        ),
        "candidate_selections": audits,
    }
    phase_supply = {
        "schema": "saea-named-knowledge-store-routing-v1",
        "stores": {
            "slot-contracts": {
                "store_id": "slot-contracts",
                "store_role": "slot-contracts",
                "store_snapshot_sha256": "2" * 64,
                "store_release_sha256": "3" * 64,
                "store_source_sha256": "4" * 64,
                "composite_snapshot_sha256": "5" * 64,
            }
        },
        "candidate_supply": candidate_supply,
        "candidate_selections": audits,
    }
    if defect == "wrong_store_id":
        candidate_supply["specs"][0]["store_id"] = "different-store"
        phase_supply["stores"]["different-store"] = {
            **phase_supply["stores"]["slot-contracts"],
            "store_id": "different-store",
        }
    elif defect == "wrong_store_binding":
        phase_supply["stores"]["slot-contracts"]["store_release_sha256"] = "9" * 64
    receipts = {
        "schema": "saea-flight-receipts-v1",
        "run_id": "native-run",
        "attempt_id": "native-attempt",
        "stages": {
            "run_phases": _stage("run_phases", phase_supply=phase_supply),
            "seal": _stage(
                "seal", phases_path=str(phase_path), phases_sha256=phase_pin["sha256"]
            ),
        },
    }
    receipts["receipts_hash"] = content_hash(receipts)
    flight_pin = _write(tmp_path / "flight-receipts.json", receipts)
    manifest_path = tmp_path / "native-run.run-manifest.json"
    manifest_pin = _write(manifest_path, {"synthetic": True})
    split_hash = split_identity_hash(prefixed("slurp", ids))
    bundle = SimpleNamespace(
        manifest_path=manifest_path,
        manifest={
            "status": "COMPLETED",
            "run_id": "native-run",
            "plan": {"attempt_id": "native-attempt", "protocol_hash": protocol_hash},
            "split": {"identity_hash": split_hash},
        },
        attempt_state="FINALIZED",
        split_ids=frozenset(ids),
        outputs_rows=tuple(output_rows),
        trace_records=trace_records,
    )
    score_pin = {**_write(tmp_path / "score-receipt.json", {}), "cell_id": "system"}
    unused_pin = {"path": str(tmp_path / "unused"), "sha256": "0" * 64}
    config = {
        "experiment_id": "synthetic-native-diagnostics",
        "execution_profile": "model-free-check",
        "analysis": {
            "full_roster": unused_pin,
            "roster": unused_pin,
            "metadata": unused_pin,
            "source_diagnostics": {
                "native_system_perception_source": {
                    "manifest": manifest_pin,
                    "phase_artifact": phase_pin,
                    "split_identity_hash": split_hash,
                    "candidate_count_range": [1, 3],
                    "producer_policy_id": "native-policy",
                    "compact_source_phase": "perception",
                    "candidate_selection_phase": "solver",
                    "projection_policy": BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
                },
                "reference_source": {
                    "kind": "slurp-split",
                    "split_id": "devel",
                    "split_identity_hash": split_hash,
                    "lock": _write(tmp_path / "lock.json", {}),
                    "data_root": str(tmp_path),
                },
            },
            "inputs": {
                "system": {
                    "manifest": manifest_pin,
                    "score_receipt": score_pin,
                }
            },
        },
    }
    if with_flight_receipts:
        config["analysis"]["source_diagnostics"][
            "native_system_perception_source"
        ]["flight_receipts"] = flight_pin
    if defect == "phase_hash":
        phase_path.write_text(phase_path.read_text() + " ", encoding="utf-8")
    return ids, legal_ids, config, bundle


def test_native_mode_reads_internal_perception_and_reports_actual_width(tmp_path, monkeypatch):
    ids, legal_ids, config, bundle = _native_fixture(tmp_path)
    config_path = tmp_path / "analysis.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setattr(
        cli,
        "_roster_ids",
        lambda _value, label: ids if label.endswith("full_roster") else (ids[0],),
    )
    monkeypatch.setattr(
        cli,
        "_metadata",
        lambda *_args: {sample_id: {"scenario": "synthetic"} for sample_id in ids},
    )
    result = cli.run(
        config_path,
        tmp_path / "report.json",
        bundle_verifier=lambda _path: bundle,
        score_receipt_verifier=lambda _ref, _bundle: {"verified": True},
        candidate_contract_loader=lambda *_args: SimpleNamespace(
            candidate_ids=tuple(sorted(legal_ids))
        ),
        reference_loader=lambda *_args, **_kwargs: [
            SimpleNamespace(sample_id="s1", intent="a_x"),
            SimpleNamespace(sample_id="s2", intent="a_x"),
        ],
    )
    pooled = result["diagnostics"]["DEV1000"]
    assert result["source"]["binding_name"] == "native_system_perception_source"
    assert set(pooled["by_observed_distinct_width"]) == {"1", "2"}
    assert pooled["source"]["topn_included"] == 1
    assert pooled["branches"]["system"]["candidate_present_final_correct"] == 1
    assert result["source"]["candidate_source"]["status"] == (
        "verified-source-derived-projection"
    )
    assert result["source"]["actual_candidate_supply"]["status"] == "unavailable"
    assert (
        result["source"]["actual_candidate_supply"]["candidate_selection_audits"]
        is None
    )
    assert result["diagnostic_semantics"]["rank1_rescues_harms"].endswith(
        "system Perception rank one"
    )


def test_native_mode_verifies_actual_supply_from_genuine_flight_receipts(tmp_path):
    ids, legal_ids, config, bundle = _native_fixture(
        tmp_path, with_flight_receipts=True
    )
    source = config["analysis"]["source_diagnostics"]["native_system_perception_source"]

    rows, branches, receipt = cli._native_system_rows(
        source, bundle, ids, legal_ids=legal_ids
    )

    assert [row.candidate_ids for row in rows] == [("a_x", "b_y"), ("b_y",)]
    assert len(branches) == 2
    assert receipt["actual_candidate_supply"]["status"] == "verified"
    assert receipt["actual_candidate_supply"]["candidate_selection_audits"] == 2


@pytest.mark.parametrize(
    "defect,match",
    [
        ("wrong_phase", "exactly one Perception"),
        ("wrong_source", "source response SHA-256"),
        ("wrong_contact", "source contact mismatch"),
        ("wrong_sample", "configured phase and sample_id"),
        ("wrong_trace", "differs from manifest-verified trace"),
        ("wrong_trace_role", "differs from manifest-verified trace"),
        ("phase_hash", "phase artifact hash mismatch"),
    ],
)
def test_native_source_refuses_phase_source_contact_sample_and_artifact_hash(
    tmp_path, defect, match
):
    ids, legal_ids, config, bundle = _native_fixture(tmp_path, defect=defect)
    source = config["analysis"]["source_diagnostics"]["native_system_perception_source"]
    with pytest.raises(cli.SlurpTopNAnalysisError, match=match):
        cli._native_system_rows(source, bundle, ids, legal_ids=legal_ids)


@pytest.mark.parametrize("defect", ("wrong_store_id", "wrong_store_binding"))
def test_native_actual_supply_refuses_candidate_spec_or_store_disagreement(
    tmp_path, defect
):
    ids, legal_ids, config, bundle = _native_fixture(
        tmp_path, defect=defect, with_flight_receipts=True
    )
    source = config["analysis"]["source_diagnostics"]["native_system_perception_source"]

    with pytest.raises(
        cli.SlurpTopNAnalysisError,
        match="candidate audit lacks released-store provenance",
    ):
        cli._native_system_rows(source, bundle, ids, legal_ids=legal_ids)
