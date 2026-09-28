#!/usr/bin/env python3
"""The knowledge wave's shared-A/A preconditions (owner decision 164), checked model-free.

Used by ``scripts/flights/wave/wave_flip.sh`` (``--mode flip``) before anything is re-pinned, and by
``scripts/flights/wave/batch_chain_wave.sh`` (``--mode chain``) against the checkout that will fly.

Both modes refuse unless:

* the A/A's byte-identity proof (``shared-aa-proof-v1.json``) reads ``IDENTICAL``;
* the wave campaign plan is exactly [the wave A/A, the W1 arm], and W3's and W4's plans carry their
  arm alone (the A/A is spent once, in step 1, beside the first arm -- the decision-160 shape);
* every wave arm's CANONICAL ``stage3_measurement`` names the wave A/A as its ``replicate_run_id``;
* W3 flies as W3a ONLY -- its arm's Solver ``train-exemplars`` supply equals the AGREE arm's, i.e. the
  per-intent exemplar cap (W3b) is absent -- unless ``--skip-w3`` drops W3 from the wave altogether.
  The first W3 registration carried BOTH W3a and W3b; it was re-derived in place as W3a alone on
  2026-09-27 (coordinator ruling under decision 164's one-change rule), so this check holds for W3.

``--mode flip`` additionally refuses unless every decision receipt the wave needs is minted under the
data root, and every flight row, every model-free row the families' own flip scripts name, and the A/A's
rows are ROOT COUNTERSIGNED (never a draft), and every READ row exists (a READ row may stay a draft until
the seal). No model, tokenizer, encoder, scorer, server or GPU contact; nothing is written.

    python scripts/flights/wave/wave_preconditions.py --repo-root R --data-root D --mode flip|chain [--skip-w3]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

AA_PACKAGE = "docs/readiness/2026-09-27-slurp-stage3-wave1-aa-fold-a-v1"
AA_RUN = "SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1"
AA_CELL = "slurp-native-stage3-wave1-aa-fold-a-v1"
WAVE_CAMPAIGN = "configs/campaign/slurp-native-stage3-wave1-fold-a-v1.json"
AGREE_BASELINE = "configs/baseline/slurp-native-stage3-agree-w1-fold-a-baseline-v1.json"

FAMILIES = {
    "aa": {
        "package": AA_PACKAGE,
        "receipt": "coordination/slurp-stage3-wave1-aa-fold-a-v1/root-admission-v1.json",
        "mint": "scripts/flights/wave/wave_mint_receipt.py",
        "rows": [AA_RUN, "SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-FIT-V1"],
        "read": "SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-PAIRED-READ-V1",
    },
    "w1": {
        "package": "docs/readiness/2026-09-27-slurp-stage3-w1-card-selection-fold-a-v1",
        "arm_run": "SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-V1",
        "receipt": "coordination/slurp-stage3-w1-cardsel-fold-a-v1/root-admission-v1.json",
        "mint": "scripts/flights/w1/w1_mint_receipt.py",
        "rows": ["SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-V1", "SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-FIT-V1",
                 "SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-SMOKE-4-V1", "SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-SMOKE-4-FIT-V1",
                 "SAEA-SLURP-INTENT-SLOT-LEGALITY-POOL-V1", "SAEA-SLURP-W1-CARD-SELECTION-MEASUREMENT-V1"],
        "read": "SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-PAIRED-ANALYSIS-V1",
    },
    "w3": {
        "package": "docs/readiness/2026-09-27-slurp-stage3-w3-contrast-fold-a-v1",
        "arm_run": "SAEA-SLURP-STAGE3-W3-FOLD-A-V1",
        "campaign": "configs/campaign/slurp-native-stage3-w3-fold-a-v1.json",
        "cell": "slurp-native-stage3-w3-fold-a-v1",
        "baseline": "configs/baseline/slurp-native-stage3-w3-fold-a-baseline-v1.json",
        "receipt": "coordination/slurp-stage3-w3-contrast-fold-a-v1/root-admission-v1.json",
        "mint": "scripts/flights/w3/w3_mint_receipt.py",
        "rows": ["SAEA-SLURP-STAGE3-W3-FOLD-A-V1", "SAEA-SLURP-STAGE3-W3-FOLD-A-FIT-V1",
                 "SAEA-SLURP-STAGE3-W3-FOLD-A-SMOKE-4-V1", "SAEA-SLURP-STAGE3-W3-FOLD-A-SMOKE-4-FIT-V1",
                 "SAEA-SLURP-W3-INTENT-CONTRAST-CARDS-BUILD-V1", "SAEA-SLURP-W3-CONTRAST-CAP-OFFLINE-V1"],
        "read": "SAEA-SLURP-STAGE3-W3-FOLD-A-PAIRED-ANALYSIS-V1",
    },
    "w4": {
        "package": "docs/readiness/2026-09-27-slurp-stage3-w4-slot-conventions-fold-a-v1",
        "arm_run": "SAEA-SLURP-STAGE3-W4-FOLD-A-V1",
        "campaign": "configs/campaign/slurp-native-stage3-w4-fold-a-v1.json",
        "cell": "slurp-native-stage3-w4-fold-a-v1",
        "receipt": "coordination/slurp-stage3-w4-fold-a-v1/root-admission-v1.json",
        "mint": "scripts/flights/w4/w4_mint_receipt.py",
        "rows": ["SAEA-SLURP-STAGE3-W4-FOLD-A-V1", "SAEA-SLURP-STAGE3-W4-FOLD-A-FIT-V1",
                 "SAEA-SLURP-STAGE3-W4-FOLD-A-SMOKE-4-V1", "SAEA-SLURP-STAGE3-W4-FOLD-A-SMOKE-4-FIT-V1",
                 "SAEA-SLURP-SLOT-CONVENTIONS-W4-PREPARE-V1", "SAEA-SLURP-W4-FOLD-A-OFFLINE-ESTIMATE-V1"],
        "read": "SAEA-SLURP-STAGE3-W4-FOLD-A-PAIRED-READ-V1",
    },
}


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _cells(repo: Path, relpath: str) -> list[str]:
    return [cell["cell"] for cell in _load(repo / relpath)["cells"]]


def _gate(repo: Path):
    path = repo / "scripts" / "checks" / "flight_registration_check.py"
    spec = importlib.util.spec_from_file_location("flight_registration_check", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules.setdefault("flight_registration_check", module)
    spec.loader.exec_module(module)
    return module


def w3_carries_the_cap(repo: Path) -> bool:
    """True when the W3 arm's Solver train-exemplars supply differs from the AGREE arm's (W3b present)."""

    w3 = _load(repo / FAMILIES["w3"]["baseline"])["knowledge_stores"]["train-exemplars"]["phase_supply"]["solver"]
    agree = _load(repo / AGREE_BASELINE)["knowledge_stores"]["train-exemplars"]["phase_supply"]["solver"]
    return json.dumps(w3, sort_keys=True) != json.dumps(agree, sort_keys=True)


def check(repo: Path, data: Path, mode: str, skip_w3: bool) -> list[str]:
    problems: list[str] = []
    families = [name for name in FAMILIES if not (skip_w3 and name == "w3")]
    proof_path = repo / AA_PACKAGE / "shared-aa-proof-v1.json"
    if not proof_path.is_file():
        problems.append("the shared A/A proof is missing (scripts/flights/wave/wave_shared_aa_proof.py)")
    elif _load(proof_path).get("verdict") != "IDENTICAL":
        problems.append(f"the shared A/A proof reads {_load(proof_path).get('verdict')!r}, not IDENTICAL")
    plan = _cells(repo, WAVE_CAMPAIGN)
    if plan != [AA_CELL, "slurp-native-stage3-w1-cardsel-fold-a-v1"]:
        problems.append(f"the wave campaign plan is {plan}, not [the wave A/A, the W1 arm]")
    for name in ("w3", "w4"):
        if name not in families:
            continue
        cells = _cells(repo, FAMILIES[name]["campaign"])
        if cells != [FAMILIES[name]["cell"]]:
            problems.append(f"the {name.upper()} campaign plan is {cells}, not the arm alone")
    for name in families:
        if name == "aa":
            continue
        family = FAMILIES[name]
        facts = _load(repo / family["package"] / "registered-facts-v1.json")
        replicate = facts["stage3_measurement"][family["arm_run"]].get("replicate_run_id")
        if replicate != AA_RUN:
            problems.append(f"the {name.upper()} arm's replicate_run_id is {replicate!r}, not {AA_RUN}")
    if "w3" in families and w3_carries_the_cap(repo):
        problems.append(
            "the registered W3 arm carries W3b (the per-intent exemplar cap: its Solver train-exemplars supply is not "
            "the AGREE arm's) -- the wave flies W3a ONLY; re-derive W3 as W3a alone, or drop W3 with --skip-w3 / "
            "WAVE_SKIP_W3=1"
        )
    if mode == "flip":
        gate = _gate(repo)
        ledger = gate.parse_ledger(repo, repo / "docs" / "exposure-ledger.md")
        for name in families:
            family = FAMILIES[name]
            if not (data / family["receipt"]).is_file():
                problems.append(f"the {name.upper()} decision receipt is not minted: {family['receipt']} ({family['mint']})")
            for run_id in family["rows"]:
                rows = ledger.get(run_id, [])
                if len(rows) != 1:
                    problems.append(f"{run_id}: {len(rows)} exposure-ledger rows, expected exactly one")
                elif not gate.is_countersigned(rows[0]):
                    problems.append(f"{run_id}: the exposure row is not root countersigned")
            if not ledger.get(family["read"]):
                problems.append(f"{family['read']}: the READ row is not in the exposure ledger")
        receipt = data / FAMILIES["aa"]["receipt"]
        if receipt.is_file():
            eligible = _load(receipt).get("eligible_run_ids", [])
            missing = [run for run in FAMILIES["aa"]["rows"] if run not in eligible]
            if missing:
                problems.append(f"the wave A/A receipt does not list {missing} as eligible")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--mode", required=True, choices=("flip", "chain"))
    parser.add_argument("--skip-w3", action="store_true")
    args = parser.parse_args(argv)
    problems = check(args.repo_root.resolve(), args.data_root, args.mode, args.skip_w3)
    for problem in problems:
        print(f"refusing ({args.mode}, owner decision 164): {problem}")
    if not problems:
        print(f"wave preconditions hold ({args.mode}) at {args.repo_root}; W3 {'skipped' if args.skip_w3 else 'included (W3a only)'}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
