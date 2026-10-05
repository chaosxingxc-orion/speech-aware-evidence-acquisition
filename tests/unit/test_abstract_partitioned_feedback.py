"""Keep both original K8 cohorts complete and normalize only within each cohort."""
from copy import deepcopy
from test_experiment_population_config import config
from speech_aware_evidence_acquisition.rails.hashing import content_hash
import pytest

from speech_aware_evidence_acquisition.analysis.abstract_node_feedback import (
    abstract_episode, abstract_partitioned_population_feedback, abstract_population_feedback,
)


def fixture():
    sources, expected = {}, {}
    for panel, first in (("k8a", 1), ("k8b", 9)):
        bundles = {f"branch-{i:02d}": f"{i:064x}" for i in range(first, first + 8)}
        templates = []
        for rank, (cid, bundle) in enumerate(bundles.items()):
            samples = []
            for index in range(2):
                # Large cross-panel shift must not affect within-panel returns.
                counts = {f"slu_f1_{axis}_{kind}": value for axis in ("word", "char")
                          for kind, value in (("tp", 100 if panel == "k8b" else 1),
                                              ("fp", rank if index else 0), ("fn", 0))}
                counts["scenario_action_exact"] = 1
                episode = abstract_episode(
                    [{"role": "planner", "visit": 0, "interrupted": False,
                      "text": "ACCEPT", "measurements": {"input_tokens": 7}}],
                    counts=counts, reference_f1=.5, reliable=True, abstained=False,
                    elapsed_seconds=1.)
                samples.append({"input_index": index, **episode})
            templates.append({"candidate_id": cid, "bundle_id": bundle,
                              "official_summary": {"slu_f1": 50., "intent": 100.},
                              "samples": samples})
        sources[panel] = {"source_batch": panel + "-batch", "family_id": panel + "-family",
                          "reference_f1": .5, "templates": templates,
                          "sample_order_sha256": content_hash([f"slurp:train:{i}" for i in range(2)])}
        expected[panel] = {"expected_bundles": bundles,
                           "expected_family_id": panel + "-family",
                           "expected_source_batch": panel + "-batch",
                           "reference_f1": .5, "sample_order_sha256": content_hash([f"slurp:train:{i}" for i in range(2)])}
    return sources, expected


def population_config():
    value = config((8, 8), 2)
    for c, panel, first in zip(value["cohorts"], ("k8a", "k8b"), (1, 9)):
        c["cohort_id"] = panel
        c["candidate_ids"] = [f"branch-{i:02d}" for i in range(first, first+8)]
    return value


def test_complete_two_panels_preserve_cohorts_without_cross_panel_normalization():
    sources, expected = fixture()
    before = deepcopy(sources)
    result = abstract_partitioned_population_feedback(
        sources, expected_partitions=expected, population_config=population_config())
    assert sources == before
    assert set(result["cohorts"]) == {"k8a", "k8b"}
    assert "groups" not in result and "frontier" not in result
    assert result["runtime_admission"] is False
    values = []
    for panel in ("k8a", "k8b"):
        cohort = result["cohorts"][panel]
        assert cohort["family_id"] == expected[panel]["expected_family_id"]
        assert cohort["source_batch"] == expected[panel]["expected_source_batch"]
        assert len(cohort["groups"][0]["members"]) == 8
        assert all(m["relative_return"] == 0 for m in cohort["groups"][0]["members"])
        values.append([m["relative_return"] for m in cohort["groups"][1]["members"]])
        assert abs(sum(values[-1])) < 1e-12
    assert values[0] == values[1]
    result["cohorts"]["k8a"]["groups"][0]["members"][0]["terminal"]["reliable"] = False
    assert sources == before


@pytest.mark.parametrize("defect", [
    "missing_panel", "extra_panel", "missing_contract", "wrong_ids", "missing_candidate",
    "duplicate_candidate", "same_family", "same_batch", "changed_reference", "wrong_order",
    "changed_roster", "bad_roster_hash", "content_leak", "unmeasured_node_quality",
    "bad_utility", "missing_sample", "extra_contract_field",
])
def test_refuse_incomplete_mixed_or_contaminated_partitions(defect):
    sources, expected = fixture()
    s, e = sources["k8b"], expected["k8b"]
    if defect == "missing_panel": sources.pop("k8b")
    elif defect == "extra_panel": sources["extra"] = deepcopy(s)
    elif defect == "missing_contract": expected.pop("k8b")
    elif defect == "wrong_ids": e["expected_bundles"] = expected["k8a"]["expected_bundles"]
    elif defect == "missing_candidate": s["templates"].pop()
    elif defect == "duplicate_candidate": s["templates"][-1] = deepcopy(s["templates"][0])
    elif defect == "same_family": s["family_id"] = e["expected_family_id"] = "k8a-family"
    elif defect == "same_batch": s["source_batch"] = e["expected_source_batch"] = "k8a-batch"
    elif defect == "changed_reference": s["reference_f1"] = e["reference_f1"] = .6
    elif defect == "wrong_order": s["templates"].reverse()
    elif defect == "changed_roster": s["sample_order_sha256"] = e["sample_order_sha256"] = "b" * 64
    elif defect == "bad_roster_hash": s["sample_order_sha256"] = e["sample_order_sha256"] = "private-roster"
    elif defect == "content_leak": s["templates"][0]["samples"][0]["utterance"] = "PRIVATE"
    elif defect == "unmeasured_node_quality": s["templates"][0]["samples"][0]["nodes"][0][4][-1] = .9
    elif defect == "bad_utility": s["templates"][0]["samples"][0]["terminal"]["utility"] = 999
    elif defect == "missing_sample": s["templates"][0]["samples"].pop()
    else: e["extra"] = "PRIVATE"
    with pytest.raises(ValueError):
        abstract_partitioned_population_feedback(sources, expected_partitions=expected, population_config=population_config())


def test_single_cohort_refuses_a_subset_of_configured_members():
    sources, expected = fixture()
    source, args = deepcopy(sources["k8a"]), deepcopy(expected["k8a"])
    source.pop("sample_order_sha256")
    args.pop("sample_order_sha256")
    args["expected_bundles"].update(expected["k8b"]["expected_bundles"])
    with pytest.raises(ValueError, match="original cohort"):
        abstract_population_feedback(source, sample_count=2, **args)


def test_asymmetric_configured_cohorts_have_no_eight_candidate_assumption():
    sources, expected = fixture()
    configured = population_config()
    for old, new, size, cohort in zip(("k8a", "k8b"), ("first", "second"), (3, 5), configured["cohorts"]):
        sources[new] = sources.pop(old)
        expected[new] = expected.pop(old)
        cohort["cohort_id"] = new
        cohort["candidate_ids"] = cohort["candidate_ids"][:size]
        sources[new]["templates"] = sources[new]["templates"][:size]
        expected[new]["expected_bundles"] = {c:expected[new]["expected_bundles"][c] for c in cohort["candidate_ids"]}
    result = abstract_partitioned_population_feedback(sources, expected_partitions=expected, population_config=configured)
    assert [len(c["groups"][0]["members"]) for c in result["cohorts"].values()] == [3, 5]
