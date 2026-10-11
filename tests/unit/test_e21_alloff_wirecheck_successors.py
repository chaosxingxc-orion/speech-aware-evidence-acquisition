"""Preflight for the wire-check-only successors of the E21 module ALL-OFF cells.

The registered cells omit ``wire-check`` from ``allowed_execution_stages`` (so
``core.flight.cli wire-check`` is refused); registered bytes are never edited, so
``scripts/flights/module/derive_e21_alloff_wirecheck_successors.py`` writes
successor fragments that admit only ``[check, wire-check]``."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.flight.campaign import (
    CampaignCell, CampaignError, load_campaign_cells,
)

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/flights/module/derive_e21_alloff_wirecheck_successors.py"
PARENTS = (
    "earnings21-native-stage3-module-alloff-v1",
    "earnings21-native-stage3-module-alloff-smoke-4-v1",
)


def _script():
    spec = importlib.util.spec_from_file_location("derive_e21_wire", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load(name: str) -> dict:
    return json.loads((ROOT / f"configs/experiment/{name}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("parent", PARENTS)
def test_successor_differs_from_parent_only_in_identity_stage_and_prose(parent):
    a, b = _load(parent), _load(parent + "-wire-v1")
    assert sorted(k for k in a if a[k] != b[k]) == ["cells", "experiment_id", "purpose"]
    assert set(a) == set(b)
    ca, cb = a["cells"][0], b["cells"][0]
    assert sorted(k for k in set(ca) | set(cb) if ca.get(k) != cb.get(k)) == [
        "allowed_execution_stages", "attempt_id", "cell_id", "readiness", "run_id"]
    for key in ("model_fragment", "dataset_fragment", "baseline_fragment"):
        assert ca[key] == cb[key]
    assert ca["allowed_execution_stages"] == ["check", "worker", "campaign"]
    assert cb["allowed_execution_stages"] == ["check", "wire-check"]
    assert cb["readiness"]["state"] == "held"
    assert cb["run_id"].endswith("-WIRE-V1") and cb["run_id"] != ca["run_id"]
    assert cb["cell_id"] == parent + "-wire-v1"


@pytest.mark.parametrize("parent", PARENTS)
def test_successor_permits_wire_check_and_nothing_that_contacts_a_model(parent):
    cell = load_campaign_cells(ROOT, parent + "-wire-v1")[0]
    cell.assert_mode("check")
    cell.assert_mode("wire-check")
    for mode in ("worker", "campaign", "prompt-fit", "prepare-window-features", "seal-only"):
        with pytest.raises(CampaignError, match="does not permit"):
            cell.assert_mode(mode)
    # The registered parent still refuses wire-check: its bytes were not edited.
    parent_cell = load_campaign_cells(ROOT, parent)[0]
    with pytest.raises(CampaignError, match="does not permit execution stage wire-check"):
        parent_cell.assert_mode("wire-check")


@pytest.mark.parametrize("parent", PARENTS)
def test_committed_successor_is_what_the_script_derives(parent):
    module = _script()
    text = (ROOT / f"configs/experiment/{parent}.json").read_text(encoding="utf-8")
    derived = module.render(module.successor_document(parent, json.loads(text)))
    assert (ROOT / f"configs/experiment/{parent}-wire-v1.json").read_text(encoding="utf-8") == derived
    plan = json.loads((ROOT / f"configs/campaign/{parent}-wire-v1.json").read_text(encoding="utf-8"))
    assert plan["cells"] == [{"cell": parent + "-wire-v1", "experiment": parent + "-wire-v1"}]
