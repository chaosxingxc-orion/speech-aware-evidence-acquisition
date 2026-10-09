"""Configuration identity reaches scope, prelaunch and the shared proposal compiler."""
from copy import deepcopy
import json
from types import SimpleNamespace
import pytest
from test_experiment_population_config import config
from test_context_population_scope import population, scope
from test_system_context_learning import pin, repin
from test_context_population_update import fixture as update_fixture
from speech_aware_evidence_acquisition.rails import system_context_learning as learning
from speech_aware_evidence_acquisition.rails.experiment_population import population_accounting
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError


def configured(tmp_path, monkeypatch, k):
    f, _ = population(tmp_path, monkeypatch)
    d = config((k,), 20)
    ids = f.protocol["candidate_members"][:k]
    d["cohorts"][0]["candidate_ids"] = ids
    d["cohorts"][0]["sample_ids"] = list(f.recipe["sample_ids"])
    ref = pin(tmp_path, "experiment-population.json", d)
    budget = population_accounting(d, "cohort-0")
    for item in (f.recipe, f.registration, f.protocol):
        item.update(experiment_population=ref, population_cohort="cohort-0", population_budget=budget)
    f.protocol.pop("population_authorization")
    f.protocol.update(K=k, candidate_members=ids)
    f.registration["member_bindings"] = {c:v for c,v in f.registration["member_bindings"].items() if c in ids+["seed","seed-aa"]}
    f.registration["expected_members"] = {c:v["run_id"] for c,v in f.registration["member_bindings"].items()}
    f.recipe["expected_members"] = deepcopy(f.registration["expected_members"])
    repin(f)
    return f, d, ref


@pytest.mark.parametrize("k", [3, 8, 16])
def test_scope_resolves_population_from_file(tmp_path, monkeypatch, k):
    f, _, _ = configured(tmp_path, monkeypatch, k)
    assert len(scope(f)[0]) == k


@pytest.mark.parametrize("fault", ["K", "nodes", "sampling", "budget", "recipe-pin", "cohort", "file"])
def test_scope_refuses_configuration_drift(tmp_path, monkeypatch, fault):
    f, d, ref = configured(tmp_path, monkeypatch, 8)
    if fault == "K": f.protocol["K"] = 16
    elif fault == "nodes": f.protocol["M"].reverse()
    elif fault == "sampling": f.protocol["sampling"]["seed"] += 1
    elif fault == "budget": f.registration["population_budget"]["family_trajectories"] += 1
    elif fault == "recipe-pin": f.recipe["experiment_population"] = {**ref,"sha256":"0"*64}
    elif fault == "cohort": f.recipe["population_cohort"] = "other"
    else: (tmp_path/"experiment-population.json").write_text("{}")
    repin(f)
    with pytest.raises((PolicyError, KeyError)): scope(f)


@pytest.mark.parametrize("k", [3, 8, 16])
def test_loaded_config_controls_reservation_and_all_response_slots(tmp_path, k):
    archive, packet, response = update_fixture(tmp_path)
    ids = list(packet["policies"])[:k]
    d = config((k,), len(packet["groups"]))
    d["cohorts"][0]["candidate_ids"] = ids
    d["cohorts"][0]["sample_ids"] = [g["sample_id"] for g in packet["groups"]]
    ref = pin(archive.root, "context-learning/configuration.json", d)
    packet.update(experiment_population=ref, population_cohort="cohort-0")
    packet["policies"] = {c:packet["policies"][c] for c in ids}
    packet["budget"] = population_accounting(d, "cohort-0")
    packet["population_update_plan"]["proposal_slots"] = k
    for g in packet["groups"]: g["members"] = g["members"][:k]
    packet.pop("input_sha256")
    packet["input_sha256"] = content_hash(packet)
    (archive.root/"context-learning/inputs/population.json").write_text(json.dumps(packet))
    response["branches"] = response["branches"][:k]
    response["input_sha256"] = packet["input_sha256"]
    for b in response["branches"]: b["proposal"]["evidence"] = [packet["input_sha256"]]
    reservation = learning.reserve_context_population_update(archive,
        input_sha256=packet["input_sha256"], actor_input_sha256="a"*64)
    assert reservation["proposal_slots"] == k
    assert reservation["experiment_population"] == ref
    result = learning.record_context_population_update(archive,
        input_sha256=packet["input_sha256"], response_document=response)
    assert len(result["records"]) == k and result["experiment_population"] == ref
    assert all(row["status"] == "provisional" for row in result["records"])
    # Rewriting the config under the old identity never grants another contact.
    (archive.root/ref["relpath"]).write_text("{}")
    with pytest.raises(PolicyError):
        learning._population_update_input(archive, packet["input_sha256"])


@pytest.mark.parametrize("fault", [None, "cell_pin", "effective_pin", "temperature", "seed", "contact_cap"])
def test_prelaunch_checks_the_config_consumed_by_runtime(tmp_path, monkeypatch, fault):
    from test_flight_registration_check import gate
    from speech_aware_evidence_acquisition.core import config as core_config
    from speech_aware_evidence_acquisition.rails import system_text_policy
    f, d, ref = configured(tmp_path, monkeypatch, 8)
    member = f.registration["member_bindings"]["branch-01"]
    cell = {"model_fragment":"m","dataset_fragment":"d","baseline_fragment":"b",
            "attempt_id":member["attempt_id"], "system_text_policy_binding":{"bundle_id":member["bundle_id"]},
            "experiment_population":deepcopy(ref), "population_cohort":"cohort-0"}
    effective = {"experiment_population":deepcopy(ref), "population_cohort":"cohort-0",
                 "system_search_measurement":f.protocol["measurement_profile"],
                 "serving_slots":4,"serving_slot_tokens":24576,"native_episode":{},
                 "decoding_params":{**d["sampling"],"max_tokens":512},
                 "server_args":["-np","4","-c","98304"],
                 "native_contact_fit":{"contact_cap":20*13*4}}
    if fault == "cell_pin": cell["experiment_population"]["sha256"] = "0"*64
    elif fault == "effective_pin": effective.pop("experiment_population")
    elif fault in ("seed","temperature"): effective["decoding_params"][fault] += 1
    elif fault == "contact_cap": effective["native_contact_fit"]["contact_cap"] += 1
    monkeypatch.setattr(core_config,"compose",lambda *a,**kw:SimpleNamespace(values=effective,config_hash=member["config_hash"]))
    monkeypatch.setattr(system_text_policy,"verify_system_text_binding",lambda *a,**kw:None)
    report=SimpleNamespace(run_id=member["run_id"],experiment="e",findings=[])
    gate._check_system_text_binding(report,cell,{},f.recipe,tmp_path,tmp_path/"data")
    assert bool(report.findings) == (fault is not None)


@pytest.mark.parametrize("role", ["generation", "fit"])
@pytest.mark.parametrize("fault", [None, "missing-pin", "cap", "missing-plan"])
def test_registered_plan_uses_config_even_without_supply_annotation(tmp_path, role, fault):
    from test_flight_registration_check import gate
    from speech_aware_evidence_acquisition.rails.experiment_population import population_stage_spec
    d = config((3,), 7)
    ref = pin(tmp_path, "population.json", d)
    spec = population_stage_spec(ref, repo_root=tmp_path, cohort_id="cohort-0")
    baseline = {k: spec[k] for k in ("experiment_population", "population_cohort")}
    run_ids = {"generation":"generation-id", "fit":"fit-id"}
    cap_key = "member_generation_contacts_cap" if role == "generation" else "member_fit_endpoints_cap"
    document = {**baseline, "run_id":run_ids[role], "execution_plan":{"planned_model_calls":spec[cap_key]}}
    if fault == "missing-pin": document.pop("experiment_population")
    elif fault == "cap": document["execution_plan"]["planned_model_calls"] += 1
    elif fault == "missing-plan": document.pop("execution_plan")
    directory = tmp_path/gate.READINESS/"package"
    directory.mkdir(parents=True)
    (directory/"member-plan-registered-v1.json").write_text(json.dumps(document))
    report = SimpleNamespace(run_ids=run_ids, findings=[])
    # The plans carry no carrier_lock_key, so the (required) exposure-ledger argument is never consulted.
    gate._check_registered_supply_binding(report, baseline, SimpleNamespace(repo_root=tmp_path), "package", {})
    assert bool(report.findings) == (fault is not None)


@pytest.mark.parametrize("k", [3, 8, 16])
def test_authoring_population_comes_from_same_file(tmp_path, k):
    from test_template_population import fixture
    from speech_aware_evidence_acquisition.rails.template_population import validate_population_response
    request, response, hashes = fixture()
    request["slots"] = request["slots"][:k]
    response["branches"] = response["branches"][:k]
    strategies = list(dict.fromkeys(s["strategy_id"] for s in request["slots"]))
    response["strategies"] = response["strategies"][:len(strategies)]
    d = config((k,), 7)
    d["cohorts"][0]["candidate_ids"] = [s["candidate_id"] for s in request["slots"]]
    ref = pin(tmp_path, "population.json", d)
    request.update(experiment_population=ref, population_cohort="cohort-0")
    assert len(validate_population_response(response, request, input_hashes=hashes, repo_root=tmp_path)) == k
    request["slots"].pop()
    with pytest.raises(PolicyError):
        validate_population_response(response, request, input_hashes=hashes, repo_root=tmp_path)


def test_shared_compiler_preserves_real_configuration_pin(tmp_path):
    from test_system_text_policy import ROOT, BASE, seed_document
    from speech_aware_evidence_acquisition.rails.system_text_policy import SystemTextPolicyBundle, compile_system_text_policy
    config_pin = json.loads((ROOT/"docs/readiness/2026-10-05-configured-population-lifecycle-v1/config-pin.json").read_text())
    baseline = json.loads((ROOT/BASE).read_text())
    baseline.update(experiment_population=config_pin, population_cohort="panel-a")
    document = seed_document()
    document["seed_config_sha256"] = content_hash(baseline)
    bundle = SystemTextPolicyBundle.from_json(document)
    compiled = compile_system_text_policy(baseline, bundle, repo_root=ROOT, output_root=tmp_path)
    assert compiled["experiment_population"] == config_pin
    assert compiled["population_cohort"] == "panel-a"
    assert compiled["scorers"] == baseline["scorers"]
    baseline["experiment_population"] = {**config_pin, "sha256":"0"*64}
    with pytest.raises(PolicyError):
        compile_system_text_policy(baseline, bundle, repo_root=ROOT, output_root=tmp_path/"bad")
    assert not (tmp_path/"bad").exists()


@pytest.mark.parametrize("fault", [None, "existing-drift", "symlink-escape"])
def test_feedback_preparation_archives_identical_config_bytes(tmp_path, monkeypatch, fault):
    from test_system_context_learning import setup, prepare
    f = setup(tmp_path, monkeypatch)
    d = config((len(f.protocol["candidate_members"]),), len(f.recipe["sample_ids"]))
    d["cohorts"][0].update(candidate_ids=f.protocol["candidate_members"], sample_ids=f.recipe["sample_ids"])
    ref = pin(tmp_path, "population.json", d)
    for document in (f.recipe, f.registration, f.protocol):
        document.update(experiment_population=ref, population_cohort="cohort-0",
                        population_budget=population_accounting(d,"cohort-0"))
    repin(f)
    target = f.archive.root/ref["relpath"]
    target.parent.mkdir(parents=True, exist_ok=True)
    if fault == "existing-drift": target.write_text("{}")
    elif fault == "symlink-escape": target.symlink_to(tmp_path/"outside.json")
    if fault:
        with pytest.raises(PolicyError): prepare(f)
        assert not (f.archive.root/"context-learning/inputs").exists()
    else:
        packet = prepare(f)
        assert packet["experiment_population"] == ref
        assert packet["budget"] == population_accounting(d,"cohort-0")
        assert target.read_bytes() == (tmp_path/ref["relpath"]).read_bytes()


def test_root_report_retains_config_binding(tmp_path):
    from test_context_population_read import population, call
    parts = population(tmp_path)
    _, recipe, registration, protocol, _, _ = parts
    d = config((len(protocol["candidate_members"]),), len(recipe["sample_ids"]))
    d["cohorts"][0].update(candidate_ids=protocol["candidate_members"], sample_ids=recipe["sample_ids"])
    ref = pin(tmp_path, "population.json", d)
    for document in (recipe, registration, protocol):
        document.update(experiment_population=ref, population_cohort="cohort-0",
                        population_budget=population_accounting(d,"cohort-0"))
    report = call(parts)
    assert report["experiment_population"] == ref
    assert report["population_budget"]["K"] == len(protocol["candidate_members"])
    recipe["experiment_population"] = {**ref,"sha256":"0"*64}
    with pytest.raises(PolicyError): call(parts)
