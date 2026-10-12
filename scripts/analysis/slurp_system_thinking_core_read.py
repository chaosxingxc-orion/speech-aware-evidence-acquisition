#!/usr/bin/env python3
"""slurp_system_thinking_core_read.py -- the preregistered READ of the 268-B read (the locked SLURP system on the Thinking core, TRAIN Fold B).

Package ``docs/readiness/2026-10-12-slurp-system-thinking-core-fold-b-v1/``. Two stages:

  smoke   the four-row Thinking-system smoke: per-NODE decode cost from the sealed trace (completion tokens, seconds, cap hits, empty
          completions, forced closes, finish reasons) and the GPU-hour projection. Nothing is scored; the coordinator reads it to sign off the arms.
  read    the full read over four sealed, scored arms on the SAME 1,080-row TRAIN Fold B roster:
            lock   the Thinking system arm (this package)             aa    its request-identical twin (this package)
            inst   the Instruct lock column of loop iteration 3        bare  the bare Thinking core of 266-E (direct-only form)
          Paired, utterance-cluster bootstrap (10,000 draws, seed 20261011):
            d_system   = SLU(lock) - SLU(inst)            the transfer of the core lever to the system (cross-flight)
            o_twin     = SLU(aa)   - SLU(lock)            the same-core offset the contrast is judged against (the in-chain A/A)
            d_vs_bare  = SLU(lock) - SLU(bare)            what the system adds on the Thinking core
            transfer   = d_system / 11.90                 the share of the bare core delta (266-E) the system keeps
          each also for intent (scenario_action exact), per scenario (natural-mixture and equal-scenario weightings), the cap-hit / empty-completion /
          parse-failure table per NODE (Perception vs Solver contacts) and the cost per contact per node.

Verdict (preregistered; development numbers only, never a test claim; claims_benefit is false):
  HARM                 d_system <= -bar and the CI95 upper bound < -|o_twin|
  TRANSFERS-ABOVE-BAR  d_system >= bar, CI95 lower bound > |o_twin|, intent guard holds and no reasoning marker was delivered
  PARTIAL              the CI95 lower bound > |o_twin| (a resolved positive effect) but d_system < bar, or the intent guard fails
  NO-TRANSFER          otherwise
bar = 2.5 pp (the cross-flight bar at n = 1,080); intent guard: the intent delta CI95 lower bound >= -0.65 pp (decision 190 floor).

Model-free. Every sealed byte is opened read-only. NO utterance text, transcript, gold label, model output or reasoning text is printed or
persisted: contact text is reduced to booleans and counts at read time and dropped.

    python -B scripts/analysis/slurp_system_thinking_core_read.py --stage smoke --data-root $SPEECHRL_DATA_DIR
    python -B scripts/analysis/slurp_system_thinking_core_read.py --stage read  --data-root $SPEECHRL_DATA_DIR
"""

from __future__ import annotations

import re

import argparse
import base64
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Callable, Mapping, Sequence

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parents[1]
for _path in (str(_REPO / "src"), str(_HERE), str(_REPO / "scripts" / "flights" / "direct"), str(_REPO / "scripts" / "flights" / "tfrl")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import slurp_direct_fold_b_core_read as base  # noqa: E402
import thinking_system_family as fam  # noqa: E402

from speech_aware_evidence_acquisition.analysis.paired import resampled_statistic  # noqa: E402


def _authority_default() -> str:
    """The data-root default assigned in scripts/lib/data_root.sh (decision 274: one authority, no literal here)."""
    lib = Path(__file__).resolve().parents[1] / "lib" / "data_root.sh"
    match = re.search(r"^SAEA_DATA_ROOT_DEFAULT=(\S+)\s*$", lib.read_text(encoding="utf-8"), re.M)
    if match is None:
        raise SystemExit(f"{lib} does not assign SAEA_DATA_ROOT_DEFAULT")
    return match.group(1)


def _data_root_env() -> str:
    return os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or _authority_default()

SCHEMA_SMOKE = "saea-slurp-system-thinking-core-read-smoke-v1"
SCHEMA_READ = "saea-slurp-system-thinking-core-read-v1"
VERDICT_WORDS = ("TRANSFERS-ABOVE-BAR", "PARTIAL", "NO-TRANSFER", "HARM")
BAR_PP = base.BAR_PP
INTENT_GUARD_PP = 0.65
ROLES = ("perception", "solver")
INTENT_FIELD, SLU_GROUPS, SCORER = base.INTENT_FIELD, base.SLU_GROUPS, base.SCORER
ReadError = base.ReadError
CONTACTS_ZERO = base.CONTACTS_ZERO


# --------------------------------------------------------------------------- per-node contacts (text reduced to booleans and counts)


def wire_flags(wire: Mapping, budget_message: str) -> dict:
    """Booleans and counts from one preserved wire response; no text is returned."""

    choice = (wire.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content = message.get("content")
    content_flags = base.text_flags(content)
    # Decision 286: new traces carry the stored projection ``message.reasoning`` (hash and statistics, no bytes). Traces sealed before
    # it (immutable) still carry ``reasoning_content``; read those the old way.
    stats = message.get("reasoning")
    reasoning = message.get("reasoning_content")
    if isinstance(stats, Mapping):
        chars, forced = int(stats.get("reasoning_chars") or 0), bool(stats.get("forced_close"))
    else:
        chars = len(reasoning) if isinstance(reasoning, str) else 0
        forced = bool(isinstance(reasoning, str) and budget_message and budget_message in reasoning)
    return {
        "finish_reason": choice.get("finish_reason"),
        "empty_content": content_flags["empty"], "no_json_object": content_flags["no_object"], "marker_in_content": content_flags["leak"],
        "reasoning_chars": chars,
        "forced_close": forced,
    }


def node_contacts(trace: Path, budget_message: str = fam.THINK_BUDGET_MESSAGE) -> list[dict]:
    """One record per model contact: its node (``use_role_id``), COST tokens and latency, and the wire flags. Joined by the flight key
    ``record_id.split('/')[0]`` exactly as ``stage3_wave_beside_read.role_tokens`` does."""

    role: dict[str, str] = {}
    cost: dict[str, dict] = {}
    wire: dict[str, dict] = {}
    with Path(trace).open("rb") as handle:
        for raw in handle:
            head = raw[:40]
            if b'"USE"' not in head and b'"COST"' not in head and b'"MODEL_WIRE_RESPONSE"' not in head:
                continue
            record = json.loads(raw)
            channel, key = record.get("channel"), str(record.get("record_id", "")).split("/", 1)[0]
            payload = record.get("payload") or {}
            if channel == "USE" and "use_role_id" in payload:
                role[key] = str(payload["use_role_id"])
            elif channel == "COST":
                cost[key] = {"prompt_tokens": int(payload.get("prompt_tokens") or 0), "completion_tokens": int(payload.get("completion_tokens") or 0),
                             "latency_seconds": float(payload.get("latency_seconds") or 0.0)}
            elif channel == "MODEL_WIRE_RESPONSE":
                wire[key] = wire_flags(json.loads(base64.b64decode(payload["response_b64"])), budget_message)
    return [{"node": role.get(key, "unattributed"), **value, **wire.get(key, {"finish_reason": None, "empty_content": None, "no_json_object": None,
                                                                              "marker_in_content": None, "reasoning_chars": None, "forced_close": None})}
            for key, value in sorted(cost.items())]


def node_table(contacts: Sequence[Mapping], *, cap: int = fam.THINK_MAX_TOKENS, rows: int = fam.ROWS, slots: int = fam.THINK_SLOTS) -> dict:
    """The cap-hit / empty-completion / parse-failure table and the cost per contact, per NODE (Perception vs Solver)."""

    groups: dict[str, list[Mapping]] = defaultdict(list)
    for contact in contacts:
        groups[str(contact["node"])].append(contact)
    table: dict[str, dict] = {}
    for node, items in sorted(groups.items()):
        n = len(items)
        tokens = [int(c["completion_tokens"]) for c in items]
        seconds = [float(c["latency_seconds"]) for c in items]
        wired = [c for c in items if c.get("empty_content") is not None]
        mean_s = sum(seconds) / n if n else float("nan")
        table[node] = {
            "contacts": n, "cap": cap,
            "cap_hits": sum(1 for t in tokens if t >= cap), "finish_reason_length": sum(1 for c in wired if c.get("finish_reason") == "length"),
            "empty_content": sum(1 for c in wired if c["empty_content"]), "no_json_object": sum(1 for c in wired if c["no_json_object"]),
            "marker_in_content": sum(1 for c in wired if c["marker_in_content"]),
            "forced_closes": sum(1 for c in wired if c["forced_close"]), "wire_records": len(wired),
            "finish_reasons": dict(sorted(Counter(str(c.get("finish_reason")) for c in wired).items())),
            "completion_tokens": {"mean": sum(tokens) / n if n else float("nan"), "p50": base.percentile(tokens, 50), "p90": base.percentile(tokens, 90),
                                  "p99": base.percentile(tokens, 99), "max": max(tokens) if tokens else float("nan")},
            "prompt_tokens_mean": sum(int(c["prompt_tokens"]) for c in items) / n if n else float("nan"),
            "seconds_per_contact": {"mean": mean_s, "p50": base.percentile(seconds, 50), "p99": base.percentile(seconds, 99)},
            "slot_normalised_gpu_hours_per_pass": rows * mean_s / slots / 3600.0 if n else float("nan"),
        }
    return table


def smoke_stage(contacts: Sequence[Mapping], *, rows: int = fam.ROWS) -> dict:
    return {"schema": SCHEMA_SMOKE, "status": "DECODE-COST PER NODE (no score, no read)", "nodes": node_table(contacts, rows=rows),
            "projection": {"rows": rows, "per_pass_gpu_hours_by_node_sum": sum(v["slot_normalised_gpu_hours_per_pass"] for v in node_table(contacts, rows=rows).values()),
                           "registered_plan_gpu_hours_per_arm": fam.CELLS["lock"]["gpu_hours"]},
            "contacts": CONTACTS_ZERO}


# --------------------------------------------------------------------------- the contrasts


def _pooled(rows: Mapping[str, Mapping[str, float]], ids: Sequence[str]) -> float:
    return base._pooled(rows, ids)


def _intent(rows: Mapping[str, Mapping[str, float]], ids: Sequence[str]) -> float:
    return base._mean_field(rows, ids, INTENT_FIELD)


def paired_contrasts(arms: Mapping[str, Mapping[str, Mapping[str, float]]], ids: Sequence[str], cluster_of: Callable[[str], str], *, seed: int, draws: int) -> dict:
    """arms = {'lock', 'aa', 'inst', 'bare'} per-row score tables over the same ids."""

    lock, aa, inst, bare = arms["lock"], arms["aa"], arms["inst"], arms["bare"]

    def run(statistic: Callable[[Sequence[str]], float]) -> dict:
        result = resampled_statistic(sample_ids=list(ids), statistic=statistic, seed=seed, n_replicates=draws, ci_level=0.95, cluster_of=cluster_of)
        return base.interval(result.replicates, result.point_estimate)

    def sht(left: Mapping, right: Mapping) -> dict:
        saves = sum(1 for i in ids if right[i][INTENT_FIELD] > left[i][INTENT_FIELD])
        harms = sum(1 for i in ids if right[i][INTENT_FIELD] < left[i][INTENT_FIELD])
        return {"saves": saves, "harms": harms, "ties": len(ids) - saves - harms}

    slu = {
        "inst_pct": 100 * _pooled(inst, ids), "bare_pct": 100 * _pooled(bare, ids), "lock_pct": 100 * _pooled(lock, ids), "aa_pct": 100 * _pooled(aa, ids),
        "d_system_lock_vs_inst": run(lambda r: _pooled(lock, r) - _pooled(inst, r)),
        "o_twin_aa_vs_lock": run(lambda r: _pooled(aa, r) - _pooled(lock, r)),
        "d_vs_bare_lock_vs_bare": run(lambda r: _pooled(lock, r) - _pooled(bare, r)),
    }
    intent = {
        "inst_pct": 100 * _intent(inst, ids), "bare_pct": 100 * _intent(bare, ids), "lock_pct": 100 * _intent(lock, ids), "aa_pct": 100 * _intent(aa, ids),
        "d_system_lock_vs_inst": run(lambda r: _intent(lock, r) - _intent(inst, r)),
        "o_twin_aa_vs_lock": run(lambda r: _intent(aa, r) - _intent(lock, r)),
        "d_vs_bare_lock_vs_bare": run(lambda r: _intent(lock, r) - _intent(bare, r)),
        "saves_harms_ties": {"lock_vs_inst": sht(inst, lock), "aa_vs_lock": sht(lock, aa), "lock_vs_bare": sht(bare, lock)},
    }
    d = slu["d_system_lock_vs_inst"]["point_pp"]
    slu["transfer_share_of_bare_delta"] = {"d_system_pp": d, "bare_delta_pp": fam.BARE_DELTA_SLU_PP, "share": d / fam.BARE_DELTA_SLU_PP}
    return {"slu_f1": slu, "intent": intent, "n": len(ids)}


def per_scenario_table(arms: Mapping[str, Mapping[str, Mapping[str, float]]], ids: Sequence[str], scenario_of: Callable[[str], str]) -> dict:
    groups: dict[str, list[str]] = defaultdict(list)
    for sid in ids:
        groups[scenario_of(sid)].append(sid)
    table: dict[str, dict] = {}
    for name, members in sorted(groups.items()):
        entry: dict = {"n": len(members)}
        for key in ("inst", "bare", "lock", "aa"):
            entry[f"slu_{key}_pct"] = 100 * _pooled(arms[key], members)
            entry[f"intent_{key}_pct"] = 100 * _intent(arms[key], members)
        entry["slu_d_system_pp"] = entry["slu_lock_pct"] - entry["slu_inst_pct"]
        entry["intent_d_system_pp"] = entry["intent_lock_pct"] - entry["intent_inst_pct"]
        entry["slu_d_vs_bare_pp"] = entry["slu_lock_pct"] - entry["slu_bare_pct"]
        table[name] = entry
    scenarios = list(table.values())
    keys = ("slu_d_system_pp", "intent_d_system_pp", "slu_d_vs_bare_pp")
    equal = {k: sum(e[k] for e in scenarios) / len(scenarios) for k in keys} if scenarios else {}
    natural = {"slu_d_system_pp": 100 * (_pooled(arms["lock"], ids) - _pooled(arms["inst"], ids)),
               "intent_d_system_pp": 100 * (_intent(arms["lock"], ids) - _intent(arms["inst"], ids)),
               "slu_d_vs_bare_pp": 100 * (_pooled(arms["lock"], ids) - _pooled(arms["bare"], ids))}
    return {"scenarios": table, "natural_mixture": natural, "equal_scenario": equal}


def verdict(contrast: Mapping, marker_total: int, bar_pp: float = BAR_PP, guard_pp: float = INTENT_GUARD_PP) -> str:
    slu, intent = contrast["slu_f1"], contrast["intent"]
    d, o = slu["d_system_lock_vs_inst"], slu["o_twin_aa_vs_lock"]
    margin = abs(o["point_pp"])
    guard_ok = intent["d_system_lock_vs_inst"]["ci95_lo_pp"] >= -guard_pp
    if d["point_pp"] <= -bar_pp and d["ci95_hi_pp"] < -margin:
        return "HARM"
    if d["point_pp"] >= bar_pp and d["ci95_lo_pp"] > margin and guard_ok and marker_total == 0:
        return "TRANSFERS-ABOVE-BAR"
    if d["ci95_lo_pp"] > margin:
        return "PARTIAL"
    return "NO-TRANSFER"


#: Owner decision 299 A (2026-10-12): the P3 trigger that decides whether the engineering base is rebuilt around the Thinking core.
#: Three conditions on the lock-vs-Instruct contrast and the Thinking lock arm's contacts: SLU CI95 lower bound above the twin
#: offset AND point >= P3_SLU_POINT_PP; intent CI95 lower bound >= -INTENT_GUARD_PP; completion rate (contacts that neither hit
#: the cap nor returned empty content) >= P3_COMPLETION_RATE. Three of three -> REBUILD-BASE-ON-THINKING; two -> THINKING-ON-SLURP-ONLY
#: (carriers stay on Instruct, plus one DEV replicate); otherwise STAY-ON-INSTRUCT. A development reading, never a benefit claim: the
#: benefit bar of the registered verdict stays BAR_PP (cross-flight, decision 190 instrument).
P3_SLU_POINT_PP = 1.5
P3_COMPLETION_RATE = 0.99


def p3_trigger(contrast: Mapping, lock_nodes: Mapping[str, Mapping], *, slu_point_pp: float = P3_SLU_POINT_PP,
               guard_pp: float = INTENT_GUARD_PP, completion_rate: float = P3_COMPLETION_RATE) -> dict:
    """Decision 299 A: the three conditions, each reported, and the resulting direction word."""
    slu, intent = contrast["slu_f1"], contrast["intent"]
    d, o = slu["d_system_lock_vs_inst"], slu["o_twin_aa_vs_lock"]
    contacts = sum(int(n.get("contacts") or 0) for n in lock_nodes.values())
    incomplete = sum(int(n.get("cap_hits") or 0) + int(n.get("empty_content") or 0) for n in lock_nodes.values())
    rate = (contacts - incomplete) / contacts if contacts else float("nan")
    conditions = {
        "slu_resolved_and_above_point": bool(d["ci95_lo_pp"] > abs(o["point_pp"]) and d["point_pp"] >= slu_point_pp),
        "intent_guard": bool(intent["d_system_lock_vs_inst"]["ci95_lo_pp"] >= -guard_pp),
        "completion_rate": bool(contacts and rate >= completion_rate),
    }
    met = sum(conditions.values())
    direction = "REBUILD-BASE-ON-THINKING" if met == 3 else ("THINKING-ON-SLURP-ONLY" if met == 2 else "STAY-ON-INSTRUCT")
    return {"decision": "299 A (owner 2026-10-12)", "conditions": conditions, "met": met, "direction": direction,
            "slu_point_pp": d["point_pp"], "slu_ci95_lo_pp": d["ci95_lo_pp"], "twin_offset_abs_pp": abs(o["point_pp"]),
            "intent_ci95_lo_pp": intent["d_system_lock_vs_inst"]["ci95_lo_pp"], "lock_contacts": contacts,
            "lock_incomplete_contacts": incomplete, "lock_completion_rate": rate,
            "thresholds": {"slu_point_pp": slu_point_pp, "intent_guard_pp": guard_pp, "completion_rate": completion_rate},
            "note": "development reading on TRAIN Fold B; never a benefit claim (the benefit bar stays bar_pp)"}


def read_stage(arms: Mapping[str, Mapping[str, Mapping[str, float]]], ids: Sequence[str], cluster_of: Callable[[str], str], scenario_of: Callable[[str], str],
               flags: Mapping[str, Mapping[str, Mapping]], contacts_by_arm: Mapping[str, Sequence[Mapping]], *,
               seed: int = base.DEFAULT_SEED, draws: int = base.DEFAULT_DRAWS) -> dict:
    contrast = paired_contrasts(arms, ids, cluster_of, seed=seed, draws=draws)
    delivered = {key: base.flag_counts(flags[key]) for key in sorted(flags)}
    contacts = [c for key in contacts_by_arm for c in contacts_by_arm[key]]
    markers = sum(v["reasoning_leak"] for v in delivered.values()) + sum(1 for c in contacts if c.get("marker_in_content"))
    return {
        "schema": SCHEMA_READ, "status": "PREREGISTERED-READ (development numbers; never a test claim; claims_benefit false)",
        "verdict": verdict(contrast, markers), "verdict_words": list(VERDICT_WORDS), "bar_pp": BAR_PP, "intent_guard_pp": INTENT_GUARD_PP,
        "interval": {"kind": "utterance-cluster bootstrap", "draws": draws, "seed": seed, "level": "CI95"},
        "contrast": contrast, "per_scenario": per_scenario_table(arms, ids, scenario_of),
        "nodes_by_arm": {key: node_table(contacts_by_arm[key]) for key in sorted(contacts_by_arm)},
        "p3_trigger_299": p3_trigger(contrast, node_table(contacts_by_arm.get("lock", []))),
        "delivered_content": delivered, "reasoning_marker_total": markers,
        "scorer_parse_failures": {key: sum(1 for row in arms[key].values() if row.get("parsed", 1.0) == 0.0) for key in sorted(arms)},
        "contacts": CONTACTS_ZERO,
    }


def render_markdown(result: Mapping) -> str:
    lines = [f"# 268-B read -- verdict {result.get('verdict', 'n/a')}", ""]
    p3 = result.get("p3_trigger_299")
    if p3:
        lines += [f"Decision 299 A direction: **{p3['direction']}** ({p3['met']}/3 conditions: "
                  + ", ".join(f"{k}={'yes' if v else 'no'}" for k, v in p3["conditions"].items())
                  + f"; SLU {p3['slu_point_pp']:+.2f} pp, CI-lo {p3['slu_ci95_lo_pp']:+.2f} vs twin offset {p3['twin_offset_abs_pp']:.2f}; "
                  + f"intent CI-lo {p3['intent_ci95_lo_pp']:+.2f}; completion {p3['lock_completion_rate']:.4f} over {p3['lock_contacts']} contacts)", ""]
    c = result.get("contrast")
    if c:
        s, i = c["slu_f1"], c["intent"]
        lines += ["| metric | Instruct lock (i3) | bare Thinking | Thinking system | twin | d_system (pp) | CI95 | twin offset (pp) | vs bare (pp) |",
                  "| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |"]
        for name, block in (("SLU-F1", s), ("intent", i)):
            d, o, b = block["d_system_lock_vs_inst"], block["o_twin_aa_vs_lock"], block["d_vs_bare_lock_vs_bare"]
            lines.append(f"| {name} | {block['inst_pct']:.2f} | {block['bare_pct']:.2f} | {block['lock_pct']:.2f} | {block['aa_pct']:.2f} | {d['point_pp']:+.2f} | "
                         f"[{d['ci95_lo_pp']:+.2f}, {d['ci95_hi_pp']:+.2f}] | {o['point_pp']:+.2f} | {b['point_pp']:+.2f} |")
        share = s["transfer_share_of_bare_delta"]
        lines += ["", f"Transfer share of the bare 266-E delta (+{share['bare_delta_pp']:.2f} pp): {100 * share['share']:.1f} %.", ""]
    sc = result.get("per_scenario")
    if sc:
        lines += ["| scenario | n | SLU d_system (pp) | intent d_system (pp) | SLU vs bare (pp) |", "| --- | ---: | ---: | ---: | ---: |"]
        for name, e in sc["scenarios"].items():
            lines.append(f"| {name} | {e['n']} | {e['slu_d_system_pp']:+.2f} | {e['intent_d_system_pp']:+.2f} | {e['slu_d_vs_bare_pp']:+.2f} |")
        nat, eq = sc["natural_mixture"], sc["equal_scenario"]
        lines += [f"| natural mixture | | {nat['slu_d_system_pp']:+.2f} | {nat['intent_d_system_pp']:+.2f} | {nat['slu_d_vs_bare_pp']:+.2f} |",
                  f"| equal scenario | | {eq.get('slu_d_system_pp', float('nan')):+.2f} | {eq.get('intent_d_system_pp', float('nan')):+.2f} | {eq.get('slu_d_vs_bare_pp', float('nan')):+.2f} |", ""]
    for arm, nodes in sorted((result.get("nodes_by_arm") or {}).items()):
        lines += [f"Nodes of `{arm}`:", "", "| node | contacts | cap hits | length finishes | empty | no JSON | forced closes | tokens p50 / p99 | s per contact |",
                  "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |"]
        for node, t in nodes.items():
            lines.append(f"| {node} | {t['contacts']} | {t['cap_hits']} | {t['finish_reason_length']} | {t['empty_content']} | {t['no_json_object']} | "
                         f"{t['forced_closes']} | {t['completion_tokens']['p50']:.0f} / {t['completion_tokens']['p99']:.0f} | {t['seconds_per_contact']['mean']:.2f} |")
        lines.append("")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- the sealed-run adapter and the CLI


def load_scored(data_root: Path, run_id: str, attempt_id: str) -> dict:
    """Per-row official scores and the delivered-content flags of a COMPLETED sealed run (no trace)."""

    paths = base.run_paths(data_root, run_id, attempt_id)
    for name in ("outputs", "scores", "manifest"):
        if not paths[name].exists():
            raise ReadError(f"{run_id}: missing sealed file {paths[name]}")
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    if str(manifest.get("status", "")).upper() != "COMPLETED":
        raise ReadError(f"{run_id}: run manifest status is {manifest.get('status')!r}, not COMPLETED")
    return {"rows": base.rows_table(json.loads(paths["scores"].read_text(encoding="utf-8")), SCORER), "flags": base.load_output_flags(paths["outputs"]),
            "hashes": {n: base.sha256_file(paths[n]) for n in ("outputs", "scores", "manifest")}}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("smoke", "read"), required=True)
    parser.add_argument("--data-root", type=Path, default=Path(_data_root_env()))
    parser.add_argument("--repo-root", type=Path, default=_REPO)
    parser.add_argument("--analysis-root", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=base.DEFAULT_SEED)
    parser.add_argument("--draws", type=int, default=base.DEFAULT_DRAWS)
    args = parser.parse_args(argv)
    root = args.analysis_root or (args.data_root / "analysis" / fam.READ_RUN_ID)
    root.mkdir(parents=True, exist_ok=True)
    cells = fam.CELLS
    try:
        if args.stage == "smoke":
            trace = base.run_paths(args.data_root, cells["smoke"]["run"], cells["smoke"]["attempt"])["trace"]
            if not trace.exists():
                raise ReadError(f"missing sealed trace {trace}")
            result = smoke_stage(node_contacts(trace))
            result["sealed_trace_sha256"] = base.sha256_file(trace)
            out = root / "smoke-decode-cost.json"
        else:
            loaded = {key: load_scored(args.data_root, cells[key]["run"], cells[key]["attempt"]) for key in fam.ARM_KEYS}
            loaded["inst"] = load_scored(args.data_root, fam.COMPARATOR_COLUMN, fam.COMPARATOR_ATTEMPT)
            loaded["bare"] = load_scored(args.data_root, fam.BARE_THINKING_RUN, fam.BARE_THINKING_ATTEMPT)
            ids, cluster_of, scenario_of = base.roster_maps(args.repo_root / fam.ROSTER["arm"])
            for key, arm in loaded.items():
                if set(arm["rows"]) != set(ids):
                    raise ReadError(f"{key}: the per-sample id set is not the frozen Fold B roster's")
            contacts_by_arm = {}
            for key in fam.ARM_KEYS:
                trace = base.run_paths(args.data_root, cells[key]["run"], cells[key]["attempt"])["trace"]
                contacts_by_arm[key] = node_contacts(trace)
                loaded[key]["hashes"]["trace"] = base.sha256_file(trace)
            result = read_stage({k: loaded[k]["rows"] for k in loaded}, ids, cluster_of, scenario_of, {k: loaded[k]["flags"] for k in loaded},
                                contacts_by_arm, seed=args.seed, draws=args.draws)
            result["sealed_hashes"] = {k: loaded[k]["hashes"] for k in sorted(loaded)}
            out = root / "read.json"
    except ReadError as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 2
    if out.exists():
        print(f"REFUSED: {out} exists (write-once)", file=sys.stderr)
        return 6
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / ("smoke-decode-cost.md" if args.stage == "smoke" else "README.md")).write_text(render_markdown(result) if args.stage == "read" else
                                                                                           json.dumps(result.get("nodes"), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"written": str(out), "verdict": result.get("verdict")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
