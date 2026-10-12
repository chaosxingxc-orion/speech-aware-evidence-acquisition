#!/usr/bin/env python3
"""P-SV-1 branch contrast for the sealed-credit inner loop, run 2: PRE-READ, DESCRIPTIVE.

P-SV-1 (``SAEA-SLURP-STAGE3-PSV1-FOLD-B-V1``, seal-only completion) flew three level-2
Perception branches per row: ``a-agree`` (delivered), ``b-top2contrast`` (presentation
``top2-contrast-v1``) and ``t-twin`` (A's byte twin). Its registered READ row is countersigned
by the coordinator, not by this script; this script computes the B-vs-A (and the T-vs-A twin
null) numbers the inner loop's ``presentation_id = top2-contrast-v1`` knob needs, directly from
the sealed records, with the perception-branch read primitives
(``scripts/analysis/slurp_perception_branch_read.py``: ``paired_top1_read`` /
``paired_present_read`` and its 10,000-draw seed-20260807 bootstrap) and, for the level-2
answer columns, the official SLURP arithmetic in-process (``reproduction.slurp_scoring.
score_slu``, the same per-sample function the official scorer sums). Every number is labelled
pre-read and descriptive; nothing here is a READ verdict.

Level-2 columns: each branch's own first Solver answer is recovered from the declared
predecessor attempt's trace (``core.bundle.outputs.verify_predecessor_attempts``, the I7r
re-hash), matched to the branch by ``solver_response_text_sha256``, passed through the row's
own sealed deliver normaliser (``core.base.DELIVERY_NORMALISERS``) exactly like
``stage3_rollout_score.py --mode perception-branches`` renders a column, then parsed.

Zero model, server, GPU, scorer-subprocess or network contact. Gold only through the governed
TRAIN loader (``data.slurp.load_slurp_split``), in-process. The output JSON carries counts,
rates, pp and hashes only -- never utterance text, gold values, fillers or model output.
Deterministic apart from ``generated_at``; ``--check`` re-derives and diffs.
"""

from __future__ import annotations
import os

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

RUN_ID = "SAEA-SLURP-STAGE3-PSV1-FOLD-B-V1"
ATTEMPT = "attempt-slurp-native-stage3-psv1-fold-b-generation-v1-seal-only"
READ_ID = "SAEA-SLURP-SEALED-CREDIT-INNER-LOOP-RUN-2-PSV1-PREREAD-V1"
A, B, T = "a-agree", "b-top2contrast", "t-twin"
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")


def _load_branch_read():
    path = REPO_ROOT / "scripts" / "analysis" / "slurp_perception_branch_read.py"
    spec = importlib.util.spec_from_file_location("slurp_perception_branch_read", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["slurp_perception_branch_read"] = module
    spec.loader.exec_module(module)
    return module


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pooled_slu_f1(counts, ids) -> float:
    tp = sum(counts[i][0] for i in ids)
    fp = sum(counts[i][1] for i in ids)
    fn = sum(counts[i][2] for i in ids)
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return 100.0 * (2 * p * r / (p + r)) if p + r else 0.0


def derive(data_root: Path, lock_path: Path, workers: int) -> dict:
    from speech_aware_evidence_acquisition.analysis.bootstrap import paired_cluster_bootstrap
    from speech_aware_evidence_acquisition.core.base import DELIVERY_NORMALISERS
    from speech_aware_evidence_acquisition.core.bundle.outputs import verify_predecessor_attempts
    from speech_aware_evidence_acquisition.data.lock import load_lock
    from speech_aware_evidence_acquisition.data.slurp import load_slurp_split
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import parse_slu_response, score_slu
    import speech_aware_evidence_acquisition.rails.delivery_normalisers  # noqa: F401  (registers the normalisers)

    br = _load_branch_read()
    directory = data_root / "runs" / RUN_ID / ATTEMPT
    manifest_path = directory / f"{RUN_ID}.run-manifest.json"
    outputs_path = directory / f"{RUN_ID}.outputs.jsonl"
    scores_path = directory / f"{RUN_ID}.scores.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "COMPLETED":
        raise SystemExit("refused: P-SV-1 seal-only manifest is not COMPLETED")
    rows = [json.loads(line) for line in outputs_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = frozenset(r["sample_id"] for r in rows)
    traces, kept = verify_predecessor_attempts(manifest, split_ids=ids, attempt_id=ATTEMPT)
    if kept != ids:
        raise SystemExit("refused: predecessor did not keep every sealed row")
    sealed = {s["sample_id"]: s for s in json.loads(scores_path.read_text(encoding="utf-8"))
              ["slurp-slu-official-train"]["per_sample"]}

    gold_records = {r.sample_id: r for r in load_slurp_split(load_lock(lock_path), data_root, "train", workers=workers)}
    gold_intent = {sid: gold_records[sid].intent for sid in ids}

    # level 1 (the Perception note's own candidate list)
    level1 = {
        "top1_b_minus_a": br.paired_top1_read(rows, gold_intent, branch_id=B, against=A),
        "present_b_minus_a": br.paired_present_read(rows, gold_intent, branch_id=B, against=A),
        "top1_t_minus_a": br.paired_top1_read(rows, gold_intent, branch_id=T, against=A),
        "present_t_minus_a": br.paired_present_read(rows, gold_intent, branch_id=T, against=A),
        "top1_b_minus_a_utterance": br.utterance_level_top1_read(rows, gold_intent, branch_id=B, against=A),
    }
    rank_counts = {name: {"1": 0, "2": 0, "3+": 0, "absent": 0} for name in (A, B, T)}
    for row in rows:
        for name, outcome in br.level1_row_outcomes(row, gold_intent[row["sample_id"]]).items():
            if name in rank_counts:
                rank = outcome["rank"]
                key = "absent" if rank is None else ("3+" if rank >= 3 else str(rank))
                rank_counts[name][key] += 1

    # level 2 (each branch's own first Solver answer, through the row's own normaliser)
    intent_ok = {name: {} for name in (A, B, T)}
    slu_counts = {name: {} for name in (A, B, T)}
    unresolved = {name: 0 for name in (A, B, T)}
    malformed = {name: 0 for name in (A, B, T)}
    a_vs_delivered_intent_mismatch = 0
    for row in rows:
        sid = row["sample_id"]
        gold = gold_records[sid]
        records = traces[sid]
        by_hash = {}
        for key, record in records.items():
            if key.endswith("/response") and isinstance(record.get("text"), str):
                by_hash[record.get("response_text_sha256")] = record["text"]
        episode = row["native_episode_receipt"]
        normaliser = (episode.get("deliver_normaliser") or {}).get("normaliser_id")
        for item in episode["perception_branches"]["branches"]:
            name = item.get("branch_id")
            if name not in intent_ok:
                continue
            raw = by_hash.get(item.get("solver_response_text_sha256"))
            if raw is None or hashlib.sha256(raw.encode("utf-8")).hexdigest() != item.get("solver_response_text_sha256"):
                unresolved[name] += 1
                raw = ""
            text = DELIVERY_NORMALISERS.resolve(normaliser)(raw).text if normaliser else raw
            scenario, action, entities, ok = parse_slu_response(text)
            if not ok:
                malformed[name] += 1
            s = score_slu(gold_scenario=gold.scenario, gold_action=gold.action, gold_entities=gold.entities,
                          predicted_scenario=scenario, predicted_action=action, predicted_entities=entities)
            intent_ok[name][sid] = s.scenario_action_exact
            slu_counts[name][sid] = (s.slu_f1_word_tp + s.slu_f1_char_tp, s.slu_f1_word_fp + s.slu_f1_char_fp,
                                     s.slu_f1_word_fn + s.slu_f1_char_fn)
        if intent_ok[A].get(sid) != float(sealed[sid]["scenario_action_exact"]):
            a_vs_delivered_intent_mismatch += 1

    def paired(metric: str, left: str, right: str) -> dict:
        common = sorted(set(intent_ok[left]) & set(intent_ok[right]))
        if metric == "intent":
            stat = lambda xs: 100.0 * sum(intent_ok[left][x] - intent_ok[right][x] for x in xs) / len(xs)
        else:
            stat = lambda xs: _pooled_slu_f1(slu_counts[left], xs) - _pooled_slu_f1(slu_counts[right], xs)
        res = paired_cluster_bootstrap(sample_ids=common, statistic=stat, n_replicates=br.BOOT_N,
                                       seed=br.BOOT_SEED, ci_level=br.BOOT_LEVEL)
        out = {"n": len(common), "point_pp": round(res.point_estimate, 4),
               "ci95": [round(res.ci_low, 4), round(res.ci_high, 4)]}
        if metric == "intent":
            out["saves"] = sum(1 for x in common if intent_ok[left][x] > intent_ok[right][x])
            out["harms"] = sum(1 for x in common if intent_ok[left][x] < intent_ok[right][x])
        return out

    level2 = {
        "intent_pct": {n: round(100.0 * sum(v.values()) / len(v), 4) for n, v in intent_ok.items()},
        "slu_f1_pooled": {n: round(_pooled_slu_f1(c, sorted(c)), 4) for n, c in slu_counts.items()},
        "intent_b_minus_a": paired("intent", B, A),
        "intent_t_minus_a": paired("intent", T, A),
        "slu_b_minus_a": paired("slu", B, A),
        "slu_t_minus_a": paired("slu", T, A),
        "unresolved_answers": unresolved,
        "malformed_answers": malformed,
        "a_column_vs_sealed_delivered_intent_mismatch_rows": a_vs_delivered_intent_mismatch,
        "sealed_delivered_intent_pct": round(
            100.0 * sum(float(sealed[s]["scenario_action_exact"]) for s in ids) / len(ids), 4),
    }
    return {
        "schema": "saea-sealed-credit-psv1-preread-v1",
        "read_id": READ_ID,
        "status": "PRE-READ, DESCRIPTIVE (the P-SV-1 READ row is the coordinator's to countersign)",
        "run_id": RUN_ID, "attempt": ATTEMPT, "rows": len(rows),
        "inputs_sha256": {"run_manifest": _sha(manifest_path), "outputs": _sha(outputs_path),
                          "scores": _sha(scores_path)},
        "branches": {"delivered": A, "variant": B, "twin": T},
        "level1_rank_counts": rank_counts,
        "level1": level1,
        "level2": level2,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-root", default=DEFAULT_DATA_ROOT)
    parser.add_argument("--lock", default=DEFAULT_LOCK)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    data_root = Path(args.data_root)
    out = data_root / "analysis" / READ_ID / "report.json"
    report = derive(data_root, Path(args.lock), args.workers)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    strip = lambda s: re.sub(r'"generated_at": "[^"]*"', "", s)
    if args.check:
        same = out.is_file() and strip(out.read_text(encoding="utf-8")) == strip(text)
        print("check:", "IDENTICAL apart from generated_at" if same else "DIFFERS")
        return 0 if same else 1
    if out.exists():
        print(f"refused: {out} exists; pass --check", file=sys.stderr)
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {out} sha256 {hashlib.sha256(text.encode()).hexdigest()}")
    print(json.dumps({"level1": {k: {kk: v[kk] for kk in ("point_pp", "ci95", "n")} for k, v in report["level1"].items()},
                      "level1_rank_counts": report["level1_rank_counts"],
                      "level2": report["level2"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
