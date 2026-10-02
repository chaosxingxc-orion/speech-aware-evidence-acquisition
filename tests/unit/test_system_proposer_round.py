"""Offline first-round admission checks; no credentials or provider requests."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_proposer_capsule import ProposerCapsule
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError
from test_system_proposer_capsule import fixture, reseal

spec = importlib.util.spec_from_file_location("proposer_round", Path(__file__).parents[2] / "scripts/flights/system_text_proposer_round.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def pin(path, document):
    raw = json.dumps(document).encode()
    path.write_bytes(raw)
    return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}


def registration(tmp_path):
    protocol = {"proposer_exact_version": "gpt-6-sol", "proposal_input_token_cap": 32768,
                "proposal_output_token_cap": 4096, "proposal_contact_cap": 4}
    r = {"schema": "saea-system-text-proposer-round-registration-v1", "status": "root-admitted", "owner_decision": 217,
         "owner_receipt": pin(tmp_path / "owner.json", {"decisions": {"217": {"status": "approved"}}}),
         "protocol": pin(tmp_path / "protocol.json", protocol), "members": [],
         "provider_admission": pin(tmp_path / "admission.json", {"protocol_sha256": content_hash(protocol)})}
    rows = ["| run/experiment id | execution profile | speech carrier + split | split role | split identity hash | consumed | calls | speech audio seconds | gpu hours | notes |", "|---|---|---|---|---|---|---|---|---|---|"]
    for branch, slot in [("L", 1), ("B", 1), ("L", 2), ("B", 2)]:
        key = f"{branch}-1-{slot}"; folder = tmp_path / key; folder.mkdir()
        packet, roots = fixture(folder, branch)
        packet.update(slot=slot, session_id=key, protocol_sha256=content_hash(protocol)); reseal(packet)
        capsule = ProposerCapsule.from_packet(packet, roots=roots)
        run = f"SAEA-SLURP-PROPOSER-{key}"
        member = {"key": key, "capsule": pin(folder / "capsule.json", capsule.as_json()),
                  "input": pin(folder / "input.json", packet), "request_sha256": content_hash(capsule.request()),
                  "execution_plan": {"run_id": run, "execution_profile": "bounded-discovery-probe", "carrier_lock_key": "slurp",
                  "split_role": "discovery", "split_identity_hash": packet["input_sha256"], "planned_model_calls": 4,
                  "planned_gpu_hours": 1.0, "planned_speech_audio_seconds": 1, "protocol_hash": content_hash(protocol)}}
        r["members"].append(member)
        rows.append(f"| {run} | bounded-discovery-probe | slurp TRAIN | discovery | {packet['input_sha256']} | no | 4 | 1 | 1.0 | REGISTERED BEFORE contact |")
    p = tmp_path / "ledger.md"; p.write_text("\n".join(rows))
    r["ledger"] = {"path": str(p), "sha256": runner.digest(p)}
    return r


def test_exact_four_inputs_pass_without_contact(tmp_path):
    jobs, _, _ = runner.load_members(registration(tmp_path))
    assert len(jobs) == 4
    assert all(runner.request_bound(c.request()) < 32768 for _, c, _ in jobs)


def test_closed_failed_slot_is_not_replaced_or_reexecuted(tmp_path):
    r = registration(tmp_path)
    r["closed_allocations"] = {"L-1-1": {
        "outcome": pin(tmp_path / "failed.json", {"status": "failed"}),
        "import": pin(tmp_path / "invalid.json", {"status": "invalid", "proposal_allocation": ["L", 1, 1]})}}
    jobs, _, _ = runner.load_members(r)
    assert [member["key"] for member, _, _ in jobs] == ["B-1-1", "L-1-2", "B-1-2"]
    r["closed_allocations"]["L-1-1"]["outcome"] = pin(tmp_path / "success.json", {"status": "received"})
    with pytest.raises(PolicyError, match="closed allocation"):
        runner.load_members(r)


@pytest.mark.parametrize("mutation", ["capsule", "ledger", "model", "request", "membership"])
def test_changed_registration_never_reaches_transport(tmp_path, mutation):
    r = registration(tmp_path)
    if mutation in {"capsule", "ledger"}:
        target = r["members"][0]["capsule"] if mutation == "capsule" else r["ledger"]
        Path(target["path"]).write_text("changed")
    elif mutation == "request":
        r["members"][0]["request_sha256"] = "0" * 64
    elif mutation == "membership":
        r["members"].pop()
    else:
        protocol = json.loads(Path(r["protocol"]["path"]).read_text()); protocol["proposer_exact_version"] = "changed"
        r["protocol"] = pin(Path(r["protocol"]["path"]), protocol)
    with pytest.raises(PolicyError):
        runner.load_members(r)
