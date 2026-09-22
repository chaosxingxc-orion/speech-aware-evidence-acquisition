from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.contracts import ExecutionPlan
from speech_aware_evidence_acquisition.core.config import compose
from speech_aware_evidence_acquisition.core.flight.campaign import (
    declared_readiness,
    load_campaign_cells,
)
from speech_aware_evidence_acquisition.core.flight.runtime import compute_protocol_hash


ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = "e21-native-window-direct-full44-fit-v1"
HELD_EXPERIMENT = "e21-native-window-direct-full44-registration-v1"
BASELINE = "e21-native-window-direct-full44-registration-v1"
MODEL = "q4km-e21-native-window-packets-cddb000c-np4-max1024-v1"
DATASET = "earnings21-native-window-full44-v1"
SPLIT = "fcc1b0bc55432d02347dcdf730c6bcef561a9b0ad9605c45b367e1ed3da5d69e"
FIT_RUN = "SAEA-E21-NATIVE-WINDOW-DIRECT-FULL44-FIT-V1"
FIT_ATTEMPT = "attempt-e21-native-window-direct-full44-fit-v1"
GENERATION_RUN = "SAEA-E21-NATIVE-WINDOW-DIRECT-FULL44-V1"
SYSTEM_RUNS = {
    "SAEA-E21-NATIVE-WINDOW-CONTEXT-TOOLS-FULL44-V1",
    "SAEA-E21-NATIVE-WINDOW-CONTEXT-TOOLS-FULL44-V1-FIT",
    "SAEA-E21-NATIVE-WINDOW-CONTEXT-TOOLS-FULL44-ASR-V1",
}
READINESS = ROOT / "docs/readiness/2026-09-15-e21-native-window-direct-fit-registration-v1"
ADMISSION_RELPATH = "coordination/e21-native-window-registration-v1/admission-v1.json"
ADMISSION_SHA256 = "de78bb55f4fcb46e0b04432da997dc2ff3c8e5a002d358646f7cdcd0542272e8"
LEDGER_PREFIX_BYTES = 3715862
# Re-pinned 2026-09-22: the ledger hygiene pass of 2026-09-2x (6d4cca75 / f0ae76f2, closing or superseding
# back-catalogue rows inside the prefix) and the B8b smoke re-pin (6f921100) legitimately rewrote bytes
# inside the prefix; the boundary is unchanged and the E21 rows after it are unchanged.
LEDGER_PREFIX_SHA256 = "788104a32e0c483948a58c0995e91fbac2e4a1e64162ed374ce7c5c4c50fb781"
# Re-pinned 2026-09-16: commit 2736fab6 ("docs: correct Audio2Tool scope-tools
# ledger carrier") legitimately lower-cased four "Audio2Tool" occurrences that
# happen to fall inside this byte window after this test was authored at
# 1daad518; LEDGER_PREFIX_BYTES still marks the same boundary, only the prefix's
# hash changes to match the corrected, current ledger content.


def _composed(experiment: str):
    return compose(ROOT, MODEL, DATASET, BASELINE, experiment)


def test_fit_is_ready_from_the_exact_root_decision_and_generation_stays_held() -> None:
    fit, generation = load_campaign_cells(ROOT, EXPERIMENT)
    assert (fit.run_id, fit.attempt_id) == (FIT_RUN, FIT_ATTEMPT)
    assert fit.document["allowed_execution_stages"] == ["check", "prompt-fit"]
    assert fit.document["readiness"] == {
        "state": "ready",
        "reason": (
            "Root admits only the direct static execution-unit fit. Final source "
            "freeze, the exact resident service and exclusive lease remain mandatory."
        ),
        "requirements": [
            {
                "kind": "decision",
                "expected_decision_id": "e21-native-window-full44-stable-source-admission-v1",
                "relpath": ADMISSION_RELPATH,
                "sha256": ADMISSION_SHA256,
                "reason": "Root scientific and stable-source admission for the direct static fit.",
            }
        ],
    }
    data_root = os.environ.get("SPEECHRL_DATA_DIR")
    if data_root is None:
        pytest.skip("Exact external admission validation requires SPEECHRL_DATA_DIR")
    assert declared_readiness(fit, Path(data_root)).state == "ready"

    assert generation.run_id == GENERATION_RUN
    assert generation.document["readiness"]["state"] == "held"
    assert generation.document["allowed_execution_stages"] == ["check", "campaign"]
    assert fit.document["baseline_fragment"] == generation.document["baseline_fragment"]
    assert fit.document["model_fragment"] == generation.document["model_fragment"] == MODEL
    assert fit.document["dataset_fragment"] == generation.document["dataset_fragment"] == DATASET


def test_successor_changes_no_runtime_behavior_or_budget() -> None:
    held = _composed(HELD_EXPERIMENT)
    final = _composed(EXPERIMENT)
    allowed_changes = {"cells", "experiment_id", "purpose"}
    assert {
        key: value for key, value in final.values.items() if key not in allowed_changes
    } == {
        key: value for key, value in held.values.items() if key not in allowed_changes
    }
    assert final.values["execution_plan"] == {
        "execution_profile": "bounded-discovery-probe",
        "planned_gpu_hours": 4.0,
        "planned_model_calls": 1593,
        "planned_speech_audio_seconds": 141346,
        "split_role": "discovery",
    }
    assert final.values["prompt_fit_multiple"] == 1.3333333333333333
    assert final.values["population"] == {
        "count": 44,
        "execution_units": 1593,
        "historically_exposed": True,
        "split_identity_hash": SPLIT,
    }
    assert "prepared_request_fit" not in final.values


def test_plan_is_the_exact_shared_protocol_with_the_fit_cap_override() -> None:
    composed = _composed(EXPERIMENT)
    protocol_hash = compute_protocol_hash(composed.config_hash, composed.values["arm"], SPLIT)
    expected = ExecutionPlan(
        run_id=FIT_RUN,
        attempt_id=FIT_ATTEMPT,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="earnings21-original",
        split_role="discovery",
        split_identity_hash=SPLIT,
        planned_model_calls=4780,
        planned_gpu_hours=4.0,
        planned_speech_audio_seconds=141346,
        protocol_hash=protocol_hash,
    ).validate()

    plan_document = json.loads((READINESS / "direct-fit-plan-v1.json").read_text(encoding="utf-8"))
    assert plan_document["protocol_document"]["sha256"] == hashlib.sha256(
        (READINESS / "protocol-v1.json").read_bytes()
    ).hexdigest()
    plan = ExecutionPlan(**plan_document["execution_plan"]).validate()
    assert plan == expected
    assert plan_document["contact_cap"] == 4780
    assert plan_document["actual_request_count"] == 1593
    assert plan_document["generation_contacts"] == 0
    assert plan_document["fit_mode"] == "static-execution-unit-aware"

    protocol = json.loads((READINESS / "protocol-v1.json").read_text(encoding="utf-8"))
    assert protocol["configuration"]["composed_config_hash"] == composed.config_hash
    assert protocol["configuration"]["runtime_protocol_hash"] == protocol_hash
    assert protocol["execution_plan"] == plan_document["execution_plan"]
    assert protocol["fit"]["entry"].endswith("core.flight.cli prompt-fit")
    assert protocol["root_admission"]["sha256"] == ADMISSION_SHA256
    recipe = (READINESS / "README.md").read_text(encoding="utf-8")
    assert "core.flight.cli prompt-fit" in recipe
    assert "--lease-token-file" in recipe
    assert "root-fit-lease-token-v1.json" in recipe
    assert "PYTHONDONTWRITEBYTECODE=1 " + chr(92) + chr(10) in recipe
    assert "<root-issued-fit-lease-token>" not in recipe
    assert "coordinate-fit route is not selected" in recipe
    assert protocol["held_contacts"] == {
        "direct_generation": GENERATION_RUN,
        "system_generation": "SAEA-E21-NATIVE-WINDOW-CONTEXT-TOOLS-FULL44-V1",
        "system_native_fit": "SAEA-E21-NATIVE-WINDOW-CONTEXT-TOOLS-FULL44-V1-FIT",
        "reviewer_cpu_asr": "SAEA-E21-NATIVE-WINDOW-CONTEXT-TOOLS-FULL44-ASR-V1",
    }


def test_ledger_preserves_prefix_and_registers_only_the_direct_fit() -> None:
    ledger = (ROOT / "docs/exposure-ledger.md").read_bytes()
    prefix = ledger[:LEDGER_PREFIX_BYTES]
    assert hashlib.sha256(prefix).hexdigest() == LEDGER_PREFIX_SHA256
    suffix = ledger[LEDGER_PREFIX_BYTES:].decode("utf-8")
    marker = "### 2026-09-15: Earnings21 direct static execution-unit fit"
    assert suffix.count(marker) == 1
    section = suffix.split(marker, 1)[1].split(chr(10) + "### ", 1)[0]
    assert section.count(FIT_RUN) == 1
    assert "| no | 4780 | 141346 | 4.0 |" in section
    assert GENERATION_RUN not in section
    assert not SYSTEM_RUNS.intersection(section.split())

    plan_path = READINESS / "direct-fit-plan-v1.json"
    plan_sha256 = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    assert f"Plan SHA-256 {plan_sha256}" in section
