"""Registered native Audio2Tool Perception-state response format."""

from __future__ import annotations

import csv

import pytest
from jsonschema import ValidationError
from jsonschema.validators import validator_for

from speech_aware_evidence_acquisition.core.base import RESPONSE_FORMATS
from speech_aware_evidence_acquisition.rails.controllers import (
    register_response_formats_v1,
)

from speech_aware_evidence_acquisition.rails.a2t_response_schema import (
    A2tResponseSchemaError,
    audio2tool_perception_state_response_format,
)


register_response_formats_v1()


_TOOL_NAMES = ("setLight", "setColor", "dimLight", "getLight")


@pytest.fixture
def pinned_registry(tmp_path):
    root = tmp_path / "data"
    carrier = root / "datasets" / "audio2tool"
    carrier.mkdir(parents=True)
    path = carrier / "tools_registry.csv"
    fields = (
        "tool_id",
        "domain",
        "category",
        "tool_name",
        "signature",
        "description",
        "argument_defaults",
        "argument_constraints",
    )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, name in enumerate(_TOOL_NAMES, start=1):
            writer.writerow(
                {
                    "tool_id": index,
                    "domain": "smart_home",
                    "category": "lighting",
                    "tool_name": name,
                    "signature": f"{name}()",
                    "description": "Synthetic public registry row.",
                    "argument_defaults": "",
                    "argument_constraints": "",
                }
            )
    lock = {
        "asset_catalog": [
            {
                "name": "audio2tool",
                "kind": "dataset",
                "local_subdir": "datasets/audio2tool",
            }
        ]
    }
    return lock, root


def _validator(response_format):
    schema = response_format["json_schema"]["schema"]
    cls = validator_for(schema)
    cls.check_schema(schema)
    return cls(schema)


def _action(action_id, candidates):
    return {
        "action_id": action_id,
        "candidate_tools": candidates,
        "evidence": "José requested a lighting change.",
        "uncertain_arguments": ["room", "colour"],
    }


def test_registered_public_factory_accepts_order_repeats_large_state_and_no_actions(
    pinned_registry,
):
    lock, root = pinned_registry
    factory = RESPONSE_FORMATS.resolve("audio2tool-perception-state-v1")
    response_format = factory(
        lock,
        root,
        max_actions=6,
        max_candidates_per_action=5,
    )

    assert response_format["json_schema"]["name"] == "audio2tool_perception_state"
    validator = _validator(response_format)
    actions = [
        _action(
            f"turn:{index}",
            ["setLight", "setColor", "setLight", "dimLight"],
        )
        for index in range(5)
    ]
    validator.validate(
        {
            "actions": actions,
            "global_constraints": ["Preserve the spoken order."],
        }
    )
    validator.validate({"actions": [], "global_constraints": []})

    # JSON Schema cannot express uniqueness of one field across objects.
    # The parser enforces unique occurrence IDs after constrained decoding.
    validator.validate(
        {
            "actions": [
                _action("turn:1", ["setLight"]),
                _action("turn:1", ["setColor"]),
            ],
            "global_constraints": [],
        }
    )


@pytest.mark.parametrize(
    "document",
    [
        {
            "actions": [_action("turn:1", ["notRegistered"])],
            "global_constraints": [],
        },
        {
            "actions": [_action("bad id", ["setLight"])],
            "global_constraints": [],
        },
        {
            "actions": [
                {
                    **_action("turn:1", ["setLight"]),
                    "confidence": 0.5,
                }
            ],
            "global_constraints": [],
        },
        {
            "actions": [_action("turn:1", [])],
            "global_constraints": [],
        },
        {"actions": [], "global_constraints": [], "answer": "forbidden"},
    ],
)
def test_registered_schema_rejects_illegal_tools_ids_and_wrong_fields(
    pinned_registry, document
):
    lock, root = pinned_registry
    factory = RESPONSE_FORMATS.resolve("audio2tool-perception-state-v1")
    validator = _validator(
        factory(
            lock,
            root,
            max_actions=5,
            max_candidates_per_action=4,
        )
    )
    with pytest.raises(ValidationError):
        validator.validate(document)


@pytest.mark.parametrize(
    "params",
    [
        {"max_actions": 0, "max_candidates_per_action": 4},
        {"max_actions": True, "max_candidates_per_action": 4},
        {"max_actions": 5, "max_candidates_per_action": 0},
        {"max_actions": 5, "max_candidates_per_action": False},
    ],
)
def test_registered_factory_rejects_invalid_explicit_bounds(pinned_registry, params):
    lock, root = pinned_registry
    factory = RESPONSE_FORMATS.resolve("audio2tool-perception-state-v1")
    with pytest.raises(A2tResponseSchemaError, match="positive integers"):
        factory(lock, root, **params)


def test_registered_factory_requires_exact_supported_params(pinned_registry):
    lock, root = pinned_registry
    factory = RESPONSE_FORMATS.resolve("audio2tool-perception-state-v1")
    with pytest.raises(TypeError):
        factory(
            lock,
            root,
            max_actions=5,
            max_candidates_per_action=4,
            top_k=3,
        )
    with pytest.raises(TypeError):
        factory(lock, root, max_actions=5)


def test_builder_rejects_invalid_authoritative_inventory():
    rows = (
        {"tool_name": "validTool"},
        {"tool_name": "validTool"},
    )
    with pytest.raises(A2tResponseSchemaError, match="duplicate tool"):
        audio2tool_perception_state_response_format(
            rows,
            max_actions=5,
            max_candidates_per_action=4,
        )
