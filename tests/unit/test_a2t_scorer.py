"""Audio2Tool tool-call scorer binding (P1 scaffold) + gated-driver end-to-end.

The scorer is registered under ``a2t-toolcall`` in the ONE scorer registry
(``core.base.SCORERS``) so ``score_bundle``/``finalize_bundle`` reach it with
the uniform ``scorer(outputs_path, lock, root)`` signature. Gold enters
scorer-side only (``data.audio2tool.load_expected_calls``); the frozen
scoring package is never touched.
"""

import json

import pytest

import speech_aware_evidence_acquisition.core  # noqa: F401 (populate registries)
import speech_aware_evidence_acquisition.reproduction.a2t_scorer as a2t_scorer_module
from speech_aware_evidence_acquisition.contracts import ExecutionPlan
from speech_aware_evidence_acquisition.core.base import SCORERS
from speech_aware_evidence_acquisition.core.config import ComposedConfig, protocol_hash
from speech_aware_evidence_acquisition.core.driver import load_split, run_experiment
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.reproduction.a2t_scorer import (
    ToolCallScoringError,
    score_audio2tool_outputs,
)

A2T_RECEIPT_NAME = "r1-a2t-test"

_CORRECT_TIER1 = '[{"name": "setLighting", "arguments": {}}]'


def _write_outputs(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )
    return path


def _rows(tier1_text=_CORRECT_TIER1, tier3_text="no json here", tier7_text="not json"):
    return [
        {"sample_id": "tier1_direct:000001", "text": tier1_text},
        {"sample_id": "tier3_multi_intent:000004", "text": tier3_text},
        {"sample_id": "tier7_multiturn:000009", "text": tier7_text},
    ]


def test_scorer_is_registered():
    assert "a2t-toolcall" in SCORERS.names()


def test_scores_per_sample_per_tier_and_aggregate(audio2tool_world, tmp_path):
    lock = load_lock(audio2tool_world.lock_path)
    outputs = _write_outputs(tmp_path / "run.outputs.jsonl", _rows())
    result = score_audio2tool_outputs(
        outputs, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root
    )
    per_sample = {entry["sample_id"]: entry for entry in result["per_sample"]}
    assert per_sample["tier1_direct:000001"]["tool_accuracy"] == 1.0
    assert per_sample["tier1_direct:000001"]["exact_match"] == 1.0
    assert per_sample["tier1_direct:000001"]["parsed"] is True
    assert per_sample["tier3_multi_intent:000004"]["tool_accuracy"] == 0.0
    assert per_sample["tier3_multi_intent:000004"]["parsed"] is False
    assert per_sample["tier7_multiturn:000009"]["tier"] == "tier7_multiturn"
    aggregate = result["aggregate"]
    assert aggregate["samples"] == 3
    assert aggregate["tool_accuracy"] == pytest.approx(1 / 3)
    assert aggregate["parse_failures"] == 2
    assert aggregate["scorer_version"] == "a2t-scorer-v1"
    assert aggregate["gold_version"] == "a2t-gold-v1"
    per_tier = aggregate["per_tier"]
    assert set(per_tier) == {"tier1_direct", "tier3_multi_intent", "tier7_multiturn"}
    assert per_tier["tier1_direct"]["tool_accuracy"] == 1.0
    assert per_tier["tier3_multi_intent"]["samples"] == 1


def test_partial_slot_credit_flows_through(audio2tool_world, tmp_path):
    lock = load_lock(audio2tool_world.lock_path)
    # tier3 gold: setSecurityMode(mode='Armed_Away', level=2) + 3 more calls.
    tier3_text = json.dumps(
        [{"name": "setSecurityMode", "arguments": {"mode": "Armed_Away", "level": 2}}]
    )
    outputs = _write_outputs(tmp_path / "run.outputs.jsonl", _rows(tier3_text=tier3_text))
    result = score_audio2tool_outputs(
        outputs, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root
    )
    tier3 = next(
        entry for entry in result["per_sample"] if entry["sample_id"] == "tier3_multi_intent:000004"
    )
    assert tier3["tool_accuracy"] == 0.0  # 3 gold calls missing
    assert tier3["slot_precision"] == 1.0  # every predicted slot is correct
    assert 0.0 < tier3["slot_f1"] < 1.0


def test_unknown_sample_id_fails_closed(audio2tool_world, tmp_path):
    lock = load_lock(audio2tool_world.lock_path)
    outputs = _write_outputs(
        tmp_path / "run.outputs.jsonl", [{"sample_id": "tier9_bogus:000001", "text": "[]"}]
    )
    with pytest.raises(ToolCallScoringError, match="tier9_bogus"):
        score_audio2tool_outputs(
            outputs, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root
        )


def test_duplicate_sample_rows_fail_closed(audio2tool_world, tmp_path):
    lock = load_lock(audio2tool_world.lock_path)
    row = {"sample_id": "tier1_direct:000001", "text": _CORRECT_TIER1}
    outputs = _write_outputs(tmp_path / "run.outputs.jsonl", [row, row])
    with pytest.raises(ToolCallScoringError, match="duplicate"):
        score_audio2tool_outputs(
            outputs, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root
        )


def test_empty_outputs_fail_closed(audio2tool_world, tmp_path):
    lock = load_lock(audio2tool_world.lock_path)
    outputs = tmp_path / "run.outputs.jsonl"
    outputs.write_text("", encoding="utf-8")
    with pytest.raises(ToolCallScoringError, match="empty"):
        score_audio2tool_outputs(
            outputs, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root
        )


def test_malformed_jsonl_fails_closed(audio2tool_world, tmp_path):
    lock = load_lock(audio2tool_world.lock_path)
    outputs = tmp_path / "run.outputs.jsonl"
    outputs.write_text("{not json}\n", encoding="utf-8")
    with pytest.raises(ToolCallScoringError, match="malformed"):
        score_audio2tool_outputs(
            outputs, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root
        )


def test_registered_scorer_uses_the_study_repo_receipt_by_default(
    audio2tool_world, tmp_path, monkeypatch
):
    """Through the registry (the exact ``score_bundle`` call shape, three
    positional args), the scorer binds to the study repo's own committed
    receipt; the monkeypatch stands in for REPO_ROOT because tests must not
    depend on the real receipt resolving against synthetic data."""

    monkeypatch.setattr(a2t_scorer_module, "REPO_ROOT", audio2tool_world.repo_root)
    lock = load_lock(audio2tool_world.lock_path)
    outputs = _write_outputs(tmp_path / "run.outputs.jsonl", _rows())
    scorer = SCORERS.resolve("a2t-toolcall")
    result = scorer(outputs, lock, audio2tool_world.data_root)
    assert result["aggregate"]["samples"] == 3


# ---------------------------------------------------------------------------
# End-to-end: the gated driver path over the synthetic Audio2Tool world.
# ---------------------------------------------------------------------------


class _OpenGate:
    def assert_model_touch_allowed(self, plan):
        pass


def _transport(request_bytes):
    payload = json.loads(request_bytes.decode("utf-8"))
    assert "Available tools" in payload["task_instruction"]
    assert '"tool_name": "setLighting"' in payload["task_instruction"]
    return json.dumps({"text": _CORRECT_TIER1, "usage": {"prompt_tokens": 3}}).encode()


def test_run_experiment_end_to_end_on_the_probe_split(audio2tool_world, tmp_path, monkeypatch):
    # The CARRIERS seam calls loaders as loader(lock, root); the audio2tool
    # loader resolves its receipt repo at call time from the module attribute,
    # so the synthetic world binds it here exactly as a real run binds the
    # real checkout.
    import speech_aware_evidence_acquisition.data.audio2tool as audio2tool_module

    monkeypatch.setattr(audio2tool_module, "REPO_ROOT", audio2tool_world.repo_root)
    lock = load_lock(audio2tool_world.lock_path)
    repo_root = audio2tool_world.repo_root
    ids, split_hash, split_role = load_split(
        repo_root, A2T_RECEIPT_NAME, lock, audio2tool_world.data_root
    )
    assert len(ids) == 3
    assert split_role == "discovery"
    values = {
        "carrier_lock_key": "audio2tool",
        "split_name": A2T_RECEIPT_NAME,
        "arm": "bare-core",
        "policy": "fixed",
        "evidence_source": "none",
        "evidence_mismatch": False,
        "scorers": ["a2t-toolcall", "cost"],
        "task_instruction_template": audio2tool_world.template_relpath,
        "task_instruction_fill": "audio2tool-tool-schemas",
        "decoding_params": {"temperature": 0, "seed": 20260803},
        "experiment_id": "SAEA-E-TEST",
    }
    composed = ComposedConfig(
        values=values,
        config_hash="d" * 64,
        fragments={"model": "m", "dataset": "d", "baseline": "b", "experiment": "e"},
    )
    plan = ExecutionPlan(
        run_id="SAEA-E-TEST-a2t",
        execution_profile="baseline-reproduction",
        carrier_lock_key="audio2tool",
        split_role="discovery",
        split_identity_hash=split_hash,
        planned_model_calls=10,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=1000,
        protocol_hash=protocol_hash("d" * 64, "bare-core", split_hash),
        attempt_id="attempt-a2t-0001",
    )
    result = run_experiment(
        composed=composed,
        plan=plan,
        gate=_OpenGate(),
        lock=lock,
        root=audio2tool_world.data_root,
        run_dir=tmp_path / "run",
        transport=_transport,
        repo_root=repo_root,
    )
    lines = result.outputs_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    rows = [json.loads(line) for line in lines]
    assert [row["sample_id"] for row in rows] == [
        "tier1_direct:000001",
        "tier3_multi_intent:000004",
        "tier7_multiturn:000009",
    ]
    assert result.cost["calls_used"] == 3

    scores = score_audio2tool_outputs(
        result.outputs_path, lock, audio2tool_world.data_root, repo_root=repo_root
    )
    # The transport answered setLighting() everywhere: only tier1 is right.
    assert scores["aggregate"]["tool_accuracy"] == pytest.approx(1 / 3)
    assert scores["aggregate"]["per_tier"]["tier1_direct"]["exact_match"] == 1.0
