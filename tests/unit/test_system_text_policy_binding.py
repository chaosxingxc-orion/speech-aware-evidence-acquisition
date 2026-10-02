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
        assert "system-text-policy-binding" not in _kinds(result)
        compiled["phase_material"]["planner"]["instruction_template"] = "probes/legacy.txt"
        _write(w.repo / "configs/baseline" / (base_name + ".json"), compiled)
        result = w.run(cells=[EXPERIMENT])
        assert "system-text-policy-binding" in _kinds(result)
        assert not result["passed"]
