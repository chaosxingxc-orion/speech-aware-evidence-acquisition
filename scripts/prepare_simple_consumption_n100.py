#!/usr/bin/env python3
"""Prepare exactly four frozen systems on existing UPDATE2 fixed400; never admit."""
import argparse
from copy import deepcopy
from dataclasses import asdict
import gc
import hashlib
import json
from pathlib import Path
import socket
from unittest.mock import patch

from speech_aware_evidence_acquisition.analysis.native_graph_capacity import native_graph_capacity_budget
from speech_aware_evidence_acquisition.core.config import drop_null_arms, compose
from speech_aware_evidence_acquisition.core.flight.factory import build_flight_runtime
from speech_aware_evidence_acquisition.core.preparation import digest, prepare_artifact, load_artifact
from speech_aware_evidence_acquisition.data.runtime_subset import build_runtime_subset
from speech_aware_evidence_acquisition.rails.experiment_population import population_stage_spec
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_policy import require, verify_system_text_binding

PACKAGE = "docs/readiness/2026-10-07-slurp-simple-consumption-n100-preparation-v1"
POPULATION = "configs/experiments/slurp-simple-consumption-architecture-n100-v1.json"
OLD_POPULATION = "configs/experiments/slurp-simple-consumption-architecture-n20-v2.json"
FULL_VIEW = "configs/dataset/slurp-speech-native-system-text-update-2-400-v1.json"
DATASET = "slurp-speech-native-simple-consumption-n100-v1"
GRAPH_DATASET = "slurp-speech-native-simple-consumption-n100-graph4-v1"
SELECTOR = "manual-architecture-fixed-roster-v1"


def pin(path, root):
    path = Path(path).resolve()
    require(path.is_relative_to(root.resolve()), "preparation pin escapes root")
    return {"relpath": path.relative_to(root.resolve()).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def read(binding, root):
    path = root / binding["relpath"]
    require(pin(path, root) == binding, "preparation source raw pin differs")
    return json.loads(path.read_bytes())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write((json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def refuse(*args, **kwargs):
    raise RuntimeError("N100 preparation forbids model, tokenizer and scorer contacts")


def extent(root):
    return {"schema": "saea-manual-architecture-fixed-roster-extent-v1",
            "source_population": pin(root / OLD_POPULATION, root),
            "runtime_view": pin(root / FULL_VIEW, root), "count": 100, "selection_seed": 20261001}


def subset_output(output, ids):
    require(set(output) == {"facets", "values"} and not output["facets"]
            and set(output["values"]) == {"perception"}, "frozen supply shape differs")
    require(set(ids) <= set(output["values"]["perception"]), "fixed400 supply omits inputs")
    return {"facets": {}, "values": {"perception": {
        sid: deepcopy(output["values"]["perception"][sid]) for sid in ids}}}


def prepare(root, data, lock, *, source_commit, continue_offline=False):
    root, data = root.resolve(), data.resolve()
    package = root / PACKAGE
    require(len(source_commit) == 40 and all(c in "0123456789abcdef" for c in source_commit), "full source commit required")
    require(not package.exists() or continue_offline, "N100 preparation requires a fresh package")
    original = read(pin(root / OLD_POPULATION, root), root)
    full = read(pin(root / FULL_VIEW, root), root)
    require(full["runtime_view_sha256"] == content_hash({k: v for k, v in full.items()
            if k != "runtime_view_sha256"}), "fixed400 runtime view identity differs")
    ids = [i["sample_id"] for i in full["items"]]
    old_ids = original["cohorts"][0]["sample_ids"]
    require(len(ids) == len(set(ids)) == 400 and ids[:len(old_ids)] == old_ids,
            "exact UPDATE2fixed400 configured order or original20 prefix differs")
    full_ids = ids
    view, selection_receipt = build_runtime_subset(full, seed=20261001, count=100,
        name="SLURP-SIMPLE-CONSUMPTION-N100-V1")
    ids = selection_receipt["sample_ids"]
    owner225 = json.loads((root / "docs/receipts/rosters/slurp-system-text-fixed400-prefix100-owner225-v1.json").read_bytes())
    require(ids == owner225["sample_ids"] and ids[:len(old_ids)] == old_ids
        and owner225["parent_runtime_view_sha256"] == full["runtime_view_sha256"], "registered stable prefix100 differs")
    population = deepcopy(original)
    population["experiment_id"] = "slurp-simple-consumption-architecture-n100-v1"
    population["cohorts"][0]["sample_ids"] = ids
    require([m["member_id"] for m in population["architecture"]["members"]]
            == ["seed", "seed-aa", "review-off", "solver-lookup"], "frozen family differs")
    names = [(m["member_id"], "slurp-native-stage3-simple-consumption-" + m["member_id"] + "-n100-v1")
             for m in population["architecture"]["members"]]
    for label, stem in names:
        run = "SAEA-SLURP-SIMPLE-CONSUMPTION-" + label.upper() + "-N100-V1"
        for suffix in ("", "-CAPACITY", "-GRAPH"):
            name = stem if not suffix else stem.removesuffix("-v1") + suffix.lower() + "-v1"
            for kind in ("baseline", "experiment"):
                require(continue_offline or not (root / "configs" / kind / (name + ".json")).exists(), "new config identity exists")
        for identity in (run, run.removesuffix("-V1") + "-CAPACITY-FIT-V1",
                         run.removesuffix("-V1") + "-GRAPH-V1"):
            require(all(not (data / folder / identity).exists() for folder in (("attempts", "runs") if continue_offline else ("prepared", "attempts", "runs"))),
                    "new DATA identity exists")
    for target in (root / POPULATION, root / ("configs/dataset/" + DATASET + ".json"),
                   root / ("configs/dataset/" + GRAPH_DATASET + ".json")):
        require(continue_offline or not target.exists(), "fresh population or dataset already exists")
    basis = read({"relpath": "prepared/SAEA-SLURP-SYSTEM-TEXT-UPDATE2-RH1-L-PARENT-V1/phase-supply-v1.json",
                  "sha256": "99ba974066d6a87f086e8850c316252857e205e5213387e9ae7ed030c22900f0"}, data)
    require(basis["output_sha256"] == digest(basis["output"])
            and set(basis["output"]["values"]["perception"]) == set(full_ids), "full400 supply seal differs")
    graph_view, graph_roster = build_runtime_subset(full, seed=20261001, count=4,
                                                  name="SLURP-SIMPLE-CONSUMPTION-N100-GRAPH4-V1")
    require(graph_roster["sample_ids"] == ids[:4], "graph4 membership differs")
    def keep_or_save(path, value):
        if path.exists():
            require(continue_offline and json.loads(path.read_bytes()) == value, "existing offline metadata drift")
        else:
            save(path, value)
    keep_or_save(root / POPULATION, population)
    keep_or_save(root / ("configs/dataset/" + DATASET + ".json"), view)
    keep_or_save(root / ("configs/dataset/" + GRAPH_DATASET + ".json"), graph_view)
    keep_or_save(package / "graph-roster-v1.json", graph_roster)
    keep_or_save(package / "roster-v1.json", {"schema": "saea-runtime-subset-receipt-v1",
        "parent_runtime_view_sha256": full["runtime_view_sha256"], "selection": "existing UPDATE2fixed400 stable SHA256 prefix100",
        "seed": full["seed"], "sample_ids": ids, "count": len(ids), "contacts": {"model": 0, "tool": 0, "scorer": 0, "gpu": 0}})
    population_pin = pin(root / POPULATION, root)
    stage = population_stage_spec(population_pin, repo_root=root, cohort_id="comparison", allow_architecture=True)
    records = []
    capacity_sources = json.loads((root / "docs/readiness/2026-10-07-slurp-simple-consumption-prepared-graph-recovery2-v1/prepared-capacities-v3.json").read_bytes())
    capacity_sources = {m["label"]: m for m in capacity_sources["members"]}
    with patch.object(socket.socket, "connect", refuse), patch.object(socket.socket, "connect_ex", refuse):
        for member in stage["architecture_members"]:
            label = member["member_id"]
            stem = "slurp-native-stage3-simple-consumption-" + label + "-n100-v1"
            old = "slurp-native-stage3-simple-consumption-" + label + "-n20-v2"
            baseline = json.loads((root / "configs/baseline" / (old + ".json")).read_bytes())
            document = json.loads((root / "configs/experiment" / (old + ".json")).read_bytes())
            previous_supply = read(baseline.pop("prepared_phase_supply"), data)
            require(subset_output(basis["output"], old_ids) == previous_supply["output"],
                    "original20 member selection is not exact fixed400 prefix")
            generation_cap = stage["member_generation_contacts_caps"][label]
            fit_cap = stage["member_fit_endpoints_caps"][label]
            baseline["what_this_is"] = "Frozen simple-consumption policy on the registered fixed400 prefix100; model-free preparation, root admission pending."
            baseline.update(experiment_population=population_pin, architecture_extent=extent(root),
                            population_budget=stage["population_budget"])
            for kind in ("generation", "capacity", "graph"):
                name = stem if kind == "generation" else stem.removesuffix("-v1") + "-" + kind + "-v1"
                existing_receipt = package / (label + "-" + kind + "-prepared-v1.json")
                if continue_offline and existing_receipt.exists():
                    prior_record = json.loads(existing_receipt.read_bytes())
                    c = json.loads((root / "configs/experiment" / (name + ".json")).read_bytes())["cells"][0]
                    configured = compose(root, c["model_fragment"], c["dataset_fragment"], c["baseline_fragment"], name)
                    from speech_aware_evidence_acquisition.rails.architecture_natural_registration import _require_prepared_implementation
                    envelope = read(prior_record["prepared_phase_supply"], data)
                    _require_prepared_implementation(envelope, root, configured.values)
                    require(configured.config_hash == prior_record["config_hash"]
                            and prior_record["output_sha256"] == digest(envelope["output"])
                            and envelope["output"] == subset_output(basis["output"], prior_record["configured_sample_ids"]),
                            "preserved completed offline preparation differs")
                    record = {**prior_record, "prepared_source_commit": source_commit,
                              "supersedes_preparation": pin(existing_receipt, root)}
                    keep_or_save(package / (label + "-" + kind + "-prepared-v2.json"), record)
                    records.append(record)
                    print(label + ": " + kind + " existing strict output/source verified; metadata successor only", flush=True)
                    continue
                run = "SAEA-SLURP-SIMPLE-CONSUMPTION-" + label.upper() + "-N100" + (
                    "-V1" if kind == "generation" else "-CAPACITY-FIT-V1" if kind == "capacity" else "-GRAPH-V1")
                bp, ep = deepcopy(baseline), deepcopy(document)
                selected = ids[:4] if kind == "graph" else ids
                selected_view = graph_view if kind == "graph" else view
                dataset = GRAPH_DATASET if kind == "graph" else DATASET
                attempt = "attempt-" + name + ("-generation" if kind == "generation" else "-fit" if kind == "capacity" else "-graph")
                cap = generation_cap if kind == "generation" else 4 * member["model_per_trajectory"]
                if kind == "generation":
                    bp["native_contact_fit"].update(run_id=run.removesuffix("-V1") + "-FIT-V1",
                        attempt_id=attempt + "-fit", contact_cap=fit_cap)
                else:
                    bp.pop("native_contact_fit", None)
                    if kind == "capacity":
                        old_capacity = json.loads((root / "configs/experiment" / (capacity_sources[label]["new_capacity"] + ".json")).read_bytes())
                        cap = old_capacity["execution_plan"]["planned_model_calls"]
                ep.update(experiment_id=run, split_id=selected_view["split_name"])
                ep["execution_plan"].update(planned_model_calls=cap, planned_speech_audio_seconds=max(1500, selected_view["audio_seconds_total"]))
                ep["population"] = {"count": len(selected), "split_identity_hash": selected_view["split_identity_hash"],
                    "roster_receipt": PACKAGE + ("/graph-roster-v1.json" if kind == "graph" else "/roster-v1.json")}
                ep["populations"] = [{"dataset_fragment": dataset, "ids": selected}]
                ep["stage3_measurement"].update(rows=len(selected), read_roster=selected_view["split_name"],
                    note="Four unchanged policies on registered prefix100: diagnostic form proof, no benefit or independent validation claim.")
                ep["family_budget"] = {"complete_system_trajectories": stage["N"], "generation_calls_cap": generation_cap,
                    "actual_request_fit_endpoint_cap": fit_cap, "official_complete_scoring_jobs": 1} if kind == "generation" else {
                    "complete_system_trajectories": 0, "generation_calls_cap": 0, "official_complete_scoring_jobs": 0,
                    "tokenizer_endpoint_cap": cap if kind == "capacity" else 0}
                cell = ep["cells"][0]
                cell.update(cell_id=name, run_id=run, attempt_id=attempt, baseline_fragment=name, dataset_fragment=dataset,
                    allowed_execution_stages=["check", "prepare-supply", "worker", "campaign"] if kind == "generation" else
                        ["check", "prepare-supply", "prompt-fit"] if kind == "capacity" else ["check", "prepare-supply"],
                    readiness={"state": "held", "reason": "Exact root admission, fresh N100 capacity and frozen/live gates pending.", "requirements": []})
                keep_or_save(root / "configs/baseline" / (name + ".json"), bp)
                experiment_path = root / "configs/experiment" / (name + ".json")
                if continue_offline and experiment_path.exists() and kind == "graph":
                    partial = json.loads(experiment_path.read_bytes())
                    corrected = deepcopy(partial)
                    corrected["execution_plan"]["planned_model_calls"] = cap
                    require(corrected == ep, "graph parser correction changed unrelated metadata")
                    save(package / (label + "-graph-refused-config-v1.json"), partial)
                    experiment_path.write_bytes((json.dumps(ep, sort_keys=True, indent=2) + "\n").encode("utf-8"))
                else:
                    keep_or_save(experiment_path, ep)
                def runtime():
                    return build_flight_runtime(root, data, model=cell["model_fragment"], dataset=dataset,
                        baseline=name, experiment=name, run_id=run, attempt_id=attempt,
                        runtime_root=Path("/home/chao"), lock_path=lock, campaign_active=False, score_batch=refuse)
                rt = runtime()
                context = rt.preparation_context()
                require(len(context["sample_ids"]) == len(set(context["sample_ids"])) == len(selected)
                        and set(context["sample_ids"]) == set(selected), "complete production runtime order differs")
                pure_budget = None
                if kind == "capacity":
                    stores = context["values"]["knowledge_stores"]
                    from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot
                    counts = {}
                    for key in ("slot-contracts", "intent-boundaries"):
                        binding = stores[key]["snapshot"]
                        snapshot = KnowledgeSnapshot.from_frozen_json(json.loads((data / binding["relpath"]).read_bytes()))
                        require(snapshot.content_hash() == binding["sha256"], "canonical source snapshot pin differs")
                        counts[key] = len(snapshot.values)
                    pure_budget = native_graph_capacity_budget(context["values"],
                        slot_value_count=counts["slot-contracts"], intent_value_count=counts["intent-boundaries"],
                        graph_rows=4, media_parts=1, profile=context["values"]["native_graph_capacity_profile"])
                    require(pure_budget["contact_cap"] == cap, "fresh pure capacity ceiling differs")
                policy = drop_null_arms(read(member["execution_config"], root))
                require(all(context["values"].get(k) == v for k, v in policy.items() if k != "what_this_is"),
                        "frozen execution policy changed")
                verify_system_text_binding(context["values"], cell["system_text_policy_binding"], repo_root=root, data_root=data)
                *_, inputs = rt.phase_supply_artifact_identity()
                supply = data / "prepared" / run / "phase-supply-v1.json"
                output = subset_output(basis["output"], selected)
                prepare_artifact(supply, kind="phase-supply", inputs=inputs, producer=lambda: deepcopy(output))
                bp["prepared_phase_supply"] = pin(supply, data)
                cell["readiness"]["requirements"] = [{"kind": "preparation", **bp["prepared_phase_supply"],
                    "reason": "Exact fixed400 selection outputs reused with current source identity; zero contacts."}]
                for path, value in ((root / "configs/baseline" / (name + ".json"), bp),
                                    (root / "configs/experiment" / (name + ".json"), ep)):
                    path.write_bytes((json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8"))
                rt = runtime()
                context = rt.preparation_context()
                *_, final_inputs = rt.phase_supply_artifact_identity()
                require(load_artifact(supply, expected_sha256=bp["prepared_phase_supply"]["sha256"],
                    kind="phase-supply", inputs=final_inputs) == output, "strict prepared output differs")
                rt.verify_prepared_artifacts()
                record = {"member_id": label, "kind": kind, "experiment": name, "baseline": name,
                    "run_id": run, "attempt_id": attempt, "config_hash": rt._composed.config_hash,
                    "execution_plan": asdict(context["execution_plan"]), "source_policy": member["execution_config"],
                    "policy_binding": cell["system_text_policy_binding"], "prepared_phase_supply": bp["prepared_phase_supply"],
                    "source_prepared_phase_supply": {"relpath": "prepared/SAEA-SLURP-SYSTEM-TEXT-UPDATE2-RH1-L-PARENT-V1/phase-supply-v1.json",
                        "sha256": "99ba974066d6a87f086e8850c316252857e205e5213387e9ae7ed030c22900f0"},
                    "configured_sample_ids": selected, "runtime_sample_ids": context["sample_ids"],
                    "generation_cap": generation_cap, "fit_endpoint_cap": fit_cap,
                    "output_sha256": digest(output), "output_equal": True, "warm_verified": True,
                    "prepared_source_commit": source_commit, "runtime_admission": False, "contacts": 0,
                    "architecture_extent": extent(root), "pure_capacity_budget": pure_budget, "draft_plans": {}}
                save(package / (label + "-" + kind + "-prepared-v1.json"), record)
                records.append(record)
                print(label + ": " + kind + " strict preparation PASS; zero contacts", flush=True)
                del rt, context
                gc.collect()
    summary = {"status": "PREPARED_HELD_NOT_ADMITTED", "experiment_population": population_pin,
        "architecture_extent": extent(root), "population_budget": stage["population_budget"],
        "members": records, "contacts": {"generation": 0, "tokenizer": 0, "scorer": 0},
        "configured_original20_is_prefix": True, "runtime_original20_is_paired_subset": True,
        "windows_startup_free_memory_gib": 4, "windows_running_free_memory_gib": 4,
        "source_commit": source_commit}
    save(package / "preparation-summary-v1.json", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("repo-root", "data-root", "lock-path", "source-commit"):
        parser.add_argument("--" + option, required=True)
    parser.add_argument("--continue-offline", action="store_true")
    args = parser.parse_args()
    prepare(Path(args.repo_root), Path(args.data_root), Path(args.lock_path), source_commit=args.source_commit, continue_offline=args.continue_offline)
