"""Explicit seed migration keeps old allocations and verifies the real source bytes."""

import hashlib
import json
import shutil
import pytest
from test_system_search_successor import setup
from test_system_search_allocations import write_pin
from test_system_text_policy import ROOT, BASE
from speech_aware_evidence_acquisition.rails.system_search_archive import (
    SystemSearchArchive,
)
from speech_aware_evidence_acquisition.rails.system_search_successor import (
    build_successor,
    register_successor,
    validate_successor,
)
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    PolicyError,
    bind_four_node_seed,
)

AUTHORITY = "docs/receipts/owner/2026-10-04-node-optimization-space.json"


def prepared(tmp_path):
    old, new, repo, seed, prior, args = setup(tmp_path)
    base = json.loads((ROOT / BASE).read_bytes())
    baseline = write_pin(repo, BASE, base)
    role_rel = "configs/" + base["phase_material"]["perception"]["instruction_template"]
    role = repo / role_rel
    role.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / role_rel, role)
    authority = write_pin(
        repo,
        AUTHORITY,
        {
            "schema": "saea-owner-node-optimization-space-v1",
            "gpu_dispatch_authorized_by_this_record": False,
            "new_human_permission_required_within_owner227": False,
        },
    )
    child = bind_four_node_seed(seed, base, repo_root=repo)
    source = SystemSearchArchive(tmp_path / "seed-stage")
    source.store_policy(seed)
    source.store_policy(child)
    seed_path = source.root / "policies" / (child.bundle_id + ".json")
    receipt = write_pin(
        repo,
        "seed-transition.json",
        {
            "schema": "saea-four-node-seed-transition-v1",
            "status": "frozen-offline-seed",
            "runtime_admission": False,
            "parent_bundle_id": seed.bundle_id,
            "bundle_id": child.bundle_id,
            "authority": authority,
            "original_seed_config": baseline,
            "source_perception": {
                "relpath": role_rel,
                "sha256": hashlib.sha256(role.read_bytes()).hexdigest(),
            },
            "seed_bundle": {
                "relpath": "seed-stage/policies/" + child.bundle_id + ".json",
                "sha256": hashlib.sha256(seed_path.read_bytes()).hexdigest(),
            },
        },
    )
    descriptor = {
        "receipt": receipt,
        "source_archive": str(source.root),
        "parent_bundle_id": seed.bundle_id,
        "bundle_sha256": hashlib.sha256(seed_path.read_bytes()).hexdigest(),
    }
    decision = json.loads((repo / args["transition"]["relpath"]).read_bytes())
    decision.update(context_authority=authority, seed_transition=descriptor)
    args["transition"] = write_pin(repo, "seed-decision.json", decision)
    return old, new, repo, seed, child, args, descriptor


def test_explicit_seed_successor_preserves_predecessor_and_publishes_new_seed(tmp_path):
    old, new, repo, seed, child, args, desc = prepared(tmp_path)
    before = {
        str(p.relative_to(old.root)): p.read_bytes()
        for p in old.root.rglob("*")
        if p.is_file()
    }
    doc = build_successor(old, new, **args)
    assert doc["schema"] == "saea-system-search-successor-sequence-v4"
    assert doc["seed_bundle_id"] == child.bundle_id
    assert doc["seed_transition"] == desc
    assert not (old.root / "policies" / (child.bundle_id + ".json")).exists()
    register_successor(old, new, doc, repo_root=repo)
    assert new.load_policy(child.bundle_id).as_json() == child.as_json()
    assert new.load_policy(seed.bundle_id).as_json() == seed.as_json()
    assert new.allocation_extension(4) == doc
    assert validate_successor(new, doc) == doc
    assert before == {
        str(p.relative_to(old.root)): p.read_bytes()
        for p in old.root.rglob("*")
        if p.is_file()
    }
    for key in doc["held_allocations"]:
        assert not (new.root / "inputs" / (key + ".json")).exists()


@pytest.mark.parametrize(
    "fault",
    [
        "parent",
        "digest",
        "source-alias",
        "authority",
        "receipt",
        "source-text",
        "new-seed",
        "decision-mismatch",
        "unknown-field",
    ],
)
def test_seed_transition_refuses_forged_or_changed_custody_before_publication(
    tmp_path, fault
):
    old, new, repo, seed, child, args, desc = prepared(tmp_path)
    doc = build_successor(old, new, **args)
    if fault == "parent":
        doc["seed_transition"]["parent_bundle_id"] = "a" * 64
    elif fault == "digest":
        doc["seed_transition"]["bundle_sha256"] = "a" * 64
    elif fault == "source-alias":
        doc["seed_transition"]["source_archive"] = str(new.root)
    elif fault == "authority":
        doc["context_authority"]["sha256"] = "a" * 64
    elif fault == "receipt":
        (repo / desc["receipt"]["relpath"]).write_text("{}")
    elif fault == "source-text":
        r = json.loads((repo / desc["receipt"]["relpath"]).read_bytes())
        (repo / r["source_perception"]["relpath"]).write_text("Changed facts.")
    elif fault == "new-seed":
        doc["seed_bundle_id"] = seed.bundle_id
    elif fault == "decision-mismatch":
        d = json.loads((repo / args["transition"]["relpath"]).read_bytes())
        d.pop("seed_transition")
        doc["transition"] = write_pin(repo, "wrong-decision.json", d)
    else:
        doc["seed_transition"]["allow_rebase"] = True
    with pytest.raises((PolicyError, FileNotFoundError)):
        register_successor(old, new, doc, repo_root=repo)
    assert not new.root.exists()


def test_seed_successor_detects_published_policy_change(tmp_path):
    old, new, repo, seed, child, args, desc = prepared(tmp_path)
    doc = build_successor(old, new, **args)
    register_successor(old, new, doc, repo_root=repo)
    path = new.root / "policies" / (child.bundle_id + ".json")
    path.write_text("{}")
    with pytest.raises((PolicyError, KeyError)):
        validate_successor(new, doc, repo_root=repo)
