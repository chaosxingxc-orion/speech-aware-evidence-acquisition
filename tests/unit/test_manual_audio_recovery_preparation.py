"""Model-free recovery composition and sealed-output reuse; no runtime launch."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import pytest
from speech_aware_evidence_acquisition.core.preparation import digest, load_artifact, prepare_artifact
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("audio_recovery_prepare", ROOT / "scripts/preparation/prepare_manual_audio_recovery.py")
helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)


@pytest.mark.parametrize("label,bound", [("seed",3820),("seed-aa",3820),("review-off",588),("solver-lookup",882)])
def test_actual_original_four_configs_change_only_explicit_audio_and_identities(label, bound):
    stem = "slurp-native-stage3-simple-consumption-" + label + "-n100-v1"
    ep = json.loads((ROOT / "configs/experiment" / (stem + ".json")).read_bytes())
    bp = json.loads((ROOT / "configs/baseline" / (stem + ".json")).read_bytes())
    before = deepcopy((ep,bp))
    new_ep, new_bp, row = helper.successor_documents(ep,bp,suffix="audio-recovery1-v1",
        report={"required_integer_audio_seconds":bound})
    assert (ep,bp) == before
    assert new_ep["execution_plan"]["planned_speech_audio_seconds"] == max(ep["execution_plan"]["planned_speech_audio_seconds"],bound)
    assert new_ep["execution_plan"]["planned_gpu_hours"] == ep["execution_plan"]["planned_gpu_hours"]
    assert new_ep["population"] == ep["population"] and new_ep["populations"] == ep["populations"]
    assert new_ep["family_budget"] == ep["family_budget"]
    assert new_bp["knowledge_stores"] == bp["knowledge_stores"] and new_bp["native_episode"] == bp["native_episode"]
    assert row["run_id"] != ep["cells"][0]["run_id"] and row["fit_run_id"] != bp["native_contact_fit"]["run_id"]
    assert new_ep["cells"][0]["readiness"]["state"] == "held" and "prepared_phase_supply" not in new_bp


@pytest.mark.parametrize("bound", [None,0,-1,True,3819.5])
def test_bad_derivation_refused(bound):
    ep = {"cells":[{}]}
    with pytest.raises(PolicyError,match="positive integer ceiling"):
        helper.successor_documents(ep,{},suffix="audio-recovery1-v1",report={"required_integer_audio_seconds":bound})


def source_fixture(tmp_path):
    ids = ["s3","s1"]
    parent_output = {"facets":{},"values":{"perception":{x:{"supplied":"synthetic-"+x} for x in ["s1","s2","s3"]}}}
    selected = {"facets":{},"values":{"perception":{x:parent_output["values"]["perception"][x] for x in ids}}}
    def envelope(name,output):
        path=tmp_path/name
        helper.save(path,{"output":output,"output_sha256":digest(output)})
        return helper.pin(path,tmp_path)
    receipt={"prepared_phase_supply":envelope("selected.json",selected),
             "source_prepared_phase_supply":envelope("parent.json",parent_output),"output_sha256":digest(selected)}
    return ids,receipt,selected


def test_reenvelope_changes_inputs_only_and_preserves_original_bytes(tmp_path):
    ids,receipt,selected = source_fixture(tmp_path)
    before={p:p.read_bytes() for p in tmp_path.glob("*.json")}
    original=helper.verified_source_output(receipt,tmp_path,ids)
    inputs={"config_sha256":"b"*64,"split_identity_hash":"c"*64,"sources":{"implementation":{"runtime":"d"*64}}}
    path=tmp_path/"fresh"/"phase-supply-v1.json"
    prepare_artifact(path,kind="phase-supply",inputs=inputs,producer=lambda:deepcopy(original["output"]))
    assert load_artifact(path,expected_sha256=helper.pin(path,tmp_path)["sha256"],kind="phase-supply",inputs=inputs)==selected
    assert all(p.read_bytes()==raw for p,raw in before.items())


@pytest.mark.parametrize("fault",["parent-seal","selected-forgery","missing-selected","raw-pin"])
def test_original_parent_or_selected_output_mismatch_refused(tmp_path,fault):
    ids,receipt,selected=source_fixture(tmp_path)
    field="source_prepared_phase_supply" if fault in ("parent-seal","missing-selected") else "prepared_phase_supply"
    path=tmp_path/receipt[field]["relpath"]
    value=json.loads(path.read_bytes())
    if fault=="parent-seal": value["output_sha256"]="a"*64
    elif fault=="missing-selected":
        value["output"]["values"]["perception"].pop(ids[0]);value["output_sha256"]=digest(value["output"])
    elif fault=="selected-forgery":
        value["output"]["values"]["perception"][ids[0]]={"supplied":"changed"}
        value["output_sha256"]=receipt["output_sha256"]=digest(value["output"])
    else: value["output_sha256"]="a"*64
    path.write_text(json.dumps(value))
    if fault!="raw-pin": receipt[field]=helper.pin(path,tmp_path)
    with pytest.raises(PolicyError): helper.verified_source_output(receipt,tmp_path,ids)
