"""Reachable-request capacity keeps legal responses and exact wire bodies."""
import json
import pytest
from speech_aware_evidence_acquisition.analysis.native_graph_capacity import (
    bounded_response_texts, measure_captured_requests,
)
from speech_aware_evidence_acquisition.rails.review_handoff import normalize_review_handoff


def test_bounded_response_texts_keep_three_candidates_and_valid_review():
    texts, counts = bounded_response_texts(lambda s: len(s.encode()) // 4 + 1,
        targets=["media_type", "device_type"], intents=["calendar_query", "calendar_set", "calendar_remove"])
    assert all(n <= 512 for n in counts.values())
    assert len(json.loads(texts["perception"])["candidates"]) == 3
    assert all(len(c["distinction"]) <= 128 for c in json.loads(texts["perception"])["candidates"])
    assert json.loads(normalize_review_handoff(texts["reviewer"]))["status"] == "valid"
    assert len(json.loads(texts["reviewer"])["findings"]) == 4
    assert texts["solver"].startswith("intent: calendar_query")


def test_capacity_measures_exact_body_and_reserves_once(monkeypatch):
    import speech_aware_evidence_acquisition.core.preparation as p
    body = {"messages": [{"role": "user", "content": "real projected history"}], "max_tokens": 512}
    received = []
    def measure(client, actual, **kw):
        received.append((actual, kw))
        return {"required_tokens": 24000, "margin_tokens": 576, "fits": True,
                "maximum_completion_tokens": 512}
    monkeypatch.setattr(p, "measure_request", measure)
    rows = measure_captured_requests(None, [{"request": body, "sample_id": "s"}],
                                    media_marker="MEDIA", speech_max=195, reserve=2048)
    assert received[0][0] is body
    assert received[0][1]["speech_tokens"] == (195,)
    assert body["messages"] == [{"role": "user", "content": "real projected history"}]
    assert rows[0]["fits"] is False
    assert rows[0]["margin_after_structural_reserve"] == -1472
    with pytest.raises(ValueError, match="completion"):
        measure_captured_requests(None, [{"request": {**body, "max_tokens": 256}, "sample_id": "s"}],
                                  media_marker="MEDIA", speech_max=195)
