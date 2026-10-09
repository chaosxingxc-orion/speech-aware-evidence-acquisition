#!/usr/bin/env python3
"""Author a fresh root-only manual comparison package; never register or dispatch.

Finalize approved ready metadata before composing. Preserve original receipts and
experiment bytes. Reverify existing supply without reconstructing its outputs.
Default plans remain prospective unsigned; READ always remains DRAFT.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import re
import subprocess
from unittest.mock import patch

from speech_aware_evidence_acquisition.analysis.native_graph_rehearsal import (
    require_prepared_graph_artifacts,
)
from speech_aware_evidence_acquisition.analysis.system_text_update import (
    load_additional_contrast_document, require_additional_contrast_binding,
    validate_additional_paired_contrasts,
)
from speech_aware_evidence_acquisition.core.config import compose
from speech_aware_evidence_acquisition.core.flight.campaign import load_campaign_cells
from speech_aware_evidence_acquisition.core.flight.factory import build_flight_runtime
from speech_aware_evidence_acquisition.core.flight.cli import load_campaign_plan
from speech_aware_evidence_acquisition.rails.experiment_population import (
    population_stage_spec,
)
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    _read_pin,
    require,
)
from speech_aware_evidence_acquisition.analysis import (
    system_architecture_read as reader,
)


from speech_aware_evidence_acquisition.rails.reward_links import RewardProjection, SLURP_NATIVE_FIELDS


ROOT = Path(__file__).resolve().parents[2]


def official_slurp_projection():
    """Preserve official native counts and the established SLURP endpoints."""
    return RewardProjection(
        "manual-architecture-official-counts-v1",
        "slurp-slu-official-train",
        ("port_micro.slu_f1", "port_micro.intent_accuracy"),
        SLURP_NATIVE_FIELDS,
    ).as_json()


def serialized(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def raw_pin(path, root):
    path = Path(path).resolve()
    require(path.is_relative_to(root), "authoring pin escapes its declared root")
    return {
        "relpath": path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(serialized(value))


@contextmanager
def no_contacts():
    def refuse(*args, **kwargs):
        raise RuntimeError("Manual authoring refuses network/model/tokenizer transport")

    with (
        patch("socket.socket.connect", refuse),
        patch("socket.socket.connect_ex", refuse),
        patch("socket.create_connection", refuse),
    ):
        yield


def _member_inputs(spec, stage, repo_root):
    labels = stage["control_members"] + stage["candidate_members"]
    require(
        set(spec["preparation_receipts"]) == set(labels),
        "every configured preparation receipt required",
    )
    members = []
    profiles = []
    for label in labels:
        receipt_pin = spec["preparation_receipts"][label]
        receipt = json.loads(_read_pin(receipt_pin, repo_root))
        (cell,) = load_campaign_cells(repo_root, receipt["experiment"])
        c = cell.document
        configured = compose(
            repo_root,
            c["model_fragment"],
            c["dataset_fragment"],
            c["baseline_fragment"],
            receipt["experiment"],
        )
        from speech_aware_evidence_acquisition.rails.architecture_audio_budget import require_manual_architecture_audio_budget
        require_manual_architecture_audio_budget(configured.values)
        profiles.append(deepcopy(configured.values["system_search_measurement"]))
        runtime = receipt["runtime_sample_ids"]
        require(
            receipt.get("member_id") == label
            and receipt.get("config_hash") == configured.config_hash
            and receipt.get("run_id") == c["run_id"]
            and receipt.get("attempt_id") == c["attempt_id"]
            and receipt.get("configured_sample_ids")
            == configured.values["populations"][0]["ids"]
            == stage["sample_ids"]
            and len(runtime) == len(set(runtime)) == stage["N"]
            and set(runtime) == set(stage["sample_ids"])
            and type(receipt.get("contacts")) is int
            and receipt["contacts"] == 0
            and receipt.get("output_equal") is True
            and receipt.get("warm_verified") is True
            and receipt.get("runtime_admission") is False
            and receipt.get("prepared_phase_supply")
            == configured.values["prepared_phase_supply"],
            "fresh preparation/configuration/order/output identity differs",
        )
        (identity,) = [
            m for m in stage["architecture_members"] if m["member_id"] == label
        ]
        require(
            receipt.get("source_policy") == identity["execution_config"],
            "preparation policy differs",
        )
        c = deepcopy(c)
        c["experiment"] = receipt["experiment"]
        fit = configured.values["native_contact_fit"]
        members.append((label, receipt_pin, receipt, c, fit, identity))
    require(
        len({c["run_id"] for _, _, _, c, _, _ in members}) == len(members)
        and len({fit["run_id"] for _, _, _, _, fit, _ in members}) == len(members),
        "duplicate member spend identity",
    )
    require(
        profiles and all(p == profiles[0] for p in profiles),
        "manual family measurement profiles differ before authoring",
    )
    return members, profiles[0]


def validate_inputs(spec, *, repo_root, data_root):
    """Validate raw-pinned source metadata before any ready/configuration write."""
    require(
        spec.get("schema") == "saea-manual-architecture-authoring-input-v1"
        and spec.get("architecture_proof") in reader.SELECTORS,
        "explicit manual authoring input required",
    )
    package = (repo_root / spec["package_relpath"]).resolve()
    require(
        package.is_relative_to(repo_root / "docs/readiness")
        and package != repo_root / "docs/readiness"
        and not package.exists(),
        "authoring needs a fresh readiness package",
    )
    require(
        "frozen_source_commit" not in spec,
        "pre-freeze authoring must not invent a self-referential worker commit",
    )
    require(
        all(
            isinstance(spec[k], str) and spec[k].strip()
            for k in (
                "family_id",
                "read_run_id",
                "ready_reason",
                "registered_at_utc",
                "queue_owner",
            )
        ),
        "explicit family, READ, ready reason and authoring metadata required",
    )
    stage = population_stage_spec(
        spec["experiment_population"],
        repo_root=repo_root,
        cohort_id=spec["population_cohort"],
        allow_architecture=True,
    )
    members, measurement_profile = _member_inputs(spec, stage, repo_root)
    decision = json.loads(_read_pin(spec["decision_receipt"], data_root))
    require(spec.get("execution_identity_map") == decision.get("execution_identity_map"),
            "authoring and root execution identity maps differ")
    require(spec.get("natural_source_compatibility") == decision.get("natural_source_compatibility"),
            "authoring natural source compatibility differs")
    if spec.get("natural_source_compatibility") is not None:
        from speech_aware_evidence_acquisition.rails.natural_source_compatibility import validate_compatibility
        prerequisite = spec["natural_prerequisite"]
        qualified = json.loads(_read_pin(prerequisite["qualification"], data_root))
        validate_compatibility(json.loads(_read_pin(spec["natural_source_compatibility"], data_root)),
            prerequisite, qualified, decision, repo_root=repo_root, data_root=data_root)
    if spec["architecture_proof"] in reader.LOCAL_NODE_SELECTORS:
        from speech_aware_evidence_acquisition.rails.local_node_panel import require_local_node_basis
        population = json.loads(_read_pin(spec["experiment_population"], repo_root))
        require(spec.get("local_node_basis") == decision.get("local_node_basis")
                and spec.get("natural_source_compatibility") is None,
                "local node authoring requires its exact basis and fresh proof")
        require_local_node_basis(spec["local_node_basis"], population, repo_root=repo_root, data_root=data_root)
    else:
        require(spec.get("local_node_basis") is None, "local node basis requires its named opt-in selector")
    joint_pin = spec.get("joint_role_basis")
    if joint_pin is not None:
        from speech_aware_evidence_acquisition.rails.architecture_natural_registration import require_joint_role_basis
        require(spec["architecture_proof"] == reader.SELECTOR
                and decision.get("joint_role_basis") == joint_pin
                and spec.get("natural_source_compatibility") is None,
                "joint authoring requires exact generic basis and fresh proof")
        population = json.loads(_read_pin(spec["experiment_population"], repo_root))
        require_joint_role_basis(joint_pin,population,repo_root=repo_root,data_root=data_root)
        require(all(receipt.get("joint_role_basis") == joint_pin
                    and compose(repo_root,c["model_fragment"],c["dataset_fragment"],c["baseline_fragment"],c["experiment"]).values.get("joint_role_basis") == joint_pin
                    for _,_,receipt,c,_,_ in members),
                "joint complete preparation/configuration basis differs")
    else:
        require(decision.get("joint_role_basis") is None
                and all(receipt.get("joint_role_basis") is None for _,_,receipt,_,_,_ in members),
                "unsolicited joint authoring custody refused")
    extent = spec.get("architecture_extent")
    if spec.get("execution_identity_map") is not None:
        from speech_aware_evidence_acquisition.rails.architecture_natural_registration import _mapped_execution_cells
        population = json.loads(_read_pin(spec["experiment_population"], repo_root))
        mapped = _mapped_execution_cells(spec["execution_identity_map"], population,
                                        spec["experiment_population"], extent, repo_root=repo_root,
                                         **({"data_root":data_root} if joint_pin is not None else {}))
        require([(label, c.document["cell_id"], configured.config_hash) for label, c, configured in mapped]
                == [(label, c["cell_id"], receipt["config_hash"]) for label, _, receipt, c, _, _ in members],
                "authoring preparation differs from its complete pinned execution identity map")
    require(decision.get("architecture_extent") == extent
            and all(receipt.get("architecture_extent") == extent
                    for _, _, receipt, _, _, _ in members),
            "authoring configured or root decision extent differs")
    require(all(compose(repo_root, c["model_fragment"], c["dataset_fragment"],
                        c["baseline_fragment"], c["experiment"]).values.get("architecture_extent") == extent
                for _, _, _, c, _, _ in members),
            "authoring compiled configuration extent differs")
    if extent is not None:
        require(spec["architecture_proof"] == reader.FIXED_ROSTER_SELECTOR,
                "authoring extended configuration requires fixed-roster selector")
        from speech_aware_evidence_acquisition.rails.architecture_natural_registration import _fixed400_basis
        population = json.loads(_read_pin(spec["experiment_population"], repo_root))
        _fixed400_basis({"architecture_extent": extent}, {role: {
            "architecture_extent": extent, "architecture_proof": spec["architecture_proof"]}
            for role in ("generation", "fit")}, population, repo_root=repo_root)
    else:
        require(spec["architecture_proof"] != reader.FIXED_ROSTER_SELECTOR,
                "authoring fixed-roster selector requires explicit extent")
    eligible = [
        run for _, _, _, c, fit, _ in members for run in (c["run_id"], fit["run_id"])
    ]
    require(
        decision.get("schema") == "saea-campaign-decision-v1"
        and decision.get("status") == "decided"
        and 227 in decision.get("owner_decisions", [])
        and decision.get("learner_export") is False
        and decision.get("eligible_run_ids") == eligible
        and len(set(eligible)) == len(eligible)
        and decision.get("experiment_population") == spec["experiment_population"]
        and decision.get("capacity_prerequisite") == spec["capacity_prerequisite"]
        and decision.get("natural_prerequisite") == spec["natural_prerequisite"]
        and all(
            receipt.get("prepared_source_commit")
            == decision.get("source_preparation_commit")
            for _, _, receipt, _, _, _ in members
        )
        and re.fullmatch(
            r"[0-9a-f]{40}", str(decision.get("source_preparation_commit"))
        )
        is not None,
        "exact decided root family, preparation source or prerequisite binding differs",
    )
    for prerequisite in (spec["capacity_prerequisite"], spec["natural_prerequisite"]):
        require(
            set(prerequisite) == {"registration", "qualification"},
            "exact prerequisite pin pair required",
        )
        for p in prerequisite.values():
            _read_pin(p, data_root)
    template = load_additional_contrast_document(_read_pin(spec["analysis_template"], repo_root))
    require(
        template["experiment_population"] == spec["experiment_population"]
        and template["population_cohort"] == spec["population_cohort"]
        and template["sample_ids"] == stage["sample_ids"]
        and template["population_budget"] == stage["population_budget"],
        "held analysis template differs",
    )
    validate_additional_paired_contrasts(
        template, {"architecture": (*stage["control_members"], stage["candidate_members"])}
    )
    for pin in (
        template["analysis_roster"],
        spec["stratum_metadata"],
        spec["owner_decision"],
    ):
        _read_pin(pin, repo_root)
    roster = json.loads(_read_pin(template["analysis_roster"], repo_root))
    require(
        [r["sample_id"] for r in roster["items"]] == stage["sample_ids"],
        "analysis construction roster differs before authoring",
    )
    strata = json.loads(_read_pin(spec["stratum_metadata"], repo_root))["items"]
    require(
        len({r["sample_id"] for r in strata}) == len(strata),
        "duplicate stratum metadata",
    )
    indexed = {r["sample_id"]: r for r in strata}
    require(
        all(sid in indexed for sid in stage["sample_ids"])
        and all(
            indexed[r["sample_id"]]["utterance_id"] == r["utterance_id"]
            for r in roster["items"]
        ),
        "analysis stratum identity differs before authoring",
    )
    require(spec["read_run_id"] not in eligible, "READ cannot reuse a spend identity")
    require(
        type(spec.get("process_memory_diagnostics")) is bool,
        "explicit boolean process_memory_diagnostics required",
    )
    guard = spec["process_guard"]
    require(
        set(guard) == {"start_gib", "floor_gib", "wait_seconds", "stable_samples"}
        and all(
            type(guard[k]) in (int, float) and guard[k] > 0
            for k in ("start_gib", "floor_gib")
        )
        and guard["start_gib"] >= guard["floor_gib"]
        and all(
            type(guard[k]) is int and guard[k] > 0
            for k in ("wait_seconds", "stable_samples")
        ),
        "explicit process memory/wait policy required",
    )
    require(
        decision.get("resource_policy")
        == {**guard, "process_memory_diagnostics": spec["process_memory_diagnostics"]},
        "process memory/wait/instrumentation input differs from exact decided resource policy",
    )
    return package, stage, members, decision, template, measurement_profile


def finalize_member(spec, member, decision, *, package, repo_root, data_root):
    """Set final ready bytes once, then require unchanged cached output and order."""
    label, receipt_pin, original, cell, fit, identity = member
    experiment = cell["experiment"]
    path = repo_root / "configs/experiment" / (experiment + ".json")
    original_bytes = path.read_bytes()
    snapshot = package / (label + "-original-experiment-v1.json")
    with snapshot.open("xb") as stream:
        stream.write(original_bytes)
    document = json.loads(original_bytes)
    (selected,) = [c for c in document["cells"] if c["cell_id"] == cell["cell_id"]]
    require(
        len(document["cells"]) == 1,
        "manual authoring requires one exact cell per fragment",
    )
    selected["readiness"] = {
        "state": "ready",
        "reason": spec["ready_reason"],
        "requirements": [
            {
                "kind": "preparation",
                **original["prepared_phase_supply"],
                "reason": "Exact reused prepared supply; strict warm identity verified before plans.",
            },
            {
                "kind": "decision",
                **spec["decision_receipt"],
                "expected_decision_id": decision["decision_id"],
                "reason": "Root decided this exact configured generation/FIT family before contact.",
            },
        ],
    }
    path.write_bytes(serialized(document))
    runtime = build_flight_runtime(
        repo_root,
        data_root,
        model=cell["model_fragment"],
        dataset=cell["dataset_fragment"],
        baseline=cell["baseline_fragment"],
        experiment=experiment,
        run_id=cell["run_id"],
        attempt_id=cell["attempt_id"],
        runtime_root=Path(spec["runtime_root"]),
        lock_path=Path(spec["datasets_lock_path"]),
        campaign_active=False,
    )
    require_prepared_graph_artifacts(runtime)
    context = runtime.preparation_context()
    verified = list(runtime.verify_prepared_artifacts())
    require(
        list(context["sample_ids"]) == original["runtime_sample_ids"]
        and context["values"]["prepared_phase_supply"]
        == original["prepared_phase_supply"],
        "final ready configuration changed prepared supply or production order",
    )
    _read_pin(original["prepared_phase_supply"], data_root)
    successor = {
        **original,
        "original_preparation_receipt": receipt_pin,
        "original_experiment": raw_pin(snapshot, repo_root),
        "final_experiment": raw_pin(path, repo_root),
        "config_hash": runtime._composed.config_hash,
        "execution_plan": asdict(context["execution_plan"]),
        "generation_cap": context["execution_plan"].planned_model_calls,
        "fit_endpoint_cap": context["values"]["native_contact_fit"]["contact_cap"],
        "status": "READY METADATA FINALIZED; exact root registration remains separate",
        "strict_prepared_artifacts": verified,
        "finalization_source_commit": None,
        "source_resolution": "PENDING EXTERNAL ROOT FROZEN-LAUNCH BINDING",
        "final_ready_metadata": selected["readiness"],
        "contacts": 0,
        "output_equal": True,
        "warm_verified": True,
        "runtime_admission": False,
    }
    successor_path = package / (label + "-preparation-receipt-final-v1.json")
    write_new(successor_path, successor)
    return selected, context, successor, raw_pin(successor_path, repo_root)


def author(spec, *, repo_root, data_root, root_countersign_plans=False):
    """Author package only; no ledger, queue control, attempt, READ or dispatch write."""
    repo_root, data_root = Path(repo_root).resolve(), Path(data_root).resolve()
    package, stage, members, decision, template, measurement_profile = validate_inputs(
        spec, repo_root=repo_root, data_root=data_root
    )
    package.mkdir(parents=True)
    bindings, expected, queue, campaign, checks, plan_rows = {}, {}, [], [], [], []
    from speech_aware_evidence_acquisition.rails.architecture_natural_registration import (
        require_architecture_n20_registration,
    )

    with no_contacts():
        for order, member in enumerate(members, 1):
            label, _, _, _, _, identity = member
            cell, context, receipt, receipt_pin = finalize_member(
                spec,
                member,
                decision,
                package=package,
                repo_root=repo_root,
                data_root=data_root,
            )
            require(
                context["values"]["system_search_measurement"] == measurement_profile,
                "warm member measurement profile differs from composed family",
            )
            plan = context["execution_plan"]
            fit = context["values"]["native_contact_fit"]
            bound_fit = replace(
                plan,
                run_id=fit["run_id"],
                attempt_id=fit["attempt_id"],
                planned_model_calls=fit["contact_cap"],
            )
            plans = []
            plan_pins = {}
            for role, bound in (("generation", plan), ("fit", bound_fit)):
                document = {
                    "schema": f"saea-registered-{role}-plan-v1",
                    "plan_role": role,
                    "status": "ROOT COUNTERSIGNED BEFORE CONTACT; explicit root authoring"
                    if root_countersign_plans
                    else "PROSPECTIVE UNSIGNED; root must countersign before contact",
                    "registered_at_utc": spec["registered_at_utc"],
                    "architecture_proof": spec["architecture_proof"],
                    "architecture_member": label,
                    "cell": cell["cell_id"],
                    "experiment": member[3]["experiment"],
                    "composed_config_hash": receipt["config_hash"],
                    "experiment_population": spec["experiment_population"],
                    "population_cohort": spec["population_cohort"],
                    "population_budget": stage["population_budget"],
                    "configured_sample_ids": stage["sample_ids"],
                    "runtime_sample_ids": receipt["runtime_sample_ids"],
                    "execution_plan": asdict(bound),
                    "policy_binding": cell["system_text_policy_binding"],
                    "prepared_phase_supply": receipt["prepared_phase_supply"],
                    "preparation_receipt": receipt_pin,
                    "capacity_prerequisite": spec["capacity_prerequisite"],
                    "natural_prerequisite": spec["natural_prerequisite"],
                    "decision_receipt": spec["decision_receipt"],
                    "official_score_jobs": 1,
                    "learner_export": False,
                    "measurement_profile": context["values"][
                        "system_search_measurement"
                    ],
                    "read_run_id": spec["read_run_id"],
                }
                if spec["architecture_proof"] == reader.FIXED_ROSTER_SELECTOR:
                    document["architecture_extent"] = deepcopy(spec["architecture_extent"])
                if spec["architecture_proof"] in reader.LOCAL_NODE_SELECTORS:
                    document["local_node_basis"] = deepcopy(spec["local_node_basis"])
                if spec.get("natural_source_compatibility") is not None:
                    document["natural_source_compatibility"] = deepcopy(spec["natural_source_compatibility"])
                if spec.get("joint_role_basis") is not None:
                    document["joint_role_basis"] = deepcopy(spec["joint_role_basis"])
                if spec.get("execution_identity_map") is not None:
                    document["execution_identity_map"] = deepcopy(spec["execution_identity_map"])
                plans.append(document)
                target = package / (label + "-" + role + "-plan-registered-v1.json")
                write_new(target, document)
                plan_pins[role] = raw_pin(target, repo_root)
                plan_rows.append(
                    {
                        "label": label,
                        "role": role,
                        "plan": plan_pins[role],
                        "execution_plan": asdict(bound),
                    }
                )
            # This is the existing natural4 prospective convention: candidate status
            # exists only in memory unless root explicitly selected authoring above.
            prospective = [
                {
                    **p,
                    "status": "ROOT COUNTERSIGNED BEFORE CONTACT; in-memory prospective validation only",
                }
                for p in plans
            ]
            checked = require_architecture_n20_registration(
                context["values"],
                cell,
                prospective,
                repo_root=repo_root,
                data_root=data_root,
            )
            require(
                checked["member_id"] == label
                and checked["generation_cap"]
                == stage["member_generation_contacts_caps"][label]
                and checked["fit_cap"] == stage["member_fit_endpoints_caps"][label]
                and checked["runtime_sample_ids"] == receipt["runtime_sample_ids"],
                "shared pair result differs",
            )
            expected[label] = plan.run_id
            bindings[label] = {
                "run_id": plan.run_id,
                "attempt_id": plan.attempt_id,
                "config_hash": receipt["config_hash"],
                "bundle_id": identity["base_bundle_id"],
                "experiment": member[3]["experiment"],
                "registered_plans": plan_pins,
                "runtime_sample_ids": receipt["runtime_sample_ids"],
            }
            campaign.append(
                {"experiment": member[3]["experiment"], "cell": cell["cell_id"]}
            )
            guard = spec["process_guard"]
            queue.append(
                {
                    "order": order,
                    "short": spec["family_id"] + "-" + label,
                    "kind": "cell",
                    "experiment": member[3]["experiment"],
                    "cell": cell["cell_id"],
                    "campaign_plan": None,
                    "run_id": plan.run_id,
                    "fit_run_id": fit["run_id"],
                    "gen_attempt_id": plan.attempt_id,
                    "smoke_experiment": None,
                    "smoke_cell": None,
                    "smoke_run_id": None,
                    "smoke_attempt_id": None,
                    "expected_rows": stage["N"],
                    "contacts_per_row": len(identity["active_roles"]),
                    "ceiling_per_row": identity["model_per_trajectory"],
                    "notool": False,
                    "owner": spec["queue_owner"],
                    "process_memory_diagnostics": spec["process_memory_diagnostics"],
                    "process_start_gib": guard["start_gib"],
                    "process_floor_gib": guard["floor_gib"],
                    "process_start_wait_seconds": guard["wait_seconds"],
                    "process_start_stable_samples": guard["stable_samples"],
                    "experiment_population": spec["experiment_population"],
                    "population_cohort": spec["population_cohort"],
                    "population_budget": stage["population_budget"],
                }
            )
            checks.append(
                {
                    "member": label,
                    "shared_pair": checked,
                    "preparation_receipt": receipt_pin,
                    "final_config_hash": receipt["config_hash"],
                }
            )
    wrapper = {
        "schema": "saea-manual-architecture-analysis-intent-v1",
        "architecture_proof": spec["architecture_proof"],
        "family_id": spec["family_id"],
        "read_id": spec["read_run_id"],
        "experiment_population": spec["experiment_population"],
        "population_cohort": spec["population_cohort"],
        "sample_ids": stage["sample_ids"],
        "population_budget": stage["population_budget"],
        "ordered_member_labels": list(expected),
        "expected_members": expected,
        "member_bindings": bindings,
        "measurement_profile": deepcopy(measurement_profile),
        "rows_per_member": stage["N"],
        "official_score_jobs_cap": len(expected),
        "learner_export": False,
    }
    recipe = {
        k: deepcopy(template[k])
        for k in (
            "schema",
            "analysis_roster",
            "resampling",
            "endpoint",
            "scientific_claims",
        )
    }
    recipe.update(
        architecture_proof=spec["architecture_proof"],
        family_id=spec["family_id"],
        run_ids={"read": spec["read_run_id"]},
        status="DRAFT_ROOT_READ_NOT_COUNTERSIGNED",
        experiment_population=spec["experiment_population"],
        population_cohort=spec["population_cohort"],
        population_budget=stage["population_budget"],
        sample_ids=stage["sample_ids"],
        expected_members=expected,
        measurement_profile=deepcopy(measurement_profile),
        required_rows_per_member=stage["N"],
        score_jobs=len(expected),
        learner_export=False,
        runtime_sample_ids={m: b["runtime_sample_ids"] for m, b in bindings.items()},
        comparison_groups={
            "architecture": [*stage["control_members"], stage["candidate_members"]]
        },
        capacity_prerequisite=spec["capacity_prerequisite"],
        natural_prerequisite=spec["natural_prerequisite"],
    )
    if spec["architecture_proof"] in reader.LOCAL_NODE_SELECTORS:
        wrapper["local_node_basis"] = deepcopy(spec["local_node_basis"])
        recipe["local_node_basis"] = deepcopy(spec["local_node_basis"])
    if spec["architecture_proof"] == reader.FIXED_ROSTER_SELECTOR:
        wrapper["architecture_extent"] = deepcopy(spec["architecture_extent"])
        recipe["architecture_extent"] = deepcopy(spec["architecture_extent"])
    if spec.get("natural_source_compatibility") is not None:
        wrapper["natural_source_compatibility"] = deepcopy(spec["natural_source_compatibility"])
        recipe["natural_source_compatibility"] = deepcopy(spec["natural_source_compatibility"])
    if spec.get("joint_role_basis") is not None:
        wrapper["joint_role_basis"] = deepcopy(spec["joint_role_basis"])
        recipe["joint_role_basis"] = deepcopy(spec["joint_role_basis"])
    if spec.get("execution_identity_map") is not None:
        wrapper["execution_identity_map"] = deepcopy(spec["execution_identity_map"])
        recipe["execution_identity_map"] = deepcopy(spec["execution_identity_map"])
    if "additional_paired_contrasts" in template:
        wrapper["additional_paired_contrasts"] = deepcopy(template["additional_paired_contrasts"])
        recipe["additional_paired_contrasts"] = deepcopy(template["additional_paired_contrasts"])
    source_code = {
        "reader": raw_pin(
            repo_root / "scripts/analysis/system_text_pilot_read.py", repo_root
        ),
        "analyzer": raw_pin(
            repo_root
            / "src/speech_aware_evidence_acquisition/analysis/system_architecture_read.py",
            repo_root,
        ),
    }
    if "additional_paired_contrasts" in template:
        for name in ("system_text_update", "paired", "bootstrap", "null_calibration"):
            source_code[name] = raw_pin(
                repo_root / ("src/speech_aware_evidence_acquisition/analysis/" + name + ".py"), repo_root
            )
    wrapper.update(
        status="HELD; source-unresolved immutable pre-freeze analysis intent",
        analysis_definition=deepcopy(recipe),
        supplement_definition={
            "schema": "saea-manual-architecture-analysis-supplement-v1",
            "owner_decision": spec["owner_decision"],
            "stratum_metadata": spec["stratum_metadata"],
            "projection": official_slurp_projection(),
            "resampling": template["resampling"],
            "source_code": source_code,
        },
        decision_receipt=spec["decision_receipt"],
    )
    intent_path = package / "manual-architecture-analysis-intent-v1.json"
    write_new(intent_path, wrapper)
    recipe.update(
        schema="saea-manual-architecture-analysis-intent-recipe-v1",
        analysis_intent=raw_pin(intent_path, repo_root),
        source_resolution="PENDING EXTERNAL ROOT FROZEN-LAUNCH BINDING; not executable scientific READ",
    )
    recipe_path = package / "analysis-recipe-intent-v1.json"
    write_new(recipe_path, recipe)
    campaign_path = package / "campaign-plan-v1.json"
    write_new(campaign_path, {"schema": "saea-campaign-plan-v1", "cells": campaign})
    load_campaign_plan(repo_root, campaign_path)
    write_new(package / "queue-v1.json", queue)
    write_new(
        package / "root-read-draft-v1.json",
        {
            "status": "DRAFT ROOT COUNTERSIGNATURE PENDING",
            "run_id": spec["read_run_id"],
            "execution_profile": "model-free-check",
            "split_role": "discovery",
            "planned_model_calls": 0,
            "recipe": raw_pin(recipe_path, repo_root),
            "expected_members": expected,
            "complete_family_required": True,
            "optimizer_export": False,
            "read_authorized": False,
        },
    )
    write_new(
        package / "exposure-rows-authoring-draft-v1.json",
        {
            "status": "DRAFT NOT INSERTED INTO LEDGER",
            "plans": plan_rows,
            "read_run_id": spec["read_run_id"],
            "read_recipe": raw_pin(recipe_path, repo_root),
        },
    )
    write_new(
        package / "authoring-validation-v1.json",
        {
            "status": "OFFLINE AUTHORING ONLY",
            "members": checks,
            "original_inputs": spec,
            "persisted_root_plan_countersignatures": root_countersign_plans,
            "root_read_signed": False,
            "runtime_dispatch": False,
            "exposure_ledger_changed": False,
            "contacts": 0,
        },
    )
    (package / "README.md").write_text(
        "# Manual architecture prospective package\n\n"
        "Root-only pre-freeze authoring; READ remains DRAFT. The worker contains immutable analysis intent, not a self-pinned source commit. Resolve the final wrapper, recipe and supplement only in a separate root analysis checkout after the raw-pinned external frozen-launch receipt establishes the actual worker commit. Never commit that successor back into the worker. All members require exact exposure, frozen source, live gates and complete unique official scores. "
        "Preserve original receipts and experiment snapshots. Never edit ready metadata after the final config hashes. "
        "No dispatch, task-quality read or learner export was performed by authoring.\n"
    )
    return {
        "package": package.relative_to(repo_root).as_posix(),
        "members": list(expected),
        "population_budget": stage["population_budget"],
        "contacts": 0,
        "read_authorized": False,
    }


def _frozen_identity(worker_root):
    """Read the existing detached worker identity; never modify its checkout."""

    def git(*args):
        return subprocess.check_output(
            ["git", "-C", str(worker_root), *args], text=True
        ).strip()

    commit = git("rev-parse", "HEAD")
    require(
        re.fullmatch(r"[0-9a-f]{40}", commit) is not None,
        "frozen worker Git commit is missing",
    )
    require(
        not git("status", "--porcelain", "--untracked-files=no"),
        "frozen worker has changed tracked source bytes",
    )
    return commit


def resolve_analysis(spec, *, repo_root, data_root, frozen_worker_root):
    """Resolve only source identity after freeze, in a separate analysis checkout.

    The unchanged reader still requires the exact manifest study_commit. Root must
    bind this successor recipe to its exact READ row before any scientific read.
    """
    repo_root, data_root = Path(repo_root).resolve(), Path(data_root).resolve()
    worker = Path(frozen_worker_root).resolve()
    require(
        repo_root != worker and not repo_root.is_relative_to(worker),
        "resolved analysis must remain outside the immutable worker checkout",
    )
    require(
        spec.get("schema") == "saea-manual-architecture-analysis-resolution-input-v1",
        "explicit post-freeze resolution input required",
    )
    package = (repo_root / spec["package_relpath"]).resolve()
    require(
        package.is_relative_to(repo_root / "docs/readiness")
        and package != repo_root / "docs/readiness"
        and not package.exists(),
        "analysis resolution needs a fresh readiness package",
    )
    intent_raw = _read_pin(spec["analysis_intent"], repo_root)
    require(
        _read_pin(spec["analysis_intent"], worker) == intent_raw,
        "analysis intent differs from immutable worker bytes",
    )
    intent = load_additional_contrast_document(intent_raw)
    require(
        intent.get("schema") == "saea-manual-architecture-analysis-intent-v1"
        and intent.get("architecture_proof") in reader.SELECTORS
        and "source_commit" not in intent
        and all("source_commit" not in b for b in intent["member_bindings"].values()),
        "frozen intent must be explicitly source-unresolved",
    )
    binding = json.loads(_read_pin(spec["frozen_launch_binding"], data_root))
    commit = _frozen_identity(worker)
    require(
        binding.get("schema") == "saea-root-frozen-launch-binding-v1"
        and binding.get("status") == "decided"
        and 227 in binding.get("owner_decisions", [])
        and binding.get("worker_commit") == commit
        and Path(binding.get("worker_root", "")).resolve() == worker
        and binding.get("admission_sha256") == intent["decision_receipt"]["sha256"],
        "exact external root frozen-launch source or admission binding differs",
    )
    _read_pin(intent["decision_receipt"], data_root)
    queue_path = Path(spec["analysis_intent"]["relpath"]).parent / "queue-v1.json"
    queue_raw = (worker / queue_path).read_bytes()
    require(
        hashlib.sha256(queue_raw).hexdigest() == binding.get("queue_sha256")
        and (repo_root / queue_path).read_bytes() == queue_raw,
        "frozen queue differs from root launch binding or analysis checkout",
    )
    definition = intent["analysis_definition"]
    supplement = intent["supplement_definition"]
    require_additional_contrast_binding(definition, intent)
    validate_additional_paired_contrasts(definition, definition.get("comparison_groups", {}))
    if "additional_paired_contrasts" in definition:
        require(content_hash(definition["resampling"]) == content_hash(supplement["resampling"]),
                "additional paired contrast immutable recipe/supplement resampling differs")
    RewardProjection.from_json(supplement["projection"])
    require(
        intent.get("measurement_profile") == definition.get("measurement_profile")
        and "measurement_profile" in intent,
        "frozen registration measurement profile differs from analysis definition",
    )
    pins = [
        intent["experiment_population"],
        definition["analysis_roster"],
        supplement["owner_decision"],
        supplement["stratum_metadata"],
        *supplement["source_code"].values(),
    ]
    for member in intent["member_bindings"].values():
        for plan_pin in member["registered_plans"].values():
            plan_raw = _read_pin(plan_pin, worker)
            require(
                _read_pin(plan_pin, repo_root) == plan_raw,
                "registered plan succession changed",
            )
            plan = json.loads(plan_raw)
            receipt_raw = _read_pin(plan["preparation_receipt"], worker)
            require(
                _read_pin(plan["preparation_receipt"], repo_root) == receipt_raw,
                "final preparation receipt succession changed",
            )
            receipt = json.loads(receipt_raw)
            pins.extend(
                [
                    receipt["original_preparation_receipt"],
                    receipt["original_experiment"],
                    receipt["final_experiment"],
                    receipt["source_policy"],
                ]
            )
        (cell,) = load_campaign_cells(worker, member["experiment"])
        c = cell.document
        composed = compose(
            worker,
            c["model_fragment"],
            c["dataset_fragment"],
            c["baseline_fragment"],
            member["experiment"],
        )
        require(
            composed.config_hash == member["config_hash"],
            "frozen composed member differs",
        )
        for kind in ("model", "dataset", "baseline"):
            pins.append(
                raw_pin(
                    worker / "configs" / kind / (c[kind + "_fragment"] + ".json"),
                    worker,
                )
            )
    for pin in pins:
        require(
            _read_pin(pin, worker) == _read_pin(pin, repo_root),
            "post-freeze analysis source differs from immutable intent dependency",
        )
    registration = {
        k: deepcopy(v)
        for k, v in intent.items()
        if k
        not in {
            "status",
            "analysis_definition",
            "supplement_definition",
            "decision_receipt",
        }
    }
    registration["schema"] = reader.REGISTRATION
    registration["source_commit"] = commit
    registration["measurement_profile"] = deepcopy(definition["measurement_profile"])
    for member in registration["member_bindings"].values():
        member["source_commit"] = commit
    registration["registration_sha256"] = content_hash(registration)
    package.mkdir(parents=True)
    wrapper_path = package / "manual-architecture-registration-v1.json"
    write_new(wrapper_path, registration)
    recipe = deepcopy(definition)
    recipe["manual_architecture_registration"] = raw_pin(wrapper_path, repo_root)
    recipe_path = package / "analysis-recipe-v1.json"
    write_new(recipe_path, recipe)
    resolution_path = package / "source-resolution-v1.json"
    write_new(
        resolution_path,
        {
            "schema": "saea-manual-architecture-source-resolution-v1",
            "status": "SOURCE RESOLVED; root READ remains DRAFT",
            "analysis_intent": spec["analysis_intent"],
            "frozen_launch_binding": spec["frozen_launch_binding"],
            "worker_commit": commit,
            "successor_recipe": raw_pin(recipe_path, repo_root),
            "comparisons_changed": False,
            "contacts": 0,
            "read_authorized": False,
        },
    )
    supplement = deepcopy(supplement)
    supplement.update(
        recipe=raw_pin(recipe_path, repo_root),
        registration=raw_pin(wrapper_path, repo_root),
        source_resolution=raw_pin(resolution_path, repo_root),
    )
    write_new(package / "analysis-supplement-v1.json", supplement)
    write_new(
        package / "root-read-draft-v1.json",
        {
            "status": "DRAFT ROOT COUNTERSIGNATURE PENDING",
            "run_id": registration["read_id"],
            "execution_profile": "model-free-check",
            "split_role": "discovery",
            "planned_model_calls": 0,
            "recipe": raw_pin(recipe_path, repo_root),
            "frozen_analysis_intent": spec["analysis_intent"],
            "expected_members": registration["expected_members"],
            "read_authorized": False,
            "optimizer_export": False,
        },
    )
    return {
        "package": package.relative_to(repo_root).as_posix(),
        "worker_commit": commit,
        "contacts": 0,
        "read_authorized": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--input-sha256", required=True)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--root-countersign-plans", action="store_true")
    parser.add_argument("--resolve-analysis", action="store_true")
    parser.add_argument("--frozen-worker-root", type=Path)
    args = parser.parse_args()
    raw = args.input.read_bytes()
    require(
        hashlib.sha256(raw).hexdigest() == args.input_sha256,
        "authoring input hash differs",
    )
    require(
        args.input.resolve().is_relative_to(args.data_root.resolve() / "coordination"),
        "root authoring input must remain in DATA coordination",
    )
    with no_contacts():
        if args.resolve_analysis:
            require(
                args.frozen_worker_root is not None and not args.root_countersign_plans,
                "post-freeze resolution requires only a frozen worker, never plan countersigning",
            )
            result = resolve_analysis(
                json.loads(raw),
                repo_root=args.repo_root,
                data_root=args.data_root,
                frozen_worker_root=args.frozen_worker_root,
            )
        else:
            require(
                args.frozen_worker_root is None,
                "worker source belongs only to post-freeze resolution",
            )
            result = author(
                json.loads(raw),
                repo_root=args.repo_root,
                data_root=args.data_root,
                root_countersign_plans=args.root_countersign_plans,
            )
    require(
        args.input.read_bytes() == raw, "root authoring input changed during authoring"
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
