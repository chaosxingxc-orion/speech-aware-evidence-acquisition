"""Fail-closed checks for the committed Audio2Tool schema-risk result."""

from __future__ import annotations

import json
from pathlib import Path

from speech_aware_evidence_acquisition.analysis import (
    training_free_a2t_schema_risk_memory as risk,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
CHECK_DIR = (
    REPO_ROOT
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-01-a2t-schema-risk-memory"
)


def _load(name: str) -> dict[str, object]:
    return json.loads((CHECK_DIR / name).read_text(encoding="utf-8"))


def test_committed_policy_is_self_hashed_and_rejects_scale() -> None:
    policy = _load("policy-v1.json")
    risk.assert_self_hash(policy)
    assert policy["experiment_id"] == risk.EXPERIMENT_ID
    assert policy["promotion_passed"] is False
    assert policy["selected_candidate"] is None
    assert policy["next_scale"] == (
        "close schema-risk targeting for the current supply action"
    )
    assert policy["offline_guard"] == {
        "outbound_connection_attempts": 0,
        "targets": [],
    }


def test_committed_candidates_preserve_the_safe_all_stop_outcome() -> None:
    policy = _load("policy-v1.json")
    reports = policy["candidate_reports"]
    assert set(reports) == set(risk.CANDIDATE_IDS)
    for report in reports.values():
        metrics = report["metrics"]
        assert report["promotion_passed"] is False
        assert metrics["n_samples"] == 104
        assert metrics["stopped"] == 104
        assert metrics["supplied"] == 0
        assert metrics["saved"] == 0
        assert metrics["harmed"] == 0
        assert metrics["net_gain"] == 0
        assert metrics["fold_net_gains"] == [0, 0, 0, 0, 0]


def test_result_summary_binds_live_state_and_negative_information_gain() -> None:
    summary = _load("result-summary.json")
    assert summary["promotion_passed"] is False
    assert summary["selected_candidate"] is None
    assert summary["decision"] == (
        "close schema-risk targeting for the current supply action"
    )
    assert summary["contacts"] == {
        "frozen_core": 0,
        "embedding_tool": 0,
        "tokenizer": 0,
        "http_or_socket": 0,
        "audio_seconds": 0,
        "gpu_hours": 0.0,
    }
    parser = summary["registry_parser_audit"]
    assert parser["rows"] == parser["parsed_signatures"] == 152
    assert parser["unresolved_signatures"] == 0
    assert parser["enum_constraints"] == 80
    assert parser["numeric_range_constraints"] == 33
    assert parser["uncheckable_constraints"] == 1
    state = summary["state_summary"]
    assert state["risk_relation_counts"] == {
        "exact": 75,
        "m0-lower": 3,
        "observation-lower": 3,
        "unresolved": 23,
    }
    assert state["most_promising_safe_cell"] == {
        "state": '["schema-clean","empty","unresolved","zero","zero"]',
        "support": 7,
        "saves": 1,
        "harms": 0,
        "frozen_minimum_saves": 2,
        "eligible": False,
    }


def test_result_summary_binds_external_bytes_and_terminal_rule() -> None:
    summary = _load("result-summary.json")
    raw = summary["raw_result"]
    assert raw["bytes"] == 19602
    assert raw["file_sha256"] == (
        "be88b018c11183173bd3cb22cb132b03c9d09fbb17dfeab6c54ce0e5f582120a"
    )
    assert raw["self_sha256"] == (
        "7837e9e0a821af5809cfa96e0eefbb8caf7ceb3dcafb52988f7149c26fa4960b"
    )
    assert raw["policy_self_sha256"] == (
        "85872638953f31fe16f24687017997f2aa5d1ac3980fbd1b0427f7cc09214b26"
    )
    assert summary["next_design_constraint"] == (
        "change information acquisition or evidence generation; do not tune "
        "schema-risk thresholds or categories on these returns"
    )
