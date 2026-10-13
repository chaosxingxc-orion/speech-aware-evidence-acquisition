"""The autonomous typed-loop driver (decision 263-A, design section 7): ``open`` / ``close`` / ``status`` on a SYNTHETIC sealed tree.

What is proved (all model-free, no data root, no GPU, no real flight or lease; every external analysis script is replaced by a
stand-in that writes a synthetic output):

* the pinned protocol equals the implemented constants, and a tampered protocol or a changed pin stops the driver;
* the guard refuses while a batch driver / flight / flip loop runs, and refuses when processes cannot be listed;
* ``open --stage propose`` writes the tables, the proposer artefacts, the 18 reflector materials and the HELD proposer / reflector
  cells, and is idempotent (a second run changes nothing; a changed input is refused);
* ``open --stage cell`` with an EMPTY typed arm (a legal state) curates the ACE playbook and derives the iteration cell with the arms
  ace / aa / lock; with a valid knob-set candidate it adds ``typ``;
* ``close`` applies the preregistered selection rule to the synthetic paired reads: accepted, refused (point floor, intent guard,
  twin) and unflown states are archived, the curve repeats the previous level when nothing is accepted, the meta summary and the
  parent choice are produced, a re-run is a no-op and a changed read is refused;
* without ``--execute`` the driver stops at the first missing analysis output and writes no archive state;
* the stop rule: iteration 3 closes the loop.

Fixtures are aggregate-only and synthetic: no utterance, gold label or model output appears in this file.
"""

from __future__ import annotations

import copy
import json
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
TFRL = REPO / "scripts" / "flights" / "tfrl"
for _p in (str(REPO / "src"), str(TFRL)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import tfrl_family as tf  # noqa: E402
import tfrl_loop_driver as drv  # noqa: E402
import tfrl_loop_lib as lib  # noqa: E402
import tfrl_overlay  # noqa: E402

from speech_aware_evidence_acquisition.analysis.sealed_credit import archive as ar  # noqa: E402
from speech_aware_evidence_acquisition.rails import tfrl_ace_material as ace  # noqa: E402
from speech_aware_evidence_acquisition.rails import tfrl_typed_proposer as tp  # noqa: E402

SLOT_TYPES = ["date", "time", "place_name", "person", "event_name"]
INTENTS = ["alarm_set", "calendar_set", "weather_query", "social_post"]
SCENARIOS = list(tp.SCENARIOS)
INTENTS = sorted(set(INTENTS) | {f"{s}_query" for s in SCENARIOS})
BINS = ("1", "2", "3", "4-5", "6-10", "11+", "off-list", "no-shortlist")


# ---------------------------------------------------------------------------------------------------------------------------
# synthetic sealed bytes
# ---------------------------------------------------------------------------------------------------------------------------


def synthetic_tables(run_id: str = "SYNTHETIC-RUN") -> dict:
    pools = {}
    for pool in ("comp1b_fold_a", "a2"):
        pools[pool] = {"split": "train", "rows": 1000, "analytic_rates_pp": {"recover_one_missing_entity": 0.062},
                       "empirical_rates_pp": {k: {"mean_pp": 0.05, "n": 100} for k in (
                           "remove_one_spurious_entity", "recover_one_missing_entity", "one_extra_exact_row.any_non_exact_row",
                           "one_extra_exact_row.non_empty_gold_row", "one_extra_exact_row.empty_gold_false_fill_row",
                           "one_extra_exact_row.s1_parsed_not_exact_row")},
                       "node_rates": {}}
    document = {
        "schema": "saea-tfrl-contrast-tables-v1",
        "source": {"run_id": run_id, "attempt": "attempt-x", "arm": "lock", "scorer": "slurp-slu-official-train", "split": "train",
                   "rows": 1080, "files": {}},
        "suppression": {"min_cell": 3, "marker": "<3"},
        "scenario_rows": {s: 60 for s in SCENARIOS},
        "table_a": {"columns": ["class", "slot_type", "scenario", "in_supply", "in_store_not_delivered", "in_train_not_in_store",
                                "nowhere", "total"],
                    "rows": [["MISSING", "date", "calendar", 41, 8, 12, 5, 66], ["SPURIOUS", "person", "social", "<3", 3, "<3", 0, "<3"],
                             ["WRONG-VALUE", "place_name", "weather", 9, 0, 4, 3, 16]],
                    "marginals": {}},
        "table_b": {"per_scenario": {s: {"empty_gold_rows": 10, "false_fill_rows": 4, "false_fill_rate_pct": 40.0, "spurious_entities": 5}
                                     for s in SCENARIOS}, "overall": {}},
        "table_c": {"per_scenario": {s: {"rows": 60, "intent_wrong_rows": 8, "gold_on_shortlist_rows": 55,
                                         "gold_on_shortlist_rate_pct": 91.67, "wrong_rows_gold_on_shortlist": 4,
                                         "wrong_rank_histogram": {b: 1 for b in BINS}} for s in SCENARIOS}, "overall": {}},
        "table_d": {"overall": {"rows": 1080, "exemplars": {"n": 1080, "mean": 40.0, "p50": 41, "p99": 53},
                                "cards": {"n": 1080, "mean": 3.0, "p50": 3, "p99": 5},
                                "supplied_tokens": {"n": 1080, "mean": 10486.3, "p50": 10400, "p99": 14641}}, "per_scenario": {}},
        "table_e": {"source": "analysis/x/report.json", "source_sha256": "0" * 64, "note": "copied", "pools": pools},
        "table_f": {"columns": ["candidate_id", "operator_class", "predicted_pp", "measured_pp", "verdict"], "rows": []},
        "table_g": {"playbook_release": None, "items": []},
    }
    import hashlib

    body = dict(document)
    document["tables_sha256"] = hashlib.sha256(json.dumps(body, indent=2, sort_keys=True).encode("utf-8")).hexdigest()
    return document


def contrast_doc(slu: float, lo: float, hi: float, intent: float = 0.0, ilo: float = -0.3, ihi: float = 0.3) -> dict:
    return {
        "pooled_micro": {"slu_f1_micro": {"left_pct": 66.0, "right_pct": 66.0 + slu, "delta_pp": slu,
                                          "cluster_bootstrap": {"ci95_pp": [lo, hi]}}},
        "per_row": {"scenario_action_exact": {"left_pct": 83.0, "right_pct": 83.0 + intent, "delta_pp": intent,
                                              "cluster_bootstrap": {"ci95_pp": [ilo, ihi]}}},
    }


def per_scenario_doc(slu: float, intent: float) -> dict:
    return {"per_scenario": {s: {"slu_f1": {"delta_pp": slu}, "intent": {"delta_pp": intent}} for s in SCENARIOS}}


def fit_report(delta: float, lo: float, refused: bool = False) -> dict:
    return {"schema": "saea-tfrl-delivery-fit-v1", "refused": refused,
            "cross_fitted": {"delta_slu_pp": delta, "ci95_slu_pp": [lo, delta + 0.5], "delta_intent_pp": 0.0, "right_slu_f1_pp": 66.0 + delta,
                             "per_scenario": {}},
            "rule_table": None if refused else {"schema": "saea-tfrl-delivery-rule-table-v1", "family": "ee"}}


class Fakes:
    """The stand-in for every external analysis script; ``pairs`` maps ``"<right>-vs-<left>"`` to a contrast document."""

    def __init__(self, pairs: dict | None = None, fits: dict | None = None):
        self.pairs, self.fits, self.calls = pairs or {}, fits or {}, []

    def __call__(self, name: str, argv: list[str], produced: list[Path]) -> None:
        self.calls.append(name)
        for path in produced:
            path.parent.mkdir(parents=True, exist_ok=True)
        if name == "tables":
            produced[0].write_text(json.dumps(synthetic_tables()), encoding="utf-8")
        elif name == "score-columns":
            arms = {a: {"official": {"slu_f1": 0.66, "intent_accuracy": 0.83}} for a in ("ace", "aa", "lock", "typ", "par")}
            produced[0].write_text(json.dumps({"arms": arms}), encoding="utf-8")
        elif name == "node-local":
            paired = {"empty_gold_false_fill": {"n": 100, "diff_pp": -0.5}, "nonempty_exact": {"n": 980, "diff_pp": 0.4}}
            produced[0].write_text(json.dumps({"arms": {a: {"paired_vs_delivering": paired} for a in ("ace", "aa", "typ", "par")}}),
                                   encoding="utf-8")
        elif name.startswith("paired-"):
            pair = name[len("paired-"):]
            doc = self.pairs.get(pair) or contrast_doc(0.0, -0.8, 0.8)
            produced[0].write_text(json.dumps(doc), encoding="utf-8")
            (produced[0].parent / "per-scenario-tables.json").write_text(json.dumps(per_scenario_doc(0.1, 0.0)), encoding="utf-8")
        elif name.startswith("delivery-fit-"):
            key = name[len("delivery-fit-"):]
            produced[0].write_text(json.dumps(self.fits.get(key) or fit_report(0.2, -0.1, refused=True)), encoding="utf-8")
        elif name == "row-scores":      # the stand-in of tfrl_row_scores.py: 12 synthetic rows, ace better on every even row
            import tfrl_row_scores as rs

            rows = [f"slurp:train:{i:06d}:audio-{i}" for i in range(12)]
            doc = rs.build_row_scores({sid: 0.5 for sid in rows}, {sid: (0.7 if i % 2 == 0 else 0.4) for i, sid in enumerate(rows)},
                                      {sid: {"scenario": "calendar", "slot_types": ["date"]} for sid in rows})
            produced[0].write_text(json.dumps(doc), encoding="utf-8")
        else:  # pragma: no cover
            raise AssertionError(name)


class World:
    """A temporary overlay repository, a copy of the committed protocol, a data root and a way to call the driver."""

    def __init__(self, tmp_path: Path):
        self.root = tfrl_overlay.make_overlay(tmp_path / "overlay", REPO)
        self.pkg = tmp_path / "pkg"
        self.pkg.mkdir()
        shutil.copyfile(REPO / tf.PROTOCOL_RELPATH, self.pkg / "tfrl-loop-protocol-v1.json")
        self.data = tmp_path / "data"
        self.data.mkdir()
        self.tmp = tmp_path
        self.out: list[str] = []
        self.enums = tmp_path / "enums.json"
        self.enums.write_text(json.dumps({"slot_types": SLOT_TYPES, "intents": INTENTS}), encoding="utf-8")
        self.processes: list[str] | None = []

    def run(self, *argv: str, fakes: Fakes | None = None, execute: bool = False) -> tuple[int, str]:
        base = ["--repo-root", str(self.root), "--package-dir", str(self.pkg), "--data-root", str(self.data)]
        runner = lib.Runner(execute=execute, cwd=self.root, fake=fakes)
        out: list[str] = []
        code = drv.main(base + list(argv), runner=runner, lister=lambda: self.processes, out=out.append)
        self.out = out
        return code, "\n".join(out)

    def receipt(self, t: int, step: str) -> dict:
        return json.loads((self.pkg / "iterations" / f"i{t}" / f"{step}-receipt.json").read_text(encoding="utf-8"))

    def archive(self) -> ar.Archive:
        return ar.Archive(self.pkg / "archive")

    def analysis(self, t: int) -> Path:
        return self.data / tf.ANALYSIS_ROOT / f"i{t}"


@pytest.fixture()
def world(tmp_path):
    return World(tmp_path)


def propose_args(world: World, t: int = 1) -> list[str]:
    return ["open", "--iter", str(t), "--stage", "propose", "--enums-file", str(world.enums), "--study-commit", "a" * 40]


def reflector_answers(path: Path) -> Path:
    answers = {}
    for i, scenario in enumerate(SCENARIOS):
        answers[scenario] = json.dumps({"deltas": [{"op": "add", "target_id": "", "section": "strategy",
                                                    "scope": {"scenarios": [scenario], "slot_types": []},
                                                    "text": f"Alpha {scenario} beta{i} gamma{i} delta{i} epsilon{i} zeta{i} eta{i} theta{i}.",
                                                    "rationale": "boundary errors dominate"}]})
    path.write_text(json.dumps({"answers": answers}), encoding="utf-8")
    return path


def knob_receipt(value: int = 12) -> list[dict]:
    cand = {"schema": tp.CANDIDATE_SCHEMA_ID, "iteration": 1, "parent_state_id": drv.ROOT_DISPLAY, "operator_class": "supply",
            "operator": "knob-set",
            "target": {"failure_class": "MISSING", "slot_types": ["date"], "scenarios": ["calendar"], "value_in_supply": "E1"},
            "hypothesis_code": "type-inventory", "applications": [{"tail": "train-exemplars.phase_supply.solver.k", "value": value}]}
    return [{"allowed_classes": ["supply"], "receipt": tp.read_typed_candidate_receipt(json.dumps(cand))}]


def predictions(path: Path, entries: list[dict], pp: float) -> Path:
    path.write_text(json.dumps({"schema": tp.PREDICTIONS_SCHEMA_ID,
                                "predictions": {e["receipt"]["candidate_id"]: {"slu_pp": pp, "basis": "stub"} for e in entries}}),
                    encoding="utf-8")
    return path


def open_cell_args(world: World, t: int = 1, **extra) -> list[str]:
    answers = reflector_answers(world.tmp / f"answers-i{t}.json")
    args = ["open", "--iter", str(t), "--stage", "cell", "--reflector-answers", str(answers), "--enums-file", str(world.enums),
            "--study-commit", "a" * 40]
    if extra.get("empty", True) and "typed" not in extra:
        args.append("--typed-arm-empty")
    if "typed" in extra:
        args += ["--typed-receipts", str(extra["typed"]), "--predictions", str(extra["predictions"])]
    return args


# ---------------------------------------------------------------------------------------------------------------------------
# protocol and guards
# ---------------------------------------------------------------------------------------------------------------------------


def test_the_committed_protocol_equals_the_implemented_constants():
    import build_tfrl_loop_protocol as bp

    built = bp.build()
    committed = json.loads((REPO / tf.PROTOCOL_RELPATH).read_text(encoding="utf-8"))
    assert committed == built
    from speech_aware_evidence_acquisition.analysis.sealed_credit import parent_choice, selection

    assert committed["selection"]["rules"] == selection.DEFAULT_RULES
    assert committed["selection"]["rules"]["slu_floor_pp"] == 1.49 and committed["selection"]["rules"]["intent_guard_pp"] == 0.65
    assert committed["parent_choice"]["child_penalty_pp"] == parent_choice.CHILD_PENALTY_PP == 0.25
    assert committed["edit_budget_L_t"]["1"] == 2 and committed["edit_budget_L_t"]["2"] == 1
    assert committed["loop"]["stop_rule"]["iterations"] == 3
    assert committed["ace"]["constants_sha256"] == ace.constants_hash(ace.ACE_CONSTANTS)
    assert committed["arm_sets"]["1"]["arms"] == ["ace", "aa", "lock"]
    assert committed["status"] == "DRAFT-HELD"


def test_a_tampered_protocol_stops_the_driver(world):
    path = world.pkg / "tfrl-loop-protocol-v1.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["selection"]["rules"]["slu_floor_pp"] = 0.1
    path.write_text(json.dumps(document), encoding="utf-8")
    code, text = world.run("status")
    assert code == 3 or "protocol" in text.lower()
    code, text = world.run(*propose_args(world), fakes=Fakes())
    assert code == 3 and "protocol" in text


def test_the_pinned_protocol_hash_may_not_change_after_the_first_open(world):
    code, _ = world.run(*propose_args(world), fakes=Fakes())
    assert code == 0
    state = json.loads((world.pkg / lib.STATE_FILE).read_text(encoding="utf-8"))
    state["protocol_sha256"] = "f" * 64
    (world.pkg / lib.STATE_FILE).write_text(json.dumps(state), encoding="utf-8")
    code, text = world.run(*propose_args(world), fakes=Fakes())
    assert code == 3 and "changed since the loop was opened" in text


@pytest.mark.parametrize("busy", ["bash scripts/flights/batch/batch_driver.sh", "python -m core.flight.cli worker",
                                  "bash repin_loop_generic.sh x", "bash scripts/flights/tfrl/tfrl_i1_flip.sh"])
def test_the_guard_refuses_while_a_batch_a_flight_or_a_flip_loop_runs(world, busy):
    world.processes = ["python -m unrelated", busy]
    code, text = world.run(*propose_args(world), fakes=Fakes())
    assert code == 3 and "running" in text
    assert not (world.pkg / "iterations").exists() and not list((world.pkg / "archive").glob("*")) if (world.pkg / "archive").exists() else True


def test_the_guard_refuses_when_processes_cannot_be_listed(world):
    world.processes = None
    code, text = world.run("close", "--iter", "1")
    assert code == 3 and "cannot list processes" in text


# ---------------------------------------------------------------------------------------------------------------------------
# open: propose
# ---------------------------------------------------------------------------------------------------------------------------


def test_open_propose_writes_the_artefacts_the_cells_and_the_receipt(world):
    code, text = world.run(*propose_args(world), fakes=Fakes())
    assert code == 0, text
    A = world.analysis(1)
    assert (A / "tables" / "tables-v1.json").is_file() and (A / "proposer-tables.json").is_file()
    assert (A / "proposer-context.json").is_file() and (A / "playbook" / "playbook-i0.json").is_file()
    assert len(list((A / "ace-material").glob("material-*.json"))) == 18
    # the proposer's own reader accepts what the adapter wrote
    tables = tp.load_tables(A / "proposer-tables.json")
    assert tables.iteration == 1 and tables.table("failure_cube")["rows"]
    tp.load_context(A / "proposer-context.json")
    for path in (A / "ace-material").glob("material-*.json"):
        ace.load_material(path)
    receipt = world.receipt(1, "open-propose")
    assert receipt["edit_budget_L_t"] == 2 and receipt["ace"]["t_cap"] == 14641 + ace.ACE_CONSTANTS["allowance_tokens"]
    assert receipt["ace"]["constants_sha256"] == ace.constants_hash(ace.ACE_CONSTANTS)
    assert receipt["parent_display_id"] == drv.ROOT_DISPLAY
    assert receipt["registration"]["status"] == "DRAFT-HELD"
    # the two text-only cells exist in the overlay and are HELD
    for kind in ("typed", "ace"):
        n = tf.names(1, kind)
        experiment = json.loads((world.root / "configs" / "experiment" / f"{n['experiment']}.json").read_text(encoding="utf-8"))
        assert experiment["cells"][0]["readiness"]["state"] == "held"
        assert experiment["stage3_algorithm"]["id"] == (tf.ALGORITHM_TYPED if kind == "typed" else tf.ALGORITHM_ACE)
    rows = (world.root / receipt["registration"]["package"] / "draft-ledger-rows.md").read_text(encoding="utf-8")
    assert "DRAFT" in rows and "consumed" in rows
    # the exposure ledger is untouched: the overlay's copy still equals the repository ledger (which since 2026-10-11 carries live TFRL rows)
    assert (world.root / "docs" / "exposure-ledger.md").read_bytes() == (REPO / "docs" / "exposure-ledger.md").read_bytes()
    # the archive holds the two iteration-0 roots only
    assert sorted((s["arm"], s["iteration"]) for s in world.archive().states()) == [("ace", 0), ("typed", 0)]


def test_open_propose_writes_no_text_and_no_gold(world):
    world.run(*propose_args(world), fakes=Fakes())
    banned = ("transcript", "utterance", "gold_label")
    for path in list(world.analysis(1).rglob("*.json")):
        text = path.read_text(encoding="utf-8")
        for word in banned:
            assert word not in text.lower().replace("gold_on_shortlist", "").replace("wrong_rows_gold_on_shortlist", ""), (path.name, word)


def test_open_propose_is_idempotent_and_refuses_a_changed_input(world):
    fakes = Fakes()
    assert world.run(*propose_args(world), fakes=fakes)[0] == 0
    before = {p.name: p.read_bytes() for p in (world.pkg / "iterations" / "i1").iterdir()}
    artefacts = {p: p.read_bytes() for p in world.analysis(1).rglob("*.json")}
    assert world.run(*propose_args(world), fakes=fakes)[0] == 0
    assert {p.name: p.read_bytes() for p in (world.pkg / "iterations" / "i1").iterdir()} == before
    assert {p: p.read_bytes() for p in world.analysis(1).rglob("*.json")} == artefacts
    # a different enum set changes the proposer artefact: write-once refuses
    world.enums.write_text(json.dumps({"slot_types": SLOT_TYPES[:3], "intents": INTENTS}), encoding="utf-8")
    code, text = world.run(*propose_args(world), fakes=fakes)
    assert code == 3 and ("write-once" in text or "different inputs" in text)


def test_without_execute_the_driver_plans_and_writes_nothing(world):
    code, text = world.run(*propose_args(world))          # no fakes, no --execute
    assert code == 0 and '"status": "planned"' in text and "tfrl_contrast_tables.py" in text
    assert not world.analysis(1).exists()


def test_open_propose_needs_the_measured_lock_p99(world):
    def no_trace(name, argv, produced):
        produced[0].parent.mkdir(parents=True, exist_ok=True)
        doc = synthetic_tables()
        doc["table_d"]["overall"]["supplied_tokens"] = {"n": 1080, "mean": None, "p50": None, "p99": None}
        produced[0].write_text(json.dumps(doc), encoding="utf-8")

    code, text = world.run(*propose_args(world), fakes=no_trace)
    assert code == 3 and "p99" in text
    code, _ = world.run(*propose_args(world), "--lock-p99-supplied-tokens", "15000", fakes=no_trace)
    assert code == 0 and world.receipt(1, "open-propose")["ace"]["t_cap"] == 15000 + 1880


# ---------------------------------------------------------------------------------------------------------------------------
# open: cell
# ---------------------------------------------------------------------------------------------------------------------------


def test_open_cell_with_an_empty_typed_arm_is_legal_and_curates_the_playbook(world):
    world.run(*propose_args(world), fakes=Fakes())
    code, text = world.run(*open_cell_args(world))
    assert code == 0, text
    receipt = world.receipt(1, "open-cell")
    assert receipt["typed_arm"] == "empty (legal)" and receipt["arms"] == ["ace", "aa", "lock"]
    assert receipt["program"] == "phase-native-module-v1-c4"
    assert receipt["ace"]["items"] == 18 and receipt["ace"]["playbook_iteration"] == 1
    playbook = ace.load_playbook(world.analysis(1) / "playbook" / "playbook-i1.json")
    assert len(playbook["items"]) == 18
    # no model-written item text reaches a receipt or the repository tree
    assert "epsilon" not in json.dumps(receipt)
    # the loader accepts the ace column under the real hooks (lock v2.3); only the release pins of the iteration are pending
    assert receipt["loader_verification"] == {"ok": True, "refusal": None}
    assert {b["id"] for b in receipt["blockers"]} == {"ace-release-pins-pending"}
    # no typed child in the archive
    assert [s for s in world.archive().states() if s["arm"] == "typed" and s["iteration"] > 0] == []


def test_open_cell_flies_a_valid_knob_candidate_as_the_typed_arm(world):
    world.run(*propose_args(world), fakes=Fakes())
    receipts = knob_receipt(12)
    typed = world.tmp / "typed.json"
    typed.write_text(json.dumps(receipts), encoding="utf-8")
    pred = predictions(world.tmp / "pred.json", receipts, 1.8)
    code, text = world.run(*open_cell_args(world, typed=typed, predictions=pred))
    assert code == 0, text
    receipt = world.receipt(1, "open-cell")
    assert receipt["arms"] == ["typ", "ace", "aa", "lock"] and receipt["program"] == "phase-native-module-v1-c5"
    assert receipt["typed_arm"]["predicted_slu_pp"] == 1.8
    block = json.loads((world.root / "configs" / "baseline" / f"{tf.names(1, 'arm')['baseline']}.json").read_text(encoding="utf-8"))
    columns = {c["column_id"]: c for c in block["native_episode"]["consumption_module"]["columns"]}
    assert columns["typ"]["overrides"] == {"knowledge_stores.train-exemplars.phase_supply.solver.k": 12}
    assert columns["ace"]["release_swap"]["store_id"] == tf.ACE_STORE_ID


def test_a_candidate_under_the_predicted_bar_leaves_the_typed_arm_empty(world):
    world.run(*propose_args(world), fakes=Fakes())
    receipts = knob_receipt(12)
    typed = world.tmp / "typed.json"
    typed.write_text(json.dumps(receipts), encoding="utf-8")
    pred = predictions(world.tmp / "pred.json", receipts, 0.2)
    code, _ = world.run(*open_cell_args(world, typed=typed, predictions=pred))
    assert code == 0
    receipt = world.receipt(1, "open-cell")
    assert receipt["typed_arm"] == "empty (legal)" and receipt["refused"] == 1
    record = json.loads((world.pkg / "iterations" / "i1" / "candidates.json").read_text(encoding="utf-8"))
    assert record["refused"][0]["refusal_code"] == "refused-prediction" and record["flown"] is None


def test_open_cell_requires_the_typed_receipts_or_an_explicit_empty_arm(world):
    world.run(*propose_args(world), fakes=Fakes())
    args = open_cell_args(world)
    args.remove("--typed-arm-empty")
    code, text = world.run(*args)
    assert code == 3 and "typed-arm-empty" in text


def test_open_cell_is_idempotent(world):
    world.run(*propose_args(world), fakes=Fakes())
    assert world.run(*open_cell_args(world))[0] == 0
    before = {p.name: p.read_bytes() for p in (world.pkg / "iterations" / "i1").iterdir()}
    assert world.run(*open_cell_args(world))[0] == 0
    assert {p.name: p.read_bytes() for p in (world.pkg / "iterations" / "i1").iterdir()} == before


# ---------------------------------------------------------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------------------------------------------------------


def stall_iteration(world: World, fakes: Fakes, t: int = 1) -> None:
    assert world.run(*propose_args(world, t), fakes=fakes)[0] == 0
    assert world.run(*open_cell_args(world, t))[0] == 0


def test_close_refuses_an_ace_state_under_the_point_floor_and_repeats_the_level(world):
    fakes = Fakes(pairs={"ace-vs-lock": contrast_doc(0.8, 0.1, 1.5), "aa-vs-lock": contrast_doc(0.1, -0.7, 0.9)})
    stall_iteration(world, fakes)
    code, text = world.run("close", "--iter", "1", fakes=fakes)
    assert code == 0, text
    receipt = world.receipt(1, "close")
    verdict = receipt["verdicts"]["ace"]
    assert verdict["status"] == "refused" and "b_point_floor" in verdict["failed"]
    assert receipt["typed_arm_was_empty"] is True and receipt["verdicts"].get("typed") is None
    states = world.archive().states()
    ace_states = [s for s in states if s["arm"] == "ace" and s["iteration"] == 1]
    assert [s["verdict"] for s in ace_states] == ["refused"]
    # a refused ACE state is still archived as the child of the previous ACE state
    assert ace_states[0]["parent_id"] == next(s["state_id"] for s in states if s["arm"] == "ace" and s["iteration"] == 0)
    curve = json.loads((world.pkg / "iterations" / "i1" / "curve.json").read_text(encoding="utf-8"))
    assert curve["typed"][0]["marked"] == "unflown" and curve["ace"][0]["marked"] == "refused"
    assert curve["typed"][0]["level"] == {"point": 0.0, "lo": 0.0, "hi": 0.0}
    meta = json.loads((world.pkg / "iterations" / "i1" / "proposer-meta.json").read_text(encoding="utf-8"))
    assert meta["never_shipped"] is True
    parent = json.loads((world.pkg / "iterations" / "i1" / "parent.json").read_text(encoding="utf-8"))
    assert parent["parent_display_id"] == drv.ROOT_DISPLAY
    assert receipt["loop_complete"] is False and receipt["next_iteration"] == 2


def test_close_accepts_an_ace_state_that_clears_the_instrument(world):
    fakes = Fakes(pairs={"ace-vs-lock": contrast_doc(2.1, 0.6, 3.6, intent=0.2, ilo=-0.2, ihi=0.6), "aa-vs-lock": contrast_doc(0.1, -0.7, 0.9)})
    stall_iteration(world, fakes)
    assert world.run("close", "--iter", "1", fakes=fakes)[0] == 0
    verdict = world.receipt(1, "close")["verdicts"]["ace"]
    assert verdict["status"] == "accepted" and verdict["failed"] == []
    assert "vacuous" in verdict["clause_d"]
    curve = json.loads((world.pkg / "iterations" / "i1" / "curve.json").read_text(encoding="utf-8"))
    assert curve["ace"][0]["level"]["point"] == pytest.approx(2.1) and curve["ace"][0]["marked"] is None


def test_close_applies_the_twin_clause_and_the_intent_guard(world):
    # beats the floor and the lower bound, but not the twin
    fakes = Fakes(pairs={"ace-vs-lock": contrast_doc(1.8, 0.3, 3.3), "aa-vs-lock": contrast_doc(2.0, 0.5, 3.5)})
    stall_iteration(world, fakes)
    assert world.run("close", "--iter", "1", fakes=fakes)[0] == 0
    assert world.receipt(1, "close")["verdicts"]["ace"]["failed"] == ["c_beats_twin"]
    # intent guard: a point loss of intent refuses a column that clears the SLU clauses
    world2 = World(world.tmp / "w2")
    fakes2 = Fakes(pairs={"ace-vs-lock": contrast_doc(2.5, 0.8, 4.2, intent=-0.4, ilo=-0.9, ihi=0.1), "aa-vs-lock": contrast_doc(0.0, -0.8, 0.8)})
    stall_iteration(world2, fakes2)
    assert world2.run("close", "--iter", "1", fakes=fakes2)[0] == 0
    assert "e_intent_guard" in world2.receipt(1, "close")["verdicts"]["ace"]["failed"]


def test_close_archives_an_accepted_typed_child_and_chooses_it_as_the_parent(world):
    receipts = knob_receipt(12)
    typed = world.tmp / "typed.json"
    typed.write_text(json.dumps(receipts), encoding="utf-8")
    pred = predictions(world.tmp / "pred.json", receipts, 1.9)
    fakes = Fakes(pairs={"typ-vs-lock": contrast_doc(2.4, 0.7, 4.0, intent=0.3, ilo=-0.1, ihi=0.7),
                         "ace-vs-lock": contrast_doc(0.2, -0.7, 1.1), "aa-vs-lock": contrast_doc(0.1, -0.7, 0.9)})
    assert world.run(*propose_args(world), fakes=fakes)[0] == 0
    assert world.run(*open_cell_args(world, typed=typed, predictions=pred))[0] == 0
    code, text = world.run("close", "--iter", "1", fakes=fakes)
    assert code == 0, text
    receipt = world.receipt(1, "close")
    assert receipt["verdicts"]["typed"]["status"] == "accepted"
    states = world.archive().states()
    child = next(s for s in states if s["arm"] == "typed" and s["iteration"] == 1)
    assert child["verdict"] == "accepted" and child["predicted_slu_pp"] == 1.9 and child["operator_class"] == "supply"
    # the spec of the accepted state is recorded so iteration 2 flies it as `par`
    spec = json.loads((world.pkg / "archive-specs" / f"{child['state_id']}.json").read_text(encoding="utf-8"))
    assert spec == {"overrides": {"knowledge_stores.train-exemplars.phase_supply.solver.k": 12}}
    parent = json.loads((world.pkg / "iterations" / "i1" / "parent.json").read_text(encoding="utf-8"))
    assert parent["parent_state_id"] == child["state_id"]
    curve = json.loads((world.pkg / "iterations" / "i1" / "curve.json").read_text(encoding="utf-8"))
    assert curve["typed"][0]["level"]["point"] == pytest.approx(2.4)
    # iteration 2 opens from the accepted parent and flies `par` beside the ace arm
    assert world.run(*propose_args(world, 2), fakes=Fakes())[0] == 0
    assert world.receipt(2, "open-propose")["parent_display_id"] == child["state_id"][:48]
    assert world.run(*open_cell_args(world, 2))[0] == 0
    cell = world.receipt(2, "open-cell")
    assert cell["arms"] == ["par", "ace", "aa", "lock"] and cell["program"] == "phase-native-module-v1-c5"


def test_close_archives_a_refused_typed_child_and_masks_nothing_after_one(world):
    receipts = knob_receipt(12)
    typed = world.tmp / "typed.json"
    typed.write_text(json.dumps(receipts), encoding="utf-8")
    pred = predictions(world.tmp / "pred.json", receipts, 1.9)
    fakes = Fakes(pairs={"typ-vs-lock": contrast_doc(0.5, -0.9, 1.9), "ace-vs-lock": contrast_doc(0.2, -0.7, 1.1),
                         "aa-vs-lock": contrast_doc(0.1, -0.7, 0.9)})
    assert world.run(*propose_args(world), fakes=fakes)[0] == 0
    assert world.run(*open_cell_args(world, typed=typed, predictions=pred))[0] == 0
    assert world.run("close", "--iter", "1", fakes=fakes)[0] == 0
    receipt = world.receipt(1, "close")
    assert receipt["verdicts"]["typed"]["status"] == "refused"
    child = next(s for s in world.archive().states() if s["arm"] == "typed" and s["iteration"] == 1)
    assert child["verdict"] == "refused"
    assert not (world.pkg / "archive-specs" / f"{child['state_id']}.json").exists()
    parent = json.loads((world.pkg / "iterations" / "i1" / "parent.json").read_text(encoding="utf-8"))
    assert parent["parent_display_id"] == drv.ROOT_DISPLAY and parent["masked_classes"] == []
    # the refused sibling is shown to the next proposer (rejected-edit buffer + state_credit)
    assert world.run(*propose_args(world, 2), fakes=Fakes())[0] == 0
    context = json.loads((world.analysis(2) / "proposer-context.json").read_text(encoding="utf-8"))
    assert context["refused_buffer"][0]["refusal_code"] == "refused-by-instrument"
    assert context["meta_summary"]["supply"]["refused"] == 1


def test_close_reads_an_offline_delivery_candidate_with_the_fixed_floor(world):
    cand = {"schema": tp.CANDIDATE_SCHEMA_ID, "iteration": 1, "parent_state_id": drv.ROOT_DISPLAY, "operator_class": "delivery",
            "operator": "deliver-rule",
            "target": {"failure_class": "SPURIOUS", "slot_types": ["person"], "scenarios": ["social"], "value_in_supply": "none"},
            "hypothesis_code": "rule-filter",
            "applications": [{"family": "ee10", "guard": "wilson", "types": ["person"], "intents": []}]}
    entries = [{"allowed_classes": ["delivery", "scope"], "receipt": tp.read_typed_candidate_receipt(json.dumps(cand))}]
    typed = world.tmp / "typed.json"
    typed.write_text(json.dumps(entries), encoding="utf-8")
    pred = world.tmp / "pred.json"
    pred.write_text(json.dumps({"schema": tp.PREDICTIONS_SCHEMA_ID, "predictions": {}}), encoding="utf-8")
    fakes = Fakes(pairs={"ace-vs-lock": contrast_doc(0.2, -0.7, 1.1), "aa-vs-lock": contrast_doc(0.1, -0.7, 0.9)})
    assert world.run(*propose_args(world), fakes=fakes)[0] == 0
    assert world.run(*open_cell_args(world, typed=typed, predictions=pred))[0] == 0
    assert world.receipt(1, "open-cell")["offline"] == 1
    cid = entries[0]["receipt"]["candidate_id"]
    # cross-fitted CI lower bound above 0 but the point under 0.67 pp: refused
    fakes.fits = {cid[:8]: fit_report(0.5, 0.1)}
    assert world.run("close", "--iter", "1", fakes=fakes)[0] == 0
    offline = world.receipt(1, "close")["verdicts"]["offline"][0]
    assert offline["status"] == "refused" and offline["clauses"]["point_ge_floor"]["pass"] is False
    # and the same report above the floor is accepted (fresh world)
    w2 = World(world.tmp / "w2")
    typed2 = w2.tmp / "typed.json"
    typed2.write_text(json.dumps(entries), encoding="utf-8")
    pred2 = w2.tmp / "pred.json"
    pred2.write_text(json.dumps({"schema": tp.PREDICTIONS_SCHEMA_ID, "predictions": {}}), encoding="utf-8")
    fakes2 = Fakes(pairs=fakes.pairs, fits={cid[:8]: fit_report(0.9, 0.2)})
    assert w2.run(*propose_args(w2), fakes=fakes2)[0] == 0
    assert w2.run(*open_cell_args(w2, typed=typed2, predictions=pred2))[0] == 0
    assert w2.run("close", "--iter", "1", fakes=fakes2)[0] == 0
    assert w2.receipt(1, "close")["verdicts"]["offline"][0]["status"] == "accepted"


def test_close_is_idempotent_and_refuses_a_changed_read(world):
    fakes = Fakes(pairs={"ace-vs-lock": contrast_doc(0.8, 0.1, 1.5), "aa-vs-lock": contrast_doc(0.1, -0.7, 0.9)})
    stall_iteration(world, fakes)
    assert world.run("close", "--iter", "1", fakes=fakes)[0] == 0
    before = {p.name: p.read_bytes() for p in (world.pkg / "iterations" / "i1").iterdir()}
    states_before = {p.name: p.read_bytes() for p in (world.pkg / "archive").iterdir()}
    assert world.run("close", "--iter", "1", fakes=fakes)[0] == 0
    assert {p.name: p.read_bytes() for p in (world.pkg / "iterations" / "i1").iterdir()} == before
    assert {p.name: p.read_bytes() for p in (world.pkg / "archive").iterdir()} == states_before
    # the sealed score summary changes: the receipt refuses to be overwritten
    summary = world.data / "runs" / tf.names(1, "arm")["run_id"] / tf.names(1, "arm")["attempt_id"] / "supply-variants" / "score-summary.json"
    summary.write_text(json.dumps({"arms": {a: {"official": {"slu_f1": 0.7, "intent_accuracy": 0.8}} for a in ("ace", "aa", "lock")}}),
                       encoding="utf-8")
    code, text = world.run("close", "--iter", "1", fakes=fakes)
    assert code == 3 and ("different" in text or "write-once" in text)


def test_close_without_execute_stops_at_the_first_missing_output_and_archives_nothing(world):
    fakes = Fakes()
    stall_iteration(world, fakes)
    before = sorted(p.name for p in (world.pkg / "archive").iterdir())
    code, text = world.run("close", "--iter", "1")          # no fakes, no --execute
    assert code == 0 and '"status": "planned"' in text and "stage3_rollout_score.py" in text and "stage3_paired_read.py" in text
    assert sorted(p.name for p in (world.pkg / "archive").iterdir()) == before
    assert lib.read_receipt(world.pkg / "iterations" / "i1", "close") is None


def test_close_needs_the_open_cell_receipt(world):
    code, text = world.run("close", "--iter", "1", fakes=Fakes())
    assert code == 3 and "open-cell receipt" in text


def test_the_ace_credit_file_and_the_next_curation_use_per_row_scores(world):
    fakes = Fakes(pairs={"ace-vs-lock": contrast_doc(0.8, 0.1, 1.5), "aa-vs-lock": contrast_doc(0.1, -0.7, 0.9)})
    stall_iteration(world, fakes)
    rows = {f"slurp:train:{i:06d}:audio-{i}": 0.5 for i in range(40)}
    lock_scores = dict(rows)
    ace_scores = {sid: (0.7 if i % 2 == 0 else 0.4) for i, sid in enumerate(rows)}
    annotations = {sid: {"scenario": "calendar", "slot_types": ["date"]} for sid in rows}
    import tfrl_row_scores as rs

    export = world.tmp / "rows.json"
    export.write_text(json.dumps(rs.build_row_scores(lock_scores, ace_scores, annotations)), encoding="utf-8")
    assert world.run("close", "--iter", "1", "--row-scores", str(export), fakes=fakes)[0] == 0
    assert world.receipt(1, "close")["ace_credit"] == "written"
    credit = json.loads((world.analysis(1) / "ace-credit.json").read_text(encoding="utf-8"))
    assert credit["playbook_iteration"] == 1 and len(credit["rows"]) == 40
    assert all(len(r["row_digest"]) == 64 and "slurp" not in json.dumps(r) for r in credit["rows"])
    # iteration 2: the curator applies script counters to the items of playbook i1, then grows it into i2
    assert world.run(*propose_args(world, 2), fakes=Fakes())[0] == 0
    assert world.run(*open_cell_args(world, 2))[0] == 0
    playbook = ace.load_playbook(world.analysis(2) / "playbook" / "playbook-i2.json")
    scoped = [item for item in playbook["items"] if item["created_iteration"] == 1 and "calendar" in item["scope"]["scenarios"]]
    assert scoped and scoped[0]["helpful"] == 20 and scoped[0]["harmful"] == 20 and scoped[0]["scoped_rows"] == 40


def test_the_stop_rule_closes_the_loop_after_three_iterations_and_status_reports_it(world):
    fakes = Fakes(pairs={"ace-vs-lock": contrast_doc(0.2, -0.7, 1.1), "aa-vs-lock": contrast_doc(0.1, -0.7, 0.9)})
    code, _ = world.run("status")
    assert code == 0 and "open --iter 1 --stage propose" in "\n".join(world.out)
    for t in (1, 2, 3):
        assert world.run(*propose_args(world, t), fakes=fakes)[0] == 0
        assert world.run(*open_cell_args(world, t))[0] == 0
        assert world.run("close", "--iter", str(t), fakes=fakes)[0] == 0
    receipt = world.receipt(3, "close")
    assert receipt["loop_complete"] is True and receipt["next_iteration"] is None
    assert world.run("status")[0] == 0
    assert "loop complete" in "\n".join(world.out)
    curve = json.loads((world.pkg / "iterations" / "i3" / "curve.json").read_text(encoding="utf-8"))
    assert [p["marked"] for p in curve["typed"]] == ["unflown"] * 3 and [p["marked"] for p in curve["ace"]] == ["refused"] * 3
    code, text = world.run(*propose_args(world, 4), fakes=fakes)
    assert code == 3 or "iteration must be one of" in text


def test_the_archive_never_holds_a_text_field(world):
    fakes = Fakes(pairs={"ace-vs-lock": contrast_doc(2.1, 0.6, 3.6), "aa-vs-lock": contrast_doc(0.1, -0.7, 0.9)})
    stall_iteration(world, fakes)
    world.run("close", "--iter", "1", fakes=fakes)
    for state in world.archive().states():
        ar.assert_no_text_fields(state)
    for path in (world.pkg / "iterations" / "i1").glob("*.json"):
        text = path.read_text(encoding="utf-8")
        assert "epsilon" not in text and "boundary errors" not in text


# ---------------------------------------------------------------------------------------------------------------------------
# the construction-source material (coordinator resolution of 2026-10-11): tables from the R01C column, ACE releases on the R01C rosters
# ---------------------------------------------------------------------------------------------------------------------------


class ArgvFakes(Fakes):
    """``Fakes`` that also records the argv of every stand-in call, by step name."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.argvs: dict[str, list[list[str]]] = {}

    def __call__(self, name: str, argv: list[str], produced: list[Path]) -> None:
        self.argvs.setdefault(name, []).append(list(argv))
        super().__call__(name, argv, produced)


def flag(argv: list[str], name: str) -> str:
    return argv[argv.index(name) + 1]


def test_every_iteration_reads_its_tables_from_the_construction_column_never_from_fold_b(world):
    fakes = ArgvFakes(pairs={"ace-vs-lock": contrast_doc(0.2, -0.7, 1.1), "aa-vs-lock": contrast_doc(0.1, -0.7, 0.9)})
    for t in (1, 2, 3):
        assert world.run(*propose_args(world, t), fakes=fakes)[0] == 0
        assert world.run(*open_cell_args(world, t))[0] == 0
        assert world.run("close", "--iter", str(t), fakes=fakes)[0] == 0
    assert len(fakes.argvs["tables"]) == 3
    for argv in fakes.argvs["tables"]:
        assert flag(argv, "--run-id") == tf.CONST_RUN_ID == "SAEA-SLURP-STAGE3-TFRL-CONSTRUCTION-LOCK-R01C-V1"
        assert flag(argv, "--attempt") == tf.CONST_ATTEMPT_ID and flag(argv, "--rows") == "625" and flag(argv, "--arm") == "lock"
        assert flag(argv, "--scorer") == "slurp-slu-official-train" and flag(argv, "--split") == "train"
        assert "FOLD-B" not in " ".join(argv).upper() and "R6-PERCEPTION" not in " ".join(argv).upper()
    for t in (1, 2, 3):
        source = world.receipt(t, "open-propose")["source_column"]
        assert source["run_id"] == tf.CONST_RUN_ID and source["rows"] == 625 and source["roster_id"] == tf.CONST_ROSTER_ID
        assert source["roster"] == "docs/receipts/rosters/slurp-stage3-construction-r01c.json" and source["override"] is False
    # the Fold B column of iteration t is read at close (selection) and feeds the next iteration only through the buffer and the counters
    close_runs = {flag(a, "--run") for a in fakes.argvs["score-columns"]}
    assert close_runs == {tf.names(t, "arm")["run_id"] for t in (1, 2, 3)}
    assert all(flag(a, "--roster") == tf.ROSTER["arm"] for a in fakes.argvs["score-columns"])


def test_a_source_override_is_recorded_and_changes_only_the_column_named(world):
    fakes = ArgvFakes()
    args = propose_args(world) + ["--source-run-id", "SAEA-OVERRIDE-RUN", "--source-attempt", "attempt-override"]
    assert world.run(*args, fakes=fakes)[0] == 0
    argv = fakes.argvs["tables"][0]
    assert flag(argv, "--run-id") == "SAEA-OVERRIDE-RUN" and flag(argv, "--attempt") == "attempt-override" and flag(argv, "--rows") == "625"
    assert world.receipt(1, "open-propose")["source_column"]["override"] is True


def test_the_protocol_names_the_lock_the_material_source_and_fold_b_as_held_out_selection():
    protocol = json.loads((REPO / tf.PROTOCOL_RELPATH).read_text(encoding="utf-8"))
    assert protocol["lock"]["lock"] == "v2.3" and protocol["lock"]["parent_lock"] == "v2.2"
    source = protocol["material_source"]
    assert source["run_id"] == tf.CONST_RUN_ID and source["rows"] == 625 and source["roster"] == "SLURP-STAGE3-CONSTRUCTION-R01C"
    assert source["measurement_design"] == "material-source" and source["claims_benefit"] is False and source["program"] == "phase-native-module-v1-c2"
    assert "HELD-OUT selection" in source["fold_b_role"] and "numbers, not knowledge" in source["fold_b_role"]
    roles = protocol["fold_roles"]
    assert roles["material"]["roster"] == "SLURP-STAGE3-CONSTRUCTION-R01C" and "HELD-OUT selection" in roles["select"]["role"]
    assert roles["confirm"]["fold"] == "SLURP-EVO-FOLD-A-V2"
    assert "construction-source lock column" in protocol["ace"]["playbook_flow"] and "VER-1a" not in protocol["ace"]["playbook_flow"]
    assert "construction-source lock column" in protocol["t_cap"]["lock_p99_supplied_tokens"]
    assert source["ace_release_staging"]["forbidden_rosters"] == ["SLURP-EVO-FOLD-A-V2", "SLURP-EVO-FOLD-B-V2", "DEV-1000"]


# ---- the ACE release staging and the preparer's roster guard

I0_REGISTRATION = REPO / lib.ACE_I0_REGISTRATION_RELPATH


def staged_world(world, monkeypatch=None):
    """Iteration 1 through ``open --stage cell``: the playbook i1 and its release inputs are staged on the data root."""

    assert world.run(*propose_args(world), fakes=Fakes())[0] == 0
    assert world.run(*open_cell_args(world))[0] == 0
    return json.loads((world.pkg / "ace-playbook-i1-release-registration.json").read_text(encoding="utf-8"))


def place_data_root_pins(world, registration: dict) -> None:
    for key, source in (("construction_scope", tf.CONST_ROSTER["arm"]), ("permitted_roster", lib.ACE_CARRIER_ROSTER_RELPATH)):
        pin = registration[key]
        assert pin["root"] == "data" and tf.sha256_file(REPO / source) == pin["sha256"]          # the repository copy IS the pinned file
        target = world.data / pin["relpath"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / source, target)


def test_release_staging_binds_the_registration_to_the_r01c_construction_rosters(world):
    registration = staged_world(world)
    i0 = json.loads(I0_REGISTRATION.read_text(encoding="utf-8"))
    for key in ("construction_scope", "permitted_roster", "forbidden_rosters", "source_split_identity_hash", "builder_policy_id", "store_id",
                "store_role", "source_partition_role", "carrier_lock_key"):
        assert registration[key] == i0[key], key
    assert registration["registration_id"] == "SAEA-SLURP-ACE-PLAYBOOK-PREPARATION-I1"
    assert registration["output_namespace"] == "knowledge/slurp/semantic/ace-playbook-i1"
    assert registration["authored_source"]["root"] == "data"
    assert registration["authored_source"]["relpath"].startswith(f"{tf.ANALYSIS_ROOT}/i1/ace-release-staging/source-ace-playbook-i1")
    assert (world.data / registration["authored_source"]["relpath"]).is_file()
    assert tf.sha256_file(world.data / registration["authored_source"]["relpath"]) == registration["authored_source"]["sha256"]
    receipt = world.receipt(1, "open-cell")["ace"]["release_staging"]
    assert receipt["carrier_roster"] == lib.ACE_CARRIER_ROSTER_RELPATH and receipt["carriers"] == 50
    assert receipt["source_split_identity_hash"] == i0["source_split_identity_hash"] and receipt["registration"]["sha256"]
    # every source id of the staged rows is a carrier: inside the construction roster R01C, outside Fold B
    source = json.loads((world.data / registration["authored_source"]["relpath"]).read_text(encoding="utf-8"))
    carriers = {sid for row in source["rows"] for sid in row["source_sample_ids"]}
    r01c = {str(i["sample_id"]) for i in json.loads((REPO / tf.CONST_ROSTER["arm"]).read_text(encoding="utf-8"))["items"]}
    fold_b = {str(i["sample_id"]) for i in json.loads((REPO / tf.ROSTER["arm"]).read_text(encoding="utf-8"))["items"]}
    assert len(carriers) == 50 and carriers <= r01c and carriers.isdisjoint(fold_b)
    assert len(source["rows"]) == 18                                   # one authored row per playbook item


def test_the_preparer_accepts_the_i1_release_with_r01c_carriers_and_refuses_it_with_fold_b_carriers(world, monkeypatch):
    from speech_aware_evidence_acquisition.core.semantic_knowledge_preparation import (
        SemanticKnowledgePreparationError, prepare_semantic_knowledge_store)

    registration = staged_world(world, monkeypatch)
    place_data_root_pins(world, registration)
    mini = world.tmp / "mini-repo"                       # the preparer confines the registration and the repo-rooted pins to one repo root
    for pin in registration["forbidden_rosters"]:
        (mini / pin["relpath"]).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / pin["relpath"], mini / pin["relpath"])
    shutil.copyfile(world.pkg / "ace-playbook-i1-release-registration.json", mini / "ace-playbook-i1-release-registration.json")
    result = prepare_semantic_knowledge_store(mini / "ace-playbook-i1-release-registration.json", repo_root=mini, data_root=world.data)
    snapshot = json.loads((world.data / result["completion"]["snapshot"]["relpath"]).read_text(encoding="utf-8"))
    r01c = {str(i["sample_id"]) for i in json.loads((REPO / tf.CONST_ROSTER["arm"]).read_text(encoding="utf-8"))["items"]}
    fold_b = [str(i["sample_id"]) for i in json.loads((REPO / tf.ROSTER["arm"]).read_text(encoding="utf-8"))["items"]]
    assert set(snapshot["source_sample_ids"]) <= r01c and set(snapshot["source_sample_ids"]).isdisjoint(fold_b)
    assert result["completion"]["outer_construction_scope"]["split_identity_hash"] == "f56bc386776421aec2d8001d8697611b01c9b0562885a462759b15531e2f4515"
    # the same playbook staged with FOLD B carriers (the defect of the first driver version) is refused by the same preparer
    playbook = ace.load_playbook(world.analysis(1) / "playbook" / "playbook-i1.json")
    binding = lib.ace_release_binding(REPO)
    bad_path = mini / "ace-playbook-ifoldb-release-registration.json"
    ace.build_playbook_release(
        dict(playbook), data_root=world.data, carrier_sample_ids=sorted(fold_b)[:50], legal_intent_ids=INTENTS,
        source_split_identity_hash=binding["source_split_identity_hash"], release_dir=f"{tf.ANALYSIS_ROOT}/i1/ace-release-foldb",
        registration_binding=binding["registration_binding"], registration_path=bad_path,
        registration_id="SAEA-SLURP-ACE-PLAYBOOK-PREPARATION-IFOLDB", output_namespace="knowledge/slurp/semantic/ace-playbook-ifoldb")
    with pytest.raises(SemanticKnowledgePreparationError) as refusal:
        prepare_semantic_knowledge_store(bad_path, repo_root=mini, data_root=world.data)
    assert not (world.data / "knowledge" / "slurp" / "semantic" / "ace-playbook-ifoldb").exists()
    assert "subset of the permitted construction roster" in str(refusal.value)       # the roster guard, named


def test_the_shipped_release_rows_survive_the_preparer_with_a_rank_ordered_prior_score_in_unit_interval(world):
    from speech_aware_evidence_acquisition.core.semantic_knowledge_preparation import prepare_semantic_knowledge_store

    registration = staged_world(world)
    place_data_root_pins(world, registration)
    mini = world.tmp / "mini-repo"
    for pin in registration["forbidden_rosters"]:
        (mini / pin["relpath"]).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / pin["relpath"], mini / pin["relpath"])
    shutil.copyfile(world.pkg / "ace-playbook-i1-release-registration.json", mini / "ace-playbook-i1-release-registration.json")
    prepare_semantic_knowledge_store(mini / "ace-playbook-i1-release-registration.json", repo_root=mini, data_root=world.data)


def test_the_release_binding_refuses_a_permitted_roster_that_is_not_the_pinned_file_and_a_carrier_outside_r01c(tmp_path):
    root = tmp_path / "repo"
    (root / "docs/readiness/2026-10-11-slurp-tfrl-loop-v1").mkdir(parents=True)
    (root / "docs/receipts/rosters").mkdir(parents=True)
    shutil.copyfile(I0_REGISTRATION, root / lib.ACE_I0_REGISTRATION_RELPATH)
    shutil.copyfile(REPO / tf.CONST_ROSTER["arm"], root / tf.CONST_ROSTER["arm"])
    shutil.copyfile(REPO / lib.ACE_CARRIER_ROSTER_RELPATH, root / lib.ACE_CARRIER_ROSTER_RELPATH)
    for pin in json.loads(I0_REGISTRATION.read_text(encoding="utf-8"))["forbidden_rosters"]:
        (root / pin["relpath"]).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / pin["relpath"], root / pin["relpath"])
    assert len(lib.ace_release_binding(root)["carrier_sample_ids"]) == 50
    # a tampered permitted roster no longer hashes to the registration's pin
    permitted = json.loads((root / lib.ACE_CARRIER_ROSTER_RELPATH).read_text(encoding="utf-8"))
    tampered = copy.deepcopy(permitted)
    tampered["items"][0]["sample_id"] = "slurp:train:000000:audio-0000000000"      # sorts first, so it is a carrier; not an R01C row
    (root / lib.ACE_CARRIER_ROSTER_RELPATH).write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(lib.LoopError, match="does not hash"):
        lib.ace_release_binding(root)
    # even with the pin re-hashed, a carrier outside R01C (here a Fold B row) is refused by the driver itself
    registration = json.loads((root / lib.ACE_I0_REGISTRATION_RELPATH).read_text(encoding="utf-8"))
    registration["permitted_roster"]["sha256"] = tf.sha256_file(root / lib.ACE_CARRIER_ROSTER_RELPATH)
    (root / lib.ACE_I0_REGISTRATION_RELPATH).write_text(json.dumps(registration), encoding="utf-8")
    with pytest.raises(lib.LoopError, match="outside the construction roster"):
        lib.ace_release_binding(root)


# ---------------------------------------------------------------------------------------------------------------------------
# iteration-1 results-read defects (2026-10-11): stale playbook file, unread offline candidate, receipt flag, GPU plan
# ---------------------------------------------------------------------------------------------------------------------------


def stale_empty_playbook(world: World, t: int = 1) -> dict:
    """Write what the superseded first ``open --stage cell`` run left behind: the EMPTY playbook of the iteration."""

    constants = ace.with_measured_lock_p99(14641)
    empty = ace.curate(ace.empty_playbook(), [], {}, constants)
    assert empty["iteration"] == t and not empty["items"]
    path = world.analysis(t) / "playbook" / f"playbook-i{t}.json"
    ace.write_playbook(path, empty)
    return empty


def make_ctx_for(world: World):
    return drv.make_ctx(drv.build_parser().parse_args(["--repo-root", str(world.root), "--package-dir", str(world.pkg),
                                                       "--data-root", str(world.data), "status"]))


def test_a_stale_playbook_file_is_superseded_not_kept_and_not_the_one_the_receipt_names(world):
    world.run(*propose_args(world), fakes=Fakes())
    stale = stale_empty_playbook(world)
    path = world.analysis(1) / "playbook" / "playbook-i1.json"
    assert world.run(*open_cell_args(world))[0] == 0
    receipt = world.receipt(1, "open-cell")
    live = ace.load_playbook(path)
    assert receipt["ace"]["playbook_file"] == "rewritten" and live["content_hash"] == receipt["ace"]["playbook_content_hash"]
    assert len(live["items"]) == 18 and live["content_hash"] != stale["content_hash"]
    kept = sorted(path.parent.glob("playbook-i1.superseded-*.json"))
    assert len(kept) == 1 and ace.load_playbook(kept[0])["content_hash"] == stale["content_hash"]
    before = {p.name: p.read_bytes() for p in path.parent.iterdir()}
    assert world.run(*open_cell_args(world))[0] == 0
    assert {p.name: p.read_bytes() for p in path.parent.iterdir()} == before


def test_the_flown_playbook_is_resolved_by_the_hash_in_the_open_cell_receipt(world):
    world.run(*propose_args(world), fakes=Fakes())
    assert world.run(*open_cell_args(world))[0] == 0
    ctx = make_ctx_for(world)
    want = world.receipt(1, "open-cell")["ace"]["playbook_content_hash"]
    stale_empty_playbook(world)
    path, playbook = drv.resolve_playbook(ctx, 1)
    assert path == drv.staging_playbook_file(ctx, 1) and playbook["content_hash"] == want
    drv.staging_playbook_file(ctx, 1).unlink()
    with pytest.raises(lib.LoopError, match="repair --iter 1"):
        drv.resolve_playbook(ctx, 1)


def test_the_next_iteration_curates_from_the_flown_playbook_even_when_the_primary_file_is_stale(world):
    fakes = Fakes(pairs={"ace-vs-lock": contrast_doc(0.8, 0.1, 1.5), "aa-vs-lock": contrast_doc(0.1, -0.7, 0.9)})
    stall_iteration(world, fakes)
    assert world.run("close", "--iter", "1", fakes=fakes)[0] == 0
    stale_empty_playbook(world)
    assert world.run(*propose_args(world, 2), fakes=Fakes())[0] == 0
    assert world.run(*open_cell_args(world, 2))[0] == 0
    grown = ace.load_playbook(world.analysis(2) / "playbook" / "playbook-i2.json")
    assert len([i for i in grown["items"] if i["created_iteration"] == 1]) == 18


def test_close_asserts_that_the_archived_playbook_hash_is_the_one_behind_the_release(world):
    fakes = Fakes(pairs={"ace-vs-lock": contrast_doc(0.8, 0.1, 1.5), "aa-vs-lock": contrast_doc(0.1, -0.7, 0.9)})
    stall_iteration(world, fakes)
    ctx = make_ctx_for(world)
    opened = world.receipt(1, "open-cell")
    good = ace.load_playbook(drv.staging_playbook_file(ctx, 1))
    assert drv.assert_playbook_binding(ctx, 1, opened, good) == opened["ace"]["playbook_content_hash"]
    other = ace.curate(ace.empty_playbook(), [], {}, ace.with_measured_lock_p99(14641))
    with pytest.raises(lib.LoopError, match="not the one behind the pinned release"):
        drv.assert_playbook_binding(ctx, 1, opened, other)
    ace.write_playbook(drv.staging_playbook_file(ctx, 1), other)
    code, text = world.run("close", "--iter", "1", fakes=fakes)
    assert code == 3 and "staged release playbook" in text
    assert [s for s in world.archive().states() if s["arm"] == "ace" and s["iteration"] == 1] == []


def test_a_correction_record_repairs_the_archived_hash_without_editing_the_state_file(world):
    fakes = Fakes(pairs={"ace-vs-lock": contrast_doc(0.8, 0.1, 1.5), "aa-vs-lock": contrast_doc(0.1, -0.7, 0.9)})
    stall_iteration(world, fakes)
    assert world.run("close", "--iter", "1", fakes=fakes)[0] == 0
    good = next(s for s in world.archive().states() if s["arm"] == "ace" and s["iteration"] == 1)
    right = good["artefact_hashes"]["playbook_release"]
    wrong_hash = tf.canonical_sha256({"the": "stale empty playbook"})
    (world.pkg / "archive" / f"state-{good['state_id']}.json").unlink()
    bad = ar.build_state(artefact_hashes={"playbook_release": wrong_hash}, parent_id=good["parent_id"], iteration=1, operator_class="playbook",
                         candidate_id="ace-i1", verdict=good["verdict"], arm="ace", credit=good["credit"], run_id=good["read"]["run_id"],
                         attempt=1)
    world.archive().put(bad)
    raw = (world.pkg / "archive" / f"state-{bad['state_id']}.json").read_bytes()
    code, text = world.run("repair", "--iter", "1", "--skip-playbook-file", fakes=fakes)
    assert code == 0, text
    corrections = sorted((world.pkg / "archive" / "corrections").glob("state-*.json"))
    assert [c.name for c in corrections] == [f"state-{bad['state_id']}-playbook-hash.json"]
    record = json.loads(corrections[0].read_text(encoding="utf-8"))
    assert (record["wrong"], record["right"], record["artefact"]) == (wrong_hash, right, "playbook_release")
    assert record["derives_from"]["field"] == "ace.playbook_content_hash"
    assert record["derives_from"]["receipt"].endswith("open-cell-receipt.json")
    assert (world.pkg / "archive" / f"state-{bad['state_id']}.json").read_bytes() == raw
    view = next(s for s in world.archive().states() if s["arm"] == "ace" and s["iteration"] == 1)
    assert view["state_id"] == bad["state_id"] and view["artefact_hashes"]["playbook_release"] == right
    assert view["corrections"][0]["wrong"] == wrong_hash
    assert world.run("repair", "--iter", "1", "--skip-playbook-file", fakes=fakes)[0] == 0
    assert len(list((world.pkg / "archive" / "corrections").glob("state-*.json"))) == 1
    for name in ("close-receipt", "curve", "parent", "proposer-meta"):       # the close outputs that named the original (wrong-hash) state
        (world.pkg / "iterations" / "i1" / f"{name}.json").unlink()
    code, text = world.run("close", "--iter", "1", fakes=fakes)
    assert code == 0, text
    assert len([s for s in world.archive().states() if s["arm"] == "ace" and s["iteration"] == 1]) == 1
    assert world.receipt(1, "close")["verdicts"]["ace"]["state_id"] == bad["state_id"]
    sha_with = lib.archive_sha256(world.pkg / "archive")
    shutil.rmtree(world.pkg / "archive" / "corrections")
    assert lib.archive_sha256(world.pkg / "archive") != sha_with


def delivery_entries(family: str, types: list[str], intents: list[str], iteration: int = 1) -> list[dict]:
    cand = {"schema": tp.CANDIDATE_SCHEMA_ID, "iteration": iteration, "parent_state_id": drv.ROOT_DISPLAY, "operator_class": "delivery",
            "operator": "deliver-rule",
            "target": {"failure_class": "SPURIOUS", "slot_types": types, "scenarios": ["alarm"], "value_in_supply": "none"},
            "hypothesis_code": "rule-filter",
            "applications": [{"family": family, "guard": "none", "types": types, "intents": intents}]}
    return [{"allowed_classes": ["delivery", "scope"], "receipt": tp.read_typed_candidate_receipt(json.dumps(cand))}]


def offline_world(world: World, entries: list[dict], fakes: Fakes) -> None:
    typed = world.tmp / "typed.json"
    typed.write_text(json.dumps(entries), encoding="utf-8")
    pred = world.tmp / "pred.json"
    pred.write_text(json.dumps({"schema": tp.PREDICTIONS_SCHEMA_ID, "predictions": {}}), encoding="utf-8")
    assert world.run(*propose_args(world), fakes=fakes)[0] == 0
    assert world.run(*open_cell_args(world, typed=typed, predictions=pred))[0] == 0


def test_an_offline_candidate_of_an_unsupported_family_is_archived_refused_never_skipped(world):
    entries = delivery_entries("fx-month-ordinal", ["date"], [])
    fakes = Fakes(pairs={"ace-vs-lock": contrast_doc(0.2, -0.7, 1.1), "aa-vs-lock": contrast_doc(0.1, -0.7, 0.9)})
    offline_world(world, entries, fakes)
    assert world.receipt(1, "open-cell")["offline"] == 1
    assert world.run("close", "--iter", "1", fakes=fakes)[0] == 0
    verdict = world.receipt(1, "close")["verdicts"]["offline"][0]
    assert verdict["status"] == "refused" and verdict["refusal_code"] == "offline-family-unsupported"
    assert not any(name.startswith("delivery-fit-") for name in fakes.calls)
    child = next(s for s in world.archive().states() if s["arm"] == "typed" and s["iteration"] == 1)
    assert child["verdict"] == "refused" and child["refusal_code"] == "offline-family-unsupported"
    assert child["credit"] is None and child["read"] is None and child["candidate_id"] == entries[0]["receipt"]["candidate_id"]
    parent = json.loads((world.pkg / "iterations" / "i1" / "parent.json").read_text(encoding="utf-8"))
    assert parent["ranking"][0]["n_children"] == 0 and parent["masked_classes"] == []
    assert world.run(*propose_args(world, 2), fakes=Fakes())[0] == 0
    context = json.loads((world.analysis(2) / "proposer-context.json").read_text(encoding="utf-8"))
    assert context["refused_buffer"][0]["refusal_code"] == "offline-family-unsupported"
    assert "realised_d_slu_pp" not in context["refused_buffer"][0]


def test_fx_oclock_is_read_by_the_fitter_with_the_candidates_own_scope(world):
    entries = delivery_entries("fx-oclock", ["time"], ["alarm_query", "alarm_set"])
    cid = entries[0]["receipt"]["candidate_id"]
    argvs: list[list[str]] = []

    class Spy(Fakes):
        def __call__(self, name, argv, produced):
            if name.startswith("delivery-fit-"):
                argvs.append(list(argv))
            super().__call__(name, argv, produced)

    fakes = Spy(pairs={"ace-vs-lock": contrast_doc(0.2, -0.7, 1.1), "aa-vs-lock": contrast_doc(0.1, -0.7, 0.9)},
                fits={cid[:8]: fit_report(0.0, 0.0, refused=True)})
    offline_world(world, entries, fakes)
    assert world.run("close", "--iter", "1", fakes=fakes)[0] == 0
    assert flag(argvs[0], "--family") == "oclock" and flag(argvs[0], "--types") == "time"
    assert flag(argvs[0], "--intents") == "alarm_query,alarm_set"
    verdict = world.receipt(1, "close")["verdicts"]["offline"][0]
    assert verdict["status"] == "refused" and verdict["family"] == "fx-oclock" and "refusal_code" not in verdict
    child = next(s for s in world.archive().states() if s["arm"] == "typed" and s["iteration"] == 1)
    assert child["credit"] is not None and child["read"]["attempt"] == 1


def test_the_receipt_separates_an_empty_typed_arm_by_measurement_from_the_input_flag(world):
    world.run(*propose_args(world), fakes=Fakes())
    assert world.run(*open_cell_args(world))[0] == 0
    receipt = world.receipt(1, "open-cell")
    assert receipt["inputs"]["typed_arm_empty"] is True and receipt["typed_arm_empty_by_measurement"] is False
    w2 = World(world.tmp / "w2")
    offline_world(w2, delivery_entries("fx-oclock", ["time"], []), Fakes())
    receipt2 = w2.receipt(1, "open-cell")
    assert receipt2["typed_arm"] == "empty (legal)" and receipt2["inputs"]["typed_arm_empty"] is False
    assert receipt2["typed_arm_empty_by_measurement"] is True
    w3 = World(world.tmp / "w3")
    receipts = knob_receipt(12)
    typed = w3.tmp / "typed.json"
    typed.write_text(json.dumps(receipts), encoding="utf-8")
    w3.run(*propose_args(w3), fakes=Fakes())
    assert w3.run(*open_cell_args(w3, typed=typed, predictions=predictions(w3.tmp / "pred.json", receipts, 1.8)))[0] == 0
    assert w3.receipt(1, "open-cell")["typed_arm_empty_by_measurement"] is False


def test_planned_gpu_hours_derive_from_the_measured_iteration_one_rate():
    assert tf.planned_gpu_hours_arm(1, tf.ROWS, 4) == tf.PLANNED_GPU_HOURS_ARM
    assert tf.planned_gpu_hours_arm(2, tf.ROWS, 5) == 4.1 and tf.planned_gpu_hours_arm(3, tf.ROWS, 5) == 4.1
    assert tf.planned_gpu_hours_arm(2, tf.ROWS, 4) == 3.3
    assert tf.MEASURED_GPU_S_PER_CONTACT_I1 == pytest.approx(2.49 * 3600 / 4320, abs=1e-3)


# ---------------------------------------------------------------------------------------------------------------------------
# archived duplicates, rereads, and the self-built ACE credit (loop iteration 2, 2026-10-12)
# ---------------------------------------------------------------------------------------------------------------------------


def typed_files(world: World, name: str, entries: list[dict]) -> tuple[Path, Path]:
    typed = world.tmp / f"typed-{name}.json"
    typed.write_text(json.dumps(entries), encoding="utf-8")
    pred = world.tmp / f"pred-{name}.json"
    pred.write_text(json.dumps({"schema": tp.PREDICTIONS_SCHEMA_ID, "predictions": {}}), encoding="utf-8")
    return typed, pred


def ipath(world: World, t: int, name: str) -> Path:
    return world.pkg / "iterations" / f"i{t}" / name


def jload(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


PAIRS = {"ace-vs-lock": contrast_doc(0.2, -0.7, 1.1), "aa-vs-lock": contrast_doc(0.1, -0.7, 0.9)}


def archived_oclock_world(world: World) -> tuple[Fakes, dict]:
    """Iteration 1 closed with one refused fx-oclock offline state; returns the fakes and that archived state."""

    fakes = Fakes(pairs=PAIRS)
    offline_world(world, delivery_entries("fx-oclock", ["time"], ["alarm_query"]), fakes)
    assert world.run("close", "--iter", "1", fakes=fakes)[0] == 0
    archived = next(s for s in world.archive().states() if s["arm"] == "typed" and s["iteration"] == 1)
    assert archived["verdict"] == "refused" and archived["credit"] is not None
    return fakes, archived


def chosen_parent(world: World) -> str:
    from speech_aware_evidence_acquisition.analysis.sealed_credit import parent_choice

    return parent_choice.choose_parent(world.archive().states(), "typed")["parent_id"]


def test_a_duplicate_of_an_archived_sibling_is_refused_at_open_reread_at_close_and_shown_to_the_proposer(world):
    fakes, archived = archived_oclock_world(world)
    raw = (world.pkg / "archive" / f"state-{archived['state_id']}.json").read_bytes()
    assert world.run(*propose_args(world, 2), fakes=fakes)[0] == 0
    entries2 = delivery_entries("fx-oclock", ["time"], ["alarm_query"], iteration=2)
    cid2 = entries2[0]["receipt"]["candidate_id"]
    assert cid2 != archived["candidate_id"]                      # the id carries the iteration; the artefact set does not
    typed, pred = typed_files(world, "i2", entries2)
    assert world.run(*open_cell_args(world, 2, typed=typed, predictions=pred))[0] == 0
    receipt = world.receipt(2, "open-cell")
    assert receipt["valid"] == 0 and receipt["offline"] == 0 and receipt["refused"] == 1
    assert receipt["duplicates_of_archived"] == [{"candidate_id": cid2, "archived_state_id": archived["state_id"], "archived_status": "refused"}]
    record = jload(ipath(world, 2, "candidates.json"))
    assert record["candidates"] == [] and record["offline"] == []
    assert record["refused"][0]["refusal_code"] == "duplicate-of-archived"
    assert record["refused"][0]["archived_state_id"] == archived["state_id"] and record["refused"][0]["archived_status"] == "refused"
    offline = jload(ipath(world, 2, "offline-candidates.json"))
    assert offline["candidates"] == [] and [e["candidate_id"] for e in offline["reread_candidates"]] == [cid2]
    # an idempotent re-run of the cell stage changes nothing
    assert world.run(*open_cell_args(world, 2, typed=typed, predictions=pred))[0] == 0
    assert jload(ipath(world, 2, "candidates.json")) == record
    # close: the fit is a reread record beside the archive, never a state; the archived state is untouched
    assert world.run("close", "--iter", "2", fakes=fakes)[0] == 0, world.out
    close = world.receipt(2, "close")
    assert "offline" not in close["verdicts"] and len(close["verdicts"]["rereads"]) == 1
    assert close["verdicts"]["rereads"][0]["state_id"] == archived["state_id"]
    reread = jload(world.pkg / "archive" / "rereads" / f"{archived['state_id']}-i2.json")
    assert reread["iteration"] == 2 and reread["candidate_id"] == cid2 and reread["column"]["run_id"] == tf.names(2, "arm")["run_id"]
    assert reread["credit"]["vs_lock"]["slu"]["point"] == 0.2
    assert (world.pkg / "archive" / f"state-{archived['state_id']}.json").read_bytes() == raw
    assert [s["iteration"] for s in world.archive().states() if s["arm"] == "typed"] == [0, 1]       # rereads are not states
    assert chosen_parent(world) == jload(ipath(world, 2, "parent.json"))["parent_state_id"]
    meta = jload(ipath(world, 2, "proposer-meta.json"))
    assert [r["n_rereads"] for r in meta["rows"] if r["iteration"] == 1] == [1]
    assert world.run("close", "--iter", "2", fakes=fakes)[0] == 0          # idempotent
    # the next proposer sees the duplicate as re-proposed and refused
    assert world.run(*propose_args(world, 3), fakes=Fakes())[0] == 0
    buffer = jload(world.analysis(3) / "proposer-context.json")["refused_buffer"]
    dup = [r for r in buffer if r["refusal_code"] == "duplicate-of-archived"]
    assert len(dup) == 1 and dup[0]["archived_state_id"] == archived["state_id"][:16] and dup[0]["archived_status"] == "refused"
    assert dup[0]["iteration"] == 2 and "realised_d_slu_pp" in dup[0]


def test_repair_reclassifies_an_already_opened_duplicate_and_lets_close_complete(world, monkeypatch):
    fakes, archived = archived_oclock_world(world)
    assert world.run(*propose_args(world, 2), fakes=fakes)[0] == 0
    dup = delivery_entries("fx-oclock", ["time"], ["alarm_query"], iteration=2)
    new = delivery_entries("ee10", ["person"], [], iteration=2)
    typed, pred = typed_files(world, "i2", dup + new)
    with monkeypatch.context() as m:                              # an iteration opened before the duplicate rule existed
        m.setattr(drv, "find_archived_duplicate", lambda *a, **k: None)
        assert world.run(*open_cell_args(world, 2, typed=typed, predictions=pred))[0] == 0
    assert world.receipt(2, "open-cell")["offline"] == 2
    old_receipt = ipath(world, 2, "open-cell-receipt.json").read_bytes()
    assert world.run("repair", "--iter", "2", "--duplicates-only", fakes=fakes)[0] == 0, world.out
    cid_dup, cid_new = dup[0]["receipt"]["candidate_id"], new[0]["receipt"]["candidate_id"]
    names = sorted(p.name for p in (world.pkg / "iterations" / "i2").iterdir())
    superseded = [n for n in names if ".superseded-" in n]
    assert len(superseded) == 3 and any(n.startswith("open-cell-receipt.superseded-") for n in superseded)
    assert next(ipath(world, 2, n) for n in superseded if n.startswith("open-cell-receipt.")).read_bytes() == old_receipt
    receipt = world.receipt(2, "open-cell")
    assert receipt["offline"] == 1 and receipt["duplicates_of_archived"][0]["candidate_id"] == cid_dup
    record = jload(ipath(world, 2, "candidates.json"))
    assert record["offline"] == [cid_new] and record["refused"][0]["refusal_code"] == "duplicate-of-archived"
    offline = jload(ipath(world, 2, "offline-candidates.json"))
    assert [e["candidate_id"] for e in offline["candidates"]] == [cid_new]
    assert [e["candidate_id"] for e in offline["reread_candidates"]] == [cid_dup]
    # the second candidate is NOT a duplicate (no archived state shares its artefact set)
    assert cid_new not in {d["candidate_id"] for d in receipt["duplicates_of_archived"]}
    # idempotent: nothing more is superseded or rewritten
    before = {p.name: p.read_bytes() for p in (world.pkg / "iterations" / "i2").iterdir()}
    assert world.run("repair", "--iter", "2", "--duplicates-only", fakes=fakes)[0] == 0
    assert {p.name: p.read_bytes() for p in (world.pkg / "iterations" / "i2").iterdir()} == before
    assert world.run("close", "--iter", "2", fakes=fakes)[0] == 0, world.out
    close = world.receipt(2, "close")
    new_state = next(s for s in world.archive().states() if s["arm"] == "typed" and s["iteration"] == 2)
    assert new_state["candidate_id"] == cid_new and [v["state_id"] for v in close["verdicts"]["offline"]] == [new_state["state_id"]]
    assert [v["state_id"] for v in close["verdicts"]["rereads"]] == [archived["state_id"]]
    assert (world.pkg / "archive" / "rereads" / f"{archived['state_id']}-i2.json").is_file()
    assert len([s for s in world.archive().states() if s["arm"] == "typed" and s["iteration"] == 2]) == 1


def test_repair_duplicates_only_refuses_a_closed_iteration(world):
    fakes, _archived = archived_oclock_world(world)
    code, text = world.run("repair", "--iter", "1", "--duplicates-only", fakes=fakes)
    assert code == 3 and "closed" in text


def test_a_fitted_artefact_set_that_collides_at_close_is_a_reread_not_a_crash(world):
    # iteration 1 refuses (under the point floor) an ee10 rule (its fitted table is part of the state id); iteration 2 proposes it again under the same parent:
    # the provisional id at open differs, the fitted one collides at close
    e1 = delivery_entries("ee10", ["person"], [])
    fakes = Fakes(pairs=PAIRS, fits={e1[0]["receipt"]["candidate_id"][:8]: fit_report(0.5, 0.1)})
    offline_world(world, e1, fakes)
    assert world.run("close", "--iter", "1", fakes=fakes)[0] == 0
    child = next(s for s in world.archive().states() if s["arm"] == "typed" and s["iteration"] == 1)
    assert child["verdict"] == "refused" and child["credit"] is not None
    raw = (world.pkg / "archive" / f"state-{child['state_id']}.json").read_bytes()
    e2 = delivery_entries("ee10", ["person"], [], iteration=2)
    cid2 = e2[0]["receipt"]["candidate_id"]
    fakes.fits[cid2[:8]] = fit_report(0.5, 0.1)
    assert world.run(*propose_args(world, 2), fakes=fakes)[0] == 0
    typed, pred = typed_files(world, "i2", e2)
    code, text = world.run(*open_cell_args(world, 2, typed=typed, predictions=pred))
    assert code == 0, text
    assert world.receipt(2, "open-cell")["offline"] == 1                  # not detectable before the fit
    assert world.run("close", "--iter", "2", fakes=fakes)[0] == 0, world.out
    close = world.receipt(2, "close")
    assert "offline" not in close["verdicts"] and close["verdicts"]["rereads"][0]["state_id"] == child["state_id"]
    assert (world.pkg / "archive" / f"state-{child['state_id']}.json").read_bytes() == raw
    assert not [s for s in world.archive().states() if s["arm"] == "typed" and s["iteration"] == 2]
    assert jload(world.pkg / "archive" / "rereads" / f"{child['state_id']}-i2.json")["archived_verdict"] == "refused"


def test_close_exports_the_row_scores_and_builds_the_ace_credit_itself(world):
    fakes = Fakes(pairs={"ace-vs-lock": contrast_doc(0.8, 0.1, 1.5), "aa-vs-lock": contrast_doc(0.1, -0.7, 0.9)})
    stall_iteration(world, fakes)
    assert world.run("close", "--iter", "1", fakes=fakes)[0] == 0
    assert fakes.calls.index("score-columns") < fakes.calls.index("row-scores")
    receipt = world.receipt(1, "close")
    rows_path = world.analysis(1) / "row-scores-i1.json"
    credit_path = world.analysis(1) / "ace-credit.json"
    assert receipt["ace_credit"] == "written" and receipt["row_scores"]["source"] == "exported"
    assert receipt["inputs"]["row_scores"] == tf.sha256_file(rows_path) and receipt["inputs"]["ace_credit"] == tf.sha256_file(credit_path)
    credit = jload(credit_path)
    assert credit["playbook_iteration"] == 1 and len(credit["rows"]) == 12
    assert world.run("close", "--iter", "1", fakes=fakes)[0] == 0                    # idempotent (export is write-once)
    assert fakes.calls.count("row-scores") == 1


def test_close_keeps_row_scores_as_an_override_and_refuses_a_missing_file(world):
    fakes = Fakes(pairs={"ace-vs-lock": contrast_doc(0.8, 0.1, 1.5), "aa-vs-lock": contrast_doc(0.1, -0.7, 0.9)})
    stall_iteration(world, fakes)
    code, text = world.run("close", "--iter", "1", "--row-scores", str(world.tmp / "nope.json"), fakes=fakes)
    assert code == 3 and "does not exist" in text
    assert lib.read_receipt(world.pkg / "iterations" / "i1", "close") is None and "row-scores" not in fakes.calls
    import tfrl_row_scores as rs

    rows = [f"slurp:train:{i:06d}:a" for i in range(5)]
    export = world.tmp / "own.json"
    export.write_text(json.dumps(rs.build_row_scores({r: 0.5 for r in rows}, {r: 0.6 for r in rows},
                                                     {r: {"scenario": "calendar", "slot_types": ["date"]} for r in rows})), encoding="utf-8")
    assert world.run("close", "--iter", "1", "--row-scores", str(export), fakes=fakes)[0] == 0
    assert "row-scores" not in fakes.calls and world.receipt(1, "close")["row_scores"]["source"] == "override"
    assert len(jload(world.analysis(1) / "ace-credit.json")["rows"]) == 5


def test_a_planned_close_names_the_row_score_export(world):
    fakes = Fakes()
    stall_iteration(world, fakes)
    code, text = world.run("close", "--iter", "1")
    assert code == 0 and "tfrl_row_scores.py" in text


# ---------------------------------------------------------------------------------------------------------------------------
# owner ruling 300 A: the offered class set is checked at validation (the i2 / i3 shape: carriers offered one class proposed another)
# ---------------------------------------------------------------------------------------------------------------------------


def _delivery_candidate() -> dict:
    return {"schema": tp.CANDIDATE_SCHEMA_ID, "iteration": 1, "parent_state_id": drv.ROOT_DISPLAY, "operator_class": "delivery",
            "operator": "deliver-rule", "hypothesis_code": "rule-filter",
            "target": {"failure_class": "SPURIOUS", "slot_types": ["person"], "scenarios": ["social"], "value_in_supply": "none"},
            "applications": [{"family": "ee10", "guard": "wilson", "types": ["person"], "intents": []}]}


def test_a_candidate_outside_its_carriers_offered_class_set_is_refused_with_the_named_finding(world):
    delivery = tp.read_typed_candidate_receipt(json.dumps(_delivery_candidate()))
    knob = knob_receipt(12)[0]
    # the i2 / i3 shape: the delivery candidate came from a carrier that was offered only construction; the knob from the supply carrier
    entries = [{"allowed_classes": ["construction"], "receipt": delivery}, knob]
    typed = world.tmp / "typed.json"
    typed.write_text(json.dumps(entries), encoding="utf-8")
    pred = predictions(world.tmp / "pred.json", [knob], 1.8)
    world.run(*propose_args(world), fakes=Fakes())
    assert world.run(*open_cell_args(world, typed=typed, predictions=pred))[0] == 0
    record = json.loads((world.pkg / "iterations" / "i1" / "candidates.json").read_text(encoding="utf-8"))
    assert [r["refusal_code"] for r in record["refused"]] == ["class-not-allowed"] == [lib.FINDING_CLASS_NOT_OFFERED]
    assert record["refused"][0]["offered_classes"] == ["construction"] and record["offline"] == []
    assert record["offered_class_check"]["class_not_offered"] == 1 and record["offered_class_check"]["applied"] is True
    assert record["flown"] == knob["receipt"]["candidate_id"]


def test_the_class_finding_reaches_the_iteration_close_summary(world):
    delivery = tp.read_typed_candidate_receipt(json.dumps(_delivery_candidate()))
    entries = [{"allowed_classes": ["construction"], "receipt": delivery}]
    typed = world.tmp / "typed.json"
    typed.write_text(json.dumps(entries), encoding="utf-8")
    pred = world.tmp / "pred.json"
    pred.write_text(json.dumps({"schema": tp.PREDICTIONS_SCHEMA_ID, "predictions": {}}), encoding="utf-8")
    fakes = Fakes(pairs={"ace-vs-lock": contrast_doc(0.2, -0.7, 1.1), "aa-vs-lock": contrast_doc(0.1, -0.7, 0.9)})
    assert world.run(*propose_args(world), fakes=fakes)[0] == 0
    assert world.run(*open_cell_args(world, typed=typed, predictions=pred))[0] == 0
    code, text = world.run("close", "--iter", "1", fakes=fakes)
    assert code == 0, text
    check = world.receipt(1, "close")["typed_class_check"]
    assert check["class_not_offered"] == 1 and check["applied"] is True


def test_an_offered_duplicate_is_not_shadowed_by_a_refused_copy_from_a_carrier_not_offered_the_class(world):
    delivery = tp.read_typed_candidate_receipt(json.dumps(_delivery_candidate()))
    entries = [{"allowed_classes": ["supply"], "receipt": delivery}, {"allowed_classes": ["delivery", "scope"], "receipt": delivery}]
    typed = world.tmp / "typed.json"
    typed.write_text(json.dumps(entries), encoding="utf-8")
    pred = world.tmp / "pred.json"
    pred.write_text(json.dumps({"schema": tp.PREDICTIONS_SCHEMA_ID, "predictions": {}}), encoding="utf-8")
    world.run(*propose_args(world), fakes=Fakes())
    assert world.run(*open_cell_args(world, typed=typed, predictions=pred))[0] == 0
    record = json.loads((world.pkg / "iterations" / "i1" / "candidates.json").read_text(encoding="utf-8"))
    assert record["offline"] == [delivery["candidate_id"]] and record["offered_class_check"]["class_not_offered"] == 1


def test_receipts_sealed_before_the_fix_still_open_and_the_check_is_labelled_not_applied(world):
    legacy = [{"receipt": tp.read_typed_candidate_receipt(json.dumps(_delivery_candidate())), "sample_id_sha_prefix": "0" * 12}]
    assert lib.typed_entry_layout(legacy[0]) == lib.TYPED_ENTRY_LAYOUT_V1
    typed = world.tmp / "typed.json"
    typed.write_text(json.dumps(legacy), encoding="utf-8")
    pred = world.tmp / "pred.json"
    pred.write_text(json.dumps({"schema": tp.PREDICTIONS_SCHEMA_ID, "predictions": {}}), encoding="utf-8")
    world.run(*propose_args(world), fakes=Fakes())
    assert world.run(*open_cell_args(world, typed=typed, predictions=pred))[0] == 0
    check = json.loads((world.pkg / "iterations" / "i1" / "candidates.json").read_text(encoding="utf-8"))["offered_class_check"]
    assert check["applied"] is False and check["entry_layouts"] == [lib.TYPED_ENTRY_LAYOUT_V1] and check["class_not_offered"] == 0
