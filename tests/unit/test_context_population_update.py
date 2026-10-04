"""One original K16 response consumes all slots through the shared proposal path."""
from copy import deepcopy
import json
import pytest
from speech_aware_evidence_acquisition.rails import system_context_learning as learning
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_search_archive import SystemSearchArchive
from speech_aware_evidence_acquisition.rails.system_text_policy import SystemTextPolicyBundle, PolicyError
from test_system_text_policy import seed_document

def fixture(tmp_path):
    archive = SystemSearchArchive(tmp_path / "archive")
    policies = {}
    for i in range(1, 17):
        doc = seed_document()
        doc.update(schema="saea-system-text-policy-bundle-v3",
                   context_layout={"native_role_query_placement": None},
                   node_context={"tool_schema_rendering": "constant", "reviewer_history_scope": "full"})
        doc["role_text"]["perception"] = "Preserve observed speech evidence."
        doc["role_text"]["solver"] = f"Use the observed evidence under context policy number {i}."
        if i == 16:
            doc["cumulative_sources"].append({"kind": "feedback", "sha256": "9"*64,
                                              "sample_ids": ["slurp:train:historically-exposed"]})
        policy = SystemTextPolicyBundle.from_json(doc)
        archive.store_policy(policy)
        policies[f"branch-{i:02d}"] = {"bundle_id": policy.bundle_id, "policy": policy.as_json()}
    plan = {"schema": "saea-context-population-update-plan-v1", "batch_id": "update-two",
            "model": "gpt-6.1-sol", "reasoning_effort": "high", "semantic_batches": 1,
            "proposal_slots": 16}
    packet = {"schema": "saea-context-optimizer-input-v1", "algorithm": "tf-grpo-context-diversity",
              "iteration": 2, "policies": policies, "experience": {},
              "reference": {"sample_ids": ["slurp:train:frozen-reference"]},
              "groups": [{"sample_id": f"slurp:train:input-{i}", "semantic_advantage": "template-batch-reflection",
                          "members": [{"candidate_id": cid} for cid in policies]} for i in range(20)],
              "budget": {"N": 20, "K": 16, "candidate_trajectories": 320,
                         "control_trajectories": 40, "family_trajectories": 360},
              "population_update_plan": plan}
    packet["input_sha256"] = content_hash(packet)
    archive._write("context-learning/inputs/population.json", packet)
    response = {"schema": "saea-context-population-update-response-v1",
                "input_sha256": packet["input_sha256"], "actor_input_sha256": "a"*64,
                "model": "gpt-6.1-sol", "reasoning_effort": "high",
                "usage": {"provider_contacts": None, "input_tokens": None, "output_tokens": None},
                "branches": []}
    for cid, entry in policies.items():
        proposal = {"schema": "saea-context-policy-update-proposal-v1",
                    "algorithm": packet["algorithm"], "iteration": 2, "candidate_id": cid,
                    "component": "joint-system", "parent_ids": [entry["bundle_id"]],
                    "changes": {"role_text": {"reviewer": "Check evidence consistency before proposing a revision."}},
                    "rationale": "Improve evidence use.", "hypotheses": ["Test consistent review."],
                    "evidence": [packet["input_sha256"]]}
        response["branches"].append({"candidate_id": cid, "proposal": proposal, "experience_operations": []})
    return archive, packet, response

def reserve(archive, packet):
    return learning.reserve_context_population_update(archive, input_sha256=packet["input_sha256"], actor_input_sha256="a"*64)

def record(archive, packet, response):
    return learning.record_context_population_update(archive, input_sha256=packet["input_sha256"],
                                                    response_document=response)

def test_whole_response_uses_shared_compiler_preserves_invalid_and_nochange(tmp_path):
    a, p, r = fixture(tmp_path)
    reservation = reserve(a, p)
    assert reservation["proposal_slots"] == 16 and reservation["runtime_admission"] is False
    r["branches"][1]["proposal"]["changes"] = {}
    r["branches"][2]["proposal"]["changes"] = {"temperature": .9}
    before = deepcopy(r)
    result = record(a, p, r)
    assert result["status"] == "recorded" and len(result["records"]) == 16
    assert [x["status"] for x in result["records"][:3]] == ["provisional", "no-change", "invalid"]
    assert r == before
    raw = json.loads((a.root / "context-learning/populations/update-two/response.json").read_text())
    assert raw["response_document"] == r and raw["response_sha256"] == content_hash(r)
    assert result["runtime_admission"] is False and result["usage"] == r["usage"]
    child = a.load_policy(result["records"][0]["bundle_id"]).as_json()
    assert "slurp:train:historically-exposed" in {sid for src in child["cumulative_sources"] for sid in src["sample_ids"]}
    assert child["knowledge"] == p["policies"]["branch-01"]["policy"]["knowledge"]
    with pytest.raises(PolicyError):
        record(a, p, r)
    with pytest.raises(PolicyError):
        reserve(a, p)

def test_unreserved_response_is_not_consumed(tmp_path):
    a, p, r = fixture(tmp_path)
    with pytest.raises(PolicyError):
        record(a, p, r)
    assert not (a.root / "context-learning/populations").exists()

@pytest.mark.parametrize("fault", ["short", "schema", "input", "actor", "usage", "unknown"])
def test_invalid_envelope_is_preserved_and_all_slots_remain_spent(tmp_path, fault):
    a, p, r = fixture(tmp_path); reserve(a, p)
    if fault == "short": r["branches"].pop()
    elif fault == "schema": r["schema"] = "other"
    elif fault == "input": r["input_sha256"] = "b"*64
    elif fault == "actor": r["model"] = "another-model"
    elif fault == "usage": r["usage"]["input_tokens"] = -1
    else: r["extra"] = "Unexpected original text."
    result = record(a, p, r)
    assert result["status"] == "invalid-envelope" and len(result["records"]) == 16
    assert all(x["status"] == "invalid" for x in result["records"])
    assert not list((a.root / "context-learning/updates").glob("*")) if (a.root / "context-learning/updates").exists() else True
    with pytest.raises(PolicyError): record(a, p, r)

def test_duplicate_or_bad_branch_does_not_displace_its_reserved_slot(tmp_path):
    a, p, r = fixture(tmp_path); reserve(a, p)
    r["branches"][1] = deepcopy(r["branches"][0])
    r["branches"][3] = "Malformed original branch."
    result = record(a, p, r)
    assert result["records"][1]["candidate_id"] == "branch-02"
    assert result["records"][1]["status"] == "invalid"
    assert result["records"][3]["status"] == "invalid"
    assert result["records"][4]["status"] == "provisional"

@pytest.mark.parametrize("fault", ["missing-plan", "old-k4", "gepa", "budget", "batch-path", "hash", "missing-member"])
def test_refuse_unregistered_or_wrong_shape_input_before_reservation(tmp_path, fault):
    a, p, r = fixture(tmp_path)
    if fault == "missing-plan": p.pop("population_update_plan")
    elif fault == "old-k4": p["budget"]["K"] = 4
    elif fault == "gepa": p["algorithm"] = "gepa"
    elif fault == "budget": p["budget"]["candidate_trajectories"] = 80
    elif fault == "batch-path": p["population_update_plan"]["batch_id"] = "../escape"
    elif fault == "missing-member": p["groups"][0]["members"].pop()
    elif fault == "hash": p["experience"]["G"] = "Tampered."
    if fault != "hash":
        p.pop("input_sha256")
        p["input_sha256"] = content_hash(p)
    (a.root / "context-learning/inputs/population.json").write_text(json.dumps(p))
    with pytest.raises(PolicyError): reserve(a, p)
    assert not (a.root / "context-learning/populations").exists()

def test_interrupted_archival_keeps_original_and_forbids_automatic_reentry(tmp_path, monkeypatch):
    a, p, r = fixture(tmp_path); reserve(a, p)
    original = learning.record_context_update
    calls = []
    def stop(*args, **kwargs):
        calls.append(1)
        if len(calls) == 2: raise RuntimeError("Simulated write failure")
        return original(*args, **kwargs)
    monkeypatch.setattr(learning, "record_context_update", stop)
    with pytest.raises(RuntimeError): record(a, p, r)
    base = a.root / "context-learning/populations/update-two"
    assert (base / "response.json").exists() and not (base / "result.json").exists()
    with pytest.raises(PolicyError): record(a, p, r)

def test_capsule_identity_can_bind_private_packet_without_a_hash_cycle(tmp_path):
    a, p, r = fixture(tmp_path)
    capsule = {"optimizer_input_sha256": p["input_sha256"],
               "templates": {cid: entry["policy"]["role_text"] for cid, entry in p["policies"].items()},
               "abstract_feedback": {"schema": "synthetic-no-contents"}}
    capsule_hash = content_hash(capsule)
    learning.reserve_context_population_update(a, input_sha256=p["input_sha256"],
                                               actor_input_sha256=capsule_hash)
    r["actor_input_sha256"] = capsule_hash
    assert record(a, p, r)["status"] == "recorded"
    assert p["input_sha256"] == content_hash({k: v for k, v in p.items() if k != "input_sha256"})

def test_tampered_reservation_does_not_consume_response(tmp_path):
    a, p, r = fixture(tmp_path); reserve(a, p)
    path = a.root / "context-learning/populations/update-two/reservation.json"
    value = json.loads(path.read_text()); value["proposal_slots"] = 4
    path.write_text(json.dumps(value))
    with pytest.raises(PolicyError): record(a, p, r)
    assert not path.with_name("response.json").exists()

def test_null_original_response_consumes_all_slots_without_repair(tmp_path):
    a, p, _ = fixture(tmp_path); reserve(a, p)
    result = record(a, p, None)
    assert result["status"] == "invalid-envelope" and len(result["records"]) == 16
