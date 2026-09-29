#!/usr/bin/env python3
"""Append cell COMP-1b's five DRAFT exposure-ledger rows: the arm, its four-row
smoke, their two FIT spend identities, and one READ row for the paired analysis.
No A/A row: the comparator is the existing sealed in-chain A/A cell COMP-1 already
flew and registered; it is not re-registered here. Idempotent: replaces its own
rows in place if run again, refuses a partial set. No cell may contain a literal
'|'.

    python scripts/flights/comp1/append_slurp_comp1b_ledger.py \\
        --package-dir docs/readiness/2026-09-29-slurp-stage3-comp1b-fold-a-v1 \\
        --study-commit <sha> --registered-at 2026-09-29T16:00:00.000000+00:00
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[3]
LEDGER = "docs/exposure-ledger.md"
COMPARATOR_RUN = "SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1"

MODEL_TOOL = (
    "Frozen Q4_K_M decoder-only c98304 np4 max512; promoted EVO-FOLDS-V2 speech packets; NO native tool authority on "
    "any role; Perception / Reviewer / Planner prompt bytes cell COMP-1's own (the locked PLAN arm's); the Solver "
    "under the locked plan's own non-cited program (the citation contract removed)"
)
INHERITED = (
    "TRAIN Fold A discovery rows already exposed by the sealed dual-store anchor, the released direct anchor, cells "
    "B0/B0r, B1 and its twin, B4b, B4b-rep, B5e, B7a, B7a-v2, B8b-anchor, B1-notool, PLAN, PLANr, ROLL-2, CONV, KPROBE "
    "and COMP-1 (arm, in-chain A/A and smoke); this cell adds no new row to the fold and opens no split. Prior "
    "exposure is inherited in full."
)


def rd(path: str) -> str:
    return io.open(REPO_ROOT / path, encoding="utf-8", newline="").read()


def rdjson(path: str) -> dict:
    return json.loads(rd(path))


def sha_file(path: str) -> str:
    return hashlib.sha256((REPO_ROOT / path).read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--package-dir", required=True)
    parser.add_argument("--study-commit", required=True)
    parser.add_argument("--registered-at", required=True)
    parser.add_argument("--branch", default="fable/comp1b")
    parser.add_argument("--worktree", default="/home/chao/saea-worktrees/fable-comp1b")
    args = parser.parse_args(argv)
    os.chdir(REPO_ROOT)
    package = args.package_dir.rstrip("/").replace("\\", "/")
    stamp = args.registered_at

    facts = rdjson(package + "/registered-facts-v1.json")
    ids = facts["cells"]
    caps = ids["arm"]["family_budget"] if "family_budget" in ids["arm"] else json.loads(rd(package + "/generation-plan-registered-v1.json"))["family_budget"]
    smoke_caps = json.loads(rd(package + "/smoke-generation-plan-registered-v1.json"))["family_budget"]
    measurement = facts["stage3_measurement"]
    decision_id = "slurp-stage3-comp1b-fold-a-admission-v1"
    decision_relpath = f"coordination/slurp-stage3-comp1b-fold-a-v1/root-admission-v1.json"
    config_test = "tests/unit/test_comp1b_config.py"
    attribution_note = "docs/results/2026-09-29-slurp-comp1-slu-harm-attribution.md"
    attribution_branch = "fable/comp1slu"
    comp1_read = "docs/results/2026-09-29-slurp-comp1-fold-a-read.md"

    prose = {
        "arm": "Cell COMP-1b: cell COMP-1 minus the citation contract (2026-09-29 SLU-harm attribution, branch fable/comp1slu): the agreement term and the centroid boundary key alone, COMP-1's own committed bytes, byte for byte; the citation contract's four leaf paths reverted to the locked plan's non-cited program",
        "smoke": "Four-row form smoke of cell COMP-1b: the same two composed actions (agreement term, centroid key) on the first four rows of the unchanged roster, under the locked plan's own non-cited Solver program",
    }

    def plan_ids(key: str) -> dict:
        gen = json.loads(rd(f"{package}/{'smoke-' if key == 'smoke' else ''}generation-plan-registered-v1.json"))
        fit = json.loads(rd(f"{package}/{'smoke-' if key == 'smoke' else ''}fit-plan-registered-v1.json"))
        return {
            "run_id": gen["execution_plan"]["run_id"], "attempt_id": gen["execution_plan"]["attempt_id"],
            "fit_run_id": fit["execution_plan"]["run_id"], "fit_attempt_id": fit["execution_plan"]["attempt_id"],
            "split_identity_hash": gen["execution_plan"]["split_identity_hash"],
            "composed_config_hash": gen["composed_config_hash"], "protocol_hash": gen["execution_plan"]["protocol_hash"],
            "rows": 4 if key == "smoke" else 1080,
        }

    rows: list[tuple[str, str]] = []
    for key in ("arm", "smoke"):
        identity = plan_ids(key)
        budget = smoke_caps if key == "smoke" else caps
        decl = measurement[identity["run_id"]]
        for kind in ("generation", "fit"):
            is_fit = kind == "fit"
            run_id = identity["fit_run_id"] if is_fit else identity["run_id"]
            attempt = identity["fit_attempt_id"] if is_fit else identity["attempt_id"]
            prefix = "smoke-" if key == "smoke" else ""
            artifact = f"{package}/{prefix}{kind}-plan-registered-v1.json"
            plan_sha = sha_file(artifact)
            notes = (
                f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) {stamp[:10]} at study commit "
                f"{args.study_commit} by the COMP-1b registration agent (worktree {args.worktree}, branch "
                f"{args.branch}). This registration performs no contact and authorises none. Plan SHA256 {plan_sha}; "
                f"attempt {attempt}. Protocol hash {identity['protocol_hash']}; composed config "
                f"{identity['composed_config_hash']}; expected session serving-slurp-native-candidate-five-train-a-np4-v1 "
                f"(attach only, never spawn or stop). READINESS HELD: root mints {decision_relpath} (decision id "
                f"{decision_id}) from the package's root-admission-draft-v1.json with the four eligible run ids, then "
                f"re-pins with scripts/flights/repin_cell.py --set-ready, which mints this cell's OWN first-phase "
                f"supply under its own run id (item E16), expected to reproduce cell COMP-1's own arm supply digest "
                f"ce68bebcf2bbf5502b081221a92c3fde1095da3979106bcdddb6eeeca9e9c41a exactly (the citation contract "
                f"never touches the first-phase supply); --allow-output-change must never be passed. THE ONE CHANGE: "
                f"cell COMP-1's own committed, already-flown fragments with the citation contract's four leaf paths "
                f"reverted to the locked plan's non-cited program (policy, phase_material.solver.instruction_template, "
                f"phase_material.solver.response_format_id, native_episode.deliver_normaliser.normaliser) -- one "
                f"arming, nothing else; proven by scripts/analysis/slurp_comp1b_diff_proof.py and re-proven by "
                f"{config_test}. Comparator: the EXISTING SEALED in-chain A/A {COMPARATOR_RUN} cell COMP-1 already "
                f"flew (owner decision 160's shared-A/A pattern, as cell G5 reused it) -- reused cross-flight, never "
                f"re-flown; no new A/A cell is registered. Measurement declaration "
                f"(scripts/checks/stage3_effect_floor_check.py): measurement_design {decl['measurement_design']}, "
                f"expected_effect_pp {decl['expected_effect_pp']}, claims_benefit {'true' if decl['claims_benefit'] else 'false'}, "
                f"primary_metric_key {decl.get('primary_metric_key')}, rows {identity['rows']}, "
                f"replicate_run_id {decl.get('replicate_run_id', 'n/a (form proof)')}, tuning_roster "
                f"{decl.get('tuning_roster')!r}, read_roster {decl.get('read_roster')!r} -- canonical in "
                f"{package}/registered-facts-v1.json. Authority: the 2026-09-29 SLU-harm attribution note "
                f"(branch {attribution_branch}, {attribution_note}) and the COMP-1 read it explains ({comp1_read}); "
                f"owner decisions 25, 133, 138, 139, 152, 160, 190. Ceiling {budget['generation_calls_cap']} = "
                f"{identity['rows']} rows x 11 contacts; budgets are run-cumulative. Stop and preserve on the first "
                f"failure; AT MOST ONE root-diagnosed recovery re-registration. No paper-scale profile, no "
                f"confirmatory split, no test-split contact, no comparator re-flight and no admission entry from "
                f"this row."
            )
            scope = prose[key] + (" -- FIT spend identity, request envelopes only, no generation" if is_fit else "")
            cells = [
                "", stamp, run_id, "bounded-discovery-probe", scope, MODEL_TOOL, f"slurp TRAIN Fold A {identity['rows']}", "discovery",
                identity["split_identity_hash"], "no", str(budget["fit_endpoint_calls_cap"] if is_fit else budget["generation_calls_cap"]),
                str(budget["repeated_speech_audio_seconds_cap"]), str(budget["gpu_hours_fit_inclusive"]), INHERITED, artifact, notes, "",
            ]
            rows.append((run_id, " | ".join(cells).strip()))

    # ---- the READ row --------------------------------------------------------
    arm_ids = plan_ids("arm")
    read_run = "SAEA-SLURP-STAGE3-COMP1B-FOLD-A-PAIRED-ANALYSIS-V1"
    recipe = json.loads(rd(f"{package}/analysis-recipe-v1.json"))
    read_notes = (
        f"REGISTERED WITH THE FLIGHT (DRAFT, root countersignature pending; to be countersigned after the seal and "
        f"before any score is opened, owner decision 189 option A) {stamp[:10]} at study commit {args.study_commit}. "
        f"Recipe {recipe['recipe_id']}; output {recipe['output']['analysis_root']}. Reads the COMP-1b arm's sealed "
        f"manifest against the SAME sealed in-chain A/A {COMPARATOR_RUN} cell COMP-1 used (reused cross-flight, no "
        f"re-flight); re-verifies the shared-A/A byte identity cell COMP-1's own shared-aa-proof-v1.json established "
        f"before reading any delta. THE ATTRIBUTION PREDICTION CHECK (this cell exists to test it, "
        f"{attribution_note}): the zero-gold false-positive delta against the A/A should sit inside the same-bytes "
        f"null band (about [-27, +29]); official SLU-F1 should be no worse than -h_SLU (-1.2485); the intent gain on "
        f"identical Perception shortlists should reproduce the 3-to-gold / 1-from-gold pattern COMP-1's own read "
        f"measured. Zero model, server, encoder, embedder, tokenizer, network and GPU contact; ids, counts, rates "
        f"and hashes only. It authorises nothing by itself."
    )
    read_cells = [
        "", stamp[:10], read_run, "model-free-check",
        "The paired read of cell COMP-1b against the SAME sealed in-chain A/A cell COMP-1 used: intent primary "
        "(scenario_action exact, paired, 10,000 bootstrap draws) with official pooled SLU-F1 the non-inferiority "
        "guard, plus the attribution-prediction check (zero-gold FP inside the same-bytes null, SLU guard holds, "
        "same-shortlist intent-choice pattern reproduced), read through the standard paired driver",
        "no model or tool contact; read of sealed bytes and one official complete scoring", f"slurp TRAIN Fold A {arm_ids['rows']}, paired against the sealed in-chain A/A",
        "discovery", arm_ids["split_identity_hash"], "no", "0", "0", "0",
        "No new speech exposure: reads sealed outputs and one official scoring of the arm; the comparator's own scores are already sealed. Prior exposure inherited in full.",
        f"{package}/analysis-recipe-v1.json", read_notes, "",
    ]
    rows.append((read_run, " | ".join(read_cells).strip()))

    for run_id, line in rows:
        if len(line.split("|")) != 17:
            raise SystemExit(f"ledger row {run_id} does not have exactly fifteen cells; a literal '|' slipped into a cell")

    header = (
        "\n## Cell COMP-1b: COMP-1 minus the citation contract -- the arm, its four-row smoke, their FIT identities "
        "and the READ row (DRAFT, root countersignature pending)\n\n"
        "Five unconsumed rows: the COMP-1b arm and its four-row smoke, their two FIT spend identities, and one READ "
        "row for the paired analysis against the SAME sealed in-chain A/A cell COMP-1 already flew (owner decision "
        "160's shared-A/A pattern; no new A/A cell is registered here). Authority: the 2026-09-29 SLU-harm "
        f"attribution note (branch {attribution_branch}, {attribution_note}) and the COMP-1 read it explains "
        f"({comp1_read}). None of these rows is countersigned and none authorises a contact.\n\n"
        "| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | split role | split identity hash | consumed | "
        "calls | speech audio seconds | gpu hours | inherited exposure | artifacts | notes |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
    )

    text = rd(LEDGER)
    fresh = dict(rows)
    lines = text.split("\n")
    replaced = 0
    for index, line in enumerate(lines):
        if line.startswith("|") and len(line.split("|")) > 3 and line.split("|")[2].strip() in fresh:
            lines[index] = fresh.pop(line.split("|")[2].strip())
            replaced += 1
    if replaced and fresh:
        raise SystemExit("the ledger carries some but not all COMP-1b rows; refusing to guess")
    if replaced:
        io.open(REPO_ROOT / LEDGER, "w", encoding="utf-8", newline="").write("\n".join(lines))
        state = f"replaced-{replaced}"
    else:
        suffix = "" if text.endswith("\n") else "\n"
        io.open(REPO_ROOT / LEDGER, "w", encoding="utf-8", newline="").write(text + suffix + header + "\n".join(line for _run, line in rows) + "\n")
        state = "appended"

    print(json.dumps({"ledger_state": state, "rows": [r for r, _ in rows]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
