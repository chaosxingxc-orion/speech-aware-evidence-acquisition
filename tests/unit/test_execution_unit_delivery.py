from __future__ import annotations

import copy
import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.core.delivery import (
    stitch_execution_unit_results,
    stitch_ordered_text,
)
from speech_aware_evidence_acquisition.core.model import SliceRecord
from speech_aware_evidence_acquisition.rails.execution_units import (
    ExecutionUnit,
    ExecutionUnitRoster,
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _unit(parent: str, index: int) -> ExecutionUnit:
    record = SliceRecord(
        sample_id=parent,
        parent_media_relpath=f"parents/{parent}.mp3",
        parent_sha256=_sha(f"parent-{parent}"),
        start_seconds=float(index * 90),
        end_seconds=float((index + 1) * 90),
        audio_seconds=90.0,
        sample_rate_hz=16000,
        media_relpath=f"derived/{parent}/i{index:04d}.wav",
        sha256=_sha(f"slice-{parent}-{index}"),
        bytes=2_880_044,
        iteration=index,
    )
    return ExecutionUnit(parent, f"{parent}#w{index + 1:04d}", record)


def _result(unit: ExecutionUnit, text: str, **flags: bool) -> dict[str, object]:
    return {
        "sample_id": unit.parent_sample_id,
        "execution_unit_id": unit.request_key,
        "execution_unit_binding": unit.as_json(),
        "request_id": f"request-{unit.request_key}",
        "request_sha256": _sha(f"request-{unit.request_key}"),
        "response_sha256": _sha(f"response-{unit.request_key}"),
        "response_text_sha256": _sha(text),
        "text": text,
        "saturated": flags.get("saturated", False),
        "skipped": flags.get("skipped", False),
    }


def _roster() -> ExecutionUnitRoster:
    return ExecutionUnitRoster((_unit("a", 0), _unit("a", 1), _unit("b", 0)))


def test_stitch_ordered_text_preserves_legacy_obs_bytes() -> None:
    parts = ["  first  ", "", "second", " ", "third"]
    assert stitch_ordered_text(parts) == " ".join(part for part in parts if part)


def test_stitches_two_parents_and_binds_sources_and_hashes() -> None:
    roster = _roster()
    results = [
        _result(roster.units[0], " first "),
        _result(roster.units[1], "second"),
        _result(roster.units[2], "third"),
    ]

    rows = stitch_execution_unit_results(roster, ("a", "b"), results)

    assert [row["sample_id"] for row in rows] == ["a", "b"]
    assert [row["text"] for row in rows] == ["first second", "third"]
    assert all(
        row["execution_unit_roster_sha256"] == roster.content_hash() for row in rows
    )
    assert [source["execution_unit_id"] for source in rows[0]["sources"]] == [
        "a#w0001",
        "a#w0002",
    ]
    assert rows[0]["response_text_sha256"] == _sha("first second")
    assert rows[0]["sources"][0]["raw_text_sha256"] == _sha(" first ")
    assert rows[0]["sources"][0]["delivery_text_sha256"] == _sha("first")
    request_descriptor = json.dumps(
        {
            "stitched_request_ids": [result["request_id"] for result in results[:2]],
            "iteration_request_sha256s": [
                result["request_sha256"] for result in results[:2]
            ],
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    response_descriptor = json.dumps(
        {
            "stitched_text": "first second",
            "stitched_from_response_sha256s": [
                result["response_sha256"] for result in results[:2]
            ],
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert rows[0]["request_sha256"] == _sha(request_descriptor)
    assert rows[0]["response_sha256"] == _sha(response_descriptor)


def test_saturated_skipped_and_empty_results_normalize_before_stitch() -> None:
    roster = ExecutionUnitRoster((_unit("a", 0), _unit("a", 1), _unit("a", 2)))
    results = [
        _result(roster.units[0], "discard saturated", saturated=True),
        _result(roster.units[1], "discard skipped", skipped=True),
        _result(roster.units[2], "   "),
    ]

    row = stitch_execution_unit_results(roster, ("a",), results)[0]

    assert row["text"] == ""
    assert [source["delivery_text_sha256"] for source in row["sources"]] == [
        _sha(""),
        _sha(""),
        _sha(""),
    ]
    assert row["sources"][0]["saturated"] is True
    assert row["sources"][1]["skipped"] is True


def test_allows_additional_upstream_custody_without_copying_it() -> None:
    roster = _roster()
    results = [_result(unit, str(index)) for index, unit in enumerate(roster.units)]
    results[0]["timing_custody"] = {"validated_elsewhere": True}

    rows = stitch_execution_unit_results(roster, ("a", "b"), results)

    assert "timing_custody" not in rows[0]["sources"][0]


def test_raw_terminal_mappings_are_not_modified() -> None:
    roster = _roster()
    results = [
        _result(unit, f" text-{index} ") for index, unit in enumerate(roster.units)
    ]
    before = copy.deepcopy(results)

    first = stitch_execution_unit_results(roster, ("a", "b"), results)
    second = stitch_execution_unit_results(roster, ("a", "b"), results)

    assert results == before
    assert first == second


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "out-of-order"])
def test_requires_exact_complete_ordered_unit_coverage(mutation: str) -> None:
    roster = _roster()
    results = [_result(unit, str(index)) for index, unit in enumerate(roster.units)]
    if mutation == "missing":
        results.pop()
    elif mutation == "duplicate":
        results[1] = copy.deepcopy(results[0])
    else:
        results[0], results[1] = results[1], results[0]

    with pytest.raises(ValueError):
        stitch_execution_unit_results(roster, ("a", "b"), results)


def test_rejects_mismatched_parent_or_source_binding() -> None:
    roster = _roster()
    results = [_result(unit, str(index)) for index, unit in enumerate(roster.units)]
    results[0]["sample_id"] = "b"
    with pytest.raises(ValueError, match="out of roster order"):
        stitch_execution_unit_results(roster, ("a", "b"), results)

    results = [_result(unit, str(index)) for index, unit in enumerate(roster.units)]
    results[0]["execution_unit_binding"]["slice_record"]["sha256"] = _sha("tampered")
    with pytest.raises(ValueError, match="source binding"):
        stitch_execution_unit_results(roster, ("a", "b"), results)


def test_rejects_duplicate_request_id_bad_text_hash_and_flags() -> None:
    roster = _roster()
    results = [_result(unit, str(index)) for index, unit in enumerate(roster.units)]
    results[1]["request_id"] = results[0]["request_id"]
    with pytest.raises(ValueError, match="repeat a request_id"):
        stitch_execution_unit_results(roster, ("a", "b"), results)

    results = [_result(unit, str(index)) for index, unit in enumerate(roster.units)]
    results[0]["response_text_sha256"] = _sha("different")
    with pytest.raises(ValueError, match="text hash"):
        stitch_execution_unit_results(roster, ("a", "b"), results)

    results = [_result(unit, str(index)) for index, unit in enumerate(roster.units)]
    results[0]["saturated"] = "yes"
    with pytest.raises(ValueError, match="flags must be booleans"):
        stitch_execution_unit_results(roster, ("a", "b"), results)

    results = [_result(unit, str(index)) for index, unit in enumerate(roster.units)]
    results[0]["request_sha256"] = "not-a-hash"
    with pytest.raises(ValueError, match="lowercase SHA256"):
        stitch_execution_unit_results(roster, ("a", "b"), results)
