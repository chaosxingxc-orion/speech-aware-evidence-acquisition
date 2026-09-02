"""Model-free construction of the frozen G4 executable semantic-card corpus."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import A2tKbRow

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "build_a2t_g4_semantic_cards.py"
CORPUS = (
    REPO
    / "knowledge"
    / "audio2tool"
    / "g4-executable-semantic-cards-v1"
    / "corpus.txt"
)
RECEIPT = (
    REPO
    / "docs"
    / "checks"
    / "speech-aware-evidence-acquisition"
    / "2026-09-02-a2t-g4-semantic-cards-build-v1"
    / "build-receipt.json"
)


def _builder():
    spec = importlib.util.spec_from_file_location("build_a2t_g4_semantic_cards", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _registry_row(name: str, signature: str) -> dict[str, str]:
    return {
        "tool_id": "1",
        "domain": "synthetic",
        "category": "synthetic",
        "tool_name": name,
        "signature": signature,
        "description": f"Perform the artificial {name} operation.",
        "argument_defaults": "",
        "argument_constraints": "",
    }


def _row(
    index: int,
    tool: str,
    pairs: tuple[tuple[str, str], ...],
    *,
    private: str = "PRIVATE SOURCE UTTERANCE",
) -> A2tKbRow:
    return A2tKbRow(
        unit_id=f"tier1_direct:{index:06d}",
        tier="tier1_direct",
        query_idx=index,
        text=private,
        domain="private",
        category="private",
        tool_id=index,
        tool_name=tool,
        arg_signature=tuple(sorted(key for key, _value in pairs)),
        arg_pairs=tuple(sorted(pairs)),
        call_render=f"PRIVATE CALL {tool}",
        extra_call_names=(),
        call_count=1,
        sample_ids=(f"tier1_direct:PRIVATE_{index:06d}",),
        item_ids=(index,),
        media_relpath_by_sample_id={},
        speaker_ids=("PRIVATE SPEAKER",),
    )


def _compatibility_world():
    registry = (
        _registry_row("controlPlayback", "controlPlayback(action: MediaAction)"),
        _registry_row(
            "setAdaptiveLighting",
            "setAdaptiveLighting(deviceId: String, enabled: Boolean)",
        ),
        _registry_row(
            "setValetMode", "setValetMode(enabled: Boolean, pin: Int?)"
        ),
        _registry_row("setHapticStrength", "setHapticStrength(level: Int)"),
        _registry_row("startCleaning", "startCleaning(deviceId: String)"),
    )
    rows = (
        _row(
            1,
            "controlPlayback",
            (("action", "Play"), ("deviceId", "PRIVATE-DEVICE-A")),
        ),
        _row(
            2,
            "controlPlayback",
            (("action", "Pause"), ("deviceId", "PRIVATE-DEVICE-B")),
        ),
        _row(
            3,
            "setAdaptiveLighting",
            (("deviceId", "PRIVATE-LIGHT-A"), ("enabled", "true")),
        ),
        _row(
            4,
            "setAdaptiveLighting",
            (("deviceId", "PRIVATE-LIGHT-B"), ("enabled", "false")),
        ),
        _row(5, "setValetMode", (("enabled", "true"), ("pin", "null"))),
        _row(6, "setValetMode", (("enabled", "false"), ("pin", "null"))),
        _row(
            7,
            "setHapticStrength",
            (("strength", "PRIVATE-ANOMALY"),),
        ),
        _row(
            8,
            "startCleaning",
            (("deviceId", "PRIVATE-CLEANER-A"), ("zones:[", "PRIVATE-ZONE")),
        ),
        _row(
            9,
            "startCleaning",
            (("deviceId", "PRIVATE-CLEANER-B"), ("zones:[", "PRIVATE-ZONE")),
        ),
    )
    return registry, rows


def test_compatibility_derivation_is_aggregate_supported_structured_and_deterministic() -> None:
    builder = _builder()
    registry, rows = _compatibility_world()

    first, report = builder.derive_compatibility_rules(registry, rows)
    second, reversed_report = builder.derive_compatibility_rules(
        tuple(reversed(registry)), tuple(reversed(rows))
    )

    assert first == second
    assert report == reversed_report
    by_identity = {
        (rule.tool_name, rule.legal_argument_key_set): rule for rule in first
    }
    playback = by_identity[("controlPlayback", ("action", "deviceId"))]
    adaptive = by_identity[
        ("setAdaptiveLighting", ("deviceId", "enabled"))
    ]
    valet = by_identity[("setValetMode", ("enabled", "pin"))]
    assert playback.value_forms == (("deviceId", "string"),)
    assert playback.construction_support_count == 2
    assert adaptive.value_forms == (("enabled", "boolean-string"),)
    assert valet.value_forms == (
        ("enabled", "boolean-string"),
        ("pin", "nullable-string"),
    )
    assert all(rule.construction_support_count >= 2 for rule in first)
    assert not any(rule.tool_name == "setHapticStrength" for rule in first)
    assert not any(rule.tool_name == "startCleaning" for rule in first)
    rendered = json.dumps([rule.__dict__ for rule in first], sort_keys=True)
    assert "PRIVATE" not in rendered
    assert report["concrete_argument_values_rendered"] == 0
    assert report["singleton_skeletons_excluded"] >= 1
    assert report["malformed_key_skeletons_excluded"] >= 1


def test_build_from_partition_covers_152_tools_and_never_renders_private_fields() -> None:
    builder = _builder()
    relevant_registry, rows = _compatibility_world()
    fillers = tuple(
        _registry_row(
            f"syntheticTool{index:03d}", f"syntheticTool{index:03d}()"
        )
        for index in range(147)
    )
    registry = (*relevant_registry, *fillers)

    corpus, report = builder.build_from_partition(registry, rows)

    assert corpus.report["registry_tool_count"] == 152
    assert corpus.report["tool_card_count"] == 152
    assert corpus.text.isascii()
    assert report["deterministic_rebuild_equal"] is True
    assert report["construction_argument_pattern_family_count"] == 5
    assert report["construction_argument_key_count"] == 6
    for private in (
        "PRIVATE SOURCE UTTERANCE",
        "PRIVATE-DEVICE-A",
        "PRIVATE CALL",
        "PRIVATE_000001",
        "PRIVATE SPEAKER",
        "PRIVATE-ANOMALY",
    ):
        assert private not in corpus.text


def test_null_compatibility_requires_a_public_optional_argument() -> None:
    builder = _builder()
    registry = (
        _registry_row("optionalTool", "optionalTool(pin: Int?)"),
        _registry_row("requiredTool", "requiredTool(mode: Mode)"),
    )
    rows = (
        _row(1, "optionalTool", (("pin", "null"),)),
        _row(2, "optionalTool", (("pin", "null"),)),
        _row(3, "requiredTool", (("mode", "null"),)),
        _row(4, "requiredTool", (("mode", "null"),)),
    )

    rules, _report = builder.derive_compatibility_rules(registry, rows)

    assert rules == (
        builder.CompatibilityRule(
            tool_name="optionalTool",
            legal_argument_key_set=("pin",),
            value_forms=(("pin", "nullable-string"),),
            construction_support_count=2,
        ),
    )


def test_null_compatibility_does_not_override_a_public_constraint() -> None:
    builder = _builder()
    registry = (
        {
            **_registry_row("constrainedTool", "constrainedTool(pin: Int?)"),
            "argument_constraints": "pin: [0000-9999]",
        },
    )
    rows = (
        _row(1, "constrainedTool", (("pin", "null"),)),
        _row(2, "constrainedTool", (("pin", "null"),)),
    )

    rules, report = builder.derive_compatibility_rules(registry, rows)

    assert rules == ()
    assert report["constrained_nullable_forms_excluded"] == 1


def test_main_writes_only_explicit_outputs(monkeypatch, tmp_path: Path) -> None:
    builder = _builder()
    corpus_path = tmp_path / "corpus.txt"
    receipt_path = tmp_path / "receipt.json"
    receipt = {
        "schema": "test-receipt",
        "contacts": {"model": 0, "network": 0},
    }
    monkeypatch.setattr(builder, "run_build", lambda _root: ("ASCII CORPUS\n", receipt))
    monkeypatch.setattr(builder, "data_root", lambda: Path("/fixed/data"))

    assert (
        builder.main(
            [
                "--corpus-output",
                str(corpus_path),
                "--receipt-output",
                str(receipt_path),
            ]
        )
        == 0
    )
    assert corpus_path.read_text(encoding="utf-8") == "ASCII CORPUS\n"
    assert json.loads(receipt_path.read_text(encoding="utf-8")) == receipt


def test_run_build_records_the_hash_pinned_model_free_build(monkeypatch) -> None:
    builder = _builder()
    registry = tuple(
        _registry_row(f"syntheticTool{index:03d}", f"syntheticTool{index:03d}()")
        for index in range(152)
    )
    construction = (_row(1, "syntheticTool000", ()),)
    partition = SimpleNamespace(
        construction=construction,
        eval_sample_ids=("held-out-evaluation",),
        policy_id="synthetic-policy",
        seed=builder.PARTITION_SEED,
        split_identity_hash=lambda: builder.PROPOSED_EVAL_IDENTITY,
    )
    report = {
        "registry_tool_count": 152,
        "tool_card_count": 152,
        "task_card_count": 4,
        "examples_validated": True,
        "ascii_only": True,
        "source_utterances_rendered": 0,
        "reference_transcripts_rendered": 0,
        "source_argument_values_rendered": 0,
        "gold_values_rendered": 0,
        "source_sample_ids_rendered": 0,
        "evaluation_samples_consumed": 0,
    }
    corpus = SimpleNamespace(text="ASCII\n", sha256="f" * 64, report=report)
    audit = {
        "deterministic_rebuild_equal": True,
        "construction_argument_pattern_family_count": 354,
        "construction_argument_key_count": 85,
        "safe_construction_row_count": 1,
        "excluded_construction_row_count": 0,
        "compatibility": {
            "minimum_support": 2,
            "concrete_argument_values_rendered": 0,
        },
    }
    monkeypatch.setattr(builder, "require_clean_study_repo", lambda _repo: "abc123")
    monkeypatch.setattr(builder, "arm_offline_guard", lambda: SimpleNamespace(count=0))
    monkeypatch.setattr(
        builder,
        "_sha256_file",
        lambda path: (
            builder.PARTITION_PROPOSAL_SHA256
            if path == builder.PARTITION_PROPOSAL
            else builder.REGISTRY_SHA256
            if path.name == "tools_registry.csv"
            else "b" * 64
        ),
    )
    monkeypatch.setattr(builder, "load_lock", lambda _path: object())
    monkeypatch.setattr(builder, "umbrella_lock_path", lambda _repo: Path("lock"))
    monkeypatch.setattr(builder, "asset_dir", lambda _lock, _name, root: root)
    monkeypatch.setattr(builder, "load_tool_registry", lambda _lock, _root: registry)
    monkeypatch.setattr(
        builder,
        "a2t_pool_rows",
        lambda _lock, _root: (
            construction,
            {"pool_items": 1, "pool_units": 1, "usable_units": 1},
        ),
    )
    monkeypatch.setattr(builder, "exposed_sample_ids", lambda _repo: frozenset())
    monkeypatch.setattr(
        builder, "propose_partition", lambda _rows, _exposed, seed: partition
    )
    monkeypatch.setattr(builder, "build_from_partition", lambda _registry, _rows: (corpus, audit))

    text, receipt = builder.run_build(Path("synthetic-data"))

    assert text == "ASCII\n"
    assert receipt["study_commit"] == "abc123"
    assert receipt["corpus"]["sha256"] == "f" * 64
    assert receipt["partition"]["construction_forbidden_intersection_count"] == 0
    assert set(receipt["contacts"].values()) == {0}


def test_committed_corpus_and_receipt_preserve_model_free_static_gates() -> None:
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    corpus = CORPUS.read_bytes()

    assert receipt["execution_profile"] == "model-free-check"
    assert set(receipt["contacts"].values()) == {0}
    assert receipt["offline_guard"]["outbound_connection_attempts"] == 0
    assert receipt["partition"]["construction_forbidden_intersection_count"] == 0
    assert receipt["corpus"]["deterministic_rebuild_equal"] is True
    assert receipt["corpus"]["sha256"] == hashlib.sha256(corpus).hexdigest()
    report = receipt["corpus"]["report"]
    assert report["registry_tool_count"] == 152
    assert receipt["construction_summary"]["argument_pattern_family_count"] == 354
    assert receipt["construction_summary"]["argument_key_count"] == 85
    assert report["ascii_only"] is True
    assert report["source_utterances_rendered"] == 0
    assert report["source_argument_values_rendered"] == 0
    assert report["gold_values_rendered"] == 0
    assert report["source_sample_ids_rendered"] == 0
    assert receipt["compatibility"]["minimum_support"] == 2
    assert receipt["compatibility"]["concrete_argument_values_rendered"] == 0
