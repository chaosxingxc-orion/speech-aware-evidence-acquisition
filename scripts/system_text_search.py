#!/usr/bin/env python3
"""Offline lifecycle commands for the shared whole-system text-policy search.

No command starts a server, dispatches a flight, invokes a proposer or scores.
Each scientific source read still requires its registered complete-family gate.
"""
import argparse
import json
from pathlib import Path

from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_search_archive import SystemSearchArchive, proposal_input, proposal_sources
from speech_aware_evidence_acquisition.rails.system_text_feedback import CompleteSystemFeedback
from speech_aware_evidence_acquisition.rails.system_search_protocol import stage_for, require_stage_feedback
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    SystemTextPolicyBundle, apply_text_proposal, assert_roster_disjoint,
    compile_system_text_policy, TextPolicyUpdateProposal, require,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_new(path, document):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(document, sort_keys=True, ensure_ascii=True, indent=2) + "\n")


def read_family(path, *, _seen=()):
    """Reverify saved sources instead of treating a cached feedback JSON as authority."""
    path = Path(path).resolve()
    require(path not in _seen and len(_seen) < 4, "cyclic feedback reference")
    spec = read(path)
    require(set(spec) == {"family_id", "expected_members", "bindings", "initial_reference_member", "reference_family"},
            "family specification fields differ")
    reference = (read_family(spec["reference_family"], _seen=(*_seen, path))
                 if spec["reference_family"] is not None else None)
    return CompleteSystemFeedback.from_family(spec["bindings"], expected_members=spec["expected_members"],
        family_id=spec["family_id"], initial_reference_member=spec["initial_reference_member"], reference=reference)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    seed = commands.add_parser("import-seed")
    seed.add_argument("--bundle", type=Path, required=True)
    feedback = commands.add_parser("feedback")
    feedback.add_argument("--family", type=Path, required=True)
    feedback.add_argument("--output", type=Path, required=True)
    packet = commands.add_parser("proposal-input")
    packet.add_argument("--branch", choices=("L", "B"), required=True)
    packet.add_argument("--round", type=int, choices=(1, 2, 3), required=True)
    packet.add_argument("--slot", type=int, choices=(1, 2), required=True)
    packet.add_argument("--seed-id", required=True)
    packet.add_argument("--parent-id", required=True)
    packet.add_argument("--model-version", required=True)
    packet.add_argument("--session-id", required=True)
    packet.add_argument("--protocol", type=Path, required=True)
    packet.add_argument("--family", type=Path)
    packet.add_argument("--learning-member", action="append", default=[])
    packet.add_argument("--complementary-id", action="append", default=[])
    response = commands.add_parser("import-response")
    response.add_argument("--branch", choices=("L", "B"), required=True)
    response.add_argument("--round", type=int, choices=(1, 2, 3), required=True)
    response.add_argument("--slot", type=int, choices=(1, 2), required=True)
    response.add_argument("--receipt", type=Path, required=True)
    capsule_cmd = commands.add_parser("proposal-capsule", help="Snapshot registered English inputs; no model call")
    capsule_cmd.add_argument("--branch", choices=("L", "B"), required=True)
    capsule_cmd.add_argument("--round", type=int, choices=(1, 2, 3), required=True)
    capsule_cmd.add_argument("--slot", type=int, choices=(1, 2), required=True)
    capsule_cmd.add_argument("--protocol", type=Path, required=True)
    capsule_cmd.add_argument("--data-root", type=Path, required=True)
    capsule_cmd.add_argument("--family", type=Path)
    capsule_cmd.add_argument("--learning-member", action="append", default=[])
    compile_cmd = commands.add_parser("compile-candidate")
    compile_cmd.add_argument("--branch", choices=("L", "B"), required=True)
    compile_cmd.add_argument("--round", type=int, choices=(1, 2, 3), required=True)
    compile_cmd.add_argument("--slot", type=int, choices=(1, 2), required=True)
    compile_cmd.add_argument("--seed-config", type=Path, required=True)
    compile_cmd.add_argument("--repo-root", type=Path, required=True)
    compile_cmd.add_argument("--staging-root", type=Path, required=True)
    compile_cmd.add_argument("--evaluation-roster", type=Path, required=True)
    compile_cmd.add_argument("--output", type=Path, required=True)
    compile_cmd.add_argument("--data-root", type=Path, required=True)
    compile_cmd.add_argument("--protocol", type=Path, required=True)
    compile_cmd.add_argument("--knowledge-link", type=Path,
                             help="JSON data-root pin to a fully generated and released construction link")
    args = parser.parse_args(argv)
    archive = SystemSearchArchive(args.archive)
    if args.command == "import-seed":
        bundle = SystemTextPolicyBundle.from_json(read(args.bundle))
        print(json.dumps({"bundle_id": archive.store_policy(bundle)}))
    elif args.command == "feedback":
        value = read_family(args.family)
        write_new(args.output, value.as_json())
        print(json.dumps({"feedback_sha256": content_hash(value.as_json()), "contacts_added": 0}))
    elif args.command == "proposal-input":
        require(not (args.branch == "B" and (args.family or args.learning_member or args.complementary_id)),
                "blind input cannot open feedback sources")
        protocol = read(args.protocol)
        require(protocol["proposer_exact_version"] == args.model_version,
                "pin the actual proposer version in the protocol before exporting model input")
        require(protocol.get("seed_bundle", {}).get("bundle_id") == args.seed_id,
                "proposal seed differs from the registered starting system")
        feedback = read_family(args.family) if args.family else None
        if feedback is not None:
            require_stage_feedback(protocol, "initial" if args.round == 1 else f"update-{args.round - 1}", feedback)
            feedback = feedback.learning_view(args.learning_member)
        packet = proposal_input(branch=args.branch, round_index=args.round, slot=args.slot,
            seed=archive.load_policy(args.seed_id), parent=archive.load_policy(args.parent_id),
            model_version=args.model_version, session_id=args.session_id,
            input_token_cap=protocol["proposal_input_token_cap"], output_token_cap=protocol["proposal_output_token_cap"],
            feedback=feedback, complementary=[archive.load_policy(b) for b in args.complementary_id])
        if args.branch == "L":
            packet["learning_history"] = archive.learning_history(before_round=args.round)
        packet["protocol_sha256"] = content_hash(protocol)
        packet["input_sha256"] = content_hash({k: v for k, v in packet.items() if k != "input_sha256"})
        archive.store_input(packet)
        print(json.dumps({"input_sha256": packet["input_sha256"], "invoked": False}))
    elif args.command == "import-response":
        print(json.dumps(archive.import_response(branch=args.branch, round_index=args.round,
            slot=args.slot, receipt=read(args.receipt))))
    elif args.command == "proposal-capsule":
        from speech_aware_evidence_acquisition.rails.system_proposer_capsule import ProposerCapsule
        require(not (args.branch == "B" and (args.family or args.learning_member)),
                "blind capsule cannot open feedback sources")
        key = f"{args.branch}-{args.round}-{args.slot}"
        packet = read(args.archive / "inputs" / (key + ".json"))
        protocol = read(args.protocol)
        require(packet["protocol_sha256"] == content_hash(protocol)
                and protocol["proposer_exact_version"] == packet["model_version"], "proposal protocol/model changed")
        require(protocol.get("seed_bundle", {}).get("bundle_id") == packet["seed_bundle_id"],
                "capsule seed differs from the registered starting system")
        if args.branch == "L":
            require(args.family and args.learning_member, "revalidate the complete family before packaging feedback")
            feedback = read_family(args.family)
            require_stage_feedback(protocol, "initial" if args.round == 1 else f"update-{args.round - 1}", feedback)
            require(feedback.learning_view(args.learning_member).as_json() == packet["feedback"],
                    "feedback differs from the preregistered proposal input")
        require(not (args.archive / "capsules" / (key + ".json")).exists(), "capsule already exists")
        capsule = ProposerCapsule.from_packet(packet, roots={"data": args.data_root, "archive": args.archive},
            cache_root=args.archive / "capsule-material" / args.branch / key)
        document = capsule.as_json()
        archive._write(f"capsules/{key}.json", document)
        print(json.dumps({"capsule_sha256": content_hash(document), "artifacts": len(document["artifacts"]),
                          "invoked": False, "transport_admission": "separate-required"}))
    elif args.command == "compile-candidate":
        key = f"{args.branch}-{args.round}-{args.slot}"
        result = read(args.archive / "imports" / (key + ".json"))
        require(result["status"] in {"provisional", "no-change", "duplicate"}, "invalid import cannot activate")
        record = read(args.archive / "proposals" / (key + ".json"))
        packet = read(args.archive / "inputs" / (key + ".json"))
        protocol = read(args.protocol)
        require(packet["protocol_sha256"] == content_hash(protocol), "proposal protocol changed")
        require(packet["input_sha256"] == content_hash({k: v for k, v in packet.items() if k != "input_sha256"})
                and record["receipt"]["input_sha256"] == packet["input_sha256"], "proposal input changed")
        proposal = TextPolicyUpdateProposal.from_json(record["proposal"])
        parents = [archive.load_policy(b) for b in proposal.as_json()["parent_ids"]]
        sources = proposal_sources(packet, record)
        knowledge, construction_pin = None, None
        if args.knowledge_link:
            require(bool({"construction_instruction", "slot_value_edits"}.intersection(proposal.as_json()["changes"])),
                    "a knowledge replacement must be proposed, not added during compilation")
            from speech_aware_evidence_acquisition.rails.system_text_policy import _read_pin
            construction_pin = read(args.knowledge_link)
            link = json.loads(_read_pin(construction_pin, args.data_root))
            knowledge = link["knowledge"]
            contract = json.loads(_read_pin(link["edit_contract"], args.data_root))
            from speech_aware_evidence_acquisition.rails.system_text_construction import verify_released_slot_construction
            generated = verify_released_slot_construction(link,
                instruction=proposal.as_json()["changes"].get("construction_instruction", parents[0].as_json()["construction_instruction"]),
                data_root=args.data_root, repo_root=args.repo_root)
            if "slot_value_edits" in proposal.as_json()["changes"]:
                require(generated["generated_proposal"] == proposal.as_json()["changes"]["slot_value_edits"],
                        "construction output differs from the proposed exact slot edits")
            sources.append({"kind": "construction", "sha256": construction_pin["sha256"],
                "sample_ids": sorted({sid for ids in contract["evidence_groups"].values() for sid in ids})})
        bundle = apply_text_proposal(proposal, parents=parents, added_sources=sources,
                                     knowledge=knowledge, construction_receipt=construction_pin)
        roster = read(args.evaluation_roster)
        require([r["sample_id"] for r in roster["items"]] == stage_for(protocol, f"update-{args.round}")["sample_ids"],
                "candidate evaluation roster differs from its registered round")
        assert_roster_disjoint(bundle.as_json()["cumulative_sources"], [r["sample_id"] for r in roster["items"]])
        compiled = compile_system_text_policy(read(args.seed_config), bundle, repo_root=args.repo_root,
                                              output_root=args.staging_root, data_root=args.data_root)
        # A new candidate always needs its own prepared supply and admission.
        compiled.pop("prepared_phase_supply", None)
        write_new(args.output, compiled)
        archive.store_policy(bundle)
        print(json.dumps({"bundle_id": bundle.bundle_id, "runtime_admission": "pending", "contacts_added": 0}))


if __name__ == "__main__":
    main()
