"""The standard Stage-3 paired read (owner decision 163), on synthetic sealed fixtures and -- where
the data root is materialised -- on the sealed DET and AGREE reads.

``scripts/analysis/stage3_paired_read.py`` imports ``scripts/analysis/slurp_paired_roster_read.py``
unmodified and runs its stages. Without an extension flag its output must be BYTE-IDENTICAL to that
driver's own; with ``--per-scenario`` / ``--delivery`` / ``--frontier`` it adds the per-scenario
tables (both weightings, CI95 by the same resampler), the delivery / conversion counts and the
frontier row. Package mode refuses unless the recipe's READ row is root countersigned.

The synthetic world is twelve TRAIN-shaped rows over three scenarios, two sealed arms with
``phases.json`` consumption records, a wire trace, flight receipts and a bad-case bank block, all
under ``tmp_path``. Zero model, tokenizer, encoder, scorer, network and GPU contacts.
"""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DRIVER_PATH = REPO_ROOT / "scripts" / "analysis" / "stage3_paired_read.py"
CORE_PATH = REPO_ROOT / "scripts" / "analysis" / "slurp_paired_roster_read.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


drv = _load("_test_stage3_paired_read", DRIVER_PATH)
core = _load("_test_stage3_core_reference", CORE_PATH)

SENTINEL = "SENTINEL-DELIVERED-TEXT-7d1f"
SCORER = "slurp-slu-official-train"
ROSTER_ID = "SLURP-EVO-FOLD-A-V2"  # maps to the bank's train-fold-a block
SCENARIOS = ("alarm", "music", "weather")
FILES = ["stop.json", "structural.json", "score-contrasts.json", "per-scenario-tables.json",
         "efficiency.json", "README.md", "verdict.json"]


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = payload if isinstance(payload, str) else json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ids() -> list[str]:
    return [f"slurp:train:{i:06d}:audio-{i}" for i in range(12)]


def _scenario(i: int) -> str:
    return SCENARIOS[i % 3]


def _score_row(sample_id: str, correct: bool) -> dict:
    v = 1.0 if correct else 0.0
    tp, bad = (1.0, 0.0) if correct else (0.0, 1.0)
    return {
        "sample_id": sample_id, "parsed": True, "scenario_action_exact": v, "scenario_exact": v,
        "action_exact": v, "slot_f1_exact_f1": v, "slot_f1_exact_tp": tp, "slot_f1_exact_fp": bad,
        "slot_f1_exact_fn": bad, "slu_f1_f1": v, "slu_f1_word_tp": tp, "slu_f1_word_fp": bad,
        "slu_f1_word_fn": bad, "slu_f1_char_tp": tp, "slu_f1_char_fp": bad, "slu_f1_char_fn": bad,
    }


class World:
    """Left arm correct on rows 0-5; right correct on rows 0-3 and 6-9 (two saves in the delivered
    set, two harms); the gold boundary entry is delivered on rows 0-5 by the left arm and on rows
    0-3 and 6-11 by the right arm."""

    LEFT_CORRECT = set(range(6))
    RIGHT_CORRECT = set(range(4)) | set(range(6, 10))
    LEFT_DELIVERED = set(range(6))
    RIGHT_DELIVERED = set(range(4)) | set(range(6, 12))

    def __init__(self, tmp_path: Path, *, stratum: bool = True) -> None:
        self.tmp = tmp_path
        self.repo = tmp_path / "repo"
        self.data = tmp_path / "data"
        self.ids = _ids()
        items = []
        for i, sample_id in enumerate(self.ids):
            item = {"audio_seconds": 1.0, "headset": i % 2 == 0, "id": sample_id, "sample_id": sample_id,
                    "key": f"slurp:{sample_id}", "utterance_id": sample_id.rsplit(":", 1)[0]}
            if stratum:
                item["stratum"] = _scenario(i)
            items.append(item)
        self.split_hash = core.split_identity_hash(core.prefixed("slurp", self.ids))
        roster = {"carrier_lock_key": "slurp", "items": items, "roster_id": ROSTER_ID,
                  "split_identity_hash": self.split_hash, "split_role": "discovery"}
        if not stratum:
            roster["stratum_withheld_per_item"] = True
        self.roster_rel = "docs/receipts/rosters/unit-fold-a.json"
        _write(self.repo / self.roster_rel, roster)
        self._arm("UNIT-LEFT-V1", "attempt-left", self.LEFT_CORRECT, self.LEFT_DELIVERED, prefill=100)
        self._arm("UNIT-RIGHT-V1", "attempt-right", self.RIGHT_CORRECT, self.RIGHT_DELIVERED, prefill=130)
        bank = [json.dumps({"roster": "train-fold-a", "sample_id": s, "gold_intent": f"{_scenario(i)}_query",
                            "plan_class": "CORRECT" if i < 6 else "INTENT-UNCOVERED"})
                for i, s in enumerate(self.ids)]
        bank.append(json.dumps({"roster": "dev2000-added", "sample_id": "other", "gold_intent": "x"}))
        _write(self.data / drv.DEFAULT_BANK, "\n".join(bank) + "\n")

    def _arm(self, run_id: str, attempt: str, correct: set, delivered: set, *, prefill: int) -> None:
        run_dir = self.data / "runs" / run_id / attempt
        rows = [_score_row(s, i in correct) for i, s in enumerate(self.ids)]
        table = {r["sample_id"]: r for r in rows}
        slu = core.pooled_f1(table, self.ids, core.MICRO_METRICS["slu_f1_micro"])
        span = core.pooled_f1(table, self.ids, core.MICRO_METRICS["span_f1_micro"])
        intent = sum(r["scenario_action_exact"] for r in rows) / len(rows)
        scores_path = run_dir / f"{run_id}.scores.json"
        _write(scores_path, {SCORER: {"per_sample": rows, "aggregate": {"official": {
            "slu_f1": slu, "span_f1": span, "intent_accuracy": intent}}}})
        _write(run_dir / f"{run_id}.outputs.jsonl", "\n".join(
            json.dumps({"sample_id": s, "admitted": True, "text": SENTINEL, "response_text_sha256": "0" * 64})
            for s in self.ids) + "\n")
        _write(run_dir / f"{run_id}.generation-manifest.json", {"cost": {
            "calls_used": 2 * len(self.ids), "prompt_tokens_total": 1000 * len(self.ids),
            "completion_tokens_total": 50 * len(self.ids), "audio_seconds_used": 12.0, "tool_calls": 0}})
        _write(run_dir / f"{run_id}.run-manifest.json", {
            "status": "COMPLETED", "study_repo_dirt": [],
            "scores": {"path": str(scores_path), "sha256": _sha(scores_path)},
            "split": {"count": len(self.ids), "identity_hash": self.split_hash, "role": "discovery",
                      "name": ROSTER_ID}})
        _write(run_dir / "score-jobs.jsonl", json.dumps({"job_id": attempt}) + "\n")
        results = []
        for i, s in enumerate(self.ids):
            records = [{"supplied_item_id": f"intent-boundaries::intent-boundary:decoy_{i}", "outcome": "ignore"}]
            if i in delivered:
                records.append({"supplied_item_id": f"intent-boundaries::intent-boundary:{_scenario(i)}_query",
                                "outcome": "use"})
            results.append({"sample_id": s, "consumption": {"records": records}})
        phases_path = run_dir / f"{run_id}.phases.json"
        _write(phases_path, {"schema": "saea-flight-phase-summaries-v1", "phases": [{"results": results}]})
        trace = []
        for s in self.ids:
            for _ in range(2):
                wire = {"usage": {"prompt_tokens": 500}, "timings": {"prompt_n": prefill, "cache_n": 500 - prefill}}
                trace.append(json.dumps({"channel": "MODEL_WIRE_RESPONSE", "payload": {
                    "sample_id": s, "response_b64": base64.b64encode(json.dumps(wire).encode()).decode()}}))
            trace.append(json.dumps({"channel": "MODEL_REQUEST", "payload": {"text": SENTINEL}}))
        _write(run_dir / f"{run_id}.trace.jsonl", "\n".join(trace) + "\n")
        _write(run_dir / "flight-receipts.json", {"stages": {
            "seal": {"phases_sha256": _sha(phases_path),
                     "serving_monitor_summary": {"active_seconds": 360.0, "wall_seconds": 400.0}},
            "run_phases": {"wall_seconds": 400.0, "contacts_per_second": 0.06}}})
        _write(self.data / "attempts" / run_id / f"{attempt}.json", {"state": "FINALIZED"})

    def argv(self, out: Path, *extra: str) -> list[str]:
        return [
            "--stage", "all", "--left-run", "UNIT-LEFT-V1", "--left-attempt", "attempt-left", "--left-label", "left",
            "--right-run", "UNIT-RIGHT-V1", "--right-attempt", "attempt-right", "--right-label", "right",
            "--scorer-id", SCORER, "--expected-split-role", "discovery", "--roster", self.roster_rel,
            "--cluster-key", "sample_id", "--repo-root", str(self.repo), "--data-root", str(self.data),
            "--seed", "7", "--draws", "300", "--analysis-root", str(out), *extra,
        ]


class Clock:
    """Replays fixed stamps so two runs are comparable byte for byte."""

    queue: list[str] = []

    @classmethod
    def now(cls, tz=None):
        return datetime.fromisoformat(cls.queue.pop(0))


def _stamps(n: int) -> list[str]:
    return [f"2026-09-27T12:00:{i:02d}.000001+00:00" for i in range(n)]


@pytest.fixture
def world(tmp_path: Path) -> World:
    return World(tmp_path)


def _run(module_datetime_owner, fn, n_stamps: int):
    real = module_datetime_owner.datetime
    Clock.queue = _stamps(n_stamps)
    module_datetime_owner.datetime = Clock
    try:
        return fn()
    finally:
        module_datetime_owner.datetime = real


def test_default_output_is_byte_identical_to_the_paired_roster_read(world: World) -> None:
    a, b = world.tmp / "core", world.tmp / "stage3"
    assert _run(core, lambda: core.main(world.argv(a)), 7) == 0
    assert _run(drv.CORE, lambda: drv.main(world.argv(b)), 7) == 0
    assert sorted(p.name for p in a.iterdir()) == sorted(p.name for p in b.iterdir()) == sorted(FILES)
    for name in FILES:
        assert (a / name).read_bytes() == (b / name).read_bytes(), name
    assert json.loads((b / "stop.json").read_text())["driver_sha256"] == _sha(CORE_PATH)


def test_per_scenario_tables_both_weightings(world: World) -> None:
    out = world.tmp / "read"
    assert drv.main(world.argv(out, "--per-scenario")) == 0
    table = json.loads((out / "per-scenario-tables.json").read_text())
    assert table["status"] == "AVAILABLE" and table["strata_rows"] == {s: 4 for s in SCENARIOS}
    ids = world.ids
    for scenario in SCENARIOS:
        members = [i for i in range(12) if _scenario(i) == scenario]
        left = sum(i in World.LEFT_CORRECT for i in members) / 4
        right = sum(i in World.RIGHT_CORRECT for i in members) / 4
        row = table["per_scenario"][scenario]
        assert row["intent"]["delta_pp"] == pytest.approx(100 * (right - left))
        low, high = row["intent"]["ci95_pp"]
        assert low <= row["intent"]["delta_pp"] <= high
    per = [table["per_scenario"][s]["intent"]["delta_pp"] for s in SCENARIOS]
    assert table["equal_scenario"]["intent"]["delta_pp"] == pytest.approx(sum(per) / 3)
    contrast = json.loads((out / "score-contrasts.json").read_text())
    assert table["natural_mixture"]["intent"]["delta_pp"] == contrast["per_row"]["scenario_action_exact"]["delta_pp"]
    assert table["natural_mixture"]["slu_f1"]["ci95_pp"] == contrast["pooled_micro"]["slu_f1_micro"]["cluster_bootstrap"]["ci95_pp"]
    readme = (out / "README.md").read_text()
    assert "| weighting |" in readme and "NOT AVAILABLE" not in readme.split("## Per-scenario")[1].split("##")[0]
    verdict = json.loads((out / "verdict.json").read_text())
    assert verdict["schema"] == drv.SCHEMA_VERDICT and verdict["status"] == "DESCRIPTIVE"
    assert verdict["artifact_sha256"]["per-scenario-tables.json"] == _sha(out / "per-scenario-tables.json")
    assert len(ids) == 12


def test_a_withheld_stratum_keeps_the_core_not_available_record(tmp_path: Path) -> None:
    world = World(tmp_path, stratum=False)
    out = tmp_path / "read"
    assert drv.main(world.argv(out, "--per-scenario")) == 0
    table = json.loads((out / "per-scenario-tables.json").read_text())
    assert table["natural_mixture"]["status"] == "NOT_AVAILABLE"
    assert "NOT AVAILABLE." in (out / "README.md").read_text()


def test_delivery_and_conversion_counts(world: World) -> None:
    out = world.tmp / "read"
    assert drv.main(world.argv(out, "--delivery")) == 0
    block = json.loads((out / "delivery-conversion.json").read_text())
    assert block["status"] == "AVAILABLE"
    assert block["delivered_rows"] == {"left": 6, "right": 10}
    assert block["newly_delivered_rows"] == 6 and block["newly_lost_rows"] == 2
    conv = block["conversion"]
    # newly delivered = rows 6-11, all left-wrong; right correct on 6-9.
    assert conv["newly_delivered_left_wrong"] == 6 and conv["converted_m"] == 4
    assert conv["conversion_rate_pct"] == pytest.approx(400 / 6)
    lost = block["intent_transitions_by_delivery_group"]["newly_lost"]
    assert lost == {"rows": 2, "wrong_to_right": 0, "right_to_wrong": 2, "right_to_right": 0, "wrong_to_wrong": 0}
    assert block["newly_delivered_by_bank_class"] == {"INTENT-UNCOVERED": 6}
    assert block["gold_entry_consumption_outcome_on_newly_delivered_rows"] == {"use": 6}
    assert block["boundary_items_per_row_histogram"]["right"] == {"1": 2, "2": 10}


def test_delivery_refuses_a_bank_that_moved(world: World) -> None:
    out = world.tmp / "read"
    assert drv.main(world.argv(out, "--delivery", "--gold-bank-sha256", "0" * 64)) == 1


def test_frontier_row(world: World) -> None:
    out = world.tmp / "read"
    assert drv.main(world.argv(out, "--frontier")) == 0
    block = json.loads((out / "frontier.json").read_text())
    left, right, delta = block["left"], block["right"], block["delta_right_minus_left"]
    assert left["prefilled_tokens_per_row"] == 200 and right["prefilled_tokens_per_row"] == 260
    assert right["prompt_tokens_per_row"] == 1000 and right["wire"]["prompt_tokens_total_equals_sealed_cost"]
    assert right["wire"]["contacts_equal_sealed_calls"]
    assert right["gpu_hours_per_1080"] == pytest.approx(0.1 * 1080 / 12)
    assert delta["prefilled_tokens_per_row"] == 60
    assert delta["intent_pp"] == pytest.approx(100 * (8 - 6) / 12)
    assert "## Frontier row" in (out / "README.md").read_text()


def test_no_text_is_persisted(world: World) -> None:
    out = world.tmp / "read"
    assert drv.main(world.argv(out, "--stage3")) == 0
    for path in out.rglob("*"):
        assert SENTINEL not in path.read_text(encoding="utf-8"), path
        assert "alarm_query" not in path.read_text(encoding="utf-8"), path


def _package(world: World, read_notes: str | None) -> Path:
    package = world.repo / "docs" / "readiness" / "2026-09-27-unit-v1"
    _write(package / "analysis-recipe-v1.json", {
        "recipe_id": "unit-recipe-v1", "title": "Unit cell",
        "run_ids": {"read": "UNIT-READ-V1"},
        "output": {"analysis_root": "analysis/UNIT-READ-V1"},
        "resampling": {"seed": 7, "bootstrap_draws": 200, "unit": "row (paired)"},
        "arms": {"arm": {"run_id": "UNIT-RIGHT-V1", "attempt_id": "attempt-right"},
                 "in_chain_replicate": {"run_id": "UNIT-LEFT-V1", "attempt_id": "attempt-left"},
                 "comparator": {"run_id": "UNIT-LEFT-V1", "attempt_id": "attempt-left"}},
    })
    columns = ("date", "run/experiment id", "execution profile", "scope", "model/tool", "speech carrier + split",
               "split role", "split identity hash", "consumed", "calls", "speech audio seconds", "gpu hours",
               "inherited exposure", "artifacts", "notes")
    lines = ["# Exposure ledger", "", "| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    if read_notes is not None:
        row = {"date": "2026-09-27", "run/experiment id": "UNIT-READ-V1", "execution profile": "model-free-check",
               "consumed": "no", "notes": read_notes}
        lines.append("| " + " | ".join(row.get(c, "-") for c in columns) + " |")
    _write(world.repo / "docs" / "exposure-ledger.md", "\n".join(lines) + "\n")
    return package


def _package_argv(world: World, package: Path, out: Path) -> list[str]:
    return ["--package", str(package), "--repo-root", str(world.repo), "--data-root", str(world.data),
            "--output-base", str(out)]


def test_package_mode_refuses_a_draft_or_missing_read_row(world: World) -> None:
    out = world.tmp / "pkg-out"
    package = _package(world, "REGISTERED BEFORE RESULT READING (DRAFT, root countersignature pending)")
    assert drv.main(_package_argv(world, package, out)) == 1
    assert not out.exists()
    package = _package(world, None)
    assert drv.main(_package_argv(world, package, out)) == 1


def test_package_mode_runs_both_passes_and_never_overwrites(world: World, capsys) -> None:
    out = world.tmp / "pkg-out"
    package = _package(world, "REGISTERED BEFORE RESULT READING (root countersigned 2026-09-27 by the coordinator)")
    assert drv.main(_package_argv(world, package, out)) == 0
    record = json.loads(capsys.readouterr().out)
    assert record["read_run_id"] == "UNIT-READ-V1" and record["roster"] == world.roster_rel
    assert record["cluster_key"] == "sample_id"
    for name in ("vs-aa", "vs-comparator"):
        assert record["passes"][name]["status"] == "WRITTEN"
        names = {p.name for p in (out / name).iterdir()}
        assert {"frontier.json", "delivery-conversion.json", "slurp_paired_roster_read.py",
                "stage3_paired_read.py"} <= names
    assert drv.main(_package_argv(world, package, out)) == 1  # the pass directories already hold files


def test_the_wrapper_names_the_package_mode_and_the_countersign_refusal() -> None:
    text = (REPO_ROOT / "scripts" / "flights" / "read_paired_cell.sh").read_text(encoding="utf-8")
    assert "stage3_paired_read.py\" --package" in text
    assert "COUNTERSIGNED" in text and "shared-venv hijack" in text


# --------------------------------------------------------------------------
# The sealed reads (data root required)
# --------------------------------------------------------------------------


def _data_root() -> Path | None:
    raw = os.environ.get("SPEECHRL_DATA_DIR", "").strip()
    root = Path(raw) if raw else None
    return root if root is not None and root.is_dir() else None


AGREE = "analysis/SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-PAIRED-ANALYSIS-V1/vs-aa"
SEALED_READS = {
    "det": ("analysis/SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-READ-V1/paired-roster-read", [
        "--left-run", "SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-A-V1",
        "--left-attempt", "attempt-slurp-native-stage3-det-np1-fold-a-50-a-generation-v1",
        "--left-label", "DET pass A (np1, cache off)",
        "--right-run", "SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-B-V1",
        "--right-attempt", "attempt-slurp-native-stage3-det-np1-fold-a-50-b-generation-v1",
        "--right-label", "DET pass B (np1, cache off)",
        "--roster", "docs/receipts/rosters/slurp-stage3-det-fold-a-50-v1.json", "--cluster-key", "utterance_id",
        "--split-identity-hash", "af8154d5dedd3768b145a9d5f5ef6d90eb0ab0f6611a02ee82b2f22fd73a07fa",
        "--seed", "20260915", "--recipe-id", "slurp-stage3-det-np1-fold-a-50-paired-roster-read-v1",
        "--title", "Cell DET: pass B against pass A on the 50-row Fold A prefix (descriptive; the pair is its own control)",
    ]),
    "agree-vs-aa": (AGREE, [
        "--left-run", "SAEA-SLURP-STAGE3-AGREE-AA-FOLD-A-V1",
        "--left-attempt", "attempt-slurp-native-stage3-agree-aa-fold-a-generation-v1",
        "--left-label", "the in-chain A/A (w_agree 0.0, the locked plan's own bytes)",
        "--right-run", "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1",
        "--right-attempt", "attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1",
        "--right-label", "cell AGREE (w_agree 1.0, k 60, fuse 8-1-8)",
        "--roster", "docs/receipts/rosters/slurp-evo-fold-a-v2.json", "--cluster-key", "sample_id",
        "--split-identity-hash", "61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6",
        "--seed", "20260926", "--recipe-id", "slurp-stage3-agree-w1-fold-a-paired-analysis-v1",
        "--title", "Cell AGREE (vs-aa): the intent-boundary agreement term on TRAIN Fold A",
    ]),
}


def _sealed_stamps(sealed: Path) -> list[str]:
    stamps = []
    for name in FILES:
        if name == "README.md":
            line = next(l for l in (sealed / name).read_text(encoding="utf-8").splitlines() if l.startswith("Generated: "))
            stamps.append(line[len("Generated: "):])
        else:
            stamps.append(json.loads((sealed / name).read_text(encoding="utf-8"))["generated_at_utc"])
    return stamps


@pytest.mark.skipif(_data_root() is None, reason="SPEECHRL_DATA_DIR is not materialised on this host")
@pytest.mark.parametrize("case", sorted(SEALED_READS))
def test_the_sealed_reads_reproduce_byte_for_byte(case: str, tmp_path: Path) -> None:
    relpath, args = SEALED_READS[case]
    sealed = _data_root() / relpath
    if not (sealed / "verdict.json").exists():
        pytest.skip(f"{relpath} is not on this data root")
    real = drv.CORE.datetime
    Clock.queue = _sealed_stamps(sealed)
    drv.CORE.datetime = Clock
    try:
        code = drv.main([*args, "--stage", "all", "--scorer-id", SCORER, "--expected-split-role", "discovery",
                         "--draws", "10000", "--repo-root", str(REPO_ROOT), "--data-root", str(_data_root()),
                         "--analysis-root", str(tmp_path / "out")])
    finally:
        drv.CORE.datetime = real
    assert code == 0 and Clock.queue == []
    for name in FILES:
        assert (tmp_path / "out" / name).read_bytes() == (sealed / name).read_bytes(), name
