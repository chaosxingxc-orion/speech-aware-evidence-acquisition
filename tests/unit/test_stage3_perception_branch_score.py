"""Synthetic level-2 perception-branch derived-copy custody checks (same-flight instrument phase
2, merge set C, item 2: render_perception_branch_columns/score_perception_branch_copies).

Structurally tests/unit/test_stage3_supply_variant_score.py's own twin, over the Perception
branch group's LEVEL-2 Solver columns instead of a Solver-declared arm group. Builds its fixture
receipt through the SAME validating constructors (rails.supply_variants.perception_branch_record/
perception_branch_receipt) real custody is sealed through, rather than hand-writing raw dicts, so
a fixture can never describe a shape the real receipt could not.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails.supply_variants import (
    parse_perception_branches, perception_branch_receipt, perception_branch_record,
)

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "stage3_perception_branch_score", ROOT / "scripts/analysis/stage3_rollout_score.py",
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

SAMPLE_ID = "slurp:train:ATPB:0"
BRANCH_IDS = ("B", "T", "A")
FIT = {
    "slot_tokens": 24576, "completion_ceiling": 640,
    "base_prompt_tokens": 9600, "tokens_per_supplied_item": 120,
}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _group():
    return parse_perception_branches(
        {
            "level": 2, "fit_estimate": dict(FIT),
            "branches": [
                {
                    "branch_id": "B", "max_supplied_items": 5,
                    "overrides": {"knowledge_stores.ex.phase_supply.perception.k": 30},
                },
                {"branch_id": "T", "replicate_of": "A", "max_supplied_items": 5},
                {"branch_id": "A", "deliver": True, "max_supplied_items": 5},
            ],
        },
        first_phase_id="perception", declared_stores=("ex",),
    )


def _solver_contact(sample_id, branch_id, trace, *, raw):
    request_id = f"{sample_id}-solver-{branch_id}"
    digest = _sha(raw)
    trace[f"{request_id}/request"] = {"payload_sha256": "a" * 64}
    trace[f"{request_id}/response"] = {"text": raw, "response_text_sha256": digest}
    return {
        "agent_contact_id": request_id, "request_id": request_id,
        "request_sha256": "a" * 64, "response_text_sha256": digest,
    }


def _answer(scenario: str) -> str:
    return json.dumps({"scenario": scenario, "action": "set", "entities": []}, sort_keys=True)


def _fixture(tmp_path, *, sample_id=SAMPLE_ID, answers, delivered_text=None):
    """``answers``: ``{branch_id: raw response text}`` for all three branches. The delivered
    (sealed) row text defaults to A's own answer -- the AT1-passing shape -- unless overridden."""

    group = _group()
    trace: dict[str, object] = {}
    contacts = [_solver_contact(sample_id, b, trace, raw=answers[b]) for b in BRANCH_IDS]
    solver_visit = {
        "stage": "solver", "role_id": "solver",
        "execution_receipt": {"contacts": contacts, "final_contact": contacts[-1]},
    }
    records = []
    for index, branch_id in enumerate(BRANCH_IDS):
        branch = group.branch_at(index)
        records.append(perception_branch_record(
            branch=branch, branch_index=index,
            contact_id=f"perception-{sample_id}-{branch_id}",
            request_sha256="b" * 64, response_text_sha256="c" * 64, note_sha256="d" * 64,
            note_parse_status="ok", candidate_intent_ids=("intent_x",), supplied_value_ids=(),
            solver_contact_id=contacts[index]["agent_contact_id"],
            solver_request_sha256=contacts[index]["request_sha256"],
            solver_response_text_sha256=contacts[index]["response_text_sha256"],
            candidate_supply_value_ids=(),
        ))
    branches_receipt = perception_branch_receipt(group=group, phase_id="perception", records=records)
    row = {
        "sample_id": sample_id,
        "text": answers["A"] if delivered_text is None else delivered_text,
        "native_episode_receipt": {
            "role_visits": [solver_visit], "kind": "accepted",
            "perception_branches": branches_receipt,
        },
    }
    manifest_path = tmp_path / "runs" / "RUN" / "ATT" / "RUN.manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("{}")
    bundle = SimpleNamespace(
        manifest={
            "status": "COMPLETED", "run_id": "RUN", "config": {"config_hash": "c" * 64},
            "outputs": {"sha256": "d" * 64}, "raw_trace": {"sha256": "e" * 64},
            "scores": {"sha256": "f" * 64},
        },
        attempt_state="FINALIZED", manifest_path=manifest_path,
        split_ids=frozenset([sample_id]), outputs_rows=(row,), trace_records=trace,
    )
    return bundle, group


@pytest.fixture(autouse=True)
def _stub_delivery(monkeypatch):
    from speech_aware_evidence_acquisition.rails import native_episode_receipt
    monkeypatch.setattr(
        native_episode_receipt, "validate_native_episode_delivery_receipt",
        lambda episode, **_kwargs: SimpleNamespace(kind=episode["kind"]),
    )


def _render(bundle, group, tmp_path):
    return mod.render_perception_branch_columns(
        bundle, group, {SAMPLE_ID: "alarm"}, tmp_path / "analysis",
        run_id="RUN", attempt_id="ATT", roster_sha256="1" * 64, config_hash="c" * 64,
    )


def test_at1_passes_when_as_column_equals_the_delivered_text(tmp_path):
    a_answer = _answer("alarm")
    bundle, group = _fixture(
        tmp_path, answers={"B": _answer("audio"), "T": a_answer, "A": a_answer},
    )
    manifest = _render(bundle, group, tmp_path)
    assert manifest["schema"] == mod.PERCEPTION_BRANCH_SOLVER_RENDER_SCHEMA
    assert manifest["branch_order"] == ["B", "T", "A"]
    assert manifest["at1_column_reproduction_checked_rows"] == 1
    a_rows = list(mod.iter_jsonl(Path(manifest["copies"]["A"]["path"])))
    assert a_rows[0]["text"] == a_answer


def test_at1_refuses_when_as_column_disagrees_with_the_delivered_text(tmp_path):
    bundle, group = _fixture(
        tmp_path,
        answers={"B": _answer("audio"), "T": _answer("alarm"), "A": _answer("alarm")},
        delivered_text=_answer("weather"),
    )
    with pytest.raises(mod.Stage3ScoreError, match="AT1 column reproduction failed"):
        _render(bundle, group, tmp_path)


def test_t_reproduces_as_own_rendered_answer_when_engineered_identical(tmp_path):
    """T's own Solver contact is A's wire payload byte for byte (AT-P2's own extension to level
    2), so an engineered pair whose raw response text is identical renders to the identical
    column text -- the render's own faithful pass-through of whatever the sealed trace carries."""

    shared_answer = _answer("alarm")
    bundle, group = _fixture(
        tmp_path, answers={"B": _answer("audio"), "T": shared_answer, "A": shared_answer},
    )
    manifest = _render(bundle, group, tmp_path)
    t_rows = list(mod.iter_jsonl(Path(manifest["copies"]["T"]["path"])))
    a_rows = list(mod.iter_jsonl(Path(manifest["copies"]["A"]["path"])))
    b_rows = list(mod.iter_jsonl(Path(manifest["copies"]["B"]["path"])))
    assert t_rows[0]["text"] == a_rows[0]["text"] == shared_answer
    assert b_rows[0]["text"] != a_rows[0]["text"]


def test_column_files_are_written_for_every_declared_branch(tmp_path):
    a_answer = _answer("alarm")
    bundle, group = _fixture(
        tmp_path, answers={"B": _answer("audio"), "T": a_answer, "A": a_answer},
    )
    manifest = _render(bundle, group, tmp_path)
    assert set(manifest["copies"]) == set(BRANCH_IDS)
    for branch_id in BRANCH_IDS:
        entry = manifest["copies"][branch_id]
        path = Path(entry["path"])
        assert path.name == f"arm-{branch_id}-first-visit-outputs.jsonl"
        assert path.is_file()
        rows = list(mod.iter_jsonl(path))
        assert [row["sample_id"] for row in rows] == [SAMPLE_ID]
        assert entry["sha256"] == mod.sha256_file(path)
    # Idempotent: a second render reads the same files back rather than rewriting them.
    assert _render(bundle, group, tmp_path) == manifest


def test_render_requires_a_level_2_group(tmp_path):
    a_answer = _answer("alarm")
    bundle, group = _fixture(
        tmp_path, answers={"B": _answer("audio"), "T": a_answer, "A": a_answer},
    )
    level1_group = SimpleNamespace(level=1)
    with pytest.raises(mod.Stage3ScoreError, match="level-2 group"):
        mod.render_perception_branch_columns(
            bundle, level1_group, {SAMPLE_ID: "alarm"}, tmp_path / "analysis",
            run_id="RUN", attempt_id="ATT", roster_sha256="1" * 64, config_hash="c" * 64,
        )


def test_seal_only_render_reads_kept_rows_from_the_predecessor_trace(tmp_path):
    """A seal-only completion's own trace is empty: every kept row's Solver branch contacts live
    in the verified predecessor trace (the E4 read's fix pattern), and the render names it."""

    a_answer = _answer("alarm")
    bundle, group = _fixture(
        tmp_path, answers={"B": _answer("audio"), "T": a_answer, "A": a_answer},
    )
    predecessor_records = {SAMPLE_ID: dict(bundle.trace_records)}
    bundle.trace_records.clear()
    bundle.manifest["predecessor_attempt"] = {"attempt_id": "ATT-PRED", "trace_sha256": "9" * 64}
    with pytest.raises(mod.Stage3ScoreError, match="trace pair is absent"):
        _render(bundle, group, tmp_path)
    manifest = mod.render_perception_branch_columns(
        bundle, group, {SAMPLE_ID: "alarm"}, tmp_path / "analysis-sealonly",
        run_id="RUN", attempt_id="ATT", roster_sha256="1" * 64, config_hash="c" * 64,
        predecessor_records=predecessor_records,
    )
    assert manifest["source"]["predecessor_attempt_id"] == "ATT-PRED"
    assert manifest["source"]["predecessor_trace_sha256"] == "9" * 64
    b_rows = list(mod.iter_jsonl(Path(manifest["copies"]["B"]["path"])))
    assert b_rows[0]["text"] == _answer("audio")


def test_render_refuses_a_contact_that_answers_another_branch_record(tmp_path):
    a_answer = _answer("alarm")
    bundle, group = _fixture(
        tmp_path, answers={"B": _answer("audio"), "T": a_answer, "A": a_answer},
    )
    records = bundle.outputs_rows[0]["native_episode_receipt"]["perception_branches"]["branches"]
    records[0]["solver_response_text_sha256"] = "0" * 64
    with pytest.raises(mod.Stage3ScoreError, match="does not answer the sealed branch record"):
        _render(bundle, group, tmp_path)
