#!/usr/bin/env python3
"""Offline lifecycle commands for the shared whole-system text-policy search.

No command starts a server, dispatches a flight, invokes a proposer or scores.
Each scientific source read still requires its registered complete-family gate.
"""
import argparse
import importlib.util
import json
import sys
from functools import lru_cache
from pathlib import Path

from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_proposer_capsule import VIEW_PROFILES
from speech_aware_evidence_acquisition.rails.system_search_archive import SystemSearchArchive, proposal_input, proposal_sources
from speech_aware_evidence_acquisition.rails.system_text_feedback import CompleteSystemFeedback
from speech_aware_evidence_acquisition.rails.system_search_protocol import stage_for, require_stage_feedback
from speech_aware_evidence_acquisition.rails.system_search_stage import recipe_family_identity
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    SystemTextPolicyBundle, apply_text_proposal,
    compile_system_text_policy, TextPolicyUpdateProposal, require,
    canonical, _read_pin,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_new(path, document):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(document, sort_keys=True, ensure_ascii=True, indent=2) + "\n")


@lru_cache(maxsize=1)
def registration_gate():
    """Reuse the same ledger and countersignature predicates as Stage-3 reads."""
    path = Path(__file__).resolve().parent / "checks/flight_registration_check.py"
    spec = importlib.util.spec_from_file_location("_saea_system_text_read_registration", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def require_read_registration(spec, *, repo_root, expected_split_role="discovery"):
    """Refuse before any score/reference read; never countersign on the caller's behalf."""
    require(expected_split_role in {"discovery", "dev"}, "unsupported READ scope")
    require(expected_split_role != "dev" or spec["family_id"] == "dev", "DEV READ scope needs the endpoint family")
    pin = spec["read_registration"]
    recipe = json.loads(_read_pin(pin, repo_root))
    gate = registration_gate()
    run_id = gate.read_run_id_of(recipe)
    require(run_id, "analysis recipe must declare its exact READ run ID")
    family, members = recipe_family_identity(recipe)
    require(isinstance(members, dict) and members and members == spec["expected_members"],
            "READ recipe differs from the complete registered family")
    if "initial_members" in recipe:
        require(spec["family_id"] == "initial" and recipe["initial_members"] == members,
                "initial READ cannot authorize another stage")
    else:
        require(family == spec["family_id"], "READ recipe family identity differs")
    require(recipe.get("run_ids", {}).get("read", run_id) == run_id, "READ identifiers disagree")
    rows = gate.parse_ledger(Path(repo_root), gate.EXPOSURE_LEDGER).get(run_id, [])
    require(len(rows) == 1, "READ registration is missing or duplicated")
    row = rows[0]
    require(gate.is_countersigned(row) and not gate.PENDING.search(gate.row_text(row)),
            "READ row is not unambiguously root countersigned")
    require(row.get("execution profile") == "model-free-check" and row.get("split role") == expected_split_role
            and row.get("calls") == "0", "READ registration scope differs")
    require(row.get(gate.ARTIFACTS_COLUMN, "").strip("`") == pin["relpath"],
            "READ registration names another analysis recipe")
    authority = {"read_run_id": run_id, "recipe": pin, "ledger_row_sha256": content_hash(row)}
    if "system_search_stage" in recipe:
        from speech_aware_evidence_acquisition.rails.system_search_stage import validate_stage_registration
        registration = validate_stage_registration(recipe["system_search_stage"])
        require(registration["stage"] == spec["family_id"] and registration["expected_members"] == members
                and recipe.get("system_search_evaluation") == registration["evaluation"],
                "READ recipe differs from the prospective frozen stage")
        authority["stage_registration"] = registration
    return authority


def read_family(path, *, repo_root=None, _seen=()):
    """Reverify saved sources instead of treating a cached feedback JSON as authority."""
    path = Path(path).resolve()
    require(path not in _seen and len(_seen) < 4, "cyclic feedback reference")
    spec = read(path)
    require(set(spec) == {"family_id", "expected_members", "bindings", "initial_reference_member", "reference_family",
                         "read_registration"},
            "family specification fields differ")
    repo_root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[1]
    authority = require_read_registration(spec, repo_root=repo_root)
    reference = (read_family(spec["reference_family"], repo_root=repo_root, _seen=(*_seen, path))
                 if spec["reference_family"] is not None else None)
    feedback = CompleteSystemFeedback.from_family(spec["bindings"], expected_members=spec["expected_members"],
        family_id=spec["family_id"], initial_reference_member=spec["initial_reference_member"], reference=reference)
    require(require_read_registration(spec, repo_root=repo_root) == authority, "READ authority changed during export")
    return CompleteSystemFeedback(canonical({**feedback.as_json(), "read_authority": authority}))


def read_pilot_learning(protocol, *, round_index, family_path, repo_root, archive,
                        parent_id, complementary_ids):
    """Reverify the full registered family, then expose only its L projection."""
    from speech_aware_evidence_acquisition.analysis.system_text_pilot import read_pilot_evidence
    from speech_aware_evidence_acquisition.rails.system_text_feedback import _absolute_json
    from speech_aware_evidence_acquisition.rails.system_optimization import (
        PILOT, exploratory_selection, load_optimization_panel,
    )
    if round_index != 3:
        from speech_aware_evidence_acquisition.rails.system_search_allocations import validate_extension
        extension = archive.allocation_extension(round_index)
        require(extension is not None and extension == protocol.get("allocation_extension"),
                "exploratory learning requires the registered extra round")
        validate_extension(archive, extension, repo_root=repo_root)
    pin = protocol["exploratory_learning"]
    binding = json.loads(_read_pin(pin, repo_root))
    require(set(binding) == {"schema", "family", "analysis_supplement", "owner_learning",
            "reference_family", "next_round", "parent_id", "complementary_ids",
            "optimization_plan", "expected_projection_sha256"}
            and binding["schema"] == "saea-exploratory-learning-binding-v1"
            and type(round_index) is int and round_index == binding["next_round"]
            and parent_id == binding["parent_id"]
            and list(complementary_ids) == binding["complementary_ids"],
            "exploratory parent, allocation or binding differs")
    panel = load_optimization_panel(protocol, f"update-{round_index}", repo_root=repo_root)
    require(panel is not None and binding["optimization_plan"] == protocol["optimization_panel"]["plan"],
            "exploratory learning needs the exact fixed optimization panel")
    require(Path(family_path).resolve() == Path(binding["family"]["path"]).resolve(),
            "exploratory family path differs")
    spec = _absolute_json(binding["family"])
    # Check the reference pin before opening either family's scientific results.
    _absolute_json(binding["reference_family"])
    recipe = json.loads(_read_pin(spec["read_registration"], repo_root))
    supplement = json.loads(_read_pin(binding["analysis_supplement"], repo_root))
    is_panel = "system_panel_registration" in recipe
    expected_schema = "saea-system-panel-analysis-supplement-v1" if is_panel else "saea-pilot-analysis-supplement-v1"
    require(supplement.get("schema") == expected_schema
            and supplement.get("recipe") == spec["read_registration"], "exploratory supplement differs")
    require(is_panel or spec["family_id"] == PILOT, "exploratory family differs")
    owner = json.loads(_read_pin(supplement["owner_decision"], repo_root))
    amendment = json.loads(_read_pin(binding["owner_learning"], repo_root))
    registration_pin = recipe["system_panel_registration" if is_panel else "pilot_registration"]
    registration = json.loads(_read_pin(registration_pin, repo_root))
    kwargs = {}
    reader = read_pilot_evidence
    if is_panel:
        from speech_aware_evidence_acquisition.analysis import system_text_panel as measured_panel
        kwargs = measured_panel.load_scope(registration, owner, supplement, repo_root=repo_root, recipe=recipe)
        expected_learning = supplement["learning_owner_decision"] if "evaluation" in kwargs else supplement["growth_owner_decision"]
        require(binding["owner_learning"] == expected_learning
                and round_index > registration["proposal_round"]
                and kwargs["pool_ids"] == panel[1],
                "panel feedback needs its own approved allowance and the same pool in a later round")
        reader = measured_panel.read_evidence
    authority = require_read_registration(spec, repo_root=repo_root)
    evidence = reader(spec["bindings"], recipe=recipe, registration=registration,
        owner=owner, authority=authority, **kwargs)
    reference = read_family(binding["reference_family"]["path"], repo_root=repo_root)
    projected = evidence.learning_projection(amendment=amendment, reference=reference)
    require(content_hash(projected.as_json()) == binding["expected_projection_sha256"],
            "pilot learning projection differs from its pinned source")
    require(require_read_registration(spec, repo_root=repo_root) == authority,
            "pilot READ authority changed during export")
    require(json.loads(_read_pin(pin, repo_root)) == binding
            and _absolute_json(binding["family"]) == spec,
            "pilot binding changed during export")
    if is_panel:
        for source in (spec["read_registration"], binding["analysis_supplement"],
                       supplement["owner_decision"], binding["owner_learning"], registration_pin):
            _read_pin(source, repo_root)
        require(measured_panel.load_scope(registration, owner, supplement, repo_root=repo_root, recipe=recipe) == kwargs
                and load_optimization_panel(protocol, f"update-{round_index}", repo_root=repo_root) == panel,
                "fixed panel scope changed during export")
        _absolute_json(binding["reference_family"])
    document = projected.as_json()
    if not is_panel:
        document["interpretation"] = (
            "Exploratory twenty-input full-system learning feedback under owner222/224. "
            "Use all successes, failures, unchanged cases and damaged answers. "
            "Continue on the pinned reused optimization panel; retain cumulative exposure. "
            "Freeze knowledge and supply; revise role/context text only. "
            "No independent-validation claim, formal adoption, node causal credit, "
            "policy gradient or guaranteed improvement.")
    feedback = CompleteSystemFeedback(canonical(document))
    parents = [archive.load_policy(b).as_json() for b in [parent_id, *complementary_ids]]
    selection = exploratory_selection(feedback, registration=registration, binding=binding,
        protocol=protocol, parents=parents)
    return feedback, selection


def require_learning_members(feedback, member_ids):
    expected = {cid for cid in feedback.as_json()["summaries"]
                if cid.startswith("L-") or cid in {"seed", "seed-aa"}}
    require(len(member_ids) == len(set(member_ids)) and set(member_ids) == expected,
            "include every learning-branch member, including the comparator and A/A")


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
    packet.add_argument("--round", type=int, required=True)
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
    response.add_argument("--round", type=int, required=True)
    response.add_argument("--slot", type=int, choices=(1, 2), required=True)
    response.add_argument("--receipt", type=Path, required=True)
    capsule_cmd = commands.add_parser("proposal-capsule", help="Snapshot registered English inputs; no model call")
    capsule_cmd.add_argument("--branch", choices=("L", "B"), required=True)
    capsule_cmd.add_argument("--round", type=int, required=True)
    capsule_cmd.add_argument("--slot", type=int, choices=(1, 2), required=True)
    capsule_cmd.add_argument("--protocol", type=Path, required=True)
    capsule_cmd.add_argument("--data-root", type=Path, required=True)
    capsule_cmd.add_argument("--cache-name", help="New cache directory for an offline packaging correction; never overwrite a prior cache")
    capsule_cmd.add_argument("--capsule-name", help="Create a separately named offline packaging revision; proposal allocation is unchanged")
    capsule_cmd.add_argument("--view-profile", choices=VIEW_PROFILES, default="full-index-v1",
                             help="Opt into source-addressed compact feedback; requires separate transport admission")
    capsule_cmd.add_argument("--family", type=Path)
    capsule_cmd.add_argument("--learning-member", action="append", default=[])
    compile_cmd = commands.add_parser("compile-candidate")
    compile_cmd.add_argument("--branch", choices=("L", "B"), required=True)
    compile_cmd.add_argument("--round", type=int, required=True)
    compile_cmd.add_argument("--slot", type=int, choices=(1, 2), required=True)
    compile_cmd.add_argument("--seed-config", type=Path, required=True)
    compile_cmd.add_argument("--repo-root", type=Path, required=True)
    compile_cmd.add_argument("--staging-root", type=Path, required=True)
    compile_cmd.add_argument("--evaluation-roster", type=Path, required=True)
    compile_cmd.add_argument("--output", type=Path, required=True)
    compile_cmd.add_argument("--data-root", type=Path, required=True)
    compile_cmd.add_argument("--protocol", type=Path, required=True)
    compile_cmd.add_argument("--cohort-binding", type=Path,
                             help="Pinned exact-cohort query, agreement and runtime inputs; required before compilation")
    compile_cmd.add_argument("--knowledge-link", type=Path,
                             help="JSON data-root pin to a fully generated and released construction link")
    scale_cmd = commands.add_parser("bind-scaling-policy", help="Prepare unchanged policy on an exact larger prefix; no dispatch")
    for option in ("compiled", "policy-binding", "protocol", "cohort-binding", "repo-root", "data-root", "output"):
        scale_cmd.add_argument("--" + option, type=Path, required=True)
    scale_cmd.add_argument("--size", type=int, choices=(50, 100, 200), required=True)
    stage_cmd = commands.add_parser("freeze-update", help="Freeze spent slots and membership before contact; no dispatch")
    stage_cmd.add_argument("--protocol", type=Path, required=True)
    stage_cmd.add_argument("--round", type=int, choices=(1, 2, 3), required=True)
    stage_cmd.add_argument("--member-bindings", type=Path, required=True)
    stage_cmd.add_argument("--data-root", type=Path, required=True)
    panel_cmd = commands.add_parser("freeze-panel", help="Freeze a reviewed exact extra-round panel; no dispatch or READ authority")
    panel_cmd.add_argument("--round", type=int, required=True)
    panel_cmd.add_argument("--rows", type=int, choices=(20, 50, 100, 200, 400), required=True)
    for option in ("protocol", "member-bindings", "root-review", "repo-root", "data-root"):
        panel_cmd.add_argument("--" + option, type=Path, required=True)
    successor_cmd = commands.add_parser("freeze-successor-panel", help="Freeze exact six admitted members with all spent custody; no dispatch")
    successor_cmd.add_argument("--round", type=int, required=True)
    successor_cmd.add_argument("--rows", type=int, choices=(20, 50, 100, 200), required=True)
    for option in ("protocol", "member-bindings", "root-review", "repo-root", "data-root", "evaluation-authority"):
        successor_cmd.add_argument("--" + option, type=Path, required=True)
    selection_cmd = commands.add_parser("freeze-selection", help="Bind historical nominees before the common cohort; no dispatch")
    selection_cmd.add_argument("--protocol", type=Path, required=True)
    selection_cmd.add_argument("--update-family", type=Path, action="append", required=True,
                               help="Supply each of the three complete registered update family specifications")
    selection_cmd.add_argument("--member-bindings", type=Path, required=True)
    selection_cmd.add_argument("--data-root", type=Path, required=True)
    selection_cmd.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    retain_cmd = commands.add_parser("retain-feedback", help="Record root-reviewed same-cohort choices; no automatic verdict")
    retain_cmd.add_argument("--stage", choices=("update-1", "update-2", "update-3", "selection"), required=True)
    retain_cmd.add_argument("--branch", choices=("L", "B"), required=True)
    retain_cmd.add_argument("--selected-id", action="append", required=True,
                            help="Quality parent first, then at most one complementary survivor")
    retain_cmd.add_argument("--retain-parent", action="store_true",
                            help="Record root's no-qualified-candidate fallback to the measured parent")
    freeze_cmd = commands.add_parser("freeze-finalists", help="Freeze both common-selection choices before DEV")
    dev_cmd = commands.add_parser("freeze-dev", help="Bind four frozen finalists to the registered DEV cohort; no dispatch")
    dev_cmd.add_argument("--member-bindings", type=Path, required=True)
    dev_cmd.add_argument("--data-root", type=Path, required=True)
    dev_compile = commands.add_parser("compile-dev-member", help="Compile one frozen endpoint system; no proposal or dispatch")
    dev_compile.add_argument("--member", choices=("seed", "seed-aa", "L-frozen", "B-frozen"), required=True)
    for option in ("seed-config", "cohort-binding", "staging-root", "data-root", "output"):
        dev_compile.add_argument("--" + option, type=Path, required=True)
    for command in (retain_cmd, freeze_cmd, dev_cmd, dev_compile):
        command.add_argument("--protocol", type=Path, required=True)
        command.add_argument("--family", type=Path, required=True)
        command.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    for command in (packet, capsule_cmd):
        command.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    archive = SystemSearchArchive(args.archive)
    extension = None
    if hasattr(args, "round"):
        extension = archive.allocation_extension(args.round)
        if extension is not None and hasattr(args, "protocol"):
            from speech_aware_evidence_acquisition.rails.system_search_allocations import validate_extension
            require(read(args.protocol).get("allocation_extension") == extension, "protocol allocation differs")
            validate_extension(archive, extension, repo_root=args.repo_root)
    if args.command == "import-seed":
        document = read(args.bundle)
        parents = [archive.load_policy(identity) for identity in document.get("parent_ids", [])]
        bundle = SystemTextPolicyBundle.from_json(document, parents=parents)
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
        feedback, selection = None, None
        if args.family and protocol.get("exploratory_learning"):
            feedback, selection = read_pilot_learning(protocol, round_index=args.round,
                family_path=args.family, repo_root=args.repo_root, archive=archive,
                parent_id=args.parent_id, complementary_ids=args.complementary_id)
            require_learning_members(feedback, args.learning_member)
        elif args.family:
            feedback = read_family(args.family)
            require_stage_feedback(protocol, "initial" if args.round == 1 else f"update-{args.round - 1}", feedback)
            require_learning_members(feedback, args.learning_member)
            selection = archive.learning_selection(protocol=protocol, round_index=args.round, feedback=feedback,
                parent_id=args.parent_id, complementary_ids=args.complementary_id)
            feedback = feedback.learning_view(args.learning_member)
        packet = proposal_input(branch=args.branch, round_index=args.round, slot=args.slot,
            seed=archive.load_policy(args.seed_id), parent=archive.load_policy(args.parent_id),
            model_version=args.model_version, session_id=args.session_id,
            input_token_cap=protocol["proposal_input_token_cap"], output_token_cap=protocol["proposal_output_token_cap"],
            feedback=feedback, complementary=[archive.load_policy(b) for b in args.complementary_id],
            allocation_extension=extension)
        if args.branch == "L":
            packet["learning_history"] = archive.learning_history(before_round=args.round)
            if selection is not None:
                packet["selection"] = selection
        from speech_aware_evidence_acquisition.rails.system_optimization import load_optimization_panel, optimization_scope_for
        if load_optimization_panel(protocol, f"update-{args.round}", repo_root=args.repo_root) is not None:
            packet["optimization_scope"] = optimization_scope_for(protocol, args.round)
        packet["protocol_sha256"] = content_hash(protocol)
        if "proposal_budget_profile" in protocol:
            packet["budget_profile"] = protocol["proposal_budget_profile"]
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
            complementary = [content_hash(p) for p in packet["complementary_policies"]]
            if protocol.get("exploratory_learning"):
                feedback, selection = read_pilot_learning(protocol, round_index=args.round,
                    family_path=args.family, repo_root=args.repo_root, archive=archive,
                    parent_id=packet["parent_bundle_id"], complementary_ids=complementary)
                require_learning_members(feedback, args.learning_member)
            else:
                feedback = read_family(args.family)
                require_stage_feedback(protocol, "initial" if args.round == 1 else f"update-{args.round - 1}", feedback)
                require_learning_members(feedback, args.learning_member)
                selection = archive.learning_selection(protocol=protocol, round_index=args.round, feedback=feedback,
                    parent_id=packet["parent_bundle_id"], complementary_ids=complementary)
                feedback = feedback.learning_view(args.learning_member)
            require(packet.get("selection") == selection, "selection differs from the preregistered proposal input")
            require(feedback.as_json() == packet["feedback"],
                    "feedback differs from the preregistered proposal input")
        capsule_name = args.capsule_name or key
        require(capsule_name.startswith(key) and all(c.isascii() and (c.isalnum() or c in "-_") for c in capsule_name),
                "invalid capsule name")
        require(not (args.archive / "capsules" / (capsule_name + ".json")).exists(), "capsule already exists")
        cache_name = args.cache_name or key
        require(cache_name.startswith(key) and Path(cache_name).name == cache_name
                and all(c.isascii() and (c.isalnum() or c in "-_") for c in cache_name),
                "invalid capsule cache name")
        capsule = ProposerCapsule.from_packet(packet, roots={"data": args.data_root, "archive": args.archive},
            cache_root=args.archive / "capsule-material" / args.branch / cache_name, view_profile=args.view_profile)
        document = capsule.as_json()
        archive._write(f"capsules/{capsule_name}.json", document)
        print(json.dumps({"capsule_sha256": content_hash(document), "artifacts": len(document["artifacts"]),
                          "invoked": False, "transport_admission": "separate-required"}))
    elif args.command == "compile-candidate":
        require(args.cohort_binding is not None, "candidate compilation requires an exact cohort binding")
        key = f"{args.branch}-{args.round}-{args.slot}"
        require(not (archive.root / f"compilations/{key}.json").exists(), "candidate compilation already exists")
        result = read(args.archive / "imports" / (key + ".json"))
        require(result["status"] in {"provisional", "no-change", "duplicate"}, "invalid import cannot activate")
        record = read(args.archive / "proposals" / (key + ".json"))
        packet = read(args.archive / "inputs" / (key + ".json"))
        protocol = read(args.protocol)
        require(packet["protocol_sha256"] == content_hash(protocol), "proposal protocol changed")
        require(packet["input_sha256"] == content_hash({k: v for k, v in packet.items() if k != "input_sha256"})
                and record["receipt"]["input_sha256"] == packet["input_sha256"], "proposal input changed")
        proposal = TextPolicyUpdateProposal.from_json(record["proposal"], allocation_extension=extension)
        from speech_aware_evidence_acquisition.rails.system_optimization import (
            assert_policy_roster, require_context_only_changes,
        )
        require_context_only_changes(proposal.as_json()["changes"], protocol=protocol,
            stage=f"update-{args.round}", repo_root=args.repo_root)
        parents = [archive.load_policy(b) for b in proposal.as_json()["parent_ids"]]
        sources = proposal_sources(packet, record)
        knowledge, construction_pin = None, None
        if args.knowledge_link:
            require(bool({"construction_instruction", "slot_value_edits"}.intersection(proposal.as_json()["changes"])),
                    "a knowledge replacement must be proposed, not added during compilation")
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
        assert_policy_roster(bundle.as_json()["cumulative_sources"], [r["sample_id"] for r in roster["items"]],
            protocol=protocol, stage=f"update-{args.round}", repo_root=args.repo_root)
        compiled = compile_system_text_policy(read(args.seed_config), bundle, repo_root=args.repo_root,
                                              output_root=args.staging_root, data_root=args.data_root)
        from speech_aware_evidence_acquisition.rails.system_text_cohort import bind_system_text_cohort
        compiled = bind_system_text_cohort(compiled, read(args.cohort_binding), protocol=protocol,
            stage=f"update-{args.round}", repo_root=args.repo_root, data_root=args.data_root)
        # A new candidate always needs its own prepared supply and admission.
        compiled.pop("prepared_phase_supply", None)
        write_new(args.output, compiled)
        archive.store_policy(bundle)
        archive.record_compilation(branch=args.branch, round_index=args.round, slot=args.slot,
                                   bundle=bundle, configuration=compiled)
        print(json.dumps({"bundle_id": bundle.bundle_id, "runtime_admission": "pending", "contacts_added": 0}))
    elif args.command == "bind-scaling-policy":
        from speech_aware_evidence_acquisition.rails.system_text_scaling import bind_scaling_policy
        result = bind_scaling_policy(read(args.compiled), read(args.policy_binding),
            source_protocol=read(args.protocol), cohort_binding=read(args.cohort_binding),
            size=args.size, repo_root=args.repo_root, data_root=args.data_root)
        write_new(args.output, result)
        print(json.dumps({"bundle_id": result["preparation"]["bundle_id"], "rows": args.size,
            "preparation_sha256": content_hash(result["preparation"]),
            "contacts_added": 0, "runtime_admission": "separate-required"}))
    elif args.command == "freeze-update":
        from speech_aware_evidence_acquisition.rails.system_search_stage import freeze_update_stage
        registration = freeze_update_stage(archive, protocol=read(args.protocol), round_index=args.round,
            member_bindings=read(args.member_bindings), data_root=args.data_root)
        print(json.dumps({"registration_sha256": registration["registration_sha256"],
            "members": len(registration["expected_members"]), "trajectory_cap": registration["trajectory_cap"],
            "contacts_added": 0, "runtime_admission": "separate-required"}))
    elif args.command in {"freeze-panel", "freeze-successor-panel"}:
        from speech_aware_evidence_acquisition.rails.system_search_stage import freeze_optimization_panel
        frozen = freeze_optimization_panel(archive, protocol=read(args.protocol), round_index=args.round,
            rows=args.rows, member_bindings=read(args.member_bindings), root_review=read(args.root_review),
            repo_root=args.repo_root, data_root=args.data_root,
            **({"evaluation_authority": read(args.evaluation_authority)} if args.command == "freeze-successor-panel" else {}))
        registration = frozen["registration"]
        print(json.dumps({"registration_sha256": registration["registration_sha256"],
            "members": len(registration["expected_members"]), "trajectory_cap": registration["trajectory_cap"],
            "contacts_added": 0, "runtime_admission": "separate-required"}))
    elif args.command == "freeze-selection":
        from speech_aware_evidence_acquisition.rails.system_selection_stage import freeze_selection_stage
        require(len(args.update_family) == 3, "supply three distinct update families")
        declared = [read(path).get("family_id") for path in args.update_family]
        require(set(declared) == {"update-1", "update-2", "update-3"},
                "supply three distinct update families before reading any results")
        histories = {}
        for path, expected in zip(args.update_family, declared):
            feedback = read_family(path, repo_root=args.repo_root)
            name = feedback.as_json()["family_id"]
            require(name == expected and name not in histories, "update family changed during read")
            histories[name] = feedback
        registration = freeze_selection_stage(archive, protocol=read(args.protocol), update_feedback=histories,
            member_bindings=read(args.member_bindings), data_root=args.data_root)
        print(json.dumps({"registration_sha256": registration["registration_sha256"],
            "members": len(registration["expected_members"]), "trajectory_cap": registration["trajectory_cap"],
            "contacts_added": 0, "runtime_admission": "separate-required"}))
    elif args.command in {"freeze-dev", "compile-dev-member"}:
        from speech_aware_evidence_acquisition.rails.system_dev_stage import freeze_dev_stage, compile_dev_member
        require(read(args.family).get("family_id") == "selection", "DEV freeze requires the common selection family")
        feedback = read_family(args.family, repo_root=args.repo_root)
        if args.command == "compile-dev-member":
            compiled = compile_dev_member(archive, protocol=read(args.protocol), selection_feedback=feedback,
                member=args.member, baseline=read(args.seed_config), cohort_binding=read(args.cohort_binding),
                repo_root=args.repo_root, staging_root=args.staging_root, data_root=args.data_root)
            write_new(args.output, compiled)
            print(json.dumps({"member": args.member, "configuration_sha256": content_hash(compiled),
                "contacts_added": 0, "runtime_admission": "separate-required"}))
            return
        registration = freeze_dev_stage(archive, protocol=read(args.protocol), selection_feedback=feedback,
            member_bindings=read(args.member_bindings), data_root=args.data_root)
        print(json.dumps({"registration_sha256": registration["registration_sha256"],
            "members": len(registration["expected_members"]), "trajectory_cap": registration["trajectory_cap"],
            "contacts_added": 0, "runtime_admission": "separate-required"}))
    elif args.command in {"retain-feedback", "freeze-finalists"}:
        protocol = read(args.protocol)
        feedback = read_family(args.family, repo_root=args.repo_root)
        # The policy/run/config mapping must be part of the exact READ recipe,
        # frozen with the family before contact, never a post-hoc command input.
        recipe = json.loads(_read_pin(feedback.as_json()["read_authority"]["recipe"], args.repo_root))
        require("system_search_evaluation" in recipe, "READ recipe lacks the registered policy evaluation binding")
        if args.command == "retain-feedback":
            record = archive.retain_feedback(protocol=protocol, stage_name=args.stage, feedback=feedback,
                evaluation=recipe["system_search_evaluation"], branch=args.branch,
                selected_ids=args.selected_id, retain_parent=args.retain_parent)
            print(json.dumps({"selection_sha256": record["selection_sha256"], "status": record["status"], "contacts_added": 0}))
        else:
            record = archive.freeze_finalists(protocol=protocol, feedback=feedback)
            print(json.dumps({"freeze_sha256": record["freeze_sha256"], "status": record["status"], "contacts_added": 0}))


if __name__ == "__main__":
    main()
