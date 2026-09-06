"""KC-A1's contrast-note artifact and KC-A1c's category-only control.

Two halves. The model-free half pins the construction rule
(``rails.proposer.contrast_note_records``): a note may say nothing the
registry does not already say, and the control is the category word grown to
EXACTLY the note's size -- in characters by default, and in TOKENS whenever a
counter is injected, which is what the 2026-09-06 owner ruling makes the
flown rule. The registry half -- skipped on a host without
``tools_registry.csv`` -- resolves the two COMMITTED baseline fragments the
way a flight resolves them and holds the shape the sealed official-protocol
cell was measured with: 152 lines, the published system sentence untouched,
and exactly the LIGHTING target's eight rows changed (the owner's option B of
2026-09-06), with the two arms token-matched line for line on the flight
tokenizer as the committed artifact receipt records them.
"""

import importlib.util
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
#: Where the flown arms' MEASURED token costs live: the builder writes it
#: against a live ``/tokenize`` route, and it is the only place a unit test
#: can read a tokenizer's verdict without starting a server.
RECEIPT = (
    REPO / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-05-a2t-kc-a1-contrast-notes-4000-v1/artifact-receipt.json"
)
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


# -- the 2026-09-06 owner ruling: the control is matched on TOKENS -----------


def _word_counter(text: str) -> int:
    """A stand-in tokenizer: one token per whitespace-separated word, so a
    ``" tool"`` filler costs exactly one and the arithmetic is checkable by
    hand. The real counter is the resident server's ``/tokenize`` route."""

    return len(text.split())


def test_the_control_is_token_matched_when_a_counter_is_injected():
    records = contrast_note_records(
        ROWS, TARGETS, function_words=[], token_counter=_word_counter
    )
    by_tool = {record["tool_name"]: record for record in records}
    for record in records:
        assert record["control_match"] == "tokens"
        assert record["note_cell_tokens"] == record["control_cell_tokens"]
        assert _word_counter(record["kc_a1"]) == _word_counter(record["kc_a1c"])
        # the control is the category and neutral filler, and nothing else
        assert record["control_note"].startswith("; " + record["category"])
        assert set(record["control_note"].removeprefix("; ").split()) <= {
            record["category"], "tool"
        }
    # "; smart_home color" is two words after the category, so the control
    # takes one " tool"; "; smart_car cabin" likewise.
    assert by_tool["setColor"]["control_note"] == "; lighting tool"
    assert by_tool["setColor"]["control_filler_repeats"] == 1
    assert by_tool["setAmbientLighting"]["control_note"] == "; media_cabin tool"
    # a token match is NOT a character match, which is exactly the point: the
    # arms are equal in tokens and free to differ in bytes.
    assert len(by_tool["setColor"]["control_note"]) != len(by_tool["setColor"]["note"])


def test_a_control_that_cannot_land_on_the_note_token_count_is_refused():
    """The filler is a whole token; a gap it would overshoot is a refusal, not
    an approximation."""

    with pytest.raises(ProposerError, match="cannot be token-matched"):
        # a per-character counter leaves an 8-unit gap that a 5-unit filler
        # steps over: 36 -> 41 -> 46 against the note's 44.
        contrast_note_records(
            ROWS,
            {"lighting": {"setColor": "; smart_home color"}},
            function_words=[],
            token_counter=len,
        )


def test_the_builder_refuses_to_register_an_artifact_on_the_estimator():
    """``--write`` without ``--tokenizer-url`` is the defect attempt 1 shipped:
    the gate passed because the caller fed it an estimate."""

    import sys

    path = REPO / "scripts/build_a2t_contrast_notes.py"
    spec = importlib.util.spec_from_file_location("build_a2t_contrast_notes", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    argv = sys.argv
    sys.argv = [str(path), "--write"]
    try:
        with pytest.raises(SystemExit, match="--write needs --tokenizer-url"):
            module.main()
    finally:
        sys.argv = argv


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
def test_the_two_arms_are_token_matched_line_for_line():
    """The committed control is matched to the treatment on TOKENS, and the
    artifact receipt is where that measurement lives.

    Nothing here can tokenize -- the authority is the resident server's
    ``/tokenize`` route, which a unit test may not start -- so the test binds
    the committed BYTES to the committed MEASUREMENT: the receipt's per-line
    token counts must be equal arm for arm, its whole-block equality flag must
    be true, and the lines the receipt prices must be the lines the fragments
    actually render. A control edited after the measurement fails here.
    """

    lock, root = _REAL
    blocks = {}
    for arm, (path, _) in FRAGMENTS.items():
        values = json.loads(path.read_text(encoding="utf-8"))
        rendered = resolve_active_task_instruction(values, REPO, lock, root)
        blocks[arm] = rendered.split("## Available Tools:\n", 1)[1].rstrip("\n").split("\n")
    treatment, control = blocks["kc-a1"], blocks["kc-a1c"]
    assert [line == other for line, other in zip(treatment, control)].count(False) == 8

    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert receipt["whole_block_token_equality"]["token_matched"] is True
    assert receipt["tokenizer"]["route"].startswith("POST /tokenize")
    by_tool = {record["tool_name"]: record for record in receipt["per_tool"]}
    assert len(by_tool) == 8
    for record in by_tool.values():
        assert record["control_match"] == "tokens"
        assert record["kc_a1_line_tokens"] == record["kc_a1c_line_tokens"]
        assert record["kc_a1_added_line_tokens"] == record["kc_a1c_added_line_tokens"]
    rendered_lines = {line.split("(", 1)[0][2:]: line for line in treatment}
    control_lines = {line.split("(", 1)[0][2:]: line for line in control}
    for tool, record in by_tool.items():
        assert rendered_lines[tool].endswith(record["kc_a1"])
        assert control_lines[tool].endswith(record["kc_a1c"])
