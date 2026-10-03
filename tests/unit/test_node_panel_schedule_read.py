"""Keep the whole scheduling comparison distinct from learning and partial reads."""
import copy

import pytest

from speech_aware_evidence_acquisition.rails.system_search_stage import recipe_family_identity
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError


def recipe():
    pairs = [f"{layout}-{schedule}-pair{pair}" for schedule in ("trajectory", "panel")
             for layout in ("legacy", "before-speech") for pair in (1, 2)]
    def run(label):
        return "SAEA-SLURP-NODE-PANEL-SCHEDULE-N20-" + label.upper() + "-V1"
    return {"schema": "saea-node-panel-schedule-analysis-v1", "rows_per_member": 20,
            "trajectory_cap": 320, "optimizer_export": False,
            "run_ids": {"read": "SAEA-SLURP-NODE-PANEL-SCHEDULE-N20-READ-V1"},
            "comparisons": [{"layout": p, "primary": run(p + "-primary"), "aa": run(p + "-aa")} for p in pairs],
            "complete_family": [run(p + "-" + r) for p in pairs for r in ("primary", "aa")]}


def test_exact_sixteen_member_schedule_read_has_no_learning_alias():
    family, members = recipe_family_identity(recipe())
    assert family == "node-panel-schedule-n20"
    assert len(members) == 16
    assert members["before-speech-panel-pair2-aa"].endswith("BEFORE-SPEECH-PANEL-PAIR2-AA-V1")
    assert not any(label.startswith(("L-", "B-")) for label in members)


@pytest.mark.parametrize("fault", ["read", "partial", "duplicate", "extra", "swapped-repeat", "learning", "alias", "stage", "rows", "budget"])
def test_schedule_read_refuses_partial_or_reinterpreted_families(fault):
    doc = recipe()
    if fault == "read":
        doc["run_ids"]["read"] = "OTHER-READ"
    elif fault == "partial":
        doc["complete_family"].pop()
    elif fault == "duplicate":
        doc["complete_family"][-1] = doc["complete_family"][0]
    elif fault == "extra":
        doc["comparisons"].append(copy.deepcopy(doc["comparisons"][0]))
    elif fault == "swapped-repeat":
        pair = doc["comparisons"][0]
        pair["primary"], pair["aa"] = pair["aa"], pair["primary"]
    elif fault == "learning":
        doc["optimizer_export"] = True
    elif fault == "alias":
        doc["family_id"] = "update-2"
    elif fault == "stage":
        doc["stage"] = "update-2"
    elif fault == "rows":
        doc["rows_per_member"] = 400
    else:
        doc["trajectory_cap"] = 160
    with pytest.raises(PolicyError):
        recipe_family_identity(doc)
