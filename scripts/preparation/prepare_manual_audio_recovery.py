#!/usr/bin/env python3
"""Prepare held audio-recovery identities by re-enveloping unchanged supplied bytes."""
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
    raise RuntimeError("Audio recovery preparation forbids model, tokenizer, scorer and network contacts")


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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("input", "input-sha256", "repo-root", "data-root"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    p = Path(args.input)
    require(hashlib.sha256(p.read_bytes()).hexdigest() == args.input_sha256, "recovery input raw pin differs")
    print(json.dumps(prepare(json.loads(p.read_bytes()), repo_root=args.repo_root, data_root=args.data_root), sort_keys=True))


if __name__ == "__main__":
    main()
