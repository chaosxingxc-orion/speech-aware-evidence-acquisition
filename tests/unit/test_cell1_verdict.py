"""Tests for the cell CELL-1 verdict writer (owner decisions 83, 99, 101, 106; decision 58).

Everything here runs against SYNTHETIC fixtures under ``tmp_path``: analysis roots in the shape
``scripts/analysis/plan_cell_read.py`` writes (``score-contrasts.json``, ``efficiency.json``,
``frontier.json``, ``structural.json``, ``per-scenario-tables.json``) plus the
``delta-consumption.json`` the S3-4s read adds, and a miniature repository carrying an
exposure ledger, a results ledger and the owner-decisions file. No real ``SPEECHRL_DATA_DIR``
byte and no real repository document is read or written.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DRIVER_PATH = REPO_ROOT / "scripts" / "flights" / "batch" / "cell1_verdict.py"

_SPEC = importlib.util.spec_from_file_location("cell1_verdict", DRIVER_PATH)
drv = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = drv
_SPEC.loader.exec_module(drv)

DATE = "2026-09-24"
NOTE = f"docs/results/{DATE}-slurp-stage3-delta-cell-r01-verdict.md"
TWIN_NOTE = f"docs/results/{DATE}-slurp-stage3-delta-cell-twin-read.md"

#: The rows a real CELL-1 family ledger carries at read time: the four retired smoke rows are
#: already closed, everything else is open.
LEDGER_ROWS = [
    ("SAEA-SLURP-STAGE3-DELTA-CELL-R01-V1", "no"),
    ("SAEA-SLURP-STAGE3-DELTA-CELL-R01-FIT-V1", "no"),
    ("SAEA-SLURP-STAGE3-DELTA-CELL-TWIN-V1", "no"),
    ("SAEA-SLURP-STAGE3-DELTA-CELL-TWIN-FIT-V1", "no"),
    ("SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-V1", "yes"),
    ("SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-FIT-V1", "yes"),
    ("SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-TWIN-V1", "no"),
    ("SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-TWIN-FIT-V1", "no"),
    ("SAEA-SLURP-STAGE3-DELTA-CELL-R01-PAIRED-ANALYSIS-V1", "no"),
    ("SAEA-SLURP-STAGE3-DELTA-CELL-TWIN-PAIRED-ANALYSIS-V1", "no"),
    ("SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-V2", "yes"),
    ("SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-V2-FIT-V1", "yes"),
    ("SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-V3", "no"),
    ("SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-V3-FIT-V1", "no"),
    # a neighbouring family that must never be touched, open on purpose
    ("SAEA-SLURP-STAGE3-ADVANTAGE-R01-V1", "no"),
    ("SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1", "no"),
]

EXPECTED_CLOSED = [run_id for run_id, consumed in LEDGER_ROWS
                   if consumed == "no" and run_id.startswith(drv.FAMILY_PREFIX)]


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )


def _interval(point, low, high):
    return {
        "resampling": "paired whole-speaker cluster bootstrap",
        "point_estimate_pp": point,
        "sigma_hat_pp": 0.5,
        "ci95_pp": [low, high],
        "ci95_half_width_pp": (high - low) / 2.0,
        "ci90_pp": [low + 0.1, high - 0.1],
        "ci90_half_width_pp": (high - low) / 2.0 - 0.1,
        "n_replicates": 10000,
        "seed": 20260915,
    }


def _pooled(left, right, delta, low, high):
    return {
        "delta_pp": delta,
        "direction": "right(arm)-minus-left(comparator)",
        "equal_scenario_delta_pp": delta + 0.05,
        "estimand": "pooled-count-f1",
        "left_pct": left,
        "right_pct": right,
        "per_scenario": {
            "alarm": {"delta_pp": delta, "left_pct": left, "n": 60, "right_pct": right}
        },
        "scenario_stratified": _interval(delta, low - 0.05, high + 0.05),
        "speaker_clustered": _interval(delta, low, high),
    }


def _per_row(left, right, delta, low, high, saves, harms, ties):
    block = _pooled(left, right, delta, low, high)
    block.update(
        {"estimand": "per-row-mean", "saves": saves, "harms": harms, "ties": ties,
         "n": saves + harms + ties, "sign_test_p": 0.25, "sign_test": "mcnemar-exact"}
    )
    return block


def _contrasts(*, slu_delta, slu_ci, intent_delta, intent_ci, status, recipe):
    slu = _pooled(62.10, 62.10 + slu_delta, slu_delta, slu_ci[0], slu_ci[1])
    intent = _per_row(
        80.00, 80.00 + intent_delta, intent_delta, intent_ci[0], intent_ci[1], 21, 12, 1047
    )
    span = _pooled(49.00, 49.40, 0.40, -0.60, 1.40)
    return {
        "recipe_id": recipe,
        "title": "test",
        "analysis_root": "analysis/TEST",
        "comparisons": {
            "arm_vs_comparator": {
                "contrast": "arm minus comparator",
                "pooled_micro": {"slu_f1_micro": slu, "span_f1_micro": span},
                "per_row": {
                    "scenario_action_exact": intent,
                    "scenario_exact": _per_row(86.0, 86.4, 0.40, -0.5, 1.3, 10, 6, 1064),
                    "action_exact": _per_row(81.0, 81.3, 0.30, -0.6, 1.2, 9, 5, 1066),
                    "slu_f1_f1": _per_row(42.0, 43.1, 1.10, 0.20, 2.0, 55, 33, 992),
                    "slot_f1_exact_f1": _per_row(34.0, 34.8, 0.80, -0.1, 1.7, 40, 30, 1010),
                },
                "row_counts": {"arm": 1080, "comparator": 1080},
            }
        },
        "band": {
            "arm_vs_comparator": {
                "decision_17_flagged_scenarios": [],
                "scenarios_losing_beyond_the_band": [],
            }
        },
        "decision": {
            "status": status,
            "margins": {"h_slu_pp": 1.2485, "h_intent_pp": 0.9943},
            "harmful_reasons": [],
            "guards": {
                "official_pooled_slu_f1": {
                    "arm_pct": 62.10 + slu_delta,
                    "comparator_pct": 62.10,
                    "delta_pp": slu_delta,
                    "ci95_pp": list(slu_ci),
                    "margin_h_pp": 1.2485,
                    "ci95_lower_exceeds_minus_h": slu_ci[0] > -1.2485,
                    "ci95_upper_below_zero": slu_ci[1] < 0,
                    "point_below_minus_h": slu_delta < -1.2485,
                },
                "intent_accuracy": {
                    "arm_pct": 80.00 + intent_delta,
                    "comparator_pct": 80.00,
                    "delta_pp": intent_delta,
                    "ci95_pp": list(intent_ci),
                    "margin_h_pp": 0.9943,
                    "ci95_lower_exceeds_minus_h": intent_ci[0] > -0.9943,
                    "ci95_upper_below_zero": intent_ci[1] < 0,
                    "point_below_minus_h": intent_delta < -0.9943,
                },
            },
        },
    }


def _seal_root(root: Path, *, slu_delta, intent_delta, slu_ci, intent_ci, status, recipe,
               consumption=True, official_slu=63.5):
    _write(
        root / "score-contrasts.json",
        _contrasts(
            slu_delta=slu_delta, slu_ci=slu_ci, intent_delta=intent_delta,
            intent_ci=intent_ci, status=status, recipe=recipe,
        ),
    )
    _write(
        root / "efficiency.json",
        {
            "headline": {
                "contacts_per_row": 4.10,
                "contacts_per_row_comparator": 4.096,
                "contacts_per_minute": 40.1,
                "contacts_per_minute_comparator": 39.9,
                "prefilled_tokens_per_row": 8900.0,
                "prefilled_tokens_per_row_comparator": 8400.0,
                "gpu_hours_per_1080": 1.81,
                "gpu_hours_per_1080_comparator": 1.7579,
                "cache_hit_share": 0.74,
                "cache_hit_share_comparator": 0.7545,
                "wall_seconds": 6600.0,
                "cost_is_lower_than_the_base": False,
                "gpu_hours_decomposition": {"comparator_wall_seconds": 6400.0},
            }
        },
    )
    _write(
        root / "frontier.json",
        {
            "row": {
                "cell": "CELL-1",
                "official_slu": official_slu,
                "official_intent": 81.2,
                "gpu_hours_per_1080": 1.81,
                "contacts_per_row": 4.10,
                "prefilled_tokens_per_row": 8900.0,
            },
            "plan_is_on_the_gpu_hour_frontier": False,
            "plan_is_on_the_prefilled_token_frontier": True,
        },
    )
    _write(
        root / "structural.json",
        {
            "trajectory": {
                "arm": {
                    "contacts": 4430,
                    "contacts_per_row": 4.1019,
                    "contacts_per_row_histogram": {"4": 1070, "7": 10},
                },
                "comparator": {
                    "contacts": 4424,
                    "contacts_per_row": 4.0963,
                    "contacts_per_row_histogram": {"4": 1069, "7": 11},
                },
            },
            "dispositions": {
                "arm": {
                    "finite_stops": {"count": 9, "sample_ids": []},
                    "other_terminal_dispositions": {"count": 0},
                    "planner_action_illegal": {"count": 1, "sample_ids": []},
                    "react_exhaustion_rows": 0,
                }
            },
            "context_fit_compaction": {
                "arm": {
                    "contacts_compacted": 12,
                    "one_receipt_per_row": True,
                    "flight_receipt_dispositions": {"context_compaction_rows": 12},
                }
            },
        },
    )
    _write(
        root / "per-scenario-tables.json",
        {
            "natural_mixture_and_equal_scenario": {
                "arm_vs_comparator": {
                    "pooled_slu_f1_equal_scenario_delta_pp": 0.51,
                    "pooled_slu_f1_per_scenario": {
                        "alarm": {"delta_pp": 1.5, "left_pct": 74.9, "n": 60, "right_pct": 76.4},
                        "audio": {"delta_pp": -0.5, "left_pct": 67.9, "n": 60, "right_pct": 67.4},
                    },
                }
            }
        },
    )
    if consumption:
        _write(
            root / "delta-consumption.json",
            {
                "store_id": "stage3-deltas",
                "store": {
                    "store_release_sha256": "r" * 64,
                    "store_snapshot_sha256": "s" * 64,
                },
                "consumption": {
                    "node_order": ["perception", "solver", "reviewer", "planner"],
                    "summary": {
                        "rows_total": 1080,
                        "rows_supplied_any_node": 1080,
                        "items_supplied_total": 5400,
                        "distinct_value_ids_supplied": 121,
                        "skip_events": 900,
                        "projection_events": 25,
                        "inert_routes": [],
                    },
                    "per_node": {
                        "perception": {
                            "cap": 4, "rows_supplied": 1080, "rows_supplied_share": 1.0,
                            "items_supplied_total": 4320,
                            "items_per_supplied_row_mean": 4.0, "rows_at_full_cap": 1080,
                            "distinct_value_ids": 4,
                            "skips": {"skip_events": 0, "rows_skipped": 0},
                            "outcome_on_supplied_rows": {
                                "rows_joined": 1080,
                                "slu_f1": {"saves": 55, "harms": 33, "neutral": 992,
                                           "mean_delta_pp": 1.10},
                                "intent": {"saves": 21, "harms": 12, "neutral": 1047,
                                           "mean_delta_pp": 0.83},
                            },
                        },
                        "solver": {
                            "cap": 8, "rows_supplied": 90, "rows_supplied_share": 0.0833,
                            "items_supplied_total": 180,
                            "items_per_supplied_row_mean": 2.0, "rows_at_full_cap": 0,
                            "distinct_value_ids": 11,
                            "skips": {"skip_events": 990, "rows_skipped": 990},
                        },
                        "reviewer": {
                            "cap": 4, "rows_supplied": 400, "rows_supplied_share": 0.37,
                            "items_supplied_total": 700,
                            "items_per_supplied_row_mean": 1.75, "rows_at_full_cap": 10,
                            "distinct_value_ids": 24,
                            "skips": {"skip_events": 680, "rows_skipped": 680},
                        },
                        "planner": {
                            "cap": 4, "rows_supplied": 150, "rows_supplied_share": 0.14,
                            "items_supplied_total": 200,
                            "items_per_supplied_row_mean": 1.33, "rows_at_full_cap": 0,
                            "distinct_value_ids": 6,
                            "skips": {"skip_events": 930, "rows_skipped": 930},
                        },
                    },
                },
            },
        )
    return root


def _ledger_line(run_id: str, consumed: str) -> str:
    cells = [
        "2026-09-23T18:00:00.000000+00:00", run_id, "bounded-discovery-probe",
        f"purpose of {run_id}", "geometry", "slurp TRAIN Fold A 1080", "discovery",
        "6" * 64, consumed, "11880", "33930", "12.0", "prior exposure",
        "docs/readiness/plan.json", "notes",
    ]
    return "| " + " | ".join(cells) + " |"


@pytest.fixture()
def repo(tmp_path) -> Path:
    root = tmp_path / "repo"
    ledger = root / drv.LEDGER
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(
        "# Exposure ledger\n\n"
        + "\n".join(_ledger_line(run_id, consumed) for run_id, consumed in LEDGER_ROWS)
        + "\n",
        encoding="utf-8",
        newline="",
    )
    results = root / drv.RESULTS_LEDGER
    results.parent.mkdir(parents=True, exist_ok=True)
    results.write_text("# Stage-2 results ledger\n", encoding="utf-8", newline="")
    decisions = root / drv.DECISIONS
    decisions.parent.mkdir(parents=True, exist_ok=True)
    decisions.write_text("# Owner decisions\n", encoding="utf-8", newline="")
    return root


@pytest.fixture()
def arm_root(tmp_path) -> Path:
    return _seal_root(
        tmp_path / "analysis" / "ARM",
        slu_delta=1.40, slu_ci=(0.30, 2.50),
        intent_delta=0.83, intent_ci=(-0.20, 1.90),
        status="GAIN PROVEN", recipe="slurp-stage3-delta-cell-arm-paired-analysis-v1",
    )


@pytest.fixture()
def twin_root(tmp_path) -> Path:
    return _seal_root(
        tmp_path / "analysis" / "TWIN",
        slu_delta=0.30, slu_ci=(-0.80, 1.40),
        intent_delta=0.10, intent_ci=(-0.95, 1.10),
        status="NON-INFERIORITY NOT PROVEN",
        recipe="slurp-stage3-delta-cell-twin-paired-analysis-v1",
        official_slu=62.4,
    )


def _argv(repo, arm_root, *extra, which="arm"):
    return [
        "--which", which,
        "--repo", str(repo),
        "--arm-root", str(arm_root),
        "--status", "ADMITTED (provisional)",
        "--factor", "the locked v2.0 plan plus the per-node stage3-deltas-v1r store",
        "--reading", "The store's content carries the gain.",
        "--commit", "abc12345",
        "--flown", "2026-09-24T01:00 to 03:00 UTC",
        "--date", DATE,
        *extra,
    ]


# --------------------------------------------------------------------------
# Dry run
# --------------------------------------------------------------------------

def test_dry_run_writes_nothing(repo, arm_root, capsys):
    before = {
        path: (repo / path).read_text(encoding="utf-8")
        for path in (drv.LEDGER, drv.RESULTS_LEDGER, drv.DECISIONS)
    }
    assert drv.main(_argv(repo, arm_root, "--no-twin", "--dry-run")) == 0
    for path, text in before.items():
        assert (repo / path).read_text(encoding="utf-8") == text
    assert not (repo / NOTE).exists()
    out = capsys.readouterr().out
    assert "DRY RUN -- would write" in out
    assert f"would close {len(EXPECTED_CLOSED)} ledger row(s)" in out


# --------------------------------------------------------------------------
# The verdict document
# --------------------------------------------------------------------------

def test_headline_table_carries_the_intervals_the_driver_wrote(repo, arm_root):
    assert drv.main(_argv(repo, arm_root, "--no-twin")) == 0
    text = (repo / NOTE).read_text(encoding="utf-8")
    # the precedent rendered an EMPTY headline table because it looked for a `ci95` key; the
    # driver writes the point interval under `speaker_clustered.ci95_pp`, the CI90 beside it and
    # the scenario-stratified CI90 under `scenario_stratified.ci90_pp`
    assert (
        "| slu_f1_micro | 62.10 | 63.50 | +1.40 | [+0.30, +2.50] | [+0.40, +2.40] "
        "| [+0.35, +2.45] | +1.45 |"
    ) in text
    assert (
        "| scenario_action_exact | 80.00 | 80.83 | +0.83 | [-0.20, +1.90] | [-0.10, +1.80] "
        "| [-0.15, +1.85] | +0.88 |"
    ) in text
    # the saves / harms / ties companion, with the exact two-sided McNemar p
    assert "| scenario_action_exact | 21 | 12 | 1047 | 0.2500 |" in text


def test_guard_table_states_what_each_guard_decides(repo, arm_root):
    assert drv.main(_argv(repo, arm_root, "--no-twin")) == 0
    text = (repo / NOTE).read_text(encoding="utf-8")
    assert "| official pooled SLU-F1 |" in text
    assert "proven gain" in text
    assert "1.2485" in text and "0.9943" in text


def test_the_registered_decision_rule_is_restated(repo, arm_root):
    assert drv.main(_argv(repo, arm_root, "--no-twin")) == 0
    text = (repo / NOTE).read_text(encoding="utf-8")
    for fragment in ("**ADMITTED**", "**NEUTRAL**", "**HARMFUL**", "TWIN = attribution",
                     "**Replication**"):
        assert fragment in text


def test_caveats_carry_the_twin_bound_the_compaction_and_the_launch_failures(repo, arm_root):
    assert drv.main(_argv(repo, arm_root, "--no-twin")) == 0
    text = (repo / NOTE).read_text(encoding="utf-8")
    assert "363 of 379" in text
    assert "COMPACT_REQUIRED" in text and "317 tokens" in text
    assert "contacts compacted 12" in text
    assert "Four launch failures" in text
    assert "metering 320 contacts" in text
    for calls in ("| 4 |", "| 12 |", "| 304 |"):
        assert calls in text


def test_delta_consumption_section_is_rendered(repo, arm_root):
    assert drv.main(_argv(repo, arm_root, "--no-twin")) == 0
    text = (repo / NOTE).read_text(encoding="utf-8")
    assert "## 6. Per-node delta consumption (item S3-4s)" in text
    assert "| solver | 8 | 90 |" in text
    assert "distinct value ids" in text


def test_a_missing_delta_consumption_file_is_flagged_not_silent(repo, tmp_path):
    root = _seal_root(
        tmp_path / "analysis" / "NOCONS",
        slu_delta=1.40, slu_ci=(0.30, 2.50), intent_delta=0.83, intent_ci=(-0.20, 1.90),
        status="GAIN PROVEN", recipe="r", consumption=False,
    )
    assert drv.main(_argv(repo, root, "--no-twin")) == 0
    text = (repo / NOTE).read_text(encoding="utf-8")
    assert "`delta-consumption.json` is not present" in text
    assert "PRIMARY deliverable" in text


# --------------------------------------------------------------------------
# The twin
# --------------------------------------------------------------------------

def test_arm_read_folds_in_the_twin_and_marks_the_attribution_descriptive(
    repo, arm_root, twin_root
):
    assert drv.main(_argv(repo, arm_root, "--twin-root", str(twin_root))) == 0
    text = (repo / NOTE).read_text(encoding="utf-8")
    assert "## 3. The derangement twin" in text
    # arm +1.40, twin +0.30 -> arm minus twin +1.10, descriptive
    assert "| slu_f1_micro | +1.40 | [+0.30, +2.50] | +0.30 | [-0.80, +1.40] | +1.10 |" in text
    assert "DESCRIPTIVE" in text
    assert "decides attribution, never admission" in text
    # both frontier rows are placed side by side
    assert "| CELL-1 |" in text and "| CELL-1 twin |" in text


def test_without_a_twin_root_the_gain_is_declared_unattributed(repo, arm_root):
    assert drv.main(_argv(repo, arm_root, "--no-twin")) == 0
    text = (repo / NOTE).read_text(encoding="utf-8")
    assert "UNATTRIBUTED" in text


def test_the_twin_read_writes_its_own_note_and_closes_no_record(repo, twin_root):
    before = {
        path: (repo / path).read_text(encoding="utf-8")
        for path in (drv.LEDGER, drv.RESULTS_LEDGER, drv.DECISIONS)
    }
    assert drv.main(_argv(repo, twin_root, which="twin")) == 0
    assert (repo / TWIN_NOTE).exists()
    assert not (repo / NOTE).exists()
    for path, text in before.items():
        assert (repo / path).read_text(encoding="utf-8") == text
    text = (repo / TWIN_NOTE).read_text(encoding="utf-8")
    assert "twin read" in text
    assert "No record is closed by the twin read" in text


# --------------------------------------------------------------------------
# Record closure
# --------------------------------------------------------------------------

def test_exactly_the_open_family_rows_are_closed(repo, arm_root):
    assert drv.main(_argv(repo, arm_root, "--no-twin")) == 0
    text = (repo / drv.LEDGER).read_text(encoding="utf-8")
    closed = {}
    for line in text.split("\n"):
        if not line.startswith("|"):
            continue
        cells = line.split("|")
        closed[cells[2].strip()] = cells[9].strip()
    for run_id in EXPECTED_CLOSED:
        assert closed[run_id] == "yes", run_id
    # the retired smoke rows keep their own note and must be byte-identical to their input
    rows = {
        line.split("|")[2].strip(): line
        for line in text.split(chr(10))
        if line.startswith("|")
    }
    for run_id in drv.RETIRED_ROWS:
        assert closed[run_id] == "yes"
        assert NOTE not in rows[run_id]
        assert rows[run_id] == _ledger_line(run_id, "yes")
    # a neighbouring family is left open
    assert closed["SAEA-SLURP-STAGE3-ADVANTAGE-R01-V1"] == "no"
    assert closed["SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1"] == "no"


def test_the_closure_note_says_what_each_row_kind_is(repo, arm_root):
    assert drv.main(_argv(repo, arm_root, "--no-twin")) == 0
    lines = {
        line.split("|")[2].strip(): line
        for line in (repo / drv.LEDGER).read_text(encoding="utf-8").split("\n")
        if line.startswith("|")
    }
    assert "CONSUMED (fit, within cap)" in lines["SAEA-SLURP-STAGE3-DELTA-CELL-R01-FIT-V1"]
    assert "model-free read" in lines["SAEA-SLURP-STAGE3-DELTA-CELL-R01-PAIRED-ANALYSIS-V1"]
    assert "four-row smoke" in lines["SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-V3"]
    assert "form control" in lines["SAEA-SLURP-STAGE3-DELTA-CELL-TWIN-V1"]
    arm_line = lines["SAEA-SLURP-STAGE3-DELTA-CELL-R01-V1"]
    assert "4430 contacts" in arm_line and "ADMITTED (provisional)" in arm_line
    assert "abc12345" in arm_line


def test_expect_rows_refuses_a_count_that_moved(repo, arm_root):
    with pytest.raises(SystemExit):
        drv.main(_argv(repo, arm_root, "--no-twin", "--expect-rows", "3"))


def test_a_ledger_with_no_open_family_row_is_refused(repo, arm_root):
    path = repo / drv.LEDGER
    path.write_text(
        path.read_text(encoding="utf-8").replace("| no |", "| yes |"),
        encoding="utf-8",
        newline="",
    )
    with pytest.raises(SystemExit):
        drv.main(_argv(repo, arm_root, "--no-twin"))


def test_results_ledger_entry_carries_the_real_numbers(repo, arm_root):
    assert drv.main(_argv(repo, arm_root, "--no-twin")) == 0
    text = (repo / drv.RESULTS_LEDGER).read_text(encoding="utf-8")
    assert f"## {DATE}: cell CELL-1," in text
    # the precedent rendered 0.00 -> 0.00 / +0.00 here by reading the wrong keys
    assert "62.10 -> 63.50" in text
    assert "**+1.40 pp CI95 [+0.30, +2.50]**" in text
    assert "80.00 -> 80.83" in text
    assert "**+0.83 pp CI95 [-0.20, +1.90]**" in text
    assert "0.00 -> 0.00" not in text
    assert "tfgrpo-semantic-advantage-v1" in text
    assert "4430 contacts" in text


def test_decision_99_outcome_is_appended(repo, arm_root):
    assert drv.main(_argv(repo, arm_root, "--no-twin")) == 0
    text = (repo / drv.DECISIONS).read_text(encoding="utf-8")
    assert f"Outcome of decision 99 (CELL-1, {DATE}): ADMITTED (provisional)." in text
    assert NOTE in text


# --------------------------------------------------------------------------
# Refusals
# --------------------------------------------------------------------------

def test_a_missing_analysis_root_is_refused(repo, tmp_path):
    with pytest.raises(SystemExit):
        drv.main(_argv(repo, tmp_path / "nothing", "--no-twin"))


def test_a_root_missing_a_required_deliverable_is_refused(repo, arm_root):
    (arm_root / "efficiency.json").unlink()
    with pytest.raises(SystemExit):
        drv.main(_argv(repo, arm_root, "--no-twin"))
