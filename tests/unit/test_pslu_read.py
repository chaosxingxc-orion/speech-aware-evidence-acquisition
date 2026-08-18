"""``analysis.pslu_read``: the P-SLU pinned offline read suite.

Engineering-only, zero live model contact -- every fixture here is a
hand-authored synthetic attempt directory. This module is NEVER pointed at
the real flight attempt directory
(``$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pslu-n60/``); that is a separate,
one-shot registered read.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.pslu_read import (
    PsluReadError,
    RecheckMismatch,
    arm_copy_rate,
    build_pslu_report,
    count_induced_substitutions,
    main as pslu_read_main,
)
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpAdapter
from speech_aware_evidence_acquisition.rails.probes.pslu_flight import pslu_supply_packet
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity, parse_slu_response

ARMS = ("A0", "A1", "A1p", "A2", "A3", "A4")
SLURP_IDS = (101, 900, 901)


# ---------------------------------------------------------------------------
# Synthetic SLURP world: 3 devel samples -- 101 (scenario "iot", one gold
# entity house_place=kitchen) plus two "neutral" no-entity samples (900, 901,
# scenario "email") every arm can trivially answer identically, so a
# fixture's own signal lives entirely in how the six arms answer sample 101.
# ---------------------------------------------------------------------------


def _write_flac(path: Path, *, sample_rate_hz: int = 16000, seconds: float = 0.2) -> None:
    import numpy as np
    import soundfile as sf

    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(sample_rate_hz * seconds)
    sf.write(str(path), np.zeros(frames, dtype="float32"), sample_rate_hz, format="FLAC")


def _tokens(*surfaces: str) -> list[dict]:
    return [{"surface": s, "id": i, "lemma": s, "pos": "NN"} for i, s in enumerate(surfaces)]


DEVEL_RECORDS = [
    {
        "slurp_id": 101,
        "sentence": "turn on the kitchen lights",
        "sentence_annotation": "turn on the [house_place : kitchen] lights",
        "intent": "iot_hue_lighton",
        "scenario": "iot",
        "action": "hue_lighton",
        "tokens": _tokens("turn", "on", "the", "kitchen", "lights"),
        "entities": [{"span": [3], "type": "house_place"}],
        "recordings": [{"file": "audio-101.flac", "wer": 0.0, "ent_wer": 0.0, "status": "correct"}],
    },
    {
        "slurp_id": 900,
        "sentence": "check my email",
        "sentence_annotation": "check my email",
        "intent": "email_query",
        "scenario": "email",
        "action": "query",
        "tokens": _tokens("check", "my", "email"),
        "entities": [],
        "recordings": [{"file": "audio-900.flac", "wer": 0.0, "ent_wer": None, "status": "correct"}],
    },
    {
        "slurp_id": 901,
        "sentence": "any new email",
        "sentence_annotation": "any new email",
        "intent": "email_query",
        "scenario": "email",
        "action": "query",
        "tokens": _tokens("any", "new", "email"),
        "entities": [],
        "recordings": [{"file": "audio-901.flac", "wer": 0.0, "ent_wer": None, "status": "correct"}],
    },
]

# Deliberately excludes "kitchen" (the true gold filler) from the "iot"
# roster -- a SUPPLY-CONVERTS fixture's correct answer therefore proves the
# arm answered correctly, not merely echoed a roster value; a COPY-TRAP
# fixture can then supply a WRONG roster value ("bedroom"/"office") for the
# induced-substitution clause to catch.
ROSTER_DOC = {
    "probe": "P-SLU",
    "legality_tier": "legal",
    "train_synthetic_refused": {"train_jsonl_overlap_with_devel": 0},
    "arms": {
        "A1_scenario_roster": {
            "rosters": {
                "iot": [["house_place", "bedroom"], ["house_place", "office"]],
                "email": [["email_folder", "inbox"]],
            }
        },
        "A2_global_type_vocabulary": {"types": ["house_place", "email_folder"]},
        "A3_full_ontology_dose_capped": {"roster": [["house_place", "bedroom"], ["email_folder", "inbox"]]},
        "A4_deranged": {"mapping": {"iot": "email", "email": "iot"}},
    },
}


class PsluWorld:
    def __init__(self, tmp_path: Path) -> None:
        self.data_root = tmp_path / "data"
        self.lock_path = tmp_path / "lock.json"
        audio_root = self.data_root / "datasets" / "slurp"
        metadata_dir = audio_root / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        (metadata_dir / "devel.jsonl").write_text(
            "\n".join(json.dumps(r) for r in DEVEL_RECORDS) + "\n", encoding="utf-8"
        )
        real_dir = audio_root / "slurp_real"
        for record in DEVEL_RECORDS:
            for recording in record["recordings"]:
                _write_flac(real_dir / recording["file"])
        lock_doc = {
            "datasets": [
                {
                    "name": "slurp",
                    "kind": "dataset",
                    "local_subdir": "repos/slurp/scripts/audio",
                    "license": "mixed: textual part CC BY 4.0, audio part CC BY-NC 4.0",
                    "annotations": {"governed_copy": "datasets/slurp/metadata"},
                }
            ]
        }
        self.lock_path.write_text(json.dumps(lock_doc), encoding="utf-8")
        self.lock = load_lock(self.lock_path)
        self.adapter = SlurpAdapter(self.lock, self.data_root)
        samples = {s.sample_id: s for s in self.adapter.load_split("devel")}
        self.sid = {slurp_id: self._find(samples, slurp_id) for slurp_id in SLURP_IDS}

        self.roster_table_path = tmp_path / "rosters.json"
        self.roster_table_path.write_text(json.dumps(ROSTER_DOC), encoding="utf-8")
        from speech_aware_evidence_acquisition.rails.probes.pslu_flight import load_pslu_rosters

        self.rosters = load_pslu_rosters(self.roster_table_path)

        self.sample_manifest_path = tmp_path / "manifest.json"
        manifest_doc = {
            "probe": "P-SLU",
            "seed": 20260807,
            "split_identity_hash": "a" * 64,
            "items": [{"sample_id": self.sid[slurp_id].sample_id} for slurp_id in SLURP_IDS],
        }
        self.sample_manifest_path.write_text(json.dumps(manifest_doc), encoding="utf-8")

    @staticmethod
    def _find(samples: dict, slurp_id: int):
        needle = f":{slurp_id:06d}:"
        for sample_id, sample in samples.items():
            if needle in sample_id:
                return sample
        raise KeyError(slurp_id)


@pytest.fixture()
def pslu_world(tmp_path):
    return PsluWorld(tmp_path)


def _resp(scenario: str, action: str, entities: list[tuple[str, str]]) -> str:
    return json.dumps(
        {"scenario": scenario, "action": action, "entities": [{"type": t, "filler": f} for t, f in entities]}
    )


NEUTRAL = _resp("email", "query", [])
NEUTRAL_CHANGED = _resp("alarm", "set", [])


def _scenario_for_arm(arm: str, gold_scenario: str, predicted_scenario) -> str | None:
    if arm in ("A1", "A4"):
        return gold_scenario
    if arm in ("A1p", "A2", "A3"):
        return predicted_scenario
    return None


def _row(world: PsluWorld, sample, arm: str, response_text: str, *, predicted_scenario, silence_swapped=False) -> dict:
    scenario = _scenario_for_arm(arm, sample.scenario, predicted_scenario)
    supply = None if arm == "A0" else pslu_supply_packet(arm, scenario=scenario, rosters=world.rosters)
    messages = list(world.adapter.assemble_prompt(sample, supply))
    if silence_swapped:
        relpath = f"derived/silence/{sample.sample_id.replace(':', '_')}.flac"
        user_message = messages[1]
        new_content = []
        for part in user_message["content"]:
            if isinstance(part, dict) and part.get("type") == "input_audio":
                new_content.append({**part, "media_relpath": relpath})
            else:
                new_content.append(dict(part))
        messages[1] = {"role": "user", "content": new_content}
    metrics = dict(world.adapter.score(sample, response_text))
    consumption = world.adapter.extract_consumption(sample, supply, response_text).as_json()
    phase1_parsed = None
    if arm == "A0":
        _, _, _, phase1_parsed = parse_slu_response(response_text)
    return {
        "arm": arm,
        "sample_id": sample.sample_id,
        "silence_swapped": silence_swapped,
        "phase1_scenario_parsed": phase1_parsed,
        "messages": messages,
        "response_text": response_text,
        "metrics": metrics,
        "consumption": consumption,
    }


def _build_rows(
    world: PsluWorld,
    responses: dict[tuple[int, str], str],
    predicted_scenario_by_slurp_id: dict[int, str],
    silence_responses: dict[int, str],
) -> tuple[list[dict], dict[str, str]]:
    predicted_scenarios: dict[str, str] = {}
    for slurp_id in SLURP_IDS:
        predicted_scenarios[world.sid[slurp_id].sample_id] = predicted_scenario_by_slurp_id[slurp_id]

    rows: list[dict] = []
    for slurp_id in SLURP_IDS:
        sample = world.sid[slurp_id]
        predicted_scenario = predicted_scenario_by_slurp_id[slurp_id]
        for arm in ARMS:
            rows.append(_row(world, sample, arm, responses[(slurp_id, arm)], predicted_scenario=predicted_scenario))
    for slurp_id in SLURP_IDS:
        sample = world.sid[slurp_id]
        predicted_scenario = predicted_scenario_by_slurp_id[slurp_id]
        rows.append(
            _row(
                world, sample, "A1p", silence_responses[slurp_id],
                predicted_scenario=predicted_scenario, silence_swapped=True,
            )
        )
    return rows, predicted_scenarios


def _write_attempt_dir(path: Path, rows: list[dict], predicted_scenarios: dict, *, status="COMPLETED", error=None) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    with (path / "outputs.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    (path / "predicted-scenarios.json").write_text(json.dumps(predicted_scenarios), encoding="utf-8")
    (path / "flight-receipt.json").write_text(json.dumps({"status": status, "error": error}), encoding="utf-8")
    return path


def _neutral_responses(overrides: dict[tuple[int, str], str]) -> dict[tuple[int, str], str]:
    """900/901 tied identically NEUTRAL across every arm by default; only
    sample 101's per-arm responses vary between fixtures."""

    responses = {(slurp_id, arm): NEUTRAL for slurp_id in (900, 901) for arm in ARMS}
    responses.update(overrides)
    return responses


_PREDICTED_SCENARIOS = {101: "iot", 900: "email", 901: "email"}


def _build_report(world: PsluWorld, tmp_path: Path, rows, predicted_scenarios):
    attempt_dir = _write_attempt_dir(tmp_path / "attempt", rows, predicted_scenarios)
    return build_pslu_report(
        attempt_dir,
        world.lock,
        world.data_root,
        sample_manifest_path=world.sample_manifest_path,
        roster_table_path=world.roster_table_path,
    )


# ---------------------------------------------------------------------------
# Branch-rule fixtures.
# ---------------------------------------------------------------------------


def test_lands_supply_converts(pslu_world, tmp_path):
    a0_101 = _resp("iot", "turn_on_generic", [])
    correct_101 = _resp("iot", "hue_lighton", [("house_place", "kitchen")])
    responses = _neutral_responses(
        {
            (101, "A0"): a0_101,
            (101, "A1"): correct_101,
            (101, "A1p"): correct_101,
            (101, "A2"): a0_101,
            (101, "A3"): a0_101,
            (101, "A4"): a0_101,
        }
    )
    silence_responses = {101: NEUTRAL_CHANGED, 900: NEUTRAL_CHANGED, 901: NEUTRAL_CHANGED}
    rows, predicted_scenarios = _build_rows(pslu_world, responses, _PREDICTED_SCENARIOS, silence_responses)
    report = _build_report(pslu_world, tmp_path, rows, predicted_scenarios)

    # VOID clause 3: every recomputed TP/FP/FN/parsed ingredient reproduces
    # score_slu exactly against the embedded metrics (the module's own
    # score_slu reuse, applied to the SAME response text/gold this report
    # loaded) -- proves reproduction on this fixture.
    assert report.recheck_mismatches == ()
    assert report.harness_defect_reasons == ()

    verdict = report.branch_verdict
    assert verdict.voided is False
    assert verdict.copy_trap is False
    assert verdict.supply_converts is True
    assert verdict.overall == "SUPPLY-CONVERTS"
    assert all(c.verdict == "met" for c in verdict.supply_converts_clauses)

    a0 = report.aggregates["A0"]
    a1p = report.aggregates["A1p"]
    assert a0.slu_f1_f1 == pytest.approx(0.0)
    assert a1p.slu_f1_f1 - a0.slu_f1_f1 >= 0.05
    assert a1p.copy_rate < 0.50


def test_lands_copy_trap_via_induced_substitution(pslu_world, tmp_path):
    a0_101 = _resp("iot", "turn_on_generic", [])
    wrong_via_roster_101 = _resp("iot", "hue_lighton", [("house_place", "bedroom")])
    responses = _neutral_responses(
        {
            (101, "A0"): a0_101,
            (101, "A1"): a0_101,
            (101, "A1p"): wrong_via_roster_101,
            (101, "A2"): a0_101,
            (101, "A3"): a0_101,
            (101, "A4"): a0_101,
        }
    )
    silence_responses = {101: NEUTRAL_CHANGED, 900: NEUTRAL_CHANGED, 901: NEUTRAL_CHANGED}
    rows, predicted_scenarios = _build_rows(pslu_world, responses, _PREDICTED_SCENARIOS, silence_responses)
    report = _build_report(pslu_world, tmp_path, rows, predicted_scenarios)

    assert report.recheck_mismatches == ()
    assert report.harness_defect_reasons == ()

    verdict = report.branch_verdict
    assert verdict.voided is False
    assert verdict.copy_trap is True
    assert verdict.overall == "COPY-TRAP"
    induced_clause = next(c for c in verdict.copy_trap_clauses if "induced-substitution" in c.clause_text)
    assert induced_clause.verdict == "met"

    assert report.aggregates["A1p"].induced_substitution_count == 1


def test_lands_void_by_silence_swap_unanimous_unchanged(pslu_world, tmp_path):
    """Reuses the SUPPLY-CONVERTS-worthy responses (proving VOID overrides
    an otherwise-affirming numeric result), but every silence-swap answer
    is identical to its real-audio A1' counterpart."""

    a0_101 = _resp("iot", "turn_on_generic", [])
    correct_101 = _resp("iot", "hue_lighton", [("house_place", "kitchen")])
    responses = _neutral_responses(
        {
            (101, "A0"): a0_101,
            (101, "A1"): correct_101,
            (101, "A1p"): correct_101,
            (101, "A2"): a0_101,
            (101, "A3"): a0_101,
            (101, "A4"): a0_101,
        }
    )
    silence_responses = {101: correct_101, 900: NEUTRAL, 901: NEUTRAL}  # unanimous unchanged
    rows, predicted_scenarios = _build_rows(pslu_world, responses, _PREDICTED_SCENARIOS, silence_responses)
    report = _build_report(pslu_world, tmp_path, rows, predicted_scenarios)

    assert report.recheck_mismatches == ()
    assert report.harness_defect_reasons == ()
    assert all(c.unchanged for c in report.silence_comparisons)

    verdict = report.branch_verdict
    assert verdict.voided is True
    assert verdict.overall == "VOID"
    silence_clause = next(c for c in verdict.void_clauses if "silence-swap" in c.clause_text)
    assert silence_clause.verdict == "met"
    harness_clause = next(c for c in verdict.void_clauses if c.clause_text == "harness defect")
    assert harness_clause.verdict == "not_met"
    recheck_clause = next(c for c in verdict.void_clauses if "recheck" in c.clause_text)
    assert recheck_clause.verdict == "not_met"


def test_lands_inert(pslu_world, tmp_path):
    identical_wrong_101 = _resp("iot", "hue_lighton", [("house_place", "attic")])
    responses = _neutral_responses({(101, arm): identical_wrong_101 for arm in ARMS})
    silence_responses = {101: NEUTRAL_CHANGED, 900: NEUTRAL_CHANGED, 901: NEUTRAL_CHANGED}
    rows, predicted_scenarios = _build_rows(pslu_world, responses, _PREDICTED_SCENARIOS, silence_responses)
    report = _build_report(pslu_world, tmp_path, rows, predicted_scenarios)

    assert report.recheck_mismatches == ()
    assert report.harness_defect_reasons == ()

    verdict = report.branch_verdict
    assert verdict.voided is False
    assert verdict.copy_trap is False
    assert verdict.supply_converts is False
    assert verdict.inert is True
    assert verdict.overall == "INERT"
    assert verdict.dose_confirm.verdict == "not_met"


def test_lands_dose_confirm_secondary(pslu_world, tmp_path):
    a0_101 = _resp("iot", "turn_on_generic", [])
    correct_101 = _resp("iot", "hue_lighton", [("house_place", "kitchen")])
    responses = _neutral_responses(
        {
            (101, "A0"): a0_101,
            (101, "A1"): a0_101,
            (101, "A1p"): a0_101,  # tied with A0 -> SUPPLY-CONVERTS/COPY-TRAP clause 1 both guarded off
            (101, "A2"): correct_101,  # A2 improves ...
            (101, "A3"): a0_101,  # ... A3 does not -> "A3 underperforms A2"
            (101, "A4"): a0_101,
        }
    )
    silence_responses = {101: NEUTRAL_CHANGED, 900: NEUTRAL_CHANGED, 901: NEUTRAL_CHANGED}
    rows, predicted_scenarios = _build_rows(pslu_world, responses, _PREDICTED_SCENARIOS, silence_responses)
    report = _build_report(pslu_world, tmp_path, rows, predicted_scenarios)

    assert report.recheck_mismatches == ()
    assert report.harness_defect_reasons == ()

    verdict = report.branch_verdict
    assert verdict.voided is False
    assert verdict.copy_trap is False
    assert verdict.supply_converts is False
    assert verdict.inert is False  # A2's own gain is well above the +0.02 floor
    assert verdict.dose_confirm.verdict == "met"
    assert "DOSE-CONFIRM" in verdict.overall
    assert report.aggregates["A3"].slu_f1_f1 < report.aggregates["A2"].slu_f1_f1


# ---------------------------------------------------------------------------
# VOID via a deliberately corrupted embedded metric (the recheck clause).
# ---------------------------------------------------------------------------


def test_lands_void_via_recheck_mismatch(pslu_world, tmp_path):
    a0_101 = _resp("iot", "turn_on_generic", [])
    responses = _neutral_responses({(101, arm): a0_101 for arm in ARMS})
    silence_responses = {101: NEUTRAL_CHANGED, 900: NEUTRAL_CHANGED, 901: NEUTRAL_CHANGED}
    rows, predicted_scenarios = _build_rows(pslu_world, responses, _PREDICTED_SCENARIOS, silence_responses)

    # Corrupt ONE row's embedded metrics -- simulates a harness scoring bug.
    target = next(r for r in rows if r["arm"] == "A2" and not r["silence_swapped"] and r["sample_id"] == pslu_world.sid[101].sample_id)
    target["metrics"] = dict(target["metrics"])
    target["metrics"]["slot_f1_exact_tp"] = 999.0

    report = _build_report(pslu_world, tmp_path, rows, predicted_scenarios)

    assert len(report.recheck_mismatches) == 1
    mismatch = report.recheck_mismatches[0]
    assert isinstance(mismatch, RecheckMismatch)
    assert mismatch.field == "slot_f1_exact_tp"
    assert mismatch.embedded == 999.0

    verdict = report.branch_verdict
    assert verdict.voided is True
    assert verdict.overall == "VOID"
    recheck_clause = next(c for c in verdict.void_clauses if "recheck" in c.clause_text)
    assert recheck_clause.verdict == "met"


def test_lands_void_via_harness_defect_missing_arm(pslu_world, tmp_path):
    a0_101 = _resp("iot", "turn_on_generic", [])
    responses = _neutral_responses({(101, arm): a0_101 for arm in ARMS})
    silence_responses = {101: NEUTRAL_CHANGED, 900: NEUTRAL_CHANGED, 901: NEUTRAL_CHANGED}
    rows, predicted_scenarios = _build_rows(pslu_world, responses, _PREDICTED_SCENARIOS, silence_responses)

    sample_101_id = pslu_world.sid[101].sample_id
    rows = [r for r in rows if not (r["arm"] == "A3" and r["sample_id"] == sample_101_id and not r["silence_swapped"])]

    report = _build_report(pslu_world, tmp_path, rows, predicted_scenarios)

    verdict = report.branch_verdict
    assert verdict.voided is True
    harness_clause = next(c for c in verdict.void_clauses if c.clause_text == "harness defect")
    assert harness_clause.verdict == "met"
    assert any("A3" in reason and "missing" in reason for reason in report.harness_defect_reasons)


# ---------------------------------------------------------------------------
# Focused unit tests for the small pure helpers.
# ---------------------------------------------------------------------------


def test_count_induced_substitutions_counts_wrong_roster_copy():
    predicted = (SlotEntity(type="house_place", filler="bedroom"),)
    gold = (SlotEntity(type="house_place", filler="kitchen"),)
    assert count_induced_substitutions(predicted, gold, ("bedroom", "office")) == 1


def test_count_induced_substitutions_zero_when_correct_even_if_also_roster_value():
    predicted = (SlotEntity(type="house_place", filler="kitchen"),)
    gold = (SlotEntity(type="house_place", filler="kitchen"),)
    # "kitchen" is itself supplied -- the aligned reference IS a roster word,
    # so this is not an induced substitution (module docstring note 3).
    assert count_induced_substitutions(predicted, gold, ("kitchen", "bedroom")) == 0


def test_count_induced_substitutions_zero_without_a_same_type_gold_entity():
    predicted = (SlotEntity(type="time", filler="six"),)
    gold = (SlotEntity(type="house_place", filler="kitchen"),)
    assert count_induced_substitutions(predicted, gold, ("six",)) == 0


def test_count_induced_substitutions_zero_roster_values_short_circuits():
    predicted = (SlotEntity(type="house_place", filler="bedroom"),)
    gold = (SlotEntity(type="house_place", filler="kitchen"),)
    assert count_induced_substitutions(predicted, gold, ()) == 0


def test_arm_copy_rate_guards_zero_denominator():
    class _Row:
        consumption = {"records": []}

    rate, copies, total = arm_copy_rate([_Row(), _Row()])
    assert (rate, copies, total) == (0.0, 0, 0)


def test_arm_copy_rate_micro_aggregates_across_rows():
    class _Row:
        def __init__(self, records):
            self.consumption = {"records": records}

    rows = [
        _Row([{"outcome": "copy"}, {"outcome": "ignore"}]),
        _Row([{"outcome": "use"}, {"outcome": "copy"}]),
    ]
    rate, copies, total = arm_copy_rate(rows)
    assert (copies, total) == (2, 4)
    assert rate == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Loading-layer errors.
# ---------------------------------------------------------------------------


def test_load_attempt_rows_refuses_missing_outputs_jsonl(pslu_world, tmp_path):
    empty_dir = tmp_path / "attempt-empty"
    empty_dir.mkdir()
    with pytest.raises(PsluReadError, match="no outputs.jsonl"):
        build_pslu_report(
            empty_dir, pslu_world.lock, pslu_world.data_root,
            sample_manifest_path=pslu_world.sample_manifest_path,
            roster_table_path=pslu_world.roster_table_path,
        )


# ---------------------------------------------------------------------------
# CLI: idempotence guard (refuses to run twice against the same output dir).
# ---------------------------------------------------------------------------


def _cli_repo_layout(tmp_path: Path, pslu_world: PsluWorld) -> Path:
    """<umbrella>/studies/<name>/ so umbrella_lock_path's own
    ``repo_root.parent.parent / "docs" / "datasets.lock.json"`` convention
    resolves to this world's own lock file."""

    repo_root = tmp_path / "umbrella" / "studies" / "study"
    repo_root.mkdir(parents=True)
    lock_dest = tmp_path / "umbrella" / "docs" / "datasets.lock.json"
    lock_dest.parent.mkdir(parents=True, exist_ok=True)
    lock_dest.write_text(pslu_world.lock_path.read_text(encoding="utf-8"), encoding="utf-8")
    return repo_root


def test_cli_refuses_to_run_twice_against_the_same_output_dir(pslu_world, tmp_path, monkeypatch, capsys):
    a0_101 = _resp("iot", "turn_on_generic", [])
    responses = _neutral_responses({(101, arm): a0_101 for arm in ARMS})
    silence_responses = {101: NEUTRAL_CHANGED, 900: NEUTRAL_CHANGED, 901: NEUTRAL_CHANGED}
    rows, predicted_scenarios = _build_rows(pslu_world, responses, _PREDICTED_SCENARIOS, silence_responses)
    attempt_dir = _write_attempt_dir(tmp_path / "attempt", rows, predicted_scenarios)

    repo_root = _cli_repo_layout(tmp_path, pslu_world)
    monkeypatch.setenv("SPEECHRL_DATA_DIR", str(pslu_world.data_root))
    output_dir = tmp_path / "read-report"
    output_dir.mkdir()

    argv = [
        str(attempt_dir),
        "--output-dir", str(output_dir),
        "--repo-root", str(repo_root),
        "--sample-manifest", str(pslu_world.sample_manifest_path),
        "--roster-table", str(pslu_world.roster_table_path),
    ]

    first_exit = pslu_read_main(argv)
    assert first_exit == 0
    verdict_path = output_dir / "verdict.json"
    assert verdict_path.is_file()
    first_bytes = verdict_path.read_bytes()

    second_exit = pslu_read_main(argv)
    assert second_exit == 1
    captured = capsys.readouterr()
    assert "REFUSED" in captured.err
    assert "already exists" in captured.err
    assert verdict_path.read_bytes() == first_bytes  # untouched by the refused second run
