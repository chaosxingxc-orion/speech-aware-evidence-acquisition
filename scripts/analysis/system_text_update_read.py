#!/usr/bin/env python3
"""Read one complete TRAIN update for root review, without selecting or dispatching.

The frozen recipe supplies the resampling plan; the frozen protocol supplies
roster metadata. The shared reader rechecks every member, seal, official score
and exact READ authority. This report is never an isolated proposer input.
"""

import argparse
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from speech_aware_evidence_acquisition.analysis.system_text_update import analyze_update
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_search_protocol import stage_for
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    _read_pin,
    require,
)

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "_system_text_update_read_gate", ROOT / "scripts/system_text_search.py"
)
CLI = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = CLI
spec.loader.exec_module(CLI)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def render(report):
    lines = [
        "# DESCRIPTIVE: complete system-text update",
        "",
        report["interpretation"],
        "",
        "| Member | SLU-F1 | Intent | Reliable completion | Model calls | Tool calls |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for cid, row in report["official_summaries"].items():
        lines.append(
            f"| {cid} | {100 * row['slu_f1']:.4f}% | {100 * row['intent']:.4f}% | {100 * row['reliable_completion_rate']:.2f}% | {row['model_calls']} | {row['tool_calls']} |"
        )
    lines += [
        "",
        "## Paired differences",
        "",
        "Differences and confidence intervals below are percentage points.",
        "",
        "| Branch / contrast | Metric | Difference | CI95 |",
        "|---|---|---:|---|",
    ]
    for branch, data in report["branches"].items():
        for name, pair in data["comparisons"].items():
            for metric in ("slu_f1", "intent"):
                r = pair[metric]
                lines.append(
                    f"| {branch} / {name} | {metric} | {100 * r['point_estimate']:+.4f} | [{100 * r['ci_low']:+.4f}, {100 * r['ci_high']:+.4f}] |"
                )
    lines += [
        "",
        "## Strata",
        "",
        report["equal_stratum_definition"],
        "",
        "| Stratum | n | Member | SLU-F1 | Intent |",
        "|---|---:|---|---:|---:|",
    ]
    for s in report["per_stratum"]:
        for cid, row in s["members"].items():
            lines.append(
                f"| {s['stratum']} | {s['n']} | {cid} | {100 * row['slu_f1']:.4f}% | {100 * row['intent']:.4f}% |"
            )
    lines += [
        "",
        "## Equal-stratum descriptive view",
        "",
        "| Member | SLU-F1 | Intent |",
        "|---|---:|---:|",
    ]
    for cid, row in report["equal_stratum_macro"].items():
        lines.append(
            f"| {cid} | {100 * row['slu_f1']:.4f}% | {100 * row['intent']:.4f}% |"
        )
    lines += [
        "",
        "The JSON retains every measured version, same-cohort frontier, terminal disposition and unknown cost. Root must apply the registered own-null protection and tie-breaks before recording any parent. This report grants no scientific adoption or additional sampling.",
        "",
    ]
    return "\n".join(lines)


def run(family_path, *, protocol_path, repo_root, data_root, output):
    repo_root, data_root, output = (
        Path(repo_root).resolve(),
        Path(data_root).resolve(),
        Path(output).resolve(),
    )
    require(
        output.is_relative_to(data_root / "analysis")
        and output != data_root / "analysis",
        "root reports must remain outside the optimizer archive",
    )
    require(not output.exists(), "analysis output already exists")
    family_path, protocol_path = (
        Path(family_path).resolve(),
        Path(protocol_path).resolve(),
    )
    require(
        protocol_path.is_relative_to(repo_root), "protocol must be a repository source"
    )
    implementation = [
        Path(__file__).resolve(),
        Path(sys.modules[analyze_update.__module__].__file__).resolve(),
    ]
    original = {p: digest(p) for p in (family_path, protocol_path, *implementation)}
    family = CLI.read(family_path)
    # This is the only path to scientific data; never analyze a cached feedback JSON.
    feedback = CLI.read_family(family_path, repo_root=repo_root)
    authority = feedback.as_json()["read_authority"]
    require(
        authority["recipe"] == family["read_registration"], "family READ recipe changed"
    )
    recipe = json.loads(_read_pin(family["read_registration"], repo_root))
    protocol = CLI.read(protocol_path)
    require(
        recipe["system_search_evaluation"]["protocol_sha256"] == content_hash(protocol),
        "protocol differs from registration",
    )
    stage = stage_for(protocol, feedback.as_json()["family_id"])
    roster_pin = protocol["source_rosters"][stage["source_roster"]]
    source = json.loads(_read_pin(roster_pin, repo_root))
    items = source["items"]
    require(
        len({r["sample_id"] for r in items}) == len(items),
        "duplicate roster source identity",
    )
    ids = set(stage["sample_ids"])
    roster = {r["sample_id"]: r for r in items if r["sample_id"] in ids}
    report = analyze_update(feedback, protocol=protocol, recipe=recipe, roster=roster)
    require(
        CLI.require_read_registration(family, repo_root=repo_root) == authority,
        "READ authority changed during analysis",
    )
    require(
        all(digest(p) == value for p, value in original.items()),
        "input changed during analysis",
    )
    _read_pin(roster_pin, repo_root)
    _read_pin(family["read_registration"], repo_root)
    report["read_at_utc"] = datetime.now(timezone.utc).isoformat()
    report["source_pins"] = {
        "family": {"path": str(family_path), "sha256": original[family_path]},
        "protocol": {
            "relpath": protocol_path.relative_to(repo_root).as_posix(),
            "sha256": original[protocol_path],
        },
        "roster": roster_pin,
        "recipe": family["read_registration"],
        "reader": {"path": str(Path(__file__).resolve()), "sha256": digest(__file__)},
    }
    report["source_pins"]["analyzer"] = {
        "path": str(implementation[1]),
        "sha256": original[implementation[1]],
    }
    output.mkdir(parents=True, exist_ok=False)
    (output / "report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    (output / "README.md").write_text(render(report), encoding="utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("family", "protocol", "data-root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    report = run(
        args.family,
        protocol_path=args.protocol,
        repo_root=args.repo_root,
        data_root=args.data_root,
        output=args.output,
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "family_id": report["family_id"],
                "status": report["status"],
            }
        )
    )


if __name__ == "__main__":
    main()
