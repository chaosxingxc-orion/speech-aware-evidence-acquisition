"""A waiting callback is neither a failed proposal nor a new model contact."""

import json
import time
from concurrent.futures import ThreadPoolExecutor
import pytest
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError


def scope():
    return {
        "schema": "saea-context-callback-exchange-v1",
        "algorithm": "gepa",
        "iteration": 1,
        "plan_sha256": "a" * 64,
        "callback_caps": {
            "summarize": 0,
            "compare": 0,
            "update_experience": 0,
            "propose": 1,
            "evaluate": 1,
        },
        "actors": {
            "propose": "gpt-6.1-sol-subagent",
            "evaluate": "root-complete-family",
        },
        "timeout_seconds": 5,
        "poll_seconds": 0.01,
        "max_request_bytes": 100000,
        "max_response_bytes": 100000,
    }


def wait_request(root):
    until = time.monotonic() + 3
    while time.monotonic() < until:
        found = list(root.glob("requests/*/request.json"))
        if found:
            return found[-1]
        time.sleep(0.01)
    pytest.fail("request not published")


def envelope(value="No change."):
    return {
        "value": value,
        "provenance": {"source": "synthetic-original-response"},
        "usage": {
            "provider_contacts": None,
            "input_tokens": None,
            "output_tokens": None,
        },
    }


def test_external_wait_then_exact_response_preserves_request_usage_and_caps(tmp_path):
    from speech_aware_evidence_acquisition.rails.system_context_exchange import (
        ContextCallbackExchange,
        submit_response,
    )

    root = tmp_path / "exchange"
    x = ContextCallbackExchange(root, scope())
    task = {
        "input_sha256": "b" * 64,
        "candidate_id": "a",
        "instruction": "Preserve all evidence.",
    }
    with ThreadPoolExecutor() as pool:
        pending = pool.submit(x.callbacks().propose, task)
        request_path = wait_request(root)
        req = json.loads(request_path.read_text())
        assert req["task"] == task and req["task_sha256"] == content_hash(task)
        assert not pending.done()
        raw = envelope()
        submit_response(request_path, raw, actor="gpt-6.1-sol-subagent")
        result = pending.result(timeout=2)
    assert result["usage"]["provider_contacts"] is None
    assert (
        result["provenance"]["external_exchange"]["request_sha256"]
        == req["request_sha256"]
    )
    assert (
        json.loads((request_path.parent / "accepted.json").read_text())["stage"]
        == "propose"
    )
    with pytest.raises(PolicyError):
        x.callbacks().propose(task)
    with pytest.raises((PolicyError, FileExistsError)):
        submit_response(request_path, raw, actor="gpt-6.1-sol-subagent")
    with pytest.raises(FileExistsError):
        ContextCallbackExchange(root, scope())


@pytest.mark.parametrize("fault", ["actor", "task", "negative", "missing", "language"])
def test_malformed_response_retained_without_retry(tmp_path, fault):
    from speech_aware_evidence_acquisition.rails.system_context_exchange import (
        ContextCallbackExchange,
        submit_response,
    )

    root = tmp_path / "exchange"
    x = ContextCallbackExchange(root, scope())
    with ThreadPoolExecutor() as pool:
        pending = pool.submit(x.callbacks().propose, {"input_sha256": "b" * 64})
        path = wait_request(root)
        req = json.loads(path.read_text())
        raw = envelope()
        if fault == "negative":
            raw["usage"]["input_tokens"] = -1
        if fault == "missing":
            raw.pop("provenance")
        if fault == "language":
            raw["value"] = "\u4e2d\u6587"
        if fault in ("actor", "task"):
            response = {
                "schema": "saea-context-callback-response-v1",
                "request_sha256": req["request_sha256"],
                "actor": "gpt-6.1-sol-subagent",
                "response": raw,
            }
            if fault == "actor":
                response["actor"] = "other"
            else:
                response["request_sha256"] = "c" * 64
            (path.parent / "response.json").write_text(json.dumps(response))
        else:
            submit_response(path, raw, actor="gpt-6.1-sol-subagent")
        with pytest.raises(PolicyError):
            pending.result(timeout=2)
    assert (path.parent / "response.json").exists()
    assert (path.parent / "failed.json").exists()
    assert not (path.parent / "accepted.json").exists()
    with pytest.raises(PolicyError):
        x.callbacks().evaluate({"input_sha256": "b" * 64})


def test_timeout_is_terminal_and_preserves_outstanding_request(tmp_path):
    from speech_aware_evidence_acquisition.rails.system_context_exchange import (
        ContextCallbackExchange,
    )

    s = scope()
    s["timeout_seconds"] = 0.02
    x = ContextCallbackExchange(tmp_path / "exchange", s)
    with pytest.raises(TimeoutError):
        x.callbacks().propose({"input_sha256": "b" * 64})
    assert list(x.root.glob("requests/*/request.json"))
    assert list(x.root.glob("requests/*/failed.json"))
    with pytest.raises(PolicyError):
        x.callbacks().evaluate({"input_sha256": "b" * 64})


def test_evaluation_response_contains_bindings_not_scores(tmp_path):
    from speech_aware_evidence_acquisition.rails.system_context_exchange import (
        ContextCallbackExchange,
        submit_response,
    )

    x = ContextCallbackExchange(tmp_path / "exchange", scope())
    with ThreadPoolExecutor() as pool:
        pending = pool.submit(x.callbacks().evaluate, {"input_sha256": "b" * 64})
        path = wait_request(x.root)
        submit_response(path, envelope({"reward": 1}), actor="root-complete-family")
        with pytest.raises(PolicyError):
            pending.result(timeout=2)
    assert list(x.root.glob("requests/*/failed.json"))


@pytest.mark.parametrize("algorithm", ["gepa", "tf-grpo-context-diversity"])
def test_shared_iteration_waits_for_external_reflection_and_evaluation(
    tmp_path, monkeypatch, algorithm
):
    from speech_aware_evidence_acquisition.rails.system_context_exchange import (
        ContextCallbackExchange,
        submit_response,
    )
    from test_system_context_iteration import iteration_fixture, run

    f = iteration_fixture(tmp_path, monkeypatch, algorithm=algorithm)
    real_callbacks = f.callbacks
    s = scope()
    s["algorithm"] = algorithm
    s["max_request_bytes"] = 4000000
    s["callback_caps"] = {
        "summarize": 80,
        "compare": 20,
        "update_experience": 1,
        "propose": 4 if algorithm.startswith("tf") else 1,
        "evaluate": 1,
    }
    s["actors"] = {
        k: ("root-complete-family" if k == "evaluate" else "gpt-6.1-sol-subagent")
        for k in s["callback_caps"]
    }
    x = ContextCallbackExchange(tmp_path / "exchange", s)
    f.callbacks = x.callbacks()
    serviced = set()
    with ThreadPoolExecutor() as pool:
        pending = pool.submit(run, f, algorithm)
        deadline = time.monotonic() + 15
        while not pending.done() and time.monotonic() < deadline:
            for path in sorted(x.root.glob("requests/*/request.json")):
                if path in serviced:
                    continue
                req = json.loads(path.read_text())
                answer = getattr(real_callbacks, req["stage"])(req["task"])
                submit_response(path, answer, actor=req["actor"])
                serviced.add(path)
            time.sleep(0.005)
        decision = pending.result(timeout=2)
    assert decision["status"] == "retained-for-optimization"
    assert decision["accounting"]["provider_contacts"] is None
    assert decision["accounting"]["evaluation_candidate_trajectories_reserved"] == 80
    assert len(serviced) == (2 if algorithm == "gepa" else 101)
    assert len(list(x.root.glob("requests/*/accepted.json"))) == len(serviced)


@pytest.mark.parametrize(
    "fault", ["scope", "quota", "request-size", "family", "duplicate-json"]
)
def test_exchange_refuses_changed_scope_or_unbounded_work(tmp_path, fault):
    from speech_aware_evidence_acquisition.rails.system_context_exchange import (
        ContextCallbackExchange,
    )

    s = scope()
    if fault == "request-size":
        s["max_request_bytes"] = 1
    x = ContextCallbackExchange(tmp_path / "exchange", s)
    task = {"input_sha256": "b" * 64}
    if fault == "scope":
        (x.root / "scope.json").write_text("{}")
    elif fault == "family":
        x.input_sha256 = "c" * 64
    if fault in ("scope", "quota", "request-size", "family"):
        with pytest.raises(PolicyError):
            getattr(x.callbacks(), "summarize" if fault == "quota" else "propose")(task)
        assert not list(x.root.glob("requests/*/request.json"))
    else:
        with ThreadPoolExecutor() as pool:
            pending = pool.submit(x.callbacks().propose, task)
            path = wait_request(x.root)
            (path.parent / "response.json").write_text('{"schema":1,"schema":2}')
            with pytest.raises(PolicyError, match="duplicate"):
                pending.result(timeout=2)


def test_valid_evaluation_bindings_are_forwarded_without_claiming_qualification(
    tmp_path,
):
    from speech_aware_evidence_acquisition.rails.system_context_exchange import (
        ContextCallbackExchange,
        submit_response,
    )

    x = ContextCallbackExchange(tmp_path / "exchange", scope())
    with ThreadPoolExecutor() as pool:
        pending = pool.submit(x.callbacks().evaluate, {"input_sha256": "b" * 64})
        path = wait_request(x.root)
        submit_response(
            path,
            envelope({"bindings": [], "recipe_pin": {}}),
            actor="root-complete-family",
        )
        result = pending.result(timeout=2)
    assert result["value"] == {"bindings": [], "recipe_pin": {}}
    assert (
        result["provenance"]["external_exchange"]["actor_label_is_not_authentication"]
        is True
    )
    # The existing runner subsequently rejects unqualified bindings; this I/O layer does not qualify them.


@pytest.mark.parametrize("fault", [None, "unsigned", "plan", "algorithm", "crash"])
def test_external_iteration_entry_qualifies_before_creating_exchange(
    tmp_path, monkeypatch, fault
):
    from speech_aware_evidence_acquisition.rails import (
        system_context_exchange as exchange,
    )
    from speech_aware_evidence_acquisition.rails import (
        system_context_learning as learning,
    )

    s = scope()
    root = tmp_path / "exchange"

    def qualified(*a, **kw):
        if fault == "unsigned":
            raise PolicyError("unsigned READ")
        return ({}, {}, {}, {}, [], ["seed", "seed-aa"], {})

    monkeypatch.setattr(learning, "_qualified_feedback", qualified)
    monkeypatch.setattr(
        learning,
        "_iteration_plan",
        lambda *a: ({"sha256": "a" * 64}, {"callback_caps": scope()["callback_caps"]}),
    )

    def run(*a, **kw):
        assert (root / "scope.json").exists()
        if fault == "crash":
            raise RuntimeError("preserved synthetic failure")
        assert isinstance(kw["callbacks"], learning.ContextLearningCallbacks)
        return {"decision_sha256": "d" * 64, "status": "no-change"}

    monkeypatch.setattr(learning, "run_context_learning_iteration", run)
    if fault == "plan":
        s["plan_sha256"] = "c" * 64
    if fault == "algorithm":
        s["algorithm"] = "tf-grpo-context-diversity"
    kwargs = dict(
        archive=None,
        bindings=[],
        recipe_pin={},
        repo_root=tmp_path,
        algorithm="gepa",
        iteration=1,
        policies={},
        exchange_root=root,
        exchange_scope=s,
    )
    if fault:
        with pytest.raises((PolicyError, RuntimeError)):
            exchange.run_external_context_iteration(**kwargs)
        if fault == "crash":
            assert (
                json.loads((root / "worker-exit.json").read_text())["status"]
                == "failed"
            )
        else:
            assert not root.exists()
    else:
        d = exchange.run_external_context_iteration(**kwargs)
        assert (
            json.loads((root / "worker-exit.json").read_text())["decision_sha256"]
            == d["decision_sha256"]
        )
