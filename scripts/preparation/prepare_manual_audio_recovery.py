#!/usr/bin/env python3
"""Prepare held recovery/local-node identities with existing immutable supply bytes.

The local schema accepts only root-compiled policies and pinned original proposal
custody. It prepares fresh configurations; it never compiles templates or contacts
a model, tokenizer, scorer or network service.
"""
import argparse
from copy import deepcopy
from dataclasses import asdict
import gc
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
from unittest.mock import patch

from speech_aware_evidence_acquisition.core.config import compose, drop_null_arms
from speech_aware_evidence_acquisition.core.flight.campaign import load_campaign_cells
from speech_aware_evidence_acquisition.core.flight.factory import build_flight_runtime
from speech_aware_evidence_acquisition.core.preparation import digest, load_artifact, prepare_artifact
from speech_aware_evidence_acquisition.rails.architecture_natural_registration import _mapped_execution_cells, _require_prepared_implementation
from speech_aware_evidence_acquisition.rails.experiment_population import population_stage_spec
from speech_aware_evidence_acquisition.rails.system_text_policy import _read_pin, require, verify_system_text_binding


def pin(path, root):
    path, root = Path(path).resolve(), Path(root).resolve()
    require(path.is_relative_to(root), "recovery pin escapes declared root")
    return {"relpath": path.relative_to(root).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write((json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def refuse(*args, **kwargs):
    raise RuntimeError("Manual preparation forbids model, tokenizer, scorer and network contacts")


def source_head(root, expected):
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}
    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args], env=env, text=True).strip()
    require(len(expected) == 40 and git("rev-parse", "HEAD") == expected
            and not git("status", "--porcelain"), "recovery source must be clean at its exact declared commit")


def successor_documents(experiment, baseline, *, suffix, report):
    """Change only fresh spend identity, held admission metadata and derived allowance."""
    require(isinstance(suffix, str) and suffix.startswith("audio-recovery")
            and suffix.endswith("-v1") and all(c.isalnum() or c == "-" for c in suffix),
            "explicit lower-case recovery suffix required")
    require(len(experiment.get("cells", [])) == 1, "one predecessor generation cell required")
    ceiling = report.get("required_integer_audio_seconds")
    require(type(ceiling) is int and ceiling > 0, "pure audio derivation must provide a positive integer ceiling")
    ep, bp = deepcopy(experiment), deepcopy(baseline)
    c = ep["cells"][0]
    old = c["cell_id"]
    require(old.endswith("-v1") and c["run_id"].endswith("-V1"), "versioned predecessor identity required")
    name = old.removesuffix("-v1") + "-" + suffix
    run = c["run_id"].removesuffix("-V1") + "-" + suffix.upper()
    attempt = "attempt-" + name + "-generation"
    fit_run, fit_attempt = run.removesuffix("-V1") + "-FIT-V1", attempt + "-fit"
    ep["experiment_id"] = run
    old_audio = ep["execution_plan"]["planned_speech_audio_seconds"]
    require(type(old_audio) is int and old_audio > 0, "positive integer predecessor audio allowance required")
    ep["execution_plan"]["planned_speech_audio_seconds"] = max(old_audio, ceiling)
    c.update(cell_id=name, run_id=run, attempt_id=attempt, baseline_fragment=name,
             readiness={"state": "held", "reason": "Derived cumulative audio correction; exact root admission and frozen/live gates pending.", "requirements": []})
    bp["native_contact_fit"].update(run_id=fit_run, attempt_id=fit_attempt)
    bp.pop("prepared_phase_supply", None)
    row = dict(member_id=ep["architecture_member"], experiment=name, cell_id=name, run_id=run,
               attempt_id=attempt, fit_run_id=fit_run, fit_attempt_id=fit_attempt,
               planned_speech_audio_seconds=ep["execution_plan"]["planned_speech_audio_seconds"])
    return ep, bp, row


def verified_source_output(receipt, data_root, ids):
    """Retain both original seals and exact full-parent selected output equality."""
    original = json.loads(_read_pin(receipt["prepared_phase_supply"], data_root))
    parent = json.loads(_read_pin(receipt["source_prepared_phase_supply"], data_root))
    output = parent["output"]
    require(parent["output_sha256"] == digest(output)
            and set(output) == {"facets", "values"} and output["facets"] == {}
            and set(output["values"]) == {"perception"}
            and set(ids) <= set(output["values"]["perception"]), "recovery original full-parent seal or coverage differs")
    selected = {"facets": {}, "values": {"perception": {sid: output["values"]["perception"][sid] for sid in ids}}}
    require(original["output_sha256"] == digest(original["output"]) == receipt["output_sha256"]
            and original["output"] == selected, "recovery exact prior selected output seal differs")
    return original


def prepare(spec, *, repo_root, data_root):
    from speech_aware_evidence_acquisition.rails.architecture_audio_budget import derive_manual_architecture_audio_budget
    root, data = Path(repo_root).resolve(), Path(data_root).resolve()
    require(spec.get("schema") == "saea-manual-architecture-audio-recovery-preparation-input-v1",
            "explicit audio-recovery input required")
    source_head(root, spec["source_preparation_commit"])
    worker = Path(spec["predecessor_worker_root"]).resolve()
    source_head(worker, spec["predecessor_source_commit"])
    disposition = json.loads(_read_pin(spec["root_disposition"], data))
    require(disposition.get("schema") == "saea-root-bounded-incident-disposition-v1"
            and str(disposition.get("status", "")).startswith("DECIDED")
            and disposition.get("dispatch_authorized_by_this_record_alone") is False
            and disposition.get("scientific_read_authorized") is False and disposition.get("learner_export") is False
            and disposition.get("original_source") == {"commit": spec["predecessor_source_commit"], "path": str(worker)},
            "exact prospective root incident disposition required")
    _read_pin(disposition["owner_decision"], root)
    _read_pin(disposition["root_cause_receipt"], root)
    package = (root / spec["package_relpath"]).resolve()
    require(package.is_relative_to(root / "docs/readiness") and not package.exists(), "fresh recovery preparation package required")
    population = json.loads(_read_pin(spec["experiment_population"], root))
    stage = population_stage_spec(spec["experiment_population"], repo_root=root,
                                 cohort_id=spec["population_cohort"], allow_architecture=True)
    labels = stage["control_members"] + stage["candidate_members"]
    require(set(spec["preparation_receipts"]) == set(labels), "every exact predecessor preparation receipt required")
    pending, maps = [], []
    with patch.object(socket.socket, "connect", refuse), patch.object(socket.socket, "connect_ex", refuse):
        for label in labels:
            receipt_pin = spec["preparation_receipts"][label]
            receipt = json.loads(_read_pin(receipt_pin, root))
            (cell,) = load_campaign_cells(root, receipt["experiment"])
            c = cell.document
            ep_path = root / "configs/experiment" / (receipt["experiment"] + ".json")
            bp_path = root / "configs/baseline" / (c["baseline_fragment"] + ".json")
            ep_pin, bp_pin = pin(ep_path, root), pin(bp_path, root)
            require(_read_pin(ep_pin, root) == _read_pin(ep_pin, worker)
                    and _read_pin(bp_pin, root) == _read_pin(bp_pin, worker), "predecessor config bytes differ from immutable worker")
            old = compose(root, c["model_fragment"], c["dataset_fragment"], c["baseline_fragment"], receipt["experiment"])
            identity, = [m for m in stage["architecture_members"] if m["member_id"] == label]
            runtime_ids = receipt["runtime_sample_ids"]
            require(receipt["source_policy"] == identity["execution_config"]
                    and len(runtime_ids) == len(set(runtime_ids)) == stage["N"]
                    and set(runtime_ids) == set(stage["sample_ids"]), "predecessor policy or runtime membership differs")
            require(receipt["member_id"] == label and receipt["config_hash"] == old.config_hash
                    and receipt["run_id"] == c["run_id"] and receipt["attempt_id"] == c["attempt_id"]
                    and receipt["configured_sample_ids"] == old.values["populations"][0]["ids"] == stage["sample_ids"]
                    and old.values["experiment_population"] == spec["experiment_population"]
                    and receipt["prepared_phase_supply"] == old.values["prepared_phase_supply"]
                    and type(receipt.get("contacts")) is int and receipt["contacts"] == 0
                    and receipt.get("output_equal") is True and receipt.get("warm_verified") is True
                    and receipt.get("runtime_admission") is False,
                    "predecessor preparation identity differs")
            original = verified_source_output(receipt, data, stage["sample_ids"])
            _require_prepared_implementation(original, worker, old.values)
            report = derive_manual_architecture_audio_budget(old.values)
            ep, bp, row = successor_documents(json.loads(ep_path.read_bytes()), json.loads(bp_path.read_bytes()),
                                             suffix=spec["successor_suffix"], report=report)
            row.update(predecessor_experiment=ep_pin, predecessor_baseline=bp_pin)
            for run in (row["run_id"], row["fit_run_id"]):
                require(all(not (data / folder / run).exists() for folder in ("prepared", "attempts", "runs")), "fresh recovery run already has DATA state")
            for kind in ("experiment", "baseline"):
                require(not (root / "configs" / kind / (row["experiment"] + ".json")).exists(), "successor config already exists")
            maps.append(row)
            pending.append((label, receipt_pin, receipt, ep, bp, row, report))
        require(len({x for m in maps for x in (m["run_id"], m["fit_run_id"])}) == len(maps) * 2
                and len({x for m in maps for x in (m["attempt_id"], m["fit_attempt_id"])}) == len(maps) * 2,
                "recovery spend identities repeat")
        for label, receipt_pin, receipt, ep, bp, row, report in pending:
            name = row["experiment"]
            ep_path, bp_path = root / "configs/experiment" / (name + ".json"), root / "configs/baseline" / (name + ".json")
            save(ep_path, ep); save(bp_path, bp)
            c = ep["cells"][0]
            def runtime():
                return build_flight_runtime(root, data, model=c["model_fragment"], dataset=c["dataset_fragment"],
                    baseline=name, experiment=name, run_id=row["run_id"], attempt_id=row["attempt_id"],
                    runtime_root=Path(spec["runtime_root"]), lock_path=Path(spec["datasets_lock_path"]),
                    campaign_active=False, score_batch=refuse)
            rt = runtime()
            context = rt.preparation_context()
            require(list(context["sample_ids"]) == receipt["runtime_sample_ids"], "recovery runtime order differs")
            policy = drop_null_arms(json.loads(_read_pin(receipt["source_policy"], root)))
            require(all(context["values"].get(k) == v for k, v in policy.items() if k != "what_this_is"), "recovery execution policy changed")
            verify_system_text_binding(context["values"], c["system_text_policy_binding"], repo_root=root, data_root=data)
            original = json.loads(_read_pin(receipt["prepared_phase_supply"], data))
            *_, inputs = rt.phase_supply_artifact_identity()
            supply = data / "prepared" / row["run_id"] / "phase-supply-v1.json"
            prepare_artifact(supply, kind="phase-supply", inputs=inputs, producer=lambda: deepcopy(original["output"]))
            bp["prepared_phase_supply"] = pin(supply, data)
            bp_path.write_text(json.dumps(bp, indent=2, sort_keys=True) + "\n")
            # Only these newly authored config bytes are finalized; old bytes are untouched.
            rt = runtime(); context = rt.preparation_context()
            *_, final_inputs = rt.phase_supply_artifact_identity()
            require(load_artifact(supply, expected_sha256=bp["prepared_phase_supply"]["sha256"], kind="phase-supply", inputs=final_inputs)
                    == original["output"], "recovery exact reused prepared output differs")
            verified = list(rt.verify_prepared_artifacts())
            require(list(context["sample_ids"]) == receipt["runtime_sample_ids"], "recovery verified runtime order differs")
            record = {**receipt, "member_id": label, "experiment": name, "baseline": name,
                      "run_id": row["run_id"], "attempt_id": row["attempt_id"], "config_hash": rt._composed.config_hash,
                      "execution_plan": asdict(context["execution_plan"]), "prepared_phase_supply": bp["prepared_phase_supply"],
                      "prepared_source_commit": spec["source_preparation_commit"], "predecessor_preparation_receipt": receipt_pin,
                      "predecessor_prepared_phase_supply": receipt["prepared_phase_supply"], "audio_budget_derivation": report,
                      "strict_prepared_artifacts": verified, "contacts": 0, "output_equal": True,
                      "warm_verified": True, "runtime_admission": False, "status": "HELD AUDIO RECOVERY; ROOT REGISTRATION PENDING"}
            save(package / (label + "-generation-prepared-v1.json"), record)
            print(label + ": exact output reuse and strict warm verification PASS; zero contacts", flush=True)
            del rt, context, original
            gc.collect()
        identity_map = dict(schema="saea-manual-architecture-execution-identity-map-v1",
                            experiment_population=spec["experiment_population"],
                            architecture_extent=json.loads(_read_pin(maps[0]["predecessor_baseline"], root))["architecture_extent"],
                            members=maps)
        map_path = package / "execution-identity-map-v1.json"
        save(map_path, identity_map)
        map_pin = pin(map_path, root)
        _mapped_execution_cells(map_pin, population, spec["experiment_population"], identity_map["architecture_extent"], repo_root=root)
        for _, receipt_pin, receipt, _, _, _, _ in pending:
            _read_pin(receipt_pin, root)
            verified_source_output(receipt, data, stage["sample_ids"])
        _read_pin(spec["root_disposition"], data)
        summary = dict(schema="saea-manual-architecture-audio-recovery-preparation-v1", status="PREPARED_HELD_NOT_ADMITTED",
                       experiment_population=spec["experiment_population"], source_preparation_commit=spec["source_preparation_commit"],
                       execution_identity_map=map_pin, root_disposition=spec["root_disposition"],
                       preparation_receipts={label: pin(package / (label + "-generation-prepared-v1.json"), root) for label in labels},
                       contacts={"model": 0, "tokenizer": 0, "scorer": 0}, runtime_admission=False, read_authorized=False)
        save(package / "preparation-summary-v1.json", summary)
        return summary




def local_companion_documents(generation_experiment, generation_baseline, row, *, kind, graph_view,
                              graph_dataset, capacity_budget):
    """Derive fresh proof cells from one held local policy; keep original data/knowledge."""
    from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
    from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config
    from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash
    ep, bp = deepcopy(generation_experiment), deepcopy(generation_baseline)
    bp.pop("prepared_phase_supply", None)
    native = load_native_episode_config({**bp, "carrier_lock_key": "slurp"}, default_phase_program(bp["policy"]))
    require(kind in {"capacity", "graph", "natural"}, "unknown local node proof companion")
    c = ep["cells"][0]
    c.update(cell_id=row["cell_id"], baseline_fragment=row["experiment"], run_id=row["run_id"],
             attempt_id=row["attempt_id"], readiness={"state": "held", "reason": "Fresh local node proof; exact root registration pending.",
                                                   "requirements": []})
    ep["experiment_id"] = row["run_id"]
    if kind == "capacity":
        require(row["run_id"].endswith("-FIT-V1"), "local capacity must use a separately named FIT identity")
        cap = capacity_budget["contact_cap"]
        c["allowed_execution_stages"] = ["check", "prepare-supply", "prompt-fit"]
        bp.pop("native_contact_fit", None)
    else:
        ids = [item["sample_id"] for item in graph_view["items"]]
        require(len(ids) == len(set(ids)) == 4
                and ids == ep["populations"][0]["ids"][:4], "local proof must preserve the existing graph4 prefix")
        cap = len(ids) * native.max_contacts
        c["dataset_fragment"] = graph_dataset
        c["allowed_execution_stages"] = ["check", "prepare-supply"] if kind == "graph" else ["check", "prepare-supply", "worker"]
        ep["populations"] = [{"dataset_fragment": graph_dataset, "ids": ids}]
        ep["population"].update(count=len(ids), split_identity_hash=split_identity_hash(prefixed("slurp", ids)),
                                roster_receipt="docs/readiness/2026-10-07-slurp-simple-consumption-n100-preparation-v1/graph-roster-v1.json")
        ep["split_id"] = graph_view["split_name"]
        ep["stage3_measurement"].update(rows=len(ids), read_roster=graph_view["split_name"])
        import math
        ep["execution_plan"]["planned_speech_audio_seconds"] = math.ceil(math.fsum(
            item["audio_seconds"] * native.max_contacts for item in graph_view["items"]))
        if kind == "graph":
            bp.pop("native_contact_fit", None)
        else:
            bp["native_contact_fit"].update(run_id=row["fit_run_id"], attempt_id=row["fit_attempt_id"],
                contact_cap=cap * (generation_baseline["native_contact_fit"]["contact_cap"]
                                   // generation_experiment["execution_plan"]["planned_model_calls"]))
    ep["execution_plan"]["planned_model_calls"] = cap
    if kind == "natural":
        ep["family_budget"] = {"complete_system_trajectories": len(ids), "generation_calls_cap": cap,
                              "actual_request_fit_endpoint_cap": bp["native_contact_fit"]["contact_cap"],
                              "official_complete_scoring_jobs": 0}
    else:
        ep["family_budget"] = {"complete_system_trajectories": 0, "generation_calls_cap": 0,
                              "official_complete_scoring_jobs": 0, "tokenizer_endpoint_cap": cap if kind == "capacity" else 0}
    return ep, bp


def local_capacity_budget(experiment, baseline, *, slot_value_count, intent_value_count):
    """Supply explicit carrier and experiment profile to the shared pure estimator."""
    from speech_aware_evidence_acquisition.analysis.native_graph_capacity import native_graph_capacity_budget
    profile = experiment["native_graph_capacity_profile"]
    return native_graph_capacity_budget({**baseline, "carrier_lock_key": "slurp",
        "native_graph_capacity_profile": profile}, slot_value_count=slot_value_count,
        intent_value_count=intent_value_count, graph_rows=4, media_parts=1, profile=profile)


def prepare_local_companions(spec, *, root, data, pending, original, package):
    """Prepare configured graph4/capacity/natural4 with the same supply wrapper path."""
    from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot
    graph_dataset = spec["graph_dataset_fragment"]
    require(graph_dataset == "slurp-speech-native-simple-consumption-n100-graph4-v1",
            "local node must reuse the original graph4 dataset fragment")
    graph_view = json.loads((root / "configs/dataset" / (graph_dataset + ".json")).read_bytes())
    all_runs, all_attempts, all_names = [], [], []
    companions = []
    for identity, row, ep, bp, _ in pending:
        member = spec["member_specs"][identity["member_id"]]
        require(set(member["companions"]) == {"capacity", "graph", "natural"},
                "local node complete configured proof companions required")
        counts = {}
        for key in ("slot-contracts", "intent-boundaries"):
            binding = bp["knowledge_stores"][key]["snapshot"]
            snapshot = KnowledgeSnapshot.from_frozen_json(json.loads((data / binding["relpath"]).read_bytes()))
            require(snapshot.content_hash() == binding["sha256"], "local node source snapshot identity differs")
            counts[key] = len(snapshot.values)
        budget = local_capacity_budget(ep, bp, slot_value_count=counts["slot-contracts"],
                                      intent_value_count=counts["intent-boundaries"])
        for kind, proof in member["companions"].items():
            keys = {"experiment", "cell_id", "run_id", "attempt_id"}
            if kind == "natural":
                keys |= {"fit_run_id", "fit_attempt_id"}
            require(set(proof) == keys and proof["experiment"] == proof["cell_id"],
                    "local node companion identity fields differ")
            import re
            require(all(isinstance(v, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", v)
                        for v in proof.values()), "local node companion identity is not path-safe")
            pp, pb = local_companion_documents(ep, bp, proof, kind=kind, graph_view=graph_view,
                                               graph_dataset=graph_dataset, capacity_budget=budget)
            all_runs.extend([proof["run_id"]] + ([proof["fit_run_id"]] if kind == "natural" else []))
            all_attempts.extend([proof["attempt_id"]] + ([proof["fit_attempt_id"]] if kind == "natural" else []))
            all_names.append(proof["experiment"])
            for run in all_runs[-(2 if kind == "natural" else 1):]:
                require(all(not (data / folder / run).exists() for folder in ("prepared", "attempts", "runs")),
                        "local node proof run already exists")
            for attempt in all_attempts[-(2 if kind == "natural" else 1):]:
                require(not (data / "attempts" / attempt).exists(), "local node proof attempt already exists")
            for fragment in ("baseline", "experiment"):
                require(not (root / "configs" / fragment / (proof["experiment"] + ".json")).exists(),
                        "local node proof config already exists")
            companions.append((identity, kind, proof, pp, pb, budget))
    generation_runs = [x for _, row, _, _, _ in pending for x in (row["run_id"], row["fit_run_id"])]
    generation_attempts = [x for _, row, _, _, _ in pending for x in (row["attempt_id"], row["fit_attempt_id"])]
    generation_names = [row["experiment"] for _, row, _, _, _ in pending]
    require(len(set(all_runs + generation_runs)) == len(all_runs + generation_runs)
            and len(set(all_attempts + generation_attempts)) == len(all_attempts + generation_attempts)
            and len(set(all_names + generation_names)) == len(all_names + generation_names),
            "local node proof and generation identities duplicate")
    if spec.get("joint_role_basis") is not None:
        from speech_aware_evidence_acquisition.rails.architecture_natural_registration import require_joint_role_basis, _joint_original_spend
        from speech_aware_evidence_acquisition.rails.experiment_population import load_population_config
        population = load_population_config(spec["experiment_population"], repo_root=root, allow_architecture=True)
        bound = require_joint_role_basis(spec["joint_role_basis"], population, repo_root=root, data_root=data)
        original_runs, original_attempts = _joint_original_spend(bound, repo_root=root)
        require(not set(all_runs + generation_runs).intersection(original_runs)
                and not set(all_attempts + generation_attempts).intersection(original_attempts),
                "joint preparation cannot reuse original generation/FIT spend")
    records = {}
    for identity, kind, proof, ep, bp, budget in companions:
        name, label = proof["experiment"], identity["member_id"]
        exp_path, base_path = root / "configs/experiment" / (name + ".json"), root / "configs/baseline" / (name + ".json")
        save(exp_path, ep); save(base_path, bp)
        c = ep["cells"][0]
        def runtime():
            return build_flight_runtime(root, data, model=c["model_fragment"], dataset=c["dataset_fragment"],
                baseline=name, experiment=name, run_id=c["run_id"], attempt_id=c["attempt_id"],
                runtime_root=Path(spec["runtime_root"]), lock_path=Path(spec["datasets_lock_path"]),
                campaign_active=False, score_batch=refuse)
        rt = runtime(); context = rt.preparation_context()
        ids = ep["populations"][0]["ids"]
        output = {"facets": {}, "values": {"perception": {
            sid: original["output"]["values"]["perception"][sid] for sid in ids}}}
        *_, inputs = rt.phase_supply_artifact_identity()
        path = data / "prepared" / proof["run_id"] / "phase-supply-v1.json"
        prepare_artifact(path, kind="phase-supply", inputs=inputs, producer=lambda: deepcopy(output))
        bp["prepared_phase_supply"] = pin(path, data)
        base_path.write_text(json.dumps(bp, indent=2, sort_keys=True) + "\n")
        rt = runtime(); context = rt.preparation_context()
        *_, inputs = rt.phase_supply_artifact_identity()
        require(load_artifact(path, expected_sha256=bp["prepared_phase_supply"]["sha256"],
                kind="phase-supply", inputs=inputs) == output, "local node proof supplied output changed")
        verified = list(rt.verify_prepared_artifacts())
        record = dict(member_id=label, kind=kind, experiment=name, baseline=name,
            run_id=proof["run_id"], attempt_id=proof["attempt_id"], config_hash=rt._composed.config_hash,
            execution_plan=asdict(context["execution_plan"]), source_policy=identity["execution_config"],
            policy_binding=c["system_text_policy_binding"], configured_sample_ids=ids,
            runtime_sample_ids=list(context["sample_ids"]), prepared_phase_supply=bp["prepared_phase_supply"],
            output_sha256=digest(output), output_equal=True, warm_verified=True, contacts=0,
            prepared_source_commit=spec["source_preparation_commit"], runtime_admission=False,
            pure_capacity_budget=budget if kind == "capacity" else None,
            strict_prepared_artifacts=verified, **({"joint_role_basis":spec["joint_role_basis"]}
                if spec.get("joint_role_basis") is not None else {"local_node_basis":spec["local_node_basis"]}))
        receipt_path = package / (label + "-" + kind + "-prepared-v1.json")
        save(receipt_path, record)
        records.setdefault(label, {})[kind] = pin(receipt_path, root)
        del rt, context
        gc.collect()
    return records

def prepare_local_node_panel(spec, *, repo_root, data_root):
    """Re-envelope a configured local panel on original N100; never register or contact."""
    from speech_aware_evidence_acquisition.rails.local_node_panel import (
        SELECTOR, REVIEWER_SELECTOR, MAP_SCHEMA, require_local_node_basis, require_local_identities, local_node_documents,
    )
    from speech_aware_evidence_acquisition.rails.experiment_population import load_population_config
    from speech_aware_evidence_acquisition.rails.architecture_audio_budget import derive_manual_architecture_audio_budget
    root, data = Path(repo_root).resolve(), Path(data_root).resolve()
    joint_mode = spec.get("schema") == "saea-joint-role-import-preparation-input-v1"
    require(joint_mode or spec.get("schema") == "saea-local-node-panel-preparation-input-v1",
            "explicit local or joint preparation input required")
    source_head(root, spec["source_preparation_commit"])
    if not joint_mode:
        require(spec.get("joint_role_basis") is None, "unsolicited joint preparation basis refused")
        require(spec.get("target_role") == spec["local_node_basis"].get("target_role"), "local target role and basis differ")
    else:
        require(spec.get("local_node_basis") is None and spec.get("target_role") is None,
                "joint preparation cannot inherit local-role topology")
    package = (root / spec["package_relpath"]).resolve()
    require(package.is_relative_to(root / "docs/readiness") and package != root / "docs/readiness"
            and not package.exists(), "fresh local node preparation package required")
    population = load_population_config(spec["experiment_population"], repo_root=root, allow_architecture=True)
    if joint_mode:
        from speech_aware_evidence_acquisition.rails.architecture_natural_registration import require_joint_role_basis, JOINT_MAP_SCHEMA
        joint_bound = require_joint_role_basis(spec["joint_role_basis"],population,repo_root=root,data_root=data)
        receipt = joint_bound["receipt"]
    else:
        receipt = require_local_node_basis(spec["local_node_basis"], population, repo_root=root, data_root=data)
    stage = population_stage_spec(spec["experiment_population"], repo_root=root,
                                 cohort_id=spec["population_cohort"], allow_architecture=True)
    labels = stage["control_members"] + stage["candidate_members"]
    require(set(spec["member_specs"]) == set(labels), "local node complete configured membership required")
    source_cell, = load_campaign_cells(root, receipt["experiment"])
    c = source_cell.document
    old = compose(root, c["model_fragment"], c["dataset_fragment"], c["baseline_fragment"], receipt["experiment"])
    require(old.config_hash == receipt["config_hash"]
            and old.values["populations"][0]["ids"] == stage["sample_ids"]
            and old.values["prepared_phase_supply"] == receipt["prepared_phase_supply"],
            "local node original composed preparation identity differs")
    source_exp = json.loads((root / "configs/experiment" / (receipt["experiment"] + ".json")).read_bytes())
    source_base = json.loads((root / "configs/baseline" / (c["baseline_fragment"] + ".json")).read_bytes())
    original = verified_source_output(receipt, data, stage["sample_ids"])
    rows = [dict(member_id=label, **spec["member_specs"][label]["identity"]) for label in labels]
    require_local_identities(rows, source_cell=c, source_fit=source_base["native_contact_fit"])
    pending = []
    for identity in stage["architecture_members"]:
        label = identity["member_id"]
        row = rows[labels.index(label)]
        member = spec["member_specs"][label]
        require(set(member) == {"identity", "policy_binding", "companions"}
                and member["policy_binding"]["bundle_id"] == identity["base_bundle_id"],
                "local node policy binding differs from configured member")
        policy = drop_null_arms(json.loads(_read_pin(identity["execution_config"], root)))
        values = {**deepcopy(old.values), **{k: v for k, v in policy.items() if k != "what_this_is"}}
        report = derive_manual_architecture_audio_budget(values)
        require(report["sample_count"] == stage["N"], "local node duration roster differs")
        ep, bp = local_node_documents(source_exp, source_base, policy, row,
            policy_binding=member["policy_binding"], population_pin=spec["experiment_population"],
            cohort_id=spec["population_cohort"], stage=stage, basis={} if joint_mode else spec["local_node_basis"], report=report)
        if joint_mode:
            bp.pop("local_node_basis");bp["joint_role_basis"] = spec["joint_role_basis"]
            ep["stage3_measurement"].update(tuning_roster=source_exp["stage3_measurement"]["read_roster"],
                read_roster=source_exp["stage3_measurement"]["read_roster"],
                independent_validation=False,runtime_adoption=False,learner_export=False)
        verify_system_text_binding(bp, member["policy_binding"], repo_root=root, data_root=data)
        for run in (row["run_id"], row["fit_run_id"]):
            require(all(not (data / folder / run).exists() for folder in ("prepared", "attempts", "runs")),
                    "local node fresh run already has DATA state")
        for attempt in (row["attempt_id"], row["fit_attempt_id"]):
            require(not (data / "attempts" / attempt).exists(), "local node fresh attempt already exists")
        for kind in ("experiment", "baseline"):
            require(not (root / "configs" / kind / (row["experiment"] + ".json")).exists(),
                    "local node fresh config already exists")
        pending.append((identity, row, ep, bp, report))
    with (patch.object(socket.socket, "connect", refuse),
          patch.object(socket.socket, "connect_ex", refuse),
          patch("socket.create_connection", refuse)):
        companion_receipts = prepare_local_companions(spec, root=root, data=data, pending=pending, original=original, package=package)
    map_rows, receipts = [], {}
    with (patch.object(socket.socket, "connect", refuse),
          patch.object(socket.socket, "connect_ex", refuse),
          patch("socket.create_connection", refuse)):
        for identity, row, ep, bp, report in pending:
            label, name = identity["member_id"], row["experiment"]
            exp_path, base_path = root / "configs/experiment" / (name + ".json"), root / "configs/baseline" / (name + ".json")
            save(exp_path, ep); save(base_path, bp)
            def runtime():
                return build_flight_runtime(root, data, model=c["model_fragment"], dataset=c["dataset_fragment"],
                    baseline=name, experiment=name, run_id=row["run_id"], attempt_id=row["attempt_id"],
                    runtime_root=Path(spec["runtime_root"]), lock_path=Path(spec["datasets_lock_path"]),
                    campaign_active=False, score_batch=refuse)
            rt = runtime()
            context = rt.preparation_context()
            require(list(context["sample_ids"]) == receipt["runtime_sample_ids"], "local node runtime order changed")
            *_, inputs = rt.phase_supply_artifact_identity()
            supply = data / "prepared" / row["run_id"] / "phase-supply-v1.json"
            prepare_artifact(supply, kind="phase-supply", inputs=inputs, producer=lambda: deepcopy(original["output"]))
            bp["prepared_phase_supply"] = pin(supply, data)
            # Only this new held baseline is finalized. Historical bytes are untouched.
            base_path.write_text(json.dumps(bp, indent=2, sort_keys=True) + "\n")
            rt = runtime(); context = rt.preparation_context()
            *_, final_inputs = rt.phase_supply_artifact_identity()
            require(load_artifact(supply, expected_sha256=bp["prepared_phase_supply"]["sha256"],
                    kind="phase-supply", inputs=final_inputs) == original["output"], "local node reused supply output changed")
            verified = list(rt.verify_prepared_artifacts())
            verify_system_text_binding(context["values"], ep["cells"][0]["system_text_policy_binding"],
                                       repo_root=root, data_root=data)
            record = {**receipt, "member_id": label, "experiment": name, "baseline": name,
                "run_id": row["run_id"], "attempt_id": row["attempt_id"], "config_hash": rt._composed.config_hash,
                "source_policy": identity["execution_config"], "policy_binding": ep["cells"][0]["system_text_policy_binding"],
                "execution_plan": asdict(context["execution_plan"]), "prepared_phase_supply": bp["prepared_phase_supply"],
                "prepared_source_commit": spec["source_preparation_commit"],
                "predecessor_preparation_receipt": (json.loads(_read_pin(spec["joint_role_basis"],root))["source_preparation_receipt"]
                    if joint_mode else spec["local_node_basis"]["source_preparation_receipt"]),
                "predecessor_prepared_phase_supply": receipt["prepared_phase_supply"],
                "configured_sample_ids": stage["sample_ids"], "runtime_sample_ids": list(context["sample_ids"]),
                "generation_cap": stage["member_generation_contacts_caps"][label],
                "fit_endpoint_cap": stage["member_fit_endpoints_caps"][label],
                "audio_budget_derivation": report, **({"joint_role_basis":spec["joint_role_basis"]} if joint_mode else {"local_node_basis":spec["local_node_basis"]}),
                "strict_prepared_artifacts": verified, "contacts": 0, "output_equal": True, "warm_verified": True,
                "runtime_admission": False, "status": "HELD LOCAL NODE; FRESH PROOFS AND ROOT REGISTRATION PENDING",
                "architecture_extent": None, "pure_capacity_budget": None, "draft_plans": {}}
            if joint_mode:
                capacity_record = json.loads(_read_pin(companion_receipts[label]["capacity"], root))
                record["source_prepared_phase_supply"] = capacity_record["prepared_phase_supply"]
                record["status"] = "HELD JOINT IMPORT; FRESH PROOFS AND ROOT REGISTRATION PENDING"
            save(package / (label + "-generation-prepared-v1.json"), record)
            receipts[label] = pin(package / (label + "-generation-prepared-v1.json"), root)
            map_rows.append({**row, "planned_speech_audio_seconds": report["required_integer_audio_seconds"]})
            del rt, context
            gc.collect()
    mapping = dict(schema=JOINT_MAP_SCHEMA if joint_mode else MAP_SCHEMA,
                   experiment_population=spec["experiment_population"], architecture_extent=None, members=map_rows,
                   **({"joint_role_basis":spec["joint_role_basis"]} if joint_mode else {"local_node_basis":spec["local_node_basis"]}))
    map_path = package / "execution-identity-map-v1.json"
    save(map_path, mapping)
    _mapped_execution_cells(pin(map_path, root), population, spec["experiment_population"], None, repo_root=root,
                            **({"data_root":data} if joint_mode else {}))
    if joint_mode:
        require_joint_role_basis(spec["joint_role_basis"],population,repo_root=root,data_root=data)
    else:
        require_local_node_basis(spec["local_node_basis"], population, repo_root=root, data_root=data)
    summary = dict(schema="saea-joint-role-import-preparation-v1" if joint_mode else "saea-local-node-panel-preparation-v1", status="PREPARED_HELD_NOT_ADMITTED",
        architecture_proof="manual-architecture-n20-v1" if joint_mode else SELECTOR if spec["target_role"] == "solver" else REVIEWER_SELECTOR,
        experiment_population=spec["experiment_population"],
        **({"joint_role_basis":spec["joint_role_basis"]} if joint_mode else {"local_node_basis":spec["local_node_basis"]}),
        source_preparation_commit=spec["source_preparation_commit"],
        execution_identity_map=pin(map_path, root), preparation_receipts=receipts,
        companion_preparation_receipts=companion_receipts,
        population_budget=stage["population_budget"], contacts={"model": 0, "tokenizer": 0, "scorer": 0},
        runtime_admission=False, read_authorized=False)
    if joint_mode:
        from speech_aware_evidence_acquisition.rails.architecture_natural_registration import JOINT_PROOF_MAP_SCHEMA, JOINT_PROOF_ROSTER
        proof_maps={}
        for stage_name in ("capacity","natural"):
            proof_rows=[]
            for label in labels:
                record=json.loads(_read_pin(companion_receipts[label][stage_name],root))
                declared=spec["member_specs"][label]["companions"][stage_name]
                proof_rows.append(dict(member_id=label,config_hash=record["config_hash"],**declared))
            proof_map=dict(schema=JOINT_PROOF_MAP_SCHEMA,stage=stage_name,experiment_population=spec["experiment_population"],
                joint_role_basis=spec["joint_role_basis"],generation_identity_map=pin(map_path,root),
                proof_roster=JOINT_PROOF_ROSTER,members=proof_rows)
            proof_path=package/(stage_name+"-identity-map-v1.json")
            save(proof_path,proof_map);proof_maps[stage_name]=pin(proof_path,root)
        summary["joint_proof_identity_maps"]=proof_maps
        summary["cumulative_source_summary"] = [{"kind":x["kind"],"sha256":x["sha256"],"sample_count":len(x["sample_ids"])}
                                                for x in joint_bound["cumulative_sources"]]
    save(package / "preparation-summary-v1.json", summary)
    return summary

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("input", "input-sha256", "repo-root", "data-root"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    p = Path(args.input)
    require(hashlib.sha256(p.read_bytes()).hexdigest() == args.input_sha256, "recovery input raw pin differs")
    document = json.loads(p.read_bytes())
    operation = prepare_local_node_panel if document.get("schema") in {"saea-local-node-panel-preparation-input-v1","saea-joint-role-import-preparation-input-v1"} else prepare
    print(json.dumps(operation(document, repo_root=args.repo_root, data_root=args.data_root), sort_keys=True))


if __name__ == "__main__":
    main()
