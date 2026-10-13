"""Pure and near-pure building blocks of the autonomous typed loop driver (decision 263-A, design section 7).

Everything here is MODEL-FREE and imports no GPU, server, tokenizer-service, encoder or network code. The pieces:

* guards (:func:`refuse_if_busy`), the write-once receipt discipline (:func:`write_receipt`), the protocol pin
  (:func:`check_protocol`) and the external-script :class:`Runner` (plan-only unless ``--execute``);
* ADAPTERS written here because the merged modules do not meet at their edges (interface gaps, reported in the final note):
  :func:`adapt_tables_for_proposer` (E-T3 ``tables-v1.json`` -> E-T1's ``saea-tfrl-contrast-tables-v1`` document),
  :func:`build_reflector_material` (E-T3 tables -> E-T2's ``saea-ace-reflector-material-v1``), :func:`build_proposer_context`
  (E-T4 archive -> E-T1's context artefact), :func:`credit_from_contrasts` / :func:`ace_credit_from_row_scores` (paired-read bytes
  -> E-T4 credit vectors / E-T2 ``saea-ace-credit-v1``), :func:`offline_credit_from_fit_report` (E-T3 delivery-fit report -> credit);
* archive helpers (:func:`ensure_root_states`, :func:`put_state_idempotent`).

Text discipline: nothing here prints or persists an utterance, transcript, gold label or model output. The ACE playbook items are
model-written by design (the baseline) and are persisted only through E-T2's ``write_playbook`` under the data root's analysis
directory, never in the repository and never printed.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import tfrl_family as tf  # noqa: E402

REPO_ROOT = tf.REPO_ROOT
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

RECEIPT_SCHEMA = "saea-tfrl-loop-receipt-v1"
STATE_FILE = "loop-state.json"
#: Processes whose presence means a batch driver, a flight or a flip loop is running (the chain wrappers' own pgrep patterns,
#: scripts/flights/batch/batch_chain_*.sh, plus the flip loop's).
BUSY_PATTERN = re.compile(
    r"core\.flight\.cli|batch_driver\.sh|repin_loop_generic\.sh|repin_cell_generic\.sh|scripts/flights/repin_cell\.py|"
    r"refresh_registered_plan_pins\.py|_flip\.sh|batch_chain_"
)


class LoopError(RuntimeError):
    pass


class GuardRefusal(LoopError):
    pass


class ProtocolDrift(LoopError):
    pass


class ReceiptConflict(LoopError):
    pass


class MissingInput(LoopError):
    pass


# ---------------------------------------------------------------------------------------------------------------------------
# guards, receipts, protocol, runner
# ---------------------------------------------------------------------------------------------------------------------------


def list_processes() -> list[str] | None:
    """Command lines of every running process (``/proc``), or ``None`` where that cannot be read (non-Linux)."""

    proc = Path("/proc")
    if not proc.is_dir():
        return None
    me = {os.getpid(), os.getppid()}
    out: list[str] = []
    for entry in proc.iterdir():
        if not entry.name.isdigit() or int(entry.name) in me:
            continue
        try:
            raw = (entry / "cmdline").read_bytes()
        except OSError:
            continue
        text = raw.replace(b"\0", b" ").decode("utf-8", "replace").strip()
        if text:
            out.append(text)
    return out


def refuse_if_busy(lister: Callable[[], "list[str] | None"] | None = None, *, skip: bool = False) -> None:
    """Refuse while a batch driver, a flight (core.flight.cli) or a flip loop runs; refuse when that cannot be verified."""

    if skip:
        return
    processes = (lister or list_processes)()
    if processes is None:
        raise GuardRefusal("cannot list processes on this host: run the driver in WSL (or pass --skip-process-guard)")
    busy = [p for p in processes if BUSY_PATTERN.search(p) and "tfrl_loop_driver" not in p and "pytest" not in p]
    if busy:
        raise GuardRefusal(f"a batch driver / flight / flip loop is running ({len(busy)} process(es)); refusing")


def _json_text(document: object) -> str:
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def write_json_new(path: Path, document: object) -> str:
    """Write a JSON file; an identical existing file is left alone, a different one is a conflict. Returns its sha256."""

    path = Path(path)
    text = _json_text(document)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise ReceiptConflict(f"{path} already exists with different content (write-once)")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    return tf.sha256_bytes(text.encode("utf-8"))


def write_receipt(directory: Path, step: str, payload: Mapping[str, Any], *, inputs: Mapping[str, Any]) -> tuple[Path, bool]:
    """Write ``<directory>/<step>-receipt.json``. Same inputs -> no-op (returns ``created=False``); other inputs -> conflict."""

    directory = Path(directory)
    path = directory / f"{step}-receipt.json"
    body = {"schema": RECEIPT_SCHEMA, "step": step, "inputs_sha256": tf.canonical_sha256(inputs), "inputs": dict(inputs),
            **{k: v for k, v in payload.items() if k not in ("schema", "step", "inputs_sha256", "inputs")}}
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get("inputs_sha256") != body["inputs_sha256"]:
            raise ReceiptConflict(f"{path.name}: a receipt with different inputs exists; the loop never overwrites a receipt")
        return path, False
    directory.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_text(body), encoding="utf-8", newline="\n")
    return path, True


def read_receipt(directory: Path, step: str) -> dict | None:
    path = Path(directory) / f"{step}-receipt.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def build_protocol() -> dict:
    import build_tfrl_loop_protocol as bp  # noqa: PLC0415

    return bp.build()


def check_protocol(package_dir: Path, *, pin: bool) -> dict:
    """Load the committed protocol, require that it equals the implemented constants, and (re)check the pinned hash."""

    path = Path(package_dir) / "tfrl-loop-protocol-v1.json"
    if not path.is_file():
        raise MissingInput(f"no protocol at {path}")
    document = json.loads(path.read_text(encoding="utf-8"))
    body = {k: v for k, v in document.items() if k != "protocol_sha256"}
    if tf.canonical_sha256(body) != document.get("protocol_sha256"):
        raise ProtocolDrift("protocol_sha256 does not match the file content")
    built = build_protocol()
    if built["protocol_sha256"] != document["protocol_sha256"]:
        raise ProtocolDrift("the committed protocol differs from the implemented constants (rebuild: build_tfrl_loop_protocol.py)")
    state_path = Path(package_dir) / STATE_FILE
    if state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("protocol_sha256") != document["protocol_sha256"]:
            raise ProtocolDrift("the protocol hash changed since the loop was opened; the driver refuses to run")
    elif pin:
        state_path.write_text(_json_text({"schema": "saea-tfrl-loop-state-v1", "protocol_sha256": document["protocol_sha256"]}),
                              encoding="utf-8", newline="\n")
    return document


@dataclass
class StepResult:
    name: str
    status: str            # present | planned | ran
    argv: list[str]
    produces: list[str]


class Runner:
    """Runs the external, model-free analysis scripts. Plan-only unless ``execute``; skips a step whose outputs exist."""

    def __init__(self, *, execute: bool, cwd: Path | None = None, python: str | None = None,
                 fake: "Callable[[str, list[str], list[Path]], None] | None" = None):
        self.execute, self.cwd, self.python, self.fake = execute, Path(cwd or REPO_ROOT), python or sys.executable, fake
        self.log: list[StepResult] = []

    def run(self, name: str, argv: Sequence[str], *, produces: Sequence[Path], ok_codes: Sequence[int] = (0,)) -> StepResult:
        argv = [str(a) for a in argv]
        produced = [Path(p) for p in produces]
        if produced and all(p.exists() for p in produced):
            result = StepResult(name, "present", argv, [str(p) for p in produced])
        elif self.fake is not None:
            self.fake(name, argv, produced)
            result = StepResult(name, "ran", argv, [str(p) for p in produced])
            missing = [str(p) for p in produced if not p.exists()]
            if missing:
                raise LoopError(f"step {name}: the stand-in produced no {missing}")
        elif not self.execute:
            result = StepResult(name, "planned", argv, [str(p) for p in produced])
        else:
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
            completed = subprocess.run([self.python, "-B", *argv], cwd=str(self.cwd), env=env, check=False)  # noqa: S603
            if completed.returncode not in ok_codes:
                raise LoopError(f"step {name} failed with exit status {completed.returncode}")
            missing = [str(p) for p in produced if not p.exists()]
            if missing:
                raise LoopError(f"step {name} finished but did not produce {missing}")
            result = StepResult(name, "ran", argv, [str(p) for p in produced])
        self.log.append(result)
        return result

    @property
    def planned(self) -> list[StepResult]:
        return [r for r in self.log if r.status == "planned"]


# ---------------------------------------------------------------------------------------------------------------------------
# adapters: E-T3 tables -> E-T1 proposer artefact
# ---------------------------------------------------------------------------------------------------------------------------

_STATE_TO_SUPPLY = {"in_supply": "any", "in_store_not_delivered": "none", "in_train_not_in_store": "none", "nowhere": "none"}
_CLASS_MAP = {"SPURIOUS": "SPURIOUS", "MISSING": "MISSING", "WRONG-TYPE": "WRONG-TYPE", "BOUNDARY": "BOUNDARY", "NEAR": "NEAR",
              "WRONG-VALUE": "WRONG-VALUE", "FORMAT": "FORMAT"}
SHORT_STATE_ID = 16


def _num(value: Any) -> "float | None":
    """A count or rate as a number; the suppression marker and null become ``None``."""

    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _count(value: Any) -> "int | str":
    """A count cell as the proposer's artefact carries it: an int, or the suppression marker."""

    if isinstance(value, str):
        return "<3"
    return int(value)


def failure_cube_rows(tables_v1: Mapping[str, Any]) -> list[list[Any]]:
    """E-T1 ``failure_cube`` rows from E-T3 table (a) and (b).

    Table (a) splits each (class, slot type, scenario) cell into four supply states; E-T1's ``value_in_supply`` enum cannot tell
    E1 from E2 from E3, so ``in_supply`` becomes ``any`` and the three not-supplied states are summed into ``none``. ``mass_pp``
    is the cell's share of the column's rows in percent (rate-free; the exchange-rate table carries the SLU conversion).
    Suppressed counts stay ``<3`` and carry a null mass. Table (b)'s false-fill rows become ``EMPTY-GOLD-FILL`` cells."""

    rows_total = int(tables_v1["source"]["rows"])
    table_a = tables_v1["table_a"]
    columns = table_a["columns"]
    index = {name: columns.index(name) for name in columns}
    out: list[list[Any]] = []
    for row in table_a["rows"]:
        klass, slot, scen = row[index["class"]], row[index["slot_type"]], row[index["scenario"]]
        if klass not in _CLASS_MAP:
            continue
        supplied = row[index["in_supply"]]
        others = [row[index[s]] for s in ("in_store_not_delivered", "in_train_not_in_store", "nowhere")]
        for supply, cells in (("any", [supplied]), ("none", others)):
            if any(isinstance(c, str) for c in cells):
                n: "int | str" = "<3"
                mass = None
            else:
                n = int(sum(cells))
                mass = round(100.0 * n / rows_total, 4)
            if n == 0:
                continue
            out.append([klass, slot, supply, scen, n, mass])
    for scen, block in sorted(tables_v1["table_b"]["per_scenario"].items()):
        fills = block["false_fill_rows"]
        if isinstance(fills, str):
            out.append(["EMPTY-GOLD-FILL", "any", "none", scen, "<3", None])
        elif fills:
            out.append(["EMPTY-GOLD-FILL", "any", "none", scen, int(fills), round(100.0 * fills / rows_total, 4)])
    return out


def scenario_summary_rows(tables_v1: Mapping[str, Any]) -> list[list[Any]]:
    rows = []
    for scen in sorted(tables_v1["scenario_rows"]):
        n = tables_v1["scenario_rows"][scen]
        c = tables_v1["table_c"]["per_scenario"].get(scen, {})
        b = tables_v1["table_b"]["per_scenario"].get(scen, {})
        n_val, wrong, empty = _num(n), _num(c.get("intent_wrong_rows")), _num(b.get("empty_gold_rows"))
        intent_acc = None if n_val in (None, 0.0) or wrong is None else round(100.0 * (1.0 - wrong / n_val), 4)
        empty_share = None if n_val in (None, 0.0) or empty is None else round(empty / n_val, 4)
        rows.append([scen, _count(n), None, intent_acc, empty_share])
    return rows


def exchange_rate_rows(tables_v1: Mapping[str, Any]) -> list[list[Any]]:
    rows: list[list[Any]] = []
    tags = {"comp1b_fold_a": "c1b", "a2": "a2"}
    for pool, block in sorted(tables_v1["table_e"]["pools"].items()):
        tag = tags.get(pool, pool[:6])
        for key, value in sorted(block["empirical_rates_pp"].items()):
            mean = value.get("mean_pp")
            rows.append([f"{tag}.emp.{key.replace('one_extra_exact_row.', 'xr.')}"[:48], None if mean is None else float(mean)])
    return rows


def state_credit_rows(states: Iterable[Mapping[str, Any]], operators: Mapping[str, str] | None = None) -> list[list[Any]]:
    """E-T1 ``state_credit`` rows from the archive (refused siblings included). The root is ``s0-lock-v2.2``."""

    operators = operators or {}
    rows: list[list[Any]] = [["s0-lock-v2.2", "none", "none", "accepted", 0.0, 0.0, 0.0, 0.0]]
    for s in states:
        if s["arm"] != "typed" or s["iteration"] < 1 or s["verdict"] == "unflown" or s.get("credit") is None:
            continue
        vs = s["credit"]["vs_lock"]
        rows.append([s["state_id"][:SHORT_STATE_ID], s["operator_class"], operators.get(s["candidate_id"] or "", "unknown"),
                     s["verdict"], vs["slu"]["point"], vs["slu"]["lo"], vs["slu"]["hi"], vs["intent"]["point"]])
    return rows


def adapt_tables_for_proposer(
    tables_v1: Mapping[str, Any], *, iteration: int, enums: Mapping[str, Sequence[str]],
    states: Iterable[Mapping[str, Any]] = (), operators: Mapping[str, str] | None = None,
    pool_after_selector: Sequence[Sequence[Any]] | None = None,
) -> dict:
    """E-T3's ``tables-v1.json`` -> E-T1's ``saea-tfrl-contrast-tables-v1`` document (sealed with its canonical hash)."""

    from speech_aware_evidence_acquisition.rails import tfrl_typed_proposer as tp  # noqa: PLC0415

    tables: dict[str, Any] = {
        "failure_cube": {"columns": ["failure_class", "slot_type", "value_in_supply", "scenario", "n_rows", "mass_pp"],
                         "rows": failure_cube_rows(tables_v1)},
        "scenario_summary": {"columns": ["scenario", "n_rows", "slu", "intent_acc", "empty_share"],
                             "rows": scenario_summary_rows(tables_v1)},
        "state_credit": {"columns": ["state_id", "operator_class", "operator", "status", "d_slu_pp", "d_slu_lo_pp", "d_slu_hi_pp",
                                     "d_intent_pp"], "rows": state_credit_rows(states, operators)},
        "exchange_rates": {"columns": ["name", "pp"], "rows": exchange_rate_rows(tables_v1)},
    }
    if pool_after_selector:
        tables["pool_after_selector"] = {"columns": ["scenario", "selector", "theta", "pool_size"],
                                         "rows": [list(r) for r in pool_after_selector]}
    document = {
        "schema": tp.TABLES_SCHEMA_ID, "iteration": iteration,
        "enums": {"slot_types": list(enums["slot_types"]), "intents": list(enums["intents"]),
                  "scenarios": list(enums.get("scenarios") or tp.SCENARIOS)},
        "tables": tables,
    }
    document["tables_sha256"] = tp.canonical_tables_sha256(document)
    tp.parse_tables(document)     # fail closed: the proposer's own reader accepts it
    return document


def build_proposer_context(
    *, iteration: int, parent_state_id: str, archive_sha256: str, refused_buffer: Sequence[Mapping[str, Any]],
    states: Iterable[Mapping[str, Any]],
) -> dict:
    """E-T1's context artefact; the meta summary is keyed by operator class (counts and one mean only)."""

    from speech_aware_evidence_acquisition.rails import tfrl_typed_proposer as tp  # noqa: PLC0415

    by_class: dict[str, dict[str, Any]] = {}
    for s in states:
        if s["arm"] != "typed" or s["iteration"] < 1:
            continue
        c = by_class.setdefault(s["operator_class"], {"proposed": 0, "valid": 0, "flown": 0, "accepted": 0, "refused": 0, "_d": []})
        c["proposed"] += 1
        c["valid"] += 1
        if s["verdict"] in ("accepted", "refused"):
            c["flown"] += 1
            c[s["verdict"]] += 1
            if s.get("predicted_slu_pp") is not None and s.get("credit") is not None:
                block = s["credit"].get("vs_parent") or s["credit"]["vs_lock"]
                c["_d"].append(block["slu"]["point"] - float(s["predicted_slu_pp"]))
    meta = {}
    for name, c in by_class.items():
        d = c.pop("_d")
        c["mean_realised_minus_predicted_pp"] = (sum(d) / len(d)) if d else None
        meta[name] = c
    document = {"schema": tp.CONTEXT_SCHEMA_ID, "iteration": iteration, "parent_state_id": parent_state_id[:48],
                "archive_sha256": archive_sha256, "refused_buffer": [dict(r) for r in refused_buffer], "meta_summary": meta}
    tp.parse_context(document)
    return document


# ---------------------------------------------------------------------------------------------------------------------------
# adapters: E-T3 tables -> E-T2 reflector material
# ---------------------------------------------------------------------------------------------------------------------------


def build_reflector_material(
    tables_v1: Mapping[str, Any], *, scenario: str, iteration: int, column_arm: str, run_id: str, credit_receipt_sha256: str,
    playbook: Mapping[str, Any], item_credit: Mapping[str, Mapping[str, int]] | None = None,
) -> dict:
    """One sealed ``saea-ace-reflector-material-v1`` document for ONE scenario from the E-T3 tables.

    The credit tables are the scenario's slice of tables (a), (b) and (c); the item counters are the playbook's own cumulative
    counters (by script) overlaid with the table-(g) item credit when given. Aggregates and labels only."""

    from speech_aware_evidence_acquisition.rails import tfrl_ace_material as ace  # noqa: PLC0415

    cols_a = tables_v1["table_a"]["columns"]
    ia = {name: cols_a.index(name) for name in cols_a}
    rows_a = [
        [r[ia["class"]], r[ia["slot_type"]], r[ia["in_supply"]], r[ia["in_store_not_delivered"]],
         r[ia["in_train_not_in_store"]], r[ia["nowhere"]], r[ia["total"]]]
        for r in tables_v1["table_a"]["rows"] if r[ia["scenario"]] == scenario
    ][:60]
    b = tables_v1["table_b"]["per_scenario"].get(scenario, {})
    c = tables_v1["table_c"]["per_scenario"].get(scenario, {})
    hist = c.get("wrong_rank_histogram", {})
    credit_tables = [
        {"table_id": "failure-by-slot", "title": "Entity failures by class and slot type",
         "columns": ["class", "slot_type", "in_supply", "in_store_unused", "in_train_unused", "nowhere", "total"], "rows": rows_a},
        {"table_id": "empty-answer", "title": "Rows whose reference has no entities",
         "columns": ["empty_rows", "false_fill_rows", "false_fill_pct", "spurious_entities"],
         "rows": [[b.get("empty_gold_rows", 0), b.get("false_fill_rows", 0), b.get("false_fill_rate_pct"),
                   b.get("spurious_entities", 0)]]},
        {"table_id": "intent-errors", "title": "Intent errors and the rank of the right intent",
         "columns": ["rows", "intent_wrong", "on_shortlist_pct", "rank_1", "rank_2", "rank_3", "rank_4_5", "rank_6_10", "rank_11_plus"],
         "rows": [[c.get("rows", 0), c.get("intent_wrong_rows", 0), c.get("gold_on_shortlist_rate_pct"), hist.get("1", 0),
                   hist.get("2", 0), hist.get("3", 0), hist.get("4-5", 0), hist.get("6-10", 0), hist.get("11+", 0)]]},
    ]
    counters = []
    for item in playbook["items"]:
        step = (item_credit or {}).get(item["item_id"])
        counters.append({"item_id": item["item_id"], "helpful": int(step["helpful"]) if step else int(item["helpful"]),
                         "harmful": int(step["harmful"]) if step else int(item["harmful"]),
                         "scoped_rows": int(step["scoped_rows"]) if step else int(item["scoped_rows"])})
    n_rows = _num(tables_v1["scenario_rows"].get(scenario)) or 0
    material = {
        "schema": ace.MATERIAL_SCHEMA, "iteration": iteration, "scenario": scenario,
        "source": {"column_arm": column_arm, "run_id": run_id, "credit_receipt_sha256": credit_receipt_sha256},
        "n_rows": int(n_rows), "credit_tables": credit_tables, "item_counters": counters,
    }
    sealed = ace.seal_material(material)
    ace.validate_material(sealed)
    return sealed


# ---------------------------------------------------------------------------------------------------------------------------
# credit vectors
# ---------------------------------------------------------------------------------------------------------------------------


def _ci_block(entry: Mapping[str, Any], where: str) -> dict[str, float]:
    boot = entry.get("cluster_bootstrap") if isinstance(entry.get("cluster_bootstrap"), Mapping) else entry
    interval = boot.get("ci95_pp")
    if not (isinstance(interval, (list, tuple)) and len(interval) == 2):
        raise LoopError(f"{where}: no ci95_pp interval in the paired-read block")
    point = entry.get("delta_pp", boot.get("point_estimate_pp"))
    if point is None:
        raise LoopError(f"{where}: no delta_pp in the paired-read block")
    lo, hi, pt = float(interval[0]), float(interval[1]), float(point)
    return {"point": pt, "lo": min(lo, pt), "hi": max(hi, pt)}


def credit_from_contrasts(
    contrasts: Mapping[str, Any], *, own_slu_f1: float, own_intent: float, contacts_per_row: float,
    per_scenario_tables: Mapping[str, Any] | None = None, node_local: Mapping[str, Any] | None = None, arm: str = "",
    versus_twin: Mapping[str, Any] | None = None, versus_parent: Mapping[str, Any] | None = None,
) -> dict:
    """An E-T4 credit vector from ``score-contrasts.json`` bytes (point and CI95 in percentage points).

    ``contrasts`` is the arm-vs-lock paired read; ``versus_twin`` / ``versus_parent`` are the same reads against the aa and par
    columns (``None`` when no such column flew). ``node_local`` is the node-local reader's report (empty-gold false fill and
    non-empty exact, paired against the delivering arm); a missing block records ``n = 0`` and a zero delta."""

    def block(doc: Mapping[str, Any] | None, where: str) -> "dict | None":
        if doc is None:
            return None
        slu = doc["pooled_micro"]["slu_f1_micro"]
        intent = doc["per_row"]["scenario_action_exact"]
        return {"slu": _ci_block(slu, f"{where}.slu"), "intent": _ci_block(intent, f"{where}.intent")}

    per_scenario: dict[str, Any] = {}
    if per_scenario_tables:
        table = per_scenario_tables.get("per_scenario") if isinstance(per_scenario_tables, Mapping) else None
        if isinstance(table, Mapping):
            for scen, row in table.items():
                try:
                    per_scenario[str(scen)] = {"slu": float(row["slu_f1"]["delta_pp"]), "intent": float(row["intent"]["delta_pp"])}
                except (KeyError, TypeError):
                    continue
    fill = {"n": 0, "delta_pp": 0.0}
    exact = {"n": 0, "delta_pp": 0.0}
    if node_local:
        paired = (((node_local.get("arms") or {}).get(arm) or {}).get("paired_vs_delivering")) or {}
        for target, key in ((fill, "empty_gold_false_fill"), (exact, "nonempty_exact")):
            entry = paired.get(key)
            if isinstance(entry, Mapping) and entry.get("diff_pp") is not None:
                target.update(n=int(entry.get("n", 0)), delta_pp=float(entry["diff_pp"]))
    vs_lock = block(contrasts, "vs_lock")
    assert vs_lock is not None
    return {"slu_f1": float(own_slu_f1), "intent": float(own_intent), "vs_lock": vs_lock,
            "vs_twin": block(versus_twin, "vs_twin"), "vs_parent": block(versus_parent, "vs_parent"),
            "per_scenario": per_scenario, "false_fill": fill, "non_empty_exact": exact, "contacts_per_row": float(contacts_per_row)}


def offline_credit_from_fit_report(report: Mapping[str, Any]) -> dict:
    """An E-T4 credit vector for an OFFLINE delivery / scope state from a ``saea-tfrl-delivery-fit-v1`` report. Labels never
    change in the delivery grammar, so the intent delta is exactly zero."""

    cross = report["cross_fitted"]
    lo, hi = (float(x) for x in cross["ci95_slu_pp"])
    point = float(cross["delta_slu_pp"])
    block = {"slu": {"point": point, "lo": min(lo, point), "hi": max(hi, point)}, "intent": {"point": 0.0, "lo": 0.0, "hi": 0.0}}
    per = {str(s): {"slu": float(v.get("delta_slu_pp", 0.0) if isinstance(v, Mapping) else 0.0), "intent": 0.0}
           for s, v in (cross.get("per_scenario") or {}).items() if isinstance(v, Mapping)}
    return {"slu_f1": float(cross["right_slu_f1_pp"]), "intent": 0.0, "vs_lock": block, "vs_twin": None, "vs_parent": None,
            "per_scenario": per, "false_fill": {"n": 0, "delta_pp": 0.0}, "non_empty_exact": {"n": 0, "delta_pp": 0.0},
            "contacts_per_row": 0.0}


def offline_verdict(report: Mapping[str, Any]) -> tuple[str, dict]:
    """Design 5.3: an offline candidate is accepted on a cross-fitted CI95 lower bound above 0 AND a point of at least 0.67 pp."""

    cross = report["cross_fitted"]
    lb_ok = (not report.get("refused")) and float(cross["ci95_slu_pp"][0]) > 0.0
    point_ok = float(cross["delta_slu_pp"]) >= tf.OFFLINE_FLOOR_PP
    clauses = {"ci_lb_gt_0": {"pass": bool(lb_ok), "value": float(cross["ci95_slu_pp"][0]), "threshold": 0.0},
               "point_ge_floor": {"pass": bool(point_ok), "value": float(cross["delta_slu_pp"]), "threshold": tf.OFFLINE_FLOOR_PP}}
    return ("accepted" if lb_ok and point_ok else "refused"), clauses


def ace_credit_from_row_scores(row_scores: Mapping[str, Any], *, playbook_iteration: int) -> dict:
    """``saea-ace-credit-v1`` from a ``saea-tfrl-row-scores-v1`` export (per-row official SLU-F1 of the lock and ace columns).

    Rows are keyed by an opaque digest of the sample id; the sample id itself never enters the credit (E-T2 contract)."""

    from speech_aware_evidence_acquisition.rails import tfrl_ace_material as ace  # noqa: PLC0415

    if row_scores.get("schema") != "saea-tfrl-row-scores-v1":
        raise LoopError("not a saea-tfrl-row-scores-v1 export")
    lock, ace_scores, rows_meta = row_scores["arms"]["lock"], row_scores["arms"]["ace"], row_scores["rows"]
    if sorted(lock) != sorted(ace_scores) or sorted(lock) != sorted(rows_meta):
        raise LoopError("the lock and ace columns and the row annotations do not cover the same rows")
    import hashlib  # noqa: PLC0415

    rows = []
    for sid in sorted(lock):
        meta = rows_meta[sid]
        rows.append({"row_digest": hashlib.sha256(f"tfrl-row:{sid}".encode("utf-8")).hexdigest(),
                     "scenarios": sorted(set(meta["scenarios"])), "slot_types": sorted(set(meta["slot_types"])),
                     "lock": float(lock[sid]), "ace": float(ace_scores[sid])})
    credit = {"schema": ace.CREDIT_SCHEMA, "playbook_iteration": int(playbook_iteration), "rows": rows}
    ace.validate_credit(credit)
    return credit


def item_credit_from_tables(tables_v1: Mapping[str, Any]) -> dict[str, dict[str, int]]:
    """Table (g) -> ``{item_id: {helpful, harmful, scoped_rows}}`` (suppressed cells count as 0: aggregates under three rows)."""

    out: dict[str, dict[str, int]] = {}
    for item in (tables_v1.get("table_g") or {}).get("items", []):
        def n(v: Any) -> int:
            return 0 if isinstance(v, str) else int(v)
        out[str(item["item_id"])] = {"helpful": n(item["helpful"]), "harmful": n(item["harmful"]), "scoped_rows": n(item["rendered_rows"])}
    return out


# ---------------------------------------------------------------------------------------------------------------------------
# archive helpers
# ---------------------------------------------------------------------------------------------------------------------------


def put_state_idempotent(archive: Any, state: Mapping[str, Any]) -> bool:
    """Write a state once; an identical state already on disk is accepted (a re-run), a different one is refused."""

    from speech_aware_evidence_acquisition.analysis.sealed_credit.archive import ArchiveError  # noqa: PLC0415

    wanted = json.loads(json.dumps(state))
    # a state whose recorded hash was corrected by a correction record keeps its original state_id: the same artefact set under the
    # corrected view is the same state (a re-run of the step must not archive a duplicate)
    for held in archive.states():
        if held.get("corrections") and held["state_id"] != wanted["state_id"] and held["artefact_hashes"] == wanted["artefact_hashes"]:
            view = {k: v for k, v in held.items() if k not in ("corrections", "state_id")}
            if view != {k: v for k, v in wanted.items() if k != "state_id"}:
                raise ReceiptConflict(f"state {held['state_id'][:12]} is archived (corrected) with different content")
            return False
    try:
        archive.get(state["state_id"])
    except ArchiveError:
        archive.put(state)
        return True
    existing = archive.get(state["state_id"])
    if existing != wanted:
        raise ReceiptConflict(f"state {state['state_id'][:12]} is archived with different content")
    return False


def stored_state_id(archive: Any, state: Mapping[str, Any]) -> str:
    """The id under which ``state`` is archived: its own, or the original id of the corrected state it equals."""

    wanted = json.loads(json.dumps(state))
    for held in archive.states():
        if held.get("corrections") and held["artefact_hashes"] == wanted["artefact_hashes"] and held["state_id"] != wanted["state_id"]:
            return held["state_id"]
    return wanted["state_id"]


# ---------------------------------------------------------------------------------------------------------------------------
# the ace-playbook release binding (releases i1+): the construction roster, never Fold B
# ---------------------------------------------------------------------------------------------------------------------------

#: The committed permitted roster of the ``stage3-deltas-v1r`` registration (SLURP-STAGE3-ADVANTAGE-R01C-DISAGREEING-V1, a subset of R01C): the
#: repository copy is byte-identical to the data-root file the registration pins (sha256 checked below).
ACE_CARRIER_ROSTER_RELPATH = "docs/receipts/rosters/slurp-stage3-advantage-r01c-disagreeing-v1.json"
ACE_I0_REGISTRATION_RELPATH = f"{tf.PACKAGE_DIR}/ace-playbook-i0-release-registration.json"


def ace_release_binding(repo_root: Path) -> dict:
    """The roster binding of every ``ace-playbook`` release i1 and later, read from the COMMITTED i0 registration.

    ``registration_binding`` is that registration's ``construction_scope`` (R01C), ``permitted_roster`` (a subset of R01C) and
    ``forbidden_rosters`` (Fold A, Fold B, DEV-1000); ``carrier_sample_ids`` are the first :data:`tf.ACE_CARRIERS` sorted ids of the permitted
    roster, so the semantic-knowledge preparer accepts the release. Refuses (LoopError) when the repository copy of the permitted roster does not
    hash to the registration's pin, when its split identity differs from the registration's, or when a carrier lies outside the construction
    roster R01C or inside any committed forbidden roster (the Fold B guard of 2026-09-23)."""

    root = Path(repo_root)
    registration = json.loads((root / ACE_I0_REGISTRATION_RELPATH).read_text(encoding="utf-8"))
    binding = {key: json.loads(json.dumps(registration[key])) for key in ("construction_scope", "permitted_roster", "forbidden_rosters")}
    permitted_path = root / ACE_CARRIER_ROSTER_RELPATH
    if tf.sha256_file(permitted_path) != binding["permitted_roster"]["sha256"]:
        raise LoopError("the repository copy of the permitted roster does not hash to the i0 registration's pin")
    permitted = json.loads(permitted_path.read_text(encoding="utf-8"))
    identity = str(registration["source_split_identity_hash"])
    if permitted.get("split_identity_hash") != identity:
        raise LoopError("the permitted roster's split identity differs from the i0 registration's source_split_identity_hash")
    carriers = sorted(str(item["sample_id"]) for item in permitted["items"])[: tf.ACE_CARRIERS]
    scope = {str(item["sample_id"]) for item in json.loads((root / tf.CONST_ROSTER["arm"]).read_text(encoding="utf-8"))["items"]}
    outside = [c for c in carriers if c not in scope]
    if outside:
        raise LoopError(f"{len(outside)} carrier id(s) lie outside the construction roster {tf.CONST_ROSTER_ID}")
    for pin in binding["forbidden_rosters"]:
        if pin.get("root") != "repo":
            continue
        forbidden = {str(item.get("sample_id") or item["id"])
                     for item in json.loads((root / pin["relpath"]).read_text(encoding="utf-8"))["items"]}
        shared = [c for c in carriers if c in forbidden]
        if shared:
            raise LoopError(f"{len(shared)} carrier id(s) lie inside the forbidden roster {pin['relpath']}")
    return {"registration_binding": binding, "carrier_sample_ids": carriers, "source_split_identity_hash": identity}


def lock_root_hash(repo_root: Path | None = None) -> str:
    """sha256 of the canonical lock v2.2 policy layer: the artefact hash of the typed root state."""

    from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import carrier_module_hooks  # noqa: PLC0415

    layer = carrier_module_hooks(repo_root=repo_root or REPO_ROOT).lock_versions[tf.PARENT_LOCK]()
    return tf.canonical_sha256(layer)


def zero_credit() -> dict:
    """The lock root's own credit vector: zero against itself (the archive requires a measured credit for an accepted state)."""

    zero = {"point": 0.0, "lo": 0.0, "hi": 0.0}
    return {"slu_f1": 0.0, "intent": 0.0, "vs_lock": {"slu": dict(zero), "intent": dict(zero)}, "vs_twin": None, "vs_parent": None,
            "per_scenario": {}, "false_fill": {"n": 0, "delta_pp": 0.0}, "non_empty_exact": {"n": 0, "delta_pp": 0.0},
            "contacts_per_row": 0.0}


def ensure_root_states(archive: Any, *, lock_hash: str, empty_playbook_content_hash: str) -> dict[str, str]:
    """The two iteration-0 roots (typed: the lock; ace: the empty playbook i0). Returns ``{arm: state_id}``."""

    from speech_aware_evidence_acquisition.analysis.sealed_credit import archive as ar  # noqa: PLC0415

    typed = ar.build_state(artefact_hashes={"supply_fragment": lock_hash}, parent_id=None, iteration=0, operator_class=None,
                           candidate_id=None, verdict="accepted", arm="typed", credit=zero_credit(), run_id="lock-v2.2", attempt=0)
    ace_root = ar.build_state(artefact_hashes={"playbook_release": empty_playbook_content_hash}, parent_id=None, iteration=0,
                              operator_class=None, candidate_id=None, verdict="accepted", arm="ace", credit=zero_credit(),
                              run_id="ace-playbook-i0", attempt=0)
    put_state_idempotent(archive, typed)
    put_state_idempotent(archive, ace_root)
    return {"typed": typed["state_id"], "ace": ace_root["state_id"]}


def archive_sha256(archive_dir: Path) -> str:
    """One digest of the archive: the sha256 of the sorted ``state_id:file_sha`` lines."""

    lines = []
    for path in sorted(Path(archive_dir).glob("state-*.json")):
        lines.append(f"{path.name}:{tf.sha256_file(path)}")
    for path in sorted((Path(archive_dir) / "corrections").glob("state-*.json")):      # correction records are part of the archive
        lines.append(f"corrections/{path.name}:{tf.sha256_file(path)}")
    for path in sorted((Path(archive_dir) / "rereads").glob("*-i*.json")):             # so are the reread records
        lines.append(f"rereads/{path.name}:{tf.sha256_file(path)}")
    return tf.sha256_bytes("\n".join(lines).encode("ascii"))


__all__ = [name for name in globals() if not name.startswith("_")]


# ---------------------------------------------------------------------------------------------------------------------------
# typed-receipt entry layouts (owner ruling 300 A, 2026-10-12)
# ---------------------------------------------------------------------------------------------------------------------------

#: Layout label of an entry sealed before the fix: ``sample_id_sha_prefix`` held the RESPONSE-hash prefix and no offered class set was carried.
TYPED_ENTRY_LAYOUT_V1 = "v1-legacy-response-hash-in-sample-id-field"
#: Layout label of an entry built after the fix: ``sample_id_sha_prefix`` is ``sha256(sample_id)[:12]``, ``response_sha256_prefix`` is
#: ``receipt.response_sha256[:12]`` and ``allowed_classes`` is the carrier's offered class set from the proposer brief.
TYPED_ENTRY_LAYOUT_V2 = "v2-sample-id-sha-and-response-sha-prefixes"
FINDING_CLASS_NOT_OFFERED = "class-not-allowed"   # the validator's own refusal code (``tfrl_typed_proposer.validate_candidate``)


def typed_entry_layout(entry: Mapping[str, Any]) -> str:
    """Label the layout of one typed-receipt entry. Both layouts stay readable; the old one is labelled, never rewritten."""

    if "response_sha256_prefix" in entry:
        return TYPED_ENTRY_LAYOUT_V2
    return TYPED_ENTRY_LAYOUT_V1


def typed_entry_response_prefix(entry: Mapping[str, Any]) -> str | None:
    """The response-hash prefix of an entry under either layout (v1 stored it in ``sample_id_sha_prefix``)."""

    if "response_sha256_prefix" in entry:
        return str(entry["response_sha256_prefix"])
    receipt = entry.get("receipt") or {}
    digest = receipt.get("response_sha256")
    if isinstance(digest, str):
        return digest[:12]
    legacy = entry.get("sample_id_sha_prefix")
    return str(legacy) if legacy is not None else None


def typed_entry_sample_id_prefix(entry: Mapping[str, Any]) -> str | None:
    """The sample-id sha prefix of an entry: ``None`` for a v1 entry (its field never held it)."""

    if typed_entry_layout(entry) == TYPED_ENTRY_LAYOUT_V2:
        return str(entry["sample_id_sha_prefix"])
    return None
