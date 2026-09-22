"""Item E35 (owner decision 89, 2026-09-21): compose + load every new
registration-package config for the Earnings21+ConEC four-row smoke and the
sub10 paired direct-vs-system engineering read. Model-free: reads committed
JSON through the repository's own ``core.config.compose``, and loads the
system arms through ``rails.native_episode_config.load_native_episode_config``
-- exactly the pattern ``tests/unit/test_default_plan_lock_cells.py`` /
``tests/unit/test_b8a_deliver_normalise_smoke_config.py`` use. No model,
tokenizer, encoder, scorer, server or network contact, and nothing under
SPEECHRL_DATA_DIR is read (the composed configs reference a derived
execution-unit artifact this item deliberately did NOT materialize -- see
``scripts/build_e21_native_window_unit_subset.py`` -- so no test here touches
it).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.config import compose
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.delivery_normalisers import (
    DELIVER_NORMALISE_EARNINGS_TEXT_V1,
)
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    load_native_episode_config,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
MODEL = "q4km-e21-native-window-packets-cddb000c-np4-max1024-v1"

FOUR_ROW_DATASET = "e21-native-window-four-row-v1"
FOUR_ROW_EXPERIMENT = "e21-native-window-four-row-direct-vs-system-v1"
FOUR_ROW_DIRECT_BASELINE = "e21-native-window-direct-four-row-v1"
FOUR_ROW_SYSTEM_BASELINE = "e21-native-window-system-four-row-v1"

SUB10_DATASET = "e21-native-window-sub10-v1"
SUB10_EXPERIMENT = "e21-native-window-sub10-direct-vs-system-v1"
SUB10_DIRECT_BASELINE = "e21-native-window-direct-sub10-v1"
SUB10_SYSTEM_BASELINE = "e21-native-window-system-sub10-v1"


def _compose(dataset: str, baseline: str, experiment: str):
    return compose(str(REPO_ROOT), MODEL, dataset, baseline, experiment)


@pytest.mark.parametrize(
    "dataset, baseline, experiment",
    (
        (FOUR_ROW_DATASET, FOUR_ROW_DIRECT_BASELINE, FOUR_ROW_EXPERIMENT),
        (SUB10_DATASET, SUB10_DIRECT_BASELINE, SUB10_EXPERIMENT),
    ),
)
def test_the_direct_arm_composes_and_declares_one_phase_per_unit(dataset, baseline, experiment):
    values = _compose(dataset, baseline, experiment).values
    assert values["policy"] == "phase-direct-only-v1"
    assert values["carrier_lock_key"] == "earnings21-original"
    # phase-direct-only-v1 is an EXISTING, already-tested single-phase program
    # (tests exercising it elsewhere prove it dispatches exactly one contact
    # per execution unit); this fragment declares exactly the one phase it
    # supplies material for.
    assert set(values["phase_material"]) == {"direct"}


@pytest.mark.parametrize(
    "dataset, baseline, experiment, expected_unit_count",
    (
        (FOUR_ROW_DATASET, FOUR_ROW_SYSTEM_BASELINE, FOUR_ROW_EXPERIMENT, 4),
        (SUB10_DATASET, SUB10_SYSTEM_BASELINE, SUB10_EXPERIMENT, 342),
    ),
)
def test_the_system_arm_composes_and_loads_the_six_node_episode(
    dataset, baseline, experiment, expected_unit_count
):
    values = _compose(dataset, baseline, experiment).values
    assert values["policy"] == "phase-native-review-revise-acquire-v1"
    assert values["carrier_lock_key"] == "earnings21-original"
    assert values["prepared_execution_units"]["unit_count"] == expected_unit_count
    assert set(values["phase_material"]) == {"perception", "reviewer", "planner", "solver"}
    assert "phase_tools" not in values
    assert "knowledge_stores" not in values

    program = default_phase_program(str(values["policy"]))
    config = load_native_episode_config(values, program)
    assert config.deliver_normaliser_id == DELIVER_NORMALISE_EARNINGS_TEXT_V1
    assert config.max_contacts == 11
    assert set(role.phase_id for role in config.roles) == {
        "perception",
        "reviewer",
        "planner",
        "solver",
    }
    assert config.acquisition_role is not None
    assert config.acquisition_role.phase_id == "acquisition"
    assert config.acquisition_role.max_iterations == 0


@pytest.mark.parametrize(
    "dataset, baseline, experiment",
    (
        (FOUR_ROW_DATASET, FOUR_ROW_DIRECT_BASELINE, FOUR_ROW_EXPERIMENT),
        (FOUR_ROW_DATASET, FOUR_ROW_SYSTEM_BASELINE, FOUR_ROW_EXPERIMENT),
        (SUB10_DATASET, SUB10_DIRECT_BASELINE, SUB10_EXPERIMENT),
        (SUB10_DATASET, SUB10_SYSTEM_BASELINE, SUB10_EXPERIMENT),
    ),
)
def test_every_new_cell_shares_the_same_carrier_and_scorers(dataset, baseline, experiment):
    values = _compose(dataset, baseline, experiment).values
    assert values["carrier_lock_key"] == "earnings21-original"
    assert values["scorers"] == [
        "asr-wer-whisper",
        "conec-entity-wer-official",
        "numeric-value-accuracy-v1",
        "semantic-high-impact-error-rate-v1",
        "cost",
    ]
