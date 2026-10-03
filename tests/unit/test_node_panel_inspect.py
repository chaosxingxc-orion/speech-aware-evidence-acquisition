"""Panel completion inspection visits every declared attempt without quality output."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import json
import pytest


@pytest.mark.parametrize("mode", ["node-panel", "node-panel-worker"])
def test_inspector_keeps_all_member_results_even_after_failure(
    tmp_path, monkeypatch, capsys, mode
):
    path = (
        Path(__file__).resolve().parents[2]
        / "scripts/flights/batch/node_panel_inspect.py"
    )
    spec = importlib.util.spec_from_file_location("node_panel_inspect_fixture", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    members = [
        SimpleNamespace(
            run_id=f"r{i}", attempt_id=f"a{i}", job_keys=(("s0", None), ("s1", None))
        )
        for i in range(8)
    ]

    def load(repo, plan, *, mode):
        assert mode == selected_mode
        return (), "panel", members

    selected_mode = mode
    monkeypatch.setattr(module, "load_node_panel_plan", load)
    calls = []

    def execute(cmd, **kw):
        calls.append(cmd)
        return SimpleNamespace(
            returncode=2 if cmd[4] == "r3" else 0,
            stdout=json.dumps(
                {"run_id": cmd[4], "attempt_id": cmd[5], "pass": cmd[4] != "r3"}
            ),
            stderr="",
        )

    monkeypatch.setattr(module.subprocess, "run", execute)
    argv = [
        "--mode",
        mode,
        "--repo-root",
        str(tmp_path),
        "--data-root",
        str(tmp_path),
        "--campaign-plan",
        str(tmp_path / "plan.json"),
        "--flight-commit",
        "a" * 40,
        "--ceiling-per-row",
        "13",
    ]
    assert module.main(argv) == 2
    assert [cmd[4:6] for cmd in calls] == [[m.run_id, m.attempt_id] for m in members]
    expected = "worker" if mode == "node-panel-worker" else "arm"
    assert all(cmd[6:9] == [expected, "2", "13"] for cmd in calls)
    report = json.loads(capsys.readouterr().out)
    assert len(report["members"]) == 8 and not report["pass"]
    assert report["panel_id"] == "panel"
    outside = argv.copy()
    outside[outside.index("--campaign-plan") + 1] = str(
        tmp_path.parent / "outside.json"
    )
    with pytest.raises(SystemExit):
        module.main(outside)
