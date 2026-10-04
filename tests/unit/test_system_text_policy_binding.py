"""Refuse runtime role text that differs from its declared immutable policy."""
import copy
import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.rails.system_search_archive import SystemSearchArchive
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    PolicyError, SystemTextPolicyBundle, compile_system_text_policy,
    verify_system_text_binding,
)
from test_system_text_policy import seed_document, BASE, ROOT
from test_flight_registration_check import World, EXPERIMENT, RUN, PACKAGE, _write, _kinds


def add_runtime_fragments(w):
    """Give a bound cell the exact four-fragment runtime composition."""
    path = w.repo / "configs/experiment" / (EXPERIMENT + ".json")
    fragment = json.loads(path.read_text())
    fragment["cells"][0].update(model_fragment="synthetic-model",
                                 dataset_fragment="synthetic-dataset")
    _write(path, fragment)
    for kind in ("model", "dataset"):
        _write(w.repo / "configs" / kind / ("synthetic-" + kind + ".json"), {})


@pytest.fixture
def bound(tmp_path):
    repo, data = tmp_path / "worker", tmp_path / "data"
    baseline = json.loads((ROOT / BASE).read_text())
    doc = seed_document()
    doc["role_text"]["planner"] += "\nReturn exactly one bare token: ACCEPT or REVISE.\n"
    bundle = SystemTextPolicyBundle.from_json(doc)
    archive = SystemSearchArchive(data / "search")
    archive.store_policy(bundle)
    raw = (archive.root / "policies" / (bundle.bundle_id + ".json")).read_bytes()
    binding = {"schema": "saea-system-text-role-binding-v1", "bundle_id": bundle.bundle_id,
               "bundle": {"relpath": "search/policies/" + bundle.bundle_id + ".json",
                          "sha256": hashlib.sha256(raw).hexdigest()}}
    import shutil
    from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import (
        LOCK_BASELINE_FRAGMENT, LOCK_V2_0_REVIEWER_TEMPLATE, LOCK_V2_1_REVIEWER_TEMPLATE,
    )
    required = ["configs/baseline/" + LOCK_BASELINE_FRAGMENT + ".json",
                "configs/" + LOCK_V2_0_REVIEWER_TEMPLATE[0],
                "configs/" + LOCK_V2_1_REVIEWER_TEMPLATE[0]]
    required += [c["record"] for c in baseline["native_episode"]["consumption_module"]["components"]
                 if "record" in c]
    for rel in required:
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, target)
    compiled = compile_system_text_policy(baseline, bundle, repo_root=ROOT, output_root=repo)
    return compiled, binding, repo, data, baseline, bundle


def test_compiled_seed_and_candidates_match_bound_role_bytes(bound):
    compiled, binding, repo, data, baseline, bundle = bound
    before = copy.deepcopy(compiled)
    receipt = verify_system_text_binding(compiled, binding, repo_root=repo, data_root=data)
    assert receipt["bundle_id"] == bundle.bundle_id
    assert set(receipt["role_sha256"]) == {"solver", "reviewer", "planner"}
    assert compiled == before


@pytest.mark.parametrize("mutation", ["old-pointer", "changed-bytes", "bundle-hash",
    "bundle-id", "supply", "knowledge", "missing-role", "traversal", "extra-field",
    "component-pointer", "missing-baseline"])
def test_binding_refuses_mismatched_or_unpinned_runtime_before_contact(bound, mutation):
    c, b, repo, data, old, bundle = bound
    if mutation == "old-pointer":
        c["phase_material"]["planner"] = old["phase_material"]["planner"]
    elif mutation == "changed-bytes":
        (repo / "configs" / c["phase_material"]["planner"]["instruction_template"]).write_text("ACCEPT")
    elif mutation == "bundle-hash":
        b["bundle"]["sha256"] = "0" * 64
    elif mutation == "bundle-id":
        b["bundle_id"] = "0" * 64
    elif mutation == "supply":
        c["phase_tools"]["planner"]["knowledge_value_limit"] = 1
    elif mutation == "knowledge":
        c["knowledge_stores"]["slot-contracts"]["snapshot"]["sha256"] = "0" * 64
    elif mutation == "missing-role":
        del c["phase_material"]["reviewer"]
    elif mutation == "traversal":
        b["bundle"]["relpath"] = "../outside.json"
    elif mutation == "extra-field":
        b["ignore_mismatch"] = True
    elif mutation == "missing-baseline":
        c = None
    else:
        for item in c["native_episode"]["consumption_module"]["components"]:
            if item["component_id"] == "knowledge-consumption-opportunity":
                item["params"]["planner_template"] = "probes/old.txt"
    with pytest.raises((PolicyError, ValueError), match="."):
        verify_system_text_binding(c, b, repo_root=repo, data_root=data)


def test_uncompiled_seed_is_not_a_runtime_bundle(bound):
    _, binding, repo, data, baseline, _ = bound
    with pytest.raises(PolicyError, match="role|template"):
        verify_system_text_binding(baseline, binding, repo_root=repo, data_root=data)


@pytest.mark.parametrize("missing", [False, True])
def test_real_prelaunch_gate_requires_the_registered_bundle(bound, tmp_path, missing):
    compiled, binding, repo, data, _, _ = bound
    w = World(tmp_path / "gate").build()
    add_runtime_fragments(w)
    # Materialize role and policy bytes in the synthetic prelaunch repository.
    import shutil
    shutil.copytree(repo / "configs", w.repo / "configs", dirs_exist_ok=True)
    shutil.copytree(repo / "docs", w.repo / "docs", dirs_exist_ok=True)
    shutil.copytree(data / "search", w.data / "search")
    exp = w.repo / "configs/experiment" / (EXPERIMENT + ".json")
    fragment = json.loads(exp.read_text())
    if not missing:
        fragment["cells"][0]["system_text_policy_binding"] = binding
    _write(exp, fragment)
    base_name = fragment["cells"][0]["baseline_fragment"]
    _write(w.repo / "configs/baseline" / (base_name + ".json"), compiled)
    w.recipe.update(family_id="fixed400-context20-v1")
    registration = {"member_bindings": {"B-parent": {"run_id": RUN, "bundle_id": binding["bundle_id"]}}}
    reg_path = w.repo / "docs/readiness" / PACKAGE / "binding.json"
    _write(reg_path, registration)
    w.recipe["pilot_registration"] = {
        "relpath": reg_path.relative_to(w.repo).as_posix(),
        "sha256": hashlib.sha256(reg_path.read_bytes()).hexdigest()}
    _write(w.repo / "docs/readiness" / PACKAGE / "analysis-recipe-v1.json", w.recipe)
    result = w.run(cells=[EXPERIMENT])
    if missing:
        assert "system-text-policy-binding" in _kinds(result)
        assert not result["passed"]
    else:
        assert "system-text-policy-binding" not in _kinds(result), result
        compiled["phase_material"]["planner"]["instruction_template"] = "probes/legacy.txt"
        _write(w.repo / "configs/baseline" / (base_name + ".json"), compiled)
        result = w.run(cells=[EXPERIMENT])
        assert "system-text-policy-binding" in _kinds(result)
        assert not result["passed"]


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "missing-binding",
        "missing-registration",
        "changed-pin",
        "wrong-family",
        "wrong-policy",
        "wrong-attempt",
        "duplicate-member",
        "old-planner",
        "ambiguous",
        "changed-registration",
        "measurement-missing-runtime",
        "measurement-wrong-recipe",
        "measurement-wrong-registration",
        "measurement-wrong-slots",
        "measurement-valid",
    ],
)
def test_new_panel_prelaunch_requires_exact_member_and_effective_role_bytes(
    bound, tmp_path, fault
):
    import shutil
    from speech_aware_evidence_acquisition.rails.hashing import content_hash

    compiled, binding, repo, data, _, _ = bound
    w = World(tmp_path / "panel-gate").build()
    add_runtime_fragments(w)
    shutil.copytree(repo / "configs", w.repo / "configs", dirs_exist_ok=True)
    shutil.copytree(repo / "docs", w.repo / "docs", dirs_exist_ok=True)
    shutil.copytree(data / "search", w.data / "search")
    path = w.repo / "configs/experiment" / (EXPERIMENT + ".json")
    fragment = json.loads(path.read_text())
    cell = fragment["cells"][0]
    cell["attempt_id"] = "attempt-panel-generation"
    if fault != "missing-binding":
        cell["system_text_policy_binding"] = binding
    base_path = w.repo / "configs/baseline" / (cell["baseline_fragment"] + ".json")
    _write(base_path, compiled)
    w.recipe["family_id"] = "fixed400-text-round4-n50-v1"
    registration = {
        "schema": "saea-fixed400-system-panel-registration-v1",
        "family_id": w.recipe["family_id"],
        "member_bindings": {
            "B-parent": {
                "run_id": RUN,
                "attempt_id": cell["attempt_id"],
                "bundle_id": binding["bundle_id"],
            }
        },
    }
    if fault == "wrong-family":
        registration["family_id"] = "another"
    elif fault == "wrong-policy":
        registration["member_bindings"]["B-parent"]["bundle_id"] = "0" * 64
    elif fault == "wrong-attempt":
        registration["member_bindings"]["B-parent"]["attempt_id"] = "another-attempt"
    elif fault == "duplicate-member":
        registration["member_bindings"]["B-parent-aa"] = registration[
            "member_bindings"
        ]["B-parent"]
    if fault and fault.startswith("measurement-"):
        from test_system_search_measurement import profile
        p = profile()
        registration["measurement_profile"] = p
        w.recipe["measurement_profile"] = copy.deepcopy(p)
        fragment["system_search_measurement"] = copy.deepcopy(p)
        compiled.update(serving_slots=4, serving_slot_tokens=24576,
                        server_args=["-np", "4", "-c", "98304"], decoding_params={"max_tokens": 512})
        if fault == "measurement-missing-runtime":
            del fragment["system_search_measurement"]
        elif fault == "measurement-wrong-recipe":
            w.recipe["measurement_profile"]["queue_depth"] = 16
        elif fault == "measurement-wrong-registration":
            registration["measurement_profile"] = {**p, "queue_depth": 16}
        elif fault == "measurement-wrong-slots":
            compiled["serving_slots"] = 8
        _write(base_path, compiled)
    registration["registration_sha256"] = content_hash(registration)
    if fault == "changed-registration":
        registration["registration_sha256"] = "0" * 64
    rp = w.repo / "docs/readiness" / PACKAGE / "panel.json"
    _write(rp, registration)
    if fault != "missing-registration":
        w.recipe["system_panel_registration"] = {
            "relpath": rp.relative_to(w.repo).as_posix(),
            "sha256": hashlib.sha256(rp.read_bytes()).hexdigest(),
        }
    if fault == "changed-pin":
        rp.write_text("{}")
    elif fault == "ambiguous":
        w.recipe["pilot_registration"] = w.recipe["system_panel_registration"]
    elif fault == "old-planner":
        compiled["phase_material"]["planner"]["instruction_template"] = (
            "probes/legacy.txt"
        )
        _write(base_path, compiled)
    _write(path, fragment)
    _write(w.repo / "docs/readiness" / PACKAGE / "analysis-recipe-v1.json", w.recipe)
    result = w.run(cells=[EXPERIMENT])
    if fault and fault != "measurement-valid":
        assert "system-text-policy-binding" in _kinds(result)
    else:
        assert "system-text-policy-binding" not in _kinds(result), result


@pytest.mark.parametrize("fault", [None, "runtime-missing", "recipe-conflict", "slots-conflict"])
def test_standalone_engineering_prelaunch_binds_its_measured_profile(bound, tmp_path, fault):
    import shutil
    from test_system_search_measurement import profile
    compiled, binding, repo, data, _, _ = bound
    w = World(tmp_path / "engineering-measured").build()
    add_runtime_fragments(w)
    shutil.copytree(repo / "configs", w.repo / "configs", dirs_exist_ok=True)
    shutil.copytree(repo / "docs", w.repo / "docs", dirs_exist_ok=True)
    shutil.copytree(data / "search", w.data / "search")
    path = w.repo / "configs/experiment" / (EXPERIMENT + ".json")
    fragment = json.loads(path.read_text())
    cell = fragment["cells"][0]
    cell["system_text_policy_binding"] = binding
    fragment["system_search_measurement"] = profile()
    compiled.update(serving_slots=4, serving_slot_tokens=24576,
        server_args=["-np", "4", "-c", "98304"], decoding_params={"max_tokens": 512})
    w.recipe["measurement_profile"] = profile()
    if fault == "runtime-missing":
        fragment.pop("system_search_measurement")
    elif fault == "recipe-conflict":
        w.recipe["measurement_profile"]["queue_depth"] = 16
    elif fault == "slots-conflict":
        compiled["serving_slots"] = 8
    _write(w.repo / "configs/baseline" / (cell["baseline_fragment"] + ".json"), compiled)
    _write(path, fragment)
    _write(w.repo / "docs/readiness" / PACKAGE / "analysis-recipe-v1.json", w.recipe)
    result = w.run(cells=[EXPERIMENT])
    assert ("system-text-policy-binding" in _kinds(result)) is (fault is not None), result
