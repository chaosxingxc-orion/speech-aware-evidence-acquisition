"""``scripts/flights/batch/roll1_fill_placeholders.py``: the placeholder substitution tool.

The tool grew a ``--fragments`` argument and an ``--occurrence-policy`` when the Stage-3 ADV-1 /
CELL-1 packages were re-pointed onto the clean construction subset R01C: those packages pin one
release hash from several held cells of ONE experiment fragment, and a twin token appears only in
the twin's baselines, neither of which the original "exactly once per fragment" rule allows.

What this file proves: cell ROLL-1's own contract is unchanged (default fragments, default policy,
the exactly-once refusal, the placeholder-block bookkeeping), the two looser policies do what they
say, a token that matches nothing anywhere is still refused under every policy, and a fragment that
carries no ``stage3_pending_placeholders`` block does not grow one.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOL = REPO_ROOT / "scripts" / "flights" / "batch" / "roll1_fill_placeholders.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("roll1_fill_placeholders", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


TOOL_MODULE = _load_tool()


def _run(tmp_path: Path, argv: list[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["roll1_fill_placeholders.py", *argv])
    TOOL_MODULE.main()


def _values(tmp_path: Path, mapping: dict) -> str:
    path = tmp_path / "values.json"
    path.write_text(json.dumps(mapping), encoding="utf-8")
    return str(path)


def _fragment(tmp_path: Path, name: str, document: dict) -> str:
    path = tmp_path / name
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return name


def _read(tmp_path: Path, name: str) -> dict:
    return json.loads((tmp_path / name).read_text(encoding="utf-8"))


def test_the_default_fragments_are_still_cell_roll1s_two_baselines() -> None:
    assert TOOL_MODULE.ROLL1_FRAGMENTS == (
        "configs/baseline/slurp-native-stage3-rollout-baseline-v1.json",
        "configs/baseline/slurp-native-stage3-rollout-smoke-4-baseline-v1.json",
    )
    assert TOOL_MODULE.FRAGMENTS == TOOL_MODULE.ROLL1_FRAGMENTS


def test_fills_and_moves_a_documented_placeholder(tmp_path, monkeypatch) -> None:
    name = _fragment(tmp_path, "a.json", {
        "pin": {"sha256": "PENDING_X"},
        "stage3_pending_placeholders": [{"path": "pin.sha256", "reason": "waits for the seal"}],
    })
    _run(tmp_path, ["--fragments", name, "--values", _values(tmp_path, {"PENDING_X": "a" * 64}),
                    "--by", "the seal", "--date", "2026-09-23"], monkeypatch)
    document = _read(tmp_path, name)
    assert document["pin"]["sha256"] == "a" * 64
    assert document["stage3_pending_placeholders"] == []
    assert document["stage3_placeholders_filled"] == [
        {"path": "pin.sha256", "filled": "2026-09-23", "by": "the seal"}
    ]


def test_exactly_one_is_still_the_default_and_refuses_a_repeated_token(tmp_path, monkeypatch) -> None:
    name = _fragment(tmp_path, "a.json", {"one": "PENDING_X", "two": "PENDING_X"})
    with pytest.raises(SystemExit, match="occurs 2 times"):
        _run(tmp_path, ["--fragments", name, "--values", _values(tmp_path, {"PENDING_X": "v"}),
                        "--by", "note"], monkeypatch)


def test_at_least_one_allows_a_repeated_token_in_one_fragment(tmp_path, monkeypatch) -> None:
    name = _fragment(tmp_path, "a.json", {"one": "PENDING_X", "two": "PENDING_X"})
    _run(tmp_path, ["--fragments", name, "--values", _values(tmp_path, {"PENDING_X": "v"}),
                    "--by", "note", "--occurrence-policy", "at-least-one"], monkeypatch)
    assert _read(tmp_path, name) == {"one": "v", "two": "v"}


def test_at_least_one_still_refuses_a_fragment_that_lacks_the_token(tmp_path, monkeypatch) -> None:
    present = _fragment(tmp_path, "a.json", {"one": "PENDING_X"})
    absent = _fragment(tmp_path, "b.json", {"other": "kept"})
    with pytest.raises(SystemExit, match="expected at least 1"):
        _run(tmp_path, ["--fragments", present, absent,
                        "--values", _values(tmp_path, {"PENDING_X": "v"}),
                        "--by", "note", "--occurrence-policy", "at-least-one"], monkeypatch)


def test_any_allows_a_token_absent_from_one_fragment_of_the_set(tmp_path, monkeypatch) -> None:
    generation = _fragment(tmp_path, "a.json", {"pin": "PENDING_GEN"})
    twin = _fragment(tmp_path, "b.json", {"pin": "PENDING_TWIN"})
    _run(tmp_path, ["--fragments", generation, twin,
                    "--values", _values(tmp_path, {"PENDING_GEN": "g", "PENDING_TWIN": "t"}),
                    "--by", "note", "--occurrence-policy", "any"], monkeypatch)
    assert _read(tmp_path, generation) == {"pin": "g"}
    assert _read(tmp_path, twin) == {"pin": "t"}


def test_a_token_matching_nothing_anywhere_is_refused_under_any_policy(tmp_path, monkeypatch) -> None:
    name = _fragment(tmp_path, "a.json", {"pin": "PENDING_X"})
    with pytest.raises(SystemExit, match="matched nothing"):
        _run(tmp_path, ["--fragments", name,
                        "--values", _values(tmp_path, {"PENDING_X": "v", "PENDING_TYPO": "v"}),
                        "--by", "note", "--occurrence-policy", "any"], monkeypatch)


def test_a_fragment_without_a_placeholder_block_does_not_grow_one(tmp_path, monkeypatch) -> None:
    name = _fragment(tmp_path, "a.json", {"pin": "PENDING_X"})
    _run(tmp_path, ["--fragments", name, "--values", _values(tmp_path, {"PENDING_X": "v"}),
                    "--by", "note"], monkeypatch)
    assert _read(tmp_path, name) == {"pin": "v"}


def test_a_value_that_is_itself_a_placeholder_is_refused(tmp_path, monkeypatch) -> None:
    name = _fragment(tmp_path, "a.json", {"pin": "PENDING_X"})
    with pytest.raises(SystemExit, match="bad fill"):
        _run(tmp_path, ["--fragments", name,
                        "--values", _values(tmp_path, {"PENDING_X": "PENDING_Y"}),
                        "--by", "note"], monkeypatch)
