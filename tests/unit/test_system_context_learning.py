"""Synthetic offline learner inputs retain custody, controls and deterministic identity."""

import copy
import json
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails import system_context_learning as learning
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_search_archive import SystemSearchArchive
from speech_aware_evidence_acquisition.rails.system_text_feedback import CompleteSystemFeedback
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    PolicyError, SystemTextPolicyBundle, TextPolicyUpdateProposal, canonical,
)
from test_system_text_policy import seed_document


def pin(root, name, document):
    import hashlib
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical(document))
    return {"relpath": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def setup(tmp_path, monkeypatch):
    ids = [f"slurp:train:{i}" for i in range(400)]
    candidates = [f"context-{i}" for i in range(4)]
    controls = ["seed", "seed-aa"]
    policies = {}
    for i, cid in enumerate(candidates):
        doc = seed_document()
        doc.update(schema="saea-system-text-policy-bundle-v3",
                   context_layout={"native_role_query_placement": None},
                   node_context={"tool_schema_rendering": "constant", "reviewer_history_scope": "full"})
        doc["role_text"]["perception"] = f"Preserve observed speech evidence for context {i}."
        policies[cid] = SystemTextPolicyBundle.from_json(doc)
    owner = {"schema": "saea-owner-deterministic-context-rollouts-v1", "resolved_contract": {
        "initial_N": 20, "initial_K": 4, "M": ["perception", "solver", "reviewer", "planner"],
        "temperature": 0, "seed": 20260913}}
    reference_spec = {"family_id": "initial", "expected_members": {"seed": "old-seed", "seed-aa": "old-aa"},
                      "read_registration": {"relpath": "old-recipe.json", "sha256": "a" * 64},
                      "initial_reference_member": "seed", "reference_family": None}
    protocol = {"schema": "saea-context-learning-protocol-v1", "family_id": "context-initial20-v1",
        "iteration": 1, "candidate_members": candidates, "control_members": controls,
        "N": 20, "K": 4, "M": owner["resolved_contract"]["M"],
        "sampling": {"temperature": 0, "seed": 20260913},
        "owner": pin(tmp_path, "owner.json", owner), "fixed_roster": pin(tmp_path, "pool.json", {"sample_ids": ids}),
        "frozen_reference": pin(tmp_path, "reference-spec.json", reference_spec),
        "algorithms": ["tf-grpo-context-diversity", "gepa"], "automatic_expansion": False,
        "independent_validation": False,
        "measurement_profile": {"schema": "saea-system-search-measurement-profile-v1", "slot_count": 4,
            "queue_depth": 4, "required_objectives": ["slu_f1", "intent", "model_calls", "tool_calls",
                "mean_sample_seconds", "mean_nonfirst_sample_seconds", "reliable_completion_rate"]}}
    # Reuse the real profile fixture rather than introducing a second profile dialect.
    from test_system_optimization_stage import measurement_profile
    protocol["measurement_profile"] = measurement_profile()
    members = candidates + controls
    bindings = {cid: {"run_id": "run-" + cid, "attempt_id": "attempt-" + cid,
        "config_hash": content_hash(cid), "bundle_id": policies[cid].bundle_id if cid in policies else "f" * 64}
        for cid in members}
    registration = {"schema": "saea-context-learning-registration-v1", "family_id": protocol["family_id"],
        "protocol": pin(tmp_path, "protocol.json", protocol), "member_bindings": bindings,
        "expected_members": {c: b["run_id"] for c, b in bindings.items()}, "read_id": "CONTEXT-READ-V1",
        "measurement_profile": copy.deepcopy(protocol["measurement_profile"])}
    registration["registration_sha256"] = content_hash(registration)
    recipe = {"schema": "saea-context-learning-analysis-v1", "family_id": protocol["family_id"],
        "expected_members": registration["expected_members"], "sample_ids": ids[:20],
        "required_rows_per_member": 20, "run_ids": {"read": registration["read_id"]},
        "measurement_profile": copy.deepcopy(protocol["measurement_profile"]),
        "context_learning_registration": pin(tmp_path, "registration.json", registration)}
    recipe_pin = pin(tmp_path, "recipe.json", recipe)
    sources = [{"candidate_id": cid, **bindings[cid]} for cid in members]
    groups = []
    for i, sid in enumerate(ids[:20]):
        rows = []
        for j, cid in enumerate(members):
            # First row has exactly equal utility, later rows include negative utility.
            counts = {f"slu_f1_{a}_{k}": (0 if i == 0 else (j if k == "tp" else 1))
                      for a in ("word", "char") for k in ("tp", "fp", "fn")}
            execution = {"model_calls": 4 + j, "tool_calls": 0, "prompt_tokens": None,
                "completion_tokens": None, "wall_time_seconds": 1 + j, "delivery_kind": "abstention" if j == 0 else "accepted",
                "reliable_completion": j != 0, "abstained": j == 0, "missing_model_responses": 1 if j == 0 else 0,
                "sample_timing": {"elapsed_seconds": 1 + j, "position": i}, "trace": {"sha256": "b" * 64}}
            rows.append({"candidate_id": cid, "native_counts": counts, "execution": execution})
        groups.append({"sample_id": sid, "members": rows})
    evidence = {"schema": "saea-context-learning-feedback-v1", "family_id": protocol["family_id"],
        "summaries": {c: {"slu_f1": .6, "mean_sample_seconds": 2} for c in members},
        "feedback": {"carrier_lock_key": "slurp", "candidate_ids": members, "sources": sources, "groups": groups}}
    from test_system_search_measurement import timing
    evidence["measurement_profile"] = protocol["measurement_profile"]
    for j, cid in enumerate(members):
        evidence["summaries"][cid].update(intent=.8, model_calls=20 * (4 + j), tool_calls=0,
            reliable_completion_rate=0 if j == 0 else 1,
            sample_timing=timing(ids[:20], seconds=1 + j, failed=j == 0), timing_session_sha256="e" * 64)
    reference = CompleteSystemFeedback(canonical({"schema": "saea-complete-system-feedback-v1",
        "reference": {"family_id": "initial", "candidate_id": "seed", "source_sha256": "c" * 64,
                      "sample_ids": ids, "f1": .6}}))
    events = []
    authority = {"read_run_id": "CONTEXT-READ-V1", "recipe": recipe_pin, "ledger_row_sha256": "a" * 64}
    cli = SimpleNamespace(require_read_registration=lambda *a, **kw: (events.append("read-gate") or authority),
                          read_family=lambda *a, **kw: (events.append("reference") or reference))
    monkeypatch.setattr(learning, "_read_cli", lambda root: cli)
    monkeypatch.setattr(learning, "_job_metadata", lambda b: (events.append("jobs") or {"job": "a" * 64}))
    def complete(*a, **kw):
        events.append("complete-family")
        return CompleteSystemFeedback(canonical({**evidence, "read_authority": kw["authority"],
            "registration_sha256": kw["registration"]["registration_sha256"]}))
    monkeypatch.setattr(learning, "_read_complete_evidence", complete)
    archive = SystemSearchArchive(tmp_path / "archive")
    return SimpleNamespace(root=tmp_path, recipe=recipe, recipe_pin=recipe_pin, registration=registration,
        protocol=protocol, policies=policies, bindings=[{"candidate_id": c} for c in members],
        evidence=evidence, reference=reference, archive=archive, events=events, cli=cli)


def prepare(f, algorithm="tf-grpo-context-diversity", **kwargs):
    return learning.prepare_context_optimizer_input(f.archive, bindings=f.bindings,
        recipe_pin=f.recipe_pin, repo_root=f.root, algorithm=algorithm, iteration=1,
        policies=f.policies, **kwargs)


def repin(f):
    f.registration["protocol"] = pin(f.root, "protocol.json", f.protocol)
    f.registration["registration_sha256"] = content_hash({k: v for k, v in f.registration.items() if k != "registration_sha256"})
    f.recipe["context_learning_registration"] = pin(f.root, "registration.json", f.registration)
    f.recipe_pin = pin(f.root, "recipe.json", f.recipe)
    f.cli.require_read_registration = lambda *a, **kw: {"read_run_id": "CONTEXT-READ-V1", "recipe": f.recipe_pin, "ledger_row_sha256": "a" * 64}


def test_tf_input_exact_n_k_retains_controls_costs_and_zero_variation(tmp_path, monkeypatch):
    f = setup(tmp_path, monkeypatch)
    packet = prepare(f, experiences={"G1": "Check evidence boundaries."})
    assert packet["budget"] == {"N": 20, "K": 4, "M": 4, "candidate_trajectories": 80,
        "control_trajectories": 40, "family_trajectories": 120, "minimum_initial_node_visits_if_complete": 320}
    assert len(packet["groups"]) == 20 and all(len(g["members"]) == 4 for g in packet["groups"])
    assert packet["groups"][0]["semantic_advantage"] == "skip-zero-variation"
    assert packet["groups"][1]["members"][0]["utility"] < 0
    assert "relative_return" not in canonical(packet)
    assert packet["groups"][1]["members"][0]["execution"]["missing_model_responses"] == 1
    assert all(not m["candidate_id"].startswith("seed") for g in packet["groups"] for m in g["members"])
    assert packet["family_commitment"]["member_ids"] == list(f.registration["member_bindings"])
    assert f.events.index("complete-family") < f.events.index("reference")
    assert packet["experience"] == {"G1": "Check evidence boundaries."}
    assert len(packet["business_measurements"]) == 4
    assert packet["business_measurements"][0]["eligible"] is False
    assert packet["business_measurements"][0]["mean_sample_seconds"] == 1
    assert packet["business_measurements"][0]["non_first_mean_seconds"] == 1
    with pytest.raises(PolicyError, match="exists|consumed"):
        prepare(f)


@pytest.mark.parametrize("fault", ["omitted-control", "duplicate-input", "wrong-pool", "temperature", "seed", "K1", "N400",
    "same-bundle", "config", "missing-member", "duplicate-group", "missing-source", "profile", "algorithm", "protocol-hash"])
def test_refuse_malformed_scope_or_incomplete_feedback(tmp_path, monkeypatch, fault):
    f = setup(tmp_path, monkeypatch)
    if fault == "omitted-control":
        f.bindings.pop()
    elif fault == "duplicate-input":
        f.recipe["sample_ids"][1] = f.recipe["sample_ids"][0]
    elif fault == "wrong-pool":
        f.recipe["sample_ids"].reverse()
    elif fault in {"temperature", "seed"}:
        f.protocol["sampling"][fault] += 1
    elif fault == "K1":
        f.protocol["K"] = 1
    elif fault == "N400":
        f.protocol["N"] = 400
    elif fault == "same-bundle":
        f.registration["member_bindings"]["context-1"]["bundle_id"] = f.policies["context-0"].bundle_id
    elif fault == "config":
        f.evidence["feedback"]["sources"][0]["config_hash"] = "d" * 64
    elif fault == "missing-member":
        f.evidence["feedback"]["groups"][0]["members"].pop()
    elif fault == "duplicate-group":
        f.evidence["feedback"]["groups"][1] = copy.deepcopy(f.evidence["feedback"]["groups"][0])
    elif fault == "missing-source":
        f.evidence["feedback"]["sources"].pop()
    elif fault == "profile":
        f.recipe["measurement_profile"]["queue_depth"] = 3
    elif fault == "algorithm":
        f.protocol["algorithms"] = ["gepa", "other"]
    repin(f)
    if fault == "protocol-hash":
        (f.root / "protocol.json").write_text("{}")
    with pytest.raises((PolicyError, KeyError)):
        prepare(f)
    assert not (f.archive.root / "context-learning").exists()


def test_no_caller_feedback_or_numeric_reference_authority(tmp_path, monkeypatch):
    f = setup(tmp_path, monkeypatch)
    f.cli.require_read_registration = lambda *a, **kw: (_ for _ in ()).throw(PolicyError("not countersigned"))
    with pytest.raises(PolicyError, match="countersigned"):
        prepare(f)
    assert f.events == []


@pytest.mark.parametrize("fault", ["test", "noninitial", "f1", "hash"])
def test_original_reference_scope_is_checked(tmp_path, monkeypatch, fault):
    f = setup(tmp_path, monkeypatch)
    d = f.reference.as_json()
    if fault == "test":
        d["reference"]["sample_ids"][0] = "slurp:test:0"
    elif fault == "noninitial":
        d["reference"]["family_id"] = "milestone"
    elif fault == "f1":
        d["reference"]["f1"] = 2
    else:
        d["reference"]["source_sha256"] = "not-a-hash"
    f.cli.read_family = lambda *a, **kw: CompleteSystemFeedback(canonical(d))
    with pytest.raises(PolicyError):
        prepare(f)


def test_gepa_per_example_front_and_component_task_are_distinct(tmp_path, monkeypatch):
    f = setup(tmp_path, monkeypatch)
    p = prepare(f, "gepa", candidate_id="context-3", component="role_text.reviewer")
    assert p["per_example_front"][p["groups"][0]["sample_id"]] == list(f.policies)
    assert p["per_example_front"][p["groups"][1]["sample_id"]] == ["context-3"]
    assert p["reflection_task"]["component"] == "role_text.reviewer"
    assert "experience_operations" not in p["reflection_task"]
    assert "cost_frontier" not in p
    assert p["reflection_task"]["parent_bundle_id"] == f.policies["context-3"].bundle_id


@pytest.mark.parametrize("component", ["knowledge", "temperature", "role_text.unknown"])
def test_gepa_forbids_non_context_mutation(tmp_path, monkeypatch, component):
    f = setup(tmp_path, monkeypatch)
    with pytest.raises(PolicyError):
        prepare(f, "gepa", candidate_id="context-3", component=component)


def response(packet, *, changes=None):
    return {"schema": "saea-context-policy-update-proposal-v1", "algorithm": packet["algorithm"],
        "iteration": packet["iteration"], "candidate_id": "context-3", "component": "role_text.reviewer" if packet["algorithm"] == "gepa" else "joint-system",
        "parent_ids": [packet["policies"]["context-3"]["bundle_id"]],
        "changes": {} if changes is None else changes, "rationale": "Check source-grounded review.",
        "hypotheses": ["Preserve legal role boundaries."], "evidence": [packet["input_sha256"]]}


@pytest.mark.parametrize("kind", ["valid", "no-change", "invalid", "wrong-parent", "wrong-component", "wrong-iteration"])
def test_update_records_are_immutable_and_materialize_only_legal_edits(tmp_path, monkeypatch, kind):
    f = setup(tmp_path, monkeypatch)
    p = prepare(f, "gepa", candidate_id="context-3", component="role_text.reviewer")
    d = response(p, changes={"role_text": {"reviewer": "Check each proposed entity against observed evidence."}})
    if kind == "no-change":
        d["changes"] = {}
    elif kind == "invalid":
        d["changes"]["temperature"] = .7
    elif kind == "wrong-parent":
        d["parent_ids"] = ["a" * 64]
    elif kind == "wrong-component":
        d["changes"]["role_text"]["solver"] = "Alter another component."
    elif kind == "wrong-iteration":
        d["iteration"] = 2
    record = learning.record_context_update(f.archive, input_sha256=p["input_sha256"],
        update_id="reviewer-update-1", proposal_document=d)
    assert record["status"] == ("provisional" if kind == "valid" else "no-change" if kind == "no-change" else "invalid")
    assert record["runtime_admission"] is False
    assert record["raw_proposal"] == d
    if kind == "valid":
        child = f.archive.load_policy(record["bundle_id"])
        assert child.as_json()["role_text"]["reviewer"] == d["changes"]["role_text"]["reviewer"]
        assert child.as_json()["knowledge"] == f.policies["context-3"].as_json()["knowledge"]
        assert p["input_sha256"] in [s["sha256"] for s in child.as_json()["cumulative_sources"]]
    with pytest.raises(PolicyError, match="exists|consumed"):
        learning.record_context_update(f.archive, input_sha256=p["input_sha256"], update_id="reviewer-update-1", proposal_document=d)
    assert not (f.archive.root / "proposals").exists()


def test_proposal_has_no_legacy_slot_alias_and_legacy_parser_refuses_it(tmp_path, monkeypatch):
    f = setup(tmp_path, monkeypatch)
    p = prepare(f)
    d = response(p, changes={"context_layout": {"native_role_query_placement": "before-speech-v1"}})
    parsed = TextPolicyUpdateProposal.from_context_json(d)
    assert parsed.as_json() == d
    with pytest.raises(PolicyError):
        TextPolicyUpdateProposal.from_json(d)
    d["slot"] = 1
    with pytest.raises(PolicyError):
        TextPolicyUpdateProposal.from_context_json(d)


def test_semantic_experience_operations_preserve_rejected_history_seam():
    original = {"G1": "Check speech support.", "G2": "Preserve uncertainty."}
    result = learning.apply_experience_operations(original, [
        {"operation": "keep", "id": "G1"}, {"operation": "delete", "id": "G2"},
        {"operation": "add", "id": "G3", "text": "Check bidirectional coverage."},
        {"operation": "modify", "id": "G1", "text": "Check direct speech support."}])
    assert result == {"G1": "Check direct speech support.", "G3": "Check bidirectional coverage."}
    assert original["G1"] == "Check speech support."
    for operations in ([{"operation": "add", "id": "G1", "text": "Duplicate."}],
                       [{"operation": "gradient", "id": "G1"}], [{"operation": "delete", "id": "absent"}]):
        with pytest.raises(PolicyError):
            learning.apply_experience_operations(original, operations)


def real_custody(f, monkeypatch):
    """Keep operational custody and shared reader real; stub synthetic score decoding."""
    import hashlib
    from speech_aware_evidence_acquisition.analysis import system_text_panel as panel
    from speech_aware_evidence_acquisition.analysis import system_text_pilot as pilot
    def save(path, document):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(canonical(document))
        return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    actual = []
    for cid, expected in f.registration["member_bindings"].items():
        directory = f.root / "runs" / expected["run_id"] / expected["attempt_id"]
        state = directory / "attempt.json"
        save(state, {"state": "FINALIZED", "run_id": expected["run_id"], "attempt_id": expected["attempt_id"]})
        manifest_path = directory / "run.json"
        manifest = {"status": "COMPLETED", "run_id": expected["run_id"],
            "plan": {"split_role": "discovery"}, "config": {"config_hash": expected["config_hash"]},
            "split": {"count": 20, "ids": f.recipe["sample_ids"]},
            "attempt": {"state_path": str(state), "attempt_id": expected["attempt_id"]}}
        roster = save(directory / "roster.json", {"items": [{"sample_id": s} for s in f.recipe["sample_ids"]]})
        mp = save(manifest_path, manifest)
        job = {"job_id": expected["attempt_id"], "manifest": str(manifest_path)}
        save(directory / "score-jobs.jsonl", job)
        save(directory / "score-batch/batch-summary.json", {"job_count": 1, "succeeded": 1, "failed": 0,
            "include_per_sample": True, "jobs": [{**job, "returncode": 0, "status": "succeeded", "operation": "finalize"}]})
        actual.append({"candidate_id": cid, "config": {"manifest": mp, "construction_roster": roster}})
    f.bindings = actual
    monkeypatch.setattr(learning, "_job_metadata", panel._job_metadata)
    monkeypatch.setattr(learning, "_read_complete_evidence", pilot._read_complete_evidence)
    monkeypatch.setattr(pilot, "verify_bundle", lambda path: (f.events.append("seal-" + path.parent.name)
        or SimpleNamespace(attempt_state="FINALIZED")))
    monkeypatch.setattr(pilot, "build_group_relative_feedback", lambda b: (f.events.append("score-counts")
        or copy.deepcopy(f.evidence["feedback"])))
    rows = {c: {g["sample_id"]: next(m["execution"] for m in g["members"] if m["candidate_id"] == c)
        for g in f.evidence["feedback"]["groups"]} for c in f.registration["member_bindings"]}
    monkeypatch.setattr(pilot, "_official_family_rows", lambda *a, **k: (rows, f.evidence["summaries"]))


def test_real_shared_reader_checks_all_six_seals_before_counts_and_reference(tmp_path, monkeypatch):
    f = setup(tmp_path, monkeypatch)
    real_custody(f, monkeypatch)
    p = prepare(f)
    assert p["read_authority"]["recipe"] == f.recipe_pin
    assert len([e for e in f.events if e.startswith("seal-")]) == 6
    assert f.events.index("score-counts") > max(i for i, e in enumerate(f.events) if e.startswith("seal-"))
    assert f.events.index("reference") > f.events.index("score-counts")


@pytest.mark.parametrize("fault", ["unfinalized-control", "bad-seal", "duplicate-score", "failed-score", "config", "roster"])
def test_real_shared_reader_refuses_before_any_score_count_read(tmp_path, monkeypatch, fault):
    f = setup(tmp_path, monkeypatch)
    real_custody(f, monkeypatch)
    binding = f.bindings[-1]
    path = __import__("pathlib").Path(binding["config"]["manifest"]["path"])
    if fault == "unfinalized-control":
        state = path.parent / "attempt.json"
        d = json.loads(state.read_text())
        d["state"] = "RUNNING"
        state.write_text(canonical(d))
    elif fault == "bad-seal":
        from speech_aware_evidence_acquisition.analysis import system_text_pilot as pilot
        monkeypatch.setattr(pilot, "verify_bundle", lambda p: SimpleNamespace(attempt_state="RUNNING"))
    elif fault == "duplicate-score":
        job = path.parent / "score-jobs.jsonl"
        job.write_text(job.read_text() + "\n" + job.read_text())
    elif fault == "failed-score":
        summary = path.parent / "score-batch/batch-summary.json"
        d = json.loads(summary.read_text())
        d["failed"] = 1
        summary.write_text(canonical(d))
    elif fault == "config":
        import hashlib
        d = json.loads(path.read_text())
        d["config"]["config_hash"] = "a" * 64
        path.write_text(canonical(d))
        binding["config"]["manifest"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    else:
        import hashlib
        roster = __import__("pathlib").Path(binding["config"]["construction_roster"]["path"])
        d = json.loads(roster.read_text())
        d["items"].reverse()
        roster.write_text(canonical(d))
        binding["config"]["construction_roster"]["sha256"] = hashlib.sha256(roster.read_bytes()).hexdigest()
    with pytest.raises(PolicyError):
        prepare(f)
    assert "score-counts" not in f.events and "reference" not in f.events


def test_real_read_ledger_gate_requires_exact_recipe_and_countersignature(tmp_path, monkeypatch):
    from test_system_text_search_cli import ROOT
    real_cli = learning._read_cli(ROOT)
    f = setup(tmp_path, monkeypatch)
    monkeypatch.setattr(learning, "_read_cli", lambda root: real_cli)
    ledger = f.root / "docs/exposure-ledger.md"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    header = "| run/experiment id | execution profile | split role | calls | artifacts | notes |\n|---|---|---|---|---|---|\n"
    for note, artifact in (("DRAFT", "recipe.json"), ("ROOT COUNTERSIGNED", "wrong.json")):
        ledger.write_text(header + f"| CONTEXT-READ-V1 | model-free-check | discovery | 0 | {artifact} | {note} |\n")
        with pytest.raises(PolicyError):
            prepare(f)
        assert "complete-family" not in f.events


def test_gepa_requires_front_parent_and_tf_rejects_component_override(tmp_path, monkeypatch):
    f = setup(tmp_path, monkeypatch)
    f.evidence["feedback"]["groups"][0] = copy.deepcopy(f.evidence["feedback"]["groups"][1])
    f.evidence["feedback"]["groups"][0]["sample_id"] = f.recipe["sample_ids"][0]
    with pytest.raises(PolicyError, match="per-example front"):
        prepare(f, "gepa", candidate_id="context-0", component="node_context")
    with pytest.raises(PolicyError, match="complete context-diversity"):
        prepare(f, candidate_id="context-3")


def test_input_tampering_and_update_path_traversal_refused(tmp_path, monkeypatch):
    f = setup(tmp_path, monkeypatch)
    p = prepare(f)
    with pytest.raises(PolicyError, match="identity"):
        learning.record_context_update(f.archive, input_sha256=p["input_sha256"], update_id="../escape", proposal_document=response(p))
    path = f.archive.root / "context-learning/inputs/tf-grpo-context-diversity-1.json"
    changed = json.loads(path.read_text())
    changed["sampling"]["temperature"] = 1
    path.write_text(canonical(changed))
    with pytest.raises(PolicyError, match="hash"):
        learning.record_context_update(f.archive, input_sha256=p["input_sha256"], update_id="tampered", proposal_document=response(p))


def test_tf_semantic_experience_history_is_separate_from_runtime_text(tmp_path, monkeypatch):
    f = setup(tmp_path, monkeypatch)
    p = prepare(f, experiences={"G1": "Check evidence support."})
    operations = [{"operation": "modify", "id": "G1", "text": "Check bidirectional evidence support."}]
    record = learning.record_context_update(f.archive, input_sha256=p["input_sha256"], update_id="experience-1",
        proposal_document=response(p), experience_operations=operations)
    assert record["experience_after"] == {"G1": operations[0]["text"]}
    assert record["experience_operations"] == operations
    assert record["status"] == "no-change"
    assert f.archive.load_policy(record["bundle_id"]).as_json()["role_text"] == f.policies["context-3"].as_json()["role_text"]


@pytest.mark.parametrize("fault", ["control-timing", "control-session", "missing-candidate-timing", "reg-profile"])
def test_all_family_timing_is_checked_before_projection(tmp_path, monkeypatch, fault):
    f = setup(tmp_path, monkeypatch)
    if fault == "control-timing":
        f.evidence["summaries"]["seed-aa"]["sample_timing"]["all_samples"]["mean_seconds"] = 0
    elif fault == "control-session":
        f.evidence["summaries"]["seed-aa"]["timing_session_sha256"] = "d" * 64
    elif fault == "missing-candidate-timing":
        f.evidence["feedback"]["groups"][0]["members"][0]["execution"].pop("sample_timing")
    else:
        f.registration["measurement_profile"]["queue_depth"] = 8
        repin(f)
    with pytest.raises(PolicyError):
        prepare(f)
    assert not (f.archive.root / "context-learning").exists()


def test_tf_all_equal_utility_cannot_invent_advantage_update(tmp_path, monkeypatch):
    f = setup(tmp_path, monkeypatch)
    for group in f.evidence["feedback"]["groups"]:
        for member in group["members"]:
            member["native_counts"] = copy.deepcopy(group["members"][0]["native_counts"])
    p = prepare(f)
    record = learning.record_context_update(f.archive, input_sha256=p["input_sha256"], update_id="no-advantage",
        proposal_document=response(p), experience_operations=[{"operation": "add", "id": "G1", "text": "Invent an improvement."}])
    assert record["status"] == "invalid" and "zero variation" in record["error"]


def test_gepa_cannot_import_tf_experience_operations(tmp_path, monkeypatch):
    f = setup(tmp_path, monkeypatch)
    p = prepare(f, "gepa", candidate_id="context-3", component="node_context")
    d = response(p)
    d["component"] = "node_context"
    record = learning.record_context_update(f.archive, input_sha256=p["input_sha256"], update_id="wrong-algorithm",
        proposal_document=d, experience_operations=[])
    assert record["status"] == "invalid" and "GEPA" in record["error"]


def test_declared_control_free_family_does_not_add_a_candidate_multiplier(tmp_path, monkeypatch):
    f = setup(tmp_path, monkeypatch)
    f.protocol["control_members"] = []
    for key in ("seed", "seed-aa"):
        del f.registration["member_bindings"][key]
        del f.registration["expected_members"][key]
        del f.evidence["summaries"][key]
    f.bindings = f.bindings[:4]
    f.evidence["feedback"]["sources"] = f.evidence["feedback"]["sources"][:4]
    for group in f.evidence["feedback"]["groups"]:
        group["members"] = group["members"][:4]
    repin(f)
    p = prepare(f)
    assert p["budget"]["family_trajectories"] == 80
    assert p["budget"]["control_trajectories"] == 0


@pytest.mark.parametrize("fault", ["blind-source", "milestone-source", "owner", "registration-hash", "owner-bytes"])
def test_source_scope_rejections_precede_current_quality_read(tmp_path, monkeypatch, fault):
    f = setup(tmp_path, monkeypatch)
    if fault in {"blind-source", "milestone-source"}:
        spec = json.loads((f.root / "reference-spec.json").read_text())
        if fault == "blind-source":
            spec["initial_reference_member"] = "B-parent"
            spec["expected_members"] = {"B-parent": "blind", "B-parent-aa": "blind-aa"}
        else:
            spec["family_id"] = "milestone"
        f.protocol["frozen_reference"] = pin(f.root, "reference-spec.json", spec)
    elif fault == "owner":
        owner = json.loads((f.root / "owner.json").read_text())
        owner["resolved_contract"]["seed"] = 0
        f.protocol["owner"] = pin(f.root, "owner.json", owner)
    repin(f)
    if fault == "registration-hash":
        f.registration["registration_sha256"] = "a" * 64
        f.recipe["context_learning_registration"] = pin(f.root, "registration.json", f.registration)
        f.recipe_pin = pin(f.root, "recipe.json", f.recipe)
    elif fault == "owner-bytes":
        (f.root / "owner.json").write_text("{}")
    with pytest.raises(PolicyError):
        prepare(f)
    assert "complete-family" not in f.events


@pytest.mark.parametrize("field", ["knowledge", "supply", "unknown-role", "compression", "unicode", "evidence"])
def test_invalid_context_edit_is_retained_without_runtime_change(tmp_path, monkeypatch, field):
    f = setup(tmp_path, monkeypatch)
    p = prepare(f)
    changes = {"knowledge": {}} if field == "knowledge" else {"supply": {}} if field == "supply" else (
        {"role_text": {"answerer": "New role."}} if field == "unknown-role" else
        {"node_context": {"compression": True}} if field == "compression" else
        {"role_text": {"solver": "\u4e2d\u6587"}} if field == "unicode" else {})
    d = response(p, changes=changes)
    if field == "evidence":
        d["evidence"] = ["unregistered-feedback"]
    record = learning.record_context_update(f.archive, input_sha256=p["input_sha256"], update_id="invalid-" + field,
                                           proposal_document=d)
    assert record["status"] == "invalid" and "bundle_id" not in record


def test_full_four_role_joint_edit_and_assembly_reuse_shared_materializer(tmp_path, monkeypatch):
    f = setup(tmp_path, monkeypatch)
    p = prepare(f)
    changes = {"role_text": {r: f"Preserve source-supported {r} role boundaries." for r in learning.ROLES},
               "context_layout": {"native_role_query_placement": "before-speech-v1"},
               "node_context": {"tool_schema_rendering": "per-role", "reviewer_history_scope": "latest-solver-and-local-tools"}}
    r = learning.record_context_update(f.archive, input_sha256=p["input_sha256"], update_id="joint-1",
                                      proposal_document=response(p, changes=changes))
    child = f.archive.load_policy(r["bundle_id"]).as_json()
    assert r["status"] == "provisional"
    assert all(child[k] == changes[k] for k in changes)
    assert child["seed_config_sha256"] == f.policies["context-3"].as_json()["seed_config_sha256"]
    assert len(child["cumulative_sources"]) == 3
    feedback_source = next(s for s in child["cumulative_sources"] if s["kind"] == "feedback")
    assert set(feedback_source["sample_ids"]) == set(p["reference"]["sample_ids"])


def test_feedback_export_rechecks_pinned_owner_and_reference_bytes(tmp_path, monkeypatch):
    f = setup(tmp_path, monkeypatch)
    original = f.cli.read_family
    def read_then_change(*a, **kw):
        result = original(*a, **kw)
        (f.root / "owner.json").write_text("{}")
        return result
    f.cli.read_family = read_then_change
    with pytest.raises(PolicyError, match="hash"):
        prepare(f)
    assert not (f.archive.root / "context-learning").exists()


def test_candidate_systems_cannot_vary_knowledge_or_supply(tmp_path, monkeypatch):
    f = setup(tmp_path, monkeypatch)
    d = f.policies["context-3"].as_json()
    d["supply"]["value_limit"] = 1
    f.policies["context-3"] = SystemTextPolicyBundle.from_json(d)
    f.registration["member_bindings"]["context-3"]["bundle_id"] = f.policies["context-3"].bundle_id
    repin(f)
    with pytest.raises(PolicyError, match="fixed"):
        prepare(f)
