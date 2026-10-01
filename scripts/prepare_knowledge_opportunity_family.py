#!/usr/bin/env python3
"""Prepare metadata and HELD configurations through the shared module compiler.

No model, tool, scoring or service contact. Existing outputs must match exactly;
this script never flips readiness or edits an exposure/attempt record.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from speech_aware_evidence_acquisition.data.runtime_subset import build_runtime_subset
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.knowledge_stores import load_knowledge_store_binding
from speech_aware_evidence_acquisition.rails.consumption_module import compile_module, resolve_carrier_hooks

RECORD = "docs/readiness/2026-10-01-slurp-knowledge-opportunity-v1/owner-decisions.md"
STEM = "slurp-native-stage3-knowledge-opportunity"
AGREEMENT = "SAEA-SLURP-KNOWLEDGE-OPPORTUNITY-R01C-AGREEMENT-V1"


def write_identical(path, document):
    payload = (json.dumps(document, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode()
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError(f"Refuse to replace different prepared bytes: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)


def prepare(repo, data_root):
    baseline_dir = repo / "configs/baseline"
    common = json.loads((baseline_dir / "slurp-native-stage3-system-common-r01c-v1.json").read_text())
    template = json.loads((baseline_dir / "slurp-native-stage3-module-comp1b-dev2000-added-baseline-v1.json").read_text())
    parent = json.loads((repo / "configs/dataset/slurp-speech-native-stage3-construction-r01c.json").read_text())
    subset, subset_receipt = build_runtime_subset(parent, seed=20261001, count=400, name="STAGE3-KNOWLEDGE-OPPORTUNITY-R01C400")
    binding = load_knowledge_store_binding(common, data_root=data_root)
    # Match the existing agreement builder's recording-independent exclusion.
    utterance = lambda sid: ":".join(sid.split(":")[:3])
    population = {utterance(i["sample_id"]) for i in parent["items"]}
    store_audit = {}
    for store_id, store in binding.stores.items():
        sources = {sid for value in store.snapshot.values for sid in value.source_sample_ids}
        if any(len(sid.split(":")) < 3 for sid in sources):
            raise ValueError(f"Unverifiable source identity in {store_id}")
        overlap = population.intersection(utterance(sid) for sid in sources)
        if overlap:
            raise ValueError(f"Source leakage in {store_id}: {len(overlap)} utterances")
        store_audit[store_id] = {"snapshot_sha256": store.snapshot.content_hash(),
            "source_ids": len(sources), "overlapping_utterances": len(overlap),
            "values": len(store.snapshot.values)}
    package = repo / "docs/readiness/2026-10-01-slurp-knowledge-opportunity-v1"
    receipt_path = repo / "docs/receipts/rosters/slurp-knowledge-opportunity-r01c400-v1.json"
    write_identical(receipt_path, subset_receipt)
    write_identical(repo / "configs/dataset/slurp-speech-native-knowledge-opportunity-r01c400-v1.json", subset)
    write_identical(package / "source-binding.json", {"schema": "saea-knowledge-opportunity-sources-v1",
        "roster_sha256": subset["runtime_view_sha256"], "binding_sha256": binding.binding_sha256,
        "stores": store_audit, "contacts": {"model": 0, "tool": 0, "gpu": 0, "scorer": 0}})
    block = copy.deepcopy(template["native_episode"]["consumption_module"])
    agreement_pin = {"kind": "sealed-agreement", "relpath": f"prepared/{AGREEMENT}/agreement.jsonl",
        "sha256": "0"*64, "tool_contact_ledger_row": AGREEMENT,
        "embedded_signal": "Pending source-isolated R01C agreement preparation through the shared builder. No runtime authority."}
    agreement_receipt_path = data_root / f"prepared/{AGREEMENT}/receipt.json"
    if agreement_receipt_path.exists():
        receipt = json.loads(agreement_receipt_path.read_text())
        artifact = data_root / agreement_pin["relpath"]
        rows = [json.loads(line) for line in artifact.read_text().splitlines()]
        source = receipt["derived_from"]
        if (receipt["artifact_id"] != AGREEMENT or any(receipt["contacts"].values())
                or receipt["artifact"]["rows"] != subset["count"]
                or source["split_identity_hash"] != subset["split_identity_hash"]
                or source["vote_snapshot_sha256"] != binding.store("train-exemplars").snapshot.content_hash()
                or source["target_snapshot_sha256"] != binding.store("intent-boundaries").snapshot.content_hash()
                or len(rows) != subset["count"]
                or {row["id"] for row in rows} != {row["sample_id"] for row in subset["items"]}
                or hashlib.sha256(artifact.read_bytes()).hexdigest() != receipt["artifact"]["sha256"]):
            raise ValueError("Agreement source, roster or artifact hash mismatch")
        agreement_pin.update(sha256=receipt["artifact"]["sha256"],
            embedded_signal="Derived, source-excluded TRAIN exemplar vote shares for the exact seeded F1 roster; existing sealed speech vectors, zero model/encoder/GPU contacts.")
    for component in block["components"]:
        if component["component_id"] == "agree-vote-seed":
            component["params"]["agreement_source"] = agreement_pin
    exemplar = common["knowledge_stores"]["train-exemplars"]
    block["components"].append({"component_id": "construction-store-binding", "state": "on",
        "admitted_by": RECORD, "record": RECORD,
        "params": {"store_id": "train-exemplars", "snapshot": exemplar["snapshot"], "release": exemplar["release"]}})
    for arm, mode in (("a", None), ("b", "reread"), ("c", "targeted")):
        current = copy.deepcopy(block)
        if mode:
            current["components"].append({"component_id": "knowledge-consumption-opportunity", "state": "on",
                "admitted_by": "Owner-approved bounded exploration only; no effectiveness admission",
                "record": RECORD, "params": {"mode": mode, "store_id": "slot-contracts",
                    "reviewer_template": "probes/slurp_native_role_reviewer_slot_issues_v1.txt",
                    "planner_template": "probes/slurp_native_role_planner_slot_lookup_v1.txt"}})
        compiled = compile_module(current, resolve_carrier_hooks("slurp", repo_root=repo), repo_root=repo)
        fragment = compiled.apply_to(common)
        fragment["native_episode"]["consumption_module"] = current
        fragment["what_this_is"] = f"HELD F1 arm {arm.upper()}; shared complete-system execution. Agreement is source-bound; own supply, fit and registration remain pending. A-prime uses arm A byte-identically."
        write_identical(baseline_dir / f"{STEM}-{arm}-v1.json", fragment)
    write_identical(baseline_dir / f"{STEM}-aprime-v1.json",
        json.loads((baseline_dir / f"{STEM}-a-v1.json").read_text()))
    cells=[]
    for arm in ("a", "aprime", "b", "c"):
        rid=f"SAEA-SLURP-STAGE3-KNOWLEDGE-OPPORTUNITY-{arm.upper()}-V1"
        cells.append({"cell_id": f"{STEM}-{arm}-v1", "run_id": rid,
            "attempt_id": f"attempt-{STEM}-{arm}-v1",
            "baseline_fragment": f"{STEM}-{arm}-v1",
            "dataset_fragment": "slurp-speech-native-knowledge-opportunity-r01c400-v1",
            "model_fragment": "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1",
            "allowed_execution_stages": ["check", "prepare-supply"],
            "readiness": {"state": "held", "requirements": [], "reason":
                "Owner-approved offline implementation. No dispatch: milestone disposition, own supply, full request fit, smoke4, exposure and fresh service binding remain required."}})
    experiment={"experiment_id": "SAEA-SLURP-STAGE3-KNOWLEDGE-OPPORTUNITY-V1", "date": "2026-10-01",
        "execution_profile": "bounded-discovery-probe", "split_id": subset["split_name"], "cells": cells,
        "population": {"count":400, "split_identity_hash": subset["split_identity_hash"], "roster_receipt": str(receipt_path.relative_to(repo))},
        "stage3_algorithm": {"id":"none", "operators_used":[], "note":"Bounded capability exploration of complete-system knowledge opportunities; no learned policy or RL claim."},
        "stage3_measurement": {"measurement_design":"cross-flight-with-in-chain-replicate", "rows":400,
            "primary_metric":"official pooled SLU-F1", "primary_metric_key":"slu", "claims_benefit":False,
            "expected_effect_pp":0, "replicate_run_id": "SAEA-SLURP-STAGE3-KNOWLEDGE-OPPORTUNITY-APRIME-V1",
            "note":"Unknown conversion measured in owner-approved capability exploration. Zero is no effect forecast. No benefit admission; the recorded A/A and formal measurement rules remain mandatory for progression."},
        "preserve_wire_responses":True,
        "family_budget": {"complete_system_trajectories":1600, "generation_calls_cap":19200,
            "model_calls_by_arm":{"a":4400,"aprime":4400,"b":5200,"c":5200},
            "knowledge_tool_calls_cap":800,"official_complete_scoring_jobs":4,
            "note":"Formal execution plan, retries, smoke and FIT contacts are not authorised by these draft ceilings. Per-arm ceilings are 400 times shared program 11/11/13/13."}}
    experiment["execution_plan"] = {"execution_profile": "bounded-discovery-probe",
        "split_role": "discovery", "planned_model_calls": 5200, "planned_gpu_hours": 12.0,
        "planned_speech_audio_seconds": int(subset["audio_seconds_total"] * 13) + 1}
    experiment["populations"] = [{"dataset_fragment": "slurp-speech-native-knowledge-opportunity-r01c400-v1",
        "ids": [row["sample_id"] for row in subset["items"]]}]
    write_identical(repo / f"configs/experiment/{STEM}-v1.json", experiment)
    return {"rows":subset["count"], "roster_sha256":subset["runtime_view_sha256"], "stores":store_audit, "status":"HELD"}


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    args=parser.parse_args()
    print(json.dumps(prepare(args.repo_root.resolve(), args.data_root.resolve()), sort_keys=True))
