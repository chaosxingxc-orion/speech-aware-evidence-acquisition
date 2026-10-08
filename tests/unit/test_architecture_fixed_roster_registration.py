"""Stable-prefix admission binds approved original sources without contacts."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pytest
from speech_aware_evidence_acquisition.rails import architecture_natural_registration as admission
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError
from speech_aware_evidence_acquisition.core.config import compose
from speech_aware_evidence_acquisition.analysis.native_graph_capacity import native_graph_capacity_budget
ROOT = Path(__file__).resolve().parents[2]


def raw(rel):
    return {"relpath": rel, "sha256": hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()}


def example(count):
    old = "configs/experiments/slurp-simple-consumption-architecture-n20-v2.json"
    full = "configs/dataset/slurp-speech-native-system-text-update-2-400-v1.json"
    extent = {"schema": "saea-manual-architecture-fixed-roster-extent-v1",
              "source_population": raw(old), "runtime_view": raw(full),
              "count": count, "selection_seed": 20261001}
    population = json.loads((ROOT / old).read_bytes())
    population["experiment_id"] = f"slurp-simple-consumption-architecture-n{count}-v1"
    population["cohorts"][0]["sample_ids"] = [r["sample_id"] for r in json.loads((ROOT / full).read_bytes())["items"]][:count]
    plans = {r: {"architecture_proof": admission.FIXED_ROSTER_SELECTOR,
                 "architecture_extent": deepcopy(extent)} for r in ("generation", "fit")}
    return {"architecture_extent": extent}, plans, population


@pytest.mark.parametrize("count", [100, 400])
def test_real_original_stable_prefix(count):
    values, plans, population = example(count)
    original, pin = admission._fixed400_basis(values, plans, population, repo_root=ROOT)
    assert population["cohorts"][0]["sample_ids"][:20] == original["cohorts"][0]["sample_ids"]
    assert pin == values["architecture_extent"]["source_population"]


@pytest.mark.parametrize("mutation", ["raw-view", "raw-policy", "seed", "count", "selector", "roster", "policy"])
def test_fixed_prefix_authority_mismatch_refused(mutation):
    values, plans, population = example(100)
    extent = values["architecture_extent"]
    if mutation == "raw-view": extent["runtime_view"]["sha256"] = "e" * 64
    elif mutation == "raw-policy": extent["source_population"]["sha256"] = "e" * 64
    elif mutation == "seed": extent["selection_seed"] = 20261002
    elif mutation == "count": extent["count"] = 101
    elif mutation == "selector": plans["fit"]["architecture_proof"] = "manual-architecture-n20-v1"
    elif mutation == "roster": population["cohorts"][0]["sample_ids"][-1] = "slurp:train:foreign"
    elif mutation == "policy": population["architecture"]["members"][0]["model_per_trajectory"] += 1
    if mutation != "selector":
        for p in plans.values(): p["architecture_extent"] = deepcopy(extent)
    with pytest.raises((PolicyError, ValueError)):
        admission._fixed400_basis(values, plans, population, repo_root=ROOT)


@pytest.mark.parametrize("label,ceiling", [("seed",299),("seed-aa",299),("review-off",157),("solver-lookup",241)])
def test_pure_capacity_ceiling_freshly_derived(label, ceiling):
    report=json.loads((ROOT / "docs/readiness/2026-10-07-slurp-simple-consumption-prepared-graph-recovery2-v1/prepared-capacities-v3.json").read_bytes())
    member=next(m for m in report["members"] if m["label"] == label)
    name=member["new_capacity"]
    cell=json.loads((ROOT / "configs/experiment" / (name + ".json")).read_bytes())["cells"][0]
    values=compose(ROOT,cell["model_fragment"],cell["dataset_fragment"],cell["baseline_fragment"],name).values
    budget=native_graph_capacity_budget(values,slot_value_count=54,intent_value_count=60,
                                      graph_rows=4,media_parts=1,profile=values["native_graph_capacity_profile"])
    assert budget["contact_cap"] == ceiling
    assert budget["ranking_tokenizer_endpoints"] == 114


def public_n100_fixture(tmp_path, monkeypatch):
    """Stub only fresh raw evidence dependencies; retain natural and supply gates."""
    from dataclasses import asdict, replace
    from types import SimpleNamespace
    import test_architecture_n20_registration as legacy
    from speech_aware_evidence_acquisition.contracts import ExecutionPlan
    from speech_aware_evidence_acquisition.core.config import _canonical_hash, protocol_hash
    from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash
    args = legacy.fixture(tmp_path, monkeypatch)
    old_capacity = args["registered_plans"][0]["capacity_prerequisite"]
    original_capacity = admission._qualified_capacity
    original_read = admission._read_pin
    original_load = admission.load_population_config
    original_compose = admission.compose
    original_cells = admission.load_campaign_cells
    values, plans, population = example(100)
    extent = values["architecture_extent"]
    new_pop = legacy.write(tmp_path, "new-population.json", population)
    monkeypatch.setattr(admission, "load_population_config", lambda pin, **kw:
        deepcopy(population) if pin == new_pop else original_load(pin, **kw))
    compositions, cells, eligible = {}, {}, []
    roster = population["cohorts"][0]["sample_ids"]
    for label in legacy.LABELS:
        name = f"slurp-native-stage3-simple-consumption-{label}-n100-v1"
        (old_cell,) = original_cells(ROOT, f"slurp-native-stage3-simple-consumption-{label}-n20-v2")
        c = deepcopy(old_cell.document)
        v = deepcopy(original_compose(ROOT, c["model_fragment"], c["dataset_fragment"],
                                      c["baseline_fragment"], c["cell_id"]).values)
        c.update(cell_id=name, run_id=f"N100-{label}", attempt_id=f"N100-{label}-attempt")
        v.update(experiment_population=new_pop, architecture_extent=deepcopy(extent),
                 population_budget=admission.population_accounting(population,"comparison"))
        v["population"].update(count=100,split_identity_hash=split_identity_hash(prefixed("slurp",roster)))
        v["populations"][0]["ids"] = deepcopy(roster)
        cap = population["architecture"]["members"][list(legacy.LABELS).index(label)]["model_per_trajectory"] * 100
        v["execution_plan"]["planned_model_calls"] = cap
        v["native_contact_fit"].update(run_id=f"N100-{label}-FIT",attempt_id=f"N100-{label}-FIT-attempt",contact_cap=cap*4)
        v["family_budget"].update(complete_system_trajectories=100,generation_calls_cap=cap,actual_request_fit_endpoint_cap=cap*4)
        # The named audio gate consumes exact runtime-view duration metadata.
        # Enlarging only ids would leave the inherited N20 duration inventory stale.
        from speech_aware_evidence_acquisition.rails.architecture_audio_budget import derive_manual_architecture_audio_budget
        view = json.loads((ROOT / extent["runtime_view"]["relpath"]).read_bytes())
        by_id = {row["sample_id"]: row for row in view["items"]}
        v["items"] = [deepcopy(by_id[sid]) for sid in roster]
        derived = derive_manual_architecture_audio_budget(v)
        v["execution_plan"]["planned_speech_audio_seconds"] = max(
            v["execution_plan"]["planned_speech_audio_seconds"], derived["required_integer_audio_seconds"])
        cells[name] = SimpleNamespace(document=c)
        compositions[name] = SimpleNamespace(values=v,config_hash=_canonical_hash(v))
        eligible.extend([c["run_id"],v["native_contact_fit"]["run_id"]])
    name = "slurp-native-stage3-simple-consumption-seed-n100-v1"
    values, cell = compositions[name].values, cells[name].document
    source_ids = [r["sample_id"] for r in json.loads((ROOT/extent["runtime_view"]["relpath"]).read_bytes())["items"]]
    full_output = {"facets":{},"values":{"perception":{sid:{"synthetic":True} for sid in source_ids}}}
    selected = {"facets":{},"values":{"perception":{sid:full_output["values"]["perception"][sid] for sid in roster}}}
    supply_pin = legacy.supply(tmp_path,"n100/supply.json",values)
    supply = json.loads((tmp_path/supply_pin["relpath"]).read_bytes())
    supply.update(output=selected,output_sha256=legacy.digest(selected))
    supply_pin = legacy.write(tmp_path,"n100/supply.json",supply)
    values["prepared_phase_supply"] = supply_pin
    compositions[name].config_hash = _canonical_hash(values)
    original_source = {"relpath":"prepared/SAEA-SLURP-SYSTEM-TEXT-UPDATE2-RH1-L-PARENT-V1/phase-supply-v1.json",
                       "sha256":"99ba974066d6a87f086e8850c316252857e205e5213387e9ae7ed030c22900f0"}
    fresh = {"registration":legacy.write(tmp_path,"fresh/registration.json",{"synthetic":"fresh100"}),
             "qualification":legacy.write(tmp_path,"fresh/qualification.json",{"synthetic":"qualified100"})}
    historical, qualified = original_capacity(json.loads((ROOT/extent["source_population"]["relpath"]).read_bytes()),
                  extent["source_population"],old_capacity,repo_root=ROOT,data_root=tmp_path)
    capacity = deepcopy(historical)
    capacity["members"][0].update(runtime_sample_ids=deepcopy(roster),
        prepared_artifact_verification={"capacity":{"prepared_pin":supply_pin}})
    monkeypatch.setattr(admission,"_qualified_capacity",lambda pop,pin,prerequisite,**kw:
        (deepcopy(capacity),deepcopy(qualified)) if prerequisite == fresh else original_capacity(pop,pin,prerequisite,**kw))
    receipt = json.loads(original_read(args["registered_plans"][0]["preparation_receipt"],ROOT))
    receipt.update(experiment=name,run_id=cell["run_id"],attempt_id=cell["attempt_id"],
        config_hash=compositions[name].config_hash,configured_sample_ids=roster,runtime_sample_ids=roster,
        prepared_phase_supply=supply_pin,source_prepared_phase_supply=original_source,
        output_sha256=legacy.digest(selected),architecture_extent=extent)
    receipt_pin = legacy.write(tmp_path,"n100/repo-preparation.json",receipt)
    def rawread(pin,root):
        if pin == original_source:
            return json.dumps({"output":full_output,"output_sha256":legacy.digest(full_output)}).encode()
        if pin == new_pop or pin == receipt_pin:
            return original_read(pin,tmp_path)
        return original_read(pin,root)
    monkeypatch.setattr(admission,"_read_pin",rawread)
    monkeypatch.setattr(admission,"compose",lambda root,m,d,b,e:
        deepcopy(compositions[e]) if e in compositions else original_compose(root,m,d,b,e))
    monkeypatch.setattr(admission,"load_campaign_cells",lambda root,e:
        (deepcopy(cells[e]),) if e in cells else original_cells(root,e))
    split=values["population"]["split_identity_hash"]
    expected=ExecutionPlan(**values["execution_plan"],run_id=cell["run_id"],attempt_id=cell["attempt_id"],
        carrier_lock_key="slurp",split_identity_hash=split,
        protocol_hash=protocol_hash(compositions[name].config_hash,values["arm"],split)).validate()
    pair=args["registered_plans"]
    for plan in pair:
        role=plan["plan_role"]
        bound=expected if role=="generation" else replace(expected,run_id=values["native_contact_fit"]["run_id"],
              attempt_id=values["native_contact_fit"]["attempt_id"],planned_model_calls=5200)
        plan.update(architecture_proof=admission.FIXED_ROSTER_SELECTOR,architecture_extent=extent,
            experiment_population=new_pop,population_budget=values["population_budget"],cell=name,experiment=name,
            composed_config_hash=compositions[name].config_hash,configured_sample_ids=roster,runtime_sample_ids=roster,
            prepared_phase_supply=supply_pin,capacity_prerequisite=fresh,preparation_receipt=receipt_pin,
            execution_plan=asdict(bound),run_id=bound.run_id,attempt_id=bound.attempt_id)
    decision=legacy.write(tmp_path,"n100/admission.json",dict(schema="saea-campaign-decision-v1",status="decided",
        owner_decisions=[227],learner_export=False,source_preparation_commit=receipt["prepared_source_commit"],
        experiment_population=new_pop,capacity_prerequisite=fresh,natural_prerequisite=pair[0]["natural_prerequisite"],
        architecture_extent=extent,eligible_run_ids=eligible))
    for plan in pair:plan["decision_receipt"]=decision
    args.update(values=values,cell=cell)
    return args, receipt, receipt_pin, capacity, old_capacity, original_source


def test_public_n100_real_natural_bridge_and_selected_supply(tmp_path,monkeypatch):
    args,*_=public_n100_fixture(tmp_path,monkeypatch)
    result=admission.require_architecture_n20_registration(**args)
    assert len(result["sample_ids"]) == 100
    assert result["generation_cap"] == 1300 and result["fit_cap"] == 5200


@pytest.mark.parametrize("fault",["old-capacity","foreign-source","unequal-capacity-output"])
def test_public_n100_supply_or_capacity_refused(tmp_path,monkeypatch,fault):
    import test_architecture_n20_registration as legacy
    args,receipt,rpin,capacity,old_capacity,source=public_n100_fixture(tmp_path,monkeypatch)
    if fault == "old-capacity":
        for p in args["registered_plans"]:p["capacity_prerequisite"]=old_capacity
    elif fault == "foreign-source":
        receipt["source_prepared_phase_supply"]={**source,"sha256":"f"*64}
        new=legacy.write(tmp_path,rpin["relpath"],receipt)
        for p in args["registered_plans"]:p["preparation_receipt"]=new
        original=admission._read_pin
        monkeypatch.setattr(admission,"_read_pin",lambda pin,root:
            (tmp_path/new["relpath"]).read_bytes() if pin==new else
            original(source,root) if pin==receipt["source_prepared_phase_supply"] else original(pin,root))
    else:
        bad={"output":{"facets":{},"values":{}},"output_sha256":"e"*64}
        pin=legacy.write(tmp_path,"fresh/unequal.json",bad)
        capacity["members"][0]["prepared_artifact_verification"]["capacity"]["prepared_pin"]=pin
    with pytest.raises((PolicyError,ValueError)):admission.require_architecture_n20_registration(**args)


def test_existing_named_checker_routes_fixed_roster_pair(tmp_path,monkeypatch):
    from test_flight_registration_check import gate
    from types import SimpleNamespace
    from speech_aware_evidence_acquisition.core.config import _canonical_hash
    import speech_aware_evidence_acquisition.core.config as config_module
    import test_architecture_n20_registration as legacy
    args,*_=public_n100_fixture(tmp_path,monkeypatch)
    cell,values=args["cell"],args["values"]
    package=tmp_path/"packages"/"n100"
    monkeypatch.setattr(gate,"READINESS",package.parent)
    for plan in args["registered_plans"]:
        legacy.write(package,plan["plan_role"]+"-plan-registered-v1.json",plan)
    original=config_module.compose
    monkeypatch.setattr(config_module,"compose",lambda root,m,d,b,e:
        SimpleNamespace(values=values,config_hash=_canonical_hash(values)) if e==cell["cell_id"] else original(root,m,d,b,e))
    baseline=deepcopy(values)
    fragment={"experiment_id":cell["run_id"],"cells":[cell]}
    report=gate.CellReport(experiment=cell["cell_id"],cell_id=cell["cell_id"],run_id=cell["run_id"],state="held",named=True)
    report.run_ids={"generation":cell["run_id"],"native_contact_fit":values["native_contact_fit"]["run_id"]}
    gate._check_registered_supply_binding(report,baseline,gate.PackageIndex(ROOT),"n100",{},
        cell=cell,fragment=fragment,data_root=tmp_path)
    assert not report.findings
