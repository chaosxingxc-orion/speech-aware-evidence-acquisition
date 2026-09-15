"""Data-independent regression checks for the held E21 native-window cells."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _cell(name):
    return json.loads((ROOT / "configs" / "experiment" / name).read_text())


def test_held_direct_and_context_cells_share_the_44_parent_1593_window_roster():
    direct = _cell("e21-native-window-direct-full44-v1.json")
    system = _cell("e21-native-window-context-tools-full44-v1.json")
    for document in (direct, system):
        assert document["population"] == {
            "count": 44,
            "execution_units": 1593,
            "historically_exposed": True,
            "split_identity_hash": "fcc1b0bc55432d02347dcdf730c6bcef561a9b0ad9605c45b367e1ed3da5d69e",
        }
        assert document["generation_budget"]["ceilings_are_not_targets"] is True
        cell = document["cells"][0]
        assert cell["readiness"]["state"] == "held"
        assert cell["allowed_execution_stages"] == ["check"]
        assert document["execution_plan"]["planned_model_calls"] == document["generation_budget"]["cap"]
        assert "automatic restart" in document["failure_policy"]
    assert direct["cells"][0]["dataset_fragment"] == system["cells"][0]["dataset_fragment"]
    assert direct["cells"][0]["model_fragment"] == system["cells"][0]["model_fragment"]
    assert direct["generation_budget"] == {"cap": 1593, "ceilings_are_not_targets": True, "target": 1593}
    assert system["generation_budget"]["target"] == 1593 * 4
    assert system["generation_budget"]["cap"] >= system["generation_budget"]["target"]


def test_held_cells_do_not_admit_worker_fit_or_encoding_stages():
    for name in (
        "e21-native-window-direct-full44-v1.json",
        "e21-native-window-context-tools-full44-v1.json",
    ):
        stages = _cell(name)["cells"][0]["allowed_execution_stages"]
        assert set(stages).isdisjoint({"worker", "fit", "encoding", "generate"})
