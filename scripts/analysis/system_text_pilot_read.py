#!/usr/bin/env python3
"""Read a registered complete optimization family with zero scorer/model calls.

Create source-addressed analysis derivatives outside optimizer storage. Preserve
all original manifests, attempts, score jobs, artifacts and registration bytes.
"""

import argparse
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from speech_aware_evidence_acquisition.analysis import system_text_context as context
from speech_aware_evidence_acquisition.analysis import system_text_panel as panel
from speech_aware_evidence_acquisition.analysis import system_architecture_read as architecture
from speech_aware_evidence_acquisition.analysis import system_context_read as context_read
from speech_aware_evidence_acquisition.rails import system_context_learning as context_learning
from speech_aware_evidence_acquisition.rails.system_text_feedback import CompleteSystemFeedback
from speech_aware_evidence_acquisition.rails.system_text_policy import canonical
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.analysis.system_text_pilot import (
    analyze_pilot,
    read_pilot_evidence,
    validate_pilot_registration,
)
from speech_aware_evidence_acquisition.core.bundle.verify import verify_bundle
from speech_aware_evidence_acquisition.core.scoring_receipt import (
    write_complete_saved_score_receipt,
)
from speech_aware_evidence_acquisition.rails.reward_link_io import (
    build_reward_link_artifact,
)
from speech_aware_evidence_acquisition.rails.system_text_feedback import (
    preflight_family,
    _absolute_json,
)
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    _read_pin,
    require,
)

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "_pilot_read_ledger", ROOT / "scripts/system_text_search.py"
)
CLI = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = CLI
spec.loader.exec_module(CLI)


def pin(path):
    path = Path(path).resolve()
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def load_documents(recipe_pin, supplement_pin, root):
    from speech_aware_evidence_acquisition.analysis.system_text_update import load_additional_contrast_document

    recipe = load_additional_contrast_document(_read_pin(recipe_pin, root))
    supplement = json.loads(_read_pin(supplement_pin, root))
    require(
        supplement.get("schema")
        == (
            "saea-manual-architecture-analysis-supplement-v1"
            if "manual_architecture_registration" in recipe
            else "saea-context-learning-analysis-supplement-v1"
            if "context_learning_registration" in recipe
            else "saea-system-panel-analysis-supplement-v1"
            if "system_panel_registration" in recipe
            else "saea-context-analysis-supplement-v1"
            if recipe.get("family_id") in context.READ_IDS
            else "saea-pilot-analysis-supplement-v1"
        )
        and supplement.get("recipe") == recipe_pin,
        "analysis supplement names another recipe",
    )
    key = ("manual_architecture_registration" if "manual_architecture_registration" in recipe else
           "context_learning_registration" if "context_learning_registration" in recipe else
           "system_panel_registration" if "system_panel_registration" in recipe else "pilot_registration")
    registration = load_additional_contrast_document(_read_pin(recipe[key], root))
    if key == "manual_architecture_registration":
        require(recipe.get("architecture_proof") in architecture.SELECTORS
                and supplement.get("registration") == recipe[key]
                and supplement.get("process_diagnostics") == recipe.get("process_diagnostics"),
                "manual selector, supplement or READ-pinned process binding differs")
        require(supplement.get("source_code", {}).get("reader", {}).get("relpath")
                == "scripts/analysis/system_text_pilot_read.py"
                and supplement["source_code"].get("analyzer", {}).get("relpath")
                == "src/speech_aware_evidence_acquisition/analysis/system_architecture_read.py"
                and supplement["source_code"]["reader"]["sha256"] == pin(__file__)["sha256"]
                and supplement["source_code"]["analyzer"]["sha256"] == pin(architecture.__file__)["sha256"],
                "manual reader requires exact executing reader and analyzer pins")
        architecture.require_additional_contrast_binding(recipe, registration)
        architecture.validate_additional_paired_contrasts(recipe, recipe.get("comparison_groups", {}))
        if "additional_paired_contrasts" in recipe:
            require(content_hash(recipe["resampling"]) == content_hash(supplement["resampling"]),
                    "additional paired contrast recipe/supplement resampling differs")
            from speech_aware_evidence_acquisition.analysis import (
                system_text_update, paired, bootstrap, null_calibration,
            )
            for module in (system_text_update, paired, bootstrap, null_calibration):
                name = module.__name__.rsplit(".", 1)[-1]
                source_pin = supplement["source_code"].get(name, {})
                require(source_pin.get("relpath")
                        == "src/speech_aware_evidence_acquisition/analysis/" + name + ".py"
                        and source_pin.get("sha256") == pin(module.__file__)["sha256"],
                        "additional pooled contrast requires exact executing shared dependency pins")
        for source_pin in supplement["source_code"].values():
            _read_pin(source_pin, root)
        owner = json.loads(_read_pin(supplement["owner_decision"], root))
    elif key == "context_learning_registration":
        require(not any(k in recipe for k in ("system_panel_registration", "pilot_registration")),
                "context recipe cannot mix family registration types")
        for source_pin in supplement.get("source_code", {}).values():
            _read_pin(source_pin, root)
        require(supplement.get("registration") == recipe[key], "context supplement registration differs")
        owner = json.loads(_read_pin(registration["protocol"], root))
        context_learning._validate_scope(recipe, registration, owner, root=root)
    else:
        owner = json.loads(_read_pin(supplement["owner_decision"], root))
    return recipe, registration, owner, supplement


def source_bindings(registration, roster_pin, data_root):
    """Read all operational job metadata before any saved score is opened."""
    result, metadata_pins = [], []
    for cid, member in registration["member_bindings"].items():
        binding, pins = member_source_binding(cid, member, roster_pin, data_root)
        result.append(binding)
        metadata_pins.extend(pins)
    return result, metadata_pins


def member_source_binding(cid, member, roster_pin, data_root):
    """Inspect one complete original score job; return no family evidence."""
    directory = data_root / "runs" / member["run_id"] / member["attempt_id"]
    jobs_path, summary_path = (
        directory / "score-jobs.jsonl",
        directory / "score-batch/batch-summary.json",
    )
    metadata_pins = [pin(jobs_path), pin(summary_path)]
    jobs = [
        json.loads(line)
        for line in jobs_path.read_text().splitlines()
        if line.strip()
    ]
    summary = CLI.read(summary_path)
    require(
        len(jobs) == 1
        and jobs[0]["job_id"] == member["attempt_id"]
        and summary.get("job_count") == summary.get("succeeded") == 1
        and summary.get("failed") == 0
        and summary.get("include_per_sample") is True
        and len(summary.get("jobs", [])) == 1,
        "pilot requires exactly one successful complete official job and zero failures",
    )
    job = summary["jobs"][0]
    require(
        job["job_id"] == jobs[0]["job_id"]
        and job.get("returncode") == 0
        and job.get("status") == "succeeded"
        and job.get("operation") == "finalize"
        and Path(job["manifest"]).resolve() == Path(jobs[0]["manifest"]).resolve(),
        "pilot official job identity/status differs",
    )
    manifest = Path(jobs[0]["manifest"]).resolve()
    require(
        manifest.parent == directory.resolve(),
        "pilot manifest escaped its original attempt",
    )
    binding = {
            "candidate_id": cid,
            "config": {
                "manifest": pin(manifest),
                "construction_roster": roster_pin,
            },
    }
    return binding, metadata_pins


def qualify_registered_context_family(*, recipe_pin, repo_root, data_root, frozen_check):
    """Verify a whole configured family without scoring, signing or reporting quality.

    Count members and rows from validated registration/configuration. Check every
    attempt before reading score metadata or parsing sealed output bundles. This
    metadata qualification never substitutes for the separate root READ.
    """
    repo_root, data_root = Path(repo_root).resolve(), Path(data_root).resolve()
    recipe = json.loads(_read_pin(recipe_pin, repo_root))
    registration_pin = recipe["context_learning_registration"]
    registration = json.loads(_read_pin(registration_pin, repo_root))
    protocol = json.loads(_read_pin(registration["protocol"], repo_root))
    context_learning._validate_scope(recipe, registration, protocol, root=repo_root)
    members = registration["member_bindings"]
    frozen_members = frozen_check.get("members", [])
    require(
        frozen_check.get("passed") is True and frozen_check.get("contacts") == 0
        and len(frozen_members) == len(members)
        and {m["member"] for m in frozen_members} == set(members)
        and all(m["config_hash"] == members[m["member"]]["config_hash"]
                for m in frozen_members),
        "qualification requires every exact frozen member/configuration",
    )
    attempt_paths, observed, attempt_pins = {}, [], []
    for cid, member in members.items():
        directory = (data_root / "attempts" / member["run_id"]).resolve()
        path = (directory / (member["attempt_id"] + ".json")).resolve()
        require(directory.parent == data_root / "attempts" and path.parent == directory,
                "registered attempt escaped its operational directory")
        attempt_paths[cid] = path
        attempt = json.loads(path.read_text()) if path.exists() else {}
        observed.append({"member": cid, "state": attempt.get("state", "ABSENT"),
                         "calls": attempt.get("actual", {}).get("calls")})
        if path.exists():
            attempt_pins.append(pin(path))
    if any(m["state"] != "FINALIZED" for m in observed):
        return {"status": "WAIT", "members": observed, "quality_values_reported": False,
                "root_read_signed_by_this_function": False}
    roster_pin = recipe["analysis_roster"]
    _read_pin(roster_pin, repo_root)
    bindings, job_pins = source_bindings(
        registration, pin(repo_root / roster_pin["relpath"]), data_root
    )
    require(len(bindings) == len(members)
            and {b["candidate_id"] for b in bindings} == set(members),
            "operational bindings omit or duplicate a registered member")
    metadata = preflight_family(bindings, registration["expected_members"])
    qualified = []
    for binding, (_, job) in zip(bindings, metadata, strict=True):
        cid = binding["candidate_id"]
        member = members[cid]
        manifest_pin = binding["config"]["manifest"]
        require(pin(manifest_pin["path"]) == manifest_pin, "manifest changed before verification")
        bundle = verify_bundle(Path(manifest_pin["path"]))
        require(
            bundle.attempt_state == "FINALIZED"
            and len(bundle.outputs_rows) == recipe["required_rows_per_member"]
            and bundle.split_ids == set(recipe["sample_ids"])
            and bundle.manifest["run_id"] == member["run_id"]
            and bundle.manifest["attempt"]["attempt_id"] == member["attempt_id"]
            and bundle.manifest["config"]["config_hash"] == member["config_hash"]
            and bundle.manifest["study_commit"] == frozen_check["commit"],
            "verified family member differs from registered identity, rows or frozen source",
        )
        qualified.append({"member": cid, "run_id": member["run_id"],
                          "attempt_id": member["attempt_id"], "state": "FINALIZED",
                          "rows": len(bundle.outputs_rows), "verified_seal": True,
                          "official_successful_jobs": 1, "failed_jobs": 0,
                          "manifest": manifest_pin, "score_job_id": job["job_id"]})
    require(all(pin(p["path"]) == p for p in job_pins + attempt_pins
                + [m["manifest"] for m in qualified]),
            "operational evidence changed during whole-family qualification")
    _read_pin(recipe_pin, repo_root)
    _read_pin(registration_pin, repo_root)
    _read_pin(registration["protocol"], repo_root)
    context_learning._validate_scope(recipe, registration, protocol, root=repo_root)
    return {"schema": "saea-configured-family-qualified-v1",
            "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "ALL_MEMBERS_OPERATIONALLY_QUALIFIED", "members": qualified,
            "attempt_observations": observed, "attempt_metadata_pins": attempt_pins,
            "job_metadata_pins": job_pins, "read_id": registration["read_id"],
            "recipe": recipe_pin, "frozen_commit": frozen_check["commit"],
            "root_read_signed_by_this_function": False, "quality_values_reported": False,
            "model_contacts_added": 0, "scorer_contacts_added": 0}


def run(
    *,
    recipe_pin,
    supplement_pin,
    repo_root,
    data_root,
    output,
    learning_amendment_pin=None,
    reference_family_path=None,
):
    repo_root, data_root, output = map(
        lambda p: Path(p).resolve(), (repo_root, data_root, output)
    )
    require(
        output.is_relative_to(data_root / "analysis")
        and output != data_root / "analysis"
        and not output.exists(),
        "pilot analysis needs a fresh directory outside optimizer storage",
    )
    require(
        (learning_amendment_pin is None) == (reference_family_path is None),
        "learning export requires both owner222 and the frozen reference family",
    )
    recipe, registration, owner, supplement = load_documents(
        recipe_pin, supplement_pin, repo_root
    )
    family = {
        "family_id": recipe["family_id"],
        "expected_members": recipe["expected_members"],
        "read_registration": recipe_pin,
    }
    authority = CLI.require_read_registration(family, repo_root=repo_root)
    is_manual = "manual_architecture_registration" in recipe
    if is_manual:
        require(learning_amendment_pin is None and reference_family_path is None,
                "manual architecture never exports optimizer feedback")
    is_learning_context = "context_learning_registration" in recipe
    is_context = recipe.get("family_id") in context.READ_IDS
    is_panel = "system_panel_registration" in recipe
    validate = panel.validate_registration if is_panel else (
        context.validate_registration if is_context else validate_pilot_registration
    )
    evidence_reader = panel.read_evidence if is_panel else (context.read_evidence if is_context else read_pilot_evidence)
    analyzer = panel.analyze if is_panel else (context.analyze if is_context else analyze_pilot)
    recovery_pin = supplement.get("recovery_owner_decision")
    recovery_kwargs = {}
    if recipe.get("family_id") == context.RECOVERY_FAMILY:
        require(
            isinstance(recovery_pin, dict)
            and recovery_pin == registration.get("recovery_owner_decision"),
            "recovery decision pin differs or is absent",
        )
    if recovery_pin is not None:
        require(is_context, "recovery authority belongs only to its context family")
        recovery_kwargs = {"recovery": json.loads(_read_pin(recovery_pin, repo_root))}
    if is_panel:
        recovery_kwargs = panel.load_scope(registration, owner, supplement, repo_root=repo_root, recipe=recipe)
        if learning_amendment_pin is not None:
            expected_learning = supplement["learning_owner_decision"] if "evaluation" in recovery_kwargs else supplement["growth_owner_decision"]
            require(learning_amendment_pin == expected_learning,
                    "panel learning export must use its exact approved growth authority")
    if is_manual:
        recovery_kwargs = {"scope": architecture.validate_registration(
            recipe, registration, owner, authority, repo_root=repo_root, data_root=data_root)}
        evidence_reader, analyzer = architecture.read_evidence, architecture.analyze
    elif is_learning_context:
        require(learning_amendment_pin is None, "context baseline input uses its own qualification")
        context_learning._validate_scope(recipe, registration, owner, root=repo_root)
    else:
        validate(recipe, registration, owner, authority, **recovery_kwargs)
    reference_pin = pin(reference_family_path) if is_panel and reference_family_path else None
    if is_context:
        require(
            learning_amendment_pin is None, "context comparison has no proposer export"
        )
        pool = json.loads(_read_pin(owner["fixed_roster"], repo_root))["sample_ids"]
        require(
            len(pool) == len(set(pool)) == 400
            and content_hash(pool) == owner["sample_ids_sha256"]
            and recipe["sample_ids"] == pool[:20],
            "context roster must be the first twenty of the pinned owner224 pool",
        )
    roster_path = repo_root / recipe["analysis_roster"]["relpath"]
    roster = json.loads(_read_pin(recipe["analysis_roster"], repo_root))
    require(
        [r["sample_id"] for r in roster["items"]] == recipe["sample_ids"],
        "pilot analysis roster differs",
    )
    preliminary, metadata_pins = source_bindings(
        registration, pin(roster_path), data_root
    )
    metadata = preflight_family(preliminary, recipe["expected_members"])
    # Validate registration/roster against all operational manifests before seal parsing.
    for binding, (manifest, _) in zip(preliminary, metadata, strict=True):
        expected = registration["member_bindings"][binding["candidate_id"]]
        require(
            manifest["config"]["config_hash"] == expected["config_hash"]
            and manifest["attempt"]["attempt_id"] == expected["attempt_id"]
            and manifest["split"]["count"] == recipe["required_rows_per_member"]
            and set(manifest["split"]["ids"]) == set(recipe["sample_ids"]),
            "pilot manifest/roster differs from the frozen registration",
        )
    verified = [
        verify_bundle(Path(b["config"]["manifest"]["path"])) for b in preliminary
    ]
    require(
        all(v.attempt_state == "FINALIZED" for v in verified),
        "every registered member seal must verify",
    )
    if is_manual:
        for binding, bundle in zip(preliminary, verified, strict=True):
            member = registration["member_bindings"][binding["candidate_id"]]
            require(bundle.manifest.get("study_commit") == member["source_commit"]
                    and [r["sample_id"] for r in bundle.outputs_rows] == member["runtime_sample_ids"],
                    "manual sealed source or production order differs")
    metadata_source = json.loads(_read_pin(supplement["stratum_metadata"], repo_root))
    items = metadata_source["items"]
    require(
        len({r["sample_id"] for r in items}) == len(items),
        "duplicate stratum source identity",
    )
    ids = set(recipe["sample_ids"])
    strata = {
        r["sample_id"]: {k: r[k] for k in ("sample_id", "utterance_id", "stratum")}
        for r in items
        if r["sample_id"] in ids
    }
    require(
        set(strata) == ids
        and all(
            strata[r["sample_id"]]["utterance_id"] == r["utterance_id"]
            for r in roster["items"]
        ),
        "pilot stratum identity differs",
    )
    output.mkdir(parents=True, exist_ok=False)
    bindings = []
    for binding, bundle, (_, job) in zip(preliminary, verified, metadata, strict=True):
        cid = binding["candidate_id"]
        receipt = write_complete_saved_score_receipt(
            output / cid / "saved-score", job_id=job["job_id"], verified_bundle=bundle
        )
        config = {
            **binding["config"],
            "schema": "saea-reward-link-artifact-config-v1",
            "complete_score_receipt": {
                "path": str(receipt.path),
                "sha256": receipt.sha256,
                "cell_id": receipt.cell_id,
            },
            "projection": supplement["projection"],
        }
        artifact = output / cid / "reward-links.json"
        build_reward_link_artifact(config, artifact)
        bindings.append(
            {"candidate_id": cid, "config": config, "artifact": pin(artifact)}
        )
    if is_learning_context:
        qualified = context_learning._qualified_feedback(bindings, recipe_pin=recipe_pin, repo_root=repo_root)
        evidence = CompleteSystemFeedback(canonical(qualified[0]))
        analyzer = context_read.analyze
        report = analyzer(evidence, recipe=recipe, registration=registration,
                          protocol=owner, roster=strata, supplement=supplement)
    else:
        evidence = evidence_reader(
            bindings,
            recipe=recipe,
            registration=registration,
            owner=owner,
            authority=authority,
            **recovery_kwargs,
        )
        report = analyzer(
            evidence,
            recipe=recipe,
            registration=registration,
            roster=strata,
            supplement=supplement,
            **(recovery_kwargs if is_manual else {}),
        )
    process_pin = supplement.get("process_diagnostics") if is_manual else None
    if is_manual:
        report["process_diagnostics_status"] = "UNAVAILABLE_UNTIL_QUALIFIED_PINNED_DERIVATIVE"
        require(recipe.get("process_diagnostics") == process_pin,
                "manual process derivative must be pinned by the exact root READ recipe")
        if process_pin is not None:
            process_document = json.loads(_read_pin(process_pin, data_root))
            score_sources = {}
            for binding in bindings:
                cid = binding["candidate_id"]
                receipt = _absolute_json(binding["config"]["complete_score_receipt"])
                score_sources[cid] = {"manifest": binding["config"]["manifest"],
                                     "score_result": receipt["score_result"],
                                     "attempt_id": registration["member_bindings"][cid]["attempt_id"]}
            report["process_comparison"] = architecture.combine_process(
                recipe=recipe, business=report, process=process_document,
                timing=process_document["timing"], scope=recovery_kwargs["scope"],
                score_sources=score_sources)
            report["process_diagnostics_status"] = "COMPLETE_SOURCE_BOUND_V2_DERIVATIVE"
    require(
        CLI.require_read_registration(family, repo_root=repo_root) == authority,
        "root READ changed during pilot analysis",
    )
    load_documents(recipe_pin, supplement_pin, repo_root)
    if process_pin is not None:
        _read_pin(process_pin, data_root)
    if is_manual:
        require(all(pin(b["config"]["manifest"]["path"]) == b["config"]["manifest"]
                    for b in preliminary), "manual original manifest changed during read")
        require(architecture.validate_registration(recipe, registration, owner, authority,
                repo_root=repo_root, data_root=data_root) == recovery_kwargs["scope"],
                "manual registration or source changed during read")
    if recovery_pin is not None:
        _read_pin(recovery_pin, repo_root)
    if is_context:
        _read_pin(owner["fixed_roster"], repo_root)
    if is_panel:
        require(panel.load_scope(registration, owner, supplement, repo_root=repo_root, recipe=recipe) == recovery_kwargs,
                "panel scope changed during read")
    for source in (recipe["analysis_roster"], supplement["stratum_metadata"]):
        _read_pin(source, repo_root)
    require(
        all(pin(p["path"]) == p for p in metadata_pins),
        "official job metadata changed during read",
    )
    learning = None
    if learning_amendment_pin is not None:
        amendment = json.loads(_read_pin(learning_amendment_pin, repo_root))
        reference = CLI.read_family(reference_family_path, repo_root=repo_root)
        learning = evidence.learning_projection(
            amendment=amendment, reference=reference
        )
        _read_pin(learning_amendment_pin, repo_root)
        if reference_pin is not None:
            require(pin(reference_family_path) == reference_pin, "frozen reference family changed during export")
        report["learning_projection"] = {
            "owner_decision": learning_amendment_pin,
            "scope": f"All {len(learning.as_json()['summaries'])} admitted L members only; all {recipe['required_rows_per_member']} cases; no B outcomes; not formal adoption.",
        }
    report["read_at_utc"] = datetime.now(timezone.utc).isoformat()
    report["source_pins"] = {
        "recipe": recipe_pin,
        "supplement": supplement_pin,
        "job_metadata": metadata_pins,
        "reader": pin(__file__),
        "analyzer": pin(Path(sys.modules[analyzer.__module__].__file__)),
    }
    if process_pin is not None:
        report["source_pins"]["process_diagnostics"] = process_pin
    if recovery_pin is not None:
        report["source_pins"]["recovery_authority"] = recovery_pin
    CLI.write_new(output / "family.json", {**family, "bindings": bindings})
    CLI.write_new(output / "evidence.json", evidence.as_json())
    if learning is not None:
        CLI.write_new(output / "learning-feedback.json", learning.as_json())
    CLI.write_new(output / "report.json", report)
    lines = [
        f"# Exploratory {recipe['required_rows_per_member']}-row whole-system panel",
        "",
        report["interpretation"],
        "",
        "| Member | Official SLU-F1 | Intent | Reliable completion | Model calls | Tool calls |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for cid, row in report["official_summaries"].items():
        lines.append(
            f"| {cid} | {100 * row['slu_f1']:.4f}% | {100 * row['intent']:.2f}% | "
            f"{100 * row['reliable_completion_rate']:.2f}% | {row['model_calls']} | {row['tool_calls']} |"
        )
    lines += [
        "",
        "The JSON retains own-A/A contrasts, clustered confidence intervals, every stratum, "
        "equal-stratum descriptions, actual costs, whole-answer repair/damage associations and source pins.",
        "No optimizer, policy, queue, runtime, scorer or sampling authority was changed.",
        "",
    ]
    with (output / "README.md").open("x") as f:
        f.write("\n".join(lines))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("recipe", "supplement", "data-root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--learning-amendment", type=Path)
    parser.add_argument("--reference-family", type=Path)
    args = parser.parse_args()
    root = args.repo_root.resolve()

    def relative_pin(path):
        p = path.resolve()
        require(
            p.is_relative_to(root), "analysis registration must be in the repository"
        )
        return {"relpath": p.relative_to(root).as_posix(), "sha256": pin(p)["sha256"]}

    report = run(
        recipe_pin=relative_pin(args.recipe),
        supplement_pin=relative_pin(args.supplement),
        repo_root=root,
        data_root=args.data_root,
        output=args.output,
        learning_amendment_pin=relative_pin(args.learning_amendment)
        if args.learning_amendment
        else None,
        reference_family_path=args.reference_family,
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "output": str(args.output),
                "contacts_added": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
