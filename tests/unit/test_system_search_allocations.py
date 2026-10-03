"""Prospective extensions preserve spent slots and never authorize runtime."""

import copy
import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_search_archive import (
    SystemSearchArchive,
    proposal_input,
)
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    PolicyError,
    SystemTextPolicyBundle,
    TextPolicyUpdateProposal,
)
from speech_aware_evidence_acquisition.rails.system_search_allocations import (
    OWNER223,
    build_extension,
    register_extension,
    require_round,
    require_packet_allocation,
)
from test_system_text_policy import seed_document


def write_pin(root, name, document):
    p = root / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(document))
    return {"relpath": name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}


def fixture(tmp_path):
    repo = tmp_path / "repo"
    archive = SystemSearchArchive(tmp_path / "archive")
    seed = SystemTextPolicyBundle.from_json(seed_document())
    owner = write_pin(repo, OWNER223, {"decision_id": 223, "status": "approved"})
    protocol = {
        "proposer_exact_version": "GPT6-pinned",
        "proposal_input_token_cap": 32768,
        "proposal_output_token_cap": 4096,
        "proposal_contact_cap": 4,
        "seed_bundle": {"bundle_id": seed.bundle_id},
    }
    previous = write_pin(repo, "previous.json", protocol)
    for round_index in (1, 2, 3):
        for branch in ("L", "B"):
            for slot in (1, 2):
                key = f"{branch}-{round_index}-{slot}"
                packet = {
                    "branch": branch,
                    "round": round_index,
                    "slot": slot,
                    "model_version": "GPT6-pinned",
                    "session_id": key,
                }
                packet["input_sha256"] = content_hash(packet)
                response = {
                    "model_version": "GPT6-pinned",
                    "input_sha256": packet["input_sha256"],
                    "session_id": key,
                    "raw_response": "invalid",
                    "input_tokens": 10,
                    "output_tokens": 1,
                }
                imported = {
                    "proposal_allocation": [branch, round_index, slot],
                    "status": "invalid",
                    "input_sha256": packet["input_sha256"],
                    "receipt_sha256": content_hash(response),
                }
                for folder, d in (
                    ("inputs", packet),
                    ("responses", response),
                    ("imports", imported),
                ):
                    archive._write(f"{folder}/{key}.json", d)
    extension = build_extension(
        archive, round_index=4, owner=owner, previous_protocol=previous, repo_root=repo
    )
    return archive, repo, seed, extension


def test_build_is_read_only_and_registration_preserves_twelve_spent_slots(tmp_path):
    archive, repo, _, extension = fixture(tmp_path)
    assert len(extension["earlier_allocations"]) == 12
    assert not (archive.root / "allocations").exists()
    before = {str(p): p.read_bytes() for p in archive.root.rglob("*.json")}
    register_extension(archive, extension, repo_root=repo)
    assert archive.allocation_extension(4) == extension
    assert all(
        __import__("pathlib").Path(p).read_bytes() == raw for p, raw in before.items()
    )
    with pytest.raises(PolicyError, match="consumed|exists|registered"):
        register_extension(archive, extension, repo_root=repo)


@pytest.mark.parametrize("index", [0, True, "4", 5, -1])
def test_explicit_extension_cannot_open_other_rounds(tmp_path, index):
    _, _, _, extension = fixture(tmp_path)
    with pytest.raises(PolicyError):
        require_round(index, extension)


def test_unregistered_rounds_still_refuse_and_default_parser_stays_bounded(tmp_path):
    archive, _, seed, extension = fixture(tmp_path)
    with pytest.raises(PolicyError):
        archive.allocation_extension(4)
    with pytest.raises(PolicyError):
        proposal_input(
            branch="B",
            round_index=4,
            slot=1,
            seed=seed,
            parent=seed,
            model_version="GPT6-pinned",
            session_id="new",
            input_token_cap=32768,
            output_token_cap=4096,
        )
    doc = {
        "schema": "saea-text-policy-update-proposal-v1",
        "branch": "B",
        "round": 4,
        "slot": 1,
        "parent_ids": [seed.bundle_id],
        "changes": {},
        "rationale": "Retain seed.",
        "hypotheses": [],
        "evidence": [],
    }
    with pytest.raises(PolicyError):
        TextPolicyUpdateProposal.from_json(doc)
    assert TextPolicyUpdateProposal.from_json(doc, allocation_extension=extension)


@pytest.mark.parametrize(
    "fault",
    [
        "missing-import",
        "changed-response",
        "wrong-identity",
        "owner",
        "model",
        "budget",
        "runtime",
        "scope",
        "partial-history",
        "old-slot-opened",
    ],
)
def test_registration_refuses_broken_custody_before_input_or_contact(tmp_path, fault):
    archive, repo, _, extension = fixture(tmp_path)
    if fault == "missing-import":
        (archive.root / "imports/L-2-1.json").unlink()
    elif fault == "changed-response":
        (archive.root / "responses/L-1-1.json").write_text("{}")
    elif fault == "wrong-identity":
        p = archive.root / "imports/B-3-1.json"
        d = json.loads(p.read_text())
        d["proposal_allocation"] = ["L", 3, 1]
        p.write_text(json.dumps(d))
    elif fault == "owner":
        (repo / OWNER223).write_text("{}")
    elif fault == "model":
        extension["model_version"] = "another-model"
    elif fault == "budget":
        extension["output_token_cap"] += 1
    elif fault == "runtime":
        extension["no_runtime_authority"] = False
    elif fault == "scope":
        extension["editable"] = ["role_text", "knowledge"]
    elif fault == "partial-history":
        extension["earlier_allocations"].pop("L-1-1")
    else:
        archive._write("inputs/L-4-1.json", {})
    with pytest.raises((PolicyError, FileNotFoundError)):
        register_extension(archive, extension, repo_root=repo)
    assert not (archive.root / "allocations/round-4.json").exists()


def test_new_round_import_is_immutable_and_blind_input_has_no_history(tmp_path):
    archive, repo, seed, extension = fixture(tmp_path)
    register_extension(archive, extension, repo_root=repo)
    packet = proposal_input(
        branch="B",
        round_index=4,
        slot=1,
        seed=seed,
        parent=seed,
        model_version="GPT6-pinned",
        session_id="fresh-four",
        input_token_cap=32768,
        output_token_cap=4096,
        allocation_extension=extension,
    )
    assert (
        "feedback" not in packet
        and "learning_history" not in packet
        and "earlier_allocations" not in packet
    )
    assert packet["allocation_extension_sha256"] == content_hash(extension)
    archive.store_input(packet)
    doc = {
        "schema": "saea-text-policy-update-proposal-v1",
        "branch": "B",
        "round": 4,
        "slot": 1,
        "parent_ids": [seed.bundle_id],
        "changes": {},
        "rationale": "Retain seed.",
        "hypotheses": [],
        "evidence": [],
    }
    receipt = {
        "raw_response": json.dumps(doc),
        "session_id": "fresh-four",
        "model_version": "GPT6-pinned",
        "input_sha256": packet["input_sha256"],
        "input_tokens": 100,
        "output_tokens": 40,
    }
    assert (
        archive.import_response(branch="B", round_index=4, slot=1, receipt=receipt)[
            "status"
        ]
        == "no-change"
    )
    with pytest.raises(PolicyError):
        archive.import_response(branch="B", round_index=4, slot=1, receipt=receipt)
    assert len(list((archive.root / "imports").glob("*.json"))) == 13


def test_packet_digest_is_not_its_own_execution_authority(tmp_path):
    _, _, seed, extension = fixture(tmp_path)
    packet = proposal_input(
        branch="B",
        round_index=4,
        slot=1,
        seed=seed,
        parent=seed,
        model_version="GPT6-pinned",
        session_id="new",
        input_token_cap=32768,
        output_token_cap=4096,
        allocation_extension=extension,
    )
    protocol = {"allocation_extension": extension}
    require_packet_allocation(packet, protocol)
    for fault in ("missing", "digest", "round", "model", "budget"):
        p, spec = copy.deepcopy(packet), copy.deepcopy(protocol)
        if fault == "missing":
            spec.clear()
        elif fault == "digest":
            p["allocation_extension_sha256"] = "f" * 64
        elif fault == "round":
            p["round"] = 5
        elif fault == "model":
            p["model_version"] = "different"
        else:
            p["output_token_cap"] += 1
        with pytest.raises(PolicyError):
            require_packet_allocation(p, spec)


def test_changed_prior_bytes_invalidate_already_registered_extension(tmp_path):
    archive, repo, _, extension = fixture(tmp_path)
    register_extension(archive, extension, repo_root=repo)
    p = archive.root / "imports/L-1-1.json"
    p.write_text(p.read_text() + " ")
    with pytest.raises(PolicyError, match="changed"):
        archive.allocation_extension(4)


def test_invalid_receipt_identity_still_spends_prior_slot(tmp_path):
    archive, repo, _, extension = fixture(tmp_path)
    p = archive.root / "responses/L-1-1.json"
    response = json.loads(p.read_text())
    response["session_id"] = "wrong-session"
    p.write_text(json.dumps(response))
    p = archive.root / "imports/L-1-1.json"
    imported = json.loads(p.read_text())
    imported["receipt_sha256"] = content_hash(response)
    p.write_text(json.dumps(imported))
    rebuilt = build_extension(
        archive,
        round_index=4,
        owner=extension["owner"],
        previous_protocol=extension["previous_protocol"],
        repo_root=repo,
    )
    register_extension(archive, rebuilt, repo_root=repo)
    assert len(rebuilt["earlier_allocations"]) == 12


def test_following_extension_requires_the_closed_preceding_round(tmp_path):
    archive, repo, seed, extension = fixture(tmp_path)
    register_extension(archive, extension, repo_root=repo)
    previous = json.loads(
        (repo / extension["previous_protocol"]["relpath"]).read_text()
    )
    previous["allocation_extension"] = extension
    previous_pin = write_pin(repo, "fourth.json", previous)
    with pytest.raises(PolicyError, match="not closed"):
        build_extension(
            archive,
            round_index=5,
            owner=extension["owner"],
            previous_protocol=previous_pin,
            repo_root=repo,
        )
    for branch in ("L", "B"):
        for slot in (1, 2):
            key = f"{branch}-4-{slot}"
            packet = {
                "branch": branch,
                "round": 4,
                "slot": slot,
                "model_version": "GPT6-pinned",
                "session_id": key,
            }
            packet["input_sha256"] = content_hash(packet)
            response = {
                "model_version": "GPT6-pinned",
                "input_sha256": packet["input_sha256"],
                "session_id": key,
            }
            imported = {
                "proposal_allocation": [branch, 4, slot],
                "status": "no-change",
                "input_sha256": packet["input_sha256"],
                "receipt_sha256": content_hash(response),
            }
            for folder, d in (
                ("inputs", packet),
                ("responses", response),
                ("imports", imported),
            ):
                archive._write(f"{folder}/{key}.json", d)
    fifth = build_extension(
        archive,
        round_index=5,
        owner=extension["owner"],
        previous_protocol=previous_pin,
        repo_root=repo,
    )
    assert len(fifth["earlier_allocations"]) == 16
    register_extension(archive, fifth, repo_root=repo)
    assert archive.allocation_extension(5) == fifth
    previous.pop("allocation_extension")
    wrong = write_pin(repo, "wrong-previous.json", previous)
    with pytest.raises(PolicyError, match="preceding"):
        build_extension(
            archive,
            round_index=5,
            owner=extension["owner"],
            previous_protocol=wrong,
            repo_root=repo,
        )
