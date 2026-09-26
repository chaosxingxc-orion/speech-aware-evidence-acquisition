"""Verify summary custody against frozen configs, actor inputs and raw outputs."""
from dataclasses import asdict
import copy
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from test_system_summary_preparation import summary_world, prepared, load, pin  # noqa: F401
from test_artifact_result_kind import _plan as artifact_plan
from test_rails_frozen_core_client import _plan
from speech_aware_evidence_acquisition.analysis import system_summary_source as module
from speech_aware_evidence_acquisition.core.bundle.artifacts import VerifiedBundle
from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
from speech_aware_evidence_acquisition.core.flight.runtime import validate_artifact_result_binding
from speech_aware_evidence_acquisition.rails.core_client import _agent_history
from speech_aware_evidence_acquisition.rails.hashing import content_hash


@pytest.fixture
def summary_source(summary_world, tmp_path, monkeypatch):  # noqa: F811
    return make_text_stage_source(summary_world, tmp_path, monkeypatch)


def make_text_stage_source(world, tmp_path, monkeypatch, *, prepared_spec=None,
                           baseline="system-trajectory-summary-text-v1", stage_name="summary"):
    data, actor, binding, _source_pin, _calls = world
    spec = prepared_spec if prepared_spec is not None else prepared(world)[0]
    states, _ = load(world, spec)
    sid = actor.sample_ids[0]
    project = Path(__file__).parents[2]
    repo = tmp_path / (stage_name + "-source")
    roster_rel = "docs/receipts/rosters/construction.json"
    (repo / roster_rel).parent.mkdir(parents=True)
    (repo / roster_rel).write_bytes((data / binding["construction_roster"]["relpath"]).read_bytes())
    values = json.loads((project / "configs/baseline" / (baseline + ".json")).read_text())
    values.update(prepared_training_feedback=spec, live_phase_fit={
        "run_id": "summary-fit", "attempt_id": "summary-fit-1", "contact_cap": 3},
        artifact_result={"schema": "saea-artifact-result-binding-v1",
                         "role": "training-feedback-proposal", "construction_roster": {
                             "repo_relpath": roster_rel,
                             "sha256": binding["construction_roster"]["sha256"]}})
    names = {kind: kind for kind in ("model", "dataset", "baseline", "experiment")}
    for kind in names:
        path = repo / "configs" / kind / f"{kind}.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(values if kind == "baseline" else {}))
    template_rel = "configs/" + values["phase_material"]["direct"]["instruction_template"]
    (repo / template_rel).parent.mkdir(parents=True)
    (repo / template_rel).write_bytes((project / template_rel).read_bytes())
    for command in (
        ["git", "init", "-q"], ["git", "add", "."],
        ["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
         "commit", "-qm", "Freeze synthetic summary inputs"],
    ):
        subprocess.run(command, cwd=repo, check=True, capture_output=True)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    composed = compose(repo, **names)
    plan = _plan(carrier_lock_key="slurp", split_identity_hash=actor.plan.split_identity_hash,
                 protocol_hash=protocol_hash(composed.config_hash, values["arm"], actor.plan.split_identity_hash),
                 run_id="summary-run", attempt_id="summary-attempt", planned_model_calls=1)
    authority = validate_artifact_result_binding(values, plan=artifact_plan(actor.plan.split_identity_hash),
                                                 repo_root=repo, sample_ids=(sid,), data_root=data)
    text = "Solver revised; Planner accepted; final delivery retained the revision."
    rid = stage_name + ":1"
    payload = {
        "request_id": rid, "carrier_lock_key": "slurp", "sample_id": sid,
        "speech_ref": "slurp/" + sid, "media_relpath": "audio/source.wav",
        "audio_seconds": 1.0, "sample_rate_hz": 16000,
        "task_instruction": values["task_instruction"], "prepared_text": "saea-prepared-text-v1",
        "decoding_params": {"max_tokens": 128},
        "history": _agent_history(agent_state=(states[sid].as_json(),), agent_contact_id="summary",
                                  contact_instruction=(repo / template_rel).read_text()),
    }
    response = {"text": text, "response_sha256": "e"*64,
                "response_text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "usage": {"completion_tokens": 20}}
    output = {"sample_id": sid, "request_id": rid, "text": text,
              "response_text_sha256": response["response_text_sha256"]}
    manifest = {
        "status": "COMPLETED", "study_commit": commit, "result_kind": "artifact", "scorers": [],
        "arm": values["arm"], "config": {"fragments": names, "config_hash": composed.config_hash},
        "artifact_result": authority, "plan": asdict(plan),
    }
    source_pin = pin(data, stage_name + "-run/manifest.json", manifest)
    bundle = VerifiedBundle(data / source_pin["relpath"], manifest, None, (output,), {
        rid + "/request": {"payload": payload, "payload_sha256": content_hash(payload)},
        rid + "/response": response,
    }, frozenset((sid,)), "FINALIZED")
    monkeypatch.setattr(module, "verify_bundle", lambda _path: bundle)
    from speech_aware_evidence_acquisition.analysis import prepared_text_source
    previous_verifier = prepared_text_source.verify_bundle
    def verified(path):
        if Path(path) == data / source_pin["relpath"]:
            return bundle
        return previous_verifier(path)
    monkeypatch.setattr(prepared_text_source, "verify_bundle", verified)
    return dict(pin=source_pin, repo=repo, data=data, bundle=bundle, payload=payload,
                response=response, output=output, spec=spec, request_id=rid)


def verify(world):
    return module.verify_system_summaries(world["pin"], repo_root=world["repo"], data_root=world["data"])


def test_summary_is_bound_to_actual_complete_input(summary_source):
    result = verify(summary_source)
    row = next(iter(result.rows.values()))
    assert row["status"] == "usable"
    assert row["summary"] == summary_source["output"]["text"]
    assert result.actor_binding["round_id"] == "round-1"


@pytest.mark.parametrize("change", ["episode", "phase", "extra-request", "output", "dirty", "commit", "hash"])
def test_summary_substitution_is_refused(summary_source, change):
    w = summary_source
    if change in ("episode", "phase"):
        item = w["payload"]["history"][0 if change == "episode" else -1]
        item["content"] += " changed"
        item["content_sha256"] = hashlib.sha256(item["content"].encode()).hexdigest()
        w["bundle"].trace_records["summary:1/request"]["payload_sha256"] = content_hash(w["payload"])
    elif change == "extra-request":
        w["bundle"].trace_records["extra/request"] = copy.deepcopy(w["bundle"].trace_records["summary:1/request"])
    elif change == "output":
        w["output"]["text"] = "unrelated"
    elif change == "dirty":
        (w["repo"] / "configs/model/model.json").write_text("{} ")
    elif change == "commit":
        w["bundle"].manifest["study_commit"] = "f"*40
        w["pin"] = pin(w["data"], "summary-run/manifest.json", w["bundle"].manifest)
    else:
        w["pin"]["sha256"] = "f"*64
    with pytest.raises(module.SummarySourceError):
        verify(w)


@pytest.mark.parametrize("count,text,status", [(128,"unfinished","output-limit"),
    (None,"some summary","unknown-completion"), (0,"","empty")])
def test_unusable_summary_is_retained_without_retry(summary_source, count, text, status):
    w = summary_source
    w["response"].update(text=text, response_text_sha256=hashlib.sha256(text.encode()).hexdigest(),
                         usage={} if count is None else {"completion_tokens": count})
    w["output"].update(text=text, response_text_sha256=w["response"]["response_text_sha256"])
    row = next(iter(verify(w).rows.values()))
    assert row["status"] == status and row["summary"] == text


@pytest.mark.parametrize("finish,status", [("length", "output-limit"), ("tool_calls", "nonstandard-finish")])
def test_wire_finish_prevents_silent_use_of_partial_summary(summary_source, finish, status):
    summary_source["bundle"].trace_records["summary:1/wire-response"] = {"finish_reason": finish}
    row = next(iter(verify(summary_source).rows.values()))
    assert row["status"] == status
    assert row["summary"] == summary_source["output"]["text"]
