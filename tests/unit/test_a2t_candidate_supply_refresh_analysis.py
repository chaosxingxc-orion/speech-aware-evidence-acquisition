"""Verify refreshed candidate provenance and operative Solver inputs offline."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_candidate_supply import (
    A2TCandidateSupplyError, analyze_a2t_candidate_supply,
)
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.knowledge import (
    AgentStateArtifact, AgentStepTransition, FusionDecision, QueryState,
    RankedFacet, RankResult,
)
from test_a2t_candidate_supply_analysis import (
    _action, _fixture, _provider_audit, _rehash_selection,
)


def _latest_fixture(tmp_path, *, refresh=True, interrupted=None, repeat=False):
    source, receipts, inventory = _fixture(tmp_path)
    sample = source.sample_ids[0]
    result = source.phase_results[sample]
    route = receipts["stages"]["run_phases"]["phase_supply"]
    store = route["stores"]["parameter-meaning"]
    spec = source.composed.values["knowledge_stores"]["parameter-meaning"]["candidate_supply"]["solver"]
    spec["candidate_state_selection"] = "latest"
    for target in (route["candidate_supply"]["specs"][0], store["candidate_supply"][0]):
        target["candidate_state_selection"] = "latest"
    query = QueryState.from_json(result["initial_query_state"])
    result.update(agent_states=[], contacts=[], transitions=[], waves=[])
    episode = {"role_visits": [], "planner_routes": []}
    result["native_episode_receipt"] = episode
    traces = source.bundle.trace_records
    traces.clear()
    audits = {}
    current = None

    def contact(stage, text, *, finite=False):
        nonlocal current
        index = len(result["contacts"])
        request_id = f"request-{index}"
        text_sha = hashlib.sha256(text.encode()).hexdigest()
        final = {
            "agent_contact_id": f"policy:{stage}:{index}:{sample}",
            "request_id": request_id, "request_sha256": "b" * 64,
            "response_sha256": "c" * 64, "response_text_sha256": text_sha,
        }
        execution = {"contacts": [final], "final_contact": final}
        visit = {"role_id": stage, "stage": stage, "execution_receipt": execution}
        result["contacts"].append({
            "plan": {"contact_id": final["agent_contact_id"], "query_state_sha256": query.content_hash()},
            "query_state_sha256": query.content_hash(), "response_sha256": text_sha,
        })
        traces[f"{request_id}/request"] = {
            "payload": {"request_id": request_id, "sample_id": sample},
            "payload_sha256": final["request_sha256"],
        }
        traces[f"{request_id}/response"] = {
            "text": text, "response_sha256": final["response_sha256"],
            "response_text_sha256": text_sha,
        }
        traces[f"{request_id}/native-role-contact"] = {
            "use_role_id": stage, "use_agent_contact_id": final["agent_contact_id"],
            "use_request_sha256": final["request_sha256"],
            "use_response_sha256": final["response_sha256"],
            "use_response_text_sha256": text_sha,
        }
        if finite:
            episode["interrupted_role"] = visit
            episode["terminal_disposition"] = {
                "reason": "finite_completion", "finish_reason": "length",
                "role_id": stage, "stage": stage, "revision_count": 1,
                "planner_accepted": False, "rejected_contact": final,
            }
        else:
            episode["role_visits"].append(visit)
            if stage == "perception":
                current = AgentStateArtifact(
                    state_id=f"{final['agent_contact_id']}:perception:{sample}",
                    state_kind="phase:perception", content=text,
                    source_query_state_sha256=query.content_hash(),
                    source_response_sha256=text_sha, producer_policy_id="policy",
                    cited_value_ids=(),
                ).validate()
                result["agent_states"].append(current.as_json())
        return execution

    def perceive(names, *, finite=False):
        return contact("perception", json.dumps({
            "actions": [_action(0, names)], "global_constraints": ["Keep order."],
        }), finite=finite)

    def solve(*, finite=False):
        nonlocal query
        actions = json.loads(current.content)["actions"]
        audit = _provider_audit(sample_id=sample, state=current, actions=actions, store_fields=store)
        qualified = [f"parameter-meaning::{item}" for item in audit["selected_value_ids"]]
        old = [item for item in qualified if item in query.retrieved_value_ids]
        added = [item for item in qualified if item not in query.retrieved_value_ids]
        disposition = "acquired" if added else "already-visible" if qualified else "no-mapping"
        audit.update({key: store[key] for key in (
            "store_id", "store_role", "store_snapshot_sha256", "store_release_sha256",
            "store_source_sha256", "composite_snapshot_sha256",
        )})
        audit.update(
            candidate_inventory_source_sha256=inventory.source_sha256,
            candidate_inventory_authority=inventory.source_authority,
            query_state_sha256=query.content_hash(),
            qualified_selected_value_ids=qualified, supply_disposition=disposition,
            source_selection_policy="last-matching-state-in-query-order-v1",
            selected_source_state_id=current.state_id,
            selected_source_state_sha256=current.content_hash(),
            already_visible_value_ids=old, added_value_ids=added,
        )
        _rehash_selection(audit)
        audits[f"solver:{sample}:{query.content_hash()}"] = audit
        if current.state_id in query.agent_state_ids:
            planner = contact("planner", '{"action":"REVISE"}')["final_contact"]
            staged = AgentStateArtifact(
                state_id=f"{planner['agent_contact_id']}:planner:{sample}",
                state_kind="phase:planner", content='{"action":"REVISE"}',
                source_query_state_sha256=query.content_hash(),
                source_response_sha256=planner["response_text_sha256"],
                producer_policy_id="policy", cited_value_ids=(),
            ).validate()
            result["agent_states"].append(staged.as_json())
            new_states = (staged.state_id,)
        else:
            new_states = (current.state_id,)
        support = tuple(f"parameter-meaning::facet:{name}" for name in audit["candidate_ids"])
        new_support = tuple(item for item in support if item not in query.visible_facet_ids)
        next_query = replace(
            query, query_id=f"query:{len(result['waves'])}:{sample}", loop_step=query.loop_step + 1,
            agent_state_ids=query.agent_state_ids + new_states,
            retrieved_value_ids=query.retrieved_value_ids + tuple(added),
            visible_facet_ids=query.visible_facet_ids + new_support,
        ).validate()
        target = (
            "knowledge-store:parameter-meaning:audio2tool-candidate-semantic-v1:"
            "saea-ranked-candidate-round-robin-v1:saea-candidate-semantic-passthrough-v1:"
            f"selection-receipt={audit['selection_receipt_sha256']}"
        )
        transition = AgentStepTransition(
            snapshot_sha256=store["composite_snapshot_sha256"],
            prior_query_state_sha256=query.content_hash(), next_query_state_sha256=next_query.content_hash(),
            action_kind="acquire" if added else "organize",
            action_target_refs=tuple(f"state:{item}" for item in new_states) + ((target,) if added else ()),
            new_value_ids=tuple(added), used_value_ids=(), dropped_value_ids=(),
            new_agent_state_ids=new_states, dropped_agent_state_ids=(), new_facet_ids=new_support,
        ).validate()
        rank = RankResult(
            snapshot_sha256=store["composite_snapshot_sha256"], query_state_sha256=query.content_hash(),
            ranking_policy_id=spec["rank_policy"],
            candidates=tuple(RankedFacet(facet_id=item, score=float(len(support)-i))
                             for i, item in enumerate(support)),
        ).validate() if added else None
        fusion = FusionDecision(
            snapshot_sha256=store["composite_snapshot_sha256"], query_state_sha256=query.content_hash(),
            rank_result_sha256=rank.content_hash(), fusion_policy_id=spec["fuse_policy"],
            supporting_facet_ids=new_support, selected_value_ids=tuple(added),
        ).validate() if rank else None
        result["transitions"].append(transition.as_json())
        result["waves"].append({
            "query_state_sha256": query.content_hash(), "next_query_state_sha256": next_query.content_hash(),
            "transition": transition.as_json(), "rank_result": rank.as_json() if rank else None,
            "fusion_decision": fusion.as_json() if fusion else None,
        })
        query = next_query
        return contact("solver", "synthetic answer", finite=finite)

    perceive(("alpha",))
    first_solver = solve()
    final_solver = first_solver
    if refresh:
        perceive(("alpha", "beta"), finite=interrupted == "perception")
        if interrupted != "perception":
            final_solver = solve(finite=interrupted == "solver")
    if repeat:
        final_solver = solve()
    if interrupted:
        episode["terminal_solver_receipt"] = first_solver
    else:
        episode["accepted_solver_receipt"] = final_solver
    stop = AgentStepTransition(
        snapshot_sha256=store["composite_snapshot_sha256"],
        prior_query_state_sha256=query.content_hash(), next_query_state_sha256=None,
        action_kind="stop", action_target_refs=(), new_value_ids=(), used_value_ids=(),
        dropped_value_ids=(), new_agent_state_ids=(), dropped_agent_state_ids=(),
    ).validate().as_json()
    result["transitions"].append(stop)
    if interrupted:
        result["waves"].append({
            "query_state_sha256": query.content_hash(), "next_query_state_sha256": None,
            "transition": stop, "rank_result": None, "fusion_decision": None,
            "termination_reason": "controller-stop",
        })
    result["final_query_state"] = query.as_json()
    route["candidate_selections"] = audits
    route["candidate_supply"]["candidate_selections"] = deepcopy(audits)
    return source, receipts, inventory


def _read(tmp_path, **kwargs):
    source, receipts, inventory = _latest_fixture(tmp_path, **kwargs)
    return analyze_a2t_candidate_supply(
        source, flight_receipts=receipts, candidate_inventory=inventory, data_root=tmp_path,
    )


def test_latest_without_refresh_preserves_initial_and_operative_source(tmp_path):
    report = _read(tmp_path, refresh=False)
    row = report["samples"][0]
    assert report["schema"] == "saea-a2t-candidate-supply-attribution-v2"
    assert len(row["perception_visits"]) == 1
    assert row["initial"]["unique_candidate_ids"] == ["alpha"]
    assert row["operative"]["candidate_source"]["unique_candidate_ids"] == ["alpha"]
    assert row["operative"]["delivery_kind"] == "accepted"


def test_refresh_preserves_both_sources_and_only_adds_missing_parameter_value(tmp_path):
    row = _read(tmp_path)["samples"][0]
    assert row["initial"]["unique_candidate_ids"] == ["alpha"]
    assert row["last_attempted"]["unique_candidate_ids"] == ["alpha", "beta"]
    assert row["operative"]["candidate_source"]["unique_candidate_ids"] == ["alpha", "beta"]
    assert len(row["perception_visits"]) == 2
    second = row["perception_visits"][1]["selections"][0]
    assert second["already_visible_value_ids"] == ["parameter-meaning::card:alpha:value"]
    assert second["added_value_ids"] == ["parameter-meaning::card:beta:value"]


@pytest.mark.parametrize("stage", ["perception", "solver"])
def test_finite_refresh_retains_the_original_delivered_solver_source(tmp_path, stage):
    row = _read(tmp_path, interrupted=stage)["samples"][0]
    assert row["operative"]["delivery_kind"] == "finite"
    assert row["operative"]["candidate_source"]["unique_candidate_ids"] == ["alpha"]
    assert row["last_attempted"]["status"] == ("unavailable" if stage == "perception" else "observed")


@pytest.mark.parametrize("field,value", [
    ("source_selection_policy", "any-state"),
    ("selected_source_state_sha256", "0" * 64),
    ("added_value_ids", ["parameter-meaning::card:alpha:value", "parameter-meaning::card:beta:value"]),
    ("already_visible_value_ids", []),
])
def test_rehashed_latest_extension_tampering_is_rejected(tmp_path, field, value):
    source, receipts, inventory = _latest_fixture(tmp_path)
    route = receipts["stages"]["run_phases"]["phase_supply"]
    audit = list(route["candidate_selections"].values())[-1]
    audit[field] = value
    _rehash_selection(audit)
    route["candidate_supply"]["candidate_selections"] = deepcopy(route["candidate_selections"])
    with pytest.raises(A2TCandidateSupplyError):
        analyze_a2t_candidate_supply(
            source, flight_receipts=receipts, candidate_inventory=inventory, data_root=tmp_path,
        )


def test_missing_operative_selection_is_explicit_not_guessed_from_last_perception(tmp_path):
    source, receipts, inventory = _latest_fixture(tmp_path)
    route = receipts["stages"]["run_phases"]["phase_supply"]
    route["candidate_selections"].pop(list(route["candidate_selections"])[-1])
    route["candidate_supply"]["candidate_selections"] = deepcopy(route["candidate_selections"])
    row = analyze_a2t_candidate_supply(
        source, flight_receipts=receipts, candidate_inventory=inventory, data_root=tmp_path,
    )["samples"][0]
    assert row["last_attempted"]["unique_candidate_ids"] == ["alpha", "beta"]
    assert row["operative"]["status"] == "unavailable"
    assert row["operative"]["candidate_source"] is None


@pytest.mark.parametrize("actions,queries,expected", [
    (None, ("d"*64,), "f8d6b96c7ebdead519029e59fde499222edbacd40a75a3fdd20c8798520039ed"),
    ([_action(0, ("alpha","beta")), _action(1, ("alpha","gamma"))], ("d"*64,"e"*64),
     "62af48395c0b3a53bc092f5feb9972673920cc7dc114541153b6b3b871cf53ec"),
    ([], ("d"*64,), "2ec56fcc1dabbd9eee4cf170b9f7436d7429eda471fb14fcbdffd1ac0ff43f20"),
])
def test_historical_single_reports_are_byte_identical(tmp_path, actions, queries, expected):
    source, receipts, inventory = _fixture(tmp_path, actions=actions, solver_queries=queries)
    report = analyze_a2t_candidate_supply(
        source, flight_receipts=receipts, candidate_inventory=inventory, data_root=tmp_path,
    )
    assert content_hash(report) == expected


def test_repeated_solver_visits_keep_the_same_latest_mapping(tmp_path):
    row = _read(tmp_path, repeat=True)["samples"][0]
    selections = row["perception_visits"][1]["selections"]
    assert len(selections) == 2
    assert selections[1]["supply_disposition"] == "already-visible"
    assert selections[1]["added_value_ids"] == []
    assert selections[0]["selected_value_ids"] == selections[1]["selected_value_ids"]


def test_rehashed_stale_source_is_rejected_even_with_matching_provider_and_transition(tmp_path):
    source, receipts, inventory = _latest_fixture(tmp_path)
    route = receipts["stages"]["run_phases"]["phase_supply"]
    entries = list(route["candidate_selections"].items())
    old, audit = deepcopy(entries[0][1]), entries[1][1]
    old_target_hash = audit["selection_receipt_sha256"]
    for key in (
        "candidate_state_id", "candidate_state_sha256", "candidate_source_response_sha256",
        "candidate_ids", "mappings", "selected_value_ids", "candidate_occurrences",
        "selection_sha256", "qualified_selected_value_ids", "selected_source_state_id",
        "selected_source_state_sha256",
    ):
        audit[key] = old[key]
    audit.update(
        already_visible_value_ids=old["qualified_selected_value_ids"], added_value_ids=[],
        supply_disposition="already-visible",
    )
    _rehash_selection(audit)
    result = source.phase_results[source.sample_ids[0]]
    for transition in result["transitions"]:
        transition["action_target_refs"] = [
            target.replace(old_target_hash, audit["selection_receipt_sha256"])
            for target in transition["action_target_refs"]
        ]
    for wave in result["waves"]:
        wave["transition"]["action_target_refs"] = [
            target.replace(old_target_hash, audit["selection_receipt_sha256"])
            for target in wave["transition"]["action_target_refs"]
        ]
    route["candidate_supply"]["candidate_selections"] = deepcopy(route["candidate_selections"])
    with pytest.raises(A2TCandidateSupplyError, match="stale or foreign"):
        analyze_a2t_candidate_supply(
            source, flight_receipts=receipts, candidate_inventory=inventory, data_root=tmp_path,
        )


def test_duplicate_perception_visits_are_rejected(tmp_path):
    source, receipts, inventory = _latest_fixture(tmp_path)
    visits = source.phase_results[source.sample_ids[0]]["native_episode_receipt"]["role_visits"]
    visits.insert(1, deepcopy(visits[0]))
    with pytest.raises(A2TCandidateSupplyError, match="duplicate"):
        analyze_a2t_candidate_supply(
            source, flight_receipts=receipts, candidate_inventory=inventory, data_root=tmp_path,
        )
