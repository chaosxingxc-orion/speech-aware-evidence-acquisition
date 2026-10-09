"""NX R1 read repair: ``stage3_rollout_score.py`` reads a ``template_variants`` group.

The registered column read failed because ``supply_variant_main`` fed the raw ``supply_variants`` block of the
Solver role to ``parse_supply_variants`` on a cell that declares ``template_variants``. These tests drive the
SAME code path (``parse_solver_arm_group`` -> ``render_supply_variant_first_visit``) on a synthetic sealed
template run, the supply-group regression, and the cross-kind refusals.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from speech_aware_evidence_acquisition.rails import controllers  # noqa: F401 - registers formats
from speech_aware_evidence_acquisition.rails.solver_citation import DELIVER_CITED_ANSWER_V1
from speech_aware_evidence_acquisition.rails.supply_variants import (
    parse_template_variants,
    supply_variant_arm_record,
    supply_variant_receipt,
)

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("stage3_tpl_score", ROOT / "scripts/analysis/stage3_rollout_score.py")
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

IDS = ("slurp:train:000001:a", "slurp:train:000002:b")
FIT = {"slot_tokens": 24576, "completion_ceiling": 640,
       "base_prompt_tokens": 9600, "tokens_per_supplied_item": 120}
LOCKED = "probes/lock.txt"


def _block():
    return {
        "node": "solver", "max_supplied_items": 4, "fit_estimate": dict(FIT),
        "arms": [
            {"arm_id": "t1", "template_tokens": 400, "instruction_template": {
                "relpath": "configs/probes/nx/t1.txt", "sha256": "a" * 64}},
            {"arm_id": "aa", "replicate_of": "lock"},
            {"arm_id": "lock", "deliver": True, "template_tokens": 380},
        ],
    }


def _group():
    return parse_template_variants(_block(), role_kind="solver", phase_id="solver", locked_template=LOCKED)


def _values(solver_extra):
    return {"phase_material": {"solver": {"instruction_template": LOCKED}},
            "native_episode": {"roles": {"solver": {"phase_id": "solver", **solver_extra}}}}


def _parse(solver_extra):
    values = _values(solver_extra)
    solver = values["native_episode"]["roles"]["solver"]
    return mod.parse_solver_arm_group(values, solver, {"phase_id": "perception"}, {})


def _raw(answer):
    return json.dumps({"scenario": answer, "action": "set", "entities": []})


def _bundle(tmp_path, group, *, schema_override=None):
    trace, contacts = {}, []
    for arm in group.arms:
        raw = _raw("alarm" if arm.arm_id != "t1" else "audio")
        rid = f"{IDS[0]}-0-{arm.arm_id}"
        digest = hashlib.sha256(raw.encode()).hexdigest()
        trace[f"{rid}/request"] = {"payload_sha256": "a" * 64}
        trace[f"{rid}/response"] = {"text": raw, "response_text_sha256": digest}
        contacts.append({"agent_contact_id": rid, "request_id": rid,
                         "request_sha256": "a" * 64, "response_text_sha256": digest})
    visits = [{"stage": "solver", "role_id": "solver",
               "execution_receipt": {"contacts": contacts, "final_contact": contacts[-1]}}]
    records = [supply_variant_arm_record(arm=arm, arm_index=i, contact_id=contacts[i]["agent_contact_id"],
                                         supplied_value_ids=(), template_group=group.is_template)
               for i, arm in enumerate(group.arms)]
    variants = supply_variant_receipt(group=group, phase_id="solver", records=records)
    if schema_override:
        variants["schema"] = schema_override
    row = {"sample_id": IDS[0], "text": mod.render_answer({"scenario": "alarm", "action": "set", "entities": []}),
           "native_episode_receipt": {"role_visits": visits, "kind": "accepted"},
           "supply_variants": variants}
    path = tmp_path / "runs" / "RUN" / "ATT" / "RUN.manifest.json"
    path.parent.mkdir(parents=True)
    path.write_text("{}")
    return SimpleNamespace(
        manifest={"status": "COMPLETED", "run_id": "RUN", "config": {"config_hash": "c" * 64},
                  "outputs": {"sha256": "d" * 64}, "raw_trace": {"sha256": "e" * 64},
                  "scores": {"sha256": "f" * 64}},
        attempt_state="FINALIZED", manifest_path=path, split_ids=frozenset([IDS[0]]),
        outputs_rows=(row,), trace_records=trace,
    )


@pytest.fixture(autouse=True)
def _stub_delivery(monkeypatch):
    from speech_aware_evidence_acquisition.rails import native_episode_receipt
    monkeypatch.setattr(native_episode_receipt, "validate_native_episode_delivery_receipt",
                        lambda episode, **_kw: SimpleNamespace(kind=episode["kind"]))


def _render(bundle, group, tmp_path):
    return mod.render_supply_variant_first_visit(
        bundle, group, {IDS[0]: "alarm"}, tmp_path / "analysis", run_id="RUN", attempt_id="ATT",
        roster_sha256="1" * 64, config_hash="c" * 64)


def test_template_declaration_parses_through_the_harness_parser():
    group = _parse({"template_variants": _block()})
    assert group.is_template and group.arm_ids == ("t1", "aa", "lock")


def test_supply_declaration_still_parses_through_the_supply_parser():
    block = {"arms": [{"arm_id": "small", "overrides": {
        "knowledge_stores.a.phase_supply.solver.k": 10}}, {"arm_id": "plan", "deliver": True}],
        "fit_estimate": dict(FIT)}
    # the supply parser needs a declared store and a non-first phase; its refusal text proves the dispatch
    with pytest.raises(mod.Stage3ScoreError, match="arm group is invalid"):
        _parse({"supply_variants": block})


def test_cross_kind_and_double_and_missing_declarations_refuse_by_name():
    with pytest.raises(mod.Stage3ScoreError, match="declares both supply_variants and template_variants"):
        _parse({"template_variants": _block(), "supply_variants": {}})
    with pytest.raises(mod.Stage3ScoreError, match="declares neither"):
        _parse({})
    with pytest.raises(mod.Stage3ScoreError, match="arm group is invalid"):
        _parse({"supply_variants": _block()})  # a template block under the supply key
    with pytest.raises(mod.Stage3ScoreError, match="arm group is invalid"):
        _parse({"template_variants": {"arms": [], "fit_estimate": dict(FIT)}})  # supply-shaped block


def test_template_column_render_through_the_scorer_code_path(tmp_path):
    group = _group()
    bundle = _bundle(tmp_path, group)
    bundle_text = bundle.outputs_rows[0]["text"]
    manifest = _render(bundle, group, tmp_path)
    assert manifest["arm_order"] == ["t1", "aa", "lock"] and manifest["arm_group_kind"] == "template"
    assert manifest["at1_column_reproduction_checked_rows"] == 1
    decl = {row["arm_id"]: row for row in manifest["arm_declarations"]}
    assert decl["t1"]["instruction_template"]["relpath"] == "probes/nx/t1.txt"
    assert decl["lock"]["instruction_template"] is None
    texts = {arm: next(mod.iter_jsonl(Path(e["path"])))["text"] for arm, e in manifest["copies"].items()}
    assert json.loads(texts["t1"])["scenario"] == "audio"
    assert texts["lock"] == texts["aa"] == bundle_text


def test_receipt_kind_must_match_declared_kind(tmp_path):
    group = _group()
    bundle = _bundle(tmp_path, group, schema_override="saea-supply-variant-arms-v3")
    with pytest.raises(mod.Stage3ScoreError, match="receipt kind does not match"):
        _render(bundle, group, tmp_path)
