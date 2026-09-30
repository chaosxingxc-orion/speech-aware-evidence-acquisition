"""Policy-space document validation on synthetic documents."""

from __future__ import annotations

import json

import pytest

from speech_aware_evidence_acquisition.analysis.sealed_credit import policy_space as ps


def _doc(**overrides):
    base = {
        "schema": "saea-sealed-credit-policy-space-v1",
        "knobs": [
            {
                "id": "phase_supply.k", "node": "solver_supply", "route": "phase_supply", "tail": ["k"],
                "estimator": "conversion_estimate", "flown_value": 20,
                "values": [{"value": 10, "conversion_source": {"type": "pool_pair_delta", "pools": ["b", "a"]}}],
            },
        ],
    }
    base.update(overrides)
    return base


def _write(path, doc):
    path.write_text(json.dumps(doc), encoding="utf-8")


def test_load_valid(tmp_path):
    path = tmp_path / "ps.json"
    _write(path, _doc())
    doc = ps.load_policy_space(path)
    assert doc["knobs"][0]["id"] == "phase_supply.k"


def test_load_missing_schema(tmp_path):
    path = tmp_path / "ps.json"
    _write(path, {"knobs": []})
    with pytest.raises(ps.PolicySpaceError):
        ps.load_policy_space(path)


def test_load_unknown_estimator(tmp_path):
    path = tmp_path / "ps.json"
    doc = _doc()
    doc["knobs"][0]["estimator"] = "not-an-estimator"
    _write(path, doc)
    with pytest.raises(ps.PolicySpaceError):
        ps.load_policy_space(path)


def test_excluded_knob_with_values_refused(tmp_path):
    path = tmp_path / "ps.json"
    doc = _doc()
    doc["knobs"][0]["estimator"] = "excluded"
    doc["knobs"][0]["excluded_reason"] = "closed"
    # values still present -- refused
    _write(path, doc)
    with pytest.raises(ps.PolicySpaceError):
        ps.load_policy_space(path)


def test_unknown_source_type_refused(tmp_path):
    path = tmp_path / "ps.json"
    doc = _doc()
    doc["knobs"][0]["values"][0]["conversion_source"] = {"type": "not-a-real-type"}
    _write(path, doc)
    with pytest.raises(ps.PolicySpaceError):
        ps.load_policy_space(path)


def test_supply_variant_route_validation_accepts_admitted_tail():
    doc = _doc()
    validated = ps.validate_supply_variant_routes(doc)
    assert validated == ["phase_supply.k"]


def test_supply_variant_route_validation_rejects_bad_tail():
    doc = _doc()
    doc["knobs"][0]["tail"] = ["not_a_real_tail"]
    with pytest.raises(ps.PolicySpaceError):
        ps.validate_supply_variant_routes(doc)


def test_non_tuning_source_refused():
    doc = _doc()
    with pytest.raises(ps.PolicySpaceError):
        ps.validate_tuning_sources(doc, tuning_pool_labels={"a"})  # "b" is missing
    ps.validate_tuning_sources(doc, tuning_pool_labels={"a", "b"})  # both present: no raise


def test_value_status_is_validated(tmp_path):
    """run 3: optional value-level status must be open / admitted / closed."""
    doc = _doc()
    doc["knobs"][0]["values"][0]["status"] = "closed"
    path = tmp_path / "ps.json"
    _write(path, doc)
    assert ps.load_policy_space(path)["knobs"][0]["values"][0]["status"] == "closed"
    doc["knobs"][0]["values"][0]["status"] = "retired"
    _write(path, doc)
    with pytest.raises(ps.PolicySpaceError):
        ps.load_policy_space(path)
