"""Validate only the reviewed inactive historical-natural audio guard delta."""
import ast
import json
from pathlib import Path
from .system_text_policy import require

HELPER_SHA = "b694fc1c645eea1bac20beaf5f3127e2f667a5468ecb8d0f13b4747446099718"
PATHS = {"runtime": "core/flight/runtime.py", **{name: "rails/" + name + ".py" for name in ("kb_policy", "knowledge_provider", "knowledge_stores", "phase_supply")}}
PREFIX = "src/speech_aware_evidence_acquisition/"
GUARD = """from ...rails.architecture_audio_budget import (
    manual_architecture_audio_budget_applies, require_manual_architecture_audio_budget,
)
if manual_architecture_audio_budget_applies(values):
    require_manual_architecture_audio_budget(values, [
        {"sample_id": sample.sample_id, "audio_seconds": getattr(sample, "audio_seconds", None)}
        for sample in samples
    ])
"""

def exact_runtime_delta(original, current):
    old, new = ast.parse(original), ast.parse(current)
    expected = [ast.dump(n, include_attributes=False) for n in ast.parse(GUARD).body]
    matches = []
    for cls in new.body:
        if not isinstance(cls, ast.ClassDef) or cls.name != "FlightRuntime":
            continue
        for node in cls.body:
            if isinstance(node, ast.FunctionDef) and node.name == "preflight":
                for i in range(1, len(node.body) - 2):
                    if [ast.dump(n, include_attributes=False) for n in node.body[i:i+2]] == expected:
                        before, after = node.body[i-1], node.body[i+2]
                        require(ast.dump(before, include_attributes=False) == ast.dump(ast.parse("samples = self._samples").body[0], include_attributes=False)
                                and ast.dump(after, include_attributes=False) == ast.dump(ast.parse("plan = self._build_execution_plan(values, carrier_lock_key, identity_hash)").body[0], include_attributes=False),
                                "reviewed audio guard location differs")
                        matches.append((node, i))
    require(len(matches) == 1, "exact reviewed audio guard insertion required")
    node, i = matches[0]
    del node.body[i:i+2]
    require(ast.dump(old, include_attributes=False) == ast.dump(new, include_attributes=False),
            "unreviewed historical-natural runtime delta")

def validate_compatibility(record, prerequisite, qualified, decision=None, *, repo_root, data_root, read_pin=None):
    """Read-only proof usable before authoring a decision or registration."""
    if read_pin is None:
        from .architecture_natural_registration import _read_pin
        read_pin = _read_pin
    from ..core.bundle.git_commit import require_clean_study_repo
    fields = {"schema", "status", "original_natural_prerequisite", "original_source", "incident_disposition",
              "original_implementation", "current_implementation", "audio_guard", "scope",
              "runtime_admission", "scientific_feedback", "learner_export"}
    require(isinstance(record, dict) and set(record) == fields
            and record["schema"] == "saea-natural-precontact-audio-guard-compatibility-v1"
            and record["status"] == "ROOT APPROVED SOURCE COMPATIBILITY"
            and record["scope"] == "precontact-audio-adequacy-only"
            and all(record[k] is False for k in ("runtime_admission", "scientific_feedback", "learner_export"))
            and record["original_natural_prerequisite"] == prerequisite
            and (decision is None or record["incident_disposition"] == decision.get("incident_disposition")),
            "exact root natural source compatibility scope required")
    incident = json.loads(read_pin(record["incident_disposition"], Path(data_root)))
    require(incident.get("schema") == "saea-root-bounded-incident-disposition-v1"
            and incident.get("status") == "DECIDED ENGINEERING AND PROSPECTIVE REGISTRATION; DISPATCH REQUIRES FINAL ADMISSION"
            and type(incident.get("model_tokenizer_scorer_contacts")) is int and incident["model_tokenizer_scorer_contacts"] == 0
            and all(incident.get(k) is False for k in ("scientific_read_authorized", "learner_export", "controls_mutated")),
            "exact bounded source-only incident required")
    owner = json.loads(read_pin(incident["owner_decision"], Path(repo_root)))
    require(owner.get("schema") == "saea-owner-decision-supplement-v1" and owner.get("decision_id") == 227
            and owner.get("status") == "approved", "approved owner227 incident authority required")
    require(isinstance(prerequisite, dict) and set(prerequisite) == {"registration", "qualification"}
            and json.loads(read_pin(prerequisite["qualification"], Path(data_root))) == qualified
            and qualified.get("registration") == prerequisite["registration"],
            "original raw natural qualification differs")
    read_pin(prerequisite["registration"], Path(data_root))
    source = record["original_source"]
    require(set(source) == {"path", "commit"} and source["path"] == qualified["frozen_worker"]
            and source["commit"] == qualified["source_commit"], "original qualified source differs")
    original = Path(source["path"]).resolve()
    require(require_clean_study_repo(original) == source["commit"], "original source must remain clean and pinned")
    contents = {}
    for kind, root in (("original_implementation", original), ("current_implementation", Path(repo_root))):
        require(set(record[kind]) == set(PATHS), "exact five implementation pins required")
        contents[kind] = {}
        for name, path in PATHS.items():
            pin = record[kind][name]
            require(set(pin) == {"relpath", "sha256"} and pin["relpath"] == PREFIX + path,
                    "implementation path differs")
            contents[kind][name] = read_pin(pin, root)
    for name in PATHS.keys() - {"runtime"}:
        require(contents["original_implementation"][name] == contents["current_implementation"][name],
                "unreviewed supply implementation delta")
    guard = record["audio_guard"]
    require(guard == {"relpath": PREFIX + "rails/architecture_audio_budget.py", "sha256": HELPER_SHA},
            "audited audio helper pin differs")
    read_pin(guard, Path(repo_root))
    exact_runtime_delta(contents["original_implementation"]["runtime"], contents["current_implementation"]["runtime"])
    return original
