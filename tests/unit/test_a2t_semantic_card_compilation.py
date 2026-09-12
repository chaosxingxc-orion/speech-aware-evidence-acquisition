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
