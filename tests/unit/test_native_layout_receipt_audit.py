"""Check layout acceptance against original request and independently pinned FIT."""
import copy
import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.analysis.system_wire_context import verify_role_query_layout_receipt
from speech_aware_evidence_acquisition.core.preparation import canonical_bytes, digest
from test_native_evidence_projection_transport import _feature_payload, _prepare_feature_transport
from test_raw_native_transport import _raw_framework_payload, _transport


def example(tmp_path):
    payload, _, _ = _raw_framework_payload(tmp_path)
    transport = _transport(tmp_path)
    transport._native_role_query_placement = "before-speech-v1"
    request = canonical_bytes(payload)
    body, receipt = transport.render_request_with_receipt(request)
    return request, body, receipt


def test_accepts_exact_source_and_reports_only_structural_identity(tmp_path):
    request, body, receipt = example(tmp_path)
    original = copy.deepcopy((body, receipt))
    checked = verify_role_query_layout_receipt(request, body, receipt, fitted_body_sha256=digest(body))
    assert checked["verified"] is True
    assert checked["role_id"] == receipt["role_query_layout"]["role_id"]
    assert checked["request_body_sha256"] == digest(body)
    assert "messages" not in checked and "content" not in checked
    assert (body, receipt) == original


def test_accepts_combined_evidence_projection_receipt(tmp_path, monkeypatch):
    transport, _ = _prepare_feature_transport(tmp_path, monkeypatch)
    transport._native_role_query_placement = "before-speech-v1"
    request = canonical_bytes(_feature_payload())
    body, receipt = transport.render_request_with_receipt(request)
    assert receipt["policy_id"]
    assert verify_role_query_layout_receipt(
        request, body, receipt, fitted_body_sha256=digest(body))["verified"]


@pytest.mark.parametrize("field", ["input_request_id", "input_request_bytes_sha256", "rendered_body_canonical_sha256"])
def test_refuses_transplanted_outer_binding(tmp_path, field):
    request, body, receipt = example(tmp_path)
    receipt[field] = "foreign"
    with pytest.raises(ValueError, match="binding"):
        verify_role_query_layout_receipt(request, body, receipt, fitted_body_sha256=digest(body))


@pytest.mark.parametrize("field", ["schema", "placement", "role_id", "sample_id", "contact_id", "source_control_sha256", "role_query_sha256"])
def test_refuses_transplanted_layout_identity(tmp_path, field):
    request, body, receipt = example(tmp_path)
    receipt["role_query_layout"][field] = "foreign"
    with pytest.raises(ValueError, match="layout"):
        verify_role_query_layout_receipt(request, body, receipt, fitted_body_sha256=digest(body))


@pytest.mark.parametrize("change", ["system", "authority", "position", "query", "empty", "shape"])
def test_refuses_wrong_actual_placement_even_with_rehashed_body(tmp_path, change):
    request, body, receipt = example(tmp_path)
    if change == "system":
        body["messages"][0]["content"] += " Changed."
    elif change == "authority":
        body["messages"][1]["role"] = "system"
    elif change == "position":
        body["messages"][1]["content"].reverse()
    elif change == "query":
        body["messages"][1]["content"][0]["text"] += " Changed."
    elif change == "empty":
        body["messages"][1]["content"] = []
    else:
        body["messages"] = {}
    receipt["rendered_body_canonical_sha256"] = digest(body)
    with pytest.raises(ValueError, match="placement"):
        verify_role_query_layout_receipt(request, body, receipt, fitted_body_sha256=digest(body))


def test_requires_original_independently_pinned_fit_hash(tmp_path):
    request, body, receipt = example(tmp_path)
    with pytest.raises(ValueError, match="FIT"):
        verify_role_query_layout_receipt(request, body, receipt, fitted_body_sha256="0" * 64)


@pytest.mark.parametrize("change", ["control_sha", "no_framework", "invalid_framework", "no_identity", "not_object"])
def test_refuses_unbound_source_even_if_outer_receipt_is_rehashed(tmp_path, change):
    request, body, receipt = example(tmp_path)
    payload = json.loads(request)
    if change == "control_sha":
        payload["history"][-1]["content_sha256"] = "0" * 64
        receipt["role_query_layout"]["source_control_sha256"] = "0" * 64
    elif change == "no_framework":
        payload["history"] = []
    elif change == "invalid_framework":
        control = json.loads(payload["history"][-1]["content"])
        control["sample_id"] = "foreign"
        payload["history"][-1]["content"] = json.dumps(control)
    elif change == "no_identity":
        payload.pop("request_id")
        receipt["input_request_id"] = None
    else:
        payload = []
    request = canonical_bytes(payload)
    receipt["input_request_bytes_sha256"] = hashlib.sha256(request).hexdigest()
    with pytest.raises(ValueError):
        verify_role_query_layout_receipt(request, body, receipt, fitted_body_sha256=digest(body))


@pytest.mark.parametrize("receipt", [None, {}, {"role_query_layout": []}])
def test_refuses_missing_receipt(tmp_path, receipt):
    request, body, _ = example(tmp_path)
    with pytest.raises(ValueError):
        verify_role_query_layout_receipt(request, body, receipt, fitted_body_sha256=digest(body))
