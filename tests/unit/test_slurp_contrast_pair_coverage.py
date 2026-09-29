"""``scripts/analysis/slurp_contrast_pair_coverage.py`` (O7 ruling, same-flight instrument phase 2):
pure, model-free tests over a synthetic seed and table -- no data root, no real knowledge store, no
server, no GPU. Mirrors the import pattern
``tests/unit/test_build_slurp_intent_contrast_pairs.py`` uses for a ``scripts/`` module with no
package ``__init__.py``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_ANALYSIS = _REPO / "scripts" / "analysis"
if str(_ANALYSIS) not in sys.path:
    sys.path.insert(0, str(_ANALYSIS))

import slurp_contrast_pair_coverage as coverage  # noqa: E402


def _table(pairs: list[tuple[str, str]]) -> dict:
    rows = {}
    for x_id, y_id in pairs:
        rows[f"{x_id}|{y_id}"] = {
            "intents": [x_id, y_id],
            "activation_sentence": f"{x_id} vs {y_id} activation",
            "exclusion_sentence": f"{x_id} vs {y_id} exclusion",
        }
    return {"schema": "saea-slurp-perception-contrast-pairs-v1", "rows": rows}


def _qualified(store: str, intent: str) -> str:
    return f"{store}::intent-boundary:{intent}"


def _seed(branch_id: str, rows: dict[str, list[str]]) -> dict:
    return {"schema": "saea-prepared-artifact-v1", "output": {"branches": {branch_id: rows}}}


def test_table_pairs_reads_the_intents_field_as_unordered_pairs():
    table_doc = _table([("alpha", "beta"), ("gamma", "delta")])
    pairs = coverage.table_pairs(table_doc)
    assert pairs == {frozenset({"alpha", "beta"}), frozenset({"gamma", "delta"})}


def test_table_pairs_rejects_a_malformed_row():
    with pytest.raises(coverage.CoverageError, match="malformed"):
        coverage.table_pairs({"rows": {"bad": {"intents": ["only_one"]}}})


def test_branch_rows_raises_on_an_unknown_branch():
    seed_doc = _seed("a-agree", {"s1": [_qualified("store", "x")]})
    with pytest.raises(coverage.CoverageError, match="b-top2contrast"):
        coverage.branch_rows(seed_doc, "b-top2contrast")


def test_classify_counts_hit_no_table_row_and_fewer_than_two_intents():
    rows = {
        # rank-1/rank-2 pair {a, b} IS in the table -> hit.
        "s1": [_qualified("store", "a"), _qualified("store", "b")],
        # rank-1/rank-2 pair {a, c} is NOT in the table -> no-table-row.
        "s2": [_qualified("store", "a"), _qualified("store", "c")],
        # only one distinct intent (a repeats) -> fewer-than-two-intents.
        "s3": [_qualified("store", "a"), _qualified("store", "a")],
        # a second no-table-row hit on the SAME missing pair as s2 (order-independent).
        "s4": [_qualified("store", "c"), _qualified("store", "a")],
    }
    pairs = coverage.table_pairs(_table([("a", "b")]))
    result = coverage.classify(rows, pairs)
    counts = result["counts"]
    assert counts[coverage.HIT] == 1
    assert counts[coverage.NO_TABLE_ROW] == 2
    assert counts[coverage.FEWER_THAN_TWO] == 1
    assert result["missing"][("a", "c")] == 2


def test_classify_ignores_the_shared_guidance_sentinel_and_unrelated_stores():
    # branch_supplied_intent_ids (reused verbatim) skips the shared-guidance sentinel and any
    # value id that is not the intent-boundary store's own local-id shape.
    rows = {
        "s1": [
            "store::intent-boundary:shared-guidance",
            "store::intent-boundary:a",
            "other-store::something-else",
            "store::intent-boundary:b",
        ],
    }
    pairs = coverage.table_pairs(_table([("a", "b")]))
    result = coverage.classify(rows, pairs)
    assert result["counts"][coverage.HIT] == 1


def test_main_end_to_end_reports_top_missing_pairs_by_count(tmp_path, capsys):
    data_root = tmp_path
    seed_relpath = "prepared/TEST-SEED/seeds.json"
    table_relpath = "prepared/TEST-TABLE/table-v1.json"
    (data_root / "prepared" / "TEST-SEED").mkdir(parents=True)
    (data_root / "prepared" / "TEST-TABLE").mkdir(parents=True)
    seed_doc = _seed("b-top2contrast", {
        "s1": [_qualified("store", "a"), _qualified("store", "b")],
        "s2": [_qualified("store", "a"), _qualified("store", "c")],
        "s3": [_qualified("store", "a"), _qualified("store", "c")],
        "s4": [_qualified("store", "a"), _qualified("store", "d")],
        "s5": [_qualified("store", "only-one")],
    })
    (data_root / seed_relpath).write_text(json.dumps(seed_doc), encoding="utf-8")
    (data_root / table_relpath).write_text(json.dumps(_table([("a", "b")])), encoding="utf-8")

    exit_code = coverage.main([
        "--data-root", str(data_root), "--seed", seed_relpath, "--table", table_relpath,
        "--top-missing", "1",
    ])
    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["rows_total"] == 5
    assert output["rows_hit"] == 1
    assert output["rows_no_table_row"] == 3
    assert output["rows_fewer_than_two_intents"] == 1
    assert output["distinct_missing_pairs"] == 2
    # top-missing=1 -> only the highest-count pair (a, c) with count 2 is reported.
    assert output["top_missing_pairs"] == [{"intents": ["a", "c"], "count": 2}]


def test_main_requires_a_data_root():
    with pytest.raises(SystemExit, match="data-root"):
        coverage.main([
            "--data-root", "/definitely-does-not-exist-slurp-coverage-test",
            "--seed", "x", "--table", "y",
        ])
