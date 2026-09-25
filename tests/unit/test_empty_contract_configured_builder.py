"""Source-bound sibling builds use the released empty-contract builder rails."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.e0.artifacts import write_json_artifact
from speech_aware_evidence_acquisition.rails.knowledge_build import (
    KB_BUILD_POLICY_ID,
    KbRow,
    KnowledgeBuildSpec,
    VIEW_ANNOTATED_EXEMPLARS,
    VIEW_ANNOTATED_EXEMPLARS_EMPTY_CONTRACT,
    build_knowledge_snapshot,
)

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "configured_empty_contract_builder",
    REPO / "scripts/build_slurp_train_exemplars_with_empty_store.py",
)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _row(number: int, *, entity: bool = False) -> KbRow:
    uid = str(number)
    sample = f"slurp:train:{uid}:audio-{uid}"
    return KbRow(
        utterance_id=uid, content=f"sample words {uid}",
        scenario="alarm", action="set", intent="alarm_set",
        entity_types=("time",) if entity else (),
        entity_fillers={"time": ("nine",)} if entity else {},
        sample_ids=(sample,), speaker_by_sample_id={sample: "FO-001"},
        media_relpath_by_sample_id={sample: f"datasets/slurp/{uid}.flac"},
    )


def _snapshot(rows, view):
    return build_knowledge_snapshot(
        KnowledgeBuildSpec(
            carrier_lock_key="slurp", dimensions=("content",), view=view
        ).validate(),
        rows=rows, forbidden_sample_ids=frozenset(),
    )


def _fixture(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    data = tmp_path / "data"
    repo.mkdir()
    data.mkdir()
    monkeypatch.setattr(builder, "REPO_ROOT", repo)
    monkeypatch.setattr(builder, "data_root", lambda: data)
    monkeypatch.setattr(builder, "load_lock", lambda _: object())
    monkeypatch.setattr(builder, "umbrella_lock_path", lambda _: repo / "lock")
    monkeypatch.setattr(builder, "slurp_kb_rows", lambda _lock, _root: all_rows)
    monkeypatch.setattr(
        builder, "build_knowledge_snapshot",
        lambda _spec, **kw: _snapshot(kw["rows"], VIEW_ANNOTATED_EXEMPLARS_EMPTY_CONTRACT),
    )
    monkeypatch.setattr(builder, "coverage_report", lambda *_: {"covered": True})
    all_rows = (_row(1), _row(2, entity=True), _row(3))
    kept = all_rows[1:]
    parent = _snapshot(kept, VIEW_ANNOTATED_EXEMPLARS)
    parent_rel = f"knowledge/slurp/{KB_BUILD_POLICY_ID}/size-parent/snapshot.json"
    parent_path = data / parent_rel
    parent_file_sha = write_json_artifact(parent_path, parent.frozen_json())
    parent_receipt_rel = "docs/receipts/knowledge/parent.json"
    parent_receipt_sha = write_json_artifact(
        repo / parent_receipt_rel,
        {
            "schema": "saea-kb-build-receipt-v1",
            "snapshot_sha256": parent.content_hash(),
            "source_split_identity_hash": parent.source_split_identity_hash,
            "value_count": len(kept),
            "builder_policy_id": KB_BUILD_POLICY_ID,
            "snapshot_artifact_relpath": parent_rel,
        },
    )
    roster_rel = "docs/receipts/rosters/exclude.json"
    roster_sha = write_json_artifact(
        repo / roster_rel, {"items": [{"sample_id": all_rows[0].sample_ids[0]}]},
    )
    source = data / builder.TRAIN_METADATA_RELPATH
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("synthetic\n", encoding="utf-8")
    vector_rel = "vectors/synthetic.jsonl"
    vectors = data / vector_rel
    vectors.parent.mkdir(parents=True, exist_ok=True)
    vectors.write_text(
        "".join(json.dumps({"id": facet.facet_id}) + "\n" for facet in parent.facets),
        encoding="utf-8",
    )
    monkeypatch.setattr(builder, "FACET_VECTORS_RELPATH", vector_rel)
    monkeypatch.setattr(builder, "FACET_VECTORS_SHA256", builder._sha256_path(vectors))
    config = {
        "schema": builder.CONFIG_SCHEMA,
        "parent": {
            "snapshot_relpath": parent_rel,
            "snapshot_file_sha256": parent_file_sha,
            "snapshot_sha256": parent.content_hash(),
            "receipt_relpath": parent_receipt_rel,
            "receipt_sha256": parent_receipt_sha,
            "source_split_identity_hash": parent.source_split_identity_hash,
            "utterance_count": len(kept),
        },
        "exclude_rosters": [{"relpath": roster_rel, "sha256": roster_sha}],
        "output": {
            "tier": "pool-annotated-exemplars-empty-contract-minus-r01-v1",
            "release_name": "train-exemplars-with-empty-minus-r01-v1",
            "receipt_relpath": "docs/receipts/knowledge/sibling.json",
        },
        "authority": "Synthetic unit registration",
        "exposure_ledger_row": "SYNTHETIC-MODEL-FREE-BUILD",
    }
    config_path = repo / "configs" / "knowledge" / "sibling.json"
    write_json_artifact(config_path, config)
    return repo, data, config_path, parent, vectors


def test_configured_build_excludes_rows_and_changes_only_empty_values(tmp_path, monkeypatch):
    repo, data, config_path, parent, _ = _fixture(tmp_path, monkeypatch)
    config = builder.load_config(config_path)
    result = builder.build_store(check=False, out_root=data, config=config)
    assert result["utterance_count"] == 2
    assert result["parent_relation"]["parent_snapshot_sha256"] == parent.content_hash()
    assert result["parent_relation"]["values_changed"] == 1
    assert result["parent_relation"]["facets_changed"] == 0
    parent_values = {value.value_id: value.content for value in parent.values}
    derived_values = {value.value_id: value.content for value in result["snapshot"].values}
    assert derived_values["value:2"] == parent_values["value:2"]
    assert derived_values["value:3"] == parent_values["value:3"].replace(
        " | none", ' | "entities":[]'
    )
    receipt = json.loads((repo / config["output"]["receipt_relpath"]).read_text())
    assert receipt["build_config"]["file_sha256"] == builder._sha256_path(config_path)
    assert receipt["parent_store"]["snapshot_relpath"] == config["parent"]["snapshot_relpath"]
    assert receipt["parent_store"]["relation"]["values_byte_identical"] == 1
    assert result["release"]["store_id"] == builder.STORE_ID
    assert result["release"]["store_role"] == builder.STORE_ROLE


@pytest.mark.parametrize("bad_field", ["snapshot_file_sha256", "receipt_sha256", "snapshot_sha256"])
def test_configured_build_refuses_wrong_parent_binding(tmp_path, monkeypatch, bad_field):
    repo, data, config_path, _, _ = _fixture(tmp_path, monkeypatch)
    document = json.loads(config_path.read_text())
    document["parent"][bad_field] = "0" * 64
    write_json_artifact(config_path, document)
    config = builder.load_config(config_path)
    with pytest.raises(SystemExit, match="parent"):
        builder.build_store(check=False, out_root=data, config=config)
    assert not (repo / document["output"]["receipt_relpath"]).exists()
    assert not (data / "knowledge" / "slurp" / KB_BUILD_POLICY_ID /
                "size-pool-annotated-exemplars-empty-contract-minus-r01-v1").exists()


def test_vector_gap_prevents_publication(tmp_path, monkeypatch):
    repo, data, config_path, _, vectors = _fixture(tmp_path, monkeypatch)
    vectors.write_text("", encoding="utf-8")
    monkeypatch.setattr(builder, "FACET_VECTORS_SHA256", builder._sha256_path(vectors))
    config = builder.load_config(config_path)
    with pytest.raises(SystemExit, match="facet id"):
        builder.build_store(check=False, out_root=data, config=config)
    assert not (repo / config["output"]["receipt_relpath"]).exists()


def test_configured_build_refuses_different_published_artifact(tmp_path, monkeypatch):
    repo, data, config_path, _, _ = _fixture(tmp_path, monkeypatch)
    config = builder.load_config(config_path)
    output = data / "knowledge" / "slurp" / KB_BUILD_POLICY_ID / (
        "size-" + config["output"]["tier"]
    ) / "snapshot.json"
    output.parent.mkdir(parents=True)
    output.write_text("published other bytes", encoding="utf-8")
    with pytest.raises(SystemExit, match="refusing to overwrite"):
        builder.build_store(check=False, out_root=data, config=config)
    assert output.read_text() == "published other bytes"
    assert not (repo / config["output"]["receipt_relpath"]).exists()


def test_config_path_and_roster_paths_are_confined(tmp_path, monkeypatch):
    repo, _, config_path, _, _ = _fixture(tmp_path, monkeypatch)
    document = json.loads(config_path.read_text())
    document["exclude_rosters"][0]["relpath"] = "../outside.json"
    write_json_artifact(config_path, document)
    with pytest.raises(SystemExit, match="invalid confined"):
        builder.load_config(config_path)


def test_no_config_defaults_remain_the_historical_release():
    assert builder.TIER == "pool-annotated-exemplars-empty-contract-v1"
    assert builder.RELEASE_NAME == "train-exemplars-with-empty-v1"
    assert builder.EXPECTED_UTTERANCE_COUNT == 9354
    assert len(builder.EXCLUDE_ROSTER_RELPATHS) == 3
    assert builder.RECEIPT_PATH.name == (
        "slurp-kb-size-pool-annotated-exemplars-empty-contract-v1.json"
    )
