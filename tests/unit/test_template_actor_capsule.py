"""Template actors receive only a bounded, immutable request and instructions."""
import copy
import hashlib
import json
from dataclasses import replace

import pytest

from speech_aware_evidence_acquisition.rails import system_context_exchange as exchange
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError
from test_system_context_iteration import iteration_fixture, run
from test_system_context_learning import pin, repin
from test_system_context_template_feedback import configure


def requests(tmp_path, monkeypatch):
    f = iteration_fixture(tmp_path, monkeypatch, algorithm="tf-grpo-context-diversity")
    plan = configure(f)
    plan["feedback_profile"]["examples_per_template"] = 0
    f.protocol["iteration_plan"] = pin(f.root, "iteration-plan.json", plan)
    repin(f)
    captured = []
    old = f.callbacks.propose
    def experience(task):
        captured.append(("update_experience", task))
        return {"value": [], "provenance": {"kind": "synthetic"},
                "usage": dict.fromkeys(("provider_contacts", "input_tokens", "output_tokens"), None)}
    def propose(task):
        captured.append(("propose", task))
        return old(task)
    f.callbacks = replace(f.callbacks, summarize=None, compare=None, update_experience=experience, propose=propose)
    assert run(f, "tf-grpo-context-diversity")["status"] == "retained-for-optimization"
    return captured


def prepare(tmp_path, stage, task, fault=None):
    task = copy.deepcopy(task)
    if fault == "knowledge": task["knowledge"] = {"entries": ["Specific answer"]}
    if fault == "sample-id": task["experience"] = {"bad": "slurp:train:42"}
    view = task if stage == "update_experience" else task["qualified_input"]
    if fault == "case": view["template_feedback"]["templates"][0]["examples"] = [{"answer": "Specific answer"}]
    if fault == "profile": view["template_feedback"]["profile"]["examples_per_template"] = 3
    if fault == "policy": view["policies"][next(iter(view["policies"]))]["policy"]["extra"] = "Hidden context"
    req = {"schema": "saea-context-callback-request-v1", "stage": stage,
           "algorithm": "tf-grpo-context-diversity", "iteration": 1,
           "task": task, "task_sha256": content_hash(task), "input_sha256": task["input_sha256"],
           "contact_authority": False}
    req["request_sha256"] = content_hash(req)
    expected = req["request_sha256"]
    if fault == "tamper": req["task"]["experience"] = {"tampered": "Changed after commitment"}
    if fault == "task-hash":
        req["task_sha256"] = "a" * 64
        req["request_sha256"] = expected = content_hash({k: v for k, v in req.items() if k != "request_sha256"})
    path = tmp_path / "request.json"
    path.write_text(json.dumps(req))
    instructions = tmp_path / "instructions.md"
    instructions.write_text("Optimize complete templates using aggregate outcomes only.\n")
    sha = hashlib.sha256(instructions.read_bytes()).hexdigest()
    if fault == "instructions": sha = "0" * 64
    if fault == "terminal": (tmp_path / "accepted.json").write_text("{}")
    args = dict(request_sha256=expected, instructions_path=instructions,
                instructions_sha256=sha, output_dir=tmp_path / "capsule",
                max_input_bytes=1 if fault == "bytes" else 262144)
    return path, args


def test_actual_batch_and_proposal_requests_make_two_file_capsules(tmp_path, monkeypatch):
    for i, (stage, task) in enumerate(requests(tmp_path, monkeypatch)):
        directory = tmp_path / str(i)
        directory.mkdir()
        path, args = prepare(directory, stage, task)
        manifest = exchange.prepare_template_actor_capsule(path, **args)
        assert len(manifest["allowed_files"]) == 2
        assert not manifest["contact_authority"] and not manifest["runtime_dispatch"]
        assert manifest["source_request"]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
        for p in manifest["allowed_files"]:
            assert hashlib.sha256(__import__("pathlib").Path(p["path"]).read_bytes()).hexdigest() == p["sha256"]
        assert manifest["input_bytes"] <= 262144
        with pytest.raises(FileExistsError):
            exchange.prepare_template_actor_capsule(path, **args)


@pytest.mark.parametrize("fault", ["knowledge", "sample-id", "case", "profile", "policy", "tamper", "task-hash", "instructions", "terminal", "bytes"])
def test_capsule_rejects_scope_expansion_and_broken_custody_before_publication(tmp_path, monkeypatch, fault):
    stage, task = requests(tmp_path, monkeypatch)[1]
    path, args = prepare(tmp_path, stage, task, fault)
    with pytest.raises(PolicyError):
        exchange.prepare_template_actor_capsule(path, **args)
    assert not args["output_dir"].exists()
    assert path.exists()