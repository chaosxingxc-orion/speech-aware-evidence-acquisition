"""Root-only numeric stage persistence over synthetic verified sources."""
import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest
from speech_aware_evidence_acquisition.analysis import slurp_process_metrics as metrics
from speech_aware_evidence_acquisition.analysis import system_architecture_read as architecture
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from test_slurp_solver_stage_attribution import _source, _reference, _saved_row, _answer, _sha
from test_system_architecture_read import process_fixture
from test_manual_architecture_process_derivative import fixture, repin, m


def built(answers=None):
    answers = answers or {"slurp:devel:one": [_answer("weather", "query", ("city", "paris"))]}
    source = _source(answers)
    refs = tuple(_reference(sid) for sid in source.sample_ids)
    args = dict(reference_records=refs,
        official_final_rows=tuple(_saved_row(ref, source.output_rows[ref.sample_id]["text"]) for ref in refs),
        reference_binding_sha256="d"*64, official_score_result_sha256="e"*64, legal_slot_types=("city",))
    return source, args


def validate(report):
    return metrics.validate_solver_stage_statistics(report["solver_stage_statistics"],
        rows=report["rows"], custody=report["custody"], source=report["source"])


def test_default_exact_legacy_payload_and_root_only_projection():
    source, args = built()
    legacy = metrics.build_slurp_process_metrics(source, **args)
    explicit = metrics.build_slurp_process_metrics(source, **args, solver_stage_statistics=False)
    richer = metrics.build_slurp_process_metrics(source, **args, solver_stage_statistics=True)
    assert legacy == explicit == {k:v for k,v in richer.items() if k != "solver_stage_statistics"}
    stage = richer["solver_stage_statistics"]
    assert stage["source"] == legacy["source"] and stage["root_only"]
    assert stage["learner_export_allowed"] is False
    assert "paris" not in json.dumps(stage) and "weather" not in json.dumps(stage["rows"])
    assert set(stage["rows"][0]) == {"sample_id", "metrics", "revision", "custody"}
    assert set(stage["rows"][0]["metrics"]) == {"draft", "pre_delivery", "final"}
    assert stage["aggregate"]["stages"]["draft"]["exactness"]["intent"]["correct"] == 1
    validate(richer)


def test_unparsed_unknown_entities_preserve_fixed_n_and_intent_full_failures():
    source, args = built({"slurp:devel:unparsed": ["invalid"]})
    report = metrics.build_slurp_process_metrics(source, **args, solver_stage_statistics=True)
    stage = report["solver_stage_statistics"]["aggregate"]["stages"]["draft"]
    assert stage["parse"] == {"parsed": 0, "unparsed": 1, "unavailable": 0}
    assert stage["exactness"]["entity"] == {"correct":0,"known":0,"unknown":1,"fixed_n":1,"fixed_n_value":0.0}
    assert stage["exactness"]["full"]["known"] == stage["exactness"]["intent"]["known"] == 1
    assert report["solver_stage_statistics"]["aggregate"]["transitions"]["raw_model"]["entity"]["unknown"] == 1


def test_raw_harm_repaired_by_postprocessing_is_not_model_repair(monkeypatch):
    from speech_aware_evidence_acquisition.rails import slurp_projection_v3 as v3
    from speech_aware_evidence_acquisition.rails.delivery_normalisers import SlurpProjectionV3DeliveryNormaliser
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import legal_intent_inventory
    monkeypatch.setattr(v3, "_default_legal_intent_inventory", lambda: legal_intent_inventory({"weather": ("query",)}))
    sid = "slurp:devel:normalised"
    correct = _answer("weather", "query", ("city", "paris"))
    wrong = _answer("weather", "query", ("city", "PARIS"))
    source = _source({sid:[correct, wrong]})
    normalised = SlurpProjectionV3DeliveryNormaliser()(wrong)
    phase = source.phase_results[sid]
    phase["native_episode_receipt"]["deliver_normaliser"] = dict(normalised.receipt)
    phase["final_response_text"] = normalised.text
    phase["final_response_sha256"] = _sha(normalised.text)
    source.output_rows[sid].update(text=normalised.text, carrier_lock_key="slurp")
    ref = _reference(sid)
    report = metrics.build_slurp_process_metrics(source, reference_records=(ref,),
        official_final_rows=(_saved_row(ref, normalised.text),), reference_binding_sha256="d"*64,
        official_score_result_sha256="e"*64, legal_slot_types=("city",), solver_stage_statistics=True)
    transitions = report["solver_stage_statistics"]["aggregate"]["transitions"]
    assert transitions["raw_model"]["entity"]["correct_to_wrong"] == 1
    assert transitions["raw_model"]["entity"]["net_repairs"] == -1
    assert transitions["postprocessing"]["entity"]["wrong_to_correct"] == 1
    assert report["transitions"]["entity"]["stable_correct"] == 1
    validate(report)


@pytest.mark.parametrize("fault", ["partial", "duplicate", "order", "source", "phase", "row-hash", "row", "aggregate", "transition", "parse", "revision", "custody", "text", "semantics", "typed", "native"])
def test_tampered_stage_payload_refused(fault):
    correct = _answer("weather", "query", ("city", "paris"))
    source, args = built({"slurp:devel:one":[correct],"slurp:devel:two":[correct]})
    report = metrics.build_slurp_process_metrics(source, **args, solver_stage_statistics=True)
    stage = report["solver_stage_statistics"]
    if fault == "partial": stage["rows"].pop()
    elif fault == "duplicate": stage["rows"][1] = copy.deepcopy(stage["rows"][0])
    elif fault == "order": stage["rows"].reverse()
    elif fault == "source": stage["source"]["config_hash"] = "f"*64
    elif fault == "phase": stage["source"]["phase_artifact_sha256"] = "f"*64
    elif fault == "row-hash": stage["rows_sha256"] = "f"*64
    elif fault == "row": stage["rows"][0]["metrics"]["draft"]["intent_exact"] = 0
    elif fault == "aggregate": stage["aggregate"]["stages"]["draft"]["exactness"]["entity"]["correct"] = 0
    elif fault == "transition": stage["aggregate"]["transitions"]["raw_model"]["entity"]["unknown"] = 1
    elif fault == "parse": stage["aggregate"]["stages"]["draft"]["parse"]["parsed"] = 0
    elif fault == "revision": stage["rows"][0]["revision"]["delivered_solver_revision"] = True
    elif fault == "custody": stage["rows"][0]["custody"]["initial_solver"]["response_sha256"] = "f"*64
    elif fault == "text": stage["rows"][0]["metrics"]["draft"]["answer"] = correct
    elif fault == "semantics": stage["semantics"] = "causal model repair"
    elif fault == "typed": stage["rows"][0]["metrics"]["draft"]["parsed"] = 1
    elif fault == "native": stage["rows"][0]["metrics"]["draft"]["native_fields"]["slot_f1_exact_tp"] = float("nan")
    if fault not in {"row-hash", "row"}:
        stage["rows_sha256"] = content_hash(stage["rows"]) if fault != "native" else stage["rows_sha256"]
    with pytest.raises(ValueError): validate(report)


def declare_fixture(f):
    declaration = copy.deepcopy(metrics.SOLVER_STAGE_STATISTICS_DECLARATION)
    scope_path = Path(f.inputs["root_diagnostic_scope"]["path"])
    fixed = json.loads(scope_path.read_text())
    fixed["solver_stage_statistics"] = declaration
    f.inputs["root_diagnostic_scope"] = f.save(scope_path, fixed)
    new_pin = {"relpath": "coordination/scope.json", "sha256": f.inputs["root_diagnostic_scope"]["sha256"]}
    f.root_read["diagnostic_scope"] = new_pin
    f.execution["diagnostic_scope"] = new_pin
    f.execution["root_read_authority"] = f.save(Path(f.execution["root_read_authority"]["path"]), f.root_read)
    f.execution["solver_stage_statistics"] = declaration
    for label, source in list(f.sources.items()):
        f.sources[label] = replace(source, phase_artifact_sha256=f.inputs["members"][label]["phase_artifact"]["sha256"])
    repin(f)


def test_existing_derivative_persists_complete_declared_stages_only(tmp_path, monkeypatch):
    f = fixture(tmp_path, monkeypatch)
    declare_fixture(f)
    result = m.run(f.inputs, **f.args)
    process = json.loads((f.args["output"] / "process-v2.json").read_text())
    comparison = json.loads((f.args["output"] / "comparison-v2.json").read_text())
    assert result["model_contacts"] == result["scorer_contacts"] == 0
    assert all("solver_stage_statistics" in value for value in process["members"].values())
    assert all("rows" not in value["solver_stage_statistics"] for value in comparison["process"].values())
    assert comparison["business"]["paired_comparisons"] == f.business["branches"]
    assert "Root-only diagnostic Solver endpoints" in (f.args["output"] / "report.md").read_text()
    assert process["members"]["review-off"]["solver_stage_statistics"]["aggregate"]["review_applicability"]["not_applicable"] == 2
    assert m.read_absolute(f.args["business_report_pin"]) == f.business


@pytest.mark.parametrize("fault", ["absent-scope", "absent-execution", "wrong-schema", "export", "typed", "different-phase"])
def test_stage_scope_refuses_before_quality_or_persistence(tmp_path, monkeypatch, fault):
    f = fixture(tmp_path, monkeypatch)
    declare_fixture(f)
    if fault == "absent-scope":
        path = Path(f.inputs["root_diagnostic_scope"]["path"])
        fixed = json.loads(path.read_text());fixed.pop("solver_stage_statistics")
        f.inputs["root_diagnostic_scope"] = f.save(path, fixed)
    elif fault == "absent-execution": f.execution.pop("solver_stage_statistics")
    elif fault == "wrong-schema": f.execution["solver_stage_statistics"]["schema"] = "unknown"
    elif fault == "export": f.execution["solver_stage_statistics"]["learner_export"] = True
    elif fault == "typed": f.execution["solver_stage_statistics"]["root_only"] = 1
    else: f.sources["seed"] = replace(f.sources["seed"], phase_artifact_sha256="f"*64)
    repin(f)
    with pytest.raises(ValueError): m.run(f.inputs, **f.args)
    assert not f.args["output"].exists()
    if fault != "different-phase": assert not f.events


def test_complete_family_default_refuses_unsolicited_stage_payload(tmp_path, monkeypatch):
    values = process_fixture(tmp_path, monkeypatch)
    values["process"]["members"]["seed"]["solver_stage_statistics"] = {}
    with pytest.raises(ValueError): architecture.combine_process(**values)


@pytest.mark.parametrize("field", ["phase_artifact_sha256", "reference_binding_sha256",
    "official_score_result_sha256", "config_hash", "protocol_hash", "split_identity_hash",
    "ordered_sample_ids_sha256", "run_id", "attempt_id"])
def test_every_original_stage_source_pin_is_independently_bound(field):
    source, args = built()
    report = metrics.build_slurp_process_metrics(source, **args, solver_stage_statistics=True)
    report["solver_stage_statistics"]["source"][field] = "f" * 64
    with pytest.raises(ValueError): validate(report)


def test_stage_aggregate_types_and_native_f1_are_rederived():
    source, args = built()
    report = metrics.build_slurp_process_metrics(source, **args, solver_stage_statistics=True)
    changed = copy.deepcopy(report)
    changed["solver_stage_statistics"]["aggregate"]["sample_count"] = True
    with pytest.raises(ValueError): validate(changed)
    changed = copy.deepcopy(report)
    changed["solver_stage_statistics"]["rows"][0]["metrics"]["draft"]["slot_f1_exact_f1"] = 0.0
    changed["solver_stage_statistics"]["rows_sha256"] = content_hash(changed["solver_stage_statistics"]["rows"])
    with pytest.raises(ValueError): validate(changed)


def test_registered_stage_pairs_join_same_ids_across_different_orders():
    from speech_aware_evidence_acquisition.analysis.system_process_report import _paired_solver_stage_counts
    correct = _answer("weather", "query", ("city", "paris"))
    wrong = _answer("calendar", "query", ("city", "paris"))
    primary, args = built({"slurp:devel:a":[correct], "slurp:devel:b":[wrong]})
    candidate, candidate_args = built({"slurp:devel:b":[correct], "slurp:devel:a":["invalid"]})
    primary = metrics.build_slurp_process_metrics(primary, **args, solver_stage_statistics=True)
    candidate = metrics.build_slurp_process_metrics(candidate, **candidate_args, solver_stage_statistics=True)
    process = {"members":{"parent":primary,"aa":copy.deepcopy(primary),"candidate":candidate}}
    recipe = {"sample_ids":["slurp:devel:a","slurp:devel:b"],
              "comparison_groups":{"registered":["parent","aa",["candidate"]]}}
    paired = _paired_solver_stage_counts(recipe, process)["groups"]["registered"]
    assert set(paired) == {"same-request-null", "candidate-minus-parent", "candidate-minus-aa"}
    counts = paired["candidate-minus-parent"]["diagnostic_sufficient_counts"]["draft"]
    assert counts["intent"]["member_only_correct"] == counts["intent"]["comparator_only_correct"] == 1
    assert counts["entity"]["unknown_pairs"] == 1 and counts["entity"]["fixed_n"] == 2
    assert counts["entity"]["fixed_n_correct_difference"] == -1
    process["members"]["undeclared"] = copy.deepcopy(candidate)
    assert _paired_solver_stage_counts(recipe, process)["groups"]["registered"] == paired


def test_existing_member_aggregate_excludes_all_stage_rows_and_custody():
    from test_manual_architecture_member_read import m as member
    source, args = built()
    process = metrics.build_slurp_process_metrics(source, **args, solver_stage_statistics=True)
    clock = {"content_sha256":"a"*64,"first_admitted_sample":{"sample_id":"opaque", "at_utc":"opaque"}}
    filtered, _ = member.aggregate_only(process, clock, {"by_role":{}})
    assert "solver_stage_statistics" not in filtered
    assert "rows" not in filtered and "custody" not in filtered and "source" not in filtered
    assert "rows" not in filtered["delivery_stages"]


def test_unavailable_endpoints_remain_unknown_on_the_complete_fixed_roster():
    from speech_aware_evidence_acquisition.core.delivery import native_abstention_records
    sid = "slurp:devel:abstain"
    source = _source({sid:[_answer("weather", "query")]})
    episode = source.phase_results[sid]["native_episode_receipt"]
    interrupted = episode["role_visits"].pop()
    rejected = interrupted["execution_receipt"]["final_contact"]
    episode.pop("accepted_solver_receipt")
    episode["interrupted_role"] = interrupted
    episode["terminal_disposition"] = {"reason":"finite_completion", "finish_reason":"length",
        "role_id":"solver", "stage":"solver", "revision_count":0, "planner_accepted":False,
        "rejected_contact":rejected}
    episode["abstention_receipt"] = {"source_contact":rejected}
    derived_id, request, response = native_abstention_records(sample_id=sid, source_contact=rejected, finish_reason="length")
    source.phase_results[sid].update(final_response_text="",final_response_sha256=_sha(""))
    source.output_rows[sid].update(text="",request_id=derived_id,request_sha256=request["payload_sha256"],
        response_sha256=response["response_sha256"],response_text_sha256=response["response_text_sha256"])
    ref = _reference(sid)
    report = metrics.build_slurp_process_metrics(source, reference_records=(ref,),
        official_final_rows=(_saved_row(ref,""),),reference_binding_sha256="d"*64,
        official_score_result_sha256="e"*64,legal_slot_types=("city",),solver_stage_statistics=True)
    stage = report["solver_stage_statistics"]
    for endpoint in ("draft","pre_delivery"):
        assert stage["aggregate"]["stages"][endpoint]["parse"]["unavailable"] == 1
        assert stage["aggregate"]["stages"][endpoint]["exactness"]["intent"]["unknown"] == 1
        assert stage["aggregate"]["stages"][endpoint]["exactness"]["intent"]["fixed_n"] == 1
    assert stage["rows"][0]["revision"]["delivered_solver_revision"] is None
    validate(report)
