"""The SLURP consumption cell KU-S1c, as committed configuration.

Cell KU-S1c is the equal-contact, no-knowledge control of the 2026-09-05
three-dimension experiment program's consumption dimension: two contacts per
DEV-1000 row over the closed-list task, phase ``draft`` then phase ``revise``,
with the model's own draft threaded into the second control turn and no
knowledge retrieved, supplied or rendered anywhere.

Everything the cell claims is expressible as bytes in ``configs/``, so it is
checkable here, model-free, before any contact:

* the system message is the sealed closed-list baseline's, template and fill;
* both control turns are short directives and are pinned in the probe manifest;
* the phase material loads against ``phase-draft-revise-v1`` with the right
  predecessor bindings and no state fill;
* the bound knowledge snapshot is the label/prior/speaker one -- NOT the full
  ``size-full`` snapshot, whose content dimension the containment analysis
  measured refusing 78 of the 1,000 phase-2 control turns;
* the registered plan covers the arithmetic of two passes over the roster.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.phase_material import (
    load_phase_material_specs,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIGS = REPO_ROOT / "configs"
BASELINE = CONFIGS / "baseline" / "slurp-phase-draft-revise-v1.json"
CLOSED_LIST_BASELINE = CONFIGS / "baseline" / "slurp-direct-closed-list.json"
EXPERIMENT = CONFIGS / "experiment" / "slurp-consumption-ku-s1c-v1.json"
SMOKE = CONFIGS / "experiment" / "slurp-consumption-ku-s1c-smoke-4-v1.json"
PROBE_MANIFEST = CONFIGS / "probes" / "manifest.json"
PROGRAM_ID = "phase-draft-revise-v1"
DRAFT_TEMPLATE = "slurp_phase_direct.txt"
REVISE_TEMPLATE = "slurp_phase_revise.txt"
#: The TRAIN snapshot WITHOUT its content dimension: 349 label/prior/speaker
#: facets plus all 11,514 exemplar values. The full ``size-full`` snapshot is
#: what KU-S1 would have needed and what the containment analysis refused.
SNAPSHOT_SHA256 = "07f94807d173b2f2bdda9dcd95b21354e018234a208a76683d0ca4989d9ffa65"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_system_message_is_the_closed_list_baseline_s() -> None:
    fragment = _load(BASELINE)
    comparator = _load(CLOSED_LIST_BASELINE)
    for key in (
        "task_instruction_template",
        "task_instruction_fill",
        "task_instruction_template_active",
    ):
        assert fragment[key] == comparator[key], key
    # A free-text task_instruction would silently replace the template pair.
    assert "task_instruction" not in fragment
    assert fragment["scorers"] == comparator["scorers"]
    assert fragment["arm"] == comparator["arm"]
    assert (
        fragment["speech_packet_promotion_receipt_sha256"]
        == comparator["speech_packet_promotion_receipt_sha256"]
    )


def test_phase_material_loads_against_the_draft_revise_program() -> None:
    fragment = _load(BASELINE)
    assert fragment["policy"] == PROGRAM_ID
    program = default_phase_program(PROGRAM_ID)
    assert tuple(program.phase_names()) == ("draft", "revise")
    specs = load_phase_material_specs(fragment, program)
    assert set(specs) == {"draft", "revise"}

    draft = specs["draft"]
    assert draft.instruction_template == "probes/%s" % DRAFT_TEMPLATE
    assert draft.instruction_fill is None
    assert draft.response_format_id is None
    assert draft.predecessor_binding == "none"
    assert draft.state_fill is None

    revise = specs["revise"]
    assert revise.instruction_template == "probes/%s" % REVISE_TEMPLATE
    assert revise.instruction_fill is None
    assert revise.response_format_id is None
    # THIS run's own draft, threaded by rails.phase_runner.run_program -- never
    # a sealed manifest of another run, and never gold.
    assert revise.predecessor_binding == "append-sealed-state"
    assert revise.predecessor_source is None
    # No per-sample fill: the control adds a contact and nothing else.
    assert revise.state_fill is None


def test_both_control_turns_are_short_directives_pinned_in_the_probe_manifest() -> None:
    manifest = _load(PROBE_MANIFEST)
    for name in (DRAFT_TEMPLATE, REVISE_TEMPLATE):
        path = CONFIGS / "probes" / name
        measured = hashlib.sha256(path.read_bytes()).hexdigest()
        assert manifest["templates"][name]["sha256"] == measured, name
        text = path.read_text(encoding="utf-8")
        # Short: a control turn that carried the ontology would collide with
        # the leakage rule (the KC-S1 finding) and would also stop being a
        # single-factor control.
        assert 0 < len(text) <= 600, name
        assert "{tool_schemas}" not in text
    entry = manifest["probes"]["SLURP-CONSUMPTION-KU-S1C"]
    assert entry["arms"]["draft_revise"] == [DRAFT_TEMPLATE, REVISE_TEMPLATE]
    assert entry["profile"] == "bounded-discovery-probe"
    assert manifest["samples"]["SLURP-CONSUMPTION-KU-S1C"]["receipt"] == "DEV-1000.json"


def test_the_bound_snapshot_excludes_the_content_dimension() -> None:
    fragment = _load(BASELINE)
    assert fragment["knowledge_snapshot_sha256"] == SNAPSHOT_SHA256
    assert fragment["knowledge_snapshot_relpath"].endswith(
        "size-full-label-prior-speaker/snapshot.json"
    )
    # The default size-full snapshot must not creep back in: its content facets
    # refuse 78 of the 1,000 phase-2 control turns (docs/checks/
    # speech-aware-evidence-acquisition/2026-09-05-slurp-consumption-ku-s1-v1/
    # containment-analysis.json).
    assert "size-full/snapshot.json" not in fragment["knowledge_snapshot_relpath"]


def test_the_cell_declares_no_serving_geometry_override() -> None:
    """The comparator's own geometry, unchanged.

    KC-S1b needed ``-np 4`` for per-slot context; this cell carries no
    per-sample block, so leaving the ``SlurpAdapter`` defaults keeps the
    contrast geometry-matched against the sealed closed-list arm.
    """

    fragment = _load(BASELINE)
    assert "serving_slots" not in fragment
    assert "serving_slot_tokens" not in fragment
    cell = _load(EXPERIMENT)["cells"][0]
    assert cell["model_fragment"].startswith("q4km-mmproj-free-speech-native-np8-")


def test_registered_plan_covers_two_passes_over_the_roster() -> None:
    experiment = _load(EXPERIMENT)
    plan = experiment["execution_plan"]
    assert experiment["experiment_id"] == "SAEA-SLURP-KU-S1C-DRAFT-REVISE-DEV1000-V1"
    assert plan["execution_profile"] == "bounded-discovery-probe"
    assert plan["split_role"] == "dev"
    # 1,000 rows x 2 phases, plus canaries.
    assert plan["planned_model_calls"] >= 2 * 1000 + 8
    # Two passes over DEV-1000's own 2,884.7936875 seconds.
    assert plan["planned_speech_audio_seconds"] >= 2 * 2884.7936875
    assert experiment["decision"] == {"test_tuning": False, "paper_scale": False}
    assert len(experiment["cells"]) == 1
    assert experiment["cells"][0]["baseline_fragment"] == BASELINE.stem


def test_the_smoke_fragment_names_its_four_rows_and_budgets_two_passes() -> None:
    smoke = _load(SMOKE)
    assert smoke["experiment_id"] == "SAEA-SLURP-KU-S1C-SMOKE-4-V1"
    assert smoke["cells"][0]["baseline_fragment"] == BASELINE.stem
    (population,) = smoke["populations"]
    assert len(population["ids"]) == 4
    assert len(set(population["ids"])) == 4
    assert all(sample_id.startswith("slurp:devel:") for sample_id in population["ids"])
    # 4 rows x 2 phases = 8 contacts, plus room for the one permitted recovery.
    assert smoke["execution_plan"]["planned_model_calls"] >= 8


def test_the_smoke_rows_are_dev1000_rows() -> None:
    view = _load(CONFIGS / "dataset" / "slurp-speech-native-dev1000.json")
    roster = {str(item["sample_id"]) for item in view["items"]}
    (population,) = _load(SMOKE)["populations"]
    assert set(population["ids"]) <= roster
