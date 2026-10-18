"""Owner ruling 330 A: the bounded diagnostic exception to decision 286, and the proof that nothing else changes.

Stub servers only (the transport's injected ``post``); no llama.cpp, GPU, encoder or dataset is contacted.
"""

from __future__ import annotations

import base64
import hashlib
import json
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.model.transport import _llama_server_factory
from speech_aware_evidence_acquisition.core.reasoning_knobs import (
    DIAGNOSTIC_RUN_ID,
    REASONING_BYTES_POLICY,
    RETAIN_DIAGNOSTIC_POLICY,
    ReasoningKnobError,
    ReasoningRetention,
)
from speech_aware_evidence_acquisition.core.session import SessionError

from test_llama_server_transport import (  # noqa: F401  (the autouse fixture must be imported to run)
    _base_url,
    _boundary_payload,
    _fake_runtime_receipt,
    _fake_session,
    _live,
    _spawn_live_matching_process,
    _transport,
)
from test_thinking_transport_and_native_knobs import (  # noqa: F401
    GUARD, KNOBS, MESSAGE, _post_script, _wire,
)

SECRET = "the private chain of thought RETAINED-DIAGNOSTIC-BYTES"


def _plan(run_id=DIAGNOSTIC_RUN_ID, profile="bounded-discovery-probe"):
    return SimpleNamespace(run_id=run_id, execution_profile=profile)


def _retention(tmp_path):
    root = tmp_path / "data-root"
    root.mkdir(exist_ok=True)
    return ReasoningRetention.from_plan(_plan(), root), root


def _retaining_transport(tmp_path, post, retention, **kwargs):
    return _transport(
        _base_url(), tmp_path, post=post, reasoning_content_guard=GUARD, reasoning_telemetry=True, forced_close_message=MESSAGE,
        reasoning_bytes_policy=RETAIN_DIAGNOSTIC_POLICY, reasoning_retention=retention, **kwargs,
    )


def _send(transport, tmp_path, *, budget=3072, **extra):
    payload = _boundary_payload(tmp_path)
    payload["decoding_params"] = {"temperature": 0, "seed": 20260913, **KNOBS, "thinking_budget_tokens": budget, **extra}
    return json.loads(transport(json.dumps(payload).encode()))


def test_retention_is_built_only_from_the_diagnostic_plan(tmp_path):
    (tmp_path / "root").mkdir()
    with pytest.raises(ReasoningKnobError, match="not the diagnostic run"):
        ReasoningRetention.from_plan(_plan(run_id="SAEA-SLURP-STAGE3-NXT-R2B-SOLVER-BUDGET-FOLD-B-V1"), tmp_path / "root")
    with pytest.raises(ReasoningKnobError, match="execution profile"):
        ReasoningRetention.from_plan(_plan(profile="baseline-reproduction"), tmp_path / "root")
    with pytest.raises(ReasoningKnobError, match="existing data root"):
        ReasoningRetention.from_plan(_plan(), tmp_path / "absent")
    with pytest.raises(ReasoningKnobError, match="from_plan"):
        ReasoningRetention(_token=object(), run_id=DIAGNOSTIC_RUN_ID, directory=tmp_path)


def test_the_policy_and_the_retention_object_are_required_together(tmp_path):
    retention, _root = _retention(tmp_path)
    post = _post_script([_wire("x", reasoning=SECRET)], [])
    with pytest.raises(SessionError, match="required together"):
        _transport(_base_url(), tmp_path, post=post, reasoning_content_guard=GUARD, reasoning_bytes_policy=RETAIN_DIAGNOSTIC_POLICY)
    with pytest.raises(SessionError, match="required together"):
        _transport(_base_url(), tmp_path, post=post, reasoning_content_guard=GUARD, reasoning_retention=retention)
    with pytest.raises(SessionError, match="must be one of"):
        _transport(_base_url(), tmp_path, post=post, reasoning_content_guard=GUARD, reasoning_bytes_policy="keep-everything-v1")
    with pytest.raises(SessionError, match="reasoning_content_guard"):
        _transport(_base_url(), tmp_path, post=post, reasoning_bytes_policy=RETAIN_DIAGNOSTIC_POLICY, reasoning_retention=retention)
    with pytest.raises(SessionError, match="built from the diagnostic plan"):
        _transport(_base_url(), tmp_path, post=post, reasoning_content_guard=GUARD,
                   reasoning_bytes_policy=RETAIN_DIAGNOSTIC_POLICY, reasoning_retention=object())


def test_a_model_fragment_cannot_declare_the_policy(tmp_path):
    values = {"base_url": _base_url(), "prompt_order": "evidence-first-system-v3", "reasoning_content_guard": GUARD,
              "reasoning_bytes_policy": RETAIN_DIAGNOSTIC_POLICY}
    with pytest.raises(SessionError, match="cannot be declared in a model fragment"):
        _llama_server_factory(values, tmp_path, session=_fake_session(), runtime_receipt=_fake_runtime_receipt(),
                              runtime_root=_live["runtime_root"])


def test_the_factory_passes_a_built_retention_through_and_nothing_else_does(tmp_path):
    retention, _root = _retention(tmp_path)
    values = {"base_url": _base_url(), "prompt_order": "evidence-first-system-v3", "reasoning_content_guard": GUARD}
    armed = _llama_server_factory(values, tmp_path, session=_fake_session(), runtime_receipt=_fake_runtime_receipt(),
                                  runtime_root=_live["runtime_root"], reasoning_retention=retention)
    assert armed._reasoning_retention is retention and armed._reasoning_bytes_policy == RETAIN_DIAGNOSTIC_POLICY
    plain = _llama_server_factory(values, tmp_path, session=_fake_session(), runtime_receipt=_fake_runtime_receipt(),
                                  runtime_root=_live["runtime_root"])
    assert plain._reasoning_retention is None and plain._reasoning_bytes_policy == REASONING_BYTES_POLICY


def test_the_bytes_go_only_to_the_diagnostic_directory_and_the_stored_message_stays_projected(tmp_path):
    retention, root = _retention(tmp_path)
    reasoning = SECRET + " " + MESSAGE
    transport = _retaining_transport(tmp_path, _post_script([_wire("turn on the lights", reasoning=reasoning)], []), retention,
                                     preserve_wire_responses=True)
    envelope = _send(transport, tmp_path)
    expected = root / "diagnostics" / DIAGNOSTIC_RUN_ID / "reasoning" / "5000001.txt"
    assert expected.read_bytes() == reasoning.encode("utf-8")
    receipt = envelope["reasoning_retention"]
    assert receipt == {"policy": RETAIN_DIAGNOSTIC_POLICY, "run_id": DIAGNOSTIC_RUN_ID, "relpath": "reasoning/5000001.txt",
                       "sha256": hashlib.sha256(reasoning.encode()).hexdigest(), "bytes": len(reasoning.encode()), "chars": len(reasoning)}
    # The sealed projection is unchanged: hash and statistics only, no bytes anywhere in the envelope or the stored wire response.
    assert envelope["reasoning"]["reasoning_content_sha256"] == receipt["sha256"]
    assert envelope["reasoning"]["reasoning_bytes_policy"] == REASONING_BYTES_POLICY
    stored = base64.b64decode(envelope["wire_response_b64"])
    assert b"RETAINED-DIAGNOSTIC-BYTES" not in stored and b'"reasoning_content"' not in stored
    assert "RETAINED-DIAGNOSTIC-BYTES" not in json.dumps({k: v for k, v in envelope.items() if k != "wire_response_b64"})
    # Nothing else was written under the data root.
    written = sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())
    assert written == [f"diagnostics/{DIAGNOSTIC_RUN_ID}/reasoning/5000001.txt"]


def test_a_non_default_budget_gets_its_own_file_and_a_second_attempt_never_overwrites(tmp_path):
    retention, root = _retention(tmp_path)
    transport = _retaining_transport(tmp_path, _post_script([_wire("x", reasoning=SECRET)], []), retention)
    _send(transport, tmp_path, budget=6144)
    assert (root / "diagnostics" / DIAGNOSTIC_RUN_ID / "reasoning" / "5000001.b6144.txt").is_file()
    with pytest.raises(FileExistsError):
        _send(transport, tmp_path, budget=6144)


def test_a_response_without_reasoning_writes_nothing(tmp_path):
    retention, root = _retention(tmp_path)
    transport = _retaining_transport(tmp_path, _post_script([_wire("x", reasoning=None)], []), retention)
    envelope = _send(transport, tmp_path)
    assert "reasoning_retention" not in envelope
    assert not (root / "diagnostics").exists()


def test_every_other_path_still_projects_the_bytes_out(tmp_path):
    """A default transport (no policy, no retention) writes no file and returns no retention receipt, whatever the knobs."""

    for kwargs in ({}, {"reasoning_bytes_policy": REASONING_BYTES_POLICY}):
        transport = _transport(_base_url(), tmp_path, post=_post_script([_wire("x", reasoning=SECRET)], []),
                               reasoning_content_guard=GUARD, reasoning_telemetry=True, forced_close_message=MESSAGE, **kwargs)
        envelope = _send(transport, tmp_path)
        assert "reasoning_retention" not in envelope and "RETAINED-DIAGNOSTIC-BYTES" not in json.dumps(envelope)
        assert envelope["reasoning"]["reasoning_bytes_policy"] == REASONING_BYTES_POLICY
    unguarded = _transport(_base_url(), tmp_path, post=_post_script([_wire("x", reasoning=SECRET)], []))
    envelope = json.loads(unguarded(json.dumps(_boundary_payload(tmp_path)).encode()))
    assert "RETAINED-DIAGNOSTIC-BYTES" not in json.dumps(envelope)
    assert not (tmp_path / "diagnostics").exists() and not list(tmp_path.rglob("*.txt"))
