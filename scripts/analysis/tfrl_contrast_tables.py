#!/usr/bin/env python3
"""E-T3: the contrast tables the TFRL typed proposer and the ACE reflector read (zero GPU, text-free).

Design: ``docs/superpowers/specs/2026-10-11-slurp-autonomous-typed-loop-with-ace-comparator-design.md``
sections 1.1 (OBSERVE / ANALYSE), 3.3 (the tables are the ONLY content the proposer reads), 4.1-4.2 (the ACE
material: typed credit tables plus per-item helpful / harmful counters computed from official credit).
Short contract: ``docs/readiness/2026-10-11-slurp-tfrl-tables-contract-v1.md``.

From ONE sealed, officially scored column (run id + attempt + arm label) it writes ONE JSON artefact,
``tables-v1.json``, whose last field ``tables_sha256`` is the sha256 of the canonical document (sorted keys,
indent 2) without that field.  Nothing in it depends on the wall clock, so a re-run is byte-identical.

INPUT CONTRACT (what the downstream renderers E-T1 / E-T2 may rely on)
----------------------------------------------------------------------
Top level keys: ``schema`` (``saea-tfrl-contrast-tables-v1``), ``source``, ``suppression``,
``scenario_rows``, ``table_a``, ``table_b``, ``table_c``, ``table_d``, ``table_e``, ``table_f``,
``table_g``, ``tables_sha256``.

* ``source``      -- ``{run_id, attempt, arm, scorer, split, rows, files: {outputs|scores|phases|trace:
                     [relpath, sha256]}}``; ``arm`` is the caller's label for the column.
* ``suppression`` -- ``{min_cell: 3, marker: "<3"}``.  Every COUNT in tables a-d and g that is 1 or 2 is the
                     string ``"<3"`` (0 stays 0), so a cell cannot single out a row.  Rates are computed from
                     the unsuppressed counts and are omitted (null) where their denominator is below 3.
* ``scenario_rows`` -- ``{scenario: rows}`` for the column's gold scenarios (18 on SLURP).
* ``table_a``     -- failure class x slot type x scenario.  ``columns`` = [``class``, ``slot_type``,
                     ``scenario``, ``in_supply``, ``in_store_not_delivered``, ``in_train_not_in_store``,
                     ``nowhere``, ``total``]; ``rows`` = one list per non-empty cell; ``class`` is one of
                     SPURIOUS / MISSING / WRONG-TYPE / BOUNDARY / NEAR / WRONG-VALUE / FORMAT (the
                     ``entity_states.entity_items`` kinds).  The four supply states partition ``total``; the
                     value judged is the gold value for gold-side classes and the predicted value for
                     SPURIOUS:
                       in_supply             printed by a supplied exemplar (E1/E2) or named by a supplied card (E3);
                       in_store_not_delivered  in the exemplar store or any slot card, not supplied to this row;
                       in_train_not_in_store   in TRAIN gold of ANOTHER utterance, not in the store;
                       nowhere               none of the above.
                     ``marginals`` = ``{class_x_state: {class: {state: n}}, class_x_scenario: {...}}``.
* ``table_b``     -- empty-gold false fill per scenario: ``per_scenario[scenario] = {empty_gold_rows,
                     false_fill_rows, false_fill_rate_pct, spurious_entities}``; ``spurious_types_by_scenario
                     [scenario] = {slot_type: n}`` (SPURIOUS items on empty-gold rows) and
                     ``spurious_types_all_rows_by_scenario`` (SPURIOUS items on every row); ``overall``.
* ``table_c``     -- intent: ``per_scenario[scenario] = {rows, intent_wrong_rows, gold_on_shortlist_rows,
                     gold_on_shortlist_rate_pct, wrong_rows_gold_on_shortlist, wrong_rank_histogram}`` where
                     ``wrong_rank_histogram`` has the bins 1, 2, 3, 4-5, 6-10, 11+, off-list, no-shortlist
                     (rank of the gold intent on the Perception shortlist, on intent-WRONG rows).
* ``table_d``     -- supply structure per row, aggregated: ``overall`` and ``per_scenario`` blocks
                     ``{rows, exemplars: {mean,p50,p99}, cards: {...}, supplied_tokens: {...}}``;
                     ``supplied_tokens`` = the first Solver contact's realised prompt tokens (the server's own
                     sealed usage count) or null when the trace pass is skipped.
* ``table_e``     -- exchange rates COPIED from the pinned note
                     ``docs/results/2026-10-09-slurp-nx-exchange-rates-offline.md`` section 4
                     (``analysis/SAEA-SLURP-NX-EXCHANGE-RATES-V1/report.json``, its sha256 recorded): per pool
                     (``comp1b_fold_a`` / ``a2``) analytic and empirical pp per unit, never recomputed here.
* ``table_f``     -- ``{columns: [candidate_id, operator_class, predicted_pp, measured_pp, verdict], rows: []}``;
                     the refused-candidate buffer slot the DRIVER fills; the script always emits it empty.
* ``table_g``     -- ``item_credit`` for the ACE material (section 4.2 step 3).  Only with
                     ``--playbook-release`` (plus a lock column): for each playbook item id,
                     ``rendered_rows`` and the rows whose official per-row SLU-F1 (the scorer's
                     ``slu_f1_f1``) in this column is above / below / equal to the same row in the lock
                     column -> ``helpful`` / ``harmful`` / ``neutral``.  Item ids only, never item text.  With no
                     playbook the table is ``{"items": []}``.

Forbidden content: the self-check ``assert_text_free`` fails the script if any dictionary key equals
``text`` / ``transcript`` / ``gold`` / ``value_text`` / ``utterance`` / ``answer`` (exact, case-insensitive) or a
string value is longer than 200 characters.  Gold labels are used offline on TRAIN / DEV rows exactly as the
existing diagnostics do (``slurp_s1_slu_error_taxonomy``, ``slurp_nx_exchange_rates``) and reach no output.

Reuse, not re-implementation: gold / delivered / sealed-score loaders and ``TrainStats``-free parsing from
``slurp_nx_postproc_v4_search``; phases (exemplars, cards, Perception shortlist) from
``slurp_gold_position_and_solver_freedom_read``; the first-Solver trace pass from
``slurp_nx_exchange_rates``; entity item kinds from ``analysis.sealed_credit.entity_states``.  Zero model,
server, tokenizer, encoder, embedder, scorer-subprocess, network and GPU contacts.

    PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/tfrl_contrast_tables.py \\
        --run-id SAEA-SLURP-STAGE3-NX-R5-COMPOSED-DEV2000-ADDED-V1 \\
        --attempt attempt-slurp-native-stage3-nx-r5-composed-dev2000-added-generation-v1 \\
        --arm r5-composed --scorer slurp-slu-official --split devel --rows 1000
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT / "src"), str(REPO_ROOT / "scripts" / "analysis")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

SCHEMA = "saea-tfrl-contrast-tables-v1"
READ_ID = "SAEA-SLURP-TFRL-TABLES-DEV-V1"
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
EXCHANGE_RATES_RELPATH = "analysis/SAEA-SLURP-NX-EXCHANGE-RATES-V1/report.json"

MIN_CELL = 3
MARKER = "<3"
CLASSES = ("SPURIOUS", "MISSING", "WRONG-TYPE", "BOUNDARY", "NEAR", "WRONG-VALUE", "FORMAT")
STATES = ("in_supply", "in_store_not_delivered", "in_train_not_in_store", "nowhere")
RANK_BINS = ("1", "2", "3", "4-5", "6-10", "11+", "off-list", "no-shortlist")
FORBIDDEN_KEYS = frozenset({"text", "transcript", "gold", "value_text", "utterance", "answer"})
MAX_STRING = 200
REFUSED_COLUMNS = ["candidate_id", "operator_class", "predicted_pp", "measured_pp", "verdict"]
EXCHANGE_POOLS = ("comp1b_fold_a", "a2")
EXCHANGE_EMPIRICAL_KEYS = (
    "remove_one_spurious_entity", "recover_one_missing_entity",
    "one_extra_exact_row.any_non_exact_row", "one_extra_exact_row.non_empty_gold_row",
    "one_extra_exact_row.empty_gold_false_fill_row", "one_extra_exact_row.s1_parsed_not_exact_row",
)


class TablesError(RuntimeError):
    """A sealed input is missing, drifted, or the artefact would carry forbidden content."""


# ---------------------------------------------------------------------------
# pure parts (unit-tested on synthetic rows)


def cell(n: int):
    """A count as published: 0 and >= 3 verbatim, 1 and 2 as the suppression marker."""

    return n if n == 0 or n >= MIN_CELL else MARKER


def rate_pct(num: int, den: int):
    """Percent to two places, or ``None`` where the denominator is below the suppression floor."""

    return round(100.0 * num / den, 2) if den >= MIN_CELL else None


def percentile(values: Sequence[float], p: float):
    """Nearest-rank percentile (deterministic); ``None`` for an empty list."""

    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(p * len(ordered)) - 1)]


def dist(values: Sequence[float]) -> dict:
    vals = [v for v in values if v is not None]
    if len(vals) < MIN_CELL:
        return {"n": cell(len(vals)), "mean": None, "p50": None, "p99": None}
    return {"n": len(vals), "mean": round(sum(vals) / len(vals), 2),
            "p50": percentile(vals, 0.50), "p99": percentile(vals, 0.99)}


def rank_bin(rank: int | None, shortlist_len: int) -> str:
    """The histogram bin of the gold intent's 1-based rank on the Perception shortlist."""

    if shortlist_len == 0:
        return "no-shortlist"
    if rank is None:
        return "off-list"
    if rank <= 3:
        return str(rank)
    if rank <= 5:
        return "4-5"
    if rank <= 10:
        return "6-10"
    return "11+"


def gold_rank(shortlist: Sequence[str], gold_intent: str) -> int | None:
    for k, intent in enumerate(shortlist):
        if intent == gold_intent:
            return k + 1
    return None


def supply_state(value: str, entity_type: str, printed: set, card_hit: bool, store_values: set,
                 store_cards_hit: bool, train_utterances: frozenset, own_utterance: str) -> str:
    """The four-way value-in-supply split of one (type, folded value).  ``printed`` holds the (type, value)
    pairs the row's supplied exemplars print; ``store_values`` every folded filler of the exemplar store;
    ``train_utterances`` the utterance ids whose TRAIN gold carries the value (the row's own is ignored)."""

    if (entity_type, value) in printed or any(v == value for _t, v in printed) or card_hit:
        return "in_supply"
    if value in store_values or store_cards_hit:
        return "in_store_not_delivered"
    if train_utterances - {own_utterance}:
        return "in_train_not_in_store"
    return "nowhere"


def failure_cube(items: Sequence[Mapping]) -> dict:
    """Table (a) from ``items`` = [{class, type, scenario, state}], one per error item."""

    cube: dict[tuple, Counter] = defaultdict(Counter)
    by_state: dict[str, Counter] = defaultdict(Counter)
    by_scenario: dict[str, Counter] = defaultdict(Counter)
    for it in items:
        cube[(it["class"], it["type"], it["scenario"])][it["state"]] += 1
        by_state[it["class"]][it["state"]] += 1
        by_scenario[it["class"]][it["scenario"]] += 1
    rows = []
    for (klass, typ, scen) in sorted(cube, key=lambda k: (CLASSES.index(k[0]), k[1], k[2])):
        c = cube[(klass, typ, scen)]
        rows.append([klass, typ, scen] + [cell(c[s]) for s in STATES] + [cell(sum(c.values()))])
    return {
        "columns": ["class", "slot_type", "scenario", *STATES, "total"],
        "rows": rows,
        "marginals": {
            "class_x_state": {k: {s: cell(by_state[k][s]) for s in STATES} for k in CLASSES if k in by_state},
            "class_x_scenario": {k: {s: cell(n) for s, n in sorted(by_scenario[k].items())}
                                 for k in CLASSES if k in by_scenario},
        },
    }


def empty_gold_table(rows: Sequence[Mapping]) -> dict:
    """Table (b).  ``rows``: {scenario, gold_empty, filled, spurious: [type, ...]} per sample."""

    scen_rows: dict[str, list] = defaultdict(list)
    for r in rows:
        scen_rows[r["scenario"]].append(r)
    per, on_empty, on_all = {}, {}, {}
    tot_empty = tot_fill = tot_spur = 0
    for scen in sorted(scen_rows):
        sub = scen_rows[scen]
        empty = [r for r in sub if r["gold_empty"]]
        fills = [r for r in empty if r["filled"]]
        spur_empty = Counter(t for r in empty for t in r["spurious"])
        spur_all = Counter(t for r in sub for t in r["spurious"])
        per[scen] = {"empty_gold_rows": cell(len(empty)), "false_fill_rows": cell(len(fills)),
                     "false_fill_rate_pct": rate_pct(len(fills), len(empty)),
                     "spurious_entities": cell(sum(spur_empty.values()))}
        on_empty[scen] = {t: cell(n) for t, n in sorted(spur_empty.items())}
        on_all[scen] = {t: cell(n) for t, n in sorted(spur_all.items())}
        tot_empty += len(empty)
        tot_fill += len(fills)
        tot_spur += sum(spur_empty.values())
    return {"per_scenario": per, "spurious_types_by_scenario": on_empty,
            "spurious_types_all_rows_by_scenario": on_all,
            "overall": {"empty_gold_rows": cell(tot_empty), "false_fill_rows": cell(tot_fill),
                        "false_fill_rate_pct": rate_pct(tot_fill, tot_empty),
                        "spurious_entities": cell(tot_spur)}}


def intent_table(rows: Sequence[Mapping]) -> dict:
    """Table (c).  ``rows``: {scenario, intent_ok, shortlist_len, rank} per sample."""

    scen_rows: dict[str, list] = defaultdict(list)
    for r in rows:
        scen_rows[r["scenario"]].append(r)
    per = {}
    tot = Counter()
    for scen in sorted(scen_rows):
        sub = scen_rows[scen]
        wrong = [r for r in sub if not r["intent_ok"]]
        on = [r for r in sub if r["rank"] is not None]
        wrong_on = [r for r in wrong if r["rank"] is not None]
        hist = Counter(rank_bin(r["rank"], r["shortlist_len"]) for r in wrong)
        per[scen] = {"rows": cell(len(sub)), "intent_wrong_rows": cell(len(wrong)),
                     "gold_on_shortlist_rows": cell(len(on)),
                     "gold_on_shortlist_rate_pct": rate_pct(len(on), len(sub)),
                     "wrong_rows_gold_on_shortlist": cell(len(wrong_on)),
                     "wrong_rank_histogram": {b: cell(hist[b]) for b in RANK_BINS}}
        tot["rows"] += len(sub)
        tot["wrong"] += len(wrong)
        tot["on"] += len(on)
        tot["wrong_on"] += len(wrong_on)
    return {"per_scenario": per,
            "overall": {"rows": cell(tot["rows"]), "intent_wrong_rows": cell(tot["wrong"]),
                        "gold_on_shortlist_rate_pct": rate_pct(tot["on"], tot["rows"]),
                        "wrong_rows_gold_on_shortlist": cell(tot["wrong_on"])}}


def structure_table(rows: Sequence[Mapping]) -> dict:
    """Table (d).  ``rows``: {scenario, exemplars, cards, prompt_tokens|None} per sample."""

    def block(sub):
        return {"rows": cell(len(sub)),
                "exemplars": dist([r["exemplars"] for r in sub]),
                "cards": dist([r["cards"] for r in sub]),
                "supplied_tokens": dist([r["prompt_tokens"] for r in sub])}

    groups: dict[str, list] = defaultdict(list)
    for r in rows:
        groups[r["scenario"]].append(r)
    return {"overall": block(list(rows)), "per_scenario": {s: block(groups[s]) for s in sorted(groups)}}


def item_credit_table(item_ids: Sequence[str], rendered: Mapping[str, set], column_slu: Mapping[str, float],
                      lock_slu: Mapping[str, float]) -> dict:
    """Table (g): per playbook item, rows rendered and the official per-row SLU delta sign vs the lock column."""

    out = []
    for item in sorted(item_ids):
        helpful = harmful = neutral = 0
        rows = [s for s, ids in rendered.items() if item in ids]
        for s in rows:
            delta = column_slu[s] - lock_slu[s]
            if delta > 1e-12:
                helpful += 1
            elif delta < -1e-12:
                harmful += 1
            else:
                neutral += 1
        out.append({"item_id": item, "rendered_rows": cell(len(rows)), "helpful": cell(helpful),
                    "harmful": cell(harmful), "neutral": cell(neutral)})
    return {"items": out}


def assert_text_free(node, path: str = "$") -> None:
    """Fail on a forbidden key or an over-long string leaf anywhere in the artefact."""

    if isinstance(node, Mapping):
        for key, value in node.items():
            if str(key).lower() in FORBIDDEN_KEYS:
                raise TablesError(f"forbidden key {key!r} at {path}")
            assert_text_free(value, f"{path}.{key}")
    elif isinstance(node, (list, tuple)):
        for k, value in enumerate(node):
            assert_text_free(value, f"{path}[{k}]")
    elif isinstance(node, str) and len(node) > MAX_STRING:
        raise TablesError(f"string longer than {MAX_STRING} characters at {path}")


def finalize(document: dict) -> dict:
    """Attach ``tables_sha256`` (the hash of the canonical document without that field)."""

    assert_text_free(document)
    body = {k: v for k, v in document.items() if k != "tables_sha256"}
    text = json.dumps(body, indent=2, sort_keys=True)
    out = dict(body)
    out["tables_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return out


def exchange_table(report: Mapping, report_sha256: str) -> dict:
    """Table (e), copied from the pinned exchange-rate report; nothing recomputed."""

    pools = {}
    for name in EXCHANGE_POOLS:
        pool = report["pools"][name]
        emp = {}
        for key in EXCHANGE_EMPIRICAL_KEYS:
            block = pool["empirical_rates"][key]
            emp[key] = {"mean_pp": block.get("mean_pp"), "n": block.get("n")}
        pools[name] = {
            "split": pool["split"], "rows": pool["rows"],
            "analytic_rates_pp": dict(sorted(pool["analytic_rates"].items())),
            "empirical_rates_pp": emp,
            "node_rates": {k: v for k, v in sorted(pool["node_rates"].items()) if k != "note"},
        }
    return {"source": EXCHANGE_RATES_RELPATH, "source_sha256": report_sha256,
            "note": "docs/results/2026-10-09-slurp-nx-exchange-rates-offline.md section 4",
            "pools": pools}


# ---------------------------------------------------------------------------
# loaders (sealed bytes only)


def import_path(path: Path, name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_playbook_item_ids(path: Path) -> list[str]:
    """Item ids of a playbook release.  Accepts a snapshot (``values[].value_id``) or ``items[].item_id``;
    only ids are read, never an item's text."""

    document = json.loads(path.read_text(encoding="utf-8"))
    ids = []
    for value in document.get("values") or ():
        vid = str(value["value_id"])
        ids.append(vid.split("value:", 1)[-1].rsplit("::", 1)[-1])
    for item in document.get("items") or ():
        ids.append(str(item["item_id"]))
    if not ids:
        raise TablesError(f"{path}: no playbook items (expected values[].value_id or items[].item_id)")
    return sorted(set(ids))


def rendered_item_ids(phase_row: Mapping, item_ids: set) -> set:
    seen = set()
    pool = list(phase_row.get("solver_ids") or ()) + list(phase_row.get("ex_rendered") or ()) + \
        list(phase_row.get("contracts") or ()) + list(phase_row.get("boundary") or ())
    for raw in pool:
        raw = str(raw)
        for cand in (raw, raw.split("value:", 1)[-1], raw.rsplit("::", 1)[-1]):
            if cand in item_ids:
                seen.add(cand)
    return seen


def build(args) -> dict:
    from speech_aware_evidence_acquisition.analysis.sealed_credit.entity_states import entity_items, fold
    from speech_aware_evidence_acquisition.data.lock import load_lock

    V4 = import_path(REPO_ROOT / "scripts/analysis/slurp_nx_postproc_v4_search.py", "slurp_nx_postproc_v4_search")
    ES = import_path(REPO_ROOT / "scripts/analysis/slurp_agree_arm_error_sources.py",
                     "slurp_agree_arm_error_sources")
    W5 = import_path(REPO_ROOT / "scripts/analysis/slurp_w5_fold_a_offline_estimate.py",
                     "slurp_w5_fold_a_offline_estimate")
    GP = ES.GP
    ER = import_path(REPO_ROOT / "scripts/analysis/slurp_nx_exchange_rates.py", "slurp_nx_exchange_rates")

    data_root = Path(args.data_root)
    lock = load_lock(Path(args.lock))
    if args.split not in ("train", "devel"):
        raise TablesError(f"split {args.split!r} is not read (the test split is closed)")
    spec = {"label": args.arm, "run_id": args.run_id, "attempt": args.attempt, "scorer": args.scorer,
            "split": args.split, "rows": args.rows}

    gold = V4.load_gold(lock, data_root, args.split)
    delivered = V4.load_delivered(data_root, spec)
    ids = sorted(delivered["rows"])
    if any(s not in gold for s in ids):
        raise TablesError("roster ids absent from the gold split")
    phases = GP.load_phases(data_root, spec)
    if set(phases["rows"]) != set(ids):
        raise TablesError("the phase artefact does not cover the roster")
    directory = phases["directory"]

    # --- the store: exemplar snapshot, slot cards, TRAIN gold ------------------------------------
    pool = GP.load_exemplar_pool(data_root, ES.EX_SNAPSHOT)
    m1 = W5.snapshot_values(data_root, W5.M1_SNAPSHOT)
    m1_by_key = {vid.split("value:", 1)[-1]: v for vid, v in m1.items()}
    cards = GP.load_contract_bodies(data_root)
    store_values = {f for v in pool["values"].values() for fl in v["fillers"].values() for f in fl}
    all_cards = "\n".join(cards["bodies"].values())
    train_gold = gold if args.split == "train" else V4.load_gold(lock, data_root, "train")
    train_index: dict[str, set] = defaultdict(set)
    for g in train_gold.values():
        for e in g["entities"]:
            train_index[fold(e.filler)].add(g["utterance_id"])

    card_cache: dict[str, bool] = {}

    def in_all_cards(value: str) -> bool:
        if len(value) < 3:
            return False
        if value not in card_cache:
            card_cache[value] = re.search(r"(?<![a-z0-9])" + re.escape(value) + r"(?![a-z0-9])", all_cards) is not None
        return card_cache[value]

    # --- first-Solver prompt tokens ---------------------------------------------------------------
    contacts, trace_path = {}, directory / f"{args.run_id}.trace.jsonl"
    if not args.no_trace:
        contacts = ER.first_solver_contacts(trace_path, set(ids))

    items, empty_rows, intent_rows, struct_rows, unresolved = [], [], [], [], 0
    column_slu = {}
    for sid in ids:
        g = gold[sid]
        scen = g["scenario"]
        d = delivered["rows"][sid]
        ph = phases["rows"][sid]
        pred = d["entities"] if d["parsed"] else ()
        printed = set()
        for key in ph["ex_rendered"]:
            value = m1_by_key.get(key)
            if value is None:
                unresolved += 1
                continue
            printed |= W5.printed_pairs(value.content)
        card_bodies = [cards["bodies"].get(c, "") for c in ph["contracts"]]
        card_cache_row: dict[str, bool] = {}

        def row_card_hit(value: str) -> bool:
            if len(value) < 3:
                return False
            if value not in card_cache_row:
                pat = re.compile(r"(?<![a-z0-9])" + re.escape(value) + r"(?![a-z0-9])")
                card_cache_row[value] = any(pat.search(b) for b in card_bodies)
            return card_cache_row[value]

        spurious_types = []
        for it in entity_items(tuple(g["entities"]), tuple(pred)):
            if it["gold_index"] is None:
                ent = pred[it["pred_index"]]
                spurious_types.append(it["type"])
            else:
                ent = g["entities"][it["gold_index"]]
            value = fold(ent.filler)
            state = supply_state(value, ent.type, printed, row_card_hit(value), store_values, in_all_cards(value),
                                 frozenset(train_index.get(value, ())), g["utterance_id"])
            items.append({"class": it["kind"], "type": it["type"], "scenario": scen, "state": state})
        sealed = delivered["sealed"][sid]
        empty_rows.append({"scenario": scen, "gold_empty": not g["entities"],
                           "filled": bool(d["parsed"] and pred), "spurious": spurious_types})
        gold_intent = f"{g['scenario']}_{g['action']}"
        shortlist = list(ph["perception"])
        intent_rows.append({"scenario": scen, "intent_ok": float(sealed["scenario_action_exact"]) >= 1.0,
                            "shortlist_len": len(shortlist), "rank": gold_rank(shortlist, gold_intent)})
        struct_rows.append({"scenario": scen, "exemplars": len(ph["ex_rendered"]), "cards": len(ph["contracts"]),
                            "prompt_tokens": (contacts.get(sid) or {}).get("prompt_tokens")})
        column_slu[sid] = float(sealed["slu_f1_f1"])

    files = {"outputs": delivered["outputs"], "scores": delivered["scores"],
             "phases": [phases["relpath"], phases["sha256"]],
             "trace": [str(trace_path.relative_to(data_root)), sha256_file(trace_path)] if not args.no_trace else None}

    # --- table (g): item credit --------------------------------------------------------------------
    playbook = None
    if args.playbook_release:
        if not (args.lock_run_id and args.lock_attempt):
            raise TablesError("--playbook-release needs the lock column (--lock-run-id / --lock-attempt)")
        lock_spec = dict(spec, label="lock", run_id=args.lock_run_id, attempt=args.lock_attempt,
                         scorer=args.lock_scorer or args.scorer)
        lock_delivered = V4.load_delivered(data_root, lock_spec)
        if sorted(lock_delivered["rows"]) != ids:
            raise TablesError("the lock column and the column disagree on the roster")
        lock_slu = {s: float(lock_delivered["sealed"][s]["slu_f1_f1"]) for s in ids}
        item_ids = load_playbook_item_ids(Path(args.playbook_release))
        wanted = set(item_ids)
        rendered = {s: rendered_item_ids(phases["rows"][s], wanted) for s in ids}
        playbook = item_credit_table(item_ids, rendered, column_slu, lock_slu)
        playbook["playbook_release"] = {"path": str(Path(args.playbook_release).name),
                                        "sha256": sha256_file(Path(args.playbook_release)),
                                        "lock_run_id": args.lock_run_id}
    table_g = playbook if playbook is not None else {"playbook_release": None, "items": []}

    # --- table (e): pinned exchange rates -----------------------------------------------------------
    rates_path = data_root / EXCHANGE_RATES_RELPATH
    table_e = exchange_table(json.loads(rates_path.read_text(encoding="utf-8")), sha256_file(rates_path))

    scen_counts = Counter(gold[s]["scenario"] for s in ids)
    document = {
        "schema": SCHEMA,
        "source": {"run_id": args.run_id, "attempt": args.attempt, "arm": args.arm, "scorer": args.scorer,
                   "split": args.split, "rows": len(ids), "files": files,
                   "store": {"exemplar_snapshot": [pool["relpath"], pool["sha256"]],
                             "slot_cards": [cards["relpath"], cards["sha256"]],
                             "unresolved_exemplar_keys": unresolved}},
        "suppression": {"min_cell": MIN_CELL, "marker": MARKER},
        "scenario_rows": {s: cell(n) for s, n in sorted(scen_counts.items())},
        "table_a": failure_cube(items),
        "table_b": empty_gold_table(empty_rows),
        "table_c": intent_table(intent_rows),
        "table_d": structure_table(struct_rows),
        "table_e": table_e,
        "table_f": {"columns": REFUSED_COLUMNS, "rows": []},
        "table_g": table_g,
    }
    return finalize(document)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--arm", required=True, help="caller's label for the column (recorded, not interpreted)")
    parser.add_argument("--scorer", default="slurp-slu-official", help="scores.json block key")
    parser.add_argument("--split", required=True, choices=("train", "devel"))
    parser.add_argument("--rows", type=int, required=True, help="roster size (the complete column)")
    parser.add_argument("--data-root", default=os.environ.get("SPEECHRL_DATA_DIR", DEFAULT_DATA_ROOT))
    parser.add_argument("--lock", default=DEFAULT_LOCK)
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--no-trace", action="store_true", help="skip the first-Solver trace pass (tokens null)")
    parser.add_argument("--playbook-release", default=None,
                        help="ACE playbook release JSON: fills table_g (item_credit); needs the lock column")
    parser.add_argument("--lock-run-id", default=None)
    parser.add_argument("--lock-attempt", default=None)
    parser.add_argument("--lock-scorer", default=None)
    args = parser.parse_args(argv)
    document = build(args)
    out_dir = Path(args.out_dir) if args.out_dir else Path(args.data_root) / "analysis" / READ_ID / args.run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "tables-v1.json"
    out.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"tfrl contrast tables: wrote {out} tables_sha256={document['tables_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
