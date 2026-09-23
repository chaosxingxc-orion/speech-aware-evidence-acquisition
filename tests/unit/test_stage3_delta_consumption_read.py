"""Tests for the Stage-3 per-node delta-consumption read (item S3-4s, owner decision 99).

Everything here runs against SYNTHETIC fixtures under ``tmp_path``: a four-row sealed run tree in
exactly the shape the CELL-1 flight seals (run manifest, flight receipts carrying the
named-knowledge-store routing receipt with its ``delta_supply`` skip audits and
``delta_candidate_projection`` audits, a phase artefact whose waves carry the per-node transitions,
and a score file), plus a comparator run and a roster-metadata file. No real ``SPEECHRL_DATA_DIR``
byte is read and the driver is never pointed at the real data root.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DRIVER_PATH = REPO_ROOT / "scripts" / "analysis" / "stage3_delta_consumption_read.py"

_SPEC = importlib.util.spec_from_file_location("stage3_delta_consumption_read", DRIVER_PATH)
drv = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = drv
_SPEC.loader.exec_module(drv)


#: Text that must never leave the flight artefacts: the read is counts, ids and hashes only.
SENTINEL = "SENTINEL-DELTA-STATEMENT-TEXT-4f91ab"

POLICY = "phase-test-native-v1"
STORE = "stage3-deltas"
RUN = "SAEA-TEST-DELTA-CELL-V1"
ATTEMPT = "attempt-test-delta-cell-v1-generation"
COMPARATOR_RUN = "SAEA-TEST-PLAN-V1"
COMPARATOR_ATTEMPT = "attempt-test-plan-v1-generation"
SCORER = "slurp-slu-official-train"
SPLIT_HASH = "0" * 64
ROSTER_METADATA = "analysis/TEST-ROSTER/roster-metadata.json"

ROWS = ["s:1", "s:2", "s:3", "s:4"]
SCENARIOS = {"s:1": "alarm", "s:2": "alarm", "s:3": "audio", "s:4": "audio"}

#: comparator per-row official values, then the arm's. r1 improves, r2 regresses, r3/r4 tie.
COMPARATOR_SCORES = {
    "s:1": {"slu_f1_f1": 0.50, "scenario_action_exact": 0.0},
    "s:2": {"slu_f1_f1": 0.60, "scenario_action_exact": 1.0},
    "s:3": {"slu_f1_f1": 0.70, "scenario_action_exact": 1.0},
    "s:4": {"slu_f1_f1": 0.40, "scenario_action_exact": 0.0},
}
ARM_SCORES = {
    "s:1": {"slu_f1_f1": 0.70, "scenario_action_exact": 1.0},
    "s:2": {"slu_f1_f1": 0.50, "scenario_action_exact": 0.0},
    "s:3": {"slu_f1_f1": 0.70, "scenario_action_exact": 1.0},
    "s:4": {"slu_f1_f1": 0.40, "scenario_action_exact": 0.0},
}


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )


def _qualified(value_id: str) -> str:
    return f"{STORE}::{value_id}"


def _transition(*, refs, new_value_ids, action_kind="acquire") -> dict:
    return {
        "action_kind": action_kind,
        "action_target_refs": list(refs),
        "new_facet_ids": [],
        "new_value_ids": list(new_value_ids),
        "transition_version": "1",
    }


def _wave(sample_id: str, role: str, index: int, transition) -> dict:
    return {
        "batch_id": f"{POLICY}:{role}:0:{sample_id}",
        "wave_index": index,
        "transition": transition,
    }


def _contact_ref(sample_id: str, role: str) -> str:
    return f"{POLICY}:{role}:{POLICY}:{role}:0:{sample_id}"


COMPOSITE = "source-scoped-context-composite-v1"


def _node_ref(node: str, cap: int) -> str:
    return f"knowledge-store:{STORE}:stage3-delta-candidate-bound-v1:node={node}:cap={cap}"


def _result(sample_id: str, waves) -> dict:
    return {
        "sample_id": sample_id,
        # the unconditional first-phase seed: two deltas beside a sibling store's values
        "initial_query_state": {
            "retrieved_value_ids": [
                "intent-boundaries::b0",
                _qualified("d0"),
                _qualified("d1"),
            ],
            "visible_facet_ids": [],
        },
        "waves": waves,
        "transitions": [wave["transition"] for wave in waves],
        # heavy, text-bearing fields the read must never open
        "final_response_text": SENTINEL,
        "consumption": {"records": [{"evidence": SENTINEL}]},
    }


def _build_rows() -> list:
    results = []
    # row 1: the solver is fed through the COMPOSITE ref (three supplies compose there), the
    # reviewer through the store's own node ref, and the planner takes nothing.
    results.append(
        _result(
            "s:1",
            [
                _wave("s:1", "perception", 0, _transition(
                    refs=[_contact_ref("s:1", "perception"), COMPOSITE],
                    new_value_ids=["train-exemplars::v1", _qualified("d2"), _qualified("d3")],
                )),
                _wave("s:1", "solver", 1, _transition(
                    refs=[_contact_ref("s:1", "solver"), _node_ref("reviewer", 4)],
                    new_value_ids=[_qualified("d4")],
                )),
                _wave("s:1", "reviewer", 2, _transition(
                    refs=[_contact_ref("s:1", "reviewer")], new_value_ids=[]
                )),
                _wave("s:1", "planner", 3, _transition(
                    refs=[_contact_ref("s:1", "planner")],
                    new_value_ids=[],
                    action_kind="organize",
                )),
            ],
        )
    )
    # row 2: the solver route skips, the reviewer and the planner both take one delta.
    results.append(
        _result(
            "s:2",
            [
                _wave("s:2", "perception", 0, _transition(
                    refs=[_contact_ref("s:2", "perception"), COMPOSITE],
                    new_value_ids=["train-exemplars::v2"],
                )),
                _wave("s:2", "solver", 1, _transition(
                    refs=[_contact_ref("s:2", "solver"), _node_ref("reviewer", 4)],
                    new_value_ids=[_qualified("d4")],
                )),
                _wave("s:2", "reviewer", 2, _transition(
                    refs=[_contact_ref("s:2", "reviewer"), _node_ref("planner", 4)],
                    new_value_ids=[_qualified("d5")],
                )),
                _wave("s:2", "planner", 3, _transition(
                    refs=[_contact_ref("s:2", "planner")],
                    new_value_ids=[],
                    action_kind="organize",
                )),
            ],
        )
    )
    # row 3: every candidate-bound route skips; only the unconditional seed reaches it.
    results.append(
        _result(
            "s:3",
            [
                _wave("s:3", "perception", 0, _transition(
                    refs=[_contact_ref("s:3", "perception"), COMPOSITE],
                    new_value_ids=["train-exemplars::v3"],
                )),
                _wave("s:3", "solver", 1, _transition(
                    refs=[_contact_ref("s:3", "solver")], new_value_ids=[]
                )),
            ],
        )
    )
    # row 4: the solver is fed through the store's OWN node ref (a cap the receipt names).
    results.append(
        _result(
            "s:4",
            [
                _wave("s:4", "perception", 0, _transition(
                    refs=[_contact_ref("s:4", "perception"), _node_ref("solver", 8)],
                    new_value_ids=[_qualified("d2")],
                )),
                _wave("s:4", "solver", 1, _transition(
                    refs=[_contact_ref("s:4", "solver")], new_value_ids=[]
                )),
                _wave("s:4", "reviewer", 2, _transition(
                    refs=[_contact_ref("s:4", "reviewer")], new_value_ids=[]
                )),
                _wave("s:4", "planner", 3, _transition(
                    refs=[_contact_ref("s:4", "planner")],
                    new_value_ids=[],
                    action_kind="organize",
                )),
            ],
        )
    )
    return results


SKIPS = [
    ("solver", "s:2", 0, "no delta of this node slice matches the row candidates"),
    ("solver", "s:3", 0, "no delta of this node slice matches the row candidates"),
    ("reviewer", "s:3", 0, "no delta of this node slice matches the row candidates"),
    ("reviewer", "s:4", 2, "every ranked delta of this node slice is already acquired in this episode"),
    ("planner", "s:1", 0, "no delta of this node slice matches the row candidates"),
    ("planner", "s:3", 0, "no delta of this node slice matches the row candidates"),
    ("planner", "s:4", 0, "no delta of this node slice matches the row candidates"),
]


def _scores_document(rows: dict) -> dict:
    return {
        SCORER: {
            "aggregate": {"slu_f1": 60.0},
            "per_sample": [
                {"sample_id": sample_id, **values} for sample_id, values in sorted(rows.items())
            ],
        }
    }


def _seal_run(data_root: Path, run_id: str, attempt_id: str, *, results, scores, with_projection):
    directory = data_root / "runs" / run_id / attempt_id
    _write(
        directory / f"{run_id}.run-manifest.json",
        {
            "run_id": run_id,
            "status": "COMPLETED",
            "study_commit": "deadbeef",
            "study_repo_dirt": [],
            "split": {"identity_hash": SPLIT_HASH, "role": "discovery", "count": len(ROWS)},
            "scores": None,
        },
    )
    receipt_supply = {
        "schema": "saea-named-knowledge-store-routing-v1",
        "binding_sha256": "b" * 64,
        "stores": {
            STORE: {
                "store_id": STORE,
                "store_role": "stage3-deltas",
                "store_release_sha256": "r" * 64,
                "store_snapshot_sha256": "s" * 64,
                "store_source_sha256": "o" * 64,
                "composite_snapshot_sha256": "c" * 64,
                "context_supply": ["perception", "planner", "reviewer", "solver"],
                "unconditional_context_supply": {
                    "provider": "stage3-delta-unconditional-v1",
                    "node_target": "perception",
                    "phase": "perception",
                    "cap": 2,
                    "selected_value_ids": [_qualified("d0"), _qualified("d1")],
                },
            },
            "train-exemplars": {"store_id": "train-exemplars", "store_role": "exemplars"},
        },
        "delta_supply": {
            f"{node}:{sample_id}:{'q' * 64}": {
                "node": node,
                "phase": node,
                "sample_id": sample_id,
                "store_id": STORE,
                "selected": 0,
                "already_acquired": already,
                "reason": reason,
            }
            for node, sample_id, already, reason in SKIPS
        },
    }
    if with_projection:
        receipt_supply["delta_candidate_projection"] = {
            f"perception:s:1:{'p' * 64}": {
                "node": "solver",
                "phase": "solver",
                "sample_id": "s:1",
                "store_id": STORE,
                "raw_positions": 3,
                "retained_positions": 2,
                "projection_policy_id": "bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1",
                "projection_policy_sha256": "a" * 64,
                "original_text_sha256": "t" * 64,
                "projected_content_sha256": "u" * 64,
            }
        }
    _write(
        directory / "flight-receipts.json",
        {
            "attempt_id": attempt_id,
            "run_id": run_id,
            "schema": "saea-flight-receipts-v1",
            "receipts_hash": "h" * 64,
            "stages": {"run_phases": {"phase_supply": receipt_supply}},
        },
    )
    _write(
        directory / f"{run_id}.phases.json",
        {
            "schema": "saea-flight-phase-summaries-v1",
            "run_id": run_id,
            "attempt_id": attempt_id,
            "policy": POLICY,
            "phases": [
                {
                    "run_id": run_id,
                    "controller_policy_id": POLICY,
                    "agent_executor_id": "test-executor",
                    "knowledge_snapshot_sha256": "k" * 64,
                    "protocol_hash": "p" * 64,
                    "results": results,
                }
            ],
        },
    )
    if scores is not None:
        _write(directory / f"{run_id}.scores.json", _scores_document(scores))
    return directory


@pytest.fixture()
def sealed(tmp_path, monkeypatch):
    data_root = tmp_path / "data"
    monkeypatch.setattr(drv, "DATA", data_root)
    _seal_run(
        data_root, RUN, ATTEMPT, results=_build_rows(), scores=ARM_SCORES, with_projection=True
    )
    _seal_run(
        data_root,
        COMPARATOR_RUN,
        COMPARATOR_ATTEMPT,
        results=_build_rows(),
        scores=COMPARATOR_SCORES,
        with_projection=False,
    )
    _write(
        data_root / ROSTER_METADATA,
        {"rows": {sample_id: {"scenario": scenario} for sample_id, scenario in SCENARIOS.items()}},
    )
    config = tmp_path / "baseline.json"
    _write(
        config,
        {
            "knowledge_stores": {
                STORE: {
                    "store_role": "stage3-deltas",
                    "release": {"relpath": "knowledge/x/release.json", "sha256": "r" * 64},
                    "snapshot": {"relpath": "knowledge/x/snapshot.json", "sha256": "s" * 64},
                    "context_supply": {
                        "perception": {
                            "provider": "stage3-delta-unconditional-v1",
                            "node_target": "perception",
                            "cap": 2,
                            "rank_by": "prior_score",
                        },
                        "solver": {
                            "provider": "stage3-delta-candidate-bound-v1",
                            "node_target": "solver",
                            "candidate_state_phase": "perception",
                            "cap": 8,
                            "rank_by": "prior_score",
                        },
                        "reviewer": {
                            "provider": "stage3-delta-candidate-bound-v1",
                            "node_target": "reviewer",
                            "candidate_state_phase": "perception",
                            "cap": 4,
                            "rank_by": "prior_score",
                        },
                        "planner": {
                            "provider": "stage3-delta-candidate-bound-v1",
                            "node_target": "planner",
                            "candidate_state_phase": "perception",
                            "cap": 4,
                            "rank_by": "prior_score",
                        },
                    },
                }
            }
        },
    )
    return {"data_root": data_root, "config": config, "out": tmp_path / "out"}


def _run(sealed, *extra):
    argv = [
        "--run", RUN,
        "--attempt", ATTEMPT,
        "--analysis-root", str(sealed["out"]),
        "--roster-metadata", ROSTER_METADATA,
        "--baseline-config", str(sealed["config"]),
        *extra,
    ]
    assert drv.main(argv) == 0
    return json.loads((sealed["out"] / "delta-consumption.json").read_text(encoding="utf-8"))


def _run_joined(sealed, *extra):
    return _run(
        sealed,
        "--comparator-run", COMPARATOR_RUN,
        "--comparator-attempt", COMPARATOR_ATTEMPT,
        *extra,
    )


# --------------------------------------------------------------------------
# The supply extraction
# --------------------------------------------------------------------------

def test_per_node_counts_bind_the_sealed_transitions(sealed):
    payload = _run_joined(sealed)
    nodes = payload["consumption"]["per_node"]
    # the unconditional first-phase seed reaches every row, at its full cap
    assert nodes["perception"]["rows_supplied"] == 4
    assert nodes["perception"]["items_supplied_total"] == 8
    assert nodes["perception"]["distinct_value_ids"] == 2
    assert nodes["perception"]["cap"] == 2
    assert nodes["perception"]["rows_at_full_cap"] == 4
    # the solver is fed once through the COMPOSITE ref (row 1) and once through the store's
    # own node ref (row 4): both must be attributed to the solver
    assert nodes["solver"]["rows_supplied"] == 2
    assert nodes["solver"]["items_supplied_total"] == 3
    assert sorted(nodes["solver"]["distinct_value_id_list"]) == [
        f"{STORE}::d2", f"{STORE}::d3"
    ]
    assert nodes["solver"]["cap"] == 8
    assert nodes["reviewer"]["rows_supplied"] == 2
    assert nodes["reviewer"]["items_supplied_total"] == 2
    assert nodes["planner"]["rows_supplied"] == 1
    assert nodes["planner"]["items_supplied_total"] == 1
    assert payload["consumption"]["summary"]["items_supplied_total"] == 14
    assert payload["consumption"]["summary"]["distinct_value_ids_supplied"] == 6
    assert payload["consumption"]["summary"]["rows_supplied_any_node"] == 4
    assert payload["consumption"]["summary"]["inert_routes"] == []
    assert payload["attribution_audit"]["unattributed_supplied_items"] == 0
    assert payload["attribution_audit"]["node_label_disagreements"] == []


def test_node_order_is_the_role_graph_order(sealed):
    payload = _run(sealed)
    assert payload["consumption"]["node_order"] == [
        "perception", "solver", "reviewer", "planner"
    ]


def test_declared_caps_and_pins_are_checked_against_the_flight_receipt(sealed):
    payload = _run(sealed)
    audit = payload["attribution_audit"]
    assert audit["declared_release_matches_the_flight_receipt"] is True
    assert audit["declared_snapshot_matches_the_flight_receipt"] is True
    assert audit["cap_disagreements"] == []
    # the receipt itself only names the caps of the routes that served a node ALONE
    assert audit["caps_from_refs"] == {"reviewer": 4, "planner": 4, "solver": 8}


def test_a_cap_disagreement_between_the_config_and_the_flight_is_reported(sealed, tmp_path):
    config = json.loads(sealed["config"].read_text(encoding="utf-8"))
    config["knowledge_stores"][STORE]["context_supply"]["reviewer"]["cap"] = 9
    other = tmp_path / "baseline-moved.json"
    _write(other, config)
    payload = _run(sealed, "--baseline-config", str(other))
    assert payload["attribution_audit"]["cap_disagreements"] == [
        {"node": "reviewer", "flown_cap": 4, "declared_cap": 9}
    ]


# --------------------------------------------------------------------------
# Skips and projections
# --------------------------------------------------------------------------

def test_skip_receipts_are_counted_by_node_and_by_reason(sealed):
    payload = _run(sealed)
    nodes = payload["consumption"]["per_node"]
    assert payload["consumption"]["summary"]["skip_events"] == 7
    assert nodes["solver"]["skips"]["skip_events"] == 2
    assert nodes["solver"]["skips"]["rows_skipped"] == 2
    assert nodes["reviewer"]["skips"]["skip_events"] == 2
    assert nodes["reviewer"]["skips"]["already_acquired_total"] == 2
    assert nodes["reviewer"]["skips"]["already_acquired_events"] == 1
    assert nodes["planner"]["skips"]["skip_events"] == 3
    assert nodes["perception"]["skips"]["skip_events"] == 0
    reasons = nodes["reviewer"]["skips"]["reasons"]
    assert sum(reasons.values()) == 2
    assert any("already acquired" in reason for reason in reasons)


def test_projection_events_are_counted(sealed):
    payload = _run(sealed)
    projection = payload["consumption"]["projection"]
    assert projection["published"] is True
    assert projection["events"] == 1
    assert projection["rows"] == 1
    assert projection["positions_dropped"] == 1
    assert projection["by_node"] == {"solver": 1}


def test_a_receipt_without_the_projection_key_is_reported_not_refused(sealed):
    payload = _run(
        sealed,
        "--run", COMPARATOR_RUN,
        "--attempt", COMPARATOR_ATTEMPT,
    )
    projection = payload["consumption"]["projection"]
    assert projection["published"] is False
    assert projection["events"] == 0
    assert "predates" in projection["note"]


# --------------------------------------------------------------------------
# The paired join
# --------------------------------------------------------------------------

def test_per_value_outcomes_are_the_paired_rows_that_value_reached(sealed):
    payload = _run_joined(sealed)
    values = payload["consumption"]["per_value_id"]
    # d4 reached rows 1 and 2: one save and one harm on both metrics
    d4 = values[f"{STORE}::d4"]
    assert d4["nodes"] == ["reviewer"]
    assert d4["rows_reached"] == 2
    assert d4["outcome"]["slu_f1"] == {
        "saves": 1, "harms": 1, "neutral": 0, "mean_delta_pp": pytest.approx(5.0)
    }
    assert d4["outcome"]["intent"] == {
        "saves": 1, "harms": 1, "neutral": 0, "mean_delta_pp": pytest.approx(0.0)
    }
    # d3 reached row 1 alone: one save
    d3 = values[f"{STORE}::d3"]
    assert d3["rows_reached"] == 1
    assert d3["outcome"]["slu_f1"]["saves"] == 1
    assert d3["outcome"]["slu_f1"]["mean_delta_pp"] == pytest.approx(20.0)
    # d2 reached rows 1 and 4 (composite ref and node ref): one save, one tie
    d2 = values[f"{STORE}::d2"]
    assert d2["rows_reached"] == 2
    assert d2["outcome"]["slu_f1"]["neutral"] == 1
    assert d2["outcome"]["slu_f1"]["mean_delta_pp"] == pytest.approx(10.0)


def test_per_node_outcome_is_restricted_to_the_rows_that_node_supplied(sealed):
    payload = _run_joined(sealed)
    solver = payload["consumption"]["per_node"]["solver"]["outcome_on_supplied_rows"]
    assert solver["rows_joined"] == 2
    assert solver["slu_f1"]["saves"] == 1
    assert solver["slu_f1"]["neutral"] == 1
    assert solver["slu_f1"]["mean_delta_pp"] == pytest.approx(10.0)


def test_per_scenario_aggregates_both_supply_and_outcome(sealed):
    payload = _run_joined(sealed)
    scenarios = payload["consumption"]["per_scenario"]
    assert set(scenarios) == {"alarm", "audio"}
    assert scenarios["alarm"]["rows_total"] == 2
    assert scenarios["alarm"]["nodes"]["reviewer"]["rows_supplied"] == 2
    assert scenarios["alarm"]["nodes"]["planner"]["rows_supplied"] == 1
    assert scenarios["audio"]["nodes"]["solver"]["rows_supplied"] == 1
    assert scenarios["audio"]["nodes"]["reviewer"]["rows_supplied"] == 0
    # audio rows tie on both metrics, so every delta there is neutral
    assert scenarios["audio"]["outcome_on_supplied_rows"]["slu_f1"]["neutral"] == 2


def test_without_a_comparator_the_read_still_reports_supply(sealed):
    payload = _run(sealed)
    assert payload["consumption"]["summary"]["score_join"] == "not available"
    assert payload["comparator"] is None
    assert "outcome" not in payload["consumption"]["per_value_id"][f"{STORE}::d4"]
    assert payload["consumption"]["per_node"]["solver"]["rows_supplied"] == 2


# --------------------------------------------------------------------------
# A REVISE revisit (the seven-wave trajectory the real flight carries)
# --------------------------------------------------------------------------

def test_a_revise_revisit_accumulates_under_the_same_node(tmp_path, monkeypatch):
    """A Planner REVISE sends the episode back to the Solver, so a role is VISITED TWICE.

    Cell PLAN's own sealed trajectory carries such rows (contacts-per-row histogram 4 and 7), so
    the node attribution must aggregate a role's repeated visits under that one node rather than
    inventing a node or dropping the second supply.
    """

    data_root = tmp_path / "data"
    monkeypatch.setattr(drv, "DATA", data_root)
    sample_id = "s:9"
    order = [
        ("perception", [_contact_ref(sample_id, "perception"), COMPOSITE], [_qualified("d2")]),
        ("solver", [_contact_ref(sample_id, "solver"), _node_ref("reviewer", 4)],
         [_qualified("d4")]),
        ("reviewer", [_contact_ref(sample_id, "reviewer"), _node_ref("planner", 4)],
         [_qualified("d5")]),
        # the Planner answers REVISE: the episode returns to the Solver, supplying nothing
        ("planner", [_contact_ref(sample_id, "planner"), COMPOSITE], []),
        # the SECOND Solver visit feeds the SECOND Reviewer visit
        ("solver", [_contact_ref(sample_id, "solver"), _node_ref("reviewer", 4)],
         [_qualified("d6")]),
        ("reviewer", [_contact_ref(sample_id, "reviewer"), _node_ref("planner", 4)], []),
        ("planner", [_contact_ref(sample_id, "planner")], []),
    ]
    waves = [
        _wave(sample_id, role, index, _transition(refs=refs, new_value_ids=new))
        for index, (role, refs, new) in enumerate(order)
    ]
    _seal_run(
        data_root,
        RUN,
        ATTEMPT,
        results=[_result(sample_id, waves)],
        scores=None,
        with_projection=False,
    )
    out = tmp_path / "out"
    assert drv.main([
        "--run", RUN, "--attempt", ATTEMPT, "--analysis-root", str(out),
        "--roster-metadata", "analysis/ABSENT/roster-metadata.json",
    ]) == 0
    nodes = json.loads((out / "delta-consumption.json").read_text(encoding="utf-8"))[
        "consumption"
    ]["per_node"]
    assert nodes["perception"]["items_supplied_total"] == 2  # the unconditional seed
    assert nodes["solver"]["items_supplied_total"] == 1
    assert nodes["solver"]["distinct_value_id_list"] == [f"{STORE}::d2"]
    # both Reviewer visits land on the reviewer node, on the SAME row
    assert nodes["reviewer"]["rows_supplied"] == 1
    assert nodes["reviewer"]["items_supplied_total"] == 2
    assert nodes["reviewer"]["distinct_value_id_list"] == [
        f"{STORE}::d4", f"{STORE}::d6"
    ]
    assert nodes["planner"]["items_supplied_total"] == 1
    assert nodes["planner"]["distinct_value_id_list"] == [f"{STORE}::d5"]


# --------------------------------------------------------------------------
# Refusals
# --------------------------------------------------------------------------

def test_an_unfinished_manifest_is_refused(sealed):
    path = (
        sealed["data_root"] / "runs" / RUN / ATTEMPT / f"{RUN}.run-manifest.json"
    )
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["status"] = "FAILED"
    _write(path, manifest)
    with pytest.raises(SystemExit):
        _run(sealed)


def test_a_dirty_study_tree_is_refused(sealed):
    path = (
        sealed["data_root"] / "runs" / RUN / ATTEMPT / f"{RUN}.run-manifest.json"
    )
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["study_repo_dirt"] = ["src/x.py"]
    _write(path, manifest)
    with pytest.raises(SystemExit):
        _run(sealed)


def test_a_receipt_without_this_store_is_refused(sealed):
    path = sealed["data_root"] / "runs" / RUN / ATTEMPT / "flight-receipts.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["stages"]["run_phases"]["phase_supply"]["stores"].pop(STORE)
    _write(path, document)
    with pytest.raises(SystemExit):
        _run(sealed)


def test_a_flown_row_missing_from_the_comparator_scores_is_refused(sealed):
    path = (
        sealed["data_root"]
        / "runs"
        / COMPARATOR_RUN
        / COMPARATOR_ATTEMPT
        / f"{COMPARATOR_RUN}.scores.json"
    )
    document = json.loads(path.read_text(encoding="utf-8"))
    document[SCORER]["per_sample"] = [
        row for row in document[SCORER]["per_sample"] if row["sample_id"] != "s:2"
    ]
    _write(path, document)
    with pytest.raises(SystemExit):
        _run_joined(sealed)


# --------------------------------------------------------------------------
# What the read must never emit
# --------------------------------------------------------------------------

def test_no_statement_or_response_text_is_persisted(sealed):
    _run_joined(sealed)
    for name in ("delta-consumption.json", "delta-consumption.md"):
        text = (sealed["out"] / name).read_text(encoding="utf-8")
        assert SENTINEL not in text
        assert "final_response_text" not in text
        assert "evidence" not in text


def test_the_markdown_carries_the_per_node_and_per_value_tables(sealed):
    _run_joined(sealed)
    text = (sealed["out"] / "delta-consumption.md").read_text(encoding="utf-8")
    assert "## 2. Per node" in text
    assert "## 3. Per supplied value id" in text
    assert "## 4. Per scenario" in text
    assert "## 5. Candidate projection events" in text
    assert f"{STORE}::d4" in text
    assert "| solver |" in text


def test_the_markdown_truncates_the_value_table_and_says_so(sealed):
    _run_joined(sealed, "--max-value-rows", "2")
    text = (sealed["out"] / "delta-consumption.md").read_text(encoding="utf-8")
    assert "further value ids omitted" in text
