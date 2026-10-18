#!/usr/bin/env python3
"""slurp_nxt_r3_solver_template_column_read.py -- the preregistered READ of NX-T R3 (the Solver instruction-template column on the Thinking core, TRAIN Fold B).

Package ``docs/readiness/2026-10-18-slurp-nxt-r3-solver-template-fold-b-v1/``. A sealed run whose Solver node carries ``template_variants`` (receipt
``saea-supply-variant-arms-v4``) holds, per row, one Perception note and K = 6 first-visit Solver answers: ``t1-decide-once`` / ``t2-grounded-or-empty`` /
``t3-supply-focus`` / ``t4-decide-once-grounded`` (candidates), ``aa`` (the in-flight A/A, replicate_of lock) and ``lock`` (the delivering arm). Stages:

  columns  (run first, by ``scripts/flights/nx/nxt_r3_read.sh columns``) the OFFICIAL per-arm scoring: ``stage3_rollout_score.py --mode supply-variants`` renders each
           arm's first Solver answer and scores it once, complete, with the registered official scorer (``slurp-slu-official-train``).
  smoke    the four-row smoke: per ARM the Solver decode cost from the sealed trace (completion tokens, finish reasons, cap hits, empty completions, forced closes,
           seconds) and the shared Perception node as ``_perception``. Nothing is scored; the machine sign-off reads it.
  read     the full read, PAIRED per row against the delivering ``lock`` arm (utterance-cluster bootstrap, 10,000 draws, seed 20261018): official SLU-F1 (primary)
           and intent accuracy (scenario_action exact) per arm; each candidate and the twin minus ``lock`` with CI95; the per-scenario table (natural mixture and
           equal scenario); per arm the Solver completion / finish-reason / cap-hit / empty / forced-close tables, seconds per contact, the forced-close share SPLIT
           BY SUPPLIED-ITEM BIN (< 40 and >= 40 items), the empty-gold false-fill rows SPLIT BY FORCED STATUS, and the non-empty exact-set rate.

Arm words (preregistered; development numbers only; claims_benefit is false -- a nomination, never an admission). The twin ``aa`` is the in-flight A/A: its SLU delta
against ``lock`` is the offset o and |o| the bar. For each candidate arm X with SLU delta d (CI95 [lo, hi]) and intent delta i (CI95 [ilo, ihi]), the first rule that
applies wins:

  NOMINATED          lo > 0 AND i >= -0.65 pp AND d >= |o|
  EFFICIENT-NO-LOSS  hi >= -|o| AND ihi >= -0.65 pp (the NX-T R1 NO-RESOLVED-LOSS rule on SLU and, with the decision-190 intent floor, on intent) AND the arm's Solver
                     seconds per contact <= 0.85 x the lock arm's
  HARM               hi < 0
  NEUTRAL            otherwise

A NOMINATED or EFFICIENT-NO-LOSS arm goes to a 2-arm Fold A confirm (not built here).

Model-free. Every sealed byte is opened read-only. NO utterance text, transcript, gold label, model output or reasoning text is printed or persisted: contact text is
reduced to booleans and counts at read time and dropped.

    python -B scripts/analysis/slurp_nxt_r3_solver_template_column_read.py --stage smoke --data-root $SPEECHRL_DATA_DIR
    python -B scripts/analysis/slurp_nxt_r3_solver_template_column_read.py --stage read  --data-root $SPEECHRL_DATA_DIR
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Callable, Mapping, Sequence

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parents[1]
for _path in (str(_REPO / "src"), str(_HERE), str(_REPO / "scripts" / "flights" / "nx"), str(_REPO / "scripts" / "flights" / "direct"),
              str(_REPO / "scripts" / "flights" / "tfrl")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import nxt_r3_family as fam  # noqa: E402
import slurp_direct_fold_b_core_read as base  # noqa: E402
import slurp_nxt_thinking_policy_column_read as npc  # noqa: E402  (trace attribution, per-node tables, paired contrasts and the per-scenario table, reused)


def _authority_default() -> str:
    lib = Path(__file__).resolve().parents[1] / "lib" / "data_root.sh"
    match = re.search(r"^SAEA_DATA_ROOT_DEFAULT=(\S+)\s*$", lib.read_text(encoding="utf-8"), re.M)
    if match is None:
        raise SystemExit(f"{lib} does not assign SAEA_DATA_ROOT_DEFAULT")
    return match.group(1)


def _data_root_env() -> str:
    return os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or _authority_default()


SCHEMA_SMOKE = fam.SMOKE_SCHEMA
SCHEMA_READ = fam.READ_SCHEMA
WORDS = ("NOMINATED", "EFFICIENT-NO-LOSS", "HARM", "NEUTRAL")
SEED = 20261018
DRAWS = base.DEFAULT_DRAWS
INTENT_FIELD, SCORER = base.INTENT_FIELD, base.SCORER
ReadError = base.ReadError
CONTACTS_ZERO = base.CONTACTS_ZERO
ARMS = fam.ARM_ORDER
DELIVERING, TWIN, CANDIDATES = fam.DELIVERING, fam.TWIN, fam.CANDIDATE_ARMS
PERCEPTION = "_perception"
SLOTS = fam.THINK_SLOTS
SUPPLY_BIN_EDGE = 40                                   # supplied items: "lt40" below, "ge40" at or above (the coordinator's row-level analysis of the sealed R2b column)
COLUMN_SCORE_NAME = "arm-{arm}-{scorer}-scores.json"
WORD_TP, WORD_FP, WORD_FN = "slu_f1_word_tp", "slu_f1_word_fp", "slu_f1_word_fn"


# --------------------------------------------------------------------------- the sealed row -> arm -> contact map (ids only)


def load_outputs_rows(path: Path) -> list[dict]:
    """The sealed outputs reduced to what the map needs (ids and counts only; every delivered text is dropped): per row, the sample id, the template arms
    ``[(arm_id, contact_id, supplied_item_count)]`` of the one arm receipt and the Perception contact ids of the role visits."""

    rows: list[dict] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            receipt = row.get("supply_variants") if isinstance(row.get("supply_variants"), Mapping) else None
            arms = [(str(a.get("arm_id")), str(a.get("contact_id")), a.get("supplied_item_count")) for a in (receipt or {}).get("arms") or []]
            perception = []
            for visit in ((row.get("native_episode_receipt") or {}).get("role_visits") or []):
                if isinstance(visit, Mapping) and visit.get("stage") == "perception":
                    contacts = ((visit.get("execution_receipt") or {}).get("contacts")) or []
                    perception += [str(c.get("agent_contact_id")) for c in contacts if isinstance(c, Mapping) and c.get("agent_contact_id")]
            rows.append({"sample_id": str(row["sample_id"]), "arms": arms, "perception": perception})
            row.clear()
    return rows


def arm_contact_map(outputs_rows: Sequence[Mapping]) -> dict[str, tuple[str, str]]:
    """``{agent_contact_id: (arm, node)}``: each Solver arm contact to its arm, each Perception contact to the shared ``_perception`` pseudo-arm."""

    mapping: dict[str, tuple[str, str]] = {}
    for row in outputs_rows:
        for arm_id, contact_id, _ in row["arms"]:
            mapping[contact_id] = (arm_id, "solver")
        for contact_id in row["perception"]:
            mapping[contact_id] = (PERCEPTION, "perception")
    return mapping


def contact_rows(outputs_rows: Sequence[Mapping], contacts: Sequence[Mapping]) -> list[dict]:
    """Solver arm contacts joined to their row: ``{sample_id, arm, supplied, forced_close, ...}`` (booleans and counts only)."""

    by_contact = {c["agent_contact_id"]: c for c in contacts if c.get("agent_contact_id")}
    out: list[dict] = []
    for row in outputs_rows:
        for arm_id, contact_id, supplied in row["arms"]:
            c = by_contact.get(contact_id)
            if c is None:
                continue
            out.append({"sample_id": row["sample_id"], "arm": arm_id, "supplied": supplied, "forced_close": c.get("forced_close"),
                        "completion_tokens": c.get("completion_tokens"), "latency_seconds": c.get("latency_seconds")})
    return out


def missing_columns(outputs_rows: Sequence[Mapping], contacts: Sequence[Mapping], arms: Sequence[str] = ARMS) -> dict:
    """The arm columns a sealed row declares but whose Solver contact is absent from the trace (counts per arm), and rows lacking a declared arm."""

    present = {c.get("agent_contact_id") for c in contacts}
    by_arm: dict[str, int] = {arm: 0 for arm in arms}
    for row in outputs_rows:
        declared = {arm_id for arm_id, _, _ in row["arms"]}
        for arm in arms:
            if arm not in declared:
                by_arm[arm] += 1
        for arm_id, contact_id, _ in row["arms"]:
            if contact_id not in present:
                by_arm[arm_id] = by_arm.get(arm_id, 0) + 1
    return {"by_arm": by_arm, "total": sum(by_arm.values())}


# --------------------------------------------------------------------------- tables


def tables_by_arm(by_arm: Mapping[str, Sequence[Mapping]]) -> dict[str, dict]:
    """Per arm, the per-node decode table (``npc.arm_node_table``: think mode, the 4,096 cap, forced closes, finish reasons, tokens, seconds)."""

    return {arm: npc.arm_node_table(by_arm[arm], arm, slots=SLOTS) for arm in sorted(by_arm)}


def solver_seconds(tables: Mapping[str, Mapping]) -> dict[str, float]:
    return {arm: float(t["solver"]["seconds_per_contact"]["mean"]) for arm, t in tables.items() if "solver" in t}


def throughput_table(tables: Mapping[str, Mapping], rows: int) -> dict:
    """Seconds per row of the column flight (the shared Perception mean plus every arm's Solver mean) in lock-row equivalents against the registered arm mix, plus the
    slot-normalised GPU hours of a pass over ``rows`` rows. Measured seconds only."""

    secs = solver_seconds(tables)
    perception = float(tables.get(PERCEPTION, {}).get("perception", {}).get("seconds_per_contact", {}).get("mean", float("nan")))
    lock = secs.get(DELIVERING)
    per_row = perception + sum(v for k, v in secs.items() if k in ARMS)
    lock_row = perception + lock if lock is not None else float("nan")
    return {"slots": SLOTS, "perception_seconds_per_contact": perception, "solver_seconds_per_contact": dict(sorted(secs.items())),
            "seconds_per_row_column": per_row, "seconds_per_row_lock": lock_row,
            "arm_mix_measured_rows": per_row / lock_row if lock_row == lock_row and lock_row else float("nan"), "arm_mix_registered_rows": fam.ARM_MIX_ROWS,
            "registered_rows_per_minute_full": fam.ROWS_PER_MINUTE_FULL, "registered_gpu_hours_ceiling": fam.CELLS["arm"]["gpu_hours"],
            "measured_gpu_hours_one_flight": rows * per_row / SLOTS / 3600.0 if per_row == per_row else float("nan")}


def smoke_stage(by_arm: Mapping[str, Sequence[Mapping]], *, rows: int = fam.SMOKE_ROWS, missing: Mapping | None = None) -> dict:
    tables = tables_by_arm(by_arm)
    missing = missing if missing is not None else {"total": 0, "by_arm": {}}
    return {"schema": SCHEMA_SMOKE, "status": "DECODE-COST PER ARM (no score, no read)", "arms": tables, "throughput": throughput_table(tables, fam.ROWS), "smoke_rows": rows,
            "absent_columns": missing["total"], "absent_columns_by_arm": dict(missing["by_arm"]), "unattributed_contacts": len(by_arm.get("unattributed", [])),
            "contacts": CONTACTS_ZERO}


def supply_bin(count: object) -> str:
    """``lt40`` / ``ge40`` by the supplied-item count of the arm's receipt row; ``unknown`` when the receipt carries no count."""

    if not isinstance(count, int) or isinstance(count, bool):
        return "unknown"
    return "lt40" if count < SUPPLY_BIN_EDGE else "ge40"


def forced_by_supply_bin(contacts: Sequence[Mapping], arm: str) -> dict:
    """The arm's forced-close share split by the supplied-item bin of its row (counts and shares; contacts without a wire record are counted as ``no_wire``)."""

    out: dict[str, dict] = {b: {"contacts": 0, "forced": 0, "no_wire": 0} for b in ("lt40", "ge40", "unknown")}
    for c in contacts:
        if c["arm"] != arm:
            continue
        cell = out[supply_bin(c["supplied"])]
        cell["contacts"] += 1
        if c["forced_close"] is None:
            cell["no_wire"] += 1
        elif c["forced_close"]:
            cell["forced"] += 1
    for cell in out.values():
        seen = cell["contacts"] - cell["no_wire"]
        cell["forced_share"] = cell["forced"] / seen if seen else float("nan")
    return out


def gold_empty(row: Mapping[str, float]) -> bool:
    """A row whose gold entity list is empty: the official scorer found no true positive and no false negative (word level)."""

    return row.get(WORD_TP, 0.0) + row.get(WORD_FN, 0.0) == 0.0


def empty_gold_false_fill(rows: Mapping[str, Mapping[str, float]], forced_of: Callable[[str], object]) -> dict:
    """On the arm's empty-gold rows: how many were false-filled (the arm emitted at least one entity: word false positives > 0), overall and split by whether the
    arm's Solver contact was a FORCED close (``None`` when the wire record is absent)."""

    out = {"empty_gold_rows": 0, "false_fill_rows": 0, "forced": {"rows": 0, "false_fill": 0}, "natural": {"rows": 0, "false_fill": 0}, "no_wire": {"rows": 0, "false_fill": 0}}
    for sid, row in rows.items():
        if not gold_empty(row):
            continue
        filled = row.get(WORD_FP, 0.0) > 0.0
        out["empty_gold_rows"] += 1
        out["false_fill_rows"] += int(filled)
        forced = forced_of(sid)
        cell = out["no_wire"] if forced is None else out["forced"] if forced else out["natural"]
        cell["rows"] += 1
        cell["false_fill"] += int(filled)
    for key in ("forced", "natural", "no_wire"):
        out[key]["false_fill_share"] = out[key]["false_fill"] / out[key]["rows"] if out[key]["rows"] else float("nan")
    out["false_fill_share"] = out["false_fill_rows"] / out["empty_gold_rows"] if out["empty_gold_rows"] else float("nan")
    return out


def nonempty_exact(rows: Mapping[str, Mapping[str, float]]) -> dict:
    """On non-empty-gold rows: the share whose official word-level false positives and false negatives are both zero (the row's entity set matched exactly)."""

    n = exact = 0
    for row in rows.values():
        if gold_empty(row):
            continue
        n += 1
        exact += int(row.get(WORD_FP, 0.0) == 0.0 and row.get(WORD_FN, 0.0) == 0.0)
    return {"nonempty_gold_rows": n, "exact_rows": exact, "exact_share": exact / n if n else float("nan")}


def arm_secondaries(arms_rows: Mapping[str, Mapping[str, Mapping[str, float]]], contacts: Sequence[Mapping], tables: Mapping[str, Mapping]) -> dict:
    """The per-arm secondaries: Solver forced-close share (overall and by supplied-item bin), completion tokens, seconds per contact, empty-gold false fill (overall and
    by forced status) and the non-empty exact-set share."""

    out: dict[str, dict] = {}
    for arm, rows in arms_rows.items():
        forced_map = {c["sample_id"]: c["forced_close"] for c in contacts if c["arm"] == arm}
        solver = (tables.get(arm) or {}).get("solver") or {}
        wire = solver.get("wire_records") or 0
        out[arm] = {
            "solver_forced_close_share": (solver.get("forced_closes", 0) / wire) if wire else float("nan"),
            "solver_forced_closes": solver.get("forced_closes"), "solver_wire_records": wire,
            "forced_close_by_supplied_items_bin": forced_by_supply_bin(contacts, arm),
            "completion_tokens": solver.get("completion_tokens"), "seconds_per_contact": solver.get("seconds_per_contact"),
            "empty_gold_false_fill": empty_gold_false_fill(rows, lambda sid, m=forced_map: m.get(sid)),
            "nonempty_exact_set": nonempty_exact(rows),
        }
    return out


# --------------------------------------------------------------------------- the words


def arm_words(contrast: Mapping, seconds: Mapping[str, float], *, floor_intent_pp: float = fam.FLOOR_INTENT_PP, intent_guard_pp: float = fam.INTENT_GUARD_PP,
              ratio_max: float = fam.EFFICIENT_SECONDS_RATIO) -> dict:
    """The preregistered arm words per candidate (see the module docstring); the twin ``aa`` supplies |o|. Rules apply in order: NOMINATED, EFFICIENT-NO-LOSS, HARM, NEUTRAL."""

    versus = contrast["versus_delivering"]
    twin = versus.get(TWIN)
    offset = abs(twin["slu_f1"]["point_pp"]) if twin else 0.0
    lock_s = seconds.get(DELIVERING)
    words: dict[str, dict] = {}
    for arm in CANDIDATES:
        if arm not in versus:
            continue
        slu, intent = versus[arm]["slu_f1"], versus[arm]["intent"]
        ratio = (seconds[arm] / lock_s) if (arm in seconds and lock_s) else float("nan")
        conditions = {
            "slu_ci_lo_above_zero": slu["ci95_lo_pp"] > 0.0,
            "intent_point_at_or_above_guard": intent["point_pp"] >= intent_guard_pp,
            "slu_point_at_or_above_twin_bar": slu["point_pp"] >= offset,
            "slu_no_resolved_loss": slu["ci95_hi_pp"] >= -offset,
            "intent_no_resolved_loss": intent["ci95_hi_pp"] >= -floor_intent_pp,
            "solver_seconds_ratio_ok": bool(ratio == ratio and ratio <= ratio_max),
            "slu_ci_hi_below_zero": slu["ci95_hi_pp"] < 0.0,
        }
        if conditions["slu_ci_lo_above_zero"] and conditions["intent_point_at_or_above_guard"] and conditions["slu_point_at_or_above_twin_bar"]:
            word = "NOMINATED"
        elif conditions["slu_no_resolved_loss"] and conditions["intent_no_resolved_loss"] and conditions["solver_seconds_ratio_ok"]:
            word = "EFFICIENT-NO-LOSS"
        elif conditions["slu_ci_hi_below_zero"]:
            word = "HARM"
        else:
            word = "NEUTRAL"
        words[arm] = {"word": word, "next_step": "2-arm Fold A confirm" if word in ("NOMINATED", "EFFICIENT-NO-LOSS") else None,
                      "slu_delta_pp": slu["point_pp"], "slu_ci95": [slu["ci95_lo_pp"], slu["ci95_hi_pp"]],
                      "intent_delta_pp": intent["point_pp"], "intent_ci95": [intent["ci95_lo_pp"], intent["ci95_hi_pp"]],
                      "solver_seconds_ratio_vs_lock": ratio, "conditions": conditions}
    return {"twin_offset_abs_pp": offset, "twin_offset_point_pp": twin["slu_f1"]["point_pp"] if twin else None,
            "external_reference_268b": {"twin_offset_slu_pp": fam.TWIN_OFFSET_268B_SLU_PP, "twin_offset_intent_pp": fam.TWIN_OFFSET_268B_INTENT_PP,
                                        "twin_offset_p31_slu_pp": fam.TWIN_OFFSET_P31_SLU_PP, "thinking_system_slu": fam.THINKING_SYSTEM_SLU,
                                        "thinking_system_intent": fam.THINKING_SYSTEM_INTENT},
            "floors_pp": {"slu": fam.FLOOR_SLU_PP, "intent": floor_intent_pp}, "intent_guard_pp": intent_guard_pp, "seconds_ratio_max": ratio_max, "words": words}


def read_stage(arms: Mapping[str, Mapping[str, Mapping[str, float]]], ids: Sequence[str], cluster_of: Callable[[str], str], scenario_of: Callable[[str], str],
               by_arm: Mapping[str, Sequence[Mapping]], contacts: Sequence[Mapping], *, seed: int = SEED, draws: int = DRAWS, missing: Mapping | None = None) -> dict:
    """The full read: paired contrasts, the arm words, the per-scenario table and every per-arm secondary."""

    missing = missing if missing is not None else {"total": 0, "by_arm": {}}
    contrast = npc.paired_contrasts(arms, ids, cluster_of, seed=seed, draws=draws, delivering=DELIVERING)
    tables = tables_by_arm(by_arm)
    secs = solver_seconds(tables)
    return {
        "schema": SCHEMA_READ, "status": "PREREGISTERED-READ (development numbers; never a test claim; claims_benefit false)",
        "arm_words": arm_words(contrast, secs), "arm_words_vocabulary": list(WORDS),
        "interval": {"kind": "utterance-cluster bootstrap", "draws": draws, "seed": seed, "level": "CI95"},
        "contrast": contrast, "per_scenario": npc.per_scenario_table(arms, ids, scenario_of, DELIVERING),
        "secondaries": arm_secondaries(arms, contacts, tables), "arms_nodes": tables, "throughput": throughput_table(tables, fam.ROWS),
        "unattributed_contacts": len(by_arm.get("unattributed", [])), "absent_columns": missing["total"], "absent_columns_by_arm": dict(missing["by_arm"]),
        "scorer_parse_failures": {arm: sum(1 for row in rows.values() if row.get("parsed", 1.0) == 0.0) for arm, rows in sorted(arms.items())},
        "contacts": CONTACTS_ZERO,
    }


def render_markdown(result: Mapping) -> str:
    lines = [f"# {fam.READ_TITLE}", ""]
    rs = result.get("resume")
    if rs:
        lines += [f"RESUME: n = {rs['rows']:,}; {rs['kept']:,} rows kept from the stopped attempt by replay and {rs['flown']} rows flown by the resume "
                  "(the split is reported only; kept and flown rows are never separated in a contrast).", ""]
    aw = result.get("arm_words")
    if aw:
        lines += [f"In-flight twin offset |o| = {aw['twin_offset_abs_pp']:.2f} pp SLU (external 268-B reference {aw['external_reference_268b']['twin_offset_slu_pp']:+.2f}).", "",
                  "| arm | word | SLU d (pp) | SLU CI95 | intent d (pp) | intent CI95 | Solver s ratio | next step |", "| --- | --- | ---: | --- | ---: | --- | ---: | --- |"]
        for arm, w in aw["words"].items():
            lines.append(f"| {arm} | {w['word']} | {w['slu_delta_pp']:+.2f} | [{w['slu_ci95'][0]:+.2f}, {w['slu_ci95'][1]:+.2f}] | {w['intent_delta_pp']:+.2f} | "
                         f"[{w['intent_ci95'][0]:+.2f}, {w['intent_ci95'][1]:+.2f}] | {w['solver_seconds_ratio_vs_lock']:.2f} | {w['next_step'] or ''} |")
        lines.append("")
    c = result.get("contrast")
    if c:
        lines += ["| arm | SLU-F1 | intent | SLU d vs lock (pp) | CI95 | intent d (pp) | CI95 | intent saves / harms |", "| --- | ---: | ---: | ---: | --- | ---: | --- | --- |"]
        for arm, lv in c["levels"].items():
            v = c["versus_delivering"].get(arm)
            if v is None:
                lines.append(f"| {arm} (delivering) | {lv['slu_f1_pct']:.2f} | {lv['intent_pct']:.2f} | | | | | |")
            else:
                s, i, t = v["slu_f1"], v["intent"], v["intent_saves_harms_ties_vs_delivering"]
                lines.append(f"| {arm} | {lv['slu_f1_pct']:.2f} | {lv['intent_pct']:.2f} | {s['point_pp']:+.2f} | [{s['ci95_lo_pp']:+.2f}, {s['ci95_hi_pp']:+.2f}] | "
                             f"{i['point_pp']:+.2f} | [{i['ci95_lo_pp']:+.2f}, {i['ci95_hi_pp']:+.2f}] | {t['saves']} / {t['harms']} |")
        lines.append("")
    sec = result.get("secondaries")
    if sec:
        lines += ["| arm | forced share | forced < 40 items | forced >= 40 items | completion tokens mean | s per contact | empty-gold false fill (forced / natural) | non-empty exact |",
                  "| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |"]
        for arm, s in sec.items():
            b, e = s["forced_close_by_supplied_items_bin"], s["empty_gold_false_fill"]
            tokens = (s["completion_tokens"] or {}).get("mean", float("nan"))
            seconds = (s["seconds_per_contact"] or {}).get("mean", float("nan"))
            lines.append(f"| {arm} | {s['solver_forced_close_share']:.3f} | {b['lt40']['forced_share']:.3f} ({b['lt40']['contacts']}) | {b['ge40']['forced_share']:.3f} ({b['ge40']['contacts']}) | "
                         f"{tokens:.0f} | {seconds:.1f} | {e['forced']['false_fill']}/{e['forced']['rows']} vs {e['natural']['false_fill']}/{e['natural']['rows']} | "
                         f"{s['nonempty_exact_set']['exact_share']:.3f} |")
        lines.append("")
    for arm, nodes in sorted((result.get("arms_nodes") or {}).items()):
        lines += [f"Nodes of `{arm}`:", "", "| node | contacts | cap | cap hits | length | empty | no JSON | forced | markers | tokens p50 / p99 | s per contact |",
                  "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |"]
        for node, t in nodes.items():
            lines.append(f"| {node} | {t['contacts']} | {t['cap']} | {t['cap_hits']} | {t['finish_reason_length']} | {t['empty_content']} | {t['no_json_object']} | "
                         f"{t['forced_closes']} | {t['marker_in_content']} | {t['completion_tokens']['p50']:.0f} / {t['completion_tokens']['p99']:.0f} | {t['seconds_per_contact']['mean']:.2f} |")
        lines.append("")
    tp = result.get("throughput")
    if tp:
        lines += [f"Seconds per row (column) {tp['seconds_per_row_column']:.1f}, lock row {tp['seconds_per_row_lock']:.1f}; arm mix measured {tp['arm_mix_measured_rows']:.2f} lock rows "
                  f"(registered {tp['arm_mix_registered_rows']}); one flight measured {tp['measured_gpu_hours_one_flight']:.2f} GPU-h (ceiling {tp['registered_gpu_hours_ceiling']}).", ""]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- the sealed-run adapter and the CLI


def load_column_rows(analysis_columns: Path, scorer_id: str = SCORER) -> dict[str, dict]:
    """Per-arm per-row official scores from ``arm-<arm>-<scorer>-scores.json`` (written by stage3_rollout_score --mode supply-variants)."""

    out: dict[str, dict] = {}
    for arm in ARMS:
        path = Path(analysis_columns) / COLUMN_SCORE_NAME.format(arm=arm, scorer=scorer_id)
        if not path.exists():
            raise ReadError(f"missing column score file {path}; run `nxt_r3_read.sh columns` first")
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
    budget_message = fam.THINKING_KNOBS["budget_message"]
    try:
        if args.stage == "smoke":
            paths = base.run_paths(args.data_root, cells["smoke"]["run"], cells["smoke"]["attempt"])
            for name in ("trace", "outputs"):
                if not paths[name].exists():
                    raise ReadError(f"missing sealed file {paths[name]}")
            outputs_rows = load_outputs_rows(paths["outputs"])
            contacts = npc.trace_contacts(paths["trace"], budget_message)
            by_arm = npc.attribute(contacts, arm_contact_map(outputs_rows))
            result = smoke_stage(by_arm, missing=missing_columns(outputs_rows, contacts))
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
            resume = None
            declared = json.loads((args.repo_root / "configs" / "experiment" / f"{cells['arm']['cell']}.json").read_text(encoding="utf-8"))["cells"][0].get("resume_from")
            if declared is not None:
                resume = npc.resume_block(manifest, declared, fam.ROWS)
            arms = load_column_rows(root / "columns")
            ids, cluster_of, scenario_of = base.roster_maps(args.repo_root / fam.ROSTER["arm"])
            for arm, rows in arms.items():
                if set(rows) != set(ids):
                    raise ReadError(f"{arm}: the per-sample id set is not the frozen Fold B roster's")
            outputs_rows = load_outputs_rows(paths["outputs"])
            contacts = npc.trace_contacts(paths["trace"], budget_message)
            by_arm = npc.attribute(contacts, arm_contact_map(outputs_rows))
            result = read_stage(arms, ids, cluster_of, scenario_of, by_arm, contact_rows(outputs_rows, contacts), seed=args.seed, draws=args.draws,
                                missing=missing_columns(outputs_rows, contacts))
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
    note.write_text(render_markdown({"arms_nodes": result["arms"], "throughput": result.get("throughput")}) if args.stage == "smoke" else render_markdown(result),
                    encoding="utf-8")
    print(json.dumps({"written": str(out), "arm_words": {a: w["word"] for a, w in (result.get("arm_words") or {}).get("words", {}).items()}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
