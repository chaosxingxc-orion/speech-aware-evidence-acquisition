"""A later full-system read preserves registration and shared attribution."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts/analysis"))
spec=importlib.util.spec_from_file_location("trajectory_cli",ROOT/"scripts/analysis/slurp_system_trajectory_read.py")
cli=importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


def fixture(tmp_path,monkeypatch):
    roster={"relpath":"roster.json","sha256":"a"*64,"split_role":"discovery",
            "split_identity_hash":"b"*64,"rows":2}
    registration={"read_id":"read","roster":roster,
                  "arms":{k:{"run_id":k,"attempt_id":"attempt"} for k in ("left","right")}}
    raw=json.dumps(registration).encode()
    (tmp_path/"scope.json").write_bytes(raw)
    recipe={"schema":"saea-slurp-system-attribution-read-v1","execution_profile":"model-free-check",
            "feedback_role":"construction","status":"sealed","read_run_id":"read","roster":roster,
            "registration":{"relpath":"scope.json","sha256":hashlib.sha256(raw).hexdigest()},
            "comparison":["left","right"],
            "arms":{k:{"manifest":{"relpath":f"runs/{k}/attempt/{k}.run-manifest.json"}}
                    for k in ("left","right")}}
    monkeypatch.setattr(cli.var1,"load_roster",lambda *a: {
        "sha256":"a"*64,"split_role":"discovery","split_identity_hash":"b"*64,"ids":["s1","s2"]})
    return recipe


def test_registered_pair_has_no_hardcoded_plan_arm(tmp_path,monkeypatch):
    recipe=fixture(tmp_path,monkeypatch)
    roster,pair,legacy=cli.recipe_roster(recipe,tmp_path)
    assert pair==("left","right") and not legacy and len(roster["ids"])==2


@pytest.mark.parametrize("change",["roster","registration","arm","run","pair","evaluation","template"])
def test_unregistered_read_is_refused_before_label_loading(tmp_path,monkeypatch,change):
    recipe=fixture(tmp_path,monkeypatch)
    if change=="roster":recipe["roster"]=dict(recipe["roster"],rows=1)
    elif change=="registration":recipe["registration"]["sha256"]="f"*64
    elif change=="arm":recipe["arms"]["other"]=recipe["arms"].pop("right")
    elif change=="run":recipe["arms"]["right"]["manifest"]["relpath"]="runs/other/attempt/other.run-manifest.json"
    elif change=="pair":recipe["comparison"]=["left","left"]
    elif change=="evaluation":recipe["feedback_role"]="evaluation"
    else:recipe["status"]="template"
    with pytest.raises(ValueError):cli.recipe_roster(recipe,tmp_path)


def test_contact_projection_retains_actual_input_volume_without_claiming_use():
    payload={"history":[{"content":"abc","state_kind":"tool-result"}],
             "supplied_evidence":[{"evidence_id":"store::one","content":"12345"}],
             "tool_schemas":[{"name":"lookup"}],"speech_packet_sha256":"s","task_instruction":"abcd"}
    source=SimpleNamespace(bundle=SimpleNamespace(trace_records={"r/request":{"payload":payload}}))
    visit={"stage":"review","execution_receipt":{"contacts":[{"request_id":"r"}]}}
    result=cli._context(source,visit)["contacts"][0]
    assert result["text_input_chars"]=={"task_instruction":4,"history":3,"supplied_evidence":5}
    assert result["tool_schema_count"]==1
    assert result["history_state_kinds"]==["tool-result"]
    assert "semantic_use" not in result


@pytest.mark.parametrize("mutation", [None, "missing", "different", "wrong-hash"])
def test_full_arm_attribution_preserves_unreached_row_and_binds_proposal(monkeypatch, mutation):
    import copy
    from speech_aware_evidence_acquisition.rails.hashing import content_hash

    block = {"schema": "saea-native-candidate-proposal-consumption-v1",
             "proposals": {}, "contacts": [], "prepared_without_response": []}
    native = {"candidate_proposal": block, "role_visits": [], "planner_routes": []}
    source = SimpleNamespace(
        plan=SimpleNamespace(run_id="run", attempt_id="attempt"),
        phase_artifact_sha256="p", sample_ids=("s1",),
        phase_results={"s1": {"native_episode_receipt": native, "agent_states": []}},
        output_rows={"s1": {"text": ""}},
        bundle=SimpleNamespace(manifest={"outputs": {"sha256": "o"}, "scores": {}},
                               manifest_path=Path("/tmp/fake-manifest.json"), trace_records={}))
    trajectory = {"sample_id": "s1", "trajectory_sha256": "t", "planner_routes": [], "tool_events": [],
                  "candidate_proposal": {"receipt": copy.deepcopy(block), "receipt_sha256": content_hash(block)}}
    feedback = {"run_id": "run", "attempt_id": "attempt",
                "system_trajectories": {"source": {"phase_artifact_sha256": "p", "outputs_sha256": "o"},
                                        "trajectories": [trajectory]},
                "terminal_feedback": [{"sample_id": "s1", "intent_exact": False, "fallback_flags": []}]}
    scores = {"slurp-slu-official-train": {"per_sample": [
        {"sample_id": "s1", "slot_f1_exact_tp": 0, "slot_f1_exact_fp": 0, "slot_f1_exact_fn": 0}]}}
    monkeypatch.setattr(cli, "_verify_artifact", lambda *args, **kwargs: json.dumps(scores).encode())
    gold = {"s1": SimpleNamespace(scenario="alarm", action="set", entities=())}
    if mutation == "missing":
        del trajectory["candidate_proposal"]
    elif mutation == "different":
        trajectory["candidate_proposal"]["receipt"]["prepared_without_response"] = [{"request_id": "other"}]
    elif mutation == "wrong-hash":
        trajectory["candidate_proposal"]["receipt_sha256"] = "f"*64
    if mutation:
        with pytest.raises(ValueError, match="proposal"):
            cli.analyze_arm(source, feedback, gold)
    else:
        result = cli.analyze_arm(source, feedback, gold)
        assert result["summary"]["rows"] == result["summary"]["solver_not_reached"] == 1
        assert result["candidate_recovery"]["status_counts"] == {"not_reached": 1}
        assert result["candidate_recovery"]["supplied_rows"] == 0
        assert result["rows"][0]["candidate_recovery"]["selection_origin"]["first"] == "unavailable"
