"""NX-T R4: ``stage3_rollout_score.py`` reads a ``decoding_variants`` group (the column read's first stage), model-free.

Drives the SAME code path (``parse_solver_arm_group`` -> ``render_supply_variant_first_visit``) on a synthetic sealed decoding run: the declaration dispatch and its
cross-kind refusals, the render of every arm's first-visit answer with the declared sampling override stated in the manifest, and the receipt-kind and override checks.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails import controllers  # noqa: F401 - registers formats
from speech_aware_evidence_acquisition.rails.supply_variants import (
    parse_decoding_variants,
    supply_variant_arm_record,
    supply_variant_receipt,
)

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("stage3_dec_score", ROOT / "scripts/analysis/stage3_rollout_score.py")
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

IDS = ("slurp:train:000001:a", "slurp:train:000002:b")
FIT = {"slot_tokens": 24576, "completion_ceiling": 640, "base_prompt_tokens": 9600, "tokens_per_supplied_item": 120}
LOCKED = "probes/lock.txt"


def _block():
    return {
        "node": "solver", "max_supplied_items": 4, "template_tokens": 380, "fit_estimate": dict(FIT),
        "arms": [
            {"arm_id": "d1", "decoding": {"temperature": 0.6, "top_p": 0.95, "top_k": 20}},
            {"arm_id": "aa", "replicate_of": "lock"},
            {"arm_id": "lock", "deliver": True},
        ],
    }


def _group():
    return parse_decoding_variants(_block(), role_kind="solver", phase_id="solver")


def _parse(solver_extra):
    values = {"phase_material": {"solver": {"instruction_template": LOCKED}},
              "native_episode": {"roles": {"solver": {"phase_id": "solver", **solver_extra}}}}
    solver = values["native_episode"]["roles"]["solver"]
    return mod.parse_solver_arm_group(values, solver, {"phase_id": "perception"}, {})


def _raw(answer):
    return json.dumps({"scenario": answer, "action": "set", "entities": []})


def _bundle(tmp_path, group, *, schema_override=None, override_edit=None):
    trace, contacts = {}, []
    for arm in group.arms:
        raw = _raw("alarm" if arm.arm_id != "d1" else "audio")
        rid = f"{IDS[0]}-0-{arm.arm_id}"
        digest = hashlib.sha256(raw.encode()).hexdigest()
        trace[f"{rid}/request"] = {"payload_sha256": "a" * 64}
        trace[f"{rid}/response"] = {"text": raw, "response_text_sha256": digest}
        contacts.append({"agent_contact_id": rid, "request_id": rid, "request_sha256": "a" * 64, "response_text_sha256": digest})
    visits = [{"stage": "solver", "role_id": "solver", "execution_receipt": {"contacts": contacts, "final_contact": contacts[-1]}}]
    records = [supply_variant_arm_record(arm=arm, arm_index=i, contact_id=contacts[i]["agent_contact_id"], supplied_value_ids=(), decoding_group=True)
               for i, arm in enumerate(group.arms)]
    variants = supply_variant_receipt(group=group, phase_id="solver", records=records)
    if schema_override:
        variants["schema"] = schema_override
    if override_edit:
        override_edit(variants)
    row = {"sample_id": IDS[0], "text": mod.render_answer({"scenario": "alarm", "action": "set", "entities": []}),
           "native_episode_receipt": {"role_visits": visits, "kind": "accepted"}, "supply_variants": variants}
    path = tmp_path / "runs" / "RUN" / "ATT" / "RUN.manifest.json"
    path.parent.mkdir(parents=True)
    path.write_text("{}")
    return SimpleNamespace(
        manifest={"status": "COMPLETED", "run_id": "RUN", "config": {"config_hash": "c" * 64}, "outputs": {"sha256": "d" * 64},
                  "raw_trace": {"sha256": "e" * 64}, "scores": {"sha256": "f" * 64}},
        attempt_state="FINALIZED", manifest_path=path, split_ids=frozenset([IDS[0]]), outputs_rows=(row,), trace_records=trace,
    )


@pytest.fixture(autouse=True)
def _stub_delivery(monkeypatch):
    from speech_aware_evidence_acquisition.rails import native_episode_receipt

    monkeypatch.setattr(native_episode_receipt, "validate_native_episode_delivery_receipt", lambda episode, **_kw: SimpleNamespace(kind=episode["kind"]))


def _render(bundle, group, tmp_path):
    return mod.render_supply_variant_first_visit(
        bundle, group, {IDS[0]: "alarm"}, tmp_path / "analysis", run_id="RUN", attempt_id="ATT", roster_sha256="1" * 64, config_hash="c" * 64)


def test_decoding_declaration_parses_through_the_harness_parser():
    group = _parse({"decoding_variants": _block()})
    assert group.is_decoding and group.arm_ids == ("d1", "aa", "lock")


def test_cross_kind_and_missing_declarations_refuse_by_name():
    with pytest.raises(mod.Stage3ScoreError, match="decoding_variants beside supply_variants or template_variants"):
        _parse({"decoding_variants": _block(), "template_variants": {}})
    with pytest.raises(mod.Stage3ScoreError, match="decoding_variants beside supply_variants or template_variants"):
        _parse({"decoding_variants": _block(), "supply_variants": {}})
    with pytest.raises(mod.Stage3ScoreError, match="declares neither supply_variants nor template_variants nor decoding_variants"):
        _parse({})
    broken = _block()
    broken["arms"][0]["decoding"] = {"seed": 1}
    with pytest.raises(mod.Stage3ScoreError, match="arm group is invalid"):
        _parse({"decoding_variants": broken})


def test_decoding_column_render_through_the_scorer_code_path(tmp_path):
    group = _group()
    bundle = _bundle(tmp_path, group)
    bundle_text = bundle.outputs_rows[0]["text"]
    manifest = _render(bundle, group, tmp_path)
    assert manifest["arm_order"] == ["d1", "aa", "lock"] and manifest["arm_group_kind"] == "decoding"
    assert manifest["at1_column_reproduction_checked_rows"] == 1
    decl = {row["arm_id"]: row for row in manifest["arm_declarations"]}
    assert decl["d1"]["decoding_override"] == {"temperature": 0.6, "top_p": 0.95, "top_k": 20} or decl["d1"]["decoding_override"] == {"temperature": 0.6, "top_k": 20, "top_p": 0.95}
    assert decl["lock"]["decoding_override"] is None and decl["aa"]["decoding_override"] is None
    assert "instruction_template" not in decl["d1"]
    texts = {arm: next(mod.iter_jsonl(Path(e["path"])))["text"] for arm, e in manifest["copies"].items()}
    assert json.loads(texts["d1"])["scenario"] == "audio"
    assert texts["lock"] == texts["aa"] == bundle_text


def test_receipt_kind_must_match_declared_kind(tmp_path):
    group = _group()
    for schema in ("saea-supply-variant-arms-v3", "saea-supply-variant-arms-v4"):
        bundle = _bundle(tmp_path / schema, group, schema_override=schema)
        with pytest.raises(mod.Stage3ScoreError, match="receipt kind does not match|invalid|unregistered|shape"):
            _render(bundle, group, tmp_path / schema)


def test_a_sealed_override_other_than_the_declared_one_is_refused(tmp_path):
    group = _group()

    def edit(variants):
        variants["arms"][0]["decoding_override"] = {"temperature": 0.7}

    bundle = _bundle(tmp_path, group, override_edit=edit)
    with pytest.raises(mod.Stage3ScoreError, match="sampling override differs from declaration"):
        _render(bundle, group, tmp_path)
