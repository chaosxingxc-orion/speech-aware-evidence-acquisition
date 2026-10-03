"""Bind a prospective context layout into the complete immutable policy."""
import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.rails.system_search_archive import SystemSearchArchive
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    PolicyError, SystemTextPolicyBundle, TextPolicyUpdateProposal,
    apply_text_proposal, compile_system_text_policy, verify_system_text_binding,
)
from test_system_text_policy import seed_document, ROOT
from test_system_text_policy_binding import bound, add_runtime_fragments


V2 = "saea-system-text-policy-bundle-v2"
FIELD = "native_role_query_placement"


def successor(parent, placement):
    document = parent.as_json()
    document.update(schema=V2, parent_ids=[parent.bundle_id],
                    context_layout={FIELD: placement})
    document["role_text"]["reviewer"] += "\nKeep the handoff concise and source-bound."
    return SystemTextPolicyBundle.from_json(document, parents=[parent])


@pytest.mark.parametrize("placement", [None, "before-speech-v1"])
def test_joint_text_and_layout_have_one_identity_and_keep_ancestry(placement):
    parent = SystemTextPolicyBundle.from_json(seed_document())
    child = successor(parent, placement)
    assert child.bundle_id != parent.bundle_id
    assert child.as_json()["cumulative_sources"] == parent.as_json()["cumulative_sources"]
    assert child.as_json()["role_text"] != parent.as_json()["role_text"]
    other = successor(parent, None if placement else "before-speech-v1")
    assert child.bundle_id != other.bundle_id
    raw = child.as_json()
    raw["context_layout"][FIELD] = "foreign"
    assert child.as_json()["context_layout"][FIELD] == placement


@pytest.mark.parametrize("context", [{}, {FIELD: True}, {FIELD: "unknown"},
    {FIELD: []}, {FIELD: {}}, {FIELD: ""}, {FIELD: None, "scorers": []}])
def test_context_is_an_exact_declared_surface(context):
    d = seed_document()
    d.update(schema=V2, context_layout=context)
    with pytest.raises(PolicyError, match="context layout"):
        SystemTextPolicyBundle.from_json(d)


def test_schema_upgrade_is_explicit_and_cannot_be_silently_downgraded():
    d = seed_document()
    d["context_layout"] = {FIELD: None}
    with pytest.raises(PolicyError, match="fields"):
        SystemTextPolicyBundle.from_json(d)
    d.pop("context_layout")
    d["schema"] = V2
    with pytest.raises(PolicyError, match="fields"):
        SystemTextPolicyBundle.from_json(d)
    parent = SystemTextPolicyBundle.from_json(seed_document())
    child = successor(parent, "before-speech-v1")
    legacy = child.as_json()
    legacy.pop("context_layout")
    legacy.update(schema=parent.as_json()["schema"], parent_ids=[child.bundle_id])
    with pytest.raises(PolicyError, match="downgrade"):
        SystemTextPolicyBundle.from_json(legacy, parents=[child])


@pytest.mark.parametrize("placement", [None, "before-speech-v1"])
def test_compiler_binds_layout_and_verifier_refuses_runtime_drift(bound, placement):
    _, _, repo, data, baseline, parent = bound
    child = successor(parent, placement)
    compiled = compile_system_text_policy(baseline, child, repo_root=ROOT, output_root=repo)
    assert compiled.get(FIELD) == placement
    assert compile_system_text_policy(baseline, child, repo_root=ROOT,
                                      output_root=repo, enabled=False) == baseline
    archive = SystemSearchArchive(data / "search")
    archive.store_policy(child)
    rel = "search/policies/" + child.bundle_id + ".json"
    binding = {"schema": "saea-system-text-role-binding-v1", "bundle_id": child.bundle_id,
               "bundle": {"relpath": rel, "sha256": hashlib.sha256((data / rel).read_bytes()).hexdigest()}}
    checked = verify_system_text_binding(compiled, binding, repo_root=repo, data_root=data)
    assert checked["context_layout"] == {FIELD: placement}
    assert archive.load_policy(child.bundle_id).as_json() == child.as_json()
    compiled[FIELD] = None if placement else "before-speech-v1"
    with pytest.raises(PolicyError, match="context layout"):
        verify_system_text_binding(compiled, binding, repo_root=repo, data_root=data)


def test_v1_binding_rejects_undeclared_layout_without_changing_legacy_receipt(bound):
    compiled, binding, repo, data, _, _ = bound
    original = verify_system_text_binding(compiled, binding, repo_root=repo, data_root=data)
    assert set(original) == {"bundle_id", "role_sha256"}
    compiled[FIELD] = "before-speech-v1"
    with pytest.raises(PolicyError, match="context layout"):
        verify_system_text_binding(compiled, binding, repo_root=repo, data_root=data)


def test_existing_text_proposals_keep_layout_without_expanding_their_scope():
    seed = SystemTextPolicyBundle.from_json(seed_document())
    parent = successor(seed, "before-speech-v1")
    d = {"schema": "saea-text-policy-update-proposal-v1", "branch": "L", "round": 1,
         "slot": 1, "parent_ids": [parent.bundle_id],
         "changes": {"role_text": {"solver": "Use only source-supported evidence."}},
         "rationale": "Test a joint system while retaining its registered layout.",
         "hypotheses": [], "evidence": []}
    proposal = TextPolicyUpdateProposal.from_json(d)
    child = apply_text_proposal(proposal, parents=[parent], added_sources=[])
    assert child.as_json()["context_layout"] == parent.as_json()["context_layout"]
    d["changes"]["context_layout"] = {FIELD: None}
    with pytest.raises(PolicyError, match="editable"):
        TextPolicyUpdateProposal.from_json(d)


@pytest.mark.parametrize("location", ["model", "dataset", "experiment", "missing-model", "collision"])
@pytest.mark.parametrize("declared", [False, True])
def test_prelaunch_binds_effective_layout_across_all_runtime_fragments(
    bound, tmp_path, location, declared
):
    import shutil
    from test_flight_registration_check import World, EXPERIMENT, _write, _kinds

    compiled, binding, repo, data, baseline, parent = bound
    if declared:
        child = successor(parent, "before-speech-v1")
        compiled = compile_system_text_policy(baseline, child, repo_root=ROOT, output_root=repo)
        archive = SystemSearchArchive(data / "search")
        archive.store_policy(child)
        rel = "search/policies/" + child.bundle_id + ".json"
        binding.update(bundle_id=child.bundle_id, bundle={
            "relpath": rel, "sha256": hashlib.sha256((data / rel).read_bytes()).hexdigest()})
        compiled.pop(FIELD)
    w = World(tmp_path / "effective-gate").build()
    add_runtime_fragments(w)
    shutil.copytree(repo / "configs", w.repo / "configs", dirs_exist_ok=True)
    shutil.copytree(repo / "docs", w.repo / "docs", dirs_exist_ok=True)
    shutil.copytree(data / "search", w.data / "search")
    path = w.repo / "configs/experiment" / (EXPERIMENT + ".json")
    fragment = json.loads(path.read_text())
    cell = fragment["cells"][0]
    cell["system_text_policy_binding"] = binding
    _write(w.repo / "configs/baseline" / (cell["baseline_fragment"] + ".json"), compiled)
    if location == "missing-model":
        cell["model_fragment"] = "absent"
    elif location == "collision":
        fragment[FIELD] = "before-speech-v1"
        _write(w.repo / "configs/model/synthetic-model.json", {FIELD: "before-speech-v1"})
    elif location == "experiment":
        fragment[FIELD] = "before-speech-v1"
    else:
        _write(w.repo / "configs" / location / ("synthetic-" + location + ".json"),
               {FIELD: "before-speech-v1"})
    _write(path, fragment)
    result = w.run(cells=[EXPERIMENT])
    should_fail = not declared or location in {"missing-model", "collision"}
    assert ("system-text-policy-binding" in _kinds(result)) is should_fail
