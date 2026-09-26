import json
import re
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.config import compose
from speech_aware_evidence_acquisition.core.flight.campaign import declared_readiness, load_campaign_cells

REPO = Path(__file__).resolve().parents[2]
CONFIGS = (
    REPO / "configs/experiment/slurp-ku-s3a-g1-max256-v1.json",
    REPO / "configs/experiment/slurp-ku-s3a-twin-g1-max256-v1.json",
    REPO / "configs/experiment/slurp-ku-s3a-control-g1-max256-v1.json",
)
MODEL = "q4km-mmproj-free-speech-native-np4-base-speech-query-prefix-max64"
DATASET = "slurp-speech-native-dev1000"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", CONFIGS)
def test_max256_successor_is_held_and_split_into_fit_generation(path, tmp_path):
    document = read(path)
    fit, generation = document["cells"]
    assert document["migration_status"].startswith("HELD:")
    assert document["request_decoding_overrides"] == {"max_tokens": 256}
    assert document["preserve_wire_responses"] is True
    assert fit["readiness"]["state"] in {"held", "ready"}
    assert generation["readiness"]["state"] in {"held", "ready"}
    assert fit["allowed_execution_stages"] == ["check", "wire-check", "prompt-fit"]
    assert generation["allowed_execution_stages"] == ["check", "wire-check", "prepare-supply", "worker", "campaign"]
    assert fit["run_id"].endswith("-FIT-V1")
    assert generation["run_id"] == document["experiment_id"]
    assert re.fullmatch(r"attempt-[0-9TZ-]+-[0-9a-f]+", fit["attempt_id"])
    assert re.fullmatch(r"attempt-[0-9TZ-]+-[0-9a-f]+", generation["attempt_id"])
    assert fit["attempt_id"] != generation["attempt_id"]
    assert fit["model_fragment"] == generation["model_fragment"] == MODEL
    assert fit["dataset_fragment"] == generation["dataset_fragment"] == DATASET
    for cell in load_campaign_cells(REPO, path.stem):
        readiness = declared_readiness(cell, tmp_path)
        assert readiness.state != "ready" if cell.document["readiness"]["state"] == "ready" else readiness.state == "held"
        if cell.document["readiness"]["state"] == "ready" and not cell.document["run_id"].endswith("-FIT-V1"):
            pin = document.get("prepared_request_fit")
            assert isinstance(pin, dict)
            assert any(item.get("kind") == "preparation" and item.get("relpath") == pin.get("relpath") and item.get("sha256") == pin.get("sha256") for item in cell.document["readiness"].get("requirements", []))


@pytest.mark.parametrize("path", CONFIGS)
def test_max256_successor_has_registered_budgets_and_valid_active_pins(path):
    document = read(path)
    assert document["execution_plan"]["planned_model_calls"] == 1050
    assert document["execution_plan"]["planned_gpu_hours"] == 2.0
    assert document["execution_plan"]["planned_speech_audio_seconds"] == 3000
    assert document["pending_preparation"]["fit"]["endpoint_count"] == 3001
    for name in ("prepared_request_fit", "prepared_phase_supply"):
        if name in document:
            pin = document[name]
            assert not Path(pin["relpath"]).is_absolute()
            assert ".." not in Path(pin["relpath"]).parts
            assert re.fullmatch(r"[0-9a-f]{64}", pin["sha256"])
    if "control" in path.stem:
        assert "prepared_phase_supply" not in document
    assert all("depends_on" not in cell["readiness"] for cell in document["cells"])
    assert "unexposed NEW500" not in path.read_text(encoding="utf-8")


@pytest.mark.parametrize("path", CONFIGS)
def test_max256_composition_preserves_valid_overrides_and_historical_refusal(path, tmp_path):
    document = read(path)
    control = "control" in path.stem
    baseline = "slurp-phase-slots-given-intent-schema-v1" if control else ("slurp-phase-slots-supplied-fillers-twin-v1" if "twin" in path.stem else "slurp-phase-slots-supplied-fillers-speech-v1")
    if control:
        # Preserve the immutable historical fragment's empty-list defect.
        # Current composition must refuse it; do not relax the shared validator
        # or rewrite old experiment bytes to make a historical cell launchable.
        from speech_aware_evidence_acquisition.core.config import ConfigError
        assert document["preparation_source_receipts"] == []
        with pytest.raises(ConfigError, match="preparation_source_receipts must be a non-empty list"):
            compose(REPO, model=MODEL, dataset=DATASET, baseline=baseline, experiment=path.stem)
        return
    composed = compose(REPO, model=MODEL, dataset=DATASET, baseline=baseline, experiment=path.stem)
    assert composed.values["experiment_id"] == document["experiment_id"]
    assert composed.values["request_decoding_overrides"] == {"max_tokens": 256}
    assert composed.values["pending_preparation"]["fit"]["endpoint_count"] == 3001
    for name in ("prepared_request_fit", "prepared_phase_supply"):
        if name in composed.values:
            pin = composed.values[name]
            assert not Path(pin["relpath"]).is_absolute()
            assert ".." not in Path(pin["relpath"]).parts
            assert re.fullmatch(r"[0-9a-f]{64}", pin["sha256"])
    for cell in load_campaign_cells(REPO, path.stem):
        readiness = declared_readiness(cell, tmp_path)
        if cell.document["readiness"]["state"] == "ready":
            assert readiness.state != "ready"
        else:
            assert readiness.state == "held"


def test_max256_control_is_explicit_no_retrieval_and_keeps_owner_schema():
    document = read(CONFIGS[2])
    assert all(cell["arm"] == "speech-feature-query" for cell in document["cells"])
    assert document["retrieval_mode"] == "none"
    assert all(cell["baseline_fragment"] == "slurp-phase-slots-given-intent-schema-v1" for cell in document["cells"])
    assert document["owner_schema_decision"]["decision_id"] == "OWNER-KUS3-SCHEMA-003"
    assert document["source_pins"]["runtime_predecessor"]["manifest_sha256"] == "f908ff4c7b0267322b34c7bf2ca9ad29d6db97ee8bb3cf18bf8824a057ebc94c"
    assert document["source_pins"]["kc_s1b_comparator"]["manifest_sha256"] == "088c9307a39f38db124a5204793806e9a8589d942259b15e7826ad2685fe8d08"


def test_budget_decision_is_english_and_narrow():
    text = (REPO / "docs/superpowers/plans/experiment-handoff/OWNER-KUS3-BUDGET-005.md").read_text(encoding="utf-8")
    assert "OWNER-BUDGET-PROBE-004" in text
    assert "256 tokens" in text
    assert "four-row" in text
    assert "no extra full sweep" in text
