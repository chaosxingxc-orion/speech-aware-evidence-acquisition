"""Unit tests for ``scripts/mf8_speech_to_knowledge_audit.py``.

Pure helpers only: no SLURP data, no lock, no model, no GPU and no filesystem
beyond the tmp paths the tests write themselves.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
AUDIT_SCRIPT = REPO / "scripts" / "mf8_speech_to_knowledge_audit.py"


def _audit():
    """Load the script by path -- the shared WSL venv carries an unrelated
    top-level ``scripts`` package, so ``import scripts.<name>`` resolves to
    that one instead of this repository's."""

    name = "test_mf8_audit_module"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, AUDIT_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


audit = _audit()


def test_recording_filename_inverts_the_sample_id_construction() -> None:
    assert audit.recording_filename("slurp:devel:000011:audio-1497266596") == (
        "audio-1497266596.flac"
    )
    assert audit.recording_filename("slurp:train:000042:audio-1") == "audio-1.flac"


@pytest.mark.parametrize(
    "sample_id",
    ["", "slurp:devel:000011", "slurp:devel:000011:", "slurp:devel:000011:a:b"],
)
def test_recording_filename_refuses_a_malformed_sample_id(sample_id: str) -> None:
    with pytest.raises(ValueError):
        audit.recording_filename(sample_id)


def test_roster_sample_ids_reads_committed_file_order(tmp_path: Path) -> None:
    path = tmp_path / "roster.json"
    path.write_text(
        json.dumps({"items": [{"sample_id": "b"}, {"sample_id": "a"}]}),
        encoding="utf-8",
    )
    assert audit.roster_sample_ids(path) == ("b", "a")


def test_roster_sample_ids_refuses_an_empty_or_repeating_roster(tmp_path: Path) -> None:
    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({"items": []}), encoding="utf-8")
    with pytest.raises(ValueError):
        audit.roster_sample_ids(empty)

    repeated = tmp_path / "repeated.json"
    repeated.write_text(
        json.dumps({"items": [{"sample_id": "a"}, {"sample_id": "a"}]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        audit.roster_sample_ids(repeated)

    untyped = tmp_path / "untyped.json"
    untyped.write_text(json.dumps({"items": [{"sample_id": 7}]}), encoding="utf-8")
    with pytest.raises(ValueError):
        audit.roster_sample_ids(untyped)


def test_histogram_is_sorted_by_integer_key() -> None:
    assert audit.histogram([10, 2, 2, 0]) == {"0": 1, "2": 2, "10": 1}
    assert audit.histogram([]) == {}


def test_quantiles_are_nearest_rank_and_stable() -> None:
    assert audit.quantiles([]) == {}
    single = audit.quantiles([4])
    assert single["min"] == single["median"] == single["max"] == 4.0
    values = list(range(1, 11))
    result = audit.quantiles(values)
    assert result["min"] == 1.0
    assert result["max"] == 10.0
    assert result["mean"] == 5.5
    assert result["median"] in {5.0, 6.0}
    assert result["p25"] <= result["median"] <= result["p75"] <= result["p90"]


def test_at_least_counts_are_monotone() -> None:
    counts = audit.at_least_counts([0, 1, 3, 5, 8], (1, 3, 5, 8))
    assert counts == {">=1": 4, ">=3": 3, ">=5": 2, ">=8": 1}
