#!/usr/bin/env python3
"""R0.4 diagnostic: attribute the per-scenario losses of the v4 post-processing column (zero GPU).

The R0.4 read (``docs/results/2026-10-09-slurp-nx-postprocessing-v4-offline-read.md``) selected v4 =
v3 + fx-article + fx-oclock + scope + ti1 + ee10 on A2 and confirmed it once on TRAIN Fold A. Fold A
loses -17.47 pp on its 60 audio rows; A2 loses on iot, datetime and email. This driver is a
DIAGNOSTIC RE-READ of those two already-produced columns. It is not a new selection and not a second
confirmation: the rule list is fixed (the selected five), nothing is chosen on Fold A, and the
sibling driver's write-once ``confirm-fold-a`` report is never touched.

What it computes, per pool (``a2``, ``fold-a``), from the sealed delivered column and the same
TRAIN statistics as the search driver (it imports that driver and calls its ``prepare_partA``, so
the base matrix is re-proved row by row against the sealed official fields):

  * the full v4 column and its per-scenario delta (must equal the search driver's report);
  * per rule, the column WITHOUT that rule and the per-scenario marginal
    (delta(v4) - delta(v4 minus the rule));
  * per rule, the cumulative step delta in the fixed application order (the steps telescope to the
    full delta);
  * a trace of every edit, attributed to the rule that made it: per scenario x rule x slot TYPE,
    drops and filler rewrites, each classed against gold (exact / spurious / other matched);
  * per firing intent, the TRAIN pool statistics the rule consulted (pool exemplars, entity rate,
    type share) -- TRAIN-side numbers only.

``--guards`` (A2 only, the selection pool) additionally reads the named guards of ``GUARDS``, each
defined from TRAIN pool statistics and the rule's own threshold (never from Fold-A gold), plus an
n-threshold sensitivity sweep that is reported as such and is not a guard. Fold A is never read
under a guard: a guard that changes the rule set needs a fresh confirmation roster.

Gold discipline: gold enters only offline through the governed loader (via the search driver's
``load_gold``: ``train`` / ``devel``; the test split is refused). The report holds rule ids, slot
TYPE names, scenario names, intent ids, counts, pp and hashes only -- no utterance, transcript,
filler, gold value or model output text. Zero model, server, tokenizer, encoder, embedder, network
and GPU contacts.

    PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/slurp_nx_postproc_v4_audio_attribution.py
    PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/slurp_nx_postproc_v4_audio_attribution.py --guards
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

READ_ID = "SAEA-SLURP-NX-POSTPROC-V4-AUDIO-ATTRIBUTION-V1"
SCHEMA = "saea-slurp-nx-postproc-v4-audio-attribution-v1"
V4 = ("fx-article", "fx-oclock", "scope", "ti1", "ee10")


def import_path(path: Path, name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


DRV = import_path(REPO_ROOT / "scripts/analysis/slurp_nx_postproc_v4_search.py", "slurp_nx_postproc_v4_search")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# edit trace


def trace(rules, ents, ctx, stats, env, gold_entities, rule_fns):
    """Apply ``rules`` in order; return the kept pairs and one event per edit, attributed to the rule
    that made it: (rule, kind, slot type, class), class against gold at that step."""
    pairs = list(enumerate(ents))
    events = []
    for rule in rules:
        before = pairs
        after = rule_fns[rule](before, ctx, stats, env)
        cls_before = DRV.entity_class(gold_entities, [e for _i, e in before])
        kept = {i for i, _e in after}
        where = {i: (pos, e) for pos, (i, e) in enumerate(before)}
        for pos, (i, e) in enumerate(before):
            if i not in kept:
                events.append((rule, "drop", e.type, cls_before[pos]))
        cls_after = DRV.entity_class(gold_entities, [e for _i, e in after]) if after else {}
        for pos, (i, e) in enumerate(after):
            if e != where[i][1]:
                events.append((rule, "rewrite", e.type, f"{cls_before[where[i][0]]}->{cls_after[pos]}"))
        pairs = after
    return pairs, events


def build_column(P, rules, rule_fns, stats=None):
    """The search driver's ``ColumnBuilder.build`` arithmetic with a pluggable rule table, plus the
    edit trace. Returns the matrix, the edited ids and the events keyed by sample id."""
    import numpy as np
    stats = stats or P["stats"]
    env = P["builder"].env
    matrix = P["base"].copy()
    events_by_row = {}
    for k, sid in enumerate(P["ids"]):
        row = P["delivered"]["rows"][sid]
        ents = row["entities"]
        if not row["parsed"] or not ents or not rules:
            continue
        pairs, events = trace(rules, ents, P["contexts"][sid], stats, env, P["gold"][sid]["entities"], rule_fns)
        new = [e for _i, e in pairs]
        if new == list(ents):
            continue
        events_by_row[sid] = events
        vec = DRV.score_vector(P["gold"][sid], row["scenario"], row["action"], new)
        if vec[9] != matrix[k, 9]:
            raise DRV.SearchError("a rule changed intent")
        matrix[k] = np.array(vec)
    return matrix, events_by_row


def scenario_of(P):
    return {sid: P["gold"][sid]["scenario"] for sid in P["ids"]}


def scen_delta(P, left, right):
    out = DRV.per_scenario(P["ids"], P["gold"], left, right)
    return {s: v["delta_pp"] for s, v in out["per_scenario"].items()}, out


def attribute(P, rule_fns=None):
    rule_fns = rule_fns or DRV.RULES
    base = P["base"]
    scen = scenario_of(P)
    full, events_full = build_column(P, V4, rule_fns)
    full_delta, full_block = scen_delta(P, base, full)
    pooled_full = P["boot"].contrast(base, full)
    # marginal removal
    marginal = {}
    for rule in V4:
        reduced = tuple(r for r in V4 if r != rule)
        m, _e = build_column(P, reduced, rule_fns)
        d, _b = scen_delta(P, base, m)
        marginal[rule] = {
            "pooled_marginal_pp": round(pooled_full["delta_slu_pp"] - P["boot"].contrast(base, m)["delta_slu_pp"], 4),
            "per_scenario_marginal_pp": {s: round(full_delta[s] - d[s], 4) for s in sorted(full_delta)},
        }
    # cumulative steps (telescoping)
    steps = {}
    prev = base
    for k, rule in enumerate(V4):
        m, _e = build_column(P, V4[:k + 1], rule_fns)
        d, _b = scen_delta(P, prev, m)
        steps[rule] = {"per_scenario_step_pp": {s: round(v, 4) for s, v in sorted(d.items())},
                       "pooled_step_pp": round(P["boot"].contrast(prev, m)["delta_slu_pp"], 4)}
        prev = m
    # per-rule single (alone)
    alone = {}
    for rule in V4:
        m, _e = build_column(P, (rule,), rule_fns)
        d, _b = scen_delta(P, base, m)
        alone[rule] = {s: round(v, 4) for s, v in sorted(d.items())}
    # event table: scenario -> rule -> kind -> type -> class -> count
    table = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(Counter))))
    rows_by = defaultdict(lambda: defaultdict(set))
    intents = defaultdict(lambda: defaultdict(Counter))
    row_effect = defaultdict(lambda: defaultdict(Counter))
    index = {sid: k for k, sid in enumerate(P["ids"])}
    for sid, events in events_full.items():
        s = scen[sid]
        intent = P["contexts"][sid].intent
        rules_here = sorted({e[0] for e in events}, key=V4.index)
        before, after = DRV.row_f1(base[index[sid]]), DRV.row_f1(full[index[sid]])
        effect = "save" if after > before + 1e-12 else "harm" if after < before - 1e-12 else "neutral"
        row_effect[s]["+".join(rules_here)][effect] += 1
        for rule, kind, slot_type, cls in events:
            table[s][rule][kind][slot_type][cls] += 1
            rows_by[s][rule].add(sid)
            if rule in ("ti1", "ee10"):
                intents[intent][rule][f"{kind}:{slot_type}:{cls}"] += 1
    intent_stats = {}
    for intent in sorted(i for i in intents if i):
        st = P["stats"]
        types = sorted({k.split(":")[1] for r in intents[intent].values() for k in r})
        intent_stats[intent] = {
            "pool_exemplars": st.intent_n.get(intent, 0),
            "pool_entity_rate": None if st.entity_rate(intent) is None else round(st.entity_rate(intent), 4),
            "pool_type_share": {t: round(st.type_share(intent, t), 4) for t in types},
            "pool_type_count": {t: st.intent_type[intent][t] for t in types},
            "events": {r: dict(sorted(c.items())) for r, c in sorted(intents[intent].items())},
            "scenario_of_intent": intent.split("_", 1)[0],
        }
    return {
        "pooled": pooled_full,
        "per_scenario": full_block,
        "marginal_removal": marginal,
        "cumulative_steps": steps,
        "rule_alone_per_scenario_pp": alone,
        "events": {s: {r: {k: {t: dict(sorted(c.items())) for t, c in sorted(tv.items())}
                           for k, tv in sorted(kv.items())}
                       for r, kv in sorted(rv.items(), key=lambda x: V4.index(x[0]))}
                   for s, rv in sorted(table.items())},
        "rows_edited_by_rule": {s: {r: len(v) for r, v in sorted(rv.items(), key=lambda x: V4.index(x[0]))}
                                for s, rv in sorted(rows_by.items())},
        "row_effect_by_rule_set": {s: {k: dict(c) for k, c in sorted(v.items())} for s, v in sorted(row_effect.items())},
        "firing_intents_ti1_ee10": intent_stats,
    }


# ---------------------------------------------------------------------------
# guards (A2 only; parameters fixed from TRAIN pool statistics)


Z95 = 1.959963984540054


def wilson_upper(k: int, n: int, z: float = Z95) -> float:
    """The Wilson score interval's upper bound for k successes of n (TRAIN pool counts only)."""
    if n == 0:
        return 1.0
    p = k / n
    centre = p + z * z / (2 * n)
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return (centre + half) / (1 + z * z / n)


#: The guards, each defined from TRAIN pool statistics and the rule's own threshold only:
#:  ti-expressible  ti1 fires on an intent only when its pool holds >= 1 / 0.01 = 100 exemplars, i.e.
#:                  when "< 1 %" is a different statement from "never seen" (below 100 exemplars
#:                  ti1 degenerates into ti0 on a sample too small to show rarity)
#:  ee-wilson       ee10 fires on an intent only when its pool entity rate is RESOLVED below 10 %:
#:                  the Wilson 95 % upper bound of (exemplars with entities) / (exemplars) < 0.10
#:  ee-np5          ee10 fires only when the threshold is worth >= 5 expected exemplars
#:                  (n * 0.10 >= 5, the normal-approximation adequacy rule), i.e. n >= 50
GUARDS = ("ti-expressible", "ee-wilson", "ee-np5")


def guarded_rules(guards, min_n_sweep: int | None = None):
    base_ti, base_ee = DRV.RULES["ti1"], DRV.RULES["ee10"]

    def n_of(ctx, stats):
        return stats.intent_n.get(ctx.intent, 0) if ctx.intent else 0

    def ti(entities, ctx, stats, env):
        n = n_of(ctx, stats)
        if "ti-expressible" in guards and n < round(1 / DRV.TI1_SHARE):
            return entities
        if min_n_sweep is not None and n < min_n_sweep:
            return entities
        return base_ti(entities, ctx, stats, env)

    def ee(entities, ctx, stats, env):
        n = n_of(ctx, stats)
        if "ee-wilson" in guards and n and wilson_upper(stats.intent_with_entities[ctx.intent], n) >= 0.10:
            return entities
        if "ee-np5" in guards and n * 0.10 < 5:
            return entities
        if min_n_sweep is not None and n < min_n_sweep:
            return entities
        return base_ee(entities, ctx, stats, env)

    fns = dict(DRV.RULES)
    fns["ti1"], fns["ee10"] = ti, ee
    return fns


def pool_guard_table(stats) -> dict:
    """TRAIN-only: the intents ee10 can fire on and what each guard decides for them, and how many
    intents ti-expressible removes from ti1."""
    ee = {}
    for intent in sorted(stats.intent_n):
        n = stats.intent_n[intent]
        k = stats.intent_with_entities[intent]
        if k / n < 0.10:
            ee[intent] = {"pool_exemplars": n, "with_entities": k, "rate": round(k / n, 4),
                          "wilson_upper_95": round(wilson_upper(k, n), 4),
                          "ee_wilson_fires": wilson_upper(k, n) < 0.10, "ee_np5_fires": n * 0.10 >= 5}
    small = sorted(i for i, n in stats.intent_n.items() if n < 100)
    return {"ee10_intents": ee, "intents_below_100_pool_exemplars": len(small),
            "intents_total": len(stats.intent_n), "pool_exemplars_in_those_intents":
            sum(stats.intent_n[i] for i in small)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pools", default="a2,fold-a")
    parser.add_argument("--guards", action="store_true", help="A2 only: read the TRAIN-fixed guard variants")
    parser.add_argument("--guard-min-n", default="50,100,200", help="sensitivity sweep only (not a guard)")
    parser.add_argument("--data-root", default=DRV.DEFAULT_DATA_ROOT)
    parser.add_argument("--lock", default=DRV.DEFAULT_LOCK)
    args = parser.parse_args(argv)
    args.row_cluster = False
    out_root = Path(args.data_root) / "analysis" / READ_ID
    summary = {}
    for pool in [p.strip() for p in args.pools.split(",") if p.strip()]:
        if pool not in ("a2", "fold-a"):
            raise SystemExit("pools: a2, fold-a")
        P = DRV.prepare_partA(args, pool)
        report = {"pool": pool, "base": DRV.base_block(P), "rules": list(V4), "attribution": attribute(P)}
        if args.guards and pool == "a2":
            variants = [
                ("v4 (no guard)", (), None, V4),
                ("v4 minus ee10", (), None, tuple(r for r in V4 if r != "ee10")),
                ("ee-wilson", ("ee-wilson",), None, V4),
                ("ee-np5", ("ee-np5",), None, V4),
                ("ti-expressible", ("ti-expressible",), None, V4),
                ("ti-expressible + ee-wilson", ("ti-expressible", "ee-wilson"), None, V4),
                ("ti-expressible + ee-np5", ("ti-expressible", "ee-np5"), None, V4),
            ] + [(f"sensitivity: ti1 and ee10 need pool n>={n}", (), n, V4)
                 for n in [int(x) for x in args.guard_min_n.split(",") if x]]
            guards = {}
            v4_matrix = build_column(P, V4, DRV.RULES)[0]
            for label, names, sweep, rules in variants:
                m, _e = build_column(P, rules, guarded_rules(names, sweep))
                _d, block = scen_delta(P, P["base"], m)
                over_v4 = P["boot"].contrast(v4_matrix, m)
                guards[label] = {"pooled": P["boot"].contrast(P["base"], m), "per_scenario": block,
                                 "vs_v4": {k: over_v4[k] for k in ("delta_slu_pp", "ci95_slu_pp")},
                                 "rows_scoring_differently_from_v4": int(sum(
                                     1 for k in range(len(P["ids"])) if (m[k] != v4_matrix[k]).any()))}
            report["guards"] = guards
            report["guard_pool_table"] = pool_guard_table(P["stats"])
        if args.guards and pool == "fold-a":
            report["guards"] = "not read on Fold A (a guard that changes the rule set needs a fresh confirmation)"
        report.update({"read_id": READ_ID, "schema": SCHEMA, "status": "DESCRIPTIVE",
                       "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                       "driver_sha256": sha256_file(Path(__file__)),
                       "search_driver_sha256": sha256_file(REPO_ROOT / "scripts/analysis/slurp_nx_postproc_v4_search.py"),
                       "contacts": {k: 0 for k in ("model", "server", "tokenizer", "encoder", "embedder",
                                                   "network", "gpu", "paid_api", "scorer")}})
        out_dir = out_root / pool
        out_dir.mkdir(parents=True, exist_ok=True)
        text = json.dumps(report, indent=1, sort_keys=True, default=str) + "\n"
        (out_dir / "report.json").write_text(text, encoding="utf-8", newline="\n")
        summary[pool] = {"report": str(out_dir / "report.json"), "sha256": sha256_file(out_dir / "report.json")}
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
