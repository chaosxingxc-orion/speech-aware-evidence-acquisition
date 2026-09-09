import json
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
    assert fit["readiness"]["state"] == generation["readiness"]["state"] == "held"
    assert fit["allowed_execution_stages"] == ["check", "wire-check", "prompt-fit"]
    assert generation["allowed_execution_stages"] == ["check", "wire-check", "prepare-supply", "worker", "campaign"]
    assert fit["run_id"].endswith("-FIT-V1")
    assert generation["run_id"] == document["experiment_id"]
    assert fit["attempt_id"].startswith("PENDING-REGISTERED-")
    assert generation["attempt_id"].startswith("PENDING-REGISTERED-")
    assert fit["model_fragment"] == generation["model_fragment"] == MODEL
    assert fit["dataset_fragment"] == generation["dataset_fragment"] == DATASET
    assert declared_readiness(load_campaign_cells(REPO, path.stem)[0], tmp_path).state == "held"
    assert declared_readiness(load_campaign_cells(REPO, path.stem)[1], tmp_path).state == "held"


@pytest.mark.parametrize("path", CONFIGS)
def test_max256_successor_has_pending_fit_supply_and_no_active_pins(path):
    document = read(path)
    assert document["execution_plan"]["planned_model_calls"] == 1050
    assert document["execution_plan"]["planned_gpu_hours"] == 2.0
    assert document["execution_plan"]["planned_speech_audio_seconds"] == 3000
    assert document["pending_preparation"]["fit"]["endpoint_count"] == 3001
    assert document["pending_preparation"]["fit"]["artifact_sha256"].startswith("PENDING-")
    assert document["pending_preparation"]["phase_supply"]["artifact_sha256"].startswith("PENDING-")
    assert "prepared_phase_supply" not in document
    assert "prepared_request_fit" not in document
    assert all("depends_on" not in cell["readiness"] for cell in document["cells"])
    assert "unexposed NEW500" not in path.read_text(encoding="utf-8")


@pytest.mark.parametrize("path", CONFIGS)
def test_max256_composition_preserves_override_and_held_pending_state(path, tmp_path):
    document = read(path)
    control = "control" in path.stem
    baseline = "slurp-phase-slots-given-intent-schema-v1" if control else ("slurp-phase-slots-supplied-fillers-twin-v1" if "twin" in path.stem else "slurp-phase-slots-supplied-fillers-speech-v1")
    composed = compose(REPO, model=MODEL, dataset=DATASET, baseline=baseline, experiment=path.stem)
    assert composed.values["experiment_id"] == document["experiment_id"]
    assert composed.values["request_decoding_overrides"] == {"max_tokens": 256}
    assert composed.values["pending_preparation"]["fit"]["endpoint_count"] == 3001
    assert "prepared_phase_supply" not in composed.values
    assert "prepared_request_fit" not in composed.values
    assert declared_readiness(load_campaign_cells(REPO, path.stem)[0], tmp_path).state == "held"


def test_max256_control_is_explicit_no_retrieval_and_keeps_owner_schema():
    document = read(CONFIGS[2])
    assert all(cell["arm"] == "no-retrieval-control" for cell in document["cells"])
    assert document["retrieval_mode"] == "none"
    assert all(cell["baseline_fragment"] == "slurp-phase-slots-given-intent-schema-v1" for cell in document["cells"])
    assert document["owner_schema_decision"]["decision_id"] == "OWNER-KUS3-SCHEMA-003"
    assert document["source_pins"]["runtime_predecessor"]["manifest_sha256"] == "f908ff4c7b0267322b34c7bf2ca9ad29d6db97ee8bb3cf18bf8824a057ebc94c"
    assert document["source_pins"]["kc_s1b_comparator"]["manifest_sha256"] == "088c9307a39f38db124a5204793806e9a8589d942259b15e7826ad2685fe8d08"


def test_budget_decision_is_english_and_narrow():
    text = (REPO / "docs/superpowers/plans/experiment-handoff/OWNER-KUS3-BUDGET-005.md").read_text(encoding="utf-8")
    assert "OWNER-KUS3-BUDGET-004" in text
    assert "max_tokens=256" in text
    assert "four-row" in text
    assert "no extra full sweep" in text
