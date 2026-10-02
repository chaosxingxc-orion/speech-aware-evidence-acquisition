#!/usr/bin/env python3
"""Check a pinned assumed continuation; never call a provider or admit a flight."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from speech_aware_evidence_acquisition.rails.system_proposer_capacity import audit_scenario
from speech_aware_evidence_acquisition.rails.system_proposer_responses import strict_json
from speech_aware_evidence_acquisition.rails.system_text_policy import canonical, require


def pinned(path, expected):
    raw = Path(path).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == expected, "capacity input file hash differs")
    return strict_json(raw)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capsule", required=True)
    parser.add_argument("--capsule-sha256", required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--scenario-sha256", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args(argv)
    report_path = Path(args.report)
    require(not report_path.exists(), "capacity report already exists")
    report = audit_scenario(pinned(args.capsule, args.capsule_sha256),
                            pinned(args.scenario, args.scenario_sha256))
    report["input_files"] = {name: {"path": str(Path(getattr(args, name)).resolve()),
                                    "sha256": getattr(args, name + "_sha256")}
                             for name in ("capsule", "scenario")}
    with report_path.open("x", encoding="utf-8") as stream:
        stream.write(canonical(report) + "\n")
    print(canonical({"status": report["status"], "covered_requests": report["covered_requests"],
                     "first_failed_contact": report["first_failed_contact"], "actual_contacts": 0}))
    return 0 if report["status"] == "covered_requests_fit" else 2


if __name__ == "__main__":
    raise SystemExit(main())
