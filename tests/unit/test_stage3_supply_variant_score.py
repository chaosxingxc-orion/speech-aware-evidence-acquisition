"""Synthetic first-visit supply-variant derived-copy custody checks."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from speech_aware_evidence_acquisition.rails import controllers  # noqa: F401 - registers formats
from speech_aware_evidence_acquisition.rails.solver_citation import DELIVER_CITED_ANSWER_V1
from speech_aware_evidence_acquisition.rails.supply_variants import SupplyVariantFitEstimate

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("stage3_supply_score", ROOT / "scripts/analysis/stage3_rollout_score.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

IDS = ("slurp:train:000001:a", "slurp:train:000002:b")
FIT = {"slot_tokens": 24576, "completion_ceiling": 640,
       "base_prompt_tokens": 9600, "tokens_per_supplied_item": 120}


def _group():
    arms = []
    for i, name in enumerate(("small", "plan")):
        knobs = () if i else (SimpleNamespace(path="knowledge_stores.a.phase_supply.solver.k", value=10),)
        arms.append(SimpleNamespace(arm_id=name, deliver=i == 1, knobs=knobs,
                                    max_supplied_items=20))
    return SimpleNamespace(arms=tuple(arms), fit_estimate=SupplyVariantFitEstimate(**FIT))


def _contact(sid, visit, arm, trace, *, raw=None):
    request_id = f"{sid}-{visit}-{arm}"
    if raw is None:
        raw = json.dumps({"scenario": "alarm" if visit == 0 else "audio",
                          "action": "set", "entities": []})
    digest = hashlib.sha256(raw.encode()).hexdigest()
    trace[f"{request_id}/request"] = {"payload_sha256": "a" * 64}
    trace[f"{request_id}/response"] = {
        "text": raw, "response_text_sha256": digest,
    }
    return {"agent_contact_id": request_id, "request_id": request_id,
            "request_sha256": "a" * 64, "response_text_sha256": digest}


def envelope(*, answer, intent=(), entities=()):
    """A valid ``saea-solver-cited-answer-v1`` envelope (module docstring's own shape,
    mirroring ``tests/unit/test_solver_citation.py``'s ``envelope`` helper)."""

    entity_text = ",".join(
        '{"type":%s,"evidence_ids":%s}' % (json.dumps(kind), json.dumps(list(ids)))
        for kind, ids in entities
    )
    return (
        '{"schema":%s,"answer":%s,"citations":{"intent":%s,"entities":[%s]}}'
        % (json.dumps("saea-solver-cited-answer-v1"), answer, json.dumps(list(intent)), entity_text)
    )


def _fixture(tmp_path, *, revisions=1, terminal=False):
    group = _group()
    trace = {}
    visits = []
    for visit in range(revisions + 1):
        contacts = [_contact(IDS[0], visit, arm.arm_id, trace) for arm in group.arms]
        visits.append({"stage": "solver", "role_id": "solver",
                       "execution_receipt": {"contacts": contacts, "final_contact": contacts[-1]}})
    records = []
    for i, arm in enumerate(group.arms):
        records.append({
            "arm_index": i, "arm_id": arm.arm_id, "deliver": arm.deliver,
            "contact_id": visits[-1]["execution_receipt"]["contacts"][i]["agent_contact_id"],
            "resolved_knobs": [{"path": k.path, "value": k.value} for k in arm.knobs],
            "supplied_value_ids": [], "supplied_item_count": 0,
            "max_supplied_items": arm.max_supplied_items,
        })
    variants = {"schema": "saea-supply-variant-arms-v1", "phase_id": "solver",
                "arm_count": 2, "delivered_arm_id": "plan",
                "fit_estimate": group.fit_estimate.as_json(), "arms": records}
    rows = [
        {"sample_id": IDS[0], "native_episode_receipt": {"role_visits": visits, "kind": "accepted"},
         "supply_variants": variants},
        {"sample_id": IDS[1], "native_episode_receipt": {
            "role_visits": [] if terminal else visits, "kind": "abstention"},
         "supply_variants": None if terminal else variants},
    ]
    manifest_path = tmp_path / "runs" / "RUN" / "ATT" / "RUN.manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text("{}")
    bundle = SimpleNamespace(
        manifest={"status": "COMPLETED", "run_id": "RUN",
                  "config": {"config_hash": "c" * 64},
                  "outputs": {"sha256": "d" * 64}, "raw_trace": {"sha256": "e" * 64},
                  "scores": {"sha256": "f" * 64}},
        attempt_state="FINALIZED", manifest_path=manifest_path,
        split_ids=frozenset(IDS), outputs_rows=tuple(rows), trace_records=trace,
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
    return mod.render_supply_variant_first_visit(
        bundle, group, {sid: "alarm" for sid in IDS}, tmp_path / "analysis",
        run_id="RUN", attempt_id="ATT", roster_sha256="1" * 64,
        config_hash="c" * 64,
    )


def test_first_visit_columns_ignore_revision_and_keep_terminal_row(tmp_path):
    bundle, group = _fixture(tmp_path, terminal=True)
    manifest = _render(bundle, group, tmp_path)
    assert manifest["rows"] == 2
    assert manifest["arm_order"] == ["small", "plan"]
    assert manifest["no_solver_visit_rows"] == 1
    assert manifest["later_solver_visit_count"] == 1
    for entry in manifest["copies"].values():
        rows = list(mod.iter_jsonl(Path(entry["path"])))
        assert [row["sample_id"] for row in rows] == list(IDS)
        assert json.loads(rows[0]["text"])["scenario"] == "alarm"
        assert rows[1]["text"] == mod.EMPTY_ANSWER
    meta = json.loads((tmp_path / "analysis" / "first-visit-rows.json").read_text())
    assert meta["rows"][1]["availability"] == "no_solver_visit"
    assert meta["rows"][0]["later_solver_visits"] == 1


def test_wrong_declared_arm_order_and_partial_first_group_refused(tmp_path):
    bundle, group = _fixture(tmp_path, terminal=True)
    bundle.outputs_rows[0]["supply_variants"]["arms"].reverse()
    with pytest.raises(mod.Stage3ScoreError, match="ordered by ascending arm_index"):
        _render(bundle, group, tmp_path)
    bundle, group = _fixture(tmp_path / "second", terminal=True)
    bundle.outputs_rows[0]["native_episode_receipt"]["role_visits"][0][
        "execution_receipt"]["contacts"].pop()
    with pytest.raises(mod.Stage3ScoreError, match="complete arm group"):
        _render(bundle, group, tmp_path / "second")


def test_missing_roster_row_and_unbound_source_refused(tmp_path):
    bundle, group = _fixture(tmp_path, terminal=True)
    bundle.outputs_rows = bundle.outputs_rows[:1]
    with pytest.raises(mod.Stage3ScoreError, match="roster"):
        _render(bundle, group, tmp_path)
    bundle, group = _fixture(tmp_path / "other", terminal=True)
    bundle.manifest["config"]["config_hash"] = "0" * 64
    with pytest.raises(mod.Stage3ScoreError, match="config hash"):
        _render(bundle, group, tmp_path / "other")


def test_render_is_idempotent_and_refuses_existing_copy_drift(tmp_path):
    bundle, group = _fixture(tmp_path, terminal=True)
    first = _render(bundle, group, tmp_path)
    assert _render(bundle, group, tmp_path) == first
    copy = Path(first["copies"]["small"]["path"])
    copy.write_text("tampered", encoding="utf-8")
    with pytest.raises(mod.Stage3ScoreError, match="existing derived copy"):
        _render(bundle, group, tmp_path)


def test_missing_solver_without_declared_terminal_fallback_refused(tmp_path):
    bundle, group = _fixture(tmp_path, terminal=True)
    bundle.outputs_rows[1]["native_episode_receipt"]["kind"] = "accepted"
    with pytest.raises(mod.Stage3ScoreError, match="not a declared terminal fallback"):
        _render(bundle, group, tmp_path)


# --------------------------------------------------------------------------
# owner decision 172, docs/superpowers/specs/2026-09-27-same-flight-supply-variant-instrument-
# design.md section 3/7: normalised column render (AT1), per-arm cited_value_ids from the trace.
# --------------------------------------------------------------------------


def _cited_fixture(tmp_path, *, delivered_text, small_answer, plan_answer):
    group = _group()
    trace = {}
    contacts = [
        _contact(IDS[0], 0, "small", trace, raw=envelope(
            answer=small_answer, intent=("value:s1",), entities=(("time", ("value:s2",)),),
        )),
        _contact(IDS[0], 0, "plan", trace, raw=envelope(
            answer=plan_answer, intent=("value:p1",), entities=(),
        )),
    ]
    visits = [{"stage": "solver", "role_id": "solver",
               "execution_receipt": {"contacts": contacts, "final_contact": contacts[-1]}}]
    records = []
    for i, arm in enumerate(group.arms):
        records.append({
            "arm_index": i, "arm_id": arm.arm_id, "deliver": arm.deliver,
            "contact_id": contacts[i]["agent_contact_id"],
            "resolved_knobs": [{"path": k.path, "value": k.value} for k in arm.knobs],
            "supplied_value_ids": [f"value:{arm.arm_id}-supplied"], "supplied_item_count": 1,
            "max_supplied_items": arm.max_supplied_items,
        })
    variants = {"schema": "saea-supply-variant-arms-v1", "phase_id": "solver",
                "arm_count": 2, "delivered_arm_id": "plan",
                "fit_estimate": group.fit_estimate.as_json(), "arms": records}
    row = {
        "sample_id": IDS[0], "text": delivered_text,
        "native_episode_receipt": {
            "role_visits": visits, "kind": "accepted",
            "deliver_normaliser": {"normaliser_id": DELIVER_CITED_ANSWER_V1},
        },
        "supply_variants": variants,
    }
    manifest_path = tmp_path / "runs" / "RUN" / "ATT" / "RUN.manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text("{}")
    bundle = SimpleNamespace(
        manifest={"status": "COMPLETED", "run_id": "RUN",
                  "config": {"config_hash": "c" * 64},
                  "outputs": {"sha256": "d" * 64}, "raw_trace": {"sha256": "e" * 64},
                  "scores": {"sha256": "f" * 64}},
        attempt_state="FINALIZED", manifest_path=manifest_path,
        split_ids=frozenset([IDS[0]]), outputs_rows=(row,), trace_records=trace,
    )
    return bundle, group


def test_at1_column_reproduction_passes_under_the_cited_answer_normaliser_and_derives_citations(
    tmp_path,
):
    plan_answer = '{ "action":"set" ,"scenario": "alarm","entities":[]}'
    small_answer = '{"action":"set","scenario":"alarm","entities":[]}'
    bundle, group = _cited_fixture(
        tmp_path, delivered_text=plan_answer, small_answer=small_answer, plan_answer=plan_answer,
    )
    manifest = mod.render_supply_variant_first_visit(
        bundle, group, {IDS[0]: "alarm"}, tmp_path / "analysis",
        run_id="RUN", attempt_id="ATT", roster_sha256="1" * 64, config_hash="c" * 64,
    )
    assert manifest["at1_column_reproduction_checked_rows"] == 1
    plan_rows = list(mod.iter_jsonl(Path(manifest["copies"]["plan"]["path"])))
    assert plan_rows[0]["text"] == plan_answer

    citation_rows = list(mod.iter_jsonl(Path(manifest["citation_rows"]["path"])))
    assert manifest["citation_rows"]["rows"] == 2
    by_arm = {row["arm_id"]: row for row in citation_rows}
    assert by_arm["plan"]["cited_value_ids"] == ["value:p1"]
    assert by_arm["plan"]["cited_value_ids_ok"] is True
    assert by_arm["plan"]["supplied_value_ids"] == ["value:plan-supplied"]
    assert by_arm["small"]["cited_value_ids_ok"] is True
    assert sorted(by_arm["small"]["cited_value_ids"]) == ["value:s1", "value:s2"]
    assert by_arm["small"]["response_format_id"] == "saea-solver-cited-answer-v1"


def test_at1_column_reproduction_refuses_on_mismatch(tmp_path):
    plan_answer = '{ "action":"set" ,"scenario": "alarm","entities":[]}'
    bundle, group = _cited_fixture(
        tmp_path, delivered_text='{"not": "what was delivered"}',
        small_answer='{"x":1}', plan_answer=plan_answer,
    )
    with pytest.raises(mod.Stage3ScoreError, match="AT1 column reproduction failed"):
        mod.render_supply_variant_first_visit(
            bundle, group, {IDS[0]: "alarm"}, tmp_path / "analysis",
            run_id="RUN", attempt_id="ATT", roster_sha256="1" * 64, config_hash="c" * 64,
        )


def test_a_row_with_no_normaliser_derives_citations_as_not_ok_and_keeps_the_old_render(tmp_path):
    # the pre-cited-answer / VAR-2 shape: no deliver_normaliser on the row, so the render falls
    # back to parse_slu_response exactly as before, and citations are recorded absent (not ok)
    # rather than invented.
    bundle, group = _fixture(tmp_path, revisions=0, terminal=True)
    manifest = _render(bundle, group, tmp_path)
    assert manifest["at1_column_reproduction_checked_rows"] == 0
    citation_rows = list(mod.iter_jsonl(Path(manifest["citation_rows"]["path"])))
    assert citation_rows and all(not row["cited_value_ids_ok"] for row in citation_rows)
    assert all(row["cited_value_ids"] == [] for row in citation_rows)
