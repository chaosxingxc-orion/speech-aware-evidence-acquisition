#!/usr/bin/env python3
"""Source-bound F10 input and runtime supplement; no scorer or model invocation."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(REPO / "scripts"))
from build_slurp_train_exemplars_with_empty_store import FIELD_SEPARATOR, PARENT_EMPTY_FORM, SOLVER_EMPTY_ENTITY_LIST_FORM
import slurp_var1_variant_read as shared
from speech_aware_evidence_acquisition.analysis.system_feedback import write_system_feedback
from speech_aware_evidence_acquisition.core.config import compose
from speech_aware_evidence_acquisition.rails.finite_policy_artifacts import _pinned_json
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.knowledge_stores import load_knowledge_store_binding


def read_inputs(data, binding):
    manifest, _ = _pinned_json(data, {
        "relpath": "runs/" + binding["run_id"] + "/" + binding["attempt_id"] + "/"
                   + binding["run_id"] + ".run-manifest.json",
        "sha256": binding["source_sha256"]["run_manifest"]}, "sealed F10 manifest")
    parts = manifest["config"]["fragments"]
    cfg = compose(REPO, parts["model"], parts["dataset"], parts["baseline"], parts["experiment"])
    if cfg.config_hash != manifest["config"]["config_hash"]:
        raise ValueError("F10 source configuration changed")
    stores = load_knowledge_store_binding(cfg.values, data_root=data)
    values = {v.value_id: v for v in stores.composite_snapshot.values}
    directory = data / "runs" / binding["run_id"] / binding["attempt_id"]
    phases = shared.bank.load_phase_results(directory, binding["run_id"])
    rows = phases["results"]
    if len(rows) != 625 or len({row["sample_id"] for row in rows}) != 625:
        raise ValueError("F10 full population changed")
    first_requests = {}
    roles = {}
    terminal = Counter()
    for row in rows:
        native = row["native_episode_receipt"]
        terminal.update([native.get("terminal_disposition", {}).get("reason", "accepted")])
        for visit in native["role_visits"] + ([native["interrupted_role"]] if native.get("interrupted_role") else []):
            contacts = visit["execution_receipt"]["contacts"]
            for contact in contacts:
                roles[contact["request_id"] + "/request"] = visit["stage"]
            if visit["stage"] == "solver" and contacts and row["sample_id"] not in first_requests:
                first_requests[row["sample_id"]] = contacts[0]["request_id"] + "/request"
    reverse = {rid: sid for sid, rid in first_requests.items()}
    trace = manifest["raw_trace"]
    path = Path(trace["path"]).resolve()
    if not path.is_relative_to(data.resolve()):
        raise ValueError("trace path escapes data")
    digest = hashlib.sha256()
    inputs = {}
    volume = Counter()
    requests = Counter()
    seen = set()
    with path.open("rb") as f:
        for line in f:
            digest.update(line)
            record = json.loads(line)
            rid = record["record_id"]
            if rid not in roles:
                continue
            if rid in seen:
                raise ValueError("duplicate request")
            seen.add(rid)
            payload = record["payload"]["payload"]
            if content_hash(payload) != record["payload"]["payload_sha256"]:
                raise ValueError("request payload hash mismatch")
            requests.update([roles[rid]])
            volume["task_instruction_chars"] += len(payload.get("task_instruction", ""))
            volume["history_chars"] += sum(len(x.get("content", "")) for x in payload["history"])
            volume["supplied_evidence_chars"] += sum(len(x["content"]) for x in payload["supplied_evidence"])
            if rid in reverse:
                items = [x for x in payload["supplied_evidence"] if x["evidence_id"].startswith("train-exemplars::")]
                ids = [x["evidence_id"] for x in items]
                for item in items:
                    if item["content"] != values[item["evidence_id"]].content:
                        raise ValueError("actual evidence differs from pinned knowledge")
                empty = [item["evidence_id"] for item in items if item["content"].endswith((FIELD_SEPARATOR + PARENT_EMPTY_FORM, FIELD_SEPARATOR + SOLVER_EMPTY_ENTITY_LIST_FORM))]
                inputs[reverse[rid]] = {"example_ids": ids, "empty_example_ids": empty}
    if digest.hexdigest() != trace["sha256"] or seen != set(roles):
        raise ValueError("trace hash or request population differs")
    return {"trace_sha256": trace["sha256"], "knowledge_binding_sha256": stores.binding_sha256,
            "first_solver_rows": len(inputs), "no_solver_request_rows": 625-len(inputs),
            "first_solver_example_count_distribution": dict(Counter(len(x["example_ids"]) for x in inputs.values())),
            "first_solver_empty_example_count_distribution": dict(Counter(len(x["empty_example_ids"]) for x in inputs.values())),
            "first_solver_empty_examples_total": sum(len(x["empty_example_ids"]) for x in inputs.values()),
            "terminal_reasons": dict(terminal), "role_request_counts": dict(requests),
            "text_input_chars_over_all_requests": dict(volume), "rows": inputs}


def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-root", required=True, type=Path)
    a = p.parse_args()
    recipe = json.loads((REPO / "docs/readiness/2026-09-25-slurp-stage3-f10-v1/analysis-binding-sealed-v1.json").read_text())
    arms = {name: read_inputs(a.data_root, spec) for name, spec in recipe["arms"].items()}
    left, right = arms["control"]["rows"], arms["empty"]["rows"]
    common = set(left) & set(right)
    out = {"schema": "saea-f10-source-input-supplement-v1", "arms": arms,
           "common_first_solver_rows": len(common),
           "same_ordered_first_solver_example_ids": sum(left[s]["example_ids"] == right[s]["example_ids"] for s in common),
           "model_contacts_added": 0, "scorer_contacts_added": 0,
           "limitations": "Character counts are actual text volume, not token counts or speech-feature volume.",
           "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    out["content_sha256"] = content_hash(out)
    path = a.data_root / "analysis/SAEA-SLURP-STAGE3-F10-OFFICIAL-READ-V1/input-supplement.json"
    sha = write_system_feedback(path, out)
    print(json.dumps({"output": str(path), "sha256": sha, "summary": {
        name: {k: v for k, v in arm.items() if k != "rows"} for name, arm in arms.items()},
        "common": len(common), "same_examples": out["same_ordered_first_solver_example_ids"]}))


if __name__ == "__main__":
    main()
