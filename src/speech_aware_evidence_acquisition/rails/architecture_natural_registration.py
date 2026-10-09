"""Bind one manual natural four-row plan pair; grant neither contacts nor READ."""
from copy import deepcopy
from dataclasses import asdict, replace
import json
import hashlib
from collections import Counter
from pathlib import Path

from ..contracts import ExecutionPlan
from ..core.config import _canonical_hash, compose, drop_null_arms, protocol_hash
from ..core.flight.campaign import load_campaign_cells
from ..data.splits import prefixed, split_identity_hash
from .controllers import default_phase_program
from .experiment_population import ARCHITECTURE_VERSION, load_population_config, population_accounting, require_population_binding
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
    joint_pin = values.get("joint_role_basis")
    if joint_pin is not None:
        require(all(p.get("joint_role_basis") == joint_pin for p in plans.values()),
                "joint natural pair basis differs")
        require_joint_proof_registration(values,cell,list(plans.values()),population,
                repo_root=repo_root,data_root=data_root,stage="natural")
    else:
        require(all(p.get("joint_role_basis") is None for p in plans.values()),
                "unsolicited joint natural basis refused")
    result = dict(member_id=identity["member_id"], sample_ids=deepcopy(roster), generation_cap=generation_cap,
                  fit_cap=fit_cap, capacity_registration_sha256=content_hash(capacity) if recovered else qualified["registration_sha256"],
                  capacity_source_commit=capacity["worker_commit"], runtime_admission=False, read_authorized=False)
    if recovered:
        member, = [m for m in qualified["members"] if m["label"] == identity["member_id"]]
        result.update(capacity_source=member["source"], capacity_recovery_sha256=content_hash(qualified),
                      capacity_source_exits=[s["exit_code"] for s in qualified["sources"]],
                      failed_attempt_tokenizer_endpoints=qualified["failed_attempt_tokenizer_endpoints"])
    return result


FIXED_ROSTER_SELECTOR = "manual-architecture-fixed-roster-v1"


def _fixed400_basis(values, plans, population, *, repo_root):
    """Bind an explicit stable prefix to the approved immutable UPDATE2fixed400."""
    extent = values.get("architecture_extent")
    require(isinstance(extent, dict) and set(extent) == {"schema", "source_population", "runtime_view", "count", "selection_seed"}
            and extent["schema"] == "saea-manual-architecture-fixed-roster-extent-v1"
            and type(extent["count"]) is int and extent["count"] in (100, 400)
            and extent["selection_seed"] == 20261001
            and all(p.get("architecture_extent") == extent
                    and p.get("architecture_proof") == FIXED_ROSTER_SELECTOR for p in plans.values()),
            "fixed400 extent or plan selector differs")
    require(extent["source_population"]["relpath"] == "configs/experiments/slurp-simple-consumption-architecture-n20-v2.json"
            and extent["runtime_view"]["relpath"] == "configs/dataset/slurp-speech-native-system-text-update-2-400-v1.json",
            "fixed400 source identity is not the original configured basis")
    require(extent["runtime_view"]["sha256"] == "1e5cd463fcad7bc6cdcb637de0fcc63ac16cfa6e7b9c1d835207366ac679e31c"
            and extent["source_population"]["sha256"] == "f127f9ed88299e4555631b469b598cae4dc67cf1982fcaed95484b794de7201f",
            "fixed-roster original frozen source raw pin differs")
    basis = load_population_config(extent["source_population"], repo_root=repo_root, allow_architecture=True)
    view = json.loads(_read_pin(extent["runtime_view"], repo_root))
    from ..core.preparation import digest
    ids = [r["sample_id"] for r in view["items"]]
    require(view.get("runtime_view_sha256") == digest({k: v for k, v in view.items() if k != "runtime_view_sha256"})
            and view.get("count") == len(ids) == len(set(ids)) == 400
            and view.get("split_role") == "discovery" and view.get("carrier_lock_key") == "slurp"
            and ids[:20] == basis["cohorts"][0]["sample_ids"]
            and len(basis["cohorts"][0]["sample_ids"]) == 20,
            "fixed400 runtime view seal, extent or original20 prefix differs")
    from ..data.runtime_subset import build_runtime_subset
    _, selected = build_runtime_subset(view, seed=extent["selection_seed"], count=extent["count"], name="extent-verification")
    selected_ids = selected["sample_ids"]
    require(ids[:extent["count"]] == selected_ids, "fixed-roster stable prefix differs")
    expected = deepcopy(basis)
    expected["experiment_id"] = "slurp-simple-consumption-architecture-n" + str(extent["count"]) + "-v1"
    expected["cohorts"][0]["sample_ids"] = selected_ids
    require(content_hash(population) == content_hash(expected),
            "fixed400 population changed policies, roles, controls, geometry or roster")
    return basis, extent["source_population"]


def _fixed400_natural(values, plans, population, *, repo_root, data_root):
    """Reuse original natural proof only after independent historical qualification."""
    basis, pin = _fixed400_basis(values, plans, population, repo_root=repo_root)
    prerequisite = plans["generation"]["natural_prerequisite"]
    admission = json.loads(_read_pin(prerequisite["registration"], Path(data_root).resolve()))
    historical_capacity = admission["capacity_prerequisite"]
    capacity, _ = _qualified_capacity(basis, pin, historical_capacity, repo_root=repo_root, data_root=data_root)
    return _qualified_natural_family(basis, pin, prerequisite, historical_capacity, capacity,
                                    repo_root=repo_root, data_root=data_root, compatibility=plans["generation"].get("natural_source_compatibility"),
                                    decision_pin=plans["generation"].get("decision_receipt"))


def require_architecture_n20_registration(values, cell, registered_plans, *, repo_root, data_root=None):
    """Bind one manual N20 pair to the completed N20 family and root READ.

    This validates preregistration metadata only. Existing runtime, scoring and
    complete-family READ gates retain their independent authority.
    """
    from ..analysis.native_graph_rehearsal import rehearsal_profile
    from ..core.preparation_fit import validate_native_contact_fit_config

    require(isinstance(registered_plans, list) and len(registered_plans) == 2
            and all(isinstance(p, dict) for p in registered_plans)
            and {p.get("plan_role") for p in registered_plans} == {"generation", "fit"},
            "N20 proof requires exactly one generation and one FIT plan")
    plans = {p["plan_role"]: p for p in registered_plans}
    from .local_node_panel import SELECTORS as LOCAL_NODE_SELECTORS, require_local_node_basis
    local = all(p.get("architecture_proof") in LOCAL_NODE_SELECTORS for p in plans.values())
    require(not local or len({p["architecture_proof"] for p in plans.values()}) == 1, "local node selector pair differs")
    fixed400 = values.get("architecture_extent") is not None
    joint = values.get("joint_role_basis") is not None
    require(not joint or (not local and not fixed400
            and all(p.get("architecture_proof") == "manual-architecture-n20-v1"
                    and p.get("natural_source_compatibility") is None
                    and p.get("joint_role_basis") == values["joint_role_basis"] for p in plans.values())),
            "joint imports require their exact generic manual basis and fresh proofs")
    require(joint or all(p.get("joint_role_basis") is None for p in plans.values()),
            "unsolicited joint plan basis refused")
    require(not local or (not fixed400 and all(p.get("natural_source_compatibility") is None for p in plans.values())),
            "local node requires fresh structural proof without historical compatibility")
    require(cell.get("allowed_execution_stages") == ["check", "prepare-supply", "worker", "campaign"],
            "N20 proof permits exactly check/prepare-supply/worker/campaign")
    require(not any(k in values for k in ("system_context_learning", "system_search_learning", "system_optimization"))
            and values.get("stage3_algorithm", {}).get("id") == "none"
            and values["stage3_algorithm"].get("operators_used") == []
            and values.get("stage3_measurement", {}).get("claims_benefit") is False,
            "N20 proof cannot admit learning or benefit claims")
    pin = values["experiment_population"]
    population = load_population_config(pin, repo_root=repo_root, allow_architecture=True)
    require(population["schema"] == ARCHITECTURE_VERSION, "N20 proof requires explicit V4 architecture")
    identity, = [m for m in population["architecture"]["members"]
                if m["member_id"] == values["architecture_member"] and m["cohort_id"] == values["population_cohort"]]
    cohort = require_population_binding(population, pin, identity["cohort_id"], values, *registered_plans)
    joint_basis = (require_joint_role_basis(values["joint_role_basis"], population,
                    repo_root=repo_root, data_root=data_root) if joint else None)
    if joint:
        from .system_text_policy import verify_system_text_binding
        verify_system_text_binding(values, cell["system_text_policy_binding"], repo_root=repo_root, data_root=data_root)
    if local:
        basis = values.get("local_node_basis")
        require(basis is not None and plans["generation"]["architecture_proof"] == "local-" + basis.get("target_role", "") + "-panel-v1", "local node selector and target role differ")
        require(all(p.get("local_node_basis") == basis for p in plans.values()),
                "local node plan basis differs")
        require_local_node_basis(basis, population, repo_root=repo_root, data_root=data_root)
        from .system_text_policy import verify_system_text_binding
        verify_system_text_binding(values, cell["system_text_policy_binding"], repo_root=repo_root, data_root=data_root)
    else:
        require(values.get("local_node_basis") is None, "local node basis requires its named opt-in selector")
    require(plans["generation"]["capacity_prerequisite"] == plans["fit"]["capacity_prerequisite"],
            "N20 plan pair has different capacity prerequisites")
    prerequisite = plans["generation"]["capacity_prerequisite"]
    capacity, qualified = _qualified_capacity(population, pin, prerequisite, repo_root=repo_root, data_root=data_root)
    require(plans["generation"].get("natural_prerequisite") == plans["fit"].get("natural_prerequisite"),
            "N20 pair has different natural prerequisites")
    compatibility = plans["generation"].get("natural_source_compatibility")
    require(compatibility == plans["fit"].get("natural_source_compatibility"), "natural compatibility pair differs")
    if compatibility is not None:
        require(plans["generation"].get("decision_receipt") == plans["fit"].get("decision_receipt"), "natural compatibility decisions differ")
        authority = json.loads(_read_pin(plans["generation"]["decision_receipt"], Path(data_root).resolve()))
        require(authority.get("schema") == "saea-campaign-decision-v1" and authority.get("status") == "decided"
                and 227 in authority.get("owner_decisions", []) and authority.get("natural_source_compatibility") == compatibility,
                "natural compatibility root authority differs")
    natural = (_fixed400_natural(values, plans, population, repo_root=repo_root, data_root=data_root)
               if fixed400 else _qualified_natural_family(population, pin, plans["generation"]["natural_prerequisite"],
                   prerequisite, capacity, repo_root=repo_root, data_root=data_root, compatibility=compatibility,
                   decision_pin=plans["generation"].get("decision_receipt"),
                   joint_basis=values.get("joint_role_basis")))
    member, = [m for m in capacity["members"] if m["member_id"] == identity["member_id"]]
    roster = values["populations"][0]["ids"]
    require(len(values["populations"]) == 1 and type(values["population"]["count"]) is int
            and values["population"]["count"] == len(roster) == len(cohort["sample_ids"])
            and roster == cohort["sample_ids"] and len(set(roster)) == len(roster),
            "N20 configured roster differs from its immutable cohort")
    prepared = json.loads(_read_pin(values["prepared_phase_supply"], Path(data_root).resolve()))
    receipt_pin = plans["generation"].get("preparation_receipt")
    require(receipt_pin == plans["fit"].get("preparation_receipt"), "N20 preparation receipts differ")
    receipt = json.loads(_read_pin(receipt_pin, repo_root))
    require(receipt.get("member_id") == identity["member_id"]
            and receipt.get("experiment") == cell["cell_id"] and receipt.get("run_id") == cell["run_id"]
            and receipt.get("attempt_id") == cell["attempt_id"] and receipt.get("config_hash") == _canonical_hash(values)
            and receipt.get("configured_sample_ids") == roster
            and receipt.get("prepared_phase_supply") == values["prepared_phase_supply"]
            and receipt.get("contacts") == 0 and type(receipt["contacts"]) is int
            and receipt.get("output_equal") is True and receipt.get("warm_verified") is True
            and receipt.get("runtime_admission") is False
            and receipt.get("source_policy") == identity["execution_config"], "N20 preparation provenance differs")
    if local:
        require(receipt.get("local_node_basis") == values["local_node_basis"]
                and receipt.get("predecessor_preparation_receipt")
                == values["local_node_basis"]["source_preparation_receipt"],
                "local node preparation receipt basis differs")
    if joint:
        require(receipt.get("joint_role_basis") == values["joint_role_basis"]
                and receipt.get("predecessor_preparation_receipt")
                == json.loads(_read_pin(values["joint_role_basis"], repo_root))["source_preparation_receipt"]
                and prepared.get("output") == joint_basis["output"],
                "joint preparation lost original full400/N100 custody")
    _require_prepared_implementation(prepared, repo_root, values)
    require(prepared.get("output_sha256") == receipt.get("output_sha256"), "N20 prepared output binding differs")
    require(fixed400 or local or receipt["source_prepared_phase_supply"]
            == member["prepared_artifact_verification"]["capacity"]["prepared_pin"],
            "N20 prepared output source differs from original qualified capacity")
    prior = json.loads(_read_pin(receipt["source_prepared_phase_supply"], Path(data_root).resolve()))
    from ..core.preparation import digest
    if fixed400 or local:
        require(receipt["source_prepared_phase_supply"] == {
            "relpath": "prepared/SAEA-SLURP-SYSTEM-TEXT-UPDATE2-RH1-L-PARENT-V1/phase-supply-v1.json",
            "sha256": "99ba974066d6a87f086e8850c316252857e205e5213387e9ae7ed030c22900f0"},
            "fixed-roster original source supply raw pin differs")
        require(prior.get("output_sha256") == digest(prior["output"])
                and set(prior["output"]) == {"facets", "values"} and prior["output"]["facets"] == {}
                and set(prior["output"]["values"]) == {"perception"}
                and prepared["output"] == {"facets": {}, "values": {"perception": {
                    sid: prior["output"]["values"]["perception"][sid] for sid in roster}}},
                "fixed-roster prepared selection output equality differs")
    else:
        require(prior.get("output_sha256") == prepared["output_sha256"] == digest(prior["output"]),
                "N20 prepared output equality differs")
    if fixed400 or local:
        capacity_supply = json.loads(_read_pin(member["prepared_artifact_verification"]["capacity"]["prepared_pin"],
                                               Path(data_root).resolve()))
        require(capacity_supply.get("output_sha256") == prepared["output_sha256"]
                == digest(capacity_supply["output"])
                and capacity_supply["output"] == prepared["output"]
                and receipt.get("architecture_extent") == values.get("architecture_extent"),
                "fresh capacity supply or preparation extent differs")
    runtime_roster = receipt["runtime_sample_ids"]
    require(isinstance(runtime_roster, list) and all(isinstance(x, str) for x in runtime_roster)
            and len(runtime_roster) == len(set(runtime_roster)) == len(roster)
            and set(runtime_roster) == set(roster)
            and runtime_roster == member.get("runtime_sample_ids", cohort["sample_ids"]),
            "N20 prepared runtime roster differs from original capacity order")
    policy = drop_null_arms(json.loads(_read_pin(identity["execution_config"], repo_root)))
    require(all(values.get(k) == v for k, v in policy.items() if k != "what_this_is"),
            "N20 effective policy differs from its pinned member")
    program = default_phase_program(values["policy"])
    native = load_native_episode_config(values, program)
    require(native is not None and native.max_contacts == identity["model_per_trajectory"]
            and [r for r in population["nodes"] if native.role(r).max_iterations > 0] == identity["active_roles"],
            "N20 role/contact identity differs")
    require(values["native_graph_capacity_profile"] == member["rehearsal_profile"], "N20 profile differs")
    rehearsal_profile(values, member["rehearsal_profile"])
    require(all(values.get("decoding_params", {}).get(k) == v for k, v in population["sampling"].items())
            and all(values["system_search_measurement"].get(k) == v for k, v in population["execution"].items())
            and values["serving_slots"] == population["execution"]["slot_count"]
            and values["serving_slot_tokens"] == 24576, "N20 sampling/execution geometry differs")
    fit = validate_native_contact_fit_config(values, program)
    generation_cap = len(roster) * native.max_contacts
    fit_cap = generation_cap * population["contact_limits"]["fit_endpoints_per_model_contact"]
    require(fit is not None and fit.get("max_speech_packets", 1) == 1 and type(fit["contact_cap"]) is int
            and fit["contact_cap"] == fit_cap and fit["run_id"] != cell["run_id"]
            and fit["attempt_id"] != cell["attempt_id"], "N20 FIT identity or ceiling differs")
    expected_budget = dict(complete_system_trajectories=len(roster), generation_calls_cap=generation_cap,
                           actual_request_fit_endpoint_cap=fit_cap, official_complete_scoring_jobs=1)
    require(content_hash(values["family_budget"]) == content_hash(expected_budget), "N20 family budget differs")
    config_hash = _canonical_hash(values)
    split = split_identity_hash(prefixed("slurp", roster))
    require(values["population"]["split_identity_hash"] == split, "N20 split identity differs")
    expected = ExecutionPlan(**values["execution_plan"], run_id=cell["run_id"], attempt_id=cell["attempt_id"],
                            carrier_lock_key="slurp", split_identity_hash=split,
                            protocol_hash=protocol_hash(config_hash, values["arm"], split)).validate()
    require(expected.planned_model_calls == generation_cap and type(expected.planned_model_calls) is int
            and expected.execution_profile == "bounded-discovery-probe" and expected.split_role == "discovery",
            "N20 generation plan differs")
    for role, document in plans.items():
        bound_plan = expected if role == "generation" else replace(expected, run_id=fit["run_id"],
                                                                  attempt_id=fit["attempt_id"], planned_model_calls=fit_cap)
        require(document.get("schema") == f"saea-registered-{role}-plan-v1"
                and document.get("architecture_proof") == (plans["generation"]["architecture_proof"] if local else FIXED_ROSTER_SELECTOR if fixed400 else "manual-architecture-n20-v1")
                and str(document.get("status", "")).upper().startswith("ROOT COUNTERSIGNED BEFORE CONTACT")
                and document.get("architecture_member") == identity["member_id"]
                and document.get("cell") == cell["cell_id"] and document.get("experiment") == cell["cell_id"]
                and document.get("composed_config_hash") == config_hash and document.get("configured_sample_ids") == roster
                and document.get("runtime_sample_ids") == runtime_roster
                and document.get("policy_binding") == cell["system_text_policy_binding"]
                and cell["system_text_policy_binding"]["bundle_id"] == identity["base_bundle_id"]
                and document.get("prepared_phase_supply") == values["prepared_phase_supply"]
                and document.get("run_id", bound_plan.run_id) == bound_plan.run_id
                and document.get("attempt_id", bound_plan.attempt_id) == bound_plan.attempt_id
                and content_hash(document["execution_plan"]) == content_hash(asdict(bound_plan))
                and type(document.get("official_score_jobs")) is int and document["official_score_jobs"] == 1
                and document.get("learner_export") is False
                and document.get("population_budget") == population_accounting(population, identity["cohort_id"]),
                "N20 registered plan differs from its exact configuration, scope or identity")
    _require_n20_root_decision(plans, population, natural, repo_root=repo_root, data_root=data_root,
                               extent=values.get("architecture_extent"))
    return dict(member_id=identity["member_id"], sample_ids=deepcopy(roster),
                runtime_sample_ids=deepcopy(runtime_roster), generation_cap=generation_cap, fit_cap=fit_cap,
                capacity_registration_sha256=qualified["registration_sha256"],
                capacity_source_commit=capacity["worker_commit"],
                natural_qualification_sha256=plans["generation"]["natural_prerequisite"]["qualification"]["sha256"],
                natural_source_commit=natural["source_commit"], runtime_admission=False, read_authorized=False)


def _require_prepared_implementation(prepared, repo_root, values):
    """Bind the existing supply fingerprint to exact current source bytes."""
    from ..core.preparation import artifact_inputs, digest, SCHEMA
    require(prepared.get("schema") == SCHEMA and prepared.get("kind") == "phase-supply"
            and prepared.get("contact_class") == "model-free"
            and digest(prepared["output"]) == prepared.get("output_sha256"), "N20 prepared supply seal differs")
    expected = artifact_inputs(config=values, split_identity_hash=values["population"]["split_identity_hash"],
                               sources=prepared["inputs"]["sources"])
    require(prepared["inputs"] == expected
            and set(prepared["inputs"]["sources"]["packets"]) == set(values["populations"][0]["ids"]),
            "N20 prepared supply config or packet membership differs")
    implementation = prepared["inputs"]["sources"]["implementation"]
    paths = {"runtime": "core/flight/runtime.py"}
    paths.update({"speech_aware_evidence_acquisition.rails." + name: "rails/" + name + ".py"
                  for name in ("kb_policy", "knowledge_provider", "knowledge_stores", "phase_supply")})
    require(set(implementation) == set(paths), "N20 prepared implementation coverage differs")
    package = Path(repo_root) / "src/speech_aware_evidence_acquisition"
    require(all(hashlib.sha256((package / path).read_bytes()).hexdigest() == implementation[name]
                for name, path in paths.items()), "N20 prepared implementation source differs")


def _mapped_execution_cells(pin, population, population_pin, extent, *, repo_root, data_root=None):
    """Compose a complete pinned successor map without pinning its future config."""
    root = Path(repo_root).resolve()
    mapping = json.loads(_read_pin(pin, root))
    from .local_node_panel import MAP_SCHEMA, mapped_local_node_cells
    if mapping.get("schema") == JOINT_MAP_SCHEMA:
        require(extent is None, "joint map cannot inherit historical extent")
        return _mapped_joint_cells(mapping, population, population_pin, repo_root=root, data_root=data_root)
    if mapping.get("schema") == MAP_SCHEMA:
        require(extent is None, "local node map cannot inherit historical fixed-roster extent")
        return mapped_local_node_cells(mapping, population, population_pin, repo_root=root)
    labels = [m["member_id"] for m in population["architecture"]["members"]]
    require(isinstance(mapping, dict) and set(mapping) == {
        "schema", "experiment_population", "architecture_extent", "members"}
        and mapping["schema"] == "saea-manual-architecture-execution-identity-map-v1"
        and mapping["experiment_population"] == population_pin
        and mapping["architecture_extent"] == extent
        and isinstance(mapping["members"], list)
        and [m.get("member_id") for m in mapping["members"]] == labels,
        "manual execution identity map scope or ordered membership differs")
    keys = {"member_id", "experiment", "cell_id", "run_id", "attempt_id", "fit_run_id",
            "fit_attempt_id", "planned_speech_audio_seconds", "predecessor_experiment", "predecessor_baseline"}
    current_runs, current_attempts, old_runs, old_attempts, experiments, result = [], [], [], [], [], []
    for row in mapping["members"]:
        require(isinstance(row, dict) and set(row) == keys
                and all(isinstance(row[k], str) and row[k].strip() for k in (
                    "experiment", "cell_id", "run_id", "attempt_id", "fit_run_id", "fit_attempt_id"))
                and type(row["planned_speech_audio_seconds"]) is int
                and row["planned_speech_audio_seconds"] > 0,
                "manual execution identity map fields differ")
        prior_stem = "slurp-native-stage3-simple-consumption-" + row["member_id"] + (
            "-n" + str(extent["count"]) + "-v1" if extent is not None else "-n20-v2")
        require(row["predecessor_experiment"]["relpath"] == "configs/experiment/" + prior_stem + ".json"
                and row["experiment"] != prior_stem and row["experiment"] == row["cell_id"]
                and all(c.isalnum() or c == "-" for c in row["experiment"]),
                "manual execution predecessor or successor stem differs")
        old_exp = json.loads(_read_pin(row["predecessor_experiment"], root))
        require(len(old_exp.get("cells", [])) == 1, "manual predecessor needs one exact cell")
        old_cell = old_exp["cells"][0]
        require(old_cell["cell_id"] == prior_stem
                and row["predecessor_baseline"]["relpath"] == "configs/baseline/" + old_cell["baseline_fragment"] + ".json",
                "manual predecessor baseline binding differs")
        old_base = json.loads(_read_pin(row["predecessor_baseline"], root))
        expected_exp, expected_base = deepcopy(old_exp), deepcopy(old_base)
        expected_exp["experiment_id"] = row["run_id"]
        require(row["planned_speech_audio_seconds"] >= old_exp["execution_plan"]["planned_speech_audio_seconds"],
                "manual successor cannot reduce its declared audio allowance")
        expected_exp["execution_plan"]["planned_speech_audio_seconds"] = row["planned_speech_audio_seconds"]
        expected_cell = expected_exp["cells"][0]
        expected_cell.update(cell_id=row["cell_id"], run_id=row["run_id"], attempt_id=row["attempt_id"],
                             baseline_fragment=row["experiment"])
        expected_cell.pop("readiness", None)
        expected_base["native_contact_fit"].update(run_id=row["fit_run_id"], attempt_id=row["fit_attempt_id"])
        expected_base.pop("prepared_phase_supply", None)
        actual_exp = json.loads((root / "configs/experiment" / (row["experiment"] + ".json")).read_bytes())
        actual_base = json.loads((root / "configs/baseline" / (row["experiment"] + ".json")).read_bytes())
        projected_exp, projected_base = deepcopy(actual_exp), deepcopy(actual_base)
        require(len(projected_exp.get("cells", [])) == 1, "manual successor needs one exact cell")
        projected_exp["cells"][0].pop("readiness", None)
        projected_base.pop("prepared_phase_supply", None)
        require(projected_exp == expected_exp and projected_base == expected_base,
                "manual successor changed fields outside the pinned identity/audio/admission projection")
        cell, = load_campaign_cells(root, row["experiment"])
        c = cell.document
        configured = compose(root, c["model_fragment"], c["dataset_fragment"], c["baseline_fragment"], row["experiment"])
        require(configured.values["experiment_population"] == population_pin
                and configured.values.get("architecture_extent") == extent
                and configured.values["architecture_member"] == row["member_id"],
                "manual successor composed population or member differs")
        current_runs.extend([row["run_id"], row["fit_run_id"]])
        current_attempts.extend([row["attempt_id"], row["fit_attempt_id"]])
        old_runs.extend([old_cell["run_id"], old_base["native_contact_fit"]["run_id"]])
        old_attempts.extend([old_cell["attempt_id"], old_base["native_contact_fit"]["attempt_id"]])
        experiments.append(row["experiment"])
        result.append((row["member_id"], cell, configured))
    require(len(current_runs) == len(set(current_runs))
            and len(current_attempts) == len(set(current_attempts))
            and len(experiments) == len(set(experiments))
            and not set(current_runs).intersection(old_runs)
            and not set(current_attempts).intersection(old_attempts),
            "manual successor identities are duplicated or reuse a predecessor")
    return result


def _require_n20_root_decision(plans, population, natural, *, repo_root, data_root, extent=None):
    """Require one decided owner227 admission for the exact prospective family."""
    decision_pin = plans["generation"].get("decision_receipt")
    require(decision_pin == plans["fit"].get("decision_receipt"), "N20 pair root decisions differ")
    decision = json.loads(_read_pin(decision_pin, Path(data_root).resolve()))
    require(all(p.get("natural_source_compatibility") == decision.get("natural_source_compatibility") for p in plans.values()),
            "natural compatibility decision and pair differ")
    require(decision.get("schema") == "saea-campaign-decision-v1" and decision.get("status") == "decided"
            and 227 in decision.get("owner_decisions", []) and decision.get("learner_export") is False
            and decision.get("experiment_population") == plans["generation"]["experiment_population"]
            and decision.get("capacity_prerequisite") == plans["generation"]["capacity_prerequisite"]
            and decision.get("natural_prerequisite") == plans["generation"]["natural_prerequisite"],
            "N20 decided owner227 admission differs")
    receipt = json.loads(_read_pin(plans["generation"]["preparation_receipt"], repo_root))
    source = receipt.get("prepared_source_commit")
    require(isinstance(source, str) and len(source) == 40 and all(x in "0123456789abcdef" for x in source)
            and decision.get("source_preparation_commit") == source, "N20 root preparation source differs")
    if plans["generation"].get("architecture_proof") in ("local-solver-panel-v1", "local-reviewer-panel-v1"):
        require(decision.get("local_node_basis") == plans["generation"].get("local_node_basis")
                == plans["fit"].get("local_node_basis") and decision.get("natural_source_compatibility") is None,
                "local node root basis or fresh proof differs")
    require(decision.get("architecture_extent") == extent
            and all(p.get("architecture_extent") == extent for p in plans.values()),
            "manual root decision extent differs")
    map_pin = decision.get("execution_identity_map")
    require(all(p.get("execution_identity_map") == map_pin for p in plans.values()),
            "manual root decision identity maps differ")
    joint_pin = plans["generation"].get("joint_role_basis")
    if joint_pin is not None:
        require(decision.get("joint_role_basis") == joint_pin == plans["fit"].get("joint_role_basis")
                and map_pin is not None and decision.get("natural_source_compatibility") is None,
                "joint root admission requires exact basis/map and fresh proof")
    else:
        require(decision.get("joint_role_basis") is None, "unsolicited joint root admission refused")
    if map_pin is not None:
        cells = _mapped_execution_cells(map_pin, population, plans["generation"]["experiment_population"],
                                        extent, repo_root=repo_root, **({"data_root":data_root} if joint_pin is not None else {}))
    else:
        cells = []
        for member in population["architecture"]["members"]:
            stem = "slurp-native-stage3-simple-consumption-" + member["member_id"] + ("-n" + str(extent["count"]) + "-v1" if extent is not None else "-n20-v2")
            cell, = load_campaign_cells(repo_root, stem)
            document = cell.document
            config = compose(repo_root, document["model_fragment"], document["dataset_fragment"],
                             document["baseline_fragment"], stem)
            cells.append((member["member_id"], cell, config))
    expected_ids = []
    for member_id, cell, config in cells:
        document = cell.document
        fit = config.values["native_contact_fit"]
        expected_ids.extend([document["run_id"], fit["run_id"]])
        if member_id == plans["generation"]["architecture_member"]:
            for role, run_id, attempt_id in (("generation", document["run_id"], document["attempt_id"]),
                                            ("fit", fit["run_id"], fit["attempt_id"])):
                plan = plans[role]
                require(plan["cell"] == plan["experiment"] == document["cell_id"]
                        and plan["composed_config_hash"] == config.config_hash
                        and plan["execution_plan"]["run_id"] == run_id
                        and plan["execution_plan"]["attempt_id"] == attempt_id,
                        "N20 root member identity differs from its independently composed cell")
    require(decision.get("eligible_run_ids") == expected_ids and len(set(expected_ids)) == len(expected_ids),
            "N20 root admission family eligibility differs")
    if joint_pin is not None:
        require_joint_adaptive_disposition(decision, joint_pin, population, cells,
                repo_root=repo_root, data_root=data_root)


def _qualified_natural_family(population, pin, prerequisite, capacity_prerequisite, capacity, *, repo_root, data_root, compatibility=None, decision_pin=None, joint_basis=None):
    """Validate all raw-pinned structural prerequisites without reading task answers."""
    require(data_root is not None and isinstance(prerequisite, dict)
            and set(prerequisite) == {"registration", "qualification"}, "exact N20 natural prerequisite required")
    root = Path(data_root).resolve()
    def read(raw_pin):
        return json.loads(_read_pin(raw_pin, root))
    admission, qualified = read(prerequisite["registration"]), read(prerequisite["qualification"])
    labels = [m["member_id"] for m in population["architecture"]["members"]]
    require(qualified.get("schema") == "saea-architecture-natural-family-qualification-v1"
            and qualified.get("status") == "QUALIFIED_STRUCTURAL_ONLY" and qualified.get("passed") is True
            and qualified.get("registration") == prerequisite["registration"]
            and qualified.get("experiment_population") == pin
            and type(qualified.get("official_score_jobs")) is int and qualified["official_score_jobs"] == 0
            and qualified.get("scientific_feedback") is False and qualified.get("learner_export") is False
            and qualified.get("next_panel_admitted") is False,
            "N20 natural qualification scope or registration differs")
    source = qualified["source_commit"]
    require(isinstance(source, str) and len(source) == 40 and all(x in "0123456789abcdef" for x in source),
            "N20 natural source commit invalid")
    root_read = read(qualified["root_read_receipt"])
    require(root_read.get("schema") == "saea-architecture-natural-family-root-read-v1"
            and root_read.get("status") == "ROOT COUNTERSIGNED STRUCTURAL READ" and root_read.get("passed") is True
            and root_read.get("registration") == prerequisite["registration"]
            and root_read.get("experiment_population") == pin and root_read.get("source_commit") == source
            and root_read.get("frozen_worker") == qualified["frozen_worker"]
            and root_read.get("member_labels") == labels
            and type(root_read.get("official_score_jobs")) is int and root_read["official_score_jobs"] == 0
            and root_read.get("scientific_feedback") is False and root_read.get("learner_export") is False,
            "N20 whole-family root structural READ differs")
    require(admission.get("schema") == "saea-campaign-decision-v1" and admission.get("status") == "decided"
            and 227 in admission.get("owner_decisions", []) and admission.get("next_panel_authorized") is False
            and admission.get("learning") == "HELD" and admission.get("capacity_prerequisite") == capacity_prerequisite,
            "N20 natural owner227 admission differs")
    require([m.get("label") for m in qualified["members"]] == labels
            and [m.get("label") for m in root_read["members"]] == labels,
            "N20 natural family incomplete, duplicated or reordered")
    implementation_root = repo_root
    if compatibility is not None:
        from .natural_source_compatibility import validate_compatibility
        decision = read(decision_pin)
        require(decision.get("natural_source_compatibility") == compatibility, "natural compatibility authority differs")
        implementation_root = validate_compatibility(read(compatibility), prerequisite, qualified, decision,
            repo_root=repo_root, data_root=data_root, read_pin=_read_pin)
    eligible = []
    for identity, member, read_member in zip(population["architecture"]["members"], qualified["members"],
                                           root_read["members"], strict=True):
        label = identity["member_id"]
        cell, = load_campaign_cells(repo_root, member["experiment"])
        cell = cell.document
        config = compose(repo_root, cell["model_fragment"], cell["dataset_fragment"],
                         cell["baseline_fragment"], member["experiment"])
        values = config.values
        capmember, = [m for m in capacity["members"] if m["label"] == label]
        roster, runtime = member["configured_sample_ids"], member["runtime_sample_ids"]
        require(isinstance(roster, list) and isinstance(runtime, list)
                and all(isinstance(x, str) for x in roster + runtime)
                and len(roster) == len(set(roster)) == len(runtime) == len(set(runtime)) == member["rows"] == 4
                and roster == capmember["graph_sample_ids"]
                and runtime == capmember.get("runtime_graph_sample_ids", roster), "N20 natural runtime membership differs")
        require(cell.get("allowed_execution_stages") == ["check", "prepare-supply", "worker"]
                and values["architecture_member"] == label and values["experiment_population"] == pin
                and config.config_hash == member["config_hash"] and values["populations"][0]["ids"] == roster
                and cell["run_id"] == member["run_id"] and cell["attempt_id"] == member["attempt_id"]
                and values["native_contact_fit"]["run_id"] == member["fit_run_id"]
                and cell["system_text_policy_binding"] == member["policy_binding"]
                and member["policy_binding"]["bundle_id"] == identity["base_bundle_id"]
                and values["prepared_phase_supply"] == member["prepared_phase_supply"],
                "N20 natural member config, policy or identity differs")
        policy = drop_null_arms(json.loads(_read_pin(identity["execution_config"], repo_root)))
        require(all(values.get(k) == v for k, v in policy.items() if k != "what_this_is"),
                "N20 natural effective policy differs")
        if compatibility is not None:
            from .architecture_audio_budget import manual_architecture_audio_budget_applies
            require(not manual_architecture_audio_budget_applies(values), "historical natural audio guard must be inactive")
        _require_prepared_implementation(read(member["prepared_phase_supply"]), implementation_root, values)
        require(all(read_member.get(k) == member[k] for k in ("run_id", "attempt_id", "manifest", "guard_finished")),
                "N20 root READ member custody binding differs")
        manifest, attempt, inspection, guard, report = [read(member[k]) for k in
            ("manifest", "attempt", "inspection", "guard_finished", "structural_report")]
        split = split_identity_hash(prefixed("slurp", roster))
        expected_plan = ExecutionPlan(**values["execution_plan"], run_id=member["run_id"],
            attempt_id=member["attempt_id"], carrier_lock_key="slurp", split_identity_hash=split,
            protocol_hash=protocol_hash(config.config_hash, values["arm"], split)).validate()
        fit_spec = values["native_contact_fit"]
        expected_fit = replace(expected_plan, run_id=fit_spec["run_id"], attempt_id=fit_spec["attempt_id"],
                               planned_model_calls=fit_spec["contact_cap"])
        contacts = member["model_contacts"]
        require(type(contacts) is int and 0 < contacts <= 4 * identity["model_per_trajectory"],
                "N20 natural contact accounting invalid")
        require(manifest.get("schema") == "saea-run-manifest-v1" and manifest.get("status") == "COMPLETED"
                and manifest.get("run_id") == member["run_id"] and manifest.get("study_commit") == source
                and manifest.get("study_repo_dirt") == [] and manifest["config"]["config_hash"] == member["config_hash"]
                and manifest["plan"] == asdict(expected_plan) and manifest.get("scores") is None,
                "N20 natural manifest source, identity or completion differs")
        require(attempt.get("state") == "OPENED" and attempt.get("run_id") == member["run_id"]
                and attempt.get("attempt_id") == member["attempt_id"] and attempt["actual"]["calls"] == contacts,
                "N20 natural attempt accounting differs")
        require(inspection.get("pass") is True and inspection.get("bundle_verified") is True
                and inspection.get("fails") == [] and inspection.get("dirt") == []
                and inspection.get("study_commit") == source and inspection.get("manifest_status") == "COMPLETED"
                and inspection.get("run_id") == member["run_id"] and inspection.get("attempt_id") == member["attempt_id"]
                and inspection.get("rows") == inspection.get("distinct") == 4
                and inspection["actual"]["calls"] == contacts
                and inspection.get("sha256_run-manifest") == member["manifest"]["sha256"],
                "N20 natural custody inspection differs")
        require(guard.get("schema") == "saea-flight-process-memory-guard-v1" and guard.get("status") == "completed"
                and type(guard.get("exit_code")) is int and guard["exit_code"] == 0
                and type(guard.get("worker_returncode")) is int and guard["worker_returncode"] == 0
                and guard["identity"]["run_id"] == member["run_id"]
                and guard["identity"]["attempt_id"] == member["attempt_id"]
                and guard["identity"]["study_head"] == source
                and guard["identity"]["repo_root"] == qualified["frozen_worker"], "N20 natural guarded terminal differs")
        require(report.get("schema") == "saea-natural-architecture-structural-report-v1"
                and all(report.get(k) is True for k in ("passed", "bundle_verified", "all_contacts_joined",
                                                       "all_original_fits_verified", "terminal_policy_verified"))
                and all(report.get(k) == member[k] for k in ("label", "run_id", "attempt_id", "config_hash",
                    "configured_sample_ids", "runtime_sample_ids", "model_contacts"))
                and report.get("source_commit") == source and report.get("official_score_jobs") == 0
                and report.get("scientific_feedback") is False and report.get("learner_export") is False
                and len(report["rows"]) == 4
                and [row["sample_id"] for row in report["rows"]] == runtime
                and all(row.get("terminal_policy_verified") is True for row in report["rows"])
                and sum(row["contacts"] for row in report["rows"]) == contacts
                and report.get("reviewer_applicable") == ("reviewer" in identity["active_roles"]),
                "N20 natural structural report differs")
        _read_pin(report["flight_receipts"], root)
        accounting = read(member["actual_fit_accounting"])
        require(member["actual_fit_accounting"] == root_read["actual_fit_accounting"]
                and accounting.get("schema") == "saea-native-actual-fit-accounting-v1", "N20 FIT accounting scope differs")
        fit, = [f for f in accounting["members"] if f["run_id"] == member["fit_run_id"]]
        records = fit["records"]
        require(len(records) == fit["actual_request_receipts"] == report["actual_fit_receipts"]
                and len({r["relpath"] for r in records}) == len(records)
                and fit["actual_endpoints"] == report["actual_fit_endpoints"]
                == sum(r["actual_endpoints"] for r in records)
                and {r["relpath"]: r["sha256"] for r in records}
                == {r["relpath"]: r["sha256"] for r in report["fit_receipts"]}, "N20 actual FIT coverage differs")
        for record in records:
            from ..core.preparation import load_artifact
            raw_pin = {k: record[k] for k in ("relpath", "sha256")}
            artifact = read(raw_pin)
            output = load_artifact(root / raw_pin["relpath"], expected_sha256=raw_pin["sha256"],
                                   kind="request-fit", inputs=artifact["inputs"])
            journal = _read_pin({"relpath": record["relpath"] + ".contacts.jsonl",
                                 "sha256": record["journal_sha256"]}, root)
            journal = [json.loads(line) for line in journal.splitlines() if line.strip()]
            require(artifact["contact_class"] == "tokenizer" and output.get("every_request_fits") is True
                    and output.get("capacity_scope") == "actual-variable-trajectory-contact"
                    and output.get("generation_contacts") == 0
                    and artifact["inputs"]["fit_plan"] == asdict(expected_fit)
                    and artifact["inputs"]["native_contact"]["agent_contact_id"] == output["agent_contact_id"]
                    and len(journal) == output["contacts"] == record["actual_endpoints"]
                    and dict(Counter(row["method"] + " " + row["route"] for row in journal)) == output["contact_counts"]
                    and [row["contact"] for row in journal]
                    == list(range(output["cumulative_contacts"] - output["contacts"] + 1,
                                  output["cumulative_contacts"] + 1)), "N20 original FIT journal or identity differs")
        eligible.extend([member["run_id"], member["fit_run_id"]])
    require(admission.get("eligible_run_ids") == eligible and len(set(eligible)) == len(eligible),
            "N20 natural admission eligibility differs")
    if joint_basis is not None:
        require(compatibility is None and decision_pin is not None,
                "joint natural proof cannot reuse historical source compatibility")
        next_decision = read(decision_pin)
        require(next_decision.get("joint_role_basis") == joint_basis,
                "joint N100 natural prerequisite authority differs")
        _require_joint_completed_natural(admission, qualified, next_decision, population, pin,
                repo_root=repo_root, data_root=data_root)
    else:
        require(admission.get("joint_role_basis") is None, "unsolicited joint natural prerequisite refused")
    return qualified


def _require_joint_completed_natural(admission, qualified, next_decision, population, population_pin, *, repo_root, data_root):
    """Join the completed original proof to its full prospective N100 parent map."""
    basis_pin = next_decision.get("joint_role_basis")
    require(basis_pin is not None and admission.get("joint_role_basis") == basis_pin,
            "joint N100 and original natural admission basis differ")
    map_pin = admission.get("joint_proof_identity_map")
    mapping = json.loads(_read_pin(map_pin, repo_root))
    require(mapping.get("generation_identity_map") == next_decision.get("execution_identity_map"),
            "joint natural proof belongs to another N100 parent family")
    cells = _mapped_joint_proof_cells(map_pin, population, population_pin,
            repo_root=repo_root, data_root=data_root, stage="natural")
    require_joint_adaptive_disposition(admission, basis_pin, population, cells,
            repo_root=repo_root, data_root=data_root, stage="natural")
    expected = []
    require(len(qualified["members"]) == len(cells), "joint original natural family is partial")
    for member, (label, cell, config) in zip(qualified["members"], cells, strict=True):
        c = cell.document
        require(member["label"] == label and member["experiment"] == c["cell_id"]
                and member["run_id"] == c["run_id"] and member["attempt_id"] == c["attempt_id"]
                and member["config_hash"] == config.config_hash
                and member["configured_sample_ids"] == config.values["populations"][0]["ids"]
                and member["fit_run_id"] == config.values["native_contact_fit"]["run_id"],
                "joint qualified original natural member differs from its separate registration")
        expected.extend((c["run_id"], config.values["native_contact_fit"]["run_id"]))
    require(admission.get("eligible_run_ids") == expected,
            "joint complete natural eligibility differs from original proof map")


JOINT_BASIS_SCHEMA = "saea-joint-role-import-n100-basis-v1"
JOINT_MAP_SCHEMA = "saea-joint-role-import-execution-identity-map-v1"
JOINT_SOURCE_DECISION = {
    "relpath": "docs/readiness/2026-10-09-slurp-local-to-joint-n100-v1/root-decision-v1.json",
    "sha256": "68f4ab8ce4d71e8731f743e357738786fc78fb086022a135245cbcf413dd3d51",
}
JOINT_DONOR_PREPARATIONS = {
    "solver": {"relpath": "docs/readiness/2026-10-08-slurp-local-solver-n100-k4-update3-v1/prepared-v1/candidate-4-generation-prepared-v1.json",
               "sha256": "0577d4b04c7f9a162cf5ba041c2e7021644318360e336d1c859e57d6fdabdf5b"},
    "reviewer": {"relpath": "docs/readiness/2026-10-08-slurp-local-reviewer-n100-k4-update2-v1/prepared-v1/candidate-1-generation-prepared-v1.json",
                 "sha256": "21a535092ca6bf9697ed2d78f29803c46b362c2d5f99241c78c05442572f9f18"},
}
JOINT_FULL_SUPPLY = {
    "relpath": "prepared/SAEA-SLURP-SYSTEM-TEXT-UPDATE2-RH1-L-PARENT-V1/phase-supply-v1.json",
    "sha256": "99ba974066d6a87f086e8850c316252857e205e5213387e9ae7ed030c22900f0",
}
JOINT_PROOF_ROSTER = {
    "relpath": "configs/dataset/slurp-speech-native-simple-consumption-n100-graph4-v1.json",
    "sha256": "fe35d4a89f4ddac7c4a3f4b32da1ed244f9c1f1d422d56098d6118085190d80d",
}


def _joint_original_spend(bound, *, repo_root):
    """Retain all original generation/FIT identities without reading outcomes."""
    runs, attempts = set(), set()
    for receipt in [bound["receipt"], *bound["donor_receipts"].values()]:
        cell, = load_campaign_cells(repo_root, receipt["experiment"])
        c = cell.document
        config = compose(repo_root, c["model_fragment"], c["dataset_fragment"],
                         c["baseline_fragment"], receipt["experiment"])
        require(c["run_id"] == receipt["run_id"] and c["attempt_id"] == receipt["attempt_id"],
                "joint original spend metadata differs")
        fit = config.values["native_contact_fit"]
        runs.update((c["run_id"], fit["run_id"]))
        attempts.update((c["attempt_id"], fit["attempt_id"]))
    return runs, attempts


def _joint_proof_roster(population, *, repo_root):
    """Use the original raw-pinned graph proof rather than an arbitrary subset."""
    view = json.loads(_read_pin(JOINT_PROOF_ROSTER, repo_root))
    ids = [item["sample_id"] for item in view["items"]]
    require(view.get("split_role") == "discovery" and len(ids) == len(set(ids)) == view["count"]
            and ids == population["cohorts"][0]["sample_ids"][:len(ids)],
            "joint original complete graph proof roster differs")
    return view, ids


def _joint_archived_policy(binding, data_root):
    """Resolve the exact original canonical archive without selecting a policy."""
    from .system_search_archive import SystemSearchArchive
    require(isinstance(binding, dict)
            and binding.get("schema") == "saea-system-text-role-binding-v1",
            "joint original role binding required")
    policy_pin = binding["bundle"]
    path = Path(data_root).resolve() / policy_pin["relpath"]
    require(path.resolve().is_relative_to(Path(data_root).resolve())
            and path.parent.name == "policies" and path.name == binding["bundle_id"] + ".json",
            "joint original policy must retain its canonical archive path")
    _read_pin(policy_pin, data_root)
    return SystemSearchArchive(path.parent.parent).load_policy(binding["bundle_id"])


def _joint_policy_projection(source, candidate, texts, *, repo_root):
    """Refuse every effective change beyond content-addressed exact role text."""
    normalized, actual_texts = [], []
    for policy in (source, candidate):
        value = drop_null_arms(deepcopy(policy))
        value.pop("what_this_is", None)
        material = value["phase_material"]
        params, = [c["params"] for c in value["native_episode"]["consumption_module"]["components"]
                   if c["component_id"] == "knowledge-consumption-opportunity"]
        role_text = {}
        for role in ("perception", "solver", "reviewer", "planner"):
            relative = material[role]["instruction_template"]
            path = (Path(repo_root) / "configs" / relative).resolve()
            require(path.is_relative_to(Path(repo_root).resolve() / "configs")
                    and params.get(role + "_template") == relative,
                    "joint role template custody differs")
            role_text[role] = path.read_bytes()
            material[role]["instruction_template"] = "<bound-" + role + "-template>"
            params[role + "_template"] = material[role]["instruction_template"]
        normalized.append(value)
        actual_texts.append(role_text)
    require(normalized[0] == normalized[1], "joint import changed full-seed topology or fixed configuration")
    require(actual_texts[1] == {r: texts[r].encode("utf-8") for r in actual_texts[0]},
            "joint compiled role bytes differ from exact seed/import mask")


def require_joint_role_basis(basis_pin, population, *, repo_root, data_root):
    """Bind adaptive deterministic imports to original full400/N100 custody.

    This metadata validator grants no contacts, registration, READ or adoption.
    """
    from .local_node_panel import SOURCE_POPULATION, REVIEWER_SOURCE_RECEIPT
    from .system_text_policy import import_exact_role_texts, cumulative_sources
    require(data_root is not None, "joint basis requires original DATA custody")
    basis = json.loads(_read_pin(basis_pin, repo_root))
    require(isinstance(basis, dict) and set(basis) == {
        "schema", "root_decision", "source_population", "source_preparation_receipt",
        "donor_preparation_receipts", "root_selection_sources"}
        and basis["schema"] == JOINT_BASIS_SCHEMA
        and basis["root_decision"] == JOINT_SOURCE_DECISION
        and basis["source_population"] == SOURCE_POPULATION
        and basis["source_preparation_receipt"] == REVIEWER_SOURCE_RECEIPT
        and basis["donor_preparation_receipts"] == JOINT_DONOR_PREPARATIONS,
        "joint exact owner/source/preparation basis differs")
    decision = json.loads(_read_pin(JOINT_SOURCE_DECISION, repo_root))
    require(decision.get("schema") == "saea-root-local-to-joint-development-decision-v1"
            and decision.get("status") == "SOURCE_ENGINEERING_APPROVED_RUNTIME_HELD"
            and type(decision.get("owner_decision")) is int and decision["owner_decision"] == 227
            and decision.get("roster_basis") == SOURCE_POPULATION
            and decision.get("analysis", {}).get("claims_benefit") is False
            and decision["analysis"].get("independent_validation") is False
            and decision["analysis"].get("runtime_adoption") is False
            and decision["analysis"].get("learner_export") is False,
            "joint development authority does not permit broader claims")
    original = load_population_config(SOURCE_POPULATION, repo_root=repo_root, allow_architecture=True)
    require(len(population["cohorts"]) == len(original["cohorts"]) == 1,
            "joint requires the complete original singleton cohort")
    cohort, = population["cohorts"]
    old, = original["cohorts"]
    ids = old["sample_ids"]
    members = population["architecture"]["members"]
    ordered = decision["ordered_members"]
    require(cohort["sample_ids"] == ids and len(ids) == len(set(ids)) == decision["rows_per_member"]
            and [m["member_id"] for m in members] == [m["id"] for m in ordered]
            and cohort["control_ids"] == [m["id"] for m in ordered if not m["imports"]]
            and cohort["candidate_ids"] == [m["id"] for m in ordered if m["imports"]]
            and len(cohort["control_ids"]) == decision["control_count"]
            and len(cohort["candidate_ids"]) == decision["candidate_count"]
            and population["sampling"] == original["sampling"]
            and population["execution"] == original["execution"]
            and population["contact_limits"] == original["contact_limits"],
            "joint cohort/order/count/sampling/geometry/contact accounting differs")
    receipt = json.loads(_read_pin(REVIEWER_SOURCE_RECEIPT, repo_root))
    require(receipt.get("configured_sample_ids") == ids
            and type(receipt.get("contacts")) is int and receipt["contacts"] == 0
            and receipt.get("warm_verified") is True and receipt.get("output_equal") is True
            and receipt.get("runtime_admission") is False
            and receipt.get("source_prepared_phase_supply") == JOINT_FULL_SUPPLY,
            "joint original full-seed preparation custody differs")
    sources = [{"kind":"selection", "sha256":JOINT_SOURCE_DECISION["sha256"], "sample_ids":ids}]
    for evidence in decision["prior_evidence"]:
        _read_pin(evidence, repo_root)  # Raw custody only; never parse quality.
        sources.append({"kind":"selection", "sha256":evidence["sha256"], "sample_ids":ids})
    require(basis["root_selection_sources"] == cumulative_sources([], sources),
            "joint root-visible complete family selection exposure is partial or changed")
    seed = _joint_archived_policy(receipt["policy_binding"], data_root)
    require(seed.bundle_id == decision["full_seed_bundle_id"], "joint full seed identity differs")
    donors, donor_receipts = {}, {}
    for role, pin in JOINT_DONOR_PREPARATIONS.items():
        donor_receipt = json.loads(_read_pin(pin, repo_root))
        require(donor_receipt.get("configured_sample_ids") == ids
                and donor_receipt.get("source_prepared_phase_supply") == JOINT_FULL_SUPPLY
                and donor_receipt.get("policy_binding", {}).get("bundle_id") == decision["donors"][role]["bundle_id"],
                "joint original selected donor preparation or full400 basis differs")
        donors[role] = _joint_archived_policy(donor_receipt["policy_binding"], data_root)
        donor_receipts[role] = donor_receipt
    source_policy = drop_null_arms(json.loads(_read_pin(receipt["source_policy"], repo_root)))
    policies = {}
    for identity, declared in zip(members, ordered, strict=True):
        bundle = (import_exact_role_texts(seed, donors, roles=declared["imports"],
                  decision=decision, selection_sources=basis["root_selection_sources"])
                  if declared["imports"] else seed)
        require(identity["base_bundle_id"] == bundle.bundle_id
                and identity["active_roles"] == ["perception", "solver", "reviewer", "planner"],
                "joint actual import identity or full-seed active roles differ")
        candidate = drop_null_arms(json.loads(_read_pin(identity["execution_config"], repo_root)))
        _joint_policy_projection(source_policy, candidate, bundle.as_json()["role_text"], repo_root=repo_root)
        native = load_native_episode_config({**candidate,"carrier_lock_key":"slurp"}, default_phase_program(candidate["policy"]))
        require(native.review_loop_enabled is True
                and native.max_contacts == identity["model_per_trajectory"] == population["contact_limits"]["model_per_trajectory"],
                "joint complete full-seed contact topology differs")
        policies[identity["member_id"]] = bundle
    from ..core.preparation import digest
    parent = json.loads(_read_pin(JOINT_FULL_SUPPLY, data_root))
    selected = json.loads(_read_pin(receipt["prepared_phase_supply"], data_root))
    require(parent.get("output_sha256") == digest(parent["output"])
            and set(parent["output"]) == {"facets","values"} and parent["output"]["facets"] == {}
            and set(parent["output"]["values"]) == {"perception"}
            and set(ids) <= set(parent["output"]["values"]["perception"]),
            "joint original full400 supply seal or complete coverage differs")
    output = {"facets":{},"values":{"perception":{sid:parent["output"]["values"]["perception"][sid] for sid in ids}}}
    require(selected["output"] == output and selected.get("output_sha256") == receipt["output_sha256"] == digest(output),
            "joint original same-N100 selected supply differs")
    return {"decision":decision,"receipt":receipt,"donor_receipts":donor_receipts,
            "policies":policies,"output":output,"source_policy":source_policy,
            "cumulative_sources":cumulative_sources([seed,*donors.values()],basis["root_selection_sources"])}



def _mapped_joint_cells(mapping, population, population_pin, *, repo_root, data_root):
    """Validate exact seed-derived fresh identities through the existing projection."""
    from .local_node_panel import require_local_identities, local_node_documents
    from .experiment_population import population_stage_spec
    from .architecture_audio_budget import derive_manual_architecture_audio_budget
    require(isinstance(mapping,dict) and set(mapping) == {
        "schema","experiment_population","architecture_extent","joint_role_basis","members"}
        and mapping["schema"] == JOINT_MAP_SCHEMA and mapping["experiment_population"] == population_pin
        and mapping["architecture_extent"] is None,
        "joint complete fresh execution map scope differs")
    bound = require_joint_role_basis(mapping["joint_role_basis"],population,repo_root=repo_root,data_root=data_root)
    receipt = bound["receipt"]
    source_cell, = load_campaign_cells(repo_root,receipt["experiment"])
    c = source_cell.document
    source = compose(repo_root,c["model_fragment"],c["dataset_fragment"],c["baseline_fragment"],receipt["experiment"])
    require(source.config_hash == receipt["config_hash"], "joint original full-seed composed identity differs")
    rows = mapping["members"]
    require([r.get("member_id") for r in rows] == [m["member_id"] for m in population["architecture"]["members"]],
            "joint map requires complete ordered configured family")
    identities = [{k:v for k,v in row.items() if k != "planned_speech_audio_seconds"} for row in rows]
    require_local_identities(identities,source_cell=c,source_fit=source.values["native_contact_fit"])
    result = []
    original_exp = json.loads((Path(repo_root)/"configs/experiment"/(receipt["experiment"]+".json")).read_bytes())
    original_base = json.loads((Path(repo_root)/"configs/baseline"/(c["baseline_fragment"]+".json")).read_bytes())
    prior_runs, prior_attempts = _joint_original_spend(bound, repo_root=repo_root)
    for row,identity in zip(rows,identities,strict=True):
        require(set(row) == set(identity)|{"planned_speech_audio_seconds"}
                and type(row["planned_speech_audio_seconds"]) is int and row["planned_speech_audio_seconds"] > 0
                and not {row["run_id"],row["fit_run_id"]}.intersection(prior_runs)
                and not {row["attempt_id"],row["fit_attempt_id"]}.intersection(prior_attempts),
                "joint fresh identities reuse original spend or differ in audio allowance")
        cell, = load_campaign_cells(repo_root,row["experiment"])
        d = cell.document
        require(d["cell_id"] == row["cell_id"] and d["run_id"] == row["run_id"]
                and d["attempt_id"] == row["attempt_id"] and d["baseline_fragment"] == row["experiment"]
                and d["model_fragment"] == c["model_fragment"] and d["dataset_fragment"] == c["dataset_fragment"],
                "joint fresh cell differs from full-seed geometry/carrier identity")
        config = compose(repo_root,d["model_fragment"],d["dataset_fragment"],d["baseline_fragment"],row["experiment"])
        member, = [m for m in population["architecture"]["members"] if m["member_id"] == row["member_id"]]
        stage = population_stage_spec(population_pin,repo_root=repo_root,cohort_id=member["cohort_id"],allow_architecture=True)
        policy = json.loads(_read_pin(member["execution_config"],repo_root))
        report = derive_manual_architecture_audio_budget(config.values)
        ep,bp = local_node_documents(original_exp,original_base,policy,identity,
                policy_binding=d["system_text_policy_binding"],population_pin=population_pin,
                cohort_id=member["cohort_id"],stage=stage,basis={},report=report)
        bp.pop("local_node_basis");bp["joint_role_basis"] = mapping["joint_role_basis"]
        ep["stage3_measurement"].update(tuning_roster=original_exp["stage3_measurement"]["read_roster"],
                read_roster=original_exp["stage3_measurement"]["read_roster"],
                independent_validation=False,runtime_adoption=False,learner_export=False)
        actual_exp = json.loads((Path(repo_root)/"configs/experiment"/(row["experiment"]+".json")).read_bytes())
        actual_base = json.loads((Path(repo_root)/"configs/baseline"/(row["experiment"]+".json")).read_bytes())
        for experiment in (ep,actual_exp):experiment["cells"][0].pop("readiness",None)
        actual_base.pop("prepared_phase_supply",None)
        require(ep == actual_exp and bp == actual_base
                and config.values.get("joint_role_basis") == mapping["joint_role_basis"]
                and config.values.get("local_node_basis") is None and config.values.get("architecture_extent") is None,
                "joint composed configuration drifted beyond exact held seed/import projection")
        result.append((row["member_id"],cell,config))
    return result


def require_joint_adaptive_disposition(decision,basis_pin,population,cells,*,repo_root,data_root,stage="generation"):
    """Authenticate only explicit adaptive discovery on the exact original roster."""
    require(decision.get("schema") == "saea-campaign-decision-v1" and decision.get("status") == "decided"
            and 227 in decision.get("owner_decisions",[]) and decision.get("learner_export") is False
            and decision.get("joint_role_basis") == basis_pin,
            "decided owner227 joint admission required")
    bound = require_joint_role_basis(basis_pin,population,repo_root=repo_root,data_root=data_root)
    require(stage in {"generation", "capacity", "natural"}, "unknown joint admission stage")
    disposition = decision.get("adaptive_joint_roster_reuse")
    ids = population["cohorts"][0]["sample_ids"]
    proof_ids = _joint_proof_roster(population, repo_root=repo_root)[1] if stage == "natural" else None
    require([label for label, _, _ in cells] == [m["member_id"] for m in population["architecture"]["members"]],
            "joint adaptive disposition requires the complete ordered family")
    expected = []
    for label,cell,config in cells:
        values = config.values
        measurement = values["stage3_measurement"]
        plan = values["execution_plan"]
        allowed_profiles = {"bounded-discovery-probe", "model-free-check"} if stage == "capacity" else {"bounded-discovery-probe"}
        actual_ids = values["populations"][0]["ids"]
        require(plan.get("execution_profile") in allowed_profiles and plan.get("split_role") == "discovery"
                and measurement.get("claims_benefit") is False and measurement.get("independent_validation") is False
                and measurement.get("runtime_adoption") is False and measurement.get("learner_export") is False
                and measurement.get("tuning_roster") is not None and measurement.get("read_roster") is not None
                and (stage == "natural" or (measurement["tuning_roster"] == measurement["read_roster"] and actual_ids == ids))
                and (stage != "natural" or actual_ids == proof_ids),
                "joint adaptive reuse cannot broaden scope, claim benefit, hide tuning or change roster")
        d=cell.document
        expected.append({"member_id":label,"cell_id":d["cell_id"],"run_id":d["run_id"],"attempt_id":d["attempt_id"],
            "config_hash":config.config_hash,"tuning_roster":measurement["tuning_roster"],
            "read_roster":measurement["read_roster"],"intersection_sample_ids":actual_ids})
    require(isinstance(disposition,dict) and set(disposition) == {
        "schema","root_decision","joint_role_basis","scope","claims_benefit","independent_validation",
        "runtime_adoption","learner_export","members","cumulative_sources","stage"}
        and disposition["stage"] == stage
        and disposition["schema"] == "saea-owner227-adaptive-joint-roster-reuse-v1"
        and disposition["root_decision"] == JOINT_SOURCE_DECISION and disposition["joint_role_basis"] == basis_pin
        and disposition["scope"] == "adaptive-development-discovery-only"
        and all(disposition[k] is False for k in ("claims_benefit","independent_validation","runtime_adoption","learner_export"))
        and disposition["members"] == expected
        and disposition["cumulative_sources"] == bound["cumulative_sources"],
        "exact root-decided complete adaptive overlap disposition required")
    return disposition


JOINT_PROOF_MAP_SCHEMA = "saea-joint-role-import-proof-identity-map-v1"


def _mapped_joint_proof_cells(map_pin,population,population_pin,*,repo_root,data_root,stage):
    """Bind exact complete fresh capacity/natural companions; never arbitrary subsets."""
    import importlib.util
    require(stage in {"capacity","natural"}, "unknown joint proof stage")
    mapping=json.loads(_read_pin(map_pin,repo_root))
    require(isinstance(mapping,dict) and set(mapping) == {
        "schema","stage","experiment_population","joint_role_basis","generation_identity_map","proof_roster","members"}
        and mapping["schema"] == JOINT_PROOF_MAP_SCHEMA and mapping["stage"] == stage
        and mapping["experiment_population"] == population_pin and mapping["proof_roster"] == JOINT_PROOF_ROSTER,
        "joint exact proof identity map scope differs")
    generation_map=json.loads(_read_pin(mapping["generation_identity_map"],repo_root))
    require(generation_map.get("joint_role_basis") == mapping["joint_role_basis"], "joint proof parent map basis differs")
    parents=_mapped_joint_cells(generation_map,population,population_pin,repo_root=repo_root,data_root=data_root)
    rows=mapping["members"]
    require(isinstance(rows,list) and [r.get("member_id") for r in rows] == [r[0] for r in parents],
            "joint proof requires complete ordered controls/A/A/import family")
    path=Path(repo_root)/"scripts/preparation/prepare_manual_audio_recovery.py"
    spec=importlib.util.spec_from_file_location("_joint_existing_preparation",path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    graph_dataset="slurp-speech-native-simple-consumption-n100-graph4-v1"
    graph_view, _ = _joint_proof_roster(population, repo_root=repo_root)
    result=[];runs=[];attempts=[];names=[]
    parent_runs={v for _,c,config in parents for v in (c.document["run_id"],config.values["native_contact_fit"]["run_id"])}
    parent_attempts={v for _,c,config in parents for v in (c.document["attempt_id"],config.values["native_contact_fit"]["attempt_id"])}
    bound = require_joint_role_basis(mapping["joint_role_basis"],population,repo_root=repo_root,data_root=data_root)
    original_runs, original_attempts = _joint_original_spend(bound, repo_root=repo_root)
    parent_runs.update(original_runs); parent_attempts.update(original_attempts)
    for row,(label,parent,parent_config) in zip(rows,parents,strict=True):
        fields={"member_id","experiment","cell_id","run_id","attempt_id","config_hash"}
        if stage == "natural":fields|={"fit_run_id","fit_attempt_id"}
        require(isinstance(row,dict) and set(row) == fields and row["member_id"] == label
                and row["experiment"] == row["cell_id"], "joint proof identity fields differ")
        import re
        require(all(isinstance(row[k],str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*",row[k])
                    for k in fields-{"config_hash"})
                and re.fullmatch(r"[a-f0-9]{64}",row["config_hash"]), "joint proof identity is not path-safe")
        cell,=load_campaign_cells(repo_root,row["experiment"]);c=cell.document
        config=compose(repo_root,c["model_fragment"],c["dataset_fragment"],c["baseline_fragment"],row["experiment"])
        require(config.config_hash == row["config_hash"] and c["cell_id"] == row["cell_id"]
                and c["run_id"] == row["run_id"] and c["attempt_id"] == row["attempt_id"]
                and c["baseline_fragment"] == row["experiment"]
                and config.values.get("joint_role_basis") == mapping["joint_role_basis"],
                "joint proof composed identity/basis differs")
        pc=parent.document
        ep=json.loads((Path(repo_root)/"configs/experiment"/(pc["cell_id"]+".json")).read_bytes())
        bp=json.loads((Path(repo_root)/"configs/baseline"/(pc["baseline_fragment"]+".json")).read_bytes())
        budget={} if stage == "natural" else module.local_capacity_budget(ep,bp,
                    **_joint_knowledge_counts(bp,data_root))
        identity={k:row[k] for k in fields-{"member_id","config_hash"}}
        expected_exp,expected_base=module.local_companion_documents(ep,bp,identity,kind=stage,
            graph_view=graph_view,graph_dataset=graph_dataset,capacity_budget=budget)
        actual_exp=json.loads((Path(repo_root)/"configs/experiment"/(row["experiment"]+".json")).read_bytes())
        actual_base=json.loads((Path(repo_root)/"configs/baseline"/(row["experiment"]+".json")).read_bytes())
        for document in (expected_exp,actual_exp):document["cells"][0].pop("readiness",None)
        actual_base.pop("prepared_phase_supply",None)
        require(expected_exp == actual_exp and expected_base == actual_base,
                "joint proof changed fields outside the exact existing companion projection")
        runs.append(row["run_id"]);attempts.append(row["attempt_id"]);names.append(row["experiment"])
        if stage == "natural":runs.append(row["fit_run_id"]);attempts.append(row["fit_attempt_id"])
        result.append((label,cell,config))
    require(len(set(runs)) == len(runs) and len(set(attempts)) == len(attempts)
            and len(set(names)) == len(names) and not set(runs).intersection(parent_runs)
            and not set(attempts).intersection(parent_attempts), "joint proof repeats generation or proof spend identities")
    return result


def _joint_knowledge_counts(baseline,data_root):
    """Count original released snapshots for the existing pure capacity estimator."""
    from .knowledge import KnowledgeSnapshot
    result={}
    for key,name in (("slot-contracts","slot_value_count"),("intent-boundaries","intent_value_count")):
        pin=baseline["knowledge_stores"][key]["snapshot"]
        snapshot=KnowledgeSnapshot.from_frozen_json(json.loads((Path(data_root)/pin["relpath"]).read_bytes()))
        require(snapshot.content_hash() == pin["sha256"], "joint original capacity snapshot identity differs")
        result[name]=len(snapshot.values)
    return result


def require_joint_proof_registration(values,cell,plans,population,*,repo_root,data_root,stage):
    """Authenticate the separately decided full structural/FIT family after its canonical gate."""
    basis_pin=values["joint_role_basis"]
    require(all(p.get("joint_role_basis") == basis_pin for p in plans), "joint proof plan basis differs")
    pins={json.dumps(p.get("joint_proof_identity_map"),sort_keys=True) for p in plans}
    decisions={json.dumps(p.get("decision_receipt"),sort_keys=True) for p in plans}
    require(len(pins) == len(decisions) == 1 and "null" not in pins|decisions,
            "joint proof pair requires exact map and separate decided root admission")
    map_pin=plans[0]["joint_proof_identity_map"]
    cells=_mapped_joint_proof_cells(map_pin,population,values["experiment_population"],
                repo_root=repo_root,data_root=data_root,stage=stage)
    matches=[(c,config) for label,c,config in cells if label == values["architecture_member"]]
    require(len(matches) == 1 and matches[0][0].document == cell
            and matches[0][1].config_hash == _canonical_hash(values), "joint proof plan names another original member")
    decision=json.loads(_read_pin(plans[0]["decision_receipt"],data_root))
    expected=[]
    for _,c,config in cells:
        expected.append(c.document["run_id"])
        if stage == "natural":expected.append(config.values["native_contact_fit"]["run_id"])
    require(decision.get("joint_proof_identity_map") == map_pin
            and decision.get("experiment_population") == values["experiment_population"]
            and decision.get("eligible_run_ids") == expected and len(set(expected)) == len(expected),
            "joint separate proof admission eligibility differs")
    require_joint_adaptive_disposition(decision,basis_pin,population,cells,
            repo_root=repo_root,data_root=data_root,stage=stage)
