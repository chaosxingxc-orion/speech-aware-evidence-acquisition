"""Publish existing governed compiler outputs through the shared preparation entry."""
from dataclasses import replace
from pathlib import Path
import hashlib
import json
import socket

import pytest

from speech_aware_evidence_acquisition.core.driver.cli import main
from speech_aware_evidence_acquisition.core.preparation import canonical_bytes
from speech_aware_evidence_acquisition.core.semantic_knowledge_preparation import (
    SemanticKnowledgePreparationError, prepare_semantic_knowledge_store,
)
from speech_aware_evidence_acquisition.rails import knowledge_compile_a2t as compiler
from speech_aware_evidence_acquisition.rails.errors import RailsError
from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot
from speech_aware_evidence_acquisition.rails.knowledge_stores import load_knowledge_store_binding
from test_a2t_semantic_card_compilation import _world


def _pin(path, root):
    return {
        "relpath": path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def _prepared(tmp_path, view="parameter-meaning"):
    config = _world(tmp_path)
    out = config.data_root / "compiled"
    config = replace(
        config, presentation_version=compiler.NATIVE_COMPATIBLE_PRESENTATION_V1,
        snapshot_value_view=view, corpus_output_path=out / "corpus.txt",
        receipt_output_path=out / "compilation.json",
        snapshot_output_path=out / "snapshot.json",
    )
    # The production CLI guard lasts for its process. Keep it active during
    # compilation, then restore this test process for later loopback fixtures.
    with pytest.MonkeyPatch.context() as isolation:
        for owner, name in (
            (socket.socket, "connect"), (socket.socket, "connect_ex"),
            (socket, "create_connection"),
        ):
            isolation.setattr(owner, name, getattr(owner, name))
        compiler.compile_a2t_semantic_card_artifacts(config)
    repo = tmp_path / "release-repo"
    repo.mkdir()
    registration = {
        "schema": "saea-compiled-knowledge-store-preparation-v1",
        "registration_id": "SYNTHETIC-COMPILED-STORE",
        "store_id": view,
        "store_role": view,
        "compilation_receipt": _pin(config.receipt_output_path, config.data_root),
        "snapshot": _pin(config.snapshot_output_path, config.data_root),
        "output_namespace": "released/" + view,
    }
    path = repo / "registration.json"
    path.write_bytes(canonical_bytes(registration))
    return repo, config, path, registration


@pytest.mark.parametrize("view", ["tool-activation", "parameter-meaning"])
def test_compiled_store_public_cli_roundtrip_and_exact_cache(tmp_path, capsys, view):
    repo, config, path, registration = _prepared(tmp_path, view)
    before = {p: p.read_bytes() for p in (config.snapshot_output_path, config.receipt_output_path)}
    assert main(["prepare-semantic-knowledge", "--registration", str(path),
                 "--repo-root", str(repo), "--data-root", str(config.data_root)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["cache"] == "cold"
    completion = result["completion"]
    binding = load_knowledge_store_binding({"knowledge_stores": {view: {
        "store_role": view, "snapshot": completion["snapshot"],
        "release": completion["release"],
    }}}, data_root=config.data_root)
    assert binding.composite_snapshot.source_partition_role == "external-governed"
    assert len(binding.snapshot_for(view).values) == 152
    release = config.data_root / completion["release"]["relpath"]
    mtime = release.stat().st_mtime_ns
    again = prepare_semantic_knowledge_store(path, repo_root=repo, data_root=config.data_root)
    assert again["cache"] == "warm" and release.stat().st_mtime_ns == mtime
    assert before == {p: p.read_bytes() for p in before}
    assert completion["contacts"] == {"model": 0, "tool": 0, "scorer": 0}


@pytest.mark.parametrize("defect", ["snapshot-pin", "receipt-pin", "role-view", "source-changed", "collision"])
def test_compiled_store_refuses_bad_binding_or_overwrite(tmp_path, defect):
    repo, config, path, registration = _prepared(tmp_path)
    if defect == "snapshot-pin":
        registration["snapshot"]["sha256"] = "0" * 64
    elif defect == "receipt-pin":
        registration["compilation_receipt"]["sha256"] = "0" * 64
    elif defect == "role-view":
        registration["store_role"] = "tool-activation"
    elif defect == "source-changed":
        config.construction_receipt_path.write_text("changed source")
    else:
        target = config.data_root / registration["output_namespace"] / "release.json"
        target.parent.mkdir(parents=True)
        target.write_text("preserve me")
    path.write_bytes(canonical_bytes(registration))
    with pytest.raises(SemanticKnowledgePreparationError):
        prepare_semantic_knowledge_store(path, repo_root=repo, data_root=config.data_root)
    if defect == "collision":
        assert target.read_text() == "preserve me"
    assert not (config.data_root / registration["output_namespace"] / "completion.json").exists()


@pytest.mark.parametrize("field", [
    ("compilation_id",), ("corpus", "sha256"),
    ("compiler", "minimum_compatibility_support"), ("compiler", "max_utf8_bytes"),
    ("registry", "tool_count"), ("knowledge_snapshot", "value_count"),
])
def test_compiled_store_refuses_rebinding_receipt_claims(tmp_path, field):
    repo, config, path, registration = _prepared(tmp_path)
    receipt = json.loads(config.receipt_output_path.read_text())
    target = receipt
    for key in field[:-1]:
        target = target[key]
    prior = target[field[-1]]
    target[field[-1]] = prior + 1 if isinstance(prior, int) else "different-compilation"
    config.receipt_output_path.write_bytes(canonical_bytes(receipt))
    registration["compilation_receipt"] = _pin(config.receipt_output_path, config.data_root)
    path.write_bytes(canonical_bytes(registration))
    with pytest.raises(SemanticKnowledgePreparationError, match="compiler receipt"):
        prepare_semantic_knowledge_store(path, repo_root=repo, data_root=config.data_root)
    assert not (config.data_root / registration["output_namespace"] / "completion.json").exists()


def _direct_validator_inputs(config):
    receipt = json.loads(config.receipt_output_path.read_text())
    snapshot_document = json.loads(config.snapshot_output_path.read_text())
    snapshot = KnowledgeSnapshot.from_frozen_json(snapshot_document)
    return receipt, snapshot


def test_shared_compiled_snapshot_validator_returns_bound_source_metadata(
    tmp_path, monkeypatch
):
    _repo, config, _path, _registration = _prepared(tmp_path)
    receipt, snapshot = _direct_validator_inputs(config)

    snapshot_file_sha256 = hashlib.sha256(
        config.snapshot_output_path.read_bytes()
    ).hexdigest()
    monkeypatch.setattr(
        Path,
        "read_bytes",
        lambda _path: pytest.fail("pure validator attempted file I/O"),
    )
    metadata = compiler.validate_compiled_knowledge_snapshot(
        receipt,
        snapshot,
        store_role="parameter-meaning",
        snapshot_file_sha256=snapshot_file_sha256,
        snapshot_path=config.snapshot_output_path,
    )

    assert metadata == receipt["knowledge_snapshot"]["source"]["metadata"]


@pytest.mark.parametrize(
    ("target_path", "replacement"),
    [
        (("knowledge_snapshot", "value_view"), "tool-activation"),
        (
            ("knowledge_snapshot", "source", "metadata", "value_view"),
            "tool-activation",
        ),
        (("knowledge_snapshot", "file_sha256"), "0" * 64),
        (("knowledge_snapshot", "snapshot_sha256"), "0" * 64),
        (("knowledge_snapshot", "source", "sha256"), "0" * 64),
        (("sources", "dataset_lock", "sha256"), "0" * 64),
        (("registry", "tool_count"), 151),
        (("knowledge_snapshot", "value_count"), 151),
    ],
)
def test_shared_compiled_snapshot_validator_rejects_direct_tampering(
    tmp_path, target_path, replacement
):
    _repo, config, _path, _registration = _prepared(tmp_path)
    receipt, snapshot = _direct_validator_inputs(config)
    target = receipt
    for key in target_path[:-1]:
        target = target[key]
    target[target_path[-1]] = replacement

    with pytest.raises(RailsError):
        compiler.validate_compiled_knowledge_snapshot(
            receipt,
            snapshot,
            store_role="parameter-meaning",
            snapshot_file_sha256=hashlib.sha256(
                config.snapshot_output_path.read_bytes()
            ).hexdigest(),
            snapshot_path=config.snapshot_output_path,
        )


def test_compiler_fixture_restores_process_socket_functions(tmp_path):
    before = (socket.socket.connect, socket.socket.connect_ex, socket.create_connection)
    _prepared(tmp_path)
    assert before == (socket.socket.connect, socket.socket.connect_ex, socket.create_connection)


@pytest.mark.parametrize("defect", ["swapped-targets", "swapped-facets", "swapped-value-ids"])
def test_compiled_validator_refuses_rehashed_tool_card_association_swaps(tmp_path, defect):
    _repo, config, _path, _registration = _prepared(tmp_path)
    receipt, snapshot = _direct_validator_inputs(config)
    values = list(snapshot.values)
    first, second = values[:2]
    field = {
        "swapped-targets": "task_target",
        "swapped-facets": "associated_facet_ids",
        "swapped-value-ids": "value_id",
    }[defect]
    values[0] = replace(first, **{field: getattr(second, field)})
    values[1] = replace(second, **{field: getattr(first, field)})
    changed = replace(snapshot, values=tuple(values)).validate()
    raw = canonical_bytes(changed.frozen_json())
    raw_sha = hashlib.sha256(raw).hexdigest()
    receipt["knowledge_snapshot"]["snapshot_sha256"] = changed.content_hash()
    receipt["knowledge_snapshot"]["file_sha256"] = raw_sha
    with pytest.raises(RailsError, match="tool-to-card association"):
        compiler.validate_compiled_knowledge_snapshot(
            receipt, changed, store_role="parameter-meaning",
            snapshot_file_sha256=raw_sha, snapshot_path=config.snapshot_output_path,
        )
