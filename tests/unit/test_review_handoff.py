"""Reviewer handoffs retain criticism and never manufacture tool evidence."""
import json
from speech_aware_evidence_acquisition.rails.review_handoff import normalize_review_handoff


def test_normalize_deduplicate_and_preserve_uncertainty():
    finding = {"kind": "boundary", "slot_types": ["event_time", "event_time"],
               "draft_fragment": " tomorrow ", "reason": " Check whether the date belongs in this field. "}
    raw = json.dumps({"findings": [finding, finding], "checked": ["type meaning", "type meaning"]})
    out = json.loads(normalize_review_handoff(raw))
    assert out["status"] == "valid"
    assert len(out["findings"]) == 1
    assert out["findings"][0]["slot_types"] == ["event_time"]
    assert out["findings"][0]["draft_fragment"] == "tomorrow"
    assert out["evidence_kind"] == "model-criticism"
    assert out["checked"] == ["type meaning"]


def test_invalid_never_becomes_accept_or_answer():
    for raw in ['not JSON', '{"answer": "calendar_set"}', '{"findings": [], "checked": [], "gold": "x"}']:
        out = json.loads(normalize_review_handoff(raw))
        assert out["status"] == "invalid"
        assert out["findings"] == []
        assert "answer" not in out


def test_empty_is_valid_but_not_a_correctness_claim():
    out = json.loads(normalize_review_handoff('{"findings": [], "checked": []}'))
    assert out["status"] == "valid"
    assert out["evidence_kind"] == "model-criticism"


def test_schema_and_bounds_refuse_unsupported_findings():
    good = {"kind": "existence", "slot_types": ["x"], "draft_fragment": "", "reason": "uncertain"}
    for patch in [{"kind": "correct_answer"}, {"slot_types": ["a", "b", "c"]}, {"reason": "x"*513}]:
        raw = json.dumps({"findings": [{**good, **patch}], "checked": []})
        assert json.loads(normalize_review_handoff(raw))["status"] == "invalid"
