"""KC-A1's contrast-note artifact and KC-A1c's category-only control.

Two halves. The model-free half pins the construction rule
(``rails.proposer.contrast_note_records``): a note may say nothing the
registry does not already say, and the control is the category word padded to
EXACTLY the note's character count. The registry half -- skipped on a host
without ``tools_registry.csv`` -- resolves the two COMMITTED baseline
fragments the way a flight resolves them and holds the shape the sealed
official-protocol cell was measured with: 152 lines, the published system
sentence untouched, and exactly the LIGHTING target's eight rows changed --
the owner's option B of 2026-09-06, which keeps the rendered block inside the
program's +40-token form cap.
"""

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.instructions import (
    resolve_active_task_instruction,
)
from speech_aware_evidence_acquisition.data.audio2tool_tools import (
    render_registry_compact,
)
from speech_aware_evidence_acquisition.rails.proposer import (
    ProposerError,
    contrast_note_records,
)

REPO = Path(__file__).resolve().parents[2]
#: The spec the COMMITTED fragments were built from: lighting only. The
#: five-target parent stays committed beside it and is what the four unflown
#: clusters return through, so both are read here and the flown one is the
#: subset the artifacts must match.
SPEC = REPO / "configs/knowledge/a2t-kc-a1/targets-lighting-v1.json"
PARENT_SPEC = REPO / "configs/knowledge/a2t-kc-a1/targets-v1.json"
FRAGMENTS = {
    "kc-a1": (REPO / "configs/baseline/a2t-kc-a1-contrast-notes.json", "kc_a1"),
    "kc-a1c": (REPO / "configs/baseline/a2t-kc-a1c-category-only.json", "kc_a1c"),
}
#: The published system prompt's own four sentences, from the frozen template
#: ``configs/probes/r1_audio2tool_official.txt``. A KC-A1 fragment that
#: changed one word of it would no longer be a single-factor cell.
OFFICIAL_SENTENCE = (
    "You are an AI assistant that converts voice commands into tool calls. "
    "Listen to the audio and determine which tool should be called. Output ONLY "
    "the tool call in the format: tool_name(param1=value1, param2=value2). If no "
    "parameters are mentioned, output: tool_name()."
)

ROWS = (
    {
        "tool_name": "setColor",
        "signature": "setColor(deviceId: String, color: HsbColor)",
        "description": "Sets the color of a light.",
        "domain": "smart_home",
        "category": "lighting",
        "argument_constraints": "color: [Hue:0-360]",
        "argument_defaults": "deviceId='light_1'",
    },
    {
        "tool_name": "setAmbientLighting",
        "signature": "setAmbientLighting(color: HexCode)",
        "description": "Sets the interior ambient lighting.",
        "domain": "smart_car",
        "category": "media_cabin",
        "argument_constraints": "",
        "argument_defaults": "color='#0000FF'",
    },
)
TARGETS = {
    "lighting": {
        "setColor": "; smart_home color",
        "setAmbientLighting": "; smart_car cabin",
    }
}


def test_a_note_may_not_say_what_the_registry_does_not():
    with pytest.raises(ProposerError, match="the registry does not"):
        contrast_note_records(
            ROWS,
            {"lighting": {"setColor": "; the warmest bulb"}},
            function_words=["the"],
        )


def test_the_control_is_padded_to_exactly_the_note_length():
    records = contrast_note_records(ROWS, TARGETS, function_words=[])
    by_tool = {record["tool_name"]: record for record in records}
    for record in records:
        assert len(record["control_note"]) == len(record["note"])
        assert record["kc_a1c"] == record["kc_a1"][: -record["note_chars"]] + record[
            "control_note"
        ]
    # an 18-character note takes one " tool" filler and three trailing spaces;
    # a 13-character category leaves room for none.
    assert by_tool["setColor"]["control_note"] == "; lighting tool   "
    assert by_tool["setAmbientLighting"]["control_note"] == "; media_cabin    "
    assert by_tool["setColor"]["kc_a1"] == "Sets the color of a light.; smart_home color"


def test_the_flown_spec_is_the_parents_lighting_target_unchanged():
    """Option B narrows the target LIST and rewrites no note.

    A lighting-only spec that had also reworded a note would make KC-A1 a
    different manipulation from the one MF-1 priced, so the flown spec's one
    target must be the parent's own entry and its rules must be the parent's.
    """

    flown = json.loads(SPEC.read_text(encoding="utf-8"))
    parent = json.loads(PARENT_SPEC.read_text(encoding="utf-8"))
    parent_lighting = [
        target for target in parent["targets"] if target["target_id"] == "lighting"
    ]
    assert flown["targets"] == parent_lighting
    assert len(flown["targets"][0]["tools"]) == 8
    for key in ("schema", "source_receipt", "note_rules", "control_rules", "statements"):
        assert flown[key] == parent[key]
    # the parent keeps all five targets: the four unflown clusters are
    # retained for a later per-cluster cell, not deleted.
    assert len(parent["targets"]) == 5
    assert flown["owner_decision"]["option"] == "B"


def test_a_category_longer_than_its_note_is_refused_rather_than_truncated():
    with pytest.raises(ProposerError, match="cannot be padded down"):
        contrast_note_records(
            ROWS, {"lighting": {"setAmbientLighting": "; car"}}, function_words=[]
        )


# -- the real 152-row registry and the two committed fragments ---------------


def _real_lock_and_root():
    from speech_aware_evidence_acquisition.data.audio2tool import AUDIO2TOOL_LOCK_KEY
    from speech_aware_evidence_acquisition.data.lock import (
        AssetResolutionError,
        asset_dir,
        data_root,
        load_lock,
        umbrella_lock_path,
    )

    try:
        root = data_root()
        lock = load_lock(umbrella_lock_path())
        if not (asset_dir(lock, AUDIO2TOOL_LOCK_KEY, root) / "tools_registry.csv").is_file():
            return None
        return lock, root
    except (AssetResolutionError, OSError):
        return None


_REAL = _real_lock_and_root()


@pytest.mark.skipif(_REAL is None, reason="real audio2tool registry not available")
@pytest.mark.parametrize("arm", sorted(FRAGMENTS))
def test_each_committed_fragment_renders_152_lines_with_its_overrides(arm):
    lock, root = _REAL
    path, key = FRAGMENTS[arm]
    values = json.loads(path.read_text(encoding="utf-8"))
    rendered = resolve_active_task_instruction(values, REPO, lock, root)

    assert rendered.startswith(OFFICIAL_SENTENCE)
    assert "## Available Tools:\n" in rendered
    block = rendered.split("## Available Tools:\n", 1)[1].rstrip("\n").split("\n")
    baseline = render_registry_compact(lock, root).split("\n")
    assert len(block) == 152 == len(baseline)

    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    assert [target["target_id"] for target in spec["targets"]] == ["lighting"]
    expected = {
        tool: body["note"]
        for target in spec["targets"]
        for tool, body in target["tools"].items()
    }
    differing = [index for index in range(152) if block[index] != baseline[index]]
    assert len(differing) == len(expected) == 8
    # the changed rows are the lighting target's own tools and nothing else:
    # the four unflown MF-1 targets keep their released descriptions.
    assert {block[index].split("(", 1)[0][2:] for index in differing} == set(expected)
    for index in differing:
        # every changed line is the baseline line plus this arm's appended
        # text, so the signature half and the released description are intact
        assert block[index].startswith(baseline[index])
        if arm == "kc-a1":
            assert block[index][len(baseline[index]) :] in expected.values()
        else:
            assert block[index][len(baseline[index]) :].startswith("; ")


@pytest.mark.skipif(_REAL is None, reason="real audio2tool registry not available")
def test_the_two_arms_are_length_matched_line_for_line():
    lock, root = _REAL
    blocks = {}
    for arm, (path, _) in FRAGMENTS.items():
        values = json.loads(path.read_text(encoding="utf-8"))
        rendered = resolve_active_task_instruction(values, REPO, lock, root)
        blocks[arm] = rendered.split("## Available Tools:\n", 1)[1].rstrip("\n").split("\n")
    treatment, control = blocks["kc-a1"], blocks["kc-a1c"]
    assert [len(line) for line in treatment] == [len(line) for line in control]
