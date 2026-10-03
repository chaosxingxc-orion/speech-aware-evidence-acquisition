#!/usr/bin/env python3
"""Read one complete engineering matrix through the shared root ledger gate.

Never countersign, score, contact a model, change a policy or export to a proposer.
The original frozen runtime remains separate from this offline numeric reader.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

from speech_aware_evidence_acquisition.analysis.context_configuration import describe_configurations
from speech_aware_evidence_acquisition.analysis.context_configuration_source import preflight_members, read_numeric_members
from speech_aware_evidence_acquisition.rails.finite_policy_artifacts import _pinned_json
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_search_stage import recipe_family_identity
from speech_aware_evidence_acquisition.rails.system_text_policy import _read_pin, require

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("_context_matrix_shared_read_gate", ROOT / "scripts/system_text_search.py")
CLI = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = CLI
spec.loader.exec_module(CLI)


def _document(pin, root):
    return json.loads(_read_pin(pin, root))


def render(report):
    lines = ["# Context configuration: business quality and sample latency", "", report["interpretation"], "",
             "| Member | SLU-F1 | Intent | Reliable delivery | All samples (s) | First admitted (s) | Remaining (s) |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for name, row in report["members"].items():
        lines.append(f"| {name} | {100 * row['slu_f1']:.3f}% | {100 * row['intent']:.2f}% | "
                     f"{100 * row['reliable_completion_rate']:.2f}% | {row['all_samples_mean_seconds']:.3f} | "
                     f"{row['first_admitted_seconds']:.3f} | {row['remaining_samples_mean_seconds']:.3f} |")
    lines += ["", "## Original node timings", "",
              "Contact-weighted means below retain their distinct measurement boundaries. The JSON also retains p50, p95, missingness and every source index.", "",
              "| Member | Role | Contacts | Client (ms) | Prefill (ms) | Decode (ms) | Reused input |",
              "|---|---|---:|---:|---:|---:|---:|"]
    for name, row in report["members"].items():
        for role, node in row["node_timing"]["by_role"].items():
            means = [node["metrics"][key]["mean_observed"] for key in ("client_transport_ms", "prefill_ms", "generation_ms")]
            cells = ["unavailable" if value is None else f"{value:.3f}" for value in means]
            reused = node["reused_input_fraction"]
            reuse = "unavailable" if reused is None else f"{100 * reused:.2f}%"
            lines.append(f"| {name} | {role} | {node['contacts']} | {' | '.join(cells)} | {reuse} |")
    lines += ["", "The report retains all configurations, both repeats, paired uncertainty, own-repeat differences, per-scenario support and both weightings. No automatic selection or optimizer export. Batch wall/count is throughput, not individual latency.", ""]
    return "\n".join(lines)


def run(inputs, *, repo_root, data_root, output):
    root, data, output = (Path(p).resolve() for p in (repo_root, data_root, output))
    require(output.is_relative_to(data / "analysis") and output != data / "analysis" and not output.exists(),
            "use a fresh analysis directory outside optimizer storage")
    require(set(inputs) == {"schema", "recipe", "registration", "roster", "strata", "frozen_worker"}
            and inputs["schema"] == "saea-context-matrix-read-inputs-v1", "exact matrix reader inputs are required")
    reader_names = ["scripts/analysis/context_matrix_read.py", "scripts/system_text_search.py",
                    "src/speech_aware_evidence_acquisition/analysis/context_configuration.py",
                    "src/speech_aware_evidence_acquisition/analysis/context_configuration_source.py",
                    "src/speech_aware_evidence_acquisition/analysis/system_wire_context.py",
                    "src/speech_aware_evidence_acquisition/rails/system_search_stage.py"]
    reader_pins = [{"relpath": name, "sha256": hashlib.sha256((ROOT / name).read_bytes()).hexdigest()}
                   for name in reader_names]
    recipe, registration = (_document(inputs[key], root) for key in ("recipe", "registration"))
    family, members = recipe_family_identity(recipe)
    read_spec = {"family_id": family, "expected_members": members, "read_registration": inputs["recipe"]}
    authority = CLI.require_read_registration(read_spec, repo_root=root)
    require(registration.get("schema") == "saea-context-matrix-n20-registration-v1"
            and registration.get("analysis") == inputs["recipe"]
            and registration.get("read_id") == authority["read_run_id"]
            and registration.get("rows_per_member") == 20 and registration.get("trajectory_cap") == 160
            and registration.get("official_complete_scores") == 8
            and len(registration.get("members", [])) == 8
            and {member["label"]: member["run_id"] for member in registration["members"]} == members
            and registration.get("complete_family") == recipe["complete_family"],
            "matrix registration differs from its exact READ recipe")
    admission, _ = _pinned_json(data, registration["admission"], "matrix admission")
    require(registration["admission"] == recipe["admission"]
            and admission.get("decision_id") == "slurp-context-matrix-n20-owner227-v1"
            and admission.get("status") == "decided" and admission.get("owner_decisions") == [227]
            and admission.get("next_scale_admitted") is False
            and set(members.values()) <= set(admission.get("eligible_run_ids", [])),
            "exact decided root matrix admission is required")
    frozen = Path(inputs["frozen_worker"]["path"])
    for pin in recipe["source_checks"]:
        _read_pin(pin, frozen)
    roster = _document(inputs["roster"], root)
    strata = _document(inputs["strata"], root)
    ids = [row["sample_id"] for row in roster["items"]]
    require(len(ids) == len(set(ids)) == 20, "matrix roster must retain twenty unique inputs")
    indexed = {row["sample_id"]: row for row in strata["items"]}
    require(len(indexed) == len(strata["items"]), "duplicate stratum metadata")
    joined = {}
    for row in roster["items"]:
        sid = row["sample_id"]
        require(sid in indexed and row["utterance_id"] == indexed[sid]["utterance_id"],
                "matrix stratum join differs from original utterance identity")
        joined[sid] = {key: indexed[sid][key] for key in ("sample_id", "utterance_id", "stratum")}
    sources = preflight_members(registration, data_root=data, sample_ids=ids, commit=inputs["frozen_worker"]["commit"])
    numeric = read_numeric_members(sources, data_root=data, frozen_repo=frozen)
    uncertainty = recipe["uncertainty"]
    report = describe_configurations(numeric, comparisons=recipe["comparisons"], roster=joined,
                                     bootstrap_draws=uncertainty["bootstrap_draws"], seed=uncertainty["seed"])
    require(CLI.require_read_registration(read_spec, repo_root=root) == authority,
            "root READ authority changed during analysis")
    repeated = preflight_members(registration, data_root=data, sample_ids=ids, commit=inputs["frozen_worker"]["commit"])
    require([entry["metadata_pins"] for entry in sources] == [entry["metadata_pins"] for entry in repeated],
            "source metadata changed during analysis")
    for key in ("recipe", "registration", "roster", "strata"):
        _read_pin(inputs[key], root)
    for pin in reader_pins:
        _read_pin(pin, ROOT)
    for member in numeric.values():
        _read_pin(member["context_execution"]["wire_requests"]["artifact"], data)
    _pinned_json(data, registration["admission"], "matrix admission")
    report.update(read_authority=authority, source_inputs=inputs, reader_sources=reader_pins,
                  numeric_source_bindings={run: member["source_bindings"] for run, member in numeric.items()},
                  context_execution={run: member["context_execution"] for run, member in numeric.items()},
                  model_contacts_added=0, scorer_contacts_added=0)
    report.pop("content_sha256", None)
    report["content_sha256"] = content_hash(report)
    output.mkdir(parents=True, exist_ok=False)
    CLI.write_new(output / "report.json", report)
    CLI.write_new(output / "numeric-evidence.json", numeric)
    with (output / "README.md").open("x", encoding="utf-8") as handle:
        handle.write(render(report))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("inputs", "data-root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    args = parser.parse_args()
    raw = args.inputs.read_bytes()
    report = run(json.loads(raw), repo_root=args.repo_root, data_root=args.data_root, output=args.output)
    print(json.dumps({"output": str(args.output), "report_sha256": report["content_sha256"],
                      "inputs_sha256": hashlib.sha256(raw).hexdigest(), "model_contacts_added": 0,
                      "scorer_contacts_added": 0}))


if __name__ == "__main__":
    main()
