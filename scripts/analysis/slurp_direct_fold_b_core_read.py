#!/usr/bin/env python3
"""slurp_direct_fold_b_core_read.py -- the preregistered READ of the 266-E bare-core read (Thinking versus Instruct, direct-only, TRAIN Fold B).

Package ``docs/readiness/2026-10-11-slurp-direct-only-fold-b-thinking-vs-instruct-v1/`` (preregistration section 3). Two stages:

  smoke   the four-row Thinking smoke: decode cost from the sealed trace -- completion tokens per answer (p50/p99), seconds per contact (p50/p99)
          and the GPU-hour projection for 1,080 rows -- plus the reasoning-leak count and the empty / no-object counts of the delivered content.
          Nothing is scored; the coordinator reads this to sign off the Thinking arm.
  read    the full read over the three sealed arms: paired SLU-F1 and intent contrasts, Thinking minus the mean of the two Instruct passes
          (utterance-cluster bootstrap), the twin offset (replicate minus Instruct), the per-scenario table (natural-mixture and equal-scenario
          weightings), the Thinking answer-length and parse-failure tables, the reasoning-leak count over all three arms, cost, and the preregistered
          verdict word (RESOLVED-ABOVE-BAR / NOT RESOLVED / HARM).

Model-free. Every sealed byte is opened read-only. NO utterance text, transcript, gold label, model output or reasoning text is ever printed or
persisted: delivered text is reduced to boolean flags (empty / no JSON object / reasoning marker) at read time and dropped; artifacts carry ids,
scenario names, flags, scores, counts and hashes only.

    python -B scripts/analysis/slurp_direct_fold_b_core_read.py --stage smoke --data-root $SPEECHRL_DATA_DIR
    python -B scripts/analysis/slurp_direct_fold_b_core_read.py --stage read  --data-root $SPEECHRL_DATA_DIR
"""

from __future__ import annotations
import os

import argparse
import hashlib
import json
import math
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Callable, Mapping, Sequence

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parents[1]
for _path in (str(_REPO / "src"), str(_HERE), str(_REPO / "scripts" / "flights" / "direct")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from speech_aware_evidence_acquisition.analysis.null_calibration import pooled_f1  # noqa: E402
from speech_aware_evidence_acquisition.analysis.paired import resampled_statistic  # noqa: E402
from speech_aware_evidence_acquisition.core.model.transport import reasoning_marker_in_content  # noqa: E402

SCHEMA_SMOKE = "saea-slurp-direct-fold-b-core-read-smoke-v1"
SCHEMA_READ = "saea-slurp-direct-fold-b-core-read-v1"
SLU_GROUPS = (("slu_f1_word_tp", "slu_f1_char_tp"), ("slu_f1_word_fp", "slu_f1_char_fp"), ("slu_f1_word_fn", "slu_f1_char_fn"))
INTENT_FIELD = "scenario_action_exact"
SCORER = "slurp-slu-official-train"
DEFAULT_SEED = 20261011
DEFAULT_DRAWS = 10_000
BAR_PP = 2.5
#: The Thinking completion cap of the amended geometry (direct_fb_family.THINK_MAX_TOKENS; 2048 before the 2026-10-11 decode-cost sign-off).
THINKING_CAP = 8192
EMPTY_COMPLETION_SCHEMA = "saea-empty-completion-v1"
SLOTS = 4
CONTACTS_ZERO = {"model": 0, "tokenizer": 0, "encoder": 0, "scorer": 0, "server": 0}
VERDICT_WORDS = ("RESOLVED-ABOVE-BAR", "NOT RESOLVED", "HARM")


class ReadError(RuntimeError):
    """A refusal: a sealed artifact is missing, malformed, or the arms do not share the roster."""


# --------------------------------------------------------------------------- small statistics


def percentile(values: Sequence[float], q: float) -> float:
    """Linear-interpolation percentile, q in [0, 100]; NaN for an empty sequence."""

    ordered = sorted(float(v) for v in values)
    if not ordered:
        return float("nan")
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * q / 100.0
    lo, hi = math.floor(rank), math.ceil(rank)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (rank - lo)


def interval(replicates: Sequence[float], point: float, level: float = 0.95) -> dict:
    tail = (1.0 - level) / 2.0 * 100.0
    lo, hi = percentile(replicates, tail), percentile(replicates, 100.0 - tail)
    return {"point_pp": 100.0 * point, "ci95_lo_pp": 100.0 * lo, "ci95_hi_pp": 100.0 * hi, "ci95_half_width_pp": 50.0 * (hi - lo), "draws": len(replicates)}


# --------------------------------------------------------------------------- loaders (delivered text is reduced to flags and dropped)


def text_flags(text: object) -> dict:
    if not isinstance(text, str):
        return {"empty": True, "no_object": True, "leak": False}
    stripped = text.strip()
    return {"empty": stripped == "", "no_object": "{" not in stripped, "leak": reasoning_marker_in_content(text) is not None}


def load_output_flags(path: Path) -> dict[str, dict]:
    """{sample_id: flags} from ``<run>.outputs.jsonl``; the ``text`` field is reduced to flags and never kept."""

    flags: dict[str, dict] = {}
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            flags[str(row["sample_id"])] = text_flags(row.get("text"))
            row.clear()
    return flags


def load_trace_costs(path: Path) -> list[dict]:
    """One record per contact from the trace's COST channel: tokens and latency only (the trace's MODEL_RESPONSE text is never read)."""

    costs: list[dict] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if '"COST"' not in line:
                continue
            record = json.loads(line)
            if record.get("channel") != "COST":
                continue
            payload = record.get("payload") or {}
            costs.append({"completion_tokens": int(payload.get("completion_tokens") or 0), "prompt_tokens": int(payload.get("prompt_tokens") or 0),
                          "latency_seconds": float(payload.get("latency_seconds") or 0.0)})
    return costs


def load_trace_empty_receipts(path: Path) -> list[dict]:
    """The empty-completion receipts of a trace (rails.runner.EMPTY_COMPLETION_SCHEMA): flags, token counts and the finish reason only."""

    receipts: list[dict] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if EMPTY_COMPLETION_SCHEMA not in line:
                continue
            payload = (json.loads(line).get("payload") or {})
            if payload.get("schema") != EMPTY_COMPLETION_SCHEMA:
                continue
            receipts.append({"cap_hit": bool(payload.get("cap_hit")), "completion_tokens": payload.get("completion_tokens"),
                             "finish_reason": payload.get("finish_reason")})
    return receipts


def receipt_table(receipts: Sequence[Mapping]) -> dict:
    """Counts only: how many contacts delivered empty content, how many of those spent their whole budget, and the finish reasons."""

    return {"n": len(receipts), "cap_hit": sum(1 for r in receipts if r["cap_hit"]),
            "finish_reasons": dict(sorted(Counter(str(r["finish_reason"]) for r in receipts).items()))}


def rows_table(scores: Mapping, scorer_id: str) -> dict[str, dict[str, float]]:
    """{sample_id: numeric fields} of a scorer's per-sample rows; refuses a text field (the shape a stray answer would take)."""

    table: dict[str, dict[str, float]] = {}
    for row in scores[scorer_id]["per_sample"]:
        sid = str(row["sample_id"])
        values: dict[str, float] = {}
        for key, value in row.items():
            if key == "sample_id":
                continue
            if isinstance(value, str):
                raise ReadError(f"per-sample row {sid!r} field {key!r} is text; refusing to load it")
            if isinstance(value, bool):
                values[key] = 1.0 if value else 0.0
            elif isinstance(value, (int, float)):
                values[key] = float(value)
        table[sid] = values
    return table


# --------------------------------------------------------------------------- tables


def answer_length_table(costs: Sequence[Mapping], cap: int = THINKING_CAP) -> dict:
    tokens = [c["completion_tokens"] for c in costs]
    hits = sum(1 for t in tokens if t >= cap)
    return {"n": len(tokens), "cap": cap, "cap_hits": hits, "cap_hit_rate": hits / len(tokens) if tokens else float("nan"),
            "completion_tokens": {"mean": sum(tokens) / len(tokens) if tokens else float("nan"), "p10": percentile(tokens, 10), "p50": percentile(tokens, 50),
                                  "p90": percentile(tokens, 90), "p99": percentile(tokens, 99), "max": max(tokens) if tokens else float("nan")}}


def cost_table(costs: Sequence[Mapping], rows: int = 1080, slots: int = SLOTS) -> dict:
    """Seconds per contact and the 1,080-row GPU-hour projection.

    ``projection_gpu_hours = rows x mean latency / slots / 3600`` assumes the slots stay saturated (np4 here); ``upper_gpu_hours`` uses the p99
    latency. A four-row smoke fills the four slots once, so both are ESTIMATES -- the sign-off reads them beside the cap-hit rate."""

    latencies = [c["latency_seconds"] for c in costs]
    mean = sum(latencies) / len(latencies) if latencies else float("nan")
    p99 = percentile(latencies, 99)
    return {"contacts": len(latencies), "seconds_per_contact": {"mean": mean, "p50": percentile(latencies, 50), "p99": p99},
            "projection_rows": rows, "slots": slots,
            "projection_gpu_hours": rows * mean / slots / 3600.0 if latencies else float("nan"),
            "upper_gpu_hours": rows * p99 / slots / 3600.0 if latencies else float("nan"),
            "prompt_tokens_per_contact_mean": sum(c["prompt_tokens"] for c in costs) / len(costs) if costs else float("nan")}


def flag_counts(flags: Mapping[str, Mapping]) -> dict:
    n = len(flags)
    return {"rows": n, "empty_content": sum(1 for f in flags.values() if f["empty"]), "no_json_object": sum(1 for f in flags.values() if f["no_object"]),
            "reasoning_leak": sum(1 for f in flags.values() if f["leak"])}


def absent_solver_columns(outputs_rows: Sequence[Mapping], arms: Sequence[str]) -> dict:
    """NX-T R1 seal fix (2026-10-15): per arm, the rows whose level-2 Solver column is ABSENT (a NON-delivering branch whose Solver contact ended on a
    finite completion; receipt keys ``solver_absent`` / ``absent_reason``). Ids, counts and reason codes only. Such a row is that arm's DELIVERY FAILURE:
    the column renderer scores it as the canonical empty answer (zero in every paired contrast), and a reader reports the count beside its table."""

    ids: dict[str, list[str]] = {arm: [] for arm in arms}
    reasons: dict[str, int] = {}
    for row in outputs_rows:
        branches = (((row.get("native_episode_receipt") or {}).get("perception_branches") or {}).get("branches")) or []
        for branch in branches:
            if branch.get("solver_absent"):
                ids.setdefault(str(branch.get("branch_id")), []).append(str(row["sample_id"]))
                reason = str(branch.get("absent_reason"))
                reasons[reason] = reasons.get(reason, 0) + 1
    by_arm = {arm: len(sorted(found)) for arm, found in ids.items()}
    return {"by_arm": by_arm, "sample_ids_by_arm": {arm: sorted(found) for arm, found in ids.items()}, "total": sum(by_arm.values()),
            "rows": len({sid for found in ids.values() for sid in found}), "reasons": dict(sorted(reasons.items()))}


def require_absent_scored_zero(arm_scores: Mapping[str, Mapping[str, Mapping[str, float]]], absent: Mapping, intent_field: str = INTENT_FIELD) -> None:
    """Refuse a read in which an absent Solver column carries a non-zero score: it must have been rendered as the canonical empty answer."""

    for arm, sample_ids in (absent.get("sample_ids_by_arm") or {}).items():
        rows = arm_scores.get(arm) or {}
        for sample_id in sample_ids:
            row = rows.get(sample_id)
            if row is None:
                raise ReadError(f"{arm}: the absent Solver column of a row has no score row")
            bad = sorted(key for key, value in row.items() if (key.endswith("_tp") or key == intent_field) and value != 0)
            if bad:
                raise ReadError(f"{arm}: an absent Solver column is not scored as the canonical empty answer ({bad})")


def smoke_stage(costs: Sequence[Mapping], flags: Mapping[str, Mapping], cap: int = THINKING_CAP, rows: int = 1080,
                receipts: Sequence[Mapping] = ()) -> dict:
    return {"schema": SCHEMA_SMOKE, "status": "DECODE-COST (no score, no read)", "answer_length": answer_length_table(costs, cap), "cost": cost_table(costs, rows),
            "delivered_content": flag_counts(flags), "empty_completion_receipts": receipt_table(receipts), "contacts": CONTACTS_ZERO}


def _pooled(rows: Mapping[str, Mapping[str, float]], ids: Sequence[str]) -> float:
    return pooled_f1(rows, ids, SLU_GROUPS)


def _mean_field(rows: Mapping[str, Mapping[str, float]], ids: Sequence[str], field: str) -> float:
    return sum(rows[i][field] for i in ids) / len(ids) if ids else float("nan")


def paired_contrasts(arms: Mapping[str, Mapping[str, Mapping[str, float]]], ids: Sequence[str], cluster_of: Callable[[str], str], *, seed: int, draws: int) -> dict:
    """arms = {'instruct': rows, 'replicate': rows, 'thinking': rows}. d = Thinking - mean(Instruct, replicate); o = replicate - Instruct."""

    inst, rep, think = arms["instruct"], arms["replicate"], arms["thinking"]

    def run(statistic: Callable[[Sequence[str]], float]) -> dict:
        result = resampled_statistic(sample_ids=list(ids), statistic=statistic, seed=seed, n_replicates=draws, ci_level=0.95, cluster_of=cluster_of)
        return interval(result.replicates, result.point_estimate)

    def slu_d(resampled: Sequence[str]) -> float:
        return _pooled(think, resampled) - 0.5 * (_pooled(inst, resampled) + _pooled(rep, resampled))

    def slu_o(resampled: Sequence[str]) -> float:
        return _pooled(rep, resampled) - _pooled(inst, resampled)

    def intent_d(resampled: Sequence[str]) -> float:
        return _mean_field(think, resampled, INTENT_FIELD) - 0.5 * (_mean_field(inst, resampled, INTENT_FIELD) + _mean_field(rep, resampled, INTENT_FIELD))

    def intent_o(resampled: Sequence[str]) -> float:
        return _mean_field(rep, resampled, INTENT_FIELD) - _mean_field(inst, resampled, INTENT_FIELD)

    def sht(left: Mapping, right: Mapping) -> dict:
        saves = sum(1 for i in ids if right[i][INTENT_FIELD] > left[i][INTENT_FIELD])
        harms = sum(1 for i in ids if right[i][INTENT_FIELD] < left[i][INTENT_FIELD])
        return {"saves": saves, "harms": harms, "ties": len(ids) - saves - harms}

    return {
        "slu_f1": {"instruct_pct": 100 * _pooled(inst, ids), "replicate_pct": 100 * _pooled(rep, ids), "thinking_pct": 100 * _pooled(think, ids),
                   "delta_thinking_vs_mean_instruct": run(slu_d), "twin_offset_replicate_minus_instruct": run(slu_o)},
        "intent": {"instruct_pct": 100 * _mean_field(inst, ids, INTENT_FIELD), "replicate_pct": 100 * _mean_field(rep, ids, INTENT_FIELD),
                   "thinking_pct": 100 * _mean_field(think, ids, INTENT_FIELD),
                   "delta_thinking_vs_mean_instruct": run(intent_d), "twin_offset_replicate_minus_instruct": run(intent_o),
                   "saves_harms_ties": {"thinking_vs_instruct": sht(inst, think), "thinking_vs_replicate": sht(rep, think), "replicate_vs_instruct": sht(inst, rep)}},
        "n": len(ids),
    }


def per_scenario_table(arms: Mapping[str, Mapping[str, Mapping[str, float]]], ids: Sequence[str], scenario_of: Callable[[str], str]) -> dict:
    groups: dict[str, list[str]] = defaultdict(list)
    for sid in ids:
        groups[scenario_of(sid)].append(sid)
    table: dict[str, dict] = {}
    for name, members in sorted(groups.items()):
        entry: dict = {"n": len(members)}
        for key in ("instruct", "replicate", "thinking"):
            entry[f"slu_{key}_pct"] = 100 * _pooled(arms[key], members)
            entry[f"intent_{key}_pct"] = 100 * _mean_field(arms[key], members, INTENT_FIELD)
        entry["slu_delta_pp"] = entry["slu_thinking_pct"] - 0.5 * (entry["slu_instruct_pct"] + entry["slu_replicate_pct"])
        entry["intent_delta_pp"] = entry["intent_thinking_pct"] - 0.5 * (entry["intent_instruct_pct"] + entry["intent_replicate_pct"])
        table[name] = entry
    scenarios = list(table.values())
    equal = {k: sum(e[k] for e in scenarios) / len(scenarios) for k in ("slu_delta_pp", "intent_delta_pp")} if scenarios else {}
    natural = {"slu_delta_pp": 100 * (_pooled(arms["thinking"], ids) - 0.5 * (_pooled(arms["instruct"], ids) + _pooled(arms["replicate"], ids))),
               "intent_delta_pp": 100 * (_mean_field(arms["thinking"], ids, INTENT_FIELD)
                                         - 0.5 * (_mean_field(arms["instruct"], ids, INTENT_FIELD) + _mean_field(arms["replicate"], ids, INTENT_FIELD)))}
    return {"scenarios": table, "natural_mixture": natural, "equal_scenario": equal}


def verdict(delta_pp: float, ci_lo_pp: float, ci_hi_pp: float, offset_pp: float, leak_count: int, bar_pp: float = BAR_PP) -> str:
    """The preregistered verdict word (preregistration section 3)."""

    margin = abs(offset_pp)
    if delta_pp >= bar_pp and ci_lo_pp > margin and leak_count == 0:
        return "RESOLVED-ABOVE-BAR"
    if delta_pp <= -bar_pp and ci_hi_pp < -margin:
        return "HARM"
    return "NOT RESOLVED"


def read_stage(arms: Mapping[str, Mapping[str, Mapping[str, float]]], ids: Sequence[str], cluster_of: Callable[[str], str], scenario_of: Callable[[str], str],
               flags: Mapping[str, Mapping[str, Mapping]], thinking_costs: Sequence[Mapping], costs_by_arm: Mapping[str, Sequence[Mapping]], *,
               seed: int = DEFAULT_SEED, draws: int = DEFAULT_DRAWS, cap: int = THINKING_CAP, thinking_receipts: Sequence[Mapping] = ()) -> dict:
    contrast = paired_contrasts(arms, ids, cluster_of, seed=seed, draws=draws)
    leaks = sum(flag_counts(flags[key])["reasoning_leak"] for key in flags)
    slu = contrast["slu_f1"]
    word = verdict(slu["delta_thinking_vs_mean_instruct"]["point_pp"], slu["delta_thinking_vs_mean_instruct"]["ci95_lo_pp"],
                   slu["delta_thinking_vs_mean_instruct"]["ci95_hi_pp"], slu["twin_offset_replicate_minus_instruct"]["point_pp"], leaks)
    return {
        "schema": SCHEMA_READ, "status": "PREREGISTERED-READ (development numbers; never a test claim)", "verdict": word, "verdict_words": list(VERDICT_WORDS),
        "bar_pp": BAR_PP, "interval": {"kind": "utterance-cluster bootstrap", "draws": draws, "seed": seed, "level": "CI95"},
        "contrast": contrast, "per_scenario": per_scenario_table(arms, ids, scenario_of),
        "thinking_answer_length": answer_length_table(thinking_costs, cap),
        "thinking_empty_completion_receipts": receipt_table(thinking_receipts),
        "delivered_content": {key: flag_counts(flags[key]) for key in sorted(flags)},
        "reasoning_leak_total": leaks,
        "scorer_parse_failures": {key: sum(1 for row in arms[key].values() if row.get("parsed", 1.0) == 0.0) for key in sorted(arms)},
        "cost": {key: cost_table(costs_by_arm[key], len(ids)) for key in sorted(costs_by_arm)},
        "contacts": CONTACTS_ZERO,
    }


def render_markdown(result: Mapping) -> str:
    lines = [f"# 266-E bare-core read -- verdict {result.get('verdict', 'n/a')}", ""]
    c = result.get("contrast")
    if c:
        s, i = c["slu_f1"], c["intent"]
        d, o = s["delta_thinking_vs_mean_instruct"], s["twin_offset_replicate_minus_instruct"]
        lines += ["| metric | Instruct | replicate | Thinking | delta vs mean Instruct (pp) | CI95 | twin offset (pp) |", "| --- | ---: | ---: | ---: | ---: | --- | ---: |",
                  f"| SLU-F1 | {s['instruct_pct']:.2f} | {s['replicate_pct']:.2f} | {s['thinking_pct']:.2f} | {d['point_pp']:+.2f} | [{d['ci95_lo_pp']:+.2f}, {d['ci95_hi_pp']:+.2f}] | {o['point_pp']:+.2f} |"]
        di, oi = i["delta_thinking_vs_mean_instruct"], i["twin_offset_replicate_minus_instruct"]
        lines += [f"| intent | {i['instruct_pct']:.2f} | {i['replicate_pct']:.2f} | {i['thinking_pct']:.2f} | {di['point_pp']:+.2f} | [{di['ci95_lo_pp']:+.2f}, {di['ci95_hi_pp']:+.2f}] | {oi['point_pp']:+.2f} |", ""]
    sc = result.get("per_scenario")
    if sc:
        lines += ["| scenario | n | SLU delta (pp) | intent delta (pp) |", "| --- | ---: | ---: | ---: |"]
        for name, e in sc["scenarios"].items():
            lines.append(f"| {name} | {e['n']} | {e['slu_delta_pp']:+.2f} | {e['intent_delta_pp']:+.2f} |")
        lines += [f"| natural mixture | | {sc['natural_mixture']['slu_delta_pp']:+.2f} | {sc['natural_mixture']['intent_delta_pp']:+.2f} |",
                  f"| equal scenario | | {sc['equal_scenario'].get('slu_delta_pp', float('nan')):+.2f} | {sc['equal_scenario'].get('intent_delta_pp', float('nan')):+.2f} |", ""]
    a = result.get("thinking_answer_length") or result.get("answer_length")
    if a:
        t = a["completion_tokens"]
        lines += [f"Thinking completion tokens per answer: p10 {t['p10']:.0f}, p50 {t['p50']:.0f}, p90 {t['p90']:.0f}, p99 {t['p99']:.0f}, max {t['max']:.0f}; cap {a['cap']} hit {a['cap_hits']} of {a['n']}.", ""]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- the sealed-run adapter and the CLI


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_paths(data_root: Path, run_id: str, attempt_id: str) -> dict[str, Path]:
    run_dir = Path(data_root) / "runs" / run_id / attempt_id
    return {"dir": run_dir, "outputs": run_dir / f"{run_id}.outputs.jsonl", "trace": run_dir / f"{run_id}.trace.jsonl", "scores": run_dir / f"{run_id}.scores.json",
            "manifest": run_dir / f"{run_id}.run-manifest.json"}


def load_arm(data_root: Path, run_id: str, attempt_id: str, *, scored: bool = True) -> dict:
    paths = run_paths(data_root, run_id, attempt_id)
    needed = ["outputs", "trace"] + (["scores", "manifest"] if scored else [])
    for name in needed:
        if not paths[name].exists():
            raise ReadError(f"{run_id}: missing sealed file {paths[name]}")
    arm = {"flags": load_output_flags(paths["outputs"]), "costs": load_trace_costs(paths["trace"]), "receipts": load_trace_empty_receipts(paths["trace"]), "hashes": {n: sha256_file(paths[n]) for n in needed}}
    if scored:
        manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
        if str(manifest.get("status", "")).upper() != "COMPLETED":
            raise ReadError(f"{run_id}: run manifest status is {manifest.get('status')!r}, not COMPLETED")
        arm["rows"] = rows_table(json.loads(paths["scores"].read_text(encoding="utf-8")), SCORER)
    return arm


def roster_maps(roster_path: Path) -> tuple[list[str], Callable[[str], str], Callable[[str], str]]:
    document = json.loads(Path(roster_path).read_text(encoding="utf-8"))
    items = document["items"]
    utterance = {str(i["sample_id"]): str(i.get("utterance_id", i["sample_id"])) for i in items}
    scenario = {str(i["sample_id"]): str(i.get("stratum", "unknown")) for i in items}
    return [str(i["sample_id"]) for i in items], utterance.__getitem__, scenario.__getitem__


def main(argv: Sequence[str] | None = None) -> int:
    import direct_fb_family as fam  # noqa: PLC0415

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("smoke", "read"), required=True)
    parser.add_argument("--data-root", type=Path, default=Path((os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")))
    parser.add_argument("--repo-root", type=Path, default=_REPO)
    parser.add_argument("--analysis-root", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--draws", type=int, default=DEFAULT_DRAWS)
    args = parser.parse_args(argv)
    root = args.analysis_root or (args.data_root / "analysis" / fam.READ_RUN_ID)
    root.mkdir(parents=True, exist_ok=True)
    cells = fam.CELLS
    try:
        if args.stage == "smoke":
            arm = load_arm(args.data_root, cells["smoke"]["run"], cells["smoke"]["attempt"], scored=False)
            result = smoke_stage(arm["costs"], arm["flags"], receipts=arm["receipts"])
            result["sealed_hashes"] = arm["hashes"]
            out = root / "smoke-decode-cost.json"
        else:
            loaded = {key: load_arm(args.data_root, cells[key]["run"], cells[key]["attempt"]) for key in fam.ARM_KEYS}
            ids, cluster_of, scenario_of = roster_maps(args.repo_root / fam.ROSTER["arm"])
            for key, arm in loaded.items():
                if set(arm["rows"]) != set(ids):
                    raise ReadError(f"{key}: the per-sample id set is not the frozen Fold B roster's")
            result = read_stage({k: loaded[k]["rows"] for k in fam.ARM_KEYS}, ids, cluster_of, scenario_of, {k: loaded[k]["flags"] for k in fam.ARM_KEYS},
                                loaded["thinking"]["costs"], {k: loaded[k]["costs"] for k in fam.ARM_KEYS}, seed=args.seed, draws=args.draws,
                                thinking_receipts=loaded["thinking"]["receipts"])
            result["sealed_hashes"] = {k: loaded[k]["hashes"] for k in fam.ARM_KEYS}
            out = root / "read.json"
    except ReadError as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 2
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / ("smoke-decode-cost.md" if args.stage == "smoke" else "README.md")).write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps({"written": str(out), "verdict": result.get("verdict"), "reasoning_leak": result.get("reasoning_leak_total", result.get("delivered_content", {}).get("reasoning_leak"))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
