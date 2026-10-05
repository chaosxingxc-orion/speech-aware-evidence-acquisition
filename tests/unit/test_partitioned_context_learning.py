"""Complete historical cohorts feed one immutable, configuration-driven update."""
from copy import deepcopy
import json
import pytest
from test_abstract_population_projection import setup, with_archive
from test_abstract_population_sources import pin
from speech_aware_evidence_acquisition.analysis import abstract_population_projection as projection
from speech_aware_evidence_acquisition.rails import system_context_learning as learning
from speech_aware_evidence_acquisition.rails import system_context_partitioned_learning as subject
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError


@pytest.fixture
def ready(with_archive, monkeypatch):
    s = with_archive
    for family in s.joined["private_families"].values():
        family[-1]["sample_ids"] = ["slurp:train:PRIVATE_REFERENCE"]
    monkeypatch.setattr(subject, "read_registered_population_sources", projection.read_registered_population_sources)
    s.registration = {"schema": "saea-partitioned-context-update-registration-v1",
        "status": "ROOT_REGISTERED", "algorithm": "tf-grpo-context-diversity", "iteration": 3,
        "projection": s.pin, "source_population": s.joined["projection_config"],
        "population_update_plan": {"schema": "saea-context-population-update-plan-v1",
            "batch_id": "partitioned-next", "model": s.cfg["proposer"]["model"],
            "reasoning_effort": s.cfg["proposer"]["reasoning_effort"], "semantic_batches": 1,
            "proposal_slots": sum(len(c["candidate_ids"]) for c in s.cfg["cohorts"])}}
    s.registration_pin = pin(s.root, "update.json", s.registration)
    return s


def prepare(s):
    return subject.prepare_partitioned_context_optimizer_input(s.archive,
        registration_pin=s.registration_pin, repo_root=s.root, data_root=s.data)


def test_complete_input_preserves_cohorts_templates_and_all_exposure(ready):
    s = ready; packet = prepare(s)
    view = subject.partitioned_context_actor_view(s.archive, input_sha256=packet["input_sha256"])
    assert len(packet["policies"]) == 5
    assert list(view["feedback"]["cohorts"]) == ["cohort-0", "cohort-1"]
    assert [len(c["templates"]) for c in view["feedback"]["cohorts"].values()] == [2, 3]
    assert view["source_budget"]["family_trajectories"] == 18
    assert view["runtime_admission"] is False
    for secret in ("PRIVATE_EXPOSURE", "PRIVATE_REFERENCE", "PRIVATE_VALUE", "slurp:train:", "construction_instruction"):
        assert secret not in json.dumps(view)
    assert "slurp:train:PRIVATE_REFERENCE" in packet["feedback_sample_ids"]
    assert not (s.archive.root / "context-learning/populations").exists()
    with pytest.raises(PolicyError): prepare(s)


def response(packet, capsule_hash):
    return {"schema": "saea-context-population-update-response-v1", "input_sha256": packet["input_sha256"],
        "actor_input_sha256": capsule_hash, "model": "gpt-6.1-sol", "reasoning_effort": "high",
        "usage": {"provider_contacts": None, "input_tokens": None, "output_tokens": None},
        "branches": [{"candidate_id": cid, "proposal": {"schema": "saea-context-policy-update-proposal-v1",
            "algorithm": packet["algorithm"], "iteration": packet["iteration"], "candidate_id": cid,
            "component": "joint-system", "parent_ids": [p["bundle_id"]], "changes": {},
            "rationale": "Preserve unchanged templates when no variation supports an update.",
            "hypotheses": ["No causal node claim."], "evidence": [packet["input_sha256"]]},
            "experience_operations": []} for cid, p in packet["policies"].items()]}


def test_shared_one_shot_compiler_retains_nochange_invalid_and_cross_cohort_exposure(ready):
    s = ready; p = prepare(s)
    view = subject.partitioned_context_actor_view(s.archive, input_sha256=p["input_sha256"])
    h = content_hash(view)
    reservation = learning.reserve_context_population_update(s.archive, input_sha256=p["input_sha256"], actor_input_sha256=h)
    assert reservation["proposal_slots"] == 5 and reservation["source_population"] == p["source_population"]
    document = response(p, h)
    document["branches"][1]["proposal"]["changes"] = {"temperature": .9}
    result = learning.record_context_population_update(s.archive, input_sha256=p["input_sha256"], response_document=document)
    assert [r["status"] for r in result["records"]] == ["no-change", "invalid", "no-change", "no-change", "no-change"]
    child = s.archive.load_policy(result["records"][0]["bundle_id"]).as_json()
    exposed = {sid for entry in child["cumulative_sources"] for sid in entry["sample_ids"]}
    assert {"slurp:train:PRIVATE_REFERENCE", "slurp:train:PRIVATE_EXPOSURE"} <= exposed
    assert set(s.cfg["cohorts"][0]["sample_ids"]) <= exposed
    with pytest.raises(PolicyError): learning.record_context_population_update(s.archive, input_sha256=p["input_sha256"], response_document=document)


@pytest.mark.parametrize("fault", ["draft", "algorithm", "iteration", "slots", "model", "extra"])
def test_bad_registration_refuses_before_source_contacts_or_archive_writes(ready, fault):
    s = ready
    if fault == "draft": s.registration["status"] = "DRAFT"
    elif fault == "algorithm": s.registration["algorithm"] = "gepa"
    elif fault == "iteration": s.registration["iteration"] = 0
    elif fault == "slots": s.registration["population_update_plan"]["proposal_slots"] = 99
    elif fault == "model": s.registration["population_update_plan"]["model"] = "other"
    else: s.registration["extra"] = True
    s.registration_pin = pin(s.root, "update.json", s.registration)
    with pytest.raises(PolicyError): prepare(s)
    assert not s.calls
    assert not (s.archive.root / "context-learning/inputs").exists()


def test_last_source_failure_never_produces_partial_optimizer_packet(ready, monkeypatch):
    def refuse(**kwargs): raise PolicyError("last source family incomplete")
    monkeypatch.setattr(projection, "read_registered_population_sources", refuse)
    with pytest.raises(PolicyError): prepare(ready)
    assert not (ready.archive.root / "context-learning/inputs").exists()


@pytest.mark.parametrize("fault", ["flatten", "partial", "policy", "config", "hash"])
def test_changed_private_packet_refuses_before_reservation(ready, fault):
    s = ready; p = prepare(s)
    if fault == "flatten": p["groups"] = []
    elif fault == "partial": p["learner_view"]["population"]["cohorts"].pop("cohort-1")
    elif fault == "policy": next(iter(p["policies"].values()))["policy"]["role_text"]["solver"] = "Changed."
    elif fault == "config": (s.archive.root / p["source_population"]["relpath"]).write_text("{}")
    else: p["iteration"] += 1
    if fault != "hash":
        p.pop("input_sha256"); p["input_sha256"] = content_hash(p)
    path = next((s.archive.root / "context-learning/inputs").glob("*.json"))
    path.write_text(json.dumps(p))
    with pytest.raises(PolicyError): learning.reserve_context_population_update(s.archive, input_sha256=p["input_sha256"], actor_input_sha256="a"*64)
    assert not (s.archive.root / "context-learning/populations").exists()


@pytest.mark.parametrize("fault", ["business-content", "node-content", "relative", "business-latency", "business-quality", "missing-control", "template-content"])
def test_actor_boundary_rejects_unqualified_content_and_changed_measurements(ready, fault):
    s = ready; p = prepare(s); v = p["learner_view"]
    c = v["population"]["cohorts"]["cohort-0"]
    if fault == "business-content": v["business_measurements"]["cohort-0"][0]["reason"] = "PRIVATE_CONTENT"
    elif fault == "node-content": c["groups"][0]["members"][0]["nodes"][0][3][1] = "PRIVATE_CONTENT"
    elif fault == "relative": c["groups"][0]["members"][0]["relative_return"] = 8.
    elif fault == "business-latency": v["business_measurements"]["cohort-0"][0]["mean_sample_seconds"] += 1
    elif fault == "business-quality": v["business_measurements"]["cohort-0"][0]["slu_f1"] += .1
    elif fault == "missing-control": v["business_measurements"]["cohort-0"].pop()
    else: v["templates"]["cohort-0"]["candidate-0"]["knowledge"] = "PRIVATE_CONTENT"
    p.pop("input_sha256");p["input_sha256"] = content_hash(p)
    path = next((s.archive.root / "context-learning/inputs").glob("*.json"));path.write_text(json.dumps(p))
    with pytest.raises((PolicyError, ValueError)):
        subject.partitioned_context_actor_view(s.archive, input_sha256=p["input_sha256"])


def test_nonconstant_own_cohort_uses_shared_joint_template_compiler(ready, monkeypatch):
    s = ready
    original = projection.learning._candidate_groups
    def varied(*args, **kwargs):
        groups = original(*args, **kwargs)
        for group in groups:
            member = group["members"][0]
            member["native_counts"] = dict(member["native_counts"], slu_f1_word_fp=1)
            member["utility"] = projection.learning.feedback_utility(member["native_counts"], .5)
        return groups
    monkeypatch.setattr(projection.learning, "_candidate_groups", varied)
    p = prepare(s)
    view = subject.partitioned_context_actor_view(s.archive, input_sha256=p["input_sha256"])
    h = content_hash(view)
    learning.reserve_context_population_update(s.archive, input_sha256=p["input_sha256"], actor_input_sha256=h)
    r = response(p, h)
    r["branches"][0]["proposal"]["changes"] = {"role_text": {"reviewer": "Check whether each proposed correction is supported before requesting revision."}}
    out = learning.record_context_population_update(s.archive, input_sha256=p["input_sha256"], response_document=r)
    assert out["records"][0]["status"] == "provisional"
    assert out["runtime_admission"] is False
    child = s.archive.load_policy(out["records"][0]["bundle_id"]).as_json()
    parent = p["policies"]["candidate-0"]["policy"]
    for key in ("knowledge", "construction_instruction", "supply", "seed_config_sha256"):
        assert child[key] == parent[key]


@pytest.mark.parametrize("different", [False, True])
def test_existing_archived_config_is_verified_not_rewritten(ready, different):
    s = ready; ref = s.registration["source_population"]
    target = s.archive.root / ref["relpath"];target.parent.mkdir(parents=True, exist_ok=True)
    original = b"{}" if different else (s.root / ref["relpath"]).read_bytes()
    target.write_bytes(original)
    if different:
        with pytest.raises(PolicyError, match="archived source config differs"): prepare(s)
        assert not (s.archive.root / "context-learning/inputs").exists()
    else:
        assert prepare(s)["runtime_admission"] is False
    assert target.read_bytes() == original


def test_last_cohort_indirect_exposure_is_carried_into_first_cohort_child(ready):
    from speech_aware_evidence_acquisition.rails.system_text_policy import SystemTextPolicyBundle
    s = ready
    binding = s.joined["private_families"]["cohort-1"][2]["member_bindings"]["candidate-4"]
    doc = s.archive.load_policy(binding["bundle_id"]).as_json()
    doc["cumulative_sources"].append({"kind": "feedback", "sha256": "b"*64,
                                      "sample_ids": ["slurp:train:other-cohort-only"]})
    parent = SystemTextPolicyBundle.from_json(doc);s.archive.store_policy(parent)
    binding["bundle_id"] = parent.bundle_id
    p = prepare(s);h = content_hash(subject.partitioned_context_actor_view(s.archive, input_sha256=p["input_sha256"]))
    learning.reserve_context_population_update(s.archive, input_sha256=p["input_sha256"], actor_input_sha256=h)
    out = learning.record_context_population_update(s.archive, input_sha256=p["input_sha256"], response_document=response(p,h))
    child = s.archive.load_policy(out["records"][0]["bundle_id"]).as_json()
    assert "slurp:train:other-cohort-only" in {sid for src in child["cumulative_sources"] for sid in src["sample_ids"]}


def test_single_family_trial_entry_refuses_partitioned_source(ready):
    s = ready;p = prepare(s)
    with pytest.raises(PolicyError, match="partitioned update requires"):
        learning.qualify_context_population_trial(s.archive, input_sha256=p["input_sha256"],
            request={}, repo_root=s.root, data_root=s.data)
