"""Recover source-bound delivered windows; never rescore or choose another answer."""

from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis import delivery_windows as subject
from speech_aware_evidence_acquisition.core.bundle.artifacts import VerifiedBundle
from speech_aware_evidence_acquisition.core.delivery import stitch_execution_unit_results
from speech_aware_evidence_acquisition.rails.execution_units import (
    ExecutionUnitRoster, execution_unit_scope,
)
from test_execution_unit_delivery import _result, _sha, _unit
from test_native_episode_diagnostics import _fixture, _terminal_fixture, _finite_fixture


def _bundle(roster, results, traces=None):
    parents = tuple(dict.fromkeys(unit.parent_sample_id for unit in roster.units))
    stitched = stitch_execution_unit_results(roster, parents, results)
    trace = {} if traces is None else deepcopy(traces)
    for result in results:
        request_id = result["request_id"]
        trace.setdefault(request_id + "/request", {
            "payload": {"request_id": request_id, "sample_id": result["sample_id"]},
            "payload_sha256": result["request_sha256"],
        })
        trace.setdefault(request_id + "/response", {
            "text": result["text"], "response_sha256": result["response_sha256"],
            "response_text_sha256": result["response_text_sha256"],
        })
    outputs = []
    for row in stitched:
        request_id = row["sample_id"] + ":unit-stitch"
        output = {
            "sample_id": row["sample_id"], "request_id": request_id, "text": row["text"],
            **{key: row[key] for key in ("request_sha256", "response_sha256", "response_text_sha256")},
            "execution_unit_delivery": row,
        }
        outputs.append(output)
        trace[request_id + "/request"] = {
            "payload_sha256": row["request_sha256"], "stitch": True,
            "stitched_request_ids": row["request_ids"],
            "execution_unit_roster_sha256": row["execution_unit_roster_sha256"],
        }
        trace[request_id + "/response"] = {
            "stitch": True, "text": row["text"], "response_sha256": row["response_sha256"],
            "response_text_sha256": row["response_text_sha256"],
            "stitched_from_response_sha256s": row["source_response_sha256s"],
        }
        trace[request_id + "/use"] = {
            "use_admitted": True, "use_response_sha256": row["response_sha256"],
            "use_stitched_iterations": len(row["sources"]),
            "use_execution_unit_sources": row["sources"],
        }
    return VerifiedBundle(
        Path("/synthetic/manifest.json"), {"schema": "saea-run-manifest-v1", "status": "COMPLETED"}, None,
        tuple(outputs), trace, frozenset(parents), "FINALIZED",
    )


def test_source_order_empty_and_quarantined_windows_remain_present():
    roster = ExecutionUnitRoster((_unit("b", 0), _unit("b", 1), _unit("a", 0)))
    results = [
        _result(roster.units[0], " first "),
        _result(roster.units[1], "bad truncated text", saturated=True),
        _result(roster.units[2], "   "),
    ]
    bundle = _bundle(roster, results)
    before = deepcopy(bundle)
    windows = subject.verified_execution_unit_windows(bundle)
    assert tuple(windows) == ("b", "a")
    assert [span.text for span in windows["b"]] == ["first", ""]
    assert windows["b"][1].saturated is True
    assert windows["a"][0].text == ""
    assert windows["b"][1].start_seconds == 90
    assert windows["b"][1].execution_unit_id == "b#w0002"
    assert bundle == before


@pytest.mark.parametrize("kind", ("accepted", "terminal", "finite", "abstention"))
def test_native_selected_solver_or_abstention_is_replayed(kind):
    if kind == "accepted":
        _, phase, output, trace = _fixture()
    elif kind == "terminal":
        _, phase, output, trace = _terminal_fixture()
    else:
        _, phase, output, trace = _finite_fixture(with_solver=kind == "finite")
    episode = phase["native_episode_receipt"]
    unit = _unit("s1", 0)
    from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
        validate_native_episode_delivery_receipt,
    )
    selected = validate_native_episode_delivery_receipt(
        episode, episode["role_visits"], episode["planner_routes"],
    )
    request_id = output.get("request_id", selected.final_contact["request_id"])
    request, response = trace[request_id + "/request"], trace[request_id + "/response"]
    result = {
        **_result(unit, response["text"]), "request_id": request_id,
        "request_sha256": request["payload_sha256"], "response_sha256": response["response_sha256"],
    }
    trace[execution_unit_scope(unit.request_key) + "/s1/native-policy/native-episode"] = {
        "use_native_episode": episode,
    }
    bundle = _bundle(ExecutionUnitRoster((unit,)), [result], trace)
    span, = subject.verified_execution_unit_windows(bundle)["s1"]
    assert span.request_id == request_id
    assert span.text == output["text"].strip()
    assert span.delivery_kind == kind
    assert span.execution_unit_id == unit.request_key


@pytest.mark.parametrize("mutation", (
    "raw_text", "raw_request_hash", "source_unit", "reordered_sources",
    "use_sources", "parent_text", "roster_hash", "negative_duration",
    "missing_source_response", "mixed_delivery",
))
def test_inconsistent_delivery_custody_refuses(mutation):
    roster = ExecutionUnitRoster((_unit("a", 0), _unit("a", 1), _unit("b", 0)))
    bundle = _bundle(roster, [_result(unit, "text") for unit in roster.units])
    row = bundle.outputs_rows[0]
    delivery = row["execution_unit_delivery"]
    source = delivery["sources"][0]
    if mutation == "raw_text":
        bundle.trace_records[source["request_id"] + "/response"]["text"] = "changed"
    elif mutation == "raw_request_hash":
        bundle.trace_records[source["request_id"] + "/request"]["payload_sha256"] = _sha("changed")
    elif mutation == "source_unit":
        source["execution_unit_binding"]["parent_sample_id"] = "b"
    elif mutation == "reordered_sources":
        delivery["sources"].reverse()
    elif mutation == "use_sources":
        bundle.trace_records[row["request_id"] + "/use"]["use_execution_unit_sources"] = []
    elif mutation == "parent_text":
        row["text"] = "changed"
    elif mutation == "roster_hash":
        delivery["execution_unit_roster_sha256"] = _sha("wrong roster")
    elif mutation == "negative_duration":
        source["execution_unit_binding"]["slice_record"]["audio_seconds"] = -90
    elif mutation == "missing_source_response":
        del bundle.trace_records[source["request_id"] + "/response"]
    else:
        del bundle.outputs_rows[1]["execution_unit_delivery"]
    with pytest.raises((subject.DeliveryWindowsError, ValueError)):
        subject.verified_execution_unit_windows(bundle)


def test_unfinalized_bundle_refuses():
    roster = ExecutionUnitRoster((_unit("a", 0),))
    bundle = _bundle(roster, [_result(roster.units[0], "text")])
    with pytest.raises(subject.DeliveryWindowsError):
        subject.verified_execution_unit_windows(replace(bundle, attempt_state="OPENED"))

def test_shared_saved_score_entry_reconstructs_native_units_without_rescoring(tmp_path, monkeypatch):
    import hashlib
    import json

    from speech_aware_evidence_acquisition.analysis import e21_score_window_read as reader
    from test_e21_score_window_read import fixture

    texts = ("paid twenty", "one dollars today")
    _, score = fixture(texts)
    roster = ExecutionUnitRoster((_unit("call1", 0), _unit("call1", 1)))
    bundle = _bundle(roster, [_result(unit, text) for unit, text in zip(roster.units, texts)])

    def write(name, value):
        path = tmp_path / name
        path.write_text(json.dumps(value))
        return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    manifest = write("manifest.json", {})
    score_pin = write("score.json", score)
    receipt = write("receipt.json", {"score_result": score_pin})
    receipt["cell_id"] = "synthetic-cell"
    calls = []
    monkeypatch.setattr(reader, "verify_bundle", lambda path: bundle)

    def verify(reference, actual_bundle):
        assert reference.sha256 == receipt["sha256"]
        assert actual_bundle is bundle
        calls.append(reference)
        return {"score_result": score_pin}

    monkeypatch.setattr(reader, "verify_complete_score_receipt", verify)
    config = write("analysis.json", {
        "execution_profile": "model-free-check",
        "analysis": {"manifest": manifest, "score_receipt": receipt,
                     "expected_calls": 1, "expected_windows": 2},
    })
    result = reader.run(Path(config["path"]), tmp_path / "result.json")
    assert len(calls) == 1
    assert result["aggregate"]["errors"] == 0
    assert [row["execution_unit_id"] for row in result["rows"]] == [
        unit.request_key for unit in roster.units
    ]
    assert result["official_scorer_invocations"] == 0
    assert result["reference_loader_invocations"] == 0
    assert result["per_call"][0]["numeric_matched_shortfall"] == 0

def test_rehashed_planner_text_cannot_replace_native_solver_delivery():
    _, phase, _, trace = _fixture()
    episode = phase["native_episode_receipt"]
    unit = _unit("s1", 0)
    wrong = episode["role_visits"][-1]["execution_receipt"]["final_contact"]
    request_id = wrong["request_id"]
    response = trace[request_id + "/response"]
    result = {
        **_result(unit, response["text"]), "request_id": request_id,
        "request_sha256": wrong["request_sha256"],
        "response_sha256": wrong["response_sha256"],
    }
    trace[execution_unit_scope(unit.request_key) + "/s1/native-policy/native-episode"] = {
        "use_native_episode": episode,
    }
    bundle = _bundle(ExecutionUnitRoster((unit,)), [result], trace)
    with pytest.raises(subject.DeliveryWindowsError, match="recorded native Solver"):
        subject.verified_execution_unit_windows(bundle)


def _normalised_native_unit(raw_text="Transcript:  accepted \n  answer"):
    """An accepted native Solver unit whose episode ran the Earnings delivery
    normaliser over a raw response the rule changes (E11/E35 custody)."""
    import json

    from speech_aware_evidence_acquisition.core.base import DELIVERY_NORMALISERS
    from speech_aware_evidence_acquisition.rails import delivery_normalisers  # noqa: F401
    from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
        validate_native_episode_delivery_receipt,
    )

    _, phase, _, trace = _fixture()
    episode = phase["native_episode_receipt"]
    selected = validate_native_episode_delivery_receipt(
        episode, episode["role_visits"], episode["planner_routes"],
    )
    request_id = selected.final_contact["request_id"]
    old_hash = trace[request_id + "/response"]["response_text_sha256"]
    new_hash = _sha(raw_text)
    def swap(value):
        return json.loads(json.dumps(value).replace(old_hash, new_hash))

    episode, trace = swap(episode), swap(trace)
    trace[request_id + "/response"]["text"] = raw_text
    normalisation = DELIVERY_NORMALISERS.resolve("saea-deliver-earnings-text-v1")(raw_text)
    assert normalisation.changed
    episode["deliver_normaliser"] = dict(normalisation.receipt)
    unit = _unit("s1", 0)
    request, response = trace[request_id + "/request"], trace[request_id + "/response"]
    result = {
        **_result(unit, normalisation.text), "request_id": request_id,
        "request_sha256": request["payload_sha256"], "response_sha256": response["response_sha256"],
    }
    trace[execution_unit_scope(unit.request_key) + "/s1/native-policy/native-episode"] = {
        "use_native_episode": episode,
    }
    return unit, result, trace, episode, normalisation


def test_normalised_native_unit_is_replayed_from_its_raw_response():
    unit, result, trace, _, normalisation = _normalised_native_unit()
    bundle = _bundle(ExecutionUnitRoster((unit,)), [result], trace)
    span, = subject.verified_execution_unit_windows(bundle)["s1"]
    assert span.text == normalisation.text == "accepted answer"
    assert span.delivery_kind == "accepted"
    raw = bundle.trace_records[result["request_id"] + "/response"]["text"]
    assert raw != normalisation.text  # the raw custody is untouched


@pytest.mark.parametrize("damage", (
    "input_digest", "output_digest", "unregistered_rule", "raw_hash_as_delivery", "missing_digest",
))
def test_normalised_unit_refuses_unproven_bytes(damage):
    unit, result, trace, episode, normalisation = _normalised_native_unit()
    block = episode["deliver_normaliser"]
    if damage == "input_digest":
        block["input_sha256"] = _sha("another response")
    elif damage == "output_digest":
        block["output_sha256"] = _sha("another delivery")
    elif damage == "unregistered_rule":
        block["normaliser_id"] = "saea-deliver-unregistered-v0"
    elif damage == "missing_digest":
        del block["output_sha256"]
    else:
        raw = trace[result["request_id"] + "/response"]["text"]
        result = {**result, "text": raw, "response_text_sha256": _sha(raw)}
    bundle = _bundle(ExecutionUnitRoster((unit,)), [result], trace)
    with pytest.raises(subject.DeliveryWindowsError):
        subject.verified_execution_unit_windows(bundle)
