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
    # the real exposure ledger is untouched; the overlay's copy carries no TFRL row
    assert "tfrl-loop" not in (world.root / "docs" / "exposure-ledger.md").read_text(encoding="utf-8").lower()
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
    # the loader's verdict on the ace column is the named interface gap, not an unexplained failure
    assert "ace-playbook" in json.dumps(receipt["loader_verification"])
    assert {b["id"] for b in receipt["blockers"]} >= {"ace-playbook-store-not-in-lock-layer"}
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
