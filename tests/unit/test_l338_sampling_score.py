"""Decision 338: ``stage3_rollout_score.py --mode perception-branches`` reads a SAMPLING group.

The runner is flown on the fake transport (``test_l338_sampling_live._run``), its sealed v6 receipts and trace are lifted into the bundle shape
``render_perception_branch_columns`` reads, and the render is held to the registered commit: the ``l1`` column is the COMMITTED answer of its
n Solver samples (not the raw sample 0), ``l1-sample0`` is the stream column, the other branches' columns are their own single contact, and a tampered
sample or an incomplete contact group is refused.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

from test_l338_sampling_live import _run
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("stage3_rollout_score_l338", ROOT / "scripts/analysis/stage3_rollout_score.py")
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

pytestmark = pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")


def _bundle(tmp_path, summary, harness):
    trace = {record_id: payload for _channel, record_id, payload in harness.trace.records}
    rows = [{"sample_id": r.sample_id, "native_episode_receipt": r.native_episode_receipt} for r in summary.results]
    path = tmp_path / "runs" / "RUN" / "ATT" / "RUN.manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}")
    ids = frozenset(r["sample_id"] for r in rows)
    return SimpleNamespace(
        manifest={"status": "COMPLETED", "run_id": "RUN", "config": {"config_hash": "c" * 64}, "outputs": {"sha256": "d" * 64},
                  "raw_trace": {"sha256": "e" * 64}, "scores": {"sha256": "f" * 64}},
        attempt_state="FINALIZED", manifest_path=path, split_ids=ids, outputs_rows=tuple(rows), trace_records=trace,
    ), ids


def _render(tmp_path, bundle, group, ids):
    return mod.render_perception_branch_columns(
        bundle, group, {sid: "gold" for sid in ids}, tmp_path / "analysis", run_id="RUN", attempt_id="ATT",
        roster_sha256="1" * 64, config_hash="c" * 64)


def _texts(manifest, name):
    return {row["sample_id"]: row["text"] for row in mod.iter_jsonl(Path(manifest["copies"][name]["path"]))}


def test_the_sampling_declaration_parses_through_the_dispatch_and_is_exclusive():
    from test_l338_sampling_live import BLOCK

    values = {"native_episode": {"roles": {"perception": {"phase_id": "perception", "sampling_variants": BLOCK}}}}
    group = mod.parse_perception_arm_group(values, values["native_episode"]["roles"]["perception"], {})
    assert group.is_sampling and group.branch_ids == ("l1", "l2", "aa", "lock")
    with pytest.raises(mod.Stage3ScoreError, match="sampling_variants beside"):
        perception = {"phase_id": "perception", "sampling_variants": BLOCK, "thinking_variants": {}}
        mod.parse_perception_arm_group({}, perception, {})


def test_the_l1_column_is_the_committed_answer_and_the_stream_column_is_sample_zero(tmp_path):
    group, harness, summary = _run(tmp_path)
    bundle, ids = _bundle(tmp_path, summary, harness)
    manifest = _render(tmp_path, bundle, group, ids)
    assert manifest["branch_order"] == ["l1", "l2", "aa", "lock"] and manifest["stream_order"] == ["l1-sample0"]
    assert set(manifest["copies"]) == {"l1", "l2", "aa", "lock", "l1-sample0"}
    l1, stream, lock = _texts(manifest, "l1"), _texts(manifest, "l1-sample0"), _texts(manifest, "lock")
    for sid in ids:
        # The live proof's samples: two carry "paris", one is empty -> support 2 keeps paris; the committed answer equals sample 0 here.
        assert json.loads(l1[sid])["entities"] == [{"type": "place_name", "filler": "paris"}]
        assert l1[sid] == stream[sid] == lock[sid]
    rows = json.loads((tmp_path / "analysis" / "sampling-rows.json").read_text(encoding="utf-8"))["rows"]
    assert len(rows) == len(ids)
    for row in rows:
        solver = row["branches"]["l1"]
        assert solver["n"] == 3 and solver["delivered_entity_count"] == 1 and solver["entity_supports"] == [{"type": "place_name", "support": 2}]
        assert solver["gate"]["status"] == "n1-unavailable" and solver["parse_status"] == ["ok", "ok", "ok"]
        union = row["branches"]["l2"]["perception_samples"]
        assert union["merged_candidate_ids"] == ["i:a", "i:b", "i:c"] and union["appended_candidate_ids"] == ["i:c"]
        assert [s["candidate_intent_ids"] for s in union["sample_lists"]] == [["i:a", "i:b"], ["i:c", "i:a"]]


def test_a_committed_answer_that_differs_from_sample_zero_is_scored_as_committed(tmp_path):
    # Sample 0 carries an entity no other sample supports: the support filter drops it, so the column differs from the stream column.
    from test_l338_sampling_live import _answer, _note

    def output(key):
        sample_id, phase, visit, turn = key
        if phase == "perception":
            return _note("i:a", "i:b")
        if phase == "solver":
            return {1: _answer("paris", "rome"), 2: _answer("paris"), 3: _answer("paris")}.get(turn, _answer("paris"))
        return f"{phase}-analysis:{sample_id}:{visit}"

    group, harness, summary = _run(tmp_path, output=output)
    bundle, ids = _bundle(tmp_path, summary, harness)
    manifest = _render(tmp_path, bundle, group, ids)
    for sid in ids:
        assert [e["filler"] for e in json.loads(_texts(manifest, "l1")[sid])["entities"]] == ["paris"]
        assert [e["filler"] for e in json.loads(_texts(manifest, "l1-sample0")[sid])["entities"]] == ["paris", "rome"]
    rows = json.loads((tmp_path / "analysis" / "sampling-rows.json").read_text(encoding="utf-8"))["rows"]
    assert rows[0]["branches"]["l1"]["base_entity_count"] == 2 and rows[0]["branches"]["l1"]["delivered_entity_count"] == 1


def test_a_tampered_trace_text_is_refused(tmp_path):
    group, harness, summary = _run(tmp_path)
    bundle, ids = _bundle(tmp_path, summary, harness)
    sid = sorted(ids)[0]
    receipt = next(r.native_episode_receipt for r in summary.results if r.sample_id == sid)
    visit = next(v for v in receipt["role_visits"] if v["stage"] == "solver")
    second = visit["execution_receipt"]["contacts"][1]["request_id"]
    original = bundle.trace_records[f"{second}/response"]
    bundle.trace_records[f"{second}/response"] = {**original, "text": original["text"] + " "}
    with pytest.raises(mod.Stage3ScoreError, match="hash differs from custody|digest|differs"):
        _render(tmp_path / "t1", bundle, group, ids)


def test_the_stream_column_is_scored_once_beside_the_branch_columns(tmp_path, monkeypatch):
    group, harness, summary = _run(tmp_path)
    bundle, ids = _bundle(tmp_path, summary, harness)
    out = tmp_path / "analysis"
    manifest = _render(tmp_path, bundle, group, ids)
    from speech_aware_evidence_acquisition.core import scoring_batch

    scored = []

    def fake_score(*, outputs_copy, result_path, column_binding, **_kw):
        scored.append(column_binding["branch_id"])
        per = [{"sample_id": row["sample_id"]} for row in mod.iter_jsonl(Path(outputs_copy))]
        result = {"aggregate": {"official": {"n": len(per)}, "identity_check": {"passed": True}}, "per_sample": per, "binding": column_binding}
        Path(result_path).write_text(json.dumps(result), encoding="utf-8")
        return result

    monkeypatch.setattr(scoring_batch, "score_complete_derived_copy", fake_score)
    delivered = {sid: {} for sid in ids}
    result = mod.score_perception_branch_copies("slurp-slu-official-train", manifest, out, {}, tmp_path, delivered)
    assert scored == ["l1", "l2", "aa", "lock", "l1-sample0"] and result["stream_order"] == ["l1-sample0"]
    assert (out / "arm-l1-sample0-slurp-slu-official-train-scores.json").is_file()
