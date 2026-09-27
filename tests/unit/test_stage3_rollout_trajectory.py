"""Stage-3 S3-4s (owner decision 106): ``pairs.json``'s per-row trajectory.

A synthetic sealed attempt -- one ``outputs.jsonl`` whose rows carry both a
``solver_group`` custody and a ``native_episode_receipt``, plus a
``<run>.trace.jsonl`` in the channel shape
``core.bundle.raw_contact_source`` reads -- exercises the whole rebuild
without any dataset, model or registered official scorer.

What the tests hold:

* the block is rebuilt from the SEAL alone (no re-flight, no model contact);
* it carries ids, labels, counts and hashes and NO text -- asserted by
  searching the serialised file for the synthetic transcript words;
* everything a seal does not carry is reported absent with a reason
  (cell ROLL-1 arms no ``reviewer_verdict``, so the Reviewer labels are
  re-derived from the sealed response with the registered parser);
* ``pairs.json`` stays idempotent and gains its ``pairs_schema`` bump.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "analysis" / "stage3_rollout_score.py"

_spec = importlib.util.spec_from_file_location("stage3_rollout_score_traj", MODULE_PATH)
mod = importlib.util.module_from_spec(_spec)
sys.modules.setdefault(_spec.name, mod)
_spec.loader.exec_module(mod)  # type: ignore[union-attr]

sys.path.insert(0, str(REPO_ROOT / "src"))
from speech_aware_evidence_acquisition.core.base import SCORERS, CoreError  # noqa: E402

FAKE_SCORER_ID = "test-stage3-traj-fake-scorer-v1"
RUN_ID = "TEST-STAGE3-TRAJ-RUN"
ATTEMPT_ID = "attempt-test-stage3-traj-generation-v1"
SAMPLES = 3
ROWS = ("slurp:train:100001:audio-1", "slurp:train:100002:audio-1")
GOLD = {
    "slurp:train:100001:audio-1": "alarm_set",
    "slurp:train:100002:audio-1": "audio_volume_up",
}
# The only "utterance text" in this fixture. It must never appear in
# pairs.json / per_row.json.
SECRET_WORD = "zebracrossing"


def fake_scorer(outputs_path, lock, root):
    rows = [
        json.loads(line)
        for line in outputs_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    per_sample = []
    correct = 0
    for row in rows:
        payload = json.loads(row["text"])
        exact = f"{payload['scenario']}_{payload['action']}" == GOLD[row["sample_id"]]
        correct += 1 if exact else 0
        per_sample.append({
            "sample_id": row["sample_id"],
            "scenario_action_exact": 1.0 if exact else 0.0,
            "slu_f1_f1": 1.0 if exact else 0.2,
        })
    return {
        "aggregate": {
            "official": {"slu_f1": correct / len(rows), "intent_accuracy": correct / len(rows)},
            "identity_check": {"passed": True},
        },
        "per_sample": per_sample,
    }


@pytest.fixture(autouse=True)
def _unregister_fake_scorer():
    # The fake scorer is registered into the process-global core.base.SCORERS by the tests that need it; drop it
    # after every test so no later module (test_engineering_base_check's registry/source agreement) sees a
    # test-only id.
    yield
    SCORERS._entries.pop(FAKE_SCORER_ID, None)


def _register_fake_scorer():
    try:
        SCORERS.register(FAKE_SCORER_ID, fake_scorer)
    except CoreError:
        pass


def _answer(scenario, action):
    return {"scenario": scenario, "action": action, "entities": []}


def _contact(request_id):
    return {
        "agent_contact_id": f"contact:{request_id}",
        "request_id": request_id,
        "request_sha256": "1" * 64,
        "response_sha256": "2" * 64,
        "response_text_sha256": hashlib.sha256(request_id.encode()).hexdigest(),
    }


def _visit(stage, role_id, request_id, *, truncated=False):
    contact = _contact(request_id)
    visit = {
        "role_id": role_id,
        "stage": stage,
        "execution_receipt": {"contacts": [contact], "final_contact": contact},
    }
    if truncated:
        visit["truncated"] = True
    return visit


def _episode_receipt(sample_id, *, accepted=True, truncated_planner=False):
    """One row's sealed episode receipt, in the exact key shape
    ``rails.runner`` seals for cell ROLL-1: role_visits + planner_routes +
    accepted/terminal solver receipt, and NO reviewer_verdicts (ROLL-1's
    native_episode fragment arms no reviewer_verdict)."""

    perception = _visit("perception", "perception", f"{sample_id}/perception/0")
    solver = _visit("solver", "solver", f"{sample_id}/solver/0")
    review = _visit("review", "reviewer", f"{sample_id}/review/0")
    planner = _visit(
        "planner", "planner", f"{sample_id}/planner/0", truncated=truncated_planner
    )
    visits = [perception, solver, review, planner]
    receipt = {
        "role_visits": visits,
        "planner_routes": [
            {
                "role_visit_index": 3,
                "revision_count": 0 if accepted else 1,
                "action": "ACCEPT" if accepted else "REVISE",
            }
        ],
    }
    if accepted:
        receipt["accepted_solver_receipt"] = solver["execution_receipt"]
    else:
        receipt["terminal_solver_receipt"] = solver["execution_receipt"]
        receipt["terminal_disposition"] = {
            "reason": "revision_limit",
            "revision_count": 1,
            "planner_action": "REVISE",
            "planner_accepted": False,
        }
    return receipt


def _trace_lines(sample_id, *, candidates, verdict, tokens, planner_finish="stop"):
    def response(request_id, text, completion_tokens):
        return json.dumps({
            "channel": "MODEL_RESPONSE",
            "record_id": f"{request_id}/response",
            "payload": {
                "text": text,
                "response_text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "usage": {"completion_tokens": completion_tokens},
            },
        })

    def wire(request_id, finish_reason):
        return json.dumps({
            "channel": "MODEL_WIRE_RESPONSE",
            "record_id": f"{request_id}/wire-response",
            "payload": {"request_id": request_id, "finish_reason": finish_reason},
        })

    perception_body = json.dumps({
        "schema": "saea-slurp-intent-hypotheses-v1",
        "sample_id": sample_id,
        "candidates": [
            {"intent_id": intent, "distinction": f"because {SECRET_WORD}",
             "evidence_refs": [], "unresolved_fields": []}
            for intent in candidates
        ],
    })
    return [
        response(f"{sample_id}/perception/0", perception_body, tokens["perception"]),
        wire(f"{sample_id}/perception/0", "stop"),
        response(f"{sample_id}/solver/0", "{}", tokens["solver"]),
        wire(f"{sample_id}/solver/0", "stop"),
        response(f"{sample_id}/review/0", f"{verdict}\nthe {SECRET_WORD} rationale",
                 tokens["review"]),
        wire(f"{sample_id}/review/0", "stop"),
        response(f"{sample_id}/planner/0", "ACCEPT", tokens["planner"]),
        wire(f"{sample_id}/planner/0", planner_finish),
    ]


@pytest.fixture()
def sealed(tmp_path):
    data_root = tmp_path / "data-root"
    directory = data_root / "runs" / RUN_ID / ATTEMPT_ID
    directory.mkdir(parents=True)

    row_answers = {
        # row 0 disagrees: sample 0 correct, samples 1-2 wrong.
        ROWS[0]: [_answer("alarm", "set"), _answer("alarm", "query"), _answer("alarm", "query")],
        # row 1 agrees: every sample correct -> not a pair.
        ROWS[1]: [_answer("audio", "volume_up")] * SAMPLES,
    }
    lines = []
    scores = []
    trace_lines = []
    for index, sample_id in enumerate(ROWS):
        samples = row_answers[sample_id]
        lines.append(json.dumps({
            "sample_id": sample_id,
            "solver_group": {
                "samples": [
                    {
                        "sample_index": i,
                        "parse_status": "ok",
                        "parsed_answer": payload,
                        "contacts": [_contact(f"{sample_id}/solver/{i}")],
                    }
                    for i, payload in enumerate(samples)
                ],
            },
            "native_episode_receipt": _episode_receipt(
                sample_id, accepted=(index == 1), truncated_planner=(index == 0),
            ),
        }))
        delivered_exact = (
            f"{samples[1]['scenario']}_{samples[1]['action']}" == GOLD[sample_id]
        )
        scores.append({
            "sample_id": sample_id,
            "scenario_action_exact": 1.0 if delivered_exact else 0.0,
            "slu_f1_f1": 1.0 if delivered_exact else 0.2,
        })
        trace_lines += _trace_lines(
            sample_id,
            candidates=(["alarm_query", "alarm_set", "alarm_query"] if index == 0
                        else ["audio_volume_down"]),
            verdict="ACCEPT" if index == 1 else "REVISE-INTENT",
            tokens={"perception": 40, "solver": 30, "review": 20, "planner": 5},
            planner_finish="length" if index == 0 else "stop",
        )
    (directory / f"{RUN_ID}.outputs.jsonl").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    (directory / f"{RUN_ID}.scores.json").write_text(
        json.dumps({FAKE_SCORER_ID: {"per_sample": scores}}), encoding="utf-8"
    )
    (directory / f"{RUN_ID}.trace.jsonl").write_text(
        "\n".join(trace_lines) + "\n", encoding="utf-8"
    )

    repo_root = tmp_path / "studies" / "speech-aware-evidence-acquisition"
    repo_root.mkdir(parents=True)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "datasets.lock.json").write_text("{}", encoding="utf-8")
    (repo_root / "roster.json").write_text(
        json.dumps({
            "items": [{"sample_id": sid, "stratum": sid.split(":")[2]} for sid in ROWS],
            "split_identity_hash": "test-identity-hash",
        }),
        encoding="utf-8",
    )
    (repo_root / "gold.json").write_text(json.dumps(GOLD), encoding="utf-8")
    return data_root, repo_root


def _run(data_root, repo_root, out_dir, *extra):
    _register_fake_scorer()
    argv = [
        "--run", RUN_ID, "--attempt", ATTEMPT_ID,
        "--roster", "roster.json", "--analysis-root", str(out_dir),
        "--scorer-id", FAKE_SCORER_ID, "--samples", str(SAMPLES),
        "--repo-root", str(repo_root), "--data-root", str(data_root),
        "--stage", "all", *extra,
    ]
    assert mod.main(argv) == 0
    return json.loads((out_dir / "pairs.json").read_text(encoding="utf-8"))


def test_pairs_schema_is_bumped_and_the_pair_rows_carry_a_trajectory(sealed, tmp_path):
    data_root, repo_root = sealed
    pairs_doc = _run(data_root, repo_root, tmp_path / "analysis")
    assert pairs_doc["pairs_schema"] == "saea-stage3-rollout-pairs-v2"
    assert pairs_doc["count"] == 1
    pair = pairs_doc["pairs"][0]
    assert pair["sample_id"] == ROWS[0]
    trajectory = pair["trajectory"]
    assert trajectory["available"] is True
    assert trajectory["trace_joined"] is True


def test_the_perception_candidate_list_is_ordered_distinct_with_the_raw_count(
    sealed, tmp_path
):
    data_root, repo_root = sealed
    pairs_doc = _run(data_root, repo_root, tmp_path / "analysis")
    perception = pairs_doc["pairs"][0]["trajectory"]["perception"]
    # Three raw candidates, two distinct, in first-occurrence order.
    assert perception["candidate_intent_ids"] == ["alarm_query", "alarm_set"]
    assert perception["candidate_count"] == 2
    assert perception["raw_candidate_count"] == 3
    assert perception["reading"] == "sealed-perception-response"
    # No gold map supplied -> the question is reported unanswered, not guessed.
    assert perception["gold_intent_known"] is False
    assert perception["gold_intent_in_candidates"] is None


def test_the_gold_intent_enters_only_as_a_boolean_and_a_rank(sealed, tmp_path):
    data_root, repo_root = sealed
    pairs_doc = _run(
        data_root, repo_root, tmp_path / "analysis",
        "--gold-intents", str(repo_root / "gold.json"),
    )
    perception = pairs_doc["pairs"][0]["trajectory"]["perception"]
    assert perception["gold_intent_known"] is True
    assert perception["gold_intent_in_candidates"] is True
    assert perception["gold_intent_rank"] == 1
    assert pairs_doc["trajectory_summary"]["gold_intent_source"] == "gold-intents-file"
    # The label itself never lands in the file.
    assert "alarm_set" not in json.dumps(pairs_doc["pairs"][0]["trajectory"]["delivered"])


def test_the_delivered_path_carries_labels_counts_and_the_below_best_flag(
    sealed, tmp_path
):
    data_root, repo_root = sealed
    pairs_doc = _run(data_root, repo_root, tmp_path / "analysis")
    delivered = pairs_doc["pairs"][0]["trajectory"]["delivered"]
    assert delivered["kind"] == "terminal"
    assert delivered["planner_actions"] == [
        {"action": "REVISE", "legal": True, "disposition": None, "revision_count": 1}
    ]
    assert delivered["revision_count"] == 1
    # ROLL-1 arms no reviewer_verdict, so the label is re-derived from the
    # sealed Reviewer response with the registered closed-vocabulary parser.
    assert delivered["reviewer_verdict_source"] == "derived-from-sealed-response"
    assert delivered["reviewer_verdicts"] == [
        {"visit": 0, "token": "REVISE-INTENT", "disposition": "legal"}
    ]
    # The sealed delivered answer (sample 1) is wrong, the best sample is right.
    assert delivered["delivered_below_best"] is True


def test_per_node_tokens_and_truncation_flags_come_from_the_trace(sealed, tmp_path):
    data_root, repo_root = sealed
    pairs_doc = _run(data_root, repo_root, tmp_path / "analysis")
    trajectory = pairs_doc["pairs"][0]["trajectory"]
    assert trajectory["completion_tokens_by_stage"] == {
        "perception": 40, "solver": 30, "review": 20, "planner": 5,
    }
    assert trajectory["truncated_stages"] == ["planner"]
    planner = [node for node in trajectory["nodes"] if node["stage"] == "planner"][0]
    assert planner["finish_reasons"] == ["length"]
    assert planner["truncated"] is True
    assert trajectory["best"]["sample_index"] == 0
    assert trajectory["worst"]["sample_index"] == 1
    assert len(trajectory["best"]["answer_sha256"]) == 64
    # Each raw Solver sample carries its own contacts in the solver_group
    # custody, so its completion tokens join the trace by request id too.
    assert trajectory["best"]["completion_tokens"] == 30


def test_no_text_of_any_kind_reaches_the_two_written_files(sealed, tmp_path):
    data_root, repo_root = sealed
    out_dir = tmp_path / "analysis"
    _run(data_root, repo_root, out_dir, "--gold-intents", str(repo_root / "gold.json"))
    for name in ("pairs.json", "per_row.json"):
        body = (out_dir / name).read_text(encoding="utf-8")
        assert SECRET_WORD not in body
        assert "rationale" not in body


def test_without_the_trace_the_block_says_so_rather_than_guessing(sealed, tmp_path):
    data_root, repo_root = sealed
    pairs_doc = _run(data_root, repo_root, tmp_path / "analysis-notrace", "--trace", "none")
    trajectory = pairs_doc["pairs"][0]["trajectory"]
    assert trajectory["trace_joined"] is False
    assert trajectory["perception"]["candidate_intent_ids"] == []
    assert trajectory["perception"]["reading"] == "absent"
    assert trajectory["delivered"]["reviewer_verdicts"] == [
        {"visit": 0, "token": None, "disposition": "unavailable"}
    ]
    assert trajectory["completion_tokens_by_stage"] == {}
    assert trajectory["unknown_completion_tokens_by_stage"] == {
        "perception": 1, "solver": 1, "review": 1, "planner": 1,
    }


def test_the_loader_shaped_rows_view_is_readable_by_load_advantage_pairs(
    sealed, tmp_path
):
    from speech_aware_evidence_acquisition.rails.stage3_advantage import (
        load_advantage_pairs,
    )

    data_root, repo_root = sealed
    out_dir = tmp_path / "analysis"
    _run(data_root, repo_root, out_dir)
    loaded = load_advantage_pairs(out_dir / "pairs.json", repo_root=repo_root)
    assert [pair.sample_id for pair in loaded.pairs] == [ROWS[0]]
    assert loaded.pairs[0].best.sample_index == 0
    assert loaded.pairs[0].worst.sample_index == 1


def test_the_pairs_stage_stays_idempotent(sealed, tmp_path):
    data_root, repo_root = sealed
    out_dir = tmp_path / "analysis"
    _run(data_root, repo_root, out_dir)
    before = (out_dir / "pairs.json").read_bytes()
    _run(data_root, repo_root, out_dir)
    assert (out_dir / "pairs.json").read_bytes() == before
