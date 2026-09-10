"""Pin a phase delivery to the actual program before any model contact."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.bundle import BundleError
from speech_aware_evidence_acquisition.core.bundle.delivery_replay import (
    canonical,
    sha256,
    validate_phase_delivery_sources,
)
from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program


def _values():
    program = default_phase_program("phase-draft-revise-v1")
    return {
        "policy": program.program_id,
        "cells": [{
            "cell_id": "generation", "model_fragment": "m",
            "dataset_fragment": "d", "baseline_fragment": "b",
        }],
        "delivery_derivatives": [{
            "cell_id": "delivered", "parent_cell_id": "generation",
            "response_postprocessor": "e21-free-refresh-delivery-v1",
            "response_postprocessor_params": {},
            "source_selector": {
                "schema": "saea-phase-response-pair-v1",
                "program_id": program.program_id,
                "program_sha256": sha256(canonical(program.as_json())),
                "predecessor_phase": "draft",
                "response_phase": "revise",
            },
        }],
    }


def test_exact_program_is_accepted_and_legacy_has_no_new_program_dependency():
    validate_phase_delivery_sources(_values())
    validate_phase_delivery_sources({"policy": "obs-repair-loop-ojw"})
    validate_phase_delivery_sources({
        "policy": "obs-repair-loop-ojw",
        "delivery_derivatives": [{
            "cell_id": "legacy", "parent_cell_id": "generation",
            "response_postprocessor": "e21-free-refresh-delivery-v1",
            "response_postprocessor_params": {},
        }],
    })


def test_execution_object_change_refuses_even_when_its_name_is_unchanged():
    program = default_phase_program("phase-draft-revise-v1")
    changed = replace(program, max_contacts=program.max_contacts + 1)
    with pytest.raises(BundleError, match="executing program"):
        validate_phase_delivery_sources(_values(), program=changed)


@pytest.mark.parametrize("bad_pin", [None, "", "0" * 64, "not-a-hash"])
def test_wrong_program_pin_refuses_before_adapter_gate_or_service(tmp_path, monkeypatch, bad_pin):
    import speech_aware_evidence_acquisition.core.flight.runtime as module

    values = _values()
    values["delivery_derivatives"][0]["source_selector"]["program_sha256"] = bad_pin
    monkeypatch.setattr(module, "compose", lambda *args: SimpleNamespace(values=values))

    def forbidden(*args, **kwargs):
        pytest.fail("Invalid program identity must refuse before data or contact setup")

    runtime = object.__new__(FlightRuntime)
    runtime._repo_root = tmp_path
    runtime._lock = None
    runtime._model, runtime._dataset, runtime._baseline, runtime._experiment = "m", "d", "b", "e"
    runtime._adapter_factory = runtime._gate_factory = runtime._session_starter = forbidden
    monkeypatch.setattr(module, "load_lock", forbidden)
    with pytest.raises(BundleError, match="program hash"):
        runtime._prepare()


def test_another_parent_delivery_does_not_block_matching_direct_control():
    values = _values()
    values["policy"] = "phase-direct-only-v1"
    control = default_phase_program(values["policy"])
    validate_phase_delivery_sources(
        values, program=control,
        parent_fragments={"model_fragment": "m", "dataset_fragment": "d", "baseline_fragment": "control"},
    )
    with pytest.raises(BundleError, match="parent policy"):
        validate_phase_delivery_sources(
            values, program=control,
            parent_fragments={"model_fragment": "m", "dataset_fragment": "d", "baseline_fragment": "b"},
        )


def test_selected_delivery_requires_an_unambiguous_parent_cell():
    values = _values()
    values["cells"] *= 2
    with pytest.raises(BundleError, match="exactly one"):
        validate_phase_delivery_sources(
            values, parent_fragments={"model_fragment": "m", "dataset_fragment": "d", "baseline_fragment": "b"},
        )


@pytest.mark.parametrize("field,value", [
    ("response_postprocessor", "unregistered-delivery"),
    ("response_postprocessor_params", {"unknown_parameter": True}),
    ("response_postprocessor_params", []),
])
def test_invalid_declared_delivery_rule_refuses_before_generation(field, value):
    values = _values()
    values["delivery_derivatives"][0][field] = value
    with pytest.raises(BundleError, match="rule"):
        validate_phase_delivery_sources(values)


@pytest.mark.parametrize("mutation", [
    "missing-cell", "unsafe-cell", "unsafe-parent", "unknown-field", "duplicate-cell",
])
def test_invalid_delivery_declaration_refuses_before_data_or_contact_setup(
    tmp_path, monkeypatch, mutation,
):
    import speech_aware_evidence_acquisition.core.flight.runtime as module

    values = _values()
    declaration = values["delivery_derivatives"][0]
    if mutation == "missing-cell":
        declaration.pop("cell_id")
    elif mutation == "unsafe-cell":
        declaration["cell_id"] = "../escape"
    elif mutation == "unsafe-parent":
        declaration["parent_cell_id"] = "../generation"
    elif mutation == "unknown-field":
        declaration["extra"] = True
    else:
        values["delivery_derivatives"].append(dict(declaration))
    monkeypatch.setattr(module, "compose", lambda *args: SimpleNamespace(values=values))

    def forbidden(*args, **kwargs):
        pytest.fail("Invalid delivery declaration must refuse before contact setup")

    runtime = object.__new__(FlightRuntime)
    runtime._repo_root = tmp_path
    runtime._lock = None
    runtime._model, runtime._dataset, runtime._baseline, runtime._experiment = "m", "d", "b", "e"
    runtime._adapter_factory = runtime._gate_factory = runtime._session_starter = forbidden
    monkeypatch.setattr(module, "load_lock", forbidden)
    with pytest.raises(BundleError, match="delivery"):
        runtime._prepare()


@pytest.mark.parametrize("mutation", ["missing-declaration", "changed-rule"])
def test_phase_delivery_cannot_hide_outside_the_actual_experiment(tmp_path, mutation):
    import json
    from speech_aware_evidence_acquisition.core.bundle.delivery_replay import (
        require_experiment_phase_declarations,
    )

    values = _values()
    declarations = validate_phase_delivery_sources(values)
    experiment = tmp_path / "configs/experiment/e.json"
    experiment.parent.mkdir(parents=True)
    document = json.loads(json.dumps(values))
    if mutation == "missing-declaration":
        document.pop("delivery_derivatives")
    else:
        document["delivery_derivatives"][0]["response_postprocessor"] = "changed-rule"
    experiment.write_text(json.dumps(document))
    with pytest.raises(BundleError, match="actual experiment fragment"):
        require_experiment_phase_declarations(
            tmp_path, "e", declarations,
            {"model_fragment": "m", "dataset_fragment": "d", "baseline_fragment": "b"},
        )
