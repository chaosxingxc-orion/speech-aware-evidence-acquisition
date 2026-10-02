"""Read the qualified initial family; preserve original scores and all trajectories."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
from speech_aware_evidence_acquisition.analysis.null_calibration import pooled_f1
from speech_aware_evidence_acquisition.analysis.paired import resampled_statistic


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    module_spec = importlib.util.spec_from_file_location("system_text_search", REPO / "scripts/system_text_search.py")
    cli = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(cli)
    family = cli.read_family(args.family, repo_root=REPO).as_json()
    assert family["family_id"] == "initial" and set(family["summaries"]) == {"seed", "seed-aa"}
    groups = family["feedback"]["groups"]
    ids = [row["sample_id"] for row in groups]
    roster_path = REPO / "docs/receipts/rosters/slurp-stage3-construction-r01c.json"
    roster = {r["sample_id"]: r for r in json.loads(roster_path.read_text())["items"]}
    assert len(ids) == 400 and set(ids) <= set(roster)
    counts = {cid: {} for cid in ("seed", "seed-aa")}
    costs = {cid: Counter() for cid in counts}
    terminals = {cid: Counter() for cid in counts}
    for group in groups:
        for member in group["members"]:
            cid = member["candidate_id"]
            counts[cid][group["sample_id"]] = member["native_counts"]
            execution = member["execution"]
            for key in ("prompt_tokens", "completion_tokens", "model_calls", "tool_calls"):
                if execution[key] is not None:
                    costs[cid][key] += execution[key]
            terminals[cid][execution["delivery_kind"]] += 1
    fields = tuple(tuple(f"slu_f1_{axis}_{kind}" for axis in ("word", "char")) for kind in ("tp", "fp", "fn"))

    def slu(cid, selected):
        return pooled_f1(counts[cid], selected, fields)

    def intent(cid, selected):
        return math.fsum(counts[cid][sid]["scenario_action_exact"] for sid in selected) / len(selected)

    for cid in counts:
        assert abs(slu(cid, ids) - family["summaries"][cid]["slu_f1"]) < 1e-6
        assert abs(intent(cid, ids) - family["summaries"][cid]["intent"]) < 1e-6
    contrasts = {}
    for name, metric in (("slu_f1", slu), ("intent", intent)):
        estimate = resampled_statistic(sample_ids=ids,
            statistic=lambda selected, m=metric: m("seed-aa", selected) - m("seed", selected),
            cluster_of=lambda sid: roster[sid]["utterance_id"],
            seed=20261001, n_replicates=10000, ci_level=0.95)
        contrasts[name] = estimate.as_json()
    strata = []
    for label in sorted({roster[sid]["stratum"] for sid in ids}):
        selected = [sid for sid in ids if roster[sid]["stratum"] == label]
        strata.append({"stratum": label, "n": len(selected),
                       **{cid: {"slu_f1": slu(cid, selected), "intent": intent(cid, selected)} for cid in counts}})
    equal = {cid: {metric: math.fsum(row[cid][metric] for row in strata) / len(strata)
                   for metric in ("slu_f1", "intent")} for cid in counts}
    report = {
        "schema": "saea-system-text-initial-read-v1", "status": "DESCRIPTIVE",
        "read_at_utc": datetime.now(timezone.utc).isoformat(),
        "read_authority": family["read_authority"],
        "reference": {k: v for k, v in family["reference"].items() if k != "sample_ids"},
        "sample_count": len(ids), "cluster_count": len({roster[sid]["utterance_id"] for sid in ids}),
        "summaries": family["summaries"], "aa_minus_seed": contrasts, "per_stratum": strata,
        "equal_stratum_macro": equal,
        "equal_stratum_definition": "Arithmetic mean of the eighteen within-scenario pooled F1 values and intent accuracies; descriptive, not the official pooled metric.",
        "costs": costs, "terminal_kinds": terminals,
        "source_pins": [{"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                        for p in (args.family, roster_path, Path(__file__))],
        "interpretation": "Initial feedback and same-policy A/A instrument observation only. No candidate, feedback-learning benefit, causal node contribution or adoption is established.",
        "contacts_added": {"model": 0, "scorer": 0},
    }
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    lines = ["# DESCRIPTIVE: initial system-text feedback", "", report["interpretation"], "",
             "| Member | Rows | Official SLU-F1 | Intent | Reliable completion | Model calls | Knowledge calls |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for cid, row in report["summaries"].items():
        lines.append(f"| {cid} | 400 | {100*row['slu_f1']:.4f}% | {100*row['intent']:.2f}% | {100*row['reliable_completion_rate']:.2f}% | {row['model_calls']} | {row['tool_calls']} |")
    lines += ["", f"Frozen F_ref: {report['reference']['f1']:.16f}.", ""]
    for metric, row in contrasts.items():
        lines.append(f"A/A minus seed {metric}: {100*row['point_estimate']:+.4f} pp; CI95 [{100*row['ci_low']:.4f}, {100*row['ci_high']:.4f}] pp.")
    lines += ["", "Both runs offered the knowledge opportunity and recorded zero actual tool calls. This initial pair cannot establish targeted knowledge-consumption benefit.", "",
              "| Scenario | n | Seed SLU-F1 | A/A SLU-F1 | Seed intent | A/A intent |",
              "|---|---:|---:|---:|---:|---:|"]
    for row in strata:
        lines.append(f"| {row['stratum']} | {row['n']} | {100*row['seed']['slu_f1']:.2f}% | {100*row['seed-aa']['slu_f1']:.2f}% | {100*row['seed']['intent']:.2f}% | {100*row['seed-aa']['intent']:.2f}% |")
    lines += ["", report["equal_stratum_definition"], "", "All failures, abstentions and unchanged outcomes remain in feedback. Raw outputs, scores, original failed score-entry evidence and STOP were not modified. The recovery is owner216's single approved scoring entry, not a new generation or second scientific score. Historical roster exposure limits interpretation."]
    (args.output / "README.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"output": str(args.output), "summaries": report["summaries"], "aa_minus_seed": contrasts, "equal_stratum_macro": equal}))


if __name__ == "__main__":
    main()
