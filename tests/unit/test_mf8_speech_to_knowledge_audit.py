"""Unit tests for ``scripts/mf8_speech_to_knowledge_audit.py``.

Pure helpers only: no SLURP data, no lock, no model, no GPU and no filesystem
beyond the tmp paths the tests write themselves.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
AUDIT_SCRIPT = REPO / "scripts" / "mf8_speech_to_knowledge_audit.py"


def _audit():
    """Load the script by path -- the shared WSL venv carries an unrelated
    top-level ``scripts`` package, so ``import scripts.<name>`` resolves to
    that one instead of this repository's."""

    name = "test_mf8_audit_module"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, AUDIT_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


audit = _audit()


def test_recording_filename_inverts_the_sample_id_construction() -> None:
    assert audit.recording_filename("slurp:devel:000011:audio-1497266596") == (
        "audio-1497266596.flac"
    )
    assert audit.recording_filename("slurp:train:000042:audio-1") == "audio-1.flac"


@pytest.mark.parametrize(
    "sample_id",
    ["", "slurp:devel:000011", "slurp:devel:000011:", "slurp:devel:000011:a:b"],
)
def test_recording_filename_refuses_a_malformed_sample_id(sample_id: str) -> None:
    with pytest.raises(ValueError):
        audit.recording_filename(sample_id)


def test_roster_sample_ids_reads_committed_file_order(tmp_path: Path) -> None:
    path = tmp_path / "roster.json"
    path.write_text(
        json.dumps({"items": [{"sample_id": "b"}, {"sample_id": "a"}]}),
        encoding="utf-8",
    )
    assert audit.roster_sample_ids(path) == ("b", "a")


def test_roster_sample_ids_refuses_an_empty_or_repeating_roster(tmp_path: Path) -> None:
    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({"items": []}), encoding="utf-8")
    with pytest.raises(ValueError):
        audit.roster_sample_ids(empty)

    repeated = tmp_path / "repeated.json"
    repeated.write_text(
        json.dumps({"items": [{"sample_id": "a"}, {"sample_id": "a"}]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        audit.roster_sample_ids(repeated)

    untyped = tmp_path / "untyped.json"
    untyped.write_text(json.dumps({"items": [{"sample_id": 7}]}), encoding="utf-8")
    with pytest.raises(ValueError):
        audit.roster_sample_ids(untyped)


def test_histogram_is_sorted_by_integer_key() -> None:
    assert audit.histogram([10, 2, 2, 0]) == {"0": 1, "2": 2, "10": 1}
    assert audit.histogram([]) == {}


def test_quantiles_are_nearest_rank_and_stable() -> None:
    assert audit.quantiles([]) == {}
    single = audit.quantiles([4])
    assert single["min"] == single["median"] == single["max"] == 4.0
    values = list(range(1, 11))
    result = audit.quantiles(values)
    assert result["min"] == 1.0
    assert result["max"] == 10.0
    assert result["mean"] == 5.5
    assert result["median"] in {5.0, 6.0}
    assert result["p25"] <= result["median"] <= result["p75"] <= result["p90"]


def test_at_least_counts_are_monotone() -> None:
    counts = audit.at_least_counts([0, 1, 3, 5, 8], (1, 3, 5, 8))
    assert counts == {">=1": 4, ">=3": 3, ">=5": 2, ">=8": 1}


def _outputs_file(tmp_path: Path, rows: list[dict[str, object]]) -> Path:
    path = tmp_path / "outputs.jsonl"
    path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )
    return path


def test_read_sealed_outputs_maps_sample_id_to_text(tmp_path: Path) -> None:
    path = _outputs_file(
        tmp_path,
        [{"sample_id": "a", "text": "{}"}, {"sample_id": "b", "text": "x"}],
    )
    assert audit.read_sealed_outputs(path) == {"a": "{}", "b": "x"}


def test_read_sealed_outputs_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        audit.read_sealed_outputs(_outputs_file(tmp_path, [{"sample_id": "a"}]))
    with pytest.raises(ValueError):
        audit.read_sealed_outputs(
            _outputs_file(tmp_path, [{"sample_id": "a", "text": "1"}] * 2)
        )
    empty = tmp_path / "empty.jsonl"
    empty.write_text("\n\n", encoding="utf-8")
    with pytest.raises(ValueError):
        audit.read_sealed_outputs(empty)


def test_sealed_outputs_carry_logprobs_is_a_substring_test(tmp_path: Path) -> None:
    plain = tmp_path / "plain.jsonl"
    plain.write_text('{"sample_id": "a", "text": "x"}\n', encoding="utf-8")
    assert audit.sealed_outputs_carry_logprobs(plain) is False
    with_probs = tmp_path / "probs.jsonl"
    with_probs.write_text('{"logprobs": {"content": []}}\n', encoding="utf-8")
    assert audit.sealed_outputs_carry_logprobs(with_probs) is True


def test_ordered_candidates_dedupes_in_rank_order() -> None:
    assert audit.ordered_candidates(
        [("a", 0.9), ("b", 0.8), ("a", 0.7), ("c", 0.1)]
    ) == ("a", "b", "c")
    assert audit.ordered_candidates([]) == ()


def test_audio_prompt_tokens_charges_whole_one_second_chunks() -> None:
    assert audit.audio_prompt_tokens(0.0) == 0
    assert audit.audio_prompt_tokens(0.001) == 13
    assert audit.audio_prompt_tokens(1.0) == 13
    assert audit.audio_prompt_tokens(1.0001) == 26
    assert audit.audio_prompt_tokens(2.0) == 26
    # the Earnings-21 wire anchor: 90 s of buffered audio, 2.0 s of appended
    # silence, 26 tokens of difference per window and no residue.
    assert audit.audio_prompt_tokens(92.0) - audit.audio_prompt_tokens(90.0) == 26
    with pytest.raises(ValueError):
        audit.audio_prompt_tokens(-0.5)


LEGAL_SCENARIOS = frozenset({"iot", "music"})
LEGAL_PAIRS = frozenset({("iot", "hue_lightoff"), ("music", "query")})


def test_judge_verdict_passes_a_legal_pair() -> None:
    assert (
        audit.judge_verdict("iot", "hue_lightoff", True, LEGAL_SCENARIOS, LEGAL_PAIRS)
        is None
    )


def test_judge_verdict_names_the_tier_it_flags() -> None:
    assert (
        audit.judge_verdict(None, None, False, LEGAL_SCENARIOS, LEGAL_PAIRS) == "unparsed"
    )
    assert (
        audit.judge_verdict(None, "query", True, LEGAL_SCENARIOS, LEGAL_PAIRS) == "no-label"
    )
    assert (
        audit.judge_verdict("locations", "query", True, LEGAL_SCENARIOS, LEGAL_PAIRS)
        == "scenario-not-legal"
    )
    assert (
        audit.judge_verdict("iot", "query", True, LEGAL_SCENARIOS, LEGAL_PAIRS)
        == "action-illegal-for-scenario"
    )


def test_jsonl_field_names_counts_keys_and_never_values(tmp_path: Path) -> None:
    path = tmp_path / "split.jsonl"
    path.write_text(
        '{"slurp_id": 1, "sentence": "secret words"}\n'
        "\n"
        '{"slurp_id": 2, "scenario": "iot"}\n',
        encoding="utf-8",
    )
    assert audit.jsonl_field_names(path) == {
        "__rows__": 2,
        "scenario": 1,
        "sentence": 1,
        "slurp_id": 2,
    }
    assert audit.jsonl_field_names(path, limit=1) == {
        "__rows__": 1,
        "sentence": 1,
        "slurp_id": 1,
    }


def test_jsonl_field_names_refuses_a_non_object_row(tmp_path: Path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text("[1, 2]\n", encoding="utf-8")
    with pytest.raises(ValueError):
        audit.jsonl_field_names(path)


def test_compose_candidates_leads_with_the_scenario_then_fills() -> None:
    scenario = ("iot_hue_lightoff", "iot_hue_lighton", "iot_wemo_on")
    neighbours = ("music_query", "iot_hue_lightoff", "play_music")
    assert audit.compose_candidates(scenario, neighbours, 5, scenario_lead=3) == (
        "iot_hue_lightoff",
        "iot_hue_lighton",
        "iot_wemo_on",
        "music_query",
        "play_music",
    )
    # scenario_lead 0 is the neighbours-only design.
    assert audit.compose_candidates(scenario, neighbours, 2, scenario_lead=0) == (
        "music_query",
        "iot_hue_lightoff",
    )
    # the lead never exceeds k, and an empty scenario list is legal.
    assert audit.compose_candidates((), neighbours, 2, scenario_lead=3) == (
        "music_query",
        "iot_hue_lightoff",
    )
    assert len(audit.compose_candidates(scenario, neighbours, 1, scenario_lead=3)) == 1


def test_compose_candidates_refuses_a_nonsense_shape() -> None:
    with pytest.raises(ValueError):
        audit.compose_candidates(("a",), ("b",), 0, scenario_lead=1)
    with pytest.raises(ValueError):
        audit.compose_candidates(("a",), ("b",), 3, scenario_lead=-1)


def test_recall_at_reads_only_the_first_k() -> None:
    candidates = ("a", "b", "c", "d")
    assert audit.recall_at(candidates, "a", 1) is True
    assert audit.recall_at(candidates, "c", 2) is False
    assert audit.recall_at(candidates, "c", 3) is True
    assert audit.recall_at(candidates, "z", 4) is False
