#!/usr/bin/env python3
"""slurp_l338_column_read.py -- the preregistered READ of L338 (the decision-338 lever column on the Thinking core, TRAIN Fold B).

Package ``docs/readiness/2026-10-19-slurp-l338-lever-column-fold-b-v1/``. A sealed run whose Perception node carries ``sampling_variants`` (receipt
``saea-perception-branch-arms-v6``, level 2) holds, per row, four first-visit branches: ``l1-support`` (lever L1: 1 Perception contact and n = 5 Solver samples committed
by ``saea-commit-first-support-v1``), ``l2-union`` (lever L2: k = 4 Perception samples merged by ``saea-perception-candidate-union-v1``, one Solver contact), ``aa`` (the
in-flight A/A, replicate_of lock) and ``lock`` (the delivering arm, the 268-B lock form). Stages:

  columns  (run first, by ``scripts/flights/nx/l338_read.sh columns``) the OFFICIAL per-arm scoring: ``stage3_rollout_score.py --mode perception-branches`` renders each
           branch's first Solver column (the COMMITTED answer for ``l1-support``) plus the extra stream column ``l1-support-sample0`` (the branch's own sample 0) and scores
           each once, complete, with the registered official scorer (``slurp-slu-official-train``).
  smoke    the four-row smoke: per ARM and per NODE the decode cost from the sealed trace (completion tokens, finish reasons, cap hits, empty completions, forced closes,
           seconds), the measured arm mix against the registered one. Nothing is scored; the machine sign-off reads it.
  read     the full read, PAIRED per row against the delivering ``lock`` arm (utterance-cluster bootstrap, 10,000 draws, seed 20261018): official SLU-F1 and intent
           accuracy (scenario_action exact) per arm; every other arm and the twin minus ``lock`` with CI95; the arm words per LEVER; the per-scenario table (natural
           mixture and equal scenario); the per-node decode tables; the L1 secondaries (pure-filter delta = committed column minus its own sample 0, false fills removed,
           non-empty exact lost / gained, the support-count table); the L2 secondaries (union-size table, forced-close share by list size, and -- when ``--gold-intents`` is
           supplied -- merged-list recall against sample 0's, newly listed / lost gold and conversion by gold position); and the DISCORDANCE of every sampled stream against
           the twin's.

Arm words (preregistered; development numbers only; claims_benefit is false -- a nomination, never an admission). Floors (decision 190, n = 1,080) are 1.49 pp SLU and
0.65 pp intent. Both candidate arms COST MORE than the lock (l1: 5 Solver samples; l2: 4 Perception samples), so NO-RESOLVED-LOSS (a cheaper arm that loses nothing) does not
apply to either: the vocabulary is exactly NOMINATED / HARM / NEUTRAL. The twin ``aa`` is the in-flight A/A noise bar: reported beside the words, used in no word.

  L1 (``l1-support``; SLU primary, intent guard)
    NOMINATED  SLU delta CI95 lower bound >= 1.49 AND intent delta CI95 upper bound >= -0.65 (no resolved intent loss)
    HARM       SLU delta CI95 upper bound < -1.49, or intent delta CI95 upper bound < -0.65
    NEUTRAL    otherwise
  L2 (``l2-union``; intent primary, SLU guard)
    NOMINATED  intent delta CI95 lower bound >= 0.65 AND SLU delta CI95 upper bound >= -1.49 (no resolved SLU loss)
    HARM       intent delta CI95 upper bound < -0.65, or SLU delta CI95 upper bound < -1.49
    NEUTRAL    otherwise

The l1 branch's sample 0 is a second A/A (reported, used in no word). A NOMINATED arm goes to the 335 B Fold A column (not built here).

Optional offline inputs (nothing is read from them unless supplied): ``--gold-intents`` (a JSON ``{sample_id: gold intent id}`` for the L2 recall tables) and ``--n1-json`` (a
JSON ``{sample_id: N1}``, the entity-free share of the supplied exemplars, for the N1-gated L1 forms; N1 is unavailable in flight).

Model-free. Every sealed byte is opened read-only. NO utterance text, transcript, gold label, model output or reasoning text is printed or persisted: contact text is
reduced to booleans, counts and parse keys at read time and dropped.

    python -B scripts/analysis/slurp_l338_column_read.py --stage smoke --data-root $SPEECHRL_DATA_DIR
    python -B scripts/analysis/slurp_l338_column_read.py --stage read  --data-root $SPEECHRL_DATA_DIR
"""

from __future__ import annotations

import argparse
import dataclasses
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

import l338_family as fam  # noqa: E402
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
WORDS = ("NOMINATED", "HARM", "NEUTRAL")
SEED = 20261018
DRAWS = base.DEFAULT_DRAWS
INTENT_FIELD, SCORER = base.INTENT_FIELD, base.SCORER
ReadError = base.ReadError
CONTACTS_ZERO = base.CONTACTS_ZERO
ARMS = fam.ARM_ORDER
DELIVERING, TWIN, CANDIDATES = fam.DELIVERING, fam.TWIN, fam.CANDIDATE_ARMS
LEVER_OF = dict(fam.ARM_LEVER)
SLOTS = fam.THINK_SLOTS
COLUMN_SCORE_NAME = "arm-{arm}-{scorer}-scores.json"
SAMPLE0_SUFFIX = "-sample0"
WORD_TP, WORD_FP, WORD_FN = "slu_f1_word_tp", "slu_f1_word_fp", "slu_f1_word_fn"
ROW_RESULT_FIELDS = (WORD_TP, WORD_FP, WORD_FN)
LIST_SIZE_BINS = ("1", "2", "3", "other")


def stream_column_names() -> list[str]:
    """The extra official columns the render writes: one ``<branch>-sample0`` per ``solver_samples`` branch."""

    return [f"{a['arm_id']}{SAMPLE0_SUFFIX}" for a in fam.ARM_SPECS if a["axis"] == "solver_samples"]


# --------------------------------------------------------------------------- the sealed row -> branch -> contact map (ids only)


def _branch_view(branch: Mapping) -> dict:
    """One sealed branch record reduced to ids, statuses and counts (every note and answer text is dropped)."""

    sampling = branch.get("sampling") if isinstance(branch.get("sampling"), Mapping) else {}
    perception = sampling.get("perception_samples") if isinstance(sampling.get("perception_samples"), Mapping) else None
    solver = sampling.get("solver_samples") if isinstance(sampling.get("solver_samples"), Mapping) else None
    return {
        "branch_id": str(branch.get("branch_id")), "contact_id": branch.get("contact_id"), "solver_contact_id": branch.get("solver_contact_id"),
        "solver_absent": bool(branch.get("solver_absent")), "candidate_ids": [str(x) for x in branch.get("candidate_intent_ids") or []],
        "perception_samples": None if perception is None else {
            "merged_ids": [str(x) for x in perception.get("merged_candidate_ids") or []],
            "appended_ids": [str(x) for x in perception.get("appended_candidate_ids") or []],
            "samples": [{"contact_id": s.get("contact_id"), "candidate_ids": [str(x) for x in s.get("candidate_intent_ids") or []],
                         "note_parse_status": s.get("note_parse_status")} for s in perception.get("samples") or []]},
        "solver_samples": None if solver is None else {
            "samples": [{"contact_id": s.get("contact_id"), "parse_status": s.get("parse_status")} for s in solver.get("samples") or []],
            "outcome": dict(solver.get("outcome") or {})},
    }


def load_outputs_rows(path: Path) -> list[dict]:
    """The sealed outputs reduced to what the map needs (ids, statuses and counts only; every delivered text is dropped): per row the branch views and the
    ``{agent_contact_id: request_id}`` of every contact of every Solver visit (the key to the trace's response record)."""

    rows: list[dict] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            episode = row.get("native_episode_receipt") or {}
            branches = [_branch_view(b) for b in ((episode.get("perception_branches") or {}).get("branches")) or []]
            requests: dict[str, str] = {}
            for visit in episode.get("role_visits") or []:
                if isinstance(visit, Mapping) and visit.get("stage") == "solver":
                    for contact in ((visit.get("execution_receipt") or {}).get("contacts")) or []:
                        if isinstance(contact, Mapping) and contact.get("agent_contact_id") and contact.get("request_id"):
                            requests[str(contact["agent_contact_id"])] = str(contact["request_id"])
            rows.append({"sample_id": str(row["sample_id"]), "branches": branches, "requests": requests})
            row.clear()
    return rows


def arm_contact_map(outputs_rows: Sequence[Mapping]) -> dict[str, tuple[str, str]]:
    """``{agent_contact_id: (arm, node)}``: each branch's Perception and Solver contact, and every sampled Perception / Solver contact of a sampling axis."""

    mapping: dict[str, tuple[str, str]] = {}
    for row in outputs_rows:
        for branch in row["branches"]:
            arm = branch["branch_id"]
            if branch["contact_id"]:
                mapping[str(branch["contact_id"])] = (arm, "perception")
            if branch["solver_contact_id"]:
                mapping[str(branch["solver_contact_id"])] = (arm, "solver")
            for sample in (branch["perception_samples"] or {}).get("samples", []):
                if sample.get("contact_id"):
                    mapping[str(sample["contact_id"])] = (arm, "perception")
            for sample in (branch["solver_samples"] or {}).get("samples", []):
                if sample.get("contact_id"):
                    mapping[str(sample["contact_id"])] = (arm, "solver")
    return mapping


def list_size(branch: Mapping) -> int:
    """The candidate-list size the branch's Solver was shown: the merged list for a ``perception_samples`` branch, else its own note's candidate count."""

    merged = (branch["perception_samples"] or {}).get("merged_ids")
    return len(merged) if merged else len(branch["candidate_ids"])


def list_size_bin(size: int) -> str:
    return str(size) if size in (1, 2, 3) else "other"


def contact_rows(outputs_rows: Sequence[Mapping], contacts: Sequence[Mapping]) -> list[dict]:
    """Each branch's first-visit Solver contact (the column's sample 0) joined to its row: ``{sample_id, arm, list_size, forced_close, ...}`` (booleans and counts only)."""

    by_contact = {c["agent_contact_id"]: c for c in contacts if c.get("agent_contact_id")}
    out: list[dict] = []
    for row in outputs_rows:
        for branch in row["branches"]:
            c = by_contact.get(branch["solver_contact_id"])
            if c is None:
                continue
            out.append({"sample_id": row["sample_id"], "arm": branch["branch_id"], "list_size": list_size(branch), "forced_close": c.get("forced_close"),
                        "completion_tokens": c.get("completion_tokens"), "latency_seconds": c.get("latency_seconds")})
    return out


def missing_columns(outputs_rows: Sequence[Mapping], contacts: Sequence[Mapping], arms: Sequence[str] = ARMS) -> dict:
    """The arm columns a sealed row declares but whose Solver contact is absent from the trace (counts per arm), and rows lacking a declared arm."""

    present = {c.get("agent_contact_id") for c in contacts}
    by_arm: dict[str, int] = {arm: 0 for arm in arms}
    for row in outputs_rows:
        declared = {b["branch_id"] for b in row["branches"]}
        for arm in arms:
            if arm not in declared:
                by_arm[arm] += 1
        for b in row["branches"]:
            if b["solver_contact_id"] not in present and not b["solver_absent"]:
                by_arm[b["branch_id"]] = by_arm.get(b["branch_id"], 0) + 1
    return {"by_arm": by_arm, "total": sum(by_arm.values())}


# --------------------------------------------------------------------------- tables


def tables_by_arm(by_arm: Mapping[str, Sequence[Mapping]]) -> dict[str, dict]:
    """Per arm, the per-node decode table (``npc.arm_node_table``): every contact of the arm, sampled ones included, per node."""

    return {arm: npc.arm_node_table(by_arm[arm], arm, slots=SLOTS) for arm in sorted(by_arm)}


def _node_total_seconds(table: Mapping, node: str) -> float:
    cell = table.get(node)
    return float(cell["seconds_per_contact"]["mean"]) * int(cell["contacts"]) if cell else 0.0


def throughput_table(tables: Mapping[str, Mapping], rows: int) -> dict:
    """Seconds per row of the column flight (every contact of every arm, sampled ones included) in lock-row equivalents against the registered arm mix, and the
    slot-normalised GPU hours of a pass over ``rows`` rows. The lock row is the lock arm's Perception plus Solver contact seconds. Measured seconds only."""

    arms = {a: t for a, t in tables.items() if a != "unattributed"}
    per_arm = {a: sum(_node_total_seconds(t, n) for n in ("perception", "solver")) / max(rows, 1) for a, t in arms.items()}
    lock = arms.get(DELIVERING) or {}
    lock_row = (_node_total_seconds(lock, "perception") + _node_total_seconds(lock, "solver")) / max(rows, 1)
    per_row = sum(per_arm.values())
    contacts_per_row = {a: {n: (t[n]["contacts"] / max(rows, 1)) for n in t} for a, t in arms.items()}
    return {"slots": SLOTS, "seconds_per_row_by_arm": dict(sorted(per_arm.items())), "contacts_per_row_by_arm": contacts_per_row,
            "seconds_per_row_column": per_row, "seconds_per_row_lock": lock_row,
            "arm_mix_measured_rows": per_row / lock_row if lock_row else float("nan"), "arm_mix_registered_rows": fam.ARM_MIX_ROWS,
            "registered_rows_per_minute_full": fam.ROWS_PER_MINUTE_FULL, "registered_gpu_hours_ceiling": fam.CELLS["arm"]["gpu_hours"],
            "measured_gpu_hours_one_flight": (fam.ROWS * per_row / SLOTS / 3600.0) if per_row == per_row else float("nan")}


def smoke_stage(by_arm: Mapping[str, Sequence[Mapping]], *, rows: int = fam.SMOKE_ROWS, missing: Mapping | None = None) -> dict:
    tables = tables_by_arm(by_arm)
    missing = missing if missing is not None else {"total": 0, "by_arm": {}}
    return {"schema": SCHEMA_SMOKE, "status": "DECODE-COST PER ARM AND NODE (no score, no read)", "arms": tables, "throughput": throughput_table(tables, rows),
            "smoke_rows": rows, "absent_columns": missing["total"], "absent_columns_by_arm": dict(missing["by_arm"]),
            "unattributed_contacts": len(by_arm.get("unattributed", [])), "contacts": CONTACTS_ZERO}


def forced_by_list_size(contacts: Sequence[Mapping], arm: str) -> dict:
    """The arm's first-visit Solver forced-close share split by the size of the candidate list the Solver saw (1 / 2 / 3 / other)."""

    out: dict[str, dict] = {b: {"contacts": 0, "forced": 0, "no_wire": 0} for b in LIST_SIZE_BINS}
    for c in contacts:
        if c["arm"] != arm:
            continue
        cell = out[list_size_bin(c["list_size"])]
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
    """On the arm's empty-gold rows: how many were false-filled (word false positives > 0), overall and split by whether the arm's first Solver contact was a FORCED
    close (``None`` when the wire record is absent)."""

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


def _exact(row: Mapping[str, float]) -> bool:
    return row.get(WORD_FP, 0.0) == 0.0 and row.get(WORD_FN, 0.0) == 0.0


def l1_filter_effect(committed: Mapping[str, Mapping[str, float]], sample0: Mapping[str, Mapping[str, float]], ids: Sequence[str]) -> dict:
    """The L1 filter's effect read off the two official columns of the same branch (committed minus its own sample 0): empty-gold false fills removed (and added),
    non-empty-gold rows whose entity set was exact in sample 0 and is no longer (lost) and the reverse (gained)."""

    removed = added = lost = gained = 0
    for sid in ids:
        a, b = sample0[sid], committed[sid]
        if gold_empty(a):
            filled_a, filled_b = a.get(WORD_FP, 0.0) > 0.0, b.get(WORD_FP, 0.0) > 0.0
            removed += int(filled_a and not filled_b)
            added += int(filled_b and not filled_a)
        else:
            lost += int(_exact(a) and not _exact(b))
            gained += int(_exact(b) and not _exact(a))
    return {"empty_gold_false_fills_removed": removed, "empty_gold_false_fills_added": added,
            "nonempty_exact_lost": lost, "nonempty_exact_gained": gained, "rows": len(ids),
            "note": "committed column versus the branch's own sample 0 (the second A/A): official per-row word-level results"}


def discordance_table(arms: Mapping[str, Mapping[str, Mapping[str, float]]], ids: Sequence[str], *, delivering: str = DELIVERING, twin: str = TWIN) -> dict:
    """Per column other than the delivering one: how many rows' official per-row results differ from the lock's (SLU side: the word-level TP / FP / FN triple; intent side:
    the scenario_action exactness), and the SLU-discordant share as a multiple of the twin's. The twin ``aa`` is the baseline run-to-run variation (its request is
    identical to the lock's in every declared field), so a sampled arm is read against it, never against zero."""

    ref = arms[delivering]
    out: dict[str, dict] = {}
    for arm, rows in arms.items():
        if arm == delivering:
            continue
        slu = sum(1 for i in ids if any(rows[i].get(k) != ref[i].get(k) for k in ROW_RESULT_FIELDS))
        intent = sum(1 for i in ids if rows[i].get(INTENT_FIELD) != ref[i].get(INTENT_FIELD))
        either = sum(1 for i in ids if any(rows[i].get(k) != ref[i].get(k) for k in ROW_RESULT_FIELDS) or rows[i].get(INTENT_FIELD) != ref[i].get(INTENT_FIELD))
        n = len(ids)
        out[arm] = {"rows": n, "slu_discordant_rows": slu, "slu_discordant_share": slu / n if n else float("nan"),
                    "intent_discordant_rows": intent, "intent_discordant_share": intent / n if n else float("nan"),
                    "any_discordant_rows": either, "any_discordant_share": either / n if n else float("nan")}
    base_share = out.get(twin, {}).get("slu_discordant_share")
    for arm, cell in out.items():
        cell["slu_discordant_share_over_twin"] = (cell["slu_discordant_share"] / base_share) if base_share else float("nan")
        cell["is_twin"] = arm == twin
    return {"delivering": delivering, "twin": twin, "twin_slu_discordant_share": base_share, "arms": out,
            "note": "per-row official results compared with the lock's; the twin is the run-to-run variation at identical declared request fields"}


# --------------------------------------------------------------------------- per-stream discordance (parse keys from the trace; no text kept)


def answer_key(text: str | None) -> tuple:
    """A comparable key of one Solver answer text: ``(scenario, action, sorted (type, filler) pairs)``; ``("malformed",)`` for text the governed parser refuses and
    ``("absent",)`` for no text. The key is a tuple of short strings, never persisted as text."""

    if text is None:
        return ("absent",)
    from speech_aware_evidence_acquisition.reproduction.ojw.native_group_solver import parse_solver_answer_text

    parsed = parse_solver_answer_text(text)
    if parsed is None:
        return ("malformed",)
    return (parsed.scenario, parsed.action, tuple(sorted((e.type, e.filler) for e in parsed.entities)))


def trace_response_keys(trace: Path, wanted_request_ids: set[str]) -> dict[str, tuple]:
    """``{request_id: answer_key}`` for the wanted requests, read once from the sealed trace's MODEL_RESPONSE records (the text is reduced to its key and dropped)."""

    out: dict[str, tuple] = {}
    with Path(trace).open("rb") as handle:
        for raw in handle:
            if b'"MODEL_RESPONSE"' not in raw[:60]:
                continue
            record = json.loads(raw)
            rid = str(record.get("record_id", ""))
            if not rid.endswith("/response"):
                continue
            request_id = rid[: -len("/response")]
            if request_id in wanted_request_ids:
                text = (record.get("payload") or {}).get("text")
                out[request_id] = answer_key(text if isinstance(text, str) else None)
    return out


def solver_stream_keys(outputs_rows: Sequence[Mapping], response_keys: Mapping[str, tuple]) -> dict[str, dict[str, tuple]]:
    """``{stream name: {sample_id: answer key}}`` for every Solver stream: ``<arm>`` (the branch's first-visit contact) and, for a ``solver_samples`` branch, ``<arm>.s<j>``
    for each sample (``.s0`` is the branch contact itself)."""

    streams: dict[str, dict[str, tuple]] = defaultdict(dict)
    for row in outputs_rows:
        for branch in row["branches"]:
            arm = branch["branch_id"]
            request = row["requests"].get(str(branch["solver_contact_id"]))
            streams[arm][row["sample_id"]] = response_keys.get(request, ("absent",)) if request else ("absent",)
            for j, sample in enumerate((branch["solver_samples"] or {}).get("samples", [])):
                request = row["requests"].get(str(sample.get("contact_id")))
                streams[f"{arm}.s{j}"][row["sample_id"]] = response_keys.get(request, ("absent",)) if request else ("absent",)
    return dict(streams)


def perception_stream_keys(outputs_rows: Sequence[Mapping]) -> dict[str, dict[str, tuple]]:
    """``{stream name: {sample_id: candidate id list}}`` for every Perception stream: ``<arm>`` (the branch's own note) and, for a ``perception_samples`` branch,
    ``<arm>.s<j>`` for each sample plus ``<arm>.merged`` (the list the Solver was shown)."""

    streams: dict[str, dict[str, tuple]] = defaultdict(dict)
    for row in outputs_rows:
        for branch in row["branches"]:
            arm = branch["branch_id"]
            sampled = branch["perception_samples"]
            streams[arm][row["sample_id"]] = tuple((sampled["samples"][0]["candidate_ids"] if sampled and sampled["samples"] else branch["candidate_ids"]))
            if sampled:
                for j, sample in enumerate(sampled["samples"]):
                    streams[f"{arm}.s{j}"][row["sample_id"]] = tuple(sample["candidate_ids"])
                streams[f"{arm}.merged"][row["sample_id"]] = tuple(sampled["merged_ids"])
    return dict(streams)


def stream_discordance(streams: Mapping[str, Mapping[str, tuple]], ids: Sequence[str], *, delivering: str = DELIVERING, twin: str = TWIN) -> dict:
    """Per stream other than the lock's: the share of rows whose answer key (Solver) or candidate list (Perception) differs from the lock's, and that share as a
    multiple of the twin's. A stream missing a row counts that row as discordant."""

    ref = streams[delivering]
    out: dict[str, dict] = {}
    for name, rows in streams.items():
        if name == delivering:
            continue
        discordant = sum(1 for i in ids if rows.get(i) != ref.get(i))
        out[name] = {"rows": len(ids), "discordant_rows": discordant, "discordant_share": discordant / len(ids) if ids else float("nan")}
    base_share = out.get(twin, {}).get("discordant_share")
    for name, cell in out.items():
        cell["share_over_twin"] = (cell["discordant_share"] / base_share) if base_share else float("nan")
        cell["is_twin"] = name == twin
    return {"delivering": delivering, "twin": twin, "twin_discordant_share": base_share, "streams": out}


# --------------------------------------------------------------------------- the sampling tables (support counts, union size, gold-aware recall)


def support_count_table(sampling_rows: Sequence[Mapping]) -> dict:
    """The L1 support-count table from ``sampling-rows.json`` (ids and counts only): delivered entities by support count, base / delivered / dropped entity totals, rows
    that dropped at least one entity, rows emptied, the gate status counts and the sample parse-status counts."""

    by_support: Counter = Counter()
    gate: Counter = Counter()
    parse: Counter = Counter()
    base_total = delivered_total = rows_dropped = rows_emptied = rows = 0
    for row in sampling_rows:
        meta = (row.get("branches") or {}).get(_l1_arm(), {})
        if not meta or meta.get("solver_samples_absent"):
            continue
        rows += 1
        for entity in meta.get("entity_supports") or []:
            by_support[str(entity.get("support"))] += 1
        for status in meta.get("parse_status") or []:
            parse[str(status)] += 1
        gate[str((meta.get("gate") or {}).get("status"))] += 1
        base = meta.get("base_entity_count")
        delivered = int(meta.get("delivered_entity_count") or 0)
        if base is not None:
            base_total += base
            rows_dropped += int(base > delivered)
            rows_emptied += int(base > 0 and delivered == 0)
        delivered_total += delivered
    return {"rows": rows, "delivered_entities_by_support": dict(sorted(by_support.items())), "base_entities_total": base_total, "delivered_entities_total": delivered_total,
            "dropped_entities_total": base_total - delivered_total, "rows_with_a_drop": rows_dropped, "rows_emptied": rows_emptied,
            "gate_status_counts": dict(sorted(gate.items())), "sample_parse_status_counts": dict(sorted(parse.items())),
            "note": "base = the branch's sample-0 entity count; the gate reports n1-unavailable in flight"}


def _l1_arm() -> str:
    return next(a["arm_id"] for a in fam.ARM_SPECS if a["axis"] == "solver_samples")


def _l2_arm() -> str:
    return next(a["arm_id"] for a in fam.ARM_SPECS if a["axis"] == "perception_samples")


def union_size_table(sampling_rows: Sequence[Mapping]) -> dict:
    """The L2 union-size table from ``sampling-rows.json``: the merged list size distribution, the appended-candidate count distribution, the rows where the merge changed
    sample 0's list, and the per-sample list sizes."""

    merged_sizes: Counter = Counter()
    appended: Counter = Counter()
    sample_sizes: Counter = Counter()
    changed = rows = 0
    for row in sampling_rows:
        meta = ((row.get("branches") or {}).get(_l2_arm()) or {}).get("perception_samples")
        if not meta:
            continue
        rows += 1
        merged_sizes[str(len(meta.get("merged_candidate_ids") or []))] += 1
        appended[str(len(meta.get("appended_candidate_ids") or []))] += 1
        changed += int(bool(meta.get("appended_candidate_ids")))
        for sample in meta.get("sample_lists") or []:
            sample_sizes[str(len(sample.get("candidate_intent_ids") or []))] += 1
    return {"rows": rows, "merged_list_size": dict(sorted(merged_sizes.items())), "appended_count": dict(sorted(appended.items())),
            "rows_where_the_merge_changed_sample0": changed, "per_sample_list_size": dict(sorted(sample_sizes.items()))}


def l2_gold_tables(outputs_rows: Sequence[Mapping], gold: Mapping[str, str], l2_rows: Mapping[str, Mapping[str, float]], lock_rows: Mapping[str, Mapping[str, float]],
                   ids: Sequence[str]) -> dict:
    """The gold-aware L2 tables (needs ``--gold-intents``): recall of sample 0's list, of the merged list and of the lock's note; newly listed / lost gold; and the
    intent conversion (the scorer's scenario_action exactness) of the l2 branch and of the lock by the gold intent's position in the merged list."""

    l2 = _l2_arm()
    by_row = {row["sample_id"]: {b["branch_id"]: b for b in row["branches"]} for row in outputs_rows}
    sample0_hit = merged_hit = lock_hit = newly = lost = n = 0
    position: dict[str, dict] = {k: {"rows": 0, "l2_intent_correct": 0, "lock_intent_correct": 0} for k in ("1", "2", "3", "absent")}
    for sid in ids:
        branches = by_row.get(sid)
        if branches is None or sid not in gold or l2 not in branches or DELIVERING not in branches:
            continue
        g = gold[sid]
        n += 1
        sampled = branches[l2]["perception_samples"]
        s0 = sampled["samples"][0]["candidate_ids"] if sampled and sampled["samples"] else branches[l2]["candidate_ids"]
        merged = sampled["merged_ids"] if sampled else s0
        lock_note = branches[DELIVERING]["candidate_ids"]
        sample0_hit += int(g in s0)
        merged_hit += int(g in merged)
        lock_hit += int(g in lock_note)
        newly += int(g in merged and g not in s0)
        lost += int(g in s0 and g not in merged)
        key = str(merged.index(g) + 1) if g in merged else "absent"
        cell = position[key] if key in position else position["3"]
        cell["rows"] += 1
        cell["l2_intent_correct"] += int(l2_rows[sid].get(INTENT_FIELD, 0.0) == 1.0)
        cell["lock_intent_correct"] += int(lock_rows[sid].get(INTENT_FIELD, 0.0) == 1.0)
    return {"rows": n, "recall_sample0_list": sample0_hit / n if n else float("nan"), "recall_merged_list": merged_hit / n if n else float("nan"),
            "recall_lock_note": lock_hit / n if n else float("nan"), "gold_newly_listed_rows": newly, "gold_lost_rows": lost, "conversion_by_gold_position_in_merged_list": position}


def l1_forms(outputs_rows: Sequence[Mapping], answer_texts: Mapping[str, Sequence[str | None]], n1: Mapping[str, float] | None) -> dict:
    """The L1 secondary forms from the raw samples (counts only; the official SLU delta of a form is a zero-GPU composition by ``scripts/analysis/slurp_ver1_offline.py`` over
    the same custody): per form (``s2`` = the registered rule; ``s3``; ``filter_only`` = s2 without the gate; ``gate_only`` = no filter, gate on), the rows whose delivered entity
    list differs from sample 0's, the entities dropped and the rows emptied. A form that needs N1 reports ``n1-unavailable`` unless ``--n1-json`` supplied it."""

    from speech_aware_evidence_acquisition.rails.supply_variants import commit_solver_samples

    axis = fam.SAMPLING_GROUP.branch(_l1_arm()).solver_samples
    forms = {"s2_gated": {"min_support": 2, "gated": True}, "s3_gated": {"min_support": 3, "gated": True},
             "s2_filter_only": {"min_support": 2, "gated": False}, "gate_only": {"min_support": 1, "gated": True}}
    out: dict[str, dict] = {}
    for name, spec in forms.items():
        variant = dataclasses.replace(axis, min_support=spec["min_support"], n1_min=axis.n1_min if spec["gated"] else None,
                                      empty_votes_min=axis.empty_votes_min if spec["gated"] else None)
        changed = dropped = emptied = rows = unavailable = 0
        for row in outputs_rows:
            texts = answer_texts.get(row["sample_id"])
            if texts is None:
                continue
            rows += 1
            outcome = commit_solver_samples(variant, list(texts), n1=(n1 or {}).get(row["sample_id"]) if spec["gated"] else None)
            base_keys = answer_key(texts[0])
            base_entities = len(base_keys[2]) if len(base_keys) == 3 else 0
            delivered = len(outcome.entities)
            changed += int(delivered != base_entities)
            dropped += max(0, base_entities - delivered)
            emptied += int(base_entities > 0 and delivered == 0)
            unavailable += int(spec["gated"] and n1 is None)
        out[name] = {"rows": rows, "rows_with_a_changed_entity_list": changed, "entities_dropped": dropped, "rows_emptied": emptied,
                     "gate_n1_unavailable_rows": unavailable if spec["gated"] else 0}
    return out


# --------------------------------------------------------------------------- the words


def arm_words(contrast: Mapping, *, floor_slu_pp: float = fam.FLOOR_SLU_PP, floor_intent_pp: float = fam.FLOOR_INTENT_PP) -> dict:
    """The preregistered arm words per candidate (see the module docstring): NOMINATED / HARM / NEUTRAL for both levers, judged against the decision-190 floors. The twin
    ``aa`` is reported beside the words (its absolute offsets are the noise bar) and enters no word. NOMINATED and HARM cannot both hold: NOMINATED needs both upper bounds
    at or above minus their floors, and HARM needs one below."""

    versus = contrast["versus_delivering"]
    twin = versus.get(TWIN)
    o_slu = abs(twin["slu_f1"]["point_pp"]) if twin else 0.0
    o_int = abs(twin["intent"]["point_pp"]) if twin else 0.0
    words: dict[str, dict] = {}
    for arm in CANDIDATES:
        if arm not in versus:
            continue
        lever = LEVER_OF[arm]
        slu, intent = versus[arm]["slu_f1"], versus[arm]["intent"]
        c = {
            "slu_ci_lo_at_or_above_floor": slu["ci95_lo_pp"] >= floor_slu_pp,
            "slu_no_resolved_loss": slu["ci95_hi_pp"] >= -floor_slu_pp,
            "intent_ci_lo_at_or_above_floor": intent["ci95_lo_pp"] >= floor_intent_pp,
            "intent_no_resolved_loss": intent["ci95_hi_pp"] >= -floor_intent_pp,
        }
        if lever == "L1":
            primary_clears, guard_ok = c["slu_ci_lo_at_or_above_floor"], c["intent_no_resolved_loss"]
        else:
            primary_clears, guard_ok = c["intent_ci_lo_at_or_above_floor"], c["slu_no_resolved_loss"]
        if primary_clears and guard_ok:
            word = "NOMINATED"
        elif not c["slu_no_resolved_loss"] or not c["intent_no_resolved_loss"]:
            word = "HARM"
        else:
            word = "NEUTRAL"
        words[arm] = {"lever": lever, "primary": fam.PRIMARY_OF_LEVER[lever], "word": word, "next_step": "335 B Fold A column" if word == "NOMINATED" else None,
                      "slu_delta_pp": slu["point_pp"], "slu_ci95": [slu["ci95_lo_pp"], slu["ci95_hi_pp"]],
                      "intent_delta_pp": intent["point_pp"], "intent_ci95": [intent["ci95_lo_pp"], intent["ci95_hi_pp"]], "conditions": c}
    return {"twin_offset_slu_abs_pp": o_slu, "twin_offset_intent_abs_pp": o_int,
            "twin_offset_slu_point_pp": twin["slu_f1"]["point_pp"] if twin else None, "twin_offset_intent_point_pp": twin["intent"]["point_pp"] if twin else None,
            "external_reference_268b": {"twin_offset_slu_pp": fam.TWIN_OFFSET_268B_SLU_PP, "twin_offset_intent_pp": fam.TWIN_OFFSET_268B_INTENT_PP,
                                        "twin_offset_p31_slu_pp": fam.TWIN_OFFSET_P31_SLU_PP, "thinking_system_slu": fam.THINKING_SYSTEM_SLU,
                                        "thinking_system_intent": fam.THINKING_SYSTEM_INTENT},
            "floors_pp": {"slu": floor_slu_pp, "intent": floor_intent_pp}, "words": words}


def arm_secondaries(arms_rows: Mapping[str, Mapping[str, Mapping[str, float]]], contacts: Sequence[Mapping], tables: Mapping[str, Mapping]) -> dict:
    """The per-arm secondaries over the official columns: first-visit Solver forced-close share (overall and by candidate-list size), completion tokens, seconds per contact,
    empty-gold false fill (overall and by forced status) and the non-empty exact-set share."""

    out: dict[str, dict] = {}
    for arm, rows in arms_rows.items():
        if arm.endswith(SAMPLE0_SUFFIX):
            continue
        forced_map = {c["sample_id"]: c["forced_close"] for c in contacts if c["arm"] == arm}
        solver = (tables.get(arm) or {}).get("solver") or {}
        wire = solver.get("wire_records") or 0
        out[arm] = {
            "solver_forced_close_share": (solver.get("forced_closes", 0) / wire) if wire else float("nan"),
            "solver_forced_closes": solver.get("forced_closes"), "solver_wire_records": wire,
            "forced_close_by_list_size": forced_by_list_size(contacts, arm),
            "completion_tokens": solver.get("completion_tokens"), "seconds_per_contact": solver.get("seconds_per_contact"),
            "empty_gold_false_fill": empty_gold_false_fill(rows, lambda sid, m=forced_map: m.get(sid)),
            "nonempty_exact_set": nonempty_exact(rows),
        }
    return out


def read_stage(arms: Mapping[str, Mapping[str, Mapping[str, float]]], ids: Sequence[str], cluster_of: Callable[[str], str], scenario_of: Callable[[str], str],
               by_arm: Mapping[str, Sequence[Mapping]], contacts: Sequence[Mapping], *, seed: int = SEED, draws: int = DRAWS, missing: Mapping | None = None,
               stream_disc: Mapping | None = None, perception_disc: Mapping | None = None, sampling_rows: Sequence[Mapping] | None = None,
               gold: Mapping[str, str] | None = None, outputs_rows: Sequence[Mapping] | None = None, forms: Mapping | None = None) -> dict:
    """The full read: paired contrasts, the arm words, the per-scenario table, the discordances and every per-arm and per-lever secondary."""

    missing = missing if missing is not None else {"total": 0, "by_arm": {}}
    scored = {a: r for a, r in arms.items()}
    column_arms = {a: r for a, r in scored.items() if a in ARMS}
    contrast = npc.paired_contrasts(scored, ids, cluster_of, seed=seed, draws=draws, delivering=DELIVERING)
    tables = tables_by_arm(by_arm)
    l1, l2 = _l1_arm(), _l2_arm()
    result = {
        "schema": SCHEMA_READ, "status": "PREREGISTERED-READ (development numbers; never a test claim; claims_benefit false)",
        "arm_words": arm_words(contrast), "arm_words_vocabulary": list(WORDS), "levers": dict(LEVER_OF),
        "interval": {"kind": "utterance-cluster bootstrap", "draws": draws, "seed": seed, "level": "CI95"},
        "contrast": contrast, "per_scenario": npc.per_scenario_table(column_arms, ids, scenario_of, DELIVERING),
        "discordance": discordance_table(scored, ids), "stream_discordance": {"solver_answer": stream_disc, "perception_note": perception_disc},
        "secondaries": arm_secondaries(scored, contacts, tables), "arms_nodes": tables, "throughput": throughput_table(tables, len(ids)),
        "unattributed_contacts": len(by_arm.get("unattributed", [])), "absent_columns": missing["total"], "absent_columns_by_arm": dict(missing["by_arm"]),
        "scorer_parse_failures": {arm: sum(1 for row in rows.values() if row.get("parsed", 1.0) == 0.0) for arm, rows in sorted(scored.items())},
        "contacts": CONTACTS_ZERO,
    }
    if l1 + SAMPLE0_SUFFIX in scored:
        result["l1_pure_filter"] = {
            "delta_vs_own_sample0": npc.paired_contrasts({l1: scored[l1], l1 + SAMPLE0_SUFFIX: scored[l1 + SAMPLE0_SUFFIX]}, ids, cluster_of, seed=seed, draws=draws,
                                                          delivering=l1 + SAMPLE0_SUFFIX)["versus_delivering"][l1],
            "filter_effect": l1_filter_effect(scored[l1], scored[l1 + SAMPLE0_SUFFIX], ids),
            "sample0_vs_lock_second_aa": npc.paired_contrasts({l1 + SAMPLE0_SUFFIX: scored[l1 + SAMPLE0_SUFFIX], DELIVERING: scored[DELIVERING]}, ids, cluster_of, seed=seed,
                                                                draws=draws, delivering=DELIVERING)["versus_delivering"][l1 + SAMPLE0_SUFFIX],
            "note": "the branch's sample 0 is a second A/A: reported, used in no word"}
    if sampling_rows is not None:
        result["support_count_table"] = support_count_table(sampling_rows)
        result["union_size_table"] = union_size_table(sampling_rows)
    if forms is not None:
        result["l1_forms"] = forms
    if gold is not None and outputs_rows is not None:
        result["l2_gold_tables"] = l2_gold_tables(outputs_rows, gold, scored[l2], scored[DELIVERING], ids)
    else:
        result["l2_gold_tables"] = {"status": "not computed: no --gold-intents supplied"}
    return result


def render_markdown(result: Mapping) -> str:
    lines = [f"# {fam.READ_TITLE}", ""]
    aw = result.get("arm_words")
    if aw:
        lines += [f"In-flight twin offsets |o_SLU| = {aw['twin_offset_slu_abs_pp']:.2f} pp, |o_int| = {aw['twin_offset_intent_abs_pp']:.2f} pp "
                  f"(external 268-B reference SLU {aw['external_reference_268b']['twin_offset_slu_pp']:+.2f}).", "",
                  "| arm | lever | word | SLU d (pp) | SLU CI95 | intent d (pp) | intent CI95 | next step |", "| --- | --- | --- | ---: | --- | ---: | --- | --- |"]
        for arm, w in aw["words"].items():
            lines.append(f"| {arm} | {w['lever']} ({w['primary']}) | {w['word']} | {w['slu_delta_pp']:+.2f} | [{w['slu_ci95'][0]:+.2f}, {w['slu_ci95'][1]:+.2f}] | "
                         f"{w['intent_delta_pp']:+.2f} | [{w['intent_ci95'][0]:+.2f}, {w['intent_ci95'][1]:+.2f}] | {w['next_step'] or ''} |")
        lines.append("")
    c = result.get("contrast")
    if c:
        lines += ["| column | SLU-F1 | intent | SLU d vs lock (pp) | CI95 | intent d (pp) | CI95 | intent saves / harms |", "| --- | ---: | ---: | ---: | --- | ---: | --- | --- |"]
        for arm, lv in c["levels"].items():
            v = c["versus_delivering"].get(arm)
            if v is None:
                lines.append(f"| {arm} (delivering) | {lv['slu_f1_pct']:.2f} | {lv['intent_pct']:.2f} | | | | | |")
            else:
                s, i, t = v["slu_f1"], v["intent"], v["intent_saves_harms_ties_vs_delivering"]
                lines.append(f"| {arm} | {lv['slu_f1_pct']:.2f} | {lv['intent_pct']:.2f} | {s['point_pp']:+.2f} | [{s['ci95_lo_pp']:+.2f}, {s['ci95_hi_pp']:+.2f}] | "
                             f"{i['point_pp']:+.2f} | [{i['ci95_lo_pp']:+.2f}, {i['ci95_hi_pp']:+.2f}] | {t['saves']} / {t['harms']} |")
        lines.append("")
    pf = result.get("l1_pure_filter")
    if pf:
        d, e = pf["delta_vs_own_sample0"], pf["filter_effect"]
        lines += [f"L1 pure filter (committed minus its own sample 0): SLU {d['slu_f1']['point_pp']:+.2f} pp [{d['slu_f1']['ci95_lo_pp']:+.2f}, {d['slu_f1']['ci95_hi_pp']:+.2f}], "
                  f"intent {d['intent']['point_pp']:+.2f}; empty-gold false fills removed {e['empty_gold_false_fills_removed']} (added {e['empty_gold_false_fills_added']}); "
                  f"non-empty exact lost {e['nonempty_exact_lost']} / gained {e['nonempty_exact_gained']}.", ""]
    for key, title in (("solver_answer", "Solver answer"), ("perception_note", "Perception note")):
        block = ((result.get("stream_discordance") or {}).get(key))
        if block:
            lines += [f"{title} streams: discordance against `{block['delivering']}`; the twin `{block['twin']}` is the run-to-run baseline.", "",
                      "| stream | discordant rows | share | x twin |", "| --- | ---: | ---: | ---: |"]
            for name, d in sorted(block["streams"].items()):
                lines.append(f"| {name}{' (twin)' if d['is_twin'] else ''} | {d['discordant_rows']} | {d['discordant_share']:.3f} | {d['share_over_twin']:.2f} |")
            lines.append("")
    for key, title in (("support_count_table", "L1 support counts"), ("union_size_table", "L2 union sizes")):
        if result.get(key):
            lines += [f"{title}: `{json.dumps(result[key], sort_keys=True)}`", ""]
    sec = result.get("secondaries")
    if sec:
        lines += ["| arm | forced share | forced by list size 1 / 2 / 3 | tokens mean | s per contact | empty-gold false fill (forced / natural) | non-empty exact |",
                  "| --- | ---: | --- | ---: | ---: | --- | ---: |"]
        for arm, s in sec.items():
            b, e = s["forced_close_by_list_size"], s["empty_gold_false_fill"]
            tokens = (s["completion_tokens"] or {}).get("mean", float("nan"))
            seconds = (s["seconds_per_contact"] or {}).get("mean", float("nan"))
            lines.append(f"| {arm} | {s['solver_forced_close_share']:.3f} | {b['1']['forced_share']:.3f} / {b['2']['forced_share']:.3f} / {b['3']['forced_share']:.3f} | "
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
    """Per-column per-row official scores from ``arm-<column>-<scorer>-scores.json`` (written by stage3_rollout_score --mode perception-branches): the four arm columns
    and the stream columns (``<l1 arm>-sample0``) when present."""

    out: dict[str, dict] = {}
    for arm in [*ARMS, *stream_column_names()]:
        path = Path(analysis_columns) / COLUMN_SCORE_NAME.format(arm=arm, scorer=scorer_id)
        if not path.exists():
            raise ReadError(f"missing column score file {path}; run `l338_read.sh columns` first")
        out[arm] = base.rows_table(json.loads(path.read_text(encoding="utf-8")), scorer_id)
    return out


def _load_json(path: Path | None):
    return None if path is None else json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("smoke", "read"), required=True)
    parser.add_argument("--data-root", type=Path, default=Path(_data_root_env()))
    parser.add_argument("--repo-root", type=Path, default=_REPO)
    parser.add_argument("--analysis-root", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--draws", type=int, default=DRAWS)
    parser.add_argument("--gold-intents", type=Path, default=None, help="optional JSON {sample_id: gold intent id} for the L2 recall tables")
    parser.add_argument("--n1-json", type=Path, default=None, help="optional JSON {sample_id: N1} for the N1-gated L1 forms")
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
            arms = load_column_rows(root / "columns")
            ids, cluster_of, scenario_of = base.roster_maps(args.repo_root / fam.ROSTER["arm"])
            for arm, rows in arms.items():
                if set(rows) != set(ids):
                    raise ReadError(f"{arm}: the per-sample id set is not the frozen Fold B roster's")
            outputs_rows = load_outputs_rows(paths["outputs"])
            contacts = npc.trace_contacts(paths["trace"], budget_message)
            by_arm = npc.attribute(contacts, arm_contact_map(outputs_rows))
            wanted = {request for row in outputs_rows for request in row["requests"].values()}
            response_keys = trace_response_keys(paths["trace"], wanted)
            streams = solver_stream_keys(outputs_rows, response_keys)
            sampling_path = root / "columns" / "sampling-rows.json"
            sampling_rows = json.loads(sampling_path.read_text(encoding="utf-8"))["rows"] if sampling_path.exists() else None
            gold, n1 = _load_json(args.gold_intents), _load_json(args.n1_json)
            forms = l1_forms_from_trace(outputs_rows, paths["trace"], n1)
            result = read_stage(arms, ids, cluster_of, scenario_of, by_arm, contact_rows(outputs_rows, contacts), seed=args.seed, draws=args.draws,
                                missing=missing_columns(outputs_rows, contacts), stream_disc=stream_discordance(streams, ids),
                                perception_disc=stream_discordance(perception_stream_keys(outputs_rows), ids), sampling_rows=sampling_rows, gold=gold,
                                outputs_rows=outputs_rows, forms=forms)
            result["sealed_hashes"] = {n: base.sha256_file(paths[n]) for n in ("trace", "outputs", "manifest")}
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


def l1_forms_from_trace(outputs_rows: Sequence[Mapping], trace: Path, n1: Mapping[str, float] | None) -> dict:
    """Read the l1 branch's n raw Solver sample texts once from the trace and evaluate :func:`l1_forms` (texts live only inside this call)."""

    arm = _l1_arm()
    wanted: dict[str, tuple[str, int]] = {}
    for row in outputs_rows:
        for branch in row["branches"]:
            if branch["branch_id"] != arm or not branch["solver_samples"]:
                continue
            for j, sample in enumerate(branch["solver_samples"]["samples"]):
                request = row["requests"].get(str(sample.get("contact_id")))
                if request and not str(sample.get("parse_status")).startswith("finite-completion"):
                    wanted[request] = (row["sample_id"], j)
    texts: dict[str, list] = {}
    n = fam.SAMPLING_GROUP.branch(arm).solver_samples.n
    with Path(trace).open("rb") as handle:
        for raw in handle:
            if b'"MODEL_RESPONSE"' not in raw[:60]:
                continue
            record = json.loads(raw)
            rid = str(record.get("record_id", ""))
            request_id = rid[: -len("/response")] if rid.endswith("/response") else None
            if request_id in wanted:
                sid, j = wanted[request_id]
                texts.setdefault(sid, [None] * n)[j] = (record.get("payload") or {}).get("text")
    return l1_forms(outputs_rows, texts, n1)


if __name__ == "__main__":
    raise SystemExit(main())
