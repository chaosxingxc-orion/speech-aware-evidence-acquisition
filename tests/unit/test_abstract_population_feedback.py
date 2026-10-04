"""Reject content leakage and broken pairing before batch template reflection."""
from copy import deepcopy
import json
import pytest
from speech_aware_evidence_acquisition.analysis.abstract_node_feedback import (
    abstract_episode, abstract_population_feedback,
)

def fixture():
    bundles = {f"branch-{i:02d}": f"{i:064x}" for i in range(1, 17)}
    templates = []
    for i, (cid, bundle) in enumerate(bundles.items()):
        rows = []
        for j in range(2):
            counts = {f"slu_f1_{axis}_{kind}": value
                      for axis in ("word", "char")
                      for kind, value in (("tp", 1), ("fp", i if j else 0), ("fn", 0))}
            counts["scenario_action_exact"] = 1
            row = abstract_episode(
                [{"role": "planner", "visit": 0, "interrupted": False,
                  "text": "ACCEPT", "measurements": {"input_tokens": 5}}],
                counts=counts, reference_f1=.5, reliable=True, abstained=False,
                elapsed_seconds=1.0)
            rows.append({"input_index": j, **row})
        templates.append({"candidate_id": cid, "bundle_id": bundle,
                          "official_summary": {"slu_f1": 60., "intent": 80.},
                          "samples": rows})
    source = {"source_batch": "own-complete", "family_id": "family",
              "reference_f1": .5, "templates": templates}
    args = dict(expected_bundles=bundles, expected_family_id="family",
                expected_source_batch="own-complete", sample_count=2, reference_f1=.5)
    return source, args

def test_complete_population_preserves_pairing_and_zero_variation():
    source, args = fixture()
    before = deepcopy(source)
    result = abstract_population_feedback(source, **args)
    assert source == before
    assert len(result["groups"]) == 2
    assert len(result["groups"][0]["members"]) == 16
    assert all(m["relative_return"] == 0 for m in result["groups"][0]["members"])
    returns = [m["relative_return"] for m in result["groups"][1]["members"]]
    assert returns[0] > returns[-1] and abs(sum(returns)) < 1e-12
    assert result["groups"][1]["members"][-1]["terminal"]["utility"] == -13
    assert result["templates"][0]["official_summary"] == source["templates"][0]["official_summary"]
    assert result["runtime_admission"] is False
    assert result["groups"][0]["members"][0]["nodes"][0][4][-1] is None
    result["groups"][0]["members"][0]["terminal"]["reliable"] = False
    assert source == before

@pytest.mark.parametrize("path,value", [
    (["private"], "PRIVATE_CASE"),
    (["family_id"], "other-family"),
    (["source_batch"], "another-cohort"),
    (["reference_f1"], .6),
    (["templates", 0, "bundle_id"], "0" * 64),
    (["templates", 0, "candidate_id"], "branch-02"),
    (["templates", 0, "official_summary", "reason"], "PRIVATE_CASE"),
    (["templates", 0, "official_summary", "intent"], float("nan")),
    (["templates", 0, "samples", 0, "input_index"], 1),
    (["templates", 0, "samples", 0, "reason"], "PRIVATE_CASE"),
    (["templates", 0, "samples", 0, "nodes", 0, 0], 4),
    (["templates", 0, "samples", 0, "nodes", 0, 1], -1),
    (["templates", 0, "samples", 0, "nodes", 0, 2], "false"),
    (["templates", 0, "samples", 0, "nodes", 0, 3], [True, "PRIVATE_CASE"]),
    (["templates", 0, "samples", 0, "nodes", 0, 4, 0], float("inf")),
    (["templates", 0, "samples", 0, "nodes", 0, 4, 7], .5),
    (["templates", 0, "samples", 0, "missing_roles"], []),
    (["templates", 0, "samples", 0, "terminal", "utility"], 999),
    (["templates", 0, "samples", 0, "terminal", "sample_seconds"], -1),
    (["templates", 0, "samples", 0, "terminal", "official_aggregate_f1"], 1),
    (["templates", 0, "samples", 0, "terminal", "reliable"], 1),
    (["templates", 0, "samples", 0, "terminal", "intent_correct"], 0),
    (["templates", 0, "samples", 0, "terminal", "official_counts", "private"], "PRIVATE_CASE"),
])
def test_reject_bad_content_or_binding(path, value):
    source, args = fixture()
    target = source
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValueError):
        abstract_population_feedback(source, **args)

@pytest.mark.parametrize("target", ["templates", "samples", "nodes", "counts"])
def test_reject_incomplete_population_or_episode(target):
    source, args = fixture()
    if target == "templates":
        source["templates"].pop()
    elif target == "samples":
        source["templates"][0]["samples"].pop()
    elif target == "nodes":
        source["templates"][0]["samples"][0]["nodes"] = []
    else:
        source["templates"][0]["samples"][0]["terminal"]["official_counts"].pop("slu_f1_word_tp")
    with pytest.raises(ValueError):
        abstract_population_feedback(source, **args)

def test_structural_all_roles_and_unavailable_outputs():
    source, args = fixture()
    rows = [
        [0, 0, False, [True, 1, 0, 1], [None] * 8],
        [1, 1, False, [True, 1, 1, None, None, None, None], [None] * 8],
        [2, 2, True, [False] + [None] * 7, [None] * 8],
        [3, 3, False, [False, 2], [None] * 8],
    ]
    sample = source["templates"][0]["samples"][0]
    sample["nodes"], sample["missing_roles"] = rows, []
    assert len(abstract_population_feedback(source, **args)["groups"][0]["members"][0]["nodes"]) == 4
    rows[2][3][1] = 1
    with pytest.raises(ValueError):
        abstract_population_feedback(source, **args)

@pytest.mark.parametrize("change", ["bad_bundles", "bad_n", "bad_reference", "negative_visit_order", "count_bool"])
def test_reject_invalid_contract_and_numeric_shapes(change):
    source, args = fixture()
    sample = source["templates"][0]["samples"][0]
    if change == "bad_bundles":
        args["expected_bundles"] = {}
    elif change == "bad_n":
        args["sample_count"] = True
    elif change == "bad_reference":
        args["reference_f1"] = float("nan")
    elif change == "count_bool":
        sample["terminal"]["official_counts"]["slu_f1_word_tp"] = True
    else:
        sample["nodes"] = [[3, 1, False, [True, 0], [None]*8],
                           [3, 0, False, [True, 0], [None]*8]]
    with pytest.raises(ValueError):
        abstract_population_feedback(source, **args)

def test_official_fractional_counts_and_float_binary_flags_are_preserved():
    source, args = fixture()
    terminal = source["templates"][0]["samples"][0]["terminal"]
    terminal["official_counts"]["slu_f1_word_fp"] = .25
    terminal["official_counts"]["scenario_action_exact"] = 1.0
    terminal["intent_correct"] = 1.0
    terminal["utility"] = 1.875
    out = abstract_population_feedback(source, **args)
    assert out["groups"][0]["members"][0]["terminal"]["official_counts"]["slu_f1_word_fp"] == .25
