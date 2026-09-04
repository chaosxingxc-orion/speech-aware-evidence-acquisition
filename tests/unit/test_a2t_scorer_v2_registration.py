"""Registration + I/O-contract tests for the v2 Audio2Tool scorer (slice
C3c): ``a2t-toolcall-v2`` binds ``reproduction.a2t_scorer.
score_audio2tool_outputs_v2`` into the SAME ``core.base.SCORERS`` registry
``a2t-toolcall`` (v1, unchanged) already lives in.

The synthetic-fixture tests below reuse ``audio2tool_world`` (the SAME
fixture ``tests/unit/test_a2t_scorer.py`` uses for v1) rather than defining
a second one: its ``tools_registry.csv`` covers ``setLighting``/
``setSecurityMode`` only, which is exactly what is needed to exercise both
the positive path (tier1's gold is ``setLighting``, in registry) and the
registry-drift refusal (tier7's gold is ``setAlarm``, absent from that
fixture's registry) without any synthetic data of this test file's own.

The identity test at the bottom is opt-in: it is skipped unless
``SPEECHRL_DATA_DIR`` and the real sealed A0-400 ``outputs.jsonl`` are
actually present on this host (same skip convention as
``tests/unit/test_audio2tool_tools.py``'s real-registry coverage).
"""

from __future__ import annotations

import json

import pytest

import speech_aware_evidence_acquisition.core  # noqa: F401 (populate registries)
from speech_aware_evidence_acquisition.core.base import SCORERS
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.reproduction.a2t_scorer import (
    ToolCallScoringError,
    score_audio2tool_outputs,
    score_audio2tool_outputs_v2,
)

_CORRECT_TIER1 = '[{"name": "setLighting", "arguments": {}}]'


def _write_outputs(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )
    return path


# ---------------------------------------------------------------------------
# Registration.
# ---------------------------------------------------------------------------


def test_v2_scorer_is_registered():
    assert "a2t-toolcall-v2" in SCORERS.names()


def test_v2_scorer_resolves_to_the_same_function_object():
    assert SCORERS.resolve("a2t-toolcall-v2") is score_audio2tool_outputs_v2


def test_v1_scorer_stays_registered_alongside_v2():
    assert "a2t-toolcall" in SCORERS.names()
    assert SCORERS.resolve("a2t-toolcall") is score_audio2tool_outputs


# ---------------------------------------------------------------------------
# I/O contract, over the synthetic Audio2ToolWorld fixture.
# ---------------------------------------------------------------------------


def test_v2_scores_a_correct_tier1_row_with_ordered_and_multiset_fields(audio2tool_world, tmp_path):
    lock = load_lock(audio2tool_world.lock_path)
    outputs = _write_outputs(
        tmp_path / "run.outputs.jsonl",
        [{"sample_id": "tier1_direct:000001", "text": _CORRECT_TIER1}],
    )
    result = score_audio2tool_outputs_v2(
        outputs, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root
    )
    entry = result["per_sample"][0]
    assert entry["tool_accuracy"] == 1.0
    assert entry["tool_accuracy_multiset"] == 1.0
    assert entry["exact_match"] == 1.0
    assert entry["parsed"] is True
    assert entry["extra_keys_stripped"] == 0
    assert entry["coerced_values"] == 0

    aggregate = result["aggregate"]
    assert aggregate["samples"] == 1
    assert aggregate["scorer_version"] == "a2t-scorer-v2"
    assert aggregate["gold_version"] == "a2t-gold-v1"
    assert aggregate["per_tier"]["tier1_direct"]["exact_match"] == 1.0


def test_v2_refuses_on_registry_drift(audio2tool_world, tmp_path):
    # tier7's gold tool ("setAlarm") has no row at all in this fixture's
    # tools_registry.csv (only setSecurityMode/setLighting are present) --
    # a registry-drift refusal, wrapped as the same ToolCallScoringError
    # every other refusal in this module raises.
    lock = load_lock(audio2tool_world.lock_path)
    outputs = _write_outputs(
        tmp_path / "run.outputs.jsonl",
        [{"sample_id": "tier7_multiturn:000009", "text": "[]"}],
    )
    with pytest.raises(ToolCallScoringError, match="setAlarm"):
        score_audio2tool_outputs_v2(
            outputs, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root
        )


def test_v2_and_v1_agree_on_registered_sample_universe_refusals(audio2tool_world, tmp_path):
    lock = load_lock(audio2tool_world.lock_path)
    outputs = _write_outputs(
        tmp_path / "run.outputs.jsonl", [{"sample_id": "tier9_bogus:000001", "text": "[]"}]
    )
    with pytest.raises(ToolCallScoringError, match="tier9_bogus"):
        score_audio2tool_outputs_v2(
            outputs, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root
        )


def test_v2_empty_outputs_fails_closed(audio2tool_world, tmp_path):
    lock = load_lock(audio2tool_world.lock_path)
    outputs = tmp_path / "run.outputs.jsonl"
    outputs.write_text("", encoding="utf-8")
    with pytest.raises(ToolCallScoringError, match="empty"):
        score_audio2tool_outputs_v2(
            outputs, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root
        )


def test_v2_through_the_registry_uses_the_study_repo_receipt_by_default(
    audio2tool_world, tmp_path, monkeypatch
):
    import speech_aware_evidence_acquisition.reproduction.a2t_scorer as a2t_scorer_module

    monkeypatch.setattr(a2t_scorer_module, "REPO_ROOT", audio2tool_world.repo_root)
    lock = load_lock(audio2tool_world.lock_path)
    outputs = _write_outputs(
        tmp_path / "run.outputs.jsonl",
        [{"sample_id": "tier1_direct:000001", "text": _CORRECT_TIER1}],
    )
    scorer = SCORERS.resolve("a2t-toolcall-v2")
    result = scorer(outputs, lock, audio2tool_world.data_root)
    assert result["aggregate"]["samples"] == 1
    assert result["aggregate"]["exact_match"] == 1.0


# ---------------------------------------------------------------------------
# Identity test (opt-in): score the real sealed A0-400 outputs with both
# scorers and compare against the S1 study's already-verified numbers
# (docs/checks/speech-aware-evidence-acquisition/
# 2026-09-03-a2t-scorer-v2-zero-contact-study/README.md). Skipped when
# SPEECHRL_DATA_DIR or the sealed outputs file are not available on this
# host -- same convention as test_audio2tool_tools.py's real-registry test.
# ---------------------------------------------------------------------------


def _real_a0_fixture():
    from speech_aware_evidence_acquisition.data.lock import (
        AssetResolutionError,
        data_root,
        umbrella_lock_path,
    )

    try:
        root = data_root()
        lock = load_lock(umbrella_lock_path())
        outputs = (
            root
            / "runs"
            / "SAEA-BASE-a2t-a0-400"
            / "attempt-20260818T055500Z-res315"
            / "outputs.jsonl"
        )
        if not outputs.is_file():
            return None
        return lock, root, outputs
    except (AssetResolutionError, OSError):
        return None


_REAL_A0 = _real_a0_fixture()


@pytest.mark.skipif(
    _REAL_A0 is None,
    reason="SPEECHRL_DATA_DIR / sealed A0-400 outputs.jsonl not available on this host",
)
def test_v1_and_v2_identity_against_sealed_a0_outputs(tmp_path):
    """The real sealed A0 flight's outputs.jsonl carries the model text
    under ``response_text`` (this flight's own field name -- see
    ``analysis.a2t_scorer_v2_study``'s ``text_field`` parameter docstring),
    not the ``text`` field both registered scorer functions read; this test
    remaps the field name into a scratch copy (never touches the sealed
    file itself) before calling the real, unmodified scorer functions --
    the same remap the S1 study already performed for this exact source."""

    lock, root, outputs = _REAL_A0
    remapped = tmp_path / "a0-outputs-text-remap.jsonl"
    lines = outputs.read_text(encoding="utf-8").split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    with remapped.open("w", encoding="utf-8", newline="\n") as handle:
        for line in lines:
            row = json.loads(line)
            row["text"] = row.pop("response_text")
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    v1 = score_audio2tool_outputs(remapped, lock, root)
    v2 = score_audio2tool_outputs_v2(remapped, lock, root)

    assert round(v1["aggregate"]["tool_accuracy"], 4) == 0.5425
    assert round(v1["aggregate"]["exact_match"], 4) == 0.2425

    assert round(v2["aggregate"]["tool_accuracy"], 4) == 0.5300
    assert round(v2["aggregate"]["exact_match"], 4) == 0.3125

    tier1 = v2["aggregate"]["per_tier"]["tier1_direct"]
    assert round(tier1["tool_accuracy"], 4) == 0.5800
    assert round(tier1["exact_match"], 4) == 0.4000
