"""Exact prospective TRAIN slices, source custody and create-only publication."""

import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    SystemTextPolicyBundle,
)
from test_system_text_policy import seed_document

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = "docs/readiness/2026-10-01-slurp-system-text-search-v1"


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "runtime_views", ROOT / "scripts/prepare_system_text_runtime_views.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    repo, data = tmp_path / "repo", tmp_path / "data"
    protocol = json.loads((ROOT / PACKAGE / "protocol-control-v2.json").read_text())
    paths = [p["relpath"] for p in protocol["source_rosters"].values()]
    paths += [
        f"configs/dataset/slurp-speech-native-evo-fold-{k}-1080.json" for k in "ab"
    ]
    for rel in paths:
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, repo / rel)
    bundle = SystemTextPolicyBundle.from_json(seed_document())
    data.mkdir()
    raw = json.dumps(bundle.as_json()).encode()
    (data / "seed.json").write_bytes(raw)
    protocol["seed_bundle"] = {
        "relpath": "seed.json",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bundle_id": bundle.bundle_id,
    }
    path = repo / PACKAGE / "protocol-control-v2.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(protocol))
    calls = []

    def verify(path, **kwargs):
        d = json.loads(path.read_text())
        assert kwargs["data_root"] == data
        assert kwargs["expected_count"] == d["count"]
        assert kwargs["expected_split_name"] == d["split_name"]
        assert kwargs["workers"] == 4
        calls.append(d)

    monkeypatch.setattr(module, "load_slurp_engineering_gate", verify)
    return module, repo, data, path, protocol, calls


def invoke(fixture):
    module, repo, data, path, _, _ = fixture
    return module.prepare(repo=repo, data_root=data, protocol_path=path, workers=4)


def test_publish_exact_four_slices_after_native_verification(prepared):
    module, repo, _, _, protocol, calls = prepared
    result = invoke(prepared)
    assert [c["count"] for c in calls] == [1080, 1080, 400, 400, 400, 400]
    assert result["no_runtime_authority"] is True
    assert not any(result["contacts"].values())
    assert len(result["stages"]) == 4
    for entry, stage in zip(result["stages"], protocol["stages"][1:5]):
        d = json.loads((repo / entry["runtime_view"]["relpath"]).read_text())
        receipt = json.loads((repo / entry["subset_receipt"]["relpath"]).read_text())
        assert [r["sample_id"] for r in d["items"]] == stage["sample_ids"]
        assert d["source_binding_sha256"] == content_hash(receipt)
        assert d["split_role"] == "discovery"
        assert entry["seed_source_overlap_utterances"] == 0
        assert entry["roster_sha256"] == stage["roster_sha256"]
    original = {p: p.read_bytes() for p in repo.rglob("*system-text*400-v1.json")}
    assert invoke(prepared) == result
    assert all(p.read_bytes() == b for p, b in original.items())


@pytest.mark.parametrize("mutation", ["order", "hash", "seed", "source", "duplicate"])
def test_refuse_changed_registered_selection_before_writes(prepared, mutation):
    _, repo, _, path, protocol, calls = prepared
    if mutation == "order":
        protocol["stages"][2]["sample_ids"].reverse()
    elif mutation == "hash":
        protocol["stages"][2]["roster_sha256"] = "0" * 64
    elif mutation == "seed":
        protocol["seed"] = 5
    elif mutation == "source":
        pin = protocol["source_rosters"]["fold_b"]
        (repo / pin["relpath"]).write_text("{}")
    else:
        protocol["stages"].append(protocol["stages"][1])
    path.write_text(json.dumps(protocol))
    with pytest.raises(ValueError):
        invoke(prepared)
    assert not calls
    assert not list(repo.glob("configs/dataset/*system-text*"))


def test_refuse_parent_roster_substitution(prepared):
    _, repo, _, _, _, calls = prepared
    p = repo / "configs/dataset/slurp-speech-native-evo-fold-b-1080.json"
    d = json.loads(p.read_text())
    d["items"][0]["sample_id"] = "slurp:train:999999:recording"
    d["runtime_view_sha256"] = content_hash(
        {k: v for k, v in d.items() if k != "runtime_view_sha256"}
    )
    p.write_text(json.dumps(d))
    with pytest.raises(ValueError, match="parent roster"):
        invoke(prepared)
    assert not list(repo.glob("configs/dataset/*system-text*"))


def test_seed_indirect_exposure_overlap_is_refused(prepared):
    _, repo, data, path, protocol, _ = prepared
    d = json.loads((data / "seed.json").read_text())
    d["cumulative_sources"][0]["sample_ids"] = [protocol["stages"][4]["sample_ids"][0]]
    bundle = SystemTextPolicyBundle.from_json(d)
    raw = json.dumps(bundle.as_json()).encode()
    (data / "seed.json").write_bytes(raw)
    protocol["seed_bundle"].update(
        sha256=hashlib.sha256(raw).hexdigest(), bundle_id=bundle.bundle_id
    )
    path.write_text(json.dumps(protocol))
    with pytest.raises(ValueError, match="overlap"):
        invoke(prepared)
    assert not list(repo.glob("configs/dataset/*system-text*"))


def test_native_media_failure_publishes_nothing(prepared, monkeypatch):
    module, repo, _, _, _, calls = prepared
    verify = module.load_slurp_engineering_gate

    def fail_last(path, **kwargs):
        verify(path, **kwargs)
        if len(calls) == 6:
            raise ValueError("media hash differs")

    monkeypatch.setattr(module, "load_slurp_engineering_gate", fail_last)
    with pytest.raises(ValueError, match="media hash"):
        invoke(prepared)
    assert not list(repo.glob("configs/dataset/*system-text*"))


def test_different_existing_output_refused_before_any_publication(prepared):
    _, repo, _, _, _, _ = prepared
    path = (
        repo / "configs/dataset/slurp-speech-native-system-text-selection-400-v1.json"
    )
    path.write_text("immutable different bytes")
    with pytest.raises(ValueError, match="replace"):
        invoke(prepared)
    assert path.read_text() == "immutable different bytes"
    assert len(list(repo.glob("configs/dataset/*system-text*"))) == 1


def test_corrected_seed_requires_pinned_complete_parent_chain(prepared):
    module, repo, data, path, protocol, _ = prepared
    old_protocol = repo / PACKAGE / "parent-protocol.json"
    old_protocol.write_text(json.dumps(protocol))
    parent = SystemTextPolicyBundle.from_json(
        json.loads((data / "seed.json").read_text())
    )
    child = parent.as_json()
    child["parent_ids"] = [parent.bundle_id]
    child["role_text"]["planner"] += " Return only the legal action text."
    bundle = SystemTextPolicyBundle.from_json(child, parents=[parent])
    raw = json.dumps(bundle.as_json()).encode()
    (data / "child.json").write_bytes(raw)
    protocol["seed_bundle"] = {
        "relpath": "child.json",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bundle_id": bundle.bundle_id,
    }
    path.write_text(json.dumps(protocol))
    with pytest.raises(ValueError, match="parent"):
        invoke(prepared)
    result = module.prepare(
        repo=repo,
        data_root=data,
        protocol_path=path,
        workers=4,
        parent_protocol_paths=[old_protocol],
    )
    assert result["seed_ancestry"][0]["bundle_id"] == parent.bundle_id
    assert result["seed_bundle"]["bundle_id"] == bundle.bundle_id


@pytest.mark.parametrize("workers", [True, 0, 9])
def test_worker_ceiling_is_enforced(prepared, workers):
    module, repo, data, path, _, _ = prepared
    with pytest.raises(ValueError, match="workers"):
        module.prepare(repo=repo, data_root=data, protocol_path=path, workers=workers)


def test_wrong_seed_identity_is_refused(prepared):
    _, _, _, path, protocol, _ = prepared
    protocol["seed_bundle"]["bundle_id"] = "0" * 64
    path.write_text(json.dumps(protocol))
    with pytest.raises(ValueError, match="identity"):
        invoke(prepared)


def test_cli_runs_same_preparation(prepared, monkeypatch, capsys):
    module, repo, data, path, _, _ = prepared
    monkeypatch.setattr(
        "sys.argv",
        [
            "prepare",
            "--repo-root",
            str(repo),
            "--data-root",
            str(data),
            "--protocol",
            str(path),
            "--workers",
            "4",
        ],
    )
    module.main()
    output = json.loads(capsys.readouterr().out)
    assert output["rows"] == 1600
    assert output["no_runtime_authority"]
    assert not any(output["contacts"].values())
