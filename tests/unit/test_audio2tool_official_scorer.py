"""The vendored Audio2Tool official evaluation code, and the scorer over it.

Two kinds of assertion live here and they are deliberately separate:

1. IDENTITY. ``reproduction/audio2tool_official/metrics.py`` must still be
   the pinned upstream file, byte for byte, and ``parse.py`` must still be
   the pinned upstream ``BaseAudioModel.parse_tool_call`` under the one
   documented derivation (dedent one level, drop the bound ``self``). The
   metrics check is hash-only and always runs; the parse check re-derives
   from the local clone and SKIPS with a clear reason when the clone is
   absent, because a machine without ``SPEECHRL_DATA_DIR`` cannot be asked
   to prove a fact about a repository it does not have.

2. SEMANTICS. Hand cases pinning the four behaviours the replication
   depends on: an argument-free Tier-1 call versus one carrying an argument,
   ``20.0`` versus ``20`` under the official value normalization, the
   first-call-only rule on a multi-call response, and an unparsed row.

``a2t-toolcall``/``a2t-toolcall-v2`` are untouched by everything here.
"""

import hashlib
import json
import os
import textwrap
from pathlib import Path

import pytest

import speech_aware_evidence_acquisition.core  # noqa: F401 (populate registries)
from speech_aware_evidence_acquisition.core.base import SCORERS
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.reproduction.a2t_scorer import (
    ToolCallScoringError,
    score_audio2tool_outputs_official,
)
from speech_aware_evidence_acquisition.reproduction.audio2tool_official import (
    AUDIO2TOOL_OFFICIAL_BASE_BLOB_SHA1,
    AUDIO2TOOL_OFFICIAL_COMMIT,
    AUDIO2TOOL_OFFICIAL_METRICS_BLOB_SHA1,
    metrics as official_metrics,
)
from speech_aware_evidence_acquisition.reproduction.audio2tool_official import parse as official_parse

VENDORED_DIR = Path(official_metrics.__file__).parent
CLONE_RELPATH = "repos/audio2tool"


def git_blob_sha1(data: bytes) -> str:
    """The SHA-1 git itself would assign to ``data`` as a blob."""

    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def clone_root() -> Path | None:
    data_root = os.environ.get("SPEECHRL_DATA_DIR")
    if not data_root:
        return None
    candidate = Path(data_root) / CLONE_RELPATH
    return candidate if (candidate / "audio_benchmark" / "models" / "base.py").is_file() else None


# ---------------------------------------------------------------------------
# 1. Identity of the vendored upstream code
# ---------------------------------------------------------------------------


def test_vendored_metrics_is_the_pinned_upstream_blob():
    data = (VENDORED_DIR / "metrics.py").read_bytes()
    assert git_blob_sha1(data) == AUDIO2TOOL_OFFICIAL_METRICS_BLOB_SHA1
    assert AUDIO2TOOL_OFFICIAL_METRICS_BLOB_SHA1 == (
        "d98277bcf69795c9a0ae54e538c170abfd8c51ca"
    )
    assert b"\r\n" not in data


def test_vendored_parse_matches_the_clone():
    root = clone_root()
    if root is None:
        pytest.skip(
            "the pinned Audio2Tool clone is absent on this machine "
            "($SPEECHRL_DATA_DIR/repos/audio2tool/audio_benchmark/models/base.py); "
            "rebuild it with the command in "
            "docs/receipts/environments/audio2tool-official-code.json"
        )
    import ast

    base_path = root / "audio_benchmark" / "models" / "base.py"
    upstream_bytes = base_path.read_bytes()
    assert git_blob_sha1(upstream_bytes) == AUDIO2TOOL_OFFICIAL_BASE_BLOB_SHA1, (
        "the local clone is not at commit " + AUDIO2TOOL_OFFICIAL_COMMIT
    )
    source = upstream_bytes.decode("utf-8")
    lines = source.splitlines(keepends=True)
    node = next(
        item
        for item in ast.walk(ast.parse(source))
        if isinstance(item, ast.FunctionDef) and item.name == "parse_tool_call"
    )
    segment = "".join(lines[node.lineno - 1 : node.end_lineno])
    expected = textwrap.dedent(segment).replace(
        "def parse_tool_call(self, raw_output: str)",
        "def parse_tool_call(raw_output: str)",
        1,
    )

    vendored = (VENDORED_DIR / "parse.py").read_text(encoding="utf-8")
    marker = "def parse_tool_call(raw_output: str)"
    assert marker in vendored
    assert vendored[vendored.index(marker) :] == expected


def test_official_scorer_is_registered():
    assert "a2t-toolcall-official" in SCORERS.names()
    # v1 and v2 stay registered: the official scorer is reported beside them.
    assert {"a2t-toolcall", "a2t-toolcall-v2"} <= set(SCORERS.names())


# ---------------------------------------------------------------------------
# 2. Semantics
# ---------------------------------------------------------------------------


def test_parse_takes_the_first_call_only():
    name, call, params = official_parse.parse_tool_call(
        "setLighting(state='On') setThermostatMode(mode='Cool')"
    )
    assert name == "setLighting"
    assert call == "setLighting(state='On')"
    assert params == {"state": "On"}


def test_parse_falls_back_to_a_bare_call_token_then_to_empty():
    assert official_parse.parse_tool_call("I would call setLighting() next")[0] == "setLighting"
    assert official_parse.parse_tool_call("no tool here at all")[0] == ""


def test_numeric_normalization_20_versus_20_point_0():
    assert official_metrics.compute_parameter_accuracy({"level": "20"}, {"level": 20})[
        "exact_match"
    ]
    assert not official_metrics.compute_parameter_accuracy({"level": "20.0"}, {"level": 20})[
        "exact_match"
    ]
    assert official_metrics.compute_parameter_accuracy({"level": "20.0"}, {"level": 20.0})[
        "exact_match"
    ]


def _write_outputs(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )
    return path


def _score(world, tmp_path, rows):
    lock = load_lock(world.lock_path)
    outputs = _write_outputs(tmp_path / "run.outputs.jsonl", rows)
    result = score_audio2tool_outputs_official(
        outputs, lock, world.data_root, repo_root=world.repo_root
    )
    return {entry["sample_id"]: entry for entry in result["per_sample"]}, result["aggregate"]


def test_tier1_argument_free_call_is_an_exact_match(audio2tool_world, tmp_path):
    # Gold: setLighting, extracted_params {}.
    per_sample, _ = _score(
        audio2tool_world,
        tmp_path,
        [{"sample_id": "tier1_direct:000001", "text": "setLighting()"}],
    )
    row = per_sample["tier1_direct:000001"]
    assert row["predicted_tool"] == "setLighting"
    assert row["tool_correct"] is True
    assert row["param_exact_match"] is True
    assert row["exact_match"] is True
    assert row["parsed"] is True


def test_tier1_extra_argument_keeps_the_tool_but_loses_exact_match(
    audio2tool_world, tmp_path
):
    per_sample, _ = _score(
        audio2tool_world,
        tmp_path,
        [{"sample_id": "tier1_direct:000001", "text": "setLighting(deviceId='light_1')"}],
    )
    row = per_sample["tier1_direct:000001"]
    assert row["tool_correct"] is True
    assert row["param_exact_match"] is False
    assert row["exact_match"] is False
    assert row["param_precision"] == 0.0
    assert row["param_recall"] == 1.0
    assert row["param_predicted_keys"] == 1
    assert row["param_gold_keys"] == 0


def test_multi_call_response_is_judged_on_its_first_call(audio2tool_world, tmp_path):
    # tier3 gold: primary setSecurityMode + two additional entries. A response
    # naming the right primary first scores tool_correct even though the
    # official HF path can only ever see one call.
    per_sample, aggregate = _score(
        audio2tool_world,
        tmp_path,
        [
            {
                "sample_id": "tier3_multi_intent:000004",
                "text": (
                    "setSecurityMode(mode='Armed_Away', level=2) "
                    "calibrateThermostat()"
                ),
            }
        ],
    )
    row = per_sample["tier3_multi_intent:000004"]
    assert row["predicted_tool"] == "setSecurityMode"
    assert row["tool_correct"] is True
    assert row["exact_match"] is True  # mode + level both match after normalization
    assert row["is_multi_tool"] is True
    assert row["num_expected_tools"] == 3
    # Only the FIRST call is scored, so the additional tools are missing.
    assert row["multi_tool_all_match"] is False
    assert row["multi_tool_recall"] == pytest.approx(1 / 3)
    # The diagnostic still records that the response named two calls.
    assert row["official_call_matches"] == 2
    assert aggregate["rows_with_multiple_call_matches"] == 1


def test_unparsed_row_scores_zero_and_lowers_the_parse_rate(audio2tool_world, tmp_path):
    per_sample, aggregate = _score(
        audio2tool_world,
        tmp_path,
        [
            {"sample_id": "tier1_direct:000001", "text": "setLighting()"},
            {"sample_id": "tier3_multi_intent:000004", "text": "I am not sure what to do."},
        ],
    )
    bad = per_sample["tier3_multi_intent:000004"]
    assert bad["predicted_tool"] == ""
    assert bad["parsed"] is False
    assert bad["tool_correct"] is False
    assert bad["exact_match"] is False
    assert aggregate["samples"] == 2
    assert aggregate["parse_rate"] == 0.5
    assert aggregate["parse_failures"] == 1
    assert aggregate["tool_accuracy"] == 0.5


def test_aggregate_reports_macro_and_micro_parameter_f1(audio2tool_world, tmp_path):
    # tier3 gold has 2 parameters; predicting one correct key gives
    # per-sample precision 1.0 and recall 0.5. tier1 gold has none, and both
    # empty is a 1.0/1.0 row upstream -- so the MACRO mean is not the MICRO
    # pooled figure, which is exactly why both are reported.
    _, aggregate = _score(
        audio2tool_world,
        tmp_path,
        [
            {"sample_id": "tier1_direct:000001", "text": "setLighting()"},
            {
                "sample_id": "tier3_multi_intent:000004",
                "text": "setSecurityMode(mode='Armed_Away')",
            },
        ],
    )
    assert aggregate["param_precision"] == pytest.approx(1.0)
    assert aggregate["param_recall"] == pytest.approx(0.75)  # (1.0 + 0.5) / 2
    assert aggregate["param_f1"] == pytest.approx((1.0 + 2 / 3) / 2)
    assert aggregate["param_correct_keys"] == 1
    assert aggregate["param_predicted_keys"] == 1
    assert aggregate["param_gold_keys"] == 2
    assert aggregate["param_precision_micro"] == pytest.approx(1.0)
    assert aggregate["param_recall_micro"] == pytest.approx(0.5)
    assert aggregate["param_f1_micro"] == pytest.approx(2 / 3)
    assert aggregate["official_commit"] == AUDIO2TOOL_OFFICIAL_COMMIT


def test_per_tier_blocks_and_refusals(audio2tool_world, tmp_path):
    lock = load_lock(audio2tool_world.lock_path)
    outputs = _write_outputs(
        tmp_path / "run.outputs.jsonl",
        [
            {"sample_id": "tier1_direct:000001", "text": "setLighting()"},
            {"sample_id": "tier7_multiturn:000009", "text": "setAlarm(time='06:30')"},
        ],
    )
    result = score_audio2tool_outputs_official(
        outputs, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root
    )
    per_tier = result["aggregate"]["per_tier"]
    assert set(per_tier) == {"tier1_direct", "tier7_multiturn"}
    assert per_tier["tier1_direct"]["tool_accuracy"] == 1.0
    assert per_tier["tier7_multiturn"]["samples"] == 1

    unknown = _write_outputs(
        tmp_path / "bad.outputs.jsonl", [{"sample_id": "tier9_bogus:000001", "text": "x()"}]
    )
    with pytest.raises(ToolCallScoringError, match="tier9_bogus"):
        score_audio2tool_outputs_official(
            unknown, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root
        )

    duplicate_row = {"sample_id": "tier1_direct:000001", "text": "setLighting()"}
    duplicated = _write_outputs(
        tmp_path / "dup.outputs.jsonl", [duplicate_row, duplicate_row]
    )
    with pytest.raises(ToolCallScoringError, match="duplicate"):
        score_audio2tool_outputs_official(
            duplicated, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root
        )


def test_official_gold_is_the_release_shape_not_a2t_gold_v1(audio2tool_world, tmp_path):
    """The official gold must be ``extracted_params`` VERBATIM.

    ``a2t-gold-v1`` JSON-coerces values and can take the primary arguments
    from the ``expected_tool_call`` call string; the release loader does
    neither. The fixture's tier7 row is the discriminator: its
    ``extracted_params`` carries ``repeat`` as the STRING ``'["Weekdays"]'``
    while its call string carries the Python list ``['Weekdays']``.
    """

    from speech_aware_evidence_acquisition.data.audio2tool import (
        load_expected_calls,
        load_official_gold,
    )

    lock = load_lock(audio2tool_world.lock_path)
    official = load_official_gold(
        lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root
    )
    v1 = load_expected_calls(
        lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root
    )
    row = official["tier7_multiturn:000009"]
    assert row.tool_name == "setAlarm"
    assert row.extracted_params == {"time": "06:30", "repeat": '["Weekdays"]'}
    assert row.additional_tool_calls == ()
    # a2t-gold-v1 disagrees on the same row, which is the whole point.
    assert v1["tier7_multiturn:000009"][0].arguments["repeat"] == ["Weekdays"]
    # Additional tool calls stay VERBATIM strings; the release never splits a
    # concatenated element the way a2t-gold-v1 does.
    tier3 = official["tier3_multi_intent:000004"]
    assert tier3.additional_tool_calls == (
        "setTargetTemperature(temperature=68.0)setColor(color='blue')",
        "calibrateThermostat",
    )
    assert len(v1["tier3_multi_intent:000004"]) == 4


# ---------------------------------------------------------------------------
# 3. The request side: the compact registry fill and the frozen template that
#    together render the release's own system message.
# ---------------------------------------------------------------------------

OFFICIAL_SYSTEM_PROMPT = (
    "You are an AI assistant that converts voice commands into tool calls. "
    "Listen to the audio and determine which tool should be called. "
    "Output ONLY the tool call in the format: tool_name(param1=value1, param2=value2). "
    "If no parameters are mentioned, output: tool_name()."
)

REPO_ROOT_PATH = Path(__file__).resolve().parents[2]
OFFICIAL_TEMPLATE = REPO_ROOT_PATH / "configs" / "probes" / "r1_audio2tool_official.txt"


def test_official_template_bytes_are_the_release_envelope():
    data = OFFICIAL_TEMPLATE.read_bytes()
    assert b"\r\n" not in data
    text = data.decode("utf-8")
    assert text == OFFICIAL_SYSTEM_PROMPT + "\n\n## Available Tools:\n{tool_schemas}"
    # No trailing newline: upstream builds the message as
    # f"{system_prompt}\n\n## Available Tools:\n{tool_lines}" and tool_lines
    # is a "\n".join with nothing after it.
    assert not text.endswith("\n")


def test_official_template_is_pinned_in_the_probe_manifest():
    manifest = json.loads(
        (REPO_ROOT_PATH / "configs" / "probes" / "manifest.json").read_text(encoding="utf-8")
    )
    entry = manifest["templates"]["r1_audio2tool_official.txt"]
    assert entry["sha256"] == hashlib.sha256(OFFICIAL_TEMPLATE.read_bytes()).hexdigest()
    probe = manifest["probes"]["R1-audio2tool-official-protocol"]
    assert probe["arms"]["direct"] == ["r1_audio2tool_official.txt"]
    assert probe["profile"] == "baseline-reproduction"
    # The reconstruction template R1/A0/A0' flew is untouched.
    assert "r1_audio2tool_direct.txt" in manifest["templates"]


def test_compact_registry_fill_is_registered_and_renders_upstream_lines(
    audio2tool_world,
):
    from speech_aware_evidence_acquisition.core.base import INSTRUCTION_FILLS
    from speech_aware_evidence_acquisition.data.audio2tool_tools import (
        render_registry_compact,
    )

    assert "audio2tool-registry-compact" in INSTRUCTION_FILLS.names()
    # The pre-existing fill stays registered and is not replaced.
    assert "audio2tool-tool-schemas" in INSTRUCTION_FILLS.names()

    lock = load_lock(audio2tool_world.lock_path)
    rendered = render_registry_compact(lock, audio2tool_world.data_root)
    # Sorted by tool_name under plain string order, NOT by tool_id (the
    # fixture registry lists setSecurityMode, tool_id 10, before setLighting,
    # tool_id 2, so tool_id order would put setSecurityMode first).
    assert rendered == (
        "- setLighting(deviceId: String): Turns a light on.\n"
        "- setSecurityMode(mode: Mode): Sets the security mode."
    )
    # Only signature and description: no defaults, no constraints.
    assert "argument" not in rendered
    assert "Home" not in rendered
    assert not rendered.endswith("\n")


def test_official_baseline_fragment_declares_the_published_protocol():
    fragment = json.loads(
        (
            REPO_ROOT_PATH
            / "configs"
            / "baseline"
            / "a2t-direct-official-protocol.json"
        ).read_text(encoding="utf-8")
    )
    assert fragment["arm"] == "bare-core"
    assert fragment["task_instruction_template"] == "probes/r1_audio2tool_official.txt"
    assert fragment["task_instruction_fill"] == "audio2tool-registry-compact"
    assert fragment["task_instruction_template_active"] is True
    assert fragment["user_turn_text"] == "Convert this voice command to a tool call."
    assert fragment["user_turn_audio_first"] is True
    # The paper-facing scorer runs first, with v2 and v1 beside it.
    assert fragment["scorers"][0] == "a2t-toolcall-official"
    assert {"a2t-toolcall-v2", "a2t-toolcall", "cost"} <= set(fragment["scorers"])
    # No native tools list: the pinned adapter never sends one.
    assert "tool_schema_fill" not in fragment


def test_legacy_calibration_baselines_are_untouched():
    """The four sealed calibration cells must keep flying what they flew.

    They carry driver-path template keys the flight path has never honoured;
    the opt-in flag is what keeps that true now that the flight path CAN
    honour them.
    """

    for name in (
        "a2t-direct-calibration",
        "a2t-direct-native-tools-calibration",
        "a2t-direct-packets",
        "a2t-direct-packets-native-tools",
    ):
        fragment = json.loads(
            (REPO_ROOT_PATH / "configs" / "baseline" / f"{name}.json").read_text(
                encoding="utf-8"
            )
        )
        assert "task_instruction_template_active" not in fragment
        assert "user_turn_text" not in fragment
