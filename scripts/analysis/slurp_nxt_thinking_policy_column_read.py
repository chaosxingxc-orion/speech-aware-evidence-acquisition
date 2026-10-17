#!/usr/bin/env python3
"""slurp_nxt_thinking_policy_column_read.py -- the preregistered READ of NX-T R1 (the per-node thinking-policy column on the Thinking core, TRAIN Fold B).

Package ``docs/readiness/2026-10-13-slurp-nxt-r1-thinking-policy-fold-b-v1/``. A sealed run whose Perception node carries ``thinking_variants`` (receipt
``saea-perception-branch-arms-v5``, level 2) holds, per row, five Perception notes and five first-visit Solver answers: ``perception-off`` / ``solver-off`` /
``both-off`` (candidates), ``both-on-twin`` (the in-flight A/A) and ``both-on`` (the delivering arm, the 268-B lock form). Two stages:

  columns  (run first, by ``scripts/flights/nx/nxt_r1_read.sh columns``) the OFFICIAL per-arm scoring: ``stage3_rollout_score.py --mode
           perception-branches`` renders each arm's first Solver answer and scores it once, complete, with the registered official scorer.
  smoke    the four-row smoke: per ARM and per NODE decode cost from the sealed trace (completion tokens, finish reasons, cap hits, empty
           completions, forced closes, reasoning characters, seconds) -- including whether a no-think arm still emits reasoning bytes or a think
           marker. Nothing is scored; the coordinator reads it to sign off the column flight.
  read     the full read over the sealed, column-scored run, PAIRED per row against the delivering ``both-on`` arm (utterance-cluster bootstrap,
           10,000 draws, seed 20261013): official SLU-F1 (primary) and intent accuracy (scenario_action exact) levels per arm; each candidate arm and the
           twin minus ``both-on`` with CI95; saves/harms/ties of intent; the per-scenario table (natural and equal weightings); the per-arm per-node
           token / finish-reason / cap-hit / empty / forced-close / reasoning-marker tables; seconds per contact; and the THROUGHPUT table (rows per
           minute at the flight's own measured seconds per row, and each arm's cost in full both-on rows against the registered cost mix).

Node words (preregistered; development numbers only; claims_benefit is false -- an attribution, never an admission). The in-flight twin offset o is
``both-on-twin`` minus ``both-on`` (SLU). For each candidate arm X with SLU delta d and CI95 [lo, hi]:
  NEEDS-THINKING            hi < -|o|                (turning thinking off at that node resolves a loss beyond the A/A offset)
  NO-RESOLVED-LOSS          otherwise, with the extra word NOT-NEEDED-AT-THE-FLOOR when lo >= -1.49 pp (SLU floor) and the intent delta CI95 lo >= -0.65 pp
                            (intent floor): the loss, if any, is inside the design's own resolution (decision 190 node-column floors)
  GAIN                      lo > |o|                 (turning thinking off RAISES the score beyond the A/A offset)
The external reference for the twin offset is the 268-B cross-flight twin offset (+1.15 SLU, -0.09 intent); it is reported beside, never used in a word.

Model-free. Every sealed byte is opened read-only. NO utterance text, transcript, gold label, model output or reasoning text is printed or persisted:
contact text is reduced to booleans and counts at read time and dropped.

    python -B scripts/analysis/slurp_nxt_thinking_policy_column_read.py --stage smoke --data-root $SPEECHRL_DATA_DIR
    python -B scripts/analysis/slurp_nxt_thinking_policy_column_read.py --stage read  --data-root $SPEECHRL_DATA_DIR
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Callable, Mapping, Sequence

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parents[1]
for _path in (str(_REPO / "src"), str(_HERE), str(_REPO / "scripts" / "flights" / "nx"), str(_REPO / "scripts" / "flights" / "direct"),
              str(_REPO / "scripts" / "flights" / "tfrl")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import nxt_r1_family as fam  # noqa: E402
import slurp_direct_fold_b_core_read as base  # noqa: E402
import slurp_system_thinking_core_read as sysread  # noqa: E402

from speech_aware_evidence_acquisition.analysis.paired import resampled_statistic  # noqa: E402


def _authority_default() -> str:
    lib = Path(__file__).resolve().parents[1] / "lib" / "data_root.sh"
    match = re.search(r"^SAEA_DATA_ROOT_DEFAULT=(\S+)\s*$", lib.read_text(encoding="utf-8"), re.M)
    if match is None:
        raise SystemExit(f"{lib} does not assign SAEA_DATA_ROOT_DEFAULT")
    return match.group(1)


def _data_root_env() -> str:
    return os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or _authority_default()


SCHEMA_SMOKE = "saea-nxt-r1-thinking-policy-column-smoke-v1"
SCHEMA_READ = "saea-nxt-r1-thinking-policy-column-read-v1"
NODE_WORDS = ("NEEDS-THINKING", "NO-RESOLVED-LOSS", "GAIN")
EXTRA_WORD = "NOT-NEEDED-AT-THE-FLOOR"
SEED = 20261013
DRAWS = base.DEFAULT_DRAWS
INTENT_FIELD, SLU_GROUPS, SCORER = base.INTENT_FIELD, base.SLU_GROUPS, base.SCORER
ReadError = base.ReadError
CONTACTS_ZERO = base.CONTACTS_ZERO
ARMS = fam.ARM_ORDER
DELIVERING, TWIN, CANDIDATES = fam.DELIVERING, fam.TWIN, fam.CANDIDATE_ARMS
NODES = ("perception", "solver")
#: arm -> node -> True when the arm's policy turns that node's thinking OFF (the rest think at the locked form).
NO_THINK = {arm: {node: bool(fam.POLICIES.get(arm, {}).get(node, {}).get("enable_thinking") is False) for node in NODES} for arm in ARMS}
THINK_CAP, NO_THINK_CAP = fam.tsf.THINK_MAX_TOKENS, fam.tsf.THINK_ANSWER_RESERVE_TOKENS
SLOTS = fam.THINK_SLOTS
COLUMN_SCORE_NAME = "arm-{arm}-{scorer}-scores.json"


# --------------------------------------------------------------------------- the sealed row -> arm -> contact map (ids only)


def arm_contact_map(outputs_rows: Sequence[Mapping]) -> dict[str, tuple[str, str]]:
    """``{agent_contact_id: (arm, node)}`` from the v5 receipts of the sealed rows: each branch row names its Perception contact and its Solver contact."""

    mapping: dict[str, tuple[str, str]] = {}
    for row in outputs_rows:
        receipt = ((row.get("native_episode_receipt") or {}).get("perception_branches") or {})
        for branch in receipt.get("branches") or []:
            arm = str(branch.get("branch_id"))
            if branch.get("contact_id"):
                mapping[str(branch["contact_id"])] = (arm, "perception")
            if branch.get("solver_contact_id"):
                mapping[str(branch["solver_contact_id"])] = (arm, "solver")
    return mapping


def load_outputs_rows(path: Path) -> list[dict]:
    """The sealed outputs reduced to what the map needs: the sample id and the native episode receipt's branch ids (the delivered text is dropped)."""

    rows: list[dict] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            branches = (((row.get("native_episode_receipt") or {}).get("perception_branches") or {}).get("branches")) or []
            rows.append({"sample_id": str(row["sample_id"]), "native_episode_receipt": {"perception_branches": {"branches": [
                {k: b.get(k) for k in ("branch_id", "contact_id", "solver_contact_id", "thinking_policy", "solver_absent", "absent_reason")} for b in branches]}}})
            row.clear()
    return rows


def trace_contacts(trace: Path, budget_message: str = fam.tsf.THINK_BUDGET_MESSAGE) -> list[dict]:
    """One record per model request: its agent contact id and node (USE channel), COST tokens and latency, and the wire flags (booleans and counts only)."""

    agent: dict[str, str] = {}
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
            if channel == "USE" and "use_agent_contact_id" in payload:
                agent[key] = str(payload["use_agent_contact_id"])
                role[key] = str(payload.get("use_role_id", ""))
            elif channel == "COST":
                cost[key] = {"prompt_tokens": int(payload.get("prompt_tokens") or 0), "completion_tokens": int(payload.get("completion_tokens") or 0),
                             "latency_seconds": float(payload.get("latency_seconds") or 0.0)}
            elif channel == "MODEL_WIRE_RESPONSE":
                wire[key] = sysread.wire_flags(json.loads(base64.b64decode(payload["response_b64"])), budget_message)
    empty_wire = {"finish_reason": None, "empty_content": None, "no_json_object": None, "marker_in_content": None, "reasoning_chars": None, "forced_close": None}
    return [{"agent_contact_id": agent.get(key), "role": role.get(key), **value, **wire.get(key, empty_wire)} for key, value in sorted(cost.items())]


def attribute(contacts: Sequence[Mapping], mapping: Mapping[str, tuple[str, str]]) -> dict[str, list[dict]]:
    """Contacts grouped by arm, each tagged with its node. A contact the receipts do not name is counted under ``unattributed``."""

    out: dict[str, list[dict]] = defaultdict(list)
    for contact in contacts:
        arm, node = mapping.get(str(contact.get("agent_contact_id")), ("unattributed", str(contact.get("role") or "unattributed")))
        out[arm].append({**contact, "node": node})
    return dict(out)


def arm_node_table(contacts: Sequence[Mapping], arm: str, *, slots: int = SLOTS) -> dict:
    """The per-node completion / finish-reason / cap-hit / empty / forced-close / reasoning-marker table of ONE arm. The cap of a node is 1,024 when the arm
    turns its thinking off and 4,096 otherwise; a no-think contact that still returns reasoning characters or a think marker is counted explicitly."""

    groups: dict[str, list[Mapping]] = defaultdict(list)
    for contact in contacts:
        groups[str(contact["node"])].append(contact)
    table: dict[str, dict] = {}
    for node, items in sorted(groups.items()):
        n = len(items)
        no_think = bool(NO_THINK.get(arm, {}).get(node, False))
        cap = NO_THINK_CAP if no_think else THINK_CAP
        tokens = [int(c["completion_tokens"]) for c in items]
        seconds = [float(c["latency_seconds"]) for c in items]
        wired = [c for c in items if c.get("empty_content") is not None]
        table[node] = {
            "contacts": n, "mode": "no-think" if no_think else "think", "cap": cap,
            "cap_hits": sum(1 for t in tokens if t >= cap),
            "finish_reasons": dict(sorted(Counter(str(c.get("finish_reason")) for c in wired).items())),
            "finish_reason_length": sum(1 for c in wired if c.get("finish_reason") == "length"),
            "empty_content": sum(1 for c in wired if c["empty_content"]), "no_json_object": sum(1 for c in wired if c["no_json_object"]),
            "marker_in_content": sum(1 for c in wired if c["marker_in_content"]),
            "forced_closes": sum(1 for c in wired if c["forced_close"]),
            "contacts_with_reasoning_chars": sum(1 for c in wired if (c.get("reasoning_chars") or 0) > 0),
            "reasoning_chars_mean": (sum(int(c.get("reasoning_chars") or 0) for c in wired) / len(wired)) if wired else float("nan"),
            "wire_records": len(wired),
            "completion_tokens": {"mean": sum(tokens) / n if n else float("nan"), "p50": base.percentile(tokens, 50), "p90": base.percentile(tokens, 90),
                                  "p99": base.percentile(tokens, 99), "max": max(tokens) if tokens else float("nan")},
            "prompt_tokens_mean": sum(int(c["prompt_tokens"]) for c in items) / n if n else float("nan"),
            "seconds_per_contact": {"mean": sum(seconds) / n if n else float("nan"), "p50": base.percentile(seconds, 50), "p99": base.percentile(seconds, 99)},
        }
    return table


def tables_by_arm(by_arm: Mapping[str, Sequence[Mapping]]) -> dict[str, dict]:
    return {arm: arm_node_table(by_arm[arm], arm) for arm in sorted(by_arm)}


def throughput_table(tables: Mapping[str, Mapping], rows: int, *, slots: int = SLOTS, delivering: str = DELIVERING) -> dict:
    """Seconds per row (the arm's Perception plus Solver mean contact seconds), rows per minute at ``slots`` slots, the slot-normalised GPU hours of a pass over
    ``rows`` rows, and the arm's cost in full ``both-on`` rows next to the registered mix (``nxt_r1_family.ROW_COST``). Measured seconds only."""

    seconds = {arm: sum(node["seconds_per_contact"]["mean"] for node in t.values()) for arm, t in tables.items() if arm != "unattributed"}
    ref = seconds.get(delivering)
    out: dict[str, dict] = {}
    for arm, per_row in sorted(seconds.items()):
        out[arm] = {
            "seconds_per_row": per_row, "rows_per_minute": slots * 60.0 / per_row if per_row else float("nan"),
            "gpu_hours_per_pass": rows * per_row / slots / 3600.0,
            "cost_in_both_on_rows": per_row / ref if ref else float("nan"), "registered_cost_in_rows": fam.ROW_COST.get(arm),
        }
    total = sum(v["cost_in_both_on_rows"] for v in out.values()) if ref else float("nan")
    return {"slots": slots, "arms": out, "arm_mix_measured_rows": total, "arm_mix_registered_rows": fam.ARM_MIX_ROWS,
            "registered_rows_per_minute_full": fam.ROWS_PER_MINUTE_FULL, "registered_gpu_hours_ceiling": fam.CELLS["arm"]["gpu_hours"],
            "measured_gpu_hours_one_flight": sum(v["gpu_hours_per_pass"] for v in out.values())}


def smoke_stage(by_arm: Mapping[str, Sequence[Mapping]], *, rows: int = fam.SMOKE_ROWS, absent: Mapping | None = None) -> dict:
    tables = tables_by_arm(by_arm)
    absent = absent if absent is not None else base.absent_solver_columns([], ARMS)
    no_think_leaks = {
        arm: {node: {"contacts_with_reasoning_chars": t["contacts_with_reasoning_chars"], "marker_in_content": t["marker_in_content"],
                     "empty_content": t["empty_content"], "finish_reasons": t["finish_reasons"]}
              for node, t in nodes.items() if t["mode"] == "no-think"} for arm, nodes in tables.items()}
    projection_rows = fam.ROWS
    return {"schema": SCHEMA_SMOKE, "status": "DECODE-COST PER ARM AND NODE (no score, no read)", "arms": tables,
            "no_think_nodes": {arm: v for arm, v in no_think_leaks.items() if v},
            "throughput": throughput_table(tables, projection_rows), "smoke_rows": rows,
            "absent_columns": absent["total"], "absent_rows_by_arm": dict(absent["by_arm"]),
            "unattributed_contacts": len(by_arm.get("unattributed", [])), "contacts": CONTACTS_ZERO}


# --------------------------------------------------------------------------- the paired contrasts


def _pooled(rows: Mapping[str, Mapping[str, float]], ids: Sequence[str]) -> float:
    return base._pooled(rows, ids)


def _intent(rows: Mapping[str, Mapping[str, float]], ids: Sequence[str]) -> float:
    return base._mean_field(rows, ids, INTENT_FIELD)


def paired_contrasts(arms: Mapping[str, Mapping[str, Mapping[str, float]]], ids: Sequence[str], cluster_of: Callable[[str], str], *,
                     seed: int = SEED, draws: int = DRAWS, delivering: str = DELIVERING) -> dict:
    """Every other arm (candidates and twin) minus the delivering arm, SLU-F1 and intent, utterance-cluster bootstrap; levels per arm."""

    ref = arms[delivering]

    def run(statistic: Callable[[Sequence[str]], float]) -> dict:
        result = resampled_statistic(sample_ids=list(ids), statistic=statistic, seed=seed, n_replicates=draws, ci_level=0.95, cluster_of=cluster_of)
        return base.interval(result.replicates, result.point_estimate)

    def sht(left: Mapping, right: Mapping) -> dict:
        saves = sum(1 for i in ids if right[i][INTENT_FIELD] > left[i][INTENT_FIELD])
        harms = sum(1 for i in ids if right[i][INTENT_FIELD] < left[i][INTENT_FIELD])
        return {"saves": saves, "harms": harms, "ties": len(ids) - saves - harms}

    levels = {arm: {"slu_f1_pct": 100 * _pooled(rows, ids), "intent_pct": 100 * _intent(rows, ids)} for arm, rows in arms.items()}
    versus: dict[str, dict] = {}
    for arm, rows in arms.items():
        if arm == delivering:
            continue
        versus[arm] = {
            "slu_f1": run(lambda r, rows=rows: _pooled(rows, r) - _pooled(ref, r)),
            "intent": run(lambda r, rows=rows: _intent(rows, r) - _intent(ref, r)),
            "intent_saves_harms_ties_vs_delivering": sht(ref, rows),
        }
    return {"n": len(ids), "delivering": delivering, "levels": levels, "versus_delivering": versus}


def node_words(contrast: Mapping, *, floor_slu_pp: float = fam.FLOOR_SLU_PP, floor_intent_pp: float = fam.FLOOR_INTENT_PP) -> dict:
    """The preregistered node words per candidate arm, judged against the in-flight twin offset (see the module docstring)."""

    versus = contrast["versus_delivering"]
    twin = versus.get(TWIN)
    offset = abs(twin["slu_f1"]["point_pp"]) if twin else 0.0
    words: dict[str, dict] = {}
    for arm in CANDIDATES:
        if arm not in versus:
            continue
        slu, intent = versus[arm]["slu_f1"], versus[arm]["intent"]
        if slu["ci95_hi_pp"] < -offset:
            word = "NEEDS-THINKING"
        elif slu["ci95_lo_pp"] > offset:
            word = "GAIN"
        else:
            word = "NO-RESOLVED-LOSS"
        extra = bool(word == "NO-RESOLVED-LOSS" and slu["ci95_lo_pp"] >= -floor_slu_pp and intent["ci95_lo_pp"] >= -floor_intent_pp)
        words[arm] = {"word": word, "extra_word": EXTRA_WORD if extra else None, "slu_delta_pp": slu["point_pp"], "slu_ci95": [slu["ci95_lo_pp"], slu["ci95_hi_pp"]],
                      "intent_delta_pp": intent["point_pp"], "intent_ci95": [intent["ci95_lo_pp"], intent["ci95_hi_pp"]],
                      "node": {"perception-off": "perception", "solver-off": "solver", "both-off": "both"}[arm]}
    return {"twin_offset_abs_pp": offset, "twin_offset_point_pp": twin["slu_f1"]["point_pp"] if twin else None,
            "external_reference_268b": {"twin_offset_slu_pp": fam.TWIN_OFFSET_268B_SLU_PP, "twin_offset_intent_pp": fam.TWIN_OFFSET_268B_INTENT_PP,
                                        "thinking_system_slu": fam.THINKING_SYSTEM_SLU, "thinking_system_intent": fam.THINKING_SYSTEM_INTENT,
                                        "instruct_system_slu": fam.INSTRUCT_SYSTEM_SLU, "instruct_system_intent": fam.INSTRUCT_SYSTEM_INTENT},
            "floors_pp": {"slu": floor_slu_pp, "intent": floor_intent_pp}, "words": words}


def per_scenario_table(arms: Mapping[str, Mapping[str, Mapping[str, float]]], ids: Sequence[str], scenario_of: Callable[[str], str],
                       delivering: str = DELIVERING) -> dict:
    groups: dict[str, list[str]] = defaultdict(list)
    for sid in ids:
        groups[scenario_of(sid)].append(sid)
    table: dict[str, dict] = {}
    for name, members in sorted(groups.items()):
        entry: dict = {"n": len(members)}
        for arm, rows in arms.items():
            entry[f"slu_{arm}_pct"] = 100 * _pooled(rows, members)
            entry[f"intent_{arm}_pct"] = 100 * _intent(rows, members)
        for arm in arms:
            if arm != delivering:
                entry[f"slu_d_{arm}_pp"] = entry[f"slu_{arm}_pct"] - entry[f"slu_{delivering}_pct"]
                entry[f"intent_d_{arm}_pp"] = entry[f"intent_{arm}_pct"] - entry[f"intent_{delivering}_pct"]
        table[name] = entry
    scenarios = list(table.values())
    others = [a for a in arms if a != delivering]
    equal = {f"slu_d_{a}_pp": sum(e[f"slu_d_{a}_pp"] for e in scenarios) / len(scenarios) for a in others} if scenarios else {}
    natural = {f"slu_d_{a}_pp": 100 * (_pooled(arms[a], ids) - _pooled(arms[delivering], ids)) for a in others}
    return {"scenarios": table, "natural_mixture": natural, "equal_scenario": equal}


def read_stage(arms: Mapping[str, Mapping[str, Mapping[str, float]]], ids: Sequence[str], cluster_of: Callable[[str], str], scenario_of: Callable[[str], str],
               by_arm: Mapping[str, Sequence[Mapping]], flags: Mapping[str, Mapping], *, seed: int = SEED, draws: int = DRAWS,
               absent: Mapping | None = None) -> dict:
    """The full read. ``absent`` (``base.absent_solver_columns``): a NON-delivering arm's absent Solver column is that arm's DELIVERY FAILURE -- scored as
    the canonical empty answer (zero for that row's arm in the paired contrast, proved here) and COUNTED per arm in ``absent_rows`` beside the table."""

    absent = absent if absent is not None else base.absent_solver_columns([], ARMS)
    base.require_absent_scored_zero(arms, absent)
    contrast = paired_contrasts(arms, ids, cluster_of, seed=seed, draws=draws)
    for arm, level in contrast["levels"].items():
        level["absent_rows"] = int(absent["by_arm"].get(arm, 0))
    tables = tables_by_arm(by_arm)
    delivered = base.flag_counts(flags)
    markers = delivered["reasoning_leak"] + sum(t["marker_in_content"] for nodes in tables.values() for t in nodes.values())
    return {
        "schema": SCHEMA_READ, "status": "PREREGISTERED-READ (development numbers; never a test claim; claims_benefit false)",
        "node_words": node_words(contrast), "node_words_vocabulary": list(NODE_WORDS), "extra_word": EXTRA_WORD,
        "interval": {"kind": "utterance-cluster bootstrap", "draws": draws, "seed": seed, "level": "CI95"},
        "contrast": contrast, "per_scenario": per_scenario_table(arms, ids, scenario_of),
        "arms_nodes": tables,
        "completion_and_finish_reasons": {arm: {node: {"finish_reasons": t["finish_reasons"], "completion_tokens_mean": t["completion_tokens"]["mean"],
                                                       "cap_hits": t["cap_hits"], "empty_content": t["empty_content"], "forced_closes": t["forced_closes"],
                                                       "contacts_with_reasoning_chars": t["contacts_with_reasoning_chars"], "marker_in_content": t["marker_in_content"],
                                                       "mode": t["mode"]}
                                              for node, t in nodes.items()} for arm, nodes in tables.items()},
        "throughput": throughput_table(tables, fam.ROWS), "delivered_content": delivered, "reasoning_marker_total": markers,
        "unattributed_contacts": len(by_arm.get("unattributed", [])),
        "absent_columns": absent["total"], "absent_rows_by_arm": dict(absent["by_arm"]), "absent_reasons": dict(absent["reasons"]),
        "scorer_parse_failures": {arm: sum(1 for row in rows.values() if row.get("parsed", 1.0) == 0.0) for arm, rows in sorted(arms.items())},
        "contacts": CONTACTS_ZERO,
    }


def sealonly_block(roster_doc: Mapping, resume_from: Mapping, manifest: Mapping | None = None) -> dict:
    """The seal-only completion's account, by COUNT: the complete rows the read runs at, the failing row(s) and the never-started rows the stopped attempt left
    (never scored, never in n), and -- when a sealed manifest is given -- proof that its predecessor block names the registered trace. Ids stay in the roster document."""

    block = {
        "rows": int(roster_doc["count"]), "parent_rows": int(roster_doc["parent_rows"]),
        "failed_rows": int((roster_doc.get("failed_rows") or {}).get("count", 0)),
        "never_started_rows": int((roster_doc.get("never_started_rows") or {}).get("count", 0)),
        "stopped_attempt": dict(roster_doc.get("stopped_attempt") or {}), "resume_from": dict(resume_from),
        "failed_rows_are": "delivery failures of the both-off arm's Solver contact (a finite completion), reported by count and not scored",
    }
    if block["rows"] + block["failed_rows"] + block["never_started_rows"] != block["parent_rows"]:
        raise ReadError("the seal-only roster document does not account for every parent row (complete + failed + never started)")
    if manifest is not None:
        predecessor = manifest.get("predecessor_attempt")
        recorded = predecessor.get("trace_sha256") if isinstance(predecessor, Mapping) else None
        if recorded != resume_from.get("trace_sha256"):
            raise ReadError(f"the sealed manifest's predecessor_attempt names trace {recorded!r}, not the registered {resume_from.get('trace_sha256')!r}")
    return block


def resume_block(manifest: Mapping, resume_from: Mapping, rows: int) -> dict:
    """The mode-A RESUME (rec2, owner ruling 320 B) account, by COUNT: the rows kept from the stopped attempt by trace replay and the rows the resume flew, with
    proof that the sealed manifest's predecessor block names the registered trace. The read is at the full roster (kept + flown); the split is reported, never used."""

    predecessor = manifest.get("predecessor_attempt")
    if not isinstance(predecessor, Mapping) or predecessor.get("trace_sha256") != resume_from.get("trace_sha256"):
        raise ReadError(f"the sealed manifest's predecessor_attempt does not name the registered trace {resume_from.get('trace_sha256')!r}")
    kept = len(predecessor.get("kept_sample_ids") or [])
    if kept == 0 or kept >= rows:
        raise ReadError(f"a resume that kept {kept} of {rows} rows is not the registered kept/flown split")
    return {"kept": kept, "flown": rows - kept, "rows": rows, "resume_from": dict(resume_from), "predecessor_counts": dict(predecessor.get("counts") or {}),
            "kept_sample_ids_sha256": predecessor.get("kept_sample_ids_sha256")}


def render_markdown(result: Mapping) -> str:
    lines = ["# NX-T R1 read -- the per-node thinking-policy column", ""]
    rs = result.get("resume")
    if rs:
        lines += [f"RESUME (rec2, mode A): n = {rs['rows']:,}; {rs['kept']:,} rows kept from the stopped attempt by trace replay and {rs['flown']} rows flown by the resume "
                  "(the split is reported only; kept and flown rows are never separated in a contrast). Absent columns are counted per arm below.", ""]
    so = result.get("sealonly")
    if so:
        lines += [f"SEAL-ONLY completion: n = {so['rows']:,} of {so['parent_rows']:,} registered rows (the rows the stopped attempt completed); {so['failed_rows']} failing row(s) and "
                  f"{so['never_started_rows']} never-started row(s) are reported by count and never scored.", ""]
    nw = result.get("node_words")
    if nw:
        lines += [f"In-flight twin offset |o| = {nw['twin_offset_abs_pp']:.2f} pp SLU (external 268-B reference {nw['external_reference_268b']['twin_offset_slu_pp']:+.2f}).", "",
                  "| arm | node | word | SLU d (pp) | SLU CI95 | intent d (pp) | intent CI95 |", "| --- | --- | --- | ---: | --- | ---: | --- |"]
        for arm, w in nw["words"].items():
            word = w["word"] + (f" / {w['extra_word']}" if w["extra_word"] else "")
            lines.append(f"| {arm} | {w['node']} | {word} | {w['slu_delta_pp']:+.2f} | [{w['slu_ci95'][0]:+.2f}, {w['slu_ci95'][1]:+.2f}] | "
                         f"{w['intent_delta_pp']:+.2f} | [{w['intent_ci95'][0]:+.2f}, {w['intent_ci95'][1]:+.2f}] |")
        lines.append("")
    c = result.get("contrast")
    if c:
        lines += ["| arm | SLU-F1 | intent | SLU d vs both-on (pp) | CI95 | intent d (pp) | CI95 | intent saves / harms | absent rows |", "| --- | ---: | ---: | ---: | --- | ---: | --- | --- | ---: |"]
        for arm, lv in c["levels"].items():
            v = c["versus_delivering"].get(arm)
            if v is None:
                lines.append(f"| {arm} (delivering) | {lv['slu_f1_pct']:.2f} | {lv['intent_pct']:.2f} | | | | | | {lv.get('absent_rows', 0)} |")
            else:
                s, i, t = v["slu_f1"], v["intent"], v["intent_saves_harms_ties_vs_delivering"]
                lines.append(f"| {arm} | {lv['slu_f1_pct']:.2f} | {lv['intent_pct']:.2f} | {s['point_pp']:+.2f} | [{s['ci95_lo_pp']:+.2f}, {s['ci95_hi_pp']:+.2f}] | "
                             f"{i['point_pp']:+.2f} | [{i['ci95_lo_pp']:+.2f}, {i['ci95_hi_pp']:+.2f}] | {t['saves']} / {t['harms']} | {lv.get('absent_rows', 0)} |")
        lines += ["", "An absent row is that arm's delivery failure (its Solver contact ended on a finite completion): scored as the canonical empty answer, zero for that row's arm, "
                  "and counted in the last column. The delivering arm's own column is never absent.", ""]
    for arm, nodes in sorted((result.get("arms_nodes") or {}).items()):
        lines += [f"Nodes of `{arm}`:", "", "| node | mode | contacts | cap | cap hits | length | empty | no JSON | forced | reasoning chars>0 | markers | tokens p50 / p99 | s per contact |",
                  "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |"]
        for node, t in nodes.items():
            lines.append(f"| {node} | {t['mode']} | {t['contacts']} | {t['cap']} | {t['cap_hits']} | {t['finish_reason_length']} | {t['empty_content']} | {t['no_json_object']} | "
                         f"{t['forced_closes']} | {t['contacts_with_reasoning_chars']} | {t['marker_in_content']} | {t['completion_tokens']['p50']:.0f} / "
                         f"{t['completion_tokens']['p99']:.0f} | {t['seconds_per_contact']['mean']:.2f} |")
        lines.append("")
    tp = result.get("throughput")
    if tp:
        lines += ["| arm | s per row | rows / min | cost in both-on rows | registered cost | GPU-h per pass |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
        for arm, v in tp["arms"].items():
            lines.append(f"| {arm} | {v['seconds_per_row']:.1f} | {v['rows_per_minute']:.2f} | {v['cost_in_both_on_rows']:.2f} | {v['registered_cost_in_rows']} | {v['gpu_hours_per_pass']:.2f} |")
        lines += ["", f"Arm mix measured {tp['arm_mix_measured_rows']:.2f} rows (registered {tp['arm_mix_registered_rows']}); one flight measured "
                  f"{tp['measured_gpu_hours_one_flight']:.2f} GPU-h (ceiling {tp['registered_gpu_hours_ceiling']}).", ""]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- the sealed-run adapter and the CLI


def load_column_rows(analysis_columns: Path, scorer_id: str = SCORER) -> dict[str, dict]:
    """Per-arm per-row official scores from ``arm-<arm>-<scorer>-scores.json`` (written by stage3_rollout_score --mode perception-branches)."""

    out: dict[str, dict] = {}
    for arm in ARMS:
        path = Path(analysis_columns) / COLUMN_SCORE_NAME.format(arm=arm, scorer=scorer_id)
        if not path.exists():
            raise ReadError(f"missing column score file {path}; run `nxt_r1_read.sh columns` first")
        out[arm] = base.rows_table(json.loads(path.read_text(encoding="utf-8")), scorer_id)
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("smoke", "read"), required=True)
    parser.add_argument("--data-root", type=Path, default=Path(_data_root_env()))
    parser.add_argument("--repo-root", type=Path, default=_REPO)
    parser.add_argument("--analysis-root", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--draws", type=int, default=DRAWS)
    parser.add_argument("--sealonly", action="store_true",
                        help="read the SEAL-ONLY completion's attempt at the complete-row n (package -sealonly-v1); the failing and never-started rows are reported by count")
    args = parser.parse_args(argv)
    spec = fam.sealonly_spec()
    root = args.analysis_root or (args.data_root / fam.ANALYSIS_ROOT / (spec["analysis_dir"] if args.sealonly else ""))
    root.mkdir(parents=True, exist_ok=True)
    cells = fam.CELLS
    try:
        if args.sealonly and args.stage != "read":
            raise ReadError("--sealonly reads the sealed completion only (--stage read); the smoke was sealed by the first attempt")
        if args.stage == "smoke":
            paths = base.run_paths(args.data_root, cells["smoke"]["run"], cells["smoke"]["attempt"])
            for name in ("trace", "outputs"):
                if not paths[name].exists():
                    raise ReadError(f"missing sealed file {paths[name]}")
            outputs_rows = load_outputs_rows(paths["outputs"])
            by_arm = attribute(trace_contacts(paths["trace"]), arm_contact_map(outputs_rows))
            result = smoke_stage(by_arm, absent=base.absent_solver_columns(outputs_rows, ARMS))
            result["sealed_hashes"] = {n: base.sha256_file(paths[n]) for n in ("trace", "outputs")}
            out = root / "smoke-decode-cost.json"
        else:
            attempt = spec["attempt"] if args.sealonly else cells["arm"]["attempt"]
            roster_path = args.repo_root / (spec["complete_rows"] if args.sealonly else fam.ROSTER["arm"])
            paths = base.run_paths(args.data_root, cells["arm"]["run"], attempt)
            for name in ("trace", "outputs", "manifest"):
                if not paths[name].exists():
                    raise ReadError(f"missing sealed file {paths[name]}")
            manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
            if str(manifest.get("status", "")).upper() != "COMPLETED":
                raise ReadError(f"manifest status is {manifest.get('status')!r}, not COMPLETED")
            sealonly = None
            if args.sealonly:
                registered = json.loads((args.repo_root / "configs" / "experiment" / f"{spec['experiment']}.json").read_text(encoding="utf-8"))["cells"][0]["resume_from"]
                sealonly = sealonly_block(json.loads(roster_path.read_text(encoding="utf-8")), registered, manifest)
            resume = None
            if not args.sealonly:
                declared = json.loads((args.repo_root / "configs" / "experiment" / f"{cells['arm']['cell']}.json").read_text(encoding="utf-8"))["cells"][0].get("resume_from")
                if declared is not None:
                    resume = resume_block(manifest, declared, fam.ROWS)
            arms = load_column_rows(root / "columns")
            ids, cluster_of, scenario_of = base.roster_maps(roster_path)
            for arm, rows in arms.items():
                if set(rows) != set(ids):
                    raise ReadError(f"{arm}: the per-sample id set is not the frozen {'seal-only complete-row' if args.sealonly else 'Fold B'} roster's")
            outputs_rows = load_outputs_rows(paths["outputs"])
            by_arm = attribute(trace_contacts(paths["trace"]), arm_contact_map(outputs_rows))
            flags = base.load_output_flags(paths["outputs"])
            result = read_stage(arms, ids, cluster_of, scenario_of, by_arm, flags, seed=args.seed, draws=args.draws,
                                absent=base.absent_solver_columns(outputs_rows, ARMS))
            result["sealed_hashes"] = {n: base.sha256_file(paths[n]) for n in ("trace", "outputs", "manifest")}
            if sealonly is not None:
                result["sealonly"] = sealonly
            if resume is not None:
                result["resume"] = resume
            out = root / "read.json"
    except ReadError as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 2
    if out.exists():
        print(f"REFUSED: {out} exists (write-once)", file=sys.stderr)
        return 6
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    note = out.with_name("smoke-decode-cost.md" if args.stage == "smoke" else "README.md")
    note.write_text(render_markdown({"arms_nodes": result["arms"], "throughput": result.get("throughput")}) if args.stage == "smoke" else render_markdown(result),
                    encoding="utf-8")
    print(json.dumps({"written": str(out), "node_words": {a: w["word"] for a, w in (result.get("node_words") or {}).get("words", {}).items()}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
