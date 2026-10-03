"""Run a registered round through the existing isolated proposer, without GPU dispatch."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from speech_aware_evidence_acquisition.contracts import ExecutionPlan, assert_wsl_execution_environment
from speech_aware_evidence_acquisition.contracts.ledger import _parse_ledger_tables
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_proposer_capsule import ProposerCapsule, ProposalDispatch, input_references
from speech_aware_evidence_acquisition.rails.system_proposer_responses import ResponsesHTTP, ResponsesProposer
from speech_aware_evidence_acquisition.rails.system_search_archive import SystemSearchArchive
from speech_aware_evidence_acquisition.rails.system_subscription_auth import SubscriptionBearer
from speech_aware_evidence_acquisition.rails.system_text_policy import canonical, require


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_pin(pin):
    raw = Path(pin["path"]).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == pin["sha256"], "registered file changed")
    return json.loads(raw)


def write_once(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(canonical(value) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def request_bound(request):
    """Conservative byte-level text bound plus the registered framing reserve.

    Count the entire serialized request, including tools and repeated history.
    Provider usage is independently checked; a violation rejects the proposal.
    This is an admission bound, not a claim to expose the private tokenizer.
    """
    return len(canonical(request).encode("utf-8")) + 4096


def require_feedback_transition(packet, *, protocol, round_index):
    """Distinguish the exact exploratory allowance from formal round progression."""
    from speech_aware_evidence_acquisition.rails.system_optimization import (
        require_exploratory_packet, require_optimization_scope,
    )
    require_optimization_scope(packet, protocol=protocol)
    if packet["branch"] == "L" and round_index > 1:
        if protocol.get("exploratory_learning"):
            require_exploratory_packet(packet, protocol=protocol)
        else:
            selection, feedback = packet.get("selection"), packet["feedback"]
            require(isinstance(selection, dict)
                    and feedback.get("family_id") == f"update-{round_index - 1}"
                    and bool(feedback.get("read_gate_family_sha256"))
                    and selection.get("feedback_sha256") == feedback["read_gate_family_sha256"],
                    "preceding complete-family feedback and selection binding required")


def load_members(registration, *, check_only=False):
    r = registration
    require(r["schema"] == "saea-system-text-proposer-round-registration-v1"
            and (r["status"] == "root-admitted" or (check_only is True
                and r["status"] == "prepared-awaiting-exact-root-admission"))
            and r["owner_decision"] == 217,
            "round admission required")
    # Older admitted registrations covered round one and omitted this field.
    # Later rounds must name their allocation explicitly, never infer it from a key.
    round_index = r.get("round_index", 1)
    require(type(round_index) is int and round_index > 0, "invalid registered round")
    owner = read_pin(r["owner_receipt"])
    require(owner["decisions"]["217"]["status"] == "approved", "owner217 is not approved")
    admission = read_pin(r["provider_admission"])
    protocol = read_pin(r["protocol"])
    from speech_aware_evidence_acquisition.rails.system_search_allocations import (
        require_round, require_packet_allocation, validate_extension,
    )
    extension = protocol.get("allocation_extension") if round_index > 3 else None
    require_round(round_index, extension)
    if extension is not None:
        archive = SystemSearchArchive(r["archive"])
        require(archive.allocation_extension(round_index) == extension, "registered archive extension differs")
        validate_extension(archive, extension, repo_root=r["source_root"])
        require(protocol["proposal_contact_cap"] == extension["contact_cap"], "extension contact budget differs")
    require(admission["protocol_sha256"] == content_hash(protocol), "provider protocol differs")
    from speech_aware_evidence_acquisition.rails.system_proposer_continuation import require_limits
    require_limits(protocol.get("proposal_continuation_limits"))
    require(admission.get("continuation_limits") == protocol.get("proposal_continuation_limits"),
            "provider continuation envelope differs")
    profile = r.get("capsule_view_profile", "full-index-v1")
    require(profile == admission.get("capsule_view_profile", "full-index-v1"),
            "capsule view profile requires provider admission")
    require(digest(r["ledger"]["path"]) == r["ledger"]["sha256"], "contact ledger changed")
    ledger = _parse_ledger_tables(Path(r["ledger"]["path"]).read_text())
    jobs, keys = [], set()
    for member in r["members"]:
        document = read_pin(member["capsule"])
        packet = document["packet"]
        input_references(packet)
        require_packet_allocation(packet, protocol)
        require(type(packet["round"]) is int and packet["round"] == round_index,
                "proposal differs from the registered round")
        require_feedback_transition(packet, protocol=protocol, round_index=round_index)
        key = f"{packet['branch']}-{packet['round']}-{packet['slot']}"
        require(key == member["key"] and key not in keys, "duplicate or wrong proposal allocation")
        keys.add(key)
        require(packet["protocol_sha256"] == content_hash(protocol)
                and packet["model_version"] == protocol["proposer_exact_version"]
                and packet["input_token_cap"] == protocol["proposal_input_token_cap"]
                and packet["output_token_cap"] == protocol["proposal_output_token_cap"],
                "proposal protocol/model/budgets differ")
        require(read_pin(member["input"]) == packet, "capsule input differs from immutable archive input")
        plan = ExecutionPlan(**member["execution_plan"]).validate()
        require(plan.protocol_hash == content_hash(protocol) and plan.split_identity_hash == packet["input_sha256"]
                and plan.split_role == "discovery" and plan.planned_model_calls == protocol["proposal_contact_cap"],
                "proposal execution plan differs")
        rows = [row for row in ledger if row.get("run/experiment id") == plan.run_id]
        require(len(rows) == 1 and rows[0]["consumed"] == "no"
                and rows[0]["split identity hash"] == packet["input_sha256"]
                and int(rows[0]["calls"]) == plan.planned_model_calls
                and "REGISTERED BEFORE" in rows[0].get("notes", ""),
                "proposal contact preregistration missing or changed")
        capsule = ProposerCapsule.from_json(document)
        require(capsule.view_profile == profile, "both branches require the same admitted capsule view profile")
        request = capsule.request()
        require(content_hash(request) == member["request_sha256"], "actual initial request differs")
        require(request_bound(request) <= packet["input_token_cap"], "initial input does not fit")
        jobs.append((member, capsule, plan))
    require(keys == {f"{branch}-{round_index}-{slot}" for branch in ("L", "B") for slot in (1, 2)},
            "registered round membership differs")
    closed = r.get("closed_allocations", {})
    require(set(closed) <= keys, "unknown closed allocation")
    for key, evidence in closed.items():
        outcome = read_pin(evidence["outcome"])
        imported = read_pin(evidence["import"])
        require(outcome["status"] == "failed" and imported["status"] == "invalid"
                and imported["proposal_allocation"] == [key[0], round_index, int(key[-1])],
                "closed allocation must retain failed transport and invalid import")
    jobs = [job for job in jobs if job[0]["key"] not in closed]
    require(jobs, "no unconsumed proposal allocations")
    return jobs, admission, protocol


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("registration", type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    r = read_pin({"path": str(args.registration), "sha256": args.sha256})
    require(sys.dont_write_bytecode and os.environ.get("PYTHONDONTWRITEBYTECODE") == "1", "disable bytecode writing")
    assert_wsl_execution_environment()
    root = Path(r["source_root"])
    require(not subprocess.check_output(["git", "-C", str(root), "status", "--porcelain"], text=True).strip(), "worker must be clean")
    require(subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip() == r["source_commit"], "worker commit differs")
    for relative, expected in r["source_pins"].items():
        require(digest(root / relative) == expected, "admitted proposer source changed")
    jobs, admission, protocol = load_members(r, check_only=args.check_only)
    # Construct the real validator before credentials, reservations or contacts.
    # This constructor performs no network request; never call its bearer here.
    def no_preflight_credentials():
        raise RuntimeError("Offline transport preflight cannot request credentials")
    ResponsesHTTP(admission["endpoint"], bearer=no_preflight_credentials, admission=admission)
    if args.check_only:
        print(canonical({"preflight": "PASS", "members": len(jobs), "contacts_added": 0,
                         "request_bounds": {m["key"]: request_bound(c.request()) for m, c, _ in jobs}}))
        return 0
    # Record entry before credentials, while every proposal slot is still free.
    # Keep check-only side-effect free; never place child streams in receipts.
    output = Path(r["output_root"])
    output.mkdir(parents=True, exist_ok=False)
    write_once(output / "precontact.json", {"at_utc": datetime.now(timezone.utc).isoformat(),
        "pid": os.getpid(), "registration_sha256": args.sha256,
        "phase": "credential-check", "generation_contacts": 0, "allocations_reserved": 0})
    try:
        # This may renew the own-app grant; it makes no proposal/model request.
        bearer = SubscriptionBearer(**r["auth"])
        ready_token = bearer()
        del ready_token
    except Exception as error:
        failure = {"at_utc": datetime.now(timezone.utc).isoformat(),
            "registration_sha256": args.sha256, "phase": "credential-check",
            "status": "precontact-failure", "error_type": type(error).__name__,
            "generation_contacts": 0, "allocations_reserved": 0, "retry_permitted": False}
        from speech_aware_evidence_acquisition.rails.system_subscription_auth import (
            CredentialFailure, safe_credential_failure,
        )
        if type(error) is CredentialFailure:
            failure["credential_failure"] = safe_credential_failure(error)
        write_once(output / "precontact-failure.json", failure)
        print(canonical(failure))
        return 1
    write_once(output / "started.json", {"at_utc": datetime.now(timezone.utc).isoformat(), "pid": os.getpid(),
        "registration_sha256": args.sha256, "retry_permitted": False})
    archive = SystemSearchArchive(r["archive"])
    outcomes = []
    for member, capsule, plan in jobs:
        key = member["key"]
        try:
            def before_contact(evidence):
                require(1 <= evidence["contact"] <= plan.planned_model_calls
                        and evidence["proposal_input_sha256"] == plan.split_identity_hash,
                        "unregistered contact")
                write_once(output / "contacts" / key / f"{evidence['contact']:03d}.json", {
                    "at_utc": datetime.now(timezone.utc).isoformat(), "execution_plan": member["execution_plan"],
                    "registration_sha256": args.sha256, "reservation": evidence})
            transport = ResponsesProposer(capsule, ResponsesHTTP(admission["endpoint"], bearer=bearer,
                admission=admission, timeout=300), audit_dir=output / "transport" / key,
                input_counter=request_bound, before_contact=before_contact, contact_cap=protocol["proposal_contact_cap"],
                continuation_limits=protocol.get("proposal_continuation_limits"))
            receipt = ProposalDispatch(Path(r["archive"]) / "dispatch", capsule).run(transport)
            packet = capsule.as_json()["packet"]
            imported = archive.import_response(branch=packet["branch"], round_index=packet["round"],
                slot=packet["slot"], receipt=receipt)
            outcomes.append({"key": key, "status": imported["status"], "activation": "none"})
        except Exception as error:
            outcomes.append({"key": key, "status": "failed", "error_type": type(error).__name__, "retry_permitted": False})
            break
    write_once(output / "finished.json", {"at_utc": datetime.now(timezone.utc).isoformat(),
        "outcomes": outcomes, "stopped_on_transport_failure": len(outcomes) < len(jobs) or outcomes[-1]["status"] == "failed",
        "gpu_dispatch": False, "paid_api_spend": 0})
    print(canonical(outcomes))
    return 1 if any(o["status"] == "failed" for o in outcomes) else 0


if __name__ == "__main__":
    raise SystemExit(main())
