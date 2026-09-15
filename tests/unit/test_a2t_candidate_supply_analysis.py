"""Receipt-bound Audio2Tool candidate attribution without outcome reads."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_candidate_supply import (
    A2TCandidateSupplyError,
    analyze_a2t_candidate_supply,
)
from speech_aware_evidence_acquisition.analysis.native_episode_source import (
    VerifiedNativeEpisodeSource,
)
from speech_aware_evidence_acquisition.core.bundle.artifacts import VerifiedBundle
from speech_aware_evidence_acquisition.core.config import ComposedConfig
from speech_aware_evidence_acquisition.core.flight.receipts import FlightReceipts
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.knowledge import (
    AgentStateArtifact,
    AgentStepTransition,
    FusionDecision,
    KeyFacet,
    KnowledgeSnapshot,
    QueryState,
    RankedFacet,
    RankResult,
    ValueBundle,
)
from speech_aware_evidence_acquisition.rails.task_adapter import CandidateInventory


_STORE_FIELDS = {
    "store_id": "parameter-meaning",
    "store_role": "parameter-meaning",
    "store_release_sha256": "2" * 64,
    "store_source_sha256": "3" * 64,
    "composite_snapshot_sha256": "4" * 64,
}


def _action(index: int, names: tuple[str, ...]) -> dict[str, object]:
    return {
        "action_id": f"action:{index}",
        "candidate_tools": list(names),
        "evidence": "Evidence from the bound speech.",
        "uncertain_arguments": [],
    }


def _spec() -> dict[str, object]:
    return {
        "candidate_state_phase": "perception",
        "compact_source_phase": "perception",
        "fuse_policy": "saea-candidate-semantic-passthrough-v1",
        "max_actions": 8,
        "max_candidates_per_action": 4,
        "max_total_values": 32,
        "max_values_per_candidate": 1,
        "provider": "audio2tool-candidate-semantic-v1",
        "rank_policy": "saea-ranked-candidate-round-robin-v1",
    }


def _inventory() -> CandidateInventory:
    return CandidateInventory(
        candidate_ids=("alpha", "beta", "gamma"),
        source_sha256="9" * 64,
        source_authority="audio2tool-public-tool-registry",
    )


def _provider_audit(
    *, sample_id: str, state: AgentStateArtifact, actions: list[dict[str, object]],
    store_fields: dict[str, object],
) -> dict[str, object]:
    candidate_ids = list(dict.fromkeys(
        name for action in actions for name in action["candidate_tools"]
    ))
    mappings = [
        {
            "candidate_id": candidate_id,
            "mapped_value_ids": [f"card:{candidate_id}:value"],
            "selected_value_ids": [f"card:{candidate_id}:value"],
            "ignored_mappings": [],
            "status": "mapped",
        }
        for candidate_id in candidate_ids
    ]
    body = {
        "schema": "saea-candidate-semantic-selection-v1",
        "snapshot_sha256": store_fields["store_snapshot_sha256"],
        "sample_id": sample_id,
        "candidate_state_id": state.state_id,
        "candidate_state_sha256": hashlib.sha256(state.content.encode()).hexdigest(),
        "candidate_source_response_sha256": state.source_response_sha256,
        "candidate_ids": candidate_ids,
        "legal_candidate_inventory_sha256": content_hash(
            {"candidate_ids": sorted(_inventory().candidate_ids)}
        ),
        "selection_policy_id": "saea-ranked-candidate-round-robin-v1",
        "max_actions": 8,
        "max_candidates_per_action": 4,
        "max_values_per_candidate": 1,
        "max_total_values": 32,
        "mappings": mappings,
        "selected_value_ids": [f"card:{name}:value" for name in candidate_ids],
        "compact_source_phase": "perception",
        "candidate_occurrences": [
            {
                "action_id": action["action_id"],
                "candidate_tools": action["candidate_tools"],
            }
            for action in actions
        ],
    }
    return {**body, "selection_sha256": content_hash(body)}


def _selection(
    *, sample_id: str, state: AgentStateArtifact, actions: list[dict[str, object]],
    query_sha256: str, disposition: str, store_fields: dict[str, object],
) -> dict[str, object]:
    provider = _provider_audit(
        sample_id=sample_id, state=state, actions=actions, store_fields=store_fields
    )
    selected = provider["selected_value_ids"]
    receipt = {
        **provider,
        **store_fields,
        "candidate_inventory_source_sha256": _inventory().source_sha256,
        "candidate_inventory_authority": _inventory().source_authority,
        "query_state_sha256": query_sha256,
        "qualified_selected_value_ids": [
            f"parameter-meaning::{value_id}" for value_id in selected
        ],
        "supply_disposition": disposition,
    }
    receipt["selection_receipt_sha256"] = content_hash(receipt)
    return receipt


def _fixture(
    tmp_path: Path, *, actions: list[dict[str, object]] | None = None,
    solver_queries: tuple[str, ...] = ("d" * 64,),
) -> tuple[VerifiedNativeEpisodeSource, dict[str, object], CandidateInventory]:
    sample_id = "tier1_direct:000001"
    actions = [_action(0, ("alpha", "beta"))] if actions is None else actions
    source_id = "public-registry"
    facets = tuple(
        KeyFacet(
            facet_id=f"facet:{name}", dimension="content", representation_kind="text",
            representation=f"Parameter guidance for {name}.",
            source_sample_ids=(source_id,),
        ).validate()
        for name in _inventory().candidate_ids
    )
    snapshot = KnowledgeSnapshot(
        snapshot_id="parameter-meaning", source_partition_role="external-governed",
        source_split_identity_hash="1" * 64, source_sample_ids=(source_id,),
        builder_policy_id="fixture", facets=facets,
        values=tuple(
            ValueBundle(
                value_id=f"card:{name}:value", content=f"Use the {name} parameters.",
                associated_facet_ids=(f"facet:{name}",),
                source_sample_ids=(source_id,), provenance_refs=("fixture",),
                task_target=name,
            ).validate()
            for name in _inventory().candidate_ids
        ),
    ).validate()
    snapshot_path = tmp_path / "prepared" / "snapshot.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(json.dumps(snapshot.frozen_json()), encoding="utf-8")
    store_fields = {**_STORE_FIELDS, "store_snapshot_sha256": snapshot.content_hash()}
    content = json.dumps({"actions": actions, "global_constraints": ["Keep order."]})
    text_sha = hashlib.sha256(content.encode()).hexdigest()
    perception_contact_id = f"policy:perception:0:{sample_id}"
    initial_query = QueryState(
        query_id=f"query:initial:{sample_id}", query_sample_id=sample_id,
        speech_packet_id=f"packet:{sample_id}", speech_packet_sha256="a" * 64,
        use_split_identity_hash="b" * 64,
    ).validate()
    perception_query = initial_query.content_hash()
    perception_request_id = "request-perception"
    perception_final = {
        "agent_contact_id": perception_contact_id,
        "request_id": perception_request_id,
        "request_sha256": "b" * 64,
        "response_sha256": "c" * 64,
        "response_text_sha256": text_sha,
    }
    state = AgentStateArtifact(
        state_id=f"{perception_contact_id}:perception:{sample_id}",
        state_kind="phase:perception", content=content,
        source_query_state_sha256=perception_query,
        source_response_sha256=text_sha, producer_policy_id="policy",
        cited_value_ids=(),
    ).validate()
    perception_visit = {
        "role_id": "perception", "stage": "perception",
        "execution_receipt": {"contacts": [perception_final], "final_contact": perception_final},
    }
    phase_contacts = [{
        "plan": {"contact_id": perception_contact_id,
                 "query_state_sha256": perception_query},
        "query_state_sha256": perception_query, "response_sha256": text_sha,
    }]
    visits = [perception_visit]
    selections: dict[str, object] = {}
    transitions: list[dict[str, object]] = []
    waves: list[dict[str, object]] = []
    current_query = initial_query
    qualified = [
        f"parameter-meaning::card:{name}:value"
        for name in dict.fromkeys(
            name for action in actions for name in action["candidate_tools"]
        )
    ]
    supporting = tuple(
        f"parameter-meaning::facet:{name}"
        for name in dict.fromkeys(
            name for action in actions for name in action["candidate_tools"]
        )
    )
    for index, _requested_hash in enumerate(solver_queries):
        audit_query_hash = current_query.content_hash()
        disposition = "acquired" if index == 0 and actions else (
            "already-visible" if actions else "no-mapping"
        )
        audit = _selection(
            sample_id=sample_id, state=state, actions=actions,
            query_sha256=audit_query_hash, disposition=disposition,
            store_fields=store_fields,
        )
        selections[f"solver:{sample_id}:{audit_query_hash}"] = audit
        next_state_ids = current_query.agent_state_ids + (
            state.state_id if index == 0 else f"revision-state:{index}:{sample_id}",
        )
        next_query = QueryState(
            query_id=f"query:solver:{index}:{sample_id}", query_sample_id=sample_id,
            speech_packet_id=current_query.speech_packet_id,
            speech_packet_sha256=current_query.speech_packet_sha256,
            use_split_identity_hash=current_query.use_split_identity_hash,
            loop_step=current_query.loop_step + 1,
            agent_state_ids=next_state_ids,
            retrieved_value_ids=tuple(qualified),
            visible_facet_ids=supporting,
        ).validate()
        target = (
            "knowledge-store:parameter-meaning:audio2tool-candidate-semantic-v1:"
            "saea-ranked-candidate-round-robin-v1:"
            "saea-candidate-semantic-passthrough-v1:selection-receipt="
            f"{audit['selection_receipt_sha256']}"
        )
        transition = AgentStepTransition(
            snapshot_sha256=store_fields["composite_snapshot_sha256"],
            prior_query_state_sha256=audit_query_hash,
            next_query_state_sha256=next_query.content_hash(),
            action_kind="acquire" if disposition == "acquired" else "organize",
            action_target_refs=(
                (f"state:{next_state_ids[-1]}", target)
                if disposition == "acquired" else (f"state:{next_state_ids[-1]}",)
            ),
            new_value_ids=tuple(qualified) if disposition == "acquired" else (),
            used_value_ids=(), dropped_value_ids=(),
            new_agent_state_ids=(next_state_ids[-1],), dropped_agent_state_ids=(),
            new_facet_ids=supporting if disposition == "acquired" else (),
        ).validate()
        rank = None
        fusion = None
        if disposition == "acquired":
            rank = RankResult(
                snapshot_sha256=store_fields["composite_snapshot_sha256"],
                query_state_sha256=audit_query_hash,
                ranking_policy_id="saea-ranked-candidate-round-robin-v1",
                candidates=tuple(
                    RankedFacet(facet_id=facet_id, score=float(len(supporting) - position))
                    for position, facet_id in enumerate(supporting)
                ),
            ).validate()
            fusion = FusionDecision(
                snapshot_sha256=store_fields["composite_snapshot_sha256"],
                query_state_sha256=audit_query_hash,
                rank_result_sha256=rank.content_hash(),
                fusion_policy_id="saea-candidate-semantic-passthrough-v1",
                supporting_facet_ids=supporting,
                selected_value_ids=tuple(qualified),
            ).validate()
        transitions.append(transition.as_json())
        waves.append({
            "query_state_sha256": audit_query_hash,
            "next_query_state_sha256": next_query.content_hash(),
            "transition": transition.as_json(),
            "rank_result": None if rank is None else rank.as_json(),
            "fusion_decision": None if fusion is None else fusion.as_json(),
        })
        query_hash = next_query.content_hash()
        solver_contact_id = f"policy:solver:{index}:{sample_id}"
        solver_final = {
            "agent_contact_id": solver_contact_id,
            "request_id": f"request-solver-{index}",
            "request_sha256": "e" * 64, "response_sha256": "f" * 64,
            "response_text_sha256": "0" * 64,
        }
        visits.append({
            "role_id": "solver", "stage": "solver",
            "execution_receipt": {"contacts": [solver_final], "final_contact": solver_final},
        })
        phase_contacts.append({
            "plan": {"contact_id": solver_contact_id, "query_state_sha256": query_hash},
            "query_state_sha256": query_hash, "response_sha256": "0" * 64,
        })
        current_query = next_query
    transitions.append(AgentStepTransition(
        snapshot_sha256=store_fields["composite_snapshot_sha256"],
        prior_query_state_sha256=current_query.content_hash(),
        next_query_state_sha256=None, action_kind="stop", action_target_refs=(),
        new_value_ids=(), used_value_ids=(), dropped_value_ids=(),
        new_agent_state_ids=(), dropped_agent_state_ids=(),
    ).validate().as_json())
    result = {
        "sample_id": sample_id, "agent_states": [state.as_json()],
        "contacts": phase_contacts, "initial_query_state": initial_query.as_json(),
        "final_query_state": current_query.as_json(),
        "transitions": transitions, "waves": waves,
        "native_episode_receipt": {
            "role_visits": visits, "planner_routes": [],
            "accepted_solver_receipt": visits[-1]["execution_receipt"],
        },
    }
    traces = {
        f"{perception_request_id}/request": {
            "payload": {"request_id": perception_request_id, "sample_id": sample_id},
            "payload_sha256": perception_final["request_sha256"],
        },
        f"{perception_request_id}/response": {
            "text": content, "response_sha256": perception_final["response_sha256"],
            "response_text_sha256": text_sha,
        },
        f"{perception_request_id}/native-role-contact": {
            "use_role_id": "perception", "use_agent_contact_id": perception_contact_id,
            "use_request_sha256": perception_final["request_sha256"],
            "use_response_sha256": perception_final["response_sha256"],
            "use_response_text_sha256": text_sha,
        },
    }
    values = {"knowledge_stores": {"parameter-meaning": {
        "store_role": "parameter-meaning", "candidate_supply": {"solver": _spec()},
        "snapshot": {
            "relpath": "prepared/snapshot.json", "sha256": snapshot.content_hash(),
        },
    }}}
    bundle = VerifiedBundle(
        manifest_path=Path("manifest.json"), manifest={}, outputs_path=None,
        outputs_rows=(), trace_records=traces, split_ids=frozenset({sample_id}),
        attempt_state="FINALIZED",
    )
    source = VerifiedNativeEpisodeSource(
        bundle=bundle,
        composed=ComposedConfig(values=values, config_hash="8" * 64, fragments={}),
        plan=SimpleNamespace(run_id="run-a", attempt_id="attempt-a"),
        sample_ids=(sample_id,), phase_results={sample_id: result}, output_rows={},
        phase_artifact_sha256="7" * 64, diagnostics={},
    )
    receipt_spec = {"phase": "solver", "store_id": "parameter-meaning", **_spec()}
    store = {**store_fields, "candidate_supply": [receipt_spec], "phase_supply": None}
    candidate_supply = {
        "schema": "saea-candidate-semantic-supply-v1", "specs": [receipt_spec],
        "candidate_inventory_authority": _inventory().source_authority,
        "candidate_inventory_count": len(_inventory().candidate_ids),
        "candidate_inventory_sha256": content_hash(
            {"candidate_ids": sorted(_inventory().candidate_ids)}
        ),
        "candidate_inventory_source_sha256": _inventory().source_sha256,
        "candidate_selections": selections,
    }
    phase_supply = {
        "schema": "saea-named-knowledge-store-routing-v1",
        "binding_sha256": "6" * 64, "stores": {"parameter-meaning": store},
        "candidate_supply": candidate_supply,
        "candidate_selections": deepcopy(selections),
    }
    receipts = FlightReceipts("run-a", "attempt-a")
    for stage, payload in (
        ("preflight", {}), ("preprocess", {}), ("serve", {}),
        ("run_phases", {"phase_supply": phase_supply}),
    ):
        receipts.record(stage, payload)
    return source, receipts.as_json(), _inventory()


def _rehash_selection(audit: dict[str, object]) -> None:
    unsigned = dict(audit)
    unsigned.pop("selection_receipt_sha256", None)
    audit["selection_receipt_sha256"] = content_hash(unsigned)


def _rehash_provider_and_selection(audit: dict[str, object]) -> None:
    provider_keys = {
        "schema", "snapshot_sha256", "sample_id", "candidate_state_id",
        "candidate_state_sha256", "candidate_source_response_sha256",
        "candidate_ids", "legal_candidate_inventory_sha256",
        "selection_policy_id", "max_actions", "max_candidates_per_action",
        "max_values_per_candidate", "max_total_values", "mappings",
        "selected_value_ids", "compact_source_phase", "candidate_occurrences",
    }
    audit["selection_sha256"] = content_hash({
        key: value for key, value in audit.items() if key in provider_keys
    })
    _rehash_selection(audit)


def test_reports_repeated_action_occurrences_and_deduplicates_revision_candidates(tmp_path):
    actions = [_action(0, ("alpha", "beta")), _action(1, ("alpha", "gamma"))]
    source, receipts, inventory = _fixture(
        tmp_path,
        actions=actions, solver_queries=("d" * 64, "e" * 64)
    )
    first_audit = next(iter(
        receipts["stages"]["run_phases"]["phase_supply"]
        ["candidate_selections"].values()
    ))
    first_solver = source.phase_results["tier1_direct:000001"]["contacts"][1]
    assert first_audit["query_state_sha256"] != first_solver["query_state_sha256"]
    report = analyze_a2t_candidate_supply(
        source, flight_receipts=receipts, candidate_inventory=inventory,
        data_root=tmp_path,
    )
    row = report["samples"][0]
    assert report["source_sample_ids"] == ["tier1_direct:000001"]
    assert row["candidate_state_status"] == "observed"
    assert row["action_count"] == 2
    assert row["per_action_candidate_widths"] == [2, 2]
    assert row["unique_candidate_ids"] == ["alpha", "beta", "gamma"]
    assert row["actions"] == [
        {"action_id": "action:0", "candidate_tools": ["alpha", "beta"],
         "candidate_width": 2},
        {"action_id": "action:1", "candidate_tools": ["alpha", "gamma"],
         "candidate_width": 2},
    ]
    assert row["selection"]["selection_count"] == 2
    assert row["selection"]["supply_dispositions"] == {
        "acquired": 1, "already-visible": 1,
    }
    assert row["selection"]["mapped_candidate_count"] == 3
    assert row["selection"]["mapping_coverage"] == 1.0
    assert report["summary"]["unique_candidate_observation_count"] == 3


def test_missing_selection_is_unavailable_but_valid_empty_state_is_observed(tmp_path):
    empty_source, empty_receipts, inventory = _fixture(tmp_path / "empty", actions=[])
    empty = analyze_a2t_candidate_supply(
        empty_source, flight_receipts=empty_receipts, candidate_inventory=inventory,
        data_root=tmp_path / "empty",
    )["samples"][0]
    assert empty["candidate_state_status"] == "observed"
    assert empty["actions"] == []
    assert empty["unique_candidate_ids"] == []
    assert empty["selection"]["status"] == "available"
    assert empty["selection"]["selection_count"] == 1
    assert empty["selection"]["mapping_coverage"] is None

    source, receipts, inventory = _fixture(tmp_path / "missing")
    supply = receipts["stages"]["run_phases"]["phase_supply"]
    supply["candidate_selections"] = {}
    supply["candidate_supply"]["candidate_selections"] = {}
    missing = analyze_a2t_candidate_supply(
        source, flight_receipts=receipts, candidate_inventory=inventory,
        data_root=tmp_path / "missing",
    )["samples"][0]
    assert missing["candidate_state_status"] == "observed"
    assert missing["selection"] == {
        "status": "unavailable",
        "missing_reason": "candidate selection receipt is missing",
        "selection_count": 0, "supply_dispositions": {},
        "store_id": "parameter-meaning", "store_role": "parameter-meaning",
        "selected_value_ids": None, "qualified_selected_value_ids": None,
        "mappings": None, "mapped_candidate_ids": None,
        "absent_candidate_ids": None, "mapped_candidate_count": None,
        "absent_candidate_count": None, "mapping_coverage": None,
    }


@pytest.mark.parametrize(
    "defect, match",
    [("sample", "sample"), ("state", "state"), ("response-hash", "response")],
)
def test_rejects_wrong_sample_state_or_response_hash(tmp_path, defect, match):
    source, receipts, inventory = _fixture(tmp_path)
    supply = receipts["stages"]["run_phases"]["phase_supply"]
    audit = next(iter(supply["candidate_selections"].values()))
    nested = next(iter(supply["candidate_supply"]["candidate_selections"].values()))
    if defect == "sample":
        audit["sample_id"] = nested["sample_id"] = "foreign"
        _rehash_selection(audit)
        _rehash_selection(nested)
    elif defect == "state":
        audit["candidate_state_id"] = nested["candidate_state_id"] = "foreign-state"
        _rehash_provider_and_selection(audit)
        _rehash_provider_and_selection(nested)
    else:
        source.bundle.trace_records["request-perception/response"][
            "response_text_sha256"
        ] = "5" * 64
    with pytest.raises(A2TCandidateSupplyError, match=match):
        analyze_a2t_candidate_supply(
            source, flight_receipts=receipts, candidate_inventory=inventory,
            data_root=tmp_path,
        )


@pytest.mark.parametrize("defect", ("hash", "source", "authority"))
def test_rejects_wrong_public_inventory_binding(tmp_path, defect):
    source, receipts, inventory = _fixture(tmp_path)
    candidate = receipts["stages"]["run_phases"]["phase_supply"]["candidate_supply"]
    if defect == "hash":
        candidate["candidate_inventory_sha256"] = "0" * 64
    elif defect == "source":
        candidate["candidate_inventory_source_sha256"] = "0" * 64
    else:
        candidate["candidate_inventory_authority"] = "another-authority"
    with pytest.raises(A2TCandidateSupplyError, match="inventory"):
        analyze_a2t_candidate_supply(
            source, flight_receipts=receipts, candidate_inventory=inventory,
            data_root=tmp_path,
        )


def test_rejects_configured_bound_or_mirrored_selection_substitution(tmp_path):
    source, receipts, inventory = _fixture(tmp_path / "bounds")
    source.composed.values["knowledge_stores"]["parameter-meaning"][
        "candidate_supply"
    ]["solver"]["max_actions"] = 7
    with pytest.raises(A2TCandidateSupplyError, match="configured|spec"):
        analyze_a2t_candidate_supply(
            source, flight_receipts=receipts, candidate_inventory=inventory,
            data_root=tmp_path / "bounds",
        )

    source, receipts, inventory = _fixture(tmp_path / "mirror")
    outer = receipts["stages"]["run_phases"]["phase_supply"]["candidate_selections"]
    next(iter(outer.values()))["supply_disposition"] = "no-mapping"
    with pytest.raises(A2TCandidateSupplyError, match="copies differ"):
        analyze_a2t_candidate_supply(
            source, flight_receipts=receipts, candidate_inventory=inventory,
            data_root=tmp_path / "mirror",
        )


def test_rejects_changed_selection_hashes_and_mapping_algorithm(tmp_path):
    source, receipts, inventory = _fixture(tmp_path / "hash")
    supply = receipts["stages"]["run_phases"]["phase_supply"]
    for audit in (
        next(iter(supply["candidate_selections"].values())),
        next(iter(supply["candidate_supply"]["candidate_selections"].values())),
    ):
        audit["selection_sha256"] = "0" * 64
        _rehash_selection(audit)
    with pytest.raises(A2TCandidateSupplyError, match="selection hash"):
        analyze_a2t_candidate_supply(
            source, flight_receipts=receipts, candidate_inventory=inventory,
            data_root=tmp_path / "hash",
        )

    source, receipts, inventory = _fixture(tmp_path / "mapping")
    supply = receipts["stages"]["run_phases"]["phase_supply"]
    for audit in (
        next(iter(supply["candidate_selections"].values())),
        next(iter(supply["candidate_supply"]["candidate_selections"].values())),
    ):
        audit["mappings"][0]["selected_value_ids"] = []
        _rehash_provider_and_selection(audit)
    with pytest.raises(A2TCandidateSupplyError, match="mapping"):
        analyze_a2t_candidate_supply(
            source, flight_receipts=receipts, candidate_inventory=inventory,
            data_root=tmp_path / "mapping",
        )


def test_rejects_changed_selection_receipt_hash(tmp_path):
    source, receipts, inventory = _fixture(tmp_path)
    supply = receipts["stages"]["run_phases"]["phase_supply"]
    for audit in (
        next(iter(supply["candidate_selections"].values())),
        next(iter(supply["candidate_supply"]["candidate_selections"].values())),
    ):
        audit["selection_receipt_sha256"] = "0" * 64
    with pytest.raises(A2TCandidateSupplyError, match="receipt hash"):
        analyze_a2t_candidate_supply(
            source, flight_receipts=receipts, candidate_inventory=inventory,
            data_root=tmp_path,
        )


def test_frozen_task_target_is_authoritative_for_candidate_mapping(tmp_path):
    source, receipts, inventory = _fixture(tmp_path)
    snapshot_path = tmp_path / "prepared" / "snapshot.json"
    document = json.loads(snapshot_path.read_text(encoding="utf-8"))
    body = {key: value for key, value in document.items() if key != "snapshot_sha256"}
    body["values"][0]["task_target"] = "beta"
    new_hash = content_hash(body)
    snapshot_path.write_text(
        json.dumps({**body, "snapshot_sha256": new_hash}), encoding="utf-8"
    )
    source.composed.values["knowledge_stores"]["parameter-meaning"]["snapshot"][
        "sha256"
    ] = new_hash
    supply = receipts["stages"]["run_phases"]["phase_supply"]
    supply["stores"]["parameter-meaning"]["store_snapshot_sha256"] = new_hash
    for audit in (
        next(iter(supply["candidate_selections"].values())),
        next(iter(supply["candidate_supply"]["candidate_selections"].values())),
    ):
        audit["snapshot_sha256"] = new_hash
        audit["store_snapshot_sha256"] = new_hash
        _rehash_provider_and_selection(audit)
    with pytest.raises(A2TCandidateSupplyError, match="task_target"):
        analyze_a2t_candidate_supply(
            source, flight_receipts=receipts, candidate_inventory=inventory,
            data_root=tmp_path,
        )


def test_reports_malformed_and_finite_perception_without_turning_it_into_empty(tmp_path):
    source, receipts, inventory = _fixture(tmp_path / "malformed")
    result = source.phase_results["tier1_direct:000001"]
    state = result["agent_states"][0]
    state["content"] = "not-json"
    malformed_hash = hashlib.sha256(b"not-json").hexdigest()
    state["source_response_sha256"] = malformed_hash
    response = source.bundle.trace_records["request-perception/response"]
    response["text"] = "not-json"
    response["response_text_sha256"] = malformed_hash
    source.bundle.trace_records["request-perception/native-role-contact"][
        "use_response_text_sha256"
    ] = malformed_hash
    perception = result["native_episode_receipt"]["role_visits"][0]["execution_receipt"]
    perception["contacts"][0]["response_text_sha256"] = malformed_hash
    result["contacts"][0]["response_sha256"] = malformed_hash
    supply = receipts["stages"]["run_phases"]["phase_supply"]
    supply["candidate_selections"] = {}
    supply["candidate_supply"]["candidate_selections"] = {}
    row = analyze_a2t_candidate_supply(
        source, flight_receipts=receipts, candidate_inventory=inventory,
        data_root=tmp_path / "malformed",
    )["samples"][0]
    assert row["candidate_state_status"] == "malformed"
    assert "valid JSON" in row["candidate_state_malformed_reason"]
    assert row["actions"] is None

    source, receipts, inventory = _fixture(tmp_path / "finite")
    result = source.phase_results["tier1_direct:000001"]
    initial_perception = result["native_episode_receipt"]["role_visits"][0]
    result["agent_states"] = []
    result["contacts"] = result["contacts"][:1]
    result["native_episode_receipt"] = {
        "role_visits": [], "planner_routes": [],
        "interrupted_role": {
            "role_id": "perception", "stage": "perception",
            "execution_receipt": initial_perception["execution_receipt"],
        },
        "terminal_disposition": {
            "reason": "finite_completion", "finish_reason": "length",
            "role_id": "perception", "stage": "perception",
            "revision_count": 0, "planner_accepted": False,
        },
    }
    result["final_query_state"] = deepcopy(result["initial_query_state"])
    stop = deepcopy(result["transitions"][-1])
    stop["prior_query_state_sha256"] = QueryState.from_json(
        result["initial_query_state"]
    ).content_hash()
    result["transitions"] = [stop]
    result["waves"] = [_terminal_stop_wave(stop)]
    supply = receipts["stages"]["run_phases"]["phase_supply"]
    supply["candidate_selections"] = {}
    supply["candidate_supply"]["candidate_selections"] = {}
    row = analyze_a2t_candidate_supply(
        source, flight_receipts=receipts, candidate_inventory=inventory,
        data_root=tmp_path / "finite",
    )["samples"][0]
    assert row["candidate_state_status"] == "unavailable"
    assert row["candidate_state_missing_reason"] == (
        "Perception did not complete before finite termination"
    )
    assert row["finite_reason"] == {
        "reason": "finite_completion", "finish_reason": "length",
        "role_id": "perception", "stage": "perception", "revision_count": 0,
    }


def test_rejects_unsupported_second_perception_visit(tmp_path):
    source, receipts, inventory = _fixture(tmp_path)
    result = source.phase_results["tier1_direct:000001"]
    result["native_episode_receipt"]["role_visits"].append(
        deepcopy(result["native_episode_receipt"]["role_visits"][0])
    )
    with pytest.raises(A2TCandidateSupplyError, match="one Perception visit"):
        analyze_a2t_candidate_supply(
            source, flight_receipts=receipts, candidate_inventory=inventory,
            data_root=tmp_path,
        )



def _terminal_stop_wave(stop):
    return {
        "transition": deepcopy(stop),
        "query_state_sha256": stop["prior_query_state_sha256"],
        "next_query_state_sha256": None,
        "termination_reason": "controller-stop",
        "rank_result": None,
        "fusion_decision": None,
    }


def _finite_tail(result):
    receipt = result["native_episode_receipt"]
    receipt.pop("accepted_solver_receipt")
    receipt["terminal_disposition"] = {
        "reason": "finite_completion", "finish_reason": "length",
        "role_id": "reviewer", "stage": "review", "revision_count": 0,
        "planner_accepted": False,
    }
    result["waves"].append(_terminal_stop_wave(result["transitions"][-1]))


def test_finite_reviewer_retains_prior_candidates_and_supply(tmp_path):
    source, receipts, inventory = _fixture(tmp_path)
    _finite_tail(source.phase_results["tier1_direct:000001"])
    row = analyze_a2t_candidate_supply(
        source, flight_receipts=receipts, candidate_inventory=inventory,
        data_root=tmp_path,
    )["samples"][0]
    assert row["candidate_state_status"] == "observed"
    assert row["unique_candidate_ids"] == ["alpha", "beta"]


@pytest.mark.parametrize("mutation", [
    "missing_non_stop", "missing_finite_stop", "wrong_stop_query",
    "stop_has_supply", "stop_wrong_reason", "unregistered_stop_wave",
    "stop_before_transition",
])
def test_rejects_misbound_or_missing_finite_waves(tmp_path, mutation):
    source, receipts, inventory = _fixture(tmp_path)
    result = source.phase_results["tier1_direct:000001"]
    _finite_tail(result)
    if mutation == "missing_non_stop":
        result["waves"].pop(0)
    elif mutation == "missing_finite_stop":
        result["waves"].pop()
    elif mutation == "wrong_stop_query":
        result["waves"][-1]["query_state_sha256"] = "0" * 64
    elif mutation == "stop_has_supply":
        result["waves"][-1]["rank_result"] = {"unexpected": "supply"}
    elif mutation == "stop_wrong_reason":
        result["waves"][-1]["termination_reason"] = "continue"
    elif mutation == "unregistered_stop_wave":
        result["native_episode_receipt"].pop("terminal_disposition")
    elif mutation == "stop_before_transition":
        stop = deepcopy(result["transitions"][-1])
        stop["prior_query_state_sha256"] = QueryState.from_json(
            result["initial_query_state"]
        ).content_hash()
        result["transitions"].insert(0, stop)
    with pytest.raises(A2TCandidateSupplyError, match="wave|stop"):
        analyze_a2t_candidate_supply(
            source, flight_receipts=receipts, candidate_inventory=inventory,
            data_root=tmp_path,
        )
