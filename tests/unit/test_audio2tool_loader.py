"""Audio2Tool carrier loader (P1 scaffold): frozen-receipt-scoped, fail-closed.

The loader's sample universe IS the frozen probe receipt: it never hydrates
manifest rows outside it (the fixture proves this by giving a non-receipt row
a wav path that does not exist on disk). Runtime surface is the standard
five-field ``SampleRef``; gold (expected tool calls) is exposed ONLY through
the separate scorer-side ``load_expected_calls``.
"""

import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.data.audio2tool import (
    AUDIO2TOOL_LOCK_KEY,
    load_audio2tool,
    load_expected_calls,
    load_tool_registry,
    load_tool_registry_with_sha256,
    render_registry_row,
    render_tool_schemas,
)
from speech_aware_evidence_acquisition.data.loader import LoaderError, SampleRef
from speech_aware_evidence_acquisition.data.lock import AssetResolutionError, load_lock
from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import ToolCall


def _load(world):
    lock = load_lock(world.lock_path)
    return load_audio2tool(lock, world.data_root, repo_root=world.repo_root)


def test_loads_exactly_the_receipt_items_sorted(audio2tool_world):
    samples = _load(audio2tool_world)
    assert [sample.sample_id for sample in samples] == [
        "tier1_direct:000001",
        "tier3_multi_intent:000004",
        "tier7_multiturn:000009",
    ]
    assert all(isinstance(sample, SampleRef) for sample in samples)
    assert all(sample.carrier_lock_key == AUDIO2TOOL_LOCK_KEY for sample in samples)


def test_media_facts_come_from_the_manifest_and_wav_header(audio2tool_world):
    by_id = {sample.sample_id: sample for sample in _load(audio2tool_world)}
    tier1 = by_id["tier1_direct:000001"]
    assert tier1.media_relpath == (
        "datasets/audio2tool/public/tier1_direct_audios/query_00001/turn.wav"
    )
    assert tier1.audio_seconds == 0.5
    assert tier1.sample_rate_hz == 16000
    tier3 = by_id["tier3_multi_intent:000004"]
    assert tier3.sample_rate_hz == 22050
    assert tier3.audio_seconds == 1.25


def test_tier7_uses_the_final_user_turn(audio2tool_world):
    by_id = {sample.sample_id: sample for sample in _load(audio2tool_world)}
    tier7 = by_id["tier7_multiturn:000009"]
    assert tier7.media_relpath == (
        "datasets/audio2tool/public/tier7_multiturn_audios/query_00009/turn_02_user.wav"
    )
    assert tier7.audio_seconds == 6.7
    assert tier7.sample_rate_hz == 16000


def test_runtime_view_passes_the_information_boundary(audio2tool_world):
    sample = _load(audio2tool_world)[0]
    view = sample.runtime_view()
    assert view["speech_ref"] == "audio2tool/tier1_direct:000001"
    assert set(view) == {
        "carrier_lock_key",
        "sample_id",
        "speech_ref",
        "media_relpath",
        "audio_seconds",
        "sample_rate_hz",
    }


def test_receipt_hash_mismatch_fails_closed(audio2tool_world):
    audio2tool_world.write_receipt(split_identity_hash="f" * 64)
    with pytest.raises(LoaderError, match="split_identity_hash"):
        _load(audio2tool_world)


def test_receipt_item_missing_from_manifest_fails_closed(audio2tool_world):
    items = audio2tool_world.receipt_items()
    items.append(
        {"id": 999, "key": "audio2tool:tier1_direct:000999", "query_idx": 1, "tier": "tier1_direct"}
    )
    audio2tool_world.write_receipt(items=items)
    with pytest.raises(LoaderError, match="000999|999"):
        _load(audio2tool_world)


def test_receipt_query_idx_drift_fails_closed(audio2tool_world):
    items = audio2tool_world.receipt_items()
    items[0]["query_idx"] = 555
    audio2tool_world.write_receipt(items=items)
    with pytest.raises(LoaderError, match="query_idx"):
        _load(audio2tool_world)


def test_missing_wav_fails_closed(audio2tool_world):
    wav = (
        audio2tool_world.public
        / "tier1_direct_audios"
        / "query_00001"
        / "turn.wav"
    )
    wav.unlink()
    with pytest.raises(LoaderError, match="tier1_direct:000001"):
        _load(audio2tool_world)


def test_confirmatory_receipt_role_fails_closed(audio2tool_world):
    audio2tool_world.write_receipt(split_role="confirmatory")
    with pytest.raises(LoaderError, match="split_role"):
        _load(audio2tool_world)


def test_traversal_audio_path_fails_closed(audio2tool_world):
    manifest = audio2tool_world.public / "tier1_direct_data" / "tier1_direct.json"
    entries = json.loads(manifest.read_text(encoding="utf-8"))
    entries[0]["path"] = "../../../evil.wav"
    manifest.write_text(json.dumps(entries), encoding="utf-8")
    with pytest.raises(LoaderError, match="path"):
        _load(audio2tool_world)


def test_tier7_final_turn_must_be_a_user_turn(audio2tool_world):
    manifest = audio2tool_world.public / "tier7_multiturn_data" / "tier7_multiturn.json"
    entries = json.loads(manifest.read_text(encoding="utf-8"))
    entries[0]["chat_history"][-1]["role"] = "agent"
    manifest.write_text(json.dumps(entries), encoding="utf-8")
    with pytest.raises(LoaderError, match="user"):
        _load(audio2tool_world)


def test_missing_lock_entry_is_the_only_missing_piece(audio2tool_world):
    """KNOWN BLOCKER shape: with no ``audio2tool`` lock entry the loader fails
    closed at lock resolution — everything else in this module is complete."""

    lock = {"asset_catalog": [], "models": []}
    with pytest.raises(AssetResolutionError, match="audio2tool"):
        load_audio2tool(lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root)


def test_expected_calls_are_scorer_side_and_parsed(audio2tool_world):
    lock = load_lock(audio2tool_world.lock_path)
    expected = load_expected_calls(
        lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root
    )
    assert set(expected) == {
        "tier1_direct:000001",
        "tier3_multi_intent:000004",
        "tier7_multiturn:000009",
    }
    assert expected["tier1_direct:000001"] == (ToolCall("setLighting", {}),)
    tier3 = expected["tier3_multi_intent:000004"]
    assert [call.name for call in tier3] == [
        "setSecurityMode",
        "setTargetTemperature",
        "setColor",
        "calibrateThermostat",
    ]
    assert tier3[0].arguments == {"mode": "Armed_Away", "level": 2}
    (tier7,) = expected["tier7_multiturn:000009"][:1]
    assert tier7 == ToolCall("setAlarm", {"time": "06:30", "repeat": ["Weekdays"]})


def test_render_tool_schemas_is_sorted_and_deterministic(audio2tool_world):
    lock = load_lock(audio2tool_world.lock_path)
    rendered = render_tool_schemas(lock, audio2tool_world.data_root)
    lines = rendered.split("\n")
    assert len(lines) == 2
    first, second = (json.loads(line) for line in lines)
    assert first["tool_name"] == "setLighting"  # tool_id 2 sorts before 10
    assert second["tool_name"] == "setSecurityMode"
    assert second["argument_constraints"] == "mode: [Home, Armed_Away]"
    assert rendered == render_tool_schemas(lock, audio2tool_world.data_root)


def test_registry_rows_and_sha_are_bound_to_the_same_raw_bytes(audio2tool_world, monkeypatch):
    lock = load_lock(audio2tool_world.lock_path)
    registry_path = audio2tool_world.carrier_dir / "tools_registry.csv"
    original_bytes = registry_path.read_bytes()
    replacement = original_bytes.replace(b"setLighting", b"setBrightness")
    real_read_bytes = type(registry_path).read_bytes
    reads = 0

    def read_then_replace(path):
        nonlocal reads
        raw = real_read_bytes(path)
        if path == registry_path:
            reads += 1
            registry_path.write_bytes(replacement)
        return raw

    monkeypatch.setattr(type(registry_path), "read_bytes", read_then_replace)
    rows, source_sha256 = load_tool_registry_with_sha256(
        lock, audio2tool_world.data_root
    )

    assert reads == 1
    assert tuple(row["tool_name"] for row in rows) == (
        "setLighting",
        "setSecurityMode",
    )
    assert source_sha256 == hashlib.sha256(original_bytes).hexdigest()


def test_render_tool_schemas_missing_registry_fails_closed(audio2tool_world):
    (audio2tool_world.carrier_dir / "tools_registry.csv").unlink()
    lock = load_lock(audio2tool_world.lock_path)
    with pytest.raises(LoaderError, match="tools_registry"):
        render_tool_schemas(lock, audio2tool_world.data_root)


def test_render_registry_row_strip_defaults_removes_only_that_key(audio2tool_world):
    """Stage-2b B1's own nodefaults rendering (docs/readiness/2026-08-18-
    pa2t-stage2b-preregistration-REGISTERED.md section 1, Q-A): the
    ``argument_defaults`` KEY is absent, every other key/value and the JSON
    formatting convention stay byte-identical to the normal rendering."""

    lock = load_lock(audio2tool_world.lock_path)
    rows = load_tool_registry(lock, audio2tool_world.data_root)
    (setlighting_row,) = (row for row in rows if row["tool_name"] == "setLighting")
    assert setlighting_row["argument_defaults"] == "deviceId='light_1'"  # non-empty: a real test

    normal = render_registry_row(setlighting_row)
    stripped = render_registry_row(setlighting_row, strip_defaults=True)
    assert stripped != normal

    normal_obj = json.loads(normal)
    stripped_obj = json.loads(stripped)
    assert "argument_defaults" in normal_obj
    assert "argument_defaults" not in stripped_obj
    assert {k: v for k, v in normal_obj.items() if k != "argument_defaults"} == stripped_obj

    # Byte-identical formatting convention (sort_keys, ensure_ascii, no
    # trailing whitespace) -- not just equal parsed content.
    assert stripped == json.dumps(
        {k: v for k, v in dict(setlighting_row).items() if k != "argument_defaults"},
        ensure_ascii=False,
        sort_keys=True,
    )


def test_render_registry_row_strip_defaults_is_a_noop_when_already_absent():
    row = {
        "tool_id": "1",
        "domain": "d",
        "category": "c",
        "tool_name": "t",
        "signature": "t()",
        "description": "desc",
        "argument_defaults": "",
        "argument_constraints": "",
    }
    assert render_registry_row(row, strip_defaults=True) == json.dumps(
        {k: v for k, v in row.items() if k != "argument_defaults"},
        ensure_ascii=False,
        sort_keys=True,
    )


def test_p1_config_fragments_compose_against_the_real_repo():
    """The committed four-fragment composition for P1 is well-formed: disjoint
    keys, the frozen template+fill pair instead of a literal instruction, and
    the frozen probe split name. No data root and no lock is touched here."""

    from speech_aware_evidence_acquisition.core.config import compose
    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    composed = compose(
        REPO_ROOT,
        "qwen3-omni-llamacpp",
        "audio2tool-r1-sample400",
        "a2t-direct",
        "r1-audio2tool",
    )
    values = composed.values
    assert values["carrier_lock_key"] == "audio2tool"
    assert values["split_name"] == "r1-audio2tool-sample"
    assert values["arm"] == "bare-core"
    assert values["scorers"] == ["a2t-toolcall", "cost"]
    assert "task_instruction" not in values
    assert values["task_instruction_template"] == "probes/r1_audio2tool_direct.txt"
    assert values["task_instruction_fill"] == "audio2tool-tool-schemas"
    assert values["execution_profile"] == "baseline-reproduction"
    # The frozen template really is the manifest-hashed one and carries the
    # placeholder the fill renders.
    template = REPO_ROOT / "configs" / values["task_instruction_template"]
    assert "{tool_schemas}" in template.read_text(encoding="utf-8")
