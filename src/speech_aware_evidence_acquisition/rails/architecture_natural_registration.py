"""Bind one manual natural four-row plan pair; grant neither contacts nor READ."""
from copy import deepcopy
from dataclasses import asdict, replace
import json
from pathlib import Path

from ..contracts import ExecutionPlan
from ..core.config import _canonical_hash, compose, drop_null_arms, protocol_hash
from ..core.flight.campaign import load_campaign_cells
from ..data.splits import prefixed, split_identity_hash
from .controllers import default_phase_program
from .experiment_population import ARCHITECTURE_VERSION, load_population_config, require_population_binding
from .hashing import content_hash
from .native_episode_config import load_native_episode_config
from .system_context_structural_entry import qualify_architecture_capacity_family, qualify_architecture_capacity_recovery
from .system_text_policy import _read_pin, require

RECOVERED_CAPACITY_PREREQUISITE = "saea-architecture-recovered-capacity-prerequisite-v1"


def _recovery_record(pin, root, *, expected_path=None):
    """Read an absolute operational pin only within the declared data root."""
    require(isinstance(pin, dict) and set(pin) == {"path", "sha256"}, "exact recovery record pin required")
    path = Path(pin["path"])
    require(path.is_absolute() and path.resolve().is_relative_to(root), "recovery evidence escapes its data root")
    path = path.resolve()
    require(expected_path is None or path == expected_path, "recovery record differs from its bound entry")
    return json.loads(_read_pin({"relpath": path.relative_to(root).as_posix(), "sha256": pin["sha256"]}, root))


def _verify_recovery_envelope(envelope, root, labels, receipt_labels):
    """Check persisted records against the raw-pinned envelope, without rewriting it."""
    registration = envelope["registration"]
    entry = Path(registration["new_receipt_root"]).resolve()
    require(entry.is_relative_to(root)
            and [m["label"] for m in registration["members"]] == labels
            and set(envelope["pins"]) == {"registration", "finished", "windows_exit"}
            and set(envelope["member_terminals"]) == set(labels)
            and set(envelope["receipts"]) == set(receipt_labels), "recovery envelope coverage or entry differs")
    for key, name in (("registration", "registration-v1.json"), ("finished", "capacity-finished.json"),
                      ("windows_exit", "capacity-task-exit.json")):
        actual = _recovery_record(envelope["pins"][key], root, expected_path=entry / name)
        require(content_hash(actual) == content_hash(envelope[key]), "recovery envelope differs from its original record")
    require(content_hash(registration) == content_hash(envelope["original_registration"]),
            "recovery registration differs from the independently pinned original")
    source_pin, = registration["frozen_preflight_receipts"]
    require(Path(source_pin["path"]).resolve().is_relative_to(entry), "recovery source check escapes its entry")
    source = _recovery_record(source_pin, root)
    require(content_hash(source) == content_hash(envelope["source_check"]) == registration["source_check_sha256"]
            and source["passed"] is True and source["commit"] == source["source_commit"] == registration["worker_commit"],
            "recovery source check differs from its worker or original bytes")
    # The envelope's raw pin commits to each nested record. Compare the actual
    # persisted contents as well; a synthetic successful envelope cannot replace them.
    for field, names in (("member_terminals", {label: label + "-capacity-finished.json" for label in labels}),
                         ("receipts", {label: label + "/request-fit-v1.json" for label in receipt_labels})):
        for label, name in names.items():
            path = (entry / name).resolve()
            require(path.is_relative_to(entry), "recovery member record escapes its entry")
            require(content_hash(json.loads(path.read_bytes())) == content_hash(envelope[field][label]),
                    "recovery member evidence differs from its persisted record")
    return registration


def _qualified_recovered_capacity(population, pin, prerequisite, member_id, *, repo_root, data_root):
    """Recompute the explicit recovery qualifier; retain both actual source exits."""
    keys = {"original_evidence", "recovery_evidence", "root_disposition", "source_compatibility", "failed_contacts", "qualification"}
    require(data_root is not None and isinstance(prerequisite, dict)
            and set(prerequisite) == keys | {"schema"}
            and prerequisite["schema"] == RECOVERED_CAPACITY_PREREQUISITE, "exact recovered capacity prerequisite required")
    root = Path(data_root).resolve()
    raw = {key: _read_pin(prerequisite[key], root) for key in keys}
    pins = {key: {"path": str((root / prerequisite[key]["relpath"]).resolve()),
                  "sha256": prerequisite[key]["sha256"]} for key in keys}
    original, recovery = json.loads(raw["original_evidence"]), json.loads(raw["recovery_evidence"])
    labels = [m["member_id"] for m in population["architecture"]["members"]]
    old = _verify_recovery_envelope(original, root, labels, labels[:-1])
    new = _verify_recovery_envelope(recovery, root, labels[-1:], labels[-1:])
    qualification = json.loads(raw["qualification"])
    require(Path(pins["qualification"]["path"]) == Path(new["new_receipt_root"]).resolve() / "capacity-qualified-v1.json"
            and qualification["schema"] == "saea-simple-consumption-capacity-recovery-root-qualification-v1"
            and qualification["runtime_admission"] is False and qualification["read_authorized"] is False,
            "completed recovered capacity qualification required")
    graphs, policies = {}, {}
    for source, registration in (("original", old), ("recovery", new)):
        graphs[source] = {}
        for member in registration["members"]:
            graph, = load_campaign_cells(repo_root, member["graph"])
            g = graph.document
            config = compose(repo_root, g["model_fragment"], g["dataset_fragment"], g["baseline_fragment"], member["graph"])
            policy_bytes = _read_pin(member["execution_config"], repo_root)
            policy = drop_null_arms(json.loads(policy_bytes))
            require(config.config_hash == member["graph_config_hash"]
                    and config.values["populations"][0]["ids"] == member["graph_sample_ids"]
                    and all(config.values.get(k) == v for k, v in policy.items() if k != "what_this_is"),
                    "recovered capacity member graph or policy differs from its independently composed source")
            graphs[source][member["label"]] = config.config_hash
            policies[member["label"]] = policy_bytes
    result = qualify_architecture_capacity_recovery(
        population, pin, raw["original_evidence"], recovery, original_evidence_pin=pins["original_evidence"],
        root_disposition_bytes=raw["root_disposition"], root_disposition_pin=pins["root_disposition"],
        source_compatibility_bytes=raw["source_compatibility"], source_compatibility_pin=pins["source_compatibility"],
        failed_contacts_bytes=raw["failed_contacts"], failed_contacts_pin=pins["failed_contacts"],
        policy_config_bytes=policies, graph_config_hashes=graphs, output_reserve=512, structural_reserve=2048, slot_tokens=24576)
    require(content_hash(qualification["result"]) == content_hash(result),
            "recovered capacity qualification differs from its original evidence")
    selected, = [m for m in result["members"] if m["label"] == member_id]
    return (old if selected["source"] == "original" else new), result


def _qualified_capacity(population, pin, prerequisite, *, repo_root, data_root):
    """Recompute the existing qualifier from its pinned original evidence."""
    require(data_root is not None and isinstance(prerequisite, dict)
            and set(prerequisite) == {"registration", "qualification"}, "exact capacity prerequisite required")
    root = Path(data_root).resolve()
    registration = json.loads(_read_pin(prerequisite["registration"], root))
    qualification = json.loads(_read_pin(prerequisite["qualification"], root))
    entry = Path(registration["new_receipt_root"]).resolve()
    require(entry.is_relative_to(root)
            and (root / prerequisite["registration"]["relpath"]).resolve() == entry / "registration-v1.json"
            and (root / prerequisite["qualification"]["relpath"]).resolve() == entry / "capacity-qualified-v1.json",
            "capacity prerequisite differs from its original entry")
    require(qualification["schema"] == "saea-simple-consumption-capacity-root-qualification-v1"
            and qualification["runtime_admission"] is False, "completed capacity qualification required")
    evidence = {}
    for item in qualification["evidence"]:
        path = Path(item["path"]).resolve()
        require(path.is_relative_to(root) and path not in evidence, "capacity evidence escapes or repeats")
        evidence[path] = json.loads(_read_pin(
            {"relpath": path.relative_to(root).as_posix(), "sha256": item["sha256"]}, root))
    require(content_hash(evidence[entry / "registration-v1.json"]) == content_hash(registration),
            "qualification registration differs from the independently pinned original")
    source_pin, = registration["frozen_preflight_receipts"]
    source = json.loads(_read_pin({"relpath": Path(source_pin["path"]).resolve().relative_to(root).as_posix(),
                                  "sha256": source_pin["sha256"]}, root))
    require(content_hash(source) == content_hash(evidence[Path(source_pin["path"]).resolve()]) and source["passed"] is True
            and source["commit"] == source["source_commit"] == registration["worker_commit"],
            "capacity source check is not bound to the original worker")
    members = registration["members"]
    graph_hashes = {}
    for member in members:
        graph, = load_campaign_cells(repo_root, member["graph"])
        g = graph.document
        config = compose(repo_root, g["model_fragment"], g["dataset_fragment"], g["baseline_fragment"], member["graph"])
        require(config.config_hash == member["graph_config_hash"]
                and config.values["populations"][0]["ids"] == member["graph_sample_ids"],
                "capacity member graph differs from its independently composed source")
        graph_hashes[member["label"]] = config.config_hash
    result = qualify_architecture_capacity_family(
        population, pin, registration, evidence[entry / "capacity-finished.json"],
        evidence[entry / "capacity-task-exit.json"],
        {m["label"]: evidence[entry / m["label"] / "request-fit-v1.json"] for m in members},
        original_registration=evidence[entry / "registration-v1.json"],
        member_terminals={m["label"]: evidence[entry / (m["label"] + "-capacity-finished.json")] for m in members},
        policy_config_bytes={m["label"]: _read_pin(m["execution_config"], repo_root) for m in members},
        source_check=source, output_reserve=512, structural_reserve=2048, slot_tokens=24576,
        graph_config_hashes=graph_hashes)
    require(content_hash(qualification["result"]) == content_hash(result),
            "capacity qualification differs from its original evidence")
    return registration, result


def require_architecture_natural_registration(values, cell, registered_plans, *, repo_root, data_root=None):
    """Validate exactly one generation/FIT pair for the qualified four-row roster.

    Both ordinary registered plan schemas add architecture_proof='natural-four-row-v1',
    plan_role ('generation' or 'fit'), member/cohort/sample_ids, policy/supply pins,
    zero official_score_jobs, false scientific_feedback/learner_export, and identical
    capacity_prerequisite {registration, qualification} DATA-relative SHA256 pins.
    The latter points to the existing original capacity entry and root qualification;
    its actual result/evidence/source_commit keys are verified, not reinterpreted.
    The explicit recovered-capacity prerequisite instead pins original_evidence,
    recovery_evidence, root_disposition, source_compatibility, failed_contacts and
    qualification under RECOVERED_CAPACITY_PREREQUISITE. Both envelopes retain
    actual registration/source/terminal/receipt records and independent absolute
    pins for registration, finished and windows_exit. The root qualification uses
    saea-simple-consumption-capacity-recovery-root-qualification-v1 and the exact
    shared recovery result, with runtime_admission and read_authorized both false.
    Historical and nongenerative capacity admission are separate and unchanged.
    """
    from ..analysis.native_graph_rehearsal import rehearsal_profile
    from ..core.preparation_fit import validate_native_contact_fit_config

    require(isinstance(registered_plans, list) and len(registered_plans) == 2
            and all(isinstance(p, dict) for p in registered_plans)
            and {p.get("plan_role") for p in registered_plans} == {"generation", "fit"},
            "natural proof requires exactly one generation and one FIT plan")
    plans = {p["plan_role"]: p for p in registered_plans}
    require(cell.get("allowed_execution_stages") == ["check", "prepare-supply", "worker"],
            "natural proof permits only check/prepare-supply/worker")
    require(not any(k in values for k in ("system_context_learning", "system_search_learning", "system_optimization"))
            and values.get("stage3_algorithm", {}).get("id") == "none"
            and values["stage3_algorithm"].get("operators_used") == []
            and values.get("stage3_measurement", {}).get("claims_benefit") is False,
            "natural proof cannot admit learning or scientific feedback")
    pin = values["experiment_population"]
    population = load_population_config(pin, repo_root=repo_root, allow_architecture=True)
    require(population["schema"] == ARCHITECTURE_VERSION, "natural proof requires explicit V4 architecture")
    identity, = [m for m in population["architecture"]["members"]
                if m["member_id"] == values["architecture_member"] and m["cohort_id"] == values["population_cohort"]]
    cohort = require_population_binding(population, pin, identity["cohort_id"], values, *registered_plans)
    require(plans["generation"]["capacity_prerequisite"] == plans["fit"]["capacity_prerequisite"],
            "natural plan pair has different capacity prerequisites")
    prerequisite = plans["generation"]["capacity_prerequisite"]
    recovered = isinstance(prerequisite, dict) and prerequisite.get("schema") == RECOVERED_CAPACITY_PREREQUISITE
    if recovered:
        capacity, qualified = _qualified_recovered_capacity(population, pin, prerequisite, identity["member_id"],
                                                            repo_root=repo_root, data_root=data_root)
    else:
        capacity, qualified = _qualified_capacity(population, pin, prerequisite, repo_root=repo_root, data_root=data_root)
    member, = [m for m in capacity["members"] if m["member_id"] == identity["member_id"]]
    graph, = load_campaign_cells(repo_root, member["graph"])
    g = graph.document
    graph_config = compose(repo_root, g["model_fragment"], g["dataset_fragment"], g["baseline_fragment"], member["graph"])
    roster = values["populations"][0]["ids"]
    require(len(values["populations"]) == 1 and type(values["population"]["count"]) is int
            and values["population"]["count"] == len(roster) == 4 and len(set(roster)) == 4
            and set(roster) <= set(cohort["sample_ids"])
            and roster == member["graph_sample_ids"] == graph_config.values["populations"][0]["ids"]
            and graph_config.config_hash == member["graph_config_hash"], "natural four-row graph binding differs")
    policy = drop_null_arms(json.loads(_read_pin(identity["execution_config"], repo_root)))
    require(all(values.get(k) == v for k, v in policy.items() if k != "what_this_is"),
            "natural effective policy differs from its pinned member")
    program = default_phase_program(values["policy"])
    native = load_native_episode_config(values, program)
    require(native is not None and native.max_contacts == identity["model_per_trajectory"]
            and [r for r in population["nodes"] if native.role(r).max_iterations > 0] == identity["active_roles"],
            "natural role/contact identity differs")
    require(values["native_graph_capacity_profile"] == member["rehearsal_profile"], "natural profile differs")
    rehearsal_profile(values, member["rehearsal_profile"])
    require(all(values.get("decoding_params", {}).get(k) == v for k, v in population["sampling"].items())
            and all(values["system_search_measurement"].get(k) == v for k, v in population["execution"].items())
            and values["serving_slots"] == population["execution"]["slot_count"]
            and values["serving_slot_tokens"] == 24576, "natural sampling/execution geometry differs")
    fit = validate_native_contact_fit_config(values, program)
    generation_cap = 4 * native.max_contacts
    fit_cap = generation_cap * population["contact_limits"]["fit_endpoints_per_model_contact"]
    require(fit is not None and fit.get("max_speech_packets", 1) == 1 and type(fit["contact_cap"]) is int
            and fit["contact_cap"] == fit_cap and fit["run_id"] != cell["run_id"]
            and fit["attempt_id"] != cell["attempt_id"], "natural FIT identity or ceiling differs")
    expected_budget = dict(complete_system_trajectories=4, generation_calls_cap=generation_cap,
                           actual_request_fit_endpoint_cap=fit_cap, official_complete_scoring_jobs=0)
    require(content_hash(values["family_budget"]) == content_hash(expected_budget), "natural family budget differs")
    config_hash = _canonical_hash(values)
    split = split_identity_hash(prefixed("slurp", roster))
    require(values["population"]["split_identity_hash"] == split, "natural split identity differs")
    expected = ExecutionPlan(**values["execution_plan"], run_id=cell["run_id"], attempt_id=cell["attempt_id"],
                            carrier_lock_key="slurp", split_identity_hash=split,
                            protocol_hash=protocol_hash(config_hash, values["arm"], split)).validate()
    require(expected.planned_model_calls == generation_cap and type(expected.planned_model_calls) is int
            and expected.execution_profile == "bounded-discovery-probe" and expected.split_role == "discovery",
            "natural generation plan differs")
    for role, document in plans.items():
        bound_plan = expected if role == "generation" else replace(expected, run_id=fit["run_id"],
                                                                  attempt_id=fit["attempt_id"], planned_model_calls=fit_cap)
        require(document.get("schema") == f"saea-registered-{role}-plan-v1"
                and document.get("architecture_proof") == "natural-four-row-v1"
                and str(document.get("status", "")).upper().startswith("ROOT COUNTERSIGNED BEFORE CONTACT")
                and document.get("architecture_member") == identity["member_id"]
                and document.get("cell") == cell["cell_id"] and document.get("experiment") == cell["cell_id"]
                and document.get("composed_config_hash") == config_hash and document.get("sample_ids") == roster
                and document.get("policy_binding") == cell["system_text_policy_binding"]
                and cell["system_text_policy_binding"]["bundle_id"] == identity["base_bundle_id"]
                and document.get("prepared_phase_supply") == values["prepared_phase_supply"]
                and document.get("run_id", bound_plan.run_id) == bound_plan.run_id
                and document.get("attempt_id", bound_plan.attempt_id) == bound_plan.attempt_id
                and content_hash(document["execution_plan"]) == content_hash(asdict(bound_plan))
                and type(document.get("official_score_jobs")) is int and document["official_score_jobs"] == 0
                and document.get("scientific_feedback") is False and document.get("learner_export") is False,
                "natural registered plan differs from its exact configuration, scope or identity")
    result = dict(member_id=identity["member_id"], sample_ids=deepcopy(roster), generation_cap=generation_cap,
                  fit_cap=fit_cap, capacity_registration_sha256=content_hash(capacity) if recovered else qualified["registration_sha256"],
                  capacity_source_commit=capacity["worker_commit"], runtime_admission=False, read_authorized=False)
    if recovered:
        member, = [m for m in qualified["members"] if m["label"] == identity["member_id"]]
        result.update(capacity_source=member["source"], capacity_recovery_sha256=content_hash(qualified),
                      capacity_source_exits=[s["exit_code"] for s in qualified["sources"]],
                      failed_attempt_tokenizer_endpoints=qualified["failed_attempt_tokenizer_endpoints"])
    return result
