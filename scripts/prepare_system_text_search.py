#!/usr/bin/env python3
"""Prepare prospective text-search metadata and HELD seed cells, without contacts."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.knowledge_stores import load_knowledge_store_binding
from speech_aware_evidence_acquisition.rails.system_search_protocol import build_protocol
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    SystemTextPolicyBundle, assert_roster_disjoint, compile_system_text_policy,
)

PACKAGE = "docs/readiness/2026-10-01-slurp-system-text-search-v1"
BASE = "configs/baseline/slurp-native-stage3-knowledge-opportunity-c-v1.json"
STEM = "slurp-native-stage3-system-text-initial"


def write_identical(path, document):
    raw = (json.dumps(document, ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode()
    path = Path(path)
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError(f"Refuse to overwrite different registered bytes: {path}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)
    return hashlib.sha256(raw).hexdigest()


def prepare(repo, data_root):
    names = {"r01c": "slurp-stage3-construction-r01c", "fold_a": "slurp-evo-fold-a-v2",
             "fold_b": "slurp-evo-fold-b-v2", "dev": "slurp-dev-2000-added-v1"}
    rosters, pins = {}, {}
    for key, name in names.items():
        relative = f"docs/receipts/rosters/{name}.json"
        raw = (repo / relative).read_bytes()
        rosters[key] = [row["sample_id"] for row in json.loads(raw)["items"]]
        pins[key] = {"relpath": relative, "sha256": hashlib.sha256(raw).hexdigest()}
    protocol = build_protocol(rosters)
    protocol["source_rosters"] = pins
    baseline = json.loads((repo / BASE).read_text())
    binding = load_knowledge_store_binding(baseline, data_root=data_root)
    sources, store_audit = [], {}
    for sid, store in binding.stores.items():
        sample_ids = sorted({source for value in store.snapshot.values for source in value.source_sample_ids})
        source = {"kind": "knowledge", "sha256": store.snapshot.content_hash(), "sample_ids": sample_ids}
        sources.append(source)
        for ids in rosters.values():
            assert_roster_disjoint([source], ids)
        store_audit[sid] = {"source_count": len(sample_ids), "snapshot_sha256": store.snapshot.content_hash(),
                           "overlapping_utterances": 0, "values": len(store.snapshot.values)}
    bundle = SystemTextPolicyBundle.from_json({
        "schema": "saea-system-text-policy-bundle-v1", "parent_ids": [],
        "seed_config_sha256": content_hash(baseline),
        "construction_instruction": "Reuse the frozen released slot-contracts seed. Preserve source-supported meanings, applicability, extraction boundaries, ambiguity and absence. A future change to this construction instruction requires a separately registered materialized successor release.",
        "role_text": {role: (repo / "configs" / baseline["phase_material"][role]["instruction_template"]).read_text()
                      for role in ("solver", "reviewer", "planner")},
        "supply": {"mode": "targeted", "value_limit": 2},
        "knowledge": {key: baseline["knowledge_stores"]["slot-contracts"][key] for key in ("snapshot", "release")},
        "construction_receipt": None, "cumulative_sources": sources, "optimizer_experience": [],
    })
    rel = "prepared/SAEA-SLURP-SYSTEM-TEXT-SEARCH-V1/seed-policy.json"
    bundle_sha = write_identical(data_root / rel, bundle.as_json())
    protocol["seed_bundle"] = {"relpath": rel, "sha256": bundle_sha, "bundle_id": bundle.bundle_id}
    package = repo / PACKAGE
    write_identical(package / "protocol.json", protocol)
    write_identical(package / "source-audit.json", {"stores": store_audit, "rosters": pins,
        "binding_sha256": binding.binding_sha256, "seed_bundle": protocol["seed_bundle"],
        "contacts": {"model": 0, "tool": 0, "scorer": 0}})
    compiled = compile_system_text_policy(baseline, bundle, repo_root=repo, output_root=repo)
    compiled.pop("prepared_phase_supply", None)
    compiled["what_this_is"] = "HELD initial same-chain seed for whole-system text search; no learned improvement. Own preparation, FIT, four-row engineering proof and runtime admission are required."
    cells = []
    old = json.loads((repo / "configs/experiment/slurp-native-stage3-knowledge-opportunity-v1.json").read_text())
    for name in ("seed", "seed-aa"):
        own = copy.deepcopy(compiled)
        own["native_contact_fit"] = {
            "run_id": f"SAEA-SLURP-SYSTEM-TEXT-INITIAL-{name.upper()}-FIT-V1",
            "attempt_id": f"attempt-{STEM}-{name}-fit-v1",
            "contact_cap": 20800, "max_speech_packets": 1}
        write_identical(repo / f"configs/baseline/{STEM}-{name}-v1.json", own)
        cell = copy.deepcopy(old["cells"][3])
        cell.update(cell_id=f"{STEM}-{name}-v1", baseline_fragment=f"{STEM}-{name}-v1",
                    run_id=f"SAEA-SLURP-SYSTEM-TEXT-INITIAL-{name.upper()}-V1",
                    attempt_id=f"attempt-{STEM}-{name}-v1")
        cell["readiness"] = {"state": "held", "requirements": [], "reason":
            "Await serial integration, own source preparation, real full-request FIT, four-row proof, exposure registration and fresh resource/service admission. Proposal version remains unpinned. No dispatch authority from this preparation."}
        cells.append(cell)
    experiment = {key: copy.deepcopy(old[key]) for key in (
        "date", "execution_profile", "execution_plan", "population", "populations", "split_id",
        "preserve_wire_responses", "stage3_measurement")}
    experiment.update(experiment_id="SAEA-SLURP-SYSTEM-TEXT-INITIAL-V1", cells=cells,
        stage3_algorithm={"id": "system-text-black-box-v1", "operators_used": ["rollout", "scoring"],
                          "note": "Initial seed and same-chain A/A only. No policy update or benefit claim before complete-family feedback."},
        family_budget={"complete_system_trajectories": 800, "generation_calls_cap": 10400,
                       "knowledge_tool_calls_cap": 800, "official_complete_scoring_jobs": 2})
    experiment["stage3_measurement"]["replicate_run_id"] = cells[1]["run_id"]
    write_identical(repo / f"configs/experiment/{STEM}-v1.json", experiment)
    return {"status": "HELD", "stages": len(protocol["stages"]), "trajectory_cap": protocol["trajectory_cap"],
            "source_audit": store_audit, "seed_bundle_id": bundle.bundle_id, "contacts_added": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.repo_root.resolve(), args.data_root.resolve()), sort_keys=True))
