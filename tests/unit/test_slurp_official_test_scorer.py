"""Registration + refusal tests for ``slurp-slu-official-test`` (one-read protocol
section 3.4): the TEST sibling of the official SLURP scorer.

Every test here runs on FAKES. No test gold, test roster, test audio or data root is
opened: the delegate ``score_slurp_outputs_official`` is monkeypatched, so the tests
prove only the binding (split ``test``, ``allow_heldout=True``) and the two local
refusals that run before the data root would be touched.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import speech_aware_evidence_acquisition.core  # noqa: F401 (populate registries)
from speech_aware_evidence_acquisition.core.base import SCORERS
from speech_aware_evidence_acquisition.reproduction import slurp_official_eval as module
from speech_aware_evidence_acquisition.reproduction.slurp_official_eval import (
    SlurpOfficialEvalError,
    score_slurp_outputs_official,
    score_slurp_outputs_official_test,
)


def _outputs(tmp_path: Path, sample_ids: list[str]) -> Path:
    path = tmp_path / "outputs.jsonl"
    path.write_text(
        "".join(json.dumps({"sample_id": sid, "response": "{}"}) + "\n" for sid in sample_ids),
        encoding="utf-8",
    )
    return path


def test_registered_under_its_own_id_and_distinct_from_the_devel_binding():
    assert SCORERS.resolve("slurp-slu-official-test") is score_slurp_outputs_official_test
    assert SCORERS.resolve("slurp-slu-official") is score_slurp_outputs_official


def test_binds_split_test_and_allow_heldout(monkeypatch, tmp_path):
    seen: dict[str, object] = {}

    def fake(outputs_path, lock, root, **kwargs):
        seen.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(module, "score_slurp_outputs_official", fake)
    path = _outputs(tmp_path, ["slurp:test:000001:audio-1-headset", "slurp:test:000002:audio-2"])
    assert score_slurp_outputs_official_test(path, {}, tmp_path) == {"ok": True}
    assert seen == {"split_id": "test", "allow_heldout": True}


def test_refuses_a_non_test_row_before_the_data_root(monkeypatch, tmp_path):
    def fake(*args, **kwargs):  # pragma: no cover - must never be reached
        raise AssertionError("the delegate must not be called for a non-test row")

    monkeypatch.setattr(module, "score_slurp_outputs_official", fake)
    path = _outputs(tmp_path, ["slurp:test:000001:audio-1", "slurp:devel:000002:audio-2"])
    with pytest.raises(SlurpOfficialEvalError, match="not a 'slurp:test:' sample"):
        score_slurp_outputs_official_test(path, {}, tmp_path)


def test_refuses_allow_heldout_false(monkeypatch, tmp_path):
    monkeypatch.setattr(module, "score_slurp_outputs_official", lambda *a, **k: {})
    path = _outputs(tmp_path, ["slurp:test:000001:audio-1"])
    with pytest.raises(SlurpOfficialEvalError, match="allow_heldout=True by construction"):
        score_slurp_outputs_official_test(path, {}, tmp_path, allow_heldout=False)


def test_devel_binding_still_refuses_a_test_row(tmp_path):
    path = _outputs(tmp_path, ["slurp:test:000001:audio-1"])
    with pytest.raises(SlurpOfficialEvalError, match="HELD OUT 'test' split"):
        score_slurp_outputs_official(path, {}, tmp_path)
