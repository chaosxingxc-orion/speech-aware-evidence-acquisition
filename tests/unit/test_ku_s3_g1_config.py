import json
import hashlib
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.config import compose
from speech_aware_evidence_acquisition.core.flight.campaign import declared_readiness, load_campaign_cells


REPO = Path(__file__).resolve().parents[2]
EXPERIMENTS = (
    REPO / "configs/experiment/slurp-ku-s3a-g1-v1.json",
    REPO / "configs/experiment/slurp-ku-s3a-twin-g1-v1.json",
)
MODEL = "q4km-mmproj-free-speech-native-np4-base-speech-query-prefix-max64"
DATASET = "slurp-speech-native-dev1000"


#: a7e688c3 ("bind verified KU-S3 prepared supply and owner successor",
#: docs/readiness/2026-09-09-ku-s3-g1-successor.md) bound each experiment's prepared supply to the verified G1
#: preparation run; before it the fragments carried none.
G1_PREPARATION_PREFIX = "prepared/SAEA-SLURP-KU-S3-G1-PREPARE-V1/"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_no_supply_or_the_verified_g1_preparation(values):
    supply = values.get("prepared_phase_supply")
    if supply is None:
        return
    assert supply["relpath"].startswith(G1_PREPARATION_PREFIX), supply
    assert len(supply["sha256"]) == 64 and not supply["sha256"].startswith("PENDING"), supply


@pytest.mark.parametrize("path", EXPERIMENTS)
def test_ku_s3_g1_has_held_fit_and_generation_cells(path):
    doc = load(path)
    assert len(doc["cells"]) == 2
    fit, generation = doc["cells"]
    assert fit["readiness"]["state"] == generation["readiness"]["state"] == "held"
    assert fit["run_id"].startswith("SAEA-SLURP-KU-S3A")
    assert fit["attempt_id"].startswith("attempt-")
    assert generation["run_id"].startswith("SAEA-SLURP-KU-S3-FILLERS-")
    assert generation["attempt_id"].startswith("attempt-")
    assert fit["allowed_execution_stages"] == ["check", "wire-check", "prompt-fit"]
    assert generation["allowed_execution_stages"] == ["check", "wire-check", "prepare-supply", "worker", "campaign"]
    assert generation["readiness"].get("depends_on") is None
    assert generation["readiness"]["requirements"] == []
    assert all(cell["model_fragment"] == MODEL for cell in (fit, generation))
    assert all(cell["dataset_fragment"] == DATASET for cell in (fit, generation))
    assert "unexposed NEW500" not in path.read_text(encoding="utf-8")


@pytest.mark.parametrize("path", EXPERIMENTS)
def test_ku_s3_g1_fit_budget_and_pending_supply_are_fail_closed(path):
    doc = load(path)
    basis = doc["execution_plan_basis"]["fit"]
    assert "3,001" in basis
    _assert_no_supply_or_the_verified_g1_preparation(doc)
    assert doc["pending_preparation"]["phase_supply"]["artifact_sha256"].startswith("PENDING-")
    generation = doc["cells"][1]
    assert generation["readiness"]["requirements"] == []
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


@pytest.mark.parametrize("path", EXPERIMENTS)
def test_ku_s3_g1_campaign_cells_are_held_without_flight_dependencies(path, tmp_path):
    cells = load_campaign_cells(REPO, path.stem)
    assert len(cells) == 2
    assert cells[0].document["cell_id"].endswith("-fit")
    assert cells[1].document["cell_id"].endswith("-generation")
    assert all(cell.dependencies() == () for cell in cells)
    assert all(declared_readiness(cell, tmp_path).state == "held" for cell in cells)


@pytest.mark.parametrize("path, baseline", tuple(zip(EXPERIMENTS, ("slurp-ku-s3a-g1-v1", "slurp-ku-s3a-twin-g1-v1"))))
def test_ku_s3_g1_composition_strips_only_unbound_runtime_pins(path, baseline):
    composed = compose(
        REPO,
        model="q4km-mmproj-free-speech-native-np4-base-speech-query-prefix-max64",
        dataset="slurp-speech-native-dev1000",
        baseline=("slurp-phase-slots-supplied-fillers-speech-v1" if "twin" not in baseline else "slurp-phase-slots-supplied-fillers-twin-v1"),
        experiment=path.stem,
    )
    assert composed.values["experiment_id"] == load(path)["experiment_id"]
    _assert_no_supply_or_the_verified_g1_preparation(composed.values)
    assert "pending_preparation" in composed.values


def test_ku_s3_g1_small_source_receipts_match_pinned_hashes():
    for relpath, expected in (
        ("docs/receipts/knowledge/slurp-kb-size-full-content-slot-fillers.json", "2abda571900bfcb5bf4a384eac1cb858fa8841ab3873d034b862c85671af443c"),
        ("docs/checks/speech-aware-evidence-acquisition/2026-09-07-slurp-kus3-vectors/vectors.json", "3c213ad4f4787e32d92fe30dd1119395817a73ba48d46cbed292a8f471aa86e5"),
    ):
        digest = hashlib.sha256((REPO / relpath).read_bytes()).hexdigest()
        assert digest == expected
