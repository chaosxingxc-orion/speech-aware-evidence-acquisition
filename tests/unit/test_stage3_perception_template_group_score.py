"""R6 read repair: ``stage3_rollout_score.py --mode perception-branches`` reads a Perception
``template_variants`` group.

The registered R6 column read failed because ``perception_branch_main`` fed the raw ``branches``
block of the Perception role to ``parse_perception_branches`` on a cell that declares
``roles.perception.template_variants`` (receipt schema ``saea-perception-branch-arms-v4``). These
tests drive the SAME code path (``parse_perception_arm_group`` -> ``render_perception_branch_columns``
-> ``score_perception_branch_copies``) over a synthetic sealed template-group run, keyed by the arm
ids p1, p2, aa, lock, and check the dispatch refusals.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails.supply_variants import (
    perception_branch_receipt, perception_branch_record,
)

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "stage3_perception_template_score", ROOT / "scripts/analysis/stage3_rollout_score.py",
)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

SAMPLE_ID = "slurp:train:TPL:0"
ARMS = ("p1", "p2", "aa", "lock")
FIT = {"slot_tokens": 24576, "completion_ceiling": 640,
       "base_prompt_tokens": 9600, "tokens_per_supplied_item": 120}
LOCKED = "probes/lock.txt"


def _block():
    return {
        "node": "perception", "max_supplied_items": 4, "fit_estimate": dict(FIT),
        "arms": [
            {"arm_id": "p1", "template_tokens": 400, "instruction_template": {
                "relpath": "configs/probes/nx/p1.txt", "sha256": "a" * 64}},
            {"arm_id": "p2", "template_tokens": 400, "instruction_template": {
                "relpath": "configs/probes/nx/p2.txt", "sha256": "b" * 64}},
            {"arm_id": "aa", "replicate_of": "lock"},
            {"arm_id": "lock", "deliver": True, "template_tokens": 380},
        ],
    }


def _values(perception_extra, *, material=True):
    values = {"native_episode": {"roles": {"perception": {"phase_id": "perception", **perception_extra}}}}
    if material:
        values["phase_material"] = {"perception": {"instruction_template": LOCKED}}
    return values


def _parse(perception_extra, **kwargs):
    values = _values(perception_extra, **kwargs)
    return mod.parse_perception_arm_group(
        values, values["native_episode"]["roles"]["perception"], {},
    )


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _answer(scenario):
    return json.dumps({"scenario": scenario, "action": "set", "entities": []}, sort_keys=True)


def _bundle(tmp_path, group, answers):
    trace, contacts, records = {}, [], []
    for index, branch in enumerate(group.branches):
        raw = answers[branch.branch_id]
        rid = f"{SAMPLE_ID}-solver-{branch.branch_id}"
        digest = _sha(raw)
        trace[f"{rid}/request"] = {"payload_sha256": "a" * 64}
        trace[f"{rid}/response"] = {"text": raw, "response_text_sha256": digest}
        contacts.append({"agent_contact_id": rid, "request_id": rid,
                         "request_sha256": "a" * 64, "response_text_sha256": digest})
        records.append(perception_branch_record(
            branch=branch, branch_index=index, contact_id=f"perception-{branch.branch_id}",
            request_sha256="b" * 64, response_text_sha256="c" * 64, note_sha256="d" * 64,
            note_parse_status="ok", candidate_intent_ids=("intent_x",), supplied_value_ids=(),
            solver_contact_id=rid, solver_request_sha256="a" * 64,
            solver_response_text_sha256=digest, candidate_supply_value_ids=(),
            template_group=True,
        ))
    receipt = perception_branch_receipt(group=group, phase_id="perception", records=records)
    row = {"sample_id": SAMPLE_ID, "text": answers["lock"],
           "native_episode_receipt": {
               "role_visits": [{"stage": "solver", "role_id": "solver", "execution_receipt": {
                   "contacts": contacts, "final_contact": contacts[-1]}}],
               "kind": "accepted", "perception_branches": receipt}}
    path = tmp_path / "runs" / "RUN" / "ATT" / "RUN.manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}")
    return SimpleNamespace(
        manifest={"status": "COMPLETED", "run_id": "RUN", "config": {"config_hash": "c" * 64},
                  "outputs": {"sha256": "d" * 64}, "raw_trace": {"sha256": "e" * 64},
                  "scores": {"sha256": "f" * 64}},
        attempt_state="FINALIZED", manifest_path=path, split_ids=frozenset([SAMPLE_ID]),
        outputs_rows=(row,), trace_records=trace,
    ), receipt


@pytest.fixture(autouse=True)
def _stub_delivery(monkeypatch):
    from speech_aware_evidence_acquisition.rails import native_episode_receipt
    monkeypatch.setattr(native_episode_receipt, "validate_native_episode_delivery_receipt",
                        lambda episode, **_kw: SimpleNamespace(kind=episode["kind"]))


def test_template_declaration_parses_through_the_runtime_parser():
    group = _parse({"template_variants": _block()})
    assert group.branch_ids == ARMS and group.level == 2
    assert group.delivering_branch.branch_id == "lock" and group.twin_branch.branch_id == "aa"


def test_declaration_refusals_by_name():
    with pytest.raises(mod.Stage3ScoreError, match="declares both branches and template_variants"):
        _parse({"template_variants": _block(), "branches": {}})
    with pytest.raises(mod.Stage3ScoreError, match="needs the node's own phase_material"):
        _parse({"template_variants": _block()}, material=False)
    with pytest.raises(mod.Stage3ScoreError, match="arm group is invalid"):
        _parse({"template_variants": {"arms": [], "fit_estimate": dict(FIT)}})


def test_a_branches_declaration_still_takes_the_legacy_parser():
    with pytest.raises(mod.Stage3ScoreError, match="must be an object with exactly"):
        _parse({})


def test_render_and_score_per_arm_over_a_sealed_template_run(tmp_path, monkeypatch):
    group = _parse({"template_variants": _block()})
    lock_answer = _answer("alarm")
    bundle, receipt = _bundle(tmp_path, group, {
        "p1": _answer("audio"), "p2": _answer("weather"), "aa": lock_answer, "lock": lock_answer})
    assert receipt["schema"] == "saea-perception-branch-arms-v4"
    out = tmp_path / "analysis"
    manifest = mod.render_perception_branch_columns(
        bundle, group, {SAMPLE_ID: "alarm"}, out, run_id="RUN", attempt_id="ATT",
        roster_sha256="1" * 64, config_hash="c" * 64)
    assert manifest["branch_order"] == list(ARMS) and set(manifest["copies"]) == set(ARMS)
    assert manifest["at1_column_reproduction_checked_rows"] == 1
    texts = {a: next(mod.iter_jsonl(Path(e["path"])))["text"] for a, e in manifest["copies"].items()}
    assert json.loads(texts["p1"])["scenario"] == "audio" and texts["lock"] == texts["aa"] == lock_answer

    from speech_aware_evidence_acquisition.core import scoring_batch

    def fake_score(*, outputs_copy, result_path, column_binding, **_kw):
        scenario = json.loads(next(mod.iter_jsonl(Path(outputs_copy)))["text"])["scenario"]
        result = {"aggregate": {"official": {"scenario": scenario},
                                "identity_check": {"passed": True}},
                  "per_sample": [{"sample_id": SAMPLE_ID}], "binding": column_binding}
        Path(result_path).write_text(json.dumps(result), encoding="utf-8")
        return result

    monkeypatch.setattr(scoring_batch, "score_complete_derived_copy", fake_score)
    summary = mod.score_perception_branch_copies(
        "slurp-slu-official-train", manifest, out, {}, tmp_path, {SAMPLE_ID: {}})
    assert summary["branch_order"] == list(ARMS) and set(summary["branches"]) == set(ARMS)
    assert summary["branches"]["p2"]["official"] == {"scenario": "weather"}
    for arm in ARMS:
        assert (out / f"arm-{arm}-slurp-slu-official-train-scores.json").is_file()
