from pathlib import Path
import pytest
from speech_aware_evidence_acquisition.rails.natural_source_compatibility import exact_runtime_delta, GUARD

OLD = "class FlightRuntime:\n    def preflight(self):\n        samples = self._samples\n        plan = self._build_execution_plan(values, carrier_lock_key, identity_hash)\n"
NEW = OLD.replace("        plan =", "".join("        " + line + "\n" for line in GUARD.splitlines()) + "        plan =")

def test_exact_reviewed_delta():
    exact_runtime_delta(OLD, NEW)

@pytest.mark.parametrize("new", [NEW.replace("self._samples", "self.other"), NEW.replace("audio_seconds", "duration"), NEW + "x = 1\n", OLD, NEW.replace("def preflight", "def another")])
def test_unreviewed_delta_refused(new):
    with pytest.raises(ValueError):
        exact_runtime_delta(OLD, new)

import hashlib
import json
from copy import deepcopy
from speech_aware_evidence_acquisition.rails.natural_source_compatibility import validate_compatibility, PATHS, PREFIX, HELPER_SHA
from speech_aware_evidence_acquisition.rails.architecture_natural_registration import _read_pin

ROOT = Path(__file__).resolve().parents[2]

def pinned(root, relpath, content):
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return {"relpath": relpath, "sha256": hashlib.sha256(content).hexdigest()}

def example(tmp_path, monkeypatch):
    old, current, data = (tmp_path / n for n in ("old", "current", "data"))
    source = "a" * 40
    monkeypatch.setattr("speech_aware_evidence_acquisition.core.bundle.git_commit.require_clean_study_repo", lambda root: source)
    maps = {}
    for name, root, runtime in (("original_implementation", old, OLD), ("current_implementation", current, NEW)):
        maps[name] = {key: pinned(root, PREFIX + path, (runtime if key == "runtime" else "value = 1\n").encode()) for key, path in PATHS.items()}
    helper = (ROOT / (PREFIX + "rails/architecture_audio_budget.py")).read_bytes()
    guard = pinned(current, PREFIX + "rails/architecture_audio_budget.py", helper)
    assert guard["sha256"] == HELPER_SHA
    owner = pinned(current, "owner.json", json.dumps({"schema": "saea-owner-decision-supplement-v1", "decision_id": 227, "status": "approved"}).encode())
    incident = pinned(data, "incident.json", json.dumps({"schema": "saea-root-bounded-incident-disposition-v1", "status": "DECIDED ENGINEERING AND PROSPECTIVE REGISTRATION; DISPATCH REQUIRES FINAL ADMISSION", "owner_decision": owner,
        "model_tokenizer_scorer_contacts": 0, "scientific_read_authorized": False, "learner_export": False, "controls_mutated": False}).encode())
    prerequisite = {"registration": {"relpath": "r", "sha256": "b" * 64}, "qualification": {"relpath": "q", "sha256": "c" * 64}}
    registration = pinned(data, "natural-registration.json", b"{}")
    qualified = {"frozen_worker": str(old), "source_commit": source, "registration": registration}
    qualification = pinned(data, "natural-qualified.json", json.dumps(qualified).encode())
    prerequisite = {"registration": registration, "qualification": qualification}
    record = dict(schema="saea-natural-precontact-audio-guard-compatibility-v1", status="ROOT APPROVED SOURCE COMPATIBILITY", original_natural_prerequisite=prerequisite,
                  original_source={"path": str(old), "commit": source}, incident_disposition=incident, **maps,
                  audio_guard=guard, scope="precontact-audio-adequacy-only", runtime_admission=False, scientific_feedback=False, learner_export=False)
    kwargs = dict(prerequisite=prerequisite, qualified=qualified, decision={"incident_disposition": incident}, repo_root=current, data_root=data, read_pin=_read_pin)
    return record, kwargs

def test_complete_raw_source_contract(tmp_path, monkeypatch):
    record, kwargs = example(tmp_path, monkeypatch)
    assert validate_compatibility(record, **kwargs) == Path(record["original_source"]["path"])

@pytest.mark.parametrize("field", ["scope", "runtime_admission", "scientific_feedback", "learner_export", "original_natural_prerequisite", "incident_disposition", "original_source", "audio_guard"])
def test_record_authority_drift_refused(tmp_path, monkeypatch, field):
    record, kwargs = example(tmp_path, monkeypatch)
    record[field] = True if field in ("runtime_admission", "scientific_feedback", "learner_export") else {}
    with pytest.raises((ValueError, TypeError)):
        validate_compatibility(record, **kwargs)

@pytest.mark.parametrize("name", list(PATHS))
def test_rehashed_current_source_drift_refused(tmp_path, monkeypatch, name):
    record, kwargs = example(tmp_path, monkeypatch)
    record["current_implementation"][name] = pinned(kwargs["repo_root"], PREFIX + PATHS[name], b"value = 2\n")
    with pytest.raises(ValueError):
        validate_compatibility(record, **kwargs)

def test_stale_raw_pin_refused(tmp_path, monkeypatch):
    record, kwargs = example(tmp_path, monkeypatch)
    (kwargs["repo_root"] / (PREFIX + PATHS["runtime"])).write_bytes(OLD.encode())
    with pytest.raises(ValueError):
        validate_compatibility(record, **kwargs)

def test_original_clean_source_required(tmp_path, monkeypatch):
    record, kwargs = example(tmp_path, monkeypatch)
    monkeypatch.setattr("speech_aware_evidence_acquisition.core.bundle.git_commit.require_clean_study_repo", lambda root: "b" * 40)
    with pytest.raises(ValueError):
        validate_compatibility(record, **kwargs)

@pytest.mark.parametrize("role", ["generation", "fit"])
def test_cross_plan_pin_refused_before_source_override(tmp_path, monkeypatch, role):
    from test_architecture_n20_registration import fixture, invoke
    args = fixture(tmp_path, monkeypatch)
    next(p for p in args["registered_plans"] if p["plan_role"] == role)["natural_source_compatibility"] = {"relpath": "foreign", "sha256": "d" * 64}
    with pytest.raises(ValueError, match="compatibility pair"):
        invoke(args)


def test_pure_predecision_validation(tmp_path, monkeypatch):
    record, kwargs = example(tmp_path, monkeypatch)
    kwargs.pop("decision")
    kwargs.pop("read_pin")
    assert validate_compatibility(record, **kwargs) == Path(record["original_source"]["path"])

@pytest.mark.parametrize("label", ["seed", "seed-aa", "review-off", "solver-lookup"])
def test_optin_public_chain_keeps_all_natural_checks(tmp_path, monkeypatch, label):
    from test_architecture_n20_registration import fixture, invoke, write
    args = fixture(tmp_path, monkeypatch, label)
    pair = args["registered_plans"]
    compatibility = write(tmp_path, "compatibility.json", {"synthetic": True})
    decision_pin = pair[0]["decision_receipt"]
    decision = json.loads((tmp_path / decision_pin["relpath"]).read_bytes())
    decision["natural_source_compatibility"] = compatibility
    new_pin = write(tmp_path, decision_pin["relpath"], decision)
    for plan in pair:
        plan["decision_receipt"] = new_pin
        plan["natural_source_compatibility"] = compatibility
    seen = []
    # Full proof validator has separate real raw-byte tests above; this stub isolates
    # authority propagation while the complete natural custody validator remains real.
    def proof(record, prerequisite, qualified, authority, **kwargs):
        seen.append((prerequisite, qualified, authority))
        assert authority["natural_source_compatibility"] == compatibility
        return ROOT
    monkeypatch.setattr("speech_aware_evidence_acquisition.rails.natural_source_compatibility.validate_compatibility", proof)
    result = invoke(args)
    assert result["member_id"] == label and len(seen) == 1

@pytest.mark.parametrize("change", ["decision", "omit-plan"])
def test_consistent_pair_without_root_compatibility_authority_refused(tmp_path, monkeypatch, change):
    from test_architecture_n20_registration import fixture, invoke, write
    args = fixture(tmp_path, monkeypatch)
    compatibility = write(tmp_path, "compatibility.json", {})
    for plan in args["registered_plans"]:
        plan["natural_source_compatibility"] = compatibility
    if change == "decision":
        args["registered_plans"][1]["decision_receipt"] = {"relpath": "other", "sha256": "f" * 64}
    with pytest.raises(ValueError, match="compatibility"):
        invoke(args)

def test_actual_reviewed_full_runtime_ast():
    import subprocess
    old = subprocess.check_output(["git", "-C", str(ROOT), "show", "d4ba0ec70:src/speech_aware_evidence_acquisition/core/flight/runtime.py"], env=__import__("os").environ.copy())
    current = (ROOT / (PREFIX + PATHS["runtime"])).read_bytes()
    exact_runtime_delta(old, current)

@pytest.mark.parametrize("root_agrees", [False, True])
def test_author_compatibility_refuses_before_any_ready_write(tmp_path, monkeypatch, root_agrees):
    from test_manual_architecture_authoring import fixture, helper
    repo, data, inputs, _, _, checks, warm = fixture(tmp_path, monkeypatch)
    compatibility = pinned(data, "bad-compatibility.json", b"{}")
    inputs["natural_source_compatibility"] = compatibility
    if root_agrees:
        decision = json.loads((data / inputs["decision_receipt"]["relpath"]).read_bytes())
        decision["natural_source_compatibility"] = compatibility
        inputs["decision_receipt"] = pinned(data, inputs["decision_receipt"]["relpath"], json.dumps(decision).encode())
    before = {p: p.read_bytes() for p in (repo / "configs/experiment").glob("*.json")}
    with pytest.raises(ValueError, match="compatibility"):
        helper.author(inputs, repo_root=repo, data_root=data)
    assert not (repo / inputs["package_relpath"]).exists() and not checks and not warm
    assert all(p.read_bytes() == content for p, content in before.items())
