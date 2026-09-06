"""Tests for the OpenAI-format tool schema renderer (D1a).

Real-registry coverage (152/152) runs when ``SPEECHRL_DATA_DIR`` and the
materialized ``audio2tool`` asset are actually available (skipped
otherwise); every other test exercises the SAME rendering logic either via
the shared ``audio2tool_world`` synthetic on-disk registry fixture (real
``load_tool_registry`` code path, tiny fixture CSV) or via a monkeypatched
``load_tool_registry`` (full control over row shapes, including malformed
ones a real registry never contains).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.data import audio2tool_tools as module
from speech_aware_evidence_acquisition.data.audio2tool_tools import (
    Audio2ToolSchemaError,
    _build_tool_schema,
    _parse_constraints,
    _parse_defaults,
    _parse_signature,
    openai_tools_sha256,
    render_openai_tools,
    render_registry_compact,
    render_registry_compact_rows,
)
from speech_aware_evidence_acquisition.data.lock import AssetResolutionError, load_lock


def _row(
    *,
    tool_id="0",
    domain="d",
    category="c",
    tool_name="doThing",
    signature="doThing()",
    description="does the thing",
    argument_defaults="",
    argument_constraints="",
):
    return {
        "tool_id": tool_id,
        "domain": domain,
        "category": category,
        "tool_name": tool_name,
        "signature": signature,
        "description": description,
        "argument_defaults": argument_defaults,
        "argument_constraints": argument_constraints,
    }


# ---------------------------------------------------------------------------
# Signature parsing
# ---------------------------------------------------------------------------


def test_parse_signature_zero_params():
    assert _parse_signature("foo", "foo()") == []


def test_parse_signature_multiple_params_with_optional_marker():
    params = _parse_signature(
        "setLighting",
        "setLighting(deviceId: String, state: OnOff, level: Int?, color: HexCode?)",
    )
    assert params == [
        ("deviceId", "String", False),
        ("state", "OnOff", False),
        ("level", "Int", True),
        ("color", "HexCode", True),
    ]


def test_parse_signature_accepts_generic_list_type():
    params = _parse_signature("startCleaning", "startCleaning(zones: List<String>?)")
    assert params == [("zones", "List<String>", True)]


def test_parse_signature_rejects_name_mismatch():
    with pytest.raises(ValueError):
        _parse_signature("bar", "foo()")


def test_parse_signature_rejects_malformed_parameter():
    with pytest.raises(ValueError):
        _parse_signature("foo", "foo(not a param)")


def test_parse_signature_rejects_duplicate_parameter_names():
    with pytest.raises(ValueError):
        _parse_signature("foo", "foo(x: Int, x: Int)")


def test_parse_signature_rejects_unbalanced_parens():
    with pytest.raises(ValueError):
        _parse_signature("foo", "foo(x: Int")


# ---------------------------------------------------------------------------
# Defaults parsing (quote-aware split)
# ---------------------------------------------------------------------------


def test_parse_defaults_quoted_value_with_embedded_comma_stays_one_token():
    """The real setColor row's own default -- the one row in
    tools_registry.csv whose quoted default VALUE itself contains a comma."""

    defaults = _parse_defaults("deviceId='light_1', color='0,0,100'")
    assert defaults == {"deviceId": "light_1", "color": "0,0,100"}


def test_parse_defaults_null_and_object_and_bool_and_numeric():
    defaults = _parse_defaults("a=null, b={}, c=True, d=20.0, e=5")
    assert defaults == {"a": "null", "b": "{}", "c": "True", "d": "20.0", "e": "5"}


def test_parse_defaults_empty_text():
    assert _parse_defaults("") == {}
    assert _parse_defaults("   ") == {}


def test_parse_defaults_rejects_malformed_entry():
    with pytest.raises(ValueError):
        _parse_defaults("not an assignment")


# ---------------------------------------------------------------------------
# Constraint parsing
# ---------------------------------------------------------------------------


def test_parse_constraints_multiple_brackets():
    constraints = _parse_constraints(
        "zone: [Driver, Passenger, Rear_Left, Rear_Right], temperature: [15.0-30.0]"
    )
    assert constraints == {
        "zone": "Driver, Passenger, Rear_Left, Rear_Right",
        "temperature": "15.0-30.0",
    }


def test_parse_constraints_empty_text():
    assert _parse_constraints("") == {}


# ---------------------------------------------------------------------------
# Full per-row schema building (_build_tool_schema) -- every registry shape
# ---------------------------------------------------------------------------


def test_build_tool_schema_zero_param_tool():
    schema = _build_tool_schema(_row(tool_name="ventWindows", signature="ventWindows()"))
    assert schema == {
        "type": "function",
        "function": {
            "name": "ventWindows",
            "description": "does the thing",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    }


def test_build_tool_schema_enum_and_range_and_default_text_never_a_schema_default():
    row = _row(
        tool_name="setZoneTemperature",
        signature="setZoneTemperature(zone: Zone, temperature: Float)",
        argument_defaults="zone='Driver', temperature=20.0",
        argument_constraints=(
            "zone: [Driver, Passenger, Rear_Left, Rear_Right], temperature: [15.0-30.0]"
        ),
    )
    schema = _build_tool_schema(row)
    props = schema["function"]["parameters"]["properties"]
    assert props["zone"] == {
        "type": "string",
        "enum": ["Driver", "Passenger", "Rear_Left", "Rear_Right"],
        "description": "type: Zone; default: Driver",
    }
    assert props["temperature"] == {
        "type": "number",
        "minimum": 15.0,
        "maximum": 30.0,
        "description": "type: Float; default: 20.0",
    }
    # Tier 1 is argument-free: the registry default is named ONLY in the
    # description text, never populated as a JSON-schema "default".
    assert "default" not in props["zone"]
    assert "default" not in props["temperature"]
    assert schema["function"]["parameters"]["required"] == []


def test_build_tool_schema_required_parameter_has_no_default_entry():
    """No real tools_registry.csv row has a required parameter (every real
    parameter carries a default -- Tier 1 is argument-free by the paper's
    own protocol, confirmed against the real 152-row registry), so this path
    is exercised only by a synthetic row."""

    row = _row(
        tool_name="doThing",
        signature="doThing(target: String)",
        argument_defaults="",
        argument_constraints="",
    )
    schema = _build_tool_schema(row)
    assert schema["function"]["parameters"]["required"] == ["target"]
    assert schema["function"]["parameters"]["properties"]["target"] == {
        "type": "string",
        "description": "type: String",
    }


def test_build_tool_schema_mixed_required_and_defaulted_parameters_preserve_order():
    row = _row(
        tool_name="mixedThing",
        signature="mixedThing(a: String, b: Int, c: Boolean)",
        argument_defaults="b=5",
        argument_constraints="",
    )
    schema = _build_tool_schema(row)
    assert list(schema["function"]["parameters"]["properties"]) == ["a", "b", "c"]
    assert schema["function"]["parameters"]["required"] == ["a", "c"]


def test_build_tool_schema_boolean_ignores_its_constraint_bracket():
    row = _row(
        tool_name="setSteeringWheelHeat",
        signature="setSteeringWheelHeat(enabled: Boolean)",
        argument_defaults="enabled=False",
        argument_constraints="enabled: [True, False]",
    )
    schema = _build_tool_schema(row)
    prop = schema["function"]["parameters"]["properties"]["enabled"]
    assert prop == {"type": "boolean", "description": "type: Boolean; default: False"}
    assert "enum" not in prop
    assert "minimum" not in prop


def test_build_tool_schema_list_constraint_attaches_to_items_not_the_array():
    row = _row(
        tool_name="setAlarm",
        signature="setAlarm(repeat: List<String>?)",
        argument_defaults="repeat=null",
        argument_constraints="repeat: [Daily, Weekdays, Weekends, Once]",
    )
    schema = _build_tool_schema(row)
    prop = schema["function"]["parameters"]["properties"]["repeat"]
    assert prop["type"] == "array"
    assert prop["items"] == {
        "type": "string",
        "enum": ["Daily", "Weekdays", "Weekends", "Once"],
    }
    assert "enum" not in prop
    assert prop["description"] == "type: List<String>?; default: null"
    # Optional (has a default) -> excluded from required regardless of "?".
    assert schema["function"]["parameters"]["required"] == []


def test_build_tool_schema_optional_marker_does_not_by_itself_decide_required():
    """setAlarm's real 'label: String?' has a NON-null default ('Wake Up'):
    required tracks presence-of-default only, independent of '?'."""

    row = _row(
        tool_name="setAlarm",
        signature="setAlarm(label: String?)",
        argument_defaults="label='Wake Up'",
        argument_constraints="",
    )
    schema = _build_tool_schema(row)
    assert schema["function"]["parameters"]["required"] == []
    assert schema["function"]["parameters"]["properties"]["label"]["description"] == (
        "type: String?; default: Wake Up"
    )


def test_build_tool_schema_map_type_maps_to_object():
    row = _row(
        tool_name="setThermostatSchedule",
        signature="setThermostatSchedule(schedule: Map)",
        argument_defaults="schedule={}",
        argument_constraints="",
    )
    schema = _build_tool_schema(row)
    prop = schema["function"]["parameters"]["properties"]["schedule"]
    assert prop == {"type": "object", "description": "type: Map; default: {}"}


def test_build_tool_schema_compound_constraint_body_is_a_described_string_not_an_enum():
    """HsbColor's real constraint body ("Hue:0-360, Sat:0-100, Bri:0-100")
    describes the fields of one composite value, so it must render as a free
    string whose format is stated in the description -- never as an enum of
    the field labels, which would steer the model to emit "Hue:0-360"."""

    row = _row(
        tool_name="setColor",
        signature="setColor(color: HsbColor)",
        argument_defaults="color='0,0,100'",
        argument_constraints="color: [Hue:0-360, Sat:0-100, Bri:0-100]",
    )
    schema = _build_tool_schema(row)
    prop = schema["function"]["parameters"]["properties"]["color"]
    assert prop["type"] == "string"
    assert "enum" not in prop
    assert prop["type"] == "string"
    assert prop["description"] == "type: HsbColor; format: Hue:0-360, Sat:0-100, Bri:0-100; default: 0,0,100"


def test_build_tool_schema_negative_and_spaced_numeric_range():
    row = _row(
        tool_name="setMirrorAngle",
        signature="setMirrorAngle(x: Int)",
        argument_defaults="x=0",
        argument_constraints="x: [-10 - 10]",
    )
    schema = _build_tool_schema(row)
    prop = schema["function"]["parameters"]["properties"]["x"]
    assert prop["minimum"] == -10
    assert prop["maximum"] == 10


def test_build_tool_schema_zero_padded_numeric_range():
    row = _row(
        tool_name="setSecureStorageAccess",
        signature="setSecureStorageAccess(pin: Int?)",
        argument_defaults="pin=null",
        argument_constraints="pin: [0000-9999]",
    )
    schema = _build_tool_schema(row)
    prop = schema["function"]["parameters"]["properties"]["pin"]
    assert prop["minimum"] == 0
    assert prop["maximum"] == 9999


def test_build_tool_schema_string_type_can_carry_an_enum():
    row = _row(
        tool_name="searchPOI",
        signature="searchPOI(category: String)",
        argument_defaults="category='Food'",
        argument_constraints="category: [Food, Charging, Parking, Hotel, Entertainment]",
    )
    schema = _build_tool_schema(row)
    prop = schema["function"]["parameters"]["properties"]["category"]
    assert prop["type"] == "string"
    assert prop["enum"] == ["Food", "Charging", "Parking", "Hotel", "Entertainment"]


# ---------------------------------------------------------------------------
# render_openai_tools orchestration: ordering, determinism, fail-closed
# ---------------------------------------------------------------------------


def _synthetic_registry():
    return (
        _row(tool_id="0", tool_name="ventWindows", signature="ventWindows()"),
        _row(
            tool_id="1",
            tool_name="setZoneTemperature",
            signature="setZoneTemperature(zone: Zone, temperature: Float)",
            argument_defaults="zone='Driver', temperature=20.0",
            argument_constraints=(
                "zone: [Driver, Passenger, Rear_Left, Rear_Right], temperature: [15.0-30.0]"
            ),
        ),
        _row(
            tool_id="2",
            tool_name="setFanSpeed",
            signature="setFanSpeed(level: Int)",
            argument_defaults="level=5",
            argument_constraints="level: [1-10]",
        ),
    )


def test_render_openai_tools_synthetic_registry_deterministic_order_and_hash(monkeypatch):
    monkeypatch.setattr(module, "load_tool_registry", lambda lock, root: _synthetic_registry())
    tools_a = render_openai_tools({}, Path("/unused"))
    tools_b = render_openai_tools({}, Path("/unused"))
    assert tools_a == tools_b
    assert [t["function"]["name"] for t in tools_a] == [
        "ventWindows",
        "setZoneTemperature",
        "setFanSpeed",
    ]
    assert all(t["type"] == "function" for t in tools_a)
    assert openai_tools_sha256(tools_a) == openai_tools_sha256(tools_b)
    # sha256 is sensitive to the actual tool set.
    assert openai_tools_sha256(tools_a) != openai_tools_sha256(tools_a[:-1])


def test_render_openai_tools_fails_closed_on_unparsable_signature_reporting_tool_name(
    monkeypatch,
):
    bad_rows = (
        _row(tool_id="0", tool_name="good", signature="good()"),
        _row(tool_id="1", tool_name="bad", signature="bad(this is not a param list"),
    )
    monkeypatch.setattr(module, "load_tool_registry", lambda lock, root: bad_rows)
    with pytest.raises(Audio2ToolSchemaError) as excinfo:
        render_openai_tools({}, Path("/unused"))
    message = str(excinfo.value)
    assert "1/2" in message
    assert "bad" in message
    assert "good" not in message.split(":", 1)[1]  # only the FAILING tool is named


# ---------------------------------------------------------------------------
# End-to-end over the shared synthetic on-disk registry fixture (real
# load_tool_registry code path -- the "synthetic ... registry when the data
# root is available" case for a data root that IS available, just not the
# real 152-row one).
# ---------------------------------------------------------------------------


def test_render_openai_tools_over_the_shared_synthetic_carrier_fixture(audio2tool_world):
    lock = load_lock(audio2tool_world.lock_path)
    tools = render_openai_tools(lock, audio2tool_world.data_root)
    # audio2tool_world's tools_registry.csv carries exactly two rows,
    # tool_id 2 (setLighting) before tool_id 10 (setSecurityMode) --
    # registry (tool_id) order, not file order.
    assert [t["function"]["name"] for t in tools] == ["setLighting", "setSecurityMode"]
    lighting = tools[0]["function"]["parameters"]["properties"]
    assert lighting["deviceId"] == {
        "type": "string",
        "description": "type: String; default: light_1",
    }
    security = tools[1]["function"]["parameters"]["properties"]
    assert security["mode"] == {
        "type": "string",
        "enum": ["Home", "Armed_Away"],
        "description": "type: Mode; default: Home",
    }
    assert render_openai_tools(lock, audio2tool_world.data_root) == tools
    assert openai_tools_sha256(tools) == openai_tools_sha256(
        render_openai_tools(lock, audio2tool_world.data_root)
    )


# ---------------------------------------------------------------------------
# Real registry (152/152), when the data root/lock are actually available.
# ---------------------------------------------------------------------------


def _real_lock_and_root():
    from speech_aware_evidence_acquisition.data.audio2tool import AUDIO2TOOL_LOCK_KEY
    from speech_aware_evidence_acquisition.data.lock import (
        asset_dir,
        data_root,
        umbrella_lock_path,
    )

    try:
        root = data_root()
        lock = load_lock(umbrella_lock_path())
        carrier_dir = asset_dir(lock, AUDIO2TOOL_LOCK_KEY, root)
        if not (carrier_dir / "tools_registry.csv").is_file():
            return None
        return lock, root
    except (AssetResolutionError, OSError):
        return None


_REAL = _real_lock_and_root()


@pytest.mark.skipif(_REAL is None, reason="real audio2tool registry not available on this host")
def test_render_openai_tools_real_registry_is_152_of_152():
    lock, root = _REAL
    tools = render_openai_tools(lock, root)
    assert len(tools) == 152
    names = [t["function"]["name"] for t in tools]
    assert len(set(names)) == 152
    # deterministic across calls
    assert render_openai_tools(lock, root) == tools
    assert openai_tools_sha256(tools) == openai_tools_sha256(render_openai_tools(lock, root))
    # every tool is well-formed enough to be sent as-is
    for tool in tools:
        assert tool["type"] == "function"
        function = tool["function"]
        assert isinstance(function["name"], str) and function["name"]
        assert isinstance(function["description"], str) and function["description"]
        parameters = function["parameters"]
        assert parameters["type"] == "object"
        assert set(parameters["required"]) <= set(parameters["properties"])
        for prop in parameters["properties"].values():
            assert "default" not in prop


# ---------------------------------------------------------------------------
# The compact renderer's `description_overrides` seam (E3a, 2026-09-05).
#
# The evolution loop's state `A_r` is nothing but a set of replacement
# descriptions, and `A_0` must stay byte-identical to the sealed baseline.
# Two proofs of that identity, deliberately separate:
#
# 1. a HASH PIN on the real 152-row registry, which skips where the asset is
#    absent (a machine without the registry cannot be asked to prove a fact
#    about bytes it does not have);
# 2. EXACT BYTES on the synthetic `audio2tool_world` registry, which always
#    runs -- the same rendering code, a registry small enough to write out in
#    full.
# ---------------------------------------------------------------------------

# sha256 of `render_registry_compact(lock, root)` over the locked
# tools_registry.csv, measured 2026-09-05 on the primary dev host BEFORE the
# `description_overrides` parameter existed. 152 lines, 15,854 characters.
COMPACT_REAL_SHA256 = "752dd381a02028dc7345a6ac826109bdcc879d82547a9029a43d559d0de8a605"
COMPACT_REAL_LINES = 152
COMPACT_REAL_CHARS = 15854

SYNTHETIC_COMPACT = (
    "- setLighting(deviceId: String): Turns a light on.\n"
    "- setSecurityMode(mode: Mode): Sets the security mode."
)


@pytest.mark.skipif(_REAL is None, reason="real audio2tool registry not available on this host")
def test_compact_default_bytes_are_unchanged_on_the_real_registry():
    lock, root = _REAL
    rendered = render_registry_compact(lock, root)
    assert hashlib.sha256(rendered.encode("utf-8")).hexdigest() == COMPACT_REAL_SHA256
    assert len(rendered.split("\n")) == COMPACT_REAL_LINES
    assert len(rendered) == COMPACT_REAL_CHARS
    # None and {} are both "no override at all", not "an empty override".
    assert render_registry_compact(lock, root, description_overrides=None) == rendered
    assert render_registry_compact(lock, root, description_overrides={}) == rendered


@pytest.mark.skipif(_REAL is None, reason="real audio2tool registry not available on this host")
def test_compact_override_on_the_real_registry_changes_one_line_only():
    from speech_aware_evidence_acquisition.data.audio2tool import load_tool_registry

    lock, root = _REAL
    rows = load_tool_registry(lock, root)
    victim = sorted(row["tool_name"] for row in rows)[0]
    baseline = render_registry_compact(lock, root).split("\n")
    evolved = render_registry_compact(
        lock, root, description_overrides={victim: "A replacement description."}
    ).split("\n")
    assert len(evolved) == len(baseline) == COMPACT_REAL_LINES
    differing = [index for index in range(len(baseline)) if baseline[index] != evolved[index]]
    assert len(differing) == 1
    assert evolved[differing[0]].endswith(": A replacement description.")
    # The signature half of the line, and therefore the sort key, is untouched.
    assert evolved[differing[0]].split(":")[0] == baseline[differing[0]].split(":")[0]


def test_compact_default_bytes_on_the_synthetic_registry(audio2tool_world):
    lock = load_lock(audio2tool_world.lock_path)
    rendered = render_registry_compact(lock, audio2tool_world.data_root)
    assert rendered == SYNTHETIC_COMPACT
    assert render_registry_compact(
        lock, audio2tool_world.data_root, description_overrides=None
    ) == SYNTHETIC_COMPACT
    assert render_registry_compact(
        lock, audio2tool_world.data_root, description_overrides={}
    ) == SYNTHETIC_COMPACT


def test_compact_override_keeps_the_released_shape(audio2tool_world):
    lock = load_lock(audio2tool_world.lock_path)
    rendered = render_registry_compact(
        lock,
        audio2tool_world.data_root,
        description_overrides={"setLighting": "Switches one named lamp."},
    )
    assert rendered == (
        "- setLighting(deviceId: String): Switches one named lamp.\n"
        "- setSecurityMode(mode: Mode): Sets the security mode."
    )
    # Same line count, same order, no trailing newline -- only the text after
    # the colon of one line differs.
    assert len(rendered.split("\n")) == len(SYNTHETIC_COMPACT.split("\n"))
    assert not rendered.endswith("\n")


def test_compact_rows_renderer_agrees_with_the_lock_shaped_entry(audio2tool_world):
    from speech_aware_evidence_acquisition.data.audio2tool import load_tool_registry

    lock = load_lock(audio2tool_world.lock_path)
    rows = load_tool_registry(lock, audio2tool_world.data_root)
    overrides = {"setSecurityMode": "Arms or disarms the house."}
    assert render_registry_compact_rows(rows) == render_registry_compact(
        lock, audio2tool_world.data_root
    )
    assert render_registry_compact_rows(
        rows, description_overrides=overrides
    ) == render_registry_compact(
        lock, audio2tool_world.data_root, description_overrides=overrides
    )


def test_compact_override_refuses_a_tool_the_registry_does_not_carry(audio2tool_world):
    lock = load_lock(audio2tool_world.lock_path)
    with pytest.raises(Audio2ToolSchemaError, match="not a tools_registry.csv tool"):
        render_registry_compact(
            lock, audio2tool_world.data_root, description_overrides={"noSuchTool": "x"}
        )


@pytest.mark.parametrize(
    "replacement, message",
    [
        ("", "non-empty text"),
        ("   ", "non-empty text"),
        (7, "non-empty text"),
        ("two\nlines", "newline"),
        ("carriage\rreturn", "newline"),
    ],
)
def test_compact_override_refuses_a_malformed_replacement(
    audio2tool_world, replacement, message
):
    lock = load_lock(audio2tool_world.lock_path)
    with pytest.raises(Audio2ToolSchemaError, match=message):
        render_registry_compact(
            lock,
            audio2tool_world.data_root,
            description_overrides={"setLighting": replacement},
        )
