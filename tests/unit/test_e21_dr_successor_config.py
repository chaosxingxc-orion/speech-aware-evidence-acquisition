"""Keep the held DR successor on the real shared window controller path."""
import hashlib
import json
from pathlib import Path

from speech_aware_evidence_acquisition.core.config import compose
from speech_aware_evidence_acquisition.core.flight.campaign import load_campaign_cells
from speech_aware_evidence_acquisition.reproduction.window_controller import validate_window_controller

REPO = Path(__file__).resolve().parents[2]
EXPERIMENT = "e21-dr-shared-two-generation-v1"


def test_dr_successor_composes_real_controller_and_preserves_legacy_wire_fields():
    cells = load_campaign_cells(REPO, EXPERIMENT)
    assert len(cells) == 4
    for cell in cells:
        spec = cell.document
        assert spec["readiness"]["state"] == "held"
        values = compose(REPO, spec["model_fragment"], spec["dataset_fragment"],
                         spec["baseline_fragment"], EXPERIMENT).values
        assert values["policy"] == "obs-repair-loop-ojw"
        assert values["decoding_params"]["max_tokens"] == 1024
        assert validate_window_controller(values)
        new = json.loads((REPO / "configs/baseline" / (spec["baseline_fragment"] + ".json")).read_text())
        old = json.loads((REPO / "configs/baseline" / (spec["baseline_fragment"].removesuffix("-ojw") + ".json")).read_text())
        changed = {key for key in set(new) | set(old) if new.get(key) != old.get(key)}
        assert changed == {"policy", "ojw_workflow_timeout_seconds", "obs_controller_program"}


def test_dr_declares_four_correlated_deliveries_and_valid_source_pins():
    document = json.loads((REPO / "configs/experiment" / (EXPERIMENT + ".json")).read_text())
    parents = {c["cell_id"] for c in document["cells"] if "campaign" in c["allowed_execution_stages"]}
    deliveries = document["delivery_derivatives"]
    assert len(parents) == 2 and len(deliveries) == 4
    for parent in parents:
        group = [d for d in deliveries if d["parent_cell_id"] == parent]
        assert {d["response_postprocessor"] for d in group} == {
            "e21-entity-repair-substitutions-v1", "e21-free-refresh-delivery-v1"}
    for pin in document["source_pins"].values():
        assert hashlib.sha256((REPO / pin["repo_relpath"]).read_bytes()).hexdigest() == pin["sha256"]
    assert document["fit_execution_plan"]["planned_endpoint_contacts_per_fit"] == 1594
