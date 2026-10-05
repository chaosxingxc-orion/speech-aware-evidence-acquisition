"""Join qualified complete cohorts to anonymous measured node feedback."""
from copy import deepcopy
from types import SimpleNamespace
import json
import pytest
from test_experiment_population_config import config
from test_abstract_population_sources import pin
from speech_aware_evidence_acquisition.analysis import abstract_population_projection as subject
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError
from speech_aware_evidence_acquisition.rails.system_text_feedback import feedback_utility


@pytest.fixture
def setup(tmp_path, monkeypatch):
    root, data = tmp_path / "repo", tmp_path / "data"
    root.mkdir(); data.mkdir()
    cfg = config((2, 3), 2)
    cp = pin(root, "config.json", cfg)
    families, private, backends, sources, timings = [], {}, {}, {}, {}
    calls = []
    counts = {f"slu_f1_{a}_{k}": (1 if k == "tp" else 0)
              for a in ("word", "char") for k in ("tp", "fp", "fn")}
    counts["scenario_action_exact"] = 1
    for cohort in cfg["cohorts"]:
        tag = cohort["cohort_id"]
        candidates, controls = cohort["candidate_ids"], cohort["control_ids"]
        members = {cid: {"bundle_id": str(index + 1) * 64} for index, cid in enumerate(candidates + controls)}
        recipe = {"family_id": "family-" + tag, "sample_ids": cohort["sample_ids"]}
        reg = {"member_bindings": members, "expected_members": {cid: cid for cid in candidates + controls}}
        reg["protocol"] = pin(root, tag + "-protocol.json", {})
        recipe["context_learning_registration"] = pin(root, tag + "-registration.json", reg)
        evidence = {"summaries": {cid: {"slu_f1": .5, "intent_accuracy": 1.0, "sample_timing": {"first_admitted_sample": {"elapsed_seconds": 2.0}}} for cid in candidates + controls}}
        private[tag] = (evidence, recipe, reg, {"measurement_profile": {}}, candidates, controls, {"f1": .5})
        bindings, backend = [], {}
        for cid in candidates + controls:
            mp = pin(data, tag + "/" + cid + "/manifest.json", {}, True)
            phase = pin(data, tag + "/" + cid + "/phase.json", {}, True)
            bindings.append({"candidate_id": cid, "config": {"manifest": mp}})
            backend[cid] = {"phase": phase, "repo_root": str(root)}
            records, contacts = {}, []
            for index, sid in enumerate(cohort["sample_ids"]):
                for visit, (role, text) in enumerate([
                    ("solver", '{"scenario":"PRIVATE_LABEL","action":"PRIVATE_ACTION","entities":[{"type":"PRIVATE_TYPE","filler":"PRIVATE_VALUE"}]}'),
                    ("planner", "ACCEPT")]):
                    rid = sid + "-" + str(visit)
                    records[rid + "/response"] = {"text": text}
                    contacts.append({"sample_id": sid, "request_id": rid, "role_id": role,
                                     "visit_index": visit, "interrupted": False,
                                     "measurements": {"generated_tokens": 3}})
            sources[mp["path"]] = SimpleNamespace(sample_ids=tuple(cohort["sample_ids"]),
                bundle=SimpleNamespace(trace_records=records))
            timings[mp["path"]] = {"contacts": contacts, "content_sha256": "c"*64}
        saved = pin(data, tag + "/family.json", {"bindings": bindings}, True)
        recipe_pin = pin(root, tag + ".json", recipe)
        families.append({"cohort_id": tag, "saved_family": saved, "recipe": recipe_pin})
        backends[tag] = pin(data, tag + "/sources.json", backend, True)
    source_manifest = {"families": families, "projection_config": cp}
    sp = pin(root, "join.json", source_manifest)
    joined = {"projection_config": cp, "private_families": private,
              "qualifications": {c["cohort_id"]: {"members": [], "attempt_metadata_pins": [],
                    "job_metadata_pins": []} for c in cfg["cohorts"]}}
    def join(**kwargs):
        calls.append("join-all")
        return deepcopy(joined)
    monkeypatch.setattr(subject, "read_registered_population_sources", join)
    def groups(evidence, recipe, reg, candidates, reference):
        return [{"sample_id": sid, "members": [{"candidate_id": cid, "native_counts": counts,
                 "utility": feedback_utility(counts, .5), "execution": {"reliable_completion": True,
                  "abstained": False, "wall_time_seconds": 2., "model_calls": 2}}
                for cid in candidates]} for sid in recipe["sample_ids"]]
    monkeypatch.setattr(subject.learning, "_candidate_groups", groups)
    def measured(evidence, ids, bindings, **kwargs):
        calls.append("measurement-all")
        return [{"candidate_id": cid, "bundle_id": bindings[cid]["bundle_id"],
                 "slu_f1": .5, "intent": 1., "reliable_completion_rate": 1.,
                 "mean_sample_seconds": 2., "non_first_mean_seconds": 2.,
                 "model_calls": 4, "tool_calls": 0, "eligible": True,
                 "timing_report_sha256": "d"*64, "private_note": "PRIVATE_MEASUREMENT"}
                for cid in ids]
    monkeypatch.setattr(subject.learning, "measured_rows", measured)
    def verify(**kwargs):
        mp = str(kwargs["manifest_path"])
        calls.append("trace:" + mp)
        s = deepcopy(sources[mp]); s.key = mp
        return s
    monkeypatch.setattr(subject, "verify_native_episode_source", verify)
    monkeypatch.setattr(subject, "export_system_node_timing", lambda s: deepcopy(timings[s.key]))
    def authority(spec, **kwargs): return {"read_id": spec["family_id"]}
    monkeypatch.setattr(subject, "_reader", lambda root: SimpleNamespace(
        CLI=SimpleNamespace(require_read_registration=authority)))
    request = {"schema": "saea-abstract-population-projection-v1", "status": "ROOT_REGISTERED",
               "source_join": sp, "source_specifications": backends, "runtime_admission": False}
    rp = pin(root, "projection.json", request)
    return SimpleNamespace(root=root, data=data, cfg=cfg, request=request, pin=rp,
                           calls=calls, joined=joined, sources=sources, timings=timings)


def run(s):
    return subject.project_registered_population(projection_pin=s.pin, repo_root=s.root, data_root=s.data)


def test_complete_anonymous_projection_retains_every_partition(setup):
    s = setup; out = run(s)
    assert s.calls[0] == "join-all"
    assert len([c for c in s.calls if c.startswith("trace:")]) == 5
    assert list(out["learner_view"]["population"]["cohorts"]) == ["cohort-0", "cohort-1"]
    text = json.dumps(out["learner_view"])
    for secret in ("PRIVATE_LABEL", "PRIVATE_ACTION", "PRIVATE_TYPE", "PRIVATE_VALUE", "slurp:train:", str(s.data)):
        assert secret not in text
    assert len(out["private_custody"]["sources"]) == 5
    assert out["runtime_admission"] is False
    assert out["learner_exported"] is False
    assert out["model_contacts"] == out["scorer_contacts"] == 0


def test_incomplete_join_never_opens_traces(setup, monkeypatch):
    def refuse(**kwargs): raise PolicyError("last cohort incomplete")
    monkeypatch.setattr(subject, "read_registered_population_sources", refuse)
    with pytest.raises(PolicyError): run(setup)
    assert setup.calls == []


@pytest.mark.parametrize("fault", ["draft", "runtime", "missing_cohort", "extra_cohort", "changed_backend", "missing_member", "extra_member"])
def test_projection_refuses_unregistered_source_shape(setup, fault):
    s = setup
    if fault == "draft": s.request["status"] = "DRAFT"
    elif fault == "runtime": s.request["runtime_admission"] = True
    elif fault == "missing_cohort": s.request["source_specifications"].pop("cohort-1")
    elif fault == "extra_cohort": s.request["source_specifications"]["unknown"] = s.request["source_specifications"]["cohort-0"]
    else:
        p = s.data / "cohort-1/sources.json"
        if fault == "changed_backend": p.write_text("{}")
        else:
            b = json.loads(p.read_text())
            if fault == "missing_member": b.pop("seed")
            else: b["unknown"] = b["seed"]
            s.request["source_specifications"]["cohort-1"] = pin(s.data, "cohort-1/sources.json", b, True)
    s.pin = pin(s.root, "projection.json", s.request)
    with pytest.raises(PolicyError): run(s)
    assert not any(x.startswith("trace:") for x in s.calls)


@pytest.mark.parametrize("fault", ["foreign_sample", "missing_contact", "duplicate_request", "wrong_roster"])
def test_no_partial_projection_on_corrupt_episode(setup, fault):
    s = setup; key = next(k for k in s.timings if "candidate-4" in k)
    if fault == "foreign_sample": s.timings[key]["contacts"][-1]["sample_id"] = "foreign"
    elif fault == "missing_contact": s.timings[key]["contacts"].pop()
    elif fault == "duplicate_request": s.timings[key]["contacts"][-1]["request_id"] = s.timings[key]["contacts"][0]["request_id"]
    else: s.sources[key].sample_ids = ("foreign",)
    with pytest.raises((PolicyError, ValueError)): run(s)


def test_changed_source_during_projection_cannot_return(setup, monkeypatch):
    s = setup; original = subject.export_system_node_timing
    def changed(source):
        result = original(source)
        (s.root / "config.json").write_text("{}")
        return result
    monkeypatch.setattr(subject, "export_system_node_timing", changed)
    with pytest.raises(PolicyError): run(s)


@pytest.mark.parametrize("which", ["cohort-1.json", "cohort-1-registration.json", "cohort-1-protocol.json"])
def test_late_scope_mutation_refuses_result(setup, monkeypatch, which):
    s = setup; original = subject.export_system_node_timing
    def changed(source):
        result = original(source)
        (s.root / which).write_text('{"changed":true}')
        return result
    monkeypatch.setattr(subject, "export_system_node_timing", changed)
    with pytest.raises(PolicyError): run(s)


def test_read_authority_revocation_refuses_result(setup, monkeypatch):
    s = setup; active = [True]
    monkeypatch.setattr(subject, "_reader", lambda root: SimpleNamespace(CLI=SimpleNamespace(
        require_read_registration=lambda spec, **kwargs: {"read_id": spec["family_id"], "active": active[0]})))
    original = subject.export_system_node_timing
    def changed(source):
        active[0] = False
        return original(source)
    monkeypatch.setattr(subject, "export_system_node_timing", changed)
    with pytest.raises(PolicyError, match="READ changed"): run(s)


def test_native_source_verifier_refusal_is_not_normalized(setup, monkeypatch):
    def refuse(**kwargs): raise ValueError("frozen source seal differs")
    monkeypatch.setattr(subject, "verify_native_episode_source", refuse)
    with pytest.raises(ValueError, match="seal differs"): run(setup)


def test_measured_first_nonfirst_and_controls_are_in_learner_view(setup):
    out = run(setup)
    rows = out["learner_view"]["business_measurements"]
    for cohort in setup.cfg["cohorts"]:
        actual = rows[cohort["cohort_id"]]
        assert [r["candidate_id"] for r in actual] == cohort["candidate_ids"] + cohort["control_ids"]
        assert all(r["first_sample_seconds"] == r["non_first_mean_seconds"] == 2 for r in actual)
        assert all(r["slu_f1"] == .5 for r in actual)
        assert [r["is_control"] for r in actual] == [False]*len(cohort["candidate_ids"]) + [True]*len(cohort["control_ids"])
    assert "PRIVATE_MEASUREMENT" not in json.dumps(out["learner_view"])
    first_trace = next(i for i, x in enumerate(setup.calls) if x.startswith("trace:"))
    assert setup.calls[:first_trace].count("measurement-all") == len(setup.cfg["cohorts"])


@pytest.mark.parametrize("fault", ["missing", "order", "bundle", "quality", "mean", "calls", "reliability", "first", "nonfirst"])
def test_measurement_mismatch_rejects_complete_projection(setup, monkeypatch, fault):
    original = subject.learning.measured_rows
    def changed(*args, **kwargs):
        rows = original(*args, **kwargs)
        if fault == "missing": rows.pop()
        elif fault == "order": rows.reverse()
        elif fault == "bundle": rows[0]["bundle_id"] = "f"*64
        elif fault == "quality": rows[0]["slu_f1"] = .7
        elif fault == "mean": rows[0]["mean_sample_seconds"] = 9.
        elif fault == "calls": rows[0]["model_calls"] = 5
        elif fault == "reliability": rows[0]["reliable_completion_rate"] = .5
        elif fault == "first":
            args[0]["summaries"][rows[0]["candidate_id"]]["sample_timing"]["first_admitted_sample"]["elapsed_seconds"] = 9.
        else: rows[0]["non_first_mean_seconds"] = 3.
        return rows
    monkeypatch.setattr(subject.learning, "measured_rows", changed)
    with pytest.raises(PolicyError):
        run(setup)


def test_last_family_measurement_failure_opens_no_native_trace(setup, monkeypatch):
    original = subject.learning.measured_rows
    def changed(*args, **kwargs):
        if args[1][0] == setup.cfg["cohorts"][-1]["candidate_ids"][0]:
            raise PolicyError("missing actual admission-order measurements")
        return original(*args, **kwargs)
    monkeypatch.setattr(subject.learning, "measured_rows", changed)
    with pytest.raises(PolicyError):
        run(setup)
    assert not any(x.startswith("trace:") for x in setup.calls)
