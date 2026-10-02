#!/usr/bin/env python3
"""Gate the four frozen DEV systems, then reuse the standard paired analysis.

This endpoint report is not an optimizer feedback artifact. It neither scores,
dispatches, countersigns, selects a new policy nor changes the learning archive.
Register the exact recipe before execution and countersign READ after the whole
family qualifies. Attach hash-pinned operational artifacts in a separate family
specification once available; never invent their hashes before generation.
"""
import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

from speech_aware_evidence_acquisition.core.bundle.verify import verify_bundle
from speech_aware_evidence_acquisition.core.scoring_receipt import (
    SavedScoreReceiptRef, load_complete_score_receipt, verify_complete_score_receipt,
)
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_dev_stage import SLOTS, validate_dev_registration
from speech_aware_evidence_acquisition.rails.system_search_protocol import stage_for
from speech_aware_evidence_acquisition.rails.system_search_archive import OBJECTIVES, pareto_frontier
from speech_aware_evidence_acquisition.rails.system_text_feedback import _absolute_json, _row_cost_and_terminal
from speech_aware_evidence_acquisition.rails.system_text_policy import _read_pin, require, sha


def _module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


SCRIPT = Path(__file__).resolve()
CLI = _module("_saea_dev_read_authority", SCRIPT.parents[1] / "system_text_search.py")
PAIRED = _module("_saea_dev_standard_paired", SCRIPT.with_name("stage3_paired_read.py"))
COMPARISONS = {
    "same-request-null": ["seed", "seed-aa"],
    "primary-learning-minus-blind": ["B-frozen", "L-frozen"],
    "secondary-learning-minus-seed": ["seed", "L-frozen"],
    "learning-versus-in-chain-aa": ["seed-aa", "L-frozen"],
    "blind-versus-in-chain-aa": ["seed-aa", "B-frozen"],
}


def _authority(family, repo_root):
    return CLI.require_read_registration(family, repo_root=repo_root, expected_split_role="dev")


def _confined(path, root):
    p = Path(path)
    require(p.is_absolute() and p.resolve().is_relative_to(root.resolve()), "source escapes its registered root")
    return p.resolve()


def preflight(family, *, repo_root, data_root):
    """Inspect all operational metadata, all seals, then all complete score receipts.

    The shared verifier parses sealed artifacts to verify custody; no score is
    interpreted and no pair analysis starts until every member passes it.
    """
    repo_root, data_root = Path(repo_root).resolve(), Path(data_root).resolve()
    require(set(family) == {"family_id", "expected_members", "read_registration", "bindings"}
            and family["family_id"] == "dev", "DEV family fields differ; feedback references are forbidden")
    authority = _authority(family, repo_root)
    recipe = json.loads(_read_pin(family["read_registration"], repo_root))
    protocol = json.loads(_read_pin(recipe["protocol"], repo_root))
    registration = validate_dev_registration(authority.get("stage_registration"), protocol=protocol)
    require(set(family["bindings"]) == SLOTS and set(recipe["attempts"]) == SLOTS,
            "all four endpoint members and attempts are required")
    require(recipe["comparisons"] == COMPARISONS, "endpoint comparisons differ from the fixed read")
    analysis = recipe["analysis"]
    require(set(analysis) == {"cluster_key", "seed", "draws", "gold_bank"}
            and analysis["cluster_key"] == "utterance_id"
            and type(analysis["seed"]) is int and type(analysis["draws"]) is int and analysis["draws"] > 0,
            "declare the paired utterance resampling before the read")
    bank = analysis["gold_bank"]
    require(set(bank) == {"data_relpath", "sha256", "roster"} and bank["roster"] == "dev2000-added",
            "the endpoint requires its exact offline DEV stratum source")
    require(not Path(bank["data_relpath"]).is_absolute(), "gold bank must be data relative")
    _confined(data_root / bank["data_relpath"], data_root)
    sha(bank["sha256"])
    roster = json.loads(_read_pin(recipe["roster"], repo_root))
    ids = [item["sample_id"] for item in roster["items"]]
    require(roster.get("split_role") == "dev" and roster.get("carrier_lock_key") == "slurp"
            and ids == stage_for(protocol, "dev")["sample_ids"]
            and content_hash(ids) == registration["roster_sha256"], "endpoint roster differs")
    metadata, sources = {}, {}
    for cid in sorted(SLOTS):
        b = family["bindings"][cid]
        require(set(b) == {"manifest", "complete_score_receipt", "score_batch"}, "member source fields differ")
        run, attempt = family["expected_members"][cid], recipe["attempts"][cid]
        require(isinstance(attempt, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,240}", attempt),
                "attempt identity is not confined")
        root = data_root / "runs" / run / attempt
        path = _confined(b["manifest"]["path"], root)
        require(path == (root / f"{run}.run-manifest.json").resolve(), "manifest belongs to another attempt")
        m = _absolute_json(b["manifest"])
        require(m.get("status") == "COMPLETED" and m.get("run_id") == run
                and m.get("plan", {}).get("split_role") == "dev"
                and m.get("config", {}).get("config_hash") == registration["evaluation"]["member_bindings"][cid]["config_hash"]
                and m.get("scorers") == ["slurp-slu-official", "cost"], "member identity, config or DEV scope differs")
        split = m["split"]
        require(split.get("role") == "dev" and split.get("carrier_lock_key") == "slurp"
                and split.get("count") == 1000 and split.get("ids") == sorted(ids)
                and split.get("identity_hash") == roster["split_identity_hash"], "member cohort differs")
        state_path = data_root / "attempts" / run / f"{attempt}.json"
        require(m["attempt"]["attempt_id"] == attempt
                and Path(m["attempt"]["state_path"]).resolve() == state_path.resolve(), "attempt binding differs")
        state = CLI.read(state_path)
        require(state.get("state") == "FINALIZED" and state.get("run_id") == run
                and state.get("attempt_id") == attempt, "complete family member is not finalized")
        jobs_path = root / "score-jobs.jsonl"
        jobs = [json.loads(line) for line in jobs_path.read_text().splitlines() if line.strip()]
        require(len(jobs) == 1 and jobs[0]["job_id"] == attempt
                and Path(jobs[0]["manifest"]).resolve() == path, "exactly one original score job is required")
        batch_path = _confined(b["score_batch"]["path"], root)
        require(batch_path == (root / "score-batch/batch-summary.json").resolve(), "score batch source differs")
        batch = _absolute_json(b["score_batch"])
        require(batch.get("job_count") == batch.get("succeeded") == 1 and batch.get("failed") == 0
                and len(batch.get("jobs", [])) == 1, "one successful official score and no failure are required")
        job = batch["jobs"][0]
        require(job.get("status") == "succeeded" and job.get("returncode") == 0
                and job.get("job_id") == attempt and Path(job["manifest"]).resolve() == path,
                "successful job identity differs")
        rp = b["complete_score_receipt"]
        ref = SavedScoreReceiptRef(rp["cell_id"], _confined(rp["path"], data_root), rp["sha256"])
        receipt = load_complete_score_receipt(ref)
        require(ref.cell_id == attempt and receipt["job_id"] == attempt and receipt["manifest"] == b["manifest"]
                and receipt["scorers"] == m["scorers"], "complete score receipt identity differs")
        metadata[cid] = {"manifest": m, "path": path, "receipt": ref}
        sources[cid] = {**b, "state_sha256": PAIRED.digest(state_path), "score_jobs_sha256": PAIRED.digest(jobs_path)}
    bundles = {}
    for cid, item in metadata.items():
        bundles[cid] = verify_bundle(item["path"])
        require(bundles[cid].attempt_state == "FINALIZED", "endpoint seal is not finalized")
    for cid, item in metadata.items():
        verify_complete_score_receipt(item["receipt"], bundles[cid])
    require(_authority(family, repo_root) == authority, "READ authority changed during verification")
    return {"authority": authority, "recipe": recipe, "metadata": metadata,
            "sources": sources, "sample_ids": ids, "split_identity_hash": roster["split_identity_hash"]}


def _execution(manifest, sample_ids):
    rows = _row_cost_and_terminal(manifest)
    require(set(rows) == set(sample_ids), "terminal cohort differs from endpoint registration")
    summary = {"rows": len(rows)}
    for key in ("model_calls", "tool_calls", "missing_model_responses", "prompt_tokens", "completion_tokens"):
        values = [r[key] for r in rows.values()]
        summary[key] = None if any(v is None for v in values) else sum(values)
    for key in ("reliable_completion", "abstained"):
        summary[key + "_rate"] = sum(r[key] for r in rows.values()) / len(rows)
    for key in ("role_contacts", "tool_events"):
        summary[key] = {name: sum(r[key].get(name, 0) for r in rows.values())
                        for name in sorted({name for r in rows.values() for name in r[key]})}
    return summary


def run(family, *, repo_root, data_root, output):
    """Write one descriptive endpoint report, outside every optimizer input route."""
    output = Path(output).resolve()
    require(output.is_relative_to((Path(data_root).resolve() / "analysis"))
            and output != (Path(data_root).resolve() / "analysis"),
            "endpoint reports must stay in a new data-root analysis directory, outside optimizer inputs")
    require(not output.exists(), "analysis output already exists; preserve prior reports")
    ctx = preflight(family, repo_root=repo_root, data_root=data_root)
    recipe, authority = ctx["recipe"], ctx["authority"]
    execution = {cid: _execution(item["manifest"], ctx["sample_ids"]) for cid, item in ctx["metadata"].items()}
    require(_authority(family, repo_root) == authority, "READ authority changed before paired analysis")
    output.mkdir(parents=True, exist_ok=False)
    analysis, passes, points = recipe["analysis"], {}, {}
    bank = analysis["gold_bank"]
    ext = PAIRED.Extensions(per_scenario=True, frontier=True, gold_bank=bank["data_relpath"],
        gold_bank_sha256=bank["sha256"], gold_bank_roster=bank["roster"], strata_source="gold-bank")
    for name, (left, right) in COMPARISONS.items():
        def arm(cid):
            return PAIRED.CORE.ArmSpec(cid, family["expected_members"][cid], recipe["attempts"][cid])
        args = PAIRED.CORE.Args(stage="all", left=arm(left), right=arm(right), scorer_id="slurp-slu-official",
            roster_relpath=recipe["roster"]["relpath"], cluster_key=analysis["cluster_key"],
            analysis_root=output / name, repo_root=Path(repo_root), data_root=Path(data_root),
            seed=analysis["seed"], draws=analysis["draws"], recipe_id=authority["read_run_id"], title=name,
            split_identity_hash=ctx["split_identity_hash"], expected_split_role="dev")
        PAIRED.run_pair(args, ext)
        strata = CLI.read(args.analysis_root / "per-scenario-tables.json")
        require(strata.get("status") == "AVAILABLE"
                and sum(strata.get("strata_rows", {}).values()) == len(ctx["sample_ids"]),
                "complete natural-mixture and equal-stratum tables are required")
        frontier = CLI.read(args.analysis_root / "frontier.json")
        for side, cid in (("left", left), ("right", right)):
            quality = frontier[side]
            point = {"member": cid, "bundle_id": authority["stage_registration"]["finalists"]["members"][cid],
                "cohort_id": authority["stage_registration"]["roster_sha256"],
                "slu_f1": quality["official_slu_pct"] / 100, "intent": quality["official_intent_pct"] / 100,
                "model_calls": execution[cid]["model_calls"], "tool_calls": execution[cid]["tool_calls"]}
            require(cid not in points or points[cid] == point, "shared member quality changed between paired reads")
            points[cid] = point
        passes[name] = {"left": left, "right": right, "path": name,
                        "verdict_sha256": PAIRED.digest(args.analysis_root / "verdict.json")}
    # Recheck operational custody as well as root authority before publishing.
    after = preflight(family, repo_root=repo_root, data_root=data_root)
    require(after["sources"] == ctx["sources"] and after["authority"] == authority,
            "family sources or READ authority changed during analysis")
    report = {"schema": "saea-system-text-dev-report-v1", "status": "DESCRIPTIVE_ROOT_INTERPRETATION_REQUIRED",
        "read_authority": authority, "sources": ctx["sources"], "execution": execution, "comparisons": passes,
        "pareto": {"objectives": OBJECTIVES, "points": list(points.values()),
            "non_dominated_members": [r["member"] for r in pareto_frontier(list(points.values()), identity_key="member")],
            "interpretation": "Same-cohort point-estimate frontier only. Preserve A/A separately; no averaging, adoption or significance claim."},
        "optimizer_feedback_allowed": False, "model_contacts_added": 0, "scorer_contacts_added": 0,
        "limitations": ["Historically exposed DEV regression, not independent confirmatory evidence.",
            "One registered learning sequence; no claim of stable recursive self-improvement.",
            "Judge registered effects against the same-chain null and confidence intervals; do not decide on strata.",
            "Missing token usage remains unknown; no claim of matched realized total compute.",
            "No automatic adoption or policy update follows from this report."],
        "analysis_sources": {p.name: PAIRED.digest(p) for p in (SCRIPT, PAIRED._DRIVER_PATH, PAIRED.CORE_PATH)}}
    CLI.write_new(output / "report.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("family", "repo-root", "data-root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args(argv)
    result = run(CLI.read(args.family), repo_root=args.repo_root, data_root=args.data_root, output=args.output)
    print(json.dumps({"status": result["status"], "report": str(args.output / "report.json"), "contacts_added": 0}))


if __name__ == "__main__":
    main()
