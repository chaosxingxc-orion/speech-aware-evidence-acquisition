#!/usr/bin/env python3
"""Derive the TEST-SAMPLE milestone cells of COMP-1b (owner decisions 151 and 202) from the
committed DEV-2000-ADDED cells (decision 58: script-derived registrations).

WHY. Owner decision 202 (2026-09-29): GO for the test-sample milestone read once cell A2
(``slurp-native-stage3-comp1b-dev2000-added-v1``, COMP-1b on DEV-2000-ADDED) reads NOMINATED or
better. The signed allowance ``docs/receipts/owner/2026-09-27-slurp-test-sample-allowance-v1.json``
(decision 151) names the two read run ids this needs:

* ``SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-00-PLAN-V1`` -- THE COMPARATOR: "the locked PLAN system
  (the v2.0 lock of 2026-09-22, as flown, unchanged) on all 3,010 sample rows, one attempt, ever";
* ``SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-01-V1`` -- MILESTONE 01: one dev-admitted composed arm
  on all 3,010 sample rows, one attempt, ever, read against MILESTONE-00-PLAN.

WHAT THIS WRITES. Two cells, re-targeted from DEV-2000-ADDED to SLURP-TEST-SAMPLE-3010-V1:

* ``slurp-native-stage3-plan-testsample-milestone00-v1`` from the SEALED DEV plan arm
  ``slurp-native-default-plan-dev2000-added-v1`` (the v2.0 lock as flown on DEV-2000-ADDED);
* ``slurp-native-stage3-comp1b-testsample-v1`` from the A2 arm
  ``slurp-native-stage3-comp1b-dev2000-added-v1`` (COMP-1b's bytes);

and one campaign plan that flies the comparator and then the arm in ONE chain (instrument rule 3:
the comparator is the in-chain replicate). The re-target is a fixed list of roster-bound
substitutions (dataset view, roster receipt, packet promotion receipt, this roster's speech-query
vectors and alias, this roster's agreement table) plus the role-bound changes the ``final-report``
split role forces (split role, the owner-allowance pin, the TEST scorer sibling
``slurp-slu-official-test``, the one-attempt failure policy) and the row-scaled budgets.
``write_slurp_comp1b_testsample_registration.py`` PROVES from the composed configs that nothing
else moved and that the arm-vs-comparator delta on the sample equals A2's arm-vs-DEV-plan delta
(the composition square).

WHAT THE ALLOWANCE FORBIDS, AND THIS SCRIPT THEREFORE DOES NOT WRITE. A four-row smoke on the
sample: the allowance names no smoke run id, and a smoke under a read run id would consume that
read's one attempt. The FIT identities are written (the native contact-fit gate requires a
distinct run id per cell, ``core.preparation_fit.build_native_contact_fit_gate``), but the v1
allowance does not name them, so ``contracts.plan.require_owner_split_allowance`` refuses them
until a SUCCESSOR allowance names them -- the registration package says so in its own words.

PENDING PINS AND SAMPLE-PREPARATION PINS. Every data-root artifact of the sample (its query
vectors, its alias receipt, preparation 2's encode receipt and this roster's agreement table) is
written as 64 zeros and listed as a readiness requirement with a PENDING reason until it exists;
the cells stay ``held`` and the flip refuses while any zero pin remains. With ``--data-root``,
each artifact the sample preparations (2 and 3, owner decision 156) have produced is pinned to
its real sha256 instead: the pin is READ from the preparations' own summary receipt
(:data:`PREPARATION_SUMMARY`, which names each output's sha256) and VERIFIED by hashing the file
on the data root; a mismatch, a summary that is not this roster's, or a summary that reads labels
refuses. The agreement table, built later from these vectors, is not named by that summary: with
``--data-root`` it is pinned from ITS OWN receipt (:data:`AGREEMENT_RECEIPT`, written by
``scripts/build_slurp_intent_exemplar_agreement.py``), which must name this roster's split identity,
the MILESTONE-00-PLAN cell and run id, 3,010 rows and zero contacts of every kind, and whose declared
table sha256 must equal the table's bytes; both the table and the receipt are pinned. Until the
receipt exists both stay PENDING.

Config only: no contact, no ledger row, no receipt, no flip, no media, no gold. The data-root
read hashes bytes; it opens no vector, no utterance and no label as content.

    python scripts/flights/comp1/derive_slurp_comp1b_testsample_cells.py --date 2026-09-29 \
        [--data-root "$SPEECHRL_DATA_DIR"]
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[3]

ZERO = "0" * 64
PENDING = "PENDING"

# ---- sources ---------------------------------------------------------------------------------
ARM_SRC_CELL = "slurp-native-stage3-comp1b-dev2000-added-v1"
ARM_SRC_BASELINE = "slurp-native-stage3-comp1b-dev2000-added-baseline-v1"
PLAN_SRC_CELL = "slurp-native-default-plan-dev2000-added-v1"
PLAN_SRC_BASELINE = "slurp-native-default-plan-dev2000-added-baseline-v1"

# ---- targets ---------------------------------------------------------------------------------
ARM_CELL = "slurp-native-stage3-comp1b-testsample-v1"
ARM_BASELINE = "slurp-native-stage3-comp1b-testsample-baseline-v1"
PLAN_CELL = "slurp-native-stage3-plan-testsample-milestone00-v1"
PLAN_BASELINE = "slurp-native-stage3-plan-testsample-milestone00-baseline-v1"
CAMPAIGN_PLAN = "configs/campaign/slurp-native-stage3-comp1b-testsample-v1.json"

ARM_RUN = "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-01-V1"
ARM_FIT_RUN = "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-01-FIT-V1"
ARM_ATTEMPT = "attempt-slurp-test-sample-3010-milestone-01-generation-v1"
ARM_FIT_ATTEMPT = "attempt-slurp-test-sample-3010-milestone-01-fit-v1"
PLAN_RUN = "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-00-PLAN-V1"
PLAN_FIT_RUN = "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-00-PLAN-FIT-V1"
PLAN_ATTEMPT = "attempt-slurp-test-sample-3010-milestone-00-plan-generation-v1"
PLAN_FIT_ATTEMPT = "attempt-slurp-test-sample-3010-milestone-00-plan-fit-v1"

# ---- the signed sample ----------------------------------------------------------------------
DATASET_FRAGMENT = "slurp-speech-native-test-sample-3010"
ROSTER_ID = "SLURP-TEST-SAMPLE-3010-V1"
ROSTER_RECEIPT = "docs/receipts/rosters/slurp-test-sample-3010-v1.json"
ROSTER_RECEIPT_SHA256 = "48d9fb336ce99ad1725bf5ca0f74687d37711d685fa9fb4f594b2f1d88344e6d"
SPLIT_IDENTITY = "0164dabf7b30f8e06f830ba28af849cef7459e8c8821cfbea7a56cabb32470f9"
# Owner decision 207 (2026-09-30): the cells pin the SIGNED successor allowance v2, which adds the two FIT run ids;
# every other term is v1's. The sample preparations (2 and 3) ran under v1, so their summary receipt still pins v1's
# bytes (PREPARATION_ALLOWANCE_SHA256) and is checked against those.
ALLOWANCE = "docs/receipts/owner/2026-09-30-slurp-test-sample-allowance-v2.json"
ALLOWANCE_SHA256 = "be2bfa5a612d30cf46a2356efa5e8cf5a54707370b4f57378a278bb835fd0ed8"
PREPARATION_ALLOWANCE = "docs/receipts/owner/2026-09-27-slurp-test-sample-allowance-v1.json"
PREPARATION_ALLOWANCE_SHA256 = "c2ae2c4eb2142b5aef27d85c04c7dcd55952c105b469fd195592c71cb6bb331b"
ROWS = 3010
AUDIO_SECONDS = 8206.436875
PROMOTION_RECEIPT_SHA256 = "d0a827b62e4c8b00facd753c9fd76cc2f5bcfbb3eea5038ca5c84e75814eaa28"
SCORER = "slurp-slu-official-test"
SPLIT_ROLE = "final-report"
SPLIT_ID = "TEST-SAMPLE"

AGREEMENT_RELPATH = "prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-TEST-SAMPLE-3010-V1/agreement.jsonl"
AGREEMENT_RECEIPT = "prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-TEST-SAMPLE-3010-V1/receipt.json"
AGREEMENT_ARTIFACT_ID = "SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-TEST-SAMPLE-3010-V1"
SEGMENT_VECTORS = "vectors/slurp-test-sample-3010-v1/query-vectors-speech-segments.jsonl"
CONTENT_VECTORS = "vectors/slurp-test-sample-3010-v1/query-vectors-speech-content-v1.jsonl"

#: Longest-first raw-text substitutions: the roster-bound identifiers of DEV-2000-ADDED.
ROSTER_SUBSTITUTIONS = [
    ("SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-DEV2000-ADDED-V1", "SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-TEST-SAMPLE-3010-V1"),
    ("SAEA-SLURP-DEV2000-ADDED-SPEECH-QUERY-ENCODING-V1", "SAEA-SLURP-TEST-SAMPLE-3010-SPEECH-QUERY-ENCODING-V1"),
    ("prepared/SAEA-SLURP-DEV2000-ADDED-ALIAS-V1/", "prepared/SAEA-SLURP-TEST-SAMPLE-3010-ALIAS-V1/"),
    ("vectors/slurp-dev2000-added-v1/", "vectors/slurp-test-sample-3010-v1/"),
    ("docs/receipts/rosters/slurp-dev-2000-added-v1.json", ROSTER_RECEIPT),
    ("DEV-2000-ADDED-promotion.json", "TEST-SAMPLE-3010-promotion.json"),
]

#: Every data-root artifact the sample has not yet produced (preparations 2 and 3, and the
#: agreement table built from their output). Each pin is written as 64 zeros.
PENDING_ARTIFACTS = {
    "prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-TEST-SAMPLE-3010-V1/agreement.jsonl":
        "this roster's own exemplar-intent agreement table (scripts/build_slurp_intent_exemplar_agreement.py "
        "against the MILESTONE-00-PLAN cell, as the DEV-2000-ADDED table was built against the sealed DEV plan "
        "cell); model-free (zero model, encoder, server or GPU contacts); NOT YET BUILT -- it runs only once the "
        "MILESTONE-00-PLAN cell pins the sample's real query vectors, which its loaders verify before a number is taken",
    "prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-TEST-SAMPLE-3010-V1/receipt.json":
        "the agreement table's receipt (same builder)",
    SEGMENT_VECTORS:
        "the sample's intent-boundary segment vectors, written by the zero-contact alias of preparation 2 "
        "(SAEA-SLURP-TEST-SAMPLE-3010-SPEECH-QUERY-ENCODING-V1, not yet run)",
    CONTENT_VECTORS:
        "the sample's content-dimension query vectors, written by preparation 3 "
        "(SAEA-SLURP-TEST-SAMPLE-3010-QUERY-VECTOR-EXPORT-V1, not yet run)",
    "preparation-runs/SAEA-SLURP-TEST-SAMPLE-3010-SPEECH-QUERY-ENCODING-V1/encode-v1/receipt.json":
        "preparation 2's encode receipt (not yet run)",
    "prepared/SAEA-SLURP-TEST-SAMPLE-3010-ALIAS-V1/query-dimension-alias.json":
        "preparation 2's alias receipt (not yet run)",
}

#: The sample preparations' own summary receipt (preparations 2 and 3, owner decision 156): it names
#: every output's sha256. Maps its ``outputs`` keys to the re-targeted relpaths the cells pin.
PREPARATION_SUMMARY = "prepared/slurp-test-sample-3010-preparations-v1/summary-queries.json"
PREPARATION_RUN_IDS = ["SAEA-SLURP-TEST-SAMPLE-3010-SPEECH-QUERY-ENCODING-V1", "SAEA-SLURP-TEST-SAMPLE-3010-QUERY-VECTOR-EXPORT-V1"]
SUMMARY_OUTPUTS = {
    "segments": SEGMENT_VECTORS,
    "content": CONTENT_VECTORS,
    "alias_receipt": "prepared/SAEA-SLURP-TEST-SAMPLE-3010-ALIAS-V1/query-dimension-alias.json",
    "encode_receipt": "preparation-runs/SAEA-SLURP-TEST-SAMPLE-3010-SPEECH-QUERY-ENCODING-V1/encode-v1/receipt.json",
}
#: Short names for the PINNED reasons.
PINNED_WHAT = {
    SEGMENT_VECTORS: "the sample's intent-boundary segment vectors (preparation 2's zero-contact alias)",
    CONTENT_VECTORS: "the sample's content-dimension query vectors (preparation 3)",
    SUMMARY_OUTPUTS["alias_receipt"]: "preparation 2's alias receipt",
    SUMMARY_OUTPUTS["encode_receipt"]: "preparation 2's encode receipt",
}

#: Solver-phase / boundary-phase text fields whose DEV-2000-ADDED wording is re-targeted.
TEXT_RETARGET = ("DEV-2000-ADDED", "TEST-SAMPLE-3010")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_preparation_pins(data_root: Path | None) -> tuple[dict[str, str], dict | None]:
    """Real pins for the sample-preparation artifacts, read from the summary receipt and verified.

    Returns ({relpath: sha256}, summary provenance or None). Without a data root, or before the
    summary exists, every pin stays PENDING. Refuses (SystemExit) on any mismatch rather than
    writing a wrong pin.
    """

    if data_root is None:
        return {}, None
    summary_path = data_root / PREPARATION_SUMMARY
    if not summary_path.is_file():
        return {}, None
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("split_identity_hash") != SPLIT_IDENTITY or summary.get("rows") != ROWS:
        raise SystemExit(f"{PREPARATION_SUMMARY}: not this roster's summary (split identity / rows)")
    if summary.get("reads_labels") is not False:
        raise SystemExit(f"{PREPARATION_SUMMARY}: reads_labels is not false; refusing")
    if (summary.get("allowance") or {}).get("sha256") != PREPARATION_ALLOWANCE_SHA256:
        raise SystemExit(f"{PREPARATION_SUMMARY}: does not pin the v1 allowance bytes the preparations ran under")
    if summary.get("run_ids") != PREPARATION_RUN_IDS:
        raise SystemExit(f"{PREPARATION_SUMMARY}: run ids {summary.get('run_ids')} are not preparations 2 and 3")
    pins: dict[str, str] = {}
    outputs = summary.get("outputs") or {}
    for key, relpath in SUMMARY_OUTPUTS.items():
        entry = outputs.get(key)
        if not entry:
            continue
        if not str(entry.get("path", "")).replace("\\", "/").endswith("/" + relpath):
            raise SystemExit(f"{PREPARATION_SUMMARY}: output {key} is {entry.get('path')!r}, not {relpath}")
        declared = entry.get("sha256")
        actual = _sha256_file(data_root / relpath)
        if declared != actual:
            raise SystemExit(f"{relpath}: the summary receipt declares {declared}, the file hashes {actual}; refusing")
        pins[relpath] = actual
    provenance = {"relpath": PREPARATION_SUMMARY, "sha256": _sha256_file(summary_path)}
    return pins, provenance


def rd(path: str) -> str:
    return io.open(path, encoding="utf-8", newline="").read()


def wr(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def dump_like(raw: str, obj: object) -> str:
    match = re.search(r"\n( +)\"", raw)
    indent = len(match.group(1)) if match else 2
    return json.dumps(obj, indent=indent, ensure_ascii=False, sort_keys=True) + ("\n" if raw.endswith("\n") else "")


def substitute(text: str, pairs) -> str:
    for old, new in pairs:
        text = text.replace(old, new)
    return text


def scaled_budget(source: dict) -> dict:
    """Row-scale the source family budget from its own rows to 3,010, keeping the per-row law."""

    rows = source["_rows"]
    per_row_generation = source["generation_calls_cap"] // rows
    per_row_fit = source["fit_endpoint_calls_cap"] // rows
    per_row_contract = source["native_task_contract_calls_cap"] // rows
    if per_row_generation * rows != source["generation_calls_cap"] or per_row_fit * rows != source["fit_endpoint_calls_cap"]:
        raise SystemExit("the source budget is not an exact per-row law; refusing to scale it")
    return {
        "asr_calls": 0,
        "ceilings_are_not_targets": True,
        "encoder_calls": 0,
        "fit_endpoint_calls_cap": per_row_fit * ROWS,
        "generation_calls_cap": per_row_generation * ROWS,
        "gpu_hours_fit_inclusive": round(math.ceil(source["gpu_hours_fit_inclusive"] * ROWS / rows * 10) / 10, 1),
        "native_task_contract_calls_cap": per_row_contract * ROWS,
        "official_complete_scoring_jobs": 1,
        "repeated_speech_audio_seconds_cap": math.ceil(per_row_generation * AUDIO_SECONDS),
    }


def pend(requirements_reason: str, relpath: str) -> dict:
    return {"kind": "preparation", "relpath": relpath, "sha256": ZERO,
            "reason": f"{PENDING}: {requirements_reason}. The pin is 64 zeros until the artifact exists; the "
                      "milestone flip refuses while any zero pin remains (scripts/flights/comp1/comp1b_testsample_flip.sh)."}


def pin_requirement(relpath: str, pins: dict[str, str], provenance: dict | None) -> dict:
    """A readiness requirement: the real, verified pin when the preparations produced it, else PENDING."""

    if relpath == AGREEMENT_RELPATH and relpath in pins:
        return {"kind": "preparation", "relpath": relpath, "sha256": pins[relpath],
                "reason": (f"PINNED: this roster's own exemplar-intent agreement table ({AGREEMENT_ARTIFACT_ID}), built "
                           "model-free (zero model, encoder, server, GPU and network contacts) by "
                           "scripts/build_slurp_intent_exemplar_agreement.py against the MILESTONE-00-PLAN cell, as the "
                           "DEV-2000-ADDED table was built against the sealed DEV plan cell, and read from its receipt "
                           f"{AGREEMENT_PROVENANCE['relpath']} (sha256 {AGREEMENT_PROVENANCE['sha256']}); the derive "
                           "script verified the sha256 against the file bytes on the data root.")}
    if relpath in pins:
        return {"kind": "preparation", "relpath": relpath, "sha256": pins[relpath],
                "reason": (f"PINNED: {PINNED_WHAT[relpath]}, produced by the label-free sample preparations (owner "
                           f"decision 156) and read from their summary receipt {provenance['relpath']} (sha256 "
                           f"{provenance['sha256']}); the derive script verified the sha256 against the file bytes on "
                           "the data root.")}
    return pend(PENDING_ARTIFACTS[relpath], relpath)


def resolve_agreement_pins(data_root: Path | None) -> tuple[dict[str, str], dict | None]:
    """Real pins for this roster's agreement table and its receipt, read from the receipt and verified.

    Returns ({relpath: sha256}, receipt provenance or None). Without a data root, or before the
    receipt exists, both pins stay PENDING. Refuses (SystemExit) on any mismatch.
    """

    if data_root is None:
        return {}, None
    receipt_path = data_root / AGREEMENT_RECEIPT
    if not receipt_path.is_file():
        return {}, None
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    artifact = receipt.get("artifact") or {}
    derived = receipt.get("derived_from") or {}
    contacts = receipt.get("contacts") or {}
    if receipt.get("schema") != "saea-phase-agreement-receipt-v1" or receipt.get("artifact_id") != AGREEMENT_ARTIFACT_ID:
        raise SystemExit(f"{AGREEMENT_RECEIPT}: not this roster's agreement receipt (schema / artifact id)")
    if artifact.get("relpath") != AGREEMENT_RELPATH or artifact.get("rows") != ROWS:
        raise SystemExit(f"{AGREEMENT_RECEIPT}: the artifact is not the {ROWS}-row table at {AGREEMENT_RELPATH}")
    if (derived.get("split_identity_hash") != SPLIT_IDENTITY or derived.get("cell") != PLAN_CELL
            or derived.get("run_id") != PLAN_RUN):
        raise SystemExit(f"{AGREEMENT_RECEIPT}: not built against MILESTONE-00-PLAN on this roster's split identity")
    if receipt.get("contact_class") != "model-free" or not contacts or any(v != 0 for v in contacts.values()):
        raise SystemExit(f"{AGREEMENT_RECEIPT}: not a zero-contact model-free build; refusing")
    actual = _sha256_file(data_root / AGREEMENT_RELPATH)
    if artifact.get("sha256") != actual:
        raise SystemExit(f"{AGREEMENT_RELPATH}: the receipt declares {artifact.get('sha256')}, the file hashes {actual}; refusing")
    receipt_sha = _sha256_file(receipt_path)
    return {AGREEMENT_RELPATH: actual, AGREEMENT_RECEIPT: receipt_sha}, {"relpath": AGREEMENT_RECEIPT, "sha256": receipt_sha}


#: Real pins resolved in main() (empty = every sample-preparation pin PENDING).
PINS: dict[str, str] = {}
#: The agreement table's receipt provenance, when its pins are real (main()).
AGREEMENT_PROVENANCE: dict[str, str] = {}


def retarget_baseline(src: str, out: str, *, pairs, fit_run: str, fit_attempt: str, what_this_is: str) -> dict:
    raw = rd(f"configs/baseline/{src}.json")
    document = json.loads(substitute(raw, ROSTER_SUBSTITUTIONS + pairs))
    document.pop("prepared_phase_supply", None)  # E16: the flip mints this cell's own supply
    document["what_this_is"] = what_this_is
    document["scorers"] = [SCORER, "cost"]
    document["speech_packet_promotion_receipt_sha256"] = PROMOTION_RECEIPT_SHA256
    if not str(document.get("speech_packet_promotion_receipt", "")).endswith("TEST-SAMPLE-3010-promotion.json"):
        raise SystemExit(f"{src}: the packet promotion receipt did not re-target")

    fit = document["native_contact_fit"]
    per_row = fit["contact_cap"] // 1000
    if per_row * 1000 != fit["contact_cap"]:
        raise SystemExit(f"{src}: the FIT cap is not an exact per-row law at 1,000 rows")
    document["native_contact_fit"] = {**fit, "run_id": fit_run, "attempt_id": fit_attempt, "contact_cap": per_row * ROWS}

    def walk(node, path=""):
        if isinstance(node, dict):
            relpath = node.get("relpath")
            if isinstance(relpath, str) and "sha256" in node:
                if relpath in PENDING_ARTIFACTS:
                    node["sha256"] = PINS.get(relpath, ZERO)
                elif relpath == ROSTER_RECEIPT:
                    node["sha256"] = ROSTER_RECEIPT_SHA256
            for key, value in node.items():
                if isinstance(value, str) and key in ("embedded_signal",):
                    node[key] = value.replace(*TEXT_RETARGET)
                else:
                    walk(value, f"{path}.{key}")
        elif isinstance(node, list):
            for value in node:
                walk(value, path)

    walk(document)
    if isinstance(document.get("what_the_train_exemplars_store_is"), str):
        document["what_the_train_exemplars_store_is"] = document["what_the_train_exemplars_store_is"].replace(*TEXT_RETARGET)
    # what_this_is is this script's own prose (it names its source cell); every other value must be free of
    # DEV-2000-ADDED identifiers.
    probe = {k: v for k, v in document.items() if k != "what_this_is"}
    leftover = [m for m in re.findall(r"[^\"]{0,40}(?:DEV2000|dev2000|DEV-2000|dev-2000)[^\"]{0,40}", json.dumps(probe))]
    if leftover:
        raise SystemExit(f"{src}: DEV-2000-ADDED identifiers survived the re-target: {leftover[:5]}")
    wr(f"configs/baseline/{out}.json", dump_like(raw, document))
    return document


def retarget_experiment(src: str, out_cell: str, *, baseline: str, run: str, attempt: str, date: str,
                        purpose: str, readiness_reason: str, requirements: list[dict], algorithm: dict,
                        decision_population: str, failure_policy: str) -> dict:
    raw = rd(f"configs/experiment/{src}.json")
    document = json.loads(raw)
    src_rows = document["population"]["count"]
    budget = scaled_budget({**document["family_budget"], "_rows": src_rows})
    cell = document["cells"][0]
    cell.update({
        "allowed_execution_stages": ["check", "prepare-supply", "worker", "campaign"],
        "attempt_id": attempt,
        "baseline_fragment": baseline,
        "cell_id": out_cell,
        "dataset_fragment": DATASET_FRAGMENT,
        "run_id": run,
        "readiness": {"reason": readiness_reason, "requirements": requirements, "state": "held"},
    })
    document["cells"] = [cell]
    document["date"] = date
    document["experiment_id"] = run
    document["execution_plan"] = {
        "execution_profile": "bounded-discovery-probe",
        "planned_gpu_hours": budget["gpu_hours_fit_inclusive"],
        "planned_model_calls": budget["generation_calls_cap"],
        "planned_speech_audio_seconds": budget["repeated_speech_audio_seconds_cap"],
        "split_role": SPLIT_ROLE,
    }
    document["owner_allowance"] = {"path": ALLOWANCE, "sha256": ALLOWANCE_SHA256}
    document["family_budget"] = budget
    generation = document["generation_budget"]
    per_row_target = generation["target"] / src_rows
    document["generation_budget"] = {
        "cap": budget["generation_calls_cap"],
        "definition": (
            "The role graph is the source cell's, unchanged (perception 1, solver 1, reviewer 3, planner 1, "
            "max_revisions 1), so rails.native_episode_config.load_native_episode_config resolves the program "
            f"ceiling 1 + 2 * (3 + 1 + 1) = 11 contacts per row and {ROWS} * 11 = {budget['generation_calls_cap']} "
            f"is the exact program maximum. The target is the source cell's own registered per-row rate "
            f"({per_row_target:.3f}) times {ROWS}, an ESTIMATE only; the sample has never been flown."
        ),
        "target": round(per_row_target * ROWS),
    }
    document["population"] = {
        "count": ROWS,
        "dataset_fragment": DATASET_FRAGMENT,
        "decision_population": decision_population,
        "roster_receipt": ROSTER_RECEIPT,
        "split_identity_hash": SPLIT_IDENTITY,
    }
    document["purpose"] = purpose
    document["failure_policy"] = failure_policy
    document["split_id"] = SPLIT_ID
    document["stage3_algorithm"] = algorithm
    wr(f"configs/experiment/{out_cell}.json", dump_like(raw, document))
    return document


FAILURE_POLICY = (
    "ONE ATTEMPT, EVER (owner decision 151; allowance milestone_rule; contracts.gate_exposure."
    "_ExposureAndCarrierMixin._require_final_report_attempt_budget). Stop and preserve on the first failure. "
    "There is NO recovery re-registration, NO resume-recovery (the E10 clause of the source cell does not apply "
    "to a final-report read run id: the gate refuses a second attempt of a read run id even as a recovery), no "
    "re-score, no re-projection of delivered bytes, no best-of, no row filtering and no roster, role-graph, "
    "prompt, knowledge, geometry or cap change. A failed attempt consumes the milestone number; a further "
    "milestone needs a fresh run id in a SUCCESSOR allowance under a fresh coordinator report to the owner. A "
    "partial manifest is never scored and never read."
)

COMPOSITION = (
    "COMP-1b on the signed test sample: the locked v2.0 plan (the sealed DEV-2000-ADDED plan arm's bytes, as "
    "flown) + (1) the agreement term (w_agree 1.0 over the exemplar-intent vote, recall k 60, delivered 8-1-8) "
    "with THIS roster's own vote table SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-TEST-SAMPLE-3010-V1 + (2) the "
    "centroid boundary key (prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/facets.jsonl) + (3) NO citation "
    "contract + (4) nothing else -- cell A2's arm bytes with only the roster moved."
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--date", required=True)
    parser.add_argument("--data-root", type=Path, default=None,
                        help="pin every sample-preparation artifact the summary receipt names (verified by hashing)")
    args = parser.parse_args(argv)
    os.chdir(REPO_ROOT)
    written: list[str] = []
    pins, provenance = resolve_preparation_pins(args.data_root)
    agreement_pins, agreement_provenance = resolve_agreement_pins(args.data_root)
    pins = {**pins, **agreement_pins}
    PINS.clear()
    PINS.update(pins)
    AGREEMENT_PROVENANCE.clear()
    AGREEMENT_PROVENANCE.update(agreement_provenance or {})

    decision_population = (
        f"The signed SLURP test SAMPLE {ROSTER_ID} (3,010 recordings, 682 prompts, a prompt-partition of the frozen "
        "13,078-recording test split; roster receipt docs/receipts/rosters/slurp-test-sample-3010-v1.json), "
        "authorised for milestone reads by owner decision 151 (allowance docs/receipts/owner/2026-09-27-slurp-test-"
        "sample-allowance-v1.json). Its audio was previously contact-only for the label-free packet ENCODE+PROMOTE "
        "preparation SAEA-SN-TEST-SAMPLE-3010-PREPROCESS (3,010 one-token contacts, owner decision 156). No answer "
        "surface of any sample row has been read. The closure roster SLURP-TEST-CLOSURE-10068-V1 stays untouched."
    )
    common_requirements = [
        pin_requirement(SEGMENT_VECTORS, pins, provenance),
        pin_requirement(CONTENT_VECTORS, pins, provenance),
    ]

    # ---- MILESTONE-00-PLAN: the locked v2.0 plan on the sample ---------------------------------
    plan_pairs = [("SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-FIT-V1", PLAN_FIT_RUN),
                  ("attempt-slurp-native-default-plan-dev2000-added-fit-v1", PLAN_FIT_ATTEMPT)]
    retarget_baseline(
        PLAN_SRC_BASELINE, PLAN_BASELINE, pairs=plan_pairs, fit_run=PLAN_FIT_RUN, fit_attempt=PLAN_FIT_ATTEMPT,
        what_this_is=(
            "MILESTONE-00-PLAN, THE COMPARATOR of the test-sample milestone reads (owner decisions 151 and 202): the "
            "locked v2.0 default plan exactly as the sealed DEV-2000-ADDED plan arm flew it (cell B6 plan arm, "
            "slurp-native-default-plan-dev2000-added-v1), re-targeted to the signed test sample SLURP-TEST-SAMPLE-"
            "3010-V1 by roster-bound pins alone (dataset view, roster receipt, packet promotion receipt, this "
            "roster's speech-query vectors and alias) plus the final-report role's own changes (the TEST scorer "
            "sibling slurp-slu-official-test and the owner-allowance pin). Nothing is retuned, re-prompted or "
            "re-geometried (one-read protocol section 4.1). It is the in-chain replicate every milestone arm is read "
            "against; it carries no operator of its own."
        ),
    )
    written.append(f"configs/baseline/{PLAN_BASELINE}.json")
    retarget_experiment(
        PLAN_SRC_CELL, PLAN_CELL, baseline=PLAN_BASELINE, run=PLAN_RUN, attempt=PLAN_ATTEMPT, date=args.date,
        purpose=(
            "MILESTONE-00-PLAN (allowance docs/receipts/owner/2026-09-27-slurp-test-sample-allowance-v1.json, owner "
            "decision 151): the locked PLAN system, the v2.0 lock as flown, unchanged, on all 3,010 sample rows, ONE "
            "attempt, ever. Every milestone arm is read against this sealed read of the locked system's own answers, "
            "per stratum, in natural-mixture (post-stratified to full-test shares) and equal-stratum weightings. "
            "Development evidence under owner decision 28 (dev numbers are not test claims); a milestone read is not "
            "the final read. Nothing here authorises a flight, a readiness flip or an admission entry."
        ),
        readiness_reason=(
            f"MILESTONE-00-PLAN registered before contact on {args.date} from the sealed DEV-2000-ADDED plan arm "
            "(decision 58: script-derived, roster re-target only). HELD until (1) owner decision 202's condition holds "
            "(cell A2 read NOMINATED or better) and the coordinator has reported it to the owner in conversation "
            "(decision 151's first-contact gate), (2) a SUCCESSOR allowance names this cell's FIT run id, (3) "
            "preparations 2 and 3 of the sample have run and every PENDING pin below is real, (4) root countersigns "
            "the rows, mints the admission receipt and re-pins with scripts/flights/repin_cell.py --set-ready, which "
            "also mints this cell's own first-phase supply (item E16). --allow-output-change must never be passed."
        ),
        requirements=common_requirements + [{
            "kind": "preparation",
            "reason": "This cell's OWN prepared first-phase Perception supply, minted model-free under this run id "
                      "with core.flight.cli prepare-supply at the flip from the sample's segment vectors and the "
                      "locked plan's key file (E16). PENDING until the flip.",
            "relpath": f"prepared/{PLAN_RUN}/phase-supply-v1.json",
            "sha256": ZERO,
        }],
        algorithm={"id": "none", "operators_used": [], "note": (
            "This cell carries NO training-free RL operator and says so explicitly: it is the locked plan's own form "
            "on the test sample, the comparator and in-chain replicate of the milestone arms.")},
        decision_population=decision_population,
        failure_policy=FAILURE_POLICY,
    )
    written.append(f"configs/experiment/{PLAN_CELL}.json")

    # ---- MILESTONE-01: COMP-1b on the sample ------------------------------------------------------
    arm_pairs = [("SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-FIT-V1", ARM_FIT_RUN),
                 ("attempt-slurp-native-stage3-comp1b-dev2000-added-fit-v1", ARM_FIT_ATTEMPT)]
    retarget_baseline(
        ARM_SRC_BASELINE, ARM_BASELINE, pairs=arm_pairs, fit_run=ARM_FIT_RUN, fit_attempt=ARM_FIT_ATTEMPT,
        what_this_is=(
            "MILESTONE-01 of the test sample (owner decisions 151 and 202): " + COMPOSITION + " Re-targeted from "
            "cell A2's committed arm (slurp-native-stage3-comp1b-dev2000-added-v1) by roster-bound pins alone plus "
            "the final-report role's own changes (the TEST scorer sibling slurp-slu-official-test and the "
            "owner-allowance pin)."
        ),
    )
    written.append(f"configs/baseline/{ARM_BASELINE}.json")
    retarget_experiment(
        ARM_SRC_CELL, ARM_CELL, baseline=ARM_BASELINE, run=ARM_RUN, attempt=ARM_ATTEMPT, date=args.date,
        purpose=(
            "MILESTONE-01 (allowance docs/receipts/owner/2026-09-27-slurp-test-sample-allowance-v1.json, owner "
            "decisions 151 and 202): does COMP-1b, admitted-or-nominated on DEV-2000-ADDED by cell A2, hold its "
            "intent gain on the signed test sample against MILESTONE-00-PLAN (the locked v2.0 plan on the same 3,010 "
            "rows, flown in the same chain before this arm), with official pooled SLU-F1 (slurp-slu-official-test) "
            "the non-inferiority guard? " + COMPOSITION + " ONE attempt, ever; the milestone number is consumed "
            "whether the arm gains, loses or is neutral. Development evidence under owner decision 28; never a test "
            "claim and never the final read. Nothing here authorises a flight, a readiness flip or an admission entry."
        ),
        readiness_reason=(
            f"MILESTONE-01 registered before contact on {args.date} from cell A2's committed arm (decision 58: "
            "script-derived, roster re-target only). HELD until (1) cell A2 reads NOMINATED or better and the "
            "coordinator has reported the dev-admitted composed arm to the owner in conversation (decisions 151 and "
            "202), (2) root re-declares expected_effect_pp from the A2 read, (3) a SUCCESSOR allowance names this "
            "cell's FIT run id, (4) preparations 2 and 3 of the sample have run, this roster's agreement table is "
            "built and every PENDING pin below is real, (5) root countersigns the rows, mints the admission receipt "
            "and re-pins with scripts/flights/repin_cell.py --set-ready (item E16). --allow-output-change must never "
            "be passed."
        ),
        requirements=[pin_requirement(AGREEMENT_RELPATH, pins, provenance)] + common_requirements + [{
            "kind": "preparation",
            "reason": "This cell's OWN prepared first-phase Perception supply, minted model-free under this run id "
                      "with core.flight.cli prepare-supply at the flip from the sample's segment vectors, the "
                      "centroid key file and this roster's agreement table (E16). PENDING until the flip.",
            "relpath": f"prepared/{ARM_RUN}/phase-supply-v1.json",
            "sha256": ZERO,
        }],
        algorithm={"id": "sealed-credit-system-policy-v1", "operators_used": ["context_application"], "note": (
            "MILESTONE-01 composes the SAME two typed, executable consumption actions COMP-1b composed on Fold A and "
            "A2 on DEV-2000-ADDED -- a rank weight over a pre-computed vote and a retrieval key file -- each chosen "
            "and credited OFFLINE over sealed TRAIN bytes; nothing is chosen, tuned or credited on the sample. "
            "Operator context_application. No rollout, per-sample scoring, credit assignment or update of its own.")},
        decision_population=decision_population,
        failure_policy=FAILURE_POLICY,
    )
    written.append(f"configs/experiment/{ARM_CELL}.json")

    plan = {"cells": [{"cell": PLAN_CELL, "experiment": PLAN_CELL}, {"cell": ARM_CELL, "experiment": ARM_CELL}],
            "schema": "saea-campaign-plan-v1"}
    wr(CAMPAIGN_PLAN, json.dumps(plan, indent=2, sort_keys=True) + "\n")
    written.append(CAMPAIGN_PLAN)
    print(json.dumps({"written": written, "pinned": pins, "summary_receipt": provenance,
                      "agreement_receipt": agreement_provenance,
                      "still_pending": sorted(set(PENDING_ARTIFACTS) - set(pins))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
