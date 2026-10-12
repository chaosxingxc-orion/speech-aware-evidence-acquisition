"""Decision 283 A: the Thinking-core harness knobs, model-free (no server, GPU, encoder or dataset contact).

Covers the model-fragment schema and its hashing, the per-node ``thinking_policy`` resolution, the answer-only fallback decoding and
receipt, the family-level fallback contact allowance, the controller's contact-to-node map, the runner's fallback re-ask and plan ceiling
(stub core client), and a source check against the pinned llama.cpp fork so a rebase that renames a field fails loudly.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
import threading
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core import reasoning_knobs as rk
from speech_aware_evidence_acquisition.core.config import ConfigError, compose, effective_request_decoding_params
from speech_aware_evidence_acquisition.core.tracing import get_current_trace_buffer
from speech_aware_evidence_acquisition.rails import controllers as rc
from speech_aware_evidence_acquisition.rails import run_speech_native_agent_loop
from speech_aware_evidence_acquisition.rails import runner as rails_runner
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

from test_rails_runner import (
    _SHA_C,
    _agent_trace,
    _controller_registry,
    _knowledge_snapshot,
    _one_sample_adapter,
    _plan,
)
from test_direct_empty_completion import _direct_controller

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "flights" / "direct"))

MESSAGE = "Considering the limited time by the user, I have to give the solution based on the thinking directly now."
MESSAGE_SHA = hashlib.sha256(MESSAGE.encode("utf-8")).hexdigest()
GUARD = "refuse-think-marker-in-content"

# Config hashes of the two real direct-only cells composed on master BEFORE this change (Instruct and the 266-E Thinking max8192 arm).
PRE_CHANGE = {
    "instruct": ("4ede3a96f1b83d8960e72085984f71d1fb204af2984012af7342e42f659ad849",
                 {"id_slot": "per-sample", "max_tokens": 512, "seed": 20260913, "temperature": 0}),
    "thinking": ("3cc0aaa963dfdd030d22f5efd264c31355a1a3d874d44ec585fd960b01992c17",
                 {"id_slot": "per-sample", "max_tokens": 8192, "seed": 20260913, "temperature": 0}),
}


def thinking_fragment(**overrides) -> dict:
    """The 268 registration shape (budget 3,072 + reserve 1,024 = 4,096) as an example model fragment."""

    fragment = {
        "model_lock_key": "qwen3-omni-30b-a3b-thinking-gguf-q4km",
        "transport": "llama-server",
        "server_args": ["-c", "98304", "-np", "4", "--reasoning-format", "deepseek", "--reasoning-budget-message", MESSAGE],
        "decoding_params": {"temperature": 0, "seed": 20260913, "max_tokens": 4096, "id_slot": "per-sample"},
        "reasoning_content_guard": GUARD,
        "reasoning_budget_tokens": 3072,
        "answer_reserve_tokens": 1024,
        "enable_thinking": True,
        "reasoning_context_policy": "drop-reasoning-v1",
        "forced_close_message_sha256": MESSAGE_SHA,
    }
    fragment.update(overrides)
    return {key: value for key, value in fragment.items() if value is not None}


def _write_tree(root: Path, model: dict, *, baseline: dict | None = None) -> None:
    for kind, name, body in (
        ("model", "m", model), ("dataset", "d", {"dataset_key": "x"}),
        ("baseline", "b", baseline or {"baseline_key": "y"}), ("experiment", "e", {"experiment_key": "z"}),
    ):
        folder = root / "configs" / kind
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{name}.json").write_text(json.dumps(body), encoding="utf-8")


def _compose(tmp_path: Path, model: dict, **kwargs):
    _write_tree(tmp_path, model, **kwargs)
    return compose(tmp_path, "m", "d", "b", "e")


# ---------------------------------------------------------------------------
# fragment schema
# ---------------------------------------------------------------------------


def test_thinking_fragment_composes_and_folds_the_two_wire_fields(tmp_path):
    values = _compose(tmp_path, thinking_fragment()).values
    decoding = values["decoding_params"]
    assert decoding["thinking_budget_tokens"] == 3072
    assert decoding["chat_template_kwargs"] == {"enable_thinking": True}
    assert decoding["max_tokens"] == 4096
    # the knobs themselves stay on the fragment: they are the hashed source
    assert values["reasoning_budget_tokens"] == 3072 and values["answer_reserve_tokens"] == 1024
    assert effective_request_decoding_params(values)["thinking_budget_tokens"] == 3072


@pytest.mark.parametrize("knob,value", [
    ("reasoning_budget_tokens", 2048), ("enable_thinking", False), ("reasoning_context_policy", None),
    ("forced_close_message_sha256", None),
])
def test_every_knob_enters_the_config_hash(tmp_path, knob, value):
    base = _compose(tmp_path / "a", thinking_fragment()).config_hash
    changed = thinking_fragment(**{knob: value})
    if knob == "reasoning_budget_tokens":
        changed["decoding_params"] = dict(changed["decoding_params"], max_tokens=2048 + 1024)
        changed["answer_reserve_tokens"] = 1024
    if knob == "enable_thinking":
        changed.pop("reasoning_budget_tokens"), changed.pop("answer_reserve_tokens")
    if knob == "forced_close_message_sha256":
        changed["server_args"] = [t for t in changed["server_args"] if t not in ("--reasoning-budget-message", MESSAGE)]
    assert _compose(tmp_path / "b", changed).config_hash != base


def test_the_pinned_message_hash_and_the_server_flag_must_agree(tmp_path):
    with pytest.raises(ConfigError, match="differs from forced_close_message_sha256"):
        _compose(tmp_path, thinking_fragment(forced_close_message_sha256="0" * 64))
    wrong = thinking_fragment()
    wrong["server_args"] = ["-c", "98304", "--reasoning-budget-message", MESSAGE + " changed"]
    with pytest.raises(ConfigError, match="differs from forced_close_message_sha256"):
        _compose(tmp_path, wrong)
    no_pin = thinking_fragment(forced_close_message_sha256=None)
    with pytest.raises(ConfigError, match="pins no forced_close_message_sha256"):
        _compose(tmp_path, no_pin)
    no_flag = thinking_fragment()
    no_flag["server_args"] = ["-c", "98304"]
    with pytest.raises(ConfigError, match="carries no --reasoning-budget-message"):
        _compose(tmp_path, no_flag)
    equals_form = thinking_fragment()
    equals_form["server_args"] = ["-c", "98304", f"--reasoning-budget-message={MESSAGE}"]
    assert _compose(tmp_path, equals_form).values["forced_close_message_sha256"] == MESSAGE_SHA


def test_max_tokens_must_equal_budget_plus_reserve(tmp_path):
    bad = thinking_fragment()
    bad["decoding_params"] = dict(bad["decoding_params"], max_tokens=4097)
    with pytest.raises(ConfigError, match="must equal reasoning_budget_tokens \\+ answer_reserve_tokens"):
        _compose(tmp_path, bad)
    only_budget = thinking_fragment(answer_reserve_tokens=None)
    only_budget["decoding_params"] = dict(only_budget["decoding_params"], max_tokens=3072)
    with pytest.raises(ConfigError, match="must exceed reasoning_budget_tokens"):
        _compose(tmp_path, only_budget)
    reserve_alone = thinking_fragment(reasoning_budget_tokens=None)
    with pytest.raises(ConfigError, match="requires reasoning_budget_tokens"):
        _compose(tmp_path, reserve_alone)


def test_an_instruct_fragment_refuses_every_thinking_knob_but_accepts_the_context_policy(tmp_path):
    instruct = {"model_lock_key": "qwen3-omni-30b-a3b-instruct-gguf-q4km", "decoding_params": {"temperature": 0, "max_tokens": 512}}
    assert _compose(tmp_path / "ok", dict(instruct, reasoning_context_policy="drop-reasoning-v1")).values["decoding_params"] == instruct["decoding_params"]
    for key, value in (("reasoning_budget_tokens", 100), ("answer_reserve_tokens", 10), ("enable_thinking", False),
                       ("forced_close_message_sha256", MESSAGE_SHA)):
        with pytest.raises(ConfigError, match="valid only on a reasoning fragment"):
            _compose(tmp_path / key, dict(instruct, **{key: value}))
    with pytest.raises(ConfigError, match="reasoning_context_policy must be one of"):
        _compose(tmp_path / "enum", dict(instruct, reasoning_context_policy="carry-all"))


def test_wire_fields_cannot_be_declared_directly_in_decoding_params(tmp_path):
    for direct in ({"thinking_budget_tokens": 5}, {"chat_template_kwargs": {"enable_thinking": False}}):
        model = {"model_lock_key": "x", "decoding_params": {"temperature": 0, **direct}}
        with pytest.raises(ConfigError, match="must not carry"):
            _compose(tmp_path / next(iter(direct)), model)


def test_enable_thinking_false_contradicts_a_budget_and_must_be_a_bool(tmp_path):
    with pytest.raises(ConfigError, match="contradicts enable_thinking false"):
        _compose(tmp_path / "a", thinking_fragment(enable_thinking=False))
    with pytest.raises(ConfigError, match="enable_thinking must be a boolean"):
        _compose(tmp_path / "b", thinking_fragment(enable_thinking="yes"))
    off = thinking_fragment(enable_thinking=False)
    for key in ("reasoning_budget_tokens", "answer_reserve_tokens"):
        off.pop(key)
    assert _compose(tmp_path / "c", off).values["decoding_params"]["chat_template_kwargs"] == {"enable_thinking": False}


def test_a_request_override_cannot_break_the_budget_plus_reserve_identity(tmp_path):
    values = dict(_compose(tmp_path, thinking_fragment()).values, request_decoding_overrides={"max_tokens": 2048})
    with pytest.raises(ConfigError, match="keep max_tokens equal"):
        effective_request_decoding_params(values)


@pytest.mark.parametrize("key", ["instruct", "thinking"])
def test_existing_direct_cells_compose_byte_identically(key):
    """No request-bytes change for fragments that do not declare the knobs: the pre-change config hashes and decoding blocks hold."""

    spec = __import__("direct_fb_family").CELLS[key]
    cell = json.loads((REPO / "configs" / "experiment" / f"{spec['cell']}.json").read_text(encoding="utf-8"))["cells"][0]
    composed = compose(REPO, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], spec["cell"])
    expected_hash, expected_decoding = PRE_CHANGE[key]
    assert composed.config_hash == expected_hash
    assert dict(composed.values["decoding_params"]) == expected_decoding
    assert not (rk.REASONING_WIRE_KEYS & set(composed.values["decoding_params"]))


# ---------------------------------------------------------------------------
# per-node policy
# ---------------------------------------------------------------------------


def _base_decoding():
    return {"temperature": 0, "max_tokens": 4096, "thinking_budget_tokens": 3072, "chat_template_kwargs": {"enable_thinking": True}}


def test_node_resolution_without_an_entry_is_a_pure_copy():
    base = _base_decoding()
    out = rk.resolve_node_decoding(base, {"solver": {"reasoning_budget_tokens": 1024}}, "perception")
    assert out == base and out is not base
    assert rk.resolve_node_decoding(base, None, "solver") == base


def test_node_override_changes_budget_and_max_tokens_together():
    out = rk.resolve_node_decoding(_base_decoding(), {"solver": {"reasoning_budget_tokens": 1024}}, "solver")
    assert out["thinking_budget_tokens"] == 1024 and out["max_tokens"] == 1024 + 1024
    out = rk.resolve_node_decoding(_base_decoding(), {"solver": {"answer_reserve_tokens": 512, "reasoning_budget_tokens": 2048}}, "solver")
    assert (out["thinking_budget_tokens"], out["max_tokens"]) == (2048, 2560)


def test_a_no_think_node_drops_the_budget_and_caps_at_the_reserve():
    out = rk.resolve_node_decoding(_base_decoding(), {"perception": {"enable_thinking": False}}, "perception")
    assert "thinking_budget_tokens" not in out
    assert out["chat_template_kwargs"] == {"enable_thinking": False} and out["max_tokens"] == 1024
    assert rk.fallback_reserve(out) is None  # a no-think request has no fallback
    out = rk.resolve_node_decoding(_base_decoding(), {"perception": {"enable_thinking": False, "answer_reserve_tokens": 256}}, "perception")
    assert out["max_tokens"] == 256
    with pytest.raises(rk.ReasoningKnobError, match="contradicts enable_thinking false"):
        rk.resolve_node_decoding(_base_decoding(), {"perception": {"enable_thinking": False, "reasoning_budget_tokens": 5}}, "perception")


def test_a_node_may_not_exceed_the_geometry_cap():
    with pytest.raises(rk.ReasoningKnobError, match="exceeds the geometry cap"):
        rk.resolve_node_decoding(_base_decoding(), {"solver": {"reasoning_budget_tokens": 4000}}, "solver", cap=4096)


def test_thinking_policy_validation_and_hashing(tmp_path):
    policy = {"perception": {"enable_thinking": False}, "solver": {"reasoning_budget_tokens": 2048}}
    composed = _compose(tmp_path / "a", thinking_fragment(), baseline={"thinking_policy": policy})
    again = _compose(tmp_path / "b", thinking_fragment(), baseline={"thinking_policy": copy.deepcopy(policy)})
    altered = _compose(tmp_path / "c", thinking_fragment(), baseline={"thinking_policy": {**policy, "solver": {"reasoning_budget_tokens": 1024}}})
    plain = _compose(tmp_path / "d", thinking_fragment())
    assert composed.config_hash == again.config_hash != altered.config_hash != plain.config_hash
    assert rk.knobs_sha256(composed.values) != rk.knobs_sha256(plain.values)
    for bad in ({}, {"solver": {}}, {"solver": {"nope": 1}}, {"solver": {"reasoning_budget_tokens": True}}, {"": {"enable_thinking": True}},
                {"solver": {"reasoning_budget_tokens": 4000}}):
        with pytest.raises(ConfigError):
            _compose(tmp_path / f"bad{abs(hash(json.dumps(bad)))}", thinking_fragment(), baseline={"thinking_policy": bad})
    instruct = {"model_lock_key": "x", "decoding_params": {"temperature": 0, "max_tokens": 512}}
    with pytest.raises(ConfigError, match="valid only on a reasoning fragment"):
        _compose(tmp_path / "inst", instruct, baseline={"thinking_policy": policy})


def test_request_control_shapes():
    rk.validate_request_controls({"thinking_budget_tokens": 0, "chat_template_kwargs": {"enable_thinking": True}})
    for bad in ({"thinking_budget_tokens": -1}, {"thinking_budget_tokens": True}, {"thinking_budget_tokens": "3"},
                {"chat_template_kwargs": {"enable_thinking": "false"}}, {"chat_template_kwargs": {"enable_thinking": True, "x": 1}},
                {"chat_template_kwargs": {}}, {"chat_template_kwargs": {"enable_thinking": False}, "thinking_budget_tokens": 5}):
        with pytest.raises(rk.ReasoningKnobError):
            rk.validate_request_controls(bad)


# ---------------------------------------------------------------------------
# fallback decoding, receipt, allowance
# ---------------------------------------------------------------------------


def test_answer_only_decoding_and_receipt_carry_no_text():
    out = rk.answer_only_decoding({**_base_decoding(), "id_slot": 2, "seed": 7})
    assert out == {"temperature": 0, "max_tokens": 1024, "chat_template_kwargs": {"enable_thinking": False}, "id_slot": 2, "seed": 7}
    with pytest.raises(rk.ReasoningKnobError):
        rk.answer_only_decoding({"max_tokens": 10})
    receipt = rk.fallback_receipt(
        agent_contact_id="c1", first_request_id="r1", reask_request_id="r2", first_finish_reason="length", reask_finish_reason="stop",
        first_tokens={"prompt_tokens": 9, "completion_tokens": 4096}, reask_tokens={"prompt_tokens": 9, "completion_tokens": 17},
        reserve=1024, answered=True,
    )
    assert receipt["schema"] == "saea-thinking-answer-fallback-v1" and receipt["attempt"] == 1
    assert receipt["first_finish_reason"] == "length" and receipt["reask_finish_reason"] == "stop"
    assert (receipt["first_completion_tokens"], receipt["reask_completion_tokens"]) == (4096, 17)
    assert receipt["disposition"] == "answered-after-fallback" and receipt["reask_max_tokens"] == 1024
    assert not any(isinstance(value, str) and len(value) > 40 for value in receipt.values())


def test_family_level_fallback_contact_allowance():
    thinking, plain = _base_decoding(), {"temperature": 0, "max_tokens": 512}
    assert rk.fallback_contacts_per_row("phase-native-module-v1-c4", thinking) == 2
    assert rk.fallback_contacts_per_row("phase-direct-only-v1", thinking) == 1
    assert rk.fallback_contacts_per_row("phase-native-module-v1-c4", plain) == 0
    assert rc.module_program_fallback_contacts_per_row("phase-native-module-v1-c4") == 2
    assert rc.module_program_fallback_contacts_per_row("phase-direct-only-v1") == 1


def test_forced_close_detection_reads_the_end_of_the_reasoning_channel():
    assert rk.detect_forced_close("long thinking... " + MESSAGE + "\n", MESSAGE) is True
    assert rk.detect_forced_close("a natural finish", MESSAGE) is False
    assert rk.detect_forced_close("anything", None) is None and rk.detect_forced_close("", MESSAGE) is None


def test_controller_maps_each_contact_to_its_program_node():
    controller = _direct_controller()
    from test_rails_controllers import _context, _query_state

    contact = controller.initial_contact(_context(_query_state()))
    assert controller.phase_name_for_contact(contact.contact_id) == "direct"
    assert controller.phase_name_for_contact("never-dispatched") is None


# ---------------------------------------------------------------------------
# runner: answer-only fallback with a stub core client
# ---------------------------------------------------------------------------


class _ScriptClient:
    """A text-only client that scripts successive completions and emits each one's COST record like the real adapter."""

    def __init__(self, script):
        self.script, self.calls, self._lock = list(script), [], threading.Lock()

    def complete(self, messages, **options):
        with self._lock:
            index = len(self.calls) + 1
            self.calls.append((tuple(messages), dict(options)))
            text, completion_tokens, finish = self.script[index - 1]
        cost = {"calls": 1, "audio_seconds": 2.0, "latency_seconds": 0.5, "prompt_tokens": 2285, "completion_tokens": completion_tokens}
        if finish is not None:
            cost["finish_reason"] = finish
        get_current_trace_buffer().emit("COST", f"req-{index}/cost", cost)
        return text


THINKING_DECODING = {"temperature": 0, "max_tokens": 4096, "thinking_budget_tokens": 3072, "chat_template_kwargs": {"enable_thinking": True}}

EXECUTORS = [
    "reference-trajectory-v1",
    pytest.param("openjiuwen-workflow-v1", marks=pytest.mark.skipif(
        not openjiuwen_available(), reason="openjiuwen is absent; the reference executor remains dependency-free")),
]


def _fly(tmp_path, client, executor, decoding=None, **overrides):
    trace = _agent_trace()
    summary = run_speech_native_agent_loop(
        data_root=tmp_path,
        plan=_plan(execution_profile="model-free-check"),
        adapter=_one_sample_adapter(),
        core_client=client,
        split_id="all",
        knowledge_snapshot=_knowledge_snapshot(),
        speech_packet_bindings={"s1": {"packet_id": "fake/dev/s1", "sha256": _SHA_C}},
        controller_policy_id="direct-empty-test-v1",
        controller_registry=_controller_registry("direct-empty-test-v1", lambda _sid: _direct_controller()),
        max_contacts=1,
        slot_count=1,
        queue_depth=1,
        trace_sink=trace,
        agent_executor_id=executor,
        decoding_params=dict(THINKING_DECODING if decoding is None else decoding),
        **overrides,
    )
    return summary, trace


def _records(trace, suffix):
    return [(rid, payload) for channel, rid, payload in trace.iter_records() if channel == "TOOL" and rid.endswith(suffix)]


@pytest.mark.parametrize("executor", EXECUTORS)
def test_a_normal_thinking_answer_makes_one_contact_and_no_receipt(tmp_path, executor):
    client = _ScriptClient([("turn on the lights", 700, "stop")])
    summary, trace = _fly(tmp_path, client, executor)
    assert summary.results[0].final_response_text == "turn on the lights"
    assert len(client.calls) == 1 and client.calls[0][1]["decoding_params"]["thinking_budget_tokens"] == 3072
    assert _records(trace, "/reasoning-fallback") == [] and _records(trace, "/empty-completion") == []


@pytest.mark.parametrize("executor", EXECUTORS)
def test_a_forced_close_answer_is_delivered_without_a_re_ask(tmp_path, executor):
    """The forced close worked: content arrived, so the harness never re-asks (the close is visible only on the COST record)."""

    client = _ScriptClient([("set an alarm", 4000, "stop")])
    summary, trace = _fly(tmp_path, client, executor)
    assert summary.results[0].final_response_text == "set an alarm" and len(client.calls) == 1
    assert _records(trace, "/reasoning-fallback") == []


@pytest.mark.parametrize("executor", EXECUTORS)
def test_empty_content_at_the_cap_triggers_exactly_one_answer_only_re_ask_and_a_receipt(tmp_path, executor):
    client = _ScriptClient([("", 4096, "length"), ("play some jazz", 33, "stop")])
    summary, trace = _fly(tmp_path, client, executor)
    assert summary.results[0].final_response_text == "play some jazz"
    assert len(client.calls) == 2
    first, second = client.calls[0][1]["decoding_params"], client.calls[1][1]["decoding_params"]
    assert first["thinking_budget_tokens"] == 3072 and first["max_tokens"] == 4096
    assert "thinking_budget_tokens" not in second
    assert second["chat_template_kwargs"] == {"enable_thinking": False} and second["max_tokens"] == 1024
    assert client.calls[0][0] == client.calls[1][0], "the re-ask repeats the same messages"
    (rid, receipt), = _records(trace, "/reasoning-fallback")
    assert rid == "c-direct-s1/reasoning-fallback"
    assert receipt["schema"] == "saea-thinking-answer-fallback-v1" and receipt["attempt"] == 1
    assert (receipt["first_finish_reason"], receipt["reask_finish_reason"]) == ("length", "stop")
    assert (receipt["first_completion_tokens"], receipt["reask_completion_tokens"]) == (4096, 33)
    assert receipt["answered"] is True and receipt["disposition"] == "answered-after-fallback"
    assert (receipt["first_request_id"], receipt["reask_request_id"]) == ("req-1", "req-2")
    assert _records(trace, "/empty-completion") == []


@pytest.mark.parametrize("executor", EXECUTORS)
def test_empty_twice_is_the_existing_abstention_with_the_re_ask_receipted(tmp_path, executor):
    client = _ScriptClient([("", 4096, "length"), ("", 1024, "length")])
    summary, trace = _fly(tmp_path, client, executor)
    assert summary.results[0].final_response_text == "" and len(client.calls) == 2
    (_rid, receipt), = _records(trace, "/reasoning-fallback")
    assert receipt["answered"] is False and receipt["disposition"] == "empty-after-fallback-abstention"
    (_rid, empty), = _records(trace, "/empty-completion")
    assert empty["cap_hit"] is True and empty["max_tokens"] == 1024 and empty["completion_tokens"] == 1024


@pytest.mark.parametrize("executor", EXECUTORS)
def test_an_empty_stop_is_not_a_budget_failure_and_is_not_re_asked(tmp_path, executor):
    client = _ScriptClient([("", 97, "stop")])
    summary, trace = _fly(tmp_path, client, executor)
    assert summary.results[0].final_response_text == "" and len(client.calls) == 1
    assert _records(trace, "/reasoning-fallback") == [] and len(_records(trace, "/empty-completion")) == 1


@pytest.mark.parametrize("executor", EXECUTORS)
def test_a_request_without_knobs_never_re_asks(tmp_path, executor):
    """The Instruct path is untouched: empty at the cap without a thinking budget is the historical receipted abstention."""

    client = _ScriptClient([("", 2048, "length")])
    summary, trace = _fly(tmp_path, client, executor, decoding={"temperature": 0, "max_tokens": 2048})
    assert summary.results[0].final_response_text == "" and len(client.calls) == 1
    assert _records(trace, "/reasoning-fallback") == [] and len(_records(trace, "/empty-completion")) == 1


@pytest.mark.parametrize("executor", EXECUTORS)
def test_per_node_policy_resolves_per_contact_in_the_runner(tmp_path, executor):
    client = _ScriptClient([("hello", 5, "stop")])
    _fly(tmp_path, client, executor, thinking_policy={"direct": {"reasoning_budget_tokens": 1024}})
    sent = client.calls[0][1]["decoding_params"]
    assert sent["thinking_budget_tokens"] == 1024 and sent["max_tokens"] == 1024 + 1024
    client = _ScriptClient([("hello", 5, "stop")])
    _fly(tmp_path, client, executor, thinking_policy={"direct": {"enable_thinking": False}})
    sent = client.calls[0][1]["decoding_params"]
    assert sent["chat_template_kwargs"] == {"enable_thinking": False} and "thinking_budget_tokens" not in sent and sent["max_tokens"] == 1024


def test_the_plan_ceiling_allows_the_fallback_contact(tmp_path):
    """One row, one planned contact, one allowed fallback: a plan of 1 model call is refused for a budgeted thinking request."""

    client = _ScriptClient([("x", 1, "stop")])
    with pytest.raises(rails_runner.RailsRunnerError, match="exceeds the ExecutionPlan budget"):
        _fly_with_plan(tmp_path, client, 1)
    summary, _trace = _fly_with_plan(tmp_path, _ScriptClient([("x", 1, "stop")]), 2)
    assert summary.results[0].final_response_text == "x"


def _fly_with_plan(tmp_path, client, planned_calls):
    trace = _agent_trace()
    summary = run_speech_native_agent_loop(
        data_root=tmp_path, plan=_plan(execution_profile="model-free-check", planned_model_calls=planned_calls),
        adapter=_one_sample_adapter(), core_client=client, split_id="all", knowledge_snapshot=_knowledge_snapshot(),
        speech_packet_bindings={"s1": {"packet_id": "fake/dev/s1", "sha256": _SHA_C}},
        controller_policy_id="direct-empty-test-v1",
        controller_registry=_controller_registry("direct-empty-test-v1", lambda _sid: _direct_controller()),
        max_contacts=1, slot_count=1, queue_depth=1, trace_sink=trace, agent_executor_id="reference-trajectory-v1",
        decoding_params=dict(THINKING_DECODING),
    )
    return summary, trace


# ---------------------------------------------------------------------------
# pinned fork source
# ---------------------------------------------------------------------------

FORK = Path(os.environ.get("SAEA_LLAMA_CPP_SOURCE", "/home/chao/llama.cpp-featcache"))


@pytest.mark.skipif(not (FORK / "tools" / "server").is_dir(), reason="the pinned llama.cpp fork source is not present on this host")
def test_the_pinned_fork_source_still_carries_the_fields_this_harness_relies_on():
    """A fork rebase that renames a request field or the budget-message flag must fail here, loudly, before a flight does."""

    common = (FORK / "tools" / "server" / "server-common.cpp").read_text(encoding="utf-8", errors="replace")
    schema = (FORK / "tools" / "server" / "server-schema.cpp").read_text(encoding="utf-8", errors="replace")
    arg = (FORK / "common" / "arg.cpp").read_text(encoding="utf-8", errors="replace")
    assert rk.WIRE_BUDGET_KEY in common, "per-request thinking_budget_tokens"
    assert rk.WIRE_TEMPLATE_KWARGS_KEY in common and "enable_thinking" in common, "per-request chat_template_kwargs.enable_thinking"
    assert "reasoning_budget_message" in common and "reasoning_budget_message" in schema, "budget message forwarded to the sampler"
    assert rk.BUDGET_MESSAGE_FLAG in arg, "server flag --reasoning-budget-message"
    assert "--reasoning-budget" in arg and "--reasoning-format" in arg
