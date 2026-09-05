"""A2T-ORG-1: the domain-grouped tool registry, and the fill that renders it.

One factor separates the ORG-1 cell from the sealed official-protocol cells:
which of the pinned release's TWO registry renderers builds the tool block.
``format_tools_compact`` (already ported as ``render_registry_compact``)
drops the registry's ``domain`` and ``category`` columns entirely;
``format_tools_for_prompt(tools, include_constraints=False)`` groups the same
152 rows by domain under an upper-cased header. This file pins that second
port.

Two kinds of assertion, deliberately separate, mirroring
``test_audio2tool_official_scorer.py``:

1. BYTE EQUALITY against the release's own function, imported from the
   pinned clone (``$SPEECHRL_DATA_DIR/repos/audio2tool``) and executed over
   the same ``tools_registry.csv``. This is the assertion that makes the port
   a port; it SKIPS with a stated reason where the clone or the controlled
   data root is absent, because a machine without them cannot be asked to
   prove a fact about a repository it does not have.

2. SHAPE, on the synthetic ``audio2tool_world`` registry, which always runs:
   the exact rendered bytes, the sorted-domain / sorted-name order, the
   withheld constraints, the leading newline and the absent trailing one.

Plus the config identity the flight binds: the fill registration, the probe
template's bytes and its manifest pin, and the baseline fragment's fields.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.data.lock import load_lock

REPO_ROOT_PATH = Path(__file__).resolve().parents[2]
GROUPED_TEMPLATE = REPO_ROOT_PATH / "configs" / "probes" / "r1_audio2tool_official_grouped.txt"
OFFICIAL_TEMPLATE = REPO_ROOT_PATH / "configs" / "probes" / "r1_audio2tool_official.txt"
BASELINE_FRAGMENT = (
    REPO_ROOT_PATH / "configs" / "baseline" / "a2t-org1-domain-grouped.json"
)
CLONE_RELPATH = Path("repos") / "audio2tool"


def _clone_schema_module() -> Path | None:
    """The pinned clone's ``utils/tools_schema.py``, or ``None`` if absent.

    Stdlib-only upstream (csv, pathlib, typing), so importing it needs no
    torch and no installed package -- it is a genuinely independent rendering
    of the same CSV rather than a re-run of this repository's fill.
    """

    data_root = os.environ.get("SPEECHRL_DATA_DIR")
    if not data_root:
        return None
    candidate = (
        Path(data_root) / CLONE_RELPATH / "audio_benchmark" / "utils" / "tools_schema.py"
    )
    return candidate if candidate.is_file() else None


def _real_registry_csv() -> Path | None:
    """The locked ``tools_registry.csv``, or ``None`` where it is not on disk."""

    from speech_aware_evidence_acquisition.data.lock import (
        AssetResolutionError,
        asset_dir,
        data_root,
        umbrella_lock_path,
    )

    try:
        lock = load_lock(umbrella_lock_path(REPO_ROOT_PATH))
        path = asset_dir(lock, "audio2tool", data_root()) / "tools_registry.csv"
    except (AssetResolutionError, OSError, ValueError):
        return None
    return path if path.is_file() else None


# ---------------------------------------------------------------------------
# 1. Byte equality with the release's own renderer
# ---------------------------------------------------------------------------


def test_grouped_fill_is_byte_identical_to_the_release_renderer():
    schema_module = _clone_schema_module()
    if schema_module is None:
        pytest.skip(
            "the pinned Audio2Tool clone is absent on this machine "
            "($SPEECHRL_DATA_DIR/repos/audio2tool/audio_benchmark/utils/tools_schema.py); "
            "rebuild it with the command in "
            "docs/receipts/environments/audio2tool-official-code.json"
        )
    csv_path = _real_registry_csv()
    if csv_path is None:
        pytest.skip(
            "the locked Audio2Tool tools_registry.csv is not materialized under "
            "$SPEECHRL_DATA_DIR on this machine; run the umbrella fetch scripts"
        )

    from speech_aware_evidence_acquisition.data.lock import (
        data_root,
        umbrella_lock_path,
    )
    from speech_aware_evidence_acquisition.data.audio2tool_tools import (
        render_registry_grouped,
    )

    spec = importlib.util.spec_from_file_location(
        "_a2t_official_tools_schema_org1", schema_module
    )
    assert spec is not None and spec.loader is not None
    upstream = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(upstream)

    expected = upstream.format_tools_for_prompt(
        upstream.load_tools_from_csv(str(csv_path)), include_constraints=False
    )
    rendered = render_registry_grouped(
        load_lock(umbrella_lock_path(REPO_ROOT_PATH)), data_root()
    )
    assert rendered == expected
    # The withheld factor: constraints never appear, even though the release
    # function can emit them.
    assert "Constraints:" not in rendered
    with_constraints = upstream.format_tools_for_prompt(
        upstream.load_tools_from_csv(str(csv_path)), include_constraints=True
    )
    assert with_constraints != expected


# ---------------------------------------------------------------------------
# 2. Shape, on the synthetic registry (always runs)
# ---------------------------------------------------------------------------


def test_grouped_fill_renders_the_upstream_shape(audio2tool_world):
    from speech_aware_evidence_acquisition.core.base import INSTRUCTION_FILLS
    from speech_aware_evidence_acquisition.data.audio2tool_tools import (
        render_registry_compact,
        render_registry_grouped,
    )

    assert "audio2tool-registry-grouped" in INSTRUCTION_FILLS.names()
    # The three pre-existing fills stay registered and are not replaced.
    assert "audio2tool-registry-compact" in INSTRUCTION_FILLS.names()
    assert "audio2tool-tool-schemas" in INSTRUCTION_FILLS.names()
    assert INSTRUCTION_FILLS.resolve("audio2tool-registry-grouped") is (
        render_registry_grouped
    )

    lock = load_lock(audio2tool_world.lock_path)
    rendered = render_registry_grouped(lock, audio2tool_world.data_root)
    # Domain groups in sorted-domain order; within a group, sorted by
    # tool_name (setLighting before setSecurityMode, though its tool_id is
    # higher-sorting the other way); header upper-cased with underscores
    # replaced by spaces; a leading newline; no constraints; no trailing
    # newline.
    assert rendered == (
        "\n## SMART HOME"
        "\n\n### setLighting(deviceId: String)"
        "\nTurns a light on."
        "\n\n### setSecurityMode(mode: Mode)"
        "\nSets the security mode."
    )
    assert rendered.startswith("\n## ")
    assert not rendered.endswith("\n")
    assert "Constraints:" not in rendered
    # It is a DIFFERENT organization of the same rows, not the compact one.
    compact = render_registry_compact(lock, audio2tool_world.data_root)
    assert rendered != compact
    # Same rows, same signatures, same descriptions -- only the organization
    # differs, and only the grouped form carries the domain.
    from speech_aware_evidence_acquisition.data.audio2tool import load_tool_registry

    for row in load_tool_registry(lock, audio2tool_world.data_root):
        assert "- %s: %s" % (row["signature"], row["description"]) in compact
        assert "### %s\n%s" % (row["signature"], row["description"]) in rendered
        assert row["domain"] not in compact.lower()
    assert "smart home" in rendered.lower()


def test_grouped_fill_is_reachable_through_resolve_task_instruction(audio2tool_world):
    from speech_aware_evidence_acquisition.core.instructions import (
        resolve_task_instruction,
    )
    from speech_aware_evidence_acquisition.data.audio2tool_tools import (
        render_registry_grouped,
    )

    lock = load_lock(audio2tool_world.lock_path)
    values = {
        "task_instruction_template": "probes/r1_audio2tool_official_grouped.txt",
        "task_instruction_fill": "audio2tool-registry-grouped",
    }
    rendered = resolve_task_instruction(
        values, REPO_ROOT_PATH, lock, audio2tool_world.data_root
    )
    fill = render_registry_grouped(lock, audio2tool_world.data_root)
    assert rendered == (
        GROUPED_TEMPLATE.read_text(encoding="utf-8").replace("{tool_schemas}", fill)
    )
    # The envelope is the release's own: system prompt, blank line, the fixed
    # header line, then the block -- whose own leading newline is what puts a
    # blank line before the first domain header.
    assert "\n\n## Available Tools:\n\n## " in rendered


# ---------------------------------------------------------------------------
# 3. The config identity the flight binds
# ---------------------------------------------------------------------------


def test_grouped_template_bytes_equal_the_official_template():
    data = GROUPED_TEMPLATE.read_bytes()
    assert b"\r\n" not in data
    # Only the FILL differs between ORG-1 and the sealed official cells; the
    # envelope is the same released system message shape, byte for byte.
    assert data == OFFICIAL_TEMPLATE.read_bytes()
    assert not data.decode("utf-8").endswith("\n")


def test_grouped_template_is_pinned_in_the_probe_manifest():
    manifest = json.loads(
        (REPO_ROOT_PATH / "configs" / "probes" / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    entry = manifest["templates"]["r1_audio2tool_official_grouped.txt"]
    assert entry["sha256"] == hashlib.sha256(GROUPED_TEMPLATE.read_bytes()).hexdigest()
    probe = manifest["probes"]["R1-audio2tool-org1-domain-grouped"]
    assert probe["arms"]["direct"] == ["r1_audio2tool_official_grouped.txt"]
    assert probe["profile"] == "baseline-reproduction"
    # The templates the sealed cells flew are untouched.
    assert "r1_audio2tool_official.txt" in manifest["templates"]
    assert "r1_audio2tool_direct.txt" in manifest["templates"]


def test_org1_baseline_fragment_varies_exactly_one_factor():
    fragment = json.loads(BASELINE_FRAGMENT.read_text(encoding="utf-8"))
    official = json.loads(
        (
            REPO_ROOT_PATH / "configs" / "baseline" / "a2t-direct-official-protocol.json"
        ).read_text(encoding="utf-8")
    )
    assert fragment["arm"] == "bare-core"
    assert fragment["rails_arms"] == ["zero-supply"]
    assert fragment["scorers"] == [
        "a2t-toolcall-official",
        "a2t-toolcall-v2",
        "a2t-toolcall",
        "cost",
    ]
    assert (
        fragment["task_instruction_template"] == "probes/r1_audio2tool_official_grouped.txt"
    )
    assert fragment["task_instruction_fill"] == "audio2tool-registry-grouped"
    assert fragment["task_instruction_template_active"] is True
    # The user turn is the official fragment's, byte for byte.
    assert fragment["user_turn_text"] == official["user_turn_text"]
    assert fragment["user_turn_text"] == "Convert this voice command to a tool call."
    assert fragment["user_turn_audio_first"] == official["user_turn_audio_first"]
    assert fragment["policy"] == official["policy"]
    assert fragment["evidence_source"] == official["evidence_source"]
    assert fragment["evidence_mismatch"] == official["evidence_mismatch"]
    # No native tools list: the pinned adapter never sends one.
    assert "tool_schema_fill" not in fragment
    # Exactly one wire-affecting field differs in VALUE from the official
    # fragment, plus the template PATH -- whose bytes are proved identical by
    # test_grouped_template_bytes_equal_the_official_template, so the rendered
    # difference is the fill and nothing else.
    wire_keys = {
        "arm",
        "policy",
        "evidence_source",
        "evidence_mismatch",
        "rails_arms",
        "scorers",
        "task_instruction_template",
        "task_instruction_fill",
        "task_instruction_template_active",
        "user_turn_text",
        "user_turn_audio_first",
    }
    differing = {key for key in wire_keys if fragment.get(key) != official.get(key)}
    assert differing == {"task_instruction_fill", "task_instruction_template"}
