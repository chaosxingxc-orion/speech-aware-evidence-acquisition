"""A new proposal sequence preserves spent and held predecessor allocations."""
import copy
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_search_archive import SystemSearchArchive, proposal_input
from speech_aware_evidence_acquisition.rails.system_search_allocations import require_round, build_extension
from speech_aware_evidence_acquisition.rails.system_search_successor import (
    OWNER227, build_successor, register_successor, validate_successor,
)
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError
from test_system_search_allocations import fixture, write_pin


def setup(tmp_path):
    old, repo, seed, ext = fixture(tmp_path)
    held = ["B-3-1", "L-3-2", "B-3-2"]
    for key in held:
        for folder in ("responses", "imports"):
            (old.root / folder / (key + ".json")).unlink()
    old.store_policy(seed)
    old._write("dispatch/budget.json", {"input_token_cap": 32768})
    owner = write_pin(repo, OWNER227, {"decision_id": 227, "status": "approved"})
    decision = {"status": "root-selected-for-preparation", "sequence_id": "successor-v1",
        "round": 4, "input_token_cap": 131072, "output_token_cap": 4096, "contact_cap": 4,
        "held_allocations": held, "new_allocations": ["L-4-1", "B-4-1", "L-4-2", "B-4-2"],
        "dispatch_authority": False}
    transition = write_pin(repo, "transition.json", decision)
    new = SystemSearchArchive(tmp_path / "successor")
    args = dict(round_index=4, owner=owner, transition=transition,
        previous_protocol=ext["previous_protocol"], repo_root=repo, sequence_id="successor-v1")
    doc = build_successor(old, new, **args)
    return old, new, repo, seed, doc, args


def test_successor_copies_only_closed_custody_without_resetting_old_budget(tmp_path):
    old, new, repo, seed, doc, _ = setup(tmp_path)
    before = {p.relative_to(old.root): p.read_bytes() for p in old.root.rglob("*.json")}
    assert len(doc["earlier_allocations"]) == 9 and len(doc["held_allocations"]) == 3
    assert not new.root.exists()
    register_successor(old, new, doc, repo_root=repo)
    assert new.allocation_extension(4) == doc
    assert new.load_policy(seed.bundle_id).bundle_id == seed.bundle_id
    assert not (new.root / "dispatch").exists()
    assert all((old.root / p).read_bytes() == raw for p, raw in before.items())
    for key in doc["held_allocations"]:
        assert not (new.root / "inputs" / (key + ".json")).exists()
        assert not (old.root / "responses" / (key + ".json")).exists()
    assert len(list((new.root / "imports").glob("*.json"))) == 9
    with pytest.raises(PolicyError):
        register_successor(old, new, doc, repo_root=repo)
    with pytest.raises(PolicyError, match="not closed"):
        build_extension(old, round_index=4, owner=args_owner(repo),
            previous_protocol=doc["previous_protocol"], repo_root=repo)


def args_owner(repo):
    from speech_aware_evidence_acquisition.rails.system_search_allocations import OWNER223
    import hashlib
    return {"relpath": OWNER223, "sha256": hashlib.sha256((repo / OWNER223).read_bytes()).hexdigest()}


@pytest.mark.parametrize("fault", ["budget", "held-spent", "changed-input", "hidden-reservation",
    "source-equals-destination", "missing-history", "owner", "decision", "new-allocation", "copied-held"])
def test_successor_refuses_relabeling_and_mutation(tmp_path, fault):
    old, new, repo, _, doc, _ = setup(tmp_path)
    if fault == "budget": doc["input_token_cap"] = 262144
    elif fault == "held-spent": doc["earlier_allocations"]["B-3-1"] = doc["earlier_allocations"]["B-2-1"]
    elif fault == "changed-input": (old.root / "inputs/L-1-1.json").write_text("{}")
    elif fault == "hidden-reservation": old._write("dispatch/B-3-1/reservation.json", {})
    elif fault == "source-equals-destination": doc["successor_archive"] = str(old.root)
    elif fault == "missing-history": doc["earlier_allocations"].pop("L-1-1")
    elif fault == "owner": (repo / OWNER227).write_text("{}")
    elif fault == "decision": (repo / "transition.json").write_text("{}")
    elif fault == "new-allocation": doc["allocations"].append("L-4-3")
    else:
        new._write("inputs/B-3-1.json", {})
    with pytest.raises((PolicyError, KeyError)):
        register_successor(old, new, doc, repo_root=repo)
    assert not (new.root / "allocations/round-4.json").exists()


def test_blind_successor_only_receives_seed_and_new_cap(tmp_path):
    old, new, repo, seed, doc, _ = setup(tmp_path)
    register_successor(old, new, doc, repo_root=repo)
    packet = proposal_input(branch="B", round_index=4, slot=1, seed=seed, parent=seed,
        model_version="GPT6-pinned", session_id="fresh-successor", input_token_cap=131072,
        output_token_cap=4096, allocation_extension=doc)
    assert not ({"feedback", "learning_history", "earlier_allocations", "held_allocations"} & packet.keys())
    new.store_input(packet)
    assert json.loads((old.root / "dispatch/budget.json").read_text())["input_token_cap"] == 32768
    with pytest.raises(PolicyError):
        proposal_input(branch="B", round_index=4, slot=2, seed=seed, parent=seed,
            model_version="GPT6-pinned", session_id="foreign", input_token_cap=32768,
            output_token_cap=4096, allocation_extension=doc)
    with pytest.raises(PolicyError): require_round(5, doc)
    with pytest.raises(PolicyError): require_round(3, doc)


def test_registered_successor_rechecks_source_and_snapshot(tmp_path):
    old, new, repo, _, doc, _ = setup(tmp_path)
    register_successor(old, new, doc, repo_root=repo)
    (new.root / "imports/L-1-1.json").write_text("{}")
    with pytest.raises(PolicyError, match="snapshot"):
        new.allocation_extension(4)


def test_successor_preserves_exact_fixed_pool_scope(tmp_path):
    from test_system_optimization import fixture as panel_fixture
    from speech_aware_evidence_acquisition.rails.system_optimization import load_optimization_panel
    old, new, repo, _, doc, _ = setup(tmp_path)
    protocol, ids = panel_fixture(repo)
    protocol["allocation_extension"] = doc
    protocol["optimization_panel"]["stages"] = ["update-4"]
    assert load_optimization_panel(protocol, "update-4", repo_root=repo)[1] == ids
