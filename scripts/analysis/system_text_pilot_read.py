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
    recipe = json.loads(_read_pin(recipe_pin, root))
    supplement = json.loads(_read_pin(supplement_pin, root))
    require(
        supplement.get("schema")
        == (
            "saea-system-panel-analysis-supplement-v1"
            if "system_panel_registration" in recipe
            else "saea-context-analysis-supplement-v1"
            if recipe.get("family_id") in context.READ_IDS
            else "saea-pilot-analysis-supplement-v1"
        )
        and supplement.get("recipe") == recipe_pin,
        "analysis supplement names another recipe",
    )
    key = "system_panel_registration" if "system_panel_registration" in recipe else "pilot_registration"
    registration = json.loads(_read_pin(recipe[key], root))
    owner = json.loads(_read_pin(supplement["owner_decision"], root))
    return recipe, registration, owner, supplement


def source_bindings(registration, roster_pin, data_root):
    """Read all operational job metadata before any saved score is opened."""
    result, metadata_pins = [], []
    for cid, member in registration["member_bindings"].items():
        directory = data_root / "runs" / member["run_id"] / member["attempt_id"]
        jobs_path, summary_path = (
            directory / "score-jobs.jsonl",
            directory / "score-batch/batch-summary.json",
        )
        metadata_pins.extend([pin(jobs_path), pin(summary_path)])
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
        result.append(
            {
                "candidate_id": cid,
                "config": {
                    "manifest": pin(manifest),
                    "construction_roster": roster_pin,
                },
            }
        )
    return result, metadata_pins


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
    )
    require(
        CLI.require_read_registration(family, repo_root=repo_root) == authority,
        "root READ changed during pilot analysis",
    )
    load_documents(recipe_pin, supplement_pin, repo_root)
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
