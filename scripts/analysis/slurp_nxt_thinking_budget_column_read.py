#!/usr/bin/env python3
"""slurp_nxt_thinking_budget_column_read.py -- the preregistered READ of NX-T R2 (the per-node reasoning-budget column on the Thinking core, TRAIN Fold B).

Package ``docs/readiness/2026-10-15-slurp-nxt-r2-thinking-budget-fold-b-v1/``. A sealed run whose Perception node carries ``thinking_variants`` (receipt
``saea-perception-branch-arms-v5``, level 2) holds, per row, one Perception note and one first-visit Solver answer per arm: the candidate budget arms of
``scripts/flights/nx/nxt_r2_arms.json`` (default ``budget-1536`` and ``budget-2048``) and the delivering arm ``budget-3072`` (the 268-B lock form). NO twin flies
(owner decision 313 A). Stages:

  columns  (run first, by ``scripts/flights/nx/nxt_r2_read.sh columns``) the OFFICIAL per-arm scoring: ``stage3_rollout_score.py --mode
           perception-branches`` renders each arm's first Solver answer and scores it once, complete, with the registered official scorer.
  smoke    the four-row smoke: per ARM and per NODE decode cost from the sealed trace (completion tokens, finish reasons, cap hits, empty completions, FORCED CLOSES =
           contacts that hit the budget, reasoning characters, seconds), the measured arm mix against the registered one, and the machine sign-off conditions of
           decision 314 A as booleans. Nothing is scored; the coordinator reads it to sign off the column flight.
  read     the full read over the sealed, column-scored run, PAIRED per row against the delivering arm (utterance-cluster bootstrap, 10,000 draws, seed 20261015):
           official SLU-F1 (primary) and intent accuracy (scenario_action exact) levels per arm; each candidate minus the delivering arm with CI95; saves/harms/ties
           of intent; the per-scenario table (natural and equal weightings); the per-arm per-node token / finish-reason / cap-hit / empty / forced-close /
           reasoning-marker tables; seconds per contact; and the THROUGHPUT table (rows per minute at the flight's own measured seconds per row, the projected
           GPU-h of a 1,080-row LOCK flight at each budget, and each arm's cost in delivering rows against the registered cost).

Node words (preregistered; development numbers only; claims_benefit is false -- an attribution and a saving, never an admission). With NO twin the null is the
DECLARED same-core A/A offset ``|o|`` = 1.15 pp SLU (the larger of the two measured offsets, 268-B +1.15 and P3.1 -0.61; owner decision 313 A) and the paired floor is
0.7 pp (decisions 172/231/313). For each candidate arm X with SLU delta d and CI95 [lo, hi], and intent CI95 lower bound ilo, the FIRST rule that applies:
  GAIN                         lo > +|o|                       (the cheaper budget RAISES the score beyond the declared A/A width)
  NEEDS-FULL-BUDGET            hi < -|o|                       (the cheaper budget loses more than the declared A/A width)
  CHEAPER-AT-NO-RESOLVED-LOSS  lo >= -1.49 pp and ilo >= -0.65 pp   (decision 190 floors: any loss is inside the design's own resolution)
  UNRESOLVED                   otherwise
The twin offsets of 268-B and P3.1 are reported beside, never re-measured here.

Model-free. Every sealed byte is opened read-only. NO utterance text, transcript, gold label, model output or reasoning text is printed or persisted:
contact text is reduced to booleans and counts at read time and dropped.

    python -B scripts/analysis/slurp_nxt_thinking_budget_column_read.py --stage smoke --data-root $SPEECHRL_DATA_DIR
    python -B scripts/analysis/slurp_nxt_thinking_budget_column_read.py --stage read  --data-root $SPEECHRL_DATA_DIR
"""

from __future__ import annotations

import argparse
import base64
import importlib
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

import slurp_direct_fold_b_core_read as base  # noqa: E402
import slurp_system_thinking_core_read as sysread  # noqa: E402

from speech_aware_evidence_acquisition.analysis.paired import resampled_statistic  # noqa: E402

#: The family this reader reads is a PARAMETER (default NX-T R2's, so R2's behaviour is unchanged). NX-T R2b loads a second copy of this module with
#: ``NXT_COLUMN_READ_FAMILY=nxt_r2b_family`` (``slurp_nxt_r2b_solver_budget_column_read.py``). A family may optionally define ``NODE_BUDGETS`` (arm -> node ->
#: budget), ``NODE_CAPS`` (arm -> node -> completion cap), ``WORD_MODE`` ("cheaper", the default, or "raise" for an arm whose budget is ABOVE the delivering one),
#: ``SMOKE_SCHEMA``, ``READ_SCHEMA`` and ``READ_TITLE``.
FAMILY_ENV = "NXT_COLUMN_READ_FAMILY"
fam = importlib.import_module(os.environ.get(FAMILY_ENV) or "nxt_r2_family")


def _authority_default() -> str:
    lib = Path(__file__).resolve().parents[1] / "lib" / "data_root.sh"
    match = re.search(r"^SAEA_DATA_ROOT_DEFAULT=(\S+)\s*$", lib.read_text(encoding="utf-8"), re.M)
    if match is None:
        raise SystemExit(f"{lib} does not assign SAEA_DATA_ROOT_DEFAULT")
    return match.group(1)


def _data_root_env() -> str:
    return os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or _authority_default()


SCHEMA_SMOKE = getattr(fam, "SMOKE_SCHEMA", "saea-nxt-r2-thinking-budget-column-smoke-v1")
SCHEMA_READ = getattr(fam, "READ_SCHEMA", "saea-nxt-r2-thinking-budget-column-read-v1")
READ_TITLE = getattr(fam, "READ_TITLE", "NX-T R2 read -- the per-node reasoning-budget column")
#: "cheaper" (NX-T R2: an arm BELOW the delivering budget) or "raise" (NX-T R2b: an arm ABOVE it; the words invert).
WORD_MODE = getattr(fam, "WORD_MODE", "cheaper")
#: The node words in the order the rules apply (the first that applies wins).
NODE_WORDS = (("GAIN", "HARM", "NEEDS-NO-MORE-BUDGET", "UNRESOLVED") if WORD_MODE == "raise"
              else ("GAIN", "NEEDS-FULL-BUDGET", "CHEAPER-AT-NO-RESOLVED-LOSS", "UNRESOLVED"))
SEED = 20261015
DRAWS = base.DEFAULT_DRAWS
INTENT_FIELD, SLU_GROUPS, SCORER = base.INTENT_FIELD, base.SLU_GROUPS, base.SCORER
ReadError = base.ReadError
CONTACTS_ZERO = base.CONTACTS_ZERO
ARMS = fam.ARM_ORDER
DELIVERING, CANDIDATES = fam.DELIVERING, fam.CANDIDATE_ARMS
NODES = fam.NODES
#: arm -> node -> the node's reasoning budget in tokens (``None`` = thinking OFF at that node).
BUDGET = (getattr(fam, "NODE_BUDGETS", None)
          or {arm: {node: (None if setting == fam.OFF else int(setting)) for node, setting in zip(NODES, fam.SETTINGS[arm])} for arm in ARMS})
#: arm -> node -> the node's own completion cap (a family without per-node caps: the cap never moves, see ``arm_node_table``).
NODE_CAPS = getattr(fam, "NODE_CAPS", None)
#: arm -> node -> True when the arm turns that node's thinking OFF.
NO_THINK = {arm: {node: BUDGET[arm][node] is None for node in NODES} for arm in ARMS}
THINK_CAP, NO_THINK_CAP = fam.COMPLETION_CAP, fam.tsf.THINK_ANSWER_RESERVE_TOKENS
SLOTS = fam.THINK_SLOTS
COLUMN_SCORE_NAME = "arm-{arm}-{scorer}-scores.json"
#: Decision 314 A machine sign-off: the measured arm mix may be at most this multiple of the registered one.
MIX_TOLERANCE = 1.3


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
    """The per-node completion / finish-reason / cap-hit / empty / forced-close / reasoning-marker table of ONE arm. The cap of a node is 1,024 when the arm turns its
    thinking off and 4,096 otherwise (it never moves with the budget); ``forced_closes`` counts the contacts that hit the node's reasoning budget; a no-think contact
    that still returns reasoning characters or a think marker is counted explicitly."""

    groups: dict[str, list[Mapping]] = defaultdict(list)
    for contact in contacts:
        groups[str(contact["node"])].append(contact)
    table: dict[str, dict] = {}
    for node, items in sorted(groups.items()):
        n = len(items)
        no_think = bool(NO_THINK.get(arm, {}).get(node, False))
        cap = NO_THINK_CAP if no_think else THINK_CAP
        if NODE_CAPS is not None and node in NODE_CAPS.get(arm, {}):
            cap = int(NODE_CAPS[arm][node])                       # a family with a completion cap per node setting (NX-T R2b)
        tokens = [int(c["completion_tokens"]) for c in items]
        seconds = [float(c["latency_seconds"]) for c in items]
        wired = [c for c in items if c.get("empty_content") is not None]
        forced = sum(1 for c in wired if c["forced_close"])
        table[node] = {
            "contacts": n, "mode": "no-think" if no_think else "think", "cap": cap, "budget": BUDGET.get(arm, {}).get(node),
            "cap_hits": sum(1 for t in tokens if t >= cap),
            "finish_reasons": dict(sorted(Counter(str(c.get("finish_reason")) for c in wired).items())),
            "finish_reason_length": sum(1 for c in wired if c.get("finish_reason") == "length"),
            "empty_content": sum(1 for c in wired if c["empty_content"]), "no_json_object": sum(1 for c in wired if c["no_json_object"]),
            "marker_in_content": sum(1 for c in wired if c["marker_in_content"]),
            "forced_closes": forced, "forced_close_share": (forced / len(wired)) if wired else float("nan"),
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
    """THE EFFICIENCY DELIVERABLE. Per arm: seconds per row (the arm's Perception plus Solver mean contact seconds), rows per minute at ``slots`` slots, the slot-normalised
    GPU hours of a pass over ``rows`` rows -- which IS the GPU-h of a ``rows``-row LOCK flight that ran this arm's setting on both nodes (``gpu_hours_per_lock_flight``) --
    the same projected at the registered 1.84 rows/min reference, the saving against the delivering arm, and the arm's cost in delivering rows next to the registered
    cost (``nxt_r2_family.ROW_COST``). Measured seconds only."""

    seconds = {arm: sum(node["seconds_per_contact"]["mean"] for node in t.values()) for arm, t in tables.items() if arm != "unattributed"}
    ref = seconds.get(delivering)
    out: dict[str, dict] = {}
    for arm, per_row in sorted(seconds.items()):
        cost = per_row / ref if ref else float("nan")
        out[arm] = {
            "seconds_per_row": per_row, "rows_per_minute": slots * 60.0 / per_row if per_row else float("nan"),
            "gpu_hours_per_lock_flight": rows * per_row / slots / 3600.0,
            "gpu_hours_per_lock_flight_at_reference_throughput": rows / (fam.ROWS_PER_MINUTE_FULL / cost) / 60.0 if ref and cost else float("nan"),
            "saving_vs_delivering": 1.0 - cost if ref else float("nan"),
            "cost_in_delivering_rows": cost, "registered_cost_in_rows": fam.ROW_COST.get(arm),
        }
    total = sum(v["cost_in_delivering_rows"] for v in out.values()) if ref else float("nan")
    return {"slots": slots, "lock_flight_rows": rows, "arms": out, "arm_mix_measured_rows": total, "arm_mix_registered_rows": fam.ARM_MIX_ROWS,
            "mix_ratio_measured_over_registered": total / fam.ARM_MIX_ROWS if ref else float("nan"),
            "registered_rows_per_minute_full": fam.ROWS_PER_MINUTE_FULL, "registered_gpu_hours_ceiling": fam.CELLS["arm"]["gpu_hours"],
            "measured_gpu_hours_one_flight": sum(v["gpu_hours_per_lock_flight"] for v in out.values())}


def signoff_conditions(tables: Mapping[str, Mapping], throughput: Mapping, unattributed: int, absent_columns: int = 0) -> dict:
    """Decision 314 A machine sign-off conditions as booleans (the coordinator keeps the veto; this reader never writes the marker): zero cap hits / empty answers /
    malformed JSON / length finishes, zero think markers, no reasoning bytes on a no-think node, every contact attributed, the measured mix within 1.3x the registered
    one. ``forced_closes_by_budget`` is informational (four independent rows are noisy)."""

    nodes = [(arm, node, t) for arm, per_node in tables.items() if arm != "unattributed" for node, t in per_node.items()]
    by_budget: dict[str, dict[str, int]] = defaultdict(dict)
    for arm, node, t in nodes:
        if t["mode"] == "think" and t["budget"] is not None:
            by_budget[node][f"{arm}@{t['budget']}"] = t["forced_closes"]
    mix = throughput.get("mix_ratio_measured_over_registered", float("nan"))
    cond = {
        "no_cap_hits_empty_or_malformed": all(t["cap_hits"] == t["empty_content"] == t["no_json_object"] == t["finish_reason_length"] == 0 for _, _, t in nodes),
        "no_think_markers_in_content": all(t["marker_in_content"] == 0 for _, _, t in nodes),
        "no_reasoning_bytes_on_a_no_think_node": all(t["contacts_with_reasoning_chars"] == 0 for _, _, t in nodes if t["mode"] == "no-think"),
        "every_contact_attributed": unattributed == 0,
        "no_absent_columns": absent_columns == 0,
        "mix_within_tolerance": bool(mix == mix and mix <= MIX_TOLERANCE),
    }
    return {"conditions": cond, "all_ok": all(cond.values()), "mix_tolerance": MIX_TOLERANCE, "mix_ratio": mix,
            "forced_closes_by_budget": {node: dict(sorted(v.items())) for node, v in sorted(by_budget.items())}}


def smoke_stage(by_arm: Mapping[str, Sequence[Mapping]], *, rows: int = fam.SMOKE_ROWS, absent: Mapping | None = None) -> dict:
    tables = tables_by_arm(by_arm)
    absent = absent if absent is not None else base.absent_solver_columns([], ARMS)
    no_think_leaks = {
        arm: {node: {"contacts_with_reasoning_chars": t["contacts_with_reasoning_chars"], "marker_in_content": t["marker_in_content"],
                     "empty_content": t["empty_content"], "finish_reasons": t["finish_reasons"]}
              for node, t in nodes.items() if t["mode"] == "no-think"} for arm, nodes in tables.items()}
    projection_rows = fam.ROWS
    throughput = throughput_table(tables, projection_rows)
    unattributed = len(by_arm.get("unattributed", []))
    return {"schema": SCHEMA_SMOKE, "status": "DECODE-COST PER ARM AND NODE (no score, no read)", "arms": tables,
            "no_think_nodes": {arm: v for arm, v in no_think_leaks.items() if v},
            "throughput": throughput, "smoke_rows": rows, "signoff": signoff_conditions(tables, throughput, unattributed, absent["total"]),
            "absent_columns": absent["total"], "absent_rows_by_arm": dict(absent["by_arm"]),
            "unattributed_contacts": unattributed, "contacts": CONTACTS_ZERO}


# --------------------------------------------------------------------------- the paired contrasts


def _pooled(rows: Mapping[str, Mapping[str, float]], ids: Sequence[str]) -> float:
    return base._pooled(rows, ids)


def _intent(rows: Mapping[str, Mapping[str, float]], ids: Sequence[str]) -> float:
    return base._mean_field(rows, ids, INTENT_FIELD)


def paired_contrasts(arms: Mapping[str, Mapping[str, Mapping[str, float]]], ids: Sequence[str], cluster_of: Callable[[str], str], *,
                     seed: int = SEED, draws: int = DRAWS, delivering: str = DELIVERING) -> dict:
    """Every candidate arm minus the delivering arm (no twin flies), SLU-F1 and intent, utterance-cluster bootstrap; levels per arm."""

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


def classify(slu: Mapping, intent: Mapping, *, offset: float = fam.DECLARED_OFFSET_SLU_PP, floor_slu_pp: float = fam.FLOOR_SLU_PP,
             floor_intent_pp: float = fam.FLOOR_INTENT_PP) -> str:
    """The preregistered word of one candidate arm from its SLU and intent contrasts (each with ``ci95_lo_pp`` / ``ci95_hi_pp``): the FIRST rule that applies."""

    if WORD_MODE == "raise":
        # An arm whose budget is ABOVE the delivering one (NX-T R2b): the R2 "cheaper" words invert. GAIN / HARM against the declared A/A offset, then "no resolved gain"
        # (even the optimistic end of both intervals is inside the decision-190 floors: the raise buys nothing the design can resolve), else UNRESOLVED.
        if slu["ci95_lo_pp"] > offset:
            return "GAIN"
        if slu["ci95_hi_pp"] < -offset:
            return "HARM"
        if slu["ci95_hi_pp"] <= floor_slu_pp and intent["ci95_hi_pp"] <= floor_intent_pp:
            return "NEEDS-NO-MORE-BUDGET"
        return "UNRESOLVED"
    if slu["ci95_lo_pp"] > offset:
        return "GAIN"
    if slu["ci95_hi_pp"] < -offset:
        return "NEEDS-FULL-BUDGET"
    if slu["ci95_lo_pp"] >= -floor_slu_pp and intent["ci95_lo_pp"] >= -floor_intent_pp:
        return "CHEAPER-AT-NO-RESOLVED-LOSS"
    return "UNRESOLVED"


def node_label(arm: str) -> str:
    """Which node(s) the arm changes, from the arm table (``perception@1536+solver@1536``; a node at the locked budget is not named; ``off`` is spelled)."""

    parts = [f"{node}@{'off' if BUDGET[arm][node] is None else BUDGET[arm][node]}" for node in NODES if BUDGET[arm][node] != fam.DELIVERING_BUDGET]
    return "+".join(parts) if parts else "none (the delivering arm)"


def node_words(contrast: Mapping, *, offset: float = fam.DECLARED_OFFSET_SLU_PP, floor_slu_pp: float = fam.FLOOR_SLU_PP,
               floor_intent_pp: float = fam.FLOOR_INTENT_PP) -> dict:
    """The preregistered words per candidate arm against the DECLARED A/A offset (no twin flies; see the module docstring)."""

    versus = contrast["versus_delivering"]
    words: dict[str, dict] = {}
    for arm in CANDIDATES:
        if arm not in versus:
            continue
        slu, intent = versus[arm]["slu_f1"], versus[arm]["intent"]
        words[arm] = {"word": classify(slu, intent, offset=offset, floor_slu_pp=floor_slu_pp, floor_intent_pp=floor_intent_pp),
                      "slu_delta_pp": slu["point_pp"], "slu_ci95": [slu["ci95_lo_pp"], slu["ci95_hi_pp"]],
                      "intent_delta_pp": intent["point_pp"], "intent_ci95": [intent["ci95_lo_pp"], intent["ci95_hi_pp"]],
                      "node": node_label(arm), "budget": dict(BUDGET[arm])}
    return {"declared_offset_abs_pp": offset, "paired_floor_pp": fam.PAIRED_FLOOR_PP,
            "declared_offset_basis": "owner decision 313 A: the larger of the two measured same-core A/A offsets (no twin flies)",
            "external_reference_twin_offsets": {"268b_slu_pp": fam.TWIN_OFFSET_268B_SLU_PP, "268b_intent_pp": fam.TWIN_OFFSET_268B_INTENT_PP,
                                                "p31_slu_pp": fam.TWIN_OFFSET_P31_SLU_PP, "p31_intent_pp": fam.TWIN_OFFSET_P31_INTENT_PP,
                                                "thinking_system_slu": fam.THINKING_SYSTEM_SLU, "thinking_system_intent": fam.THINKING_SYSTEM_INTENT},
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
        "node_words": node_words(contrast), "node_words_vocabulary": list(NODE_WORDS),
        "interval": {"kind": "utterance-cluster bootstrap", "draws": draws, "seed": seed, "level": "CI95"},
        "contrast": contrast, "per_scenario": per_scenario_table(arms, ids, scenario_of),
        "arms_nodes": tables,
        "completion_and_finish_reasons": {arm: {node: {"finish_reasons": t["finish_reasons"], "completion_tokens_mean": t["completion_tokens"]["mean"],
                                                       "cap_hits": t["cap_hits"], "empty_content": t["empty_content"], "forced_closes": t["forced_closes"],
                                                       "forced_close_share": t["forced_close_share"],
                                                       "contacts_with_reasoning_chars": t["contacts_with_reasoning_chars"], "marker_in_content": t["marker_in_content"],
                                                       "mode": t["mode"], "budget": t["budget"]}
                                              for node, t in nodes.items()} for arm, nodes in tables.items()},
        "throughput": throughput_table(tables, fam.ROWS), "delivered_content": delivered, "reasoning_marker_total": markers,
        "unattributed_contacts": len(by_arm.get("unattributed", [])),
        "absent_columns": absent["total"], "absent_rows_by_arm": dict(absent["by_arm"]), "absent_reasons": dict(absent["reasons"]),
        "scorer_parse_failures": {arm: sum(1 for row in rows.values() if row.get("parsed", 1.0) == 0.0) for arm, rows in sorted(arms.items())},
        "contacts": CONTACTS_ZERO,
    }


def resume_block(manifest: Mapping, resume_from: Mapping, rows: int) -> dict:
    """The RESUME (rec2, owner ruling 328) account, by COUNT: the rows kept from the stopped rec1 attempt and the rows the resume flew, with proof that the sealed
    manifest's predecessor block names the registered pin (the trace sha256 in mode A, the row-checkpoint sha256 in mode B). The read is at the full roster (kept +
    flown); the split is reported, never used."""

    predecessor = manifest.get("predecessor_attempt")
    pin_key = "checkpoint_sha256" if "checkpoint_sha256" in resume_from else "trace_sha256"
    if not isinstance(predecessor, Mapping) or predecessor.get(pin_key) != resume_from.get(pin_key):
        raise ReadError(f"the sealed manifest's predecessor_attempt does not name the registered {pin_key} {resume_from.get(pin_key)!r}")
    kept = len(predecessor.get("kept_sample_ids") or [])
    if kept == 0 or kept >= rows:
        raise ReadError(f"a resume that kept {kept} of {rows} rows is not the registered kept/flown split")
    return {"kept": kept, "flown": rows - kept, "rows": rows, "resume_from": dict(resume_from), "predecessor_counts": dict(predecessor.get("counts") or {}),
            "kept_sample_ids_sha256": predecessor.get("kept_sample_ids_sha256"), "mode": "checkpoint" if pin_key == "checkpoint_sha256" else "trace"}


def render_markdown(result: Mapping) -> str:
    lines = [f"# {READ_TITLE}", ""]
    rs = result.get("resume")
    if rs:
        lines += [f"RESUME (rec2, mode {'B' if rs['mode'] == 'checkpoint' else 'A'}): n = {rs['rows']:,}; {rs['kept']:,} rows kept from the stopped attempt and {rs['flown']:,} rows "
                  "flown by the resume (the split is reported only; kept and flown rows are never separated in a contrast).", ""]
    nw = result.get("node_words")
    if nw:
        ref = nw["external_reference_twin_offsets"]
        lines += [f"Declared A/A offset |o| = {nw['declared_offset_abs_pp']:.2f} pp SLU (no twin flies; measured twins: 268-B {ref['268b_slu_pp']:+.2f}, P3.1 {ref['p31_slu_pp']:+.2f}); "
                  f"paired floor {nw['paired_floor_pp']} pp; no-resolved-loss floors SLU {nw['floors_pp']['slu']} / intent {nw['floors_pp']['intent']} pp.", "",
                  "| arm | node(s) changed | word | SLU d (pp) | SLU CI95 | intent d (pp) | intent CI95 |", "| --- | --- | --- | ---: | --- | ---: | --- |"]
        for arm, w in nw["words"].items():
            lines.append(f"| {arm} | {w['node']} | {w['word']} | {w['slu_delta_pp']:+.2f} | [{w['slu_ci95'][0]:+.2f}, {w['slu_ci95'][1]:+.2f}] | "
                         f"{w['intent_delta_pp']:+.2f} | [{w['intent_ci95'][0]:+.2f}, {w['intent_ci95'][1]:+.2f}] |")
        lines.append("")
    c = result.get("contrast")
    if c:
        lines += [f"| arm | SLU-F1 | intent | SLU d vs {DELIVERING} (pp) | CI95 | intent d (pp) | CI95 | intent saves / harms | absent rows |", "| --- | ---: | ---: | ---: | --- | ---: | --- | --- | ---: |"]
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
        lines += [f"Nodes of `{arm}`:", "", "| node | mode | budget | contacts | cap | cap hits | length | empty | no JSON | forced closes | reasoning chars>0 | markers | tokens p50 / p99 | s per contact |",
                  "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |"]
        for node, t in nodes.items():
            lines.append(f"| {node} | {t['mode']} | {t['budget'] if t['budget'] is not None else '-'} | {t['contacts']} | {t['cap']} | {t['cap_hits']} | {t['finish_reason_length']} | "
                         f"{t['empty_content']} | {t['no_json_object']} | {t['forced_closes']} | {t['contacts_with_reasoning_chars']} | {t['marker_in_content']} | "
                         f"{t['completion_tokens']['p50']:.0f} / {t['completion_tokens']['p99']:.0f} | {t['seconds_per_contact']['mean']:.2f} |")
        lines.append("")
    tp = result.get("throughput")
    if tp:
        lines += [f"THROUGHPUT (the efficiency deliverable): GPU-h of a {tp['lock_flight_rows']:,}-row LOCK flight at each arm's setting.", "",
                  "| arm | s per row | rows / min | GPU-h per lock flight | at the 1.84 rows/min reference | saving vs delivering | cost in delivering rows | registered cost |",
                  "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
        for arm, v in tp["arms"].items():
            lines.append(f"| {arm} | {v['seconds_per_row']:.1f} | {v['rows_per_minute']:.2f} | {v['gpu_hours_per_lock_flight']:.2f} | "
                         f"{v['gpu_hours_per_lock_flight_at_reference_throughput']:.2f} | {v['saving_vs_delivering']:+.1%} | {v['cost_in_delivering_rows']:.2f} | "
                         f"{v['registered_cost_in_rows']} |")
        lines += ["", f"Arm mix measured {tp['arm_mix_measured_rows']:.2f} rows (registered {tp['arm_mix_registered_rows']}, ratio {tp['mix_ratio_measured_over_registered']:.2f}); one "
                  f"flight measured {tp['measured_gpu_hours_one_flight']:.2f} GPU-h (ceiling {tp['registered_gpu_hours_ceiling']}).", ""]
    so = result.get("signoff")
    if so:
        lines += ["Sign-off conditions (decision 314 A; informational, the coordinator keeps the veto): "
                  + ", ".join(f"{k} = {v}" for k, v in so["conditions"].items()) + f"; all_ok = {so['all_ok']}.", ""]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- the sealed-run adapter and the CLI


def load_column_rows(analysis_columns: Path, scorer_id: str = SCORER) -> dict[str, dict]:
    """Per-arm per-row official scores from ``arm-<arm>-<scorer>-scores.json`` (written by stage3_rollout_score --mode perception-branches)."""

    out: dict[str, dict] = {}
    for arm in ARMS:
        path = Path(analysis_columns) / COLUMN_SCORE_NAME.format(arm=arm, scorer=scorer_id)
        if not path.exists():
            raise ReadError(f"missing column score file {path}; run `nxt_r2_read.sh columns` first")
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
    args = parser.parse_args(argv)
    root = args.analysis_root or (args.data_root / fam.ANALYSIS_ROOT)
    root.mkdir(parents=True, exist_ok=True)
    cells = fam.CELLS
    try:
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
            paths = base.run_paths(args.data_root, cells["arm"]["run"], cells["arm"]["attempt"])
            for name in ("trace", "outputs", "manifest"):
                if not paths[name].exists():
                    raise ReadError(f"missing sealed file {paths[name]}")
            manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
            if str(manifest.get("status", "")).upper() != "COMPLETED":
                raise ReadError(f"manifest status is {manifest.get('status')!r}, not COMPLETED")
            declared = json.loads((args.repo_root / "configs" / "experiment" / f"{cells['arm']['cell']}.json").read_text(encoding="utf-8"))["cells"][0].get("resume_from")
            resume = resume_block(manifest, declared, fam.ROWS) if declared is not None else None
            arms = load_column_rows(root / "columns")
            ids, cluster_of, scenario_of = base.roster_maps(args.repo_root / fam.ROSTER["arm"])
            for arm, rows in arms.items():
                if set(rows) != set(ids):
                    raise ReadError(f"{arm}: the per-sample id set is not the frozen Fold B roster's")
            outputs_rows = load_outputs_rows(paths["outputs"])
            by_arm = attribute(trace_contacts(paths["trace"]), arm_contact_map(outputs_rows))
            flags = base.load_output_flags(paths["outputs"])
            result = read_stage(arms, ids, cluster_of, scenario_of, by_arm, flags, seed=args.seed, draws=args.draws,
                                absent=base.absent_solver_columns(outputs_rows, ARMS))
            result["sealed_hashes"] = {n: base.sha256_file(paths[n]) for n in ("trace", "outputs", "manifest")}
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
    note.write_text(render_markdown({"arms_nodes": result["arms"], "throughput": result.get("throughput"), "signoff": result.get("signoff")})
                    if args.stage == "smoke" else render_markdown(result), encoding="utf-8")
    print(json.dumps({"written": str(out), "node_words": {a: w["word"] for a, w in (result.get("node_words") or {}).get("words", {}).items()}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
