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
