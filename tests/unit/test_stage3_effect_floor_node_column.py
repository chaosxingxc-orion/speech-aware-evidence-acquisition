"""NX programme E1: the effect-floor gate admits ``same-flight-node-column``.

A cell declaring ``measurement_design`` ``same-flight-node-column`` with a
``template_variants`` summary is read at the same-flight CONTRAST floor
(borrowed from ``same-flight-supply-variant`` until a node-column cell measures
its own twin null). Every refusal below is raised before any contact.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from test_stage3_effect_floor_check import _build, _declaration, _kinds

import stage3_effect_floor_check as gate

SUMMARY = {"node": "solver", "candidate_arms": 3, "twin": True}


def _node_column(**overrides):
    return _declaration(
        measurement_design="same-flight-node-column",
        expected_effect_pp=2.0,
        rows=1080,
        primary_metric_key="slu",
        template_variants=dict(SUMMARY),
        **overrides,
    )


def test_the_design_is_registered_with_the_same_flight_contrast_floors():
    assert "same-flight-node-column" in gate.DESIGNS
    assert gate.floor_for("same-flight-node-column", 1080, metric="slu")[0] == pytest.approx(1.49)
    assert gate.floor_for("same-flight-node-column", 1080, metric="intent")[0] == pytest.approx(0.65)
    assert (
        gate.floor_for("same-flight-node-column", 1080, metric="slu")[0]
        == gate.floor_for("same-flight-supply-variant", 1080, metric="slu")[0]
    )
    # a per-metric design refuses a metric-blind call
    with pytest.raises(ValueError, match="per-metric floors"):
        gate.floor_for("same-flight-node-column", 1080)


def test_the_node_set_and_arm_bound_mirror_the_rails():
    from speech_aware_evidence_acquisition.rails import supply_variants as sv

    assert gate.TEMPLATE_VARIANT_NODES == sv.TEMPLATE_VARIANT_NODES
    assert gate.MIN_TEMPLATE_CANDIDATE_ARMS == sv.MIN_TEMPLATE_CANDIDATE_ARMS
    assert gate.MAX_TEMPLATE_CANDIDATE_ARMS == sv.MAX_TEMPLATE_CANDIDATE_ARMS


def test_a_node_column_cell_above_the_floor_is_accepted(tmp_path: Path):
    _build(tmp_path, declaration=_node_column(), registered_date="2026-10-10")
    data = gate.evaluate(tmp_path)
    assert data["findings"] == [] and data["passed"] is True
    declaration = data["in_scope_cells"][0]["declaration"]
    assert declaration["measurement_design"] == "same-flight-node-column"
    assert declaration["template_variants"] == SUMMARY


def test_a_node_column_cell_below_the_floor_is_refused(tmp_path: Path):
    _build(
        tmp_path,
        declaration=_node_column() | {"expected_effect_pp": 1.0},
        registered_date="2026-10-10",
    )
    data = gate.evaluate(tmp_path)
    assert _kinds(data) == ["effect-below-floor"]
    assert "1.4900 pp" in data["findings"][0]["message"]


def test_a_node_column_cell_must_say_which_metric_it_means(tmp_path: Path):
    declaration = _node_column()
    del declaration["primary_metric_key"]
    _build(tmp_path, declaration=declaration, registered_date="2026-10-10")
    data = gate.evaluate(tmp_path)
    assert _kinds(data) == ["primary-metric-key-missing"]


def test_a_node_column_cell_under_200_rows_may_only_prove_form(tmp_path: Path):
    _build(
        tmp_path,
        declaration=_node_column() | {"rows": 4},
        registered_date="2026-10-10",
        rows=4,
    )
    assert "underpowered-benefit-claim" in _kinds(gate.evaluate(tmp_path))
    form_root = tmp_path / "form"
    form_root.mkdir()
    _build(
        form_root,
        declaration=_node_column() | {"rows": 4, "claims_benefit": False, "expected_effect_pp": 0.0},
        registered_date="2026-10-10",
        rows=4,
    )
    assert _kinds(gate.evaluate(form_root)) == []


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda d: d.pop("template_variants"), "requires a template_variants block"),
        (lambda d: d["template_variants"].update(node="reviewer"), "may sit only at"),
        (lambda d: d["template_variants"].update(candidate_arms=0), "from 1 to 6"),
        (lambda d: d["template_variants"].update(candidate_arms=7), "from 1 to 6"),
        (lambda d: d["template_variants"].update(candidate_arms=True), "from 1 to 6"),
        (lambda d: d["template_variants"].update(twin="yes"), "true or false"),
        (lambda d: d["template_variants"].update(extra=1), "must be exactly"),
        (lambda d: d["template_variants"].pop("twin"), "must be exactly"),
        (lambda d: d.update(template_variants="solver"), "must be exactly"),
        (lambda d: d.update(measurement_design="same-flight-supply-variant"), "node-template column read"),
    ],
)
def test_a_malformed_template_variants_block_is_unparsable(tmp_path: Path, mutate, message):
    declaration = _node_column()
    mutate(declaration)
    _build(tmp_path, declaration=declaration, registered_date="2026-10-10")
    data = gate.evaluate(tmp_path)
    assert _kinds(data) == ["unparsable-declaration"]
    assert message in data["findings"][0]["message"]
    assert data["passed"] is False


def test_the_summary_is_read_from_every_legal_place(tmp_path: Path):
    for where in ("registered-facts", "preregistration", "fragment"):
        root = tmp_path / where
        root.mkdir()
        _build(root, declaration=_node_column(), declaration_in=where, registered_date="2026-10-10")
        data = gate.evaluate(root)
        assert data["findings"] == [], where


def test_explain_lists_the_new_design(tmp_path: Path, capsys):
    _build(tmp_path, declaration=_node_column(), registered_date="2026-10-10")
    gate.main(["--repo-root", str(tmp_path), "--explain"])
    assert "same-flight-node-column" in capsys.readouterr().out


# Decision 338: the sampling column's ``variant_kind``.
def test_the_sampling_variant_kinds_are_accepted_with_a_twin(tmp_path: Path):
    for kind in ("perception-sampling", "solver-sampling"):
        _build(tmp_path / kind, declaration=_node_column(variant_kind=kind), registered_date="2026-10-19")
        data = gate.evaluate(tmp_path / kind)
        assert data["findings"] == [] and data["passed"] is True
        assert data["in_scope_cells"][0]["declaration"]["variant_kind"] == kind


def test_a_sampling_kind_without_a_twin_and_an_unknown_kind_are_refused(tmp_path: Path):
    no_twin = _declaration(
        measurement_design="same-flight-node-column", expected_effect_pp=2.0, rows=1080, primary_metric_key="slu",
        template_variants={"node": "perception", "candidate_arms": 2, "twin": False}, variant_kind="perception-sampling",
    )
    _build(tmp_path / "a", declaration=no_twin, registered_date="2026-10-19")
    assert gate.evaluate(tmp_path / "a")["passed"] is False
    _build(tmp_path / "b", declaration=_node_column(variant_kind="made-up-kind"), registered_date="2026-10-19")
    assert gate.evaluate(tmp_path / "b")["passed"] is False
