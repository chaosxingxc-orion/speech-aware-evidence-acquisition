"""Shared source-bound Audio2Tool semantic-card compilation."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails import (
    knowledge_compile_a2t as compilation,
)
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import (
    TIERS,
    A2tKbRow,
    a2t_metadata_inventory,
)
from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot


REPO = Path(__file__).resolve().parents[2]
HISTORICAL_SCRIPT = REPO / "scripts" / "build_a2t_g4_semantic_cards.py"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _registry_rows() -> tuple[dict[str, str], ...]:
    return tuple(
        {
            "tool_id": str(index),
            "domain": "synthetic",
            "category": f"group_{index % 4}",
            "tool_name": f"syntheticTool{index:03d}",
            "signature": f"syntheticTool{index:03d}()",
            "description": f"Perform synthetic operation {index:03d}.",
            "argument_defaults": "",
            "argument_constraints": "",
        }
        for index in range(152)
    )


def _row(index: int = 100) -> A2tKbRow:
    return A2tKbRow(
        unit_id=f"tier1_direct:{index:06d}",
        tier="tier1_direct",
        query_idx=index,
        text="PRIVATE SELECTED SOURCE",
        domain="private",
        category="private",
        tool_id=0,
        tool_name="syntheticTool000",
        arg_signature=(),
        arg_pairs=(),
        call_render="PRIVATE GOLD CALL",
        extra_call_names=(),
        call_count=1,
        sample_ids=(f"tier1_direct:{index:06d}",),
        item_ids=(index,),
        media_relpath_by_sample_id={
            f"tier1_direct:{index:06d}": "private/selected.wav"
        },
        speaker_ids=("PRIVATE SPEAKER",),
    )


def _manifest_entry(
    tier: str,
    item_id: int,
    query_idx: int,
    *,
    selected: bool,
) -> dict[str, object]:
    identity = {
        "id": item_id,
        "tier": tier,
        "query_idx": query_idx,
    }
    if not selected:
        return {
            **identity,
            "query": {"poison": "excluded invocation"},
            "user_request": {"poison": "excluded invocation"},
            "tool_name": {"poison": "excluded gold"},
            "expected_tool_call": {"poison": "excluded gold"},
            "path": {"poison": "excluded media"},
            "speaker_id": {"poison": "excluded speaker"},
        }
    return {
        **identity,
        "query": "PRIVATE SELECTED SOURCE",
        "user_request": "PRIVATE SELECTED SOURCE",
        "domain": "private",
        "category": "private",
        "tool_id": 0,
        "tool_name": "syntheticTool000",
        "expected_tool_call": "syntheticTool000()",
        "extracted_params": {},
        "additional_tool_calls": None,
        "path": f"{tier}_audios/query_{item_id:05d}/turn.wav",
        "duration": 0.25,
        "speaker_id": "PRIVATE SPEAKER",
    }


def _write_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _world(tmp_path: Path) -> compilation.A2tSemanticCardCompilationConfig:
    data_root = tmp_path / "data"
    carrier = data_root / "datasets" / "audio2tool"
    public = carrier / "public"
    for index, tier in enumerate(TIERS):
        manifest = public / f"{tier}_data" / f"{tier}.json"
        _write_json(
            manifest,
            [
                _manifest_entry(
                    tier,
                    100 + index,
                    1000 + index,
                    selected=index == 0,
                )
            ],
        )

    registry_path = carrier / "tools_registry.csv"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    with registry_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(_registry_rows()[0]))
        writer.writeheader()
        writer.writerows(_registry_rows())

    lock_path = tmp_path / "datasets.lock.json"
    _write_json(
        lock_path,
        {
            "datasets": [
                {
                    "name": "audio2tool",
                    "local_subdir": "datasets/audio2tool",
                }
            ]
        },
    )
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    inventory = a2t_metadata_inventory(lock, data_root)
    allowed = next(
        unit for unit in inventory["units"] if unit["unit_id"] == "tier1_direct:001000"
    )
    excluded = [
        sample_id
        for unit in inventory["units"]
        if unit["unit_id"] != allowed["unit_id"]
        for sample_id in unit["sample_ids"]
    ]
    selection_path = tmp_path / "construction-selection.json"
    _write_json(
        selection_path,
        {
            "schema": "saea-a2t-construction-selection-v1",
            "source_manifest_sha256_by_tier": inventory[
                "source_manifest_sha256_by_tier"
            ],
            "allowed_units": [
                {
                    "unit_id": allowed["unit_id"],
                    "sample_ids": allowed["sample_ids"],
                }
            ],
            "excluded_sample_ids": excluded,
        },
    )
    return compilation.A2tSemanticCardCompilationConfig(
        compilation_id="SYNTHETIC-CARD-COMPILATION",
        dataset_lock_path=lock_path,
        dataset_lock_sha256=_sha256(lock_path),
        data_root=data_root,
        construction_receipt_path=selection_path,
        construction_receipt_sha256=_sha256(selection_path),
        tool_registry_path=registry_path,
        tool_registry_sha256=_sha256(registry_path),
        corpus_output_path=tmp_path / "outputs" / "corpus.txt",
        receipt_output_path=tmp_path / "outputs" / "receipt.json",
    )


@pytest.fixture()
def offline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        compilation, "arm_offline_guard", lambda: SimpleNamespace(count=0)
    )


def _historical_builder():
    spec = importlib.util.spec_from_file_location(
        "build_a2t_g4_semantic_cards", HISTORICAL_SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_historical_script_reexports_the_shared_compiler_compatibly() -> None:
    historical = _historical_builder()

    assert (
        historical.derive_compatibility_rules is compilation.derive_compatibility_rules
    )
    assert historical.build_from_partition is compilation.build_from_partition
    assert (
        historical.G4SemanticCardBuildError is compilation.SemanticCardCompilationError
    )
    shared = compilation.build_from_partition(_registry_rows(), (_row(),))
    legacy = historical.build_from_partition(_registry_rows(), (_row(),))
    assert shared == legacy


def test_compilation_writes_all_tools_and_source_bound_provenance(
    tmp_path: Path, offline: None
) -> None:
    config = _world(tmp_path)

    receipt = compilation.compile_a2t_semantic_card_artifacts(config)

    assert json.loads(config.receipt_output_path.read_text(encoding="utf-8")) == receipt
    corpus = config.corpus_output_path.read_text(encoding="utf-8")
    assert "TOOL CARD syntheticTool000" in corpus
    assert "TOOL CARD syntheticTool151" in corpus
    assert "PRIVATE SELECTED SOURCE" not in corpus
    assert "poison" not in corpus
    assert receipt["registry"] == {
        "tool_count": 152,
        "selected_target_tool_count": 1,
        "selected_target_tools": ["syntheticTool000"],
        "schema_only_tool_count": 151,
        "schema_only_tools": [f"syntheticTool{index:03d}" for index in range(1, 152)],
    }
    assert receipt["sources"]["dataset_lock"]["sha256"] == config.dataset_lock_sha256
    assert (
        receipt["sources"]["construction_selection"]["sha256"]
        == config.construction_receipt_sha256
    )
    assert receipt["sources"]["tool_registry"]["sha256"] == config.tool_registry_sha256
    assert receipt["construction_selection"]["allowed_unit_count"] == 1
    assert receipt["construction_selection"]["excluded_sample_count"] == 7
    assert (
        receipt["corpus"]["sha256"]
        == hashlib.sha256(config.corpus_output_path.read_bytes()).hexdigest()
    )
    assert receipt["contacts"] == {
        "audio_seconds": 0,
        "embedding_tool": 0,
        "frozen_core": 0,
        "gpu_hours": 0,
        "network": 0,
        "retriever": 0,
        "scorer": 0,
        "tokenizer": 0,
    }


def test_compilation_is_deterministic_across_new_output_locations(
    tmp_path: Path, offline: None
) -> None:
    first_config = _world(tmp_path)
    first = compilation.compile_a2t_semantic_card_artifacts(first_config)
    second_config = replace(
        first_config,
        corpus_output_path=tmp_path / "second" / "corpus.txt",
        receipt_output_path=tmp_path / "second" / "receipt.json",
    )

    second = compilation.compile_a2t_semantic_card_artifacts(second_config)

    assert first_config.corpus_output_path.read_bytes() == (
        second_config.corpus_output_path.read_bytes()
    )
    assert first["corpus"]["sha256"] == second["corpus"]["sha256"]
    assert first["compiler"] == second["compiler"]
    assert first["registry"] == second["registry"]
    assert first["construction_selection"] == second["construction_selection"]


def test_compilation_opt_in_uses_public_legality_presentation(
    tmp_path: Path, offline: None
) -> None:
    config = replace(
        _world(tmp_path),
        presentation_version=compilation.PUBLIC_API_LEGALITY_PRESENTATION_V1,
    )

    receipt = compilation.compile_a2t_semantic_card_artifacts(config)

    corpus = config.corpus_output_path.read_text(encoding="utf-8")
    assert "Public argument legality:" in corpus
    assert "Construction-observed argument patterns:" in corpus
    assert "poison" not in corpus
    assert receipt["compiler"]["presentation_version"] == (
        compilation.PUBLIC_API_LEGALITY_PRESENTATION_V1
    )
    assert receipt["corpus"]["report"]["unobserved_public_combinations_forbidden"] is (
        False
    )


def test_compilation_refuses_unknown_presentation_before_reading_sources(
    tmp_path: Path, offline: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = replace(_world(tmp_path), presentation_version="unknown-presentation")
    monkeypatch.setattr(
        compilation,
        "a2t_pool_rows",
        lambda *_args, **_kwargs: pytest.fail("source pool was read"),
    )

    with pytest.raises(
        compilation.SemanticCardCompilationError,
        match="presentation_version",
    ):
        compilation.compile_a2t_semantic_card_artifacts(config)

    assert not config.corpus_output_path.exists()
    assert not config.receipt_output_path.exists()


@pytest.mark.parametrize(
    ("change", "message"),
    (
        (
            lambda config, tmp_path: replace(config, dataset_lock_sha256="0" * 64),
            "dataset lock SHA-256",
        ),
        (
            lambda config, tmp_path: replace(config, tool_registry_sha256="0" * 64),
            "tool registry SHA-256",
        ),
        (
            lambda config, tmp_path: replace(
                config,
                tool_registry_path=tmp_path / "different-registry.csv",
            ),
            "resolved public tool registry",
        ),
        (
            lambda config, tmp_path: replace(
                config, construction_receipt_sha256="0" * 64
            ),
            "construction receipt SHA-256",
        ),
    ),
)
def test_compilation_refuses_wrong_source_bindings(
    tmp_path: Path, offline: None, change, message: str
) -> None:
    config = change(_world(tmp_path), tmp_path)

    with pytest.raises(compilation.SemanticCardCompilationError, match=message):
        compilation.compile_a2t_semantic_card_artifacts(config)

    assert not config.corpus_output_path.exists()
    assert not config.receipt_output_path.exists()


def test_compilation_refuses_registry_drift_during_parse(
    tmp_path: Path, offline: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _world(tmp_path)
    load_registry = compilation.load_tool_registry

    def load_then_mutate(lock, data_root):
        rows = load_registry(lock, data_root)
        config.tool_registry_path.write_bytes(
            config.tool_registry_path.read_bytes() + b"\n"
        )
        return rows

    monkeypatch.setattr(compilation, "load_tool_registry", load_then_mutate)

    with pytest.raises(
        compilation.SemanticCardCompilationError,
        match="changed while it was being parsed",
    ):
        compilation.compile_a2t_semantic_card_artifacts(config)

    assert not config.corpus_output_path.exists()
    assert not config.receipt_output_path.exists()


def test_compilation_refuses_overwrite_without_reading_sources(
    tmp_path: Path, offline: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _world(tmp_path)
    config.corpus_output_path.parent.mkdir(parents=True)
    config.corpus_output_path.write_text("PRESERVE\n", encoding="utf-8")
    monkeypatch.setattr(
        compilation,
        "a2t_pool_rows",
        lambda *_args, **_kwargs: pytest.fail("source pool was read"),
    )

    with pytest.raises(
        compilation.SemanticCardCompilationError, match="already exists"
    ):
        compilation.compile_a2t_semantic_card_artifacts(config)

    assert config.corpus_output_path.read_text(encoding="utf-8") == "PRESERVE\n"
    assert not config.receipt_output_path.exists()


def test_compilation_never_overwrites_a_completed_pair(
    tmp_path: Path, offline: None
) -> None:
    config = _world(tmp_path)
    compilation.compile_a2t_semantic_card_artifacts(config)
    original_corpus = config.corpus_output_path.read_bytes()
    original_receipt = config.receipt_output_path.read_bytes()

    with pytest.raises(
        compilation.SemanticCardCompilationError, match="already exists"
    ):
        compilation.compile_a2t_semantic_card_artifacts(config)

    assert config.corpus_output_path.read_bytes() == original_corpus
    assert config.receipt_output_path.read_bytes() == original_receipt


def test_compilation_refuses_an_offline_guard_attempt_without_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _world(tmp_path)
    monkeypatch.setattr(
        compilation, "arm_offline_guard", lambda: SimpleNamespace(count=1)
    )

    with pytest.raises(
        compilation.SemanticCardCompilationError, match="outbound attempt"
    ):
        compilation.compile_a2t_semantic_card_artifacts(config)

    assert not config.corpus_output_path.exists()
    assert not config.receipt_output_path.exists()


def test_compilation_opt_in_uses_native_compatible_presentation(
    tmp_path: Path, offline: None
) -> None:
    config = replace(
        _world(tmp_path),
        presentation_version=compilation.NATIVE_COMPATIBLE_PRESENTATION_V1,
    )

    receipt = compilation.compile_a2t_semantic_card_artifacts(config)

    corpus = config.corpus_output_path.read_text(encoding="utf-8")
    assert "Public API documentation:" in corpus
    assert "Observed native task forms:" in corpus
    assert "poison" not in corpus
    assert receipt["compiler"]["presentation_version"] == (
        compilation.NATIVE_COMPATIBLE_PRESENTATION_V1
    )
    assert receipt["corpus"]["report"]["observations_exhaustive"] is False
    assert (
        receipt["corpus"]["report"][
            "public_required_keys_forced_into_observed_replacements"
        ]
        is False
    )


def test_native_compilation_can_export_a_source_bound_snapshot(
    tmp_path: Path, offline: None
) -> None:
    config = replace(
        _world(tmp_path),
        presentation_version=compilation.NATIVE_COMPATIBLE_PRESENTATION_V1,
        snapshot_output_path=tmp_path / "outputs" / "snapshot.json",
    )

    receipt = compilation.compile_a2t_semantic_card_artifacts(config)

    frozen = json.loads(config.snapshot_output_path.read_text(encoding="utf-8"))
    snapshot = KnowledgeSnapshot.from_frozen_json(frozen)
    assert snapshot.source_partition_role == "external-governed"
    assert len(snapshot.facets) == len(snapshot.values) == 152
    assert {value.task_target for value in snapshot.values} == {
        f"syntheticTool{index:03d}" for index in range(152)
    }
    assert any(value.task_target == "syntheticTool151" for value in snapshot.values)

    facets = {facet.facet_id: facet for facet in snapshot.facets}
    values = {value.task_target: value for value in snapshot.values}
    selected_value = values["syntheticTool000"]
    selected_key = facets[selected_value.associated_facet_ids[0]].representation
    schema_only_value = values["syntheticTool151"]
    schema_only_key = facets[schema_only_value.associated_facet_ids[0]].representation
    assert "Exact tool name: syntheticTool000 (synthetic tool 000)." in selected_key
    assert "Choose semantics: Perform synthetic operation 000." in selected_key
    assert "Avoid when:" not in selected_key
    assert "Avoid when:" in selected_value.content
    assert selected_value.content in config.corpus_output_path.read_text(
        encoding="utf-8"
    )
    assert "Exact tool name: syntheticTool151" in schema_only_key
    assert "TOOL CARD syntheticTool151" in schema_only_value.content

    snapshot_receipt = receipt["knowledge_snapshot"]
    assert snapshot_receipt["snapshot_sha256"] == frozen["snapshot_sha256"]
    assert (
        snapshot_receipt["file_sha256"]
        == hashlib.sha256(config.snapshot_output_path.read_bytes()).hexdigest()
    )
    assert snapshot_receipt["positive_content_facet_count"] == 152
    assert snapshot_receipt["value_count"] == 152
    assert snapshot_receipt["schema_only_tool_count"] == 151
    assert snapshot_receipt["avoid_semantics_in_positive_keys"] is False
    assert snapshot.source_split_identity_hash == snapshot_receipt["source"]["sha256"]
    for value in snapshot.values:
        card_hash_ref = next(
            ref
            for ref in value.provenance_refs
            if ref.startswith("a2t-native-card-sha256:")
        )
        assert card_hash_ref.removeprefix("a2t-native-card-sha256:") == (
            hashlib.sha256(value.content.encode("utf-8")).hexdigest()
        )


def test_snapshot_export_is_deterministic_and_does_not_change_default_outputs(
    tmp_path: Path, offline: None
) -> None:
    default_config = _world(tmp_path / "default")
    default_receipt = compilation.compile_a2t_semantic_card_artifacts(default_config)
    assert "knowledge_snapshot" not in default_receipt

    first_config = replace(
        _world(tmp_path / "first"),
        presentation_version=compilation.NATIVE_COMPATIBLE_PRESENTATION_V1,
        snapshot_output_path=tmp_path / "first" / "snapshot.json",
    )
    second_config = replace(
        _world(tmp_path / "second"),
        presentation_version=compilation.NATIVE_COMPATIBLE_PRESENTATION_V1,
        snapshot_output_path=tmp_path / "second" / "snapshot.json",
    )

    first = compilation.compile_a2t_semantic_card_artifacts(first_config)
    second = compilation.compile_a2t_semantic_card_artifacts(second_config)

    assert first_config.snapshot_output_path.read_bytes() == (
        second_config.snapshot_output_path.read_bytes()
    )
    assert (
        first["knowledge_snapshot"]["source"] == second["knowledge_snapshot"]["source"]
    )
    assert (
        first["knowledge_snapshot"]["snapshot_sha256"]
        == second["knowledge_snapshot"]["snapshot_sha256"]
    )


@pytest.mark.parametrize(
    "presentation_version",
    (None, compilation.PUBLIC_API_LEGALITY_PRESENTATION_V1),
)
def test_snapshot_export_refuses_non_native_presentations_before_reading_sources(
    tmp_path: Path,
    offline: None,
    monkeypatch: pytest.MonkeyPatch,
    presentation_version: str | None,
) -> None:
    config = replace(
        _world(tmp_path),
        presentation_version=presentation_version,
        snapshot_output_path=tmp_path / "outputs" / "snapshot.json",
    )
    monkeypatch.setattr(
        compilation,
        "a2t_pool_rows",
        lambda *_args, **_kwargs: pytest.fail("source pool was read"),
    )

    with pytest.raises(
        compilation.SemanticCardCompilationError,
        match="native-compatible presentation",
    ):
        compilation.compile_a2t_semantic_card_artifacts(config)

    assert not config.corpus_output_path.exists()
    assert not config.receipt_output_path.exists()
    assert not config.snapshot_output_path.exists()


def test_snapshot_export_refuses_overwrite_without_partial_outputs(
    tmp_path: Path, offline: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = replace(
        _world(tmp_path),
        presentation_version=compilation.NATIVE_COMPATIBLE_PRESENTATION_V1,
        snapshot_output_path=tmp_path / "outputs" / "snapshot.json",
    )
    config.snapshot_output_path.parent.mkdir(parents=True)
    config.snapshot_output_path.write_text("PRESERVE\n", encoding="utf-8")
    monkeypatch.setattr(
        compilation,
        "a2t_pool_rows",
        lambda *_args, **_kwargs: pytest.fail("source pool was read"),
    )

    with pytest.raises(
        compilation.SemanticCardCompilationError, match="already exists"
    ):
        compilation.compile_a2t_semantic_card_artifacts(config)

    assert config.snapshot_output_path.read_text(encoding="utf-8") == "PRESERVE\n"
    assert not config.corpus_output_path.exists()
    assert not config.receipt_output_path.exists()


def test_snapshot_export_refuses_an_output_path_alias_before_reading_sources(
    tmp_path: Path, offline: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = _world(tmp_path)
    config = replace(
        base,
        presentation_version=compilation.NATIVE_COMPATIBLE_PRESENTATION_V1,
        snapshot_output_path=base.corpus_output_path,
    )
    monkeypatch.setattr(
        compilation,
        "a2t_pool_rows",
        lambda *_args, **_kwargs: pytest.fail("source pool was read"),
    )

    with pytest.raises(
        compilation.SemanticCardCompilationError,
        match="output paths must be different",
    ):
        compilation.compile_a2t_semantic_card_artifacts(config)

    assert not config.corpus_output_path.exists()
    assert not config.receipt_output_path.exists()


def _native_source(corpus, *, value_view: str | None = None) -> dict[str, object]:
    source: dict[str, object] = {
        "schema": compilation.NATIVE_CARD_SNAPSHOT_SOURCE_V1,
        "compilation_id": "SYNTHETIC-CARD-COMPILATION",
        "presentation_version": compilation.NATIVE_COMPATIBLE_PRESENTATION_V1,
        "dataset_lock_sha256": "1" * 64,
        "construction_selection_sha256": "2" * 64,
        "tool_registry_sha256": "3" * 64,
        "corpus_sha256": corpus.sha256,
        "minimum_compatibility_support": 2,
        "max_utf8_bytes": 524288,
    }
    if value_view is not None:
        source["value_view"] = value_view
    return source


def _compile_native_view(tmp_path: Path, value_view: str | None):
    config = replace(
        _world(tmp_path),
        presentation_version=compilation.NATIVE_COMPATIBLE_PRESENTATION_V1,
        snapshot_output_path=tmp_path / "outputs" / "snapshot.json",
        snapshot_value_view=value_view,
    )
    receipt = compilation.compile_a2t_semantic_card_artifacts(config)
    snapshot = KnowledgeSnapshot.from_frozen_json(
        json.loads(config.snapshot_output_path.read_text(encoding="utf-8"))
    )
    return receipt, snapshot


def test_native_snapshot_value_views_preserve_keys_and_all_tools(
    tmp_path: Path, offline: None
) -> None:
    full_receipt, full = _compile_native_view(tmp_path / "full", "full")
    activation_receipt, activation = _compile_native_view(
        tmp_path / "activation", "tool-activation"
    )
    parameter_receipt, parameter = _compile_native_view(
        tmp_path / "parameter", "parameter-meaning"
    )
    expected_keys = [(facet.facet_id, facet.representation) for facet in full.facets]
    assert [(facet.facet_id, facet.representation) for facet in activation.facets] == expected_keys
    assert [(facet.facet_id, facet.representation) for facet in parameter.facets] == expected_keys
    for snapshot in (full, activation, parameter):
        assert len(snapshot.facets) == len(snapshot.values) == 152
        assert {value.task_target for value in snapshot.values} == {
            f"syntheticTool{index:03d}" for index in range(152)
        }

    activation_value = next(v for v in activation.values if v.task_target == "syntheticTool000")
    lines = activation_value.content.splitlines()
    assert lines[:3] == [
        "TOOL CARD syntheticTool000",
        "Exact tool name: syntheticTool000",
        "Choose when: Perform synthetic operation 000.",
    ]
    assert len(lines) == 4
    assert lines[3].startswith("Avoid when: ")
    assert "Public signature:" not in activation_value.content

    parameter_value = next(v for v in parameter.values if v.task_target == "syntheticTool000")
    assert "Choose when:" not in parameter_value.content
    assert "Avoid when:" not in parameter_value.content
    for retained in (
        "Exact tool name: syntheticTool000",
        "Public signature:",
        "Public types:",
        "Public constraints:",
        "Public API documentation: required keys",
        "Observed native task forms:",
        "Native task form scope:",
        "Public spoken-role-to-key guidance:",
        "Observed native-role-to-key guidance:",
        "Public synthetic JSON examples:",
        "Native-form synthetic JSON examples:",
    ):
        assert retained in parameter_value.content

    assert "value_view" not in full_receipt["knowledge_snapshot"]
    assert "value_view" not in full_receipt["knowledge_snapshot"]["source"]["metadata"]
    for receipt, view in (
        (activation_receipt, "tool-activation"),
        (parameter_receipt, "parameter-meaning"),
    ):
        assert receipt["knowledge_snapshot"]["value_view"] == view
        assert receipt["knowledge_snapshot"]["source"]["metadata"]["value_view"] == view


def test_nondefault_value_view_is_bound_in_each_value_provenance(
    tmp_path: Path, offline: None
) -> None:
    _receipt, snapshot = _compile_native_view(tmp_path, "parameter-meaning")
    for value in snapshot.values:
        assert "a2t-native-card-value-view:parameter-meaning" in value.provenance_refs


@pytest.mark.parametrize("value_view", ("", "unknown", []))
def test_compilation_refuses_unknown_snapshot_value_view_before_reading_sources(
    tmp_path: Path, offline: None, monkeypatch: pytest.MonkeyPatch, value_view
) -> None:
    config = replace(_world(tmp_path), snapshot_value_view=value_view)
    monkeypatch.setattr(
        compilation, "a2t_pool_rows",
        lambda *_args, **_kwargs: pytest.fail("source pool was read"),
    )
    with pytest.raises(compilation.SemanticCardCompilationError, match="snapshot_value_view"):
        compilation.compile_a2t_semantic_card_artifacts(config)


@pytest.mark.parametrize(
    ("presentation_version", "with_snapshot"),
    ((None, True), (compilation.NATIVE_COMPATIBLE_PRESENTATION_V1, False)),
)
def test_nondefault_value_view_requires_native_snapshot_export_before_source_read(
    tmp_path: Path, offline: None, monkeypatch: pytest.MonkeyPatch,
    presentation_version: str | None, with_snapshot: bool
) -> None:
    config = replace(
        _world(tmp_path),
        presentation_version=presentation_version,
        snapshot_output_path=(tmp_path / "outputs" / "snapshot.json") if with_snapshot else None,
        snapshot_value_view="tool-activation",
    )
    monkeypatch.setattr(
        compilation, "a2t_pool_rows",
        lambda *_args, **_kwargs: pytest.fail("source pool was read"),
    )
    with pytest.raises(
        compilation.SemanticCardCompilationError,
        match="non-default snapshot_value_view requires native-compatible snapshot export",
    ):
        compilation.compile_a2t_semantic_card_artifacts(config)


def test_native_snapshot_refuses_source_view_mismatch() -> None:
    corpus, _ = compilation.build_from_partition_with_native_compatibility(
        _registry_rows(), (_row(),)
    )
    with pytest.raises(compilation.SemanticCardCompilationError, match="value view does not match"):
        compilation.build_native_compatible_knowledge_snapshot(
            corpus,
            compilation_source=_native_source(corpus, value_view="parameter-meaning"),
            value_view="tool-activation",
        )


def test_nondefault_native_snapshot_refuses_card_prefix_drift() -> None:
    corpus, _ = compilation.build_from_partition_with_native_compatibility(
        _registry_rows(), (_row(),)
    )
    malformed = replace(
        corpus.tool_cards[0],
        text=corpus.tool_cards[0].text.replace("Choose when:", "Select when:", 1),
    )
    drifted = replace(corpus, tool_cards=(malformed, *corpus.tool_cards[1:]))
    with pytest.raises(compilation.SemanticCardCompilationError, match="activation prefix drift"):
        compilation.build_native_compatible_knowledge_snapshot(
            drifted,
            compilation_source=_native_source(corpus, value_view="parameter-meaning"),
            value_view="parameter-meaning",
        )


def test_explicit_full_value_view_is_identical_to_omission(
    tmp_path: Path, offline: None
) -> None:
    omitted_receipt, omitted = _compile_native_view(tmp_path / "omitted", None)
    explicit_receipt, explicit = _compile_native_view(tmp_path / "explicit", "full")

    assert omitted.frozen_json() == explicit.frozen_json()
    assert omitted.frozen_json()["snapshot_sha256"] == (
        "d88f144e5273c9497318a9fe568ff7d9b93e3b277256fffdeca7f3047bb21a2e"
    )
    frozen_bytes = (json.dumps(omitted.frozen_json(), indent=2, sort_keys=True) + "\n").encode()
    assert hashlib.sha256(frozen_bytes).hexdigest() == (
        "8d476d35537c4fd5292571026fa268b20950dde965d324e262c65baf5a591c2e"
    )
    assert omitted_receipt["knowledge_snapshot"]["source"] == (
        explicit_receipt["knowledge_snapshot"]["source"]
    )
    assert "value_view" not in omitted_receipt["knowledge_snapshot"]
    assert "value_view" not in explicit_receipt["knowledge_snapshot"]


def test_parameter_meaning_retains_supported_native_form_details() -> None:
    registry = list(_registry_rows())
    registry[0] = {
        **registry[0],
        "signature": "syntheticTool000(deviceId: String?)",
        "argument_constraints": "deviceId: [named device]",
    }
    rows = tuple(
        replace(
            _row(index),
            arg_signature=("action", "deviceId"),
            arg_pairs=(("action", "play"), ("deviceId", "device")),
        )
        for index in (100, 101)
    )
    corpus, _ = compilation.build_from_partition_with_native_compatibility(
        tuple(registry), rows
    )
    snapshot = compilation.build_native_compatible_knowledge_snapshot(
        corpus,
        compilation_source=_native_source(
            corpus, value_view="parameter-meaning"
        ),
        value_view="parameter-meaning",
    )
    content = next(
        value.content
        for value in snapshot.values
        if value.task_target == "syntheticTool000"
    )

    assert "Choose when:" not in content
    assert "Avoid when:" not in content
    assert "Public signature: syntheticTool000(deviceId: String?)" in content
    assert "Public constraints: deviceId: [named device]" in content
    assert "Observed native task forms:" in content
    assert "action: JSON string" in content
    assert "construction support count: 2" in content
    assert "source scope: hash-pinned, evaluation-excluded construction units" in content
    assert "Observed native role: action -> action (JSON string)" in content
    assert "Native-form synthetic JSON examples:" in content


def _config_document(
    config: compilation.A2tSemanticCardCompilationConfig,
) -> dict[str, object]:
    document: dict[str, object] = {
        "compilation_id": config.compilation_id,
        "dataset_lock_path": str(config.dataset_lock_path),
        "dataset_lock_sha256": config.dataset_lock_sha256,
        "data_root": str(config.data_root),
        "construction_receipt_path": str(config.construction_receipt_path),
        "construction_receipt_sha256": config.construction_receipt_sha256,
        "tool_registry_path": str(config.tool_registry_path),
        "tool_registry_sha256": config.tool_registry_sha256,
        "corpus_output_path": str(config.corpus_output_path),
        "receipt_output_path": str(config.receipt_output_path),
        "minimum_compatibility_support": config.minimum_compatibility_support,
        "max_utf8_bytes": config.max_utf8_bytes,
        "presentation_version": config.presentation_version,
        "snapshot_output_path": (
            str(config.snapshot_output_path)
            if config.snapshot_output_path is not None
            else None
        ),
        "snapshot_value_view": config.snapshot_value_view,
    }
    return document


def test_cli_loads_pinned_config_and_honors_snapshot_value_view(
    tmp_path: Path, offline: None, capsys: pytest.CaptureFixture[str]
) -> None:
    config = replace(
        _world(tmp_path),
        presentation_version=compilation.NATIVE_COMPATIBLE_PRESENTATION_V1,
        snapshot_output_path=tmp_path / "outputs" / "snapshot.json",
        snapshot_value_view="tool-activation",
    )
    config_path = tmp_path / "compilation.json"
    _write_json(config_path, _config_document(config))

    assert compilation.main(["--config", str(config_path)]) == 0

    snapshot = KnowledgeSnapshot.from_frozen_json(
        json.loads(config.snapshot_output_path.read_text(encoding="utf-8"))
    )
    assert all("Choose when:" in value.content for value in snapshot.values)
    assert all("Public signature:" not in value.content for value in snapshot.values)
    summary = json.loads(capsys.readouterr().out)
    assert summary["compilation_id"] == config.compilation_id
    assert summary["snapshot_value_view"] == "tool-activation"
    assert summary["receipt_output_path"] == str(config.receipt_output_path)


@pytest.mark.parametrize(
    ("mutate", "message"),
    (
        (lambda document: document.update({"unknown": True}), "missing or unknown fields"),
        (lambda document: document.pop("compilation_id"), "missing or unknown fields"),
        (lambda document: document.update({"data_root": 7}), "data_root"),
        (
            lambda document: document.update({"minimum_compatibility_support": True}),
            "minimum_compatibility_support",
        ),
        (
            lambda document: document.update({"snapshot_value_view": []}),
            "snapshot_value_view",
        ),
    ),
)
def test_config_loader_refuses_malformed_or_unknown_fields(
    tmp_path: Path, mutate, message: str
) -> None:
    config = _world(tmp_path)
    document = _config_document(config)
    mutate(document)
    path = tmp_path / "invalid.json"
    _write_json(path, document)

    with pytest.raises(compilation.SemanticCardCompilationError, match=message):
        compilation.load_a2t_semantic_card_compilation_config(path)


def test_config_loader_refuses_malformed_json(tmp_path: Path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text("{", encoding="utf-8")

    with pytest.raises(compilation.SemanticCardCompilationError, match="cannot parse"):
        compilation.load_a2t_semantic_card_compilation_config(path)


def test_cli_invalid_config_fails_before_compilation_or_output(
    tmp_path: Path, offline: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _world(tmp_path)
    document = _config_document(config)
    document["unknown"] = "forged"
    path = tmp_path / "invalid.json"
    _write_json(path, document)
    monkeypatch.setattr(
        compilation,
        "compile_a2t_semantic_card_artifacts",
        lambda _config: pytest.fail("compiler was invoked"),
    )

    with pytest.raises(
        compilation.SemanticCardCompilationError,
        match="missing or unknown fields",
    ):
        compilation.main(["--config", str(path)])

    assert not config.corpus_output_path.exists()
    assert not config.receipt_output_path.exists()
