"""Model-free build boundary for the full Audio2Tool action schema."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails.a2t_executable_semantic_cards import (
    CompatibilityRule,
    ExecutableSemanticCardCorpus,
    ToolSemanticCard,
)


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "build_a2t_structured_action_schema.py"


def _builder():
    spec = importlib.util.spec_from_file_location(
        "build_a2t_structured_action_schema", SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _production_shape() -> tuple[
    tuple[dict[str, str], ...], ExecutableSemanticCardCorpus, dict[str, object]
]:
    registry: list[dict[str, str]] = []
    cards: list[ToolSemanticCard] = []
    rules: list[CompatibilityRule] = []
    for index in range(152):
        name = f"actionTool{index:03d}"
        rich = index < 93
        signature = f"{name}(first: String?, second: String?)" if rich else f"{name}()"
        skeletons = ((), ("first",), ("first", "second")) if rich else ((),)
        card_rules: tuple[CompatibilityRule, ...] = ()
        if index < 43:
            rule = CompatibilityRule(
                tool_name=name,
                legal_argument_key_set=("first",),
                value_forms=(("first", "string"),),
                construction_support_count=2,
            )
            rules.append(rule)
            card_rules = (rule,)
        registry.append(
            {
                "tool_name": name,
                "signature": signature,
                "argument_constraints": "",
            }
        )
        cards.append(
            ToolSemanticCard(
                tool_name=name,
                choose_semantics="SYNTHETIC_SOURCE_VALUE_MUST_NOT_RENDER",
                avoid_semantics="SYNTHETIC_EVAL_VALUE_MUST_NOT_RENDER",
                signature=signature,
                constraints="",
                legal_argument_key_sets=skeletons,
                compatibility_rules=card_rules,
                role_guidance=("SYNTHETIC_ROLE_VALUE_MUST_NOT_RENDER",),
                examples=("SYNTHETIC_EXAMPLE_VALUE_MUST_NOT_RENDER",),
                text="SYNTHETIC_CARD_TEXT_MUST_NOT_RENDER",
            )
        )
    report = {
        "registry_tool_count": 152,
        "tool_card_count": 152,
        "legal_argument_key_set_count": 338,
        "compatibility_rule_count": 43,
        "source_utterances_rendered": 0,
        "source_argument_values_rendered": 0,
        "source_sample_ids_rendered": 0,
        "reference_transcripts_rendered": 0,
        "gold_values_rendered": 0,
        "evaluation_samples_consumed": 0,
    }
    corpus = ExecutableSemanticCardCorpus(
        text="SYNTHETIC_CORPUS_TEXT_MUST_NOT_RENDER",
        sha256="c" * 64,
        tool_cards=tuple(cards),
        task_cards=(),
        report=report,
    )
    audit = {
        "deterministic_rebuild_equal": True,
        "construction_argument_pattern_family_count": 354,
        "construction_argument_key_count": 85,
        "safe_construction_row_count": 12_550,
        "excluded_construction_row_count": 51,
        "compatibility": {
            "minimum_support": 2,
            "rule_count": len(rules),
            "source_utterances_rendered": 0,
            "source_sample_ids_rendered": 0,
            "call_renders_rendered": 0,
            "concrete_argument_values_rendered": 0,
            "reference_transcripts_rendered": 0,
            "evaluation_rows_consumed": 0,
        },
    }
    return tuple(registry), corpus, audit


def test_pure_build_renders_the_full_canonical_value_free_schema() -> None:
    builder = _builder()
    registry, corpus, audit = _production_shape()

    artifact = builder.build_structured_action_schema(registry, corpus, audit)

    assert artifact.response_format["type"] == "json_schema"
    assert artifact.tool_count == 152
    assert artifact.branch_count == 338
    assert artifact.compatibility_rule_count == 43
    assert artifact.text.isascii()
    assert (
        artifact.text
        == json.dumps(
            artifact.response_format,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    )
    assert artifact.utf8_bytes == len(artifact.text.encode("ascii"))
    assert artifact.sha256 == hashlib.sha256(artifact.text.encode("ascii")).hexdigest()
    assert "SYNTHETIC_" not in artifact.text
    assert artifact.safety == {
        "card_examples_consumed": 0,
        "card_text_consumed": 0,
        "source_utterances_rendered": 0,
        "source_argument_values_rendered": 0,
        "source_sample_ids_rendered": 0,
        "reference_transcripts_rendered": 0,
        "gold_values_rendered": 0,
        "evaluation_rows_consumed": 0,
    }


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("registry_tool_count", 151, "152 tools"),
        ("legal_argument_key_set_count", 337, "338 branches"),
        ("compatibility_rule_count", 42, "43 compatibility rules"),
        ("source_argument_values_rendered", 1, "value-free"),
    ),
)
def test_pure_build_refuses_g4_identity_or_safety_drift(
    field: str, value: int, message: str
) -> None:
    builder = _builder()
    registry, corpus, audit = _production_shape()
    changed_report = {**corpus.report, field: value}
    changed = ExecutableSemanticCardCorpus(
        text=corpus.text,
        sha256=corpus.sha256,
        tool_cards=corpus.tool_cards,
        task_cards=corpus.task_cards,
        report=changed_report,
    )

    with pytest.raises(builder.StructuredActionSchemaBuildError, match=message):
        builder.build_structured_action_schema(registry, changed, audit)


def test_run_build_records_pinned_sources_zero_contacts_and_offline_guard(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    builder = _builder()
    registry, corpus, audit = _production_shape()
    corpus = replace(corpus, sha256=builder.G4_CORPUS_SHA256)
    partition = SimpleNamespace(
        construction=(
            SimpleNamespace(unit_id="construction-1", sample_ids=("sample-1",)),
        ),
        eval_sample_ids=("evaluation-1",),
        policy_id="saea-a2t-block-partition-v1",
        seed=builder.PARTITION_SEED,
        split_identity_hash=lambda: builder.PROPOSED_EVAL_IDENTITY,
    )
    g4_receipt = {
        "source_hashes": {
            "builder": builder.G4_BUILDER_SHA256,
            "registry": builder.REGISTRY_SHA256,
        },
        "corpus": {"sha256": builder.G4_CORPUS_SHA256},
    }
    hashes = {
        builder.PARTITION_PROPOSAL: builder.PARTITION_PROPOSAL_SHA256,
        builder.G4_BUILDER: builder.G4_BUILDER_SHA256,
        builder.G4_CORPUS: builder.G4_CORPUS_SHA256,
        builder.G4_RECEIPT: builder.G4_RECEIPT_SHA256,
        builder.RESPONSE_SCHEMA_BUILDER: "d" * 64,
        Path(builder.__file__): "e" * 64,
    }
    monkeypatch.setattr(builder, "require_clean_study_repo", lambda _repo: "abc123")
    monkeypatch.setattr(builder, "arm_offline_guard", lambda: SimpleNamespace(count=0))
    monkeypatch.setattr(
        builder,
        "_sha256_file",
        lambda path: hashes.get(Path(path), builder.REGISTRY_SHA256),
    )
    monkeypatch.setattr(builder, "_read_json", lambda _path: g4_receipt)
    monkeypatch.setattr(builder, "load_lock", lambda _path: object())
    monkeypatch.setattr(builder, "umbrella_lock_path", lambda _repo: Path("lock"))
    monkeypatch.setattr(builder, "asset_dir", lambda _lock, _name, root: root)
    monkeypatch.setattr(builder, "load_tool_registry", lambda _lock, _root: registry)
    monkeypatch.setattr(
        builder,
        "a2t_pool_rows",
        lambda _lock, _root: (
            partition.construction,
            {"pool_items": 1, "pool_units": 1, "usable_units": 1},
        ),
    )
    monkeypatch.setattr(builder, "exposed_sample_ids", lambda _repo: frozenset())
    monkeypatch.setattr(
        builder, "propose_partition", lambda _rows, _exposed, seed: partition
    )
    monkeypatch.setattr(
        builder.g4_builder,
        "build_from_partition",
        lambda _registry, _construction: (corpus, audit),
    )

    artifact, receipt = builder.run_build(tmp_path)

    assert receipt["study_commit"] == "abc123"
    assert receipt["schema_artifact"]["sha256"] == artifact.sha256
    assert receipt["schema_artifact"]["utf8_bytes"] == artifact.utf8_bytes
    assert receipt["schema_artifact"]["branch_count"] == 338
    assert receipt["source_hashes"]["g4_builder"] == builder.G4_BUILDER_SHA256
    assert receipt["source_hashes"]["g4_corpus"] == builder.G4_CORPUS_SHA256
    assert receipt["source_hashes"]["g4_receipt"] == builder.G4_RECEIPT_SHA256
    assert set(receipt["contacts"].values()) == {0}
    assert receipt["offline_guard"] == {
        "outbound_connection_attempts": 0,
        "targets": [],
    }


def test_main_defaults_schema_to_data_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    builder = _builder()
    artifact = SimpleNamespace(text='{"type":"json_schema"}\n')
    receipt = {"schema": "test", "contacts": {"frozen_core": 0}}
    receipt_path = tmp_path / "receipt.json"
    monkeypatch.setattr(builder, "data_root", lambda: tmp_path)
    monkeypatch.setattr(builder, "run_build", lambda _root: (artifact, receipt))

    assert builder.main(["--receipt-output", str(receipt_path)]) == 0
    schema_path = (
        tmp_path
        / "knowledge"
        / "audio2tool"
        / "structured-action-schema-v1"
        / "response-format.json"
    )
    assert schema_path.read_text(encoding="ascii") == artifact.text
    assert json.loads(receipt_path.read_text(encoding="utf-8")) == receipt
