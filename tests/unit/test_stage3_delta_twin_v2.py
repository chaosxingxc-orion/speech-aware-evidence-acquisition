"""Stage-3 S3-4s (owner decision 106): the NODE-AWARE derangement twin.

The form control must differ from its parent in WHAT IS ATTACHED TO WHAT and
in nothing else:

* candidate-bound nodes (solver / reviewer / planner) keep v1's facet
  derangement;
* the unconditional node (perception) -- which has no facet binding at
  flight time -- gets a derangement of its TARGET fields instead;
* the TOKEN COUNT is held exactly, which is what makes the twin a form
  control rather than a second, smaller store.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

_spec = importlib.util.spec_from_file_location(
    "build_slurp_stage3_delta_twin_v2",
    REPO_ROOT / "scripts" / "build_slurp_stage3_delta_twin.py",
)
twin = importlib.util.module_from_spec(_spec)
sys.modules.setdefault(_spec.name, twin)
_spec.loader.exec_module(twin)  # type: ignore[union-attr]

SEED = 20260923


def _row(suffix, *, node, kind, target, content):
    return {
        "value_id": f"delta:1:{suffix}",
        "content": content,
        "associated_facet_ids": [target],
        "node_target": node,
        "source_sample_ids": ["train-1"],
        "provenance_refs": [f"advantage:SAEA-TEST-RUN:train-1:0:1:{suffix[:1]}"],
        "task_target": f"{node}:{kind}:{target}",
        "prior_score": 0.5,
    }


def _document():
    return {
        "schema": "saea-stage3-authored-deltas-v2",
        "iteration": 1,
        "rows": [
            _row("aaaaaaaaaaaa", node="solver", kind="slot-contract",
                 target="alarm_set", content="Keep the time slot when a clock time is stated."),
            _row("bbbbbbbbbbbb", node="solver", kind="intent-boundary",
                 target="alarm_query", content="Do not answer a query as a set."),
            _row("cccccccccccc", node="reviewer", kind="reviewer-criterion",
                 target="alarm_set", content="Reject a draft with no device slot."),
            _row("dddddddddddd", node="planner", kind="planner-rule",
                 target="alarm_set", content="Revise once when the reviewer flags the intent."),
            _row("eeeeeeeeeeee", node="perception", kind="perception-hint",
                 target="audio_volume_up", content="Propose the volume intent for loudness words."),
            _row("ffffffffffff", node="perception", kind="perception-hint",
                 target="alarm_query", content="Propose the query intent for existing alarms."),
        ],
    }


def _v1_document():
    rows = []
    for suffix, target in (("aaaaaaaaaaaa", "alarm_set"), ("bbbbbbbbbbbb", "alarm_query")):
        row = _row(suffix, node="solver", kind="slot-contract", target=target,
                   content=f"A statement about {target}.")
        row.pop("node_target")
        row["task_target"] = f"slot-contract:{target}"
        rows.append(row)
    return {"schema": "saea-stage3-authored-deltas-v1", "iteration": 1, "rows": rows}


def test_the_twin_holds_the_token_count_exactly() -> None:
    parent = _document()
    built = twin.build_twin_document(parent, seed=SEED)
    assert twin.authored_token_count(built) == twin.authored_token_count(parent)


def test_candidate_bound_rows_have_their_facets_deranged() -> None:
    """A POSITIONAL derangement: no row keeps its own slot, the multiset of
    attachments is preserved (which is what holds the token count), and only
    the attachment moves.

    A real store carries several deltas per target, so a duplicate row can
    legitimately land on an equal VALUE -- the builder tolerates that and
    counts it, and refuses only a group with one distinct attachment.
    """

    parent = _document()
    built = twin.build_twin_document(parent, seed=SEED)
    by_id = {row["value_id"]: row for row in built["rows"]}
    bound = [row for row in parent["rows"] if row["node_target"] != "perception"]
    for row in bound:
        twinned = by_id[row["value_id"]]
        # Only the attachment moves.
        assert twinned["content"] == row["content"]
        assert twinned["node_target"] == row["node_target"]
        assert twinned["task_target"] == row["task_target"]
    changed = [
        row for row in bound
        if by_id[row["value_id"]]["associated_facet_ids"] != row["associated_facet_ids"]
    ]
    assert changed, "the candidate-bound group was not twinned at all"
    assert sorted(
        tuple(by_id[row["value_id"]]["associated_facet_ids"]) for row in bound
    ) == sorted(tuple(row["associated_facet_ids"]) for row in bound)
    assert twin.count_value_fixed_points(parent["rows"], built["rows"]) < len(
        parent["rows"]
    )


def test_a_group_whose_rows_all_name_one_attachment_is_refused() -> None:
    document = _document()
    for row in document["rows"]:
        if row["node_target"] == "perception":
            continue
        row["associated_facet_ids"] = ["alarm_set"]
    with pytest.raises(twin.Stage3DeltaTwinError):
        twin.build_twin_document(document, seed=SEED)


def test_the_unconditional_rows_have_their_targets_permuted() -> None:
    parent = _document()
    built = twin.build_twin_document(parent, seed=SEED)
    by_id = {row["value_id"]: row for row in built["rows"]}
    perception = [row for row in parent["rows"] if row["node_target"] == "perception"]
    for row in perception:
        twinned = by_id[row["value_id"]]
        assert twinned["content"] == row["content"]
        assert twinned["node_target"] == "perception"
        node, kind, target = twinned["task_target"].split(":", 2)
        assert (node, kind) == ("perception", "perception-hint")
        assert target != row["task_target"].split(":", 2)[2]
        assert twinned["associated_facet_ids"] == [target]
    # A permutation, so the multiset of targets is preserved.
    def _targets(rows):
        return sorted(
            row["task_target"].split(":", 2)[2]
            for row in rows if row["node_target"] == "perception"
        )

    assert _targets(built["rows"]) == _targets(parent["rows"])


def test_the_twin_is_deterministic_for_one_seed() -> None:
    first = twin.build_twin_document(_document(), seed=SEED)
    second = twin.build_twin_document(_document(), seed=SEED)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_a_group_of_one_is_refused_rather_than_left_a_fixed_point() -> None:
    document = _document()
    document["rows"] = [
        row for row in document["rows"] if row["node_target"] != "perception"
    ] + [document["rows"][-1]]
    with pytest.raises(twin.Stage3DeltaTwinError):
        twin.build_twin_document(document, seed=SEED)


def test_an_unknown_node_target_is_refused() -> None:
    document = _document()
    document["rows"][0]["node_target"] = "acquisition"
    with pytest.raises(twin.Stage3DeltaTwinError):
        twin.build_twin_document(document, seed=SEED)


def test_the_v1_twin_path_is_unchanged() -> None:
    parent = _v1_document()
    built = twin.build_twin_document(parent, seed=SEED)
    assert built["schema"] == "saea-stage3-authored-deltas-v1"
    assert twin.authored_token_count(built) == twin.authored_token_count(parent)
    for original, twinned in zip(parent["rows"], built["rows"]):
        assert twinned["content"] == original["content"]
        assert twinned["associated_facet_ids"] != original["associated_facet_ids"]
        # v1 never touches task_target.
        assert twinned["task_target"] == original["task_target"]
