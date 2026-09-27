#!/usr/bin/env python3
"""Cell AGREE: the quantities the registered recipe reports BESIDE every verdict.

The registered paired read (READ row SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-PAIRED-ANALYSIS-V1, driver
``scripts/analysis/slurp_paired_roster_read.py``) writes the contrasts, the structural block and the
efficiency block, and declines the per-scenario table on a TRAIN construction roster. The recipe
(``docs/readiness/2026-09-26-slurp-stage3-agree-w1-fold-a-v1/analysis-recipe-v1.json``,
``reported_beside_every_verdict``) asks for six more things. This script computes them from sealed
bytes only and writes them to a NEW sibling directory ``<analysis root>/beside/``; it never opens the
paired driver's own outputs or anything under ``runs/`` for writing.

1. The per-scenario table, intent (``scenario_action_exact``) and official pooled SLU-F1, in the
   natural-mixture and the equal-scenario weighting. The stratum is the Fold A roster receipt's own
   per-item ``stratum`` (``docs/receipts/rosters/slurp-evo-fold-a-v2.json``); no scenario is inferred
   from model output. The same function as the VAR-1 family read's ``stage_per_scenario``.
2. The DELIVERY CHECK: on how many rows the flown Perception consumption carried the row's own gold
   intent boundary entry, per arm, against the offline production replication's prediction (receipt
   ``analysis/SAEA-SLURP-INTENT-AGREEMENT-PRODUCTION-REPLICATION-V1/replication-v1.json``) and against
   each arm's own prepared first-phase supply, row by row.
3. The CONVERSION: of the rows that NEWLY received their gold intent's boundary entry against the
   in-chain A/A, how many answered the intent correctly -- counts only, split by the A/A's own
   verdict, beside the CONV probe's m = 32 of 70.
4. The per-class table over the bad-case bank's INTENT-UNCOVERED and INTENT-COVERED rows (and the
   other bank classes beside them).
5. The measured token delta of the Perception block against the read's +1.4 tokens per row, and the
   per-role prompt / prefilled token accounting from each flight's own sealed wire responses
   (``usage.prompt_tokens``, ``timings.prompt_n`` = prefilled, ``timings.cache_n`` = cached).
6. The frontier row (decision 75): effect x prefilled tokens per row x GPU hours per 1,080 rows, and
   the A/A-versus-PLAN instrument check.

MODEL-FREE: zero model, tokenizer, encoder, embedder, scorer, server and network contacts. Gold enters
only as the bad-case bank's per-row gold intent (the scoring side, offline), compared in memory and
discarded. No utterance text, transcript, gold label string, intent name, value id or delivered answer
is printed or persisted: counts, rates, hashes and sample-id-free aggregates only.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import speech_aware_evidence_acquisition as _pkg  # noqa: E402

if not Path(_pkg.__file__).resolve().is_relative_to(SRC.resolve()):
    raise SystemExit(
        f"refusing: the imported package resolves to {_pkg.__file__}, not this checkout's src/"
    )

from speech_aware_evidence_acquisition.analysis.null_calibration import pooled_f1  # noqa: E402


def _import_paired_driver():
    """The registered paired driver's own loaders and estimators, imported from its path so the
    per-scenario numbers and the instrument contrast use the exact same code the READ row ran."""

    path = REPO_ROOT / "scripts" / "analysis" / "slurp_paired_roster_read.py"
    spec = importlib.util.spec_from_file_location("_saea_paired_roster_read", path)
    if spec is None or spec.loader is None:
        raise SystemExit("cannot import the paired roster read driver")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


PAIRED = _import_paired_driver()

SCHEMA = "saea-slurp-agree-beside-read-v1"
PACKAGE = Path("docs/readiness/2026-09-26-slurp-stage3-agree-w1-fold-a-v1")
RECIPE_ID = "slurp-stage3-agree-w1-fold-a-paired-analysis-v1"
ANALYSIS_ROOT = Path("analysis/SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-PAIRED-ANALYSIS-V1")
ROSTER = "docs/receipts/rosters/slurp-evo-fold-a-v2.json"
ROSTER_SHA256 = "1fe7908c31396774d7535fdf37bd791762215c324999d66ed7beb9e7b2f9033d"
SCORER = "slurp-slu-official-train"
FIELD = "scenario_action_exact"
BOUNDARY_PREFIX = "intent-boundary:"
SEED = 20260926
DRAWS = 10_000

BANK = "analysis/SLURP-PLAN-BAD-CASE-BANK-V1/bank.jsonl"
BANK_SHA256 = "26231b86b86f35251fed2b7d7c59bf33e8806b5ef71739b74bf9d5bc2b8a3ccf"
BANK_ROSTER = "train-fold-a"
REPLICATION = "analysis/SAEA-SLURP-INTENT-AGREEMENT-PRODUCTION-REPLICATION-V1/replication-v1.json"
REPLICATION_SHA256 = "7cd1f6d338731ea7b6eef34408e5d37453c852670900319445968ddc2a1dc624"
REPLICATION_ARM = "train-fold-a-plan"
CONV_ROSTER = "docs/readiness/2026-09-26-slurp-stage3-conv-fold-a-70-v1/roster-derivation-v1.json"
BANK_COLLAPSE = {"INTENT-UNCOVERED": "INTENT-WRONG", "INTENT-COVERED": "INTENT-WRONG"}

ARMS = {
    "arm": ("cell AGREE (w_agree 1.0, k 60, fuse 8-1-8)", "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1",
            "attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1"),
    "aa": ("the in-chain A/A (w_agree 0.0, k 60)", "SAEA-SLURP-STAGE3-AGREE-AA-FOLD-A-V1",
           "attempt-slurp-native-stage3-agree-aa-fold-a-generation-v1"),
    "plan": ("the sealed PLAN arm", "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1",
             "attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1"),
    "planr": ("the sealed PLANr replicate", "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-REPLICATE-V1",
              "attempt-slurp-native-default-plan-lock-replicate-train-fold-a-generation-v1"),
}
CONV = ("SAEA-SLURP-STAGE3-CONV-FOLD-A-70-V1", "attempt-slurp-native-stage3-conv-fold-a-70-generation-v1")
#: (left, right, role): the gating contrast, the context contrast and the instrument checks.
PAIRS = (("aa", "arm", "gating"), ("plan", "arm", "context"), ("plan", "aa", "instrument"),
         ("planr", "aa", "instrument"))
REGISTERED_TOKEN_DELTA = 1.4
OWN_NULL = {"h_slu": 1.2485, "h_intent": 0.9943}
CONV_M, CONV_N = 32, 70
CONTACTS_ZERO = {"model": 0, "tokenizer": 0, "encoder": 0, "embedder": 0, "scorer": 0,
                 "server": 0, "network": 0}


class BesideReadError(RuntimeError):
    pass


def digest(path: Path) -> str:
    measured = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(1 << 20):
            measured.update(chunk)
    return measured.hexdigest()


def load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def bare(value_id: str) -> str:
    return value_id.split("::", 1)[1] if "::" in value_id else value_id


def pct(num: float, den: float) -> float | None:
    return 100.0 * num / den if den else None


# --------------------------------------------------------------------------- sealed arms


def load_sealed_arm(data_root: Path, key: str) -> dict:
    label, run_id, attempt_id = ARMS[key]
    arm = PAIRED.load_arm(data_root, PAIRED.ArmSpec(label=label, run_id=run_id, attempt_id=attempt_id))
    if arm.manifest.get("status") != "COMPLETED":
        raise BesideReadError(f"{run_id}: manifest is not COMPLETED")
    if arm.scores_sha256 != arm.manifest["scores"]["sha256"]:
        raise BesideReadError(f"{run_id}: scores do not hash to the manifest pin")
    outputs_path = arm.artifact("outputs.jsonl")
    outputs_sha = digest(outputs_path)
    if outputs_sha != arm.manifest["outputs"]["sha256"]:
        raise BesideReadError(f"{run_id}: outputs do not hash to the manifest pin")
    receipts = arm.flight_receipts or {}
    seal = (receipts.get("stages") or {}).get("seal") or {}
    phases_path = arm.artifact("phases.json")
    phases_sha = digest(phases_path)
    if seal.get("phases_sha256") != phases_sha:
        raise BesideReadError(f"{run_id}: phase artefact does not hash to the seal pin")
    response_sha: dict[str, str] = {}
    with outputs_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                record = json.loads(line)
                response_sha[str(record["sample_id"])] = str(record.get("response_text_sha256"))
    return {
        "key": key,
        "label": label,
        "run_id": run_id,
        "attempt_id": attempt_id,
        "arm": arm,
        "rows": PAIRED._rows_table(arm, SCORER),
        "official": arm.scores[SCORER]["aggregate"]["official"],
        "response_text_sha256": response_sha,
        "phases_path": phases_path,
        "receipts": receipts,
        "hashes": {
            "run_manifest": arm.manifest_sha256,
            "scores": arm.scores_sha256,
            "outputs": outputs_sha,
            "phases": phases_sha,
            "generation_manifest": arm.generation_manifest_sha256,
            "flight_receipts": digest(arm.flight_receipts_path),
        },
        "study_commit": arm.manifest.get("study_commit"),
    }


def phase_rows(phases_path: Path) -> dict[str, dict]:
    """Per row: the delivered boundary item set, the role of every request id, dispositions."""

    document = load_json(phases_path)
    if document.get("schema") != "saea-flight-phase-summaries-v1" or len(document["phases"]) != 1:
        raise BesideReadError(f"{phases_path}: unexpected phase artefact shape")
    out: dict[str, dict] = {}
    for result in document["phases"][0]["results"]:
        sample_id = str(result["sample_id"])
        boundary: set[str] = set()
        outcomes: dict[str, str] = {}
        for record in (result.get("consumption") or {}).get("records") or ():
            item = bare(str(record.get("supplied_item_id") or ""))
            if item.startswith(BOUNDARY_PREFIX):
                boundary.add(item)
                outcomes[item] = str(record.get("outcome"))
        kinds = Counter(
            bare(str(record.get("supplied_item_id") or "")).split(":", 1)[0]
            for record in (result.get("consumption") or {}).get("records") or ()
        )
        roles: dict[str, tuple[str, int]] = {}
        receipt = result.get("native_episode_receipt") or {}
        for index, visit in enumerate(receipt.get("role_visits") or ()):
            for contact in (visit.get("execution_receipt") or {}).get("contacts") or ():
                roles[str(contact["request_id"])] = (str(visit["role_id"]), index)
        out[sample_id] = {"boundary": boundary, "outcomes": outcomes, "roles": roles, "kinds": kinds}
    return out


def supply_kinds(phases: dict[str, dict], ids: list[str]) -> dict:
    """Mean supplied items per row by kind (intent-boundary, value, slot-contract, ...): the
    downstream roles read the acquired supply, so a change in which intents Perception proposes
    moves what later phases are sent."""

    totals = Counter()
    for s in ids:
        totals.update(phases[s]["kinds"])
    return {kind: totals[kind] / len(ids) for kind in sorted(totals)}


# --------------------------------------------------------------------------- 1. per scenario


def per_scenario(left: dict, right: dict, strata: dict[str, str], ids: list[str]) -> dict:
    by_scenario: dict[str, list[str]] = defaultdict(list)
    for sample_id in ids:
        by_scenario[strata[sample_id]].append(sample_id)
    slu_groups = PAIRED.MICRO_METRICS["slu_f1_micro"]
    cells: dict[str, dict] = {}
    for scenario in sorted(by_scenario):
        members = sorted(by_scenario[scenario])
        l_int = [left["rows"][s][FIELD] for s in members]
        r_int = [right["rows"][s][FIELD] for s in members]
        l_slu = 100 * pooled_f1(left["rows"], members, slu_groups)
        r_slu = 100 * pooled_f1(right["rows"], members, slu_groups)
        cells[scenario] = {
            "n": len(members),
            "left_intent_pct": 100 * statistics.fmean(l_int),
            "right_intent_pct": 100 * statistics.fmean(r_int),
            "intent_delta_pp": 100 * (statistics.fmean(r_int) - statistics.fmean(l_int)),
            "intent_saves": sum(1 for a, b in zip(l_int, r_int) if b > a),
            "intent_harms": sum(1 for a, b in zip(l_int, r_int) if b < a),
            "left_slu_pct": l_slu,
            "right_slu_pct": r_slu,
            "slu_delta_pp": r_slu - l_slu,
        }
    scenarios = sorted(cells)
    natural_slu = 100 * (pooled_f1(right["rows"], ids, slu_groups) - pooled_f1(left["rows"], ids, slu_groups))
    natural_intent = 100 * (statistics.fmean(right["rows"][s][FIELD] for s in ids)
                            - statistics.fmean(left["rows"][s][FIELD] for s in ids))
    return {
        "left": left["label"],
        "right": right["label"],
        "per_scenario": cells,
        "weightings": {
            "natural_mixture": {
                "intent_delta_pp": natural_intent,
                "slu_delta_pp": natural_slu,
                "definition": "pooled over all roster rows in their own mixture (the headline contrast)",
            },
            "equal_scenario": {
                "intent_delta_pp": statistics.fmean(cells[s]["intent_delta_pp"] for s in scenarios),
                "slu_delta_pp": statistics.fmean(cells[s]["slu_delta_pp"] for s in scenarios),
                "definition": "unweighted mean of the per-scenario deltas over the strata",
            },
        },
        "scenarios_intent_up_down_flat": [
            sum(1 for s in scenarios if cells[s]["intent_delta_pp"] > 0),
            sum(1 for s in scenarios if cells[s]["intent_delta_pp"] < 0),
            sum(1 for s in scenarios if cells[s]["intent_delta_pp"] == 0),
        ],
        "scenarios_slu_up_down_flat": [
            sum(1 for s in scenarios if cells[s]["slu_delta_pp"] > 0),
            sum(1 for s in scenarios if cells[s]["slu_delta_pp"] < 0),
            sum(1 for s in scenarios if cells[s]["slu_delta_pp"] == 0),
        ],
    }


# --------------------------------------------------------------------------- 2-4. delivery


def load_bank(data_root: Path, ids: list[str]) -> dict[str, dict]:
    path = data_root / BANK
    if digest(path) != BANK_SHA256:
        raise BesideReadError("the bad-case bank does not hash to its pin")
    wanted = set(ids)
    rows: dict[str, dict] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry.get("roster") != BANK_ROSTER or entry.get("sample_id") not in wanted:
                continue
            rows[str(entry["sample_id"])] = {
                "plan_class": entry["plan_class"],
                "gold_id": f"{BOUNDARY_PREFIX}{entry['gold_intent']}" if entry.get("gold_intent") else None,
            }
    if sorted(rows) != sorted(ids) or any(r["gold_id"] is None for r in rows.values()):
        raise BesideReadError("the bank does not carry a gold intent for every roster row")
    return rows


def delivery(arms: dict, phases: dict, bank: dict, ids: list[str], data_root: Path, repo: Path) -> dict:
    delivered = {k: {s: bank[s]["gold_id"] in phases[k][s]["boundary"] for s in ids} for k in phases}
    widths = {k: dict(sorted(Counter(len(phases[k][s]["boundary"]) for s in ids).items())) for k in phases}

    # Each arm's flown boundary set against its own prepared first-phase supply, row by row.
    prepared_check: dict[str, dict] = {}
    for key in phases:
        pins = (arms[key]["receipts"]["stages"]["preflight"].get("prepared_artifacts")) or []
        pin = next(p for p in pins if p.get("key") == "prepared_phase_supply")
        path = data_root / pin["relpath"]
        if digest(path) != pin["sha256"]:
            raise BesideReadError(f"{key}: the flown prepared supply does not hash to its preflight pin")
        values = load_json(path)["output"]["values"]["perception"]
        equal = sum(
            1 for s in ids
            if {bare(v) for v in values[s] if bare(v).startswith(BOUNDARY_PREFIX)} == phases[key][s]["boundary"]
        )
        prepared_check[key] = {"prepared_relpath": pin["relpath"], "prepared_sha256": pin["sha256"],
                               "rows_flown_set_equals_prepared_set": equal, "rows": len(ids)}

    # Per bank class (collapsed like the replication) and per plan class.
    by_class: dict[str, Counter] = defaultdict(Counter)
    by_plan_class: dict[str, Counter] = defaultdict(Counter)
    for s in ids:
        plan_class = bank[s]["plan_class"]
        klass = BANK_COLLAPSE.get(plan_class, plan_class)
        for bucket in (by_class[klass], by_plan_class[plan_class]):
            bucket["rows"] += 1
            for key in phases:
                bucket[f"{key}_delivered"] += int(delivered[key][s])
            bucket["newly_delivered_arm_vs_aa"] += int(delivered["arm"][s] and not delivered["aa"][s])
            bucket["newly_lost_arm_vs_aa"] += int(delivered["aa"][s] and not delivered["arm"][s])

    replication_path = data_root / REPLICATION
    if digest(replication_path) != REPLICATION_SHA256:
        raise BesideReadError("the production-replication receipt does not hash to its pin")
    predicted = load_json(replication_path)["arms"][REPLICATION_ARM]["delivery"]
    comparison: dict[str, dict] = {}
    for klass, pred in sorted(predicted["classes"].items()):
        flown = by_class.get(klass, Counter())
        comparison[klass] = {
            "rows": pred["rows"], "flown_rows": flown["rows"],
            "predicted_base": pred["base_fused"], "flown_aa": flown["aa_delivered"],
            "flown_plan": flown["plan_delivered"],
            "predicted_treat": pred["treat_fused"], "flown_arm": flown["arm_delivered"],
            "predicted_treat_pct": pred["treat_fused_pct"], "flown_arm_pct": pct(flown["arm_delivered"], flown["rows"]),
        }
    split_comparison: dict[str, dict] = {}
    for plan_class, pred in sorted(predicted["plan_class_split"].items()):
        flown = by_plan_class.get(plan_class, Counter())
        split_comparison[plan_class] = {
            "rows": pred["rows"],
            "predicted_newly_delivered": pred["newly_delivered"],
            "flown_newly_delivered": flown["newly_delivered_arm_vs_aa"],
            "predicted_newly_lost": pred["newly_lost"],
            "flown_newly_lost": flown["newly_lost_arm_vs_aa"],
        }

    conv = load_json(repo / CONV_ROSTER)["roster"]
    conv_ids = [str(s) for s in conv["ids"]]
    conv_lost = [str(s) for s in conv.get("newly_lost_ids") or ()]
    conv_rows = {
        "predicted_newly_delivered_rows": len(conv_ids),
        "flown_newly_delivered_among_them": sum(1 for s in conv_ids if delivered["arm"][s] and not delivered["aa"][s]),
        "flown_arm_delivered_among_them": sum(1 for s in conv_ids if delivered["arm"][s]),
        "predicted_newly_lost_rows": len(conv_lost),
        "flown_newly_lost_among_them": sum(1 for s in conv_lost if delivered["aa"][s] and not delivered["arm"][s]),
    }
    totals = {key: sum(delivered[key].values()) for key in phases}
    newly = [s for s in ids if delivered["arm"][s] and not delivered["aa"][s]]
    lost = [s for s in ids if delivered["aa"][s] and not delivered["arm"][s]]
    gold_outcome = Counter(phases["arm"][s]["outcomes"].get(bank[s]["gold_id"]) for s in newly)
    return {
        "delivered": delivered,
        "newly": newly,
        "lost": lost,
        "conv_ids": conv_ids,
        "report": {
            "definition": (
                "delivered = the row's own gold intent boundary value id is among the boundary items of the "
                "flown Perception consumption records (phases.json), the CONV read's and the replication's "
                "sealed-side definition"
            ),
            "rows": len(ids),
            "delivered_rows": totals,
            "aa_equals_plan_on_every_row": all(delivered["aa"][s] == delivered["plan"][s] for s in ids),
            "boundary_items_per_row_histogram": widths,
            "flown_vs_own_prepared_supply": prepared_check,
            "by_collapsed_class_vs_replication": comparison,
            "by_plan_class_vs_replication": split_comparison,
            "conv_roster_rows": conv_rows,
            "newly_delivered_arm_vs_aa": len(newly),
            "newly_lost_arm_vs_aa": len(lost),
            "gold_entry_consumption_outcome_on_newly_delivered_rows": dict(sorted(Counter(
                str(k) for k in gold_outcome.elements()).items())),
        },
    }


def transitions(arms: dict, ids: list[str]) -> dict:
    l_rows, r_rows = arms["aa"]["rows"], arms["arm"]["rows"]
    counts = Counter()
    for s in ids:
        counts[(int(l_rows[s][FIELD]), int(r_rows[s][FIELD]))] += 1
    return {"wrong_to_right": counts[(0, 1)], "right_to_wrong": counts[(1, 0)],
            "right_to_right": counts[(1, 1)], "wrong_to_wrong": counts[(0, 0)], "rows": len(ids)}


def conversion(arms: dict, deliv: dict, bank: dict, ids: list[str], data_root: Path) -> dict:
    d = deliv["delivered"]
    groups = {
        "newly_delivered (arm yes, A/A no)": [s for s in ids if d["arm"][s] and not d["aa"][s]],
        "newly_lost (arm no, A/A yes)": [s for s in ids if d["aa"][s] and not d["arm"][s]],
        "delivered_in_both": [s for s in ids if d["aa"][s] and d["arm"][s]],
        "delivered_in_neither": [s for s in ids if not d["aa"][s] and not d["arm"][s]],
    }
    table = {name: transitions(arms, members) for name, members in groups.items()}
    newly = groups["newly_delivered (arm yes, A/A no)"]
    aa_wrong_newly = [s for s in newly if not arms["aa"]["rows"][s][FIELD]]
    both_aa_wrong = [s for s in groups["delivered_in_both"] if not arms["aa"]["rows"][s][FIELD]]

    # The CONV probe's own 70 rows, flown under the same treatment in a different flight.
    conv_run, conv_attempt = CONV
    conv_dir = data_root / "runs" / conv_run / conv_attempt
    conv_manifest = load_json(conv_dir / f"{conv_run}.run-manifest.json")
    conv_scores_path = conv_dir / f"{conv_run}.scores.json"
    if digest(conv_scores_path) != conv_manifest["scores"]["sha256"]:
        raise BesideReadError("the CONV scores do not hash to their manifest pin")
    conv_rows = {str(r["sample_id"]): float(r[FIELD]) for r in load_json(conv_scores_path)[SCORER]["per_sample"]}
    conv_ids = deliv["conv_ids"]
    if sorted(conv_rows) != sorted(conv_ids):
        raise BesideReadError("the CONV per-sample rows are not the CONV roster")
    arm_correct_on_conv = sum(1 for s in conv_ids if arms["arm"]["rows"][s][FIELD])
    agree = sum(1 for s in conv_ids if bool(arms["arm"]["rows"][s][FIELD]) == bool(conv_rows[s]))
    by_class = Counter(bank[s]["plan_class"] for s in newly)
    return {
        "by_delivery_transition": table,
        "newly_delivered_rows": len(newly),
        "newly_delivered_by_plan_class": dict(sorted(by_class.items())),
        "newly_delivered_arm_intent_correct": sum(1 for s in newly if arms["arm"]["rows"][s][FIELD]),
        "newly_delivered_aa_wrong": len(aa_wrong_newly),
        "conversion_m": sum(1 for s in aa_wrong_newly if arms["arm"]["rows"][s][FIELD]),
        "conversion_rate_pct": pct(sum(1 for s in aa_wrong_newly if arms["arm"]["rows"][s][FIELD]), len(aa_wrong_newly)),
        "conv_probe_reference": {"m": CONV_M, "n": CONV_N, "rate_pct": 100 * CONV_M / CONV_N},
        "on_the_conv_probe_rows": {
            "rows": len(conv_ids),
            "arm_intent_correct": arm_correct_on_conv,
            "conv_probe_intent_correct": int(sum(conv_rows.values())),
            "aa_intent_correct": sum(1 for s in conv_ids if arms["aa"]["rows"][s][FIELD]),
            "per_row_correctness_agreement_arm_vs_conv": agree,
        },
        "already_delivered_but_aa_wrong": {
            "rows": len(both_aa_wrong),
            "arm_intent_correct": sum(1 for s in both_aa_wrong if arms["arm"]["rows"][s][FIELD]),
        },
    }


def per_class(arms: dict, bank: dict, ids: list[str]) -> dict:
    groups: dict[str, list[str]] = defaultdict(list)
    for s in ids:
        groups[bank[s]["plan_class"]].append(s)
    slu_groups = PAIRED.MICRO_METRICS["slu_f1_micro"]
    out = {}
    for name, members in sorted(groups.items()):
        t = transitions(arms, members)
        out[name] = {
            "rows": len(members),
            "aa_intent_correct": t["right_to_right"] + t["right_to_wrong"],
            "arm_intent_correct": t["right_to_right"] + t["wrong_to_right"],
            "gained": t["wrong_to_right"],
            "lost": t["right_to_wrong"],
            "aa_slu_pct": 100 * pooled_f1(arms["aa"]["rows"], members, slu_groups),
            "arm_slu_pct": 100 * pooled_f1(arms["arm"]["rows"], members, slu_groups),
        }
    return out


# --------------------------------------------------------------------------- 5. tokens


def token_accounting(arm: dict, phases: dict[str, dict], ids: list[str]) -> dict:
    role_of: dict[str, tuple[str, int]] = {}
    for s in ids:
        role_of.update(phases[s]["roles"])
    per_role: dict[str, Counter] = defaultdict(Counter)
    perception_prompt: dict[str, int] = {}
    totals = Counter()
    unmapped = 0
    trace = arm["arm"].artifact("trace.jsonl")
    with trace.open("r", encoding="utf-8") as handle:
        for line in handle:
            if '"MODEL_WIRE_RESPONSE"' not in line[:64]:
                continue
            record = json.loads(line)
            if record.get("channel") != "MODEL_WIRE_RESPONSE":
                continue
            payload = record["payload"]
            wire = json.loads(base64.b64decode(payload["response_b64"]))
            usage = wire.get("usage") or {}
            timings = wire.get("timings") or {}
            prompt = int(usage.get("prompt_tokens") or 0)
            prefilled = timings.get("prompt_n")
            cached = timings.get("cache_n")
            del wire
            role = role_of.get(str(payload.get("request_id")))
            if role is None:
                # A wire response whose request id no role-visit receipt names: counted in the
                # totals so they reconcile to the sealed cost, and reported under its own bucket
                # rather than guessed into a role.
                unmapped += 1
                role = ("unattributed", -1)
            role_id, visit = role
            bucket = per_role[role_id]
            bucket["contacts"] += 1
            bucket["prompt_tokens"] += prompt
            totals["contacts"] += 1
            totals["prompt_tokens"] += prompt
            if prefilled is not None:
                bucket["prefilled_tokens"] += int(prefilled)
                bucket["cached_tokens"] += int(cached or 0)
                totals["prefilled_tokens"] += int(prefilled)
                totals["cached_tokens"] += int(cached or 0)
                totals["with_timings"] += 1
            if role_id == "perception" and visit == 0:
                perception_prompt[str(payload.get("sample_id"))] = prompt
    rows = len(ids)
    cost = arm["arm"].generation_manifest.get("cost") or {}
    return {
        "contacts": totals["contacts"],
        "contacts_with_timings": totals["with_timings"],
        "unmapped_wire_responses": unmapped,
        "prompt_tokens_total": totals["prompt_tokens"],
        "prompt_tokens_total_equals_sealed_cost": totals["prompt_tokens"] == int(cost.get("prompt_tokens_total", -1)),
        "contacts_equal_sealed_calls": totals["contacts"] == int(cost.get("calls_used", -1)),
        "prompt_tokens_per_row": totals["prompt_tokens"] / rows,
        "prefilled_tokens_per_row": totals["prefilled_tokens"] / rows,
        "cached_share": (totals["cached_tokens"] / totals["prompt_tokens"]) if totals["prompt_tokens"] else None,
        "per_role": {
            role: {
                "contacts": c["contacts"],
                "contacts_per_row": c["contacts"] / rows,
                "prompt_tokens_per_row": c["prompt_tokens"] / rows,
                "prefilled_tokens_per_row": c["prefilled_tokens"] / rows,
                "cached_share": (c["cached_tokens"] / c["prompt_tokens"]) if c["prompt_tokens"] else None,
            }
            for role, c in sorted(per_role.items())
        },
        "_perception_prompt_by_row": perception_prompt,
    }


def perception_block_delta(left: dict, right: dict, ids: list[str]) -> dict:
    lp, rp = left["_perception_prompt_by_row"], right["_perception_prompt_by_row"]
    missing = [s for s in ids if s not in lp or s not in rp]
    if missing:
        raise BesideReadError(f"{len(missing)} rows carry no first Perception contact on one side")
    deltas = [rp[s] - lp[s] for s in ids]
    return {
        "definition": (
            "per row, the first Perception contact's usage.prompt_tokens, arm minus A/A: the speech packet, "
            "the task contract and every other Perception input are byte-identical between the two cells, so "
            "the difference is the boundary block alone"
        ),
        "rows": len(ids),
        "mean_delta_tokens_per_row": statistics.fmean(deltas),
        "median_delta": statistics.median(deltas),
        "min_delta": min(deltas),
        "max_delta": max(deltas),
        "rows_with_zero_delta": sum(1 for d in deltas if d == 0),
        "registered_delta_tokens_per_row": REGISTERED_TOKEN_DELTA,
        "aa_mean_perception_prompt_tokens": statistics.fmean(lp[s] for s in ids),
        "arm_mean_perception_prompt_tokens": statistics.fmean(rp[s] for s in ids),
    }


# --------------------------------------------------------------------------- 6. instrument


def instrument(arms: dict, roster, ids: list[str]) -> dict:
    out = {}
    for left_key, right_key, role in PAIRS:
        left, right = arms[left_key], arms[right_key]
        pooled = PAIRED._pooled_contrast_block(
            left["rows"], right["rows"], ids, PAIRED.MICRO_METRICS["slu_f1_micro"],
            cluster_of=lambda s: roster.cluster_of_id[s], seed=SEED, draws=DRAWS,
        )
        per_row = PAIRED._per_row_block(
            left["rows"], right["rows"], ids, cluster_of=lambda s: roster.cluster_of_id[s],
            strata_of=None, seed=SEED, draws=DRAWS,
        )[FIELD]
        identical = sum(1 for s in ids if left["response_text_sha256"][s] == right["response_text_sha256"][s])
        out[f"{right_key}_vs_{left_key}"] = {
            "role": role,
            "left": left["label"], "right": right["label"],
            "slu_left_pct": pooled["left_pct"], "slu_right_pct": pooled["right_pct"],
            "slu_delta_pp": pooled["delta_pp"], "slu_ci95_pp": pooled["cluster_bootstrap"]["ci95_pp"],
            "intent_left_pct": per_row["left_pct"], "intent_right_pct": per_row["right_pct"],
            "intent_delta_pp": per_row["delta_pp"], "intent_ci95_pp": per_row["cluster_bootstrap"]["ci95_pp"],
            "intent_saves": per_row["saves"], "intent_harms": per_row["harms"],
            "delivered_answer_byte_identical_rows": identical,
            "inside_own_null": {
                "slu": abs(pooled["delta_pp"]) <= OWN_NULL["h_slu"],
                "intent": abs(per_row["delta_pp"]) <= OWN_NULL["h_intent"],
            },
        }
    return out


# --------------------------------------------------------------------------- main


def render(result: dict) -> str:
    lines = [f"# Cell AGREE: beside-verdict quantities ({result['generated_at_utc']})", "",
             "Model-free; counts only. Machine record: beside-v1.json.", ""]
    for name, block in result["per_scenario"].items():
        lines += [f"## Per scenario, {name}", "",
                  "| scenario | n | intent left | intent right | delta | saves | harms | SLU left | SLU right | delta |",
                  "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
        for scenario, c in block["per_scenario"].items():
            lines.append(
                f"| {scenario} | {c['n']} | {c['left_intent_pct']:.2f} | {c['right_intent_pct']:.2f} | "
                f"{c['intent_delta_pp']:+.2f} | {c['intent_saves']} | {c['intent_harms']} | "
                f"{c['left_slu_pct']:.2f} | {c['right_slu_pct']:.2f} | {c['slu_delta_pp']:+.2f} |")
        w = block["weightings"]
        lines += ["", f"natural mixture: intent {w['natural_mixture']['intent_delta_pp']:+.4f}, "
                      f"SLU {w['natural_mixture']['slu_delta_pp']:+.4f}; equal-scenario: intent "
                      f"{w['equal_scenario']['intent_delta_pp']:+.4f}, SLU {w['equal_scenario']['slu_delta_pp']:+.4f}", ""]
    lines += ["## Delivery, conversion, per class, tokens, frontier, instrument", "", "```json",
              json.dumps({k: result[k] for k in ("delivery", "conversion", "per_class", "tokens",
                                                   "perception_block_delta", "frontier", "instrument")},
                         indent=1, sort_keys=True), "```", ""]
    return "\n".join(lines)


def run(args: argparse.Namespace) -> int:
    repo = Path(args.repo_root).resolve()
    data_root = Path(args.data_root).resolve()
    out_dir = Path(args.out_dir) if args.out_dir else data_root / ANALYSIS_ROOT / "beside"
    if out_dir.resolve().parent != (data_root / ANALYSIS_ROOT).resolve() or out_dir.name != "beside":
        raise BesideReadError("the output directory must be <analysis root>/beside")
    roster = PAIRED.load_roster(repo, ROSTER, "sample_id")
    if roster.sha256 != ROSTER_SHA256:
        raise BesideReadError("the Fold A roster receipt does not hash to its pin")
    strata = {str(item["sample_id"]): str(item["stratum"]) for item in roster.document["items"]}
    ids = list(roster.ids)

    arms = {key: load_sealed_arm(data_root, key) for key in ARMS}
    for key, arm in arms.items():
        if sorted(arm["rows"]) != sorted(ids):
            raise BesideReadError(f"{key}: the official per-sample rows are not the roster")

    # The paired driver's own gating numbers must reproduce here, or nothing below is believed.
    contrasts = load_json(data_root / ANALYSIS_ROOT / "vs-aa" / "score-contrasts.json")
    slu_groups = PAIRED.MICRO_METRICS["slu_f1_micro"]
    for side, key in (("left_pct", "aa"), ("right_pct", "arm")):
        mine = 100 * pooled_f1(arms[key]["rows"], ids, slu_groups)
        if abs(mine - contrasts["pooled_micro"]["slu_f1_micro"][side]) > 1e-9:
            raise BesideReadError(f"pooled SLU-F1 of {key} does not reproduce the paired driver")
        mine_i = 100 * statistics.fmean(arms[key]["rows"][s][FIELD] for s in ids)
        if abs(mine_i - contrasts["per_row"][FIELD][side]) > 1e-9:
            raise BesideReadError(f"intent of {key} does not reproduce the paired driver")

    phases = {key: phase_rows(arms[key]["phases_path"]) for key in ("arm", "aa", "plan")}
    bank = load_bank(data_root, ids)
    deliv = delivery(arms, phases, bank, ids, data_root, repo)
    conv = conversion(arms, deliv, bank, ids, data_root)
    classes = per_class(arms, bank, ids)

    tokens = {key: token_accounting(arms[key], phases[key], ids) for key in ("arm", "aa")}
    block = perception_block_delta(tokens["aa"], tokens["arm"], ids)
    for key, t in tokens.items():
        t.pop("_perception_prompt_by_row")
        t["supplied_items_per_row_by_kind"] = supply_kinds(phases[key], ids)

    efficiency_path = data_root / ANALYSIS_ROOT / "vs-aa" / "efficiency.json"
    efficiency = load_json(efficiency_path)
    intent = contrasts["per_row"][FIELD]
    slu = contrasts["pooled_micro"]["slu_f1_micro"]
    frontier = {}
    for key, side in (("arm", "right"), ("aa", "left")):
        hours = efficiency[side]["gpu_hours"] * 1080 / efficiency[side]["rows"]
        frontier[key] = {
            "official_intent_pct": arms[key]["official"]["intent_accuracy"] * 100,
            "official_slu_pct": arms[key]["official"]["slu_f1"] * 100,
            "gpu_hours_per_1080": hours,
            "contacts_per_row": efficiency[side]["contacts_per_row"],
            "prompt_tokens_per_row": tokens[key]["prompt_tokens_per_row"],
            "prefilled_tokens_per_row": tokens[key]["prefilled_tokens_per_row"],
        }
    frontier["delta_arm_minus_aa"] = {
        "intent_pp": intent["delta_pp"],
        "slu_pp": slu["delta_pp"],
        "gpu_hours_per_1080": frontier["arm"]["gpu_hours_per_1080"] - frontier["aa"]["gpu_hours_per_1080"],
        "prefilled_tokens_per_row": frontier["arm"]["prefilled_tokens_per_row"] - frontier["aa"]["prefilled_tokens_per_row"],
        "prompt_tokens_per_row": frontier["arm"]["prompt_tokens_per_row"] - frontier["aa"]["prompt_tokens_per_row"],
        "intent_pp_per_gpu_hour_per_1080": intent["delta_pp"] / frontier["arm"]["gpu_hours_per_1080"],
        "intent_pp_per_1000_prefilled_tokens_per_row": 1000 * intent["delta_pp"] / frontier["arm"]["prefilled_tokens_per_row"],
    }
    frontier["gpu_hours_source"] = {"relpath": str(ANALYSIS_ROOT / "vs-aa" / "efficiency.json"),
                                    "sha256": digest(efficiency_path)}

    per_scen = {
        "arm vs A/A (gating)": per_scenario(arms["aa"], arms["arm"], strata, ids),
        "arm vs PLAN (context)": per_scenario(arms["plan"], arms["arm"], strata, ids),
    }
    result = {
        "schema": SCHEMA,
        "recipe_id": RECIPE_ID,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "driver": {"relpath": "scripts/analysis/slurp_agree_beside_read.py", "sha256": digest(Path(__file__))},
        "paired_driver_sha256": digest(REPO_ROOT / "scripts" / "analysis" / "slurp_paired_roster_read.py"),
        "contacts": dict(CONTACTS_ZERO),
        "roster": {"relpath": ROSTER, "sha256": roster.sha256, "rows": len(ids),
                   "strata": dict(sorted(Counter(strata[s] for s in ids).items()))},
        "sealed": {key: {"run_id": a["run_id"], "attempt_id": a["attempt_id"], "study_commit": a["study_commit"],
                         "hashes": a["hashes"]} for key, a in arms.items()},
        "per_scenario": per_scen,
        "delivery": deliv["report"],
        "conversion": conv,
        "per_class": classes,
        "tokens": tokens,
        "perception_block_delta": block,
        "frontier": frontier,
        "instrument": instrument(arms, roster, ids),
        "boundary": "A development read on a TRAIN construction fold (owner decisions 28 and 86).",
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "beside-v1.json"
    json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path = out_dir / "beside-v1.md"
    md_path.write_text(render(result), encoding="utf-8")
    print(f"beside-v1.json sha256 {digest(json_path)}")
    print(f"beside-v1.md sha256 {digest(md_path)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--out-dir", default=None)
    args = parser.parse_args(argv)
    try:
        return run(args)
    except BesideReadError as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
