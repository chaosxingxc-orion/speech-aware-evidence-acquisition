"""File handoff for externally serviced callbacks of the existing learner.

This adapter owns no provider, GPU queue, scoring, READ, retry or model admission.
A live learner waits for one exact response. A dead worker is not resumed here.
"""

from functools import partial
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import threading
import time

from .hashing import content_hash
from .prepared_feedback import reject_non_latin_scripts
from .system_context_learning import ContextLearningCallbacks
from .system_text_policy import (
    CONTEXT_LEARNING_ALGORITHMS,
    canonical,
    require,
    sha,
    PolicyError,
)

STAGES = ("summarize", "compare", "update_experience", "propose", "evaluate")


def _english(value):
    try:
        reject_non_latin_scripts(canonical(value))
    except ValueError as error:
        raise PolicyError(str(error)) from error


def _publish(path, document):
    """Publish complete bytes create-only; never expose a half-written response."""
    path = Path(path)
    raw = (canonical(document) + "\n").encode("utf-8")
    fd, scratch = tempfile.mkstemp(prefix=".publish-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(scratch, path)
    finally:
        os.unlink(scratch)


def _read(path, limit):
    path = Path(path)
    require(not path.is_symlink(), "exchange source cannot be a symlink")
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    require(len(raw) <= limit, "exchange source exceeds registered byte ceiling")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate exchange JSON field")
            result[key] = value
        return result

    document = json.loads(raw, object_pairs_hook=unique)
    canonical(document)
    return document, hashlib.sha256(raw).hexdigest()


class ContextCallbackExchange:
    """Wait in the original worker; the parent algorithm retains all decisions."""

    def __init__(self, root, scope):
        self.scope = json.loads(canonical(scope))
        s = self.scope
        require(
            set(s)
            == {
                "schema",
                "algorithm",
                "iteration",
                "plan_sha256",
                "callback_caps",
                "actors",
                "timeout_seconds",
                "poll_seconds",
                "max_request_bytes",
                "max_response_bytes",
            }
            and s["schema"] == "saea-context-callback-exchange-v1"
            and s["algorithm"] in CONTEXT_LEARNING_ALGORITHMS
            and type(s["iteration"]) is int
            and s["iteration"] > 0,
            "exchange scope differs",
        )
        sha(s["plan_sha256"])
        caps = s["callback_caps"]
        require(
            isinstance(caps, dict)
            and set(caps) == set(STAGES)
            and all(type(v) is int and v >= 0 for v in caps.values())
            and set(s["actors"]) == {k for k, v in caps.items() if v}
            and all(isinstance(v, str) and v.strip() for v in s["actors"].values()),
            "explicit callback caps and actor identities required",
        )
        for key in ("timeout_seconds", "poll_seconds"):
            require(
                type(s[key]) in (int, float) and math.isfinite(s[key]) and s[key] > 0,
                "finite positive wait bounds required",
            )
        require(s["poll_seconds"] <= s["timeout_seconds"], "poll exceeds wait deadline")
        require(
            all(
                type(s[k]) is int and s[k] > 0
                for k in ("max_request_bytes", "max_response_bytes")
            ),
            "positive byte ceilings required",
        )
        _english(s)
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=False)
        (self.root / "requests").mkdir()
        _publish(self.root / "scope.json", s)
        _publish(
            self.root / "worker.json",
            {
                "pid": os.getpid(),
                "started_unix": time.time(),
                "scope_sha256": content_hash(s),
                "model_contacts_added": 0,
                "restart_allowed": False,
            },
        )
        self.counts = dict.fromkeys(STAGES, 0)
        self.input_sha256 = None
        self.failed = False
        self.lock = threading.Lock()

    def callbacks(self):
        return ContextLearningCallbacks(
            **{stage: partial(self.invoke, stage) for stage in STAGES}
        )

    def invoke(self, stage, task):
        require(self.lock.acquire(blocking=False), "only one callback may be pending")
        directory = None
        try:
            require(
                not self.failed and stage in STAGES,
                "exchange is failed or stage invalid",
            )
            require(
                self.counts[stage] < self.scope["callback_caps"][stage],
                "callback quota spent; no retry",
            )
            require(
                _read(self.root / "scope.json", 1048576)[0] == self.scope,
                "exchange scope changed",
            )
            canonical(task)
            _english(task)
            identity = task.get("input_sha256")
            sha(identity)
            require(
                self.input_sha256 in (None, identity), "callback input family changed"
            )
            self.input_sha256 = identity
            request = {
                "schema": "saea-context-callback-request-v1",
                "stage": stage,
                "ordinal": sum(self.counts.values()),
                "algorithm": self.scope["algorithm"],
                "iteration": self.scope["iteration"],
                "scope_sha256": content_hash(self.scope),
                "plan_sha256": self.scope["plan_sha256"],
                "actor": self.scope["actors"][stage],
                "task": task,
                "task_sha256": content_hash(task),
                "input_sha256": identity,
                "contact_authority": False,
            }
            request["request_sha256"] = content_hash(request)
            require(
                len(canonical(request).encode("utf-8")) + 1
                <= self.scope["max_request_bytes"],
                "request exceeds registered byte ceiling",
            )
            directory = self.root / "requests" / f"{request['ordinal']:04d}-{stage}"
            directory.mkdir(exist_ok=False)
            self.counts[stage] += 1
            _publish(directory / "request.json", request)
            deadline = time.monotonic() + self.scope["timeout_seconds"]
            response_path = directory / "response.json"
            while not response_path.exists():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(
                        "External callback deadline elapsed; preserve pending evidence"
                    )
                time.sleep(min(self.scope["poll_seconds"], remaining))
            response, response_sha = _read(
                response_path, self.scope["max_response_bytes"]
            )
            require(
                set(response) == {"schema", "request_sha256", "actor", "response"}
                and response["schema"] == "saea-context-callback-response-v1"
                and response["request_sha256"] == request["request_sha256"]
                and response["actor"] == request["actor"],
                "response identity differs",
            )
            require(
                _read(self.root / "scope.json", 1048576)[0] == self.scope,
                "exchange scope changed",
            )
            envelope = response["response"]
            require(
                isinstance(envelope, dict)
                and set(envelope) == {"value", "provenance", "usage"}
                and isinstance(envelope["provenance"], dict)
                and envelope["provenance"]
                and "external_exchange" not in envelope["provenance"],
                "original provenance envelope required",
            )
            usage = envelope["usage"]
            require(
                isinstance(usage, dict)
                and set(usage) == {"provider_contacts", "input_tokens", "output_tokens"}
                and all(v is None or type(v) is int and v >= 0 for v in usage.values()),
                "measured nonnegative or unknown usage required",
            )
            _english(envelope)
            if stage == "evaluate":
                require(
                    isinstance(envelope["value"], dict)
                    and set(envelope["value"]) == {"bindings", "recipe_pin"},
                    "evaluation must return complete source bindings, not rewards",
                )
            envelope["provenance"]["external_exchange"] = {
                "request_path": str(directory / "request.json"),
                "request_sha256": request["request_sha256"],
                "response_path": str(response_path),
                "response_sha256": response_sha,
                "actor_label": request["actor"],
                "actor_label_is_not_authentication": True,
            }
            _publish(
                directory / "accepted.json",
                {
                    "stage": stage,
                    "request_sha256": request["request_sha256"],
                    "response_sha256": response_sha,
                },
            )
            return envelope
        except Exception as error:
            self.failed = True
            if directory is not None:
                _publish(
                    directory / "failed.json",
                    {
                        "stage": stage,
                        "error_type": type(error).__name__,
                        "retry_allowed": False,
                        "original_sources_preserved": True,
                    },
                )
            raise
        finally:
            self.lock.release()


def submit_response(request_path, envelope, *, actor):
    """Preserve a response once. The waiting adapter validates it without repair.

    This write does not certify model identity, costs, READ or dispatch authority.
    The coordinator must retain original agent/runtime receipts in provenance.
    """
    path = Path(request_path).resolve()
    request, _ = _read(path, 64 * 1024 * 1024)
    require(
        request.get("schema") == "saea-context-callback-request-v1"
        and request.get("request_sha256")
        == content_hash({k: v for k, v in request.items() if k != "request_sha256"}),
        "request commitment differs",
    )
    require(
        not any(
            (path.parent / name).exists() for name in ("failed.json", "accepted.json")
        ),
        "terminal request cannot accept another response",
    )
    _publish(
        path.parent / "response.json",
        {
            "schema": "saea-context-callback-response-v1",
            "request_sha256": request["request_sha256"],
            "actor": actor,
            "response": envelope,
        },
    )


def run_external_context_iteration(
    *,
    archive,
    bindings,
    recipe_pin,
    repo_root,
    algorithm,
    iteration,
    policies,
    exchange_root,
    exchange_scope,
    previous_decision_sha256=None,
):
    """Qualify source and plan before exposing any asynchronous callback request.

    Each external actor still needs separate prospective contact admission. This
    entry runs the original algorithm, without an alternative retention policy.
    """
    from . import system_context_learning as learning

    qualified = learning._qualified_feedback(
        bindings, recipe_pin=recipe_pin, repo_root=repo_root
    )
    _, recipe, _, protocol, _, controls, _ = qualified
    plan_pin, plan = learning._iteration_plan(
        protocol, recipe, Path(repo_root), algorithm, iteration, controls
    )
    require(
        exchange_scope.get("algorithm") == algorithm
        and exchange_scope.get("iteration") == iteration
        and exchange_scope.get("plan_sha256") == plan_pin["sha256"]
        and exchange_scope.get("callback_caps") == plan["callback_caps"],
        "exchange differs from exact qualified iteration plan",
    )
    exchange = ContextCallbackExchange(exchange_root, exchange_scope)
    try:
        decision = learning.run_context_learning_iteration(
            archive,
            bindings=bindings,
            recipe_pin=recipe_pin,
            repo_root=repo_root,
            algorithm=algorithm,
            iteration=iteration,
            policies=policies,
            callbacks=exchange.callbacks(),
            previous_decision_sha256=previous_decision_sha256,
        )
    except Exception as error:
        _publish(
            exchange.root / "worker-exit.json",
            {
                "status": "failed",
                "error_type": type(error).__name__,
                "original_sources_preserved": True,
                "restart_allowed": False,
            },
        )
        raise
    _publish(
        exchange.root / "worker-exit.json",
        {
            "status": decision["status"],
            "decision_sha256": decision["decision_sha256"],
            "restart_allowed": False,
        },
    )
    return decision


def prepare_template_actor_capsule(request_path, *, request_sha256, instructions_path,
                                   instructions_sha256, output_dir, max_input_bytes):
    """Snapshot a zero-case template request; never admit or dispatch an actor.

    Root must bind these exact bytes to a separate prospective actor receipt.
    Source paths are custody references, not permission to open other material.
    """
    from .system_context_template_feedback import validate_template_profile
    import re

    require(type(max_input_bytes) is int and max_input_bytes > 0, "positive capsule byte ceiling required")
    sha(request_sha256)
    sha(instructions_sha256)
    path = Path(request_path)
    request, source_sha = _read(path, max_input_bytes)
    require(request.get("schema") == "saea-context-callback-request-v1"
            and request.get("request_sha256") == request_sha256
            == content_hash({k: v for k, v in request.items() if k != "request_sha256"}),
            "capsule request commitment differs")
    require(not any((path.parent / name).exists() for name in
                    ("response.json", "accepted.json", "failed.json")),
            "capsule requires an unconsumed request")
    stage = request.get("stage")
    require(stage in ("update_experience", "propose"), "template semantic stage required")
    task = request["task"]
    require(request.get("task_sha256") == content_hash(task)
            and request.get("input_sha256") == task.get("input_sha256"), "capsule task commitment differs")
    expected = ({"input_sha256", "experience", "template_feedback", "policies", "reflection_task"}
                if stage == "update_experience" else
                {"input_sha256", "candidate_id", "algorithm", "iteration", "parent_bundle_id",
                 "component", "policy", "experience", "qualified_input"})
    if stage == "update_experience" and "rejected_trial_feedback" in task:
        expected.add("rejected_trial_feedback")
    require(set(task) == expected, "template task fields differ")
    view = task if stage == "update_experience" else task["qualified_input"]
    feedback = view["template_feedback"]
    profile = validate_template_profile(feedback["profile"])
    require(profile["examples_per_template"] == 0
            and all(t["examples"] == [] for t in feedback["templates"]), "aggregate-only capsule required")
    views = [view]
    if "rejected_trial_feedback" in view:
        history = view["rejected_trial_feedback"]
        require(set(history) == {"schema", "previous_decision_sha256", "status", "promoted_to_parent",
                    "source_recipe", "family_commitment", "policies", "template_feedback"}
                and history["schema"] == "saea-rejected-template-history-v1"
                and history["status"] == "rejected" and history["promoted_to_parent"] is False,
                "rejected history view differs")
        sha(history["previous_decision_sha256"])
        history_profile = validate_template_profile(history["template_feedback"]["profile"])
        require(history_profile == profile
                and all(t["examples"] == [] for t in history["template_feedback"]["templates"]),
                "historical feedback must remain aggregate-only")
        views.append(history)
    require(all(len(v["policies"]) == 4 for v in views), "complete four-system template view required")
    policy_views = [p["policy"] for v in views for p in v["policies"].values()]
    if stage == "propose":
        policy_views.append(task["policy"])
    for policy in policy_views:
        require(set(policy) == {"schema", "source_policy_sha256", "role_text", "context_layout", "node_context"}
                and policy["schema"] == "saea-template-policy-view-v1", "template policy view fields differ")
        sha(policy["source_policy_sha256"])
    forbidden = {"knowledge", "construction_instruction", "construction_receipt", "supply",
                 "cumulative_sources", "unsampled_sample_ids", "groups", "official_summaries",
                 "comparisons", "summary_tasks"}
    def check(value):
        if isinstance(value, dict):
            require(not forbidden.intersection(value), "excluded material in template actor task")
            for item in value.values(): check(item)
        elif isinstance(value, list):
            for item in value: check(item)
    check(task)
    require(re.search(r"slurp:(?:train|dev|test):", canonical(task)) is None,
            "individual sample identifiers excluded from template actor task")
    _english(request)
    instruction_path = Path(instructions_path)
    require(not instruction_path.is_symlink(), "capsule instructions cannot be a symlink")
    with instruction_path.open("rb") as stream:
        instruction_bytes = stream.read(max_input_bytes + 1)
    require(hashlib.sha256(instruction_bytes).hexdigest() == instructions_sha256,
            "capsule instruction commitment differs")
    instructions = instruction_bytes.decode("utf-8")
    _english(instructions)
    input_bytes = len((canonical(request) + "\n").encode("utf-8")) + len(instruction_bytes)
    require(input_bytes <= max_input_bytes, "capsule exceeds registered byte ceiling")
    directory = Path(output_dir).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    _publish(directory / "request.json", request)
    with (directory / "instructions.md").open("xb") as stream:
        stream.write(instruction_bytes)
    def pin(p):
        return {"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size}
    manifest = {"schema": "saea-template-actor-capsule-v1", "stage": stage,
        "source_request": {"path": str(path.resolve()), "sha256": source_sha},
        "request_sha256": request_sha256, "instructions_sha256": instructions_sha256,
        "allowed_files": [pin(directory / "request.json"), pin(directory / "instructions.md")],
        "input_bytes": input_bytes, "max_input_bytes": max_input_bytes,
        "output": str(directory / "original-response.json"),
        "contact_authority": False, "runtime_dispatch": False, "automatic_retry": False,
        "bounds_are_token_limits": False}
    _publish(directory / "manifest.json", manifest)
    return manifest