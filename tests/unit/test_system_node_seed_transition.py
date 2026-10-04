"""An explicit seed schema transition preserves behavior and cumulative custody."""

import copy
import json
import pytest
from speech_aware_evidence_acquisition.rails import system_text_policy as policy
from test_system_text_policy import seed_document, ROOT, BASE
from speech_aware_evidence_acquisition.rails.hashing import content_hash


def inputs():
    return policy.SystemTextPolicyBundle.from_json(seed_document()), json.loads(
        (ROOT / BASE).read_bytes()
    )


def test_transition_binds_four_role_bytes_and_retains_all_ancestry():
    parent, base = inputs()
    before = copy.deepcopy(base)
    child = policy.bind_four_node_seed(parent, base, repo_root=ROOT)
    old, new = parent.as_json(), child.as_json()
    assert base == before
    assert new["schema"] == policy.NODE_BUNDLE_SCHEMA
    assert new["parent_ids"] == [parent.bundle_id]
    assert new["role_text"]["perception"] == (
        ROOT / "configs" / base["phase_material"]["perception"]["instruction_template"]
    ).read_bytes().decode("utf-8")
    for role, text in old["role_text"].items():
        assert new["role_text"][role] == text
    for key in set(old) - {"schema", "parent_ids", "role_text"}:
        assert new[key] == old[key]
    assert new["node_context"] == {
        "tool_schema_rendering": "constant",
        "reviewer_history_scope": "full",
    }
    assert new["context_layout"] == {"native_role_query_placement": None}
    assert child.bundle_id != parent.bundle_id
    assert (
        policy.bind_four_node_seed(parent, base, repo_root=ROOT).bundle_id
        == child.bundle_id
    )


def test_transition_compiles_same_effective_policy(tmp_path):
    parent, base = inputs()
    child = policy.bind_four_node_seed(parent, base, repo_root=ROOT)
    old = policy.compile_system_text_policy(
        base, parent, repo_root=ROOT, output_root=tmp_path / "old"
    )
    new = policy.compile_system_text_policy(
        base, child, repo_root=ROOT, output_root=tmp_path / "new"
    )
    for role in ("perception", "solver", "reviewer", "planner"):
        old_path = (
            (ROOT if role == "perception" else tmp_path / "old")
            / "configs"
            / old["phase_material"][role]["instruction_template"]
        )
        new_path = (
            tmp_path
            / "new"
            / "configs"
            / new["phase_material"][role]["instruction_template"]
        )
        assert old_path.read_bytes() == new_path.read_bytes()
        new["phase_material"][role]["instruction_template"] = old["phase_material"][
            role
        ]["instruction_template"]
    # Compiler metadata and explicit default history are the only representation changes.
    new["native_episode"]["consumption_module"] = old["native_episode"][
        "consumption_module"
    ]
    new["native_episode"]["roles"]["reviewer"].pop("history_scope")
    assert new == old


@pytest.mark.parametrize(
    "kind",
    [
        "changed-base",
        "already-v3",
        "feedback-seed",
        "experience-seed",
        "escaped-template",
        "unsupported-context",
        "missing-template",
    ],
)
def test_transition_refuses_implicit_factor_or_evidence_changes(tmp_path, kind):
    parent, base = inputs()
    if kind == "changed-base":
        base["policy"] = "different"
    elif kind == "already-v3":
        parent = policy.bind_four_node_seed(parent, base, repo_root=ROOT)
    elif kind in ("feedback-seed", "experience-seed"):
        d = parent.as_json()
        if kind == "feedback-seed":
            d["cumulative_sources"].append(
                {
                    "kind": "feedback",
                    "sha256": "b" * 64,
                    "sample_ids": ["slurp:train:2:audio-3"],
                }
            )
        else:
            d["optimizer_experience"] = [
                {"relpath": "feedback.json", "sha256": "b" * 64}
            ]
        parent = policy.SystemTextPolicyBundle.from_json(d)
    else:
        if kind == "escaped-template":
            base["phase_material"]["perception"]["instruction_template"] = (
                "../../../outside.txt"
            )
        elif kind == "missing-template":
            base["phase_material"]["perception"].pop("instruction_template")
        else:
            base["native_episode"]["tool_schema_rendering"] = "invented"
        d = parent.as_json()
        d["seed_config_sha256"] = content_hash(base)
        parent = policy.SystemTextPolicyBundle.from_json(d)
    with pytest.raises(policy.PolicyError):
        policy.bind_four_node_seed(parent, base, repo_root=ROOT)


def test_v2_context_is_preserved_not_reset():
    parent, base = inputs()
    d = parent.as_json()
    d.update(
        schema=policy.CONTEXT_BUNDLE_SCHEMA,
        context_layout={"native_role_query_placement": "before-speech-v1"},
    )
    parent = policy.SystemTextPolicyBundle.from_json(d)
    child = policy.bind_four_node_seed(parent, base, repo_root=ROOT)
    assert child.as_json()["context_layout"] == d["context_layout"]


def test_implicit_runtime_defaults_and_parent_are_not_mutated():
    parent, base = inputs()
    base["native_episode"].pop("tool_schema_rendering")
    d = parent.as_json()
    d["seed_config_sha256"] = content_hash(base)
    parent = policy.SystemTextPolicyBundle.from_json(d)
    child = policy.bind_four_node_seed(parent, base, repo_root=ROOT)
    assert child.as_json()["node_context"]["tool_schema_rendering"] == "per-role"
    assert parent.as_json() == d
