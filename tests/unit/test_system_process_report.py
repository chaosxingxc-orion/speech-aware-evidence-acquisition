"""Keep business, mechanism and cost evidence together without leaking raw cases."""
import copy
import pytest
from speech_aware_evidence_acquisition.analysis.system_process_report import (
    build_process_comparison, render_process_comparison,
)
from speech_aware_evidence_acquisition.analysis.slurp_process_metrics import aggregate_process_metrics, rate

def documents():
    rows = [dict(sample_id="s1", scenario="music", gold_empty=False,
                 draft_entity_correct=False, final_entity_correct=True,
                 draft_full_correct=False, final_full_correct=True,
                 review_alarm=True, review_valid=True, handoff_visible=True, revised=True)]
    metrics = aggregate_process_metrics(rows)
    metrics.update(rows=rows, custody=[{"response": "SECRET_TASK_OUTPUT"}],
                   recall_status="initial-request-card-and-candidate-projection-only",
                   intent_support={"metrics": {"card": rate([True])},
                                   "samples": [{"gold": "SECRET_GOLD"}]},
                   delivery_stages={"model_revision": {"entity": {"wrong_to_correct": 0}},
                                    "postprocessing": {"entity": {"wrong_to_correct": 1}},
                                    "rows": [{"answer": "SECRET_ANSWER"}]})
    recipe = {"family_id": "family", "run_ids": {"read": "READ"},
              "sample_ids": ["s1"], "expected_members": {"seed": "S", "child": "C"}}
    business = {"family_id": "family", "read_authority": {"read_run_id": "READ"}, "official_summaries": {
        m: {"slu_f1": .5, "intent": 1., "reliable_completion_rate": 1.,
            "model_calls": 6, "tool_calls": 0} for m in recipe["expected_members"]},
        "branches": {"context": {"aa": {"delta": .01}}},
        "per_stratum": {"music": {"n": 1}}, "equal_stratum_macro": {"seed": .5},
        "execution": {m: {"rows": 1} for m in recipe["expected_members"]}}
    process = {"read_id": "READ", "members": {m: copy.deepcopy(metrics) for m in recipe["expected_members"]}}
    timing = {m: {"all_samples": {"count": 1, "mean_seconds": 3.},
                  "excluding_first": {"count": 0, "mean_seconds": None},
                  "first_admitted_sample": {"sample_id": "s1", "elapsed_seconds": 3.},
                  "completed_samples": 1, "failed_samples": 0, "by_role": {},
                  "timing_scope": "Admission to settled workflow."}
              for m in recipe["expected_members"]}
    return dict(recipe=recipe, business=business, process=process, timing=timing)

def test_preserves_business_process_uncertainty_and_aa_without_cases():
    values=documents(); result=build_process_comparison(**values)
    assert result["business"]["paired_comparisons"] == values["business"]["branches"]
    assert result["business"]["per_stratum"] == values["business"]["per_stratum"]
    assert result["process"]["seed"]["metrics"]["review_error_detection"] == rate([True])
    assert result["process"]["seed"]["delivery_stages"]["postprocessing"]["entity"]["wrong_to_correct"] == 1
    assert result["unique_inputs"] == 1 and result["trajectories"] == 2
    assert result["resources"]["seed"]["non_first_mean_seconds"] is None
    assert result["adoption_decided"] is False and result["learner_exported"] is False
    assert "SECRET_" not in str(result) and "sample_id" not in str(result)

@pytest.mark.parametrize("surface", ["business", "process", "timing"])
def test_rejects_missing_or_extra_member(surface):
    for extra in [False, True]:
        v=documents()
        mapping=v[surface]["official_summaries"] if surface=="business" else v[surface]["members"] if surface=="process" else v[surface]
        if extra: mapping["foreign"]={}
        else: mapping.pop("seed")
        with pytest.raises(ValueError): build_process_comparison(**v)

@pytest.mark.parametrize("change", ["read", "family", "duplicate", "foreign-input", "wrong-count", "timing-count", "false-causal", "false-semantic"])
def test_rejects_wrong_sources_and_claims(change):
    v=documents(); p=v["process"]["members"]["seed"]
    if change=="read": v["process"]["read_id"]="OTHER"
    elif change=="family": v["business"]["family_id"]="OTHER"
    elif change=="duplicate": p["rows"].append(copy.deepcopy(p["rows"][0]))
    elif change=="foreign-input": p["rows"][0]["sample_id"]="other"
    elif change=="wrong-count": p["sample_count"]=2
    elif change=="timing-count": v["timing"]["seed"]["completed_samples"]=0
    elif change=="false-causal": p["claims_causal_node_credit"]=True
    else: p["claims_semantically_correct_criticism"]=True
    with pytest.raises(ValueError): build_process_comparison(**v)

def test_render_business_first_and_preserves_unknowns():
    v=documents(); v["process"]["members"]["child"]["metrics"]["review_error_detection"]=rate([None])
    result=build_process_comparison(**v); text=render_process_comparison(result)
    assert text.index("Official business outcomes") < text.index("Review and revision") < text.index("Latency and cost")
    assert "0/0; unknown 1" in text and "unavailable" in text
    assert "Model revision" in text and "Postprocessing" in text
    assert "SECRET_" not in text

def test_report_does_not_alias_source_documents():
    v=documents(); result=build_process_comparison(**v)
    result["business"]["official_summaries"]["seed"]["slu_f1"]=0
    assert v["business"]["official_summaries"]["seed"]["slu_f1"]==.5

def test_exact_same_roster_in_different_record_order_is_joined_by_identity():
    v=documents()
    v["recipe"]["sample_ids"]=["s1","s2"]
    for member in v["recipe"]["expected_members"]:
        source=v["process"]["members"][member]
        second=copy.deepcopy(source["rows"][0]);second["sample_id"]="s2"
        source["rows"]=[second,source["rows"][0]]
        source["sample_count"]=2
        v["timing"][member]["completed_samples"]=2
    result=build_process_comparison(**v)
    assert result["unique_inputs"]==2 and result["trajectories"]==4
