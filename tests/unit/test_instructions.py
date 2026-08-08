"""Task-instruction resolution seam (P1 scaffold).

A baseline fragment supplies EITHER a literal ``task_instruction`` (every
pre-existing fragment, byte-identical behavior) OR a frozen template
reference (``task_instruction_template`` under ``configs/`` +
``task_instruction_fill`` naming a registered ``INSTRUCTION_FILLS`` entry)
whose single supported ``{tool_schemas}`` placeholder is rendered at run
time from pinned carrier data — never committed into Git.
"""

import pytest

from speech_aware_evidence_acquisition.core.base import INSTRUCTION_FILLS, CoreError
from speech_aware_evidence_acquisition.core.instructions import (
    TOOL_SCHEMAS_PLACEHOLDER,
    resolve_task_instruction,
)
from speech_aware_evidence_acquisition.data.lock import load_lock


def test_literal_task_instruction_passes_through(tmp_path):
    values = {"task_instruction": "Transcribe."}
    assert resolve_task_instruction(values, tmp_path, {}, tmp_path) == "Transcribe."


def test_literal_and_template_together_are_refused(tmp_path):
    values = {"task_instruction": "x", "task_instruction_template": "probes/t.txt"}
    with pytest.raises(CoreError, match="both"):
        resolve_task_instruction(values, tmp_path, {}, tmp_path)


def test_neither_literal_nor_template_is_refused(tmp_path):
    with pytest.raises(CoreError, match="task_instruction"):
        resolve_task_instruction({}, tmp_path, {}, tmp_path)


def test_template_renders_the_registered_fill(audio2tool_world):
    lock = load_lock(audio2tool_world.lock_path)
    values = {
        "task_instruction_template": audio2tool_world.template_relpath,
        "task_instruction_fill": "audio2tool-tool-schemas",
    }
    rendered = resolve_task_instruction(
        values, audio2tool_world.repo_root, lock, audio2tool_world.data_root
    )
    assert TOOL_SCHEMAS_PLACEHOLDER not in rendered
    assert '"tool_name": "setLighting"' in rendered
    assert '"tool_name": "setSecurityMode"' in rendered
    assert rendered.startswith("You control tools.")


def test_template_without_fill_is_refused(audio2tool_world):
    values = {"task_instruction_template": audio2tool_world.template_relpath}
    with pytest.raises(CoreError, match="task_instruction_fill"):
        resolve_task_instruction(
            values, audio2tool_world.repo_root, {}, audio2tool_world.data_root
        )


def test_template_missing_placeholder_is_refused(audio2tool_world, tmp_path):
    template = audio2tool_world.repo_root / "configs" / "probes" / "noslot.txt"
    template.write_text("no placeholder here\n", encoding="utf-8")
    lock = load_lock(audio2tool_world.lock_path)
    values = {
        "task_instruction_template": "probes/noslot.txt",
        "task_instruction_fill": "audio2tool-tool-schemas",
    }
    with pytest.raises(CoreError, match="placeholder"):
        resolve_task_instruction(
            values, audio2tool_world.repo_root, lock, audio2tool_world.data_root
        )


def test_template_path_traversal_is_refused(audio2tool_world):
    values = {
        "task_instruction_template": "../secrets.txt",
        "task_instruction_fill": "audio2tool-tool-schemas",
    }
    with pytest.raises(CoreError, match="template"):
        resolve_task_instruction(
            values, audio2tool_world.repo_root, {}, audio2tool_world.data_root
        )


def test_missing_template_file_is_refused(audio2tool_world):
    values = {
        "task_instruction_template": "probes/absent.txt",
        "task_instruction_fill": "audio2tool-tool-schemas",
    }
    with pytest.raises(CoreError, match="template"):
        resolve_task_instruction(
            values, audio2tool_world.repo_root, {}, audio2tool_world.data_root
        )


def test_unknown_fill_name_is_refused(audio2tool_world):
    values = {
        "task_instruction_template": audio2tool_world.template_relpath,
        "task_instruction_fill": "no-such-fill",
    }
    with pytest.raises(CoreError, match="no-such-fill"):
        resolve_task_instruction(
            values, audio2tool_world.repo_root, {}, audio2tool_world.data_root
        )


def test_audio2tool_fill_is_registered():
    assert "audio2tool-tool-schemas" in INSTRUCTION_FILLS.names()
