import json
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[2]
EXPERIMENTS = (
    REPO / "configs/experiment/slurp-ku-s3a-g1-v1.json",
    REPO / "configs/experiment/slurp-ku-s3a-twin-g1-v1.json",
)
MODEL = "q4km-mmproj-free-speech-native-np4-base-speech-query-prefix-max64"
DATASET = "slurp-speech-native-dev1000"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", EXPERIMENTS)
def test_ku_s3_g1_has_held_fit_and_generation_cells(path):
    doc = load(path)
    assert len(doc["cells"]) == 2
    fit, generation = doc["cells"]
    assert fit["readiness"]["state"] == generation["readiness"]["state"] == "held"
    assert fit["run_id"].startswith("PENDING-")
    assert fit["attempt_id"].startswith("PENDING-")
    assert generation["run_id"].startswith("SAEA-SLURP-KU-S3-FILLERS-")
    assert generation["attempt_id"].startswith("PENDING-")
    assert fit["allowed_execution_stages"] == ["check", "wire-check", "prompt-fit"]
    assert generation["allowed_execution_stages"] == ["check", "wire-check", "prepare-supply", "worker", "campaign"]
    assert generation["readiness"]["depends_on"][0]["run_id"] == fit["run_id"]
    assert all(cell["model_fragment"] == MODEL for cell in (fit, generation))
    assert all(cell["dataset_fragment"] == DATASET for cell in (fit, generation))
    assert "unexposed NEW500" not in path.read_text(encoding="utf-8")


@pytest.mark.parametrize("path", EXPERIMENTS)
def test_ku_s3_g1_fit_budget_and_pending_supply_are_fail_closed(path):
    doc = load(path)
    basis = doc["execution_plan_basis"]["fit"]
    assert "3,001" in basis
    assert doc["prepared_phase_supply"]["sha256"].startswith("PENDING-")
    generation = doc["cells"][1]
    assert all(item["sha256"].startswith("PENDING-") for item in generation["readiness"]["requirements"])
    assert doc["prepared_supply_inputs"]["k"] == 5
    assert doc["prepared_supply_inputs"]["tau"] == 0.0


def test_ku_s3_g1_source_pins_match_existing_baseline_authorities():
    speech = load(REPO / "configs/baseline/slurp-phase-slots-supplied-fillers-speech-v1.json")
    twin = load(REPO / "configs/baseline/slurp-phase-slots-supplied-fillers-twin-v1.json")
    speech_doc = load(EXPERIMENTS[0])
    twin_doc = load(EXPERIMENTS[1])
    assert speech_doc["source_pins"]["runtime_predecessor"]["manifest_sha256"] == speech["phase_material"]["slots"]["predecessor_source"]["manifest_sha256"]
    assert twin_doc["source_pins"]["runtime_predecessor"]["manifest_sha256"] == twin["phase_material"]["slots"]["predecessor_source"]["manifest_sha256"]
    assert speech_doc["source_pins"]["vector_inputs"]["query_sha256"] == speech["phase_supply"]["slots"]["query_source"]["sha256"]
    assert twin_doc["source_pins"]["vector_inputs"]["query_sha256"] == twin["phase_supply"]["slots"]["query_source"]["sha256"]
    assert speech_doc["source_pins"]["kc_s1b_comparator"]["manifest_sha256"] == "088c9307a39f38db124a5204793806e9a8589d942259b15e7826ad2685fe8d08"
