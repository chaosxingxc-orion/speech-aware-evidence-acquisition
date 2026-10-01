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
import re
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

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

    def __init__(
        self, tmp_path: Path, *, stratum: bool = True, roster_id: str = ROSTER_ID,
        ids: list[str] | None = None, scenario_of=None,
        left_correct: set | None = None, right_correct: set | None = None,
        left_delivered: set | None = None, right_delivered: set | None = None,
        stratification: dict | None = None, split_role: str = "discovery",
        bank_roster: str = "train-fold-a",
    ) -> None:
        self.tmp = tmp_path
        self.repo = tmp_path / "repo"
        self.data = tmp_path / "data"
        self.ids = ids if ids is not None else _ids()
        self.scenario_of = scenario_of or _scenario
        self.bank_roster = bank_roster
        self.roster_id = roster_id
        self.split_role = split_role
        # Instance overrides shadow the class defaults above; a caller that passes none of these
        # gets EXACTLY the class-level sets, unchanged (every pre-existing World(...) call).
        self.LEFT_CORRECT = World.LEFT_CORRECT if left_correct is None else left_correct
        self.RIGHT_CORRECT = World.RIGHT_CORRECT if right_correct is None else right_correct
        self.LEFT_DELIVERED = World.LEFT_DELIVERED if left_delivered is None else left_delivered
        self.RIGHT_DELIVERED = World.RIGHT_DELIVERED if right_delivered is None else right_delivered
        items = []
        for i, sample_id in enumerate(self.ids):
            item = {"audio_seconds": 1.0, "headset": i % 2 == 0, "id": sample_id, "sample_id": sample_id,
                    "key": f"slurp:{sample_id}", "utterance_id": sample_id.rsplit(":", 1)[0]}
            if stratum:
                item["stratum"] = self.scenario_of(i)
            items.append(item)
        self.split_hash = core.split_identity_hash(core.prefixed("slurp", self.ids))
        roster = {"carrier_lock_key": "slurp", "items": items, "roster_id": roster_id,
                  "split_identity_hash": self.split_hash, "split_role": split_role}
        if not stratum:
            roster["stratum_withheld_per_item"] = True
        if stratification is not None:
            roster["stratification"] = stratification
        self.roster_rel = "docs/receipts/rosters/unit-fold-a.json"
        _write(self.repo / self.roster_rel, roster)
        self._arm("UNIT-LEFT-V1", "attempt-left", self.LEFT_CORRECT, self.LEFT_DELIVERED, prefill=100)
        self._arm("UNIT-RIGHT-V1", "attempt-right", self.RIGHT_CORRECT, self.RIGHT_DELIVERED, prefill=130)
        bank = [
            json.dumps({"roster": self.bank_roster, "sample_id": s,
                        "gold_intent": f"{self.scenario_of(i)}_query",
                        "plan_class": "CORRECT" if i in self.LEFT_CORRECT else "INTENT-UNCOVERED"})
            for i, s in enumerate(self.ids)
        ]
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
        _write(scores_path, {SCORER: {"per_sample": rows, "aggregate": {
            "identity_check": {"passed": True},
            "official": {"slu_f1": slu, "span_f1": span, "intent_accuracy": intent}}}})
        _write(run_dir / f"{run_id}.outputs.jsonl", "\n".join(
            json.dumps({"sample_id": s, "admitted": True, "text": SENTINEL, "response_text_sha256": "0" * 64})
            for s in self.ids) + "\n")
        _write(run_dir / f"{run_id}.generation-manifest.json", {"cost": {
            "calls_used": 2 * len(self.ids), "prompt_tokens_total": 1000 * len(self.ids),
            "completion_tokens_total": 50 * len(self.ids), "audio_seconds_used": 12.0, "tool_calls": 0}})
        _write(run_dir / f"{run_id}.run-manifest.json", {
            "status": "COMPLETED", "study_repo_dirt": [],
            "scores": {"path": str(scores_path), "sha256": _sha(scores_path)},
            "split": {"count": len(self.ids), "identity_hash": self.split_hash, "role": self.split_role,
                      "name": self.roster_id}})
        _write(run_dir / "score-jobs.jsonl", json.dumps({"job_id": attempt}) + "\n")
        results = []
        for i, s in enumerate(self.ids):
            records = [{"supplied_item_id": f"intent-boundaries::intent-boundary:decoy_{i}", "outcome": "ignore"}]
            if i in delivered:
                records.append({"supplied_item_id": f"intent-boundaries::intent-boundary:{self.scenario_of(i)}_query",
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
        prepared_path = self.data / "prepared" / f"{run_id}.json"
        _write(prepared_path, {"output": {"values": {"perception": {
            row["sample_id"]: [r["supplied_item_id"] for r in row["consumption"]["records"]]
            for row in results
        }}}})
        _write(run_dir / "flight-receipts.json", {"stages": {
            "preflight": {"prepared_artifacts": [{"key": "prepared_phase_supply",
                "relpath": str(prepared_path.relative_to(self.data)), "sha256": _sha(prepared_path)}]},
            "seal": {"phases_sha256": _sha(phases_path),
                     "serving_monitor_summary": {"active_seconds": 360.0, "wall_seconds": 400.0}},
            "run_phases": {"wall_seconds": 400.0, "contacts_per_second": 0.06}}})
        _write(self.data / "attempts" / run_id / f"{attempt}.json", {"state": "FINALIZED"})

    def argv(self, out: Path, *extra: str) -> list[str]:
        return [
            "--stage", "all", "--left-run", "UNIT-LEFT-V1", "--left-attempt", "attempt-left", "--left-label", "left",
            "--right-run", "UNIT-RIGHT-V1", "--right-attempt", "attempt-right", "--right-label", "right",
            "--scorer-id", SCORER, "--expected-split-role", self.split_role, "--roster", self.roster_rel,
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


# --------------------------------------------------------------------------
# --delivery, gold-free, on a final-report roster (recipe step 2: no gold, no gold bank)
# --------------------------------------------------------------------------


def _final_report_roster(ids: list[str], roster_id: str = "UNIT-FINAL-REPORT") -> SimpleNamespace:
    return SimpleNamespace(ids=ids, document={"split_role": "final-report", "roster_id": roster_id})


def test_delivery_gold_free_on_a_final_report_roster(world: World) -> None:
    left = core.load_arm(world.data, core.ArmSpec("left", "UNIT-LEFT-V1", "attempt-left"))
    right = core.load_arm(world.data, core.ArmSpec("right", "UNIT-RIGHT-V1", "attempt-right"))
    block = drv.stage_delivery(SimpleNamespace(data_root=world.data), drv.Extensions(), left, right, _final_report_roster(world.ids))
    assert block["status"] == "AVAILABLE"
    assert block["gold_bank_extension"]["status"] == "NOT_APPLICABLE (final-report)"
    assert block["mismatches"] == []
    left_detail, right_detail = block["detail"]["left"], block["detail"]["right"]
    assert left_detail["rows"] == right_detail["rows"] == 12
    assert left_detail["answered_rows"] == 12 and left_detail["missing_answer_ids"] == []
    assert right_detail["answered_rows"] == 12 and right_detail["missing_answer_ids"] == []
    assert left_detail["boundary_selected_rows"] == 6  # World.LEFT_DELIVERED
    assert right_detail["boundary_selected_rows"] == 10  # World.RIGHT_DELIVERED
    assert left_detail["prepared_supply"]["rows_flown_set_equals_prepared_set"] == 12
    assert right_detail["prepared_supply"]["rows_flown_set_equals_prepared_set"] == 12
    assert left_detail["contacts"]["contacts_equal_sealed_calls"]
    assert right_detail["contacts"]["prompt_tokens_total_equals_sealed_cost"]
    rendered = "\n".join(drv._render_delivery(block))
    assert "Gold-bank extension: NOT_APPLICABLE (final-report)" in rendered
    assert "conversion" not in block  # never the gold-bank shape


def test_delivery_gold_free_reports_a_missing_answer_as_a_mismatch(tmp_path: Path) -> None:
    world = World(tmp_path)
    left_outputs = world.data / "runs" / "UNIT-LEFT-V1" / "attempt-left" / "UNIT-LEFT-V1.outputs.jsonl"
    rows = [json.loads(line) for line in left_outputs.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows[0]["admitted"] = False
    left_outputs.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    left = core.load_arm(world.data, core.ArmSpec("left", "UNIT-LEFT-V1", "attempt-left"))
    right = core.load_arm(world.data, core.ArmSpec("right", "UNIT-RIGHT-V1", "attempt-right"))
    block = drv.stage_delivery(SimpleNamespace(data_root=world.data), drv.Extensions(), left, right, _final_report_roster(world.ids))
    assert block["detail"]["left"]["missing_answer_ids"] == [world.ids[0]]
    assert any("delivered no answer" in m for m in block["mismatches"])



@pytest.mark.parametrize("mode", ["different", "missing-row", "extra-row", "bad-pin", "missing-pin", "duplicate-pin", "escape", "bad-row", "duplicate-value", "extra-phase", "bad-phases"])
def test_final_report_requires_own_prepared_supply(world: World, mode: str) -> None:
    left = core.load_arm(world.data, core.ArmSpec("left", "UNIT-LEFT-V1", "attempt-left"))
    right = core.load_arm(world.data, core.ArmSpec("right", "UNIT-RIGHT-V1", "attempt-right"))
    pins = left.flight_receipts["stages"]["preflight"]["prepared_artifacts"]
    path = world.data / pins[0]["relpath"]
    doc = json.loads(path.read_text())
    values = doc["output"]["values"]["perception"]
    if mode == "different":
        values[world.ids[0]] = ["intent-boundary:changed", SENTINEL]
    elif mode == "missing-row":
        del values[world.ids[0]]
    elif mode == "extra-row":
        values["outside-roster"] = []
    elif mode == "bad-row":
        values[world.ids[0]] = "not-a-list"
    elif mode == "duplicate-value":
        values[world.ids[0]] *= 2
    elif mode == "extra-phase":
        doc["output"]["values"]["solver"] = {}
    elif mode == "bad-phases":
        doc["output"]["values"] = []
    elif mode == "bad-pin":
        pins[0]["sha256"] = "0" * 64
    elif mode == "missing-pin":
        pins.clear()
    elif mode == "duplicate-pin":
        pins.append(dict(pins[0]))
    elif mode == "escape":
        pins[0]["relpath"] = "../outside.json"
    if mode in {"different", "missing-row", "extra-row", "bad-row", "duplicate-value", "extra-phase", "bad-phases"}:
        _write(path, doc)
        pins[0]["sha256"] = _sha(path)
    args = SimpleNamespace(data_root=world.data)
    if mode in {"different", "missing-row"}:
        block = drv.stage_delivery(args, drv.Extensions(), left, right, _final_report_roster(world.ids))
        assert block["detail"]["left"]["prepared_supply"]["rows_flown_set_equals_prepared_set"] == 11
        assert any("prepared supply" in item for item in block["mismatches"])
        assert block["detail"]["right"]["prepared_supply"]["rows_flown_set_equals_prepared_set"] == 12
        encoded = json.dumps(block)
        assert "intent-boundary:changed" not in encoded and SENTINEL not in encoded
    else:
        with pytest.raises(drv.Stage3ReadError, match="prepared supply"):
            drv.stage_delivery(args, drv.Extensions(), left, right, _final_report_roster(world.ids))


@pytest.mark.parametrize("mode", ["missing-row", "empty-row", "empty-phase", "missing-phase"])
def test_prepared_supply_sparse_rows_are_empty_not_unknown(world: World, mode: str) -> None:
    """Match runtime sparse bootstrap semantics without hiding a flown nonempty set."""
    left = core.load_arm(world.data, core.ArmSpec("left", "UNIT-LEFT-V1", "attempt-left"))
    pin = left.flight_receipts["stages"]["preflight"]["prepared_artifacts"][0]
    path = world.data / pin["relpath"]
    doc = json.loads(path.read_text())
    values = doc["output"]["values"]["perception"]
    boundary = {sid: {drv.bare(value): "use" for value in row
                      if drv.bare(value).startswith(drv.BOUNDARY_PREFIX)}
                for sid, row in values.items()}
    if mode in {"missing-row", "empty-row"}:
        values.pop(world.ids[0])
        if mode == "empty-row":
            values[world.ids[0]] = []
        boundary[world.ids[0]] = {}
    else:
        doc["output"]["values"] = {"perception": {}} if mode == "empty-phase" else {}
        boundary = {sid: {} for sid in world.ids}
    _write(path, doc)
    pin["sha256"] = _sha(path)
    report = drv._prepared_boundary_check(world.data, left, boundary, world.ids)
    assert report["rows_flown_set_equals_prepared_set"] == len(world.ids)
    assert report["mismatched_rows"] == 0
    expected_omitted = {"missing-row": 1, "empty-row": 0,
                        "empty-phase": len(world.ids), "missing-phase": len(world.ids)}[mode]
    assert report["omitted_rows_with_empty_default"] == expected_omitted
    boundary[world.ids[0]] = {"intent-boundary:unexpected": "use"}
    assert drv._prepared_boundary_check(world.data, left, boundary, world.ids)["mismatched_rows"] == 1

def test_delivery_still_gold_bank_on_a_non_final_report_roster(world: World) -> None:
    # world's default split_role is "discovery": stage_delivery must take the ORIGINAL gold-bank
    # path, unchanged, whatever the final-report addition does.
    out = world.tmp / "read"
    assert drv.main(world.argv(out, "--delivery")) == 0
    block = json.loads((out / "delivery-conversion.json").read_text())
    assert "conversion" in block and "gold_bank_extension" not in block


def _package(
    world: World, read_notes: str | None, *, resampling_unit: str = "row (paired)",
    arm_extra: dict | None = None, replicate_extra: dict | None = None,
) -> Path:
    package = world.repo / "docs" / "readiness" / "2026-09-27-unit-v1"
    _write(package / "analysis-recipe-v1.json", {
        "recipe_id": "unit-recipe-v1", "title": "Unit cell",
        "run_ids": {"read": "UNIT-READ-V1"},
        "output": {"analysis_root": "analysis/UNIT-READ-V1"},
        "resampling": {"seed": 7, "bootstrap_draws": 200, "unit": resampling_unit},
        "arms": {"arm": {"run_id": "UNIT-RIGHT-V1", "attempt_id": "attempt-right", **(arm_extra or {})},
                 "in_chain_replicate": {"run_id": "UNIT-LEFT-V1", "attempt_id": "attempt-left",
                                        **(replicate_extra or {})},
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


def test_package_mode_refuses_a_column_recipe_that_does_not_resample_by_row(world: World) -> None:
    # owner decision 172 Q4: a same-flight column read resamples by row; declaring a column
    # (arms.arm.column) beside an utterance-clustered resampling.unit is refused before any
    # score is opened.
    out = world.tmp / "pkg-out"
    package = _package(
        world, "REGISTERED BEFORE RESULT READING (root countersigned 2026-09-27 by the coordinator)",
        resampling_unit="utterance (paired)", arm_extra={"column": "plan"},
    )
    assert drv.main(_package_argv(world, package, out)) == 1
    assert not out.exists()


def test_package_mode_threads_column_flags_into_the_driver_argv(world: World, monkeypatch) -> None:
    # owner decision 172 section 3: arms.arm and arms.in_chain_replicate accept "column"; package
    # mode passes them through as --right-column / --left-column without opening any score itself.
    out = world.tmp / "pkg-out"
    package = _package(
        world, "REGISTERED BEFORE RESULT READING (root countersigned 2026-09-27 by the coordinator)",
        arm_extra={"column": "plan"}, replicate_extra={"column": "twin"},
    )
    seen: list = []

    def _fake_run_pair(core_args, ext):
        seen.append(core_args)
        _write(core_args.analysis_root / "verdict.json", {"extensions": []})
        return {"extensions": []}

    monkeypatch.setattr(drv, "run_pair", _fake_run_pair)
    assert drv.main(_package_argv(world, package, out)) == 0
    aa_call = next(c for c in seen if c.left.run_id == "UNIT-LEFT-V1" and c.right.run_id == "UNIT-RIGHT-V1")
    assert aa_call.left.column == "twin"
    assert aa_call.right.column == "plan"


# --------------------------------------------------------------------------
# final-report role: accepted ONLY under all four conditions (owner allowance naming the milestone
# read id, the recipe's own read_driver.scorer, --strata-source scorer, root countersignature)
# --------------------------------------------------------------------------


FINAL_REPORT_COUNTERSIGNED = "REGISTERED BEFORE RESULT READING (root countersigned 2026-09-27 by the coordinator)"
FINAL_REPORT_ALLOWANCE_RELPATH = "docs/receipts/owner/unit-final-report-allowance-v1.json"


@pytest.fixture
def world_final_report(tmp_path: Path) -> World:
    return World(tmp_path, split_role="final-report")


def _final_report_package(
    world: World, read_notes: str | None, *,
    recipe_scorer: str = "slurp-slu-official-test",
    used_ids: list[str] | None = None,
    allowance_ids: list[str] | None = None,
    write_allowance: bool = True,
) -> Path:
    """A milestone package: analysis recipe (naming the arm and its in-chain A/A only, no
    comparator), registered facts (the allowance path and the ids it declares used) and a FAKE
    owner allowance file -- every id is fake, exactly like ``_package``'s own fixtures."""

    package = world.repo / "docs" / "readiness" / "2026-09-27-unit-final-report-v1"
    _write(package / "analysis-recipe-v1.json", {
        "recipe_id": "unit-final-report-recipe-v1", "title": "Unit final-report cell",
        "run_ids": {"read": "UNIT-FR-READ-V1"},
        "output": {"analysis_root": "analysis/UNIT-FR-READ-V1"},
        "resampling": {"seed": 7, "bootstrap_draws": 200, "unit": "row (paired)"},
        "read_driver": {"scorer": recipe_scorer},
        "arms": {"arm": {"run_id": "UNIT-RIGHT-V1", "attempt_id": "attempt-right"},
                 "in_chain_replicate": {"run_id": "UNIT-LEFT-V1", "attempt_id": "attempt-left"}},
    })
    _write(package / "registered-facts-v1.json", {
        "allowance": {
            "path": FINAL_REPORT_ALLOWANCE_RELPATH,
            "read_run_ids_used": used_ids if used_ids is not None else ["UNIT-RIGHT-V1", "UNIT-LEFT-V1"],
        },
    })
    if write_allowance:
        _write(world.repo / FINAL_REPORT_ALLOWANCE_RELPATH, {
            "read_run_ids": allowance_ids if allowance_ids is not None else ["UNIT-RIGHT-V1", "UNIT-LEFT-V1"],
        })
    columns = ("date", "run/experiment id", "execution profile", "scope", "model/tool", "speech carrier + split",
               "split role", "split identity hash", "consumed", "calls", "speech audio seconds", "gpu hours",
               "inherited exposure", "artifacts", "notes")
    lines = ["# Exposure ledger", "", "| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    if read_notes is not None:
        row = {"date": "2026-09-27", "run/experiment id": "UNIT-FR-READ-V1", "execution profile": "model-free-check",
               "consumed": "no", "notes": read_notes}
        lines.append("| " + " | ".join(row.get(c, "-") for c in columns) + " |")
    _write(world.repo / "docs" / "exposure-ledger.md", "\n".join(lines) + "\n")
    return package


def _recording_run_pair(monkeypatch, seen: list) -> None:
    def _fake(core_args, ext):
        seen.append(core_args)
        _write(core_args.analysis_root / "verdict.json", {"extensions": []})
        return {"extensions": []}

    monkeypatch.setattr(drv, "run_pair", _fake)


def test_final_report_condition_a_refuses_an_id_the_allowance_does_not_list(
    world_final_report: World, monkeypatch,
) -> None:
    world = world_final_report
    out = world.tmp / "pkg-out"
    package = _final_report_package(world, FINAL_REPORT_COUNTERSIGNED, allowance_ids=["SOME-OTHER-ID"])
    seen: list = []
    _recording_run_pair(monkeypatch, seen)
    argv = _package_argv(world, package, out) + ["--strata-source", "scorer"]
    assert drv.main(argv) == 1
    assert seen == []


def test_final_report_condition_a_refuses_when_registered_facts_do_not_name_the_id(
    world_final_report: World, monkeypatch,
) -> None:
    world = world_final_report
    out = world.tmp / "pkg-out"
    package = _final_report_package(world, FINAL_REPORT_COUNTERSIGNED, used_ids=["UNIT-LEFT-V1"])
    seen: list = []
    _recording_run_pair(monkeypatch, seen)
    argv = _package_argv(world, package, out) + ["--strata-source", "scorer"]
    assert drv.main(argv) == 1
    assert seen == []


def test_final_report_condition_b_refuses_a_recipe_scorer_that_is_not_official_test(
    world_final_report: World, monkeypatch,
) -> None:
    world = world_final_report
    out = world.tmp / "pkg-out"
    package = _final_report_package(world, FINAL_REPORT_COUNTERSIGNED, recipe_scorer="slurp-slu-official")
    seen: list = []
    _recording_run_pair(monkeypatch, seen)
    argv = _package_argv(world, package, out) + ["--strata-source", "scorer"]
    assert drv.main(argv) == 1
    assert seen == []


def test_final_report_condition_c_refuses_without_strata_source_scorer(
    world_final_report: World, monkeypatch,
) -> None:
    world = world_final_report
    out = world.tmp / "pkg-out"
    package = _final_report_package(world, FINAL_REPORT_COUNTERSIGNED)
    seen: list = []
    _recording_run_pair(monkeypatch, seen)
    assert drv.main(_package_argv(world, package, out)) == 1  # default --strata-source is roster-item
    assert seen == []


def test_final_report_condition_d_refuses_without_countersignature(
    world_final_report: World, monkeypatch,
) -> None:
    world = world_final_report
    out = world.tmp / "pkg-out"
    package = _final_report_package(
        world, "REGISTERED BEFORE RESULT READING (DRAFT, root countersignature pending)",
    )
    seen: list = []
    _recording_run_pair(monkeypatch, seen)
    argv = _package_argv(world, package, out) + ["--strata-source", "scorer"]
    assert drv.main(argv) == 1
    assert seen == []


def test_final_report_accepted_when_all_four_conditions_hold(
    world_final_report: World, monkeypatch,
) -> None:
    world = world_final_report
    out = world.tmp / "pkg-out"
    package = _final_report_package(world, FINAL_REPORT_COUNTERSIGNED)
    seen: list = []
    _recording_run_pair(monkeypatch, seen)
    argv = _package_argv(world, package, out) + ["--strata-source", "scorer"]
    assert drv.main(argv) == 0
    assert len(seen) == 1  # the recipe names no comparator: only vs-aa runs
    core_args = seen[0]
    assert core_args.scorer_id == "slurp-slu-official-test"
    assert core_args.expected_split_role == "final-report"
    assert core_args.left.run_id == "UNIT-LEFT-V1" and core_args.right.run_id == "UNIT-RIGHT-V1"


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


# --------------------------------------------------------------------------
# Driver provenance: recorded, never compared to a frozen fixture
# --------------------------------------------------------------------------
#
# ``driver_sha256`` is the sha256 of the driver script's own bytes
# (``scripts/analysis/slurp_paired_roster_read.py``), not read content: a legitimate driver edit
# changes it while leaving every computed number, id and input hash untouched. ``verdict.json``'s
# ``artifact_sha256`` map (mirrored by the README's own "Artefact hashes" table) moves in lock
# step, since its entries are hashes of files that themselves embed ``driver_sha256``. Both are
# recorded as provenance -- asserted present and well-formed -- and excluded from the
# byte-for-byte comparison, which still applies to everything else.

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ARTEFACT_TABLE_ROW = re.compile(r"^\| (?P<name>[^|]+) \| (?P<digest>[0-9a-f]{64}) \|$")


def _assert_sha256(value: object) -> str:
    assert isinstance(value, str) and _SHA256_RE.match(value), value
    return value


def _canonical_modulo_driver_provenance(payload: dict, *, is_fresh: bool) -> dict:
    cleaned = dict(payload)
    if "driver_sha256" in cleaned:
        digest_value = _assert_sha256(cleaned.pop("driver_sha256"))
        if is_fresh:
            assert digest_value == _sha(CORE_PATH)
    if "artifact_sha256" in cleaned:
        artifact_sha256 = cleaned.pop("artifact_sha256")
        assert isinstance(artifact_sha256, dict) and artifact_sha256
        for value in artifact_sha256.values():
            _assert_sha256(value)
        cleaned["artifact_sha256_names"] = sorted(artifact_sha256)
    return cleaned


def _readme_modulo_driver_provenance(text: str) -> str:
    lines = []
    for line in text.splitlines():
        match = _ARTEFACT_TABLE_ROW.match(line)
        if match:
            _assert_sha256(match["digest"])
            lines.append(f"| {match['name']} | <sha256> |")
        else:
            lines.append(line)
    return "\n".join(lines)


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
        fresh_bytes = (tmp_path / "out" / name).read_bytes()
        sealed_bytes = (sealed / name).read_bytes()
        if name == "README.md":
            assert (_readme_modulo_driver_provenance(fresh_bytes.decode("utf-8"))
                    == _readme_modulo_driver_provenance(sealed_bytes.decode("utf-8"))), name
            continue
        fresh = _canonical_modulo_driver_provenance(json.loads(fresh_bytes), is_fresh=True)
        expected = _canonical_modulo_driver_provenance(json.loads(sealed_bytes), is_fresh=False)
        assert fresh == expected, name


# --------------------------------------------------------------------------
# Population-weighted post-stratification (owner, 2026-09-29): a floored roster's
# natural-mixture slot must be POST-STRATIFIED, never the raw roster mean; DEV-2000-ADDED-shaped
# rosters are not floored and must reproduce raw == post-stratified when weights are proportional.
# --------------------------------------------------------------------------


def test_detect_roster_floored_reads_the_stratification_block() -> None:
    assert drv._detect_roster_floored({}, "auto") is False
    assert drv._detect_roster_floored({"stratification": {}}, "auto") is False
    assert drv._detect_roster_floored({"stratification": {"floor_driven_utterances": 279}}, "auto") is True
    assert drv._detect_roster_floored({"stratification": {"sample_floor_utterances": 5}}, "auto") is True
    assert drv._detect_roster_floored(
        {"stratification": {"even_split_intents": [{"intent": "x"}]}}, "auto"
    ) is True
    # override forces the answer regardless of the receipt's own content
    assert drv._detect_roster_floored({"stratification": {"floor_driven_utterances": 279}}, "false") is False
    assert drv._detect_roster_floored({}, "true") is True
    with pytest.raises(drv.Stage3ReadError):
        drv._detect_roster_floored({}, "bogus")


def test_load_population_weights_drops_and_renormalises_absent_strata(tmp_path: Path) -> None:
    path = tmp_path / "population-counts-v1.json"
    path.write_text(json.dumps({"population_counts": {"a": 80, "b": 15, "c": 5}}), encoding="utf-8")
    weights, source = drv._load_population_weights(str(path), ["a", "b"])
    assert weights == pytest.approx({"a": 80 / 95, "b": 15 / 95})
    assert source["dropped_strata"] == ["c"]
    assert source["strata"] == ["a", "b"]


def test_load_population_weights_accepts_a_bare_mapping_too(tmp_path: Path) -> None:
    path = tmp_path / "counts.json"
    path.write_text(json.dumps({"a": 1, "b": 1}), encoding="utf-8")
    weights, _source = drv._load_population_weights(str(path), ["a", "b"])
    assert weights == pytest.approx({"a": 0.5, "b": 0.5})


def test_load_population_weights_refuses_a_missing_stratum(tmp_path: Path) -> None:
    path = tmp_path / "population-counts-v1.json"
    path.write_text(json.dumps({"a": 1}), encoding="utf-8")
    with pytest.raises(drv.Stage3ReadError):
        drv._load_population_weights(str(path), ["a", "d"])


def test_load_population_weights_resolves_a_relative_path_against_repo_root(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "docs" / "counts.json").write_text(json.dumps({"a": 1, "b": 1}), encoding="utf-8")
    weights, _source = drv._load_population_weights("docs/counts.json", ["a", "b"], repo_root=repo)
    assert weights == pytest.approx({"a": 0.5, "b": 0.5})


def test_post_stratified_intent_statistic_and_levels_match_the_weighted_mean_formula() -> None:
    field = drv.INTENT
    left = {"r1": {field: 0.0}, "r2": {field: 1.0}, "r3": {field: 0.0}, "r4": {field: 1.0}}
    right = {"r1": {field: 1.0}, "r2": {field: 1.0}, "r3": {field: 0.0}, "r4": {field: 0.0}}
    stratum_of = {"r1": "a", "r2": "a", "r3": "b", "r4": "b"}.get
    ids = ["r1", "r2", "r3", "r4"]
    weights = {"a": 0.75, "b": 0.25}
    statistic = drv._post_stratified_intent_statistic(weights, stratum_of, left, right)
    # stratum a: left mean 0.5, right mean 1.0, delta +0.5; stratum b: left mean 0.5, right mean 0.0, delta -0.5
    expected = 0.75 * 0.5 + 0.25 * (-0.5)
    assert statistic(ids) == pytest.approx(expected)
    assert drv._post_stratified_intent_level(weights, stratum_of, left, ids) == pytest.approx(0.75 * 0.5 + 0.25 * 0.5)
    assert drv._post_stratified_intent_level(weights, stratum_of, right, ids) == pytest.approx(0.75 * 1.0 + 0.25 * 0.0)


def test_post_stratified_slu_statistic_weights_totals_before_pooling_not_per_stratum_f1() -> None:
    """The documented formula: weight each stratum's TP/FP/FN TOTALS (divided by its own row
    count) before pooling into one F1 per arm -- never weight each stratum's own F1 score."""

    fields = (("tp",), ("fp",), ("fn",))
    left = {
        "r1": {"tp": 1, "fp": 0, "fn": 1}, "r2": {"tp": 0, "fp": 1, "fn": 0}, "r3": {"tp": 2, "fp": 0, "fn": 0},
        "r4": {"tp": 5, "fp": 5, "fn": 0},
    }
    right = {
        "r1": {"tp": 2, "fp": 0, "fn": 0}, "r2": {"tp": 1, "fp": 0, "fn": 1}, "r3": {"tp": 0, "fp": 2, "fn": 2},
        "r4": {"tp": 10, "fp": 0, "fn": 0},
    }
    stratum_of = {"r1": "a", "r2": "a", "r3": "a", "r4": "b"}.get
    ids = ["r1", "r2", "r3", "r4"]
    weights = {"a": 0.2, "b": 0.8}

    def grouped():
        groups: dict[str, list[str]] = {}
        for sid in ids:
            groups.setdefault(stratum_of(sid), []).append(sid)
        return groups

    def f1_of_weighted_totals(rows):
        tp = fp = fn = 0.0
        for stratum, members in grouped().items():
            n = len(members)
            tp += weights[stratum] * sum(rows[s]["tp"] for s in members) / n
            fp += weights[stratum] * sum(rows[s]["fp"] for s in members) / n
            fn += weights[stratum] * sum(rows[s]["fn"] for s in members) / n
        return 2 * tp / (2 * tp + fp + fn)

    expected = f1_of_weighted_totals(right) - f1_of_weighted_totals(left)
    statistic = drv._post_stratified_slu_statistic(weights, stratum_of, left, right, fields)
    assert statistic(ids) == pytest.approx(expected)
    assert drv._post_stratified_slu_level(weights, stratum_of, left, ids, fields) == pytest.approx(
        f1_of_weighted_totals(left)
    )
    assert drv._post_stratified_slu_level(weights, stratum_of, right, ids, fields) == pytest.approx(
        f1_of_weighted_totals(right)
    )

    # The WRONG formula -- weight each stratum's own F1 SCORE, never its TP/FP/FN totals -- gives
    # a materially different number on this fixture, proving the driver is not accidentally
    # computing that instead.
    def stratum_f1(rows, members):
        tp = sum(rows[s]["tp"] for s in members)
        fp = sum(rows[s]["fp"] for s in members)
        fn = sum(rows[s]["fn"] for s in members)
        return 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 0.0

    def naive_weighted_f1_delta():
        groups = grouped()
        left_naive = sum(weights[s] * stratum_f1(left, m) for s, m in groups.items())
        right_naive = sum(weights[s] * stratum_f1(right, m) for s, m in groups.items())
        return right_naive - left_naive

    assert statistic(ids) != pytest.approx(naive_weighted_f1_delta())


def test_gold_bank_strata_source_produces_an_available_table_when_items_withhold_it(
    tmp_path: Path,
) -> None:
    """A dev/test roster withholds its per-item stratum by design; ``--strata-source gold-bank``
    is the sanctioned fallback (the same offline gold bank ``--delivery`` already reads)."""

    world = World(tmp_path, stratum=False)  # stratum_withheld_per_item: true, as a real test roster is
    out = tmp_path / "read"
    assert drv.main(world.argv(
        out, "--per-scenario", "--strata-source", "gold-bank", "--strata-key", "gold_intent"
    )) == 0
    table = json.loads((out / "per-scenario-tables.json").read_text())
    assert table["status"] == "AVAILABLE"
    assert table["stratum_source"]["field"] == "gold-bank:train-fold-a.gold_intent"
    assert table["strata_rows"] == {f"{s}_query": 4 for s in SCENARIOS}
    for scenario in SCENARIOS:
        members = [i for i in range(12) if _scenario(i) == scenario]
        left = sum(i in World.LEFT_CORRECT for i in members) / 4
        right = sum(i in World.RIGHT_CORRECT for i in members) / 4
        row = table["per_scenario"][f"{scenario}_query"]
        assert row["intent"]["delta_pp"] == pytest.approx(100 * (right - left))


def test_floored_roster_reports_three_different_weightings_and_refuses_raw_as_natural_mixture(
    tmp_path: Path,
) -> None:
    """A floored two-stratum fake (3 'small'-stratum rows, 9 'big'-stratum rows): the RIGHT arm is
    correct on every 'small' row and no 'big' row, the LEFT arm on none, so the per-stratum intent
    delta is +100pp ('small') and 0pp ('big'). The raw roster mean (weighted by the roster's own
    3:9 row split) is +25pp, the equal-stratum mean (unweighted 1:1) is +50pp, and the
    population-weighted post-stratified mean (weights 0.9:0.1) is +90pp -- three DIFFERENT numbers
    by construction, each with a bootstrap CI95 straddling its own point estimate."""

    ids = _ids()
    scenario_of = lambda i: "small" if i < 3 else "big"  # noqa: E731
    world = World(
        tmp_path, stratum=False, roster_id="SLURP-POSTSTRAT-FAKE-V1", ids=ids, scenario_of=scenario_of,
        left_correct=set(), right_correct={0, 1, 2}, left_delivered=set(), right_delivered=set(),
        stratification={"floor_driven_utterances": 3, "sample_floor_utterances": 3},
        split_role="dev", bank_roster="poststrat-fake",
    )
    counts_path = world.repo / "docs" / "readiness" / "unit-poststrat" / "population-counts-v1.json"
    # the bank's gold_intent values carry the "_query" suffix World's bank-building always adds
    # (f"{scenario_of(i)}_query"); the population counts must key on those same strings.
    _write(counts_path, {"population_counts": {"small_query": 90, "big_query": 10}})
    counts_rel = "docs/readiness/unit-poststrat/population-counts-v1.json"
    common = ["--per-scenario", "--strata-source", "gold-bank", "--strata-key", "gold_intent",
              "--gold-bank-roster", "poststrat-fake", "--population-counts", counts_rel]

    # default --weighting is "raw"; the roster is floored, so the read REFUSES rather than
    # silently labelling the raw roster mean "natural_mixture".
    out_refused = tmp_path / "read-refused"
    assert drv.main(world.argv(out_refused, *common)) == 1

    out = tmp_path / "read"
    assert drv.main(world.argv(out, *common, "--weighting", "post-stratified")) == 0
    table = json.loads((out / "per-scenario-tables.json").read_text())
    assert table["status"] == "AVAILABLE" and table["roster_floored"] is True
    assert table["raw"]["label"] == "raw roster mean (not a population estimate)"
    assert table["raw"]["intent"]["delta_pp"] == pytest.approx(25.0)
    assert table["equal_scenario"]["intent"]["delta_pp"] == pytest.approx(50.0)
    assert table["post_stratified"]["status"] == "AVAILABLE"
    assert table["post_stratified"]["intent"]["delta_pp"] == pytest.approx(90.0)
    assert table["natural_mixture"]["selected_weighting"] == "post-stratified"
    assert table["natural_mixture"]["roster_floored"] is True
    assert table["natural_mixture"]["intent"]["delta_pp"] == pytest.approx(90.0)
    for block in (table["raw"], table["post_stratified"], table["equal_scenario"]):
        low, high = block["intent"]["ci95_pp"]
        assert low <= block["intent"]["delta_pp"] <= high
    # the three weightings differ from one another, by construction
    values = {table["raw"]["intent"]["delta_pp"], table["equal_scenario"]["intent"]["delta_pp"],
              table["post_stratified"]["intent"]["delta_pp"]}
    assert len(values) == 3

    # equal-stratum is also a legal --weighting for a floored roster (only "raw" is refused)
    out_eq = tmp_path / "read-eq"
    assert drv.main(world.argv(out_eq, *common, "--weighting", "equal-stratum")) == 0
    table_eq = json.loads((out_eq / "per-scenario-tables.json").read_text())
    assert table_eq["natural_mixture"]["selected_weighting"] == "equal-stratum"
    assert table_eq["natural_mixture"]["intent"]["delta_pp"] == pytest.approx(50.0)


def test_proportional_population_weights_make_post_stratified_equal_raw_on_a_dev2000_added_shaped_roster(
    tmp_path: Path,
) -> None:
    """DEV-2000-ADDED is not floored: its roster is drawn proportionally to the full split, so
    population weights equal to the roster's own per-stratum share must reproduce the raw roster
    mean exactly (owner, 2026-09-29)."""

    world = World(
        tmp_path, stratum=False, roster_id="SLURP-DEV-2000-ADDED-V1", split_role="dev",
        bank_roster="dev2000-added",
    )
    counts_path = world.repo / "docs" / "readiness" / "unit-a2" / "population-counts-v1.json"
    # equal population shares, matching this roster's own equal 4:4:4 per-scenario row split.
    _write(counts_path, {"population_counts": {f"{s}_query": 400 for s in SCENARIOS}})
    counts_rel = "docs/readiness/unit-a2/population-counts-v1.json"
    out = tmp_path / "read"
    assert drv.main(world.argv(
        out, "--per-scenario", "--strata-source", "gold-bank", "--strata-key", "gold_intent",
        "--population-counts", counts_rel, "--weighting", "post-stratified",
    )) == 0
    table = json.loads((out / "per-scenario-tables.json").read_text())
    assert table["roster_floored"] is False
    assert table["post_stratified"]["intent"]["delta_pp"] == pytest.approx(table["raw"]["intent"]["delta_pp"])
    assert table["post_stratified"]["slu_f1"]["delta_pp"] == pytest.approx(table["raw"]["slu_f1"]["delta_pp"])
    assert table["natural_mixture"]["selected_weighting"] == "post-stratified"


# --------------------------------------------------------------------------
# --strata-source scorer (coordinator ruling 2026-09-30): aggregate-only post-stratification
# inside the official-scoring step, equivalent to the gold-bank path
# --------------------------------------------------------------------------


from speech_aware_evidence_acquisition.core import scoring_strata as scs  # noqa: E402


def _fake_gold(world: World):
    """The fake world's gold intent per row -- the SAME strings its bank carries -- handed to the
    scorer step as its gold binding (a real read uses ``official_gold_intents``)."""

    gold = {s: f"{world.scenario_of(i)}_query" for i, s in enumerate(world.ids)}

    def binding(scorer_id: str, sample_ids):
        assert scorer_id == SCORER
        return {s: gold[s] for s in sample_ids}

    return binding


def _in_process_scorer(world: World, calls: list):
    def runner(argv):
        calls.append(list(argv))
        args = scs._parser().parse_args(list(argv))
        try:
            scs.score_paired_strata(
                scorer_id=args.scorer_id, left_scores=Path(args.left_scores),
                right_scores=Path(args.right_scores), roster=Path(args.roster),
                population_counts=Path(args.population_counts), output=Path(args.output),
                cluster_key=args.cluster_key, seed=args.seed, draws=args.draws,
                gold_intents=_fake_gold(world), population_counts_label=args.population_counts_label,
            )
        except scs.ScorerStrataError as error:
            raise drv.Stage3ReadError(f"the scorer's --strata-inside-scorer step refused: {error}")

    return runner


def _floored_world(tmp_path: Path) -> tuple[World, str]:
    world = World(
        tmp_path, stratum=False, roster_id="SLURP-POSTSTRAT-FAKE-V1", ids=_ids(),
        scenario_of=lambda i: "small" if i < 3 else "big",
        left_correct=set(), right_correct={0, 1, 2}, left_delivered=set(), right_delivered=set(),
        stratification={"floor_driven_utterances": 3, "sample_floor_utterances": 3},
        split_role="dev", bank_roster="poststrat-fake",
    )
    counts_rel = "docs/readiness/unit-poststrat/population-counts-v1.json"
    _write(world.repo / counts_rel, {"population_counts": {"small_query": 90, "big_query": 10}})
    return world, counts_rel


def _comparable(table: dict) -> dict:
    return {k: v for k, v in table.items()
            if k not in ("generated_at_utc", "stratum_source", "scorer_strata_receipt")}


def test_scorer_strata_source_reproduces_the_gold_bank_path_exactly(tmp_path: Path, monkeypatch) -> None:
    """The floored two-stratum fake (raw +25 / post-stratified +90 / equal-stratum +50 pp) read
    through ``--strata-source scorer`` equals the gold-bank read float for float -- point deltas,
    CI95s, per-stratum tables, all three weightings -- because both paths call the shared
    estimators with the same sorted ids, strata, clusters, seed and draws (same bootstrap
    indices)."""

    world, counts_rel = _floored_world(tmp_path)
    common = ["--per-scenario", "--population-counts", counts_rel, "--weighting", "post-stratified"]
    out_bank = tmp_path / "read-bank"
    assert drv.main(world.argv(out_bank, *common, "--strata-source", "gold-bank",
                               "--strata-key", "gold_intent", "--gold-bank-roster", "poststrat-fake")) == 0
    calls: list = []
    monkeypatch.setattr(drv, "run_scorer_strata", _in_process_scorer(world, calls))
    out_scorer = tmp_path / "read-scorer"
    assert drv.main(world.argv(out_scorer, *common, "--strata-source", "scorer")) == 0
    assert len(calls) == 1 and calls[0][0] == "--strata-inside-scorer"

    bank = json.loads((out_bank / "per-scenario-tables.json").read_text())
    scorer = json.loads((out_scorer / "per-scenario-tables.json").read_text())
    assert _comparable(scorer) == _comparable(bank)
    assert scorer["raw"]["intent"]["delta_pp"] == pytest.approx(25.0)
    assert scorer["post_stratified"]["intent"]["delta_pp"] == pytest.approx(90.0)
    assert scorer["equal_scenario"]["intent"]["delta_pp"] == pytest.approx(50.0)
    assert scorer["natural_mixture"]["intent"]["delta_pp"] == pytest.approx(90.0)
    assert scorer["stratum_source"]["relpath"] == drv.SCORER_STRATA_FILE
    verdict = json.loads((out_scorer / "verdict.json").read_text())
    assert drv.SCORER_STRATA_FILE in verdict["artifact_sha256"]

    receipt = json.loads((out_scorer / drv.SCORER_STRATA_FILE).read_text())
    assert receipt["schema"] == drv.SCORER_STRATA_SCHEMA
    assert receipt["strata_count"] == 2
    counts = receipt["per_stratum"]["small_query"]["counts"]
    assert counts["left"]["n"] == 3 and counts["left"]["intent_correct"] == 0
    assert counts["right"]["intent_correct"] == 3 and counts["right"]["tp"] == 6.0


def test_scorer_strata_source_writes_no_file_pairing_a_sample_id_with_a_stratum(
    tmp_path: Path, monkeypatch,
) -> None:
    world, counts_rel = _floored_world(tmp_path)
    monkeypatch.setattr(drv, "run_scorer_strata", _in_process_scorer(world, []))
    out = tmp_path / "read-scorer"
    assert drv.main(world.argv(out, "--per-scenario", "--population-counts", counts_rel,
                               "--weighting", "post-stratified", "--strata-source", "scorer")) == 0
    strata = ("small_query", "big_query")
    for path in sorted(p for p in out.rglob("*") if p.is_file()):
        text = path.read_text(encoding="utf-8", errors="replace")
        carries_id = any(sample_id in text for sample_id in world.ids)
        carries_stratum = any(stratum in text for stratum in strata)
        assert not (carries_id and carries_stratum), path.name
    receipt_text = (out / drv.SCORER_STRATA_FILE).read_text(encoding="utf-8")
    assert not any(sample_id in receipt_text for sample_id in world.ids)


def test_scorer_strata_source_refuses_without_population_counts(tmp_path: Path, monkeypatch) -> None:
    world, _ = _floored_world(tmp_path)
    calls: list = []
    monkeypatch.setattr(drv, "run_scorer_strata", _in_process_scorer(world, calls))
    assert drv.main(world.argv(tmp_path / "read", "--per-scenario", "--weighting", "equal-stratum",
                               "--strata-source", "scorer")) == 1
    assert calls == []


def test_scorer_strata_source_refuses_a_roster_without_a_stratification_block(
    tmp_path: Path, monkeypatch,
) -> None:
    world = World(tmp_path, stratum=False, roster_id="SLURP-DEV-2000-ADDED-V1", split_role="dev",
                  bank_roster="dev2000-added")
    counts_rel = "docs/readiness/unit-a2/population-counts-v1.json"
    _write(world.repo / counts_rel, {"population_counts": {f"{s}_query": 400 for s in SCENARIOS}})
    monkeypatch.setattr(drv, "run_scorer_strata", _in_process_scorer(world, []))
    out = tmp_path / "read"
    assert drv.main(world.argv(out, "--per-scenario", "--population-counts", counts_rel,
                               "--weighting", "post-stratified", "--strata-source", "scorer")) == 1
    assert not (out / drv.SCORER_STRATA_FILE).exists()


def test_scorer_strata_source_refuses_a_receipt_that_does_not_match_the_read(
    tmp_path: Path, monkeypatch,
) -> None:
    world, counts_rel = _floored_world(tmp_path)
    inner = _in_process_scorer(world, [])

    def tampering(argv):
        inner(argv)
        path = Path(argv[argv.index("--output") + 1])
        receipt = json.loads(path.read_text())
        receipt["weightings"]["post_stratified"]["intent"]["delta_pp"] = 12.0
        path.write_text(json.dumps(receipt), encoding="utf-8")

    monkeypatch.setattr(drv, "run_scorer_strata", tampering)
    assert drv.main(world.argv(tmp_path / "read", "--per-scenario", "--population-counts", counts_rel,
                               "--weighting", "post-stratified", "--strata-source", "scorer")) == 1
