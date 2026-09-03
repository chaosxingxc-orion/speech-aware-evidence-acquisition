"""Contract checks for the amended G8 action-support preregistration."""

from __future__ import annotations

import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
EXPERIMENT = (
    REPO / "configs/experiment/a2t-g8-action-support-reachability-fixed16-v1.json"
)
BASELINE = REPO / "configs/baseline/a2t-g8-action-support-reachability-agentloop.json"


def test_decomposed_response_envelopes_and_terminal_failure_are_frozen() -> None:
    experiment = json.loads(EXPERIMENT.read_text(encoding="utf-8"))
    contract = experiment["protocol"]["decomposed_response_contract"]

    assert contract == {
        "maximum_selection_calls": 32,
        "selection_response_utf8_bytes_maximum": 4096,
        "binding_response_utf8_bytes_maximum": 12288,
        "duplicates": "Preserve every repeated exact registered name in order.",
        "binding_alignment": (
            "Require exactly one typed binding object per sealed selection occurrence, "
            "with identical name, count, and order."
        ),
        "invalid_stage_behavior": (
            "Abort and terminalize the one-shot attempt before the next contact; do not "
            "retry, repair, substitute an empty answer, emit branch manifests, or score."
        ),
    }


def test_decomposed_completion_reserves_cover_the_frozen_response_envelopes() -> None:
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    experiment = json.loads(EXPERIMENT.read_text(encoding="utf-8"))

    assert baseline["decomposed_selection_completion_token_cap"] >= baseline[
        "decomposed_selection_response_utf8_bytes_maximum"
    ]
    assert baseline["decomposed_binding_completion_token_cap"] >= baseline[
        "decomposed_binding_response_utf8_bytes_maximum"
    ]
    assert experiment["prompt_fit"]["decomposed_selection_completion_tokens"] == 4096
    assert experiment["prompt_fit"]["decomposed_binding_completion_tokens"] == 12288
    assert baseline["special_token_reserve"] == 512
    assert experiment["prompt_fit"]["special_token_reserve"] == 512


def test_score_detail_is_captured_by_each_single_official_invocation() -> None:
    experiment = json.loads(EXPERIMENT.read_text(encoding="utf-8"))
    scoring = experiment["sealing_and_scoring"]

    assert scoring["score_invocation_limit"] == (
        "Exactly one official scoring invocation per complete branch manifest."
    )
    assert scoring["per_sample_capture"] == (
        "Persist aggregate and per-sample scorer output from that same invocation; never "
        "rerun a branch scorer to recover row detail."
    )
    assert scoring["outer_parallelism"] == (
        "Independent complete branch manifests may be scored in parallel by an outer "
        "coordinator after the common gold-open condition is satisfied."
    )
