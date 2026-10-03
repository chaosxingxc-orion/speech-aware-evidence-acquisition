"""Read queue references without introducing another experiment implementation."""

import json
from pathlib import Path
import pytest
from speech_aware_evidence_acquisition.core.flight.cli import load_campaign_plan
from speech_aware_evidence_acquisition.core.flight.campaign import CampaignError

R = Path(__file__).resolve().parents[2]


def test_registered_campaign_preserves_explicit_order_and_fragments():
    pairs = load_campaign_plan(
        R, R / "docs/readiness/2026-09-09-ku-s3-max256-registration/campaign.json"
    )
    assert [cell.run_id for _, cell in pairs] == [
        "SAEA-SLURP-KU-S3A-CONTROL-G1-MAX256-V1",
        "SAEA-SLURP-KU-S3A-G1-MAX256-V1",
        "SAEA-SLURP-KU-S3A-TWIN-G1-MAX256-V1",
    ]
    assert all(
        "campaign" in cell.document["allowed_execution_stages"] for _, cell in pairs
    )


@pytest.mark.parametrize("defect", ["duplicate", "fit", "missing", "empty"])
def test_invalid_campaign_plan_refuses_before_runtime_build(tmp_path, defect):
    item = {
        "experiment": "slurp-ku-s3a-g1-max256-v1",
        "cell": "ku-s3a-g1-max256-generation",
    }
    cells = [item]
    if defect == "duplicate":
        cells = [item, item]
    if defect == "fit":
        cells = [{**item, "cell": "ku-s3a-g1-max256-fit"}]
    if defect == "missing":
        cells = [{**item, "cell": "not-declared"}]
    if defect == "empty":
        cells = []
    path = tmp_path / "plan.json"
    path.write_text(json.dumps({"schema": "saea-campaign-plan-v1", "cells": cells}))
    with pytest.raises(CampaignError):
        load_campaign_plan(R, path)


def node_plan(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core.flight import cli
    from speech_aware_evidence_acquisition.core.flight.campaign import CampaignCell

    cells = [
        CampaignCell.from_document(
            {
                "cell_id": f"cell-{i}",
                "model_fragment": "m",
                "dataset_fragment": "d",
                "baseline_fragment": "b",
                "run_id": f"run-{i}",
                "attempt_id": f"attempt-{i}",
                "readiness": {"state": "ready"},
                "allowed_execution_stages": ["node-panel"],
            }
        )
        for i in range(2)
    ]
    monkeypatch.setattr(cli, "load_campaign_cells", lambda repo, exp: tuple(cells))
    document = {
        "schema": "saea-node-panel-plan-v1",
        "panel_id": "panel",
        "cells": [
            {
                "experiment": "fixture",
                "cell": c.document["cell_id"],
                "run_id": c.run_id,
                "attempt_id": c.attempt_id,
                "job_keys": [["s0", None], ["s1", None]],
            }
            for c in cells
        ],
    }
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(document))
    return path, document, cells


def test_node_plan_keeps_exact_independent_ownership_and_order(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core.flight.cli import load_node_panel_plan

    path, document, cells = node_plan(tmp_path, monkeypatch)
    selected, panel_id, members = load_node_panel_plan(tmp_path, path)
    assert tuple(c for _, c in selected) == tuple(cells)
    assert panel_id == "panel"
    assert [(m.run_id, m.attempt_id, m.job_keys) for m in members] == [
        (c.run_id, c.attempt_id, (("s0", None), ("s1", None))) for c in cells
    ]


@pytest.mark.parametrize(
    "defect",
    [
        "schema",
        "attempt",
        "run",
        "empty",
        "duplicate",
        "roster",
        "mode",
        "resume",
        "extra",
    ],
)
def test_node_plan_refuses_ambiguous_or_recovery_members(tmp_path, monkeypatch, defect):
    from speech_aware_evidence_acquisition.core.flight.cli import load_node_panel_plan

    path, doc, cells = node_plan(tmp_path, monkeypatch)
    if defect == "schema":
        doc["schema"] = "saea-campaign-plan-v1"
    if defect in {"attempt", "run"}:
        doc["cells"][0][defect + "_id"] = "wrong"
    if defect == "empty":
        doc["cells"] = []
    if defect == "duplicate":
        doc["cells"][1] = doc["cells"][0]
    if defect == "roster":
        doc["cells"][0]["job_keys"] *= 2
    if defect == "mode":
        cells[0].document["allowed_execution_stages"] = ["campaign"]
    if defect == "resume":
        cells[0].document["resume_from"] = {"attempt_id": "old"}
    if defect == "extra":
        doc["cells"][0]["replacement"] = True
    path.write_text(json.dumps(doc))
    with pytest.raises(CampaignError):
        load_node_panel_plan(tmp_path, path)


@pytest.mark.parametrize("mode", ["node-panel", "node-panel-worker"])
def test_node_panel_cli_uses_all_runtime_owners_and_no_partial_override(
    tmp_path, monkeypatch, capsys, mode
):
    from speech_aware_evidence_acquisition.core.flight import cli
    from types import SimpleNamespace

    path, document, cells = node_plan(tmp_path, monkeypatch)
    for cell in cells:
        cell.document["allowed_execution_stages"] = [mode]
    seen = []
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    monkeypatch.setattr(cli, "__file__", str(tmp_path / "src/pkg/core/flight/cli.py"))
    monkeypatch.setattr(
        cli, "build_flight_runtime", lambda *a, **kw: SimpleNamespace(**kw)
    )
    monkeypatch.setattr(
        cli,
        "assert_prepared_artifacts_current",
        lambda flights: seen.append(("verify", len(flights))),
    )

    def run(flights, **kw):
        assert tuple(f.run_id for f in flights) == tuple(c.run_id for c in cells)
        assert kw["panel_id"] == "panel" and len(kw["members"]) == 2
        assert kw["mode"] == mode
        seen.append(("run", len(flights)))
        return {"schema": "saea-node-panel-status-v1", "states": {}}

    monkeypatch.setattr(cli, "run_node_panel", run)
    argv = [
        mode,
        "--repo-root",
        str(tmp_path),
        "--data-root",
        str(tmp_path),
        "--runtime-root",
        str(tmp_path),
        "--lock-path",
        str(tmp_path / "lock"),
        "--campaign-plan",
        str(path),
        "--owner",
        "root",
        "--expected-session-id",
        "session",
    ]
    assert cli.main(argv) == 0
    assert seen == [("verify", 2), ("run", 2)]
    with pytest.raises(SystemExit):
        cli.main(argv + ["--cell", "cell-0"])
    with pytest.raises(SystemExit):
        cli.main(argv + ["--lease-token-file", str(tmp_path / "token")])


@pytest.mark.parametrize("mode", ["node-panel", "node-panel-worker"])
def test_panel_plan_admission_does_not_convert_scoring_lifecycle(
    tmp_path, monkeypatch, mode
):
    from speech_aware_evidence_acquisition.core.flight.cli import load_node_panel_plan

    path, document, cells = node_plan(tmp_path, monkeypatch)
    for cell in cells:
        cell.document["allowed_execution_stages"] = [mode]
    assert len(load_node_panel_plan(tmp_path, path, mode=mode)[0]) == 2
    other = "node-panel" if mode == "node-panel-worker" else "node-panel-worker"
    with pytest.raises(CampaignError):
        load_node_panel_plan(tmp_path, path, mode=other)
    with pytest.raises(CampaignError):
        load_node_panel_plan(tmp_path, path, mode="worker")
