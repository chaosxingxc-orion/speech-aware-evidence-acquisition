"""E17: constant native tool-schema rendering across the roles of one row.

Lever L1 of ``docs/results/2026-09-19-slurp-throughput-root-cause-v1.md``.
The measured fact this module encodes: ``task_instruction`` is byte-identical
across every role of a SLURP native row, only the tool-bearing role carries a
native ``tool_schemas`` entry, and the Qwen3-Omni chat template renders that
array INSIDE the system message -- so with one slot pinned per row the block
toggles on at the first Reviewer contact and off at the Planner contact, and
each toggle re-prefills the whole prefix, speech packet included.

``native_episode.tool_schema_rendering`` ``"constant"`` renders the SAME
``tools`` array on every contact of the row. Tool AUTHORITY is untouched: a
role that may not call a tool still sends ``tool_choice`` ``"none"``, is
advertised no ability by the framework, and is still refused by
``_RoleAuthorityRail`` if it emits a call anyway.

Every episode here runs the real OpenJiuwen role graph, the real
``rails.runner`` and the real ``LlamaServerTransport.render_request`` over the
shared fake transport. No model, no tokenizer, no encoder, no server.

Design: ``docs/superpowers/specs/2026-09-19-e17-constant-tool-rendering-design.md``.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import replace

import pytest

from speech_aware_evidence_acquisition.rails.native_episode_config import (
    load_native_episode_config,
)
from speech_aware_evidence_acquisition.rails.phase_tools import TASK_CONTRACT_TOOL
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available
from speech_aware_evidence_acquisition.reproduction.ojw.native_request import (
    NativeRoleSpeechBinding,
    NativeSpeechRequestError,
    _assert_framework_schemas,
)
from speech_aware_evidence_acquisition.reproduction.ojw.native_roles import (
    NativeRoleContactContext,
    NativeRoleNode,
    NativeRoleNodeSpec,
)

from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_episode_config import config as _episode_values
from test_native_episode_config import program as _episode_program
from test_native_episode_runner import _ActualEpisodeHarness
from test_ojw_native_roles import _card, _completion, _MeteredScript, _tool_call

#: The five contacts of one row, in the order the pinned slot sees them --
#: the same shape section 3.1 of the throughput report measures (Reviewer
#: 1.99 contacts per row).
CONTACT_KEYS = (
    ("s1", "perception", 1, 1),
    ("s1", "solver", 1, 1),
    ("s1", "reviewer", 1, 1),
    ("s1", "reviewer", 1, 2),
    ("s1", "planner", 1, 1),
)

#: The three contacts whose bytes the armed key is allowed to move: the roles
#: that carry no tool authority and therefore carried no ``tools`` array.
TOOL_FREE_KEYS = (CONTACT_KEYS[0], CONTACT_KEYS[1], CONTACT_KEYS[4])

#: The two contacts of the one role that already carried the array, and whose
#: bytes must therefore not move at all.
TOOL_BEARING_KEYS = (CONTACT_KEYS[2], CONTACT_KEYS[3])


# The switch key itself -- that ``native_episode.tool_schema_rendering``
# resolves in the episode class, that ``"per-role"`` is its null arm and that
# its two arms differ in exactly one leaf -- is proved beside every other
# switch key, in ``tests/unit/test_config_table_module_switches.py`` section
# 12d, which also carries the closed-allowlist ratchet.


# ---------------------------------------------------------------------------
# 1. The loader: the default, the armed value, and the two fail-closed rules.
# ---------------------------------------------------------------------------


def _values_with_reviewer_tool(*, rendering=None, planner_tool=False):
    values = _episode_values()
    values["phase_tools"] = {
        "reviewer": {
            "mode": "native-tools",
            "source_authority_role": "reviewer",
            "allowed_tools": ["analyze"],
        }
    }
    if planner_tool:
        values["phase_tools"]["planner"] = {
            "mode": "native-tools",
            "source_authority_role": "planner",
            "allowed_tools": ["inspect"],
        }
    if rendering is not None:
        values["native_episode"]["tool_schema_rendering"] = rendering
    return values


def test_the_default_is_per_role_and_renders_no_constant_array():
    parsed = load_native_episode_config(_values_with_reviewer_tool(), _episode_program())

    assert parsed.tool_schema_rendering == "per-role"
    assert parsed.constant_tool_names is None
    # Spelling the default out loud composes the same episode.
    explicit = load_native_episode_config(
        _values_with_reviewer_tool(rendering="per-role"), _episode_program()
    )
    assert explicit == parsed


def test_the_armed_value_names_the_one_constant_array():
    parsed = load_native_episode_config(
        _values_with_reviewer_tool(rendering="constant"), _episode_program()
    )

    assert parsed.tool_schema_rendering == "constant"
    # The union IS the tool-bearing role's own ordered array, so that role's
    # request is byte-identical to the per-role arm's.
    assert parsed.constant_tool_names == ("analyze",)
    assert parsed.role("reviewer").tool_names == ("analyze",)
    assert parsed.role("solver").tool_names == ()


def test_an_unknown_rendering_mode_refuses():
    values = _values_with_reviewer_tool(rendering="union")
    with pytest.raises(ValueError, match="tool_schema_rendering"):
        load_native_episode_config(values, _episode_program())


def test_constant_without_any_tool_authority_refuses():
    """With no role holding tools, 'constant' is a second spelling of
    'per-role' -- and two spellings of one thing is how a cell ends up with
    two identities."""

    values = _episode_values()
    values["native_episode"]["tool_schema_rendering"] = "constant"
    with pytest.raises(ValueError, match="at least one role with tool authority"):
        load_native_episode_config(values, _episode_program())


def test_constant_with_disagreeing_tool_authority_refuses():
    """Rendering may widen a tool-FREE role, never a tool-bearing one: the
    native tool-authority custody path re-derives a request's schema array
    from the names the model called and compares its digest to the request's
    own, which only holds while a caller's array is exactly its authority."""

    values = _values_with_reviewer_tool(rendering="constant", planner_tool=True)
    values["native_episode"]["roles"]["reviewer"]["max_iterations"] = 1
    with pytest.raises(ValueError, match="same ordered tool names"):
        load_native_episode_config(values, _episode_program())

    # The same two roles agreeing on one ordered array is admitted.
    agreeing = _values_with_reviewer_tool(rendering="constant", planner_tool=True)
    agreeing["phase_tools"]["planner"]["allowed_tools"] = ["analyze"]
    parsed = load_native_episode_config(agreeing, _episode_program())
    assert parsed.constant_tool_names == ("analyze",)


# ---------------------------------------------------------------------------
# 2. The binding and the request builder, without a graph.
# ---------------------------------------------------------------------------


def _schema(name: str) -> dict[str, object]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": f"Synthetic {name}.",
            "parameters": {"type": "object", "properties": {}},
        },
    }


def test_rendered_names_must_contain_the_authority_names():
    messages = [
        {"role": "system", "content": "instruction"},
        {"role": "user", "content": "query"},
    ]
    with pytest.raises(NativeSpeechRequestError, match="must contain every tool"):
        NativeRoleSpeechBinding(
            role_id="reviewer", sample_id="s1", role_query="query",
            base_messages=messages, core_kwargs={"agent_state": []},
            tool_names=("analyze",), rendered_tool_names=("inspect",),
        )
    with pytest.raises(NativeSpeechRequestError, match="nonempty ordered unique"):
        NativeRoleSpeechBinding(
            role_id="reviewer", sample_id="s1", role_query="query",
            base_messages=messages, core_kwargs={"agent_state": []},
            tool_names=(), rendered_tool_names=(),
        )
    # A tool-FREE role rendering the union is exactly the admitted shape.
    binding = NativeRoleSpeechBinding(
        role_id="solver", sample_id="s1", role_query="query",
        base_messages=messages, core_kwargs={"agent_state": []},
        tool_names=(), rendered_tool_names=("analyze",),
    )
    assert binding.tool_names == ()
    assert binding.rendered_tool_names == ("analyze",)


def test_the_schema_cross_check_is_exact_per_role_and_containment_constant():
    visible = ({"name": "analyze", "description": "Synthetic analyze.",
                "parameters": {"type": "object", "properties": {}}},)
    rendered = [_schema("analyze"), _schema("inspect")]

    # per-role: same length, in order -- the historical rule, unchanged.
    _assert_framework_schemas(visible, [rendered[0]], constant_rendering=False)
    with pytest.raises(NativeSpeechRequestError, match="do not match the selected scope"):
        _assert_framework_schemas(visible, rendered, constant_rendering=False)

    # constant: containment by name, with every field still compared.
    _assert_framework_schemas(visible, rendered, constant_rendering=True)
    _assert_framework_schemas((), rendered, constant_rendering=True)
    with pytest.raises(NativeSpeechRequestError, match="do not match the selected scope"):
        _assert_framework_schemas(visible, [rendered[1]], constant_rendering=True)
    drifted = json.loads(json.dumps(rendered))
    drifted[0]["function"]["description"] = "changed"
    with pytest.raises(NativeSpeechRequestError, match="differs from the registered tool"):
        _assert_framework_schemas(visible, drifted, constant_rendering=True)


# ---------------------------------------------------------------------------
# 3. Authority is not rendering: the refusal path, unchanged.
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_a_role_without_authority_is_still_refused_a_tool_call():
    """The same proof ``test_ojw_native_roles`` makes for the per-role arm,
    restated here because ``constant`` rendering is what makes the question
    live: three roles now SEE the tool definitions in their system message.
    Seeing is not calling -- the rail refuses the call, hands the role the
    refusal as a tool result, and the episode continues."""

    from openjiuwen.core.foundation.tool import LocalFunction
    from openjiuwen.core.runner import Runner

    calls: list[int] = []
    name = "native_role_e17_unadvertised"
    Runner.resource_mgr.add_tool(
        LocalFunction(card=_card(name), func=lambda value: calls.append(value)),
        refresh=True,
    )
    script = _MeteredScript([
        _completion(
            text="calling a tool I was only shown",
            tool_calls=_tool_call(name, "call-1", '{"value":7}'),
        ),
        _completion(text="continued after denial", contact_id="contact-2", serial=2),
    ])
    node = NativeRoleNode(
        spec=NativeRoleNodeSpec(
            role_id="solver", role_kind="solver",
            prompt="Answer; you may call nothing.", max_iterations=2,
        ),
        metered_request=script,
        contact_context_provider=lambda index: NativeRoleContactContext(
            sample_id="sample-1", agent_contact_id=f"contact-{index + 1}"
        ),
    )

    result = asyncio.run(node.invoke_direct("Try an unavailable action."))

    assert calls == []
    assert result["actor_output"] == "continued after denial"
    assert script.requests[0].visible_tool_names == ()
    assert "outside role authority" in script.requests[1].messages[-1]["content"]


# ---------------------------------------------------------------------------
# 4. The production render path: per-role versus constant, byte for byte.
# ---------------------------------------------------------------------------


def _episode(tmp_path, *, rendering):
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=0,
        max_contacts=5,
        planner_actions=("ACCEPT",),
        reviewer_task_tool=True,
    )
    harness.config = replace(harness.config, tool_schema_rendering=rendering)
    try:
        summary = harness.run()
    finally:
        harness.close()
    return harness, summary


def _bodies(harness):
    assert set(harness.prepared) == set(CONTACT_KEYS), sorted(harness.prepared)
    return {key: harness.prepared[key]["rendered"] for key in CONTACT_KEYS}


def _system_prefix(body):
    """What the chat template folds into ONE system message: the task
    instruction plus, when present, the native tools array."""

    return json.dumps(
        {"system": body["messages"][0], "tools": body.get("tools")},
        sort_keys=True, ensure_ascii=False,
    )


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_the_system_prefix_toggles_per_role_and_is_constant_when_armed(tmp_path):
    off_harness, _off = _episode(tmp_path / "off", rendering="per-role")
    on_harness, _on = _episode(tmp_path / "on", rendering="constant")
    off, on = _bodies(off_harness), _bodies(on_harness)

    # The measured premise: the task instruction itself never changes.
    assert len({json.dumps(body["messages"][0], sort_keys=True) for body in off.values()}) == 1
    assert len({json.dumps(body["messages"][0], sort_keys=True) for body in on.values()}) == 1

    # per-role: TWO distinct system prefixes in one row -- the block toggles
    # on at the first Reviewer contact and off again at the Planner's.
    assert len({_system_prefix(body) for body in off.values()}) == 2
    assert [key for key in CONTACT_KEYS if "tools" in off[key]] == list(TOOL_BEARING_KEYS)

    # constant: ONE. Every contact of the row renders the same array, so the
    # pinned slot's KV prefix survives every role handover.
    assert len({_system_prefix(body) for body in on.values()}) == 1
    assert all("tools" in on[key] for key in CONTACT_KEYS)
    assert len({json.dumps(on[key]["tools"], sort_keys=True) for key in CONTACT_KEYS}) == 1
    assert [tool["function"]["name"] for tool in on[CONTACT_KEYS[0]]["tools"]] == [
        TASK_CONTRACT_TOOL
    ]


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_the_armed_arm_adds_the_block_and_changes_nothing_else(tmp_path):
    off_harness, _off = _episode(tmp_path / "off", rendering="per-role")
    on_harness, _on = _episode(tmp_path / "on", rendering="constant")
    off, on = _bodies(off_harness), _bodies(on_harness)

    # The role that already carried the array is untouched, byte for byte --
    # same schemas, same tool_choice, same everything.
    for key in TOOL_BEARING_KEYS:
        assert on[key] == off[key]
        assert on[key]["tool_choice"] == "auto"

    # The three tool-free contacts differ in exactly one key: the added
    # array. Their tool_choice stays 'none', which is what keeps authority
    # and rendering separate on the wire.
    for key in TOOL_FREE_KEYS:
        assert "tools" not in off[key]
        assert {k: v for k, v in on[key].items() if k != "tools"} == off[key]
        assert on[key]["tool_choice"] == "none"
        assert off[key]["tool_choice"] == "none"


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_the_receipt_proves_the_constancy(tmp_path):
    _harness, summary = _episode(tmp_path, rendering="constant")
    receipt = summary.results[0].native_episode_receipt["tool_schema_rendering"]

    assert receipt["schema"] == "saea-native-tool-schema-rendering-v1"
    assert receipt["mode"] == "constant"
    assert receipt["rendered_tool_names"] == [TASK_CONTRACT_TOOL]
    assert len(receipt["contacts"]) == len(CONTACT_KEYS)
    # The verdict-facing number: one distinct rendered-array digest over the
    # whole row is the constancy claim.
    assert receipt["distinct_tool_schemas_sha256"] == 1
    digests = {row["tool_schemas_sha256"] for row in receipt["contacts"]}
    assert len(digests) == 1 and all(len(value) == 64 for value in digests)
    by_role = {}
    for row in receipt["contacts"]:
        assert row["rendered_tool_names"] == [TASK_CONTRACT_TOOL]
        by_role.setdefault(row["role_id"], []).append(row["authority_tool_names"])
    # Authority, recorded beside rendering and visibly NOT widened.
    assert by_role["reviewer"] == [[TASK_CONTRACT_TOOL], [TASK_CONTRACT_TOOL]]
    assert by_role["perception"] == [[]]
    assert by_role["solver"] == [[]]
    assert by_role["planner"] == [[]]


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_the_off_arm_is_the_keys_absence_down_to_the_byte(tmp_path):
    """``per-role`` renders exactly what the pre-E17 tree rendered, and seals
    exactly the receipt it sealed: no block, no field, no extra record."""

    first, first_summary = _episode(tmp_path / "a", rendering="per-role")
    second, _second = _episode(tmp_path / "b", rendering="per-role")

    assert _bodies(first) == _bodies(second)
    assert "tool_schema_rendering" not in first_summary.results[0].native_episode_receipt
