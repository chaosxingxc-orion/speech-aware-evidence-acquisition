"""NX-T column readers and the smoke sign-off after the absent-Solver-column fix (2026-10-15).

An arm whose Solver contact ended on a finite completion has an ABSENT Solver column on that row. The readers (the NX-T R1 policy reader and the
NX-T R2 budget reader) count it as that arm's delivery failure: scored as the canonical empty answer (zero for that row's arm in the paired
contrast, proved by the reader itself) and reported as ``absent_rows`` beside the table; the smoke sign-off conditions gain ``absent_columns == 0``.
Model-free and synthetic.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
for _extra in (REPO / "scripts" / "flights" / "nx", REPO / "scripts" / "flights" / "direct", REPO / "scripts" / "flights" / "tfrl",
               REPO / "scripts" / "analysis", REPO / "scripts" / "flights" / "batch", REPO / "src"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

import slurp_direct_fold_b_core_read as base  # noqa: E402
import slurp_nxt_thinking_budget_column_read as budget  # noqa: E402
import slurp_nxt_thinking_policy_column_read as policy  # noqa: E402
import smoke_signoff as signoff  # noqa: E402

CONDITIONS = REPO / "docs" / "readiness" / "2026-10-13-slurp-nxt-r1-thinking-policy-fold-b-v1-signoff-conditions-v1.json"


def _receipts(arms, *, absent=()):
    """Sealed-output rows reduced as the readers load them: ``absent`` is ``[(sample_id, arm), ...]``."""

    rows = []
    for sid in ("s1", "s2", "s3"):
        rows.append({"sample_id": sid, "native_episode_receipt": {"perception_branches": {"branches": [
            {"branch_id": arm, "contact_id": f"{sid}:{arm}:p", "solver_contact_id": f"{sid}:{arm}:s",
             **({"solver_absent": True, "absent_reason": "finite-completion:length"} if (sid, arm) in absent else {})}
            for arm in arms]}}})
    return rows


def _scores(ids, arms, *, absent=(), absent_score=0.0):
    """Per-row scores: every row perfect, except an absent (sample, arm) row, scored ``absent_score`` (zero = the canonical empty answer)."""

    out = {}
    for arm in arms:
        out[arm] = {}
        for sid in ids:
            tp = absent_score if (sid, arm) in absent else 3.0
            fp = 3.0 if (sid, arm) in absent else 1.0
            out[arm][sid] = {"slu_f1_word_tp": tp, "slu_f1_char_tp": tp, "slu_f1_word_fp": fp, "slu_f1_char_fp": fp, "slu_f1_word_fn": fp, "slu_f1_char_fn": fp,
                             base.INTENT_FIELD: absent_score if (sid, arm) in absent else 1.0}
    return out


# ---- the shared count and the zero-score proof ---------------------------------------------------------------------------------------------------


def test_the_absent_columns_are_counted_per_arm_with_ids_and_reason_codes_only():
    arms = policy.ARMS
    found = base.absent_solver_columns(_receipts(arms, absent={("s2", "both-off"), ("s3", "both-off"), ("s3", "solver-off")}), arms)
    assert found["by_arm"] == {arm: {"both-off": 2, "solver-off": 1}.get(arm, 0) for arm in arms}
    assert found["total"] == 3 and found["rows"] == 2 and found["reasons"] == {"finite-completion:length": 3}
    assert found["sample_ids_by_arm"]["both-off"] == ["s2", "s3"]
    assert base.absent_solver_columns(_receipts(arms), arms)["total"] == 0


def test_an_absent_column_scored_above_zero_is_refused_by_the_reader():
    ids, arms = ["s1", "s2", "s3"], policy.ARMS
    absent = base.absent_solver_columns(_receipts(arms, absent={("s2", "both-off")}), arms)
    base.require_absent_scored_zero(_scores(ids, arms, absent={("s2", "both-off")}), absent)
    with pytest.raises(base.ReadError, match="not scored as the canonical empty answer"):
        base.require_absent_scored_zero(_scores(ids, arms, absent={("s2", "both-off")}, absent_score=2.0), absent)
    with pytest.raises(base.ReadError, match="no score row"):
        base.require_absent_scored_zero({"both-off": {}}, absent)


# ---- the policy reader ---------------------------------------------------------------------------------------------------------------------


def test_the_policy_reader_counts_absent_rows_as_that_arms_delivery_failure():
    ids, arms = ["s1", "s2", "s3"], policy.ARMS
    flagged = {("s2", "both-off")}
    absent = base.absent_solver_columns(_receipts(arms, absent=flagged), arms)
    result = policy.read_stage(_scores(ids, arms, absent=flagged), ids, lambda sid: sid, lambda sid: "alarm", {}, {}, seed=1, draws=50, absent=absent)
    assert result["absent_columns"] == 1 and result["absent_rows_by_arm"]["both-off"] == 1 and result["absent_rows_by_arm"]["both-on"] == 0
    assert result["absent_reasons"] == {"finite-completion:length": 1}
    assert result["contrast"]["levels"]["both-off"]["absent_rows"] == 1 and result["contrast"]["levels"][policy.DELIVERING]["absent_rows"] == 0
    # The failed row drags that arm below the delivering arm in the paired contrast (zero for the row), and no other arm moves.
    versus = result["contrast"]["versus_delivering"]
    assert versus["both-off"]["slu_f1"]["point_pp"] < 0 and versus["perception-off"]["slu_f1"]["point_pp"] == 0.0
    assert versus["both-off"]["intent_saves_harms_ties_vs_delivering"] == {"saves": 0, "harms": 1, "ties": 2}
    markdown = policy.render_markdown(result)
    assert "absent rows" in markdown and "delivery failure" in markdown


def test_the_policy_reader_refuses_a_read_whose_absent_column_was_scored_as_an_answer():
    ids, arms = ["s1", "s2", "s3"], policy.ARMS
    absent = base.absent_solver_columns(_receipts(arms, absent={("s2", "both-off")}), arms)
    with pytest.raises(base.ReadError, match="canonical empty answer"):
        policy.read_stage(_scores(ids, arms, absent={("s2", "both-off")}, absent_score=1.0), ids, lambda sid: sid, lambda sid: "a", {}, {}, seed=1, draws=50, absent=absent)


def test_the_policy_smoke_table_carries_absent_columns_and_the_signoff_conditions_require_zero():
    arms = policy.ARMS
    mapping = policy.arm_contact_map(_receipts(arms))
    clean = policy.smoke_stage(policy.attribute([], mapping), absent=base.absent_solver_columns(_receipts(arms), arms))
    dirty = policy.smoke_stage(policy.attribute([], mapping), absent=base.absent_solver_columns(_receipts(arms, absent={("s1", "both-off")}), arms))
    assert clean["absent_columns"] == 0 and dirty["absent_columns"] == 1 and dirty["absent_rows_by_arm"]["both-off"] == 1
    assert policy.smoke_stage(policy.attribute([], mapping))["absent_columns"] == 0                    # a caller that passes nothing sees zero
    conditions = json.loads(CONDITIONS.read_text(encoding="utf-8"))
    signoff.validate_conditions(conditions)
    assert {"id": "absent-columns", "path": "absent_columns", "op": "==", "value": 0} in conditions["extras"]

    def verdict(table):
        return {c["id"]: c for c in signoff.evaluate(conditions, table) if c["id"].startswith("extra/absent-columns")}

    assert verdict(clean)["extra/absent-columns/absent_columns"]["ok"] is True
    failing = verdict(dirty)["extra/absent-columns/absent_columns"]
    assert failing["ok"] is False and failing["observed"] == 1 and failing["limit"] == 0
    assert verdict({"schema": "x"})["extra/absent-columns"]["ok"] is False                        # a table without the field is refused, not passed


def test_the_policy_reader_keeps_only_ids_and_the_absent_mark_from_the_sealed_outputs(tmp_path):
    path = tmp_path / "outputs.jsonl"
    row = {"sample_id": "s1", "text": "SECRET ANSWER TEXT", "native_episode_receipt": {"perception_branches": {"branches": [
        {"branch_id": "both-off", "contact_id": "c1", "solver_contact_id": "c2", "thinking_policy": None, "note_sha256": "x" * 64,
         "solver_absent": True, "absent_reason": "finite-completion:length"}]}}}
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    loaded = policy.load_outputs_rows(path)
    assert "SECRET" not in json.dumps(loaded)
    kept = loaded[0]["native_episode_receipt"]["perception_branches"]["branches"][0]
    assert kept["solver_absent"] is True and kept["absent_reason"] == "finite-completion:length"
    assert base.absent_solver_columns(loaded, ["both-off"])["by_arm"] == {"both-off": 1}


# ---- the budget reader ---------------------------------------------------------------------------------------------------------------------


def test_the_budget_reader_counts_absent_rows_and_its_signoff_requires_none():
    ids, arms = ["s1", "s2", "s3"], budget.ARMS
    flagged = {("s2", arms[0])}
    absent = base.absent_solver_columns(_receipts(arms, absent=flagged), arms)
    result = budget.read_stage(_scores(ids, arms, absent=flagged), ids, lambda sid: sid, lambda sid: "alarm", {}, {}, seed=1, draws=50, absent=absent)
    assert result["absent_columns"] == 1 and result["absent_rows_by_arm"][arms[0]] == 1
    assert result["contrast"]["levels"][arms[0]]["absent_rows"] == 1 and result["contrast"]["levels"][budget.DELIVERING]["absent_rows"] == 0
    assert "absent rows" in budget.render_markdown(result)
    mapping = budget.arm_contact_map(_receipts(arms))
    clean = budget.smoke_stage(budget.attribute([], mapping), absent=base.absent_solver_columns(_receipts(arms), arms))
    dirty = budget.smoke_stage(budget.attribute([], mapping), absent=absent)
    assert clean["signoff"]["conditions"]["no_absent_columns"] is True and dirty["signoff"]["conditions"]["no_absent_columns"] is False
    assert dirty["signoff"]["all_ok"] is False and dirty["absent_columns"] == 1
    with pytest.raises(base.ReadError):
        budget.read_stage(_scores(ids, arms, absent=flagged, absent_score=1.0), ids, lambda sid: sid, lambda sid: "a", {}, {}, seed=1, draws=50, absent=absent)
