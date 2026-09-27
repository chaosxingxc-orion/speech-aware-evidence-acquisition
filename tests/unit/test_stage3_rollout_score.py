"""Synthetic tests for ``scripts/analysis/stage3_rollout_score.py`` (S3-3).

A synthetic five-sample (here: three-sample, for test speed) sealed run
directory plus a FAKE registered scorer exercise the full render -> score ->
pairs pipeline without touching any real dataset, model or the registered
official SLURP scorers.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "analysis" / "stage3_rollout_score.py"

_spec = importlib.util.spec_from_file_location("stage3_rollout_score", MODULE_PATH)
mod = importlib.util.module_from_spec(_spec)
sys.modules.setdefault(_spec.name, mod)
_spec.loader.exec_module(mod)  # type: ignore[union-attr]

sys.path.insert(0, str(REPO_ROOT / "src"))
from speech_aware_evidence_acquisition.core.base import SCORERS, CoreError  # noqa: E402

FAKE_SCORER_ID = "test-stage3-fake-scorer-v1"
SAMPLES = 3
ROWS = ("slurp:train:000001:audio-1", "slurp:train:000002:audio-1", "slurp:train:000003:audio-1")
STRATA = {"slurp:train:000001:audio-1": "alarm",
          "slurp:train:000002:audio-1": "audio",
          "slurp:train:000003:audio-1": "audio"}
# The "gold" this fake scorer checks against: row -> the scenario_action that
# counts as correct.
GOLD = {
    "slurp:train:000001:audio-1": "alarm_set",
    "slurp:train:000002:audio-1": "audio_volume_up",
    "slurp:train:000003:audio-1": "audio_volume_up",
}


def fake_scorer(outputs_path, lock, root):
    """A deterministic model-free stand-in for a registered official scorer:
    reads the rendered ``{"sample_id", "text"}`` copy and scores each row's
    ``scenario_action_exact`` / ``slu_f1_f1`` against :data:`GOLD`."""

    rows = [json.loads(line) for line in outputs_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    per_sample = []
    correct = 0
    for row in rows:
        payload = json.loads(row["text"])
        scenario_action = f"{payload['scenario']}_{payload['action']}"
        exact = scenario_action == GOLD[row["sample_id"]]
        correct += 1 if exact else 0
        per_sample.append({
            "sample_id": row["sample_id"],
            "scenario_action_exact": 1.0 if exact else 0.0,
            "slu_f1_f1": 1.0 if exact else 0.2,
            "slot_f1_exact_tp": 1 if exact else 0,
            "slot_f1_exact_fp": 0 if exact else 1,
            "slot_f1_exact_fn": 0,
        })
    return {
        "aggregate": {
            "official": {"slu_f1": correct / len(rows), "intent_accuracy": correct / len(rows)},
            "identity_check": {"passed": True},
            "split_id": "train",
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
        pass  # already registered by an earlier test in this session


def _write_sealed_run(tmp_path: Path, *, row_answers: dict) -> Path:
    """A synthetic ``runs/<RUN>/<ATTEMPT>/`` sealed attempt directory."""

    run_id, attempt_id = "TEST-STAGE3-RUN", "attempt-test-stage3-generation-v1"
    directory = tmp_path / "runs" / run_id / attempt_id
    directory.mkdir(parents=True)

    outputs_lines = []
    scores_per_sample = []
    for sample_id in ROWS:
        samples = row_answers[sample_id]
        assert len(samples) == SAMPLES
        outputs_lines.append(json.dumps({
            "sample_id": sample_id,
            "solver_group": {
                "samples": [
                    {
                        "sample_index": index,
                        "parse_status": "ok" if payload is not None else "malformed",
                        "parsed_answer": payload,
                    }
                    for index, payload in enumerate(samples)
                ],
            },
        }))
        # the "delivered" (sealed) answer is just sample 0, for this synthetic fixture.
        delivered_payload = samples[0]
        delivered_exact = (
            delivered_payload is not None
            and f"{delivered_payload['scenario']}_{delivered_payload['action']}" == GOLD[sample_id]
        )
        scores_per_sample.append({
            "sample_id": sample_id,
            "scenario_action_exact": 1.0 if delivered_exact else 0.0,
            "slu_f1_f1": 1.0 if delivered_exact else 0.2,
        })
    (directory / f"{run_id}.outputs.jsonl").write_text("\n".join(outputs_lines) + "\n", encoding="utf-8")
    (directory / f"{run_id}.scores.json").write_text(
        json.dumps({FAKE_SCORER_ID: {"per_sample": scores_per_sample}}), encoding="utf-8"
    )
    return tmp_path, run_id, attempt_id


def _write_roster(repo_root: Path) -> Path:
    roster = {
        "items": [{"sample_id": sid, "stratum": STRATA[sid]} for sid in ROWS],
        "split_identity_hash": "test-identity-hash",
    }
    path = repo_root / "roster.json"
    path.write_text(json.dumps(roster), encoding="utf-8")
    return path


def _fake_repo_root(tmp_path: Path) -> Path:
    """A synthetic checkout in the registered adjacent layout
    ``<umbrella>/studies/speech-aware-evidence-acquisition/`` (``data.lock.
    umbrella_lock_path``'s own layout assumption), with a trivial empty
    umbrella lock -- the fake scorer never reads it."""

    repo_root = tmp_path / "studies" / "speech-aware-evidence-acquisition"
    repo_root.mkdir(parents=True)
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "datasets.lock.json").write_text("{}", encoding="utf-8")
    return repo_root


def _answer(scenario: str, action: str):
    return {"scenario": scenario, "action": action, "entities": []}


@pytest.fixture()
def sealed_run(tmp_path):
    # Row 1: all three samples agree and are correct -> disagreement 0.
    # Row 2: samples disagree (one correct, two wrong) -> disagreement > 0.
    # Row 3: one sample malformed (parsed_answer None) -> disagreement > 0.
    row_answers = {
        ROWS[0]: [_answer("alarm", "set"), _answer("alarm", "set"), _answer("alarm", "set")],
        ROWS[1]: [_answer("audio", "volume_up"), _answer("audio", "volume_down"), _answer("audio", "volume_down")],
        ROWS[2]: [_answer("audio", "volume_up"), None, _answer("audio", "volume_down")],
    }
    data_root_dir = tmp_path / "data-root"
    data_root_dir.mkdir()
    data_root, run_id, attempt_id = _write_sealed_run(data_root_dir, row_answers=row_answers)
    repo_root = _fake_repo_root(tmp_path)
    roster_path = _write_roster(repo_root)
    return data_root, run_id, attempt_id, repo_root


def test_render_answer_empty_payload_is_the_canonical_empty_form():
    assert mod.render_answer(None) == mod.EMPTY_ANSWER
    empty = json.loads(mod.EMPTY_ANSWER)
    assert empty == {"scenario": "", "action": "", "entities": []}


def test_render_answer_renders_scenario_action_and_entities_sorted():
    payload = {"scenario": "alarm", "action": "set", "entities": [{"type": "time", "filler": "9am"}]}
    text = mod.render_answer(payload)
    assert json.loads(text) == {"scenario": "alarm", "action": "set",
                                 "entities": [{"type": "time", "filler": "9am"}]}


def test_best_worst_deterministic_tie_break_ascending_index():
    samples_correct = [
        {"slu_f1_f1": 0.5, "scenario_action_exact": True},
        {"slu_f1_f1": 0.9, "scenario_action_exact": True},
        {"slu_f1_f1": 0.9, "scenario_action_exact": True},  # ties sample 1 on best
        {"slu_f1_f1": 0.2, "scenario_action_exact": False},
    ]
    best_index, worst_index = mod.best_worst(samples_correct)
    assert best_index == 1  # first (lowest index) among the 0.9 tie
    assert worst_index == 3


def test_render_writes_one_copy_per_sample_index_and_a_manifest(sealed_run, tmp_path):
    data_root, run_id, attempt_id, repo_root = sealed_run
    roster, _, _ = mod.load_roster(repo_root, "roster.json")
    directory = mod.run_dir(data_root, run_id, attempt_id)
    out_dir = tmp_path / "analysis"
    manifest = mod.render(directory, run_id, roster, SAMPLES, out_dir)
    assert manifest["rows"] == 3
    assert manifest["malformed_samples"] == 1
    assert manifest["rows_with_a_malformed_sample"] == 1
    assert set(manifest["copies"]) == {"sample_0", "sample_1", "sample_2"}
    for entry in manifest["copies"].values():
        path = Path(entry["path"])
        assert path.is_file()
        assert mod.sha256_file(path) == entry["sha256"]


def test_render_refuses_a_roster_row_missing_from_outputs(sealed_run, tmp_path):
    data_root, run_id, attempt_id, repo_root = sealed_run
    roster, _, _ = mod.load_roster(repo_root, "roster.json")
    roster["slurp:train:999999:audio-1"] = "weather"
    directory = mod.run_dir(data_root, run_id, attempt_id)
    with pytest.raises(mod.Stage3ScoreError):
        mod.render(directory, run_id, roster, SAMPLES, tmp_path / "analysis2")


def test_full_render_score_pairs_pipeline(sealed_run, tmp_path):
    _register_fake_scorer()
    data_root, run_id, attempt_id, repo_root = sealed_run
    out_dir = tmp_path / "analysis"
    argv = [
        "--run", run_id, "--attempt", attempt_id,
        "--roster", "roster.json", "--analysis-root", str(out_dir),
        "--scorer-id", FAKE_SCORER_ID, "--samples", str(SAMPLES),
        "--repo-root", str(repo_root), "--data-root", str(data_root),
        "--stage", "all",
    ]
    assert mod.main(argv) == 0

    per_row = json.loads((out_dir / "per_row.json").read_text(encoding="utf-8"))
    pairs_doc = json.loads((out_dir / "pairs.json").read_text(encoding="utf-8"))

    assert per_row["contacts"] == {"model": 0, "tokenizer": 0, "encoder": 0, "asr": 0,
                                    "server": 0, "network": 0, "scorer": SAMPLES}
    assert len(per_row["rows"]) == 3

    row0 = next(r for r in per_row["rows"] if r["sample_id"] == ROWS[0])
    assert row0["disagreement"] == 0.0  # all three samples agree and are correct

    row1 = next(r for r in per_row["rows"] if r["sample_id"] == ROWS[1])
    assert row1["disagreement"] > 0.0
    assert row1["best_index"] == 0  # the only correct sample

    # disagreeing rows (2 and 3) are exactly pairs.json's rows; row 1 is excluded.
    pair_ids = {p["sample_id"] for p in pairs_doc["pairs"]}
    assert pair_ids == {ROWS[1], ROWS[2]}
    assert pairs_doc["count"] == 2

    coverage = pairs_doc["coverage_by_stratum"]
    assert coverage["alarm"]["rows"] == 1
    assert coverage["alarm"]["disagreeing_rows"] == 0
    assert coverage["audio"]["rows"] == 2
    assert coverage["audio"]["disagreeing_rows"] == 2

    # idempotent re-run: stage-by-stage should read back cached files, not
    # rewrite them, and produce byte-identical results.
    before = (out_dir / "per_row.json").read_bytes()
    assert mod.main(argv) == 0
    assert (out_dir / "per_row.json").read_bytes() == before


def test_pairs_stage_alone_reuses_a_prior_render_and_score(sealed_run, tmp_path):
    _register_fake_scorer()
    data_root, run_id, attempt_id, repo_root = sealed_run
    out_dir = tmp_path / "analysis-staged"
    base_argv = [
        "--run", run_id, "--attempt", attempt_id,
        "--roster", "roster.json", "--analysis-root", str(out_dir),
        "--scorer-id", FAKE_SCORER_ID, "--samples", str(SAMPLES),
        "--repo-root", str(repo_root), "--data-root", str(data_root),
    ]
    assert mod.main(base_argv + ["--stage", "render"]) == 0
    assert mod.main(base_argv + ["--stage", "score"]) == 0
    assert mod.main(base_argv + ["--stage", "pairs"]) == 0
    assert (out_dir / "pairs.json").is_file()


def test_pairs_stage_without_a_prior_render_refuses(tmp_path, sealed_run):
    data_root, run_id, attempt_id, repo_root = sealed_run
    out_dir = tmp_path / "analysis-empty"
    argv = [
        "--run", run_id, "--attempt", attempt_id,
        "--roster", "roster.json", "--analysis-root", str(out_dir),
        "--scorer-id", FAKE_SCORER_ID,
        "--repo-root", str(repo_root), "--data-root", str(data_root),
        "--stage", "pairs",
    ]
    with pytest.raises(mod.Stage3ScoreError):
        mod.main(argv)


# ---------------------------------------------------------------------------
# The 2026-09-26 fan-out: one COMPLETE scoring per worker, never a shard.
# ---------------------------------------------------------------------------


def _render_and_score(sealed_run, tmp_path, name: str, workers: int):
    _register_fake_scorer()
    data_root, run_id, attempt_id, repo_root = sealed_run
    roster, _, _ = mod.load_roster(repo_root, "roster.json")
    directory = mod.run_dir(data_root, run_id, attempt_id)
    out = tmp_path / name
    manifest = mod.render(directory, run_id, roster, SAMPLES, out)
    scored = mod.score(FAKE_SCORER_ID, manifest, out, {}, data_root, workers=workers)
    return out, manifest, scored


def _without_timing(scored):
    return {
        name: {key: value for key, value in side.items() if key != "scoring_seconds"}
        for name, side in scored.items()
    }


@pytest.mark.parametrize("workers", [1, 2, 4])
def test_score_stage_is_worker_count_invariant(sealed_run, tmp_path, workers):
    """One complete scoring per copy; the numbers cannot depend on how many
    of them ran at once, and the copy names come back sorted, never in
    completion order."""

    out, _manifest, scored = _render_and_score(sealed_run, tmp_path, f"w{workers}", workers)
    assert list(scored) == [f"sample_{index}" for index in range(SAMPLES)]
    serial_out, _m, serial = _render_and_score(sealed_run, tmp_path, f"ref{workers}", 1)
    assert _without_timing(scored) == _without_timing(serial)
    for index in range(SAMPLES):
        stem = f"sample_{index}-{FAKE_SCORER_ID}-scores.json"
        assert (out / stem).read_bytes() == (serial_out / stem).read_bytes(), stem


def test_score_stage_verifies_every_copy_before_the_first_scoring(sealed_run, tmp_path):
    """A drifted copy must refuse BEFORE any scorer contact, not after some."""

    _register_fake_scorer()
    data_root, run_id, attempt_id, repo_root = sealed_run
    roster, _, _ = mod.load_roster(repo_root, "roster.json")
    directory = mod.run_dir(data_root, run_id, attempt_id)
    out = tmp_path / "drift"
    manifest = mod.render(directory, run_id, roster, SAMPLES, out)
    last = Path(manifest["copies"][f"sample_{SAMPLES - 1}"]["path"])
    last.write_text(last.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(mod.Stage3ScoreError, match="drifted from its render manifest"):
        mod.score(FAKE_SCORER_ID, manifest, out, {}, data_root, workers=4)
    assert not list(out.glob(f"*-{FAKE_SCORER_ID}-scores.json"))


def test_score_stage_reuses_the_cached_result_file_at_any_worker_count(sealed_run, tmp_path):
    data_root = sealed_run[0]
    out, manifest, first = _render_and_score(sealed_run, tmp_path, "cached", 4)
    second = mod.score(FAKE_SCORER_ID, manifest, out, {}, data_root, workers=4)
    assert all(side["scoring_seconds"] == 0.0 for side in second.values())
    assert _without_timing(second) == _without_timing(first)
