"""Actor input exposes complete templates and abstract outcomes, never custody."""
from copy import deepcopy
import json
import pytest
from speech_aware_evidence_acquisition.rails import system_context_learning as learning
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError
from test_context_population_update import fixture as archive_fixture
from test_abstract_population_feedback import fixture as source_fixture

def setup(tmp_path):
    archive, packet, _ = archive_fixture(tmp_path)
    source, _ = source_fixture()
    source["templates"] = deepcopy(source["templates"])
    for template in source["templates"]:
        template["bundle_id"] = packet["policies"][template["candidate_id"]]["bundle_id"]
    packet["business_measurements"] = []
    for template in source["templates"]:
        template["official_summary"] = {"slu_f1": .6, "intent": .8}
        packet["business_measurements"].append({"candidate_id": template["candidate_id"],
            "bundle_id": template["bundle_id"], "slu_f1": .6, "intent": .8,
            "reliable_completion_rate": 1., "mean_sample_seconds": 1., "non_first_mean_seconds": 1.,
            "model_calls": 2, "tool_calls": 0, "eligible": True, "timing_report_sha256": "b"*64})
    packet["family_id"] = source["family_id"]
    packet["abstract_source"] = {"source_sha256": content_hash(source),
                                "source_batch": source["source_batch"]}
    packet["reference"]["f1"] = .5
    packet["budget"].update(N=2, candidate_trajectories=32, control_trajectories=4, family_trajectories=36)
    packet["groups"] = []
    for index in range(2):
        members = []
        for template in source["templates"]:
            terminal = template["samples"][index]["terminal"]
            members.append({"candidate_id": template["candidate_id"],
                            "native_counts": terminal["official_counts"], "utility": terminal["utility"],
                            "execution": {"reliable_completion": terminal["reliable"],
                                          "abstained": terminal["abstained"],
                                          "wall_time_seconds": terminal["sample_seconds"],
                                          "model_calls": len(template["samples"][index]["nodes"])}})
        packet["groups"].append({"sample_id": f"slurp:train:PRIVATE-{index}",
                                 "semantic_advantage": "template-batch-reflection", "members": members})
    repin(archive, packet)
    return archive, packet, source

def repin(archive, packet):
    packet.pop("input_sha256", None)
    packet["input_sha256"] = content_hash(packet)
    (archive.root / "context-learning/inputs/population.json").write_text(json.dumps(packet))

def test_complete_templates_and_abstract_outcomes_reach_actor_without_private_content(tmp_path):
    archive, packet, source = setup(tmp_path)
    before = deepcopy(packet)
    view = learning.context_population_actor_view(archive, input_sha256=packet["input_sha256"], source=source)
    assert len(view["templates"]) == 16 and len(view["feedback"]["groups"]) == 2
    assert view["templates"]["branch-01"]["role_text"] == packet["policies"]["branch-01"]["policy"]["role_text"]
    assert view["templates"]["branch-01"]["node_context"] == packet["policies"]["branch-01"]["policy"]["node_context"]
    assert view["optimizer_input_sha256"] == packet["input_sha256"] and view["runtime_admission"] is False
    text = json.dumps(view)
    assert "slurp:train:" not in text
    for field in ("cumulative_sources", "construction_instruction", "construction_receipt", "knowledge", "sample_id"):
        assert field not in view["templates"]["branch-01"]
    assert "PRIVATE-" not in text
    assert packet == before
    # The exact actor view can be hashed after the private packet, then reserved.
    receipt = learning.reserve_context_population_update(archive, input_sha256=packet["input_sha256"],
                                                          actor_input_sha256=content_hash(view))
    assert receipt["actor_input_sha256"] == content_hash(view)

@pytest.mark.parametrize("fault", ["unpinned", "cohort", "counts", "utility", "reliability",
                                   "elapsed", "calls", "abstract_content"])
def test_mismatched_or_concrete_projection_is_rejected_before_actor_input(tmp_path, fault):
    archive, packet, source = setup(tmp_path)
    if fault == "unpinned": source["templates"][0]["official_summary"]["slu_f1"] = 99
    elif fault == "cohort": packet["abstract_source"]["source_batch"] = "other"
    elif fault == "counts": packet["groups"][0]["members"][0]["native_counts"] = {}
    elif fault == "utility": packet["groups"][0]["members"][0]["utility"] = 100
    elif fault == "reliability": packet["groups"][0]["members"][0]["execution"]["reliable_completion"] = False
    elif fault == "elapsed": packet["groups"][0]["members"][0]["execution"]["wall_time_seconds"] = 999
    elif fault == "calls": packet["groups"][0]["members"][0]["execution"]["model_calls"] = 999
    else:
        source["templates"][0]["samples"][0]["task_answer"] = "PRIVATE_ANSWER"
        packet["abstract_source"]["source_sha256"] = content_hash(source)
    repin(archive, packet)
    with pytest.raises(ValueError):
        learning.context_population_actor_view(archive, input_sha256=packet["input_sha256"], source=source)
    assert not (archive.root / "context-learning/populations").exists()

def test_missing_abstract_admission_and_raw_episode_fields_do_not_fall_back(tmp_path):
    archive, packet, source = setup(tmp_path)
    packet.pop("abstract_source")
    packet["raw_episodes"] = ["PRIVATE_RAW"]
    repin(archive, packet)
    with pytest.raises(PolicyError):
        learning.context_population_actor_view(archive, input_sha256=packet["input_sha256"], source=source)

def test_private_budget_annotations_and_freeform_experience_are_not_exported(tmp_path):
    archive, packet, source = setup(tmp_path)
    packet["budget"]["private_case_note"] = "PRIVATE_BUDGET"
    packet["experience"] = {"private-note": "PRIVATE_EXPERIENCE"}
    repin(archive, packet)
    view = learning.context_population_actor_view(archive, input_sha256=packet["input_sha256"], source=source)
    assert "PRIVATE_BUDGET" not in json.dumps(view)
    assert "PRIVATE_EXPERIENCE" not in json.dumps(view)
    assert view["budget"]["candidate_trajectories"] == 32 and view["budget"]["M"] == 4

def test_actual_nonfirst_latency_is_not_reconstructed_from_roster_order(tmp_path):
    archive, packet, source = setup(tmp_path)
    source["templates"][0]["samples"][0]["terminal"]["sample_seconds"] = 9.
    packet["groups"][0]["members"][0]["execution"]["wall_time_seconds"] = 9.
    packet["business_measurements"][0].update(mean_sample_seconds=5., non_first_mean_seconds=9.)
    packet["abstract_source"]["source_sha256"] = content_hash(source)
    repin(archive, packet)
    view = learning.context_population_actor_view(archive, input_sha256=packet["input_sha256"], source=source)
    assert view["business_measurements"][0]["non_first_mean_seconds"] == 9.
    assert view["business_measurements"][0]["mean_sample_seconds"] == 5.

@pytest.mark.parametrize("fault", ["absent", "short", "mean", "identity", "quality", "timing-pin"])
def test_reject_missing_or_inconsistent_measured_objectives(tmp_path, fault):
    archive, packet, source = setup(tmp_path)
    if fault == "absent": packet.pop("business_measurements")
    elif fault == "short": packet["business_measurements"].pop()
    elif fault == "mean": packet["business_measurements"][0]["mean_sample_seconds"] = 999.
    elif fault == "identity": packet["business_measurements"][0]["candidate_id"] = "branch-02"
    elif fault == "quality": packet["business_measurements"][0]["slu_f1"] = .99
    else: packet["business_measurements"][0]["timing_report_sha256"] = "not-pinned"
    repin(archive, packet)
    with pytest.raises(ValueError):
        learning.context_population_actor_view(archive, input_sha256=packet["input_sha256"], source=source)
