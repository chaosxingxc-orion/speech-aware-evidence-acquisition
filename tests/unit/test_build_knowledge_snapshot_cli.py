"""The shared knowledge CLI resolves an explicitly bound lock from an isolated checkout."""

import importlib.util
from pathlib import Path
import sys

import pytest


_SCRIPT = Path(__file__).resolve().parents[2] / "scripts/build_knowledge_snapshot.py"
_SPEC = importlib.util.spec_from_file_location("knowledge_build_cli_under_test", _SCRIPT)
cli = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(cli)


@pytest.mark.parametrize("explicit", [True, False])
def test_build_cli_preserves_default_and_explicit_lock_binding(monkeypatch, tmp_path, explicit):
    lock = tmp_path / "datasets.lock.json"
    captured = {}
    monkeypatch.setattr(cli, "build_one", lambda *args, **kwargs: captured.update(
        args=args, kwargs=kwargs,
    ) or 0)
    argv = [str(_SCRIPT), "--size", "full", "--dimensions", "content",
            "--view", "slot-fillers", "--value-format", "intent-role-coverage"]
    if explicit:
        argv.extend(["--lock-path", str(lock)])
    monkeypatch.setattr(sys, "argv", argv)
    assert cli.main() == 0
    assert captured["kwargs"]["lock_path"] == (lock if explicit else None)
    assert captured["kwargs"]["value_format"] == "intent-role-coverage"


def test_build_resolves_explicit_lock_without_adjacent_checkout(monkeypatch, tmp_path):
    lock = tmp_path / "pinned-lock.json"
    seen = []
    monkeypatch.setattr(cli, "umbrella_lock_path",
                        lambda *_: pytest.fail("must not infer another checkout"))
    def stop_after_resolution(path):
        seen.append(path)
        raise RuntimeError("stop before reading sources")
    monkeypatch.setattr(cli, "load_lock", stop_after_resolution)
    with pytest.raises(RuntimeError, match="stop before reading sources"):
        cli.build_one(None, ("content",), lock_path=lock)
    assert seen == [lock]


def test_split_identity_uses_the_same_explicit_lock_binding(monkeypatch, tmp_path):
    lock = tmp_path / "pinned-lock.json"
    captured = []
    monkeypatch.setattr(sys, "argv", [str(_SCRIPT), "--freeze-split-identity",
                                     "--lock-path", str(lock)])
    monkeypatch.setattr(cli, "freeze_split_identity",
                        lambda lock_path=None: captured.append(lock_path) or 0)
    assert cli.main() == 0
    assert captured == [lock]
