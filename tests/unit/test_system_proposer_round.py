"""Offline round admission and dispatch checks; no credentials or provider requests."""
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


def registration(tmp_path, round_index=1):
    protocol = {"proposer_exact_version": "gpt-6-sol", "proposal_input_token_cap": 32768,
                "proposal_output_token_cap": 4096, "proposal_contact_cap": 4}
    r = {"schema": "saea-system-text-proposer-round-registration-v1", "status": "root-admitted", "owner_decision": 217,
         "round_index": round_index,
         "owner_receipt": pin(tmp_path / "owner.json", {"decisions": {"217": {"status": "approved"}}}),
         "protocol": pin(tmp_path / "protocol.json", protocol), "members": [],
         "provider_admission": pin(tmp_path / "admission.json", {"protocol_sha256": content_hash(protocol)})}
    rows = ["| run/experiment id | execution profile | speech carrier + split | split role | split identity hash | consumed | calls | speech audio seconds | gpu hours | notes |", "|---|---|---|---|---|---|---|---|---|---|"]
    for branch, slot in [("L", 1), ("B", 1), ("L", 2), ("B", 2)]:
        key = f"{branch}-{round_index}-{slot}"
        folder = tmp_path / key
        folder.mkdir()
        packet, roots = fixture(folder, branch)
        packet.update(round=round_index, slot=slot, session_id=key, protocol_sha256=content_hash(protocol))
        if branch == "L" and round_index > 1:
            packet["feedback"].update(family_id=f"update-{round_index - 1}", read_gate_family_sha256="f" * 64)
            selection = {"branch": "L", "stage": f"update-{round_index - 1}",
                         "protocol_sha256": content_hash(protocol), "active_ids": [packet["parent_bundle_id"]],
                         "feedback_sha256": "f" * 64, "measurements": [], "member_bindings": {},
                         "cumulative_sources": []}
            selection["selection_sha256"] = content_hash(selection)
            packet["selection"] = selection
        reseal(packet)
        capsule = ProposerCapsule.from_packet(packet, roots=roots)
        run = f"SAEA-SLURP-PROPOSER-{key}"
        member = {"key": key, "capsule": pin(folder / "capsule.json", capsule.as_json()),
                  "input": pin(folder / "input.json", packet), "request_sha256": content_hash(capsule.request()),
                  "execution_plan": {"run_id": run, "execution_profile": "bounded-discovery-probe", "carrier_lock_key": "slurp",
                  "split_role": "discovery", "split_identity_hash": packet["input_sha256"], "planned_model_calls": 4,
                  "planned_gpu_hours": 1.0, "planned_speech_audio_seconds": 1, "protocol_hash": content_hash(protocol)}}
        r["members"].append(member)
        rows.append(f"| {run} | bounded-discovery-probe | slurp TRAIN | discovery | {packet['input_sha256']} | no | 4 | 1 | 1.0 | REGISTERED BEFORE contact |")
    p = tmp_path / "ledger.md"
    p.write_text("\n".join(rows))
    r["ledger"] = {"path": str(p), "sha256": runner.digest(p)}
    return r


@pytest.mark.parametrize("round_index", [1, 2, 3])
def test_exact_four_inputs_pass_without_contact(tmp_path, round_index):
    jobs, _, _ = runner.load_members(registration(tmp_path, round_index))
    assert len(jobs) == 4
    assert all(runner.request_bound(c.request()) < 32768 for _, c, _ in jobs)
    assert {c.as_json()["packet"]["round"] for _, c, _ in jobs} == {round_index}


def test_existing_first_round_registration_remains_compatible(tmp_path):
    r = registration(tmp_path)
    del r["round_index"]
    assert len(runner.load_members(r)[0]) == 4


def test_compact_profile_requires_matching_transport_admission(tmp_path):
    r = registration(tmp_path)
    r["capsule_view_profile"] = "compact-feedback-v1"
    with pytest.raises(PolicyError, match="profile.*admission"):
        runner.load_members(r)
    admission = runner.read_pin(r["provider_admission"])
    admission["capsule_view_profile"] = "compact-feedback-v1"
    r["provider_admission"] = pin(Path(r["provider_admission"]["path"]), admission)
    with pytest.raises(PolicyError, match="same admitted.*profile"):
        runner.load_members(r)


@pytest.mark.parametrize("declared", [0, 4, True, "2", 1, 3])
def test_round_mismatch_or_undeclared_round_refuses_before_transport(tmp_path, declared):
    r = registration(tmp_path, 2)
    r["round_index"] = declared
    with pytest.raises(PolicyError, match="round"):
        runner.load_members(r)


@pytest.mark.parametrize("round_index", [2, 3])
def test_closed_allocation_cannot_borrow_another_rounds_failure(tmp_path, round_index):
    r = registration(tmp_path, round_index)
    key = f"L-{round_index}-1"
    evidence = {"outcome": pin(tmp_path / "failed.json", {"status": "failed"}),
                "import": pin(tmp_path / "invalid.json", {"status": "invalid", "proposal_allocation": ["L", round_index, 1]})}
    r["closed_allocations"] = {key: evidence}
    jobs, _, _ = runner.load_members(r)
    assert key not in [member["key"] for member, _, _ in jobs]
    evidence["import"] = pin(tmp_path / "wrong-round.json", {"status": "invalid", "proposal_allocation": ["L", 1, 1]})
    with pytest.raises(PolicyError, match="closed allocation"):
        runner.load_members(r)


@pytest.mark.parametrize("mutation", ["missing-selection", "old-feedback", "different-feedback"])
def test_later_round_cannot_skip_the_preceding_selection_binding(tmp_path, mutation):
    r = registration(tmp_path, 2)
    member = r["members"][0]
    document = runner.read_pin(member["capsule"])
    packet = document["packet"]
    if mutation == "missing-selection":
        del packet["selection"]
    elif mutation == "old-feedback":
        packet["feedback"]["family_id"] = "initial"
    else:
        packet["feedback"]["read_gate_family_sha256"] = "e" * 64
    reseal(packet)
    capsule = ProposerCapsule(packet, {a["artifact_id"]: a for a in document["artifacts"]})
    member["input"] = pin(Path(member["input"]["path"]), packet)
    member["capsule"] = pin(Path(member["capsule"]["path"]), capsule.as_json())
    member["request_sha256"] = content_hash(capsule.request())
    member["execution_plan"]["split_identity_hash"] = packet["input_sha256"]
    ledger = Path(r["ledger"]["path"])
    rows = ledger.read_text().splitlines()
    rows[2] = rows[2].replace(rows[2].split("|")[5].strip(), packet["input_sha256"])
    ledger.write_text("\n".join(rows))
    r["ledger"]["sha256"] = runner.digest(ledger)
    with pytest.raises(PolicyError, match="preceding"):
        runner.load_members(r)


@pytest.mark.parametrize("round_index", [2, 3])
def test_later_round_dispatch_imports_its_own_allocation(tmp_path, monkeypatch, round_index):
    r = registration(tmp_path, round_index)
    r.update(source_root=str(tmp_path), source_commit="fixture-commit", source_pins={}, auth={},
             archive=str(tmp_path / "archive"), output_root=str(tmp_path / "execution"))
    r["provider_admission"] = pin(tmp_path / "admission.json", {
        "protocol_sha256": runner.read_pin(r["provider_admission"])["protocol_sha256"], "endpoint": "fixture-only"})
    archive = runner.SystemSearchArchive(r["archive"])
    for member in r["members"]:
        archive.store_input(runner.read_pin(member["input"]))
    path = tmp_path / "registration.json"
    registered = pin(path, r)
    monkeypatch.setattr(runner.sys, "argv", ["proposer_round", str(path), "--sha256", registered["sha256"]])
    monkeypatch.setattr(runner.sys, "dont_write_bytecode", True)
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    monkeypatch.setattr(runner, "assert_wsl_execution_environment", lambda: None)
    monkeypatch.setattr(runner.subprocess, "check_output", lambda command, **kw: "" if "status" in command else "fixture-commit\n")
    monkeypatch.setattr(runner, "SubscriptionBearer", lambda **kw: lambda: "fixture-no-token")
    monkeypatch.setattr(runner, "ResponsesHTTP", lambda *args, **kw: None)

    def fake_transport(capsule, client, **options):
        def receive(request):
            packet = capsule.as_json()["packet"]
            options["before_contact"]({"contact": 1, "proposal_input_sha256": packet["input_sha256"]})
            return {"raw_response": json.dumps(capsule.initial_input()["response_contract"]["example"]),
                    "model_version": packet["model_version"], "input_tokens": 100, "output_tokens": 10}
        return receive

    monkeypatch.setattr(runner, "ResponsesProposer", fake_transport)
    assert runner.main() == 0
    for member in r["members"]:
        result = json.loads((archive.root / "imports" / (member["key"] + ".json")).read_text())
        assert result["proposal_allocation"] == [member["key"][0], round_index, int(member["key"][-1])]
        assert result["status"] == "no-change"
    assert not list((archive.root / "imports").glob("*-1-*.json"))


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
        protocol = json.loads(Path(r["protocol"]["path"]).read_text())
        protocol["proposer_exact_version"] = "changed"
        r["protocol"] = pin(Path(r["protocol"]["path"]), protocol)
    with pytest.raises(PolicyError):
        runner.load_members(r)


def fourth_registration(tmp_path):
    from test_system_search_allocations import fixture as allocation_fixture
    from speech_aware_evidence_acquisition.rails.system_search_allocations import register_extension
    archive, repo, _, extension = allocation_fixture(tmp_path / "extension")
    requests = tmp_path / "requests"
    requests.mkdir()
    r = registration(requests, 3)
    seed_id = runner.read_pin(r["members"][0]["input"])["seed_bundle_id"]
    previous_path = repo / extension["previous_protocol"]["relpath"]
    previous = json.loads(previous_path.read_text())
    previous["seed_bundle"]["bundle_id"] = seed_id
    previous_path.write_text(json.dumps(previous))
    extension["previous_protocol"]["sha256"] = runner.digest(previous_path)
    extension["seed_bundle_id"] = seed_id
    register_extension(archive, extension, repo_root=repo)
    protocol = runner.read_pin(r["protocol"])
    protocol.update(allocation_extension=extension, proposer_exact_version=extension["model_version"])
    r.update(round_index=4, source_root=str(repo), archive=str(archive.root))
    r["protocol"] = pin(Path(r["protocol"]["path"]), protocol)
    r["provider_admission"] = pin(Path(r["provider_admission"]["path"]), {"protocol_sha256": content_hash(protocol)})
    ledger = Path(r["ledger"]["path"])
    rows = ledger.read_text()
    for member in r["members"]:
        doc = runner.read_pin(member["capsule"])
        packet = doc["packet"]
        old_hash = packet["input_sha256"]
        packet.update(round=4, model_version=extension["model_version"], protocol_sha256=content_hash(protocol),
                      allocation_extension_sha256=content_hash(extension), seed_bundle_id=extension["seed_bundle_id"])
        # The fixture seed bytes are identical; this asserts the custody join.
        assert packet["parent_bundle_id"] == extension["seed_bundle_id"]
        if packet["branch"] == "L":
            packet["feedback"]["family_id"] = "update-3"
            packet["selection"].update(stage="update-3", protocol_sha256=content_hash(protocol))
            packet["selection"]["selection_sha256"] = content_hash({k: v for k, v in packet["selection"].items() if k != "selection_sha256"})
        reseal(packet)
        member["key"] = f"{packet['branch']}-4-{packet['slot']}"
        capsule = ProposerCapsule(packet, {a["artifact_id"]: a for a in doc["artifacts"]})
        member["capsule"] = pin(Path(member["capsule"]["path"]), capsule.as_json())
        member["input"] = pin(Path(member["input"]["path"]), packet)
        member["request_sha256"] = content_hash(capsule.request())
        member["execution_plan"].update(protocol_hash=content_hash(protocol), split_identity_hash=packet["input_sha256"])
        rows = rows.replace(old_hash, packet["input_sha256"])
    ledger.write_text(rows)
    r["ledger"]["sha256"] = runner.digest(ledger)
    return r


def test_registered_fourth_round_requires_actual_archive_and_owner_before_transport(tmp_path):
    r = fourth_registration(tmp_path)
    assert len(runner.load_members(r)[0]) == 4
    allocation = Path(r["archive"]) / "allocations/round-4.json"
    allocation.unlink()
    with pytest.raises(PolicyError, match="extension"):
        runner.load_members(r)


def test_fourth_round_rejects_changed_owner_even_when_packet_and_archive_match(tmp_path):
    from speech_aware_evidence_acquisition.rails.system_search_allocations import OWNER223
    r = fourth_registration(tmp_path)
    (Path(r["source_root"]) / OWNER223).write_text("{}")
    with pytest.raises(PolicyError):
        runner.load_members(r)


def test_fourth_round_mock_transport_spends_exactly_four_new_slots(tmp_path, monkeypatch):
    r = fourth_registration(tmp_path)
    r.update(source_commit="fixture-commit", source_pins={}, auth={}, output_root=str(tmp_path / "execution"))
    admission = runner.read_pin(r["provider_admission"])
    admission["endpoint"] = "fixture-only"
    r["provider_admission"] = pin(Path(r["provider_admission"]["path"]), admission)
    archive = runner.SystemSearchArchive(r["archive"])
    before = {str(p): p.read_bytes() for folder in ("inputs", "responses", "imports")
              for p in (archive.root / folder).glob("*.json")}
    for member in r["members"]:
        archive.store_input(runner.read_pin(member["input"]))
    registered = pin(tmp_path / "dispatch.json", r)
    monkeypatch.setattr(runner.sys, "argv", ["proposer_round", registered["path"], "--sha256", registered["sha256"]])
    monkeypatch.setattr(runner.sys, "dont_write_bytecode", True)
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    monkeypatch.setattr(runner, "assert_wsl_execution_environment", lambda: None)
    monkeypatch.setattr(runner.subprocess, "check_output", lambda command, **kw: "" if "status" in command else "fixture-commit\n")
    monkeypatch.setattr(runner, "SubscriptionBearer", lambda **kw: lambda: "fixture-no-token")
    monkeypatch.setattr(runner, "ResponsesHTTP", lambda *args, **kw: None)
    def transport(capsule, client, **options):
        def receive(request):
            packet = capsule.as_json()["packet"]
            options["before_contact"]({"contact": 1, "proposal_input_sha256": packet["input_sha256"]})
            return {"raw_response": json.dumps(capsule.initial_input()["response_contract"]["example"]),
                    "model_version": packet["model_version"], "input_tokens": 100, "output_tokens": 10}
        return receive
    monkeypatch.setattr(runner, "ResponsesProposer", transport)
    assert runner.main() == 0
    assert all(Path(p).read_bytes() == raw for p, raw in before.items())
    assert len(list((archive.root / "imports").glob("*.json"))) == 16
    for member in r["members"]:
        imported = json.loads((archive.root / "imports" / (member["key"] + ".json")).read_text())
        assert imported["status"] == "no-change"
        assert imported["proposal_allocation"][1] == 4


def test_check_only_validates_transport_fingerprint_without_credentials(tmp_path, monkeypatch):
    r = registration(tmp_path)
    r.update(source_root=str(tmp_path), source_commit="fixture", source_pins={}, auth={})
    admission = runner.read_pin(r["provider_admission"])
    admission.update(endpoint="https://api.openai.com/v1/responses", status="admitted", owner_decision=217,
                     provider_profile="chatgpt-plan-preview", budget_profile="subscription-metered-reject-v1",
                     output_cap_enforcement="metered-reject-after-completion", paid_api_spend=0,
                     model_version="gpt-6-sol", sha256="0" * 64)
    r["provider_admission"] = pin(tmp_path / "admission.json", admission)
    registered = pin(tmp_path / "dispatch.json", r)
    monkeypatch.setattr(runner.sys, "argv", ["proposer_round", registered["path"], "--sha256", registered["sha256"], "--check-only"])
    monkeypatch.setattr(runner.sys, "dont_write_bytecode", True)
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    monkeypatch.setattr(runner, "assert_wsl_execution_environment", lambda: None)
    monkeypatch.setattr(runner.subprocess, "check_output", lambda command, **kw: "" if "status" in command else "fixture\n")
    def forbidden_credentials(**kwargs):
        raise AssertionError("Offline preflight cannot load credentials.")
    monkeypatch.setattr(runner, "SubscriptionBearer", forbidden_credentials)
    with pytest.raises(PolicyError, match="fingerprint"):
        runner.main()
    admission["sha256"] = content_hash({k:v for k,v in admission.items() if k != "sha256"})
    r["provider_admission"] = pin(tmp_path / "admission.json", admission)
    registered = pin(tmp_path / "dispatch.json", r)
    runner.sys.argv = ["proposer_round", registered["path"], "--sha256", registered["sha256"], "--check-only"]
    assert runner.main() == 0


@pytest.mark.parametrize("error_class", [PolicyError, TimeoutError])
def test_credential_failure_is_durable_before_any_allocation(tmp_path, monkeypatch, error_class):
    r = registration(tmp_path)
    r.update(source_root=str(tmp_path), source_commit="fixture-commit", source_pins={}, auth={},
             archive=str(tmp_path / "archive"), output_root=str(tmp_path / "execution"))
    admission = runner.read_pin(r["provider_admission"])
    admission["endpoint"] = "fixture-only"
    r["provider_admission"] = pin(tmp_path / "admission.json", admission)
    path = tmp_path / "registration.json"
    registered = pin(path, r)
    monkeypatch.setattr(runner.sys, "argv", ["proposer_round", str(path), "--sha256", registered["sha256"]])
    monkeypatch.setattr(runner.sys, "dont_write_bytecode", True)
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    monkeypatch.setattr(runner, "assert_wsl_execution_environment", lambda: None)
    monkeypatch.setattr(runner.subprocess, "check_output", lambda command, **kw: "" if "status" in command else "fixture-commit\n")
    monkeypatch.setattr(runner, "ResponsesHTTP", lambda *a, **k: None)
    calls = []
    def unavailable():
        calls.append(1)
        assert (tmp_path / "execution/precontact.json").is_file()
        raise error_class("secret-from-untrusted-child-stream")
    monkeypatch.setattr(runner, "SubscriptionBearer", lambda **kw: unavailable)
    monkeypatch.setattr(runner, "ProposalDispatch", lambda *a, **k: pytest.fail("slot reserved"))
    assert runner.main() == 1
    output = tmp_path / "execution"
    evidence = json.loads((output / "precontact-failure.json").read_text())
    assert evidence["phase"] == "credential-check"
    assert evidence["generation_contacts"] == evidence["allocations_reserved"] == 0
    assert evidence["error_type"] == error_class.__name__
    assert evidence["retry_permitted"] is False
    assert not (output / "started.json").exists()
    assert not (tmp_path / "archive").exists()
    assert "secret" not in "".join(p.read_text() for p in output.iterdir())
    with pytest.raises(FileExistsError):
        runner.main()
    assert len(calls) == 1


def test_prepared_registration_is_only_readable_for_no_contact_check(tmp_path):
    r = registration(tmp_path)
    r["status"] = "prepared-awaiting-exact-root-admission"
    with pytest.raises(PolicyError, match="admission"):
        runner.load_members(r)
    assert len(runner.load_members(r, check_only=True)[0]) == 4
