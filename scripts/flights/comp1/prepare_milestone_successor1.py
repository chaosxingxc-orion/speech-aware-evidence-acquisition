#!/usr/bin/env python3
"""Derive owner-213 successor identities; reuse the existing registration writer.

Model-free preparation only. Never changes old artifacts, starts a service, clears
STOP, countersigns exposure, or dispatches a flight. Refuse existing target configs.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import write_slurp_comp1b_testsample_registration as registration

ROOT = Path(__file__).resolve().parents[3]
OLD_PACKAGE = "docs/readiness/2026-09-29-slurp-stage3-comp1b-testsample-v1"
PACKAGE = "docs/readiness/2026-10-01-slurp-milestone-successor1-v1"
ALLOWANCE = "docs/receipts/owner/2026-10-01-slurp-test-sample-successor1-allowance-v1.json"
SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"
DECISION_ID = "slurp-milestone-successor1-admission-v1"
DECISION_PATH = "coordination/slurp-milestone-successor1-v1/root-admission-v1.json"
READ_RUN = "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR1-READ-V1"
CELLS = {"plan": "slurp-milestone-successor1-plan-v1", "arm": "slurp-milestone-successor1-comp1b-v1"}
SOURCES = dict(registration.CELLS)


def read(path):
    return json.loads((ROOT / path).read_text())


def write(path, value):
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def remap(value, replacements):
    if isinstance(value, dict):
        return {remap(k, replacements): remap(v, replacements) for k, v in value.items()}
    if isinstance(value, list):
        return [remap(v, replacements) for v in value]
    if isinstance(value, str):
        for before, after in sorted(replacements.items(), key=lambda pair: -len(pair[0])):
            value = value.replace(before, after)
    return value


def derive():
    allowance = read(ALLOWANCE)
    assert allowance["status"] == "authorised" and allowance["signature"]["decision"] == 213
    replacements = {OLD_PACKAGE: PACKAGE}
    for key, source in SOURCES.items():
        old = read(f"configs/experiment/{source}.json")
        cell = old["cells"][0]
        baseline = read(f"configs/baseline/{cell['baseline_fragment']}.json")
        label = "PLAN" if key == "plan" else "COMP1B"
        run = f"SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR1-{label}-V1"
        fit = run[:-3] + "-FIT-V1"
        attempt = f"attempt-slurp-milestone-successor1-{label.lower()}-generation-v1"
        fit_attempt = attempt.replace("generation", "fit")
        replacements.update({cell["run_id"]: run, baseline["native_contact_fit"]["run_id"]: fit,
                             cell["attempt_id"]: attempt, baseline["native_contact_fit"]["attempt_id"]: fit_attempt,
                             source: CELLS[key]})
        exp_path = f"configs/experiment/{CELLS[key]}.json"
        base_name = CELLS[key].replace("-v1", "-baseline-v1")
        base_path = f"configs/baseline/{base_name}.json"
        if (ROOT / exp_path).exists() or (ROOT / base_path).exists():
            raise SystemExit("Successor configuration exists; use shared re-pin, never re-derive it.")
        new = remap(copy.deepcopy(old), replacements)
        nc = new["cells"][0]
        nc["baseline_fragment"] = base_name
        nc["readiness"] = {"state": "held", "reason": "Owner decision 213 permits this fresh pair; registration, own supply, admission and full launch gates must pass.",
                           "requirements": [r for r in nc["readiness"]["requirements"] if r["kind"] != "decision"]}
        for req in nc["readiness"]["requirements"]:
            if "phase-supply-v" in req["relpath"]:
                req["sha256"] = "0" * 64
                req["reason"] = "Fresh successor-owned preparation, selection output must equal its original source."
        new["date"] = "2026-10-01"
        new["service_session"] = SESSION
        new["owner_allowance"] = {"path": ALLOWANCE, "sha256": hashlib.sha256((ROOT / ALLOWANCE).read_bytes()).hexdigest()}
        new["purpose"] = f"Owner-213 fresh {label} milestone. Original scientific settings; failed outputs remain unread and unscored."
        new["generation_budget"]["definition"] = "Inherited unchanged ceiling: 3010 rows times 11 graph contacts. Target is an estimate, never an execution requirement."
        new["population"]["decision_population"] = allowance["prior_exposure"]
        newbase = copy.deepcopy(baseline)
        newbase["native_contact_fit"].update(run_id=fit, attempt_id=fit_attempt)
        write(exp_path, new)
        write(base_path, newbase)
    write("configs/campaign/slurp-milestone-successor1-v1.json", {"schema": "saea-campaign-plan-v1", "cells": [{"experiment": CELLS[k], "cell": CELLS[k]} for k in ("plan", "arm")]})
    # Carry forward all original analysis amendments before calling the proven writer.
    for name in ("registered-facts-v1.json", "analysis-recipe-v1.json", "population-counts-v1.json"):
        write(PACKAGE + "/" + name, remap(read(OLD_PACKAGE + "/" + name), replacements))
    write(PACKAGE + "/successor-identity-map.json", {"owner_decision": 213, "replacements": replacements, "generation_rows": 6020, "dispatch_authority": False})


def register(argv):
    if READ_RUN in (ROOT / "docs/exposure-ledger.md").read_text():
        raise SystemExit("Already registered; use the shared re-pin tool, never regenerate custody documents.")
    registration.CELLS = CELLS
    registration.ALLOWANCE = ALLOWANCE
    registration.CAMPAIGN_PLAN = "configs/campaign/slurp-milestone-successor1-v1.json"
    registration.PACKAGE_NAME = "slurp-milestone-successor1-v1"
    registration.DECISION_ID = DECISION_ID
    registration.DECISION_RELPATH = DECISION_PATH
    registration.READ_RUN = READ_RUN
    registration.ANALYSIS_ROOT = "analysis/" + READ_RUN
    registration.SESSION = SESSION
    registration.BOOKKEEPING += ("service_session", "generation_budget.definition", "population.decision_population")
    return registration.main(["--package-dir", PACKAGE, *argv])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("derive", "register"))
    args, remaining = parser.parse_known_args()
    if args.mode == "derive":
        derive()
    else:
        raise SystemExit(register(remaining))
