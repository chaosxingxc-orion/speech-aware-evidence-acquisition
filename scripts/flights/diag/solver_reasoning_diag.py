#!/usr/bin/env python3
"""solver_reasoning_diag.py -- the registered Solver reasoning diagnostic (owner ruling 330 A, package
``docs/readiness/2026-10-18-slurp-solver-reasoning-diagnostic-v1/``).

One small registered probe re-issues the SEALED budget-3072 Solver requests of about 40 rows of the sealed NX-T R2b column to the resident Thinking
server (``think-budget-np4``: budget 3,072 / cap 4,096, temperature 0, the sealed seed) and RETAINS the reasoning bytes under the data root only
(``<data root>/diagnostics/SAEA-SLURP-SOLVER-REASONING-DIAGNOSTIC-V1/reasoning/``), to classify the non-terminating reasoning (enumeration versus a
repetition loop). Decision 286 stays in force for every other cell: the exception is the ``ReasoningRetention`` object, which only a plan naming the
diagnostic run id can build (``core.reasoning_knobs``), and the stored wire message and every trace record remain the decision-286 projection.

Subcommands (all but ``run`` are offline and read sealed bytes read-only; none contacts a model, a server, a tokenizer or a GPU):

  select   compute the preregistered roster from the sealed trace, outputs and the per-row column scores (deterministic, fixed seed) and write it
  verify   re-read the sealed trace for the roster rows and prove each rebuilt request hashes to the sealed ``payload_sha256`` (and to the first-visit
           ``request_sha256``); with ``--render`` also render the exact wire body through the transport's own ``render_request`` (still no POST)
  run      the live re-issue (the coordinator launches it through ``scripts/flights/diag/solver_reasoning_diag.sh``); refuses unless every precondition holds

    python -B scripts/flights/diag/solver_reasoning_diag.py select --data-root $SPEECHRL_DATA_DIR --out ROSTER.json
    python -B scripts/flights/diag/solver_reasoning_diag.py verify --data-root $SPEECHRL_DATA_DIR
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
import re
import sys
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Iterable, Iterator, Mapping, Sequence

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

PACKAGE = "docs/readiness/2026-10-18-slurp-solver-reasoning-diagnostic-v1"
ROSTER_NAME, PLAN_NAME, PROTOCOL_NAME = "roster-v1.json", "execution-plan-v1.json", "protocol-v1.json"

RUN_ID = "SAEA-SLURP-SOLVER-REASONING-DIAGNOSTIC-V1"
READ_RUN_ID = "SAEA-SLURP-SOLVER-REASONING-DIAGNOSTIC-READ-V1"
SOURCE_RUN_ID = "SAEA-SLURP-STAGE3-NXT-R2B-SOLVER-BUDGET-FOLD-B-V1"
SOURCE_ATTEMPT_ID = "attempt-slurp-native-stage3-nxt-r2b-solver-budget-fold-b-generation-v1"
SOURCE_EXPERIMENT = "slurp-native-stage3-nxt-r2b-solver-budget-fold-b-v1"
SOURCE_READ_ID = "SAEA-SLURP-NXT-R2B-SOLVER-BUDGET-FOLD-B-READ-V1"
SPLIT_IDENTITY_HASH = "4407794c4a5d2e8883d93fdf242deb33c0987405d62e05a7d8416f5251a3484a"
EXPECTED_SESSION_ID = "serving-slurp-thinking-module-fold-b-np4-budget3072-max4096-v1"      # swap target think-budget-np4
ARM_DELIVERING, ARM_RAISED = "budget-3072", "solver-6144"
ROSTER_SCHEMA = "saea-solver-reasoning-diag-roster-v1"
RESULT_SCHEMA = "saea-solver-reasoning-diag-result-v1"
SEED = 20261018
CALL_CEILING = 56                                         # the plan's cap: 40 budget-3072 re-issues + 16 budget-6144 re-issues (+ 0 spare; one attempt)
GPU_HOURS_CEILING = 0.9
SUPPLIED_BIN_EDGE = 40                                    # supplied items < 40 or >= 40 (the coordinator's forced-close analysis bins)

#: (group id, quota). Order is the roster order. ``forced`` is the Solver's forced close (the reasoning budget was hit) at that arm.
GROUPS = (("forced-both", 16), ("forced-3072-only", 8), ("forced-6144-only", 8), ("natural-both", 8))
#: Stratification cells, fixed order: (supplied bin, empty gold).
STRATA = (("lt40", False), ("lt40", True), ("ge40", False), ("ge40", True))


class DiagError(RuntimeError):
    """A precondition is not met; refuse rather than guess."""


# --------------------------------------------------------------------------------------------------------------------- hashing


def canonical_request_bytes(payload: Mapping[str, object]) -> bytes:
    """The bytes the adapter hashes and hands the transport: ``core.model.request_types._canonical`` (imported, never re-implemented)."""

    from speech_aware_evidence_acquisition.core.model.request_types import _canonical

    return _canonical(payload)


def request_sha256(payload: Mapping[str, object]) -> str:
    return hashlib.sha256(canonical_request_bytes(payload)).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# --------------------------------------------------------------------------------------------------------------------- sealed paths


def sealed_paths(data_root: Path) -> dict[str, Path]:
    root = Path(data_root)
    run_dir = root / "runs" / SOURCE_RUN_ID / SOURCE_ATTEMPT_ID
    columns = root / "analysis" / SOURCE_READ_ID / "columns"
    return {
        "trace": run_dir / f"{SOURCE_RUN_ID}.trace.jsonl",
        "manifest": run_dir / f"{SOURCE_RUN_ID}.run-manifest.json",
        "first_visit": columns / "first-visit-rows.json",
        "scores_3072": columns / f"arm-{ARM_DELIVERING}-slurp-slu-official-train-scores.json",
        "scores_6144": columns / f"arm-{ARM_RAISED}-slurp-slu-official-train-scores.json",
    }


# --------------------------------------------------------------------------------------------------------------------- the trace


_WANTED_HEADS = (b'"MODEL_REQUEST"', b'"COST"')


def iter_trace(trace: Path, channels: Sequence[bytes] = _WANTED_HEADS) -> Iterator[tuple[str, str, Mapping[str, object]]]:
    """``(channel, record key, payload)`` for the wanted channels of a sealed trace, streamed (the channel is checked on the line head before parsing)."""

    with Path(trace).open("rb") as handle:
        for raw in handle:
            head = raw[:48]
            if not any(token in head for token in channels):
                continue
            record = json.loads(raw)
            yield str(record.get("channel")), str(record.get("record_id", "")).split("/", 1)[0], record.get("payload") or {}


def scan_trace_facts(trace: Path, solver_contacts: Mapping[str, str]) -> tuple[dict[str, dict], dict[str, dict]]:
    """One pass over the sealed trace. Returns ``(requests by contact id, costs by record key)`` for the Solver contacts named in ``solver_contacts``
    (contact id -> arm). A request fact keeps its hash, key, decoding facts and (budget-3072 arm only) the supplied evidence ids; no text."""

    requests: dict[str, dict] = {}
    costs: dict[str, dict] = {}
    for channel, key, payload in iter_trace(trace):
        if channel == "COST":
            costs[key] = {name: payload.get(name) for name in (
                "forced_close", "finish_reason", "completion_tokens", "prompt_tokens", "reasoning_chars", "reasoning_tokens",
                "reasoning_content_sha256", "latency_seconds")}
        elif channel == "MODEL_REQUEST":
            body = payload.get("payload") or {}
            history = body.get("history") or []
            contact = history[-1].get("contact_id") if history and isinstance(history[-1], Mapping) else None
            if contact not in solver_contacts:
                continue
            decoding = body.get("decoding_params") or {}
            supplied = body.get("supplied_evidence") or []
            fact = {
                "contact_id": contact, "request_key": key, "payload_sha256": payload.get("payload_sha256"),
                "sample_id": body.get("sample_id"), "audio_seconds": body.get("audio_seconds"), "supplied_items": len(supplied),
                "thinking_budget_tokens": decoding.get("thinking_budget_tokens"), "max_tokens": decoding.get("max_tokens"),
                "id_slot": decoding.get("id_slot"),
            }
            if solver_contacts[contact] == ARM_DELIVERING:
                fact["supplied_evidence_ids"] = [str(item.get("evidence_id")) for item in supplied if isinstance(item, Mapping)]
            requests[contact] = fact
    return requests, costs


def fetch_payloads(trace: Path, keys: Iterable[str]) -> dict[str, dict]:
    """The sealed MODEL_REQUEST records for the given record keys (``{key: {"payload": ..., "payload_sha256": ...}}``)."""

    wanted, found = set(keys), {}
    for channel, key, payload in iter_trace(trace, (b'"MODEL_REQUEST"',)):
        if channel == "MODEL_REQUEST" and key in wanted:
            found[key] = {"payload": payload["payload"], "payload_sha256": payload["payload_sha256"]}
    return found


# --------------------------------------------------------------------------------------------------------------------- the rows


def build_rows(first_visit: Mapping, requests: Mapping[str, dict], costs: Mapping[str, dict],
               scores: Mapping[str, Mapping[str, Mapping[str, object]]]) -> list[dict]:
    """One record per sample with both arms' sealed Solver facts. ``scores`` is ``{arm: {sample_id: per-sample official row}}``."""

    rows: list[dict] = []
    for entry in first_visit["rows"]:
        sample = str(entry["sample_id"])
        if entry.get("availability") != "first_solver_visit" or entry.get("later_solver_visits"):
            continue
        arms: dict[str, dict] = {}
        for branch in entry["branches"]:
            arm, contact = str(branch["branch_id"]), str(branch["contact_id"])
            fact = requests.get(contact)
            if fact is None:
                raise DiagError(f"{sample}: no sealed request for contact {contact}")
            if fact["payload_sha256"] != branch["request_sha256"]:
                raise DiagError(f"{sample}/{arm}: sealed trace payload hash differs from the first-visit request_sha256")
            cost = costs.get(fact["request_key"])
            if cost is None or cost.get("forced_close") is None:
                raise DiagError(f"{sample}/{arm}: no COST record or no forced-close fact")
            per = scores.get(arm, {}).get(sample)
            if per is None:
                raise DiagError(f"{sample}/{arm}: no per-sample official score")
            arms[arm] = {**{k: v for k, v in fact.items() if k not in ("supplied_evidence_ids",)}, "forced_close": bool(cost["forced_close"]),
                         **{k: cost.get(k) for k in ("finish_reason", "completion_tokens", "prompt_tokens", "reasoning_chars", "reasoning_tokens",
                                                     "reasoning_content_sha256")},
                         "response_text_sha256": branch.get("response_text_sha256"),
                         "slu_f1": per.get("slu_f1_f1"), "intent_exact": per.get("scenario_action_exact")}
            if arm == ARM_DELIVERING:
                gold_empty = (float(per.get("slot_f1_exact_tp", 0)) + float(per.get("slot_f1_exact_fn", 0))) == 0.0
                arms[arm]["gold_empty"] = gold_empty
                arms[arm]["supplied_evidence_ids"] = fact.get("supplied_evidence_ids", [])
        if set(arms) != {ARM_DELIVERING, ARM_RAISED}:
            raise DiagError(f"{sample}: expected both arms, found {sorted(arms)}")
        rows.append({"sample_id": sample, "arms": arms})
    return rows


def classify_row(row: Mapping) -> dict[str, object]:
    """The selection facts of one row: its group (forced status at both arms), supplied bin and empty-gold flag."""

    f3, f6 = bool(row["arms"][ARM_DELIVERING]["forced_close"]), bool(row["arms"][ARM_RAISED]["forced_close"])
    group = "forced-both" if f3 and f6 else "forced-3072-only" if f3 else "forced-6144-only" if f6 else "natural-both"
    supplied = int(row["arms"][ARM_DELIVERING]["supplied_items"])
    return {"group": group, "supplied_bin": "ge40" if supplied >= SUPPLIED_BIN_EDGE else "lt40",
            "gold_empty": bool(row["arms"][ARM_DELIVERING]["gold_empty"]), "supplied_items": supplied}


def rank_key(seed: int, group: str, sample_id: str) -> str:
    return hashlib.sha256(f"{seed}|{group}|{sample_id}".encode("utf-8")).hexdigest()


def select_roster(rows: Sequence[Mapping], *, seed: int = SEED, groups: Sequence[tuple[str, int]] = GROUPS) -> dict:
    """The preregistered selection. Per group the quota is split evenly over the four strata (supplied bin x empty gold); inside a stratum rows are
    ranked by ``sha256(seed|group|sample_id)``; a stratum that cannot fill its share is backfilled from the group's remaining rows in the same
    ranking order and the shortfall is recorded. Deterministic: the same rows and seed give the same roster."""

    classified = [(row, classify_row(row)) for row in rows]
    selected: list[dict] = []
    report: dict[str, dict] = {}
    for group, quota in groups:
        pool = [(row, facts) for row, facts in classified if facts["group"] == group]
        share = quota // len(STRATA)
        taken: list[tuple[Mapping, dict, str]] = []
        taken_ids: set[str] = set()
        cells: dict[str, dict] = {}
        for supplied_bin, gold_empty in STRATA:
            cell = [(r, f) for r, f in pool if f["supplied_bin"] == supplied_bin and f["gold_empty"] == gold_empty]
            ranked = sorted(cell, key=lambda item: rank_key(seed, group, item[0]["sample_id"]))
            for row, facts in ranked[:share]:
                taken.append((row, facts, "stratum"))
                taken_ids.add(row["sample_id"])
            cells[f"{supplied_bin}/{'empty-gold' if gold_empty else 'non-empty-gold'}"] = {
                "pool": len(cell), "share": share, "taken": min(share, len(cell)), "short": max(0, share - len(cell))}
        backfill = [(r, f) for r, f in sorted(pool, key=lambda item: rank_key(seed, group, item[0]["sample_id"])) if r["sample_id"] not in taken_ids]
        for row, facts in backfill[: max(0, quota - len(taken))]:
            taken.append((row, facts, "backfill"))
        report[group] = {"quota": quota, "pool": len(pool), "selected": len(taken), "cells": cells,
                         "backfilled": sum(1 for _r, _f, how in taken if how == "backfill")}
        order = {cell: index for index, cell in enumerate(STRATA)}
        taken.sort(key=lambda item: (order[(item[1]["supplied_bin"], item[1]["gold_empty"])], rank_key(seed, group, item[0]["sample_id"])))
        for row, facts, how in taken:
            selected.append({
                "sample_id": row["sample_id"], "group": group, "fill": how,
                "stratum": {"supplied_bin": facts["supplied_bin"], "gold_empty": facts["gold_empty"], "supplied_items": facts["supplied_items"]},
                "rank": rank_key(seed, group, row["sample_id"]), "arms": row["arms"],
            })
    return {"rows": selected, "selection_report": report, "seed": seed}


# --------------------------------------------------------------------------------------------------------------------- the sealed read


def _per_sample(path: Path) -> dict[str, Mapping[str, object]]:
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    return {str(item["sample_id"]): item for item in document["slurp-slu-official-train"]["per_sample"]}


def read_sealed(data_root: Path) -> tuple[list[dict], dict]:
    """Rows of the sealed R2b column with both arms' Solver facts, plus the source pins. Read-only; no model, server or GPU."""

    paths = sealed_paths(data_root)
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise DiagError(f"sealed inputs are missing: {missing}")
    first_visit = json.loads(paths["first_visit"].read_text(encoding="utf-8"))
    trace_sha = file_sha256(paths["trace"])
    if first_visit["source"]["raw_trace_sha256"] != trace_sha:
        raise DiagError("the sealed trace differs from the one the first-visit rows were rendered from")
    contacts = {str(b["contact_id"]): str(b["branch_id"]) for entry in first_visit["rows"] for b in entry["branches"]}
    requests, costs = scan_trace_facts(paths["trace"], contacts)
    scores = {ARM_DELIVERING: _per_sample(paths["scores_3072"]), ARM_RAISED: _per_sample(paths["scores_6144"])}
    rows = build_rows(first_visit, requests, costs, scores)
    pins = {"run_id": SOURCE_RUN_ID, "attempt_id": SOURCE_ATTEMPT_ID, "trace_sha256": trace_sha,
            "first_visit_rows_sha256": file_sha256(paths["first_visit"]), "manifest_sha256": first_visit["source"].get("manifest_sha256"),
            "config_hash": first_visit["source"].get("config_hash"),
            "scores_sha256": {ARM_DELIVERING: file_sha256(paths["scores_3072"]), ARM_RAISED: file_sha256(paths["scores_6144"])}}
    return rows, pins


def roster_document(selection: Mapping, pins: Mapping, rows_total: int) -> dict:
    rows = []
    for item in selection["rows"]:
        arm = item["arms"][ARM_DELIVERING]
        raised = item["arms"][ARM_RAISED]
        rows.append({
            "sample_id": item["sample_id"], "group": item["group"], "fill": item["fill"], "stratum": item["stratum"], "rank": item["rank"],
            "supplied_evidence_ids": arm["supplied_evidence_ids"],
            "reissue": {k: arm[k] for k in ("contact_id", "request_key", "payload_sha256", "id_slot", "audio_seconds", "thinking_budget_tokens", "max_tokens")},
            "sealed": {ARM_DELIVERING: {k: arm.get(k) for k in (
                "forced_close", "finish_reason", "completion_tokens", "prompt_tokens", "reasoning_chars", "reasoning_tokens", "reasoning_content_sha256",
                "response_text_sha256", "slu_f1", "intent_exact")},
                       ARM_RAISED: {k: raised.get(k) for k in (
                "forced_close", "finish_reason", "completion_tokens", "prompt_tokens", "reasoning_chars", "reasoning_tokens", "reasoning_content_sha256",
                "response_text_sha256", "slu_f1", "intent_exact")}},
            "raised_arm_request": {k: raised[k] for k in ("contact_id", "request_key", "payload_sha256", "id_slot", "audio_seconds", "thinking_budget_tokens",
                                                         "max_tokens")},
        })
    counts = Counter(row["group"] for row in rows)
    return {
        "schema": ROSTER_SCHEMA, "run_id": RUN_ID, "source": dict(pins), "seed": selection["seed"], "rows_in_column": rows_total,
        "selection_rule": ("per group the quota is split evenly over supplied bin (<40, >=40 items of the budget-3072 arm's Solver request) x empty gold; "
                           "rank = sha256(seed|group|sample_id); a short stratum is backfilled from the group in the same rank order"),
        "groups": {group: quota for group, quota in GROUPS}, "selected_counts": dict(counts), "selection_report": selection["selection_report"],
        "reissue_arm": ARM_DELIVERING, "raised_arm_reissue": True,
        "raised_arm_note": ("Coordinator decision 2 (ruling 330 A, both budgets): the sealed solver-6144 requests (budget 6144, max_tokens 7168) of the forced-both "
                            "rows are re-issued too, after the budget-3072 requests, on the same per-slot sequential workers. The resident np4 server admits them "
                            "(max_tokens is a request parameter; the server carries no -n cap). 40 + 16 = 56 contacts."),
        "rows": rows,
    }


def contacts_from_roster(roster: Mapping) -> list[dict]:
    """The contacts to send, in launch order: every row's budget-3072 request first, then (when the roster re-issues the raised arm) the budget-6144
    requests of the forced-both rows. Each contact carries the sealed facts of ITS arm; workers keep this order within a slot."""

    contacts: list[dict] = [{"sample_id": row["sample_id"], "group": row["group"], "arm": ARM_DELIVERING, "reissue": row["reissue"],
                             "sealed": row["sealed"]} for row in roster["rows"]]
    if roster.get("raised_arm_reissue"):
        for row in roster["rows"]:
            if row["group"] == "forced-both":
                contacts.append({"sample_id": row["sample_id"], "group": row["group"], "arm": ARM_RAISED, "reissue": row["raised_arm_request"],
                                 "sealed": row["sealed"]})
    return contacts


def roster_sample_ids(roster: Mapping) -> list[str]:
    return [row["sample_id"] for row in roster["rows"]]


# --------------------------------------------------------------------------------------------------------------------- verification


def verify_roster(roster: Mapping, data_root: Path, *, render: Callable[[bytes], Mapping] | None = None) -> dict:
    """Prove, from the sealed bytes, that each roster row's request is reconstructible: the trace payload re-hashes (with the adapter's own canonical
    serialisation) to the sealed ``payload_sha256``, which equals the roster's / first-visit's ``request_sha256``; the request is the budget-3072 arm's;
    and with ``render`` the exact wire body is built by the transport's own renderer (no POST). Nothing here prints request text."""

    paths = sealed_paths(data_root)
    contacts = contacts_from_roster(roster)
    keys = {c["reissue"]["request_key"]: c for c in contacts}
    found = fetch_payloads(paths["trace"], keys)
    results, failures = [], []
    for key, row in keys.items():
        sample = row["sample_id"]
        record = found.get(key)
        if record is None:
            failures.append(f"{sample}: sealed MODEL_REQUEST {key} not found")
            continue
        payload = record["payload"]
        rebuilt = request_sha256(payload)
        facts = {"sample_id": sample, "arm": row["arm"], "request_key": key, "rebuilt_sha256": rebuilt, "sealed_payload_sha256": record["payload_sha256"],
                 "roster_sha256": row["reissue"]["payload_sha256"]}
        facts["hash_match"] = rebuilt == record["payload_sha256"] == row["reissue"]["payload_sha256"]
        decoding = payload.get("decoding_params") or {}
        want_budget, want_cap = (3072, 4096) if row["arm"] == ARM_DELIVERING else (6144, 7168)
        facts["budget_matches_arm"] = decoding.get("thinking_budget_tokens") == want_budget and decoding.get("max_tokens") == want_cap
        facts["sample_matches"] = payload.get("sample_id") == sample
        facts["control_contact_matches"] = (payload.get("history") or [{}])[-1].get("contact_id") == row["reissue"]["contact_id"]
        if render is not None:
            body = render(canonical_request_bytes(payload))
            facts["wire_body_canonical_sha256"] = hashlib.sha256(
                json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
            facts["wire_body_budget"] = body.get("thinking_budget_tokens")
            facts["wire_body_max_tokens"] = body.get("max_tokens")
        ok = facts["hash_match"] and facts["budget_matches_arm"] and facts["sample_matches"] and facts["control_contact_matches"]
        if not ok:
            failures.append(f"{sample}: {json.dumps({k: v for k, v in facts.items() if isinstance(v, bool)})}")
        results.append(facts)
    return {"schema": "saea-solver-reasoning-diag-verify-v1", "rows": len(roster["rows"]), "contacts_checked": len(contacts), "verified": len(results) - len(failures),
            "failures": failures, "all_match": not failures and len(results) == len(contacts), "rendered": render is not None,
            "results": results, "contacts": 0}


# --------------------------------------------------------------------------------------------------------------------- the plan


def load_package_json(root: Path, name: str) -> dict:
    return json.loads((Path(root) / PACKAGE / name).read_text(encoding="utf-8"))


def check_registration(root: Path) -> tuple[dict, dict, dict]:
    """The roster, protocol and plan of the package, with every cross-binding checked: the plan names this run, profile and Fold B split; its protocol
    hash is the protocol file's sha256; the protocol pins the roster's sha256; the roster has its quota and respects the call ceiling."""

    from speech_aware_evidence_acquisition.contracts import ExecutionPlan

    package = Path(root) / PACKAGE
    roster, protocol, plan_doc = (load_package_json(root, n) for n in (ROSTER_NAME, PROTOCOL_NAME, PLAN_NAME))
    plan = ExecutionPlan(**plan_doc["execution_plan"]).validate()
    if plan.run_id != RUN_ID or plan.execution_profile != "bounded-discovery-probe" or plan.split_role != "discovery":
        raise DiagError("the execution plan does not name the diagnostic run, the bounded probe profile and the discovery split")
    if plan.split_identity_hash != SPLIT_IDENTITY_HASH:
        raise DiagError("the plan's split identity is not the Fold B discovery roster's")
    if plan.protocol_hash != file_sha256(package / PROTOCOL_NAME):
        raise DiagError("the plan's protocol_hash is not the sha256 of protocol-v1.json")
    if protocol["roster_sha256"] != file_sha256(package / ROSTER_NAME):
        raise DiagError("protocol-v1.json does not pin the roster file's sha256")
    if len(contacts_from_roster(roster)) > plan.planned_model_calls or plan.planned_model_calls > CALL_CEILING or plan.planned_gpu_hours >= 1.0:
        raise DiagError("the roster or the plan exceeds the registered ceilings (48 calls, < 1 GPU-h)")
    quota = {group: n for group, n in GROUPS}
    if roster["selected_counts"] != quota:
        raise DiagError(f"the roster does not hold the preregistered group counts {quota}")
    return roster, protocol, plan_doc


# --------------------------------------------------------------------------------------------------------------------- the live re-issue


def sealed_slot_groups(rows: Sequence[Mapping]) -> dict[object, list[Mapping]]:
    """Roster rows grouped by their SEALED ``id_slot``: each group is one sequential worker, so every sent payload is the sealed payload byte for byte."""

    groups: dict[object, list[Mapping]] = defaultdict(list)
    for row in rows:
        groups[row["reissue"]["id_slot"]].append(row)
    return dict(groups)


def result_row(row: Mapping, payload_sha: str, envelope: Mapping, latency: float) -> dict:
    """The statistics-only result of one contact: no reasoning text, no answer text. The reasoning-hash comparison is recorded either way (np4
    batching is not deterministic, so a mismatch is a finding, not an error)."""

    summary = envelope.get("reasoning") or {}
    retained = envelope.get("reasoning_retention") or {}
    arm = row.get("arm", ARM_DELIVERING)
    sealed = row["sealed"][arm]
    text = envelope.get("text") if isinstance(envelope.get("text"), str) else ""
    answer_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {
        "schema": RESULT_SCHEMA, "run_id": RUN_ID, "sample_id": row["sample_id"], "group": row["group"], "arm": arm,
        "request_sha256_sealed": row["reissue"]["payload_sha256"], "request_sha256_sent": payload_sha,
        "finish_reason": envelope.get("finish_reason"), "completion_tokens": (envelope.get("usage") or {}).get("completion_tokens"),
        "prompt_tokens": (envelope.get("usage") or {}).get("prompt_tokens"),
        "reasoning_chars": summary.get("reasoning_chars"), "reasoning_tokens": summary.get("reasoning_tokens"),
        "forced_close": summary.get("forced_close"), "reasoning_content_sha256": summary.get("reasoning_content_sha256"),
        "sealed_reasoning_content_sha256": sealed.get("reasoning_content_sha256"),
        "reasoning_hash_match": summary.get("reasoning_content_sha256") == sealed.get("reasoning_content_sha256"),
        "sealed_forced_close": sealed.get("forced_close"), "forced_close_reproduced": summary.get("forced_close") == sealed.get("forced_close"),
        "response_text_sha256": answer_sha, "sealed_response_text_sha256": sealed.get("response_text_sha256"),
        "answer_match": answer_sha == sealed.get("response_text_sha256"),
        "retained_relpath": retained.get("relpath"), "retained_sha256": retained.get("sha256"), "retained_chars": retained.get("chars"),
        "latency_seconds": round(latency, 3),
    }


def reissue_rows(rows: Sequence[Mapping], payloads: Mapping[str, Mapping], send: Callable[[bytes], bytes], out_dir: Path, *,
                 ceiling: int = CALL_CEILING, clock: Callable[[], float] = time.monotonic, workers: int | None = None) -> list[dict]:
    """Send the sealed requests: one sequential worker per sealed ``id_slot``. Every contact is counted before it is sent and the ceiling is a hard stop;
    the first failure stops its worker and is re-raised after the others finish their current contact (nothing is retried). Each answer text is written
    under ``out_dir/answers`` (the data root only) and one statistics row per contact is appended to ``out_dir/results.jsonl``."""

    out_dir = Path(out_dir)
    (out_dir / "answers").mkdir(parents=True, exist_ok=True)
    results_path = out_dir / "results.jsonl"
    lock, state = threading.Lock(), {"calls": 0, "stop": False}
    results: list[dict] = []
    errors: list[BaseException] = []

    def one(row: Mapping) -> None:
        record = payloads[row["reissue"]["request_key"]]
        request_bytes = canonical_request_bytes(record["payload"])
        sent_sha = hashlib.sha256(request_bytes).hexdigest()
        if sent_sha != row["reissue"]["payload_sha256"]:
            raise DiagError(f"{row['sample_id']}: the request to send does not hash to the sealed payload hash")
        with lock:
            if state["stop"]:
                return
            if state["calls"] + 1 > ceiling:
                raise DiagError(f"call ceiling {ceiling} reached")
            state["calls"] += 1
        started = clock()
        envelope = json.loads(send(request_bytes))
        latency = clock() - started
        answer = envelope.get("text") if isinstance(envelope.get("text"), str) else ""
        stem = re.sub(r"[^A-Za-z0-9._-]", "_", row["sample_id"]).strip(".") or "sample"
        suffix = "" if row.get("arm", ARM_DELIVERING) == ARM_DELIVERING else ".b6144"
        with open(out_dir / "answers" / f"{stem}{suffix}.txt", "xb") as handle:
            handle.write(answer.encode("utf-8"))
        entry = result_row(row, sent_sha, envelope, latency)
        with lock:
            results.append(entry)
            with results_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(entry, sort_keys=True) + "\n")

    def worker(items: Sequence[Mapping]) -> None:
        for row in items:
            if state["stop"]:
                return
            try:
                one(row)
            except BaseException as error:        # noqa: BLE001 -- first failure stops every worker, nothing is retried
                with lock:
                    state["stop"] = True
                    errors.append(error)
                return

    groups = sealed_slot_groups(rows)
    with ThreadPoolExecutor(max_workers=workers or max(1, len(groups))) as pool:
        for future in [pool.submit(worker, items) for items in groups.values()]:
            future.result()
    if errors:
        raise errors[0]
    return results


def summarize_results(results: Sequence[Mapping]) -> dict:
    by_group: dict[str, dict] = {}
    labels = [(group, group, ARM_DELIVERING) for group, _q in GROUPS] + [("forced-both@6144", "forced-both", ARM_RAISED)]
    for label, group, arm in labels:
        items = [r for r in results if r["group"] == group and r.get("arm", ARM_DELIVERING) == arm]
        by_group[label] = {
            "contacts": len(items), "reasoning_hash_match": sum(1 for r in items if r["reasoning_hash_match"]),
            "forced_close_reproduced": sum(1 for r in items if r["forced_close_reproduced"]),
            "answer_match": sum(1 for r in items if r["answer_match"]), "forced_close_now": sum(1 for r in items if r["forced_close"]),
            "finish_reasons": dict(Counter(str(r["finish_reason"]) for r in items)),
        }
    return {"contacts": len(results), "by_group": by_group}


def flight_present(data_root: Path) -> list[str]:
    """Reasons a diagnostic contact must not start: a flight lock on the data root."""

    reasons = []
    if (Path(data_root) / "locks" / "flight.lock").exists():
        reasons.append("flight.lock present")
    return reasons


def build_live(root: Path, data_root: Path, runtime_root: Path, plan, retention):
    """The live transport (retention armed) over the resident serving session, built the way the flight runtime and ``core.driver.cli`` build theirs:
    the gate for the plan's model touch (it demands the root-countersigned exposure row), the session receipt of the ONE resident session (which must be
    ``think-budget-np4``), the configured transport and the cell's composed values."""

    import functools

    from speech_aware_evidence_acquisition.contracts import FrozenCoreGate
    from speech_aware_evidence_acquisition.core.config import (
        compose, d1_evidence_supplement_relpath, d1_evidence_supplement_sha256, d1_media_supplement_relpath, d1_media_supplement_sha256,
        model_lock_key, model_materialization_root, resolve_runtime_receipt_path, runtime_receipt_relpath,
    )
    from speech_aware_evidence_acquisition.core.configured_transport import build_configured_transport
    from speech_aware_evidence_acquisition.core.model.transport import _llama_server_factory
    from speech_aware_evidence_acquisition.core.session import attach_session, load_runtime_receipt
    from speech_aware_evidence_acquisition.core.session.serving import SESSION_RECEIPT_NAME, find_resident_session

    experiment = json.loads((Path(root) / "configs" / "experiment" / f"{SOURCE_EXPERIMENT}.json").read_text(encoding="utf-8"))
    cell = next(c for c in experiment["cells"] if c["cell_id"] == SOURCE_EXPERIMENT)
    composed = compose(Path(root), cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], SOURCE_EXPERIMENT)
    values = composed.values
    resident = find_resident_session(Path(data_root))
    if resident is None or resident[1].get("session_id") != EXPECTED_SESSION_ID:
        raise DiagError(f"the resident serving session must be {EXPECTED_SESSION_ID} (swap target think-budget-np4)")
    configured_root = model_materialization_root(values)
    gate = FrozenCoreGate.for_study_repo(
        Path(root), Path(data_root), Path(runtime_root), runtime_receipt_relpath=runtime_receipt_relpath(values),
        expected_model_lock_key=model_lock_key(values),
        model_root=Path(configured_root) if configured_root is not None else None,
        d1_media_supplement_relpath=d1_media_supplement_relpath(values), d1_media_supplement_sha256=d1_media_supplement_sha256(values),
        d1_evidence_supplement_relpath=d1_evidence_supplement_relpath(values), d1_evidence_supplement_sha256=d1_evidence_supplement_sha256(values),
    )
    gate.assert_model_touch_allowed(plan)
    runtime_receipt = load_runtime_receipt(resolve_runtime_receipt_path(Path(root), values))
    session = attach_session(Path(resident[0]) / SESSION_RECEIPT_NAME, runtime_receipt=runtime_receipt, runtime_root=Path(runtime_root))
    transport = build_configured_transport(
        values, Path(data_root), repo_root=Path(root), session=session, runtime_receipt=runtime_receipt, runtime_root=Path(runtime_root),
        transport_factory=functools.partial(_llama_server_factory, reasoning_retention=retention),
    )
    return transport, composed


def compose_source_cell(root: Path):
    """The sealed R2b cell's composed config (the registered fragments at this checkout) and its model values."""

    from speech_aware_evidence_acquisition.core.config import compose

    experiment = json.loads((Path(root) / "configs" / "experiment" / f"{SOURCE_EXPERIMENT}.json").read_text(encoding="utf-8"))
    cell = next(c for c in experiment["cells"] if c["cell_id"] == SOURCE_EXPERIMENT)
    return compose(Path(root), cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], SOURCE_EXPERIMENT)


def offline_renderer(root: Path, data_root: Path) -> tuple[Callable[[bytes], Mapping], dict]:
    """The transport's own ``render_request`` over the SEALED run's pinned session receipt: the exact wire body of a sealed request, built with no
    server, no socket and no model (the precedent is ``analysis.context_configuration_source``). Also returns the composed config hash beside the
    sealed one, as a fact (a difference means a fragment changed since the flight; the render then proves shape only)."""

    from speech_aware_evidence_acquisition.core.config import model_materialization_root, resolve_runtime_receipt_path
    from speech_aware_evidence_acquisition.core.configured_transport import build_configured_transport
    from speech_aware_evidence_acquisition.core.session.receipt import SessionReceipt, load_runtime_receipt, resolve_pinned_session_receipt

    composed = compose_source_cell(root)
    manifest = json.loads(sealed_paths(data_root)["manifest"].read_text(encoding="utf-8"))
    pin = manifest["session_receipt"]
    session = SessionReceipt.from_json(json.loads(resolve_pinned_session_receipt(Path(pin["path"]), pin["sha256"])))
    values = composed.values
    runtime_root = model_materialization_root(values)
    if runtime_root is None:
        raise DiagError("the cell declares no model materialization root")
    from unittest import mock

    # The sealed flight's server is gone, and the transport's constructor asserts that its session pid is alive. ``render_request`` never touches
    # the server, so for this READ-ONLY renderer (and only here) the liveness assertion is stubbed while the transport is constructed; the
    # transport returned is never called, so no socket can open.
    with mock.patch("speech_aware_evidence_acquisition.core.model.transport.assert_session_alive", lambda *_a, **_k: None):
        transport = build_configured_transport(
            values, Path(data_root), repo_root=Path(root), session=session,
            runtime_receipt=load_runtime_receipt(resolve_runtime_receipt_path(Path(root), values)), runtime_root=Path(runtime_root))
    def render(raw: bytes) -> Mapping:
        with mock.patch("speech_aware_evidence_acquisition.core.model.transport.assert_session_alive", lambda *_a, **_k: None):
            return transport.render_request(raw)

    return render, {"composed_config_hash": composed.config_hash, "sealed_config_hash": manifest.get("config_hash"),
                                      "session_liveness_assertion": "stubbed-for-the-offline-renderer-only"}


def run_live(args: argparse.Namespace) -> int:
    from speech_aware_evidence_acquisition.contracts import ExecutionPlan
    from speech_aware_evidence_acquisition.core.reasoning_knobs import DIAGNOSTIC_RUN_ID, ReasoningRetention

    root, data_root = Path(args.repo_root).resolve(), Path(args.data_root)
    roster, _protocol, plan_doc = check_registration(root)
    plan = ExecutionPlan(**plan_doc["execution_plan"]).validate()
    reasons = flight_present(data_root)
    if reasons:
        raise DiagError("refused: " + "; ".join(reasons))
    retention = ReasoningRetention.from_plan(plan, data_root)
    out_dir = retention.diagnostic_root
    if (out_dir / "results.jsonl").exists() or retention.directory.exists():
        raise DiagError("refused: the diagnostic directory already holds an attempt (one attempt; supersede, never overwrite)")
    paths = sealed_paths(data_root)
    contacts = contacts_from_roster(roster)
    payloads = fetch_payloads(paths["trace"], [c["reissue"]["request_key"] for c in contacts])
    verified = verify_roster(roster, data_root)
    if not verified["all_match"]:
        raise DiagError(f"refused: the sealed requests do not all rebuild: {verified['failures'][:3]}")
    transport, composed = build_live(root, data_root, Path(args.runtime_root), plan, retention)
    if args.render_only:
        proof = verify_roster(roster, data_root, render=transport.render_request)
        print(json.dumps({"render_only": True, "config_hash": composed.config_hash, "all_match": proof["all_match"], "rows": proof["rows"]}))
        return 0 if proof["all_match"] else 1
    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    results = reissue_rows(contacts, payloads, transport, out_dir, ceiling=plan.planned_model_calls)
    summary = {"schema": "saea-solver-reasoning-diag-run-summary-v1", "run_id": DIAGNOSTIC_RUN_ID, "config_hash": composed.config_hash,
               "wall_seconds": round(time.monotonic() - started, 1), **summarize_results(results), "model_contacts": len(results)}
    (out_dir / "run-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    return 0


# --------------------------------------------------------------------------------------------------------------------- CLI


def _default_data_root() -> str:
    return os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "/home/chao/saea-data/speechrl-data"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    select = sub.add_parser("select", help="compute and write the preregistered roster (offline)")
    select.add_argument("--data-root", default=_default_data_root())
    select.add_argument("--out", type=Path, required=True)
    verify = sub.add_parser("verify", help="prove the roster's requests rebuild to the sealed hashes (offline)")
    verify.add_argument("--data-root", default=_default_data_root())
    verify.add_argument("--repo-root", default=str(REPO))
    verify.add_argument("--render", action="store_true", help="also render each exact wire body through the transport's own renderer (no POST)")
    run =sub.add_parser("run", help="the live re-issue (launched by the coordinator through the .sh wrapper)")
    run.add_argument("--data-root", default=_default_data_root())
    run.add_argument("--repo-root", default=str(REPO))
    run.add_argument("--runtime-root", default="/home/chao")
    run.add_argument("--render-only", action="store_true", help="build everything and render the wire bodies, but never POST")
    args = parser.parse_args(argv)
    if args.command == "select":
        rows, pins = read_sealed(Path(args.data_root))
        document = roster_document(select_roster(rows), pins, len(rows))
        Path(args.out).write_bytes((json.dumps(document, indent=1, sort_keys=True) + "\n").encode("utf-8"))
        print(json.dumps({"rows_in_column": len(rows), "selected_counts": document["selected_counts"], "selection_report": document["selection_report"]},
                         sort_keys=True))
        return 0
    if args.command == "verify":
        roster = load_package_json(Path(args.repo_root), ROSTER_NAME)
        render, config_facts = None, {}
        if args.render:
            render, config_facts = offline_renderer(Path(args.repo_root), Path(args.data_root))
        report = verify_roster(roster, Path(args.data_root), render=render)
        if config_facts:
            config_facts["sealed_config_hash"] = roster["source"]["config_hash"]
            config_facts["config_hash_match"] = config_facts["composed_config_hash"] == roster["source"]["config_hash"]
        report["config"] = config_facts
        print(json.dumps({k: v for k, v in report.items() if k != "results"}, sort_keys=True))
        if args.render:
            shapes = Counter(f"budget={r['wire_body_budget']},max_tokens={r['wire_body_max_tokens']}" for r in report["results"])
            print(json.dumps({"wire_body_shapes": dict(shapes)}, sort_keys=True))
        return 0 if report["all_match"] else 1
    return run_live(args)


if __name__ == "__main__":
    raise SystemExit(main())
