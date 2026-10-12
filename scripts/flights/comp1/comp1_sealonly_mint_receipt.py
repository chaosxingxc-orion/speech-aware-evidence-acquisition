#!/usr/bin/env python3
"""Mint the COMP-1 SEAL-ONLY completion decision receipt (owner decision 189 option A) on the data root.

Root's act, never an agent's, and ONLY after the owner has ruled decision 189 for option A and root has
countersigned the seal-only DRAFT clauses. Derives
``$SPEECHRL_DATA_DIR/coordination/slurp-stage3-comp1-fold-a-v1/root-admission-sealonly-v1.json`` from the
attempt-3 receipt ``root-admission-resume-v3.json`` (pinned by sha256 below, so a moved template refuses):

* decision id ``slurp-stage3-comp1-fold-a-sealonly-admission-v1``; status ``decided``; recorded now;
* eligible run ids the arm and its FIT identity only (no dry run: nothing is flown); eligible attempt the
  seal-only attempt only; the FIT attempt id the fresh seal-only one;
* ``resume_from`` the two-predecessor list the cell declares (checked against the committed experiment config);
* ``resume_replay_proof`` copied from the package's generation plan (refused unless 1,080 / 0 / 0);
* ``declared_expected_effect_pp`` 3.23 UNCHANGED (asserted against the template);
* ``antecedents.superseded_resume_receipt_v3`` naming the v3 receipt; every other repository antecedent
  ``{"path", "sha256"}`` re-hashed to the bytes current at minting.

Refuses to overwrite an existing receipt. Writes nothing with ``--dry``.

    python scripts/flights/comp1/comp1_sealonly_mint_receipt.py [--coordinator "Fable5.1"] [--dry]
"""

from __future__ import annotations
import os

import argparse
import hashlib
import io
import json
import os
from datetime import datetime, timezone

DATA = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
ROOT = os.environ.get("SAEA_STUDY_ROOT", "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")
OUT_DIR = "coordination/slurp-stage3-comp1-fold-a-v1"
TEMPLATE = OUT_DIR + "/root-admission-resume-v3.json"
TEMPLATE_SHA256 = "af9401aec9129edc304d466efc328f9953ad555fd7ee97c7d0d8f25caab7d5d3"
OUT_NAME = "root-admission-sealonly-v1.json"
DECISION_ID = "slurp-stage3-comp1-fold-a-sealonly-admission-v1"
PACKAGE = "docs/readiness/2026-09-28-slurp-stage3-comp-1-fold-a-v1-resume-v1"
EXPERIMENT = "configs/experiment/slurp-native-stage3-comp1-fold-a-v1-resume.json"
RUN = "SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1"
FIT_RUN = "SAEA-SLURP-STAGE3-COMP1-FOLD-A-FIT-V1"
ORIG = "attempt-slurp-native-stage3-comp1-fold-a-generation-v1"
R3 = "attempt-slurp-native-stage3-comp1-fold-a-generation-v1-resume-3"
SO = "attempt-slurp-native-stage3-comp1-fold-a-generation-v1-seal-only"
FSO = "attempt-slurp-native-stage3-comp1-fold-a-fit-v1-seal-only"
RESUME_FROM = [
    {"attempt_id": ORIG, "trace_sha256": "029a2dbbd62bc8752ff9e7d6a53dfee0cb49872f48b11267e49c4022c9561997"},
    {"attempt_id": R3, "trace_sha256": "87be5cefcaa395ad58a010b6d79986c5c79981c8cebe0279029bd22f7343df26"},
]
DECLARED_PP = 3.23


def _sha(path: str) -> str:
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()


def rehash(node, root: str) -> int:
    count = 0
    if isinstance(node, dict):
        path = node.get("path")
        if isinstance(path, str) and os.path.isfile(os.path.join(root, path)):
            node["sha256"] = _sha(os.path.join(root, path))
            count += 1
        for value in node.values():
            count += rehash(value, root)
    elif isinstance(node, list):
        for value in node:
            count += rehash(value, root)
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coordinator", default="Fable5.1")
    parser.add_argument("--dry", action="store_true", help="print the receipt, write nothing")
    args = parser.parse_args()
    root = ROOT.rstrip("/")

    template_path = os.path.join(DATA, TEMPLATE)
    if _sha(template_path) != TEMPLATE_SHA256:
        raise SystemExit(f"refusing to mint: {TEMPLATE} no longer hashes to {TEMPLATE_SHA256[:12]}...")
    template = json.loads(io.open(template_path, encoding="utf-8").read())
    if template.get("declared_expected_effect_pp") != DECLARED_PP:
        raise SystemExit(f"refusing to mint: the template declares {template.get('declared_expected_effect_pp')!r}, not {DECLARED_PP}")

    cell = json.loads(io.open(os.path.join(root, EXPERIMENT), encoding="utf-8").read())["cells"][0]
    if cell.get("attempt_id") != SO or cell.get("resume_from") != RESUME_FROM:
        raise SystemExit("refusing to mint: the committed resume cell does not declare the seal-only attempt and its two-predecessor resume_from")
    plan = json.loads(io.open(os.path.join(root, PACKAGE, "generation-plan-registered-v1.json"), encoding="utf-8").read())
    proof = plan.get("resume_replay_proof") or {}
    if (proof.get("rows_checked"), proof.get("rows_failing"), proof.get("sealed_twice")) != (1080, 0, 0):
        raise SystemExit(f"refusing to mint: the registered resume_replay_proof is not 1,080 / 0 / 0 ({proof.get('rows_checked')} / {proof.get('rows_failing')} / {proof.get('sealed_twice')})")

    receipt = json.loads(json.dumps(template))
    receipt["decision_id"] = DECISION_ID
    receipt["status"] = "decided"
    receipt["recorded_at_utc"] = datetime.now(timezone.utc).isoformat()
    receipt["coordinator"] = args.coordinator
    receipt["eligible_run_ids"] = [RUN, FIT_RUN]
    receipt["eligible_attempt_ids"] = [SO]
    receipt["fit_attempt_ids"] = {FIT_RUN: FSO}
    receipt["resume_from"] = RESUME_FROM
    receipt["resume_replay_proof"] = proof
    receipt["declared_expected_effect_pp"] = DECLARED_PP
    receipt["decision"] = (
        "Seal the COMP-1 arm SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1 as the SEAL-ONLY completion of its one recovery (row 175): attempt "
        + SO + " keeps the union of the original attempt's 471 sealed rows and attempt 3's 609 flown rows (1,080) with ZERO new model "
        "contacts through core.flight.cli seal-only, finalizes it with the one official score job, and reads it at the FINALIZED shared A/A "
        "SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1 by the unchanged READ row SAEA-SLURP-STAGE3-COMP1-FOLD-A-PAIRED-ANALYSIS-V1; then the G5 smoke "
        "and arm in the same chain.")
    receipt["cell_kind"] = (
        "COMP-1 SEAL-ONLY COMPLETION: a new attempt " + SO + " (FIT attempt " + FSO + ", records no contact) under the SAME run id " + RUN
        + ", resume_from [" + ORIG + " (trace 029a2dbb..., 471 complete rows), " + R3 + " (trace 87be5cef..., 609 complete rows)]; the union "
        "covers the 1,080-row roster, so nothing is flown; the shared A/A is FINALIZED, is the comparator and is never re-flown.")
    receipt["authorization_basis"] = (
        "Owner decision 189 option A (seal-only completion of resume attempt 3 under the merged replay fix d619e1c5), on the offline replay "
        "proof recorded as resume_replay_proof (1,080 rows checked, 0 failing, 0 sealed twice). Owner decisions 22, 175 and 181 (outcome and "
        "addendum) stand; the parent authorization basis stands: owner decisions 138, 152, 160, 161. " + str(template.get("authorization_basis", "")))
    receipt["retry_basis"] = (
        "Resume attempt 3 flew all 609 remaining rows (2,476 calls, 7,392.9 s audio) and ABORTED at the seal on the core.flight.resume._classify "
        "replay defect (the raw recorded response instead of the deliver normaliser's output for kept rows), fixed at d619e1c5. Its 609 rows are "
        "complete in its trace; the seal-only completion keeps them with the original attempt's 471 and flies nothing. Attempts 1, 2 and 3 stay "
        "charged run-cumulatively (4,441 calls of 11,880).")
    budget = receipt.setdefault("budget", {})
    budget.pop("dry_run", None)
    budget["resume"] = {
        "kept_rows": 1080, "flown_rows": 0, "kept_from": {ORIG: 471, R3: 609}, "seal_only": True,
        "flown_worst_case_calls": 0, "run_cumulative_actual_calls": 4441,
        "run_cumulative_actual_breakdown_calls": {ORIG: 1913, ORIG + "-resume": 4, ORIG + "-resume-2": 48, R3: 2476},
        "cap_calls": 11880,
        "note": "plan budgets are run-cumulative across the aborted attempt and resume attempts 1, 2 and 3; the seal-only completion adds none",
    }
    history = list(receipt.get("resume_attempt_history") or [])
    history.append({
        "attempt_id": R3, "flight_commit": "8fd87fca", "state": "ABORTED", "calls": 2476, "audio_seconds": 7392.8838125,
        "rows_sealed": 0, "complete_rows_in_trace": 609,
        "trace_sha256": "87be5cefcaa395ad58a010b6d79986c5c79981c8cebe0279029bd22f7343df26",
        "cause": "HARNESS: seal-time replay of the 471 kept rows used the raw recorded response instead of the deliver normaliser's output (core.flight.resume._classify); fixed at d619e1c5",
    })
    receipt["resume_attempt_history"] = history
    not_authorized = [item for item in receipt.get("not_authorized", []) if "RESUME3-SMOKE" not in item and "resume attempt 3" not in item]
    not_authorized += [
        "flying any row of SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1 again (the seal-only completion makes zero model contacts)",
        "any core.flight.cli worker or campaign run of the resume cell (it allows check, prepare-supply and seal-only only)",
        "writing, moving or compressing anything under resume attempt 3's directory",
    ]
    receipt["not_authorized"] = not_authorized
    antecedents = receipt.setdefault("antecedents", {})
    antecedents["superseded_resume_receipt_v3"] = {
        "relpath": TEMPLATE, "sha256": TEMPLATE_SHA256, "decision_id": template.get("decision_id"),
        "status": "SUPERSEDED by the seal-only completion: it named resume attempt 3, which aborted at the seal on the replay defect fixed at d619e1c5",
    }
    for key in ("dry_run_generation_plan", "dry_run_fit_plan"):
        antecedents.pop(key, None)
    antecedents["registration_commit"] = "fable/comp1seal (hashes above are re-derived at minting; the flip re-pins the plan and protocol hashes)"
    receipt["minted_from"] = {"template_receipt": TEMPLATE, "tool": "scripts/flights/comp1/comp1_sealonly_mint_receipt.py"}
    population = receipt.setdefault("population", {})
    population["partition"] = "TRAIN Fold A 1,080, unchanged; 471 kept from the original attempt, 609 kept from resume attempt 3, 0 flown"
    rehashed = rehash(receipt, root)

    out_dir = os.path.join(DATA, OUT_DIR)
    out = os.path.join(out_dir, OUT_NAME)
    text = json.dumps(receipt, indent=2, ensure_ascii=False) + "\n"
    if args.dry:
        print(text)
        print(f"(dry) would write {out}; re-hashed {rehashed} antecedent path(s)")
        return 0
    if os.path.exists(out):
        raise SystemExit(f"refusing to overwrite an existing receipt: {out}")
    os.makedirs(out_dir, exist_ok=True)
    io.open(out, "w", encoding="utf-8", newline="\n").write(text)
    print(json.dumps({"written": out, "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "decision_id": DECISION_ID,
                      "eligible_run_ids": receipt["eligible_run_ids"], "eligible_attempt_ids": receipt["eligible_attempt_ids"],
                      "declared_expected_effect_pp": DECLARED_PP, "rehashed_paths": rehashed}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
