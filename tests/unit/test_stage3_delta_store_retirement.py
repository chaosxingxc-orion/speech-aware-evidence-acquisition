"""Stage-3 S3-6: the curator's ``--retire-value-ids`` option (owner decision
83, the amendment of append-only).

Four obligations:

1. The retention document's RETIRE ids are read as ids, from either shape
   the retention CLI emits or a bare list.
2. The named predecessor rows are DROPPED from version t+1's set and their
   ids are recorded in the curation report.
3. A retired row stays a dedup TOMBSTONE: curating version t+1 from the same
   advantage outputs must not reinstate the retired statement under a fresh
   iteration's value id. A live survivor still wins over a tombstone.
4. Without the option not one byte moves -- and an option that retires
   nothing is byte-identical to no option at all.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

_spec = importlib.util.spec_from_file_location(
    "build_slurp_stage3_delta_store_retirement",
    REPO_ROOT / "scripts" / "build_slurp_stage3_delta_store.py",
)
cli = importlib.util.module_from_spec(_spec)
sys.modules.setdefault(_spec.name, cli)
_spec.loader.exec_module(cli)  # type: ignore[union-attr]

SOLVER_STATEMENT = "Keep the time slot whenever the speech states a clock time."
PERCEPTION_STATEMENT = (
    "Propose the query intent when the utterance asks about an alarm."
)
BLOCKS = (
    "NODE: solver\n"
    "DELTA-KIND: slot-contract\n"
    "TARGET: alarm_set\n"
    f"STATEMENT: {SOLVER_STATEMENT}\n"
    "NODE: perception\n"
    "DELTA-KIND: perception-hint\n"
    "TARGET: alarm_query\n"
    f"STATEMENT: {PERCEPTION_STATEMENT}\n"
)


def _row(value_id, content, *, node="solver"):
    return {
        "value_id": value_id,
        "content": content,
        "associated_facet_ids": ["alarm_set"],
        "node_target": node,
        "source_sample_ids": ["train-1"],
        "provenance_refs": ["advantage:SAEA-TEST-RUN:train-1:2:4:0"],
        "task_target": f"{node}:slot-contract:alarm_set",
        "prior_score": 0.6,
    }


# ---------------------------------------------------------------------------
# 1. Reading the retirement list
# ---------------------------------------------------------------------------


def test_the_retention_document_is_read_as_ids(tmp_path) -> None:
    path = tmp_path / "retention-v2.json"
    path.write_text(
        json.dumps({
            "schema": "saea-stage3-delta-retention-v1",
            "retired_value_ids": ["delta:1:bbbb", "delta:1:aaaa", "delta:1:bbbb"],
        }),
        encoding="utf-8", newline="\n",
    )
    # Ordered as given and de-duplicated: the file is authority on WHICH ids,
    # never on how many times one is named.
    assert cli.load_retired_value_ids(path) == ["delta:1:bbbb", "delta:1:aaaa"]


def test_a_decisions_list_and_a_bare_list_are_both_accepted(tmp_path) -> None:
    decisions = tmp_path / "decisions.json"
    decisions.write_text(
        json.dumps({
            "decisions": [
                {"value_id": "delta:1:aaaa", "decision": "RETIRE"},
                {"value_id": "delta:1:bbbb", "decision": "KEEP"},
            ]
        }),
        encoding="utf-8", newline="\n",
    )
    assert cli.load_retired_value_ids(decisions) == ["delta:1:aaaa"]
    bare = tmp_path / "bare.json"
    bare.write_text(json.dumps(["delta:1:cccc"]), encoding="utf-8", newline="\n")
    assert cli.load_retired_value_ids(bare) == ["delta:1:cccc"]


def test_an_empty_or_malformed_retirement_list_is_refused(tmp_path) -> None:
    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps([]), encoding="utf-8", newline="\n")
    with pytest.raises(cli.Stage3DeltaStoreError):
        cli.load_retired_value_ids(empty)
    malformed = tmp_path / "malformed.json"
    malformed.write_text(json.dumps({"rows": []}), encoding="utf-8", newline="\n")
    with pytest.raises(cli.Stage3DeltaStoreError):
        cli.load_retired_value_ids(malformed)


# ---------------------------------------------------------------------------
# 2. The partition
# ---------------------------------------------------------------------------


def test_partition_drops_the_named_rows_and_records_their_ids() -> None:
    rows = [
        _row("delta:1:aaaa", SOLVER_STATEMENT),
        _row("delta:1:bbbb", PERCEPTION_STATEMENT, node="perception"),
    ]
    kept, retired, report = cli.partition_retired(
        rows, ["delta:1:aaaa", "delta:1:zzzz"]
    )
    assert [row["value_id"] for row in kept] == ["delta:1:bbbb"]
    assert [row["value_id"] for row in retired] == ["delta:1:aaaa"]
    assert report["requested"] == 2
    assert report["applied"] == 1
    assert report["applied_value_ids"] == ["delta:1:aaaa"]
    # An id the predecessor never carried is reported, not raised: a
    # retention document written against one version must be auditable when
    # it is replayed against another.
    assert report["not_present_value_ids"] == ["delta:1:zzzz"]
    assert report["predecessor_rows_in"] == 2
    assert report["predecessor_rows_kept"] == 1
    # The report names ids and counts only -- never a statement.
    assert SOLVER_STATEMENT not in json.dumps(report)


# ---------------------------------------------------------------------------
# 3. The tombstone
# ---------------------------------------------------------------------------


def test_a_retired_statement_cannot_re_enter_as_a_fresh_candidate() -> None:
    survivors, counts = cli.curate(
        predecessor_rows=[_row("delta:1:bbbb", PERCEPTION_STATEMENT, node="perception")],
        candidate_rows=[_row("delta:2:aaaa", SOLVER_STATEMENT)],
        retired_rows=[_row("delta:1:aaaa", SOLVER_STATEMENT)],
    )
    assert [row["value_id"] for row in survivors] == ["delta:1:bbbb"]
    assert counts["retired_suppressed"] == 1
    assert counts["retired_tombstones"] == 1
    assert counts["new_accepted"] == 0


def test_a_near_duplicate_of_a_retired_statement_is_suppressed_too() -> None:
    near = SOLVER_STATEMENT.replace("Keep", "Always keep")
    _, counts = cli.curate(
        predecessor_rows=(),
        candidate_rows=[_row("delta:2:aaaa", near)],
        retired_rows=[_row("delta:1:aaaa", SOLVER_STATEMENT)],
    )
    assert counts["retired_suppressed"] == 1
    assert counts["new_accepted"] == 0


def test_a_live_survivor_wins_over_a_tombstone() -> None:
    survivors, counts = cli.curate(
        predecessor_rows=[_row("delta:1:bbbb", SOLVER_STATEMENT)],
        candidate_rows=[_row("delta:2:aaaa", SOLVER_STATEMENT)],
        retired_rows=[_row("delta:1:aaaa", SOLVER_STATEMENT)],
    )
    # Retirement removes a statement; it does not poison an unrelated
    # survivor that happens to be close to the retired one.
    assert [row["value_id"] for row in survivors] == ["delta:1:bbbb"]
    assert counts["exact_duplicate"] == 1
    assert counts["retired_suppressed"] == 0


def test_without_tombstones_nothing_changes() -> None:
    survivors, counts = cli.curate(
        predecessor_rows=(),
        candidate_rows=[_row("delta:2:aaaa", SOLVER_STATEMENT)],
    )
    assert [row["value_id"] for row in survivors] == ["delta:2:aaaa"]
    assert counts["retired_tombstones"] == 0
    assert counts["retired_suppressed"] == 0


# ---------------------------------------------------------------------------
# 4. End to end through the CLI
# ---------------------------------------------------------------------------


def _fixture(tmp_path):
    pairs_path = tmp_path / "pairs.json"
    pairs_path.write_text(
        json.dumps({
            "rows": [{
                "sample_id": "train-1",
                "best": {"sample_index": 2, "response_text_sha256": "a" * 64},
                "worst": {"sample_index": 4, "response_text_sha256": "b" * 64},
            }]
        }),
        encoding="utf-8", newline="\n",
    )
    outputs_path = tmp_path / "outputs.jsonl"
    outputs_path.write_text(
        json.dumps({
            "sample_id": "train-1", "response_text": BLOCKS, "disagreement": 0.6,
        }) + "\n",
        encoding="utf-8", newline="\n",
    )
    return pairs_path, outputs_path


def _curate(tmp_path, out_name, *, predecessor="none", iteration=1, extra=()):
    pairs_path, outputs_path = _fixture(tmp_path)
    out_path = tmp_path / out_name
    argv = [
        "--advantage-outputs", str(outputs_path),
        "--pairs", str(pairs_path),
        "--repo-root", str(tmp_path),
        "--predecessor", predecessor,
        "--iteration", str(iteration),
        "--run-id", "SAEA-TEST-RUN",
        "--out-authored", str(out_path),
        "--facet-rule", "target-only",
        *extra,
    ]
    assert cli.main(argv) == 0
    return out_path


def test_the_cli_drops_the_retired_row_and_does_not_let_it_back_in(
    tmp_path, capsys
) -> None:
    version_1 = _curate(tmp_path, "v1.json")
    rows = json.loads(version_1.read_bytes())["rows"]
    retired_id = next(
        row["value_id"] for row in rows if row["node_target"] == "solver"
    )
    capsys.readouterr()

    retention = tmp_path / "retention-v2.json"
    retention.write_text(
        json.dumps({
            "schema": "saea-stage3-delta-retention-v1",
            "retired_value_ids": [retired_id],
        }),
        encoding="utf-8", newline="\n",
    )
    version_2 = _curate(
        tmp_path, "v2.json", predecessor=str(version_1), iteration=2,
        extra=("--retire-value-ids", str(retention)),
    )
    document = json.loads(version_2.read_bytes())
    assert [row["node_target"] for row in document["rows"]] == ["perception"]
    # The same advantage outputs re-propose the retired statement at
    # iteration 2; the tombstone is what keeps it out.
    assert all(row["value_id"] != retired_id for row in document["rows"])
    assert all("delta:2:" not in row["value_id"] for row in document["rows"])

    report = json.loads(capsys.readouterr().out)
    assert report["retirement"]["applied_value_ids"] == [retired_id]
    assert report["retirement"]["predecessor_rows_in"] == 2
    assert report["retirement"]["predecessor_rows_kept"] == 1
    assert report["retirement"]["not_present_value_ids"] == []
    assert report["curation"]["retired_suppressed"] == 1
    assert report["survivor_count"] == 1
    assert SOLVER_STATEMENT not in json.dumps(report)


def test_a_retirement_that_applies_to_nothing_is_byte_identical(tmp_path) -> None:
    version_1 = _curate(tmp_path, "v1.json")
    plain = _curate(
        tmp_path, "plain.json", predecessor=str(version_1), iteration=2
    )
    retention = tmp_path / "retention-none.json"
    retention.write_text(
        json.dumps({"retired_value_ids": ["delta:1:not-in-this-store"]}),
        encoding="utf-8", newline="\n",
    )
    with_option = _curate(
        tmp_path, "with-option.json", predecessor=str(version_1), iteration=2,
        extra=("--retire-value-ids", str(retention)),
    )
    assert with_option.read_bytes() == plain.read_bytes()


def test_the_option_needs_a_predecessor(tmp_path) -> None:
    retention = tmp_path / "retention.json"
    retention.write_text(
        json.dumps({"retired_value_ids": ["delta:1:aaaa"]}),
        encoding="utf-8", newline="\n",
    )
    with pytest.raises(cli.Stage3DeltaStoreError, match="requires a --predecessor"):
        _curate(
            tmp_path, "out.json",
            extra=("--retire-value-ids", str(retention)),
        )
